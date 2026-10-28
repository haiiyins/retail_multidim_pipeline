"""Step 8 (optional) — Replay the three Bronze event tables into Redpanda, each ordered by its event time.

  raw.tracking        bronze.tracking_ecom_events    key session_id     ordered by timestamp_utc
  raw.favorite_sport  bronze.f_member_favorite_sport key member_id      ordered by event_datetime_utc
  raw.member_purchase bronze.f_member_purchase       key transaction_id ordered by association_datetime_utc

Env: REPLAY_COUNTRY (default XX), REPLAY_MONTH (YYYY-MM, default 2025-01), REPLAY_TOPICS (comma list of topic
names, default all three), KAFKA_BOOTSTRAP, DUCKDB_PATH.
Each message value is the whole row as JSON (nested metadata / _errors stay JSON, not Python repr).
"""
import duckdb, os, sys, time
from datetime import date
from dotenv import load_dotenv
from confluent_kafka import Producer
load_dotenv()

BATCH = 20000
# event time is also the month filter: f_member_purchase.tech_year / tech_month hold 1970-01 and other
# values that disagree with association_datetime_utc, so they are not used.
TOPICS = {
    "raw.tracking": dict(
        key="session_id", ts="timestamp_utc", country="country_code", month_expr="date::DATE",
        cols="id, session_id, name, country_code, platform, timestamp_utc::VARCHAR AS timestamp_utc, "
             "date::VARCHAR AS date, is_event_to_use, to_json(_errors) AS _errors, to_json(metadata) AS metadata",
        table="bronze.tracking_ecom_events"),
    "raw.favorite_sport": dict(
        key="member_id", ts="event_datetime_utc", country="country_code", month_expr="event_datetime_utc",
        cols="member_id, sport_id, event_type, event_datetime_utc::VARCHAR AS event_datetime_utc, "
             "tech_integration_datetime_utc::VARCHAR AS tech_integration_datetime_utc, country_code",
        table="bronze.f_member_favorite_sport"),
    "raw.member_purchase": dict(
        key="transaction_id", ts="association_datetime_utc", country="member_country_code",
        month_expr="association_datetime_utc",
        cols="transaction_id, member_id, association_datetime_utc::VARCHAR AS association_datetime_utc, "
             "transaction_source, transaction_operator, member_country_code",
        table="bronze.f_member_purchase"),
}


def month_bounds(month):
    y, m = map(int, month.split("-"))
    start = date(y, m, 1)
    end = date(y + (m == 12), m % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


def replay(con, p, topic, cfg, country, month):
    lo, hi = month_bounds(month)
    # TimeZone is UTC for the session, so the TIMESTAMPTZ columns compare as UTC
    cur = con.execute(
        f"""SELECT {cfg['key']}::VARCHAR AS k, to_json(s)::VARCHAR AS v
            FROM (SELECT {cfg['cols']} FROM {cfg['table']}
                  WHERE {cfg['country']} = ? AND {cfg['month_expr']} >= ?::TIMESTAMP AND {cfg['month_expr']} < ?::TIMESTAMP
                  ORDER BY {cfg['ts']}, {cfg['key']}) s""", [country, lo, hi])
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
    wanted = [t.strip() for t in os.environ.get("REPLAY_TOPICS", ",".join(TOPICS)).split(",") if t.strip()]
    unknown = [t for t in wanted if t not in TOPICS]
    if unknown:
        sys.exit(f"unknown topic(s) {unknown}; choose from {list(TOPICS)}")
    p = Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092")})
    con = duckdb.connect(os.environ["DUCKDB_PATH"], read_only=True)
    con.execute("SET TimeZone = 'UTC'")
    failed = sum(replay(con, p, t, TOPICS[t], country, month) for t in wanted)
    if failed:
        sys.exit(f"{failed} message(s) were not delivered")


if __name__ == "__main__":
    main()
