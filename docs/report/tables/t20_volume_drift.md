### QC-5 volume drift per table × country: days, flagged days (|drift| > 50 % vs the same-weekday 28-day mean) and probable causes

| table name | country code | days | days without rows | flagged days | flagged drops | holiday related | unexplained | first day | last day |
|---|---|---:|---:|---:|---:|---:|---:|---|---|
| sales_detail | VN | 1,395 | 0 | 69 | 15 | 31 | 14 | 2023-01-01 | 2026-10-26 |
| tracking_ecom_events | VN | 1 | 0 | 0 | 0 | 0 | 0 | 2025-06-06 | 2025-06-06 |

*Source:* `audit.volume_drift` (`sql/audit_checks.sql` 4e, `make gates`). *Generated:* 2026-10-28 11:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
