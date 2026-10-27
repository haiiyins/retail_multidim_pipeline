-- QC-3 routing (issue #24): national price rows whose promotion depth falls outside [0, 0.9]; slv_price_sku_interval excludes them.
-- ABOVE_REFERENCE  promotional price above the reference price     DEPTH_GT_0_9  more than 90 % off the reference price
SELECT item_code, country_code, currency_code, price_type, CAST(price_start_date AS DATE) AS eff_start,
       CAST(COALESCE(price_end_date, TIMESTAMP '2099-12-31') AS DATE) AS eff_end,
       value_with_taxes AS price, reference_value_with_taxes AS ref_price, ROUND(1 - value_with_taxes / reference_value_with_taxes, 4) AS promo_depth,
       CASE WHEN value_with_taxes > reference_value_with_taxes THEN 'ABOVE_REFERENCE' ELSE 'DEPTH_GT_0_9' END AS reason
FROM {{ source('bronze', 'all_store_selling_price') }}
WHERE value_with_taxes > 0 AND price_type <> 'STANDARD' AND COALESCE(reference_value_with_taxes, 0) > 0
  AND (business_unit_third_type = 50 OR {{ var('allow_store_prices') }})
  AND {{ country_where('country_code') }}
  AND NOT ((1 - value_with_taxes / reference_value_with_taxes) BETWEEN 0 AND 0.9)
