-- Entity 2: model × country features at the anchor, one row per row of gold.anchor_model_grid (no row loss: every feature is
-- LEFT-joined from a CTE keyed on the grid). Groups (schema.yml meta.group, evaluation/ablation_configs.yml):
--   F1 price at the anchor   the SKU intervals valid on the anchor date (eff_start <= anchor <= eff_end), one per SKU with a temporary
--                            promotion preferred over STANDARD when both are valid, then the MEDIAN over the model's SKUs — intervals are
--                            never pre-aggregated per model because the SKUs of a model do not share their dates (DESIGN §3)
--   F3 promotion & calendar  promo kind / depth at the anchor, country promo share, commercial event, days to the next public holiday
--   F2 popularity & history  buyers and units in the 28 days before the anchor, popularity rank, model age (first sale before the anchor)
--   F3 seasonality           units in the same two weeks one year earlier over the weekly average of the year before the anchor
--   Stock                    only when vars.use_stock is true; the signal is switched off (decision 2026-10-28, issue #21) because the only
--                            exported table covers spare parts and availability stays above 90 %, so the columns are NULL
-- last_source_ts = latest transaction timestamp that fed the row (QC-6, tests/leakage_fs_model_country.sql).
{% set use_stock = var('use_stock', false) %}
WITH g AS (SELECT model_code, country_code, anchor_date FROM gold.anchor_model_grid),
sku_valid AS (   -- one valid interval per SKU at the anchor: temporary promotion first, then the lowest price
  SELECT g.model_code, g.country_code, g.anchor_date, dm.item_code, p.price_type, p.promo_kind, p.is_temp_promo, p.price, p.ref_price, p.eff_start
  FROM g
  JOIN {{ ref('slv_dim_model') }} dm USING (model_code)
  JOIN {{ ref('slv_price_sku_interval') }} p
    ON p.item_code = dm.item_code AND p.country_code = g.country_code AND p.price_scope = 'NATIONAL'
   AND g.anchor_date BETWEEN p.eff_start AND p.eff_end
  QUALIFY ROW_NUMBER() OVER (PARTITION BY g.model_code, g.country_code, g.anchor_date, dm.item_code
                             ORDER BY p.is_temp_promo DESC, p.price ASC, p.eff_start DESC) = 1),
n_sku AS (SELECT model_code, COUNT(*) AS n_sku FROM {{ ref('slv_dim_model') }} GROUP BY 1),
price AS (
  SELECT model_code, country_code, anchor_date,
         COUNT(*) AS n_sku_priced,
         MEDIAN(price) AS price_local, MEDIAN(ref_price) AS ref_price_local,
         MODE(promo_kind) AS promo_kind,
         AVG(CAST(is_temp_promo AS INT)) AS temp_promo_share,
         LEAST(0.9, GREATEST(0, 1 - MEDIAN(price) / NULLIF(MEDIAN(ref_price), 0))) AS promo_depth,
         MAX(eff_start) AS last_price_start
  FROM sku_valid GROUP BY 1, 2, 3),
pop AS (
  SELECT g.model_code, g.country_code, g.anchor_date,
         COUNT(DISTINCT f.member_id) AS buyers_28d, SUM(f.qty) AS qty_28d, MAX(f.transaction_ts_utc) AS last_tx_ts
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f
    ON f.model_code = g.model_code AND f.country_code = g.country_code
   AND f.transaction_date BETWEEN g.anchor_date - 28 AND g.anchor_date - 1
  GROUP BY 1, 2, 3),
season AS (
  SELECT g.model_code, g.country_code, g.anchor_date,
         SUM(CASE WHEN f.transaction_date BETWEEN g.anchor_date - 371 AND g.anchor_date - 358 THEN f.qty ELSE 0 END)
           / NULLIF(SUM(f.qty) / 52.0, 0) AS seasonal_idx
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f
    ON f.model_code = g.model_code AND f.country_code = g.country_code
   AND f.transaction_date BETWEEN g.anchor_date - 730 AND g.anchor_date - 366
  GROUP BY 1, 2, 3),
first_sale AS (SELECT model_code, country_code, MIN(transaction_date) AS first_d FROM {{ ref('slv_fact_sales_line') }} GROUP BY 1, 2),
{% if use_stock %}
stock AS (
  SELECT g.model_code, g.country_code, g.anchor_date, s.avail_store_ratio, s.stock_qty_national
  FROM g ASOF LEFT JOIN {{ ref('slv_stock_daily_national') }} s
    ON s.model_code = g.model_code AND s.country_code = g.country_code AND g.anchor_date >= s.calendar_date),
{% else %}
stock AS (SELECT model_code, country_code, anchor_date, CAST(NULL AS DOUBLE) AS avail_store_ratio, CAST(NULL AS BIGINT) AS stock_qty_national FROM g),
{% endif %}
ranked AS (
  SELECT g.model_code, g.country_code, g.anchor_date,
         COALESCE(pop.buyers_28d, 0) AS buyers_28d, COALESCE(pop.qty_28d, 0) AS qty_28d,
         RANK() OVER (PARTITION BY g.country_code, g.anchor_date ORDER BY COALESCE(pop.buyers_28d, 0) DESC, COALESCE(pop.qty_28d, 0) DESC) AS popularity_rank,
         pop.last_tx_ts
  FROM g LEFT JOIN pop USING (model_code, country_code, anchor_date))
SELECT g.model_code, g.country_code, g.anchor_date,
       -- F1 price at the anchor
       pr.price_local, pr.ref_price_local, COALESCE(pr.n_sku_priced, 0) AS n_sku_priced,
       COALESCE(pr.n_sku_priced, 0) * 1.0 / NULLIF(ns.n_sku, 0) AS sku_price_coverage,
       -- F3 promotion and calendar
       pr.promo_kind, (COALESCE(pr.temp_promo_share, 0) >= 0.5) AS is_temp_promo, pr.temp_promo_share, pr.promo_depth,
       cal.in_commercial_event, cal.days_to_next_holiday, cal.promo_share AS country_promo_share,
       -- F2 popularity and history
       r.buyers_28d, r.qty_28d, r.popularity_rank,
       CASE WHEN fs.first_d < g.anchor_date THEN g.anchor_date - fs.first_d END AS model_age_days,
       -- F3 seasonality
       season.seasonal_idx,
       -- Stock (NULL unless vars.use_stock)
       st.avail_store_ratio, st.stock_qty_national,
       -- QC-6 bookkeeping
       GREATEST(r.last_tx_ts, CAST(pr.last_price_start AS TIMESTAMP)) AS last_source_ts
FROM g
LEFT JOIN price pr USING (model_code, country_code, anchor_date)
LEFT JOIN n_sku ns USING (model_code)
LEFT JOIN ranked r USING (model_code, country_code, anchor_date)
LEFT JOIN season USING (model_code, country_code, anchor_date)
LEFT JOIN stock st USING (model_code, country_code, anchor_date)
LEFT JOIN first_sale fs USING (model_code, country_code)
LEFT JOIN {{ ref('slv_calendar_enriched') }} cal ON cal.country_code = g.country_code AND cal.calendar_date = g.anchor_date
