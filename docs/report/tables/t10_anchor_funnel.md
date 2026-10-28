### Anchor grid: every Monday after the second purchase, then the label-horizon rule, the training stride and the per-country cap

| country code | split | anchors | members | with purchase within 90d | after train stride | used after cap | members used |
|---|---|---:|---:|---:|---:|---:|---:|
| VN | train | 19,998,412 | 307,025 | 4,597,359 | 1,149,318 | 50,000 | 41,005 |
| VN | valid | 2,974,199 | 340,187 | 525,727 | 525,727 | 15,000 | 13,679 |
| VN | test | 10,024,984 | 423,678 | 2,004,187 | 2,004,187 | 50,000 | 40,626 |

*Source:* `gold.anchor_grid` (`evaluation/build_anchor_grid.py`, `evaluation/split.yml`). *Generated:* 2026-10-28 10:07 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
