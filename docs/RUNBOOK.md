# Runbook — step-by-step implementation

Nine steps. Each step lists the commands to run, the files involved, how to verify, and a **definition of done (DoD)**. Do not move to the next step before the DoD is met. Design rationale is in `DESIGN_DECISIONS.md`.

Conventions: `$ROOT` is the repository root; commands assume the virtual environment is active; SQL is DuckDB SQL; files under `dbt_multidim/models/` are dbt models (Jinja allowed).

| Step | Name | Main output |
|---|---|---|
| 1 | Environment | repo, venv, `.env`, `profiles.yml`, DBeaver connection |
| 2 | CSV profiling | `data/audit/csv_profile.md`, the country codes, nested-column format |
| 3 | Bronze | 11 partitioned Parquet tables + `bronze.*` views + rejects |
| 4 | Gates & audit | `audit.gates_by_country`, stock coverage, price uniformity, inter-purchase gaps, date span |
| 5 | Silver (dbt) | 13 Silver models, tests passing |
| 6 | Gold (dbt + Python) | anchor grid, three feature entities, candidates, labels, leakage tests passing |
| 7 | Experiments | B0 / Full / 10 ablation arms, CI, cost, scale test |
| 8 | Streaming lane (optional) | Redpanda, consumer, QC-7 reconciliation |
| 9 | Packaging | dbt docs, result tables, submission checklist |

---

## Step 1 — Environment

### 1.1 Machines

| | Laptop (development, one country) | Server (all three countries, Gold, experiments) |
|---|---|---|
| CPU / RAM | 8 cores / 16 GB | 16 threads / 125 GB (≈ 100 GB free for DuckDB) |
| Free disk | ≥ 150 GB | 894 GB NVMe (raw set ≈ 230 GB) |
| OS | macOS / Ubuntu | Linux |
| DuckDB | `DUCKDB_MEMORY=10GB`, `DUCKDB_THREADS=6` | `DUCKDB_MEMORY=80GB`, `DUCKDB_THREADS=16` |
| dbt concurrency | `DBT_THREADS=4` | `DBT_THREADS=1` — concurrent models share one DuckDB; 16 of them starved each other (Appendix B) |

### 1.2 Data download

The Drive folder must be shared as *Anyone with the link → Viewer*, otherwise `gdown` gets HTTP 401. The ten single-file tables are about 27 GB (the largest, `sales_detail.parquet`, 12.2 GB); the web-event table adds about 200 GB as 1,774 Parquet parts, so download it on the server only and keep a few parts on the laptop. Expect hours for the files and a day or more for the web events, depending on the connection.

```bash
mkdir -p data/raw_csv && cd data/raw_csv
# --continue resumes .part files and skips files already present; --timeout avoids hanging on a dead connection
caffeinate -i gdown --continue --retries 20 --timeout 60 "<TEAM_DRIVE_FOLDER_LINK>"   # drop caffeinate on Linux
# gdown recreates the Drive sub-folder ("Raw data/"); flatten it and rename to plain table names
mv "Raw data"/* . && rmdir "Raw data"
for f in *.csv *.parquet; do [ -e "$f" ] && mv "$f" "$(echo "$f" | sed -E 's/ — .*\.(csv|parquet)$/.\1/')"; done
ls -la          # 11 files expected: sales_detail.parquet … d_member.csv (Parquet for the 4 re-exported tables, CSV for the rest)
md5sum *.csv *.parquet > ../raw_csv_md5.txt
```

Run exactly one `gdown` at a time: two copies resuming the same `.part` file corrupt it silently. If a download has to be restarted, check with `ps -axo pid,command | grep gdown` that no copy is still running. Before trusting a file, compare its size with the exact byte count Drive reports:

```bash
curl -sIL -r 0-0 -b ~/.cache/gdown/cookies.txt \
  "https://drive.usercontent.google.com/download?id=<FILE_ID>&export=download&confirm=t" | grep -i content-range
```

If `gdown` keeps failing on a large file, use `rclone` with a Google Drive remote or download through the browser.

**Chunked tables.** A table may arrive as a Drive sub-folder of Spark parts (`part-*.snappy.parquet`; 2026-10-27: `Tracking Ecom Event`, about 1,800 daily files of 110–155 MB, many uploaded twice under the same name). `gdown` downloads the sub-folder recursively and skips a second copy with the same name, so the local directory holds each part once; move it to `data/raw_csv/tracking_ecom_events/` (plain table name) and the loader and probes read `<table>/*.parquet`. Verify the directory with `ls | wc -l` against the number of distinct names on Drive and `md5sum tracking_ecom_events/*.parquet` for the checksum file.

**Re-exports.** When the team re-exports a table in a new format (2026-10-27: `sales_detail`, `sales_tender_detail`, `f_member_purchase`, `all_store_selling_price` arrived as Parquet; 2026-10-28: the complete `dim_item`, 4.36 M items, with `gender` as a list column), download only the new files and move the superseded file to `data/raw_csv/superseded_<YYYY-MM-DD>/` (ignored by git, kept for reconciliation) so that exactly one file per table remains in `data/raw_csv/`; the loader and both probes prefer `<table>.parquet` over `<table>.csv` only as a safety net. Then recompute `md5sum *.csv *.parquet > ../raw_csv_md5.txt`, rerun `make probe` and `make probe-full`, and commit the checksum file and both reports in the same PR. A machine that already holds Bronze reloads only the re-exported table — `BRONZE_TABLES=dim_item make bronze` (comma-separated list) — and then reruns gates and Silver.

### 1.3 Python environment

```bash
python3.11 -m venv .venv && source .venv/bin/activate
# or, if the python3.11 binary is not installed: uv venv --python 3.11 .venv
pip install -r requirements.txt
```

### 1.4 Configuration

- Copy `.env.example` to `.env`; set `DATA_ROOT`, `DUCKDB_PATH`, `DUCKDB_MEMORY` (≈ 60–70 % of RAM), `DUCKDB_THREADS` (parallelism of
  each query), `DBT_THREADS` (models built concurrently: 4 on the laptop, 1 on the server), `COUNTRY_FILTER`.
- Use **absolute paths** for `DATA_ROOT` and `DUCKDB_PATH`: dbt runs from `dbt_multidim/`, the Python scripts from the repository root. `make` normalises relative paths; a plain `dbt` command does not and would create a second database under `dbt_multidim/data/`.
- Verify: `set -a; source .env; set +a; cd dbt_multidim && dbt deps && dbt debug`.
- `dbt_multidim/profiles.yml` reads these variables; `dbt_multidim/dbt_project.yml` holds `vars.countries` (fill after step 2).
- `Makefile` targets: `probe`, `bronze`, `gates`, `holidays`, `silver`, `gold`, `train`, `ablation`, `docs`.

### 1.5 DBeaver

1. New connection → DuckDB → path: the **absolute** path of `data/lakehouse.duckdb`; download the driver when prompted and pick the version matching the `duckdb` package in the venv (for example `2.0.0.0` for duckdb 2.0.0).
2. Driver properties tab → set `access_mode` to `READ_ONLY` (equivalent to adding `duckdb.read_only = true`). **Mandatory:** read-only stops DBeaver from writing to the lakehouse and lets several readers share the file.
3. **Disconnect DBeaver before running `make …`, `dbt run` or any loader; reconnect afterwards.** A DuckDB writer needs an exclusive lock on the file, and any other open connection, even read-only, makes it fail with `Could not set lock on file … Conflicting lock is held` (verified with DuckDB 2.0.0).
4. Use DBeaver to browse `bronze / silver / gold / quarantine / audit / ext`, run checks, take screenshots for the report, and `EXPLAIN ANALYZE` queries.

**DoD:** `dbt debug` reports all checks passed; DBeaver opens the (empty) database read-only; 11 raw files (CSV or Parquet) with checksums.

---

## Step 2 — CSV profiling

Nothing is transformed before its assumptions are measured. `ingestion/probe_csv_format.py` (`make probe`) reads the first 20,000 rows of each file and reports column types, null ratios, enumerated values, the format of the three nested columns, and the date span. Because the exports are sorted by country, that sample cannot give the country list or the real date span: `ingestion/probe_full_scan.py` (`make probe-full`, seconds on the laptop) reads every file once and writes `data/audit/csv_fullscan.md` with rows and min/max timestamp per country, value domains and key-column formats. Both scripts resolve the raw input through `ingestion/raw_source.py`: `<table>.parquet`, else a directory `<table>/*.parquet`, else `<table>.csv`.

```bash
make probe        # → data/audit/csv_profile.md
```

Fill in from the report:

| Question | Where to record |
|---|---|
| The country codes present in `sales_detail` (SG, TH, VN since the 2026-10-27 re-export; scope decision in #54) | `vars.countries` in `dbt_project.yml` and `COUNTRIES` in `.env` |
| `item_operation_type` ∈ {sale, return, cancel}? | confirms the dedup rule in `slv_fact_sales_line` |
| `price_type` values (four in the export, three in VN; promotion names are in `price_modifier_detail[].rule`) | confirms the `promo_kind` macro and the modifier extraction |
| Nested columns are `Map(k -> v)` strings (already confirmed) | `extract_map_field` macro is used |
| Inferred types of `item_code`, `business_unit_gln`, `site_gln` per table | `cast` entries in `table_contracts.yml` |
| Max `gmv_recorded_at` | drives `evaluation/split.yml` in step 7 |

**DoD:** `csv_profile.md` has 11 sections; country codes filled in; nested-column format recorded.

---

## Step 3 — Bronze

`ingestion/table_contracts.yml` declares, per table, the key, Bronze partition columns, required columns, key casts and the country column (`country_col`; `sales_tender_detail` has none and follows the loaded sales lines through `country_via`). `ingestion/batch_csv_to_bronze.py` converts each raw table (`ingestion/raw_source.py`: `<table>.parquet`, else `<table>/*.parquet`, else `<table>.csv`) to ZSTD Parquet under `data/bronze/<table>/` (`PARTITION_BY` per contract; an unpartitioned table is written as `<table>/<table>.parquet`), stores CSV parse rejects in `quarantine.rejects_<table>` (CSV inputs only), creates `bronze.<table>` views over the Parquet tree and logs rows/bytes/seconds and the country filter to `audit.pipeline_run_metrics`.

`COUNTRY_FILTER` in `.env` selects the scope: a single code (laptop: `VN`, the smallest country with complete data) loads only that country's rows from the seven tables that have a country column plus the matching tender lines, and loads the three dimension tables whole; `ALL` (server) loads everything. A table without rows for the chosen country (web events exist only for SG) still gets an empty `bronze.<table>` view with the source schema.

```bash
make bronze
```

Notes: `nullstr=['null','']` because the Spark export writes the string `null`; `max_line_size` is raised for `tracking_ecom_events`. DuckDB 2.x keeps two reject tables per CSV scan, so both are named per table (`rej_<table>`, `rejscan_<table>`); reject counts cover the whole file, not only the selected country. Disconnect DBeaver first (§1.5). Run the loaders through `make`: its recipes raise the open-file limit (`ulimit -n`), which a partitioned `COPY` with `COUNTRY_FILTER=ALL` exceeds on Linux (`f_member_purchase` partitions by member country — 85 values — × year × month; see Appendix B). A rerun after a failed load should start from an empty `data/bronze/<table>/`: `OVERWRITE_OR_IGNORE` replaces files of the same name but keeps extra files from the previous attempt.

Verification:

```sql
SELECT 'sales_detail' t, economical_businessunit_country_code c, COUNT(*) n FROM bronze.sales_detail GROUP BY 1,2
UNION ALL SELECT 'f_member_purchase', member_country_code, COUNT(*) FROM bronze.f_member_purchase GROUP BY 1,2 ORDER BY 1,2;
SELECT model_name, country_filter, output_rows, ROUND(wall_time_sec) s FROM audit.pipeline_run_metrics WHERE layer = 'bronze' ORDER BY executed_at;
SELECT error_type, column_name, COUNT(*) FROM quarantine.rejects_d_member GROUP BY 1,2 ORDER BY 3 DESC;   -- one table per CSV input with rejects
```

**DoD:** 11 `bronze.*` views; Bronze rows per table = rows of the selected country in `data/audit/csv_fullscan.md` (for CSV inputs minus the rows quarantined); rejects < 0.1 % per table; 11 rows with `layer = 'bronze'` and the run's `country_filter` in `audit.pipeline_run_metrics`.

---

## Step 4 — Gates and audit checks

```bash
make gates        # runs sql/gates_by_country.sql and sql/audit_checks.sql
```

- `audit.gates_by_country` — per country × year: member-link rate (≥ 60 %), item match rate (≥ 95 %), price coverage (≥ 90 %), members with ≥ 2 transactions (≥ 20,000) → `PASS` / `REVIEW`. With several countries the gates **group** countries rather than select one: `PASS` countries form the main evaluation set; `REVIEW` countries are still processed and reported in an appendix. Lower the fourth threshold for small countries and record it. Decision of the three-country run (2026-10-28, issue #9): main set TH + VN, SG REVIEW because of its member-link rate (DESIGN §2).
- `audit.stock_coverage` — share of sold items present in the stock table (team confirmed ≈ 100 %; rerun to keep evidence).
- `audit.price_uniformity` — store vs website price gaps; if `p95_rel_gap` < 5 %, keep the website business unit as the national reference (default); otherwise set `allow_store_prices: true`.
- `audit.interpurchase_days` — quantiles of inter-purchase gaps (validates Δ).
- `audit.date_span` — min/max transaction timestamps per country (drives `split.yml`).
- `audit.stream_reconciliation` — QC-7 (optional streaming lane, step 8): batch vs stream Bronze, rows / distinct keys / hash per table × country × day; written by `ingestion/qc7_stream_reconciliation.py`, not by `make gates`.
- `audit.volume_drift` — QC-5: rows per table (`sales_detail`, `tracking_ecom_events`) × country × day against the trailing 28-day mean of the same weekday; `flagged` when |drift| > 50 %, with a `probable_cause` hint (NO_ROWS, EXPORT_EDGE, AFTER_GAP, PUBLIC_HOLIDAY, ADJACENT_TO_HOLIDAY, UNEXPLAINED). `make gates` therefore runs `make holidays` first and prints the flagged-day count; review the UNEXPLAINED days and comment them on issue #25. Warn-level: nothing is blocked. `distinct_lines` and `dup_factor` compare the raw rows with the distinct (transaction, line, version) keys: `DUPLICATED_EXPORT` marks days on which the export repeated rows (1 – 13 October 2023 in all three countries, factor 1.6 – 2.0), which Silver deduplicates.

QC-5 regression checks run against synthetic, in-memory Bronze tables using the production SQL:

```bash
make test-volume-drift
```

After `make gates`, export the local QC-5 review without overwriting the committed report tables:

```bash
python tools/report_tables.py --only t20 --out data/audit/qc5_review
```

The summary and flagged-day detail include CSV copies. Probable causes are hints, not confirmed explanations.
A one-day web-event sample cannot validate drift or server-wide gaps. For issue #25, repeat the review on
the server with SG, TH and VN. The October 2023 spike (1 – 13 October, all three countries) is explained: the
export repeated those rows (`dup_factor` 1.6 – 2.0), so the check labels them `DUPLICATED_EXPORT`; the question
left for the data owner is the February 2025 doubling of the SG and TH web events.

**DoD:** the audit tables listed above exist; decisions on price reference and gate grouping recorded in the README.

---

## Step 5 — Silver (dbt)

Run order and purpose:

| Model | Purpose |
|---|---|
| `slv_member_bridge` | one member per transaction (earliest association) |
| `slv_member_profile` | static `d_member` attributes dated ≤ t and the account-exclusion flag |
| `slv_dim_model` | SKU → model catalogue; drops marketplace (UUID) and services |
| `slv_fact_sales_line` | version dedup → sale/cancel netting → transaction classification → SALE lines only |
| `slv_fact_returns` | return lines |
| `slv_price_sku_interval` | SKU price intervals, website business unit first, `promo_kind` |
| `slv_calendar_enriched` | public holidays + commercial events inferred from the temporary-promotion share (trailing 60-day z-score) |
| `slv_web_events_clean` | metadata struct flattened by path, one row per event with the numeric product codes as a list (unnested only in `gld_web_stitched` for attributed events), `is_event_to_use`, marketplace removed |
| `slv_user_to_member` | order-based + login-based stitching; one member per cookie |
| `slv_identity_conflicts` | cookies with several members (quarantine) |
| `slv_stock_daily_model`, `slv_stock_daily_national` | stock per model × site × day with ≤ 3-day forward fill |
| `slv_member_sport_asof` | favourite-sport validity intervals |
| `slv_member_store_daily` | input for the usual store at the anchor |

```bash
make silver       # dbt deps, dbt run --select staging silver, dbt test --select staging silver
```

Before the run: `make holidays` is executed automatically; it needs `COUNTRIES` in `.env`.

Manual check: pick 20 transactions that contain both `sale` and `cancel` lines in Bronze and confirm they are either absent from `slv_fact_sales_line` or keep only `qty > 0`.

Stitching coverage has two levels. Event level: `audit.stitching_coverage` (below). Anchor level, after step 6: the share of used anchors whose member has at least one attributed event in the 30 days before the anchor *and* whose attribution was already known at the anchor — the point-in-time rule that `gld_web_stitched.identity_verified_ts` exists for (WBS 3.2, issue #30):

```sql
WITH a AS (SELECT member_id, anchor_date, split FROM gold.anchor_grid WHERE is_used),
w AS (SELECT DISTINCT a.member_id, a.anchor_date FROM a JOIN gold.gld_web_stitched w ON w.member_id = a.member_id
      AND w.event_date BETWEEN a.anchor_date - 30 AND a.anchor_date - 1 AND w.identity_verified_ts <= CAST(a.anchor_date AS TIMESTAMP))
SELECT a.split, COUNT(*) used_anchors, COUNT(w.member_id) with_web_signal FROM a LEFT JOIN w USING (member_id, anchor_date) GROUP BY 1;
```

`audit.stitching_coverage` (dbt model in `models/audit/`, built by `make silver`): share of web events per country by identity source, DIRECT (member on the event) / STITCHED (attached within ± 90 days of `identity_verified_ts`) / ANON — the before-and-after view of stitching required by the DoD. Every `dbt run` also appends one row per model (wall time, rows, country filter) to `audit.pipeline_run_metrics` through the `on-run-end` hook `log_run_results`, the same table the Bronze loader writes.

Quarantine (schema `quarantine`, built by `make silver` together with Silver; rows a model refuses, kept with a reason):

| Table | Source model | Reasons |
|---|---|---|
| `rejects_<table>` | Bronze loader (CSV inputs) | DuckDB parse errors of the raw CSV (cut rows, embedded delimiters) |
| `qrt_sales_line` | `slv_fact_sales_line` | `NET_QTY_NONPOSITIVE`, `NET_GMV_NONPOSITIVE`, `TXN_NOT_SALE`, `SERVICE_LINE`, `NON_MERCHANDISE` (store fixtures and carrier bags, retail univers `FIXT & FURNIT`), `ITEM_NOT_IN_CATALOGUE` |
| `qrt_price_interval` | `slv_price_sku_interval` | `ABOVE_REFERENCE`, `DEPTH_GT_0_9` |
| `slv_identity_conflicts` | `slv_user_to_member` | cookie linked to more than one member |

```sql
SELECT 'sales' t, reason, COUNT(*) FROM quarantine.qrt_sales_line GROUP BY 1,2
UNION ALL SELECT 'price', reason, COUNT(*) FROM quarantine.qrt_price_interval GROUP BY 1,2 ORDER BY 1,3 DESC;
```

Warn-level tests (do not block): `discount_local >= 0` on the sales fact (negative values are surcharges), `store_tz` not null (missing store timezone falls back to UTC), `member_bridge_conflicts`, `referential_member_link_rate` (QC-2 is enforced through the gates, not the test).

**DoD:** `make silver` succeeds (`dbt run` and `dbt test` over staging, silver, quarantine and audit, warnings explained); quarantine tables listed above exist; `audit.stitching_coverage` has the before / after shares; `audit.pipeline_run_metrics` has one row per Silver model; 20 sale/cancel transactions verified.

---

## Step 6 — Gold

```bash
make gold         # build_anchor_grid.py, dbt run --select gold, dbt test --select gold
```

- `evaluation/build_anchor_grid.py` creates `gold.anchor_grid` (every Monday after a member's second transaction inside the train / valid / test windows of `split.yml`, with `split`, `days_to_next_buy` and `in_train_sample` by `TRAIN_ANCHOR_STRIDE`) and `gold.anchor_model_grid`. Downstream Gold models use only `is_used` anchors: a purchase within `ANCHOR_LABEL_HORIZON` days (an anchor without one has all-zero labels, useless for LambdaRank and unscorable by HR / NDCG), the stride for train, and a per-country cap by hash rank (`TRAIN_ANCHOR_CAP`, `VALID_ANCHOR_CAP`, `TEST_ANCHOR_CAP`). The script prints anchors before and after each rule and the pair-table estimate; measured on VN (issue #29), the unrestricted grid would give 20 M train anchors and 10 M test anchors, i.e. billions of pair rows.
- `gld_web_stitched`, `gld_copurchase_lift` (support, confidence, lift per country over baskets before `vars.copurchase_cutoff` = `valid_lo` of `split.yml`, checked by `tests/copurchase_cutoff_before_validation.sql` against `gold.split_windows`), `gld_fs_member` (feature groups F0 / F1 / F3 / F5 / Sport / Store, `web_data_available`), `gld_fs_model_country` (price = median over the SKU intervals valid on the anchor date, temporary promotion preferred per SKU; popularity, seasonality, calendar; stock columns NULL unless `vars.use_stock`, issue #21), `gld_candidates` (R1 repurchase, R2 co-purchase partners, R3 web intent, R4 sport × offer through `gld_sport_department_affinity`, R5 national best-sellers; priority R1 > R3 > R2 > R4 > R5, capped at `n_candidates`; recall per source in `audit.candidate_recall`), `gld_fs_pair`, `gld_ranking_dataset` (labels Δ = 30 / 90, returned purchases excluded).
- Singular tests `tests/leakage_*.sql` implement QC-6 and must return zero rows; `quarantine.leakage_violations` materialises the same predicates with model name and rule, so a violation leaves a trace (`tests/leakage_violations_empty.sql`).

Candidate recall per source: `audit.candidate_recall` (built together with the Gold models) gives recall@`n_candidates` overall and per source r1 … r5 for Δ = 30 / 90, per country × split, measured against every non-returned purchase in the window after a used anchor — it does not depend on `gld_ranking_dataset`. VN first run: 34 % (Δ = 30) with the national best-sellers (R5) at 30 %, repurchase (R1) 7 %, co-purchase (R2) 4 %; web (R3) and sport (R4) need the server's web data and SG / TH sport events to be read.

**DoD:** three entities and `gld_ranking_dataset` exist; leakage tests return zero rows; candidate recall per source recorded; training pair table ≤ ~30 M rows with stride 4.

---

## Step 7 — Experiments

### 7.1 Temporal split

From `audit.date_span`: test = the last six months of Monday anchors whose Δ = 90 label window closes before the export ends; validation = two months before test; purge gap of six weeks (the Δ = 90 window, which also covers Δ = 30); training = the remainder. The six dates are in `evaluation/split.yml` (drafted 2026-10-28 for the 2023-01-01 → 2026-10-26 exports: train to 2025-09-15, valid 2025-10-27 → 2025-12-22, test 2026-02-02 → 2026-07-27; issue #11).

### 7.2 Ranker

```bash
make train                                   # --config full --delta 30 → freezes evaluation/frozen_params.json
python evaluation/train_eval_lambdarank.py --config full --delta 90
```

`train_eval_lambdarank.py` trains LightGBM LambdaRank grouped by (member, anchor); on the first `full` run it early-stops on NDCG@20 and freezes `params` and `num_boost_round`; every later run reuses them. Outputs per-member metrics (`data/audit/results_<config>_d<Δ>.parquet`) and feature importance. On the laptop, rebuild Gold with small caps (`TRAIN_ANCHOR_CAP=5000 VALID_ANCHOR_CAP=2000 TEST_ANCHOR_CAP=5000 make gold`) and run the script with `--no-freeze --tag smoke`: it tunes with early stopping but leaves `frozen_params.json` untouched and writes `results_<config>_d<Δ>_smoke.parquet`, so the frozen parameters always come from the full three-country run on the server.

### 7.3 Ablation matrix

```bash
python evaluation/run_ablation_2axes.py                  # add --measure-cost to also rerun dbt per arm (≈ 1 h per rebuild on the server; not used for the 2026-10-28 run)
```

Runs the 12 configurations in `evaluation/ablation_configs.yml` for Δ = 30 and 90 (`--arms no_f1,no_f3 --deltas 30` to pick a subset; `--no-freeze --tag smoke` for laptop runs). With `--measure-cost`, arms that declare `exclude_models` rerun dbt without those models before training, so processing cost is measured as well as quality; dbt and training wall times go to `audit.ablation_runs`. `no_stock` is skipped while `vars.use_stock` is false (issue #21).

### 7.4 Bootstrap

```bash
python evaluation/bootstrap_ci.py 30 && python evaluation/bootstrap_ci.py 90
```

Member-level resampling (`BOOT_N`, default 500): 95 % CI per metric and for the paired difference arm − Full, overall, per country and per member segment (new ≤ 1 transaction in the previous year, loyal ≥ 3) → `data/audit/ablation_results_d<Δ>.csv` with a `significant` flag (`--tag smoke` reads the smoke results).

### 7.5 Cost profiler

```bash
python evaluation/pipeline_cost_profiler.py        # all Silver/Gold models, or pass model names
```

Each model rebuilt alone: wall time, peak RSS of the dbt process tree, output rows → `audit.pipeline_run_metrics`, plus output bytes in `audit.model_cost`. The MT3 table joins ablation results with the cost of the excluded models.

```bash
python evaluation/mt3_table.py            # → data/audit/mt3_table.csv; report table t24 via make report-tables
```

`mt3_table.py` joins each arm's gain (Full − arm on NDCG@20, HR@10, Recall@50 with the bootstrap CI) with the cost of what it removes: profiler wall time, peak RSS and output size of the models that exist only for that source (`exclude_models` of the arm, or the producing models of a candidate source), the Bronze load time of the raw tables feeding only that source, and the arm's training time. Costs are lower bounds (models the profiler did not time are listed with cost 0). The decision of 2026-10-28 was to measure cost this way (one profiler pass, ≈ 1 h) instead of `--measure-cost` (nine Silver + Gold rebuilds).

### 7.6 Scale test

```bash
python evaluation/scale_test.py VN TH SG            # countries axis, cumulative → data/audit/scale_test.png
python evaluation/scale_test.py VN --months 3,12,36  # months axis on one country → data/audit/scale_test_months.png
```

Each point reruns staging / Silver / quarantine / audit with the dbt vars `scale_countries` and `sales_min_date` (macros `country_where`, `sales_date_floor`), rebuilds the anchor grid and the Gold layer, and records bronze rows, wall time per stage, peak RSS, threads and memory limit in `audit.scale_test`; the lakehouse is left at the last point, so finish with `make silver && make gold`. Four with/without comparisons on a small country: `python evaluation/technique_comparisons.py --reps 3` (`TECHNIQUE_COUNTRY`, default VN) runs each variant in a fresh child process three times and writes medians of wall time and peak RSS to `audit.technique_comparisons`: Parquet vs CSV scan of the same 10-column extract; materialising the 24 staging columns vs all 141 columns of the raw sales Parquet (one year); price at four Monday anchors by ASOF JOIN vs exploding the intervals to days; member / user / order ids from the metadata as a JSON string by SQL `regexp_extract` vs a row-wise Python `json.loads` loop (the production struct path is kept as reference). Each comparison yields one measured number — these replace any unmeasured performance claims.

**DoD:** `frozen_params.json` committed; 12 configurations × 2 Δ with results; `ablation_results_d*.csv` with CI; cost table per arm; scale-test chart.

---

## Step 7b — Figures for the report

```bash
make docs-figures     # dbt docs generate → docs/figures/lineage_*.svg|png (Graphviz) + explain_analyze_asof_price.txt
```

`tools/lineage_graph.py` draws the model DAG from `target/manifest.json` (full, Bronze → Silver, Silver → Gold; the Python-built grid tables appear as components), `tools/explain_figures.py` saves the `EXPLAIN ANALYZE` of the ASOF price lookup. The DBeaver screenshots listed in `docs/figures/README.md` are taken by hand with the queries given there. Graphviz is required (`brew install graphviz` on macOS, `apt install graphviz` on the server).

---

## Step 8 — Streaming lane (optional)

```bash
docker compose up -d                                # Redpanda + Console (http://localhost:8080)
REPLAY_COUNTRY=XX REPLAY_MONTH=2025-01 python ingestion/kafka_producer_replay.py
python ingestion/kafka_consumer_to_bronze.py        # three topics → bronze/<table>_stream, rejects → quarantine.rejected_stream_events
```

The producer replays one topic per event table, each ordered by its event time and keyed as shown; a message value is the row's message columns as JSON (tracking: 10 of the 22 Bronze columns; `metadata` and `_errors` stay nested JSON). Topic, key, order and event-date column, message columns, stream partition and QC-7 hash columns per table are the `stream:` block of `ingestion/table_contracts.yml`, read once by `ingestion/stream_contracts.py` for the producer, the consumer and QC-7 (#103):

| Topic | Bronze table | Key | Month filter |
|---|---|---|---|
| `raw.tracking` | `tracking_ecom_events` | `session_id` | `date` |
| `raw.favorite_sport` | `f_member_favorite_sport` | `member_id` | `event_datetime_utc` |
| `raw.member_purchase` | `f_member_purchase` | `transaction_id` | `association_datetime_utc` |

`f_member_purchase.tech_year` / `tech_month` are not used for the month filter: they contain 1970-01 and values that disagree with `association_datetime_utc`. `REPLAY_TOPICS=raw.tracking,raw.favorite_sport` replays a subset; the run prints sent / failed counts and msg/s per topic and exits non-zero if any message was not delivered. Laptop smoke test: `REPLAY_COUNTRY=VN REPLAY_MONTH=2025-06` (464 150 / 102 / 245 746 messages, matching the Bronze counts; ≈ 23 k msg/s for tracking).

QC-7 reconciliation, after the consumer has run on the same country-month:

```bash
REPLAY_COUNTRY=XX REPLAY_MONTH=2025-01 python ingestion/qc7_stream_reconciliation.py
```

```sql
SELECT * FROM audit.stream_reconciliation WHERE NOT ok ORDER BY tbl, day;   -- empty when the lanes agree
SELECT tbl, COUNT(*) AS country_days, SUM(n_batch) AS n_batch, SUM(n_stream) AS n_stream FROM audit.stream_reconciliation GROUP BY 1;
```

`ingestion/qc7_stream_reconciliation.py` replaces the `REPLAY_COUNTRY` × `REPLAY_MONTH` slice of `audit.stream_reconciliation` (other countries and months stay, so SG, TH and VN can be run one after another): per table × country × day, rows (`n_*`), distinct business keys (`d_*`) and an order-independent hash (`h_*` = `SUM(hash(row columns))`, so duplicated rows do not cancel as under XOR; `f_member_purchase` repeats each `(transaction_id, member_id)` about three times in VN 2025-06), the batch − stream differences, `hash_match` and `ok`. Both sides use the same predicate and day: `tracking_ecom_events` by `date` with `WHERE is_event_to_use` on the batch side (the consumer keeps only those; pruned by `country_code, year, month`), `f_member_favorite_sport` by the UTC day of `event_datetime_utc` (pruned by `country_code, year`), `f_member_purchase` by the day of `association_datetime_utc` (`tech_year` / `tech_month` / `tech_day` are not reliable, so only the country is pruned and that country's partitions are scanned). `hash_match` covers only the table's `hash_columns` in `ingestion/table_contracts.yml` (tracking: `id, session_id, name, timestamp_utc`, not `metadata` or `_errors`), so it does not mean the payload is intact. A day present on one side only shows as a difference. The script exits with status 1 when anything differs; batch Bronze stays the source for Silver either way. It writes to the lakehouse, so close DBeaver first.

Consumer (`ingestion/kafka_consumer_to_bronze.py`): reads `raw.tracking`, `raw.favorite_sport` and `raw.member_purchase` from the beginning up to the offsets present at start and then exits (`STREAM_TOPICS` selects a subset, `STREAM_IDLE_TIMEOUT` = seconds without a message before it gives up, default 60). Valid messages are written to `data/bronze/<table>_stream/` (`tracking_ecom_events_stream` partitioned by `country_code, year, month` from `date`; `f_member_favorite_sport_stream` by `country_code, year`; `f_member_purchase_stream` by `member_country_code, year, month` from `association_datetime_utc`), with `metadata` and `_errors` kept as JSON. A message goes to `quarantine.rejected_stream_events(topic, kafka_partition, kafka_offset, reason, payload, rejected_at)` when it is not a JSON object (`invalid_json`, `not_a_json_object`), when a `not_null` column of the table in `ingestion/table_contracts.yml` (or its `event_date` column) is empty (`missing_<column>`), or when the table's `require_true` column is not true (tracking: `is_event_to_use` → `is_event_to_use_not_true`; `_errors` is not tested because the Parquet export fills it on every event). A batch whose values the declared types cannot hold is moved to the same table as `batch_write_error`. Each run first empties the stream folders and the topic's rows in the reject table, so a rerun gives the same result; it prints ok / bad per topic and the total msg/s.

The consumer holds the DuckDB write lock until it exits: close DBeaver and do not run `dbt` or the loaders at the same time (Appendix B).

```sql
SELECT topic, reason, COUNT(*) FROM quarantine.rejected_stream_events GROUP BY 1, 2;
```

Malformed-message test: produce 10 records without `session_id` to `raw.tracking` and rerun the consumer; the query above must show `raw.tracking | missing_session_id | 10` and the stream Parquet must not contain them. Laptop run on VN 2025-06: 464 150 / 102 / 245 746 valid messages, 0 rejected, about 20 k msg/s in total.

**DoD:** topic visible in Console; `diff = 0` for every replayed day; batch Bronze remains the source for Silver.

---

## Step 9 — Packaging

```bash
make docs         # dbt docs generate && dbt docs serve → lineage graph
```

Required tables and figures for the final report (`make report-tables` writes items 1 – 6 and 9 as Markdown + CSV into `docs/report/tables/` from the lakehouse, each with its source; the chapter drafts in `docs/report/` quote only those files):

| # | Item | Source |
|---|---|---|
| 1 | Profile of 11 tables, nested-column format, country list | `data/audit/csv_profile.md` |
| 2 | Gates per country × year, PASS / REVIEW grouping | `audit.gates_by_country` |
| 3 | Stock coverage, price uniformity, inter-purchase gaps | `audit.stock_coverage`, `price_uniformity`, `interpurchase_days` |
| 4 | Stitching coverage before / after, per country | `audit.stitching_coverage` |
| 5 | Inferred commercial events with names | `slv_calendar_enriched`, `ext.commercial_event_names` |
| 6 | Candidate recall@200 per source | step 6 |
| 7 | B0 vs Full and 10 ablation arms × metrics ± CI, per country and overall | `ablation_results_d*.csv` |
| 8 | Cost × gain table (MT3) | ablation results ⋈ `pipeline_run_metrics` |
| 9 | Scale test and four technique comparisons | `audit.scale_test`, `scale_test.png` |
| 10 | dbt lineage graph; DBeaver screenshots | dbt docs, DBeaver |

Submission checklist:

- [ ] No organisation names or personal paths in repo or report.
- [ ] README states machine requirements, `make all`, `.env` variables and measured run times.
- [ ] `requirements.txt`, DuckDB / dbt versions and `raw_csv_md5.txt` included.
- [ ] All dbt tests pass; `leakage_*` return zero rows; `frozen_params.json` committed.
- [ ] Numbers in slides and proposal match `audit.*` (200 candidates, 11 tables, 3 countries, @10 / @20).
- [ ] Five-minute demo: DBeaver → `audit.gates_by_country` → dbt docs lineage → ablation table.

---

## Appendix A — Data contracts (summary)

| Table | Key | Bronze partition | Silver usage | Pitfalls handled |
|---|---|---|---|---|
| sales_detail | transaction_id, transaction_num_line | country, year, month | ~18 columns | multiple versions; sale/cancel/return; local time; nested columns |
| f_member_purchase | transaction_id, member_id | country, year, month | 3 columns | duplicates; one transaction → several members |
| d_member | member_id | member_country_code | 8 static columns | current-snapshot columns not used |
| dim_item | item_code | — | 20 hierarchy columns | key type; marketplace; services |
| dim_business_unit | business_unit_gln | — | id, name, country, timezone, region | key type differs across tables |
| dim_calendar | date_of_day | — | ISO weeks | no holidays |
| all_store_selling_price | item, bu, start, price_type | country | 9 columns | overlapping intervals; 5 price types; store-level volume |
| stock_availability_rate | site, item, date, type | country, year, month | 6 columns | spare parts only (`availability_type = spare`); inventory tables `stock_pictures` / `obt_stock` not exported (issue #21) |
| f_member_favorite_sport | member, sport, ts | country, year | 4 columns | create/delete event log |
| sales_tender_detail | transaction_id, tender_num_line | year, month | — (out of feature scope) | — |
| tracking_ecom_events | id | country, year, month | 10 fields extracted from metadata | `Map(k -> v)`; 15.6 % with member |

## Appendix B — Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Could not set lock on file … Conflicting lock is held` on `dbt run` or a loader | another process has the database open, usually DBeaver, even read-only | disconnect DBeaver (right-click the connection → Disconnect), rerun, reconnect afterwards |
| Every model of `make gold` or `make silver` crawls, a 14-second model takes 30 minutes, CPU far from saturated | too many dbt threads: the concurrent models run inside the same DuckDB and share `memory_limit` and the DuckDB threads (server 2026-10-28 with `DUCKDB_THREADS=16` driving dbt concurrency) | `DBT_THREADS=1` on the server, 4 on the laptop (`.env`); `DUCKDB_THREADS` stays the per-query parallelism |
| Out of memory on a large join | `memory_limit` too high for the machine, or the spill directory full (dbt spills to `data/lakehouse.duckdb.tmp`, the loaders to `data/duck_temp`) | set `memory_limit` to ≈ 60–70 % of RAM; make sure `temp_directory` is writable and has space |
| `IO Error: Cannot open file "…/bronze/f_member_purchase/member_country_code=…/data_0.parquet": Too many open files` on `make bronze` | Linux default of 1 024 open files per process; the partitioned `COPY` keeps one writer per open partition per thread (85 member countries × year × month with `COUNTRY_FILTER=ALL`) | the `make` recipes raise the limit (`ulimit -n 65536`); when calling a script directly, run `ulimit -n 65536` first; if the hard limit is lower (`ulimit -Hn`), raise it in `/etc/security/limits.conf`; then `rm -rf data/bronze/<table>` and rerun |
| `make bronze` on a large partitioned table crawls at ~300 % CPU while `data/duck_temp` grows past the size of the output (server 2026-10-28: 112 GB of temp for 64 GB of `tracking_ecom_events` after 3 h) | a partitioned `COPY` buffers `partitioned_write_flush_threshold` rows per thread and per partition before writing; with ~120 partitions × 16 threads the default 524 288 holds the whole table and spills it | the loader sets `partitioned_write_flush_threshold = 32768` and `partitioned_write_max_open_files = 1024` (2.7× faster, no spill on a 150-partition synthetic test); if it still spills, lower the threshold or `DUCKDB_THREADS`; stop the run, `rm -rf data/bronze/<table> data/duck_temp`, `BRONZE_TABLES=<table> make bronze` |
| Regex extraction returns mostly null | key name or spacing differs in the string | inspect five raw strings, adjust the pattern; compare null rates |
| `ASOF JOIN` error | exactly one inequality on the time column is allowed; other conditions must be equalities | write `ON a.key = b.key AND a.ts >= b.ts` |
| `accepted_values` test fails | a value not seen in profiling | check `csv_profile.md`, extend the list, note it in the report |
| LightGBM slow or out of memory | pair table too large | raise `TRAIN_ANCHOR_STRIDE`, lower `N_CANDIDATES`, or move to the server |
| `Cannot open file ".../dbt_multidim/data/lakehouse.duckdb"` on `dbt debug` | relative `DUCKDB_PATH` / `DATA_ROOT` resolved from `dbt_multidim/` | use absolute paths in `.env`, or run dbt through `make` (which normalises them) |
| `python3.11: command not found` | Python 3.11 not installed | `uv venv --python 3.11 .venv` (uv downloads the interpreter) |
