"""t37 (plan §12): training / tuning / inference cost from the run registry, and the retrieval cost of every source against the
explore coverage it adds (best valid Δ cand_explore over R1–R5@200). Wall times are on the shared GH200 (other users on the GPU),
so they are upper bounds. Builds split by country run in parallel: GPU-hours = sum, wall = max.
Usage: python ml/analysis/cost.py"""
import os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ml_path
from ml.common.registry import runs
from ml.common.tuning import N_TRIALS
from ml.retrieval.base import CFG

DEVICE = {"ease": "GPU", "tifuknn": "GPU", "item2vec": "CPU", "two_tower": "GPU", "sasrec": "GPU", "explin": "GPU", "rp3beta": "GPU",
          "trend": "CPU"}


def latest(r, model):
    d = r[(r["model"] == model) & (r["status"] == "ok")]
    return d.sort_values("finished").iloc[-1] if len(d) else None


def builds(r, source):
    """The latest complete build: the runs of the last build day (one per country when split)."""
    d = r[(r["model"] == f"cand:{source}") & (r["status"] == "ok")].sort_values("finished")
    if d.empty:
        return None, None
    start = pd.to_datetime(d["started"])
    last = d[start >= start.iloc[-1] - pd.Timedelta(hours=1)]   # the parallel per-country processes of the last build
    return last["wall_sec"].sum(), last["wall_sec"].max()


def budget(name):
    """(trials, hours, best value) of the first N_TRIALS trials of a study."""
    p = ml_path("tuning", f"{name}.parquet")
    if not os.path.exists(p):
        return None, None, None
    t = pd.read_parquet(p)
    t = t[(t["trial"] < N_TRIALS) & (t["state"] == "COMPLETE")]
    return len(t), t["wall_sec"].sum() / 3600, t["value"].max()


def retrieval(r):
    rows = []
    for s in CFG["mixer"]["learned"]:
        n, h, best = budget(s)
        gpu, wall = builds(r, s)
        rows.append({"source": s, "device": DEVICE.get(s, ""), "tuning trials": n, "tuning h": h,
                     "build h (sum)": gpu / 3600 if gpu else None, "build h (wall)": wall / 3600 if wall else None,
                     "best valid Δ cand_explore": best})
    t = pd.DataFrame(rows)
    t["Δ explore per build hour"] = t["best valid Δ cand_explore"] / t["build h (sum)"]
    return t


def rankers(r):
    rows = []
    for label, tune_name, run_name in (("P1-frozen (v2)", None, "p1_frozen_v2"), ("P1-tuned (v2)", "tune:p1_v2", "p1_tuned_v2"),
                                       ("P2 (v2)", "tune:p2_v2", "p2_v2"), ("P3 two heads", "tune:p3", "p3:v2:full"),
                                       ("P3 one head", None, "p3:v2:onehead"), ("EASE NBR", "tune:ease_nbr", "baseline:ease_nbr"),
                                       ("TIFU-KNN NBR", "tune:tifuknn_nbr", "baseline:tifuknn_nbr")):
        _, h, _ = budget(tune_name.split(":", 1)[1]) if tune_name else (None, None, None)
        f = latest(r, run_name)
        m = f["metrics"] if f is not None else {}
        rows.append({"model": label, "tuning h": h,
                     "final fit min": (m.get("train_sec") or (f["wall_sec"] if f is not None else None) or 0) / 60 or None,
                     "parameters": m.get("params"),
                     "test inference s / 1 000 anchors": m.get("test_score_sec_per_1000") or m.get("test_sec_per_1000")})
    return pd.DataFrame(rows)


def main():
    r = runs()
    a, b = retrieval(r), rankers(r)
    with open(ml_path("report", "t37.md"), "w") as f:
        f.write("# t37 — cost (shared GH200; wall times are upper bounds)\n\n## Retrieval sources\n\n")
        f.write(a.to_markdown(index=False, floatfmt=".3f") + "\n\n## Rankers and baselines\n\n")
        f.write(b.to_markdown(index=False, floatfmt=".3f") + "\n")
    print(a.round(3).to_string(index=False))
    print(b.round(3).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
