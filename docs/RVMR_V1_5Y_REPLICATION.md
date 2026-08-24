# RVMR-V1 — FIVE-YEAR RANGE / VOLUME MOVEMENT-REGIME REPLICATION

**MULTI-YEAR HISTORICAL REPLICATION (backward out-of-sample).** The
data **precedes** the discovery year, so this is not prospective
validation and is not called that. Engine and specs frozen at commit
`84933d2` **before any five-year outcome was computed**. Full raw
output: `analysis/rvmr/RVMR_5Y_OUTPUT.txt`.

## **VERDICTS**

- **RANGE-REGIME-V1 — STRONG MULTI-YEAR REPLICATION**
- **VOLUME-REGIME-V1 — STRONG MULTI-YEAR REPLICATION**
- **RVMR-V1 CERTIFIED FOR FUTURE STRATEGY-RESEARCH USE** — meaning the
  regime information is robust enough to serve as a pre-registered
  contextual variable in future strategy research. **It does NOT mean a
  proven trading edge.** No strategy, filter, sizing or direction test
  was run in this study, by design.
- **RANGE AND VOLUME BOTH SURVIVE AND CONTAIN INCREMENTAL INFORMATION.
  RVMR-C1 COMBINATION STUDY IS JUSTIFIED AS A SEPARATE PRE-REGISTERED
  HYPOTHESIS.** No combined score was created here.

---

## 1–2. Source-of-truth audit

Located, read (not remembered), and hashed:

| file | sha256 (16) | supplies |
|---|---|---|
| `analysis/mag/mag_lib.py` | `c1b2a961cb2cd464` | feature formulas |
| `analysis/mag/mag_h3.py` | `a7cd3d0b057b2fe0` | universe, buckets, labels |
| `analysis/mag/mag_h3_perm.py` | `54fe03d8b5c0de9d` | day-clustered statistics |
| `analysis/mag/MAG_H3_OUTPUT.txt` | `dc705ea8a4abdcd6` | reproduction target |
| `docs/MAG_PREREGISTRATION.md` | `0041f47e8ff5f37e` | original freeze |
| `src/V4Shared.cs` (V4SessionMap) | — | RTH 570..960 |

## 3–4. Exact frozen specifications (`analysis/rvmr/rvmr_spec.py`)

```
score(x)_t = x_t / mean(x_{t-1440 .. t-1})        x = high-low  (RANGE)
                                                  x = volume    (VOLUME)
window = 1440 BARS (not wall-clock), full merged series incl. overnight,
current bar EXCLUDED from its own normaliser
BUCKETS (both tools, verbatim from the original implementation, which
applied MAG_SCORE's U-partition terciles to the benchmark scores too):
  LOW < 1.270    MEDIUM 1.270..2.335    HIGH > 2.335
UNIVERSE: close-stamp ET in [09:30, 15:00], ATR(20)=SMA(TR) > 0,
  both scores non-None, next 60 bars minute-contiguous
LABELS from close[j]: |ret|, window range, MFE+MAE at 5/10/15/30/60m
STATS: day = cluster unit; day-median Spearman + 20k whole-day
  permutations; day bootstrap CIs; full-sample Spearman as point est.
```

**No recalibration anywhere** — the same two numeric thresholds score
2019 and 2025 alike. Requires **nothing beyond ordinary OHLCV**.

## Reproduction gates — run before the battery

**GATE A (exactness):** the ported machinery reproduced the archived
discovery-year benchmark **exactly** — universe 83,596; bucket Ns
37,593/31,550/14,453 (RNG) and 21,950/28,720/32,926 (VOL); Spearmans
+0.2656/+0.2658 to four decimals. *(Disclosed: the first gate run
printed FAIL on five medians that differed by exactly 0.05 — my
verification harness compared full-precision quarter-point medians
(9.75) against the archive's one-decimal printout (9.8) with a strict
tolerance. Harness fixed to print-format equality; the tool was never
touched.)*

**GATE B (OHLCV purity):** the pure-OHLCV pipeline — own ATR(20), own
session clock, own ratios — produced a **byte-identical universe
(delta +0 rows)** and identical tables on the discovery year. The
translation layer contributes zero drift.

## 5–7. Five-year data audit

Asset: the Phase-0-audited V3 1m export (`docs/V5_PHASE0_AUDIT.md`),
reduced from event-expanded form to **2,503,622 one-row-per-bar OHLCV
records — exactly the Phase-0 count — 0 conflicting duplicates, 0
duplicate timestamps, strictly monotonic**, 2019-07-04 → 2026-08-17,
ET close-stamped, DST-consistent (the sole DST anomaly, 2022-11-06, was
classified in Phase 0).

- **Basis comparability is PROVEN, not assumed:** in the overlap year,
  118,935 of 118,939 bars (100.0%) match the canonical capture's OHLC
  **exactly** at stamp shift 0, median volume ratio **1.0000**. The V3
  stamp convention and volume basis are identical to the discovery
  data's.
- **Roll/contract audit:** the largest session-reopen jumps are all
  Sunday weekend gaps (largest 360.00 pt, 2025-04-06), not quarterly
  rolls; prices are raw (no back-adjustment). Reopen gaps sit
  **structurally outside every RTH label window** (windows never span
  18:00) and enter the tool only as one bar among 1,440 in the
  normaliser.
- **Volume regime of the instrument itself:** median RTH volume grew
  255 (2019, MNQ infancy) → 3,071 (2026). The trailing-ratio
  construction normalises the level by design; selectivity drift is
  reported in Test 11.

**Primary window: strictly pre-discovery, < 2025-08-18** —
2,152,556 bars, **510,309 eligible universe bars, 1,573 days**.

---

## 8–10. Overall results and monotonicity (Test 1)

| tool | bucket | n | med \|ret\| 5m | 15m | 30m | 60m |
|---|---|---|---|---|---|---|
| RANGE | LOW | 202,881 | 5.75 | 10.50 | 15.00 | 21.25 |
| RANGE | MEDIUM | 214,771 | 8.50 | 14.75 | 21.00 | 28.75 |
| RANGE | HIGH | 92,657 | 11.75 | 19.75 | **27.50** | **36.50** |
| VOLUME | LOW | 130,884 | 5.25 | 9.25 | 13.50 | 19.50 |
| VOLUME | MEDIUM | 181,852 | 7.50 | 13.00 | 18.75 | 26.00 |
| VOLUME | HIGH | 197,573 | 10.50 | 17.75 | **25.00** | **33.75** |

Monotone **5 of 5 horizons, both tools**. Mean |ret|@30m: RANGE HIGH
38.76 [37.51, 40.00] vs LOW 22.56 [21.80, 23.35] — **HIGH−LOW +16.21,
H/L 1.72×**; VOLUME +15.37, 1.75×. CIs nowhere near overlapping.

## 11–12. Year-by-year (Test 2) — the headline table

**70 of 70 cells strictly monotone.** Seven calendar years × five
horizons × two tools, LOW < MEDIUM < HIGH held **every single time** —
2019's quiet infancy, 2020's COVID crash, 2021's melt-up, 2022's bear,
2023–24, and 2025. No cell was excused as noise; none needed to be.

## Spearman stability (Test 3)

Full-period day-level Spearman **+0.3967 (RANGE)** and **+0.4481
(VOLUME)**, permutation p = 0.00005, CIs [+0.352, +0.440] and
[+0.403, +0.491]. Per-year day-level values: RANGE +0.263…+0.502,
VOLUME +0.332…+0.514 — **positive every year, p = 0.0002 in every
year, zero sign flips.** The discovery year's values (+0.39 / +0.38 on
day medians) sit inside the historical range.

## 13. Month stability (Test 13)

**74 of 74 months positive — both tools.** RANGE: median monthly
HIGH−LOW +12.25, worst month **+4.00** (2019-07), best +28.00
(2022-01). VOLUME: median +10.00, worst **+3.00**, best +27.50. The
effect is not driven by a handful of months; it never even changes
sign.

## 14. Time-of-day (Test 5)

Monotone 5/5 in **all four predeclared buckets** for both tools.
Strongest at the open (VOLUME L/M/H 11.50/24.25/30.75), flattest at
midday (13.50/17.75/20.00) — weakens, never disappears, and no bucket
is promoted to a filter.

## 15. Volatility-era robustness (Test 4)

Months split into QUIET/MID/VOLATILE by realized range (diagnostic
slicing only): monotone **5/5 within every era**, day-Spearman +0.34 to
+0.54 within eras. The tool ranks future movement **inside quiet
markets and inside violent ones** — it is not merely "volatile years
have larger bars."

## 16. Persistence (Test 6)

H/L future-range ratio: **1.92× at +3m decaying only to 1.73× at
+30m** (RANGE); VOLUME 1.91× → 1.74×. Persistent regime, not one large
bar — and the decay profile reproduces the discovery year's RANGE-H1
(1.7–1.8×) almost exactly.

## 17. Head-to-head (Test 7)

| metric | RANGE | VOLUME |
|---|---|---|
| full Spearman@30 | +0.2160 | **+0.2268** |
| day-level Spearman | +0.3967 | **+0.4481** |
| HIGH−LOW mean@30 | **+16.21** | +15.37 |
| persistence H/L @+30 | 1.73 | 1.74 |
| year stability | 7/7 | 7/7 |

**COMPLEMENTARY — near-tie.** VOLUME is marginally stronger
statistically; RANGE carries a marginally larger effect per event.
Neither is declared redundant.

## 18. Redundancy (Test 8)

Score correlation +0.8143; bucket agreement 58.6%. **Asymmetric
containment:** P(VOL HIGH | RNG HIGH) = **94.5%** but P(RNG HIGH | VOL
HIGH) = **44.3%** — a range shock almost always comes with a volume
shock, not conversely. The RNG-HIGH/VOL-LOW corner is nearly empty
(n = 583 of 510k) but carries the largest median movement (34.00) —
big moves on thin volume; noted, tiny sample, no conclusion drawn.

## 19. Incremental value (Test 9)

- VOLUME within RANGE buckets: monotone in LOW and MEDIUM outers; fails
  only in the HIGH outer (the n=583 corner above).
- RANGE within VOLUME buckets: monotone **3/3**.
- Rank regression |ret|@30 ~ range + volume: **β_volume +0.151,
  β_range +0.093** — with both present, volume carries more weight.

**Both add information after the other is known.** Hence the RVMR-C1
justification above — as a separate future pre-registration, not here.

## 20. Transitions (Test 10, diagnostic)

VOLUME-HIGH is far stickier than RANGE-HIGH: P(stay next bar) 74.4% vs
50.6%; staying-HIGH predicts more subsequent movement than
entering-HIGH for both (27.25 vs 20.00 median @30, VOLUME). No
transition rule is built.

## 21. Selectivity (Test 11)

RANGE: 39.8 / 42.1 / 18.2% (L/M/H), HIGH share ranging 13.7–21.0%
across years. VOLUME: 25.6 / 35.6 / 38.7%, HIGH 32.9–41.6%. VOLUME's
larger HIGH share is a structural property of the frozen construction
(both tools inherit MAG_SCORE's terciles, and the volume ratio's
distribution sits higher). Drift across seven years is modest — nothing
approaching the 90%/10% pathology — and **nothing was repaired.**

## 22. Extreme years (Test 12 — the destruction test)

Chosen by realized range, not by RVMR: most volatile **2022** (median
daily RTH range 285.0), least volatile **2019** (69.5). Monotone
**5/5 in both years, both tools.** The tool works in the quietest year
in the sample and in the most violent.

## 23. Leave-one-year-out (Test 14)

Rest-of-sample HIGH−LOW is +10.75…+13.00 under every omission; every
omitted year is itself positive (+4.25…+18.50). No single year carries
the result.

## 24–26. Placebo / artifact decomposition (Test 15)

- **Day-shuffle permutation** (formal null): p = 0.00005.
- **Time-of-day-matched separation:** comparing HIGH vs LOW bars *at
  the same minute of day*, RANGE retains **84%** of the pooled effect
  and VOLUME **104%** — the effect is **not** an opening-range or
  time-of-day artifact, and not volume seasonality.
- **3-trading-day-lagged label:** retains 52% (RANGE) / 63% (VOLUME) —
  about half the separation is slow multi-day volatility clustering;
  the other half is **local, same-hour state information**.
- Roll artifact: excluded structurally (audit). Serial dependence:
  handled by day clustering throughout; minutes were never treated as
  independent trials. Lookback artifact: none observed — selectivity
  and effect are stable across eras despite a 12× volume level change.

## Minimum success criteria — 12 of 12

positive full-period Spearman ✓ · monotone at all primary horizons ✓ ·
positive in every year ✓ · no sign inversion in any era ✓ ·
economically meaningful (H−L ≈ +15–16 pt @30m vs ~0.9 pt round-trip
cost scale) ✓ · persists beyond the current bar ✓ · survives
time-of-day matching ✓ · not driven by top months (74/74 positive) ✓ ·
sane selectivity ✓ · beats placebo ✓ · stable under dependence-aware
statistics ✓ · computable from ordinary OHLCV ✓

---

# FINAL ANSWERS

1. **DOES RANGE-REGIME-V1 PREDICT FUTURE MOVEMENT MAGNITUDE OVER ~5
   YEARS? YES.**
2. **DOES VOLUME-REGIME-V1? YES.**
3. **LOW < MEDIUM < HIGH ACROSS MOST YEARS AND HORIZONS? YES — all 70
   of 70 year×horizon cells, both tools.**
4. **DOES THE EFFECT PERSIST BEYOND THE CURRENT BAR? YES — H/L ≈ 1.9×
   at +3m, still ≈ 1.73× at +30m.**
5. **WHICH TOOL IS STRONGER? COMPLEMENTARY.** VOLUME marginally
   stronger statistically, RANGE marginally larger per-event effect.
6. **DOES VOLUME ADD INFORMATION AFTER RANGE? YES** (β_volume +0.151;
   monotone within RANGE buckets outside one n=583 corner).
7. **DOES RANGE ADD INFORMATION AFTER VOLUME? YES** (monotone 3/3
   within VOLUME buckets; β_range +0.093).
8. **COMPUTABLE FROM ORDINARY LONG-HISTORY OHLCV? YES** — proven by a
   zero-drift pure-OHLCV gate and a five-year run that used nothing
   else.
9. **IS THE EFFECT MOSTLY JUST VOLATILITY PERSISTENCE? PARTLY** — and
   now quantified: ~84–104% survives time-of-day matching, ~52–63%
   survives a 3-day label lag. The tool *is* volatility persistence by
   construction; roughly half its separation is local same-hour state
   beyond both time-of-day and multi-day clustering.
10. **ROBUST ENOUGH AS A PRE-REGISTERED MARKET-STATE VARIABLE? YES.**

## What research may be done next (exact recommendation)

1. **RVMR-C1** — pre-registered combination study (both tools carry
   incremental information). Separate freeze, separate M.
2. **Pre-registered strategy×regime interaction** — e.g. OFH13 economics
   conditioned on the frozen RVMR states (the RANGE-H2-style question),
   as its own family with per-event accounting. Note the known prior:
   83% of OFH13 events already occur in HIGH magnitude states.
3. **Prospective confirmation** — log RVMR states in the forward ledger
   alongside the existing candidates; the only evidence stronger than
   this replication is data that postdates the freeze.

**Frozen artifacts:** `analysis/rvmr/rvmr_spec.py` (specification),
`analysis/rvmr/rvmr_run.py` (engine + gates + battery),
`analysis/rvmr/rvmr_extract.py` (extraction),
`analysis/rvmr/RVMR_5Y_OUTPUT.txt` (full raw output).
No canonical frozen code was modified. OFH13_PROSPECTIVE_V1 untouched.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
