-- SKU-level price validity intervals; the website business unit (third_type = 50) is the national reference price
SELECT item_code, country_code, currency_code, business_unit_third_type AS bu_type, price_type,
       {{ promo_kind('price_type') }} AS promo_kind,
       CAST(price_start_date AS DATE) AS eff_start,
       CAST(COALESCE(price_end_date, TIMESTAMP '2099-12-31') AS DATE) AS eff_end,
       value_with_taxes AS price, NULLIF(reference_value_with_taxes, 0) AS ref_price
FROM {{ source('bronze', 'all_store_selling_price') }}
WHERE value_with_taxes > 0
  AND price_start_date <= COALESCE(price_end_date, TIMESTAMP '2099-12-31')
  AND (business_unit_third_type = 50 OR {{ var('allow_store_prices') }})
  AND {{ country_where('country_code') }}
