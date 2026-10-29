# Figures for the report and the demo (WBS 5.1, issue #44)

Generated files (reproducible). Lineage layout (`tools/lineage_graph.py`): columns are dependency depth — Bronze sources in the first
column, every model one column right of its deepest input — so each column reads as one stage; colours mark the layer (legend in the
figure); edges are orthogonal; the three Gold tables built by `evaluation/build_anchor_grid.py` appear as components with the Silver
tables the script reads as inputs.

| file | caption | how to regenerate |
|---|---|---|
| `lineage_full.svg` / `.png` | dbt lineage of the whole pipeline: Bronze sources → staging views → Silver → quarantine / audit → Gold; the anchor grid, model grid and split windows are built by `evaluation/build_anchor_grid.py` (component nodes) | `make docs-figures` |
| `lineage_bronze_to_silver.svg` / `.png` | Bronze → Silver detail with the quarantine and audit tables | `make docs-figures` |
| `lineage_silver_to_gold.svg` / `.png` | Silver → Gold detail: two feature entities, candidates, pairs, ranking dataset, leakage ledger | `make docs-figures` |
| `scale_test.png`, `scale_test_months.png` | Silver → Gold wall time against Bronze sales rows: countries axis VN → VN + TH → VN + TH + SG and months axis 3 / 12 / 36 of VN (server 2026-10-29, 16 threads, 80 GB; report §5.9, issue #42) | `python evaluation/scale_test.py VN TH SG` and `… VN --months 3,12,36` write `data/audit/scale_test*.png`; copied here |
| `explain_analyze_asof_price.txt` | `EXPLAIN ANALYZE` of the ASOF price lookup at one anchor date (DuckDB 2.0, laptop) | `make docs-figures` |

Terminal evidence (screenshots of the server log, prompt line cropped so that no host or account name appears):

| file | caption | source |
|---|---|---|
| `dbt_tests_gold_server.png` | dbt test summary of the full three-country Gold run: 64 tests PASS, 0 WARN, 0 ERROR (QC-6 leakage rules included), server 2026-10-28 13:16 UTC | `data/pipeline_all_try8.log` on the server, block `### gold_test` (issue #36) |

Screenshots to take in DBeaver, saved here as PNG with the file names below. The EXPLAIN one is taken on the laptop lakehouse (read-only
connection to `data/lakehouse.duckdb`); the four data screenshots are taken on `evidence_3c.duckdb`, a small extract of the server
lakehouse (`audit.gates_by_country`, `audit.stitching_coverage`, `audit.volume_drift`, `audit.candidate_recall`,
`quarantine.leakage_violations`, `quarantine.qrt_sales_line`, `gold.gld_fs_member`, written with `ATTACH … (READ_ONLY)` + `CREATE TABLE AS`
once the experiment chain has released the lock, then copied to the laptop and never committed). No screenshot shows member, user or
transaction identifiers:

| file | query | caption |
|---|---|---|
| `dbeaver_gates_by_country.png` | `SELECT * FROM audit.gates_by_country ORDER BY country, year;` | Go / no-go gates per country × year: member link, item match, price coverage, members with ≥ 2 transactions, decision |
| `dbeaver_quarantine_sales_line.png` | `SELECT country_code, reason, COUNT(*) AS lines, COUNT(DISTINCT transaction_id) AS transactions FROM quarantine.qrt_sales_line GROUP BY 1, 2 ORDER BY 1, 3 DESC;` | Sales lines refused by `slv_fact_sales_line`, by country and reason (nothing is dropped silently) |
| `dbeaver_gold_fs_member.png` | `SELECT country_code, anchor_date, split, tx_365d, days_since_last_tx, price_q50, promo_affinity, n_sports, web_sessions_30d, web_data_available FROM gold.gld_fs_member WHERE split = 'test' ORDER BY anchor_date LIMIT 20;` (no `member_id`) | Member feature entity at the anchor (one row per used anchor, point-in-time) |
| `dbeaver_explain_asof.png` | the query in `explain_analyze_asof_price.txt` prefixed with `EXPLAIN ANALYZE`, plan shown in the Value panel (taken 2026-10-29, laptop lakehouse, VN) | ASOF JOIN plan for the price at the anchor: 0.123 s, `Asof Join` LEFT on item, country and anchor date, median per model |
| `dbeaver_leakage_ledger.png` | `SELECT * FROM quarantine.leakage_violations;` (expected: no rows) and `SELECT * FROM audit.stitching_coverage ORDER BY 1, 2;` | QC-6 ledger empty; stitching coverage before / after per country |

Captions are in English for the report; the data screenshots show the three-country server build.
