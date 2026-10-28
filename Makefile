include .env
# resolve relative paths so that dbt (run from dbt_multidim/) and the Python scripts
# (run from the repository root) open the same database
DATA_ROOT := $(abspath $(DATA_ROOT))
DUCKDB_PATH := $(abspath $(DUCKDB_PATH))
export
# Linux gives a process 1 024 open files by default; a partitioned COPY (f_member_purchase: 85 member countries ×
# year × month, DUCKDB_THREADS writers each) exceeds it with "IO Error: … Too many open files". Raise the soft limit
# in every recipe shell that opens the lakehouse; the fallback covers hosts with a small hard limit.
NOFILE = ulimit -n 65536 2>/dev/null || ulimit -n 4096 2>/dev/null || true
PYTHONUNBUFFERED = 1   # stream the loaders' per-table lines into a redirected log instead of flushing them at exit
.PHONY: probe probe-full bronze bronze-views gates holidays silver gold train ablation docs all
probe:
	python ingestion/probe_csv_format.py
probe-full:
	python ingestion/probe_full_scan.py
bronze:
	$(NOFILE); python ingestion/batch_csv_to_bronze.py
bronze-views:
	$(NOFILE); python ingestion/bronze_views_from_parquet.py
gates:
	$(NOFILE); python -c "import duckdb,os;c=duckdb.connect(os.environ['DUCKDB_PATH']);c.execute(open('sql/gates_by_country.sql').read());c.execute(open('sql/audit_checks.sql').read());print(c.execute('SELECT * FROM audit.gates_by_country').df())"
holidays:
	$(NOFILE); python ingestion/holiday_commercial_builder.py
silver: holidays
	$(NOFILE); cd dbt_multidim && dbt deps && dbt run --select staging silver quarantine audit && dbt test --select staging silver quarantine audit
gold:
	$(NOFILE); python evaluation/build_anchor_grid.py
	$(NOFILE); cd dbt_multidim && dbt run --select gold leakage_violations && dbt test --select gold leakage_violations
train:
	$(NOFILE); python evaluation/train_eval_lambdarank.py --config full --delta 30
ablation:
	$(NOFILE); python evaluation/run_ablation_2axes.py
docs:
	cd dbt_multidim && dbt docs generate && dbt docs serve
all: bronze gates silver gold train ablation
