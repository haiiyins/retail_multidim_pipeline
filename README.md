# retail_multidim_pipeline

A multi-signal data processing and integration pipeline for personalized product recommendation on large-scale retail data.
Course project for **Data Processing Engineering** (IT2047.26.1.CH.01) · Group 6 · University of Information Technology, VNU-HCM.

**Architecture — Local Lakehouse:** DuckDB (out-of-core OLAP) + Parquet (ZSTD, Hive-partitioned) + dbt-duckdb + DBeaver (+ optional Redpanda/Kafka stream) + LightGBM LambdaRank.
Three layers Bronze → Silver → Gold, strict point-in-time discipline, seven automated quality gates, and a two-axis ablation study that weighs recommendation gain against data-processing cost.

## Scope (frozen)
- 11 source tables · 5 APAC countries · 2023 – 2026 · ~34 GB raw CSV
- Recommendation unit `model_code` · members with ≥ 2 transactions · 200 candidates per member · Δ = 30 days (primary), 90 days (secondary)
- The pipeline is the deliverable; a fixed ranking model is only the measuring instrument

## Quick start
```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # set DATA_ROOT, DUCKDB_MEMORY, DUCKDB_THREADS, COUNTRY_FILTER
# place the 11 CSV files in data/raw_csv/<table>.csv  (see docs/RUNBOOK.md §1.2)
make probe      # step 2: profile CSV formats          → data/audit/csv_profile.md
make bronze     # step 3: CSV → partitioned Parquet + bronze.* views
make gates      # step 4: four go/no-go gates per country × year + audit checks
make silver     # step 5: dbt run/test for Silver
make gold       # step 6: anchor grid + feature store + candidates + leakage tests
make train      # step 7: full ranker (freezes hyper-parameters)
make ablation   # step 7: baseline + 10 ablation arms × Δ
```

## Layout
```
ingestion/      CSV probe, batch CSV→Bronze, data contracts, holiday calendar, optional Kafka replay/consumer
sql/            gate queries and audit checks (run in DBeaver or the duckdb CLI)
dbt_multidim/   dbt-duckdb project: staging → silver → gold, macros, tests
evaluation/     anchor grid, LightGBM ranker, two-axis ablation, bootstrap CI, cost profiler, scale test
docs/           runbook (step by step) and frozen design decisions
data/           (git-ignored) raw_csv, bronze, silver, gold, quarantine, audit, duck_temp
```

## Documentation
- `docs/RUNBOOK.md` — nine implementation steps, each with commands, files, checks and a definition of done
- `docs/DESIGN_DECISIONS.md` — frozen design decisions and the full work-breakdown structure

## Team conventions
- `main` is protected; one branch per work package `feat/<wbs>-<name>`; merge through a pull request with one reviewer.
- Never commit data, `.env`, `*.duckdb`, or `duck_temp/`.
- Every new dbt model ships with tests in `schema.yml`; Gold models must pass `tests/leakage_*.sql`.
- Do not reference the data owner organisation or personal paths anywhere in code or docs.

## Team
Phan Nguyễn Hải Yến · Nguyễn Viết Kha · Lê Đức Mạnh — Supervisor: Dr. Võ Phương Bình
