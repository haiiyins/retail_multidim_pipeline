{# Extract one field from a Spark toString-style Map(k -> v) / List(Map(k -> v, ...)) string #}
{% macro extract_map_field(col, key) -%}
  NULLIF(TRIM(regexp_extract({{ col }}, '(?:^|[ ,(]){{ key }} -> ([^,)]*)', 1)), 'null')
{%- endmacro %}

{# Extract every value of a key (e.g. model_code inside product_details) #}
{% macro extract_map_list(col, key) -%}
  list_filter(regexp_extract_all({{ col }}, '{{ key }} -> ([^,)]*)', 1), x -> x <> 'null' AND x <> '')
{%- endmacro %}
