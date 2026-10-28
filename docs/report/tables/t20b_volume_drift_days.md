### QC-5 flagged days other than public holidays (to review)

| table name | country code | calendar date | day of week | rows | mean same weekday 28d | drift | probable cause |
|---|---|---|---:|---:|---:|---:|---|
| sales_detail | VN | 2023-02-04 | 6 | 17,338 | 10,438.3 | 0.661 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2023-02-05 | 0 | 19,188 | 10,848.8 | 0.769 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2023-02-06 | 1 | 8,764 | 5,771.5 | 0.518 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2023-02-07 | 2 | 10,103 | 6,653.5 | 0.518 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2023-02-11 | 6 | 19,165 | 11,341.8 | 0.69 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2023-02-12 | 0 | 19,643 | 12,068.3 | 0.628 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2023-06-01 | 4 | 7,699 | 4,645.3 | 0.657 | UNEXPLAINED |
| sales_detail | VN | 2023-06-06 | 2 | 7,331 | 4,751.3 | 0.543 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2023-10-01 | 0 | 15,529 | 9,606.5 | 0.617 | UNEXPLAINED |
| sales_detail | VN | 2023-10-03 | 2 | 6,691 | 4,425.0 | 0.512 | UNEXPLAINED |
| sales_detail | VN | 2023-10-04 | 3 | 7,310 | 4,337.5 | 0.685 | UNEXPLAINED |
| sales_detail | VN | 2023-10-05 | 4 | 7,854 | 4,336.0 | 0.811 | UNEXPLAINED |
| sales_detail | VN | 2023-10-06 | 5 | 9,168 | 4,560.3 | 1.01 | UNEXPLAINED |
| sales_detail | VN | 2023-10-07 | 6 | 15,899 | 9,308.3 | 0.708 | UNEXPLAINED |
| sales_detail | VN | 2023-10-08 | 0 | 18,381 | 11,154.5 | 0.648 | UNEXPLAINED |
| sales_detail | VN | 2023-10-10 | 2 | 10,455 | 5,006.3 | 1.088 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2023-10-11 | 3 | 9,677 | 4,993.0 | 0.938 | UNEXPLAINED |
| sales_detail | VN | 2023-10-12 | 4 | 9,588 | 5,140.5 | 0.865 | UNEXPLAINED |
| sales_detail | VN | 2023-10-13 | 5 | 9,402 | 5,821.5 | 0.615 | UNEXPLAINED |
| sales_detail | VN | 2023-11-11 | 6 | 25,353 | 16,100.3 | 0.575 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2023-11-24 | 5 | 15,389 | 9,435.8 | 0.631 | BLACK_FRIDAY |
| sales_detail | VN | 2023-12-12 | 2 | 10,637 | 6,858.0 | 0.551 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-01-03 | 3 | 3,586 | 7,261.5 | -0.506 | UNEXPLAINED |
| sales_detail | VN | 2024-01-08 | 1 | 3,639 | 7,831.3 | -0.535 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2024-01-09 | 2 | 3,609 | 7,456.0 | -0.516 | UNEXPLAINED |
| sales_detail | VN | 2024-02-16 | 5 | 5,934 | 3,726.5 | 0.592 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2024-03-02 | 6 | 9,348 | 6,079.0 | 0.538 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2024-03-03 | 0 | 11,155 | 7,203.3 | 0.549 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-06-06 | 4 | 7,468 | 4,910.3 | 0.521 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-09-07 | 6 | 4,205 | 9,434.8 | -0.554 | UNEXPLAINED |
| sales_detail | VN | 2024-10-10 | 4 | 5,719 | 3,742.5 | 0.528 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-11-11 | 1 | 7,054 | 3,736.0 | 0.888 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-11-29 | 5 | 11,573 | 5,460.8 | 1.119 | BLACK_FRIDAY |
| sales_detail | VN | 2024-12-12 | 4 | 8,220 | 5,342.3 | 0.539 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2025-06-06 | 5 | 11,635 | 6,658.5 | 0.747 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2025-11-11 | 2 | 11,398 | 5,332.0 | 1.138 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2025-11-28 | 5 | 10,501 | 6,621.8 | 0.586 | BLACK_FRIDAY |
| sales_detail | VN | 2026-03-03 | 2 | 8,205 | 4,747.0 | 0.728 | DOUBLE_DAY_SALE |

*Source:* `audit.volume_drift`. *Generated:* 2026-10-28 11:13 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=VN`.
