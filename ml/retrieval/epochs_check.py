"""Is the fixed epoch budget of the neural sources binding? Fits a neural source (two_tower or sasrec) with its tuned parameters at
several epoch counts for one country and scores the valid anchors: Δ explore coverage over R1–R5@200 (the tuning objective of
ml/retrieval/base.py) and stand-alone Recall@100, member means over the valid anchors of that country. The training log
(loss per epoch) is the logger output of ml/retrieval/neural.py.
Usage: python ml/retrieval/epochs_check.py --source sasrec --country TH --epochs 4,8,16  →  data/ml/report/epochs_<source>_<country>.md"""
import argparse, importlib, os, sys, time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path
from ml.eval.protocol import build_positives, evaluate
from ml.retrieval.base import ALL_K, CFG, Events, baseline_relation, generate, tuned_params, union_relation

CLASSES = {"two_tower": "TwoTower", "sasrec": "SASRec"}


def coverage(con, rel, country):
    res = evaluate(con, rel, f"read_parquet('{build_positives(con, 'valid', CFG['delta'])}')", ks=(100, ALL_K))
    res = res[res["country_code"] == country]
    by_member = res.groupby("member_id")[[f"recall_explore@{ALL_K}", "Recall@100"]].mean().mean()
    return float(by_member[f"recall_explore@{ALL_K}"]), float(by_member["Recall@100"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=sorted(CLASSES), required=True)
    ap.add_argument("--country", default="TH")
    ap.add_argument("--epochs", default="4,8,16")
    a = ap.parse_args()
    mod = importlib.import_module(f"ml.retrieval.{a.source}")
    src = getattr(mod, CLASSES[a.source])()
    src.seed = 0
    params = tuned_params(a.source)
    con = connect()
    ev = Events.load(con, a.country)
    base, _ = coverage(con, baseline_relation("valid"), a.country)
    rows = []
    for n in (int(x) for x in a.epochs.split(",")):
        mod.C["epochs"] = n
        t0 = time.time()
        cands = pd.concat([p for _, _, p in generate(src, params, con, ["valid"], [a.country], lambda c: ev)], ignore_index=True)
        con.register("_cands", cands)
        union, _ = coverage(con, union_relation([baseline_relation("valid"), "_cands"]), a.country)
        _, alone = coverage(con, "_cands", a.country)
        con.unregister("_cands")
        rows.append({"source": a.source, "country": a.country, "epochs": n, "delta_cand_explore": union - base,
                     "Recall@100 alone": alone, "fit_sec": time.time() - t0})
        print(rows[-1], flush=True)
    t = pd.DataFrame(rows)
    path = ml_path("report", f"epochs_{a.source}_{a.country}.md")
    with open(path, "w") as f:
        f.write(f"# Epoch budget check, {a.source}, {a.country}, valid (R1–R5@200 cand_explore {base:.4f})\n\n")
        f.write(t.to_markdown(index=False, floatfmt=".4f") + "\n")
    print(t.round(4).to_string(index=False))
    print(f"→ {path}")


if __name__ == "__main__":
    sys.exit(main())
