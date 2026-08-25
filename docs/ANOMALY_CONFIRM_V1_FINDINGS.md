# ANOMALY-CONFIRM-V1 — FINDINGS (ONE-SHOT HOLDOUT EXECUTION)

**SHOCK-CONT-MEDIUM: FAILED HOLDOUT (11/15).
MONDAY-RTH: FAILED HOLDOUT (8/9).**

Executed once against the preregistration frozen at
`fd2311af1cd7e4071e6105a1ebf58f4089796cce`
(sha256 `813f03e274059bf664b0a283291899d174e005f9b794afbe772f7aae84136aec`,
2026-08-25T21:14:42+00:00). No threshold, cutpoint or definition was
changed. No strategy was simulated. No order was submitted.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1. FREEZE VERIFICATION

| check | result |
|---|---|
| preregistration sha256 | `813f03e2…4136aec` — **MATCHES** |
| freeze commit `fd2311af…` present and unchanged | **YES** |
| `docs/ANOMALY_CONFIRM_V1_PREREGISTRATION.md` byte-identical to commit | **IDENTICAL** |
| `analysis/anomaly/confirm_freeze.py` byte-identical | **IDENTICAL** (`507c6368…`) |
| `analysis/anomaly/CONFIRM_FREEZE_OUTPUT.txt` byte-identical | **IDENTICAL** (`d307fd55…`) |
| discovery decile cutpoints reproduce | **EXACT** (see below) |
| RVMR thresholds reproduce | **EXACT** — `W=1440`, own bar excluded, first scored index 1440, LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH, five independent probes exact |
| prior 2024+ confirmation artifact exists | **NONE** |
| working tree at execution | clean, `fd2311af…`, branch `claude/ninjatrader-mnq-automation-rqjzgg` |

### 1.1 A halt on the first execution attempt — disclosed in full

The first attempt **halted at PHASE 0 with `ANOMALY-CONFIRM-V1 FREEZE
FAILURE` and never opened the holdout.** The cause was mine and it was
not a defect in the study:

The preregistration publishes the nine cutpoints to **10 decimal
places** (§4.3), and the engine hardcodes those published values. My
reproduction check used a tolerance of `1e-12` — *finer than the
precision at which the constants were published*. The measured deltas
were 2.6e-12 to 4.9e-11, i.e. exactly rounding in the 10th decimal.

The fix changed the **verification tolerance only**, to `5e-11` = half a
unit in the last published place. It touched no threshold, no cutpoint,
no definition, and no holdout statistic existed when it was made. This
is the §10.1 crash-fix clause, exercised and disclosed.

| cut | frozen (published) | reproduced (full precision) | delta |
|---|---|---|---|
| 1 | −0.0011017009 | −0.00110170086197 | 3.80e-11 |
| 2 | −0.0005520548 | −0.00055205484095 | 4.10e-11 |
| 3 | −0.0002889478 | −0.00028894775063 | 4.94e-11 |
| 4 | −0.0001179931 | −0.00011799310597 | 5.97e-12 |
| 5 | +0.0000168159 | +0.00001681590785 | 7.85e-12 |
| 6 | +0.0001601759 | +0.00016017590261 | 2.61e-12 |
| 7 | +0.0003325537 | +0.00033255368277 | 1.72e-11 |
| 8 | +0.0005951824 | +0.00059518244098 | 4.10e-11 |
| 9 | +0.0011091640 | +0.00110916402595 | 2.60e-11 |

**The engine used the FROZEN PUBLISHED values, not the full-precision
reproduction** — that is what "transport unchanged" means. To prove the
rounding cannot have moved a single event: **0 of 59,700** holdout
shocks lie within `1e-9` of any cutpoint.

**One cosmetic defect, disclosed rather than fixed:** the SC2 row's
descriptive string in the raw output still reads "reproduced to 1e-12".
The executed check used 5e-11. The label is stale; the check is correct.

---

## 2. HOLDOUT BOUNDARY

```
DISCOVERY   day <= 2023-12-31    1,577,173 bars   2019-07-04 18:25 .. 2023-12-29 17:00
HOLDOUT     day >= 2024-01-01      926,449 bars   2024-01-01 18:01 .. 2026-08-17 15:16
```

Disjoint, and separated by an unbridged ~73-hour gap.
**Returns using a discovery predecessor bar: 0.** Every shock block and
every forward block in every event is dated ≥ 2024-01-01 (asserted).

## 3. COVERAGE RECONCILIATION

| quantity | frozen expectation | measured | |
|---|---|---|---|
| holdout bars | 926,449 | **926,449** | ✔ |
| contiguous 1m returns | 925,748 | **925,748** | ✔ |
| exchange days | 820 | **820** | ✔ |
| distinct months | 32 | **32** | ✔ |
| 2024 / 2025 / 2026 days | 313 / 311 / 196 | **313 / 311 / 196** | ✔ |
| first holdout bar | 2024-01-01 18:01 | **2024-01-01 18:01** | ✔ |

Derived: 61,073 non-overlapping 15m blocks → **59,700 shock/forward
pairs**; 1 pair crosses a calendar-date label through genuine midnight
contiguity.

## 4. CAUSAL AUDIT (17 rows re-run)

| FIELD | AVAILABLE TIME | OUTCOME TIME | CAUSAL? |
|---|---|---|---|
| 1m log return `r_i` | close of bar `i` | — | **YES** |
| shock block return `rv` | close of bar `i1` | — | **YES** |
| **RVMR RANGE score at `j0`** | close of bar `i1` (window `j0−1440…j0−1` ends at `i1`) | forward block `j0…j1` | **YES** |
| RVMR bucket at `j0` | thresholds fixed 2019 | forward block | **YES** |
| decile cutpoints | frozen 2026-08-25, pre-holdout | holdout events | **YES** |
| decile label | close of bar `i1` | forward block | **YES** |
| shock direction `sgn` | close of bar `i1` | forward block | **YES** |
| forward return `rf` | close of `j1`, all bars > `i1` | itself | **YES** |
| `atr20(i1)` | close of bar `i1` | forward block | **YES** |
| ATR tercile cutpoints | frozen pre-holdout | holdout events | **YES** |
| time-of-day bucket | clock | forward block | **YES** |
| \|shock\| median split | frozen pre-holdout | holdout events | **YES** |
| Monday label | clock / ET date | Monday RTH accrual | **YES** |
| Monday RTH bounds 570–960 | fixed 2019 | Monday accrual | **YES** |
| non-Monday control pool | disjoint days, same construction | — | **YES** |
| secondary diagnostic definitions | frozen pre-holdout | holdout series | **YES** |
| 15m block boundaries | at block close | — | **YES** |

**Every row YES.** Mechanically verified: `j0 = i1 + 1` enforced for
every pair; blocks never share a bar; `trailing_ratio` excludes its own
bar (exact at five probes); no discovery/holdout overlap; leak count 0.

## 5. SHOCK-CONT COUNTS

Holdout decile occupancy under the **frozen** cutpoints — bins are not
10% each, and are not supposed to be:

| dec | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| n | 5918 | 6190 | 5868 | 5954 | 5696 | 6048 | 5954 | 6079 | 6210 | 5783 |
| % | 9.91 | 10.37 | 9.83 | 9.97 | 9.54 | 10.13 | 9.97 | 10.18 | 10.40 | 9.69 |

The distribution transported almost perfectly — the shock-size
distribution of NQ 15m returns is stable across the two eras.

Extreme set (dec0 ∪ dec9): **11,701** events — UP 5,783, DOWN 5,918.
Dropped for a missing RVMR score: **0**.

## 6–9. PRIMARY RESULT — THE LADDER

`cont = sign(shock) × forward15`, state = `RB[j0]`, day-clustered over
the forward block's date, 20,000 iterations, seed 20260825.

| state | n | cont (bp) | 95% CI (bp) | boot p | discovery |
|---|---|---|---|---|---|
| LOW | 6,296 | **−0.1698** | [−0.5358, +0.1959] | 0.3569 | +0.0710 |
| **MEDIUM** | **3,880** | **+0.5345** | **[−0.1041, +1.1703]** | **0.1005** | +0.8423 |
| HIGH | 1,525 | +0.1990 | [−1.1917, +1.5576] | 0.7726 | +0.5354 |

**The MEDIUM effect survived in sign and in most of its magnitude — and
lost its statistical support.** The confidence interval now includes
zero.

### 7–8. UP and DOWN — the structural failure

| side | n | cont (bp) | 95% CI (bp) | p | discovery |
|---|---|---|---|---|---|
| **UP** (dec9) | 1,791 | **+1.1838** | [+0.1193, +2.2664] | 0.0283 | +0.9750 |
| **DOWN** (dec0) | 2,089 | **−0.0222** | [−1.0680, +0.9579] | 0.9659 | +0.7224 |

**The down-shock leg is gone.** In discovery both tails continued
(+0.975 / +0.722). On the holdout, up-shocks continue *more strongly
than in discovery*, and down-shocks do not continue at all — the mean is
essentially zero and slightly negative. The whole of the MEDIUM effect
is now carried by one side. This is exactly the failure mode SC5 was
written to catch, and it caught it.

Context (not gated): LOW-UP +0.1696, LOW-DOWN −0.5724, HIGH-UP −1.8076,
HIGH-DOWN +1.4169 bp.

### 9. Ladder condition

`MEDIUM (+0.5345) > LOW (−0.1698)` ✔ and `MEDIUM > HIGH (+0.1990)` ✔ —
**SC6 PASSES.** The ordering the discovery found is the ordering the
holdout shows. (As frozen in §4.7, no sign requirement was placed on
HIGH; HIGH came out positive but statistically indistinguishable from
zero, exactly as in discovery.)

## 10. dec7 SECONDARY

MEDIUM n 729, fwd15 **−0.0915 bp**, CI [−1.1514, +0.9794], p 0.8679
(discovery +0.7274). All states n 6,079, **−0.0415 bp** (discovery
+0.2420). **The dec7 corroboration did not replicate.** It cannot and
does not rescue anything.

## 11. EFFECT RETENTION

| | discovery | holdout | retention |
|---|---|---|---|
| SHOCK-CONT MEDIUM | +0.8423 bp | **+0.5345 bp** | **63.5%** |

Well above the frozen floor of +0.2808 bp — **SC4 PASSES**. Retention
was never the problem; support was.

## 12. ECONOMIC SCALE vs COST (reported, never gated)

Mean close at holdout MEDIUM extreme events: **23,640.57**.

- effect **+0.5345 bp = +1.2636 NQ points** per event
- frozen round-turn cost **0.87 points** = 0.3680 bp at this price level
- **gross multiple of cost: 1.452×**

Read this correctly: the point estimate sits above cost *gross*, and the
effect is nonetheless **not statistically distinguishable from zero**
(CI [−0.1041, +1.1703]), is **one-sided**, and is **destroyed by
removing 1% of events** (§18). A positive point estimate above a cost
line is not an edge. **No strategy was simulated and none may be built
on this.**

## 13. ATR CONTROL (C1)

| tercile | n MED | MED cont (bp) | n all | ATR-only cont (bp) |
|---|---|---|---|---|
| ATR-LOW | 879 | −0.2649 | 4,107 | −0.1112 |
| ATR-MID | 1,372 | **+1.0992** | 3,934 | +0.1871 |
| ATR-HIGH | 1,629 | +0.4902 | 3,660 | +0.2811 |

- MEDIUM-size weighted: +0.5345 bp — **degenerate, identical to the
  unstratified mean by construction** (see §13.1)
- ATR-standardised (reweighted to the all-state ATR distribution):
  **+0.4299 bp** — 80.4% of unstratified, above the 50% requirement
- terciles with MEDIUM > 0: **2 of 3**
- REDUNDANT-WITH-ATR condition 1 (standardised < 50% of unstratified):
  **False**
- REDUNDANT-WITH-ATR condition 2 (max ATR-only ≥ MEDIUM): **False**
  (max ATR-only +0.2811 vs MEDIUM +0.5345)

→ **not redundant with ATR. SC12 PASSES.** Whatever the MEDIUM effect
is, ordinary volatility state does not account for it.

### 13.1 A specification ambiguity in my own frozen text — disclosed

Preregistration §4.13 defines the stratified effect as the
"stratum-size-weighted mean of the within-tercile MEDIUM effects".
Weighted by **MEDIUM** stratum sizes this is algebraically identical to
the unstratified mean, so the condition could never fire — a degenerate
specification, the same class of defect as the impossible-envelope
errors that voided XMARKET-H8 and RVMR-STRAT-B6.

The only reading that performs the stated job ("if ordinary volatility
state explains the continuation, RVMR gets no credit") is direct
standardisation to the **all-state** ATR distribution. Both numbers are
reported above; the gate was applied on the standardised one. **The
choice did not affect the verdict** — condition 2 is False either way,
so REDUNDANT-WITH-ATR cannot trigger under any reading.

## 14. TIME-OF-DAY CONTROL (C2)

| bucket | n | cont (bp) | 95% CI (bp) |
|---|---|---|---|
| OVERNIGHT | 887 | +0.0370 | [−0.9621, +0.9817] |
| RTH_AM | 1,865 | +0.5880 | [−0.3774, +1.5288] |
| RTH_PM | 1,128 | +0.8373 | [−0.5288, +2.2521] |

3 of 3 positive — **SC13 PASSES**. No CI excludes zero.

## 15. SHOCK-SIZE CONTROL (C3)

| half | n | cont (bp) | 95% CI (bp) | p |
|---|---|---|---|---|
| smaller \|shock\| | 1,698 | +0.6929 | [−0.1855, +1.6408] | 0.1310 |
| larger \|shock\| | 2,182 | +0.4112 | [−0.5526, +1.3655] | 0.3974 |

Smaller half not significantly negative — **SC14 PASSES**. The effect is
not confined to the largest shocks.

**Reported-only diagnostics:** preceding block same sign as shock
n 5,798 cont +0.0087 bp; opposite sign n 5,709 cont +0.2734 bp. Flag:
mild concentration in reversal-following shocks, not gated.

## 16. YEAR STABILITY

| year | n MED | MED (bp) | UP (bp) | DOWN (bp) | LOW (bp) | HIGH (bp) |
|---|---|---|---|---|---|---|
| 2024 | 1,318 | +0.5535 | +2.2988 | **−1.0841** | +0.1400 | +1.3974 |
| 2025 | 1,490 | +0.2503 | +0.6555 | −0.0817 | −0.1512 | −1.0345 |
| 2026 | 1,072 | +0.9063 | +0.4435 | +1.2843 | −0.3823 | +0.1642 |

**3 of 3 years positive — SC9 PASSES.** But look at the DOWN column:
−1.08, −0.08, +1.28. The down-shock leg has no stable sign in any year.

## 17. MONTH STABILITY

**19 of 32 positive**, median month **+0.3275 bp** — **SC10 PASSES**.
Best 2026-07 +5.0906 bp; worst 2026-08 −3.2742 bp.

| | | | |
|---|---|---|---|
| 2024-01 +0.514 | 2024-02 −0.482 | 2024-03 +1.378 | 2024-04 +0.020 |
| 2024-05 +1.468 | 2024-06 +0.710 | 2024-07 +1.740 | 2024-08 −0.250 |
| 2024-09 +2.053 | 2024-10 +1.438 | 2024-11 +0.266 | 2024-12 −2.181 |
| 2025-01 +1.332 | 2025-02 +0.112 | 2025-03 −1.378 | 2025-04 +1.924 |
| 2025-05 −1.490 | 2025-06 −0.602 | 2025-07 −0.253 | 2025-08 −1.133 |
| 2025-09 +2.700 | 2025-10 −0.168 | 2025-11 +3.737 | 2025-12 −3.178 |
| 2026-01 −2.114 | 2026-02 +0.328 | 2026-03 +0.568 | 2026-04 +0.971 |
| 2026-05 −0.480 | 2026-06 +0.818 | 2026-07 +5.091 | 2026-08 −3.274 |

## 18. TAIL DESTRUCTION — THE DECISIVE RESULT

Frozen gate: mean > 0 after removing the top 1% **and** top 5% by
**signed** continuation.

| trim | events removed | n | cont (bp) |
|---|---|---|---|
| full sample | — | 3,880 | +0.5345 |
| **remove top 1%** | 39 | 3,841 | **−0.3629** |
| **remove top 5%** | 194 | 3,686 | **−2.1122** |

> **The top 1% of events — 39 of 3,880 — contribute 167.2% of the total
> MEDIUM effect.** Remove them and the effect is negative. Remove 5% and
> it is strongly negative.

**SC11 FAILS.** The frozen question was "can a small number of huge
continuation events carry confirmation?" The answer on this holdout is
yes, and they do.

Pre-declared reported-only symmetric trims (removing the largest |cont|
in *both* directions) leave it positive: 1% → +0.6359 bp, 5% → +0.4020
bp. The two procedures disagree, and that disagreement is itself the
finding: the outcome distribution has heavy tails on both sides, and the
positive mean depends on the upper tail outrunning the lower one. The
gate is the one-sided signed trim, as frozen. Reported, not
reinterpreted.

## 19. BOOTSTRAP AND PERMUTATIONS

- day-clustered 95% CI on MEDIUM: **[−0.1041, +1.1703]** — **includes 0**
- bootstrap p: **0.1005**
- **P1** day sign-flip: **p = 0.0982**
- **P2** within-day RVMR state shuffle: **p = 0.0644**

**SC7 FAILS on all three legs.** P2 is the null that speaks directly to
the research question — it destroys only the link between RVMR state and
outcome while preserving each day's state composition and outcome
distribution. At p = 0.064 the holdout cannot reject the hypothesis that
the MEDIUM label carries no information about continuation.

## 20–21. MULTIPLICITY

| candidate | boot p | BH q (M=2, **binding**) | BH q (M=5, non-binding) |
|---|---|---|---|
| SHOCK-CONT-MEDIUM | 0.10050 | **0.10050** | 0.25125 |
| MONDAY-RTH | 0.03570 | **0.07140** | 0.17850 |

**Neither clears q ≤ 0.05 at the binding M = 2.** The M = 5 family-size
sensitivity is reported as frozen and changed no verdict.

## 22. SC1–SC15 GATE

| # | criterion | measured | |
|---|---|---|---|
| SC1 | holdout-only data | leak = 0, all events ≥ 2024-01-01 | **PASS** |
| SC2 | frozen cutpoints transported | reproduced within published precision; 0 holdout quantiles | **PASS** |
| SC3 | MEDIUM cont > 0 | +0.5345 bp | **PASS** |
| SC4 | retention ≥ +0.2808 bp | +0.5345 bp (63.5%) | **PASS** |
| SC5 | UP > 0 **AND** DOWN > 0 | UP +1.1838, **DOWN −0.0222** | **FAIL** |
| SC6 | MED > LOW and MED > HIGH | +0.5345 > −0.1698, > +0.1990 | **PASS** |
| SC7 | CI excludes 0 AND P1 ≤ .05 AND P2 ≤ .05 | CI [−0.1041, +1.1703], P1 0.0982, P2 0.0644 | **FAIL** |
| SC8 | BH q ≤ 0.05 at M = 2 | q = 0.1005 | **FAIL** |
| SC9 | positive in ≥ 2 of 3 years | 3 of 3 | **PASS** |
| SC10 | ≥ 18/32 months AND median > 0 | 19 of 32, median +0.3275 bp | **PASS** |
| SC11 | mean > 0 after top-1% and top-5% removal | **−0.3629 / −2.1122 bp** | **FAIL** |
| SC12 | ATR control + not redundant | 2/3 terciles > 0; std +0.4299 vs +0.5345; redundant = False | **PASS** |
| SC13 | ≥ 2 of 3 time buckets positive | 3 of 3 | **PASS** |
| SC14 | smaller-\|shock\| half not significantly negative | CI [−0.1855, +1.6408] | **PASS** |
| SC15 | min n | MED 3,880 ≥ 2,000; extreme 11,701 ≥ 6,000; UP 1,791 / DOWN 2,089 ≥ 800 | **PASS** |

**SC PASSED 11 / 15.**

## 23. SHOCK-CONT-MEDIUM VERDICT

> # FAILED HOLDOUT

Applying the frozen precedence mechanically:

- **REDUNDANT WITH ATR** — does not apply; neither condition fired.
- **CONFIRMED** — requires all 15; four failed.
- **TAIL-DEPENDENT** — its frozen definition requires the effect to be
  "positive **and supported** on the full sample" before failing SC11.
  It is positive but **not** supported (SC7 and SC8 both fail), so this
  verdict does not apply even though the tail failure is real and severe.
- **PARTIALLY CONFIRMED** — requires sign, CI, permutation and BH all to
  pass. SC7 and SC8 fail.
- **INSUFFICIENT DATA** — every n floor was met comfortably.
- **FAILED HOLDOUT** — "any of sign, CI, permutation or BH fails."
  SC7 and SC8 fail. **This is the verdict.**

Plain statement: the effect kept its sign and 63.5% of its size, and
lost everything that made it a claim. It is one-sided, it is not
distinguishable from zero under dependence-aware inference, the state
label fails its own shuffle test at p = 0.064, and 39 events out of
3,880 carry more than all of it.

---

## 24. MONDAY-RTH RESULT

138 Monday-dated exchange days; **137 with RTH bars** (one holiday
Monday has no RTH session — absent, not imputed, exactly as frozen).

| | n | mean (bp) | 95% CI (bp) | p |
|---|---|---|---|---|
| **MONDAY RTH** | 137 | **+14.7444** | **[+0.8872, +28.5287]** | **0.0357** |
| non-Monday RTH | 539 | −2.8478 | [−11.3800, +5.9354] | — |

Companion segments: SUN 18:00–24:00 n 137 **+6.0331 bp** CI [−0.9135,
+13.1896]; MON 00:00–09:29 n 137 **+9.9777 bp** CI [+0.7380, +19.1120].

> **Honest note, not a gate:** in discovery the effect was *localised* to
> RTH, with both overnight segments null. On the holdout, Monday
> 00:00–09:29 is also positive with a CI excluding zero. The
> "localisation to RTH" part of the discovery story did **not** hold.
> The frozen hypothesis was Monday RTH specifically, and that is what
> was tested; the localisation claim is simply now unsupported.

## 25. MONDAY vs NON-MONDAY DIFFERENTIAL

**+17.5922 bp** (discovery +16.2602 bp) — **MR9 PASSES on sign.**
P4 weekday-label permutation p = 0.0671. Monday is not merely a rising
market: non-Monday RTH accrual over the same window is **negative**
(−2.85 bp).

## 26. MONDAY RETENTION

| | discovery | holdout | retention |
|---|---|---|---|
| MONDAY-RTH | +16.6296 bp | **+14.7444 bp** | **88.7%** |

Far above the +5.5432 bp floor. **MR4 PASSES.** This is the strongest
retention figure the programme has produced.

## 27. MONDAY YEAR STABILITY

| year | n | mean (bp) |
|---|---|---|
| 2024 | 52 | +9.9665 |
| 2025 | 52 | +16.8174 |
| 2026 | 33 | +19.0068 |

**3 of 3 positive**, and monotonically increasing.

## 28. MONDAY MONTH STABILITY

**22 of 32 positive**, median **+26.459 bp**. Best 2024-08 +58.628;
worst 2026-07 −67.369. **MR7 PASSES.**

## 29. MONDAY TAIL DESTRUCTION

| trim | removed | n | mean (bp) | removed share of total |
|---|---|---|---|---|
| full | — | 137 | +14.7444 | — |
| remove top 1% | 1 Monday | 136 | **+12.3022** | 17.2% |
| remove top 5% | 7 Mondays | 130 | **+4.7047** | 69.7% |

**MR8 PASSES** — positive after both trims. Mean +14.7444, median
+10.4514, 10%-trimmed mean +15.1978 bp. The median being positive and
close to the mean is meaningful: unlike SHOCK-CONT, this is a broad
effect, not a few sessions. (Seven Mondays still account for ~70% of
total accrual, which is normal for a heavy-tailed daily series and is
reported for completeness.)

## 30. MONDAY INFERENCE

- day-clustered 95% CI: **[+0.8872, +28.5287]** — excludes 0
- bootstrap p: **0.0357**
- **P3** sign-flip permutation: **p = 0.0406**
- **P4** weekday-label permutation (differential): p = 0.0671
- **BH q at M = 2: 0.0714**

## 31. MR1–MR9 GATE

| # | criterion | measured | |
|---|---|---|---|
| MR1 | holdout-only data | all Mondays ≥ 2024-01-01, leak = 0 | **PASS** |
| MR2 | n ≥ 120 Mondays | 137 | **PASS** |
| MR3 | mean Monday RTH > 0 | +14.7444 bp | **PASS** |
| MR4 | retention ≥ +5.5432 bp | +14.7444 bp (88.7%) | **PASS** |
| MR5 | CI excludes 0 AND P3 ≤ 0.05 | CI [+0.8872, +28.5287], P3 0.0406 | **PASS** |
| MR6 | BH q ≤ 0.05 at M = 2 | **q = 0.0714** | **FAIL** |
| MR7 | ≥ 2/3 years AND ≥ 17/32 months | 3 of 3, 22 of 32 | **PASS** |
| MR8 | mean > 0 after top-1% and top-5% | +12.3022 / +4.7047 bp | **PASS** |
| MR9 | definition unchanged AND Mon − nonMon > 0 | +17.5922 bp | **PASS** |

**MR PASSED 8 / 9.**

## 32. MONDAY-RTH VERDICT

> # FAILED HOLDOUT

MONDAY-RTH passed **every substantive condition** — sign, 88.7%
retention, CI excluding zero, its own permutation null, 3/3 years,
22/32 months, both tail trims, and the non-Monday control — and failed
on **one** thing: the multiplicity correction. Its raw p of 0.0357
becomes q = 0.0714 once corrected for the two-hypothesis family.

The frozen rule is unambiguous: "FAILED HOLDOUT — any of sign, CI,
permutation **or BH** fails." I am not going to soften that, because the
correction is the entire reason M was fixed in advance. Two hypotheses
were tested; one produced p = 0.036; that is roughly what one expects
from two draws under a weak or absent effect, which is precisely what BH
is for.

What is fair to record, and what a future study may act on: **this is
the closest any candidate in this programme has come**, and it failed by
a margin (0.0714 vs 0.05) that a modestly larger holdout could decide
either way. That is a reason to design a new, separately preregistered
test — not a reason to reinterpret this one.

---

## 33. AC-FLIP (SECONDARY / NON-PROMOTABLE) — **REPLICATED**

| state | n (1m) | AC1 1m | discovery | n (15m) | AC1 15m | discovery |
|---|---|---|---|---|---|---|
| LOW | 706,196 | **−0.012551** | −0.028036 | 48,046 | −0.002351 | +0.002265 |
| MEDIUM | 165,327 | +0.000460 | +0.016644 | 10,094 | +0.024989 | −0.005023 |
| HIGH | 54,225 | **+0.009395** | +0.023863 | 2,933 | **−0.067115** | −0.032083 |

Frozen criterion: `AC1(1m|LOW) < 0 < AC1(1m|HIGH)` — **holds**
(−0.0126 < 0 < +0.0094). Sub-check `AC1(15m|HIGH) < 0` — **holds**
(−0.0671, twice the discovery magnitude).

Adjacency-restricted variant (both minutes adjacent **and** same state):
LOW −0.013145, MEDIUM −0.002058, HIGH +0.007271 — **the flip survives
the estimator-artifact correction**, so it is market structure, not
filtering.

→ **REPLICATED.** Honest qualifications: magnitudes retained ~45% (LOW)
and ~39% (HIGH); the MEDIUM cell collapsed from +0.0166 to +0.0005; and
the 15m LOW and MEDIUM cells flipped sign versus discovery. None of
those were in the frozen criterion. **This is non-promotable, cannot
rescue SHOCK-CONT, and per §7 of the preregistration adds no RVMR
certificate clause because that clause was conditioned on SHOCK-CONT
confirming.**

## 34. CLV-FLIP (SECONDARY / NON-PROMOTABLE) — **FAILED REPLICATION**

| state | n | corr(CLV, r₊₁) | discovery |
|---|---|---|---|
| LOW | 705,577 | −0.006817 | −0.007007 |
| MEDIUM | 165,239 | −0.007489 | +0.008840 |
| HIGH | 54,214 | **−0.004151** | +0.014121 |

Frozen criterion: negative in LOW **and** positive in HIGH. LOW held
almost exactly; **HIGH did not** — it is negative. All three states are
now negative and essentially flat, so there is **no flip at all**.

One of two legs held, so PARTIAL is arguable; I record **FAILED
REPLICATION** because the object under test *is* the flip, and the leg
that held (LOW negative) is the ordinary bid-ask-bounce baseline while
the discriminating leg failed. Both readings are stated so the
reasoning is auditable.

## 35. LEVERAGE-V (SECONDARY / NON-PROMOTABLE) — **REPLICATED**

P(RVMR RANGE HIGH within 30m | frozen shock decile):

| dec | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| **holdout** | **0.6342** | 0.4045 | 0.2947 | 0.2302 | 0.2111 | 0.2119 | 0.2261 | 0.2698 | 0.3392 | **0.5553** |
| discovery | 0.6402 | 0.4257 | 0.3228 | 0.2608 | 0.2374 | 0.2469 | 0.2741 | 0.3174 | 0.3870 | 0.5562 |

V-shape (d0 and d9 above every d3…d6): **True**. Downside asymmetry
`P(d0) > P(d9)`: **True** (0.6342 vs 0.5553).

→ **REPLICATED**, and remarkably tightly — every decile within 0.03 of
its discovery value across a completely separate 2.6-year window. This
is the most durable structure the whole programme has found. It is a
statement about **volatility-state arrival**, not direction. **No
strategy interpretation. Non-promotable.**

## 36. 15m GRID DISCLOSURE

The frozen grid is anchored to **each calendar day's first valid
contiguous return**, not to a `:00/:15/:30/:45` clock grid. It was
preserved exactly and **not "fixed"** — doing so would have created a
different study.

Measured on the holdout: 2024-01-01 block 1 = 18:02–18:16; 2024-01-02
onward = 00:00–00:14. Across 820 holdout days the grid takes **6
distinct phases**. This is a property of the frozen construction, is
identical in kind to discovery, and is reported so no reader mistakes
these blocks for clock-aligned bars.

## 37. KNOWLEDGE / CANDIDATE FREEZES

**NONE — none is authorized.**

- `SHOCK-CONT-MEDIUM-CANDIDATE-V1` is **NOT** created. It required
  SC1–SC15 all passing; four failed.
- No Monday calendar-anomaly object is frozen; MR6 failed.
- **RVMR-V1's certificate is UNCHANGED.** The shock clause required
  SHOCK-CONT confirmation. The return-memory clause was conditioned on
  SHOCK-CONT confirming as well. Neither is added.
- `rvmr_spec.py`, `rvmr_run.py`, the RVMR forward logger, the
  prospective ledgers, OFH13/OFH14 and every NinjaTrader host are
  **byte-for-byte unmodified**.
- **No strategy may be built from either candidate.**

M stays at 2. Both candidates are **destroyed, not retuned**. No decile,
threshold, horizon, grid, Monday window, weekday split or retention
floor was changed, and none may be.

## 38. SOURCE HASHES

| artifact | sha256 |
|---|---|
| `docs/ANOMALY_CONFIRM_V1_PREREGISTRATION.md` | `813f03e274059bf664b0a283291899d174e005f9b794afbe772f7aae84136aec` |
| `analysis/anomaly/confirm_freeze.py` | `507c63687985b94feb1eb720ddd058ed983fc07fd9ce2781a85ec40087387f80` |
| `analysis/anomaly/CONFIRM_FREEZE_OUTPUT.txt` | `d307fd550a331eafefbab30163bb7c3d5bf9101df9ab680751a8e43cca94f1ab` |
| `docs/ANOMALY_SCAN_V1_PROTOCOL.md` | `edd1f1baae50619a689da15b2ffedfb9c5865e698304c45588b4dbb2ab19255f` |
| `docs/ANOMALY_SCAN_V1_FINDINGS.md` | `79e0355cdc996f5bf7a278c3265140c05ae5997727fd5d7b336890ccd1d0ef22` |
| `analysis/anomaly/scan_run.py` | `03d65b1dd6f5fb8995373d188ea2576c9956fa20ab8928d0e5171548a2c92e89` |
| `analysis/anomaly/scan2_run.py` | `6c52693ff4a44fcd7090e9bfd82869196572822ef137547b4e42b9a47f9fd747` |
| `analysis/rvmr/rvmr_spec.py` | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` |
| `analysis/rvmr/rvmr_run.py` | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` |

Execution artifacts: `analysis/anomaly/confirm_run.py`,
`analysis/anomaly/CONFIRM_RUN_OUTPUT.txt`.

Freeze commit executed against: `fd2311af1cd7e4071e6105a1ebf58f4089796cce`.

## 39–40. COMMIT AND TREE

Recorded in the commit that carries this file. Working tree verified
clean at execution time (`git status --porcelain` → 0 lines, HEAD
`fd2311af…`).

---

## CLOSING NOTE

The scan's strongest economic finding did not replicate, and the
calendar effect missed by 0.021 of a q-value. That is what the frozen
gate was built to determine, and it determined it in one run with
nothing changed after the fact.

What survived is not directional and not tradeable: RVMR conditions
short-horizon return memory (AC-FLIP), and RVMR state arrival is
forecastable with a stable downside asymmetry (LEVERAGE-V, every decile
within 0.03 across 2.6 unseen years). Both are structure. Neither is an
edge, and neither is promotable.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
