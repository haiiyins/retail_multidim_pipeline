-- QC-3 / QC-4 routing (issue #24): netted (transaction, item) rows that slv_fact_sales_line does not keep, with the reason.
-- NET_QTY_NONPOSITIVE   sale and cancel lines net to zero or less      NET_GMV_NONPOSITIVE  quantity left but gmv <= 0 (free / refunded)
-- TXN_NOT_SALE          whole transaction nets to <= 0 (CANCELLED / RETURN)   SERVICE_LINE  fee / workshop / delivery line (by design)
-- ITEM_NOT_IN_CATALOGUE physical item missing from slv_dim_model (incomplete dim_item export, issue #54)
SELECT transaction_id, item_code, country_code, store_id, channel, item_type, txn_status, net_qty, net_gmv, gmv_recorded_at, year, month,
       CASE WHEN net_qty <= 0 THEN 'NET_QTY_NONPOSITIVE'
            WHEN net_gmv <= 0 THEN 'NET_GMV_NONPOSITIVE'
            WHEN txn_status <> 'SALE' THEN 'TXN_NOT_SALE'
            WHEN COALESCE(item_type, '') = 'service' THEN 'SERVICE_LINE'
            WHEN NOT in_catalogue THEN 'ITEM_NOT_IN_CATALOGUE' END AS reason
FROM {{ ref('slv_sales_line_netted') }}
WHERE NOT (net_qty > 0 AND net_gmv > 0 AND COALESCE(item_type, '') <> 'service' AND txn_status = 'SALE' AND in_catalogue)
