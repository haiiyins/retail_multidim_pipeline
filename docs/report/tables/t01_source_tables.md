### The eleven source tables: raw format, contract key, Bronze partitioning and loaded volume

| table | raw format | contract key | country column | bronze partition | rows loaded | parquet MB | load sec |
|---|---|---|---|---|---:|---:|---:|
| sales_detail | parquet | transaction_id, transaction_num_line | economical_businessunit_country_code | economical_businessunit_country_code, year, month | 11,599,372 | 1,058.2 | 68.4 |
| sales_tender_detail | parquet | transaction_id, tender_num_line | via sales_detail | year, month | 4,256,418 | 134.3 | 1.8 |
| f_member_purchase | parquet | transaction_id, member_id | member_country_code | member_country_code, tech_year, tech_month | 7,996,811 | 113.2 | 1.9 |
| d_member | csv | member_id | member_country_code | member_country_code | 953,877 | 41.5 | 2.3 |
| dim_item | parquet | item_code | - | - | 4,364,106 | 474.5 | 2.7 |
| dim_business_unit | csv | business_unit_gln | - | - | 275 | 0 | 0.1 |
| dim_calendar | csv | date_of_day | - | - | 1,461 | 0.1 | 0.1 |
| all_store_selling_price | parquet | item_code, business_unit_gln_code, price_start_date, price_type | country_code | country_code, tech_ingestion_year | 11,273,268 | 184.3 | 1.9 |
| stock_availability_rate | csv | site_gln, item_code, snapshot_date, availability_type | country_code | country_code, year, month | 4,238,621 | 9.1 | 3.4 |
| f_member_favorite_sport | csv | member_id, sport_id, event_datetime_utc | country_code | country_code, year | 27,300 | 0.4 | 0.4 |
| tracking_ecom_events | parquet-dir | id | country_code | country_code, year, month | 464,150 | 51 | 3.5 |

*Source:* `ingestion/table_contracts.yml`, `ingestion/raw_source.py`, `audit.pipeline_run_metrics` (layer bronze, latest load per table). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`. Raw formats and full-file row counts per country are in `data/audit/csv_fullscan.md`.
