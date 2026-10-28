"""QC-7 (optional streaming lane) — batch Bronze vs stream Bronze, rows and hash per country × day → audit.stream_reconciliation.

Run after ingestion/kafka_consumer_to_bronze.py for the same REPLAY_COUNTRY / REPLAY_MONTH. Per table both sides use the same
predicate and the same day: tracking_ecom_events by `date` (is_event_to_use only, as the consumer keeps), f_member_favorite_sport by
the UTC day of event_datetime_utc, f_member_purchase by the day of association_datetime_utc (tech_year / tech_month / tech_day are not
used: they hold 1970-01 and a bare day of month). Columns: n_* rows, d_* distinct business keys, h_* order-independent hash
(SUM of a row hash, so duplicated rows do not cancel as they would under XOR), diff_* = batch - stream, ok = all three agree.
A run replaces only its own slice of the table (REPLAY_COUNTRY × REPLAY_MONTH, all three tables), so SG, TH and VN results can sit side
by side. Exit status 1 when any country × day of this run differs.

Env: REPLAY_COUNTRY (default XX), REPLAY_MONTH (YYYY-MM, default 2025-01), DATA_ROOT, DUCKDB_PATH.
"""
import duckdb, os, pathlib, sys
from datetime import date
from dotenv import load_dotenv
load_dotenv()

ROOT = pathlib.Path(os.environ["DATA_ROOT"])
COUNTRY = os.environ.get("REPLAY_COUNTRY", "XX")
MONTH = os.environ.get("REPLAY_MONTH", "2025-01")
Y, M = map(int, MONTH.split("-"))
LO, HI = date(Y, M, 1).isoformat(), date(Y + (M == 12), M % 12 + 1, 1).isoformat()

# prune: columns of the batch Parquet partitioning that are reliable for the table (purchase: tech_* are not, so the whole country is scanned)
TABLES = {
    "tracking_ecom_events": dict(
        country="country_code", day="date::DATE", when_batch="is_event_to_use AND year = {y} AND month = {m}", when_stream="TRUE",
        key="id", row="id, session_id, name, timestamp_utc"),
    "f_member_favorite_sport": dict(
        country="country_code", day="event_datetime_utc::DATE", when_batch="year = {y}", when_stream="TRUE",
        key="member_id, sport_id, event_datetime_utc", row="member_id, sport_id, event_type, event_datetime_utc"),
    "f_member_purchase": dict(
        country="member_country_code", day="association_datetime_utc::DATE", when_batch="TRUE", when_stream="TRUE",
        key="transaction_id, member_id",
        row="transaction_id, member_id, association_datetime_utc, transaction_source, transaction_operator"),
}


def side(cfg, source, when):
    """One side: per country × day rows, distinct keys, hash; `source` is a relation expression."""
    return f"""SELECT {cfg['country']} AS country_code, {cfg['day']} AS day, COUNT(*) AS n, COUNT(DISTINCT ({cfg['key']})) AS d,
                      SUM(hash({cfg['row']})::HUGEINT) AS h
               FROM {source}
               WHERE {cfg['country']} = ? AND {cfg['day']} >= ?::DATE AND {cfg['day']} < ?::DATE AND {when}
               GROUP BY 1, 2"""


def main():
    con = duckdb.connect(os.environ["DUCKDB_PATH"])
    con.execute("SET TimeZone = 'UTC'")
    con.execute("CREATE SCHEMA IF NOT EXISTS audit")
    parts = []
    for t, cfg in TABLES.items():
        stream = ROOT / "bronze" / f"{t}_stream"
        if not any(stream.glob("**/*.parquet")):
            sys.exit(f"no stream Parquet under {stream}; run ingestion/kafka_consumer_to_bronze.py first")
        b = side(cfg, f"bronze.{t}", cfg["when_batch"].format(y=Y, m=M))
        s = side(cfg, f"read_parquet('{stream.as_posix()}/**/*.parquet', hive_partitioning=true)", cfg["when_stream"])
        parts.append(f"""SELECT '{t}' AS tbl, COALESCE(b.country_code, s.country_code) AS country_code, COALESCE(b.day, s.day) AS day,
                          COALESCE(b.n, 0) AS n_batch, COALESCE(s.n, 0) AS n_stream, COALESCE(b.n, 0) - COALESCE(s.n, 0) AS diff_rows,
                          COALESCE(b.d, 0) AS d_batch, COALESCE(s.d, 0) AS d_stream, COALESCE(b.d, 0) - COALESCE(s.d, 0) AS diff_distinct,
                          b.h AS h_batch, s.h AS h_stream, b.h IS NOT DISTINCT FROM s.h AS hash_match
                   FROM ({b}) b FULL OUTER JOIN ({s}) s USING (country_code, day)""")
    all_params = [COUNTRY, LO, HI] * (2 * len(TABLES))
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
