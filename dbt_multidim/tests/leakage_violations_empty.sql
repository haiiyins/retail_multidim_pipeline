-- QC-6 (WBS 3.8): the leakage ledger must be empty on every run
SELECT model_name, rule, COUNT(*) AS violations FROM {{ ref('leakage_violations') }} GROUP BY 1, 2
