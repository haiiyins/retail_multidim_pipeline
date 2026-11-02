"""Paired member-bootstrap differences between two score sets on the same test anchors (unconditional, TH + VN): mean of the
per-member difference of a metric with a 95 % interval and the share of resamples above 0. Reads the per-anchor results that
ml/eval/protocol.py --reeval writes.
Usage: python ml/eval/paired.py --a p1_frozen_v2 --b p1_frozen [--metrics NDCG@20,recall_explore@20]
       python ml/eval/paired.py --pairs p3_onehead:p3_full,p3_noseq:p3_full --out t32_paired"""
import argparse, os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR

MAIN = ("TH", "VN")


def results(name):
    r = pd.read_parquet(os.path.join(ML_DIR, "eval", f"results_{name}_test_d30_unconditional.parquet"))
    return r[r["country_code"].isin(MAIN)]


def paired(a, b, metric, n=1000, seed=0):
    j = a[["member_id", "anchor_date", metric]].merge(b[["member_id", "anchor_date", metric]], on=["member_id", "anchor_date"],
                                                       suffixes=("_a", "_b")).dropna()
    d = (j[f"{metric}_a"] - j[f"{metric}_b"]).groupby(j["member_id"]).mean().to_numpy()
    rng = np.random.default_rng(seed)
    boots = np.array([d[rng.integers(0, len(d), len(d))].mean() for _ in range(n)])
    return {"metric": metric, "members": len(d), "diff": d.mean(), "ci_lo": np.percentile(boots, 2.5),
            "ci_hi": np.percentile(boots, 97.5), "P(diff > 0)": float((boots > 0).mean())}


def compare(a, b, metrics):
    ra, rb = results(a), results(b)
    return pd.DataFrame([{"a": a, "b": b, **paired(ra, rb, m)} for m in metrics])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--pairs", help="a:b,a:b,… instead of --a/--b")
    ap.add_argument("--out", help="write data/ml/report/<out>.md/.csv")
    ap.add_argument("--metrics", default="NDCG@20,HR@10,recall_repeat@20,recall_explore@20")
    a = ap.parse_args()
    pairs = [p.split(":") for p in a.pairs.split(",")] if a.pairs else [(a.a, a.b)]
    df = pd.concat([compare(x, y, a.metrics.split(",")) for x, y in pairs], ignore_index=True)
    print(df.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    if a.out:
        base = os.path.join(ML_DIR, "report", a.out)
        df.to_csv(base + ".csv", index=False)
        with open(base + ".md", "w") as f:
            f.write(f"# {a.out} — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b\n\n")
            f.write(df.to_markdown(index=False, floatfmt=".4f") + "\n")


if __name__ == "__main__":
    sys.exit(main())
