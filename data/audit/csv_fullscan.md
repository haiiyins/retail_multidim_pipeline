# CSV full-file scan

Every file read once with `all_varchar=true`; counts are exact, distinct counts are approximate (HyperLogLog).


## Summary

| table | country codes |
|---|---|
| sales_detail | PH, SG, TH, TW, VN |
| f_member_purchase | PH, SG, TH, TW, VN |
| d_member | PH, SG, TH, TW, VN |
| dim_business_unit | PH, SG, TH, TW, VN |
| all_store_selling_price | TW |
| stock_availability_rate | PH, SG, TH, TW, VN |
| f_member_favorite_sport | PH, SG, TH, TW, VN |
| tracking_ecom_events | SG |

**Union of country codes:** PH, SG, TH, TW, VN

| country | sales_detail rows | min gmv_recorded_at | max gmv_recorded_at |
|---|---:|---|---|
| PH | 442,158 | 2023-01-01 00:15:28 | 2023-10-31 23:46:14 |
| SG | 1,120,242 | 2023-01-01 01:36:52 | 2023-10-31 23:36:22 |
| TH | 548,402 | 2023-01-01 08:07:23 | 2023-10-31 23:59:55 |
| TW | 1,554,038 | 2023-01-01 00:14:34 | 2023-10-31 23:55:49 |
| VN | 249,126 | 2023-01-01 00:09:13 | 2023-10-31 23:44:52 |

## sales_detail  (3,913,966 rows, 1 s)

| economical_businessunit_country_code | rows | min gmv_recorded_at | max gmv_recorded_at |
|---|---:|---|---|
| PH | 442,158 | 2023-01-01 00:15:28 | 2023-10-31 23:46:14 |
| SG | 1,120,242 | 2023-01-01 01:36:52 | 2023-10-31 23:36:22 |
| TH | 548,402 | 2023-01-01 08:07:23 | 2023-10-31 23:59:55 |
| TW | 1,554,038 | 2023-01-01 00:14:34 | 2023-10-31 23:55:49 |
| VN | 249,126 | 2023-01-01 00:09:13 | 2023-10-31 23:44:52 |

**item_operation_type** (3 values): `sale` 3,825,185, `return` 88,204, `cancel` 577

**transaction_channel_type** (2 values): `offline` 3,610,210, `online` 303,756

**transaction_status** (5 values): `finished` 3,861,863, `shipped` 29,815, `authorized` 11,050, `delivered` 7,369, `canceled` 3,784

**item_type** (2 values): `stock` 3,859,680, `service` 54,286

**customer_identification_type** (1 values): `member` 3,228,075

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| transaction_id | 0.0 % | 30 | 42 | 1,285,755 | 0 |
| item_code | 100.0 % | 1 | 13 | 111,227 | 0 |
| model_code | 99.9 % | 6 | 7 | 41,154 | 0 |
| economical_businessunit_gln | 100.0 % | 13 | 13 | 76 | 0 |
| merchant_businessunit_gln | 100.0 % | 13 | 13 | 78 | 0 |

## sales_tender_detail  (17,452,155 rows, 1 s)

| country | rows | min tender_recorded_at | max tender_recorded_at |
|---|---:|---|---|
| ALL | 17,452,155 | 2021-02-21 14:10:53 | 2026-09-29 17:29:28 |

**tender_operation_type** (2 values): `sale` 15,418,171, `refund` 2,033,984

**tender_type** (68 values): `CreditCard` 7,889,616, `Cash` 3,949,769, `QRPayment` 1,163,212, `LinePay` 1,023,526, `Nets` 525,609, `DebitCard` 324,753, `ECheque` 310,682, `CashOnDelivery` 304,954, `ApplePay` 262,022, `DecashopCashOnDelivery` 202,885, `ExternalMarketPlace` 179,712, `VNPAY` 130,658, `EGiftcardTW` 111,944, `DecashopEcommerce` 111,840, `Wallet` 86,471 … (+53 more)

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| transaction_id | 0.0 % | 30 | 48 | 14,463,607 | 0 |

## f_member_purchase  (14,641,035 rows, 1 s)

| member_country_code | rows | min association_datetime_utc | max association_datetime_utc |
|---|---:|---|---|
| PH | 2,222,260 | 2023-08-31 22:44:34 | 2026-09-29 05:30:06 |
| SG | 4,851,835 | 2023-08-31 22:12:59 | 2026-09-29 05:29:42 |
| TH | 5,533,484 | 2023-09-01 01:15:25 | 2026-09-29 05:29:48 |
| TW | 2,020,120 | 2023-09-01 01:03:08 | 2026-09-29 05:29:37 |
| VN | 13,336 | 2023-09-01 03:41:39 | 2026-09-29 04:59:15 |

**transaction_source** (2 values): `AUTO` 14,608,666, `MANUAL` 32,369

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| transaction_id | 0.0 % | 28 | 48 | 14,372,749 | 0 |
| member_id | 0.0 % | 36 | 36 | 4,800,579 | 0 |

## d_member  (5,691,382 rows, 1 s)

| member_country_code | rows | min account_creation_datetime_utc | max account_creation_datetime_utc |
|---|---:|---|---|
| PH | 1,056,154 | 2023-01-01 00:11:08 | 2026-10-13 21:57:02.338000 |
| SG | 745,010 | 2023-01-01 01:07:02 | 2026-10-13 19:46:37.506000 |
| TH | 1,600,414 | 2023-01-01 00:52:29 | 2026-10-13 21:35:08.222000 |
| TW | 1,335,927 | 2023-01-01 00:34:21 | 2026-10-13 20:48:27.355000 |
| VN | 953,877 | 2023-01-01 01:08:49 | 2026-10-13 21:29:26.973000 |

**is_teammate** (2 values): `false` 5,690,393, `true` 989

**is_business** (2 values): `false` 5,691,297, `true` 85

**is_legal_entity** (2 values): `false` 5,691,247, `true` 135

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| member_id | 0.0 % | 36 | 36 | 5,893,420 | 0 |
| preferred_store_gln | 100.0 % | 13 | 13 | 1,018 | 0 |
| creation_store_gln | 100.0 % | 13 | 13 | 129 | 0 |

## dim_item  (3,847,407 rows, 1 s)

| country | rows | min - | max - |
|---|---:|---|---|
| ALL | 3,847,407 | None | None |

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| item_code | 100.0 % | 3 | 8 | 3,661,798 | 0 |
| model_code | 100.0 % | 1 | 7 | 929,185 | 0 |
| supermodel_code | 30.3 % | 2 | 8 | 789,798 | 0 |

## dim_business_unit  (275 rows, 0 s)

| country_code | rows | min - | max - |
|---|---:|---|---|
| PH | 49 | None | None |
| SG | 75 | None | None |
| TH | 66 | None | None |
| TW | 52 | None | None |
| VN | 33 | None | None |

**business_unit_third_type** (5 values): `7` 137, `48` 65, `50` 49, `9` 15, `15` 9

**plant_type** (8 values): `STORE` 125, `VADA` 65, `WEBSITE` 49, `WAREHOUSE` 15, `COUNTRY` 9, `UNDEFINED` 9, `OUTLET` 2, `WORKSHOP` 1

**is_business_unit_closed** (2 values): `false` 251, `true` 24

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| business_unit_gln | 100.0 % | 13 | 13 | 275 | 0 |
| business_unit_third_id | 0.0 % | 7 | 14 | 276 | 0 |

## dim_calendar  (1,461 rows, 0 s)

| country | rows | min date_of_day | max date_of_day |
|---|---:|---|---|
| ALL | 1,461 | 2023-01-01 00:00:00 | 2026-12-31 00:00:00 |

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| date_of_day | 0.0 % | 10 | 10 | 1,513 | 0 |

## all_store_selling_price  (9,429,844 rows, 1 s)

| country_code | rows | min price_start_date | max price_start_date |
|---|---:|---|---|
| TW | 9,429,844 | 2017-03-09 00:00:00 | 2100-10-07 00:00:00 |

**price_type** (3 values): `STANDARD` 5,626,265, `END_OF_LINE` 3,150,001, `DAY_TO_DAY_PROMOTION` 653,578

**business_unit_third_type** (2 values): `7` 7,153,416, `50` 2,276,428

**timeline_type** (2 values): `unlinked_timeline` 9,418,039, `default_timeline` 11,805

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| item_code | 100.0 % | 4 | 8 | 283,412 | 0 |
| business_unit_gln_code | 100.0 % | 13 | 13 | 16 | 0 |

## stock_availability_rate  (36,701,681 rows, 2 s)

| country_code | rows | min snapshot_date | max snapshot_date |
|---|---:|---|---|
| PH | 6,154,258 | 2024-01-04 00:00:00 | 2026-09-28 00:00:00 |
| SG | 9,076,499 | 2024-01-04 00:00:00 | 2026-09-28 00:00:00 |
| TH | 8,930,348 | 2024-01-04 00:00:00 | 2026-09-28 00:00:00 |
| TW | 8,301,955 | 2024-01-04 00:00:00 | 2026-09-28 00:00:00 |
| VN | 4,238,621 | 2024-01-04 00:00:00 | 2026-09-28 00:00:00 |

**availability_type** (1 values): `spare` 36,701,681

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| item_code | 100.0 % | 5 | 7 | 5,502 | 0 |
| site_gln | 100.0 % | 13 | 13 | 131 | 0 |

## f_member_favorite_sport  (796,143 rows, 0 s)

| country_code | rows | min event_datetime_utc | max event_datetime_utc |
|---|---:|---|---|
| PH | 122,474 | 2023-01-01 00:41:37.791000 | 2026-09-29 04:12:13.999000 |
| SG | 115,804 | 2023-01-01 02:03:27.965000 | 2026-09-26 04:09:07.861000 |
| TH | 116,892 | 2023-01-01 00:24:09.900000 | 2026-09-09 04:51:47.794000 |
| TW | 413,673 | 2023-01-01 01:03:45.050000 | 2026-09-26 04:58:32.634000 |
| VN | 27,300 | 2023-01-01 11:15:21.176000 | 2026-09-29 04:39:05.103000 |

**event_type** (2 values): `delete` 427,564, `create` 368,579

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| member_id | 0.0 % | 36 | 36 | 299,960 | 0 |
| sport_id | 100.0 % | 1 | 3 | 2,272 | 0 |

## tracking_ecom_events  (844,188 rows, 1 s)

| country_code | rows | min timestamp_utc | max timestamp_utc |
|---|---:|---|---|
| SG | 844,188 | 2025-11-09 16:00:00.090000 | 2025-11-12 15:59:59.826000 |

**name** (13 values): `page_viewed` 343,853, `product_list_viewed` 222,597, `product_page_viewed` 121,077, `search_results_viewed` 58,530, `search_completed` 49,499, `product_size_selected` 15,623, `menu_item_selected` 9,959, `cart_viewed` 9,513, `product_added_to_cart` 7,392, `checkout_commenced` 2,652, `checkout_payment_viewed` 1,644, `order_completed` 1,060, `checkout_shipping_viewed` 789

**platform** (2 values): `app` 492,895, `web` 351,293

**is_event_to_use** (1 values): `true` 844,188

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| id | 0.0 % | 32 | 32 | 836,708 | 0 |
| session_id | 0.0 % | 32 | 32 | 82,332 | 0 |