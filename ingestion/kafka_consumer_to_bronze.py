"""Step 8 (optional) — Micro-batch consumer: contract checks → bronze/tracking_ecom_events_stream, rejects → quarantine."""
import duckdb, os, json, pathlib
from dotenv import load_dotenv
from confluent_kafka import Consumer
load_dotenv()
ROOT = pathlib.Path(os.environ["DATA_ROOT"]); DST = ROOT / "bronze" / "tracking_ecom_events_stream"
c = Consumer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092"), "group.id": "bronze-sink", "auto.offset.reset": "earliest"})
c.subscribe(["raw.tracking"]); con = duckdb.connect(os.environ["DUCKDB_PATH"])
con.execute("CREATE TABLE IF NOT EXISTS quarantine.rejected_stream_events(payload JSON, reason VARCHAR, rejected_at TIMESTAMP DEFAULT current_timestamp)")
batch, ok, bad = [], 0, 0
def flush(batch):
    if not batch: return
    con.execute("CREATE OR REPLACE TEMP TABLE mb AS SELECT * FROM read_json_auto(?)", [json.dumps(batch)])
    con.execute(f"COPY (SELECT *, EXTRACT(year FROM date::DATE) year, EXTRACT(month FROM date::DATE) month FROM mb) TO '{DST}' "
                f"(FORMAT PARQUET, COMPRESSION ZSTD, PARTITION_BY (country_code, year, month), APPEND)")
while True:
    msg = c.poll(1.0)
    if msg is None:
        flush(batch); batch = []; continue
    rec = json.loads(msg.value())
    if not all(rec.get(k) for k in ("id", "session_id", "timestamp_utc", "country_code")) or str(rec.get("is_event_to_use")).lower() != "true" \
       or (rec.get("_errors") not in (None, "", "null", "List()")):
        con.execute("INSERT INTO quarantine.rejected_stream_events VALUES (?, 'contract_or_quality', current_timestamp)", [json.dumps(rec)]); bad += 1
    else:
        batch.append(rec); ok += 1
    if len(batch) >= 20000:
        flush(batch); batch = []; print("ok", ok, "bad", bad)
