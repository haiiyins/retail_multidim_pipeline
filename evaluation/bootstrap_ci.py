"""Step 7.4 — Member-level bootstrap (WBS 4.4, issue #40): 95 % CI for every metric and for the paired difference arm − Full,
overall, per country and per member segment (new: at most one transaction in the previous 365 days; loyal: three or more).
Reads data/audit/results_<config>_d<Δ>[_<tag>].parquet written by train_eval_lambdarank.py; writes data/audit/ablation_results_d<Δ>[_<tag>].csv.
Usage: python evaluation/bootstrap_ci.py 30 [--tag smoke]      BOOT_N (default 500) resamples."""
import pandas as pd, numpy as np, glob, os, re, argparse, duckdb
from dotenv import load_dotenv
load_dotenv()
ap = argparse.ArgumentParser(); ap.add_argument("delta"); ap.add_argument("--tag", default="")
a = ap.parse_args(); tag = f"_{a.tag}" if a.tag else ""
B = int(os.environ.get("BOOT_N", 500)); rng = np.random.default_rng(0)
metrics = ["HR@10", "MRR@10", "NDCG@10", "HR@20", "MRR@20", "NDCG@20", "Recall@50"]
pat = re.compile(rf"results_(.+)_d{a.delta}{re.escape(tag)}\.parquet$")
files = {}
for f in glob.glob(f"data/audit/results_*_d{a.delta}{tag}.parquet"):
    m = pat.search(os.path.basename(f))
    if m: files[m.group(1)] = pd.read_parquet(f)
assert "full" in files, f"no results_full_d{a.delta}{tag}.parquet — run the Full configuration first"
con = duckdb.connect(os.environ["DUCKDB_PATH"], read_only=True)
seg = con.execute("SELECT member_id, anchor_date, CASE WHEN tx_365d <= 1 THEN 'new' WHEN tx_365d >= 3 THEN 'loyal' ELSE 'mid' END AS segment FROM gold.gld_fs_member").df()
seg["anchor_date"] = pd.to_datetime(seg["anchor_date"])
for name in files:
    files[name]["anchor_date"] = pd.to_datetime(files[name]["anchor_date"])
    files[name] = files[name].merge(seg, on=["member_id", "anchor_date"], how="left")

def member_means(df):   # one value per member, so resampling members (not anchors) gives the CI
    return df.groupby("member_id")[metrics].mean()

def ci(vals):
    boots = np.array([rng.choice(vals, len(vals)).mean() for _ in range(B)])
    return vals.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)

scopes = [("ALL", lambda d: d)] + [(c, lambda d, c=c: d[d["country_code"] == c]) for c in sorted(files["full"]["country_code"].unique())] \
       + [(f"segment:{s}", lambda d, s=s: d[d["segment"] == s]) for s in ("new", "mid", "loyal")]
rows = []
for scope, fn in scopes:
    full = member_means(fn(files["full"]))
    if len(full) < 20: continue
    for name, df in files.items():
        per = member_means(fn(df)); common = per.index.intersection(full.index)
        if len(common) < 20: continue
        diff = per.loc[common] - full.loc[common]
        for m in metrics:
            mean, lo, hi = ci(per[m].values); dmean, dlo, dhi = ci(diff[m].values)
            rows.append((scope, name, int(a.delta), m, len(per), mean, lo, hi, dmean, dlo, dhi, (dlo > 0) or (dhi < 0)))
out = pd.DataFrame(rows, columns=["scope", "config", "delta", "metric", "members", "mean", "ci_lo", "ci_hi", "diff_vs_full", "diff_lo", "diff_hi", "significant"])
out.to_csv(f"data/audit/ablation_results_d{a.delta}{tag}.csv", index=False)
show = out[(out["scope"] == "ALL") & (out["metric"].isin(["HR@10", "NDCG@10", "Recall@50"]))]
print(show.round(4).to_string(index=False))
print(f"→ data/audit/ablation_results_d{a.delta}{tag}.csv  ({len(out)} rows, B={B})")
