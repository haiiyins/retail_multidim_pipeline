"""P1-frozen (reference row, D5): the KTXLDL LambdaRank with the hyper-parameters and round count of evaluation/frozen_params.json,
refitted on the train split of a ranking dataset (v1 = gold.gld_ranking_dataset, v2 = the pairs of ml.candidates_v2) with the
original feature set (columns of gld_ranking_dataset only: the source ranks and point-in-time columns of v2 are not features).
Usage: python ml/rankers/frozen.py --source v2 --name p1_frozen_v2   →  data/ml/scores/<name>_{valid,test}_d30.parquet"""
import argparse, json, os, sys, time
import lightgbm as lgb

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, ROOT, connect, ml_path
from ml.common.registry import Run
from ml.rankers.gbdt import CATEGORICAL, NONFEAT, groups, load, threads

FROZEN = json.load(open(ROOT / "evaluation" / "frozen_params.json"))
V1 = "lh.gold.gld_ranking_dataset"


def relation(source):
    return V1 if source == "v1" else f"read_parquet('{ml_path('pairs_' + source, '*.parquet')}')"


def v1_features(con):
    cols = [r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {V1}").fetchall()]
    return [c for c in cols if c not in NONFEAT] + ["country_code"]


def train(tr, feat, delta=30, rounds=None):
    p = {**FROZEN["params"], "num_threads": threads()}
    cats = [c for c in CATEGORICAL if c in feat]
    d = lgb.Dataset(tr[feat], tr[f"label_{delta}"], group=groups(tr), categorical_feature=cats)
    return lgb.train(p, d, num_boost_round=rounds or FROZEN["num_boost_round"])


def scores(booster, df, feat):
    out = df[["member_id", "anchor_date", "model_code", "country_code"]].copy()
    out["country_code"] = out["country_code"].astype(str)
    out["score"] = booster.predict(df[feat])
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="v2")
    ap.add_argument("--name", default="p1_frozen_v2")
    ap.add_argument("--delta", type=int, default=30)
    a = ap.parse_args()
    con = connect()
    rel = relation(a.source)
    feat = [c for c in v1_features(con)]
    with Run(a.name, config={"source": a.source, "frozen": FROZEN}) as run:
        t0 = time.time()
        tr = load(con, "train", a.delta, rel)
        feat = [c for c in feat if c in tr.columns]
        m = train(tr, feat, a.delta)
        run.metrics.update(train_rows=len(tr), features=len(feat), train_sec=time.time() - t0)
        print(f"train {len(tr):,} rows · {len(feat)} features · {time.time() - t0:.0f}s", flush=True)
        del tr
        for split in ("valid", "test"):
            df = load(con, split, a.delta, rel)
            path = os.path.join(ML_DIR, "scores", f"{a.name}_{split}_d{a.delta}.parquet")
            scores(m, df, feat).to_parquet(path, index=False)
            run.artifacts[split] = path
            print(f"  {split}: {len(df):,} rows → {path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
