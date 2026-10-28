-- QC-6 at the pair level: a pair may carry web attention only if at least one attributed event for that member × model lies in the
-- 30-day window with identity_verified_ts <= anchor_date (i.e. the attribution was known at the anchor).
SELECT p.member_id, p.anchor_date, p.model_code, p.web_view_30d, p.web_list_30d, p.web_cart_30d
FROM {{ ref('gld_fs_pair') }} p
WHERE (p.web_view_30d > 0 OR p.web_list_30d > 0 OR p.web_cart_30d > 0)
  AND NOT EXISTS (
    SELECT 1 FROM {{ ref('gld_web_stitched') }} w
    WHERE w.member_id = p.member_id AND w.model_code = p.model_code
      AND w.event_date BETWEEN p.anchor_date - 30 AND p.anchor_date - 1
      AND w.identity_verified_ts <= CAST(p.anchor_date AS TIMESTAMP))
