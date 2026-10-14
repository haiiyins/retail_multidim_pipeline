-- QC-2: member link rate per country must be ≥ 60% (warning so REVIEW countries are not blocked)
{{ config(severity='warn') }}
SELECT country_code, AVG(CASE WHEN member_id IS NOT NULL THEN 1.0 ELSE 0 END) AS link_rate
FROM {{ ref('slv_fact_sales_line') }} GROUP BY 1 HAVING link_rate < 0.60
