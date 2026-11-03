"""ML-17 — pair features and labels of ml.candidates_v2 from the very SQL of Gold: dbt_multidim/models/gold/gld_fs_pair.sql and
gld_ranking_dataset.sql are rendered with Jinja, ref('gld_candidates') pointing at candidates_v2 and every other ref at the read-only
lakehouse (lh.silver / lh.gold), so the feature logic stays defined once and the lakehouse write lock is never needed.

Per split × country: data/ml/pairs_v2/<split>_<country>.parquet = gld_ranking_dataset columns (pair features, label_30 / label_90)
plus the source columns of candidates_v2. Checks (the dbt tests of Gold, on the new table): leakage_fs_pair (last_source_ts after the
anchor: 0 rows), no row loss (one pair row per candidate), point-in-time of the learned sources (pit.assert_pit).
Usage: python ml/common/pairs.py [--splits train,valid,test] [--countries SG,TH,VN] [--version v3: candidates_v3 → pairs_v3]"""
import argparse, os, sys, time
import jinja2, yaml

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ROOT, connect, ml_path
from ml.common.pit import assert_pit

GOLD = ROOT / "dbt_multidim" / "models" / "gold"
SCHEMA = {"slv_": "silver", "gld_": "gold"}


class PairCheckFailed(Exception):
    pass


def render(model, refs):
    """Rendered SQL of a Gold model; refs overrides ref(name) with a relation."""
    project_vars = yaml.safe_load(open(ROOT / "dbt_multidim" / "dbt_project.yml"))["vars"]

    def ref(name):
        return refs.get(name) or f"lh.{SCHEMA[name[:4]]}.{name}"

    def var(name, default=None):
        return project_vars.get(name, default)

    return jinja2.Environment().from_string(open(GOLD / f"{model}.sql").read()).render(ref=ref, var=var)


def ranking_sql(candidates):
    pair = render("gld_fs_pair", {"gld_candidates": candidates})
    return render("gld_ranking_dataset", {"gld_fs_pair": f"(\n{pair}\n)"})


def build(con, split, country, cand_glob, version="v2"):
    cand = (f"(SELECT * REPLACE (CAST(anchor_date AS DATE) AS anchor_date) FROM read_parquet('{cand_glob}') "
            f"WHERE country_code = '{country}')")
    out = ml_path(f"pairs_{version}", f"{split}_{country}.parquet")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    t0 = time.time()
    con.execute(f"COPY ({ranking_sql(cand)}) TO '{out}' (FORMAT parquet)")
    rel = f"read_parquet('{out}')"
    n_pair, leak = con.execute(f"SELECT COUNT(*), COUNT(*) FILTER (WHERE last_source_ts > CAST(anchor_date AS TIMESTAMP)) FROM {rel}").fetchall()[0]
    n_cand = con.execute(f"SELECT COUNT(*) FROM {cand}").fetchall()[0][0]
    if leak or n_pair != n_cand:
        raise PairCheckFailed(f"{out}: {leak} rows with last_source_ts after the anchor, {n_pair:,} pair rows for {n_cand:,} candidates")
    pit = assert_pit(con, rel, require=())
    print(f"  pairs {split} {country}: {n_pair:,} rows, leakage 0, no row loss, pit {pit}, {time.time() - t0:.0f}s", flush=True)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--splits", default="train,valid,test")
    ap.add_argument("--countries", default="SG,TH,VN")
    ap.add_argument("--version", default="v2")
    a = ap.parse_args()
    con = connect(threads=int(os.environ.get("PAIRS_THREADS", 32)))
    con.execute(f"SET memory_limit='{os.environ.get('PAIRS_MEMORY', '150GB')}'")
    for split in a.splits.split(","):
        for country in a.countries.split(","):
            build(con, split, country, ml_path(f"candidates_{a.version}", f"{split}_*.parquet"), a.version)
    con.close()


if __name__ == "__main__":
    sys.exit(main())
