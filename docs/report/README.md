# Final report — chapter drafts

Drafts of the report chapters, written so that they can be pasted into the shared document. Every number is taken from a table in
[`tables/`](tables/INDEX.md), which `make report-tables` (`tools/report_tables.py`) regenerates from the lakehouse; no number is typed
by hand. Every table carries the **three-country server build of 2026-10-28 – 29** (`COUNTRY_FILTER=ALL`, Bronze → Gold, experiments,
cost profiler, scale test and technique comparisons on the same machine); `tables/INDEX.md` shows the build and time of every table.

| Chapter | File | RUNBOOK §9 items | Issue |
|---|---|---|---|
| 2. Data | [ch2_data.md](ch2_data.md) | 1 — profile of the 11 tables, nested columns, country list and date spans; data facts confirmed by the owner | #45 |
| 3. Data processing | [ch3_processing.md](ch3_processing.md) | technique-by-technique mapping to course topics; Bronze, Silver, calendar, stitching, Gold overview; technique comparisons (item 9, second half) | #45 |
| 4. Quality evidence | [ch4_quality.md](ch4_quality.md) | 2 — gates and PASS / REVIEW grouping; 3 — stock, price and inter-purchase audits; 4 — stitching before / after; 5 — inferred commercial events; dbt tests and the leakage ledger | #45 |
| 5. Feature store, candidates, experiments, results | [ch5_results.md](ch5_results.md) | 6 — candidate recall per source (`t12`); 7 — Full by country and segment, B0 vs Full and the ablation arms with CI (`t22`, `t23`, `t26`); 8 — cost × gain (`t24`), feature importance (`t25`); 9 — scale test (§5.9, filled after the run of 2026-10-29) and the technique comparisons of chapter 3 | #46 |

Conventions used in the drafts:

- A table reference such as **(t04)** points to `tables/t04_gates.md`; the Markdown table can be pasted as is, the CSV next to it feeds a
  spreadsheet or a plot.
- Figures: `docs/figures/` holds the dbt lineage graphs (`lineage_full.png`, `lineage_bronze_to_silver.png`, `lineage_silver_to_gold.png`),
  the `EXPLAIN ANALYZE` of the ASOF price lookup, and the list of DBeaver screenshots to take (`docs/figures/README.md`).
- Design rationale is quoted from `docs/DESIGN_DECISIONS.md` (§ numbers) and the procedure from `docs/RUNBOOK.md` (step numbers), so the
  report never contradicts the repository.
- No organisation names, personal paths or member-level data appear in the drafts or the tables (`REDACT_TERMS` is applied when the
  tables are generated; the submission checklist, issue #48, greps the report again).
