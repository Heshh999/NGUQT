# TR-H1 Class D Management Pass — R:R Verdict

Date 2026-08-20. DEV + VAL only; OOS and LOCKBOX not read. Entries are
the frozen TR-H1 sample (membership function byte-identical to
confirm.py): DEV n=299 (first 2019-08-08, last 2022-12-29), VAL n=131
(2023-01-04 .. 2024-06-27), long-only, matching the prior report
exactly. Full tables produced by analysis/v41/trh1_rr.py.

PRIMARY STOP = MEDIUM (frozen at preregistration; the only stop the
engine's race grid was computed against). Median 15.1 pt, mean 21.0 pt.

## The three decisive facts

1. DEV supports NO fixed-R multiple. Every target from 0.5R to 5R is
   net-negative or zero at base costs (best cells: 2R +0.011R,
   2.5R +0.007R, PF <= 1.02). VAL is broadly positive (0.5R..3R, peak
   1R +0.119R) — but a region that is flat-to-negative in the selection
   sample and positive only in the later sample cannot be selected
   without hindsight. Retention classification: SIGN FLIP (inverted)
   at 0.5R..1.5R; economic zero -> small at 2R/2.5R.

2. The entries have no location advantage. Median MFE 2.1R/2.3R vs
   median MAE 2.3R/2.5R (DEV/VAL); MAE p75 is 4.3R..5.5R. Price
   routinely travels multiple stop-distances in BOTH directions within
   the 240m window after entry.

3. The stop does not invalidate the thesis. Of trades stopped at 1R,
   45.5% (DEV) and 63.5% (VAL) later reached +1R inside the same
   window; even at 3R a quarter of stopped trades later hit +3R.
   TIGHT stops are hit in ~89% of trades (median MAE 4.5-4.9 tight-R).
   STRUCTURAL stops (median 40 pt) are hit in ~44% with no captured
   race grid.

## Cost sensitivity
Only VAL 1R/2R survive +1 tick/side extra slippage; nothing survives
+2 ticks/side in both splits. Year-by-year at 2R: +0.11, +0.06, -0.05,
+0.00, +0.02, +0.27 — 2024 alone carries the VAL result.

## Class D exploration (same entries)
Unconditional 1m EMA9 trail: negative in both splits (-0.10R/-0.11R).
Pre-existing vector-zone target: DEV -0.29R -> VAL +0.09R (flip).
Structural swing target: +0.00R (n=58) -> +0.46R (n=20) — samples too
small to mean anything. The preregistered conditional-EMA9 (strong-
trend gate) is not computable: no causal 1m trend-state feature exists
in the capture; noted for any future preregistration.

## VERDICT

**NO ROBUST PAYOFF REGION.**

TR-H1's favorable excursion is symmetric with its adverse excursion,
so no fixed-R geometry can extract an edge that entry location does
not contain. The earlier points-level result (+1.21/+2.99 pt at 60m)
equals roughly +0.06R/+0.16R gross against the frozen stop — always
economically thin per unit of risk, and Step 3 shows it does not map
to any usable stop/target profile. This is consistent with, and
sharpens, the primary verdict: the candidate remains failed; OOS and
LOCKBOX remain untouched.
