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

---

# WAVE 3 ADDENDUM — DIRECTION / TREND MACHINERY
# (frozen BEFORE any Wave-3 statistic is computed)

Same discovery window (<= 2023-12-31), same holdout rule, day-clustered
machinery, **seed 20260826** for Wave 3 (new-work seed convention).
Eight further statistics, fixed now — the parameter lists below are the
COMPLETE set; no post-hoc additions, no sweeps.

## The exclusion zone (binding on this wave)

RVMR-MOMENTUM-V1 (`docs/RVMR_MOMENTUM_V1_PREREGISTRATION.md`, sha256
`210306f0…`, commit `832faa61…`) is frozen and UNEXECUTED. Its objects —
`sign(c[t]/c[t-5]-1) x (5m forward return)` and
`sign(c[t]/c[t-30]-1) x (15m forward return)`, pooled or by RVMR state,
including its declared baselines — may NOT be computed, revealed, or
reconstructed by any Wave-3 statistic. No statistic below conditions on
a trailing 5m or 30m return sign, and no statistic uses the 30m-trail /
15m-forward pairing. Where a Wave-3 object is a timeframe NEIGHBOUR of
the frozen ones (S28's 60m-trail/30m-forward), that adjacency is
declared here, in advance.

## Holdout-contamination ledger (recorded now, per statistic)

The 2024-2026 window is LESS pristine than it was for Waves 1-2:
ANOMALY-CONFIRM, MEMORY-PRED and HIGH-ARRIVAL computed on it. For any
future confirmation claim, each Wave-3 statistic carries this exposure
label, fixed in advance:

- S23 run hazard: k=1 hazard by state EXPOSED via MEMORY-PRED
  (full-window sign-continuation); k>=2 structure unexposed.
- S24 ordinal motifs: unexposed, except the last-leg marginal (== lag-1,
  exposed). The scan's headline is therefore the WITHIN-last-leg /
  cross-motif structure, not the lag-1 marginal.
- S25 range position: neighbourhood exposed via XMARKET breakout
  outcomes on 2024-2026 (different definitions); partial flag.
- S26 extreme aging: unexposed.
- S27 VWAP occupancy: strategy neighbourhood touched (RVMR-STRAT, DVT);
  the occupancy response curve itself unexposed; partial flag.
- S28 OBV-price divergence: unexposed (bar-volume flow proxy; genuine
  order-flow delta does not exist in the archive).
- S29 daily TSMOM: daily returns exposed on 2024+ only as weekday
  aggregates (MONDAY); TSMOM-conditional means unexposed; minor flag.
- S30 half-session persistence: unexposed.

## Frozen statistic menu

| # | statistic | mathematical object | RVMR interaction asked |
|---|---|---|---|
| S23 | Directional run hazard h(k) = P(run continues \| length k), k = 1..8 (k>=9 pooled), on contiguous nonzero 1m signs; zero return or minute gap TERMINATES a run; a zero next-return is NOT an opportunity. Headline contrast h(3+) - h(1), day-clustered. Also 15m-block sign runs, k = 1..4 | renewal / hazard analysis of directional runs; flat hazard = martingale | hazard curve by RB[t]; does HIGH raise the far hazard? |
| S24 | Ordinal 3-motifs of (c[t-2], c[t-1], c[t]) (Bandt-Pompe, strict inequalities, ties skipped, em-contiguity 2): motif frequencies vs 1/6; P(next 1m up \| motif); E[r_{t+1} \| motif]. Headline: E[r \| ascending] - E[r \| descending], day-clustered | ordinal-pattern statistics, invariant to monotone transforms | motif table by RB[t] |
| S25 | Range-position response: PosR = (c - min low 60) / (max high 60 - min low 60) over trailing 60 contiguous bars (incl. t) -> forward 30m return, FIXED 0.1-grid deciles (natural units, nothing fitted) | Donchian position response curve — breakout persistence vs range reversion | extreme deciles by RB[t] |
| S26 | Extreme aging: a = (bars since trailing-240m high) - (bars since trailing-240m low), ties to most recent; FIXED bins ±{1-29, 30-89, 90-179, 180-239} and {0} -> forward 30m return. Headline: E[fwd30 \| a<=-30] - E[fwd30 \| a>=+30] (fresh-high minus fresh-low), day-clustered | age-of-extremes drift (drawup/drawdown asymmetry) | headline contrast by RB[t] |
| S27 | VWAP-side occupancy: occ = share of last 60 contiguous bars with close > session VWAP (frozen SessionVwap) -> forward 60m return; FIXED bins {0}, 0.1-grid, {1}. Headline: E[fwd60 \| occ=1] - E[fwd60 \| occ=0], day-clustered | side-persistence at the OU-informed 60m horizon (median VWAP half-life 106m, S6) | headline contrast by RB[t] |
| S28 | OBV-price divergence: over trailing 60 contiguous bars, dP = c[t]-c[t-60], dV = sum(sign(r) x volume); 2x2 cells (sign dP x sign dV); aligned30 = sign(dP) x forward 30m return. Headline: confirm - diverge contrast within each price sign and pooled, day-clustered. DECLARED timeframe-neighbour of the frozen momentum objects (60m/30m vs frozen 30m/15m) | volume-flow confirmation vs divergence (bar-volume proxy; no fabricated order flow) | contrasts by RB[t] |
| S29 | Daily time-series momentum, COMPLETE lag family {1, 5, 20} days: aligned = sign(sum of last L day returns) x next-day return; day bootstrap | classic TSMOM at the shortest daily scales — the longer-horizon direction the OU finding points at | by day-level RANGE-score tercile (S6 construction) |
| S30 | Half-session persistence: A = 09:31-12:00 accrual, B = 12:01-16:00 accrual (>=120 / >=180 bars present); aligned = sign(A) x B; day bootstrap | morning-trend -> afternoon persistence (session structure, no tunable window) | by RB at the last bar <= 12:00 and by day-level tercile |

Machinery: contiguous 1m log returns, gaps never bridged; frozen RVMR
states unchanged; frozen `dvt_spec.SessionVwap`; forward windows
verified inside the discovery window; day-clustered bootstrap (5,000
iterations headline / 1,000 per cell, seed 20260826); no ML; no
parameter sweeps. At most TWO promotable candidates may emerge from this
wave, and any future promotable test enters the cumulative programme
family (next slot: M_cum = 7). Outputs remain EXPLORATORY.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
