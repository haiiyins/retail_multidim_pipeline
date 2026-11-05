-- Sample representativeness: share of each segment, label horizon and quarter among the used anchors (the per-country hash-rank
-- sample) against the rest of the pool they were drawn from (days_to_next_buy <= 90 and, in train, the training stride).
-- gold.gld_fs_member covers the used anchors only, so tx_365d (distinct transactions in [t - 365, t), as in gld_fs_member) is
-- recomputed for the whole pool from cumulative transaction counts per member with two ASOF joins. Read-only.
-- Run: tools/report_tables.py --only t10b (table t10b_sample_representativeness).
CREATE OR REPLACE TEMP TABLE _txc AS
  SELECT member_id, d, SUM(n) OVER (PARTITION BY member_id ORDER BY d) AS cum
  FROM (SELECT member_id, CAST(transaction_date AS DATE) AS d, COUNT(DISTINCT transaction_id) AS n
        FROM silver.slv_fact_sales_line WHERE member_id IS NOT NULL GROUP BY 1, 2);
CREATE OR REPLACE TEMP TABLE _pool AS
  SELECT p.*, COALESCE(c1.cum, 0) - COALESCE(c2.cum, 0) AS tx_365d
  FROM (SELECT member_id, country_code, CAST(anchor_date AS DATE) AS anchor_date, split, is_used, week_idx, days_to_next_buy
        FROM gold.anchor_grid WHERE days_to_next_buy <= 90 AND (split <> 'train' OR in_train_sample)) p
  ASOF LEFT JOIN _txc c1 ON c1.member_id = p.member_id AND c1.d < p.anchor_date
  ASOF LEFT JOIN _txc c2 ON c2.member_id = p.member_id AND c2.d < p.anchor_date - 365;
WITH a AS (
  SELECT country_code, split, is_used, week_idx,
         CASE WHEN tx_365d <= 1 THEN 'new' WHEN tx_365d >= 3 THEN 'loyal' ELSE 'mid' END AS segment,
         CASE WHEN days_to_next_buy <= 30 THEN 'd30' ELSE 'd90' END AS horizon
  FROM _pool),
dist AS (
  SELECT country_code, split, is_used, dim, val, COUNT(*) AS n,
         COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY country_code, split, is_used, dim) AS share
  FROM (SELECT country_code, split, is_used, 'segment' AS dim, segment AS val FROM a UNION ALL
        SELECT country_code, split, is_used, 'horizon', horizon FROM a UNION ALL
        SELECT country_code, split, is_used, 'quarter', CAST(week_idx // 13 AS VARCHAR) FROM a)
  GROUP BY country_code, split, is_used, dim, val)
SELECT p.country_code, p.split, p.dim, p.val, p.n AS n_rest_of_pool, s.n AS n_sample,
       ROUND(p.share, 4) AS share_rest_of_pool, ROUND(s.share, 4) AS share_sample, ROUND(s.share - p.share, 4) AS diff
FROM dist p JOIN dist s USING (country_code, split, dim, val)
WHERE NOT p.is_used AND s.is_used
ORDER BY p.country_code, CASE p.split WHEN 'train' THEN 1 WHEN 'valid' THEN 2 ELSE 3 END, p.dim, TRY_CAST(p.val AS INT), p.val
