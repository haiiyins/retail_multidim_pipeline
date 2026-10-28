### Quarantined sales rows by reason (QC-3 / QC-4 routing)

| country code | reason | netted rows | pct of quarantine |
|---|---|---:|---:|
| SG | NON_MERCHANDISE | 1,123,249 | 39.31 |
| SG | NET_GMV_NONPOSITIVE | 966,612 | 33.83 |
| SG | TXN_NOT_SALE | 459,770 | 16.09 |
| SG | SERVICE_LINE | 284,137 | 9.94 |
| SG | ITEM_NOT_IN_CATALOGUE | 23,886 | 0.84 |
| SG | NET_QTY_NONPOSITIVE | 3 | 0 |
| TH | NET_GMV_NONPOSITIVE | 712,842 | 44.74 |
| TH | NON_MERCHANDISE | 482,438 | 30.28 |
| TH | SERVICE_LINE | 256,942 | 16.13 |
| TH | TXN_NOT_SALE | 137,743 | 8.65 |
| TH | ITEM_NOT_IN_CATALOGUE | 3,320 | 0.21 |
| TH | NET_QTY_NONPOSITIVE | 2 | 0 |
| VN | NON_MERCHANDISE | 517,802 | 45.67 |
| VN | NET_GMV_NONPOSITIVE | 312,747 | 27.59 |
| VN | TXN_NOT_SALE | 156,895 | 13.84 |
| VN | SERVICE_LINE | 145,735 | 12.85 |
| VN | ITEM_NOT_IN_CATALOGUE | 557 | 0.05 |
| VN | NET_QTY_NONPOSITIVE | 21 | 0 |

*Source:* `quarantine.qrt_sales_line` (`models/quarantine/qrt_sales_line.sql`). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
