import pandas as pd
import ml.common.data as data
from ml.common.tuning import tune

SPACE = {"x": {"type": "float", "low": -3.0, "high": 3.0}, "k": {"type": "int", "low": 1, "high": 4},
         "c": {"type": "categorical", "choices": ["a", "b"]}, "f": {"type": "fixed", "value": 7}}


def test_tune_records_every_trial(tmp_path, monkeypatch):
    monkeypatch.setattr(data, "ML_DIR", str(tmp_path))
    seen = []

    def objective(params, trial):
        seen.append(params)
        return -(params["x"] - 1) ** 2 + params["k"] + (params["c"] == "b")

    study, trials = tune("toy", objective, n_trials=5, space=SPACE, tag="_test")
    assert len(trials) == 5 and (trials["state"] == "COMPLETE").all()
    assert all(p["f"] == 7 and -3 <= p["x"] <= 3 for p in seen)
    assert pd.read_parquet(tmp_path / "tuning" / "toy_test.parquet")["trial"].tolist() == [0, 1, 2, 3, 4]
    reg = pd.read_json(tmp_path / "registry" / "runs.jsonl", lines=True)
    assert reg.iloc[-1]["model"] == "tune:toy_test" and reg.iloc[-1]["metrics"]["completed"] == 5
    # same seed → same proposals: the budget is reproducible
    _, again = tune("toy", objective, n_trials=5, space=SPACE, tag="_test2")
    assert again["params"].tolist() == trials["params"].tolist()
