### Audit checks: stock-table coverage, in-country price uniformity, inter-purchase gaps, date span

| country | sold items | in spare parts table | spare parts coverage | store vs national pairs | mean rel gap | p95 rel gap | interpurchase q25 q50 q75 q90 days | n gaps | first sale | last sale |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|---|
| VN | 31,035 | 517 | 0.017 | 35,881,236 | 0 | 0 | 19 / 70 / 196 / 397 | 1,523,746 | 2023-01-01 00:09 | 2026-10-26 17:29 |

*Source:* `audit.stock_coverage`, `audit.price_uniformity`, `audit.interpurchase_days`, `audit.date_span` (`sql/audit_checks.sql`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`. The exported stock table covers spare parts only (data owner, issue #21), hence the low coverage.
