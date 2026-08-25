# RVMR-STRUCTURE-TO-PREDICTION-V1 — PREREGISTRATION

**M = 2.  H1 = MEMORY-PRED-V1.  H2 = HIGH-ARRIVAL-UTILITY-V1.**

**Status: PREREGISTRATION ONLY.** No predictive result has been
computed for either hypothesis. This document is frozen, hashed,
committed and pushed first. A later directive may execute it.

Offline research only. No orders. Nothing frozen is modified.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 0. CRITICAL EPISTEMIC STATUS — READ BEFORE ANY NUMBER IS BELIEVED

> **The entire 2019-07 → 2026-08 history is EXPOSED for these two new
> hypotheses. No part of it is a clean out-of-sample test.**

Why, precisely: AC-FLIP and LEVERAGE-V were *discovered* on ≤ 2023-12-31
and their *replication was inspected* on 2024-01-01 → 2026-08-17
(ANOMALY-CONFIRM-V1, commit `9ae76aae…`) **before** the two predictive
hypotheses below were written. The selection of these two structures —
out of the sixteen scanned statistics — used the holdout outcome. That
is legitimate for hypothesis *generation* and fatal for hypothesis
*confirmation* on the same data.

Historical testing here may be used for:

- mechanism development
- robustness and destruction
- cross-year stability
- effect sizing

and **may NOT** be used for independent confirmation, however many gates
are passed. A hypothesis that passes every gate in §7 and §8 earns
exactly one label: **DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE**.

True confirmation requires NQ data generated **after** this freeze. The
exact prospective start timestamp is fixed in §11 and may not be
backdated.

### 0.1 Cumulative multiplicity — the never-shrink clause, honoured

`ANOMALY_CONFIRM_V1_PREREGISTRATION.md` §6.4 states that if AC-FLIP,
CLV-FLIP or LEVERAGE-V is ever proposed for **promotion**, it enters a
cumulative family `M_cum ≥ 3`, and "the family may grow with each new
promotable test; it may never shrink."

This study does exactly that. Bookkeeping, recorded now:

| # | promotable test on 2019–2026 | status |
|---|---|---|
| 1 | SHOCK-CONT-MEDIUM | spent — FAILED HOLDOUT |
| 2 | MONDAY-RTH | spent — FAILED HOLDOUT |
| 3 | **MEMORY-PRED-V1** (this study, H1) | new |
| 4 | **HIGH-ARRIVAL-UTILITY-V1** (this study, H2) | new |

**M_binding = 2** for this study's BH correction, as directed.
**M_cum = 4** is reported alongside as a **disclosed, non-binding**
family-size sensitivity. It may not change a verdict; it exists so no
future reader mistakes the corrected family for the full set of
promotable tests this programme has run on this data.

### 0.2 Absolute protection

Not read for modification, not written, not touched: `rvmr_spec.py`,
`rvmr_run.py`, the RVMR forward logger, `OFH13_PROSPECTIVE_V1`,
`OFH14_PROSPECTIVE_V1`, every prospective ledger, every NinjaTrader
prospective host. The execution engine submits no orders and simulates
no trade.

---

## 1. STEP 1 — EXACT SURVIVOR DEFINITIONS (read from source, not prose)

### 1.1 Provenance

| artifact | sha256 | commit |
|---|---|---|
| `analysis/anomaly/scan_run.py` | `03d65b1dd6f5fb8995373d188ea2576c9956fa20ab8928d0e5171548a2c92e89` | `03f0e985505a06c4808bf94b34e4d241b57e6a33` |
| `analysis/anomaly/scan2_run.py` | `6c52693ff4a44fcd7090e9bfd82869196572822ef137547b4e42b9a47f9fd747` | `70c373568e636a911f6a5f43693263a058053f82` |
| `analysis/anomaly/confirm_run.py` | `5ae5e3d4645b2452cbfb1723ef731819c68cc07f0cb92e19f206cc8be22623b8` | `9ae76aae16ff33fadb10e647f30bcfad3f98ef75` |
| `analysis/anomaly/confirm_freeze.py` | `507c63687985b94feb1eb720ddd058ed983fc07fd9ce2781a85ec40087387f80` | `fd2311af1cd7e4071e6105a1ebf58f4089796cce` |
| `docs/ANOMALY_CONFIRM_V1_PREREGISTRATION.md` | `813f03e274059bf664b0a283291899d174e005f9b794afbe772f7aae84136aec` | `fd2311af1cd7e4071e6105a1ebf58f4089796cce` |
| `docs/ANOMALY_CONFIRM_V1_FINDINGS.md` | `807b5c8a5a0df9c177e303d3e683d382efcf8862ebbbf92d0eb344923ef7ff8f` | `9ae76aae16ff33fadb10e647f30bcfad3f98ef75` |
| `docs/ANOMALY_SCAN_V1_FINDINGS.md` | `79e0355cdc996f5bf7a278c3265140c05ae5997727fd5d7b336890ccd1d0ef22` | `70c373568e636a911f6a5f43693263a058053f82` |
| `analysis/rvmr/rvmr_spec.py` | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` | `84933d28c71c07e149e7728a96b4af7d30ea1685` |
| `analysis/rvmr/rvmr_run.py` | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` | `9d14dfaa9be90b5a3ee407690b543dcedbb27bc0` |

### 1.2 Shared substrate (unchanged, transported)

- **Loader**: `rvmr_run.load_bars()`, `STAMP_SHIFT = 0`, close-stamped
  ET wall clock, 2,503,622 rows, 2019-07-04 18:25 → 2026-08-17 15:16.
- **Return**: `r_i = log(c[i]/c[i-1])`, admitted only when
  `em[i] − em[i-1] == 1` and `c[i-1] > 0`. Gaps skipped, never bridged.
  No bar interpolated, forward-filled, or split to a lower timeframe.
- **RVMR RANGE state**: `RS.trailing_ratio(high − low, W = 1440)` then
  `RS.bucket()` — `LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH`. The window is
  1440 **bars** ending at `i−1` and **excludes bar `i`**. Verified
  EXACT at five probes during ANOMALY-CONFIRM-V1.
  **Availability: `RB[i]` is known at the close of bar `i−1`.**
- **VOLUME regime is not used anywhere in this study.**

### 1.3 AC-FLIP — exact definition and replication result

**Estimator** (`scan_run.py:201-208`), applied to the *state-filtered*
return list (`scan_run.py:216-219`):

```python
def ac(rs, lag):
    n = len(rs)
    if n < lag + 100: return float('nan')
    m = sum(rs) / n
    num = sum((rs[i]-m)*(rs[i-lag]-m) for i in range(lag, n))
    den = sum((x-m)**2 for x in rs)
    return num/den if den > 0 else float('nan')
rs = [r for i, r in rets if RB[i] == st]
```

**Adjacency-restricted variant** (`confirm_run.py:862-888`) — pairs
retained only when `i − prev_i == 1` **and** `RB[i] == RB[prev_i] == st`.
Because a return at array index `i` already requires `em[i]−em[i−1]==1`,
array adjacency here is exactly minute adjacency: the pair is
`(r_{i−1}, r_i)`, consecutive minute returns, with **both** bars in
state `st`.

| scale | slice | discovery | holdout | replication |
|---|---|---|---|---|
| 1m | LOW | −0.028036 | **−0.012551** (n 706,196) | sign held |
| 1m | MEDIUM | +0.016644 | +0.000460 (n 165,327) | collapsed |
| 1m | HIGH | +0.023863 | **+0.009395** (n 54,225) | sign held |
| 1m adj-restricted | LOW / MED / HIGH | — | −0.013145 / −0.002058 / **+0.007271** | flip survives |
| 15m | LOW | +0.002265 | −0.002351 | sign flipped |
| 15m | MEDIUM | −0.005023 | +0.024989 | sign flipped |
| 15m | HIGH | −0.032083 | **−0.067115** (n 2,933) | sign held, ~2× |

Frozen criterion `AC1(1m|LOW) < 0 < AC1(1m|HIGH)` **held**; sub-check
`AC1(15m|HIGH) < 0` **held**. Verdict recorded: **REPLICATED**
(non-promotable). Magnitude retention ≈ 45% (LOW) / 39% (HIGH).

### 1.4 LEVERAGE-V — exact definition and replication result

**Statistic** (`scan2_run.py:326-334`):

```python
for a in range(len(r15)):
    i0, i1, rv_, dd = r15[a]
    fut = any(RB[j] == 'HIGH' for j in range(i1+1, min(i1+31, N)))
    rbmap.setdefault(dec_of(rv_), []).append(1 if fut else 0)
```

- **Prior-return object**: the non-overlapping 15m block
  (`scan2_run.py:78-89`) — 15 consecutive contiguous 1m returns with
  index span exactly 14, grid anchored to each calendar day's first
  valid contiguous return (**not** a `:00/:15/:30/:45` clock grid; 6
  distinct phases were measured across the 820 holdout days).
- **Bins**: `dec_of()` against the nine **discovery-frozen static
  cutpoints** (§2.2). Not trailing, not annual, not recalibrated.
- **Horizon**: the 30 bars strictly after the block's last bar `i1`.
- **Availability**: the bin is known at the close of `i1`; the outcome
  spans `i1+1 … i1+30`.

| dec | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
|---|---|---|---|---|---|---|---|---|---|---|
| **discovery P** | **0.6402** | 0.4257 | 0.3228 | 0.2608 | 0.2374 | 0.2469 | 0.2741 | 0.3174 | 0.3870 | **0.5562** |
| holdout P | 0.6342 | 0.4045 | 0.2947 | 0.2302 | 0.2111 | 0.2119 | 0.2261 | 0.2698 | 0.3392 | 0.5553 |

V-shape held; downside asymmetry `P(d0) > P(d9)` held; every decile
within 0.03 of its discovery value across 2.6 unseen years. Verdict
recorded: **REPLICATED** (non-promotable).

**Known lineage blemish, restated:** `min(i1+31, N)` uses the *full*
series length, so 2 of 102,706 discovery blocks could scan up to 30 bars
past the discovery boundary, reading a *range* (never a return or an
outcome). Disclosed in ANOMALY-CONFIRM §0.4(b); the same expression is
used here so all eras are treated identically.

---

## 2. FROZEN CONSTANTS TRANSPORTED INTO THIS STUDY

### 2.1 Nothing is recalibrated

No decile is re-quantiled, no RVMR threshold is re-fit, no LEVERAGE-V
mapping is re-estimated from each event's own future.

### 2.2 The nine shock cutpoints (from `CONFIRM_FREEZE_OUTPUT.txt`)

```
-0.0011017009  -0.0005520548  -0.0002889478  -0.0001179931
+0.0000168159  +0.0001601759  +0.0003325537  +0.0005951824
+0.0011091640
```

Published to 10 decimals; reproduction tolerance is **5e-11** (half a
unit in the last published place) — the lesson recorded in
ANOMALY-CONFIRM §1.1, applied from the start here.

### 2.3 The frozen HIGH-arrival propensity mapping (H2)

`propensity(bin) = the DISCOVERY-window P from §1.4`, a fixed lookup of
ten constants. **It is never re-estimated, at any event, in any era.**

Propensity groups, frozen now with round cutpoints at **0.30** and
**0.40**, chosen before any H2 outcome exists and giving roughly
equal-mass groups:

| group | rule | bins | discovery P |
|---|---|---|---|
| **P-LOW** | P < 0.30 | d3, d4, d5, d6 | 0.2608, 0.2374, 0.2469, 0.2741 |
| **P-MID** | 0.30 ≤ P < 0.40 | d2, d7, d8 | 0.3228, 0.3174, 0.3870 |
| **P-HIGH** | P ≥ 0.40 | d1, d9, d0 | 0.4257, 0.5562, 0.6402 |

### 2.4 Frozen |shock| bands (H2 asymmetry matching, no new constants)

The absolute values of the nine cutpoints, sorted, give nine edges and
ten bands:

```
0.0000168159  0.0001179931  0.0001601759  0.0002889478  0.0003325537
0.0005520548  0.0005951824  0.0011017009  0.0011091640
```

### 2.5 Frozen time-of-day buckets

`OVERNIGHT` = `mod ≥ 1081 or mod ≤ 569`; `RTH_AM` = `570 ≤ mod ≤ 750`;
`RTH_PM` = `751 ≤ mod ≤ 960`.

### 2.6 Cutpoints computed at execution (declared as such, never tuned)

Where a control needs a partition that no frozen constant supplies, the
cutpoints are **terciles of the full eligible population, computed once
at execution, on the pooled 2019–2026 data, with no search and no
alternatives tried**. This is an in-sample partition and is labelled as
such wherever reported. It applies to: `atrRel` terciles, `|r[t]|`
terciles/quantiles, prior-60-bar mean range terciles, prior-60-bar mean
volume terciles. **No threshold may be adjusted after any outcome is
seen.**

---

## 3. FAMILY SIZE

> **M = 2.** H1 = MEMORY-PRED-V1, H2 = HIGH-ARRIVAL-UTILITY-V1.
>
> They are evaluated **independently**. **No combined model is built in
> this study** — not shock + predicted HIGH arrival, not actual HIGH
> arrival + AC-FLIP momentum, not any state machine. Forbidden even if
> both survive (§10).
>
> M remains 2 if either becomes VOID, FAILED or UNSTABLE.

---

## 4. H1 — MEMORY-PRED-V1

### 4.1 Purpose and scope limit

Translate the replicated AC-FLIP structure into the most direct forward
prediction it implies, and nothing else. **No EMA, no VWAP, no vector
classification, no order flow, no 4H trend, no candlestick pattern, no
chart pattern of any kind enters this hypothesis.** The only inputs are
the completed 1m return and the causally available RVMR RANGE state.

### 4.2 Event and eligibility (frozen)

At decision time `t` (the close of bar `t`), the forecaster knows
`r[t]`, `RB[t]` and `RB[t+1]` — the last because `trailing_ratio` at
index `t+1` uses bars `t+1−1440 … t`, which ends at `t`. Both are
therefore legitimately in the conditioning set.

An event exists at `t` iff:

1. `r[t]` and `r[t+1]` both exist under §1.2 (so `em[t+1] − em[t] == 1`,
   `em[t] − em[t−1] == 1`, `c[t−1], c[t], c[t+1] > 0`);
2. `RB[t]` and `RB[t+1]` are both non-`None`;
3. `r[t] ≠ 0` (**zero-return handling, frozen**: a zero predictor has no
   sign, so the event is **excluded**);
4. no restriction is placed on `r[t+1]`; if `r[t+1] == 0` then
   `memoryReturn = 0` and the event **is retained** for the mean
   endpoint, and **excluded** from the sign-probability endpoint only,
   where its sign is undefined.

### 4.3 Outcome

```
memoryReturn = sign(r[t]) × r[t+1]
```

`> 0` = continuation, `< 0` = reversal.

### 4.4 State conditioning — PRIMARY and SECONDARY, both frozen now

- **PRIMARY — both-bars-same-state.** An event is assigned to state
  `st` iff `RB[t] == RB[t+1] == st`. This is the *exact* object that
  replicated on the holdout (the adjacency-restricted AC1,
  `confirm_run.py:862-888`) — a 1:1 mapping onto the survivor, with no
  reconstruction.
- **SECONDARY — forward-state-only.** Assign by `RB[t+1]` alone (the
  broader, more operational conditioning, and the same convention
  SHOCK-CONT used for `RB[j0]`). Reported; **cannot rescue** a failed
  primary and cannot overturn a passing one.

### 4.5 Primary structural claim (one decisive scalar)

> **Δ = E[memoryReturn | HIGH] − E[memoryReturn | LOW] > 0**

MEDIUM is reported but is not part of the primary — the holdout MEDIUM
AC1 collapsed to +0.0005, and requiring monotonicity would be a
post-hoc tightening.

**Additionally required** (the directive's "LOW should show greater
reversal tendency", and the one leg that held its sign in both eras):

> **E[memoryReturn | LOW] < 0**

Profitability is **not** required anywhere in H1.

### 4.6 Sign-probability endpoint (required secondary)

`P(sign(r[t+1]) == sign(r[t]) | state)` for LOW, MEDIUM, HIGH. Report
continuation probability, reversal probability, deviation from 0.50, and
the HIGH − LOW difference in continuation probability, each with
day-clustered CIs. **Required to agree in sign with the primary Δ.**
**No probability threshold is optimised. No threshold is searched.**

### 4.7 Magnitude robustness — a fixed set of three, frozen now

1. all eligible returns (**PRIMARY population**)
2. top 50% by `|r[t]|`
3. top 20% by `|r[t]|`

Cutpoints per §2.6. **These are robustness only and cannot rescue
failure of the full-population primary.** No top-10%, top-5%, top-2% or
any other sweep exists in this study.

### 4.8 15m secondary (required secondary, cannot rescue)

Using the exact replicated 15m construction (§1.4 block definition,
state = `RB[block start]`, as in `scan_run.py:220-237`): does HIGH show
greater next-block **reversal** than LOW and MEDIUM?

Endpoint: `E[memoryReturn15 | HIGH] < E[memoryReturn15 | LOW]` where
`memoryReturn15 = sign(block_k) × block_{k+1}` over consecutive blocks
with `start_{k+1} − end_k == 1`. **No 5m, 10m or 30m variant is created.**

### 4.9 Controls (§2.6 partitions; the matched contrast is a gate)

Controlled for: `atrRel(t) = atr20(t)/c[t]`; time-of-day bucket of
`t+1`; `|r[t]|`; recent momentum (`sign(r[t−1])`, when it exists); year;
and the **continuous** RVMR RANGE score at `t+1`, not merely its label.

**Matched Δ (direct standardisation):** stratify by
`ATR tercile × |r[t]| tercile × time bucket` = 27 cells. Within each
cell compute `Δ_cell = mean(HIGH) − mean(LOW)`. Combine as

```
Δ_matched = Σ_cell w_cell · Δ_cell / Σ_cell w_cell ,
w_cell = number of (HIGH ∪ LOW) events in that cell
```

> **Defect note, learned the hard way.** In ANOMALY-CONFIRM §4.13 I
> wrote a "stratum-size-weighted" rule that, weighted by the subgroup's
> own sizes, was algebraically identical to the unstratified statistic
> and could never fire. The weighting above is a **common** weight
> applied to a **difference of two means**, so it is genuinely different
> from the raw Δ (which weights HIGH by HIGH's covariate distribution
> and LOW by LOW's). Both `Δ_raw` and `Δ_matched` are reported.

Supplementary (reported, not gated): OLS of `memoryReturn` on
`[HIGH dummy, MEDIUM dummy, |r[t]|, atrRel, RVMR score, time dummies,
sign(r[t−1])]`, day-clustered, using the per-day sufficient-statistics
bootstrap of `analysis/rvmr_val/track_b.py` (normal equations are
additive over observations, so whole-day resampling accumulates
precomputed per-day `X'X` and `X'y` blocks — identical estimator,
tractable computation).

### 4.10 Economic reporting (never a gate)

Report Δ and each state's mean in **bp**, in **NQ points** at the mean
close of the eligible events, and as a **multiple of the frozen 0.87-pt
round-turn cost**.

> **Stated in advance so the result cannot be spun:** a 1m
> return-memory effect is expected to be one to two orders of magnitude
> below cost. Discovery already put the predictable 1m component near
> 0.2 points against 0.87. If H1 is statistically real and below cost,
> the correct label is **REPLICATED PREDICTIVE STRUCTURE — SUB-COST**,
> and that is a legitimate, useful, non-tradeable result. **Being
> sub-cost is not a failure and must not be reported as one; being
> above cost is not a strategy and must not be reported as one.**

### 4.11 Minimum n (precondition — failure ⇒ INSUFFICIENT DATA, not FAILED)

Primary population: LOW ≥ **500,000**, MEDIUM ≥ **80,000**,
HIGH ≥ **25,000** events.

### 4.12 THE TEN H1 GATES

| # | condition | frozen threshold |
|---|---|---|
| **MP1** | adjacency exactness | every event has `em[t+1]−em[t] == 1` and `em[t]−em[t−1] == 1`; count of violations = **0** |
| **MP2** | no leakage | every conditioning input available at close of `t`: `RB` windows end at `t` or earlier (verified by probe), `atr20(t)` ends at `t`, no forward bar enters any predictor; violations = **0** |
| **MP3** | ordering | `Δ = E[mem\|HIGH] − E[mem\|LOW] > 0` **AND** `E[mem\|LOW] < 0` |
| **MP4** | dependence-aware CI | day-clustered 95% CI on `Δ` excludes 0 (20,000 iters, seed 20260825) |
| **MP5** | corrected support | BH `q ≤ 0.05` at M = 2 **AND** within-day state-shuffle permutation `p ≤ 0.05` |
| **MP6** | year stability | `Δ > 0` in **≥ 6 of 8** years {2019p, 2020, 2021, 2022, 2023, 2024, 2025, 2026p}; **no year deleted** |
| **MP7** | time-of-day stability | `Δ > 0` in **≥ 2 of 3** buckets |
| **MP8** | ATR-matched survival | `Δ_matched > 0` **AND** `Δ_matched ≥ 0.50 × Δ_raw` |
| **MP9** | magnitude-matched survival | `Δ > 0` in the top-50% and top-20% `\|r[t]\|` subsets |
| **MP10** | no tail artifact | `Δ > 0` after removing the top 1% **and** the top 5% of events by `\|memoryReturn\|` |

---

## 5. H2 — HIGH-ARRIVAL-UTILITY-V1

### 5.1 Purpose

LEVERAGE-V already established that prior-return magnitude predicts
RVMR-HIGH arrival. **This study does not re-test that.** It asks the
next question: does the *forecast* of HIGH arrival carry information
about future market **activity**, available **before** the HIGH state
arrives, beyond what the current shock already tells you?

Direction-free throughout. No directional claim may be derived from H2.

### 5.2 Event and eligibility (frozen)

For each 15m block (§1.4 construction) ending at bar `i1`:

1. the block's decile bin under the **frozen** cutpoints (§2.2);
2. the frozen `propensity(bin)` and its group (§2.3);
3. eligibility requires the full forward window to exist and be
   contiguous: `em[i1+30] − em[i1] == 30`;
4. `RB[i1]`, `atr20(i1)` and `c[i1]` available (they are, by §1.2).

Everything in the conditioning set is known at the close of `i1`.

### 5.3 Primary outcome — ONE endpoint, source-consistent

Over the **same 30 bars** LEVERAGE-V forecasts into:

```
move30 = ( max(high[i1+1 … i1+30]) − min(low[i1+1 … i1+30]) ) / c[i1]
```

reported in bp. Realised range, normalised by the decision-time price so
it is comparable across a 9,950 → 24,000 price history.

**Not normalised by ATR** — ATR is a control (§5.5) and normalising by
it would silently absorb the control.

**Secondaries** (reported, non-deciding): `|Σ r over the 30 bars|`;
actual HIGH arrival within 30m (the LEVERAGE-V object itself).

### 5.4 Primary claim — monotonicity preferred over one cell

> **E[move30 | P-LOW] < E[move30 | P-MID] < E[move30 | P-HIGH]**

with the decisive scalar being the contrast
`C = E[move30 | P-HIGH] − E[move30 | P-LOW]`. Full monotonicity is a
gate (HA2); a single significant cell does not substitute for it.

### 5.5 THE INCREMENTAL-VALUE TEST — the crux of H2

**The identification problem, stated honestly and in advance:** the
frozen propensity is very nearly a deterministic function of the shock
itself — `propensity ≈ f(|shock|, sign(shock))`, since the bins are
quantiles of the signed shock. A large current move already predicts
future volatility. So an "incremental value" test against a *linear*
control for `|shock|` would mostly be measuring **functional form**, not
new information, and passing it would prove very little.

Two nested day-clustered OLS baselines are therefore frozen, and **the
strict one is binding**:

- **B1 (reported only)** — `move30 ~ |shock| + atrRel(i1) + RVMR score at
  i1 + time dummies + prior-60-bar mean relative range + log prior-60-bar
  mean volume`
- **B2 (BINDING)** — B1 **plus** `|shock|²`, a **down-shock indicator**,
  and `down × |shock|`. This is a flexible function of the shock itself,
  so anything the propensity adds on top of B2 is genuinely not "the
  size and sign of the current move".

Augmented model `A = B2 + propensity(bin)` as a single scalar covariate.

> **HA6 (binding):** the coefficient on `propensity` in model A is
> **positive** with a day-clustered 95% CI **excluding 0**, and
> `ΔR² = R²(A) − R²(B2) > 0`.

If the propensity adds nothing beyond B2, the honest verdict is
**STATE-ARRIVAL LAW REAL BUT FORECAST-REDUNDANT** — and that is a real,
publishable result, not a failure to be argued around.

Matched reporting alongside the regression: the contrast `C` recomputed
within each `atrRel` tercile and within each `|shock|` tercile,
plus a direct-standardised `C_matched` using the §4.9 common-weight
construction over `ATR tercile × |shock| tercile × time bucket`.

### 5.6 Downside asymmetry (SECONDARY — declared, never gated)

Within each of the ten frozen `|shock|` bands (§2.4), compare

```
P(HIGH arrival within 30m | negative shock)  vs  P(… | positive shock)
```

and then whether `move30` also differs at matched `|shock|`. Exact
matching on frozen constants, requiring no new cutpoint.

**No directional trade, signal, or claim may be derived from this.**

### 5.7 Calibration (reported; one gate)

The frozen propensity is a probability forecast, so it is scored as one.
Using the 3 frozen groups (primary reliability structure) and the 10
frozen deciles (finer report):

- predicted probability (frozen discovery `P`) vs observed HIGH-arrival
  frequency, per bin;
- **Brier score** `mean((p_bin − y)²)`, `y = 1` if HIGH arrived within
  30m;
- **calibration error** `mean |p_group − observed_group|` over the 3
  groups;
- reference: the Brier score of the constant base-rate forecast
  (observed overall HIGH-arrival frequency).

**No flexible or ML calibrator is fitted.** No isotonic regression, no
Platt scaling, no learned recalibration of any kind.

### 5.8 Minimum n (precondition ⇒ INSUFFICIENT DATA)

Total eligible blocks ≥ **100,000**; each propensity group ≥ **20,000**.

### 5.9 THE TEN H2 GATES

| # | condition | frozen threshold |
|---|---|---|
| **HA1** | no leakage | mapping is the frozen ten-constant lookup, never re-estimated; all predictors known at close of `i1`; forward window strictly `i1+1 … i1+30`; violations = **0** |
| **HA2** | monotone ordering | `E[move30\|P-LOW] < E[move30\|P-MID] < E[move30\|P-HIGH]` |
| **HA3** | dependence-aware CI | day-clustered 95% CI on `C` excludes 0 (20,000 iters, seed 20260825) |
| **HA4** | corrected support | BH `q ≤ 0.05` at M = 2 **AND** within-day group-shuffle permutation `p ≤ 0.05` |
| **HA5** | ATR control | ordering `P-LOW < P-HIGH` holds in **≥ 2 of 3** ATR terciles **AND** `C_matched ≥ 0.50 × C_raw` |
| **HA6** | **current-\|shock\| control (BINDING)** | propensity coefficient in `A = B2 + propensity` positive, day-clustered 95% CI excludes 0, and `ΔR²(A vs B2) > 0` |
| **HA7** | time-of-day control | `C > 0` in **≥ 2 of 3** buckets |
| **HA8** | calibration | `\|observed − predicted\| ≤ 0.10` in **each** of the 3 frozen groups **AND** Brier score ≤ that of the constant base-rate forecast |
| **HA9** | year stability | `C > 0` in **≥ 6 of 8** years; **no year deleted** |
| **HA10** | tail robustness | `C > 0` after removing the top 1% **and** the top 5% of events by `move30` |

---

## 6. INFERENCE (shared, frozen)

- **Cluster unit: the exchange day.** H1 clusters on `day[t+1]`; H2 on
  `day[i1+1]`. A minute or a block is never an independent trial.
- **Day-clustered percentile bootstrap**, whole days resampled with
  replacement, **20,000 iterations**, **seed 20260825**, **95%** CI.
- **Bootstrap p:** `p = 2 × min(#{b ≤ 0}, #{b ≥ 0}) / B`, floored at
  `1/(B+1)`. This is the p carried into BH.
- **Permutation nulls**, 20,000 iterations, seed 20260825, two-sided,
  **required at p ≤ 0.05** as corroboration, never as a substitute:
  - **H1** — within-day shuffle of state labels among that day's
    eligible events, outcomes left in place. Preserves each day's state
    composition and outcome distribution; destroys only the link.
  - **H2** — within-day shuffle of propensity-group labels, identically
    constructed.
- **OLS bootstrap** uses the per-day sufficient-statistics method cited
  in §4.9 (mathematically identical estimator).
- **Multiplicity:** BH at **M = 2** (binding); BH at **M_cum = 4**
  reported as a **non-binding** sensitivity (§0.1) that may not change a
  verdict.
- **No minute-level iid standard error is a deciding statistic anywhere.**
- No ML. No parameter sweeps. No retuning. One execution run.

## 6.1 Year robustness (development only)

Report every year separately: **2019** (partial, from 2019-07-04),
2020, 2021, 2022, 2023, 2024, 2025, **2026** (partial, to 2026-08-17).
**No year is deleted, excluded, or labelled out-of-sample.** Later years
are *not* OOS for these hypotheses (§0).

## 6.2 Month robustness

For each hypothesis: positive months, negative months, median month,
worst month, best month, across all ~86 months. **No month selection.**

## 6.3 Rolling-origin diagnostic — INTERNAL TEMPORAL VALIDATION

Optional and, if run, reported under that name only. Expanding-origin by
year: report the statistic computed on each year with origins advancing
forward. **This is not independent OOS confirmation and may never be
described as such.** All historical outcomes are epistemically exposed.

## 6.4 Tail destruction

Frozen for both hypotheses: remove the top 1% and the top 5% of events
and recompute. **H1** trims by `|memoryReturn|` — the question is
whether a handful of giant next-minute moves manufacture the memory
effect. **H2** trims by `move30` — the question is whether a handful of
huge volatility episodes manufacture all the apparent forecast value.
Symmetric-versus-signed trims: H1's outcome is already sign-normalised,
so `|memoryReturn|` trimming removes the largest continuations and the
largest reversals together, which is the correct symmetric test here;
H2's outcome is non-negative by construction, so its trim is one-sided
by nature. Both are stated now so neither can be reinterpreted later.

---

## 7. ALLOWED VERDICTS

**H1 — MEMORY-PRED-V1**

| verdict | meaning |
|---|---|
| **PREDICTIVE STRUCTURE SURVIVES** | all ten gates pass **and** the effect exceeds the 0.87-pt round-turn cost |
| **PREDICTIVE STRUCTURE SURVIVES BUT SUB-COST** | all ten gates pass, effect below cost. **A full pass, not a lesser one.** |
| **REDUNDANT WITH VOLATILITY** | MP8 or MP9 fails such that `Δ_matched ≤ 0` or the matched contrast vanishes — the state label adds nothing beyond volatility/magnitude |
| **UNSTABLE** | MP3/MP4/MP5 pass but MP6 or MP7 fails |
| **FAILED** | MP3, MP4 or MP5 fails |
| **VOID** | a defect in *this* document makes the test unexecutable, with written diagnosis |

**H2 — HIGH-ARRIVAL-UTILITY-V1**

| verdict | meaning |
|---|---|
| **INCREMENTAL STATE-ARRIVAL FORECAST SURVIVES** | all ten gates pass, including HA6 |
| **STATE-ARRIVAL LAW REAL BUT FORECAST-REDUNDANT** | HA2/HA3 pass but **HA6 fails** — the transition law is real and adds nothing to a flexible function of the current shock |
| **UNSTABLE** | HA2/HA3/HA4 pass but HA9 or HA7 fails |
| **FAILED** | HA2, HA3 or HA4 fails |
| **VOID** | as above |

**Precedence:** REDUNDANT (H1) and FORECAST-REDUNDANT (H2) **outrank**
any surviving label. UNSTABLE outranks a survival label. A precondition
failure (§4.11, §5.8) yields **INSUFFICIENT DATA** and is not a FAIL.

**No "strategy edge" label exists in this study, at any outcome.**
A failed hypothesis is **destroyed, not retuned**: no threshold, state,
horizon, grid, bin, or population may be changed after any result is
seen, and no hypothesis may be re-run under a new name.

---

## 8. WHAT SURVIVAL DOES AND DOES NOT AUTHORISE

**If H1 survives** — freeze it as a predictive research candidate.
Allowed claim, verbatim: *"RVMR state changes the conditional
probability of immediate continuation versus reversal."* Not allowed:
any statement that this is an edge, a signal, or tradeable. **No
strategy is optimised now.**

**If H2 survives** — freeze it as an activity-state forecast candidate.
Allowed claim, verbatim: *"Shock-derived state-arrival propensity
provides incremental information about future activity beyond current
volatility controls."* It may eventually inform execution expectations,
risk regime, strategy activation, or movement forecasting. **It says
nothing about direction, ever.**

**In both cases** `rvmr_spec.py`, `rvmr_run.py`, the forward logger, the
prospective ledgers, OFH13/OFH14 and every NinjaTrader host remain
byte-for-byte unmodified, and RVMR's certificate gains no clause on
historical evidence alone (§11).

---

## 9. FUTURE LEAD, RECORDED BUT NOT PURSUED

If **both** survive, the following is recorded as a *separately
preregisterable future hypothesis* and is **forbidden in this study**:

```
RVMR-STATE-MACHINE-V1  (NOT PART OF THIS STUDY)
   shock → P(HIGH arrives) → HIGH actually arrives
         → short-horizon memory changes → later 15m behaviour changes
```

Tempting and premature. It requires its own preregistration, its own
family accounting (entering `M_cum` at ≥ 5), and its own prospective
requirement.

---

## 10. EXECUTION RULES (binding on the directive that runs this)

1. **One run per hypothesis.** A crash may be fixed with the diff
   disclosed; the fix may not touch a threshold, a constant, or a
   definition. (Precedent: ANOMALY-CONFIRM §1.1.)
2. **No combination of H1 and H2**, at any stage, under any result.
3. **No new hypotheses**; nothing outside this document is computed.
4. **Report every gate**, passed and failed, by its number.
5. **Report the honest verdict**, including "the replicated structure
   predicts nothing useful" if that is what the data says.
6. Every historical result is labelled **DEVELOPMENT-SUPPORTED**, never
   confirmed.
7. The engine **submits no orders** and modifies nothing frozen.

---

## 11. PROSPECTIVE REQUIREMENT (the only route to confirmation)

Because 2019–2026 is exposed (§0), any historical survivor is at most a
**DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE**. Independent confirmation
requires NQ data generated after this freeze.

> **PROSPECTIVE START (frozen, and it may not be backdated):**
> **2026-08-26 00:00:00 ET** — the first full ET day strictly after this
> preregistration's commit date. Only bars with an ET close stamp at or
> after this instant count as prospective evidence.

**A declared secondary window, honestly labelled:** the dataset ends
2026-08-17 15:16 ET, so **2026-08-18 → 2026-08-25** is data that exists
in the world but has never been captured or examined by this programme.
It may be used as an **UNSEEN-BUT-PRE-EXISTING** check. It is weaker
than true prospective evidence because it existed at freeze time, and it
must always carry that label. It is **not** the confirmation set.

**Minimum prospective sample before any confirmation verdict may be
issued** (frozen now, so the finish line cannot move):

- ≥ **60** prospective exchange days, and
- H1: ≥ **40,000** eligible events, with HIGH ≥ **1,500**
- H2: ≥ **2,000** eligible blocks, with each propensity group ≥ **400**

Below these, the only permitted statement is *"insufficient prospective
data"*.

**RVMR's certificate may gain a clause only on prospective evidence**,
never on the historical run authorised by this document.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
