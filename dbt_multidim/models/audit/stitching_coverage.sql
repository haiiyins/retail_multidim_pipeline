-- audit.stitching_coverage (runbook §5 DoD): share of web events with a member per country, before stitching (DIRECT = member_id
-- on the event) and after (STITCHED = member attached through slv_user_to_member within ± 90 days of identity_verified_ts); ANON = rest.
-- slv_web_events_clean has one row per event, so no DISTINCT is needed.
WITH j AS (
  SELECT e.country_code,
         CASE WHEN e.member_id_direct IS NOT NULL THEN 'DIRECT' WHEN u.member_id IS NOT NULL THEN 'STITCHED' ELSE 'ANON' END AS id_source
  FROM {{ ref('slv_web_events_clean') }} e
  LEFT JOIN {{ ref('slv_user_to_member') }} u
    ON u.user_id = e.user_id AND e.event_ts_utc BETWEEN u.identity_verified_ts - INTERVAL 90 DAY AND u.identity_verified_ts + INTERVAL 90 DAY
)
SELECT country_code, id_source, COUNT(*) AS n_events,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY country_code), 2) AS pct,
       current_timestamp AS computed_at
FROM j GROUP BY 1, 2 ORDER BY 1, 2
