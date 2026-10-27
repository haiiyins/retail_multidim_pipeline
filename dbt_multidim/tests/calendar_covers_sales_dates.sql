-- Referential: every (country, transaction_date) of the sales fact exists in the enriched calendar (Gold joins on it)
SELECT s.country_code, s.transaction_date
FROM (SELECT DISTINCT country_code, transaction_date FROM {{ ref('slv_fact_sales_line') }}) s
LEFT JOIN {{ ref('slv_calendar_enriched') }} c ON c.country_code = s.country_code AND c.calendar_date = s.transaction_date
WHERE c.calendar_date IS NULL
