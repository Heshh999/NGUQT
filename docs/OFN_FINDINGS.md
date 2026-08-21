# OF-N Family: Twelve Order-Flow Event Hypotheses

**Date:** 2026-08-21
**Script:** `analysis/v41/ofn_run.py` (all mechanical parameters frozen
in its header before the first run; user-declared directions and
mechanisms). Full output: scratchpad `ofn_out2.txt`.
**Protocol:** M=12 family; sign-flip-by-day null; BH over 12; excess over
side/split-matched baseline; DEV (2025-11..2026-03) / INTERNAL
REPLICATION (2026-04..08); 60m horizon; cost 0.87; 30-min per-hypothesis
cooldown; entries at completed 1m closes only.

## Defect found and fixed on the first run

The first run produced absurd side-splits (OF-N6: 490 long / 2 short on
data where the impulse candidates measure 3,484 long / 3,705 short). The
cause was mine: scanners that process each direction in a separate full
pass shared the inline cooldown timestamp, so pass 1's final timestamp
silently blocked essentially every entry of pass 2. The declared rule
was always a chronological cooldown; it is now applied once in time
order after all scanners finish. The diagnostic that caught it and the
fix are recorded in the script. All results below are post-fix; the
pre-fix output is superseded.

## Results

| | n | excess | DEV / IR | ratio | ff1 | p raw | BH q |
|---|---|---|---|---|---|---|---|
| **OF-N3** absorption at fresh extreme | 141 | **+15.48** | **+16.9 / +14.6** | 1.089 | 52.5 | 0.105 | 0.63 |
| **OF-N6** impulse, weak pullback, re-expansion | 802 | **+6.49** | **+9.1 / +4.2** | 1.042 | 48.9 | 0.078 | 0.63 |
| OF-N8 delta flip at sweep | 628 | +1.63 | +5.4 / −2.5 | 1.009 | 50.6 | 0.377 | 0.84 |
| OF-N9 vol-per-tick exhaustion | 442 | +1.90 | −4.7 / +7.9 | 1.052 | 49.7 | 0.358 | 0.84 |
| OF-N4 stacked imbalance failure | 1915 | +0.29 | +2.1 / −1.4 | 0.980 | 49.7 | 0.459 | 0.84 |
| OF-N2 two-push exhaustion | 409 | −0.77 | | 0.986 | 49.8 | 0.569 | 0.84 |
| OF-N11 value migration | 168 | −1.91 | | 1.109 | 47.9 | 0.610 | 0.84 |
| OF-N12 value break failure | 263 | −1.97 | | 0.873 | 46.4 | 0.619 | 0.84 |
| OF-N10 delta range + directional close | 183 | −2.73 | | 0.851 | 52.5 | 0.777 | 0.89 |
| OF-N5 stacked imbalance acceptance | 1736 | −2.98 | | 0.990 | 49.8 | 0.885 | 0.89 |
| OF-N7 CVD nonconfirmation | 822 | −3.74 | | 0.948 | 49.6 | 0.845 | 0.89 |
| OF-N1 aggression failure | 10 | −14.63 | | | | | |

Family-wise max-statistic p = **0.499**. Caveat on that number: the
family's small-n members (N1 n=10, N3 n=141) blow up the null max
(median +15.5, p90 +48.6), so the family test is blunt here; the
per-hypothesis sign-flip p's and BH q's are the sharper reading, and
none clears 0.05 / q 0.10 either.

**Stop family: no hypothesis passed the declared gate** (n>=40, excess>0
in both splits, ff1>50% in both splits) - N3 failed on DEV ff1 (47.3),
N6 on IR ff1 (46.3). No stop or target work performed, by declaration.

## The informative pieces

**OF-N3 and OF-N6 are the two best-behaved candidates this window has
produced.** Both replicate in sign across DEV and IR, and both have
longs AND shorts positive (N3: +15.9/+13.9; N6: +5.1/+6.1 net) - the
first family members in the whole programme with that property. Neither
is certified: raw p 0.105 / 0.078, BH q 0.63, no ordering edge
(ff1 ~50), and concentration is heavy (N3: 7 trades carry +2,144 of
+2,060 total; N6: 40 trades carry +10,803 of +4,505; N3's 2026-08 was
−108/trade on 8 trades). They are the right shape and the wrong
certainty.

**N4 vs N5 answers the design question they were built to ask:** stacked
imbalances are neither exhaustion (N4: +0.29 on n=1,915 - exactly
nothing) nor acceptance (N5: −2.98 on n=1,736). The single-bar stacked
imbalance carries no usable directional information at this horizon,
in either framing.

**N9's control contrast is directionally right but untradeable:** fresh
extremes on very-high vol-per-tick with SMALL range (+1.90) versus the
same condition with large range (**−16.58**). The effort-without-result
ratio does discriminate - but the tradeable side of the contrast is
zero; all the signal is in "don't fade big-range extremes".

**N10 inverts its own hypothesis:** directional-close bars with huge
delta range lose (−2.73); the mid-close control WINS (+3.74). Combined
with the magnitude studies, this keeps saying the same thing: decisive-
looking bars mark spent moves.

**N7 (CVD divergence + structure break) fails again** (−3.74, n=822) -
the third divergence formulation on this layer to fail (after x-OFH1 and
the timing family). Delta divergence at extremes is now a repeatedly
falsified idea on this data.

## Verdicts

| | verdict |
|---|---|
| OF-N3 | **INTERESTING BUT INCONCLUSIVE** (best of family) |
| OF-N6 | **INTERESTING BUT INCONCLUSIVE** |
| OF-N8 | FAILED INTERNAL REPLICATION |
| OF-N9 | FAILED INTERNAL REPLICATION (control contrast noted) |
| OF-N4 | NO MEASURABLE INCREMENTAL VALUE |
| OF-N2, N5, N7, N10, N11, N12 | NO MEASURABLE INCREMENTAL VALUE |
| OF-N1 | INSUFFICIENT SAMPLE (n=10) |

**0 of 12 clears the standing protocol.** The honest cost accounting:
this window has now been searched by three 12-wide families plus the
timing family. Every additional family raises the certification bar for
everything, including N3 and N6. The frozen definitions of N3 and N6 in
`ofn_run.py` are the natural candidates for prospective scoring on
2026-09+ capture months - the only evidence source left that is not
already spent.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
