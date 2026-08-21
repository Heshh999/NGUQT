# Unseen-Window Evaluation: 2025-08-18 → 2025-11-01

**Date:** 2026-08-21
**Script:** `analysis/v41/oos_aug.py`. Output: scratchpad `oos_aug_out.txt`.
**New capture:** 2025-08-18 → 2025-11-28, 100,768 bars, 74 session days.
Order-flow audit PASSED (100% level coverage, 0.000% bid/ask mismatch, 0
off-grid bars, 1 unexplained gap ≥5m). Volume-profile audit PASSED.

## Integrity check performed before any analysis

The new capture overlaps the existing one for **26,488 November bars**.
Those bars are **byte-identical** on price, volume, bid/ask, delta and
every order-flow column. Differences exist only in:

- `f_atr` — 19 bars (warm-up; the new run has more history behind it)
- `f_profileVah` / `f_profileVal` / `f_profilePoc` — 961 / 630 / 6 bars,
  1–2 ticks, value-area tie-breaking when adjacent levels hold equal
  volume.

Same merge policy, same session template, same engine. Splicing is safe.
**No shelved hypothesis reads profile columns**, so the tie-break
differences do not touch any result below.

## What this window is, and is not

Everything before 2025-11-02 was never touched by any rule, threshold or
design decision in this repository: every DEV quantile was fit on
2025-11 → 2026-03 and every hypothesis was designed while looking at
2025-11 → 2026-08. **It is a genuine unseen holdout.**

It is **not prospective validation**. It is *earlier* data, so a regime
difference is a live alternative explanation for anything that fails
here, and success cannot rule out that a rule suits 2025–26 markets
generally. Only 2026-09+ months can do that.

Window: 74,260 bars, 65 calendar days, 16,074 eligible entry bars,
**169 frozen OFH6 signals**. Side-matched 60m baseline: long −1.645,
short +1.645.

---

## Results — nothing refit, every threshold the original frozen value

| | n | exc UNSEEN | exc SEEN | ff1 UNSEEN | ff1 SEEN | p | BH q (M=9) |
|---|---|---|---|---|---|---|---|
| **OFH6** | 169 | **−1.48** | +8.19 | 50.3 | 48.1 | .612 | .612 |
| G1 (limit −0.5 ATR) | 150 | +0.51 | +10.66 | 48.0 | 52.6 | .381 | .571 |
| G2 (limit −1.0 ATR) | 130 | −0.86 | +9.63 | 47.7 | 54.7 | .511 | .612 |
| G4 attack-failure | 36 | +13.42 | +14.65 | 55.6 | 41.4 | .133 | .387 |
| G6 stacked-go | 169 | +1.94 | +6.67 | 52.1 | 46.5 | .332 | .571 |
| N3 absorption | 5 | −6.92 | +15.48 | — | 52.5 | .560 | .612 |
| N6 impulse-pullback | 141 | +4.83 | +6.49 | 52.1 | 48.9 | .172 | .387 |
| **OFH13** | **16** | **+38.39** | +19.19 | **75.0** | 46.2 | **.0013** | **.0117** |
| OFH14 | 70 | +14.48 | +8.43 | 54.3 | 49.2 | .100 | .387 |

## The headline: OFH6 did not replicate

**OFH6 scored −1.48 pt/trade on data it had never seen, against +8.19 on
the window it was discovered in.** p = 0.61; the CI [−11.33, +8.56] is
centred near zero. Month by month: −17.4 (Aug), +9.8 (Sep), −5.2 (Oct).

This is the outcome the whole ten-month protocol was built to detect, and
it matters more than any single hypothesis. OFH6 was already only
family-wise p = 0.129 and stop-dependent; it is now a rule that failed
its first genuine unseen test. Everything built on OFH6 as a *directional
context* inherits that: G1, G2 and G6 all lose most of their edge here,
and G1/G2 lose the >50% favourable-first ordering that was their entire
claim (52.6/54.7 → 48.0/47.7).

**One thing about G1 did survive, and it is worth keeping.** The
limit-entry discount improved on immediate entry in *both* windows:

| | OFH6 immediate | G1 per-signal (unfilled = 0) | fill rate |
|---|---|---|---|
| seen window | +8.19 | +8.69 | 89% |
| **unseen window** | **−2.35** | **−0.32** | **89%** |

The execution mechanism is real and replicates (+0.50 and +2.03 pt per
signal). It just cannot rescue a signal whose drift is not there. That
is a clean separation of two effects that were confounded before.

## The one genuine positive — and the size of its asterisk

**OFH13 (FVG mitigation + opposing order-flow failure) scored +38.39
pt/trade on unseen data with p = 0.0013 and BH q = 0.0117 across the
nine hypotheses tested here.** Its day-clustered CI [+18.13, +66.02]
excludes zero. All three months positive and rising (+15.1, +34.7,
+47.7). Median trade +26.03. Favourable-first 75.0% — the first
meaningful ordering result anywhere in this programme.

The asterisk: **n = 16.** Sixteen trades over 65 days. And its
favourable-first swung 46.2 → 75.0 between windows, which is itself more
consistent with small-sample variation than with a stable property. A
16-trade sample can produce this by luck even at p = 0.0013, and the
effect size (+38 pt/trade) is implausibly large for anything real in
this market.

What makes it worth taking seriously despite that: OFH13 was **frozen
before this data existed**, so this is a correctly structured
confirmatory test of a pre-selected hypothesis, not another search. And
OFH14 — the same FVG machinery without the flow-failure filter, n = 70 —
also improved on unseen data (+14.48 vs +8.43, ff1 54.3, p = 0.10). The
two point the same way.

There is also a tension worth stating plainly: **OFH13 and OFH14 both
require OFH6 context, yet they improved while OFH6 itself failed.** The
most economical reading is that the FVG-mitigation and flow-failure
components are doing the work and the OFH6 gate is close to inert. That
is a hypothesis about the result, not a finding — and per standing
practice it is recorded, not acted on.

## Ledger update

- Order-flow history is now **2025-08-18 → 2026-08-19**, ~12 months.
- The Aug-18 → Nov-1 window is **now SPENT** as a holdout — used here.
- Remaining unspent: **capture months from 2026-09 onward.**
- Structure HOLD (2024-07 →) still sealed, untouched by any of this.

## Status changes

| | before | after |
|---|---|---|
| OFH6 | shelved, unproven | **failed an unseen test** |
| G1 | primary candidate | drift gone; entry mechanism replicates |
| G2 | companion | failed |
| G4, G6, N6 | secondary | sign held, none significant |
| N3 | candidate | n=5 here — no information |
| **OFH13** | interesting/inconclusive | **strongest candidate; BH q 0.012 on unseen data, n=16** |
| OFH14 | poor geometry | improved on unseen data, n=70 |

The right next step is not another hypothesis. It is more data: if
further backward months exist (2025-08 and earlier), they would let
OFH13's n grow from 16 toward something that can actually be judged.
Failing that, 2026-09+ forward months.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
