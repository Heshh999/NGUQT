# ANOMALY-CONFIRM-V1 — PREREGISTRATION (frozen BEFORE the holdout is opened)

**PRIMARY: SHOCK-CONT-MEDIUM.  SECONDARY PROMOTABLE: MONDAY-RTH.  M = 2.**

**Status: PREREGISTRATION ONLY.** The 2024-01-01 → 2026-08-17 holdout
has not been opened. No candidate outcome on it exists. This document is
written, hashed, committed and pushed *first*; a later directive opens
the holdout exactly once.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 0. SUPERSESSION, RESULT-BLINDNESS, AND CONTAMINATION DISCLOSURE

### 0.1 This document supersedes an earlier preregistration at the same path

An earlier ANOMALY-CONFIRM-V1 preregistration was committed at
`663fded88c6dfd0bf52dc3b28143f42b34f2c994`
(sha256 `45d699a320da19058a240a8e3e17d283c24e672107060d2837fd82e4f57e16e6`)
with the promotable family `{AC-FLIP, MONDAY}`.

Why it is replaced, stated plainly: that document existed because the
commissioning directive named AC-FLIP and MONDAY while the frozen scan
source's own final recommendation named SHOCK-CONT-MEDIUM and
MONDAY-RTH. I surfaced the conflict and resolved it provisionally in
favour of the directive. **The principal has now resolved it in favour
of the frozen source.** The family is therefore
`{SHOCK-CONT-MEDIUM, MONDAY-RTH}`, and AC-FLIP joins CLV-FLIP and
LEVERAGE-V as a non-promotable diagnostic.

**No multiplicity was consumed by the superseded document.** It was
never executed; the holdout was never opened under it; zero holdout
statistics exist from it. The superseded version remains in git history
at the commit above and is not deleted or rewritten. The
cumulative-family clause it contained is replaced by §6.3 below.

### 0.2 Result-blindness — explicit confirmations required by Step 16

| candidate | 2024+ result viewed? |
|---|---|
| SHOCK-CONT-MEDIUM | **NO** |
| MONDAY-RTH | **NO** |
| AC-FLIP | **NO** |
| CLV-FLIP | **NO** |
| LEVERAGE-V | **NO** |

Nothing on 2024+ has been computed for any candidate: no SHOCK-CONT
result, no Monday return, no autocorrelation, no CLV, no variance ratio,
no entropy, no RVMR-conditioned continuation or reversal, no leverage-V,
no CI, no p-value, no year result, no month result, no other performance
or outcome statistic. No "quick sanity check" was run.

This is structural, not a matter of my memory:

- `analysis/anomaly/scan_run.py:22,67` and `scan2_run.py:19,63` gate
  every statistic on `day[i] <= '2023-12-31'`.
- `analysis/anomaly/confirm_freeze.py` (this study's freeze program,
  committed alongside this document) restricts to the same window and
  carries a hard `assert` that no shock/forward pair touches a bar dated
  after 2023-12-31 — the assertion passed on the run recorded in
  `analysis/anomaly/CONFIRM_FREEZE_OUTPUT.txt`.

### 0.3 What was permitted and done before this freeze

Schema inspection, date coverage, counts-only feasibility, source
lineage, code audit, timestamp audit, RVMR parity audit — all performed
(§1, §2, §3.1). Plus discovery-window computation of the constants that
must transport unchanged (§4.3, §4.5, §4.9, §5.3) and the
discovery-window effect anchors that retention thresholds are written
against (§4.6, §5.4). Those are discovery-side numbers on already-mined
data; they are not holdout outcomes and they are exactly what "write the
threshold numerically now" requires.

### 0.4 Two honest lineage disclosures

**(a) The holdout is not pristine in the absolute sense.** Recorded in
the scan protocol at its own freeze (`ANOMALY_SCAN_V1_PROTOCOL.md:25–30`)
before any scan statistic existed, and restated here: prior *separate*
studies — XMARKET-V1, RVMR-VALIDATION-V1, RVMR-BANDS-V1,
NQ-DIRECTION-V1, 4H-DVT-V1 — computed on 2024–2026. None of them
computed shock-response curves, weekday accrual, state-conditional
autocorrelation, CLV predictivity, or state-arrival probability. What is
protected is **this family's selection process**: both promotable
candidates were selected on ≤ 2023-12-31 data only. A confirmed result
is therefore HISTORICAL evidence, not a prospective out-of-sample
result.

**(b) A ~30-bar edge read in the discovery LEVERAGE-V statistic.** The
frozen Wave-2 code scans forward with `min(i1 + 31, N)` where `N` is the
**full** series length (`scan2_run.py:329`). For the last 2 of 102,706
discovery blocks, that scan could reach past the final discovery bar
into early-2024 bars — and it reads `RB`, i.e. a *range* state, never a
return or an outcome. Two blocks out of 102,706, and only for a
non-promotable diagnostic. Disclosed rather than silently corrected; the
holdout run uses the identical expression so both windows are treated
the same.

---

## 1. STEP 1 — SOURCE / LINEAGE AUDIT

| artifact | role | sha256 | last commit |
|---|---|---|---|
| `docs/ANOMALY_SCAN_V1_PROTOCOL.md` | Wave-1 protocol + Wave-2 menu | `edd1f1baae50619a689da15b2ffedfb9c5865e698304c45588b4dbb2ab19255f` | `c4c4d8202e0f9562f659f3f9a659b53da842b067` |
| `docs/ANOMALY_SCAN_V1_FINDINGS.md` | scan findings, both waves | `79e0355cdc996f5bf7a278c3265140c05ae5997727fd5d7b336890ccd1d0ef22` | `70c373568e636a911f6a5f43693263a058053f82` |
| `analysis/anomaly/scan_run.py` | Wave-1 implementation | `03d65b1dd6f5fb8995373d188ea2576c9956fa20ab8928d0e5171548a2c92e89` | `03f0e985505a06c4808bf94b34e4d241b57e6a33` |
| `analysis/anomaly/scan2_run.py` | Wave-2 implementation (S9, S11, S19, S22) | `6c52693ff4a44fcd7090e9bfd82869196572822ef137547b4e42b9a47f9fd747` | `70c373568e636a911f6a5f43693263a058053f82` |
| `analysis/rvmr/rvmr_spec.py` | frozen RVMR-V1 specification | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` | `84933d28c71c07e149e7728a96b4af7d30ea1685` |
| `analysis/rvmr/rvmr_run.py` | canonical NQ 1m loader | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` | `9d14dfaa9be90b5a3ee407690b543dcedbb27bc0` |

**Freeze ORDER — the property that makes the discovery honest:**

```
9f71b24   Wave-1 protocol frozen          (BEFORE any Wave-1 statistic)
03f0e98   Wave-1 scan run + findings
c4c4d82   Wave-2 menu frozen              (BEFORE any Wave-2 statistic)
70c3735   Wave-2 scan run + findings
663fded   superseded confirm prereg       (never executed)
THIS      confirm prereg, holdout untouched
```

**Confirmed:** every candidate definition was fixed before the
computation that produced it. Wave-1's eight statistics (S1–S8) and
Wave-2's eight (S9–S14, S19, S22) were both tabulated in the protocol
before their engines ran, and the two-candidate cap was declared in the
protocol, not after seeing results.

**Data:** `…/scratchpad/rvmr_1m/rvmr_1m_{2019..2026}.csv`, eight files,
loaded by `rvmr_run.load_bars()` with `STAMP_SHIFT = 0`, close-stamped
ET wall clock, 2,503,622 rows.

**Definitions below are lifted from source by file and line. Nothing is
reconstructed from the commissioning prompt.** Where the prompt's prose
and the source disagree, the source governs and the disagreement is
reported (see §4.7, which is one such case).

---

## 2. STEP 2 — HOLDOUT VERIFICATION (counts only)

| window | rule | rows | first | last |
|---|---|---|---|---|
| DISCOVERY | `day <= 2023-12-31` | **1,577,173** | 2019-07-04 18:25 | 2023-12-29 17:00 |
| **HOLDOUT** | `day >= 2024-01-01` | **926,449** | **2024-01-01 18:01** | **2026-08-17 15:16** |

`1,577,173 + 926,449 = 2,503,622` = the full row count. **Zero overlap**:
no row satisfies both rules, and the two spans do not touch — the last
discovery bar is 2023-12-29 17:00 and the first holdout bar is
2024-01-01 18:01, an unbridged gap of ~73 hours which the `em`
contiguity test rejects automatically, so **no return, no 15m block and
no shock/forward pair can straddle the boundary.**

Holdout coverage (timestamp column only — open/high/low/close/volume
were never read to produce these):

- bars **926,449**; contiguous 1m pairs available **925,748**
- exchange days **820** — 2024: 313, 2025: 311, 2026 partial: 196
- distinct months **32** (2024-01 … 2026-08)
- day-of-week: Mon **138**, Tue 137, Wed 137, Thu 137, Fri 134, Sun 137
- RTH-stamped bars (mod 570…960) **259,372**; Monday RTH bars **51,541**
- bars strictly before the holdout, available for the RVMR 1440-bar
  warmup: **1,577,173** (warmup fully satisfied from discovery)

**Deliberately not computed:** holdout RVMR bucket occupancy and holdout
event counts. Both require reading high−low, which is one step from a
conditional result. Minimum-n floors (§4.11, §5.7) are therefore derived
from *discovery* rates scaled by the holdout row ratio
(926,449 ⁄ 1,572,786 = 0.589), never from a holdout measurement.

---

## 3. STEP 3 — FAMILY SIZE, AND THE MACHINERY BOTH CANDIDATES SHARE

### 3.1 RVMR parity audit (allowed pre-freeze; no outcome)

Run and recorded in `CONFIRM_FREEZE_OUTPUT.txt`:

- `trailing_ratio(W = 1440)` reproduced **EXACTLY** against an
  independent direct recomputation at five probe indices (1440, 100000,
  700000, 1200000, 1577000).
- First index carrying a score is **1440**, confirming the window is
  1440 *bars* ending at `i−1` and **excludes the current bar**.
- Buckets: `LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH`, unchanged.
- The array-form `atr20` used for the ATR control matches the frozen
  `rvmr_spec.atr20` with **0 mismatches** over bars 100–4999 (identical
  estimator, tractable form — the frozen function needs 2.5M tuples).

### 3.2 Family size — FROZEN

> **M = 2.** Promotable: **1. SHOCK-CONT-MEDIUM  2. MONDAY-RTH.**
>
> M remains **2** if either becomes VOID, INSUFFICIENT DATA, or FAILS.
>
> **Not** in the promotable family, and never added to it: AC-FLIP,
> CLV-FLIP, LEVERAGE-V, half-hour drift, VR(2), news-minute effects,
> clock harmonics, tail effects, OU half-life, Hill index,
> overnight drift, open-gap response, turn-of-month,
> Parkinson/close-close geometry.

### 3.3 Shared construction (verbatim from the frozen sources)

**Returns** (`scan2_run.py:68–72`):

```python
for i in idx:
    if i == 0 or em[i] - em[i-1] != 1 or c[i-1] <= 0: continue
    rets.append((i, math.log(c[i] / c[i-1])))
```

Close-to-close log returns on **strictly minute-contiguous** bars. Gaps
skipped, never bridged. No bar is interpolated, forward-filled, split
into a lower timeframe, or manufactured. For the holdout run,
`idx = [i for i in range(N) if day[i] >= '2024-01-01']`.

**15m blocks** (`scan2_run.py:74–89`): within each calendar day, walk the
day's return list; accept a block of 15 consecutive entries only if
`block[-1][0] - block[0][0] == 14` (a genuinely unbroken 15 minutes);
non-overlapping (`k += 15` on accept, `k += 1` on reject). Block return
is the sum of its 15 log returns.

> **GRID-ANCHORING FACT, verified empirically and recorded rather than
> assumed:** the block grid is anchored to **each calendar day's first
> contiguous return**, *not* to a :00/:15/:30/:45 clock grid. Measured
> first blocks in discovery: 2019-07-04 → 19:59–20:13; 2019-07-05 →
> 01:01–01:15; 2019-07-07 → 18:02–18:16; 2019-07-08 → 00:00–00:14. The
> grid phase therefore varies by day with the session's first available
> minute. This is the frozen construction and it transports unchanged.

**RVMR state**: `rvmr_spec.trailing_ratio(high − low, W = 1440)` then
`rvmr_spec.bucket()`. **RANGE component only — the VOLUME regime is not
used anywhere in this study.** Computed on the full 2019–2026 series
exactly as the scans do (`scan2_run.py:64–65`) and read only at holdout
indices. This is causal: the normaliser for bar `i` uses bars
`i−1440 … i−1` only. **`rvmr_spec.py` is not modified. No
recalibration, ever.**

### 3.4 STEP 5 — Inference (frozen)

- **Cluster unit: the exchange day.** A minute or an event is never
  treated as an independent trial. For SHOCK-CONT the day key is
  `dd2` = the calendar date of the **forward** block
  (`scan2_run.py:101`); for MONDAY-RTH it is the Monday itself.
- **Day-clustered percentile bootstrap**, whole days resampled with
  replacement, **20,000 iterations**, **seed 20260825**, **95%** CI
  (2.5 / 97.5 percentiles).
- **Bootstrap p-value:** `p = 2 × min(#{b ≤ 0}, #{b ≥ 0}) / B`, floored
  at `1/(B+1)`. This is the primary p carried into BH.
- **Permutation nulls** (independent of the bootstrap), 20,000
  iterations, seed 20260825, two-sided — per candidate in §4.10 / §5.6.
  A permutation p ≤ 0.05 is a **required corroboration**, not a
  substitute.
- **No minute-level iid standard errors are used anywhere.**
- No ML. No parameter sweeps. No retuning. One run.

### 3.5 STEP 6 — Multiplicity (frozen)

Benjamini–Hochberg at **M = 2** over the two promotable primary
p-values, target **q ≤ 0.05**. Non-promotable diagnostics are excluded
from BH, create no promotion slot, and **cannot rescue a failed
primary**; their statistics are reported and labelled
**SECONDARY / NON-PROMOTABLE**.

**Disclosed multiplicity honesty (non-binding).** Five statistics touch
the holdout: two promotable + three diagnostics. BH at M = 2 is the
binding gate as directed. Alongside it the execution will *report*
BH at M = 5 as a **sensitivity only** — it may not change a verdict in
either direction. Stating it now prevents a later reader from
mistaking the corrected family for the full set of things measured.

### 3.6 STEP 7 — Retention formula (frozen)

```
retention = holdout_effect / discovery_effect        (same units, bp)
```

Discovery and holdout are **reported separately and never pooled**.
Combined discovery+holdout significance is **never** the confirmation
statistic. Discovery anchors are fixed in §4.6 and §5.4 and may not move.

---

## 4. CANDIDATE 1 — SHOCK-CONT-MEDIUM (PRIMARY)

### 4.1 Source

`scan2_run.py:91–132` (statistic S9), reported in
`ANOMALY_SCAN_V1_FINDINGS.md` §E.

### 4.2 Exact event definition (every element frozen)

| element | frozen value / rule | source |
|---|---|---|
| return formula | `log(c[i]/c[i-1])`, contiguous minutes only | `scan2_run.py:70–72` |
| 15m aggregation | per calendar day, 15 consecutive returns with index span exactly 14, non-overlapping, grid anchored to the day's first contiguous return | `scan2_run.py:78–89` |
| timestamp convention | ET wall-clock **close** stamp, `STAMP_SHIFT = 0`; `day` = calendar date of the stamp | `rvmr_run.load_bars` |
| session universe | **all sessions, 24h** — no RTH restriction, no time-of-day filter | `scan2_run.py:95–101` |
| pairing rule | consecutive `r15` entries with `j0 − i1 == 1` (forward block starts the very next minute after the shock block ends) | `scan2_run.py:96–101` |
| RVMR component | **RANGE** = `trailing_ratio(high − low, 1440)` | `scan2_run.py:64` |
| RVMR thresholds | LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH | `rvmr_spec.py:68,76–79` |
| RVMR timing | **`RB[j0]`** — the state of the **first bar of the FORWARD block** | `scan2_run.py:101` |
| shock ranking | pooled sort of every pair's shock return | `scan2_run.py:102` |
| cutpoint construction | **global, static, in-sample over the ENTIRE discovery pair set** — *not* trailing, *not* annual, *not* rolling | `scan2_run.py:103` |
| decile assignment | `dec_of(x)`: first `k` with `x < cut[k]`, else 9 | `scan2_run.py:105–109` |
| outcome | `rf` = the forward block's 15m log return | `scan2_run.py:98` |
| overlap handling | blocks non-overlapping by construction; shock and forward never share a bar | `scan2_run.py:82–89` |
| same-session rule | pairs may cross a calendar-date label when minutes are genuinely contiguous (7 of 99,308 in discovery); they can never cross a data gap | measured |
| warmup | RVMR needs 1440 prior bars; fully supplied from discovery | §2 |
| missing bars | skipped; a block containing a gap is rejected outright | `scan2_run.py:84` |
| day boundary | day key for clustering = `dd2`, the forward block's date | `scan2_run.py:101` |

**The RVMR-timing row is the causally critical one.** `RB[j0]` depends
only on bars `j0−1440 … j0−1`, i.e. everything up to and including
`i1`, the shock block's final bar. It is therefore **known at the close
of the shock block, strictly before the outcome window opens.** This is
the opposite of the impossible-envelope defect that voided XMARKET-H8
and RVMR-STRAT-B6, and it is verified in the causal audit (§8).

### 4.3 THE FROZEN DECILE CUTPOINTS — these transport unchanged

Computed once on the discovery pair set (99,308 pairs) by
`confirm_freeze.py`. **The holdout engine hardcodes these nine numbers
and computes no quantile of its own.**

| cut | boundary | log-return | bp |
|---|---|---|---|
| 1 | dec0 \| dec1 | `-0.0011017009` | −11.017 |
| 2 | dec1 \| dec2 | `-0.0005520548` | −5.521 |
| 3 | dec2 \| dec3 | `-0.0002889478` | −2.889 |
| 4 | dec3 \| dec4 | `-0.0001179931` | −1.180 |
| 5 | dec4 \| dec5 | `+0.0000168159` | +0.168 |
| 6 | dec5 \| dec6 | `+0.0001601759` | +1.602 |
| 7 | dec6 \| dec7 | `+0.0003325537` | +3.326 |
| 8 | dec7 \| dec8 | `+0.0005951824` | +5.952 |
| 9 | dec8 \| dec9 | `+0.0011091640` | +11.092 |

Discovery decile counts are 9,930–9,931 per bin, confirming a clean
in-sample decile partition. **A holdout decile will NOT contain exactly
10% of holdout events, and that is correct** — transporting fixed
cutpoints is the whole point; any drift in the realised bin shares is
itself information and is reported, never corrected.

### 4.4 Primary endpoint — ONE decisive statistic

Direction-normalised continuation:

```
sgn  = +1 if shockReturn > 0 else -1        (zero shocks excluded)
cont = sgn × forward15Return
```

Extreme set = **dec9 ∪ dec0** (top decile up, bottom decile down).

> **PRIMARY TEST:**
> `E[ cont | dec ∈ {0,9}, RB[j0] == MEDIUM ] > 0`
> with day-clustered inference per §3.4.

**No other decile and no other horizon may rescue a failure of this
endpoint.** There is no 30m variant, no dec8, no top-5%, no top-15% in
this study.

### 4.5 Frozen control cutpoints (also transported unchanged)

| control | definition | frozen cutpoints |
|---|---|---|
| **C1 ATR** | `atrRel = atr20(i1) / close(i1)`, measured at the shock block's **last** bar | terciles `0.0004875675`, `0.0007651141` → ATR-LOW / ATR-MID / ATR-HIGH |
| **C2 time-of-day** | bucket of `mod[j0]` (forward-block start) | OVERNIGHT `mod ≥ 1081 or mod ≤ 569`; RTH_AM `570–750`; RTH_PM `751–960` |
| **C3 shock size** | `abs(shockReturn)` median split, **per side** | UP `0.0017210529` (17.211 bp); DOWN `0.0017934863` (17.935 bp) |

`atr20` is SMA(20) of true range ending at the bar — known at `i1`,
before the outcome. Discovery C2 occupancy: OVERNIGHT 8,147 /
RTH_AM 6,374 / RTH_PM 5,340.

### 4.6 Discovery anchors (the retention baseline — frozen numbers)

Extreme events in discovery: **19,861** (dec0 9,930 + dec9 9,931; 4
events dropped for a missing RVMR score).

| RVMR state at `j0` | n | cont (bp) | 95% CI (bp) |
|---|---|---|---|
| LOW | 10,530 | **+0.0710** | [−0.2441, +0.3980] |
| **MEDIUM** | **6,737** | **+0.8423** | **[+0.3598, +1.3253]** ← PRIMARY ANCHOR |
| HIGH | 2,590 | +0.5354 | [−0.4720, +1.5376] |

UP / DOWN decomposition:

| state | UP (dec9) n / cont | DOWN (dec0) n / cont |
|---|---|---|
| LOW | 5,729 / +0.0417 bp | 4,801 / +0.1059 bp |
| **MEDIUM** | **3,198 / +0.9750 bp** | **3,539 / +0.7224 bp** |
| HIGH | 1,003 / +1.1182 bp | 1,587 / +0.1670 bp |

These reproduce the published Wave-2 figures exactly (§E reported dec9
MEDIUM +0.975 bp and dec0 MEDIUM −0.722 bp; direction-normalising the
latter gives +0.7224). **Both MEDIUM tails are positive in discovery.**

dec7 secondary: MEDIUM n 1,393, fwd15 **+0.7274 bp**; all states
n 9,931, fwd15 +0.2420 bp (matching the published +0.242).

### 4.7 REGIME LADDER — a source/prose discrepancy, pinned before the holdout

The Wave-2 findings prose describes a ladder: *"LOW inert, MEDIUM
continues, HIGH reverts."* The commissioning directive repeats it and
asks whether HIGH must be required to revert.

**The frozen discovery data does not support requiring HIGH < 0 in this
statistic.** In the continuation metric, HIGH is **+0.5354 bp**,
positive, with a CI spanning zero. The "HIGH reverts" element of the
prose comes from a *different* statistic — `AC1(15m | HIGH) = −0.0321`
(Wave-1 S2) — which is the AC-FLIP diagnostic, not shock continuation.

Freezing a HIGH < 0 requirement would therefore be importing a claim the
primary statistic never made. The ladder condition is frozen as:

> **`cont(MEDIUM) > cont(LOW)` AND `cont(MEDIUM) > cont(HIGH)`**
> — MEDIUM strictly greatest. No sign requirement is placed on HIGH.

Discovery satisfies this: +0.8423 > +0.5354 and +0.8423 > +0.0710.
Whether HIGH turns negative on the holdout is **reported as
information**, and it is **not** a gate in either direction.

### 4.8 Economic materiality — reported, deliberately not the gate

At the discovery median close of **15,995.50**, 1 bp = **1.5996 index
points**, and the frozen **0.87 pt round-turn cost = 0.5439 bp**.

- Discovery MEDIUM effect +0.8423 bp ≈ **1.35 points/event** ≈ **1.55×**
  the round-turn cost, gross. (Consistent with the findings' "~1.5–2.5
  NQ points".)
- **The retention floor (§4.9) sits BELOW cost.** +0.2808 bp ≈ 0.45
  points — about 0.52× cost. This is deliberate and stated now: the
  retention gate asks *did the anomaly replicate*, not *is it
  tradeable*.

> **Cost-parity is REPORTED, never gated:** the execution reports
> whether the holdout MEDIUM effect exceeds 0.5439 bp. Exceeding it does
> **not** imply a profitable strategy — there is no spread model, no
> slippage model, no fill model, and per §7 no trade is simulated at all.

### 4.9 Effect-retention threshold — written numerically now

> **`cont(MEDIUM)` on the holdout must be ≥ +0.2808 bp**
> (= 1/3 of the discovery anchor +0.8423 bp), **and positive in sign.**

Retention ratio = `holdout_MEDIUM_bp / 0.8423`. One third is chosen as
the defensible mid-point of the 25–33% band the directive allows, fixed
before any holdout number exists. **There is no "close enough" clause.**
A holdout effect of +0.2807 bp fails SC4.

MONDAY-RTH's analogous threshold is in §5.4.

### 4.10 Inference and permutation nulls for SHOCK-CONT

Bootstrap: day-clustered over `dd2`, 20,000 iterations, seed 20260825,
95% percentile CI, p per §3.4.

Two permutation nulls, both required at p ≤ 0.05:

- **P1 — day-level sign flip.** Multiply every continuation value in a
  day by the same ±1 (probability ½ per day, independent across days),
  recompute `cont(MEDIUM)`. Null: mean continuation is zero, respecting
  within-day dependence.
- **P2 — within-day state shuffle.** Randomly permute the RVMR state
  labels **among the extreme events inside the same day**, leaving
  outcomes in place. Null: the state carries no information about
  continuation. This is the null that speaks directly to the research
  question — it preserves each day's state composition and its outcome
  distribution and destroys only the link between them.

### 4.11 Stability, tails, minimum n — all thresholds frozen

**Minimum n (SC15).** Discovery produced 6,737 MEDIUM extreme events
from 1,572,786 returns. Scaling by the holdout return ratio (0.589)
implies ≈ 3,970. Floors, set at ~50% of expectation:

- MEDIUM extreme events ≥ **2,000**; total extreme events ≥ **6,000**;
  MEDIUM-UP ≥ **800** and MEDIUM-DOWN ≥ **800**.

Below any floor → **INSUFFICIENT DATA**, not a soft pass.

**Year stability (SC9).** `cont(MEDIUM)` positive in **≥ 2 of 3** years
{2024, 2025, 2026-partial}. Individual-year significance is **not**
required. **No year may be excluded** for any reason.

**Month stability (SC10).** `cont(MEDIUM)` positive in **≥ 18 of 32**
months **and** the median month > 0. Reported: n, sign and magnitude per
month; count of positive/negative months; median, best and worst month.

**Tail destruction (SC11).** Rank the MEDIUM extreme events by **signed**
`cont`; remove the top 1% and recompute; remove the top 5% and
recompute. **Gate: the mean must remain > 0 after both trims.** Also
reported (not gated): symmetric trims by `|cont|`, and the share of the
total effect contributed by the top 1% of events.

### 4.12 THE FIFTEEN CONFIRMATION CONDITIONS (Step 9)

| # | condition | frozen threshold |
|---|---|---|
| SC1 | holdout-only data | every bar of every event dated ≥ 2024-01-01; 0 boundary-straddling returns (RVMR warmup excepted and declared causal) |
| SC2 | discovery cutpoints transported | the nine §4.3 values hardcoded; **zero** quantiles computed on holdout data |
| SC3 | MEDIUM continuation positive | `cont(MEDIUM) > 0` |
| SC4 | effect retention | `cont(MEDIUM) ≥ +0.2808 bp` (≥ 1/3 of +0.8423) |
| SC5 | both tails participate | `cont(MEDIUM, UP) > 0` **AND** `cont(MEDIUM, DOWN) > 0` |
| SC6 | regime ladder | `cont(MEDIUM) > cont(LOW)` **AND** `cont(MEDIUM) > cont(HIGH)` (no sign requirement on HIGH — §4.7) |
| SC7 | dependence-aware support | day-clustered 95% CI on `cont(MEDIUM)` excludes 0 **AND** P1 p ≤ 0.05 **AND** P2 p ≤ 0.05 |
| SC8 | multiplicity | BH-adjusted `q ≤ 0.05` at M = 2 |
| SC9 | year stability | positive in ≥ 2 of 3 years |
| SC10 | month stability | ≥ 18 of 32 months positive **AND** median month > 0 |
| SC11 | tail robustness | mean > 0 after removing top 1% **AND** after removing top 5% by signed `cont` |
| SC12 | ATR control | `cont(MEDIUM)` > 0 in ≥ 2 of 3 ATR terciles **AND** the ATR-tercile-stratified MEDIUM effect ≥ 50% of the unstratified effect **AND** not REDUNDANT-WITH-ATR by §4.13 |
| SC13 | time-of-day control | `cont(MEDIUM)` > 0 in ≥ 2 of 3 buckets (OVERNIGHT / RTH_AM / RTH_PM) |
| SC14 | shock-size control | within MEDIUM, the **smaller-\|shock\| half** must not be significantly negative (its 95% CI must not lie entirely below 0) |
| SC15 | integrity + power | minimum-n floors met; causal audit all YES; no overlap; no look-ahead; no parameter changed after execution began |

**If any required condition fails, it is not confirmed.** No exceptions.

### 4.13 The REDUNDANT-WITH-ATR rule (frozen, decided before results)

Compute continuation by ATR tercile **ignoring RVMR entirely**. Declare
**REDUNDANT WITH ATR** if **both**:

1. the ATR-stratified MEDIUM effect (stratum-size-weighted mean of the
   within-tercile MEDIUM effects) < 50% of the unstratified MEDIUM
   effect; **and**
2. `max over ATR terciles of the ATR-only continuation effect` ≥ the
   unstratified RVMR-MEDIUM effect.

Plain statement of intent, fixed in advance: **if ordinary volatility
state explains the continuation, RVMR gets no credit for it.**

Additional controls **reported, not gated** (declared now so they cannot
be introduced selectively later): continuation split by the sign of the
*preceding* block (recent momentum), by discovery-frozen terciles of the
prior 60-bar mean range, and by discovery-frozen terciles of the prior
60-bar mean volume. Each carries a pre-declared **flag** — "effect
concentrated in one stratum" — which is reported in the findings and
does not by itself change the verdict.

---

## 5. CANDIDATE 2 — MONDAY-RTH (SECONDARY PROMOTABLE)

### 5.1 Source

`scan2_run.py:357–377` (statistic S22 Monday decomposition), reported in
`ANOMALY_SCAN_V1_FINDINGS.md` §G.

### 5.2 Exact definition (every element frozen)

| element | frozen value / rule |
|---|---|
| Monday classification | `datetime.strptime(day[i], '%Y-%m-%d').weekday() == 0`, on the **calendar date of the ET close stamp** |
| timezone | ET wall clock as stamped (`STAMP_SHIFT = 0`); DST inherited, not corrected |
| RTH start | `mod ≥ 570` (09:30 close stamp) |
| RTH end | `mod ≤ 960` (16:00 close stamp) |
| return formula | sum of the contiguous 1m log returns of Monday bars with `570 ≤ mod ≤ 960`, one total per Monday |
| Sunday treatment | Sunday-dated bars (`weekday == 6`) are a **separate segment** and are excluded from MONDAY-RTH |
| overnight treatment | Monday `mod ≤ 569` is a **separate segment** and is excluded |
| holiday Mondays | simply absent; n falls. No imputation, no forward-fill, no manufactured bars |
| early closes | included as-is, unadjusted, exactly as in discovery |
| missing sessions | skipped |
| cost | none applied — this is an accrual statistic, not a strategy |
| cluster unit | the Monday itself (the day-clustered bootstrap reduces to a bootstrap over Monday totals) |

> **Precise window, stated honestly:** because a bar stamped 09:30 is the
> minute that *closes* at 09:30, its return measures 09:29→09:30. The
> accrual therefore runs from the **09:29 close to the 16:00 close**.
> That is what the frozen code computes; it transports unchanged.

The hypothesis is specifically **Monday RTH**. Not all-Monday, not
Sunday night, not Monday overnight, not Monday first hour, not
Monday × RVMR.

### 5.3 Companion segments (reported context, from the same frozen source)

| segment | n | discovery mean | 95% CI |
|---|---|---|---|
| SUN 18:00–24:00 | 231 | +1.0323 bp | [−5.0204, +6.9167] |
| MON 00:00–09:29 | 231 | −1.0632 bp | [−8.0767, +5.5052] |
| **MON RTH** | **231** | **+16.6296 bp** | **[+5.9804, +27.0853]** |

Neither overnight segment explains the effect — the discovery basis for
localising it to RTH.

### 5.4 Primary endpoint, control, and materiality — all chosen NOW

> **PRIMARY:** `E[Monday RTH return] > 0`, day-clustered 95% CI
> excluding 0.

This is the source-supported statistic — S22 computes exactly this and
computes no weekday contrast. The differential is therefore **not** the
primary.

> **REQUIRED CONTROL (gate MR9), declared now and not switchable:**
> `mean(Monday RTH) − mean(non-Monday RTH) > 0` — **sign gate**, with
> its CI reported. It exists so a generally rising market cannot pass as
> a Monday effect.

Non-Monday RTH totals use the identical construction over every
non-Monday exchange day. Discovery reference (computed by
`confirm_freeze.py`, disclosed as a control statistic not present in the
frozen source): Monday RTH +16.6296 bp vs non-Monday RTH +0.3694 bp,
**differential +16.2602 bp**.

> **MATERIALITY / RETENTION:** the holdout Monday RTH mean must be
> **≥ +5.5432 bp** (= 1/3 of +16.6296) **and** positive, **and** its
> day-clustered 95% CI must exclude 0.

### 5.5 Stability (frozen)

- **Years:** mean Monday RTH > 0 in **≥ 2 of 3** years {2024, 2025,
  2026-partial}. Individual-year significance not required. No year
  excluded.
- **Months:** > 0 in **≥ 17 of 32** months (a simple majority; ~4
  Mondays per month makes monthly cells noisy by construction).
  Quarterly means also reported.
- **Forbidden subdivisions**, declared now: no post-election Mondays, no
  FOMC Mondays, no earnings Mondays, no RVMR-HIGH Mondays, no
  holiday-adjacent Mondays, no any other post-hoc slice.

### 5.6 Inference and permutation nulls for MONDAY-RTH

Bootstrap over the Monday totals, 20,000 iterations, seed 20260825, 95%
percentile CI, p per §3.4. Two permutation nulls:

- **P3 — sign flip.** Multiply each Monday total by ±1 with probability
  ½. Required at p ≤ 0.05.
- **P4 — weekday-label permutation.** Among all holdout RTH sessions,
  randomly designate 138 as "Monday" and recompute the differential.
  Tests gate MR9's contrast. Reported; required at p ≤ 0.05 only for the
  differential, not for the primary.

### 5.7 Tail robustness and minimum n

- **Tails (MR8):** rank Mondays by **signed** RTH return; remove the top
  1% (1 Monday of 138) and recompute; remove the top 5% (7 Mondays) and
  recompute. **Gate: mean > 0 after both.** Also reported: mean, median,
  10%-trimmed mean, and the share of total accrual contributed by the
  top 5 Mondays. If the effect vanishes on trimming → **TAIL-DEPENDENT**.
- **Minimum n (MR2):** ≥ **120** Monday sessions (coverage shows 138).

### 5.8 THE NINE CONFIRMATION CONDITIONS (Step 10)

| # | condition | frozen threshold | maps to directive item |
|---|---|---|---|
| MR1 | holdout-only data | all Mondays dated ≥ 2024-01-01; no boundary straddle | 1 |
| MR2 | minimum n | ≥ 120 Monday sessions | — |
| MR3 | sign | mean Monday RTH > 0 | 2 |
| MR4 | retention | mean ≥ **+5.5432 bp** (≥ 1/3 of +16.6296) | 3 |
| MR5 | dependence-aware support | day-clustered 95% CI excludes 0 **AND** P3 p ≤ 0.05 | 4 |
| MR6 | multiplicity | BH `q ≤ 0.05` at M = 2 | 5 |
| MR7 | stability | > 0 in ≥ 2 of 3 years **AND** ≥ 17 of 32 months | 6 |
| MR8 | tail robustness | mean > 0 after removing top 1% **AND** top 5% by signed return | 7 |
| MR9 | definition integrity + control | RTH bounds 570–960 and the calendar/ET convention unchanged; no leakage; **AND** `mean(Mon RTH) − mean(non-Mon RTH) > 0` | 8, 9 |

---

## 6. NON-PROMOTABLE SECONDARY DIAGNOSTICS

These were discovered and recorded before the holdout, so they may be
evaluated. **None is in the M = 2 family. None can rescue a failed
primary. None creates a promotion slot.** Every reported figure carries
the label **SECONDARY / NON-PROMOTABLE**.

### 6.1 AC-FLIP

Estimator: `scan_run.py:201–208`, applied to the **state-filtered**
return list (`scan_run.py:217`).

> **Declared estimator artifact:** this pairs consecutive members of the
> *filtered* sequence, which are adjacent minutes only while the state
> persists. RVMR states flicker (S19 dwell median 1–2 min), so some
> pairs straddle gaps. It is replicated verbatim because a replication
> must re-measure what was found. An **adjacency-restricted** variant
> (both minutes adjacent *and* in the same state) is reported alongside,
> and cannot change any verdict.

Discovery anchors (recomputed exactly, matching the published table):

| slice | 1m n | AC1(1m) | 15m n | AC1(15m) |
|---|---|---|---|---|
| LOW | 1,187,450 | −0.028036 | 78,734 | +0.002265 |
| MEDIUM | 288,214 | +0.016644 | 18,570 | −0.005023 |
| HIGH | 95,744 | +0.023863 | 5,326 | −0.032083 |

Replication criterion: `AC1(1m|LOW) < 0 < AC1(1m|HIGH)`, plus
`AC1(15m|HIGH) < 0` as a further sub-check.
**Allowed conclusion if it replicates: "RVMR conditions return-memory
structure."  Not allowed: "directional edge."**

### 6.2 CLV-FLIP

`scan2_run.py:180–202`: `CLV = (2c − h − l)/(h − l)` on bars with
`h > l`; statistic = `corr(CLV_t, r_{t+1})` by state, pairs restricted to
adjacent minutes.

Discovery: LOW **−0.007007** (n 1,178,256) / MEDIUM **+0.008840**
(n 287,853) / HIGH **+0.014121** (n 95,624).

Replication criterion: negative in LOW, positive in HIGH. Treated only
as independent corroboration of RVMR-conditioned structure. **No
strategy implication. No multiplicity promotion.**

### 6.3 LEVERAGE-V

`scan2_run.py:326–334`: for each 15m block, `P(any RB[j] == 'HIGH' for
j in i1+1 … min(i1+30, N−1))` by frozen shock decile.

Discovery: d0 **0.6402**, d1 0.4257, d2 0.3228, d3 0.2608, d4 0.2374,
d5 0.2469, d6 0.2741, d7 0.3174, d8 0.3870, d9 **0.5562**.

Replication criterion: V-shape preserved — `P(d0)` and `P(d9)` both
exceed every middle decile `P(d3…d6)` — **and** the downside asymmetry
`P(d0) > P(d9)` holds. Allowed conclusion: *future activity-state
probability depends asymmetrically on the prior shock.* **Not:
directional trading edge.** (See §0.4(b) for the 2-block edge read.)

### 6.4 Cumulative-family clause (replaces the superseded document's)

The promotable family is `{SHOCK-CONT-MEDIUM, MONDAY-RTH}`, M = 2,
permanently for this study. If any **currently non-promotable**
statistic — AC-FLIP, CLV-FLIP, LEVERAGE-V — is ever proposed for
*promotion* in a future study on this same holdout, it enters a
cumulative family `M_cum ≥ 3` and takes its multiplicity correction
against that cumulative count. **The family may grow with each new
promotable test; it may never shrink**, and a failed candidate may never
be swapped out to make room for a fresh one.

### 6.5 STEP 4 — settled nulls that may NOT consume holdout multiplicity

Not tested, by rule: overnight drift, open-gap response, turn-of-month,
sub-60m VWAP reversion, Parkinson/close-close geometry, half-hour drift,
VR(2), the news-minute map, clock harmonics. These remain catalog
knowledge from the discovery window.

---

## 7. STEP 11 — STRATEGY PROHIBITION (binding)

This run computes **no** entries, stops, targets, EMA filters, VWAP
filters, shock-triggered stop losses, RVMR-MEDIUM trade simulation,
position sizing, or time exits — **even if SHOCK-CONT survives every
gate.**

The question is only: **is the conditional directional anomaly real?**

**STEP 12 — if and only if SHOCK-CONT passes the full frozen gate**, a
knowledge object `SHOCK-CONT-MEDIUM-CANDIDATE-V1` is frozen with status
**INDEPENDENTLY CONFIRMED CONDITIONAL DIRECTIONAL ANOMALY** — explicitly
**not** "profitable strategy", **not** "validated entry system", **not**
"live edge". Any strategy (`SHOCK-CONT-STRAT-V1`) requires its own,
later, separate preregistration.

**STEP 13 — RVMR certificate consequence.** If SHOCK-CONT-MEDIUM
confirms, RVMR-V1 gains **one documentation clause**: *"RVMR condition
modulates the response of NQ to large directional shocks."* If AC-FLIP
also independently replicates, a second clause may be added: *"RVMR
conditions short-horizon return-memory structure."*

Forbidden phrasing, now and later: **"RVMR predicts direction."** The
effect is conditional on a specific prior event. And in every case:
`rvmr_spec.py`, `rvmr_run.py`, the RVMR forward logger, the prospective
ledgers, OFH13/OFH14 and every NinjaTrader host remain **byte-for-byte
unmodified**. Confirmation changes a sentence in a document, not a line
of frozen code, and authorizes no live trading.

---

## 8. STEP 15 — PROVENANCE / CAUSAL AUDIT

| FIELD | SOURCE | AVAILABLE TIME | OUTCOME TIME | CAUSAL? |
|---|---|---|---|---|
| 1m log return `r_i` | `c[i]`, `c[i−1]` | close of bar `i` | — | **YES** |
| shock block return `rv` | bars `i0…i1` | close of bar `i1` | — | **YES** |
| RVMR RANGE score at `j0` | `trailing_ratio(h−l)` over bars `j0−1440 … j0−1` = through `i1` | close of bar `i1` | forward block `j0…j1` | **YES** |
| RVMR bucket at `j0` | thresholds 1.270 / 2.335, fixed 2019 | close of bar `i1` | forward block | **YES** |
| decile cutpoints | discovery pair set ≤ 2023-12-31 | frozen 2026-08-25, before holdout | holdout events | **YES** |
| decile label of an event | shock return vs frozen cutpoints | close of bar `i1` | forward block | **YES** |
| shock direction `sgn` | sign of `rv` | close of bar `i1` | forward block | **YES** |
| forward return `rf` | bars `j0…j1`, all strictly after `i1` | close of bar `j1` | itself | **YES** |
| `atr20(i1)` (control C1) | SMA20 of TR over bars `i1−19 … i1` | close of bar `i1` | forward block | **YES** |
| ATR tercile cutpoints | discovery extreme set | frozen before holdout | holdout events | **YES** |
| time-of-day bucket | `mod[j0]` | known from the clock | forward block | **YES** |
| \|shock\| median split | discovery extreme set | frozen before holdout | holdout events | **YES** |
| Monday label | ET calendar date of the close stamp | known from the clock | Monday RTH accrual | **YES** |
| Monday RTH bounds 570–960 | frozen `V4SessionMap` convention | fixed 2019 | Monday accrual | **YES** |
| non-Monday RTH control pool | same construction, other weekdays | same session, disjoint days | — | **YES** |
| AC-FLIP / CLV / LEVERAGE-V definitions | Wave-1/Wave-2 frozen code | frozen before holdout | holdout series | **YES** |
| 15m block boundaries | index arithmetic on contiguous minutes | at block close | — | **YES** |

**Every row is YES.** Additional mechanical checks required at execution
and reported in the findings:

1. RVMR state is never labelled using future movement — the 1440-bar
   window provably excludes its own bar (verified EXACT at five probes,
   §3.1).
2. Shock classification uses no future bar — the cutpoints are frozen
   constants and `rv` closes at `i1`.
3. The forward window begins strictly after the shock window: `j0 = i1 +
   1` is enforced, and blocks never share a bar.
4. No overlapping discovery/holdout rows: the windows are disjoint and
   separated by a 73-hour unbridged gap (§2).
5. 15m bars are correctly timestamped: block boundaries printed and
   verified (§3.3).
6. Secondary diagnostics are frozen in §6 before execution.
7. No 2024+ outcome read prior to this freeze (§0.2).

---

## 9. STEP 8 — ALLOWED VERDICTS (exhaustive)

**SHOCK-CONT-MEDIUM:** CONFIRMED · PARTIALLY CONFIRMED · FAILED HOLDOUT ·
TAIL-DEPENDENT · REDUNDANT WITH ATR · INSUFFICIENT DATA · VOID — SPEC ERROR

**MONDAY-RTH:** CONFIRMED · PARTIALLY CONFIRMED · FAILED HOLDOUT ·
TAIL-DEPENDENT · INSUFFICIENT DATA · VOID — SPEC ERROR

**AC-FLIP / CLV-FLIP / LEVERAGE-V:** REPLICATED · PARTIAL ·
FAILED REPLICATION · INSUFFICIENT DATA · VOID

Decision rules, frozen so the verdict is mechanical:

- **CONFIRMED** — every condition passes (SC1–SC15, or MR1–MR9).
- **PARTIALLY CONFIRMED** — all of sign, dependence-aware CI,
  permutation and BH pass (SC3/SC7/SC8, or MR3/MR5/MR6), but ≥ 1
  retention, stability, control or tail condition fails. Confers **no**
  promotion and **no** certificate clause.
- **TAIL-DEPENDENT** — the effect is positive and supported on the full
  sample but fails SC11 / MR8. Takes precedence over PARTIALLY
  CONFIRMED when tails are the failure.
- **REDUNDANT WITH ATR** — §4.13 triggers. Takes precedence over
  CONFIRMED and PARTIALLY CONFIRMED: RVMR is not credited for what
  volatility state already explains.
- **FAILED HOLDOUT** — any of sign, CI, permutation or BH fails.
- **INSUFFICIENT DATA** — a minimum-n floor fails (§4.11 / §5.7).
- **VOID — SPEC ERROR** — the test could not be executed as written
  because of a defect in *this* document, with a written diagnosis.

A failed candidate is **destroyed, not retuned**. No threshold in this
document may be relaxed after any holdout number is seen. No hypothesis
may be re-run under a new name, at a new decile, at a new horizon, or on
a new sub-window. **M stays 2 regardless of outcome.**

---

## 10. EXECUTION RULES (binding on the directive that opens the holdout)

1. **One run.** The engine executes once. A crash may be fixed, with the
   diff disclosed, and the fix may not touch a threshold, a cutpoint or
   a definition.
2. **No retuning** of anything in §§3–6 after any holdout number exists.
3. **No new hypotheses.** No statistic outside this document may be
   computed on the holdout in this study.
4. **Report every gate**, passed and failed, by its number.
5. **Report discovery and holdout separately**, with the retention ratio.
   Never a pooled significance claim.
6. **Report the honest verdict**, including "the strongest economic
   finding of the scan did not replicate" if that is what the data says.
7. The engine **submits no orders** and modifies nothing frozen.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
