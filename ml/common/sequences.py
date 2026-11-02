"""ML-05 — Behaviour sequences at each anchor: ml.seq_purchase_at_anchor and ml.seq_web_at_anchor.

One row per anchor (default: every is_used anchor of gold.anchor_grid), with the max_len most recent elements strictly before the
anchor date, ordered oldest → newest (the last element is the latest), its length and source_ts_max (latest input timestamp,
asserted < anchor date by ml/common/pit.py).
  purchase element: one (transaction, model) line — model_code, sport department, days_before, unit_price (local), qty, discount, channel
  web element:      one intent event on a model (config web_events) in the web_window_days before the anchor, attribution known
                    at the anchor (identity_verified_ts ≤ anchor, as R3) — model_code, event, days_before
Usage: python ml/common/sequences.py [--anchors used]   →  data/ml/features/seq_*.parquet + views ml.seq_*"""
import argparse, os, sys, time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import connect, load_config, ml_path, publish_view
from ml.common.pit import assert_pit


def purchase_seq_sql(anchors, lines, max_len):
    """anchors(member_id, country_code, anchor_date, split); lines = silver.slv_fact_sales_line or a stand-in with its columns."""
    return f"""
    WITH a AS (SELECT member_id, country_code, anchor_date, split FROM {anchors}),
    l AS (SELECT member_id, transaction_id, model_code, ANY_VALUE(sport_department_code) AS dept, transaction_date,
                 MAX(transaction_ts_local) AS ts_local, SUM(qty) AS qty, SUM(gmv_local) AS gmv_local,
                 BOOL_OR(bought_with_discount) AS discount, ANY_VALUE(channel) AS channel
          FROM {lines} WHERE member_id IN (SELECT member_id FROM a) AND model_code IS NOT NULL
          GROUP BY member_id, transaction_id, model_code, transaction_date),
    j AS (SELECT a.member_id, a.country_code, a.anchor_date, a.split, l.*,
                 ROW_NUMBER() OVER (PARTITION BY a.member_id, a.anchor_date
                                    ORDER BY l.ts_local DESC, l.transaction_id DESC, l.model_code) AS rn
          FROM a JOIN l ON l.member_id = a.member_id AND l.transaction_date < a.anchor_date
          QUALIFY rn <= {int(max_len)})
    SELECT a.member_id, a.country_code, a.anchor_date, a.split, COALESCE(s.seq_len, 0) AS seq_len, s.seq, s.source_ts_max
    FROM a LEFT JOIN (
        SELECT member_id, anchor_date, COUNT(*) AS seq_len,
               LIST(STRUCT_PACK(model_code := model_code, dept := dept, days_before := anchor_date - transaction_date,
                                unit_price := gmv_local / NULLIF(qty, 0), qty := qty, discount := discount, channel := channel)
                    ORDER BY rn DESC) AS seq,
               MAX(ts_local) AS source_ts_max
        FROM j GROUP BY member_id, anchor_date) s USING (member_id, anchor_date)"""


def web_seq_sql(anchors, web, max_len, window_days, events):
    ev = ", ".join(f"'{e}'" for e in events)
    return f"""
    WITH a AS (SELECT member_id, country_code, anchor_date, split FROM {anchors}),
    w AS (SELECT member_id, model_code, event_name, event_ts_utc, event_date, identity_verified_ts FROM {web}
          WHERE member_id IN (SELECT member_id FROM a) AND model_code IS NOT NULL AND event_name IN ({ev})),
    j AS (SELECT a.member_id, a.anchor_date, w.model_code, w.event_name, w.event_ts_utc, w.event_date,
                 ROW_NUMBER() OVER (PARTITION BY a.member_id, a.anchor_date ORDER BY w.event_ts_utc DESC, w.model_code, w.event_name) AS rn
          FROM a JOIN w ON w.member_id = a.member_id AND w.event_date < a.anchor_date
                       AND w.event_date >= a.anchor_date - {int(window_days)}
                       AND w.identity_verified_ts <= CAST(a.anchor_date AS TIMESTAMP)
          QUALIFY rn <= {int(max_len)})
    SELECT a.member_id, a.country_code, a.anchor_date, a.split, COALESCE(s.seq_len, 0) AS seq_len, s.seq, s.source_ts_max
    FROM a LEFT JOIN (
        SELECT member_id, anchor_date, COUNT(*) AS seq_len,
               LIST(STRUCT_PACK(model_code := model_code, event := event_name, days_before := anchor_date - event_date)
                    ORDER BY rn DESC) AS seq,
               MAX(event_ts_utc) AS source_ts_max
        FROM j GROUP BY member_id, anchor_date) s USING (member_id, anchor_date)"""


ANCHOR_SETS = {
    "used": "SELECT member_id, country_code, anchor_date, split FROM lh.gold.anchor_grid WHERE is_used",
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--anchors", default="used", choices=sorted(ANCHOR_SETS))
    a = ap.parse_args()
    cfg = load_config("sequences")
    con = connect()
    con.execute(f"CREATE TEMP VIEW anchors AS {ANCHOR_SETS[a.anchors]}")
    jobs = {"seq_purchase_at_anchor": purchase_seq_sql("anchors", "lh.silver.slv_fact_sales_line", cfg["max_len"]),
            "seq_web_at_anchor": web_seq_sql("anchors", "lh.gold.gld_web_stitched", cfg["max_len"], cfg["web_window_days"], cfg["web_events"])}
    suffix = "" if a.anchors == "used" else f"_{a.anchors}"
    written = {}
    for name, sql in jobs.items():
        t0 = time.time()
        path = ml_path("features", f"{name}{suffix}.parquet")
        con.execute(f"COPY ({sql}) TO '{path}' (FORMAT parquet, COMPRESSION zstd)")
        rel = f"read_parquet('{path}')"
        assert_pit(con, rel)
        stats = con.execute(f"""SELECT COUNT(*), AVG(seq_len), AVG((seq_len > 0)::INT), AVG((seq_len = {cfg['max_len']})::INT)
                                FROM {rel}""").fetchone()
        by_split = con.execute(f"SELECT split, COUNT(*), AVG(seq_len), AVG((seq_len > 0)::INT) FROM {rel} GROUP BY 1 ORDER BY 1").fetchall()
        written[name + suffix] = path
        print(f"{name}{suffix}: rows {stats[0]:,}  mean len {stats[1]:.1f}  non-empty {stats[2]:.1%}  full ({cfg['max_len']}) {stats[3]:.1%}  "
              f"{time.time() - t0:.0f}s")
        for s, n, ml, ne in by_split:
            print(f"    {s:<6} rows {n:,}  mean len {ml:.1f}  non-empty {ne:.1%}")
    con.close()   # the lakehouse is attached read-only above; the views need a write connection
    for view, path in written.items():
        publish_view(view, path)
        print(f"→ ml.{view}")


if __name__ == "__main__":
    sys.exit(main())
