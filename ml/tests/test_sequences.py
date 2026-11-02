import datetime as dt
import pandas as pd
from ml.common.data import connect
from ml.common.pit import assert_pit
from ml.common.sequences import purchase_seq_sql, web_seq_sql

T = pd.Timestamp


def fixture_con():
    con = connect(read_lakehouse=False)
    con.register("anchors", pd.DataFrame({"member_id": ["a", "a", "b"], "country_code": "VN", "split": "train",
                                          "anchor_date": [dt.date(2024, 3, 4), dt.date(2024, 3, 11), dt.date(2024, 3, 4)]}))
    lines = pd.DataFrame([
        # member, transaction, model, date, qty, gmv
        ("a", "t1", "m1", T("2024-02-01 10:00"), 1, 10.0),
        ("a", "t1", "m1", T("2024-02-01 10:00"), 1, 10.0),   # two items of one model in one transaction → one element
        ("a", "t2", "m2", T("2024-03-01 09:00"), 1, 30.0),
        ("a", "t3", "m3", T("2024-03-04 08:00"), 1, 50.0),   # on the anchor date: excluded from the 03-04 anchor
        ("a", None, None, T("2024-02-20 08:00"), 1, 5.0),     # no model: dropped
    ], columns=["member_id", "transaction_id", "model_code", "transaction_ts_local", "qty", "gmv_local"])
    lines["transaction_date"] = lines["transaction_ts_local"].dt.date
    lines["sport_department_code"], lines["bought_with_discount"], lines["channel"] = 7, False, "offline"
    con.register("lines", lines)
    web = pd.DataFrame([
        ("a", "m9", "product_page_viewed", T("2024-03-02 12:00"), T("2024-03-01")),
        ("a", "m9", "product_list_viewed", T("2024-03-02 12:01"), T("2024-03-01")),   # impression: not in the event list
        ("a", "m8", "product_added_to_cart", T("2024-03-03 12:00"), T("2024-03-05")), # identity linked after the 03-04 anchor
        ("a", "m7", "product_page_viewed", T("2023-08-01 12:00"), T("2023-08-01")),   # outside the 180-day window
    ], columns=["member_id", "model_code", "event_name", "event_ts_utc", "identity_verified_ts"])
    web["event_date"] = web["event_ts_utc"].dt.date
    con.register("web", web)
    return con


def test_purchase_sequence():
    con = fixture_con()
    r = con.execute(f"SELECT * FROM ({purchase_seq_sql('anchors', 'lines', 50)}) ORDER BY member_id, anchor_date").df()
    a1, a2, b = r.iloc[0], r.iloc[1], r.iloc[2]
    assert [e["model_code"] for e in a1["seq"]] == ["m1", "m2"]                 # oldest → newest, anchor-day purchase excluded
    assert a1["seq"][0]["qty"] == 2 and a1["seq"][0]["unit_price"] == 10.0 and a1["seq"][1]["days_before"] == 3
    assert [e["model_code"] for e in a2["seq"]] == ["m1", "m2", "m3"]
    assert b["seq_len"] == 0 and pd.isna(b["seq"])
    con.register("ps", r)
    assert_pit(con, "ps")


def test_purchase_sequence_truncates_to_latest():
    con = fixture_con()
    r = con.execute(f"SELECT * FROM ({purchase_seq_sql('anchors', 'lines', 2)}) WHERE anchor_date = DATE '2024-03-11'").df()
    assert [e["model_code"] for e in r.iloc[0]["seq"]] == ["m2", "m3"]


def test_web_sequence():
    con = fixture_con()
    sql = web_seq_sql("anchors", "web", 50, 180, ["product_page_viewed", "product_added_to_cart"])
    r = con.execute(f"SELECT * FROM ({sql}) ORDER BY member_id, anchor_date").df()
    assert [e["model_code"] for e in r.iloc[0]["seq"]] == ["m9"]               # cart on m8 not attributable yet; list view dropped
    assert [e["model_code"] for e in r.iloc[1]["seq"]] == ["m9", "m8"]
    assert r.iloc[2]["seq_len"] == 0
    con.register("ws", r)
    assert_pit(con, "ws")
