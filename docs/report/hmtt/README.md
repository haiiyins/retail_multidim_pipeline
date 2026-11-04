# HMTT report — chapter drafts

**LaTeX paper:** [`main.tex`](main.tex) (IEEE Access class `ieeeaccess.cls` on `IEEEtran.cls`, references in
[`custom.bib`](custom.bib), figures from `docs/figures/ml/`), built to [`main.pdf`](main.pdf) by `make report-pdf`. The class needs
pdfLaTeX (it uses `spotcolor` and T1 Times / Helvetica), not XeLaTeX; on the GH200 host TinyTeX provides it
(`~/.TinyTeX/bin/aarch64-linux`). When a rerun replaces a report table, update the headline-number block at the top of `main.tex`
and the tables that quote it, then rerun `make ml-figures` and `make report-pdf`. Author names, affiliation and biographies are
placeholders to complete.

Drafts of the IEEE Access paper of the course plan (§13): I Introduction · II Related work · III Data foundation (RQ1) · IV
Unconditional evaluation protocol and error analysis (RQ2) · V Learned retrieval (RQ2) · VI Ranking models · VII Results (RQ3, H1) · VIII Value, cost
and demonstrator (RQ4) · IX Discussion and limitations · X Conclusion. The slide outline is [`slides.md`](slides.md).

Every number comes from a table in [`../tables/ml/`](../tables/ml/), copied from `data/ml/report/` by
`python ml/analysis/export_tables.py`; decisions taken during the run are in [`ml/DECISIONS.md`](../../../ml/DECISIONS.md). Unless a
sentence says otherwise, numbers are on the test split (2026-02 … 2026-07), Δ = 30, main scope TH + VN (D1), unconditional protocol
(D3), one seed and 10 tuning trials per model (reduced run, DECISIONS 2026-11-02).

| Section | File | Tables |
|---|---|---|
| I – II | [s1_intro.md](s1_intro.md) | — |
| III – IV | [s3_protocol.md](s3_protocol.md) | t28, t28b |
| V | [s5_retrieval.md](s5_retrieval.md) | t30a, t30 |
| VI – VII | [s6_ranking_results.md](s6_ranking_results.md) | t29, t29b, t31 (+ t31_paired), t32 (+ t32_paired), t34 = t31_segments, t35 |
| VIII – X | [s8_feasibility.md](s8_feasibility.md) | t37, t38, t39 |
