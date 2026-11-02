"""R13 context-aware trending: the universe models bought on the most member-days in the window_days before the anchor, re-weighted by the
member's departments and price band — a personalised replacement for the capped tail of R5 (bestsellers).

score = log1p(member-days with a purchase in [t − window_days, t)) + w_dept · log(share of the member's purchases before t in the model's department + 0.01)
        + w_price · 1[|price bucket of the model − the member's mean price bucket| ≤ 1]
Counts are read at the anchor day, not at the fit cutoff: every count is of purchases strictly before the anchor, so the source
stays point-in-time although the window passes the cutoff. Price buckets: deciles of the mean unit price before the cutoff over the
universe. window_days, w_dept, w_price are tuned on valid.
Usage: python ml/retrieval/trend.py --tune | --build"""
import os, sys
import numpy as np, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.retrieval.base import DEVICE, Source, item_attributes, main

BUCKETS = 10


class Trend(Source):
    name = "trend"

    def prepare(self, ev, uni, cutoff):
        u = uni.pos[ev.i]
        k = u >= 0
        d0 = int(ev.day.min())
        n_days = int(ev.day.max()) - d0 + 1
        daily = np.bincount((ev.day[k] - d0).astype(np.int64) * uni.size + u[k], minlength=n_days * uni.size)
        cum = np.zeros((n_days + 1, uni.size), np.float32)
        np.cumsum(daily.reshape(n_days, uni.size), axis=0, out=cum[1:])   # cum[j] = member-days of purchase before d0 + j
        dept, bucket, edges = item_attributes(ev, uni, cutoff, BUCKETS)
        codes = np.unique(ev.item_dept[uni.items])
        pos = np.clip(np.searchsorted(codes, ev.item_dept), 0, len(codes) - 1)
        any_dept = np.where(codes[pos] == ev.item_dept, pos, -1)          # department index of every model, -1 outside the universe's
        return {"cum": torch.from_numpy(cum).to(DEVICE), "d0": d0, "dept": torch.from_numpy(dept).to(DEVICE), "n_dept": len(codes),
                "any_dept": any_dept, "bucket": torch.from_numpy(bucket).to(DEVICE), "edges": edges}

    def fit(self, prep, params, ev, uni, cutoff):
        return {**prep, **params}

    def scores(self, model, q):
        cum, n = model["cum"], model["cum"].shape[0] - 1
        hi = np.clip(q.day - model["d0"], 0, n)
        lo = np.clip(q.day - model["d0"] - int(model["window_days"]), 0, n)
        s = torch.log1p(cum[torch.from_numpy(hi).to(DEVICE)] - cum[torch.from_numpy(lo).to(DEVICE)])
        row, idx = q.all_row, q.all_idx
        d = model["any_dept"][q.ev.i[idx]]
        k = d >= 0
        cnt = np.bincount(row[k] * model["n_dept"] + d[k], minlength=q.n * model["n_dept"]).reshape(q.n, model["n_dept"])
        share = torch.from_numpy(cnt / np.maximum(cnt.sum(1, keepdims=True), 1)).float().to(DEVICE)
        s += model["w_dept"] * torch.log(share[:, model["dept"]] + 0.01)
        p = q.ev.price[idx]
        k = p > 0
        b = np.searchsorted(model["edges"], p[k]).astype(np.float64)
        num = np.bincount(row[k], minlength=q.n)
        mb = torch.from_numpy(np.bincount(row[k], weights=b, minlength=q.n) / np.maximum(num, 1)).float().to(DEVICE)
        match = (model["bucket"][None, :].float() - mb[:, None]).abs() <= 1
        match |= torch.from_numpy(num == 0).to(DEVICE)[:, None]             # no priced purchase: no price term
        return s + model["w_price"] * match.float()


if __name__ == "__main__":
    sys.exit(main(Trend()))
