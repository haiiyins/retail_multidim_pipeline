### Sales lines from Bronze to Silver: exact duplicates, line keys, netting and what is kept

| country code | raw rows | distinct rows | line keys | sale rows | cancel rows | return rows | sale lines kept | sale transactions | buying members | return lines kept | quarantined rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| VN | 11,599,372 | 10,607,241 | 10,604,977 | 11,196,431 | 115,011 | 287,930 | 8,311,828 | 3,806,147 | 1,019,754 | 262,476 | 1,133,757 |

*Source:* `staging.stg_sales_detail`, `silver.slv_fact_sales_line`, `silver.slv_fact_returns`, `quarantine.qrt_sales_line` (dedup and netting rules in `slv_sales_line_netted.sql`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
