# Predicting Which Trades Run — magnitude vs direction

Date 2026-08-21. The user's proposal: every test so far targeted
DIRECTION; target MAGNITUDE instead — which trades will run. Scripts:
analysis/v41/predict_run.py (+ decile stress test). HOLD not read.

## The instinct was correct, and it replicates

Fourteen causal pre-entry features, Spearman rank correlation against
favourable excursion (MFE/stop) versus against signed return:

| | strongest |rho| |
|---|---|
| vs **magnitude** (MFE_R) | **0.231** |
| vs **direction** (signed netR) | **0.047** |

Three features hold the same sign in both splits: `bodyPctOfRange`
(−0.231 / −0.227), `bodyAtr` (−0.215 / −0.189), `rangeAtr`
(−0.113 / −0.064). A composite of the three correlates **+0.219 DEV /
+0.187 VAL** with subsequent excursion.

**Magnitude is roughly five times more predictable than direction,
and direction is statistically indistinguishable from zero.** That is
a real, replicating, mechanically sensible finding: small-bodied
indecisive bars precede larger swings; large decisive bars precede
smaller ones. Displacement spends the move.

This also explains, cleanly, why every exit experiment failed. You can
forecast how far a trade will travel. You cannot forecast which way.
No exit rule converts the first into money without the second.

## The decile that looked like an edge — and what killed it

The lowest-predicted-excursion decile (large decisive break candles)
was the one place in this project showing favourable skew AND positive
net in both splits. Frozen at the DEV p90 threshold and re-tested:

| | n | mean | **median** | medMFE/medMAE | p |
|---|---|---|---|---|---|
| DEV decile-1 | 1,355 | +2.84 | +1.13 | 1.11 | 0.123 |
| VAL decile-1 | 582 | +1.69 | +3.13 | 1.10 | 0.290 |
| DEV all events | 13,548 | −1.25 | −1.37 | 1.01 | 0.931 |
| VAL all events | 5,918 | +0.07 | −1.37 | 1.04 | 0.476 |

Genuinely encouraging: positive in both splits, beats its baseline by
~4 pt and ~1.6 pt, ratio 1.10–1.11 vs 1.01–1.04, and both sides
contribute (long +3.39/+2.45, short +2.36/+0.96) — not beta this time.

Then the outlier test:

| DEV decile-1 total | +3,851 pt |
|---|---|
| remove best 1 trade | +3,414 |
| remove best 5 | +1,942 |
| **remove best 5%** | **−11,364** |
| mean +2.84 → without top 5% | **−8.82** |

**68 trades out of 1,355 carry the entire result and then some.**
Strip the top 5% and the mean goes from +2.84 to −8.82. Per year it is
already unstable (+3.55, +5.30, +4.74, **−1.16**, +2.42, +0.29), and
neither split reaches significance (p = 0.123 / 0.290).

This is exactly the profile the programme's own rules were written to
reject: "a candidate that depends on a few exceptional outcomes should
be heavily downgraded."

## Verdict

**REJECTED as a strategy. KEPT as a finding.**

The magnitude result is real and should inform any future design:
excursion is forecastable, direction is not, and bar decisiveness is
the strongest single predictor of how far price will travel next. The
decile-1 apparent edge is 68 lucky trades wearing a favourable-looking
median.

What it does NOT do is rescue the earlier failures. Those failed on
direction, and this confirms — with a measured 5:1 predictability gap —
that direction is the thing that is missing. Targeting magnitude does
not change that; it explains it.
