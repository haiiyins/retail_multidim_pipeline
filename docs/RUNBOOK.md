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

**Re-exports.** When the team re-exports a table in a new format (2026-10-27: `sales_detail`, `sales_tender_detail`, `f_member_purchase`, `all_store_selling_price` arrived as Parquet), download only the new files and move the superseded file to `data/raw_csv/superseded_<YYYY-MM-DD>/` (ignored by git, kept for reconciliation) so that exactly one file per table remains in `data/raw_csv/`; the loader and both probes prefer `<table>.parquet` over `<table>.csv` only as a safety net. Then recompute `md5sum *.csv *.parquet > ../raw_csv_md5.txt`, rerun `make probe` and `make probe-full`, and commit the checksum file and both reports in the same PR.

### 1.3 Python environment

```bash
python3.11 -m venv .venv && source .venv/bin/activate
# or, if the python3.11 binary is not installed: uv venv --python 3.11 .venv
pip install -r requirements.txt
```

### 1.4 Configuration

- Copy `.env.example` to `.env`; set `DATA_ROOT`, `DUCKDB_PATH`, `DUCKDB_MEMORY` (≈ 60–70 % of RAM), `DUCKDB_THREADS`, `COUNTRY_FILTER`.
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
| `price_type` has exactly five values? | confirms the `promo_kind` macro |
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

Notes: `nullstr=['null','']` because the Spark export writes the string `null`; `max_line_size` is raised for `tracking_ecom_events`. DuckDB 2.x keeps two reject tables per CSV scan, so both are named per table (`rej_<table>`, `rejscan_<table>`); reject counts cover the whole file, not only the selected country. Disconnect DBeaver first (§1.5).

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

- `audit.gates_by_country` — per country × year: member-link rate (≥ 60 %), item match rate (≥ 95 %), price coverage (≥ 90 %), members with ≥ 2 transactions (≥ 20,000) → `PASS` / `REVIEW`. With five countries the gates **group** countries rather than select one: `PASS` countries form the main evaluation set; `REVIEW` countries are still processed and reported in an appendix. Lower the fourth threshold for small countries and record it.
- `audit.stock_coverage` — share of sold items present in the stock table (team confirmed ≈ 100 %; rerun to keep evidence).
- `audit.price_uniformity` — store vs website price gaps; if `p95_rel_gap` < 5 %, keep the website business unit as the national reference (default); otherwise set `allow_store_prices: true`.
- `audit.interpurchase_days` — quantiles of inter-purchase gaps (validates Δ).
- `audit.date_span` — min/max transaction timestamps per country (drives `split.yml`).

**DoD:** five audit tables exist; decisions on price reference and gate grouping recorded in the README.

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
| `slv_web_events_clean` | regex extraction of `metadata`, `is_event_to_use`, marketplace removed |
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

Stitching coverage (write to `audit.stitching_coverage`):

```sql
SELECT country_code, id_source, COUNT(*) n, ROUND(100.0*COUNT(*)/SUM(COUNT(*)) OVER (PARTITION BY country_code),2) pct
FROM gold.gld_web_stitched GROUP BY 1,2 ORDER BY 1,2;   -- after step 6; compare with the raw 15.6 %
```

Quarantine (schema `quarantine`, built by `make silver` together with Silver; rows a model refuses, kept with a reason):

| Table | Source model | Reasons |
|---|---|---|
| `rejects_<table>` | Bronze loader (CSV inputs) | DuckDB parse errors of the raw CSV (cut rows, embedded delimiters) |
| `qrt_sales_line` | `slv_fact_sales_line` | `NET_QTY_NONPOSITIVE`, `NET_GMV_NONPOSITIVE`, `TXN_NOT_SALE`, `SERVICE_LINE`, `ITEM_NOT_IN_CATALOGUE` |
| `qrt_price_interval` | `slv_price_sku_interval` | `ABOVE_REFERENCE`, `DEPTH_GT_0_9` |
| `slv_identity_conflicts` | `slv_user_to_member` | cookie linked to more than one member |

```sql
SELECT 'sales' t, reason, COUNT(*) FROM quarantine.qrt_sales_line GROUP BY 1,2
UNION ALL SELECT 'price', reason, COUNT(*) FROM quarantine.qrt_price_interval GROUP BY 1,2 ORDER BY 1,3 DESC;
```

Warn-level tests (do not block): `discount_local >= 0` on the sales fact (negative values are surcharges), `store_tz` not null (missing store timezone falls back to UTC), `member_bridge_conflicts`, `referential_member_link_rate` (QC-2 is enforced through the gates, not the test).

**DoD:** `make silver` succeeds (`dbt run` and `dbt test` over staging, silver and quarantine, warnings explained); quarantine tables listed above exist; 20 sale/cancel transactions verified.

---

## Step 6 — Gold

```bash
make gold         # build_anchor_grid.py, dbt run --select gold, dbt test --select gold
```

- `evaluation/build_anchor_grid.py` creates `gold.anchor_grid` (every Monday after a member's second transaction; `in_train_sample` by `TRAIN_ANCHOR_STRIDE`) and `gold.anchor_model_grid`.
- `gld_web_stitched`, `gld_copurchase_lift` (`vars.copurchase_cutoff` must precede the first test anchor), `gld_fs_member`, `gld_fs_model_country` (price via ASOF on SKU intervals, median per model), `gld_candidates` (R1–R5, capped at `n_candidates`), `gld_fs_pair`, `gld_ranking_dataset` (labels Δ = 30 / 90, returned purchases excluded).
- Singular tests `tests/leakage_*.sql` implement QC-6 and must return zero rows.

Candidate recall per source:

```sql
SELECT 'r1' src, AVG(r1) FROM gold.gld_ranking_dataset WHERE label_30 = 1
UNION ALL SELECT 'r2', AVG(r2) FROM gold.gld_ranking_dataset WHERE label_30 = 1
-- … r3, r4, r5
```

**DoD:** three entities and `gld_ranking_dataset` exist; leakage tests return zero rows; candidate recall per source recorded; training pair table ≤ ~30 M rows with stride 4.

---

## Step 7 — Experiments

### 7.1 Temporal split

From `audit.date_span`: test = last six months minus Δ; validation = two months before test; purge gap of two weeks (Δ = 30) or six weeks (Δ = 90); training = the remainder. Write the six dates to `evaluation/split.yml`.

### 7.2 Ranker

```bash
make train                                   # --config full --delta 30 → freezes evaluation/frozen_params.json
python evaluation/train_eval_lambdarank.py --config full --delta 90
```

`train_eval_lambdarank.py` trains LightGBM LambdaRank grouped by (member, anchor); on the first `full` run it early-stops on NDCG@20 and freezes `params` and `num_boost_round`; every later run reuses them. Outputs per-member metrics (`data/audit/results_<config>_d<Δ>.parquet`) and feature importance.

### 7.3 Ablation matrix

```bash
python evaluation/run_ablation_2axes.py --measure-cost
```

Runs the 12 configurations in `evaluation/ablation_configs.yml` for Δ = 30 and 90. With `--measure-cost`, arms that declare `exclude_models` rerun dbt without those models before training, so processing cost is measured as well as quality.

### 7.4 Bootstrap

```bash
python evaluation/bootstrap_ci.py 30 && python evaluation/bootstrap_ci.py 90
```

Member-level resampling (`BOOT_N`, default 500): 95 % CI per metric and for the paired difference Full − arm → `data/audit/ablation_results_d<Δ>.csv`.

### 7.5 Cost profiler

```bash
python evaluation/pipeline_cost_profiler.py        # all Silver/Gold models, or pass model names
```

Wall time, peak RSS of the dbt child process, output rows → `audit.pipeline_run_metrics`. The MT3 table joins ablation results with the cost of the excluded models.

### 7.6 Scale test

```bash
python evaluation/scale_test.py XX XX XX XX XX      # country codes in cumulative order → data/audit/scale_test.png
```

Add four with/without comparisons on a small country (Parquet vs CSV; column projection; ASOF vs daily explode on one month; regex extraction vs row-wise Python). Each comparison yields one measured number — these replace any unmeasured performance claims.

**DoD:** `frozen_params.json` committed; 12 configurations × 2 Δ with results; `ablation_results_d*.csv` with CI; cost table per arm; scale-test chart.

---

## Step 8 — Streaming lane (optional)

```bash
docker compose up -d                                # Redpanda + Console (http://localhost:8080)
REPLAY_COUNTRY=XX REPLAY_MONTH=2025-01 python ingestion/kafka_producer_replay.py
python ingestion/kafka_consumer_to_bronze.py        # writes bronze/tracking_ecom_events_stream, rejects → quarantine
```

QC-7 reconciliation:

```sql
SELECT b.country_code, b.d, b.n AS n_batch, s.n AS n_stream, b.n - COALESCE(s.n,0) AS diff
FROM (SELECT country_code, date::DATE d, COUNT(*) n FROM bronze.tracking_ecom_events GROUP BY 1,2) b
LEFT JOIN (SELECT country_code, date::DATE d, COUNT(*) n FROM read_parquet('data/bronze/tracking_ecom_events_stream/**/*.parquet', hive_partitioning=true) GROUP BY 1,2) s USING (country_code, d)
WHERE s.n IS NOT NULL ORDER BY diff DESC;
```

**DoD:** topic visible in Console; `diff = 0` for every replayed day; batch Bronze remains the source for Silver.

---

## Step 9 — Packaging

```bash
make docs         # dbt docs generate && dbt docs serve → lineage graph
```

Required tables and figures for the final report:

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
| stock_availability_rate | site, item, date, type | country, year, month | 6 columns | `spare` default label; missing days |
| f_member_favorite_sport | member, sport, ts | country, year | 4 columns | create/delete event log |
| sales_tender_detail | transaction_id, tender_num_line | year, month | — (out of feature scope) | — |
| tracking_ecom_events | id | country, year, month | 10 fields extracted from metadata | `Map(k -> v)`; 15.6 % with member |

## Appendix B — Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Could not set lock on file … Conflicting lock is held` on `dbt run` or a loader | another process has the database open, usually DBeaver, even read-only | disconnect DBeaver (right-click the connection → Disconnect), rerun, reconnect afterwards |
| Out of memory on a large join | `memory_limit` too high for the machine or `temp_directory` unset | set `memory_limit` to ≈ 60–70 % of RAM; make sure `temp_directory` is writable and has space |
| Regex extraction returns mostly null | key name or spacing differs in the string | inspect five raw strings, adjust the pattern; compare null rates |
| `ASOF JOIN` error | exactly one inequality on the time column is allowed; other conditions must be equalities | write `ON a.key = b.key AND a.ts >= b.ts` |
| `accepted_values` test fails | a value not seen in profiling | check `csv_profile.md`, extend the list, note it in the report |
| LightGBM slow or out of memory | pair table too large | raise `TRAIN_ANCHOR_STRIDE`, lower `N_CANDIDATES`, or move to the server |
| `Cannot open file ".../dbt_multidim/data/lakehouse.duckdb"` on `dbt debug` | relative `DUCKDB_PATH` / `DATA_ROOT` resolved from `dbt_multidim/` | use absolute paths in `.env`, or run dbt through `make` (which normalises them) |
| `python3.11: command not found` | Python 3.11 not installed | `uv venv --python 3.11 .venv` (uv downloads the interpreter) |
