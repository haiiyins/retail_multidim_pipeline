-- Catalogue at SKU → model level; drop marketplace (UUID) and service items
SELECT item_code, model_code, model_label, supermodel_code, supermodel_label, item_category_label,
       product_nature_id, product_nature_label, product_nature_type,
       retail_department_code, retail_department_label, retail_univers_code, retail_univers_label,
       sport_department_code, sport_department_label, sport_univers_code, sport_univers_label,
       brand_type, age, item_size,
       -- gender is a real LIST<VARCHAR> in the 2026-10-28 Parquet export and a JSON-style list string in the older CSV
       -- (["WOMEN"], ["BOYS","GIRLS"]); casting to VARCHAR first makes both read as [WOMEN] / [BOYS, GIRLS]
       CASE WHEN gender IS NULL OR trim(regexp_replace(CAST(gender AS VARCHAR), '[\[\]"()]|^List', '', 'g')) IN ('', 'null') THEN 'UNISEX'
            ELSE array_to_string(list_sort(list_transform(string_split(regexp_replace(CAST(gender AS VARCHAR), '[\[\]"()]|^List', '', 'g'), ','), lambda g: trim(g))), '|') END AS gender_std
FROM {{ source('bronze', 'dim_item') }}
WHERE item_code IS NOT NULL AND model_code IS NOT NULL
  AND NOT regexp_matches(item_code, '^[0-9a-fA-F]{8}-')
  AND COALESCE(LOWER(product_nature_type), '') NOT IN ('service', 'services', 'fee', 'financial')
  AND COALESCE(retail_univers_label, '') <> 'SERVICES'
  AND COALESCE(retail_univers_label, '') <> 'FIXT & FURNIT'   -- store fixtures, carrier bags, printing, POS material: sold at the till but not merchandise (issue #31)
  AND COALESCE(retail_sub_department_label, '') NOT IN ('To empty', 'components created in TRACE')
