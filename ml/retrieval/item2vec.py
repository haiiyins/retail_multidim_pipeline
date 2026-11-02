"""ML-08 — R7 item2vec (Barkan & Koenigstein, 2016): skip-gram with negative sampling over each member's purchase sequence before
the cutoff (models in purchase order), per country × cutoff. The member vector at the anchor is the mean of the vectors of her universe
purchases before the anchor, weighted by 0.5^(days_before / half_life_days); candidates are the universe models of highest cosine,
searched exactly on the GPU (5 000 models per country make an ANN index unnecessary). Item vectors are kept in
data/ml/models/item2vec/<country>_<cutoff>.parquet for the similarity features of P2 (sim_max, sim_mean).
Fixed parameters (retrieval.yml): the plan gives item2vec no tuning budget.
Usage: python ml/retrieval/item2vec.py --build"""
import os, sys
import numpy as np, pandas as pd, torch
from gensim.models import Word2Vec

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ml_path
from ml.retrieval.base import CFG, DEVICE, Source, main


def sentences(ev, cutoff):
    sel = ev.before(cutoff)
    m, i = ev.m[sel], ev.i[sel]
    bounds = np.flatnonzero(np.diff(m)) + 1
    tok = np.array([str(x) for x in range(len(ev.items))], dtype=object)
    return [tok[s].tolist() for s in np.split(i, bounds) if len(s) > 1]


class Item2Vec(Source):
    name = "item2vec"

    def fit(self, prep, params, ev, uni, cutoff):
        w2v = Word2Vec(sentences(ev, cutoff), vector_size=params["d"], window=params["window"], sg=1, negative=params["negative"],
                       min_count=params["min_count"], epochs=params["epochs"], workers=CFG["item2vec"]["workers"], seed=0)
        vocab = np.array([int(t) for t in w2v.wv.index_to_key])
        pd.DataFrame({"model_code": ev.items[vocab], "vector": list(w2v.wv.vectors)}).to_parquet(
            ml_path("models", "item2vec", f"{ev.country}_{cutoff.date()}.parquet"), index=False)
        e = np.zeros((uni.size, params["d"]), np.float32)
        known = uni.pos[vocab] >= 0
        e[uni.pos[vocab][known]] = w2v.wv.vectors[known]
        e = torch.nn.functional.normalize(torch.from_numpy(e).to(DEVICE), dim=1)
        return {"e": e, "missing": torch.from_numpy(np.linalg.norm(e.cpu().numpy(), axis=1) == 0).to(DEVICE),
                "half_life": params["half_life_days"]}

    def scores(self, model, q):
        w = torch.from_numpy((0.5 ** (q.days_before / model["half_life"])).astype(np.float32)).to(DEVICE)
        u = torch.zeros(q.n, model["e"].shape[1], device=DEVICE)
        u.index_add_(0, torch.from_numpy(q.row).to(DEVICE), model["e"][torch.from_numpy(q.item).to(DEVICE)] * w[:, None])
        s = torch.nn.functional.normalize(u, dim=1) @ model["e"].T
        s[:, model["missing"]] = -torch.inf
        s[u.norm(dim=1) == 0] = -torch.inf
        return s


if __name__ == "__main__":
    sys.exit(main(Item2Vec()))
