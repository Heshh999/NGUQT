# OF-H Series: Twelve Directional Order-Flow Hypotheses

> **SUPERSEDED IN PART - read `TEN_MONTH_PROTOCOL.md` alongside this.**
> The within-day-shuffle null used below is the WRONG null for a
> directional claim: it preserves each day's own direction and hands it
> to the control for free, which is why its "noise" median came out at
> +11.6 pt. Under the correct sign-flip null, OFH6's family-wise p is
> **0.129, not 0.688**. The outlier objection raised below was also
> over-applied - OFH6 has a positive median trade and a 52% win rate.
> The overall verdict (0 of 12 proven) is unchanged, but the reasons in
> the OFH6 section below are not the right ones. OFH6 actually fails
> because its edge disappears the moment a stop is added, and because
> family-wise p = 0.129 still does not clear 0.05.

**Date:** 2026-08-21
**Scripts:** `analysis/v41/ofh.py`, `analysis/v41/ofh2.py`
**Data:** volumetric capture, 281,195 one-minute bars, 2025-11-02 ->
2026-08-19. 53,959 eligible RTH bars after the engagement rules.

**Question asked:** the magnitude study confirmed order flow predicts how
FAR price moves. Can order-flow events predict WHICH WAY - the only thing
that pays?

**Ledger and power warning, stated before the results.** The OF window is
ten months and its holdout is spent, so DEV (through 2026-03) / VAL
(2026-04+) is a replication split, not out-of-sample. Ten months is also
short enough that the noise floor of a 12-way search is enormous - that
turned out to be the decisive fact.

## The declared family

All twelve declared with direction and mechanism in the script header
before running; engine semantics verified in `V4OrderFlowV41.cs` first
(`absorptionBuyCandidate` = aggressive buyers ABSORBED at an extreme, a
bearish reading - directions follow the engine's definitions, not the
column names). RTH only, 30-min cooldown per hypothesis, entry at signal
bar close, 60m time exit (management A) and 1.5 ATR stop + 90m cap exact
race (management B), 0.87 pt cost. DEV-frozen thresholds.

## Results

| | n DEV/VAL | A net DEV | A net VAL | verdict |
|---|---|---|---|---|
| OFH1 divergence fade | 791/780 | -0.05 | +3.20 | sign unstable |
| OFH2 confirmed break go | 766/746 | +2.86 | -1.73 | sign flip |
| OFH3 absorption reversal | 123/117 | -7.04 | +17.83 | sign flip, tiny n |
| OFH4 stacked imbalance go | 877/877 | -2.46 | +2.96 | sign flip |
| OFH5 imbalance exhaust fade | 810/782 | +0.50 | -1.11 | sign flip |
| **OFH6 cum-delta trend go** | 361/422 | **+8.99** | **+5.97** | see below |
| OFH7 effort-result go | 620/591 | +2.30 | -2.22 | sign flip |
| OFH8 value rejection go | 0 | - | - | never fired |
| OFH9 value reversion | 825/821 | -3.44 | +0.32 | negative |
| OFH10 acceptance rotation | 0 | - | - | never fired |
| OFH11 delta climax fade | 0 | - | - | never fired |
| OFH12 repeat-extreme fade | 862/854 | -0.29 | -0.04 | negative |

**The silent three, diagnosed** (a declared hypothesis with n=0 is a
defect to explain, not skip): `REJECTED_FROM_VALUE` and
`ACCEPTED_INTO_VALUE` never occur in the eligible sample - the AT_POC /
AT_VAH / AT_VAL bands take precedence in the classifier and on 1m bars
they absorb every case. OFH11's `|deltaPct| >= 60` occurs on **zero of
53,959** RTH bars - a 1m MNQ bar essentially never prints 60% one-sided
delta. Declaration flaws on my side; the thresholds were folklore-sized,
not data-sized.

## OFH6 - the one nominal survivor, and why it does not stand

OFH6 (15-bar cumulative delta sum in the DEV top decile, trade its
direction) passed every stated gate: positive both splits, p_DEV = 0.023,
8 of 10 months positive, longs and shorts both positive on DEV, median
trade positive (+5.9 / +5.1 pt), win rate 52%.

Two tests kill it:

1. **Family-wise noise floor.** The identical 12-way search re-run on
   within-day-shuffled outcomes, statistic = best-of-family
   min(muDEV, muVAL): real OFH6 = +5.97; noise median = **+7.33**;
   family-wise p = **0.688**. The best real result sits BELOW the middle
   of what pure noise produces when you search 12 hypotheses on ten
   months of data. (The first-pass floor agreed: shuffled best-of-12 DEV
   mean median +9.39 vs real best +8.99; 199/200 shuffles produced at
   least one hypothesis positive in both splits.)
2. **Outlier shape.** Removing the best 5% of trades flips the mean from
   +8.99 to **-3.54** (DEV) and +5.97 to **-7.85** (VAL) - the same
   lottery-ticket tail that disqualified decile-1 on the structure side.

## Verdict

**NO directional order-flow edge demonstrated. 0 of 12.**

Two lessons worth keeping:

1. **Magnitude prediction did not convert into direction** - third
   dataset, same asymmetry. "Order flow is confirmed predictive" is true
   only of volatility, and volatility prediction cannot make a futures
   trade positive-EV on its own.
2. **Ten months cannot certify a discovery of this size at all.** The
   measured noise floor for a 12-way search on this window is roughly
   +7 pt/trade - larger than any plausible real edge. Any "discovery"
   made by searching this window is unprovable on this window.

The one legitimate forward path: the capture grows by a month every
month, and months after 2026-08 are genuine out-of-sample relative to
everything done today. A single pre-registered hypothesis (OFH6 as
frozen here, thresholds and all) evaluated on 2026-09+ data as it
arrives would be a real test with no search bias. Until then OFH6 is a
noise-consistent curiosity, not a strategy.
