# OFH6 Destruction Battery

**Rule frozen:** 2026-08-21, `analysis/v41/ofh6_spec.py`, threshold
hardcoded at |dsum15| >= 3380.0. No test below may alter it.
**Script:** `analysis/v41/ofh6_destruct.py`
**Evidence base:** all ten months treated as research evidence, not
pristine OOS. 783 trades, 193 sessions, 42 trading weeks.

Scored against the decision criteria set out before the tests were run.

| criterion | result | verdict |
|---|---|---|
| positive net across most months | 8 of 10 months | **PASS** |
| longs and shorts both positive | +9.27 (p=0.039) / +7.51 (p=0.144) | **PASS** |
| broad threshold stability | plateau 3380-4732; cooldown stable 5-60 min | **PASS** |
| costs survived | all figures net of 0.87 pt | **PASS** |
| corrected significance respectable | FWE 0.121, BH q 0.180 | **MARGINAL** |
| **MFE materially greater than MAE** | **ratio 1.026; fav-first 44.6-48.7%** | **FAIL** |

---

## 1. P&L concentration (diagnostic)

Total net +5,818.7 pt. Median trade **+3.96 pt**, win rate **52.9%**.

| slice | trades | net pt | share of total net |
|---|---|---|---|
| top 1% | 7 | +3,308 | **56.9%** |
| top 5% | 39 | +10,158 | **174.6%** |
| top 10% | 78 | +15,806 | 271.6% |

Both things are true and they matter equally. The median trade is
positive and 53% of trades win, so the centre of the distribution does
carry weight - the "three trades made the backtest" failure mode does not
apply. But the top 5% producing 175% of total net means **the other 95%
of trades lose -5.83 pt/trade in aggregate**. The distribution is
fat-tailed on both sides: many small wins, a heavier tail of large
losses, and an extreme tail of very large wins that overturns them.

## 2. Blocked stability

8 of 10 months positive; only 2026-02 is individually significant
(p=0.011). Losing months: 2025-12 (-6.42), 2026-05 (-3.04).

Longs +9.27 pt (p=0.039), shorts +7.51 pt (p=0.144). Both positive -
the effect is not a disguised long bias on a rising window.

**Weeks do not carry it.** 28 of 42 weeks positive. Dropping the best
single week removes 13.0% of total excess and the remaining 765 trades
still average +7.39. Dropping the best three removes 35.5%, remainder
still +5.79. This is the healthiest result in the battery.

## 3. Multiple-testing correction over the twelve searched

OFH6 was hypothesis #6 of 12 and was selected because it scored best. It
is not treated as #1 anywhere.

| | value |
|---|---|
| OFH6 raw sign-flip p | 0.0150 |
| **max-statistic family-wise p** | **0.1212** |
| Bonferroni (M=12) | 0.1800 |
| Benjamini-Hochberg q (M=12) | 0.1800 |

No corrected measure clears 0.05. The max-statistic figure is the right
one - it accounts for correlation between the twelve - and it is the most
favourable of the three at 0.121.

## 4. Threshold neighbourhood - a genuine plateau

| threshold | trades | excess | p |
|---|---|---|---|
| 2,028 | 1,345 | -0.28 | 0.549 |
| 2,704 | 1,045 | +1.51 | 0.308 |
| 3,042 | 900 | +3.76 | 0.141 |
| **3,380 (frozen)** | **783** | **+8.30** | **0.014** |
| 3,718 | 674 | +9.70 | 0.021 |
| 4,056 | 585 | +8.19 | 0.058 |
| 4,394 | 484 | +7.67 | 0.111 |
| 4,732 | 410 | +10.36 | 0.082 |

The frozen value is not a spike - everything at or above it sits in
+7.7 to +10.4, and the rise below it is monotone. Cooldown is equally
stable: +8.04 / +6.59 / +7.18 / +8.30 / +5.31 / +7.93 at 5/10/15/30/45/60
minutes. This passes cleanly.

## 5. Matched controls - delta direction is real; the threshold is half the story

| set | n | excess | 95% CI |
|---|---|---|---|
| OFH6 (above threshold) | 783 | +8.30 | [+1.18, +16.52] |
| matched sub-threshold controls | 783 | +4.73 | [-3.25, +12.65] |
| 15-bar PRICE momentum, matched n | 780 | +0.09 | [-7.82, +8.87] |

Controls matched on ATR quintile x relVolume quintile x 90-minute RTH
block, trading the same delta-sign rule on bars that did *not* cross the
threshold.

Two readings, both worth keeping:

- **Cumulative delta is not a volatility proxy.** Price momentum over the
  same 15 bars, same cooldown, same trade count, earns +0.09 pt against
  OFH6's +8.30, with only 25% signal overlap. The information is in the
  order flow, not in the price path.
- **But the threshold carries less than half the effect.** Volatility-,
  volume- and time-matched bars below the threshold still earn +4.73.
  The gap attributable to delta *magnitude* is only +3.57 pt.

## 6. Excursion asymmetry and favourable-first ordering - THE DECISIVE TEST

Exact first-touch races on the 1-minute path. No proxy.

| horizon | med MFE | med MAE | ratio |
|---|---|---|---|
| 60m | 58.50 pt (2.67 ATR) | 57.00 pt (2.83 ATR) | **1.026** |
| 90m | 71.50 pt (3.25 ATR) | 66.25 pt (3.12 ATR) | **1.079** |

| X (ATR) | resolved | reached +X first | sign-flip null | p |
|---|---|---|---|---|
| 0.5 | 783 | 44.6% | 45.3% | 0.690 |
| 1.0 | 783 | 47.8% | 49.6% | 0.869 |
| 1.5 | 783 | 48.3% | 49.9% | 0.849 |
| 2.0 | 776 | 48.6% | 50.0% | 0.821 |
| 3.0 | 715 | 48.7% | 49.9% | 0.748 |

**OFH6 has no ordering edge.** Every favourable-first rate is below 50%
and below its own sign-flip null. Excursions are symmetric to within 3-8%.
This is the same wall every other hypothesis in this programme hit, and
it is the criterion that was designated decisive.

## 7. Stop x target family - no plateau

Net pt/trade after cost, excess over baseline:

| stop \ target | 1.0R | 1.5R | 2.0R | 3.0R | none |
|---|---|---|---|---|---|
| 1.0 ATR | -1.87 | -2.18 | -2.01 | -3.27 | +0.02 |
| 1.5 ATR | -1.35 | -1.94 | -2.25 | -3.13 | +2.00 |
| 2.0 ATR | -1.47 | -1.37 | -1.87 | -2.26 | +2.76 |
| 2.5 ATR | -1.74 | -1.83 | -2.39 | -3.26 | +2.27 |
| 3.0 ATR | -1.13 | -1.12 | -1.16 | -1.72 | +4.44 |
| 4.0 ATR | +0.52 | +1.11 | +1.51 | +0.60 | +6.26 |

10 of 30 cells positive, and they are not a payoff region - they are the
**no-target column plus the widest-stop row**. Every cell with a target
and a stop tighter than 4 ATR (~80 pt) is negative. This is section 6
expressed in money: with symmetric excursions there is no geometry that
converts the drift into a stopped, targeted trade.

---

## Verdict

**OFH6 does not qualify for R:R and management research.**

Five of six criteria pass, several handsomely - the week-drop test, the
threshold plateau, the long/short split and the price-momentum competitor
are all genuinely good results, and they establish something real:
**cumulative delta direction carries information that price momentum does
not.** That finding stands and is worth keeping.

But the decisive criterion fails, and it fails cleanly. There is no
excursion asymmetry, no favourable-first ordering, and consequently no
stop/target plateau. OFH6's positive expectancy is entirely an artifact
of a fixed time exit absorbing a small directional drift while sitting
through symmetric path risk - median adverse excursion 57 pt, 95th
percentile 198 pt ($397/contract). At $1,000 of capital that is
unholdable regardless of whether the drift is real.

Corrected significance (FWE 0.121) does not clear 0.05 either, so the
drift itself is not established - only unrefuted.

## Status

**OFH6 - internally replicated over the available ten months; NOT
externally validated; NOT tradable as a stopped strategy.** Frozen and
shelved, not deleted.

Per the standing protocol: from this point every newly captured
order-flow day is true prospective validation. OFH6 is not to be modified
on the basis of those trades. What a forward score can settle is whether
the drift persists; it cannot rescue the missing excursion asymmetry,
which is a property of the path and is already measured.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
