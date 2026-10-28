-- Model-to-model co-purchase statistics per country: support, confidence P(b | a) and lift P(a,b) / (P(a) P(b)) over baskets
-- (transactions) dated before vars.copurchase_cutoff. The cutoff equals valid_lo of evaluation/split.yml so that no purchase
-- that can be a validation or test label contributes (QC-6; tests/copurchase_cutoff_before_validation.sql). One table serves
-- every anchor, including training anchors that precede part of the window — a static-statistics approximation recorded in
-- DESIGN_DECISIONS §6. Pairs need at least vars.copurchase_min_support common baskets; rank_in_a orders b by lift within a.
{% set cutoff = var('copurchase_cutoff') %}
{% set min_support = var('copurchase_min_support', 5) | int %}
{% set strong = var('copurchase_strong_support', 10) | int %}
WITH b AS (
    SELECT DISTINCT country_code, transaction_id, model_code
    FROM {{ ref('slv_fact_sales_line') }}
    WHERE transaction_date < DATE '{{ cutoff }}'),
n AS (SELECT country_code, COUNT(DISTINCT transaction_id) AS n_tx FROM b GROUP BY 1),
pa AS (SELECT country_code, model_code, COUNT(*) AS n_a FROM b GROUP BY 1, 2),          -- b is distinct per basket × model
pair AS (
    SELECT x.country_code, x.model_code AS model_a, y.model_code AS model_b, COUNT(*) AS n_ab
    FROM b x JOIN b y ON y.country_code = x.country_code AND y.transaction_id = x.transaction_id AND x.model_code < y.model_code
    GROUP BY 1, 2, 3 HAVING COUNT(*) >= {{ min_support }}),
sym AS (SELECT country_code, model_a, model_b, n_ab FROM pair
        UNION ALL SELECT country_code, model_b, model_a, n_ab FROM pair)
SELECT s.country_code, s.model_a, s.model_b, s.n_ab,
       s.n_ab * 1.0 / n.n_tx AS support,
       s.n_ab * 1.0 / a.n_a AS confidence,
       (s.n_ab * 1.0 * n.n_tx) / (a.n_a * bb.n_a) AS lift,
       -- rank_in_a: pairs with at least copurchase_strong_support common baskets first (by lift), then the rarer pairs by lift;
       -- a pure lift order is dominated by pairs seen 5–9 times (60 % of the VN top-20). rank_by_support orders by common baskets.
       ROW_NUMBER() OVER (PARTITION BY s.country_code, s.model_a
                          ORDER BY (s.n_ab >= {{ strong }}) DESC, (s.n_ab * 1.0 * n.n_tx) / (a.n_a * bb.n_a) DESC, s.n_ab DESC, s.model_b) AS rank_in_a,
       ROW_NUMBER() OVER (PARTITION BY s.country_code, s.model_a ORDER BY s.n_ab DESC, s.model_b) AS rank_by_support,
       DATE '{{ cutoff }}' AS cutoff_date
FROM sym s
JOIN n USING (country_code)
JOIN pa a  ON a.country_code = s.country_code AND a.model_code = s.model_a
JOIN pa bb ON bb.country_code = s.country_code AND bb.model_code = s.model_b
