# Slide outline (18 – 20 slides, 15 min + 5 min demo)

Figures are in `docs/figures/ml/` (`make ml-figures`). Numbers come from the drafts of this folder; a slide never shows a number that is not in a table of `docs/report/tables/ml/`.

1. **Title** — Next-basket recommendation as a two-stage problem: learned retrieval, multi-task ranking, honest evaluation.
2. **Problem** — member × Monday anchor, which models in the next 30 days; three countries, TH + VN main scope.
3. **Starting point** — KTXLDL P1: NDCG@20 0.206 conditional → 0.095 unconditional; 40.7 % of the anchors have no purchase in the list (t28).
4. **Where the errors are (t28b, `fig_t28b_errors`)** — stacked bar repeat / explore × top 10 / rank 11+ / capped / no source. 91 % of the positives are
   explore, 74.5 % of explore never reaches the ranker.
5. **Research questions** — RQ1 data foundation, RQ2 learned retrieval, RQ3 ranking / tuning / repeat-explore heads, RQ4 business value & cost, H1 stacking leakage.
6. **Point-in-time discipline (`fig_pit_timeline`)** — quarterly refits in every split, fit_cutoff / source_ts_max on every row, QC-6 = 0 violations;
   why a single fit at the end of train loses a third of the test positives.
7. **Learned retrieval** — eight explore-only sources, tuned on the explore coverage they add; diagram of sources → mixer → K = 300.
8. **Coverage (t30, `fig_t30_curve`)** — bar chart: R1–R5 0.370 → best single source 0.439 → candidates_v2 0.450 → uncapped union 0.541; explore × 1.30.
9. **Recall–cost curve** — K ∈ {100, 200, 300, 500}; cheap sources (RP3beta, EASE) vs neural (≈ 6 GPU-h each, t37).
10. **RQ2 to NDCG** — frozen ranker on v2: +0.0025 [0.0018, 0.0032]; explore +0.010, repeat −0.032.
11. **Rankers (`fig_rankers_compare`, `fig_p3_arch`)** — P1-tuned (GBDT, 85 features), P2 (GBDT + hazard / WTP signals), P3 UMTR (Transformer + target attention, two gated heads vs single head); uniform 10-trial budget.
12. **H1 (t29, t29b)** — naive vs rolling vs leaky: inflation in-sample, gone on test; signals add little over Gold features.
13. **RQ3 headline (t31, `fig_t31_ndcg`, `fig_t31_seeds`)** — table of the models with CIs; paired differences P3 vs P1-tuned (+0.0028 from new features, +0.0011 from tuning, +0.0009 from P3 one head).
14. **By segment (t34)** — new / mid / loyal × NDCG@20 and recall_explore@20.
15. **RQ3 ablation (t32, `fig_t32_ablation`)** — learned gate vs fixed gate (within two-head) vs one head (best overall, no gate) vs no sequence (sequence + attention disabled together); paired bootstrap.
16. **Explanations (t35)** — grouped SHAP of the GBDT; P3 gate by segment.
17. **Feasibility (t38, t39)** — multiples over random / popular / buy-again, GMV proxy (offline, not causal), serving coverage.
18. **Cost (t37)** — tuning and build hours per model vs gain.
19. **Demo** — static page, CSV → top-K with reasons; best-model tab: batch-scored P3 vs GP-TopFreq on 500 real, anonymised test
    members with what they bought next; privacy choices (salted ids, generic departments, consent, minimised sample).
20. **Limitations and next steps** — 10 trials and one seed, SASRec without its own NBR budget, explore × 1.3 not × 2, no online test.

## Demo script (5 min)

1. t28b: where the errors are (30 s).
2. t30: retrieval raises coverage (30 s).
3. t31 / t34: who wins where (1 min).
4. Open the Space, upload `sample_purchases.csv`, pick a member, show the top 10 with the source of each item (repeat,
   co-purchase, trend) and its popularity percentile (2 min).
5. Edit one row of the CSV (add a purchase in another department) and re-run: the co-purchase items change (30 s).
6. Tab "Best model (back-test)": pick a member, compare P3 and GP-TopFreq against what she bought in the next 30 days (✓);
   why batch scoring: the best model needs warehouse features and PyTorch sources (1 min).
7. Limits: reference tables frozen at the as-of date, no prices, no what-if (30 s).
