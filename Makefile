include .env
export
.PHONY: probe bronze gates holidays silver gold train ablation docs all
probe:
	python ingestion/probe_csv_format.py
bronze:
	python ingestion/batch_csv_to_bronze.py
gates:
	python -c "import duckdb,os;c=duckdb.connect(os.environ['DUCKDB_PATH']);c.execute(open('sql/gates_by_country.sql').read());c.execute(open('sql/audit_checks.sql').read());print(c.execute('SELECT * FROM audit.gates_by_country').df())"
holidays:
	python ingestion/holiday_commercial_builder.py
silver: holidays
	cd dbt_multidim && dbt deps && dbt run --select staging silver && dbt test --select staging silver
gold:
	python evaluation/build_anchor_grid.py
	cd dbt_multidim && dbt run --select gold && dbt test --select gold
train:
	python evaluation/train_eval_lambdarank.py --config full --delta 30
ablation:
	python evaluation/run_ablation_2axes.py
docs:
	cd dbt_multidim && dbt docs generate && dbt docs serve
all: bronze gates silver gold train ablation
