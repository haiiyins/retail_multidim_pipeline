-- Self-built source #2b: identity stitching (order-based + login-based); conflict rule: a cookie must map to exactly one member
WITH e AS (SELECT DISTINCT user_id, member_id_direct, web_transaction_id, event_ts_utc FROM {{ ref('slv_web_events_clean') }} WHERE user_id IS NOT NULL),
order_map AS (SELECT e.user_id, mb.member_id, MIN(e.event_ts_utc) AS verified_ts, 'ORDER' AS src
              FROM e JOIN {{ ref('slv_member_bridge') }} mb ON e.web_transaction_id = mb.transaction_id GROUP BY 1, 2),
login_map AS (SELECT user_id, member_id_direct AS member_id, MIN(event_ts_utc) AS verified_ts, 'LOGIN' AS src
              FROM e WHERE member_id_direct IS NOT NULL GROUP BY 1, 2),
allm AS (SELECT * FROM order_map UNION ALL SELECT * FROM login_map)
SELECT user_id, ANY_VALUE(member_id) AS member_id, MIN(verified_ts) AS identity_verified_ts,
       LIST(DISTINCT src) AS methods, COUNT(DISTINCT member_id) AS n_members
FROM allm GROUP BY user_id HAVING COUNT(DISTINCT member_id) = 1
