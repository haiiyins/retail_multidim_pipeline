"""Step 8 (optional) — Replay web events from Bronze into topic raw.tracking ordered by timestamp_utc."""
import duckdb, os, json
from dotenv import load_dotenv
from confluent_kafka import Producer
load_dotenv()
country = os.environ.get("REPLAY_COUNTRY", "XX"); month = os.environ.get("REPLAY_MONTH", "2025-01")
p = Producer({"bootstrap.servers": os.environ.get("KAFKA_BOOTSTRAP", "localhost:19092")})
con = duckdb.connect(os.environ["DUCKDB_PATH"], read_only=True)
cur = con.execute(f"""SELECT id, session_id, name, country_code, platform, timestamp_utc::VARCHAR ts, date::VARCHAR d, is_event_to_use, _errors, metadata
                      FROM bronze.tracking_ecom_events WHERE country_code='{country}' AND strftime(date::DATE,'%Y-%m')='{month}'
                      ORDER BY timestamp_utc""")
n = 0
for row in cur.fetchall():
    rec = dict(zip(["id","session_id","name","country_code","platform","timestamp_utc","date","is_event_to_use","_errors","metadata"], row))
    p.produce("raw.tracking", key=str(rec["session_id"]), value=json.dumps(rec, default=str)); n += 1
    if n % 20000 == 0: p.flush(); print(n)
p.flush(); print("sent", n)
