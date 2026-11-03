# ML decisions log (HMTT)

Frozen decisions D1–D14 are in the project plan; this file records the decisions taken while running it, with the evidence.
Numbers are P1-frozen on the test split, Δ = 30, unconditional protocol (D3), GH200 host.

## 2026-11-02 · Reference numbers (ML-02, t28)

- P1-frozen rerun on the GH200 host is the reference from now on: conditional NDCG@20 0.2060 (server run 0.2068: LightGBM float
  differences ARM vs x86, and 5 anchors differ because the server results predate the last Gold rebuild).
- Unconditional NDCG@20 0.090 (TH + VN 0.095) on 63,574 anchors; 40.7 % of them have no positive among the 200 candidates.
- Ranking ties are broken by `model_code` (the legacy code used an unstable sort; 12 anchors differed, all with tied scores).

## 2026-11-02 · Where the errors are (ML-03, t28b)

213,289 test positives: 8.2 % in the top 10, 23.6 % in the list below rank 10, 10.3 % proposed by a source but cut by the 200 cap,
57.9 % proposed by no source. 91.4 % of the positives are explore.

- Repeat is largely solved (65 % top 10, 1.4 % outside the list); explore is the bottleneck (2.8 % top 10, 74.5 % outside).
- 95 % of the capped positives come from R5 (national top-300): R5 fills 80 % of the slots but its lower ranks do not fit. On
  explore positives with popularity rank 101–300, 60 % are capped. Raising K or giving R5 a quota recovers them cheaply.
- No-source positives are mid-tail, not long-tail: 40 % have popularity rank 301–1000 and 55 % 1001–5000 at the anchor; 0.05 %
  fall outside `anchor_model_grid`. Positives above rank 5000 or unranked are 3.2 % of all positives.
  → Learned retrieval sources (R6–R10) can score a per-country universe of the top ~5,000 models at the anchor without losing
  more than ~3 % of the positives; this also bounds EASE to 5 k × 5 k per country.
- High-price explore positives are the hardest (84 % no source), low-price the easiest (42 %).

## 2026-11-02 · R4 dropped (ML-04)

R4 (sport × offer) has recall 0.0002 because only 1.07 % of the evaluated anchors have a favourite sport, not because the mapping
is wrong: the affinity table is sane (every kept pair has lift > 1.5, about two departments per sport, cutoff before validation).
Relaxing the rule does not help: without the promo / season filter the recall is 0.0008, below the 0.005 threshold of the plan.
R4 is left out of `ml.candidates_v2`; Gold is not rebuilt, so P1-frozen keeps its reference numbers. The favourite-sport signal
stays available as member features (`n_sports`, `sport_match`).

## 2026-11-02 · D8 revised: quarterly refits through valid and test (ML-08..10)

The plan fitted every learned source once at FINAL_CUTOFF (2025-09-16) for all valid and test anchors. On test (2026-02 … 07) that
model is 5–10 months old while a train anchor always sees a model at most one quarter old, and the catalogue moves fast: only
66–73 % of the test positives are inside the top-5 000 universe of 2025-09-16 (valid: 88–94 %).

| test positives inside the universe | SG | TH | VN |
|---|---|---|---|
| fitted once at 2025-09-16 | 0.69 | 0.66 | 0.73 |
| refitted every quarter (2026-01, 04, 07) | 0.82 | 0.83 | 0.87 |
| refitted every month | 0.86 | 0.88 | 0.91 |

Decision: candidate sources and signal models are refitted every quarter in every split (`ml/common/pit.py`: 13 cutoffs
2023-07-01 … 2026-07-01, an anchor uses the latest cutoff ≤ t). This stays point-in-time — a fit reads only events dated before its
cutoff, and supervised sources only label windows that close before it — and mirrors a system retrained quarterly. The rankers
(P1, P2, P3) are still trained once on the train split. Monthly refits would add ~4 points of universe coverage for three times the
fits of the neural sources; not worth it now.

## 2026-11-02 · Classical learned sources R6 EASE, R7 item2vec, R8 TIFU-KNN (ML-08..10, t30a)

Per country × quarterly cutoff, universe = top 5 000 models by buyers in the 365 days before the cutoff, 100 candidates per anchor
after the `anchor_model_grid` filter. EASE (λ) and TIFU-KNN (k, r_b, r_g, α) got the 30-trial TPE budget on unconditional valid
Recall@100: EASE λ ≈ 3 060 (0.254), TIFU-KNN k = 971, r_b 0.64, r_g 0.86, α 0.53 (0.261). item2vec has no tuning budget in the plan
and runs with the defaults of `ml/config/retrieval.yml`. Unconditional coverage of the positives (Δ = 30, member means):

| test, TH + VN | list size | cand | cand_repeat | cand_explore |
|---|---|---|---|---|
| R1–R5 (200) | 200 | 0.370 | 0.997 | 0.307 |
| R6 EASE alone | 100 | 0.232 | 0.607 | 0.198 |
| R7 item2vec alone | 100 | 0.181 | 0.594 | 0.138 |
| R8 TIFU-KNN alone | 100 | 0.236 | 0.972 | 0.164 |
| R1–R5 ∪ R6 ∪ R7 ∪ R8 | 336 | **0.469** | 0.997 | **0.418** |

(valid, TH + VN: 0.386 → 0.496, explore 0.318 → 0.443.)

- The coverage target of §5.2 (≥ 0.45 on TH + VN) is met on test, before the neural sources, with an uncapped union of ~336
  candidates; ML-13 has to fit it under the cap. The explore target (× 2) is not: × 1.36 (0.307 → 0.418).
- The sources are complementary: item2vec is the weakest alone but adds as much as EASE to R1–R5 (both + 0.058 on test, TH + VN) because it
  reaches explore models the co-purchase sources miss. TIFU-KNN mostly re-finds repeats, which R1 already covers.
- Quarterly refits (D8 revised) lift EASE on test from 0.201 to 0.224 (ALL).
- Exact search on the GPU replaces FAISS: 5 000 models per country, a full matrix product is cheaper than an ANN index.
- gensim 4.4 on aarch64 prints `Exception ignored in our_dot_float` a few times per fit with several workers (one dot product
  out of ~10⁹; a single worker never shows it); the vectors are finite with normal norms, so the warning is filtered from the logs.

## 2026-11-02 · Explore-only learned sources, marginal explore objective (model review, ML-11/12)

R1 already holds 99.7 % of the repeat positives, while 91 % of the positives are explore models and 74.5 % of them were outside the
list. Before this change the learned sources spent most of their slots on repeats (EASE cand_repeat 0.59, TIFU-KNN 0.97).
- Every learned source masks the models the member bought before the anchor (`retrieval.explore_only`, `base.mask_scores`).
- A source is tuned on the explore coverage it adds to R1–R5@200 on valid (Δ cand_explore of the union), not on its own Recall@100.
- Two-tower (R9): several reference days per member and epoch (4), month of t in the member tower, explore targets with a
  softmax that masks the models already seen. SASRec (R10): one step per basket (mean of its models), gap embedding, dense all-action
  explore loss (each step predicts every explore model of (t, t + Δ], PinnerFormer-style), 8 epochs. gSASRec is dropped.
- New cheap sources: R11 explin (supervised windowed linear model, X = decayed history ≤ t, Y = explore purchases in (t, t + Δ],
  closed form), R12 RP3beta, R13 context-aware trend (last-window popularity reweighted by the member's departments and price band).
- Best valid Δ cand_explore, 10 trials: EASE +0.0853, TIFU-KNN +0.0569, RP3beta +0.0877, explin +0.0738, trend +0.0692
  (two-tower, SASRec: see below).

## 2026-11-02 · Reduced run: 10 trials per model, one seed, smaller scope

The end-to-end run has to finish by 2026-11-03. Agreed with the user:
- `tuning.yml n_trials: 10` for every model with hyper-parameters (D5 keeps its meaning: the same budget for all). TPE is seeded,
  so the first 10 trials of a 30-trial study are a 10-trial study; already-finished sources were rebuilt with their best of 10
  (best of 30 vs best of 10 differ by ≤ 0.001, except TIFU-KNN 0.0578 vs 0.0569).
- One seed for the deep models (D6 asked for 3).
- Dropped: gSASRec, P4, conformal intervals, drift monitoring; P3 ablation reduced to three rows (one head, fixed gate, no
  sequence); demo v0 (CSV → top-K with reasons, no what-if, no parity check).

## 2026-11-02 · Pairs of candidates_v2 (ML-17)

`ml/common/pairs.py` renders the Gold dbt SQL of `gld_fs_pair` / `gld_ranking_dataset` (Jinja, `ref()` resolved to the attached
lakehouse or to the new candidates) and writes Parquet, because the lakehouse is read-only while jobs read it. Parity on one VN anchor
day against `gld_ranking_dataset`: same rows and columns; differences are float noise (~1e-9) and 40 `dept_buy_cnt` values that
come from ties in Gold's ASOF join, which is not deterministic.

## 2026-11-02 · P2 signals and H2 (ML-15/16, t29, t29b)

- Temporal hazard: LightGBM binary over member × department rows (departments bought before t plus the country top 10 of the last
  90 days; 4.37 M rows, 6 % positive). WTP: LightGBM quantile regression of the log unit price paid in (t, t + Δ] (α 0.5 on the
  median line, α 0.9 on the maximum). Fixed hyper-parameters (300 rounds): they are features of a ranker, not compared models.
  item2vec enters P2 through the rolling R7 rank of the pairs, not as a separate model.
- Each signal is fitted three ways (D7): rolling (quarterly cutoffs, the only point-in-time-correct variant; QC: 0 violations),
  naive (fitted once on train and applied in-sample) and leaky (fitted on every split). Fits use at most 120 000 anchors.
- t29, hazard AUC on train / pseudo-test (last train quarter) / test: rolling 0.681 / 0.703 / 0.708, naive 0.725 / 0.744 / 0.705,
  leaky 0.710 / 0.717 / 0.723. Naive looks better in-sample and is no better on test; leaky stays better on test, where it has seen
  the labels.
- t29b (v1 pairs, P1-frozen hyper-parameters, fused on train anchors ≤ 2025-05-31; unconditional NDCG@20, TH + VN): the naive
  fusion is +0.0019 over rolling on its training anchors, +0.0005 on the pseudo-test and −0.0011 on test. This is H2's direction,
  but every gap lies inside the member-bootstrap intervals (± 0.002 on test). The signals add little to the pairs (rolling
  +0.0004 over no signals on test), because Gold already has department recency/cycle and price-gap features.

## 2026-11-02 · Baselines of t31 (ML-18..21)

- P-TopFreq (the member's own purchase counts) and GP-TopFreq (then country popularity) score the full catalogue.
- EASE and TIFU-KNN as NBR rankers: the same rolling models, without the explore-only mask, with their own 10-trial budget on
  valid NDCG@20 (`ml/baselines/nbr.py`). SASRec: the R10 build also writes the unmasked top 100 of the valid and test anchors
  (`retrieval.full_catalogue`), with the R10 parameters (no separate NDCG@20 budget, a stated limitation).
- P1-frozen is refitted on the v2 pairs with its original feature set (`ml/rankers/frozen.py`) and stays a reference row.
  P1-tuned and P2 get 10 trials on v2 with every pair column, source ranks included, as does P3.

## 2026-11-02 · P3 UMTR design (ML-22..24)

User tower: a Transformer over the last 50 purchases (shared model embedding plus a log-gap embedding) and an MLP over the member
context. Item tower: model and department embeddings plus an MLP over the candidate's pair features. DIN-style target attention of
each candidate over the sequence states. Two heads, repeat and explore, each with a softmax inside its group. A learned gate g(u)
splits the probability mass: g for the repeat group, 1 − g for the explore group. The gate is trained with BCE on the repeat share
of the member's positives. Auxiliary Δ90 BCE head. The loss is listwise (mean −log p over the positives). Early stopping uses
unconditional valid NDCG@20. The department-hazard auxiliary head of the plan is dropped (its λ left the tuning space), because
P2's hazard covers that signal. Ablation (t32): one head, fixed gate (g = the member's repeat share), no sequence (context only).

## 2026-11-02 · Learned sources R6–R13, mixer and candidates_v2 (ML-11..14, t30a, t30)

Best valid Δ cand_explore over R1–R5@200 (10 trials): two-tower +0.0742 (d 256, τ 0.096), SASRec +0.0848 (d 256, one block).
Test, TH + VN, unconditional (Δ = 30):

| test, TH + VN | list | cand | cand_repeat | cand_explore |
|---|---|---|---|---|
| R1–R5 (200) | 200 | 0.370 | 0.997 | 0.307 |
| R1–R5 ∪ R12 RP3beta (best single addition) | 277 | 0.439 | 0.997 | 0.386 |
| R1–R5 ∪ R6 EASE / R10 SASRec / R7 item2vec | 260–282 | 0.430–0.435 | 0.997 | 0.375–0.381 |
| R1–R5 ∪ every learned source (uncapped) | 483 | 0.541 | 0.997 | 0.499 |
| **candidates_v2 = mixer, fixed quotas, K = 300** | 300 | **0.450** | 0.972 | **0.400** |
| mixer at K = 500 | 470 | 0.535 | 0.994 | 0.492 |

- Neural sources do not beat the cheap ones: SASRec ≈ EASE, two-tower below. RP3beta is the best single source and trains in
  minutes, while the neural sources need about 3 GPU-hours to tune and 3 more to build (t37).
- Mixer: weighted rank quotas, key = min over sources of (rank − 0.5) / w_s, where w is a source's stand-alone valid Recall@100.
  The per-member policy scales w_r1 by the member's repeat share. It ties with fixed (valid MAIN cand@300 0.4841 against
  0.4847), so fixed is used.
- The coverage target of §5.2 (≥ 0.45 on TH + VN) is met at the cap (0.450). Explore coverage rises × 1.30 (0.307 → 0.400), below
  the × 2 target. The cap costs 2.5 points of repeat coverage (0.997 → 0.972): R1 lists past rank ~60 lose their slots to
  explore candidates. K = 500 would keep 0.994 for +0.085 coverage, but 1.7× the pairs.
- QC-6 on candidates_v2: 0 rows with source_ts_max ≥ anchor or fit_cutoff > anchor; at most 300 rows per anchor.

## 2026-11-02 · Ranking results on candidates_v2 (ML-19..26, t31, t32, t29b v2)

Test, TH + VN, unconditional NDCG@20 [95 % member bootstrap]; selection on valid with 10 trials, one seed.

| model | valid | test | test 95 % CI |
|---|---|---|---|
| TIFU-KNN NBR (best baseline) | — | 0.0788 | [0.0770, 0.0806] |
| P1-frozen v1 → v2 | — | 0.0947 → 0.0973 | |
| P1-tuned v2 | 0.1033 | 0.1011 | [0.0990, 0.1033] |
| P2 v2 (+ rolling hazard / WTP) | 0.1034 | 0.1013 | [0.0994, 0.1034] |
| P3 two heads + learned gate | 0.1037 | 0.1009 | [0.0988, 0.1029] |
| P3 one head | 0.1049 | 0.1020 | [0.0999, 0.1040] |

- RQ1 (paired, t31_paired): retrieval under the frozen ranker +0.0025 [0.0018, 0.0032]; tuning the GBDT on the same pairs adds
  +0.0039 [0.0032, 0.0045]. The learned source ranks are the second SHAP group of P1-tuned (17 %, t35a).
- RQ2: P3 one head − P1-tuned +0.0009 [0.0002, 0.0016]; P3 two heads − P1-tuned −0.0002 [−0.0009, 0.0005]; P2 − P1-tuned +0.0002
  [−0.0002, 0.0006]. The order holds in every country and segment (t31_segments = t34 of the plan).
- RQ3 (t32_paired, vs two heads): one head +0.0011 [0.0007, 0.0016] with more explore recall (+0.0016); fixed gate −0.0066 and
  −0.275 repeat recall; no sequence −0.0003 and −0.024 repeat recall. The learned gate matters, the explicit split does not. The gate
  ranks segments right but is about 2× the observed repeat share (t35c).
- H2 (t29b v2): naive − rolling +0.0026 on train anchors, +0.0029 on the pseudo-test, −0.0004 on test; leaky +0.0011 on test.
- RQ4 (t38, best on valid = P3 one head): HR@10 × 1.76 popular, × 1.54 buy-again; on explore positives 0.110 vs popular 0.115.
- `business.py` is run with `--best p3_onehead`; `explain.py` keeps `--p3 p3_full` because the gate exists only with two heads.

## 2026-11-03 · Seed variance of the final fits (t31_seeds)

The plan asked for three seeds of the deep models (D6); the reduced run had one. Final fits repeated with seeds 1 and 2, same
hyper-parameters (`gbdt.py --seed`, `umtr/train.py --seed`). Test, TH + VN, NDCG@20 mean ± sd over seeds 0–2: P1-tuned
0.1013 ± 0.0002, P3 two heads 0.1008 ± 0.0003, P3 one head 0.1022 ± 0.0001. Seed-matched paired P3 one head − P1-tuned: +0.0009,
+0.0010, +0.0006; one head − two heads: +0.0011, +0.0018, +0.0011. The conclusions of t31 / t32 hold; the two-head model's repeat
recall varies most (0.79–0.85). Tuning itself (10 TPE trials, seed 0) was not repeated.

## 2026-11-03 · Candidate cap K = 500 (candidates_v3, t31_v3)

Question: does the K = 300 cap limit accuracy? The mixer list cut at K = 500 (`build_candidates.py --k 500 --version v3`, then
`pairs.py --version v3`, `umtr/data.py --source v3`) raises test TH + VN coverage 0.450 → 0.535 for 1.6× the pairs. P1-frozen was
refitted as is; P1-tuned (study `p1_v3`) and P3 (study `p3_v3`) were re-tuned with 10 trials, P3 final fits for two heads and one head.
Decision on valid, TH + VN NDCG@20: P1-tuned 0.1088 → 0.1079, P3 two heads 0.1087 → 0.1092, P3 one head 0.1096 → 0.1097 — no gain,
**K = 300 kept**. Test, reported once afterwards (t31_v3_paired, v3 − v2): P1-frozen −0.0009 [−0.0016, −0.0003], P1-tuned −0.0003
[−0.0008, 0.0001], P3 two heads +0.0006 [−0.0000, 0.0011], P3 one head +0.0012 [0.0007, 0.0017]. The one-head test gain is not
supported on valid and is not used for selection (it would be selection on test). The GBDT loses 0.025 repeat recall to the extra
negatives. Conclusion: the cap is not binding; ranking the hard explore candidates is.
Also tried on valid only: rank-averaging the final fits (P1-tuned, P2, P3, seeds) — 0.1096 → 0.1103 at best; not adopted.

## 2026-11-03 · Tuning budget 30 trials (t31_b30)

Question: was the 10-trial budget binding? The best GBDT trial was the last one and sat near the learning-rate floor (0.029 vs 0.02);
the best P3 trial sat at its floor (0.0001). P1-tuned, P2 and P3 re-tuned on the v2 pairs with the plan's 30 trials each and the floor
lowered (`--budget 30`: studies and spaces `<model>_b30` in tuning.yml; GBDT learning rate ≥ 0.005, P3 lr ≥ 0.00002; GBDT max rounds
3 000 → 6 000, no earlier fit reached 3 000). Same budget for every ranker, as D5 requires. Decision on valid, TH + VN NDCG@20, 10 → 30
trials: P1-tuned 0.1088 → 0.1089, P2 0.1089 → 0.1088, P3 two heads 0.1087 → 0.1086, P3 one head 0.1096 → 0.1092 — **10-trial fits kept**.
Test, reported once (t31_b30_paired, 30 − 10): P1-tuned +0.0001 [−0.0003, 0.0006], P2 +0.0007 [0.0003, 0.0011], P3 two heads −0.0002
[−0.0005, 0.0001], P3 one head −0.0000 [−0.0003, 0.0003]. The search had converged; the order of t31 stands.

## 2026-11-03 · Purchase-history-only ranker (t31_hist)

Question: how much of the gain over the status quo (recommending from purchase history alone) comes from the extra data dimensions,
and how much from the pipeline (multi-source retrieval + learned ranker)? P1 re-tuned (10 trials, study `p1_v2_hist`) and refitted
on the v2 pairs with `gbdt.py --history-only`: 39 of the 85 features kept (`HISTORY` in gbdt.py) — R1 / R2 / R5 and the learned source
ranks, own and department history, co-purchase, sales popularity / season / model age, activity counts, country. Dropped: web (R3,
its rank and `candidate_rank`, which mixes it), prices and promotions, stock, stores, calendar, sport affinity, member price
profile, returns, tenure, GMV. The candidate pool is unchanged (it still holds the R3 candidates, without the features that say
why), and the two-tower / trend sources use the paid unit price of the sales lines; both make the history-only row slightly
optimistic. Valid, TH + VN NDCG@20: GP-TopFreq 0.0819, TIFU-KNN 0.0890, P1-hist 0.1044, P1-tuned 0.1088, P3 one head 0.1096.
Test, reported once (t31_hist, t31_hist_paired): GP-TopFreq 0.0752, P1-hist 0.0966, P1-tuned 0.1011, P3 one head 0.1020;
P1-hist − GP-TopFreq +0.0214 [0.0204, 0.0225], P1-tuned − P1-hist +0.0045 [0.0039, 0.0052], P3 one head − P1-hist +0.0054
[0.0046, 0.0062]. Of the +0.0268 of P3 one head over GP-TopFreq, about 80 % is reached on history alone and 20 % needs the other
dimensions; the multi-dimensional gain is in explore recall (+0.0077) and costs some repeat recall in the GBDT (−0.0086).
