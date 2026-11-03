"""ML-14 — ml.candidates_v2: the mixed list of one mixer policy cut at mixer.k, in the column layout of gold.gld_candidates so that the
Gold pair SQL runs on it unchanged (ml/common/pairs.py): r1 … r5 flags and score_r1 … score_r5 (R4 is always 0, ML-04),
priority_source (6 = proposed by learned sources only), candidate_rank = mix_rank; plus rank_<source> of every mixed source (NULL when
the source does not propose the model) and fit_cutoff / source_ts_max of the learned sources. The policy defaults to the one with the
higher MAIN (TH + VN) valid coverage at mixer.k (t30). Checks: QC-6 point-in-time (pit.assert_pit) and the cap (≤ k rows per anchor).
Usage: python ml/retrieval/build_candidates.py [--policy fixed|per_member] [--k 500 --version v3]   (default k = mixer.k → candidates_v2)"""
import argparse, os, sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, ml_path, publish_view
from ml.common.pit import assert_pit
from ml.retrieval.base import recall_table
from ml.retrieval.mixer import BASE_SOURCES, M, learned_sources, mixed_relation


def pick_policy(con, k):
    best = {}
    for p in ("fixed", "per_member"):
        t = recall_table(con, {p: mixed_relation(p, "valid", k)}, "valid", ks=(100,))
        best[p] = float(t.loc[t["scope"] == "MAIN (TH+VN)", "cand"].iloc[0])
    print("valid MAIN cand@%d:" % k, {p: round(v, 4) for p, v in best.items()})
    return max(best, key=best.get)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--policy", default=None)
    ap.add_argument("--k", type=int, default=int(M["k"]))
    ap.add_argument("--version", default="v2", help="output ml.candidates_<version>")
    a = ap.parse_args()
    k, out_name = a.k, f"candidates_{a.version}"
    con = connect(threads=16)
    con.execute("SET memory_limit='100GB'")
    policy = a.policy or pick_policy(con, k)
    ranks = ", ".join(f"m.rank_{s}" for s in list(BASE_SOURCES) + learned_sources())
    mix = ml_path("candidates", f"mix_{policy}", "*.parquet")
    out_dir = os.path.dirname(ml_path(out_name, "_"))
    os.makedirs(out_dir, exist_ok=True)
    for f in os.listdir(out_dir):
        os.remove(os.path.join(out_dir, f))
    for split, country in con.execute(f"SELECT DISTINCT split, country_code FROM read_parquet('{mix}') ORDER BY ALL").fetchall():
        con.execute(f"""COPY (
            SELECT m.country_code, m.split, m.in_train_sample, m.member_id, CAST(m.anchor_date AS DATE) AS anchor_date, m.model_code,
                   COALESCE(g.r1, 0) AS r1, COALESCE(g.r2, 0) AS r2, COALESCE(g.r3, 0) AS r3, 0 AS r4, COALESCE(g.r5, 0) AS r5,
                   g.score_r1, g.score_r2, g.score_r3, CAST(NULL AS DOUBLE) AS score_r4, g.score_r5,
                   CASE WHEN g.r1 = 1 THEN 1 WHEN g.r3 = 1 THEN 2 WHEN g.r2 = 1 THEN 3 WHEN g.r5 = 1 THEN 5 ELSE 6 END AS priority_source,
                   m.mix_rank AS candidate_rank, {ranks}, m.fit_cutoff, m.source_ts_max
            FROM read_parquet('{mix}') m
            LEFT JOIN lh.gold.gld_candidates g ON g.member_id = m.member_id AND g.anchor_date = m.anchor_date AND g.model_code = m.model_code
            WHERE m.split = '{split}' AND m.country_code = '{country}' AND m.mix_rank <= {k}
        ) TO '{ml_path(out_name, f"{split}_{country}.parquet")}' (FORMAT parquet)""")
    rel = f"read_parquet('{ml_path(out_name, '*.parquet')}')"
    pit = assert_pit(con, rel, require=())
    cap = con.execute(f"SELECT MAX(n) FROM (SELECT COUNT(*) AS n FROM {rel} GROUP BY member_id, anchor_date)").fetchone()[0]
    assert cap <= k, f"cap violated: {cap} > {k}"
    n = con.execute(f"SELECT split, COUNT(*), COUNT(DISTINCT (member_id, anchor_date)) FROM {rel} GROUP BY 1 ORDER BY 1").fetchall()
    print(f"{out_name} ({policy}, k = {k}): {n}; pit {pit}; max per anchor {cap}")
    con.close()
    publish_view(out_name, ml_path(out_name, "*.parquet"))


if __name__ == "__main__":
    sys.exit(main())
