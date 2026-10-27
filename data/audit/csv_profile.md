# CSV profile (first 20,000 rows per table)


## all_store_selling_price  (30 columns, parquet)

| column | type | % null |
|---|---|---|
| item_code | BIGINT | 0.0 |
| business_unit_gln_code | BIGINT | 0.0 |
| business_unit_code | VARCHAR | 0.0 |
| business_unit_third_type | INTEGER | 0.0 |
| business_unit_number | INTEGER | 0.0 |
| business_unit_sub_number | INTEGER | 0.0 |
| country_code | VARCHAR | 0.0 |
| business_unit_country | VARCHAR | 0.0 |
| currency_code | VARCHAR | 0.0 |
| timeline_type | VARCHAR | 0.0 |
| price_start_date | TIMESTAMP | 0.0 |
| price_end_date | TIMESTAMP | 0.0 |
| price_type | VARCHAR | 0.0 |
| value_with_taxes | DOUBLE | 0.0 |
| value_without_taxes | DOUBLE | 0.1 |
| reference_value_with_taxes | DOUBLE | 74.5 |
| reference_value_without_taxes | DOUBLE | 74.5 |
| margin | DOUBLE | 0.2 |
| wapp_margin | DOUBLE | 100.0 |
| vat | DOUBLE | 0.1 |
| ecotax | DOUBLE | 100.0 |
| furniture | DOUBLE | 100.0 |
| sale_at_loss | DOUBLE | 0.1 |
| user_id | VARCHAR | 3.8 |
| tech_added_row | INTEGER | 0.0 |
| tech_ingestion_date | TIMESTAMP | 0.0 |
| tech_ingestion_year | VARCHAR | 0.0 |
| tech_ingestion_month | VARCHAR | 0.0 |
| tech_ingestion_day | VARCHAR | 0.0 |
| source_send_date | TIMESTAMP | 0.0 |

**price_type**: [('STANDARD', 14797), ('END_OF_LINE', 4594), ('DAY_TO_DAY_PROMOTION', 609)]

**country_code**: [('VN', 20000)]

**business_unit_third_type**: [(7, 20000)]

## d_member  (32 columns, csv)

| column | type | % null |
|---|---|---|
| member_id | VARCHAR | 0.0 |
| is_email_verified | BOOLEAN | 0.0 |
| gender | VARCHAR | 65.9 |
| loyalty_card_id | BIGINT | 0.0 |
| year_of_birth | BIGINT | 89.7 |
| member_country_code | VARCHAR | 0.0 |
| locale_code | VARCHAR | 0.0 |
| is_phone_verified | BOOLEAN | 0.2 |
| is_legal_entity | BOOLEAN | 0.0 |
| is_teammate | BOOLEAN | 0.0 |
| account_creation_datetime_utc | TIMESTAMP WITH TIME ZONE | 0.0 |
| is_administration | BOOLEAN | 0.0 |
| is_business | BOOLEAN | 0.0 |
| is_organization | BOOLEAN | 0.0 |
| is_sport_club | BOOLEAN | 0.0 |
| is_school | BOOLEAN | 0.0 |
| account_creation_source_client_id | VARCHAR | 0.0 |
| account_creation_source_label | VARCHAR | 13.2 |
| account_creation_channel | VARCHAR | 0.0 |
| last_interaction_date | DATE | 0.0 |
| last_interaction_type | VARCHAR | 0.0 |
| first_purchase_date | DATE | 16.5 |
| last_purchase_date | DATE | 16.5 |
| preferred_store_gln | BIGINT | 0.0 |
| preferred_store_gln_country_code | VARCHAR | 0.0 |
| creation_store_gln | BIGINT | 0.0 |
| creation_store_gln_country_code | VARCHAR | 0.0 |
| usual_store_last_change_datetime_utc | TIMESTAMP WITH TIME ZONE | 24.1 |
| is_contactable_marketing_communication | BOOLEAN | 0.0 |
| is_contactable_review_communication | BOOLEAN | 0.0 |
| is_contactable_abandonned_cart | BOOLEAN | 0.0 |
| tech_integration_datetime_utc | TIMESTAMP WITH TIME ZONE | 0.0 |

**member_country_code**: [('PH', 20000)]

**is_teammate**: [(False, 20000)]

**is_business**: [(False, 20000)]

**is_legal_entity**: [(False, 19999), (True, 1)]

## dim_business_unit  (47 columns, csv)

| column | type | % null |
|---|---|---|
| business_unit_gln | BIGINT | 0.0 |
| business_unit_third_id | VARCHAR | 0.0 |
| business_unit_third_type | BIGINT | 0.0 |
| business_unit_third_number | BIGINT | 0.0 |
| business_unit_third_sub_num | BIGINT | 0.0 |
| business_unit_name | VARCHAR | 0.0 |
| country_gln | BIGINT | 37.1 |
| country_third_id | VARCHAR | 37.1 |
| country_code | VARCHAR | 0.0 |
| country_code_3a | VARCHAR | 0.0 |
| country_name | VARCHAR | 0.0 |
| country_flag_url | VARCHAR | 0.0 |
| geographical_region | VARCHAR | 52.4 |
| geographical_region_code | VARCHAR | 52.4 |
| geographical_zone | VARCHAR | 52.4 |
| retail_region | VARCHAR | 50.2 |
| retail_zone | VARCHAR | 50.2 |
| managerial_region | VARCHAR | 0.0 |
| plant_type | VARCHAR | 0.0 |
| warehouse_type | VARCHAR | 21.1 |
| plant_id | VARCHAR | 21.5 |
| dummy_store_id | VARCHAR | 28.7 |
| sales_org | VARCHAR | 26.2 |
| sales_org_name | VARCHAR | 26.2 |
| customs_zone_gln | BIGINT | 34.5 |
| customs_zone_name | VARCHAR | 34.5 |
| sap_source | VARCHAR | 0.0 |
| distrib_channel | VARCHAR | 25.8 |
| business_unit_opened_date | DATE | 25.8 |
| business_unit_closed_date | DATE | 25.8 |
| is_business_unit_closed | BOOLEAN | 0.0 |
| is_store_franchised | BOOLEAN | 0.0 |
| franchise_start_validity_date | VARCHAR | 100.0 |
| franchise_end_validity_date | VARCHAR | 100.0 |
| postcode | VARCHAR | 5.8 |
| city | VARCHAR | 4.7 |
| address | VARCHAR | 4.4 |
| latitude | DOUBLE | 50.2 |
| longitude | DOUBLE | 50.2 |
| timezone | VARCHAR | 47.3 |
| size_sales_area | BIGINT | 25.8 |
| unit_sales_area | VARCHAR | 31.3 |
| store_sign_id | BIGINT | 54.2 |
| currency_code | VARCHAR | 0.0 |
| technical_business_unit_created_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| created_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| updated_at | TIMESTAMP WITH TIME ZONE | 0.0 |

## dim_calendar  (69 columns, csv)

| column | type | % null |
|---|---|---|
| date_of_day | DATE | 0.0 |
| date_of_day_comp | DATE | 0.0 |
| date_of_day_comp_two_years_ago | DATE | 0.0 |
| date_of_day_comp_next_year | DATE | 0.0 |
| date_of_day_comp_two_years_from | DATE | 0.0 |
| weekday_name | VARCHAR | 0.0 |
| day_of_week | BIGINT | 0.0 |
| day_of_week_comp | BIGINT | 0.0 |
| day_of_week_comp_two_years_ago | BIGINT | 0.0 |
| day_of_week_comp_next_year | BIGINT | 0.0 |
| day_of_week_comp_two_years_from | BIGINT | 0.0 |
| iso_day_of_week | BIGINT | 0.0 |
| iso_day_of_week_comp | BIGINT | 0.0 |
| is_weekend | BOOLEAN | 0.0 |
| first_date_of_week | DATE | 0.0 |
| last_date_of_week | DATE | 0.0 |
| first_date_of_week_comp | DATE | 0.0 |
| last_date_of_week_comp | DATE | 0.0 |
| iso_first_date_of_week | DATE | 0.0 |
| iso_last_date_of_week | DATE | 0.0 |
| iso_first_date_of_week_comp | DATE | 0.0 |
| iso_last_date_of_week_comp | DATE | 0.0 |
| week_WW | VARCHAR | 0.0 |
| week_WW_comp | VARCHAR | 0.0 |
| week_WW_comp_two_years_ago | VARCHAR | 0.0 |
| week_WW_comp_next_year | VARCHAR | 0.0 |
| week_WW_comp_two_years_from | VARCHAR | 0.0 |
| week_YYYYWW | VARCHAR | 0.0 |
| week_YYYYWW_comp | VARCHAR | 0.0 |
| week_YYYYWW_comp_two_years_ago | VARCHAR | 0.0 |
| week_YYYYWW_comp_next_year | VARCHAR | 0.0 |
| week_YYYYWW_comp_two_years_from | VARCHAR | 0.0 |
| iso_week_WW | VARCHAR | 0.0 |
| iso_week_WW_comp | VARCHAR | 0.0 |
| iso_week_YYYYWW | VARCHAR | 0.0 |
| iso_week_YYYYWW_comp | VARCHAR | 0.0 |
| first_date_of_month | DATE | 0.0 |
| last_date_of_month | DATE | 0.0 |
| first_date_of_month_comp | DATE | 0.0 |
| last_date_of_month_comp | DATE | 0.0 |
| month_MM | VARCHAR | 0.0 |
| month_MM_comp | VARCHAR | 0.0 |
| month_YYYYMM | VARCHAR | 0.0 |
| month_YYYYMM_comp | VARCHAR | 0.0 |
| first_date_of_quarter | DATE | 0.0 |
| last_date_of_quarter | DATE | 0.0 |
| first_date_of_quarter_comp | DATE | 0.0 |
| last_date_of_quarter_comp | DATE | 0.0 |
| quarter_QR | VARCHAR | 0.0 |
| quarter_QR_comp | VARCHAR | 0.0 |
| quarter_YYYYQR | VARCHAR | 0.0 |
| quarter_YYYYQR_comp | VARCHAR | 0.0 |
| first_date_of_semester | DATE | 0.0 |
| last_date_of_semester | DATE | 0.0 |
| first_date_of_semester_comp | DATE | 0.0 |
| last_date_of_semester_comp | DATE | 0.0 |
| semester_SR | VARCHAR | 0.0 |
| semester_SR_comp | VARCHAR | 0.0 |
| semester_YYYYSR | VARCHAR | 0.0 |
| semester_YYYYSR_comp | VARCHAR | 0.0 |
| year_YYYY | BIGINT | 0.0 |
| year_YYYY_comp | BIGINT | 0.0 |
| year_YYYY_comp_two_years_ago | BIGINT | 0.0 |
| year_YYYY_comp_next_year | BIGINT | 0.0 |
| year_YYYY_comp_two_years_from | BIGINT | 0.0 |
| iso_year_YYYY | BIGINT | 0.0 |
| iso_year_YYYY_comp | BIGINT | 0.0 |
| created_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| updated_at | TIMESTAMP WITH TIME ZONE | 0.0 |

## dim_item  (77 columns, csv)

| column | type | % null |
|---|---|---|
| item_code | BIGINT | 0.0 |
| model_code | BIGINT | 0.0 |
| model_label | VARCHAR | 0.9 |
| model | VARCHAR | 0.9 |
| supermodel_code | VARCHAR | 0.0 |
| supermodel_label | VARCHAR | 0.7 |
| supermodel | VARCHAR | 0.7 |
| conception_code | VARCHAR | 67.6 |
| item_category_label | VARCHAR | 40.5 |
| gender | VARCHAR | 58.2 |
| item_size | VARCHAR | 30.2 |
| age | VARCHAR | 73.9 |
| product_nature_id | BIGINT | 41.3 |
| product_nature_label | VARCHAR | 41.3 |
| product_nature | VARCHAR | 41.3 |
| product_nature_type | VARCHAR | 42.1 |
| is_ecodesign | BOOLEAN | 94.7 |
| is_repair_maintenance | BOOLEAN | 0.0 |
| is_repairable | BOOLEAN | 20.2 |
| is_first_technical_price | BOOLEAN | 0.0 |
| is_blue_product | BOOLEAN | 13.0 |
| primary_color | VARCHAR | 74.2 |
| secondary_color | VARCHAR | 89.7 |
| pixl_id | BIGINT | 72.8 |
| picture_url | VARCHAR | 72.8 |
| item_business_weight | DOUBLE | 74.9 |
| item_business_weight_unit | VARCHAR | 100.0 |
| sku_ean_num | VARCHAR | 40.0 |
| revamp_sku_id | VARCHAR | 49.2 |
| retail_family_code | BIGINT | 3.2 |
| retail_family_label | VARCHAR | 3.2 |
| retail_family | VARCHAR | 3.2 |
| retail_sub_department_code | BIGINT | 3.2 |
| retail_sub_department_label | VARCHAR | 3.2 |
| retail_sub_department | VARCHAR | 3.2 |
| retail_department_code | BIGINT | 3.2 |
| retail_department_label | VARCHAR | 3.2 |
| retail_department | VARCHAR | 3.2 |
| retail_univers_code | BIGINT | 3.2 |
| retail_univers_label | VARCHAR | 3.2 |
| retail_univers | VARCHAR | 3.2 |
| sport_family_code | BIGINT | 3.2 |
| sport_family_label | VARCHAR | 3.2 |
| sport_family | VARCHAR | 3.2 |
| sport_sub_department_code | BIGINT | 3.2 |
| sport_sub_department_label | VARCHAR | 3.2 |
| sport_sub_department | VARCHAR | 3.2 |
| sport_department_code | BIGINT | 3.2 |
| sport_department_label | VARCHAR | 3.2 |
| sport_department | VARCHAR | 3.2 |
| sport_univers_code | BIGINT | 3.2 |
| sport_univers_label | VARCHAR | 3.2 |
| sport_univers | VARCHAR | 3.2 |
| industrial_process_family_code | BIGINT | 49.6 |
| industrial_process_family_label | VARCHAR | 49.6 |
| industrial_process_family | VARCHAR | 49.6 |
| industrial_process_sub_department_code | BIGINT | 49.6 |
| industrial_process_sub_department_label | VARCHAR | 49.6 |
| industrial_process_sub_department | VARCHAR | 49.6 |
| industrial_process_department_code | BIGINT | 49.6 |
| industrial_process_department_label | VARCHAR | 49.6 |
| industrial_process_department | VARCHAR | 49.6 |
| industrial_process_univers_code | BIGINT | 49.6 |
| industrial_process_univers_label | VARCHAR | 49.6 |
| industrial_process_univers | VARCHAR | 49.6 |
| has_current_hierarchy | BOOLEAN | 1.3 |
| is_currently_available | BOOLEAN | 56.8 |
| product_technicity_level | VARCHAR | 56.8 |
| brand_type | VARCHAR | 8.7 |
| brand_label | VARCHAR | 6.8 |
| evaluation_status | VARCHAR | 56.9 |
| product_impact | DOUBLE | 58.2 |
| tech_source | VARCHAR | 0.0 |
| hierarchy_tech_source | VARCHAR | 1.3 |
| created_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| updated_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| unique_id | VARCHAR | 0.0 |

## f_member_favorite_sport  (9 columns, csv)

| column | type | % null |
|---|---|---|
| event_datetime_utc | TIMESTAMP WITH TIME ZONE | 0.0 |
| member_id | VARCHAR | 0.0 |
| sport_id | BIGINT | 0.0 |
| country_code | VARCHAR | 0.0 |
| event_type | VARCHAR | 0.0 |
| year | BIGINT | 0.0 |
| month | BIGINT | 0.0 |
| day | BIGINT | 0.0 |
| tech_integration_datetime_utc | TIMESTAMP WITH TIME ZONE | 0.0 |

**event_type**: [('create', 19998), ('delete', 2)]

**country_code**: [('TW', 12299), ('TH', 4462), ('SG', 3239)]

## f_member_purchase  (10 columns, parquet)

| column | type | % null |
|---|---|---|
| transaction_id | VARCHAR | 0.0 |
| member_id | VARCHAR | 3.9 |
| association_datetime_utc | TIMESTAMP | 0.0 |
| transaction_source | VARCHAR | 0.0 |
| transaction_operator | VARCHAR | 0.0 |
| member_country_code | VARCHAR | 4.0 |
| tech_year | VARCHAR | 0.0 |
| tech_month | VARCHAR | 0.0 |
| tech_day | VARCHAR | 0.0 |
| tech_topic | VARCHAR | 0.0 |

**member_country_code**: [('TH', 9594), ('VN', 6886), ('SG', 2172), (None, 798), ('FR', 108), ('IN', 76), ('GB', 47), ('MY', 44), ('TW', 35), ('HK', 27), ('DE', 27), ('IT', 21), ('PH', 16), ('IL', 16), ('NL', 15)]

## sales_detail  (141 columns, parquet)

| column | type | % null |
|---|---|---|
| transaction_id | VARCHAR | 0.0 |
| merchant_businessunit_type | VARCHAR | 0.0 |
| merchant_businessunit_country_code | VARCHAR | 0.0 |
| merchant_businessunit_id | VARCHAR | 0.0 |
| merchant_businessunit_gln | VARCHAR | 0.0 |
| customer_purchase_order_id | VARCHAR | 100.0 |
| economical_businessunit_country_code | VARCHAR | 0.0 |
| economical_businessunit_id | VARCHAR | 0.0 |
| economical_businessunit_gln | VARCHAR | 0.0 |
| gmv_recorded_at | TIMESTAMP | 0.0 |
| local_offset | VARCHAR | 100.0 |
| transaction_channel_type | VARCHAR | 0.0 |
| sales_support | VARCHAR | 0.0 |
| retrocession_type | VARCHAR | 0.0 |
| retrocession_subtype | VARCHAR | 0.0 |
| transaction_touchpoint_name | VARCHAR | 0.0 |
| seller_type | VARCHAR | 0.0 |
| merchandise_hierarchy_code | VARCHAR | 0.0 |
| merchandise_hierarchy_name | VARCHAR | 0.0 |
| item_sustainable_type | VARCHAR | 100.0 |
| is_ecodesign | BOOLEAN | 0.0 |
| item_type | VARCHAR | 0.0 |
| transaction_num_line | INTEGER | 0.0 |
| delivery_num_line | INTEGER | 0.0 |
| item_code | VARCHAR | 0.0 |
| model_code | VARCHAR | 0.0 |
| model_label | VARCHAR | 0.0 |
| transaction_status | VARCHAR | 0.0 |
| item_operation_type | VARCHAR | 0.0 |
| gmv_item_quantity | BIGINT | 0.2 |
| not_gmv_item_quantity | BIGINT | 99.8 |
| gmv_exception | VARCHAR | 99.8 |
| transaction_currency | VARCHAR | 0.0 |
| gmv_amount | DECIMAL(18,2) | 0.2 |
| gmv_amount_euros | DECIMAL(22,6) | 0.2 |
| not_gmv_amount | DECIMAL(18,2) | 99.8 |
| not_gmv_amount_euros | DECIMAL(22,6) | 99.8 |
| regular_selling_price | DECIMAL(18,2) | 0.0 |
| vat_amount | DECIMAL(18,2) | 0.0 |
| other_tax_amount | DECIMAL(18,2) | 100.0 |
| tax_detail | STRUCT("type" VARCHAR, sub_type VARCHAR, is_tax_on_margin BOOLEAN, rate VARCHAR, "percent" DOUBLE, amt DOUBLE)[] | 0.0 |
| discount_amount | DECIMAL(18,2) | 99.8 |
| price_modifier_detail | STRUCT("type" VARCHAR, "rule" VARCHAR, rule_id VARCHAR, description VARCHAR, amt DOUBLE, after_checkout_adjusted_at TIMESTAMP)[] | 99.8 |
| after_checkout_adjusted_at | TIMESTAMP | 100.0 |
| turnover_without_taxes | DECIMAL(18,2) | 0.2 |
| turnover_without_taxes_euros | DECIMAL(22,6) | 0.2 |
| economical_cession_price_amount | DECIMAL(18,2) | 0.2 |
| economical_margin_amount | DECIMAL(18,2) | 0.2 |
| economical_margin_amount_euros | DECIMAL(22,6) | 0.2 |
| accounting_cession_price_amount | DECIMAL(18,2) | 0.2 |
| accounting_margin_amount | DECIMAL(22,6) | 0.2 |
| return_reason_code | INTEGER | 97.8 |
| return_reason_name | VARCHAR | 97.8 |
| return_reason_type | VARCHAR | 100.0 |
| return_suggested_source | VARCHAR | 100.0 |
| transaction_channel_businessunit_id | VARCHAR | 100.0 |
| transaction_channel_businessunit_gln | VARCHAR | 100.0 |
| stock_origin_businessunit_id | VARCHAR | 2.1 |
| stock_origin_businessunit_gln | VARCHAR | 2.1 |
| sender_receiver_businessunit_country_code | VARCHAR | 0.0 |
| sender_receiver_businessunit_id | VARCHAR | 0.0 |
| sender_receiver_businessunit_shipping_plant_id | VARCHAR | 0.2 |
| sender_receiver_businessunit_gln | VARCHAR | 0.0 |
| sender_receiver_businessunit_type | VARCHAR | 0.0 |
| clickandcollect_businessunit_id | VARCHAR | 100.0 |
| clickandcollect_businessunit_gln | VARCHAR | 100.0 |
| fulfiller_shipping_name | VARCHAR | 100.0 |
| fulfillment_shipping_id | VARCHAR | 100.0 |
| delivery_container_id | VARCHAR | 100.0 |
| supply_purchase_order_id | VARCHAR | 100.0 |
| delivery_type | VARCHAR | 100.0 |
| delivery_notes | VARCHAR | 100.0 |
| shipping_type | VARCHAR | 100.0 |
| replenishment_requested_at | TIMESTAMP | 100.0 |
| stock_shortaged_at | TIMESTAMP | 100.0 |
| shipping_delayed_at | TIMESTAMP | 100.0 |
| delivery_split_at | TIMESTAMP | 100.0 |
| ready_for_picking_at | TIMESTAMP | 100.0 |
| picking_begun_at | TIMESTAMP | 100.0 |
| picking_ended_at | TIMESTAMP | 100.0 |
| ready_for_pickup_at | TIMESTAMP | 100.0 |
| shipment_promised_at | TIMESTAMP | 100.0 |
| delivery_initial_promised_begin_at | TIMESTAMP | 100.0 |
| delivery_initial_promised_end_at | TIMESTAMP | 100.0 |
| delivery_current_promised_begin_at | TIMESTAMP | 100.0 |
| delivery_current_promised_end_at | TIMESTAMP | 100.0 |
| delivery_shipped_at | TIMESTAMP | 99.6 |
| transaction_finished_at | TIMESTAMP | 0.4 |
| carrier_method | VARCHAR | 99.6 |
| shipping_method | VARCHAR | 100.0 |
| carrier_label | VARCHAR | 100.0 |
| tracking_number | VARCHAR | 100.0 |
| delivery_country_code | VARCHAR | 100.0 |
| delivery_postal_code | VARCHAR | 100.0 |
| delivery_city | VARCHAR | 100.0 |
| customer_channel_type | VARCHAR | 99.6 |
| customer_identification_type | VARCHAR | 15.8 |
| dummy_store_id | VARCHAR | 0.2 |
| supplying_plant | VARCHAR | 0.2 |
| sales_org | VARCHAR | 0.2 |
| assortment_grade | VARCHAR | 0.2 |
| lifestage | VARCHAR | 0.2 |
| sap_source | VARCHAR | 0.2 |
| distribution_channel | VARCHAR | 0.2 |
| bw_exception | VARCHAR | 99.8 |
| initial_item_id | VARCHAR | 0.0 |
| item_entry_method | VARCHAR | 0.0 |
| serial_number_item_entry_method | VARCHAR | 0.0 |
| serial_number_sku | VARCHAR | 100.0 |
| serial_number_gtin | VARCHAR | 35.8 |
| serial_number_item | VARCHAR[] | 32.1 |
| serial_number_epc | VARCHAR[] | 5.0 |
| serial_number_item_lookup_code | VARCHAR | 0.0 |
| voucher_id | VARCHAR | 99.9 |
| transaction_link_detail | STRUCT("type" VARCHAR, "value" VARCHAR)[] | 100.0 |
| item_invoice_type | VARCHAR | 0.0 |
| item_invoice_number | VARCHAR | 0.0 |
| item_invoiced_at | TIMESTAMP | 0.0 |
| item_invoice_detail | STRUCT("type" VARCHAR, number VARCHAR, date TIMESTAMP)[] | 0.0 |
| fiscal_businessunit_country_code | VARCHAR | 0.0 |
| fiscal_businessunit_id | VARCHAR | 0.0 |
| fiscal_businessunit_gln | VARCHAR | 0.0 |
| associate_id | VARCHAR | 100.0 |
| transaction_channel_description | VARCHAR | 100.0 |
| transaction_touchpoint_type | VARCHAR | 0.0 |
| transaction_operator_name | VARCHAR | 100.0 |
| transaction_operator_associate_id | VARCHAR | 100.0 |
| transaction_operator_num | BIGINT | 0.0 |
| exchange_rate_local_to_euros | DECIMAL(20,12) | 0.0 |
| exchange_rate_start_date_used | DATE | 0.0 |
| workstation_id | VARCHAR | 0.0 |
| poslog_producer_name | VARCHAR | 0.0 |
| transaction_touchpoint_source | VARCHAR | 100.0 |
| economical_cession_price_origin | VARCHAR | 100.0 |
| accounting_cession_price_origin | VARCHAR | 100.0 |
| transaction_created_at | TIMESTAMP | 0.0 |
| transaction_version_at | TIMESTAMP | 0.0 |
| processing_origin | VARCHAR | 0.0 |
| gold_processed_at | TIMESTAMP | 0.0 |
| year | INTEGER | 0.0 |
| month | INTEGER | 0.0 |

**item_operation_type**: [('sale', 19550), ('return', 450)]

**transaction_channel_type**: [('offline', 19928), ('online', 72)]

**transaction_status**: [('finished', 20000)]

**item_type**: [('stock', 20000)]

**economical_businessunit_country_code**: [('VN', 14392), ('TH', 5608)]

**customer_identification_type**: [('member', 16847), (None, 3153)]

**tax_detail** format: **JSON** (structure only, values redacted)

```
[{"type":"VARCHAR","sub_type":"VARCHAR","is_tax_on_margin":"BOOLEAN","rate":"VARCHAR","percent":"DOUBLE","amt":"DOUBLE"}]
```

**price_modifier_detail** format: **JSON** (structure only, values redacted)

```
[{"type":"VARCHAR","rule":"VARCHAR","rule_id":"VARCHAR","description":"VARCHAR","amt":"DOUBLE","after_checkout_adjusted_at":"NULL"}]
```

**gmv_recorded_at (sample)**: (datetime.datetime(2023, 1, 5, 11, 38, 41), datetime.datetime(2023, 1, 31, 21, 54, 7))

## sales_tender_detail  (17 columns, parquet)

| column | type | % null |
|---|---|---|
| transaction_id | VARCHAR | 0.0 |
| tender_num_line | INTEGER | 0.0 |
| tender_recorded_at | TIMESTAMP | 0.0 |
| tender_operation_type | VARCHAR | 0.0 |
| tender_code | VARCHAR | 0.0 |
| tender_description | VARCHAR | 38.9 |
| tender_type | VARCHAR | 0.0 |
| tender_currency | VARCHAR | 0.0 |
| tender_amount | DOUBLE | 0.0 |
| tender_id | VARCHAR | 15.4 |
| giftcard_number | VARCHAR | 96.9 |
| voucher_number | VARCHAR | 99.9 |
| tender_date_list | STRUCT(status VARCHAR, date TIMESTAMP)[] | 0.0 |
| transaction_created_at | TIMESTAMP | 0.0 |
| gold_processed_at | TIMESTAMP | 0.0 |
| year | INTEGER | 0.0 |
| month | INTEGER | 0.0 |

## stock_availability_rate  (21 columns, csv)

| column | type | % null |
|---|---|---|
| availability_type | VARCHAR | 0.0 |
| country_code | VARCHAR | 0.0 |
| site_gln | BIGINT | 0.0 |
| third_type | BIGINT | 0.0 |
| third_number | BIGINT | 0.0 |
| item_code | BIGINT | 0.0 |
| is_item_followed | BIGINT | 0.0 |
| stock_network_level | BIGINT | 0.0 |
| selected_stock_network_level | BOOLEAN | 0.0 |
| is_available | BIGINT | 0.0 |
| stock_quantity | BIGINT | 0.0 |
| purch_org | VARCHAR | 0.0 |
| selling_class | BIGINT | 80.6 |
| blocked_item | BIGINT | 0.0 |
| is_official | BOOLEAN | 0.0 |
| year | BIGINT | 0.0 |
| month | BIGINT | 0.0 |
| day | BIGINT | 0.0 |
| snapshot_date | DATE | 0.0 |
| technical_flow | VARCHAR | 0.0 |
| technical_date | TIMESTAMP WITH TIME ZONE | 0.0 |

**availability_type**: [('spare', 20000)]

**country_code**: [('TH', 5612), ('SG', 5336), ('TW', 3861), ('PH', 2943), ('VN', 2248)]

## tracking_ecom_events  (20 columns, csv)

| column | type | % null |
|---|---|---|
| id | VARCHAR | 0.0 |
| session_id | VARCHAR | 0.0 |
| name | VARCHAR | 0.0 |
| country_code | VARCHAR | 0.0 |
| provider | VARCHAR | 0.0 |
| platform | VARCHAR | 0.0 |
| timestamp_utc | TIMESTAMP WITH TIME ZONE | 0.0 |
| timestamp_local | TIMESTAMP WITH TIME ZONE | 0.0 |
| timezone_identifier | VARCHAR | 0.0 |
| authorized_data_treatments | VARCHAR | 0.0 |
| metadata | VARCHAR | 0.0 |
| year | BIGINT | 0.0 |
| month | BIGINT | 0.0 |
| day | BIGINT | 0.0 |
| _technical_created_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| _technical_updated_at | TIMESTAMP WITH TIME ZONE | 0.0 |
| is_event_to_use | BOOLEAN | 0.0 |
| date | DATE | 0.0 |
| _errors | VARCHAR | 0.0 |
| _warnings | VARCHAR | 100.0 |

**name**: [('page_viewed', 8184), ('product_list_viewed', 5173), ('product_page_viewed', 2979), ('search_results_viewed', 1409), ('search_completed', 1127), ('product_size_selected', 374), ('cart_viewed', 223), ('menu_item_selected', 210), ('product_added_to_cart', 186), ('checkout_commenced', 56), ('checkout_payment_viewed', 40), ('checkout_shipping_viewed', 20), ('order_completed', 19)]

**country_code**: [('SG', 20000)]

**platform**: [('app', 11671), ('web', 8329)]

**is_event_to_use**: [(True, 20000)]

**metadata** format: **JSON** (structure only, values redacted)

```
{"session_details":{"provider_session_id":"VARCHAR","provider_session_start_time":"VARCHAR"},"page_details":{"page_full_url":"VARCHAR","page_name":"VARCHAR","page_path":"VARCHAR","page_type":"VARCHAR"},"user_details":{"user_id":"VARCHAR","member_id":"VARCHAR","provider_user_id":"VARCHAR"},"device_details":{"device_type":"VARCHAR"},"traffic_source_details":{"utm_campaign":"NULL","utm_source":"NULL","utm_medium":"NULL","referring_domain":"NULL","gclid":"NULL","channel_name":"VARCHAR","utm_id":"NULL"},"product_details":"NULL","order_details":"NULL","geo_details":{"region":"NULL","city":"VARCHAR",
```