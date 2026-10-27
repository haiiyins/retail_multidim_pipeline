"""Step 2 — Profile the raw CSV files: column types, null ratio, enumerated values, format of the 3 nested columns, country list.
Run: make probe  →  data/audit/csv_profile.md"""
import duckdb, pathlib, os, re, yaml
from raw_source import parquet_reader
from dotenv import load_dotenv
load_dotenv()
RAW = pathlib.Path(os.environ.get("DATA_ROOT", "./data")) / "raw_csv"
OUT = pathlib.Path(os.environ.get("DATA_ROOT", "./data")) / "audit"
OUT.mkdir(parents=True, exist_ok=True)
ENUM_COLS = {
    "sales_detail": ["item_operation_type", "transaction_channel_type", "transaction_status", "item_type",
                     "economical_businessunit_country_code", "customer_identification_type"],
    "all_store_selling_price": ["price_type", "country_code", "business_unit_third_type"],
    "stock_availability_rate": ["availability_type", "country_code"],
    "tracking_ecom_events": ["name", "country_code", "platform", "is_event_to_use"],
    "f_member_favorite_sport": ["event_type", "country_code"],
    "d_member": ["member_country_code", "is_teammate", "is_business", "is_legal_entity"],
    "f_member_purchase": ["member_country_code"],
}
NESTED = {"sales_detail": ["tax_detail", "price_modifier_detail"], "tracking_ecom_events": ["metadata"]}

con = duckdb.connect()
report = ["# CSV profile (first 20,000 rows per table)\n"]
files = {f.stem: f for f in sorted(RAW.glob("*.csv"))}
TABLES = set(yaml.safe_load(open(pathlib.Path(__file__).with_name("table_contracts.yml"))))
files.update({d.name: d for d in sorted(RAW.iterdir()) if d.is_dir() and d.name in TABLES and any(d.glob("*.parquet"))})   # directory of Parquet parts, contract tables only
files.update({f.stem: f for f in sorted(RAW.glob("*.parquet"))})   # single Parquet re-export wins over both
for t, f in sorted(files.items()):
    kind = "csv" if f.suffix == ".csv" else ("parquet" if f.is_file() else "parquet-dir")
    reader = (parquet_reader(f, kind) if kind != "csv" else
              f"read_csv_auto('{f}', sample_size=200000, header=true, nullstr=['null',''], max_line_size=10000000)")
    con.execute(f"CREATE OR REPLACE TABLE p AS SELECT * FROM {reader} LIMIT 20000")
    cols = con.execute("DESCRIBE p").fetchall()
    report.append(f"\n## {t}  ({len(cols)} columns, {kind})\n\n| column | type | % null |\n|---|---|---|")
    for c, ty, *_ in cols:
        nul = con.execute(f'SELECT ROUND(100.0*SUM(CASE WHEN "{c}" IS NULL THEN 1 ELSE 0 END)/COUNT(*),1) FROM p').fetchone()[0]
        report.append(f"| {c} | {ty} | {nul} |")
    for c in ENUM_COLS.get(t, []):
        try:
            vals = con.execute(f'SELECT "{c}", COUNT(*) FROM p GROUP BY 1 ORDER BY 2 DESC LIMIT 15').fetchall()
            report.append(f"\n**{c}**: {vals}")
        except Exception as e:
            report.append(f"\n**{c}**: (column missing) {e}")
    for c in NESTED.get(t, []):
        try:
            sample = con.execute(f'SELECT "{c}" FROM p WHERE "{c}" IS NOT NULL LIMIT 2').fetchall()
            txt = str(sample[0][0]) if sample else ""
            kind = "JSON" if txt.lstrip().startswith(("{", "[")) else "Map(k -> v) / List(Map(...))  → use the extract_map_field macro"
            if kind == "JSON":  # commit-safe: structure (keys and types) only, no raw values
                try: txt = str(con.execute(f'SELECT json_structure("{c}") FROM p WHERE "{c}" IS NOT NULL LIMIT 1').fetchone()[0])
                except Exception: txt = re.sub(r'"[^"]*"\s*:\s*"[^"]*"', '"k":"…"', txt)
            else:
                txt = re.sub(r"->\s*[^,}\]]+", "-> …", txt)
            report.append(f"\n**{c}** format: **{kind}** (structure only, values redacted)\n\n```\n{txt[:600]}\n```")
        except Exception as e:
            report.append(f"\n**{c}**: {e}")
    # date span of the transaction table
    if t == "sales_detail":
        mx = con.execute("SELECT MIN(gmv_recorded_at), MAX(gmv_recorded_at) FROM p").fetchone()
        report.append(f"\n**gmv_recorded_at (sample)**: {mx}")
REDACT = [t.strip() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
def redact(text):  # organisation-specific tokens listed in .env (REDACT_TERMS, never in the repo) are masked in the report
    for t in REDACT: text = re.sub(re.escape(t), "[org]", text, flags=re.IGNORECASE)
    return text
OUT.joinpath("csv_profile.md").write_text(redact("\n".join(report)), encoding="utf-8")
print(f"→ {OUT/'csv_profile.md'}")
