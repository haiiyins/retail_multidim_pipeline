"""Candidate coverage of every built source (data/ml/candidates/<source>/) next to R1–R5, alone and in union, on valid and test
(unconditional positives, Δ = retrieval.delta; plan §5.2 target: union cand ≥ 0.45 on TH + VN, cand_explore × 2 over R1–R5).
Seed replicas (<source>_seed<N>, test only) are left out of the unions and summarised as mean ± std over seeds.
Usage: python ml/retrieval/report.py [--out t30a] [--sources a,b]   →  data/ml/report/<out>_sources.md, <out>_seeds.md"""
import argparse, glob, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
import pandas as pd
from ml.common.data import ML_DIR, connect, ml_path
from ml.retrieval.base import baseline_relation, candidates_relation, recall_table, show, union_relation

SEED = re.compile(r"^(.*)_seed(\d+)$")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="t30a")
    ap.add_argument("--sources", default="", help="comma-separated; default every directory of data/ml/candidates/ but seed replicas")
    a = ap.parse_args()
    built = sorted(os.path.basename(d.rstrip("/")) for d in glob.glob(os.path.join(ML_DIR, "candidates", "*", "")))
    names = a.sources.split(",") if a.sources else [n for n in built if not SEED.match(n)]
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

    replicas = {}
    for n in built:
        m = SEED.match(n)
        if m and m.group(1) in names:
            replicas.setdefault(m.group(1), [m.group(1)]).append(n)
    if replicas:
        rows = []
        for base, runs in replicas.items():
            t = recall_table(con, {r: candidates_relation(r, "test") for r in runs}, "test")
            metrics = ["cand", "cand_repeat", "cand_explore", "Recall@20", "Recall@100"]
            for scope, g in t.groupby("scope"):
                rows.append({"source": base, "scope": scope, "seeds": len(g),
                             **{f"{k}_mean": g[k].mean() for k in metrics}, **{f"{k}_std": g[k].std() for k in metrics}})
        show(pd.DataFrame(rows), ml_path("report", f"{a.out}_seeds.md"))


if __name__ == "__main__":
    sys.exit(main())
