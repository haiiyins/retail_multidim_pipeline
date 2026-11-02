# t32_paired — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a            | b       | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:-------------|:--------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| p3_onehead   | p3_full | NDCG@20           |     39385 |  0.0011 |  0.0007 |  0.0016 |        1.0000 |
| p3_onehead   | p3_full | HR@10             |     39385 |  0.0025 |  0.0007 |  0.0041 |        0.9970 |
| p3_onehead   | p3_full | recall_repeat@20  |      8043 | -0.0073 | -0.0128 | -0.0024 |        0.0020 |
| p3_onehead   | p3_full | recall_explore@20 |     37709 |  0.0016 |  0.0007 |  0.0025 |        1.0000 |
| p3_fixedgate | p3_full | NDCG@20           |     39385 | -0.0066 | -0.0074 | -0.0058 |        0.0000 |
| p3_fixedgate | p3_full | HR@10             |     39385 | -0.0105 | -0.0132 | -0.0079 |        0.0000 |
| p3_fixedgate | p3_full | recall_repeat@20  |      8043 | -0.2753 | -0.2845 | -0.2661 |        0.0000 |
| p3_fixedgate | p3_full | recall_explore@20 |     37709 |  0.0159 |  0.0149 |  0.0169 |        1.0000 |
| p3_noseq     | p3_full | NDCG@20           |     39385 | -0.0003 | -0.0007 |  0.0000 |        0.0280 |
| p3_noseq     | p3_full | HR@10             |     39385 |  0.0001 | -0.0012 |  0.0014 |        0.5660 |
| p3_noseq     | p3_full | recall_repeat@20  |      8043 | -0.0240 | -0.0282 | -0.0200 |        0.0000 |
| p3_noseq     | p3_full | recall_explore@20 |     37709 |  0.0020 |  0.0013 |  0.0028 |        1.0000 |
