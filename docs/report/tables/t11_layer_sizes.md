### Silver, quarantine, Gold and audit tables: rows and on-disk size

| layer | table | rows | size MB |
|---|---|---:|---:|
| audit | ablation_runs | 18 | 0.3 |
| audit | candidate_recall | 6 | 0.3 |
| audit | date_span | 1 | 0.3 |
| audit | gates_by_country | 4 | 0.3 |
| audit | interpurchase_days | 1 | 0.3 |
| audit | model_cost | 3 | 0.3 |
| audit | pipeline_run_metrics | 231 | 0.3 |
| audit | price_uniformity | 1 | 0.3 |
| audit | scale_test | 1 | 0.3 |
| audit | stitching_coverage | 3 | 0.3 |
| audit | stock_coverage | 1 | 0.3 |
| audit | technique_comparisons | 9 | 0.3 |
| ext | commercial_event_names | 16 | 0.3 |
| ext | public_holidays | 217 | 0.3 |
| gold | anchor_grid | 32,997,595 | 907.5 |
| gold | anchor_model_grid | 1,231,570 | 3.9 |
| gold | gld_candidates | 23,000,000 | 367 |
| gold | gld_copurchase_lift | 585,574 | 12.8 |
| gold | gld_fs_member | 115,000 | 8.1 |
| gold | gld_fs_model_country | 1,231,570 | 38.5 |
| gold | gld_fs_pair | 23,000,000 | 2,142.8 |
| gold | gld_ranking_dataset | 23,000,000 | 2,123.4 |
| gold | gld_sport_department_affinity | 85 | 0.3 |
| gold | gld_web_stitched | 625,510 | 19.1 |
| gold | split_windows | 1 | 0 |
| quarantine | leakage_violations | 0 | 0 |
| quarantine | qrt_price_interval | 312 | 0.3 |
| quarantine | qrt_sales_line | 1,133,757 | 34.3 |
| quarantine | rejects_d_member | 46 | 0.3 |
| quarantine | rejects_dim_item | 19 | 0.3 |
| quarantine | rejects_tracking_ecom_events | 1 | 0.3 |
| quarantine | slv_identity_conflicts | 8 | 0.3 |
| silver | slv_calendar_enriched | 1,461 | 0.3 |
| silver | slv_dim_model | 3,121,362 | 135 |
| silver | slv_fact_returns | 262,476 | 15.7 |
| silver | slv_fact_sales_line | 8,311,828 | 594.8 |
| silver | slv_member_bridge | 2,744,652 | 121.1 |
| silver | slv_member_profile | 953,877 | 28.6 |
| silver | slv_member_sport_asof | 21,901 | 0.8 |
| silver | slv_member_store_daily | 2,140,574 | 66.8 |
| silver | slv_price_sku_interval | 535,805 | 9.7 |
| silver | slv_stock_daily_model | 3,994,703 | 18.1 |
| silver | slv_stock_daily_national | 329,245 | 3.1 |
| silver | slv_user_to_member | 2,644 | 0.3 |
| silver | slv_web_events_clean | 464,150 | 25.4 |

*Source:* `duckdb_tables()`, `pragma_storage_info()` (distinct storage blocks × block size). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
