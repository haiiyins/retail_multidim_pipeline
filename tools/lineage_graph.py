"""Render pipeline architecture and dbt lineage figures for the report (WBS 5.1, issue #44).

Reads dbt_multidim/target/manifest.json (run `dbt docs generate` first) to verify and extract the model DAG,
and renders publication-grade vector (.svg) and high-DPI raster (.png) figures into docs/figures/:

  1. architecture_overview.{svg,png}      — High-level / generalized end-to-end architecture (for report overview & slides)
  2. architecture_detailed.{svg,png}      — Detailed end-to-end system & data-flow architecture (scripts, grains, F0–F5, R1–R5, QC-1..7)
  3. lineage_full.{svg,png}               — Complete 46-node table-level DAG across Bronze → Staging → Silver → Python Grid → Gold
  4. lineage_bronze_to_silver.{svg,png}   — Detailed Bronze → Silver lineage organized by 5 functional domain swimlanes
  5. lineage_silver_to_gold.{svg,png}     — Detailed Silver → Gold lineage (Anchor Grid, 3 Feature Entities, R1–R5, Ranking, QC-6)
  6. lineage_ingestion_to_bronze.{svg,png}— Detailed Ingestion & Bronze layer diagram (Batch + Redpanda Stream + Contracts + Gates)
  7. lineage_gold_to_evaluation.{svg,png} — Detailed Gold → Evaluation & Two-Axis Ablation diagram
"""
import json
import pathlib
import re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, PathPatch, Polygon, Circle
from matplotlib.path import Path
import numpy as np

MAN = pathlib.Path("dbt_multidim/target/manifest.json")
OUT = pathlib.Path("docs/figures")
OUT.mkdir(parents=True, exist_ok=True)

plt.rcParams["font.sans-serif"] = ["DejaVu Sans", "Arial", "Helvetica"]
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["svg.fonttype"] = "none"

man = json.loads(MAN.read_text())

# ── Colour & visual theme palette ─────────────────────────────────────────────
PALETTE = {
    "source": {
        "fill": "#F1F5F9", "border": "#64748B", "accent": "#334155",
        "title": "#0F172A", "sub": "#475569", "badge_bg": "#E2E8F0", "badge_fg": "#1E293B",
        "badge": "BRONZE VIEW", "edge": "#64748B", "legend": "Bronze source (Parquet view)"
    },
    "ext": {
        "fill": "#F3E8FF", "border": "#9333EA", "accent": "#6B21A8",
        "title": "#3B0764", "sub": "#581C87", "badge_bg": "#E9D5FF", "badge_fg": "#581C87",
        "badge": "EXT SOURCE", "edge": "#7E22CE", "legend": "Self-built external source (ext.*)"
    },
    "staging": {
        "fill": "#DCFCE7", "border": "#16A34A", "accent": "#15803D",
        "title": "#052E16", "sub": "#166534", "badge_bg": "#BBF7D0", "badge_fg": "#14532D",
        "badge": "STAGING VIEW", "edge": "#16A34A", "legend": "Staging view (pushdown & filter)"
    },
    "silver": {
        "fill": "#DBEAFE", "border": "#2563EB", "accent": "#1D4ED8",
        "title": "#172554", "sub": "#1E40AF", "badge_bg": "#BFDBFE", "badge_fg": "#1E3A8A",
        "badge": "SILVER MODEL", "edge": "#2563EB", "legend": "Silver model (cleaned & harmonised)"
    },
    "quarantine": {
        "fill": "#FFE4E6", "border": "#E11D48", "accent": "#BE123C",
        "title": "#4C0519", "sub": "#9F1239", "badge_bg": "#FECDD3", "badge_fg": "#881337",
        "badge": "QUARANTINE", "edge": "#E11D48", "legend": "Quarantine table / QC ledger"
    },
    "audit": {
        "fill": "#FEF3C7", "border": "#D97706", "accent": "#B45309",
        "title": "#451A03", "sub": "#92400E", "badge_bg": "#FDE68A", "badge_fg": "#78350F",
        "badge": "AUDIT TABLE", "edge": "#D97706", "legend": "Audit & observability table"
    },
    "python": {
        "fill": "#E0E7FF", "border": "#4F46E5", "accent": "#3730A3",
        "title": "#1E1B4B", "sub": "#3730A3", "badge_bg": "#C7D2FE", "badge_fg": "#312E81",
        "badge": "PYTHON GRID", "edge": "#4F46E5", "legend": "Gold anchor grid (Python-built)"
    },
    "gold": {
        "fill": "#FEF9C3", "border": "#CA8A04", "accent": "#A16207",
        "title": "#422006", "sub": "#713F12", "badge_bg": "#FEF08A", "badge_fg": "#713F12",
        "badge": "GOLD MODEL", "edge": "#CA8A04", "legend": "Gold feature store & ranking model"
    },
    "eval": {
        "fill": "#CCFBF1", "border": "#0D9488", "accent": "#0F766E",
        "title": "#042F2E", "sub": "#115E59", "badge_bg": "#99F6E4", "badge_fg": "#134E4A",
        "badge": "EVALUATION", "edge": "#0D9488", "legend": "Evaluation & ablation engine"
    },
}

# Concise technical descriptions for every node in the DAG
NODE_META = {
    # Sources
    "all_store_selling_price": ("Parquet · 42.4M rows", "SKU price intervals by unit type (15/50/7)"),
    "dim_calendar": ("CSV · Calendar dates", "Base date spine 2023–2026"),
    "public_holidays": ("ext.public_holidays", "Official SG/TH/VN holidays (holidays lib)"),
    "commercial_event_names": ("ext.commercial_event_names", "Curated campaign dictionary (Mid-Year, 11.11…)"),
    "stock_availability_rate": ("CSV · 5.4 GB", "Daily site stock snapshot (vars.use_stock)"),
    "dim_item": ("Parquet · 4.36M SKUs", "Product hierarchy, univers & list-typed gender"),
    "dim_business_unit": ("CSV · Store & Web units", "Unit type (7/15/50) & store timezone"),
    "sales_detail": ("Parquet · 89.3M lines", "POS & online sale / cancel / return lines"),
    "sales_tender_detail": ("Parquet · Tender lines", "Payment method breakdown per transaction"),
    "f_member_purchase": ("Parquet · Tx–Member link", "Transaction-to-loyalty-member associations"),
    "tracking_ecom_events": ("Parquet · 1,774 parts (~200 GB)", "1.0B web/app clickstream events (STRUCT/LIST)"),
    "d_member": ("CSV · 2.0 GB", "Loyalty profiles & non-consumer account flags"),
    "f_member_favorite_sport": ("CSV · Sport events", "Member add/remove favourite-sport logs"),
    # Staging
    "stg_sales_detail": ("View · 25/141 cols projected", "Projection pushdown, key casts & country filter"),
    "stg_tracking_ecom_events": ("View · Partition-pruned", "Country & date window filter on Parquet parts"),
    # Silver
    "slv_price_sku_interval": ("National SKU price timeline", "Type-15 unit priority, promo_kind, depth ≤ 90%"),
    "qrt_price_interval": ("QC-3 Quarantine · 1,118 rows", "Refused intervals with promo_depth > 90%"),
    "slv_calendar_enriched": ("Enriched country calendar", "Diff-array promo share peaks (≥1.5σ, ≥3d) + holidays"),
    "slv_dim_model": ("Model-level catalogue", "SKU → model_code, drops UUID/services/fixtures"),
    "slv_stock_daily_model": ("Site × model daily stock", "≤ 3-day forward-fill on time grid"),
    "slv_stock_daily_national": ("Country × model daily stock", "National availability roll-up"),
    "slv_sales_line_netted": ("Ephemeral · Dedup & netted", "Exact dedup, latest version_at, sale − cancel net"),
    "qrt_sales_line": ("QC-3/4 Quarantine · 6 reasons", "Non-merchandise, net ≤ 0, non-sale, unmapped SKU"),
    "slv_fact_sales_line": ("Clean merchandise sales fact", "Positive SALE lines, naive UTC tz, EUR conversion"),
    "slv_fact_returns": ("Clean return lines fact", "Linked to original sale transaction & model"),
    "slv_member_bridge": ("1:1 Transaction → Member", "Earliest association per tx; conflict warn test"),
    "slv_member_profile": ("Eligible consumer profiles", "Static attrs ≤ t; excludes staff/B2B/club/school"),
    "slv_member_sport_asof": ("Favourite-sport intervals", "Event → [valid_from, valid_to) state intervals"),
    "slv_member_store_daily": ("Running usual store (ASOF)", "Cumulative modal store per member × purchase day"),
    "slv_web_events_clean": ("Clean product web events", "Flattened STRUCT/LIST, numeric codes, is_event_to_use"),
    "slv_user_member_links": ("2-tier cookie → member links", "Tier 1 ORDER match, Tier 2 LOGIN + verified_ts"),
    "slv_user_to_member": ("Verified 1:1 cookie → member", "Unique cookie mappings with earliest verified_ts"),
    "slv_identity_conflicts": ("QC Quarantine · 945 cookies", "Cookies linked to >1 member ID (excluded)"),
    "stitching_coverage": ("Audit · Before/After stitching", "Direct vs stitched event share by country (37.6–42.0%)"),
    # Python Grid
    "split_windows": ("evaluation/split.yml cutoffs", "Train / Valid / Test bounds & 42-day purge gaps"),
    "anchor_grid": ("Eligible (member, Monday) grid", "≥2 tx, 90d positive filter, 4× train stride, 50k cap"),
    "anchor_model_grid": ("Purchasable (model, country, t)", "Models active within ±90d of used anchors"),
    # Gold
    "gld_web_stitched": ("Attributed member web events", "Direct + stitched within ±90d, verified_ts ≤ anchor"),
    "gld_sport_department_affinity": ("Learnt Sport → Dept affinity", "Empirical purchase lift strictly before valid_lo"),
    "gld_copurchase_lift": ("Basket co-purchase lift (M1, M2)", "Country pair lift strictly before valid_lo"),
    "gld_fs_member": ("Entity 1 · Member features at t", "F0 RFM, F1 price quantiles, F3 web, sport, store"),
    "gld_fs_model_country": ("Entity 2 · Model × Country at t", "ASOF SKU median price, promo, calendar, 28d pop"),
    "gld_candidates": ("Top-200 Candidates / Anchor", "5 sources: R1 > R3 > R2 > R4 > R5 in anchor_model_grid"),
    "gld_fs_pair": ("Entity 3 · Pair features (u, m, t)", "F2 rhythm, F4 basket lift, F5 price fit, dept ASOF"),
    "gld_ranking_dataset": ("Point-in-time ranking dataset", "Pair features + non-returned labels (Δ=30d, 90d)"),
    "candidate_recall": ("Audit · Candidate Recall@K", "Recall per source R1–R5 & combined pool@200"),
    "leakage_violations": ("QC-6 Point-in-Time Ledger", "Asserts max(source_ts) ≤ anchor_date (0 violations)"),
}


def strip_sql_comments(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.S)
    sql = re.sub(r"--[^\n]*", "", sql)
    return sql


PY_INPUTS = {
    "python.anchor_grid": ["silver.slv_fact_sales_line", "silver.slv_fact_returns", "silver.slv_member_profile", "python.split_windows"],
    "python.anchor_model_grid": ["python.anchor_grid", "silver.slv_fact_sales_line"],
    "python.split_windows": [],
}


def node_layer(uid: str) -> str:
    if uid.startswith("source."):
        if ".ext." in uid:
            return "ext"
        return "source"
    if uid.startswith("python."):
        return "python"
    path = man["nodes"][uid].get("original_file_path", "")
    for l in ("staging", "silver", "quarantine", "audit", "gold"):
        if f"/{l}/" in path or path.startswith(f"models/{l}/"):
            return l
    return "gold"


def node_label(uid: str) -> str:
    if uid.startswith("source."):
        return man["sources"][uid]["name"]
    if uid.startswith("python."):
        return uid.split(".", 1)[1]
    return man["nodes"][uid]["name"]


# Build canonical DAG from manifest.json + Python anchor-grid script dependencies
models = {uid: n for uid, n in man["nodes"].items() if n["resource_type"] == "model"}
sources_by_name = {v["name"]: k for k, v in man["sources"].items()}
models_by_name = {n["name"]: uid for uid, n in models.items()}

all_uids_by_name = {}
all_uids_by_name.update(sources_by_name)
all_uids_by_name.update(models_by_name)
for py_k in PY_INPUTS:
    all_uids_by_name[py_k.split(".", 1)[1]] = py_k

edges = set()
for uid, n in models.items():
    for dep in n["depends_on"].get("nodes", []):
        if dep in models or dep.startswith("source."):
            edges.add((dep, uid))
    clean_sql = strip_sql_comments(n.get("raw_code", ""))
    for t in ("anchor_grid", "anchor_model_grid", "split_windows"):
        if f"gold.{t}" in clean_sql:
            edges.add((f"python.{t}", uid))

for py, inputs in PY_INPUTS.items():
    for i in inputs:
        src = i if i.startswith("python.") else models_by_name.get(i.split(".", 1)[1])
        if src:
            edges.add((src, py))


# ── Drawing primitives ────────────────────────────────────────────────────────
def draw_rounded_box(ax, x, y, w, h, fill="#FFFFFF", border="#CBD5E1", lw=1.2, radius=0.12,
                     shadow=True, alpha=1.0, ls="-", zorder=2):
    if shadow:
        sh = FancyBboxPatch(
            (x + 0.035, y - 0.045), w, h,
            boxstyle=f"round,pad=0,rounding_size={radius}",
            facecolor="#0F172A", edgecolor="none", alpha=0.07, zorder=zorder - 0.5
        )
        ax.add_patch(sh)
    box = FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f"round,pad=0,rounding_size={radius}",
        facecolor=fill, edgecolor=border, linewidth=lw, linestyle=ls, alpha=alpha, zorder=zorder
    )
    ax.add_patch(box)
    return box


FIT_FLOOR = 0.62  # never shrink below this share of the requested size
FIT_FAILS = []


def fit_text(ax, x, y, s, maxw, **kw):
    """ax.text that shrinks its font until the rendered width is <= maxw (data units).

    Anything still too wide at FIT_FLOOR is recorded in FIT_FAILS so the caller can shorten the copy."""
    t = ax.text(x, y, s, **kw)
    fig = ax.figure
    rend = fig.canvas.get_renderer()
    inv = ax.transData.inverted()
    fs0 = t.get_fontsize()

    def width():
        bb = t.get_window_extent(rend)
        return inv.transform((bb.x1, 0))[0] - inv.transform((bb.x0, 0))[0]

    fs = fs0
    while width() > maxw and fs > fs0 * FIT_FLOOR:
        fs -= 0.1
        t.set_fontsize(fs)
    if width() > maxw + 1e-6:
        FIT_FAILS.append((ax.get_figure().get_label() or "fig", s, round(width() - maxw, 2)))
    return t


def draw_node_card(ax, cx, cy, w, h, name, kind, custom_badge=None, title_fs=9.6, sub_fs=7.8, zorder=4):
    """Draw a rich node card centered at (cx, cy) with accent bar, badge on the meta1 row, and zero text overlap."""
    pal = PALETTE[kind]
    x = cx - w / 2.0
    y = cy - h / 2.0
    radius = min(0.11, h * 0.18)

    draw_rounded_box(ax, x, y, w, h, fill=pal["fill"], border=pal["border"], lw=1.35, radius=radius, shadow=True, zorder=zorder)

    # Left accent bar
    accent_w = 0.085
    accent = FancyBboxPatch(
        (x + 0.015, y + 0.02), accent_w, h - 0.04,
        boxstyle=f"round,pad=0,rounding_size={radius * 0.7}",
        facecolor=pal["accent"], edgecolor="none", zorder=zorder + 0.2
    )
    ax.add_patch(accent)

    # Badge pill placed at top-right on the header row; card width (box_w >= 3.65) guarantees zero collision with titles
    badge_txt = custom_badge if custom_badge else pal["badge"]
    if name == "slv_sales_line_netted":
        badge_txt = "EPHEMERAL"
    elif name in ("gld_fs_member", "gld_fs_model_country", "gld_fs_pair"):
        badge_txt = "FEATURE ENTITY"

    bw = max(0.76, len(badge_txt) * 0.078 + 0.16)
    bh = 0.165
    bx = x + w - bw - 0.060
    by = y + h * (0.74 if h >= 0.90 else 0.75) - bh / 2.0
    badge_patch = FancyBboxPatch(
        (bx, by), bw, bh,
        boxstyle="round,pad=0,rounding_size=0.05",
        facecolor=pal["badge_bg"], edgecolor=pal["border"], linewidth=0.6, zorder=zorder + 0.3
    )
    ax.add_patch(badge_patch)
    ax.text(bx + bw / 2.0, by + bh / 2.0, badge_txt,
            ha="center", va="center", fontsize=4.8, fontweight="bold", color=pal["badge_fg"], zorder=zorder + 0.4)

    # Node name & subtitle lines (meta1 and meta2 have the full card width unobstructed)
    meta1, _ = NODE_META.get(name, ("", ""))
    meta2 = ""  # one subtitle line only: the second line made the cards dense
    tx = x + accent_w + 0.090
    if len(name) > 25:
        eff_title_fs = title_fs - 1.35
    elif len(name) > 21:
        eff_title_fs = title_fs - 0.90
    elif len(name) > 17:
        eff_title_fs = title_fs - 0.45
    else:
        eff_title_fs = title_fs

    tmax = bx - tx - 0.06
    mmax = x + w - tx - 0.08
    if meta1 and meta2:
        fit_text(ax, tx, y + h * (0.74 if h >= 0.90 else 0.75), name, tmax, ha="left", va="center",
                 fontsize=eff_title_fs, fontweight="bold", color=pal["title"], zorder=zorder + 0.5)
        fit_text(ax, tx, y + h * (0.43 if h >= 0.90 else 0.44), meta1, mmax, ha="left", va="center",
                 fontsize=sub_fs - 0.25, fontweight="bold", color=pal["accent"], zorder=zorder + 0.5)
        fit_text(ax, tx, y + h * (0.18 if h >= 0.90 else 0.17), meta2, mmax, ha="left", va="center",
                 fontsize=sub_fs - 0.85, color=pal["sub"], zorder=zorder + 0.5)
    elif meta1:
        fit_text(ax, tx, y + h * 0.68, name, tmax, ha="left", va="center",
                 fontsize=eff_title_fs, fontweight="bold", color=pal["title"], zorder=zorder + 0.5)
        fit_text(ax, tx, y + h * 0.26, meta1, mmax, ha="left", va="center",
                 fontsize=sub_fs, color=pal["sub"], zorder=zorder + 0.5)
    else:
        fit_text(ax, tx, cy, name, tmax, ha="left", va="center",
                 fontsize=eff_title_fs, fontweight="bold", color=pal["title"], zorder=zorder + 0.5)


def draw_arrowhead(ax, x_tip, y_tip, dx, dy, color, size=0.11, zorder=3.6):
    norm = np.hypot(dx, dy)
    if norm < 1e-6:
        ux, uy = 1.0, 0.0
    else:
        ux, uy = dx / norm, dy / norm
    px, py = -uy, ux
    bx = x_tip - ux * size
    by = y_tip - uy * size
    w = size * 0.48
    tri = Polygon(
        [(x_tip, y_tip), (bx + px * w, by + py * w), (bx - px * w, by - py * w)],
        closed=True, facecolor=color, edgecolor="none", zorder=zorder
    )
    ax.add_patch(tri)


def draw_routed_edge(ax, x1, y1, x2, y2, color="#64748B", style="-", lw=1.35, corridor_y=None, zorder=3.0):
    """Draw a smooth cubic Bézier edge (direct S-curve for adjacent columns, corridor-routed for multi-column spans)."""
    tip_trim = 0.09
    x2_body = x2 - tip_trim

    if corridor_y is None:
        dx = max(0.35, (x2_body - x1) * 0.46)
        verts = [(x1, y1), (x1 + dx, y1), (x2_body - dx, y2), (x2_body, y2)]
        codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
    else:
        span = x2_body - x1
        turn = min(0.85, max(0.42, span * 0.20))
        x_enter = x1 + turn
        x_leave = x2_body - turn
        if x_enter >= x_leave:
            dx = max(0.35, span * 0.45)
            verts = [(x1, y1), (x1 + dx, y1), (x2_body - dx, y2), (x2_body, y2)]
            codes = [Path.MOVETO, Path.CURVE4, Path.CURVE4, Path.CURVE4]
        else:
            c1 = turn * 0.52
            verts = [
                (x1, y1),
                (x1 + c1, y1),
                (x_enter - c1, corridor_y),
                (x_enter, corridor_y),
                (x_leave, corridor_y),
                (x_leave + c1, corridor_y),
                (x2_body - c1, y2),
                (x2_body, y2),
            ]
            codes = [
                Path.MOVETO,
                Path.CURVE4, Path.CURVE4, Path.CURVE4,
                Path.LINETO,
                Path.CURVE4, Path.CURVE4, Path.CURVE4,
            ]

    path = Path(verts, codes)
    # White halo under-stroke so crossings remain crisp and readable
    halo = PathPatch(path, facecolor="none", edgecolor="#FFFFFF", linewidth=lw + 1.8,
                     capstyle="round", joinstyle="round", alpha=0.88, zorder=zorder - 0.1)
    ax.add_patch(halo)

    patch = PathPatch(path, facecolor="none", edgecolor=color, linewidth=lw, linestyle=style,
                      capstyle="round", joinstyle="round", alpha=0.88, zorder=zorder)
    ax.add_patch(patch)

    # Small port dot at exit
    dot = Circle((x1, y1), radius=0.028, facecolor=color, edgecolor="#FFFFFF", linewidth=0.5, zorder=zorder + 0.2)
    ax.add_patch(dot)

    draw_arrowhead(ax, x2, y2, 1.0, 0.0, color, size=0.115, zorder=zorder + 0.3)


def draw_legend_bar(ax, x, y, w, h, kinds, include_edge_types=True):
    """Draw a clean 2-row horizontal legend bar with generous spacing."""
    draw_rounded_box(ax, x, y, w, h, fill="#F8FAFC", border="#CBD5E1", lw=1.0, radius=0.10, shadow=False, zorder=1.5)
    ax.text(x + 0.20, y + h / 2.0, "LEGEND:", ha="left", va="center", fontsize=8.4, fontweight="bold", color="#0F172A", zorder=3)

    items = [(k, PALETTE[k]["legend"]) for k in kinds if k in PALETTE]
    total_slots = len(items) + (2 if include_edge_types else 0)
    row1_cnt = (total_slots + 1) // 2
    row2_cnt = total_slots - row1_cnt

    usable_w = w - 1.85
    step1 = usable_w / max(1, row1_cnt)
    step2 = usable_w / max(1, row2_cnt)
    y_row1 = y + h * 0.68
    y_row2 = y + h * 0.30

    all_entries = [("node", k, lbl) for k, lbl in items]
    if include_edge_types:
        all_entries.append(("edge_solid", None, "Primary data dependency (AS-OF / join / view)"))
        all_entries.append(("edge_dash", None, "Quarantine / QC-6 point-in-time audit route"))

    for idx, (etype, k, label_txt) in enumerate(all_entries):
        if idx < row1_cnt:
            cur_x = x + 1.65 + idx * step1
            cy = y_row1
        else:
            cur_x = x + 1.65 + (idx - row1_cnt) * step2
            cy = y_row2

        if etype == "node":
            pal = PALETTE[k]
            sw_w, sw_h = 0.28, 0.19
            sw_y = cy - sw_h / 2.0
            draw_rounded_box(ax, cur_x, sw_y, sw_w, sw_h, fill=pal["fill"], border=pal["border"], lw=1.1, radius=0.04, shadow=False, zorder=3)
            acc = FancyBboxPatch((cur_x + 0.01, sw_y + 0.02), 0.05, sw_h - 0.04,
                                 boxstyle="round,pad=0,rounding_size=0.02", facecolor=pal["accent"], edgecolor="none", zorder=3.2)
            ax.add_patch(acc)
            ax.text(cur_x + sw_w + 0.08, cy, label_txt, ha="left", va="center", fontsize=7.5, color="#1E293B", zorder=3)
        elif etype == "edge_solid":
            ax.plot([cur_x, cur_x + 0.34], [cy, cy], color="#2563EB", lw=1.8, zorder=3)
            draw_arrowhead(ax, cur_x + 0.38, cy, 1.0, 0.0, "#2563EB", size=0.10, zorder=3.2)
            ax.text(cur_x + 0.46, cy, label_txt, ha="left", va="center", fontsize=7.5, color="#1E293B", zorder=3)
        elif etype == "edge_dash":
            ax.plot([cur_x, cur_x + 0.34], [cy, cy], color="#E11D48", lw=1.6, ls="--", zorder=3)
            draw_arrowhead(ax, cur_x + 0.38, cy, 1.0, 0.0, "#E11D48", size=0.10, zorder=3.2)
            ax.text(cur_x + 0.46, cy, label_txt, ha="left", va="center", fontsize=7.5, color="#1E293B", zorder=3)


def render_dag_figure(
    filename: str,
    title: str,
    subtitle: str,
    col_defs: list,
    swimlanes: list,
    node_positions: dict,
    kept_edges: list,
    corridor_ys: list,
    legend_kinds: list,
    box_w: float = 4.10,
    box_h: float = 0.80,
    col_pitch: float = 5.15,
    fig_scale: float = 0.78,
):
    """Render a structured DAG figure with stage columns, domain swimlanes, node cards, and obstacle-aware edges."""
    n_cols = len(col_defs)
    all_ys = [pos[1] for pos in node_positions.values()]
    min_y = min(all_ys) - 0.80
    max_y = max(all_ys) + 0.80

    left_pad = 2.65 if swimlanes else 0.45
    right_pad = 0.55
    x_min = -left_pad - box_w / 2.0
    x_max = (n_cols - 1) * col_pitch + box_w / 2.0 + right_pad

    header_top = max_y + 1.40
    footer_bot = min_y - 1.05

    width_units = x_max - x_min
    height_units = header_top - footer_bot

    fig, ax = plt.subplots(figsize=(width_units * fig_scale, height_units * fig_scale))
    ax.set_xlim(x_min, x_max)
    ax.set_ylim(footer_bot, header_top)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    # Title banner at top
    ax.text(x_min + 0.1, header_top - 0.28, title, ha="left", va="center",
            fontsize=14.8, fontweight="bold", color="#0F172A")
    ax.text(x_min + 0.1, header_top - 0.60, subtitle, ha="left", va="center",
            fontsize=9.3, color="#475569")

    # Draw horizontal domain swimlanes if provided
    for sl_title, sl_sub, y_lo, y_hi, sl_bg, sl_border, sl_fg in swimlanes:
        sl_x = x_min + 0.05
        sl_w = x_max - sl_x - 0.10
        draw_rounded_box(ax, sl_x, y_lo, sl_w, y_hi - y_lo, fill=sl_bg, border=sl_border,
                         lw=0.9, radius=0.14, shadow=False, alpha=0.55, zorder=0.5)
        lbl_w = left_pad - 0.35
        draw_rounded_box(ax, sl_x + 0.10, y_lo + 0.12, lbl_w, (y_hi - y_lo) - 0.24,
                         fill="#FFFFFF", border=sl_border, lw=1.1, radius=0.10, shadow=False, alpha=0.96, zorder=1.2)
        ym = (y_lo + y_hi) / 2.0
        fit_text(ax, sl_x + 0.10 + lbl_w / 2.0, ym + 0.26, sl_title, lbl_w - 0.2, ha="center", va="center",
                fontsize=8.0, fontweight="bold", color=sl_fg, zorder=1.5)
        fit_text(ax, sl_x + 0.10 + lbl_w / 2.0, ym - 0.26, sl_sub, lbl_w - 0.2, ha="center", va="center",
                fontsize=6.6, color="#475569", zorder=1.5)

    # Draw Stage Column headers & subtle vertical guides
    col_top = max_y + 0.55
    col_bot = min_y - 0.10
    for c_idx, (c_title, c_sub, c_color, c_bg) in enumerate(col_defs):
        cx = c_idx * col_pitch
        cw = box_w + 0.26
        draw_rounded_box(ax, cx - cw / 2.0, col_bot, cw, col_top - col_bot - 0.46,
                         fill="#F8FAFC" if not swimlanes else "#FFFFFF",
                         border="#CBD5E1", lw=0.75, radius=0.12, shadow=False,
                         alpha=0.55 if not swimlanes else 0.30, ls="--", zorder=0.8)
        hdr_h = 0.48
        hdr_y = col_top - hdr_h
        draw_rounded_box(ax, cx - cw / 2.0, hdr_y, cw, hdr_h,
                         fill=c_bg, border=c_color, lw=1.25, radius=0.09, shadow=False, zorder=2.0)
        fit_text(ax, cx, hdr_y + hdr_h * 0.65, c_title, cw - 0.2, ha="center", va="center",
                fontsize=8.4, fontweight="bold", color=c_color, zorder=2.5)
        fit_text(ax, cx, hdr_y + hdr_h * 0.24, c_sub, cw - 0.2, ha="center", va="center",
                fontsize=6.8, color="#334155", zorder=2.5)

    # Compute node coordinates and draw node cards
    coords = {}
    kinds = {}
    cols_to_ys = {i: [] for i in range(n_cols)}
    for name, (c_idx, y_val) in node_positions.items():
        uid = all_uids_by_name[name]
        k = node_layer(uid)
        cx = c_idx * col_pitch
        coords[name] = (cx, y_val, c_idx)
        kinds[name] = k
        cols_to_ys[c_idx].append(y_val)
        draw_node_card(ax, cx, y_val, box_w, box_h, name, k, zorder=4.0)

    # Filter out long-span clutter to `leakage_violations` (keep adjacent Gold entity/pair audit edges;
    # the card's subtitle already states that QC-6 audits all 8 Silver & Gold tables ≤ anchor_date)
    filtered_edges = []
    for a, b in kept_edges:
        if a in node_positions and b in node_positions:
            if b == "leakage_violations" and (coords[b][2] - coords[a][2]) > 2:
                continue
            filtered_edges.append((a, b))

    # Compute distributed exit and entry ports per node so lines never stack at a single point
    out_edges = {n: [] for n in node_positions}
    in_edges = {n: [] for n in node_positions}
    for a, b in filtered_edges:
        out_edges[a].append(b)
        in_edges[b].append(a)

    out_port_y = {}
    in_port_y = {}
    max_port_spread = box_h * 0.64

    for n, targets in out_edges.items():
        if not targets:
            continue
        _, ny, _ = coords[n]
        targets_sorted = sorted(targets, key=lambda t: (coords[t][1], coords[t][2]))
        m = len(targets_sorted)
        for i, t in enumerate(targets_sorted):
            offset = 0.0 if m == 1 else ((i / (m - 1)) - 0.5) * min(max_port_spread, m * 0.095)
            out_port_y[(n, t)] = ny + offset

    for n, sources in in_edges.items():
        if not sources:
            continue
        _, ny, _ = coords[n]
        sources_sorted = sorted(sources, key=lambda s: (coords[s][1], -coords[s][2]))
        m = len(sources_sorted)
        for i, s in enumerate(sources_sorted):
            offset = 0.0 if m == 1 else ((i / (m - 1)) - 0.5) * min(max_port_spread, m * 0.095)
            in_port_y[(s, n)] = ny + offset

    # Obstacle-aware corridor routing: only use a horizontal bypass corridor when an intermediate column's
    # node card actually blocks the direct line of sight between (x1, y1) and (x2, y2).
    corridor_usage = {cy: 0 for cy in corridor_ys}

    sorted_edges = sorted(
        filtered_edges,
        key=lambda ab: -(coords[ab[1]][2] - coords[ab[0]][2])
    )

    for a, b in sorted_edges:
        ax_x, ay_y, c1 = coords[a]
        bx_x, by_y, c2 = coords[b]
        x1 = ax_x + box_w / 2.0
        x2 = bx_x - box_w / 2.0
        y1 = out_port_y[(a, b)]
        y2 = in_port_y[(a, b)]

        ka, kb = kinds[a], kinds[b]
        is_qc = kb in ("quarantine", "audit")
        edge_col = PALETTE[kb]["edge"] if is_qc else PALETTE[ka]["edge"]
        style = "--" if is_qc else "-"
        lw = 1.25 if (c2 - c1) > 1 else 1.45

        corridor = None
        if c2 > c1 + 1 and corridor_ys:
            # Check if any node in columns (c1+1 .. c2-1) blocks the direct segment from (x1, y1) to (x2, y2)
            blocked = False
            for mid_c in range(c1 + 1, c2):
                mid_x = mid_c * col_pitch
                t_frac = (mid_x - x1) / max(1e-6, (x2 - x1))
                line_y = y1 + t_frac * (y2 - y1)
                for ny in cols_to_ys[mid_c]:
                    if abs(line_y - ny) < (box_h / 2.0 + 0.14):
                        blocked = True
                        break
                if blocked:
                    break

            if blocked:
                # Choose a corridor that is obstacle-free across all intermediate columns (c1+1 .. c2-1)
                safe_corridors = [
                    cy for cy in corridor_ys
                    if all(abs(cy - ny) >= (box_h / 2.0 + 0.10) for mid_c in range(c1 + 1, c2) for ny in cols_to_ys[mid_c])
                ]
                candidates = safe_corridors if safe_corridors else corridor_ys
                mid_y = 0.5 * (y1 + y2)
                best_c = min(candidates, key=lambda cy: abs(cy - mid_y) + 0.20 * abs(cy - y1) + 0.20 * abs(cy - y2))
                idx = corridor_usage[best_c]
                corridor_usage[best_c] += 1
                track_shift = ((idx + 1) // 2) * (0.042 if idx % 2 == 1 else -0.042)
                corridor = best_c + track_shift

        draw_routed_edge(ax, x1, y1, x2, y2, color=edge_col, style=style, lw=lw,
                         corridor_y=corridor, zorder=2.8 if (c2 - c1) > 1 else 3.3)

    # Bottom 2-Row Legend Bar
    leg_h = 0.68
    draw_legend_bar(ax, x_min + 0.05, footer_bot + 0.12, x_max - x_min - 0.10, leg_h, legend_kinds)

    for fmt in ("svg", "png"):
        out_path = OUT / f"{filename}.{fmt}"
        fig.savefig(out_path, dpi=260 if fmt == "png" else None, bbox_inches="tight", pad_inches=0.22, facecolor="#FFFFFF")
    plt.close(fig)
    for f in FIT_FAILS:
        print("  overflow:", f)
    FIT_FAILS.clear()
    print(f"→ docs/figures/{filename}.svg / .png  ({len(node_positions)} nodes, {len(sorted_edges)} edges, {n_cols} stages)")


# ══════════════════════════════════════════════════════════════════════════════
# 1. BRONZE → SILVER LINEAGE (5 Domain Swimlanes × 5 Stage Columns)
# ══════════════════════════════════════════════════════════════════════════════
def build_lineage_bronze_to_silver():
    col_defs = [
        ("STAGE 1 · BRONZE & EXT SOURCES", "10 Parquet/CSV views + 2 ext tables", "#334155", "#F1F5F9"),
        ("STAGE 2 · STAGING & BASE SILVER", "Projection pushdown & base dimensions", "#15803D", "#DCFCE7"),
        ("STAGE 3 · CORE TRANSFORMATIONS", "Dedup, netting, intervals & parsing", "#1D4ED8", "#DBEAFE"),
        ("STAGE 4 · INTEGRATED SILVER & QC", "Validated facts, links & quarantine", "#1D4ED8", "#DBEAFE"),
        ("STAGE 5 · DERIVED STATE & AUDIT", "As-of store, 1:1 identity & coverage", "#B45309", "#FEF3C7"),
    ]

    swimlanes = [
        ("1. PRICING &\nCALENDAR", "SKU intervals & inferred\npromo events (diff-array)", 9.05, 13.55, "#F8FAFC", "#CBD5E1", "#1E293B"),
        ("2. CATALOGUE &\nDAILY STOCK", "SKU → model roll-up &\nsite/national stock grid", 6.75, 8.85, "#F0FDF4", "#BBF7D0", "#14532D"),
        ("3. POS & ONLINE\nTRANSACTIONS", "Dedup, sale−cancel netting,\nUTC tz & EUR facts", 3.35, 6.55, "#EFF6FF", "#BFDBFE", "#1E3A8A"),
        ("4. WEB CLICKSTREAM\n& STITCHING", "1.0B events STRUCT/LIST &\n2-tier ORDER/LOGIN links", 0.15, 3.15, "#FAF5FF", "#E9D5FF", "#581C87"),
        ("5. LOYALTY MEMBER\n& SPORT STATE", "Consumer exclusion & ASOF\nsport validity intervals", -2.25, -0.05, "#FFFBEB", "#FDE68A", "#78350F"),
    ]

    pos = {
        # Swimlane 1: Pricing & Calendar (y: 9.5 .. 12.9)
        "all_store_selling_price": (0, 12.85),
        "dim_calendar":            (0, 11.75),
        "public_holidays":         (0, 10.65),
        "commercial_event_names":  (0, 9.55),
        "qrt_price_interval":      (1, 12.85),
        "slv_price_sku_interval":  (1, 11.75),
        "slv_calendar_enriched":   (2, 10.65),

        # Swimlane 2: Catalogue & Stock (y: 7.2 .. 8.3)
        "stock_availability_rate":  (0, 8.30),
        "dim_item":                 (0, 7.25),
        "slv_dim_model":            (1, 7.25),
        "slv_stock_daily_model":    (2, 8.30),
        "slv_stock_daily_national": (3, 8.30),

        # Swimlane 3: POS & Online Transactions (y: 3.8 .. 6.0)
        "dim_business_unit":       (0, 6.00),
        "sales_detail":            (0, 4.90),
        "f_member_purchase":       (0, 3.80),
        "stg_sales_detail":        (1, 4.90),
        "slv_member_bridge":       (1, 3.80),
        "slv_sales_line_netted":   (2, 5.45),
        "slv_fact_returns":        (2, 4.25),
        "qrt_sales_line":          (3, 6.00),
        "slv_fact_sales_line":     (3, 4.90),
        "slv_member_store_daily":  (4, 4.90),

        # Swimlane 4: Web Clickstream & Identity Stitching (y: 0.6 .. 2.7)
        "tracking_ecom_events":     (0, 1.65),
        "stg_tracking_ecom_events": (1, 1.65),
        "slv_web_events_clean":     (2, 1.65),
        "slv_user_member_links":    (3, 1.65),
        "stitching_coverage":       (4, 2.65),
        "slv_user_to_member":       (4, 1.65),
        "slv_identity_conflicts":   (4, 0.65),

        # Swimlane 5: Loyalty Member & Sport State (y: -1.8 .. -0.5)
        "d_member":                 (0, -0.60),
        "f_member_favorite_sport":  (0, -1.70),
        "slv_member_profile":       (1, -0.60),
        "slv_member_sport_asof":    (1, -1.70),
    }

    corridors = [12.30, 11.20, 10.10, 8.95, 7.78, 6.65, 5.45, 4.35, 3.25, 2.15, 1.15, 0.05, -1.15]
    kept = [(node_label(a), node_label(b)) for a, b in edges if node_label(a) in pos and node_label(b) in pos]

    render_dag_figure(
        filename="lineage_bronze_to_silver",
        title="Bronze → Silver Data Lineage & Quality Quarantine Architecture",
        subtitle="12 Bronze/ext inputs → 2 Staging views → 15 Silver models, 3 Quarantine tables & 1 Audit table across 5 functional domains (dbt-duckdb)",
        col_defs=col_defs,
        swimlanes=swimlanes,
        node_positions=pos,
        kept_edges=kept,
        corridor_ys=corridors,
        legend_kinds=["source", "ext", "staging", "silver", "quarantine", "audit"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 2. SILVER → GOLD LINEAGE (6 Stage Columns × Domain Swimlanes)
# ══════════════════════════════════════════════════════════════════════════════
def build_lineage_silver_to_gold():
    col_defs = [
        ("STAGE 1 · SILVER INPUTS", "Cleaned & harmonised Silver tables", "#1D4ED8", "#DBEAFE"),
        ("STAGE 2 · ANCHOR GRID & GOLD AUX", "Python temporal grid & pre-cutoff stats", "#3730A3", "#E0E7FF"),
        ("STAGE 3 · ENTITY FEATURE STORES", "Point-in-time Member & Model×Country", "#A16207", "#FEF9C3"),
        ("STAGE 4 · CANDIDATE ENGINE", "5-source retrieval pool (R1–R5, top 200)", "#A16207", "#FEF9C3"),
        ("STAGE 5 · PAIR FEATURES & RANKING", "Entity 3 interactions & Δ=30/90 labels", "#A16207", "#FEF9C3"),
        ("STAGE 6 · GOLD AUDIT & QC-6", "Recall@K & Point-in-Time leakage ledger", "#BE123C", "#FFE4E6"),
    ]

    swimlanes = [
        ("1. CALENDAR, PRICE\n& CATALOGUE", "Entity 2 inputs: ASOF SKU price,\npromo, holidays & model dim", 6.55, 9.85, "#F8FAFC", "#CBD5E1", "#1E293B"),
        ("2. TRANSACTIONS &\nTEMPORAL GRID", "Weekly Mondays (anchor_grid),\nbasket lift & purchasable models", 2.75, 6.35, "#EFF6FF", "#BFDBFE", "#1E3A8A"),
        ("3. MEMBER STATE &\nSPORT AFFINITY", "Entity 1 inputs: profile, usual store,\nsport intervals & dept affinity", -0.85, 2.55, "#FFFBEB", "#FDE68A", "#78350F"),
        ("4. WEB ATTRIBUTION\n& INTENT", "Stitched web events (±90d,\nverified_ts ≤ anchor_date)", -3.35, -1.05, "#FAF5FF", "#E9D5FF", "#581C87"),
    ]

    pos = {
        # Stage 1: Silver Inputs (Col 0)
        "slv_price_sku_interval":  (0, 9.30),
        "slv_calendar_enriched":   (0, 8.20),
        "slv_dim_model":           (0, 7.10),
        "slv_fact_sales_line":     (0, 5.55),
        "slv_fact_returns":        (0, 4.35),
        "slv_member_profile":      (0, 1.95),
        "slv_member_store_daily":  (0, 0.85),
        "slv_member_sport_asof":   (0, -0.25),
        "slv_web_events_clean":    (0, -1.65),
        "slv_user_to_member":      (0, -2.75),

        # Stage 2: Python Anchor Grid & Gold Auxiliaries (Col 1)
        "anchor_model_grid":             (1, 7.65),
        "gld_copurchase_lift":           (1, 5.75),
        "anchor_grid":                   (1, 4.55),
        "split_windows":                 (1, 3.35),
        "gld_sport_department_affinity": (1, 0.30),
        "gld_web_stitched":              (1, -2.20),

        # Stage 3: Entity 1 & Entity 2 Feature Stores (Col 2)
        "gld_fs_model_country":          (2, 7.65),
        "gld_fs_member":                 (2, 1.40),

        # Stage 4: Candidate Generation R1–R5 (Col 3)
        "gld_candidates":                (3, 4.55),

        # Stage 5: Pair Feature Store & Ranking Dataset (Col 4)
        "gld_fs_pair":                   (4, 5.20),
        "gld_ranking_dataset":           (4, 3.50),

        # Stage 6: Gold Quality & Recall Audit (Col 5)
        "leakage_violations":            (5, 5.20),
        "candidate_recall":              (5, 3.50),
    }

    corridors = [8.75, 7.65, 6.45, 5.05, 3.90, 2.65, 1.40, 0.30, -0.95, -2.20]
    kept = [(node_label(a), node_label(b)) for a, b in edges if node_label(a) in pos and node_label(b) in pos]

    render_dag_figure(
        filename="lineage_silver_to_gold",
        title="Silver → Gold Point-in-Time Feature Store, Candidate Engine & QC-6 Lineage",
        subtitle="10 Silver inputs → 3 Python Anchor Grid tables → 3 Feature Entities (Member, Model×Country, Pair), R1–R5 Candidates, Ranking Dataset & QC-6 Ledger",
        col_defs=col_defs,
        swimlanes=swimlanes,
        node_positions=pos,
        kept_edges=kept,
        corridor_ys=corridors,
        legend_kinds=["silver", "python", "gold", "quarantine", "audit"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 3. FULL END-TO-END LINEAGE DAG (All 46 Nodes across 7 Stage Columns)
# ══════════════════════════════════════════════════════════════════════════════
def build_lineage_full():
    col_defs = [
        ("1 · BRONZE SOURCES", "10 Parquet/CSV + 2 ext", "#334155", "#F1F5F9"),
        ("2 · STAGING & BASE", "Views & base Silver dims", "#15803D", "#DCFCE7"),
        ("3 · SILVER CORE", "Dedup, net, intervals, web", "#1D4ED8", "#DBEAFE"),
        ("4 · SILVER FACTS & QC", "Sales fact, links, quarantine", "#1D4ED8", "#DBEAFE"),
        ("5 · GRID & GOLD AUX", "Anchor grid, lift & stitched", "#3730A3", "#E0E7FF"),
        ("6 · ENTITIES & CANDS", "fs_member, fs_model & R1–R5", "#A16207", "#FEF9C3"),
        ("7 · PAIRS, RANK & QC-6", "fs_pair, labels & leakage", "#BE123C", "#FFE4E6"),
    ]

    swimlanes = [
        ("1. PRICING &\nCALENDAR", "SKU price intervals,\nholidays & promo events", 8.15, 12.65, "#F8FAFC", "#CBD5E1", "#1E293B"),
        ("2. CATALOGUE &\nDAILY STOCK", "Model roll-up & daily\nsite/national stock", 5.85, 7.95, "#F0FDF4", "#BBF7D0", "#14532D"),
        ("3. TRANSACTIONS &\nCANDIDATE POOL", "Sales/returns, anchor grid,\nR1–R5 & ranking labels", 1.95, 5.65, "#EFF6FF", "#BFDBFE", "#1E3A8A"),
        ("4. LOYALTY MEMBER\n& SPORT STATE", "Profile, usual store, sport\nintervals & Entity 1", -1.65, 1.75, "#FFFBEB", "#FDE68A", "#78350F"),
        ("5. WEB CLICKSTREAM\n& STITCHING", "1.0B events, 2-tier identity\nstitching & coverage", -4.45, -1.85, "#FAF5FF", "#E9D5FF", "#581C87"),
    ]

    pos = {
        # Col 0: Bronze & Ext Sources
        "all_store_selling_price": (0, 11.95),
        "dim_calendar":            (0, 10.85),
        "public_holidays":         (0, 9.75),
        "commercial_event_names":  (0, 8.65),
        "stock_availability_rate": (0, 7.40),
        "dim_item":                (0, 6.35),
        "dim_business_unit":       (0, 5.05),
        "sales_detail":            (0, 3.90),
        "f_member_purchase":       (0, 2.65),
        "d_member":                (0, 0.95),
        "f_member_favorite_sport": (0, -0.35),
        "tracking_ecom_events":    (0, -3.15),

        # Col 1: Staging & Base Silver
        "qrt_price_interval":       (1, 11.95),
        "slv_price_sku_interval":   (1, 10.50),
        "slv_dim_model":            (1, 6.35),
        "stg_sales_detail":         (1, 3.90),
        "slv_member_bridge":        (1, 2.65),
        "slv_member_profile":       (1, 0.95),
        "slv_member_sport_asof":    (1, -0.35),
        "stg_tracking_ecom_events": (1, -3.15),

        # Col 2: Silver Core
        "slv_calendar_enriched":    (2, 9.75),
        "slv_stock_daily_model":    (2, 7.40),
        "slv_sales_line_netted":    (2, 4.55),
        "slv_fact_returns":         (2, 3.20),
        "slv_web_events_clean":     (2, -3.15),

        # Col 3: Silver Facts, Quarantine & Identity Links
        "slv_stock_daily_national": (3, 7.40),
        "qrt_sales_line":           (3, 5.10),
        "slv_fact_sales_line":      (3, 3.90),
        "slv_user_member_links":    (3, -2.55),
        "slv_identity_conflicts":   (3, -3.85),

        # Col 4: Python Anchor Grid, Silver State & Gold Aux
        "anchor_model_grid":             (4, 6.60),
        "gld_copurchase_lift":           (4, 5.10),
        "anchor_grid":                   (4, 3.90),
        "split_windows":                 (4, 2.65),
        "slv_member_store_daily":        (4, 1.15),
        "gld_sport_department_affinity": (4, -0.35),
        "slv_user_to_member":            (4, -2.55),
        "stitching_coverage":            (4, -3.85),

        # Col 5: Gold Feature Entities (Entity 1, Entity 2), Stitched Web & Candidates
        "gld_fs_model_country":          (5, 9.20),
        "gld_candidates":                (5, 4.30),
        "gld_fs_member":                 (5, 0.65),
        "gld_web_stitched":              (5, -2.55),

        # Col 6: Pair Features (Entity 3), Ranking Dataset & Gold QC-6 / Recall
        "leakage_violations":            (6, 7.10),
        "gld_fs_pair":                   (6, 5.05),
        "gld_ranking_dataset":           (6, 3.65),
        "candidate_recall":              (6, 2.25),
    }

    corridors = [11.40, 10.15, 8.05, 6.90, 5.75, 4.50, 3.30, 1.85, 0.30, -1.10, -1.75, -3.20]
    kept = [(node_label(a), node_label(b)) for a, b in edges if node_label(a) in pos and node_label(b) in pos]

    render_dag_figure(
        filename="lineage_full",
        title="End-to-End Multi-Dimensional Retail Lakehouse Lineage (Bronze → Silver → Gold)",
        subtitle="Complete 46-node dependency graph across 7 execution stages and 5 functional domains (DuckDB 2.0 · Parquet · dbt 1.12 · Python Anchor Grid)",
        col_defs=col_defs,
        swimlanes=swimlanes,
        node_positions=pos,
        kept_edges=kept,
        corridor_ys=corridors,
        legend_kinds=["source", "ext", "staging", "silver", "python", "gold", "quarantine", "audit"],
    )


# ══════════════════════════════════════════════════════════════════════════════
# 4. SYNTHESIS DIAGRAM — HIGH-LEVEL / GENERALIZED ARCHITECTURE OVERVIEW
#    (docs/figures/architecture_overview.{svg,png})
# ══════════════════════════════════════════════════════════════════════════════
# ── Architecture views (block diagrams: short labels, numbered stages, dashed lakehouse boundary) ──────────────
LAYER = {
    "src":    {"main": "#475569", "tint": "#F1F5F9", "edge": "#CBD5E1"},
    "bronze": {"main": "#B45309", "tint": "#FFF7ED", "edge": "#FDBA74"},
    "silver": {"main": "#2563EB", "tint": "#EFF6FF", "edge": "#93C5FD"},
    "gold":   {"main": "#A16207", "tint": "#FEFCE8", "edge": "#FDE047"},
    "eval":   {"main": "#0F766E", "tint": "#F0FDFA", "edge": "#5EEAD4"},
    "qc":     {"main": "#BE123C", "tint": "#FFF1F2", "edge": "#FDA4AF"},
}


def _flow_arrow(ax, x1, y1, x2, y2, color="#334155", lw=2.4):
    ax.annotate("", xy=(x2, y2), xytext=(x1, y1), zorder=6,
                arrowprops=dict(arrowstyle="-|>", color=color, lw=lw, shrinkA=0, shrinkB=0, mutation_scale=18))


def _number_dot(ax, x, y, label, color, r=0.21, fs=11):
    ax.add_patch(Circle((x, y), r, facecolor="#FFFFFF", edgecolor="none", zorder=4.0))
    ax.text(x, y, label, ha="center", va="center", fontsize=fs, fontweight="bold", color=color, zorder=4.2)


def _tag(ax, x_right, y_mid, text, color, fs=7.8):
    tw = len(text) * 0.085 + 0.26
    ax.add_patch(FancyBboxPatch((x_right - tw, y_mid - 0.14), tw, 0.28, boxstyle="round,pad=0,rounding_size=0.08",
                                facecolor=color, edgecolor="none", alpha=0.14, zorder=4.2))
    ax.text(x_right - tw / 2.0, y_mid, text, ha="center", va="center", fontsize=fs, fontweight="bold", color=color, zorder=4.4)
    return tw


def _title_block(ax, x, y_title, title, subtitle, t_fs=21, s_fs=12):
    ax.text(x, y_title, title, ha="left", va="center", fontsize=t_fs, fontweight="bold", color="#0F172A")
    ax.text(x, y_title - 0.50, subtitle, ha="left", va="center", fontsize=s_fs, color="#475569")


def _save(fig, name):
    for fmt in ("svg", "png"):
        fig.savefig(OUT / f"{name}.{fmt}", dpi=240 if fmt == "png" else None, bbox_inches="tight", pad_inches=0.25, facecolor="#FFFFFF")
    plt.close(fig)
    for f in FIT_FAILS:
        print("  overflow:", f)
    FIT_FAILS.clear()


def _simple_card(ax, x, y, w, h, title, sub, col):
    draw_rounded_box(ax, x, y, w, h, fill="#FFFFFF", border=col["main"], lw=1.5, radius=0.12, shadow=True, zorder=3.0)
    ax.add_patch(FancyBboxPatch((x + 0.03, y + 0.05), 0.11, h - 0.10, boxstyle="round,pad=0,rounding_size=0.05",
                                facecolor=col["main"], edgecolor="none", zorder=3.2))
    fit_text(ax, x + 0.30, y + h * 0.64, title, w - 0.45, ha="left", va="center", fontsize=12.5, fontweight="bold", color="#0F172A", zorder=3.5)
    fit_text(ax, x + 0.30, y + h * 0.30, sub, w - 0.45, ha="left", va="center", fontsize=10, color="#475569", zorder=3.5)


def build_architecture_overview():
    W, H = 20.0, 11.4
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    _title_block(ax, 0.40, 10.85, "Architecture Overview — Multi-Signal Retail Recommendation Pipeline",
                 "Raw files → Bronze → Silver → Gold → fixed LambdaRank evaluation, with quality gates throughout")

    top, bot = 9.55, 2.95
    cols = [
        ("1", "Data sources", "11 tables · ~230 GB", "src", 0.40, 3.10, [
            ("Retail exports", "POS · catalogue · members"),
            ("Web clickstream", "1.0 B events"),
            ("Stream lane", "optional Redpanda replay"),
            ("External data", "holidays · event names"),
        ]),
        ("2", "Bronze", "raw, partitioned", "bronze", 4.62, 3.10, [
            ("Contract loader", "typed keys · schema checks"),
            ("Partitioned Parquet", "ZSTD · country / year / month"),
            ("Quarantine", "rejects · dead letters"),
            ("Go / No-Go gates", "per country × year"),
        ]),
        ("3", "Silver", "clean & harmonised", "silver", 8.22, 3.10, [
            ("Sales & returns", "dedup · netting · EUR"),
            ("Catalogue & prices", "SKU → model · intervals"),
            ("Web & identity", "cookie → member"),
            ("Calendar & members", "promo peaks · sport state"),
        ]),
        ("4", "Gold", "point-in-time features", "gold", 11.82, 3.10, [
            ("Anchor grid", "weekly · purge gaps"),
            ("Feature entities", "member · model · pair"),
            ("Candidates R1–R5", "top 200 per anchor"),
            ("Ranking dataset", "labels at 30 d and 90 d"),
        ]),
        ("5", "Evaluation", "frozen model, two axes", "eval", 16.05, 3.55, [
            ("LambdaRank", "hyper-parameters fixed"),
            ("Ablation", "features × candidates"),
            ("Bootstrap CI", "500× member-level"),
            ("Cost × gain", "wall time · memory"),
        ]),
    ]
    # dashed lakehouse boundary around Bronze, Silver, Gold
    ax.add_patch(FancyBboxPatch((4.40, bot - 0.15), 10.70, top - bot + 0.30, boxstyle="round,pad=0,rounding_size=0.2",
                                facecolor="none", edgecolor="#DC2626", linewidth=1.6, linestyle=(0, (6, 4)), zorder=0.6))
    ax.text(4.62, top + 0.38, "LAKEHOUSE · DuckDB + ZSTD Parquet", ha="left", va="center", fontsize=10.5,
            fontweight="bold", color="#DC2626", zorder=1)

    gap = 0.24
    card_h = (top - bot - 0.95 - 0.25 - 0.20 - 3 * gap) / 4.0
    for num, name, sub, key, x, w, cards in cols:
        c = LAYER[key]
        draw_rounded_box(ax, x, bot, w, top - bot, fill=c["tint"], border=c["edge"], lw=1.4, radius=0.18, shadow=False, zorder=1.0)
        draw_rounded_box(ax, x, top - 0.95, w, 0.95, fill=c["main"], border=c["main"], lw=1.0, radius=0.16, shadow=False, zorder=2.0)
        _number_dot(ax, x + 0.42, top - 0.475, num, c["main"])
        fit_text(ax, x + 0.78, top - 0.34, name, w - 0.95, ha="left", va="center", fontsize=16, fontweight="bold", color="#FFFFFF", zorder=2.5)
        fit_text(ax, x + 0.78, top - 0.69, sub, w - 0.95, ha="left", va="center", fontsize=10.5, color="#F1F5F9", zorder=2.5)
        cy = top - 0.95 - 0.25 - card_h
        for t, s in cards:
            _simple_card(ax, x + 0.20, cy, w - 0.40, card_h, t, s, c)
            cy -= card_h + gap

    mid = (top + bot) / 2.0 - 0.45
    for xa, xb in ((3.55, 4.38), (7.78, 8.20), (11.38, 11.80), (15.12, 16.02)):
        _flow_arrow(ax, xa, mid, xb, mid)

    # quality gates strip
    qy, qh = 0.45, 1.85
    draw_rounded_box(ax, 0.40, qy, 19.2, qh, fill=LAYER["qc"]["tint"], border=LAYER["qc"]["edge"], lw=1.4, radius=0.16, shadow=False, zorder=1.0)
    ax.text(0.70, qy + qh - 0.36, "Quality gates across every layer", ha="left", va="center", fontsize=13.5, fontweight="bold", color=LAYER["qc"]["main"])
    ax.text(19.30, qy + qh - 0.36, "64 dbt tests · audit.pipeline_run_metrics", ha="right", va="center", fontsize=10.5, color="#9F1239")
    qcs = [("QC-1", "Null keys"), ("QC-2", "Referential"), ("QC-3", "Value domains"), ("QC-4", "Uniqueness"),
           ("QC-5", "Volume drift"), ("QC-6", "Point-in-time"), ("QC-7", "Stream match")]
    pw = (18.6 - 6 * 0.18) / 7.0
    for i, (q, d) in enumerate(qcs):
        px = 0.70 + i * (pw + 0.18)
        draw_rounded_box(ax, px, qy + 0.25, pw, 0.88, fill="#FFFFFF", border=LAYER["qc"]["main"], lw=1.3, radius=0.10, shadow=False, zorder=2.0)
        ax.text(px + pw / 2.0, qy + 0.84, q, ha="center", va="center", fontsize=12, fontweight="bold", color=LAYER["qc"]["main"], zorder=3)
        fit_text(ax, px + pw / 2.0, qy + 0.48, d, pw - 0.2, ha="center", va="center", fontsize=10, color="#334155", zorder=3)
    _save(fig, "architecture_overview")
    print("→ docs/figures/architecture_overview.svg / .png  (generalized end-to-end architecture)")


def build_architecture_detailed():
    W, H = 22.0, 12.6
    fig, ax = plt.subplots(figsize=(W, H))
    ax.set_xlim(0, W)
    ax.set_ylim(0, H)
    ax.axis("off")

    _title_block(ax, 0.35, 12.05, "Detailed Architecture — Scripts, Tables and Quality Gates by Tier",
                 "Each card names the step, the script or table behind it, and what it guarantees")

    tiers = [
        ("1", "Ingestion", "ingestion/*.py", "src", [
            ("Profile raw files", "raw_source.py · probe_csv_format.py", ["Resolve parquet / csv paths", "Probe schema and nested types", "Verify MD5 checksums"], None),
            ("Batch contract loader", "batch_csv_to_bronze.py", ["11 tables, ~230 GB", "Join keys cast to VARCHAR", "Run metrics logged"], None),
            ("Streaming replay", "kafka_producer_replay.py", ["Redpanda, 3 event tables", "Consumer applies contracts", "Invalid events → dead letters"], "OPTIONAL"),
            ("External sources", "holiday_commercial_builder.py", ["Public holidays SG · TH · VN", "Commercial event names"], None),
        ]),
        ("2", "Bronze", "data/bronze · sql/*.sql", "bronze", [
            ("Partitioned Parquet", "data/bronze/<table>", ["Hive: country / year / month", "ZSTD, 32,768-row flush", "Pruning and pushdown"], None),
            ("Bronze views", "bronze_views_from_parquet.py", ["Zero-copy bronze.* views", "48 dbt source tests"], None),
            ("Row quarantine", "quarantine.rejects_<table>", ["Unparseable CSV lines kept", "Nothing dropped silently"], None),
            ("Go / No-Go gates", "audit.gates_by_country", ["Link ≥ 60% · item ≥ 95%", "Price ≥ 90% · ≥ 20k members", "TH, VN pass · SG review"], None),
            ("Drift & reconcile", "audit.volume_drift · stream_reconciliation", ["±50% vs 28-day mean", "Batch vs stream hash match"], "QC-5 · QC-7"),
        ]),
        ("3", "Silver", "dbt · models/staging, silver", "silver", [
            ("Sales & returns", "stg_sales_detail → slv_fact_sales_line", ["Dedup, latest version", "Sale − cancel netting", "Local time → UTC, EUR"], None),
            ("Catalogue & prices", "slv_dim_model · slv_price_sku_interval", ["SKU → model_code", "National price intervals", "Daily promo share, holidays"], None),
            ("Web & identity", "slv_web_events_clean · slv_user_to_member", ["Flatten STRUCT / LIST", "Cookie → member, 1:1"], None),
            ("Member state", "slv_member_profile · slv_member_sport_asof", ["Eligible consumers only", "As-of sport and usual store"], None),
            ("Quarantine & tests", "qrt_* · slv_identity_conflicts", ["Refused lines keep a reason", "Null, RI, domain, key tests"], "QC-1…4"),
        ]),
        ("4", "Gold", "build_anchor_grid.py · models/gold", "gold", [
            ("Anchor grid", "build_anchor_grid.py", ["Weekly Monday anchors", "Train / valid / test, 42-day purge", "50k / 15k / 50k anchors"], None),
            ("Feature entities 1 & 2", "gld_fs_member · gld_fs_model_country", ["Member: RFM, price, web", "Model: price, promo, calendar", "Every feature as of t"], None),
            ("Candidates R1–R5", "gld_candidates", ["Repurchase · co-purchase", "Web intent · sport affinity", "National best-sellers, top 200"], None),
            ("Pairs & ranking set", "gld_fs_pair → gld_ranking_dataset", ["Member × model features", "Labels at 30 d and 90 d"], None),
            ("Point-in-time ledger", "quarantine.leakage_violations", ["last_source_ts ≤ anchor", "0 violations · recall per source"], "QC-6"),
        ]),
        ("5", "Evaluation", "evaluation/*.py", "eval", [
            ("Fixed LambdaRank", "train_eval_lambdarank.py", ["LightGBM, grouped by member", "Tuned once, then frozen", "Early stop on NDCG@20"], None),
            ("Two-axis ablation", "run_ablation_2axes.py", ["Axis 1: drop feature groups", "Axis 2: drop candidate sources"], None),
            ("Bootstrap & cost", "bootstrap_ci.py · pipeline_cost_profiler.py", ["500× member-level 95% CI", "Cost × gain per arm"], None),
            ("Scale & techniques", "scale_test.py · technique_comparisons.py", ["1→3 countries, 3→36 months", "Parquet, pushdown, ASOF A/B"], None),
            ("Report packaging", "report_tables.py · lineage_graph.py", ["21 tables, t01–t21", "Figures from the dbt manifest"], None),
        ]),
    ]

    pitch, tw = 4.30, 3.90
    top, bot = 11.20, 0.40
    gap = 0.20
    for ti, (num, name, sub, key, cards) in enumerate(tiers):
        c = LAYER[key]
        x = 0.30 + ti * pitch
        draw_rounded_box(ax, x, bot, tw, top - bot, fill=c["tint"], border=c["edge"], lw=1.4, radius=0.18, shadow=False, zorder=1.0)
        draw_rounded_box(ax, x, top - 0.95, tw, 0.95, fill=c["main"], border=c["main"], lw=1.0, radius=0.16, shadow=False, zorder=2.0)
        _number_dot(ax, x + 0.40, top - 0.475, num, c["main"])
        fit_text(ax, x + 0.76, top - 0.34, name, tw - 0.9, ha="left", va="center", fontsize=15.5, fontweight="bold", color="#FFFFFF", zorder=2.5)
        fit_text(ax, x + 0.76, top - 0.68, sub, tw - 0.9, ha="left", va="center", fontsize=9.5, color="#F1F5F9", zorder=2.5)
        n = len(cards)
        avail = top - 0.95 - 0.20 - (bot + 0.20)
        ch = (avail - (n - 1) * gap) / n
        cy = top - 0.95 - 0.20 - ch
        for si, (title, file_, bullets, tag) in enumerate(cards):
            cx = x + 0.18
            cw = tw - 0.36
            draw_rounded_box(ax, cx, cy, cw, ch, fill="#FFFFFF", border=c["main"], lw=1.4, radius=0.10, shadow=True, zorder=3.0)
            ax.add_patch(FancyBboxPatch((cx + 0.03, cy + 0.05), 0.09, ch - 0.10, boxstyle="round,pad=0,rounding_size=0.04",
                                        facecolor=c["main"], edgecolor="none", zorder=3.2))
            tmax = cw - 0.40
            if tag:
                tmax -= len(tag) * 0.085 + 0.40
                _tag(ax, cx + cw - 0.12, cy + ch - 0.28, tag, c["main"])
            fit_text(ax, cx + 0.28, cy + ch - 0.28, f"{num}.{si + 1}  {title}", tmax, ha="left", va="center",
                     fontsize=11, fontweight="bold", color="#0F172A", zorder=3.5)
            fit_text(ax, cx + 0.28, cy + ch - 0.56, file_, cw - 0.40, ha="left", va="center",
                     fontsize=8.4, fontweight="bold", color=c["main"], zorder=3.5)
            step = min((ch - 0.84) / max(len(bullets), 1), 0.34)
            for bi, b in enumerate(bullets):
                fit_text(ax, cx + 0.28, cy + ch - 0.90 - bi * step - 0.05, f"• {b}", cw - 0.40, ha="left", va="center",
                         fontsize=9.2, color="#334155", zorder=3.5)
            cy -= ch + gap
        if ti < 4:
            ym = (top + bot) / 2.0 - 0.4
            _flow_arrow(ax, x + tw + 0.02, ym, x + pitch - 0.02, ym, lw=2.6)
    _save(fig, "architecture_detailed")
    print("→ docs/figures/architecture_detailed.svg / .png  (detailed system & data-flow architecture)")



def build_lineage_ingestion_to_bronze():
    col_defs = [
        ("STAGE 1 · RAW DATA & EXTERNAL", "11 Raw tables (~230 GB) + Python Holidays", "#334155", "#F1F5F9"),
        ("STAGE 2 · INGESTION & STREAM LANE", "Batch loader, Redpanda replay & contracts", "#0284C7", "#E0F2FE"),
        ("STAGE 3 · BRONZE STORAGE & VIEWS", "Partitioned ZSTD Parquet & bronze.* views", "#475569", "#F1F5F9"),
        ("STAGE 4 · BRONZE QUARANTINE & AUDITS", "Rejects, Go/No-Go gates, QC-5 & QC-7", "#D97706", "#FEF3C7"),
    ]

    fig, ax = plt.subplots(figsize=(18.2, 9.6))
    ax.set_xlim(0, 18.2)
    ax.set_ylim(0, 9.6)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    ax.text(0.30, 9.22, "Bronze Layer Architecture — Batch & Streaming Ingestion, Data Contracts, Partitioning & Quality Audits",
            ha="left", va="center", fontsize=14.0, fontweight="bold", color="#0F172A")
    ax.text(0.30, 8.86, "Raw CSV/Parquet (11 tables, ~230 GB) + Optional Redpanda Streaming Replay → Hive-Partitioned ZSTD Parquet, Zero-Copy Views & Gates (Step 2–4 & Step 8)",
            ha="left", va="center", fontsize=9.0, color="#475569")

    xs = [0.30, 4.75, 9.20, 13.65]
    w = 4.15
    for idx, (ctitle, csub, ccol, cbg) in enumerate(col_defs):
        cx = xs[idx]
        draw_rounded_box(ax, cx, 0.35, w, 8.20, fill="#F8FAFC", border="#CBD5E1", lw=1.0, radius=0.14, shadow=False, ls="--", zorder=0.8)
        draw_rounded_box(ax, cx, 7.95, w, 0.60, fill=cbg, border=ccol, lw=1.3, radius=0.10, shadow=False, zorder=2.0)
        fit_text(ax, cx + w / 2.0, 8.35, ctitle, w - 0.25, ha="center", va="center", fontsize=8.6, fontweight="bold", color=ccol, zorder=2.5)
        fit_text(ax, cx + w / 2.0, 8.10, csub, w - 0.25, ha="center", va="center", fontsize=7.0, color="#334155", zorder=2.5)

    def bcard(col_i, y, h, title, sub1, sub2, kind="source", badge=None):
        cx = xs[col_i] + w / 2.0
        cy = y + h / 2.0
        NODE_META[title] = (sub1, sub2)
        draw_node_card(ax, cx, cy, w - 0.26, h, title, kind, custom_badge=badge, title_fs=8.5, sub_fs=6.8, zorder=4.0)
        return (xs[col_i] + 0.13, cy, xs[col_i] + w - 0.13)

    # Col 0: Raw sources grouped by type
    r1 = bcard(0, 6.80, 0.90, "Fact Parquet Exports (4 tables)", "sales_detail (12.2 GB) · f_member_purchase", "sales_tender_detail · all_store_selling_price", "source", "PARQUET")
    r2 = bcard(0, 5.65, 0.90, "Chunked Web Event Parts", "tracking_ecom_events/part-*.snappy.parquet", "1,774 daily files (~200 GB, 1.0B events)", "source", "1,774 PARTS")
    r3 = bcard(0, 4.50, 0.90, "Catalogue & Dimension Exports", "dim_item.parquet (4.36M SKUs, 0.7 GB)", "dim_business_unit.csv · dim_calendar.csv", "source", "DIM TABLES")
    r4 = bcard(0, 3.35, 0.90, "Member, Sport & Stock CSVs", "d_member.csv (2.0 GB) · f_member_favorite_sport", "stock_availability_rate.csv (5.4 GB)", "source", "CSV TABLES")
    r5 = bcard(0, 1.95, 0.90, "Event Replay Source (3 tables)", "sales_detail · f_member_purchase", "tracking_ecom_events (streamed by timestamp)", "staging", "STREAM SRC")
    r6 = bcard(0, 0.70, 0.90, "External Reference Sources", "Python holidays library (SG, TH, VN)", "ingestion/commercial_event_names.csv", "ext", "EXT INPUT")

    # Col 1: Ingestion & Contracts
    i1 = bcard(1, 6.60, 1.10, "probe_csv_format & full_scan", "raw_source.py resolution & MD5 verification", "Outputs csv_profile.md & csv_fullscan.md", "audit", "PROFILING")
    i2 = bcard(1, 5.05, 1.25, "batch_csv_to_bronze.py", "Enforces ingestion/table_contracts.yml", "VARCHAR key casts · 32,768-row partition flush", "silver", "BATCH LOADER")
    i3 = bcard(1, 3.45, 1.25, "Redpanda Replay Lane", "kafka_producer_replay.py → Redpanda Broker", "kafka_consumer_to_bronze.py (stream_contracts.py)", "staging", "STREAM LANE")
    i4 = bcard(1, 1.95, 1.10, "bronze_views_from_parquet.py", "Binds zero-copy bronze.* views in DuckDB", "Exposes 11 tables to dbt without data duplication", "silver", "VIEW BINDER")
    i5 = bcard(1, 0.65, 0.95, "holiday_commercial_builder.py", "Builds ext.public_holidays & event dictionary", "Materialised directly in lakehouse.duckdb", "ext", "EXT BUILDER")

    # Col 2: Bronze Storage & Views
    s1 = bcard(2, 6.25, 1.40, "Hive-Partitioned ZSTD Parquet", "data/bronze/<table>/country=.../year=.../month=...", "Fact tables partitioned for pruning & pushdown", "source", "ZSTD PARQUET")
    s2 = bcard(2, 4.55, 1.35, "Unpartitioned Bronze Parquet", "data/bronze/{dim_item, d_member, dim_calendar…}", "Dimension & lookup tables in ZSTD Parquet", "source", "DIM PARQUET")
    s3 = bcard(2, 3.05, 1.15, "Streaming Bronze Parquet", "data/bronze_stream/<table>/country=.../year=...", "Micro-batch Parquet output from Kafka consumer", "staging", "STREAM LAKE")
    s4 = bcard(2, 1.75, 1.00, "bronze.* DuckDB Views (11 views)", "Unified SQL interface for dbt staging & silver", "48 dbt source tests (not_null, accepted_values)", "silver", "DBT SOURCES")
    s5 = bcard(2, 0.55, 0.95, "ext.* DuckDB Tables (2 tables)", "ext.public_holidays · ext.commercial_event_names", "Joined by slv_calendar_enriched", "ext", "EXT TABLES")

    # Col 3: Quarantine & Audits
    q1 = bcard(3, 6.55, 1.15, "quarantine.rejects_<table>", "DuckDB reject_errors on malformed CSV lines", "46 d_member & 19 dim_item rows preserved (t11)", "quarantine", "CSV REJECTS")
    q2 = bcard(3, 5.15, 1.15, "audit.gates_by_country (Step 4)", "Member link ≥60%, Item ≥95%, Price ≥90%, ≥20k", "TH & VN = PASS (main); SG = REVIEW (50–64% link)", "audit", "GO / NO-GO")
    q3 = bcard(3, 3.75, 1.15, "audit.volume_drift (QC-5)", "±50% vs 28-day trailing same-weekday mean", "Attaches holiday / event probable cause", "audit", "QC-5 DRIFT")
    q4 = bcard(3, 2.35, 1.15, "Stream DLQ & QC-7 Reconciliation", "Dead-Letter Queue for invalid Kafka payloads", "audit.stream_reconciliation: row & hash match", "quarantine", "QC-7 & DLQ")
    q5 = bcard(3, 0.70, 1.30, "Domain Audits & Run Metrics", "audit.price_uniformity · stock_coverage · gap", "audit.pipeline_run_metrics (wall time & rows)", "audit", "OBSERVABILITY")

    # Connect cards cleanly
    links = [
        (r1, i1, "#64748B", "-"), (r2, i1, "#64748B", "-"),
        (r1, i2, "#2563EB", "-"), (r2, i2, "#2563EB", "-"), (r3, i2, "#2563EB", "-"), (r4, i2, "#2563EB", "-"),
        (r5, i3, "#16A34A", "-"), (r6, i5, "#7E22CE", "-"),
        (i2, s1, "#2563EB", "-"), (i2, s2, "#2563EB", "-"), (i2, q1, "#E11D48", "--"),
        (i3, s3, "#16A34A", "-"), (i3, q4, "#E11D48", "--"),
        (s1, i4, "#475569", "-"), (s2, i4, "#475569", "-"), (i4, s4, "#2563EB", "-"),
        (i5, s5, "#7E22CE", "-"),
        (s4, q2, "#D97706", "--"), (s4, q3, "#D97706", "--"), (s4, q5, "#D97706", "--"),
        (s1, q4, "#0D9488", "--"), (s3, q4, "#0D9488", "--"),
    ]
    for (x1_l, y1, x1_r), (x2_l, y2, x2_r), col, ls in links:
        if x2_l > x1_r:
            draw_routed_edge(ax, x1_r, y1, x2_l, y2, color=col, style=ls, lw=1.35)
        else:
            draw_routed_edge(ax, x1_r, y1, x2_r, y2, color=col, style=ls, lw=1.2)

    for fmt in ("svg", "png"):
        fig.savefig(OUT / f"lineage_ingestion_to_bronze.{fmt}", dpi=260 if fmt == "png" else None, bbox_inches="tight", pad_inches=0.20, facecolor="#FFFFFF")
    plt.close(fig)
    for f in FIT_FAILS:
        print("  overflow:", f)
    FIT_FAILS.clear()
    print("→ docs/figures/lineage_ingestion_to_bronze.svg / .png  (Ingestion & Bronze layer detail)")


# ══════════════════════════════════════════════════════════════════════════════
# 7. GOLD → EVALUATION & ABLATION LAYER DIAGRAM (lineage_gold_to_evaluation.{svg,png})
# ══════════════════════════════════════════════════════════════════════════════
def build_lineage_gold_to_evaluation():
    col_defs = [
        ("STAGE 1 · GOLD SIGNALS (F0–F5 & R1–R5)", "Feature groups & candidate sources", "#A16207", "#FEF9C3"),
        ("STAGE 2 · RANKING DATASET & SPLIT", "gld_ranking_dataset & temporal purge split", "#3730A3", "#E0E7FF"),
        ("STAGE 3 · MEASURING INSTRUMENT", "Fixed LightGBM LambdaRank & 2-Axis Ablation", "#0F766E", "#CCFBF1"),
        ("STAGE 4 · EVALUATION & REPORT OUTPUTS", "Bootstrap 95% CI, Cost×Gain & Scale tests", "#1D4ED8", "#DBEAFE"),
    ]

    fig, ax = plt.subplots(figsize=(18.2, 9.6))
    ax.set_xlim(0, 18.2)
    ax.set_ylim(0, 9.6)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    ax.text(0.30, 9.22, "Gold → Evaluation & Two-Axis Ablation Architecture (Data Value vs. Processing Cost)",
            ha="left", va="center", fontsize=14.0, fontweight="bold", color="#0F172A")
    ax.text(0.30, 8.86, "How Feature Groups (F0–F5, Sport) and Candidate Generators (R1–R5) Feed the Fixed LightGBM LambdaRank Instrument & Cost–Benefit Evaluation (Step 6–7)",
            ha="left", va="center", fontsize=9.0, color="#475569")

    xs = [0.30, 4.75, 9.20, 13.65]
    w = 4.15
    for idx, (ctitle, csub, ccol, cbg) in enumerate(col_defs):
        cx = xs[idx]
        draw_rounded_box(ax, cx, 0.35, w, 8.20, fill="#F8FAFC", border="#CBD5E1", lw=1.0, radius=0.14, shadow=False, ls="--", zorder=0.8)
        draw_rounded_box(ax, cx, 7.95, w, 0.60, fill=cbg, border=ccol, lw=1.3, radius=0.10, shadow=False, zorder=2.0)
        fit_text(ax, cx + w / 2.0, 8.35, ctitle, w - 0.25, ha="center", va="center", fontsize=8.6, fontweight="bold", color=ccol, zorder=2.5)
        fit_text(ax, cx + w / 2.0, 8.10, csub, w - 0.25, ha="center", va="center", fontsize=7.0, color="#334155", zorder=2.5)

    def ecard(col_i, y, h, title, sub1, sub2, kind="gold", badge=None):
        cx = xs[col_i] + w / 2.0
        cy = y + h / 2.0
        NODE_META[title] = (sub1, sub2)
        draw_node_card(ax, cx, cy, w - 0.26, h, title, kind, custom_badge=badge, title_fs=8.5, sub_fs=6.8, zorder=4.0)
        return (xs[col_i] + 0.13, cy, xs[col_i] + w - 0.13)

    # Col 0: Gold Feature Groups & Candidate Sources
    f0 = ecard(0, 6.75, 0.95, "Baseline Signals (F0, F2, F4)", "F0 Member RFM · F2 Model repurchase & cycle", "F4 Basket co-purchase lift (purchase history only)", "gold", "BASELINE B0")
    f1 = ecard(0, 5.55, 0.95, "F1 · Member Price Profile", "price_q25, price_q50, price_q75, price_q50_eur", "promo_affinity (historical discount share)", "gold", "FEATURE F1")
    f3 = ecard(0, 4.35, 0.95, "F3 · Stitched Web Intent", "web_sessions_7d/30d, web_view_30d, web_cart_30d", "web_data_available indicator (verified_ts ≤ t)", "gold", "FEATURE F3")
    f5 = ecard(0, 3.15, 0.95, "F5 · Model Price & Calendar", "ASOF SKU median price, promo_depth, is_temp_promo", "in_commercial_event, days_to_next_holiday, ratio", "gold", "FEATURE F5")
    sp = ecard(0, 1.95, 0.95, "Sport & Store State Signals", "n_sports, sport_affinity, usual_store_share", "ASOF favourite-sport intervals & modal store", "gold", "SPORT & STORE")
    ca = ecard(0, 0.60, 1.10, "5 Candidate Sources (R1–R5)", "R1 Repurchase · R2 Co-purchase · R3 Web Intent", "R4 Sport × Dept Affinity · R5 National Best-Sellers", "gold", "POOL @ 200")

    # Col 1: Ranking Dataset & Temporal Split
    d1 = ecard(1, 5.95, 1.55, "gold.gld_ranking_dataset", "Joins Entity 1 + Entity 2 + Entity 3 (gld_fs_pair)", "Labels: non-returned purchase in Δ=30d & Δ=90d", "gold", "RANKING SET")
    d2 = ecard(1, 3.95, 1.55, "Temporal Split with Purge Gaps", "Train: 2023-01→2025-09 · Valid: 2025-10→2025-12", "Test: 2026-02→2026-07 · 42-day purge gaps (split.yml)", "python", "NO LEAKAGE")
    d3 = ecard(1, 2.15, 1.35, "Evaluation Scope & Anchor Caps", "Main set: TH + VN (PASS) · Secondary: SG (REVIEW)", "50k train / 15k valid / 50k test anchors per country", "python", "TH+VN / SG")
    d4 = ecard(1, 0.60, 1.15, "QC-6 & Candidate Recall Audit", "quarantine.leakage_violations = 0 rows verified", "audit.candidate_recall per source R1–R5 (t12)", "quarantine", "QC-6 PASS")

    # Col 2: LambdaRank & Two-Axis Ablation
    m1 = ecard(2, 6.10, 1.45, "Fixed LightGBM LambdaRank", "train_eval_lambdarank.py · group=(member, anchor)", "Tuned once on Full (valid NDCG@20), then frozen", "eval", "INSTRUMENT")
    m2 = ecard(2, 4.30, 1.45, "Baseline B0 vs Full Comparison", "B0: R1+R2+R5 candidates, F0+F2+F4 features", "Full: R1–R5 candidates, F0–F5 + Sport features", "eval", "B0 vs FULL")
    m3 = ecard(2, 2.45, 1.50, "Axis 1 · Feature Ablation", "Arms: −F1 (Price), −F3 (Web), −F5 (Cal/Price), −Sport", "Re-runs dbt with vars disabled to measure true cost", "eval", "AXIS 1: FEAT")
    m4 = ecard(2, 0.60, 1.50, "Axis 2 · Candidate Ablation", "Arms: −R1, −R2, −R3, −R4, −R5 (run_ablation_2axes.py)", "Removed source scored −∞ on same test positives", "eval", "AXIS 2: CAND")

    # Col 3: Evaluation Metrics & Report Tables
    o1 = ecard(3, 6.20, 1.35, "Ranking Quality & Bootstrap CI", "HR@10/20, MRR@10/20, NDCG@10/20, Recall@50", "500× member-level bootstrap 95% CI on Δ(Full−Arm)", "audit", "METRICS & CI")
    o2 = ecard(3, 4.45, 1.40, "Cost × Benefit Trade-Off (MT3)", "pipeline_cost_profiler.py + pipeline_run_metrics", "Wall time, peak RSS & output rows per ΔNDCG@20", "audit", "COST × GAIN")
    o3 = ecard(3, 2.65, 1.45, "Scale & Technique Tests", "scale_test.py (1→3 countries, 3→36 months)", "technique_comparisons.py (Parquet, Pushdown, ASOF)", "python", "SCALE & A/B")
    o4 = ecard(3, 0.65, 1.60, "Reproducible Report Tables", "tools/report_tables.py → docs/report/tables/t01..t21", "Zero hand-typed numbers; REDACT_TERMS enforced", "silver", "REPORT TABLES")

    links = [
        (f0, d1, "#CA8A04", "-"), (f1, d1, "#CA8A04", "-"), (f3, d1, "#CA8A04", "-"),
        (f5, d1, "#CA8A04", "-"), (sp, d1, "#CA8A04", "-"), (ca, d1, "#CA8A04", "-"),
        (ca, d4, "#D97706", "--"), (d1, d4, "#E11D48", "--"),
        (d1, m1, "#0F766E", "-"), (d2, m1, "#4F46E5", "-"), (d3, m1, "#4F46E5", "-"),
        (d1, m2, "#0F766E", "-"), (d1, m3, "#0F766E", "-"), (d1, m4, "#0F766E", "-"),
        (m1, o1, "#0D9488", "-"), (m2, o1, "#0D9488", "-"), (m3, o1, "#0D9488", "-"), (m4, o1, "#0D9488", "-"),
        (m3, o2, "#D97706", "-"), (m4, o2, "#D97706", "-"),
        (o1, o4, "#2563EB", "-"), (o2, o4, "#2563EB", "-"), (o3, o4, "#2563EB", "-"),
    ]
    for (x1_l, y1, x1_r), (x2_l, y2, x2_r), col, ls in links:
        draw_routed_edge(ax, x1_r, y1, x2_l, y2, color=col, style=ls, lw=1.35)

    for fmt in ("svg", "png"):
        fig.savefig(OUT / f"lineage_gold_to_evaluation.{fmt}", dpi=260 if fmt == "png" else None, bbox_inches="tight", pad_inches=0.20, facecolor="#FFFFFF")
    plt.close(fig)
    for f in FIT_FAILS:
        print("  overflow:", f)
    FIT_FAILS.clear()
    print("→ docs/figures/lineage_gold_to_evaluation.svg / .png  (Gold → Evaluation & Ablation detail)")


if __name__ == "__main__":
    build_architecture_overview()
    build_architecture_detailed()
    build_lineage_full()
    build_lineage_bronze_to_silver()
    build_lineage_silver_to_gold()
    build_lineage_ingestion_to_bronze()
    build_lineage_gold_to_evaluation()
