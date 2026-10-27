SELECT transaction_id, transaction_num_line, customer_purchase_order_id, CAST(transaction_version_at AS TIMESTAMP) AS transaction_version_at, transaction_status,
       item_operation_type, item_type, item_code, model_code,
       economical_businessunit_country_code AS country_code,
       CAST(economical_businessunit_id AS VARCHAR) AS store_id,
       transaction_channel_type AS channel, customer_identification_type,
       CAST(gmv_recorded_at AS TIMESTAMP) AS gmv_recorded_at,
       gmv_item_quantity, gmv_amount, gmv_amount_euros, regular_selling_price, discount_amount,
       exchange_rate_local_to_euros AS fx_eur, transaction_link_detail, return_reason_code, return_reason_type, year, month
FROM {{ source('bronze', 'sales_detail') }}
WHERE {{ country_where('economical_businessunit_country_code') }}
