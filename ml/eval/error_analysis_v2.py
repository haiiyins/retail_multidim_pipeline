"""Where the test positives end up with ml.candidates_v2 and the two-stage ranker (t28c, the v2 counterpart of t28b), and the
ceiling the 5 000-model universe of the learned sources sets.

Every test positive (ml/eval/protocol.py, Δ = 30) falls in one cell:
  top20               scored by the ranker within its first 20
  rank_21_plus        in candidates_v2 (K = mixer.k), ranked below 20                     → ranking error
  out_capped          proposed by a source list (R1–R3, R5 of gld_candidates or a learned
                      source, top n_out), but cut by the mixer at K                        → fixable by K / weights
  out_no_source_uni   proposed by no source, inside the universe of its cutoff and the grid → needs better sources
  out_no_source_out   proposed by no source, outside the universe or anchor_model_grid       → unreachable by the learned sources
Cells are shares of the pooled positives, by scope (ALL, MAIN = TH + VN) and repeat / explore; the capped positives are split by
the sources proposing them (R5, a learned source, R5 only). The ceiling table gives, per scope, the
share of positives inside the universe at the anchor's cutoff (top universe.size models by buyers in the window before the cutoff),
inside anchor_model_grid, inside both, and reachable at all (inside both or proposed by a source), pooled and as the member-mean of the
per-anchor share (the Recall@∞ of an oracle that ranks every reachable positive).
Usage: python ml/eval/error_analysis_v2.py [--scores p3_onehead] [--out t28c]"""
import argparse, os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, ml_path
from ml.common.pit import cutoff_case_sql, cutoffs
from ml.eval.protocol import MAIN_COUNTRIES, build_positives
from ml.retrieval.base import CFG
from ml.retrieval.mixer import BASE_SOURCES, learned_sources, source_relation

DELTA = 30
CELLS = ["top20", "rank_21_plus", "out_capped", "out_no_source_uni", "out_no_source_out"]


def universe(con):
    size, window = CFG["universe"]["size"], CFG["universe"]["window_days"]
    cuts = ", ".join(f"(DATE '{c}')" for c in cutoffs())
    con.execute(f"""CREATE OR REPLACE TEMP TABLE uni AS
        WITH c(cutoff) AS (VALUES {cuts}),
        b AS (SELECT f.country_code, c.cutoff, f.model_code, COUNT(DISTINCT f.member_id) AS buyers
              FROM lh.silver.slv_fact_sales_line f JOIN c ON f.transaction_date < c.cutoff AND f.transaction_date >= c.cutoff - {window}
              WHERE f.member_id IS NOT NULL AND f.model_code IS NOT NULL GROUP BY ALL)
        SELECT country_code, cutoff, model_code FROM b
        QUALIFY ROW_NUMBER() OVER (PARTITION BY country_code, cutoff ORDER BY buyers DESC, model_code) <= {size}""")


def positive_table(con, scores, split="test"):
    pos = build_positives(con, split, DELTA)
    k = CFG["mixer"]["k"]
    proposed = " UNION ALL ".join(f"SELECT member_id, anchor_date, model_code, '{s}' AS src FROM {source_relation(s, split)}"
                                  for s in list(BASE_SOURCES) + learned_sources())
    con.execute(f"""CREATE OR REPLACE TEMP TABLE prop AS
        SELECT member_id, anchor_date, model_code, BOOL_OR(src = 'r5') AS by_r5,
               BOOL_OR(src NOT IN ({", ".join(f"'{s}'" for s in BASE_SOURCES)})) AS by_learned
        FROM ({proposed}) GROUP BY ALL""")
    return con.execute(f"""
        WITH p AS (SELECT member_id, country_code, CAST(anchor_date AS DATE) AS anchor_date, model_code, is_repeat,
                          {cutoff_case_sql("CAST(anchor_date AS DATE)")} AS cutoff FROM read_parquet('{pos}')),
        cand AS (SELECT member_id, anchor_date, model_code FROM read_parquet('{ml_path("candidates_v2", f"{split}_*.parquet")}')
                 WHERE candidate_rank <= {k}),
        sc AS (SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code,
                      ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, model_code) AS rnk
               FROM read_parquet('{ml_path("scores", f"{scores}_{split}_d{DELTA}.parquet")}') WHERE score > '-inf'::DOUBLE)
        SELECT p.member_id, p.country_code, p.anchor_date, p.is_repeat,
               c.model_code IS NOT NULL AS in_list, sc.rnk, pr.model_code IS NOT NULL AS proposed,
               COALESCE(pr.by_r5, FALSE) AS by_r5, COALESCE(pr.by_learned, FALSE) AS by_learned,
               u.model_code IS NOT NULL AS in_universe, g.model_code IS NOT NULL AS in_grid
        FROM p
        LEFT JOIN cand c USING (member_id, anchor_date, model_code)
        LEFT JOIN sc USING (member_id, anchor_date, model_code)
        LEFT JOIN prop pr USING (member_id, anchor_date, model_code)
        LEFT JOIN uni u ON u.country_code = p.country_code AND u.cutoff = p.cutoff AND u.model_code = p.model_code
        LEFT JOIN lh.gold.anchor_model_grid g ON g.country_code = p.country_code AND g.anchor_date = p.anchor_date
             AND g.model_code = p.model_code""").df()


def cell(d):
    out = pd.Series("out_no_source_out", index=d.index)
    out[d["in_universe"] & d["in_grid"]] = "out_no_source_uni"
    out[d["proposed"]] = "out_capped"
    out[d["in_list"]] = "rank_21_plus"
    out[d["in_list"] & (d["rnk"] <= 20)] = "top20"
    return out


def scopes(d):
    yield "ALL", d
    yield "MAIN (TH+VN)", d[d["country_code"].isin(MAIN_COUNTRIES)]


def fate(d):
    rows = []
    for scope, s in scopes(d):
        for kind, x in (("all", s), ("repeat", s[s["is_repeat"]]), ("explore", s[~s["is_repeat"]])):
            r = x["cell"].value_counts(normalize=True).reindex(CELLS, fill_value=0.0)
            cap = x[x["cell"] == "out_capped"]
            rows.append({"scope": scope, "positives": kind, "n": len(x), **r.to_dict(),
                         "capped: by R5": cap["by_r5"].mean(), "capped: by a learned source": cap["by_learned"].mean(),
                         "capped: by R5 only": (cap["by_r5"] & ~cap["by_learned"]).mean()})
    return pd.DataFrame(rows)


def ceiling(d):
    d = d.assign(both=d["in_universe"] & d["in_grid"], reachable=(d["in_universe"] & d["in_grid"]) | d["proposed"] | d["in_list"])
    cols = ["in_universe", "in_grid", "both", "reachable", "in_list"]
    rows = []
    for scope, s in scopes(d):
        for kind, x in (("all", s), ("explore", s[~s["is_repeat"]])):
            pooled = x[cols].mean()
            member = x.groupby(["member_id", "anchor_date"])[cols].mean().groupby("member_id").mean().mean()
            rows.append({"scope": scope, "positives": kind, "measure": "pooled", **pooled.to_dict()})
            rows.append({"scope": scope, "positives": kind, "measure": "member mean", **member.to_dict()})
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--scores", default="p3_onehead")
    ap.add_argument("--out", default="t28c")
    a = ap.parse_args()
    con = connect()
    universe(con)
    d = positive_table(con, a.scores)
    d["cell"] = cell(d)
    f, c = fate(d), ceiling(d)
    path = os.path.join(ML_DIR, "report", f"{a.out}.md")
    with open(path, "w") as fh:
        fh.write(f"# {a.out}: fate of the test positives, candidates_v2 (K = {CFG['mixer']['k']}) + {a.scores}, Δ = {DELTA}\n\n")
        fh.write(f.to_markdown(index=False, floatfmt=".4f") + "\n\n")
        fh.write(f"# {a.out}: universe ceiling (top {CFG['universe']['size']} by buyers in the {CFG['universe']['window_days']} days "
                 "before the anchor's cutoff)\n\n")
        fh.write(c.to_markdown(index=False, floatfmt=".4f") + "\n")
    print(f.round(4).to_string(index=False))
    print(c.round(4).to_string(index=False))
    print(f"→ {path}")


if __name__ == "__main__":
    sys.exit(main())
