# I. Introduction

An omnichannel retailer knows a great deal about its loyalty members: what they bought and returned, what they looked at on the web
site and in the app, which sports they follow, and, for every product, its price, promotions, stock and season. Yet the list a
member sees is usually the same for everyone, the national best-sellers, or a reminder to buy the same items again. Given a member u
at an anchor Monday t, we predict the product models u buys in (t, t + 30] as an ordered top-K list. A natural baseline is a
rule-based two-stage recommender: five candidate rules (R1 repeat, R2 co-purchase, R3 web department, R4 sport × offer, R5 national
best-sellers) propose 200 models per (member, Monday) anchor, and a LightGBM LambdaRank ranker (P1), tuned once over 73 Gold pair
features, orders them. Scored on anchors where the candidate list contains at least one purchase, it reaches NDCG@20 = 0.206.
Measured over every anchor with a purchase, counting purchases outside the list as misses, the same model scores 0.090 (TH + VN:
0.095), and 40.7 % of the anchors have no purchase in the list at all (t28).

This paper builds the data foundation first and then measures what each modelling step is worth. It turns eleven operational exports
into a leakage-controlled lakehouse, reformulates next-basket recommendation as a two-stage problem in which retrieval is a model
with its own objective, and compares tuned gradient-boosted trees, a stacked variant and a deep multi-task ranker with strong
next-basket baselines under one tuning budget. The research questions are phrased as questions, not as expected orderings, because a
GBDT win is a valid outcome:

- **RQ1 (data).** Can eleven raw operational exports become a point-in-time, leakage-free feature store at member–week grain on one
  machine, and what does it hand to the models?
- **RQ2 (retrieval).** Scored over every purchase, where does the rule-based recommender fail; how much do explore-only learned
  candidate sources raise candidate recall and explore coverage over R1–R5, at what cost, and how much of that gain reaches NDCG@20
  when the ranker is unchanged?
- **RQ3 (ranking and tuning).** On the shared 300-candidate pool and under a uniform 10-trial budget, which ranker wins (tuned GBDT,
  stacking, a deep multi-task ranker with repeat and explore heads, vs NBR baselines on their own candidate lists), and how much of
  the gain comes from features, hyper-parameter tuning and the model family?
- **RQ4 (value).** How many times better than "best-sellers" and "buy the same again" is the best system, for whom, at what compute
  cost, what purchase value does it capture (offline proxy), and how much of its gain needs data beyond the purchase history?
- **H1 (hypothesis).** Naive stacking inflates metrics on training and pseudo-test anchors relative to a rolling protocol; on the real
  test the gap narrows but does not vanish.

Contributions: (1) a Bronze / Silver / Gold lakehouse with seven quality gates and a point-in-time ledger that turns the exports into
model inputs with zero leakage violations; (2) an unconditional evaluation protocol with a repeat / explore split and a positive-level
error decomposition that locates 58 % of all test purchases (63.1 % of those missed outside the top 10) in retrieval rather than
ranking; (3) an explore-only retrieval layer of eight learned sources refitted quarterly in every split, with a rank-quota mixer;
(4) a controlled comparison of P1-tuned, P2 and P3 on the shared 300-candidate pool and five NBR baseline families on their own
lists, separating features, tuning and model family, with a controlled measurement of stacking leakage (naive / rolling / leaky);
(5) a static demo with privacy safeguards that also shows the best model's batch output on real, anonymised members.

# II. Related work

*Next-basket recommendation.* The reality check of Li et al. (TOIS 2023) showed that repeat purchases dominate common NBR metrics and
that simple frequency baselines (P-TopFreq, GP-TopFreq) are hard to beat; it introduced the repeat / explore recall split used here.
TIFU-KNN (Hu et al., SIGIR 2020) models personal item frequency with time decay and neighbour smoothing.

*Item-based and graph retrieval.* EASE (Steck, WWW 2019) is a closed-form linear auto-encoder; RP3beta (Paudel et al., TiiS 2017)
re-weights random walks by item popularity; item2vec (Barkan & Koenigstein, 2016) learns co-occurrence embeddings.

*Neural retrieval and sequential models.* Two-tower models (Yi et al., RecSys 2019) score users and items in a shared space with a
softmax over items; SASRec (Kang & McAuley, ICDM 2018) and its dense all-action objective (PinnerFormer, Pancha et al., KDD 2022).
DIN (Zhou et al., KDD 2018) adds target attention over the behaviour sequence.

*Multi-task ranking and repeat-aware models.* Repeat-aware recommenders separate repeat and explore modes (RepeatNet, Ren et al., AAAI
2019; ReCANet, Ariannezhad et al., SIGIR 2022). Our P3 gates two listwise heads with a learned member-level probability.

*Leakage in stacking.* Out-of-fold or temporally rolling fits are standard for stacked models (Wolpert 1992); we measure the inflation
of an in-sample fit directly.
