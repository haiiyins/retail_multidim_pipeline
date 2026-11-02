"""Shared machinery of the learned candidate sources R6–R10 (plan §5.1, rolling protocol D8).

A source is fitted per country at a cutoff c (ml/common/pit.py) on purchases dated strictly before c, over a universe of the top
universe.size models by buyers in the universe.window_days before c (t28b: 97 % of the positives rank inside the top 5 000). A member is
scored at anchor t from her purchases strictly before t with the model of cutoff_for(t); train anchors before FIRST_CUTOFF and members
without a purchase of a universe model get no candidates. Output: data/ml/candidates/<source>/<country>_<cutoff>.parquet, at most
n_out rows per anchor after the gold.anchor_model_grid filter applied to R1–R5, with fit_cutoff, source_ts_max (latest purchase read)
and model_version; view ml.cand_<source>.
Usage: python ml/retrieval/<source>.py --tune [--trials N]   (valid, objective unconditional Recall@100)
       python ml/retrieval/<source>.py --build               (every split, tuned parameters when they exist)"""
import argparse, datetime as dt, glob, json, os, sys, time
import numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, load_config, ml_path, publish_view
from ml.common.pit import assert_pit, cutoff_for
from ml.common.registry import Run, config_hash
from ml.common.tuning import tune
from ml.eval.protocol import MAIN_COUNTRIES, build_positives, evaluate

CFG = load_config("retrieval")
EPOCH = dt.date(1970, 1, 1)
DAY_BITS = 1 << 16
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
SPLITS = ("train", "valid", "test")
KS = (20, 50, 100)


def day_num(d):
    return (pd.Timestamp(d).date() - EPOCH).days


class Events:
    """Purchases of one country, one row per member × model × day, as integer arrays sorted by (member, day, model)."""

    def __init__(self, country, members, items, m, i, day, ts):
        self.country, self.members, self.items = country, pd.Index(members), np.asarray(items)
        order = np.lexsort((i, day, m))
        self.m, self.i, self.day, self.ts = (np.asarray(x)[order] for x in (m, i, day, ts))
        self.key = self.m.astype(np.int64) * DAY_BITS + self.day

    @classmethod
    def load(cls, con, country):
        con.execute("""CREATE OR REPLACE TEMP TABLE _ev AS
            SELECT member_id, model_code, transaction_date AS d, MAX(transaction_ts_local) AS ts
            FROM lh.silver.slv_fact_sales_line
            WHERE country_code = ? AND member_id IS NOT NULL AND model_code IS NOT NULL GROUP BY ALL""", [country])
        con.execute("CREATE OR REPLACE TEMP TABLE _mem AS SELECT member_id, (ROW_NUMBER() OVER (ORDER BY member_id) - 1)::INT AS m "
                    "FROM (SELECT DISTINCT member_id FROM _ev)")
        con.execute("CREATE OR REPLACE TEMP TABLE _itm AS SELECT model_code, (ROW_NUMBER() OVER (ORDER BY model_code) - 1)::INT AS i "
                    "FROM (SELECT DISTINCT model_code FROM _ev)")
        members = con.execute("SELECT member_id FROM _mem ORDER BY m").df()["member_id"]
        items = con.execute("SELECT model_code FROM _itm ORDER BY i").df()["model_code"]
        r = con.execute("""SELECT m.m, i.i, date_diff('day', DATE '1970-01-01', e.d)::INT AS day,
                                  epoch_us(COALESCE(e.ts, CAST(e.d AS TIMESTAMP))) AS ts
                           FROM _ev e JOIN _mem m USING (member_id) JOIN _itm i USING (model_code)""").fetchnumpy()
        con.execute("DROP TABLE _ev; DROP TABLE _mem; DROP TABLE _itm")
        return cls(country, members, items, *(np.asarray(r[k]) for k in ("m", "i", "day", "ts")))

    def member_index(self, member_ids):
        return self.members.get_indexer(member_ids).astype(np.int64)

    def before(self, cutoff, window_days=None):
        c = day_num(cutoff)
        sel = self.day < c
        if window_days:
            sel &= self.day >= c - window_days
        return sel

    def history(self, m, day):
        """(row, event index) of every purchase of member m[row] strictly before day[row]; m = -1 has no history."""
        base = m * DAY_BITS
        lo, hi = np.searchsorted(self.key, base), np.searchsorted(self.key, base + day)
        n = np.where(m >= 0, hi - lo, 0)
        row = np.repeat(np.arange(len(m)), n)
        idx = np.arange(n.sum()) - np.repeat(np.cumsum(n) - n, n) + np.repeat(lo, n)
        return row, idx


class Universe:
    def __init__(self, ev, cutoff, size=None, window_days=None):
        size, window_days = size or CFG["universe"]["size"], window_days or CFG["universe"]["window_days"]
        sel = ev.before(cutoff, window_days)
        n_items = len(ev.items)
        pairs = np.unique(ev.m[sel].astype(np.int64) * n_items + ev.i[sel])
        buyers = np.bincount(pairs % n_items, minlength=n_items)
        top = np.argsort(-buyers, kind="stable")[:size]
        self.items = top[buyers[top] > 0]
        self.size = len(self.items)
        self.pos = np.full(n_items, -1, np.int64)
        self.pos[self.items] = np.arange(self.size)


class Query:
    """A batch of anchors: their purchases strictly before the anchor date, restricted to the universe (row, item, days_before),
    and source_ts_max over every purchase read (also outside the universe)."""

    def __init__(self, ev, uni, m, day):
        row, idx = ev.history(m, day)
        self.n = len(m)
        self.source_ts_max = np.full(self.n, np.iinfo(np.int64).min)
        np.maximum.at(self.source_ts_max, row, ev.ts[idx])
        u = uni.pos[ev.i[idx]]
        keep = u >= 0
        self.row, self.item, self.days_before = row[keep], u[keep], (day[row] - ev.day[idx])[keep]
        self.has_history = np.bincount(self.row, minlength=self.n) > 0


class Source:
    """prepare(): parameter-free state per country × cutoff (cached across tuning trials); fit(): the model for given parameters;
    scores(): (n, universe) tensor on DEVICE for a Query."""
    name, version = "", 1

    def prepare(self, ev, uni, cutoff):
        return None

    def fit(self, prep, params, ev, uni, cutoff):
        raise NotImplementedError

    def scores(self, model, q):
        raise NotImplementedError


def load_anchors(con, splits, countries):
    sp = ", ".join(f"'{s}'" for s in splits)
    cc = ", ".join(f"'{c}'" for c in countries)
    a = con.execute(f"""SELECT member_id, country_code, anchor_date, split FROM lh.gold.anchor_grid
                        WHERE is_used AND split IN ({sp}) AND country_code IN ({cc}) ORDER BY country_code, anchor_date, member_id""").df()
    a["anchor_date"] = pd.to_datetime(a["anchor_date"])
    cut = {pd.Timestamp(d): cutoff_for(pd.Timestamp(d).date()) for d in a["anchor_date"].unique()}
    a["fit_cutoff"] = pd.to_datetime(a["anchor_date"].map(cut))
    return a[a["fit_cutoff"].notna()]


def generate(src, params, con, splits, countries, events, cache=None):
    """Yield one candidate DataFrame per country × cutoff. events(country) -> Events; cache keeps (Universe, prep) across calls."""
    n_out, chunk = CFG["n_out"], CFG["chunk"]
    version = f"{src.name}-v{src.version}-{config_hash(params)}"
    anchors = load_anchors(con, splits, countries)
    for country, a_c in anchors.groupby("country_code", sort=True):
        ev = events(country)
        for cutoff, a in a_c.groupby("fit_cutoff", sort=True):
            key = (country, cutoff)
            if cache is not None and key in cache:
                uni, prep = cache[key]
            else:
                uni = Universe(ev, cutoff)
                prep = src.prepare(ev, uni, cutoff)
                if cache is not None:
                    cache[key] = (uni, prep)
            model = src.fit(prep, params, ev, uni, cutoff)
            m = ev.member_index(a["member_id"])
            day = ((a["anchor_date"].dt.normalize() - pd.Timestamp(EPOCH)).dt.days).to_numpy()
            k = min(n_out + 50, uni.size)   # slack for the anchor_model_grid filter
            rows, items, vals, ts = [], [], [], []
            for s in range(0, len(a), chunk):
                q = Query(ev, uni, m[s:s + chunk], day[s:s + chunk])
                with torch.no_grad():
                    sc = src.scores(model, q)
                    sc[~torch.from_numpy(q.has_history).to(sc.device)] = -torch.inf
                    v, ix = torch.topk(sc, k, dim=1)
                v, ix = v.float().cpu().numpy(), ix.cpu().numpy()
                ok = np.isfinite(v)
                r = np.broadcast_to(np.arange(q.n)[:, None], v.shape)[ok]
                rows.append(r + s)
                items.append(uni.items[ix[ok]])
                vals.append(v[ok])
                ts.append(q.source_ts_max[r])
            rows = np.concatenate(rows)
            part = pd.DataFrame({"member_id": a["member_id"].to_numpy()[rows], "country_code": country,
                                 "anchor_date": a["anchor_date"].to_numpy()[rows], "split": a["split"].to_numpy()[rows],
                                 "model_code": ev.items[np.concatenate(items)], "score": np.concatenate(vals),
                                 "fit_cutoff": cutoff, "source_ts_max": pd.to_datetime(np.concatenate(ts), unit="us"),
                                 "model_version": version})
            yield country, cutoff, grid_filter(con, part, n_out)


def grid_filter(con, part, n_out):
    con.register("_part", part)
    out = con.execute(f"""
        SELECT c.member_id, c.country_code, CAST(c.anchor_date AS DATE) AS anchor_date, c.split, c.model_code, c.score,
               ROW_NUMBER() OVER (PARTITION BY c.member_id, c.anchor_date ORDER BY c.score DESC, c.model_code) AS rank,
               CAST(c.fit_cutoff AS DATE) AS fit_cutoff, c.source_ts_max, c.model_version
        FROM _part c SEMI JOIN lh.gold.anchor_model_grid g
          ON g.country_code = c.country_code AND g.anchor_date = CAST(c.anchor_date AS DATE) AND g.model_code = c.model_code
        QUALIFY rank <= {int(n_out)}""").df()
    con.unregister("_part")
    return out


ALL_K = 10_000   # a rank no list reaches: Recall@ALL_K is the share of positives anywhere in the list


def recall_table(con, sources, split, ks=KS, ranked=None):
    """Unconditional recall per source relation (name -> SQL relation with member_id, anchor_date, model_code, score), member means.
    cand / cand_repeat / cand_explore: share of the positives anywhere in the list; Recall@K only for the names in `ranked`
    (a union of sources has no common score)."""
    pos = f"read_parquet('{build_positives(con, split, CFG['delta'])}')"
    rows = []
    for name, rel in sources.items():
        res = evaluate(con, rel, pos, ks=ks + (ALL_K,))
        size = con.execute(f"SELECT COUNT(*) / COUNT(DISTINCT (member_id, anchor_date)) FROM {rel}").fetchone()[0]
        for scope, d in (("ALL", res), ("MAIN (TH+VN)", res[res["country_code"].isin(MAIN_COUNTRIES)])):
            mean = lambda c: d.groupby("member_id")[c].mean().mean()
            row = {"split": split, "source": name, "scope": scope, "anchors": len(d), "list_size": size,
                   "cand": mean(f"Recall@{ALL_K}"), "cand_repeat": mean(f"recall_repeat@{ALL_K}"),
                   "cand_explore": mean(f"recall_explore@{ALL_K}")}
            for k in ks:
                row[f"Recall@{k}"] = mean(f"Recall@{k}") if ranked is None or name in ranked else np.nan
            rows.append(row)
    return pd.DataFrame(rows)


def union_relation(rels):
    parts = " UNION ALL ".join(f"SELECT member_id, anchor_date, model_code FROM {r}" for r in rels)
    return f"(SELECT DISTINCT member_id, anchor_date, model_code, 0.0 AS score FROM ({parts}))"


def candidates_relation(name, split):
    return (f"(SELECT member_id, anchor_date, model_code, score FROM read_parquet('{ml_path('candidates', name, '*.parquet')}') "
            f"WHERE split = '{split}')")


def objective_value(con, cands, metric="Recall@100"):
    con.register("_cands", cands)
    res = evaluate(con, "_cands", f"read_parquet('{build_positives(con, 'valid', CFG['delta'])}')", ks=KS)
    con.unregister("_cands")
    return float(res.groupby("member_id")[metric].mean().mean())


def tuned_params(name):
    defaults = dict(CFG[name]["params"])
    path = ml_path("tuning", f"{name}.parquet")
    if os.path.exists(path):
        t = pd.read_parquet(path)
        t = t[t["state"] == "COMPLETE"]
        if len(t):
            defaults.update(json.loads(t.loc[t["value"].idxmax(), "params"]))
    return defaults


def baseline_relation(split, k=200):
    """R1–R5 of gold.gld_candidates (score = −candidate_rank) for the comparison and the union."""
    return f"""(SELECT member_id, anchor_date, model_code, -candidate_rank AS score FROM lh.gold.gld_candidates
               WHERE split = '{split}' AND candidate_rank <= {int(k)})"""


def main(src):
    ap = argparse.ArgumentParser()
    ap.add_argument("--tune", action="store_true")
    ap.add_argument("--trials", type=int, default=None)
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--countries", default="SG,TH,VN")
    a = ap.parse_args()
    countries = a.countries.split(",")
    con = connect()
    loaded = {}

    def events(country):
        if country not in loaded:
            t0 = time.time()
            if not a.tune:   # one country in memory while building, all three while tuning
                loaded.clear()
            loaded[country] = Events.load(con, country)
            print(f"  events {country}: {len(loaded[country].m):,} member × model × day rows, {time.time() - t0:.0f}s", flush=True)
        return loaded[country]

    if a.tune:
        cache = {}

        def objective(params, trial):
            full = {**CFG[src.name]["params"], **params}
            cands = pd.concat([p for _, _, p in generate(src, full, con, ["valid"], countries, events, cache)], ignore_index=True)
            value = objective_value(con, cands)
            print(f"  trial {trial.number}: Recall@100 (valid, unconditional) {value:.4f}  {params}", flush=True)
            return value

        study, trials = tune(src.name, objective, n_trials=a.trials, tag="" if a.trials is None else f"_smoke{a.trials}")
        print(trials[["trial", "value", "state", "wall_sec"]].to_string(index=False))
        print(f"best {study.best_value:.4f}  {study.best_params}")

    if a.build:
        params = tuned_params(src.name)
        out_dir = os.path.dirname(ml_path("candidates", src.name, "_"))
        for c in countries:   # countries may be built by parallel processes
            for p in glob.glob(os.path.join(out_dir, f"{c}_*.parquet")):
                os.remove(p)
        with Run(f"cand:{src.name}", config={"retrieval": CFG, "source": src.name, "version": src.version}, params=params) as run:
            for country, cutoff, part in generate(src, params, con, SPLITS, countries, events):
                path = os.path.join(out_dir, f"{country}_{cutoff.date()}.parquet")
                part.to_parquet(path, index=False)
                print(f"  {country} cutoff {cutoff.date()}: {part[['member_id', 'anchor_date']].drop_duplicates().shape[0]:,} anchors, "
                      f"{len(part):,} rows", flush=True)
            run.metrics["pit"] = assert_pit(con, f"read_parquet('{out_dir}/*.parquet')")
            t = pd.concat([recall_table(con, {src.name: candidates_relation(src.name, s), "R1-R5@200": baseline_relation(s),
                                              f"R1-R5@200 ∪ {src.name}": union_relation([baseline_relation(s), candidates_relation(src.name, s)])},
                                        s, ranked={src.name, "R1-R5@200"}) for s in ("valid", "test")], ignore_index=True)
            run.metrics["recall"] = t.round(4).to_dict("records")
            run.artifacts["candidates"] = out_dir
            show(t, ml_path("report", f"cand_{src.name}.md"))
        con.close()
        publish_view(f"cand_{src.name}", os.path.join(out_dir, "*.parquet"))


def show(t, path):
    with open(path, "w") as f:
        f.write(t.round(4).to_markdown(index=False) + "\n")
    pd.set_option("display.width", 250)
    print(t.drop(columns=["anchors"]).round(4).to_string(index=False))
    print(f"report {path}")
