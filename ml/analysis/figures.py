"""Figures of the HMTT report and slides from the ML report tables (data/ml/report/), written to docs/figures/ml/.

fig_t28b_errors     where the test positives of P1-frozen end up (top 10 / rank 11+ / capped / no source), repeat vs explore
fig_t30_curve       unconditional candidate coverage against the list size K (test, TH + VN), all and explore positives
fig_t31_ndcg        NDCG@20 with 95 % member-bootstrap intervals of every t31 model (test, TH + VN)
fig_t32_ablation    paired differences of the P3 variants against P3 two heads (NDCG@20, recall_explore@20)
fig_t31_seeds       NDCG@20 of the three seeds of P1-tuned and P3
fig_arch            the two-stage system (feature store → candidate sources → mixer → rankers → unconditional evaluation)
Usage: python ml/analysis/figures.py"""
import io, os, re, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ROOT, ml_path

OUT = ROOT / "docs" / "figures" / "ml"
MAIN = "MAIN (TH+VN)"
LABELS = {"ptopfreq": "P-TopFreq", "gptopfreq": "GP-TopFreq", "ease_nbr": "EASE NBR", "tifuknn_nbr": "TIFU-KNN NBR",
          "sasrec_nbr": "SASRec NBR", "p1_frozen": "P1-frozen (R1–R5)", "p1_frozen_v2": "P1-frozen (v2)",
          "p1_tuned_v2": "P1-tuned", "p2_v2": "P2", "p3_full": "P3 two heads", "p3_onehead": "P3 one head",
          "p3_fixedgate": "P3 fixed gate", "p3_noseq": "P3 no sequence"}
CELLS = [("top10", "top 10", "#2b8a3e"), ("rank_11_plus", "rank 11+", "#94d82d"), ("out_capped", "cut by the cap", "#fab005"),
         ("out_no_source", "no source", "#e03131")]


def md_tables(name):
    """Every Markdown table of data/ml/report/<name>.md as a DataFrame, in order."""
    tables, block = [], []
    for line in open(ml_path("report", f"{name}.md"), encoding="utf-8").read().splitlines() + [""]:
        if line.startswith("|"):
            if not re.match(r"^\|[\s:|-]+\|$", line):
                block.append(line.strip("|"))
        elif block:
            df = pd.read_csv(io.StringIO("\n".join(block)), sep="|", skipinitialspace=True)
            df.columns = [c.strip() for c in df.columns]
            tables.append(df.apply(lambda s: s.str.strip() if pd.api.types.is_string_dtype(s) else s))
            block = []
    return tables


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
    df = pd.read_csv(ml_path("report", "t31.csv"))
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
    df = pd.read_csv(ml_path("report", "t32_paired.csv"))
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
    df = pd.read_csv(ml_path("report", "t31_seeds.csv"))
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


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for f in (errors, curve, ndcg, ablation, seeds, arch):
        f()


if __name__ == "__main__":
    sys.exit(main())
