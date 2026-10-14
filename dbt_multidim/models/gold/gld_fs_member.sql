-- Entity 1: member features at (member_id, anchor_date) — data strictly before anchor_date
WITH g AS (SELECT * FROM gold.anchor_grid),
tx AS (
  SELECT g.member_id, g.anchor_date,
         COUNT(DISTINCT CASE WHEN f.transaction_date >= g.anchor_date - 30  THEN f.transaction_id END) AS tx_30d,
         COUNT(DISTINCT CASE WHEN f.transaction_date >= g.anchor_date - 90  THEN f.transaction_id END) AS tx_90d,
         COUNT(DISTINCT f.transaction_id) AS tx_365d,
         g.anchor_date - MAX(f.transaction_date) AS days_since_last_tx,
         QUANTILE_CONT(f.rsp_local, 0.25) AS price_q25, QUANTILE_CONT(f.rsp_local, 0.5) AS price_q50, QUANTILE_CONT(f.rsp_local, 0.75) AS price_q75,
         QUANTILE_CONT(f.rsp_eur, 0.5) AS price_q50_eur,
         AVG(CAST(f.bought_with_discount AS INT)) AS promo_affinity,
         SUM(f.gmv_eur) AS gmv_eur_365d,
         MAX(f.transaction_ts_utc) AS last_source_ts
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f
    ON f.member_id = g.member_id AND f.transaction_date < g.anchor_date AND f.transaction_date >= g.anchor_date - 365
  GROUP BY 1, 2),
ret AS (SELECT g.member_id, g.anchor_date, COUNT(*) AS n_ret FROM g JOIN {{ ref('slv_fact_returns') }} r
        ON r.member_id = g.member_id AND r.return_date < g.anchor_date AND r.return_date >= g.anchor_date - 365 GROUP BY 1, 2),
store AS (SELECT member_id, anchor_date, store_id AS usual_store_id FROM (
          SELECT g.member_id, g.anchor_date, s.store_id,
                 ROW_NUMBER() OVER (PARTITION BY g.member_id, g.anchor_date ORDER BY SUM(s.n_lines) DESC, MAX(s.transaction_date) DESC) rn
          FROM g JOIN {{ ref('slv_member_store_daily') }} s ON s.member_id = g.member_id
            AND s.transaction_date BETWEEN g.anchor_date - 180 AND g.anchor_date - 1 GROUP BY 1, 2, 3) WHERE rn = 1),
sport AS (SELECT g.member_id, g.anchor_date, COUNT(*) AS n_sports, LIST(sa.sport_id) AS sport_ids
          FROM g JOIN {{ ref('slv_member_sport_asof') }} sa ON sa.member_id = g.member_id AND sa.is_active
            AND sa.valid_from <= g.anchor_date AND (sa.valid_to IS NULL OR sa.valid_to > g.anchor_date) GROUP BY 1, 2),
web AS (SELECT g.member_id, g.anchor_date, COUNT(DISTINCT w.session_id) AS web_sessions_30d
        FROM g JOIN {{ ref('gld_web_stitched') }} w ON w.member_id = g.member_id
          AND w.event_date BETWEEN g.anchor_date - 30 AND g.anchor_date - 1 AND w.identity_verified_ts <= g.anchor_date GROUP BY 1, 2)
SELECT g.member_id, g.country_code, g.anchor_date, g.in_train_sample,
       tx.tx_30d, tx.tx_90d, tx.tx_365d, tx.days_since_last_tx, tx.price_q25, tx.price_q50, tx.price_q75, tx.price_q50_eur,
       tx.promo_affinity, tx.gmv_eur_365d,
       COALESCE(ret.n_ret, 0) * 1.0 / NULLIF(tx.tx_365d, 0) AS return_rate,
       store.usual_store_id, COALESCE(sport.n_sports, 0) AS n_sports, sport.sport_ids,
       COALESCE(web.web_sessions_30d, 0) AS web_sessions_30d, (COALESCE(web.web_sessions_30d, 0) > 0) AS has_web_signal,
       date_diff('day', p.account_created_at, CAST(g.anchor_date AS TIMESTAMP)) AS account_tenure_days,
       tx.last_source_ts
FROM g
LEFT JOIN tx USING (member_id, anchor_date) LEFT JOIN ret USING (member_id, anchor_date)
LEFT JOIN store USING (member_id, anchor_date) LEFT JOIN sport USING (member_id, anchor_date)
LEFT JOIN web USING (member_id, anchor_date)
LEFT JOIN {{ ref('slv_member_profile') }} p USING (member_id)
