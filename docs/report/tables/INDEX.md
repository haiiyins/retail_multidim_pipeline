# Report tables

Generated 2026-10-28 10:07 UTC by `tools/report_tables.py` (`make report-tables`) with `COUNTRY_FILTER=VN`. Each file carries its source; the CSV next to it holds the same rows. Regenerate on the server after `make gold` so that the three-country numbers replace the laptop (VN) ones.

- [The eleven source tables: raw format, contract key, Bronze partitioning and loaded volume](t01_source_tables.md) — `ingestion/table_contracts.yml`, `ingestion/raw_source.py`, `audit.pipeline_run_metrics` (layer bronze, latest load per table)
- [Sales lines from Bronze to Silver: exact duplicates, line keys, netting and what is kept](t02_sales_funnel.md) — `staging.stg_sales_detail`, `silver.slv_fact_sales_line`, `silver.slv_fact_returns`, `quarantine.qrt_sales_line` (dedup and netting rules in `slv_sales_line_netted.sql`)
- [Quarantined sales rows by reason (QC-3 / QC-4 routing)](t03_quarantine_sales.md) — `quarantine.qrt_sales_line` (`models/quarantine/qrt_sales_line.sql`)
- [Go / no-go gates per country × year (thresholds 60 / 95 / 90 % and 20,000 members)](t04_gates.md) — `audit.gates_by_country` (`sql/gates_by_country.sql`, `make gates`)
- [Audit checks: stock-table coverage, in-country price uniformity, inter-purchase gaps, date span](t05_audit_checks.md) — `audit.stock_coverage`, `audit.price_uniformity`, `audit.interpurchase_days`, `audit.date_span` (`sql/audit_checks.sql`)
- [SKU price intervals: raw price rows by business-unit type, national intervals by price type, quarantine](t06_price_intervals.md) — `bronze.all_store_selling_price`, `silver.slv_price_sku_interval`, `quarantine.qrt_price_interval`
- [Commercial events inferred from the temporary-promotion share (≥ 3 consecutive peak days), named by the team dictionary](t07_calendar_events.md) — `silver.slv_calendar_enriched` (`models/silver/slv_calendar_enriched.sql`), `ext.commercial_event_names`
- [Enriched calendar per country: holidays, event days, promotion share](t07b_calendar_summary.md) — `silver.slv_calendar_enriched`, `ext.public_holidays` (`ingestion/holiday_commercial_builder.py`)
- [Identity stitching at event level: share of web events with a member before (DIRECT) and after (+ STITCHED)](t08_stitching_events.md) — `audit.stitching_coverage` (`models/audit/stitching_coverage.sql`), `silver.slv_web_events_clean`, `silver.slv_user_to_member`, `quarantine.slv_identity_conflicts`
- [Identity stitching at anchor level: used anchors whose member has an attributed web event in the 30 days before, known at the anchor](t09_stitching_anchors.md) — `gold.anchor_grid`, `gold.gld_web_stitched`, `gold.gld_fs_member.web_data_available` (RUNBOOK §5 query)
- [Anchor grid: every Monday after the second purchase, then the label-horizon rule, the training stride and the per-country cap](t10_anchor_funnel.md) — `gold.anchor_grid` (`evaluation/build_anchor_grid.py`, `evaluation/split.yml`)
- [Silver, quarantine, Gold and audit tables: rows and on-disk size](t11_layer_sizes.md) — `duckdb_tables()`, `pragma_storage_info()` (distinct storage blocks × block size)
- [Candidate recall@200 overall and per source (R1 repurchase, R2 co-purchase, R3 web, R4 sport × offer, R5 best-sellers)](t12_candidate_recall.md) — `audit.candidate_recall` (`models/audit/candidate_recall.sql`)
- [Four with / without technique comparisons (median wall time of child processes, peak RSS)](t13_technique_comparisons.md) — `audit.technique_comparisons` (`evaluation/technique_comparisons.py`, `make techniques`)
- [dbt models and tests per layer (generic + singular), from the compiled manifest](t14_dbt_tests.md) — `dbt_multidim/target/manifest.json` (`dbt parse`)
- [Sale lines by channel and the timezone fallback (website units carry no timezone; the country's is used)](t15_channel_timezone.md) — `silver.slv_fact_sales_line` (`transaction_ts_utc` derivation)
- [Catalogue coverage of sold SKUs and the model-level catalogue after the fixture exclusion](t16_catalogue.md) — `bronze.dim_item`, `staging.stg_sales_detail`, `silver.slv_dim_model`
- [Members: profiles, excluded accounts, favourite-sport and usual-store state](t17_members.md) — `silver.slv_member_profile`, `silver.slv_member_bridge`, `silver.slv_member_sport_asof`, `silver.slv_member_store_daily`
- [Sale − cancel netting check: transactions with both line kinds, and how many survive with positive net quantity](t18_sale_cancel_check.md) — `staging.stg_sales_detail`, `silver.slv_fact_sales_line` (RUNBOOK §5 manual check, automated)
- [Cost per dbt model rebuilt alone: wall time, peak RSS, output rows and bytes (latest profile per model)](t19_model_cost.md) — `audit.model_cost` (`evaluation/pipeline_cost_profiler.py`)
