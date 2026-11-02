"""Point-in-time rules for model-generated tables (plan D7–D9).

Rolling protocol: a signal model or a learned candidate source is fitted at a cutoff c on events dated strictly before c and on
label windows that close strictly before c. A train anchor t uses the latest cutoff c ≤ t (anchors before the first cutoff get no
model: NULL features / no candidates); valid and test anchors use the model fitted at FINAL_CUTOFF = train_hi + 1 day.
Every ml.* table produced by a model carries fit_cutoff, source_ts_max and model_version; assert_pit() checks them."""
import datetime as dt
from ml.common.data import split_windows

FIRST_CUTOFF = dt.date(2023, 7, 1)   # six months of history before the first fit


class PITViolation(AssertionError):
    pass


def _quarter_starts(lo, hi):
    d = dt.date(lo.year, ((lo.month - 1) // 3) * 3 + 1, 1)
    if d < lo:
        d = dt.date(d.year + (d.month + 2) // 12, (d.month + 2) % 12 + 1, 1)
    while d <= hi:
        yield d
        d = dt.date(d.year + (d.month + 2) // 12, (d.month + 2) % 12 + 1, 1)


def cutoffs():
    """Quarterly rolling cutoffs inside the training window: 2023-07-01 … 2025-07-01 (9 cutoffs)."""
    return list(_quarter_starts(FIRST_CUTOFF, split_windows()["train_hi"]))


def final_cutoff():
    return split_windows()["train_hi"] + dt.timedelta(days=1)


def all_cutoffs():
    return cutoffs() + [final_cutoff()]


def cutoff_for(anchor, split):
    """Cutoff of the model an anchor may use, or None for train anchors before FIRST_CUTOFF."""
    if split in ("valid", "test"):
        return final_cutoff()
    past = [c for c in cutoffs() if c <= anchor]
    return past[-1] if past else None


def last_fit_anchor(cutoff, delta):
    """Latest anchor whose label window (t, t + Δ] closes strictly before the cutoff."""
    return cutoff - dt.timedelta(days=delta + 1)


def cutoff_case_sql(anchor_col="anchor_date", split_col="split"):
    """SQL expression giving cutoff_for() per row, to join model outputs by fit_cutoff."""
    whens = " ".join(f"WHEN {anchor_col} >= DATE '{c}' THEN DATE '{c}'" for c in reversed(cutoffs()))
    return (f"CASE WHEN {split_col} IN ('valid', 'test') THEN DATE '{final_cutoff()}' {whens} ELSE NULL END")


def assert_pit(con, relation, anchor_col="anchor_date", require=("source_ts_max",)):
    """Raise PITViolation if a row of the relation uses information from on or after its anchor date:
    fit_cutoff > anchor (a model fitted later than the anchor) or source_ts_max ≥ anchor (an input dated on the anchor or later).
    Columns in `require` must exist; fit_cutoff and model_version are checked when present."""
    cols = {r[0] for r in con.execute(f"DESCRIBE SELECT * FROM {relation}").fetchall()}
    missing = [c for c in require if c not in cols]
    if missing:
        raise PITViolation(f"{relation}: missing point-in-time columns {missing}")
    checks = {"source_ts_max >= anchor": f"source_ts_max >= CAST({anchor_col} AS TIMESTAMP)"} if "source_ts_max" in cols else {}
    if "fit_cutoff" in cols:
        checks["fit_cutoff > anchor"] = f"fit_cutoff > CAST({anchor_col} AS DATE)"
    if "model_version" in cols:
        checks["model_version is null"] = "model_version IS NULL"
    sel = ", ".join(f"COUNT(*) FILTER (WHERE {cond})" for cond in checks.values())
    counts = dict(zip(checks, con.execute(f"SELECT {sel} FROM {relation}").fetchall()[0])) if checks else {}
    bad = {k: v for k, v in counts.items() if v}
    if bad:
        raise PITViolation(f"{relation}: {bad}")
    return counts
