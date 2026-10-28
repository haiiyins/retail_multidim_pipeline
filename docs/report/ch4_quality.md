# 4. Quality evidence

> Every check described here leaves a table in the `audit` or `quarantine` schema, so the evidence can be queried in DBeaver (the
> screenshot list is in `docs/figures/README.md`). Numbers: three-country server build (SG, TH, VN), 2026-10-28.

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
ledger (§4.6); QC-5 is the `audit.volume_drift` table of §4.8; QC-7 belongs to the optional streaming lane (RUNBOOK step 8).

## 4.2 Go / no-go gates per country × year

`make gates` (`sql/gates_by_country.sql`) computes four indicators on deduplicated Bronze sales lines: the share of transactions linked to
a member, the share of stock lines whose SKU is in the catalogue (service lines have no catalogue row by design), the share of sold
models with a price row in the country, and the number of members with at least two transactions. A country × year passes when the
four reach 60 %, 95 %, 90 % and 20,000. With several countries the gates **group** rather than select: PASS countries form the main
evaluation set, REVIEW countries are still processed and reported in an appendix (RUNBOOK step 4).

| Country | Year | Transactions | Member link % | Item match % | Price coverage % | Members ≥ 2 tx | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| SG | 2023 | 3,660,077 | 50.31 | 99.98 | 97.70 | 357,508 | REVIEW |
| SG | 2024 | 3,479,489 | 57.88 | 99.98 | 97.79 | 399,334 | REVIEW |
| SG | 2025 | 3,724,870 | 63.84 | 99.98 | 98.63 | 467,378 | PASS |
| SG | 2026 | 3,258,422 | 59.25 | 99.93 | 98.65 | 395,884 | REVIEW |
| TH | 2023 | 1,953,182 | 85.83 | 100.00 | 99.19 | 352,835 | PASS |
| TH | 2024 | 2,078,660 | 99.84 | 100.00 | 99.23 | 421,683 | PASS |
| TH | 2025 | 2,328,078 | 95.35 | 99.99 | 99.14 | 446,894 | PASS |
| TH | 2026 | 2,580,880 | 87.03 | 100.00 | 98.97 | 454,414 | PASS |
| VN | 2023 | 802,476 | 61.76 | 99.99 | 99.44 | 98,698 | PASS |
| VN | 2024 | 856,497 | 76.41 | 100.00 | 99.58 | 125,849 | PASS |
| VN | 2025 | 1,038,523 | 74.83 | 100.00 | 99.58 | 153,569 | PASS |
| VN | 2026 | 1,186,902 | 64.87 | 100.00 | 99.82 | 153,517 | PASS |

**(t04)**. TH and VN pass every year; SG passes 2025 only and misses the member-link gate in 2023, 2024 and 2026 (50.3, 57.9 and
59.3 %), while its item match and price coverage are as high as the others'. The item-match gate rose from 84.6 – 86.5 % to
99.93 – 100 % when the complete `dim_item` arrived (2.2). Decision (RUNBOOK step 4, to be confirmed by the team): the **main evaluation
set is TH + VN**; SG is processed in full and reported as a REVIEW country next to them. The reason is label quality, not size: the
repurchase labels exist only for member-linked transactions, so when half of the SG transactions carry no member, half of the
repurchases are invisible to the label and the SG metrics are biased downwards; with 358 – 467 k members holding two transactions or
more, SG is far above the fourth gate and its results remain reportable. Compared with the single-country build, the VN member-link
rate is 0.8 – 2.0 points higher here because the member bridge now holds all 85 account countries, so members registered abroad who
buy in VN are linked too.

## 4.3 Audit checks that fixed design parameters

`sql/audit_checks.sql` writes four small tables **(t05)**:

- **Stock-table coverage.** 709 of the 42,236 SKUs sold in SG since 2025, 664 of 33,980 in TH and 517 of 31,035 in VN appear in
  `stock_availability_rate` (1.7 – 2.0 %). The owner
  explained that the table tracks spare parts (`availability_type = spare`), not inventory, and that store availability stays above
  90 %. Decision (issue #21): the stock signal is switched off — with availability above 90 % the indicator is constant for more
  than nine pairs in ten and cannot move a top-20 ranking, while a daily inventory export would be the heaviest table of the pipeline.
  The columns remain in the entities as NULL and a flag re-enables everything.
- **Price uniformity.** 49.8 M store-vs-national (item, start date, price type) pairs in SG, 93.2 M in TH and 35.9 M in VN with a mean
  relative gap of 0.0 (TH 0.0001) and a 95th percentile of 0.0: the national unit is the reference price and store prices are not loaded (`allow_store_prices: false`).
- **Inter-purchase gaps.** Quartiles of the gap between consecutive purchase days of a member (q25 / q50 / q75 / q90): SG 14 / 47 /
  126 / 267 days over 6.29 M gaps, TH 17 / 62 / 171 / 357 over 5.31 M, VN 19 / 69 / 195 / 395 over 1.55 M. The label horizons Δ = 30
  and 90 days therefore sit between the first quartile and the median in every country, which is what makes the labels neither
  trivial nor empty; this also justified the 90-day rule for using an anchor (3.6).
- **Date span.** Sales from 2023-01-01 to 2026-10-26 in the three countries (first VN line at 00:09, last SG line at 18:29), from
  which `split.yml` was filled.

## 4.4 Quarantine instead of silent loss

Rows a model refuses are kept with a reason (RUNBOOK step 5). Over the three countries **(t03, t11)**:

| Table | Rows | Reasons |
|---|---:|---|
| `quarantine.qrt_sales_line` | 5,584,701 | SG 2,857,657: NON_MERCHANDISE 39.3 % · NET_GMV_NONPOSITIVE 33.8 % · TXN_NOT_SALE 16.1 % · SERVICE_LINE 9.9 % · ITEM_NOT_IN_CATALOGUE 23,886 rows — TH 1,593,287: NET_GMV_NONPOSITIVE 44.7 % · NON_MERCHANDISE 30.3 % · SERVICE_LINE 16.1 % · TXN_NOT_SALE 8.7 % · ITEM_NOT_IN_CATALOGUE 3,320 — VN 1,133,757: NON_MERCHANDISE 45.7 % · NET_GMV_NONPOSITIVE 27.6 % · TXN_NOT_SALE 13.8 % · SERVICE_LINE 12.9 % · ITEM_NOT_IN_CATALOGUE 557 — NET_QTY_NONPOSITIVE 26 rows in all |
| `quarantine.qrt_price_interval` | 1,118 | DEPTH_GT_0_9 (promotion deeper than 90 % of the reference): SG 540, TH 266, VN 312 |
| `quarantine.slv_identity_conflicts` | 945 | cookie linked to more than one member |
| `quarantine.rejects_<table>` | 46 + 19 | CSV rows DuckDB could not parse (`d_member`, `dim_item`) |
| `quarantine.leakage_violations` | 0 | QC-6 ledger (§4.6) |

The fixtures reason alone explains why the first co-purchase lists were dominated by carrier bags. Uncatalogued rows follow the SKU
coverage of 2.2: 0.84 % of the SG quarantine (23,886 rows; 96.1 % of the SKUs sold in SG are in the catalogue) against 0.21 % in TH and
0.05 % in VN, where the 557 rows are chiefly the 213 malformed item codes.

## 4.5 Identity stitching before and after

`audit.stitching_coverage` gives, per country, the share of web events by identity source: DIRECT (member on the event), STITCHED
(member attached through a cookie link within ± 90 days of its verification) and ANON. Over the full click-stream, 36.14 % of SG
events, 33.65 % of TH events and 29.94 % of VN events are DIRECT and stitching adds 5.83, 6.33 and 7.62 points (41.97 %, 39.98 % and
37.56 % identified), through 1,295,225 cookie–member links; 945 cookies linked to several members are excluded **(t08)**. The
anchor-level view **(t09)** reports how many used anchors actually receive a web signal under the point-in-time rule: 18.76 % of the
SG test anchors, 5.52 % in TH and 7.30 % in VN have an attributed event in the 30 days before the anchor, against 5.08 %, 1.79 % and
3.61 % of the training anchors, most of which precede the start of the click-stream (TH 2023-04-26, usable VN events 2024-07-01).
`web_data_available` separates the two situations: 48,989 of the 50,000 TH training anchors and 33,050 of the VN ones have usable
events somewhere in their window, the others have no data at all, so that "no activity" and "no data" are not confused. This is the
number the web ablation (chapter 5) must be read against.

## 4.6 Point-in-time correctness (QC-6)

Every Gold row carries `last_source_ts`. Five singular leakage tests assert `last_source_ts < anchor_date` for the member, product and
pair entities (`leakage_fs_member`, `leakage_fs_model_country`, `leakage_fs_pair`), that every web-derived pair feature rests on an
event whose attribution was known at the anchor (`leakage_web_identity`) and that stitched events lie inside the ± 90-day window of
their link (`leakage_web_stitched_window`); `copurchase_cutoff_before_validation` checks that the co-purchase statistics stop before
the validation window. `quarantine.leakage_violations` materialises the same predicates with the model name and the rule, so a violation
leaves a trace even after a rerun, and `leakage_violations_empty` requires it to be empty. State on the three-country build: the 10 Gold-stage
models pass their 64 tests and the ledger has 0 rows **(t14)**. The one real violation found during development — online lines shifted by +7 hours by the timezone
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
cutoff, the candidate cap, row preservation between the grid and the product entity, and the six leakage rules of §4.6. Six tests are
set to *warn* rather than block and each is explained in the RUNBOOK: negative `discount_local` values are surcharges (2,506 lines in the
three countries), a missing unit timezone falls back to the country's (1,911,963 online lines, t15), duplicate event ids in the raw
stream, member-bridge conflicts, the member-link rate (QC-2 is enforced by the gates instead) and, since the full load,
`f_member_purchase.member_id` (1,469,179 associations without a member, 96 % of them in 2026).

## 4.8 Volume drift (QC-5)

`make gates` also writes `audit.volume_drift`: rows per day of `sales_detail` and `tracking_ecom_events`, per country, on the full
calendar grid so that a day without rows counts as zero, compared with the trailing 28-day mean **of the same weekday**. The weekday
restriction matters: Saturdays and Sundays carry up to 1.8 times a weekday's lines, so a plain 28-day mean flagged 221 VN days, 180 of
them weekends; the same-weekday baseline flags 48 SG, 51 TH and 69 VN sales days out of 1,395 (3.4 – 4.9 %) **(t20)**. Each flagged day
carries a probable cause derived from the holiday table and simple calendar rules, as a hint for the review **(t20b)**: public holidays
(26, 29 and 31 holiday-related days; in VN the four days of Tết at −58 to −94 % every year, Hung Kings', Reunification, Labour and
National Day at +65 to +146 %), the e-commerce double days (SG 2, TH 6, VN 12), Black Friday, days whose baseline contained a holiday,
and 17, 11 and 14 days left unexplained.

Eleven, ten and ten of those unexplained days are the same dates in the three countries — 1 to 13 October 2023 at +51 to +114 % —
which rules out a commercial cause. The Bronze rows of those days are export duplicates: in VN the raw rows are 1.6 to 2.0 times the
distinct (transaction, line, version) keys from 1 October 2023 onwards while the last week of September is exactly 1.0, the same factor
the whole of January – March and October – December 2023 carry (the 9.5 % exact duplicates of 2.2). The check therefore did its job —
it caught an export artefact that the Silver deduplication removes — and is being extended to report raw rows and distinct line keys
side by side with a `DUPLICATED_EXPORT` cause *(next revision of `audit_checks.sql`; the server regenerates t20 / t20b after the
experiments)*. That leaves 6, 1 and 4 unexplained sales days: 24 April 2023 and five weekdays after the end-of-year peak of 2023 in SG,
28 March 2025 in TH, and in VN 1 June 2023 (Children's Day, not a public holiday), two weekdays after the end-of-year peak and Saturday
7 September 2024 (−55 %, the day typhoon Yagi made landfall in northern Vietnam). No sales day has zero rows in any country.

The web-event series behaves differently **(t20, t20b)**. SG has 86 days without any event and TH 29, all between late November 2023
and April 2024: the known 2023-10 → 2024-04 absence is not a clean hole but a fade-out — SG and TH volumes fall to near zero through
October and November 2023 (41 and 35 unexplained days at −71 to −100 % on average), then empty and near-empty days alternate from
December (SG 2023-12-22 → 2024-01-08 and 2024-02-03 → 18 without a single event, TH 2024-03-23 → 04-06) until the stream is back in
late April (TH) and early May (SG) 2024, days the check labels AFTER_GAP while the baseline refills. VN starts on 2024-04-27 and has no
empty day. Outside the gap, 13 SG and 15 TH days in February 2025 run at +90 to +104 % together — a tracking-side change rather than
traffic, to be asked of the data owner — and the other unexplained web days (SG 23, TH 19, VN 19) are scattered, half of them in the
tail of the fade-out (December 2023 – January 2024). The check is warn-level: it documents, it does not block.

## 4.9 Inferred commercial events as evidence

The calendar is itself a quality artefact: the inferred events must coincide with real commercial periods for the promotion features to
mean anything. In VN the six dictionary names (mid-year sale, back to school, Singles' Day 11.11, Black Friday, Labour Day, April holiday
sale) cover 16 of the 18 occurrences and the two unnamed peaks last three and five days; the 23 SG and 14 TH events are all unnamed
because the dictionary was written from the VN peaks — their dates (SG 2024-11-06 → 21 and 2025-10-30 → 11-18, TH 2025-10-30 → 11-17,
TH 2023-09-14 → 10-20 over 37 days) point to the same Singles' Day and year-end campaigns and are to be named in the dictionary
(issue #18) **(t07)**. The owner's hint that seasonal campaigns
run through coupon codes (`DiscountCoupon` rules with the campaign in the description) is the next source to name the remaining peaks.
