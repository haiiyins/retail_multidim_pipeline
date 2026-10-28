"""Report tables (WBS 5.2 / 5.3, RUNBOOK §9): every number quoted in docs/report/ is produced here from the lakehouse, so the
chapters can be regenerated on the server with the three-country data instead of being retyped. One Markdown table and one CSV per
item in docs/report/tables/, each with a provenance line (source table or script, generation time, country filter), plus INDEX.md.
Organisation-specific tokens are masked through REDACT_TERMS (.env, never in the repository), exactly as the probes do.

    python tools/report_tables.py                 # every table
    python tools/report_tables.py --only t04,t07  # a subset
    make report-tables
"""
import argparse, collections, csv, datetime, json, os, pathlib, re, sys
import duckdb, yaml
from dotenv import load_dotenv
load_dotenv(".env")
sys.path.insert(0, "ingestion")
from raw_source import raw_source

DB = os.environ["DUCKDB_PATH"]
ROOT = pathlib.Path(os.environ.get("DATA_ROOT", "./data"))
CF = (os.environ.get("COUNTRY_FILTER") or "ALL").strip().upper()
REDACT = [t.strip() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
NOW = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")


def redact(text):
    for t in REDACT: text = re.sub(re.escape(t), "[org]", text, flags=re.IGNORECASE)
    return text


PLAIN = {"year", "delta", "months", "threads", "dbt_threads", "reps"}   # integer columns printed without thousands separators


def fmt(v, col=""):
    if v is None: return ""
    if isinstance(v, bool): return "yes" if v else "no"
    if isinstance(v, int): return str(v) if col in PLAIN else f"{v:,}"
    if isinstance(v, float): return f"{v:,.4f}".rstrip("0").rstrip(".") if abs(v) < 1000 else f"{v:,.1f}"
    if isinstance(v, (list, tuple)): return " / ".join(fmt(x) for x in v)
    if isinstance(v, datetime.datetime): return v.strftime("%Y-%m-%d %H:%M")
    return str(v)


def write_table(out, name, title, cols, rows, source, note=None):
    """Markdown table + CSV. Numeric columns are right-aligned. Returns the INDEX line."""
    num = [all((isinstance(r[i], (int, float)) and not isinstance(r[i], bool)) or r[i] is None for r in rows) and any(r[i] is not None for r in rows) for i in range(len(cols))]
    head = "| " + " | ".join(c.replace("_", " ") for c in cols) + " |"
    align = "|" + "|".join("---:" if n else "---" for n in num) + "|"
    body = ["| " + " | ".join(fmt(v, c) for v, c in zip(r, cols)) + " |" for r in rows] or ["| " + " | ".join("" for _ in cols) + " |"]
    text = [f"### {title}", "", head, align, *body, "",
            f"*Source:* {source}. *Generated:* {NOW} by `tools/report_tables.py`, `COUNTRY_FILTER={CF}`." + (f" {note}" if note else ""), ""]
    (out / f"{name}.md").write_text(redact("\n".join(text)))
    with open(out / f"{name}.csv", "w", newline="") as f:
        w = csv.writer(f); w.writerow(cols)
        for r in rows: w.writerow([redact(str(v)) if isinstance(v, str) else (v if not isinstance(v, (list, tuple)) else " / ".join(map(str, v))) for v in r])
    print(f"{name:26s} {len(rows):>5} rows  {title}")
    return f"- [{title}]({name}.md) — {source}"


def q(con, sql):
    cur = con.execute(sql); cols = [d[0] for d in cur.description]; return cols, cur.fetchall()


def table_exists(con, schema, name):
    return con.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = ? AND table_name = ?", [schema, name]).fetchone()[0] > 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", default="", help="comma-separated table ids, e.g. t04,t07")
    ap.add_argument("--out", default="docs/report/tables")
    ap.add_argument("--index-only", action="store_true", help="only rebuild INDEX.md from the tables already in --out (no database access)")
    a = ap.parse_args()
    only = {t.strip() for t in a.only.split(",") if t.strip()}
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    if a.index_only:
        write_index(out); return
    con = duckdb.connect(DB, read_only=True)
    con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY', '10GB')}'; SET threads={os.environ.get('DUCKDB_THREADS', '6')}; SET TimeZone='UTC'")
    index = []

    def want(t): return not only or t in only

    # ---------------------------------------------------------------- item 1: the 11 source tables
    if want("t01"):
        contracts = yaml.safe_load(open("ingestion/table_contracts.yml"))
        metrics = {r[0]: r for r in con.execute("""SELECT model_name, output_rows, output_bytes, wall_time_sec, country_filter FROM audit.pipeline_run_metrics
                                                     WHERE layer = 'bronze' QUALIFY ROW_NUMBER() OVER (PARTITION BY model_name ORDER BY executed_at DESC) = 1""").fetchall()}
        scanned = dict(re.findall(r"^## (\w+)\s+\([\d,]+ rows, ([\w-]+),", pathlib.Path("data/audit/csv_fullscan.md").read_text(), re.M)) \
            if pathlib.Path("data/audit/csv_fullscan.md").exists() else {}   # raw files may have been deleted after loading (server: the 187 GB of tracking parts)
        rows = []
        for t, c in contracts.items():
            _, kind = raw_source(ROOT / "raw_csv", t)
            m = metrics.get(t)
            rows.append((t, kind or scanned.get(t, "-"), ", ".join(c.get("key", [])), c.get("country_col") or (f"via {c['country_via']['table']}" if c.get("country_via") else "-"),
                         ", ".join(c.get("partition", [])) or "-", m[1] if m else None, round(m[2] / 1e6, 1) if m and m[2] else None, round(m[3], 1) if m else None))
        index.append(write_table(out, "t01_source_tables", "The eleven source tables: raw format, contract key, Bronze partitioning and loaded volume",
                                 ["table", "raw_format", "contract_key", "country_column", "bronze_partition", "rows_loaded", "parquet_MB", "load_sec"], rows,
                                 "`ingestion/table_contracts.yml`, `ingestion/raw_source.py`, `audit.pipeline_run_metrics` (layer bronze, latest load per table)",
                                 "Raw formats and full-file row counts per country are in `data/audit/csv_fullscan.md` (also the source of the format when the raw files are no longer on disk)."))

    # ---------------------------------------------------------------- Silver: sales-line funnel and quarantine
    if want("t02"):
        cols, rows = q(con, """
            WITH s AS (SELECT * FROM staging.stg_sales_detail),
            raw AS (SELECT country_code, COUNT(*) AS raw_rows, COUNT(DISTINCT (transaction_id, transaction_num_line)) AS line_keys,
                           COUNT(*) FILTER (WHERE item_operation_type = 'sale') AS sale_rows, COUNT(*) FILTER (WHERE item_operation_type = 'cancel') AS cancel_rows,
                           COUNT(*) FILTER (WHERE item_operation_type = 'return') AS return_rows FROM s GROUP BY 1),
            dist AS (SELECT country_code, COUNT(*) AS distinct_rows FROM (SELECT DISTINCT * FROM s) GROUP BY 1),
            silver AS (SELECT country_code, COUNT(*) AS sale_lines_kept, COUNT(DISTINCT transaction_id) AS sale_transactions, COUNT(DISTINCT member_id) AS buying_members
                       FROM silver.slv_fact_sales_line GROUP BY 1),
            ret AS (SELECT country_code, COUNT(*) AS return_lines_kept FROM silver.slv_fact_returns GROUP BY 1),
            qr AS (SELECT country_code, COUNT(*) AS quarantined_rows FROM quarantine.qrt_sales_line GROUP BY 1)
            SELECT r.country_code, r.raw_rows, d.distinct_rows, r.line_keys, r.sale_rows, r.cancel_rows, r.return_rows,
                   sv.sale_lines_kept, sv.sale_transactions, sv.buying_members, rt.return_lines_kept, qr.quarantined_rows
            FROM raw r LEFT JOIN dist d USING (country_code) LEFT JOIN silver sv USING (country_code) LEFT JOIN ret rt USING (country_code) LEFT JOIN qr USING (country_code)
            ORDER BY 1""")
        index.append(write_table(out, "t02_sales_funnel", "Sales lines from Bronze to Silver: exact duplicates, line keys, netting and what is kept", cols, rows,
                                 "`staging.stg_sales_detail`, `silver.slv_fact_sales_line`, `silver.slv_fact_returns`, `quarantine.qrt_sales_line` (dedup and netting rules in `slv_sales_line_netted.sql`)"))
    if want("t03"):
        cols, rows = q(con, """SELECT country_code, reason, COUNT(*) AS netted_rows, ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (PARTITION BY country_code), 2) AS pct_of_quarantine
                                FROM quarantine.qrt_sales_line GROUP BY 1, 2 ORDER BY 1, 3 DESC""")
        index.append(write_table(out, "t03_quarantine_sales", "Quarantined sales rows by reason (QC-3 / QC-4 routing)", cols, rows,
                                 "`quarantine.qrt_sales_line` (`models/quarantine/qrt_sales_line.sql`)"))

    # ---------------------------------------------------------------- item 2: gates
    if want("t04"):
        cols, rows = q(con, "SELECT * FROM audit.gates_by_country ORDER BY country, year")
        index.append(write_table(out, "t04_gates", "Go / no-go gates per country × year (thresholds 60 / 95 / 90 % and 20,000 members)", cols, rows,
                                 "`audit.gates_by_country` (`sql/gates_by_country.sql`, `make gates`)"))

    # ---------------------------------------------------------------- item 3: stock, price uniformity, inter-purchase gaps
    if want("t05"):
        cols, rows = q(con, """
            SELECT COALESCE(g.country, p.country_code, s.c) AS country,
                   s.sold_items, s.in_stock_tbl AS in_spare_parts_table, s.coverage AS spare_parts_coverage,
                   p.n_pairs AS store_vs_national_pairs, p.mean_rel_gap, p.p95_rel_gap,
                   g.q25_50_75_90 AS interpurchase_q25_q50_q75_q90_days, g.n_gaps,
                   d.min_ts AS first_sale, d.max_ts AS last_sale
            FROM audit.interpurchase_days g
            FULL JOIN audit.price_uniformity p ON p.country_code = g.country
            FULL JOIN audit.stock_coverage s ON s.c = COALESCE(g.country, p.country_code)
            LEFT JOIN audit.date_span d ON d.country = COALESCE(g.country, p.country_code, s.c)
            ORDER BY 1""")
        index.append(write_table(out, "t05_audit_checks", "Audit checks: stock-table coverage, in-country price uniformity, inter-purchase gaps, date span", cols, rows,
                                 "`audit.stock_coverage`, `audit.price_uniformity`, `audit.interpurchase_days`, `audit.date_span` (`sql/audit_checks.sql`)",
                                 "The exported stock table covers spare parts only (data owner, issue #21), hence the low coverage."))

    # ---------------------------------------------------------------- Silver: price intervals
    if want("t06"):
        cols, rows = q(con, """
            WITH i AS (SELECT country_code, COUNT(*) AS intervals, COUNT(DISTINCT item_code) AS skus_priced,
                              COUNT(*) FILTER (WHERE price_type = 'STANDARD') AS standard_intervals,
                              COUNT(*) FILTER (WHERE price_type = 'DAY_TO_DAY_PROMOTION') AS daily_promo_intervals,
                              COUNT(*) FILTER (WHERE price_type = 'END_OF_LINE') AS end_of_line_intervals,
                              COUNT(*) FILTER (WHERE price_type = 'DROP') AS drop_intervals,
                              ROUND(AVG(CAST(is_temp_promo AS INT)), 4) AS temp_promo_share, MIN(eff_start) AS first_start
                       FROM silver.slv_price_sku_interval GROUP BY 1),
            qp AS (SELECT country_code, COUNT(*) FILTER (WHERE reason = 'ABOVE_REFERENCE') AS q_above_reference, COUNT(*) FILTER (WHERE reason = 'DEPTH_GT_0_9') AS q_depth_gt_0_9
                   FROM quarantine.qrt_price_interval GROUP BY 1),
            raw AS (SELECT country_code, COUNT(*) AS raw_price_rows, COUNT(*) FILTER (WHERE business_unit_third_type = 15) AS country_unit_rows,
                           COUNT(*) FILTER (WHERE business_unit_third_type = 50) AS website_unit_rows FROM bronze.all_store_selling_price GROUP BY 1)
            SELECT i.country_code, r.raw_price_rows, r.country_unit_rows, r.website_unit_rows, i.intervals, i.skus_priced, i.standard_intervals, i.daily_promo_intervals,
                   i.end_of_line_intervals, i.drop_intervals, i.temp_promo_share, i.first_start, qp.q_above_reference, qp.q_depth_gt_0_9
            FROM i LEFT JOIN raw r USING (country_code) LEFT JOIN qp USING (country_code) ORDER BY 1""")
        index.append(write_table(out, "t06_price_intervals", "SKU price intervals: raw price rows by business-unit type, national intervals by price type, quarantine", cols, rows,
                                 "`bronze.all_store_selling_price`, `silver.slv_price_sku_interval`, `quarantine.qrt_price_interval`"))

    # ---------------------------------------------------------------- item 5: calendar and inferred commercial events
    if want("t07"):
        cols, rows = q(con, """
            SELECT country_code, event_name, MIN(calendar_date) AS first_day, MAX(calendar_date) AS last_day, COUNT(*) AS event_days,
                   COUNT(DISTINCT event_start) AS occurrences, ROUND(AVG(promo_share), 4) AS mean_promo_share,
                   (MAX(CASE WHEN event_name LIKE 'EVENT\\_%' ESCAPE '\\' THEN 1 ELSE 0 END) = 0) AS named_from_dictionary
            FROM silver.slv_calendar_enriched WHERE in_commercial_event GROUP BY 1, 2 ORDER BY 1, 3""")
        index.append(write_table(out, "t07_calendar_events", "Commercial events inferred from the temporary-promotion share (≥ 3 consecutive peak days), named by the team dictionary", cols, rows,
                                 "`silver.slv_calendar_enriched` (`models/silver/slv_calendar_enriched.sql`), `ext.commercial_event_names`",
                                 "`EVENT_n` labels are peaks without a dictionary window."))
        cols, rows = q(con, """
            SELECT c.country_code, COUNT(*) AS calendar_days, MIN(calendar_date) AS first_day, MAX(calendar_date) AS last_day,
                   COUNT(*) FILTER (WHERE is_public_holiday) AS public_holiday_days, COUNT(*) FILTER (WHERE in_commercial_event) AS commercial_event_days,
                   COUNT(DISTINCT event_start) FILTER (WHERE in_commercial_event) AS events, ROUND(AVG(promo_share), 4) AS mean_promo_share,
                   ROUND(MAX(promo_share), 4) AS max_promo_share
            FROM silver.slv_calendar_enriched c GROUP BY 1 ORDER BY 1""")
        index.append(write_table(out, "t07b_calendar_summary", "Enriched calendar per country: holidays, event days, promotion share", cols, rows,
                                 "`silver.slv_calendar_enriched`, `ext.public_holidays` (`ingestion/holiday_commercial_builder.py`)"))

    # ---------------------------------------------------------------- item 4: stitching coverage before / after
    if want("t08"):
        cols, rows = q(con, """
            WITH s AS (SELECT country_code, id_source, n_events, pct FROM audit.stitching_coverage),
            e AS (SELECT country_code, COUNT(*) AS events, COUNT(DISTINCT event_date) AS event_days, MIN(event_date) AS first_event, MAX(event_date) AS last_event,
                         COUNT(DISTINCT user_id) AS users FROM silver.slv_web_events_clean GROUP BY 1)
            SELECT e.country_code, e.events, e.event_days, e.first_event, e.last_event, e.users,
                   MAX(CASE WHEN id_source = 'DIRECT' THEN pct END) AS direct_pct,
                   MAX(CASE WHEN id_source = 'STITCHED' THEN pct END) AS stitched_pct,
                   MAX(CASE WHEN id_source = 'ANON' THEN pct END) AS anonymous_pct,
                   MAX(CASE WHEN id_source = 'DIRECT' THEN pct END) + COALESCE(MAX(CASE WHEN id_source = 'STITCHED' THEN pct END), 0) AS identified_after_pct,
                   MAX(l.links) AS cookie_member_links_by_account_country,
                   (SELECT COUNT(*) FROM quarantine.slv_identity_conflicts) AS conflicting_cookies_all_countries
            FROM e LEFT JOIN s USING (country_code)
            LEFT JOIN (SELECT p.country_code, COUNT(*) AS links FROM silver.slv_user_to_member u JOIN silver.slv_member_profile p USING (member_id) GROUP BY 1) l USING (country_code)
            GROUP BY ALL ORDER BY 1""")
        index.append(write_table(out, "t08_stitching_events", "Identity stitching at event level: share of web events with a member before (DIRECT) and after (+ STITCHED)", cols, rows,
                                 "`audit.stitching_coverage` (`models/audit/stitching_coverage.sql`), `silver.slv_web_events_clean`, `silver.slv_user_to_member`, `quarantine.slv_identity_conflicts`",
                                 "Cookie–member links carry no country; they are attributed to the member's account country. Conflicting cookies (several members) are counted once for all countries."))
    if want("t09"):
        cols, rows = q(con, """
            WITH a AS (SELECT member_id, country_code, anchor_date, split FROM gold.anchor_grid WHERE is_used),
            w AS (SELECT DISTINCT a.member_id, a.anchor_date FROM a JOIN gold.gld_web_stitched w ON w.member_id = a.member_id
                  AND w.event_date BETWEEN a.anchor_date - 30 AND a.anchor_date - 1 AND w.identity_verified_ts <= CAST(a.anchor_date AS TIMESTAMP)),
            av AS (SELECT country_code, anchor_date, web_data_available FROM gold.gld_fs_member GROUP BY ALL)
            SELECT a.country_code, a.split, COUNT(*) AS used_anchors, COUNT(w.member_id) AS anchors_with_web_signal,
                   ROUND(100.0 * COUNT(w.member_id) / COUNT(*), 2) AS pct_with_web_signal,
                   COUNT(*) FILTER (WHERE av.web_data_available) AS anchors_with_web_data_available
            FROM a LEFT JOIN w USING (member_id, anchor_date) LEFT JOIN av ON av.country_code = a.country_code AND av.anchor_date = a.anchor_date
            GROUP BY 1, 2 ORDER BY 1, 2""")
        index.append(write_table(out, "t09_stitching_anchors", "Identity stitching at anchor level: used anchors whose member has an attributed web event in the 30 days before, known at the anchor", cols, rows,
                                 "`gold.anchor_grid`, `gold.gld_web_stitched`, `gold.gld_fs_member.web_data_available` (RUNBOOK §5 query)"))

    # ---------------------------------------------------------------- Gold: anchor funnel and layer sizes
    if want("t10"):
        cols, rows = q(con, """
            SELECT country_code, split, COUNT(*) AS anchors, COUNT(DISTINCT member_id) AS members,
                   COUNT(*) FILTER (WHERE days_to_next_buy <= 90) AS with_purchase_within_90d,
                   COUNT(*) FILTER (WHERE days_to_next_buy <= 90 AND (split <> 'train' OR in_train_sample)) AS after_train_stride,
                   COUNT(*) FILTER (WHERE is_used) AS used_after_cap, COUNT(DISTINCT member_id) FILTER (WHERE is_used) AS members_used
            FROM gold.anchor_grid GROUP BY 1, 2 ORDER BY 1, CASE split WHEN 'train' THEN 1 WHEN 'valid' THEN 2 ELSE 3 END""")
        index.append(write_table(out, "t10_anchor_funnel", "Anchor grid: every Monday after the second purchase, then the label-horizon rule, the training stride and the per-country cap", cols, rows,
                                 "`gold.anchor_grid` (`evaluation/build_anchor_grid.py`, `evaluation/split.yml`)"))
    if want("t11"):
        block = con.execute("SELECT block_size FROM pragma_database_size()").fetchone()[0]
        rows = []
        for schema, name in con.execute("SELECT schema_name, table_name FROM duckdb_tables() WHERE schema_name IN ('silver', 'quarantine', 'gold', 'audit', 'ext') ORDER BY 1, 2").fetchall():
            n = con.execute(f"SELECT COUNT(*) FROM {schema}.{name}").fetchone()[0]
            blocks = con.execute(f"SELECT COUNT(DISTINCT block_id) FROM pragma_storage_info('{schema}.{name}') WHERE block_id >= 0").fetchone()[0]
            rows.append((schema, name, n, round(blocks * block / 1e6, 1)))
        index.append(write_table(out, "t11_layer_sizes", "Silver, quarantine, Gold and audit tables: rows and on-disk size", ["layer", "table", "rows", "size_MB"], rows,
                                 "`duckdb_tables()`, `pragma_storage_info()` (distinct storage blocks × block size)"))

    # ---------------------------------------------------------------- item 6: candidate recall per source
    if want("t12") and table_exists(con, "audit", "candidate_recall"):
        cols, rows = q(con, """SELECT country_code, split, delta, positives, recall_any, recall_r1, recall_r2, recall_r3, recall_r4, recall_r5
                                FROM audit.candidate_recall ORDER BY 1, CASE split WHEN 'train' THEN 1 WHEN 'valid' THEN 2 ELSE 3 END, 3""")
        index.append(write_table(out, "t12_candidate_recall", "Candidate recall@200 overall and per source (R1 repurchase, R2 co-purchase, R3 web, R4 sport × offer, R5 best-sellers)", cols, rows,
                                 "`audit.candidate_recall` (`models/audit/candidate_recall.sql`)"))

    # ---------------------------------------------------------------- item 9: technique comparisons
    if want("t13") and table_exists(con, "audit", "technique_comparisons"):
        cols, rows = q(con, """
            WITH l AS (SELECT * FROM audit.technique_comparisons QUALIFY ROW_NUMBER() OVER (PARTITION BY comparison, variant, country ORDER BY executed_at DESC) = 1),
            b AS (SELECT * FROM l WHERE role = 'baseline'), t AS (SELECT * FROM l WHERE role = 'technique')
            SELECT b.comparison, b.country, b.variant AS baseline, t.variant AS technique, b.rows AS rows_processed,
                   ROUND(b.wall_median_sec, 2) AS baseline_sec, ROUND(t.wall_median_sec, 2) AS technique_sec,
                   ROUND(b.wall_median_sec / NULLIF(t.wall_median_sec, 0), 1) AS speedup,
                   ROUND(b.peak_rss_gb, 2) AS baseline_peak_GB, ROUND(t.peak_rss_gb, 2) AS technique_peak_GB, b.reps, b.threads, b.memory_limit
            FROM b JOIN t USING (comparison, country) ORDER BY 1, 2""")
        index.append(write_table(out, "t13_technique_comparisons", "Four with / without technique comparisons (median wall time of child processes, peak RSS)", cols, rows,
                                 "`audit.technique_comparisons` (`evaluation/technique_comparisons.py`, `make techniques`)"))

    # ---------------------------------------------------------------- quality evidence: dbt tests and the leakage ledger
    if want("t14"):
        rows = []
        mf = pathlib.Path("dbt_multidim/target/manifest.json")
        if mf.exists():
            m = json.load(open(mf)); models = collections.Counter(); tests = collections.Counter(); singular = collections.Counter()
            models["source"] = len(m.get("sources", {}))   # declared source tables
            for n in m["nodes"].values():
                if n["resource_type"] == "model": models[n["path"].split("/")[0]] += 1
                if n["resource_type"] == "test":
                    deps = [d for d in n["depends_on"]["nodes"] if d.startswith("model.") and d in m["nodes"]]
                    layers = {m["nodes"][d]["path"].split("/")[0] for d in deps}
                    layer = "gold" if "gold" in layers else (sorted(layers)[0] if layers else "source")
                    tests[layer] += 1
                    if n.get("test_metadata") is None: singular[layer] += 1
            for layer in ["source", "staging", "silver", "quarantine", "audit", "gold"]:
                rows.append((layer, models.get(layer), tests.get(layer, 0), singular.get(layer, 0)))
        leak = con.execute("SELECT COUNT(*) FROM quarantine.leakage_violations").fetchone()[0] if table_exists(con, "quarantine", "leakage_violations") else None
        index.append(write_table(out, "t14_dbt_tests", "dbt models and tests per layer (generic + singular), from the compiled manifest", ["layer", "models", "tests", "singular_tests"], rows,
                                 "`dbt_multidim/target/manifest.json` (`dbt parse`)", f"Leakage ledger `quarantine.leakage_violations`: {fmt(leak)} rows."))

    # ---------------------------------------------------------------- Silver: channel, timezone, catalogue, members
    if want("t15"):
        cols, rows = q(con, """
            SELECT country_code, channel, COUNT(*) AS sale_lines, COUNT(DISTINCT store_id) AS business_units,
                   COUNT(*) FILTER (WHERE store_tz IS NULL) AS lines_without_unit_timezone,
                   ROUND(100.0 * COUNT(*) FILTER (WHERE store_tz IS NULL) / COUNT(*), 2) AS pct_country_timezone_fallback
            FROM silver.slv_fact_sales_line GROUP BY 1, 2 ORDER BY 1, 2""")
        index.append(write_table(out, "t15_channel_timezone", "Sale lines by channel and the timezone fallback (website units carry no timezone; the country's is used)", cols, rows,
                                 "`silver.slv_fact_sales_line` (`transaction_ts_utc` derivation)"))
    if want("t16"):
        cols, rows = q(con, """
            WITH sold AS (SELECT s.country_code, s.item_code FROM staging.stg_sales_detail s WHERE s.item_type = 'stock' AND s.item_operation_type = 'sale' GROUP BY ALL),
            cat AS (SELECT DISTINCT item_code FROM bronze.dim_item),
            dm AS (SELECT COUNT(*) AS catalogue_skus, COUNT(DISTINCT model_code) AS catalogue_models FROM silver.slv_dim_model),
            fx AS (SELECT COUNT(DISTINCT model_code) AS fixture_models FROM bronze.dim_item WHERE retail_univers_label = 'FIXT & FURNIT')
            SELECT sold.country_code, COUNT(*) AS skus_sold, COUNT(cat.item_code) AS skus_in_catalogue,
                   ROUND(100.0 * COUNT(cat.item_code) / COUNT(*), 2) AS pct_skus_in_catalogue, dm.catalogue_skus, dm.catalogue_models, fx.fixture_models
            FROM sold LEFT JOIN cat USING (item_code), dm, fx GROUP BY ALL ORDER BY 1""")
        index.append(write_table(out, "t16_catalogue", "Catalogue coverage of sold SKUs and the model-level catalogue after the fixture exclusion", cols, rows,
                                 "`bronze.dim_item`, `staging.stg_sales_detail`, `silver.slv_dim_model`"))
    if want("t17"):
        cols, rows = q(con, """
            WITH p AS (SELECT country_code, COUNT(*) AS member_profiles, COUNT(*) FILTER (WHERE is_excluded_account) AS excluded_accounts FROM silver.slv_member_profile GROUP BY 1),
            b AS (SELECT f.country_code, COUNT(DISTINCT b.transaction_id) AS transactions_with_member FROM silver.slv_member_bridge b JOIN silver.slv_fact_sales_line f USING (transaction_id) GROUP BY 1),
            s AS (SELECT p.country_code, COUNT(DISTINCT sa.member_id) AS members_with_sport, COUNT(DISTINCT sa.sport_id) AS sports
                  FROM silver.slv_member_sport_asof sa JOIN silver.slv_member_profile p USING (member_id) GROUP BY 1),
            st AS (SELECT p.country_code, COUNT(DISTINCT sd.member_id) AS members_with_store_state FROM silver.slv_member_store_daily sd JOIN silver.slv_member_profile p USING (member_id) GROUP BY 1)
            SELECT p.country_code, p.member_profiles, p.excluded_accounts, b.transactions_with_member, s.members_with_sport, s.sports, st.members_with_store_state
            FROM p LEFT JOIN b USING (country_code) LEFT JOIN s USING (country_code) LEFT JOIN st USING (country_code)
            WHERE p.country_code IN (SELECT UNNEST(string_split(?, ','))) ORDER BY 1""".replace("?", "'" + os.environ.get("COUNTRIES", "SG,TH,VN").replace(" ", "") + "'"))
        other = con.execute("SELECT COUNT(*), string_agg(DISTINCT country_code, ', ' ORDER BY country_code) FROM silver.slv_member_profile WHERE country_code NOT IN (SELECT UNNEST(string_split(?, ',')))",
                            [os.environ.get("COUNTRIES", "SG,TH,VN").replace(" ", "")]).fetchone()
        index.append(write_table(out, "t17_members", "Members: profiles, excluded accounts, favourite-sport and usual-store state", cols, rows,
                                 "`silver.slv_member_profile`, `silver.slv_member_bridge`, `silver.slv_member_sport_asof`, `silver.slv_member_store_daily`",
                                 "Profiles, sport and store state are counted by the member's account-creation country; transactions with a member by transaction country. "
                                 + (f"`d_member` also holds {other[0]:,} accounts registered in {other[1]}, outside the evaluation scope (issue #54)." if other and other[0] else "")))
    if want("t18"):
        cols, rows = q(con, """
            WITH t AS (SELECT country_code, transaction_id, COUNT(*) FILTER (WHERE item_operation_type = 'sale') AS s, COUNT(*) FILTER (WHERE item_operation_type = 'cancel') AS c
                       FROM staging.stg_sales_detail GROUP BY 1, 2 HAVING s > 0 AND c > 0)
            SELECT t.country_code, COUNT(*) AS transactions_with_sale_and_cancel,
                   COUNT(*) FILTER (WHERE EXISTS (SELECT 1 FROM silver.slv_fact_sales_line f WHERE f.transaction_id = t.transaction_id)) AS kept_with_positive_net_lines,
                   (SELECT COUNT(*) FROM silver.slv_fact_sales_line f WHERE f.country_code = t.country_code AND (f.qty <= 0 OR f.gmv_local <= 0)) AS kept_lines_with_nonpositive_qty_or_gmv
            FROM t GROUP BY 1 ORDER BY 1""")
        index.append(write_table(out, "t18_sale_cancel_check", "Sale − cancel netting check: transactions with both line kinds, and how many survive with positive net quantity", cols, rows,
                                 "`staging.stg_sales_detail`, `silver.slv_fact_sales_line` (RUNBOOK §5 manual check, automated)"))

    # ---------------------------------------------------------------- cost per model (item 8 input)
    if want("t19") and table_exists(con, "audit", "model_cost"):
        cols, rows = q(con, """SELECT layer, model_name, country_filter, ROUND(wall_time_sec, 1) AS wall_sec, ROUND(peak_rss_bytes / 1e9, 2) AS peak_rss_GB, output_rows, ROUND(output_bytes / 1e6, 1) AS output_MB
                                FROM audit.model_cost QUALIFY ROW_NUMBER() OVER (PARTITION BY model_name ORDER BY executed_at DESC) = 1 ORDER BY 1, 2""")
        index.append(write_table(out, "t19_model_cost", "Cost per dbt model rebuilt alone: wall time, peak RSS, output rows and bytes (latest profile per model)", cols, rows,
                                 "`audit.model_cost` (`evaluation/pipeline_cost_profiler.py`)"))

    # ---------------------------------------------------------------- QC-5 volume drift
    if want("t20") and table_exists(con, "audit", "volume_drift"):
        cols, rows = q(con, """SELECT table_name, country_code, COUNT(*) AS days, COUNT(*) FILTER (WHERE rows = 0) AS days_without_rows, COUNT(*) FILTER (WHERE flagged) AS flagged_days,
                                       COUNT(*) FILTER (WHERE flagged AND drift < 0) AS flagged_drops, COUNT(*) FILTER (WHERE probable_cause LIKE 'PUBLIC_HOLIDAY%' OR probable_cause LIKE 'ADJACENT%') AS holiday_related,
                                       COUNT(*) FILTER (WHERE probable_cause = 'DUPLICATED_EXPORT') AS duplicated_export, COUNT(*) FILTER (WHERE dup_factor > 1.2) AS days_with_export_duplicates,
                                       COUNT(*) FILTER (WHERE probable_cause = 'UNEXPLAINED') AS unexplained, MIN(calendar_date) AS first_day, MAX(calendar_date) AS last_day
                                FROM audit.volume_drift GROUP BY 1, 2 ORDER BY 1, 2""")
        index.append(write_table(out, "t20_volume_drift", "QC-5 volume drift per table × country: days, flagged days (|drift| > 50 % vs the same-weekday 28-day mean) and probable causes", cols, rows,
                                 "`audit.volume_drift` (`sql/audit_checks.sql` 4e, `make gates`)"))
        cols, rows = q(con, """SELECT table_name, country_code, calendar_date, day_of_week, rows, distinct_lines, dup_factor, mean_same_weekday_28d, drift, probable_cause
                                FROM audit.volume_drift WHERE flagged AND probable_cause NOT LIKE 'PUBLIC_HOLIDAY%' ORDER BY 1, 2, 3""")
        index.append(write_table(out, "t20b_volume_drift_days", "QC-5 flagged days other than public holidays (to review)", cols, rows, "`audit.volume_drift`"))

    write_index(out)


def write_index(out):
    """INDEX.md lists every table present in `out` (not only the ones of this run), with its title, source and generation stamp,
    so that a partial run (--only) or a copy from another machine never drops entries."""
    lines = []
    for f in sorted(out.glob("t*.md")):
        text = f.read_text(); title = text.splitlines()[0].lstrip("# ").strip()
        m = re.search(r"\*Source:\* (.*?)\. \*Generated:\* (.*?) by `tools/report_tables.py`, `COUNTRY_FILTER=([A-Z]+)`", text, re.S)
        src, when, cf = (m.group(1), m.group(2), m.group(3)) if m else ("", "", "")
        lines.append(f"- [{title}]({f.name}) — {src} *({cf}, {when})*" if m else f"- [{title}]({f.name})")
    (out / "INDEX.md").write_text(redact("\n".join([
        "# Report tables", "",
        f"Index rebuilt {NOW} by `tools/report_tables.py` (`make report-tables`, or `--index-only`). Each file carries its source, the country filter of the build "
        "that produced it and its generation time; the CSV next to it holds the same rows. Tables generated with `COUNTRY_FILTER=ALL` come from the three-country "
        "server build, `VN` ones from the laptop; regenerate on the server after each pipeline stage so that the stamps converge.", "", *lines, ""])))
    print("→", out / "INDEX.md", f"({len(lines)} tables)")


if __name__ == "__main__":
    main()
