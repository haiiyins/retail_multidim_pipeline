-- Web / app events attributed to a member, with the timestamp from which the attribution is known (identity_verified_ts) so that
-- every consumer can apply the point-in-time rule identity_verified_ts <= anchor_date (QC-6, tests/leakage_web_identity.sql).
--   DIRECT   the event itself carries member_id (login); known at the event time
--   STITCHED the cookie (user_id) is mapped to exactly one member in slv_user_to_member and the event lies within ± 90 days of
--            the mapping's identity_verified_ts (order- or login-based evidence); known from identity_verified_ts
-- Anonymous events are dropped here; audit.stitching_coverage keeps the before / after shares per country. The product list of an
-- attributed event is unnested here (one row per event × model_code; an event without products keeps one row with NULL), so the
-- explosion only touches the ~35 % of events that have a member. The unnest is a plain UNNEST in the select list: written as
-- LEFT JOIN UNNEST(...) ON true, DuckDB 2.0 plans a delim join with a Window over the whole attributed set, which on the full
-- scope (~350 M events) materialised 135 GB of temp in 80 min without finishing; the select-list form streams (same rows, checked on VN).
WITH attributed AS (
  SELECT e.event_id, e.session_id, e.user_id, e.country_code, e.platform, e.event_name, e.event_ts_utc, e.event_date,
         e.model_codes, e.search_term, e.page_type, e.web_transaction_id,
         COALESCE(e.member_id_direct, u.member_id) AS member_id,
         CASE WHEN e.member_id_direct IS NOT NULL THEN 'DIRECT' ELSE 'STITCHED' END AS id_source,
         CASE WHEN e.member_id_direct IS NOT NULL THEN e.event_ts_utc ELSE u.identity_verified_ts END AS identity_verified_ts
  FROM {{ ref('slv_web_events_clean') }} e
  LEFT JOIN {{ ref('slv_user_to_member') }} u
    ON u.user_id = e.user_id AND e.event_ts_utc BETWEEN u.identity_verified_ts - INTERVAL 90 DAY AND u.identity_verified_ts + INTERVAL 90 DAY
  WHERE COALESCE(e.member_id_direct, u.member_id) IS NOT NULL
)
SELECT a.* EXCLUDE (model_codes),
       UNNEST(CASE WHEN a.model_codes IS NULL OR len(a.model_codes) = 0 THEN [NULL]::VARCHAR[] ELSE a.model_codes END) AS model_code
FROM attributed a
