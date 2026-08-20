# V5 ADDENDUM - THE SELECTIVITY GAP, TESTED

Run 2026-08-20, after V5's confirmatory family returned 0 of 10.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

## THE GAP THIS CLOSES

Every V4 and V5 test measured *"does X predict direction, averaged across all
bars."* That is not the question *"does a positive-EV trade exist."* A rule firing
on 0.1% of bars with real expectancy is invisible in an all-bars pooled mean, and
both prior programmes tested **main effects only** - never a single conjunction.
Real setups are conjunctions. If edge lives in a 3-way interaction, every
single-factor test returns null while the setup works.

That gap was real. This addendum fills it.

## DESIGN

- 47 binary predicates (trend/vol/range state, EMA stack, level interaction and
  sequence state, time bucket, ATR and compression percentiles, VWAP/EMA distance
  bands, body ratio, test count). **Continuous thresholds taken from DEV only.**
- All 2- and 3-way conjunctions: **17,296** candidates.
- Selectivity filter: 300 to 24,474 DEV occurrences (0.02%-2% of bars), minimum 60
  distinct days. **8,329 qualify.**
- Score: best gross mean points per trade over horizons {10,20,40,80} bars and both
  directions. Ranking by gross equals ranking by net, since cost is a constant shift.

## RESULT 1 - THE SEARCH FINDS A SPECTACULAR SETUP

| rank | conjunction | K | dir | n | gross pt/trade |
|---|---|---|---|---|---|
| 1 | `comp<q25 & trend=UP & vwap<-1` | 80 | short | 614 | **+20.5684** |
| 2 | `range=COMPRESSED & trend=UP & vwap<-1` | 80 | short | 662 | +19.7998 |
| 3 | `t=RTH_PM & trend=UP & vwap<-1` | 80 | short | 1254 | +17.1535 |

+20.57 points per trade is where a research programme declares victory.

## RESULT 2 - THE PERMUTATION NULL

The identical search, over the identical 8,329 conjunctions, on outcomes **shuffled
within each session day** - destroying every feature-outcome relationship while
preserving day structure and marginal distributions. 20 repetitions.

| | best gross pt/trade |
|---|---|
| **Real data** | **+20.5684** |
| Shuffled, mean | +16.6152 |
| Shuffled, min | +12.7502 |
| Shuffled, max | **+26.1448** |
| **Permutations >= real** | **2 of 20, p = 0.143** |

**A search of this space produces a +12 to +26 pt/trade "setup" out of pure noise.**
The real data's best sits in the middle of that distribution.

### The calibration number worth keeping

The noise floor of this search is **+16.6 pt/trade**. Any backtest optimisation over
a comparable space that reports +13 to +26 points per trade is **fully consistent
with zero edge**. That number is the single most useful thing this addendum
produces: it converts "my backtest makes 20 points a trade" from evidence into
noise.

## RESULT 3 - FORWARD DECAY

Top 50 DEV conjunctions carried forward unchanged:

| | DEV | VAL | LOCKBOX |
|---|---|---|---|
| mean gross pt/trade | +13.208 | **-0.703** | **-0.214** |
| median | +13.179 | +0.632 | -2.465 |
| sign retained | - | 27 of 50 | 21 of 50 |
| VAL abs(t) >= 2 | - | 6 of 50 | - |

**Fraction of the DEV effect retained on VAL: -5.3%.** Not decayed toward zero -
inverted. Sign retention of 27/50 and 21/50 is a coin flip. The headline
conjunction ran +20.568 -> +10.406 -> **-7.762**.

### Cost is not the binding constraint

VAL net, mean of the 50, across cost assumptions:

| cost | net pt/trade | configs positive |
|---|---|---|
| 0.50 pt | -1.203 | 25 of 50 |
| 0.75 pt | -1.453 | 25 of 50 |
| 1.00 pt | -1.703 | 24 of 50 |
| 1.50 pt | -2.203 | 23 of 50 |

Negative at every level, including 0.5 pt - better than achievable execution. The
1.5 pt assumption flagged as "NEEDS WORK" in both audits was never what decided
this.

## A POWER FLAW IN V5's OWN DECISION RULE

Recorded because it was a genuine design error, not a result.

V5's survival rule required BH at q=0.05 across 10 hypotheses **plus** predicted
direction **plus** sign agreement in all 3 splits **plus** sign agreement in 6 of 7
years. BH at rank 1 of 10 needs p <= 0.005, i.e. **abs(t) > 2.81 pooled**.

| true pooled t | passes BH | 3 splits agree | >=6 of 7 years | total power |
|---|---|---|---|---|
| 3.5 | yes | 0.94 | 0.89 | ~84% |
| 3.0 | yes | 0.86 | 0.78 | ~66% |
| 2.5 | **no** | - | - | **~0%** |
| 2.0 | **no** | - | - | **~0%** |

A genuine edge at t = 2.5 over seven years was structurally undetectable under my
own rule. The pre-registration called that strictness "the correct response"; it
optimised against false positives without checking the cost in false negatives.

The search design in this addendum does not share that flaw - it uses a permutation
null rather than a significance threshold - and it still found nothing.

## WHAT THIS DOES AND DOES NOT ESTABLISH

**Establishes:** 2- and 3-way conjunctions over this predicate pool, at trading
selectivity, with fixed-horizon exits, carry no edge - and the apparent edges they
produce are indistinguishable from data mining.

**Does not establish:** anything about 4+ way conjunctions (though the noise floor
rises with search size, making that a losing race), multi-day horizons, tick/DOM
order flow, or the operator's full strategy tested end-to-end.

## ON POSITIVE EV VERSUS EDGE

These are different claims and the distinction matters. Long MNQ has **positive
expected return** - the overnight window alone captured 12,736 points across the
sample. That is beta: compensation for bearing risk, and it is real. What seven
years of data does not support is **alpha** from intraday directional prediction
using public OHLCV on a hyper-liquid index future.

Nothing here argues against positive-EV exposure. It argues against the specific
belief that intraday structure, order flow, or clock conditioning predicts
direction well enough to pay costs.

---

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
