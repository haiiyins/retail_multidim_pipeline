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
.PHONY: probe probe-full bronze bronze-views gates test-volume-drift holidays silver gold train ablation docs docs-figures report-tables ml-test ml-seq ml-eval ml-views ml-retrieval ml-figures report-pdf all
probe:
	python ingestion/probe_csv_format.py
probe-full:
	python ingestion/probe_full_scan.py
bronze:
	$(NOFILE); python ingestion/batch_csv_to_bronze.py
bronze-views:
	$(NOFILE); python ingestion/bronze_views_from_parquet.py
gates: holidays
	$(NOFILE); python -c "import duckdb,os;c=duckdb.connect(os.environ['DUCKDB_PATH']);c.execute(open('sql/gates_by_country.sql').read());c.execute(open('sql/audit_checks.sql').read());print(c.execute('SELECT * FROM audit.gates_by_country').df());print(c.execute('SELECT table_name, country_code, COUNT(*) AS days, COUNT(*) FILTER (WHERE flagged) AS flagged_days, COUNT(*) FILTER (WHERE probable_cause = \'UNEXPLAINED\') AS unexplained FROM audit.volume_drift GROUP BY 1, 2 ORDER BY 1, 2').df())"
holidays:
	$(NOFILE); python ingestion/holiday_commercial_builder.py
test-volume-drift:
	python -m unittest discover -s tests -p 'test_volume_drift.py' -v
silver: holidays
	$(NOFILE); cd dbt_multidim && dbt deps && dbt run --select staging silver quarantine audit --exclude leakage_violations candidate_recall && dbt test --select staging silver quarantine audit --exclude leakage_violations candidate_recall
gold:
	$(NOFILE); python evaluation/build_anchor_grid.py
	$(NOFILE); cd dbt_multidim && dbt run --select gold leakage_violations candidate_recall && dbt test --select gold leakage_violations candidate_recall
train:
	$(NOFILE); python evaluation/train_eval_lambdarank.py --config full --delta 30
techniques:
	$(NOFILE); python evaluation/technique_comparisons.py --reps 3
ablation:
	$(NOFILE); python evaluation/run_ablation_2axes.py
docs:
	cd dbt_multidim && dbt docs generate && dbt docs serve
docs-figures:
	$(NOFILE); cd dbt_multidim && dbt docs generate && cd .. && python tools/lineage_graph.py && python tools/explain_figures.py
report-tables:
	$(NOFILE); python tools/report_tables.py
ml-test:
	python -m pytest ml/tests -q
ml-seq:
	$(NOFILE); python ml/common/sequences.py
ml-eval:
	$(NOFILE); python ml/eval/protocol.py --reeval p1_frozen --out t28
ml-views:
	python ml/common/data.py
ml-figures:
	python ml/analysis/export_tables.py
	python ml/analysis/figures.py
report-pdf:
	cd docs/report/hmtt && pdflatex -interaction=nonstopmode main.tex >/dev/null && bibtex -terse main && pdflatex -interaction=nonstopmode main.tex >/dev/null && pdflatex -interaction=nonstopmode -halt-on-error main.tex | grep -E 'Output written|^!'
ml-retrieval:
	$(NOFILE); for s in ease tifuknn rp3beta explin trend; do python ml/retrieval/$$s.py --tune --build || exit 1; done
	$(NOFILE); for c in SG TH VN; do python ml/retrieval/item2vec.py --build --countries $$c & done; wait
	$(NOFILE); python ml/retrieval/sasrec.py --tune --build & python ml/retrieval/two_tower.py --tune --build; wait
	$(NOFILE); python ml/retrieval/report.py && python ml/common/data.py
all: bronze gates silver gold train ablation

# Demo v0 on a public Hugging Face Space (anonymised reference, synthetic sample, anonymised real back-test sample published with
# the data owner's consent; the salt never leaves data/demo/)
DEMO_SPACE ?= yphan3103/nbr-demo
demo-reference:
	python serve/export_reference.py
	python serve/export_showcase.py
demo-push:
	python serve/build_space.py
	python serve/check_public.py --db --require-terms
	hf repos create $(DEMO_SPACE) --type space --sdk static --public --exist-ok
	hf upload $(DEMO_SPACE) data/demo/space . --repo-type space --delete "*"
