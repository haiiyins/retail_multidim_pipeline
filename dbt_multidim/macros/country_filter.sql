{# Country predicate for the staging models.
   - vars.country_filter (from COUNTRY_FILTER in .env): one country for laptop development, ALL for the full run
   - vars.scale_countries: an explicit list, used by evaluation/scale_test.py to grow the data 1 → 2 → 3 countries
   - otherwise TRUE (every country present in Bronze; Silver and Gold filter on vars.countries where it matters) #}
{% macro country_where(col) -%}
  {% if var('country_filter') != 'ALL' %} {{ col }} = '{{ var('country_filter') }}'
  {% elif var('scale_countries', none) %} {{ col }} IN ({% for c in var('scale_countries') %}'{{ c }}'{% if not loop.last %}, {% endif %}{% endfor %})
  {% else %} TRUE {% endif %}
{%- endmacro %}

{# Date floor for the sales staging model: vars.sales_min_date (ISO date) keeps only sales on or after that day; used by the
   scale test's months axis (3 / 12 / 36 months of one country). Unset = no floor. #}
{% macro sales_date_floor(col) -%}
  {% if var('sales_min_date', none) %} {{ col }} >= TIMESTAMP '{{ var('sales_min_date') }}' {% else %} TRUE {% endif %}
{%- endmacro %}
