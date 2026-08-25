# ANOMALY-SCAN-V1 — PROTOCOL (frozen BEFORE any statistic is computed)

**Purpose.** A Renaissance-style structural anomaly scan of the NQ 1m
history using mathematical machinery this programme has never applied:
scaling laws, mean-reversion process estimation, spectral/clock
structure, information theory, and extreme-value shape — each also
sliced by the frozen RVMR states to ask whether the certified magnitude
tool *modulates* market structure.

**Status: EXPLORATORY / HYPOTHESIS-GENERATING.** Everything this scan
produces is HISTORICAL DISCOVERY. Nothing it finds is validated, and
nothing may be traded, promoted, or added to any frozen system on the
basis of this scan alone.

## The one rule that makes mining honest

```
DISCOVERY WINDOW   sessionDate <= 2023-12-31   (the ONLY data scanned)
HOLDOUT WINDOW     sessionDate >= 2024-01-01   (NOT examined by this scan)
```

Every statistic in this scan is computed on the discovery window only.
Any anomaly worth pursuing must then be **pre-registered** and confirmed
on the holdout. Honesty note, recorded now: the holdout is *not*
pristine — prior studies (XMARKET, RVMR-VALIDATION, BANDS, DIRECTION,
DVT) computed on 2024–2026 — but it is untouched **by this scan's
selection process**, which is what controls this family's selection
bias. Confirmed anomalies would still be HISTORICAL evidence requiring
prospective shadow validation.

## Frozen statistic menu (computed once; no post-hoc additions)

| # | statistic | mathematical object | RVMR interaction asked |
|---|---|---|---|
| S1 | Variance ratios VR(q), q ∈ {2,5,10,15,30,60,120} | Lo–MacKinlay random-walk deviation, non-overlapping blocks, day-clustered bootstrap | VR(15) by RANGE state: does HIGH change the scaling law? |
| S2 | Serial correlation AC(1..10) of 1m and AC(1..4) of 15m returns | autocovariance structure | AC by RANGE state — does predictability appear in HIGH? |
| S3 | Clock drift: mean signed 1m return by hour-of-day (24h) + overnight (18:00→09:30) vs RTH (09:30→16:00) accrual per year | intraday seasonal drift decomposition (documented "overnight drift" anomaly class) | — |
| S4 | Minute-of-half-hour signed drift (offset 0..29 inside each :00/:30 block, RTH) | clock-harmonic microstructure | — |
| S5 | Day-of-week and turn-of-month exchange-day returns | calendar anomalies | — |
| S6 | OU half-life of (close − session VWAP) per RTH session | AR(1) mean-reversion speed θ | half-life by day-level RANGE-score tercile |
| S7 | Sign-sequence block entropy (5-bit blocks, zeros skipped) vs 5-bit maximum | information-theoretic predictability | entropy by RANGE state and ToD |
| S8 | Hill tail index of non-overlapping |15m| moves (top 5%) | extreme-value SHAPE (does RVMR change shape or only scale?) | Hill α by RANGE state |

Machinery: log returns on `em`-contiguous minutes only (gaps skipped,
never bridged); frozen RVMR states from `rvmr_spec` unchanged; session
VWAP from the frozen `dvt_spec.SessionVwap`; day-clustered bootstrap
(5,000 iterations, seed 20260825) for every headline statistic; no ML;
no parameter sweeps — the parameter lists above are the complete set.

## What this scan may NOT do

No trading rule, no entries, no stops, no filters, no RVMR-directional
use, no modification of anything frozen, no holdout contact. The scan's
only legitimate outputs are (a) a ranked list of anomalies with effect
sizes and dependence-aware uncertainty, and (b) a recommendation of at
most TWO candidates for a pre-registered confirmation study on the
holdout.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
