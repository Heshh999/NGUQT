# RVMR-BANDS-V1 — HISTORICAL CALIBRATION FINDINGS

## **HISTORICAL VERDICT (frozen rule, no discretion):**

> **BAND CALIBRATION ITSELF IS NOT RELIABLE**

All three RVMR models beat the ATR-only benchmark with day-clustered
CIs excluding zero — and **every model, the ATR-only benchmark
included, failed the frozen calibration tolerances**, with coverage
~10 pp low at P50, ~8 pp low at P80 and ~3.5 pp low at P95. Under the
frozen deterministic selection rule (§30.4 of the pre-registration):
no RVMR model passes all sixteen conditions, and Model A itself fails
calibration → the verdict above. **No model is frozen. No forward
logger is created. Nothing is retuned.**

Everything in this document is **HISTORICAL CALIBRATION EVIDENCE** —
not OOS, not prospective, not forward-validated.

Raw output: `analysis/rvmr_bands/BANDS_OUTPUT.txt`.

---

## 1. Freeze verification

| check | result |
|---|---|
| prereg sha256 at commit `9074d0c` | `ad3e21e13e20267a81bca16bb8dd8fd5dd1181389cd63a1e674d89661d7ecc7d` — **match** |
| working-tree copy | identical (0-line diff) |
| HEAD at execution start | `9074d0cb75b782f213cdeb8942d7dc51f5a88751`, tree clean |

## 2. Source provenance (all hashes matched prereg §1)

`rvmr_spec.py` `e348f035a9209540` · `rvmr_run.py` `8743161d6fb5b04e` ·
`val_lib.py` `7bde837a9c8a9369` · `track_b.py` `cfc81754c8fddd29` ·
VALIDATION prereg `025598ad685e617c` · VALIDATION findings
`cb565f9490203518` · `rvmr_prospective.py` `7397ad3d4edeb2de`.

## 3. Parity audit — PASS before any band number

- **Gate 1:** feature parity vs frozen `rvmr_run.features` — 510,309
  bars, **0 mismatches** on every column (i, day, mod, rb, vb, rr, vr,
  abs5–abs60).
- **Gate 2:** ATR quintile boundaries **regenerated from the frozen
  calendar-2019 rule** (not hardcoded): n = 40,354 →
  0.9588 / 1.2187 / 1.5612 / 2.0508 — exact match to the Track B
  record.
- ToD bins tile the eligible universe exactly (mod ∈ [570, 900];
  AFTERNOON inclusive at 900 per prereg §11).

## 4. Historical universe

593,190 eligible bars, 1,829 days, 2019-07-08 → 2026-08-17.
**Scored: 511,616 forecasts over 1,578 days** (≥ 2020-07-01).
Unavailable forecasts: **0** (the (ATRq) last-resort cell always held
≥ MIN_CELL_N after the first training year).

## 5–6. Rolling origin and monthly refresh audit

Expanding window exactly as frozen: **74 monthly refreshes**;
calibration N grew 81,574 → 589,593; tables for month M contain only
bars with sessionDate < M-01 (append-after-forecast ordering; every
eligible stamp matures intra-day, so the `t+60min < M` maturation rule
reduces to strict prior-session membership). No random split, no
future-year leakage.

## 7–10. Model definitions (as frozen)

A = ATRq × ToD · B = A-cell × VOLUME state · C = A-cell × RANGE state ·
D = A-cell × RANGE × VOLUME. Type-7 empirical quantiles;
MIN_CELL_N = 400 and ≥ 20 distinct days; frozen fallback ladders.

## 11. Cell / fallback counts

Level-0 usage: A 100% · **B 99.21%** · C 99.29% · D 96.30% (reasons:
cell-N shortfalls only; no day-count shortfalls at L0). All gates on
fallback (≥70% L0) pass easily.

## 12–17. Calibration — the decisive failure

Coverage (%, target 50 / 80 / 95; tolerances ±3.0 / ±2.5 / ±1.5 pp):

| model | 15-P50 | 15-P80 | 15-P95 | 30-P50 | 30-P80 | 30-P95 | 60-P50 | 60-P80 | 60-P95 |
|---|---|---|---|---|---|---|---|---|---|
| A | 39.64 | 71.67 | 91.62 | 39.60 | 71.78 | 91.60 | 39.44 | 71.74 | 91.71 |
| B | 39.72 | 71.74 | 91.57 | 39.65 | 71.81 | 91.54 | 39.49 | 71.79 | 91.68 |
| C | 39.65 | 71.65 | 91.60 | 39.57 | 71.76 | 91.55 | 39.45 | 71.76 | 91.67 |
| D | 39.73 | 71.66 | 91.47 | 39.67 | 71.75 | 91.47 | 39.51 | 71.74 | 91.60 |

**Worst errors ≈ −10.5 pp (P50), −8.3 pp (P80), −3.5 pp (P95)** — far
outside tolerance for every model at every horizon, and the
day-clustered CIs do not rescue any cell.

**Why (diagnosis, not repair):** NQ's absolute point volatility is
non-stationary upward across the scored era — Model A's combined
pinball rises 6.98 (2020) → 15.78 (2026) and B's median predicted
P80@30m rises only 30.50 → 41.25 while realized movement grew faster.
An expanding window anchored in 2020-vintage points systematically
under-predicts later years: per-year P80@30m coverage runs 84.7% in
2023 but only **56.2% in 2026**. The level of point-denominated bands
is not stable enough for a frozen expanding-window design, regardless
of which conditioning variables are added. That is a finding about the
band framework, and the frozen verdict list contains exactly the right
name for it.

## 18. Pinball table (mean loss per forecast)

| model | combined | 15-P50 | 15-P80 | 15-P95 | 30-P50 | 30-P80 | 30-P95 | 60-P50 | 60-P80 | 60-P95 |
|---|---|---|---|---|---|---|---|---|---|---|
| A | 9.3850 | 8.0652 | 7.6357 | 3.8130 | 11.2375 | 10.6399 | 5.3304 | 15.5541 | 14.7355 | 7.4533 |
| **B** | **9.3596** | 8.0464 | 7.6053 | 3.8067 | 11.2100 | 10.5991 | 5.3210 | 15.5185 | 14.6890 | 7.4409 |
| C | 9.3675 | 8.0518 | 7.6170 | 3.8044 | 11.2213 | 10.6130 | 5.3181 | 15.5348 | 14.7096 | 7.4378 |
| D | 9.3604 | 8.0430 | 7.6061 | 3.8099 | 11.2083 | 10.5988 | 5.3247 | 15.5169 | 14.6899 | 7.4458 |

## 19. Sharpness (median predicted band; cap 110% of A)

All models within 102% of A everywhere (worst ratio B/D 1.020, C
1.003). No model widened its way to a score. Gate 8 passes for all.

## 20–24. Paired comparisons (day-clustered bootstrap, 20,000 iters, seed 20260825)

| pair | mean diff | 95% CI | relative | CI excl 0 |
|---|---|---|---|---|
| **B − A** | **−0.02533** | [−0.03284, −0.01779] | **+0.270%** | **YES** |
| C − A | −0.01743 | [−0.02314, −0.01205] | +0.186% | YES |
| D − A | −0.02458 | [−0.03348, −0.01585] | +0.262% | YES |
| **D − B** | +0.00075 | [−0.00246, +0.00384] | −0.008% | NO |
| C − B | +0.00790 | [+0.00050, +0.01537] | −0.084% (B better) | YES |

RVMR's improvement is **real (CIs exclude zero) but small — roughly a
quarter of the frozen 1.0% materiality bar.** D adds nothing over B
(−0.008%), confirming Track B's finding that RANGE is absorbed by
VOLUME. C is significantly *worse* than B.

**Honesty caveat (secondary diagnostic, reported as declared):** on the
non-overlapping sample (mod ≡ 570 mod H), B vs A REVERSES sign
(−0.715% / −1.167% / −1.707% at 15/30/60m on n = 35,578 / 18,571 /
9,286). Primary inference remains the day-clustered pooled result as
frozen, but the pooled +0.27% clearly cannot be treated as robust when
the sparse independent-ish subsample disagrees in sign.

## 25. Year stability

B: 5/7 years positive (2020, 2021 negative), best-year(2026)-removed
+0.220% — gate PASS. C: 7/7, PASS. D: 5/7, PASS. Improvements grow
monotonically with the era's volatility (2026: B +0.513%).

## 26. Regime destruction

COVID-2020H2 B −0.239% · 2021 −0.079% · 2022 +0.228% · 2023–24
+0.263% · 2025–26 +0.476%. Value concentrated in the recent
high-volatility era.

## 27. ToD destruction

OPEN +0.577% · MIDMORN +0.208% · MIDDAY +0.063% · AFTERNOON +0.214%
(B vs A). Strongest at the open; positive everywhere; no bucket
removed. State diagnostics: B's gain concentrates in VOLUME-HIGH
(+0.980%) and is negative in VOLUME-LOW (−1.548%); by ATR quintile the
largest gain is q0 (+1.171%).

## 28–29. Tail destruction

Drop top-1%: B +0.200%, C +0.110%, D +0.149% — all survive. Drop
top-5%: B +0.058%, C +0.049%, **D −0.014% (FAIL condition 13)**.

## 30. Fallback audit — §11 above; all pass.

## 31. Promotion gate (full table in raw output)

| condition | B | C | D |
|---|---|---|---|
| 3 P50 calibration | **FAIL −10.51 pp** | FAIL | FAIL |
| 4 P80 calibration | **FAIL −8.26 pp** | FAIL | FAIL |
| 5 P95 calibration | **FAIL −3.46 pp** | FAIL | FAIL |
| 7 materiality ≥ 1.0% | **FAIL +0.270%** | FAIL +0.186% | FAIL +0.262% |
| 13 top-5% removal | PASS | PASS | **FAIL** |
| all other 11 conditions | PASS | PASS | PASS |
| **ALL SIXTEEN** | **FAIL** | **FAIL** | **FAIL** |

## 32. Deterministic selection

D does not materially beat B (−0.008%). No model passes → rule 4:
Model A calibrated? **NO** → **BAND CALIBRATION ITSELF IS NOT
RELIABLE**. No subjective override.

## 33–36. Verdict, winner, hashes

Verdict as stated. **No winning model. No `RVMR_BANDS_V1_SPEC.md` is
created.** Implementation: `analysis/rvmr_bands/bands_run.py` (hash
recorded in the commit below).

## 37–38. Commit and tree — recorded in the accompanying reply.

---

## What was NOT done

No retuning. No tolerance widening. No window redesign. No new
quantile method. No normalized-target variant. No time-bin change. No
forward logger. The diagnosis in §12–17 names the failure mechanism;
fixing it would be a **new V2 pre-registration**, not a repair of V1.

**THE FORWARD RVMR LOGGER CONTINUES UNCHANGED. OFH13_PROSPECTIVE_V1
REMAINS UNTOUCHED. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
