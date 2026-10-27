-- Step 4 — four go/no-go gates per country × year (deduplicate versions before counting; country from economical_businessunit_country_code)
-- Gate 2 (item match) is measured on item_type = 'stock' lines only: service lines (fees, workshop, delivery) have no row in dim_item by design.
CREATE OR REPLACE TABLE audit.gates_by_country AS
WITH v AS (
  SELECT * FROM bronze.sales_detail WHERE transaction_status = 'finished'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id, transaction_num_line ORDER BY transaction_version_at DESC) = 1),
s  AS (SELECT economical_businessunit_country_code AS country, year, transaction_id, item_code, item_type FROM v WHERE item_operation_type = 'sale'),
mb AS (SELECT DISTINCT transaction_id, member_id FROM bronze.f_member_purchase WHERE member_id IS NOT NULL),
it AS (SELECT DISTINCT item_code, model_code FROM bronze.dim_item WHERE model_code IS NOT NULL),
pr AS (SELECT DISTINCT p.country_code AS country, i.model_code FROM bronze.all_store_selling_price p JOIN it i USING (item_code)),
j  AS (SELECT s.*, mb.member_id, it.model_code, (pr.model_code IS NOT NULL) AS has_price
       FROM s LEFT JOIN mb USING (transaction_id) LEFT JOIN it USING (item_code)
              LEFT JOIN pr ON pr.country = s.country AND pr.model_code = it.model_code),
rep AS (SELECT country, year, COUNT(*) AS members_ge2 FROM (
          SELECT country, year, member_id, COUNT(DISTINCT transaction_id) n FROM j WHERE member_id IS NOT NULL
          GROUP BY 1,2,3 HAVING n >= 2) GROUP BY 1,2),
g AS (
  SELECT j.country, j.year,
         COUNT(DISTINCT j.transaction_id) AS n_tx,
         ROUND(100.0*COUNT(DISTINCT CASE WHEN j.member_id IS NOT NULL THEN j.transaction_id END)/COUNT(DISTINCT j.transaction_id),2) AS gate1_member_link_pct,
         ROUND(100.0*COUNT(CASE WHEN j.item_type = 'stock' AND j.model_code IS NOT NULL THEN 1 END)/COUNT(CASE WHEN j.item_type = 'stock' THEN 1 END),2) AS gate2_item_match_pct,
         ROUND(100.0*COUNT(DISTINCT CASE WHEN j.has_price THEN j.model_code END)/COUNT(DISTINCT j.model_code),2) AS gate3_price_cov_pct,
         COALESCE(MAX(rep.members_ge2),0) AS gate4_members_ge2
  FROM j LEFT JOIN rep USING (country, year)
  GROUP BY 1,2)
SELECT *,
       CASE WHEN gate1_member_link_pct>=60 AND gate2_item_match_pct>=95 AND gate3_price_cov_pct>=90 AND gate4_members_ge2>=20000
            THEN 'PASS' ELSE 'REVIEW' END AS gate_decision
FROM g ORDER BY 1,2;
