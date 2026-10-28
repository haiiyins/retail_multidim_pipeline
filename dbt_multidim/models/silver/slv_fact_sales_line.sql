-- Core fact: one net SALE line per (transaction, item). Dedup and netting live in slv_sales_line_netted (ephemeral); this model
-- keeps physical items known to the catalogue, in SALE transactions, with net quantity and net gmv > 0 (QC-3). Every row that
-- fails one of these conditions is written to quarantine.qrt_sales_line with a reason (issue #24), nothing is dropped silently.
SELECT n.transaction_id, n.item_code, dm.model_code, dm.supermodel_code, dm.sport_department_code, dm.retail_department_code,
       mb.member_id, n.country_code, n.store_id, bu.business_unit_name AS store_name, bu.timezone AS store_tz, n.channel,
       n.gmv_recorded_at AS transaction_ts_local,
       -- UTC as a naive TIMESTAMP, independent of the session time zone: interpret the local wall clock in the store's zone, else in
       -- the country's zone (mode of its business units; a store missing from dim_business_unit must not be read as UTC: that shifted
       -- 95 k VN lines by +7 h and tripped the Gold leakage test), then express the instant in UTC
       timezone('UTC', timezone(COALESCE(bu.timezone, ctz.timezone, 'UTC'), n.gmv_recorded_at)) AS transaction_ts_utc,
       CAST(n.gmv_recorded_at AS DATE) AS transaction_date,
       n.net_qty AS qty, n.net_gmv AS gmv_local, n.net_gmv * n.fx_eur AS gmv_eur,
       n.rsp_local, n.rsp_local * n.fx_eur AS rsp_eur, n.discount_local,
       (n.discount_local IS NOT NULL AND n.discount_local > 0) AS bought_with_discount,
       n.txn_status, n.year, n.month
FROM {{ ref('slv_sales_line_netted') }} n
LEFT JOIN {{ ref('slv_member_bridge') }} mb USING (transaction_id)
INNER JOIN {{ ref('slv_dim_model') }} dm USING (item_code)
LEFT JOIN {{ source('bronze', 'dim_business_unit') }} bu ON n.store_id = CAST(bu.business_unit_third_id AS VARCHAR)
LEFT JOIN (SELECT country_code, MODE(timezone) AS timezone FROM {{ source('bronze', 'dim_business_unit') }} WHERE timezone IS NOT NULL GROUP BY 1) ctz
       ON ctz.country_code = n.country_code
WHERE n.net_qty > 0 AND n.net_gmv > 0 AND COALESCE(n.item_type, '') <> 'service' AND n.txn_status = 'SALE'
