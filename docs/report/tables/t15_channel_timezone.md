### Sale lines by channel and the timezone fallback (website units carry no timezone; the country's is used)

| country code | channel | sale lines | business units | lines without unit timezone | pct country timezone fallback |
|---|---|---:|---:|---:|---:|
| SG | offline | 31,009,965 | 25 | 0 | 0 |
| SG | online | 2,828,396 | 26 | 853,606 | 30.18 |
| TH | offline | 22,149,541 | 34 | 0 | 0 |
| TH | online | 1,822,582 | 36 | 963,131 | 52.84 |
| VN | offline | 6,752,199 | 10 | 0 | 0 |
| VN | online | 1,559,629 | 16 | 95,226 | 6.11 |

*Source:* `silver.slv_fact_sales_line` (`transaction_ts_utc` derivation). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
