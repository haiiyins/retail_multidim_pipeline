"""QC-7 (optional streaming lane) — batch Bronze vs stream Bronze, rows and hash per country × day → audit.stream_reconciliation.

Run after ingestion/kafka_consumer_to_bronze.py for the same REPLAY_COUNTRY / REPLAY_MONTH. Tables, the day column (event_date), the
business key, the hash columns and the batch-side predicate (require_true plus pruning on the batch partition) are the `stream:` block
of table_contracts.yml (ingestion/stream_contracts.py, shared with the producer and the consumer), so both sides use the same predicate
and the same day: tracking_ecom_events by `date` (is_event_to_use only, as the consumer keeps), f_member_favorite_sport by the UTC day
of event_datetime_utc, f_member_purchase by the day of association_datetime_utc (tech_year / tech_month / tech_day are not used: they
hold 1970-01 and a bare day of month, so only the country is pruned). Columns: n_* rows, d_* distinct business keys, h_* order-independent
hash (SUM of a row hash, so duplicated rows do not cancel as they would under XOR), diff_* = batch - stream, ok = all three agree.
A run replaces only its own slice of the table (REPLAY_COUNTRY × REPLAY_MONTH, all tables), so SG, TH and VN results can sit side by
side. Exit status 1 when any country × day of this run differs.

Env: REPLAY_COUNTRY (default XX), REPLAY_MONTH (YYYY-MM, default 2025-01), DATA_ROOT, DUCKDB_PATH.
"""
import duckdb, os, pathlib, sys
from dotenv import load_dotenv
from stream_contracts import STREAM, batch_predicate, month_bounds
load_dotenv()

ROOT = pathlib.Path(os.environ["DATA_ROOT"])
COUNTRY = os.environ.get("REPLAY_COUNTRY", "XX")
MONTH = os.environ.get("REPLAY_MONTH", "2025-01")
Y, M = map(int, MONTH.split("-"))
LO, HI = month_bounds(MONTH)


def side(s, source, when):
    """One side: per country × day rows, distinct keys, hash; `source` is a relation expression."""
    day = f"{s['event_date']}::DATE"
    return f"""SELECT {s['country_col']} AS country_code, {day} AS day, COUNT(*) AS n, COUNT(DISTINCT ({', '.join(s['key'])})) AS d,
                      SUM(hash({', '.join(s['hash_columns'])})::HUGEINT) AS h
               FROM {source}
               WHERE {s['country_col']} = ? AND {day} >= ?::DATE AND {day} < ?::DATE AND {when}
               GROUP BY 1, 2"""


def main():
    con = duckdb.connect(os.environ["DUCKDB_PATH"])
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")
    parts = []
    for t, s in STREAM.items():
        stream = ROOT / "bronze" / f"{t}_stream"
        if not any(stream.glob("**/*.parquet")):
            sys.exit(f"no stream Parquet under {stream}; run ingestion/kafka_consumer_to_bronze.py first")
        b = side(s, f"bronze.{t}", batch_predicate(s, Y, M))
        q = side(s, f"read_parquet('{stream.as_posix()}/**/*.parquet', hive_partitioning=true)", "TRUE")
        parts.append(f"""SELECT '{t}' AS tbl, COALESCE(b.country_code, s.country_code) AS country_code, COALESCE(b.day, s.day) AS day,
                          COALESCE(b.n, 0) AS n_batch, COALESCE(s.n, 0) AS n_stream, COALESCE(b.n, 0) - COALESCE(s.n, 0) AS diff_rows,
                          COALESCE(b.d, 0) AS d_batch, COALESCE(s.d, 0) AS d_stream, COALESCE(b.d, 0) - COALESCE(s.d, 0) AS diff_distinct,
                          b.h AS h_batch, s.h AS h_stream, b.h IS NOT DISTINCT FROM s.h AS hash_match
                   FROM ({b}) b FULL OUTER JOIN ({q}) s USING (country_code, day)""")
    all_params = [COUNTRY, LO, HI] * (2 * len(STREAM))
    sql = " UNION ALL ".join(parts)
    con.execute(f"CREATE OR REPLACE TEMP TABLE qc7_run AS "
                f"SELECT *, (diff_rows = 0 AND diff_distinct = 0 AND hash_match) AS ok FROM ({sql}) ORDER BY tbl, country_code, day", all_params)
    con.execute("CREATE TABLE IF NOT EXISTS audit.stream_reconciliation AS SELECT * FROM qc7_run WHERE FALSE")
    con.execute("DELETE FROM audit.stream_reconciliation WHERE country_code = ? AND day >= ?::DATE AND day < ?::DATE", [COUNTRY, LO, HI])
    con.execute("INSERT INTO audit.stream_reconciliation SELECT * FROM qc7_run")
    for tbl, days, bad, nb, ns in con.execute(
            "SELECT tbl, COUNT(*), COUNT(*) FILTER (WHERE NOT ok), SUM(n_batch), SUM(n_stream) FROM qc7_run GROUP BY 1 ORDER BY 1").fetchall():
        print(f"{tbl}: {days} country-days, {bad} differ, rows batch {nb} / stream {ns}")
    bad_rows = con.execute("SELECT tbl, country_code, day, diff_rows, diff_distinct, hash_match FROM qc7_run WHERE NOT ok ORDER BY 1, 3").fetchall()
    for r in bad_rows[:50]:
        print("DIFF", *r)
    con.close()
    if bad_rows:
        sys.exit(1)
    print("QC-7 ok: diff = 0 for every replayed country-day")


if __name__ == "__main__":
    main()
