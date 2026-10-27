"""Rebuild the bronze.* views over an existing data/bronze/ directory, without touching the raw files.
Use it when Bronze Parquet was copied from another machine: the views stored in a copied lakehouse.duckdb point to the
other machine's absolute paths, so create a fresh database and run this instead of `make bronze`.
Tables are read from the contract list; a table with no Parquet under data/bronze/<table>/ is reported and skipped.
Run: make bronze-views"""
import duckdb, yaml, os, pathlib
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
for table in yaml.safe_load(open("ingestion/table_contracts.yml")):
    dst = ROOT / "bronze" / table
    if not any(dst.rglob("*.parquet")):
        print(f"{table:28s} SKIPPED — no Parquet under {dst}"); continue
    con.execute(f"CREATE OR REPLACE VIEW bronze.{table} AS SELECT * FROM read_parquet('{dst}/**/*.parquet', hive_partitioning=true)")
    rows = con.execute(f"SELECT COUNT(*) FROM bronze.{table}").fetchone()[0]
    print(f"{table:28s} rows={rows:>12,d}")
con.close()
