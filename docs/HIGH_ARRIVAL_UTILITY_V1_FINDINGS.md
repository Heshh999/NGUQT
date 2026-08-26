# HIGH-ARRIVAL-UTILITY-V1 (H2) — FINDINGS

# VERDICT: STATE-ARRIVAL LAW REAL BUT FORECAST-REDUNDANT — 8/10 gates, HA6 (binding) FAILED

**This is a DEVELOPMENT result on EXPOSED data — not out-of-sample, not
prospective, not confirmed.** H2 only. **H1 was not used and the two
were not combined.** No strategy simulated, no order submitted, nothing
frozen modified.

Executed once against the preregistration frozen at
`cdfcb3148513264ba58a7880ea794c4baa72f1e4`
(sha256 `afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8`,
2026-08-25T22:45:04+00:00). No threshold, constant or definition was
changed at any point; the engine ran to completion on its first launch.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1. FREEZE VERIFICATION (Phase 0 — all checks passed before any H2 outcome)

| # | check | result |
|---|---|---|
| 1–2 | preregistration sha256 + commit | `afac484b…` **MATCHES**; byte-identical to `cdfcb314…` |
| 3 | RVMR spec | T1 1.270, T2 2.335, W 1440; causality probes **EXACT** at 5 points |
| 4 | discovery return-bin cutpoints | rebuilt from 99,308 discovery pairs; max \|Δ\| **4.94e-11** vs the frozen 10-dp constants (tolerance 5e-11) — the tolerance lesson from ANOMALY-CONFIRM applied from the start |
| 5 | discovery HIGH-arrival probabilities | verbatim leverage scan reproduced all ten: max \|Δ\| **4.73e-05** vs the 4-dp frozen constants (tolerance 5e-5) |
| 6 | propensity groups | cuts 0.30/0.40 derive exactly {d3,d4,d5,d6} / {d2,d7,d8} / {d1,d9,d0} |
| 7 | outcome | `move30 = (max high[i1+1…i1+30] − min low[…]) / close[i1]` |
| 8 | B2 baseline | B1 + \|shock\|² + down + down×\|shock\|; A = B2 + propensity |
| 9–11 | controls, calibration rules, HA1–HA10 | as frozen |
| 12 | prospective start | 2026-08-26; **rows at/after it in the data: 0** |

Engine pre-computation choices (tail-trim scope = within-group gate,
ToD bucket = decision bar `i1`, rr60/logv60 definitions, numpy
multinomial day-weights for the coefficient bootstrap under seed
20260825, exact BH now that all family p-values exist) were recorded in
the engine header **before any result existed**, following the H1
precedent.

## 2. SOURCE LINEAGE

| artifact | sha256 |
|---|---|
| `docs/RVMR_STRUCTURE_TO_PREDICTION_V1_PREREGISTRATION.md` | `afac484b3d75a7bce9533a0fd8304a66fd653587eea5f20e4dac794a0898dbb8` |
| `analysis/anomaly/scan2_run.py` (LEVERAGE-V origin) | `6c52693ff4a44fcd7090e9bfd82869196572822ef137547b4e42b9a47f9fd747` |
| `analysis/anomaly/confirm_run.py` (holdout replication) | `5ae5e3d4645b2452cbfb1723ef731819c68cc07f0cb92e19f206cc8be22623b8` |
| `analysis/anomaly/confirm_freeze.py` (frozen constants origin) | `507c63687985b94feb1eb720ddd058ed983fc07fd9ce2781a85ec40087387f80` |
| `analysis/rvmr/rvmr_spec.py` | `e348f035a920954054a2b3e76ac0f0363b5502ccb2c872a2276d6236a152cd62` |

Engine: `analysis/haru/haru_run.py`; raw output
`analysis/haru/HARU_OUTPUT.txt`.

## 3. CAUSAL AUDIT — every row YES

All twelve rows (block return, decile, propensity, group, down flag,
atrRel, RVMR score, current state, ToD, rr60/logv60, and both outcomes)
verified causal: every predictor is available at the close of `i1` or
earlier; the outcome window is strictly `i1+1 … i1+30`. The propensity
is the frozen ten-constant lookup — **never re-estimated, in any era, at
any event.** Zero post-prospective rows used.

## 4–5. SAMPLE AND LOOKUP PARITY

163,779 frozen 15m blocks → skipped: 5,277 (forward window not
contiguous), 56 (state/ATR unavailable), 2 (end of data), 0 prospective.

> **ELIGIBLE EVENTS 158,444** — P-LOW 63,290 (39.9%) · P-MID 47,793
> (30.2%) · P-HIGH 47,361 (29.9%). All minimum-n preconditions met
> (≥100,000 total; every group ≥20,000).

Decile occupancy under the frozen cutpoints: 15,585–16,054 per bin.

## 6–11. PRIMARY RESULT

| group | n | mean move30 (bp) | median (bp) | 95% CI (bp) |
|---|---|---|---|---|
| P-LOW | 63,290 | **14.835** | 10.803 | [14.555, 15.119] |
| P-MID | 47,793 | **19.598** | 15.075 | [19.285, 19.922] |
| P-HIGH | 47,361 | **33.236** | 26.314 | [32.337, 34.191] |

- **Monotone P-LOW < P-MID < P-HIGH: YES.**
- **C = +18.401 bp**, CI [+17.582, +19.284], boot p **0.00005** (floor)
- +124.0% of the P-LOW mean; ≈ **+34.5 NQ points** of realised 30-min
  range at the mean close (18,724)
- Permutation (within-day group-label shuffle, 20,000 iters): **0
  exceedances**, p = 0.00005
- Stability is total: **8/8 years**, **86/86 months** positive, best
  month +30.1 bp, *worst* month still **+5.1 bp**
- Within-group tail trims: +17.827 / +16.583 bp (pooled: +16.376 /
  +13.056, with 88.2% / 84.4% of removed events being P-HIGH — the
  composition effect the pre-committed gate scope anticipated)

The raw relationship could not be stronger. **And that is not the
question H2 asked.**

## 12–15. THE DECISIVE TEST — B2 INCREMENTAL VALUE (HA6, binding)

B1 = `move30 ~ |shock| + atrRel + RVMR score + ToD dummies + rr60 +
logv60`. B2 = B1 + `|shock|²` + `down` + `down×|shock|`.
A = B2 + `propensity` (single scalar, frozen lookup).

| model | R² |
|---|---|
| B1 | 0.576099 |
| B2 | 0.577108 |
| A = B2 + propensity | 0.577176 |
| **ΔR² (A vs B2)** | **+0.000068** |

- Full-sample propensity coefficient: **+2.3977 bp per unit propensity**
  → model-implied *adjusted* P-HIGH−P-LOW gap: **+0.683 bp** (versus
  +18.401 bp raw — 96% of the raw contrast is explained by B2's
  shock/volatility terms)
- Day-clustered bootstrap (20,000 multinomial day-weights, PCG64 seed
  20260825): **CI [−1.2088, +4.7896]**, two-sided **p = 0.286**
- Per-year point estimates of the coefficient flip sign: −8.6, +2.1,
  +2.5, −3.5, −2.8, −0.4, −0.5, −2.0 — no stable incremental signal in
  any direction

> **HA6 FAILS.** Once a flexible function of the current shock's size
> and sign is in the model, the frozen HIGH-arrival propensity adds
> nothing statistically distinguishable from zero. (The ΔR² > 0 leg is
> near-tautological for in-sample OLS and is reported as such; the CI
> is the informative leg, exactly as the engine noted before results.)

## 16. ATR CONTROL (HA5)

| ATR tercile | n P-HIGH | n P-LOW | C (bp) | 95% CI |
|---|---|---|---|---|
| 0 (low vol) | 2,509 | 36,051 | +2.657 | [+2.374, +2.947] |
| 1 | 13,352 | 18,637 | +1.567 | [+1.309, +1.820] |
| 2 (high vol) | 31,500 | 8,602 | +7.118 | [+6.205, +8.127] |

Leg 1 passes (3/3 positive) — but note the within-tercile contrasts are
**one order of magnitude smaller** than the raw +18.4 bp: most of the
raw contrast is cross-ATR composition.

**C_matched (27-cell ATR × |shock| × ToD, common weight): +1.049 bp =
5.7% of C_raw** — far below the frozen 50% requirement. Only **8 of 27
cells** had ≥30 events on both sides, covering **14.8%** of P-HIGH ∪
P-LOW events. **HA5 FAILS.**

The |shock| tercile slices state the reason in the bluntest possible
form:

| \|shock\| tercile | n P-HIGH | n P-LOW | C |
|---|---|---|---|
| 0 (small) | **0** | 52,815 | DEGENERATE |
| 1 (middle) | 5,964 | 10,475 | +5.650 bp [+5.127, +6.166] |
| 2 (large) | 41,397 | **0** | DEGENERATE |

**The propensity is a function of the shock.** Small shocks are never
P-HIGH; large shocks are never P-LOW. Matching has almost no common
support — precisely the identification problem §5.5 of the
preregistration stated in advance, and precisely why the B2 regression
was made the binding test.

## 17. CURRENT-RVMR CONTROL

The frozen instrument is the RVMR score covariate inside B1/B2 (present
in every model above). Directive-requested slice diagnostic (non-gated):

| RB[i1] | n P-HIGH | n P-LOW | C (bp) | 95% CI |
|---|---|---|---|---|
| LOW | 27,176 | 55,605 | +14.881 | [+14.037, +15.830] |
| MEDIUM | 14,850 | 6,585 | +13.587 | [+12.546, +14.727] |
| HIGH | 5,335 | 1,100 | +11.779 | [+10.008, +13.500] |

The raw contrast **survives conditioning on the current RVMR state** —
the propensity is not merely restating "RVMR is already elevated." What
it *is* restating is the shock itself (§16).

## 18–20. TIME-OF-DAY, RANGE, VOLUME

- ToD (bucket of decision bar): OVERNIGHT +13.811, RTH_AM +15.724,
  RTH_PM +15.058 bp — **3/3 positive, HA7 PASSES.** No narrower window
  examined.
- Recent range (rr60) and recent volume (logv60) are covariates in
  B1/B2 as frozen; their inclusion is part of why B2's R² reaches 0.577.

## 21–23. CALIBRATION (HA8 — a genuine PASS)

Observed overall HIGH-arrival frequency: 0.3502.

| group | n | predicted | observed | \|err\| |
|---|---|---|---|---|
| P-LOW | 63,290 | 0.2549 | 0.2334 | 0.0215 |
| P-MID | 47,793 | 0.3426 | 0.3224 | 0.0202 |
| P-HIGH | 47,361 | 0.5399 | 0.5345 | **0.0054** |

**Brier(frozen propensity) 0.209153 < Brier(constant base rate)
0.227571.** All ten decile-level reliability errors ≤ 0.025 (d9:
predicted 0.5562, observed 0.5554). No calibrator of any kind was
fitted.

A 2019–2023 lookup of ten constants predicts 2019–2026 HIGH-arrival
frequencies to within ~2 percentage points per group. **The transition
law itself is extraordinarily stable.**

## 24. DOWNSIDE ASYMMETRY (secondary, never gated) — REAPPEARS

Band-matched (ten frozen |shock| bands):

> **P(HIGH | negative shock) − P(HIGH | positive shock) = +0.0336**,
> CI [+0.0288, +0.0385] — positive in **all 8 years** (range +0.019 to
> +0.050), largest in the highest bands (band 9: +0.083).
> Band-matched move30(neg) − move30(pos) = **+1.491 bp**.

Down-shocks of equal size activate the HIGH state more often and are
followed by slightly larger movement. Activity-state behaviour only; no
directional claim is derived, as frozen.

## 25–27. YEAR / MONTH / TAIL DESTRUCTION

- **Years: 8/8** monotone AND C > 0 (range +11.4 to +22.0 bp). HA9
  PASSES. Per-year β_prop (reported): sign-unstable, mostly negative.
- **Months: 86 of 86 positive** — the raw contrast never had a negative
  month in seven years. Median +12.669 bp.
- **Tails: HA10 PASSES** — within-group trims leave +17.827 (1%) and
  +16.583 bp (5%). Pooled trims (+16.376 / +13.056 bp) stay positive
  too; their removed sets are 88%/84% P-HIGH, the disclosed composition
  effect.

## 28–31. INFERENCE AND MULTIPLICITY

- Day-clustered bootstrap (cluster = `day[i1+1]`), 20,000 iterations,
  seed 20260825 throughout; scalar bootstraps `random.Random`, the
  coefficient bootstrap numpy-multinomial (disclosed, statistically
  identical).
- Permutation: 0 exceedances in 20,000 → p = 0.00005.
- **BH at M_binding = 2, now EXACT** (both primary p-values exist):
  H1 q = 0.00005, H2 q = 0.00005.
- **BH at M_cum = 4, exact, non-binding** (family {SHOCK-CONT 0.10050,
  MONDAY-RTH 0.03570, H1 0.00005, H2 0.00005}): H2 q = 0.00010. Changed
  no verdict.

## 32. HA1–HA10

| # | requirement | measured | |
|---|---|---|---|
| pre | n floors | 158,444 total; 63,290/47,793/47,361 | **PASS** |
| HA1 | no leakage | frozen lookup; predictors at close of i1; 0 post-start rows; audit all YES | **PASS** |
| HA2 | monotone ordering | 14.835 < 19.598 < 33.236 | **PASS** |
| HA3 | CI on C excludes 0 | +18.401, [+17.582, +19.284] | **PASS** |
| HA4 | BH q ≤ .05 AND perm p ≤ .05 | 0.00005 / 0.00005 | **PASS** |
| HA5 | ATR terciles + C_matched ≥ 0.5 C_raw | 3/3, but matched +1.049 vs raw +18.401 (5.7%) | **FAIL** |
| **HA6** | **B2-incremental propensity (BINDING)** | coef +2.3977, **CI [−1.2088, +4.7896]**, p 0.286, ΔR² +0.000068 | **FAIL** |
| HA7 | ToD buckets | 3 of 3 | **PASS** |
| HA8 | calibration | max group err 0.0215; Brier 0.2092 < 0.2276 | **PASS** |
| HA9 | year stability | 8 of 8 | **PASS** |
| HA10 | tail robustness | +17.827 / +16.583 bp | **PASS** |

> ### HA PASSED 8 / 10 — and the two failures are the two that decide

## 33. EXACT VERDICT — the frozen interpretation table applied

- **CASE A** (raw relationship + survives B2) — does not apply: HA6
  failed.
- **CASE B** (LEVERAGE-V replicates, raw propensity groups predict
  move30, **but B2 explains the relationship**) — **applies exactly.**
  HA2/HA3 pass; HA6 fails; the frozen §7 rule maps this to one verdict,
  and FORECAST-REDUNDANT outranks every survival label by frozen
  precedence.
- **CASE C** (no reliable ordering) — does not apply.

> # STATE-ARRIVAL LAW REAL BUT FORECAST-REDUNDANT

Plainly: the frozen LEVERAGE-V propensity predicts future movement
enormously well **because it memorises the size and sign of the current
shock, and the current shock predicts future movement.** Conditioning on
a flexible function of that shock (B2) collapses the +18.4 bp raw
contrast to a model-implied +0.68 bp with a CI spanning zero, and
matching collapses it to +1.05 bp on the 15% of events where matching is
even possible. There is no evidence of incremental forecast content.

What remains true, and is not diminished by this verdict: the transition
law is real, stable across 8/8 years and 86/86 months, calibrated to
within ~2 pp from a five-year-old ten-constant lookup, and carries a
genuine, replicated downside asymmetry. **It is structural knowledge
about how the RVMR state arrives — not a forecasting tool beyond what
the shock already tells you.**

## 34. PROSPECTIVE STATUS

- Frozen prospective start 2026-08-26 00:00:00 ET; **0 rows** at or
  after it exist in the data — nothing consumed, nothing to preserve
  beyond what already stands.
- H2 did **not** survive, so no prospective confirmation of H2 is
  scheduled. The frozen H2 minimums (≥60 days, ≥2,000 blocks, ≥400 per
  group) are moot for this candidate.
- H1's candidate freeze and its prospective requirements are untouched
  by this run.

## 35. CANDIDATE FREEZE

**NONE — not authorized.** The verdict is not a survival class.
LEVERAGE-V remains what ANOMALY-CONFIRM left it: a replicated,
non-promotable structural diagnostic — now with the added, honestly
earned annotation that its forecast utility is **redundant with the
current shock**. No `HIGH-ARRIVAL-UTILITY` candidate object is created.
**H1 and H2 are not combined**; whether an `RVMR-STATE-MACHINE-V1` is
ever preregistered would now require H2's redundancy to be confronted in
its design, since only H1 survived. RVMR-V1's certificate is
**unchanged**; `rvmr_spec.py`, `rvmr_run.py`, the forward logger, the
ledgers, OFH13/OFH14 and every NinjaTrader host remain byte-for-byte
unmodified. A failed hypothesis is destroyed, not retuned.

## 36–38. HASHES, COMMIT, TREE

Engine `analysis/haru/haru_run.py` and raw output `HARU_OUTPUT.txt`
committed with this document; the carrying commit records the ids.
Working tree verified clean at execution start (0 lines, HEAD
`db0233a67ea5561e9debc35887871541368d5d88`).

---

## CLOSING NOTE

H2 was designed so that a spectacular raw result could still fail, and
that is exactly what happened: +18.4 bp, p at the floor, 86 of 86 months
positive — and none of it is *new* information. The preregistration
called the identification problem before any number existed
("propensity ≈ f(|shock|, sign(shock)) … an 'incremental value' test
against a linear control would mostly be measuring functional form"),
made the flexible-shock baseline binding, and the baseline won.

The programme's ledger after RVMR-STRUCTURE-TO-PREDICTION-V1: **H1
survived sub-cost as a development candidate awaiting prospective data;
H2's law is real but forecast-redundant.** Nothing is tradeable, nothing
is combined, and nothing frozen moved.

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
