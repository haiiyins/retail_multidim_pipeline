"""Demo v0 reference snapshot (plan §10, reduced): what the public Space needs to recommend from an uploaded purchase CSV, anonymised.

Per main country (TH, VN), at the cutoff after the last test anchor: the retrieval universe (top 5 000 models by buyers in the
last 365 days), each model's department, price band (quintile within its department), popularity percentile (buyers in the last
30 days) and trend (last 30 days against the 90-day monthly mean); and the EASE item-item weights (tuned λ, rolling fit at that
cutoff), top NEIGHBOURS per model. Model codes become salted hashes (salt in data/demo/salt, never published) and departments
generic labels; no brand, store or member data leaves.
The sample CSV is synthetic: random walks over the EASE neighbours from popular models, not real members.
Usage: python serve/export_reference.py  →  data/demo/reference/{models,neighbours}_<country>.parquet, sample_purchases.csv"""
import datetime as dt, hashlib, os, secrets, sys
import numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.common.data import ROOT, connect, split_windows
from ml.retrieval.base import Events, Universe, day_num, tuned_params
from ml.retrieval.ease import EASE

OUT = ROOT / "data" / "demo" / "reference"
COUNTRIES = ("TH", "VN")
NEIGHBOURS = 30


def salt():
    p = ROOT / "data" / "demo" / "salt"
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(secrets.token_hex(16))
    return p.read_text().strip()


def anon(codes, s, prefix="M"):
    return np.array([prefix + hashlib.sha256((s + str(c)).encode()).hexdigest()[:10] for c in codes])


def export(con, country, cutoff, s, rng):
    ev = Events.load(con, country)
    uni = Universe(ev, cutoff)
    src = EASE()
    b = src.fit(src.prepare(ev, uni, cutoff), tuned_params("ease"), ev, uni, cutoff).cpu().numpy()
    items = uni.items
    c = day_num(cutoff)
    sel = ev.before(cutoff, 365)
    codes = ev.items[items]
    ids = anon(codes, s)
    dept = ev.item_dept[items]
    dept_ids = {d: f"Dept {k + 1:02d}" for k, d in enumerate(sorted(set(dept.tolist())))}
    price = pd.Series(ev.price[sel]).groupby(ev.i[sel]).median()
    m = pd.DataFrame({"model_id": ids, "department": [dept_ids[d] for d in dept],
                      "price": price.reindex(items).to_numpy()})
    m["price_band"] = m.groupby("department")["price"].transform(
        lambda p: pd.qcut(p.rank(method="first"), 5, labels=False) + 1 if p.notna().sum() >= 5 else 3).fillna(3).astype(int)
    for w in (30, 90):
        s_w = sel & (ev.day >= c - w)
        buyers = pd.Series(ev.m[s_w]).groupby(ev.i[s_w]).nunique()
        m[f"buyers_{w}d"] = buyers.reindex(items).fillna(0).astype(int).to_numpy()
    m["trend"] = ((m["buyers_30d"] + 1) / (m["buyers_90d"] / 3 + 1)).round(2)
    m["popularity"] = (m["buyers_30d"].rank(pct=True) * 100).round(1)   # percentile only: no sales volumes leave
    m = m.drop(columns=["price", "buyers_30d", "buyers_90d"])
    top = np.argsort(-b, axis=1)[:, :NEIGHBOURS]
    rows = np.repeat(np.arange(len(items)), NEIGHBOURS)
    nb = pd.DataFrame({"model_id": ids[rows], "neighbour_id": ids[top.ravel()], "weight": b[rows, top.ravel()]})
    nb = nb[nb["weight"] > 0]
    OUT.mkdir(parents=True, exist_ok=True)
    m.to_parquet(OUT / f"models_{country}.parquet", index=False)
    nb.to_parquet(OUT / f"neighbours_{country}.parquet", index=False)
    print(f"  {country}: {len(m):,} models, {len(nb):,} neighbour pairs", flush=True)
    return synthetic(country, m, nb, cutoff, rng)


def synthetic(country, m, nb, cutoff, rng, n_members=6):
    pop = m.sort_values("popularity", ascending=False)["model_id"].to_numpy()[:300]
    nbs = {k: (g["neighbour_id"].to_numpy(), g["weight"].to_numpy()) for k, g in nb.groupby("model_id")}
    rows = []
    for k in range(n_members):
        cur = rng.choice(pop)
        n = int(rng.integers(2, 9))
        days = np.sort(rng.integers(5, 365, n))[::-1]
        for d in days:
            rows.append({"member_id": f"{country}-demo-{k + 1}", "country_code": country, "model_id": cur,
                         "purchase_date": (cutoff - dt.timedelta(days=int(d))).isoformat(), "quantity": 1})
            if cur in nbs and rng.random() < 0.8:
                ids, w = nbs[cur]
                cur = rng.choice(ids, p=w / w.sum())
            else:
                cur = rng.choice(pop)
    return pd.DataFrame(rows)


def main():
    con = connect()
    cutoff = split_windows()["test_hi"] + dt.timedelta(days=1)
    s = salt()
    rng = np.random.default_rng(0)
    torch.set_grad_enabled(False)
    sample = pd.concat([export(con, c, cutoff, s, rng) for c in COUNTRIES], ignore_index=True)
    sample.to_csv(OUT / "sample_purchases.csv", index=False)
    (OUT / "asof.txt").write_text(cutoff.isoformat())
    print(f"  sample: {sample['member_id'].nunique()} synthetic members, {len(sample)} lines → {OUT}")


if __name__ == "__main__":
    sys.exit(main())
