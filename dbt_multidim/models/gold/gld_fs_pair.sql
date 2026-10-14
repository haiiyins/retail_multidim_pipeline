-- Entity 3: pair features (member, model, anchor_date) for candidates only
WITH c AS (SELECT * FROM {{ ref('gld_candidates') }}),
hist AS (SELECT c.member_id, c.anchor_date, c.model_code, COUNT(*) hist_buy_cnt, c.anchor_date - MAX(f.transaction_date) days_since_bought
         FROM c JOIN {{ ref('slv_fact_sales_line') }} f ON f.member_id = c.member_id AND f.model_code = c.model_code AND f.transaction_date < c.anchor_date GROUP BY 1, 2, 3),
recent AS (SELECT DISTINCT c.member_id, c.anchor_date, f.model_code FROM c JOIN {{ ref('slv_fact_sales_line') }} f
           ON f.member_id = c.member_id AND f.transaction_date BETWEEN c.anchor_date - 90 AND c.anchor_date - 1),
lift AS (SELECT c.member_id, c.anchor_date, c.model_code, MAX(cp.lift) lift_max, AVG(cp.lift) lift_mean
         FROM c JOIN recent r USING (member_id, anchor_date) JOIN {{ ref('gld_copurchase_lift') }} cp
           ON cp.country_code = c.country_code AND cp.model_a = r.model_code AND cp.model_b = c.model_code GROUP BY 1, 2, 3),
dept AS (SELECT c.member_id, c.anchor_date, c.model_code,
                c.anchor_date - MAX(f.transaction_date) AS days_since_dept_buy,
                MEDIAN(f.transaction_date - LAG(f.transaction_date) OVER (PARTITION BY f.member_id, f.sport_department_code ORDER BY f.transaction_date)) AS dept_cycle
         FROM c JOIN {{ ref('slv_dim_model') }} dm ON dm.model_code = c.model_code
         JOIN {{ ref('slv_fact_sales_line') }} f ON f.member_id = c.member_id AND f.sport_department_code = dm.sport_department_code AND f.transaction_date < c.anchor_date
         GROUP BY 1, 2, 3),
web AS (SELECT c.member_id, c.anchor_date, c.model_code,
               COUNT(CASE WHEN w.event_date >= c.anchor_date - 7 AND w.event_name LIKE '%view%' THEN 1 END) web_view_7d,
               COUNT(CASE WHEN w.event_name LIKE '%view%' THEN 1 END) web_view_30d,
               COUNT(CASE WHEN w.event_name LIKE '%cart%' THEN 1 END) web_cart_30d,
               MAX(w.event_date) last_web_date
        FROM c JOIN {{ ref('gld_web_stitched') }} w ON w.member_id = c.member_id AND w.model_code = c.model_code
          AND w.event_date BETWEEN c.anchor_date - 30 AND c.anchor_date - 1 AND w.identity_verified_ts <= c.anchor_date GROUP BY 1, 2, 3)
SELECT c.*, fm.price_q25, fm.price_q50, fm.price_q75, fm.promo_affinity, fm.tx_90d, fm.tx_365d, fm.days_since_last_tx, fm.has_web_signal,
       fm.web_sessions_30d, fm.n_sports, fm.account_tenure_days, fm.return_rate,
       mc.price_local, mc.ref_price_local, mc.promo_kind, mc.is_temp_promo, mc.promo_depth, mc.buyers_28d, mc.popularity_rank,
       mc.seasonal_idx, mc.days_to_next_holiday, mc.in_commercial_event, mc.avail_store_ratio, mc.stock_qty_national, mc.model_age_days,
       (mc.price_local - fm.price_q50) / NULLIF(fm.price_q50, 0) AS price_gap_q50,
       (mc.price_local BETWEEN fm.price_q25 AND fm.price_q75) AS in_budget_iqr,
       COALESCE(h.hist_buy_cnt, 0) AS hist_buy_cnt, h.days_since_bought,
       l.lift_max AS copurchase_lift_max, l.lift_mean AS copurchase_lift_mean,
       fm.promo_affinity * mc.promo_depth AS promo_sensitivity,
       d.days_since_dept_buy * 1.0 / NULLIF(d.dept_cycle, 0) AS dept_overdue_ratio,
       COALESCE(w.web_view_7d, 0) web_view_7d, COALESCE(w.web_view_30d, 0) web_view_30d, COALESCE(w.web_cart_30d, 0) web_cart_30d,
       list_contains(fm.sport_ids, dm.sport_department_code) AS sport_match,
       COALESCE(s.is_available_ff, 0) AS in_stock_usual_store,
       GREATEST(fm.last_source_ts, CAST(w.last_web_date AS TIMESTAMP)) AS last_source_ts
FROM c
JOIN {{ ref('gld_fs_member') }} fm USING (member_id, anchor_date)
JOIN {{ ref('gld_fs_model_country') }} mc USING (model_code, country_code, anchor_date)
JOIN {{ ref('slv_dim_model') }} dm ON dm.model_code = c.model_code
LEFT JOIN hist h USING (member_id, anchor_date, model_code)
LEFT JOIN lift l USING (member_id, anchor_date, model_code)
LEFT JOIN dept d USING (member_id, anchor_date, model_code)
LEFT JOIN web w USING (member_id, anchor_date, model_code)
LEFT JOIN {{ ref('slv_stock_daily_model') }} s ON s.model_code = c.model_code AND s.site_gln = fm.usual_store_id AND s.calendar_date = c.anchor_date
QUALIFY ROW_NUMBER() OVER (PARTITION BY c.member_id, c.anchor_date, c.model_code) = 1
