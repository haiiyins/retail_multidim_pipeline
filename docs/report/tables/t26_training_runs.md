### Training runs of the ablation on the server (16 threads): wall time per arm and horizon; no dbt rebuild per arm (cost measured once by the profiler)

| config | delta | train wall sec | dbt wall sec | executed at |
|---|---:|---:|---:|---|
| full | 30 | 283 | 0 | 2026-10-28 17:14 |
| full | 90 | 685 | 0 | 2026-10-28 17:25 |
| b0 | 30 | 282 | 0 | 2026-10-28 17:30 |
| b0 | 90 | 619 | 0 | 2026-10-28 17:40 |
| no_f1 | 30 | 274 | 0 | 2026-10-28 17:45 |
| no_f1 | 90 | 637 | 0 | 2026-10-28 17:55 |
| no_f3 | 30 | 281 | 0 | 2026-10-28 18:00 |
| no_f3 | 90 | 646 | 0 | 2026-10-28 18:11 |
| no_f5 | 30 | 283 | 0 | 2026-10-28 18:16 |
| no_f5 | 90 | 641 | 0 | 2026-10-28 18:26 |
| no_sport | 30 | 286 | 0 | 2026-10-28 18:31 |
| no_sport | 90 | 641 | 0 | 2026-10-28 18:42 |
| no_r1 | 30 | 270 | 0 | 2026-10-28 18:46 |
| no_r1 | 90 | 606 | 0 | 2026-10-28 18:56 |
| no_r2 | 30 | 260 | 0 | 2026-10-28 19:01 |
| no_r2 | 90 | 584 | 0 | 2026-10-28 19:10 |
| no_r3 | 30 | 286 | 0 | 2026-10-28 19:15 |
| no_r3 | 90 | 647 | 0 | 2026-10-28 19:26 |
| no_r4 | 30 | 285 | 0 | 2026-10-28 19:31 |
| no_r4 | 90 | 648 | 0 | 2026-10-28 19:41 |
| no_r5 | 30 | 196 | 0 | 2026-10-28 19:45 |
| no_r5 | 90 | 445 | 0 | 2026-10-28 19:52 |

*Source:* `data/audit/ablation_runs.csv` (`audit.ablation_runs`, `evaluation/run_ablation_2axes.py`). *Generated:* 2026-10-29 04:32 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. Experiment files of the three-country server run (2026-10-28), copied into `data/audit/`. Hyper-parameters frozen by the Full Δ30 run (`evaluation/frozen_params.json`): 192 boosting rounds (early stopping on validation NDCG@20), num_leaves 63, learning_rate 0.05, feature_fraction 0.8, bagging_fraction 0.8; every arm reuses them.
