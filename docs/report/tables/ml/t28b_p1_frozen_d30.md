# t28b — error analysis of p1_frozen, test, Δ = 30

positives 213,289 · anchors 63,574 · anchors with no positive in the list 40.7% · with every positive in the list 18.4% · with a top-10 hit 21.7%

source-reach check on positives in the list (agreement with r1…r5 flags): {'r1': 1.0, 'r2': 1.0, 'r3': 1.0, 'r4': 1.0, 'r5': 1.0}

## Cells by repeat / explore (share of positives)

| kind    |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:--------|------------:|--------:|---------------:|-------------:|----------------:|
| explore |      195038 |  0.028  |         0.2274 |       0.1111 |          0.6335 |
| repeat  |       18251 |  0.6537 |         0.3319 |       0.0125 |          0.0019 |

## Cells, all positives

| all   |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:------|------------:|--------:|---------------:|-------------:|----------------:|
| ALL   |      213289 |  0.0816 |         0.2363 |       0.1026 |          0.5795 |

## Cells by country

| country_code   | kind    |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:---------------|:--------|------------:|--------:|---------------:|-------------:|----------------:|
| SG             | explore |       68228 |  0.0202 |         0.1888 |       0.1172 |          0.6737 |
| SG             | repeat  |        6718 |  0.6164 |         0.3826 |       0      |          0.001  |
| TH             | explore |       68107 |  0.0325 |         0.2306 |       0.1042 |          0.6327 |
| TH             | repeat  |        6904 |  0.6424 |         0.3226 |       0.0326 |          0.0025 |
| VN             | explore |       58703 |  0.0319 |         0.2685 |       0.1119 |          0.5877 |
| VN             | repeat  |        4629 |  0.7246 |         0.2724 |       0.0009 |          0.0022 |

## Cells by segment

| segment   | kind    |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:----------|:--------|------------:|--------:|---------------:|-------------:|----------------:|
| loyal     | explore |      108320 |  0.0215 |         0.201  |       0.13   |          0.6474 |
| loyal     | repeat  |       13154 |  0.5953 |         0.3861 |       0.0172 |          0.0014 |
| mid       | explore |       36141 |  0.0348 |         0.2567 |       0.0918 |          0.6168 |
| mid       | repeat  |        2571 |  0.7981 |         0.1991 |       0.0008 |          0.0019 |
| new       | explore |       50577 |  0.0371 |         0.2629 |       0.0843 |          0.6156 |
| new       | repeat  |        2526 |  0.8108 |         0.1849 |       0.0004 |          0.004  |

## Cells by history (distinct models bought in the 365 days before the anchor)

| history   |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:----------|------------:|--------:|---------------:|-------------:|----------------:|
| 11–25     |       58511 |  0.078  |         0.2167 |       0.1118 |          0.5935 |
| 3–5       |       36175 |  0.0953 |         0.2595 |       0.081  |          0.5643 |
| 6–10      |       43012 |  0.0878 |         0.2479 |       0.0927 |          0.5716 |
| >25       |       29251 |  0.0663 |         0.1842 |       0.1629 |          0.5867 |
| ≤2        |       46340 |  0.0792 |         0.2652 |       0.0792 |          0.5763 |

## Cells by price tertile (within country)

| price_tertile   | kind    |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:----------------|:--------|------------:|--------:|---------------:|-------------:|----------------:|
| high            | explore |       67463 |  0.0102 |         0.0791 |       0.0672 |          0.8435 |
| high            | repeat  |        3458 |  0.5078 |         0.4699 |       0.0176 |          0.0046 |
| low             | explore |       61877 |  0.055  |         0.3811 |       0.147  |          0.4169 |
| low             | repeat  |        9045 |  0.7468 |         0.245  |       0.0074 |          0.0008 |
| mid             | explore |       65278 |  0.0204 |         0.2334 |       0.1226 |          0.6236 |
| mid             | repeat  |        5641 |  0.5893 |         0.3914 |       0.0179 |          0.0014 |

## Cells by popularity rank at the anchor (country, buyers in 28 days)

| popularity       | kind    |   positives |   top10 |   rank_11_plus |   out_capped |   out_no_source |
|:-----------------|:--------|------------:|--------:|---------------:|-------------:|----------------:|
| 1001–5000        | explore |       70020 |  0.0085 |         0.0259 |       0.0035 |          0.9621 |
| 1001–5000        | repeat  |        3536 |  0.3982 |         0.5724 |       0.0238 |          0.0057 |
| 101–300          | explore |       31594 |  0.0141 |         0.3882 |       0.5977 |          0      |
| 101–300          | repeat  |        3674 |  0.6614 |         0.3255 |       0.0131 |          0      |
| 1–100            | explore |       34635 |  0.112  |         0.8222 |       0.0658 |          0      |
| 1–100            | repeat  |        6565 |  0.8621 |         0.1316 |       0.0062 |          0      |
| 301–1000         | explore |       52133 |  0.0095 |         0.0321 |       0.0046 |          0.9538 |
| 301–1000         | repeat  |        4344 |  0.5548 |         0.4307 |       0.0122 |          0.0023 |
| >5000 / unranked | explore |        6656 |  0.0069 |         0.0185 |       0.0021 |          0.9725 |
| >5000 / unranked | repeat  |         132 |  0.1667 |         0.7803 |       0.0227 |          0.0303 |

## Rank of positives in the list but below 10

| rnk     |   share |
|:--------|--------:|
| 11–20   |  0.1377 |
| 21–50   |  0.267  |
| 51–100  |  0.2991 |
| 101–200 |  0.2962 |

## Capped positives: highest-priority source that proposed them

| capped_by   |   share |
|:------------|--------:|
| R5          |  0.9492 |
| R2          |  0.0258 |
| R3          |  0.0148 |
| R1          |  0.0101 |
| R4          |  0.0001 |

## No-source positives: outside anchor_model_grid / popularity

|   share_outside_grid |   share_popularity_301_1000 |   share_popularity_1001_5000 |   share_popularity_gt_5000 |
|---------------------:|----------------------------:|-----------------------------:|---------------------------:|
|               0.0005 |                      0.4024 |                       0.5452 |                     0.0524 |

## Top-15 sport departments by positives (codes)

|   sport_department_code |   positives |   retrieval_miss |
|------------------------:|------------:|-----------------:|
|                     896 |       30250 |           0.644  |
|                     128 |       27586 |           0.541  |
|                     127 |       20170 |           0.7425 |
|                     471 |       19676 |           0.5763 |
|                      15 |       14386 |           0.6334 |
|                      88 |       13233 |           0.6101 |
|                     409 |       12565 |           0.782  |
|                     424 |       12119 |           0.5498 |
|                     684 |        7643 |           0.7735 |
|                     902 |        6719 |           0.7852 |
|                     611 |        5391 |           0.8306 |
|                     686 |        5291 |           0.7821 |
|                     543 |        4520 |           0.7635 |
|                     442 |        4406 |           0.8044 |
|                     164 |        4378 |           0.8837 |

## R4: favourite-sport coverage of evaluated anchors

|   share |
|--------:|
|  0.0107 |

## R4: sport × department affinity table

| country_code   |   sports |   rows |   mean_lift |   share_lift_gt_1_5 | cutoff     |
|:---------------|---------:|-------:|------------:|--------------------:|:-----------|
| SG             |      179 |    376 |      2.8913 |                   1 | 2025-10-27 |
| TH             |      163 |    374 |      5.5198 |                   1 | 2025-10-27 |
| VN             |       47 |     88 |      2.9865 |                   1 | 2025-10-27 |

## R4: per sport, top department share and lift

| country_code   |   top1_share_in_sport |   top1_lift |   depts_lift_gt_1_5 |
|:---------------|----------------------:|------------:|--------------------:|
| SG             |                0.1613 |      3.8352 |              2.1006 |
| TH             |                0.1789 |      9.6297 |              2.2945 |
| VN             |                0.1445 |      3.9257 |              1.8723 |

## R4: pre-cap volume and recall, as built and relaxed

| variant                                    |   anchors_with_any |   candidates_per_anchor |   recall_positives |   precision |
|:-------------------------------------------|-------------------:|------------------------:|-------------------:|------------:|
| R4 as built                                |             0.0101 |                  0.211  |             0.0002 |      0.0031 |
| R4 without promo / season filter           |             0.0103 |                  0.6715 |             0.0008 |      0.004  |
| R4 affinity lift > 1.5, top-500, no filter |             0.0103 |                  0.6715 |             0.0008 |      0.004  |

## Slots of the 200-cap taken by R4 / R5 on evaluated anchors

|   r4_share_of_slots |   r5_share_of_slots |   slots_per_anchor |
|--------------------:|--------------------:|-------------------:|
|              0.0009 |              0.8007 |                200 |
