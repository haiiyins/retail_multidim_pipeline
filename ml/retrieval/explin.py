"""R11 supervised explore linear model: an EASE-like closed form fitted on the target of the candidate list instead of on the history.

W = (XᵀX + λI)⁻¹ XᵀY per country × cutoff, where a row is a training reference day t of a member (base.reference_days: the label
window closes before the cutoff), X = her universe purchases before t weighted by 0.5^(days_before / half_life_days) (latest purchase
of each model), Y = the universe models first bought in (t, t + Δ] (explore targets). Up to refs_per_member random reference days per
member (seed 0), at most max_examples rows. At the anchor s = x W with x built the same way. λ and half_life_days are tuned on valid.
Usage: python ml/retrieval/explin.py --tune | --build"""
import os, sys
import numpy as np, scipy.sparse as sp, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import CFG, DEVICE, Source, explore_targets, main, reference_days

C = CFG["explin"]


def latest(row, item, days_before):
    """One entry per (row, item): the smallest days_before."""
    key = row.astype(np.int64) * (1 << 20) + item
    order = np.lexsort((days_before, key))
    key, days_before = key[order], days_before[order]
    first = np.r_[True, key[1:] != key[:-1]]
    return (key[first] >> 20).astype(np.int64), (key[first] & ((1 << 20) - 1)).astype(np.int64), days_before[first]


class ExploreLinear(Source):
    name = "explin"

    def prepare(self, ev, uni, cutoff):
        m, t = reference_days(ev, cutoff)
        rng = np.random.default_rng(0)
        perm = rng.permutation(len(m))
        order = perm[np.argsort(m[perm], kind="stable")]
        rank = np.arange(len(order)) - np.searchsorted(m[order], m[order])
        pick = order[rank < C["refs_per_member"]]
        pick = np.sort(rng.choice(pick, min(len(pick), C["max_examples"]), replace=False))
        m, t = m[pick], t[pick]
        row, idx = ev.history(m, t)
        u = uni.pos[ev.i[idx]]
        k = u >= 0
        xr, xi, xd = latest(row[k], u[k], (t[row] - ev.day[idx])[k])
        yr, yi = explore_targets(ev, uni, m, t, xr, xi)
        y = sp.csr_matrix((np.ones(len(yr), np.float32), (yr, yi)), shape=(len(m), uni.size))
        return {"xr": xr, "xi": xi, "xd": xd.astype(np.float32), "y": y, "n": len(m), "size": uni.size}

    def fit(self, prep, params, ev, uni, cutoff):
        w = 0.5 ** (prep["xd"] / params["half_life_days"])
        x = sp.csr_matrix((w, (prep["xr"], prep["xi"])), shape=(prep["n"], prep["size"]))
        g = torch.as_tensor((x.T @ x).toarray(), dtype=torch.float64, device=DEVICE)
        r = torch.as_tensor((x.T @ prep["y"]).toarray(), dtype=torch.float64, device=DEVICE)
        g.diagonal().add_(params["l2"])
        return {"w": torch.linalg.solve(g, r).float(), "half_life": params["half_life_days"]}

    def scores(self, model, q):
        r, i, d = latest(q.row, q.item, q.days_before)
        x = torch.zeros(q.n, model["w"].shape[0], device=DEVICE)
        x[torch.from_numpy(r).to(DEVICE), torch.from_numpy(i).to(DEVICE)] = \
            torch.from_numpy((0.5 ** (d / model["half_life"])).astype(np.float32)).to(DEVICE)
        return x @ model["w"]


if __name__ == "__main__":
    sys.exit(main(ExploreLinear()))
