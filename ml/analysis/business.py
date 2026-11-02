"""Feasibility (plan §11, RQ4): t38 business multiples and GMV proxies, t39 serving coverage. Test split, Δ = 30, unconditional.

t38  HR@10 / Recall@10 of the best model against random (analytic: 10 slots drawn from the 5 000-model universe), popular (country
     best-sellers) and buy-again (P-TopFreq), by scope and for repeat / explore positives; GMV-weighted Recall@10 (positives weighted
     by the EUR value bought in (t, t + Δ]) and GMV captured per 1 000 recommendations (proxy, offline, not causal: D11).
t39  share of test anchors / members / positive GMV the personalised path serves (purchase history before t), the fallback
     (popular) for the rest, and the share of anchors with ≥ 10 candidates in ml.candidates_v2.
Usage: python ml/analysis/business.py --best p3_full [--label "P3"]"""
import argparse, os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, ml_path, split_windows

UNIVERSE = 5000
DELTA = 30


def positives_gmv(con):
    sw = split_windows()
    return con.execute(f"""
        WITH a AS (SELECT member_id, country_code, anchor_date FROM lh.gold.anchor_grid WHERE split = 'test' AND is_used),
        buy AS (SELECT f.member_id, f.model_code, f.transaction_date, f.gmv_eur FROM lh.silver.slv_fact_sales_line f
                WHERE f.member_id IS NOT NULL AND f.model_code IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM lh.silver.slv_fact_returns r WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code)),
        first_buy AS (SELECT member_id, model_code, MIN(transaction_date) AS first_d FROM buy GROUP BY ALL)
        SELECT a.member_id, a.country_code, CAST(a.anchor_date AS DATE) AS anchor_date, b.model_code, SUM(b.gmv_eur) AS gmv,
               ANY_VALUE(fb.first_d) <= a.anchor_date AS is_repeat
        FROM a JOIN buy b ON b.member_id = a.member_id AND b.transaction_date > a.anchor_date AND b.transaction_date <= a.anchor_date + {DELTA}
        JOIN first_buy fb ON fb.member_id = b.member_id AND fb.model_code = b.model_code
        GROUP BY 1, 2, 3, 4""").df()


def hits10(con, name, pos):
    path = os.path.join(ML_DIR, "scores", f"{name}_test_d{DELTA}.parquet")
    con.register("_p", pos)
    df = con.execute(f"""
        WITH s AS (SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code FROM read_parquet('{path}')
                   WHERE score > '-inf'::DOUBLE
                   QUALIFY ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, model_code) <= 10)
        SELECT p.*, s.model_code IS NOT NULL AS hit FROM _p p LEFT JOIN s USING (member_id, anchor_date, model_code)""").df()
    con.unregister("_p")
    return df


def segments(con):
    seg = con.execute("""SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date,
                                CASE WHEN tx_365d <= 1 THEN 'new' WHEN tx_365d >= 3 THEN 'loyal' ELSE 'mid' END AS segment
                         FROM lh.gold.gld_fs_member""").df()
    return seg


def scopes(df):
    yield "ALL", df
    yield "MAIN (TH+VN)", df[df["country_code"].isin(["TH", "VN"])]
    for c in sorted(df["country_code"].unique()):
        yield c, df[df["country_code"] == c]
    for s in ("new", "mid", "loyal"):
        yield f"segment:{s}", df[df["segment"] == s]


def anchor_metrics(h, kind):
    sub = h if kind == "all" else h[h["is_repeat"] == (kind == "repeat")]
    g = sub.groupby(["member_id", "anchor_date"]).agg(country_code=("country_code", "first"), segment=("segment", "first"),
                                                       n=("hit", "size"), hits=("hit", "sum"), gmv=("gmv", "sum"),
                                                       gmv_hit=("gmv_hit", "sum"))
    g["HR@10"] = (g["hits"] > 0).astype(float)
    g["Recall@10"] = g["hits"] / g["n"]
    g["random_HR@10"] = 1 - (1 - 10 / UNIVERSE) ** g["n"]
    g["random_Recall@10"] = 10 / UNIVERSE
    return g.reset_index()


def member_mean(d, col):
    return d.groupby("member_id")[col].mean().mean()


def t38(con, best, label, pos, seg):
    models = {label: best, "popular": "popular", "buy-again (P-TopFreq)": "ptopfreq"}
    per = {}
    for lab, name in models.items():
        h = hits10(con, name, pos).merge(seg, on=["member_id", "anchor_date"], how="left")
        h["gmv_hit"] = np.where(h["hit"], h["gmv"], 0.0)
        per[lab] = {k: anchor_metrics(h, k) for k in ("all", "repeat", "explore")}
    rows = []
    for kind in ("all", "repeat", "explore"):
        for scope, _ in scopes(per[label][kind]):
            r = {"positives": kind, "scope": scope}
            for lab in models:
                d = dict(scopes(per[lab][kind]))[scope]
                r[f"HR@10 {lab}"] = member_mean(d, "HR@10")
                if lab == label:
                    r["HR@10 random"] = member_mean(d, "random_HR@10")
                    r["anchors"] = len(d)
            r["× random"] = r[f"HR@10 {label}"] / r["HR@10 random"]
            r["× popular"] = r[f"HR@10 {label}"] / r["HR@10 popular"]
            r["× buy-again"] = r[f"HR@10 {label}"] / max(r["HR@10 buy-again (P-TopFreq)"], 1e-9)
            rows.append(r)
    mult = pd.DataFrame(rows)
    gmv_rows = []
    for lab in models:
        for scope, d in scopes(per[lab]["all"]):
            gmv_rows.append({"model": lab, "scope": scope, "GMV-weighted Recall@10": d["gmv_hit"].sum() / d["gmv"].sum(),
                             "GMV captured / 1 000 recommendations (EUR)": d["gmv_hit"].sum() / (len(d) * 10) * 1000})
    return mult, pd.DataFrame(gmv_rows)


def t39(con, pos):
    cand = ml_path("candidates_v2", "test_*.parquet")
    return con.execute(f"""
        WITH a AS (SELECT g.member_id, g.country_code, g.anchor_date,
                          EXISTS (SELECT 1 FROM lh.silver.slv_fact_sales_line f WHERE f.member_id = g.member_id
                                  AND f.transaction_date < g.anchor_date) AS has_history
                   FROM lh.gold.anchor_grid g WHERE g.split = 'test' AND g.is_used),
        c AS (SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, COUNT(*) AS n_cand FROM read_parquet('{cand}') GROUP BY 1, 2),
        v AS (SELECT member_id, anchor_date, SUM(gmv) AS gmv FROM _p GROUP BY 1, 2)
        SELECT a.country_code, COUNT(*) AS anchors, COUNT(DISTINCT a.member_id) AS members,
               AVG(a.has_history::INT) AS share_personalised, 1 - AVG(a.has_history::INT) AS share_fallback_popular,
               SUM(v.gmv) FILTER (WHERE a.has_history) / SUM(v.gmv) AS share_positive_gmv_personalised,
               AVG((COALESCE(c.n_cand, 0) >= 10)::INT) AS share_anchors_10_candidates,
               MEDIAN(COALESCE(c.n_cand, 0)) AS median_candidates
        FROM a LEFT JOIN c ON c.member_id = a.member_id AND c.anchor_date = CAST(a.anchor_date AS DATE)
        LEFT JOIN v ON v.member_id = a.member_id AND v.anchor_date = CAST(a.anchor_date AS DATE)
        GROUP BY ROLLUP (a.country_code) ORDER BY a.country_code NULLS LAST""").df().fillna({"country_code": "ALL"})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--best", required=True)
    ap.add_argument("--label", default=None)
    a = ap.parse_args()
    label = a.label or a.best
    con = connect()
    pos = positives_gmv(con)
    seg = segments(con)
    mult, gmv = t38(con, a.best, label, pos, seg)
    con.register("_p", pos)
    cov = t39(con, pos)
    with open(ml_path("report", "t38.md"), "w") as f:
        f.write(f"# t38 — {label} against business references (test, Δ = 30, unconditional, member means)\n\n"
                f"random = 10 slots drawn uniformly from the {UNIVERSE}-model universe (analytic). GMV figures are an offline proxy, "
                f"not a causal estimate (D11).\n\n")
        f.write(mult.to_markdown(index=False, floatfmt=".4f") + "\n\n")
        f.write(gmv.to_markdown(index=False, floatfmt=".4f") + "\n")
    with open(ml_path("report", "t39.md"), "w") as f:
        f.write("# t39 — serving coverage (test anchors)\n\nPersonalised path: the member has a purchase before the anchor; "
                "the others get the fallback (country best-sellers).\n\n")
        f.write(cov.to_markdown(index=False, floatfmt=".4f") + "\n")
    mult.to_csv(ml_path("report", "t38.csv"), index=False)
    cov.to_csv(ml_path("report", "t39.csv"), index=False)
    pd.set_option("display.width", 250)
    print(mult[mult["scope"].isin(["ALL", "MAIN (TH+VN)"])].round(4).to_string(index=False))
    print(gmv[gmv["scope"] == "MAIN (TH+VN)"].round(4).to_string(index=False))
    print(cov.round(4).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
