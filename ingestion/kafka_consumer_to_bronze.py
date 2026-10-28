"""Step 8 (optional) — Drain the replay topics: contract checks → bronze/<table>_stream Parquet, rejects → quarantine.rejected_stream_events.

Topic ↔ table, the message columns with their types, the event-date column and the stream partition are the `stream:` block of the
table in table_contracts.yml (ingestion/stream_contracts.py, shared with the producer and QC-7); year / month of the partition are
taken from event_date. A message is rejected when it is not a JSON object, a `not_null` column of the table (or its event_date
column) is missing, or the table's `require_true` column is not true (tracking: is_event_to_use; _errors is not tested: in the
Parquet export it is non-empty on every event). The run reads each topic from the beginning up to the offsets present at start, with
a fresh consumer and no committed offsets, and first empties the stream folders and the topic's rows in the reject table, so a
rerun gives the same result. The script holds the DuckDB write lock while it runs: close DBeaver and do not run dbt / loaders.

Env: STREAM_TOPICS (comma list, default all), STREAM_IDLE_TIMEOUT (seconds without a message before giving up, default 60),
KAFKA_BOOTSTRAP, DATA_ROOT, DUCKDB_PATH.
"""
import duckdb, json, os, pathlib, shutil, sys, tempfile, time
from dotenv import load_dotenv
from confluent_kafka import Consumer, TopicPartition
from stream_contracts import BY_TOPIC, derived_partition, required_columns, topics_from_env
load_dotenv()

BATCH = 20000
ROOT = pathlib.Path(os.environ["DATA_ROOT"])
TOPICS = {t: dict(s, required=required_columns(s), derived=derived_partition(s), dst=ROOT / "bronze" / f"{s['table']}_stream")
          for t, s in BY_TOPIC.items()}


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
    flag = cfg.get("require_true")
    if flag and rec.get(flag) is not True:
        return f"{flag}_not_true", None
    return None, rec


def flush(con, cfg, lines):
    """Write the valid message strings of one batch to the stream folder (explicit column types, no schema drift)."""
    with tempfile.TemporaryDirectory() as tmp:
        f = pathlib.Path(tmp) / "batch.ndjson"
        f.write_text("\n".join(lines) + "\n", encoding="utf-8")
        cols = ", ".join(f"'{k}': '{v}'" for k, v in cfg["columns"].items())
        derived = ", ".join(f"{e} AS {k}" for k, e in cfg["derived"].items())
        con.execute(f"COPY (SELECT *, {derived} FROM read_json(?, format='newline_delimited', columns={{{cols}}})) TO '{cfg['dst'].as_posix()}' "
                    f"(FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY ({', '.join(cfg['partition'])}), APPEND)", [f.as_posix()])


def main():
    wanted = topics_from_env("STREAM_TOPICS")
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
