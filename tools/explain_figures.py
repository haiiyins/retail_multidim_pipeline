"""Save the EXPLAIN ANALYZE text of the ASOF price lookup for the report (WBS 5.1, issue #44) → docs/figures/explain_analyze_asof_price.txt."""
import duckdb, os, pathlib
from dotenv import load_dotenv
load_dotenv()
country = os.environ.get("COUNTRY_FILTER", "VN") if os.environ.get("COUNTRY_FILTER", "ALL") != "ALL" else "VN"
c = duckdb.connect(os.environ["DUCKDB_PATH"], read_only=True)
anchor = c.execute("SELECT MIN(anchor_date) FROM gold.anchor_model_grid WHERE country_code = ? AND anchor_date >= DATE '2026-02-01'", [country]).fetchone()[0]
q = f"""SELECT g.model_code, g.anchor_date, MEDIAN(p.price) AS price_local
FROM (SELECT * FROM gold.anchor_model_grid WHERE country_code = '{country}' AND anchor_date = DATE '{anchor}') g
JOIN silver.slv_dim_model dm USING (model_code)
ASOF LEFT JOIN silver.slv_price_sku_interval p
  ON p.item_code = dm.item_code AND p.country_code = g.country_code AND p.price_scope = 'NATIONAL' AND g.anchor_date >= p.eff_start
WHERE p.eff_end >= g.anchor_date
GROUP BY 1, 2"""
plan = c.execute("EXPLAIN ANALYZE " + q).fetchall()
text = "\n".join(r[1] if len(r) > 1 else str(r[0]) for r in plan)
out = pathlib.Path("docs/figures/explain_analyze_asof_price.txt")
out.write_text(f"-- EXPLAIN ANALYZE of the ASOF price lookup at one anchor date ({country}, DuckDB {duckdb.__version__}): anchor_model_grid × slv_dim_model ASOF slv_price_sku_interval, median per model\n" + q + "\n\n" + text + "\n")
print("→", out)
