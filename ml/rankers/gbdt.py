"""GBDT LambdaRank shared by P1-tuned, P2 and P4: load a ranking dataset, fit, score, and the tuning objective.

Feature rule as evaluation/train_eval_lambdarank.py: every column except ids, labels and anchor-grid bookkeeping. Training and
validation keep only groups with a positive in the list (no LambdaRank gradient otherwise); the objective is the unconditional
NDCG@20 on valid (ml/eval/protocol.py), so anchors whose positives all lie outside the list still count as misses.
Usage (tuning smoke, ML-07 DoD): python ml/rankers/gbdt.py --tune p1 --trials 3"""
import argparse, os, sys
import lightgbm as lgb, numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, split_windows
from ml.common.tuning import tune
from ml.eval.protocol import build_positives, evaluate

ID = ["member_id", "anchor_date", "model_code", "country_code"]
NONFEAT = set(ID + ["label_30", "label_90", "forced_positive", "in_train_sample", "is_used", "split", "week_idx", "days_to_next_buy",
                    "last_source_ts", "sport_ids", "usual_store_id", "priority_source"])
CATEGORICAL = ("promo_kind", "country_code")
BASE = dict(objective="lambdarank", metric="ndcg", eval_at=[20], lambdarank_truncation_level=20, bagging_freq=1, verbose=-1,
            deterministic=True, force_row_wise=True, seed=42)


def threads():
    return int(os.environ.get("ML_THREADS", 32))


def load(con, split, delta, relation="lh.gold.gld_ranking_dataset", positive_groups_only=True):
    sw = split_windows()
    lo, hi = sw[f"{split}_lo"], sw[f"{split}_hi"]
    sample = "AND in_train_sample" if split == "train" else ""
    keep = f"WHERE grp_pos = 1" if positive_groups_only else ""
    df = con.execute(f"""SELECT * EXCLUDE (grp_pos) FROM (
            SELECT *, MAX(label_{delta}) OVER (PARTITION BY member_id, anchor_date) AS grp_pos FROM {relation}
            WHERE anchor_date BETWEEN DATE '{lo}' AND DATE '{hi}' {sample}) {keep}
        ORDER BY member_id, anchor_date, model_code""").df()
    for c in df.columns:
        if df[c].dtype == object and c not in NONFEAT and c not in CATEGORICAL:
            df[c] = pd.to_numeric(df[c], errors="coerce")
        elif df[c].dtype == bool:
            df[c] = df[c].astype(int)
    for c in CATEGORICAL:
        if c in df.columns:
            df[c] = df[c].astype("category")
    return df


def features(df, drop=()):
    return [c for c in df.columns if c not in NONFEAT and c not in drop] + ["country_code"]


def groups(df):
    return df.groupby(["member_id", "anchor_date"], sort=False).size().values


def fit(params, tr, va, feat, delta, max_rounds=3000, early_stop=100):
    cats = [c for c in CATEGORICAL if c in feat]
    p = {**BASE, "num_threads": threads(), **params}
    dtr = lgb.Dataset(tr[feat], tr[f"label_{delta}"], group=groups(tr), categorical_feature=cats, free_raw_data=False)
    dva = lgb.Dataset(va[feat], va[f"label_{delta}"], group=groups(va), reference=dtr, categorical_feature=cats)
    return lgb.train(p, dtr, num_boost_round=max_rounds, valid_sets=[dva], callbacks=[lgb.early_stopping(early_stop, verbose=False)])


def score(booster, df, feat):
    out = df[["member_id", "anchor_date", "model_code"]].copy()
    out["score"] = booster.predict(df[feat], num_iteration=booster.best_iteration)
    return out


def unconditional(con, scores, split, delta, metric="NDCG@20"):
    con.register("_scores", scores)
    res = evaluate(con, "_scores", f"read_parquet('{build_positives(con, split, delta)}')")
    con.unregister("_scores")
    return float(res.groupby("member_id")[metric].mean().mean()), res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", default="p1")
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--delta", type=int, default=30)
    a = ap.parse_args()
    con = connect()
    tr, va = load(con, "train", a.delta), load(con, "valid", a.delta)
    feat = features(tr)
    print(f"train {len(tr):,} rows · valid {len(va):,} rows · {len(feat)} features · {threads()} threads")

    def objective(params, trial):
        m = fit(params, tr, va, feat, a.delta)
        value, _ = unconditional(con, score(m, va, feat), "valid", a.delta)
        trial.set_user_attr("best_iteration", m.best_iteration)
        print(f"  trial {trial.number}: NDCG@20 (valid, unconditional) {value:.4f}  rounds {m.best_iteration}  {params}")
        return value

    study, trials = tune(a.tune, objective, n_trials=a.trials, tag="" if a.trials is None else f"_smoke{a.trials}")
    print(trials[["trial", "value", "state", "wall_sec"]].to_string(index=False))
    print(f"best {study.best_value:.4f}  {study.best_params}")


if __name__ == "__main__":
    sys.exit(main())
