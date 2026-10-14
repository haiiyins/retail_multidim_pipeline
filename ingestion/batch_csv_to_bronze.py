"""Step 3 — Bronze: CSV → ZSTD Parquet partitioned per table_contracts.yml, rejects → quarantine, bronze.* views.
Run: make bronze"""
import duckdb, yaml, os, time, pathlib
from dotenv import load_dotenv
load_dotenv()
ROOT = pathlib.Path(os.environ["DATA_ROOT"]); DB = os.environ["DUCKDB_PATH"]
con = duckdb.connect(DB)
con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY','10GB')}'; SET threads={os.environ.get('DUCKDB_THREADS','6')}; "
            f"SET temp_directory='{ROOT}/duck_temp'; SET preserve_insertion_order=false;")
for ext in ("parquet", "json", "icu"):
    con.execute(f"INSTALL {ext}; LOAD {ext};")
for s in ["bronze", "staging", "silver", "gold", "quarantine", "audit", "ext"]:
    con.execute(f"CREATE SCHEMA IF NOT EXISTS {s}")
con.execute("""CREATE TABLE IF NOT EXISTS audit.pipeline_run_metrics(
  run_id VARCHAR, layer VARCHAR, model_name VARCHAR, country_filter VARCHAR,
  wall_time_sec DOUBLE, output_rows BIGINT, output_bytes BIGINT, executed_at TIMESTAMP DEFAULT current_timestamp)""")
contracts = yaml.safe_load(open("ingestion/table_contracts.yml"))
run_id = time.strftime("%Y%m%d-%H%M%S")
for table, c in contracts.items():
    src = ROOT / "raw_csv" / f"{table}.csv"; dst = ROOT / "bronze" / table
    if not src.exists():
        print(f"{table:28s} SKIPPED — {src} not found"); continue
    t0 = time.time()
    casts = c.get("cast", {})
    if casts:
        excl = ", ".join(f'"{k}"' for k in casts)
        sel = f"* EXCLUDE ({excl}), " + ", ".join(f'CAST("{k}" AS {v}) AS "{k}"' for k, v in casts.items())
    else:
        sel = "*"
    part = f"PARTITION_BY ({', '.join(c['partition'])})," if c.get("partition") else ""
    con.execute(f"""
      COPY (SELECT {sel}, current_timestamp AS _ingested_at, '{src.name}' AS _source_file
            FROM read_csv_auto('{src}', header=true, sample_size=500000, nullstr=['null',''], max_line_size=10000000,
                               store_rejects=true, rejects_table='rej_{table}', rejects_limit=1000000))
      TO '{dst}' (FORMAT PARQUET, COMPRESSION ZSTD, {part} OVERWRITE_OR_IGNORE 1)""")
    con.execute(f"CREATE OR REPLACE VIEW bronze.{table} AS SELECT * FROM read_parquet('{dst}/**/*.parquet', hive_partitioning=true)")
    rows = con.execute(f"SELECT COUNT(*) FROM bronze.{table}").fetchone()[0]
    has_rej = con.execute(f"SELECT COUNT(*) FROM information_schema.tables WHERE table_name='rej_{table}'").fetchone()[0]
    rej = 0
    if has_rej:
        rej = con.execute(f"SELECT COUNT(*) FROM rej_{table}").fetchone()[0]
        if rej:
            con.execute(f"CREATE OR REPLACE TABLE quarantine.rejects_{table} AS SELECT * FROM rej_{table}")
    size = sum(p.stat().st_size for p in dst.rglob("*.parquet"))
    con.execute("INSERT INTO audit.pipeline_run_metrics VALUES (?, 'bronze', ?, 'ALL', ?, ?, ?, current_timestamp)",
                [run_id, table, time.time() - t0, rows, size])
    print(f"{table:28s} rows={rows:>12,d} rejects={rej:>7,d} parquet={size/1e9:5.2f} GB  {time.time()-t0:6.0f}s")
con.close()
