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

## 2026-11-03 · Demo: best model as batch output on real members (showcase)

The demo ran only the retrieval layer, so it showed none of the measured accuracy. The best model (P3 one head) cannot score an
uploaded CSV: it needs the Gold web / price / promotion / stock / store features and the ranks of eight learned sources, two of them
PyTorch networks, which do not run in Pyodide. It is served as a retailer would serve it, by batch scoring in the warehouse; the
Space gets a tab with that output (`serve/export_showcase.py` → `showcase.json`): 500 test anchors, 250 per country, one per member,
drawn uniformly (seed 0), with P3 one head and GP-TopFreq top 10, the history before the anchor and the purchases of the next 30
days. Sample HR@10 0.240 vs 0.190 (whole test 0.240 vs 0.184). The sample of real members is published with the data owner's
consent and minimised: sequential member ids in shuffled order (no hash of the real id), the reference's salted model hashes and
generic departments, days relative to the anchor, the last 40 history lines, no price, store, web or member attribute.

## 2026-11-03 · Report review experiments (t28c, epochs_*, t31 rows, r1_first)

Test, TH + VN, Δ = 30 unless stated; valid is the decision data.
- Features against tuning (`frozen.py --features all`, `p1_frozen_allfeat_v2`): the frozen parameters with the 85 v2 features give
  0.1001; P1-frozen v2 0.0973, P1-tuned 0.1011. Paired: new features +0.0028 [0.0021, 0.0035] (explore +0.0069), tuning +0.0011
  [0.0005, 0.0016] (repeat +0.0235). The +0.0039 of P1-tuned over P1-frozen is mostly features, not tuning.
- Fate of the positives on candidates_v2 + P3 one head and universe ceiling (`eval/error_analysis_v2.py`, t28c): top 20 13.2 %,
  rank 21+ 28.1 %, capped 9.4 % (R5 proposes 42 % of them), no source inside the universe 35.2 %, outside it 14.0 %. The universe of
  the anchor's cutoff holds 84.5 % of the positives (85.9 % member mean), 86.0 % are reachable by some source; the anchor_model_grid
  filter loses 0.04 %. The "3 %" of t28b was the popularity rank at the anchor, not the universe at the cutoff.
- Mixer weights (`mixer.py --policies r1_first`, candidates_v2r1, `p1_tuned_v2r1` with the p1_v2 parameters): repeat coverage
  0.972 → 0.997, explore −0.001; valid NDCG@20 0.1087 against 0.1088, test +0.0004 [−0.0001, 0.0009]. Fixed weights kept.
- Epoch budget of the neural sources (`retrieval/epochs_check.py`, TH, valid cutoff): Δ cand_explore 4 / 8 / 16 epochs two-tower
  0.074 / 0.077 / 0.082, SASRec 0.077 / 0.084 / 0.090. Both are under-trained at 8 epochs; candidates not rebuilt (limitation).
- SASRec NBR with full targets (`baselines/nbr.py --source sasrec_all`, SASRecAll: R10 network and parameters, repeats in the
  target, nothing masked): 0.0751 against 0.0606 for the R10 unmasked list (+0.0146 [0.0135, 0.0157], repeat recall 0.43 → 0.57);
  ties with GP-TopFreq (0.0752), below TIFU-KNN (−0.0036 [−0.0049, −0.0025]). Added to t31 as a second SASRec row.
- Serving coverage of the real test-window sales (business.py, t39): identified members 93 % / 81 % of the GMV (TH / VN), members
  with a prior purchase (personalised path) 71 % / 56 %. GMV per 1 000 recommendations over every anchor: P3 one head 112 EUR,
  buy-again 77, popular 33 (268 / 184 / 79 over the anchors with a purchase).
- `serve/check_public.py` gates every upload of the Space: structure in CI (deploy-space.yml, after staging: salted-hash model ids
  in the CSVs and showcase.json, only the published showcase fields, member ids `<country>-NNN`, no UUID / local path / salt) and,
  in `make demo-push`, also the raw model codes and member ids of the lakehouse (`--db`) and the REDACT_TERMS tokens
  (`--require-terms`). Current Space (11 files, showcase included): 0 hits; a tampered copy is caught (serve/tests).

## 2026-11-03 · Learned mixer (ML-13b, t30c, candidates_v2lm)

A LightGBM binary model scores the mixer's k_max list (up to 500 per anchor, ≈ 468 on average) from the rank in each source, the
number of proposing sources, the fixed-mixer rank and the country (`retrieval/learned_mixer.py`; 120 000 train anchors, positives
weighted 1 / |positives in the list|, early stopping on 10 % of them). Train lists are cross-fitted (two folds by member).
- Valid, TH + VN, K = 300: coverage 0.4847 → 0.5018, repeat 0.976 → 0.993, explore 0.4328 → 0.4495 (union of all sources 0.5669).
  40 000 or 120 000 training anchors give the same gain (+0.017); the model stops before 100 rounds. Main features: fixed-mixer rank,
  number of sources, R1 and R5 ranks.
- candidates_v2lm (QC-6 0, pairs leakage 0), P1 refitted with the p1_v2 parameters (`p1_tuned_v2lm`): valid TH + VN NDCG@20 0.1084
  against 0.1088 (repeat recall@20 0.817 → 0.792, explore 0.0996 → 0.1014). Test, paired against P1-tuned v2: +0.0004
  [−0.0002, 0.0009], explore +0.0021 [0.0007, 0.0035], repeat −0.0243 [−0.0296, −0.0192].
- Decision: candidates_v2 and the fixed mixer are kept. As with K = 500 and r1_first, more coverage does not reach NDCG@20: the
  extra positives are explore candidates the ranker places below rank 20, and the extra repeat candidates dilute the repeat ranking.
- Re-tune on v2lm (study p1_v2lm, 10 trials, `p1_retuned_v2lm`): best valid 0.1030 at trial 9, the same parameters as p1_v2, so the
  final fit equals `p1_tuned_v2lm`. Optuna's TPESampler starts with 10 random trials (n_startup_trials default), so with a 10-trial
  budget and sampler seed 0 every study of one model draws the same 10 configurations: the 10-trial budget is a seeded random
  search, and a re-tune on other candidates only re-ranks those 10. The 30-trial check (t31_b30) is the one that goes past the
  start-up phase. Stated in the report (Section III-D).

## 2026-11-06 · REX, a single-stage Repeat–Explore network (t31_rex, t32_rex)

Question: the candidate pool holds 45 % of the positives and caps every ranker; can one model over the whole universe, with no
candidate stage and no ranker, match the pipeline? REX (`ml/retrieval/rex.py`, run as a t31 NBR row by `nbr.py --source rex`) is
fitted per country × cutoff like the learned sources and scores the 5 000-model universe; logit = explore u · v (basket transformer
+ RFM + month against model / department / price bucket) + popularity MLP (buyers in the 7 / 30 / 90 days before t, trend, same
30 days a year earlier) + repeat MLP on the member's history of the model (purchase days, recency, age, decayed counts, repurchase
rate and cycle of the model before the cutoff) + web MLP (views and cart events in the 30 days before t, attribution known before
t). Reference days uniform in the 30 days before a purchase, t + Δ < cutoff; target every model bought in (t, t + Δ]; 8 epochs.
Tuned with the 10-trial budget on valid NDCG@20 (all countries): best 0.1060 (d 128, 2 blocks, dropout 0.008, lr 0.0008).
Test, TH + VN, reported once (t31_rex, three seeds): REX 0.1033 / 0.1029 / 0.1030, P3 one head 0.1020 / 0.1022 / 0.1022;
paired by seed +0.0012 [0.0001, 0.0023], +0.0006 [−0.0004, 0.0017], +0.0008 [−0.0002, 0.0019]; over TIFU-KNN +0.0245
[0.0234, 0.0255]. Recall repeat 0.805 vs 0.831, explore 0.0905 vs 0.0910. Ablation (t32_rex, parameters of REX, paired against
it): no web −0.0027, no popularity −0.0155, no repeat −0.0133, no sequence (member = RFM + month) −0.0121, every interval below 0.
Rejected on valid (all countries, REX 0.1054, seeds 0.1040–0.1054), never run on test: REX v2 = price / promotion of the model on
t − 1, the member's price affinity and her own repeat share and cycle (`rex2`, 0.1055); her repeat features alone
(`rex2_noprice`, 0.1058); 16 epochs (0.1015, overfits at dropout 0.008). Stock stays out (spare parts only, issue #21).
Reading: one model matches the 13-source pipeline, so the candidate cap rather than the ranker bounds it; REX uses no price, store
or member attribute, is harder to explain than the GBDT and needs a GPU. REX as a source or as a ranker feature is not tested.

## 2026-11-07 · REX with the pipeline: rank fusion and REX ranker features (t31_hybrid)

Question: do REX and the two-stage pipeline err on different anchors, so that combining them beats both? Ceilings on test TH + VN
first: a perfect order of the repeat positives alone gives 0.114, a perfect re-order of the REX top 20 0.190 and of its top 100
0.372, so the room is in the order of explore models REX already lists. (1) Rank fusion (`ml/eval/fusion.py`): w / (k + rank_REX)
+ (1 − w) / (k + rank_other), w ∈ {0.3…0.7}, k ∈ {5, 20, 60} and the partner (P1 tuned, P2, P3 one head) selected on valid
(all countries): P3 one head, w 0.5, k 5, valid 0.1098. (2) REX as ranker features (`ml/retrieval/rex_pairs.py`): REX refitted per
country × cutoff over the anchors of candidates_v2 (train anchors included, the model of cutoff_for(anchor), assert_pit clean),
log-softmax probability and rank of each candidate pair → pairs_v2rex (102,686,571 rows, as pairs_v2; coverage 94–99.7 %, the
rest train anchors before the first cutoff and models outside the universe); P1 retuned on it with the same 10-trial budget
(valid 0.1083). Test, TH + VN, reported once: fusion 0.1066 (HR@10 0.2503), P1 + REX features 0.1060, REX 0.1033, P3 0.1020,
P1 0.1011. Paired: fusion − REX +0.0033 [0.0027, 0.0039], fusion − P3 +0.0045 [0.0039, 0.0052]; P1 + REX − P1 +0.0048
[0.0041, 0.0056] (explore recall +0.0054), P1 + REX − fusion −0.0006 [−0.0012, 0.0001]. The fusion is kept (best on valid); P1 +
REX is its equal on test, stronger on explore, weaker on repeat (−0.036).
Reading: the combination adds 3–5 thousandths, the size of every model step so far; NDCG@20 0.2 at the model level is out of reach
of model changes alone (t40).

## 2026-11-07 · Seed and three-way rank fusion at the model level (t31_ens)

`ml/eval/fusion.py` generalised to weighted RRF of N score sets (DuckDB; weight set and k selected on valid, all countries).
Equal-weight fusion of the three REX seeds (`rex_ens3`, valid 0.1069 against 0.1054 for one seed) and of the three P3 one-head
seeds (`p3_ens3`, 0.1051); REX ensemble + P3 ensemble 0.1102 (the one-seed fusion 0.1098); with P1 + REX features as a third list
(`ens_main`, weights 0.4 / 0.3 / 0.3 over five sets, k 5) 0.1111, paired on valid against the one-seed fusion +0.0013
[0.0006, 0.0020]. Test, TH + VN, reported once: `ens_main` 0.1082 (HR@10 0.2536, explore recall 0.0982), REX ensemble 0.1050;
paired: `ens_main` − one-seed fusion +0.0017 [0.0013, 0.0021], − REX +0.0050 [0.0043, 0.0057], − P1 + REX +0.0023
[0.0018, 0.0028]; REX ensemble − REX +0.0017 [0.0013, 0.0022]. Rejected on valid, never run on test: REX supermodel ranking as a
prior of the fusion (RRF of the model rank and the rank of its supermodel, +0.0009 on the one-seed fusion, +0.0004 on `ens_main`).
Reading: `ens_main` is the best model-level list; it costs three REX and three P3 trainings plus the P1 pipeline.

## 2026-11-08 · REX pooled over the three countries (t31_pool)

Question: VN has a third of the purchases of TH or SG and the country universes share 73–77 % of their models; does one network
trained on every country learn better explore embeddings? `REXPool` (`nbr.py --source rex_pool`): one REX per cutoff on
Events.pool(SG, TH, VN) (members keyed by country, a member of two countries counted twice; unit prices as percentiles within the
country), models shared by code, a country embedding added to the month embedding; each country keeps its own universe (top
5 000 by its buyers; the softmax, the targets and the scores masked to it) and its own popularity counts; web attention and
repeat inputs as REX; the REX parameters, no retuning. `full_target_loss` now takes the log-probability on the targets only
(0 × −inf off them under the mask; unchanged values without a mask). Valid (all countries): 0.1079 against REX 0.1054 (seeds
0.1040–0.1054). Fusion, selected on valid: pooled REX + P3 ensemble + P1 + REX features (`ens_pool3`, weights 0.5 / 0.25 / 0.25,
k 5) 0.1118; adding the REX seed ensemble as a fourth list 0.1119, not kept (one more list for 0.0001). Test, TH + VN, reported
once: pooled REX 0.1056 (REX 0.1033, REX ensemble 0.1050), paired − REX +0.0024 [0.0017, 0.0032] (explore recall +0.0068, repeat
−0.0134), − REX ensemble +0.0007 [−0.0001, 0.0014]; by country SG +0.0005, TH +0.0014, VN +0.0036. `ens_pool3` 0.1093 (HR@10
0.2560, explore recall 0.1011), − `ens_main` +0.0011 [0.0005, 0.0016], − one-seed fusion +0.0027 [0.0022, 0.0033].
Reading: pooling helps the smallest country most and replaces the three-seed REX ensemble with one training; `ens_pool3` is the
best model-level list.

Retuned (2026-11-09, tuning.yml rex_pool: the REX space with d up to 384, 10 trials, valid NDCG@20 all countries): best d 384,
1 block, dropout 0.084, lr 0.00017, valid 0.1083 (REX parameters 0.1079; trials 0.0940–0.1083); the first build, kept as
`rex_pool_v0_nbr`, is replaced by `rex_pool_nbr`. Fusion reselected on valid (`ens_pool3t`, weights 0.4 / 0.3 / 0.3, k 5,
0.1122). Test, TH + VN, reported once: pooled REX 0.1076 (HR@10 0.2534, explore recall 0.1009), − untuned +0.0020
[0.0013, 0.0026]; `ens_pool3t` 0.1102 (HR@10 0.2567, explore recall 0.1030), − `ens_pool3` +0.0009 [0.0005, 0.0014]. The
valid gain (+0.0004) was within the seed spread, the test gain is larger; `ens_pool3t` is the best model-level list.

## 2026-11-07 · NDCG@20 at coarser product levels (t40_granularity)

Question: the target NDCG@20 ≥ 0.2 is out of reach at the model level; which change of the task reaches it, and does the model
still beat popularity there? Label windows first (valid, the Δ = 30 lists re-scored): Δ 7 / 14 / 30 / 60 / 90 and the next basket
only give 0.106–0.118 for the fusion, so the window is not the lever. Product level: `ml/eval/granularity.py` re-runs D3 with the
positives = the distinct groups bought in (anchor, anchor + Δ] (returns netted, repeat = a model of the group bought before), a
model list turned into a group list by the best model score of each group; levels from bronze.dim_item (one group per model):
supermodel (all variants of a product), product nature (the product type), retail family, sub-department, department. REX is
also trained directly at a level (`nbr.py --source rex --level <level>`: Events, web attention, universe, targets and the
anchor_model_grid filter at the group level, the model-level parameters, no retuning).
Test, TH + VN, reported once (NDCG@20; most popular / best model-level list aggregated / REX trained at the level): model 0.075 /
0.107 / –; supermodel 0.111 / 0.140 / 0.147; nature 0.297 / 0.323 / 0.372; family 0.270 / 0.298 / –; sub-department 0.430 /
0.452 / –; department 0.560 / 0.592 / –. Paired at nature: REX nature − aggregated fusion +0.0491 [0.0473, 0.0508], − most popular
+0.0750 [0.0730, 0.0770] (explore recall +0.140); at supermodel: REX supermodel − aggregated fusion +0.0074 [0.0063, 0.0085].
Rejected on valid, never run on test: the nature ranking of REX nature as a prior of the model-level fusion (RRF of the model rank
and the rank of its nature, w and k on valid: +0.0004, within the seed spread); REX with product-nature and retail-family
embeddings in the item tower (`rex_hier`, 0.1047 against 0.1054, seeds 0.1040–0.1054).
Reading: the 0.2 target is met by predicting the product type a member buys next (0.372, 0.075 over popularity), a different and
coarser question than the model; coarser still (sub-department, department) popularity alone exceeds 0.4 and the model adds less
than at nature. The model level stays the headline metric; the nature level is reported as the product-type task.
