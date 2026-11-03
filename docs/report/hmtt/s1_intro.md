# I. Introduction

A loyalty member of a multi-country sporting-goods retailer opens the app on a Monday: which product models will they buy in the next
30 days? The previous course project (KTXLDL) built a point-in-time feature store over eleven exported tables and a LightGBM
LambdaRank ranker (P1) over 200 candidates per (member, Monday) anchor. It reported NDCG@20 = 0.206 — but only on anchors where the
candidate list contained at least one purchase. Measured over every anchor with a purchase, counting purchases outside the list as
misses, the same model scores 0.090 (TH + VN: 0.095), and 40.7 % of the anchors have no purchase in the list at all (t28).

This paper asks where those errors are and what it takes to fix them. It reformulates next-basket recommendation as a two-stage
problem in which retrieval is a model with its own objective, and compares a deep multi-task ranker against tuned gradient-boosted
trees and strong next-basket baselines under one tuning budget. The research questions are phrased as questions, not as expected
orderings, because a GBDT win is a valid outcome:

- **RQ1 (retrieval).** How much do learned candidate sources (EASE, item2vec, TIFU-KNN, RP3beta, two-tower, SASRec) raise
  unconditional recall over the rule-based sources R1–R5, separately for repeat and explore purchases, at what cost — and how much of
  that gain reaches NDCG@20 when the ranker is unchanged?
- **RQ2 (ranking).** With the same tuning budget and candidates, how does an end-to-end deep multi-task ranker (P3) compare with a tuned
  GBDT (P1-tuned), stacking (P2) and next-basket baselines, overall and by segment?
- **RQ3 (repeat / explore).** Do explicit repeat and explore heads with a learned gate improve explore without hurting repeat, compared
  with a single head?
- **H1 (hypothesis).** Naive stacking inflates metrics on training and pseudo-test anchors relative to a rolling protocol; on the real
  test the gap narrows but does not vanish.
- **RQ4 (feasibility).** How many members and how much revenue can the best system serve; how many times better than "best-sellers"
  and "buy the same again" is it; what GMV does it capture (offline proxy)?

Contributions: (1) an unconditional evaluation protocol with a repeat / explore split and a positive-level error decomposition that
locates 58 % of the missed purchases in retrieval rather than ranking; (2) an explore-only retrieval layer of eight learned sources
refitted quarterly in every split, with a rank-quota mixer; (3) a fair-budget comparison of P1-tuned, P2, P3 and five baselines on the
same candidates; (4) a controlled measurement of stacking leakage (naive / rolling / leaky); (5) a static demo with privacy safeguards that also shows the best model's batch output on real, anonymised members.

# II. Related work

*Next-basket recommendation.* The reality check of Li et al. (TOIS 2023) showed that repeat purchases dominate common NBR metrics and
that simple frequency baselines (P-TopFreq, GP-TopFreq) are hard to beat; it introduced the repeat / explore recall split used here.
TIFU-KNN (Hu et al., KDD 2020) models personal item frequency with time decay and neighbour smoothing.

*Item-based and graph retrieval.* EASE (Steck, WWW 2019) is a closed-form linear auto-encoder; RP3beta (Paudel et al., TiiS 2017)
re-weights random walks by item popularity; item2vec (Barkan & Koenigstein, 2016) learns co-occurrence embeddings.

*Neural retrieval and sequential models.* Two-tower models (Yi et al., RecSys 2019) with in-batch softmax; SASRec (Kang & McAuley,
ICDM 2018) and its dense all-action objective (PinnerFormer, Pancha et al., KDD 2022). DIN (Zhou et al., KDD 2018) adds target
attention over the behaviour sequence.

*Multi-task ranking and repeat-aware models.* Repeat-aware recommenders separate repeat and explore modes (RepeatNet, Ren et al., AAAI
2019; ReCANet, Ariannezhad et al., SIGIR 2022). Our P3 gates two listwise heads with a learned member-level probability.

*Leakage in stacking.* Out-of-fold or temporally rolling fits are standard for stacked models (Wolpert 1992); we measure the inflation
of an in-sample fit directly.
