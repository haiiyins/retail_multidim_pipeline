"""Weighted reciprocal rank fusion of score sets: score = Σ_j w_j / (k + rank_j), a model missing from a list adding nothing (ranked
past every list). The weight set and k are selected on valid NDCG@20 (unconditional, all countries); test is written with them.
Output: data/ml/scores/<out>_{valid,test}_d30.parquet.
Usage: python ml/eval/fusion.py --parts rex_nbr,p3_onehead --out fuse_rex_nbr_p3_onehead            (w ∈ 0.3…0.7, k ∈ 5/20/60)
       python ml/eval/fusion.py --parts rex_nbr,rex_nbr_seed1,rex_nbr_seed2 --weights 1,1,1 --out rex_ens3
       python ml/eval/fusion.py --parts rex_ens3,p3_ens3,p1_tuned_v2rex --weights "0.4,0.3,0.3;0.34,0.33,0.33" --k 5 --out ens_main"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect
from ml.eval.protocol import MAIN_COUNTRIES, build_positives, evaluate

PAIR_W = (0.3, 0.4, 0.5, 0.6, 0.7)


def path(name, split):
    return os.path.join(ML_DIR, "scores", f"{name}_{split}_d30.parquet")


def relation(parts, weights, k, split):
    ranked = " UNION ALL ".join(
        f"""SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code, country_code,
                   {w} / ({k} + ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, model_code)) AS s
            FROM read_parquet('{path(n, split)}') WHERE score > '-inf'::DOUBLE""" for n, w in zip(parts, weights))
    return (f"(SELECT member_id, anchor_date, model_code, ANY_VALUE(country_code) AS country_code, SUM(s) AS score "
            f"FROM ({ranked}) GROUP BY ALL)")


def ndcg(con, rel, split):
    """NDCG@20 member means: (all countries, TH + VN)."""
    res = evaluate(con, rel, f"read_parquet('{build_positives(con, split, 30)}')", ks=(10, 20))
    main = res[res["country_code"].isin(MAIN_COUNTRIES)]
    return res.groupby("member_id")["NDCG@20"].mean().mean(), main.groupby("member_id")["NDCG@20"].mean().mean()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--parts", required=True)
    ap.add_argument("--weights", default="", help="weight sets 'w1,w2;w1,w2'; default w, 1 − w over 0.3…0.7 for two parts")
    ap.add_argument("--k", default="5,20,60")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    parts = a.parts.split(",")
    if a.weights:
        sets = [tuple(float(x) for x in s.split(",")) for s in a.weights.split(";")]
    else:
        assert len(parts) == 2, "give --weights for more than two parts"
        sets = [(w, round(1 - w, 2)) for w in PAIR_W]
    assert all(len(s) == len(parts) for s in sets)
    con = connect(threads=32)
    best = None
    for k in (int(x) for x in a.k.split(",")):
        for ws in sets:
            all_v, main_v = ndcg(con, relation(parts, ws, k, "valid"), "valid")
            print(f"valid k={k} w={ws}: ALL {all_v:.4f} TH+VN {main_v:.4f}", flush=True)
            if best is None or all_v > best[0]:
                best = (all_v, ws, k)
    _, ws, k = best
    print(f"selected on valid (ALL): w={ws} k={k}  {best[0]:.4f}", flush=True)
    for split in ("valid", "test"):
        con.execute(f"COPY (SELECT * FROM {relation(parts, ws, k, split)}) TO '{path(a.out, split)}' (FORMAT parquet)")
    print(f"written {path(a.out, '{valid,test}')}")


if __name__ == "__main__":
    sys.exit(main())
