# Pattern Scan — Is There Anything With Positive EV and Good R:R?

Date 2026-08-20. Asked after TR-H1 was killed. Scripts:
analysis/v41/avoid.py, analysis/v41/asymmetry.py.
Structure OOS/LOCKBOX (2024-07 onward) NOT READ.
OF-LATE (Jun–Jul 2026) is marked * — already spent as a P&L
illustration, shown for completeness, not clean evidence.

## The structural finding

Good risk-to-reward is not a target choice; it is a property of the
event. Across **13,548 DEV / 5,918 VAL break events**:

| | median MFE | median MAE | ratio | net R |
|---|---|---|---|---|
| DEV | 1.375 R | 1.363 R | **1.009** | −0.053 |
| VAL | 1.442 R | 1.380 R | **1.045** | −0.023 |

**MNQ structure breaks have symmetric excursion.** Price travels
essentially as far against you as for you before either happens. That
single fact explains every negative result in this programme: with
MFE ≈ MAE there is no asymmetry for any stop/target geometry to
harvest, which is exactly why TR-H1 had no payoff region and why no
fixed-R multiple worked.

## Asymmetry scan: 40 causal cells, ranked on DEV, checked on VAL

Families scanned: event kind, level interaction (12 states), vector
colour, W/M formation, 4H structure, 15m structure, time of day, ADR
consumption, HTF alignment. Minimum n=120.

| bar | cells clearing in BOTH splits | of those, net R > 0 in both |
|---|---|---|
| ratio ≥ 1.10 | 1 | **0** |
| ratio ≥ 1.20 | 0 | **0** |
| ratio ≥ 1.30 | 0 | **0** |

The DEV leaders invert in VAL — ACCEPTED_ABOVE 1.322 → 0.900, VIOLET
1.134 → 0.926, ACCEPTED_BELOW net +0.132 → −0.030. **Not one cell in
forty holds both a favourable excursion ratio and positive net R across
the split boundary.**

## Fade and avoidance candidates (4 tested, all reported)

| id | candidate | OF-DEV | OF-VAL | OF-LATE* |
|---|---|---|---|---|
| C1 | fade break with delta divergence against it | −0.068 R (p .67) | **+0.201 R (p .055)** | +0.004 R (p .51) |
| C2 | fade break flagged deltaFailsBreak | −0.015 R | −0.016 R | +0.064 R |

C1 works in exactly one split of three; per-month it is +0.26, −0.41,
+0.06, +0.10, +0.20, −0.00, +0.28, −0.14, +0.14 — six up, three down,
with the worst month cancelling the best two. Its fade-side excursion
is **MFE 1.06 R vs MAE 1.09 R** — symmetric again.

C2 is dead: on the break side it looked like the strongest single
separator in the whole study (−7.01 pt vs +2.27 pt), but that was a
points-scale artifact. Normalised to R and cost-adjusted it is
−0.015 R. This is a clean example of why the R unit matters.

| id | avoidance condition | DEV (in vs out) | VAL (in vs out) |
|---|---|---|---|
| C3 | breaks with NO level interaction | −0.088 vs −0.034 | −0.054 vs −0.007 |
| C4 | breaks on repeat level test (≥3 today) | +0.037 diff | −0.070 diff (flip) |

**C3 is the one consistent finding in this entire scan**: breaks with no
level interaction are worse than breaks at a level, same sign and
similar magnitude in both splits, on n=4,701/1,979. It is a genuine
negative confluence. It is *not* a strategy — excluding those events
moves you from −0.088 R to −0.034 R (DEV) and −0.054 to −0.007 (VAL).
Less negative, still not positive.

C4 flips sign. Dead.

## Answer to the question asked

**No. There is no pattern here with positive expectancy and good
risk-to-reward.** Forty cells, four candidates, and the pooled
baseline all say the same thing, and the reason is structural rather
than a failure of searching: the excursion distribution is symmetric,
so there is no R:R to find.

Two things are worth keeping:

1. **Location matters, weakly and negatively.** Breaks away from a
   tracked level are consistently worse. That is a real avoidance
   condition and it replicated. Use it to *exclude*, never as an entry.
2. **Order flow's informative side is contradiction, not
   confirmation** — every failure-flavoured feature separated harder
   than every confirmation-flavoured one. C1 is the surviving trace of
   that, and it needs far more volumetric history before it can be
   judged.

## What would actually change the answer

Not more searching of this event class — that is now well covered and
the symmetry result is stable on 19,466 events. It would take a
genuinely different event definition, and the only untested one on the
books is **VEC-H1** (the user's parent-wick hypothesis), which requires
1m vector emission the engine does not yet produce. The structure
OOS/LOCKBOX remains untouched and is the correct place to judge
whatever comes next.
