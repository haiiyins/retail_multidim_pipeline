import datetime as dt
import pandas as pd, pytest
from ml.common.data import connect, split_windows
from ml.common.pit import PITViolation, assert_pit, cutoff_case_sql, cutoff_for, cutoffs, final_cutoff, last_fit_anchor

D = dt.date


def test_cutoffs_are_quarterly_through_test():
    cs = cutoffs()
    assert cs[0] == D(2023, 7, 1) and cs[-1] == D(2026, 7, 1) and cs[-1] <= split_windows()["test_hi"]
    assert len(cs) == 13 and all(c.day == 1 and c.month in (1, 4, 7, 10) for c in cs)
    assert final_cutoff() == split_windows()["train_hi"] + dt.timedelta(days=1)


def test_cutoff_for():
    assert cutoff_for(D(2023, 6, 26)) is None
    assert cutoff_for(D(2023, 7, 3)) == D(2023, 7, 1)
    assert cutoff_for(D(2024, 12, 30)) == D(2024, 10, 1)
    assert cutoff_for(D(2025, 10, 27)) == D(2025, 10, 1)      # valid: refitted after the train window
    assert cutoff_for(D(2026, 2, 2)) == D(2026, 1, 1) and cutoff_for(D(2026, 7, 27)) == D(2026, 7, 1)
    assert last_fit_anchor(D(2024, 10, 1), 30) == D(2024, 8, 31)


def test_cutoff_case_sql_matches_python():
    con = connect(read_lakehouse=False)
    rows = [D(2023, 6, 26), D(2023, 7, 3), D(2025, 9, 15), D(2025, 12, 22), D(2026, 2, 2), D(2026, 7, 27)]
    con.register("a", pd.DataFrame({"anchor_date": rows}))
    got = [r[0] for r in con.execute(f"SELECT {cutoff_case_sql()} FROM a").fetchall()]
    assert got == [cutoff_for(t) for t in rows]


def test_assert_pit():
    con = connect(read_lakehouse=False)
    ok = pd.DataFrame({"anchor_date": [D(2024, 1, 8)], "source_ts_max": [pd.Timestamp("2024-01-07 23:59")],
                       "fit_cutoff": [D(2024, 1, 1)], "model_version": ["v1"]})
    con.register("ok", ok)
    assert assert_pit(con, "ok") == {"source_ts_max >= anchor": 0, "fit_cutoff > anchor": 0, "model_version is null": 0}
    con.register("late_input", ok.assign(source_ts_max=pd.Timestamp("2024-01-08 00:00")))
    with pytest.raises(PITViolation, match="source_ts_max"):
        assert_pit(con, "late_input")
    con.register("late_model", ok.assign(fit_cutoff=D(2024, 4, 1)))
    with pytest.raises(PITViolation, match="fit_cutoff"):
        assert_pit(con, "late_model")
    con.register("no_ts", ok.drop(columns=["source_ts_max"]))
    with pytest.raises(PITViolation, match="missing"):
        assert_pit(con, "no_ts")
