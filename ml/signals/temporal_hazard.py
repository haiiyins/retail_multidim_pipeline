"""P2 temporal hazard (plan §6): P(the member buys in department j in (t, t + Δ]) — LightGBM binary over member × department rows.

Rows of an anchor: the departments she bought before t, plus the top TOP_DEPTS departments of her country over the 90 days before t.
Features: member counts / recency / price (ml/signals/base.member_features), department counts / recency / inter-purchase cycle and
its overdue ratio, country popularity share of the department (30 / 90 days) and its trend, month, department and country (categorical).
Output: data/ml/signals/hazard_<variant>[_leaky].parquet — member_id, anchor_date, dept, hazard_p, fit_cutoff, source_ts_max, model_version."""
import lightgbm as lgb, numpy as np, pandas as pd

TOP_DEPTS = 10
PARAMS = dict(objective="binary", learning_rate=0.05, num_leaves=63, min_child_samples=100, feature_fraction=0.8, bagging_fraction=0.8,
              bagging_freq=1, verbose=-1, seed=0, deterministic=True, force_row_wise=True)
ROUNDS = 300
MEMBER_COLS = ["n_lines", "n_trips", "n_lines_90", "n_lines_365", "n_trips_365", "days_since_last", "days_since_first", "n_depts",
               "lp_q50", "lp_mean", "month"]
CATEGORICAL = ["dept", "country_code"]


def rows(con, delta):
    """member × department rows of every anchor with the Δ label."""
    return con.execute(f"""
        WITH h AS (SELECT a.member_id, a.anchor_date, b.d, b.dept FROM anc a JOIN buy b ON b.member_id = a.member_id AND b.d < a.anchor_date),
        hd AS (SELECT member_id, anchor_date, dept, COUNT(*) AS dept_lines, COUNT(DISTINCT d) AS dept_trips,
                      COUNT(*) FILTER (WHERE d >= anchor_date - 90) AS dept_lines_90, COUNT(*) FILTER (WHERE d >= anchor_date - 365) AS dept_lines_365,
                      anchor_date - MAX(d) AS days_since_dept, anchor_date - MIN(d) AS days_since_first_dept,
                      CASE WHEN COUNT(DISTINCT d) > 1 THEN (MAX(d) - MIN(d)) / (COUNT(DISTINCT d) - 1) END AS dept_cycle
               FROM h GROUP BY 1, 2, 3),
        days AS (SELECT DISTINCT country_code, anchor_date FROM anc),
        daily AS (SELECT country_code, d, dept, COUNT(*) AS n FROM buy GROUP BY 1, 2, 3),
        pop AS (SELECT x.country_code, x.anchor_date, y.dept,
                       SUM(y.n) FILTER (WHERE y.d >= x.anchor_date - 30) AS n30, SUM(y.n) AS n90
                FROM days x JOIN daily y ON y.country_code = x.country_code AND y.d < x.anchor_date AND y.d >= x.anchor_date - 90
                GROUP BY 1, 2, 3),
        popn AS (SELECT *, n30 / SUM(n30) OVER w AS pop_share_30, n90 / SUM(n90) OVER w AS pop_share_90,
                        ROW_NUMBER() OVER (PARTITION BY country_code, anchor_date ORDER BY n90 DESC, dept) AS pop_rank
                 FROM pop WINDOW w AS (PARTITION BY country_code, anchor_date)),
        cand AS (SELECT a.member_id, a.country_code, a.anchor_date, hd.dept FROM anc a JOIN hd USING (member_id, anchor_date)
                 UNION
                 SELECT a.member_id, a.country_code, a.anchor_date, p.dept FROM anc a JOIN popn p
                 ON p.country_code = a.country_code AND p.anchor_date = a.anchor_date AND p.pop_rank <= {TOP_DEPTS}),
        y AS (SELECT DISTINCT a.member_id, a.anchor_date, b.dept FROM anc a JOIN buy b
              ON b.member_id = a.member_id AND b.d > a.anchor_date AND b.d <= a.anchor_date + {delta})
        SELECT c.member_id, c.anchor_date, c.dept, hd.* EXCLUDE (member_id, anchor_date, dept),
               hd.days_since_dept / NULLIF(hd.dept_cycle, 0) AS dept_overdue,
               p.pop_share_30, p.pop_share_90, p.pop_share_30 / NULLIF(p.pop_share_90, 0) AS pop_trend, p.pop_rank,
               (y.dept IS NOT NULL)::INT AS label
        FROM cand c LEFT JOIN hd USING (member_id, anchor_date, dept)
        LEFT JOIN popn p ON p.country_code = c.country_code AND p.anchor_date = c.anchor_date AND p.dept = c.dept
        LEFT JOIN y ON y.member_id = c.member_id AND y.anchor_date = c.anchor_date AND y.dept = c.dept
        ORDER BY c.member_id, c.anchor_date, c.dept""").df()


def design(r, members):
    df = r.merge(members[["member_id", "anchor_date", "country_code"] + MEMBER_COLS], on=["member_id", "anchor_date"], how="left")
    for c in CATEGORICAL:
        df[c] = df[c].astype("category")
    feat = [c for c in df.columns if c not in ("member_id", "anchor_date", "label")]
    return df, feat


def fit(df, feat, mask, threads):
    d = lgb.Dataset(df.loc[mask, feat], df.loc[mask, "label"], categorical_feature=CATEGORICAL, free_raw_data=False)
    return lgb.train({**PARAMS, "num_threads": threads}, d, num_boost_round=ROUNDS)


def predict(model, df, feat, mask):
    return model.predict(df.loc[mask, feat])


def metrics(y, p):
    from sklearn.metrics import log_loss, roc_auc_score, average_precision_score
    y, p = np.asarray(y), np.clip(np.asarray(p), 1e-6, 1 - 1e-6)
    return {"rows": len(y), "pos_rate": float(y.mean()), "AUC": roc_auc_score(y, p), "AP": average_precision_score(y, p),
            "logloss": log_loss(y, p)}
