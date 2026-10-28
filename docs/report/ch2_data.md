# 2. Data

> Numbers: three-country server build (SG, TH, VN), 2026-10-28, unless a sentence says "export" (whole files,
> `data/audit/csv_fullscan.md`) or "owner" (data-owner answers recorded in `DESIGN_DECISIONS.md` §3). Tables are in `docs/report/tables/`.

## 2.1 Sources

The data set is an export of eleven tables from a multi-country sporting-goods retailer's data platform, covering point-of-sale and
e-commerce transactions, the product catalogue, prices, a stock table, loyalty members and their favourite sports, store master data,
a calendar, and web and app click-stream events. Two export rounds were received: a first CSV export capped in size (2026-10-25) and a
Parquet re-export of the large tables (2026-10-27, complete `dim_item` on 2026-10-28). Six tables arrive as Parquet (one of them as a
directory of 1,774 Spark parts) and five as CSV **(t01)**.

| Table | Content | Grain (contract key) | Export rows |
|---|---|---|---:|
| `sales_detail` | sale, cancel and return lines of every transaction, 141 columns | transaction × line | 89,321,540 |
| `sales_tender_detail` | payment lines (tender type, amount) | transaction × tender line | 29,740,415 |
| `f_member_purchase` | association of a transaction to a loyalty member | transaction × member | 63,047,610 |
| `d_member` | loyalty account attributes and exclusion flags | member | 5,691,382 |
| `dim_item` | SKU catalogue with model, sport department, univers, gender | item (SKU) | 4,364,106 |
| `dim_business_unit` | stores and website units, timezone, country | business unit | 275 |
| `dim_calendar` | one row per day 2023 – 2026 | day | 1,461 |
| `all_store_selling_price` | price timeline per SKU and business unit | item × unit × start date × price type | 42,416,758 |
| `stock_availability_rate` | daily availability snapshots | site × item × day × availability type | 36,701,681 |
| `f_member_favorite_sport` | favourite-sport events (add / remove) per member | member × sport × event time | 796,143 |
| `tracking_ecom_events` | web and app events with nested metadata | event id | 999,710,429 (1,774 parts, ≈ 200 GB) |

Export rows are the whole files as scanned by `ingestion/probe_full_scan.py` (`make probe-full`); the click-stream was scanned on the
server over its 1,774 parts (SG 538.0 M events from 2023-01-01, TH 282.8 M from 2023-04-26, VN 178.9 M from 2024-04-27, all up to
2026-10-25). Transactions exist for three countries (SG 46.3 M lines, TH 31.4 M, VN 11.6 M) from 2023-01-01 to 2026-10-26; `d_member`, `dim_business_unit`, the stock and the sport tables also contain PH and TW, and
`f_member_purchase` carries 85 account countries because members buy abroad.

**Scope.** The pipeline processes SG, TH and VN — the three countries covered by the Parquet re-export and the web events. PH and
TW exist only in the capped first export (sales up to October 2023, no prices, no events) and were put out of scope on 2026-10-28
(issue #54, DESIGN §2). Country is a pipeline parameter: the same code runs for one country on the laptop (VN, `COUNTRY_FILTER`) and
for the three on the server.

## 2.2 Profiling before transformation

Nothing is transformed before its assumptions are measured (RUNBOOK step 2). Two probes produce the two committed reports:

- `make probe` reads the first 20,000 rows of every file and reports column types, null ratios, enumerated values and the shape of
  the nested columns (`data/audit/csv_profile.md`);
- `make probe-full` reads every file once — exact counts, approximate distinct counts (HyperLogLog), rows and date span per country,
  value domains, key formats and contract-key duplicates (`data/audit/csv_fullscan.md`). Because the exports are sorted by country,
  the 20,000-row sample cannot show the country list or the real date span; only the full scan can.

Facts the probes established, each with its consequence for the design (DESIGN §3):

| Fact (export) | Consequence |
|---|---|
| `item_operation_type` ∈ {sale 97.6 %, cancel 0.5 %, return 2.0 %}; a cancelled online order is a `sale` line plus a `cancel` line that net to zero | signed netting per (transaction, item); transaction status derived from the net amount |
| 9.5 % of `sales_detail` rows (8.5 M) repeat a (transaction, line) key; the owner confirmed the source table is unique on that key, so the duplicates come from overlapping extracts; SG 46,292,657 rows → 41,642,599 distinct rows → 41,622,617 line keys, TH 31,429,511 → 28,596,100 → 28,592,072, VN 11,599,372 → 10,607,241 → 10,604,977 **(t02)** | exact-row deduplication, then the latest `transaction_version_at` per line key; the remaining split lines are kept |
| `transaction_status` has five values (finished, canceled, shipped, authorized, partialship); the owner: not a filter — a line counts once `gmv_recorded_at` is set | no status filter; shipped orders count as sales, cancellations net out |
| `gmv_recorded_at` is local time, `transaction_version_at` is UTC; website units carry no timezone in `dim_business_unit` | UTC derived through the unit's timezone, else the country's; the dbt session is pinned to UTC (§3.3) |
| Key formats: every `*_gln` is a 13-digit number, `item_code` digits only (1 – 13 characters, sniffed as `VARCHAR` in one file and `BIGINT` in others), `model_code` 99.9 % digits, `transaction_id` 30 – 48 characters, `member_id` a 36-character UUID | all join keys cast to `VARCHAR` in the data contracts |
| Nested columns are real `STRUCT` / `LIST<STRUCT>` values in Parquet (`tax_detail[]`, `price_modifier_detail[].{type, rule, amt}`, `metadata.user_details.member_id`, `metadata.product_details[].model_code`) and `Map(k -> v)` strings in the CSV export; `_errors` is present on every event and only lists empty optional fields | struct-path extraction macros; `is_event_to_use` alone decides event validity |
| `price_type` ∈ {STANDARD, DAY_TO_DAY_PROMOTION, END_OF_LINE, DROP} (no DROP in VN, SEASON_SALES never occurs); promotion names live in `price_modifier_detail[].rule` | `promo_kind` maps the four types; discount usage read from the modifier rules |
| Business-unit type 15 is the one COUNTRY unit per country and the national reference price; type 50 (websites) repeats it row for row (VN: 536,069 keys compared, 0 differ); type 7 are stores with the same prices (`audit.price_uniformity`, gap 0.0) | national price timeline from type 15, type 50 as fallback, store prices off |
| `member_country_code` is the account-creation country; `economical_businessunit_country_code` is the transaction country (VN 2025: 2,975 transactions by members registered elsewhere) | transaction country everywhere; account country is a profile attribute |
| Only 33.9 % of the 1.0 bn web events carry a `member_id`; `user_id` is on every event; the 2023-10 → 2024-04 gap is a real absence (owner); usable VN events start 2024-07 | two-tier identity stitching (§3.5); `web_data_available` flag in the member entity |
| `stock_availability_rate` tracks spare parts only (owner); 1.7 – 2.0 % of the SKUs sold since 2025 appear in it (SG 709 of 42,236, TH 664 of 33,980, VN 517 of 31,035) **(t05)**; real inventory sits in two unexported tables and availability stays above 90 % | stock signal switched off (issue #21), columns kept as NULL behind a flag |
| The catalogue's univers `FIXT & FURNIT` holds store fixtures, carrier bags and POS material — 23,134 models **(t16)**; in VN the paper bag alone is on 447 k sale lines and 13.5 % of baskets | excluded from the model catalogue; the lines are quarantined as `NON_MERCHANDISE` |
| The first `dim_item` lacked 4,569 VN item codes (14.5 % of stock lines); the re-export holds all but 213 malformed VN codes | SKUs sold that are in the catalogue: SG 96.09 %, TH 98.65 %, VN 99.48 % **(t16)**; gate 2, on stock lines, at 99.93 – 100 % **(t04)** |

## 2.3 Volumes after loading (SG, TH, VN)

Loading the three countries into Bronze (RUNBOOK step 3) writes 11 Parquet tables, 127.1 GB in total, in 6,643 s (1 h 51 min) on the
server; the click-stream alone is 999.7 M events, 115.6 GB and 87 minutes, `sales_detail` 89.3 M rows, 8.1 GB and 22 minutes, every other
table under 31 seconds **(t01)**. After Silver the fact table keeps 66,122,312 sale lines (SG 33,838,361, TH 23,972,123, VN 8,311,828) in
26,273,338 transactions, by 1.36 M, 2.30 M and 1.05 M buying members respectively, plus 1,575,457 return lines; 5,584,701 netted rows are
quarantined with a reason **(t02, t03)**. The member profile has 745,010 SG, 1,600,414 TH and 953,877 VN accounts (17, 1,075 and 12 of
them flagged as non-consumer and excluded); `d_member` also holds 2.39 M PH and TW accounts, outside the scope **(t17)**. The price
timeline reduces 42,416,758 raw price rows to 1,461,666 national SKU intervals (SG 563,721, TH 362,140, VN 535,805) for 468,344 SKUs
**(t06)**. The clean web table holds 971,454,050 events: SG 525.2 M over 1,250 days from 2023-01-01, TH 274.0 M over 1,215 days from
2023-04-26, VN 172.2 M over 847 days from 2024-07-01, the first day with usable VN events **(t08)**.

Sizes of every Silver, quarantine, Gold and audit table are listed in **(t11)**: the clean web events (56.0 GB) and the stitched events
(790 M rows, 33.2 GB) are the largest tables, the anchor grid holds 221 M candidate anchors (5.9 GB), and the pair-level Gold tables
are 69 M rows and 10.7 GB each because the anchor caps bound them (§5 of the report).
