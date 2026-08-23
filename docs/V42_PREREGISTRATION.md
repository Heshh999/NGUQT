# V4.2 FVG + ORDER-FLOW FAILURE FAMILY — PRE-REGISTRATION

**Committed before any V4.2 outcome was computed.** M = 10, no additions
after results. All ten are **EXPLORATORY-DERIVED**: the full 12-month
history has been examined repeatedly, so **NO TRUE HISTORICAL OOS
REMAINS** — DEV/IR are internal partitions only, and future prospective
data is required for any validation claim. The frozen shelf
(OFH13/OFH14/G4/G3/G1, prospective.py, registry) is untouched, and no
prospective OFH13 data is used for anything here.

Honesty note: the earlier RED-H10 ablation already showed one seen
result in this space (FVG + failed aggression, no location: R 1.23,
ordering 49.5%). This family partially overlaps that observation and is
therefore even more strongly exploratory-derived; that arm's existence
is WHY this batch was commissioned, and it is disclosed rather than
hidden.

## Source-of-truth / reproduction gate (passed before this commit)

`cand_spec.generate` on the merged 355,455-bar history reproduced the
canonical anchors exactly: 952 signals, OFH13 133, OFH14 462, G4 218,
G3 477, G1 845.

## Data audit

Same as `docs/RED_PREREGISTRATION.md` (per-price ladders NOT stored, no
DOM, no VWAP; developing profile causal; delta/imbalance/aggression/
volume-per-tick features available). Additionally for this family:

- **30-second data (ph2 capture):** genuine 30s OHLCV bars for
  **2025-09 → 2026-05 (9 months, 192 days), ~09:30–11:00 ET only**.
  **No 30s bid/ask, no 30s delta** — none will be invented. OFH13-30S is
  therefore restricted to canonical OFH13 parents whose FVG mitigation
  window intersects that coverage, price-action triggers only, and the
  1m order-flow context frozen when causally available.

## Frozen shared machinery (reused, not refit)

| piece | definition | source |
|---|---|---|
| FVG | canonical `cand_spec.build_fvg` — 3-candle gap **with embedded displacement** (range ≥ 1.00 ATR, body ≥ 0.50 of range, close-location ≥ 0.70, c3 beyond c1 open) | canonical |
| mitigation semantics | canonical `_mitigate`: far-side close invalidates; touch = wick into zone; trigger = completed close beyond midpoint; opposing-flow flag = any mitigation bar with opposing `|delta| ≥ 511` | canonical |
| FVG life (this family) | formation + 30 min (the canonical 30-min life anchored at formation, since these FVGs have no parent signal — the one necessary departure from OFH13's signal+30, disclosed as such; freshness/iFVG studies use formation + 120 min where the rule needs a longer observation window, stated per rule) | frozen here |
| aggression | opposing `|delta| ≥ 511` (Q_BD75, frozen long ago) | canonical |
| effort-vs-result | E2 score with the **already-frozen** RED-family DEV q75 cut **15.961**, evaluated on the FIRST opposing-aggression bar of the mitigation | frozen (RED phase) |
| entry gate | RTH, ≥ 60 min to close, valid ATR (canonical D1 semantics) | canonical |
| cooldown | 30 min chronological per hypothesis/arm | canonical convention |
| outcomes | 5/10/15/30/60 m MFE/MAE/net; favourable-first at ±0.25/±0.5/±1/+1.5 vs −1/+2 vs −1 ATR with AMBIGUOUS never assigned | as RED phase |
| matched controls | same direction, hour, ATR quintile, partition | as RED phase |
| costs | 0.87 pt RT; sensitivity +1/+2 ticks | frozen |
| partitions | U ≤ 2025-11-01, DEV ≤ 2026-03-31, IR → 2026-08-19 | established |

A mirror of `_mitigate` that additionally reports the first-aggression
bar index will be written for the studies that need it; it must agree
with canonical `_mitigate` on trigger index and flow flag on the full
FVG population before use (asserted in code).

## The ten rules (LONG stated; SHORT = exact mirror)

**FVG-F1 — FVG + flow failure, NO OFH6.** All canonical FVGs. First
mitigation walk (formation+30). Arms: A = mid-reclaim trigger only;
B = A + opposing-flow flag; **FULL = B + E2 ≥ 15.961 on the first
aggression bar.** Entry at the trigger close. Reference arm E = canonical
OFH13 numbers. Key question: does removing OFH6 preserve the behaviour?

**FVG-F2 — freshness.** Same FVGs, life extended to formation+120 for
observation. Touch episodes counted causally (an episode = entering the
zone from outside; far-side close kills the zone). The FULL-F1 logic is
evaluated within episode 1, episode 2, episode 3+. Preference is stated
in advance: monotonic decay (1st > 2nd > later), not one lucky bucket.

**FVG-F3 — sweep → displacement → FVG → failure.** Sweep = a bar whose
low trades below a causally-known 3m swing low (primary; 15m and
prior-day reported separately). A bullish canonical FVG must FORM within
10 bars after the sweep bar. Then FULL-F1 logic on that FVG. Controls:
sweep only (entry at first close back above the swept level), sweep+FVG
without flow, FVG+failure without sweep (= F1 FULL), FULL F3.

**FVG-F4 — inverse FVG.** A bearish canonical FVG, unexpired
(formation+120), is CONVERTED the moment a completed 1m close exceeds
its upper bound; the zone freezes as a bullish iFVG at that close.
First retest walk from the conversion bar (+30): touch = wick into zone,
invalid = close below zone low, aggression + E2 as shared, trigger =
close above midpoint. Controls: ordinary FVG (F1), conversion counts
without retest, retest without flow, +aggression, FULL.

**G4-FVG — canonical G4 at an FVG.** Canonical G4 events untouched. A G4
event qualifies when its entry bar touches an active same-direction
canonical FVG zone (formed within the prior 120 min, not far-side
invalidated). Compare: all G4, G4-at-FVG, G4-not-at-FVG, and FVG without
G4. Primary question: MAE / MFE-MAE / ordering improvement, not points.

**G4-SWEEP — canonical G4 after a sweep.** G4 event qualifies when a
sweep of a causally-known 3m swing low (long side) occurred within the
prior 15 bars. 15m and prior-day variants reported separately; the
declared primary is the 3m aggregate.

**FVG-WEAK-PB — continuation.** Canonical bullish FVG; impulse delta =
Σ delta of the three formation bars, required ≥ +511 (aligned). First
touch episode within formation+120. **Weak pullback:** |delta of the
touch bar| ≤ 0.5 × |impulse delta| (single frozen ratio). Zone must stay
valid. Trigger = completed close ABOVE the zone high within 10 bars of
the touch (continuation, not mid-reclaim). Controls: re-expansion after
ANY pullback; after WEAK pullback (FULL); after STRONG pullback
(complement).

**FVG-ER — effort/result buckets.** On F1-B events (mitigation +
aggression present), the frozen E2 score at the first aggression bar is
bucketed by DEV terciles (frozen before IR is examined) into
LOW/MED/HIGH. Success requires monotone geometry (HIGH > MED > LOW in
MFE/MAE, ordering, MAE, median). Comparison: the same bucketing done on
raw |delta|/scale instead of E2, to test whether effort-vs-result carries
information beyond raw aggression size.

**FVG-DISCOUNT — execution study on F1-FULL parents.** At the F1-FULL
trigger, freeze entry/zone/ATR. Arm A = market at trigger close. Arms
B/C = limit at close − 0.25 / − 0.50 ATR (exactly two levels), valid 30
minutes, cancelled on a close through the zone's far side (thesis
invalidation), filled on touch. PER-PARENT EV is the primary metric;
filled-only EV never suffices.

**OFH13-30S — execution study on canonical OFH13 parents.** Parents and
context frozen exactly as canonical. Eligible parents: mitigation window
intersects genuine 30s coverage. Arm A = canonical 1m trigger. Arm B =
first genuine 30s close beyond the FVG midpoint at or after the touch;
entry at that 30s close, outcomes anchored to the containing 1m path.
Report parents eligible, both/1m-only/30s-only/neither, entry and risk
differences, geometry, per-parent EV. Earlier ≠ better; geometry decides.

## Gates (identical to prior phases)

Raw-geometry gate before any management; survivors only get the small
mechanical stop family (FVG invalidation / attack extreme / structure /
1 / 1.5 / 2 ATR) and plateau-seeking exits (15/30/45/60 m; 0.5–3 R). No
optimization of anything else. Rankings use the pre-declared 11-item
criteria (matched-control geometry first, points last). Statistics:
sign-flip-by-day p, day-clustered CI, BH q at M = 10. Verdict vocabulary
fixed. "None of the ten survived" is an acceptable result.
