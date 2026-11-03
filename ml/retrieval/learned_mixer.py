"""ML-13b — learned mixer check: can a small model that scores the union of the sources choose a better top K than the rank-quota
mixer? Input: data/ml/candidates/mix_fixed (up to mixer.k_max candidates per anchor with the rank in every source). A LightGBM binary
classifier is fitted on a sample of train anchors (features: rank in each source, NULL when the source does not propose the model,
number of proposing sources, fixed-mixer rank, country), each positive weighted 1 / |positives of the anchor in the list| so that the
loss follows the per-anchor recall the coverage averages. On valid, the top K by score is compared with the fixed mixer's top K with
the same recall_table (unconditional, member means). Test is not read.
--write scores every split into data/ml/candidates/mix_learned (the layout of mix_fixed, mix_rank = learned rank) for
build_candidates.py --policy learned. Train anchors are cross-fitted (two folds by member, each scored by the model fitted on the
other fold), so that no train list is chosen with its own labels; valid and test use the model fitted on all train anchors.
Usage: python ml/retrieval/learned_mixer.py [--train-anchors 40000] [--ks 200,300] [--write]"""
import argparse, os, sys, time
import lightgbm as lgb, numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path
from ml.eval.protocol import build_positives
from ml.retrieval.base import CFG, recall_table, show

KEY = ["member_id", "anchor_date"]
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_data_in_leaf=200, feature_fraction=0.9, bagging_fraction=0.8,
              bagging_freq=1, verbose=-1, seed=0, num_threads=int(os.environ.get("ML_THREADS", 32)))


def load(split):
    df = pd.read_parquet(ml_path("candidates", "mix_fixed"), filters=[("split", "==", split)])
    df["anchor_date"] = pd.to_datetime(df["anchor_date"])
    return df


def features(df):
    ranks = [c for c in df.columns if c.startswith("rank_")]
    x = df[ranks + ["mix_rank"]].astype("float32")
    x["n_sources"] = df[ranks].notna().sum(axis=1).astype("float32")
    x["country"] = df["country_code"].astype("category")
    return x


def labelled(con, df, split):
    pos = pd.read_parquet(build_positives(con, split, CFG["delta"]), columns=KEY + ["model_code"])
    pos["anchor_date"] = pd.to_datetime(pos["anchor_date"])
    pos["y"] = 1
    df = df.merge(pos, on=KEY + ["model_code"], how="left")
    df["y"] = df["y"].fillna(0).astype("int8")
    n_pos = df.groupby(KEY)["y"].transform("sum")
    df["w"] = np.where(df["y"] == 1, 1.0 / n_pos.clip(lower=1), 1.0).astype("float32")
    return df


def fit(con, tr, n_anchors, rounds, label):
    """Binary LightGBM on a sample of the anchors of tr (learned sources present), early-stopped on 10 % of them."""
    t0 = time.time()
    tr = tr[tr["fit_cutoff"].notna()]                      # anchors before the first rolling cutoff have R1–R5 only
    anchors = tr[KEY].drop_duplicates()
    anchors = anchors.sample(n=min(n_anchors, len(anchors)), random_state=0)
    hold = anchors.sample(frac=0.1, random_state=1)
    tr = labelled(con, tr.merge(anchors, on=KEY), "train")
    is_hold = tr.set_index(KEY).index.isin(hold.set_index(KEY).index)
    x = features(tr)
    dtr = lgb.Dataset(x[~is_hold], tr.loc[~is_hold, "y"], weight=tr.loc[~is_hold, "w"])
    dho = lgb.Dataset(x[is_hold], tr.loc[is_hold, "y"], weight=tr.loc[is_hold, "w"], reference=dtr)
    model = lgb.train(PARAMS, dtr, num_boost_round=rounds, valid_sets=[dho], callbacks=[lgb.early_stopping(30, verbose=False)])
    print(f"fit {label}: {len(anchors):,} anchors, {len(tr):,} rows, {int(tr['y'].sum()):,} positives in the lists, "
          f"{model.best_iteration} rounds, {time.time() - t0:.0f}s", flush=True)
    return model


def rescore(df, model):
    df = df.copy()
    df["score"] = model.predict(features(df), num_iteration=model.best_iteration)
    df["learned_rank"] = df.groupby(KEY)["score"].rank(method="first", ascending=False).astype("int64")
    return df


def write(df, split):
    out = os.path.dirname(ml_path("candidates", "mix_learned", "_"))
    os.makedirs(out, exist_ok=True)
    df = df.drop(columns=["mix_rank", "score"]).rename(columns={"learned_rank": "mix_rank"})
    for country, part in df.groupby("country_code"):
        part.to_parquet(os.path.join(out, f"{split}_{country}.parquet"), index=False)
    print(f"  mix_learned {split}: {df[KEY].drop_duplicates().shape[0]:,} anchors, {len(df):,} rows", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--train-anchors", type=int, default=40_000)
    ap.add_argument("--ks", default="200,300")
    ap.add_argument("--rounds", type=int, default=400)
    ap.add_argument("--write", action="store_true")
    a = ap.parse_args()
    con = connect(threads=int(os.environ.get("DUCKDB_THREADS", 16)))
    t0 = time.time()

    tr = load("train")
    model = fit(con, tr, a.train_anchors, a.rounds, "all train")
    gain = pd.Series(model.feature_importance("gain"), index=model.feature_name())
    print("gain share:", (gain / gain.sum()).sort_values(ascending=False).round(3).to_dict(), flush=True)

    va = rescore(load("valid"), model)
    if a.write:
        fold = (pd.util.hash_pandas_object(tr["member_id"], index=False) % 2).to_numpy()
        parts = [rescore(tr[fold == f], fit(con, tr[fold != f], a.train_anchors, a.rounds, f"fold {1 - f}")) for f in (0, 1)]
        write(pd.concat(parts, ignore_index=True), "train")
        del parts
        write(va, "valid")
        write(rescore(load("test"), model), "test")
    con.register("_va", va[KEY + ["model_code", "mix_rank", "learned_rank"]])
    rels = {"union (k_max)": "(SELECT member_id, anchor_date, model_code, -mix_rank AS score FROM _va)"}
    for k in map(int, a.ks.split(",")):
        rels[f"fixed@{k}"] = f"(SELECT member_id, anchor_date, model_code, -mix_rank AS score FROM _va WHERE mix_rank <= {k})"
        rels[f"learned@{k}"] = (f"(SELECT member_id, anchor_date, model_code, -learned_rank AS score FROM _va "
                                f"WHERE learned_rank <= {k})")
    t = recall_table(con, rels, "valid", ks=(20, 100))
    show(t[["source", "scope", "list_size", "cand", "cand_repeat", "cand_explore", "Recall@20", "Recall@100"]],
         ml_path("report", "t30c_learned_mixer.csv"))
    print(f"done in {time.time() - t0:.0f}s")
    con.close()


if __name__ == "__main__":
    sys.exit(main())
