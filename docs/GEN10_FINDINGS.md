# Fourteen-Dimension Examination and the G-Family

**Date:** 2026-08-21
**Scripts:** `analysis/v41/diag14.py` (examination), `gen10_run.py`
(ten exploratory-derived hypotheses). Outputs: scratchpad
`diag14_out.txt`, `gen10_out.txt`.

**Status of everything here: EXPLORATORY.** The G-family was designed
after examining this window, so its p-values are hypothesis-generating
regardless of size. Confirmation can only come from capture months
2026-09 onward.

---

## Part 1 - what the examination measured

Strong contrasts (the ones the hypotheses were built on):

1. **Opposing delta attacks** (n=2,611): when a p75 opposing-delta bar
   attacks a 0.5-ATR trend and FAILS (trend-side extreme breaks within
   3 bars), 30m trend drift is **+17.5 pt**; when it succeeds, **-7.6**.
   (Partly contaminated by the resolution move being inside the window -
   the tradeable version is tested as G4.)
2. **Stacked imbalance resolution** (n=41,783): 73% continue (+6.2);
   27% fail and the imbalance side then loses **-16.8**. Same
   contamination caveat -> G5/G6 test the entries.
3. **Absorption inverts the folklore**: at fresh 20-bar extremes,
   HIGH bar-level absorption -> fade earns -0.29; LOW absorption ->
   fade earns +1.46. High absorption at an extreme precedes
   CONTINUATION here. (Exact footprint prices are NOT in the capture -
   MODE1 summary only; this is the bar-level proxy.)
4. **Compression release**: 10-bar envelope <= p25 + 1-ATR release bar:
   WITH aligned p75 delta +0.80, without -0.95.
5. **The discount structure (the big one)**: median adverse excursion
   after an OFH6 signal is **2.83 ATR (57 pt)**, its extreme arrives at
   t=24 min vs t=32 for the favourable extreme, and even the p25 depth
   is 1.35 ATR - so a 0.5-1.0 ATR resting limit fills in 76-89% of
   signals. The signal is systematically early; the market hands back
   a discount before it pays.

Clean nulls, equally useful: bar-level delta efficiency (nothing),
micro-structure first break after the signal (with 6.2 vs against 6.1 -
uninformative), displacement alone (-0.7), pullback depth
(shallow -1.3 vs deep -1.5), acceptance at reclaims (monotone but tiny:
-0.05 / +0.43 / +0.52). Consolidated from earlier sessions: FVGs alone
negative; sweeps re-break 65%; vector triggers late; OFH6 spent by 45m;
30s buys risk geometry, not price.

## Part 2 - the ten hypotheses and what happened

| | n | exc | DEV / IR | ff1 | months+ | p raw | BH q |
|---|---|---|---|---|---|---|---|
| **G1** RT-050 limit at -0.5 ATR | 695 | +10.66 | +11.9 / +9.6 | **52.6** | **9/10** | .003* | .030* |
| **G2** RT-100 limit at -1.0 ATR | 595 | +9.63 | +7.4 / +11.6 | **54.7** | 7/10 | .011* | .053* |
| G3 DL-20 delayed if discounted | 395 | +4.66 | +8.8 / +0.7 | 46.7 | 5/10 | .152 | .272 |
| **G4** attack-failure go | 182 | +14.65 | +20.9 / +9.9 | 41.4 | 6/10 | .068 | .179 |
| G5 stacked-failure fade | 1912 | -0.92 | +3.5 / -5.2 | 49.7 | 4/10 | .655 | .655 |
| **G6** stacked-go + OFH6 | 839 | +6.67 | +5.9 / +7.3 | 46.5 | 8/10 | .072 | .179 |
| G7 compression release | 1292 | +0.76 | +0.4 / +1.1 | 50.9 | 7/10 | .377 | .471 |
| G8 absorption continuation | 926 | +0.48 | +2.3 / -1.1 | 48.9 | 6/10 | .447 | .497 |
| G9 impulse pullback into FVG | 483 | +5.58 | +18.4 / -5.0 | 50.3 | 8/10 | .163 | .272 |
| G10 accepting sweep reclaim | 64 | +11.94 | -5.9 / +25.8 | 53.1 | 4/10 | .223 | .319 |

OFH6 baseline: exc +8.19, median +3.61, ratio 1.026, ff1 48.1.
Family-wise max-statistic p = 0.212.

**\*Statistical defect, disclosed:** for the limit-entry hypotheses
(G1/G2/G3) my sign-flip comparator entered at the bar CLOSE, not at a
mirrored limit, so their p-values and BH q's are OPTIMISTIC - the
mechanical discount is counted as edge by the null. Those stars are not
to be trusted as printed. The honest comparison for G1/G2 is direct:

| | OFH6 | G1 (fill 89%) | G2 (fill 76%) |
|---|---|---|---|
| per-SIGNAL EV (unfilled=0) | +8.19 | **+8.69** | +6.65 |
| median trade (net) | +3.61 | **+5.37** | +5.55 |
| medMFE/medMAE | 1.026 | 1.103 | 1.128 |
| ff@1ATR | 48.1 | **52.6** (IR 57.6) | **54.7** (IR 55.0) |

Same drift, better geometry. G1 keeps essentially all of OFH6's
expectancy (+8.69 vs +8.19 per signal) while entering half an ATR
cheaper, and it is the first n>500 result in this programme with
favourable-first ABOVE 50% in both partitions (52.6 pooled, 57.6 IR)
and 9/10 months positive. It is exactly what diag 12b predicted the
discount structure should buy. It remains exploratory-derived, its
excess metric embeds the discount by construction, and its top-5%
concentration is still heavy (top 34 trades exceed the total).

**G4 and G6** replicate in sign across both splits with real n (182 /
839) - drift candidates, but both have ff1 BELOW baseline (41.4 / 46.5):
they select strong-drift moments, not better entry locations. **G5 is
the useful negative**: the -16.8 "stacked failure" signal from the
examination vanishes when you can only enter AFTER the resolution -
the whole effect was the resolution move itself. G9 and G10 flip
between partitions. G7/G8 are flat.

## What goes on the forward-scoring shelf

Frozen as declared in `gen10_run.py`, to be scored on 2026-09+ months
alongside OFH6 / OF-N3 / OF-N6 / OFH13:

1. **G1 (RT-050)** - primary candidate; forward test should score
   per-signal EV, median, ff1, and MAE against same-month OFH6
   immediate entry.
2. **G2 (RT-100)** - depth-family companion, reported not selected.
3. **G4, G6** - drift replicators, secondary.

No further hypotheses will be derived from this window's results.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
