"""Step 8 (optional) — the one definition of the streaming lane's topic ↔ table mapping, read from the `stream:` block of
table_contracts.yml by kafka_producer_replay.py, kafka_consumer_to_bronze.py and qc7_stream_reconciliation.py (issue #103).

Per event table the block gives: topic, message_key, order_by (producer order within the topic), event_date (month filter of the
producer, year / month of the stream partition, day of QC-7), require_true (a BOOLEAN that must be true on both lanes; tracking:
is_event_to_use), partition (of bronze/<table>_stream), columns (the columns a message carries, with the DuckDB type the consumer
declares) and hash_columns (QC-7 row hash). key, country_col, partition (batch Bronze) and not_null come from the table's contract.
"""
import os, pathlib, sys
from datetime import date
import yaml

CONTRACTS = yaml.safe_load(open(pathlib.Path(__file__).with_name("table_contracts.yml")))
STREAM = {t: dict(c["stream"], table=t, key=c["key"], country_col=c["country_col"], batch_partition=c.get("partition", []),
                  not_null=c.get("not_null", []))
          for t, c in CONTRACTS.items() if "stream" in c}
BY_TOPIC = {s["topic"]: s for s in STREAM.values()}


def month_bounds(month):
    """'YYYY-MM' -> (first day, first day of the next month) as ISO strings."""
    y, m = map(int, month.split("-"))
    return date(y, m, 1).isoformat(), date(y + (m == 12), m % 12 + 1, 1).isoformat()


def topics_from_env(name):
    """Topics selected by the comma list in env var `name` (unset = all); exits on an unknown topic."""
    wanted = [t.strip() for t in os.environ.get(name, ",".join(BY_TOPIC)).split(",") if t.strip()]
    unknown = [t for t in wanted if t not in BY_TOPIC]
    if unknown:
        sys.exit(f"unknown topic(s) {unknown}; choose from {list(BY_TOPIC)}")
    return wanted


def message_select(s):
    """Producer SELECT list: temporal columns as text, nested columns as JSON (not Python repr), the rest as they are."""
    return ", ".join(f"to_json({c}) AS {c}" if t == "JSON" else f"{c}::VARCHAR AS {c}" if t in ("TIMESTAMP", "TIMESTAMPTZ", "DATE") else c
                     for c, t in s["columns"].items())


def required_columns(s):
    """Consumer: columns that must be present and non-empty — the contract's not_null plus the event_date column."""
    return list(dict.fromkeys(s["not_null"] + [s["event_date"]]))


def derived_partition(s):
    """Consumer: year / month of the stream partition, taken from event_date (the session TimeZone is UTC)."""
    return {p: f"EXTRACT({p} FROM {s['event_date']})::INTEGER" for p in s["partition"] if p in ("year", "month")}


def batch_predicate(s, y, m):
    """QC-7 batch side: require_true, then pruning on the batch partition columns that follow the event date (year / month).
    f_member_purchase partitions by tech_year / tech_month, which do not, so only its country is pruned."""
    parts = [s["require_true"]] if s.get("require_true") else []
    parts += [f"{p} = {v}" for p, v in (("year", y), ("month", m)) if p in s["batch_partition"]]
    return " AND ".join(parts) or "TRUE"
