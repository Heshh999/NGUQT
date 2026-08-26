# MEMORY-PRED-V1 (H1) — FINDINGS

# VERDICT: PREDICTIVE STRUCTURE SURVIVES BUT SUB-COST — 10/10 gates

**This is a DEVELOPMENT result on EXPOSED data. It is not out-of-sample,
not prospective, and not confirmed.** Highest status permitted:
**DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE.**

Executed against the preregistration frozen at
`cdfcb3148513264ba58a7880ea794c4baa72f1e4`
(sha256 `afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8`,
2026-08-25T22:45:04+00:00). H1 only. **H2 was not executed and not
combined.** No strategy simulated, no order submitted, nothing frozen
modified.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1. FREEZE VERIFICATION

| # | check | result |
|---|---|---|
| 1 | preregistration sha256 | `afac484b…0898dbb8` — **MATCHES**, byte-identical to the freeze commit |
| 2 | freeze commit `cdfcb314…` | present, unchanged, 2026-08-25T22:45:04+00:00 |
| 3 | AC-FLIP lineage | `scan_run.py` `ac()` + `confirm_run.py:862-888` adjacency-restricted variant |
| 4 | RVMR specification | `T1 1.270  T2 2.335  W 1440  RTH 570..960`; first scored index **1440**; causality probes **EXACT** at 5 points |
| 5 | H1 formula | `memoryReturn = sign(r[t]) × r[t+1]` |
| 6 | zero handling | `r[t]==0` excluded (sign undefined); `r[t+1]==0` retained as 0 for the mean, excluded from the sign endpoint |
| 7 | state conditioning | PRIMARY `RB[t] == RB[t+1]`; SECONDARY `RB[t+1]` only (cannot rescue) |
| 8 | controls | ATR × \|r[t]\| × time-of-day, common-weight difference-of-means standardisation |
| 9 | inference | day-cluster on `day[t+1]`, bootstrap 20,000, seed 20260825, 95% CI, within-day label shuffle 20,000 |
| 10 | gates | MP1–MP10 as frozen |

### 1.1 Three engine fixes, disclosed in full

The preregistration (§10.1) permits a crash fix with the diff disclosed,
provided it touches no threshold, constant or definition. Three were
needed. **None touched a threshold, constant, definition, seed or
iteration count, and every pre-permutation number was byte-identical
across all three launches** (Δ `+0.30013`, pooled trim `+0.04445`, etc.).

1. **Before any run** — `em[t-2]` was evaluated before the `t >= 2`
   guard, which would have wrapped to a negative index at `t == 1`.
   Reordered. Also removed a redundant bootstrap call inside the year
   loop whose result was immediately overwritten.
2. **After launch 1** — the permutation sampled `kh + kl` values per day
   (~1.65M draws per iteration, dominated by LOW) and would not have
   finished. Because the three states **partition** each day's assigned
   events, `SUM(LOW) = dayTotal − SUM(HIGH) − SUM(MEDIUM)`; sampling the
   two small groups and deriving LOW by complement is **mathematically
   identical** and costs ~262k draws per iteration.
3. **After launch 2** — still non-terminating. `random.sample()` switches
   to an O(n) pool copy when `n ≤ 21 + 4^ceil(log(3k,4))`; with k ≈ 118
   that threshold is **1045** and the average day holds **~1075**
   assigned events, so a large share of days took the O(n) path.
   Replaced with a partial Fisher–Yates that draws the same uniform
   subset without replacement in guaranteed O(k). The completed run took
   2,036 s, of which the permutation was ~1,800 s.

Only the order in which the RNG stream is consumed differs. The null,
the cluster unit, the 20,000 iterations and the seed are unchanged.

## 2. SOURCE LINEAGE

| artifact | sha256 |
|---|---|
| `docs/RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md` | `afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8` |
| `analysis/anomaly/scan_run.py` | `03d65b1dd6f5fb8995373d188ea2576c9956fa20ab8928d0e5171548a2c92e89` |
| `analysis/anomaly/scan2_run.py` | `6c52693ff4a44fcd7090e9bfd82869196572822ef137547b4e42b9a47f9fd747` |
| `analysis/anomaly/confirm_run.py` | `5ae5e3d4645b2452cbfb1723ef731819c68cc07f0cb92e19f206cc8be22623b8` |
| `analysis/rvmr/rvmr_spec.py` | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` |
| `analysis/rvmr/rvmr_run.py` | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` |

Engine: `analysis/mempred/mempred_run.py`, raw output
`analysis/mempred/MEMPRED_OUTPUT.txt`; supplementary diagnostic
`mempred_tailcomp.py` / `TAILCOMP_OUTPUT.txt`.

## 3. DATA COVERAGE

2,503,622 bars · 2,218 exchange days · 2019-07-04 18:25 → 2026-08-17
15:16 ET · **0 duplicate close stamps**.

- Bars at or after the frozen prospective start **2026-08-26**: **0**
  — prospective data is preserved untouched, trivially.
- Exchange days in the UNSEEN-BUT-PRE-EXISTING window
  **2026-08-18 → 2026-08-25**: **0**. The data does not exist in this
  repository. **Nothing was fabricated and no such check was run.**

## 4. ADJACENCY AUDIT

| item | count |
|---|---|
| candidate `(t, t+1)` index pairs | 2,503,620 |
| removed — gap / non-contiguous minutes | 9,348 |
| removed — `r[t] == 0` (sign undefined) | 108,421 |
| removed — RVMR state unavailable | 1,185 |
| **VALID ADJACENT EVENTS** | **2,384,666** |
| duplicates in source | 0 |
| pairs spanning a calendar-date label (true midnight contiguity, **retained**) | 1,667 |

**No array-adjacency proxy was substituted for time adjacency.** Every
retained event satisfies `em[t+1] − em[t] == 1` **and**
`em[t] − em[t−1] == 1`, so both `r[t]` and `r[t+1]` are genuine
consecutive-minute returns. Cross-session pairs are retained only when
the minutes are truly contiguous.

Primary assignment (`RB[t] == RB[t+1]`): **LOW 1,579,398 · MEDIUM
192,879 · HIGH 68,958**, plus **543,431** events where the state changed
between `t` and `t+1` and which are therefore unassigned under the
primary construction.

## 5. CAUSAL AUDIT — every row YES

| FIELD | AVAILABLE TIME | OUTCOME TIME | CAUSAL |
|---|---|---|---|
| `r[t] = log(c[t]/c[t−1])` | close of bar `t` | n/a | **YES** |
| `sign(r[t])` | close of bar `t` | n/a | **YES** |
| `RB[t]` (window `t−1440…t−1`) | close of bar `t−1` | `r[t+1]` | **YES** |
| `RB[t+1]` (window `t+1−1440…t`) | close of bar `t` | `r[t+1]` | **YES** |
| `atr20(t)` (bars `t−19…t`) | close of bar `t` | `r[t+1]` | **YES** |
| `\|r[t]\|` | close of bar `t` | `r[t+1]` | **YES** |
| time-of-day bucket of `t+1` | clock | `r[t+1]` | **YES** |
| `sign(r[t−1])` | close of bar `t−1` | `r[t+1]` | **YES** |
| RVMR thresholds 1.270/2.335 | fixed 2019 | `r[t+1]` | **YES** |
| `r[t+1]` — OUTCOME | close of bar `t+1` | itself | **YES** |

The RVMR window provably excludes its own bar (EXACT at five probes), so
`RB[t+1]` is known at the close of bar `t`, strictly before the outcome
minute begins. No input contains information from `r[t+1]` or later.

## 6–10. PRIMARY RESULT

`memoryReturn = sign(r[t]) × r[t+1]`, state = `RB[t] == RB[t+1]`.

| state | n | mean (bp) | median (bp) | sd (bp) | 95% CI (bp) | boot p |
|---|---|---|---|---|---|---|
| **LOW** | 1,579,398 | **−0.03340** | −0.00000 | 1.6438 | [−0.03607, −0.03067] | 0.00005 |
| MEDIUM | 192,879 | +0.01547 | −0.00000 | 4.2171 | [−0.00449, +0.03622] | 0.13230 |
| **HIGH** | 68,958 | **+0.26674** | +0.33073 | 9.3238 | [+0.19713, +0.33702] | 0.00005 |

> **Δ = E[mem\|HIGH] − E[mem\|LOW] = +0.30013 bp**
> **95% CI [+0.22979, +0.37161]**, bootstrap p **0.00005** (at the
> 1/20001 floor)

Both required conditions hold: **Δ > 0** and **E[mem|LOW] < 0**.

The point estimates are monotone LOW < MEDIUM < HIGH, though MEDIUM's CI
includes zero (p = 0.132) — reported, not gated, exactly as frozen.

The sign of the completed minute therefore carries **opposite**
information depending on the RVMR state: in quiet regimes it predicts
mild reversal, in active regimes it predicts continuation.

## 11–12. SIGN-PROBABILITY ENDPOINT

`r[t+1] == 0` excluded, as frozen.

| state | n non-zero | P(continuation) | P(reversal) | deviation from 50% |
|---|---|---|---|---|
| LOW | 1,493,160 | 0.481314 | 0.518686 | **−1.8686 pp** |
| MEDIUM | 190,483 | 0.501037 | 0.498963 | +0.1037 pp |
| HIGH | 68,562 | 0.513783 | 0.486217 | **+1.3783 pp** |

> **HIGH − LOW continuation probability = +3.2469 pp**,
> 95% CI [+2.8587, +3.6317] pp, p 0.00005.

The probability endpoint agrees in sign with the primary Δ, as required.
No probability threshold was optimised or searched.

## 13. ECONOMIC SCALE — reported, never a gate

Mean close over HIGH ∪ LOW events: **18,790.69**.

| quantity | value |
|---|---|
| Δ | +0.30013 bp |
| Δ in NQ points | **+0.563968** |
| frozen round-turn cost | 0.87 points (= 0.4630 bp at this level) |
| **Δ as a multiple of cost** | **0.648×** |

> **The effect is real and BELOW cost.** Per the preregistration this is
> a **full pass, not a lesser one** — the frozen verdict class
> `PREDICTIVE STRUCTURE SURVIVES BUT SUB-COST` exists precisely for this
> outcome. It is knowledge about market structure, **not** an edge.
> A 0.56-point expected move against a 0.87-point round turn is
> 0.35 points underwater per event before any spread, slippage or fill
> model is even considered.

## 14–15. MAGNITUDE ROBUSTNESS (frozen set only)

Cutpoints computed once on the assigned population, no search:
p50 `0.0000947975`, p80 `0.0002253362`.

| subset | n HIGH | n LOW | Δ (bp) | 95% CI (bp) |
|---|---|---|---|---|
| **ALL** (primary) | 68,958 | 1,579,398 | **+0.30013** | [+0.22920, +0.37202] |
| TOP50 | 64,409 | 694,347 | +0.32094 | [+0.24657, +0.39466] |
| TOP20 | 56,422 | 201,216 | +0.37282 | [+0.29023, +0.45738] |

The effect strengthens with larger current bars. No top-10%, top-5%,
top-1% or custom threshold was computed.

## 16. 15m SECONDARY — **DID NOT REPRODUCE**

163,779 blocks · 159,008 consecutive contiguous block pairs.

| conditioning | LOW | MEDIUM | HIGH | HIGH < LOW? |
|---|---|---|---|---|
| both blocks same state | −0.0251 bp (n 106,253) | **+0.3873** (n 10,459) | +0.0709 (n 2,135) | **False** |
| forward block only | −0.0202 bp (n 123,045) | **+0.4420** (n 27,951) | +0.2927 (n 7,949) | **False** |

**The frozen 15m expectation failed under both conditionings.** HIGH did
not show greater next-block reversal; it was positive with a CI spanning
zero on only 2,135 pairs.

**An honest discrepancy, stated rather than glossed:** `AC1(15m|HIGH)`
replicated as a *statistic* at −0.0671 in ANOMALY-CONFIRM, yet the
15m `memoryReturn` for HIGH is positive here. The two are different
objects: AC1 weights by magnitude and centres on the mean, whereas
`memoryReturn` uses only the sign of the prior block; and the state
assignment and pairing rules differ. A magnitude-weighted
autocorrelation can be negative while a sign-conditioned mean is
positive. The 15m secondary is a declared secondary and **cannot rescue
or overturn the 1m primary** — it does neither. What it does establish
is that the *15m* limb of AC-FLIP does not translate into a forward
prediction, and that at 15m the interesting cell is MEDIUM
**continuation**, not HIGH reversal.

## 17. ATR CONTROL

Frozen-at-execution tercile cuts: `0.0001859412`, `0.0003433469`.

| ATR tercile | n HIGH | n LOW | Δ_cell (bp) |
|---|---|---|---|
| 0 (low vol) | 722 | 606,608 | +0.55934 |
| 1 | 4,739 | 578,402 | +0.47851 |
| 2 (high vol) | 63,497 | 394,388 | +0.28902 |

| | Δ (bp) | retention |
|---|---|---|
| raw | +0.30013 | — |
| **ATR-standardised** | **+0.45565** | **151.8%** |

The effect is **stronger**, not weaker, after ATR standardisation, and
it is positive in all three terciles — including the lowest, where only
722 HIGH events exist. **RVMR state is not a proxy for volatility here.**

## 18. TIME-OF-DAY CONTROL (frozen buckets, bucket of `t+1`)

| bucket | n HIGH | n LOW | Δ (bp) | 95% CI (bp) |
|---|---|---|---|---|
| OVERNIGHT | 7,975 | 1,327,093 | +0.57352 | [+0.32460, +0.81015] |
| RTH_AM | 46,124 | 48,473 | +0.19044 | [+0.10985, +0.27112] |
| RTH_PM | 14,859 | 203,832 | +0.40291 | [+0.24112, +0.56601] |

**3 of 3 positive, all three CIs excluding zero.** No narrower window
was discovered or tested — no 09:30-only, no lunch exclusion, no
half-hour filtering.

## 19. RETURN-MAGNITUDE CONTROL

Frozen-at-execution tercile cuts: `0.0000590562`, `0.0001486436`.

| \|r[t]\| tercile | n HIGH | n LOW | Δ_cell (bp) |
|---|---|---|---|
| 0 (smallest) | 2,617 | 593,405 | +0.15420 |
| 1 | 5,009 | 574,681 | +0.39285 |
| 2 (largest) | 61,332 | 411,312 | +0.33089 |

| | Δ (bp) | retention |
|---|---|---|
| magnitude-standardised | **+0.28879** | **96.2%** |

The effect **does not disappear** when comparable-sized current bars are
compared. HIGH RVMR is not simply "bigger bars": holding `|r[t]|`
constant retains 96% of Δ, and the effect is positive in every tercile.

**MP8 full 27-cell match (ATR × |r[t]| × time-of-day):** 23 of 27 cells
had ≥ 30 events in both states; **Δ_matched = +0.45607 bp, retention
152.0%**.

## 20. RECENT-MOMENTUM CONTROL

| prior return `r[t−1]` | Δ (bp) | 95% CI (bp) |
|---|---|---|
| same sign as `r[t]` | +0.28613 | [+0.19099, +0.38046] |
| opposite sign | +0.32505 | [+0.21613, +0.43379] |
| **momentum-standardised** | **+0.30637** | retention **102.1%** |

**AC-FLIP is not a disguised momentum-state effect.** Δ is essentially
identical whether the previous minute agreed or disagreed with the
current one. The momentum window was not changed.

## 21. YEAR DESTRUCTION — no year is OOS for H1

| year | n LOW | n HIGH | LOW (bp) | HIGH (bp) | Δ (bp) | ΔP(cont) pp |
|---|---|---|---|---|---|---|
| 2019 (partial) | 93,818 | 5,037 | −0.06358 | +0.26399 | +0.32757 | +5.2852 |
| 2020 | 213,650 | 7,824 | −0.04304 | +0.61514 | +0.65819 | +5.6356 |
| 2021 | 222,345 | 10,621 | −0.02884 | +0.25130 | +0.28015 | +3.6649 |
| 2022 | 226,666 | 9,254 | −0.03339 | +0.62257 | +0.65596 | +3.9141 |
| 2023 | 221,353 | 11,025 | −0.03133 | +0.11069 | +0.14201 | +2.4538 |
| 2024 | 225,702 | 10,473 | −0.02944 | +0.24692 | +0.27636 | +3.4152 |
| **2025** | 229,506 | 9,689 | −0.01797 | **−0.04519** | **−0.02723** | +0.9032 |
| 2026 (partial) | 146,358 | 5,035 | −0.04030 | +0.08982 | +0.13013 | +2.1671 |

**7 of 8 years positive.** No year excluded. **2025 is the one negative
year** — Δ turned slightly negative because HIGH itself went negative;
note the continuation-probability difference stayed positive (+0.90 pp)
even that year, so the *sign* structure persisted while the
magnitude-weighted mean did not. There is also a visible **downward
drift in effect size** from 2020–2022 (+0.66, +0.28, +0.66) to
2023–2026 (+0.14, +0.28, −0.03, +0.13), which is exactly the kind of
decay a prospective test must settle.

## 22. MONTH DESTRUCTION

86 months · **72 positive, 14 negative** · median **+0.27232 bp** ·
best 2022-06 **+1.36801 bp** · worst 2026-02 **−1.27374 bp**.
No month excluded.

## 23. TAIL DESTRUCTION

The gate is the **within-state** trim (each state loses its own top
1%/5%), pre-committed in the engine header before any result existed.

| trim | removed | Δ (bp) |
|---|---|---|
| full sample | — | +0.30013 |
| **within-state, top 1%** | H 690, L 15,794 | **+0.29617** |
| **within-state, top 5%** | H 3,448, L 78,970 | **+0.27982** |
| pooled, top 1% | 16,484 | +0.15651 |
| pooled, top 5% | 82,418 | +0.04445 |

**MP10 passes under both readings** — Δ stays positive in all four — so
the pre-committed choice did not decide the gate. But the two disagree
in *magnitude*, and the supplementary composition diagnostic explains
why and must be reported rather than waved away:

| pooled trim | removed from HIGH | removed from LOW | surviving HIGH |
|---|---|---|---|
| top 1% | 14,004 = **20.3%** of all HIGH | 2,480 = 0.2% of LOW | 54,954 |
| top 5% | 41,251 = **59.8%** of all HIGH | 41,167 = 2.6% of LOW | 27,707 |

Because HIGH-state events have ~5.7× the dispersion of LOW-state events
(sd 9.32 vs 1.64 bp), a **pooled** trim by `|memoryReturn|` deletes most
of the HIGH sample and almost none of LOW — it changes the composition
of the comparison rather than testing its tails. That is precisely why
the within-state trim was named the gate in advance.

**The honest reading:** the effect is not carried by a handful of
freak minutes (within-state trimming removes 93% of it and Δ barely
moves), but it **is** concentrated in the larger-|memoryReturn| HIGH
events — remove the biggest 60% of HIGH observations and only +0.044 bp
remains. Both facts are true and both are stated.

## 24–25. BOOTSTRAP AND PERMUTATION

- day-clustered bootstrap, 20,000 iterations, seed 20260825, cluster =
  `day[t+1]`: Δ CI **[+0.22979, +0.37161] bp**, p **0.00005**
- within-day state-label shuffle, 20,000 iterations, seed 20260825:
  **0 exceedances out of 20,000**, p = **0.00005** (floor)

The permutation preserves each day's state composition and outcome
distribution and destroys only the link between them. Not one of 20,000
relabellings produced a |Δ| as large as the observed one.

## 26–27. MULTIPLICITY

| quantity | value |
|---|---|
| H1 bootstrap p | 0.00005 |
| **BH q at M_binding = 2, conservative bound (binding)** | **0.00010** |
| BH q at M_binding = 2, optimistic bound | 0.00005 |
| BH q at M_cum = 4, conservative (**non-binding sensitivity**) | 0.00020 |

H2 has not been run, so H1's exact BH rank is unknown; the **conservative
bound** (H1 as rank 1 of 2, q = 2p) was used for the gate. It passes by
a factor of 500, so the outcome is not H2-dependent. The M_cum = 4
sensitivity is reported as frozen and **changed no verdict**.

## 28. MP1–MP10

| # | requirement | measured | |
|---|---|---|---|
| **precondition** | LOW ≥ 500,000 · MED ≥ 80,000 · HIGH ≥ 25,000 | 1,579,398 · 192,879 · 68,958 | **PASS** |
| MP1 | adjacency exactness | all 2,384,666 events em-adjacent on both sides; violations 0 | **PASS** |
| MP2 | no leakage | causal audit all YES; RVMR probes EXACT | **PASS** |
| MP3 | Δ > 0 **and** E[mem\|LOW] < 0 | Δ +0.30013 bp, LOW −0.03340 bp | **PASS** |
| MP4 | day-clustered 95% CI excludes 0 | [+0.22979, +0.37161] bp | **PASS** |
| MP5 | BH q ≤ 0.05 at M=2 **and** permutation p ≤ 0.05 | q 0.00010, perm p 0.00005 | **PASS** |
| MP6 | Δ > 0 in ≥ 6 of 8 years | 7 of 8 | **PASS** |
| MP7 | Δ > 0 in ≥ 2 of 3 time buckets | 3 of 3 | **PASS** |
| MP8 | Δ_matched > 0 **and** ≥ 0.50 × Δ_raw | matched +0.45607 vs raw +0.30013 | **PASS** |
| MP9 | Δ > 0 in TOP50 and TOP20 | +0.32094 / +0.37282 bp | **PASS** |
| MP10 | Δ > 0 after top-1% and top-5% trims | within-state +0.29617 / +0.27982 bp | **PASS** |

> ### MP PASSED 10 / 10

**Secondary 1** (forward-state-only, `RB[t+1]` alone): LOW −0.04173,
MEDIUM +0.06223, HIGH +0.38940 bp; Δ **+0.43113 bp**, CI [+0.38210,
+0.48321]. Agrees with and slightly exceeds the primary. It cannot and
did not rescue or overturn anything.

## 29. EXACT VERDICT

> # PREDICTIVE STRUCTURE SURVIVES BUT SUB-COST

Applied mechanically against the frozen classes:

- **REDUNDANT WITH VOLATILITY** — does not apply. MP8 passed with 152%
  retention; the matched contrast strengthened rather than vanished.
  (This precedence class outranks any surviving label, so it was checked
  first.)
- **UNSTABLE** — does not apply. MP6 (7/8 years) and MP7 (3/3 buckets)
  both passed.
- **FAILED / VOID** — do not apply.
- **PREDICTIVE STRUCTURE SURVIVES** — requires the effect to exceed the
  0.87-point round turn. It does not (0.648×).
- **PREDICTIVE STRUCTURE SURVIVES BUT SUB-COST** — all ten gates pass,
  effect below cost. **This is the verdict, and it is a full pass.**

Allowed claim, verbatim from §8 of the preregistration:
*"RVMR state changes the conditional probability of immediate
continuation versus reversal."*

**Not allowed, and not claimed:** that this is an edge, a signal, or
tradeable.

## 30. PROSPECTIVE STATUS

- Frozen prospective start: **2026-08-26 00:00:00 ET**. Bars at or after
  it in this repository: **0**. Prospective data is **preserved
  untouched** for the later confirmation.
- UNSEEN-BUT-PRE-EXISTING window **2026-08-18 → 2026-08-25**: **0
  exchange days present**. The data does not exist here, so **no such
  check was run and nothing was fabricated**.
- Frozen minimum confirmation sample, unchanged: **≥ 60 prospective
  exchange days, ≥ 40,000 eligible events, HIGH ≥ 1,500.**
- **This historical run is NOT confirmation.** Every year 2019–2026 was
  epistemically exposed before H1 was written (AC-FLIP was selected out
  of sixteen scanned statistics using its 2024–2026 replication).

## 31. CANDIDATE FREEZE

Authorised by §8 (all ten gates passed), and no more than this:

```
MEMORY-PRED-V1
STATUS: DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE
  object   memoryReturn = sign(r[t]) x r[t+1]
  state    RB[t] == RB[t+1], frozen RVMR RANGE (1440-bar, 1.270/2.335)
  claim    RVMR state changes the conditional probability of immediate
           continuation versus reversal
  effect   DELTA = +0.30013 bp = +0.563968 NQ points = 0.648x cost
  support  10/10 gates, CI [+0.22979,+0.37161], perm p 0.00005
  NOT      independently confirmed / out-of-sample / prospective
  NOT      a strategy, signal, entry rule, or edge
  NEXT     prospective evidence from >= 2026-08-26 00:00:00 ET only
```

**RVMR-V1's certificate gains no clause.** `rvmr_spec.py`,
`rvmr_run.py`, the forward logger, the prospective ledgers, OFH13/OFH14
and every NinjaTrader host are **byte-for-byte unmodified**. **H2 was
not executed and the two were not combined.** No strategy was built,
optimised, or simulated.

## 32–34. HASHES, COMMIT, TREE

Source hashes in §2. Engine `analysis/mempred/mempred_run.py` and raw
output `MEMPRED_OUTPUT.txt` committed alongside this document; commit id
and clean-tree status are recorded in the commit that carries it
(`git status --porcelain` → 0 lines at execution, HEAD
`cdfcb3148513264ba58a7880ea794c4baa72f1e4`).

---

## CLOSING NOTE

The replicated memory structure does produce genuine forward predictive
information: knowing the RVMR state flips the sign of what the last
minute tells you about the next one, by 3.25 percentage points of
continuation probability, and that survives ATR matching, magnitude
matching, momentum control, every time bucket, 7 of 8 years, 72 of 86
months, tail trimming, a 20,000-iteration day-clustered bootstrap and a
20,000-iteration label permutation with zero exceedances.

It is also **0.648× the round-turn cost**, its 15m limb did not
translate, and its effect size has drifted down since 2022 with one
negative year. It is knowledge, not an edge — and on data that was
already exposed when the hypothesis was written, so it is not even
confirmed knowledge yet.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
