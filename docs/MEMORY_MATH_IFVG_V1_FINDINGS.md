# MEMORY-MATH-IFVG-V1 — FROZEN ONE-SHOT EXECUTION — FINDINGS

**HEADLINE: MEMORY-MATH-IFVG-V1 FOUND NO MONETIZABLE MEMORY
AMPLIFICATION.** Zero of 12 mathematical hypotheses passed all eight
MA gates. Zero of 4 strategy hypotheses passed all twelve SG gates.
0 of a permitted 2 mathematical anomalies and 0 of a permitted 1
strategy advanced. MEMORY-PRED remains **REAL PREDICTIVE STRUCTURE BUT
SUB-COST STANDALONE**, and the search is not expanded.

Execution UTC 2026-08-26T20:10Z · runtime 91 s · seed 20260826.

**EPISTEMIC STATUS.** 2019→2026 is fully EXPOSED for MEMORY-derived
research. Everything below is EXPLORATORY / DEVELOPMENT-DERIVED. No
partition is OOS, prospective, or independently confirmed. Nothing here
is a validated edge. SUBMITS NO ORDERS. NOTHING FROZEN WAS MODIFIED.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1. Freeze verification (Phase 0)

| # | Item | Result |
|---|---|---|
| 1 | prereg sha256 | `313127d24a8178b7064e9d90af38d7ecaac18d9110f8ba46f0b7827fbc2dac9b` **MATCH** |
| 2 | prereg commit | `7a9136feb54f201295d83e37e0b0c929310de827` |
| 3 | RVMR spec | T1 1.270 / T2 2.335 / W 1440 — OK |
| 4 | MEMORY lineage | m[t]=sign(r[t])·r[t+1]; anchor +0.30013 bp; +3.2469 pp |
| 5 | return convention | r[t]=log(c[t]/c[t−1]); r[t]==0 excluded; r[t+1]==0 kept for the mean, dropped from the sign endpoint |
| 6 | close-stamp | STAMP_SHIFT = 0, close-stamped ET |
| 7–10 | Lane A / Lane B / IFVG / S1–S4 | reproduced verbatim from the frozen text |
| 11 | cost | 0.87 NQ points round turn |
| 12–13 | MA1–MA8, SG1–SG12 | frozen, unmodified |
| 14–17 | M_math 12, M_strat 4, M_total 16, ceiling ≤2 math + ≤1 strategy | as frozen |
| 18 | prospective firewall | enforced |

## 2. Prospective firewall

Rows at/after 2026-08-26 00:00 ET are excluded **before any feature is
built**. **Excluded rows: 0** (first/last excluded: none). The frozen
grid ends 2026-08-17 15:16, so no prospective MEMORY data existed to
consume. **MEMORY-PRED's prospective lane was not touched, read, or
used.**

## 3. Causal audit (Phase 1)

2,503,622 bars, 2019-07-04 18:25 → 2026-08-17 15:16, 2,218 exchange
days, **0 duplicate close stamps**. 3,745,252 minutes spanned vs
2,503,622 present ⇒ 1,241,630 missing minutes (weekends, holidays,
session gaps, halts) **skipped, never bridged**; every window crossing
a gap is UNAVAILABLE by the `em` contiguity clock. ATR warmup: first 19
bars. RVMR unavailable: first 1,440 bars. MEMORY unavailable: r[t]==0
or broken contiguity ⇒ event dropped.

Every decision input was verified available at or before its decision
close: r[t], sign(r[t]), rr[t] (denominator strictly t−1440..t−1),
RB[t], age(t), RB[t−1], vel(t), runlen(t), eff(t), flips(t), va(t),
atr20(t); and for Lane B: FVG formation at close of bar k, zone
boundaries, touch, inversion close, IFVG availability, retest re-entry,
retest-reject, generic breakout reference window, generic failure
close. **No future-bar qualification enters any decision timestamp.**

## 4. Lineage exclusions (Phase 2)

The 15-object table was reproduced. No executed cell re-tests AC-FLIP,
LEVERAGE-V, SHOCK-CONT, MONDAY, HALF-SESSION-LOW, the failed 5m
momentum object, the failed 30m trend object, ORDINAL-V-TURN, or
OFH13 × MEMORY. OFH13/OFH14 are not used as a component of any object
here. **LINEAGE CLEAN.**

## 5. Data counts

Lane A base population: **2,384,666 events on 2,215 days.**
Lane B: 514,338 raw 3-bar FVGs; **302,398 size-qualified** (≥0.25·ATR20;
bullish 154,817 / bearish 147,581); UNTOUCHED 16,951; UNRESOLVED 6,266;
**TOUCHED 279,181**; RESOLVED 279,146; **HOLD 198,175 / INVERT 80,971**;
EXPIRED 35. Retest-reject: 44,498 before cooldown → **34,952** after the
frozen 30-bar per-direction cooldown. Generic-failure controls: 59,395.
The "≥1 tick" secondary population equals the raw count (514,338),
because an FVG gap is at least one tick by construction.

## 6. Multiplicity ledger

M_math = 12 (A1–A8, B2–B5), BH binding. M_strat = 4 (S1–S4), BH
binding. M_total = 16. Programme cumulative ledger 8 + 16 = **24**,
reported non-binding, never shrunk. **Every cell is reported, including
every failure.** No cell was dropped from the family.

---

## 7. THE CENTRAL MEASUREMENT: the deployable memory effect is ~4× smaller than the anchor

This governs everything below and is reported first because it is the
single most consequential number in the study.

The preregistration defines the Lane-A state as **RB[t]** — the state
knowable at a decision. On that construction:

| state | n | memoryReturn | P(cont) |
|---|---|---|---|
| LOW | 1,787,338 | −0.00393 bp | 0.4862 |
| MEDIUM | 448,154 | +0.01569 bp | 0.4929 |
| HIGH | 149,174 | +0.06754 bp | 0.4966 |
| **all** | **2,384,666** | **+0.00423 bp** | **0.4882** |

**HIGH − LOW = +0.0715 bp and +1.04 pp.** The frozen MEMORY-PRED anchor
is +0.30013 bp and +3.2469 pp — but that came from the
**adjacency-restricted** object (RB[t] == RB[t+1]), which requires the
*next* bar's range and is therefore **not causally available at a
decision**. The deployable effect is roughly **one quarter** of the
anchor.

MA3's materiality floor (+0.60 bp = 2× anchor) was left exactly as
frozen. The consequence is stark and worth stating plainly: **no Lane-A
cell in this study came within an order of magnitude of the floor**, and
the largest genuine conditional effect found (A4, −0.0587 bp) is about
**1/10th of it**. The floor was set against a construction that cannot
be traded. That is itself a finding about the preregistration, not a
reason to move the floor — and it is not moved.

Continuation probability never exceeds 0.5145 in any adequately-sampled
Lane-A cell, against 0.5 for a coin.

---

## 8. LANE A RESULTS (A1–A8)

### A1 — RVMR STATE AGE → **INSUFFICIENT (sample floors unmet)** · 2/8

| HIGH age | n | days | P(cont) | mem bp | NQ pts | × anchor |
|---|---|---|---|---|---|---|
| FRESH 1–3 | 118,459 | 2,139 | 0.4943 | +0.04409 | +0.0570 | 0.15 |
| YOUNG 4–15 | 26,128 | 1,721 | 0.5037 | +0.15330 | +0.2650 | 0.51 |
| ESTABLISHED 16–60 | 4,392 | 338 | 0.5145 | +0.14780 | +0.1609 | 0.49 |
| MATURE ≥61 | **195** | **12** | 0.5722 | +1.01263 | +2.1949 | 3.37 |

Primary FRESH−MATURE = −0.96853 bp, CI [−2.65825, +1.24997], p 0.45320.
**The MATURE arm holds 195 events on 12 days against frozen floors of
5,000 events / 200 days.** HIGH is a rare, short-lived state, so an aged
HIGH run barely exists. A1 is INSUFFICIENT on floors and no other gate
can rescue it.

Note the trap the floor caught: MATURE HIGH shows +1.01 bp — 3.4× the
anchor and the largest number anywhere in Lane A. On 195 events across
12 days, with year signs +1.26/+2.38/−0.78/−3.97/+0.30, it is noise.
Had the floor not been preregistered, this cell is exactly what an
undisciplined search would have promoted.

### A2 — STATE TRANSITIONS → **FAILED — WRONG DIRECTION** (MA3, MA4, MA7) · 5/8

Full 3×3 transition table (memoryReturn bp / n):

| from ↓ to → | LOW | MEDIUM | HIGH |
|---|---|---|---|
| LOW | −0.0043 (1,578,034) | +0.0183 (191,848) | +0.0674 (22,745) |
| MEDIUM | +0.0034 (193,153) | +0.0204 (192,887) | +0.0362 (57,263) |
| HIGH | −0.0513 (16,150) | −0.0066 (63,419) | **+0.0936 (69,166)** |

HIGH-ARRIVAL +0.04504 (n 80,008) vs HIGH-PERSISTENCE **+0.09357**
(n 69,166). Primary = **−0.04853 bp**, CI [−0.11876, +0.02046],
p 0.16980, perm 0.31145.

**The frozen hypothesis is refuted in direction.** Memory is *stronger*
in established HIGH than on arrival into HIGH — roughly twice as
strong — the opposite of the "activity expansion" mechanism. The effect
is not significant, so the correct reading is: arrival carries no
directional advantage, and if anything persistence carries more. This is
consistent with the HARU finding that state arrival is about activity
propensity, not direction.

### A3 — SCORE VELOCITY → **FAILED** (MA3, MA4, MA5, MA6, MA8) · 3/8

HIGH RISING +0.07245 (n 112,346) vs FALLING +0.03520 (n 30,281).
Primary **+0.03726 bp**, CI [−0.05523, +0.12953], p 0.42540, perm
0.45950. Correct sign, but 1/16th of the floor, insignificant, and
unstable (3/8 years, 1/3 ToD). Velocity adds nothing beyond the state.

### A4 — RUN LENGTH → **REAL BUT SUB-MATERIAL (correct sign, below the 2× floor)** · 7/8 — *the strongest Lane-A result*

| LOW runlen | n | P(cont) | mem bp | HIGH runlen | n | P(cont) | mem bp |
|---|---|---|---|---|---|---|---|
| 1 | 971,861 | 0.4942 | +0.01703 | 1 | 72,462 | 0.5067 | +0.12760 |
| 2 | 451,132 | 0.4801 | −0.01857 | 2 | 37,543 | 0.4958 | +0.05719 |
| ≥3 | 364,345 | 0.4726 | −0.04169 | ≥3 | 39,169 | 0.4787 | −0.03366 |

Primary (LOW, run≥3 minus run==1) = **−0.05871 bp**, CI [−0.06802,
−0.04920], boot p **0.00005**, rotation perm p **0.00005**,
common-weight standardised −0.05863 (27 cells), trims −0.06172 /
−0.06398, **years 8/8**, **ToD 3/3**.

This is a genuinely real, exceptionally stable, control-surviving
mathematical relationship: **aged runs reverse more**, monotonically, in
both LOW and HIGH, in every year and every session bucket. It fails
**only MA3** — magnitude. At −0.0587 bp it is 1/10th of the frozen
materiality floor and about 0.13 NQ points per event.

It is also the one result that independently corroborates the
ORDINAL-V-TURN knowledge object from a completely different direction,
and it explains it: the V-turn effect is aged-run reversal.

### A5 — PATH EFFICIENCY → **FAILED — WRONG DIRECTION** (MA3, MA4) · 6/8

Outcome-blind efficiency terciles (printed before any join): 0.176471 /
0.389474.

| HIGH efficiency | n | P(cont) | mem bp |
|---|---|---|---|
| NOISY | 41,735 | 0.5039 | +0.12217 |
| MID | 45,317 | 0.5038 | +0.08638 |
| EFFICIENT | 60,697 | 0.4866 | +0.01874 |

Primary (standardised within |r| terciles) = **−0.10336 bp**, CI
[−0.18262, −0.02359], p 0.01030, perm **0.22025**.

**Direction refuted.** Memory is stronger after *noisy* two-sided
movement, not after efficient directional movement — monotone across
terciles, 7/8 years, 3/3 ToD, and it survives the common-weight
standardisation (−0.09428). The bootstrap CI excludes zero but the
rotation permutation does not support it (0.22), so MA4 fails. The
honest reading: an inverse relationship that is probably real and
certainly not the one preregistered.

### A6 — FLIP COUNT → **REDUNDANT WITH RUN LENGTH** · 6/8

| HIGH flips | n | P(cont) | mem bp |
|---|---|---|---|
| ORDERLY ≤2 | 31,572 | 0.4849 | −0.01353 |
| MIXED 3–4 | 72,970 | 0.4999 | +0.09148 |
| CHOPPY ≥5 | 27,542 | 0.5065 | +0.12421 |

Primary ORDERLY−CHOPPY = −0.13774 bp, CI [−0.25524, −0.02088],
p 0.02160, perm **0.89590**. Direction refuted (orderly sequences have
*less* memory), and the **frozen incrementality duty** settles it:
standardised within run-length categories the effect collapses to
**+0.03870 bp** — sign flips, magnitude 28% — so **A6 is REDUNDANT WITH
RUN LENGTH** regardless of raw significance, exactly as the
preregistration required. The flip-count "effect" was run length wearing
a different name; the frozen duty caught it.

### A7 — VOLATILITY TRAJECTORY → **FAILED** (MA3, MA4, MA6, MA8) · 4/8

HIGH EXPANDING +0.07471 (65,944) / STABLE +0.06228 (62,245) /
CONTRACTING +0.06804 (19,229). Primary **+0.01242 bp**, CI [−0.06023,
+0.08707], p 0.74480, perm 0.75265. **Nothing.** Memory does not depend
on whether volatility is expanding, stable, or contracting; LOW shows
the same flatness (−0.008 / −0.004 / −0.001). The failed
shock-continuation object was not resurrected — this tests the ATR
trajectory, and the trajectory is inert.

### A8 — PERSISTENCE DECAY → **FAILED — WRONG DIRECTION** (MA3, MA4) · 6/8

| state | h=1 cum | h=2 cum | h=3 cum | h=5 cum | increments (1,2,3,5) |
|---|---|---|---|---|---|
| LOW | −0.00393 | −0.02436 | −0.02781 | −0.02657 | −0.0039 / −0.0205 / −0.0035 / −0.0009 |
| MEDIUM | +0.01569 | −0.03656 | −0.04526 | −0.04612 | +0.0157 / −0.0528 / −0.0089 / −0.0038 |
| HIGH | **+0.06754** | +0.02216 | +0.00256 | +0.01031 | **+0.0675** / −0.0442 / −0.0171 / −0.0228 |

Primary (HIGH, m3 − m1) = **−0.06218 bp**, CI [−0.10798, −0.01777],
p 0.00670, perm 0.28140.

**This is the decay answer, and it is decisive.** All of HIGH's memory
is delivered in minute 1 (+0.0675 bp); minute 2 gives it back
(−0.0442); by minute 3 the cumulative effect is +0.0026 — essentially
zero. Every increment after the first is **negative in every state**.
The predicted "incremental information beyond minute 1" is not merely
absent, it is negative: the market gives the memory back.

This closes the loop with the two prior frozen results — 1m memory real,
5m momentum significantly anti-persistent — and supplies the missing
middle: the reversal happens at minute 2.

---

## 9. LANE B RESULTS (B1–B6)

### B1 — the frozen mathematical IFVG

Public concept audited and cited in the preregistration; **our
implementation is a repository-consistent mathematical translation and
is NOT claimed to be any official ICT strategy.** No educational
profitability claim was treated as evidence anywhere.

302,398 size-qualified FVGs → 279,146 resolved → **80,971 inversions,
inversion rate 29.01%**. Every frozen Lane-B floor cleared with large
margin.

### B2 — WHICH FVGS INVERT? → **FAILED — SIGNIFICANT BUT OPPOSITE TO THE FROZEN PREDICTION** · 7/8

| MEMORY class at formation | n | days | inversion % |
|---|---|---|---|
| ALIGNED | 70,614 | 2,214 | **30.654** |
| OPPOSED | 145,293 | 2,215 | **28.395** |
| NEUTRAL | 63,239 | 2,212 | 28.573 |

Primary (OPPOSED − ALIGNED) = **−2.25894 pp**, CI [−2.66136, −1.85392],
boot p **0.00005**, rotation perm p **0.00005**, common-weight −2.35324
(27 cells), trims −2.25894 / −2.25894, **years 8/8**, **ToD 3/3**.

**The single most statistically robust result in the entire study — and
it points the wrong way.** The frozen hypothesis was that memory running
*against* the imbalance predicts failure. The data say the opposite: a
gap formed while memory *agrees* with its direction inverts **more**
often (30.65% vs 28.40%). MA3 fails on direction (and the magnitude,
2.26 pp, is below the 6.49 pp transported floor), so the verdict is
FAILED — not "sub-material". Reporting it as merely small would have
been a misdescription, and an earlier verdict-string defect that did
exactly that was corrected before this document (§12).

Descriptive one-way tables (all monotone, all pointing the same way):
inversion falls with RVMR state (LOW 29.54% → HIGH 26.85%), with run
length (1: 31.63% → 3+: 27.33%), with efficiency (30.33% → 27.45%) and
with score velocity (30.06% → 27.57%). The common thread is that
**quiet, fresh, choppy conditions produce fragile gaps** — a volatility
and structure story, not a memory story.

### B3 — POST-INVERSION DRIFT → **FAILED** (MA3, MA4, MA8) · 5/8

79,951 events / 2,215 days. +1m −0.0133 bp / +3m +0.0194 / **+5m
+0.0556** / +15m +0.0577. MFE 14.057, MAE 13.781, MFE/MAE 1.020,
FF@1ATR/60m **49.86%**. Primary +0.05556 bp, CI [−0.00175, +0.11263],
p 0.05820, perm 0.05370. Tail-fragile: the 5% trim collapses it to
+0.00547 (MA8 fails). Marginal at best, and 1/10th of the floor.

### B4 — FIRST RETEST-REJECT → **FAILED** (MA3, MA4) · 6/8

34,952 events after the frozen cooldown. **+5m +0.0113 bp**, CI
[−0.06384, +0.08496], p 0.76700, perm 0.77785. FF 49.87%, MFE/MAE
**0.995**. +15m turns negative (−0.1059 bp). **The retest — the part of
the public IFVG concept traders actually act on — carries no measurable
edge whatsoever.**

### B5 — MEMORY × IFVG → **FAILED** (MA3, MA4, MA5) · 5/8

| class at retest-reject | n | days | +5m bp |
|---|---|---|---|
| ALIGNED | 6,526 | 1,953 | +0.0944 |
| OPPOSED | 20,698 | 2,205 | −0.0024 |
| NEUTRAL | 7,421 | 1,923 | −0.0238 |

**Frozen floors PASS** (≥60 events / ≥40 days per arm, by a wide
margin), so this is a real test, not an insufficiency. Primary
ALIGNED−OPPOSED = **+0.09684 bp**, CI [−0.13563, +0.33476], p 0.41620,
perm 0.35120, years **4/8**. Correct sign, right order of magnitude to
be interesting — and **completely unsupported**. The CI is nearly four
times as wide as the estimate.

### B6 — GENERIC FAILURE CONTROL (decisive)

59,395 generic failed-structure events (30-minute close breakout, then a
close back through the breakout bar, 30-bar cooldown), matched
common-weight on ATR × ToD × |15m preceding return| terciles:

| comparison | IFVG − generic | CI | p | reading |
|---|---|---|---|---|
| B3 post-inversion | **+0.1045 bp** | [+0.0221, +0.1871] | 0.01250 | exceeds generic, CI excludes 0 |
| B4 retest-reject | +0.0576 bp | [−0.0490, +0.1615] | 0.29250 | **not distinguishable from generic** |

*(The engine's one-line label prints "IFVG EXCEEDS GENERIC" on the point
estimate alone; for B4 the difference is not statistically supported and
is reported as such here. The numbers are the record.)*

So the IFVG object is **not purely a visual name for generic failure**:
the inversion *event itself* carries a small excess over a matched
generic polarity flip. But that excess (+0.10 bp ≈ 0.2 NQ points) is
below every promotion floor, and the **retest** — the tradeable part —
is indistinguishable from generic structure failure.

---

## 10. MA1–MA8 GATE TABLE (M_math = 12, BH binding)

| id | primary | unit | raw p | BH q | perm p | MA1 | MA2 | MA3 | MA4 | MA5 | MA6 | MA7 | MA8 | passed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A1 | −0.9685 | bp | 0.45320 | 0.54384 | 0.19430 | P | **F** | **F** | **F** | **F** | **F** | **F** | P | 2/8 |
| A2 | −0.0485 | bp | 0.16980 | 0.29109 | 0.31145 | P | P | **F** | **F** | P | P | **F** | P | 5/8 |
| A3 | +0.0373 | bp | 0.42540 | 0.54384 | 0.45950 | P | P | **F** | **F** | **F** | **F** | P | **F** | 3/8 |
| A4 | −0.0587 | bp | 0.00005 | 0.00030 | 0.00005 | P | P | **F** | P | P | P | P | P | **7/8** |
| A5 | −0.1034 | bp | 0.01030 | 0.03090 | 0.22025 | P | P | **F** | **F** | P | P | P | P | 6/8 |
| A6 | −0.1377 | bp | 0.02160 | 0.05184 | 0.89590 | P | P | **F** | **F** | P | P | P | P | 6/8 |
| A7 | +0.0124 | bp | 0.74480 | 0.76700 | 0.75265 | P | P | **F** | **F** | P | **F** | P | **F** | 4/8 |
| A8 | −0.0622 | bp | 0.00670 | 0.02680 | 0.28140 | P | P | **F** | **F** | P | P | P | P | 6/8 |
| B2 | −2.2589 | pp | 0.00005 | 0.00030 | 0.00005 | P | P | **F** | P | P | P | P | P | **7/8** |
| B3 | +0.0556 | bp | 0.05820 | 0.11640 | 0.05370 | P | P | **F** | **F** | P | P | P | **F** | 5/8 |
| B4 | +0.0113 | bp | 0.76700 | 0.76700 | 0.77785 | P | P | **F** | **F** | P | P | P | P | 6/8 |
| B5 | +0.0968 | bp | 0.41620 | 0.54384 | 0.35120 | P | P | **F** | **F** | **F** | P | P | P | 5/8 |

**MATHEMATICAL SURVIVORS (all 8 gates): NONE.**

**MA3 failed in all twelve cells** — six on direction, six on magnitude
alone. Not one preregistered condition reached 2× the anchor.

MA7 for B3/B4/A8 is single-arm drift with no two-arm contrast to
standardise; it is scored on the B6/A8 control comparisons instead, as
noted in the raw output.

## 11. Mathematical candidate ranking

Ranked on incrementality, effect size, stability, tail robustness,
simplicity and economic relevance — **not p-value**:

1. **A4 run-length reversal** — 7/8; the only object real in the
   predicted direction, 8/8 years, 3/3 ToD, control-surviving,
   tail-stable. Fails materiality by ~10×.
2. **B2 memory-at-formation → inversion** — 7/8; the most robust
   statistic in the study, but **opposite in direction** to the frozen
   hypothesis and below the transported floor.
3. **A8 decay profile** — 6/8; not promotable, but the most
   *explanatory* result (see §16).

**Advanced: 0 of a permitted 2.** None cleared the frozen bar. The
ceiling was not reached, and third-best candidates were not advanced.

---

## 12. STRATEGY RESULTS (S1–S4) — raw geometry only

**No stop, target, trailing stop, breakeven, partial exit, or position
sizing was created, tested, or optimised anywhere.**

Hierarchy applied **exactly as the preregistration writes it**: a
strategy is *eligible for promotion* only if its parent survives;
geometry is *reported for all four regardless*. All four parents failed,
so SG1 fails for all four — and all four were still fully scored.

### S1 — HIGH + age ≤ 3, continuation → **TAIL-DEPENDENT / FAILED** · 2/12
118,459 events / 2,139 days (L 56,175 / S 62,284). +1m +0.0570 pts /
+3m −0.0321 / **+5m −0.0021** / +15m +0.0582. MFE/MAE 1.020, FF
**50.18%**, median +5m **−0.25 pts**. Gross +5m −0.0021 CI [−0.1392,
+0.1349] = **−0.002× cost**. Net +5m −0.8721. Beats **neither** control
(last-return −0.2471; state-only −0.0255). Gross sign flips under both
trims. The frozen amplifier destroys the very effect it was meant to
concentrate.

### S2 — LOW + runlen ≥ 3, reversal → **REAL BUT SUB-COST** (also failing SG1, SG4, SG6, SG7) · 8/12 — *the best strategy result*
364,345 events / 2,215 days (L 172,249 / S 192,096). +1m +0.0773 /
+3m +0.1254 / **+5m +0.1200** / +15m +0.0511. MFE/MAE 1.001, FF
**51.17%** (CI on FF−0.5 = [+0.0096, +0.0138], excludes 0), median +5m
**+0.25 pts**. Gross +5m **+0.1200 pts, CI [+0.0740, +0.1651]** —
significant. Rotation perm p **0.00005**. Trims +0.1092 / +0.1254
(tail-robust). Beats **both** controls: last-return-only +0.0782,
state-only +0.0721. Long +0.1521 / short +0.0912.

**And it is still 7× too small to trade.** Gross/cost = **0.138**;
CI-lower/cost = 0.085. Net +5m = **−0.7500 pts per event**, negative in
all 8 years. SG6 fails outright. This is the cleanest possible
demonstration of the study's thesis: a real, stable, incremental,
control-surviving directional edge that cost annihilates.

### S3 — HIGH-ARRIVAL, continuation → **TAIL-DEPENDENT / FAILED** · 1/12
80,008 events. **+5m −0.0371 pts**, net −0.9071, gross/cost −0.043,
FF 50.16%, fails 11 of 12 gates including both controls (−0.3312 and
−0.0759). Consistent with A2: arrival is worse than persistence.

### S4 — IFVG retest-reject + MEMORY ALIGNED → **FAILED** (SG1, SG3, SG4, SG5, SG6, SG7, SG11) · 5/12
6,565 events / 1,958 days (L 3,290 / S 3,275). +1m +0.0943 / +3m
**+0.3065** / **+5m +0.2087** / +15m **−0.1809**. MFE/MAE 1.017, FF
50.40%, median +5m **0.00 pts**.

Gross +5m +0.2087 pts = **0.240× cost**, but CI **[−0.1964, +0.6232]**
includes zero (SG3 fails), perm 0.28465. It *does* beat both mandatory
incremental controls on point estimate — IFVG-alone +0.2894, MEMORY-alone
+0.3293 — which is the one genuinely interesting thing in Lane B. But
with a CI three times the estimate, a +15m sign reversal, an FF
indistinguishable from a coin, and 0.24× cost, **the incremental
comparison is not evidence of anything.** Net +5m −0.6613.

## 13. SG1–SG12 GATE TABLE (M_strat = 4, BH binding)

| id | parent | net +5m | BH q | perm p | SG1 | SG2 | SG3 | SG4 | SG5 | SG6 | SG7 | SG8 | SG9 | SG10 | SG11 | SG12 | passed |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| S1 | A1 FAILED | −0.8721 | 0.00007 | 0.99865 | F | F | F | F | F | F | F | P | F | F | F | P | 2/12 |
| S2 | A4 FAILED | −0.7500 | 0.00007 | 0.00005 | F | P | P | F | P | **F** | F | P | P | **P** | P | P | **8/12** |
| S3 | A2 FAILED | −0.9071 | 0.00007 | 0.81160 | F | F | F | F | F | F | F | F | F | F | F | P | 1/12 |
| S4 | B5 FAILED | −0.6613 | 0.00100 | 0.28465 | F | P | F | F | F | F | F | P | P | **P** | F | P | 5/12 |

**STRATEGY SURVIVORS (all 12 gates): NONE. Advanced: 0 of a permitted 1.**

## 14. Cost analysis (frozen 0.87 pt round turn)

| strategy | gross +5m | gross/cost | CI-lo/cost | gross +15m | gross/cost | net +5m |
|---|---|---|---|---|---|---|
| S1 | −0.0021 | −0.002 | −0.160 | +0.0582 | 0.067 | −0.8721 |
| S2 | **+0.1200** | **0.138** | 0.085 | +0.0511 | 0.059 | −0.7500 |
| S3 | −0.0371 | −0.043 | −0.231 | +0.1761 | 0.202 | −0.9071 |
| S4 | +0.2087 | 0.240 | −0.226 | −0.1809 | −0.208 | −0.6613 |

**The best gross edge anywhere is 0.240× cost (S4, not significant); the
best *significant* gross edge is 0.138× cost (S2).** Nothing is remotely
close to clearing, and no management optimisation was attempted to
manufacture clearance.

## 15. Destruction summaries

**Tail destruction.** A4 strengthens under trimming (−0.0617/−0.0640 vs
−0.0587) — a genuinely non-tail-driven effect. B2 is trim-invariant
(−2.2589 both). B3 collapses (+0.0556 → +0.0055 at 5%). S1/S3 flip sign
under both trims. S2 (+0.1092/+0.1254) and S4 (+0.2442/+0.2212) hold.

**Year destruction.** A4 8/8 and B2 8/8. B5 only 4/8. Every strategy is
**net-negative in all 8 years**, without exception.

**ToD destruction.** A4 3/3, B2 3/3, A5 3/3, A6 3/3, A8 3/3. A1 1/3,
A3 1/3, A7 1/3. S2's gross is positive overnight (+0.104) and PM
(+0.253) but negative AM (−0.025).

**Long/short.** No catastrophic asymmetry: S2 L +0.1521 / S +0.0912;
S4 L +0.1221 / S +0.2955; S1 L +0.0107 / S −0.0137. Side-specific rules
were **not** created — that would be a new hypothesis.

## 16. Exact frozen verdicts

| id | verdict |
|---|---|
| A1 | INSUFFICIENT (sample floors unmet) |
| A2 | FAILED — WRONG DIRECTION (MA3, MA4, MA7) |
| A3 | FAILED (MA3, MA4, MA5, MA6, MA8) |
| A4 | **REAL BUT SUB-MATERIAL** (correct sign, below the 2×-anchor floor) |
| A5 | FAILED — WRONG DIRECTION (MA3, MA4) |
| A6 | **REDUNDANT WITH RUN LENGTH** |
| A7 | FAILED (MA3, MA4, MA6, MA8) |
| A8 | FAILED — WRONG DIRECTION (MA3, MA4) |
| B2 | FAILED — SIGNIFICANT BUT OPPOSITE TO THE FROZEN PREDICTION |
| B3 | FAILED (MA3, MA4, MA8) |
| B4 | FAILED (MA3, MA4) |
| B5 | FAILED (MA3, MA4, MA5) |
| S1 | TAIL-DEPENDENT / FAILED |
| S2 | REAL BUT SUB-COST (also failing SG1, SG4, SG6, SG7) |
| S3 | TAIL-DEPENDENT / FAILED |
| S4 | FAILED (SG1, SG3, SG4, SG5, SG6, SG7, SG11) |

### What exactly survived about IFVG — stated precisely

Not "IFVG works". Specifically:

- **FVG inversion prediction:** MEMORY *does* carry information about
  hold-vs-invert (p 0.00005, 8/8 years, 3/3 ToD, control-surviving) —
  but in the **opposite direction to the frozen hypothesis** and at
  1/3 of the materiality floor. FAILED as preregistered; recorded as a
  refuted direction, not a usable predictor.
- **Post-inversion continuation:** marginal (+0.0556 bp, p 0.058),
  tail-fragile, fails MA8. It *does* exceed a matched generic failure
  control by +0.1045 bp with a CI excluding zero — so the inversion
  event is **not** merely generic reversal — but the excess is far below
  every promotion floor.
- **Retest behaviour:** **no edge at all** (+0.0113 bp, p 0.767,
  MFE/MAE 0.995, FF 49.87%, negative by +15m) and **not distinguishable
  from generic structure failure** (p 0.293).
- **MEMORY interaction:** correct sign, floors met, **entirely
  unsupported** (CI [−0.136, +0.335], p 0.416, 4/8 years).

**IFVG is a marginally-real inversion event and a null retest.** The
tradeable half of the public concept is the half with nothing in it.

## 17. What this study actually established

The four Lane-A "wrong direction" results are not scattered noise — they
tell one coherent story, and it is the opposite of the study's framing:

**Memory lives in fresh, quiet, choppy, low-structure conditions, and it
dies within two minutes.**

- A8: HIGH memory is +0.0675 bp at minute 1, gives back −0.0442 at
  minute 2, and is gone by minute 3. Every later increment is negative
  in every state.
- A4: aged runs reverse; fresh single bars continue. Monotone, 8/8
  years.
- A5/A6: noisy, choppy paths carry *more* memory than efficient, orderly
  ones — and A6's version of that is just A4 again.
- A2: arrival into HIGH is *weaker* than established HIGH, refuting the
  expansion mechanism.
- B2: the same signature at the structural level — fragile gaps form in
  quiet, fresh, choppy, low-velocity conditions.

The programme now has a consistent picture across four independent
studies: 1-minute memory is real → it is spent by minute 2–3 (A8) → 5m
momentum is anti-persistent (RVMR-MOMENTUM H1) → 30m trend is real but
RVMR-redundant (H2). **A4 supplies the mechanism behind ORDINAL-V-TURN.**
None of it is large enough to pay 0.87 points.

## 18. Epistemic status and prospective implications

Everything above is **EXPLORATORY / DEVELOPMENT-DERIVED** on fully
exposed 2019→2026 data. No result is OOS, prospective, or independently
confirmed, and none may be described that way.

**No candidate was frozen, so no prospective start exists and no shadow
logger is authorised or built.** Had anything advanced, its prospective
start would have been the first ET midnight *after* its own freeze
commit, never backdated.

**Per the frozen no-variant rule, the following are NOT tested and any
of them requires a new V2 preregistration:** different state-age cuts,
age ≤1 or ≤5, other run lengths, other velocity/efficiency/flip windows,
other ATR ratios, other MEMORY horizons (2m, 3m), other FVG minimum
sizes (0.10/0.50 ATR), other IFVG lifespans, wick-based inversion, gap
midpoint or CE, second or deeper retests, other cooldowns, HIGH-only or
LOW-only IFVG, long-only or short-only, other time windows, and any stop
or target.

In particular: **A4 and B2 are not promoted, and their attractive
stability is not a licence to search near them.** B2's reversed sign is
recorded as refuted-as-preregistered, not converted into a new
"ALIGNED-gaps-are-fragile" hypothesis — that would be an
outcome-selected variant of a failed cell.

Frozen as knowledge, not monetisation: **A4 (aged-run reversal, real,
sub-material)** and **A8 (the two-minute decay profile)**. They may
later serve as features in a multi-feature probability engine; neither
is a strategy.

## 19. Execution-time disclosures

Recorded in the engine header **before** any outcome was printed; none
changes a gate, threshold, definition, or population:

- **D1 — MA3 unit transport.** B2's primary is a rate, which has no bp.
  The frozen 2×-anchor *rule* was transported to the anchor the
  preregistration quotes in the same units (+3.2469 pp → 6.4938 pp).
- **D2 — Rotation degeneracy.** Days holding fewer than 3 events cannot
  be rotated, making the frozen null conservative for sparse families.
  The gate was applied **as frozen**; the degenerate-day share is
  reported for every permutation (Lane A ≈ 0.001; B4/B5 ≈ 0.003; S4
  0.167). No substitute null was used for any gate decision.
- **D3 — SG4 ratio.** mean(MFE)/mean(MAE); the per-event ratio is
  undefined when MAE = 0.
- **D4 — A5/A8 constructions.** A5's CI is bootstrapped on the
  standardised statistic with cells and weights frozen from the observed
  sample. A8's paired m3−m1 uses the contiguity-to-t+3 population and
  rotates sign(r[t]).
- **D5 — Strategy permutation.** The cost-adjusted primary differs from
  the gross primary by the additive constant −COST, which the rotation
  does not touch, so a two-sided |statistic| test is **not invariant**
  to it: scoring |mean − COST| compares an observed −0.75 against a null
  centred on −0.87 and reports the *null* as more extreme, inverting the
  test. The permutation is evaluated on the quantity the rotation
  randomises (the directional mean) — the identical hypothesis with the
  constant removed from both sides.

## 20. Corrections applied during execution (full disclosure)

Three engine defects were found and fixed. **All three were fixed and
committed before the results they affected were ever displayed**, and
each correction is a separate commit in the history:

1. **`2278a15`** — inversion bars are not in FVG formation order (a
   later gap can invert first), so the B3 event array was not
   chronological and the day-ordering guard aborted the run. Fixed by a
   stable sort. The bootstrap is order-free; only the rotation null was
   affected. **No result was displayed before the guard fired.**
2. **`c1921ee`** — `dc_diff_cw` returns six values; the B6 caller
   unpacked five. Pure arity fix. **No B6 result was displayed before it
   raised.**
3. **This commit** — two verdict/statistic defects, both corrected
   *after* the numbers existed and both disclosed here rather than
   quietly patched:
   - the **D5 permutation defect** above, which had produced
     meaningless strategy permutation p-values (S1 0.00725, S2 1.00000,
     S3 0.05630, S4 0.91535 → corrected to 0.99865, 0.00005, 0.81160,
     0.28465);
   - a **verdict-taxonomy defect** that labelled a significant effect
     with the *wrong sign* as "REAL BUT SUB-MATERIAL". The MA gate
     scoring was always correct (MA3 requires correct sign **and**
     magnitude, and failed for both A2/A5/A8 and B2); only the
     human-readable string was mis-assigned. Corrected so a reversed
     sign reports as FAILED — WRONG DIRECTION / SIGNIFICANT BUT
     OPPOSITE TO THE FROZEN PREDICTION.

**Every Lane-A and Lane-B gate row is byte-identical before and after
the correction in item 3** (verified by diff); only verdict strings and
the four strategy permutation p-values changed. The MA/SG gate scoring
was never altered. This mirrors the RVMR-MOMENTUM-V1 precedent, where a
verdict-logic defect was likewise corrected, re-run deterministically,
and both versions kept in git history.

## 21. Artifacts

| item | path | sha256 |
|---|---|---|
| preregistration | `docs/MEMORY_MATH_IFVG_V1_PREREGISTRATION.md` | `313127d24a8178b7064e9d90af38d7ecaac18d9110f8ba46f0b7827fbc2dac9b` |
| engine (library) | `analysis/memifvg/memifvg_lib.py` | `152732d14ac6caacd7c343a55f2add6f0744cb93129c0178b211f4751b196427` |
| engine (run) | `analysis/memifvg/memifvg_run.py` | `47ac6b33c5860cb047b206c696f7248e73877449a80442f13ba8c61e2e8afd7a` |
| raw output (text) | `analysis/memifvg/MEMIFVG_OUTPUT.txt` | `596c798d195b0eac8c71c54edbcd7703a91a861c6aaca77f0431507f12f4667b` |
| raw output (machine-readable) | `analysis/memifvg/MEMIFVG_RAW.json` | `347a46de173be8817fa812f9f7feec35b723ecbc3171f4f02897cd07ff12bce4` |

The JSON carries every frozen cell — counts, means, CIs, p-values,
q-values, cost fractions, per-year and per-ToD splits, trims, control
comparisons and gate verdicts — including all failures, sufficient to
reproduce every number above. The engine is deterministic; seed 20260826
is the only source of randomness.

Execution UTC **2026-08-26T20:10Z** · findings written
2026-08-26T20:13Z. Commit and clean-tree confirmation are recorded in
the commit that adds this file.

---

**MEMORY-MATH-IFVG-V1 FOUND NO MONETIZABLE MEMORY AMPLIFICATION.**
**MEMORY-PRED remains REAL PREDICTIVE STRUCTURE BUT SUB-COST
STANDALONE.** The search is not expanded. No live or prospective
strategy was modified. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
