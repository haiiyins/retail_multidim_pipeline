import math
import numpy as np, torch

from ml.retrieval import rex
from ml.retrieval.base import DAY_BITS, EPOCH, Events, Universe, day_num

T = day_num("2025-06-15")


def toy_events():
    """Member 0 buys model A on T − 40, T − 10, T (anchor day) and T + 5; B on T − 3; member 1 buys B on T − 1 and C on T + 40."""
    rows = [(0, 0, T - 40), (0, 0, T - 10), (0, 0, T), (0, 0, T + 5), (0, 1, T - 3), (1, 1, T - 1), (1, 2, T + 40)]
    m, i, d = (np.array(c) for c in zip(*rows))
    return Events("TH", ["m0", "m1"], ["A", "B", "C"], m, i, d, d * 86_400_000_000, price=np.ones(len(m)), item_dept=np.array([1, 1, 2]))


def toy_web(ev):
    """Member 0 views B on T − 5 and T − 40 (outside the window), adds C to the cart on T (the anchor day: not yet known)."""
    w = rex.WebEvents.__new__(rex.WebEvents)
    w.m, w.i, w.day = np.array([0, 0, 0]), np.array([1, 1, 2]), np.array([T - 40, T - 5, T])
    w.views, w.carts = np.array([1.0, 2.0, 0.0], np.float32), np.array([0.0, 0.0, 1.0], np.float32)
    w.key = w.m * DAY_BITS + w.day
    return w


def universe(ev):
    return Universe(ev, EPOCH.fromordinal(EPOCH.toordinal() + T + 100), size=10, window_days=1000)


def test_batch_reads_only_what_is_known_before_the_anchor():
    ev = toy_events()
    uni = universe(ev)
    stats = np.zeros((uni.size, 2), np.float32)
    b = rex.Batch(ev, toy_web(ev), uni, stats, np.array([0, 1]), np.array([T, T]))
    pairs = {(int(r), ev.items[uni.items[it]]): phi for r, it, phi in zip(b.rep_row, b.rep_item, b.phi)}
    assert set(pairs) == {(0, "A"), (0, "B"), (1, "B")}             # A on T and T + 5, C on T + 40 are not history
    assert math.isclose(pairs[(0, "A")][0], math.log1p(2), rel_tol=1e-6)
    assert math.isclose(pairs[(0, "A")][1], math.log1p(10) / 5, rel_tol=1e-6)
    web = {(int(r), ev.items[uni.items[it]]) for r, it in zip(b.web_row, b.web_item)}
    assert web == {(0, "B")}                                          # T − 40 outside the window, the cart of day T not known
    assert b.psi[0, 0] == np.float32(math.log1p(2)) and b.psi[0, 4] == 1.0


def test_popularity_counts_days_before_the_anchor_only():
    ev = toy_events()
    uni = universe(ev)
    cum, day0 = rex.daily_buyers(ev, uni)
    f = rex.pop_features(cum, day0, np.array([T]))
    b7 = {ev.items[uni.items[j]]: math.expm1(float(f[0, j, 0]) * 5) for j in range(uni.size)}
    assert round(b7["B"]) == 2 and round(b7["A"]) == 0 and round(b7["C"]) == 0   # A of day T is not counted


def test_targets_and_reference_windows():
    ev = toy_events()
    uni = universe(ev)
    row, item = rex.targets(ev, uni, np.array([0, 1]), np.array([T, T]))
    assert sorted((int(r), ev.items[uni.items[i]]) for r, i in zip(row, item)) == [(0, "A")]   # (T, T + 30]: not T, not T + 40
    cutoff = EPOCH.fromordinal(EPOCH.toordinal() + T + 20)
    bm, bd, fd = rex.basket_days(ev, cutoff)
    lo, hi = np.maximum(bd - rex.DELTA, fd + 1), np.minimum(bd - 1, day_num(cutoff) - rex.DELTA - 1)
    ok = lo <= hi
    assert (hi[ok] + rex.DELTA < day_num(cutoff)).all() and (lo[ok] > fd[ok]).all()
    assert ((bd[ok] > hi[ok]) & (bd[ok] <= lo[ok] + rex.DELTA)).all()   # the window of every t holds the purchase it came from


def toy_price_inputs(uni, t):
    """Price table from T − 5: every model at log price 1 until T − 1, model 0 drops to log price 0 on day T."""
    day0 = T - 5
    lp = np.ones((10, uni.size), np.float32)
    lp[5:, 0] = 0.0
    f = np.stack([np.ones_like(lp), lp, np.zeros_like(lp), np.zeros_like(lp), np.zeros_like(lp)], 2)
    return rex.price_features(torch.from_numpy(f).to(rex.DEVICE), torch.from_numpy(lp).to(rex.DEVICE), day0, t)


def test_price_is_read_on_the_day_before_the_anchor():
    ev = toy_events()
    uni = universe(ev)
    p = toy_price_inputs(uni, np.array([T, T + 1, T - 5]))
    assert float(p["lp"][0, 0]) == 1.0     # the drop of day T is not known at anchor T
    assert float(p["lp"][1, 0]) == 0.0     # it is at T + 1
    assert torch.isnan(p["lp"][2]).all() and float(p["f"][2].abs().sum()) == 0.0   # before the table: no price


def test_forward_and_loss_of_every_variant():
    ev = toy_events()
    uni = universe(ev)
    b = rex.Batch(ev, toy_web(ev), uni, np.zeros((uni.size, 2), np.float32), np.array([0, 1]), np.array([T, T - 2]))
    cum, day0 = rex.daily_buyers(ev, uni)
    pop = rex.pop_features(cum.to(rex.DEVICE), day0, b.t_uni)
    price = toy_price_inputs(uni, b.t_uni)
    for base, variant in [(base, v) for base in ("rex", "rex2") for v in rex.REX.VARIANTS]:
        drop = rex.REX(variant, base).drop
        torch.manual_seed(0)
        net = rex.REXNet(uni.size, np.zeros(uni.size, np.int64), np.zeros(uni.size, np.int64), 16, 1, 0.0, drop,
                         np.zeros(uni.size, np.float32)).to(rex.DEVICE)
        logits = net(b.tensors(), pop, price)
        assert logits.shape == (2, uni.size) and logits.dtype == torch.float32, variant
        tgt = torch.zeros_like(logits, dtype=torch.bool)
        tgt[0, 0] = True
        tgt[1, 1] = True
        loss = rex.full_target_loss(logits, tgt)
        assert math.isfinite(loss.item()), variant
        loss.backward()
