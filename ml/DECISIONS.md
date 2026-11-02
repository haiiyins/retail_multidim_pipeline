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
