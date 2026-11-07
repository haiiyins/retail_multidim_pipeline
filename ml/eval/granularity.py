"""Granularity ladder — the D3 protocol re-run at coarser product levels (secondary tasks, the model level stays the headline).

A level maps every model to one group (supermodel, product nature, retail family, sub-department, department; each model has exactly
one group per level in bronze.dim_item). At level g an anchor's positives are the distinct groups of the models bought in
(anchor, anchor + Δ], returns netted as in protocol.build_positives; a group is repeat when the member had bought any model of it on or
before the anchor date. A model-level score list becomes a group list by keeping each group's best model score, so the ranking is the
model list with duplicates of a group removed. Unit, unconditional misses, IDCG over all positives and the member bootstrap are those
of protocol.py. A score set trained at a level (rex_<level>_nbr, levels.native_level) already ranks groups and is only evaluated
at that level.
Usage: python ml/eval/granularity.py --models rex_nbr,fuse_rex_nbr_p3_onehead [--levels nature,department] [--split test] [--out t40]"""
import argparse, os, sys, numpy as np, pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect
from ml.common.levels import LEVELS, group_map, native_level
from ml.eval.protocol import MAIN_COUNTRIES, member_bootstrap, metrics_from_counts

KS = (10, 20, 50)
METRICS = ["HR@10", "NDCG@20", "Recall@20", "recall_repeat@20", "recall_explore@20", "cand_recall", "repeat_share"]


def group_positives(con, split, delta, level, gmap):
    path = os.path.join(ML_DIR, "eval", f"positives_{split}_d{delta}_{level}.parquet")
    if os.path.exists(path):
        return path
    con.execute(f"""COPY (
        WITH g AS (SELECT model_code, {level} AS grp FROM read_parquet('{gmap}')),
        a AS (SELECT member_id, country_code, anchor_date FROM lh.gold.anchor_grid WHERE split = '{split}' AND is_used),
        buy AS (SELECT f.member_id, g.grp, f.transaction_date FROM lh.silver.slv_fact_sales_line f JOIN g USING (model_code)
                WHERE f.member_id IS NOT NULL
                  AND NOT EXISTS (SELECT 1 FROM lh.silver.slv_fact_returns r
                                  WHERE r.transaction_id = f.transaction_id AND r.model_code = f.model_code)),
        first_buy AS (SELECT member_id, grp, MIN(transaction_date) AS first_d FROM buy GROUP BY ALL)
        SELECT a.member_id, a.country_code, a.anchor_date, b.grp, ANY_VALUE(fb.first_d) <= a.anchor_date AS is_repeat
        FROM a JOIN buy b ON b.member_id = a.member_id AND b.transaction_date > a.anchor_date
                         AND b.transaction_date <= a.anchor_date + {int(delta)}
        JOIN first_buy fb ON fb.member_id = b.member_id AND fb.grp = b.grp
        GROUP BY a.member_id, a.country_code, a.anchor_date, b.grp
    ) TO '{path}' (FORMAT parquet)""")
    return path


def group_counts(con, scores, positives, level, gmap, native=False):
    hit_cols = ",\n".join(
        f"COUNT(*) FILTER (WHERE rnk <= {k}) AS hits_{k}, COUNT(*) FILTER (WHERE rnk <= {k} AND is_repeat) AS hits_rep_{k}, "
        f"COALESCE(SUM(1.0 / log2(rnk + 1)) FILTER (WHERE rnk <= {k}), 0) AS dcg_{k}" for k in KS)
    g = (f"SELECT DISTINCT {level} AS model_code, {level} AS grp FROM read_parquet('{gmap}')" if native
         else f"SELECT model_code, {level} AS grp FROM read_parquet('{gmap}')")
    return con.execute(f"""
        WITH g AS ({g}),
        sg AS (SELECT member_id, CAST(anchor_date AS DATE) AS anchor_date, grp, MAX(score) AS score
               FROM read_parquet('{scores}') JOIN g USING (model_code) WHERE score > '-inf'::DOUBLE GROUP BY ALL),
        s AS (SELECT *, ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY score DESC, grp) AS rnk FROM sg),
        p AS (SELECT p.member_id, p.anchor_date, p.country_code, p.grp, p.is_repeat, s.rnk FROM read_parquet('{positives}') p
              LEFT JOIN s ON s.member_id = p.member_id AND s.anchor_date = p.anchor_date AND s.grp = p.grp)
        SELECT member_id, anchor_date, ANY_VALUE(country_code) AS country_code, COUNT(*) AS n_pos,
               COUNT(*) FILTER (WHERE is_repeat) AS n_rep, COUNT(rnk) AS n_in_list, MIN(rnk) AS first_rank, {hit_cols}
        FROM p GROUP BY member_id, anchor_date ORDER BY member_id, anchor_date""").df()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", required=True)
    ap.add_argument("--levels", default=",".join(LEVELS))
    ap.add_argument("--split", default="test")
    ap.add_argument("--delta", type=int, default=30)
    ap.add_argument("--out", default="t40_granularity")
    a = ap.parse_args()
    b = int(os.environ.get("BOOT_N", 500))
    con = connect()
    gmap = group_map(con)
    rows = []
    for level in a.levels.split(","):
        pos = group_positives(con, a.split, a.delta, level, gmap)
        groups = con.execute(f"SELECT COUNT(DISTINCT grp) FROM read_parquet('{pos}')").fetchone()[0]
        for name in a.models.split(","):
            native = native_level(name)
            if native not in (None, level):
                continue
            scores = os.path.join(ML_DIR, "scores", f"{name}_{a.split}_d{a.delta}.parquet")
            res = metrics_from_counts(group_counts(con, scores, pos, level, gmap, native is not None), KS)
            res.to_parquet(os.path.join(ML_DIR, "eval", f"results_{name}_{a.split}_d{a.delta}_{level}.parquet"), index=False)
            d = res[res["country_code"].isin(MAIN_COUNTRIES)]
            row = {"level": level, "groups_bought": groups, "model": name, "anchors": len(d),
                   "pos_per_anchor": d["n_pos"].mean()}
            for m in METRICS:
                row[m], row[m + "_lo"], row[m + "_hi"] = member_bootstrap(d, m, b)
            rows.append(row)
            print(f"{level:<10} {name:<28} NDCG@20 {row['NDCG@20']:.4f} [{row['NDCG@20_lo']:.4f}, {row['NDCG@20_hi']:.4f}]", flush=True)
    t = pd.DataFrame(rows)
    rep = os.path.join(ML_DIR, "report")
    t.to_csv(os.path.join(rep, f"{a.out}.csv"), index=False)
    show = t[["level", "groups_bought", "model", "anchors", "pos_per_anchor"] + METRICS]
    with open(os.path.join(rep, f"{a.out}.md"), "w") as f:
        f.write(f"# {a.out} — D3 at coarser product levels ({a.split}, TH + VN, Δ = {a.delta})\n\n")
        f.write(show.round(4).to_markdown(index=False) + "\n")
    print(show.round(4).to_string(index=False))


if __name__ == "__main__":
    sys.exit(main())
