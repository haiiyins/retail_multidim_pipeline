# t31_hist_paired — paired member bootstrap (test, TH + VN, Δ = 30, 1 000 resamples), diff = a − b

| a           | b           | metric            |   members |    diff |   ci_lo |   ci_hi |   P(diff > 0) |
|:------------|:------------|:------------------|----------:|--------:|--------:|--------:|--------------:|
| p1_hist_v2  | gptopfreq   | NDCG@20           |     39385 |  0.0214 |  0.0204 |  0.0225 |        1.0000 |
| p1_hist_v2  | gptopfreq   | HR@10             |     39385 |  0.0465 |  0.0436 |  0.0495 |        1.0000 |
| p1_hist_v2  | gptopfreq   | recall_repeat@20  |      8043 | -0.0524 | -0.0598 | -0.0452 |        0.0000 |
| p1_hist_v2  | gptopfreq   | recall_explore@20 |     37709 |  0.0433 |  0.0413 |  0.0455 |        1.0000 |
| p1_hist_v2  | tifuknn_nbr | NDCG@20           |     39385 |  0.0178 |  0.0169 |  0.0188 |        1.0000 |
| p1_hist_v2  | tifuknn_nbr | HR@10             |     39385 |  0.0433 |  0.0405 |  0.0462 |        1.0000 |
| p1_hist_v2  | tifuknn_nbr | recall_repeat@20  |      8043 | -0.0596 | -0.0672 | -0.0521 |        0.0000 |
| p1_hist_v2  | tifuknn_nbr | recall_explore@20 |     37709 |  0.0411 |  0.0392 |  0.0431 |        1.0000 |
| p1_tuned_v2 | p1_hist_v2  | NDCG@20           |     39385 |  0.0045 |  0.0039 |  0.0052 |        1.0000 |
| p1_tuned_v2 | p1_hist_v2  | HR@10             |     39385 |  0.0092 |  0.0073 |  0.0113 |        1.0000 |
| p1_tuned_v2 | p1_hist_v2  | recall_repeat@20  |      8043 | -0.0086 | -0.0135 | -0.0040 |        0.0000 |
| p1_tuned_v2 | p1_hist_v2  | recall_explore@20 |     37709 |  0.0077 |  0.0063 |  0.0091 |        1.0000 |
| p3_onehead  | p1_hist_v2  | NDCG@20           |     39385 |  0.0054 |  0.0046 |  0.0062 |        1.0000 |
| p3_onehead  | p1_hist_v2  | HR@10             |     39385 |  0.0098 |  0.0074 |  0.0122 |        1.0000 |
| p3_onehead  | p1_hist_v2  | recall_repeat@20  |      8043 |  0.0127 |  0.0070 |  0.0185 |        1.0000 |
| p3_onehead  | p1_hist_v2  | recall_explore@20 |     37709 |  0.0061 |  0.0045 |  0.0077 |        1.0000 |
| p3_onehead  | gptopfreq   | NDCG@20           |     39385 |  0.0268 |  0.0257 |  0.0279 |        1.0000 |
| p3_onehead  | gptopfreq   | HR@10             |     39385 |  0.0563 |  0.0532 |  0.0595 |        1.0000 |
| p3_onehead  | gptopfreq   | recall_repeat@20  |      8043 | -0.0397 | -0.0474 | -0.0325 |        0.0000 |
| p3_onehead  | gptopfreq   | recall_explore@20 |     37709 |  0.0495 |  0.0474 |  0.0516 |        1.0000 |
