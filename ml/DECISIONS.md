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
