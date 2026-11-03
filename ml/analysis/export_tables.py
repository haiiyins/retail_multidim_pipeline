"""Copy the ML report tables (data/ml/report/*.md, not versioned) into docs/report/tables/ml/ for the report drafts, masking the
organisation tokens of REDACT_TERMS (.env) as tools/report_tables.py does, and refusing member ids or local paths.
Usage: python ml/analysis/export_tables.py"""
import os, re, sys
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
from ml.common.data import ROOT, ml_path

TABLES = ["t28_p1_frozen_d30", "t28b_p1_frozen_d30", "t29_signals", "t29b_v1", "t29b_v2", "t30a_sources", "t30_curve", "t31",
          "t31_segments", "t31_paired", "t31_seeds", "t31_seeds_paired", "t31_v3", "t31_v3_paired", "t31_b30", "t31_b30_paired",
          "t31_hist", "t31_hist_paired", "t32", "t32_paired", "t35", "t37", "t38", "t39", "t28c", "epochs_two_tower_TH",
          "epochs_sasrec_TH", "paired_e12", "paired_e6", "paired_e18"]
UUID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def main():
    load_dotenv(ROOT / ".env")
    redact = [t.strip() for t in os.environ.get("REDACT_TERMS", "").split(",") if t.strip()]
    out = ROOT / "docs" / "report" / "tables" / "ml"
    out.mkdir(parents=True, exist_ok=True)
    done = []
    for name in TABLES:
        src = ml_path("report", f"{name}.md")
        if not os.path.exists(src):
            continue
        text = open(src, encoding="utf-8").read().replace(str(ROOT) + "/", "")
        for t in redact:
            text = re.sub(re.escape(t), "[redacted]", text, flags=re.IGNORECASE)
        assert not UUID.search(text), f"{name}: member id in a report table"
        assert "/localhome" not in text and "/home/" not in text, f"{name}: local path in a report table"
        (out / f"{name}.md").write_text(text, encoding="utf-8")
        done.append(name)
    print(f"{len(done)} tables → {out}: {', '.join(done)}")


if __name__ == "__main__":
    sys.exit(main())
