-- Self-built source #2b, step 1: every (cookie, member) link with the moment it became known. Ephemeral, shared by
-- slv_user_to_member and slv_identity_conflicts.
--   ORDER: the web order id (metadata.order_details.transaction_id) is the e-commerce purchase order; it matches
--          sales_detail.customer_purchase_order_id (online lines), never sales_detail.transaction_id (VN sample: 708 of 816
--          orders match), and the member comes from slv_member_bridge through that transaction.
--   LOGIN: the cookie was seen with a member_id in the event itself.
{{ config(materialized='ephemeral') }}
WITH e AS (
  SELECT DISTINCT user_id, member_id_direct, web_transaction_id, event_ts_utc FROM {{ ref('slv_web_events_clean') }} WHERE user_id IS NOT NULL
),
po AS (
  SELECT DISTINCT customer_purchase_order_id AS purchase_order_id, transaction_id
  FROM {{ ref('stg_sales_detail') }} WHERE customer_purchase_order_id IS NOT NULL
),
order_map AS (
  SELECT e.user_id, mb.member_id, MIN(e.event_ts_utc) AS verified_ts, 'ORDER' AS src
  FROM e JOIN po ON po.purchase_order_id = e.web_transaction_id
         JOIN {{ ref('slv_member_bridge') }} mb ON mb.transaction_id = po.transaction_id
  GROUP BY 1, 2
),
login_map AS (
  SELECT user_id, member_id_direct AS member_id, MIN(event_ts_utc) AS verified_ts, 'LOGIN' AS src
  FROM e WHERE member_id_direct IS NOT NULL GROUP BY 1, 2
)
SELECT * FROM order_map UNION ALL SELECT * FROM login_map
