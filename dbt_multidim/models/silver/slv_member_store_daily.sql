-- Running usual store per member × purchase day (issue #23): for every day a member bought offline, the store with the most
-- offline transactions up to and including that day (ties → most recently visited store, then the smaller store id).
-- Gold reads the latest row with as_of_date < anchor_date, so the usual store is known point-in-time.
WITH daily AS (
  SELECT member_id, store_id, country_code, transaction_date AS d, COUNT(DISTINCT transaction_id) AS n_tx, COUNT(*) AS n_lines
  FROM {{ ref('slv_fact_sales_line') }}
  WHERE member_id IS NOT NULL AND channel = 'offline'
  GROUP BY 1, 2, 3, 4
),
member_days AS (SELECT DISTINCT member_id, d FROM daily),
as_of_counts AS (   -- 'asof' is a DuckDB keyword
  SELECT m.member_id, m.d, s.store_id, s.country_code, SUM(s.n_tx) AS cum_tx, SUM(s.n_lines) AS cum_lines, MAX(s.d) AS last_visit
  FROM member_days m JOIN daily s ON s.member_id = m.member_id AND s.d <= m.d
  GROUP BY 1, 2, 3, 4
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY member_id, d ORDER BY cum_tx DESC, last_visit DESC, store_id) AS rn,
         SUM(cum_tx) OVER (PARTITION BY member_id, d) AS total_tx, COUNT(*) OVER (PARTITION BY member_id, d) AS n_stores
  FROM as_of_counts
)
SELECT member_id, d AS as_of_date, store_id AS usual_store_id, country_code AS usual_store_country,
       cum_tx AS usual_store_tx, total_tx AS offline_tx_cum, n_stores AS stores_visited_cum,
       ROUND(cum_tx * 1.0 / total_tx, 3) AS usual_store_share, last_visit AS usual_store_last_visit
FROM ranked WHERE rn = 1
