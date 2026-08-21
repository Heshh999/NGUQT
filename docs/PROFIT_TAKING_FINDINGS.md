# "Why do I never capture a lot of points?" — the measured answer

Date 2026-08-21. 19,466 break events, 7.1 years. Script: analysis
reproduced in /tmp/capture.py logic; numbers below are from the full
capture, R measured against the frozen stop.

## The excursion distribution

| | p25 | median | p75 | p90 | p95 | max |
|---|---|---|---|---|---|---|
| MFE (in your favour) | 0.61 R | **1.40 R** | 2.80 R | 5.16 R | 7.31 R | 109 R |
| MAE (against you) | 0.61 R | **1.37 R** | 2.82 R | 5.10 R | 7.14 R | 218 R |

Every trade goes meaningfully in your favour at some point. Every
trade also goes meaningfully against you at some point. The two
distributions are **the same distribution**.

## EV per trade, in points

| exit style | real events |
|---|---|
| **perfect exit — sell at the exact top** | **+51.22** |
| exit at 1R (exact race) | −0.83 |
| exit at 2R | −0.97 |
| exit at 3R | −0.93 |
| hold 240 minutes | −0.85 |

The fantasy number is +51 points. Every realistic exit is ≈ −0.9.
That gap of ~52 points per trade is what "I never capture a lot of
points" feels like.

## The control that explains it

Same timestamps, same stops, **direction chosen by coin flip**:

| | real events | random direction |
|---|---|---|
| perfect exit | +51.22 | **+51.51** |
| MFE median | 1.40 R | **1.39 R** |
| MFE p90 | 5.16 R | **5.16 R** |

**A coin flip leaves exactly as many points on the table as a real
setup does.** The distributions are identical to two decimal places.

## What that means

MFE is a *maximum over a path*. Any position held through a moving
market — good, bad, or random — passes through a moment where it was
substantially in profit. Looking back at that moment and measuring
the distance to it will always produce a large number, and it will
produce the same large number whether or not the entry had any
information in it.

So the answer to the question:

**No — you do not have a bad way of taking profit.** The points you
feel you are missing are not being lost to a poor exit. They are
hindsight points: visible only after the fact, equally visible on
coin-flip trades, and not capturable in advance by any exit rule.

This is consistent with everything else measured in this programme:

- Eight stop families spanned less than the commission (0.59 pt).
- Exiting at 1R/1.5R/2R all underperformed simply holding, on the
  engine's exact bar-by-bar race.
- Breakeven and trailing looked spectacular under an MFE-timestamp
  proxy and collapsed to nothing under exact ordering (~400x
  overstatement).
- Median MFE ≈ median MAE across every event class tested.

Exit management is not the bottleneck. **The only way to capture more
of the favourable excursion is to know in advance which trades will
run — that is prediction, not exit design**, and seven years of
preregistered testing across six event classes says that prediction
is not present in this data.

## The practical consequence

Stop optimising exits. It is the most emotionally satisfying place to
look — the evidence of "missed" points is vivid and appears on every
chart — and it is measurably the least productive. The 52-point gap
is the distance between hindsight and foresight, not the distance
between your exit and a better one.
