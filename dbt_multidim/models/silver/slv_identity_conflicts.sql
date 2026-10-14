-- Cookies mapping to > 1 member (excluded from stitching; reported in quarantine)
{{ config(schema='quarantine') }}
WITH e AS (SELECT DISTINCT user_id, member_id_direct FROM {{ ref('slv_web_events_clean') }} WHERE user_id IS NOT NULL AND member_id_direct IS NOT NULL)
SELECT user_id, COUNT(DISTINCT member_id_direct) AS n_members, LIST(DISTINCT member_id_direct) AS member_ids
FROM e GROUP BY 1 HAVING COUNT(DISTINCT member_id_direct) > 1
