# Working Inside Ten Months of Order Flow

**Date:** 2026-08-21
**Scripts:** `analysis/v41/power10.py`, `power10b.py`, `ofh6_final.py`
**Window:** 2025-11-02 .. 2026-08-19, 53,914 eligible RTH bars,
**205 sessions**, 10 months. This is the whole asset and will stay so.

The question is not whether ten months is enough. It is fixed. The
question is what ten months can certify, and what protocol extracts the
most evidence from it.

---

## Two corrections to earlier results in this repo

Both changed the answer, so they are recorded before anything else.

**1. The minimum-detectable-edge table in `power10.py` was wrong by ~6x.**
I measured day-clustering inflation on the full 53,914-bar eligible set -
where each session contributes ~260 heavily overlapping observations -
and then applied that x7.50 factor to trade sets of ~800. A rule taking
~4 trades a day has nothing like that overlap. The printed MDE of 68
pt/trade was an artifact. Measured empirically, the SE at OFH6's actual
trade set is **3.98 pt**, giving MDE ~11 pt/trade.

**2. The within-day shuffle used in `ofh.py` / `ofh2.py` is the wrong
null for a directional claim, and it was not null.** Permuting returns
inside a day leaves the day's own direction intact and hands it to the
control for free. A rule that is long on up-days then scores well under
the "null" because the null already knows which days were up-days - that
is future information leaking into the control. It is why the noise
median came out at +11.6 pt, which should have been the tell.

The correct null for a directional claim is a **sign-flip**: same bars,
same times, same trade count, direction randomised, flipped by day so
within-day correlation survives. Expectation is exactly zero by
construction.

**Under the correct null, OFH6's family-wise p is 0.129, not 0.688.**
That is a near-miss, not a noise-consistent curiosity, and my previous
report of it was wrong. The related claim that the top-5% outlier test
"killed" OFH6 was also over-applied: OFH6 has a positive *median* trade
(+5.9 / +5.1 pt) and a 52% win rate, which is a central-tendency shift,
not the lottery-ticket profile that disqualified structure decile-1.

---

## What 205 sessions can resolve

| trades | SE (pt) | MDE pt/trade | MDE $/trade |
|---|---|---|---|
| 200 | 6.68 | 18.70 | 37.40 |
| 800 | 2.97 | 8.32 | 16.64 |
| 3,200 | 1.67 | 4.66 | 9.32 |
| 12,800 | 0.77 | 2.15 | 4.30 |

That table assigns each drawn trade a random side, so trades inside a day
partly cancel. A real rule holds one side most of the day. The measured
sign-flip SE for the **actual** OFH6 trade set is **3.979** at n=783 -
34% above the table - so its true single-hypothesis MDE is **11.1
pt/trade**.

**OFH6 measures +8.3 pt. It is below its own detection threshold.** To
resolve an effect that size the SE must reach ~2.96, needing about
**1.8x this window - roughly 18 months.**

## The binding constraint is SEARCH WIDTH, not sample size

| statistic | p |
|---|---|
| OFH6 alone, sign-flip null | **0.019** |
| best-of-nine family, same null | **0.129** |

Same data, same effect. The entire difference is that I searched nine
hypotheses. **On a short window, every extra hypothesis tested is paid
for out of the same fixed evidence budget.** This is the single most
actionable fact in the document: with ten months, testing one
pre-registered idea buys ~7x the statistical credit of testing nine.

## OFH6 under realistic management - where it fails

| management | excess pt | sign-flip p | median MAE | p95 MAE |
|---|---|---|---|---|
| no stop, 90m exit | +9.73 | 0.038 | 66.2 | 228.8 |
| no stop, 60m exit | +8.30 | 0.021 | 57.0 | 198.5 |
| 3.0 ATR stop, 60m | +3.77 | 0.129 | 48.2 | 120.0 |
| 1.5 ATR stop, 90m | +2.87 | 0.086 | 32.8 | 78.0 |
| 1.0 ATR stop, 60m | +0.35 | 0.135 | 25.0 | 56.0 |

**The edge exists only without a stop.** Add any stop and the excess
collapses by 60-96% and every p-value fails. The mechanism is visible in
the MAE column: these trades routinely go deep against the position and
recover by the time exit. Median adverse excursion is 57 points ($114 per
contract); the 95th percentile is 198 points (**$397 per contract**).

Daily series, one MNQ contract, best variant: total $+13,868 over 193
sessions, **max drawdown $3,732**. On a $1,000 account that drawdown is
3.7x the account. The rule is not holdable at that size even if the edge
were proven - and it is not proven.

## Verdict on OFH6

**Not proven, not tradable, not dead.** Family-wise p = 0.129 in the only
form that shows an effect (no stop), and that form carries $397
95th-percentile adverse excursions. It stays on the shelf.

## The protocol for the next ten months of work

1. **One pre-registered hypothesis at a time.** Search width costs more
   than anything else here. Write the rule, direction, threshold,
   management and stopping criterion down *before* touching the data.
2. **Sign-flip null, flipped by day.** Never the within-day shuffle for a
   directional claim - it leaks the day's direction into the control.
3. **Excess over side-matched, split-matched baseline.** The window's own
   drift (+3.4 pt/hour long in VAL) will otherwise pose as edge.
4. **Only hunt edges above ~11 pt/trade.** Anything smaller is
   undetectable in this window, and claiming it would be dishonest.
5. **Score with a stop from the start.** A no-stop result is not a
   tradable result, and testing it first avoids exactly the dead end
   above.
6. **Raise trade count, not hypothesis count.** Going from 800 to 3,200
   trades cuts the MDE roughly in half; testing four more ideas raises
   the bar instead of lowering it.
7. **The window grows one month per month.** Months after 2026-08 are
   genuine out-of-sample for everything here. The cheapest real evidence
   available is to freeze one rule now and score it forward.
