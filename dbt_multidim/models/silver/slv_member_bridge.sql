-- Transaction → member bridge, deduplicated: one member per transaction (earliest association)
SELECT transaction_id, member_id, MIN(CAST(association_datetime_utc AS TIMESTAMP)) AS associated_at
FROM {{ source('bronze', 'f_member_purchase') }}
WHERE member_id IS NOT NULL
GROUP BY 1, 2
QUALIFY ROW_NUMBER() OVER (PARTITION BY transaction_id ORDER BY associated_at) = 1
