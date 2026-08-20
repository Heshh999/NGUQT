# V4.1 Phase 0 Audit — Full-Capture Research Environment

Date: 2026-08-20. Auditor: the research agent. Scope: the 7.1-year
structure/entries capture (2019-06-30 → 2026-08-20) and the 9.5-month
order-flow/profile capture (2025-11-02 → 2026-08-19), against the
V4.1 backtest prompt's Phase 0 checklist.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. The engines submit no
orders; a source scan enforcing that runs in the regression suite.

## Verdicts

| Category | Verdict | Basis |
|---|---|---|
| DATA QUALITY | **PASS** | Structure audit PASSED: 28,554 rows, 1,847 session days, unexplained gaps 0.0123% of 2,512,300 bar transitions (threshold 0.5%). Entries: 72,403 rows verified independently — 0 duplicate (eventId, architecture) pairs, stable ~10,100 rows/yr 2020–2025, headers identical across 87 monthly files. Order flow PASSED separately: 281,214 bars, 100.00% level coverage, ask+bid ≡ volume on every bar (worst 0.0000%), byte-identical across three runs and two builds. Worst structure gap (646 min, 2025-11-28) is Thanksgiving; the order-flow capture found the same holiday gap independently. |
| AGGREGATION | **PASS** | Deterministic NT8 series map (1d/4h/60m/15m/5m/3m/1m) printed and checked at startup; a required series with zero bars aborts. Completed bars only (`Calculate.OnBarClose`). The bar-stamp convention (NT stamps a completed bar at its CLOSE) was a real defect found in sample 2, fixed, and is pinned by regression tests that reproduce the field symptom (−12 min median entry delay) from the quarantined defective function. |
| NO-LOOKAHEAD | **PASS** | 0 lookahead violations across the full capture (per-feature timestamp check against the event's `SnapshotCutoff`, order-independent). 0 negative entry delays; verified independently on all 72,403 entry rows (min minsToEntry = 1). Swings gated by `KnownAtEt` at query time; levels enter the book only on the 1m clock after they exist. |
| EVENT INDEPENDENCE | **PASS** | Break events fire once per excursion (`V4BreakGate`, fixed after sample 1 showed 84% of levels re-broken with mean 4.5 events each). Probes carry `parentEventId` and `thesisId`; thesis clustering window 60 min. Analysis will report raw signal count vs independent thesis count and use day-block bootstrap. |
| COST MODEL | **NEEDS WORK** | No user-supplied commission/slippage. A provisional family is frozen in the preregistration (base 0.87 pt RT, stressed 1.37 pt RT, plus gross and commission-only) but per the prompt NET rankings remain **pending cost-model confirmation** by the user. No strategy will be promoted on zero-friction numbers. |
| OOS / LOCKBOX INTEGRITY | **PASS** | No feature→outcome relationship on the full capture has been examined by anyone or anything to date. Verification to date inspected: schema, distinct-value counts per column (marginal only), causality timestamps, cross-column invariants (stop ordering, race bounds, recovery monotonicity), and per-year *distinctness* (not performance). Splits are frozen in the preregistration BEFORE any conditional analysis. |
| RESEARCH PIPELINE | **PASS** (2 documented exceptions) | Source audit: continuous across 6 sample iterations, 17 engine defects found and fixed, each pinned by a regression test proven to fail on the reintroduced defect. 297 deterministic tests pass. NT8 compile + runtime verified by the user's runs. Exceptions below. |

## Documented exceptions (accepted, on the record)

1. **Chart spot-check not done.** The prompt requires 20–30 EventIDs
   manually compared against the NinjaTrader chart. The agent has no
   chart. This is user-owned and OPEN. Recommended: pick ~20 eventIds
   spread across years, confirm the 15m bar OHLC, the swing that broke,
   and the vector colour against the chart. Analysis proceeds; a failed
   spot-check would invalidate conclusions and must be reported.
2. **Depth**: NT8 keeps no historical L2 → DEPTH VERDICT FAILED, no
   depth features emitted (by design, not a defect).

## Issues by severity

**CRITICAL** — none open. (The structure CSVs were not yet uploaded at
audit time; that blocks outcome analysis but is a delivery gap, not a
validity issue. Confirmatory analysis must not begin until they arrive
and pass the same verification battery as the entries.)

**HIGH**
- Cost model unconfirmed (see verdict). User to confirm actual MNQ
  round-turn commission and expected slippage.
- The order-flow layer (Nov 2025 → Aug 2026) overlaps the structure
  lockbox period. Resolution frozen in the preregistration: H6/B2 use
  their own split inside the OF window; those rows are thereby burned
  for structure-layer lockbox purposes and this is accepted and logged.

**MEDIUM**
- 1,302 AMBIGUOUS stop/target races (0.14% of 914,240). Both bounds
  recorded; the engine refuses to pick. These are the candidates for a
  later 30-second event-window pass (Phase 2, only if a parent edge
  survives). Measured on 2.28M races previously: the choice moves
  P(target-first) by ~0.042 — bounds will be carried through results.
- Holiday calendar not modelled: the 310 unexplained gaps are dominated
  by CME holiday halts (Thanksgiving, Christmas, July 4, Good Friday
  etc.); at 0.0123% this is well under threshold and affects no label
  (windows simply span the halt in event time).
- VEC-H1 (user's 15m-parent-wick + 1m-vector hypothesis) is NOT
  implementable from this capture: the engine does not emit 1m PVSRA
  classification. Recorded as NOT IMPLEMENTED, not silently dropped.
  Implementing it needs a small engine addition and an event-window
  re-run; it would then join as a NEW preregistered hypothesis.
- 3 warm-up entry rows and 62 hasEmaFan=FALSE rows in July 2019 —
  excluded by per-row readiness flags, not by trusting a date.

**LOW**
- This run's build predates v4.1.6d, so the printed warm-up line
  ("576,000 1m bars / 400 days") is the known-wrong display text
  (real requirement: 36,000 / 25 days). Display-only; `f_isWarmup`
  came from the user's date parameter, and per-row readiness flags
  supersede both.
- Startup diagnostic prints the historical "RTH+ETH" session label;
  the ETH template was used (verified by the halt map reconciling).

## Runtime / data acceptance gate

| Gate | Status |
|---|---|
| Source-code audit | PASS (continuous, 6 iterations) |
| NinjaTrader compile | PASS (user's F5, all samples) |
| Deterministic tests | PASS (297/297; defect-reintroduction discipline) |
| Startup BarsInProgress / series diagnostic | PASS (printed, all series non-zero) |
| Structure/vector audit | PASS (28,554 rows; thresholds met) |
| Order-flow audit | PASS (281,214 bars; 100% levels; 0 mismatch) |
| Profile audit | PASS (206 sessions; inherits volumetric window) |
| Depth audit | FAILED by design — depth features not emitted |
| Chart spot-check 20–30 EventIDs | OPEN — user-owned exception |

Gate result: **PROCEED**, with the two documented exceptions carried
visibly into the final report.
