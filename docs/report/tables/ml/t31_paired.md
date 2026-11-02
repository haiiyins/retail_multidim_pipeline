# t31_paired — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a            | b            | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:-------------|:-------------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| p1_frozen_v2 | p1_frozen    | NDCG@20           |     39385 |  0.0025 |  0.0018 |  0.0032 |        1.0000 |
| p1_frozen_v2 | p1_frozen    | HR@10             |     39385 |  0.0052 |  0.0027 |  0.0076 |        1.0000 |
| p1_frozen_v2 | p1_frozen    | recall_repeat@20  |      8043 | -0.0315 | -0.0376 | -0.0252 |        0.0000 |
| p1_frozen_v2 | p1_frozen    | recall_explore@20 |     37709 |  0.0101 |  0.0084 |  0.0116 |        1.0000 |
| p1_tuned_v2  | p1_frozen_v2 | NDCG@20           |     39385 |  0.0039 |  0.0032 |  0.0045 |        1.0000 |
| p1_tuned_v2  | p1_frozen_v2 | HR@10             |     39385 |  0.0091 |  0.0069 |  0.0114 |        1.0000 |
| p1_tuned_v2  | p1_frozen_v2 | recall_repeat@20  |      8043 |  0.0239 |  0.0183 |  0.0296 |        1.0000 |
| p1_tuned_v2  | p1_frozen_v2 | recall_explore@20 |     37709 |  0.0085 |  0.0069 |  0.0101 |        1.0000 |
| p2_v2        | p1_tuned_v2  | NDCG@20           |     39385 |  0.0002 | -0.0002 |  0.0006 |        0.8410 |
| p2_v2        | p1_tuned_v2  | HR@10             |     39385 |  0.0006 | -0.0011 |  0.0022 |        0.7570 |
| p2_v2        | p1_tuned_v2  | recall_repeat@20  |      8043 | -0.0102 | -0.0143 | -0.0062 |        0.0000 |
| p2_v2        | p1_tuned_v2  | recall_explore@20 |     37709 |  0.0007 | -0.0004 |  0.0019 |        0.8850 |
| p3_full      | p1_tuned_v2  | NDCG@20           |     39385 | -0.0002 | -0.0009 |  0.0005 |        0.2740 |
| p3_full      | p1_tuned_v2  | HR@10             |     39385 | -0.0019 | -0.0042 |  0.0003 |        0.0470 |
| p3_full      | p1_tuned_v2  | recall_repeat@20  |      8043 |  0.0287 |  0.0223 |  0.0350 |        1.0000 |
| p3_full      | p1_tuned_v2  | recall_explore@20 |     37709 | -0.0031 | -0.0045 | -0.0018 |        0.0000 |
| p3_onehead   | p1_tuned_v2  | NDCG@20           |     39385 |  0.0009 |  0.0002 |  0.0016 |        0.9930 |
| p3_onehead   | p1_tuned_v2  | HR@10             |     39385 |  0.0006 | -0.0016 |  0.0028 |        0.6830 |
| p3_onehead   | p1_tuned_v2  | recall_repeat@20  |      8043 |  0.0214 |  0.0154 |  0.0275 |        1.0000 |
| p3_onehead   | p1_tuned_v2  | recall_explore@20 |     37709 | -0.0016 | -0.0029 | -0.0002 |        0.0150 |
| p3_onehead   | p2_v2        | NDCG@20           |     39385 |  0.0007 |  0.0000 |  0.0014 |        0.9800 |
| p3_onehead   | p2_v2        | HR@10             |     39385 | -0.0000 | -0.0022 |  0.0022 |        0.5060 |
| p3_onehead   | p2_v2        | recall_repeat@20  |      8043 |  0.0316 |  0.0258 |  0.0378 |        1.0000 |
| p3_onehead   | p2_v2        | recall_explore@20 |     37709 | -0.0023 | -0.0037 | -0.0010 |        0.0000 |
| p1_tuned_v2  | tifuknn_nbr  | NDCG@20           |     39385 |  0.0224 |  0.0214 |  0.0234 |        1.0000 |
| p1_tuned_v2  | tifuknn_nbr  | HR@10             |     39385 |  0.0525 |  0.0495 |  0.0556 |        1.0000 |
| p1_tuned_v2  | tifuknn_nbr  | recall_repeat@20  |      8043 | -0.0682 | -0.0763 | -0.0604 |        0.0000 |
| p1_tuned_v2  | tifuknn_nbr  | recall_explore@20 |     37709 |  0.0488 |  0.0469 |  0.0507 |        1.0000 |
