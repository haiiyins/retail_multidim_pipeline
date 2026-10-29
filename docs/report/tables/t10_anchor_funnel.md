### Anchor grid: every Monday after the second purchase, then the label-horizon rule, the training stride and the per-country cap

| country code | split | anchors | members | with purchase within 90d | after train stride | used after cap | members used |
|---|---|---:|---:|---:|---:|---:|---:|
| SG | train | 57,903,993 | 722,344 | 23,228,699 | 5,807,003 | 50,000 | 47,178 |
| SG | valid | 6,846,086 | 775,665 | 2,284,331 | 2,284,331 | 15,000 | 15,000 |
| SG | test | 21,620,134 | 866,903 | 6,889,365 | 6,889,365 | 50,000 | 49,133 |
| TH | train | 65,398,695 | 870,554 | 18,968,086 | 4,742,075 | 50,000 | 46,871 |
| TH | valid | 8,339,226 | 951,373 | 2,038,628 | 2,038,628 | 15,000 | 15,000 |
| TH | test | 27,579,803 | 1,131,373 | 6,377,528 | 6,377,528 | 50,000 | 49,223 |
| VN | train | 20,295,065 | 311,858 | 4,663,798 | 1,165,934 | 50,000 | 41,161 |
| VN | valid | 3,021,511 | 345,649 | 534,409 | 534,409 | 15,000 | 13,700 |
| VN | test | 10,193,193 | 430,731 | 2,031,341 | 2,031,341 | 50,000 | 40,783 |

*Source:* `gold.anchor_grid` (`evaluation/build_anchor_grid.py`, `evaluation/split.yml`). *Generated:* 2026-10-29 07:36 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
