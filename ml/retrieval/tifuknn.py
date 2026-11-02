"""ML-10 — R8 TIFU-KNN (Hu et al., SIGIR 2020): time-decayed repeat vector of the member mixed with the mean vector of her k nearest
neighbours, p = α·u + (1 − α)·mean(u_neighbours).

Baskets are the member's purchase days, newest first; basket b (0 = latest) is in group g = b // m at position j = b % m and weighs
r_g^g · r_b^j / m (a closed form of the group-average decay of the paper). Neighbours: cosine over a pool of tifuknn.pool_size members
active in the pool_active_days before the cutoff, with their vectors at the cutoff; the anchor member's own vector uses every
purchase before the anchor. k, r_b, r_g, α are tuned on valid (tuning.yml).
Usage: python ml/retrieval/tifuknn.py --tune | --build"""
import os, sys
import numpy as np, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import CFG, DAY_BITS, DEVICE, Source, day_num, main

SUB = 1024   # queries per similarity block: SUB × pool_size floats on the GPU


def tifu_vectors(row, item, days_before, n, size, m, r_b, r_g):
    """Dense (n, size) TIFU vectors from purchase rows (row, universe item, days before the reference date)."""
    v = torch.zeros(n, size, device=DEVICE)
    if len(row) == 0:
        return v
    key = row.astype(np.int64) * DAY_BITS + days_before
    baskets, inv = np.unique(key, return_inverse=True)   # per row, ascending days_before = newest basket first
    first = np.searchsorted(baskets, (baskets // DAY_BITS) * DAY_BITS)
    b = np.arange(len(baskets)) - first
    w = (r_g ** (b // m)) * (r_b ** (b % m)) / m
    v.index_put_((torch.from_numpy(row).to(DEVICE), torch.from_numpy(item).to(DEVICE)),
                 torch.from_numpy(w[inv].astype(np.float32)).to(DEVICE), accumulate=True)
    return v


class TIFUKNN(Source):
    name = "tifuknn"

    def prepare(self, ev, uni, cutoff):
        c = day_num(cutoff)
        active = np.unique(ev.m[ev.before(cutoff, CFG["tifuknn"]["pool_active_days"])])
        rng = np.random.default_rng(0)
        pool = np.sort(rng.choice(active, min(len(active), CFG["tifuknn"]["pool_size"]), replace=False))
        sel = np.isin(ev.m, pool) & (ev.day < c)
        u = uni.pos[ev.i[sel]]
        keep = u >= 0
        return {"row": np.searchsorted(pool, ev.m[sel][keep]), "item": u[keep], "days_before": (c - ev.day[sel])[keep], "n": len(pool)}

    def fit(self, prep, params, ev, uni, cutoff):
        m = CFG["tifuknn"]["group_size"]
        pool = tifu_vectors(prep["row"], prep["item"], prep["days_before"], prep["n"], uni.size, m, params["r_b"], params["r_g"])
        return {"pool": pool, "pool_n": torch.nn.functional.normalize(pool, dim=1).half(), "params": params, "m": m}

    def scores(self, model, q):
        p = model["params"]
        u = tifu_vectors(q.row, q.item, q.days_before, q.n, model["pool"].shape[1], model["m"], p["r_b"], p["r_g"])
        k = min(int(p["k"]), model["pool"].shape[0])
        out = torch.empty_like(u)
        for s in range(0, q.n, SUB):
            sim = torch.nn.functional.normalize(u[s:s + SUB], dim=1).half() @ model["pool_n"].T
            top_i = torch.topk(sim, k, dim=1).indices
            n = top_i.shape[0]
            w = torch.sparse_coo_tensor(torch.stack([torch.arange(n, device=DEVICE).repeat_interleave(k), top_i.reshape(-1)]),
                                        torch.full((n * k,), 1.0 / k, device=DEVICE), (n, model["pool"].shape[0]),
                                        check_invariants=False)
            out[s:s + SUB] = p["alpha"] * u[s:s + SUB] + (1 - p["alpha"]) * torch.sparse.mm(w, model["pool"])
        return out


if __name__ == "__main__":
    sys.exit(main(TIFUKNN()))
