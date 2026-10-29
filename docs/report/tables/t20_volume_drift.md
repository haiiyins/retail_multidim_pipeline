### QC-5 volume drift per table × country: days, flagged days (|drift| > 50 % vs the same-weekday 28-day mean) and probable causes

| table name | country code | days | days without rows | flagged days | flagged drops | holiday related | unexplained | first day | last day |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| sales_detail | SG | 1,395 | 0 | 48 | 8 | 26 | 17 | 2023-01-01 | 2026-10-26 |
| sales_detail | TH | 1,395 | 0 | 51 | 6 | 29 | 11 | 2023-01-01 | 2026-10-26 |
| sales_detail | VN | 1,395 | 0 | 69 | 15 | 31 | 14 | 2023-01-01 | 2026-10-26 |
| tracking_ecom_events | SG | 1,394 | 86 | 181 | 116 | 7 | 77 | 2023-01-01 | 2026-10-25 |
| tracking_ecom_events | TH | 1,279 | 29 | 166 | 100 | 22 | 69 | 2023-04-26 | 2026-10-25 |
| tracking_ecom_events | VN | 912 | 0 | 76 | 15 | 11 | 19 | 2024-04-27 | 2026-10-25 |

*Source:* `audit.volume_drift` (`sql/audit_checks.sql` 4e, `make gates`). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
