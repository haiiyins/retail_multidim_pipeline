# Design decisions and work-breakdown structure

This document records the decisions frozen after the design review, so that every team member builds against the same assumptions. The step-by-step procedure lives in `RUNBOOK.md`.

## 1. Problem statement

Given an identified member *u* and an anchor date *t*, predict the set of products (`model_code`) that *u* will purchase in the window (t, t + Δ], with Δ = 30 days (primary) and 90 days (secondary). The output is a top-K list of models that are purchasable at time *t* (in stock at the member's usual store or in the country's e-commerce channel).

The **pipeline is the deliverable**. A single fixed ranking model (LightGBM LambdaRank, hyper-parameters frozen once on the full configuration) is the measuring instrument: inputs produced by the pipeline change, the model does not, so every measured difference is attributable to data.

## 2. Frozen scope

| Item | Decision | Rationale |
|---|---|---|
| Source tables | 11 (including `d_member`) | `d_member` is used only for account-exclusion flags and static attributes dated ≤ t |
| Countries | SG, TH, VN — decision 2026-10-28 (issue #54): the three countries covered by the 2026-10-27 Parquet and web-event re-exports; PH and TW exist only in the size-capped CSV export (sales Jan–Oct 2023, no prices, no web events) and are out of scope | Country is a pipeline parameter; the pipeline loops over the three |
| Period | 2023 – 2026, all available data | No time-budget constraint; full history |
| Recommendation unit | `model_code` | SKUs (`item_code`) split by size/colour are too sparse (701 SKUs per 1,000 lines in the sample) |
| Eligible members | ≥ 2 transactions, not flagged as staff / business / legal entity / club / school | Personalisation needs history; non-consumer accounts distort it |
| Candidates | 200 per (member, anchor) | Priority R1 > R3 > R2 > R4 > R5 |
| Label windows | Δ = 30 (primary), 90 (secondary) | Validated against the inter-purchase gap distribution in step 4 |
| Metrics | HR, MRR, NDCG @10 and @20; Recall@50; candidate recall per source; coverage | NDCG@20 drives early stopping |
| Hyper-parameters | Tuned once on **Full**, then frozen for every arm | Isolates the effect of data from the effect of tuning |
| Platform | DuckDB + Parquet + dbt-duckdb; laptop for development, 16-thread / 125 GB / 894 GB NVMe server for the full run (below the Tier 1 sizing of §7; training stays sampled) | Platform-independent SQL; portable to Spark |
| Streaming lane | Optional Redpanda replay for the three event tables, reconciled against batch (QC-7) | Kept as a genuine check, not a demo |

## 3. Data facts established from the samples and confirmed by the team

Re-checked on the whole 2026-10-27 exports and the VN Bronze on 2026-10-28 (issue #6): rows marked *confirmed* or *corrected*.

| Fact | Consequence |
|---|---|
| *Confirmed; refined by the data owner 2026-10-28.* `item_operation_type` ∈ {sale, cancel, return} (89.3 M lines: 97.6 / 0.5 / 2.0 %); a cancelled online order appears as a `sale` line plus a `cancel` line whose amounts net to zero. 9.5 % of the export's lines are exact duplicates and the source table has none: (`transaction_id`, `transaction_num_line`) is unique there, so the duplicates come from overlapping extracts (VN: 11.60 M rows → 10.61 M distinct → 10.60 M line keys; 1,929 keys still carry two rows with different quantity or amount). `transaction_status` is not a filter: a line counts once `gmv_recorded_at` is set (shipped orders are sales, VN 2025: 13 lines) | Exact-row dedup, latest `transaction_version_at` per line key, signed netting per (transaction, item); no `finished` filter |
| Return transactions have `SUM(gmv_amount) < 0` at transaction level | Transaction status = SALE / CANCELLED / RETURN from the net GMV; line-level flags kept for exchanges |
| *Confirmed by the data owner 2026-10-28.* `economical_businessunit_country_code` exists on every sales line and is the transaction country; `member_country_code` (in `d_member`, `f_member_purchase`) is the account-creation country (VN 2025: 2,975 transactions by FR-registered members, plus TH, SG …) | Country key = transaction country everywhere; the member's own country is a profile attribute only |
| `gmv_recorded_at` is local time; `transaction_version_at` is UTC | Keep `transaction_ts_local`; derive UTC through the store timezone |
| *Corrected; confirmed by the data owner 2026-10-28.* `price_type` has four values in the export: STANDARD, DAY_TO_DAY_PROMOTION, END_OF_LINE, DROP; SEASON_SALES never occurs and VN has no DROP. Promotion names live in `sales_detail.price_modifier_detail[].rule` (VN 2025: DiscountCoupon most frequent, then DayToDayPromotion, CommercialGesture, EndOfLine, PricingError, Set, MixAndMatch, Bundle); `type` is only the level (ItemLevelPriceChange, TransactionLevelDiscount, ItemLevelDiscount). Seasonal campaigns (e.g. an XMAS50 code) run through DiscountCoupon and are identifiable by the coupon description | `promo_kind` maps the four price types; discount usage comes from the modifier rules (`modifier_amount` macro); coupon descriptions are a candidate input for naming calendar events (#18) |
| *Corrected by the data owner 2026-10-28.* `business_unit_third_type = 15` is the COUNTRY unit, exactly one per country, and is the national reference price; type 50 are the WEBSITE units (four per country) that repeat the same price row for row (VN: 536,069 keys compared, 0 differ, no key on one side only); type 7 are stores, whose prices also equal the national price (`audit.price_uniformity`, VN gap 0.0) | `slv_price_sku_interval` builds the national timeline from type 15 and falls back to type 50 only for a key without a type-15 row; store prices only when `allow_store_prices` is true |
| SKU price intervals of one model do not align | Do not build model-level intervals; ASOF-join the anchor grid to SKU intervals, then take the median per model |
| *Corrected; confirmed by the data owner 2026-10-28.* In the Parquet exports the nested columns are real `STRUCT` / `LIST<STRUCT>` values: `metadata.user_details.member_id`, `metadata.product_details[].model_code`, `tax_detail[]`, `price_modifier_detail[].{type, rule, amt}`. `_errors` is present on every event and only lists empty optional fields (consent flags, `page_name`); `is_event_to_use` alone decides validity | Struct-path extraction macros; events are filtered on `is_event_to_use` only; consent and page-name fields are not used |
| *Corrected; gap explained by the data owner 2026-10-28.* 33.9 % of the 1.0 bn web events carry a `member_id` (VN sample day 26.8 %); `user_id` is present on every event. The 2023-10 → 2024-04 gap is real absence, not an export loss: VN has no events before 2024-04-27 (Amplitude is the only source; ≈ 3 M events per month from 2024-05), and before 2024-07-01 only Piano / GA3 events are `is_event_to_use = true`, so usable VN web data starts 2024-07 | Two-tier stitching (order-based, login-based ± 90 days); `identity_verified_ts ≤ anchor_date` in Gold; web features are structurally missing for anchors before 2024-08, so `gld_fs_member` carries a `web_data_available` indicator and the web ablation is also read on anchors from 2024-08 (#32, #40) |
| *Explained by the data owner 2026-10-28.* `stock_availability_rate` tracks spare parts only (`availability_type = spare`, global; VN 718 items, 16 sites) and is not an inventory table. Inventory exists in two unexported tables: `stock_pictures` (daily snapshots with `stock_quantity`, `stock_type`, `storage_gln`; VN Oct 2026: 26 of 26 days, 15 stores, ≈ 26.7 k retail items plus a logistics warehouse) and `core_datamart.obt_stock` (`is_available` per store, Dispo_MAG; VN 13 stores, ≈ 28.3 k items, from 2024-06-29, 122 snapshot days ≈ weekly). The owner notes availability stays above 90 % | Decision pending (issue #21): request an export of `obt_stock` (weekly flags, small) and optionally `stock_pictures` for one country and the test period, or drop the stock signal as foreseen in §9; `slv_stock_daily_model` stays blocked until then |
| *New 2026-10-28 (found through the co-purchase lift, issue #31).* The catalogue's retail univers `FIXT & FURNIT` holds store fixtures, carrier bags, printing and POS material (23,095 models); in VN the store paper bag alone is on 447 k sale lines and 13.5 % of baskets contain such an item, so it topped every co-purchase list | Excluded from `slv_dim_model`; the lines go to `quarantine.qrt_sales_line` as `NON_MERCHANDISE` instead of counting as purchases or candidates |
| *Resolved 2026-10-28.* The 2026-10-25 `dim_item` CSV lacked 4,569 VN item codes (14.5 % of stock sale lines). The Parquet re-export of 2026-10-28 (4.36 M items, +517 k) holds 4,356 of them; the 213 still missing are malformed codes (EAN barcodes, `invalid`) on 436 lines, so every well-formed VN SKU sold is in the catalogue | VN gate 2 rises from 84.6–86.5 % to 99.99–100 % and all four years PASS (issue #9); `slv_fact_sales_line` VN grows from 7.57 M to 8.81 M lines; `gender` arrives as a list and is normalised by casting to VARCHAR before the split |

## 4. Layers

| Layer | Content | Key techniques |
|---|---|---|
| Bronze | 11 tables as ZSTD Parquet partitioned by (country, year, month); ingestion metadata; rejects table; data contracts | Partition pruning, projection pushdown, key-type harmonisation |
| Silver | `fact_sales_line`, `fact_returns`, `member_bridge`, `member_profile`, `dim_model`, `price_sku_interval`, `calendar_enriched`, `web_events_clean`, `user_to_member`, `stock_daily_model(_national)`, `member_sport_asof`, `member_store_daily` | Contextual deduplication, schema harmonisation, multi-currency and timezone normalisation, interval and as-of joins, semi-structured parsing, entity resolution, external-source integration, event inference from data |
| Gold | `anchor_grid`, `fs_member`, `fs_model_country`, `fs_pair`, `candidates`, `ranking_dataset` | Point-in-time feature store with `as_of_date` keys, anchor sampling for training, leakage assertions |
| Evaluation | temporal split with purge gaps; fixed ranker; B0 vs Full; two-axis ablation; bootstrap CI; cost profiler; scale test | Cost–benefit table per data source (objective MT3) |

## 5. Quality gates

| Gate | Check | Where | On failure |
|---|---|---|---|
| QC-1 | Null keys = 0 | Bronze→Silver, Silver→Gold | Block |
| QC-2 | Referential integrity ≥ 95 / 60 / 90 % per country | Silver | Block for countries in the main evaluation set; warn otherwise |
| QC-3 | Value domains: `promo_depth ∈ [0, 0.9]`, `price > 0`, `qty > 0` | Silver | Route rows to quarantine |
| QC-4 | Uniqueness after version dedup and after netting; unique (member, model, t) in `fs_pair` | Silver, Gold | Block |
| QC-5 | Volume drift ± 50 % vs 28-day trailing mean | Bronze | Warn |
| QC-6 | Point-in-time: `max(source_ts) ≤ anchor_date` and `identity_verified_ts ≤ anchor_date` | Gold | Block, log to `quarantine.leakage_violations` |
| QC-7 | Batch vs stream reconciliation (rows and hash per day) | Bronze | Report |

## 6. Experiment design

- **Temporal split:** test = last six months minus Δ; validation = two months before test; purge gap of two weeks (Δ = 30) or six weeks (Δ = 90); training = the remainder from 2023-01.
- **Baseline B0:** candidates R1 + R2 + national popularity; features F0 + F2 + F4 (purchase history only).
- **Full:** R1–R5; F0–F5 + sport + stock.
- **Feature axis:** −F1, −F3, −F5, −Stock (replace real stock with an "on sale" proxy), −Sport — each arm switches off the corresponding dbt models so that processing cost is measured, not just columns dropped.
- **Candidate axis:** −R1 … −R5.
- **Co-purchase statistics:** one lift table per country over baskets before `valid_lo` (2025-10-27), so no validation or test label contributes. Training anchors earlier than the cutoff therefore see co-purchase structure from after their own date — a static-statistics approximation accepted because the lift is a candidate source and a feature, not a label, and because the test comparison between arms is unaffected; an anchor-dated variant is listed as a possible extension.
- **Statistics:** member-level bootstrap (≥ 500 resamples), 95 % CI for every metric and for the paired difference Full − arm.
- **Cost:** wall time, peak RSS, output rows and bytes per dbt model, recorded in `audit.pipeline_run_metrics`.
- **Scale test:** Silver→Gold for 1 → 2 → 3 countries (VN → +TH → +SG, smallest first) and for 3 → 12 → 36 months of one country, plus four with/without comparisons (Parquet vs CSV, column projection, ASOF vs daily explode, regex extraction vs row-wise Python).

## 7. Server sizing

| Component | Tier 1 — full pipeline + sampled training | Tier 2 — training on the unsampled pair table |
|---|---|---|
| CPU | 32 vCPU | 64 vCPU |
| RAM | 256 GB | 512 GB – 1 TB |
| Disk | 2 TB NVMe | 4 TB NVMe |
| GPU | Not required | Optional |
| DuckDB | `memory_limit = 200GB`, `threads = 32`, `temp_directory` on NVMe | `memory_limit = 450GB`, `threads = 64` |

Pair-table size ≈ used anchors × 200. Measured on VN (issue #29, 2026-10-28): every eligible member × Monday gives 19.9 M train, 3.0 M validation and 10.0 M test anchors, so a stride alone (one anchor in four for training) would still leave about one billion training pairs. Three rules keep the table near the target: only anchors with a non-returned purchase within the label horizon (90 days) are used, since an anchor without one carries all-zero labels that LambdaRank cannot learn from and HR / MRR / NDCG cannot score (the metrics therefore measure ranking quality given that the member buys again, not purchase propensity); training anchors are thinned by the stride; and a deterministic per-country cap by hash rank (defaults 50,000 train / 15,000 validation / 50,000 test anchors) bounds every split. With three countries that is about 30 M training pairs, 9 M validation pairs and 30 M test pairs; the caps are environment variables so the scale test can raise them.

## 8. Work-breakdown structure

| WBS | Package | Depends on | Owner | Definition of done |
|---|---|---|---|---|
| 0.1 – 0.5 | Probe & profiling | — | Kha | five `audit.*` tables exist; stock and price-reference decisions recorded |
| 1.1 – 1.3 | Bronze batch + contracts | 0.1 | Kha | 11 Parquet tables; source tests pass |
| 1.4 | Streaming lane + QC-7 | 1.1 | Kha | three topics running; reconciliation diff = 0 |
| 2.1 – 2.2 | fact_sales_line, fact_returns, dim_model, member_bridge, member_profile | 1.1 | Mạnh | QC-1, 3, 4 pass; 20 sale/cancel transactions verified by hand |
| 2.3 | price_sku_interval + price at anchor | 2.2, 3.1 | Yến | ≥ 90 % of models priced at the anchor in the main country |
| 2.4 | calendar_enriched | 2.3 | Yến | 3 countries; named commercial events |
| 2.5 | web_events_clean + stitching | 1.1 | Yến | coverage report; `quarantine.identity_conflicts` |
| 2.6 | stock_daily_model | 0.4 | Mạnh | day × model × (site, country) table |
| 2.7 | sport_asof, member_store_daily, account exclusion | 2.1 | Mạnh | as-of state verified for 20 members |
| 3.1 | anchor_grid (+ stride) | 2.1 | Mạnh | anchors per country for train / test |
| 3.2 | fs_member, fs_model_country | 2.1 – 2.7, 3.1 | Yến + Mạnh | QC-6 passes |
| 3.3 | candidates + fs_pair + labels | 3.2 | Mạnh | candidate recall per source; QC-4, QC-6 pass |
| 4.1 | Full ranker + hyper-parameter freeze | 3.3 | Mạnh | `frozen_params.json` committed |
| 4.2 | B0 + 10 ablation arms | 4.1 | all | results × cost table |
| 4.3 | Bootstrap, segments | 4.2 | Yến | CI for every comparison |
| 4.4 | Scale test + technique comparisons | 2.x | Kha | charts and tables |
| 5 | Report, slides, DBeaver + dbt docs demo | all | all | — |

Critical path: 0.1 → 1.1 → 2.1 → 3.1 → 3.3 → 4.1 → 4.2.

## 9. Residual risks

| Risk | Control |
|---|---|
| Regex extraction fails for values containing commas or parentheses | Extract only simple-valued fields (ids, codes, numbers); compare post-extraction null rate with the `null` rate in the raw strings |
| A country fails a gate | Still processed; reported in an appendix; excluded from the headline CI |
| Server not available in time | The laptop run covers the full design on one or two countries |
| Stream lane diverges from batch | QC-7 detects it; batch Bronze remains the source of truth |
| Pair table too large at stride = 1 | Stride = 1 only as a secondary experiment on Tier 2; headline results use stride = 4 plus the label-horizon rule and the per-country anchor caps (§7) |
