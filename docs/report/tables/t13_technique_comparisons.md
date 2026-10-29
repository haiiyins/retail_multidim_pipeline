### Four with / without technique comparisons (median wall time of child processes, peak RSS)

| comparison | country | baseline | technique | rows processed | baseline sec | technique sec | speedup | baseline peak GB | technique peak GB | reps | threads | memory limit |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| asof_vs_explode | VN | daily_explode | asof | 14,948,738 | 2.07 | 1.31 | 1.6 | 2.86 | 1.74 | 3 | 16 | 80GB |
| parquet_vs_csv | VN | csv | parquet | 124 | 0.71 | 0.1 | 6.9 | 0.99 | 0.08 | 3 | 16 | 80GB |
| projection | VN | all_columns | needed_columns | 2,807,686 | 13.58 | 1.54 | 8.8 | 9.3 | 2.5 | 3 | 16 | 80GB |
| regex_vs_python | VN | python_rowwise | sql_regex | 6,445,762 | 44.72 | 2.94 | 15.2 | 21.34 | 6.62 | 3 | 16 | 80GB |

*Source:* `audit.technique_comparisons` (`evaluation/technique_comparisons.py`, `make techniques`). *Generated:* 2026-10-29 11:59 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
