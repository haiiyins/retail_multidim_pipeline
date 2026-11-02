"""P3 (UMTR) inputs: one row per anchor with its K candidates, cached as torch tensors under data/ml/umtr/.

x      (A, K, F) pair features of gld_ranking_dataset / pairs_v2 (the GBDT feature set without country_code; promo_kind as codes),
       t(v) = sign(v) · log1p(|v|), standardised with the train mean / std, NaN → 0, plus a missing flag for every column with NaN
model  (A, K) global model index (0 = pad), dept (A, K) sport department index
rep    (A, K) the member bought the candidate before the anchor (hist_buy_cnt > 0): the repeat / explore split of the two heads
y30, y90 (A, K) labels; mask (A, K) real candidates
seq, gap (A, L) the last L purchases before the anchor (model index, log2 bucket of days before the anchor), oldest → newest
rho    (A,) the member's repeat share before the anchor (fixed-gate ablation); gate_y (A,) repeat share of her unconditional positives
       in (t, t + Δ] (NaN without positives), the target of the learned gate
Usage: python ml/umtr/data.py --source v1|v2 [--splits train,valid,test]"""
import argparse, os, sys, time
import numpy as np, pandas as pd, torch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, connect, load_config, ml_path, split_windows
from ml.eval.protocol import build_positives
from ml.rankers.gbdt import NONFEAT
from ml.retrieval.base import DAY_BITS, EPOCH, Events
from ml.retrieval.mixer import repeat_counts
from ml.retrieval.neural import last_window

C = load_config("umtr")
EXTRA_NONFEAT = {"fit_cutoff", "source_ts_max", "country_code"}


def relation(source):
    if source == "v1":
        return "lh.gold.gld_ranking_dataset"
    return f"read_parquet('{ml_path('pairs_v2', '*.parquet')}')"


def vocab(con):
    m = con.execute("""SELECT model_code, COALESCE(MODE(sport_department_code), -1) AS dept FROM lh.silver.slv_dim_model
                       GROUP BY 1 ORDER BY 1""").df()
    sold = con.execute("SELECT DISTINCT model_code FROM lh.silver.slv_fact_sales_line WHERE model_code IS NOT NULL").df()
    m = sold.merge(m, how="left", on="model_code").fillna({"dept": -1}).sort_values("model_code").reset_index(drop=True)
    codes, dept = m["model_code"].to_numpy(), m["dept"].astype(np.int64).to_numpy()
    _, dept_idx = np.unique(dept, return_inverse=True)
    return pd.Index(codes), dept_idx + 1   # model index i + 1, dept index + 1; 0 = pad


def feature_columns(con, rel):
    cols = [(c, t) for c, t, *_ in con.execute(f"DESCRIBE SELECT * FROM {rel}").fetchall()]
    return [c for c, t in cols if c not in NONFEAT and c not in EXTRA_NONFEAT]


def load(con, source, split, codes, dept_of, stats=None):
    rel = relation(source)
    feats = feature_columns(con, rel)
    sw = split_windows()
    sel = ", ".join(f'CAST("{c}" AS DOUBLE) AS "{c}"' if c != "promo_kind" else
                    "CAST(HASH(COALESCE(promo_kind, '')) % 1000 AS DOUBLE) AS promo_kind" for c in feats)
    t0 = time.time()
    df = con.execute(f"""SELECT member_id, country_code, anchor_date, model_code, label_30, label_90, {sel},
                                ROW_NUMBER() OVER (PARTITION BY member_id, anchor_date ORDER BY candidate_rank, model_code) - 1 AS pos
                         FROM {rel} WHERE anchor_date BETWEEN DATE '{sw[split + '_lo']}' AND DATE '{sw[split + '_hi']}'
                         {"AND in_train_sample" if split == "train" else ""}
                         ORDER BY member_id, anchor_date, pos""").df()
    df = df[df["pos"] < C["k"]]
    key = df["member_id"].astype(str) + "|" + df["anchor_date"].astype(str)
    a_idx, anchors = pd.factorize(key, sort=False)
    A, K = len(anchors), C["k"]
    pos = df["pos"].to_numpy()
    v = df[feats].to_numpy(np.float64)
    v = np.sign(v) * np.log1p(np.abs(v))
    if stats is None:
        nan = np.isnan(v)
        flag_cols = np.flatnonzero(nan.mean(0) > 0.01)
        stats = {"mean": np.nanmean(v, 0), "std": np.nanstd(v, 0) + 1e-6, "flag_cols": flag_cols, "feats": feats}
    v = (v - stats["mean"]) / stats["std"]
    flags = np.isnan(v[:, stats["flag_cols"]]).astype(np.float32)
    v = np.nan_to_num(v, nan=0.0).astype(np.float32)
    F = v.shape[1] + flags.shape[1]
    x = torch.zeros(A, K, F, dtype=torch.float16)
    x[a_idx, pos] = torch.from_numpy(np.concatenate([v, flags], 1)).half()

    def grid(values, dtype):
        out = torch.zeros(A, K, dtype=dtype)
        out[a_idx, pos] = torch.as_tensor(values, dtype=dtype)
        return out

    mi = codes.get_indexer(df["model_code"]) + 1
    hist = df["hist_buy_cnt"].fillna(0).to_numpy() > 0
    first = np.r_[True, a_idx[1:] != a_idx[:-1]]
    head = df[first][["member_id", "country_code", "anchor_date"]].reset_index(drop=True)
    head["anchor_date"] = pd.to_datetime(head["anchor_date"])
    out = {"x": x, "model": grid(mi, torch.int32), "dept": grid(dept_of[np.maximum(mi - 1, 0)] * (mi > 0), torch.int16),
           "rep": grid(hist, torch.bool), "y30": grid(df["label_30"].to_numpy(), torch.bool),
           "y90": grid(df["label_90"].to_numpy(), torch.bool), "mask": grid(np.ones(len(df)), torch.bool)}
    print(f"  {source} {split}: {A:,} anchors, {len(df):,} rows, {F} features, {time.time() - t0:.0f}s", flush=True)
    out.update(sequences(con, head, codes))
    out.update(gate_target(con, split, head))
    out["anchors"] = head
    return out, stats


def sequences(con, head, codes):
    L = C["max_len"]
    seq, gap, rho = np.zeros((len(head), L), np.int64), np.zeros((len(head), L), np.int64), np.zeros(len(head), np.float32)
    for country, h in head.groupby("country_code"):
        ev = Events.load(con, country)
        m = ev.member_index(h["member_id"])
        t = ((h["anchor_date"] - pd.Timestamp(EPOCH)).dt.days).to_numpy()
        row, idx = ev.history(m, t)
        gi = codes.get_indexer(ev.items) + 1
        s, n = last_window(row, gi[ev.i[idx]], len(h), L)
        g, _ = last_window(row, np.minimum(np.ceil(np.log2(t[row] - ev.day[idx] + 1)), 15).astype(np.int64) + 1, len(h), L)
        seq[h.index], gap[h.index] = s, g
        n_rows, n_rep = repeat_counts(ev, m, t)
        mean = n_rep.sum() / max(n_rows.sum(), 1)
        rho[h.index] = (n_rep + 20 * mean) / (n_rows + 20)
        del ev
    return {"seq": torch.from_numpy(seq).int(), "gap": torch.from_numpy(gap).to(torch.int16), "rho": torch.from_numpy(rho)}


def gate_target(con, split, head):
    p = con.execute(f"""SELECT member_id, CAST(anchor_date AS TIMESTAMP) AS anchor_date, AVG(CAST(is_repeat AS DOUBLE)) AS share
                        FROM read_parquet('{build_positives(con, split, 30)}') GROUP BY 1, 2""").df()
    p["anchor_date"] = pd.to_datetime(p["anchor_date"])
    j = head.merge(p, how="left", on=["member_id", "anchor_date"])
    return {"gate_y": torch.from_numpy(j["share"].to_numpy(np.float32))}


def cache_path(source, split):
    return os.path.join(ML_DIR, "umtr", f"{source}_{split}.pt")


def get(source, split):
    return torch.load(cache_path(source, split), weights_only=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default="v2")
    ap.add_argument("--splits", default="train,valid,test")
    a = ap.parse_args()
    con = connect(threads=16)
    con.execute("SET memory_limit='150GB'")
    codes, dept_of = vocab(con)
    splits = a.splits.split(",")
    stats = None if "train" in splits else get(a.source, "train")["meta"]["stats"]   # normalisation from train only
    splits = sorted(splits, key=lambda s: s != "train")
    os.makedirs(os.path.join(ML_DIR, "umtr"), exist_ok=True)
    for split in splits:
        out, stats = load(con, a.source, split, codes, dept_of, stats)
        out["meta"] = {"n_models": len(codes) + 1, "n_dept": int(dept_of.max()) + 1, "stats": stats, "codes": codes.to_numpy()}
        torch.save(out, cache_path(a.source, split))


if __name__ == "__main__":
    sys.exit(main())
