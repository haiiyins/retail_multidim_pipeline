"""ML-09 — R6 EASE (Steck, WWW 2019): B = −P / diag(P) with P = (XᵀX + λI)⁻¹ and diag(B) = 0, closed form per country × cutoff.

X: member × universe model, 1 when the member bought the model in the ease.fit_window_days before the cutoff. A member is scored at
the anchor from the binary vector of her universe purchases before the anchor: s = x B. λ (l2) is tuned on valid (tuning.yml).
Usage: python ml/retrieval/ease.py --tune | --build"""
import os, sys
import numpy as np, scipy.sparse as sp, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import CFG, DEVICE, Source, main


def binary_matrix(rows, cols, shape):
    x = sp.csr_matrix((np.ones(len(rows), np.float32), (rows, cols)), shape=shape)
    x.sum_duplicates()
    x.data[:] = 1.0
    return x


def ease_weights(gram, l2):
    g = torch.as_tensor(gram, dtype=torch.float64, device=DEVICE).clone()
    g.diagonal().add_(l2)
    p = torch.linalg.inv(g)
    b = -p / torch.diagonal(p)[None, :]
    b.fill_diagonal_(0.0)
    return b.float()


class EASE(Source):
    name = "ease"

    def prepare(self, ev, uni, cutoff):
        sel = ev.before(cutoff, CFG["ease"]["fit_window_days"])
        u = uni.pos[ev.i[sel]]
        keep = u >= 0
        x = binary_matrix(ev.m[sel][keep], u[keep], (len(ev.members), uni.size))
        return (x.T @ x).toarray()

    def fit(self, prep, params, ev, uni, cutoff):
        return ease_weights(prep, params["l2"])

    def scores(self, model, q):
        x = torch.zeros(q.n, model.shape[0], device=DEVICE)
        x[torch.from_numpy(q.row).to(DEVICE), torch.from_numpy(q.item).to(DEVICE)] = 1.0
        return x @ model


if __name__ == "__main__":
    sys.exit(main(EASE()))
