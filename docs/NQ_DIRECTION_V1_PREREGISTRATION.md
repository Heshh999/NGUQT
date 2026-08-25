# NQ-DIRECTION-V1 — PRE-REGISTRATION

**PREREGISTRATION ONLY. The study has NOT been run.** At this commit no
directional accuracy, hit rate, P(up), P(down), signed return, MFE, MAE,
favourable-first, Brier score, log loss, p-value, q-value, ranking or
P&L exists for any hypothesis. The only computation performed was a
**counts-only feasibility and defect check** (Step 30), which printed
event counts, day counts, year counts and long/short splits and
**nothing about outcomes**.

**Offline historical research.** Nothing frozen is modified:
`OFH13_PROSPECTIVE_V1`, `OFH14_PROSPECTIVE_V1`, RVMR-V1, the RVMR
forward logger, every prospective ledger, and the parity-verified NT8
prospective host are untouched. No orders, no Sim101, no integration.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

# 1. DIRECTIONAL LINEAGE AUDIT (read from repository)

| family | mechanism | result | why | reusable? |
|---|---|---|---|---|
| OF-H (12) | directional order flow | 0 of 12 proven | OFH6 family-wise p 0.129; edge vanishes once a stop is added | **NO** |
| OF-N (12) | order-flow events | 0 promoted; OF-N6 +6.49 p 0.078 q 0.63 | never cleared family correction | **partly** — see H2 |
| OF-SUB / OFFVG / RED (4) | order-flow variants | 0 promoted | none passed raw geometry | **NO** |
| MAG-AUC (15) | magnitude + auction | 1 survivor (MAG-H3, q 0.0008) but **magnitude, not direction**; all 11 directional cells fail | verdict: "ORDER FLOW … MORE USEFUL AS A MAGNITUDE / REGIME FEATURE THAN AS A DIRECTIONAL SIGNAL" | **NO** (as direction) |
| V4 / V4.2 / V4.2B / V5 (30+) | FVG + order-flow failure | V5: 0 of 10; V4.2: 9 of 10 fail, G4-FVG n=27 only | small-n or inverted | **NO** |
| BRK-V1 (3) | bracket / 15s compression / overnight drift | 0 promoted; BRK-H2 **VOID** (my spec error); OVN-H1 p 0.413 | BRK-H1 clears q and is still untradeable | overnight thread **unresolved** |
| MRV-V1 (10) | mean reversion / V-recovery | 0 survive; premise **inverted** — adding failure evidence made fades worse | — | **NO** (fades) |
| MRV MR-H3 | **15m sweep → reclaim** | n 581 · R 1.23 · ff 54.7% · sign-stable U/DEV/IR · "second independent replication"; logged as a lead for a future pre-registered test | failed family accounting only | **YES → DIR-H1** |
| GEN-10 | 10 exploratory | G9 impulse-pullback-into-FVG n 483 p 0.163 | exploratory by construction | **partly → DIR-H2** |
| OFH14 | FVG pullback | n 392 · +8.43 · p 0.046 · q 0.635 | on the prospective shelf; not re-tested here | reference only |
| RVMR-STRAT (Track B, 8) | RVMR-native strategies | B1 accepted breakout −1.16 · B2 pullback −0.04 · B4 VWAP **significantly negative** · B6 **VOID** · B7 opening n=192 control wins | — | **NO** |
| RVMR-AVOID (7) | counter-movement avoidance | no avoidance rule | HIGH inflates MFE and MAE together | **NO** |
| RVMR-VALIDATION | ES transport + ATR increment | replicates; modest beyond ATR; **direction-free** | — | control variable only |
| RVMR-BANDS-V1 | absolute-point quantile bands | **BAND CALIBRATION NOT RELIABLE** | non-stationary point volatility | **NO** |
| XMARKET-V1 (8) | ES cross-market | 0 of 8; H8 **VOID** (my spec error) | ES confirms 91.6% of breakouts — a near-constant | **NO** |
| XMARKET H1 NQ-alone arm | **accepted balance-breakout continuation** | n **11,065** · mean −0.909 · ff 47.2% · MFE/MAE 0.990 | directly measured, directionally flat | **NO — KILLED** |

## 2. Killed mechanisms explicitly EXCLUDED from this family

- **Balance-acceptance breakout continuation.** Directionally measured
  twice on large samples — XMARKET H1 NQ-alone (n = 11,065, ff 47.2%,
  MFE/MAE 0.990) and RVMR-STRAT B1 (n = 2,905, EV −1.16 vs control
  −1.06). Both flat-to-negative. Re-testing it as "DIR-H1" would be
  recycling a killed hypothesis under a new name, which this
  pre-registration forbids. **It is not in the family.**
- Order flow as a *primary* direction signal (~90 hypotheses, 0 survivors).
- Mean-reversion / fade-after-extension (MRV: inverted, not merely null).
- VWAP reversion (B4: significantly negative).
- ES cross-market confirmation (XMARKET: 0 of 8).
- RVMR as a direction or avoidance source (STRAT + AVOID: clean failures).

## 3. Repeated mechanisms RETAINED, and why each earns one clean test

1. **Sweep → failed acceptance → reclaim** — the only mechanism in the
   entire programme with a *second independent replication* and
   sign-stability across all three partitions, explicitly logged as a
   lead awaiting a pre-registered test. Never tested with matched
   directional controls at family accounting.
2. **Impulse → controlled pullback → re-expansion** — three independent
   constructions, same sign, none significant: OF-N6 (+6.49, replicated
   +4.83 on the August OOS pass), G9 (+5.58), OFH14 (+8.43, p = 0.046).
   Consistent positive sign across independent code paths is exactly the
   pattern that deserves one mechanical test.
3. **Opening-drive resolution** — MAG found opening-drive origin reclaim
   at q = 0.0008, but as a **magnitude** result; the directional question
   was never cleanly asked. RVMR-STRAT B7 had only n = 192.
4. **Overnight inventory resolution** — BRK states overnight carry "is
   unresolved and is the only remaining thread". OVN-H1 tested *drift*
   (failed); OVN-H3 was **VOID by my specification error** (required an
   RTH open beyond the overnight extreme — 0 events in 247 days on a
   continuous contract). The *resolution* question has never had a valid
   test.
5. **Order flow as an increment** — never asked in the one form that
   could still be true: does delta add information **after** a price
   mechanism has already fired?

---

# 4. FROZEN FAMILY SIZE: **M = 5**

Five mechanisms, fixed now, never expanded after results and **never
shrunk for a failing or void member**. M = 5 rather than 6 because the
sixth recommended slot (balance-acceptance continuation) is a killed
hypothesis and padding the family to hit a number would be dishonest.

# 5. COMMON MECHANICS (all hypotheses)

Canonical NQ 1-minute history via `rvmr_run.load_bars` (STAMP_SHIFT = 0),
2,503,622 bars, 2019-07-04 → 2026-08-17, close-stamped ET. `atr` =
frozen `rvmr_spec.atr20`. `z5(j) = (c[j] − c[j−5]) / atr[j]`, requiring
`em[j] − em[j−5] == 5`.

**Eligible decision bar** `E(j)`: `570 ≤ mod[j] ≤ 930` (so a full 30-min
horizon closes by 16:00); `atr[j] > 0`; `em[j+30] − em[j] == 30` (both
horizons contiguous). **Cooldown 30 minutes, per direction, per
hypothesis.** No interpolation, no forward-fill; a gap voids the event.

# 6. DIR-H1 — SWEEP → FAILED ACCEPTANCE → RECLAIM

```
at bar s:  HI15 = max(high[s-15 .. s-1])      LO15 = min(low[s-15 .. s-1])
           VM   = mean(volume[s-15 .. s-1])            (ALL EXCLUDE bar s)
SWEEP-UP    high[s] > HI15  AND  volume[s] >= 1.5 * VM
RECLAIM r   r = s                       if close[s]  <= HI15
            else first r in s+1..s+5 with close[r] <= HI15
            (no such r within 5 bars -> NO EVENT)
DIRECTION   DOWN.   Mirror for a down-sweep (low[s] < LO15) -> UP.
DECISION BAR = r.  Requires E(r).
```

# 7. DIR-H2 — IMPULSE → CONTROLLED PULLBACK → RE-EXPANSION

```
IMPULSE at p   move = c[p] - c[p-10], |move| >= 1.5 * atr[p], em contiguous
               d = sign(move);  O = c[p-10]
               X = max(high[p-10..p])  (d>0)  |  min(low[p-10..p])  (d<0)
PULLBACK q     first q in p+1..p+15 with retracement
               R = (X - c[q])/(X - O)  (d>0)  |  (c[q] - X)/(O - X)  (d<0)
               satisfying 0.236 <= R <= 0.618
               AND no structural failure: c[q] > O (d>0) | c[q] < O (d<0)
RE-EXPANSION e ref = max(close[p..q]) (d>0) | min(close[p..q]) (d<0)
               first e in q+1..q+10 with c[e] > ref (d>0) | c[e] < ref (d<0)
               -- the ref window ENDS AT q, so it EXCLUDES decision bar e
DIRECTION      d.   DECISION BAR = e.  Requires E(e).
```

# 8. DIR-H3 — OPENING-DRIVE RESOLUTION

```
OPENING RANGE  ORH = max(high[mod 570..584])   ORL = min(low[mod 570..584])
               (09:30-09:44 close stamps; fixed before any decision bar)
DECISION WINDOW mod in [585, 660]  (09:45-11:00) -- broad, pre-declared
ACCEPTANCE     two consecutive closes beyond an edge -> event at the 2nd
               close; direction = the breakout side. One per day per side.
FAILURE (arm)  after that acceptance, the first later close back inside
               [ORL, ORH] -> event; direction = OPPOSITE. One per day.
```

No minute-level window is tested or selected; the two windows above are
the only ones that exist in this hypothesis.

# 9. DIR-H4 — OVERNIGHT INVENTORY RESOLUTION

```
OVERNIGHT      for RTH day T: bars with mod >= 1081 on the prior RTH day
               plus bars with mod <= 569 on T.  ONH = max high, ONL = min low
               (complete by 09:29; requires ONH > ONL)
DECISION WINDOW mod in [571, 660]
ACCEPT-BEYOND  two consecutive closes > ONH (or < ONL) -> event at the 2nd
               close; direction = that side
FAIL-BACK (arm) after acceptance, first later close back inside [ONL, ONH]
               -> event; direction = OPPOSITE
OPEN LOCATION  openLoc = (c[first bar mod 570] - ONL) / (ONH - ONL)
               reported as a declared diagnostic split, never a promoter
```

No directional assumption is made about overnight moves; the frozen
states decide the test.

# 10. DIR-H5 — ORDER-FLOW INCREMENT (data-limited by construction)

Runs **only** on the genuine order-flow archive (355,455 bars, 315 days,
2025-08-18 onward). Nothing is fabricated: bar-level bid/ask volume,
delta and delta% only — **no footprint-at-price, no absorption**.

```
HOST MECHANISM = whichever of DIR-H1..H4 has the MOST events inside the
                 archive window (determined by COUNTS ONLY, declared now)
CONFIRMING   sign(delta[decision bar]) == direction AND |delta%| >= 20
OPPOSING     sign(delta[decision bar]) == -direction AND |delta%| >= 20
NEUTRAL      otherwise
MATCHED PRICE-ONLY CONTROL: the identical host events in the identical
                 matching cells with NO delta condition -- mandatory.
IF host events in the archive < 150  ->  DIR-H5 = INSUFFICIENT DATA,
                 and M REMAINS 5.
```

Primary question: **does order flow add directional information AFTER
price is already known?** If not: NO INCREMENTAL VALUE.

# 11–13. FROZEN TARGETS

```
PRIMARY   DIR15  UP if close[t+15] > close[t]; DOWN if <; TIE if ==
SECONDARY DIR30  same at 30 minutes
TIES      excluded from every hit-rate denominator, counted and reported
          separately (0.25-tick grid makes exact ties rare but real)
PATH      FF05: scanning k = 1..15 from close[t] in the signal direction,
          running MFE/MAE; first to cross +0.5*atr[t] or -0.5*atr[t] wins;
          BOTH crossed inside the same bar -> AMBIGUOUS; neither by 15 ->
          NEITHER.  AMBIGUOUS IS NEVER RESOLVED BY GUESSING and is never
          reassigned to a side.
```

5m and 60m are secondary lineage diagnostics only and cannot promote.

# 14–16. FROZEN BASELINES

- **BASELINE A — time-of-day frequency.** Expanding-window empirical
  P(up at H) per frozen ToD bucket (OPEN 570–629 · MIDMORN 630–719 ·
  MIDDAY 720–809 · AFTERNOON 810–930).
- **BASELINE B — causal NQ price-state.** Expanding-window empirical
  P(up) per cell `(ATR quintile × ToD bucket × sign(z5))` = 40 cells.
  ATR quintiles use the frozen `trailing_ratio(ATR20)` construction with
  cutpoints regenerated from calendar-2019 only (identical to
  RVMR-VALIDATION Track B and RVMR-BANDS).
- **BASELINE C — momentum sign.** Predict UP iff `z5(t) > 0`.

A hypothesis that merely reproduces "price was already going up" fails
against Baselines B and C by construction.

# 17. MATCHED-CONTROL DESIGN

For every signal event, controls are eligible NQ bars in the **same cell**:

```
(ATR quintile x ToD bucket x sign(z5) x RVMR RANGE state x year)
```

assigned the **same direction** as the signal. Cells with no counterpart
are dropped **symmetrically from both sides**. Mechanism-specific
additions, frozen now: H1 sweep distance beyond the extreme in ATR
(tercile); H2 impulse size in ATR (tercile); H3/H4 distance of the
decision close from the reference edge in ATR (tercile).

**The question is always: for otherwise similar NQ states, does this
structural event add directional information?**

# 18–20. PROBABILITY, BRIER, LOG LOSS

```
P(up | signal) = expanding-window frequency of UP among the mechanism's
                 OWN prior same-direction events, refreshed MONTHLY,
                 using only events whose 30-minute horizon matured before
                 the month began.  Training through 2020-06-30; scoring
                 from 2020-07-01 (identical discipline to RVMR-BANDS).
BRIER    = mean( (p_up - y)^2 ),  y = 1 if UP else 0, ties excluded
LOG LOSS = -mean( y*ln(p) + (1-y)*ln(1-p) ), p clipped to [0.001, 0.999]
```

Both are computed for the candidate **and** for Baselines A, B, C on the
**identical scored events**. Lower is better.

# 21. CALIBRATION (frozen, no method competition)

Empirical rolling-origin frequency as above — **no isotonic, no Platt,
no spline, and no comparison between them**. Reliability reported in five
predeclared bins: [0.50,0.55) · [0.55,0.60) · [0.60,0.65) · [0.65,0.70) ·
[0.70,1.00], each with predicted mean, observed frequency and N.

# 22. ABSTENTION (NEUTRAL is first-class)

```
NEUTRAL when  (a) the mechanism has < 100 prior same-direction matured
                  training events at the current monthly refresh, OR
              (b) no matched control cell exists for the event.
```

Coverage %, accuracy-when-active and Brier-when-active are all reported.
**The confidence threshold is frozen here and is NEVER optimized after
results.** A mechanism that abstains most of the time and is reliable
when active is an acceptable and reportable outcome.

# 23. FROZEN SAMPLE GATES (chosen from feasibility counts only)

```
MIN_EVENTS     250 scored events
MIN_DAYS       100 distinct trading days
MIN_YEARS      4 years with >= 20 scored events each
MIN_PER_SIDE   75 long AND 75 short
```

Step-30 feasibility (counts only, no outcomes): H1 19,645 events / 1,830
days / 10,459 L / 9,186 S · H2 22,732 / 1,830 / 11,712 / 11,020 · H3
1,746 acceptance + 1,342 failure · H4 1,413 acceptance + 1,068
fail-back. Every year populated; every mechanism clears the gates with
room, so the gates were not chosen to fit the data.

# 24. FROZEN MATERIALITY GATE

```
MIN_SEPARATION  matched directional hit rate must exceed the matched
                control by >= 3.0 PERCENTAGE POINTS, with a day-clustered
                95% CI excluding 0
MIN_BRIER_GAIN  >= 0.005 absolute improvement vs the BEST of Baselines
                A, B, C on the identical scored events
```

Justification, fixed before results: a directional read that beats a
matched baseline by under 3 pp cannot survive realistic execution costs
at a 15-minute horizon, and 3 pp is near the smallest effect a
day-clustered CI can separate from zero at n ≈ 250–20,000. Brier near a
0.5 base rate is ≈ 0.25, so 0.005 is a 2% relative reduction — the
smallest change that is not rounding.

**A statistically significant but economically trivial separation does
not promote. Neither does "it loses less".**

# 25. YEAR STABILITY

Per year (2019 partial → 2026 partial): N, hit rate, baseline hit rate,
difference, Brier improvement, signed-return sign, MFE/MAE. **Gate:**
separation positive in ≥ **70%** of years holding ≥ 20 events, **and**
the pooled separation with the single best year removed remains > 0.
Small partial years need not be individually significant.

# 26–27. TIME-OF-DAY AND ERA DESTRUCTION

Reported in the four frozen ToD buckets; no bucket may be removed or
down-weighted. Value confined to one bucket → **TIME-SPECIFIC**.
Frozen eras: COVID/extreme 2020 · 2021 · 2022 bear/rates · 2023–24 ·
2025–26. No regime-specific fitting; value confined to one era →
**REGIME-SPECIFIC**.

# 28. LONG / SHORT

Always reported separately, never pooled to hide asymmetry. If one side
survives and the other does not, that is reported exactly. **The weak
side is NOT deleted in V1** — narrowing to one side would require a new
frozen candidate.

# 29. TAIL DESTRUCTION

Largest positive event, largest negative event, top-1% and top-5% share,
mean excluding top 1%, mean excluding top 5%. **Directional separation
is additionally recomputed after removing events in the top 1% and top
5% of |realized 15m move|.** Gate: separation remains > 0 after both.

# 30. MULTIPLICITY AND INFERENCE

**M = 5, frozen.** Raw p, day-clustered bootstrap p and CI (20,000
iterations, seed 20260825, per-day sufficient statistics so the run is
tractable by construction), BH q and Holm at M = 5. **M is never shrunk
for a failing, void or insufficient-data member.** The day is the
cluster unit; no i.i.d. minute-level p-value is reported anywhere.

# 31. PROMOTION GATE — all fourteen required

| # | condition | frozen criterion |
|---|---|---|
| 1 | sample size | §23 gates all met |
| 2 | matched separation | ≥ +3.0 pp, day-clustered CI excludes 0 |
| 3 | proper score | Brier gain ≥ 0.005 vs best baseline |
| 4 | calibration | no reliability bin off by > 7 pp with N ≥ 100 |
| 5 | favourable-first | FF05 favourable share exceeds matched control |
| 6 | MFE/MAE geometry | signal MFE/MAE > control MFE/MAE |
| 7 | long/short transparency | both sides reported; neither catastrophic without explanation |
| 8 | year stability | §25 both parts |
| 9 | no single-era dependence | positive in ≥ 3 of 5 frozen eras |
| 10 | tail robustness | separation > 0 after top-1% and top-5% removal |
| 11 | corrected support | BH q < 0.05 at M = 5 |
| 12 | no leakage | causality audit; every reference window excludes its decision bar |
| 13 | no data artifact | gap/contiguity audit clean |
| 14 | no control artifact | symmetric cell dropping; matched N reported |

# 32. LOGICAL-FEASIBILITY / DEFECT AUDIT (Step 30) — **PASS**

Explicitly checked for the impossible-envelope class of defect that
produced XMARKET-H8 and RVMR-STRAT-B6:

| hypothesis | reference window | decision bar | self-referential? |
|---|---|---|---|
| H1 | `[s−15, s−1]` highs/lows **and** volume mean | s or s+1…s+5 | **NO** |
| H2 | `max/min close[p..q]` | e ≥ q+1 | **NO** |
| H3 | OR = 09:30–09:44 | ≥ 09:45 | **NO** |
| H4 | ONH/ONL complete 09:29 | ≥ 09:31 | **NO** |
| H5 | delta at the host decision bar | same bar, already complete | **NO** |

Every window strictly excludes its own decision bar, and the counts in
§23 confirm a **non-zero, well-populated event space for all five**.

# 33. HISTORICAL-EVIDENCE STATUS — BINDING

The NQ history has been researched extensively by this programme (~100
hypotheses across OFH, OFN, OFSUB, RED, MAG, V4, V4.2, V5, GEN-10, BRK,
MRV, RVMR-STRAT, RVMR-AVOID, RVMR-BANDS, XMARKET). **No NQ-DIRECTION-V1
result may be called pristine untouched OOS.** All outcomes are
**HISTORICAL DISCOVERY / INTERNAL REPLICATION**. A chronological holdout
does not become untouched merely by being later in the file — the market
history itself has already been inspected.

# 34. PROSPECTIVE REQUIREMENT

No historical winner is validated. Any survivor must be frozen as
`NQ-DIR-[ID]-CANDIDATE-V1` and shadow-logged prospectively, each row
carrying: timestamp · direction (BULLISH / BEARISH / NEUTRAL) · P(up) ·
P(down) · mechanism · availableTime · spec hash · implementation hash.
**No orders, ever.**

# 35. OUT OF SCOPE

RVMR may **never** create a bullish/bearish/long/short signal here; it
enters solely as a matched-control variable so a directional result is
not merely a movement-regime artifact. No stop, target, breakeven,
trailing, sizing or management research. No ML, no indicator sweeps, no
parameter grids. **No ensemble, vote, composite or meta-model** — if
several hypotheses survive they are frozen separately and
`DIRECTION-COMBINE-V1` is proposed as a future study. OFH13 is a
**reference benchmark only**: never modified, never retrained, never
filtered by this family.

# 36. ALLOWED HYPOTHESIS VERDICTS

PROMISING DIRECTIONAL EDGE · PROMISING DIRECTIONAL CONTEXT · PROMISING
REVERSAL FEATURE · PROMISING CONTINUATION FEATURE · PROMISING
OPENING-AUCTION FEATURE · PROMISING OVERNIGHT FEATURE · PROMISING
ORDER-FLOW INCREMENT · INTERESTING BUT INCONCLUSIVE · REDUNDANT WITH NQ
MOMENTUM · NO INCREMENTAL VALUE · TIME-SPECIFIC · REGIME-SPECIFIC ·
TAIL-DEPENDENT · FAILED INTERNAL REPLICATION · VOID — SPECIFICATION
ERROR · INSUFFICIENT DATA.

---

**Execution requires a separate directive. This document is the test.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
