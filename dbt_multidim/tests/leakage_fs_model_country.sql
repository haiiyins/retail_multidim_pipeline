-- QC-6: no model × country row may use a transaction or a price interval that starts after the anchor
SELECT model_code, country_code, anchor_date, last_source_ts FROM {{ ref('gld_fs_model_country') }}
WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)
