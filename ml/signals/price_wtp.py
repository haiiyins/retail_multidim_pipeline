"""P2 willingness to pay (plan §6): quantiles of the log unit price the member pays in (t, t + Δ] — LightGBM quantile regression
(α = 0.5 on the median line price of the window, α = 0.9 on its maximum), fitted on the anchors with a purchase in the window and
predicted for every anchor. Output: data/ml/signals/wtp_<variant>[_leaky].parquet — member_id, anchor_date, wtp_q50, wtp_q90
(log local currency), fit_cutoff, source_ts_max, model_version."""
import lightgbm as lgb, numpy as np

PARAMS = dict(learning_rate=0.05, num_leaves=63, min_child_samples=100, feature_fraction=0.8, bagging_fraction=0.8, bagging_freq=1,
              verbose=-1, seed=0, deterministic=True, force_row_wise=True)
ROUNDS = 300
TARGETS = {"wtp_q50": ("y_lp_q50", 0.5), "wtp_q90": ("y_lp_max", 0.9)}
FEATURES = ["country_code", "month", "n_lines", "n_trips", "n_lines_90", "n_lines_365", "n_trips_365", "days_since_last",
            "days_since_first", "n_depts", "lp_q25", "lp_q50", "lp_q75", "lp_q90", "lp_mean", "lp_max", "lp_q50_365"]


def fit(df, mask, threads):
    models = {}
    for name, (target, alpha) in TARGETS.items():
        m = mask & df[target].notna().to_numpy()
        d = lgb.Dataset(df.loc[m, FEATURES], df.loc[m, target], categorical_feature=["country_code"], free_raw_data=False)
        models[name] = lgb.train({**PARAMS, "objective": "quantile", "alpha": alpha, "num_threads": threads}, d, num_boost_round=ROUNDS)
    return models


def predict(models, df, mask):
    return {name: m.predict(df.loc[mask, FEATURES]) for name, m in models.items()}


def pinball(y, q, alpha):
    e = y - q
    return float(np.mean(np.maximum(alpha * e, (alpha - 1) * e)))


def metrics(df, pred):
    out = {"rows": int(len(df))}
    for name, (target, alpha) in TARGETS.items():
        ok = df[target].notna().to_numpy() & ~np.isnan(pred[name])
        y, q = df.loc[ok, target].to_numpy(), pred[name][ok]
        out[f"pinball_{name}"] = pinball(y, q, alpha)
        out[f"cover_{name}"] = float(np.mean(y <= q))
    return out
