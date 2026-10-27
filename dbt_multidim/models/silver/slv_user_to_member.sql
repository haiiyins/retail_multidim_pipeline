-- Self-built source #2b, step 2: one member per cookie. identity_verified_ts = first moment the link became known (QC-6);
-- cookies linked to more than one member are excluded here and listed in quarantine.slv_identity_conflicts.
SELECT user_id, ANY_VALUE(member_id) AS member_id, MIN(verified_ts) AS identity_verified_ts,
       LIST(DISTINCT src ORDER BY src) AS methods
FROM {{ ref('slv_user_member_links') }}
GROUP BY user_id HAVING COUNT(DISTINCT member_id) = 1
