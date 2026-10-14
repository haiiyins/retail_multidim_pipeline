-- From d_member: only static attributes dated ≤ t plus account-exclusion flags.
-- Do NOT use preferred_store_gln, first/last_purchase_date, last_interaction_*, is_contactable_* (current snapshots → future leakage)
SELECT member_id, member_country_code AS country_code, locale_code,
       CAST(account_creation_datetime_utc AS TIMESTAMP) AS account_created_at,
       CAST(creation_store_gln AS VARCHAR) AS creation_store_gln,
       (COALESCE(is_teammate, false) OR COALESCE(is_business, false) OR COALESCE(is_legal_entity, false)
        OR COALESCE(is_sport_club, false) OR COALESCE(is_school, false)) AS is_excluded_account
FROM {{ source('bronze', 'd_member') }}
