"""P3 UMTR (plan §8.1, D9): user tower over the purchase sequence and the member context, item tower over the candidate's pair
features, model and department embeddings, DIN-style target attention of the candidate over the sequence, and two heads.

  u = MLP([masked mean of the sequence states, last state, MLP(member context)])     (variant sequence=False: context only)
  v_k = MLP([emb(model_k), emb(dept_k), MLP(x_k)]);  a_k = attention(v_k → sequence states)   (din=False: a_k = 0)
  h_k = MLP([u, v_k, a_k, u ⊙ v_k])
  two heads: p_k = g · softmax_rep(s_rep)_k if the member bought k before, else (1 − g) · softmax_exp(s_exp)_k, with g = g(u) learned
             (gate="learned"), the member's repeat share (gate="fixed"); an empty group passes its mass to the other one.
  one head (two_head=False): p = softmax(s) over the K candidates.
Auxiliary head: Δ90 label (BCE). Scores = log p. Member context = the member-entity columns of the first candidate row."""
import math
import torch, torch.nn as nn, torch.nn.functional as F

from ml.retrieval.neural import Encoder

NEG = -1e4


def mlp(i, o, dropout):
    return nn.Sequential(nn.Linear(i, o), nn.GELU(), nn.Dropout(dropout), nn.Linear(o, o))


class UMTR(nn.Module):
    def __init__(self, n_feat, n_models, n_dept, d, dropout, heads=2, blocks=2, max_len=50,
                 two_head=True, gate="learned", sequence=True, din=True):
        super().__init__()
        self.two_head, self.gate_kind, self.sequence, self.din = two_head, gate, sequence, din
        self.seq = Encoder(n_models + 1, d, blocks, heads, dropout, max_len, causal=False)   # shared model embedding; n_models = empty
        self.gap = nn.Embedding(17, d)
        self.dept = nn.Embedding(n_dept, d)
        self.ctx = mlp(n_feat, d, dropout)
        self.feat = mlp(n_feat, d, dropout)
        self.user = mlp(3 * d if sequence else d, d, dropout)
        self.item = mlp(3 * d, d, dropout)
        self.inter = mlp(4 * d, d, dropout)
        self.s_rep, self.s_exp = nn.Linear(d, 1), nn.Linear(d, 1)
        self.aux = nn.Linear(d, 1)
        self.g = nn.Linear(d, 1)
        self.scale = 1 / math.sqrt(d)

    def forward(self, b):
        x = b["x"].float()
        mask = b["mask"]
        lens = (b["seq"] > 0).sum(1)
        has = lens > 0
        seq = torch.where(has[:, None], b["seq"], torch.zeros_like(b["seq"]))
        seq[:, 0] = torch.where(has, seq[:, 0], torch.full_like(seq[:, 0], self.seq.emb.num_embeddings - 1))   # empty history token
        lens = lens.clamp(min=1)
        c = self.ctx(x[:, 0])
        if self.sequence:
            hs = self.seq(seq, lens, self.seq.emb(seq) + self.gap(b["gap"]))
            keep = (seq > 0).unsqueeze(-1).to(hs.dtype)
            pooled = (hs * keep).sum(1) / keep.sum(1).clamp(min=1)
            last = hs[torch.arange(len(lens), device=hs.device), lens - 1]
            u = self.user(torch.cat([pooled, last, c], 1))
        else:
            u = self.user(c)
        v = self.item(torch.cat([self.seq.emb(b["model"]), self.dept(b["dept"]), self.feat(x)], 2))
        if self.din and self.sequence:
            att = torch.einsum("akd,ald->akl", v, hs) * self.scale
            att = att.masked_fill(~(seq > 0)[:, None, :], NEG).softmax(-1)
            a = torch.einsum("akl,ald->akd", att, hs)
        else:
            a = torch.zeros_like(v)
        uk = u[:, None, :].expand_as(v)
        h = self.inter(torch.cat([uk, v, a, uk * v], 2))
        out = {"aux": self.aux(h).squeeze(-1)}
        if not self.two_head:
            s = self.s_rep(h).squeeze(-1).float().masked_fill(~mask, NEG)
            out["logp"] = F.log_softmax(s, 1)
            return out
        rep = b["rep"] & mask
        exp = ~b["rep"] & mask
        lr = F.log_softmax(self.s_rep(h).squeeze(-1).float().masked_fill(~rep, NEG), 1)
        le = F.log_softmax(self.s_exp(h).squeeze(-1).float().masked_fill(~exp, NEG), 1)
        if self.gate_kind == "learned":
            out["g_logit"] = self.g(u).squeeze(-1).float()
            g = torch.sigmoid(out["g_logit"])
        else:
            g = b["rho"].float().clamp(0.01, 0.99)
        g_eff = torch.where(rep.any(1), torch.where(exp.any(1), g, torch.ones_like(g)), torch.zeros_like(g)).clamp(1e-6, 1 - 1e-6)
        logp = torch.where(rep, torch.log(g_eff)[:, None] + lr, torch.log1p(-g_eff)[:, None] + le)
        out["logp"] = logp.masked_fill(~mask, NEG)
        out["g"] = g
        return out


def loss_fn(model, b, lambda_d90, lambda_gate):
    out = model(b)
    y, mask = b["y30"] & b["mask"], b["mask"]
    has = y.any(1)
    yf = y.float()
    listwise = -((out["logp"] * yf).sum(1) / yf.sum(1).clamp(min=1))[has].mean() if has.any() else out["logp"].sum() * 0
    aux = F.binary_cross_entropy_with_logits(out["aux"].float()[mask], b["y90"][mask].float())
    loss = listwise + lambda_d90 * aux
    if "g_logit" in out:
        gy = b["gate_y"]
        ok = ~torch.isnan(gy)
        if ok.any():
            loss = loss + lambda_gate * F.binary_cross_entropy_with_logits(out["g_logit"][ok], gy[ok].float())
    return loss
