"""ML-13 — t30 recall curve: unconditional coverage of the mixed list cut at K ∈ mixer.curve_k for every mixer policy, next to R1–R5 at the
same K (gold.gld_candidates is capped at 200), on valid and test, split repeat / explore, ALL and MAIN (TH + VN); the cap of the ranker
(mixer.k) is read off this curve. Source cost (wall seconds of the candidate build) comes from the run registry.
Usage: python ml/retrieval/recall_curve.py [--out t30]   →  data/ml/report/<out>_curve.md"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pandas as pd
from ml.common.data import connect, ml_path
from ml.retrieval.base import baseline_relation, recall_table, show
from ml.retrieval.mixer import M, mixed_relation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="t30")
    ap.add_argument("--policies", default="fixed,per_member")
    a = ap.parse_args()
    con = connect()
    rows = []
    for split in ("valid", "test"):
        for k in M["curve_k"]:
            rels = {f"mix_{p}@{k}": mixed_relation(p, split, k) for p in a.policies.split(",")}
            if k <= 200:
                rels[f"R1-R5@{k}"] = baseline_relation(split, k)
            t = recall_table(con, rels, split, ks=(20, 100))
            t.insert(2, "K", k)
            rows.append(t)
    t = pd.concat(rows, ignore_index=True)
    show(t, ml_path("report", f"{a.out}_curve.md"))


if __name__ == "__main__":
    sys.exit(main())
