# Report tables

Generated 2026-10-28 11:13 UTC by `tools/report_tables.py` (`make report-tables`) with `COUNTRY_FILTER=VN`. Each file carries its source; the CSV next to it holds the same rows. Regenerate on the server after `make gold` so that the three-country numbers replace the laptop (VN) ones.

- [QC-5 volume drift per table × country: days, flagged days (|drift| > 50 % vs the same-weekday 28-day mean) and probable causes](t20_volume_drift.md) — `audit.volume_drift` (`sql/audit_checks.sql` 4e, `make gates`)
- [QC-5 flagged days other than public holidays (to review)](t20b_volume_drift_days.md) — `audit.volume_drift`
