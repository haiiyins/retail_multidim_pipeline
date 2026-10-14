-- Stock SKU → model × site × day, forward-fill ≤ 3 days (no availability_type filter: coverage ≈ 100%)
WITH raw AS (
  SELECT s.country_code, CAST(s.site_gln AS VARCHAR) AS site_gln, dm.model_code, CAST(s.snapshot_date AS DATE) AS snapshot_date,
         MAX(s.is_available) AS any_available, SUM(s.stock_quantity) AS stock_qty,
         AVG(CASE WHEN s.is_available = 1 THEN 1.0 ELSE 0 END) AS avail_rate
  FROM {{ source('bronze', 'stock_availability_rate') }} s
  JOIN {{ ref('slv_dim_model') }} dm USING (item_code)
  WHERE COALESCE(s.blocked_item, 0) = 0 AND {{ country_where('s.country_code') }}
  GROUP BY 1, 2, 3, 4),
keys AS (SELECT DISTINCT country_code, site_gln, model_code FROM raw),
days AS (SELECT DISTINCT snapshot_date AS d FROM raw),
grid AS (SELECT k.*, d.d AS calendar_date FROM keys k CROSS JOIN days d)
SELECT g.country_code, g.site_gln, g.model_code, g.calendar_date,
       LAST_VALUE(r.any_available IGNORE NULLS) OVER w AS is_available_ff,
       LAST_VALUE(r.avail_rate    IGNORE NULLS) OVER w AS avail_rate_ff,
       LAST_VALUE(r.stock_qty     IGNORE NULLS) OVER w AS stock_qty_ff
FROM grid g LEFT JOIN raw r ON r.country_code = g.country_code AND r.site_gln = g.site_gln AND r.model_code = g.model_code AND r.snapshot_date = g.calendar_date
WINDOW w AS (PARTITION BY g.country_code, g.site_gln, g.model_code ORDER BY g.calendar_date ROWS BETWEEN 3 PRECEDING AND CURRENT ROW)
