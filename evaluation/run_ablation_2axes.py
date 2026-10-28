"""Step 7.3 — Two-axis ablation matrix × Δ (WBS 4.2 / 4.3, issues #38, #39).
Runs the ranker for each configuration of evaluation/ablation_configs.yml. With --measure-cost, an arm that lists exclude_models
first reruns dbt (silver + gold) without those models, so the processing cost of the data source is measured, not only the
columns dropped; wall times go to audit.ablation_runs (dbt and training separately) and per-model costs to audit.pipeline_run_metrics.
Every arm reuses evaluation/frozen_params.json (frozen by the Full run, #37); --no-freeze / --tag are passed through for laptop
smoke runs. The no_stock arm is skipped while dbt vars.use_stock is false (issue #21)."""
import subprocess, yaml, sys, os, time, duckdb, argparse
from dotenv import load_dotenv
load_dotenv()
ap = argparse.ArgumentParser()
ap.add_argument("--arms", default="", help="comma-separated configurations to run (default: all, in the design order)")
ap.add_argument("--deltas", default="30,90", help="label horizons, comma-separated")
ap.add_argument("--measure-cost", action="store_true", help="rerun dbt without the arm's excluded models before training")
ap.add_argument("--no-freeze", action="store_true", help="passed to the trainer (laptop smoke runs)")
ap.add_argument("--tag", default="", help="passed to the trainer: suffix of the result files")
a = ap.parse_args()
cfgs = yaml.safe_load(open("evaluation/ablation_configs.yml"))
order = ["full", "b0", "no_f1", "no_f3", "no_f5", "no_stock", "no_sport", "no_r1", "no_r2", "no_r3", "no_r4", "no_r5"]
arms = [x for x in a.arms.split(",") if x] or order
unknown = [x for x in arms if x not in cfgs]
if unknown: sys.exit(f"unknown configuration(s): {unknown}")
use_stock = yaml.safe_load(open("dbt_multidim/dbt_project.yml"))["vars"].get("use_stock", False)
if not use_stock and "no_stock" in arms:
    print("skip no_stock: dbt vars.use_stock is false (issue #21)"); arms.remove("no_stock")
deltas = [int(d) for d in a.deltas.split(",")]
extra = (["--no-freeze"] if a.no_freeze else []) + (["--tag", a.tag] if a.tag else [])

def log_run(name, delta, dbt_t, train_t):   # open the database only for the insert: the trainer and dbt need the file lock
    con = duckdb.connect(os.environ["DUCKDB_PATH"])
    con.execute("CREATE TABLE IF NOT EXISTS audit.ablation_runs(config VARCHAR, delta INT, tag VARCHAR, dbt_wall_sec DOUBLE, train_wall_sec DOUBLE, executed_at TIMESTAMP)")
    con.execute("INSERT INTO audit.ablation_runs VALUES (?, ?, ?, ?, ?, current_timestamp)", [name, delta, a.tag, dbt_t, train_t])
    con.close()

for name in arms:
    for delta in deltas:
        dbt_t = 0.0
        if a.measure_cost and cfgs[name].get("exclude_models"):
            t0 = time.time(); excl = " ".join(cfgs[name]["exclude_models"])
            subprocess.run(f"cd dbt_multidim && dbt run --select silver gold leakage_violations --exclude {excl}", shell=True, check=True)
            dbt_t = time.time() - t0
        t0 = time.time()
        subprocess.run([sys.executable, "evaluation/train_eval_lambdarank.py", "--config", name, "--delta", str(delta)] + extra, check=True)
        train_t = time.time() - t0
        log_run(name, delta, dbt_t, train_t)
        print(f"=== {name} Δ={delta}: dbt {dbt_t:.0f}s, train {train_t:.0f}s", flush=True)
if a.measure_cost:   # restore the Full configuration of the lakehouse
    subprocess.run("cd dbt_multidim && dbt run --select silver gold leakage_violations", shell=True, check=True)
