"""Pre-publication check of the public demo (plan §10): nothing in the staged Space may identify the data owner, a member or a real
product. Run after serve/build_space.py, before every upload (make demo-push, .github/workflows/deploy-space.yml).
Structure (no data needed, also in CI):
  - every model_id / neighbour_id (CSV columns, showcase.json items) is a salted hash M + 10 hex digits;
  - showcase.json members carry only the published fields (member_id <country>-<NNN>, country, segment, history, bought, best,
    status_quo) and items only model_id, department (generic "Dept NN"), price_band, repeat, bought, days_before / days_after,
    quantity: no date, price, store, web or member attribute;
  - no UUID (the member ids of the lakehouse), local path or salt anywhere;
  - the organisation tokens of REDACT_TERMS (.env, comma-separated, as tools/report_tables.py) and data/demo/blocked_terms.txt
    when available (they are not in CI; locally --require-terms makes their absence an error).
--db (local): also no raw model code of slv_dim_model and no member id of slv_fact_sales_line as a token of any file.
Exits 1 and lists the hits when anything is found.
Usage: python serve/check_public.py [--dir data/demo/space] [--db] [--require-terms]"""
import argparse, json, os, pathlib, re, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
DEMO = pathlib.Path(os.environ.get("DATA_ROOT", str(ROOT / "data"))) / "demo"
HASH = re.compile(r"^M[0-9a-f]{10}$")
SHOWCASE_MEMBER = re.compile(r"^[A-Z]{2}-\d{3}$")
DEPT = re.compile(r"^Dept (\d{2}|--)$")
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.IGNORECASE)
PATH = re.compile(r"(/home/|/localhome/|/Users/|[A-Za-z]:\\\\)")
TOKEN = re.compile(r"[A-Za-z0-9_.\-]{4,}")   # '.' kept: a decimal such as 0.18429 must not yield the numeric model code 18429
TEXT = {".html", ".js", ".py", ".md", ".txt", ".json", ".css", ".yml", ".yaml", ".csv"}
MEMBER_KEYS = {"member_id", "country_code", "segment", "history", "bought", "best", "status_quo"}
ITEM_KEYS = {"model_id", "department", "price_band", "repeat", "bought", "days_before", "days_after", "quantity"}
ID_COLUMNS = ("model_id", "neighbour_id")


def blocked_terms():
    terms = [t.strip().lower() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
    extra = DEMO / "blocked_terms.txt"
    if extra.exists():
        terms += [t.strip().lower() for t in extra.read_text(encoding="utf-8").splitlines() if t.strip()]
    return terms


def check_showcase(doc):
    hits = []
    for m in doc.get("members", []):
        if set(m) - MEMBER_KEYS:
            hits.append(f"member fields {sorted(set(m) - MEMBER_KEYS)}")
        if not SHOWCASE_MEMBER.match(str(m.get("member_id", ""))):
            hits.append(f"member_id {m.get('member_id')!r}")
        for key in ("history", "bought", "best", "status_quo"):
            for it in m.get(key, []):
                if set(it) - ITEM_KEYS:
                    hits.append(f"{key} item fields {sorted(set(it) - ITEM_KEYS)}")
                if not HASH.match(str(it.get("model_id", ""))):
                    hits.append(f"{key} model_id {it.get('model_id')!r}")
                if "department" in it and not DEPT.match(str(it["department"])):
                    hits.append(f"{key} department {it['department']!r}")
    return sorted(set(hits))


def check_csv(path):
    df = pd.read_csv(path, dtype=str)
    bad = [f"{c} {v!r}" for c in ID_COLUMNS if c in df.columns for v in df[c].dropna().unique() if not HASH.match(v)]
    return bad[:5]


def raw_ids():
    sys.path.insert(0, str(ROOT))
    from ml.common.data import connect
    con = connect()
    models = set(con.execute("SELECT DISTINCT CAST(model_code AS VARCHAR) FROM lh.silver.slv_dim_model").df().iloc[:, 0])
    members = set(con.execute("SELECT DISTINCT CAST(member_id AS VARCHAR) FROM lh.silver.slv_fact_sales_line "
                              "WHERE member_id IS NOT NULL").df().iloc[:, 0])
    return models, members


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", default=str(DEMO / "space"))
    ap.add_argument("--db", action="store_true", help="also match the raw model codes and member ids of the lakehouse")
    ap.add_argument("--require-terms", action="store_true", help="fail when no blocked term is configured")
    a = ap.parse_args()
    terms = blocked_terms()
    if not terms:
        print("no blocked term (REDACT_TERMS, data/demo/blocked_terms.txt): organisation names not checked")
        if a.require_terms:
            return 1
    models, members = raw_ids() if a.db else (set(), set())
    hits, n_files = [], 0
    for path in sorted(pathlib.Path(a.dir).rglob("*")):
        if not path.is_file():
            continue
        n_files += 1
        rel = path.relative_to(a.dir)
        if "salt" in path.name.lower():
            hits.append((rel, "salt file"))
        if path.suffix.lower() not in TEXT:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if path.name == "showcase.json":
            hits += [(rel, h) for h in check_showcase(json.loads(text))]
        elif path.suffix.lower() == ".csv":
            hits += [(rel, f"not a salted hash: {h}") for h in check_csv(path)]
        if UUID.search(text):
            hits.append((rel, "UUID"))
        if PATH.search(text):
            hits.append((rel, "local path"))
        low = text.lower()
        hits += [(rel, "blocked term") for t in terms if t in low]
        if models or members:
            for tok in {t.strip(".") for t in TOKEN.findall(text)}:
                if tok in models:
                    hits.append((rel, f"raw model code {tok}"))
                elif tok in members:
                    hits.append((rel, "raw member id"))
    for rel, what in sorted(set(hits), key=str)[:50]:
        print(f"  {rel}: {what}")
    print(f"{n_files} files, {len(terms)} blocked terms, raw ids {'checked' if a.db else 'not checked'}, {len(set(hits))} hits")
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
