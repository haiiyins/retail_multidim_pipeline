-- QC-6 on the stitched table itself: every attributed event must carry a usable identity_verified_ts —
-- equal to the event time for DIRECT events, and within the ± 90-day stitching window for STITCHED events.
SELECT event_id, member_id, id_source, event_ts_utc, identity_verified_ts
FROM {{ ref('gld_web_stitched') }}
WHERE member_id IS NULL OR identity_verified_ts IS NULL
   OR (id_source = 'DIRECT'   AND identity_verified_ts <> event_ts_utc)
   OR (id_source = 'STITCHED' AND event_ts_utc NOT BETWEEN identity_verified_ts - INTERVAL 90 DAY AND identity_verified_ts + INTERVAL 90 DAY)
