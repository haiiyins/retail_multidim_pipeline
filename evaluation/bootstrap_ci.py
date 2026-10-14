"""Step 7.4 — Member-level bootstrap: 95% CI per metric and for the paired difference Full − arm."""
import pandas as pd, numpy as np, glob, os, sys
B = int(os.environ.get("BOOT_N", 500)); rng = np.random.default_rng(0)
delta = sys.argv[1] if len(sys.argv) > 1 else "30"
files = {os.path.basename(f).replace("results_", "").replace(f"_d{delta}.parquet", ""): pd.read_parquet(f) for f in glob.glob(f"data/audit/results_*_d{delta}.parquet")}
metrics = ["HR@10", "MRR@10", "NDCG@10", "HR@20", "MRR@20", "NDCG@20", "Recall@50"]
full = files["full"].groupby("member_id")[metrics].mean()
rows = []
for name, df in files.items():
    per = df.groupby("member_id")[metrics].mean()
    common = per.index.intersection(full.index); diff = per.loc[common] - full.loc[common]
    for m in metrics:
        vals = per[m].values; boots = [rng.choice(vals, len(vals)).mean() for _ in range(B)]
        dvals = diff[m].values; dboots = [rng.choice(dvals, len(dvals)).mean() for _ in range(B)]
        rows.append((name, int(delta), m, vals.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5),
                     dvals.mean(), np.percentile(dboots, 2.5), np.percentile(dboots, 97.5)))
out = pd.DataFrame(rows, columns=["config", "delta", "metric", "mean", "ci_lo", "ci_hi", "diff_vs_full", "diff_lo", "diff_hi"])
out.to_csv(f"data/audit/ablation_results_d{delta}.csv", index=False); print(out.round(4).to_string())
