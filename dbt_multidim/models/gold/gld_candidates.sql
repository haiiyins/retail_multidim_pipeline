-- Candidate generation: up to vars.n_candidates models per used anchor, from five sources flagged r1 … r5 (DESIGN §6), merged and
-- deduplicated, ranked by source priority R1 > R3 > R2 > R4 > R5 and then by the source's own score. Every source reads data
-- strictly before the anchor and links known at the anchor (QC-6).
--   R1 repurchase      models the member bought before the anchor, most recent first
--   R2 co-purchase     top-20 lift partners (gld_copurchase_lift.rank_in_a) of the models bought in the last 90 days
--   R3 web intent      models viewed or carted in the last 30 days through gld_web_stitched (attribution known at the anchor)
--   R4 sport × offer   popular models (rank ≤ 500) on a temporary promotion or in season (seasonal_idx > 1.3) whose sport department
--                      is affine to one of the member's favourite sports (gld_sport_department_affinity)
--   R5 best-sellers    national top-300 by buyers in the last 28 days; with vars.use_stock also available at the member's usual store
--                      (stock is switched off, issue #21, so R5 is the national-popularity source that B0 keeps)
-- Purchasable at t: every candidate must be in gold.anchor_model_grid for (country, anchor), i.e. the model sells in the country
-- within ± 90 days of the anchor (the stock-based definition is off with vars.use_stock); on VN this removed 2.5 % of the pairs,
-- none of which ever carried a positive label.
{% set n_cand = var('n_candidates') | int %}
{% set use_stock = var('use_stock', false) %}
WITH g AS (SELECT member_id, country_code, anchor_date, split, in_train_sample FROM gold.anchor_grid WHERE is_used),
fm AS (SELECT member_id, anchor_date, sport_ids, usual_store_id FROM {{ ref('gld_fs_member') }}),
model_dept AS (SELECT model_code, ANY_VALUE(sport_department_code) AS sport_department_code FROM {{ ref('slv_dim_model') }} GROUP BY 1),
r1 AS (
  SELECT g.member_id, g.anchor_date, f.model_code, 1.0 / (1 + (g.anchor_date - MAX(f.transaction_date))) AS score
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f ON f.member_id = g.member_id AND f.transaction_date < g.anchor_date
  GROUP BY 1, 2, 3),
recent AS (
  SELECT DISTINCT g.member_id, g.anchor_date, g.country_code, f.model_code
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f ON f.member_id = g.member_id AND f.transaction_date BETWEEN g.anchor_date - 90 AND g.anchor_date - 1),
r2 AS (
  SELECT rc.member_id, rc.anchor_date, cp.model_b AS model_code, MAX(cp.lift) AS score
  FROM recent rc JOIN {{ ref('gld_copurchase_lift') }} cp
    ON cp.country_code = rc.country_code AND cp.model_a = rc.model_code AND cp.rank_in_a <= 20
  GROUP BY 1, 2, 3),
r3 AS (
  SELECT g.member_id, g.anchor_date, w.model_code, COUNT(*) AS score
  FROM g JOIN {{ ref('gld_web_stitched') }} w
    ON w.member_id = g.member_id AND w.event_date BETWEEN g.anchor_date - 30 AND g.anchor_date - 1
   AND w.identity_verified_ts <= CAST(g.anchor_date AS TIMESTAMP) AND w.model_code IS NOT NULL
  GROUP BY 1, 2, 3),
r4 AS (
  SELECT g.member_id, g.anchor_date, m.model_code, MAX(aff.lift) AS score
  FROM g JOIN fm USING (member_id, anchor_date)
  CROSS JOIN UNNEST(fm.sport_ids) AS s(sport_id)
  JOIN {{ ref('gld_sport_department_affinity') }} aff ON aff.country_code = g.country_code AND aff.sport_id = s.sport_id
  JOIN model_dept md ON md.sport_department_code = aff.sport_department_code
  JOIN {{ ref('gld_fs_model_country') }} m ON m.model_code = md.model_code AND m.country_code = g.country_code AND m.anchor_date = g.anchor_date
  WHERE (m.is_temp_promo OR m.seasonal_idx > 1.3) AND m.popularity_rank <= 500
  GROUP BY 1, 2, 3),
r5 AS (
  SELECT g.member_id, g.anchor_date, m.model_code, 1.0 / m.popularity_rank AS score
  FROM g JOIN {{ ref('gld_fs_model_country') }} m ON m.country_code = g.country_code AND m.anchor_date = g.anchor_date AND m.popularity_rank <= 300
  {% if use_stock %}
  JOIN fm USING (member_id, anchor_date)
  JOIN {{ ref('slv_stock_daily_model') }} s ON s.model_code = m.model_code AND s.site_gln = fm.usual_store_id
    AND s.calendar_date = g.anchor_date AND s.is_available_ff = 1
  {% endif %}
),
u AS (
  SELECT member_id, anchor_date, model_code,
         MAX(r1) AS r1, MAX(r2) AS r2, MAX(r3) AS r3, MAX(r4) AS r4, MAX(r5) AS r5,
         MAX(CASE WHEN r1 = 1 THEN score END) AS score_r1, MAX(CASE WHEN r2 = 1 THEN score END) AS score_r2,
         MAX(CASE WHEN r3 = 1 THEN score END) AS score_r3, MAX(CASE WHEN r4 = 1 THEN score END) AS score_r4,
         MAX(CASE WHEN r5 = 1 THEN score END) AS score_r5
  FROM (
    SELECT member_id, anchor_date, model_code, score, 1 AS r1, 0 AS r2, 0 AS r3, 0 AS r4, 0 AS r5 FROM r1
    UNION ALL SELECT member_id, anchor_date, model_code, score, 0, 1, 0, 0, 0 FROM r2
    UNION ALL SELECT member_id, anchor_date, model_code, score, 0, 0, 1, 0, 0 FROM r3
    UNION ALL SELECT member_id, anchor_date, model_code, score, 0, 0, 0, 1, 0 FROM r4
    UNION ALL SELECT member_id, anchor_date, model_code, score, 0, 0, 0, 0, 1 FROM r5)
  GROUP BY 1, 2, 3)
SELECT g.country_code, g.split, g.in_train_sample, u.member_id, u.anchor_date, u.model_code, u.r1, u.r2, u.r3, u.r4, u.r5,
       u.score_r1, u.score_r2, u.score_r3, u.score_r4, u.score_r5,
       CASE WHEN u.r1 = 1 THEN 1 WHEN u.r3 = 1 THEN 2 WHEN u.r2 = 1 THEN 3 WHEN u.r4 = 1 THEN 4 ELSE 5 END AS priority_source,
       ROW_NUMBER() OVER (PARTITION BY u.member_id, u.anchor_date
                          ORDER BY CASE WHEN u.r1 = 1 THEN 1 WHEN u.r3 = 1 THEN 2 WHEN u.r2 = 1 THEN 3 WHEN u.r4 = 1 THEN 4 ELSE 5 END,
                                   COALESCE(u.score_r1, u.score_r3, u.score_r2, u.score_r4, u.score_r5) DESC, u.model_code) AS candidate_rank
FROM u JOIN g USING (member_id, anchor_date)
JOIN gold.anchor_model_grid am ON am.country_code = g.country_code AND am.anchor_date = g.anchor_date AND am.model_code = u.model_code
QUALIFY candidate_rank <= {{ n_cand }}
