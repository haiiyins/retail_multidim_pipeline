-- WBS 3.6 DoD: candidate recall per source against the labels — share of (member, anchor, model) purchases in the Δ = 30 / 90 window
-- after a used anchor (non-returned, model in the catalogue) that the candidate set contains, overall and per source r1 … r5.
WITH g AS (SELECT member_id, country_code, anchor_date, split FROM gold.anchor_grid WHERE is_used),
buy AS (
  SELECT DISTINCT g.member_id, g.country_code, g.anchor_date, g.split, f.model_code,
         (f.transaction_date <= g.anchor_date + 30) AS in_30, TRUE AS in_90
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f
    ON f.member_id = g.member_id AND f.transaction_date > g.anchor_date AND f.transaction_date <= g.anchor_date + 90
  WHERE NOT EXISTS (SELECT 1 FROM {{ ref('slv_fact_returns') }} r WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code)),
j AS (
  SELECT b.country_code, b.split, b.in_30, c.r1, c.r2, c.r3, c.r4, c.r5, (c.model_code IS NOT NULL) AS covered
  FROM buy b LEFT JOIN {{ ref('gld_candidates') }} c USING (member_id, anchor_date, model_code))
SELECT country_code, split, delta, COUNT(*) AS positives,
       ROUND(AVG(covered::INT), 4) AS recall_any,
       ROUND(AVG(COALESCE(r1, 0)), 4) AS recall_r1, ROUND(AVG(COALESCE(r2, 0)), 4) AS recall_r2, ROUND(AVG(COALESCE(r3, 0)), 4) AS recall_r3,
       ROUND(AVG(COALESCE(r4, 0)), 4) AS recall_r4, ROUND(AVG(COALESCE(r5, 0)), 4) AS recall_r5,
       current_timestamp AS computed_at
FROM (SELECT *, 90 AS delta FROM j UNION ALL SELECT *, 30 AS delta FROM j WHERE in_30)
GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
