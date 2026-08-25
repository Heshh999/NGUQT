# RVMR-BANDS-V1 — HISTORICAL CALIBRATION PRE-REGISTRATION

**PREREGISTRATION ONLY. The historical study has NOT been run.** At the
moment this document was committed, **zero** RVMR-BANDS-V1 performance
numbers existed: no P50/P80/P95 value, no coverage figure, no pinball
loss, no model ranking, no year/time-of-day/tail result had been
calculated for any model, including the ATR-only benchmark. Only source
code, specifications, schemas and feasibility row counts were inspected.

**Sequencing rule this document enforces:** the prospective-validation
directive was previously refused because the historical model did not
exist; the mirror error — letting historical results exist before the
historical test is frozen — is prevented here. Define the test, freeze
the test, hash the test, commit the test. Only then look at numbers.

No forward logger is created by this study. No trading research of any
kind occurs here. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

# 1. AUTHORITATIVE SOURCES (read from repository, not reconstructed)

| source | path | sha256 (16) | commit |
|---|---|---|---|
| frozen RVMR-V1 spec | `analysis/rvmr/rvmr_spec.py` | `e348f035a9209540` | `84933d2` |
| frozen RVMR-V1 engine | `analysis/rvmr/rvmr_run.py` | `8743161d6fb5b04e` | `9d14dfa` |
| VALIDATION-V1 prereg | `docs/RVMR_VALIDATION_V1_PREREGISTRATION.md` | `025598ad685e617c` | `531759c` |
| VALIDATION-V1 findings | `docs/RVMR_VALIDATION_V1_FINDINGS.md` | `cb565f9490203518` | `02a9693` |
| Track B ATR-state impl. | `analysis/rvmr_val/val_lib.py` / `track_b.py` | `7bde837a9c8a9369` / `cfc81754c8fddd29` | `02a9693` |
| canonical NQ loader | `rvmr_run.load_bars` (STAMP_SHIFT = 0) | in engine above | — |
| forward-logger reference | `analysis/rvmr/rvmr_prospective.py` | `7397ad3d4edeb2de` | `68ed951` |

The forward logger is referenced **only** so a future (post-promotion)
shadow logger can be schema-compatible. It is not touched.

# 2. SETTLED PROVENANCE (from source; no new research)

- **RANGE-REGIME-V1** = `trailing_ratio(high − low)`;
  **VOLUME-REGIME-V1** = `trailing_ratio(volume)`;
  `trailing_ratio(x, W=1440): x[i] / mean(x[i−1440 … i−1])` — 1440 **bars**
  over the full merged series, **current bar excluded** from its own
  normaliser, None until 1440 prior bars exist or when the mean ≤ 0.
- **Frozen states:** LOW < 1.270 ≤ MEDIUM ≤ 2.335 < HIGH, identical
  cutoffs for both tools, never recalibrated.
- **Availability:** every stamp is a close stamp; a bar is available at
  its own stamp and never earlier.
- **Track B ATR:** ATR20 = SMA(20) of true range over the 20 bars ending
  at j (current bar included; legal at the close stamp).
  **ATR state** = `trailing_ratio(ATR20)` (W = 1440, current bar
  excluded), quintiles with cutpoints from the first calendar year.
- **Track B conclusions:** ATR is the strongest single predictor;
  VOLUME retains independent information after ATR *and* RANGE
  (β +0.0844, CI excl. 0); RANGE is largely absorbed once VOLUME is
  present (β +0.0052, CI incl. 0); matched retention ≈ 26–33%.

# 3. FROZEN RESEARCH QUESTION

> **DOES ADDING FROZEN RVMR INFORMATION IMPROVE CAUSAL FORECASTS OF
> FUTURE ABSOLUTE NQ MOVEMENT RELATIVE TO AN ATR-ONLY BENCHMARK?**

Not asked: direction, buy/sell, trade selection, OFH13 filtering, stop
or target changes.

# 4. FROZEN PRIMARY TARGET (direct lineage, no sweep)

The exact certified RVMR target is reused:

```
target(t, H) = abs_H(t) = | close[t+H] − close[t] |     (points)
```

Direction-free; causal (uses only the completed close at t as the
anchor); measurable only after H minutes mature. 15/30/60 all belong to
the certified horizon set (5, 10, 15, 30, 60), so **no new target
definition is introduced and no alternative is tested.**

# 5. FROZEN HORIZONS

**Primary: H ∈ {15, 30, 60} minutes.** The certified 5m and 10m targets
may appear only as secondary lineage diagnostics; they cannot determine
promotion. No post-result horizon selection.

# 6. FROZEN QUANTILES

**P50, P80, P95** = conditional 50th / 80th / 95th percentiles of
`abs_H`. No alternate quantile grid may be introduced after results.

# 7. FROZEN MODEL FAMILY — EXACTLY FOUR, NO FIFTH

All models are conditional empirical-quantile tables over **categorical
frozen states** (see §10):

| model | conditioning cell |
|---|---|
| **A — PRIMARY BENCHMARK** | ATR state × ToD bucket |
| **B — PRIMARY RVMR CANDIDATE** | ATR state × ToD bucket × **VOLUME state** |
| **C — SECONDARY CHALLENGER** | ATR state × ToD bucket × **RANGE state** |
| **D — COMPLEXITY CHALLENGER** | ATR state × ToD bucket × RANGE state × VOLUME state |

B is primary because VALIDATION-V1 found VOLUME retained independent
information after ATR. **No post-result model variants.**

# 8. FROZEN ATR DEFINITION (Track B, unchanged — no incompatibility)

- ATR20 = SMA(20) of true range, 1-minute bars, current bar included,
  available at the close stamp of bar j.
- ATR state variable = `trailing_ratio(ATR20)`, W = 1440, current bar
  excluded from the normaliser.
- **State boundaries: quintiles of the ATR ratio computed from
  calendar-2019 eligible bars only** — the identical Track B rule,
  recomputed deterministically by the engine (Track B's committed output
  records 0.9588 / 1.2187 / 1.5612 / 2.0508 from n = 40,354; the engine
  must reproduce these from the rule, not hardcode them). Applied
  unchanged to all later data. Causal for every scored forecast because
  scoring begins 2020-07-01 (§16).
- **No ATR-period sweep. ATR10/14/50/100 comparisons are forbidden,
  before and after results.**

# 9. FROZEN RVMR DEFINITIONS

Frozen RVMR-V1 exactly: formulas of §2, thresholds 1.270 / 2.335, no
recalibration, no new thresholds, **no combined RVMR score**. RANGE and
VOLUME remain distinct frozen variables using their **frozen LOW/MED/HIGH
labels**.

# 10. STATE VS CONTINUOUS — DECIDED NOW

**Categorical frozen states, all four models.** Reasons fixed before
results: (a) direct lineage with every certified RVMR artifact, which is
bucket-based; (b) empirical cell quantiles need no functional form;
(c) it keeps the family at four models. **No continuous-score variant
exists in this family**, so no state-vs-continuous winner can be picked
afterward.

# 11. FROZEN TIME-OF-DAY BINS (repository convention, read from source)

The four predeclared buckets frozen in `rvmr_run` TEST 5 and reused by
VALIDATION-V1 (`val_lib.TOD`), minute-of-day boundaries in ET:

```
OPEN       570 <= mod < 630      (09:30–10:30)
MIDMORN    630 <= mod < 720      (10:30–12:00)
MIDDAY     720 <= mod < 810      (12:00–13:30)
AFTERNOON  810 <= mod <= 900     (13:30–15:00)
```

These exactly tile the eligible universe (§12), whose latest eligible
stamp is mod = 900. Overnight is not in the eligible universe and is
therefore not binned. No minute-level lookup, no post-result bin change.

# 12. FROZEN ELIGIBLE UNIVERSE

Exactly the frozen RVMR-V1 universe gate, plus ATR-state availability:

- RTH close-stamped: `570 <= mod <= 960` **and** `(960 − mod) >= 60`
  ⇒ eligible stamps are mod ∈ [570, 900];
- ATR20 available and > 0; ATR ratio (state variable) non-None;
- both frozen RVMR scores non-None (1440-bar warmup);
- the next 60 bars exist and are minute-contiguous
  (`em[j+60] − em[j] == 60`) — one gate for all three horizons, so every
  eligible bar issues forecasts at 15, 30 and 60m simultaneously;
- **no roll quarantine** (single-market NQ study; the RVMR certification
  applied none — recorded, not decided ad hoc);
- holidays/early closes and data gaps are handled solely by the
  contiguity and session rules above: a bar failing any gate issues
  **UNAVAILABLE** — never interpolated, never forward-filled.

Feasibility (row counts only, no outcomes): the identical gate produced
593,190 eligible bars over 1,829 days in VALIDATION-V1 Track B.

# 13. FROZEN CONDITIONAL QUANTILE METHOD

Empirical quantiles per conditioning cell. **Frozen algorithm** (linear
interpolation between order statistics — the "type 7" convention): for a
cell's sorted matured targets `x_1 <= … <= x_n` and quantile
`q ∈ {0.50, 0.80, 0.95}`:

```
h = (n − 1) * q + 1
P_q = x_floor(h) + (h − floor(h)) * (x_floor(h)+1 − x_floor(h))
```

No ML of any kind: no XGBoost, random forest, neural network, gradient
boosting, genetic search, or automatic feature selection.

# 14. FROZEN MINIMUM CELL SIZE

```
MIN_CELL_N = 400 matured observations AND >= 20 distinct trading days
```

Justification fixed now: at n = 400 the P95 estimate is supported by an
expected 20 exceedances beyond the quantile, the standard minimum for a
tail order statistic to be stable; the 20-distinct-day floor prevents a
cell from being certified by two or three clustered sessions, since
minutes within a day are dependent. A cell below either floor is not
used at that level — the fallback ladder applies.

# 15. FROZEN FALLBACK HIERARCHY (deterministic; first level meeting MIN_CELL_N)

```
MODEL A:  L0 (ATRq x ToD)  ->  L1 (ATRq)  ->  UNAVAILABLE
MODEL B:  L0 (ATRq x ToD x VOL)  ->  L1 (ATRq x ToD)  ->  L2 (ATRq)  ->  UNAVAILABLE
MODEL C:  L0 (ATRq x ToD x RNG)  ->  L1 (ATRq x ToD)  ->  L2 (ATRq)  ->  UNAVAILABLE
MODEL D:  L0 (ATRq x ToD x RNG x VOL)  ->  L1 (ATRq x ToD x VOL)
          ->  L2 (ATRq x ToD)  ->  L3 (ATRq)  ->  UNAVAILABLE
```

The fallback level is recorded per forecast. **No dynamic choice of
whichever neighbouring cell performs best.**

# 16. FROZEN CHRONOLOGICAL EVALUATION — ROLLING ORIGIN, EXPANDING WINDOW

- **Initial training period:** all eligible bars with
  sessionDate ≤ **2020-06-30** (≈ the first 12 months of the canonical
  history, which begins 2019-07-04).
- **Scored period:** forecasts issued at eligible bars with sessionDate ≥
  **2020-07-01** through the end of the canonical history.
- **Calibration update rule — EXPANDING window, chosen now** (rolling
  fixed-width is *not* used and may not be selected later): the quantile
  tables are recomputed at the start of **each calendar month M**, using
  exactly the matured observations whose forecast timestamp t satisfies
  `t + 60 minutes < first minute of M` — so an observation whose horizon
  crosses the month boundary is excluded from that month's tables.
  Every forecast issued inside month M uses the tables of month M.
  Deterministic, fully causal, no future observation ever enters a table
  used to score it.
- **Frozen structure vs updating values:** the model structure (states,
  bins, thresholds, hierarchy, MIN_CELL_N) never changes; only the
  empirical quantile values inside cells update on the monthly schedule.
- ATR-state boundaries (§8) come from calendar-2019 data only and are
  fixed — causal for every scored forecast.
- 2019 and 2020-H1 are training-only and are reported as such; they can
  never be scored.

# 17. FROZEN PRIMARY SCORING RULE — PINBALL LOSS

For realized y, predicted quantile ŷ_q:

```
L_q(y, yhat) = q * (y − yhat)        if y >= yhat
             = (1 − q) * (yhat − y)  if y <  yhat
```

Reported separately for each (quantile × horizon). **Primary model-level
score = the unweighted mean of the nine components** (3 quantiles × 3
horizons), each component itself the mean loss over scored forecasts.
Lower is better. This is the promotion metric and may not be replaced
because another metric looks nicer.

# 18. FROZEN CALIBRATION MEASURE AND TOLERANCE

`insideP_q = 1 if realized abs_H <= predicted P_q`. Observed coverage =
mean(insideP_q). **Coverage error = observed − nominal** (percentage
points). Frozen promotion tolerances, per horizon, for the candidate
model:

| quantile | tolerance |
|---|---|
| P50 | ±3.0 pp |
| P80 | ±2.5 pp |
| P95 | ±1.5 pp |

A calibration condition passes if the point error is within tolerance
**or** the day-clustered 95% CI of coverage includes the nominal value.

# 19. FROZEN SHARPNESS DIAGNOSTIC AND GATE

Report median predicted P50 / P80 / P95 per model, horizon and (as
diagnostics) per ToD bucket. **Material sharpness deterioration**
(promotion-relevant, defined now): a candidate whose median predicted
band exceeds **110% of Model A's median** at the same quantile and
horizon fails condition 8. (Pinball already penalizes width; this gate
prevents a coverage win bought with systematically wider bands.)

# 20. FROZEN PRIMARY COMPARISON

**MODEL B vs MODEL A.** Primary question: does B reduce out-of-period
combined pinball loss relative to A without materially degrading
sharpness (§19) or calibration (§18)? C and D are secondary.

# 21. FROZEN MATERIALITY AND RANGE-INCLUSION (COMPLEXITY) GATES

Relative improvement `Δ%(X over Y) = 100 × (PL_Y − PL_X) / PL_Y` on the
combined nine-component score.

- **Materiality (B over A):** Δ% ≥ **1.0%** and the day-clustered 95% CI
  of the paired per-day difference excludes 0.
- **RANGE earns inclusion — D over B:** D replaces B only if
  Δ%(D over B) ≥ **1.0%** with day-clustered 95% CI excluding 0.
  A marginal D defers to B; the complexity penalty favours simplicity.
- **C:** may be selected only if Δ%(C over A) ≥ 1.0% (CI excl. 0) **and**
  Δ%(C over B) ≥ 1.0% (CI excl. 0).

# 22. FROZEN DAY-CLUSTERED INFERENCE (tractable by construction)

The day is the cluster unit. For every paired comparison the engine
precomputes **per-day (sum, count) of the paired forecast-level loss
differences**, then bootstrap-resamples whole days:

- iterations **20,000**; seed **20260825** (project convention); 95% CI.
- cost per iteration is O(days) over precomputed pairs — the
  infeasible-bootstrap error made in VALIDATION-V1 Track B is excluded
  by design, before the run.
- coverage CIs use the same per-day sufficient-statistic bootstrap on
  the indicator variables.
- **No naive minute-level standard error is used for any promotion
  decision.**

# 23. FROZEN OVERLAP HANDLING

Adjacent-minute forecasts overlap heavily; effective N is far below
forecast count and is never claimed otherwise. **Primary inference:**
day-clustered bootstrap (§22). **Declared secondary diagnostic:** a
non-overlapping audit sample per horizon — forecasts whose minute-of-day
satisfies `mod ≡ 570 (mod H)` — reported for comparison, never primary.

# 24. FROZEN YEAR-STABILITY GATE

Report Δ%(candidate over A) for every scored calendar year (2020-H2,
2021, 2022, 2023, 2024, 2025, 2026-partial) with ≥ 60 eligible days.
**Gate:** the improvement is positive in ≥ **70%** of qualifying years,
**and** the pooled improvement recomputed with the single best year
removed remains > 0 (no single-year dependence). Small partial years are
not required to be independently significant.

# 25. FROZEN REGIME DESTRUCTION (diagnostics only — no regime models)

Predeclared environments: COVID-era scored portion (2020-07 → 2020-12);
2021; 2022 bear/rate-hike; 2023–24; 2025–26. Reported; never fitted
separately; never removed.

# 26. FROZEN TIME-OF-DAY DESTRUCTION

Performance reported inside each frozen bucket. No bucket may be removed
or down-weighted after results. If value concentrates in one bucket the
classification is **TIME-SPECIFIC VALUE**, which is a reporting label,
not a model change; a narrowed model would require a new pre-registered
V2.

# 27. FROZEN TAIL DESTRUCTION

Exact method: per horizon, rank scored forecasts by **realized abs_H**;
recompute Δ%(candidate over A) excluding the top 1%, then the top 5%.
Primary results always retain all data. **Gates (12, 13):** the paired
improvement remains > 0 after each removal.

# 28. HISTORICAL STATUS — BINDING LABEL

The NQ history has been researched by this programme for months. Any
RVMR-BANDS-V1 historical result is **HISTORICAL CALIBRATION EVIDENCE**,
never "prospective", never "pristine OOS". Its only power is to decide
whether a model deserves freezing for future shadow validation.

# 29. FROZEN PROMOTION GATE — ALL SIXTEEN REQUIRED

| # | condition | frozen criterion |
|---|---|---|
| 1 | causal implementation | causality audit passes; no future data in any table used to score it |
| 2 | valid rolling evaluation | §16 executed exactly; scored period only |
| 3 | P50 calibration | §18 tolerance, all three horizons |
| 4 | P80 calibration | §18 tolerance, all three horizons |
| 5 | P95 calibration | §18 tolerance, all three horizons |
| 6 | beats ATR-only | combined pinball lower than Model A |
| 7 | material improvement | Δ% ≥ 1.0%, day-cluster CI excludes 0 |
| 8 | sharpness | no quantile/horizon median > 110% of Model A's (§19) |
| 9 | dependence-aware support | §22 CI excludes 0 (same test as 7) |
| 10 | year stability | §24: ≥ 70% of qualifying years positive |
| 11 | not extreme-episode-dependent | §24 best-year-removed improvement > 0; §25 reported |
| 12 | top-1% tail removal | improvement remains > 0 |
| 13 | top-5% tail removal | improvement remains > 0 |
| 14 | fallback rate | candidate issues **level-0** forecasts for ≥ 70% of its scored forecasts |
| 15 | no leakage | §16 maturation rule verified in audit |
| 16 | no post-result parameter change | every §4–§27 value byte-identical to this document |

# 30. FROZEN DETERMINISTIC MODEL-SELECTION RULE

1. If **B** passes all sixteen and D does **not** materially beat B
   (§21) → **select B**.
2. If **D** materially beats B (§21) and D passes all sixteen →
   **select D**.
3. **C** is selected only under §21's C-rule with all sixteen passed.
4. If no RVMR model passes: if Model A meets conditions 1–5 (causal,
   valid, calibrated), the verdict is **ATR-ONLY BANDS ARE SUFFICIENT**;
   if A itself fails calibration, **BAND CALIBRATION ITSELF IS NOT
   RELIABLE**.

# 31. ALLOWED FINAL HISTORICAL VERDICTS (no others)

```
RVMR-BANDS-V1 READY FOR PROSPECTIVE SHADOW VALIDATION
RVMR-BANDS-V1 HISTORICALLY PROMISING BUT INCONCLUSIVE
ATR-ONLY BANDS ARE SUFFICIENT
RVMR DOES NOT MATERIALLY IMPROVE EXPECTED-MOVEMENT BANDS
BAND CALIBRATION ITSELF IS NOT RELIABLE
SPECIFICATION FAILURE
INSUFFICIENT DATA
```

# 32. NO FORWARD LOGGER YET — BINDING

`RVMR_BANDS_V1_FORWARD` and any prospective prediction may be
implemented **only after**: historical study complete → promotion gate
passed → winning model identified → winning model frozen → spec and
hashes committed. None of that exists yet.

# 33. NO TRADING RESEARCH — BINDING

Forbidden here and in the historical run: direction prediction, entry
filters, OFH13 integration, adaptive stops/targets/holding time,
position sizing, trade grading, trade avoidance, 5s/15s execution.
RVMR-BANDS predicts movement magnitude only.

---

**Execution of the historical study requires a separate directive. This
document is the test. The numbers come later.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
