SELECT country_code, model_code, calendar_date,
       AVG(is_available_ff) AS avail_store_ratio, SUM(stock_qty_ff) AS stock_qty_national
FROM {{ ref('slv_stock_daily_model') }} GROUP BY 1, 2, 3
