-- QC-6: the co-purchase statistics must not see any purchase that can be a validation or test label,
-- so vars.copurchase_cutoff must not exceed valid_lo of evaluation/split.yml (gold.split_windows is written by build_anchor_grid.py).
SELECT c.cutoff_date, w.valid_lo
FROM (SELECT DISTINCT cutoff_date FROM {{ ref('gld_copurchase_lift') }}) c, gold.split_windows w
WHERE c.cutoff_date > w.valid_lo
