# Raw full-file scan

Every raw file (Parquet preferred, else CSV read with `all_varchar=true`) is read once; counts are exact, distinct counts are approximate (HyperLogLog).


## Summary

| table | country codes | contract-key duplicate rows |
|---|---|---:|
| sales_detail | SG, TH, VN | 8,501,874 (9.5 %) |
| sales_tender_detail | - | 0 (0.0 %) |
| f_member_purchase | AE, AR, AT, AU, BE, BG, BH, BR, CA, CD, CH, CI, CL, CN, CO, CR, CY, CZ, DE, DZ, EE, EG, ES, FR, GB, GF, GH, GP, GR, HK, HR, HU, ID, IE, IL, IN, IT, JP, KE, KH, KR, KW, KZ, LB, LK, LT, LU, LV, MA, MQ, MT, MU, MX, MY, NC, NL, NZ, None, OM, PA, PF, PH, PL, PT, PY, QA, RE, RO, RS, SA, SE, SG, SI, SK, SN, TH, TN, TR, TW, UA, US, UY, VN, ZA | 42,907,922 (68.1 %) |
| d_member | PH, SG, TH, TW, VN | 0 (0.0 %) |
| dim_item | - | 0 (0.0 %) |
| dim_business_unit | PH, SG, TH, TW, VN | 0 (0.0 %) |
| dim_calendar | - | 0 (0.0 %) |
| all_store_selling_price | SG, TH, VN | 0 (0.0 %) |
| stock_availability_rate | PH, SG, TH, TW, VN | 5,320,870 (14.5 %) |
| f_member_favorite_sport | PH, SG, TH, TW, VN | 78,357 (9.8 %) |
| tracking_ecom_events | SG | 0 (0.0 %) |

**Union of country codes:** AE, AR, AT, AU, BE, BG, BH, BR, CA, CD, CH, CI, CL, CN, CO, CR, CY, CZ, DE, DZ, EE, EG, ES, FR, GB, GF, GH, GP, GR, HK, HR, HU, ID, IE, IL, IN, IT, JP, KE, KH, KR, KW, KZ, LB, LK, LT, LU, LV, MA, MQ, MT, MU, MX, MY, NC, NL, NZ, None, OM, PA, PF, PH, PL, PT, PY, QA, RE, RO, RS, SA, SE, SG, SI, SK, SN, TH, TN, TR, TW, UA, US, UY, VN, ZA

| country | sales_detail rows | min gmv_recorded_at | max gmv_recorded_at |
|---|---:|---|---|
| SG | 46,292,657 | 2023-01-01 01:36:52 | 2026-10-26 18:29:48 |
| TH | 31,429,511 | 2023-01-01 00:29:36 | 2026-10-26 17:29:42 |
| VN | 11,599,372 | 2023-01-01 00:09:13 | 2026-10-26 17:29:25 |

## sales_detail  (89,321,540 rows, parquet, 11 s)

| economical_businessunit_country_code | rows | min gmv_recorded_at | max gmv_recorded_at |
|---|---:|---|---|
| SG | 46,292,657 | 2023-01-01 01:36:52 | 2026-10-26 18:29:48 |
| TH | 31,429,511 | 2023-01-01 00:29:36 | 2026-10-26 17:29:42 |
| VN | 11,599,372 | 2023-01-01 00:09:13 | 2026-10-26 17:29:25 |

**item_operation_type** (3 values): `sale` 87,148,620, `return` 1,765,179, `cancel` 407,741

**transaction_channel_type** (2 values): `offline` 78,047,372, `online` 11,274,168

**transaction_status** (5 values): `finished` 87,931,561, `canceled` 768,707, `shipped` 596,618, `authorized` 23,574, `partialship` 1,080

**item_type** (2 values): `stock` 85,936,771, `service` 3,384,769

**customer_identification_type** (2 values): `member` 69,323,646, `guest` 1,271,163

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| transaction_id | 0.0 % | 30 | 48 | 26,792,434 | 0 |
| item_code | 100.0 % | 1 | 13 | 155,077 | 0 |
| model_code | 99.9 % | 1 | 7 | 49,309 | 0 |
| economical_businessunit_gln | 100.0 % | 13 | 13 | 80 | 0 |
| merchant_businessunit_gln | 100.0 % | 13 | 13 | 79 | 0 |

**Contract key** (transaction_id, transaction_num_line): 80,819,666 distinct, 8,501,874 duplicate rows (9.5 %)

## sales_tender_detail  (29,740,415 rows, parquet, 1 s)

| country | rows | min tender_recorded_at | max tender_recorded_at |
|---|---:|---|---|
| ALL | 29,740,415 | 2023-01-01 00:09:13 | 2026-10-26 18:29:42 |

**tender_operation_type** (2 values): `sale` 28,038,395, `refund` 1,702,020

**tender_type** (50 values): `CreditCard` 15,724,289, `Cash` 3,677,973, `QRPayment` 3,636,375, `Nets` 1,773,683, `[org]CashOnDelivery` 672,149, `ApplePay` 639,363, `ExternalMarketPlace` 533,745, `VNPAY` 456,366, `VNPay` 286,251, `PayNow` 266,767, `CashOnDelivery` 250,998, `ECheque` 233,155, `PromptPay` 228,965, `Giftcard` 187,660, `GiftcardVitali` 172,454 … (+35 more)

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| transaction_id | 0.0 % | 30 | 48 | 27,169,894 | 0 |

**Contract key** (transaction_id, tender_num_line): 29,740,415 distinct, 0 duplicate rows (0.0 %)

## f_member_purchase  (63,047,610 rows, parquet, 3 s)

| member_country_code | rows | min association_datetime_utc | max association_datetime_utc |
|---|---:|---|---|
| AE | 6,703 | 2023-03-15 09:26:14 | 2026-10-25 13:45:11 |
| AR | 47 | 2026-02-06 12:36:37 | 2026-10-04 09:16:12 |
| AT | 2,847 | 2023-10-10 10:10:21 | 2026-10-25 12:37:50 |
| AU | 85,515 | 2023-01-01 03:38:13 | 2026-10-26 05:22:47 |
| BE | 22,440 | 2023-01-08 09:45:58 | 2026-10-26 03:58:56 |
| BG | 3,049 | 2023-03-13 04:23:56 | 2026-10-25 13:32:53 |
| BH | 463 | 2024-07-19 06:07:47 | 2026-10-25 10:54:41 |
| BR | 16,110 | 2023-01-15 03:38:25 | 2026-10-25 13:27:08 |
| CA | 14,655 | 2023-01-14 06:16:07 | 2026-10-25 13:12:37 |
| CD | 195 | 2024-04-12 08:40:13 | 2026-10-09 04:14:43 |
| CH | 32,681 | 2023-01-12 18:16:55 | 2026-10-26 05:21:44 |
| CI | 350 | 2024-02-18 03:36:09 | 2026-10-25 10:50:11 |
| CL | 3,516 | 2023-01-06 01:38:57 | 2026-10-26 05:25:14 |
| CN | 48,954 | 2024-01-01 04:11:31 | 2024-05-06 12:08:52 |
| CO | 4,662 | 2023-09-03 06:47:11 | 2026-10-25 11:58:01 |
| CR | 9 | 2025-07-30 03:45:10 | 2026-10-24 09:10:39 |
| CY | 65 | 2025-11-16 06:56:12 | 2026-09-30 15:05:30 |
| CZ | 8,052 | 2023-02-26 07:21:21 | 2026-10-26 03:51:14 |
| DE | 65,675 | 2023-01-05 18:21:36 | 2026-10-26 04:56:43 |
| DZ | 674 | 2023-11-04 09:02:33 | 2026-10-21 13:12:14 |
| EE | 515 | 2024-01-21 04:05:51 | 2026-10-10 04:04:43 |
| EG | 5,196 | 2023-04-16 15:15:39 | 2026-10-22 12:16:29 |
| ES | 41,487 | 2023-01-05 18:22:40 | 2026-10-26 04:25:22 |
| FR | 209,585 | 2023-01-02 18:18:00 | 2026-10-26 05:00:58 |
| GB | 104,275 | 2023-01-05 05:57:21 | 2026-10-26 05:29:49 |
| GF | 28 | 2026-05-14 05:13:24 | 2026-10-02 11:48:36 |
| GH | 691 | 2023-01-14 13:56:11 | 2026-10-23 14:36:06 |
| GP | 187 | 2024-01-16 02:18:11 | 2026-10-15 07:06:15 |
| GR | 1,359 | 2023-09-29 15:28:11 | 2026-10-24 12:52:07 |
| HK | 130,825 | 2023-01-01 05:50:48 | 2026-10-26 04:32:54 |
| HR | 695 | 2023-09-23 03:28:52 | 2026-10-22 05:02:04 |
| HU | 5,931 | 2023-02-15 18:20:20 | 2026-10-25 06:06:08 |
| ID | 45,327 | 2023-01-01 07:24:26 | 2026-10-26 02:13:50 |
| IE | 5,858 | 2023-01-04 09:24:18 | 2026-10-25 11:33:45 |
| IL | 28,527 | 2023-01-03 18:25:46 | 2026-10-26 04:37:44 |
| IN | 134,425 | 2023-01-02 14:06:42 | 2026-10-26 05:17:39 |
| IT | 23,134 | 2023-01-28 18:18:17 | 2026-10-25 13:15:15 |
| JP | 9,462 | 2023-01-01 09:27:08 | 2026-10-25 12:53:35 |
| KE | 1,707 | 2023-10-05 04:43:49 | 2026-10-24 07:21:47 |
| KH | 11,593 | 2023-01-01 06:09:52 | 2026-10-26 02:27:49 |
| KR | 8,871 | 2023-01-03 09:06:01 | 2026-10-25 13:53:44 |
| KW | 781 | 2023-12-13 11:36:18 | 2026-10-24 13:50:18 |
| KZ | 6,457 | 2023-10-15 04:26:18 | 2026-10-25 13:18:54 |
| LB | 89 | 2024-02-14 05:16:44 | 2026-10-13 05:09:46 |
| LK | 4,861 | 2023-02-05 06:41:18 | 2026-10-23 06:21:55 |
| LT | 1,402 | 2023-11-11 10:11:21 | 2026-10-24 10:59:52 |
| LU | 358 | 2023-10-28 07:06:23 | 2026-10-24 10:15:35 |
| LV | 1,116 | 2023-11-12 09:53:38 | 2026-10-25 11:51:24 |
| MA | 3,994 | 2023-05-03 03:56:50 | 2026-10-25 06:09:09 |
| MQ | 270 | 2023-11-25 06:56:22 | 2026-10-24 06:09:23 |
| MT | 740 | 2023-11-14 15:20:18 | 2026-10-24 04:19:24 |
| MU | 1,452 | 2023-06-06 21:55:11 | 2026-10-25 05:20:49 |
| MX | 6,966 | 2023-01-15 18:17:14 | 2026-10-25 10:21:29 |
| MY | 452,187 | 2023-01-01 06:45:38 | 2026-10-26 05:25:27 |
| NC | 2,504 | 2023-11-06 02:28:03 | 2026-10-24 10:32:24 |
| NL | 38,731 | 2023-01-06 08:36:45 | 2026-10-26 05:18:42 |
| NZ | 747 | 2023-09-08 05:58:33 | 2026-10-23 06:25:54 |
| OM | 338 | 2024-05-02 00:45:47 | 2026-10-23 09:08:32 |
| PA | 56 | 2024-04-02 13:20:48 | 2026-06-21 01:58:41 |
| PF | 81 | 2025-06-05 05:11:31 | 2026-09-12 02:45:34 |
| PH | 77,432 | 2023-01-01 03:30:23 | 2026-10-26 05:13:56 |
| PL | 14,504 | 2023-02-01 05:48:56 | 2026-10-25 23:57:10 |
| PT | 8,367 | 2023-01-12 18:18:31 | 2026-10-25 09:14:29 |
| PY | 148 | 2025-06-15 04:19:07 | 2026-10-16 07:21:26 |
| QA | 1,116 | 2023-09-05 05:52:52 | 2026-10-24 08:29:40 |
| RE | 4,215 | 2023-11-11 11:23:17 | 2026-10-24 07:18:34 |
| RO | 6,136 | 2023-03-28 11:13:44 | 2026-10-25 11:53:48 |
| RS | 780 | 2023-11-05 12:37:48 | 2026-10-22 10:45:04 |
| SA | 732 | 2023-10-11 05:15:54 | 2026-10-17 04:17:54 |
| SE | 6,791 | 2023-02-20 05:24:14 | 2026-10-26 05:02:15 |
| SG | 26,062,587 | 2022-12-31 23:44:37 | 2026-10-26 05:29:56 |
| SI | 751 | 2023-11-04 10:05:28 | 2026-10-25 11:45:20 |
| SK | 1,911 | 2023-10-01 13:24:41 | 2026-10-23 09:30:40 |
| SN | 294 | 2023-09-20 10:38:43 | 2026-10-21 04:14:05 |
| TH | 25,627,148 | 2023-01-01 02:07:35 | 2026-10-26 05:29:53 |
| TN | 995 | 2023-09-28 08:47:03 | 2026-10-23 11:23:02 |
| TR | 37,961 | 2023-03-11 14:01:48 | 2026-10-25 13:10:29 |
| TW | 72,538 | 2023-01-01 05:41:06 | 2026-10-26 03:34:41 |
| UA | 3,220 | 2023-03-09 09:38:21 | 2026-10-24 10:47:40 |
| US | 614 | 2024-07-07 07:14:48 | 2026-10-23 04:22:27 |
| UY | 312 | 2024-02-07 13:00:01 | 2026-10-01 13:00:40 |
| VN | 7,996,811 | 2023-01-01 03:05:13 | 2026-10-26 05:29:38 |
| ZA | 2,329 | 2023-06-04 09:08:28 | 2026-10-25 10:00:57 |
| None | 1,510,448 | 2023-01-01 03:50:03 | 2026-10-26 00:46:55.148192 |

**transaction_source** (2 values): `AUTO` 61,395,961, `MANUAL` 1,651,649

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| transaction_id | 0.0 % | 30 | 48 | 19,722,778 | 0 |
| member_id | 0.0 % | 36 | 36 | 4,808,000 | 1,469,179 |

**Contract key** (transaction_id, member_id): 20,139,688 distinct, 42,907,922 duplicate rows (68.1 %)

## d_member  (5,691,382 rows, csv, 1 s)

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

**Contract key** (member_id): 5,691,382 distinct, 0 duplicate rows (0.0 %)

## dim_item  (3,847,407 rows, csv, 1 s)

| country | rows | min - | max - |
|---|---:|---|---|
| ALL | 3,847,407 | None | None |

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| item_code | 100.0 % | 3 | 8 | 3,661,798 | 0 |
| model_code | 100.0 % | 1 | 7 | 929,185 | 0 |
| supermodel_code | 30.3 % | 2 | 8 | 789,798 | 0 |

**Contract key** (item_code): 3,847,407 distinct, 0 duplicate rows (0.0 %)

## dim_business_unit  (275 rows, csv, 0 s)

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

**Contract key** (business_unit_gln): 275 distinct, 0 duplicate rows (0.0 %)

## dim_calendar  (1,461 rows, csv, 0 s)

| country | rows | min date_of_day | max date_of_day |
|---|---:|---|---|
| ALL | 1,461 | 2023-01-01 00:00:00 | 2026-12-31 00:00:00 |

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| date_of_day | 0.0 % | 10 | 10 | 1,513 | 0 |

**Contract key** (date_of_day): 1,461 distinct, 0 duplicate rows (0.0 %)

## all_store_selling_price  (42,416,758 rows, parquet, 3 s)

| country_code | rows | min price_start_date | max price_start_date |
|---|---:|---|---|
| SG | 14,372,792 | 2015-08-22 00:00:00 | 2101-01-01 00:00:00 |
| TH | 16,770,698 | 2018-12-15 00:00:00 | 2049-02-28 00:00:00 |
| VN | 11,273,268 | 2019-03-21 16:14:22 | 2027-01-06 00:00:00 |

**price_type** (4 values): `STANDARD` 31,544,099, `END_OF_LINE` 8,593,464, `DAY_TO_DAY_PROMOTION` 1,776,874, `DROP` 502,321

**business_unit_third_type** (3 values): `7` 34,636,734, `50` 6,290,150, `15` 1,489,874

**timeline_type** (2 values): `unlinked_timeline` 39,777,045, `default_timeline` 2,639,713

| key column | digits only | min len | max len | ≈ distinct | nulls |
|---|---:|---:|---:|---:|---:|
| item_code | 100.0 % | 1 | 7 | 449,406 | 0 |
| business_unit_gln_code | 100.0 % | 13 | 13 | 110 | 0 |

**Contract key** (item_code, business_unit_gln_code, price_start_date, price_type): 42,416,758 distinct, 0 duplicate rows (0.0 %)

## stock_availability_rate  (36,701,681 rows, csv, 6 s)

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

**Contract key** (site_gln, item_code, snapshot_date, availability_type): 31,380,811 distinct, 5,320,870 duplicate rows (14.5 %)

## f_member_favorite_sport  (796,143 rows, csv, 0 s)

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

**Contract key** (member_id, sport_id, event_datetime_utc): 717,786 distinct, 78,357 duplicate rows (9.8 %)

## tracking_ecom_events  (844,188 rows, csv, 1 s)

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

**Contract key** (id): 844,188 distinct, 0 duplicate rows (0.0 %)