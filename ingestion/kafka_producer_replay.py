"""Step 8 (optional) — Replay the Bronze event tables into Redpanda, one topic per table, each ordered by its event time.

Topic, message key, order column, event-date column and the columns a message carries are the `stream:` block of the table in
table_contracts.yml (ingestion/stream_contracts.py, shared with the consumer and QC-7). The month filter uses event_date, not the
tech_* partition columns: f_member_purchase.tech_year / tech_month hold 1970-01 and values that disagree with association_datetime_utc.

Env: REPLAY_COUNTRY (default XX), REPLAY_MONTH (YYYY-MM, default 2025-01), REPLAY_TOPICS (comma list of topic names, default all),
KAFKA_BOOTSTRAP, DUCKDB_PATH.
Each message value is the row's message columns as JSON (nested metadata / _errors stay JSON, not Python repr).
"""
import duckdb, os, sys, time
from dotenv import load_dotenv
from confluent_kafka import Producer
from stream_contracts import BY_TOPIC, message_select, month_bounds, topics_from_env
load_dotenv()

BATCH = 20000


def replay_sql(s):
    """Rows of one table for a country-month as (message key, JSON value), ordered by event time; parameters country, lo, hi.
    TimeZone is UTC for the session, so the TIMESTAMPTZ columns compare as UTC."""
    return f"""SELECT {s['message_key']}::VARCHAR AS k, to_json(r)::VARCHAR AS v
               FROM (SELECT {message_select(s)} FROM bronze.{s['table']}
                     WHERE {s['country_col']} = ? AND {s['event_date']} >= ?::TIMESTAMP AND {s['event_date']} < ?::TIMESTAMP
                     ORDER BY {s['order_by']}, {s['message_key']}) r"""


def replay(con, p, topic, s, country, month):
    lo, hi = month_bounds(month)
    cur = con.execute(replay_sql(s), [country, lo, hi])
    sent = failed = 0

    def on_delivery(err, msg):
        nonlocal failed
        if err is not None:
            failed += 1

    t0 = time.time()
    while rows := cur.fetchmany(BATCH):
        for k, v in rows:
            while True:
                try:
                    p.produce(topic, key=k, value=v, on_delivery=on_delivery); break
                except BufferError:  # local queue full: serve delivery reports, then retry
                    p.poll(0.5)
            p.poll(0)
        sent += len(rows)
        p.flush()
        print(f"{topic}: {sent}", flush=True)
    p.flush()
    dt = max(time.time() - t0, 1e-9)
    print(f"{topic}: sent {sent}, failed {failed}, {sent / dt:,.0f} msg/s in {dt:.1f} s")
    return failed


def main():
    country = os.environ.get("REPLAY_COUNTRY", "XX")
    month = os.environ.get("REPLAY_MONTH", "2025-01")
    wanted = topics_from_env("REPLAY_TOPICS")
    p = Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092")})
    con = duckdb.connect(os.environ["DUCKDB_PATH"], read_only=True)
    con.execute("SET TimeZone = 'UTC'")
    failed = sum(replay(con, p, t, BY_TOPIC[t], country, month) for t in wanted)
    if failed:
        sys.exit(f"{failed} message(s) were not delivered")


if __name__ == "__main__":
    main()
