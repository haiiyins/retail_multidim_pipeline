-- WBS 3.5 DoD: the feature entity keeps exactly the rows of gold.anchor_model_grid (LEFT semantics everywhere)
SELECT 'row count differs' AS problem, (SELECT COUNT(*) FROM gold.anchor_model_grid) AS grid_rows, (SELECT COUNT(*) FROM {{ ref('gld_fs_model_country') }}) AS feature_rows
WHERE (SELECT COUNT(*) FROM gold.anchor_model_grid) <> (SELECT COUNT(*) FROM {{ ref('gld_fs_model_country') }})
