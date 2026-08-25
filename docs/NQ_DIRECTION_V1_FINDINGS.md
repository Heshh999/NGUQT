# NQ-DIRECTION-V1 — HISTORICAL FINDINGS

## **FINAL VERDICT**

> **NQ-DIRECTION-V1 FAILED TO IDENTIFY A ROBUST INCREMENTAL DIRECTIONAL
> MECHANISM.**

Four mechanisms were testable and all four failed the frozen gate; the
fifth had no usable data. **Zero survivors. No candidate is frozen.**

The largest matched directional separation in the entire family was
**+1.72 pp** against a frozen bar of **+3.0 pp**, and **every** hypothesis
produced a *negative* Brier improvement — each one scored **worse** as a
probability engine than the simple baselines it had to beat.

All results are **HISTORICAL DISCOVERY / INTERNAL REPLICATION** — never
pristine OOS, never prospective, never validated. Raw output:
`analysis/nqdir/DIR_OUTPUT.txt`.

---

## 1. Freeze verification

| check | result |
|---|---|
| prereg sha256 at commit `0198497` | `c8c22db1927802df4c475ef4a80f3e0bfc6ef1e7148035d06dd6816b9096080b` — **match** |
| working-tree copy | byte-identical (0-line diff) |
| HEAD at execution | `01984973083e8d9c2b291c5ffea8b1fd2f115581`, tree clean |
| pre-existing directional artifact | **none** — only `feasibility.py` (counts-only) was tracked at the freeze commit |

## 2. Source provenance

`rvmr_spec.py` `e348f035a9209540` · `rvmr_run.py` `8743161d6fb5b04e` ·
`val_lib.py` `7bde837a9c8a9369`. Canonical NQ 1m: 2,503,622 bars,
2019-07-04 → 2026-08-17.

## 3. Implementation / parity audit — PASS

- **Gate 1:** canonical feature parity vs frozen `rvmr_run.features` —
  510,309 bars, **0 mismatches** on every column.
- **Gate 2:** ATR-ratio quintile cuts regenerated from the frozen
  calendar-2019 rule (n = 44,081): 0.9491 / 1.1992 / 1.5304 / 2.0184.
  *(These differ slightly from the RVMR-BANDS cuts because this study's
  eligibility window is `mod ≤ 930` for a 30-minute horizon rather than
  `mod ≤ 900`; the generation rule is identical and was applied as
  frozen.)*
- Usable decision bars: **648,473**. Control cells 1,896; Baseline-A
  buckets 4; Baseline-B cells 40.

## 4. Logical defect re-audit — PASS

| hypothesis | events | reference window | decision bar | self-referential? |
|---|---|---|---|---|
| DIR-H1 | 19,633 | `[s−15, s−1]` highs/lows **and** volume mean | s … s+5 | **NO** |
| DIR-H2 | 22,719 | `max/min close[p..q]` | e ≥ q+1 | **NO** |
| DIR-H3 | 1,745 + 1,340 | OR 09:30–09:44 | ≥ 09:45 | **NO** |
| DIR-H4 | 1,411 + 1,067 | ONH/ONL complete 09:29 | ≥ 09:31 | **NO** |

Non-zero event space confirmed for all. Outcomes never participate in
signal construction. **No repeat of the XMARKET-H8 / RVMR-STRAT-B6
impossible-envelope defect.**

## 5. Historical-evidence status — BINDING

The NQ history has been researched across ~100 prior hypotheses. Nothing
here is pristine OOS. Any survivor would have required prospective
shadow validation; there is no survivor.

---

## 6. DIR-H1 — SWEEP → FAILED ACCEPTANCE → RECLAIM

Frozen: 15-bar extreme over `[s−15, s−1]`, swept with volume ≥ 1.5×
the same-window mean, reclaimed within 5 bars; direction away from the
failed break.

| | |
|---|---|
| events / matched | 19,633 / **19,381** · 1,829 days · 8 years · 10,316 L / 9,065 S |
| 15m accuracy | **50.59%** vs matched control **50.20%** |
| **separation** | **+0.39 pp**, CI [−0.26, +1.05], p 0.2392 |
| 30m accuracy | 50.79% |
| signed ret15 | mean +0.334 · median +0.250 |
| favourable-first | FAV 8,817 · ADV 8,753 · **AMBIGUOUS 1,391** · NEITHER 420 → 50.18% of decided (+0.07 pp vs control) |
| MFE/MAE | 0.976 signal vs 0.957 control |
| **Brier** | 0.24948 vs best baseline (B) 0.24939 → **−0.00009** |
| years positive | 6 of 8; best-year-removed +0.26 pp |
| tails | top-1% share 4.37; mean +0.334 → **ex-top-5% −4.128** |

**The MRV lead did not replicate under matched controls.** The raw
mean is positive only because of the tail: removing the top 5% of
outcomes turns +0.334 into −4.128.

Long 52.79% vs short 48.09% is **NQ's long drift**, which the matched
control absorbs — that asymmetry is not information the mechanism added.

**Verdict: NO INCREMENTAL VALUE.**

## 7. DIR-H2 — IMPULSE → CONTROLLED PULLBACK → RE-EXPANSION

| | |
|---|---|
| events / matched | 22,719 / **22,530** · 1,829 days · 11,602 L / 10,928 S |
| 15m accuracy | 50.27% vs control 50.12% |
| **separation** | **+0.15 pp**, CI [−0.47, +0.76], p 0.6199 |
| signed ret15 | **mean −0.097** |
| favourable-first | 48.93% of decided, **−0.02 pp vs control** |
| MFE/MAE | **0.958 signal vs 0.970 control — worse** |
| Brier | −0.00007 |
| years positive | 5 of 8; best-year-removed +0.05 pp |
| tails | top-1% share **−13.5**, ex-top-5% −4.370 |

The three prior positive constructions (OF-N6, G9, OFH14) do not survive
strict momentum matching. This is the mechanism the pre-registration
flagged as most vulnerable to "price was already trending", and that is
exactly what happened.

**Verdict: REDUNDANT WITH NQ MOMENTUM.**

## 8. DIR-H3 — OPENING-DRIVE RESOLUTION

**Acceptance arm:** 1,745 events / 1,739 matched · 15m 51.41% vs 50.82%
· **separation +0.59 pp**, CI [−1.74, +2.87], p 0.6171 · Brier −0.00040
· favourable-first **−0.97 pp vs control** · **4 of 8 years positive**,
best-year(2020)-removed +0.09 pp · eras **2 of 5** positive.

**Failure arm:** 1,340 events · 15m 49.10% vs 49.90% · **separation
−0.81 pp** · Brier −0.00124 · 4 of 8 years · best-year-removed **−1.50
pp** · **tail removal drives it further negative** (−0.62 / −1.00 pp).

MIDMORN shows +7.53 pp on **n = 95** — far too small to mean anything,
and no narrower window was tested or will be.

**Verdict: NO INCREMENTAL VALUE** (and REGIME-SPECIFIC at best — the
acceptance arm's separation lives in 2020 and 2023–24).

## 9. DIR-H4 — OVERNIGHT INVENTORY RESOLUTION

**The family's best result, and still a clear failure.**

**Acceptance arm:** 1,411 events / 1,403 matched · 1,403 days · 762 L /
641 S.

| | |
|---|---|
| 15m accuracy | **52.96%** vs matched control **51.23%** |
| **separation** | **+1.72 pp**, CI [−0.86, +4.33], **p 0.1957** |
| signed ret15 | **mean −0.294** (median +3.000) |
| favourable-first | 50.80%, +0.46 pp vs control |
| MFE/MAE | **1.012 vs 0.992** |
| **Brier** | 0.24932 vs best baseline (B) 0.24785 → **−0.00147** |
| years positive | **7 of 8**; best-year(2025)-removed **+1.18 pp** |
| eras positive | 4 of 5 |
| tails | separation **survives** removal: +1.95 / +2.55 pp |

This mechanism passes 10 of 14 conditions — sample, calibration,
favourable-first, MFE/MAE, transparency, year stability, era robustness,
tail robustness, leakage, artifacts. It fails the four that matter most:
**separation less than half the frozen 3.0 pp bar with a CI spanning
zero, a negative Brier improvement, and q = 0.5981.**

Note the tension the gate is designed to catch: accuracy is 52.96% but
**mean signed return is negative (−0.294)** — it is right slightly more
often while losing slightly more when wrong.

**Fail-back arm:** 1,067 events · 15m 51.79% vs 49.69% · separation
**+2.09 pp**, CI [−0.95, +5.09], p 0.1824 · Brier **−0.00232** ·
calibration visibly broken (predicted 0.625 → observed 0.488 in the
[0.60,0.65) bin, −13.6 pp) · 2020 alone contributes +11.01 pp.

**Verdict: INTERESTING BUT INCONCLUSIVE** — the strongest signal in the
family, below every promotion bar.

## 10. DIR-H5 — ORDER-FLOW INCREMENT: **INSUFFICIENT DATA**

Archive audit: **1,611,115 genuine 1-minute archive rows scanned;
1,611,115 had an EMPTY delta field; 0 carried populated delta.** Every
row in the `of` archive is `NO_LEVELS` with empty `askVolume`,
`bidVolume` and `barDelta`; the LTF captures likewise wrote empty delta
on their 1m rows (their own runtime diagnostic recorded
`volumetric read False`).

The 355,455-bar delta-populated archive cited in `MAG_FINDINGS.md` lived
in an earlier ephemeral container and **is not present here**.

**Nothing was fabricated.** No footprint-at-price, no inferred
absorption, no proxy delta. The frozen 150-event threshold was **not**
loosened and **M REMAINS 5**.

*Disclosure:* my first loader reported "archive NOT LOADABLE" because it
used the wrong glob and column names — an implementation defect of mine
that would have blamed the loader for a real data absence. I corrected
it to scan every candidate archive with both schemas and to report the
actual row-level audit, then re-ran the study. The verdict is unchanged;
the reason is now accurate.

## 11. Baselines

**A — ToD P(up):** OPEN 0.5246 · MIDMORN 0.5226 · MIDDAY 0.5275 ·
AFTERNOON 0.5163. **B —** 40 cells (ATR quintile × ToD × sign z5).
**C —** momentum sign. Every hypothesis was scored against the **best**
of the three, never the weakest. Baseline B was the best for H1 and H4;
Baseline A for H2 and H3.

## 12. Matched-control design

Cell = `(ATR quintile × ToD × sign(z5) × RVMR RANGE state × year ×
direction)`, plus the frozen mechanism-specific tercile (sweep
magnitude / impulse size / distance from edge). Cells with fewer than 20
counterparts dropped **symmetrically**. Matched retention was 98.7–99.7%
across H1–H4, so no result is flattered by thin control coverage.

## 13–20. Cross-cutting results

**15m and 30m** reported above for every arm. **Favourable-first** used
the frozen ±0.5 ATR rule with **AMBIGUOUS preserved as its own class and
never resolved** (1,391 in H1 alone). **MFE/MAE** in ATR units against
matched controls. **Brier and log loss** computed on identical scored
events — **all four candidates lost to their baselines on both**.
**Calibration** stayed inside the frozen ±7 pp tolerance for every bin
with N ≥ 100 in H1–H4 (H4's fail-back arm broke it badly, −13.6 pp).
**Abstention:** the frozen ≥100-prior-event rule produced 100% coverage
for H1/H2/H3-acceptance and 92–97% for the H4 arms — the mechanisms
almost never abstained.

## 21. Bullish / bearish

Reported separately everywhere, never pooled. The pattern is uniform and
uninformative: longs 52.6–55.5%, shorts 46.5–49.9% across all four
hypotheses — **that is NQ's long drift, present in the controls too**,
not a directional edge. No one-sided V1 was created.

## 22–24. Year, era, time-of-day destruction

Full tables in the raw output. Year-positive counts: H1 6/8 · H2 5/8 ·
H3 4/8 · H4 **7/8**. Era-positive: H1 4/5 · H2 3/5 · H3 2/5 · H4 4/5.
Time-of-day: H1's separation concentrates in MIDMORN (+2.60 pp) and is
negative in MIDDAY/AFTERNOON; H4's is broad (+1.65 OPEN, +2.32 MIDMORN).
**No bucket, year or era was removed.**

## 25. RVMR diagnostic (never a filter)

H1 separation by RANGE state: LOW +0.49 · MEDIUM +0.33 · HIGH +0.41 —
flat, as expected from a direction-free magnitude tool. H4: LOW −2.74 ·
MEDIUM +2.53 · HIGH +1.68 on small cells. **No RVMR filter, combination
or optimization was constructed.**

## 26. Tail destruction

H1 ex-top-5% −4.128 · H2 ex-top-5% −4.370 · H3 ex-top-5% −4.668 ·
H4 ex-top-5% −5.844. **Every hypothesis's positive mean return is
tail-carried.** Separation itself survived tail removal for H1, H2, H4
(H3's failure arm did not).

## 27. Multiple testing — M = 5, not shrunk

| family | n | sep (pp) | p | BH q | Holm |
|---|---|---|---|---|---|
| DIR-H1 | 19,381 | +0.39 | 0.2392 | 0.5981 | 0.9787 |
| DIR-H2 | 22,530 | +0.15 | 0.6199 | 0.7749 | 1.0000 |
| DIR-H3 | 1,739 | +0.59 | 0.6171 | 0.7749 | 1.0000 |
| DIR-H4 | 1,403 | +1.72 | 0.1957 | 0.5981 | 0.9787 |
| DIR-H5 | — | — | — | 1.0000 | 1.0000 |

**M stayed at 5** despite H5 being INSUFFICIENT DATA.

## 28. Promotion gate

| # | condition | H1 | H2 | H3 | H4 | H5 |
|---|---|---|---|---|---|---|
| 1 | sufficient N | PASS | PASS | PASS | PASS | N/A |
| 2 | **separation ≥ 3.0 pp, CI > 0** | **FAIL** +0.39 | **FAIL** +0.15 | **FAIL** +0.59 | **FAIL** +1.72 | N/A |
| 3 | **Brier gain ≥ 0.005** | **FAIL** −0.00009 | **FAIL** −0.00007 | **FAIL** −0.00040 | **FAIL** −0.00147 | N/A |
| 4 | calibration | PASS | PASS | PASS | PASS | N/A |
| 5 | favourable-first improves | PASS | FAIL | FAIL | PASS | N/A |
| 6 | MFE/MAE > control | PASS | FAIL | PASS | PASS | N/A |
| 7 | long/short transparency | PASS | PASS | PASS | PASS | N/A |
| 8 | year stability | PASS | FAIL | FAIL | PASS | N/A |
| 9 | era robustness ≥ 3/5 | PASS | PASS | FAIL | PASS | N/A |
| 10 | tail robustness | PASS | PASS | PASS | PASS | N/A |
| 11 | **BH q < 0.05** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | N/A |
| 12 | no leakage | PASS | PASS | PASS | PASS | N/A |
| 13 | no data artifact | PASS | PASS | PASS | PASS | N/A |
| 14 | no control artifact | PASS | PASS | PASS | PASS | N/A |
| | **ALL FOURTEEN** | **FAIL** | **FAIL** | **FAIL** | **FAIL** | **N/A** |

**Conditions 2, 3 and 11 fail for all four.** No subjective override.

## 29. Survivor ranking (by matched separation — none promoted)

1. **DIR-H4** +1.72 pp — best, 10/14 conditions, still short of every
   materiality bar
2. DIR-H3 +0.59 pp · 3. DIR-H1 +0.39 pp · 4. DIR-H2 +0.15 pp ·
   5. DIR-H5 — untestable

## 30. Candidate freeze

**NONE.** No `NQ-DIR-[H#]-CANDIDATE-V1` is created. No forward logger.
No orders. No combination with RVMR or OFH13.

---

## FINAL QUESTIONS

1. **H1 reclaim added directional information?** — **NO** (+0.39 pp, p 0.24)
2. **H2 beyond momentum?** — **NO** (+0.15 pp, p 0.62; MFE/MAE worse than control)
3. **H3 opening drive?** — **NO** (+0.59 pp, p 0.62; 4/8 years, 2/5 eras)
4. **H4 overnight inventory?** — **NO** (+1.72 pp but p 0.20, CI spans 0, Brier −0.00147)
5. **H5 order flow after price?** — **INSUFFICIENT DATA** (0 delta-populated bars of 1,611,115 scanned)
6. **Largest matched separation?** — **H4** (+1.72 pp)
7. **Best Brier improvement?** — **NONE** (all four negative; least-bad H2 at −0.00007)
8. **Any exceed the 3.0 pp gate?** — **NO**
9. **Any exceed the 0.005 Brier gate?** — **NO**
10. **Any pass both?** — **NO**
11. **Any survive year destruction?** — **YES** (H1 6/8, H4 7/8) — but they fail elsewhere
12. **Any survive tail destruction?** — **YES** (H1, H2, H4 separations) — but they fail elsewhere
13. **Any pass all 14?** — **NO**
14. **How many candidates survive?** — **0**
15. **Build a directional probability tool yet?** — **NO**

---

## What failed, and what it means

- **Price mechanisms (H1, H2):** both had large samples (19k–22k events)
  and both collapsed to noise once matched on NQ's own state. H1 is the
  more significant failure — it was the programme's single best repeated
  lead, with a prior second replication, and it did not survive its first
  properly-controlled directional test.
- **Opening mechanism (H3):** no directional content in either arm; the
  acceptance arm's apparent value is confined to two eras.
- **Overnight mechanism (H4):** the only one with a coherent profile —
  7/8 years, tail-robust, MFE/MAE above control — and still less than
  half the required separation with a negative proper score. It is the
  one thread that could justify a *future* pre-registered study with a
  larger overnight sample; it is **not** promoted and **not** frozen now.
- **Order flow (H5):** untestable here. Re-testing it requires
  re-capturing genuine Volumetric bid/ask data, which is a data task,
  not a research finding.

**No further threshold batch will be generated and no directional tool
will be constructed.** Per the frozen rule, the next research branch must
introduce **genuinely new information** rather than re-cutting NQ price
history — the four mechanisms tested here exhaust the repeated leads the
existing archive contains.

**OFH13_PROSPECTIVE_V1 REMAINS UNTOUCHED. RVMR REMAINS MAGNITUDE-ONLY.
THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**
