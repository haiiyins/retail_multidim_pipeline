"""ML-11 — R9 two-tower retrieval: member tower = transformer over the purchase sequence (masked mean) + RFM + calendar month of the
reference day, model tower = model embedding (shared with the input tokens) + sport department + price bucket; cosine / learned
temperature.

Training examples mimic an anchor: a reference day t (the day before one of the member's purchase days, not the first), history =
purchases strictly before t, targets = the universe models first bought in (t, t + Δ] (explore: not bought before t, the only models
an explore-only source can return), with t + Δ < cutoff so every label window closes before the cutoff (pit.last_fit_anchor).
refs_per_epoch reference days per member are resampled every epoch. Loss: softmax over the whole universe with the models already
bought masked out, averaged over the targets — exact at 5 000 models per country, so the in-batch sampled softmax of the plan is
not needed. Price buckets: deciles of the mean unit price before the cutoff over the universe. d, temperature (initial value), lr,
dropout are tuned on valid; the plan's three seeds are built with --seed 1 / 2 --splits test.
Usage: python ml/retrieval/two_tower.py --tune | --build [--seed N --splits test]"""
import math, os, sys
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import CFG, DAY_BITS, DEVICE, Source, explore_targets, item_attributes, main, reference_days
from ml.retrieval.neural import OFFSET, PAD, Encoder, explore_loss, last_window, months, query_window, seed_everything, tokens, train

C = CFG["two_tower"]


def rfm(ev, row, idx, day, n):
    """log1p of purchases, distinct purchase days and days since the latest purchase before the reference day, / 5."""
    cnt = np.bincount(row, minlength=n)
    days = np.unique(row.astype(np.int64) * DAY_BITS + ev.day[idx])
    n_days = np.bincount((days // DAY_BITS).astype(np.int64), minlength=n)
    last = np.full(n, -1, np.int64)
    np.maximum.at(last, row, ev.day[idx])
    since = np.where(last >= 0, day - last, 3650)
    return torch.from_numpy(np.log1p(np.stack([cnt, n_days, since], 1)).astype(np.float32) / 5)


def rows_hot(row, item, n, size):
    """(n, size) bool on DEVICE, True at (row, item)."""
    s = torch.zeros(n, size, dtype=torch.bool, device=DEVICE)
    s[torch.from_numpy(row).to(DEVICE), torch.from_numpy(item).to(DEVICE)] = True
    return s


class TwoTowerNet(nn.Module):
    def __init__(self, size, item_dept, item_price, d, dropout, temperature):
        super().__init__()
        self.enc = Encoder(size + OFFSET, d, C["blocks"], C["heads"], dropout, C["max_len"], causal=False)
        self.rfm = nn.Linear(3, d)
        self.month = nn.Embedding(12, d)
        self.user = nn.Sequential(nn.Linear(3 * d, d), nn.GELU(), nn.Linear(d, d))
        self.dept = nn.Embedding(int(item_dept.max()) + 1, d)
        self.price = nn.Embedding(C["price_buckets"], d)
        self.item = nn.Sequential(nn.Linear(3 * d, d), nn.GELU(), nn.Linear(d, d))
        self.register_buffer("item_dept", torch.as_tensor(item_dept))
        self.register_buffer("item_price", torch.as_tensor(item_price))
        self.log_t = nn.Parameter(torch.tensor(math.log(temperature)))

    def items(self):
        e = self.enc.emb.weight[OFFSET:]
        return F.normalize(self.item(torch.cat([e, self.dept(self.item_dept), self.price(self.item_price)], 1)), dim=1)

    def users(self, x, lens, r, month):
        h = self.enc(x, lens)
        keep = (x != PAD).unsqueeze(-1).to(h.dtype)
        pooled = (h * keep).sum(1) / keep.sum(1).clamp(min=1)
        return F.normalize(self.user(torch.cat([pooled, self.rfm(r), self.month(month)], 1)), dim=1)

    def logits(self, u, v):
        return u @ v.T / self.log_t.clamp(math.log(0.01), 0.0).exp()


def loss_fn(model, b):
    x, lens, r, month, tgt, seen = b
    return explore_loss(model.logits(model.users(x, lens, r, month), model.items()), tgt, seen)


def pick_refs(rng, m, per_member):
    """Indices of up to per_member random reference days per member, shuffled."""
    perm = rng.permutation(len(m))
    order = perm[np.argsort(m[perm], kind="stable")]
    sm = m[order]
    rank = np.arange(len(sm)) - np.searchsorted(sm, sm)
    return rng.permutation(order[rank < per_member])


class TwoTower(Source):
    name = "two_tower"

    def prepare(self, ev, uni, cutoff):
        m, t = reference_days(ev, cutoff)
        dept, price, _ = item_attributes(ev, uni, cutoff, C["price_buckets"])
        return {"m": m, "t": t, "dept": dept, "price": price}

    def example(self, ev, uni, m, t):
        """Inputs and explore targets of reference days t of members m: seq, lens, rfm, month, (row, item) of the targets and of
        the universe models bought before t."""
        row, idx = ev.history(m, t)
        seq, lens = last_window(row, tokens(ev, uni, idx), len(m), C["max_len"])
        hu = uni.pos[ev.i[idx]]
        hk = hu >= 0
        srow, sitem = row[hk], hu[hk]
        trow, titem = explore_targets(ev, uni, m, t, srow, sitem)
        return seq, lens, rfm(ev, row, idx, t, len(m)), months(t), trow, titem, srow, sitem

    def fit(self, prep, params, ev, uni, cutoff):
        rng = seed_everything(self.seed)
        model = TwoTowerNet(uni.size, prep["dept"], prep["price"], params["d"], params["dropout"], params["temperature"]).to(DEVICE)
        bs = C["batch"]

        def batches(ep):
            pick = pick_refs(rng, prep["m"], C["refs_per_epoch"])
            for s in range(0, len(pick), bs):
                i = pick[s:s + bs]
                seq, lens, r, month, trow, titem, srow, sitem = self.example(ev, uni, prep["m"][i], prep["t"][i])
                has = torch.from_numpy((np.bincount(trow, minlength=len(i)) > 0) & (lens > 0)).to(DEVICE)
                tgt = rows_hot(trow, titem, len(i), uni.size)
                yield (torch.from_numpy(seq).to(DEVICE)[has], torch.from_numpy(np.maximum(lens, 1)).to(DEVICE)[has],
                       r.to(DEVICE)[has], torch.from_numpy(month).to(DEVICE)[has], tgt[has],
                       rows_hot(srow, sitem, len(i), uni.size)[has])

        return train(model, batches, loss_fn, C["epochs"], params["lr"], log=f"two_tower {ev.country} {str(cutoff)[:10]}")

    def scores(self, model, q):
        seq, lens = query_window(q.ev, q.uni, q, C["max_len"])
        r = rfm(q.ev, q.all_row, q.all_idx, q.day, q.n)
        with torch.autocast("cuda", dtype=torch.bfloat16, enabled=DEVICE == "cuda"):
            u = model.users(torch.from_numpy(seq).to(DEVICE), torch.from_numpy(lens).to(DEVICE), r.to(DEVICE),
                            torch.from_numpy(months(q.day)).to(DEVICE))
            return model.logits(u, model.items()).float()


if __name__ == "__main__":
    sys.exit(main(TwoTower()))
