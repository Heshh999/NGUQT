# Autopsy — Why the Best Five Lose, and What Actually Helps

Date 2026-08-21. Asked: take the top five, find what made them lose,
and test whether better stops / R:R / longer holds / confluences
repair them. Scripts: analysis/v41/autopsy.py (+ exact-race check).
HOLD (2024-07 onward) NOT read.

## 1. What actually kills these trades

Loss anatomy, all five hypotheses, consistent across both splits:

| | share of all losing trades |
|---|---|
| never worked (MFE < 0.5R) | 20–35% |
| **reached +1R, then gave it back** | **40–65%** |
| middling | 17–26% |

And winner MFE capture — how much of the favourable move the exit
actually banked:

| horizon | winner MFE captured (median) |
|---|---|
| 60 min | **28–46%** |
| 240 min | **61–70%** |

**The dominant loss mode is giving back a move that already worked**,
and at the 60-minute horizon the winners were being cut off less than
halfway through their own favourable excursion.

## 2. The finding that IS real: the horizon was wrong, not the stop

Moving 60m → 240m, stop unchanged at 1.5 ATR:

| id | DEV 60m | DEV 240m | VAL 60m | VAL 240m |
|---|---|---|---|---|
| N7 | −6.66 | **+2.46** | −12.71 | −2.84 |
| N2 | −11.48 | −2.70 | −9.91 | −3.18 |
| N6 | −11.40 | −1.17 | −9.47 | **+1.70** |
| N12 | −9.73 | **+0.87** | −8.34 | **+0.81** |
| N9 | −9.88 | **+0.55** | −8.57 | −1.01 |

Every hypothesis improves by 6–12 points per trade. This is the one
genuine, robust improvement in the whole autopsy: **these events need
four hours, not one.** 240m is the longest horizon the capture
records, so the true optimum may be longer still — that is measurable
only with a re-capture at longer horizons.

## 3. A wrong answer I caught before reporting it

My first management simulation used `minsToMaxMfe < minsToMaxMae` as
an ordering proxy for "did +1R come before the stop?" It produced
spectacular results — breakeven-after-1R and trail-at-1R turning
**every** hypothesis positive in both splits, N7 at +17.9 / +14.3.

That was an artifact. MFE and MAE timestamps mark the *extremes*, not
the first touch of a level, so the proxy systematically mis-assigns
which came first. The engine already resolves this exactly, bar by
bar, in its race grid. Checked against it:

| N12 rule | proxy said | **exact race** |
|---|---|---|
| exit at 1R | +9.12 / +8.59 | **+0.02 / −0.22** |
| exit at 1.5R | — | +0.12 / +0.06 |
| exit at 2R | — | +0.37 / +0.14 |
| hold 240m, no stop | +0.43 / +0.04 | **+0.89 / +0.57** |

| N6 rule | exact race |
|---|---|
| exit at 1R | −0.34 / −0.27 |
| exit at 2R | +0.39 / +0.03 |
| hold 240m, no stop | +3.53 / +2.81 |

**Early exits are worse than holding, not better.** The exact race
says the 1R target is reached before the stop only ~47% of the time;
capping winners there truncates the right tail while keeping every
loser. The MFE data made it look free because MFE cannot tell you
ordering. The proxy overstated trail-at-1R by roughly 400x.

The correct reading of §1 is therefore: yes, 40–65% of losers gave
back a +1R move — but you cannot harvest that, because you cannot
know in advance which ones will give it back, and the trades that
*don't* give it back are the ones paying for everything else.

## 4. Confluences — 35 cells, and the noise floor

Seven pre-declared conditions × the five hypotheses. Nine cells came
back positive in both splits, including some that look striking
(N6 + high relative volume: +6.68 / +6.60; N12 + RTH only:
+5.34 / +2.87).

Then the same 35-cell scan on within-day-shuffled outcomes:

| | cells positive in BOTH splits |
|---|---|
| real data | **9** |
| shuffled | median **7**, p90 **12**, max 17 |

**Nine is between the median and the p90 of pure noise.** The
confluence scan found nothing that a random relabelling of outcomes
does not also produce. Individually striking cells (n=118 for the
best one) are exactly what that distribution predicts.

## 5. What survives, and what it is

Only two things are positive in both splits without a fragile
neighbouring cell: N12 and N6 held 240m. N12 was already dissected —
long side +2.47/+2.82, short side −1.61/−2.22 against an
unconditional long baseline of −0.21/+1.03: **market drift, not
information.** N6 (n=729) sign-flips to −2.26/−1.59 one stop-cell
over, which is fragility by the project's own standard.

## Answer

- **What made them lose**: no location advantage (excursion ratios
  0.94–1.11), so cost decides — compounded by a 60-minute horizon
  that cut winners off at a third of their favourable move.
- **Better stop?** No. The stop-family study already showed the whole
  spread across eight stops is smaller than the commission, and the
  exact-race check kills breakeven and trailing too.
- **Better R:R?** No. Exiting at 1R/1.5R/2R all underperform simply
  holding, because early exits truncate the tail that pays.
- **Hold longer?** **Yes — this is real and it is the one thing that
  helped**, worth 6–12 points per trade across all five. It is not
  enough to make any of them a strategy, but it is a genuine property
  of the event class and should be carried into any future design.
- **Confluences?** No. Nine of 35 against a noise median of seven.
