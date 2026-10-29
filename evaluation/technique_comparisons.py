"""Step 7.6b — Four with / without technique comparisons on one country (WBS 4.7, issue #43): one measured number each instead of
unmeasured performance claims. Every variant runs in its own child process (fresh DuckDB, DUCKDB_MEMORY / DUCKDB_THREADS from .env),
three repetitions, wall time and peak RSS of the child; medians go to audit.technique_comparisons and a summary table is printed.
  1 parquet_vs_csv     same 10-column VN sales extract written once as CSV and as Parquet; same GROUP BY query on each
  2 projection         materialise VN 2025 sales from the raw Parquet with the 24 staging columns vs all 141 columns
  3 asof_vs_explode    price at every anchor date of the grid (176 Mondays) for every priced SKU: ASOF JOIN vs exploding the intervals
                       to one row per SKU per day over the whole span (the naive approach); an out-of-memory failure is recorded as a result
  4 regex_vs_python    member / user / order ids from the web-event metadata as a JSON string: SQL regexp_extract vs a row-wise
                       Python re loop with the same three patterns (the struct path used in production is the reference). The Python
                       baseline holds every row in memory, so on a full country set TECHNIQUE_EVENT_LIMIT=<n> to take a reservoir
                       sample of n events (seed 42) after the country filter; the laptop's one-day sample needs no limit.
Usage: python evaluation/technique_comparisons.py [--reps 3]      temp files under $DATA_ROOT/duck_temp, removed at the end.
Env: TECHNIQUE_COUNTRY (default VN), TECHNIQUE_EVENT_LIMIT (default none = all events of the country)."""
import duckdb, os, sys, time, json, argparse, subprocess, pathlib, statistics, psutil
from dotenv import load_dotenv
load_dotenv()
DB = os.environ["DUCKDB_PATH"]; ROOT = pathlib.Path(os.environ.get("DATA_ROOT", "./data")); TMP = ROOT / "duck_temp"
RAW = ROOT / "raw_csv"
COUNTRY = os.environ.get("TECHNIQUE_COUNTRY", "VN")
EVENT_LIMIT = int(os.environ["TECHNIQUE_EVENT_LIMIT"]) if os.environ.get("TECHNIQUE_EVENT_LIMIT") else None
STG_COLS = """transaction_id, transaction_num_line, customer_purchase_order_id, transaction_version_at, transaction_status, item_operation_type, item_type,
    item_code, model_code, economical_businessunit_country_code, economical_businessunit_id, transaction_channel_type, customer_identification_type,
    gmv_recorded_at, gmv_item_quantity, gmv_amount, gmv_amount_euros, regular_selling_price, discount_amount, exchange_rate_local_to_euros,
    transaction_link_detail, return_reason_code, return_reason_type, year, month"""

def fresh():
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY', '10GB')}'"); con.execute(f"SET threads={int(os.environ.get('DUCKDB_THREADS', '6'))}")
    con.execute(f"SET temp_directory='{TMP}'")
    return con

def prepare():
    TMP.mkdir(parents=True, exist_ok=True)
    con = fresh(); con.execute(f"ATTACH '{DB}' AS lh (READ_ONLY)")
    con.execute(f"""COPY (SELECT transaction_id, item_code, model_code, economical_businessunit_country_code AS country_code,
                           economical_businessunit_id AS store_id, gmv_recorded_at, gmv_item_quantity, gmv_amount,
                           item_operation_type, transaction_status FROM lh.bronze.sales_detail WHERE economical_businessunit_country_code = '{COUNTRY}')
                    TO '{TMP}/tc_sales.parquet' (FORMAT PARQUET)""")
    con.execute(f"COPY (SELECT * FROM read_parquet('{TMP}/tc_sales.parquet')) TO '{TMP}/tc_sales.csv' (FORMAT CSV, HEADER)")
    sample = f"USING SAMPLE {EVENT_LIMIT} ROWS (reservoir, 42)" if EVENT_LIMIT else ""   # DuckDB samples the FROM before WHERE, hence the subquery
    con.execute(f"""COPY (SELECT id, to_json(metadata) AS meta_json, metadata.user_details.member_id AS member_id_native
                    FROM (SELECT id, metadata FROM lh.bronze.tracking_ecom_events WHERE country_code = '{COUNTRY}') {sample})
                    TO '{TMP}/tc_events.parquet' (FORMAT PARQUET)""")
    con.execute(f"COPY (SELECT item_code, eff_start, eff_end, price FROM lh.silver.slv_price_sku_interval WHERE country_code = '{COUNTRY}' AND price_scope = 'NATIONAL') TO '{TMP}/tc_prices.parquet' (FORMAT PARQUET)")
    con.execute(f"COPY (SELECT DISTINCT anchor_date FROM lh.gold.anchor_model_grid WHERE country_code = '{COUNTRY}') TO '{TMP}/tc_anchors.parquet' (FORMAT PARQUET)")
    n = {f: con.execute(f"SELECT COUNT(*) FROM read_parquet('{TMP}/{f}.parquet')").fetchone()[0] for f in ("tc_sales", "tc_events", "tc_prices")}
    con.close(); return n

AGG = "SELECT date_trunc('month', gmv_recorded_at) AS m, item_operation_type, COUNT(*) AS n, SUM(gmv_amount) AS gmv FROM {src} GROUP BY 1, 2"
ANCHORS = f"(SELECT DISTINCT anchor_date AS d FROM read_parquet('{TMP}/tc_anchors.parquet'))"

def variant(name):   # runs in the child: returns rows touched / produced
    con = fresh()
    if name == "csv":
        return con.execute(AGG.format(src=f"read_csv('{TMP}/tc_sales.csv', header=true)")).fetchall().__len__()
    if name == "parquet":
        return con.execute(AGG.format(src=f"read_parquet('{TMP}/tc_sales.parquet')")).fetchall().__len__()
    if name in ("all_columns", "needed_columns"):
        cols = "*" if name == "all_columns" else STG_COLS
        con.execute(f"CREATE TEMP TABLE t AS SELECT {cols} FROM read_parquet('{RAW}/sales_detail.parquet') WHERE economical_businessunit_country_code = '{COUNTRY}' AND year = 2025")
        return con.execute("SELECT COUNT(*) FROM t").fetchone()[0]
    if name == "asof":
        return con.execute(f"""SELECT COUNT(*) FROM (
            SELECT s.item_code, a.d, p.price FROM (SELECT DISTINCT item_code FROM read_parquet('{TMP}/tc_prices.parquet')) s CROSS JOIN {ANCHORS} a
            ASOF LEFT JOIN read_parquet('{TMP}/tc_prices.parquet') p ON p.item_code = s.item_code AND a.d >= p.eff_start
            WHERE p.eff_end >= a.d)""").fetchone()[0]
    if name == "daily_explode":   # the naive design: a materialised SKU × day price table over the span, then an equi-join on the anchor day
        con.execute(f"""CREATE TEMP TABLE daily AS
            WITH span AS (SELECT MIN(d) AS d0, MAX(d) AS d1 FROM {ANCHORS}),
            days AS (SELECT UNNEST(generate_series(d0, d1, INTERVAL 1 DAY))::DATE AS d FROM span)
            SELECT p.item_code, days.d, p.price FROM read_parquet('{TMP}/tc_prices.parquet') p JOIN days ON days.d BETWEEN p.eff_start AND p.eff_end""")
        return con.execute(f"""SELECT COUNT(*) FROM (
            SELECT s.item_code, a.d, dl.price FROM (SELECT DISTINCT item_code FROM read_parquet('{TMP}/tc_prices.parquet')) s CROSS JOIN {ANCHORS} a
            JOIN daily dl ON dl.item_code = s.item_code AND dl.d = a.d)""").fetchone()[0]
    if name == "sql_regex":
        return con.execute(f"""SELECT COUNT(NULLIF(regexp_extract(meta_json, '"member_id":\\s*"([^"]+)"', 1), '')) + COUNT(NULLIF(regexp_extract(meta_json, '"user_id":\\s*"([^"]+)"', 1), ''))
                              + COUNT(NULLIF(regexp_extract(meta_json, '"transaction_id":\\s*"([^"]+)"', 1), '')) FROM read_parquet('{TMP}/tc_events.parquet')""").fetchone()[0]
    if name == "python_rowwise":   # the same three patterns, applied row by row in Python
        import re
        pats = [re.compile(r'"member_id":\s*"([^"]+)"'), re.compile(r'"user_id":\s*"([^"]+)"'), re.compile(r'"transaction_id":\s*"([^"]+)"')]
        n = 0
        for (s,) in con.execute(f"SELECT meta_json FROM read_parquet('{TMP}/tc_events.parquet')").fetchall():
            if s: n += sum(1 for pt in pats if pt.search(s))
        return n
    if name == "native_struct":
        return con.execute(f"SELECT COUNT(member_id_native) FROM read_parquet('{TMP}/tc_events.parquet')").fetchone()[0]
    raise SystemExit(f"unknown variant {name}")

COMPARISONS = [("parquet_vs_csv", "csv", "parquet"), ("projection", "all_columns", "needed_columns"),
               ("asof_vs_explode", "daily_explode", "asof"), ("regex_vs_python", "python_rowwise", "sql_regex")]

if __name__ == "__main__" and "--variant" in sys.argv:
    t0 = time.time()
    try: rows, err = variant(sys.argv[sys.argv.index("--variant") + 1]), None
    except Exception as e: rows, err = -1, str(e).splitlines()[0][:120]
    print(json.dumps({"rows": rows, "wall": time.time() - t0, "error": err})); sys.exit(0)

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--reps", type=int, default=3); a = ap.parse_args()
    sizes = prepare(); print("prepared:", sizes, flush=True)
    results = {}
    names = [v for c in COMPARISONS for v in c[1:]] + ["native_struct"]
    for v in names:
        walls, peaks, rows = [], [], None
        for _ in range(a.reps):
            p = subprocess.Popen([sys.executable, __file__, "--variant", v], stdout=subprocess.PIPE, text=True); proc = psutil.Process(p.pid); peak = 0
            while p.poll() is None:
                try: peak = max(peak, proc.memory_info().rss + sum(c.memory_info().rss for c in proc.children(recursive=True)))
                except psutil.Error: pass
                time.sleep(0.2)
            out = json.loads(p.stdout.read().strip().splitlines()[-1]); walls.append(out["wall"]); peaks.append(peak); rows = out["rows"]; err = out.get("error")
        results[v] = (statistics.median(walls), max(peaks), rows, err); print(f"{v:16s} median {results[v][0]:7.2f}s  peak {results[v][1]/1e9:5.2f} GB  rows={rows:,}" + (f"  FAILED: {err}" if err else ""), flush=True)
    con = duckdb.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS audit.technique_comparisons(comparison VARCHAR, variant VARCHAR, role VARCHAR, country VARCHAR, rows BIGINT, "
                "wall_median_sec DOUBLE, peak_rss_gb DOUBLE, reps INT, threads INT, memory_limit VARCHAR, error VARCHAR, executed_at TIMESTAMP)")
    print("\n| comparison | baseline | technique | baseline s | technique s | speed-up | baseline peak GB | technique peak GB |\n|---|---|---|---:|---:|---:|---:|---:|")
    for comp, base, tech in COMPARISONS:
        for v, role in ((base, "baseline"), (tech, "technique")):
            con.execute("INSERT INTO audit.technique_comparisons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)",
                        [comp, v, role, COUNTRY, results[v][2], results[v][0], results[v][1] / 1e9, a.reps, int(os.environ.get("DUCKDB_THREADS", 0)), os.environ.get("DUCKDB_MEMORY", ""), results[v][3]])
        b, t = results[base], results[tech]
        print(f"| {comp} | {base}{' (failed)' if b[3] else ''} | {tech}{' (failed)' if t[3] else ''} | {b[0]:.2f} | {t[0]:.2f} | ×{b[0]/t[0]:.1f} | {b[1]/1e9:.2f} | {t[1]/1e9:.2f} |")
    con.execute("INSERT INTO audit.technique_comparisons VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)",
                ["regex_vs_python", "native_struct", "reference", COUNTRY, results["native_struct"][2], results["native_struct"][0], results["native_struct"][1] / 1e9, a.reps, int(os.environ.get("DUCKDB_THREADS", 0)), os.environ.get("DUCKDB_MEMORY", ""), results["native_struct"][3]])
    con.close()
    for f in ("tc_sales.parquet", "tc_sales.csv", "tc_events.parquet", "tc_prices.parquet", "tc_anchors.parquet"):
        try: (TMP / f).unlink()
        except FileNotFoundError: pass
    print("→ audit.technique_comparisons")
