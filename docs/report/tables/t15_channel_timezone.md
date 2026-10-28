### Sale lines by channel and the timezone fallback (website units carry no timezone; the country's is used)

| country code | channel | sale lines | business units | lines without unit timezone | pct country timezone fallback |
|---|---|---:|---:|---:|---:|
| VN | offline | 6,752,199 | 10 | 0 | 0 |
| VN | online | 1,559,629 | 16 | 95,222 | 6.11 |

*Source:* `silver.slv_fact_sales_line` (`transaction_ts_utc` derivation). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
