"""P2 signal models (plan §6, D7): shared anchor-level inputs and the three fitting protocols.

Universe: every is_used anchor of the anchor grid (train, valid, test). Inputs of an anchor t are the member's non-returned purchases
dated strictly before t; labels are her purchases in (t, t + Δ]. Departments are the modal sport department of a model in
slv_dim_model (the same mapping the rankers use for candidates).
Protocols (D7):
  rolling  a model per quarterly cutoff c (ml/common/pit.py) fitted on the anchors whose label window closes before c; an anchor uses
           the model of cutoff_for(t). Anchors before the first cutoff get no value. The only point-in-time-correct variant.
  naive    one model fitted on every train-split anchor and applied everywhere, including in-sample on the anchors it was fitted on
           (the usual stacking mistake; fit_cutoff = train_hi + 1 day).
  leaky    one model fitted on every anchor of every split, test labels included (fit_cutoff = test_hi + Δ + 1).
naive and leaky outputs are written with the _leaky suffix convention of D7 (never published as ml.* views)."""
import datetime as dt, os, time
import numpy as np, pandas as pd

from ml.common.data import ml_path, split_windows
from ml.common.pit import cutoff_for, cutoffs, final_cutoff, last_fit_anchor

DELTA = 30
VARIANTS = ("rolling", "naive", "leaky")
PSEUDO_TEST_LO = dt.date(2025, 7, 1)   # last quarter of train: the pseudo-test of t29 / t29b
MAX_FIT_ANCHORS = 120_000              # anchors sampled per rolling fit (all of them for naive / leaky would bias the comparison)


def buy_table(con):
    """Temp table buy(member_id, country_code, d, dept, logp): non-returned purchase lines, as in ml/eval/protocol.py."""
    con.execute("""CREATE OR REPLACE TEMP TABLE dm AS SELECT model_code, COALESCE(MODE(sport_department_code), -1) AS dept
                   FROM lh.silver.slv_dim_model GROUP BY 1""")
    con.execute("""CREATE OR REPLACE TEMP TABLE buy AS
        SELECT f.member_id, f.country_code, f.transaction_date AS d, COALESCE(dm.dept, -1) AS dept,
               LN(f.gmv_local / f.qty) AS logp
        FROM lh.silver.slv_fact_sales_line f LEFT JOIN dm USING (model_code)
        WHERE f.member_id IS NOT NULL AND f.model_code IS NOT NULL AND f.qty > 0 AND f.gmv_local > 0
          AND NOT EXISTS (SELECT 1 FROM lh.silver.slv_fact_returns r WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code)""")


def anchor_table(con):
    con.execute("""CREATE OR REPLACE TEMP TABLE anc AS SELECT member_id, country_code, anchor_date, split FROM lh.gold.anchor_grid
                   WHERE is_used""")
    return con.execute("SELECT COUNT(*) FROM anc").fetchone()[0]


def member_features(con):
    """One row per anchor: purchase counts / recency / price distribution before t, and the Δ-window price targets."""
    return con.execute(f"""
        WITH h AS (SELECT a.member_id, a.anchor_date, b.d, b.dept, b.logp FROM anc a JOIN buy b
                   ON b.member_id = a.member_id AND b.d < a.anchor_date),
        f AS (SELECT member_id, anchor_date, COUNT(*) AS n_lines, COUNT(DISTINCT d) AS n_trips,
                     COUNT(*) FILTER (WHERE d >= anchor_date - 90) AS n_lines_90, COUNT(*) FILTER (WHERE d >= anchor_date - 365) AS n_lines_365,
                     COUNT(DISTINCT d) FILTER (WHERE d >= anchor_date - 365) AS n_trips_365,
                     anchor_date - MAX(d) AS days_since_last, anchor_date - MIN(d) AS days_since_first, COUNT(DISTINCT dept) AS n_depts,
                     QUANTILE_CONT(logp, 0.25) AS lp_q25, QUANTILE_CONT(logp, 0.5) AS lp_q50, QUANTILE_CONT(logp, 0.75) AS lp_q75,
                     QUANTILE_CONT(logp, 0.9) AS lp_q90, AVG(logp) AS lp_mean, MAX(logp) AS lp_max,
                     QUANTILE_CONT(logp, 0.5) FILTER (WHERE d >= anchor_date - 365) AS lp_q50_365,
                     MAX(d) AS last_d
              FROM h GROUP BY 1, 2),
        y AS (SELECT a.member_id, a.anchor_date, QUANTILE_CONT(b.logp, 0.5) AS y_lp_q50, MAX(b.logp) AS y_lp_max, COUNT(*) AS y_lines
              FROM anc a JOIN buy b ON b.member_id = a.member_id AND b.d > a.anchor_date AND b.d <= a.anchor_date + {DELTA} GROUP BY 1, 2)
        SELECT a.member_id, a.country_code, a.anchor_date, a.split, MONTH(a.anchor_date) AS month, f.* EXCLUDE (member_id, anchor_date),
               y.y_lp_q50, y.y_lp_max, COALESCE(y.y_lines, 0) AS y_lines
        FROM anc a LEFT JOIN f USING (member_id, anchor_date) LEFT JOIN y USING (member_id, anchor_date)
        ORDER BY a.member_id, a.anchor_date""").df()


def fit_sets(anchor_dates, splits, variant, seed=0):
    """[(fit_cutoff, fit mask, apply mask)] over the anchor rows for one protocol."""
    d = pd.to_datetime(anchor_dates).dt.date.to_numpy()
    rng = np.random.default_rng(seed)
    sw = split_windows()
    if variant == "rolling":
        out = []
        cut = np.array([cutoff_for(x) for x in d], dtype=object)
        for c in cutoffs():
            fit = d <= last_fit_anchor(c, DELTA)
            apply = cut == c
            if apply.any() and fit.any():
                out.append((c, subsample(fit, rng), apply))
        return out
    if variant == "naive":
        fit = (splits == "train") & (d <= sw["train_hi"])
        return [(final_cutoff(), subsample(fit, rng), np.ones(len(d), bool))]
    if variant == "leaky":
        return [(sw["test_hi"] + dt.timedelta(days=DELTA + 1), subsample(np.ones(len(d), bool), rng), np.ones(len(d), bool))]
    raise ValueError(variant)


def subsample(mask, rng, n=MAX_FIT_ANCHORS):
    idx = np.flatnonzero(mask)
    if len(idx) > n:
        keep = np.zeros_like(mask)
        keep[rng.choice(idx, n, replace=False)] = True
        return keep
    return mask


def eval_sets(anchor_dates, splits):
    """t29 / t29b evaluation sets: train anchors before the pseudo-test quarter, the pseudo-test quarter, test."""
    d = pd.to_datetime(anchor_dates).dt.date.to_numpy()
    return {"train": (splits == "train") & (d < PSEUDO_TEST_LO), "pseudo_test": (splits == "train") & (d >= PSEUDO_TEST_LO),
            "test": splits == "test"}


def out_path(signal, variant):
    return ml_path("signals", f"{signal}_{variant}.parquet" if variant == "rolling" else f"{signal}_{variant}_leaky.parquet")


def log(msg, t0):
    print(f"  {msg}  {time.time() - t0:.0f}s", flush=True)
