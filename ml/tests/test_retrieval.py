import datetime as dt
import numpy as np, torch

from ml.retrieval.base import Events, Query, Universe, day_num, explore_targets, mask_scores, reference_days
from ml.retrieval.rp3beta import rp3_weights
from ml.retrieval.trend import Trend
import scipy.sparse as sp
from ml.retrieval.ease import ease_weights
from ml.retrieval.tifuknn import tifu_vectors

D0 = day_num(dt.date(2024, 1, 1))


def toy_events(extra=()):
    # (member, item, day offset): member 0 buys items 0, 1, 2; member 1 buys item 0 twice; item 3 is bought once, long ago
    rows = [(0, 0, 10), (0, 1, 12), (0, 2, 15), (1, 0, 3), (1, 0, 11), (1, 3, -400)] + list(extra)
    m, i, d = (np.array(c) for c in zip(*rows))
    return Events("XX", ["a", "b"], ["m0", "m1", "m2", "m3"], m, i, D0 + d, (D0 + d).astype(np.int64) * 86_400_000_000 + 3_600_000_000,
                  price=10.0 + 10 * i, item_dept=np.array([1, 1, 2, 3]))


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


def test_explore_only_mask():
    ev = toy_events()
    uni = Universe(ev, dt.date(2024, 1, 20), size=4, window_days=365)
    q = Query(ev, uni, np.array([0, 1, -1]), np.array([D0 + 15, D0 + 16, D0 + 16]))
    sc = mask_scores(torch.zeros(3, uni.size), q, explore_only=True)
    allowed = lambda r: sorted(ev.items[uni.items[torch.isfinite(sc[r]).numpy()]].tolist())
    assert ev.items[uni.items].tolist() == ["m0", "m1", "m2"]   # m3 is outside the window
    assert allowed(0) == ["m2"]                # m0, m1 bought before the anchor; m2 only on the anchor day
    assert allowed(1) == ["m1", "m2"]          # m0 bought before
    assert allowed(2) == []                    # no history
    keep = mask_scores(torch.zeros(3, uni.size), q, explore_only=False)
    assert torch.isfinite(keep[0]).all() and not torch.isfinite(keep[2]).any()


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


def test_reference_days_and_explore_targets():
    ev = toy_events()
    m, t = reference_days(ev, dt.date(2024, 3, 1))                  # cutoff D0 + 60: windows (t, t + 30] close before it
    assert sorted(zip(m.tolist(), (t - D0).tolist())) == [(0, 11), (0, 14), (1, 2), (1, 10)]
    uni = Universe(ev, dt.date(2024, 1, 20), size=3, window_days=365)
    hist = ev.history(np.array([1]), np.array([D0 + 4]))[1]           # member 1 before day 4: items 3 (outside), 0
    hu = uni.pos[ev.i[hist]]
    row, item = explore_targets(ev, uni, np.array([1]), np.array([D0 + 4]), np.zeros((hu >= 0).sum(), np.int64), hu[hu >= 0])
    assert len(row) == 0                                             # item 0 again on day 11 is a repeat
    row, item = explore_targets(ev, uni, np.array([0]), np.array([D0 + 10]), np.array([0]), np.array([uni.pos[0]]))
    assert sorted(uni.items[item].tolist()) == [1, 2]


def test_rp3_weights():
    x = sp.csr_matrix(np.array([[1, 1, 0], [1, 0, 1], [1, 1, 1]], np.float64))
    w = rp3_weights(x, alpha=1.0, beta=0.5)
    xd = x.toarray()
    du, di = xd.sum(1), xd.sum(0)
    ref = (xd / di).T @ (xd / du[:, None]) / di[None, :] ** 0.5
    np.fill_diagonal(ref, 0)
    assert np.allclose(w, ref)


def test_trend_reads_only_before_the_anchor():
    a = toy_events()
    b = toy_events(extra=[(1, 2, 20), (1, 2, 25), (0, 1, 21)])       # purchases on and after the anchor day 20
    uni = Universe(a, dt.date(2024, 1, 20), size=3, window_days=365)
    params = {"window_days": 14, "w_dept": 1.0, "w_price": 0.5}
    m, day = np.array([0, 1]), np.array([D0 + 20, D0 + 20])
    sa, sb = (Trend().scores(Trend().fit(Trend().prepare(e, uni, dt.date(2024, 1, 20)), params, e, uni, None), Query(e, uni, m, day))
              for e in (a, b))
    assert torch.allclose(sa, sb) and torch.isfinite(sa).all()
