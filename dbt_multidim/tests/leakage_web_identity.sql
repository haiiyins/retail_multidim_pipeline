-- Stitched events used in Gold must have identity_verified_ts ≤ anchor_date (checked through fs_pair web features)
SELECT p.member_id, p.anchor_date, p.model_code FROM {{ ref('gld_fs_pair') }} p
JOIN {{ ref('gld_web_stitched') }} w ON w.member_id = p.member_id AND w.model_code = p.model_code
 AND w.event_date BETWEEN p.anchor_date - 30 AND p.anchor_date - 1
WHERE w.identity_verified_ts > CAST(p.anchor_date AS TIMESTAMP) AND (p.web_view_30d > 0 OR p.web_cart_30d > 0)
