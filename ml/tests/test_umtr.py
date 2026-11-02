import math
import torch

from ml.umtr.model import UMTR, loss_fn
from ml.umtr.train import VARIANTS


def toy_batch(a=4, k=6, f=5, n_models=20, n_dept=3, length=7):
    g = torch.Generator().manual_seed(0)
    seq = torch.randint(1, n_models, (a, length), generator=g)
    seq[0] = 0                                   # member without history
    seq[1, 3:] = 0
    rep = torch.zeros(a, k, dtype=torch.bool)
    rep[1, :2] = True
    rep[2, :] = True                             # repeat candidates only
    mask = torch.ones(a, k, dtype=torch.bool)
    mask[3, 4:] = False
    y30 = torch.zeros(a, k, dtype=torch.bool)
    y30[:, 0] = True
    return {"x": torch.randn(a, k, f, generator=g), "model": torch.randint(1, n_models, (a, k), generator=g),
            "dept": torch.randint(0, n_dept, (a, k), generator=g), "rep": rep, "y30": y30, "y90": y30.clone(), "mask": mask,
            "seq": seq, "gap": torch.randint(0, 17, (a, length), generator=g) * (seq > 0), "rho": torch.tensor([0.0, 0.5, 1.0, 0.2]),
            "gate_y": torch.tensor([float("nan"), 1.0, 1.0, 0.0])}


def test_variants_give_distributions_over_valid_candidates():
    b = toy_batch()
    for variant, kw in VARIANTS.items():
        torch.manual_seed(0)
        m = UMTR(5, 20, 3, 16, 0.0, heads=2, blocks=1, max_len=7, **kw).eval()
        lp = m(b)["logp"]
        p = lp.exp() * b["mask"]
        assert torch.allclose(p.sum(1), torch.ones(4), atol=1e-4), variant
        assert (lp[~b["mask"]] < -1e3).all(), variant
        loss = loss_fn(m.train(), b, 0.3, 0.5)
        assert math.isfinite(loss.item()), variant
        loss.backward()


def test_fixed_gate_splits_mass_by_repeat_share():
    b = toy_batch()
    m = UMTR(5, 20, 3, 16, 0.0, heads=2, blocks=1, max_len=7, gate="fixed").eval()
    p = m(b)["logp"].exp()
    assert abs(p[1][b["rep"][1]].sum().item() - 0.5) < 1e-4
    assert abs(p[2].sum().item() - 1.0) < 1e-4        # no explore candidates: all mass on repeat
