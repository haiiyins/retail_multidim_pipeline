-- Bridge between the loyalty programme's favourite-sport ids (f_member_favorite_sport.sport_id, 2–667) and the catalogue's sport
-- departments (dim_item.sport_department_code, 13–99994): the two code spaces are unrelated and no dictionary was exported, so the
-- mapping is learnt from purchases before vars.copurchase_cutoff (= valid_lo of split.yml, so no validation or test label contributes):
-- for members whose favourite-sport interval covers the purchase date, lift = P(department | sport) / P(department). Keeps the
-- departments with at least 20 lines and lift > 1.5, top 5 per sport and country. Used by candidate source R4 (gld_candidates).
{% set cutoff = var('copurchase_cutoff') %}
WITH model_dept AS (SELECT model_code, ANY_VALUE(sport_department_code) AS sport_department_code FROM {{ ref('slv_dim_model') }} GROUP BY 1),
buys AS (
  SELECT f.member_id, f.country_code, f.transaction_date, md.sport_department_code
  FROM {{ ref('slv_fact_sales_line') }} f JOIN model_dept md USING (model_code)
  WHERE f.transaction_date < DATE '{{ cutoff }}' AND md.sport_department_code IS NOT NULL AND f.member_id IS NOT NULL),
with_sport AS (
  SELECT b.country_code, s.sport_id, b.sport_department_code, COUNT(*) AS n_lines
  FROM buys b JOIN {{ ref('slv_member_sport_asof') }} s
    ON s.member_id = b.member_id AND s.is_active
   AND s.valid_from <= CAST(b.transaction_date AS TIMESTAMP) AND (s.valid_to IS NULL OR s.valid_to > CAST(b.transaction_date AS TIMESTAMP))
  GROUP BY 1, 2, 3),
tot_sport AS (SELECT country_code, sport_id, SUM(n_lines) AS n_sport FROM with_sport GROUP BY 1, 2),
tot_dept AS (SELECT country_code, sport_department_code, COUNT(*) AS n_dept FROM buys GROUP BY 1, 2),
tot AS (SELECT country_code, COUNT(*) AS n_all FROM buys GROUP BY 1)
SELECT w.country_code, w.sport_id, w.sport_department_code, w.n_lines,
       w.n_lines * 1.0 / ts.n_sport AS share_in_sport,
       (w.n_lines * 1.0 / ts.n_sport) / (td.n_dept * 1.0 / t.n_all) AS lift,
       ROW_NUMBER() OVER (PARTITION BY w.country_code, w.sport_id ORDER BY (w.n_lines * 1.0 / ts.n_sport) / (td.n_dept * 1.0 / t.n_all) DESC) AS rank_in_sport,
       DATE '{{ cutoff }}' AS cutoff_date
FROM with_sport w
JOIN tot_sport ts USING (country_code, sport_id)
JOIN tot_dept td USING (country_code, sport_department_code)
JOIN tot t USING (country_code)
WHERE w.n_lines >= 20 AND (w.n_lines * 1.0 / ts.n_sport) / (td.n_dept * 1.0 / t.n_all) > 1.5
QUALIFY rank_in_sport <= 5
