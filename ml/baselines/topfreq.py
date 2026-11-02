"""ML-18 — P-TopFreq and GP-TopFreq (Li et al., NBR Reality Check, TOIS 2023), scored on the full catalogue for t31.

P-TopFreq   the member's models ranked by the number of distinct days she bought them before the anchor, ties by the latest purchase:
            the buy-again reference of the repeat side.
GP-TopFreq  P-TopFreq, then filled with the country best-sellers at the anchor (gold.gld_fs_model_country.popularity_rank, buyers in
            the 28 days before the anchor) that she has not bought.
No parameters, so no tuning budget. Top n per anchor → data/ml/scores/<name>_<split>_d<Δ>.parquet, the input of ml/eval/protocol.py.
Usage: python ml/baselines/topfreq.py [--splits valid,test] [--n 100]"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect


def personal(split):
    return f"""(SELECT g.member_id, g.country_code, g.anchor_date, f.model_code,
                       COUNT(DISTINCT f.transaction_date) + 1.0 / (2 + (g.anchor_date - MAX(f.transaction_date))) AS score
                FROM lh.gold.anchor_grid g JOIN lh.silver.slv_fact_sales_line f
                  ON f.member_id = g.member_id AND f.transaction_date < g.anchor_date AND f.model_code IS NOT NULL
                WHERE g.is_used AND g.split = '{split}' GROUP BY 1, 2, 3, 4)"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="valid,test")
    ap.add_argument("--n", type=int, default=100)
    ap.add_argument("--delta", type=int, default=30)
    a = ap.parse_args()
    con = connect(threads=16)
    con.execute("SET memory_limit='60GB'")
    os.makedirs(os.path.join(ML_DIR, "scores"), exist_ok=True)
    for split in a.splits.split(","):
        p = personal(split)
        queries = {
            "ptopfreq": f"SELECT * FROM {p}",
            "gptopfreq": f"""SELECT * FROM {p} UNION ALL
                SELECT g.member_id, g.country_code, g.anchor_date, m.model_code, -m.popularity_rank AS score
                FROM lh.gold.anchor_grid g JOIN lh.gold.gld_fs_model_country m
                  ON m.country_code = g.country_code AND m.anchor_date = g.anchor_date AND m.popularity_rank <= {int(a.n)}
                WHERE g.is_used AND g.split = '{split}'
                  AND NOT EXISTS (SELECT 1 FROM lh.silver.slv_fact_sales_line f WHERE f.member_id = g.member_id
                                  AND f.model_code = m.model_code AND f.transaction_date < g.anchor_date)"""}
        for name, q in queries.items():
            out = os.path.join(ML_DIR, "scores", f"{name}_{split}_d{a.delta}.parquet")
            con.execute(f"""COPY (SELECT member_id, CAST(anchor_date AS TIMESTAMP) AS anchor_date, model_code, country_code, score FROM ({q})
                             QUALIFY ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, model_code) <= {int(a.n)})
                             TO '{out}' (FORMAT parquet)""")
            print(f"  {name} {split}: {con.execute(f'SELECT COUNT(*) FROM read_parquet(?)', [out]).fetchone()[0]:,} rows", flush=True)


if __name__ == "__main__":
    sys.exit(main())
