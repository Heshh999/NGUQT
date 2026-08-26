# RVMR-MOMENTUM-V1 — PREREGISTRATION

**M = 2.  H1 = SHORT-HORIZON MOMENTUM (5m).  H2 = BROADER TREND STATE (30m→15m).**

**Status: PREREGISTRATION ONLY.** No performance number for either
hypothesis has been computed. This document is frozen, hashed, committed
and pushed first; a later directive may execute it.

Offline research only. No orders. Nothing frozen is modified.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 0. TWO LANES, EPISTEMIC STATUS, AND WHAT THIS STUDY IS NOT

### 0.1 Lane separation (binding)

- **LANE A — MEMORY-PRED-V1 prospective confirmation.** Frozen and
  untouched. Prospective start 2026-08-26 00:00:00 ET; finish-line
  minimums unchanged (≥60 days, ≥40,000 events, HIGH ≥1,500). Nothing
  in this study modifies its definition, and no result here may be used
  to alter it.
- **LANE B — this study.** Historical DEVELOPMENT only, on data dated
  **strictly before 2026-08-26 00:00:00 ET**. The repository data in
  fact ends 2026-08-17 15:16 ET, so zero post-boundary rows exist; the
  execution engine must nonetheless assert the exclusion explicitly.

### 0.2 Epistemic status

The entire 2019-07 → 2026-08 history is EXPOSED. This hypothesis was
motivated by MEMORY-PRED-V1's result, which was computed on all of it.
**No historical period is pristine OOS for RVMR-MOMENTUM-V1.** A full
pass earns exactly one label: **DEVELOPMENT-SUPPORTED PREDICTIVE
CANDIDATE**. Confirmation would require its own prospective window,
declared only if something survives.

### 0.3 What is inherited, and what is explicitly NOT assumed

Inherited fact (10/10 gates, sub-cost): at the 1-minute horizon, RVMR
LOW carries mild reversal information and RVMR HIGH mild continuation
information (HIGH−LOW continuation-probability gap ≈ +3.25 pp). Also
inherited: **the 15m extension of that memory FAILED** — at 15m the
interesting cell was MEDIUM continuation, not HIGH.

Therefore this study does **not** assume "HIGH means trend-following
works." Given the failed 15m limb, H2 in particular may well fail, and
that outcome is declared acceptable in advance.

**Simplicity rule (binding):** no EMA, no VWAP, no vectors, no order
flow, no 4H trend, no candlesticks, no support/resistance, no crossover.
Price-only momentum objects. If simple momentum does not interact with
RVMR, the failure is reported, not hidden inside more indicators.

### 0.4 Absolute protection

Untouched: `rvmr_spec.py`, `rvmr_run.py`, the RVMR forward logger,
OFH13/OFH14, prospective ledgers, NinjaTrader hosts, and the frozen
MEMORY-PRED-V1 candidate object.

---

## 1. PROVENANCE (verified at this freeze)

| artifact | sha256 |
|---|---|
| `analysis/rvmr/rvmr_spec.py` (frozen RVMR-V1) | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` |
| `analysis/rvmr/rvmr_run.py` (canonical loader) | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` |
| `docs/MEMORY_PRED_V1_FINDINGS.md` (motivating result) | `641a3d2a5c9c8e003dbae9c0aeb3799a0bdd77e15d87c422b6e0e5575db4aa3b` |
| `docs/HIGH_ARRIVAL_UTILITY_V1_FINDINGS.md` (the redundancy lesson) | `35bdfa00d8f88721231c426ef2c75293802fdf5a371dc0aa512b4661ee3a9e60` |
| `docs/RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md` | `afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8` |

Base commit at freeze: `2f16b5d1657ec6ba480fd7240131902fc1b12041`, tree
clean. Data: the canonical 2,503,622-row NQ 1m capture via
`rvmr_run.load_bars()`, `STAMP_SHIFT = 0`, close-stamped ET.

---

## 2. SHARED MACHINERY (frozen)

### 2.1 Bars, contiguity, and returns

Parallel arrays from the loader; `em` = integer minutes since
2019-01-01 is the contiguity clock. **This study uses the directive's
simple-return formulas verbatim** (they are the defining objects here;
there is no prior frozen code for them):

```
mom5(t)    = c[t]/c[t-5]  - 1     requires em[t]-em[t-5]  == 5
fut5(t)    = c[t+5]/c[t]  - 1     requires em[t+5]-em[t]  == 5
trend30(t) = c[t]/c[t-30] - 1     requires em[t]-em[t-30] == 30
fut15(t)   = c[t+15]/c[t] - 1     requires em[t+15]-em[t] == 15
```

The `em`-difference conditions guarantee every window is a genuinely
unbroken run of minutes (strictly increasing integer stamps, H steps
summing to H ⇒ each step is 1). Gaps are skipped, never bridged; no bar
is interpolated, forward-filled, or split; no intrabar sequence is ever
inferred. All prices must be > 0.

### 2.2 RVMR state at decision time

State = **`RB[t]`**, the frozen RVMR RANGE bucket of the decision bar:
`trailing_ratio(high−low, W=1440)` over bars `t−1440 … t−1` (excludes
bar `t`), thresholds `LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH`, unchanged
and untouched. `RB[t]` is available at the close of `t−1`, strictly
before the decision. Events require `RB[t]` non-None.

### 2.3 Event grid and overlap (declared, not hidden)

Events are formed at **every eligible minute t**. Forward windows
therefore overlap by construction (consecutive H1 events share 4 of 5
outcome minutes). This follows the programme's frozen RVMR-V1
convention: **the exchange day is the cluster unit, a minute is never an
independent trial, and within-day overlap is handled by resampling whole
days.** The permutation null (§7.3) is chosen specifically to respect
within-day dependence.

### 2.4 Zero handling (frozen)

`mom5 == 0` (or `trend30 == 0`): event **excluded** — sign undefined.
Future return `== 0`: **retained at 0** for the mean endpoint,
**excluded** from the sign-probability endpoint only.

### 2.5 Frozen partitions and computed-at-execution cutpoints

- Time-of-day buckets (of the **decision bar** `mod[t]`):
  `OVERNIGHT` = mod ≥ 1081 or ≤ 569; `RTH_AM` = 570–750;
  `RTH_PM` = 751–960. No narrower window may be examined.
- `atrRel(t) = atr20(t)/c[t]` (SMA-20 true range ending at `t`).
- Where a control needs a partition with no frozen constant
  (`atrRel` terciles, `|mom5|` terciles, `|trend30|` terciles, score
  quintiles), cutpoints are **type-7 terciles/quintiles of the eligible
  population, computed once at execution on the pooled development
  data, with no search and no alternatives tried**, labelled in-sample
  wherever reported. No threshold may move after any outcome is seen.

### 2.6 Cluster key, year, month

Cluster day = **the calendar day of the forward window's final bar**
(`day[t+5]` for H1, `day[t+15]` for H2) — the day that owns the
outcome, consistent with MEMORY-PRED's `day[t+1]`. Year and month
assignments follow the cluster day.

---

## 3. FAMILY SIZE AND THE PROGRAMME LEDGER

> **M_binding = 2**: H1 SHORT-HORIZON MOMENTUM, H2 BROADER TREND STATE.
> No timeframe grid exists. M stays 2 under any outcome.

**Cumulative programme multiplicity, disclosed (never shrunk):**
promotable tests run on this exposed history now number
**M_cum = 6** — SHOCK-CONT-MEDIUM (p 0.10050), MONDAY-RTH (0.03570),
MEMORY-PRED (0.00005), HIGH-ARRIVAL-UTILITY (primary p 0.00005; verdict
FORECAST-REDUNDANT on the binding control), plus this study's H1 and
H2. The execution reports **exact BH at M_cum = 6** over all six primary
p-values as a **non-binding sensitivity** that may not change a verdict.

If one hypothesis is executed before the other, the BH gate uses the
**conservative bound** `q ≤ 2p` (rank 1 of 2), per the MEMORY-PRED
precedent; once both p-values exist the exact BH is reported.

---

## 4. H1 — SHORT-HORIZON MOMENTUM

### 4.1 Exact objects (frozen — ONE window, no grid)

Predictor: `mom5(t)`, the completed trailing 5-minute simple return.
Direction: `sign(mom5)`. Outcome: `fut5(t)`.

```
alignedReturn5 = sign(mom5) × fut5
```

Positive = momentum continued; negative = reversed. **No 2m/3m/4m/6m/8m/
10m variant exists in this study, before or after results.**

Eligibility at `t`: the two `em` conditions of §2.1 hold; all closes
`c[t−5…t+5] > 0`; `mom5 ≠ 0`; `RB[t]` non-None; `atr20(t)` available;
`day[t+5] ≤ 2026-08-25`.

### 4.2 Primary endpoint

> **Δ5 = E[alignedReturn5 | RB[t]=HIGH] − E[alignedReturn5 | RB[t]=LOW] > 0**

MEDIUM reported, not gated.

### 4.3 Probability endpoint (gated per MO5)

`P(sign(fut5) == sign(mom5) | state)` for LOW/MEDIUM/HIGH, with the
HIGH−LOW contrast and its day-clustered CI. Gate MO5 requires the
point-estimate contrast > 0. No probability threshold is optimised.

### 4.4 Magnitude robustness (frozen set of three; cannot rescue)

ALL (primary) · TOP 50% `|mom5|` · TOP 20% `|mom5|` (type-7 cutpoints
per §2.5). No other subset exists.

### 4.5 Minimum n (precondition ⇒ INSUFFICIENT DATA, not FAILED)

LOW ≥ 500,000 · MEDIUM ≥ 80,000 · HIGH ≥ 25,000 events.

### 4.6 THE TEN H1 GATES (MO1–MO10)

| # | condition | frozen threshold |
|---|---|---|
| MO1 | causal integrity | every event satisfies both `em` conditions; every predictor (`mom5`, `RB[t]`, `atr20(t)`, ToD) available at close of `t`; violations = 0 |
| MO2 | ordering | `Δ5 > 0` |
| MO3 | dependence-aware CI | day-clustered 95% CI on `Δ5` excludes 0 (20,000 iters, seed 20260826) |
| MO4 | corrected support | BH `q ≤ 0.05` at M = 2 **AND** rotation permutation (§7.3) `p ≤ 0.05` |
| MO5 | probability contrast | `P(cont\|HIGH) − P(cont\|LOW) > 0` |
| MO6 | \|mom5\| control | `\|mom5\|`-tercile common-weight standardised `Δ5 > 0` **AND** ≥ 0.50 × raw `Δ5` |
| MO7 | ATR control | ATR-tercile common-weight standardised `Δ5 > 0` **AND** ≥ 0.50 × raw |
| MO8 | time stability | `Δ5 > 0` in ≥ 2 of 3 frozen ToD buckets |
| MO9 | year stability | `Δ5 > 0` in ≥ 6 of 8 years (2019p…2026p); no year deleted |
| MO10 | tail robustness | `Δ5 > 0` after **within-state** removal of the top 1% and top 5% by `\|alignedReturn5\|` (pooled trim reported with composition; H1/H2 precedent) |

The full 27-cell match (`|mom5|` × ATR × ToD, common weight, cells ≥30
both sides) is **reported** alongside MO6/MO7, not separately gated.

---

## 5. H2 — BROADER TREND STATE

### 5.1 Exact objects (frozen)

Predictor: `trend30(t)`, the completed trailing 30-minute simple
return — **price itself, no moving average, by design**: a
trailing-return trend has no period/lag/crossover degrees of freedom,
so it is easier to falsify. An EMA implementation may only ever be a
later, separately preregistered study, and only if this survives.

Outcome: `fut15(t)`.

```
alignedReturn30 = sign(trend30) × fut15
```

Eligibility as §4.1 with the 30/15 `em` conditions and
`day[t+15] ≤ 2026-08-25`.

### 5.2 Primary endpoint

> **Δ30 = E[alignedReturn30 | HIGH] − E[alignedReturn30 | LOW] > 0**

### 5.3 The HIGH-ARRIVAL lesson — nonlinear baseline (binding gate MT6)

A beautiful RVMR contrast can merely relabel current movement magnitude.
Frozen day-clustered OLS (per-day sufficient statistics; numpy
multinomial day-weight bootstrap under seed 20260826, per the H2
precedent):

```
B  = alignedReturn30 ~ 1 + |trend30| + |trend30|² + up + up×|trend30|
                         + atrRel(t) + ToD dummies
A  = B + HIGH dummy + MEDIUM dummy        (LOW = base)
```

where `up = 1 if trend30 > 0`. **MT6: the HIGH-dummy coefficient in A is
positive with a day-clustered 95% CI excluding 0.** (ΔR² is reported;
as established in HIGH-ARRIVAL, in-sample ΔR² > 0 is near-tautological
and the CI is the informative leg.) The continuous-score variant of A
is a reported diagnostic only.

If MT6 fails while pooled trend continuation is itself real, the honest
verdict is **TREND REAL — RVMR REDUNDANT**, declared in advance as a
legitimate outcome, not argued around.

An analogous regression for H1 is **reported as a diagnostic**
(declared now); H1's binding magnitude control is MO6.

### 5.4 Minimum n

LOW ≥ 400,000 · MEDIUM ≥ 60,000 · HIGH ≥ 20,000 events.

### 5.5 THE TEN H2 GATES (MT1–MT10)

| # | condition | frozen threshold |
|---|---|---|
| MT1 | causal integrity | as MO1, with the 30/15 windows |
| MT2 | ordering | `Δ30 > 0` |
| MT3 | dependence-aware CI | day-clustered 95% CI on `Δ30` excludes 0 (20,000 iters, seed 20260826) |
| MT4 | corrected support | BH `q ≤ 0.05` at M = 2 **AND** rotation permutation `p ≤ 0.05` |
| MT5 | \|trend30\| control | tercile common-weight standardised `Δ30 > 0` **AND** ≥ 0.50 × raw |
| MT6 | **nonlinear trend baseline (BINDING)** | HIGH-dummy coefficient in model A positive, day-clustered 95% CI excludes 0 |
| MT7 | ATR control | ATR-tercile standardised `Δ30 > 0` **AND** ≥ 0.50 × raw |
| MT8 | time stability | `Δ30 > 0` in ≥ 2 of 3 buckets |
| MT9 | year stability | `Δ30 > 0` in ≥ 6 of 8 years; no year deleted |
| MT10 | tail robustness | `Δ30 > 0` after within-state top-1% and top-5% trims by `\|alignedReturn30\|` |

---

## 6. CONTROLS, BASELINES, DIAGNOSTICS (all declared now)

**Common-weight standardisation** (the corrected construction, not the
degenerate ANOMALY-CONFIRM §4.13 weighting): within each cell compute
`Δ_cell = mean(HIGH) − mean(LOW)`; combine with the **common** weight
`w_cell = n_HIGH + n_LOW` over cells with ≥30 events on both sides;
report cell coverage. Applied per MO6/MO7/MT5/MT7 and the 27-cell
match.

**Long/short symmetry (classification rule, not a gate):** report the
HIGH−LOW contrast separately for UP-momentum and DOWN-momentum (H1) and
UP-trend / DOWN-trend (H2). If a primary passes while one side's
contrast is ≤ 0, the verdict carries a **mandatory annotation
"ASYMMETRIC — (side)"**. NQ's upward drift must not masquerade as
trend-following; the per-side split plus the following baselines expose
it.

**Directional baselines (reported):** (1) unconditional
`P(fut > 0)` and mean `fut`; (2) pooled aligned return with no RVMR
conditioning (momentum alone), with day-clustered CI; (3) mean *signed*
future return by state with no momentum conditioning (RVMR alone —
expected ≈ 0, RVMR is non-directional); (4) the matched standardisations
of §4.6/§5.5.

**Score-vs-label diagnostic (reported only):** aligned return by
in-sample quintile of the continuous RANGE score `rr[t]`, checking
monotonicity. The 1.270/2.335 thresholds are not touched and no new
threshold is adopted.

**Raw geometry (reported; no stops, no targets):** direction-relative
favorable excursion `(max high[t+1…t+H] − c[t])/c[t]` for UP (mirrored
for DOWN) and adverse excursion likewise, plus continuation probability,
by state. **"Favorable-first" is NOT computed:** ordering excursions
inside the window would require intrabar sequence, which the programme
never invents.

**Cost framing (reported, never gated):** effects in bp, NQ points at
the mean close of HIGH∪LOW events, and multiples of the frozen 0.87-pt
round turn — reported for **both** the contrast Δ **and** the HIGH-arm
aligned mean alone, with the standing note that only an arm is
tradeable, never a difference. The SUB-COST verdict split (§8) is
decided by the **HIGH-arm** aligned mean vs 0.87 pt.

**Month destruction (reported):** monthly Δ; positive/negative counts,
median, best, worst. No month selection.

---

## 7. INFERENCE (frozen)

1. **Day-clustered percentile bootstrap**, whole days with replacement,
   **20,000 iterations**, **seed 20260826**, 95% CI;
   `p = 2 × min(#{b≤0}, #{b≥0})/B`, floored at `1/(B+1)`. Scalar
   bootstraps via `random.Random(20260826)`; the MT6 coefficient
   bootstrap via numpy multinomial day-weights (PCG64, same seed),
   disclosed as statistically identical to whole-day resampling.
2. **BH at M_binding = 2** (q ≤ 0.05) over the two primary p-values;
   exact once both exist, conservative bound `2p` if one runs first.
   **Exact BH at M_cum = 6** reported, non-binding.
3. **Permutation null — within-day circular rotation** (both
   hypotheses): within each cluster day, rotate the day's **state-label
   sequence** by a uniform random offset in `[1, n_day−1]`, leaving
   outcomes in place; recompute Δ. 20,000 iterations, seed 20260826,
   two-sided. **Why rotation, frozen now with its rationale:** with
   overlapping forward windows and persistent state labels, a naive
   within-day shuffle destroys the labels' own autocorrelation and
   makes the null anti-conservatively tight; rotation preserves the
   run-structure of both sequences and destroys only their alignment.
   This choice is made before any result exists.
4. No minute-level iid standard error decides anything. No ML. No
   parameter sweeps. One execution run per hypothesis; a crash fix must
   disclose its diff and may not touch a threshold, constant or
   definition.

---

## 8. ALLOWED VERDICTS (mechanical; the taxonomy gap is closed this time)

**H1:** RVMR-CONDITIONED MOMENTUM SURVIVES · … SURVIVES BUT SUB-COST ·
MOMENTUM REAL — RVMR REDUNDANT · UNSTABLE · FAILED · VOID.
**H2:** RVMR-CONDITIONED TREND SURVIVES · … SURVIVES BUT SUB-COST ·
TREND REAL — RVMR REDUNDANT · UNSTABLE · FAILED · VOID.

Decision rules (H1 shown; H2 identical with MT numbers and the pooled
trend baseline):

- **SURVIVES / SURVIVES BUT SUB-COST** — all ten gates pass; the split
  is decided by the HIGH-arm aligned mean vs 0.87 pt (§6). Both are
  full passes.
- **REDUNDANT** — the pooled aligned return (baseline 2) is positive
  with day-clustered CI excluding 0, **and** MO6 or MO7 (H2: MT5, MT6
  or MT7) fails. The momentum is real; RVMR adds nothing demonstrable.
  Outranks every survival label.
- **UNSTABLE** — MO2/MO3/MO4 pass but MO8 or MO9 fails. Outranks
  survival labels.
- **FAILED** — MO2, MO3 or MO4 fails, **or any other gate fails in a
  pattern not covered by REDUNDANT or UNSTABLE** (this clause closes
  the taxonomy gap that surfaced in ANOMALY-CONFIRM and
  HIGH-ARRIVAL: every non-passing pattern now maps to exactly one
  verdict, with the failing gate named).
- **VOID** — a defect in this document, with written diagnosis; the
  slot stays spent.
- Precondition failure (§4.5/§5.4) ⇒ **INSUFFICIENT DATA**, not FAILED.
- A passing verdict carries the **ASYMMETRIC** annotation when §6's
  side rule triggers.

A failed hypothesis is destroyed, not retuned. No new timeframe may be
tried because these failed. If both fail, the recorded interpretation
is: *MEMORY-PRED is a very short-horizon statistical property that does
not extend cleanly into simple multi-minute momentum or trend
following* — and that ends the branch.

---

## 9. WHAT SURVIVAL DOES AND DOES NOT AUTHORISE

- **H1 survives** → allowed claim: *"RVMR RANGE state changes the
  predictive value of a recent 5m momentum signal."* Status:
  DEVELOPMENT-SUPPORTED PREDICTIVE CANDIDATE. No strategy.
- **H2 survives** → allowed claim: *"RVMR RANGE state changes the
  persistence of a broader 30m trend into the next 15m."* Same status.
- **Both survive** → no combined model here. Future lead recorded, not
  pursued: `RVMR-TREND-MOMENTUM-COMBINE-V1` (would enter the cumulative
  family at M_cum ≥ 7, with its own preregistration).
- In every case RVMR-V1's certificate is unchanged on historical
  evidence, and MEMORY-PRED-V1's Lane-A prospective test proceeds
  exactly as frozen, untouched by these results.

---

## 10. EXECUTION RULES (binding on the executing directive)

1. Phase 0 must verify this document's sha256, the RVMR spec constants,
   and the zero-rows-past-boundary assertion **before** any outcome is
   read.
2. Report every gate by number, passed and failed. No subjective
   override. Report discovery-free honesty: all results labelled
   DEVELOPMENT.
3. Report both hypotheses' full year/month/tail/side tables regardless
   of verdict.
4. H1 and H2 may be executed in one run or separately; no result of one
   may alter the other's frozen definition.
5. The engine submits no orders and simulates no trade — no entries,
   stops, targets, sizing, or execution assumptions.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
