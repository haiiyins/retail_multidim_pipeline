"""Step 8 (optional) — Drain the three replay topics: contract checks → bronze/<table>_stream Parquet, rejects → quarantine.rejected_stream_events.

  raw.tracking        → tracking_ecom_events_stream     partition country_code, year, month   (from date)
  raw.favorite_sport  → f_member_favorite_sport_stream  partition country_code, year          (from event_datetime_utc)
  raw.member_purchase → f_member_purchase_stream        partition member_country_code, year, month (from association_datetime_utc)

A message is rejected when it is not a JSON object, a column listed under `not_null` for the table in table_contracts.yml
(or its event-time column) is missing, or — tracking only — is_event_to_use is not true (_errors is not tested: in the Parquet
export it is non-empty on every event). The run reads each topic from the beginning up to the offsets present at start, with
a fresh consumer and no committed offsets, and first empties the stream folders and the topic's rows in the reject table, so a
rerun gives the same result. The script holds the DuckDB write lock while it runs: close DBeaver and do not run dbt / loaders.

Env: STREAM_TOPICS (comma list, default all three), STREAM_IDLE_TIMEOUT (seconds without a message before giving up, default 60),
KAFKA_BOOTSTRAP, DATA_ROOT, DUCKDB_PATH.
"""
import duckdb, json, os, pathlib, shutil, sys, tempfile, time
import yaml
from dotenv import load_dotenv
from confluent_kafka import Consumer, TopicPartition
load_dotenv()

BATCH = 20000
ROOT = pathlib.Path(os.environ["DATA_ROOT"])
CONTRACTS = yaml.safe_load(open(pathlib.Path(__file__).with_name("table_contracts.yml")))
YEAR, MONTH = "EXTRACT(year FROM {c})::INTEGER", "EXTRACT(month FROM {c})::INTEGER"
TOPICS = {
    "raw.tracking": dict(
        table="tracking_ecom_events", time_col="date", partition=["country_code", "year", "month"],
        cols={"id": "VARCHAR", "session_id": "VARCHAR", "name": "VARCHAR", "country_code": "VARCHAR", "platform": "VARCHAR",
              "timestamp_utc": "TIMESTAMP", "date": "DATE", "is_event_to_use": "BOOLEAN", "_errors": "JSON", "metadata": "JSON"},
        derived={"year": YEAR.format(c="date"), "month": MONTH.format(c="date")}),
    "raw.favorite_sport": dict(
        table="f_member_favorite_sport", time_col="event_datetime_utc", partition=["country_code", "year"],
        cols={"member_id": "VARCHAR", "sport_id": "BIGINT", "event_type": "VARCHAR", "event_datetime_utc": "TIMESTAMPTZ",
              "tech_integration_datetime_utc": "TIMESTAMPTZ", "country_code": "VARCHAR"},
        derived={"year": YEAR.format(c="event_datetime_utc")}),
    "raw.member_purchase": dict(
        table="f_member_purchase", time_col="association_datetime_utc", partition=["member_country_code", "year", "month"],
        cols={"transaction_id": "VARCHAR", "member_id": "VARCHAR", "association_datetime_utc": "TIMESTAMP",
              "transaction_source": "VARCHAR", "transaction_operator": "VARCHAR", "member_country_code": "VARCHAR"},
        derived={"year": YEAR.format(c="association_datetime_utc"), "month": MONTH.format(c="association_datetime_utc")}),
}
for cfg in TOPICS.values():
    cfg["required"] = list(dict.fromkeys(CONTRACTS[cfg["table"]].get("not_null", []) + [cfg["time_col"]]))
    cfg["dst"] = ROOT / "bronze" / f"{cfg['table']}_stream"


def check(cfg, raw):
    """Return (None, record) for a valid message, else (reason, None)."""
    try:
        rec = json.loads(raw)
    except ValueError:
        return "invalid_json", None
    if not isinstance(rec, dict):
        return "not_a_json_object", None
    for col in cfg["required"]:
        if rec.get(col) in (None, ""):
            return f"missing_{col}", None
    if cfg["table"] == "tracking_ecom_events" and rec.get("is_event_to_use") is not True:
        return "is_event_to_use_not_true", None
    return None, rec


def flush(con, cfg, lines):
    """Write the valid message strings of one batch to the stream folder (explicit column types, no schema drift)."""
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "batch.ndjson"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        cols = ", ".join(f"'{k}': '{v}'" for k, v in cfg["cols"].items())
        derived = ", ".join(f"{e} AS {k}" for k, e in cfg["derived"].items())
        con.execute(f"COPY (SELECT *, {derived} FROM read_json(?, format='newline_delimited', columns={{{cols}}})) TO '{cfg['dst'].as_posix()}' "
                    f"(FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY ({', '.join(cfg['partition'])}), APPEND)", [f.as_posix()])


def main():
    wanted = [t.strip() for t in os.environ.get("STREAM_TOPICS", ",".join(TOPICS)).split(",") if t.strip()]
    unknown = [t for t in wanted if t not in TOPICS]
    if unknown:
        sys.exit(f"unknown topic(s) {unknown}; choose from {list(TOPICS)}")
    idle_limit = float(os.environ.get("STREAM_IDLE_TIMEOUT", "60"))

    con = duckdb.connect(os.environ["DUCKDB_PATH"])
    con.execute("SET TimeZone = 'UTC'")  # year of the TIMESTAMPTZ partition is the UTC year, as in batch Bronze
    con.execute("CREATE SCHEMA IF NOT EXISTS quarantine")
    con.execute("CREATE TABLE IF NOT EXISTS quarantine.rejected_stream_events(topic VARCHAR, kafka_partition INTEGER, kafka_offset BIGINT, "
                "reason VARCHAR, payload VARCHAR, rejected_at TIMESTAMP DEFAULT current_timestamp)")
    for t in wanted:
        con.execute("DELETE FROM quarantine.rejected_stream_events WHERE topic = ?", [t])
        dst = TOPICS[t]["dst"]
        if dst.name.endswith("_stream") and dst.exists():
            shutil.rmtree(dst)
        dst.parent.mkdir(parents=True, exist_ok=True)  # PARTITION_BY creates the folder but not its parent

    c = Consumer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092"), "group.id": f"bronze-sink-{int(time.time())}",
                  "enable.auto.commit": False, "auto.offset.reset": "earliest"})
    meta = c.list_topics(timeout=15)
    parts, end, remaining = [], {}, set()
    for t in wanted:
        if t not in meta.topics or meta.topics[t].error is not None:
            sys.exit(f"topic {t} not found on the broker; run ingestion/kafka_producer_replay.py first")
        for p in meta.topics[t].partitions:
            lo, hi = c.get_watermark_offsets(TopicPartition(t, p), timeout=15)
            parts.append(TopicPartition(t, p, lo)); end[(t, p)] = hi
            if hi > lo:  # drained once the message just before this end offset has been read
                remaining.add((t, p))
    c.assign(parts)

    ok = {t: 0 for t in wanted}; bad = {t: 0 for t in wanted}
    buf = {t: [] for t in wanted}; meta_buf = {t: [] for t in wanted}; rejects = []
    t0 = time.time(); last_msg = time.time()

    def flush_rejects():
        if rejects:
            con.executemany("INSERT INTO quarantine.rejected_stream_events(topic, kafka_partition, kafka_offset, reason, payload) VALUES (?, ?, ?, ?, ?)", rejects)
            rejects.clear()

    def flush_topic(t):
        if not buf[t]:
            return
        try:
            flush(con, TOPICS[t], buf[t])
        except Exception as e:  # a value the declared type cannot hold: keep the batch in the reject table instead of losing it
            print(f"{t}: batch of {len(buf[t])} not written ({e}); moved to quarantine", file=sys.stderr)
            for (part, off), raw in zip(meta_buf[t], buf[t]):
                rejects.append((t, part, off, "batch_write_error", raw))
            ok[t] -= len(buf[t]); bad[t] += len(buf[t])
        buf[t].clear(); meta_buf[t].clear()

    while remaining:
        msg = c.poll(1.0)
        if msg is None:
            if time.time() - last_msg > idle_limit:
                sys.exit(f"no message for {idle_limit:.0f} s but {sorted(remaining)} not drained")
            continue
        if msg.error():
            sys.exit(f"consumer error: {msg.error()}")
        last_msg = time.time()
        t = msg.topic(); raw = msg.value().decode("utf-8", errors="replace")
        reason, _ = check(TOPICS[t], raw)
        if reason:
            rejects.append((t, msg.partition(), msg.offset(), reason, raw)); bad[t] += 1
        else:
            buf[t].append(raw); meta_buf[t].append((msg.partition(), msg.offset())); ok[t] += 1
        if msg.offset() + 1 >= end[(t, msg.partition())]:
            remaining.discard((t, msg.partition()))
        if len(buf[t]) >= BATCH:
            flush_topic(t); print(f"{t}: ok {ok[t]} bad {bad[t]}", flush=True)
        if len(rejects) >= BATCH:
            flush_rejects()
    for t in wanted:
        flush_topic(t)
    flush_rejects()
    c.close()

    dt = max(time.time() - t0, 1e-9)
    for t in wanted:
        print(f"{t}: ok {ok[t]}, bad {bad[t]}")
    total = sum(ok.values()) + sum(bad.values())
    print(f"total {total} messages in {dt:.1f} s = {total / dt:,.0f} msg/s")
    con.close()


if __name__ == "__main__":
    main()
