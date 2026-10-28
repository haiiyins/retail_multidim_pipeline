-- QC-6 ledger (WBS 3.8, issue #36): every Gold row whose source data postdates its anchor, with the model name — the same
-- predicates as the singular tests tests/leakage_*.sql, materialised so a violation leaves a trace instead of only failing a run.
-- Expected to be empty; tests/leakage_violations_empty.sql fails otherwise.
SELECT 'gld_fs_member' AS model_name, member_id, CAST(NULL AS VARCHAR) AS model_code, anchor_date, last_source_ts AS offending_ts, 'last_source_ts > anchor' AS rule
FROM {{ ref('gld_fs_member') }} WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)
UNION ALL
SELECT 'gld_fs_model_country', NULL, model_code, anchor_date, last_source_ts, 'last_source_ts > anchor'
FROM {{ ref('gld_fs_model_country') }} WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)
UNION ALL
SELECT 'gld_fs_pair', member_id, model_code, anchor_date, last_source_ts, 'last_source_ts > anchor'
FROM {{ ref('gld_fs_pair') }} WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)
UNION ALL
SELECT 'gld_fs_pair', p.member_id, p.model_code, p.anchor_date, NULL, 'web attention without an attribution known at the anchor'
FROM {{ ref('gld_fs_pair') }} p
WHERE (p.web_view_30d > 0 OR p.web_list_30d > 0 OR p.web_cart_30d > 0)
  AND NOT EXISTS (SELECT 1 FROM {{ ref('gld_web_stitched') }} w
                  WHERE w.member_id = p.member_id AND w.model_code = p.model_code
                    AND w.event_date BETWEEN p.anchor_date - 30 AND p.anchor_date - 1
                    AND w.identity_verified_ts <= CAST(p.anchor_date AS TIMESTAMP))
UNION ALL
SELECT 'gld_candidates', c.member_id, c.model_code, c.anchor_date, MIN(f.transaction_ts_utc), 'repurchase candidate (r1) without a purchase before the anchor'
FROM {{ ref('gld_candidates') }} c LEFT JOIN {{ ref('slv_fact_sales_line') }} f
  ON f.member_id = c.member_id AND f.model_code = c.model_code AND f.transaction_date < c.anchor_date
WHERE c.r1 = 1 GROUP BY 1, 2, 3, 4 HAVING COUNT(f.transaction_id) = 0
UNION ALL
SELECT 'gld_ranking_dataset', member_id, model_code, anchor_date, NULL, 'label_30 without label_90'
FROM {{ ref('gld_ranking_dataset') }} WHERE label_30 = 1 AND label_90 = 0
