# BRK-V1 — PRE-REGISTRATION (FROZEN BEFORE RESULTS)

**Declared family size M = 3** (BRK-H1, BRK-H2, OVN-H1). REC-P1 is a
prospective registration, carries no backtest, and is NOT in the family.

This document is committed BEFORE any result is computed. Nothing below
is edited after results exist; corrections, if any, appear in the
findings document as explicit corrections.

## Why this family exists

Sixty hypotheses across five batches converged on one replicated result:
**order flow predicts MAGNITUDE, not DIRECTION.** MFE ≈ MAE, ~50%
favourable-first ordering, every family. Yet all sixty were directional
bets — the programme repeatedly tried to extract a directional edge from
a magnitude signal.

BRK-V1 tests the structure that monetizes magnitude *without* requiring
direction, plus two structural classes never opened here.

**Prior: expect all three to fail.** The value is that each failure
closes a structural class rather than a parameter setting.

---

## BRK-H1 — Magnitude-event bracket

**Claim.** If OFH6-class events elevate movement but not its sign, an OCO
bracket straddling the signal close captures the move whichever way it
breaks, and beats matched non-signal minutes.

**Universe.** The frozen OFH6 signal list, verbatim — `cand_spec.generate`
→ `SIGS`, 952 signals on the canonical 355,455-bar history. No new
signal parameters are introduced. Signal direction is RECORDED BUT NOT
USED for entry.

**Arming.** At signal bar `j` with close `C` and `atr = B[j]['atr']`:
- buy stop at `C + 0.5 * atr`
- sell stop at `C − 0.5 * atr`
- bracket life 30 bars (minutes); unfilled at expiry = **SCRATCH**

**Fill rule**, bars `j+1 … j+30`, requires consecutive bars:
- `high >= upper` → long fill at `upper`
- `low <= lower` → short fill at `lower`
- **both in the same bar → AMBIGUOUS.** 1-minute data cannot order them.
  **Primary metric assigns AMBIGUOUS conservatively** — the side whose
  outcome is worse is taken as the fill. Optimistic and excluded variants
  are reported as sensitivity only and never promoted.
- first fill only; no re-arm after a stop-out

**Management after fill** — the frozen OFH13 management, verbatim:
- stop at `fill ± 1.5 * atr` (atr from the SIGNAL bar, frozen at arming)
- **no target**
- time exit 60 minutes from FILL
- cost 0.87 pt charged on filled trades only; scratches cost 0

**Cooldown.** 30 minutes between armed brackets (the frozen `COOL`).

**Eligibility.** `entry_ok` at the signal bar; the full 30-bar arming
window and the 60-minute post-fill window must lie in consecutive bars.

**Primary metric.** Per-signal EV in points over ALL armed brackets,
scratches counted as 0 in the denominator.

**Primary test.** Difference against MATCHED CONTROLS. Sign-flip-by-day
is the null for a directional claim and is INVALID here — a bracket has
no chosen direction to flip. Controls instead:
- matched on partition, RTH hour, and ATR quintile
- must be ≥ 60 minutes from ANY OFH6 signal
- must pass `entry_ok`; identical bracket armed with identical rules
- K = 5 controls per signal, seed 20260823, sampled without replacement
- **day-clustered bootstrap 95% CI** on (signal EV − control EV), 20,000
  iterations, and a **day-clustered label-permutation p**, 20,000
  iterations

**Secondary, free.** Does OFH6 direction predict which side fills? Under
the programme's central claim this is ~50/50. This is the cleanest
instrument yet built for that claim. Reported, not part of M.

**Sensitivity, pre-declared, never promoted.** Offset ∈ {0.25, 0.75}
ATR; life ∈ {15, 60} min. Primary is 0.5 ATR / 30 min and only that.

**Stated risk.** If magnitude events are symmetric round-trips, brackets
bleed on whipsaw. Either outcome is informative: it separates
drift-after-break from pure oscillation, which sixty directional tests
never isolated.

---

## BRK-H2 — 15s compression → expansion

**Claim.** Sub-minute compression resolves into directional expansion.
Uses 15s bars as the SIGNAL SOURCE — not to re-time an OFH13 parent,
which is the construction that already failed in LTF-EXEC-BACKTEST-V1.

**Data.** The genuine 15s capture, days **≤ 2026-08-19 only**
(`FREEZE_DATA_END` is respected; 2026-08-20/21 are excluded). RTH
09:30–15:00 ET. OHLCV only — no delta is used, and none exists on
Second series.

**Box.** The 20 consecutive 15s bars ending at bar `i` (5 minutes).
`range = max(high) − min(low)`. `ATR1m20` is computed causally from the
capture's own 1m bars (true range, 20 bars, ending at or before the box).

**Compression gate.** `range <= 0.35 * ATR1m20` **and** `range >= 2.0`
points (8 ticks — a cost floor; a box tighter than this cannot pay 0.87
round trip plus slippage).

**Trigger.** The next 15s bar closes outside the box.
- entry at that bar's close, direction = break side
- stop = far box edge
- time exit 30 minutes from entry, no target
- cost 0.87 pt

**Lockout.** 15 minutes after any entry before a new box may arm.

**Primary metric.** Per-trade net, points.

**Primary test.** Sign-flip-by-day (valid — this IS a directional
claim), 20,000 iterations, plus day-clustered bootstrap 95% CI.

**Stated limitation, in advance.** The capture is 70 days, all inside
the IR era. This is already-spent history, so any positive result is
**EXPLORATORY-DERIVED** and cannot be promoted on this evidence alone.

---

## OVN-H1 — Overnight drift baseline

**Claim.** Equity-index returns concentrate overnight. This is the only
BRK hypothesis grounded in published literature rather than our own
mining, and it has zero fitted parameters.

**Rule.** Long at the 1m bar closing 18:00 ET; flat at the 1m bar
closing 09:29 ET. Both anchors must exist in the canonical history.
Net = `(exit − entry) − 0.87`. Every qualifying night is included; no
filter, no cooldown, no parameters.

**Primary metric.** Per-night net, points. Expected n ≈ 245.

**Primary test.** Sign-flip-by-day (each night is its own cluster, so
this is a signed test on nightly returns) plus day-clustered bootstrap
95% CI.

**Purpose.** Benchmarks whether MNQ carried overnight drift worth owning
this year, independent of any signal.

---

## REC-P1 — 15m stop-run reclaim, PROSPECTIVE ONLY

**No backtest is run.** The 15m stop-run reclaim is the only directional
pattern that replicated twice independently (PRO-OF-H3 n=476 R 1.21;
MR-H3 RECLAIM n=581 mean +7.85 R 1.23, sign-flip p 0.0215, day-CI
[+0.00, +15.56]) without clearing family correction (BH q 0.387 at
M=18). Both tests spent the same 12 months. **There is no untouched
history left to test it on**, so re-mining it would produce a number
with no evidential value.

Spec, lifted verbatim from `analysis/v41/mrv_run.py::mr_h3` with
`arm='RECLAIM'` (not from memory):

1. at bar `j`, for each direction `d ∈ {+1, −1}`, find a 15m level
   (`lo_at(j)` for `d=+1`, `hi_at(j)` for `d=−1`) that bar `j` sweeps —
   `low < px` for `d=+1`, `high > px` for `d=−1`; first such level
2. require `relVol >= 2.0` at bar `j`
3. scan `k ∈ [j, j+5]`, consecutive bars only; enter at the first `k > j`
   whose close is back through the swept level (`close > px` for `d=+1`,
   `close < px` for `d=−1`)
4. **no effort-failure gate** (this is what distinguishes RECLAIM from
   FULL)
5. `entry_ok` at `k`; 30-minute cooldown via `cool()`

**Action.** Registered as a SIGNAL-ONLY candidate in the prospective
logger beside G4/G3. It submits no orders and produces no trade rows.
The forward ledger is the only instrument that can promote it.

---

## Family rules (binding on all of BRK-V1)

- everything above frozen before results; **M = 3**; BH within family
- per-signal / per-night accounting — **scratches and untriggered
  signals count as 0 in the denominator**, never dropped
- cost 0.87 pt round trip, tick 0.25, **MNQ only**
- day-clustered inference throughout; no observation-level i.i.d. claim
- AMBIGUOUS ordering never assigned optimistically in a primary metric
- partitions reported (U / DEV / IR) for every hypothesis
- tail concentration (top-1%, top-10 share) reported for any positive
  cell — the programme's repeated failure mode is a result that is one
  trade wide
- **OFH13_PROSPECTIVE_V1 is not touched, tuned, or re-specified by any
  of this**
- **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING**

## Promotion gate, declared in advance

A BRK hypothesis is promoted ONLY if: BH q ≤ 0.05 at M = 3, the
day-clustered CI excludes zero, the sign is stable across U/DEV/IR, and
the result is not tail-dominated. Anything less is reported as
EXPLORATORY and explicitly NOT promoted. "All three failed" is a valid
and expected outcome.
