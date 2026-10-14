"""Step 6.1 — Weekly anchor grid (Mondays). Training anchors are sampled with TRAIN_ANCHOR_STRIDE; evaluation uses every anchor.
Creates gold.anchor_grid (member × anchor_date) and gold.anchor_model_grid (model × country × anchor_date)."""
import duckdb, os
from dotenv import load_dotenv
load_dotenv()
con = duckdb.connect(os.environ["DUCKDB_PATH"])
stride = int(os.environ.get("TRAIN_ANCHOR_STRIDE", 4))
con.execute("CREATE SCHEMA IF NOT EXISTS gold")
con.execute(f"""
CREATE OR REPLACE TABLE gold.anchor_grid AS
WITH span AS (SELECT MIN(transaction_date) d0, MAX(transaction_date) d1 FROM silver.slv_fact_sales_line),
weeks AS (SELECT (date_trunc('week', d0) + INTERVAL (7 * i) DAY)::DATE AS anchor_date, i AS week_idx
          FROM span, range(0, 400) t(i) WHERE date_trunc('week', d0) + INTERVAL (7 * i) DAY <= d1),
ordered AS (SELECT member_id, country_code, transaction_date,
                   DENSE_RANK() OVER (PARTITION BY member_id ORDER BY transaction_date, transaction_id) AS tx_rank
            FROM (SELECT DISTINCT member_id, country_code, transaction_id, transaction_date FROM silver.slv_fact_sales_line WHERE member_id IS NOT NULL)),
elig AS (SELECT o.member_id, ANY_VALUE(o.country_code) country_code, MIN(CASE WHEN tx_rank = 2 THEN transaction_date END) AS second_d
         FROM ordered o LEFT JOIN silver.slv_member_profile p USING (member_id)
         WHERE COALESCE(p.is_excluded_account, false) = false GROUP BY 1 HAVING second_d IS NOT NULL)
SELECT e.member_id, e.country_code, w.anchor_date, w.week_idx,
       ((hash(e.member_id) + w.week_idx) % {stride} = 0) AS in_train_sample
FROM elig e JOIN weeks w ON w.anchor_date > e.second_d""")
con.execute("""
CREATE OR REPLACE TABLE gold.anchor_model_grid AS
SELECT DISTINCT a.country_code, a.anchor_date, m.model_code
FROM (SELECT DISTINCT country_code, anchor_date FROM gold.anchor_grid) a
JOIN (SELECT country_code, model_code, MIN(transaction_date) d0, MAX(transaction_date) d1 FROM silver.slv_fact_sales_line GROUP BY 1, 2) m
  ON m.country_code = a.country_code AND a.anchor_date BETWEEN m.d0 - INTERVAL 90 DAY AND m.d1 + INTERVAL 90 DAY""")
print(con.execute("SELECT country_code, COUNT(*) anchors, SUM(in_train_sample::INT) train_anchors, COUNT(DISTINCT member_id) members FROM gold.anchor_grid GROUP BY 1").df())
print(con.execute("SELECT country_code, COUNT(*) model_anchor_rows FROM gold.anchor_model_grid GROUP BY 1").df())
