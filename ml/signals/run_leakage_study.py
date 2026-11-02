"""H2 leakage study (plan §6, ML-16) → t29b: the same GBDT fusion (P1-frozen hyper-parameters) on the ranking pairs plus the P2
signal features of one fitting protocol {rolling, naive, leaky}, against the pairs alone (none).

Fusion fit: train-sample anchors whose Δ window closes before the pseudo-test quarter. Measured, with the unconditional protocol
(D3), on those same training anchors, on the pseudo-test quarter (last quarter of train) and on test. H2 expects naive and leaky to
look better than rolling on the training anchors and the pseudo-test, and the gap to shrink, but not vanish, on test.
Signal features of a candidate: hazard_p of its department, wtp_q50 / wtp_q90, and the gaps of its log price to them.
Usage: python ml/signals/run_leakage_study.py [--source v1|v2]"""
import argparse, os, sys, time
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path
from ml.common.pit import last_fit_anchor
from ml.eval.protocol import build_positives, evaluate, member_bootstrap
from ml.rankers.frozen import relation, scores, train, v1_features
from ml.rankers.gbdt import load
from ml.signals.base import DELTA, PSEUDO_TEST_LO, VARIANTS, out_path

SIGNAL_FEATURES = ["hazard_p", "wtp_q50", "wtp_q90", "wtp_gap50", "wtp_gap90"]


def add_signals(con, df, variant):
    hz = pd.read_parquet(out_path("hazard", variant), columns=["member_id", "anchor_date", "dept", "hazard_p"])
    wtp = pd.read_parquet(out_path("wtp", variant), columns=["member_id", "anchor_date", "wtp_q50", "wtp_q90"])
    for x in (hz, wtp):
        x["anchor_date"] = pd.to_datetime(x["anchor_date"])
    out = df.merge(hz, how="left", on=["member_id", "anchor_date", "dept"]).merge(wtp, how="left", on=["member_id", "anchor_date"])
    lp = np.log(out["price_local"].where(out["price_local"] > 0))
    out["wtp_gap50"], out["wtp_gap90"] = lp - out["wtp_q50"], lp - out["wtp_q90"]
    return out


def with_dept(con, df):
    dm = con.execute("""SELECT model_code, COALESCE(MODE(sport_department_code), -1)::INT AS dept FROM lh.silver.slv_dim_model
                        GROUP BY 1""").df()
    df = df.merge(dm, how="left", on="model_code")
    df["dept"] = df["dept"].fillna(-1).astype(int)
    df["anchor_date"] = pd.to_datetime(df["anchor_date"])
    return df


def anchors_of(con, rel, split, lo=None, hi=None):
    cond = ["in_train_sample"] if split == "train" else []
    if lo:
        cond.append(f"anchor_date >= DATE '{lo}'")
    if hi:
        cond.append(f"anchor_date <= DATE '{hi}'")
    from ml.common.data import split_windows
    sw = split_windows()
    cond.append(f"anchor_date BETWEEN DATE '{sw[split + '_lo']}' AND DATE '{sw[split + '_hi']}'")
    return con.execute(f"SELECT DISTINCT member_id, CAST(anchor_date AS DATE) AS anchor_date FROM {rel} WHERE {' AND '.join(cond)}").df()


def ndcg(con, sc, split, anchors):
    pos = pd.read_parquet(build_positives(con, split, DELTA))
    pos["anchor_date"] = pd.to_datetime(pos["anchor_date"]).dt.date
    anchors = anchors.assign(anchor_date=pd.to_datetime(anchors["anchor_date"]).dt.date)
    pos = pos.merge(anchors, on=["member_id", "anchor_date"])
    con.register("_s", sc)
    con.register("_p", pos)
    res = evaluate(con, "_s", "_p")
    con.unregister("_s"); con.unregister("_p")
    main = res[res["country_code"].isin(["TH", "VN"])]
    m, lo, hi = member_bootstrap(main, "NDCG@20")
    return {"anchors": len(main), "NDCG@20": m, "ci_lo": lo, "ci_hi": hi}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="v1")
    ap.add_argument("--variants", default="none," + ",".join(VARIANTS))
    a = ap.parse_args()
    con = connect()
    rel = relation(a.source)
    t0 = time.time()
    tr_all = with_dept(con, load(con, "train", DELTA, rel))
    te = with_dept(con, load(con, "test", DELTA, rel))
    fit_hi = last_fit_anchor(PSEUDO_TEST_LO, DELTA)
    in_fit = tr_all["anchor_date"].dt.date <= fit_hi
    in_pseudo = tr_all["anchor_date"].dt.date >= PSEUDO_TEST_LO
    sets = {"train": (tr_all[in_fit], "train", anchors_of(con, rel, "train", hi=fit_hi)),
            "pseudo_test": (tr_all[in_pseudo], "train", anchors_of(con, rel, "train", lo=PSEUDO_TEST_LO)),
            "test": (te, "test", anchors_of(con, rel, "test"))}
    base_feat = [c for c in v1_features(con) if c in tr_all.columns]
    print(f"fit {in_fit.sum():,} rows · pseudo-test {in_pseudo.sum():,} · test {len(te):,} · {time.time() - t0:.0f}s", flush=True)
    rows = []
    for variant in a.variants.split(","):
        feat = base_feat + ([] if variant == "none" else SIGNAL_FEATURES)
        prep = (lambda d: d) if variant == "none" else (lambda d, v=variant: add_signals(con, d, v))
        fit_df = prep(sets["train"][0])
        m = train(fit_df, feat, DELTA)
        for name, (df, split, anc) in sets.items():
            r = ndcg(con, scores(m, prep(df) if name != "train" else fit_df, feat), split, anc)
            rows.append({"variant": variant, "eval": name, **r})
            print(f"  {variant:8s} {name:12s} NDCG@20 {r['NDCG@20']:.4f} [{r['ci_lo']:.4f}, {r['ci_hi']:.4f}]  {time.time() - t0:.0f}s", flush=True)
    t = pd.DataFrame(rows)
    piv = t.pivot(index="variant", columns="eval", values="NDCG@20")[["train", "pseudo_test", "test"]]
    if "rolling" in piv.index:
        for e in ("train", "pseudo_test", "test"):
            piv[f"Δ {e} vs rolling"] = piv[e] - piv.loc["rolling", e]
    t.to_csv(ml_path("report", f"t29b_{a.source}.csv"), index=False)
    with open(ml_path("report", f"t29b_{a.source}.md"), "w") as f:
        f.write(f"# t29b — H2 leakage study ({a.source} pairs, Δ = {DELTA}, unconditional NDCG@20, TH + VN)\n\n"
                f"Fusion = P1-frozen hyper-parameters on the pair features (+ the P2 signals of one protocol), fitted on train anchors "
                f"≤ {fit_hi}; pseudo_test = train anchors ≥ {PSEUDO_TEST_LO}. 95 % member-bootstrap intervals in t29b_{a.source}.csv.\n\n")
        f.write(piv.to_markdown(floatfmt=".4f"))
        f.write("\n")
    print(piv.to_string(float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    sys.exit(main())
