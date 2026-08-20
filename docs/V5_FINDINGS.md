# V5 FINDINGS OF RECORD

Frozen 2026-08-20. Companions: `V5_PREREGISTRATION.md` (frozen before any
feature->outcome relationship was examined) and `V5_PHASE0_AUDIT.md`.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

---

## FINAL DECISION: D - NO ROBUST EDGE SURVIVED

**0 of 10 pre-registered hypotheses survived**, on the same rule V4 used plus two
stricter conditions. One hypothesis cleared Benjamini-Hochberg and cleared it in the
**wrong direction** - the same shape as V4's H7.

One exploratory lead is documented at the end. It is not a decision and not a
trading recommendation.

---

## 1. THE COMPLETE FAMILY

Reported complete - the failures in the same table as the one that cleared.
BH at q = 0.05 across all 10.

| id | hypothesis | pred | effect | t | p | BH crit | BH sig | dir OK |
|---|---|---|---|---|---|---|---|---|
| **H6** | Monday RTH minus other RTH | − | **+30.0520** | **+3.09** | 0.00199 | 0.00500 | **YES** | **NO** |
| H4 | corr(overnight, 09:30-10:00) | − | −0.0985 | −2.44 | 0.01460 | 0.01000 | no | yes |
| H9 | imbalance top minus bottom decile | + | −0.9258 | −0.91 | 0.36129 | 0.01500 | no | NO |
| H2 | RTH mean <= 0 | − | +3.3441 | +0.78 | 0.43512 | 0.02000 | no | NO |
| H10 | close far above POC | − | +0.6142 | +0.74 | 0.46107 | 0.02500 | no | NO |
| H1 | overnight > 0 AND > RTH | + | +3.6038 | +0.67 | 0.50502 | 0.03000 | no | yes |
| H3 | turn-of-month minus rest | + | +5.4922 | +0.44 | 0.66269 | 0.03500 | no | yes |
| H8 | 20-bar high on negative cum-delta | − | −0.0350 | −0.03 | 0.97562 | 0.04000 | no | yes |
| H7 | top-decile barDelta | + | −0.0210 | −0.02 | 0.98158 | 0.04500 | no | NO |
| H5 | 15:30-16:00 mean | + | +0.0075 | +0.01 | 0.99506 | 0.05000 | no | yes |

**BH-significant: 1 of 10. BH-significant AND in the predicted direction: 0 of 10.**

H1 was declared as a conjunction and is evaluated as an intersection-union test, so
its p-value is the larger of its two components. Component (a), overnight mean > 0,
gives +6.95 pt at t = 2.07. Component (b), overnight > RTH, binds at t = 0.67.

---

## 2. WHY THE TWO NEAR-MISSES ARE NOT EDGES

### H1 - the overnight drift is a longer window, not an anomaly

Overnight captures 12,736 of the 18,865 points the index travelled - **67.5%** -
which is the shape of the documented equity-index overnight anomaly. Per unit of
exposure it inverts:

| window | hours | mean pt | **pt per hour** |
|---|---|---|---|
| overnight (16:00 -> 09:29) | 17.5 | +6.948 | **+0.3970** |
| RTH (09:30 -> 16:00) | 6.5 | +3.344 | **+0.5145** |

RTH drifts **faster** per hour. The entire overnight advantage is that the window is
2.7x longer, in a market that rose 2.7x over the sample. That is beta. This is
exactly why H1 was pre-registered as a conjunction requiring overnight to *beat* RTH
rather than merely to be positive - and that component fails.

### H4 - a significant correlation worth nothing

r = −0.0985 at **t = −2.44**, in the predicted direction. It explains **0.97%** of
the variance of the 09:30-10:00 move. Traded as a rule - fade the overnight move
from the 09:29 close to 10:00:

| | |
|---|---|
| gross | +1.5046 pt/day (t = 0.81) |
| **net of the 1.5 pt assumed cost** | **+0.0046 pt/day** |
| by split | DEV +0.138, VAL −1.218, LOCKBOX +1.229 |

Two percent of one tick, with splits that disagree on the sign. A real correlation
and a zero P&L: statistical significance and economic significance are different
claims, and only the second one is tradeable.

---

## 3. P2 CONTROLS - THE EXIT WAS NEVER THE PROBLEM

P2 existed to close a door: *were V4's fixed 1R/2R exits what killed it?* Validity
filter as pre-declared (R >= 1.0 pt, R <= 10 x ATR): 2,335,190 of 2,503,622 bars
(93.27%) valid.

### C1 - the bracket is the result

When one bar's low reaches the stop and its high reaches the target, OHLC cannot say
which came first. Both conventions were run:

| convention | P(+1R before −1R) | 95% CI |
|---|---|---|
| stop-first (pessimistic) | 0.4869 | ±0.0006 |
| target-first (optimistic) | 0.5290 | ±0.0006 |

**0.50 lies inside the bracket.** Each point estimate on its own would read as
overwhelmingly significant on 2.28M resolved races - the modelling ambiguity is
about **50x** the statistical uncertainty. Reporting either number alone would have
produced a spectacular and entirely fake edge. **C1 null holds.**

### C2 - 24 exit geometries, none positive

Targets 0.5R..5R x holding caps 10..80 bars:

| | |
|---|---|
| positive **net** points | **0 of 24** |
| positive **gross** points | 12 of 24 |
| best net | −1.3187 pt (M=5.0, K=80) |
| best gross | +0.1813 pt (M=5.0, K=80) |

Best gross is +0.18 pt against a 1.5 pt cost - short by a factor of eight.
**C2 null holds.**

### C3 and C4 - both reject, both traced

The pre-registration required that a rejection is not a finding until traced to a
named mechanism. Both trace, and neither is exploitable.

**C3 rejects.** Unclamped excursions rebuilt from raw OHLC:

| K | E[MFE] | E[MAE] | difference | t | drift over window |
|---|---|---|---|---|---|
| 20 | 16.3791 | 17.0513 | **−0.6723** | −7.23 | +0.1485 |
| 80 | 33.4525 | 35.3772 | **−1.9247** | −5.38 | +0.6173 |

Adverse excursion exceeds favourable excursion *despite positive drift*. Mechanism:
negative skew - the index falls faster than it rises. Real, significant, and it works
**against** the long.

**C4 rejects.** Expectancy improves monotonically with the holding cap at M=1.0:
−0.0624 (K=10) -> −0.0485 -> −0.0234 -> −0.0082 (K=80). Mechanism: the drift term,
the same beta as H1. It never reaches positive and never covers cost.

**Conclusion: V4's fixed 1R/2R exits were not what killed it.** That door is closed.

---

## 4. P3 - ORDER FLOW IS NULL UNCONDITIONALLY TOO

279,834 volumetric bars, 2025-11-02 .. 2026-08-18, 249 session days. Forward returns
built from the file's own close series because the export carries only backward
columns; 1.47% of windows voided for crossing an exchange day.

| | gross | t | predicted |
|---|---|---|---|
| H7 top-decile barDelta | −0.0210 | −0.02 | + |
| H8 20-bar high on negative cum-delta | −0.0350 | −0.03 | − |
| H9 imbalance, top vs bottom decile | −0.9258 | −0.91 | + |
| H10 close far above POC | +0.6142 | +0.74 | − |
| *unconditional baseline* | +0.2158 | +0.59 | - |

**Max |t| = 0.91.** Every net figure is negative. V4 found order flow added nothing
*at structure breaks*; V5 finds it adds nothing *anywhere*. The null was not an
artifact of conditioning on breaks.

**Sample limitation, restated:** volumetric depth exists only from 2025-11, so all
of P3 sits inside the window V4 spent as its out-of-sample. P3 has no holdout. This
is a property of the data, not a choice.

---

## 5. EXPLORATORY - THE MONDAY RESULT

**Not part of the confirmatory family. Failed its pre-registered direction. Not
eligible to support a decision.** Recorded because it is the one live thread.

RTH return by weekday, all five shown so Monday is seen in context:

| day | n | mean pt | t | median | winsor 1% | mean bp |
|---|---|---|---|---|---|---|
| **Mon** | 368 | **+27.363** | **3.37** | +22.50 | +27.321 | +13.90 |
| Tue | 371 | +1.571 | +0.17 | +8.25 | +1.633 | −1.26 |
| Wed | 367 | +1.548 | +0.14 | +9.50 | −2.382 | +1.19 |
| Thu | 369 | −12.323 | −1.19 | +8.50 | −11.980 | −4.46 |
| Fri | 358 | −1.518 | −0.16 | +7.75 | +1.050 | −1.35 |

What survives:

- Winsorising at 1% barely moves it (27.363 -> 27.321), so tails are not driving it.
- In basis points (+13.90 vs ~−1.4) it survives the 2.44x rise in index level, so it
  is not an artifact of pooling raw points across a growing price.
- Positive in all three splits: DEV +15.39, VAL +35.45, LOCKBOX +43.15.
- Positive in 7 of 8 calendar years.
- Not weekend reversal: +29.61 after down weekends, +25.58 after up weekends.
- Monday RTH contributes **10,070 pt** against a total RTH drift of 6,130 pt across
  all 1,833 days. Every other weekday combined is **−3,940 pt**. The concentration
  is real, not long exposure spread evenly.

Why it is still not a trading conclusion:

1. **It failed the pre-registered direction.** I predicted Monday would be *weak*.
   Reinterpreting a hypothesis that came out backwards converts it from confirmatory
   to exploratory, and exploratory results are how false findings are manufactured.
2. **n = 368 days.** Small for a day-of-week claim spanning seven years.
3. **The tails are violent.** Worst day −613.25 pt, best +640.00 pt, and the
   equity curve's maximum drawdown is **1,346.5 pt** - about 52 average Mondays,
   or $2,693 on a single MNQ contract.
4. **DEV is the weakest split** (t = 1.44) and the effect *grows* monotonically into
   the present. A growing effect is as often price-level or regime drift as signal.
5. **Day-of-week effects are among the most heavily mined patterns in finance.** The
   prior that an unexploited one persists in a market as liquid as MNQ should be low.

If it is pursued, the first thing a V6 pre-registration must separate is **"Monday"
from "first trading day of the week"** - roughly 48 Mondays in this sample are
absent as market holidays, and the two hypotheses are not the same claim. That
distinction should be declared before it is tested, not chosen after seeing which
one scores better.

---

## 6. FAILURE CLASSIFICATION AND DECISION

Case A (edge exists, cost kills it) is **not** ruled out the way it was in V4, where
gross was uniformly negative. Here 12 of 24 exit geometries are gross-positive and
the Monday effect is strongly gross-positive. But every gross-positive result traces
to either beta (H1, C4, the exit grid) or to an exploratory result that failed its
predicted direction (H6). None is a confirmed edge.

**FINAL DECISION: D - NO ROBUST EDGE SURVIVED.**

Three programmes have now returned the same answer on this instrument: V3, V4
(endogenous structure, 0 of 8), and V5 (exogenous clock and calendar, path geometry,
and unconditional order flow, 0 of 10). The V5 result additionally establishes two
things V4 could not:

- **The exits were not the problem.** 24 geometries, zero positive net.
- **Order flow is null unconditionally**, not merely null at structure breaks.

---

## REPRODUCTION

`analysis/v5/` - `load.py` (bar cache), `sessions.py` (daily decomposition),
`est.py` (pooled mean, day-block bootstrap, BH), `p1.py` / `p1_stab.py` /
`p1_diag.py`, `p2.py`, `p3.py`, `family.py`, `h6.py`, and the six `audit_*.py`
scripts behind `V5_PHASE0_AUDIT.md`.

Estimator throughout: **pooled mean** as point estimate, **day-block bootstrap**
(2,000 resamples) for standard error. Never mean-of-daily-means - in V4 that
estimator produced +7.12 pt / t = +4.63 on a cell whose pooled mean was −0.36 pt.

Cost: **1.5 pt round turn, assumed, not measured.** Every result reported gross and
net. MNQ only, $2 per index point per contract.

---

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
