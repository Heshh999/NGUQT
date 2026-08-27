# OFH13-POSTENTRY-V1 — FROZEN ONE-SHOT EXECUTION — FINDINGS

**HEADLINE: OFH13-POSTENTRY-V1 FOUND NO NEW CAUSAL POST-ENTRY
SEPARATOR.** 0 of 22 binding cells passed every required gate. 0 of a
permitted 1 tail-development candidate and 0 of a permitted 1
loss-failure candidate advanced. **The study is closed. No V1 rescue.**

Execution UTC 2026-08-27T13:39Z · runtime 128 s · seed 20260826.

**No management rule was created, simulated, or evaluated.** OFH13's
entry, ATR1.5 stop, 60-minute exit and prospective logger are unchanged.
All OFH13 history is DEVELOPMENT data for this study; nothing here is
OOS or independently confirmed. **NO ORDERS. THIS PROJECT DOES NOT
AUTHORIZE LIVE TRADING.**

---

## 1. Freeze verification (Phase 0)

| # | Item | Result |
|---|---|---|
| 1 | prereg sha256 | `90490ecba8556cf9f4d6facb44fdf186aa3355aafc3e20651d2af64198fe44b3` **MATCH** |
| 2 | prereg commit | `f4964c9fcf09f85b683b47f7695e815a496e671d` |
| 3 | OFH13 lineage | `cand_spec.generate()["OFH13"]`, frozen shelf |
| 5–7 | stop / target / exit | ATR1.5 · none · 60m — **all unchanged** |
| 8–10 | T5 / T15 / eligibility | exact frozen definitions, strict `tmin` contiguity |
| 11 | primary endpoint | `futureMFE(T) = max_{k∈(T,e]} dir·(extreme[j+k] − c[j+T])`, floored at 0 |
| 12–15 | F1–F6 / controls / tail / floors | reproduced verbatim |
| 16–19 | M 11+11=22 · permutation · P1–P15 · ceiling 2 | as frozen |
| 20 | contamination | all history is development; no protected segment |

## 2. Baseline reproduction (Phase 1) — **EXACT**

| | measured | registry |
|---|---|---|
| events | 133 (UNSEEN 16 / DEV 57 / IR 60) | 133 (16/57/60) |
| win rate | **36.1%** | 36.1% |
| EV / trade | **+17.26 pt** | +17.26 |
| profit factor | **1.80** | 1.80 |
| max drawdown | **333 pt** | 333 |

Every figure reproduced before any feature was computed.

## 3. Data / contamination status

**ALL AVAILABLE OFH13 HISTORY IS DEVELOPMENT DATA FOR THIS STUDY.** No
protected historical confirmation segment exists — the registry
data-freeze line is 2026-08-19 and the capture ends 2026-08-19 16:59, so
there are zero post-freeze parents. No partition (UNSEEN / DEV / IR) is
OOS and none is described as such anywhere in this document.

Additionally, and materially: the baseline controls this study required
every feature to beat — signed return to T, MFE to T, MAE to T — **had
already been viewed by eventual winner/loser class** in OFH13-V2
Studies 8–9, at 3m/5m/10m/60m. Any surviving result would therefore have
been clearing a pre-contaminated bar. Nothing survived, so this weakens
nothing in practice, but it is recorded because it would have qualified
a positive.

## 4. Checkpoint counts (Phase 2) — matches the freeze exactly

| population | n | days | LONG | SHORT | F4/RVMR available |
|---|---|---|---|---|---|
| all parents | 133 | 108 | 55 | 78 | — |
| **T5-ELIGIBLE** | **95** | **81** | 38 | 57 | 92 |
| **T15-ELIGIBLE** | **73** | **64** | 32 | 41 | 71 |

Frozen expectation was T5 95/81, T15 73/64, F4 92/71 — reproduced
exactly. Stopped by +5m: 38. Stopped by +15m: 60.

**No synthetic survival.** Eligibility is conditional on the trade still
being open under the *original* frozen management; no stop was altered
to raise eligibility and no stopped trade was carried forward. This is
an explicitly selected survivor population and no result below applies
to all 133 parents.

## 5. Causal audit (Phase 3) — **NO LEAKAGE**

| family | T | feature last input | outcome first input | leakage |
|---|---|---|---|---|
| F1, F2G1, F3, F4, F5align | 5 | bar j+5 (close) | bar j+6 onward | **NO** |
| F1, F2G1, F3, F4, F5align, F6 | 15 | bar j+15 (close) | bar j+16 onward | **NO** |

Every feature uses only completed bars j+1…j+T. Every outcome window is
`(T, e]` measured from the checkpoint close `c[j+T]`. The engine
asserted `first_outcome_bar > last_feature_bar` on every event of every
cell. **LEAKAGE DETECTED: NO.**

## 6. Endpoint validation (Phase 4)

| checkpoint | futureMFE mean | median | mean in R | secondary new-high extension |
|---|---|---|---|---|
| T5 | 76.81 pt | 54.00 pt | 2.119 R | 64.68 pt |
| T15 | 76.97 pt | 55.75 pt | 2.098 R | 53.18 pt |

Excursion achieved before T cannot contribute by construction. The
preregistered secondary reading is reported and did not replace the
primary anywhere.

## 7–12. Feature results — TAIL family (futureMFE)

| cell | T | nA | nB | mean A | mean B | effect | p | BH q | perm |
|---|---|---|---|---|---|---|---|---|---|
| F1 | 5 | 32 | 32 | +86.56 | +79.97 | +6.59 | 0.797 | 0.902 | 0.696 |
| F1 | 15 | 24 | 25 | +113.26 | +67.48 | +45.78 | 0.030 | 0.081 | 0.186 |
| F2G1 | 5 | 32 | 32 | +98.52 | +55.63 | +42.88 | 0.044 | 0.096 | 0.004 |
| F2G1 | 15 | 24 | 25 | +94.51 | +50.41 | +44.10 | 0.024 | 0.081 | 0.044 |
| F3 | 5 | 63 | 32 | +89.64 | +51.55 | +38.10 | 0.029 | 0.081 | 0.007 |
| F3 | 15 | 54 | 19 | +77.48 | +75.51 | +1.97 | 0.902 | 0.902 | 0.890 |
| F4 | 5 | **7** | 47 | +66.14 | +78.93 | −12.79 | 0.573 | 0.788 | 0.737 |
| F4 | 15 | **7** | 35 | +69.68 | +73.65 | −3.97 | 0.844 | 0.902 | 0.883 |
| F5align | 5 | 29 | 33 | +106.94 | +55.64 | **+51.30** | **0.0072** | **0.079** | 0.009 |
| F5align | 15 | 21 | 35 | +103.62 | +60.72 | +42.90 | 0.061 | 0.112 | 0.142 |
| F6 | 15 | 24 | 25 | +63.03 | +96.22 | −33.19 | 0.088 | 0.138 | 0.134 |

**No cell reaches BH q ≤ 0.05.** The best is F5align@T5 at q = 0.079.

## 7–12 (cont). Feature results — LOSS family (remaining P&L)

| cell | T | nA | nB | mean A | mean B | effect | p | BH q | perm |
|---|---|---|---|---|---|---|---|---|---|
| F1 | 5 | 32 | 32 | +30.00 | +26.82 | +3.18 | 0.901 | 0.901 | 0.844 |
| F1 | 15 | 24 | 25 | +56.22 | +17.89 | +38.33 | 0.160 | 0.328 | 0.374 |
| F2G1 | 5 | 32 | 32 | +41.71 | +11.97 | +29.73 | 0.196 | 0.328 | 0.050 |
| F2G1 | 15 | 24 | 25 | +35.59 | +0.06 | +35.53 | 0.149 | 0.328 | 0.298 |
| F3 | 5 | 63 | 32 | +27.25 | +9.49 | +17.76 | 0.314 | 0.346 | 0.174 |
| F3 | 15 | 54 | 19 | +13.91 | +35.41 | −21.51 | 0.268 | 0.328 | 0.243 |
| F4 | 5 | **7** | 47 | −12.12 | +22.51 | −34.63 | 0.250 | 0.328 | 0.498 |
| F4 | 15 | **7** | 35 | −17.22 | +17.78 | −35.01 | 0.235 | 0.328 | 0.331 |
| F5align | 5 | 29 | 33 | +43.10 | +6.93 | +36.16 | 0.059 | 0.323 | 0.205 |
| F5align | 15 | 21 | 35 | +47.04 | +6.72 | +40.31 | 0.161 | 0.328 | 0.283 |
| F6 | 15 | 24 | 25 | −8.63 | +42.32 | **−50.95** | **0.023** | 0.257 | 0.130 |

**No cell reaches BH q ≤ 0.05.** The best is F6@T15 at q = 0.257.

### Per-family reading

- **F1 path efficiency** — raw effect at T5 is essentially zero
  (+6.59 pt, p 0.797). At T15 it looks larger (+45.78) but the residual
  test cuts it to 34% and the permutation does not support it (0.186).
- **F2 excursion shape (G1)** — the largest *consistent* raw effects
  (+42.88 / +44.10) with good permutation support at T5 (0.004). Both
  collapse under residualisation (−9.94 and −2.47 — **sign flips**).
  This is the clean signature of shape being a re-description of level.
- **F3 structural acceptance** — the single most interesting raw cell:
  ACCEPTED vs (ENTANGLED ∪ RECLAIMED) at T5 gives **+38.10 pt** with
  perm 0.007 and the *best destruction profile in the study* (trims
  +30.64/+27.86, drop-1 +45.90, 11 of 11 flagged tail winners
  mostly-after-T). It fails on incrementality: residualised to **+1.86
  pt — 5% retention.** Acceptance is almost entirely early MFE/MAE
  wearing structural clothing. At T15 the ENTANGLED∪RECLAIMED arm falls
  to 19 events, below the frozen floor → INSUFFICIENT.
- **F4 RVMR post-entry evolution** — **INSUFFICIENT exactly as
  pre-declared.** The EXPANSION arm holds **7 events** at both
  checkpoints against the frozen ≥20 floor, and the preregistration
  explicitly forbade any fallback contrast. Raw effects are negative
  and insignificant at both checkpoints in both families.
- **F5 directional alignment** — the strongest raw result anywhere
  (+51.30 pt, p 0.0072, perm 0.009, best q 0.079). Residualises to
  +16.46 (**32% retention**), and the matched construction *disagrees in
  sign* (−11.77). Alignment is net progress restated.
- **F6 acceleration (T15)** — the only cell to survive residualisation
  in the tail family (−33.19 → −24.34, **73% retention, same sign**) —
  and its sign is **opposite** to the hypothesis: faster recent movement
  predicts *less* subsequent expansion. Unsupported (p 0.088, perm
  0.134, q 0.138) and fails P8 and P12.

## 13. Loss-collapse analysis

No exit, breakeven, stop tightening, or partial exit was simulated, and
no hypothetical saved loss was computed. The loss family is the same 11
states scored on remaining P&L from T.

The candidate signals are directionally sensible — F4's non-expansion
and F6's positive acceleration both associate with weaker remaining
P&L, and F3's RECLAIMED state at T15 shows −21.51 — but **not one loss
cell has a CI excluding zero except F6@T15**, and none survives BH
(best q 0.257). **No causal state was found that identifies materially
deteriorated remaining expectancy.**

## 14. Right-tail analysis

Tail winners = the top 13 of 133 by original frozen net P&L (frozen by
rank, before results). The remaining-tail-fraction rule required ≥50% of
a flagged winner's eventual from-entry MFE to occur after T.

**P13 passed in every cell** — flagged tail winners genuinely had most
of their move still ahead of them (F3@T5: 11 of 11; F2G1@T5: 7 of 7;
F5align@T5: 6 of 6; F1@T15: 7 of 9). So the features were *not* merely
identifying trades already far into their final move. That is a real
and slightly surprising negative-control result — and it did not save
any cell, because the features failed on incrementality and
significance instead.

## 15. Baseline incrementality (the decisive duty)

| cell | T | endpoint | raw | residualised | ret% | matched | ret% | agree |
|---|---|---|---|---|---|---|---|---|
| F1 | 5 | tail | +6.59 | −24.02 | 364 | −29.57 | 448 | YES (both negative — raw sign flips) |
| F1 | 15 | tail | +45.78 | +15.49 | **34** | n/a | — | NO |
| F2G1 | 5 | tail | +42.88 | **−9.94** | 23 | n/a | — | NO |
| F2G1 | 15 | tail | +44.10 | **−2.47** | 6 | n/a | — | NO |
| F3 | 5 | tail | +38.10 | +1.86 | **5** | n/a | — | NO |
| F3 | 15 | tail | +1.97 | −19.86 | 1009 | −15.27 | 776 | YES |
| F4 | 5 | tail | −12.79 | −21.60 | 169 | n/a | — | NO |
| F5align | 5 | tail | +51.30 | +16.46 | **32** | **−11.77** | 23 | **NO** |
| F5align | 15 | tail | +42.90 | +21.02 | **49** | +54.44 | 127 | YES (retention 49% < 50) |
| F6 | 15 | tail | −33.19 | −24.34 | **73** | n/a | — | NO |

**Ten of eleven tail cells fail the residual test outright** — six by
sign flip, four by retention below the 50% floor. In the loss family the
residual test is more permissive (F1@T15, F3@T15, F4, F5align@T15,
F6@T15 retain sign and ≥50%), but those cells are killed by P6/P7
instead.

**Structural disclosure — matched-construction computability.** The
matched common-weight statistic returned a value in only **8 of 22
cells**; in the other 14 no control cell held ≥5 events on *both* sides.
That is not an engine failure — it is near-collinearity: for terciled
features the arms barely co-occupy the (signed-return × MFE_T) control
cells at all, which is itself the definition of redundancy. The gate was
applied **as frozen** (undefined cannot demonstrate sign agreement, so
P4/P5 fail). **This degeneracy is not outcome-determining:** the
residual test alone independently fails 10 of 11 tail cells, and the one
cell it passes (F6@T15) fails P7, P8 and P12 regardless.

## 16. Sample-floor table

| floor | required | observed | result |
|---|---|---|---|
| T5 eligible | ≥90 events / ≥70 days | 95 / 81 | **PASS** |
| T15 eligible | ≥70 events / ≥55 days | 73 / 64 | **PASS** |
| cell arms | ≥20 events / ≥15 days | see below | 4 cells FAIL |
| F4 EXPANSION | ≥20 (no fallback) | **7 / 7** | **INSUFFICIENT** |
| F3@T15 arm B∪C | ≥20 | **19** | **INSUFFICIENT** |

No floor was lowered. The two INSUFFICIENT families are exactly the
cases the preregistration anticipated and pre-committed to failing
without a fallback contrast.

## 17. Multiplicity table

M_binding = **11 per family**; two families (futureMFE, remaining P&L);
BH applied **within each**; **M_total = 22**. Every binding cell is
reported above including all failures. **No cell was removed from the
family after seeing nulls.**

- Tail family best raw p 0.0072 (F5align@T5) → **BH q 0.079**.
- Loss family best raw p 0.0234 (F6@T15) → **BH q 0.257**.
- **Nothing anywhere reaches q ≤ 0.05.**

Programme cumulative multiplicity (24 before this study, 46 after) is
reported as **NON-BINDING sensitivity only** and does not alter these
verdicts.

## 18. Permutation results

Frozen stratified day-respecting label permutation, P = 20,000, seed
20260826, preserving OFH13 side, frozen partition and day-block
structure (implementation disclosure I1 in the engine header). Three
tail cells have perm p ≤ 0.05 — F2G1@T5 (0.004), F3@T5 (0.007),
F5align@T5 (0.009) — but **all three fail P7 anyway because BH q > 0.05,
and all three fail the incrementality duty.** The permutation was not
degenerate here (unlike a within-day rotation at ~1.2 events/day, which
is exactly why the frozen null was a stratified permutation).

## 19. Temporal destruction

Partition agreement (of 3) and calendar-quarter agreement, tail family:
F1@T5 1/3, F1@T15 3/3, F2G1@T5 2/3, F2G1@T15 3/3, F3@T5 2/3, F3@T15
1/3, F4@T5 2/3, F4@T15 1/3, F5align@T5 3/3, F5align@T15 2/3, F6@T15
3/3. **No period was excluded and no partition is OOS.**

A structural limit worth naming: at T15 only **one** calendar quarter
reaches the ≥20-event threshold, so P8's quarter clause is close to
untestable there. This was inherent in the frozen design at n = 73 and
is not grounds to relax the gate.

## 20. Long/short destruction

Side asymmetry is pervasive and consistent with the known OFH13
short-side skew. Tail family: F1@T5 LONG −30.23 / SHORT +40.43 (sign
disagreement → P9 fails); F5align@T5 +38.23 / +62.08 (agree);
F4@T5 +35.19 / −43.93 (disagree). **No long-only or short-only candidate
was created**, and no side-specific rule is proposed.

## 21. Time-of-day destruction

Frozen buckets with the pre-declared PM floor of 10. The limitation is
prominent and was flagged before results: **RTH_PM holds only 13 events
at T5 and 12 at T15** against 82 and 61 in RTH_AM. Several cells fail
P10 on a PM cell built from ~12 trades (F1@T5 PM −98.12; F5align@T5 PM
−69.69; F3@T5 loss PM −0.73). **The ToD gate is weak for OFH13 and its
verdicts should carry little weight**, exactly as the preregistration
recorded. The gate was neither strengthened nor weakened at execution.

## 22. Tail destruction (both duties, kept separate)

**A · Artifact destruction.** Top-1%/5% trims and drop-1: F3@T5 is the
most robust (trims +30.64/+27.86, drop-1 +45.90 — the effect *grows*
when the single most influential event is removed). F5align@T5 holds
(+35.42/+43.17) but drop-1 retention is 69% — just under the 70% floor,
so P12 fails. F1@T5 flips sign under the 1% trim.

**B · Tail identification.** With the full distribution restored, P13
passed everywhere (§14): the flagged winners genuinely had their move
ahead of them.

These were kept distinct throughout. No cell was rejected merely for
being tail-dependent in the economic sense, and none was credited merely
for surviving a trim.

## 23. Fifteen-gate table

**TAIL family (futureMFE)**

| cell | T | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 | P12 | P13 | P14 | P15 | passed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | 5 | P | P | P | F | F | F | F | F | F | F | P | F | P | P | P | 7/15 |
| F1 | 15 | P | P | P | F | F | P | F | F | P | P | P | F | P | P | P | 10/15 |
| F2G1 | 5 | P | P | P | F | F | P | F | P | P | P | P | F | P | P | P | 11/15 |
| F2G1 | 15 | P | P | P | F | F | P | F | F | P | P | P | F | P | P | P | 10/15 |
| **F3** | **5** | P | P | P | **F** | **F** | P | **F** | P | P | P | P | P | P | P | P | **12/15** |
| F3 | 15 | P | F | P | F | F | F | F | F | F | F | P | F | P | P | P | 6/15 |
| F4 | 5 | P | F | P | F | F | F | F | F | F | P | P | F | P | P | P | 7/15 |
| F4 | 15 | P | F | P | F | F | F | F | F | P | F | F | F | P | P | P | 6/15 |
| F5align | 5 | P | P | P | F | F | P | F | P | P | F | P | F | P | P | P | 10/15 |
| F5align | 15 | P | P | P | F | F | F | F | F | P | P | P | F | P | P | P | 9/15 |
| F6 | 15 | P | P | P | F | F | F | F | F | P | P | P | F | P | P | P | 9/15 |

**LOSS family (remaining P&L)**

| cell | T | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 | P12 | P13 | P14 | P15 | passed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| F1 | 5 | P | P | P | F | F | F | F | F | F | F | P | F | P | P | P | 7/15 |
| F1 | 15 | P | P | P | F | F | F | F | F | P | P | P | F | P | P | P | 9/15 |
| F2G1 | 5 | P | P | P | F | F | F | F | P | P | P | P | F | P | P | P | 10/15 |
| F2G1 | 15 | P | P | P | F | F | F | F | F | P | P | P | F | P | P | P | 9/15 |
| F3 | 5 | P | P | P | F | F | F | F | P | P | F | P | P | P | P | P | 10/15 |
| F3 | 15 | P | F | P | P | P | F | F | F | P | P | P | F | P | P | P | 10/15 |
| F4 | 5 | P | F | P | F | F | F | F | P | F | P | P | P | P | P | P | 9/15 |
| F4 | 15 | P | F | P | F | F | F | F | F | P | F | F | P | P | P | P | 7/15 |
| F5align | 5 | P | P | P | F | F | F | F | P | P | F | P | F | P | P | P | 9/15 |
| **F5align** | **15** | P | P | P | **P** | **P** | F | F | F | P | P | P | F | P | P | P | **11/15** |
| F6 | 15 | P | P | P | F | F | P | F | F | P | P | P | F | P | P | P | 10/15 |

**P7 (BH q ≤ 0.05 AND permutation ≤ 0.05) failed in all 22 cells.**
**P4/P5 (incrementality) failed in 20 of 22.**

## 24. Candidate ranking

Ranked on incrementality, robustness and interpretability — not p-value:

1. **F3 structural acceptance @ T5 (12/15)** — best raw destruction
   profile in the study, strong permutation support (0.007), and the
   only cell whose effect *strengthens* under drop-1. Killed by
   incrementality: 5% residual retention. Acceptance is early MFE/MAE
   in structural clothing.
2. **F5align @ T5 (10/15)** — largest raw effect (+51.30) and best raw
   p (0.0072), but 32% residual retention and a *sign-reversing* matched
   construction. Alignment is net progress restated.
3. **F2G1 @ T5 (11/15)** — good permutation support, but the residual
   sign flips. Shape is level.

None advanced.

## 25. Candidate ceiling

Permitted: ≤1 TAIL-DEVELOPMENT and ≤1 LOSS-FAILURE, maximum 2.
**Advanced: 0 and 0.** Runner-ups were not promoted. **0 / 22 binding
cells passed every required gate.**

## 26. Exact verdict

> **OFH13-POSTENTRY-V1 FOUND NO NEW CAUSAL POST-ENTRY SEPARATOR.**

Per-cell frozen verdicts:

| cell | T | tail-family verdict | loss-family verdict |
|---|---|---|---|
| F1 | 5 | REDUNDANT WITH EARLY RETURN | REDUNDANT WITH EARLY RETURN |
| F1 | 15 | REDUNDANT WITH EARLY RETURN | REDUNDANT WITH EARLY RETURN |
| F2G1 | 5 | REDUNDANT WITH EARLY MFE/MAE | REDUNDANT WITH EARLY MFE/MAE |
| F2G1 | 15 | REDUNDANT WITH EARLY MFE/MAE | REDUNDANT WITH EARLY MFE/MAE |
| F3 | 5 | REDUNDANT WITH EARLY MFE/MAE | REDUNDANT WITH EARLY MFE/MAE |
| F3 | 15 | INSUFFICIENT | INSUFFICIENT |
| F4 | 5 | INSUFFICIENT | INSUFFICIENT |
| F4 | 15 | INSUFFICIENT | INSUFFICIENT |
| F5align | 5 | REDUNDANT WITH EARLY RETURN | REDUNDANT WITH EARLY RETURN |
| F5align | 15 | REDUNDANT WITH EARLY RETURN | TAIL-DEPENDENT |
| F6 | 15 | REDUNDANT WITH EARLY RETURN | REDUNDANT WITH EARLY RETURN |

### What this actually established

The consistent finding across all six families is that **OFH13's
post-entry path has already told you everything it is going to tell you
by the time you have measured early return, early MFE and early MAE.**
Efficiency, excursion shape, structural acceptance, directional
alignment and acceleration are all — to within the resolution of 73–95
events — re-descriptions of those three numbers. F3 is the sharpest
illustration: a +38.10 pt raw separation with excellent robustness that
residualises to +1.86 pt.

This is the same answer OFH13-V2 reached from the opposite direction
(winners announce early, but so do losers), now established causally
rather than by outcome-conditioned anatomy.

## 27. Epistemic limitations

- All OFH13 history is **development data**; no partition is OOS; no
  protected segment exists.
- The baseline controls were themselves pre-contaminated (§3).
- The study is **underpowered by construction**, as the preregistration
  stated before results: 73–95 events, ~20–32 per arm, BH across 11
  cells per family, and a heavy-tailed endpoint. **A null was the
  expected outcome and is fully valid.**
- Three structural limits, all recorded before or independently of the
  outcomes: the matched construction is computable in only 8/22 cells
  (§15); at T15 only one calendar quarter reaches the P8 threshold
  (§19); RTH_PM holds ~12 events so P10 is weak (§21).
- **Per the frozen underpowering rule, this null authorizes nothing**:
  no lower floors, no new checkpoints, no new feature families, no
  different contrasts, no uncorrected p-values, no side-only rescue.
  Any alteration is a new V2 preregistration.

## 28. Prospective implications

No candidate survived, so **nothing is frozen, nothing is shadow-logged,
and no prospective lane is created.** OFH13_PROSPECTIVE_V1 continues
exactly as frozen.

The operational constraint recorded in the preregistration stands and is
now moot for this study: the prospective logger records only
end-of-trade fields and no per-minute path, so any future post-entry
state object would require a logger extension. **This study does not
authorize that extension**, does not authorize any management rule, and
does not authorize any live or Sim order change. Any economic
translation requires a separate **OFH13-MGMT-HYP-V1** preregistration.

## 29–34. Artifacts and provenance

| item | path | sha256 |
|---|---|---|
| preregistration | `docs/OFH13_POSTENTRY_V1_PREREGISTRATION.md` | `90490ecba8556cf9f4d6facb44fdf186aa3355aafc3e20651d2af64198fe44b3` |
| eligibility (counts-only) | `analysis/ofh13post/elig_counts.py` | committed at `f4964c9` |
| engine | `analysis/ofh13post/postentry_run.py` | `003ec201070bdf5ea609fdc2e271e32d0459467609b563cc6b56e7dfcb101079` |
| raw output (text) | `analysis/ofh13post/POSTENTRY_OUTPUT.txt` | `ad3b403b6d3d9923d142482bcce2551521c1a663c0374c67d98a3ae4d6d411f6` |
| raw output (machine-readable) | `analysis/ofh13post/POSTENTRY_RAW.json` | `ebb1508cc37b2b857fa3550d70f7ab7113455403b6bebd97c0c4f00b6b6860c7` |

The JSON carries every binding cell — N, days, arm means in points and
in R, futureMFE, futureMAE, remaining P&L, stop probability, effect
sizes, residualised and matched results, CIs, p-values, q-values,
permutation values, full destruction tables and all fifteen gate
results — including every failing cell. The engine is deterministic;
seed 20260826 is the only source of randomness.

**Engine defect disclosure:** one dead line (a redundant `mfe_fin`
expression immediately overwritten by the explicit loop below it) was
removed **before the engine was ever run** — no outcome had been
computed or viewed, and no frozen semantic object was affected. No other
defect was found. One implementation disclosure (I1, the exact
day-block permutation construction) is recorded in the engine header.
The preregistration was **not** edited.

Execution UTC **2026-08-27T13:39Z** · findings written 2026-08-27T13:41Z.
Commit and clean-tree confirmation are recorded in the commit adding
this file.

---

**OFH13-POSTENTRY-V1 FOUND NO NEW CAUSAL POST-ENTRY SEPARATOR. STUDY
CLOSED. NO V1 RESCUE.** OFH13's entry, ATR1.5 stop, 60-minute exit and
prospective logger are unchanged. No management rule was tested. No
orders. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
