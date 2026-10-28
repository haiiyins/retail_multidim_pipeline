### Anchor grid: every Monday after the second purchase, then the label-horizon rule, the training stride and the per-country cap

| country code | split | anchors | members | with purchase within 90d | after train stride | used after cap | members used |
|---|---|---:|---:|---:|---:|---:|---:|
| SG | train | 57,903,721 | 722,336 | 23,228,711 | 5,807,003 | 50,000 | 47,178 |
| SG | valid | 6,846,039 | 775,662 | 2,284,324 | 2,284,324 | 15,000 | 15,000 |
| SG | test | 21,619,946 | 866,894 | 6,889,381 | 6,889,381 | 50,000 | 49,133 |
| TH | train | 65,398,642 | 870,552 | 18,968,067 | 4,742,072 | 50,000 | 46,871 |
| TH | valid | 8,339,209 | 951,372 | 2,038,634 | 2,038,634 | 15,000 | 15,000 |
| TH | test | 27,579,739 | 1,131,368 | 6,377,546 | 6,377,546 | 50,000 | 49,223 |
| VN | train | 20,295,380 | 311,873 | 4,663,802 | 1,165,941 | 50,000 | 41,161 |
| VN | valid | 3,021,577 | 345,657 | 534,407 | 534,407 | 15,000 | 13,699 |
| VN | test | 10,193,198 | 430,733 | 2,031,326 | 2,031,326 | 50,000 | 40,782 |

*Source:* `gold.anchor_grid` (`evaluation/build_anchor_grid.py`, `evaluation/split.yml`). *Generated:* 2026-10-28 15:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
