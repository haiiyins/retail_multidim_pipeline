"""Demo back-test showcase: the batch-scored output of the best model (P3 one head, selected on valid; 85 pair features, 13 candidate
sources) next to the status quo (GP-TopFreq) for a random sample of real test anchors, with what each member bought in the 30 days
after the anchor. Published with the data owner's consent; minimised and anonymised: members get sequential ids in a shuffled order
(no hash of the real id), model codes the salted hashes of the reference, departments its generic labels, dates become days before
the anchor, the history is capped to the last HISTORY lines; no price, store, web or member attribute leaves.
Usage: python serve/export_showcase.py [--members 250 (per country)] [--best p3_onehead] [--status-quo gptopfreq]
  →  data/demo/reference/showcase.json"""
import argparse, json, os, sys
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.common.data import ML_DIR, connect
from ml.eval.protocol import build_positives
from ml.retrieval.base import Events, Universe
from serve.export_reference import COUNTRIES, OUT, anon, salt

TOP, HISTORY, DELTA = 10, 40, 30


def top(path, keys):
    s = pd.read_parquet(path, filters=[("member_id", "in", keys["member_id"].unique().tolist())])
    s["anchor_date"] = pd.to_datetime(s["anchor_date"])
    s = s.merge(keys[["member_id", "anchor_date"]], on=["member_id", "anchor_date"])
    s = s[np.isfinite(s["score"])].sort_values(["member_id", "anchor_date", "score", "model_code"], ascending=[True, True, False, True])
    return s.groupby(["member_id", "anchor_date"]).head(TOP)


def dept_labels(con, country, asof):
    """model_code → the generic department label of the reference (same sorted-code order as export_reference.export)."""
    ev = Events.load(con, country)
    uni = Universe(ev, asof)
    codes = sorted(set(ev.item_dept[uni.items].tolist()))
    label = {d: f"Dept {k + 1:02d}" for k, d in enumerate(codes)}
    return pd.Series([label.get(d, "Dept --") for d in ev.item_dept], index=ev.items)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--members", type=int, default=250)
    ap.add_argument("--best", default="p3_onehead")
    ap.add_argument("--status-quo", default="gptopfreq")
    a = ap.parse_args()
    con, s, rng = connect(), salt(), np.random.default_rng(0)
    asof = pd.Timestamp((OUT / "asof.txt").read_text().strip()).date()
    pos = pd.read_parquet(build_positives(con, "test", DELTA))
    pos["anchor_date"] = pd.to_datetime(pos["anchor_date"])
    anchors = pos[pos["country_code"].isin(COUNTRIES)][["member_id", "country_code", "anchor_date"]].drop_duplicates()
    # one anchor per member, then a uniform sample of members per country
    anchors = anchors.sample(frac=1, random_state=0).drop_duplicates("member_id")
    keys = pd.concat([g.sample(min(a.members, len(g)), random_state=0) for _, g in anchors.groupby("country_code")], ignore_index=True)
    best = top(os.path.join(ML_DIR, "scores", f"{a.best}_test_d{DELTA}.parquet"), keys)
    sq = top(os.path.join(ML_DIR, "scores", f"{a.status_quo}_test_d{DELTA}.parquet"), keys)
    con.register("_k", keys)
    hist = con.execute("""
        SELECT k.member_id, k.anchor_date, f.model_code, date_diff('day', f.transaction_date, CAST(k.anchor_date AS DATE)) AS days_before,
               SUM(f.qty) AS quantity
        FROM _k k JOIN lh.silver.slv_fact_sales_line f
          ON f.member_id = k.member_id AND f.country_code = k.country_code AND f.transaction_date <= CAST(k.anchor_date AS DATE)
        WHERE f.model_code IS NOT NULL GROUP BY ALL HAVING SUM(f.qty) > 0""").df()
    hist["anchor_date"] = pd.to_datetime(hist["anchor_date"])
    visits = hist[hist["days_before"] <= 365].groupby("member_id")["days_before"].nunique()
    hist = hist.sort_values(["member_id", "days_before", "model_code"]).groupby("member_id").head(HISTORY)
    refm = {c: pd.read_parquet(OUT / f"models_{c}.parquet").set_index("model_id")["price_band"] for c in COUNTRIES}

    members = [tuple(keys.iloc[i][["country_code", "member_id", "anchor_date"]]) for i in rng.permutation(len(keys))]
    labels = {c: dept_labels(con, c, asof) for c in COUNTRIES}

    def item(code, c, bought, seen):
        h = anon([code], s)[0]
        band = refm[c].get(h)
        return {"model_id": h, "department": labels[c].get(code, "Dept --"), "price_band": None if pd.isna(band) else int(band),
                "repeat": code in seen, "bought": code in bought}

    out, seq = [], {c: 0 for c in COUNTRIES}
    for c, mid, ad in members:
        seq[c] += 1
        h = hist[(hist["member_id"] == mid) & (hist["anchor_date"] == ad)]
        p = pos[(pos["member_id"] == mid) & (pos["anchor_date"] == ad)]
        bought, seen = set(p["model_code"]), set(h["model_code"])
        lists = {name: [item(m, c, bought, seen) for m in df.loc[(df["member_id"] == mid) & (df["anchor_date"] == ad), "model_code"]]
                 for name, df in (("best", best), ("status_quo", sq))}
        v = int(visits.get(mid, 0))
        out.append({"member_id": f"{c}-{seq[c]:03d}", "country_code": c,
                    "segment": "new" if v <= 1 else "mid" if v == 2 else "loyal",
                    "history": [{"model_id": anon([r.model_code], s)[0], "department": labels[c].get(r.model_code, "Dept --"),
                                 "days_before": int(r.days_before), "quantity": int(r.quantity)} for r in h.itertuples()],
                    "bought": [{"model_id": anon([r.model_code], s)[0], "department": labels[c].get(r.model_code, "Dept --"),
                                "repeat": bool(r.is_repeat), "days_after": int(r.days_to_buy)} for r in p.sort_values("days_to_buy").itertuples()],
                    **lists})
    hits = {name: float(np.mean([any(x["bought"] for x in m[name]) for m in out])) for name in ("best", "status_quo")}
    doc = {"delta": DELTA, "top": TOP, "best": a.best, "status_quo": a.status_quo, "sample_hr10": hits, "members": out}
    (OUT / "showcase.json").write_text(json.dumps(doc, ensure_ascii=False, separators=(",", ":")))
    print(f"  showcase: {len(out)} members, HR@{TOP} in the sample {a.best} {hits['best']:.3f} vs {a.status_quo} "
          f"{hits['status_quo']:.3f} → {OUT / 'showcase.json'}")


if __name__ == "__main__":
    sys.exit(main())
