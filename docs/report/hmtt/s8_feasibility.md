# VIII. Feasibility and demo

## A. Value over simple rules (RQ4, t38)

Best model selected on valid: P3 one head. Test, HR@10 (share of anchors with at least one purchase in the top 10):

| TH + VN | P3 one head | random | popular | buy-again (P-TopFreq) | × random | × popular | × buy-again |
|---|---:|---:|---:|---:|---:|---:|---:|
| all positives | 0.240 | 0.007 | 0.137 | 0.156 | 36 | 1.76 | 1.54 |
| repeat positives | 0.775 | 0.003 | 0.178 | 0.777 | 285 | 4.36 | 1.00 |
| explore positives | 0.110 | 0.006 | 0.115 | 0.000 | 17 | 0.96 | — |

"Random" is analytic: 10 slots drawn uniformly from the 5 000-model universe; "popular" is the country top 10 by buyers in the 28
days before the anchor, the same list for every member. The model is 1.8 × the
best-sellers and 1.5 × "buy the same again" overall. The split shows where the gain comes from: on repeats the model matches
buy-again (both ≈ 0.78), on explore purchases it is slightly *below* the best-sellers (0.110 vs 0.115). The value of the model is that
it does both at once in one list of ten — no single rule does.

GMV proxy (offline, not causal, D11): GMV-weighted Recall@10 0.077 against 0.053 for buy-again and 0.023 for popular, i.e. 268 EUR
of observed next-30-day purchase value per 1 000 recommendations against 184 and 79. These are purchases that happened anyway; an
online test is needed to know how many a recommendation would cause.

## B. Serving coverage (t39)

Every evaluated test anchor gets a personalised list of 300 candidates (median 300; 100 % of the anchors have at least 10). This is by
construction — the anchor grid starts after a member's second purchase — so members without a purchase history are outside the
evaluated population; at serving time they get the country best-sellers.

## C. Cost (t37)

| Candidate source | Device | Tuning h (10 trials) | Build h (13 cutoffs × 3 countries) | Valid Δ cand_explore | Δ per build hour |
|---|---|---:|---:|---:|---:|
| R6 EASE | GPU | 0.04 | 0.07 | +0.085 | 1.27 |
| R12 RP3beta | GPU | 0.05 | 0.08 | +0.088 | 1.16 |
| R8 TIFU-KNN | GPU | 0.04 | 0.08 | +0.057 | 0.75 |
| R13 trend | CPU | 0.03 | 0.13 | +0.069 | 0.54 |
| R11 explin | GPU | 0.07 | 0.47 | +0.074 | 0.16 |
| R7 item2vec | CPU | — | 0.56 | — | — |
| R9 two-tower | GPU | 2.48 | 3.05 | +0.074 | 0.02 |
| R10 SASRec | GPU | 4.19 | 3.18 | +0.085 | 0.03 |

| Ranker | Tuning h | Final fit (min) | Parameters | Test inference (s / 1 000 anchors) |
|---|---:|---:|---:|---:|
| P1-tuned | 0.25 | 3.9 | — | — |
| P2 | 0.38 | 5.1 | — | — |
| P3 two heads | 0.22 | 1.3 | 3.7 M | 0.09 |

The neural sources cost 50 – 100 × more compute than EASE or RP3beta for the same or lower coverage gain. Among the rankers the costs
are all small at this scale (150 k training anchors × 300 candidates); P3 is the fastest to fit on the GPU because of early stopping at
epoch 1 – 2.

## D. Demo v0

A static page on a public Hugging Face Space runs the recommender in the browser (Pyodide). The user uploads a purchase CSV
(`member_id, country_code, model_id, purchase_date, quantity`); the page validates it and returns the top K of each member with the
source of each item — repeat (own history with time decay), co-purchase (EASE neighbours), trend (recent country popularity) — merged
with the same rank-quota rule as the mixer, and the reason in words (number of past purchases and days since the last one; the purchased model it is often bought with; the
department it is trending in and its growth over the previous quarter). Privacy choices: model ids are salted hashes, departments carry generic labels, popularity is shown as a
percentile, the sample members are synthetic, and the salt never leaves the server. This part uses reference tables frozen at
2026-07-28 and shows the retrieval layer and its explanations.

The best model needs inputs a purchase CSV does not hold (web, price, promotion, stock and store features; the ranks of eight
learned sources, two of them and P3 itself PyTorch networks), so it is served as in production, by batch scoring in the warehouse.
The tab "Best model (back-test)" shows that output (`serve/export_showcase.py`): for 500 random test anchors (250 per country, one
per member), the top 10 of P3 one head next to GP-TopFreq, the member's purchases before the anchor and what she bought in the next
30 days. Sample HR@10: P3 0.240, GP-TopFreq 0.190 (whole test 0.240 / 0.184). Published with the data owner's consent and
minimised: sequential member ids in shuffled order, salted model hashes and generic departments of the reference, days relative to
the anchor, the last 40 history lines, no price, store, web or member attribute.

# IX. Discussion and limitations

- **GBDT vs deep.** Under the same 10-trial budget and the same candidates, the deep multi-task ranker gains about 1 % NDCG@20 over a
  tuned GBDT and only in its single-head form. The engineering effort is not repaid at this scale; the place where effort paid most
  was retrieval (+20 % coverage) and tuning (+4 % NDCG@20 on the frozen ranker).
- **Explore is still the bottleneck.** Explore coverage rose × 1.30, not × 2, and at the top 10 the model is no better than the
  best-sellers on explore purchases. On average 60 % of a member's explore purchases are still outside the 300 candidates.
- **Reduced budget.** 10 trials instead of 30, and one seed for tuning. The final fits of P1-tuned and P3 were repeated with three
  seeds: the seed spread (≤ 0.0003 NDCG@20) is smaller than the P3 one-head gain, but the trial budget itself was not repeated, so
  the hyper-parameter search noise is not measured. SASRec NBR has no NDCG@20 budget of its own.
- **Offline only.** GMV numbers are a proxy; recommendations change behaviour, which an offline replay cannot measure.
- **Scope.** SG labels are REVIEW (D1); results for SG are reported but not used for conclusions. Dropped from the plan: gSASRec, P4
  distillation, conformal intervals, drift monitoring, the what-if and parity check of the demo.

# X. Conclusion

Measured honestly, the reference recommender was half as good as reported, and most of its misses were purchases it never saw.
Treating retrieval as a model — eight explore-only sources refitted quarterly and mixed under a 300-candidate cap — raised the share of
purchases within reach from 0.370 to 0.450, and with tuned rankers that see the source ranks, NDCG@20 from 0.095 to 0.101 – 0.102 (+7 – 8 %), ahead of every next-basket baseline by more than 25 %. A deep two-head ranker with a learned gate does not beat a tuned GBDT; a
single-head version does by 1 %. The learned gate is essential, the explicit split is not. Naive stacking shows the inflation H1
predicted, small because the signals add little over a good feature store.
