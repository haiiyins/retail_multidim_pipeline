import datetime as dt
import numpy as np, torch

from ml.retrieval.base import Events, Query, Universe, day_num
from ml.retrieval.ease import ease_weights
from ml.retrieval.tifuknn import tifu_vectors

D0 = day_num(dt.date(2024, 1, 1))


def toy_events(extra=()):
    # (member, item, day offset): member 0 buys items 0, 1, 2; member 1 buys item 0 twice; item 3 is bought once, long ago
    rows = [(0, 0, 10), (0, 1, 12), (0, 2, 15), (1, 0, 3), (1, 0, 11), (1, 3, -400)] + list(extra)
    m, i, d = (np.array(c) for c in zip(*rows))
    return Events("XX", ["a", "b"], ["m0", "m1", "m2", "m3"], m, i, D0 + d, (D0 + d).astype(np.int64) * 86_400_000_000 + 3_600_000_000)


def test_history_strictly_before_anchor():
    ev = toy_events()
    row, idx = ev.history(np.array([0, 1, -1]), np.array([D0 + 15, D0 + 11, D0 + 15]))
    assert sorted(ev.i[idx[row == 0]].tolist()) == [0, 1]   # the anchor-day purchase is excluded
    assert ev.day[idx[row == 1]].tolist() == [D0 - 400, D0 + 3]
    assert (row == 2).sum() == 0                            # unknown member


def test_universe_and_query():
    ev = toy_events()
    uni = Universe(ev, dt.date(2024, 1, 20), size=2, window_days=365)
    assert ev.items[uni.items].tolist() == ["m0", "m1"]     # m0 has two buyers; m3 is outside the window
    q = Query(ev, uni, np.array([0, 1]), np.array([D0 + 16, D0 + 16]))
    assert sorted(uni.items[q.item[q.row == 0]].tolist()) == [0, 1]   # m2 is outside the universe
    assert q.source_ts_max[0] == (D0 + 15) * 86_400_000_000 + 3_600_000_000   # but still counts as read
    assert q.has_history.tolist() == [True, True]


def test_future_purchases_do_not_change_the_query():
    a, b = toy_events(), toy_events(extra=[(0, 3, 15), (0, 3, 30), (1, 1, 11)])
    uni = Universe(a, dt.date(2024, 1, 20), size=4, window_days=365)
    m, day = np.array([0, 1]), np.array([D0 + 15, D0 + 11])
    qa, qb = Query(a, uni, m, day), Query(b, uni, m, day)
    assert np.array_equal(qa.row, qb.row) and np.array_equal(qa.item, qb.item) and np.array_equal(qa.source_ts_max, qb.source_ts_max)


def test_ease_closed_form():
    x = np.array([[1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]], np.float64)
    g = x.T @ x
    b = ease_weights(g, 0.5).cpu().numpy()
    p = np.linalg.inv(g + 0.5 * np.eye(3))
    ref = -p / np.diag(p)[None, :]
    np.fill_diagonal(ref, 0)
    assert np.allclose(b, ref, atol=1e-5) and np.all(np.diag(b) == 0)


def test_tifu_decay():
    # one member, three baskets (days before 1, 5, 9), item 0 in all, item 1 only in the oldest
    row, item, days = np.array([0, 0, 0, 0]), np.array([0, 0, 0, 1]), np.array([1, 5, 9, 9])
    v = tifu_vectors(row, item, days, 1, 2, m=2, r_b=0.5, r_g=0.25).cpu().numpy()
    # basket ranks 0, 1 (group 0) and 2 (group 1): weights 1/2, 0.5/2, 0.25/2
    assert np.allclose(v[0], [0.5 + 0.25 + 0.125, 0.125])
