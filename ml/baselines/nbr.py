"""NBR baselines of t31 (plan §7, ML-19/20): EASE and TIFU-KNN as stand-alone rankers over the full catalogue (repeat models not
masked, unlike their explore-only candidate sources), with their own tuning budget (tuning.yml space of the source, n_trials trials,
objective unconditional NDCG@20 on valid); SASRec = the unmasked top-100 list written by the R10 build (retrieval.full_catalogue),
with the R10 parameters (trained on the explore target only); sasrec_all = the R10 network and parameters trained on every model
bought in the window, repeats included (ml/retrieval/sasrec.py SASRecAll); rex = the single-stage Repeat–Explore network
(ml/retrieval/rex.py), tuned like EASE / TIFU-KNN, rex2 its v2 (price dimension), and <rex|rex2>_<variant> their ablations with the
parameters of the full model. Every list comes from the rolling model of cutoff_for(anchor) and keeps the anchor_model_grid filter.
Usage: python ml/baselines/nbr.py --source ease|tifuknn|rex [--tune] [--build]
       python ml/baselines/nbr.py --source rex --build --seed 1   →  rex_nbr_seed1
       python ml/baselines/nbr.py --source rex_noweb|rex_nopop|rex_norep|rex_noseq|rex2_noprice|... --build
       python ml/baselines/nbr.py --source rex --level nature --build   →  rex_nature_nbr, items = product natures (t40)
       python ml/baselines/nbr.py --source rex_pool --build   →  rex_pool_nbr, one REX per cutoff over SG + TH + VN
       python ml/baselines/nbr.py --source sasrec|sasrec_all --build   →  data/ml/scores/<source>_nbr_{valid,test}_d30.parquet"""
import argparse, glob, importlib, json, os, sys, time
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, load_config, ml_path
from ml.common.levels import LEVELS, group_map
from ml.common.registry import Run
from ml.eval.granularity import group_counts, group_positives
from ml.eval.protocol import MAIN_COUNTRIES, metrics_from_counts
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
    ap.add_argument("--seed", type=int, default=0, help="training seed of a stochastic source; seed > 0 writes <source>_nbr_seed<N>")
    ap.add_argument("--level", default="model", choices=list(LEVELS),
                    help="REX trained directly at a product level, with the model-level parameters: rex_<level>_nbr")
    a = ap.parse_args()
    assert not (a.seed and a.tune), "seeds rebuild the tuned parameters"
    assert a.level == "model" or (a.source in ("rex", "rex2") and not a.tune), "levels: REX build only"
    con = connect()
    stem = a.source if a.level == "model" else f"{a.source}_{a.level}"
    name = f"{stem}_nbr" + (f"_seed{a.seed}" if a.seed else "")
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
    elif a.source == "rex_pool":
        from ml.retrieval.rex import REXPool
        assert not a.tune and a.level == "model", "rex_pool keeps the REX parameters"
        src = REXPool()
    elif a.source.split("_")[0] in ("rex", "rex2"):
        from ml.retrieval.rex import REX
        rex_base, _, variant = a.source.partition("_")
        assert not (a.tune and variant), "REX ablations keep the parameters of the full model"
        src = REX(variant or "full", rex_base, a.level)
    else:
        src = source(a.source)
    loaded = {}

    def events(country):
        if a.source == "rex_pool":
            if "pool" not in loaded:
                loaded["pool"] = Events.pool([Events.load(con, c) for c in COUNTRIES])
            return loaded["pool"].view(country)
        if country not in loaded:
            loaded[country] = Events.load(con, country, a.level)
        return loaded[country]

    def check(sc, path, split):
        """NDCG@20 (anchor mean, TH + VN at a level) of a written score set."""
        if a.level == "model":
            return unconditional(con, sc, split, 30)[0]
        res = metrics_from_counts(group_counts(con, path, group_positives(con, split, 30, a.level, group_map(con)), a.level,
                                               group_map(con), native=True), (10, 20, 50))
        return res[res["country_code"].isin(MAIN_COUNTRIES)]["NDCG@20"].mean()

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
        params = base.tuned_params("sasrec") if a.source == "sasrec_all" else tuned(src.base if hasattr(src, "base") else a.source)
        src.seed = a.seed
        with Run(f"baseline:{name}", config={"source": a.source, "seed": a.seed}, params=params) as run:
            for split in ("valid", "test"):
                t0 = time.time()
                sc = pd.concat([to_scores(p) for _, _, p in generate(src, params, con, [split], COUNTRIES, events, explore_only=False)])
                path = os.path.join(ML_DIR, "scores", f"{name}_{split}_d30.parquet")
                sc.to_parquet(path, index=False)
                v = check(sc, path, split)
                run.metrics[f"{split}_ndcg20"] = v
                run.metrics[f"{split}_sec_per_1000"] = (time.time() - t0) / sc[["member_id", "anchor_date"]].drop_duplicates().shape[0] * 1000
                print(f"  {split}: NDCG@20 {v:.4f} → {path}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
