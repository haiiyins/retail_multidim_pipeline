-- SKU price validity intervals per country. The COUNTRY business unit (third_type = 15, one unit per country) is the national
-- reference price (data owner, 2026-10-28); the four website units (type 50) repeat it row for row and are only a fallback
-- for a key without a type-15 row, and the stores carry the same prices (audit.price_uniformity, VN gap 0.0). Rows collapse
-- to one national timeline (price_scope = 'NATIONAL'; a store GLN when allow_store_prices is true). Overlapping intervals of the same price type are resolved "latest start wins": the earlier
-- interval is closed the day before the next one starts (VN: 71,571 of 536,016 website keys overlap in the export).
-- promo_depth = 1 - price / reference price; QC-3 keeps [0, 0.9], rows outside are excluded here and routed to quarantine in #24.
WITH src AS (
  SELECT DISTINCT item_code, country_code, currency_code, price_type, business_unit_third_type,
         CASE WHEN business_unit_third_type IN (15, 50) THEN 'NATIONAL' ELSE business_unit_gln_code END AS price_scope,
         CAST(price_start_date AS DATE) AS eff_start,
         CAST(COALESCE(price_end_date, TIMESTAMP '2099-12-31') AS DATE) AS raw_end,
         value_with_taxes AS price, NULLIF(reference_value_with_taxes, 0) AS ref_price, source_send_date
  FROM {{ source('bronze', 'all_store_selling_price') }}
  WHERE value_with_taxes > 0
    AND price_start_date <= COALESCE(price_end_date, TIMESTAMP '2099-12-31')
    AND (business_unit_third_type IN (15, 50) OR {{ var('allow_store_prices') }})
    AND {{ country_where('country_code') }}
),
one_per_start AS (   -- several prices for the same start date: the COUNTRY unit wins over the websites, then the most recently sent one
  SELECT * EXCLUDE (business_unit_third_type) FROM src
  QUALIFY ROW_NUMBER() OVER (PARTITION BY item_code, country_code, price_scope, price_type, eff_start
                             ORDER BY (business_unit_third_type = 15) DESC, source_send_date DESC NULLS LAST, raw_end DESC) = 1
),
closed AS (
  SELECT *, LEAST(raw_end, COALESCE(LEAD(eff_start) OVER (PARTITION BY item_code, country_code, price_scope, price_type ORDER BY eff_start) - INTERVAL 1 DAY, raw_end)) AS eff_end
  FROM one_per_start
)
SELECT item_code, country_code, currency_code, price_scope, price_type,
       {{ promo_kind('price_type') }} AS promo_kind,
       {{ promo_kind('price_type') }} IN ('DAILY', 'SEASONAL') AS is_temp_promo,
       eff_start, CAST(eff_end AS DATE) AS eff_end, price, ref_price,
       CASE WHEN price_type = 'STANDARD' OR ref_price IS NULL THEN 0 ELSE ROUND(1 - price / ref_price, 4) END AS promo_depth
FROM closed
WHERE CAST(eff_end AS DATE) >= eff_start
  AND (price_type = 'STANDARD' OR ref_price IS NULL OR (1 - price / ref_price) BETWEEN 0 AND 0.9)
