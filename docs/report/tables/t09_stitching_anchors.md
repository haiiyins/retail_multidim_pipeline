### Identity stitching at anchor level: used anchors whose member has an attributed web event in the 30 days before, known at the anchor

| country code | split | used anchors | anchors with web signal | pct with web signal | anchors with web data available |
|---|---|---:|---:|---:|---:|
| SG | test | 50,000 | 9,381 | 18.76 | 50,000 |
| SG | train | 50,000 | 2,540 | 5.08 | 50,000 |
| SG | valid | 15,000 | 2,909 | 19.39 | 15,000 |
| TH | test | 50,000 | 2,761 | 5.52 | 50,000 |
| TH | train | 50,000 | 896 | 1.79 | 48,989 |
| TH | valid | 15,000 | 796 | 5.31 | 15,000 |
| VN | test | 50,000 | 3,650 | 7.3 | 50,000 |
| VN | train | 50,000 | 1,804 | 3.61 | 33,050 |
| VN | valid | 15,000 | 1,218 | 8.12 | 15,000 |

*Source:* `gold.anchor_grid`, `gold.gld_web_stitched`, `gold.gld_fs_member.web_data_available` (RUNBOOK §5 query). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
