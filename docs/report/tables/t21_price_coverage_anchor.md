### Price coverage at the anchor: model × anchor rows with a price and the share of priced SKUs per model (issue #33: ≥ 90 % in the main set)

| country code | split | model anchor rows | with price pct | mean sku price coverage | all skus priced pct |
|---|---|---:|---:|---:|---:|
| SG | test | 267,747 | 98.57 | 0.929 | 78.92 |
| SG | train | 1,324,815 | 98.31 | 0.926 | 78.34 |
| SG | valid | 95,980 | 98.44 | 0.929 | 78.97 |
| TH | test | 217,971 | 99.15 | 0.936 | 80.4 |
| TH | train | 1,078,280 | 99.18 | 0.94 | 81.1 |
| TH | valid | 74,559 | 99.1 | 0.938 | 81.08 |
| VN | test | 215,865 | 99.51 | 0.933 | 78.31 |
| VN | train | 947,980 | 99.16 | 0.931 | 77.64 |
| VN | valid | 67,723 | 99.6 | 0.937 | 78.8 |

*Source:* `gold.gld_fs_model_country` (`price_local`, `sku_price_coverage`), `gold.anchor_grid`. *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
