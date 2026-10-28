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

-- 4e. QC-5 volume drift (issue #25): rows per table × country × day against the trailing 28-day mean of the SAME WEEKDAY (the four
--     previous occurrences). Retail volume is strongly weekly — VN Saturdays and Sundays carry 1.8× a weekday — so a plain 28-day
--     mean flags every weekend; the same-weekday baseline keeps the real anomalies (holidays, gaps, export edges). The day grid comes
--     from dim_calendar so a day without rows counts as 0 instead of disappearing. A day is flagged when |drift| > 50 % and at least
--     two of the four baseline days have rows (no flags while a series starts or restarts). probable_cause is a hint for the review,
--     not a verdict: NO_ROWS (gap), EXPORT_EDGE (last, partial day), AFTER_GAP (baseline still holds empty days), PUBLIC_HOLIDAY /
--     DUPLICATED_EXPORT (raw rows > 1.2 × the distinct (transaction, line, version) keys: the export repeated the rows — 1 – 13 October 2023 in all
--     three countries showed +51 to +114 % for that reason alone; Silver deduplicates, the check keeps the evidence in distinct_lines / dup_factor),
--     ADJACENT_TO_HOLIDAY (ext.public_holidays, built by make holidays), DOUBLE_DAY_SALE (day = month: 6.6, 11.11 …, the e-commerce sale days),
--     BLACK_FRIDAY, HOLIDAY_IN_BASELINE (a holiday depressed one of the four baseline days), else UNEXPLAINED. mean_28d (all days) is kept for reference.
--     rows stays the raw Bronze count (the ingest volume the check watches); tracking events have no version column, so distinct_lines = rows there.
CREATE OR REPLACE TABLE audit.volume_drift AS
WITH daily AS (
  SELECT 'sales_detail' AS table_name, economical_businessunit_country_code AS country_code, CAST(gmv_recorded_at AS DATE) AS d,
         COUNT(*) AS n, COUNT(DISTINCT (transaction_id, transaction_num_line, transaction_version_at)) AS nd
  FROM bronze.sales_detail GROUP BY 1, 2, 3
  UNION ALL
  SELECT 'tracking_ecom_events', country_code, CAST(date AS DATE), COUNT(*), COUNT(*) FROM bronze.tracking_ecom_events GROUP BY 1, 2, 3),
span AS (SELECT table_name, country_code, MIN(d) AS d_min, MAX(d) AS d_max FROM daily GROUP BY 1, 2),
grid AS (SELECT s.table_name, s.country_code, s.d_min, s.d_max, c.d
         FROM span s JOIN (SELECT DISTINCT CAST(date_of_day AS DATE) AS d FROM bronze.dim_calendar) c ON c.d BETWEEN s.d_min AND s.d_max),
hol AS (SELECT country_code, holiday_date, FIRST(holiday_name ORDER BY holiday_name) AS holiday_name FROM ext.public_holidays GROUP BY 1, 2),
g AS (SELECT grid.*, COALESCE(x.n, 0) AS n, COALESCE(x.nd, 0) AS nd, dayofweek(grid.d) AS dow, h.holiday_name
      FROM grid LEFT JOIN daily x USING (table_name, country_code, d) LEFT JOIN hol h ON h.country_code = grid.country_code AND h.holiday_date = grid.d),
w AS (SELECT *,
             AVG(n) OVER wk AS mean_same_weekday_28d, COUNT(*) FILTER (WHERE n > 0) OVER wk AS baseline_days_with_rows, COUNT(*) OVER wk AS baseline_days,
             SUM(CASE WHEN holiday_name IS NOT NULL THEN 1 ELSE 0 END) OVER wk AS baseline_holiday_days,
             AVG(n) OVER all28 AS mean_28d
      FROM g WINDOW wk AS (PARTITION BY table_name, country_code, dow ORDER BY d ROWS BETWEEN 4 PRECEDING AND 1 PRECEDING),
                   all28 AS (PARTITION BY table_name, country_code ORDER BY d ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING)),
f AS (SELECT *, n / NULLIF(mean_same_weekday_28d, 0) - 1 AS drift,
             (baseline_days = 4 AND baseline_days_with_rows >= 2 AND ABS(n / NULLIF(mean_same_weekday_28d, 0) - 1) > 0.5) AS flagged FROM w)
SELECT f.table_name, f.country_code, f.d AS calendar_date, f.dow AS day_of_week, f.n AS rows, f.nd AS distinct_lines, ROUND(f.n / NULLIF(f.nd, 0), 2) AS dup_factor,
       ROUND(f.mean_same_weekday_28d, 1) AS mean_same_weekday_28d, ROUND(f.mean_28d, 1) AS mean_28d, ROUND(f.drift, 3) AS drift,
       f.baseline_days_with_rows, f.baseline_holiday_days, f.flagged,
       CASE WHEN NOT f.flagged THEN NULL
            WHEN f.n = 0 THEN 'NO_ROWS'
            WHEN f.d = f.d_max THEN 'EXPORT_EDGE'
            WHEN f.baseline_days_with_rows < 4 THEN 'AFTER_GAP'
            WHEN f.n > 1.2 * f.nd THEN 'DUPLICATED_EXPORT'
            WHEN f.holiday_name IS NOT NULL THEN 'PUBLIC_HOLIDAY: ' || f.holiday_name
            WHEN hp.holiday_name IS NOT NULL OR hn.holiday_name IS NOT NULL THEN 'ADJACENT_TO_HOLIDAY: ' || COALESCE(hp.holiday_name, hn.holiday_name)
            WHEN day(f.d) = month(f.d) THEN 'DOUBLE_DAY_SALE'
            WHEN month(f.d) = 11 AND f.dow = 5 AND day(f.d) BETWEEN 23 AND 29 THEN 'BLACK_FRIDAY'
            WHEN f.baseline_holiday_days > 0 THEN 'HOLIDAY_IN_BASELINE'
            ELSE 'UNEXPLAINED' END AS probable_cause
FROM f
LEFT JOIN hol hp ON hp.country_code = f.country_code AND hp.holiday_date = f.d - 1
LEFT JOIN hol hn ON hn.country_code = f.country_code AND hn.holiday_date = f.d + 1
ORDER BY 1, 2, 3;
