-- Training / evaluation set: pair features + labels for Δ = 30 / 90 (returned purchases excluded)
WITH p AS (SELECT * FROM {{ ref('gld_fs_pair') }}),
buy AS (SELECT f.member_id, f.model_code, f.transaction_id, f.transaction_date FROM {{ ref('slv_fact_sales_line') }} f
        WHERE NOT EXISTS (SELECT 1 FROM {{ ref('slv_fact_returns') }} r WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code))
SELECT p.*,
       CAST(EXISTS (SELECT 1 FROM buy b WHERE b.member_id = p.member_id AND b.model_code = p.model_code AND b.transaction_date > p.anchor_date AND b.transaction_date <= p.anchor_date + 30) AS INT) AS label_30,
       CAST(EXISTS (SELECT 1 FROM buy b WHERE b.member_id = p.member_id AND b.model_code = p.model_code AND b.transaction_date > p.anchor_date AND b.transaction_date <= p.anchor_date + 90) AS INT) AS label_90,
       0 AS forced_positive
FROM p
