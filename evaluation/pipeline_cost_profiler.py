"""Step 7.5 — Cost per dbt model (WBS 4.5, issue #41): each model is rebuilt alone; wall time, peak RSS of the dbt process tree,
output rows and bytes go to audit.pipeline_run_metrics (the shared run log) and audit.model_cost (with bytes). Pass model names to
profile a subset, e.g. the models an ablation arm excludes."""
import subprocess, time, psutil, duckdb, os, sys, pathlib
from dotenv import load_dotenv
load_dotenv()
models = sys.argv[1:] or ["slv_member_bridge", "slv_dim_model", "slv_fact_sales_line", "slv_fact_returns", "slv_price_sku_interval", "slv_calendar_enriched",
                           "slv_web_events_clean", "slv_user_to_member", "slv_member_sport_asof", "slv_member_store_daily", "slv_stock_daily_model",
                           "gld_web_stitched", "gld_copurchase_lift", "gld_fs_member", "gld_fs_model_country", "gld_candidates", "gld_fs_pair", "gld_ranking_dataset"]
SCHEMA = {"slv_": "silver", "gld_": "gold", "qrt_": "quarantine", "stg_": "staging"}
run_id = time.strftime("%Y%m%d-%H%M%S")
for m in models:
    t0 = time.time(); peak = 0
    p = subprocess.Popen(f"cd dbt_multidim && dbt run --select {m}", shell=True)
    proc = psutil.Process(p.pid)
    while p.poll() is None:
        try:
            rss = proc.memory_info().rss + sum(c.memory_info().rss for c in proc.children(recursive=True)); peak = max(peak, rss)
        except psutil.Error: pass
        time.sleep(0.5)
    wall = time.time() - t0
    con = duckdb.connect(os.environ["DUCKDB_PATH"])
    schema = next((v for k, v in SCHEMA.items() if m.startswith(k)), "audit")
    try:
        rows = con.execute(f"SELECT COUNT(*) FROM {schema}.{m}").fetchone()[0]
        # on-disk size: distinct storage blocks of the table × block size (duckdb_tables().estimated_size is a row estimate, not bytes)
        blocks = con.execute(f"SELECT COUNT(DISTINCT block_id) FROM pragma_storage_info('{schema}.{m}') WHERE block_id >= 0").fetchone()[0]
        nbytes = blocks * con.execute("SELECT block_size FROM pragma_database_size()").fetchone()[0]
    except Exception: rows, nbytes = None, None
    con.execute("INSERT INTO audit.pipeline_run_metrics VALUES (?, ?, ?, ?, ?, ?, ?, current_timestamp)",
                [run_id, schema, m, os.environ.get("COUNTRY_FILTER", "ALL"), wall, rows, peak])
    con.execute("CREATE TABLE IF NOT EXISTS audit.model_cost(run_id VARCHAR, layer VARCHAR, model_name VARCHAR, country_filter VARCHAR, wall_time_sec DOUBLE, peak_rss_bytes BIGINT, output_rows BIGINT, output_bytes BIGINT, executed_at TIMESTAMP)")
    con.execute("INSERT INTO audit.model_cost VALUES (?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)", [run_id, schema, m, os.environ.get("COUNTRY_FILTER", "ALL"), wall, peak, rows, nbytes]); con.close()
    print(f"{m:28s} {wall:8.1f}s  peakRAM={peak/1e9:5.2f} GB  rows={rows}  bytes={nbytes}", flush=True)
