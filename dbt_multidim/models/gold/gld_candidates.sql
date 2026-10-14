-- Five candidate sources R1–R5, merged and capped at n_candidates with priority R1 > R3 > R2 > R4 > R5
WITH g AS (SELECT member_id, country_code, anchor_date FROM gold.anchor_grid),
fm AS (SELECT member_id, anchor_date, sport_ids, usual_store_id FROM {{ ref('gld_fs_member') }}),
r1 AS (SELECT DISTINCT g.member_id, g.anchor_date, f.model_code FROM g JOIN {{ ref('slv_fact_sales_line') }} f
       ON f.member_id = g.member_id AND f.transaction_date < g.anchor_date),
recent AS (SELECT DISTINCT g.member_id, g.anchor_date, g.country_code, f.model_code FROM g JOIN {{ ref('slv_fact_sales_line') }} f
           ON f.member_id = g.member_id AND f.transaction_date BETWEEN g.anchor_date - 90 AND g.anchor_date - 1),
r2 AS (SELECT DISTINCT rc.member_id, rc.anchor_date, cp.model_b AS model_code FROM recent rc
       JOIN {{ ref('gld_copurchase_lift') }} cp ON cp.country_code = rc.country_code AND cp.model_a = rc.model_code AND cp.rank_in_a <= 20),
r3 AS (SELECT DISTINCT g.member_id, g.anchor_date, w.model_code FROM g JOIN {{ ref('gld_web_stitched') }} w ON w.member_id = g.member_id
       AND w.event_date BETWEEN g.anchor_date - 30 AND g.anchor_date - 1 AND w.identity_verified_ts <= g.anchor_date AND w.model_code IS NOT NULL),
r4 AS (SELECT DISTINCT g.member_id, g.anchor_date, m.model_code FROM g JOIN fm USING (member_id, anchor_date)
       JOIN {{ ref('slv_dim_model') }} dm ON list_contains(fm.sport_ids, dm.sport_department_code)
       JOIN {{ ref('gld_fs_model_country') }} m ON m.model_code = dm.model_code AND m.country_code = g.country_code AND m.anchor_date = g.anchor_date
       WHERE (m.is_temp_promo OR m.seasonal_idx > 1.3) AND m.popularity_rank <= 500),
r5 AS (SELECT DISTINCT g.member_id, g.anchor_date, m.model_code FROM g JOIN fm USING (member_id, anchor_date)
       JOIN {{ ref('gld_fs_model_country') }} m ON m.country_code = g.country_code AND m.anchor_date = g.anchor_date AND m.popularity_rank <= 300
       JOIN {{ ref('slv_stock_daily_model') }} s ON s.model_code = m.model_code AND s.site_gln = fm.usual_store_id
         AND s.calendar_date = g.anchor_date AND s.is_available_ff = 1),
u AS (
  SELECT member_id, anchor_date, model_code, MAX(r1) r1, MAX(r2) r2, MAX(r3) r3, MAX(r4) r4, MAX(r5) r5 FROM (
    SELECT *, 1 r1, 0 r2, 0 r3, 0 r4, 0 r5 FROM r1 UNION ALL SELECT *, 0, 1, 0, 0, 0 FROM r2 UNION ALL SELECT *, 0, 0, 1, 0, 0 FROM r3
    UNION ALL SELECT *, 0, 0, 0, 1, 0 FROM r4 UNION ALL SELECT *, 0, 0, 0, 0, 1 FROM r5) GROUP BY 1, 2, 3)
SELECT g.country_code, u.*
FROM u JOIN g USING (member_id, anchor_date)
QUALIFY ROW_NUMBER() OVER (PARTITION BY u.member_id, u.anchor_date ORDER BY r1 DESC, r3 DESC, r2 DESC, r4 DESC, r5 DESC) <= {{ var('n_candidates') | int }}
