### Silver, quarantine, Gold and audit tables: rows and on-disk size

| layer | table | rows | size MB |
|---|---|---:|---:|
| audit | ablation_runs | 22 | 0.3 |
| audit | candidate_recall | 18 | 0.3 |
| audit | date_span | 3 | 0.3 |
| audit | gates_by_country | 12 | 0.3 |
| audit | interpurchase_days | 3 | 0.3 |
| audit | model_cost | 18 | 0.3 |
| audit | pipeline_run_metrics | 302 | 0.3 |
| audit | price_uniformity | 3 | 0.3 |
| audit | scale_test | 6 | 0.3 |
| audit | stitching_coverage | 9 | 0.3 |
| audit | stock_coverage | 3 | 0.3 |
| audit | volume_drift | 7,770 | 0.3 |
| ext | commercial_event_names | 32 | 0.3 |
| ext | public_holidays | 217 | 0.3 |
| gold | anchor_grid | 221,197,706 | 5,919.2 |
| gold | anchor_model_grid | 4,290,920 | 17 |
| gold | gld_candidates | 69,000,000 | 1,124.3 |
| gold | gld_copurchase_lift | 6,739,920 | 129.5 |
| gold | gld_fs_member | 345,000 | 26.5 |
| gold | gld_fs_model_country | 4,290,920 | 129.8 |
| gold | gld_fs_pair | 69,000,000 | 10,686.8 |
| gold | gld_ranking_dataset | 69,000,000 | 10,724.6 |
| gold | gld_sport_department_affinity | 838 | 0.3 |
| gold | gld_web_stitched | 790,097,508 | 33,233.6 |
| gold | split_windows | 1 | 0 |
| quarantine | leakage_violations | 0 | 0 |
| quarantine | qrt_price_interval | 1,118 | 0.3 |
| quarantine | qrt_sales_line | 5,584,701 | 197.7 |
| quarantine | rejects_d_member | 46 | 0.3 |
| quarantine | rejects_dim_item | 19 | 0.3 |
| quarantine | slv_identity_conflicts | 945 | 0.3 |
| silver | slv_calendar_enriched | 4,383 | 0.3 |
| silver | slv_dim_model | 3,121,362 | 130.5 |
| silver | slv_fact_returns | 1,575,457 | 109.6 |
| silver | slv_fact_sales_line | 66,122,312 | 4,869.1 |
| silver | slv_member_bridge | 19,639,945 | 881.3 |
| silver | slv_member_profile | 5,691,382 | 166.5 |
| silver | slv_member_sport_asof | 667,458 | 24.4 |
| silver | slv_member_store_daily | 15,531,428 | 552.3 |
| silver | slv_price_sku_interval | 1,461,666 | 26.5 |
| silver | slv_stock_daily_model | 45,733,153 | 316.7 |
| silver | slv_stock_daily_national | 1,949,703 | 17.3 |
| silver | slv_user_to_member | 1,295,225 | 60.8 |
| silver | slv_web_events_clean | 971,454,050 | 56,001.0 |

*Source:* `duckdb_tables()`, `pragma_storage_info()` (distinct storage blocks × block size). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
