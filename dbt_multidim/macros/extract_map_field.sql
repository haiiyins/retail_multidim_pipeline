{# Nested columns of the 2026-10-27 Parquet exports are real STRUCT / LIST<STRUCT> values, not the Spark toString
   "Map(k -> v)" strings profiled in the first CSV export (issue #6). Scalar fields are read with a plain path, e.g.
   metadata.user_details.member_id; these helpers cover the list-valued fields. DuckDB 2.x lambda syntax: lambda x: ... #}

{# model codes of the products attached to a web event (metadata.product_details is a list of structs) #}
{% macro product_model_codes(col) -%}
  list_filter(list_transform({{ col }}.product_details, lambda p: p.model_code), lambda x: x IS NOT NULL AND x <> '' AND x <> 'null')
{%- endmacro %}

{# item codes of the products attached to a web event #}
{% macro product_item_codes(col) -%}
  list_filter(list_transform({{ col }}.product_details, lambda p: p.item_code), lambda x: x IS NOT NULL AND x <> '' AND x <> 'null')
{%- endmacro %}

{# total amount of one price-modifier rule on a sales line (sales_detail.price_modifier_detail, e.g. 'DayToDayPromotion', 'DiscountCoupon') #}
{% macro modifier_amount(col, rule) -%}
  COALESCE(list_sum(list_transform(list_filter({{ col }}, lambda m: m.rule = '{{ rule }}'), lambda m: m.amt)), 0)
{%- endmacro %}
