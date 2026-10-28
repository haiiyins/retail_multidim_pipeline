-- Entity 1: member features at (member_id, anchor_date), for the used anchors of gold.anchor_grid. Every aggregate reads data
-- strictly before the anchor (dates < anchor_date; links known at the anchor); last_source_ts is the latest source timestamp
-- that fed the row, checked by tests/leakage_fs_member.sql (QC-6). Feature groups (schema.yml meta.group, ablation_configs.yml):
-- F0 purchase history · F1 price position · F3 promotion affinity · F5 web activity · Sport · Store. web_data_available separates
-- "no web activity" from "no web data": usable VN events start 2024-07 (data owner, issue #20), so the flag is false before that.
WITH g AS (SELECT member_id, country_code, anchor_date, split, in_train_sample FROM gold.anchor_grid WHERE is_used),
tx AS (
  SELECT g.member_id, g.anchor_date,
         COUNT(DISTINCT CASE WHEN f.transaction_date >= g.anchor_date - 30 THEN f.transaction_id END) AS tx_30d,
         COUNT(DISTINCT CASE WHEN f.transaction_date >= g.anchor_date - 90 THEN f.transaction_id END) AS tx_90d,
         COUNT(DISTINCT f.transaction_id) AS tx_365d,
         SUM(f.qty) AS items_365d,
         COUNT(DISTINCT f.model_code) AS models_365d,
         g.anchor_date - MAX(f.transaction_date) AS days_since_last_tx,
         QUANTILE_CONT(f.rsp_local, 0.25) AS price_q25, QUANTILE_CONT(f.rsp_local, 0.5) AS price_q50, QUANTILE_CONT(f.rsp_local, 0.75) AS price_q75,
         QUANTILE_CONT(f.rsp_eur, 0.5) AS price_q50_eur,
         AVG(CAST(f.bought_with_discount AS INT)) AS promo_affinity,
         SUM(f.gmv_eur) AS gmv_eur_365d,
         MAX(f.transaction_ts_utc) AS last_tx_ts
  FROM g JOIN {{ ref('slv_fact_sales_line') }} f
    ON f.member_id = g.member_id AND f.transaction_date < g.anchor_date AND f.transaction_date >= g.anchor_date - 365
  GROUP BY 1, 2),
ret AS (
  SELECT g.member_id, g.anchor_date,
         COUNT(DISTINCT COALESCE(r.original_transaction_id, r.transaction_id)) AS returned_tx_365d,
         MAX(r.return_ts_local) AS last_ret_ts
  FROM g JOIN {{ ref('slv_fact_returns') }} r
    ON r.member_id = g.member_id AND r.return_date < g.anchor_date AND r.return_date >= g.anchor_date - 365
  GROUP BY 1, 2),
store AS (   -- running usual store as of the last offline purchase day strictly before the anchor (#23)
  SELECT g.member_id, g.anchor_date, s.usual_store_id, s.usual_store_share, s.stores_visited_cum, s.as_of_date AS store_as_of
  FROM g ASOF LEFT JOIN {{ ref('slv_member_store_daily') }} s
    ON s.member_id = g.member_id AND s.as_of_date < g.anchor_date),
sport AS (   -- favourite sports whose validity interval covers the anchor (#22)
  SELECT g.member_id, g.anchor_date, COUNT(*) AS n_sports, LIST(sa.sport_id ORDER BY sa.sport_id) AS sport_ids, MAX(sa.valid_from) AS last_sport_ts
  FROM g JOIN {{ ref('slv_member_sport_asof') }} sa
    ON sa.member_id = g.member_id AND sa.is_active
   AND sa.valid_from <= CAST(g.anchor_date AS TIMESTAMP) AND (sa.valid_to IS NULL OR sa.valid_to > CAST(g.anchor_date AS TIMESTAMP))
  GROUP BY 1, 2),
web AS (     -- attributed web / app events in the 30 days before the anchor, attribution known at the anchor (#30)
  SELECT g.member_id, g.anchor_date,
         COUNT(DISTINCT CASE WHEN w.event_date >= g.anchor_date - 7 THEN w.session_id END) AS web_sessions_7d,
         COUNT(DISTINCT w.session_id) AS web_sessions_30d,
         COUNT(DISTINCT w.event_id) AS web_events_30d,
         COUNT(DISTINCT w.model_code) AS web_models_30d,
         MAX(w.event_ts_utc) AS last_web_ts
  FROM g JOIN {{ ref('gld_web_stitched') }} w
    ON w.member_id = g.member_id AND w.event_date BETWEEN g.anchor_date - 30 AND g.anchor_date - 1
   AND w.identity_verified_ts <= CAST(g.anchor_date AS TIMESTAMP)
  GROUP BY 1, 2),
web_cov AS (SELECT DISTINCT country_code, event_date FROM {{ ref('slv_web_events_clean') }}),
web_avail AS (   -- days with usable web events in the country during the 30-day window: 0 means the signal is absent, not quiet
  SELECT a.country_code, a.anchor_date, COUNT(c.event_date) AS web_days_available_30d
  FROM (SELECT DISTINCT country_code, anchor_date FROM g) a
  LEFT JOIN web_cov c ON c.country_code = a.country_code AND c.event_date BETWEEN a.anchor_date - 30 AND a.anchor_date - 1
  GROUP BY 1, 2)
SELECT g.member_id, g.country_code, g.anchor_date, g.split, g.in_train_sample,
       -- F0 purchase history
       COALESCE(tx.tx_30d, 0) AS tx_30d, COALESCE(tx.tx_90d, 0) AS tx_90d, COALESCE(tx.tx_365d, 0) AS tx_365d,
       COALESCE(tx.items_365d, 0) AS items_365d, COALESCE(tx.models_365d, 0) AS models_365d,
       tx.days_since_last_tx, COALESCE(tx.gmv_eur_365d, 0) AS gmv_eur_365d,
       LEAST(1.0, COALESCE(ret.returned_tx_365d, 0) * 1.0 / NULLIF(tx.tx_365d, 0)) AS return_rate,
       date_diff('day', p.account_created_at, CAST(g.anchor_date AS TIMESTAMP)) AS account_tenure_days,
       -- F1 price position
       tx.price_q25, tx.price_q50, tx.price_q75, tx.price_q50_eur,
       -- F3 promotion affinity
       tx.promo_affinity,
       -- Sport
       COALESCE(sport.n_sports, 0) AS n_sports, sport.sport_ids,
       -- Store
       store.usual_store_id, store.usual_store_share, store.stores_visited_cum,
       -- F5 web activity
       COALESCE(web.web_sessions_7d, 0) AS web_sessions_7d, COALESCE(web.web_sessions_30d, 0) AS web_sessions_30d,
       COALESCE(web.web_events_30d, 0) AS web_events_30d, COALESCE(web.web_models_30d, 0) AS web_models_30d,
       (COALESCE(web.web_sessions_30d, 0) > 0) AS has_web_signal,
       COALESCE(wa.web_days_available_30d, 0) AS web_days_available_30d,
       (COALESCE(wa.web_days_available_30d, 0) > 0) AS web_data_available,
       -- QC-6 bookkeeping
       GREATEST(tx.last_tx_ts, ret.last_ret_ts, CAST(store.store_as_of AS TIMESTAMP), sport.last_sport_ts, web.last_web_ts) AS last_source_ts
FROM g
LEFT JOIN tx USING (member_id, anchor_date)
LEFT JOIN ret USING (member_id, anchor_date)
LEFT JOIN store USING (member_id, anchor_date)
LEFT JOIN sport USING (member_id, anchor_date)
LEFT JOIN web USING (member_id, anchor_date)
LEFT JOIN web_avail wa USING (country_code, anchor_date)
LEFT JOIN {{ ref('slv_member_profile') }} p USING (member_id)
