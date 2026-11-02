# t31_seeds_paired — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a                | b                 | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:-----------------|:------------------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| p3_onehead       | p1_tuned_v2       | NDCG@20           |     39385 |  0.0009 |  0.0002 |  0.0016 |        0.9930 |
| p3_onehead       | p1_tuned_v2       | recall_explore@20 |     37709 | -0.0016 | -0.0029 | -0.0002 |        0.0150 |
| p3_onehead_seed1 | p1_tuned_v2_seed1 | NDCG@20           |     39385 |  0.0010 |  0.0003 |  0.0017 |        0.9940 |
| p3_onehead_seed1 | p1_tuned_v2_seed1 | recall_explore@20 |     37709 | -0.0002 | -0.0016 |  0.0012 |        0.4020 |
| p3_onehead_seed2 | p1_tuned_v2_seed2 | NDCG@20           |     39385 |  0.0006 | -0.0000 |  0.0013 |        0.9730 |
| p3_onehead_seed2 | p1_tuned_v2_seed2 | recall_explore@20 |     37709 | -0.0023 | -0.0038 | -0.0009 |        0.0000 |
| p3_onehead_seed1 | p1_tuned_v2       | NDCG@20           |     39385 |  0.0011 |  0.0004 |  0.0018 |        1.0000 |
| p3_onehead_seed1 | p1_tuned_v2       | recall_explore@20 |     37709 |  0.0000 | -0.0013 |  0.0014 |        0.5160 |
| p3_onehead_seed2 | p1_tuned_v2       | NDCG@20           |     39385 |  0.0011 |  0.0005 |  0.0018 |        1.0000 |
| p3_onehead_seed2 | p1_tuned_v2       | recall_explore@20 |     37709 | -0.0007 | -0.0021 |  0.0005 |        0.1350 |
| p3_onehead       | p3_full           | NDCG@20           |     39385 |  0.0011 |  0.0007 |  0.0016 |        1.0000 |
| p3_onehead       | p3_full           | recall_explore@20 |     37709 |  0.0016 |  0.0007 |  0.0025 |        1.0000 |
| p3_onehead_seed1 | p3_full_seed1     | NDCG@20           |     39385 |  0.0018 |  0.0012 |  0.0023 |        1.0000 |
| p3_onehead_seed1 | p3_full_seed1     | recall_explore@20 |     37709 | -0.0017 | -0.0028 | -0.0007 |        0.0000 |
| p3_onehead_seed2 | p3_full_seed2     | NDCG@20           |     39385 |  0.0011 |  0.0007 |  0.0016 |        1.0000 |
| p3_onehead_seed2 | p3_full_seed2     | recall_explore@20 |     37709 |  0.0010 |  0.0002 |  0.0018 |        0.9890 |
