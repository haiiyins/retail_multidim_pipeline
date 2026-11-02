import datetime as dt
import numpy as np, torch

from ml.retrieval.base import Events, Query, Universe, day_num
from ml.retrieval.neural import OOV, OFFSET, basket_windows, gap_buckets, last_window, months
from ml.retrieval.sasrec import SASRec, SASRecNet, loss_fn as sasrec_loss
from ml.retrieval.two_tower import TwoTower, pick_refs

D0 = day_num(dt.date(2024, 1, 1))
CUT = dt.date(2024, 3, 1)


def events():
    # member 0: items 0, 1, 2, 3 on days 0, 5, 10, 70 (day 70 is after the cutoff), item 0 again on day 12;
    # member 1: items 1 and 4 (4 rare) on day 2, item 0 on day 20
    rows = [(0, 0, 0), (0, 1, 5), (0, 2, 10), (0, 0, 12), (0, 3, 70), (1, 1, 2), (1, 4, 2), (1, 0, 20)]
    m, i, d = (np.array(c) for c in zip(*rows))
    day = D0 + d
    return Events("XX", ["a", "b"], ["m0", "m1", "m2", "m3", "m4"], m, i, day, day.astype(np.int64) * 86_400_000_000,
                  price=np.array([10, 20, 30, 10, 40, 20, 50, 10], np.float32), item_dept=np.array([1, 1, 2, 2, 3]))


def test_last_window():
    row = np.array([0, 0, 0, 2])
    tok = np.array([5, 6, 7, 8])
    seq, lens = last_window(row, tok, 3, 2)
    assert seq.tolist() == [[6, 7], [0, 0], [8, 0]] and lens.tolist() == [2, 0, 1]


def test_basket_windows():
    ev = events()
    uni = Universe(ev, dt.date(2024, 6, 1), size=4, window_days=365)   # item 4 (one buyer, ties broken by index) is OOV
    assert 4 not in uni.items
    row, idx = ev.history(np.array([0, 1]), np.array([D0 + 11, D0 + 30]))
    x, days, lens = basket_windows(ev, uni, row, idx, 2, 2, 2)
    assert lens.tolist() == [2, 2]
    assert (days[0] - D0).tolist() == [5, 10] and (days[1] - D0).tolist() == [2, 20]   # last two baskets, oldest first
    assert x[1, 0].tolist() == [uni.pos[1] + OFFSET, OOV]                                # universe model first, then OOV
    assert x[0, 1].tolist() == [uni.pos[2] + OFFSET, 0]


def test_gap_buckets_and_months():
    days = torch.tensor([[100, 101, 110, 0]])
    assert gap_buckets(days, torch.tensor([3])).tolist() == [[0, 1, 4, 0]]
    assert months(np.array([day_num(dt.date(2024, 1, 31)), day_num(dt.date(2024, 12, 1))])).tolist() == [0, 11]


def test_sasrec_training_is_point_in_time():
    ev = events()
    uni = Universe(ev, dt.date(2024, 6, 1), size=5, window_days=365)
    x, days, lens, c = SASRec().prepare(ev, uni, CUT)
    assert c == day_num(CUT) and len(x) == 2 and lens.tolist() == [4, 2]
    assert uni.pos[3] + OFFSET not in set(x.flatten().tolist())          # bought on day 70, after the cutoff
    # loss only from steps whose window closes before the cutoff: none when the cutoff is right after the last basket
    model = SASRecNet(uni.size, 8, 1, 0.0)
    b = (x.long(), days, lens, int(days.max()) + 1)
    assert float(sasrec_loss(model, b).detach()) == 0.0
    assert float(sasrec_loss(model, (x.long(), days, lens, c)).detach()) > 0


def test_two_tower_examples_are_point_in_time_and_explore_only():
    ev = events()
    uni = Universe(ev, dt.date(2024, 6, 1), size=5, window_days=365)
    tt = TwoTower()
    prep = tt.prepare(ev, uni, CUT)
    c = day_num(CUT)
    assert np.all(prep["t"] + 30 < c)                                     # every label window closes before the cutoff
    seq, lens, r, month, trow, titem, srow, sitem = tt.example(ev, uni, np.array([0]), np.array([D0 + 4]))
    assert lens.tolist() == [1] and seq[0, 0] == uni.pos[0] + OFFSET      # history: only day 0
    assert sorted(uni.items[titem].tolist()) == [1, 2]                   # days 5, 10; not item 0 (repeat on day 12) nor day 70
    assert uni.items[sitem].tolist() == [0] and month.tolist() == [0]
    assert r.shape == (1, 3) and torch.isfinite(r).all()


def test_pick_refs():
    m = np.array([0, 0, 0, 0, 1, 2, 2])
    p = pick_refs(np.random.default_rng(0), m, 2)
    assert np.bincount(m[p]).tolist() == [2, 1, 2] and len(set(p.tolist())) == len(p)


def test_neural_scores_are_finite(monkeypatch):
    import ml.retrieval.sasrec as s, ml.retrieval.two_tower as t
    monkeypatch.setitem(s.C, "epochs", 1)
    monkeypatch.setitem(t.C, "epochs", 1)
    ev = events()
    uni = Universe(ev, dt.date(2024, 6, 1), size=5, window_days=365)
    q = Query(ev, uni, np.array([0, 1, -1]), np.array([D0 + 60, D0 + 60, D0 + 60]))
    for src, params in ((SASRec(), {"d": 16, "blocks": 1, "dropout": 0.0, "lr": 1e-3}),
                        (TwoTower(), {"d": 16, "temperature": 0.1, "lr": 1e-3, "dropout": 0.0})):
        model = src.fit(src.prepare(ev, uni, CUT), params, ev, uni, CUT)
        with torch.no_grad():
            sc = src.scores(model, q)
        assert sc.shape == (3, uni.size) and torch.isfinite(sc).all()
