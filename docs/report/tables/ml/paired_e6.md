# paired_e6 — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a             | b           | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:--------------|:------------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| p1_tuned_v2r1 | p1_tuned_v2 | NDCG@20           |     39385 |  0.0004 | -0.0001 |  0.0009 |        0.9270 |
| p1_tuned_v2r1 | p1_tuned_v2 | recall_repeat@20  |      8043 | -0.0116 | -0.0164 | -0.0070 |        0.0000 |
| p1_tuned_v2r1 | p1_tuned_v2 | recall_explore@20 |     37709 |  0.0010 | -0.0002 |  0.0022 |        0.9500 |
