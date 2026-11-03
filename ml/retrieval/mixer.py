"""ML-13 — candidate mixer: merges R1–R3, R5 of gold.gld_candidates (R4 dropped, ML-04) with the learned sources into one ranked list
per anchor, capped at mixer.k_max; ml.candidates_v2 is this list cut at mixer.k (ML-14, build_candidates.py).

Rank merge with quotas: a candidate gets key = min over the sources that propose it of (rank_in_source − 0.5) / w_source, and the list is
sorted by key, so a source of weight 2 fills two slots for every slot of a source of weight 1. w_source = the stand-alone valid Recall@100
of the source (hits per slot). Policies (plan §5.1):
  fixed       the same weights for every member;
  per_member  w_r1 × ρ_u / mean ρ, ρ_u = the member's share of repeat purchases before the anchor (member × model × day rows whose
              model she had bought on an earlier day, smoothed towards the country mean with mixer.rho_prior rows), clipped to
              mixer.rho_clip: members who mostly repeat keep more of R1, explorers get more learned candidates;
  r1_first    the whole R1 list first (every model bought before the anchor, at most 200), then the fixed quotas for the rest:
              the repeat coverage of R1–R5 is kept whatever the weights.
Every input reads strictly before the anchor, so the merged list is point-in-time when its sources are. Train anchors before the first
rolling cutoff have R1–R5 only. Output: data/ml/candidates/mix_<policy>/<split>_<country>.parquet with mix_rank, the rank in every
source (NULL when the source does not propose the model) and fit_cutoff / source_ts_max of the learned sources.
Usage: python ml/retrieval/mixer.py [--policies fixed,per_member] [--splits train,valid,test]"""
import argparse, os, sys, time
import numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, ml_path
from ml.retrieval.base import CFG, DAY_BITS, EPOCH, Events, KS, baseline_relation, candidates_relation, recall_table, show

M = CFG["mixer"]
BASE_SOURCES = ("r1", "r2", "r3", "r5")


def learned_sources():
    return [s for s in M["learned"] if os.path.isdir(os.path.join(ML_DIR, "candidates", s))]


def source_relation(s, split):
    """(member_id, anchor_date, model_code, rk) of one source, rk = 1 … in the source's own order."""
    if s in BASE_SOURCES:
        return f"""(SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code,
                           ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score_{s} DESC, model_code) AS rk
                    FROM lh.gold.gld_candidates WHERE split = '{split}' AND {s} = 1)"""
    return (f"(SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code, rank AS rk "
            f"FROM read_parquet('{ml_path('candidates', s, '*.parquet')}') WHERE split = '{split}')")


def weights(con, sources):
    """Stand-alone valid Recall@100 of every source (member means, unconditional)."""
    w = {}
    for s in sources:
        rel = f"(SELECT member_id, anchor_date, model_code, -rk AS score FROM {source_relation(s, 'valid')})"
        t = recall_table(con, {s: rel}, "valid", ks=(100,))
        w[s] = float(t.loc[t["scope"] == "ALL", "Recall@100"].iloc[0])
    return w


def repeat_counts(ev, m, t):
    """(purchase rows, repeat rows) of members m strictly before days t; a row is a repeat when the member bought the model on an
    earlier day. m = -1 has none."""
    pair = ev.m.astype(np.int64) * len(ev.items) + ev.i
    order = np.lexsort((ev.day, pair))
    p_sorted, d_sorted = pair[order], ev.day[order]
    start = np.r_[True, p_sorted[1:] != p_sorted[:-1]]
    first = np.empty(len(pair), np.int64)
    first[order] = np.maximum.accumulate(np.where(start, np.arange(len(pair)), 0))
    cum_rep = np.r_[0, np.cumsum(ev.day > d_sorted[first])]   # events are in ev.key order (member, day, model)
    mm = np.where(m >= 0, m, 0)
    lo, hi = np.searchsorted(ev.key, mm * DAY_BITS), np.searchsorted(ev.key, mm * DAY_BITS + t)
    return np.where(m >= 0, hi - lo, 0), np.where(m >= 0, cum_rep[hi] - cum_rep[lo], 0)


def repeat_share(con, anchors):
    """ρ_u per anchor: smoothed share of repeat rows among the member's purchases before the anchor, / the country mean."""
    out = []
    for country, a in anchors.groupby("country_code"):
        ev = Events.load(con, country)
        t = ((a["anchor_date"] - pd.Timestamp(EPOCH)).dt.days).to_numpy()
        n, rep = repeat_counts(ev, ev.member_index(a["member_id"]), t)
        mean = rep.sum() / max(n.sum(), 1)
        rho = (rep + M["rho_prior"] * mean) / (n + M["rho_prior"])
        out.append(pd.DataFrame({"member_id": a["member_id"].to_numpy(), "anchor_date": a["anchor_date"].dt.date.to_numpy(),
                                 "rho_ratio": np.clip(rho / max(mean, 1e-9), *M["rho_clip"])}))
        del ev
    return pd.concat(out, ignore_index=True)


def mix(con, split, sources, w, policy, rho=None):
    cols = ",\n".join(f"MIN(rk) FILTER (WHERE s = '{s}') AS rank_{s}" for s in sources)
    parts = " UNION ALL ".join(f"SELECT *, '{s}' AS s FROM {source_relation(s, split)}" for s in sources)
    con.register("_w", pd.DataFrame({"s": list(w), "w": list(w.values())}))
    r1 = {"per_member": "w.w * COALESCE(rho.rho_ratio, 1.0)", "r1_first": "1e6"}.get(policy, "w.w")
    if policy == "per_member":
        con.register("_rho", rho)
    rho_join = "LEFT JOIN _rho rho USING (member_id, anchor_date)" if policy == "per_member" else ""
    learned = [s for s in sources if s not in BASE_SOURCES]
    meta = " UNION ALL ".join(f"SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, fit_cutoff, source_ts_max "
                              f"FROM read_parquet('{ml_path('candidates', s, '*.parquet')}') WHERE split = '{split}'" for s in learned)
    df = con.execute(f"""
        WITH src AS ({parts}),
        keyed AS (SELECT src.*, (rk - 0.5) / CASE WHEN s = 'r1' THEN {r1} ELSE w.w END AS key
                  FROM src JOIN _w w USING (s) {rho_join}),
        agg AS (SELECT member_id, anchor_date, model_code, MIN(key) AS key, {cols} FROM keyed GROUP BY ALL),
        meta AS (SELECT member_id, anchor_date, MAX(fit_cutoff) AS fit_cutoff, MAX(source_ts_max) AS source_ts_max
                 FROM ({meta}) GROUP BY ALL),
        g AS (SELECT member_id, country_code, CAST(anchor_date AS DATE) AS anchor_date, split, in_train_sample
              FROM lh.gold.anchor_grid WHERE is_used AND split = '{split}')
        SELECT g.country_code, g.split, g.in_train_sample, agg.*, meta.fit_cutoff, meta.source_ts_max,
               ROW_NUMBER() OVER (PARTITION BY agg.member_id, agg.anchor_date ORDER BY agg.key, agg.model_code) AS mix_rank
        FROM agg JOIN g USING (member_id, anchor_date) LEFT JOIN meta USING (member_id, anchor_date)
        QUALIFY mix_rank <= {int(M['k_max'])}""").df()
    con.unregister("_w")
    if policy == "per_member":
        con.unregister("_rho")
    return df.drop(columns=["key"])


def mixed_relation(policy, split, k):
    return (f"(SELECT member_id, anchor_date, model_code, -mix_rank AS score "
            f"FROM read_parquet('{ml_path('candidates', 'mix_' + policy, '*.parquet')}') WHERE split = '{split}' AND mix_rank <= {int(k)})")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policies", default="fixed,per_member")
    ap.add_argument("--splits", default="train,valid,test")
    a = ap.parse_args()
    con = connect(threads=int(os.environ.get("DUCKDB_THREADS", 16)))
    con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY_MIX', '120GB')}'")
    sources = list(BASE_SOURCES) + learned_sources()
    w = weights(con, sources)
    print("weights (valid Recall@100):", {k: round(v, 4) for k, v in w.items()}, flush=True)
    pd.DataFrame({"source": list(w), "weight": list(w.values())}).to_csv(ml_path("report", "mixer_weights.csv"), index=False)
    policies = a.policies.split(",")
    for split in a.splits.split(","):
        rho = None
        if "per_member" in policies:
            anchors = con.execute(f"SELECT member_id, country_code, anchor_date FROM lh.gold.anchor_grid WHERE is_used AND split = '{split}'").df()
            anchors["anchor_date"] = pd.to_datetime(anchors["anchor_date"])
            rho = repeat_share(con, anchors)
        for policy in policies:
            t0 = time.time()
            df = mix(con, split, sources, w, policy, rho)
            out = os.path.dirname(ml_path("candidates", f"mix_{policy}", "_"))
            for country, part in df.groupby("country_code"):
                part.to_parquet(os.path.join(out, f"{split}_{country}.parquet"), index=False)
            print(f"  {policy} {split}: {df[['member_id', 'anchor_date']].drop_duplicates().shape[0]:,} anchors, {len(df):,} rows, "
                  f"{time.time() - t0:.0f}s", flush=True)
    con.close()


if __name__ == "__main__":
    sys.exit(main())
