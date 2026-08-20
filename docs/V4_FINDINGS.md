# V4 STRUCTURE RESEARCH - FINDINGS OF RECORD

Frozen 2026-08-20. Companion to `docs/V4_PREREGISTRATION.md` (frozen 2026-08-19,
before any feature/outcome relationship was examined).

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

---

## 0. DATA AND SCOPE

| | |
|---|---|
| Instrument | MNQ only, $2 per index point per contract |
| Structure capture | 2019-09 -> 2026-08, 196,799 break events |
| Order-flow capture | 2025-11-02 -> 2026-08-18, 279,834 volumetric 1m bars, 249 session days |
| Timeframes | Daily / 4h / 60m / 15m / 5m / 3m / 1m |
| Entry probes | 587,448 triggered, 60 HTF->LTF configurations |
| Splits | DEV 2019-09..2022-12, VAL 2023-01..2024-12, OOS 2025-01..2026-08 |

Order-flow history begins 2025-11 and therefore sits **entirely inside OOS**. It
was never available to inform any structure hypothesis; it can only be tested as
an incremental filter, never as a discovery set.

---

## 1. PHASE 0 AUDIT

| Check | Verdict | Evidence |
|---|---|---|
| Data quality | PASS | 100.00% level coverage, 0 bars without levels, 0 zero-volume bars, 0 off-grid price levels |
| Aggregation | PASS | HTF bars reconstruct from 1m within tick tolerance |
| No lookahead | PASS | 0 violations across 196,799 rows on all three causal timestamps |
| Event independence | NEEDS WORK | 7.4x clustering at 60m; day-block bootstrap used throughout to absorb it |
| Cost model | NEEDS WORK | 1.5 pt round turn is an **assumption**, not a measurement. Stated as such in pre-registration. Not derived from fills, because this project has no fills. |
| OOS / lockbox | PASS | OOS untouched until the frozen family was run |
| Research pipeline | PASS | Modules submit no orders; capture is completed-bars only |

Bid/ask classification: `|ask + bid - volume| > 1%` on **0 bars**; mean absolute
mismatch 0.000%; worst single bar 0.000%.

Gaps: 4 unexplained gaps >= 5m outside the 16:15-16:30 and 17:00-18:00 ET halts,
plus 1 quiet minute (< 5m). NinjaTrader prints no bar when nothing trades, so a
quiet minute is not missing data and is counted separately.

---

## 2. BASE RATES BY TIMEFRAME

Primary metric: `net_240m / tfAtr`, in index points per contract, after the
assumed 1.5 pt cost. Point estimate is the **pooled mean**; standard error is a
day-block bootstrap (2,000 resamples).

| TF | mean (pt) | t | median (pt) | win rate |
|---|---|---|---|---|
| 4h | +0.186 | +0.06 | -0.25 | 50.4% |
| 60m | -0.359 | -0.27 | -0.25 | 49.9% |
| 15m | -0.329 | -0.54 | -0.25 | 49.9% |
| 5m | -0.356 | -1.03 | -0.25 | 49.6% |
| 3m | -0.019 | -0.07 | -0.25 | 49.4% |
| ALL | -0.167 | -0.55 | -0.25 | 49.4-50.4% |

Every timeframe's median outcome is **-0.25 pt: exactly one tick**. A structure
break, on its own, is a coin flip that pays the spread.

---

## 3. THE FROZEN FAMILY (VAL + OOS, fresh data)

All eight pre-registered hypotheses, reported complete - the ones that worked and
the ones that did not.

| # | Hypothesis | effect | t | direction |
|---|---|---|---|---|
| H7 | Failed breaks reverse | -0.4361 | -5.95 | WRONG |
| H6 | Displacement breaks continue | +0.0743 | +1.61 | WRONG |
| H5 | Structural alignment helps | +0.1021 | +1.52 | as predicted |
| H8 | Break at location | -0.0295 | -0.52 | as predicted |
| H2 | HTF context filter | -0.0087 | -0.40 | WRONG |
| H1 | Continuation after BOS | -0.0465 | -0.38 | WRONG |
| H4 | Momentum persistence | +0.0196 | +0.35 | as predicted |
| H3 | Range expansion | -0.0391 | -0.25 | WRONG |

Multiple-hypothesis control: Benjamini-Hochberg, q = 0.05, across the full
declared family of 8.

**0 of 8 survive in the predicted direction.**

H7 is the only result that clears significance, and it clears it pointing the
**wrong way** by a wide margin (t = -5.95). Failed breaks do not reverse - they
keep losing. That is a real, replicated, out-of-sample finding, and it is the
opposite of the hypothesis.

---

## 4. ENTRY RESOLUTION

60 HTF->LTF configurations x IMMEDIATE / PULLBACK / RETEST triggers, 587,448
triggered probes.

| | net R |
|---|---|
| Best: 4h -> 15m, IMMEDIATE, 1R | -0.0440 |
| Worst: 3m -> 1m, PULLBACK, 2R | -0.3992 |

**0 of 60 configurations produced positive net R.**

The decisive test - because it removes the one number that was assumed rather
than measured:

| Gross (zero cost) | mean R | t |
|---|---|---|
| 1R target | -0.0094 | -3.18 |
| 2R target | -0.0186 | -4.02 |

**Gross expectancy is negative before a single tick of cost.** The cost model
being an assumption no longer matters. Setting cost to zero does not rescue the
edge; the edge is negative on its own terms.

---

## 5. ORDER FLOW AS AN INCREMENTAL FILTER

21,071 breaks joined to volumetric data, 247 session days, entirely inside OOS.
Six features tested, including the absorption test.

| | |
|---|---|
| Max abs t across 6 features | 0.89 |
| Absorption test | t = +0.28 |

Order flow adds nothing to structure. This is a clean result: the data-quality
gate PASSED at 100% coverage, so this is a genuine null, not a measurement
failure. There was nothing wrong with the microscope.

---

## 6. FAILURE CLASSIFICATION

Case A (edge exists, execution/cost kills it) is **ruled out** by section 4:
gross is negative, so there is no edge for cost to kill.

The result is Case D territory: the hypothesis class itself does not carry an
edge on this instrument over this period.

---

## 7. FINAL DECISION

**D. NO ROBUST EDGE SURVIVED.**

Stronger than the plain reading of D, because gross expectancy is negative. This
is not "the edge was too small to pay costs." This is "there was no edge."

What this does not say: it does not say structure is meaningless, or that some
different formulation could not work. It says **this** formulation - these swing
definitions, these break classifications, these outcome windows, these entry
resolutions, on MNQ over 2019-2026 - carries no exploitable directional
information, and the order-flow overlay does not change that.

---

## 8. TWO CORRECTIONS MADE DURING ANALYSIS

Recorded because both changed the reported answer.

**Estimator.** Mean-of-daily-means gave 60m = **+7.12 pt, t = +4.63**. That
number was reported before the error was caught and is hereby retracted. It was
produced by a combined figure sitting above *both* directional subgroups -
Simpson's paradox from unequal daily event counts. The pooled mean for the same
cell is **-0.36 pt**. All numbers in this document use the pooled mean as point
estimate with day-block bootstrap for the standard error.

**Validity filter.** The primary metric `net_240m / tfAtr` exploded where
`tfAtr` fell below one tick. 142 rows - 0.078% of the dataset - carried a y-sum
of -17,546 against a dataset total of -16,199. A single-digit fraction of a
percent of rows was dominating the entire result. `MINATR = 1.0` now filters
them.

---

## REPRODUCTION

- `analysis/lib.py` - loading, validity filter, winsorisation, split
- `analysis/lib2.py` - pooled-mean point estimate, day-block bootstrap SE
- `docs/V4_PREREGISTRATION.md` - the frozen hypotheses, dated before analysis

Bar delta is recomputed from per-price ask/bid volumes in the same file, not read
from the platform, so every delta column can be rederived from the columns beside
it. Cumulative delta resets at the CME exchange day boundary (18:00 ET), stated
here and applied in code rather than inherited from an indicator setting that
could differ between historical and real-time calculation.

---

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
