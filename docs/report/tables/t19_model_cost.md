### Cost per dbt model rebuilt alone: wall time, peak RSS, output rows and bytes (latest profile per model)

| layer | model name | country filter | wall sec | peak rss GB | output rows | output MB |
|---|---|---|---:|---:|---:|---:|
| gold | gld_fs_member | VN | 5.1 | 1.92 | 115,000 | 8.1 |
| gold | gld_sport_department_affinity | VN | 5.7 | 0.31 | 0 | 0 |
| silver | slv_member_bridge | VN | 7.3 | 1.39 | 2,744,652 | 2.7 |

*Source:* `audit.model_cost` (`evaluation/pipeline_cost_profiler.py`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
