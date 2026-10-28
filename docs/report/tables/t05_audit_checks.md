### Audit checks: stock-table coverage, in-country price uniformity, inter-purchase gaps, date span

| country | sold items | in spare parts table | spare parts coverage | store vs national pairs | mean rel gap | p95 rel gap | interpurchase q25 q50 q75 q90 days | n gaps | first sale | last sale |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| SG | 42,236 | 709 | 0.017 | 49,800,587 | 0 | 0 | 14 / 47 / 126 / 267 | 6,293,283 | 2023-01-01 01:36 | 2026-10-26 18:29 |
| TH | 33,980 | 664 | 0.02 | 93,177,588 | 0.0001 | 0 | 17 / 62 / 171 / 357 | 5,307,269 | 2023-01-01 00:29 | 2026-10-26 17:29 |
| VN | 31,035 | 517 | 0.017 | 35,881,236 | 0 | 0 | 19 / 69 / 195 / 395 | 1,554,513 | 2023-01-01 00:09 | 2026-10-26 17:29 |

*Source:* `audit.stock_coverage`, `audit.price_uniformity`, `audit.interpurchase_days`, `audit.date_span` (`sql/audit_checks.sql`). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. The exported stock table covers spare parts only (data owner, issue #21), hence the low coverage.
