"""Step 2b — Whole-file scan of the raw CSV files. The sample profile (make probe) reads only the first 20,000
rows per table and the exports are sorted by country, so it cannot give the country list, the value domains
or the date span. This script reads every file once (about 27 GB) and writes data/audit/csv_fullscan.md with:
country codes and rows per country, min/max of the main timestamp per country, enumerated-value domains,
and the format of the key columns (digits only? length, distinct count) to decide the casts in table_contracts.yml.
Run: make probe-full   (minutes on the laptop; needs DUCKDB_MEMORY / DUCKDB_THREADS from .env)"""
import duckdb, pathlib, os, time
from dotenv import load_dotenv
load_dotenv()
ROOT = pathlib.Path(os.environ.get("DATA_ROOT", "./data"))
RAW, OUT = ROOT / "raw_csv", ROOT / "audit"
OUT.mkdir(parents=True, exist_ok=True)

# table: (country column, main timestamp column, enumerated columns, key columns)
SPEC = {
    "sales_detail": ("economical_businessunit_country_code", "gmv_recorded_at",
                     ["item_operation_type", "transaction_channel_type", "transaction_status", "item_type",
                      "customer_identification_type"],
                     ["transaction_id", "item_code", "model_code", "economical_businessunit_gln", "merchant_businessunit_gln"]),
    "sales_tender_detail": (None, "tender_recorded_at", ["tender_operation_type", "tender_type"], ["transaction_id"]),
    "f_member_purchase": ("member_country_code", "association_datetime_utc", ["transaction_source"],
                          ["transaction_id", "member_id"]),
    "d_member": ("member_country_code", "account_creation_datetime_utc", ["is_teammate", "is_business", "is_legal_entity"],
                 ["member_id", "preferred_store_gln", "creation_store_gln"]),
    "dim_item": (None, None, [], ["item_code", "model_code", "supermodel_code"]),
    "dim_business_unit": ("country_code", None, ["business_unit_third_type", "plant_type", "is_business_unit_closed"],
                          ["business_unit_gln", "business_unit_third_id"]),
    "dim_calendar": (None, "date_of_day", [], ["date_of_day"]),
    "all_store_selling_price": ("country_code", "price_start_date", ["price_type", "business_unit_third_type", "timeline_type"],
                                ["item_code", "business_unit_gln_code"]),
    "stock_availability_rate": ("country_code", "snapshot_date", ["availability_type"], ["item_code", "site_gln"]),
    "f_member_favorite_sport": ("country_code", "event_datetime_utc", ["event_type"], ["member_id", "sport_id"]),
    "tracking_ecom_events": ("country_code", "timestamp_utc", ["name", "platform", "is_event_to_use"], ["id", "session_id"]),
}
q = lambda c: f'"{c}"'
def ts(c):  # robust cast of a VARCHAR timestamp / timestamptz / date column
    return (f"COALESCE(TRY_CAST({q(c)} AS TIMESTAMP), TRY_CAST(TRY_CAST({q(c)} AS TIMESTAMPTZ) AS TIMESTAMP), "
            f"TRY_CAST(TRY_CAST({q(c)} AS DATE) AS TIMESTAMP))")

con = duckdb.connect()
con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY', '10GB')}'")
con.execute(f"SET threads={int(os.environ.get('DUCKDB_THREADS', '6'))}")
con.execute(f"SET temp_directory='{ROOT / 'duck_temp'}'")
con.execute("SET preserve_insertion_order=false")

report = ["# CSV full-file scan\n", "Every file read once with `all_varchar=true`; counts are exact, distinct counts are approximate (HyperLogLog).\n"]
summary_countries, summary_span = {}, {}
for t, (ccol, tcol, enums, keys) in SPEC.items():
    f = RAW / f"{t}.csv"
    if not f.exists():
        report.append(f"\n## {t}\n\n_file missing_"); continue
    t0 = time.time()
    sel = [f"{q(ccol) if ccol else chr(39)+'ALL'+chr(39)} AS country", "COUNT(*) AS n"]
    sel += [f"MIN({ts(tcol)}) AS min_ts", f"MAX({ts(tcol)}) AS max_ts"] if tcol else ["NULL AS min_ts", "NULL AS max_ts"]
    sel += [f"histogram({q(e)}) AS h_{i}" for i, e in enumerate(enums)]
    for i, k in enumerate(keys):
        sel += [f"SUM(CASE WHEN regexp_matches({q(k)}, '^[0-9]+$') THEN 1 ELSE 0 END) AS k{i}_digits",
                f"MIN(length({q(k)})) AS k{i}_minlen", f"MAX(length({q(k)})) AS k{i}_maxlen",
                f"approx_count_distinct({q(k)}) AS k{i}_nd", f"SUM(CASE WHEN {q(k)} IS NULL THEN 1 ELSE 0 END) AS k{i}_null"]
    sql = (f"SELECT {', '.join(sel)} FROM read_csv('{f}', all_varchar=true, header=true, nullstr=['null',''], ignore_errors=true, "
           f"max_line_size=10000000) GROUP BY 1 ORDER BY 1")
    rows = con.execute(sql).fetchall(); cols = [d[0] for d in con.description]
    recs = [dict(zip(cols, r)) for r in rows]
    total = sum(r["n"] for r in recs)
    report.append(f"\n## {t}  ({total:,} rows, {time.time()-t0:.0f} s)\n")
    report.append(f"| {ccol or 'country'} | rows | min {tcol or '-'} | max {tcol or '-'} |\n|---|---:|---|---|")
    for r in recs:
        report.append(f"| {r['country']} | {r['n']:,} | {r['min_ts']} | {r['max_ts']} |")
        if ccol:
            summary_countries.setdefault(t, []).append(str(r["country"]))
            if t == "sales_detail": summary_span[r["country"]] = (r["n"], r["min_ts"], r["max_ts"])
    for i, e in enumerate(enums):
        merged = {}
        for r in recs:
            for k, v in (r[f"h_{i}"] or {}).items(): merged[k] = merged.get(k, 0) + v
        top = sorted(merged.items(), key=lambda kv: -kv[1])
        shown = ", ".join(f"`{k}` {v:,}" for k, v in top[:15]) + (f" … (+{len(top)-15} more)" if len(top) > 15 else "")
        report.append(f"\n**{e}** ({len(top)} values): {shown}")
    report.append("\n| key column | digits only | min len | max len | ≈ distinct | nulls |\n|---|---:|---:|---:|---:|---:|")
    for i, k in enumerate(keys):
        dig = sum(r[f"k{i}_digits"] or 0 for r in recs); nul = sum(r[f"k{i}_null"] or 0 for r in recs)
        mn = min((r[f"k{i}_minlen"] for r in recs if r[f"k{i}_minlen"] is not None), default=None)
        mx = max((r[f"k{i}_maxlen"] for r in recs if r[f"k{i}_maxlen"] is not None), default=None)
        nd = sum(r[f"k{i}_nd"] or 0 for r in recs)
        pct = 100.0 * dig / max(total - nul, 1)
        report.append(f"| {k} | {pct:.1f} % | {mn} | {mx} | {nd:,} | {nul:,} |")
    print(f"{t}: {total:,} rows in {time.time()-t0:.0f} s", flush=True)

head = ["\n## Summary\n", "| table | country codes |", "|---|---|"]
head += [f"| {t} | {', '.join(sorted(v))} |" for t, v in summary_countries.items()]
allc = sorted({c for v in summary_countries.values() for c in v})
head.append(f"\n**Union of country codes:** {', '.join(allc)}\n")
head += ["| country | sales_detail rows | min gmv_recorded_at | max gmv_recorded_at |", "|---|---:|---|---|"]
head += [f"| {c} | {n:,} | {a} | {b} |" for c, (n, a, b) in sorted(summary_span.items())]
report[2:2] = head
OUT.joinpath("csv_fullscan.md").write_text("\n".join(report), encoding="utf-8")
print(f"→ {OUT / 'csv_fullscan.md'}")
