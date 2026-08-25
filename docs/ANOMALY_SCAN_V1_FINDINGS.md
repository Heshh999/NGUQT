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
