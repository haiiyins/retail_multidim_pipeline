-- Sales lines after contextual dedup and sale − cancel netting, BEFORE the business filters (ephemeral; shared by
-- slv_fact_sales_line, which keeps the good rows, and quarantine.qrt_sales_line, which keeps the others with a reason).
-- (1) exact duplicate rows dropped, latest transaction_version_at per (transaction_id, transaction_num_line); rows sharing a line
--     number but differing in quantity / amount are split lines and stay (issue #14)
-- (2) net sale − cancel per (transaction_id, item_code)   (3) transaction status from SUM(gmv_amount) over the finished lines
{{ config(materialized='ephemeral') }}
WITH v AS (
  SELECT DISTINCT * FROM {{ ref('stg_sales_detail') }}
  WHERE transaction_status = 'finished'
  QUALIFY transaction_version_at = MAX(transaction_version_at) OVER (PARTITION BY transaction_id, transaction_num_line)
),
net AS (
  SELECT transaction_id, item_code,
         SUM(CASE item_operation_type WHEN 'sale' THEN gmv_item_quantity WHEN 'cancel' THEN -gmv_item_quantity ELSE 0 END) AS net_qty,
         SUM(CASE item_operation_type WHEN 'sale' THEN gmv_amount        WHEN 'cancel' THEN -gmv_amount        ELSE 0 END) AS net_gmv,
         ANY_VALUE(gmv_recorded_at) AS gmv_recorded_at, ANY_VALUE(country_code) AS country_code,
         ANY_VALUE(store_id) AS store_id, ANY_VALUE(channel) AS channel, ANY_VALUE(item_type) AS item_type,
         ANY_VALUE(regular_selling_price) AS rsp_local, ANY_VALUE(discount_amount) AS discount_local,
         ANY_VALUE(fx_eur) AS fx_eur, ANY_VALUE(year) AS year, ANY_VALUE(month) AS month
  FROM v WHERE item_operation_type IN ('sale', 'cancel')
  GROUP BY 1, 2
),
txn AS (
  SELECT transaction_id,
         CASE WHEN SUM(gmv_amount) > 0 THEN 'SALE' WHEN SUM(gmv_amount) = 0 THEN 'CANCELLED' ELSE 'RETURN' END AS txn_status
  FROM v GROUP BY 1
)
SELECT n.*, t.txn_status, (dm.item_code IS NOT NULL) AS in_catalogue
FROM net n JOIN txn t USING (transaction_id)
LEFT JOIN {{ ref('slv_dim_model') }} dm USING (item_code)
