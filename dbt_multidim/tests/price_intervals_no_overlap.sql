-- QC-4: no two price intervals of the same SKU × country × scope × price type overlap
SELECT a.item_code, a.country_code, a.price_scope, a.price_type, a.eff_start, a.eff_end, b.eff_start AS next_start
FROM {{ ref('slv_price_sku_interval') }} a
JOIN {{ ref('slv_price_sku_interval') }} b
  ON a.item_code = b.item_code AND a.country_code = b.country_code AND a.price_scope = b.price_scope AND a.price_type = b.price_type
 AND a.eff_start < b.eff_start AND b.eff_start <= a.eff_end
