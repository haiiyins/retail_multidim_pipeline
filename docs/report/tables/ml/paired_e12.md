# paired_e12 — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a                    | b                    | metric            |   members |   diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:---------------------|:---------------------|:------------------|----------:|-------:|--------:|--------:|--------------:|
| p1_frozen_allfeat_v2 | p1_frozen_v2         | NDCG@20           |     39385 | 0.0028 |  0.0021 |  0.0035 |        1.0000 |
| p1_frozen_allfeat_v2 | p1_frozen_v2         | recall_repeat@20  |      8043 | 0.0004 | -0.0054 |  0.0062 |        0.5530 |
| p1_frozen_allfeat_v2 | p1_frozen_v2         | recall_explore@20 |     37709 | 0.0069 |  0.0052 |  0.0086 |        1.0000 |
| p1_tuned_v2          | p1_frozen_allfeat_v2 | NDCG@20           |     39385 | 0.0011 |  0.0005 |  0.0016 |        1.0000 |
| p1_tuned_v2          | p1_frozen_allfeat_v2 | recall_repeat@20  |      8043 | 0.0235 |  0.0176 |  0.0293 |        1.0000 |
| p1_tuned_v2          | p1_frozen_allfeat_v2 | recall_explore@20 |     37709 | 0.0016 |  0.0002 |  0.0030 |        0.9870 |
