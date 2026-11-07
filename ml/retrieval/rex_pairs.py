"""REX as a ranker feature: the REX score of every (anchor, candidate) pair of ml.candidates_v2, from the REX model of
cutoff_for(anchor) (rolling, like every learned source), on train, valid and test anchors.

  rex_lp    log-probability of the candidate under REX's softmax over the universe (NaN outside the universe or before the first
            cutoff), comparable across anchors
  rex_rank  rank of the candidate in REX's full-universe list (1 = top)

Output: data/ml/rex/pair_scores_<country>.parquet (with fit_cutoff and model_version for assert_pit), then
data/ml/pairs_v2rex/<split>_<country>.parquet = pairs_v2 + rex_lp, rex_rank, the input of gbdt.py / umtr --source v2rex.
Usage: python ml/retrieval/rex_pairs.py --countries TH --score   (one process per country can run in parallel)
       python ml/retrieval/rex_pairs.py --countries TH --pit     (source_ts_max + assert_pit on existing scores)
       python ml/retrieval/rex_pairs.py --join"""
import argparse, glob, os, sys, time
import numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.baselines.nbr import tuned
from ml.common.data import connect, ml_path
from ml.common.pit import assert_pit, cutoff_for
from ml.common.registry import Run, config_hash
from ml.retrieval.base import CFG, DEVICE, EPOCH, Events, Query, Universe, mask_scores
from ml.retrieval.rex import REX

CHUNK = 4096


def anchors(con, country):
    a = con.execute(f"""SELECT DISTINCT member_id, anchor_date FROM read_parquet('{ml_path('candidates_v2', '*.parquet')}')
                        WHERE country_code = '{country}'""").df()
    a["anchor_date"] = pd.to_datetime(a["anchor_date"])
    cut = {d: cutoff_for(pd.Timestamp(d).date()) for d in a["anchor_date"].unique()}
    a["fit_cutoff"] = a["anchor_date"].map(cut)
    return a[a["fit_cutoff"].notna()].sort_values(["fit_cutoff", "member_id", "anchor_date"]).reset_index(drop=True)


def score_country(con, country, params):
    ev = Events.load(con, country)
    items = pd.Index(ev.items)
    src = REX()
    version = f"rex-v{src.version}-{config_hash(params)}"
    a = anchors(con, country)
    cand = con.execute(f"""SELECT member_id, anchor_date, model_code FROM read_parquet('{ml_path('candidates_v2', '*.parquet')}')
                           WHERE country_code = '{country}'""").df()
    cand["anchor_date"] = pd.to_datetime(cand["anchor_date"])
    parts = []
    for cutoff, ac in a.groupby("fit_cutoff", sort=True):
        t0 = time.time()
        uni = Universe(ev, cutoff)
        model = src.fit(src.prepare(ev, uni, cutoff), params, ev, uni, cutoff)
        ac = ac.reset_index(drop=True)
        key = ac[["member_id", "anchor_date"]].assign(row=np.arange(len(ac)))
        cc = cand.merge(key, on=["member_id", "anchor_date"])
        cc = cc.sort_values("row").reset_index(drop=True)
        ii = items.get_indexer(cc["model_code"])
        pos = np.where(ii >= 0, uni.pos[np.maximum(ii, 0)], -1)
        m = ev.member_index(ac["member_id"])
        day = ((ac["anchor_date"] - pd.Timestamp(EPOCH)).dt.days).to_numpy()
        lp = np.full(len(cc), np.nan, np.float32)
        rank = np.full(len(cc), np.nan, np.float32)
        rows = cc["row"].to_numpy()
        for s in range(0, len(ac), CHUNK):
            e = min(s + CHUNK, len(ac))
            q = Query(ev, uni, m[s:e], day[s:e])
            with torch.no_grad():
                sc = mask_scores(src.scores(model, q), q, explore_only=False)
                lo, hi = np.searchsorted(rows, [s, e])
                sel = np.arange(lo, hi)[pos[lo:hi] >= 0]
                if len(sel) == 0:
                    continue
                r = torch.as_tensor(rows[sel] - s, device=DEVICE)
                p = torch.as_tensor(pos[sel], device=DEVICE)
                v = sc[r, p]
                lse = torch.logsumexp(sc, 1)
                order = torch.argsort(sc, 1, descending=True)
                ranks = torch.empty_like(order).scatter_(1, order, torch.arange(1, sc.shape[1] + 1, device=DEVICE).expand_as(order))
                rk = ranks[r, p]
                ok = torch.isfinite(v)
                lp[sel] = torch.where(ok, v - lse[r], torch.nan).cpu().numpy()
                rank[sel] = torch.where(ok, rk.float(), torch.nan).cpu().numpy()
        out = cc[["member_id", "anchor_date", "model_code"]].assign(rex_lp=lp, rex_rank=rank, fit_cutoff=pd.Timestamp(cutoff),
                                                                    model_version=version)
        parts.append(out)
        print(f"  {country} cutoff {pd.Timestamp(cutoff).date()}: {len(ac):,} anchors, {len(cc):,} pairs, "
              f"{np.isfinite(lp).mean():.1%} scored, {time.time() - t0:.0f}s", flush=True)
        del model
        torch.cuda.empty_cache()
    out = pd.concat(parts, ignore_index=True)
    path = ml_path("rex", f"pair_scores_{country}.parquet")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    out.to_parquet(path, index=False)
    return path


def add_source_ts(con, country):
    """source_ts_max of every anchor (latest purchase read, as in Query) added to the pair scores, then assert_pit."""
    path = ml_path("rex", f"pair_scores_{country}.parquet")
    s = pd.read_parquet(path).drop(columns=["source_ts_max"], errors="ignore")
    ev = Events.load(con, country)
    a = s[["member_id", "anchor_date"]].drop_duplicates().reset_index(drop=True)
    day = ((a["anchor_date"] - pd.Timestamp(EPOCH)).dt.days).to_numpy()
    row, idx = ev.history(ev.member_index(a["member_id"]), day)
    ts = np.full(len(a), np.iinfo(np.int64).min)
    np.maximum.at(ts, row, ev.ts[idx])
    a["source_ts_max"] = pd.to_datetime(np.where(ts > np.iinfo(np.int64).min, ts, 0), unit="us")
    s = s.merge(a, on=["member_id", "anchor_date"])
    s.to_parquet(path, index=False)
    return assert_pit(con, f"read_parquet('{path}')")


def join(con):
    os.makedirs(os.path.dirname(ml_path("pairs_v2rex", "_")), exist_ok=True)
    for f in sorted(glob.glob(ml_path("pairs_v2", "*.parquet"))):
        split, country = os.path.basename(f)[:-len(".parquet")].split("_")
        out = ml_path("pairs_v2rex", os.path.basename(f))
        con.execute(f"""COPY (SELECT p.*, s.rex_lp, s.rex_rank
                              FROM read_parquet('{f}') p
                              LEFT JOIN read_parquet('{ml_path('rex', f'pair_scores_{country}.parquet')}') s
                                ON s.member_id = p.member_id AND s.anchor_date = CAST(p.anchor_date AS TIMESTAMP)
                               AND s.model_code = p.model_code)
                        TO '{out}' (FORMAT parquet)""")
        n, cov = con.execute(f"SELECT COUNT(*), AVG((rex_lp IS NOT NULL)::INT) FROM read_parquet('{out}')").fetchall()[0]
        print(f"  {split} {country}: {n:,} pairs, rex_lp present {cov:.1%}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--countries", default="SG,TH,VN")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--pit", action="store_true", help="add source_ts_max to existing pair scores and run assert_pit")
    ap.add_argument("--join", action="store_true")
    a = ap.parse_args()
    con = connect(threads=16)
    if a.score:
        params = tuned("rex")
        for country in a.countries.split(","):
            with Run(f"rex_pairs:{country}", config={"retrieval": CFG["rex"], "country": country}, params=params) as run:
                run.artifacts["pair_scores"] = score_country(con, country, params)
                run.metrics["pit"] = add_source_ts(con, country)
    elif a.pit:
        for country in a.countries.split(","):
            print(country, add_source_ts(con, country), flush=True)
    if a.join:
        join(con)


if __name__ == "__main__":
    sys.exit(main())
