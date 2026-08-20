# VEC-H1 — Preregistration (FROZEN 2026-08-20)

Frozen BEFORE the capture exists. No VEC-H1 outcome has been computed,
inspected, or estimated at the time of writing. This is the first
hypothesis in the programme preregistered while that is still literally
true rather than reconstructed after the fact.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## Hypothesis

**VEC-H1 — next-15m parent-vector wick retrace + 1m same-direction
vector.** Class A, market edge. Source class: USER-DERIVED / HEURISTIC.
It is NOT presented as a Traders Reality rule; no primary public source
states these mechanics.

LONG: a completed 15m GREEN or BLUE vector with a noticeable LOWER
wick. During the immediately-following 15m candle only, price retraces
down toward the frozen low. A completed 1m GREEN or BLUE vector fires
at/near that extreme. Predicted direction: **LONG**.

SHORT: exact mirror — RED or VIOLET parent, UPPER wick, retrace up
toward the frozen high, 1m RED or VIOLET trigger. Predicted: **SHORT**.

## Frozen parameters (primary; perturbations are robustness only)

| rule | value |
|---|---|
| wick size | ≥ **20%** of the parent's total range |
| proximity | trades into the wick zone **OR** within **0.10 × parent ATR** of the extreme |
| search window | the immediately-following **15 minutes**, nothing more |
| entry | close of the qualifying completed 1m vector |
| ATR | 20-period on 15m |

## Stops — primary is 1.5 × parent ATR, and why

The stop-family study (33,929 DEV / 15,215 VAL probes, eight
definitions) found the entire spread between best and worst stop was
0.59 pt — less than the cost of trading — and that ATR-scaled stops at
1.0–2.0× were the only family ranking well in **both** splits. The 1m
candle edge was hit on **82%** of trades. So:

- TIGHT = 1m trigger candle extreme ∓ 1 tick (reported, not primary)
- **MEDIUM = 1.5 × parent 15m ATR — PRIMARY, and the race stop**
- STRUCTURAL = beyond the parent extreme ∓ 1 tick

## Primary outcome

Mean net points at **60 minutes**, probe-side signed, minus costs
(gross / 0.37 / 0.87 / 1.37 pt RT). Chosen before any outcome is
visible and not to be swapped later.

## The matched arms — the actual test

Emitted against the SAME parent so none can be chosen afterwards:

- **A_LOCATION_ONLY** — price reached the zone; first bar to do so was
  not a qualifying vector.
- **B_VECTOR_AWAY** — qualifying vector inside the window, away from
  the extreme.
- **C_FULL** — qualifying vector at/near the extreme.

**C − A isolates the vector. C − B isolates the location.** Without
both contrasts a positive C result would only show that same-colour
vectors tend to follow one another, which is not the hypothesis.

## Success and failure conditions

SUCCESS requires all of: C beats A **and** B on the primary metric in
DEV *and* VAL; positive net at 0.87 pt cost; day-block bootstrap
p < 0.05 one-sided; permutation p < 0.05; effect surviving BH across
the arm family; ≥ 200 independent C events per split.

FAILURE (any one): C ≤ max(A, B) in either split; sign flip DEV→VAL;
net negative at base cost; n < 200 in a split.

If the base fails, it will NOT be rescued by adding EMA, time-of-day,
level, order-flow, wick-size or proximity filters. That is written
here, in advance, on purpose.

## Splits

- **DEV** 2019-07-01 → 2022-12-31 (discovery, diagnostics)
- **VAL** 2023-01-01 → 2024-06-30 (confirmation)
- **HOLD** 2024-07-01 → 2026-08-20 — **UNTOUCHED**, opened only if the
  hypothesis passes DEV and VAL, once, and never again.

The order-flow OOS was spent on 2026-08-20 as a P&L illustration and is
not available to VEC-H1. The structure HOLD has never been read.

## Multiplicity on the record

Programme totals before this test: V4 8 hypotheses (0 survived), V5 10
(0), V4.1 8 (0), plus an 8,329-conjunction search with permutation
control, a 40-cell asymmetry scan, 4 fade/avoidance candidates, and 64
hypothesis × stop cells. VEC-H1 is **one** further test and will be
judged as such. The prior probability implied by that history is low
and is not adjusted upward because this idea is new.

## Known prior that argues against it

Break events in this instrument show symmetric excursion (median MFE
1.375 R vs MAE 1.363 R on 13,548 DEV events). If VEC-H1's population
shows the same symmetry, no stop or target geometry will produce an
edge, and the arm contrasts will be the only thing worth reading. The
capture records MFE/MAE so this is checked first, before any
expectancy number is quoted.
