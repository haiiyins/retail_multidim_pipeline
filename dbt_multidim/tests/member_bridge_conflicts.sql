-- QC: transactions mapping to > 1 member (warning)
{{ config(severity='warn') }}
SELECT transaction_id, COUNT(DISTINCT member_id) n FROM {{ source('bronze', 'f_member_purchase') }} WHERE member_id IS NOT NULL GROUP BY 1 HAVING n > 1
