-- Co-purchase lift P(a,b)/(P(a)P(b)) computed on transactions before the first test anchor (vars.copurchase_cutoff) to avoid leakage
{% set cutoff = var('copurchase_cutoff', '2025-01-01') %}
WITH b AS (SELECT DISTINCT transaction_id, model_code, country_code FROM {{ ref('slv_fact_sales_line') }} WHERE transaction_date < '{{ cutoff }}'),
n AS (SELECT country_code, COUNT(DISTINCT transaction_id) n_tx FROM b GROUP BY 1),
pa AS (SELECT country_code, model_code, COUNT(DISTINCT transaction_id) n_a FROM b GROUP BY 1, 2),
pair AS (SELECT x.country_code, x.model_code model_a, y.model_code model_b, COUNT(DISTINCT x.transaction_id) n_ab
         FROM b x JOIN b y ON x.transaction_id = y.transaction_id AND x.model_code < y.model_code GROUP BY 1, 2, 3 HAVING n_ab >= 5),
sym AS (SELECT country_code, model_a, model_b, n_ab FROM pair UNION ALL SELECT country_code, model_b, model_a, n_ab FROM pair)
SELECT s.country_code, s.model_a, s.model_b, s.n_ab,
       (s.n_ab * n.n_tx * 1.0) / (a.n_a * bb.n_a) AS lift,
       ROW_NUMBER() OVER (PARTITION BY s.country_code, s.model_a ORDER BY (s.n_ab * n.n_tx * 1.0) / (a.n_a * bb.n_a) DESC) AS rank_in_a
FROM sym s JOIN n USING (country_code) JOIN pa a ON a.country_code = s.country_code AND a.model_code = s.model_a
JOIN pa bb ON bb.country_code = s.country_code AND bb.model_code = s.model_b
