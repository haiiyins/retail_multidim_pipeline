-- Self-built source #2a: parse Map(k -> v) metadata with regex, keep is_event_to_use, drop marketplace models
WITH raw AS (
  SELECT id AS event_id, session_id, name AS event_name, country_code, platform, timestamp_utc AS event_ts_utc, event_date, year, month,
         {{ extract_map_field('metadata', 'user_id') }}        AS user_id,
         {{ extract_map_field('metadata', 'member_id') }}      AS member_id_direct,
         {{ extract_map_field('metadata', 'transaction_id') }} AS web_transaction_id,
         {{ extract_map_field('metadata', 'page_type') }}      AS page_type,
         {{ extract_map_field('metadata', 'search_term') }}    AS search_term,
         {{ extract_map_field('metadata', 'device_type') }}    AS device_type,
         {{ extract_map_list('metadata', 'model_code') }}      AS model_codes
  FROM {{ ref('stg_tracking_ecom_events') }}
  WHERE CAST(is_event_to_use AS VARCHAR) = 'true' AND (_errors IS NULL OR _errors IN ('null', '', 'List()'))
)
SELECT r.* EXCLUDE (model_codes), u.model_code
FROM raw r LEFT JOIN UNNEST(r.model_codes) AS u(model_code) ON true
WHERE u.model_code IS NULL OR regexp_matches(u.model_code, '^[0-9]+$')
