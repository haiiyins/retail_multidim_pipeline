"""ML-03 / ML-04 — Where P1-frozen fails under the unconditional protocol (t28b), and whether R4 is broken or useless.

Every test positive (ml/eval/protocol.py) falls in one cell:
  top10           scored by the ranker within its first 10
  rank_11_plus    in the candidate list, ranked below 10                         → ranking error
  out_capped      a source rule would propose it, but the 200 cap cut it          → retrieval error, fixable by K / quotas
  out_no_source   no source R1–R5 proposes it, or it is outside anchor_model_grid → retrieval error, needs new sources
Source reach is recomputed per positive from the rules of gld_candidates.sql without the cap; on positives inside the list it must
agree with the r1…r5 flags (printed as a check). Cells are crossed with repeat / explore, country, segment, history length, price
tertile, popularity bucket and sport department (codes only: department labels can carry brand names).
R4 check (ML-04): coverage of favourite sports, affinity sanity, pre-cap volume and recall of R4 and of two relaxed variants.

Usage: python ml/eval/error_analysis.py [--scores p1_frozen] [--delta 30] [--out t28b]"""
import argparse, os, sys, numpy as np, pandas as pd
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.eval.protocol import ML_DIR, connect, build_positives

load_dotenv()
CELLS = ["top10", "rank_11_plus", "out_capped", "out_no_source"]


def positive_table(con, scores_path, pos_path, split):
    con.execute(f"""CREATE OR REPLACE TEMP TABLE pos AS
        SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, country_code, model_code, is_repeat FROM read_parquet('{pos_path}')""")
    con.execute(f"""CREATE OR REPLACE TEMP TABLE sc AS
        SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code,
               ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, model_code) AS rnk
        FROM read_parquet('{scores_path}') WHERE score > '-inf'::DOUBLE""")
    con.execute("""CREATE OR REPLACE TEMP TABLE pm AS SELECT DISTINCT member_id FROM pos""")
    con.execute("""CREATE OR REPLACE TEMP TABLE model_dept AS
        SELECT model_code, ANY_VALUE(sport_department_code) AS sport_department_code FROM lh.silver.slv_dim_model GROUP BY 1""")
    return con.execute(f"""
        WITH hist AS (SELECT f.member_id, f.model_code, MIN(f.transaction_date) AS first_any
                      FROM lh.silver.slv_fact_sales_line f JOIN pm USING (member_id) GROUP BY ALL),
        r2 AS (SELECT DISTINCT p.member_id, p.anchor_date, p.model_code FROM pos p
               JOIN lh.silver.slv_fact_sales_line f ON f.member_id = p.member_id
                    AND f.transaction_date BETWEEN p.anchor_date - 90 AND p.anchor_date - 1
               JOIN lh.gold.gld_copurchase_lift cp ON cp.country_code = p.country_code AND cp.model_a = f.model_code
                    AND cp.model_b = p.model_code AND cp.rank_in_a <= 20),
        r3 AS (SELECT DISTINCT p.member_id, p.anchor_date, p.model_code FROM pos p
               JOIN lh.gold.gld_web_stitched w ON w.member_id = p.member_id AND w.model_code = p.model_code
                    AND w.event_date BETWEEN p.anchor_date - 30 AND p.anchor_date - 1
                    AND w.identity_verified_ts <= CAST(p.anchor_date AS TIMESTAMP)),
        r4 AS (SELECT DISTINCT p.member_id, p.anchor_date, p.model_code FROM pos p
               JOIN lh.gold.gld_fs_member fm ON fm.member_id = p.member_id AND fm.anchor_date = p.anchor_date
               CROSS JOIN UNNEST(fm.sport_ids) AS s(sport_id)
               JOIN lh.gold.gld_sport_department_affinity aff ON aff.country_code = p.country_code AND aff.sport_id = s.sport_id
               JOIN model_dept md ON md.model_code = p.model_code AND md.sport_department_code = aff.sport_department_code
               JOIN lh.gold.gld_fs_model_country m ON m.model_code = p.model_code AND m.country_code = p.country_code
                    AND m.anchor_date = p.anchor_date
               WHERE (m.is_temp_promo OR m.seasonal_idx > 1.3) AND m.popularity_rank <= 500)
        SELECT p.*, sc.rnk, c.model_code IS NOT NULL AS in_list, c.r1, c.r2, c.r3, c.r4, c.r5,
               COALESCE(h.first_any < p.anchor_date, FALSE) AS reach_r1, r2.model_code IS NOT NULL AS reach_r2,
               r3.model_code IS NOT NULL AS reach_r3, r4.model_code IS NOT NULL AS reach_r4,
               COALESCE(m.popularity_rank <= 300, FALSE) AS reach_r5, am.model_code IS NOT NULL AS in_grid,
               m.popularity_rank, m.price_local, md.sport_department_code,
               fm.tx_365d, fm.models_365d, fm.n_sports,
               CASE WHEN fm.tx_365d <= 1 THEN 'new' WHEN fm.tx_365d >= 3 THEN 'loyal' ELSE 'mid' END AS segment
        FROM pos p
        LEFT JOIN sc USING (member_id, anchor_date, model_code)
        LEFT JOIN lh.gold.gld_candidates c ON c.member_id = p.member_id AND c.anchor_date = p.anchor_date
             AND c.model_code = p.model_code AND c.split = '{split}'
        LEFT JOIN hist h ON h.member_id = p.member_id AND h.model_code = p.model_code
        LEFT JOIN r2 USING (member_id, anchor_date, model_code)
        LEFT JOIN r3 USING (member_id, anchor_date, model_code)
        LEFT JOIN r4 USING (member_id, anchor_date, model_code)
        LEFT JOIN lh.gold.gld_fs_model_country m ON m.model_code = p.model_code AND m.country_code = p.country_code
             AND m.anchor_date = p.anchor_date
        LEFT JOIN lh.gold.anchor_model_grid am ON am.model_code = p.model_code AND am.country_code = p.country_code
             AND am.anchor_date = p.anchor_date
        LEFT JOIN model_dept md ON md.model_code = p.model_code
        LEFT JOIN lh.gold.gld_fs_member fm ON fm.member_id = p.member_id AND fm.anchor_date = p.anchor_date""").df()


def add_cells(p):
    flags = ["in_list", "in_grid", "is_repeat"] + [f"reach_r{i}" for i in range(1, 6)]
    p[flags] = p[flags].fillna(False).astype(bool)
    reach_any = (p[[f"reach_r{i}" for i in range(1, 6)]].any(axis=1) & p["in_grid"]).to_numpy()
    top10 = (p["rnk"].astype(float) <= 10).to_numpy()
    p["cell"] = np.select([top10, p["in_list"].to_numpy(), reach_any], CELLS[:3], CELLS[3])
    p["kind"] = np.where(p["is_repeat"], "repeat", "explore")
    p["history"] = pd.cut(p["models_365d"].fillna(0), [-1, 2, 5, 10, 25, np.inf], labels=["≤2", "3–5", "6–10", "11–25", ">25"]).astype(str)
    p["popularity"] = pd.cut(p["popularity_rank"].fillna(1e9), [0, 100, 300, 1000, 5000, np.inf],
                             labels=["1–100", "101–300", "301–1000", "1001–5000", ">5000 / unranked"]).astype(str)
    p["price_tertile"] = p.groupby("country_code")["price_local"].transform(
        lambda s: pd.qcut(s.rank(method="first"), 3, labels=["low", "mid", "high"]) if s.notna().sum() >= 3 else np.nan).astype(str)
    p["capped_by"] = np.select([(p["cell"] != "out_capped").to_numpy()] + [p[f"reach_r{i}"].to_numpy() for i in (1, 3, 2, 4)],
                               ["", "R1", "R3", "R2", "R4"], "R5")
    return p


def cell_table(p, by):
    t = pd.crosstab([p[b] for b in by], p["cell"], normalize="index").reindex(columns=CELLS, fill_value=0)
    t.insert(0, "positives", p.groupby(by).size())
    return t.reset_index()


def r4_check(con, split):
    con.execute(f"""CREATE OR REPLACE TEMP TABLE ea AS SELECT DISTINCT member_id, anchor_date, country_code FROM pos""")
    out = {}
    out["anchors_with_sports"] = con.execute("""SELECT AVG((COALESCE(fm.n_sports, 0) > 0)::INT) FROM ea
        LEFT JOIN lh.gold.gld_fs_member fm USING (member_id, anchor_date)""").fetchone()[0]
    out["affinity"] = con.execute("""SELECT country_code, COUNT(DISTINCT sport_id) AS sports, COUNT(*) AS rows,
            AVG(lift) AS mean_lift, AVG((lift > 1.5)::INT) AS share_lift_gt_1_5, CAST(MAX(cutoff_date) AS VARCHAR) AS cutoff
        FROM lh.gold.gld_sport_department_affinity GROUP BY 1 ORDER BY 1""").df()
    out["top_per_sport"] = con.execute("""SELECT country_code, AVG(top_share) AS top1_share_in_sport, AVG(top_lift) AS top1_lift,
            AVG(n_gt) AS depts_lift_gt_1_5
        FROM (SELECT country_code, sport_id, MAX(share_in_sport) AS top_share, MAX(lift) AS top_lift, SUM((lift > 1.5)::INT) AS n_gt
              FROM lh.gold.gld_sport_department_affinity GROUP BY 1, 2) GROUP BY 1 ORDER BY 1""").df()
    variants = {"R4 as built": "(m.is_temp_promo OR m.seasonal_idx > 1.3) AND m.popularity_rank <= 500",
                "R4 without promo / season filter": "m.popularity_rank <= 500",
                "R4 affinity lift > 1.5, top-500, no filter": "m.popularity_rank <= 500 AND aff.lift > 1.5"}
    rows = []
    for name, cond in variants.items():
        con.execute(f"""CREATE OR REPLACE TEMP TABLE r4v AS
            SELECT DISTINCT ea.member_id, ea.anchor_date, m.model_code FROM ea
            JOIN lh.gold.gld_fs_member fm USING (member_id, anchor_date)
            CROSS JOIN UNNEST(fm.sport_ids) AS s(sport_id)
            JOIN lh.gold.gld_sport_department_affinity aff ON aff.country_code = ea.country_code AND aff.sport_id = s.sport_id
            JOIN model_dept md ON md.sport_department_code = aff.sport_department_code
            JOIN lh.gold.gld_fs_model_country m ON m.model_code = md.model_code AND m.country_code = ea.country_code
                 AND m.anchor_date = ea.anchor_date
            WHERE {cond}""")
        n_anchor = con.execute("SELECT COUNT(*) FROM ea").fetchone()[0]
        vol = con.execute("SELECT COUNT(*), COUNT(DISTINCT (member_id, anchor_date)) FROM r4v").fetchone()
        hit = con.execute("SELECT COUNT(*) FROM pos JOIN r4v USING (member_id, anchor_date, model_code)").fetchone()[0]
        n_pos = con.execute("SELECT COUNT(*) FROM pos").fetchone()[0]
        rows.append({"variant": name, "anchors_with_any": vol[1] / n_anchor, "candidates_per_anchor": vol[0] / n_anchor,
                     "recall_positives": hit / n_pos, "precision": hit / vol[0] if vol[0] else np.nan})
    out["variants"] = pd.DataFrame(rows)
    out["after_cap"] = con.execute(f"""SELECT AVG(r4) AS r4_share_of_slots, AVG(r5) AS r5_share_of_slots,
            COUNT(*) / COUNT(DISTINCT (member_id, anchor_date)) AS slots_per_anchor
        FROM lh.gold.gld_candidates c JOIN ea USING (member_id, anchor_date) WHERE c.split = '{split}'""").df()
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="p1_frozen")
    ap.add_argument("--split", default="test")
    ap.add_argument("--delta", type=int, default=30)
    ap.add_argument("--out", default="t28b")
    a = ap.parse_args()
    con = connect()
    pos_path = build_positives(con, a.split, a.delta)
    scores_path = os.path.join(ML_DIR, "scores", f"{a.scores}_{a.split}_d{a.delta}.parquet")
    p = add_cells(positive_table(con, scores_path, pos_path, a.split))
    rep = os.path.join(ML_DIR, "report")
    os.makedirs(rep, exist_ok=True)
    p.to_parquet(os.path.join(ML_DIR, "eval", f"positives_cells_{a.scores}_{a.split}_d{a.delta}.parquet"), index=False)

    inl = p[p["in_list"]]
    agree = {f"r{i}": float((inl[f"r{i}"].astype(bool) == inl[f"reach_r{i}"]).mean()) for i in range(1, 6)}
    anchors = p.groupby(["member_id", "anchor_date"]).agg(any_in=("in_list", "any"), all_in=("in_list", "all"),
                                                         any_top10=("cell", lambda s: (s == "top10").any()))
    rank_missed = pd.cut(inl.loc[inl["rnk"] > 10, "rnk"], [10, 20, 50, 100, 200], labels=["11–20", "21–50", "51–100", "101–200"])
    capped = p[p["cell"] == "out_capped"]
    no_src = p[p["cell"] == "out_no_source"]
    dept = (p.assign(retrieval_miss=p["cell"].str.startswith("out")).groupby("sport_department_code")
             .agg(positives=("cell", "size"), retrieval_miss=("retrieval_miss", "mean")).sort_values("positives", ascending=False).head(15))
    r4 = r4_check(con, a.split)

    sections = [
        ("Cells by repeat / explore (share of positives)", cell_table(p, ["kind"])),
        ("Cells, all positives", cell_table(p.assign(all="ALL"), ["all"])),
        ("Cells by country", cell_table(p, ["country_code", "kind"])),
        ("Cells by segment", cell_table(p, ["segment", "kind"])),
        ("Cells by history (distinct models bought in the 365 days before the anchor)", cell_table(p, ["history"])),
        ("Cells by price tertile (within country)", cell_table(p, ["price_tertile", "kind"])),
        ("Cells by popularity rank at the anchor (country, buyers in 28 days)", cell_table(p, ["popularity", "kind"])),
        ("Rank of positives in the list but below 10", rank_missed.value_counts(normalize=True).sort_index().rename("share").reset_index()),
        ("Capped positives: highest-priority source that proposed them", capped["capped_by"].value_counts(normalize=True).rename("share").reset_index()),
        ("No-source positives: outside anchor_model_grid / popularity", pd.DataFrame({
            "share_outside_grid": [float((~no_src["in_grid"]).mean())],
            "share_popularity_301_1000": [float((no_src["popularity"] == "301–1000").mean())],
            "share_popularity_1001_5000": [float((no_src["popularity"] == "1001–5000").mean())],
            "share_popularity_gt_5000": [float((no_src["popularity"] == ">5000 / unranked").mean())]})),
        ("Top-15 sport departments by positives (codes)", dept.reset_index()),
        ("R4: favourite-sport coverage of evaluated anchors", pd.DataFrame({"share": [r4["anchors_with_sports"]]})),
        ("R4: sport × department affinity table", r4["affinity"]),
        ("R4: per sport, top department share and lift", r4["top_per_sport"]),
        ("R4: pre-cap volume and recall, as built and relaxed", r4["variants"]),
        ("Slots of the 200-cap taken by R4 / R5 on evaluated anchors", r4["after_cap"]),
    ]
    head = (f"# {a.out} — error analysis of {a.scores}, {a.split}, Δ = {a.delta}\n\n"
            f"positives {len(p):,} · anchors {len(anchors):,} · anchors with no positive in the list {1 - anchors['any_in'].mean():.1%} · "
            f"with every positive in the list {anchors['all_in'].mean():.1%} · with a top-10 hit {anchors['any_top10'].mean():.1%}\n\n"
            f"source-reach check on positives in the list (agreement with r1…r5 flags): {agree}\n")
    with open(os.path.join(rep, f"{a.out}_{a.scores}_d{a.delta}.md"), "w") as f:
        f.write(head)
        for title, t in sections:
            f.write(f"\n## {title}\n\n{t.round(4).to_markdown(index=False)}\n")
    print(head)
    pd.set_option("display.width", 250)
    for title, t in sections:
        print(f"\n## {title}\n{t.round(4).to_string(index=False)}")


if __name__ == "__main__":
    sys.exit(main())
