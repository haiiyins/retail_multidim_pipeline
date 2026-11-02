# t29 — P2 signals by fitting protocol (Δ = 30)

Rows: anchors covered by the rolling protocol (from the first cutoff on). train = train anchors before the pseudo-test quarter; pseudo_test = last quarter of train; test = test.

| signal   | variant   | eval        |    rows |   pos_rate |      AUC |       AP |   logloss |   pinball_wtp_q50 |   cover_wtp_q50 |   pinball_wtp_q90 |   cover_wtp_q90 |
|:---------|:----------|:------------|--------:|-----------:|---------:|---------:|----------:|------------------:|----------------:|------------------:|----------------:|
| hazard   | rolling   | train       | 1527749 |     0.0605 |   0.6810 |   0.1306 |    0.2164 |          nan      |        nan      |          nan      |        nan      |
| hazard   | rolling   | pseudo_test |  232813 |     0.0577 |   0.7034 |   0.1398 |    0.2053 |          nan      |        nan      |          nan      |        nan      |
| hazard   | rolling   | test        | 1940801 |     0.0592 |   0.7075 |   0.1456 |    0.2083 |          nan      |        nan      |          nan      |        nan      |
| hazard   | naive     | train       | 1527749 |     0.0605 |   0.7252 |   0.1800 |    0.2078 |          nan      |        nan      |          nan      |        nan      |
| hazard   | naive     | pseudo_test |  232813 |     0.0577 |   0.7436 |   0.1883 |    0.1979 |          nan      |        nan      |          nan      |        nan      |
| hazard   | naive     | test        | 1940801 |     0.0592 |   0.7053 |   0.1438 |    0.2088 |          nan      |        nan      |          nan      |        nan      |
| hazard   | leaky     | train       | 1527749 |     0.0605 |   0.7095 |   0.1578 |    0.2109 |          nan      |        nan      |          nan      |        nan      |
| hazard   | leaky     | pseudo_test |  232813 |     0.0577 |   0.7172 |   0.1556 |    0.2027 |          nan      |        nan      |          nan      |        nan      |
| hazard   | leaky     | test        | 1940801 |     0.0592 |   0.7234 |   0.1649 |    0.2052 |          nan      |        nan      |          nan      |        nan      |
| wtp      | rolling   | train       |  123845 |   nan      | nan      | nan      |  nan      |            0.2638 |          0.4965 |            0.1705 |          0.8739 |
| wtp      | rolling   | pseudo_test |   18491 |   nan      | nan      | nan      |  nan      |            0.2707 |          0.5290 |            0.1758 |          0.8739 |
| wtp      | rolling   | test        |  150000 |   nan      | nan      | nan      |  nan      |            0.2596 |          0.5127 |            0.1667 |          0.8837 |
| wtp      | naive     | train       |  123845 |   nan      | nan      | nan      |  nan      |            0.2415 |          0.4989 |            0.1462 |          0.8981 |
| wtp      | naive     | pseudo_test |   18491 |   nan      | nan      | nan      |  nan      |            0.2483 |          0.5195 |            0.1506 |          0.9002 |
| wtp      | naive     | test        |  150000 |   nan      | nan      | nan      |  nan      |            0.2600 |          0.5160 |            0.1655 |          0.8932 |
| wtp      | leaky     | train       |  123845 |   nan      | nan      | nan      |  nan      |            0.2529 |          0.4865 |            0.1581 |          0.8870 |
| wtp      | leaky     | pseudo_test |   18491 |   nan      | nan      | nan      |  nan      |            0.2620 |          0.5177 |            0.1655 |          0.8829 |
| wtp      | leaky     | test        |  150000 |   nan      | nan      | nan      |  nan      |            0.2508 |          0.5063 |            0.1571 |          0.8900 |
