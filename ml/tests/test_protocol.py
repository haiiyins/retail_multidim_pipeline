import numpy as np, pandas as pd, pytest
from ml.eval.protocol import connect, evaluate


def legacy_metrics(df, k, label="label"):
    """metrics() of evaluation/train_eval_lambdarank.py, verbatim apart from the label name."""
    rows = []
    for (u, t), g in df.groupby(["member_id", "anchor_date"], sort=False):
        rel = g.sort_values("score", ascending=False)[label].values
        if rel.sum() == 0: continue
        top = rel[:k]; hit = top.sum() > 0
        mrr = 1.0 / (int(np.argmax(top > 0)) + 1) if hit else 0.0
        dcg = (top / np.log2(np.arange(2, len(top) + 2))).sum(); ideal = np.sort(rel)[::-1][:k]
        idcg = (ideal / np.log2(np.arange(2, len(ideal) + 2))).sum()
        rows.append((u, t, float(hit), mrr, dcg / idcg if idcg > 0 else 0.0, min(1.0, rel[:50].sum() / rel.sum())))
    return pd.DataFrame(rows, columns=["member_id", "anchor_date", f"HR@{k}", f"MRR@{k}", f"NDCG@{k}", "Recall@50"])


@pytest.fixture
def con():
    return connect(read_lakehouse=False)


@pytest.fixture
def world():
    """60 anchors × 80 scored candidates out of 300 models; positives drawn from the whole catalogue, so some fall outside the list."""
    rng = np.random.default_rng(7)
    scores, positives = [], []
    for i in range(60):
        member, anchor = f"m{i % 25}", pd.Timestamp("2026-02-02") + pd.Timedelta(weeks=i // 25)
        cand = rng.choice(300, 80, replace=False)
        for c in cand:
            scores.append((member, anchor, f"x{c}", float(rng.normal())))
        for p in rng.choice(300, rng.integers(1, 6), replace=False):
            positives.append((member, anchor, "TH", f"x{p}", bool(rng.random() < 0.3)))
    s = pd.DataFrame(scores, columns=["member_id", "anchor_date", "model_code", "score"])
    p = pd.DataFrame(positives, columns=["member_id", "anchor_date", "country_code", "model_code", "is_repeat"])
    return s, p


def test_conditional_matches_legacy(con, world):
    s, p = world
    con.register("s", s); con.register("p", p)
    new = evaluate(con, "s", "p", conditional=True)
    lab = s.merge(p[["member_id", "anchor_date", "model_code"]].assign(label=1), how="left").fillna({"label": 0})
    for k in (10, 20):
        old = legacy_metrics(lab, k)
        j = old.merge(new.assign(anchor_date=pd.to_datetime(new["anchor_date"])), on=["member_id", "anchor_date"], suffixes=("_old", ""))
        assert len(j) == len(old) == len(new)
        for m in (f"HR@{k}", f"MRR@{k}", f"NDCG@{k}", "Recall@50"):
            np.testing.assert_allclose(j[m], j[m + "_old"], atol=1e-12)


def test_unconditional_counts_outside_positives_as_misses(con, world):
    s, p = world
    con.register("s", s); con.register("p", p)
    cond, unc = evaluate(con, "s", "p", conditional=True), evaluate(con, "s", "p", conditional=False)
    assert len(unc) == p.groupby(["member_id", "anchor_date"]).ngroups >= len(cond)
    j = unc.merge(cond, on=["member_id", "anchor_date"], suffixes=("", "_c"))
    for m in ("NDCG@10", "Recall@20", "HR@10"):
        assert (j[m] <= j[m + "_c"] + 1e-12).all()
    assert (unc.loc[unc["cand_recall"] == 0, ["HR@200", "NDCG@200", "Recall@200"]] == 0).all().all()


def test_hand_example(con):
    s = pd.DataFrame({"member_id": "a", "anchor_date": pd.Timestamp("2026-02-02"), "model_code": ["m1", "m2", "m3", "m4"],
                      "score": [0.9, 0.5, -np.inf, 0.1]})
    # m2 repeat at rank 2; m3 is scored −inf (not recommendable); m9 was never a candidate
    p = pd.DataFrame({"member_id": "a", "anchor_date": pd.Timestamp("2026-02-02"), "country_code": "VN",
                      "model_code": ["m2", "m3", "m9"], "is_repeat": [True, False, False]})
    con.register("s", s); con.register("p", p)
    r = evaluate(con, "s", "p").iloc[0]
    assert r["Recall@10"] == pytest.approx(1 / 3)
    assert r["NDCG@10"] == pytest.approx((1 / np.log2(3)) / (1 + 1 / np.log2(3) + 1 / np.log2(4)))
    assert r["MRR@10"] == pytest.approx(0.5)
    assert r["recall_repeat@10"] == 1.0 and r["recall_explore@10"] == 0.0
    assert r["cand_recall"] == pytest.approx(1 / 3) and r["repeat_share"] == pytest.approx(1 / 3)
    c = evaluate(con, "s", "p", conditional=True).iloc[0]
    assert c["Recall@10"] == 1.0 and c["NDCG@10"] == pytest.approx(1 / np.log2(3))
