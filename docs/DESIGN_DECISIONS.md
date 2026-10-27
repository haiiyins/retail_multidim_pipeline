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
| Platform | DuckDB + Parquet + dbt-duckdb; laptop for development, 32 vCPU / 256 GB server for the full run | Platform-independent SQL; portable to Spark |
| Streaming lane | Optional Redpanda replay for the three event tables, reconciled against batch (QC-7) | Kept as a genuine check, not a demo |

## 3. Data facts established from the samples and confirmed by the team

| Fact | Consequence |
|---|---|
| `item_operation_type` ∈ {sale, cancel, return}; a cancelled online order appears as a `sale` line plus a `cancel` line whose amounts net to zero | Version dedup on (`transaction_id`, `transaction_num_line`, `transaction_version_at`), then net sale–cancel pairs on (`transaction_id`, `item_code`) |
| Return transactions have `SUM(gmv_amount) < 0` at transaction level | Transaction status = SALE / CANCELLED / RETURN from the net GMV; line-level flags kept for exchanges |
| `economical_businessunit_country_code` exists on every sales line | Used as the country key; `dim_business_unit` is joined only for store name, timezone and region |
| `gmv_recorded_at` is local time; `transaction_version_at` is UTC | Keep `transaction_ts_local`; derive UTC through the store timezone |
| `price_type` has five values: STANDARD, DAY_TO_DAY_PROMOTION, SEASON_SALES, END_OF_LINE, DROP | `promo_kind` with five levels; `is_temp_promo` = DAILY or SEASONAL; DROP is a permanent price change (F1), not a promotion |
| Website business unit (`business_unit_third_type = 50`) carries the national reference price | Filter it first; allow store prices only if audit shows large gaps |
| SKU price intervals of one model do not align | Do not build model-level intervals; ASOF-join the anchor grid to SKU intervals, then take the median per model |
| The nested columns `metadata`, `tax_detail`, `price_modifier_detail` are Spark toString `Map(k -> v)` strings in the CSV | Extract the few needed fields with regular expressions; do not parse the full structure |
| Only 15.6 % of web events carry a `member_id` | Two-tier stitching (order-based, login-based ± 90 days); a cookie mapping to more than one member is excluded; `identity_verified_ts ≤ anchor_date` is enforced in Gold |
| `availability_type` is always `spare`, yet the stock table covers ≈ 100 % of sold items | The value is a default label of the technical job; use the stock table as designed and ignore the filter |

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

Pair-table size ≈ members × anchors per member per year × 200. With a stride of one anchor every four weeks the training table stays within tens of millions of rows; the evaluation set uses every weekly anchor.

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
| Pair table too large at stride = 1 | Stride = 1 only as a secondary experiment on Tier 2; headline results use stride = 4 |
