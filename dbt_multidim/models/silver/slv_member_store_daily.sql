-- Input for usual_store at anchor t (computed in Gold): offline purchase lines per (member, store, day)
SELECT member_id, store_id, transaction_date, COUNT(*) AS n_lines
FROM {{ ref('slv_fact_sales_line') }}
WHERE member_id IS NOT NULL AND channel = 'offline'
GROUP BY 1, 2, 3
