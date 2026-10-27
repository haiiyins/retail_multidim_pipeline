{# price_type → promotion kind. The 2026-10-27 export has four values (STANDARD, DAY_TO_DAY_PROMOTION, END_OF_LINE, DROP);
   SEASON_SALES was expected from the first samples but never occurs, the branch is kept dormant (issue #6). #}
{% macro promo_kind(price_type) -%}
  CASE {{ price_type }}
    WHEN 'DAY_TO_DAY_PROMOTION' THEN 'DAILY'
    WHEN 'SEASON_SALES'         THEN 'SEASONAL'
    WHEN 'END_OF_LINE'          THEN 'CLEARANCE'
    WHEN 'DROP'                 THEN 'DROP'
    ELSE 'NONE' END
{%- endmacro %}
