-- Self-built source #2a: flatten the metadata struct of the web events, keep the exporter's is_event_to_use verdict.
-- One row per event: the product codes stay as a list (model_codes, numeric codes only — marketplace sellers are dropped) and
-- are unnested only in gld_web_stitched for the events that can be attributed to a member. Exploding here multiplied the
-- table by 4.4 (VN sample: 464 k events → 2.03 M rows), which on the three-country export of 1.0 bn events means ~4 bn rows.
-- _errors is a list of soft quality checks present on every event; it is not a filter (issue #6, data owner 2026-10-28).
SELECT id AS event_id, session_id, name AS event_name, country_code, platform, timestamp_utc AS event_ts_utc, event_date, year, month,
       metadata.user_details.user_id            AS user_id,
       metadata.user_details.member_id          AS member_id_direct,
       metadata.order_details.transaction_id    AS web_transaction_id,
       metadata.page_details.page_type          AS page_type,
       metadata.search_details.search_term      AS search_term,
       metadata.device_details.device_type      AS device_type,
       list_filter({{ product_model_codes('metadata') }}, lambda m: regexp_matches(m, '^[0-9]+$')) AS model_codes
FROM {{ ref('stg_tracking_ecom_events') }}
WHERE CAST(is_event_to_use AS VARCHAR) = 'true'
