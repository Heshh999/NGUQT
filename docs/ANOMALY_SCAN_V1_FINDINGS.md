# ANOMALY-SCAN-V1 — FINDINGS (DISCOVERY WINDOW ONLY)

**Everything here is EXPLORATORY / HYPOTHESIS-GENERATING**, computed
solely on the frozen discovery window (≤ 2023-12-31; 1,572,786
contiguous 1m log returns). The holdout (≥ 2024-01-01) was not examined.
Protocol frozen first at commit `9f71b24` (sha256 `179af253…47ea67`).
Raw output: `analysis/anomaly/SCAN_OUTPUT.txt`.

Per protocol, at most TWO candidates may be recommended for a
pre-registered holdout confirmation. They are §A and §B below.

---

## A. THE HEADLINE ANOMALY — RVMR flips the sign of serial correlation

| slice | n (1m rets) | AC1 (1m) | AC1 (15m) |
|---|---|---|---|
| RVMR RANGE **LOW** | 1,187,450 | **−0.0280** | +0.0023 |
| RVMR RANGE MEDIUM | 288,214 | +0.0166 | −0.0050 |
| RVMR RANGE **HIGH** | 95,744 | **+0.0239** | **−0.0321** (n 5,326 blocks) |
| pooled | 1,572,786 | +0.0085 | +0.0219 |

The pooled numbers are a blend that hides a **sign flip**: quiet regimes
mean-revert bar-to-bar (classic bid-ask-bounce/noise structure), active
regimes exhibit bar-to-bar persistence (order-flow splitting), and at
the 15m scale the pattern **inverts** — HIGH-state 15m moves partially
revert. The S1 variance-ratio gradient agrees (VR(15): LOW 0.978 →
HIGH 1.005), and the S7 entropy deficits agree (LOW 0.0056 bits vs
MEDIUM 0.0008). Three independent statistics, one coherent structure.

This is the first evidence in ~120 studies that RVMR **modulates market
structure** rather than merely scaling it. Honesty: the naive s.e. is
~0.001–0.003 per slice, but minutes cluster within days; the effect
spread (~0.05 in AC units) is far beyond plausible clustering inflation,
yet formal day-clustered confirmation is exactly what the holdout study
is for. Economic candor: at 1m, the predictable component (~0.2 pt) is
~4× below the 0.87 pt round-turn cost — this is **structure, not a
strategy**. The 15m HIGH-state reversion is the only slice with a
conceivable economic use, and its n is small.

## B. THE SECOND CANDIDATE — the Monday effect

Exchange-day returns by weekday (day-clustered CIs):

| day | n | mean | 95% CI |
|---|---|---|---|
| **Mon** | 234 | **+22.08 bp** | [+7.52, +35.73] — excludes 0 |
| Tue–Sun | 1,164 | −2.9 to +4.3 bp | all include 0 |

One of six weekday cells excludes zero, but it does so by a wide margin
and is economically sized (~+11%/yr accrued on Mondays alone in the
window). Classic Simons-class calendar anomaly; notoriously unstable
out-of-sample, which is precisely what the untouched holdout will test.

## C. Real but sub-cost — the half-hour-mark drift (recorded, not recommended)

Minute-of-half-hour signed drift (RTH): offsets **0 and +1** after each
:00/:30 mark are positive with CIs excluding zero (+0.127 / +0.143 bp);
offsets 4–5 are negative (−0.082 / −0.081 bp). Five of thirty offsets
exclude zero and they cluster exactly at the round marks — mechanistically
coherent (TWAP/hedge flows), genuinely anomalous, and at ~0.2 pt per
event roughly 4× below cost. **Microstructure knowledge, not a trade.**

## D. Nulls and refutations worth keeping

- **The famous "overnight drift" does NOT hold for NQ here:** total
  overnight accrual +16.9% vs RTH +41.8% over the window, and 2023 was
  overnight −0.7% / RTH +28.1%. A popular anomaly claim, refuted on this
  market and window.
- **Clock-hour drift:** only hours 0 and 14 ET exclude zero (2 of 24 —
  barely above the ~1.2 expected by chance). Weak.
- **Turn-of-month: null** (+4.92 vs +4.90 bp).
- **OU half-life of (close − VWAP): median 106 min**, quartiles 53–286 —
  and **RVMR does not modulate it** (112/105/103 by tercile). This also
  explains, in one number, why every VWAP-reversion strategy at ≤60m
  horizons failed: the reversion clock is slower than the frames tested.
- **Hill tail index ~2.54 pooled** (heavy tails, 3rd/4th moments
  unreliable — a standing warning for every mean-based statistic). The
  by-state pattern (LOW 2.56 / MED 3.09 / HIGH 2.72) is non-monotone on
  small k and is not a lead.
- **Variance ratios:** only VR(2) = 1.0095 rejects the random walk —
  a ~1% effect. NQ at 1m is, to first order, a martingale; whatever
  exists lives in the conditional slices, not the pooled series.

## Recommendation

Pre-register **ANOMALY-CONFIRM-V1** on the untouched holdout
(2024-01-01 → 2026-08-17) with exactly two hypotheses, frozen thresholds,
day-clustered inference, M = 2:

1. **AC-FLIP:** AC1(1m | LOW) < 0 < AC1(1m | HIGH), and secondarily
   AC1(15m | HIGH) < 0, using the frozen RVMR states unchanged.
2. **MONDAY:** mean Monday exchange-day return > 0 with day-clustered CI
   excluding 0.

Even full confirmation yields HISTORICAL evidence — structure first,
any trading application later and separately. Nothing frozen was
touched; no rule was created; RVMR remains magnitude-plus-structure
context only.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

# WAVE 2 FINDINGS (discovery window only; menu frozen at `c4c4d82`)

## E. THE ECONOMIC HEADLINE — shock continuation, gated by RVMR MEDIUM

S9 forward-15m return by decile of the prior non-overlapping 15m return:

| decile | prior move | fwd15 | CI |
|---|---|---|---|
| 0 (big down) | −22.6 bp | −0.333 bp | [−0.699, +0.064] |
| 7 | +4.5 bp | **+0.242 bp** | [+0.051, +0.429] — excludes 0 |
| 9 (big up) | +21.8 bp | **+0.451 bp** | [+0.036, +0.861] — excludes 0 |

**By RVMR state, the effect concentrates in MEDIUM and is signed
continuation on BOTH tails:** dec 9 MEDIUM **+0.975 bp** CI [+0.259,
+1.717]; dec 0 MEDIUM **−0.722 bp** CI [−1.382, −0.017]. LOW shows
nothing; HIGH is positive but wide. A ~1 bp/15m conditional edge is
~1.5–2.5 NQ points — the first scan-level effect of the same order as
the 0.87 pt cost. It is also mutually consistent with Wave 1: pooled
15m AC1 +0.022 (continuation) coexisting with HIGH-state 15m AC1 −0.032
(reversion) resolves into a **regime ladder: LOW inert, MEDIUM
continues, HIGH reverts.**

## F. The leverage V-curve — RVMR arrival is forecastable

S19: P(reaching RANGE-HIGH within 30m | prior 15m return decile):

```
dec:  0     1     2     3     4     5     6     7     8     9
P： 0.640 0.426 0.323 0.261 0.237 0.247 0.274 0.317 0.387 0.556
```

A clean V with **down-shock asymmetry** (0.640 vs 0.556 at symmetric
extremes) — the intraday leverage effect, expressed directly in RVMR's
own state space. The state RVMR-BANDS could not calibrate in points is
nonetheless **predictable as an event**. Dwell times (median 1–2 min,
p90 3–18) show the bucket sequence flickers even though the score
persists — any future state-machine use needs debouncing.

## G. Wave-2 corroborations and structure

- **CLV flip (S11)** — corr(close-location, next return): LOW −0.0070 /
  MEDIUM +0.0088 / HIGH +0.0141. A third independent statistic showing
  the LOW-vs-active sign flip of Wave 1's AC-FLIP.
- **Down-impact asymmetry (S10):** λ(down)/λ(up) = 1.02–1.04 in every
  state — down moves consume ~2–4% more price per unit volume. Small,
  consistent, correct sign for the leverage story.
- **News-minute map (S14):** |r| spikes at **08:31 (3.22×)** [08:30
  releases], **15:51 (2.09×)** [MOC imbalance], 02:01, 07:01, 16:00–01,
  10:01, 14:01, 20:01 — and **09:30 is 0.42×** (the quiet last
  pre-open minute). Execution/risk knowledge.
- **Clock harmonics (S22):** top periods ~92 min and ~30 min — the 30-min
  line matching Wave 1's half-hour-mark drift.
- **Vol long memory (S13):** ACF|r| never falls below 0.05 within 1,440
  lags (slope −0.161); the lag-1440 bump is the daily seasonal. RVMR's
  window sits *inside* the market's memory — its persistence is real.
- **MONDAY sharpened (S22):** the entire effect is **Monday RTH +16.63
  bp CI [+5.82, +27.21]**; Sunday and Monday overnight are null.

## H. Wave-2 nulls

Open-gap response curve: **flat** — all ten deciles include 0,
consistent with every prior gap-strategy failure. Parkinson/CC = 1.0006
CI [0.9948, 1.0057] — range geometry is exactly GBM-consistent (also a
data-sanity pass).

## FINAL COMBINED RECOMMENDATION (declared before any holdout contact)

Per the frozen two-candidate cap, the confirmation study
**ANOMALY-CONFIRM-V1** shall test on the untouched holdout, M = 2:

1. **SHOCK-CONT-MEDIUM** — in RVMR RANGE-MEDIUM, fwd15 after a
   top-decile prior 15m move continues (dec9 − dec0 delta > 0, both
   tails' signs as found), day-clustered CI excluding 0, using
   discovery-frozen decile cutpoints. *Declared non-promotable
   secondaries inside the same study:* the 1m AC-FLIP, the CLV flip,
   and the leverage V-curve — reported, never promoted.
2. **MONDAY-RTH** — mean Monday RTH accrual > 0, day-clustered CI
   excluding 0.

This supersedes the Wave-1 pick of raw AC-FLIP as primary (it becomes a
secondary), declared here while the holdout remains untouched, as the
frozen protocol permits.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

# WAVE 3 FINDINGS (discovery window only; menu frozen at `b054a00`)

Direction/trend machinery, seed 20260826, discovery ≤ 2023-12-31 only.
The RVMR-MOMENTUM-V1 exclusion zone was respected: no frozen momentum
object was computed. Raw output: `analysis/anomaly/SCAN3_OUTPUT.txt`.

## I. THE STRUCTURAL HEADLINE — continuation information DECAYS WITH RUN AGE

S23 run hazard h(k) = P(a directional run survives its k-th minute):

| k | pooled | LOW | MEDIUM | HIGH |
|---|---|---|---|---|
| 1 | 0.4966 | 0.4940 | 0.5025 | **0.5106** |
| 3 | 0.4761 | 0.4751 | 0.4779 | 0.4807 |
| 5 | 0.4638 | 0.4591 | 0.4700 | 0.4826 |
| 9+ | 0.4447 | 0.4490 | 0.4542 | **0.4054** |

**The hazard declines monotonically everywhere** — the older a
directional run, the more likely it dies. Headline h(3+) − h(1) =
**−0.0264**, CI [−0.0285, −0.0242], p 0.0002; and the decay is
*steepest in HIGH* (−0.0375). So the replicated memory effect is
**run-age-local**: HIGH's continuation edge exists at k = 1–2 and is
gone by k = 3; nine-minute-old runs in HIGH break hard (0.405). A
~5 pp hazard range across k dwarfs the ~3 pp lag-1 state effect.
Mechanistically this is why every multi-minute trend construction has
struggled: whatever persistence exists is spent within two minutes.

## J. THE SHARPEST CELL YET — ordinal V-TURN continuation, state-amplified

S24, mean next-1m return (bp) by close-ordinal motif and state
(012 = two up-legs, 210 = two down-legs, 102 = down-then-up-beyond,
201 = up-then-down-below):

| motif | pooled | LOW | MEDIUM | HIGH |
|---|---|---|---|---|
| 012 (up-up) | −0.0137 | −0.0190 | −0.0184 | +0.0607 |
| **102 (V-up)** | **+0.0616** | +0.0298 | +0.1066 | **+0.1877** |
| 120 | +0.0396 | +0.0287 | +0.0739 | +0.1116 |
| 021 | −0.0400 | −0.0234 | −0.0978 | −0.1700 |
| **201 (V-down)** | **−0.0534** | −0.0129 | −0.0889 | **−0.2623** |
| 210 (down-down) | +0.0297 | +0.0385 | +0.0164 | −0.0140 |

Headline (frozen): ascending − descending = **−0.0435 bp**,
CI [−0.0591, −0.0275], p 0.0002 — two-leg runs *reverse* (the run-age
story again). The new content is at **fixed last leg**: a fresh V-turn
(102/201) continues in its new direction ~4× more strongly than a
second consecutive leg, and the effect is amplified ×3–5 in HIGH
(102-HIGH +0.19 bp, 201-HIGH −0.26 bp per minute — the largest 1m
directional conditioning this programme has measured). This is genuine
beyond-lag-1 structure: within last-leg-up motifs, only the V-shaped
one carries the signal.

**Menu defect disclosed:** the frozen menu said "frequencies vs 1/6" —
the correct null for sign-driven motifs of a symmetric random walk is
1/4 (monotone) and 1/8 (mixed); observed 0.256/0.249 and ~0.12 sit near
that null, so there is NO frequency anomaly. The information is in the
conditional means, not the frequencies. The wrong stated baseline
affected no computation.

## K. THE ECONOMIC LEAD — half-session persistence in QUIET regimes

S30: aligned afternoon accrual = sign(09:31–12:00) × (12:01–16:00):

| slice | n days | aligned (bp) | P(match) |
|---|---|---|---|
| pooled | 1,120 | +3.69, CI [−0.44, +7.60] | 0.5661 |
| **noon RB = LOW** | **591** | **+8.32** | **0.6007** |
| noon RB = MEDIUM | 461 | +0.79 | 0.5401 |
| noon RB = HIGH | 67 | −16.54 | 0.4478 |

When the noon RVMR state is LOW, the morning trend persists into the
afternoon at ~+8.3 bp (~13 NQ points at discovery prices — an order of
magnitude above the 0.87-pt cost) with a 60% sign match over 591 days.
**Scale inversion:** at 1m LOW means reversal; at the half-session
scale LOW means persistence — quiet markets drift, active ones chop.
Honesty first: the pooled headline **missed** significance and this is
one cell of the frozen three-cell slice — the classic
subgroup-of-a-null trap — so it is a *lead requiring confirmation*, not
a finding. It is, however, the only Wave-3 object of tradeable
magnitude, it lives at the multi-hour horizon the OU half-life (106
min) has pointed at all along, and its 2024+ exposure is clean per the
frozen ledger.

## L. Texture (recorded, NOT promoted — none was a frozen headline)

- S26 bins: a *very fresh* 4h-high (≤29 min old) is followed by −0.77 bp
  in 30m while a 30–90-min-old high gives +0.44 — fresh extremes
  reverse, aged extremes drift. The frozen fresh-high−fresh-low headline
  is null (−0.10, p 0.59), so this stays texture.
- S29 L=1: yesterday's sign *reverses* at −4.84 bp/day (CI just includes
  0), concentrated in MID/HIGH-score days, with P(match) exactly 0.50 —
  a magnitude effect (big days mean-revert), not a sign effect.
- S26 a=0 (one bar is both 4h-high and 4h-low): n=410, +15.5 bp — a
  curiosity, nothing more.

## M. Nulls and refutations worth keeping

- **Donchian range position (S25): no breakout information.** The
  response curve is flat drift (~+0.2 bp everywhere); closing at the top
  or bottom of the 60m range says nothing about the next 30m, in any
  state.
- **VWAP-side occupancy (S27): null** (+0.14 bp, p 0.74). Being
  entirely above VWAP for an hour predicts nothing at 60m — consistent
  with the 106-min reversion clock being slower still.
- **OBV/volume divergence (S28): null** (+0.02 bp, p 0.91), and the
  cells lean *against* the classic story (diverging up-moves continued
  slightly more). Volume confirmation, as retail charting uses it,
  carries no directional information here.
- **Daily TSMOM (S29): 0 of 3 lags significant.** No daily-scale
  momentum in NQ 2019–2023.

## WAVE-3 RECOMMENDATION (declared before any holdout contact)

Under the frozen two-candidate cap for this wave, the candidates for a
future preregistered confirmation study (which would occupy cumulative
promotable slots 7 and 8, per the never-shrink clause) are:

1. **ORDINAL-V-TURN** — the fixed-last-leg cross-motif contrast
   (102 vs 012 within last-leg-up; 201 vs 210 within last-leg-down),
   state-amplified in HIGH. 2024+ exposure: clean beyond the lag-1
   marginal.
2. **HALF-SESSION-LOW** — morning-trend persistence into the afternoon
   conditional on noon RB = LOW. 2024+ exposure: clean. Carried
   *explicitly* as a subgroup-of-a-null lead whose confirmation gate
   must be written on the LOW cell alone, in advance.

S23's run-age hazard decline is established structure and travels as a
non-promotable diagnostic with either candidate. Nothing here touches
RVMR-MOMENTUM-V1, whose frozen objects remain uncomputed and whose
execution remains available and independent.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
