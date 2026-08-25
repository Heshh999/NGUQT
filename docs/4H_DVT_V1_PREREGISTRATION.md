# 4H-DVT-V1 — PRE-REGISTRATION

**4H TREND + DOUBLE 15M VECTOR WICK AT VWAP BAND + 1M EMA9 TRIGGER**

**PREREGISTRATION ONLY. No performance was calculated.** At this commit
no win rate, expectancy, return, MFE, MAE, favourable-first, P&L,
control result, year result or vector-colour result exists for this
strategy. The only computation performed was a **counts-only feasibility
and causality audit** (§33–34), which printed event counts and a
causal-availability table and **nothing about outcomes**.

Nothing frozen is modified: `OFH13_PROSPECTIVE_V1`,
`OFH14_PROSPECTIVE_V1`, RVMR-V1, every prospective ledger, the NT8
prospective host and all frozen strategy specifications are untouched.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

Specification module: `analysis/dvt/dvt_spec.py` (rules only, no outcomes).

---

# 1. 4H TREND DEFINITION

```
4H grid   anchored on the CME exchange-day open, 18:00 ET
          bucket4h(t) = (et_minutes_epoch - 1080) // 240
          -> exactly six 4H bars per day: 18, 22, 02, 06, 10, 14 ET
EMA       alpha = 2/(n+1), seeded with the SMA of the first n closes,
          recursive from COMPLETED 4H closes only
SHORT     EMA20_4H <  EMA50_4H     on the most recent COMPLETED 4H bar
LONG      EMA20_4H >  EMA50_4H     on the most recent COMPLETED 4H bar
tie       EMA20 == EMA50 -> NO SETUP (neither direction)
```

The 4H bar used is the last one **strictly before** the 15m interval in
question. A recent crossover is **not** required; alignment alone gates
the setup. Cross age is not recorded as a gate in V1.

**DECLARED AS MINE:** EMA20 and EMA50 do not exist as a pair anywhere in
source (`V4EmaFanEngine` has 5/13/50/200/800; `ScalpResearchEngine` has
9/20/200 — they never co-occur, and neither runs on 4H). The 4H grid,
the two periods and the EMA seeding above are my construction, fixed
here before any result and never tuned.

# 2–3. VWAP BAND — SOURCE-AUTHORITATIVE

Transcribed verbatim from `src/MnqTwoStrategiesShared.cs`
(L239-248, L392-399, L492-513) — the **TradingView built-in "VWAP",
Anchor = Session** with its band pair:

```
src      = hlc3 = (high + low + close) / 3          TradingView default source
vwap     = SUM(src * vol) / SUM(vol)                cumulative from the anchor
variance = SUM(vol * src * src) / SUM(vol) - vwap^2 floored at 0
stdev    = sqrt(variance)
VWAP_BAND_HIGH = vwap + 1.0 * stdev
VWAP_BAND_LOW  = vwap - 1.0 * stdev
```

| item | value |
|---|---|
| formula source | `SessionVwap` / `VwapBandHigh` / `VwapBandLow` |
| multiplier | **1.0** (`VwapBandMultiplier`, TradingView Band 1 default) |
| construction | **standard-deviation based** (not fixed-offset, not percentage) |
| session anchor | **18:00 ET**, `DayStartMinutesEt = 1080`, CME exchange-day open |
| reset | re-anchors at each new exchange day (accumulators zeroed) |
| timezone | US Eastern throughout; all stamps are close stamps |
| accumulation | only when `volume > 0`, exactly as the source does |
| **number of upper bands** | **exactly ONE — `VWAP_BAND_HIGH`** |
| **number of lower bands** | **exactly ONE — `VWAP_BAND_LOW`** |
| causal availability | the band at 1m bar *i* uses data through bar *i*, which is complete at its own close stamp — the same convention ATR20 already uses |

**The multi-band ambiguity does not arise.** `TpLevelId` contains
`VWAP, VWAP_BAND_HIGH, VWAP_BAND_LOW` and nothing else — there is no
Band 2 or Band 3 in this project. The "same-band requirement" is
therefore satisfied by construction: a SHORT double test can only ever be
`VWAP_BAND_HIGH` twice, a LONG double test `VWAP_BAND_LOW` twice. No band
selection is possible and none will be performed.

# 4. VECTOR DEFINITION — SOURCE-AUTHORITATIVE

`VectorClassifier.Classify`, `src/MnqTwoStrategiesShared.cs:116-141`:

```
avgVol10           = SUM(volume[1]..volume[10]) / 10   previous 10 COMPLETED
highestVolSpread10 = max(volume[i] * (high[i]-low[i]))  i = 1..10
volumeSpread       = volume * (high - low)
bullish            = close > open      (close == open -> BEARISH branch)

volume >= 2.0*avgVol10  OR  volumeSpread >= highestVolSpread10
        -> GREEN_VECTOR (bullish) / RED_VECTOR (bearish)   [climax has priority]
volume >= 1.5*avgVol10  -> BLUE_VECTOR / VIOLET_VECTOR
else                    -> REGULAR_BULLISH / REGULAR_BEARISH
```

**Eligible vector classes (user-specified): GREEN, BLUE, VIOLET, RED.**
`REGULAR_BULLISH` and `REGULAR_BEARISH` are **NOT** vectors and never
qualify a test. **Vector colour does not determine direction** — direction
comes from 4H alignment plus band location and rejection. No colour rule
exists in V1.

# 5. BAND TEST — ONE DEFINITION FOR COMPLETED AND DEVELOPING

This single definition is what removes the lookahead risk: the developing
case is **not a separate approximation**, it is the same function
evaluated at an earlier 1m bar.

For a 15m interval and a 1m bar *t* inside it (t = the last 1m bar of the
interval in the completed case):

```
SHORT (upper band)
  TOUCHED(t)  = EXISTS a 1m bar i from the interval start through t with
                high[i] >= VWAP_BAND_HIGH(i)
  REJECTED(t) = close[t] <  VWAP_BAND_HIGH(t)

LONG (lower band)
  TOUCHED(t)  = EXISTS a 1m bar i from the interval start through t with
                low[i]  <= VWAP_BAND_LOW(i)
  REJECTED(t) = close[t] >  VWAP_BAND_LOW(t)
```

**Exact boundary contact counts as a touch** (`>=` / `<=`), per the
directive. The band is evaluated per 1m bar with data available through
that bar, so no single "which band value" ambiguity exists.

# 6. FIRST TEST

A **COMPLETED** 15m candle that simultaneously satisfies:

1. 4H trend condition valid for its direction (§1),
2. `TOUCHED` and `REJECTED` at the direction's band (§5, t = last 1m bar),
3. classified as an **eligible vector** (§4).

Recorded: `firstTestBucket`, band side, direction, vector class, interval
extreme, close, band value at close, session key.

# 7. SECOND TEST AND MAXIMUM SPACING

The second test must occur **after** the first, test the **same band**
(automatic — only one band per side exists), and independently satisfy
the vector requirement. Vector colour need not match.

```
MAX_SPACING_15M = 16 completed 15m bars between test #1 and test #2
                  AND both tests in the SAME VWAP session
```

**Mechanistic justification, fixed before results:** 16 × 15m = **exactly
one 4H bar**, so the 4H directional context that gates the setup cannot
go stale inside the setup's own lifespan. The same-session constraint is
not a choice but a necessity — VWAP re-anchors at 18:00 ET, so a band in
a different session is a **different object** and could not be "the same
band". **ONE value. No 2/4/6/8/12-bar sweep, now or ever.**

# 8. BETWEEN-TEST INVALIDATION

```
SHORT dies if any COMPLETED 15m candle between the tests CLOSES ABOVE
      VWAP_BAND_HIGH (evaluated at that candle's close)  = acceptance
LONG  dies if any COMPLETED 15m candle between the tests CLOSES BELOW
      VWAP_BAND_LOW                                       = acceptance
Setup also dies at the VWAP session boundary (18:00 ET re-anchor) and
      if the 4H trend condition flips.
```

**Violation of the first test's wick extreme does NOT invalidate.**
Declared explicitly: the setup is about *band rejection*, not extreme
protection, and adding an extreme-protection rule would be a second
mechanism smuggled into V1. No rescue rule exists.

# 9. DEVELOPING SECOND VECTOR — THE CAUSAL CORE

At each completed 1m bar *t* inside the second 15m interval, rebuild the
developing candle from **completed 1m bars belonging to that interval
through t only**:

```
devOpen   = open  of the interval's FIRST 1m bar
devHigh   = max(high[i])   i = interval start .. t
devLow    = min(low[i])    i = interval start .. t
devClose  = close[t]
devVolume = SUM(volume[i]) i = interval start .. t
```

Vector qualification uses `avgVol10` and `highestVolSpread10` computed
from the **previous 10 COMPLETED 15m candles** — entirely in the past,
never touching the interval in progress.

The entry may be evaluated only when **all three** are already true at t:

```
A. TOUCHED(t)                      band contact has already happened
B. REJECTED(t)                     close[t] already back inside the boundary
C. is_vector(classify(devOpen, devHigh, devLow, devClose, devVolume,
                      avgVol10, highestVolSpread10))
```

**Forbidden and structurally impossible in this design:** using the
completed second candle's final volume, high or low to justify an earlier
entry. If the interval only reaches the vector threshold at 10:27, no
entry at 10:21 can exist, because `devVolume` at 10:21 does not contain
the 10:22–10:27 volume.

# 10. 1M EMA9 TRIGGER

```
EMA9 = Ema(9) over COMPLETED 1m closes, alpha = 2/10, SMA-seeded
SHORT: FIRST completed 1m candle with close < EMA9(t)
LONG:  FIRST completed 1m candle with close > EMA9(t)
```

**No crossover is required.** If price is already below EMA9 when the
developing short vector qualifies, the first qualifying completed 1m
close below EMA9 triggers. Entry timestamp = that 1m candle's close. No
intrabar anticipation.

# 11. ONE ENTRY PER DOUBLE TEST

Only the **first** valid 1m trigger during the second test creates an
entry. No repeated entries from the same parent, no pyramiding, no
re-entry. Once the second interval completes without a trigger, the
parent is closed unfilled.

# 12–13. ENTRY WINDOW AND SESSION HANDLING

```
ENTRY WINDOW: the entry 1m bar must satisfy 570 <= minuteOfDay <= 900
              (09:30-15:00 ET)
```

This is the **frozen RVMR / V4 eligible window** used by every completed
study in this programme, and it guarantees a full 60-minute measurement
horizon inside RTH. The Fake Breakout spec's 11:30 ET cutoff belongs to a
different strategy and is **not** used here. No start/end optimization,
now or ever.

**Premarket:** test #1 **may** form premarket — it is the same VWAP
session and the band is fully defined there. Only the **entry bar** is
restricted to the window above. This is logically consistent with a
setup built on 4H/15m context and is frozen now.

# 14. STRUCTURAL STOP

```
SHORT stop = max(high[i]) over the second interval's 1m bars from its
             start through the entry bar t          (causally available)
LONG  stop = min(low[i])  over the same range
```

Recorded per trade in **points, ATR units and R**. **No stop grid, no
alternative stop, no breakeven, no trailing.**

# 15–17. MEASUREMENT

**Raw geometry first, before any management:** forward returns at
**5 / 10 / 15 / 30 / 60 minutes**, MFE, MAE, MFE/MAE, favourable-first.

**Favourable-first ladder** (direction-signed, ATR-normalized):

```
+0.25 ATR before -0.25 ATR
+0.5  ATR before -0.5  ATR
+1.0  ATR before -1.0  ATR
+1.5  ATR before -1.0  ATR
+2.0  ATR before -1.0  ATR
```

**AMBIGUOUS remains AMBIGUOUS** — when both thresholds are crossed inside
the same 1m bar the outcome is AMBIGUOUS and is **never** resolved by
guessing or by inferring intrabar sequence.

**Economic reference frame (ONE, frozen):** structural stop (§14), **no
target**, **60-minute maximum hold**, **0.87 pt round-turn cost** —
repository-consistent with every frozen study. **No stop/target
optimization in V1.**

# 18. CONTROLS

**CONTROL A — do vectors add information?**
4H trend + double 15m band wick + 1m EMA9 trigger, with **neither test
required to be a vector** (REGULAR classes allowed). Identical in every
other respect.

**CONTROL B — does the second test add information?**
4H trend + **ONE** qualifying 15m vector wick + 1m EMA9 trigger. The
trigger is evaluated during the *first* qualifying test's own developing
interval, so the architecture is identical and only the test count
differs.

**CONTROL C — does the EMA9 trigger improve timing?**
4H trend + double vector band test, entering at the **close of the first
1m bar at which A+B+C (§9) are all satisfied**, with **no EMA9
condition**. This is the natural causal reference point and is frozen
here so it cannot be chosen later.

**CONTROL D — 4H alignment diagnostic** (diagnostic only, never a
strategy): the identical double-vector band event measured **without**
using 4H alignment to select direction — direction taken from the band
side alone (upper → short, lower → long). Purpose: determine whether 4H
alignment adds directional information or merely reduces frequency.

Every control is scored on the **identical measurement frame** so no
comparison can be a frame artifact.

# 19. MATCHING VARIABLES

Signal and controls are compared within cells of:

```
direction · year · time-of-day bucket · ATR quintile · RVMR RANGE state ·
sign of the 5-minute normalized return · 4H EMA separation tercile
(|EMA20-EMA50| / ATR) · distance from band at entry tercile (ATR units) ·
first-to-second-test elapsed 15m bars tercile
```

Cells lacking both sides are dropped **symmetrically**. This is the gate
that prevents vector events from simply selecting higher-volatility
minutes and calling that an edge.

# 20–21. KEY QUESTIONS

1. Does the full setup have useful directional geometry?
2. Do TWO vector tests beat ONE (vs Control B)?
3. Do VECTOR double tests beat ordinary double wicks (vs Control A)?
4. Does the 1m EMA9 trigger improve entry geometry (vs Control C)?
5. Does 4H alignment matter (vs Control D)?
6. Are both sides useful?
7–9. Year, regime and tail stability?
10. Is the developing-second-vector implementation causal?

# 22. LONG / SHORT

Always reported separately, never pooled.
SHORT = 4H EMA20 < EMA50 · upper-band double vector · 1m close below EMA9.
LONG = 4H EMA20 > EMA50 · lower-band double vector · 1m close above EMA9.
**The weak side is not deleted in V1** — that would require a new frozen
candidate.

# 23. VECTOR COLOUR — SECONDARY DIAGNOSTIC ONLY

Primary uses **any** eligible vector. Colour composition may be reported
**after** the primary result as a frozen diagnostic. **No colour rule may
be created inside V1** — not red-only, green-only, violet-only,
same-colour pair or opposite-colour pair. A surprising colour interaction
is recorded for future research and nothing more.

# 24. FIRST/SECOND EXTREME RELATIONSHIP — DIAGNOSTIC ONLY

Recorded: whether the second test sweeps beyond, equals, or fails short
of the first test's extreme. **This never filters V1.** No post-result
sweep/reclaim rescue is permitted — that mechanism was already tested and
failed in NQ-DIRECTION-V1 (DIR-H1).

# 25. SAMPLE GATES (chosen from counts only, §33)

```
MIN_EVENTS     200 scored entries
MIN_DAYS       100 distinct trading days
MIN_YEARS      5 years holding >= 15 entries each
MIN_PER_SIDE   50 long AND 50 short
```

# 26. YEAR STABILITY

Reported per year 2019–2026: N, mean, median, MFE/MAE, favourable-first,
economic reference. **Gate:** the signal-minus-control advantage is
positive in **≥ 70%** of years holding ≥ 15 entries, **and** the pooled
advantage with the single best year removed remains > 0. No single-regime
dependence.

# 27. TIME-OF-DAY DESTRUCTION

Frozen broad buckets: `OPEN 570–629 · MIDMORN 630–719 · MIDDAY 720–809 ·
AFTERNOON 810–900`. No bucket may be removed and no minute optimized. If
value is confined to one bucket → **TIME-SPECIFIC**, reported, not
silently narrowed.

# 28. RVMR ROLE

**Diagnostic context and matched-control variable only.** RVMR may never
say take-the-trade or avoid-the-trade — those questions are closed
(RVMR-STRAT-V1, RVMR-AVOID-V1). No RVMR × setup optimization.

# 29. TAIL DESTRUCTION

Largest winner, largest loser, top-1% and top-5% contribution, mean
excluding top 1%, mean excluding top 5%. Directional and
favourable-first behaviour recomputed after tail removal. If the
advantage disappears → **TAIL-DEPENDENT**, not promoted.

# 30. MULTIPLICITY

This is **ONE primary strategy hypothesis plus four preregistered
controls (A, B, C, D) and one secondary reference (§32)** — **M = 2**
promotable tests (the primary developing-entry setup and the
completed-15m secondary reference). Controls are comparisons, not
independent hypotheses, and are never promoted on their own.

Inference: **day-clustered bootstrap, 20,000 iterations, seed 20260825**,
95% CIs, plus sign-flip-by-day where a paired comparison applies. No
i.i.d. trade-level p-value is used for any promotion decision. Vector
colours, time windows, bands, stops and years are **not** turned into
separate families.

# 31. PROMOTION GATE — all fifteen required

| # | condition |
|---|---|
| 1 | sample gates (§25) all met |
| 2 | useful directional geometry (positive median and positive economic reference) |
| 3 | MFE/MAE exceeds matched control |
| 4 | favourable-first exceeds matched control |
| 5 | beats **Control A** (ordinary double wick) with day-clustered CI excluding 0 |
| 6 | beats **Control B** (single vector) — the second test adds information |
| 7 | **Control C** shows the EMA9 trigger improves or does not harm geometry |
| 8 | both sides reported; neither catastrophic without explanation |
| 9 | year stability (§26) |
| 10 | time-of-day stability or an explicit TIME-SPECIFIC label |
| 11 | tail robustness (§29) |
| 12 | day-clustered statistical support after multiplicity |
| 13 | **no lookahead** — §34 audit fully YES |
| 14 | no data artifact (contiguity, session and gap rules enforced) |
| 15 | no control-construction artifact (symmetric cell dropping, matched N reported) |

**A positive P&L number alone is insufficient.** So is a significant
p-value with trivial geometry.

# 32. COMPLETED-15M SECONDARY REFERENCE

Frozen now and counted in multiplicity: the identical setup entered on
the first qualifying 1m EMA9 close **after the second 15m candle has
completed**. Purpose: measure the cost or benefit of waiting. It is a
**SECONDARY REFERENCE and may never replace the primary developing
version**, whatever the results.

# 33. DATA SUFFICIENCY — PASS

Genuine 1m OHLCV with volume: **2,503,622 bars, 2019-07-04 → 2026-08-17,
zero non-positive-volume bars.** 15m and 4H candles are exactly
reconstructable on the 18:00-ET grid; the developing 15m candle is
exactly reconstructable from completed 1m bars. **No approximation is
required anywhere.**

**Counts-only feasibility (no outcomes inspected):**

| | count |
|---|---|
| completed 15m intervals | 169,639 |
| 15m candles that are eligible vectors | 36,043 (GREEN 11,629 · BLUE 5,699 · VIOLET 5,672 · RED 13,043) |
| completed 4H candles with EMA20/50 ready | 10,907 of 10,956 |
| first-test candidates SHORT / LONG | 1,921 / 3,374 |
| **double-test parents SHORT** | **250** over 169 days, 8 years |
| **double-test parents LONG** | **515** over 334 days, 8 years |
| **TOTAL parents** | **765 over 503 days** |

Every year 2019–2026 is populated on both sides. Parents exceed the
entry count (the 1m EMA9 trigger reduces further), which is why the
sample gates in §25 sit below these figures.

**Observed long/short asymmetry (515 vs 250) is a structural property of
4H EMA alignment across a mostly-uptrending 2019–2026, not a defect** —
it is recorded here, before results, so it cannot later be mistaken for
a finding.

# 34. CAUSAL-AVAILABILITY AUDIT — ALL YES

| field | available time | entry time | causal? |
|---|---|---|---|
| 4H EMA20 / EMA50 | close of the **prior completed** 4H bar | entry 1m close | **YES** |
| first 15m vector | close of that **completed** 15m bar | entry 1m close | **YES** |
| VWAP band (per 1m) | close of that 1m bar (bar is complete) | entry 1m close | **YES** |
| vector lookback (avgVol10, highestVolSpread10) | previous **10 completed** 15m bars | entry 1m close | **YES** |
| developing 15m OHLCV | completed 1m bars through *t* only | entry 1m close *t* | **YES** |
| 1m EMA9 | completed 1m closes through *t* | entry 1m close *t* | **YES** |
| structural stop | 2nd-interval 1m bars through *t* | entry 1m close *t* | **YES** |

**No reference window includes its own decision bar in an impossible way;
no outcome participates in signal construction; every entry timestamp is
≥ every required signal-availability timestamp.**

# 35. RESULT BLINDNESS — CONFIRMED

No win rate, expectancy, MFE, MAE, favourable-first, P&L, control result,
year result or vector-colour result was calculated before this commit.
Counts-only feasibility was performed, as the directive permits.

# 36. NO OPTIMIZATION AFTER RESULTS — BINDING

Forbidden: different EMA periods, different 4H trend EMAs, different band
multipliers, one/three wicks, different max spacing, different vector
thresholds, different 1m EMA periods, stop grids, targets, different
entry windows. **If V1 fails, V1 fails.** Any alteration becomes
**4H-DVT-V2** with its own pre-registration.

---

**Execution requires a separate directive. This document is the test.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
