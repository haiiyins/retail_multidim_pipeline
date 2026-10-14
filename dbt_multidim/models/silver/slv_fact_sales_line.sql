-- (1) version dedup on (transaction_id, transaction_num_line) → (2) net out sale–cancel pairs on (transaction_id, item_code)
-- → (3) classify the transaction by SUM(gmv_amount) → keep SALE transactions and physical items only
WITH v AS (
  SELECT * FROM {{ ref('stg_sales_detail') }}
  WHERE transaction_status = 'finished'
  QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id, transaction_num_line ORDER BY transaction_version_at DESC) = 1
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
  GROUP BY 1, 2 HAVING net_qty > 0
),
txn AS (
  SELECT transaction_id,
         CASE WHEN SUM(gmv_amount) > 0 THEN 'SALE' WHEN SUM(gmv_amount) = 0 THEN 'CANCELLED' ELSE 'RETURN' END AS txn_status
  FROM v GROUP BY 1
)
SELECT n.transaction_id, n.item_code, dm.model_code, dm.supermodel_code, dm.sport_department_code, dm.retail_department_code,
       mb.member_id, n.country_code, n.store_id, bu.business_unit_name AS store_name, bu.timezone AS store_tz, n.channel,
       n.gmv_recorded_at AS transaction_ts_local,
       timezone(COALESCE(bu.timezone, 'UTC'), n.gmv_recorded_at) AS transaction_ts_utc,
       CAST(n.gmv_recorded_at AS DATE) AS transaction_date,
       n.net_qty AS qty, n.net_gmv AS gmv_local, n.net_gmv * n.fx_eur AS gmv_eur,
       n.rsp_local, n.rsp_local * n.fx_eur AS rsp_eur, n.discount_local,
       (n.discount_local IS NOT NULL AND n.discount_local > 0) AS bought_with_discount,
       t.txn_status, n.year, n.month
FROM net n
JOIN txn t USING (transaction_id)
LEFT JOIN {{ ref('slv_member_bridge') }} mb USING (transaction_id)
INNER JOIN {{ ref('slv_dim_model') }} dm USING (item_code)
LEFT JOIN {{ source('bronze', 'dim_business_unit') }} bu ON n.store_id = CAST(bu.business_unit_third_id AS VARCHAR)
WHERE COALESCE(n.item_type, '') <> 'service' AND t.txn_status = 'SALE'
