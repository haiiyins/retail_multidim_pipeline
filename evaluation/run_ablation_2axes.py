"""Step 7.3 — Two-axis ablation matrix × Δ. For arms with exclude_models: rerun dbt without those models to measure real cost, then train."""
import subprocess, yaml, sys, os, time, duckdb
from dotenv import load_dotenv
load_dotenv()
cfgs = yaml.safe_load(open("evaluation/ablation_configs.yml"))
order = ["full", "b0", "no_f1", "no_f3", "no_f5", "no_stock", "no_sport", "no_r1", "no_r2", "no_r3", "no_r4", "no_r5"]
measure_cost = "--measure-cost" in sys.argv
con = duckdb.connect(os.environ["DUCKDB_PATH"])
con.execute("CREATE TABLE IF NOT EXISTS audit.ablation_runs(config VARCHAR, delta INT, wall_time_sec DOUBLE, executed_at TIMESTAMP DEFAULT current_timestamp)")
for name in order:
    for delta in (30, 90):
        t0 = time.time()
        if measure_cost and cfgs[name].get("exclude_models"):
            excl = " ".join(cfgs[name]["exclude_models"])
            subprocess.run(f"cd dbt_multidim && dbt run --select silver gold --exclude {excl}", shell=True, check=True)
        subprocess.run([sys.executable, "evaluation/train_eval_lambdarank.py", "--config", name, "--delta", str(delta)], check=True)
        con.execute("INSERT INTO audit.ablation_runs VALUES (?, ?, ?, current_timestamp)", [name, delta, time.time() - t0])
        print(f"=== {name} Δ={delta} done in {time.time()-t0:.0f}s")
if measure_cost:
    subprocess.run("cd dbt_multidim && dbt run --select silver gold", shell=True, check=True)   # restore Full
