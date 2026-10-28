-- WBS 3.6: no (member, anchor) may carry more than vars.n_candidates candidates, and every used anchor must have at least one
SELECT member_id, anchor_date, COUNT(*) AS n FROM {{ ref('gld_candidates') }} GROUP BY 1, 2 HAVING COUNT(*) > {{ var('n_candidates') | int }}
UNION ALL
SELECT a.member_id, a.anchor_date, 0 FROM gold.anchor_grid a WHERE a.is_used
  AND NOT EXISTS (SELECT 1 FROM {{ ref('gld_candidates') }} c WHERE c.member_id = a.member_id AND c.anchor_date = a.anchor_date)
