"""Shared access to the lakehouse and to data/ml/ for the ml/ package.

The lakehouse is attached read-only (alias lh) so that several jobs can read it at once; ml outputs are written as Parquet under
data/ml/ and exposed to dbt and DBeaver as views ml.<name> by publish_view(), which holds the write lock only for that statement."""
import os, pathlib, duckdb, yaml
from dotenv import load_dotenv

ROOT = pathlib.Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
ML_DIR = os.path.join(os.environ.get("DATA_ROOT", str(ROOT / "data")), "ml")


def connect(read_lakehouse=True, threads=None):
    con = duckdb.connect()
    con.execute(f"SET memory_limit='{os.environ.get('DUCKDB_MEMORY', '10GB')}'")
    con.execute(f"SET threads={int(threads or os.environ.get('DUCKDB_THREADS', '6'))}")
    con.execute("SET preserve_insertion_order=false")
    temp = os.path.join(os.environ.get("DATA_ROOT", str(ROOT / "data")), "duck_temp")
    if os.path.isdir(temp):
        con.execute(f"SET temp_directory='{temp}'")
    if read_lakehouse:
        con.execute(f"ATTACH '{os.environ['DUCKDB_PATH']}' AS lh (READ_ONLY)")
    return con


def split_windows():
    """The six split dates of evaluation/split.yml as datetime.date."""
    import datetime as dt
    sp = yaml.safe_load(open(ROOT / "evaluation" / "split.yml"))
    return {k: dt.date.fromisoformat(v) for k, v in sp.items() if k.endswith(("_lo", "_hi"))}


def ml_path(*parts):
    p = os.path.join(ML_DIR, *parts)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p


def load_config(name):
    return yaml.safe_load(open(ROOT / "ml" / "config" / f"{name}.yml"))


def publish_view(name, parquet_path):
    """CREATE OR REPLACE VIEW ml.<name> over a Parquet file or glob (absolute path, like the bronze views)."""
    con = duckdb.connect(os.environ["DUCKDB_PATH"])
    try:
        con.execute("CREATE SCHEMA IF NOT EXISTS ml")
        con.execute(f"CREATE OR REPLACE VIEW ml.{name} AS SELECT * FROM read_parquet('{os.path.abspath(parquet_path)}')")
    finally:
        con.close()
