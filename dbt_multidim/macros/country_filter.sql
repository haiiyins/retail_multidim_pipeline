{# Country-parameterised WHERE clause #}
{% macro country_where(col) -%}
  {% if var('country_filter') != 'ALL' %} {{ col }} = '{{ var('country_filter') }}' {% else %} TRUE {% endif %}
{%- endmacro %}
