# V4.2-B MECHANISM EXPANSION — RESULTS (H-NEW1 … H-NEW15)

Pre-registered in `docs/V42B_PREREGISTRATION.md`, committed before any
outcome. M = 15. Canonical reproduction re-verified first (355,455 bars;
952 signals; 133/462/218/477/845). Frozen shelf untouched; no prospective
OFH13 data used. All fifteen are **EXPLORATORY-DERIVED** — no true
historical OOS remains.

**Headline: none of the fifteen survived. Five were structurally
impossible in the frozen frame, three had pre-declared predictions
refuted in the exact opposite direction, and the two largest-sample
generalizations were dead flat.**

## 1–3. Audits

Sources read and reused directly, never re-derived. Data as previously
audited (no per-price ladders, no DOM, no VWAP; 30s = genuine OHLCV
only, 2025-09→2026-05, ~09:30–11:00 ET, **no 30s delta invented**).
Canonical reproduction PASS. E2 cut 15.9608 and Q_BD75 = 511 reused
from prior freezes, not refit.

## 4–5. Definitions & causality

As pre-registered. All fifteen FVG-based studies read ONE shared episode
extractor (6,387 episodes reaching a trigger), so they cannot contradict
each other. Cross-check against the V4.2 F1-FULL arm: 117 vs 116 events —
the single difference is **explained, not a defect**: V4.2 required the
*first* aggression bar to fail (E2), V4.2-B accepts *any* failed attack.
The one extra event has first-attack E2 = 5.22 and a later attack at
16.22. Documented.

## 6. THE STRUCTURAL FINDING THAT KILLED FIVE HYPOTHESES

Inside a canonical FVG mitigation episode:

| | count |
|---|---|
| episodes reaching a trigger | 6,387 |
| episodes with ≥1 opposing attack | 1,646 |
| episodes with **2** attacks | **4** |
| episodes with **≥2 FAILED attacks** | **0** |
| trigger − last failed attack = **0 bars** | **129 / 131** |
| trigger − last failed attack = 1 bar | 2 / 131 |

**The canonical reclaim fires on the same bar as the failed attack
99% of the time.** There is no room for a second attack, a slow failure,
a weakening sequence, an efficiency flip, or sustained time under
pressure. This is a property of the frozen trigger definition, not a
market claim — and it makes these five hypotheses **undefined**, not
merely unprofitable:

- **H-NEW1** persistent failed aggression — **0 events**
- **H-NEW2** failure speed — 131/131 FAST, **no variance to test**
- **H-NEW10** efficiency flip — **2 events** (2/131 have any post-failure same-side aggression)
- **H-NEW13** quality score — 3 of 5 pre-declared dimensions degenerate (≥2 attacks 0%, FAST reclaim 100%, flip 2%); a score cannot be built
- **H-NEW15** time under pressure — 115 events at 1 bar, 1 event at 2–3, **none beyond**

## 7. Frame widening (disclosed)

H-NEW4/5/9 are not intrinsically FVG-bound in their hypothesis text, and
their pre-registered frame yielded zero events. They were therefore
**also** run location-free (attack = |delta| ≥ 511; a sequence = two
same-side attacks within 10 bars; entry against the attacks at attack₂'s
close), giving 17,036 sequences. **This frame was widened after
observing zero events — disclosed, and therefore weaker evidence than a
pre-registered frame.**

## 8. Results — every pre-declared prediction refuted

**H-NEW4 (weaker second attack should be better) — REFUTED, monotone
the wrong way:**

| bucket | n | mean | MFE/MAE | ff |
|---|---|---|---|---|
| WEAKER ≤0.75 | 1474 | −3.11 | 0.98 | 48.9% |
| EQUAL | 1707 | +0.82 | 1.08 | 49.8% |
| **STRONGER >1.25** | 1565 | **+1.72** | 1.03 | **50.4%** |

**H-NEW5 (deteriorating price result should be better) — REFUTED,
monotone the wrong way:**

| bucket | n | mean | MFE/MAE | ff |
|---|---|---|---|---|
| **NONE (no deterioration)** | 1672 | **+2.13** | 1.11 | **52.3%** |
| MODERATE | 1165 | +0.74 | 1.07 | 51.9% |
| STRONG | 641 | −3.93 | 1.07 | 50.5% |

**H-NEW9 (HIGH PRIORITY; predicted C strongest) — REFUTED:**

| state | n | mean | MFE/MAE | ff |
|---|---|---|---|---|
| **A accel + accel** | 1538 | **+3.70** | 1.12 | 50.7% |
| B accel + flat | 755 | −5.91 | 0.98 | 50.5% |
| **C accel + decel (predicted)** | 1086 | +0.93 | 1.04 | 51.1% |
| D weaken + decel | 1575 | −2.88 | 1.06 | 51.6% |

Accelerating delta with *accelerating* price — i.e. **successful**
aggression — beat the absorption state. Every cell sits at R ≈ 1 and
ordering ≈ 50%.

**H-NEW11 (relative efficiency, the generalized mechanism) — DEAD FLAT
on the largest sample in the batch (84,567 bars scored):**

| quintile | n | mean | MFE/MAE | ff |
|---|---|---|---|---|
| Q0 sell-efficient | 1766 | −0.72 | 0.98 | 47.6% |
| Q1 | 2186 | −0.25 | 1.02 | 51.0% |
| Q2 | 2284 | −0.32 | 0.97 | 49.9% |
| Q3 | 2153 | −1.50 | 0.96 | 50.1% |
| Q4 buy-efficient | 1755 | +0.45 | 0.99 | 48.6% |

No gradient in mean, geometry or ordering. **Relative buy/sell
efficiency contains no incremental directional information** — the
cleanest null in the batch, and the one with the most power behind it.

**Other studies:**

| study | n | mean | MFE/MAE | ff | note |
|---|---|---|---|---|---|
| H-NEW6 continuation | 109 | +1.06 | 1.23 | 45.9% | worse than the reversal control (1.36 / 48.3%) |
| H-NEW8 after 3m sweep | 82 | −3.18 | 1.34 | 46.3% | **no-sweep control +17.78, ff 52.6%** |
| H-NEW8 after 15m sweep | 76 | +10.09 | 1.71 | 50.0% | still below the no-sweep control |
| H-NEW14 failed-breakdown trap | 205 | +1.81 | 1.05 | 45.9% | flat; 29,298 breakdowns → 305 traps |
| H-NEW12 30s micro-pullback | 100 parents | per-parent **+21.11 vs +22.62** | — | — | median entry **1.75 pt worse**; 45/100 filled |

**H-NEW3 (FVG depth) — the one monotone relationship found, but
inverted vs. the deep-mitigation intuition:**

| bucket | n | mean | MFE/MAE | ff | ctl ΔR | ctl Δff | p | BH q(15) |
|---|---|---|---|---|---|---|---|---|
| SHALLOW + failed agg | 28 | +3.11 | **3.30** | **63.0%** | +2.27 | +12.7 | 0.451 | 0.536 |
| MIDDLE + failed agg | 28 | +20.04 | 1.63 | 60.7% | +0.50 | +7.0 | 0.158 | 0.536 |
| DEEP + failed agg | 68 | −4.16 | 1.01 | 38.2% | −0.14 | −14.1 | 0.607 | 0.607 |

Monotone in MFE/MAE and ordering (SHALLOW > MIDDLE > DEEP). But depth
*alone*, without failed aggression, is flat (R 1.02 / 0.94 / 0.97), and
SHALLOW's partitions are U +25.7 / DEV +26.4 / **IR −25.7** — a sign
reversal on n = 12. Not a survivor.

**H-NEW7 (proximity to invalidation) — REFUTED and non-monotonic:**
NEAR R 1.52 · MID R 1.10 · **FAR R 2.30** (n = 17). The prediction was
NEAR best. FAR has the batch's only raw p < 0.05 (0.0490) — but its CI
touches zero [−0.46, +69.48], BH q at M=15 is **0.536**, U partition is
negative (−1.70 on n=3), and 42% of its P&L is one trade. **A single
17-event bucket from a three-bucket study on a 131-event base is exactly
the fragile-extreme pattern the pre-registration said to distrust.**

## 9–26. Long/short, stability, tails, costs, controls

Reported per candidate above. All candidate cells are direction-split
unstable or partition-unstable; tail concentration 42–100% of total P&L
in one trade for every small-n cell. Cost sensitivity is irrelevant
where no cell survives the geometry gate. Matched controls (direction,
hour, ATR quintile, partition) show advantage only for the H3/H7 cells
whose statistics then fail.

## 27. Management for survivors

**Not run — nothing passed the raw-geometry gate.** No hypothesis was
rescued with stops, targets, trailing, breakeven or time filters.

## 28. Ranking

1. H-NEW3 (depth) — the only monotone relationship; fails on partition
   reversal and q = 0.536.
2. H-NEW7 (invalidation distance) — best raw p, refuted direction,
   fragile extreme, q = 0.536.
3. H-NEW8 (sweep) — control beats it.
4. H-NEW6 / H-NEW14 — flat.
5. H-NEW12 — honest execution wash.
6. H-NEW4 / H-NEW5 / H-NEW9 / H-NEW11 — predictions refuted or dead flat.
7. H-NEW1 / H-NEW2 / H-NEW10 / H-NEW13 / H-NEW15 — structurally undefined.

## 29. Cross-hypothesis synthesis

Three things recur and are worth stating plainly:

1. **The frozen reclaim trigger is instantaneous.** Every hypothesis
   built on a *sequence* of failures inside a location died on arithmetic,
   not on P&L. Any future work on repeated-failure mechanisms needs a
   different location frame with a longer observation window — that is a
   design lesson, not an edge.
2. **Wherever a prediction about aggression was pre-declared, the data
   said the opposite.** Weaker second attack → worse. Deteriorating
   price result → worse. Absorption state (accel+decel) → worse than
   successful aggression (accel+accel). The "trapped participants"
   intuition is not supported anywhere in this batch.
3. **The generalized mechanism is flat.** H-NEW11 tested relative
   efficiency continuously with ~2,000 events per quintile and found no
   gradient at all. When the specific versions look interesting at
   n = 17–28 and the general version is flat at n = 10,000, the specific
   versions are almost certainly noise.

The one non-overlap worth recording: **H-NEW3-SHALLOW shares zero events
with the V4.2 survivor G4-FVG.** They are independent lineages, so
G4-FVG's earlier result is neither confirmed nor contradicted here.

## 30. Frozen specification for survivors

**None.** No hypothesis in this batch is frozen, assigned a version ID,
or promoted. OFH13_PROSPECTIVE_V1 is unchanged.

## Verdicts

| hypothesis | verdict |
|---|---|
| H-NEW1 persistent failed aggression | **INSUFFICIENT DATA** (0 events, structural) |
| H-NEW2 failure speed | **INSUFFICIENT DATA** (no variance) |
| H-NEW3 FVG depth | **INTERESTING MECHANISM — NEEDS MORE DATA** |
| H-NEW4 weakening second attack | **NO INCREMENTAL VALUE** (refuted, inverted) |
| H-NEW5 deteriorating price result | **NO INCREMENTAL VALUE** (refuted, inverted) |
| H-NEW6 failed flow → continuation | **NO INCREMENTAL VALUE** (below reversal control) |
| H-NEW7 invalidation proximity | **INTERESTING MECHANISM — NEEDS MORE DATA** (direction refuted) |
| H-NEW8 sweep before failure | **NO INCREMENTAL VALUE** (control is better) |
| H-NEW9 delta accel × price decel | **NO INCREMENTAL VALUE** (prediction refuted) |
| H-NEW10 efficiency flip | **INSUFFICIENT DATA** (2 events) |
| H-NEW11 relative efficiency | **NO INCREMENTAL VALUE** (flat, large sample) |
| H-NEW12 30s micro-pullback | **EXECUTION IMPROVEMENT ONLY** — and it isn't one (−1.51 per parent) |
| H-NEW13 quality score | **INSUFFICIENT DATA** (dimensions degenerate) |
| H-NEW14 failed-breakdown trap | **POOR ENTRY GEOMETRY** |
| H-NEW15 time under pressure | **INSUFFICIENT DATA** (no variance) |

### DID THIS BATCH IDENTIFY ANY NEW REPEATABLE ENTRY-LOCATION ASYMMETRY BEYOND THE EXISTING OFH13 FAMILY?

**NO.**

### WHICH MECHANISM CURRENTLY LOOKS MOST INFORMATIVE?

**NONE** — within this batch. The two candidates that produced any
signal (FVG depth, invalidation distance) fail on partition stability,
tail concentration and family-wise correction, and both are contradicted
by the flat large-sample generalization of the same idea. The only thing
this batch adds to the programme's knowledge is negative and useful: the
absorption / trapped-aggression family of intuitions does not survive
mechanical testing on this dataset, in any of the eleven forms tried.
