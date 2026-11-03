"""Demo v0 recommender: the retrieval layer of the pipeline on an uploaded purchase history, with a reason for every model.

Three sources, as R1 / R6 / R13 of ml/retrieval: repeat (the member's own models, frequency × recency decay), co-purchase (EASE
item-item weights summed over her history) and trend (models rising in her departments). Explore sources skip the models she
already bought (explore-only, ml/DECISIONS.md). Lists are merged with the mixer's weighted rank quotas: key = min_s (rank_s − 0.5) / w_s.
The offline ranker (P1 / P3) is evaluated in the report; the demo serves the candidate layer only.
Besides the Vietnamese `reason`, every row carries the structured facts behind it (times bought, days since the last purchase,
purchase cycle, due flag, the model it is bought with, trend, new department) so the page can phrase it in either language."""
import datetime as dt
import numpy as np, pandas as pd

WEIGHTS = {"repeat": 1.0, "co_purchase": 0.8, "trend": 0.4}
HALF_LIFE = 180
DUE = (0.8, 2.0)   # a repeat is due between 80 % and 200 % of the member's own cycle for that model; later it has lapsed
EXTRA = ["n", "last", "cycle", "due", "because", "trend", "popularity"]
REQUIRED = ("member_id", "country_code", "model_id", "purchase_date")


class Reference:
    def __init__(self, models, neighbours, asof):
        self.models = models.set_index("model_id")
        self.nb = neighbours.reset_index(drop=True)
        self.nb_rows = self.nb.groupby("model_id").indices
        self.asof = asof
        base = self.models["popularity"] / 100 * self.models["trend"].clip(upper=3)
        m = self.models.assign(base=base).sort_values("base", ascending=False, kind="stable")
        self.by_dept = {d: g for d, g in m.groupby("department", sort=False)}


def validate(df):
    missing = [c for c in REQUIRED if c not in df.columns]
    if missing:
        raise ValueError(f"missing columns: {', '.join(missing)}")
    df = df.copy()
    df["purchase_date"] = pd.to_datetime(df["purchase_date"], errors="coerce").dt.date
    df["quantity"] = pd.to_numeric(df["quantity"], errors="coerce").fillna(1) if "quantity" in df.columns else 1
    bad = df["purchase_date"].isna() | df["member_id"].isna() | df["model_id"].isna()
    return df[~bad], int(bad.sum())


def repeat(h, ref):
    days = np.array([(ref.asof - d).days for d in h["purchase_date"]])
    h = h.assign(w=h["quantity"] * 0.5 ** (days / HALF_LIFE), days=days)
    g = h.groupby("model_id").agg(score=("w", "sum"), n=("quantity", "sum"), last=("days", "min"), first=("days", "max"),
                                  visits=("purchase_date", "nunique")).reset_index()
    g["cycle"] = np.where(g["visits"] > 1, (g["first"] - g["last"]) / (g["visits"] - 1).clip(lower=1), np.nan).round()
    g["due"] = g["cycle"].notna() & g["last"].between(DUE[0] * g["cycle"], DUE[1] * g["cycle"])
    g["reason"] = [f"Mua lại: bạn đã mua {int(n)} lần, lần gần nhất {d} ngày trước" for n, d in zip(g["n"], g["last"])]
    return g[["model_id", "score", "reason", "n", "last", "cycle", "due"]]


def co_purchase(h, ref, seen):
    rows = [ref.nb_rows[m] for m in seen if m in ref.nb_rows]
    nb = ref.nb.iloc[np.concatenate(rows)] if rows else ref.nb.iloc[:0]
    nb = nb[~nb["neighbour_id"].isin(seen)]
    if nb.empty:
        return pd.DataFrame(columns=["model_id", "score", "reason"])
    top = nb.sort_values("weight", ascending=False).drop_duplicates("neighbour_id")[["neighbour_id", "model_id"]]
    s = nb.groupby("neighbour_id")["weight"].sum().rename("score").reset_index().merge(top, on="neighbour_id")
    s["reason"] = [f"Hay được mua cùng {m} (bạn đã mua)" for m in s["model_id"]]
    return s.rename(columns={"model_id": "because", "neighbour_id": "model_id"})[["model_id", "score", "reason", "because"]]


def trend(h, ref, seen, n=50):
    known = [m for m in h["model_id"] if m in ref.models.index]
    depts = ref.models.loc[known, "department"].value_counts()
    if depts.empty:
        depts = ref.models["department"].value_counts().head(3) * 0 + 1
    # each department's list is sorted by base score, so its top n + |seen| rows hold every model that can reach the overall top n
    m = pd.concat([ref.by_dept[d].head(n + len(seen)) for d in depts.index if d in ref.by_dept])
    m = m[~m.index.isin(seen)]
    m["score"] = m["base"] * m["department"].map(depts / depts.sum())
    m = m.sort_values("score", ascending=False).head(n).reset_index()
    m["reason"] = [f"Đang bán chạy trong {d}, ngành hàng bạn hay mua (×{t:.1f} so với quý trước)"
                   for d, t in zip(m["department"], m["trend"])]
    return m[["model_id", "score", "reason", "trend"]]


def merge(lists, k):
    keys = []
    for name, df in lists.items():
        if len(df):
            d = df.sort_values("score", ascending=False).reset_index(drop=True)
            keys.append(d.assign(source=name, key=(np.arange(len(d)) + 0.5) / WEIGHTS[name]))
    if not keys:
        return pd.DataFrame(columns=["rank", "model_id", "source", "reason"] + EXTRA[:-1])
    allk = pd.concat(keys).sort_values(["key", "score"], ascending=[True, False]).drop_duplicates("model_id").head(k)
    allk["rank"] = np.arange(1, len(allk) + 1)
    for c in EXTRA[:-1]:
        if c not in allk:
            allk[c] = np.nan
    return allk[["rank", "model_id", "source", "reason"] + EXTRA[:-1]]


def recommend(df, refs, k=10):
    """df: validated purchases of one or more members; refs: {country: Reference}. Returns the top-k of every member."""
    out = []
    for (member, country), h in df.groupby(["member_id", "country_code"], sort=True):
        ref = refs.get(country)
        if ref is None:
            continue
        h = h[h["purchase_date"] < ref.asof]
        seen = set(h["model_id"])
        r = merge({"repeat": repeat(h, ref), "co_purchase": co_purchase(h, ref, seen), "trend": trend(h, ref, seen)}, k)
        r = r.merge(ref.models[["department", "price_band", "popularity"]], left_on="model_id", right_index=True, how="left")
        own = set(ref.models.loc[ref.models.index.intersection(list(seen)), "department"])
        r["new_department"] = (r["source"] != "repeat") & ~r["department"].isin(own)
        out.append(r.assign(member_id=member, country_code=country))
    cols = ["member_id", "country_code", "rank", "model_id", "department", "price_band", "source", "reason"] + EXTRA + ["new_department"]
    return pd.concat(out, ignore_index=True)[cols] if out else pd.DataFrame(columns=cols)


def profiles(df, refs):
    """One row per member: purchases, distinct models, days since the last purchase, visits in the 365 days before the as-of date,
    segment (new ≤ 1 visit, mid 2, loyal ≥ 3, as the report's segments) and the top departments of the history."""
    rows = []
    for (member, country), h in df.groupby(["member_id", "country_code"], sort=True):
        ref = refs.get(country)
        if ref is None:
            continue
        h = h[h["purchase_date"] < ref.asof]
        if h.empty:
            continue
        days = np.array([(ref.asof - d).days for d in h["purchase_date"]])
        visits = h.loc[days <= 365, "purchase_date"].nunique()
        depts = ref.models.reindex(h["model_id"])["department"].dropna().value_counts()
        rows.append({"member_id": member, "country_code": country, "purchases": int(h["quantity"].sum()),
                     "models": h["model_id"].nunique(), "last_days": int(days.min()), "visits_365d": int(visits),
                     "segment": "new" if visits <= 1 else "mid" if visits == 2 else "loyal",
                     "departments": [{"department": d, "count": int(c)} for d, c in depts.head(4).items()]})
    return pd.DataFrame(rows)


def load_refs(root):
    import pathlib
    root = pathlib.Path(root)
    asof = dt.date.fromisoformat((root / "asof.txt").read_text().strip())
    ext = "parquet" if any(root.glob("models_*.parquet")) else "csv"
    read = pd.read_parquet if ext == "parquet" else pd.read_csv
    return {p.stem.split("_")[1]: Reference(read(p), read(root / p.name.replace("models_", "neighbours_")), asof)
            for p in sorted(root.glob(f"models_*.{ext}"))}
