"""Step 6.1 — Weekly anchor grid (Mondays), WBS 3.1 (issue #29).

gold.anchor_grid: one row per eligible member × Monday inside the train / valid / test windows of evaluation/split.yml.
  eligible          at least two transactions before the anchor (anchor_date > date of the second one) and not an excluded
                    account (slv_member_profile.is_excluded_account); anchors in the purge gaps or after test_hi are not stored
  split             train / valid / test
  days_to_next_buy  days from the anchor to the member's next non-returned purchase (NULL if none) — label information, never a feature
  in_train_sample   one anchor in TRAIN_ANCHOR_STRIDE per member (hash offset spreads members over the weeks)
  is_used           the anchors downstream Gold models build candidates and pairs for:
                    (a) a purchase within ANCHOR_LABEL_HORIZON days (default 90): an anchor without one has all-zero labels, which
                        LambdaRank cannot learn from and HR / MRR / NDCG cannot score, so it only adds cost;
                    (b) train anchors also need in_train_sample;
                    (c) a deterministic cap per country and split (TRAIN_ANCHOR_CAP / VALID_ANCHOR_CAP / TEST_ANCHOR_CAP, 0 = no cap)
                        taken by hash rank, so the pair table stays near N_CANDIDATES × cap rows.
gold.anchor_model_grid: model × country × anchor_date for used anchors, models selling within ±90 days of the anchor.
gold.split_windows: the six split dates and the selection settings as one row, for dbt tests (e.g. the co-purchase cutoff).
Prints anchors per country × split before and after the rules, members, and the pair-table estimate (used anchors × N_CANDIDATES)."""
import duckdb, os, yaml, pathlib
from dotenv import load_dotenv
load_dotenv()
con = duckdb.connect(os.environ["DUCKDB_PATH"])
con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY', '10GB')}'")
con.execute(f"SET threads={int(os.environ.get('DUCKDB_THREADS', '6'))}")
stride = int(os.environ.get("TRAIN_ANCHOR_STRIDE", 4))
n_cand = int(os.environ.get("N_CANDIDATES", 200))
horizon = int(os.environ.get("ANCHOR_LABEL_HORIZON", 90))
caps = {s: int(os.environ.get(f"{s.upper()}_ANCHOR_CAP", d)) for s, d in (("train", 50000), ("valid", 15000), ("test", 50000))}
sp = yaml.safe_load(open(pathlib.Path(__file__).with_name("split.yml")))
con.execute("CREATE SCHEMA IF NOT EXISTS gold")
con.execute(f"""CREATE OR REPLACE TABLE gold.split_windows AS SELECT DATE '{sp["train_lo"]}' AS train_lo, DATE '{sp["train_hi"]}' AS train_hi,
    DATE '{sp["valid_lo"]}' AS valid_lo, DATE '{sp["valid_hi"]}' AS valid_hi, DATE '{sp["test_lo"]}' AS test_lo, DATE '{sp["test_hi"]}' AS test_hi,
    {stride} AS train_anchor_stride, {horizon} AS anchor_label_horizon, {caps["train"]} AS train_anchor_cap, {caps["valid"]} AS valid_anchor_cap,
    {caps["test"]} AS test_anchor_cap""")  # the split as a table, so dbt tests can check vars against it
con.execute(f"""
CREATE OR REPLACE TABLE gold.anchor_grid AS
WITH weeks AS (
    SELECT (DATE '{sp["train_lo"]}' + INTERVAL (7 * i) DAY)::DATE AS anchor_date, i AS week_idx
    FROM range(0, 600) t(i) WHERE DATE '{sp["train_lo"]}' + INTERVAL (7 * i) DAY <= DATE '{sp["test_hi"]}'),
weeks_split AS (
    SELECT anchor_date, week_idx,
           CASE WHEN anchor_date BETWEEN DATE '{sp["train_lo"]}' AND DATE '{sp["train_hi"]}' THEN 'train'
                WHEN anchor_date BETWEEN DATE '{sp["valid_lo"]}' AND DATE '{sp["valid_hi"]}' THEN 'valid'
                WHEN anchor_date BETWEEN DATE '{sp["test_lo"]}'  AND DATE '{sp["test_hi"]}'  THEN 'test' END AS split
    FROM weeks),
tx AS (SELECT DISTINCT member_id, country_code, transaction_id, transaction_date
       FROM silver.slv_fact_sales_line WHERE member_id IS NOT NULL),
ordered AS (SELECT member_id, country_code, transaction_date,
                   ROW_NUMBER() OVER (PARTITION BY member_id ORDER BY transaction_date, transaction_id) AS tx_rank FROM tx),
elig AS (SELECT o.member_id, ANY_VALUE(o.country_code) AS country_code,
                MIN(CASE WHEN tx_rank = 2 THEN transaction_date END) AS second_d
         FROM ordered o LEFT JOIN silver.slv_member_profile p USING (member_id)
         WHERE COALESCE(p.is_excluded_account, false) = false
         GROUP BY 1 HAVING second_d IS NOT NULL),
grid AS (SELECT e.member_id, e.country_code, w.anchor_date, w.week_idx, w.split,
                ((hash(e.member_id) + w.week_idx) % {stride} = 0) AS in_train_sample
         FROM elig e JOIN weeks_split w ON w.anchor_date > e.second_d AND w.split IS NOT NULL),
buy AS (SELECT DISTINCT f.member_id, f.transaction_date FROM silver.slv_fact_sales_line f
        WHERE f.member_id IS NOT NULL
          AND NOT EXISTS (SELECT 1 FROM silver.slv_fact_returns r WHERE r.transaction_id = f.transaction_id)),
labelled AS (SELECT g.*, b.transaction_date - g.anchor_date AS days_to_next_buy
             FROM grid g ASOF LEFT JOIN buy b ON b.member_id = g.member_id AND b.transaction_date > g.anchor_date),
candidates AS (SELECT *, (COALESCE(days_to_next_buy <= {horizon}, false) OR {horizon} = 0)
                         AND (split <> 'train' OR in_train_sample) AS passes_rules FROM labelled),
ranked AS (SELECT *, CASE WHEN passes_rules THEN ROW_NUMBER() OVER (PARTITION BY country_code, split, passes_rules
                                                                    ORDER BY hash(member_id, anchor_date)) END AS sample_rank
           FROM candidates)
SELECT member_id, country_code, anchor_date, week_idx, split, days_to_next_buy, in_train_sample,
       passes_rules AND sample_rank <= CASE split WHEN 'train' THEN {caps['train']} WHEN 'valid' THEN {caps['valid']} ELSE {caps['test']} END
           AS is_used
FROM ranked""")
con.execute("""
CREATE OR REPLACE TABLE gold.anchor_model_grid AS
SELECT DISTINCT a.country_code, a.anchor_date, m.model_code
FROM (SELECT DISTINCT country_code, anchor_date FROM gold.anchor_grid WHERE is_used) a
JOIN (SELECT country_code, model_code, MIN(transaction_date) d0, MAX(transaction_date) d1
      FROM silver.slv_fact_sales_line GROUP BY 1, 2) m
  ON m.country_code = a.country_code AND a.anchor_date BETWEEN m.d0 - INTERVAL 90 DAY AND m.d1 + INTERVAL 90 DAY""")
print(f"TRAIN_ANCHOR_STRIDE={stride}  N_CANDIDATES={n_cand}  ANCHOR_LABEL_HORIZON={horizon}  caps per country {caps}")
print(f"split: train {sp['train_lo']}→{sp['train_hi']}, valid {sp['valid_lo']}→{sp['valid_hi']}, test {sp['test_lo']}→{sp['test_hi']}")
summary = con.execute(f"""
SELECT country_code, split, COUNT(*) AS anchors, COUNT(DISTINCT member_id) AS members,
       SUM(CASE WHEN days_to_next_buy <= {horizon} THEN 1 ELSE 0 END) AS with_purchase_in_horizon,
       SUM(CASE WHEN days_to_next_buy <= {horizon} AND (split <> 'train' OR in_train_sample) THEN 1 ELSE 0 END) AS after_stride,
       SUM(is_used::INT) AS used_anchors, COUNT(DISTINCT CASE WHEN is_used THEN member_id END) AS used_members,
       SUM(is_used::INT) * {n_cand} AS pair_rows_estimate
FROM gold.anchor_grid GROUP BY 1, 2 ORDER BY 1, CASE split WHEN 'train' THEN 1 WHEN 'valid' THEN 2 ELSE 3 END""").df()
print(summary.to_string(index=False))
print(con.execute("SELECT country_code, COUNT(*) AS model_anchor_rows, COUNT(DISTINCT anchor_date) AS anchor_dates, COUNT(DISTINCT model_code) AS models FROM gold.anchor_model_grid GROUP BY 1").df().to_string(index=False))
