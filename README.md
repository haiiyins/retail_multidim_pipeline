# Multi-Signal Data Processing and Integration Pipeline for Personalized Retail Recommendation

An end-to-end data processing and integration pipeline that turns eleven heterogeneous retail tables — point-of-sale transactions, catalogue, prices, stock, loyalty profiles, favourite sports and web clickstream — into a point-in-time feature store for personalized product recommendation on large-scale, multi-country retail data.

Course project for **Data Processing Engineering** (IT2047.26.1.CH.01), Master of Computer Science, University of Information Technology, Vietnam National University Ho Chi Minh City.

## Table of Contents

- [Introduction](#introduction)
- [Motivation](#motivation)
- [Architecture](#architecture)
- [Installation Guide](#installation-guide)
  - [Prerequisites](#prerequisites)
  - [Option 1: Installation from GitHub](#option-1-installation-from-github)
  - [Option 2: Streaming lane with Docker](#option-2-streaming-lane-with-docker-optional)
- [Project Structure](#project-structure)
- [Quality Gates](#quality-gates)
- [Results](#results)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [Team](#team)
- [Acknowledgements](#acknowledgements)

## Introduction

Most retail recommender systems in production are driven by a single signal: what a customer bought before. The information that would make recommendations sharper — the price range a customer usually pays, which products sell together, seasonality and promotions, repurchase rhythms, and what the customer browsed online — usually exists inside the company, but it is scattered across many tables, several storage layers, different update frequencies and incompatible identifiers. The bottleneck is therefore not the ranking algorithm; it is the data engineering needed to turn those scattered sources into trustworthy, leakage-free features.

This repository builds that missing layer. It implements a three-tier **local lakehouse** (Bronze → Silver → Gold) on DuckDB and Parquet, orchestrated with dbt, that ingests about 34 GB of raw CSV covering five APAC countries from 2023 to 2026, cleans and reconciles it, and produces three point-in-time feature entities: member, product × country × date, and member–candidate pair. A fixed LightGBM LambdaRank model sits at the end of the pipeline as a measuring instrument, so that every change in recommendation quality can be traced back to a specific data-processing decision and weighed against its processing cost.

## Motivation

**Data over model.** Recent work on multi-behaviour and price-aware recommendation (BCIPM, SIGIR 2024; POGCN, KDD 2024; HSTU, ICML 2024; MBRCC, TOIS 2024; and a SIGIR 2026 cross-paradigm reproducibility study) shows that how signals are normalised and integrated matters more than model complexity. This project makes that engineering work the object of study instead of a preprocessing footnote.

**Real, large and messy data.** Multiple versions of the same transaction, cancelled online orders that net to zero, local timestamps next to UTC ones, five kinds of price labels, nested `Map(k -> v)` strings exported from Spark, and web sessions where only 15.6 % of events carry a member identifier — every classic data-processing problem appears at least once in this dataset.

**Measurable trade-offs.** A two-axis ablation (feature groups × candidate sources), where each arm is paired with the measured processing cost of the data branch it removes, answers the question a data team actually faces: which data source is worth the effort of integrating?

## Architecture

```
Raw CSV (11 tables, ~34 GB)
   │  batch loader (DuckDB)                  optional: Redpanda replay of the 3 event tables
   ▼
BRONZE      ZSTD Parquet, Hive-partitioned (country / year / month)
            data contracts · rejected rows → quarantine · ingestion metadata
   │  dbt-duckdb
   ▼
SILVER      deduplicated sales lines · returns · member bridge · catalogue at model level
            SKU price intervals · holiday & commercial calendar (self-built)
            web events + identity stitching (self-built) · daily stock · favourite-sport state · usual store
   │  dbt-duckdb · quality gates QC-1 … QC-7
   ▼
GOLD        weekly anchor grid · fs_member · fs_model_country · fs_pair
            candidates R1–R5 · labels Δ = 30 / 90 days · leakage assertions
   │  Python
   ▼
EVALUATION  fixed LightGBM LambdaRank · temporal split with purge gaps · baseline vs full
            two-axis ablation · member-level bootstrap CI · cost profiler · scale test
```

Key decisions, frozen in [`docs/DESIGN_DECISIONS.md`](docs/DESIGN_DECISIONS.md):

| Decision | Value |
|---|---|
| Recommendation unit | `model_code` (product model, not size/colour SKU) |
| Eligible customers | identified members with ≥ 2 transactions; staff, business, legal-entity, club and school accounts excluded |
| Candidates per (member, anchor) | 200, from five sources: repurchase, co-purchase, web intent, sport × season/sale, local best-sellers in stock |
| Label windows | Δ = 30 days (primary), 90 days (secondary) |
| Point-in-time rule | every feature uses only data with timestamp ≤ anchor date, enforced by ASOF joins and automated leakage tests |
| Metrics | HR, MRR, NDCG @10 / @20, Recall@50, candidate recall per source, coverage, member-level bootstrap CI |
| Hyper-parameters | tuned once on the full configuration, then frozen for every ablation arm |

## Installation Guide

The pipeline runs on a laptop for development (one country, a few months) and on a 32 vCPU / 256 GB server for the full five-country run. All SQL is DuckDB-flavoured and platform independent.

### Prerequisites

- Python 3.11
- DuckDB ≥ 1.1, dbt-core ≥ 1.8, dbt-duckdb ≥ 1.8
- pyarrow, pandas, polars, pyyaml, python-dotenv
- holidays, lightgbm, scikit-learn, psutil, matplotlib
- confluent-kafka and Docker (optional, streaming lane only)
- DBeaver (optional, to browse the lakehouse read-only)
- Disk: ≥ 150 GB free for a one-country development run; ≥ 2 TB NVMe for the full run

All Python dependencies are listed in `requirements.txt`.

### Option 1: Installation from GitHub

1. **Clone the repository**

   ```bash
   git clone https://github.com/haiiyins/retail_multidim_pipeline.git
   cd retail_multidim_pipeline
   ```

2. **Create a virtual environment**

   ```bash
   python3.11 -m venv .venv
   # or, if the python3.11 binary is not installed:
   uv venv --python 3.11 .venv
   ```

3. **Activate the virtual environment**

   ```bash
   source .venv/bin/activate        # Windows: .venv\Scripts\activate
   ```

4. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   ```

5. **Configure the environment**

   ```bash
   cp .env.example .env
   ```

   Edit `.env`: `DATA_ROOT`, `DUCKDB_PATH`, `DUCKDB_MEMORY` (about 60–70 % of RAM), `DUCKDB_THREADS`, `COUNTRY_FILTER` (a single country code while developing, `ALL` for the full run) and `COUNTRIES` (the five codes found in step 2).

   Use **absolute paths** for `DATA_ROOT` and `DUCKDB_PATH`. dbt runs from `dbt_multidim/` while the Python scripts run from the repository root, so a relative path points to two different files. `make` normalises relative paths; a plain `dbt` command does not.

   Check the setup with `cd dbt_multidim && dbt deps && dbt debug` (export the variables first: `set -a; source .env; set +a`). All checks must pass before continuing.

6. **Place the raw data**

   Put the eleven CSV files in `data/raw_csv/<table>.csv`. The download and renaming commands are in [`docs/RUNBOOK.md`](docs/RUNBOOK.md) §1.2. The `data/` directory is git-ignored.

7. **Run the pipeline**

   ```bash
   make probe      # step 2 — profile the CSV files              → data/audit/csv_profile.md
   make bronze     # step 3 — CSV → partitioned Parquet          → bronze.* views
   make gates      # step 4 — four go/no-go gates + audit checks
   make silver     # step 5 — holiday calendar, dbt run / test for Silver
   make gold       # step 6 — anchor grid, feature store, candidates, leakage tests
   make train      # step 7 — full ranker, freezes hyper-parameters
   make ablation   # step 7 — baseline + 10 ablation arms × Δ
   make docs       # dbt lineage documentation
   ```

   `make all` runs steps 3 to 7 in sequence.

8. **Inspect the lakehouse**

   Open `data/lakehouse.duckdb` in DBeaver with the driver property `duckdb.read_only = true`. DuckDB allows a single writer, and dbt needs it.

### Option 2: Streaming lane with Docker (optional)

The three event tables (web tracking, favourite sports, member–purchase links) can additionally be replayed through a Kafka-compatible broker to demonstrate hybrid batch/stream ingestion with contract checks and a dead-letter queue. Batch Bronze remains the source of truth; the stream output is reconciled against it (gate QC-7).

1. **Start Redpanda and its console**

   ```bash
   docker compose up -d             # console at http://localhost:8080
   ```

2. **Replay one country-month and consume it**

   ```bash
   REPLAY_COUNTRY=XX REPLAY_MONTH=2025-01 python ingestion/kafka_producer_replay.py
   python ingestion/kafka_consumer_to_bronze.py
   ```

3. **Reconcile** the stream output with the batch Bronze tables using the SQL in `docs/RUNBOOK.md` §8. The per-day difference must be zero.

## Project Structure

```
retail_multidim_pipeline/
├── ingestion/              CSV probe, batch CSV → Bronze, data contracts, holiday calendar, Kafka replay/consumer
├── sql/                    go/no-go gates and audit checks
├── dbt_multidim/           dbt-duckdb project
│   ├── macros/             Map(k -> v) extraction, promotion kinds, country filter
│   ├── models/staging/     type harmonisation views, sources and tests
│   ├── models/silver/      13 cleaned and integrated tables
│   ├── models/gold/        feature store, candidates, ranking dataset
│   └── tests/              leakage and integrity assertions
├── evaluation/             anchor grid, LightGBM ranker, ablation matrix, bootstrap CI, cost profiler, scale test
├── docs/                   RUNBOOK.md (step by step) · DESIGN_DECISIONS.md (frozen decisions, WBS, risks)
├── data/                   git-ignored: raw_csv, bronze, silver, gold, quarantine, audit, duck_temp
├── Makefile
├── .env.example
├── requirements.txt
└── docker-compose.yml
```

## Quality Gates

| Gate | Check | On failure |
|---|---|---|
| QC-1 | Null keys = 0 | block |
| QC-2 | Referential integrity ≥ 95 / 60 / 90 % per country | block (main set) / warn |
| QC-3 | Value domains: `promo_depth ∈ [0, 0.9]`, `price > 0`, `qty > 0` | route rows to quarantine |
| QC-4 | Uniqueness after deduplication and netting | block |
| QC-5 | Volume drift ± 50 % vs 28-day trailing mean | warn |
| QC-6 | Point-in-time: `max(source_ts) ≤ anchor_date`, `identity_verified_ts ≤ anchor_date` | block, log |
| QC-7 | Batch vs stream reconciliation | report |

## Results

Step 7 writes its outputs to `data/audit/`: `ablation_results_d30.csv`, `ablation_results_d90.csv`, `scale_test.png` and the `pipeline_run_metrics` table. The final report presents, per country and overall, the baseline against the full pipeline, the contribution and processing cost of each data source, candidate recall per source, identity-stitching coverage before and after, and the scale-test curves. This section will be updated with measured numbers once the full run on the server is complete.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `Could not set lock on file` on `dbt run` | DBeaver holds a writable connection | set `duckdb.read_only = true` or disconnect |
| Out of memory on a large join | `memory_limit` too high or `temp_directory` unset | lower `DUCKDB_MEMORY`; make sure `data/duck_temp` exists and has space |
| Regex extraction returns mostly null | key name or spacing differs in the raw string | inspect five raw `metadata` values and adjust the pattern in `dbt_multidim/macros/extract_map_field.sql` |
| `ASOF JOIN` error | only one inequality on the time column is allowed | write `ON a.key = b.key AND a.ts >= b.ts` |
| `Cannot open file ".../dbt_multidim/data/lakehouse.duckdb"` on `dbt debug` | relative `DUCKDB_PATH` / `DATA_ROOT` resolved from `dbt_multidim/` | use absolute paths in `.env`, or run dbt through `make` (which normalises them) |
| `python3.11: command not found` | Python 3.11 not installed | `uv venv --python 3.11 .venv` (uv downloads the interpreter) |
| `accepted_values` test fails | a value not seen during profiling | check `csv_profile.md`, extend the list, note it in the report |
| LightGBM slow or out of memory | pair table too large | raise `TRAIN_ANCHOR_STRIDE`, lower `N_CANDIDATES`, or move to the server |

More cases are covered in `docs/RUNBOOK.md`, Appendix B. For anything else, open an issue in this repository.

## Contributing

This is a course project maintained by the team below; contributions from team members follow the work-breakdown structure in `docs/DESIGN_DECISIONS.md`.

1. Create a branch per work package: `feat/<wbs>-<short-name>` (for example `feat/2.3-price-intervals`).
2. Every new dbt model ships with `schema.yml` tests; Gold models must pass the leakage assertions in `dbt_multidim/tests/`.
3. Keep code, comments, commit messages and documentation in English. Never commit anything under `data/`, `.env` or `*.duckdb`.
4. Open a pull request against `main` using the template; one reviewer approves before merging.

Suggestions and bug reports from outside the team are welcome through the issue tracker.

## Team

| Member | Responsibilities |
|---|---|
| **Phan Nguyễn Hải Yến** | Data contracts, price timeline, holiday and commercial calendar, identity stitching, statistical evaluation |
| **Nguyễn Viết Kha** | Profiling, Bronze ingestion, quality gates, streaming lane, cost profiling and scale test |
| **Lê Đức Mạnh** | Silver core tables, Gold feature store, candidate generation, ranking model and ablation |

Supervisor: **Dr. Võ Phương Bình**, Faculty of Information Science and Engineering, University of Information Technology, VNU-HCM.

## Acknowledgements

The team thanks Dr. Võ Phương Bình for supervising the project and the Data Processing Engineering course for the framework in which it was carried out. The approach draws on published work on multi-behaviour and price-aware recommendation (SIGIR, KDD, ICML, TOIS, 2024–2026) and on the open-source projects DuckDB, Apache Parquet, dbt, Redpanda, LightGBM and the Python `holidays` library. The dataset was made available for academic use; no organisation-specific identifiers or personal paths are included in this repository.
