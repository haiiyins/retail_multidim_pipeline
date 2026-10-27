"""Step 7.6 — Scale test: run Silver→Gold for 1 → 2 → 3 countries (VN, then +TH, then +SG); record wall time vs Bronze rows; plot."""
import subprocess, time, duckdb, os, sys, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from dotenv import load_dotenv
load_dotenv()
countries = sys.argv[1:]   # cumulative order, e.g. VN TH SG
assert countries, "pass the country codes in cumulative order"
con = duckdb.connect(os.environ["DUCKDB_PATH"])
con.execute("CREATE TABLE IF NOT EXISTS audit.scale_test(n_countries INT, countries VARCHAR, bronze_rows BIGINT, wall_time_sec DOUBLE, executed_at TIMESTAMP DEFAULT current_timestamp)")
xs, ys = [], []
for k in range(1, len(countries) + 1):
    subset = countries[:k]; env = dict(os.environ, COUNTRY_FILTER="ALL")
    where = ",".join(f"'{c}'" for c in subset)
    rows = con.execute(f"SELECT COUNT(*) FROM bronze.sales_detail WHERE economical_businessunit_country_code IN ({where})").fetchone()[0]
    t0 = time.time()
    subprocess.run(f"cd dbt_multidim && dbt run --select silver gold --vars '{{countries: [{where}]}}'", shell=True, check=True, env=env)
    wall = time.time() - t0
    con.execute("INSERT INTO audit.scale_test VALUES (?, ?, ?, ?, current_timestamp)", [k, ",".join(subset), rows, wall])
    xs.append(rows); ys.append(wall); print(k, subset, rows, f"{wall:.0f}s")
plt.plot(xs, ys, marker="o"); plt.xlabel("Bronze rows (sales_detail)"); plt.ylabel("Silver→Gold wall time (s)"); plt.grid(True)
plt.savefig("data/audit/scale_test.png", dpi=150); print("→ data/audit/scale_test.png")
