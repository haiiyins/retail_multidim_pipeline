### dbt models and tests per layer (generic + singular), from the compiled manifest

| layer | models | tests | singular tests |
|---|---:|---:|---:|
| source | 13 | 48 | 1 |
| staging | 2 | 0 | 0 |
| silver | 15 | 58 | 3 |
| quarantine | 4 | 13 | 1 |
| audit | 2 | 4 | 0 |
| gold | 8 | 59 | 8 |

*Source:* `dbt_multidim/target/manifest.json` (`dbt parse`). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. Leakage ledger `quarantine.leakage_violations`: 0 rows.
