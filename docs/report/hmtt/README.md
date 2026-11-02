# HMTT report — chapter drafts

Drafts of the IEEE Access paper of the course plan (§13): I Introduction · II Related work · III Data and infrastructure · IV
Unconditional evaluation protocol and error analysis · V Learned retrieval · VI Ranking · VII Results (RQ1–RQ3, H2) · VIII Feasibility
and demo · IX Discussion and limitations · X Conclusion. The slide outline is [`slides.md`](slides.md).

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
