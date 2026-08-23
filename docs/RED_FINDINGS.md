# RED-* FAMILY — RESULTS

Four Reddit-**inspired**, mechanically translated, **exploratory-derived**
hypotheses. Rules pre-registered in `docs/RED_PREREGISTRATION.md` and
committed before any outcome was computed. M = 4. No hypothesis was added
after results. Frozen OFH13_PROSPECTIVE_V1 was not touched, and no OFH13
prospective trade was used.

**Headline: none of the four survived. No stop or R:R research was run,
because none passed the raw-geometry gate.**

## 1. Data availability audit

| feature | status |
|---|---|
| 1m OHLC, volume, bid/ask volume, bar delta, delta % | AVAILABLE |
| cumulative delta, min/max delta | AVAILABLE |
| stacked imbalance counts 2x/3x/4x (buy+sell) | AVAILABLE |
| aggressive buy/sell volume | AVAILABLE |
| price progress up/down ticks, volume per up/down tick | AVAILABLE (native effort-vs-result) |
| absorption candidate flags + raw strength | AVAILABLE (capture's proxy) |
| ATR(20) | AVAILABLE |
| developing profile POC/VAH/VAL, insideValueArea | AVAILABLE, **verified causal** |
| HVN/LVN **counts** | AVAILABLE |
| **HVN/LVN price locations** | **NOT AVAILABLE** |
| per-price footprint ladder | **NOT AVAILABLE** (`MODE1_SUMMARY`) |
| DOM/depth | **NOT AVAILABLE** |
| VWAP | **NOT AVAILABLE** |
| 3m/15m swings, prior-day H/L, FVG | DERIVED CAUSALLY |

Profile causality was verified, not assumed: 23 distinct POC values within
a single day, value-area width expanding intraday and resetting at the
session boundary.

**RED-H1 consequence:** discrete HVN prices do not exist in the capture,
so the strict HVN form is **INSUFFICIENT DATA**. The rule's alternative
wording ("high-volume-value area") was run as an explicitly labelled
**value-edge translation (RED-H1/VE)** using VAL/VAH. POC was not
substituted.

## 2. Causality audit

Every entry feature has `featureTime <= entryTime`. Swings carry the 1m
index of their confirming bar and are invisible before it. FVGs are known
only at the close of candle 3. Prior-day levels are knowable from the
following day's first bar. Forward metrics require the whole consecutive
window to exist. Entry gate: RTH, ≥60 min to the close, valid ATR.
Per-hypothesis 30-minute chronological cooldown, as in all prior work.

## 3. Event counts and frequency

| hypothesis | N | /week | /month | days | span |
|---|---|---|---|---|---|
| RED-H1/VE | 193 | 4.0 | 14.8 | 143 | 13 months |
| RED-H2 (15m) | 549 | 10.4 | 42.2 | 207 | 13 months |
| RED-H6 | 604 | 11.4 | 46.5 | 241 | 13 months |
| RED-H10 (SW3) | 54 | 1.7 | 4.5 | 49 | 12 months |

## 4. Primary results — 60-minute horizon

| hypothesis | mean | median | MFE | MAE | **MFE/MAE** | **fav-first** | wk+ | mo+ |
|---|---|---|---|---|---|---|---|---|
| RED-H1/VE | −3.65 | −10.62 | 2.60 | 2.85 | **0.91** | **50.5%** | 35.4% | 30.8% |
| RED-H2 (15m) | −0.61 | −1.87 | 2.83 | 2.92 | **0.97** | **52.0%** | 49.1% | 38.5% |
| RED-H6 | −5.59 | −11.37 | 2.60 | 2.94 | **0.89** | **47.9%** | 41.5% | 30.8% |
| RED-H10 (SW3) | −10.09 | +4.88 | 3.08 | 2.60 | **1.18** | **39.6%** | 56.2% | 50.0% |

MFE and MAE are medians in ATR units. Favourable-first is at ±1 ATR with
AMBIGUOUS excluded from the ratio and reported separately.

## 5. Partition consistency (U / DEV / IR)

| hypothesis | U | DEV | IR |
|---|---|---|---|
| RED-H1/VE | −2.45 | −6.83 | −1.26 |
| RED-H2 (15m) | −10.63 | +1.66 | +2.44 |
| RED-H6 | −18.97 | −6.04 | +0.87 |
| RED-H10 (SW3) | **+27.63** | **+6.32** | **−42.14** |

RED-H10 reverses sign between DEV and IR, with MFE/MAE falling 2.25 → 0.57
and favourable-first 43.8% → 29.2%. That is a **failed internal
replication**, and it is exactly the pattern that would have looked like a
discovery had only DEV been examined.

## 6. Long / short separation

| hypothesis | LONG mean (n) | SHORT mean (n) |
|---|---|---|
| RED-H1/VE | −12.50 (89) | +3.92 (104) |
| RED-H2 (15m) | −1.08 (366) | +0.35 (183) |
| RED-H6 | −2.03 (278) | −8.63 (326) |
| RED-H10 (SW3) | −10.95 (28) | −9.16 (26) |

No hypothesis is positive in both directions. Where one side is positive
it is small and paired with a clearly negative other side.

## 7. MFE/MAE across horizons — the recurring signature

Medians in ATR units, favourable/adverse:

| hypothesis | 5m | 10m | 15m | 30m | 60m |
|---|---|---|---|---|---|
| RED-H1/VE | 1.03 | 0.93 | 0.92 | 0.84 | 0.91 |
| RED-H2 | 1.09 | 1.00 | 0.99 | 0.94 | 0.97 |
| RED-H6 | 0.96 | 0.89 | 0.92 | 0.87 | 0.89 |
| RED-H10 | 0.85 | 1.01 | 0.97 | 0.84 | 1.18 |

**MFE ≈ MAE at every horizon** — the same finding this programme has now
reached repeatedly. None of these entries sit at a location where the
favourable excursion systematically exceeds the adverse one.

## 8. Favourable-first (AMBIGUOUS never assigned)

| hypothesis | ±0.25 | ±0.5 | ±1 | +1.5/−1 | +2/−1 |
|---|---|---|---|---|---|
| RED-H1/VE | 45.8% | 46.2% | 50.5% | 41.1% | 31.4% |
| RED-H2 | 50.6% | 49.4% | 52.0% | 37.8% | 29.9% |
| RED-H6 | 50.2% | 48.9% | 47.9% | 39.3% | 33.7% |
| RED-H10 | 45.2% | 38.5% | 39.6% | 38.9% | 25.9% |

Every value sits at or below the coin-flip line except RED-H2's marginal
52.0%, which its own matched control matches to within 1.4 pp.

## 9. Matched controls (time of day, ATR quintile, direction, partition)

| hypothesis | ΔMFE/MAE | Δfav-first | Δmean |
|---|---|---|---|
| RED-H1/VE | −0.041 | +0.3 pp | +1.58 pt |
| RED-H2 (15m) | −0.010 | +1.4 pp | −0.45 pt |
| RED-H6 | −0.131 | −1.8 pp | −4.57 pt |
| RED-H10 (SW3) | +0.172 | **−15.1 pp** | −7.56 pt |

Not one hypothesis beats a matched random entry of the same direction, in
the same hour, at the same volatility. RED-H10's higher MFE/MAE comes with
a 15-point *deficit* in ordering — larger favourable excursions that
arrive after the adverse one.

## 10. Controls and ablations — what each mechanism contributed

**RED-H1/VE** — the location control is decisive:

| arm | n | mean | MFE/MAE | fav-first |
|---|---|---|---|---|
| value-edge touch only | 2091 | −1.80 | 0.95 | 51.0% |
| + aggression | 1742 | −1.88 | 1.00 | 49.6% |
| + failure | 328 | −5.05 | 1.00 | 53.6% |
| FULL (+ reclaim) | 193 | −3.65 | 0.91 | 50.5% |
| **same failure AWAY from value** | 522 | **+9.38** | 1.04 | 50.3% |

Failed aggression *away* from the value edge outperformed the same
mechanism *at* it. The value-edge location contributes **negative**
value — the opposite of the hypothesis. (The AWAY arm's own geometry is
still flat: R 1.04, ordering 50.3%. It is drift, not an edge, and it is a
control — it is **not** promoted to a candidate.)

**RED-H2** — CVD adds nothing:

| arm | n | mean | MFE/MAE | fav-first |
|---|---|---|---|---|
| plain CVD divergence | 1132 | +0.07 | 1.10 | 51.8% |
| extreme + CVD | 1340 | −0.72 | 0.96 | 50.0% |
| extreme + confirmation, no CVD | 864 | −2.24 | 0.96 | 51.4% |
| FULL | 549 | −0.61 | 0.97 | 52.0% |

The *simplest* arm is the best one. Adding the causal extreme, then the
confirmation, then both, monotonically degrades geometry. This directly
answers the pre-registered question: CVD adds nothing beyond location and
structure — and location and structure add nothing either.

**RED-H6** — delta alignment adds nothing over the breakout:

| arm | n | mean | MFE/MAE | fav-first |
|---|---|---|---|---|
| compression breakout alone | 1808 | −3.46 | 0.94 | 48.0% |
| delta alignment, no compression | 1874 | −4.14 | 0.93 | 47.2% |
| compression + delta, breakout **against** delta | 481 | −2.82 | 0.99 | 47.7% |
| FULL (aligned) | 604 | −5.59 | 0.89 | 47.9% |

The aligned rule is the *worst* of the four, and breaking **opposite** to
the delta was no worse than breaking with it. Delta supplies no
directional information that price momentum does not already carry.

**RED-H10** — the mandatory ablation:

| arm | n | mean | MFE/MAE | fav-first |
|---|---|---|---|---|
| A FVG only | 2478 | +0.77 | 0.98 | 49.3% |
| B FVG + location (SW3) | 1508 | −0.31 | 0.99 | 49.5% |
| **C FVG + failed aggression (no location)** | **203** | **+6.57** | **1.23** | 49.5% |
| D location + failed aggression, no FVG | 328 | +1.83 | 0.96 | 48.2% |
| E FULL | 54 | −10.09 | 1.18 | 39.6% |

Location by every family (3m, 15m, prior-day, value edge) collapsed the
sample and the result: E gives n = 54 / 54 / 15 / 8 with means −10.09 /
−8.25 / +7.26 / −13.62. **The contextual location is what breaks this
hypothesis.**

Arm C — FVG plus failed aggression, *without* any location filter — is the
one arm with materially MFE > MAE (1.23). Its ordering is still 49.5%, so
the asymmetry is in *magnitude*, not *direction* — the same "order flow
predicts size, not sign" result this programme has now found four times.
**C is an ablation arm, not a hypothesis.** Promoting it would be creating
RED-H11 after seeing results, which the directive forbids and which would
forfeit any claim to pre-registration. It is recorded here as a component
finding requiring its own future pre-registered, prospective test.

## 11. Effort-vs-result diagnostics

DEV distributions of the three formulations:

| form | q25 | median | q75 (frozen cut) | q90 |
|---|---|---|---|---|
| E1 native volume/tick | 15.93 | 36.51 | 106.00 | 330.00 |
| **E2 PRIMARY** | 1.79 | 3.57 | **15.96** | 518518 |
| E3 range-based | 0.87 | 1.63 | 2.73 | 4.38 |

E2's upper tail is degenerate by construction: a bar with *zero* adverse
tick progress divides by epsilon. That is semantically correct — maximum
effort, no result — but it means the q75 cut admits the whole
zero-progress mass. Disclosed rather than patched, since the cut was
frozen before results.

**Robustness — the null does not depend on the choice:**

| form | RED-H1 | RED-H10 |
|---|---|---|
| E1 | n 392, −1.83, R 0.88, ff 50.8% | n 109, −9.48, R 1.08, ff 53.3% |
| E2 | n 193, −3.65, R 0.91, ff 50.5% | n 54, −10.09, R 1.18, ff 39.6% |
| E3 | n 693, −1.97, R 0.95, ff 49.7% | n 293, −0.76, R 1.09, ff 48.4% |

All three agree: negative mean, MFE/MAE ≈ 1, ordering ≈ coin flip.

## 12. Significance, with M = 4

| hypothesis | sign-flip-by-day p | day-clustered 95% CI on mean | BH q |
|---|---|---|---|
| RED-H1/VE | 0.6657 | [−18.59, +11.20] | 0.8951 |
| RED-H2 (15m) | 0.4673 | [−8.77, +7.50] | 0.8951 |
| RED-H6 | 0.8951 | [−12.97, +1.40] | 0.8951 |
| RED-H10 (SW3) | 0.7251 | [−40.22, +20.25] | 0.8951 |

Every confidence interval spans zero. Nothing is close to significant
before correction, let alone after.

## 13. Cost sensitivity

All four are negative at the base 0.87 pt assumption, so +1 and +2 ticks
of adverse round-trip only deepen the loss (e.g. RED-H6: −5.59 → −5.84 →
−6.09). No candidate is economically meaningful at any cost level.

## 14. Stop and R:R research — NOT RUN

The pre-registered gate: stop research proceeds only if raw geometry shows
credible improvement in MFE/MAE, favourable-first, or MAE reduction versus
matched control. **No hypothesis met it** — every one is within noise of
its control or worse. Per the directive, none was rescued with management,
and no R:R grid was run.

## 15. Ranking

Ranked on the pre-declared criteria (geometry first, points last):

1. **RED-H2** — least bad. Geometry closest to neutral (R 0.97, ordering
   52.0%), highest frequency, DEV and IR both mildly positive. But its
   own simplest control beats it and its control advantage is +1.4 pp.
2. **RED-H1/VE** — flat geometry, matched-control advantage ≈ 0, and the
   location it is built on is refuted by its own AWAY control.
3. **RED-H6** — worse than matched control on every axis; opposite-delta
   breakouts did as well as aligned ones.
4. **RED-H10 (SW3)** — best-looking MFE/MAE and the worst ordering
   (−15.1 pp vs control), tiny N, and a clean DEV→IR sign reversal.

## 16. Final verdicts

| hypothesis | verdict |
|---|---|
| **RED-H1** (strict HVN form) | **INSUFFICIENT DATA** — HVN price locations are not stored |
| **RED-H1/VE** (value-edge translation) | **NO INCREMENTAL VALUE** — indistinguishable from matched control; the value-edge location contributes negatively |
| **RED-H2** | **NO INCREMENTAL VALUE** — CVD, causal extreme and confirmation each degrade a simpler control |
| **RED-H6** | **POOR ENTRY GEOMETRY** — below control on MFE/MAE, ordering and mean; delta alignment adds nothing to a breakout |
| **RED-H10** | **FAILED INTERNAL REPLICATION** — DEV +6.32 → IR −42.14, ordering 39.6%, N = 54 |

### DID ANY REDDIT-INSPIRED ORDER-FLOW MECHANISM SHOW EVIDENCE OF A REPEATABLE NQ ENTRY LOCATION ADVANTAGE?

**NO.**

Not one of the four produced entry asymmetry. MFE ≈ MAE at every horizon
for every hypothesis; favourable-first sat at or below 50% almost
everywhere; no matched-control advantage existed anywhere; every
confidence interval spanned zero; and BH q was 0.895 across the family.

The ablations were more informative than the headline numbers, and they
point the same way three earlier passes did: **the location concepts
(HVN/value edge, structural extremes, prior-day levels) contributed
nothing or actively hurt, while the one arm with any magnitude asymmetry
(FVG + failed aggression, no location) still had coin-flip ordering.**
Order flow continues to say something about *how far*, and nothing
reliable about *which way*.

This does not touch OFH13, which remains the only candidate in this
programme with unseen-window evidence, and remains under prospective test.
