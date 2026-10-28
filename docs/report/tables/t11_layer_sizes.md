### Silver, quarantine, Gold and audit tables: rows and on-disk size

| layer | table | rows | size MB |
|---|---|---:|---:|
| audit | candidate_recall | 18 | 0.3 |
| audit | date_span | 3 | 0.3 |
| audit | gates_by_country | 12 | 0.3 |
| audit | interpurchase_days | 3 | 0.3 |
| audit | pipeline_run_metrics | 62 | 0.3 |
| audit | price_uniformity | 3 | 0.3 |
| audit | stitching_coverage | 9 | 0.3 |
| audit | stock_coverage | 3 | 0.3 |
| ext | commercial_event_names | 16 | 0.3 |
| ext | public_holidays | 217 | 0.3 |
| gold | anchor_grid | 221,197,451 | 5,917.1 |
| gold | anchor_model_grid | 4,290,922 | 17.3 |
| gold | gld_candidates | 69,000,000 | 1,123.3 |
| gold | gld_copurchase_lift | 6,739,916 | 131.1 |
| gold | gld_fs_member | 345,000 | 26.5 |
| gold | gld_fs_model_country | 4,290,922 | 131.1 |
| gold | gld_fs_pair | 69,000,000 | 10,686.0 |
| gold | gld_ranking_dataset | 69,000,000 | 10,723.8 |
| gold | gld_sport_department_affinity | 838 | 0.3 |
| gold | gld_web_stitched | 790,097,508 | 33,171.7 |
| gold | split_windows | 1 | 0 |
| quarantine | leakage_violations | 0 | 0 |
| quarantine | qrt_price_interval | 1,118 | 0.3 |
| quarantine | qrt_sales_line | 5,584,701 | 201.3 |
| quarantine | rejects_d_member | 46 | 0.3 |
| quarantine | rejects_dim_item | 19 | 0.3 |
| quarantine | slv_identity_conflicts | 945 | 0.3 |
| silver | slv_calendar_enriched | 4,383 | 0.3 |
| silver | slv_dim_model | 3,121,362 | 134.7 |
| silver | slv_fact_returns | 1,575,457 | 104.9 |
| silver | slv_fact_sales_line | 66,122,312 | 4,876.1 |
| silver | slv_member_bridge | 19,639,945 | 880 |
| silver | slv_member_profile | 5,691,382 | 167.2 |
| silver | slv_member_sport_asof | 667,458 | 24.4 |
| silver | slv_member_store_daily | 15,531,428 | 554.4 |
| silver | slv_price_sku_interval | 1,461,666 | 28 |
| silver | slv_stock_daily_model | 45,733,153 | 313.3 |
| silver | slv_stock_daily_national | 1,949,703 | 22.3 |
| silver | slv_user_to_member | 1,295,225 | 60 |
| silver | slv_web_events_clean | 971,454,050 | 55,974.8 |

*Source:* `duckdb_tables()`, `pragma_storage_info()` (distinct storage blocks × block size). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
