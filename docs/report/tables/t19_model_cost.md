### Cost per dbt model rebuilt alone: wall time, peak RSS, output rows and bytes (latest profile per model)

| layer | model name | country filter | wall sec | peak rss GB | output rows | output MB |
|---|---|---|---:|---:|---:|---:|
| gold | gld_candidates | ALL | 83.7 | 60.52 | 69,000,000 | 1,125.1 |
| gold | gld_copurchase_lift | ALL | 19.5 | 14.76 | 6,739,918 | 130.8 |
| gold | gld_fs_member | ALL | 68.1 | 33 | 345,000 | 26.5 |
| gold | gld_fs_model_country | ALL | 108.7 | 28.04 | 4,290,922 | 130 |
| gold | gld_fs_pair | ALL | 1,848.6 | 81.88 | 69,000,000 | 10,690.8 |
| gold | gld_ranking_dataset | ALL | 101.4 | 76.26 | 69,000,000 | 10,724.8 |
| gold | gld_web_stitched | ALL | 567.9 | 82.08 | 790,097,508 | 33,201.3 |
| silver | slv_calendar_enriched | ALL | 3.7 | 0.25 | 4,383 | 0.3 |
| silver | slv_dim_model | ALL | 6.9 | 1.87 | 3,121,362 | 130.5 |
| silver | slv_fact_returns | ALL | 10.4 | 6.31 | 1,575,457 | 105.4 |
| silver | slv_fact_sales_line | ALL | 103.9 | 65.84 | 66,122,312 | 4,872.2 |
| silver | slv_member_bridge | ALL | 17.9 | 5.8 | 19,639,945 | 881.1 |
| silver | slv_member_sport_asof | ALL | 4.2 | 0.6 | 667,458 | 24.1 |
| silver | slv_member_store_daily | ALL | 26 | 17.85 | 15,531,428 | 554.4 |
| silver | slv_price_sku_interval | ALL | 5.9 | 1.85 | 1,461,666 | 25.7 |
| silver | slv_stock_daily_model | ALL | 17.3 | 14.39 | 45,733,153 | 314 |
| silver | slv_user_to_member | ALL | 72.1 | 33.59 | 1,295,225 | 59.8 |
| silver | slv_web_events_clean | ALL | 614.3 | 63.5 | 971,454,050 | 56,009.2 |

*Source:* `audit.model_cost` (`evaluation/pipeline_cost_profiler.py`). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
