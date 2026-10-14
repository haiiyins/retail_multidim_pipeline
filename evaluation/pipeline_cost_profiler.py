"""Step 7.5 — Cost per dbt model: wall time, peak RSS of the child process, output rows/bytes → audit.pipeline_run_metrics"""
import subprocess, time, psutil, duckdb, os, sys, pathlib
from dotenv import load_dotenv
load_dotenv()
models = sys.argv[1:] or ["slv_member_bridge", "slv_dim_model", "slv_fact_sales_line", "slv_price_sku_interval", "slv_calendar_enriched",
                           "slv_web_events_clean", "slv_user_to_member", "slv_stock_daily_model", "gld_fs_member", "gld_fs_model_country", "gld_candidates", "gld_fs_pair"]
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
    schema = "silver" if m.startswith("slv") else "gold"
    try: rows = con.execute(f"SELECT COUNT(*) FROM {schema}.{m}").fetchone()[0]
    except Exception: rows = None
    con.execute("INSERT INTO audit.pipeline_run_metrics VALUES (?, ?, ?, ?, ?, ?, ?, current_timestamp)",
                [run_id, schema, m, os.environ.get("COUNTRY_FILTER", "ALL"), wall, rows, peak]); con.close()
    print(f"{m:28s} {wall:8.1f}s  peakRAM={peak/1e9:5.2f} GB  rows={rows}")
