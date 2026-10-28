# Figures for the report and the demo (WBS 5.1, issue #44)

Generated files (reproducible):

| file | caption | how to regenerate |
|---|---|---|
| `lineage_full.svg` / `.png` | dbt lineage of the whole pipeline: Bronze sources → staging views → Silver → quarantine / audit → Gold; the anchor grid, model grid and split windows are built by `evaluation/build_anchor_grid.py` (component nodes) | `make docs-figures` |
| `lineage_bronze_to_silver.svg` / `.png` | Bronze → Silver detail with the quarantine and audit tables | `make docs-figures` |
| `lineage_silver_to_gold.svg` / `.png` | Silver → Gold detail: two feature entities, candidates, pairs, ranking dataset, leakage ledger | `make docs-figures` |
| `explain_analyze_asof_price.txt` | `EXPLAIN ANALYZE` of the ASOF price lookup at one anchor date (DuckDB 2.0, laptop) | `make docs-figures` |

Screenshots to take in DBeaver (read-only connection to `data/lakehouse.duckdb`, after `make gold`), saved here as PNG with the file names below:

| file | query | caption |
|---|---|---|
| `dbeaver_gates_by_country.png` | `SELECT * FROM audit.gates_by_country ORDER BY country, year;` | Go / no-go gates per country × year: member link, item match, price coverage, members with ≥ 2 transactions, decision |
| `dbeaver_quarantine_sales_line.png` | `SELECT reason, COUNT(*) AS lines, COUNT(DISTINCT transaction_id) AS transactions FROM quarantine.qrt_sales_line GROUP BY 1 ORDER BY 2 DESC;` | Sales lines refused by `slv_fact_sales_line`, by reason (nothing is dropped silently) |
| `dbeaver_gold_fs_member.png` | `SELECT member_id, anchor_date, split, tx_365d, days_since_last_tx, price_q50, promo_affinity, n_sports, usual_store_id, web_sessions_30d, web_data_available FROM gold.gld_fs_member WHERE split = 'test' ORDER BY anchor_date, member_id LIMIT 20;` | Member feature entity at the anchor (one row per used anchor, point-in-time) |
| `dbeaver_explain_asof.png` | the query in `explain_analyze_asof_price.txt`, run with DBeaver's *Explain execution plan* (or prefix `EXPLAIN ANALYZE`) | ASOF JOIN plan for the price at the anchor |
| `dbeaver_leakage_ledger.png` | `SELECT * FROM quarantine.leakage_violations;` (expected: no rows) and `SELECT * FROM audit.stitching_coverage ORDER BY 1, 2;` | QC-6 ledger empty; stitching coverage before / after per country |

Captions are in English for the report; the three-country versions come from the server lakehouse.
