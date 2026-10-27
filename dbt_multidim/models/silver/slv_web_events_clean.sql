-- Self-built source #2a: flatten the metadata struct of the web events, keep the exporter's is_event_to_use verdict,
-- one row per (event, model_code); non-numeric model codes (marketplace sellers) are dropped.
-- _errors is a list of soft quality checks present on every event; it is not a filter (issue #6).
WITH raw AS (
  SELECT id AS event_id, session_id, name AS event_name, country_code, platform, timestamp_utc AS event_ts_utc, event_date, year, month,
         metadata.user_details.user_id            AS user_id,
         metadata.user_details.member_id          AS member_id_direct,
         metadata.order_details.transaction_id    AS web_transaction_id,
         metadata.page_details.page_type          AS page_type,
         metadata.search_details.search_term      AS search_term,
         metadata.device_details.device_type      AS device_type,
         {{ product_model_codes('metadata') }}    AS model_codes
  FROM {{ ref('stg_tracking_ecom_events') }}
  WHERE CAST(is_event_to_use AS VARCHAR) = 'true'
)
SELECT r.* EXCLUDE (model_codes), u.model_code
FROM raw r LEFT JOIN UNNEST(r.model_codes) AS u(model_code) ON true
WHERE u.model_code IS NULL OR regexp_matches(u.model_code, '^[0-9]+$')
