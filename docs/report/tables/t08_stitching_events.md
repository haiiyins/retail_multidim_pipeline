### Identity stitching at event level: share of web events with a member before (DIRECT) and after (+ STITCHED)

| country code | events | event days | first event | last event | users | direct pct | stitched pct | anonymous pct | identified after pct | cookie member links | conflicting cookies |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| SG | 525,240,501 | 1,250 | 2023-01-01 | 2026-10-25 | 19,604,567 | 36.14 | 5.83 | 58.04 | 41.97 | 1,295,225 | 945 |
| TH | 273,988,098 | 1,215 | 2023-04-26 | 2026-10-25 | 12,525,483 | 33.65 | 6.33 | 60.01 | 39.98 | 1,295,225 | 945 |
| VN | 172,225,451 | 847 | 2024-07-01 | 2026-10-25 | 8,178,645 | 29.94 | 7.62 | 62.44 | 37.56 | 1,295,225 | 945 |

*Source:* `audit.stitching_coverage` (`models/audit/stitching_coverage.sql`), `silver.slv_web_events_clean`, `silver.slv_user_to_member`, `quarantine.slv_identity_conflicts`. *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
