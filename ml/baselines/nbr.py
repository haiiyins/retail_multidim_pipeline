"""NBR baselines of t31 (plan §7, ML-19/20): EASE and TIFU-KNN as stand-alone rankers over the full catalogue (repeat models not
masked, unlike their explore-only candidate sources), with their own tuning budget (tuning.yml space of the source, n_trials trials,
objective unconditional NDCG@20 on valid); SASRec = the unmasked top-100 list written by the R10 build (retrieval.full_catalogue),
with the R10 parameters (trained on the explore target only); sasrec_all = the R10 network and parameters trained on every model
bought in the window, repeats included (ml/retrieval/sasrec.py SASRecAll). Every list comes from the rolling model of
cutoff_for(anchor) and keeps the anchor_model_grid filter.
Usage: python ml/baselines/nbr.py --source ease|tifuknn [--tune] [--build]
       python ml/baselines/nbr.py --source sasrec|sasrec_all --build   →  data/ml/scores/<source>_nbr_{valid,test}_d30.parquet"""
import argparse, glob, importlib, json, os, sys, time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, load_config, ml_path
from ml.common.registry import Run
from ml.common.tuning import N_TRIALS, tune
from ml.rankers.gbdt import unconditional
from ml.retrieval import base
from ml.retrieval.base import CFG, Events, generate

COUNTRIES = ("SG", "TH", "VN")


def source(name):
    mod = importlib.import_module(f"ml.retrieval.{name}")
    return next(v() for v in vars(mod).values() if isinstance(v, type) and issubclass(v, base.Source) and v is not base.Source
                and getattr(v, "name", "") == name)


def to_scores(df):
    out = df[["member_id", "anchor_date", "model_code", "country_code", "score"]].copy()
    out["anchor_date"] = pd.to_datetime(out["anchor_date"])
    return out


def tuned(name):
    p = dict(CFG[name]["params"])
    path = ml_path("tuning", f"{name}_nbr.parquet")
    if os.path.exists(path):
        t = pd.read_parquet(path)
        t = t[(t["state"] == "COMPLETE") & (t["trial"] < N_TRIALS)]
        if len(t):
            p.update(json.loads(t.loc[t["value"].idxmax(), "params"]))
    return p


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", required=True)
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--build", action="store_true")
    a = ap.parse_args()
    con = connect()
    name = f"{a.source}_nbr"
    if a.source == "sasrec":
        for split in ("valid", "test"):
            files = glob.glob(ml_path("candidates", "sasrec_full", "*.parquet"))
            df = con.execute(f"SELECT * FROM read_parquet({files}) WHERE split = '{split}'").df()
            to_scores(df).to_parquet(os.path.join(ML_DIR, "scores", f"{name}_{split}_d30.parquet"), index=False)
            print(f"  {split}: NDCG@20 {unconditional(con, to_scores(df), split, 30)[0]:.4f}", flush=True)
        return
    if a.source == "sasrec_all":
        from ml.retrieval.sasrec import SASRecAll
        assert not a.tune, "sasrec_all keeps the R10 parameters"
        src = SASRecAll()
    else:
        src = source(a.source)
    loaded = {}

    def events(country):
        if country not in loaded:
            loaded[country] = Events.load(con, country)
        return loaded[country]

    if a.tune:
        cache = {}
        space = load_config("tuning")[a.source]["space"]

        def objective(params, trial):
            full = {**CFG[a.source]["params"], **params}
            sc = pd.concat([to_scores(p) for _, _, p in generate(src, full, con, ["valid"], COUNTRIES, events, cache, explore_only=False)])
            value, _ = unconditional(con, sc, "valid", 30)
            print(f"  trial {trial.number}: NDCG@20 (valid, unconditional) {value:.4f}  {params}", flush=True)
            return value

        study, _ = tune(name, objective, space=space)
        print(f"best {study.best_value:.4f}  {study.best_params}", flush=True)
    if a.build:
        params = base.tuned_params("sasrec") if a.source == "sasrec_all" else tuned(a.source)
        with Run(f"baseline:{name}", config={"source": a.source}, params=params) as run:
            for split in ("valid", "test"):
                t0 = time.time()
                sc = pd.concat([to_scores(p) for _, _, p in generate(src, params, con, [split], COUNTRIES, events, explore_only=False)])
                path = os.path.join(ML_DIR, "scores", f"{name}_{split}_d30.parquet")
                sc.to_parquet(path, index=False)
                v, _ = unconditional(con, sc, split, 30)
                run.metrics[f"{split}_ndcg20"] = v
                run.metrics[f"{split}_sec_per_1000"] = (time.time() - t0) / sc[["member_id", "anchor_date"]].drop_duplicates().shape[0] * 1000
                print(f"  {split}: NDCG@20 {v:.4f} → {path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
