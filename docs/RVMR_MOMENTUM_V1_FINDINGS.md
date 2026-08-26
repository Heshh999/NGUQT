# RVMR-MOMENTUM-V1 — FINDINGS

# H1: FAILED (3/10). H2: TREND REAL — RVMR REDUNDANT (5/10).
# CASE 4: the simple trend-extension branch is CLOSED.

**DEVELOPMENT result on exposed data — not OOS, not prospective, not an
edge.** H1 and H2 executed once and scored separately; **no
combination**; neither result modified the other's definition. No
strategy simulated, no order submitted, nothing frozen modified.

Executed against the preregistration frozen at
`832faa61546ea5f41925f4a066dc2d5e18fc7c33`
(sha256 `210306f0ffa8f58fc8f200905677ffa51ae2ab648c15fe62bb29ed9222dbfdfe`,
2026-08-26T06:34:34+00:00).

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1–2. FREEZE VERIFICATION AND PROSPECTIVE-BOUNDARY AUDIT

All 17 Phase-0 checks passed before any outcome was read: prereg sha256
matches and is byte-identical to the freeze commit; RVMR spec unchanged
(T1 1.270, T2 2.335, W 1440); the four frozen formulas verified
(`mom5 = c[t]/c[t−5]−1`, `fut5 = c[t+5]/c[t]−1`, `trend30 =
c[t]/c[t−30]−1`, `fut15 = c[t+15]/c[t]−1`, all with strict `em`
contiguity); controls, buckets, tails, inference and both gate lists as
frozen. **Prospective boundary: max timestamp 2026-08-17 15:16 <
2026-08-26 00:00; rows at/after boundary = 0.** MEMORY-PRED-V1 Lane A
untouched.

**One disclosed engine fix (verdict logic only).** The first run's
verdict routine implemented the frozen REDUNDANT class ("the pooled
aligned return is **positive** with day-clustered CI excluding 0") as
two-sided CI exclusion, which wrongly fired "MOMENTUM REAL — RVMR
REDUNDANT" for H1 whose pooled aligned return is significantly
**negative**. The comparison was corrected to `CI lower bound > 0` and
the deterministic engine re-run; **every statistic reproduced
byte-identically** — only the H1 verdict line changed (to FAILED). No
threshold, statistic, seed or definition was touched. Both engine
versions' diffs are in the repository history.

## 3. CAUSAL AUDIT — all rows YES

Every predictor (momentum/trend, sign, `RB[t]`, score, `atr20(t)`,
magnitude, ToD) is available at the close of `t` or earlier; outcomes
(`fut`, MFE/MAE) live strictly in `t+1 … t+FW`. `em`-contiguity is
enforced in construction, so violations are structurally zero.

---

## 4–7. H1 — SHORT-HORIZON MOMENTUM: CORE RESULT

**2,417,349 events** (LOW 1,823,031 / MEDIUM 446,272 / HIGH 148,046);
minimum-n precondition PASS.

| state | n | aligned (bp) | median | 95% CI | P(cont) |
|---|---|---|---|---|---|
| LOW | 1,823,031 | **−0.0250** | −0.0873 | [−0.0363, −0.0136] | 0.4883 |
| MEDIUM | 446,272 | −0.0714 | −0.1355 | [−0.1129, −0.0294] | 0.4907 |
| HIGH | 148,046 | **−0.0690** | −0.1644 | [−0.1575, +0.0244] | 0.4914 |

> **Δ5 = HIGH − LOW = −0.0440 bp** (−0.082 NQ pts), CI [−0.1389,
> +0.0489], boot p 0.361, rotation-permutation p 0.306. **Wrong sign,
> nowhere near significant.**
>
> Continuation-probability contrast: **+0.31 pp**, CI [−0.03, +0.64].

The decisive fact is bigger than the failed contrast: **5-minute
momentum is anti-persistent in every RVMR state.** The pooled aligned
return is −0.0363 bp with CI [−0.0506, −0.0215] — significantly
negative. At 5 minutes NQ mean-reverts, and RVMR HIGH does not rescue
it (HIGH is just as negative as LOW). The tiny positive probability
contrast alongside uniformly negative means says the magnitudes reverse
even where the signs marginally persist.

## 8. H1 LONG/SHORT

| side | LOW | MEDIUM | HIGH | HIGH−LOW Δ |
|---|---|---|---|---|
| mom>0 | +0.0022 | −0.0343 | −0.0957 | **−0.0978** [−0.2551, +0.0616] |
| mom<0 | −0.0544 | −0.1073 | −0.0475 | +0.0069 [−0.1480, +0.1566] |

Both sides null; no ASYMMETRIC annotation applies (nothing survived to
annotate).

## 9–12. H1 ROBUSTNESS AND CONTROLS

- **Magnitude robustness** (frozen cuts 2.4392/6.2964 bp): ALL −0.0440,
  TOP50 −0.0315, TOP20 −0.0463 — negative at every magnitude.
- **|mom5| control (MO6):** standardised −0.0181 bp — still negative →
  FAIL.
- **ATR control (MO7):** standardised **+0.1110 bp** — sign flips
  positive under ATR standardisation (LOW-vol terciles show positive
  cells) while the raw is negative; the gate's letter is satisfied
  (std > 0 and ≥ 0.5×raw trivially, raw being negative), which is
  itself evidence of a sign-unstable non-effect. Retention percentages
  are meaningless against a negative base and are so labelled.
- **ToD (MO8):** 1 of 3 buckets positive → FAIL.

## 13–14. H1 BASELINES AND SCORE DIAGNOSTIC

- Unconditional: P(fut5 > 0) = 0.5097, mean +0.0265 bp (drift).
- **Momentum-only pooled aligned: −0.0363 bp, CI excludes 0 —
  5m momentum reversal is the real phenomenon here.**
- RVMR-only signed drift: LOW +0.027 / MED +0.038 / HIGH −0.016 bp
  (non-directional, as certified).
- Diagnostic regression: HIGH coefficient +0.0273 bp, CI [−0.0769,
  +0.1289], p 0.605 — nothing.
- **Score quintiles: −0.0137 → −0.0745 bp, monotonically MORE
  reversal as the RVMR score rises** — the exact opposite of the naive
  extension of MEMORY-PRED.

## 15–17. H1 YEARS, MONTHS, TAILS

Years with Δ5 > 0: **4 of 8** (2022, 2023, 2025, 2026 negative) → MO9
FAIL. Months: 40 of 86 positive, median −0.0506 bp. Tails: within-state
trims leave Δ5 at −0.0261/−0.0262 → MO10 FAIL (still negative).

## 18–20. H1 INFERENCE, GATES, VERDICT

Bootstrap 20,000/seed 20260826; FFT-exact circular-rotation permutation
(2,215 rotatable days), p 0.306.

| gate | result | | gate | result |
|---|---|---|---|---|
| MO1 causal | **PASS** | | MO6 \|mom\| control | FAIL |
| MO2 Δ5>0 | FAIL | | MO7 ATR control | PASS |
| MO3 CI | FAIL | | MO8 ToD | FAIL |
| MO4 BH+perm | FAIL | | MO9 years | FAIL |
| MO5 prob contrast | PASS | | MO10 tails | FAIL |

**3/10.** Pooled aligned significantly negative ⇒ the REDUNDANT class
cannot apply (momentum is not "real" in the frozen positive sense);
core gates fail ⇒

> ## H1 VERDICT: FAILED

---

## 21–24. H2 — BROADER TREND STATE: CORE RESULT

**2,356,465 events** (LOW 1,770,101 / MEDIUM 440,338 / HIGH 146,026);
precondition PASS.

| state | n | aligned (bp) | 95% CI | P(cont) |
|---|---|---|---|---|
| LOW | 1,770,101 | +0.0500 | [+0.0128, +0.0855] | 0.4932 |
| MEDIUM | 440,338 | +0.0307 | [−0.0824, +0.1417] | 0.4948 |
| HIGH | 146,026 | +0.1064 | [−0.1787, +0.3978] | 0.4946 |

> **Δ30 = +0.0563 bp** (+0.106 NQ pts), CI [−0.2358, +0.3451], boot p
> 0.700, permutation p 0.614. Probability contrast +0.14 pp. **Nothing.**

HIGH-arm aligned mean +0.1064 bp = +0.20 pts = 0.23× cost.

## 25. H2 LONG/SHORT

Uptrend Δ −0.0344 [−0.5100, +0.4412]; downtrend Δ +0.1518 [−0.2693,
+0.5572]. Both null. Note P(cont|uptrend) ≈ 0.51 vs P(cont|downtrend)
≈ 0.478 across all states — the pooled "trend continuation" leans on
the long side (NQ drift), exactly the artifact the frozen per-side
reporting exists to expose.

## 26–28. H2 MAGNITUDE CONTROL AND THE BINDING BASELINE

- **MT5 |trend30| control:** standardised **−0.0623 bp** — the sign
  flips negative once trend magnitude is matched → FAIL.
- **MT6 (BINDING) nonlinear baseline** (B = 1+|tr|+|tr|²+side+
  side×|tr|+atrRel+ToD; A = B+MED+HIGH): HIGH coefficient **+0.1007
  bp, day-clustered CI [−0.1923, +0.4100], p 0.522** → FAIL. ΔR²
  +0.000007.
- Per-year HIGH coefficient flips sign: +0.61, −0.10, +0.01, +0.34,
  −0.11, +0.57, +0.31, −0.14 — noise.

## 29–32. H2 ATR, TOD, BASELINES, SCORE

ATR terciles: +0.376*/+0.124/−0.041 (only the low-vol cell excludes 0);
ATR-standardised +0.1793 → MT7 PASS (a sign-unstable pass, reported as
such). ToD: 2 of 3 positive → MT8 PASS. Baselines: unconditional
P(fut15>0) 0.5149; **trend-only pooled aligned +0.0499 bp, CI
[+0.0001, +0.0987]** — marginally real and economically trivial;
RVMR-only drift LOW +0.078/MED +0.130/HIGH −0.037. Score quintiles:
+0.027 → +0.074 → +0.052 — non-monotone, flat.

## 33–36. H2 YEARS, MONTHS, TAILS, INFERENCE

Years with Δ30 > 0: **3 of 8** → MT9 FAIL (yearly Δ swings ±0.8 bp with
no pattern). Months: 42/86 positive, median −0.0335. Tails: within-state
trims +0.1133/+0.1107 → MT10 PASS. Permutation p 0.614 (2,214 rotatable
days).

## 37–38. H2 GATES AND VERDICT

| gate | result | | gate | result |
|---|---|---|---|---|
| MT1 causal | **PASS** | | MT6 nonlinear baseline (BINDING) | **FAIL** |
| MT2 Δ30>0 | PASS | | MT7 ATR control | PASS |
| MT3 CI | FAIL | | MT8 ToD | PASS |
| MT4 BH+perm | FAIL | | MT9 years | FAIL |
| MT5 \|trend\| control | **FAIL** | | MT10 tails | PASS |

**5/10.** The frozen REDUNDANT class applies mechanically: the pooled
trend-aligned return is positive with CI excluding 0 (barely), and
MT5/MT6 fail. Disclosed honestly: MT3/MT4 also fail, so "FAILED"
describes the RVMR contrast equally well — the frozen evaluation order
(survival → REDUNDANT → UNSTABLE → FAILED) selects REDUNDANT, and
substantively the two statements coincide here: *there is no RVMR
effect on trend persistence; what little trend persistence exists
(+0.05 bp, drift-leaning) owes nothing to RVMR.*

> ## H2 VERDICT: TREND REAL — RVMR REDUNDANT

---

## 39–40. MULTIPLICITY

| | raw p | BH q (M=2, binding) | BH q (M_cum=6, non-binding, exact) |
|---|---|---|---|
| H1 | 0.36080 | 0.70020 | 0.43296 |
| H2 | 0.70020 | 0.70020 | 0.70020 |

Nothing near any threshold; the sensitivity changed nothing.

## 41. JOINT INTERPRETATION — CASE 4

Neither hypothesis survives.

> **MEMORY-PRED is a highly local 1-minute memory phenomenon. It does
> not extend into 5-minute momentum or 30-minute trend persistence.
> The simple trend-extension branch is CLOSED.** No timeframe search
> may be conducted to rescue it.

The wider evidence now fits one coherent picture, assembled entirely
from frozen results:

1. At **1 minute**, RVMR state flips the sign of return memory
   (MEMORY-PRED, 10/10, sub-cost).
2. Wave 3's run hazard shows that continuation information **decays
   with run age and is spent by minute ~3** — steepest decay in HIGH.
3. Therefore a **5-minute** momentum window — mostly aged runs — shows
   *anti*-persistence everywhere (this study, pooled −0.0363 bp,
   significant), and the RVMR score correlates with **more** reversal,
   not less.
4. At **30m→15m** nothing directional survives controls at all.

The 1m effect and the 5m anti-persistence are not in conflict; the
second is what the first plus hazard decay predicts.

## 42. FUTURE RESEARCH STATUS

- **No candidate object is frozen from this study.** Both hypotheses
  are destroyed, not retuned. `RVMR-TREND-MOMENTUM-COMBINE-V1` is
  dead — its precondition (both survive) failed.
- MEMORY-PRED-V1's Lane-A prospective confirmation (start 2026-08-26,
  minimums unchanged) proceeds exactly as frozen.
- The programme's open leads remain the Wave-3 candidates
  (ORDINAL-V-TURN; HALF-SESSION-LOW), which are *not* simple
  trailing-return momentum and are untouched by this closure.
- Cumulative promotable ledger: **8 slots spent or committed**
  (SHOCK-CONT, MONDAY-RTH, MEMPRED, HARU, MOM-H1, MOM-H2 spent; Wave-3
  candidates 7–8 reserved if ever promoted).

## 43–45. HASHES, COMMIT, TREE

| artifact | sha256 |
|---|---|
| `docs/RVMR_MOMENTUM_V1_PREREGISTRATION.md` | `210306f0ffa8f58fc8f200905677ffa51ae2ab648c15fe62bb29ed9222dbfdfe` |
| `analysis/rvmr/rvmr_spec.py` | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` |

Engine `analysis/rvmrmom/mom_run.py` and raw output `MOM_OUTPUT.txt`
committed with this document; working tree clean at execution start
(HEAD `0ba46c1f…`). Commit id recorded by the commit carrying this file.

---

## CLOSING NOTE

This is the cleanest kind of negative result: a pre-frozen, two-gate
family executed once, with the interesting discovery arriving as a
by-product — **NQ 5-minute momentum mean-reverts, significantly, in
every volatility state**, and higher RVMR scores mean *more* reversal
at that horizon, not less. The memory effect is real for one minute and
one minute only. Direction at multi-minute horizons will not come from
trailing-return momentum conditioned on RVMR; the frozen record now
says so twice over.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
