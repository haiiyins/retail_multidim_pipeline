{# on-run-end hook: one row per successful model in audit.pipeline_run_metrics (same table the Bronze loader writes), so every
   layer's wall time and row count is logged by the run itself (runbook §7.5). output_bytes stays NULL for dbt tables. #}
{% macro log_run_results(results) %}
  {% if execute %}
    {% set rows = [] %}
    {% for r in results if r.node.resource_type == 'model' and r.status == 'success' and r.node.config.materialized in ('table', 'view', 'incremental') %}
      {% set rel = api.Relation.create(database=r.node.database, schema=r.node.schema, identifier=r.node.alias) %}
      {% set cnt = run_query("SELECT COUNT(*) FROM " ~ rel) %}
      {% set n = cnt.columns[0].values()[0] if cnt else none %}
      {% do rows.append("('" ~ invocation_id ~ "', '" ~ r.node.schema ~ "', '" ~ r.node.alias ~ "', '" ~ var('country_filter') ~ "', "
                        ~ r.execution_time ~ ", " ~ (n if n is not none else 'NULL') ~ ", NULL, current_timestamp)") %}
    {% endfor %}
    {% if rows %}
      {% do run_query("CREATE SCHEMA IF NOT EXISTS audit") %}
      {% do run_query("CREATE TABLE IF NOT EXISTS audit.pipeline_run_metrics(run_id VARCHAR, layer VARCHAR, model_name VARCHAR, country_filter VARCHAR, wall_time_sec DOUBLE, output_rows BIGINT, output_bytes BIGINT, executed_at TIMESTAMP DEFAULT current_timestamp)") %}
      {% do run_query("INSERT INTO audit.pipeline_run_metrics VALUES " ~ rows | join(", ")) %}
      {{ log("pipeline_run_metrics: " ~ rows | length ~ " models logged", info=True) }}
    {% endif %}
  {% endif %}
{% endmacro %}
