# 5. Feature store, candidates, experiments and results

> Numbers: three-country server run of 2026-10-28 — Gold build (tables t09 – t12), training, ablation, bootstrap and profiler (t22 – t26) —
> and of 2026-10-29 for the scale test (§5.9) and the technique comparisons (§5.10, t13). Tables are in `docs/report/tables/`; the
> per-member result files stay in `data/audit/` and are not committed.

## 5.1 Anchor grid and feature store

The unit of prediction is (member, anchor Monday). Over the three countries the grid places 143.6 M training anchors, 18.2 M validation
anchors and 59.4 M test anchors after a member's second purchase; the 90-day purchase rule keeps 46.9 M, 4.9 M and 15.3 M of them, the
training stride of four 11.7 M, and the per-country cap by hash rank leaves 50,000 / 15,000 / 50,000 used anchors per country —
345,000 in all, held by 41 – 49 k distinct members per country for the training and test anchors and 13.7 – 15 k for validation **(t10)**. Three entities are built for those anchors
(chapter 3, §3.6): the member entity (345,000 rows), the model × country entity (4,290,920 rows = the model grid, no row lost) and the
pair entity (69,000,000 rows, 10.7 GB), each reading only data strictly before the anchor and carrying `last_source_ts` **(t11)**.

The web features reach the anchors unevenly **(t09)**: 18.76 % of the SG test anchors, 5.52 % in TH and 7.30 % in VN have an
attributed event in the 30 days before the anchor, against 5.08 %, 1.79 % and 3.61 % of the training anchors, most of which precede the
click-stream (TH from 2023-04-26, usable VN events from 2024-07-01). `web_data_available` keeps "no data" apart from "no activity":
48,989 of the 50,000 TH training anchors and 33,050 of the VN ones have usable events somewhere in their window. These shares bound
what the web ablation of §5.6 can show.

## 5.2 Candidate generation and recall

Each anchor receives exactly 200 candidates — 69,000,000 rows, every anchor filled to the cap — from five sources in priority order:
R1 repurchase, R3 web, R2 co-purchase, R4 sport × offer, R5 national best-sellers (DESIGN §2). Recall@200 against the labels **(t12)**,
test split, Δ = 30:

| Country | Positives | Any source | R1 repurchase | R2 co-purchase | R3 web | R4 sport × offer | R5 best-sellers |
|---|---:|---:|---:|---:|---:|---:|---:|
| SG | 74,946 | 0.280 | 0.090 | 0.037 | 0.016 | 0.0002 | 0.210 |
| TH | 75,011 | 0.328 | 0.089 | 0.045 | 0.013 | 0.0001 | 0.270 |
| VN | 63,332 | 0.351 | 0.073 | 0.040 | 0.015 | 0.0001 | 0.303 |

At Δ = 90 the union reaches 0.266 / 0.311 / 0.324. Three facts matter for what follows. The best-sellers carry the bulk of the reachable
purchases, and SG's lower recall is almost entirely R5 (0.210 against 0.303 in VN): its purchases spread over more models. The web
source is now measurable everywhere (0.013 – 0.016 on the test split, against 0.004 – 0.009 on training anchors that mostly predate the
click-stream). The sport × offer source brings almost nothing as a *candidate* source (0.0002), which is why it is kept only as a
feature. Co-purchase recall is higher on the training split (0.059 – 0.086) than on test (0.037 – 0.045) because the co-purchase
statistics are computed on the training period — the expected in-sample optimism, not leakage: the cutoff test of §4.6 guarantees that
no validation or test purchase enters them.

## 5.3 Ranking dataset and labels

The ranking dataset is the pair entity with the labels attached: 30,000,000 training rows, 9,000,000 validation rows and 30,000,000
test rows (the 115,000 anchors per country × 200 candidates). A candidate is positive when the member buys the model within Δ days of
the anchor and does not return it: 72,951 / 22,558 / 67,803 positives at Δ = 30 and 201,570 / 56,958 / 188,177 at Δ = 90 for the three
splits — a label rate of 0.23 – 0.25 % at Δ = 30 **(t27, server build of 2026-10-29)**. The horizon Δ = 30 is the primary one (DESIGN
§2); Δ = 90 is reported alongside because it triples the positives and sits at the median of the inter-purchase gap (§4.3).

## 5.4 Training protocol

The ranker is a LightGBM LambdaRank model (NDCG objective, `eval_at` 10 and 20) trained on the training rows, with early stopping on
the validation NDCG@20 and the test split touched once per arm. The Full configuration tunes once — 192 boosting rounds, 63 leaves,
learning rate 0.05, feature and bagging fractions 0.8, lambdarank truncation 20, seed 42 — and freezes those values in
`evaluation/frozen_params.json`; every ablation arm reuses them, so the arms differ only in the data they see (DESIGN §2). On the
server (16 threads) a Δ = 30 training takes 260 – 286 s and a Δ = 90 training 584 – 648 s; the 22 runs of the ablation took 2 h 43 min
in all, and no dbt rebuild was done per arm — the processing cost comes from one profiler pass instead (§5.7) **(t26)**.

Metrics are computed per (member, anchor) on the test rows and averaged: HR@k (a bought model among the top k), MRR@k, NDCG@k for
k = 10 and 20, and Recall@50; the metric rows are reported for anchors with at least one positive label in the window (36,407 members
at Δ = 30, 88,251 at Δ = 90). Confidence intervals come from a member-level bootstrap (500 resamples) of the metric and of the paired
difference arm − Full; an effect is called significant when the 95 % interval of the difference excludes zero **(t22, t23)**.

## 5.5 Full pipeline: overall, per country, per segment

| Scope | Δ | Members | HR@10 | MRR@10 | NDCG@10 | HR@20 | NDCG@20 [95 % CI] | Recall@50 |
|---|---|---:|---:|---:|---:|---:|---|---:|
| All | 30 | 36,407 | 0.3667 | 0.1824 | 0.1776 | 0.4798 | 0.2068 [0.2040, 0.2097] | 0.5594 |
| All | 90 | 88,251 | 0.3776 | 0.1882 | 0.1727 | 0.4923 | 0.2022 [0.2005, 0.2037] | 0.5415 |
| SG | 30 | 12,144 | 0.3638 | 0.1784 | 0.1778 | 0.4754 | 0.2066 [0.2017, 0.2119] | 0.5582 |
| TH | 30 | 12,922 | 0.3919 | 0.2031 | 0.1914 | 0.5051 | 0.2225 [0.2178, 0.2273] | 0.5764 |
| VN | 30 | 11,341 | 0.3411 | 0.1632 | 0.1618 | 0.4556 | 0.1893 [0.1848, 0.1942] | 0.5413 |
| new (≤ 1 tx in the previous year) | 30 | 9,717 | 0.3223 | 0.1579 | 0.1537 | 0.4231 | 0.1792 [0.1731, 0.1850] | 0.5053 |
| mid (2 tx) | 30 | 7,161 | 0.3695 | 0.1804 | 0.1793 | 0.4751 | 0.2066 [0.1999, 0.2123] | 0.5484 |
| loyal (≥ 3 tx) | 30 | 19,669 | 0.3878 | 0.1953 | 0.1888 | 0.5095 | 0.2206 [0.2169, 0.2251] | 0.5901 |

**(t23)**. The Full ranker places a model the member actually buys within the next 30 days in the top 10 for 36.7 % of the anchors
with a purchase and in the top 50 for 55.9 %. TH is the easiest country and VN the hardest, in line with the candidate recall of §5.2;
SG sits in between although its gates put it in the REVIEW group (§4.2) — its labels miss the repurchases of unlinked transactions, so
its absolute values are a lower bound. Loyal members are easier than new ones by 0.04 NDCG@20, the gap the history-based sources
explain in §5.6. Δ = 90 raises HR and lowers NDCG and Recall: more positives per anchor, spread over more models.

## 5.6 Ablation: what each source is worth

Two axes, eleven arms (the −stock arm is skipped while the stock signal is off, §4.3), each retrained with the frozen parameters. A
feature arm drops the columns of one feature group from the ranker; a candidate arm keeps the pair table but scores the candidates of
one source at −∞, so the metrics show what the ranker can no longer reach. B0 keeps purchase history and national popularity only
(DESIGN §6). Differences to Full on the test anchors, all countries **(t22)**:

| Arm | Δ30 NDCG@20 diff [95 % CI] | sig | Δ30 HR@10 / Recall@50 diff | Δ90 NDCG@20 diff | sig |
|---|---|---|---|---|---|
| B0: history + popularity | −0.0179 [−0.0195, −0.0163] | yes | −0.0271 / −0.0420 | −0.0128 | yes |
| −R1 repurchase | −0.1113 [−0.1144, −0.1081] | yes | −0.1744 / −0.2101 | −0.1091 | yes |
| −R5 best-sellers | −0.1061 [−0.1095, −0.1034] | yes | −0.1816 / −0.2492 | −0.1052 | yes |
| −R2 co-purchase | −0.0193 [−0.0209, −0.0177] | yes | −0.0239 / −0.0539 | −0.0153 | yes |
| −F5 web features | −0.0161 [−0.0175, −0.0146] | yes | −0.0232 / −0.0324 | −0.0076 | yes |
| −R3 web candidates | −0.0159 [−0.0173, −0.0147] | yes | −0.0229 / −0.0299 | −0.0081 | yes |
| −F1 price | −0.0029 [−0.0039, −0.0019] | yes | −0.0013 (n.s.) / −0.0103 | −0.0027 | yes |
| −sport features | −0.0013 [−0.0022, −0.0004] | yes | −0.0020 (n.s.) / −0.0064 | +0.0001 | no |
| −R4 sport × offer | −0.0012 [−0.0021, −0.0002] | yes | −0.0005 (n.s.) / −0.0021 (n.s.) | −0.0004 | no |
| −F3 promotion & calendar | −0.0005 [−0.0015, 0.0005] | no | −0.0011 (n.s.) / −0.0031 (n.s.) | −0.0008 | yes |

Four readings.

1. **Repurchase and best-sellers are the backbone.** Without either, NDCG@20 roughly halves (0.0956 and 0.1007 remain) and Recall@50
   loses 21 – 25 points; the two sources are complementary — one reaches what the member bought before, the other what everybody buys —
   and neither costs anything beyond the fact and product entities.
2. **Co-purchase is the best second-order source**: −0.0193 NDCG@20 and −0.0539 Recall@50 when removed, for a model that builds in
   20 seconds (§5.7). Its effect is largest for loyal members (−0.0264) and smallest for new ones (−0.0047), as a basket-based source
   should be.
3. **The web click-stream is real but modest, and horizon-dependent.** Dropping the web features (−0.0161) or the web candidates
   (−0.0159) costs about the same, which says the two uses of the same source overlap; the effect halves at Δ = 90 (−0.0076 / −0.0081),
   where positives are farther from the anchor than a 7- or 30-day browsing window reaches. Per country it follows the share of
   anchors with a web signal: SG −0.0208, VN −0.0159, TH −0.0118 (18.8 %, 7.3 % and 5.5 % of test anchors, §5.1). Across segments it
   is the one source that is nearly uniform (−0.012 to −0.019): it also helps members without purchase history.
4. **Price is small but consistent; sport and calendar are not.** The price group is significant on NDCG@20 at both horizons
   (−0.0029 / −0.0027) and on every metric at Δ = 90. The sport features and the sport × offer source are significant only at Δ = 30 and
   only just; the promotion and calendar features never move NDCG@20 at Δ = 30 and barely at Δ = 90 (−0.0008), although the calendar
   itself passes its quality checks (§4.9). B0 confirms the picture from the other side: history and popularity alone reach 0.1890,
   0.0179 below Full — the whole contribution of prices, promotions, web, sport and stock together is about 9 % of the NDCG@20.

The bootstrap gives the same ordering in every country and segment (`data/audit/ablation_results_d30.csv`, scopes SG / TH / VN / new /
mid / loyal); the only sign changes are at the bottom of the table (sport and R4 at Δ = 90), where the intervals include zero.

## 5.7 Cost × gain

The profiler rebuilt every Silver and Gold model alone on the server (wall time, peak resident memory of the dbt process tree, output
rows and bytes; 18 models timed, 19:55 → 20:56 UTC). `evaluation/mt3_table.py` joins each arm's gain (Full − arm, with the bootstrap
interval) to the cost of what the arm removes: the models that exist only for that source, the Bronze load time of the raw tables that
feed only that source, and the arm's training time **(t24)**:

| Removed source | Gain NDCG@20 Δ30 [CI] | Gain Δ90 | Models removed | Model wall time | Bronze load | Peak RSS | Output | Gain per 1,000 s |
|---|---|---:|---|---:|---:|---:|---:|---:|
| R1 repurchase | +0.1113 [0.1081, 0.1144] | +0.1091 | none beyond the fact / product entities | 0 | 0 | – | – | – |
| R5 best-sellers | +0.1061 [0.1034, 0.1095] | +0.1052 | none beyond `gld_fs_model_country` | 0 | 0 | – | – | – |
| R2 co-purchase | +0.0193 [0.0177, 0.0209] | +0.0153 | `gld_copurchase_lift` | 20 s | 0 | 14.8 GB | 0.13 GB | 0.965 |
| F5 / R3 web | +0.0161 [0.0146, 0.0175] | +0.0076 | `slv_web_events_clean`, `slv_user_to_member`, `gld_web_stitched` | 1,254 s | 5,221 s | 82.1 GB | 89.3 GB | 0.0025 |
| F1 price | +0.0029 [0.0019, 0.0039] | +0.0027 | `slv_price_sku_interval` | 6 s | 30 s | 1.8 GB | 0.03 GB | 0.081 |
| sport / R4 | +0.0013 [0.0004, 0.0022] | ≈ 0 | `slv_member_sport_asof` | 4 s | 1 s | 0.6 GB | 0.02 GB | 0.2 |
| F3 promotion & calendar | +0.0005 (n.s.) | +0.0008 | `slv_calendar_enriched` | 4 s | 0 | 0.2 GB | 0.00 GB | – |
| B0 (all of the above but R1, R2, R5) | +0.0179 [0.0163, 0.0195] | +0.0128 | six models | 1,268 s | 5,253 s | 82.1 GB | 89.3 GB | 0.0027 |

The table answers the question the project set out to ask. The click-stream is the expensive source — 1.0 bn events, 115.6 GB of
Bronze, 87 minutes to load and 21 minutes of Silver + Gold with 82 GB of peak memory, i.e. 91 % of the Bronze bytes and 97 % of
the model wall time attributable to any one source — for a gain of 0.016 NDCG@20 at Δ = 30 and 0.008 at Δ = 90. Co-purchase gives a
larger gain for twenty seconds of processing; price and sport are cheap and small; the calendar costs nothing and moves nothing. The
costs are lower bounds: two models (`slv_user_member_links`, `gld_sport_department_affinity`) were not in the profiler output and count
as zero, and training time (260 – 650 s per arm, t26) is the same for every arm because the pair table keeps its shape.

## 5.8 What the ranker uses

LightGBM gain on the Full Δ = 30 model **(t25)**: the member's history with the candidate model dominates — `hist_qty` 13.9 % of the total
gain, `hist_buy_cnt` 5.3 %, `days_since_bought` 3.2 %, `r1` 2.0 % — followed by the candidate's position and popularity (`candidate_rank`
11.0 %, `score_r5` 5.8 %, `popularity_rank` 5.5 %, `qty_28d` 2.9 %, `buyers_28d` 2.5 %). Price features appear from rank 11
(`n_sku_priced` 2.6 %, `price_q50_eur` 2.3 %, `price_local` 2.3 %, `price_gap_q50` 2.1 %) and co-purchase lift at ranks 14 and 17
(`copurchase_lift_mean` 2.3 %, `copurchase_lift_max` 2.0 %); no web, promotion or sport feature is in the top 20. The importance
ranking and the ablation agree on the order of the sources; the ablation is the one to quote, because importance measures how often a
feature is split on, not what is lost without it.

## 5.9 Scale test

`evaluation/scale_test.py` reruns staging, Silver, quarantine and audit, the anchor grid and Gold on a subset of Bronze and records the
wall time of each stage and the peak resident memory of the process tree (`audit.scale_test`; server, DuckDB 16 threads, 80 GB memory
limit, one dbt thread, `dbt run` without tests). Two axes **(figures `scale_test.png`, `scale_test_months.png`)**: countries, cumulative
VN → VN + TH → VN + TH + SG, and months of VN history, 3 → 12 → 36. The five-country point of the plan is not reachable — PH and TW
left the scope when their export proved incomplete (§2.1, issue #54) — so the months axis is the second axis.

| axis | point | Bronze sales rows | Silver | anchor grid | Gold | total | peak RSS |
|---|---|---:|---:|---:|---:|---:|---:|
| countries | VN | 11,599,372 | 173 s | 33 s | 172 s | 379 s | 58.7 GB |
| countries | VN + TH | 43,028,883 | 431 s | 129 s | 463 s | 1,023 s | 82.5 GB |
| countries | VN + TH + SG | 89,321,540 | 919 s | 216 s | 2,731 s | 3,866 s | 83.9 GB |
| months, VN | 3 | 1,302,324 | 170 s | 3 s | 69 s | 243 s | 19.9 GB |
| months, VN | 12 | 3,821,126 | 130 s | 5 s | 103 s | 238 s | 55.7 GB |
| months, VN | 36 | 9,100,972 | 145 s | 14 s | 152 s | 310 s | 56.7 GB |

Silver scales at most linearly with the sales rows (×3.7 rows from VN to VN + TH for ×2.5 the time, ×2.1 rows for the third country
for ×2.1), and so does the anchor grid. Gold is the super-linear stage: ×2.7 for the second country and ×5.9 for the third, when
the pair table reaches its 69 M rows (`gld_fs_pair` alone took 1,849 s on the full build, t19) and the click-stream stitching joins
the SG events, the largest of the three. From the second point on the peak memory sits at the DuckDB limit (82.5 and 83.9 GB resident,
the limit plus the Python and allocator overhead), so the third point's Gold time includes spilling to `data/duck_temp`; the Full
rebuild of the restored lakehouse took 17 minutes of Silver and 50 of Gold with the tests, consistent with these 64 minutes without.
On the months axis the time hardly moves: 3 → 12 months triples the rows and leaves the total at 238 – 243 s, because the run is
dominated by work that does not depend on the sales window — dbt start-up, the dimensions, the price intervals, the calendar and the
VN click-stream (172 M events) — and 36 months costs ×1.3 the time of 3 months for ×7 the rows. The practical reading for the
project: adding history is cheap, adding a country is paid in Gold, and the next SG-sized country would push the full build past the
80 GB box into spill-dominated time (§5.11).

## 5.10 Technique comparisons

The four with / without measurements of chapter 3, §3.9 (server, VN: Parquet vs CSV 6.9×, column projection 8.8×, ASOF join 1.6×, SQL
regex vs row-wise Python 15.2× on a 1-in-36 sample of the web events) are the micro-level counterpart of §5.7: they show why the
pipeline is built the way it is, while §5.7 shows what each data source buys **(t13)**.

## 5.11 Threats to validity

- **Label completeness.** Labels exist only for member-linked transactions; SG links 50 – 64 % of its transactions (§4.2), so SG's
  absolute metrics are biased downwards and its results are reported as REVIEW. Comparisons between arms inside a country are
  unaffected: every arm sees the same labels.
- **Web coverage.** Usable web events start in 2023-04 (TH) and 2024-07 (VN) and reach 5 – 19 % of the test anchors (§5.1); the web
  effect measured here is the effect on the population that has data, diluted over all anchors. `web_data_available` is in the member
  entity so that a per-population reading is possible.
- **Candidate ablation by −∞ scoring** keeps the pair table of Full, so a removed source's candidates are still absent from the top k
  but the remaining candidates keep their features; this isolates the reach of a source without retraining the candidate generator.
- **One seed, frozen parameters.** Tuning once on Full and freezing (DESIGN §2) removes tuning as a confounder but means that an arm
  with a very different feature set (B0) could reach a slightly better value with its own tuning; the bootstrap intervals cover
  sampling noise, not that.
- **Costs are measured, not modelled**, on one machine (16 threads, 125 GB, NVMe) with one dbt thread (§3.7); they are lower bounds
  where the profiler missed a model.
- **Export duplicates** in Bronze (9.5 % of the sales rows, §4.8) are removed in Silver before any feature is computed; the QC-5 check
  documents them.
