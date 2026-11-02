import datetime as dt
import os, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from recommend import Reference, recommend, validate

ASOF = dt.date(2026, 7, 28)


def ref():
    models = pd.DataFrame({"model_id": ["a", "b", "c", "d", "e"], "department": ["D1", "D1", "D2", "D1", "D2"],
                           "price_band": [1, 2, 3, 4, 5], "popularity": [40.0, 80.0, 20.0, 100.0, 0.0],
                           "trend": [1.0, 2.0, 0.5, 2.5, 1.0]})
    nb = pd.DataFrame({"model_id": ["a", "a", "b"], "neighbour_id": ["c", "b", "e"], "weight": [0.5, 0.2, 0.4]})
    return {"TH": Reference(models, nb, ASOF)}


def test_sources_reasons_and_explore_only():
    df, bad = validate(pd.DataFrame({"member_id": ["u", "u", "u"], "country_code": "TH", "model_id": ["a", "a", "x"],
                                     "purchase_date": ["2026-07-01", "2026-05-01", "not a date"]}))
    assert bad == 1
    out = recommend(df, ref(), k=5)
    assert out["rank"].tolist() == list(range(1, len(out) + 1))
    assert out.loc[out["model_id"] == "a", "source"].item() == "repeat"
    assert not ((out["model_id"] == "a") & (out["source"] != "repeat")).any()   # explore sources skip bought models
    assert out["reason"].str.len().gt(0).all()
    assert {"co_purchase", "trend"} <= set(out["source"])


def test_purchases_after_asof_ignored_and_unknown_country_skipped():
    df, _ = validate(pd.DataFrame({"member_id": ["u", "v"], "country_code": ["TH", "SG"], "model_id": ["a", "a"],
                                   "purchase_date": ["2026-08-15", "2026-07-01"]}))
    out = recommend(df, ref(), k=5)
    assert set(out["member_id"]) == {"u"}
    assert "repeat" not in set(out["source"])


def test_due_window_and_profiles():
    from recommend import profiles
    df, _ = validate(pd.DataFrame({"member_id": "u", "country_code": "TH", "model_id": ["a", "a", "b", "b"],
                                   "purchase_date": ["2026-03-30", "2026-05-29", "2025-03-19", "2025-06-27"]}))
    out = recommend(df, ref(), k=5).set_index("model_id")
    assert out.loc["a", "cycle"] == 60 and out.loc["a", "due"]          # last 60 days ago, cycle 60: due
    assert out.loc["b", "cycle"] == 100 and not out.loc["b", "due"]     # last 396 days ago, cycle 100: lapsed
    assert not out.loc[out["source"] != "repeat", "due"].fillna(False).astype(bool).any()
    p = profiles(df, ref()).iloc[0]
    assert p["segment"] == "mid" and p["models"] == 2 and p["last_days"] == 60
