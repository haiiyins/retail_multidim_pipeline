"""R12 RP3beta (Paudel et al., TiiS 2017): three-step random walk item → member → item with popularity re-weighting, closed form per
country × cutoff.

X: member × universe model, 1 when the member bought the model in the rp3beta.fit_window_days before the cutoff. With the transition
probabilities raised to α, W_ij = deg_i^−α · Σ_u x_ui x_uj deg_u^−α / pop_j^β (deg = degree in X, pop_j = deg_j), diag(W) = 0. A member
is scored at the anchor from the binary vector of her universe purchases before the anchor: s = x W. α and β are tuned on valid.
Usage: python ml/retrieval/rp3beta.py --tune | --build"""
import os, sys
import numpy as np, scipy.sparse as sp, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import CFG, DEVICE, Source, main
from ml.retrieval.ease import binary_matrix


def rp3_weights(x, alpha, beta):
    deg_u = np.asarray(x.sum(1)).ravel()
    deg_i = np.asarray(x.sum(0)).ravel()
    xu = sp.diags(np.power(np.maximum(deg_u, 1), -alpha, dtype=np.float64)) @ x
    g = (x.T @ xu).toarray()
    w = np.power(np.maximum(deg_i, 1), -alpha)[:, None] * g * np.power(np.maximum(deg_i, 1), -beta)[None, :]
    np.fill_diagonal(w, 0.0)
    return w


class RP3beta(Source):
    name = "rp3beta"

    def prepare(self, ev, uni, cutoff):
        sel = ev.before(cutoff, CFG["rp3beta"]["fit_window_days"])
        u = uni.pos[ev.i[sel]]
        keep = u >= 0
        x = binary_matrix(ev.m[sel][keep], u[keep], (len(ev.members), uni.size))
        return x[np.flatnonzero(np.diff(x.indptr))].astype(np.float64)   # members with at least one purchase

    def fit(self, prep, params, ev, uni, cutoff):
        return torch.as_tensor(rp3_weights(prep, params["alpha"], params["beta"]), dtype=torch.float32, device=DEVICE)

    def scores(self, model, q):
        x = torch.zeros(q.n, model.shape[0], device=DEVICE)
        x[torch.from_numpy(q.row).to(DEVICE), torch.from_numpy(q.item).to(DEVICE)] = 1.0
        return x @ model


if __name__ == "__main__":
    sys.exit(main(RP3beta()))
