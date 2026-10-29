### QC-5 flagged days other than public holidays (to review)

| table name | country code | calendar date | day of week | rows | distinct lines | dup factor | mean same weekday 28d | drift | probable cause |
|---|---|---|---:|---:|---:|---:|---:|---:|---|
| sales_detail | SG | 2023-04-07 | 5 | 76,874 | 48,568 | 1.58 | 45,920.0 | 0.674 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-04-24 | 1 | 44,853 | 30,016 | 1.49 | 29,685.0 | 0.511 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-01 | 0 | 78,814 | 46,574 | 1.69 | 44,273.3 | 0.78 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-02 | 1 | 35,594 | 20,976 | 1.7 | 20,586.5 | 0.729 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-03 | 2 | 35,233 | 20,758 | 1.7 | 19,707.3 | 0.788 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-04 | 3 | 34,169 | 21,577 | 1.58 | 19,123.5 | 0.787 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-05 | 4 | 35,831 | 21,368 | 1.68 | 20,103.3 | 0.782 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-06 | 5 | 51,570 | 29,581 | 1.74 | 24,702.8 | 1.088 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-07 | 6 | 87,291 | 49,495 | 1.76 | 45,723.3 | 0.909 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-08 | 0 | 85,251 | 49,406 | 1.73 | 52,633.5 | 0.62 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-10 | 2 | 35,785 | 21,659 | 1.65 | 22,828.3 | 0.568 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-11 | 3 | 35,208 | 20,694 | 1.7 | 22,567.5 | 0.56 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-12 | 4 | 36,933 | 21,027 | 1.76 | 23,192.3 | 0.592 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-10-13 | 5 | 46,812 | 25,833 | 1.81 | 30,941.0 | 0.513 | DUPLICATED_EXPORT |
| sales_detail | SG | 2023-11-13 | 1 | 88,649 | 59,890 | 1.48 | 33,664.0 | 1.633 | DUPLICATED_EXPORT |
| sales_detail | SG | 2024-01-03 | 3 | 19,804 | 19,803 | 1 | 46,836.0 | -0.577 | UNEXPLAINED |
| sales_detail | SG | 2024-01-04 | 4 | 18,500 | 18,500 | 1 | 45,317.0 | -0.592 | UNEXPLAINED |
| sales_detail | SG | 2024-01-05 | 5 | 23,988 | 23,983 | 1 | 51,382.8 | -0.533 | UNEXPLAINED |
| sales_detail | SG | 2024-01-08 | 1 | 19,723 | 19,720 | 1 | 47,779.8 | -0.587 | HOLIDAY_IN_BASELINE |
| sales_detail | SG | 2024-01-09 | 2 | 19,839 | 19,839 | 1 | 40,873.5 | -0.515 | UNEXPLAINED |
| sales_detail | SG | 2024-01-10 | 3 | 18,882 | 18,881 | 1 | 39,959.5 | -0.527 | UNEXPLAINED |
| sales_detail | SG | 2024-01-15 | 1 | 18,071 | 18,066 | 1 | 40,525.8 | -0.554 | HOLIDAY_IN_BASELINE |
| sales_detail | SG | 2024-02-13 | 2 | 27,986 | 27,985 | 1 | 18,212.3 | 0.537 | ADJACENT_TO_HOLIDAY: Chinese New Year (observed) |
| sales_detail | SG | 2024-11-11 | 1 | 31,813 | 31,799 | 1 | 19,294.5 | 0.649 | DOUBLE_DAY_SALE |
| sales_detail | SG | 2026-01-22 | 4 | 14,949 | 14,949 | 1 | 30,073.5 | -0.503 | HOLIDAY_IN_BASELINE |
| sales_detail | TH | 2023-03-06 | 1 | 41,199 | 25,550 | 1.61 | 25,408.5 | 0.621 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-04-06 | 4 | 48,435 | 27,624 | 1.75 | 27,275.5 | 0.776 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-05-08 | 1 | 12,906 | 12,906 | 1 | 27,129.8 | -0.524 | HOLIDAY_IN_BASELINE |
| sales_detail | TH | 2023-05-11 | 4 | 13,145 | 13,145 | 1 | 27,130.0 | -0.515 | HOLIDAY_IN_BASELINE |
| sales_detail | TH | 2023-05-12 | 5 | 13,395 | 13,395 | 1 | 27,779.8 | -0.518 | HOLIDAY_IN_BASELINE |
| sales_detail | TH | 2023-10-01 | 0 | 47,770 | 28,200 | 1.69 | 24,725.0 | 0.932 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-02 | 1 | 25,975 | 15,298 | 1.7 | 12,127.3 | 1.142 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-03 | 2 | 24,593 | 14,516 | 1.69 | 12,786.5 | 0.923 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-04 | 3 | 23,445 | 13,955 | 1.68 | 12,581.5 | 0.863 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-05 | 4 | 24,623 | 14,484 | 1.7 | 12,624.0 | 0.95 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-06 | 5 | 26,485 | 15,747 | 1.68 | 13,841.5 | 0.913 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-07 | 6 | 42,957 | 26,049 | 1.65 | 23,392.5 | 0.836 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-08 | 0 | 47,513 | 28,267 | 1.68 | 29,735.5 | 0.598 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-09 | 1 | 24,032 | 14,464 | 1.66 | 15,344.3 | 0.566 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-10 | 2 | 25,761 | 15,535 | 1.66 | 15,562.5 | 0.655 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-11 | 3 | 25,501 | 15,340 | 1.66 | 15,026.0 | 0.697 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-12 | 4 | 26,481 | 15,717 | 1.68 | 15,454.0 | 0.714 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-13 | 5 | 41,236 | 24,764 | 1.67 | 17,044.5 | 1.419 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-10-23 | 1 | 35,755 | 21,293 | 1.68 | 21,156.0 | 0.69 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-12-05 | 2 | 54,415 | 30,491 | 1.78 | 22,963.3 | 1.37 | DUPLICATED_EXPORT |
| sales_detail | TH | 2023-12-11 | 1 | 39,733 | 22,162 | 1.79 | 24,414.3 | 0.627 | DUPLICATED_EXPORT |
| sales_detail | TH | 2024-01-05 | 5 | 17,146 | 17,146 | 1 | 34,672.0 | -0.505 | HOLIDAY_IN_BASELINE |
| sales_detail | TH | 2024-01-08 | 1 | 16,094 | 16,092 | 1 | 32,332.5 | -0.502 | HOLIDAY_IN_BASELINE |
| sales_detail | TH | 2025-03-28 | 5 | 8,104 | 8,098 | 1 | 17,493.8 | -0.537 | UNEXPLAINED |
| sales_detail | TH | 2025-10-10 | 5 | 31,682 | 31,654 | 1 | 17,317.3 | 0.83 | DOUBLE_DAY_SALE |
| sales_detail | TH | 2025-11-11 | 2 | 30,628 | 30,615 | 1 | 18,203.3 | 0.683 | DOUBLE_DAY_SALE |
| sales_detail | TH | 2026-07-07 | 2 | 38,964 | 38,956 | 1 | 20,138.8 | 0.935 | DOUBLE_DAY_SALE |
| sales_detail | TH | 2026-09-09 | 3 | 41,811 | 41,782 | 1 | 25,278.0 | 0.654 | DOUBLE_DAY_SALE |
| sales_detail | TH | 2026-10-10 | 6 | 53,735 | 53,719 | 1 | 32,309.8 | 0.663 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2023-02-04 | 6 | 17,338 | 8,717 | 1.99 | 10,438.3 | 0.661 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-02-05 | 0 | 19,188 | 9,676 | 1.98 | 10,848.8 | 0.769 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-02-06 | 1 | 8,764 | 4,407 | 1.99 | 5,771.5 | 0.518 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-02-07 | 2 | 10,103 | 5,065 | 1.99 | 6,653.5 | 0.518 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-02-11 | 6 | 19,165 | 9,677 | 1.98 | 11,341.8 | 0.69 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-02-12 | 0 | 19,643 | 9,905 | 1.98 | 12,068.3 | 0.628 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-06-01 | 4 | 7,699 | 7,699 | 1 | 4,645.3 | 0.657 | UNEXPLAINED |
| sales_detail | VN | 2023-06-06 | 2 | 7,331 | 7,331 | 1 | 4,751.3 | 0.543 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2023-10-01 | 0 | 15,529 | 9,586 | 1.62 | 9,606.5 | 0.617 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-03 | 2 | 6,691 | 4,026 | 1.66 | 4,425.0 | 0.512 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-04 | 3 | 7,310 | 4,393 | 1.66 | 4,337.5 | 0.685 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-05 | 4 | 7,854 | 4,205 | 1.87 | 4,336.0 | 0.811 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-06 | 5 | 9,168 | 4,869 | 1.88 | 4,560.3 | 1.01 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-07 | 6 | 15,899 | 8,383 | 1.9 | 9,308.3 | 0.708 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-08 | 0 | 18,381 | 9,327 | 1.97 | 11,154.5 | 0.648 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-10 | 2 | 10,455 | 5,235 | 2 | 5,006.3 | 1.088 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-11 | 3 | 9,677 | 4,856 | 1.99 | 4,993.0 | 0.938 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-12 | 4 | 9,588 | 4,802 | 2 | 5,140.5 | 0.865 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-10-13 | 5 | 9,402 | 4,900 | 1.92 | 5,821.5 | 0.615 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-11-11 | 6 | 25,353 | 15,061 | 1.68 | 16,100.3 | 0.575 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-11-24 | 5 | 15,389 | 11,065 | 1.39 | 9,435.8 | 0.631 | DUPLICATED_EXPORT |
| sales_detail | VN | 2023-12-12 | 2 | 10,637 | 6,587 | 1.61 | 6,858.0 | 0.551 | DUPLICATED_EXPORT |
| sales_detail | VN | 2024-01-03 | 3 | 3,586 | 3,586 | 1 | 7,261.5 | -0.506 | UNEXPLAINED |
| sales_detail | VN | 2024-01-08 | 1 | 3,639 | 3,639 | 1 | 7,831.3 | -0.535 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2024-01-09 | 2 | 3,609 | 3,609 | 1 | 7,456.0 | -0.516 | UNEXPLAINED |
| sales_detail | VN | 2024-02-16 | 5 | 5,934 | 5,934 | 1 | 3,726.5 | 0.592 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2024-03-02 | 6 | 9,348 | 9,348 | 1 | 6,079.0 | 0.538 | HOLIDAY_IN_BASELINE |
| sales_detail | VN | 2024-03-03 | 0 | 11,155 | 11,155 | 1 | 7,203.3 | 0.549 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-06-06 | 4 | 7,468 | 7,463 | 1 | 4,910.3 | 0.521 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-09-07 | 6 | 4,205 | 4,204 | 1 | 9,434.8 | -0.554 | UNEXPLAINED |
| sales_detail | VN | 2024-10-10 | 4 | 5,719 | 5,717 | 1 | 3,742.5 | 0.528 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-11-11 | 1 | 7,054 | 7,052 | 1 | 3,736.0 | 0.888 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2024-11-29 | 5 | 11,573 | 11,569 | 1 | 5,460.8 | 1.119 | BLACK_FRIDAY |
| sales_detail | VN | 2024-12-12 | 4 | 8,220 | 8,218 | 1 | 5,342.3 | 0.539 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2025-06-06 | 5 | 11,635 | 11,632 | 1 | 6,658.5 | 0.747 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2025-11-11 | 2 | 11,398 | 11,380 | 1 | 5,332.0 | 1.138 | DOUBLE_DAY_SALE |
| sales_detail | VN | 2025-11-28 | 5 | 10,501 | 10,498 | 1 | 6,621.8 | 0.586 | BLACK_FRIDAY |
| sales_detail | VN | 2026-03-03 | 2 | 8,205 | 8,193 | 1 | 4,747.0 | 0.728 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2023-10-04 | 3 | 808 | 808 | 1 | 103,477.5 | -0.992 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-05 | 4 | 404 | 404 | 1 | 101,208.5 | -0.996 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-06 | 5 | 261 | 261 | 1 | 104,522.8 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-07 | 6 | 203 | 203 | 1 | 126,696.5 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-08 | 0 | 151 | 151 | 1 | 140,886.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-09 | 1 | 122 | 122 | 1 | 108,328.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-10 | 2 | 110 | 110 | 1 | 104,685.8 | -0.999 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2023-10-11 | 3 | 60 | 60 | 1 | 76,830.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-12 | 4 | 64 | 64 | 1 | 74,373.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-13 | 5 | 59 | 59 | 1 | 75,018.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-14 | 6 | 41 | 41 | 1 | 91,859.0 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-15 | 0 | 68 | 68 | 1 | 100,108.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-16 | 1 | 35 | 35 | 1 | 84,819.8 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-17 | 2 | 27 | 27 | 1 | 77,218.5 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-18 | 3 | 37 | 37 | 1 | 51,341.8 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-19 | 4 | 22 | 22 | 1 | 50,562.3 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-20 | 5 | 25 | 25 | 1 | 49,538.5 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-21 | 6 | 25 | 25 | 1 | 60,710.0 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-22 | 0 | 19 | 19 | 1 | 66,532.8 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-23 | 1 | 14 | 14 | 1 | 56,925.0 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-24 | 2 | 28 | 28 | 1 | 50,056.5 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-25 | 3 | 21 | 21 | 1 | 25,439.5 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-26 | 4 | 17 | 17 | 1 | 24,960.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-27 | 5 | 20 | 20 | 1 | 24,398.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-28 | 6 | 37 | 37 | 1 | 30,482.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-29 | 0 | 23 | 23 | 1 | 34,010.8 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-30 | 1 | 8 | 8 | 1 | 29,177.5 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-10-31 | 2 | 12 | 12 | 1 | 24,153.3 | -1 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-01 | 3 | 5 | 5 | 1 | 231.5 | -0.978 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-02 | 4 | 14 | 14 | 1 | 126.8 | -0.89 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-03 | 5 | 14 | 14 | 1 | 91.3 | -0.847 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-04 | 6 | 8 | 8 | 1 | 76.5 | -0.895 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-05 | 0 | 20 | 20 | 1 | 65.3 | -0.693 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-06 | 1 | 11 | 11 | 1 | 44.8 | -0.754 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-07 | 2 | 8 | 8 | 1 | 44.3 | -0.819 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-08 | 3 | 2 | 2 | 1 | 30.8 | -0.935 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-09 | 4 | 7 | 7 | 1 | 29.3 | -0.761 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-10 | 5 | 3 | 3 | 1 | 29.5 | -0.898 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-18 | 6 | 9 | 9 | 1 | 21 | -0.571 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-19 | 0 | 1 | 1 | 1 | 18.8 | -0.947 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-11-21 | 2 | 6 | 6 | 1 | 15.3 | -0.607 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-23 | 4 | 2 | 2 | 1 | 12 | -0.833 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-24 | 5 | 4 | 4 | 1 | 12.8 | -0.686 | BLACK_FRIDAY |
| tracking_ecom_events | SG | 2023-11-25 | 6 | 0 | 0 |  | 17 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-11-26 | 0 | 4 | 4 | 1 | 14.3 | -0.719 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-11-27 | 1 | 3 | 3 | 1 | 10.8 | -0.721 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-11-28 | 2 | 3 | 3 | 1 | 9.8 | -0.692 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-11-30 | 4 | 0 | 0 |  | 8.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-01 | 5 | 4 | 4 | 1 | 8.8 | -0.543 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-12-02 | 6 | 2 | 2 | 1 | 7.8 | -0.742 | AFTER_GAP |
| tracking_ecom_events | SG | 2023-12-03 | 0 | 4 | 4 | 1 | 9.5 | -0.579 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-12-04 | 1 | 3 | 3 | 1 | 9.5 | -0.684 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-12-05 | 2 | 2 | 2 | 1 | 7.5 | -0.733 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-12-08 | 5 | 3 | 3 | 1 | 6.3 | -0.52 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-12-09 | 6 | 3 | 3 | 1 | 6.3 | -0.52 | AFTER_GAP |
| tracking_ecom_events | SG | 2023-12-10 | 0 | 1 | 1 | 1 | 5.5 | -0.818 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-12-11 | 1 | 2 | 2 | 1 | 7.5 | -0.733 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2023-12-12 | 2 | 1 | 1 | 1 | 6 | -0.833 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2023-12-13 | 3 | 1 | 1 | 1 | 6 | -0.833 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-12-14 | 4 | 0 | 0 |  | 4.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-16 | 6 | 0 | 0 |  | 3.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-18 | 1 | 1 | 1 | 1 | 3.8 | -0.733 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-12-19 | 2 | 1 | 1 | 1 | 3 | -0.667 | UNEXPLAINED |
| tracking_ecom_events | SG | 2023-12-22 | 5 | 0 | 0 |  | 4.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-23 | 6 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-24 | 0 | 1 | 1 | 1 | 3 | -0.667 | ADJACENT_TO_HOLIDAY: Christmas Day |
| tracking_ecom_events | SG | 2023-12-25 | 1 | 0 | 0 |  | 2.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-26 | 2 | 3 | 3 | 1 | 1.8 | 0.714 | ADJACENT_TO_HOLIDAY: Christmas Day |
| tracking_ecom_events | SG | 2023-12-27 | 3 | 0 | 0 |  | 3.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-30 | 6 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2023-12-31 | 0 | 0 | 0 |  | 2.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-01 | 1 | 0 | 0 |  | 1.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-02 | 2 | 0 | 0 |  | 1.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-03 | 3 | 1 | 1 | 1 | 2.3 | -0.556 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-01-04 | 4 | 0 | 0 |  | 2 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-07 | 0 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-08 | 1 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-09 | 2 | 2 | 2 | 1 | 1.3 | 0.6 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-01-12 | 5 | 0 | 0 |  | 3.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-21 | 0 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-24 | 3 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-25 | 4 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-01-30 | 2 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-01 | 4 | 1 | 1 | 1 | 0.5 | 1 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-02-02 | 5 | 2 | 2 | 1 | 1.3 | 0.6 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-02-03 | 6 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-04 | 0 | 2 | 2 | 1 | 0.5 | 3 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-02-06 | 2 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-07 | 3 | 2 | 2 | 1 | 1.3 | 0.6 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-02-08 | 4 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-09 | 5 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-10 | 6 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-11 | 0 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-12 | 1 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-13 | 2 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-14 | 3 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-15 | 4 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-16 | 5 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-17 | 6 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-18 | 0 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-21 | 3 | 2 | 2 | 1 | 0.8 | 1.667 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-02-23 | 5 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-25 | 0 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-26 | 1 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-02-28 | 3 | 2 | 2 | 1 | 1.3 | 0.6 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-03-04 | 1 | 1 | 1 | 1 | 0.5 | 1 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-03-06 | 3 | 0 | 0 |  | 1.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-03-11 | 1 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-03-13 | 3 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-03-18 | 1 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-03-20 | 3 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-03-28 | 4 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-04-01 | 1 | 1 | 1 | 1 | 0.5 | 1 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-04-04 | 4 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-04-08 | 1 | 4 | 4 | 1 | 0.5 | 7 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-04-11 | 4 | 1 | 1 | 1 | 0.5 | 1 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-04-12 | 5 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-04-15 | 1 | 0 | 0 |  | 1.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-04-18 | 4 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-04-22 | 1 | 0 | 0 |  | 1.5 | -1 | NO_ROWS |
| tracking_ecom_events | SG | 2024-04-29 | 1 | 519 | 519 | 1 | 1.3 | 414.2 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-04-30 | 2 | 839 | 839 | 1 | 1.3 | 670.2 | ADJACENT_TO_HOLIDAY: Labor Day |
| tracking_ecom_events | SG | 2024-05-04 | 6 | 235,858 | 235,858 | 1 | 126 | 1,870.9 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-06 | 1 | 214,373 | 214,373 | 1 | 130.8 | 1,638.6 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-07 | 2 | 201,821 | 201,821 | 1 | 210.8 | 956.632 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-05-08 | 3 | 195,275 | 195,275 | 1 | 60,817.0 | 2.211 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-09 | 4 | 189,928 | 189,928 | 1 | 53,036.5 | 2.581 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-11 | 6 | 238,970 | 238,970 | 1 | 59,090.5 | 3.044 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-12 | 0 | 259,045 | 259,045 | 1 | 64,549.8 | 3.013 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-13 | 1 | 224,337 | 224,337 | 1 | 53,723.0 | 3.176 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-14 | 2 | 220,581 | 220,581 | 1 | 50,665.5 | 3.354 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-05-15 | 3 | 217,760 | 217,760 | 1 | 109,635.5 | 0.986 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-16 | 4 | 210,093 | 210,093 | 1 | 100,518.3 | 1.09 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-17 | 5 | 196,182 | 196,182 | 1 | 99,990.3 | 0.962 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-18 | 6 | 224,290 | 224,290 | 1 | 118,832.8 | 0.887 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-19 | 0 | 255,860 | 255,860 | 1 | 129,311.0 | 0.979 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-20 | 1 | 227,786 | 227,786 | 1 | 109,807.3 | 1.074 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-05-21 | 2 | 199,138 | 199,138 | 1 | 105,810.5 | 0.882 | ADJACENT_TO_HOLIDAY: Vesak Day |
| tracking_ecom_events | SG | 2024-05-22 | 3 | 254,002 | 254,002 | 1 | 164,075.5 | 0.548 | AFTER_GAP |
| tracking_ecom_events | SG | 2024-08-28 | 3 | 471 | 471 | 1 | 202,033.0 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-08-29 | 4 | 453 | 453 | 1 | 197,296.8 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-08-30 | 5 | 477 | 477 | 1 | 201,883.0 | -0.998 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2024-08-31 | 6 | 779 | 779 | 1 | 235,477.8 | -0.997 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-09-04 | 3 | 230,156 | 230,156 | 1 | 152,198.5 | 0.512 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-09-05 | 4 | 245,551 | 245,551 | 1 | 149,813.0 | 0.639 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-09-09 | 1 | 375,464 | 375,464 | 1 | 233,641.0 | 0.607 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2024-11-11 | 1 | 557,569 | 557,569 | 1 | 285,227.8 | 0.955 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2024-12-28 | 6 | 563 | 563 | 1 | 249,718.5 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-12-29 | 0 | 612 | 612 | 1 | 291,167.5 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2024-12-30 | 1 | 634 | 634 | 1 | 266,310.3 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-01-11 | 6 | 323,105 | 323,105 | 1 | 171,861.5 | 0.88 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-01-12 | 0 | 333,478 | 333,478 | 1 | 194,604.5 | 0.714 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-01-13 | 1 | 279,278 | 279,278 | 1 | 173,456.5 | 0.61 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-01-19 | 0 | 318,675 | 318,675 | 1 | 207,413.8 | 0.536 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-07 | 5 | 361,938 | 361,938 | 1 | 237,936.3 | 0.521 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-08 | 6 | 612,233 | 612,233 | 1 | 287,267.5 | 1.131 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-09 | 0 | 769,645 | 769,645 | 1 | 315,938.0 | 1.436 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-10 | 1 | 573,558 | 573,558 | 1 | 261,720.3 | 1.191 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-11 | 2 | 552,476 | 552,476 | 1 | 237,421.3 | 1.327 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-12 | 3 | 614,656 | 614,656 | 1 | 231,507.8 | 1.655 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2025-02-13 | 4 | 581,017 | 581,017 | 1 | 255,599.0 | 1.273 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2025-02-14 | 5 | 569,585 | 569,585 | 1 | 259,905.5 | 1.192 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-15 | 6 | 811,756 | 811,756 | 1 | 359,549.5 | 1.258 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-16 | 0 | 985,246 | 985,246 | 1 | 424,979.8 | 1.318 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-17 | 1 | 678,247 | 678,247 | 1 | 335,290.3 | 1.023 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-18 | 2 | 651,902 | 651,902 | 1 | 315,489.0 | 1.066 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-19 | 3 | 608,528 | 608,528 | 1 | 328,107.8 | 0.855 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2025-02-20 | 4 | 624,150 | 624,150 | 1 | 346,058.5 | 0.804 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2025-02-21 | 5 | 617,838 | 617,838 | 1 | 347,391.5 | 0.779 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-22 | 6 | 838,641 | 838,641 | 1 | 494,821.8 | 0.695 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-02-23 | 0 | 901,680 | 901,680 | 1 | 591,622.5 | 0.524 | UNEXPLAINED |
| tracking_ecom_events | SG | 2025-03-03 | 1 | 922,202 | 922,202 | 1 | 548,851.5 | 0.68 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2025-11-11 | 2 | 1,519,998 | 1,519,998 | 1 | 740,523.5 | 1.053 | DOUBLE_DAY_SALE |
| tracking_ecom_events | SG | 2025-11-12 | 3 | 1,073,222 | 1,073,222 | 1 | 709,575.8 | 0.512 | UNEXPLAINED |
| tracking_ecom_events | SG | 2026-02-22 | 0 | 1,363,105 | 1,363,105 | 1 | 858,938.0 | 0.587 | UNEXPLAINED |
| tracking_ecom_events | SG | 2026-02-23 | 1 | 1,244,755 | 1,244,755 | 1 | 608,011.5 | 1.047 | UNEXPLAINED |
| tracking_ecom_events | SG | 2026-02-24 | 2 | 1,493,192 | 1,493,192 | 1 | 558,096.3 | 1.676 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | SG | 2026-02-25 | 3 | 1,471,306 | 1,471,306 | 1 | 561,321.3 | 1.621 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-06-06 | 2 | 106,818 | 106,818 | 1 | 64,776.5 | 0.649 | ADJACENT_TO_HOLIDAY: HM Queen Suthida's Birthday (in lieu); Visakha Bucha (in lieu) |
| tracking_ecom_events | TH | 2023-10-04 | 3 | 852 | 852 | 1 | 68,942.5 | -0.988 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-05 | 4 | 394 | 394 | 1 | 68,972.8 | -0.994 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-06 | 5 | 290 | 290 | 1 | 65,761.8 | -0.996 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-07 | 6 | 227 | 227 | 1 | 65,997.5 | -0.997 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-08 | 0 | 187 | 187 | 1 | 70,490.5 | -0.997 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-09 | 1 | 108 | 108 | 1 | 77,374.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-10 | 2 | 134 | 134 | 1 | 70,269.8 | -0.998 | DOUBLE_DAY_SALE |
| tracking_ecom_events | TH | 2023-10-11 | 3 | 133 | 133 | 1 | 52,047.0 | -0.997 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-12 | 4 | 93 | 93 | 1 | 52,613.3 | -0.998 | ADJACENT_TO_HOLIDAY: HM King Bhumibol Adulyadej Memorial Day |
| tracking_ecom_events | TH | 2023-10-14 | 6 | 65 | 65 | 1 | 48,171.0 | -0.999 | ADJACENT_TO_HOLIDAY: HM King Bhumibol Adulyadej Memorial Day |
| tracking_ecom_events | TH | 2023-10-15 | 0 | 57 | 57 | 1 | 52,291.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-16 | 1 | 53 | 53 | 1 | 58,158.8 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-17 | 2 | 49 | 49 | 1 | 52,522.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-18 | 3 | 46 | 46 | 1 | 36,222.8 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-19 | 4 | 53 | 53 | 1 | 36,126.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-20 | 5 | 31 | 31 | 1 | 33,389.5 | -0.999 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-10-21 | 6 | 44 | 44 | 1 | 32,717.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-22 | 0 | 30 | 30 | 1 | 35,107.5 | -0.999 | ADJACENT_TO_HOLIDAY: HM King Chulalongkorn Memorial Day |
| tracking_ecom_events | TH | 2023-10-24 | 2 | 43 | 43 | 1 | 34,013.5 | -0.999 | ADJACENT_TO_HOLIDAY: HM King Chulalongkorn Memorial Day |
| tracking_ecom_events | TH | 2023-10-25 | 3 | 33 | 33 | 1 | 18,290.8 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-26 | 4 | 42 | 42 | 1 | 18,028.8 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-27 | 5 | 34 | 34 | 1 | 17,020.8 | -0.998 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-10-28 | 6 | 27 | 27 | 1 | 16,214.0 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-29 | 0 | 26 | 26 | 1 | 17,766.0 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-10-30 | 1 | 26 | 26 | 1 | 18,881.8 | -0.999 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-10-31 | 2 | 26 | 26 | 1 | 15,339.0 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-01 | 3 | 34 | 34 | 1 | 266 | -0.872 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-02 | 4 | 33 | 33 | 1 | 145.5 | -0.773 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-03 | 5 | 24 | 24 | 1 | 112 | -0.786 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-11-04 | 6 | 29 | 29 | 1 | 90.8 | -0.68 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-05 | 0 | 20 | 20 | 1 | 75 | -0.733 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-06 | 1 | 28 | 28 | 1 | 58.5 | -0.521 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-11-07 | 2 | 17 | 17 | 1 | 63 | -0.73 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-08 | 3 | 19 | 19 | 1 | 61.5 | -0.691 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-09 | 4 | 20 | 20 | 1 | 55.3 | -0.638 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-10 | 5 | 18 | 18 | 1 | 45.5 | -0.604 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-11-11 | 6 | 17 | 17 | 1 | 41.3 | -0.588 | DOUBLE_DAY_SALE |
| tracking_ecom_events | TH | 2023-11-13 | 1 | 13 | 13 | 1 | 38.5 | -0.662 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-11-14 | 2 | 9 | 9 | 1 | 33.8 | -0.733 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-15 | 3 | 10 | 10 | 1 | 33 | -0.697 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-16 | 4 | 12 | 12 | 1 | 37 | -0.676 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-17 | 5 | 11 | 11 | 1 | 26.8 | -0.589 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-18 | 6 | 9 | 9 | 1 | 29.3 | -0.692 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-19 | 0 | 9 | 9 | 1 | 25 | -0.64 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-20 | 1 | 10 | 10 | 1 | 28.5 | -0.649 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-11-21 | 2 | 11 | 11 | 1 | 23.8 | -0.537 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-23 | 4 | 6 | 6 | 1 | 26.8 | -0.776 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-25 | 6 | 4 | 4 | 1 | 20.5 | -0.805 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-11-29 | 3 | 3 | 3 | 1 | 19 | -0.842 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-12-01 | 5 | 7 | 7 | 1 | 16.8 | -0.582 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-12-02 | 6 | 5 | 5 | 1 | 14.8 | -0.661 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-12-04 | 1 | 8 | 8 | 1 | 16.5 | -0.515 | ADJACENT_TO_HOLIDAY: HM King Bhumibol Adulyadej the Great's Birthday; National Day; National Father's Day |
| tracking_ecom_events | TH | 2023-12-06 | 3 | 5 | 5 | 1 | 11.3 | -0.556 | ADJACENT_TO_HOLIDAY: HM King Bhumibol Adulyadej the Great's Birthday; National Day; National Father's Day |
| tracking_ecom_events | TH | 2023-12-20 | 3 | 11 | 11 | 1 | 6.3 | 0.76 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-12-23 | 6 | 10 | 10 | 1 | 5.3 | 0.905 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-12-26 | 2 | 4 | 4 | 1 | 8.8 | -0.543 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2023-12-27 | 3 | 2 | 2 | 1 | 5.8 | -0.652 | UNEXPLAINED |
| tracking_ecom_events | TH | 2023-12-30 | 6 | 12 | 12 | 1 | 6.8 | 0.778 | ADJACENT_TO_HOLIDAY: Bridge Public Holiday |
| tracking_ecom_events | TH | 2024-01-06 | 6 | 4 | 4 | 1 | 8.5 | -0.529 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-01-08 | 1 | 1 | 1 | 1 | 7.5 | -0.867 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-15 | 1 | 2 | 2 | 1 | 5.3 | -0.619 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-19 | 5 | 1 | 1 | 1 | 5.5 | -0.818 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-20 | 6 | 2 | 2 | 1 | 6.8 | -0.704 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-23 | 2 | 0 | 0 |  | 3.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-01-24 | 3 | 2 | 2 | 1 | 4.3 | -0.529 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-01-25 | 4 | 1 | 1 | 1 | 4.8 | -0.789 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-01-27 | 6 | 1 | 1 | 1 | 4.8 | -0.789 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-28 | 0 | 1 | 1 | 1 | 4.3 | -0.765 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-29 | 1 | 1 | 1 | 1 | 2.8 | -0.636 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-01-31 | 3 | 1 | 1 | 1 | 4.3 | -0.765 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-02-01 | 4 | 0 | 0 |  | 3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-02-02 | 5 | 0 | 0 |  | 3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-02-07 | 3 | 0 | 0 |  | 3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-02-11 | 0 | 0 | 0 |  | 3.5 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-02-16 | 5 | 4 | 4 | 1 | 1 | 3 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-02-18 | 0 | 0 | 0 |  | 1.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-02-23 | 5 | 0 | 0 |  | 1.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-02-29 | 4 | 2 | 2 | 1 | 1.3 | 0.6 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-03-01 | 5 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-03 | 0 | 3 | 3 | 1 | 1 | 2 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-03-04 | 1 | 0 | 0 |  | 2 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-05 | 2 | 4 | 4 | 1 | 1.3 | 2.2 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-03-06 | 3 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-08 | 5 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-13 | 3 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-14 | 4 | 0 | 0 |  | 1.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-17 | 0 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-18 | 1 | 2 | 2 | 1 | 1 | 1 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-03-20 | 3 | 2 | 2 | 1 | 0.5 | 3 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-03-23 | 6 | 0 | 0 |  | 1.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-24 | 0 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-25 | 1 | 3 | 3 | 1 | 1 | 2 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-03-27 | 3 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-28 | 4 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-29 | 5 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-03-31 | 0 | 2 | 2 | 1 | 1 | 1 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-04-01 | 1 | 0 | 0 |  | 1.5 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-02 | 2 | 0 | 0 |  | 2 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-05 | 5 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-06 | 6 | 0 | 0 |  | 0.8 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-11 | 4 | 1 | 1 | 1 | 0.5 | 1 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-04-13 | 6 | 0 | 0 |  | 0.5 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-16 | 2 | 0 | 0 |  | 1 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-19 | 5 | 3 | 3 | 1 | 0.5 | 5 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-04-22 | 1 | 0 | 0 |  | 1.3 | -1 | NO_ROWS |
| tracking_ecom_events | TH | 2024-04-28 | 0 | 310 | 310 | 1 | 1.3 | 247 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-04-29 | 1 | 392 | 392 | 1 | 0.5 | 783 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-04-30 | 2 | 696 | 696 | 1 | 0.5 | 1,391.0 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-01 | 3 | 137,028 | 137,028 | 1 | 0.8 | 182,703.0 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-02 | 4 | 153,645 | 153,645 | 1 | 1 | 153,644.0 | ADJACENT_TO_HOLIDAY: National Labor Day |
| tracking_ecom_events | TH | 2024-05-03 | 5 | 154,209 | 154,209 | 1 | 1.3 | 123,366.2 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-05 | 0 | 172,372 | 172,372 | 1 | 78.3 | 2,201.8 | ADJACENT_TO_HOLIDAY: Coronation Day |
| tracking_ecom_events | TH | 2024-05-06 | 1 | 178,586 | 178,586 | 1 | 98.5 | 1,812.1 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-07 | 2 | 164,020 | 164,020 | 1 | 174.5 | 938.943 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-08 | 3 | 144,386 | 144,386 | 1 | 34,257.8 | 3.215 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-09 | 4 | 143,926 | 143,926 | 1 | 38,412.0 | 2.747 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-05-10 | 5 | 151,031 | 151,031 | 1 | 38,553.5 | 2.917 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-05-11 | 6 | 156,586 | 156,586 | 1 | 40,196.3 | 2.896 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-12 | 0 | 162,821 | 162,821 | 1 | 43,171.0 | 2.772 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-05-13 | 1 | 167,004 | 167,004 | 1 | 44,744.8 | 2.732 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-14 | 2 | 152,038 | 152,038 | 1 | 41,179.3 | 2.692 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-15 | 3 | 145,043 | 145,043 | 1 | 70,354.3 | 1.062 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2024-05-16 | 4 | 136,374 | 136,374 | 1 | 74,393.3 | 0.833 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-05-17 | 5 | 132,968 | 132,968 | 1 | 76,311.0 | 0.742 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-05-18 | 6 | 136,918 | 136,918 | 1 | 79,342.8 | 0.726 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-19 | 0 | 154,527 | 154,527 | 1 | 83,876.0 | 0.842 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-05-20 | 1 | 142,435 | 142,435 | 1 | 86,495.5 | 0.647 | AFTER_GAP |
| tracking_ecom_events | TH | 2024-05-21 | 2 | 140,405 | 140,405 | 1 | 79,188.8 | 0.773 | ADJACENT_TO_HOLIDAY: Visakha Bucha |
| tracking_ecom_events | TH | 2024-12-28 | 6 | 277 | 277 | 1 | 172,359.8 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | TH | 2024-12-29 | 0 | 295 | 295 | 1 | 189,599.0 | -0.998 | ADJACENT_TO_HOLIDAY: Bridge Public Holiday |
| tracking_ecom_events | TH | 2025-01-04 | 6 | 186,981 | 186,981 | 1 | 122,892.3 | 0.522 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-08 | 6 | 292,327 | 292,327 | 1 | 163,743.5 | 0.785 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2025-02-09 | 0 | 339,052 | 339,052 | 1 | 185,470.8 | 0.828 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-10 | 1 | 317,636 | 317,636 | 1 | 190,633.0 | 0.666 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-11 | 2 | 315,287 | 315,287 | 1 | 185,581.5 | 0.699 | ADJACENT_TO_HOLIDAY: Makha Bucha |
| tracking_ecom_events | TH | 2025-02-13 | 4 | 351,955 | 351,955 | 1 | 183,341.5 | 0.92 | ADJACENT_TO_HOLIDAY: Makha Bucha |
| tracking_ecom_events | TH | 2025-02-14 | 5 | 317,517 | 317,517 | 1 | 179,467.0 | 0.769 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-15 | 6 | 353,461 | 353,461 | 1 | 196,023.8 | 0.803 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-16 | 0 | 414,810 | 414,810 | 1 | 221,020.5 | 0.877 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-17 | 1 | 378,699 | 378,699 | 1 | 217,373.0 | 0.742 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-18 | 2 | 403,972 | 403,972 | 1 | 213,918.3 | 0.888 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-19 | 3 | 354,688 | 354,688 | 1 | 227,764.0 | 0.557 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2025-02-20 | 4 | 400,727 | 400,727 | 1 | 222,931.0 | 0.798 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-21 | 5 | 567,332 | 567,332 | 1 | 213,676.5 | 1.655 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-22 | 6 | 582,616 | 582,616 | 1 | 241,551.5 | 1.412 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-23 | 0 | 569,026 | 569,026 | 1 | 278,500.0 | 1.043 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-24 | 1 | 501,661 | 501,661 | 1 | 264,969.0 | 0.893 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-25 | 2 | 512,360 | 512,360 | 1 | 270,806.3 | 0.892 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-26 | 3 | 472,885 | 472,885 | 1 | 272,664.3 | 0.734 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2025-02-27 | 4 | 501,924 | 501,924 | 1 | 283,101.8 | 0.773 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-02-28 | 5 | 483,762 | 483,762 | 1 | 317,676.3 | 0.523 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-07-07 | 1 | 555,384 | 555,384 | 1 | 368,647.8 | 0.507 | DOUBLE_DAY_SALE |
| tracking_ecom_events | TH | 2025-11-07 | 5 | 574,720 | 574,720 | 1 | 353,494.3 | 0.626 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-11-08 | 6 | 609,378 | 609,378 | 1 | 380,220.8 | 0.603 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-11-09 | 0 | 653,187 | 653,187 | 1 | 416,235.0 | 0.569 | UNEXPLAINED |
| tracking_ecom_events | TH | 2025-11-10 | 1 | 661,970 | 661,970 | 1 | 403,832.8 | 0.639 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | TH | 2025-11-11 | 2 | 654,995 | 654,995 | 1 | 371,238.3 | 0.764 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2024-06-06 | 4 | 151,358 | 151,358 | 1 | 98,287.5 | 0.54 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2024-06-21 | 5 | 171,437 | 171,437 | 1 | 98,968.3 | 0.732 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-06-22 | 6 | 147,521 | 147,521 | 1 | 92,859.5 | 0.589 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-08-08 | 4 | 170,167 | 170,167 | 1 | 112,728.3 | 0.51 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2024-10-10 | 4 | 149,467 | 149,467 | 1 | 88,838.0 | 0.682 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2024-10-29 | 2 | 165,405 | 165,405 | 1 | 106,456.3 | 0.554 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-11-11 | 1 | 195,292 | 195,292 | 1 | 115,135.5 | 0.696 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2024-11-29 | 5 | 231,776 | 231,776 | 1 | 121,276.8 | 0.911 | BLACK_FRIDAY |
| tracking_ecom_events | VN | 2024-11-30 | 6 | 208,134 | 208,134 | 1 | 117,161.0 | 0.776 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-12-01 | 0 | 202,575 | 202,575 | 1 | 120,164.5 | 0.686 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-12-28 | 6 | 157 | 157 | 1 | 152,624.3 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-12-29 | 0 | 224 | 224 | 1 | 150,480.8 | -0.999 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-12-30 | 1 | 266 | 266 | 1 | 162,330.5 | -0.998 | UNEXPLAINED |
| tracking_ecom_events | VN | 2024-12-31 | 2 | 59,058 | 59,058 | 1 | 131,268.5 | -0.55 | ADJACENT_TO_HOLIDAY: New Year's Day |
| tracking_ecom_events | VN | 2025-02-04 | 2 | 155,201 | 155,201 | 1 | 88,563.3 | 0.752 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-05 | 3 | 165,960 | 165,960 | 1 | 84,123.5 | 0.973 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-06 | 4 | 173,535 | 173,535 | 1 | 82,991.5 | 1.091 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-07 | 5 | 160,975 | 160,975 | 1 | 82,300.8 | 0.956 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-08 | 6 | 168,479 | 168,479 | 1 | 77,269.5 | 1.18 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-09 | 0 | 183,258 | 183,258 | 1 | 92,146.3 | 0.989 | UNEXPLAINED |
| tracking_ecom_events | VN | 2025-02-10 | 1 | 203,868 | 203,868 | 1 | 102,186.0 | 0.995 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-11 | 2 | 180,840 | 180,840 | 1 | 99,953.5 | 0.809 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-12 | 3 | 208,873 | 208,873 | 1 | 98,242.0 | 1.126 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-13 | 4 | 202,681 | 202,681 | 1 | 99,325.5 | 1.041 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-14 | 5 | 185,799 | 185,799 | 1 | 96,994.8 | 0.916 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-15 | 6 | 188,819 | 188,819 | 1 | 95,585.5 | 0.975 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-16 | 0 | 199,865 | 199,865 | 1 | 112,819.0 | 0.772 | UNEXPLAINED |
| tracking_ecom_events | VN | 2025-02-17 | 1 | 228,626 | 228,626 | 1 | 124,035.0 | 0.843 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-18 | 2 | 227,782 | 227,782 | 1 | 117,681.0 | 0.936 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-19 | 3 | 210,265 | 210,265 | 1 | 124,792.3 | 0.685 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-20 | 4 | 197,443 | 197,443 | 1 | 124,234.0 | 0.589 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-21 | 5 | 207,684 | 207,684 | 1 | 116,564.3 | 0.782 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-22 | 6 | 198,209 | 198,209 | 1 | 118,344.5 | 0.675 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-02-23 | 0 | 237,019 | 237,019 | 1 | 136,862.8 | 0.732 | UNEXPLAINED |
| tracking_ecom_events | VN | 2025-02-28 | 5 | 242,665 | 242,665 | 1 | 147,809.8 | 0.642 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-03-01 | 6 | 229,956 | 229,956 | 1 | 149,156.8 | 0.542 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-03-03 | 1 | 302,070 | 302,070 | 1 | 191,967.3 | 0.574 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2025-04-04 | 5 | 257,010 | 257,010 | 1 | 156,365.5 | 0.644 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2025-04-20 | 0 | 285,932 | 285,932 | 1 | 184,307.3 | 0.551 | UNEXPLAINED |
| tracking_ecom_events | VN | 2025-04-21 | 1 | 301,418 | 301,418 | 1 | 195,143.5 | 0.545 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2025-05-05 | 1 | 382,524 | 382,524 | 1 | 239,802.0 | 0.595 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2025-06-03 | 2 | 396,459 | 396,459 | 1 | 261,116.8 | 0.518 | UNEXPLAINED |
| tracking_ecom_events | VN | 2025-06-06 | 5 | 464,150 | 464,150 | 1 | 259,279.5 | 0.79 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2025-10-10 | 5 | 286,529 | 286,529 | 1 | 190,534.8 | 0.504 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2025-11-10 | 1 | 337,511 | 337,511 | 1 | 205,928.8 | 0.639 | UNEXPLAINED |
| tracking_ecom_events | VN | 2025-11-11 | 2 | 445,150 | 445,150 | 1 | 204,815.3 | 1.173 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2025-11-28 | 5 | 384,428 | 384,428 | 1 | 240,669.0 | 0.597 | BLACK_FRIDAY |
| tracking_ecom_events | VN | 2026-02-14 | 6 | 63,347 | 63,347 | 1 | 169,723.5 | -0.627 | UNEXPLAINED |
| tracking_ecom_events | VN | 2026-02-15 | 0 | 54,215 | 54,215 | 1 | 181,132.0 | -0.701 | ADJACENT_TO_HOLIDAY: Lunar New Year's Eve |
| tracking_ecom_events | VN | 2026-02-24 | 2 | 203,787 | 203,787 | 1 | 133,394.0 | 0.528 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-02-25 | 3 | 213,778 | 213,778 | 1 | 131,794.3 | 0.622 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-02-26 | 4 | 204,229 | 204,229 | 1 | 122,281.8 | 0.67 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-02-27 | 5 | 195,706 | 195,706 | 1 | 116,457.3 | 0.68 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-02-28 | 6 | 206,782 | 206,782 | 1 | 121,678.8 | 0.699 | UNEXPLAINED |
| tracking_ecom_events | VN | 2026-03-01 | 0 | 197,998 | 197,998 | 1 | 131,922.0 | 0.501 | UNEXPLAINED |
| tracking_ecom_events | VN | 2026-03-02 | 1 | 243,577 | 243,577 | 1 | 154,593.5 | 0.576 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-03-03 | 2 | 289,829 | 289,829 | 1 | 138,394.8 | 1.094 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2026-03-04 | 3 | 237,205 | 237,205 | 1 | 139,397.8 | 0.702 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-03-05 | 4 | 204,180 | 204,180 | 1 | 130,345.8 | 0.566 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-03-08 | 0 | 212,177 | 212,177 | 1 | 137,786.8 | 0.54 | UNEXPLAINED |
| tracking_ecom_events | VN | 2026-03-12 | 4 | 229,240 | 229,240 | 1 | 142,715.3 | 0.606 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-03-13 | 5 | 214,202 | 214,202 | 1 | 139,105.0 | 0.54 | HOLIDAY_IN_BASELINE |
| tracking_ecom_events | VN | 2026-03-15 | 0 | 229,888 | 229,888 | 1 | 153,061.8 | 0.502 | UNEXPLAINED |
| tracking_ecom_events | VN | 2026-04-04 | 6 | 341,940 | 341,940 | 1 | 204,075.0 | 0.676 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2026-06-06 | 6 | 404,037 | 404,037 | 1 | 251,786.8 | 0.605 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2026-09-09 | 3 | 377,895 | 377,895 | 1 | 237,729.0 | 0.59 | DOUBLE_DAY_SALE |
| tracking_ecom_events | VN | 2026-10-10 | 6 | 324,334 | 324,334 | 1 | 208,627.0 | 0.555 | DOUBLE_DAY_SALE |

*Source:* `audit.volume_drift`. *Generated:* 2026-10-29 10:40 UTC by `tools/report_tables.py`, `COUNTRY_FILTER=ALL`.
