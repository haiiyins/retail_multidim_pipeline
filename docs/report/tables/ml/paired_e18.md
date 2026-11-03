# paired_e18 — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a              | b           | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:---------------|:------------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| sasrec_all_nbr | sasrec_nbr  | NDCG@20           |     39385 |  0.0146 |  0.0135 |  0.0157 |        1.0000 |
| sasrec_all_nbr | sasrec_nbr  | recall_repeat@20  |      8043 |  0.1361 |  0.1279 |  0.1447 |        1.0000 |
| sasrec_all_nbr | sasrec_nbr  | recall_explore@20 |     37709 |  0.0009 | -0.0005 |  0.0023 |        0.9020 |
| sasrec_all_nbr | tifuknn_nbr | NDCG@20           |     39385 | -0.0036 | -0.0049 | -0.0025 |        0.0000 |
| sasrec_all_nbr | tifuknn_nbr | recall_repeat@20  |      8043 | -0.3137 | -0.3245 | -0.3031 |        0.0000 |
| sasrec_all_nbr | tifuknn_nbr | recall_explore@20 |     37709 |  0.0250 |  0.0232 |  0.0267 |        1.0000 |
