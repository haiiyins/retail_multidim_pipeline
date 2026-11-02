"""Shared pieces of the neural candidate sources R9 two-tower and R10 SASRec-retrieval: purchase-token and basket sequences, a
transformer encoder over them, the explore-only target loss and the training loop.

Tokens: PAD = 0, OOV = 1 (a model outside the universe, kept as context), universe position + 2. Sequences are right-padded, oldest →
newest, and positions count back from the latest step (0 = latest), so the latest purchase always has the same position."""
import time
import numpy as np, torch, torch.nn as nn, torch.nn.functional as F

from ml.retrieval.base import DAY_BITS, DEVICE

PAD, OOV, OFFSET = 0, 1, 2
GAP_BUCKETS = 13   # 0 = first basket, then ceil(log2(days since the previous basket + 1)) capped (12 ≈ 11 years)


def tokens(ev, uni, idx):
    u = uni.pos[ev.i[idx]]
    return np.where(u >= 0, u + OFFSET, OOV)


def last_window(row, tok, n, length):
    """(n, length) right-padded windows with the last `length` tokens of each row and their lengths; `row` must be sorted with each
    row's tokens oldest → newest (the order of Events.history)."""
    cnt = np.bincount(row, minlength=n)
    start = np.cumsum(cnt) - cnt
    pos = np.arange(len(row)) - start[row]
    skip = np.maximum(cnt - length, 0)
    sel = pos >= skip[row]
    out = np.zeros((n, length), np.int64)
    out[row[sel], (pos - skip[row])[sel]] = tok[sel]
    return out, np.minimum(cnt, length)


def query_window(ev, uni, q, length):
    """Input windows of a Query (every purchase before the anchor, also outside the universe); empty rows get one OOV token."""
    seq, lens = last_window(q.all_row, tokens(ev, uni, q.all_idx), q.n, length)
    seq[lens == 0, 0] = OOV
    return seq, np.maximum(lens, 1)


def basket_windows(ev, uni, row, idx, n, length, width):
    """The last `length` baskets (purchase days) of each row as (n, length, width) tokens, (n, length) days and lengths; a basket
    keeps its first `width` models (universe models first). `row`, `idx` in Events.history order."""
    day = ev.day[idx]
    bk, binv = np.unique(row.astype(np.int64) * DAY_BITS + day, return_inverse=True)
    brow, bday = (bk // DAY_BITS).astype(np.int64), (bk % DAY_BITS).astype(np.int32)
    cnt = np.bincount(brow, minlength=n)
    bpos = np.arange(len(bk)) - (np.cumsum(cnt) - cnt)[brow]
    skip = np.maximum(cnt - length, 0)[brow]
    tok = tokens(ev, uni, idx)
    order = np.lexsort((tok == OOV, binv))   # within a basket: universe models first
    binv, tok = binv[order], tok[order]
    first = np.searchsorted(binv, np.arange(len(bk)))
    j = np.arange(len(binv)) - first[binv]
    keep = (bpos[binv] >= skip[binv]) & (j < width)
    out = np.zeros((n, length, width), np.int16)
    b = binv[keep]
    out[brow[b], (bpos - skip)[b], j[keep]] = tok[keep]
    days = np.zeros((n, length), np.int32)
    kb = bpos >= skip
    days[brow[kb], (bpos - skip)[kb]] = bday[kb]
    return out, days, np.minimum(cnt, length)


def gap_buckets(days, lens):
    """(n, L) log2 buckets of the days since the previous basket; 0 for the first basket and for pads."""
    gap = torch.zeros_like(days)
    gap[:, 1:] = days[:, 1:] - days[:, :-1]
    b = torch.ceil(torch.log2(gap.float() + 1)).long().clamp(1, GAP_BUCKETS - 1)
    steps = torch.arange(days.shape[1], device=days.device)[None]
    return torch.where((steps == 0) | (steps >= lens[:, None]), 0, b)


def months(day):
    """Calendar month 0–11 of day numbers (days since 1970-01-01)."""
    return np.asarray(day).astype("datetime64[D]").astype("datetime64[M]").astype(np.int64) % 12


class Encoder(nn.Module):
    def __init__(self, n_tok, d, blocks, heads, dropout, max_len, causal):
        super().__init__()
        self.emb = nn.Embedding(n_tok, d, padding_idx=PAD)
        self.pos = nn.Embedding(max_len, d)
        layer = nn.TransformerEncoderLayer(d, heads, 4 * d, dropout, batch_first=True, norm_first=True, activation="gelu")
        self.blocks = nn.TransformerEncoder(layer, blocks, enable_nested_tensor=False)
        self.norm, self.drop, self.causal = nn.LayerNorm(d), nn.Dropout(dropout), causal
        nn.init.normal_(self.emb.weight, std=0.02)   # N(0, 1) makes the tied output logits ~√d at start
        nn.init.normal_(self.pos.weight, std=0.02)
        with torch.no_grad():
            self.emb.weight[PAD].zero_()

    def forward(self, x, lens, inp=None):
        """x: (n, L) tokens, or None with inp: (n, L, d) step inputs (causal only: right padding needs no key mask)."""
        n_pos = (x if inp is None else inp).shape[1]
        dev = lens.device
        pos = (lens[:, None] - 1 - torch.arange(n_pos, device=dev)[None]).clamp(min=0)
        h = self.drop((self.emb(x) if inp is None else inp) + self.pos(pos))
        if self.causal:   # right padding: a real step never attends to a pad
            h = self.blocks(h, mask=nn.Transformer.generate_square_subsequent_mask(n_pos, device=dev), is_causal=True)
        else:
            h = self.blocks(h, src_key_padding_mask=x == PAD)
        return self.norm(h)


def explore_loss(logits, target, seen):
    """Softmax over the universe averaged over the explore targets; models already bought (seen) are masked out of the softmax,
    as they are at scoring time (retrieval.explore_only)."""
    logp = F.log_softmax(logits.float().masked_fill(seen, -1e4), dim=1)
    t = target.float()
    return -((logp * t).sum(1) / t.sum(1)).mean()


def seed_everything(seed):
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
    return np.random.default_rng(seed)


def train(model, batches, loss_fn, epochs, lr, log=""):
    """batches(epoch) yields batches for loss_fn(model, batch) -> scalar; AdamW, bf16 autocast, gradient clipping at 1."""
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=0.01)
    model.train()
    for ep in range(epochs):
        t0, tot, n = time.time(), 0.0, 0
        for b in batches(ep):
            with torch.autocast("cuda", dtype=torch.bfloat16, enabled=DEVICE == "cuda"):
                loss = loss_fn(model, b)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tot, n = tot + loss.detach(), n + 1
        print(f"    {log} epoch {ep}: loss {float(tot) / max(n, 1):.4f}  {n} steps  {time.time() - t0:.0f}s", flush=True)
    model.eval()
    return model
