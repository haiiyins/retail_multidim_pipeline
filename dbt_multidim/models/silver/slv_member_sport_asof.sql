-- Favourite-sport state as [valid_from, valid_to) intervals from the create/delete event log
SELECT member_id, sport_id, CAST(event_datetime_utc AS TIMESTAMP) AS valid_from,
       LEAD(CAST(event_datetime_utc AS TIMESTAMP)) OVER (PARTITION BY member_id, sport_id ORDER BY event_datetime_utc) AS valid_to,
       (event_type = 'create') AS is_active
FROM {{ source('bronze', 'f_member_favorite_sport') }}
