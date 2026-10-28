-- Entity 3: pair features (member, model, anchor_date) for the candidates only. Joins the two entities (gld_fs_member,
-- gld_fs_model_country) and adds member × model interactions computed strictly before the anchor: purchase history of the model,
-- co-purchase lift with the last-90-day basket, department purchase cycle, web attention to the model (attribution known at the
-- anchor). last_source_ts = greatest source timestamp of the row (QC-6, tests/leakage_fs_pair.sql). Stock at the usual store is NULL
-- unless vars.use_stock (issue #21).
{% set use_stock = var('use_stock', false) %}
WITH c AS (SELECT * FROM {{ ref('gld_candidates') }}),
fm AS (SELECT * EXCLUDE (country_code, split, in_train_sample) FROM {{ ref('gld_fs_member') }}),   -- keys and bookkeeping come from the candidates
hist AS (   -- the member's own history with the candidate model
  SELECT c.member_id, c.anchor_date, c.model_code, COUNT(DISTINCT f.transaction_id) AS hist_buy_cnt,
         c.anchor_date - MAX(f.transaction_date) AS days_since_bought, SUM(f.qty) AS hist_qty
  FROM c JOIN {{ ref('slv_fact_sales_line') }} f ON f.member_id = c.member_id AND f.model_code = c.model_code AND f.transaction_date < c.anchor_date
  GROUP BY 1, 2, 3),
recent AS (
  SELECT DISTINCT c.member_id, c.anchor_date, c.country_code, f.model_code
  FROM (SELECT DISTINCT member_id, anchor_date, country_code FROM c) c
  JOIN {{ ref('slv_fact_sales_line') }} f ON f.member_id = c.member_id AND f.transaction_date BETWEEN c.anchor_date - 90 AND c.anchor_date - 1),
lift AS (   -- co-purchase lift between a model and what the member bought in the last 90 days, aggregated per (anchor, partner)
            -- before joining the candidates (keeps the 23 M-row candidate table out of the expansion)
  SELECT r.member_id, r.anchor_date, cp.model_b AS model_code,
         MAX(cp.lift) AS copurchase_lift_max, AVG(cp.lift) AS copurchase_lift_mean, COUNT(*) AS copurchase_links
  FROM recent r JOIN {{ ref('gld_copurchase_lift') }} cp ON cp.country_code = r.country_code AND cp.model_a = r.model_code
  GROUP BY 1, 2, 3),
model_dept AS (SELECT model_code, ANY_VALUE(sport_department_code) AS sport_department_code FROM {{ ref('slv_dim_model') }} GROUP BY 1),
dept_buys AS (   -- the member's purchase days per sport department, with the gap to the previous one
  SELECT f.member_id, md.sport_department_code, f.transaction_date,
         f.transaction_date - LAG(f.transaction_date) OVER (PARTITION BY f.member_id, md.sport_department_code ORDER BY f.transaction_date) AS gap_days
  FROM (SELECT DISTINCT member_id, model_code, transaction_date FROM {{ ref('slv_fact_sales_line') }}
        WHERE member_id IN (SELECT DISTINCT member_id FROM c)) f
  JOIN model_dept md USING (model_code) WHERE md.sport_department_code IS NOT NULL),
dept_state AS (   -- running state of the member in a department as of each purchase day: count so far, median gap so far
  SELECT member_id, sport_department_code, transaction_date AS as_of_date,
         COUNT(*) OVER w AS dept_buy_cnt,
         QUANTILE_CONT(gap_days, 0.5) OVER w AS dept_cycle_days
  FROM dept_buys
  WINDOW w AS (PARTITION BY member_id, sport_department_code ORDER BY transaction_date ROWS UNBOUNDED PRECEDING)),
dept AS (   -- the latest state strictly before the anchor (ASOF), one lookup per candidate instead of a history expansion
  SELECT c.member_id, c.anchor_date, c.model_code, c.anchor_date - ds.as_of_date AS days_since_dept_buy, ds.dept_buy_cnt, ds.dept_cycle_days
  FROM c JOIN model_dept md ON md.model_code = c.model_code
  ASOF JOIN dept_state ds ON ds.member_id = c.member_id AND ds.sport_department_code = md.sport_department_code AND ds.as_of_date < c.anchor_date),
web AS (   -- attention to the candidate model in the 30 days before the anchor, attribution known at the anchor
  SELECT c.member_id, c.anchor_date, c.model_code,
         COUNT(DISTINCT CASE WHEN w.event_name IN ('product_page_viewed', 'product_size_selected') AND w.event_date >= c.anchor_date - 7 THEN w.event_id END) AS web_view_7d,
         COUNT(DISTINCT CASE WHEN w.event_name IN ('product_page_viewed', 'product_size_selected') THEN w.event_id END) AS web_view_30d,
         COUNT(DISTINCT CASE WHEN w.event_name = 'product_list_viewed' THEN w.event_id END) AS web_list_30d,
         COUNT(DISTINCT CASE WHEN w.event_name IN ('product_added_to_cart', 'cart_viewed', 'checkout_commenced') THEN w.event_id END) AS web_cart_30d,
         MAX(w.event_ts_utc) AS last_web_ts
  FROM c JOIN {{ ref('gld_web_stitched') }} w
    ON w.member_id = c.member_id AND w.model_code = c.model_code
   AND w.event_date BETWEEN c.anchor_date - 30 AND c.anchor_date - 1 AND w.identity_verified_ts <= CAST(c.anchor_date AS TIMESTAMP)
  GROUP BY 1, 2, 3)
SELECT c.*,
       -- member entity
       fm.tx_30d, fm.tx_90d, fm.tx_365d, fm.items_365d, fm.models_365d, fm.days_since_last_tx, fm.gmv_eur_365d, fm.return_rate, fm.account_tenure_days,
       fm.price_q25, fm.price_q50, fm.price_q75, fm.price_q50_eur, fm.promo_affinity,
       fm.n_sports, fm.sport_ids, fm.usual_store_id, fm.usual_store_share, fm.stores_visited_cum,
       fm.web_sessions_7d, fm.web_sessions_30d, fm.web_events_30d, fm.web_models_30d, fm.has_web_signal, fm.web_days_available_30d, fm.web_data_available,
       -- model × country entity
       mc.price_local, mc.ref_price_local, mc.n_sku_priced, mc.sku_price_coverage, mc.promo_kind, mc.is_temp_promo, mc.temp_promo_share, mc.promo_depth,
       mc.in_commercial_event, mc.days_to_next_holiday, mc.country_promo_share, mc.buyers_28d, mc.qty_28d, mc.popularity_rank, mc.model_age_days,
       mc.seasonal_idx, mc.avail_store_ratio, mc.stock_qty_national,
       -- interactions
       (mc.price_local - fm.price_q50) / NULLIF(fm.price_q50, 0) AS price_gap_q50,
       (mc.price_local BETWEEN fm.price_q25 AND fm.price_q75) AS in_budget_iqr,
       fm.promo_affinity * mc.promo_depth AS promo_sensitivity,
       COALESCE(h.hist_buy_cnt, 0) AS hist_buy_cnt, h.days_since_bought, COALESCE(h.hist_qty, 0) AS hist_qty,
       l.copurchase_lift_max, l.copurchase_lift_mean, COALESCE(l.copurchase_links, 0) AS copurchase_links,
       d.days_since_dept_buy, COALESCE(d.dept_buy_cnt, 0) AS dept_buy_cnt, d.dept_cycle_days,
       d.days_since_dept_buy * 1.0 / NULLIF(d.dept_cycle_days, 0) AS dept_overdue_ratio,
       COALESCE(w.web_view_7d, 0) AS web_view_7d, COALESCE(w.web_view_30d, 0) AS web_view_30d, COALESCE(w.web_list_30d, 0) AS web_list_30d, COALESCE(w.web_cart_30d, 0) AS web_cart_30d,
       list_contains(fm.sport_ids, CAST(aff.sport_id AS BIGINT)) IS TRUE AS sport_match,
       {% if use_stock %}
       COALESCE(s.is_available_ff, 0) AS in_stock_usual_store,
       {% else %}
       CAST(NULL AS INTEGER) AS in_stock_usual_store,
       {% endif %}
       GREATEST(fm.last_source_ts, mc.last_source_ts, w.last_web_ts) AS last_source_ts
FROM c
JOIN fm USING (member_id, anchor_date)
LEFT JOIN {{ ref('gld_fs_model_country') }} mc USING (model_code, country_code, anchor_date)   -- LEFT: a repurchase candidate may lie outside anchor_model_grid (no sale within ± 90 days); its model features stay NULL
LEFT JOIN hist h USING (member_id, anchor_date, model_code)
LEFT JOIN lift l USING (member_id, anchor_date, model_code)
LEFT JOIN dept d USING (member_id, anchor_date, model_code)
LEFT JOIN web w USING (member_id, anchor_date, model_code)
LEFT JOIN model_dept md ON md.model_code = c.model_code
LEFT JOIN (SELECT country_code, sport_department_code, MIN(sport_id) AS sport_id FROM {{ ref('gld_sport_department_affinity') }} GROUP BY 1, 2) aff
       ON aff.country_code = c.country_code AND aff.sport_department_code = md.sport_department_code
{% if use_stock %}
LEFT JOIN {{ ref('slv_stock_daily_model') }} s ON s.model_code = c.model_code AND s.site_gln = fm.usual_store_id AND s.calendar_date = c.anchor_date
{% endif %}
