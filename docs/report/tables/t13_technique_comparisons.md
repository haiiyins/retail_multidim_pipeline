### Four with / without technique comparisons (median wall time of child processes, peak RSS)

| comparison | country | baseline | technique | rows processed | baseline sec | technique sec | speedup | baseline peak GB | technique peak GB | reps | threads | memory limit |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| asof_vs_explode | VN | daily_explode | asof | 14,948,738 | 1.02 | 0.77 | 1.3 | 2.82 | 1.47 | 3 | 8 | 15GB |
| parquet_vs_csv | VN | csv | parquet | 124 | 0.36 | 0.05 | 6.6 | 0.46 | 0 | 3 | 8 | 15GB |
| projection | VN | all_columns | needed_columns | 2,807,686 | 3.41 | 0.51 | 6.7 | 5.73 | 1.65 | 3 | 8 | 15GB |
| regex_vs_python | VN | python_rowwise | sql_regex | 589,463 | 1.5 | 0.51 | 2.9 | 3.05 | 1.15 | 3 | 8 | 15GB |

*Source:* `audit.technique_comparisons` (`evaluation/technique_comparisons.py`, `make techniques`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
