"""Step 7.6 — Scale test (WBS 4.6, issue #42): Silver → anchor grid → Gold wall time and peak RSS as the data grows.
Two axes:  countries   python evaluation/scale_test.py VN TH SG          cumulative: VN, then VN+TH, then VN+TH+SG
           months      python evaluation/scale_test.py VN --months 3,12,36   one country, the last N months of sales before the export end
Each point reruns the staging / Silver / quarantine / audit models with dbt vars (scale_countries, sales_min_date), rebuilds the
anchor grid and the Gold layer, and records bronze rows, wall time and peak RSS of the dbt / python children in audit.scale_test.
Writes data/audit/scale_test.png. The run leaves the lakehouse at the last point; rerun `make silver && make gold` to restore Full."""
import subprocess, time, duckdb, os, sys, argparse, psutil, datetime, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from dotenv import load_dotenv
load_dotenv()
ap = argparse.ArgumentParser()
ap.add_argument("countries", nargs="+", help="country codes in cumulative order (countries axis) or one country (months axis)")
ap.add_argument("--months", default="", help="comma-separated month windows for the months axis, e.g. 3,12,36")
a = ap.parse_args()
DB = os.environ["DUCKDB_PATH"]

def timed(cmd):   # run a shell command, return (wall seconds, peak RSS bytes of the process tree)
    t0 = time.time(); p = subprocess.Popen(cmd, shell=True); proc = psutil.Process(p.pid); peak = 0
    while p.poll() is None:
        try: peak = max(peak, proc.memory_info().rss + sum(c.memory_info().rss for c in proc.children(recursive=True)))
        except psutil.Error: pass
        time.sleep(0.5)
    if p.returncode: sys.exit(f"command failed ({p.returncode}): {cmd}")
    return time.time() - t0, peak

def point(label, subset, min_date, months=None):
    where = ", ".join(f"'{c}'" for c in subset)
    con = duckdb.connect(DB, read_only=True)
    q = f"SELECT COUNT(*) FROM bronze.sales_detail WHERE economical_businessunit_country_code IN ({where})" + (f" AND gmv_recorded_at >= TIMESTAMP '{min_date}'" if min_date else "")
    rows = con.execute(q).fetchone()[0]; con.close()
    vars_ = "{scale_countries: [" + where + "]" + (f", sales_min_date: '{min_date}'" if min_date else "") + "}"
    w1, m1 = timed(f"cd dbt_multidim && dbt run --select staging silver quarantine audit --exclude leakage_violations candidate_recall --vars \"{vars_}\"")
    w2, m2 = timed(f"{sys.executable} evaluation/build_anchor_grid.py")
    w3, m3 = timed(f"cd dbt_multidim && dbt run --select gold leakage_violations candidate_recall --vars \"{vars_}\"")
    wall, peak = w1 + w2 + w3, max(m1, m2, m3)
    con = duckdb.connect(DB)
    con.execute("CREATE TABLE IF NOT EXISTS audit.scale_test(axis VARCHAR, label VARCHAR, countries VARCHAR, months INT, bronze_rows BIGINT, "
                "silver_sec DOUBLE, grid_sec DOUBLE, gold_sec DOUBLE, wall_time_sec DOUBLE, peak_rss_gb DOUBLE, threads INT, memory_limit VARCHAR, executed_at TIMESTAMP)")
    con.execute("INSERT INTO audit.scale_test VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, current_timestamp)",
                ["months" if min_date else "countries", label, ",".join(subset), months, rows, w1, w2, w3, wall, peak / 1e9,
                 int(os.environ.get("DUCKDB_THREADS", 0)), os.environ.get("DUCKDB_MEMORY", "")])
    con.close()
    print(f"{label:14s} bronze_rows={rows:>12,}  silver {w1:6.0f}s  grid {w2:5.0f}s  gold {w3:6.0f}s  total {wall:6.0f}s  peak {peak/1e9:5.1f} GB", flush=True)
    return rows, wall

xs, ys, labels = [], [], []
if a.months:
    con = duckdb.connect(DB, read_only=True)
    end = con.execute("SELECT MAX(CAST(gmv_recorded_at AS DATE)) FROM bronze.sales_detail").fetchone()[0]; con.close()
    for mth in [int(m) for m in a.months.split(",")]:
        min_date = (end.replace(day=1) - datetime.timedelta(days=30 * mth)).isoformat()
        r, w = point(f"{mth}m {a.countries[0]}", a.countries[:1], min_date, mth); xs.append(r); ys.append(w); labels.append(f"{mth} months")
else:
    for k in range(1, len(a.countries) + 1):
        r, w = point("+".join(a.countries[:k]), a.countries[:k], None); xs.append(r); ys.append(w); labels.append("+".join(a.countries[:k]))
plt.figure(figsize=(6, 4)); plt.plot(xs, ys, marker="o")
for x, y, l in zip(xs, ys, labels): plt.annotate(l, (x, y), textcoords="offset points", xytext=(4, 4), fontsize=8)
plt.xlabel("Bronze rows (sales_detail)"); plt.ylabel("Silver → Gold wall time (s)"); plt.grid(True); plt.tight_layout()
out = "data/audit/scale_test_months.png" if a.months else "data/audit/scale_test.png"
plt.savefig(out, dpi=150); print("→", out)
