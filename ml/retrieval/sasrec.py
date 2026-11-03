"""ML-12 — R10 SASRec-retrieval: a causal transformer (Kang & McAuley, ICDM 2018) over the member's baskets, trained with a dense
all-action loss (PinnerFormer, Pancha et al., KDD 2022) on the explore target of the candidate list.

One step per basket (purchase day): input = mean embedding of the basket's models (tied with the output) + a log2 bucket of the days
since the previous basket; the order of the models inside a day carries no meaning and is not modelled. Every step j predicts all the
universe models first bought in (d_j, d_j + Δ] (explore: not in the baskets up to j), softmax over the universe with the models
already bought masked out, averaged over the targets. Only steps whose window closes before the cutoff carry loss, so inputs and
targets are both point-in-time. Fit per country × cutoff on the last max_len baskets before the cutoff of every member with two or
more; at the anchor the state of the latest basket scores the universe. d, blocks, dropout, lr are tuned on valid (tuning.yml).
SASRecAll is the same network trained on every model of the window (repeats included), the full-target SASRec NBR baseline of t31.
Usage: python ml/retrieval/sasrec.py --tune | --build [--seed N --splits test]"""
import os, sys
import numpy as np, torch, torch.nn as nn

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import CFG, DEVICE, Source, day_num, main
from ml.retrieval.neural import (GAP_BUCKETS, OFFSET, OOV, PAD, Encoder, basket_windows, explore_loss, gap_buckets,
                                 seed_everything, train)

C = CFG["sasrec"]
SCORE_CHUNK = 1024


class SASRecNet(nn.Module):
    def __init__(self, size, d, blocks, dropout):
        super().__init__()
        self.size = size
        self.enc = Encoder(size + OFFSET, d, blocks, C["heads"], dropout, C["max_len"], causal=True)
        self.gap = nn.Embedding(GAP_BUCKETS, d)
        nn.init.normal_(self.gap.weight, std=0.02)

    def states(self, x, days, lens):
        e = self.enc.emb(x)
        inp = e.sum(2) / (x != PAD).sum(2, keepdim=True).clamp(min=1)
        return self.enc(None, lens, inp + self.gap(gap_buckets(days, lens)))

    def logits(self, h):
        return h @ self.enc.emb.weight[OFFSET:].T


def multi_hot(x, size):
    return torch.zeros(*x.shape[:2], size + OFFSET, dtype=torch.bool, device=x.device).scatter_(2, x, True)[..., OFFSET:]


def loss_fn(model, b, explore=True):
    x, days, lens, c = b
    h = model.states(x, days, lens)
    basket = multi_hot(x, model.size)                                   # (n, L, V)
    seen = basket.to(torch.int16).cumsum(1) > 0                          # bought in the baskets up to j
    steps = torch.arange(x.shape[1], device=x.device)
    valid = steps[None] < lens[:, None]
    later = (steps[None, :] > steps[:, None])[None] & valid[:, None, :] & \
            (days[:, None, :] <= days[:, :, None] + CFG["delta"])        # (n, j, k): basket k is in the window of step j
    target = torch.bmm(later.to(torch.bfloat16), basket.to(torch.bfloat16)) > 0
    if explore:
        target &= ~seen
    else:
        seen = torch.zeros_like(seen)
    ok = valid & (days + CFG["delta"] < c) & target.any(2)
    if not ok.any():
        return h.sum() * 0.0
    return explore_loss(model.logits(h[ok]), target[ok], seen[ok])


class SASRec(Source):
    name = "sasrec"
    explore = True

    def prepare(self, ev, uni, cutoff):
        m = np.arange(len(ev.members), dtype=np.int64)
        c = day_num(cutoff)
        row, idx = ev.history(m, np.full(len(m), c))
        x, days, lens = basket_windows(ev, uni, row, idx, len(m), C["max_len"], C["width"])
        keep = lens >= 2
        return torch.from_numpy(x[keep]), torch.from_numpy(days[keep]), torch.from_numpy(lens[keep]), c

    def fit(self, prep, params, ev, uni, cutoff):
        seed_everything(self.seed)
        x, days, lens = (t.to(DEVICE) for t in prep[:3])
        model = SASRecNet(uni.size, params["d"], params["blocks"], params["dropout"]).to(DEVICE)
        bs = C["batch"]
        gen = torch.Generator(device=DEVICE).manual_seed(self.seed)

        def batches(ep):
            order = torch.randperm(len(x), device=DEVICE, generator=gen)
            for s in range(0, len(order), bs):
                i = order[s:s + bs]
                n = int(lens[i].max())
                yield x[i, :n].long(), days[i, :n], lens[i], prep[3]

        return train(model, batches, lambda m, b: loss_fn(m, b, self.explore), C["epochs"], params["lr"],
                     log=f"sasrec{'' if self.explore else '_all'} {ev.country} {str(cutoff)[:10]}")

    def scores(self, model, q):
        x, days, lens = basket_windows(q.ev, q.uni, q.all_row, q.all_idx, q.n, C["max_len"], C["width"])
        x[lens == 0, 0, 0] = OOV
        lens = np.maximum(lens, 1)
        x, out = x.astype(np.int64), []
        for s in range(0, q.n, SCORE_CHUNK):   # (chunk, L, width, d) basket embeddings
            xs, ds, ns = (torch.from_numpy(a[s:s + SCORE_CHUNK]).to(DEVICE) for a in (x, days, lens))
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=DEVICE == "cuda"):
                h = model.states(xs, ds, ns)
                out.append(model.logits(h[torch.arange(len(ns), device=DEVICE), ns - 1]).float())
        return torch.cat(out)


class SASRecAll(SASRec):
    """SASRec NBR baseline (ml/baselines/nbr.py --source sasrec_all): the R10 network and parameters trained on every model bought
    in (d_j, d_j + Δ], repeats included and nothing masked, so it can rank repeats as well as new models."""
    version, explore = 2, False


if __name__ == "__main__":
    sys.exit(main(SASRec()))
