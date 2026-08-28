# MTF-V1 — MULTI-TIMEFRAME ANOMALY SURVEY — PROTOCOL FREEZE

Frozen and committed **before any outcome is computed**.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.

## 0. Why this program exists, and what it deliberately is not

The user's directive: signal discovery so far has lived almost entirely
at 1-minute resolution; widen the horizon and test whether an edge lives
at any timeframe. The honest prior-coverage map (read before this
freeze): 15m breakouts / opening range / overnight-level breaks
(NQ-DIRECTION 0/4), 4H setups (DVT), daily direction batteries, Monday
(failed holdout), half-session persistence (failed holdout), daily
brackets (VTBS), turn-of-month and clock-hour are **dead and are not
re-run here**.

MTF-V1 instead does two things the record shows were never done:

1. **Scale-extends the programme's only holdout-CONFIRMED anomaly.**
   ANOMALY-CONFIRM-V2 H1 (ORDINAL-V-TURN) passed 13/14 on the untouched
   2024+ window (boot p 0.00005, both sides, magnitude-matched at 107%)
   and was shelved solely because at 1m it is ~0.075 pt/event vs 0.87 pt
   cost. It was never tested at any other scale. Registry note: the
   coarse ANOMALY-CONFIRM-V2 registry row says DEAD_FROZEN because H2
   failed; the committed findings are authoritative that **H1 is
   confirmed, not dead** — extension of a confirmed anomaly to new
   scales is not a dead-hypothesis rescue.
2. **Opens the multi-hour reversion cell its own measurement points at.**
   ANOMALY-SCAN measured the OU half-life of (close − VWAP) at a median
   **106 minutes** and recorded: "the reversion clock is slower than the
   frames tested." Every prior VWAP-reversion death was at ≤60 min
   horizons. The matched-clock cell (~2× half-life) was never opened.
   **Dual reading disclosed:** this sits in the spent
   PRICE_MEANREV_INTRADAY neighborhood; the distinctness claim is a
   measurement-driven horizon correction (mis-clocked prior tests are
   uninformative about the 3-4 h cell), not a threshold retune. A
   reviewer applying the strict cosmetic-derivative rule may discard
   B2's verdict; the judgment is recorded either way, exactly as done
   for VTBS/BRK.

Everything runs on the exposed 7.1-year DEV — every verdict ceiling is
**exploratory**; nothing here can be called confirmed on this data.

## 1. Data (exact)

Canonical 1m grid (`analysis/rvmr/rvmr_run.py::load_bars()`,
STAMP_SHIFT=0, close-stamped ET), tradedays ≤ **2026-08-17**.
Buffer/VALIDATION/OOS/LOCKBOX untouched. T-minute bars are built on the
`em` contiguity clock: bucket = `em // T`; a T-bar is **valid only if all
T constituent minutes are present**; consecutive T-bars additionally
require bucket adjacency. Daily series = last RTH close (stamp ≤ 960)
per day.

## 2. Module A — descriptive multi-scale map (ledgered, never promotable)

- **A1** lag-1 and lag-2 autocorrelation of valid T-bar log returns,
  T ∈ {5, 15, 30, 60, 240}; day-clustered percentile bootstrap
  B=5,000, seed 20260830. 10 cells.
- **A2** daily momentum spectrum: mean next-day close-to-close return
  conditional on sign(past k-day return), k ∈ {1,2,3,5,10,20}; contrast
  up-minus-down; stationary 20-day block bootstrap B=5,000, seed
  20260831. 6 cells.
- **A3** cross-scale alignment: sign of the last completed 240m-bar
  return vs sign of the last completed 15m-bar return; contrast
  (aligned − conflicted) on the next 60m log return, sampled at each
  valid 15m close, overlapping windows purged to non-overlapping 60m
  steps; day-clustered bootstrap. 1 cell.

BH across all 17 Module-A cells. Descriptive only.

## 3. Module B1 — V-TURN-SCALE (confirmatory, 4 cells)

Frozen construction, transported verbatim from `confirm2_run.py`:
motif over three consecutive **valid, contiguous** T-bar closes
(x0,x1,x2), all distinct; ordinal encoding via rank order; VUP='102',
EUP='012', VDN='201', EDN='210'; last-leg sign `lls = sign(x2−x1)`;
outcome = next contiguous T-bar log return `r1`;
`ta = lls × r1` (bp). Primary statistic per T:
`Δturn = E[ta | V] − E[ta | E]`, day-blocked percentile bootstrap
B=10,000, seed 20260832, two-sided boot p. **T ∈ {5, 15, 30, 60}** —
four primary cells, BH across the four.

Also reported per T (economics, not a gate on the anomaly):
`E[ta | V]` in bp and in **points per event** at that bar's average
price, vs the 0.87 / 1.305 pt cost model. Translation to a strategy cell
is considered **only if** a T-cell passes BH q ≤ 0.05 with positive
Δturn AND `E[ta|V]` in points exceeds base cost — then the frozen
translation is: enter at next T-bar open after a V-motif in the last-leg
direction, hold exactly one T-bar, market orders, house gates. No other
translation may be invented after seeing results.

## 4. Module B2 — VWAP-OU-CLOCK (confirmatory, 1 cell + frozen neighbors)

- Session VWAP: cumulative Σ(tp·v)/Σv over RTH stamps 571..t,
  tp=(h+l+c)/3, per day.
- `base_d` = trailing-60-day median RTH range (≥40 valid required, as in
  VTBS). Normalized extension `z_t = (c_t − vwap_t)/base_d`.
- Eligibility: stamps 631..900, VWAP ≥ 60 min mature, day has valid base.
- **Event**: first bar where `|z| ≥ thr_d`, `thr_d` = type-7 q90 of the
  pooled |z| values over the prior 20 eligible days (causal; ≥2,000 pool
  values required). One position at a time; next event eligible only
  after exit.
- **Trade**: enter at next 1m bar open, direction = toward VWAP.
  Stop: adverse — distance to VWAP reaching 2× the entry distance
  (risk R = entry distance in points, gap-through at worse). Exit:
  first bar whose range touches the current bar's VWAP, or entry+212
  min (2× the measured 106-min half-life), or stamp 955 — whichever
  first; exits at that bar's close for VWAP-touch (conservative:
  fill at vwap only if between low and high, else close), open-based
  for time exits.
- Stats: day-clustered bootstrap B=10,000 seed 20260833 on stressed
  mean; day-blocked sign-flip permutation P=10,000 seed 20260834;
  house gates (n≥200, days≥60, PF 1.30/1.15, EV +0.10R/+0.05R, CI>0,
  p≤0.05, q≤0.05 with B1 in one BH family of 5 confirmatory cells,
  ≥6/8 years positive, no >50% domination, best-day/top-1% removal,
  profiles).
- Frozen neighbors (diagnostics, never candidates): thr q85/q95;
  exits 106m/318m.

## 5. Costs, multiplicity, ceilings

Base 0.87 pt RT, stressed 1.305 pt RT, MNQ $2/pt, one contract.
Confirmatory BH family = 5 cells (B1×4 + B2). Module A ledgered
separately. All cells, pass or fail, enter the hypothesis ledger and the
spent registry at close-out. DEV is exposed: the strongest permitted
positive conclusion is exploratory-pass requiring untouched
confirmation. The complete frozen search runs to completion regardless
of early results; no cell may be added, merged, or re-thresholded after
outcomes.
