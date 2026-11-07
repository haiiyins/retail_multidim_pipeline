"""Rank fusion of two score sets (reciprocal rank fusion): score = w / (k + rank_a) + (1 − w) / (k + rank_b), a model missing from
one list ranked past every list. w and k are selected on valid NDCG@20 (unconditional, all countries); test is written with them.
Output: data/ml/scores/fuse_<a>_<b>_{valid,test}_d30.parquet.
Usage: python ml/eval/fusion.py rex_nbr p3_onehead"""
import os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect
from ml.eval.protocol import MAIN_COUNTRIES
from ml.rankers.gbdt import unconditional

GRID_K, GRID_W = (5, 20, 60), (0.3, 0.4, 0.5, 0.6, 0.7)
MISSING = 1e6


def load(name, split):
    s = pd.read_parquet(os.path.join(ML_DIR, "scores", f"{name}_{split}_d30.parquet"))
    s["anchor_date"] = pd.to_datetime(s["anchor_date"])
    s = s[np.isfinite(s["score"])]
    s["rank"] = s.groupby(["member_id", "anchor_date"])["score"].rank(ascending=False, method="first")
    return s[["member_id", "anchor_date", "model_code", "country_code", "rank"]]


def fuse(a, b, w, k):
    m = a.merge(b, how="outer", on=["member_id", "anchor_date", "model_code"], suffixes=("_a", "_b"))
    m["country_code"] = m["country_code_a"].fillna(m["country_code_b"])
    m["score"] = w / (k + m["rank_a"].fillna(MISSING)) + (1 - w) / (k + m["rank_b"].fillna(MISSING))
    return m[["member_id", "anchor_date", "model_code", "country_code", "score"]]


def ndcg(con, sc, split):
    """NDCG@20 member means: (TH + VN, all countries)."""
    _, res = unconditional(con, sc, split, 30)
    main = res[res["country_code"].isin(MAIN_COUNTRIES)]
    return main.groupby("member_id")["NDCG@20"].mean().mean(), res.groupby("member_id")["NDCG@20"].mean().mean()


def main():
    a, b = sys.argv[1], sys.argv[2]
    con = connect(threads=16)
    va, vb = load(a, "valid"), load(b, "valid")
    best = None
    for k in GRID_K:
        for w in GRID_W:
            main_v, all_v = ndcg(con, fuse(va, vb, w, k), "valid")
            print(f"valid k={k} w={w}: ALL {all_v:.4f} TH+VN {main_v:.4f}", flush=True)
            if best is None or all_v > best[0]:
                best = (all_v, w, k)
    _, w, k = best
    print(f"selected on valid (ALL): w={w} k={k}  {best[0]:.4f}")
    out = os.path.join(ML_DIR, "scores", f"fuse_{a}_{b}_{{}}_d30.parquet")
    fuse(va, vb, w, k).to_parquet(out.format("valid"), index=False)
    te = fuse(load(a, "test"), load(b, "test"), w, k)
    te.to_parquet(out.format("test"), index=False)
    print("test NDCG@20 (TH+VN, ALL)", ndcg(con, te, "test"))


if __name__ == "__main__":
    sys.exit(main())
