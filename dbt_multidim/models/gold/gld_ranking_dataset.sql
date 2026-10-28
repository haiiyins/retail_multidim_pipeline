-- Training / evaluation set: pair features + labels. label_Δ = 1 when the member buys the candidate model in (anchor, anchor + Δ]
-- and that purchase is not returned (slv_fact_returns on transaction × model). Split membership and in_train_sample come from
-- gold.anchor_grid through the candidates; the ranker reads them, never as features.
WITH p AS (SELECT * FROM {{ ref('gld_fs_pair') }}),
buy AS (
  SELECT f.member_id, f.model_code, f.transaction_date
  FROM {{ ref('slv_fact_sales_line') }} f
  WHERE f.member_id IS NOT NULL
    AND NOT EXISTS (SELECT 1 FROM {{ ref('slv_fact_returns') }} r WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code)),
nxt AS (   -- first non-returned purchase of the candidate model after the anchor, within 90 days
  SELECT p.member_id, p.anchor_date, p.model_code, MIN(b.transaction_date) - p.anchor_date AS days_to_buy
  FROM p JOIN buy b ON b.member_id = p.member_id AND b.model_code = p.model_code
                   AND b.transaction_date > p.anchor_date AND b.transaction_date <= p.anchor_date + 90
  GROUP BY 1, 2, 3)
SELECT p.*,
       CAST(COALESCE(n.days_to_buy <= 30, FALSE) AS INT) AS label_30,
       CAST(COALESCE(n.days_to_buy <= 90, FALSE) AS INT) AS label_90,
       0 AS forced_positive
FROM p LEFT JOIN nxt n USING (member_id, anchor_date, model_code)
