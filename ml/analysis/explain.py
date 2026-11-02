"""Interpretation (plan §12, t35, reduced): grouped TreeSHAP of the GBDT rankers and the distribution of the P3 gate.

t35a  mean |SHAP| per feature group (LightGBM pred_contrib) on a sample of test anchors of the v2 pairs, overall and for repeat /
      explore candidates, for P1-tuned and P2.
t35c  P3 learned gate g (share of probability mass on the member's repeat candidates) by segment and country, against the
      repeat share of her positives: "who the model thinks is a re-buyer".
Usage: python ml/analysis/explain.py [--gbdt p1_tuned_v2,p2_v2] [--p3 p3_full] [--anchors 3000]"""
import argparse, os, sys
import lightgbm as lgb, numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path, split_windows
from ml.rankers.frozen import relation
from ml.rankers.gbdt import CATEGORICAL, load

GROUPS = [
    ("retrieval: R1-R5 flags / scores / rank", lambda c: c[:1] == "r" and c[1:].isdigit() or c.startswith("score_r") or c == "candidate_rank"),
    ("retrieval: learned source ranks", lambda c: c.startswith("rank_")),
    ("member: activity / RFM", lambda c: c in {"tx_30d", "tx_90d", "tx_365d", "items_365d", "models_365d", "days_since_last_tx",
                                                "gmv_eur_365d", "return_rate", "account_tenure_days", "n_sports", "usual_store_share",
                                                "stores_visited_cum"}),
    ("member: price profile", lambda c: c in {"price_q25", "price_q50", "price_q75", "price_q50_eur", "promo_affinity", "promo_sensitivity"}),
    ("web behaviour", lambda c: c.startswith("web_") or c == "has_web_signal"),
    ("model: price / promo", lambda c: c in {"price_local", "ref_price_local", "n_sku_priced", "sku_price_coverage", "promo_kind",
                                             "is_temp_promo", "temp_promo_share", "promo_depth", "country_promo_share"}),
    ("model: popularity / season / stock", lambda c: c in {"buyers_28d", "qty_28d", "popularity_rank", "model_age_days", "seasonal_idx",
                                                           "avail_store_ratio", "stock_qty_national", "in_commercial_event",
                                                           "days_to_next_holiday", "in_stock_usual_store"}),
    ("pair: own history", lambda c: c in {"hist_buy_cnt", "days_since_bought", "hist_qty"}),
    ("pair: department recency / cycle", lambda c: c.startswith("dept_") or c == "days_since_dept_buy"),
    ("pair: co-purchase / sport / budget", lambda c: c.startswith("copurchase_") or c in {"sport_match", "price_gap_q50", "in_budget_iqr"}),
    ("P2 signals", lambda c: c.startswith("hazard") or c.startswith("wtp_")),
    ("country", lambda c: c == "country_code"),
]


def group_of(c):
    return next((g for g, f in GROUPS if f(c)), "other")


def shap_table(con, name, signals, n_anchors, rng):
    booster = lgb.Booster(model_file=ml_path("models", f"{name}.txt"))
    feat = booster.feature_name()
    df = load(con, "test", 30, relation("v2"))
    if signals:
        from ml.signals.run_leakage_study import add_signals, with_dept
        df = add_signals(con, with_dept(con, df), "rolling")
    keys = df[["member_id", "anchor_date"]].drop_duplicates()
    keys = keys.iloc[rng.choice(len(keys), min(n_anchors, len(keys)), replace=False)]
    df = df.merge(keys, on=["member_id", "anchor_date"])
    for c in CATEGORICAL:
        if c in df.columns:
            df[c] = df[c].astype("category")
    contrib = booster.predict(df[feat], pred_contrib=True)[:, :-1]
    groups = pd.Series([group_of(c) for c in feat])
    absval = pd.DataFrame(np.abs(contrib), columns=feat)
    rep = df["hist_buy_cnt"].fillna(0).to_numpy() > 0
    out = {}
    for label, mask in (("all", np.ones(len(df), bool)), ("repeat candidates", rep), ("explore candidates", ~rep)):
        g = absval[mask].mean().groupby(groups.values).sum()
        out[label] = g / g.sum()
    t = pd.DataFrame(out).sort_values("all", ascending=False)
    t.index.name = f"{name}: share of mean |SHAP|"
    return t, len(df)


@torch.no_grad()
def gate_table(con, name):
    from ml.umtr.data import get
    from ml.umtr.train import DEVICE, batch, build
    ck = torch.load(ml_path("models", f"{name}.pt"), weights_only=False)
    te = get("v2", "test")
    model = build(te["meta"], ck["params"], ck["variant"])
    model.load_state_dict(ck["state"])
    model.eval()
    g = []
    for s in range(0, len(te["x"]), 1024):
        g.append(model(batch(te, torch.arange(s, min(s + 1024, len(te["x"])))))["g"].float().cpu())
    head = te["anchors"].copy()
    head["g"] = torch.cat(g).numpy()
    head["gate_target"] = te["gate_y"].numpy()
    head["anchor_date"] = pd.to_datetime(head["anchor_date"])
    seg = con.execute("""SELECT member_id, anchor_date, CASE WHEN tx_365d <= 1 THEN 'new' WHEN tx_365d >= 3 THEN 'loyal' ELSE 'mid' END AS segment
                         FROM lh.gold.gld_fs_member""").df()
    seg["anchor_date"] = pd.to_datetime(seg["anchor_date"])
    head = head.merge(seg, on=["member_id", "anchor_date"], how="left")
    rows = []
    for by in ("segment", "country_code"):
        for k, d in head.groupby(by):
            rows.append({"by": by, "group": k, "anchors": len(d), "mean g": d["g"].mean(), "median g": d["g"].median(),
                         "repeat share of positives": d["gate_target"].mean(),
                         "corr(g, target)": d[["g", "gate_target"]].dropna().corr().iloc[0, 1]})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gbdt", default="p1_tuned_v2,p2_v2")
    ap.add_argument("--p3", default="p3_full")
    ap.add_argument("--anchors", type=int, default=3000)
    a = ap.parse_args()
    con = connect()
    rng = np.random.default_rng(0)
    with open(ml_path("report", "t35.md"), "w") as f:
        f.write("# t35 — interpretation (test, v2 pairs)\n\n")
        for name in filter(None, a.gbdt.split(",")):
            if not os.path.exists(ml_path("models", f"{name}.txt")):
                continue
            t, n = shap_table(con, name, name.startswith("p2"), a.anchors, rng)
            f.write(f"## t35a {name} — grouped TreeSHAP, {a.anchors} test anchors ({n:,} candidate rows)\n\n")
            f.write(t.to_markdown(floatfmt=".3f") + "\n\n")
            print(t.round(3).to_string(), flush=True)
        if a.p3 and os.path.exists(ml_path("models", f"{a.p3}.pt")):
            t = gate_table(con, a.p3)
            f.write(f"## t35c {a.p3} — learned gate g against the repeat share of the positives\n\n")
            f.write(t.to_markdown(index=False, floatfmt=".3f") + "\n")
            print(t.round(3).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
