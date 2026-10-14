SELECT id, session_id, name, country_code, platform, CAST(timestamp_utc AS TIMESTAMP) AS timestamp_utc,
       CAST(date AS DATE) AS event_date, is_event_to_use, _errors, metadata, year, month
FROM {{ source('bronze', 'tracking_ecom_events') }}
WHERE {{ country_where('country_code') }}
