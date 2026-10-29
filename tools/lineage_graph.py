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


def draw_node_card(ax, cx, cy, w, h, name, kind, custom_badge=None, title_fs=8.5, sub_fs=6.8, zorder=4):
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

    bw = max(0.76, len(badge_txt) * 0.068 + 0.14)
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
    meta1, meta2 = NODE_META.get(name, ("", ""))
    tx = x + accent_w + 0.090
    if len(name) > 25:
        eff_title_fs = title_fs - 1.35
    elif len(name) > 21:
        eff_title_fs = title_fs - 0.90
    elif len(name) > 17:
        eff_title_fs = title_fs - 0.45
    else:
        eff_title_fs = title_fs

    if meta1 and meta2:
        ax.text(tx, y + h * (0.74 if h >= 0.90 else 0.75), name, ha="left", va="center",
                fontsize=eff_title_fs, fontweight="bold", color=pal["title"], zorder=zorder + 0.5)
        ax.text(tx, y + h * (0.43 if h >= 0.90 else 0.44), meta1, ha="left", va="center",
                fontsize=sub_fs - 0.25, fontweight="bold", color=pal["accent"], zorder=zorder + 0.5)
        ax.text(tx, y + h * (0.18 if h >= 0.90 else 0.17), meta2, ha="left", va="center",
                fontsize=sub_fs - 0.85, color=pal["sub"], zorder=zorder + 0.5)
    elif meta1:
        ax.text(tx, y + h * 0.68, name, ha="left", va="center",
                fontsize=eff_title_fs, fontweight="bold", color=pal["title"], zorder=zorder + 0.5)
        ax.text(tx, y + h * 0.26, meta1, ha="left", va="center",
                fontsize=sub_fs, color=pal["sub"], zorder=zorder + 0.5)
    else:
        ax.text(tx, cy, name, ha="left", va="center",
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
        ax.text(sl_x + 0.10 + lbl_w / 2.0, ym + 0.26, sl_title, ha="center", va="center",
                fontsize=8.0, fontweight="bold", color=sl_fg, zorder=1.5)
        ax.text(sl_x + 0.10 + lbl_w / 2.0, ym - 0.26, sl_sub, ha="center", va="center",
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
        ax.text(cx, hdr_y + hdr_h * 0.65, c_title, ha="center", va="center",
                fontsize=8.4, fontweight="bold", color=c_color, zorder=2.5)
        ax.text(cx, hdr_y + hdr_h * 0.24, c_sub, ha="center", va="center",
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
def build_architecture_overview():
    fig, ax = plt.subplots(figsize=(18.5, 10.2))
    ax.set_xlim(0, 18.5)
    ax.set_ylim(0, 10.2)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    # Header
    ax.text(0.35, 9.78, "Multi-Signal Retail Lakehouse & Personalized Recommendation Pipeline — Architecture Overview",
            ha="left", va="center", fontsize=15.5, fontweight="bold", color="#0F172A")
    ax.text(0.35, 9.40, "Three-Tier Medallion Lakehouse (Bronze → Silver → Gold) on DuckDB & ZSTD Parquet + Fixed LightGBM LambdaRank Evaluation Instrument (SG · TH · VN, 2023–2026)",
            ha="left", va="center", fontsize=9.6, color="#475569")

    # 5 Macro Stage Columns
    stages = [
        (0.35, 3.15, "1. DATA SOURCES", "11 Raw Tables (~230 GB)\n+ Streaming & External", "#334155", "#F8FAFC", "#CBD5E1"),
        (3.85, 3.15, "2. BRONZE LAYER", "Partitioned ZSTD Parquet\nContracts & Quarantine", "#475569", "#F1F5F9", "#94A3B8"),
        (7.35, 3.55, "3. SILVER LAYER", "Cleaned, Harmonised &\nIntegrated Domain Models", "#1D4ED8", "#EFF6FF", "#93C5FD"),
        (11.25, 3.55, "4. GOLD LAYER", "Point-in-Time Feature Store\n& Candidate Engine (R1–R5)", "#A16207", "#FEFCE8", "#FDE047"),
        (15.15, 3.00, "5. EVALUATION", "Fixed LambdaRank & 2-Axis\nCost × Benefit Ablation", "#0F766E", "#F0FDFA", "#5EEAD4"),
    ]

    col_bot = 1.65
    col_top = 9.05
    col_h = col_top - col_bot

    for sx, sw, stitle, ssub, scol, sbg, sborder in stages:
        draw_rounded_box(ax, sx, col_bot, sw, col_h, fill=sbg, border=sborder, lw=1.4, radius=0.16, shadow=True, zorder=1.0)
        draw_rounded_box(ax, sx, col_top - 0.82, sw, 0.82, fill=scol, border=scol, lw=1.0, radius=0.14, shadow=False, zorder=2.0)
        ax.text(sx + sw / 2.0, col_top - 0.28, stitle, ha="center", va="center", fontsize=10.5, fontweight="bold", color="#FFFFFF", zorder=2.5)
        ax.text(sx + sw / 2.0, col_top - 0.60, ssub, ha="center", va="center", fontsize=7.6, color="#E2E8F0", zorder=2.5)

    def add_card(x, y, w, h, title, bullets, accent="#2563EB", bg="#FFFFFF", border="#CBD5E1", badge=None):
        draw_rounded_box(ax, x, y, w, h, fill=bg, border=border, lw=1.15, radius=0.10, shadow=True, zorder=3.0)
        bar = FancyBboxPatch((x + 0.015, y + 0.025), 0.075, h - 0.05,
                             boxstyle="round,pad=0,rounding_size=0.04", facecolor=accent, edgecolor="none", zorder=3.2)
        ax.add_patch(bar)
        if badge:
            bw = max(0.62, len(badge) * 0.062 + 0.12)
            bh = 0.18
            bp = FancyBboxPatch((x + w - bw - 0.07, y + h - bh - 0.05), bw, bh,
                                boxstyle="round,pad=0,rounding_size=0.05", facecolor=accent, edgecolor="none", alpha=0.14, zorder=3.3)
            ax.add_patch(bp)
            ax.text(x + w - bw / 2.0 - 0.07, y + h - bh / 2.0 - 0.05, badge,
                    ha="center", va="center", fontsize=5.8, fontweight="bold", color=accent, zorder=3.4)
        t_fs = 7.9 if len(title) > 26 else 8.3
        ax.text(x + 0.14, y + h - 0.16, title, ha="left", va="center", fontsize=t_fs, fontweight="bold", color="#0F172A", zorder=3.5)
        n_b = len(bullets)
        for idx, btxt in enumerate(bullets):
            by = y + h - 0.40 - idx * ((h - 0.48) / max(1, n_b))
            ax.text(x + 0.16, by, f"• {btxt}", ha="left", va="center", fontsize=6.95, color="#334155", zorder=3.5)

    # Stage 1 cards
    add_card(0.50, 6.40, 2.85, 1.62, "Batch Retail Exports", [
        "POS & Online Sales (89.3M lines)",
        "Catalogue (4.36M SKUs) & Prices (42.4M)",
        "Members (2.0 GB), Purchase Bridge, Sport",
        "Business Units, Calendar & Daily Stock"
    ], accent="#334155", badge="CSV / PARQUET")

    add_card(0.50, 4.55, 2.85, 1.62, "Web & App Clickstream", [
        "tracking_ecom_events (~200 GB)",
        "1,774 Spark Parquet parts · 1.0B events",
        "Nested STRUCT & LIST<STRUCT> schemas",
        "33.9% direct member_id · 100% user_id"
    ], accent="#475569", badge="1.0B EVENTS")

    add_card(0.50, 3.05, 2.85, 1.28, "Optional Streaming Lane", [
        "Redpanda replay of 3 event tables",
        "Consumer applies contracts + DLQ",
        "Reconciled daily vs batch (QC-7)"
    ], accent="#0284C7", badge="REDPANDA")

    add_card(0.50, 1.85, 2.85, 1.00, "Self-Built External Data", [
        "Public holidays (holidays library)",
        "Commercial event dictionary (ext.*)"
    ], accent="#7E22CE", badge="EXT SOURCES")

    # Stage 2 cards
    add_card(4.00, 6.40, 2.85, 1.62, "Data Contracts & Loader", [
        "table_contracts.yml & stream_contracts.py",
        "Key columns cast to VARCHAR",
        "Required-column & schema validation",
        "Streaming 32k-row partition flush"
    ], accent="#475569", badge="DUCKDB 2.0")

    add_card(4.00, 4.55, 2.85, 1.62, "Partitioned Parquet Lake", [
        "ZSTD compressed Parquet files",
        "Hive-partitioned (country / year / month)",
        "Partition pruning & projection pushdown",
        "Exposed as zero-copy bronze.* views"
    ], accent="#334155", badge="HIVE ZSTD")

    add_card(4.00, 3.05, 2.85, 1.28, "Rejects & Go/No-Go Gates", [
        "Malformed CSV → quarantine.rejects_*",
        "4 Go/No-Go gates per country × year",
        "TH + VN = PASS (main), SG = REVIEW"
    ], accent="#E11D48", badge="QUARANTINE")

    add_card(4.00, 1.85, 2.85, 1.00, "Bronze Observability", [
        "QC-5 Volume drift (±50% vs 28d mean)",
        "QC-7 Batch vs Stream hash match"
    ], accent="#D97706", badge="QC-5 / QC-7")

    # Stage 3 cards
    add_card(7.50, 6.72, 3.25, 1.32, "Sales Netting & Returns", [
        "Exact dedup + latest transaction_version_at",
        "Signed sale − cancel netting per (tx, item)",
        "Local → naive UTC tz; EUR conversion"
    ], accent="#1D4ED8", badge="FACT SALES")

    add_card(7.50, 5.25, 3.25, 1.32, "Catalogue & Price Timeline", [
        "SKU → model_code (excl. UUID & fixtures)",
        "National SKU price intervals (type 15 > 50)",
        "4 price types → promo_kind; depth ≤ 90%"
    ], accent="#2563EB", badge="MODEL & PRICE")

    add_card(7.50, 3.92, 3.25, 1.18, "Inferred Commercial Calendar", [
        "O(N+D) difference-array daily promo share",
        "Peaks ≥ 1.5σ & ≥ 3 days + public holidays"
    ], accent="#0284C7", badge="SELF-BUILT")

    add_card(7.50, 2.60, 3.25, 1.18, "Web Parsing & Identity Stitching", [
        "STRUCT/LIST flatten; numeric model filter",
        "2-tier cookie→member (ORDER, LOGIN ±90d)"
    ], accent="#7E22CE", badge="STITCHING")

    add_card(7.50, 1.80, 3.25, 0.68, "Member State & Quarantine Routing", [
        "Consumer filter, ASOF sport/store · qrt_sales_line"
    ], accent="#BE123C", badge="QC-1..4")

    # Stage 4 cards
    add_card(11.40, 6.72, 3.25, 1.32, "Temporal Anchor Grid (Python)", [
        "Weekly Mondays after member's 2nd tx",
        "Train / Valid / Test with 42-day purge gaps",
        "90d purchase filter, 4× stride, 50k/15k/50k cap"
    ], accent="#4338CA", badge="ANCHOR GRID")

    add_card(11.40, 4.95, 3.25, 1.62, "3 Point-in-Time Feature Entities", [
        "Entity 1 (gld_fs_member): F0 RFM, F1 price, F3 web",
        "Entity 2 (gld_fs_model_country): ASOF median price,",
        "  promo depth, calendar events & 28d popularity",
        "Entity 3 (gld_fs_pair): F2 rhythm, F4 lift, F5 fit"
    ], accent="#CA8A04", badge="AS-OF ≤ t")

    add_card(11.40, 3.25, 3.25, 1.55, "5 Candidate Generators (Top 200)", [
        "R1 Repurchase history · R2 Basket co-purchase lift",
        "R3 Web intent (30d) · R4 Sport × Dept affinity",
        "R5 National 28d best-sellers (priority R1>R3>R2>R4>R5)"
    ], accent="#D97706", badge="R1 – R5")

    add_card(11.40, 1.80, 3.25, 1.30, "Ranking Dataset & QC-6 Ledger", [
        "gld_ranking_dataset: non-returned Δ = 30d & 90d",
        "QC-6 asserts last_source_ts ≤ anchor_date (0 rows)",
        "audit.candidate_recall per source R1–R5"
    ], accent="#BE123C", badge="QC-6 = 0")

    # Stage 5 cards
    add_card(15.30, 6.45, 2.70, 1.58, "Fixed Measuring Instrument", [
        "LightGBM LambdaRank (NDCG@20)",
        "Hyper-parameters tuned once on",
        "  Full, frozen across all arms",
        "Isolates data value from model tuning"
    ], accent="#0F766E", badge="LAMBDARANK")

    add_card(15.30, 4.55, 2.70, 1.72, "Two-Axis Ablation Study", [
        "Baseline B0 vs Full configuration",
        "Feature axis: −F1, −F3, −F5, −Sport",
        "Candidate axis: −R1 … −R5 (−∞ mask",
        "  keeps identical test positives)"
    ], accent="#0D9488", badge="10 ARMS")

    add_card(15.30, 2.95, 2.70, 1.42, "Statistical & Cost Analysis", [
        "HR, MRR, NDCG@10/20, Recall@50",
        "500× Member-level Bootstrap 95% CI",
        "Cost × Gain via pipeline_run_metrics"
    ], accent="#0891B2", badge="COST × GAIN")

    add_card(15.30, 1.80, 2.70, 0.98, "Scale & Technique Benchmarks", [
        "1→2→3 countries · 3→12→36 months",
        "Parquet, Projection, ASOF, SQL Regex"
    ], accent="#4F46E5", badge="SCALE TEST")

    # Inter-stage flow arrows
    arrow_xs = [(3.50, 3.85), (7.00, 7.35), (10.90, 11.25), (14.80, 15.15)]
    for x1, x2 in arrow_xs:
        for ay in (7.15, 5.10, 3.15):
            ax.plot([x1, x2 - 0.08], [ay, ay], color="#334155", lw=2.2, zorder=4)
            draw_arrowhead(ax, x2, ay, 1.0, 0.0, "#334155", size=0.14, zorder=4.2)

    # Bottom Cross-Cutting Governance & Observability Bar
    draw_rounded_box(ax, 0.35, 0.22, 17.80, 1.18, fill="#0F172A", border="#334155", lw=1.4, radius=0.14, shadow=True, zorder=2.0)
    ax.text(0.60, 1.12, "CROSS-CUTTING DATA QUALITY GATES (QC-1 … QC-7) & PIPELINE OBSERVABILITY (64 dbt Tests · audit.pipeline_run_metrics)",
            ha="left", va="center", fontsize=8.8, fontweight="bold", color="#F8FAFC", zorder=3.0)

    qc_badges = [
        ("QC-1 · Null Keys = 0", "Block at Bronze→Silver & Gold", "#38BDF8"),
        ("QC-2 · Referential Integrity", "≥95/60/90% · TH,VN Pass, SG Review", "#4ADE80"),
        ("QC-3 · Value Domains", "Route bad price/qty to Quarantine", "#FB7185"),
        ("QC-4 · Key Uniqueness", "Block after dedup, net & fs_pair", "#A78BFA"),
        ("QC-5 · Volume Drift", "±50% vs 28d weekday mean", "#FBBF24"),
        ("QC-6 · Point-in-Time", "source_ts & verified_ts ≤ anchor", "#F43F5E"),
        ("QC-7 · Stream Reconcile", "Batch vs Redpanda row/hash match", "#2DD4BF"),
    ]
    qx = 0.58
    qw = 2.42
    for qtitle, qsub, qcol in qc_badges:
        draw_rounded_box(ax, qx, 0.34, qw, 0.58, fill="#1E293B", border=qcol, lw=1.0, radius=0.08, shadow=False, zorder=3.0)
        ax.text(qx + qw / 2.0, 0.72, qtitle, ha="center", va="center", fontsize=7.1, fontweight="bold", color=qcol, zorder=3.5)
        ax.text(qx + qw / 2.0, 0.48, qsub, ha="center", va="center", fontsize=6.2, color="#CBD5E1", zorder=3.5)
        qx += qw + 0.08

    for fmt in ("svg", "png"):
        fig.savefig(OUT / f"architecture_overview.{fmt}", dpi=260 if fmt == "png" else None, bbox_inches="tight", pad_inches=0.20, facecolor="#FFFFFF")
    plt.close(fig)
    print("→ docs/figures/architecture_overview.svg / .png  (generalized end-to-end architecture)")


# ══════════════════════════════════════════════════════════════════════════════
# 5. SYNTHESIS DIAGRAM — DETAILED SYSTEM & DATA-FLOW ARCHITECTURE
#    (docs/figures/architecture_detailed.{svg,png})
# ══════════════════════════════════════════════════════════════════════════════
def build_architecture_detailed():
    fig, ax = plt.subplots(figsize=(22.0, 13.5))
    ax.set_xlim(0, 22.0)
    ax.set_ylim(0, 13.5)
    ax.axis("off")
    fig.patch.set_facecolor("#FFFFFF")

    # Title banner
    ax.text(0.35, 13.08, "Detailed System & Data-Flow Architecture — Multi-Dimensional Retail Recommendation Pipeline",
            ha="left", va="center", fontsize=16.0, fontweight="bold", color="#0F172A")
    ax.text(0.35, 12.70, "End-to-End Execution Blueprint: Ingestion & Streaming Contracts → Bronze Lakehouse & Audits → Silver Domain Models → Gold Feature Entities (F0–F5) & Candidates (R1–R5) → Evaluation",
            ha="left", va="center", fontsize=9.8, color="#475569")

    # 5 Detailed Tier Bands (Left to Right)
    tiers = [
        (0.30, 3.85, "TIER 1 · INGESTION & STREAMING", "ingestion/*.py · table_contracts.yml", "#334155", "#F8FAFC", "#CBD5E1"),
        (4.45, 3.85, "TIER 2 · BRONZE & PROFILING GATES", "data/bronze/* · sql/*.sql · QC-5 & QC-7", "#475569", "#F1F5F9", "#94A3B8"),
        (8.60, 4.35, "TIER 3 · SILVER DOMAIN LAYER (dbt)", "models/staging & models/silver · QC-1..4", "#1D4ED8", "#EFF6FF", "#93C5FD"),
        (13.25, 4.55, "TIER 4 · GOLD FEATURE STORE & CANDIDATES", "build_anchor_grid.py · models/gold · QC-6", "#A16207", "#FEFCE8", "#FDE047"),
        (18.10, 3.60, "TIER 5 · RANKING, ABLATION & METRICS", "evaluation/*.py · LightGBM LambdaRank", "#0F766E", "#F0FDFA", "#5EEAD4"),
    ]

    t_bot = 0.35
    t_top = 12.35
    t_h = t_top - t_bot

    for tx, tw, ttitle, tsub, tcol, tbg, tborder in tiers:
        draw_rounded_box(ax, tx, t_bot, tw, t_h, fill=tbg, border=tborder, lw=1.4, radius=0.16, shadow=True, zorder=1.0)
        draw_rounded_box(ax, tx, t_top - 0.78, tw, 0.78, fill=tcol, border=tcol, lw=1.0, radius=0.14, shadow=False, zorder=2.0)
        ax.text(tx + tw / 2.0, t_top - 0.26, ttitle, ha="center", va="center", fontsize=9.8, fontweight="bold", color="#FFFFFF", zorder=2.5)
        ax.text(tx + tw / 2.0, t_top - 0.56, tsub, ha="center", va="center", fontsize=7.4, color="#E2E8F0", zorder=2.5)

    def detail_box(x, y, w, h, header, subheader, lines, accent="#1D4ED8", bg="#FFFFFF", border="#CBD5E1", tag=None):
        draw_rounded_box(ax, x, y, w, h, fill=bg, border=border, lw=1.15, radius=0.10, shadow=True, zorder=3.0)
        draw_rounded_box(ax, x, y + h - 0.46, w, 0.46, fill=accent, border=accent, lw=0.8, radius=0.09, shadow=False, alpha=0.12, zorder=3.1)
        bar = FancyBboxPatch((x + 0.015, y + 0.02), 0.07, h - 0.04,
                             boxstyle="round,pad=0,rounding_size=0.03", facecolor=accent, edgecolor="none", zorder=3.2)
        ax.add_patch(bar)
        h_fs = 7.7 if len(header) > 34 else 8.1
        ax.text(x + 0.14, y + h - 0.14, header, ha="left", va="center", fontsize=h_fs, fontweight="bold", color="#0F172A", zorder=3.5)
        ax.text(x + 0.14, y + h - 0.35, subheader, ha="left", va="center", fontsize=6.35, fontweight="bold", color=accent, zorder=3.5)
        if tag:
            tw = max(0.60, len(tag) * 0.058 + 0.12)
            bp = FancyBboxPatch((x + w - tw - 0.06, y + h - 0.24), tw, 0.19,
                                boxstyle="round,pad=0,rounding_size=0.04", facecolor=accent, edgecolor="none", zorder=3.4)
            ax.add_patch(bp)
            ax.text(x + w - tw / 2.0 - 0.06, y + h - 0.145, tag, ha="center", va="center", fontsize=5.6, fontweight="bold", color="#FFFFFF", zorder=3.5)
        body_h = h - 0.52
        n = len(lines)
        for i, ln in enumerate(lines):
            ly = y + h - 0.62 - i * (body_h / max(1, n))
            ax.text(x + 0.14, ly, ln, ha="left", va="center", fontsize=6.65, color="#1E293B", zorder=3.5)

    # ── TIER 1: INGESTION & STREAMING ──
    detail_box(0.45, 9.55, 3.55, 1.85, "1.1 Raw Profiling & Resolution", "raw_source.py · probe_csv_format.py · probe_full_scan.py", [
        "• Resolves <table>.parquet → <table>/*.parquet → .csv",
        "• 20k-row schema/nested probe → data/audit/csv_profile.md",
        "• Full scan country × date span → data/audit/csv_fullscan.md",
        "• Checksum verification via data/raw_csv_md5.txt"
    ], accent="#334155", tag="STEP 2")

    detail_box(0.45, 6.75, 3.55, 2.60, "1.2 Batch Contract Loader", "batch_csv_to_bronze.py · table_contracts.yml", [
        "• 11 tables (~230 GB across SG, TH, VN, 2023–2026):",
        "  - Fact Parquet: sales_detail (12.2 GB), f_member_purchase,",
        "    sales_tender_detail, all_store_selling_price",
        "  - Event Parts: tracking_ecom_events (1,774 parts, ~200 GB)",
        "  - CSV Tables: stock_availability_rate (5.4 GB), d_member",
        "    (2.0 GB), dim_item (Parquet 0.7 GB), dim_business_unit,",
        "    dim_calendar, f_member_favorite_sport",
        "• Casts join keys to VARCHAR; logs pipeline_run_metrics"
    ], accent="#475569", tag="STEP 3")

    detail_box(0.45, 3.95, 3.55, 2.60, "1.3 Optional Streaming Replay Lane", "stream_contracts.py · kafka_producer / consumer", [
        "• Redpanda broker (docker-compose.yml)",
        "• Replay producer streams 3 event tables:",
        "  sales_detail, f_member_purchase, tracking_ecom_events",
        "• Consumer enforces stream: block of table_contracts.yml",
        "• Invalid payloads routed to Dead-Letter Queue (DLQ)",
        "• Valid micro-batches written to partitioned Bronze stream"
    ], accent="#0284C7", tag="STEP 8")

    detail_box(0.45, 1.95, 3.55, 1.80, "1.4 Self-Built External Sources", "holiday_commercial_builder.py · commercial_event_names.csv", [
        "• Generates ext.public_holidays via Python holidays lib",
        "  (53 SG, 106 TH, 58 VN official holidays 2023–2026)",
        "• Loads curated ext.commercial_event_names dictionary",
        "  for naming inferred promotion peaks in Silver"
    ], accent="#7E22CE", tag="EXT DATA")

    detail_box(0.45, 0.55, 3.55, 1.20, "1.5 Zero-Copy Bronze View Binder", "bronze_views_from_parquet.py", [
        "• Registers bronze.<table> views in lakehouse.duckdb",
        "• Reads Hive-partitioned Parquet folders without copying"
    ], accent="#334155", tag="VIEWS")

    # ── TIER 2: BRONZE & PROFILING GATES ──
    detail_box(4.60, 9.15, 3.55, 2.25, "2.1 Partitioned Bronze Lakehouse", "data/bronze/<table>/ · ZSTD Parquet", [
        "• Fact tables Hive-partitioned by (country, year, month)",
        "• Partitioned COPY flush threshold = 32,768 rows",
        "  (prevents 112 GB spill on 85-country member tables)",
        "• Enables partition pruning & column projection (6.7×)",
        "• 48 dbt source schema tests on bronze.* & ext.*"
    ], accent="#334155", tag="BRONZE")

    detail_box(4.60, 7.15, 3.55, 1.80, "2.2 Malformed Row Quarantine", "quarantine.rejects_<table> (DuckDB reject_errors)", [
        "• Captures unparseable CSV rows (cut lines, delimiters)",
        "• Zero silent drops: 46 d_member & 19 dim_item rows",
        "  quarantined with raw line & error message (t11)"
    ], accent="#E11D48", bg="#FFF1F2", border="#FDA4AF", tag="REJECTS")

    detail_box(4.60, 4.55, 3.55, 2.40, "2.3 Go / No-Go Quality Gates", "sql/gates_by_country.sql → audit.gates_by_country", [
        "• Evaluated per (country × year) before Silver build:",
        "  - Gate 1: Member link rate ≥ 60% of sale lines",
        "  - Gate 2: Catalogue item match ≥ 95% (99.9%+)",
        "  - Gate 3: National price coverage ≥ 90% (97.7%+)",
        "  - Gate 4: Eligible repeat members ≥ 20,000",
        "• Decision: TH & VN = PASS (main set); SG = REVIEW"
    ], accent="#D97706", bg="#FFFBEB", border="#FCD34D", tag="STEP 4")

    detail_box(4.60, 2.30, 3.55, 2.05, "2.4 Domain & Drift Audits (QC-5)", "sql/audit_checks.sql → audit.*", [
        "• audit.volume_drift (QC-5): flags daily count ±50% vs",
        "  28d trailing same-weekday mean + holiday cause",
        "• audit.price_uniformity: store (type 7) vs country (15)",
        "• audit.stock_coverage & audit.interpurchase_gap (Δ=30,90)"
    ], accent="#B45309", bg="#FFFBEB", border="#FCD34D", tag="QC-5")

    detail_box(4.60, 0.55, 3.55, 1.55, "2.5 Stream Reconciliation (QC-7)", "qc7_stream_reconciliation.py → audit.stream_reconciliation", [
        "• Reconciles batch vs stream Bronze per (table, country, day)",
        "• Verifies exact row_count match & ordered key/payload hash"
    ], accent="#0D9488", bg="#F0FDFA", border="#99F6E4", tag="QC-7")

    # ── TIER 3: SILVER DOMAIN LAYER ──
    detail_box(8.75, 9.25, 4.05, 2.15, "3.1 Transactions, Netting & Returns", "stg_sales_detail → slv_sales_line_netted → slv_fact_sales_line", [
        "• stg_sales_detail: projects 25/141 cols, applies country/date vars",
        "• slv_sales_line_netted: exact dedup + latest version_at + signed",
        "  sale − cancel netting per (transaction_id, item_code)",
        "• slv_fact_sales_line: positive SALE lines, merchandise in catalogue,",
        "  store/country timezone → naive UTC, local → EUR conversion",
        "• slv_fact_returns: return lines matched to original sale tx"
    ], accent="#1D4ED8", tag="SALES & TZ")

    detail_box(8.75, 7.00, 4.05, 2.05, "3.2 Catalogue, Pricing & Enriched Calendar", "slv_dim_model · slv_price_sku_interval · slv_calendar_enriched", [
        "• slv_dim_model: SKU→model_code; drops UUIDs, services & FIXT & FURNIT",
        "• slv_price_sku_interval: national SKU intervals (type 15, fallback 50),",
        "  maps 4 price_types → promo_kind; depth > 90% → qrt_price_interval",
        "• slv_calendar_enriched: O(N+D) difference-array promo share; ≥3 peak",
        "  days (≥1.5σ & ≥0.2% floor) named via dictionary + public holidays"
    ], accent="#2563EB", tag="CAT & CAL")

    detail_box(8.75, 4.75, 4.05, 2.05, "3.3 Web Clickstream & Identity Stitching", "stg_tracking_ecom_events → slv_web_events_clean → slv_user_to_member", [
        "• slv_web_events_clean: extracts STRUCT/LIST paths, keeps numeric model",
        "  codes, filters is_event_to_use = true (1.0B raw → clean product events)",
        "• slv_user_member_links: Tier 1 ORDER match + Tier 2 LOGIN event",
        "• slv_user_to_member: keeps 1:1 cookies with earliest identity_verified_ts;",
        "  multi-member cookies → slv_identity_conflicts; audit.stitching_coverage"
    ], accent="#7E22CE", tag="STITCHING")

    detail_box(8.75, 2.55, 4.05, 2.00, "3.4 Member State, Sport & Daily Stock", "slv_member_bridge · slv_member_profile · slv_member_sport_asof · store_daily", [
        "• slv_member_bridge: earliest member_id per tx; slv_member_profile: consumer",
        "  accounts only (excludes staff, B2B, legal entity, club, school)",
        "• slv_member_sport_asof: add/remove events → [valid_from, valid_to) intervals",
        "• slv_member_store_daily: running modal store per member × purchase day",
        "• slv_stock_daily_model / _national: ≤3d forward-fill (behind vars.use_stock)"
    ], accent="#0284C7", tag="STATE ASOF")

    detail_box(8.75, 0.55, 4.05, 1.80, "3.5 Silver Quarantine & Gates (QC-1 … QC-4)", "qrt_sales_line · qrt_price_interval · slv_identity_conflicts", [
        "• qrt_sales_line routes refused lines with 6 explicit reasons (NON_MERCHANDISE,",
        "  NET_ZERO_OR_NEGATIVE, NON_SALE_TX, UNMAPPED_ITEM…)",
        "• Block tests on null keys (QC-1), RI (QC-2), domains (QC-3), unique keys (QC-4)"
    ], accent="#E11D48", bg="#FFF1F2", border="#FDA4AF", tag="QC-1..4")

    # ── TIER 4: GOLD FEATURE STORE & CANDIDATES ──
    detail_box(13.40, 9.55, 4.25, 1.85, "4.1 Temporal Anchor Grid & Aux Tables", "build_anchor_grid.py · gld_web_stitched · gld_copurchase_lift · sport_affinity", [
        "• anchor_grid: eligible (member, Monday) in split.yml (42d purge gaps),",
        "  requires non-returned purchase in 90d, 4× train stride, 50k/15k/50k cap",
        "• anchor_model_grid: active models (±90d) per (country, anchor_date)",
        "• Pre-validation (< valid_lo) gld_copurchase_lift & gld_sport_department_affinity"
    ], accent="#4338CA", tag="STEP 6A")

    detail_box(13.40, 7.15, 4.25, 2.20, "4.2 Entity 1 & Entity 2 Feature Stores (< t)", "gld_fs_member (Entity 1) · gld_fs_model_country (Entity 2)", [
        "• gld_fs_member (member, anchor): F0 purchase RFM (30/90/365d, return_rate),",
        "  F1 price quantiles (q25/q50/q75, promo_affinity), F3 web sessions/models",
        "  (verified_ts ≤ t, web_data_available flag), ASOF sport & usual store",
        "• gld_fs_model_country (model, country, anchor): ASOF SKU median price,",
        "  promo_depth, calendar (in_commercial_event, holiday gap), 28d popularity"
    ], accent="#CA8A04", tag="ENTITIES 1 & 2")

    detail_box(13.40, 4.85, 4.25, 2.10, "4.3 Candidate Generation (Top 200 / Anchor)", "gld_candidates (filtered to anchor_model_grid, priority R1 > R3 > R2 > R4 > R5)", [
        "• R1 Repurchase: member's past models prior to anchor_date",
        "• R2 Co-purchase: top lift partners of member's last-90d basket",
        "• R3 Web Intent: models viewed/carted in last 30d (verified_ts ≤ anchor)",
        "• R4 Sport × Offer: active favourite sports → top affinity depts → popular models",
        "• R5 National Best-Sellers: top-300 models by buyers in trailing 28 days"
    ], accent="#D97706", tag="R1 – R5")

    detail_box(13.40, 2.55, 4.25, 2.10, "4.4 Entity 3 Pair Features & Ranking Set", "gld_fs_pair (Entity 3) → gld_ranking_dataset", [
        "• gld_fs_pair (member, model, anchor): joins Entity 1 + Entity 2 + pair",
        "  signals: F2 model repurchase count/recency & ASOF dept purchase cycle,",
        "  F4 basket co-purchase lift max/mean, F5 member-to-model price ratio,",
        "  F3 model web views/carts (7d/30d), Sport×Dept affinity score",
        "• gld_ranking_dataset: attaches non-returned labels label_30 & label_90"
    ], accent="#A16207", tag="ENTITY 3 & LABELS")

    detail_box(13.40, 0.55, 4.25, 1.80, "4.5 Point-in-Time Ledger (QC-6) & Recall", "quarantine.leakage_violations · audit.candidate_recall · 6 singular tests", [
        "• Every Gold entity tracks last_source_ts; QC-6 asserts last_source_ts ≤ anchor",
        "  and identity_verified_ts ≤ anchor across all Gold tables (0 violations, 64 PASS)",
        "• audit.candidate_recall measures Recall@K per source R1–R5 & union@200"
    ], accent="#BE123C", bg="#FFF1F2", border="#FDA4AF", tag="QC-6 LEDGER")

    # ── TIER 5: EVALUATION & ABLATION ──
    detail_box(18.25, 9.25, 3.30, 2.15, "5.1 Fixed LambdaRank Instrument", "train_eval_lambdarank.py · split.yml", [
        "• LightGBM LambdaRank grouped by (member, anchor)",
        "• Early stopping on Validation NDCG@20",
        "• Hyper-parameters tuned once on Full config,",
        "  then frozen across all ablation arms",
        "• Primary horizon Δ = 30d; secondary Δ = 90d"
    ], accent="#0F766E", tag="STEP 7A")

    detail_box(18.25, 6.45, 3.30, 2.60, "5.2 Two-Axis Ablation Engine", "run_ablation_2axes.py · ablation_configs.yml", [
        "• Baseline B0 (R1+R2+Pop, F0+F2+F4) vs Full",
        "• Axis 1 — Feature Groups (dbt rebuilds):",
        "  −F1 (Price), −F3 (Web), −F5 (Price/Calendar), −Sport",
        "• Axis 2 — Candidate Sources (−R1 … −R5):",
        "  Removed source candidates kept in test pool",
        "  with score = −∞ (prevents denominator inflation)"
    ], accent="#0D9488", tag="STEP 7B")

    detail_box(18.25, 4.10, 3.30, 2.15, "5.3 Bootstrap CI & Cost × Gain", "bootstrap_ci.py · pipeline_cost_profiler.py", [
        "• Metrics: HR@10/20, MRR@10/20, NDCG@10/20,",
        "  Recall@50, Catalog Coverage",
        "• 500× member-clustered bootstrap 95% CI on",
        "  paired Δ(Full − Arm) for TH+VN and SG",
        "• Joins ΔNDCG@20 with wall-time & RSS cost"
    ], accent="#0891B2", tag="MT3 COST×GAIN")

    detail_box(18.25, 2.15, 3.30, 1.75, "5.4 Scale & Technique Comparisons", "scale_test.py · technique_comparisons.py", [
        "• Scale: 1→2→3 countries; 3→12→36 months",
        "• 4 A/B benchmarks: Parquet vs CSV (6.6×),",
        "  Projection (6.7×), ASOF vs Explode (1.3×, ½ RAM),",
        "  SQL Regex vs Python UDF (2.9×)"
    ], accent="#4F46E5", tag="BENCHMARKS")

    detail_box(18.25, 0.55, 3.30, 1.40, "5.5 Automated Report Packaging", "tools/report_tables.py · tools/lineage_graph.py", [
        "• Generates 21 Markdown/CSV tables (t01–t21)",
        "• Applies REDACT_TERMS privacy check"
    ], accent="#334155", tag="STEP 9")

    # Tier-to-tier connectors
    connectors = [(4.15, 4.45), (8.30, 8.60), (12.95, 13.25), (17.80, 18.10)]
    for x1, x2 in connectors:
        for cy in (10.3, 7.8, 5.4, 3.1, 1.3):
            ax.plot([x1, x2 - 0.08], [cy, cy], color="#334155", lw=2.0, zorder=4)
            draw_arrowhead(ax, x2, cy, 1.0, 0.0, "#334155", size=0.13, zorder=4.2)

    for fmt in ("svg", "png"):
        fig.savefig(OUT / f"architecture_detailed.{fmt}", dpi=260 if fmt == "png" else None, bbox_inches="tight", pad_inches=0.20, facecolor="#FFFFFF")
    plt.close(fig)
    print("→ docs/figures/architecture_detailed.svg / .png  (detailed system & data-flow architecture)")


# ══════════════════════════════════════════════════════════════════════════════
# 6. INGESTION & BRONZE LAYER DIAGRAM (lineage_ingestion_to_bronze.{svg,png})
# ══════════════════════════════════════════════════════════════════════════════
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
        ax.text(cx + w / 2.0, 8.35, ctitle, ha="center", va="center", fontsize=8.6, fontweight="bold", color=ccol, zorder=2.5)
        ax.text(cx + w / 2.0, 8.10, csub, ha="center", va="center", fontsize=7.0, color="#334155", zorder=2.5)

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
        ax.text(cx + w / 2.0, 8.35, ctitle, ha="center", va="center", fontsize=8.6, fontweight="bold", color=ccol, zorder=2.5)
        ax.text(cx + w / 2.0, 8.10, csub, ha="center", va="center", fontsize=7.0, color="#334155", zorder=2.5)

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
    o3 = ecard(3, 2.65, 1.45, "Scale & Technique Benchmarks", "scale_test.py (1→3 countries, 3→36 months)", "technique_comparisons.py (Parquet, Pushdown, ASOF)", "python", "SCALE & A/B")
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
    print("→ docs/figures/lineage_gold_to_evaluation.svg / .png  (Gold → Evaluation & Ablation detail)")


if __name__ == "__main__":
    build_architecture_overview()
    build_architecture_detailed()
    build_lineage_full()
    build_lineage_bronze_to_silver()
    build_lineage_silver_to_gold()
    build_lineage_ingestion_to_bronze()
    build_lineage_gold_to_evaluation()
