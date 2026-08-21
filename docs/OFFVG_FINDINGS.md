# OFH11-OFH14: Liquidity / FVG / IFVG / Order-Flow Timing Family

**Date:** 2026-08-21
**Scripts:** `analysis/v41/offvg_run.py` (all mechanical definitions frozen
in its header before the first run), `offvg_stop.py`, `offvg_30s.py`.
Output: scratchpad `offvg_out.txt`.

**Provenance.** Research translations inspired by publicly discussed PB
Trading / ICT concepts. **Not claimed to be any official PB Trading or
ICT strategy** - no primary source was consulted for exact mechanical
rules, so every threshold here is my own frozen choice.

Frozen OFH6 imported unmodified as DIRECTION only; 30-minute context
life, not re-optimised. DEV = 2025-11..2026-03, INTERNAL REPLICATION =
2026-04..08; neither is true OOS. M=4 family.

---

## Results

| | n | excess | ratio | ff@1ATR | p_exc | p_ff | BH q |
|---|---|---|---|---|---|---|---|
| OFH6 baseline | 783 | +8.19 | 1.026 | 48.1 | - | - | - |
| **OFH11** sweep+FVG | 10 | +20.71 | 2.036 | 60.0 | 0.136 | 0.375 | 0.136 |
| **OFH12** sweep+IFVG | 17 | +50.93 | 2.803 | 47.1 | 0.008 | 0.696 | **0.030** |
| **OFH13** FVG+flow-failure | 117 | +19.19 | 1.410 | 46.2 | 0.032 | 0.813 | 0.061 |
| **OFH14** FVG pullback | 392 | +8.43 | 1.117 | 49.2 | 0.046 | 0.635 | 0.061 |

Family-wise max-statistic p = **0.0100** (driven by OFH12).

## The central finding: the ratio improved, the ordering did not

MFE/MAE rose materially (1.03 -> 1.41 for OFH13, 2.80 for OFH12) while
1-ATR favourable-first stayed at **46-49%** everywhere, none better than
OFH6's 48.1%, every p_ff > 0.37. Those two facts are only compatible one
way, and the timing measurement confirms it:

| | med MFE | med MAE | med minutes to MFE | med minutes to MAE |
|---|---|---|---|---|
| OFH6 | 58.5 | 57.0 | 32 | **24** |
| OFH13 | 70.5 | 50.0 | 31 | **20** |
| OFH14 | 57.5 | 51.5 | 31 | **25** |

**The adverse excursion systematically arrives first - by 6 to 11 minutes
of median.** The larger favourable excursion is real but late. This is
the mechanism behind every failed ratio improvement in this programme,
now measured directly rather than inferred.

The stop test is that fact in money. Structural-stop hit rates:
OFH13 **80.3%**, OFH14 **85.7%** - and these are the *tight* stops the
setups were supposed to earn (15.75 / 13.75 pt vs OFH6's 21.68). The
fixed-R grid (conservative treatment of intrabar ties) is negative in
essentially every cell for OFH14, and for OFH13 only at 3-4R, where the
target is so wide it is effectively no target. Intrabar ambiguity runs
16-19% at 0.5R and is reported, never resolved by assumption.

## Ablation - the one clear positive result

| cell | n | excess | ratio |
|---|---|---|---|
| FVG only (unconditional) | 1620 | **-4.25** | 0.895 |
| OFH6 + FVG | 392 | +8.43 | 1.117 |
| FVG + flow-failure | 606 | +8.47 | 1.132 |
| OFH6 + FVG + flow-failure | 117 | **+19.19** | 1.410 |

Three things follow, and they are worth keeping regardless of the
verdict:

1. **FVG mitigation on its own is worthless here** - negative on 1,620
   events. The gap is not a location edge by itself.
2. **Order flow DOES add timing information beyond correct delta bias.**
   OFH6 alone adds +12.7 over FVG-only; the opposing-flow-failure
   condition alone adds +12.7; together they add +23.4. Roughly additive,
   i.e. carrying largely independent information. That is a direct answer
   to the ablation question that was posed.
3. What it adds is **drift, not ordering** - ff@1ATR across the four
   cells is 47.5 / 49.2 / 50.4 / 46.2.

## Per-hypothesis notes

**OFH11** (n=10): best ordering in the family (ff1 60.0, ratio 2.04) but
ten trades, DEV 7 / IR 3, IR negative. The full chain (sweep -> reclaim
-> displacement FVG -> mitigation) inside a 30-minute context is simply
rare. Controls are informative though: OFH6+sweep+**ordinary** reclaim
(n=154, +17.62, ratio 1.390) and OFH6+sweep+displacement-**without**-FVG
(n=55, +20.10, ratio 1.709) both beat the FVG version on frequency and
match it on geometry - the FVG requirement costs events without buying
geometry.

**OFH12** (n=17): the only result in this entire programme to clear a
family-wise test (p = 0.0100, BH q 0.030). It is nonetheless not
promotable: DEV n=7 ratio **0.778**, IR n=10 ratio **3.717** - the two
partitions point in opposite directions, so there is nothing to
replicate; its ff1 (47.1) is *below* the OFH6 baseline; and the declared
primary endpoint is entry asymmetry, on which it scores p_ff = 0.696. A
17-trade mean passing a permutation test on a secondary endpoint is not
evidence of an edge.

**OFH13** (n=117): the strongest candidate this programme has produced,
and the only one whose robustness profile is genuinely healthy - both
splits positive (+31.69 / +7.32), both sides positive (long +25.91,
short +14.68), 7/10 months, positive median trade (+8.51), and it
**survives outlier removal**: dropping the top 5% still leaves
+5.3 pt/trade (every prior candidate flipped negative on that test).
Structural stop positive in both splits (+12.03 / +10.02). Against that:
BH q 0.061, excess CI [-0.57, +38.54] includes zero, no ordering
improvement, and 80% stop-hit.

**OFH14** (n=392): reproduces OFH6's drift almost exactly (+8.43 vs
+8.19) at 32% lower risk-to-invalidation. Stable across splits (+7.17 /
+9.47) and months (7/10). But ratio 1.117 and ff1 49.2 are within noise
of baseline, and every fixed-R cell is negative.

**FVG depth diagnostics** (descriptive, as required): no single depth
dominates. OFH14 by penetration bucket: edge <25% -0.94, 25-50% +12.73,
50-75% +3.75, 75-100% +27.55, full fill +12.03. Non-monotone and
scattered - no evidence that one exact depth "works", which is the
reassuring reading rather than the suspicious one.

## 30s execution arm (secondary)

Same frozen parents replayed on the genuine 30s grid (09:30-11:00 ET, the
only coverage that exists). OFH13 n=46, OFH14 n=95 paired. Entry-price
improvement is nil (median 0.00 pt; mean -0.52 / +0.40), and only 17-24%
of triggers fire earlier at all. The one real effect is **risk**: median
distance to invalidation falls by 10.50 pt (OFH13) and 6.00 pt (OFH14),
because the 30s trigger prints a shallower mitigation extreme. No
geometry change. Consistent with `OFSUB_FINDINGS.md`.

## Ranking (by the declared criteria, not by average points)

1. **OFH13** - best combination of ratio (1.410), MAE reduction (57->50),
   split and side replication, outlier robustness, and the only clean
   incremental-value ablation. Fails on ordering.
2. **OFH14** - most frequent (392), most stable, lowest risk, but
   geometrically indistinguishable from OFH6 itself.
3. **OFH12** - largest numbers and the only family-wise pass, but n=17
   with DEV and IR in opposition.
4. **OFH11** - best raw ordering, n=10, unusable.

## Verdicts

| | verdict |
|---|---|
| OFH11 | **INSUFFICIENT SAMPLE** |
| OFH12 | **INSUFFICIENT SAMPLE** (DEV/IR in opposition; family-wise pass not credited) |
| OFH13 | **INTERESTING BUT INCONCLUSIVE** |
| OFH14 | **DIRECTIONAL BUT POOR GEOMETRY** |

## The answer

**DID LIQUIDITY + FVG / IFVG / ORDER-FLOW TIMING CONVERT FROZEN OFH6
DIRECTIONAL INFORMATION INTO A BETTER ENTRY LOCATION?**

# INCONCLUSIVE

Better in three of the four dimensions asked about - MFE/MAE (1.03 ->
1.41), median MAE (57 -> 50), and risk-to-invalidation (21.7 -> 15.8 pt)
- with DEV/IR agreement, side symmetry, and outlier robustness that
nothing earlier in this programme achieved. Not better in the dimension
that decides tradability: favourable-first ordering is unchanged at
46-49%, because the adverse excursion arrives 11 minutes earlier than
the favourable one, so an 80% stop-hit rate eats the improved ratio
before it can be realised.

Per the instruction: **no OFH15 is created and no rule here is tuned.**
OFH13's definition is frozen in `offvg_run.py`. Given that it is
inconclusive rather than failed, the recommendation is not to shelve
OFH6-based construction outright but to stop *searching* on this window
- it has now absorbed three 12-wide families plus two timing families,
and every further test raises the bar for everything already tested. The
only unspent evidence is capture months from 2026-09 onward, where
OFH13 can be scored prospectively at zero statistical cost.

*THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.*
