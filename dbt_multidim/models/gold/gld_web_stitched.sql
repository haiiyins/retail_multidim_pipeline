-- Web events attributed to a member (direct or stitched within ±90 days), with identity_verified_ts for QC-6
SELECT e.event_id, e.session_id, e.country_code, e.event_name, e.event_ts_utc, e.event_date, e.model_code, e.search_term, e.page_type,
       COALESCE(e.member_id_direct, u.member_id) AS member_id,
       CASE WHEN e.member_id_direct IS NOT NULL THEN 'DIRECT' WHEN u.member_id IS NOT NULL THEN 'STITCHED' ELSE 'ANON' END AS id_source,
       CASE WHEN e.member_id_direct IS NOT NULL THEN e.event_ts_utc ELSE u.identity_verified_ts END AS identity_verified_ts
FROM {{ ref('slv_web_events_clean') }} e
LEFT JOIN {{ ref('slv_user_to_member') }} u
  ON u.user_id = e.user_id AND e.event_ts_utc BETWEEN u.identity_verified_ts - INTERVAL 90 DAY AND u.identity_verified_ts + INTERVAL 90 DAY
WHERE COALESCE(e.member_id_direct, u.member_id) IS NOT NULL
