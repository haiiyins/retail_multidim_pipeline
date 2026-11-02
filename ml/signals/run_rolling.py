"""P2 signals × {rolling, naive, leaky} (plan §6, D7, ML-15) and their stand-alone quality → t29.

t29: hazard AUC / AP / log-loss over member × department rows, WTP pinball loss and coverage, on train anchors before the
pseudo-test quarter, the pseudo-test quarter (last quarter of train) and test; every variant on the rows the rolling protocol
covers (anchors from the first cutoff on), so the three variants are compared on the same rows.
Usage: python ml/signals/run_rolling.py [--signals hazard,wtp] [--variants rolling,naive,leaky]"""
import argparse, os, sys, time
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path, publish_view
from ml.common.pit import assert_pit
from ml.rankers.gbdt import threads
from ml.signals import price_wtp, temporal_hazard
from ml.signals.base import DELTA, VARIANTS, anchor_table, buy_table, eval_sets, fit_sets, log, member_features, out_path


def inputs(con):
    """Cached anchor-level and member × department inputs."""
    mp, hp = ml_path("signals", "_members.parquet"), ml_path("signals", "_hazard_rows.parquet")
    if os.path.exists(mp) and os.path.exists(hp):
        return pd.read_parquet(mp), pd.read_parquet(hp)
    t0 = time.time()
    buy_table(con)
    n = anchor_table(con)
    members = member_features(con)
    log(f"member features: {n:,} anchors", t0)
    rows = temporal_hazard.rows(con, DELTA)
    log(f"hazard rows: {len(rows):,} member × department rows, positive rate {rows['label'].mean():.3f}", t0)
    members.to_parquet(mp, index=False)
    rows.to_parquet(hp, index=False)
    return members, rows


def finish(out, variant):
    out["model_version"] = f"p2_{variant}"
    return out


def run_hazard(members, rows, variant, nthreads):
    t0 = time.time()
    df, feat = temporal_hazard.design(rows, members)
    split = df[["member_id", "anchor_date"]].merge(members[["member_id", "anchor_date", "split", "last_d"]], how="left")
    p = np.full(len(df), np.nan)
    fit_cut = np.full(len(df), None, dtype=object)
    # fit sets are drawn over anchors, then expanded to their department rows
    keys = members[["member_id", "anchor_date"]].reset_index(drop=True)
    row_anchor = df[["member_id", "anchor_date"]].merge(keys.reset_index(), how="left")["index"].to_numpy()
    for c, fit_a, apply_a in fit_sets(members["anchor_date"], members["split"].to_numpy(), variant):
        fit_m, apply_m = fit_a[row_anchor], apply_a[row_anchor]
        model = temporal_hazard.fit(df, feat, fit_m, nthreads)
        p[apply_m] = temporal_hazard.predict(model, df, feat, apply_m)
        fit_cut[apply_m] = c
        log(f"hazard {variant} cutoff {c}: fit {fit_m.sum():,} rows, apply {apply_m.sum():,}", t0)
    out = pd.DataFrame({"member_id": df["member_id"], "anchor_date": df["anchor_date"], "dept": df["dept"].astype(int),
                        "hazard_p": p, "fit_cutoff": pd.to_datetime(pd.Series(fit_cut)).dt.date, "source_ts_max": split["last_d"].to_numpy(),
                        "label": df["label"].to_numpy(), "split": split["split"].to_numpy()})
    return finish(out[out["hazard_p"].notna()], variant)


def run_wtp(members, variant, nthreads):
    t0 = time.time()
    df = members.copy()
    df["country_code"] = df["country_code"].astype("category")
    pred = {k: np.full(len(df), np.nan) for k in price_wtp.TARGETS}
    fit_cut = np.full(len(df), None, dtype=object)
    for c, fit_m, apply_m in fit_sets(df["anchor_date"], df["split"].to_numpy(), variant):
        models = price_wtp.fit(df, fit_m, nthreads)
        for k, v in price_wtp.predict(models, df, apply_m).items():
            pred[k][apply_m] = v
        fit_cut[apply_m] = c
        log(f"wtp {variant} cutoff {c}: fit {fit_m.sum():,} anchors, apply {apply_m.sum():,}", t0)
    out = df[["member_id", "anchor_date", "split", "y_lp_q50", "y_lp_max"]].copy()
    for k, v in pred.items():
        out[k] = v
    out["fit_cutoff"] = pd.to_datetime(pd.Series(fit_cut)).dt.date.to_numpy()
    out["source_ts_max"] = df["last_d"].to_numpy()
    return finish(out[out["wtp_q50"].notna()], variant)


def t29(results):
    """results: {(signal, variant): frame}; rows restricted to the anchors the rolling variant covers."""
    lines = []
    for signal in ("hazard", "wtp"):
        if (signal, "rolling") not in results:
            continue
        keys = results[(signal, "rolling")][["member_id", "anchor_date"]].drop_duplicates()
        for variant in VARIANTS:
            if (signal, variant) not in results:
                continue
            df = results[(signal, variant)].merge(keys, on=["member_id", "anchor_date"])
            for name, m in eval_sets(df["anchor_date"], df["split"].to_numpy()).items():
                sub = df[m]
                if signal == "hazard":
                    r = temporal_hazard.metrics(sub["label"], sub["hazard_p"])
                else:
                    r = price_wtp.metrics(sub, {k: sub[k].to_numpy() for k in price_wtp.TARGETS})
                lines.append({"signal": signal, "variant": variant, "eval": name, **r})
    return pd.DataFrame(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--signals", default="hazard,wtp")
    ap.add_argument("--variants", default=",".join(VARIANTS))
    a = ap.parse_args()
    con = connect()
    os.makedirs(ml_path("signals"), exist_ok=True)
    members, rows = inputs(con)
    nthreads = threads()
    results = {}
    for signal in a.signals.split(","):
        for variant in a.variants.split(","):
            path = out_path(signal, variant)
            if os.path.exists(path):
                results[(signal, variant)] = pd.read_parquet(path)
                continue
            out = run_hazard(members, rows, variant, nthreads) if signal == "hazard" else run_wtp(members, variant, nthreads)
            out.to_parquet(path, index=False)
            results[(signal, variant)] = out
            if variant == "rolling":
                assert_pit(con, f"read_parquet('{path}')")
    t = t29(results)
    t.to_csv(ml_path("report", "t29_signals.csv"), index=False)
    with open(ml_path("report", "t29_signals.md"), "w") as f:
        f.write("# t29 — P2 signals by fitting protocol (Δ = 30)\n\nRows: anchors covered by the rolling protocol (from the first "
                "cutoff on). train = train anchors before the pseudo-test quarter; pseudo_test = last quarter of train; test = test.\n\n")
        f.write(t.to_markdown(index=False, floatfmt=".4f"))
        f.write("\n")
    print(t.to_string(index=False, float_format=lambda x: f"{x:.4f}"))
    con.close()
    for signal in a.signals.split(","):
        publish_view(f"sig_{signal}", out_path(signal, "rolling"))


if __name__ == "__main__":
    sys.exit(main())
