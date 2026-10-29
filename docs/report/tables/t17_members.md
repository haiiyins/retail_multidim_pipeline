### Members: profiles, excluded accounts, favourite-sport and usual-store state

| country code | member profiles | excluded accounts | transactions with member | members with sport | sports | members with store state |
|---|---:|---:|---:|---:|---:|---:|
| SG | 745,010 | 17 | 7,865,777 | 2,240 | 350 | 496,026 |
| TH | 1,600,414 | 1,075 | 8,145,811 | 1,888 | 361 | 1,401,604 |
| VN | 953,877 | 12 | 2,649,363 | 1,169 | 224 | 722,885 |

*Source:* `silver.slv_member_profile`, `silver.slv_member_bridge`, `silver.slv_member_sport_asof`, `silver.slv_member_store_daily`. *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. Profiles, sport and store state are counted by the member's account-creation country; transactions with a member by transaction country. `d_member` also holds 2,392,081 accounts registered in PH, TW, outside the evaluation scope (issue #54).
