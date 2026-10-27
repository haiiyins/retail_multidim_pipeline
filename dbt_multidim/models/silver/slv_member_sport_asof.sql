-- Favourite-sport validity intervals [valid_from, valid_to) per member × sport from the create / delete event log (issue #22).
-- Exact duplicate events are dropped; only state changes are kept: a create after a create (duplicate) and a delete after a
-- delete are ignored. A delete without a prior create means the sport was already active when the export starts
-- (VN: 5,548 of 10,944 deletes): the interval then starts at the export start with from_before_export = true.
-- Open intervals (no delete yet) have valid_to = NULL. is_active is true on every row (each row is an active period).
WITH ev AS (
  SELECT DISTINCT member_id, sport_id, country_code, CAST(event_datetime_utc AS TIMESTAMP) AS ts, event_type
  FROM {{ source('bronze', 'f_member_favorite_sport') }}
  WHERE member_id IS NOT NULL AND sport_id IS NOT NULL AND event_type IN ('create', 'delete')
),
ordered AS (
  SELECT *, LAG(event_type) OVER (PARTITION BY member_id, sport_id ORDER BY ts, event_type) AS prev_type FROM ev
),
changes AS (   -- state changes only
  SELECT *,
         CASE WHEN event_type = 'delete' AND prev_type IS NULL THEN 'PRE_EXPORT_CREATE' ELSE event_type END AS kind
  FROM ordered
  WHERE (event_type = 'create' AND (prev_type IS NULL OR prev_type = 'delete'))
     OR (event_type = 'delete' AND prev_type = 'create')
     OR (event_type = 'delete' AND prev_type IS NULL)
),
seq AS (
  SELECT *, LEAD(ts) OVER (PARTITION BY member_id, sport_id ORDER BY ts) AS next_ts FROM changes
)
SELECT member_id, sport_id, country_code,
       CASE WHEN kind = 'PRE_EXPORT_CREATE' THEN TIMESTAMP '2023-01-01 00:00:00' ELSE ts END AS valid_from,
       CASE WHEN kind = 'PRE_EXPORT_CREATE' THEN ts ELSE next_ts END AS valid_to,
       (kind = 'PRE_EXPORT_CREATE') AS from_before_export,
       true AS is_active
FROM seq
WHERE kind IN ('create', 'PRE_EXPORT_CREATE')
