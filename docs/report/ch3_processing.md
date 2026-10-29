# 3. Data processing

> The pipeline is the deliverable (DESIGN §1): a three-tier lakehouse on DuckDB and Parquet, orchestrated with dbt, that turns the
> eleven tables into point-in-time features. This chapter follows the data through Bronze, Silver and Gold and names the technique
> applied at each step; §3.8 maps the techniques to the course topics and §3.9 reports the four with / without measurements.
> Numbers: three-country server build (SG, TH, VN), 2026-10-28, tables in `docs/report/tables/`; §3.9 is still the laptop (VN) measurement.

## 3.1 Architecture and tooling

```
raw CSV + Parquet (11 tables)
  │  ingestion/batch_csv_to_bronze.py            (optional) Redpanda replay of the three event tables
  ▼
BRONZE  ZSTD Parquet, Hive-partitioned (country / year / month); data contracts; rejects → quarantine; load metrics
  │  dbt-duckdb (staging views → silver tables)
  ▼
SILVER  deduplicated and netted sales lines · returns · member bridge and profile · model-level catalogue · SKU price intervals
        holiday + commercial calendar · clean web events + identity stitching · daily stock · sport state · usual store
  │  dbt-duckdb · quality gates QC-1 … QC-6 (tests + quarantine)
  ▼
GOLD    weekly anchor grid · fs_member · fs_model_country · candidates R1–R5 · fs_pair · ranking dataset with labels Δ = 30 / 90
  │  Python
  ▼
EVALUATION  fixed LightGBM LambdaRank · temporal split with purge gaps · B0 vs Full · two-axis ablation · bootstrap CI · cost · scale
```

DuckDB (2.0) executes every transformation as SQL on a single machine; Parquet is the storage format of Bronze and the
`lakehouse.duckdb` file holds Silver and Gold. dbt (1.12, `dbt-duckdb`) gives the dependency graph (`docs/figures/lineage_full.png`,
45 nodes), the tests and the documentation; 31 models are organised in five folders (2 staging views, 15 Silver, 4 quarantine, 2 audit,
8 Gold) **(t14)**. Every `dbt run` appends wall time and rows per model to `audit.pipeline_run_metrics` through an `on-run-end` hook, the
same table the Bronze loader writes, so the cost of each step is a by-product of running it. The laptop (M-series, 8 threads, 15 GB
memory limit) develops on VN; the leased server (16 threads, 125 GB, NVMe) runs the three countries with the same `make` targets.

## 3.2 Bronze — contracts, partitioning, rejects

`ingestion/table_contracts.yml` declares for each table its key, the required columns, the columns cast to `VARCHAR` (join keys) and the
Bronze partition **(t01)**. The loader resolves the raw input per table (`<table>.parquet`, else a directory of parts, else `<table>.csv`),
reads it with DuckDB, applies the casts and writes ZSTD Parquet partitioned by (country, year, month) for the fact tables, so that a
country run and a month window prune files instead of scanning them. CSV rows DuckDB cannot parse (cut rows, embedded delimiters) are
kept in `quarantine.rejects_<table>` instead of being dropped silently: the full load rejects 46 `d_member` and 19 `dim_item` CSV rows
**(t11)**. Two settings matter at scale and were found on the server: the partitioned write buffers rows per thread *and* per partition
before flushing, so the default threshold held a billion-row table in memory and spilled 112 GB; a threshold of 32,768 rows streams it.
The open-file limit is raised in every recipe because 85 member countries × year × month exceed 1,024 files.

Bronze is exposed to dbt as views (`bronze.*`) over the Parquet folders; nothing is copied into the database at this layer.

## 3.3 Silver — one technique per model

| Model | What it does | Technique |
|---|---|---|
| `stg_sales_detail` (view) | projects the 25 needed columns of the 141, casts timestamps, applies the country and date filters as dbt vars | projection pushdown; parameterised filters |
| `slv_sales_line_netted` (ephemeral) | (1) exact-duplicate rows dropped, latest `transaction_version_at` per (transaction, line); (2) `sale − cancel` quantities and amounts netted per (transaction, item); (3) transaction status from the net amount | contextual deduplication; versioned records; signed netting |
| `slv_fact_sales_line` | keeps positive net lines of SALE transactions, in the catalogue, merchandise only; derives `transaction_ts_utc` through the unit's timezone, else the country's; EUR amounts through the export's rate | business filters with reasons; timezone normalisation; multi-currency |
| `qrt_sales_line` | the rows the fact refuses, with one of six reasons **(t03)** | quarantine routing (QC-3 / QC-4) |
| `slv_fact_returns` | return lines, linked to the original transaction when the export gives it | — |
| `slv_member_bridge` | one member per transaction (earliest association); the conflict count is a warn-level test | entity resolution across tables |
| `slv_member_profile` | static attributes dated ≤ t and the non-consumer exclusion flag (staff, business, legal entity, club, school) | account exclusion |
| `slv_dim_model` | SKU → model catalogue; drops marketplace (UUID) items, services and the fixtures univers; normalises the list-typed `gender` | schema harmonisation; semi-structured column |
| `slv_price_sku_interval` | national price timeline per SKU: type-15 country unit first, type 50 as fallback, one interval per start date, `promo_kind` from `price_type`, depth checked | interval construction; reference-price rules; QC-3 to quarantine |
| `slv_calendar_enriched` | public holidays (self-built) and commercial events inferred from the promotion share (§3.4) | external-source integration; event inference |
| `slv_web_events_clean` | one row per event; struct paths flattened; product codes kept as a list and filtered to numeric codes; `is_event_to_use`; marketplace removed | semi-structured parsing (STRUCT / LIST) |
| `slv_user_to_member`, `slv_identity_conflicts` | cookie → member stitching (§3.5), conflicts quarantined | identity resolution |
| `slv_stock_daily_model`, `_national` | stock per model × site × day with ≤ 3-day forward fill (kept behind `use_stock`) | gap filling on a time grid |
| `slv_member_sport_asof` | favourite-sport validity intervals from add / remove events | event → state intervals |
| `slv_member_store_daily` | running usual store per member per purchase day | as-of state table |

**Deduplication and netting evidence.** 69,699 SG, 35,861 TH and 41,581 VN transactions contain both a sale and a cancel line; after
netting 13,547, 1,449 and 4,529 of them keep at least one positive line and no kept line has a non-positive quantity or amount **(t18)**
— the manual 20-transaction check of RUNBOOK step 5, automated. The quarantine is dominated by non-merchandise (SG 39.3 %, TH 30.3 %,
VN 45.7 %), by lines whose net amount is zero or negative (33.8 %, 44.7 %, 27.6 %: the cancelled orders) and by transactions
classified as non-sale (16.1 %, 8.7 %, 13.8 %) **(t03)**.

**Timezone.** The online channel has 2,828,396 SG, 1,822,582 TH and 1,559,629 VN sale lines from 26, 36 and 16 website units;
1,911,963 of them (30.2 %, 52.8 % and 6.1 %) belong to units without a timezone and fall back to the country's **(t15)**. Reading those local clocks as UTC had shifted them by seven hours and produced five
point-in-time failures in Gold; the derivation `timezone('UTC', timezone(zone, local_ts))` yields a naive UTC value that no longer
depends on the machine's clock, and the dbt profile pins the session to UTC.

**Prices.** The 42.4 M price rows (SG 14.4 M, TH 16.8 M, VN 11.3 M) contain 591,633 / 362,172 / 536,069 country-unit rows and
1.6 – 2.5 M website rows per country that repeat them; the national timeline keeps 563,721 / 362,140 / 535,805 intervals for
187,055 / 165,748 / 115,541 SKUs — in VN 392,786 STANDARD, 126,286 END_OF_LINE (clearance), 16,733 DAY_TO_DAY_PROMOTION and none of
type DROP, which exists only in SG and TH (9,470 and 3,754 intervals) — with 3.1 – 4.7 % of intervals being temporary promotions;
540 / 266 / 312 intervals deeper than 90 % are quarantined **(t06)**. Intervals of
the SKUs of one model do not align, so the price of a model at a date is computed in Gold by an ASOF join on SKU intervals followed by
a median (DESIGN §3); the `EXPLAIN ANALYZE` of that lookup is in `docs/figures/explain_analyze_asof_price.txt`.

## 3.4 Self-built source: holidays and inferred commercial events

No calendar of commercial events was exported, so one is inferred from the data (RUNBOOK step 5, `slv_calendar_enriched`). For each
country and day the share of SKUs on a temporary promotion among SKUs with a standard price in force is computed with a difference
array (+1 at each interval start, −1 the day after its end, running sum) — O(intervals + days) where the day × interval join produced
170 M intermediate rows and ran out of memory. A day is a peak when the share exceeds the trailing 60-day mean by 1.5 standard
deviations and at least 0.2 % of SKUs are on promotion; three or more consecutive peak days form an event. Events are named by
overlap with a small dictionary the team maintains after looking at the peaks (`ingestion/commercial_event_names.csv`), otherwise
labelled `EVENT_n`. Public holidays come from the `holidays` library (`make holidays`, 53 SG, 106 TH and 58 VN days over 2023 – 2026).

In VN the method finds 18 event occurrences covering 225 days, eight distinct names, six of them from the dictionary — mid-year sale
(five occurrences), back to school, Singles' Day, Black Friday, Labour Day, April holiday sale — and two unnamed peaks of three to
five days; in SG it finds 23 occurrences (275 days) and in TH 14 (277 days). After the SG / TH naming pass (issue #18) the dictionary
covers 11 of the 23 SG occurrences (mid-year sale ×5, Singles' Day ×3, Lunar New Year sale ×2, Labour Day) and 7 of the 14 TH
occurrences (mid-year sale ×3, Lunar New Year sale, Singles' Day, Black Friday, Songkran sale); the other 12 SG and 7 TH peaks, almost
all single occurrences, stay `EVENT_n` until the data owner names them **(t07, t07b)**. The promotion share itself stays low (mean 0.35 % in VN, 1.1 % in SG and TH;
maximum 2.2 – 2.5 %), which is why the floor is needed. The
calendar feeds three features (in commercial event, days to the next public holiday, country promotion share) and the seasonality
index.

## 3.5 Self-built source: identity stitching of web events

Only part of the click-stream carries a member identifier; every event carries the cookie / app `user_id`. Stitching links a cookie to
a member in two tiers (`slv_user_member_links` → `slv_user_to_member`): ORDER — the web order id carried by the event matches the
purchase-order id of an online sales line, whose member comes from the member bridge — and LOGIN — the cookie was seen with a member id
on an event. Each link carries an `identity_verified_ts`, the earliest moment the link was known; a cookie linked to several members is
quarantined (`slv_identity_conflicts`) and only cookies with exactly one member are kept. In Gold, an event is
attributed to a member only within ± 90 days of that timestamp (`gld_web_stitched`, `id_source` DIRECT or STITCHED) and the features
use an event only when the link was known at the anchor (`identity_verified_ts ≤ anchor_date`) — the point-in-time rule the leakage
tests check.

Over the full click-stream, 36.1 % of SG events, 33.7 % of TH events and 29.9 % of VN events carry a member directly, and stitching
adds 5.8, 6.3 and 7.6 points (42.0 %, 40.0 % and 37.6 % identified), through 274,979 / 212,098 / 203,167 cookie–member links whose member account is in SG / TH / VN (1,295,225 over every account
country); 945 cookies linked to
several members are excluded **(t08)**. At anchor level — the share of used anchors whose member has an attributed event in the 30 days
before, known at the anchor **(t09)** — the test anchors reach 18.8 % in SG, 5.5 % in TH and 7.3 % in VN, the training anchors 5.1 %,
1.8 % and 3.6 % because most of them precede the start of the click-stream (TH 2023-04, usable VN events 2024-07); the
`web_data_available` indicator marks the 48,989 TH and 33,050 VN training anchors whose 30-day window contains usable events, so that
"no activity" and "no data" stay apart.

## 3.6 Gold — point-in-time feature store (overview; details in chapter 5)

The unit of prediction is (member, anchor date). `evaluation/build_anchor_grid.py` places an anchor on every Monday after a member's
second transaction inside the train / validation / test windows of `evaluation/split.yml` (train 2023-01-02 → 2025-09-15, validation
2025-10-27 → 2025-12-22, test 2026-02-02 → 2026-07-27, purge gaps of 42 days). Three rules bound the grid: an anchor is used only when
a non-returned purchase follows within 90 days (an anchor without one has all-zero labels), training anchors are thinned by a stride
of four, and a deterministic per-country cap by hash rank keeps 50,000 / 15,000 / 50,000 anchors. Over the three countries this takes
143.6 M training anchors (SG 57.9 M, TH 65.4 M, VN 20.3 M) to 46.9 M with a purchase, 11.7 M after the stride and 3 × 50,000 used;
59.4 M test anchors to 15.3 M and 3 × 50,000 **(t10)**.

Three feature entities are built for the used anchors — member (`gld_fs_member`), model × country (`gld_fs_model_country`) and the
member–candidate pair (`gld_fs_pair`) — each reading only data strictly before the anchor and carrying `last_source_ts`, the latest
source timestamp that fed the row. Candidates come from five sources (repurchase, co-purchase partners, web intent, sport × offer,
national best-sellers), capped at 200 per anchor; labels are the non-returned purchases within 30 and 90 days. Six singular tests
(`tests/leakage_*.sql`) assert the point-in-time rules and a ledger (`quarantine.leakage_violations`) materialises any violation with
the model and rule — it has 0 rows **(t14)**. Chapter 5 describes the entities, the candidate sources and their recall **(t12)**.

## 3.7 Orchestration and reproducibility

`make bronze → gates → silver → gold → train → ablation` runs the whole chain; `.env` holds the paths, the country filter, the DuckDB
memory and thread limits and the anchor caps, so the same repository runs on the laptop and on the server. Raw-file checksums
(`data/raw_csv_md5.txt`) and the two probe reports are committed; data never is. dbt tests run after every layer; a failing block test
stops the chain, warnings are explained in the RUNBOOK. The optional streaming lane (Redpanda replay of the three event tables with a
consumer that applies the same contracts and a dead-letter queue) is reconciled against batch Bronze per day (QC-7).

## 3.8 Techniques mapped to course topics

The mapping below uses the topic names of the course outline as the team understood them; the instructor's wording should be
substituted where it differs.

| Course topic | Where it is applied in the pipeline | Evidence |
|---|---|---|
| Data ingestion, file formats and storage layout | CSV and Parquet readers; ZSTD Parquet; Hive partitioning by (country, year, month); partition pruning and projection pushdown | **(t01)**; Parquet vs CSV 6.6× and projection 6.7× **(t13)** |
| Data contracts and schema management | `table_contracts.yml`: keys, required columns, key casts; dbt source tests (48) | **(t14)** |
| Data profiling and quality assessment | the two probes; four go / no-go gates per country × year; five audit tables | **(t04, t05)**, chapter 4 |
| Cleaning: deduplication, versioning, netting | exact-row dedup, latest version per key, sale − cancel netting; quarantine with reasons | **(t02, t03, t18)** |
| Data integration and entity resolution | member bridge across transactions and members; cookie → member identity stitching with validity windows | **(t08, t09, t17)** |
| Schema and value harmonisation | key casts, model-level catalogue, four price types to `promo_kind`, list-typed `gender`, currency conversion | §3.3 |
| Temporal data: time zones, intervals, as-of joins | local → UTC through the unit or country zone; SKU price intervals; ASOF joins for price, usual store, sport state, department state | **(t15)**, ASOF vs daily explode 1.3× and half the memory **(t13)** |
| Semi-structured data | STRUCT / LIST paths in Parquet, `Map(k -> v)` strings in CSV, regex extraction; `is_event_to_use` | SQL regex vs row-wise Python 2.9× **(t13)** |
| External-source integration and data enrichment | public holidays (library), commercial events inferred from the promotion share and named by a dictionary | **(t07, t07b)** |
| Feature engineering with point-in-time correctness | anchor grid, `last_source_ts`, `identity_verified_ts`, leakage tests and ledger | **(t10, t14)** |
| Testing and data observability | 182 dbt tests in five layers, quarantine tables, run metrics per model, cost profiler | **(t14, t19)** |
| Performance and scalability | memory-bounded SQL (difference array, pre-aggregation, ASOF), partitioned write tuning, scale test over countries and months | **(t13)**, chapter 5 |
| Stream processing (optional lane) | Redpanda replay and consumer with contract checks; batch vs stream reconciliation (QC-7) | RUNBOOK step 8 |
| Experimental method on data | fixed ranker as instrument; two-axis ablation; bootstrap CI; cost × gain table | chapter 5 |

## 3.9 With / without comparisons of four techniques

`evaluation/technique_comparisons.py` (`make techniques`) measures four techniques against their naive alternative on VN, each
variant in a fresh child process, three repetitions, median wall time and peak resident memory **(t13)**:

| Comparison | Baseline → technique | Rows | Wall time | Peak memory |
|---|---|---:|---|---|
| Parquet vs CSV | the same GROUP BY aggregate over an extract of the VN sales lines, read from CSV → from Parquet | 124 result groups | 0.36 s → 0.05 s (6.6×) | 0.46 GB → ≈ 0 |
| Column projection | materialise the VN 2025 sales lines from the raw Parquet with all 141 columns → with the 25 staged columns | 2.8 M lines | 3.41 s → 0.51 s (6.7×) | 5.73 → 1.65 GB |
| ASOF join vs daily explode | price of every priced SKU at every anchor Monday: explode the intervals to days and equi-join → ASOF join | 14.9 M lookups | 1.02 s → 0.77 s (1.3×) | 2.82 → 1.47 GB |
| SQL regex vs row-wise Python | extract member, user and order ids from the JSON metadata string of the VN events: Python `re` per row → `regexp_extract` in SQL | 589 k values | 1.50 s → 0.51 s (2.9×) | 3.05 → 1.15 GB |

The native STRUCT path of the Parquet export (reference variant) reads the same member ids in 0.01 s, which is why the pipeline extracts
by struct path and keeps the regex only for the CSV-era `Map` strings. The server rerun on the three countries replaces this table.
