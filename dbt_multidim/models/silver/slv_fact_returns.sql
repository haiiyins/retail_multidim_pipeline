-- Return lines (used to drop returned positives from labels and to compute return rates)
WITH r AS (
  SELECT * FROM {{ ref('stg_sales_detail') }} WHERE item_operation_type = 'return'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id, transaction_num_line ORDER BY transaction_version_at DESC) = 1
)
SELECT r.transaction_id, r.transaction_num_line, r.item_code, dm.model_code, mb.member_id, r.country_code,
       CAST(r.gmv_recorded_at AS DATE) AS return_date, r.gmv_item_quantity AS qty, r.gmv_amount AS gmv_local
FROM r
LEFT JOIN {{ ref('slv_member_bridge') }} mb USING (transaction_id)
LEFT JOIN {{ ref('slv_dim_model') }} dm USING (item_code)
