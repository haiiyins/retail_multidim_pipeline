-- Cookies mapping to > 1 member across both tiers (order-based and login-based); excluded from stitching, kept for the audit
{{ config(schema='quarantine') }}
SELECT user_id, COUNT(DISTINCT member_id) AS n_members, LIST(DISTINCT member_id) AS member_ids, LIST(DISTINCT src ORDER BY src) AS methods,
       MIN(verified_ts) AS first_seen, MAX(verified_ts) AS last_seen
FROM {{ ref('slv_user_member_links') }}
GROUP BY user_id HAVING COUNT(DISTINCT member_id) > 1
