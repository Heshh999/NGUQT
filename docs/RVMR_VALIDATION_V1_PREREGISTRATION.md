# RVMR-VALIDATION-V1 — PRE-REGISTRATION

**Frozen before any Track A or Track B result was calculated.** No
result of this study existed when this document was committed.

Two tracks, one question each:

- **TRACK A — RVMR-ES-V1.** Does the exact frozen mechanism transport to
  a market it was never built on?
- **TRACK B — RVMR-INCR-V1.** Does RVMR know anything ATR does not
  already know?

**This is an OFFLINE COMPANION STUDY.** Nothing frozen is modified:
not `rvmr_spec.py`, not `rvmr_run.py`, not the RVMR forward logger, not
`OFH13_PROSPECTIVE_V1`, not `OFH14_PROSPECTIVE_V1`, not the prospective
registry, not the NT8 parity-verified host, not any forward ledger.

No trading, no direction, no management, no bands, no new thresholds, no
combined score. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

# 1. FROZEN RVMR SOURCE PROVENANCE (read from source, not remembered)

| item | value |
|---|---|
| spec path | `analysis/rvmr/rvmr_spec.py` |
| spec sha256 | `e348f035a9209540…` |
| spec freeze commit | `84933d2` |
| engine path | `analysis/rvmr/rvmr_run.py` |
| engine sha256 | `8743161d6fb5b04e…` |
| engine commit | `9d14dfa` |
| certificate doc | `docs/RVMR_V1_SPEC.md` (`3197e013c3d8521a…`, `68ed951`) |
| replication doc | `docs/RVMR_V1_5Y_REPLICATION.md` (`6a39ca4206c1ee40…`) |

### Exact formulas, transcribed from source

```
trailing_ratio(x, W=1440):  out[i] = x[i] / mean(x[i-1440 .. i-1])
    - window is 1440 BARS, over the FULL merged series incl. overnight
    - the CURRENT BAR IS EXCLUDED from its own normaliser
    - None until 1440 prior bars exist; None when the mean is <= 0

RANGE-REGIME-V1  = trailing_ratio(high - low)
VOLUME-REGIME-V1 = trailing_ratio(volume)

atr20(bars): SMA of true range over the 20 bars ENDING AT j (inclusive)
    tr[i] = high-low            if i == 0
          = max(high-low, |high-prev_close|, |low-prev_close|)  otherwise
    None until 20 bars exist
```

### Exact thresholds (source, not this prompt)

```
T1, T2 = 1.270, 2.335
LOW     score <  1.270
MEDIUM  1.270 <= score <= 2.335
HIGH    score >  2.335
```

Identical numeric cutoffs for **both** tools. The original
implementation applied MAG_SCORE's U-partition terciles to the benchmark
scores; that construction is preserved verbatim and is **never**
recalibrated.

### Exact universe gate (per bar j, close-stamped ET)

```
RTH_START, RTH_END = 570, 960          (09:30 .. 16:00)
570 <= minuteOfDay <= 960
(960 - minuteOfDay) >= 60               => stamp <= 15:00
atr20(j) is not None and > 0
range score and volume score both not None
D['em'][j+60] - D['em'][j] == 60        (60 minute-contiguous fwd bars)
```

### Exact certified horizons and movement targets

```
HOR = (5, 10, 15, 30, 60)   minutes, measured from close[j]
abs_h = |close[j+h] - close[j]|                      <- PRIMARY TARGET
rng_h = max(close[j], high[j+1..j+h]) - min(close[j], low[j+1..j+h])
exc_h = MFE_h + MAE_h
```

**The primary certified statistic is median `abs_30`.** Warmup: no
score before 1440 prior bars; no ATR before 20 bars.

### Availability convention

Every stamp is a **close stamp**. A bar is available exactly at its own
stamp and never earlier. `trailing_ratio` excludes the current bar from
its normaliser; `atr20` includes bar j, which is legitimate because bar
j is complete at its close stamp. `STAMP_SHIFT = 0`.

---

# 2. TRACK A — RVMR-ES-V1, OUT-OF-MARKET REPLICATION

## A.0 Data and zero-recalibration rule

ES universe: `scratchpad/es_bar1m`, 2,542,424 genuine 1-minute bars,
2019-06-02 → 2026-08-17, certified by ES-NQ-DATA-V1 (Gate 1 PASS,
Gate 2 PASS, commit `0910732`). Captured by `V41Bar1mCaptureHost`;
0 duplicate stamps, 0 OHLC violations, 0 malformed rows.

**The frozen NQ formula, lookback, score definition, thresholds, timing,
universe gate, horizons and targets are applied to ES UNCHANGED.**
Explicitly forbidden in this track: ES-specific threshold fitting, ES
quantiles as tool cutoffs, tercile recalibration, year-specific
thresholds, ATR-normalized replacement thresholds, time-of-day
thresholds.

**Roll quarantine: NOT applied**, because the frozen NQ certification
applied none and Track A must run the same battery. A roll-quarantined
slice is reported as a **declared secondary diagnostic only**.

**PRIMARY WINDOW: the full ES history.** Every ES bar is genuinely
out-of-market and out-of-sample for RVMR, which was built on NQ alone.
**SECONDARY:** the pre-`2025-08-18` slice, for window-matching with the
NQ five-year replication.

## A.1 Primary endpoints

For **RANGE-REGIME-V1** and **VOLUME-REGIME-V1 separately** (never
combined), on the frozen ES universe:

1. Bucket occupancy N and share for LOW / MEDIUM / HIGH.
2. Median and mean `abs_h` at h ∈ (5, 10, 15, 30, 60) by bucket.
3. Monotonicity LOW < MEDIUM < HIGH at each horizon.
4. `HIGH − LOW` and `HIGH / LOW` on mean `abs_30`, with **day-clustered
   bootstrap 95% CI** (20,000 resamples of whole days).
5. Day-level Spearman (per-day median score vs per-day median `abs_30`)
   with **day-shuffle permutation p** (20,000).

## A.2 Declared pass rules — frozen now

**FULL OUT-OF-MARKET REPLICATION** requires *all seven*, for a tool:

| # | condition |
|---|---|
| A1 | monotone LOW<MED<HIGH on median `abs_h` at **≥ 4 of 5** horizons |
| A2 | `HIGH − LOW` mean@30 > 0 with day-clustered 95% CI excluding 0 |
| A3 | day-level Spearman permutation **p < 0.05** |
| A4 | **≥ 70%** of eligible months show positive `HIGH − LOW` median@30 |
| A5 | **≥ 6 of 8** years show positive `HIGH − LOW` |
| A6 | ToD-matched separation retains **≥ 50%** of pooled separation |
| A7 | each of LOW / MEDIUM / HIGH holds **≥ 5%** of the eligible universe |

**A7 is the calibration-transport test and is deliberately separated
from the mechanism tests.** Per the directive's interpretation rule:

- A1–A6 hold but **A7 fails** → **PARTIAL REPLICATION — CALIBRATION
  DOES NOT TRANSPORT.** Mechanism generalizes; the absolute NQ cutoffs
  do not.
- Conditions hold for one tool only → **PARTIAL — RANGE ONLY** or
  **PARTIAL — VOLUME ONLY**.
- A1–A3 fail for both tools → **FAILED OUT-OF-MARKET REPLICATION**.
- Insufficient eligible bars (< 20,000) → **INSUFFICIENT DATA**.

**Declared diagnostic for separating mechanism from calibration only:**
ES-internal terciles of the raw ES score, reported *solely* to answer
"is the raw score still monotone with future movement". These are
**never** adopted as thresholds, never used in any other test, and
create no new tool.

## A.3 Secondary diagnostics (reported, never decisive)

Year stability (per-year N and mean by bucket, `HIGH − LOW`,
monotonicity); month stability (eligible months, % positive, worst /
median / best, **inverted months shown, never hidden**); time-of-day
using the frozen predeclared buckets `OPEN 570–630 · MIDMORN 630–720 ·
MIDDAY 720–810 · AFTERNOON 810–900`; persistence (mean 1-minute range
per minute after the state, at +3/+5/+10/+15/+30, H/L ratio and decay
shape versus NQ); redundancy (Spearman between the two ES scores);
symmetry (MFE and MAE separately by bucket, plus MFE/MAE — if HIGH
enlarges both sides together that supports the certified magnitude
reading; **a directional asymmetry, if found, is REPORTED and NOT turned
into a strategy hypothesis inside this study**); roll-quarantined slice;
pre-discovery-window slice.

---

# 3. TRACK B — RVMR-INCR-V1, INCREMENTAL VALUE BEYOND ATR

Run on the **canonical NQ history**, broad eligible RVMR universe, **no
strategy parents**.

## B.0 THE ATR DEFINITION — frozen before execution, ONE primary

```
PRIMARY ATR = rvmr_spec.atr20  (SMA(20) of true range)
  bar resolution   1 minute
  period           20
  current bar      INCLUDED in the ATR window (frozen definition; legal
                   because bar j is complete at its close stamp)
  availability     close stamp of bar j, never earlier
```

**No ATR-period sweep. No ATR10/14/50/100 competition, before or after
results.** One primary ATR definition, fixed here.

## B.1 Causal ATR-state construction — frozen before execution

```
atr_ratio(j) = ATR20(j) / mean(ATR20 over bars j-1440 .. j-1)
```

This is `trailing_ratio` applied to ATR — **the identical mathematical
construction RVMR itself uses**, current bar excluded from the
normaliser. This is deliberate: it puts ATR and RVMR on exactly equal
footing, so no RVMR advantage can arise merely from RVMR being a
relative measure while ATR is absolute.

**Strata: QUINTILES of `atr_ratio`**, cutpoints computed on the **FIRST
FULL CALENDAR YEAR of the eligible NQ universe ONLY**, then applied
unchanged to all later data. Causal; no full-sample or future-aware
labels. Quintiles rather than terciles is the conservative choice — a
stricter control.

**Declared secondary:** the same test using quintiles of **raw ATR20 in
points** (cutpoints from the same first-year window), to confirm the
conclusion is not an artifact of the ratio form.

## B.2 Time-of-day control — frozen

The four predeclared frozen buckets (`OPEN / MIDMORN / MIDDAY /
AFTERNOON`), **plus** the per-minute ToD-matched construction already
frozen in `rvmr_run` TEST 15 (weighted by cell size, minimum 10
observations per side).

The decisive comparison is stated explicitly: **similar ATR + similar
time of day + different RVMR.** A 09:30 HIGH compared naively against a
13:00 LOW is not evidence and is not reported as such.

## B.3 Primary endpoints

| id | endpoint |
|---|---|
| **B1** | Within each ATR quintile, is median `abs_30` monotone RVMR LOW<MED<HIGH? Full **5 × 3** surface with N, mean, median, day-clustered CI per populated cell. Repeated at all five frozen horizons as a secondary. |
| **B2** | Same within each **ATR quintile × ToD bucket** cell (20 × 3). |
| **B3** | Continuous model, **no ML, no mining** — see below. |
| **B4** | Non-parametric matched test — see below. |

### B3 — continuous model, frozen form

Primary, source-consistent with `rvmr_run` TEST 9's standardized rank
OLS, extended by the ATR term:

```
rank(abs_30) ~ b0 + b_atr * rank(atr_ratio)
                  + b_rng * rank(range_score)
                  + b_vol * rank(volume_score)
                  + ToD bucket fixed effects
```

Secondary, raw units, for interpretable magnitudes:

```
abs_30 ~ b0 + b_atr*atr_ratio + b_rng*range_score + b_vol*volume_score
             + ToD fixed effects
```

Inference: **day-clustered block bootstrap over whole days (20,000)**
for every coefficient CI.

**FORBIDDEN, before and after seeing any result:** quadratic terms,
interaction terms, splines, machine learning, feature selection, lag
sweeps, additional predictors.

### B4 — matched incremental test, frozen form

For every RVMR-HIGH bar, comparison bars are drawn from LOW ∪ MEDIUM
within the **same (ATR quintile × ToD bucket × year)** cell. Cells
lacking both sides are dropped **symmetrically**. Report matched N,
`HIGH − control` on mean and median `abs_30`, day-clustered 95% CI, and:

```
RETENTION = matched_delta / unconditional_delta
```

## B.4 Declared verdict rules — frozen now

Applied per tool (RANGE, VOLUME) using B3 and B4 jointly:

| verdict | rule |
|---|---|
| **STRONG INCREMENTAL VALUE BEYOND ATR** | B4 CI excludes 0, **retention ≥ 50%**, B3 β > 0 with CI excluding 0, B1 monotone in ≥ 4 of 5 ATR quintiles, consistent sign in ≥ 6 of 8 years |
| **MODEST INCREMENTAL VALUE** | B4 CI excludes 0 and **retention 20–50%** |
| **RANGE INCREMENTAL / VOLUME REDUNDANT** (or mirror) | one tool reaches STRONG/MODEST, the other does not |
| **MOSTLY REDUNDANT WITH ATR** | **retention 5–20%**, or B4 CI includes 0 |
| **FULLY REDUNDANT WITH ATR/TIME OF DAY** | **retention < 5%** or matched delta ≤ 0 |
| **INCONCLUSIVE** | B3 and B4 disagree in sign |
| **INSUFFICIENT DATA** | any primary cell family under-populated |

## B.5 Secondary diagnostics

RANGE incremental to ATR; VOLUME incremental to ATR; **RANGE after
VOLUME and VOLUME after RANGE** (each after ATR, reported separately,
never auto-combined); year-by-year sign and effect size — *consistent
sign and absence of single-year domination matter more than per-year
significance*; and the **slow-regime vs local-state decomposition**
using the already-certified TEST 15 lag methodology (3-trading-day
lagged label at the same minute-of-day), to indicate whether the
incremental-to-ATR component is multi-day clustering, local state, or
both. **No trading rule is derived from this decomposition.**

---

# 4. STATISTICAL DISCIPLINE — frozen

## Family and multiplicity

**PRIMARY FAMILY, M = 4**, fixed now and never shrunk:

```
1  TRACK A  RANGE-REGIME-V1  transports to ES
2  TRACK A  VOLUME-REGIME-V1 transports to ES
3  TRACK B  RANGE-REGIME-V1  incremental to ATR + ToD
4  TRACK B  VOLUME-REGIME-V1 incremental to ATR + ToD
```

BH and Holm reported at **M = 4**. Every horizon, year, month, ToD
slice, ATR stratum and surface cell is a **SECONDARY DIAGNOSTIC**,
reported without correction and **never sufficient for a verdict on its
own.** Dozens of independent "hypotheses" are not manufactured from
horizons and years.

## Dependence — no pseudo-sample inflation

RVMR states persist and adjacent minutes are highly dependent. **The day
is the cluster unit throughout.** Day-clustered bootstrap (20,000) and
day-level permutation (20,000), matching the frozen RVMR machinery.
Overlapping 60-minute forward windows inside a day are handled by
resampling **whole days**. **No i.i.d. minute-level standard errors and
no minute-level p-values are reported anywhere.** Millions of minute
bars are never treated as millions of independent observations.

## Tail audit — destruction only

Both tracks repeated excluding the **top 1%** and **top 5%** of `abs_30`
observations. These are **not** removed from the primary result; the
exclusion is a robustness check reported alongside it.

---

# 5. OUT OF SCOPE — will not be tested in this study

Long vs short signals · RVMR direction · fade entries · breakout entries
· OFH13 filters, stops or targets · RVMR-scaled sizing · RVMR-scaled
management · 5s/15s execution · new RVMR thresholds · any combined RVMR
score · expected-move bands.

**RVMR-BANDS-V1 is NOT built in this run.** If and only if results
justify it, a pre-registration *proposal* is returned — never an
executed study.

## Forward logger

The existing prospective RVMR logger continues unchanged and
uncontaminated. **Every result in this study is HISTORICAL RESEARCH and
is never relabelled prospective.**

**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
