### The eleven source tables: raw format, contract key, Bronze partitioning and loaded volume

| table | raw format | contract key | country column | bronze partition | rows loaded | parquet MB | load sec |
|---|---|---|---|---|---:|---:|---:|
| sales_detail | parquet | transaction_id, transaction_num_line | economical_businessunit_country_code | economical_businessunit_country_code, year, month | 89,321,540 | 8,141.4 | 1,319.7 |
| sales_tender_detail | parquet | transaction_id, tender_num_line | via sales_detail | year, month | 29,740,415 | 943.4 | 10.2 |
| f_member_purchase | parquet | transaction_id, member_id | member_country_code | member_country_code, tech_year, tech_month | 63,047,610 | 835.9 | 23.2 |
| d_member | csv | member_id | member_country_code | member_country_code | 5,691,382 | 245 | 10.5 |
| dim_item | parquet | item_code | - | - | 4,364,106 | 474.4 | 5.1 |
| dim_business_unit | csv | business_unit_gln | - | - | 275 | 0 | 0.1 |
| dim_calendar | csv | date_of_day | - | - | 1,461 | 0.1 | 0.2 |
| all_store_selling_price | parquet | item_code, business_unit_gln_code, price_start_date, price_type | country_code | country_code, tech_ingestion_year | 42,416,758 | 718.5 | 30.1 |
| stock_availability_rate | csv | site_gln, item_code, snapshot_date, availability_type | country_code | country_code, year, month | 36,701,681 | 83.1 | 21.7 |
| f_member_favorite_sport | csv | member_id, sport_id, event_datetime_utc | country_code | country_code, year | 796,143 | 11.1 | 1.5 |
| tracking_ecom_events | - | id | country_code | country_code, year, month | 999,710,429 | 115,620.9 | 5,220.9 |

*Source:* `ingestion/table_contracts.yml`, `ingestion/raw_source.py`, `audit.pipeline_run_metrics` (layer bronze, latest load per table). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. Raw formats and full-file row counts per country are in `data/audit/csv_fullscan.md`.
