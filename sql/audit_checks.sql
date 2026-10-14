-- 4a. stock table coverage of sold items (team confirmed ≈ 100% — rerun to keep the evidence)
CREATE OR REPLACE TABLE audit.stock_coverage AS
WITH sold AS (SELECT DISTINCT economical_businessunit_country_code c, item_code FROM bronze.sales_detail WHERE year >= 2025),
     stk  AS (SELECT DISTINCT country_code c, item_code FROM bronze.stock_availability_rate)
SELECT sold.c, COUNT(*) sold_items, COUNT(stk.item_code) in_stock_tbl, ROUND(COUNT(stk.item_code)*1.0/COUNT(*),3) coverage
FROM sold LEFT JOIN stk USING (c, item_code) GROUP BY 1;

-- 4b. in-country price uniformity: store vs website, same item, same start date, same price_type
CREATE OR REPLACE TABLE audit.price_uniformity AS
SELECT country_code, COUNT(*) n_pairs,
       ROUND(AVG(ABS(store_price/web_price - 1)),4) AS mean_rel_gap,
       ROUND(QUANTILE_CONT(ABS(store_price/web_price - 1), 0.95),4) AS p95_rel_gap
FROM (SELECT w.country_code, w.item_code, w.price_start_date, w.value_with_taxes web_price, s.value_with_taxes store_price
      FROM bronze.all_store_selling_price w JOIN bronze.all_store_selling_price s
        ON w.item_code=s.item_code AND w.country_code=s.country_code AND w.price_start_date=s.price_start_date
       AND w.business_unit_third_type=50 AND s.business_unit_third_type<>50 AND w.price_type=s.price_type
      WHERE w.value_with_taxes > 0)
GROUP BY 1;

-- 4c. inter-purchase gap distribution (validates Δ = 30 / 90)
CREATE OR REPLACE TABLE audit.interpurchase_days AS
SELECT country, QUANTILE_CONT(gap, [0.25,0.5,0.75,0.9]) AS q25_50_75_90, COUNT(*) n_gaps FROM (
  SELECT country, member_id, date_diff('day', LAG(d) OVER (PARTITION BY member_id ORDER BY d), d) gap
  FROM (SELECT DISTINCT s.economical_businessunit_country_code country, mb.member_id, CAST(s.gmv_recorded_at AS DATE) d
        FROM bronze.sales_detail s JOIN bronze.f_member_purchase mb USING (transaction_id)))
WHERE gap IS NOT NULL GROUP BY 1;

-- 4d. data date span (to fill split.yml)
CREATE OR REPLACE TABLE audit.date_span AS
SELECT economical_businessunit_country_code country, MIN(gmv_recorded_at) min_ts, MAX(gmv_recorded_at) max_ts FROM bronze.sales_detail GROUP BY 1;
