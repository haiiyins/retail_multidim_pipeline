"""Step 7.5 — MT3 cost × gain table (WBS 4.5, issue #41).

Joins the ablation results (bootstrap CSVs of step 7.4) with the processing cost of what each arm removes:
  gain  = Full − arm on NDCG@20, HR@10 and Recall@50 (positive = the removed source helps), with the bootstrap CI and significance;
  cost  = wall time, peak RSS and output size of the dbt models that exist only for the removed source (profiler rows of step 7.5,
          `audit.model_cost` → data/audit/model_cost.csv), plus the Bronze load time of the raw tables that feed only that source
          (`audit.pipeline_run_metrics`, layer bronze), plus the training time of the arm (`audit.ablation_runs`).
Feature arms take their models from `exclude_models` in evaluation/ablation_configs.yml; candidate arms (no_r*) take the models that
produce the source (SOURCE_MODELS below); b0 removes the union of the feature groups F1 / F3 / F5 / sport and the sources R3 / R4.
Models the profiler did not time are listed in `models_not_profiled` and cost 0, so every cost is a lower bound.

Inputs (default data/audit/, or --experiments DIR for a folder copied from the server): ablation_results_d30.csv, ablation_results_d90.csv,
ablation_runs.csv, model_cost.csv, pipeline_run_metrics.csv. Output: data/audit/mt3_table.csv (one row per arm × Δ), printed as a table.
"""
import argparse, csv, pathlib, yaml

ap = argparse.ArgumentParser()
ap.add_argument("--experiments", default="data/audit", help="folder holding the experiment CSVs (default data/audit)")
ap.add_argument("--out", default="data/audit/mt3_table.csv")
a = ap.parse_args()
E = pathlib.Path(a.experiments)

CFG = yaml.safe_load(open("evaluation/ablation_configs.yml"))
SOURCE_MODELS = {   # dbt models that exist only to produce a candidate source (no_r1 and no_r5 read the fact and product entities, shared)
    "no_r2": ["gld_copurchase_lift"],
    "no_r3": ["slv_web_events_clean", "slv_user_member_links", "slv_user_to_member", "gld_web_stitched"],
    "no_r4": ["slv_member_sport_asof", "gld_sport_department_affinity"],
}
BRONZE_INPUTS = {   # raw tables that feed only the removed source
    "no_f1": ["all_store_selling_price"], "no_f3": ["dim_calendar"], "no_f5": ["tracking_ecom_events"], "no_sport": ["f_member_favorite_sport"],
    "no_r3": ["tracking_ecom_events"], "no_r4": ["f_member_favorite_sport"],
}
LABEL = {"b0": "B0: history + popularity only", "no_f1": "−F1 price", "no_f3": "−F3 promotion & calendar", "no_f5": "−F5 web", "no_stock": "−stock",
         "no_sport": "−sport", "no_r1": "−R1 repurchase", "no_r2": "−R2 co-purchase", "no_r3": "−R3 web", "no_r4": "−R4 sport × offer", "no_r5": "−R5 best-sellers"}


def models_for(arm):
    if arm == "b0":
        ms = set()
        for sub in ("no_f1", "no_f3", "no_f5", "no_sport", "no_r3", "no_r4"): ms |= set(models_for(sub))
        return sorted(ms)
    return sorted(set(CFG.get(arm, {}).get("exclude_models", []) or []) | set(SOURCE_MODELS.get(arm, [])))


def bronze_for(arm):
    if arm == "b0":
        return sorted({t for sub in ("no_f1", "no_f3", "no_f5", "no_sport") for t in BRONZE_INPUTS[sub]})
    return BRONZE_INPUTS.get(arm, [])


def read(name): return list(csv.DictReader(open(E / name)))


cost = {r["model_name"]: r for r in read("model_cost.csv")}
bronze = {}
for r in sorted(read("pipeline_run_metrics.csv"), key=lambda r: r["executed_at"]):
    if r["layer"] == "bronze": bronze[r["model_name"]] = float(r["wall_time_sec"])          # latest load per table wins
train = {(r["config"], int(r["delta"])): float(r["train_wall_sec"]) for r in read("ablation_runs.csv")}
rows = []
for delta in (30, 90):
    res = [r for r in read(f"ablation_results_d{delta}.csv") if r["scope"] == "ALL"]
    arms = sorted({r["config"] for r in res} - {"full"}, key=lambda c: list(LABEL).index(c) if c in LABEL else 99)
    for arm in arms:
        m = {r["metric"]: r for r in res if r["config"] == arm}
        ms = models_for(arm); timed = [x for x in ms if x in cost]; missing = [x for x in ms if x not in cost]
        wall = sum(float(cost[x]["wall_time_sec"]) for x in timed)
        rss = max((float(cost[x]["peak_rss_bytes"]) for x in timed), default=0.0) / 1e9
        out_gb = sum(float(cost[x]["output_bytes"]) for x in timed) / 1e9
        bz = sum(bronze.get(t, 0.0) for t in bronze_for(arm))
        row = {"config": arm, "delta": delta, "removed": LABEL.get(arm, arm), "models_removed": " ".join(ms) or "-", "models_costed": len(timed),
               "models_not_profiled": " ".join(missing) or "-", "model_wall_sec": round(wall, 1), "peak_rss_gb": round(rss, 1), "output_gb": round(out_gb, 2),
               "bronze_load_sec": round(bz), "total_cost_sec": round(wall + bz), "train_wall_sec": round(train.get((arm, delta), 0.0))}
        for metric, key in (("NDCG@20", "ndcg20"), ("HR@10", "hr10"), ("Recall@50", "recall50")):
            r = m[metric]
            row[f"gain_{key}"] = round(-float(r["diff_vs_full"]), 4)
            row[f"gain_{key}_lo"] = round(-float(r["diff_hi"]), 4); row[f"gain_{key}_hi"] = round(-float(r["diff_lo"]), 4)
            row[f"sig_{key}"] = r["significant"] in ("True", "true", "1")
        row["ndcg20_gain_per_1000s"] = round(row["gain_ndcg20"] / (row["total_cost_sec"] / 1000), 4) if row["total_cost_sec"] else None
        rows.append(row)

out = pathlib.Path(a.out); out.parent.mkdir(parents=True, exist_ok=True)
with open(out, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)
print(f"{'arm':10s} {'Δ':>3} {'gain NDCG@20':>13} {'sig':>4} {'gain HR@10':>11} {'gain Rec@50':>12} {'model s':>8} {'bronze s':>9} {'RSS GB':>7} {'out GB':>7} {'train s':>8}")
for r in rows:
    print(f"{r['config']:10s} {r['delta']:>3} {r['gain_ndcg20']:>+13.4f} {'yes' if r['sig_ndcg20'] else 'no':>4} {r['gain_hr10']:>+11.4f} {r['gain_recall50']:>+12.4f} "
          f"{r['model_wall_sec']:>8.0f} {r['bronze_load_sec']:>9.0f} {r['peak_rss_gb']:>7.1f} {r['output_gb']:>7.2f} {r['train_wall_sec']:>8.0f}")
print("→", out, f"({len(rows)} rows)")
