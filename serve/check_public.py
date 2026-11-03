"""Pre-publication check of the public demo (plan §10): nothing in the files pushed to the Space may identify the data owner, a
member or a real product. Scans every file under data/demo/space (text files as text, Parquet / CSV string columns as values) for
  - raw model codes of slv_dim_model and member ids of slv_fact_sales_line (exact tokens; the published ids are salted hashes),
  - the organisation tokens of REDACT_TERMS (.env, comma-separated, as tools/report_tables.py) and the optional extra terms of
    data/demo/blocked_terms.txt (one per line: store or private product names), case-insensitive substrings. Both stay local, so
    the terms themselves are not published either.
Exits 1 and lists the hits when anything is found, or when no blocked term is configured.
Usage: python serve/check_public.py [--dir data/demo/space]"""
import argparse, os, re, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from ml.common.data import ROOT, connect

DEMO = os.path.join(os.environ.get("DATA_ROOT", str(ROOT / "data")), "demo")
TOKEN = re.compile(r"[A-Za-z0-9_\-]{4,}")
TEXT = {".html", ".js", ".py", ".md", ".txt", ".json", ".css", ".yml", ".yaml"}


def file_strings(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".parquet":
        df = pd.read_parquet(path)
    elif ext == ".csv":
        df = pd.read_csv(path, dtype=str)
    elif ext in TEXT:
        with open(path, encoding="utf-8", errors="replace") as f:
            return [f.read()]
    else:
        return []
    cols = [c for c in df.columns if df[c].dtype == object]
    return [" ".join(map(str, df.columns))] + [" ".join(df[c].dropna().astype(str)) for c in cols]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=os.path.join(DEMO, "space"))
    a = ap.parse_args()
    terms = [t.strip().lower() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
    extra = os.path.join(DEMO, "blocked_terms.txt")
    if os.path.exists(extra):
        with open(extra, encoding="utf-8") as f:
            terms += [t.strip().lower() for t in f if t.strip()]
    if not terms:
        print("no blocked term: set REDACT_TERMS in .env (and optionally data/demo/blocked_terms.txt)")
        return 1
    con = connect()
    models = set(con.execute("SELECT DISTINCT CAST(model_code AS VARCHAR) FROM lh.silver.slv_dim_model").df().iloc[:, 0])
    members = set(con.execute("SELECT DISTINCT CAST(member_id AS VARCHAR) FROM lh.silver.slv_fact_sales_line "
                              "WHERE member_id IS NOT NULL").df().iloc[:, 0])
    hits, n_files = [], 0
    for root, _, files in os.walk(a.dir):
        for name in files:
            path = os.path.join(root, name)
            n_files += 1
            for s in file_strings(path):
                low = s.lower()
                hits += [(path, "term", t) for t in terms if t in low]
                for tok in set(TOKEN.findall(s)):
                    if tok in models:
                        hits.append((path, "model_code", tok))
                    elif tok in members:
                        hits.append((path, "member_id", tok))
    for path, kind, what in sorted(set(hits))[:50]:
        print(f"  {kind:10s} {os.path.relpath(path, a.dir)}: {what if kind != 'term' else '<blocked term>'}")
    print(f"{n_files} files, {len(terms)} blocked terms, {len(set(hits))} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
