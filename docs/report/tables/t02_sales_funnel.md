### Sales lines from Bronze to Silver: exact duplicates, line keys, netting and what is kept

| country code | raw rows | distinct rows | line keys | sale rows | cancel rows | return rows | sale lines kept | sale transactions | buying members | return lines kept | quarantined rows |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| SG | 46,292,657 | 41,642,599 | 41,622,617 | 45,010,018 | 186,757 | 1,095,882 | 33,838,361 | 13,572,821 | 1,355,235 | 972,530 | 2,857,657 |
| TH | 31,429,511 | 28,596,100 | 28,592,072 | 30,942,171 | 105,973 | 381,367 | 23,972,123 | 8,894,370 | 2,303,028 | 340,451 | 1,593,287 |
| VN | 11,599,372 | 10,607,241 | 10,604,977 | 11,196,431 | 115,011 | 287,930 | 8,311,828 | 3,806,147 | 1,049,572 | 262,476 | 1,133,757 |

*Source:* `staging.stg_sales_detail`, `silver.slv_fact_sales_line`, `silver.slv_fact_returns`, `quarantine.qrt_sales_line` (dedup and netting rules in `slv_sales_line_netted.sql`). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
