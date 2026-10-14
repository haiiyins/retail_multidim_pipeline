-- QC-6: no row may use source data after the anchor
SELECT * FROM {{ ref('gld_fs_member') }} WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)
