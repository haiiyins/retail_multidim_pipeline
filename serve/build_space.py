"""Stage the demo as a static Hugging Face Space: serve/index.html runs serve/recommend.py in the browser with Pyodide (pandas from
the Pyodide distribution; Gradio-Lite 5.45 no longer installs, its dependencies cannot be resolved from PyPI), on the anonymised
reference as CSV (Pyodide has no pyarrow), plus the back-test showcase (serve/export_showcase.py), read by the page itself. serve/app.py is the same demo with a Gradio UI, for local runs.
Usage: python serve/build_space.py  →  data/demo/space/  (then `make demo-push`)
       python serve/build_space.py --ref-csv live/reference  (CI, .github/workflows/deploy-space.yml: the reference as published on
       the live Space, so that a change under serve/ deploys without data/demo/)"""
import argparse, json, pathlib, shutil, sys
import pandas as pd

ROOT = pathlib.Path(__file__).resolve().parents[1]
SRC, REF, OUT = ROOT / "serve", ROOT / "data" / "demo" / "reference", ROOT / "data" / "demo" / "space"

CARD = """---
title: Next-basket recommendation demo
emoji: 🛒
colorFrom: blue
colorTo: green
sdk: static
pinned: false
license: mit
---

Demo of a course project on next-basket recommendation for sporting-goods retail members, built as a CRM / marketing console: upload a
purchase CSV (`member_id, country_code, model_id, purchase_date, quantity`), browse each member's re-buy reminders (with their
purchase cycle and a "due" flag) and new-product suggestions with the reason of each, preview what the member would see in an app,
and build a campaign audience (due re-buys, cross-sell, department expansion) exported as CSV. Vietnamese / English. It runs in the browser (Pyodide); the first load takes a few seconds. Product codes and
departments are anonymised (salted hashes, generic labels); the sample file is synthetic. The "Best model (back-test)" tab shows the
batch-scored output of the best model next to today's approach for an anonymised random sample of real test customers, published
with the data owner's consent.
"""


REQUIRED = ("asof.txt", "sample_purchases.csv", "showcase.json", "models_TH.csv", "models_VN.csv", "neighbours_TH.csv", "neighbours_VN.csv")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref-csv", help="directory already holding the published reference (*.csv, asof.txt, showcase.json); "
                                      "default: convert data/demo/reference/*.parquet")
    a = ap.parse_args()
    if a.ref_csv:
        missing = [f for f in REQUIRED if not (pathlib.Path(a.ref_csv) / f).is_file()]
        assert not missing, f"reference incomplete in {a.ref_csv}: {missing}"
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "reference").mkdir(parents=True)
    shutil.copy(SRC / "recommend.py", OUT / "recommend.py")
    shutil.copy(SRC / "ABOUT.md", OUT / "ABOUT.md")
    if a.ref_csv:
        for p in sorted(pathlib.Path(a.ref_csv).iterdir()):
            if p.suffix in (".csv", ".txt", ".json"):
                shutil.copy(p, OUT / "reference" / p.name)
    else:
        for p in sorted(REF.glob("*.parquet")):
            pd.read_parquet(p).to_csv(OUT / "reference" / f"{p.stem}.csv", index=False, float_format="%.5g")
        for f in ("sample_purchases.csv", "asof.txt", "showcase.json"):
            shutil.copy(REF / f, OUT / "reference" / f)
    assert not any("salt" in p.name for p in OUT.rglob("*")), "the salt must never be published"
    mounts = ["recommend.py"] + [f"reference/{p.name}" for p in sorted((OUT / "reference").iterdir()) if p.name != "showcase.json"]
    html = (SRC / "index.html").read_text(encoding="utf-8").replace("__FILES__", json.dumps(mounts))
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "README.md").write_text(CARD, encoding="utf-8")
    print(f"staged {sum(1 for _ in OUT.rglob('*') if _.is_file())} files, "
          f"{sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) / 1e6:.1f} MB → {OUT}")


if __name__ == "__main__":
    sys.exit(main())
