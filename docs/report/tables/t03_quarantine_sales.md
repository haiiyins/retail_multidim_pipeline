### Quarantined sales rows by reason (QC-3 / QC-4 routing)

| country code | reason | netted rows | pct of quarantine |
|---|---|---:|---:|
| VN | NON_MERCHANDISE | 517,802 | 45.67 |
| VN | NET_GMV_NONPOSITIVE | 312,747 | 27.59 |
| VN | TXN_NOT_SALE | 156,895 | 13.84 |
| VN | SERVICE_LINE | 145,735 | 12.85 |
| VN | ITEM_NOT_IN_CATALOGUE | 557 | 0.05 |
| VN | NET_QTY_NONPOSITIVE | 21 | 0 |

*Source:* `quarantine.qrt_sales_line` (`models/quarantine/qrt_sales_line.sql`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
