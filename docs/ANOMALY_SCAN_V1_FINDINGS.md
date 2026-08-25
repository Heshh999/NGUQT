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
