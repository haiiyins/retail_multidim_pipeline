### MT3 cost × gain: what each removed source costs to process (profiler wall time of its models, Bronze load of its raw tables, peak RSS, output size) against what it adds to the Full ranker (Full − arm, bootstrap CI)

| removed | delta | gain ndcg20 | gain ndcg20 lo | gain ndcg20 hi | sig ndcg20 | gain hr10 | sig hr10 | gain recall50 | sig recall50 | models costed | model wall sec | bronze load sec | total cost sec | peak rss gb | output gb | train wall sec | ndcg20 gain per 1000s | models not profiled |
|---|---:|---:|---:|---:|---|---:|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---|
| B0: history + popularity only | 30 | 0.0179 | 0.0163 | 0.0195 | yes | 0.0271 | yes | 0.042 | yes | 6 | 1,268.1 | 5,253 | 6,521 | 82.1 | 89.32 | 282 | 0.0027 | gld_sport_department_affinity slv_user_member_links |
| −F5 web | 30 | 0.0161 | 0.0146 | 0.0175 | yes | 0.0232 | yes | 0.0324 | yes | 3 | 1,254.2 | 5,221 | 6,475 | 82.1 | 89.27 | 283 | 0.0025 | - |
| −R3 web | 30 | 0.0159 | 0.0147 | 0.0173 | yes | 0.0229 | yes | 0.0299 | yes | 3 | 1,254.2 | 5,221 | 6,475 | 82.1 | 89.27 | 286 | 0.0025 | slv_user_member_links |
| −F1 price | 30 | 0.0029 | 0.0019 | 0.0039 | yes | 0.0013 | no | 0.0103 | yes | 1 | 5.9 | 30 | 36 | 1.8 | 0.03 | 274 | 0.0806 | - |
| −R2 co-purchase | 30 | 0.0193 | 0.0177 | 0.0209 | yes | 0.0239 | yes | 0.0539 | yes | 1 | 19.5 | 0 | 20 | 14.8 | 0.13 | 260 | 0.965 | - |
| −sport | 30 | 0.0013 | 0.0004 | 0.0022 | yes | 0.002 | no | 0.0064 | yes | 1 | 4.2 | 1 | 6 | 0.6 | 0.02 | 286 | 0.2167 | - |
| −R4 sport × offer | 30 | 0.0012 | 0.0002 | 0.0021 | yes | 0.0005 | no | 0.0021 | no | 1 | 4.2 | 1 | 6 | 0.6 | 0.02 | 285 | 0.2 | gld_sport_department_affinity |
| −F3 promotion & calendar | 30 | 0.0005 | -0.0005 | 0.0015 | no | 0.0011 | no | 0.0031 | no | 1 | 3.7 | 0 | 4 | 0.2 | 0 | 281 | 0.125 | - |
| −R1 repurchase | 30 | 0.1113 | 0.1081 | 0.1144 | yes | 0.1744 | yes | 0.2101 | yes | 0 | 0 | 0 | 0 | 0 | 0 | 270 |  | - |
| −R5 best-sellers | 30 | 0.1061 | 0.1034 | 0.1095 | yes | 0.1816 | yes | 0.2492 | yes | 0 | 0 | 0 | 0 | 0 | 0 | 196 |  | - |
| B0: history + popularity only | 90 | 0.0128 | 0.0122 | 0.0136 | yes | 0.0188 | yes | 0.0327 | yes | 6 | 1,268.1 | 5,253 | 6,521 | 82.1 | 89.32 | 619 | 0.002 | gld_sport_department_affinity slv_user_member_links |
| −F5 web | 90 | 0.0076 | 0.0069 | 0.0083 | yes | 0.0123 | yes | 0.0147 | yes | 3 | 1,254.2 | 5,221 | 6,475 | 82.1 | 89.27 | 641 | 0.0012 | - |
| −R3 web | 90 | 0.0081 | 0.0073 | 0.0088 | yes | 0.0125 | yes | 0.0154 | yes | 3 | 1,254.2 | 5,221 | 6,475 | 82.1 | 89.27 | 647 | 0.0013 | slv_user_member_links |
| −F1 price | 90 | 0.0027 | 0.0022 | 0.0034 | yes | 0.0023 | yes | 0.0084 | yes | 1 | 5.9 | 30 | 36 | 1.8 | 0.03 | 637 | 0.075 | - |
| −R2 co-purchase | 90 | 0.0153 | 0.0144 | 0.0162 | yes | 0.0205 | yes | 0.0404 | yes | 1 | 19.5 | 0 | 20 | 14.8 | 0.13 | 584 | 0.765 | - |
| −sport | 90 | -0.0001 | -0.0006 | 0.0004 | no | 0.0001 | no | -0.0014 | no | 1 | 4.2 | 1 | 6 | 0.6 | 0.02 | 641 | -0.0167 | - |
| −R4 sport × offer | 90 | 0.0004 | -0.0001 | 0.0009 | no | 0.001 | no | -0.0004 | no | 1 | 4.2 | 1 | 6 | 0.6 | 0.02 | 648 | 0.0667 | gld_sport_department_affinity |
| −F3 promotion & calendar | 90 | 0.0008 | 0.0003 | 0.0013 | yes | 0.0002 | no | 0.0051 | yes | 1 | 3.7 | 0 | 4 | 0.2 | 0 | 646 | 0.2 | - |
| −R1 repurchase | 90 | 0.1091 | 0.1071 | 0.1111 | yes | 0.176 | yes | 0.2035 | yes | 0 | 0 | 0 | 0 | 0 | 0 | 606 |  | - |
| −R5 best-sellers | 90 | 0.1052 | 0.1033 | 0.1068 | yes | 0.1877 | yes | 0.2397 | yes | 0 | 0 | 0 | 0 | 0 | 0 | 445 |  | - |

*Source:* `data/audit/mt3_table.csv` (`evaluation/mt3_table.py` over `audit.model_cost`, `audit.pipeline_run_metrics`, `audit.ablation_runs` and the bootstrap CSVs). *Generated:* 2026-10-29 08:50 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. Experiment files of the three-country server run (2026-10-28), copied into `data/audit/`. Costs are lower bounds: models the profiler did not time cost 0 and are listed.
