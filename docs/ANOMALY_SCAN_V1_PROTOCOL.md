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

---

# WAVE 2 ADDENDUM (frozen BEFORE any Wave-2 statistic is computed)

Same discovery window (≤ 2023-12-31), same holdout rule, same
day-clustered machinery, seed 20260825. Eight further statistics, fixed
now — no post-hoc additions:

| # | statistic | mathematical object | RVMR interaction asked |
|---|---|---|---|
| S9 | Shock-response curve: forward 15m/30m return by decile of the prior non-overlapping 15m return | conditional drift after large deviations | response curve by RANGE state |
| S10 | Asymmetric price impact: mean \|r\|/volume for up-bars vs down-bars | Amihud/Kyle-lambda direction asymmetry | by state and ToD |
| S11 | Parkinson vs close-close variance ratio per day; close-location value CLV = (2c−h−l)/(h−l) and corr(CLV_t, r_{t+1}) | range-interior geometry | CLV predictivity by state |
| S12 | Open-gap response: ln(09:30 open / prior 16:00 close) deciles → same-day RTH open-to-close return (lineage note: gap *strategies* tested before; the response *curve* was never mapped) | overnight-inventory response function | — |
| S13 | ACF of \|r\| at lags 1..1440; log-log decay slope; memory length where ACF < 0.05 | long-memory of volatility; checks RVMR's 1440-bar window against the market's actual memory | direct RVMR-design diagnostic |
| S14 | Minute-of-day \|r\| seasonal curve; minutes deviating > 30% from the ±10-minute local median | vol-seasonality spikes (news minutes, MOC) | — |
| S19 | RVMR state transition matrix, dwell-time distribution and hazard; P(→HIGH within 30m) by signed prior 15m return decile (leverage asymmetry) | the state process ITSELF as the object | native |
| S22 | DFT periodogram of the mean-signed-return-by-minute-of-day vector (top-5 periods); MONDAY decomposition into Sunday-overnight / Monday-overnight / Monday-RTH accrual | clock harmonics; sharpening the Wave-1 Monday lead before its confirmation is registered | — |

Outputs remain EXPLORATORY. The two-candidate cap for holdout
confirmation applies to the COMBINED waves: the final recommendation
after Wave 2 may still name at most TWO hypotheses (which may replace
Wave-1 picks only by being declared before any holdout contact).
