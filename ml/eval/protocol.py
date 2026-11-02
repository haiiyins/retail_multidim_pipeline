"""ML-02 — Unconditional evaluation protocol (ml/DECISIONS.md D3), table t28.

Unit: an is_used anchor of the split with at least one non-returned purchase in (anchor, anchor + Δ]. Positives: every model bought in
that window (the label rule of gld_ranking_dataset: returns netted on transaction × model), whether or not a candidate source proposed
it; a positive outside the scored list is a miss. A positive is repeat when the member had already bought the model on or before the
anchor date, explore otherwise (NBR Reality Check, TOIS 2023). IDCG is computed over all positives.
mode=conditional keeps only positives inside the scored list and anchors with at least one of them: the KTXLDL measure of
evaluation/train_eval_lambdarank.py, kept next to the new one in t28 to show what it hid.

Scores: data/ml/scores/<name>_<split>_d<Δ>.parquet with member_id, anchor_date, model_code, score (−inf = not recommendable). Anchors
without scores still count, with every metric at 0.
Usage: python ml/eval/protocol.py --reeval p1_frozen --out t28 [--delta 30] [--split test] [--legacy data/audit/results_full_d30.parquet]"""
import argparse, os, sys, duckdb, numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect

KS = (10, 20, 50, 100, 200)
REPORT_METRICS = ["HR@10", "NDCG@10", "NDCG@20", "MRR@20", "Recall@20", "Recall@50", "recall_repeat@20", "recall_explore@20",
                  "PHR_repeat@20", "PHR_explore@20", "cand_recall", "repeat_share"]
MAIN_COUNTRIES = ("TH", "VN")


def build_positives(con, split, delta):
    """Positives of every is_used anchor of the split, cached as Parquet (the lakehouse stays read-only)."""
    path = os.path.join(ML_DIR, "eval", f"positives_{split}_d{delta}.parquet")
    if os.path.exists(path):
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    con.execute(f"""COPY (
        WITH a AS (SELECT member_id, country_code, anchor_date FROM lh.gold.anchor_grid WHERE split = '{split}' AND is_used),
        buy AS (SELECT f.member_id, f.model_code, f.transaction_date FROM lh.silver.slv_fact_sales_line f
                WHERE f.member_id IS NOT NULL AND f.model_code IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM lh.silver.slv_fact_returns r
                                  WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code)),
        first_buy AS (SELECT member_id, model_code, MIN(transaction_date) AS first_d FROM buy GROUP BY ALL)
        SELECT a.member_id, a.country_code, a.anchor_date, b.model_code,
               MIN(b.transaction_date) - a.anchor_date AS days_to_buy,
               ANY_VALUE(fb.first_d) <= a.anchor_date AS is_repeat
        FROM a JOIN buy b ON b.member_id = a.member_id AND b.transaction_date > a.anchor_date
                         AND b.transaction_date <= a.anchor_date + {int(delta)}
        JOIN first_buy fb ON fb.member_id = b.member_id AND fb.model_code = b.model_code
        GROUP BY a.member_id, a.country_code, a.anchor_date, b.model_code
    ) TO '{path}' (FORMAT parquet)""")
    return path


def anchor_counts(con, scores_src, positives_src, conditional=False, ks=KS):
    """Per-anchor counts: positives (all / repeat / in the scored list), hits and DCG at each K, rank of the first hit.
    scores_src / positives_src are anything DuckDB can select from (a registered view, read_parquet(...))."""
    hit_cols = ",\n".join(
        f"COUNT(*) FILTER (WHERE rnk <= {k}) AS hits_{k}, COUNT(*) FILTER (WHERE rnk <= {k} AND is_repeat) AS hits_rep_{k}, "
        f"COALESCE(SUM(1.0 / log2(rnk + 1)) FILTER (WHERE rnk <= {k}), 0) AS dcg_{k}" for k in ks)
    return con.execute(f"""
        WITH s AS (SELECT member_id, anchor_date, model_code,
                          ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, model_code) AS rnk
                   FROM (SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, model_code, score FROM {scores_src})
                   WHERE score > '-inf'::DOUBLE),
        p AS (SELECT p.member_id, CAST(p.anchor_date AS DATE) AS anchor_date, p.country_code, p.model_code, p.is_repeat, s.rnk
              FROM {positives_src} p LEFT JOIN s ON s.member_id = p.member_id AND s.anchor_date = CAST(p.anchor_date AS DATE)
                                               AND s.model_code = p.model_code
              {"WHERE s.rnk IS NOT NULL" if conditional else ""})
        SELECT member_id, anchor_date, ANY_VALUE(country_code) AS country_code, COUNT(*) AS n_pos,
               COUNT(*) FILTER (WHERE is_repeat) AS n_rep, COUNT(rnk) AS n_in_list, MIN(rnk) AS first_rank,
               {hit_cols}
        FROM p GROUP BY member_id, anchor_date ORDER BY member_id, anchor_date""").df()


def metrics_from_counts(c, ks=KS):
    """Per-anchor metrics from anchor_counts(); repeat / explore metrics are NaN for anchors without such positives."""
    disc = 1.0 / np.log2(np.arange(2, max(ks) + 2))
    cum = np.cumsum(disc)
    n_pos = c["n_pos"].to_numpy()
    n_rep = c["n_rep"].to_numpy()
    n_exp = n_pos - n_rep
    first = c["first_rank"].to_numpy(dtype=float)
    out = c[["member_id", "anchor_date", "country_code"]].copy()
    for k in ks:
        hits = c[f"hits_{k}"].to_numpy()
        hits_rep = c[f"hits_rep_{k}"].to_numpy()
        hits_exp = hits - hits_rep
        idcg = cum[np.minimum(n_pos, k) - 1]
        out[f"HR@{k}"] = (hits > 0).astype(float)
        out[f"MRR@{k}"] = np.where(first <= k, 1.0 / np.where(np.isnan(first), 1, first), 0.0)
        out[f"NDCG@{k}"] = c[f"dcg_{k}"].to_numpy() / idcg
        out[f"Recall@{k}"] = hits / n_pos
        with np.errstate(divide="ignore", invalid="ignore"):
            out[f"recall_repeat@{k}"] = np.where(n_rep > 0, hits_rep / n_rep, np.nan)
            out[f"recall_explore@{k}"] = np.where(n_exp > 0, hits_exp / n_exp, np.nan)
        out[f"PHR_repeat@{k}"] = np.where(n_rep > 0, (hits_rep > 0).astype(float), np.nan)
        out[f"PHR_explore@{k}"] = np.where(n_exp > 0, (hits_exp > 0).astype(float), np.nan)
    out["cand_recall"] = c["n_in_list"].to_numpy() / n_pos
    out["repeat_share"] = n_rep / n_pos
    out["n_pos"] = n_pos
    return out


def evaluate(con, scores_src, positives_src, conditional=False, ks=KS):
    return metrics_from_counts(anchor_counts(con, scores_src, positives_src, conditional, ks), ks)


def member_bootstrap(res, metric, b=500, seed=0):
    """Mean over members of per-member means, with a 95 % member-level bootstrap interval (NaN rows ignored)."""
    m = res.groupby("member_id")[metric].mean().dropna().to_numpy()
    if len(m) == 0:
        return np.nan, np.nan, np.nan
    rng = np.random.default_rng(seed)
    boots = np.array([m[rng.integers(0, len(m), len(m))].mean() for _ in range(b)])
    return m.mean(), np.percentile(boots, 2.5), np.percentile(boots, 97.5)


def scopes(res, segments):
    r = res.merge(segments, on=["member_id", "anchor_date"], how="left")
    yield "ALL", r
    yield "MAIN (TH+VN)", r[r["country_code"].isin(MAIN_COUNTRIES)]
    for cc in sorted(r["country_code"].unique()):
        yield cc, r[r["country_code"] == cc]
    for s in ("new", "mid", "loyal"):
        yield f"segment:{s}", r[r["segment"] == s]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--reeval", required=True, help="score set name: data/ml/scores/<name>_<split>_d<Δ>.parquet")
    ap.add_argument("--out", default="t28")
    ap.add_argument("--split", default="test")
    ap.add_argument("--delta", type=int, default=30)
    ap.add_argument("--legacy", default="", help="per-anchor results of evaluation/train_eval_lambdarank.py to check the conditional mode against")
    a = ap.parse_args()
    b = int(os.environ.get("BOOT_N", 500))
    con = connect()
    scores = os.path.join(ML_DIR, "scores", f"{a.reeval}_{a.split}_d{a.delta}.parquet")
    pos = build_positives(con, a.split, a.delta)
    src_s, src_p = f"read_parquet('{scores}')", f"read_parquet('{pos}')"
    res = {mode: evaluate(con, src_s, src_p, conditional=(mode == "conditional")) for mode in ("conditional", "unconditional")}
    out_dir = os.path.join(ML_DIR, "eval")
    for mode, r in res.items():
        r.to_parquet(os.path.join(out_dir, f"results_{a.reeval}_{a.split}_d{a.delta}_{mode}.parquet"), index=False)

    if a.legacy:
        old = pd.read_parquet(a.legacy)
        old["anchor_date"] = pd.to_datetime(old["anchor_date"])
        new = res["conditional"].assign(anchor_date=lambda d: pd.to_datetime(d["anchor_date"]))
        j = old.merge(new, on=["member_id", "anchor_date"], suffixes=("_old", "_new"))
        print(f"legacy check: anchors old {len(old):,} / new conditional {len(new):,} / matched {len(j):,}")
        for m in ("HR@10", "MRR@10", "NDCG@10", "HR@20", "NDCG@20", "Recall@50"):
            print(f"  {m:<10} mean old {j[m + '_old'].mean():.6f}  new {j[m + '_new'].mean():.6f}  "
                  f"max |diff| {np.abs(j[m + '_old'] - j[m + '_new']).max():.2e}")

    seg = con.execute("""SELECT member_id, anchor_date, CASE WHEN tx_365d <= 1 THEN 'new' WHEN tx_365d >= 3 THEN 'loyal' ELSE 'mid' END AS segment
                         FROM lh.gold.gld_fs_member""").df()
    seg["anchor_date"] = pd.to_datetime(seg["anchor_date"])
    rows = []
    for mode, r in res.items():
        r = r.assign(anchor_date=pd.to_datetime(r["anchor_date"]))
        for scope, d in scopes(r, seg):
            row = {"mode": mode, "scope": scope, "anchors": len(d), "members": d["member_id"].nunique()}
            for m in REPORT_METRICS:
                mean, lo, hi = member_bootstrap(d, m, b)
                row[m], row[m + "_lo"], row[m + "_hi"] = mean, lo, hi
            rows.append(row)
    t = pd.DataFrame(rows)
    rep_dir = os.path.join(ML_DIR, "report")
    os.makedirs(rep_dir, exist_ok=True)
    t.to_csv(os.path.join(rep_dir, f"{a.out}_{a.reeval}_d{a.delta}.csv"), index=False)
    show = t[["mode", "scope", "anchors", "members"] + REPORT_METRICS]
    with open(os.path.join(rep_dir, f"{a.out}_{a.reeval}_d{a.delta}.md"), "w") as f:
        f.write(show.round(4).to_markdown(index=False) + "\n")
    pd.set_option("display.width", 250)
    print(show.round(4).to_string(index=False))
    u = res["unconditional"]
    print(f"unconditional anchors {len(u):,}; without any positive in the scored list {(u['cand_recall'] == 0).mean():.1%}; "
          f"positives repeat {u['repeat_share'].mean():.1%} (anchor mean)")


if __name__ == "__main__":
    sys.exit(main())
