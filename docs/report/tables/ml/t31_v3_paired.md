# t31_v3_paired — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a             | b            | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:--------------|:-------------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| p1_frozen_v3  | p1_frozen_v2 | NDCG@20           |     39385 | -0.0009 | -0.0016 | -0.0003 |        0.0000 |
| p1_frozen_v3  | p1_frozen_v2 | HR@10             |     39385 | -0.0028 | -0.0048 | -0.0004 |        0.0110 |
| p1_frozen_v3  | p1_frozen_v2 | recall_repeat@20  |      8043 | -0.0021 | -0.0081 |  0.0045 |        0.2690 |
| p1_frozen_v3  | p1_frozen_v2 | recall_explore@20 |     37709 | -0.0025 | -0.0040 | -0.0009 |        0.0020 |
| p1_tuned_v3   | p1_tuned_v2  | NDCG@20           |     39385 | -0.0003 | -0.0008 |  0.0001 |        0.0890 |
| p1_tuned_v3   | p1_tuned_v2  | HR@10             |     39385 | -0.0006 | -0.0025 |  0.0011 |        0.2490 |
| p1_tuned_v3   | p1_tuned_v2  | recall_repeat@20  |      8043 | -0.0250 | -0.0294 | -0.0200 |        0.0000 |
| p1_tuned_v3   | p1_tuned_v2  | recall_explore@20 |     37709 |  0.0002 | -0.0011 |  0.0014 |        0.6000 |
| p3_v3_full    | p3_full      | NDCG@20           |     39385 |  0.0006 | -0.0000 |  0.0011 |        0.9660 |
| p3_v3_full    | p3_full      | HR@10             |     39385 |  0.0013 | -0.0008 |  0.0033 |        0.8880 |
| p3_v3_full    | p3_full      | recall_repeat@20  |      8043 | -0.0259 | -0.0312 | -0.0199 |        0.0000 |
| p3_v3_full    | p3_full      | recall_explore@20 |     37709 |  0.0042 |  0.0030 |  0.0054 |        1.0000 |
| p3_v3_onehead | p3_onehead   | NDCG@20           |     39385 |  0.0012 |  0.0007 |  0.0017 |        1.0000 |
| p3_v3_onehead | p3_onehead   | HR@10             |     39385 |  0.0020 |  0.0002 |  0.0037 |        0.9870 |
| p3_v3_onehead | p3_onehead   | recall_repeat@20  |      8043 |  0.0038 | -0.0007 |  0.0085 |        0.9430 |
| p3_v3_onehead | p3_onehead   | recall_explore@20 |     37709 |  0.0013 |  0.0001 |  0.0024 |        0.9860 |
