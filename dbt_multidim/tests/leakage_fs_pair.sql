SELECT * FROM {{ ref('gld_fs_pair') }} WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)
