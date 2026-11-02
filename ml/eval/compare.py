"""Comparison tables from the per-model protocol reports (ml/eval/protocol.py --reeval): t31 (main comparison, test, unconditional,
TH + VN, 95 % member-bootstrap intervals), t34 (by segment and country) and t32 (P3 ablation). Missing reports are computed first.
Usage: python ml/eval/compare.py --out t31 --models ptopfreq,gptopfreq,ease_nbr,...  [--labels "P-TopFreq,GP-TopFreq,..."]"""
import argparse, os, subprocess, sys
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ML_DIR, ROOT, ml_path

METRICS = ["NDCG@20", "HR@10", "Recall@20", "recall_repeat@20", "recall_explore@20", "cand_recall"]


def report(name, delta=30):
    path = ml_path("report", f"t31_{name}_d{delta}.csv")
    if not os.path.exists(path) or os.path.getmtime(path) < os.path.getmtime(os.path.join(ML_DIR, "scores", f"{name}_test_d{delta}.parquet")):
        subprocess.run([sys.executable, str(ROOT / "ml" / "eval" / "protocol.py"), "--reeval", name, "--out", "t31"], check=True,
                       stdout=subprocess.DEVNULL)
    return pd.read_csv(path)


def table(models, labels, scope_filter):
    rows = []
    for name, label in zip(models, labels):
        t = report(name)
        t = t[(t["mode"] == "unconditional") & t["scope"].map(scope_filter)]
        for _, r in t.iterrows():
            row = {"model": label, "scope": r["scope"], "anchors": int(r["anchors"])}
            for m in METRICS:
                row[m] = r[m]
            row["NDCG@20 95% CI"] = f"[{r['NDCG@20_lo']:.4f}, {r['NDCG@20_hi']:.4f}]"
            rows.append(row)
    return pd.DataFrame(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="t31")
    ap.add_argument("--models", required=True)
    ap.add_argument("--labels", default=None)
    ap.add_argument("--title", default="")
    a = ap.parse_args()
    models = a.models.split(",")
    labels = a.labels.split(",") if a.labels else models
    main_t = table(models, labels, lambda s: s == "MAIN (TH+VN)")
    seg_t = table(models, labels, lambda s: s not in ("ALL", "MAIN (TH+VN)"))
    with open(ml_path("report", f"{a.out}.md"), "w") as f:
        f.write(f"# {a.out} — {a.title or 'model comparison'} (test, Δ = 30, unconditional protocol D3, TH + VN)\n\n")
        f.write(main_t.drop(columns=["scope"]).to_markdown(index=False, floatfmt=".4f") + "\n")
    with open(ml_path("report", f"{a.out}_segments.md"), "w") as f:
        f.write(f"# {a.out} by country and segment (test, Δ = 30, unconditional; segments from gld_fs_member tx_365d)\n\n")
        piv = seg_t.pivot(index="model", columns="scope", values="NDCG@20").reindex(labels)
        f.write("NDCG@20\n\n" + piv.to_markdown(floatfmt=".4f") + "\n\n")
        piv = seg_t.pivot(index="model", columns="scope", values="recall_explore@20").reindex(labels)
        f.write("recall_explore@20\n\n" + piv.to_markdown(floatfmt=".4f") + "\n")
    main_t.to_csv(ml_path("report", f"{a.out}.csv"), index=False)
    print(main_t.drop(columns=["scope"]).to_string(index=False, float_format=lambda x: f"{x:.4f}"))


if __name__ == "__main__":
    sys.exit(main())
