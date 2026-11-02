"""Candidate coverage of every built source (data/ml/candidates/<source>/) next to R1–R5, alone and in union, on valid and test
(unconditional positives, Δ = retrieval.delta; plan §5.2 target: union cand ≥ 0.45 on TH + VN, cand_explore × 2 over R1–R5).
Usage: python ml/retrieval/report.py [--out t30a]   →  data/ml/report/<out>_sources.md"""
import argparse, glob, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pandas as pd
from ml.common.data import ML_DIR, connect, ml_path
from ml.retrieval.base import baseline_relation, candidates_relation, recall_table, show, union_relation


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="t30a")
    ap.add_argument("--sources", default="", help="comma-separated; default every directory of data/ml/candidates/")
    a = ap.parse_args()
    names = (a.sources.split(",") if a.sources else
             sorted(os.path.basename(d.rstrip("/")) for d in glob.glob(os.path.join(ML_DIR, "candidates", "*", ""))))
    con = connect()
    tables = []
    for s in ("valid", "test"):
        own = {n: candidates_relation(n, s) for n in names}
        rels = {"R1-R5@200": baseline_relation(s), **own}
        rels.update({f"R1-R5 ∪ {n}": union_relation([baseline_relation(s), r]) for n, r in own.items()})
        if len(own) > 1:
            rels["learned (∪ " + ", ".join(names) + ")"] = union_relation(list(own.values()))
            rels["R1-R5 ∪ all learned"] = union_relation([baseline_relation(s), *own.values()])
        tables.append(recall_table(con, rels, s, ranked=set(own) | {"R1-R5@200"}))
    show(pd.concat(tables, ignore_index=True), ml_path("report", f"{a.out}_sources.md"))


if __name__ == "__main__":
    sys.exit(main())
