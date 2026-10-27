-- Self-built source #1: public holidays (ext.public_holidays) + commercial events inferred from the share of priced SKUs on a
-- DAILY/SEASONAL promotion: a day is a peak when the share exceeds the trailing 60-day mean by 1.5 sigma AND at least 0.2 % of the
-- SKUs are on promotion (the floor removes peaks of a near-zero baseline); >= 3 consecutive peak days form an event. Events are
-- named by overlap with ext.commercial_event_names (team dictionary, ingestion/commercial_event_names.csv), else EVENT_n.
WITH days AS (SELECT CAST(date_of_day AS DATE) AS d, iso_week_YYYYWW, is_weekend FROM {{ source('bronze', 'dim_calendar') }}),
ctry AS (SELECT DISTINCT country_code FROM {{ ref('slv_price_sku_interval') }}),
grid AS (SELECT c.country_code, d.* FROM ctry c CROSS JOIN days d),
promo_share AS (
  SELECT g.country_code, g.d,
         COUNT(DISTINCT CASE WHEN p.promo_kind IN ('DAILY', 'SEASONAL') THEN p.item_code END) * 1.0 / NULLIF(COUNT(DISTINCT p.item_code), 0) AS share
  FROM grid g JOIN {{ ref('slv_price_sku_interval') }} p ON p.country_code = g.country_code AND g.d BETWEEN p.eff_start AND p.eff_end
  GROUP BY 1, 2),
z AS (SELECT *, AVG(share) OVER w AS mu, STDDEV_SAMP(share) OVER w AS sigma FROM promo_share
      WINDOW w AS (PARTITION BY country_code ORDER BY d ROWS BETWEEN 60 PRECEDING AND 1 PRECEDING)),
ev AS (SELECT country_code, d, share, (mu IS NOT NULL AND share > mu + 1.5 * COALESCE(sigma, 0) AND share >= 0.002) AS is_peak FROM z),
runs AS (SELECT *, SUM(CASE WHEN is_peak THEN 0 ELSE 1 END) OVER (PARTITION BY country_code ORDER BY d) AS grp FROM ev),
events AS (SELECT country_code, grp, MIN(d) ev_start, MAX(d) ev_end, 'EVENT_' || ROW_NUMBER() OVER (PARTITION BY country_code ORDER BY MIN(d)) AS ev_label
           FROM runs WHERE is_peak GROUP BY 1, 2 HAVING COUNT(*) >= 3),
named AS (SELECT e.*, (SELECT FIRST(n.event_name ORDER BY n.event_start) FROM {{ source('ext', 'commercial_event_names') }} n
                       WHERE n.country_code = e.country_code AND n.event_start <= e.ev_end AND n.event_end >= e.ev_start) AS dict_name FROM events e),
hol AS (SELECT country_code, holiday_date, FIRST(holiday_name) AS holiday_name FROM {{ source('ext', 'public_holidays') }} GROUP BY 1, 2)
SELECT g.country_code, g.d AS calendar_date, g.iso_week_YYYYWW, g.is_weekend,
       (h.holiday_date IS NOT NULL) AS is_public_holiday, h.holiday_name,
       (SELECT MIN(hh.holiday_date) FROM hol hh WHERE hh.country_code = g.country_code AND hh.holiday_date >= g.d) - g.d AS days_to_next_holiday,
       (e.ev_start IS NOT NULL) AS in_commercial_event, e.ev_start AS event_start, e.ev_end AS event_end,
       COALESCE(e.dict_name, e.ev_label) AS event_name, ps.share AS promo_share
FROM grid g
LEFT JOIN hol h ON h.country_code = g.country_code AND h.holiday_date = g.d
LEFT JOIN named e ON e.country_code = g.country_code AND g.d BETWEEN e.ev_start AND e.ev_end
LEFT JOIN promo_share ps ON ps.country_code = g.country_code AND ps.d = g.d
