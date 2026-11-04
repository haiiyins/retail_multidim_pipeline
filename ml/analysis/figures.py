"""Figures of the HMTT report and slides from the ML report tables (data/ml/report/ or docs/report/tables/ml/), written to docs/figures/ml/.

fig_t28b_errors     where the test positives of P1-frozen end up (top 10 / rank 11+ / capped / no source), repeat vs explore
fig_t30_curve       unconditional candidate coverage against the list size K (test, TH + VN), all and explore positives
fig_t31_ndcg        NDCG@20 with 95 % member-bootstrap intervals of every t31 model (test, TH + VN)
fig_t32_ablation    paired differences of the P3 variants against P3 two heads (NDCG@20, recall_explore@20)
fig_t31_seeds       NDCG@20 of the three seeds of P1-tuned and P3
fig_arch            the two-stage system (feature store → candidate sources → mixer → rankers → unconditional evaluation)
fig_pit_timeline    point-in-time rolling refits (13 quarterly cutoffs) vs single ranker fit with 42-day purge gaps
fig_rankers_compare comparison of the three two-stage rankers (P1-tuned, P2 stacked, P3 UMTR)
fig_p3_arch         architecture of the deep ranker P3 (UMTR) with two-head + gate vs single-head scoring
Usage: python ml/analysis/figures.py"""
import io, os, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ROOT, ml_path

OUT = ROOT / "docs" / "figures" / "ml"
TABLES_FALLBACK = ROOT / "docs" / "report" / "tables" / "ml"
MAIN = "MAIN (TH+VN)"
LABELS = {"ptopfreq": "P-TopFreq", "gptopfreq": "GP-TopFreq", "ease_nbr": "EASE NBR", "tifuknn_nbr": "TIFU-KNN NBR",
          "sasrec_nbr": "SASRec NBR", "sasrec_all_nbr": "SASRec NBR (all targets)", "p1_frozen": "P1-frozen (R1–R5)",
          "p1_frozen_v2": "P1-frozen (v2)", "p1_frozen_allfeat_v2": "P1-frozen (v2, 85 features)",
          "p1_tuned_v2": "P1-tuned", "p2_v2": "P2", "p3_full": "P3 two heads", "p3_onehead": "P3 one head",
          "p3_fixedgate": "P3 fixed gate", "p3_noseq": "P3 no sequence"}
CELLS = [("top10", "top 10", "#2b8a3e"), ("rank_11_plus", "rank 11+", "#94d82d"), ("out_capped", "cut by the cap", "#fab005"),
         ("out_no_source", "no source", "#e03131")]


def report_md_path(name):
    p = ml_path("report", f"{name}.md")
    return p if os.path.exists(p) else str(TABLES_FALLBACK / f"{name}.md")


def md_tables(name):
    """Every Markdown table of data/ml/report/<name>.md (or docs/report/tables/ml/<name>.md) as a DataFrame, in order."""
    tables, block = [], []
    for line in open(report_md_path(name), encoding="utf-8").read().splitlines() + [""]:
        if line.startswith("|"):
            if not re.match(r"^\|[\s:|-]+\|$", line):
                block.append(line.strip("|"))
        elif block:
            df = pd.read_csv(io.StringIO("\n".join(block)), sep="|", skipinitialspace=True)
            df.columns = [c.strip() for c in df.columns]
            tables.append(df.apply(lambda s: s.str.strip() if pd.api.types.is_string_dtype(s) else s))
            block = []
    return tables


def read_report_table(name):
    p = ml_path("report", f"{name}.csv")
    if os.path.exists(p):
        return pd.read_csv(p)
    df = md_tables(name)[0].copy()
    if "scope" not in df.columns:
        df["scope"] = MAIN
    for col in df.columns:
        if col not in ("model", "scope", "NDCG@20 95% CI", "a", "b", "metric", "kind"):
            df[col] = pd.to_numeric(df[col], errors="ignore")
    return df


def save(fig, name):
    fig.tight_layout()
    fig.savefig(OUT / f"{name}.png", dpi=160)
    plt.close(fig)
    print(f"docs/figures/ml/{name}.png")


def errors():
    kinds, total = md_tables("t28b_p1_frozen_d30")[:2]
    df = pd.concat([kinds.set_index("kind"), total.rename(columns={"all": "kind"}).set_index("kind")])
    df = df.loc[["repeat", "explore", "ALL"]].rename(index={"ALL": "all"})
    fig, ax = plt.subplots(figsize=(7, 2.6))
    left = pd.Series(0.0, index=df.index)
    for col, label, color in CELLS:
        ax.barh(df.index, df[col], left=left, color=color, label=label)
        for k in df.index:
            if df.loc[k, col] > 0.06:
                ax.text(left[k] + df.loc[k, col] / 2, k, f"{df.loc[k, col]:.0%}", ha="center", va="center", fontsize=8)
        left += df[col]
    ax.set_yticks(range(len(df)), [f"{k} ({int(n):,})" for k, n in df["positives"].items()])
    ax.invert_yaxis()
    ax.set_xlim(0, 1)
    ax.set_xlabel("share of test positives (P1-frozen, R1–R5 candidates, Δ = 30)")
    ax.legend(ncol=4, fontsize=8, loc="upper center", bbox_to_anchor=(0.5, 1.3), frameon=False)
    save(fig, "fig_t28b_errors")


def curve():
    df = md_tables("t30_curve")[0]
    df = df[(df["split"] == "test") & (df["scope"] == MAIN)].copy()
    df["policy"] = df["source"].str.replace(r"@\d+$", "", regex=True)
    df[["K", "cand", "cand_explore"]] = df[["K", "cand", "cand_explore"]].astype(float)
    names = {"mix_fixed": "mixer, fixed quotas (candidates_v2)", "mix_per_member": "mixer, per-member quotas", "R1-R5": "R1–R5 only"}
    fig, axes = plt.subplots(1, 2, figsize=(9, 3.4), sharex=True)
    for ax, col, title in ((axes[0], "cand", "all positives"), (axes[1], "cand_explore", "explore positives")):
        for policy, g in df.groupby("policy"):
            g = g.sort_values("K")
            ax.plot(g["K"], g[col], marker="o", label=names.get(policy, policy), ls="--" if policy == "R1-R5" else "-")
        ax.axvline(300, color="grey", lw=0.8, ls=":")
        ax.set_title(title, fontsize=10)
        ax.set_xlabel("candidates per anchor (K)")
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("coverage (test, TH + VN)")
    axes[0].legend(fontsize=8)
    save(fig, "fig_t30_curve")


def ndcg():
    df = read_report_table("t31")
    df = df[df["scope"] == MAIN].copy()
    df[["lo", "hi"]] = df["NDCG@20 95% CI"].str.strip("[]").str.split(",", expand=True).astype(float)
    df = df.sort_values("NDCG@20")
    color = ["#868e96" if m.endswith("nbr") or "topfreq" in m else "#1c7ed6" if m.startswith("p1") or m.startswith("p2")
             else "#ae3ec9" for m in df["model"]]
    fig, ax = plt.subplots(figsize=(7, 4))
    y = range(len(df))
    ax.barh(y, df["NDCG@20"], color=color)
    ax.errorbar(df["NDCG@20"], y, xerr=[df["NDCG@20"] - df["lo"], df["hi"] - df["NDCG@20"]], fmt="none", ecolor="black", capsize=2)
    for i, v in zip(y, df["NDCG@20"]):
        ax.text(v + 0.0035, i, f"{v:.4f}", va="center", fontsize=8)
    ax.set_yticks(list(y), [LABELS.get(m, m) for m in df["model"]])
    ax.set_xlim(0, df["hi"].max() * 1.12)
    ax.set_xlabel("NDCG@20, unconditional (test, TH + VN, Δ = 30), 95 % member bootstrap")
    save(fig, "fig_t31_ndcg")


def ablation():
    df = read_report_table("t32_paired")
    metrics = ["NDCG@20", "recall_explore@20", "recall_repeat@20"]
    fig, axes = plt.subplots(1, 3, figsize=(10, 2.6), sharey=True)
    for ax, m in zip(axes, metrics):
        g = df[df["metric"] == m]
        y = range(len(g))
        ax.errorbar(g["diff"], y, xerr=[g["diff"] - g["ci_lo"], g["ci_hi"] - g["diff"]], fmt="o", color="#ae3ec9", capsize=3)
        ax.axvline(0, color="grey", lw=0.8)
        ax.set_yticks(list(y), [LABELS.get(a, a) for a in g["a"]])
        ax.set_title(f"Δ {m}", fontsize=10)
        ax.grid(alpha=0.3, axis="x")
    axes[0].invert_yaxis()
    fig.suptitle("P3 variant − P3 two heads (paired member bootstrap, test, TH + VN)", fontsize=10)
    save(fig, "fig_t32_ablation")


def seeds():
    df = read_report_table("t31_seeds")
    df = df[df["scope"] == MAIN].copy()
    df["family"] = df["model"].str.replace(r"_seed\d$", "", regex=True)
    order = ["p1_tuned_v2", "p3_full", "p3_onehead"]
    fig, ax = plt.subplots(figsize=(6, 2.4))
    for i, f in enumerate(order):
        g = df[df["family"] == f]
        ax.scatter(g["NDCG@20"], [i] * len(g), s=40, color="#1c7ed6" if f.startswith("p1") else "#ae3ec9", zorder=3)
        ax.plot([g["NDCG@20"].mean()] * 2, [i - 0.25, i + 0.25], color="black", lw=1.5)
    ax.set_yticks(range(len(order)), [LABELS[f] for f in order])
    ax.xaxis.set_major_locator(matplotlib.ticker.MaxNLocator(5))
    ax.xaxis.set_major_formatter(matplotlib.ticker.FormatStrFormatter("%.4f"))
    ax.set_xlabel("NDCG@20 (test, TH + VN), seeds 0 / 1 / 2; bar = mean")
    ax.grid(alpha=0.3, axis="x")
    save(fig, "fig_t31_seeds")


def arch():
    boxes = {   # name: (x, y, width, text, colour)
        "fs": (0.0, 1.2, 2.2, "Feature store\nBronze / Silver / Gold\nQC-1…7, point in time", "#e9ecef"),
        "rules": (2.8, 2.1, 2.2, "Rules R1–R5\nrepurchase, co-purchase,\nweb, best-sellers", "#ffe8cc"),
        "learned": (2.8, 0.3, 2.2, "Learned R6–R13\nexplore-only,\nquarterly refits", "#ffc078"),
        "mix": (5.6, 1.2, 1.6, "Mixer\nrank quotas\nK = 300", "#fff3bf"),
        "rank": (7.8, 1.2, 2.2, "Rankers\nP1 GBDT, P2 stacking,\nP3 two heads + gate", "#d0ebff"),
        "eval": (10.6, 1.2, 2.0, "Unconditional\nevaluation,\nrepeat / explore", "#d3f9d8"),
    }
    h = 1.2
    fig, ax = plt.subplots(figsize=(9, 2.6))
    for x, y, w, text, colour in boxes.values():
        ax.add_patch(matplotlib.patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.05", fc=colour, ec="#495057"))
        ax.text(x + w / 2, y + h / 2, text, ha="center", va="center", fontsize=8)

    def arrow(a, b):
        xa, ya, wa = boxes[a][:3]
        xb, yb, _ = boxes[b][:3]
        ax.annotate("", xy=(xb, yb + h / 2), xytext=(xa + wa, ya + h / 2),
                    arrowprops=dict(arrowstyle="-|>", color="#495057", lw=1.2, shrinkA=2, shrinkB=2))

    for a, b in (("fs", "rules"), ("fs", "learned"), ("rules", "mix"), ("learned", "mix"), ("mix", "rank"), ("rank", "eval")):
        arrow(a, b)
    ax.annotate("", xy=(8.9, 1.15), xytext=(1.1, 1.15), arrowprops=dict(arrowstyle="-|>", color="#adb5bd", lw=1, ls="--",
                connectionstyle="arc3,rad=0.3", shrinkA=2, shrinkB=2))
    ax.text(5.0, -0.55, "pair features", fontsize=7, color="#868e96", ha="center")
    ax.set_xlim(-0.1, 12.7)
    ax.set_ylim(-0.8, 3.4)
    ax.axis("off")
    save(fig, "fig_arch")


def _card(ax, x, y, w, h, title, lines, fill="#F8FAFC", border="#64748B", accent="#334155", title_fs=8.6, body_fs=7.6):
    sh = FancyBboxPatch((x + 0.04, y - 0.05), w, h, boxstyle="round,pad=0,rounding_size=0.10",
                        facecolor="#0F172A", edgecolor="none", alpha=0.06, zorder=1)
    ax.add_patch(sh)
    box = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.10",
                         facecolor=fill, edgecolor=border, linewidth=1.2, zorder=2)
    ax.add_patch(box)
    bar = FancyBboxPatch((x, y + h - 0.30), w, 0.30, boxstyle="round,pad=0,rounding_size=0.10",
                         facecolor=accent, edgecolor="none", zorder=3)
    ax.add_patch(bar)
    ax.text(x + w / 2, y + h - 0.15, title, color="white", fontsize=title_fs, fontweight="bold", va="center", ha="center", zorder=4)
    top = y + h - 0.46
    step = (h - 0.38) / max(len(lines), 1)
    for idx, line in enumerate(lines):
        ax.text(x + 0.14, top - idx * step, line, color="#1E293B", fontsize=body_fs, va="top", ha="left", zorder=4)


def pit_timeline():
    fig, ax = plt.subplots(figsize=(8.6, 2.75))
    ax.set_xlim(-0.2, 11.4)
    ax.set_ylim(0.0, 3.6)
    ax.axis("off")

    # Lane 1: Splits and 42-day purge gaps
    ax.text(-0.1, 2.92, "Anchor splits\n& purge gaps", fontsize=8.4, fontweight="bold", color="#0F172A", va="center")
    splits = [
        (1.65, 3.55, "Train anchors\n≤ 2025-09-15 (50k/country)", "#DBEAFE", "#2563EB"),
        (5.28, 0.88, "42d\npurge", "#FEE2E2", "#DC2626"),
        (6.24, 1.55, "Valid anchors\n10-27 .. 12-22", "#FEF3C7", "#D97706"),
        (7.87, 0.88, "42d\npurge", "#FEE2E2", "#DC2626"),
        (8.83, 2.40, "Test anchors\n2026-02-02 .. 07-27", "#DCFCE7", "#16A34A"),
    ]
    for x, w, label, fc, ec in splits:
        b = FancyBboxPatch((x, 2.54), w, 0.76, boxstyle="round,pad=0,rounding_size=0.07", facecolor=fc, edgecolor=ec, lw=1.15)
        ax.add_patch(b)
        ax.text(x + w / 2, 2.92, label, ha="center", va="center", fontsize=7.6, color="#0F172A",
                fontweight="bold" if "purge" not in label else "normal")

    # Lane 2: 13 Quarterly rolling cutoffs (R6-R13 + P2 signals)
    ax.text(-0.1, 1.66, "Quarterly refits\n(R6–R13, P2)", fontsize=8.4, fontweight="bold", color="#0F172A", va="center")
    ax.plot([1.65, 11.23], [1.66, 1.66], color="#475569", lw=1.5, zorder=1)
    xs = [1.65 + i * (11.23 - 1.65) / 12.0 for i in range(13)]
    labels_q = ["23Q3", "23Q4", "24Q1", "24Q2", "24Q3", "24Q4", "25Q1", "25Q2", "25Q3", "25Q4", "26Q1", "26Q2", "26Q3"]
    for x, lq in zip(xs, labels_q):
        ax.scatter([x], [1.66], s=36, color="#D97706", edgecolor="white", lw=0.9, zorder=3)
        ax.text(x, 1.38, lq, ha="center", va="top", fontsize=7.0, color="#334155")
    ax.text(6.44, 1.94, "13 quarterly cutoffs (2023-07-01 .. 2026-07-01): fit strictly before c (t + Δ < c); anchor t uses latest c ≤ t",
            ha="center", va="bottom", fontsize=7.6, color="#78350F")

    # Lane 3: Ranker fit once + QC-6 rule
    ax.text(-0.1, 0.58, "Ranker fit &\nQC-6 check", fontsize=8.4, fontweight="bold", color="#0F172A", va="center")
    b_rk = FancyBboxPatch((1.65, 0.20), 3.55, 0.74, boxstyle="round,pad=0,rounding_size=0.07",
                          facecolor="#E0E7FF", edgecolor="#4F46E5", lw=1.15)
    ax.add_patch(b_rk)
    ax.text(3.425, 0.57, "P1 / P2 / P3 fitted ONCE on train\n(FINAL_CUTOFF = 2025-09-16)",
            ha="center", va="center", fontsize=7.5, fontweight="bold", color="#1E1B4B")

    b_qc = FancyBboxPatch((5.65, 0.20), 5.58, 0.74, boxstyle="round,pad=0,rounding_size=0.07",
                          facecolor="#F1F5F9", edgecolor="#64748B", lw=1.15)
    ax.add_patch(b_qc)
    ax.text(8.44, 0.57, "QC-6 assertions on every row: source_ts_max < anchor_date\nand fit_cutoff ≤ anchor_date (0 violations across all splits)",
            ha="center", va="center", fontsize=7.5, color="#0F172A")
    ax.annotate("", xy=(5.62, 0.57), xytext=(5.23, 0.57),
                arrowprops=dict(arrowstyle="-|>", color="#4F46E5", lw=1.3))
    save(fig, "fig_pit_timeline")


def rankers_compare():
    fig, ax = plt.subplots(figsize=(9.2, 3.05))
    ax.set_xlim(0.0, 11.4)
    ax.set_ylim(0.0, 3.65)
    ax.axis("off")

    top_b = FancyBboxPatch((0.20, 2.94), 11.0, 0.56, boxstyle="round,pad=0,rounding_size=0.08",
                           facecolor="#FEF9C3", edgecolor="#CA8A04", lw=1.15)
    ax.add_patch(top_b)
    ax.text(5.70, 3.22, "Shared pool: candidates_v2 (K = 300/anchor) · 44,795 positive train anchors · 10 TPE trials on unconditional valid NDCG@20",
            ha="center", va="center", fontsize=8.0, fontweight="bold", color="#422006")

    _card(ax, 0.20, 0.16, 3.45, 2.52, "P1-tuned (GBDT Trees)",
          ["• 85 Gold pair features",
           "  (73 v1 + 12 v2 incl. R6–R13 ranks)",
           "• Drops IDs, labels & PIT metadata",
           "• Categorical: country, promo_kind",
           "• Loss: LightGBM LambdaRank@20",
           "• Test NDCG@20: 0.1011"],
          fill="#EFF6FF", border="#2563EB", accent="#1D4ED8")

    _card(ax, 3.975, 0.16, 3.45, 2.52, "P2 (Stacked GBDT + Signals)",
          ["• 85 pair cols + 5 rolling signals",
           "• Dept hazard: P(buy dept in Δ=30d)",
           "• WTP q50 (median log-price) &",
           "  q90 (max log-price) + price gaps",
           "• Loss: LightGBM LambdaRank@20",
           "• Test NDCG@20: 0.1013 (+0.0002)"],
          fill="#F0FDFA", border="#0D9488", accent="#0F766E")

    _card(ax, 7.75, 0.16, 3.45, 2.52, "P3 (UMTR Deep · 3.7M params)",
          ["• Last 50 purchases + 84 dense cols",
           "  (signed-log + 16 NaN flags = 100)",
           "• Shared model emb + target attn",
           "• Two heads + gate g(u) vs One head",
           "• Loss: Listwise NLL + λ_90 + λ_g",
           "• Test NDCG@20: 0.1020 (one head)"],
          fill="#FAF5FF", border="#9333EA", accent="#7E22CE")

    for x in (1.925, 5.70, 9.475):
        ax.annotate("", xy=(x, 2.70), xytext=(x, 2.93),
                    arrowprops=dict(arrowstyle="-|>", color="#64748B", lw=1.3))
    save(fig, "fig_rankers_compare")


def p3_arch():
    fig, ax = plt.subplots(figsize=(11.2, 3.55))
    ax.set_xlim(0.0, 14.6)
    ax.set_ylim(0.0, 4.4)
    ax.axis("off")

    # Column 1: Inputs
    _card(ax, 0.15, 2.30, 3.15, 1.92, "1. Sequence Input (A, 50)",
          ["• Last L = 50 purchase lines",
           "  (member × model × day)",
           "• Shared model emb e(m_l)",
           "• Log2 recency gap emb g(Δt_l)",
           "• Reverse position emb p(L-1-l)"],
          fill="#EFF6FF", border="#2563EB", accent="#1D4ED8")

    _card(ax, 0.15, 0.16, 3.15, 1.92, "2. Candidate Input (A, 300, 100)",
          ["• K = 300 candidates / anchor",
           "• 84 dense cols (excl. country)",
           "  signed-log + z-score + 16 NaN flags",
           "• Shared model emb e(m_k)",
           "• Sport department emb d(dept_k)"],
          fill="#FEF9C3", border="#CA8A04", accent="#A16207")

    # Column 2: Towers
    _card(ax, 3.75, 2.30, 3.25, 1.92, "3. Sequence & User Tower (u)",
          ["• Bidirectional Transformer",
           "  (2 blocks, 2 heads, Pre-LN)",
           "• Sequence states h_1..h_L",
           "• Context c = MLP_ctx(x[:, 0])",
           "• u = MLP_user([mean(h), h_last, c])"],
          fill="#E0E7FF", border="#4F46E5", accent="#3730A3")

    _card(ax, 3.75, 0.16, 3.25, 1.92, "4. Item Tower & Target Attn",
          ["• Pair MLP: f_k = MLP_feat(x_k)",
           "• Item vector:",
           "  v_k = MLP_item([e_k, d_k, f_k])",
           "• Scaled dot-product target attn:",
           "  a_k = softmax(v_k h_l^T / √d) h_l"],
          fill="#DCFCE7", border="#16A34A", accent="#15803D")

    # Column 3: Interaction
    _card(ax, 7.45, 1.15, 3.00, 2.15, "5. Candidate Interaction (h_k)",
          ["• Feature fusion per candidate k:",
           "  [u, v_k, a_k, u ⊙ v_k] ∈ R^{4d}",
           "• Interaction MLP:",
           "  h_k = MLP([u, v_k, a_k, u ⊙ v_k])",
           "• Aux Δ=90 head: σ(w_aux^T h_k)"],
          fill="#F3E8FF", border="#9333EA", accent="#6B21A8")

    # Column 4: Output modes
    _card(ax, 10.90, 2.30, 3.55, 1.92, "6a. Two-Head + Gate (p3_full)",
          ["• Split R_a (hist_buy_cnt>0) vs E_a",
           "• Within-group softmaxes P_rep, P_exp",
           "• Gate g(u) = σ(w_g^T u) + BCE(g, y_rep)",
           "• p(k) = g·P_rep(k) or (1-g)·P_exp(k)",
           "• Test NDCG@20: 0.1009"],
          fill="#FFE4E6", border="#E11D48", accent="#BE123C")

    _card(ax, 10.90, 0.16, 3.55, 1.92, "6b. Single-Head Mode (p3_onehead)",
          ["• Single linear logit s_k = w^T h_k",
           "• One listwise softmax over all K:",
           "  p(k) = exp(s_k) / Σ_{j∈C_a} exp(s_j)",
           "• No repeat/explore split or gate",
           "• Best Test NDCG@20: 0.1020 (+1% vs P1)"],
          fill="#CCFBF1", border="#0D9488", accent="#0F766E")

    # Arrows
    arr = dict(arrowstyle="-|>", color="#334155", lw=1.3, shrinkA=2, shrinkB=2)
    ax.annotate("", xy=(3.75, 3.26), xytext=(3.30, 3.26), arrowprops=arr)
    ax.annotate("", xy=(3.75, 1.12), xytext=(3.30, 1.12), arrowprops=arr)
    # x[:, 0] to User Tower context
    ax.annotate("", xy=(3.75, 2.75), xytext=(3.30, 1.55),
                arrowprops=dict(arrowstyle="-|>", color="#CA8A04", lw=1.1, ls="--", shrinkA=2, shrinkB=2))
    # h_1..h_L to Target Attention
    ax.annotate("", xy=(5.375, 2.08), xytext=(5.375, 2.30),
                arrowprops=dict(arrowstyle="-|>", color="#4F46E5", lw=1.2, shrinkA=2, shrinkB=2))
    # Towers to Interaction
    ax.annotate("", xy=(7.45, 2.65), xytext=(7.00, 3.15), arrowprops=arr)
    ax.annotate("", xy=(7.45, 1.75), xytext=(7.00, 1.25), arrowprops=arr)
    # Interaction to Heads
    ax.annotate("", xy=(10.90, 3.26), xytext=(10.45, 2.55), arrowprops=arr)
    ax.annotate("", xy=(10.90, 1.12), xytext=(10.45, 1.85), arrowprops=arr)
    save(fig, "fig_p3_arch")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (errors, curve, ndcg, ablation, seeds, arch, pit_timeline, rankers_compare, p3_arch):
        f()


if __name__ == "__main__":
    sys.exit(main())
