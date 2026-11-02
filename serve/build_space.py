"""Stage the demo as a static Hugging Face Space: serve/index.html runs serve/recommend.py in the browser with Pyodide (pandas from
the Pyodide distribution; Gradio-Lite 5.45 no longer installs, its dependencies cannot be resolved from PyPI), on the anonymised
reference as CSV (Pyodide has no pyarrow). serve/app.py is the same demo with a Gradio UI, for local runs.
Usage: python serve/build_space.py  →  data/demo/space/  (then `make demo-push`)"""
import json, pathlib, shutil, sys
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

Demo v0 of a course project on next-basket recommendation for retail members: upload a purchase CSV
(`member_id, country_code, model_id, purchase_date, quantity`) and get the top-K models of every member with the source and the
reason of each recommendation. It runs in the browser (Pyodide); the first load takes a few seconds. Product codes and
departments are anonymised (salted hashes, generic labels); the sample file is synthetic.
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "reference").mkdir(parents=True)
    shutil.copy(SRC / "recommend.py", OUT / "recommend.py")
    shutil.copy(SRC / "ABOUT.md", OUT / "ABOUT.md")
    for p in sorted(REF.glob("*.parquet")):
        pd.read_parquet(p).to_csv(OUT / "reference" / f"{p.stem}.csv", index=False, float_format="%.5g")
    for f in ("sample_purchases.csv", "asof.txt"):
        shutil.copy(REF / f, OUT / "reference" / f)
    assert not any("salt" in p.name for p in OUT.rglob("*")), "the salt must never be published"
    mounts = ["recommend.py"] + [f"reference/{p.name}" for p in sorted((OUT / "reference").iterdir())]
    html = (SRC / "index.html").read_text(encoding="utf-8").replace("__FILES__", json.dumps(mounts))
    (OUT / "index.html").write_text(html, encoding="utf-8")
    (OUT / "README.md").write_text(CARD, encoding="utf-8")
    print(f"staged {sum(1 for _ in OUT.rglob('*') if _.is_file())} files, "
          f"{sum(p.stat().st_size for p in OUT.rglob('*') if p.is_file()) / 1e6:.1f} MB → {OUT}")


if __name__ == "__main__":
    sys.exit(main())
