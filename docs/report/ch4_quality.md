# 4. Quality evidence

> Every check described here leaves a table in the `audit` or `quarantine` schema, so the evidence can be queried in DBeaver (the
> screenshot list is in `docs/figures/README.md`). Numbers: VN laptop build, 2026-10-28; the server run regenerates the tables for
> SG, TH and VN.

## 4.1 Quality gates (QC-1 … QC-7)

| Gate | Check | Where | On failure |
|---|---|---|---|
| QC-1 | null keys = 0 | Bronze → Silver, Silver → Gold | block |
| QC-2 | referential integrity: member link ≥ 60 %, item match ≥ 95 %, price coverage ≥ 90 % per country | gates table | block for the main evaluation set, warn otherwise |
| QC-3 | value domains: `promo_depth ∈ [0, 0.9]`, `price > 0`, `qty > 0` | Silver | rows routed to quarantine |
| QC-4 | uniqueness after version dedup and after netting; unique (member, model, anchor) in the pair table | Silver, Gold | block |
| QC-5 | volume drift ± 50 % against the 28-day trailing mean | Bronze | warn |
| QC-6 | point in time: `max(source_ts) ≤ anchor_date`, `identity_verified_ts ≤ anchor_date` | Gold | block, logged in `quarantine.leakage_violations` |
| QC-7 | batch vs stream reconciliation (rows and hash per day) | Bronze | report |

QC-1, QC-3 and QC-4 are dbt tests and quarantine models; QC-2 is enforced through the gates below; QC-6 through singular tests and the
ledger (§4.6). QC-5 is specified on the Bronze load metrics and still to be wired (issue #25); QC-7 belongs to the optional streaming
lane (RUNBOOK step 8).

## 4.2 Go / no-go gates per country × year

`make gates` (`sql/gates_by_country.sql`) computes four indicators on deduplicated Bronze sales lines: the share of transactions linked to
a member, the share of stock lines whose SKU is in the catalogue (service lines have no catalogue row by design), the share of sold
models with a price row in the country, and the number of members with at least two transactions. A country × year passes when the
four reach 60 %, 95 %, 90 % and 20,000. With several countries the gates **group** rather than select: PASS countries form the main
evaluation set, REVIEW countries are still processed and reported in an appendix (RUNBOOK step 4).

| Country | Year | Transactions | Member link % | Item match % | Price coverage % | Members ≥ 2 tx | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| VN | 2023 | 802,476 | 60.93 | 99.99 | 99.44 | 97,625 | PASS |
| VN | 2024 | 856,497 | 74.39 | 100.00 | 99.58 | 123,502 | PASS |
| VN | 2025 | 1,038,523 | 73.37 | 100.00 | 99.58 | 150,852 | PASS |
| VN | 2026 | 1,186,902 | 63.50 | 100.00 | 99.82 | 150,457 | PASS |

**(t04)**. Two facts behind the numbers: the item-match gate rose from 84.6 – 86.5 % to 99.99 – 100 % when the complete `dim_item`
arrived (2.2), and the member-link rate, between 61 and 74 % depending on the year, is the gate closest to its threshold — the one to
watch when SG and TH are added. *(Server: add the SG and TH rows and state which countries form the main set.)*

## 4.3 Audit checks that fixed design parameters

`sql/audit_checks.sql` writes four small tables **(t05)**:

- **Stock-table coverage.** 517 of the 31,035 SKUs sold in VN since 2025 appear in `stock_availability_rate` (1.7 %). The owner
  explained that the table tracks spare parts (`availability_type = spare`), not inventory, and that store availability stays above
  90 %. Decision (issue #21): the stock signal is switched off — with availability above 90 % the indicator is constant for more
  than nine pairs in ten and cannot move a top-20 ranking, while a daily inventory export would be the heaviest table of the pipeline.
  The columns remain in the entities as NULL and a flag re-enables everything.
- **Price uniformity.** 35,881,236 store-vs-national (item, start date, price type) pairs in VN with a mean and 95th-percentile relative
  gap of 0.0: the national unit is the reference price and store prices are not loaded (`allow_store_prices: false`).
- **Inter-purchase gaps.** Quartiles of the gap between consecutive purchase days of a member: 19 / 70 / 196 / 397 days (q25 / q50 /
  q75 / q90) over 1,523,746 gaps. The label horizons Δ = 30 and 90 days therefore sit around the first quartile and the median, which
  is what makes the labels neither trivial nor empty; this also justified the 90-day rule for using an anchor (3.6).
- **Date span.** Sales from 2023-01-01 00:09 to 2026-10-26 17:29, from which `split.yml` was filled.

## 4.4 Quarantine instead of silent loss

Rows a model refuses are kept with a reason (RUNBOOK step 5). In VN **(t03, t11)**:

| Table | Rows | Reasons |
|---|---:|---|
| `quarantine.qrt_sales_line` | 1,133,757 | NON_MERCHANDISE 517,802 (45.7 %) · NET_GMV_NONPOSITIVE 312,747 (27.6 %) · TXN_NOT_SALE 156,895 (13.8 %) · SERVICE_LINE 145,735 (12.9 %) · ITEM_NOT_IN_CATALOGUE 557 · NET_QTY_NONPOSITIVE 21 |
| `quarantine.qrt_price_interval` | 312 | DEPTH_GT_0_9 (promotion deeper than 90 % of the reference) |
| `quarantine.slv_identity_conflicts` | 8 | cookie linked to more than one member |
| `quarantine.rejects_<table>` | 46 + 19 + 1 | CSV rows DuckDB could not parse (`d_member`, `dim_item`, events) |
| `quarantine.leakage_violations` | 0 | QC-6 ledger (§4.6) |

The fixtures reason alone explains why the first co-purchase lists were dominated by carrier bags; the 557 uncatalogued rows come from
SKUs absent from the catalogue, chiefly the 213 malformed item codes (2.2).

## 4.5 Identity stitching before and after

`audit.stitching_coverage` gives, per country, the share of web events by identity source: DIRECT (member on the event), STITCHED
(member attached through a cookie link within ± 90 days of its verification) and ANON. In VN, on the laptop's day of events, 26.81 %
of events are DIRECT and stitching adds 7.22 points (34.03 % identified), through 2,644 cookie–member links; 8 cookies with several
members are excluded **(t08)**. The anchor-level view **(t09)** reports how many used anchors actually receive a web signal under the
point-in-time rule; it is the number the web ablation depends on and is to be read from the server run (full click-stream, usable VN
events from 2024-07) together with `web_data_available`, which marks anchors whose 30-day window contains no usable events at all so
that "no activity" and "no data" are not confused.

## 4.6 Point-in-time correctness (QC-6)

Every Gold row carries `last_source_ts`. Five singular leakage tests assert `last_source_ts < anchor_date` for the member, product and
pair entities (`leakage_fs_member`, `leakage_fs_model_country`, `leakage_fs_pair`), that every web-derived pair feature rests on an
event whose attribution was known at the anchor (`leakage_web_identity`) and that stitched events lie inside the ± 90-day window of
their link (`leakage_web_stitched_window`); `copurchase_cutoff_before_validation` checks that the co-purchase statistics stop before
the validation window. `quarantine.leakage_violations` materialises the same predicates with the model name and the rule, so a violation
leaves a trace even after a rerun, and `leakage_violations_empty` requires it to be empty. State on the VN build: all Gold tests pass
and the ledger has 0 rows **(t14)**. The one real violation found during development — online lines shifted by +7 hours by the timezone
bug (3.3) — was caught by these tests before any experiment ran.

## 4.7 dbt tests by layer

| Layer | Models | Tests | Singular |
|---|---:|---:|---:|
| sources (11 Bronze tables + 2 external) | 13 | 48 | 1 |
| staging | 2 | 0 | 0 |
| silver | 15 | 58 | 3 |
| quarantine | 4 | 13 | 1 |
| audit | 2 | 4 | 0 |
| gold | 8 | 59 | 8 |

**(t14)**. Generic tests cover nulls, uniqueness, accepted values and ranges; the thirteen singular ones cover the calendar covering
every sales date, the price timeline (no overlapping intervals per SKU), member-bridge conflicts, the member-link rate, the co-purchase
cutoff, the candidate cap, row preservation between the grid and the product entity, and the six leakage rules of §4.6. Five tests are
set to *warn* rather than block and each is explained in the RUNBOOK: negative `discount_local` values are surcharges (1,291 VN lines),
a missing unit timezone falls back to the country's, duplicate event ids in the raw stream, member-bridge conflicts, and the member-link
rate (QC-2 is enforced by the gates instead).

## 4.8 Inferred commercial events as evidence

The calendar is itself a quality artefact: the inferred events must coincide with real commercial periods for the promotion features to
mean anything. In VN the six dictionary names (mid-year sale, back to school, Singles' Day 11.11, Black Friday, Labour Day, April holiday
sale) cover 16 of the 18 occurrences; the two unnamed peaks last three and five days **(t07)**. The owner's hint that seasonal campaigns
run through coupon codes (`DiscountCoupon` rules with the campaign in the description) is the next source to name the remaining peaks.
