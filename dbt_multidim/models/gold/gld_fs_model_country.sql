-- Entity 2: model × country features at the anchor; price via ASOF on SKU intervals, then MEDIAN per model
WITH g AS (SELECT * FROM gold.anchor_model_grid),
sku_at_t AS (
  SELECT g.model_code, g.country_code, g.anchor_date, p.item_code, p.promo_kind,
         CASE WHEN p.eff_end >= g.anchor_date THEN p.price     END AS price_valid,
         CASE WHEN p.eff_end >= g.anchor_date THEN p.ref_price END AS ref_valid
  FROM g JOIN {{ ref('slv_dim_model') }} dm USING (model_code)
  ASOF LEFT JOIN {{ ref('slv_price_sku_interval') }} p
       ON p.item_code = dm.item_code AND p.country_code = g.country_code AND g.anchor_date >= p.eff_start),
price AS (SELECT model_code, country_code, anchor_date,
                 MEDIAN(price_valid) AS price_local, MEDIAN(ref_valid) AS ref_price_local, MODE(promo_kind) AS promo_kind,
                 LEAST(0.9, GREATEST(0, (MEDIAN(ref_valid) - MEDIAN(price_valid)) / NULLIF(MEDIAN(ref_valid), 0))) AS promo_depth
          FROM sku_at_t GROUP BY 1, 2, 3),
pop AS (SELECT g.model_code, g.country_code, g.anchor_date, COUNT(DISTINCT f.member_id) AS buyers_28d
        FROM g JOIN {{ ref('slv_fact_sales_line') }} f ON f.model_code = g.model_code AND f.country_code = g.country_code
          AND f.transaction_date BETWEEN g.anchor_date - 28 AND g.anchor_date - 1 GROUP BY 1, 2, 3),
season AS (SELECT g.model_code, g.country_code, g.anchor_date,
                  SUM(CASE WHEN f.transaction_date BETWEEN g.anchor_date - 371 AND g.anchor_date - 358 THEN f.qty END) / NULLIF(SUM(f.qty) / 52.0, 0) AS seasonal_idx
           FROM g JOIN {{ ref('slv_fact_sales_line') }} f ON f.model_code = g.model_code AND f.country_code = g.country_code
             AND f.transaction_date BETWEEN g.anchor_date - 730 AND g.anchor_date - 366 GROUP BY 1, 2, 3),
stock AS (SELECT g.model_code, g.country_code, g.anchor_date, s.avail_store_ratio, s.stock_qty_national
          FROM g ASOF LEFT JOIN {{ ref('slv_stock_daily_national') }} s
            ON s.model_code = g.model_code AND s.country_code = g.country_code AND g.anchor_date >= s.calendar_date),
first_sale AS (SELECT model_code, country_code, MIN(transaction_date) AS first_d FROM {{ ref('slv_fact_sales_line') }} GROUP BY 1, 2)
SELECT g.model_code, g.country_code, g.anchor_date,
       pr.price_local, pr.ref_price_local, pr.promo_kind, (pr.promo_kind IN ('DAILY', 'SEASONAL')) AS is_temp_promo, pr.promo_depth,
       COALESCE(pop.buyers_28d, 0) AS buyers_28d,
       RANK() OVER (PARTITION BY g.country_code, g.anchor_date ORDER BY COALESCE(pop.buyers_28d, 0) DESC) AS popularity_rank,
       season.seasonal_idx, cal.days_to_next_holiday, cal.in_commercial_event,
       st.avail_store_ratio, st.stock_qty_national,
       g.anchor_date - fs.first_d AS model_age_days
FROM g
LEFT JOIN price pr USING (model_code, country_code, anchor_date)
LEFT JOIN pop USING (model_code, country_code, anchor_date)
LEFT JOIN season USING (model_code, country_code, anchor_date)
LEFT JOIN stock st USING (model_code, country_code, anchor_date)
LEFT JOIN first_sale fs USING (model_code, country_code)
LEFT JOIN {{ ref('slv_calendar_enriched') }} cal ON cal.country_code = g.country_code AND cal.calendar_date = g.anchor_date
