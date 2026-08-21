# G-Family Re-Test on the Extended History

**Date:** 2026-08-21
**Script:** `analysis/v41/gen10_oos.py`. Output: scratchpad
`gen10_oos_out.txt`.
**History:** merged capture, 355,455 bars, 2025-08-18 → 2026-08-19
(~12 months). 74,260 bars come from the new backward extension.

All ten G hypotheses re-scored with **every threshold unchanged**, on
three disjoint windows:

| window | dates | status |
|---|---|---|
| **UNSEEN** | 2025-08-18 → 2025-11-01 | never touched by any fit or design |
| DEV | 2025-11-02 → 2026-03-31 | original threshold-fit window |
| IR | 2026-04-01 → 2026-08-19 | original replication window |

DEV and IR are in-sample by construction — the G-family was designed
while looking at them. **UNSEEN is the only honest column.** It is still
*earlier* data, not forward data, so a regime difference remains a live
alternative explanation for anything that fails there.

## A defect caught by this re-run, and corrected

The script recomputes the frozen thresholds on the original DEV slice
and asserts they match. On the first attempt **the assertion fired**:
p75 |barDelta| came out 477 against the frozen 511.

Cause: `ofht_spec.entry_ok` — the predicate every original G/N/OFH run
used — does **not** enforce the ">=30 min after RTH open" rule that its
own header describes. Only `ofh6_spec.eligible()` (the OFH6 signal gate)
enforces it. The `entry_ok` I hand-wrote for `oos_aug.py` last turn *did*
enforce it, so that run used a slightly smaller eligible population than
the runs it was being compared against.

Corrected here by matching `ofht_spec.entry_ok` exactly; thresholds now
reproduce to the digit (511.00 / 2111.00 / 72.44 / 2.46). The mismatch is
documented in the code rather than "fixed", because changing the
predicate would refit every frozen quantile in the repo.

**Effect on the previously reported numbers: negligible.** OFH6 unseen
moves −1.48 → −1.40; G1 +0.51 → +0.67; G2 −0.86 → −0.63; G4 +13.42 →
+13.93; G6 +1.94 → +2.94. No verdict changes. The corrected values are
used below.

## Results

| | UNSEEN n / exc / ff1 | DEV exc | IR exc | verdict |
|---|---|---|---|---|
| OFH6 | 169 / **−1.40** / 50.3 | +9.50 | +7.07 | fails |
| G1 limit −0.5 ATR | 150 / +0.67 / 48.0 | +11.92 | +9.55 | holds, weakly |
| G2 limit −1.0 ATR | 130 / −0.63 / 47.7 | +7.39 | +11.64 | fails |
| **G3 delayed-if-discounted** | 82 / **+13.42** / 52.4 | +8.75 | +0.72 | **holds** |
| **G4 attack-failure** | 36 / **+13.93** / 55.6 | +20.88 | +9.87 | **holds** |
| G5 stacked-failure fade | 477 / −0.61 / 47.8 | +3.51 | −5.22 | fails |
| G6 stacked-go + OFH6 | 169 / +2.94 / 50.3 | +5.90 | +7.34 | holds, weakly |
| G7 compression release | 306 / **−5.36** / 45.3 | +0.42 | +1.09 | fails |
| G8 absorption continuation | 116 / **−10.60** / 41.1 | +2.33 | −1.13 | fails |
| G9 impulse→FVG | 92 / +0.66 / 50.5 | +18.43 | −4.98 | fails |
| G10 accepting reclaim | 16 / −11.86 / 56.2 | −5.86 | +25.79 | fails |

**Not one hypothesis clears correction on the unseen window.** Best raw
p = 0.087 (G3); **BH q over M=10 ranges 0.654 → 0.855.** Nothing is
significant, and that is the honest headline.

## What survived in substance

**G3 and G4 are the only two that both hold their sign and carry
comparable size on unseen data.**

- **G3** (enter 20 min after the OFH6 signal *only if* price is then on
  the adverse side) scored **+13.42 unseen vs +4.66 seen** — the only G
  hypothesis that did *better* out of sample. Its per-signal EV on the
  unseen window is **+6.09 against OFH6's −2.27**, at a 49% trigger
  rate. But its IR column is +0.72, so across the three windows it reads
  +13.4 / +8.8 / +0.7 — declining, not stable.
- **G4** (opposing-delta attack that fails) is the most consistent
  hypothesis in the family: **+13.93 / +20.88 / +9.87** across all three
  windows, positive everywhere, and unseen ff1 55.6%. n is only 36 on the
  unseen window and p = 0.131.

**G1's execution mechanism replicated a third time.** Per-signal EV
versus OFH6 immediate entry:

| window | OFH6 | G1 | fill |
|---|---|---|---|
| UNSEEN | −2.27 | **−0.17** | 89% |
| DEV | +8.63 | **+9.97** | 90% |
| IR | +6.20 | **+7.59** | 87% |

G1 beats immediate entry in **all three windows** (+2.10, +1.34, +1.39),
with a stable ~88% fill rate. The discount is a real execution effect.
It is not a strategy — it cannot manufacture drift that is not there,
which is exactly what the unseen window shows (−0.17 is still negative).

## What died

**G7, G8 and G10 reversed hard** on unseen data (−5.4, −10.6, −11.9
against +0.8, +0.5, +11.9 seen). G8 is the sharpest lesson: the
"absorption at fresh extremes precedes continuation" inversion, which the
diag14 examination surfaced and which read as a genuine folklore
correction, scores **−10.60 with ff1 41.1%** on data it had not seen.
That inversion was an artifact of the window it was found in.

**G5 is confirmed dead** (−0.61 unseen, −0.92 seen, n=1,419 total) —
consistent with its original diagnosis as resolution-move contamination.

**G9 flips** (+18.43 DEV, −4.98 IR, +0.66 UNSEEN) — a DEV-only effect.

## Status

**The G-family does not survive.** Ten exploratory-derived hypotheses,
none significant after correction on the first data they had not been
designed against. Two (G3, G4) hold their sign with meaningful size and
belong on the forward shelf; one mechanism (G1's limit discount)
replicates across all three windows as an *execution* improvement worth
roughly +1.3 to +2.1 pt per signal.

This is the second independent confirmation that the OFH6 drift is not
real: OFH6 itself is −1.40 unseen, and every hypothesis that depends on
it for direction (G1, G2, G6) is flat-to-negative there while the same
rules looked strong on DEV and IR.

Shelf after this pass: **G3, G4** (unseen-holding, unproven),
**G1's discount** (execution mechanism, replicated 3/3),
**OFH13 / OFH14** (from the prior pass, n=16/70).
Only 2026-09+ months remain unspent.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
