{# 5 price_type values → 5 promotion kinds #}
{% macro promo_kind(price_type) -%}
  CASE {{ price_type }}
    WHEN 'DAY_TO_DAY_PROMOTION' THEN 'DAILY'
    WHEN 'SEASON_SALES'         THEN 'SEASONAL'
    WHEN 'END_OF_LINE'          THEN 'CLEARANCE'
    WHEN 'DROP'                 THEN 'DROP'
    ELSE 'NONE' END
{%- endmacro %}
