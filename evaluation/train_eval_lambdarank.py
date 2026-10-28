"""Step 7.2 — Fixed LightGBM LambdaRank ranker. Run 'full' first to freeze hyper-parameters (frozen_params.json)."""
import duckdb, lightgbm as lgb, numpy as np, pandas as pd, yaml, argparse, json, os, time
from dotenv import load_dotenv
load_dotenv()
ap = argparse.ArgumentParser()
ap.add_argument("--config", default="full"); ap.add_argument("--delta", type=int, default=30); ap.add_argument("--seed", type=int, default=42)
ap.add_argument("--no-freeze", action="store_true", help="tune with early stopping but do not write frozen_params.json (laptop smoke runs)")
ap.add_argument("--tag", default="", help="suffix for the result files, e.g. smoke")
a = ap.parse_args()
cfg = yaml.safe_load(open("evaluation/ablation_configs.yml"))[a.config]
split = yaml.safe_load(open("evaluation/split.yml"))
con = duckdb.connect(os.environ["DUCKDB_PATH"], read_only=True)
drop_cols = set(cfg.get("drop_features", [])); drop_r = cfg.get("drop_sources", [])
where_r = " AND ".join([f"{r} = 0" for r in drop_r]) or "TRUE"
ID = ["member_id", "anchor_date", "model_code", "country_code"]
NONFEAT = set(ID + ["label_30", "label_90", "forced_positive", "in_train_sample", "is_used", "split", "week_idx", "days_to_next_buy",
                    "last_source_ts", "sport_ids", "usual_store_id", "priority_source"])  # anchor-grid bookkeeping and label information are never features

def load(lo, hi, train):
    # only anchors with at least one positive for this Δ: a group without a positive carries no LambdaRank gradient and no
    # HR / MRR / NDCG value, so it only costs memory (Δ = 30 keeps about a quarter of the anchors, Δ = 90 about two thirds)
    q = f"""SELECT * FROM gold.gld_ranking_dataset WHERE anchor_date BETWEEN '{lo}' AND '{hi}' AND ({where_r})
            {'AND in_train_sample' if train else ''}
            QUALIFY MAX(label_{a.delta}) OVER (PARTITION BY member_id, anchor_date) = 1
            ORDER BY member_id, anchor_date"""
    df = con.execute(q).df()
    for c in df.columns:   # DECIMAL / HUGEINT aggregates arrive as Python objects: make every non-id column numeric
        if df[c].dtype == object and c not in NONFEAT and c not in ("promo_kind", "country_code"):
            df[c] = pd.to_numeric(df[c], errors="coerce")
    return df
t0 = time.time()
tr, va, te = load(split["train_lo"], split["train_hi"], True), load(split["valid_lo"], split["valid_hi"], False), load(split["test_lo"], split["test_hi"], False)
label = f"label_{a.delta}"
feat = [c for c in tr.columns if c not in NONFEAT and c not in drop_cols]
for df in (tr, va, te):
    for c in ("promo_kind", "country_code"):
        if c in df.columns: df[c] = df[c].astype("category")
    for c in feat:
        if df[c].dtype == bool: df[c] = df[c].astype(int)
cat_feats = [c for c in ("promo_kind", "country_code") if c in feat]
if "country_code" not in feat: feat.append("country_code"); cat_feats.append("country_code")
groups = lambda df: df.groupby(["member_id", "anchor_date"], sort=False).size().values

FROZEN = "evaluation/frozen_params.json"
if os.path.exists(FROZEN) and not a.no_freeze:
    frozen = json.load(open(FROZEN)); params = frozen["params"]; rounds = frozen["num_boost_round"]; tune = False
else:
    assert a.config == "full" or a.no_freeze, "Run --config full first to freeze the hyper-parameters"
    params = dict(objective="lambdarank", metric="ndcg", eval_at=[10, 20], num_leaves=63, learning_rate=0.05, min_child_samples=50,
                  feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1, lambdarank_truncation_level=20, verbose=-1,
                  num_threads=int(os.environ.get("DUCKDB_THREADS", 6)), seed=a.seed)
    rounds = 3000; tune = True
dtr = lgb.Dataset(tr[feat], tr[label], group=groups(tr), categorical_feature=cat_feats, free_raw_data=False)
dva = lgb.Dataset(va[feat], va[label], group=groups(va), reference=dtr, categorical_feature=cat_feats)
callbacks = [lgb.log_evaluation(100)] + ([lgb.early_stopping(100)] if tune else [])
m = lgb.train(params, dtr, num_boost_round=rounds, valid_sets=[dva], callbacks=callbacks)
if tune and not a.no_freeze:
    json.dump({"params": params, "num_boost_round": m.best_iteration}, open(FROZEN, "w"), indent=2); print("→ frozen", FROZEN)
elif tune:
    print(f"(no-freeze) best_iteration={m.best_iteration}; frozen_params.json untouched")
te["score"] = m.predict(te[feat], num_iteration=m.best_iteration if tune else None)

def metrics(df, k):
    rows = []
    for (u, t), g in df.groupby(["member_id", "anchor_date"], sort=False):
        rel = g.sort_values("score", ascending=False)[label].values
        if rel.sum() == 0: continue
        top = rel[:k]; hit = top.sum() > 0
        mrr = 1.0 / (int(np.argmax(top > 0)) + 1) if hit else 0.0
        dcg = (top / np.log2(np.arange(2, len(top) + 2))).sum(); ideal = np.sort(rel)[::-1][:k]
        idcg = (ideal / np.log2(np.arange(2, len(ideal) + 2))).sum()
        rows.append((u, t, g["country_code"].iloc[0], float(hit), mrr, dcg / idcg if idcg > 0 else 0.0, min(1.0, rel[:50].sum() / rel.sum())))
    return pd.DataFrame(rows, columns=["member_id", "anchor_date", "country_code", f"HR@{k}", f"MRR@{k}", f"NDCG@{k}", "Recall@50"])
r10, r20 = metrics(te, 10), metrics(te, 20)
res = r10.merge(r20[["member_id", "anchor_date", "HR@20", "MRR@20", "NDCG@20"]], on=["member_id", "anchor_date"])
os.makedirs("data/audit", exist_ok=True)
tag = f"_{a.tag}" if a.tag else ""
res.to_parquet(f"data/audit/results_{a.config}_d{a.delta}{tag}.parquet")
imp = pd.DataFrame({"feature": feat, "gain": m.feature_importance("gain")}).sort_values("gain", ascending=False)
imp.to_csv(f"data/audit/importance_{a.config}_d{a.delta}{tag}.csv", index=False)
summ = res.drop(columns=["member_id", "anchor_date"]).groupby("country_code").mean(numeric_only=True).round(4)
print(summ); print("OVERALL:", res.drop(columns=["member_id", "anchor_date", "country_code"]).mean(numeric_only=True).round(4).to_dict())
print(f"rows train/valid/test = {len(tr):,}/{len(va):,}/{len(te):,}  feats={len(feat)}  time={time.time()-t0:.0f}s")
