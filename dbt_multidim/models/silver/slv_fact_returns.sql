-- Return lines of finished return transactions: used to drop returned purchases from the labels and for return-rate features.
-- Exact duplicate rows are removed as in slv_fact_sales_line; the original sale is linked through transaction_link_detail
-- (type 'OriginalTransaction'; present on 16 % of the VN return lines, every linked id exists among the sales lines).
WITH r AS (
  SELECT DISTINCT * FROM {{ ref('stg_sales_detail') }}
  WHERE item_operation_type = 'return' AND transaction_status = 'finished'
  QUALIFY transaction_version_at = MAX(transaction_version_at) OVER (PARTITION BY transaction_id, transaction_num_line)
)
SELECT r.transaction_id, r.transaction_num_line, r.item_code, dm.model_code, mb.member_id, r.country_code, r.store_id,
       r.gmv_recorded_at AS return_ts_local, CAST(r.gmv_recorded_at AS DATE) AS return_date,
       r.gmv_item_quantity AS qty, r.gmv_amount AS gmv_local, r.gmv_amount * r.fx_eur AS gmv_eur,
       list_filter(r.transaction_link_detail, lambda x: x.type = 'OriginalTransaction')[1].value AS original_transaction_id,
       r.return_reason_type, r.year, r.month
FROM r
LEFT JOIN {{ ref('slv_member_bridge') }} mb USING (transaction_id)
LEFT JOIN {{ ref('slv_dim_model') }} dm USING (item_code)
