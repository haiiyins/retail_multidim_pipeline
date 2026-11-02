"""GBDT LambdaRank shared by P1-tuned, P2 and P4: load a ranking dataset, fit, score, and the tuning objective.

Feature rule as evaluation/train_eval_lambdarank.py: every column except ids, labels and anchor-grid bookkeeping. Training and
validation keep only groups with a positive in the list (no LambdaRank gradient otherwise); the objective is the unconditional
NDCG@20 on valid (ml/eval/protocol.py), so anchors whose positives all lie outside the list still count as misses.
P2 = the same GBDT with the rolling P2 signal features (ml/signals/run_leakage_study.add_signals) added to the pairs.
Usage (tuning smoke, ML-07 DoD): python ml/rankers/gbdt.py --tune p1 --trials 3
       python ml/rankers/gbdt.py --tune p1 --source v2 [--final --name p1_tuned_v2]      (P1-tuned on ml.candidates_v2)
       python ml/rankers/gbdt.py --tune p2 --source v2 --signals [--final --name p2_v2]  (P2)
       python ml/rankers/gbdt.py --tune p1 --source v2 --final --skip-tune --seed 1 --name p1_tuned_v2_seed1  (seed variance)"""
import argparse, json, os, sys
import lightgbm as lgb, numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, ml_path, split_windows
from ml.common.tuning import N_TRIALS, tune
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


POINT_IN_TIME = ("fit_cutoff", "source_ts_max", "model_version")


def features(df, drop=()):
    return [c for c in df.columns if c not in NONFEAT and c not in drop and c not in POINT_IN_TIME] + ["country_code"]


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


def best_params(name):
    t = pd.read_parquet(ml_path("tuning", f"{name}.parquet"))
    t = t[(t["state"] == "COMPLETE") & (t["trial"] < N_TRIALS)]
    return json.loads(t.loc[t["value"].idxmax(), "params"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", default="p1")
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--delta", type=int, default=30)
    ap.add_argument("--source", default="v1", help="v1 = gold.gld_ranking_dataset, v2 = pairs of ml.candidates_v2")
    ap.add_argument("--signals", action="store_true", help="add the rolling P2 signal features (P2)")
    ap.add_argument("--final", action="store_true", help="refit the best trial and write valid / test scores")
    ap.add_argument("--name", default=None)
    ap.add_argument("--skip-tune", action="store_true")
    ap.add_argument("--seed", type=int, default=0, help="final refit with LightGBM seed 42 + SEED (seed variance)")
    a = ap.parse_args()
    from ml.rankers.frozen import relation
    con = connect()
    rel = relation(a.source)
    tr, va = load(con, "train", a.delta, rel), load(con, "valid", a.delta, rel)
    if a.signals:
        from ml.signals.run_leakage_study import add_signals, with_dept
        tr, va = (add_signals(con, with_dept(con, d), "rolling").drop(columns=["dept"]) for d in (tr, va))
    feat = features(tr)
    print(f"train {len(tr):,} rows · valid {len(va):,} rows · {len(feat)} features · {threads()} threads", flush=True)
    tag = "" if a.source == "v1" else f"_{a.source}"
    study_name = f"{a.tune}{tag}"

    def objective(params, trial):
        m = fit(params, tr, va, feat, a.delta)
        value, _ = unconditional(con, score(m, va, feat), "valid", a.delta)
        trial.set_user_attr("best_iteration", m.best_iteration)
        print(f"  trial {trial.number}: NDCG@20 (valid, unconditional) {value:.4f}  rounds {m.best_iteration}  {params}", flush=True)
        return value

    if not a.skip_tune:
        from ml.common.data import load_config
        space = load_config("tuning")[a.tune]["space"]
        study, trials = tune(study_name, objective, n_trials=a.trials, space=space,
                             tag="" if a.trials is None else f"_smoke{a.trials}")
        print(trials[["trial", "value", "state", "wall_sec"]].to_string(index=False))
        print(f"best {study.best_value:.4f}  {study.best_params}", flush=True)
    if a.final:
        from ml.common.registry import Run
        params = best_params(study_name) | ({"seed": BASE["seed"] + a.seed} if a.seed else {})
        name = a.name or f"{study_name}"
        with Run(name, config={"source": a.source, "signals": a.signals, "seed": a.seed}, params=params) as run:
            m = fit(params, tr, va, feat, a.delta)
            run.metrics["best_iteration"] = m.best_iteration
            te = load(con, "test", a.delta, rel)
            if a.signals:
                te = add_signals(con, with_dept(con, te), "rolling").drop(columns=["dept"])
            for split, df in (("valid", va), ("test", te)):
                sc = score(m, df, feat).assign(country_code=df["country_code"].astype(str).to_numpy())
                path = os.path.join(ML_DIR, "scores", f"{name}_{split}_d{a.delta}.parquet")
                sc.to_parquet(path, index=False)
                v, _ = unconditional(con, sc, split, a.delta)
                run.metrics[f"{split}_ndcg20"] = v
                print(f"  {split}: NDCG@20 {v:.4f} → {path}", flush=True)
            os.makedirs(ml_path("models"), exist_ok=True)
            m.save_model(ml_path("models", f"{name}.txt"), num_iteration=m.best_iteration)
            run.artifacts["model"] = ml_path("models", f"{name}.txt")
            imp = pd.DataFrame({"feature": feat, "gain": m.feature_importance("gain")}).sort_values("gain", ascending=False)
            imp.to_csv(ml_path("report", f"importance_{name}.csv"), index=False)


if __name__ == "__main__":
    sys.exit(main())
