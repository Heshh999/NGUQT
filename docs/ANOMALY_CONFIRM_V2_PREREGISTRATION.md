# ANOMALY-CONFIRM-V2 — PREREGISTRATION

**M = 2.  H1 = ORDINAL-V-TURN.  H2 = HALF-SESSION-LOW.**

**Status: PREREGISTRATION ONLY.** No 2024+ outcome for either candidate
has been computed. This document is frozen, hashed, committed and pushed
first; a later directive opens the confirmation window exactly once.

Offline research only. No orders. Nothing frozen is modified.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 0. EPISTEMIC STATUS — HYPOTHESIS-SPECIFIC UNEXAMINED HISTORICAL CONFIRMATION

This is **not** globally untouched data, and **not** prospective
confirmation. It is precisely this:

> **The 2024-01-01 → 2026-08-17 window has been used by other studies,
> but the exact outcome objects of ORDINAL-V-TURN and HALF-SESSION-LOW
> have never been computed on it.** A pass earns the label
> **CONFIRMED (hypothesis-specific historical)** — stronger than a
> development result, weaker than a prospective one. Prospective
> validation on data after this capture would remain a separate step.

### 0.1 Contamination audit (mechanical, performed before freeze)

Both scan waves hard-restrict every statistic to `day <= '2023-12-31'`
(`scan3_run.py`: `LAST = max i with day[i] <= DISC_END`, and every S24
and S30 loop guards `if day[...] > DISC_END: continue`). So Wave 3
itself never touched 2024+ for these objects.

Prior 2024+ studies and what they computed — checked object by object:

| study | 2024+ object | overlaps a candidate here? |
|---|---|---|
| ANOMALY-CONFIRM-V1 | shock-continuation deciles; Monday-RTH accrual | **No** |
| MEMORY-PRED-V1 | `sign(r[t])×r[t+1]` by RVMR state (lag-1) | **Partial — see 0.2** |
| HIGH-ARRIVAL-UTILITY-V1 | 30m realised range by shock propensity | **No** |
| RVMR-MOMENTUM-V1 | `sign(mom5)×fut5`, `sign(trend30)×fut15` by state | **No** (5m/30m trailing, not 3-bar ordinal, not half-session) |

### 0.2 The one honest overlap, and why the primary is clean of it

MEMORY-PRED computed the lag-1 direction-normalized return
`sign(r[t])×r[t+1]` by RVMR state on 2024+. An ordinal 3-motif's
**last-leg marginal** — `P(r[t+1] up | last leg up)` — is exactly that
lag-1 object, so the raw per-motif means are **partially exposed** on
2024+ through their last-leg component.

**This is exactly why H1's primary is a WITHIN-last-leg contrast.**
The primary Δturn (§5) compares a V-turn motif against an established
motif **at the same last-leg sign**, so the exposed lag-1 marginal is
common to both arms and **cancels out of the contrast**. The
second-order object — does path *shape* add information beyond the
last leg — is unexamined on 2024+. The raw per-motif means are reported
but flagged partially-exposed; only the within-last-leg contrast is
gated. **No candidate outcome was inspected; if the confirmation engine
ever shows one was, STOP and disclose.**

### 0.3 Absolute protection

Untouched: MEMORY-PRED-V1 and its 2026-08-26 prospective start and
ledger; RVMR-V1; the RVMR forward logger; OFH13/OFH14; the NinjaTrader
prospective host. The engine asserts the confirmation window is
`>= 2024-01-01` and consumes zero rows `>= 2026-08-26`.

---

## 1. STEP 1 — SOURCE LINEAGE

| artifact | sha256 | commit |
|---|---|---|
| `docs/ANOMALY_SCAN_V1_PROTOCOL.md` (Wave-3 menu) | `3b8f13a8ad6180e91924a3ee66beef18b1e9ed48146c99a6cba19709e027fbb8` | `b054a00c71255a74be908df001ee157fbf8c3b0f` |
| `analysis/anomaly/scan3_run.py` (Wave-3 engine) | `b8495516a9dcf9ada3ac287e304292fedd9ba3a8ac4a446bef858ad7dba73135` | `0ba46c1f59fa41d1dc4573bdf32efceec1de362a` |
| `docs/ANOMALY_SCAN_V1_FINDINGS.md` (Wave-3 findings) | `4ab01ba03528a53c7f71697cdaeed630577f7a6d201c15413117b8baf4bd2be2` | `0ba46c1f59fa41d1dc4573bdf32efceec1de362a` |
| `analysis/rvmr/rvmr_spec.py` (RVMR-V1) | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` | (frozen) |
| `analysis/rvmr/rvmr_run.py` (canonical loader) | `8743161d6fb5b04e8092f4ea571e86bb09bedd9db161dc6d31b364a0b868bd8c` | (frozen) |

Freeze order: Wave-3 menu `b054a00` (before computation) → Wave-3 run +
findings `0ba46c1` → RVMR-MOMENTUM executed and closed → **this
preregistration**. Definitions below are read from the engine by line;
none is reconstructed from this prompt.

---

## 2. STEP 2 — FAMILY SIZE AND LEDGER

> **M_binding = 2**: H1 ORDINAL-V-TURN, H2 HALF-SESSION-LOW.
> **RUN-AGE-HAZARD is NON-PROMOTABLE** — mechanism corroboration only,
> cannot rescue either candidate. M stays 2 under FAIL / VOID /
> INSUFFICIENT DATA.

**Cumulative programme ledger (never-shrink), promotable tests:**

| # | test | outcome |
|---|---|---|
| 1 | SHOCK-CONT-MEDIUM | FAILED HOLDOUT |
| 2 | MONDAY-RTH | FAILED HOLDOUT |
| 3 | MEMORY-PRED-V1 | SURVIVES SUB-COST (dev) |
| 4 | HIGH-ARRIVAL-UTILITY-V1 | FORECAST-REDUNDANT |
| 5 | RVMR-MOMENTUM H1 | FAILED |
| 6 | RVMR-MOMENTUM H2 | TREND REAL — RVMR REDUNDANT |
| 7 | **ORDINAL-V-TURN** (this study) | — |
| 8 | **HALF-SESSION-LOW** (this study) | — |

**M_cum = 8.** BH at M_cum = 8 over all eight primary p-values is
reported as a **non-binding** sensitivity; it may not change the binding
verdict.

---

## 3. SHARED MACHINERY (frozen)

- **Loader** `rvmr_run.load_bars()`, `STAMP_SHIFT = 0`, close-stamped ET.
- **Return** `r[i] = log(c[i]/c[i-1])` admitted only on `em[i]−em[i-1]==1`,
  `c[i-1]>0`. Gaps skipped, never bridged; no bar split or interpolated.
- **RVMR state** `RB[t]` = `bucket(trailing_ratio(high−low,1440))`,
  window `t−1440…t−1` excludes bar `t`, thresholds 1.270/2.335
  **untouched**. Available at close of `t−1`.
- **Confirmation window** `2024-01-01 ≤ day ≤ 2026-08-17`. Discovery
  window `day ≤ 2023-12-31` is read only to recompute frozen retention
  anchors (public data).
- **Inference** day-clustered percentile bootstrap, whole days, **20,000
  iterations, seed 20260826**, 95% CI, `p = 2·min(#≤0,#≥0)/B` floored
  at `1/(B+1)`. No minute-level iid SE decides anything. No ML, no
  sweeps, one run per hypothesis.
- **Cost** 0.87-pt round turn, reported never gated.

---

## 4. CANDIDATE 1 — ORDINAL-V-TURN

### 4.1 Exact motif definition (verbatim, `scan3_run.py` S24)

At bar `t`, with `em[t]−em[t−2]==2` and `em[t+1]−em[t]==1`, take closes
`(x0,x1,x2)=(c[t−2],c[t−1],c[t])`. **Ties skipped:**
`if x0==x1 or x1==x2 or x0==x2: continue`. Motif =
`''.join(str(j) for j in sorted(range(3), key=lambda j:(x0,x1,x2)[j]))`.
Outcome `r[t+1]` must exist (contiguous). Encoding:

| motif | shape | last leg (x1→x2) | role |
|---|---|---|---|
| **102** | down then up (**V-up**, fresh reversal up) | **UP** | V-turn |
| **012** | up then up (established up-run) | UP | established |
| **201** | up then down (**Λ-down**, fresh reversal down) | **DOWN** | V-turn |
| **210** | down then down (established down-run) | DOWN | established |

`120` and `021` (partial reversals) are **reported, not in the primary**.

### 4.2 Direction-normalized aligned return

`lastLegSign = sign(x2 − x1)` (+1 for 102/012, −1 for 201/210).
`turnAligned = lastLegSign × r[t+1]`. Positive = price continued in the
last-leg direction.

### 4.3 PRIMARY contrast (one scalar, within last leg)

> **Δturn = E[turnAligned | V-turn {102,201}] − E[turnAligned |
> established {012,210}] > 0**

Because both arms share the same last-leg sign composition, the
lag-1-exposed marginal cancels; Δturn measures only whether a **fresh
reversal** carries more forward continuation than an **aged run** of the
same final direction. This is the fixed-last-leg cross-motif contrast
the Wave-3 findings recommendation named.

**Reported secondary (continuity with the frozen protocol headline):**
`E[r|012] − E[r|210]` (ascending−descending), the S24 protocol headline.
Cannot rescue or overturn the primary.

### 4.4 RVMR amplification — SECONDARY, per the frozen protocol

The Wave-3 **protocol** (menu `b054a00`) declares S24's RVMR interaction
as a *"motif table by RB[t]"* — reported, not a gated primary. Resolved
**before holdout**, therefore: **Option A** — the primary claim is the
POOLED Δturn > 0; RVMR is a corroborating secondary, **not** part of the
primary. Frozen amplification secondary (gate VT-amp, corroborating):

> **Δturn|HIGH > Δturn|LOW** (state at bar `t`, `RB[t]`).

Discovery anchors (from findings §J): up-side HIGH contrast +0.1270 vs
LOW +0.0488; down-side HIGH +0.2483 vs LOW +0.0514 bp — amplification
present in discovery. This secondary corroborates mechanism; it cannot
rescue a failed pooled primary.

### 4.5 Both directions required (frozen)

> **Bullish side** `E[turnAligned|102] − E[turnAligned|012] > 0`
> **AND bearish side** `E[turnAligned|201] − E[turnAligned|210] > 0`.

Neither tail may carry the result alone. Discovery: up-side +0.0753,
down-side +0.0831 bp — both positive.

### 4.6 Final-leg magnitude control — BINDING (the crux)

A V-turn must not win merely because its last leg `|x2−x1|` is larger
than the established motif's. Frozen matched contrast:

Stratify events by **`|x2−x1|` tercile × ATR tercile × ToD bucket**
(in-sample terciles, computed once, no search). Within each cell compute
`Δturn_cell = mean(turnAligned|V-turn) − mean(turnAligned|established)`;
combine with the **common** weight `w = n_Vturn + n_established` over
cells with ≥30 both sides. This is the corrected common-weight
difference-of-means (not the degenerate ANOMALY-CONFIRM §4.13 form).

> **VT8: Δturn_matched > 0 AND ≥ 0.50 × Δturn_raw.**

A day-clustered OLS is reported alongside (turnAligned ~ V-turn dummy +
`|lastleg|` + `|lastleg|²` + atrRel + ToD + RVMR score), non-gated.

### 4.7 RUN-AGE-HAZARD diagnostic (non-promotable)

Recompute h(k)=P(a 1m directional run survives its k-th minute) for
k∈{1,3,5,9+} by state on the confirmation window, checking the same
qualitative monotone decay found in discovery (steepest in HIGH). This
tests the *mechanism* (fresh directions carry more information than aged
runs). **It cannot rescue ORDINAL-V-TURN.**

### 4.8 Controls, economics, stability, tails

- **Controls** (VT8 binding; rest reported): last-leg sign (built into
  the within-leg contrast), last-leg magnitude, ATR, ToD, RVMR state,
  recent 60-bar range, recent 60-bar volume, year.
- **Economics** (reported, never gated): Δturn and the V-turn arm alone
  in bp, NQ points at the holdout mean close, and multiples of 0.87 pt.
  A 1-minute path-shape effect is expected sub-cost; that is a full pass
  class, not a failure.
- **Effect retention**: Δturn_holdout ≥ **⅓ × Δturn_discovery** (engine
  recomputes both on their own windows; no pooling).
- **Stability**: Δturn > 0 in **≥ 2 of 3** years {2024, 2025, 2026p} and
  **≥ 18 of ~32** holdout months.
- **Tails**: within-group (V-turn and established each trimmed at their
  own top 1% / 5% by `|turnAligned|`) — Δturn > 0 after both. Pooled
  trim reported with composition.
- **Minimum n** (precondition ⇒ INSUFFICIENT DATA): each of {102, 012,
  201, 210} ≥ **20,000** events on the confirmation window.

### 4.9 THE FOURTEEN H1 GATES (VT1–VT14)

| # | condition | threshold |
|---|---|---|
| VT1 | hypothesis-specific holdout integrity | all events `2024-01-01 ≤ day ≤ 2026-08-17`; 0 rows ≥ 2026-08-26; contamination audit clean |
| VT2 | exact motifs transported | tie-skip + em-contiguity verbatim; encoding table reproduced |
| VT3 | fresh-turn contrast sign | `Δturn > 0` |
| VT4 | dependence-aware CI | day-clustered 95% CI on Δturn excludes 0 (20,000, seed 20260826) |
| VT5 | corrected support | BH `q ≤ 0.05` at M = 2 **AND** within-day motif-label rotation permutation `p ≤ 0.05` |
| VT6 | bullish side | `E[turnAligned\|102] − E[turnAligned\|012] > 0` |
| VT7 | bearish side | `E[turnAligned\|201] − E[turnAligned\|210] > 0` |
| VT8 | final-leg magnitude match (BINDING) | `Δturn_matched > 0` AND `≥ 0.50 × Δturn_raw` |
| VT9 | ATR survival | Δturn > 0 in ≥ 2 of 3 ATR terciles |
| VT10 | time stability | Δturn > 0 in ≥ 2 of 3 ToD buckets |
| VT11 | year stability | Δturn > 0 in ≥ 2 of 3 years |
| VT12 | month stability | Δturn > 0 in ≥ 18 of ~32 months |
| VT13 | tail robustness | Δturn > 0 after within-group 1% and 5% trims |
| VT14 | retention | Δturn_holdout ≥ ⅓ × Δturn_discovery |

VT-amp (RVMR amplification, corroborating, non-gating): reported.

---

## 5. CANDIDATE 2 — HALF-SESSION-LOW

### 5.1 Exact definition (verbatim, `scan3_run.py` S30)

Per exchange day, over bars with a contiguous return (`rarr[i]` not
None):

- **morning** `am[d] = Σ r[i]` for `571 ≤ mod[i] ≤ 720` (09:31–12:00 ET
  close stamps); **`am_n[d]`** counts those bars.
- **afternoon** `pm[d] = Σ r[i]` for `721 ≤ mod[i] ≤ 960` (12:01–16:00);
  **`pm_n[d]`** counts those.
- **noon state** `noonRB[d]` = `RB` at the **last** morning bar (mod
  closest to 720) — the noon decision point, known at 12:00.
- **eligibility** `am_n[d] ≥ 120` AND `pm_n[d] ≥ 180` AND `am[d] ≠ 0`.
- **outcome** `halfSessionAligned = sign(am[d]) × pm[d]`.

No hour, session, holiday, or early-close rule is adjusted. Days failing
the bar-count thresholds simply drop out (no imputation).

### 5.2 PRIMARY claim and its declared subgroup status

> **E[halfSessionAligned | noonRB = LOW] > 0**, day-clustered 95% CI
> excluding 0. (Cluster = the day; the bootstrap is over LOW days.)

**Declared honestly and bindingly:** HALF-SESSION-LOW is a **subgroup of
a pooled null** — the Wave-3 pooled headline (+3.69 bp) did **not**
reach significance. Therefore:

> **The confirmation stands entirely on the LOW cell's own frozen
> criteria. Pooled or all-state performance may NOT be used as
> supporting evidence, ever.**

Discovery anchors: LOW +8.32 bp, n 591, P(match) 0.6007; MED +0.79;
HIGH −16.54 (n 67). Feasibility (timestamp-only census): **649** eligible
holdout days total (2024: 249, 2025: 246, 2026p: 154); the LOW subset
is a fraction thereof.

### 5.3 Direction symmetry (frozen)

Report `E[·|LOW, am>0]` and `E[·|LOW, am<0]` separately. NQ's upward
drift must not manufacture the effect.

> **HS-sym (required): the LOW effect must be positive on BOTH morning
> signs** — `E[sign×pm | LOW, am>0] > 0` (i.e. up-mornings continue up)
> **AND** `E[sign×pm | LOW, am<0] > 0` (down-mornings continue down).
> If only one side is positive, the verdict carries **ASYMMETRIC** and
> cannot be CONFIRMED (downgrades to PARTIALLY CONFIRMED at best).

### 5.4 Controls (reported; HS8/HS9 binding)

- **HS8 morning-magnitude control (BINDING):** split LOW days at the
  in-sample median `|am|`; the LOW effect must be positive in **both**
  halves (i.e. not driven only by big-morning days). Also reported: a
  day-level OLS `halfSessionAligned ~ |am| + atrRel(noon) + RVMR score
  (noon) + recent range + recent volume` on LOW days — is the LOW mean
  more than "quiet morning → quiet drift"?
- **HS9 non-LOW contrast (BINDING):** `E[·|LOW] − E[·|non-LOW] > 0` with
  its own day-clustered CI excluding 0 — the effect must be **specific**
  to the LOW state, not present everywhere. (non-LOW = MED ∪ HIGH days.)
- Reported baselines: pooled (context only, non-supporting), MED, HIGH,
  morning-sign-only without RVMR, ATR-matched LOW vs non-LOW.

### 5.5 Economics, stability, tails, retention

- **Economics** (reported): mean, NQ points at holdout close, cost
  multiple. Discovery ≈ +8.3 bp ≈ 13 pts — economically large, which
  makes destruction **more** important.
- **Effect retention**: `E[·|LOW]_holdout ≥ ⅓ × E[·|LOW]_discovery`
  (i.e. ≥ **+2.77 bp** against the +8.32 anchor) and positive.
- **Stability**: LOW mean > 0 in **≥ 2 of 3** years and in **≥ 17 of
  ~32** months (small monthly n acknowledged).
- **Tails (critical)**: report full, ex-top-1%, ex-top-5% (by signed
  `halfSessionAligned`), median, 10%-trimmed mean, and the 5 largest
  contributing days. Gate: mean > 0 after top-1% AND top-5% removal;
  else **TAIL-DEPENDENT**.
- **Minimum n** (precondition ⇒ INSUFFICIENT DATA): LOW days ≥ **120**.

### 5.6 THE FOURTEEN H2 GATES (HS1–HS14)

| # | condition | threshold |
|---|---|---|
| HS1 | exact LOW subgroup definition | mod windows 571–720 / 721–960, noonRB = last morning bar, bar-count thresholds verbatim |
| HS2 | adequate n | LOW days ≥ 120 |
| HS3 | positive aligned mean | `E[·\|LOW] > 0` |
| HS4 | effect retention | `≥ ⅓ × discovery` (≥ +2.77 bp) |
| HS5 | dependence-aware CI | day-clustered 95% CI excludes 0 (20,000, seed 20260826) |
| HS6 | corrected support | BH `q ≤ 0.05` at M = 2 **AND** day sign-flip permutation `p ≤ 0.05` |
| HS7 | long/short honesty | both morning signs positive (else ASYMMETRIC, downgrade) |
| HS8 | morning-magnitude control (BINDING) | LOW effect > 0 in both `\|am\|` halves |
| HS9 | LOW-specificity (BINDING) | `E[·\|LOW] − E[·\|non-LOW] > 0`, own CI excludes 0 |
| HS10 | ATR control | LOW effect > 0 after ATR-median split (both halves) |
| HS11 | year stability | LOW mean > 0 in ≥ 2 of 3 years |
| HS12 | month stability | LOW mean > 0 in ≥ 17 of ~32 months |
| HS13 | tail robustness | mean > 0 after top-1% AND top-5% removal |
| HS14 | no subgroup rescue | pooled/all-state performance not used as support (structural rule; auto-pass if honored, documented) |

---

## 6. INFERENCE AND MULTIPLICITY (frozen)

- Day-clustered bootstrap, 20,000 iters, seed 20260826, 95% CI.
- **H1 permutation:** within-day circular rotation of the motif-label
  sequence (preserves each day's motif run-structure and outcome series,
  breaks their alignment), 20,000 iters — the RVMR-MOMENTUM precedent.
- **H2 permutation:** day-level sign-flip of `halfSessionAligned` over
  LOW days, 20,000 iters.
- **BH at M_binding = 2** over the two primary p-values (Δturn p,
  LOW-mean p). Exact once both exist; conservative bound `2p` if one runs
  first.
- **BH at M_cum = 8** reported, non-binding.

---

## 7. ALLOWED VERDICTS

**H1 ORDINAL-V-TURN:** CONFIRMED (hypothesis-specific historical) ·
CONFIRMED BUT SUB-COST · PARTIALLY CONFIRMED · PATH-SHAPE REDUNDANT (VT8
fails: shape adds nothing beyond last-leg magnitude) · UNSTABLE ·
FAILED · VOID · INSUFFICIENT DATA.

**H2 HALF-SESSION-LOW:** CONFIRMED (hypothesis-specific historical) ·
CONFIRMED BUT SUB-COST · PARTIALLY CONFIRMED · TAIL-DEPENDENT · UNSTABLE
· FAILED · VOID · INSUFFICIENT DATA.

**Decision rules (mechanical, precedence top-down):**

- **INSUFFICIENT DATA** — a minimum-n precondition fails.
- **VOID** — a defect in this document blocks execution (written
  diagnosis; slot stays spent).
- **CONFIRMED [BUT SUB-COST]** — every gate passes; sub-cost split by the
  actionable arm (V-turn arm for H1; LOW mean for H2) vs 0.87 pt.
- **PATH-SHAPE REDUNDANT** (H1 only) — VT3/VT4 pass but VT8 fails.
- **TAIL-DEPENDENT** (H2 only) — HS3/HS5 pass but HS13 fails.
- **PARTIALLY CONFIRMED** — sign, CI, permutation and BH pass, but a
  retention/stability/side condition fails (includes the ASYMMETRIC
  downgrade).
- **UNSTABLE** — core stats pass but year or month stability fails.
- **FAILED** — any of sign, CI, permutation, BH fails, or any
  non-passing pattern not captured above (failing gates named).

A failed candidate is **destroyed, not retuned**. No motif set, midday
time, session split, RVMR threshold, run-age bin, or window may change
after any outcome is seen. M stays 2.

---

## 8. NO CONTAMINATION FROM RVMR-MOMENTUM / NO NEW SEARCH

RVMR-MOMENTUM-V1's results (5m anti-persistence; no trend extension) did
**not** shape any definition here — motifs, run-age bins, half-session
hours, RVMR states and controls are read from the Wave-3 source, frozen
before that study's relevance is discussed. No Wave 4, no new motifs, no
alternative pattern lengths, midday times, thresholds, or session splits
are introduced. The two candidates are frozen exactly.

**If either survives:** it is frozen as a CONFIRMED (hypothesis-specific
historical) structural object — **not** a predictive candidate, **not** a
strategy. A separate preregistration would be required to turn it into
either, and prospective data would remain the only route to true
validation. RVMR-V1's certificate is unchanged on this evidence.

---

## 9. HOLDOUT-PROTECTION CONFIRMATION

- ORDINAL-V-TURN 2024+ outcome viewed: **NO**.
- HALF-SESSION-LOW 2024+ outcome viewed: **NO**.
- Only timestamp-only coverage counts were taken (§5.2 feasibility);
  they read no close ordinal, no return sign, no RVMR state, no outcome.
- MEMORY-PRED-V1 Lane A untouched; 0 rows ≥ 2026-08-26 will be consumed.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
