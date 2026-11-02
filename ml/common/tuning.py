"""Fair tuning harness (plan D5): every model with hyper-parameters gets the same Optuna budget on valid.

Budget: N_TRIALS = 30 trials of TPE (seed 0) is the binding budget; an optional per-model timeout (tuning.yml) only stops a study
early and is reported. Objective: unconditional NDCG@20 on valid (ml/eval/protocol.py), maximised. Search spaces are declared in
ml/config/tuning.yml. Every trial is written to data/ml/tuning/<model>.parquet (model, trial, params, value, state, wall_sec) and the
summary (best, median of completed trials) to the run registry."""
import json, time
import numpy as np, optuna, pandas as pd
from ml.common.data import load_config, ml_path
from ml.common.registry import Run

N_TRIALS = 30


def suggest(trial, space):
    params = {}
    for name, s in space.items():
        kind = s["type"]
        if kind == "int":
            params[name] = trial.suggest_int(name, s["low"], s["high"], log=s.get("log", False))
        elif kind == "float":
            params[name] = trial.suggest_float(name, s["low"], s["high"], log=s.get("log", False))
        elif kind == "categorical":
            params[name] = trial.suggest_categorical(name, s["choices"])
        elif kind == "fixed":
            params[name] = s["value"]
        else:
            raise ValueError(f"unknown parameter type {kind} for {name}")
    return params


def tune(model, objective, n_trials=None, seed=0, pruner=None, space=None, tag=""):
    """objective(params, trial) -> valid metric (higher is better); may call trial.report / raise optuna.TrialPruned."""
    cfg = load_config("tuning")[model] if space is None else {"space": space}
    space = cfg["space"]
    n_trials = n_trials or cfg.get("n_trials", N_TRIALS)
    optuna.logging.set_verbosity(optuna.logging.WARNING)
    study = optuna.create_study(direction="maximize", sampler=optuna.samplers.TPESampler(seed=seed),
                                pruner=pruner or optuna.pruners.NopPruner(), study_name=f"{model}{tag}")
    walls = {}

    def wrapped(trial):
        t0 = time.time()
        try:
            return objective(suggest(trial, space), trial)
        finally:
            walls[trial.number] = time.time() - t0

    with Run(f"tune:{model}{tag}", config={"space": space, "n_trials": n_trials, "seed": seed}) as run:
        study.optimize(wrapped, n_trials=n_trials, timeout=cfg.get("timeout_sec"), gc_after_trial=True)
        trials = pd.DataFrame([{"model": model, "trial": t.number, "params": json.dumps(t.params, sort_keys=True),
                                "value": t.value, "state": t.state.name, "wall_sec": walls.get(t.number)} for t in study.trials])
        trials.to_parquet(ml_path("tuning", f"{model}{tag}.parquet"), index=False)
        done = trials[trials["state"] == "COMPLETE"]
        run.metrics.update(best=study.best_value if len(done) else None, median=float(np.median(done["value"])) if len(done) else None,
                           completed=int(len(done)), requested=int(n_trials))
        run.record["params"].update(study.best_params if len(done) else {})
    return study, trials
