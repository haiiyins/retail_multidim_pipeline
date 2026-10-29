### Sale − cancel netting check: transactions with both line kinds, and how many survive with positive net quantity

| country code | transactions with sale and cancel | kept with positive net lines | kept lines with nonpositive qty or gmv |
|---|---:|---:|---:|
| SG | 69,699 | 13,547 | 0 |
| TH | 35,861 | 1,449 | 0 |
| VN | 41,581 | 4,529 | 0 |

*Source:* `staging.stg_sales_detail`, `silver.slv_fact_sales_line` (RUNBOOK §5 manual check, automated). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
