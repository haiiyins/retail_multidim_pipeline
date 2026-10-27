"""Locate the raw input of one table under data/raw_csv and name its format.
Precedence: <table>.parquet (single re-exported file) > <table>/ (directory of Parquet parts, e.g. the chunked
Spark export of tracking_ecom_events: part-*.snappy.parquet) > <table>.csv (original export). Returns (path, kind)
with kind in {"parquet", "parquet-dir", "csv"}, or (None, None) when the table has no raw file."""
import pathlib

def raw_source(raw: pathlib.Path, table: str):
    f = raw / f"{table}.parquet"
    if f.exists(): return f, "parquet"
    d = raw / table
    if d.is_dir() and any(d.glob("*.parquet")): return d, "parquet-dir"
    c = raw / f"{table}.csv"
    if c.exists(): return c, "csv"
    return None, None

def parquet_reader(path: pathlib.Path, kind: str) -> str:
    """DuckDB read_parquet() expression for a single file or a directory of parts (schema differences unioned by name)."""
    return f"read_parquet('{path}')" if kind == "parquet" else f"read_parquet('{path}/*.parquet', union_by_name=true)"
