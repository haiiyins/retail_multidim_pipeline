### Top-20 features of the Full ranker by LightGBM gain (Δ = 30) and their share of the total gain

| rank no | feature | gain | share pct |
|---:|---|---:|---:|
| 1 | hist_qty | 97,335.0 | 13.93 |
| 2 | candidate_rank | 76,724.0 | 10.98 |
| 3 | score_r5 | 40,803.0 | 5.84 |
| 4 | popularity_rank | 38,139.0 | 5.46 |
| 5 | hist_buy_cnt | 37,087.0 | 5.31 |
| 6 | score_r1 | 26,200.0 | 3.75 |
| 7 | days_since_bought | 22,098.0 | 3.16 |
| 8 | days_since_dept_buy | 21,457.0 | 3.07 |
| 9 | qty_28d | 20,296.0 | 2.91 |
| 10 | models_365d | 19,231.0 | 2.75 |
| 11 | n_sku_priced | 18,317.0 | 2.62 |
| 12 | buyers_28d | 17,762.0 | 2.54 |
| 13 | price_q50_eur | 16,025.0 | 2.29 |
| 14 | copurchase_lift_mean | 15,963.0 | 2.29 |
| 15 | price_local | 15,941.0 | 2.28 |
| 16 | price_gap_q50 | 14,651.0 | 2.1 |
| 17 | copurchase_lift_max | 14,171.0 | 2.03 |
| 18 | r1 | 14,075.0 | 2.01 |
| 19 | dept_overdue_ratio | 10,827.0 | 1.55 |
| 20 | model_age_days | 9,450.0 | 1.35 |

*Source:* `data/audit/importance_full_d30.csv` (`evaluation/train_eval_lambdarank.py`). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`. Experiment files of the three-country server run (2026-10-28), copied into `data/audit/`.
