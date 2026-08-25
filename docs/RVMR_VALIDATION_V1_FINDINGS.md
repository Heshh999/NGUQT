# RVMR-VALIDATION-V1 — FINDINGS

## **COMBINED VERDICT — CASE 1**

> **TRACK A: FULL OUT-OF-MARKET REPLICATION** (both tools, zero recalibration)
> **TRACK B: MODEST INCREMENTAL VALUE BEYOND ATR** (both tools)

RVMR transports intact to a market it was never built on, **and** it
retains roughly a quarter to a third of its separation after controlling
for ATR, time of day and year. It is a real cross-market
movement-magnitude phenomenon that is **not merely a restatement of
realized volatility** — but ATR remains the single strongest predictor,
and RVMR's contribution is a genuine minority share.

Nothing frozen was modified. All results are **HISTORICAL RESEARCH**.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

Raw output: `analysis/rvmr_val/TRACK_A_OUTPUT.txt`,
`analysis/rvmr_val/TRACK_B_OUTPUT.txt`.

---

## 1. Frozen RVMR source provenance

| item | value |
|---|---|
| spec | `analysis/rvmr/rvmr_spec.py` · `e348f035a9209540…` · commit `84933d2` |
| engine | `analysis/rvmr/rvmr_run.py` · `8743161d6fb5b04e…` · commit `9d14dfa` |
| certificate | `docs/RVMR_V1_SPEC.md` · `3197e013c3d8521a…` · commit `68ed951` |

Formulas read from source: `trailing_ratio(x, W=1440) = x[i] / mean(x[i−1440…i−1])`,
**current bar excluded from its own normaliser**; RANGE = trailing_ratio(high−low);
VOLUME = trailing_ratio(volume); `atr20` = SMA(20) of true range ending at j.
Thresholds **1.270 / 2.335** confirmed from source, identical for both tools.
Horizons (5, 10, 15, 30, 60); primary target median `abs_30`. Universe:
RTH 570–960, ≥60 min to close, ATR20 > 0, both scores non-None, 60
minute-contiguous forward bars.

## 2. Pre-registration

| | |
|---|---|
| path | `docs/RVMR_VALIDATION_V1_PREREGISTRATION.md` |
| sha256 | `025598ad685e617ca8ea4d2d044be52e38343de22ac2db899a22958ea4b161c3` |
| commit | `531759c4101a36c2622b445ebde0eb50d0d015aa` |
| timestamp | 2026-08-25T08:17:53+00:00 |

## 3. Result-blindness

**Every pass rule, verdict band, ATR definition, stratification scheme
and statistical method was frozen and pushed before the engines existed.**
No Track A or Track B number had been calculated at commit time. The
retention bands (≥50 / 20–50 / 5–20 / <5%) that decide Track B's verdict
were fixed in advance, so the answer could not be argued after the fact.

### Parity gate — the results rest on a verified transcription

`val_lib.features` was checked against the **frozen** `rvmr_run.features`
before a single ES number was computed:

```
universe size 510,309  MATCH
columns i, day, mod, rb, vb, rr, vr, abs5, abs10, abs15, abs30, abs60
                        0 mismatches each
PARITY GATE: PASS
```

### One implementation defect, found and fixed

The first Track B run used a day-clustered OLS bootstrap that rebuilt a
593k-row design matrix on every one of 2,000 iterations — **computationally
infeasible**, and my design error. It was killed and restructured using
per-day sufficient statistics: OLS normal equations are additive over
observations, so `X'X(sample) = Σ over sampled days of (X'X)_day`. The
estimator, resampling unit and coefficients are **identical**; only the
arithmetic changed, which made the pre-registered **20,000** iterations
feasible. Re-running reproduced the earlier B4 figures to four decimals
(RANGE +4.6052, retention 32.7%), confirming determinism.

---

# TRACK A — RVMR-ES-V1

## 4. ES dataset provenance

`scratchpad/es_bar1m`, **2,542,424** genuine 1-minute bars,
2019-06-02 18:02 → 2026-08-17 16:59, captured by `V41Bar1mCaptureHost`,
certified by ES-NQ-DATA-V1 (Gate 1 PASS, Gate 2 PASS, commit `0910732`).
**Eligible universe: 602,664 bars over 1,858 days.**

## 5. ES label distribution — the calibration test

| tool | LOW | MEDIUM | HIGH | smallest |
|---|---|---|---|---|
| RANGE | 248,860 (41.29%) | 254,557 (42.24%) | 99,247 (16.47%) | **16.47%** |
| VOLUME | 143,426 (23.80%) | 226,378 (37.56%) | 232,860 (38.64%) | **23.80%** |

**A7 PASS both.** This is the result I expected least: A7 was written
anticipating that NQ's absolute cutoffs would not transport. They do.
The distributions are skewed — RANGE toward LOW/MED, VOLUME toward HIGH —
but every bucket sits far above the 5% floor. **There is no
"mechanism-works-calibration-fails" split to report**, so the ES-internal
tercile diagnostic is reported and set aside, exactly as pre-registered.

## 6–7. Horizon table and monotonicity

**RANGE-REGIME-V1** (median |ret|, points)

| bucket | n | 5m | 10m | 15m | 30m | 60m |
|---|---|---|---|---|---|---|
| LOW | 248,860 | 1.50 | 2.00 | 2.50 | 3.50 | 5.00 |
| MEDIUM | 254,557 | 2.00 | 2.75 | 3.25 | 4.75 | 6.75 |
| HIGH | 99,247 | 2.50 | 3.75 | 4.50 | 6.25 | 8.25 |

**monotone 5 of 5 horizons.** mean@30 HIGH 8.94 CI[8.65, 9.24] · LOW 5.45
CI[5.27, 5.64] · **HIGH−LOW +3.489, day-clustered CI [+3.224, +3.758]** ·
H/L 1.640× · H/M 1.259× · full Spearman +0.1939 (point estimate only) ·
**day-level Spearman +0.4048 over 1,858 days, day-shuffle p = 0.00005**.

**VOLUME-REGIME-V1**

| bucket | n | 5m | 10m | 15m | 30m | 60m |
|---|---|---|---|---|---|---|
| LOW | 143,426 | 1.25 | 1.75 | 2.25 | 3.00 | 4.50 |
| MEDIUM | 226,378 | 1.75 | 2.50 | 3.00 | 4.25 | 6.00 |
| HIGH | 232,860 | 2.25 | 3.25 | 4.00 | 5.50 | 7.50 |

**monotone 5 of 5 horizons.**

## 8. Year stability — 8 of 8, both tools

RANGE `HIGH−LOW` by year: 2019 → 2026 all positive, **mono 5/5 every
year**, rising from +1.4-class early years to **+4.15 (2025)** and
**+5.37 (2026)**. VOLUME: +1.39 / +2.73 / +2.75 / +3.47 / +2.13 / +2.35 /
+3.81 / +4.44 — **8 of 8 positive, mono 5/5 every year.**

## 9. Month stability — nothing hidden

| tool | months | positive | median | worst | best |
|---|---|---|---|---|---|
| RANGE | 87 | **87 (100%)** | +2.50 | +0.75 (2024-05) | +7.50 (2026-02) |
| VOLUME | 87 | 86 (99%) | +2.00 | **+0.00 (2025-04)** | +5.75 (2026-02) |

The single flat month is named rather than omitted.

## 10. Time of day — not a clock artifact

Monotone **5/5 in all four frozen session buckets**, both tools.
Per-minute ToD-matched separation retains **85%** (RANGE) and **102%**
(VOLUME) of pooled separation. A6 PASS.

## 11. Persistence — decays like NQ

Mean 1-minute range after the state, H/L ratio:

| window | +3 | +5 | +10 | +15 | +30 |
|---|---|---|---|---|---|
| RANGE | 1.84 | 1.84 | 1.77 | 1.74 | **1.69** |
| VOLUME | 2.00 | 1.89 | 1.84 | 1.81 | **1.75** |

Elevated movement persists and decays gradually — the same shape the NQ
certification recorded.

## 12–13. RANGE and VOLUME — both transport

Both pass all seven conditions independently. **Caveat: the two ES scores
correlate at Spearman +0.7297**, so they are *not* independent
confirmations of one another.

## 14. Symmetry — the certified reading holds on ES

| tool | bucket | med MFE60 | med MAE60 | MFE/MAE |
|---|---|---|---|---|
| RANGE | LOW | 5.25 | 5.00 | 1.050 |
| | MEDIUM | 6.75 | 6.75 | 1.000 |
| | HIGH | 8.25 | 8.50 | **0.971** |
| VOLUME | LOW | 4.75 | 4.50 | 1.056 |
| | MEDIUM | 6.25 | 6.25 | 1.000 |
| | HIGH | 7.50 | 7.75 | **0.968** |

HIGH enlarges **both** excursions together. **No directional asymmetry
appeared**, so there is nothing here to be tempted into a strategy
hypothesis — and the direction-free certificate is confirmed on a second
market.

## 15. Tail destruction

| | RANGE | VOLUME |
|---|---|---|
| full | +3.489 | +3.334 (roll-clean) |
| drop top 1% | +2.916, mono 5/5 | +2.872, mono 5/5 |
| drop top 5% | **+2.009, mono 5/5** | **+2.041, mono 5/5** |

Not tail-driven. Secondary slices: roll-quarantined +3.500 / +3.334;
pre-discovery window +3.174 / +3.037 — both mono 5/5.

## 16. **TRACK A VERDICT: FULL OUT-OF-MARKET REPLICATION** (both tools)

All 7 conditions PASS × 2 tools = 14/14.

---

# TRACK B — RVMR-INCR-V1

## 17–18. Frozen ATR definition and state

**PRIMARY ATR = ATR20**, SMA of true range over the 20 bars ending at j,
1-minute resolution, current bar included (legal: bar j is complete at
its close stamp), available at the close stamp and never earlier. **No
period sweep was performed, before or after results.**

**ATR STATE = `trailing_ratio(ATR20)`, W = 1440, current bar excluded
from the normaliser** — the identical construction RVMR itself uses. This
was deliberate: it removes any possibility that RVMR looks better merely
because it is a relative measure while ATR is absolute. **Quintiles**
(stricter than terciles), cutpoints from the **first full year only**,
then applied unchanged. NQ eligible universe 593,190 bars.

**Reference to beat** (HIGH vs LOW∪MED, unconditional):
RANGE **+14.099** CI[+13.073, +15.219] · VOLUME **+13.135** CI[+12.370, +13.987].

## 19–20. ATR × RVMR surface — within-ATR monotonicity

**RANGE — monotone in 5 of 5 populated ATR quintiles.**

| ATR q | LOW | MEDIUM | HIGH | mono |
|---|---|---|---|---|
| q0 | 52,819 → 10.50 | 5,210 → 12.00 | 542 → 28.75 | Y |
| q1 | 74,228 → 15.25 | 26,450 → 16.00 | 2,802 → 23.00 | Y |
| q2 | 74,359 → 18.50 | 69,861 → 19.25 | 10,323 → 24.25 | Y |
| q3 | 32,580 → 21.50 | 83,780 → 23.75 | 25,257 → 25.50 | Y |
| q4 | 6,104 → 25.50 | 60,796 → 29.00 | 68,079 → 32.25 | Y |

**VOLUME — monotone in 4 of 5** (fails at q4, the highest-ATR stratum,
where 114,160 of 134,979 observations are VOLUME-HIGH and the LOW cell
holds only 1,787).

## 21. Time-of-day-controlled result

Monotone in **13 of 19** populated (ATR × ToD) cells for RANGE and
**14 of 20** for VOLUME. The failures are concentrated where the control
is most degenerate — RANGE at low-ATR mid-session, VOLUME at q4. Both
tools are monotone in **every OPEN-session cell** except VOLUME q4.

## 22. Continuous model — the most informative single result

Standardized rank OLS with ToD fixed effects, day-clustered CIs from
**20,000** whole-day resamples:

| coefficient | β | 95% CI | |
|---|---|---|---|
| **ATR** | **+0.1817** | [+0.1634, +0.1995] | CI excludes 0 |
| **RANGE** | **+0.0052** | [−0.0094, +0.0197] | **CI INCLUDES 0** |
| **VOLUME** | **+0.0844** | [+0.0620, +0.1072] | CI excludes 0 |

Standalone and pairwise:

| model | β_ATR | β_RANGE | β_VOLUME |
|---|---|---|---|
| ATR alone | **+0.2575** | — | — |
| RANGE alone | — | +0.2148 | — |
| VOLUME alone | — | — | +0.2293 |
| ATR + RANGE | +0.2100 | **+0.0680** | — |
| ATR + VOLUME | +0.1895 | — | **+0.0987** |
| all three | +0.1817 | **+0.0052** | +0.0844 |

Secondary, raw units: β_ATR +9.0927 · β_RANGE +1.7706 · β_VOLUME +0.5383 pts.

## 23. Matched incremental test — the primary

| tool | matched n | HIGH − control | day-clustered 95% CI | p | **retention** |
|---|---|---|---|---|---|
| RANGE | 106,948 | **+4.6052** | [+3.4566, +5.8210] | 0.0000 | **32.7%** |
| VOLUME | 230,178 | **+3.4503** | [+2.5077, +4.4125] | 0.0000 | **26.3%** |

Cells = (ATR quintile × ToD bucket × year), dropped symmetrically so
missing control coverage cannot flatter the signal. **Roughly two-thirds
of RVMR's raw separation is explained by ATR, time of day and year; about
one-third is not.**

## 24–26. RANGE and VOLUME separately, and after each other

- **RANGE after ATR alone: β +0.0680, survives.**
- **VOLUME after ATR alone: β +0.0987, survives.**
- **RANGE after ATR *and* VOLUME: β +0.0052, CI includes 0 — absorbed.**
- **VOLUME after ATR *and* RANGE: β +0.0844, CI excludes 0 — survives.**

This is the sharpest finding in Track B. Each tool is incremental to ATR
on its own, but **RANGE's incremental content is almost entirely shared
with VOLUME, while VOLUME retains independent information after both.**
In the matched test RANGE scores higher (32.7% vs 26.3%) because matching
does not partial out the other tool; in the joint model, which does,
VOLUME is the one that stands alone.

## 27. Year stability — 8 of 8, both tools

RANGE: +1.95 / +2.35 / +3.11 / +6.01 / +3.55 / +3.79 / +6.30 / **+11.11**
VOLUME: +1.56 / +0.62 / +4.71 / +3.52 / +2.53 / +3.53 / +5.70 / +4.13

**All sixteen year-tool cells positive.** No single-year domination; the
effect is strengthening in recent years rather than decaying.

## 28. Tail destruction

| | RANGE | VOLUME |
|---|---|---|
| full matched | +4.6052 | +3.4503 |
| drop top 1% | +3.1323 | +2.8784 |
| drop top 5% | **+1.8213** | **+1.6780** |

Attenuates but stays clearly positive. **Not tail-dependent.**

## 29. Dependence-aware statistics

The **day is the cluster unit everywhere**. Day-clustered bootstrap
(20,000) for every delta and coefficient; day-shuffle permutation
(20,000) for Track A. **No i.i.d. minute-level standard error or p-value
is reported anywhere in this study**, and 593k/603k minute bars are never
treated as independent trials. Multiplicity: **M = 4**, BH and Holm —
all four primary endpoints have permutation/bootstrap p < 0.0001, so
every q < 0.001 and correction changes nothing.

## Slow regime vs local state

| tool | live label | 3-day-lagged label | **slow share** |
|---|---|---|---|
| RANGE | +4.6052 | +1.9252 | **42%** |
| VOLUME | +3.4503 | +2.4754 | **72%** |

Both components exist. **RANGE's incremental-to-ATR information is
majority LOCAL (58%)**; **VOLUME's is majority SLOW multi-day clustering
(72%)**. No trading rule is derived from this decomposition.

## 30. **TRACK B VERDICT: MODEST INCREMENTAL VALUE BEYOND ATR** (both tools)

---

# 31. Combined interpretation

**CASE 1: A PASSES, B PASSES.** RVMR is a genuine cross-market
movement-regime phenomenon that adds real, if minority, information
beyond ordinary realized volatility.

Three things are now established that were not before:

1. **It is not an NQ artifact.** The exact mechanism, with the exact
   NQ-fitted cutoffs, reproduces on 602,664 ES bars — 8/8 years,
   87/87 months, 5/5 horizons, p = 0.00005.
2. **It is not merely ATR in slow motion.** After controlling for ATR
   quintile, time-of-day bucket and year, 26–33% of the separation
   survives, positive in all 16 year-tool cells.
3. **It remains strictly direction-free.** ES MFE/MAE is 1.05 / 1.00 /
   0.97 across LOW/MED/HIGH — symmetric expansion, on a second market.

Equally, the honest limits:

- **ATR is still the strongest single predictor** (β +0.2575 alone vs
  RANGE +0.2148, VOLUME +0.2293), and **two-thirds of RVMR's raw
  separation is explained by ATR/ToD/year.**
- **RANGE is largely redundant with VOLUME** once both are in the model.
- The two tools correlate at +0.73 and are not independent evidence.
- Track B's B2 surface fails in 6 of 19 and 6 of 20 cells, concentrated
  where the strata are degenerate.

# 32. Should the RVMR certificate change?

**Yes — it should be strengthened in scope, and qualified in
independence.** The certified role is unchanged: **direction-free,
symmetric, movement-magnitude context.** What the certificate may now
add:

- **cross-market validated** on ES with zero recalibration;
- **incremental to ATR and time of day at ~26–33% retention**, so it is
  not a pure volatility restatement;
- **with the qualification** that ATR dominates, and that RANGE's
  independent contribution is largely absorbed by VOLUME.

The two closed questions stay closed: **RVMR is still not direction, not
entry, not grading, not avoidance.** RVMR-STRAT-V1 and RVMR-AVOID-V1 are
unaffected by this study.

# 33. Is RVMR-BANDS-V1 justified?

**YES — as a proposal only. It was not built in this run**, as
pre-registered. A short proposal follows this document; the essential
design requirement is that any band be **benchmarked head-to-head against
ATR-only bands**, because Track B shows ATR carries the larger share.

# 34–35. Commit and tree

Recorded in the reply accompanying this document.

---

## FINAL QUESTIONS

1. **DOES FROZEN RVMR REPLICATE ON ES?** — **YES**
2. **DO THE EXACT NQ THRESHOLDS TRANSPORT WITHOUT RECALIBRATION?** — **YES**
3. **DOES RVMR ADD INFORMATION BEYOND ATR?** — **MODESTLY**
4. **DOES RVMR ADD INFORMATION BEYOND ATR + TIME OF DAY?** — **MODESTLY** (26–33% retention, 16/16 year-tool cells positive)
5. **WHICH COMPONENT IS STRONGER AFTER CONTROLS?** — **VOLUME** (survives ATR *and* RANGE at β +0.0844; RANGE collapses to +0.0052 with CI including 0)
6. **IS RVMR STILL BEST DESCRIBED AS A DISTINCT MOVEMENT-REGIME TOOL?** — **YES**, with ATR acknowledged as the larger single component
7. **SHOULD WE PROCEED TO RVMR-BANDS-V1?** — **YES** (proposal only, benchmarked against ATR-only bands)

**THE FORWARD LOGGER CONTINUES UNCHANGED AND UNCONTAMINATED.
OFH13_PROSPECTIVE_V1 REMAINS UNTOUCHED.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
