# V5 PRE-REGISTRATION

**Frozen 2026-08-20, before any feature->outcome relationship was examined.**

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.

Companion documents: `V5_PHASE0_AUDIT.md` (the audit that precedes this),
`V4_FINDINGS.md` and `V4_PREREGISTRATION.md` (the programme this replaces).

---

## 0. WHY THESE CLASSES

V4 tested whether endogenous price structure predicts direction and returned a
clean negative: 0 of 8 hypotheses survived, 0 of 60 entry configurations were
positive, and gross expectancy was negative before any cost. Re-tuning that family
would manufacture a curve fit, so V5 changes the hypothesis class rather than the
parameters.

| Programme | What changes vs V4 |
|---|---|
| **P1 exogenous** | The conditioner is not derived from price at all. Every V4 conditioner was endogenous. |
| **P2 path/exit** | The entry is fixed and the exit is searched - the exact complement of V4, which fixed exits at 1R/2R and searched entries. |
| **P3 order flow primary** | Order flow is tested unconditionally, not only at structure breaks, where V4 conditioning may have destroyed it. |

Short-horizon (3-10 min) reversion was considered and deliberately excluded: the
median 3-minute move is 0.25 pt (one tick) against an assumed 1.5 pt round turn,
so the arithmetic is hostile before testing begins. Excluded by choice, recorded
here so the exclusion is not silently forgotten.

---

## 1. DISCLOSURE - WHAT WAS ALREADY SEEN

Full disclosure of everything observed before this freeze, so the reader can judge
contamination rather than take an assurance:

- All Phase 0 audit statistics in `V5_PHASE0_AUDIT.md` - coverage, gap classes,
  reconstruction match rates, feature causality, the R distribution.
- **Unconditional outcome marginals on one DEV month (2021-03):** median
  `mfeLong_20` 12.00 pt, median `maeLong_20` 12.25 pt, median `net_3` +0.25 pt,
  median `net_20` +0.50 pt.

That last line means the unconditional drift over the sampled month is known to be
slightly positive. It does **not** reveal how that drift splits across any
conditioner declared below. No feature->outcome relationship, no subgroup mean, and
no split-by-anything has been examined.

**Historical burn.** This 1-minute asset was used by earlier V3 research in this
project, and its 2025-01..2026-08 tail was spent as V4's out-of-sample window. The
dependent variables and conditioners declared below were never examined in either.
Because that burn is real but hard to quantify precisely, V5 does not rely on a
single holdout - it adds a per-year stability requirement (section 6) that a
window-specific fluke cannot pass.

---

## 2. DATA AND SPLITS

| Split | Window | Bars |
|---|---|---|
| DEV | 2019-07-04 .. 2022-12-31 | ~1.22M |
| VAL | 2023-01-01 .. 2024-12-31 | ~0.71M |
| LOCKBOX | 2025-01-01 .. 2026-08-17 | ~0.57M |

**P3 exception, stated plainly:** volumetric depth exists only from 2025-11-02, so
every P3 observation falls inside LOCKBOX and P3 has no holdout at all. P3 results
are single-sample and suggestive. They are not eligible to support a trading
decision on their own, and this is a property of the data, not a choice.

---

## 3. VALIDITY FILTERS - DECLARED BEFORE OUTCOMES

Fixed now so they cannot be tuned to a result:

1. `barsObserved >= K` for any horizon K (drops the final 80 bars of history).
2. **P2 only:** require `R >= 1.0 pt` (4 ticks) **and** `R <= 10 x ATR`. This
   removes the 1.13% of bars where R is exactly 0 and the extreme upper tail
   (R reaches 1266.50 pt). Without it, small-R bars dominate every pooled
   R-multiple - the failure mode that produced a retracted number in V4.
3. `posInSessRange` and `relVolume` are quarantined (audit section). Where V5 needs
   such a quantity it is reconstructed with an explicit causal definition and a
   denominator guard, never taken from the file.
4. Outcomes are reported in **index points per contract** as the primary unit.
   R-multiples are reported alongside, never alone.

## 4. COST MODEL

**1.5 pt round turn, ASSUMED, not measured.** Identical to V4 and carried forward
unchanged. This project has no fills, so no fill-derived cost estimate is possible,
and inventing one would be worse than naming the assumption.

Every result is reported **both net and gross**. In V4 the gross figure was
decisive: it was negative, which ruled out "the edge existed but costs ate it"
without needing the cost number to be right. The same reporting discipline applies
here.

MNQ only. MNQ = $2 per index point per contract.

## 5. ESTIMATOR

- **Point estimate: pooled mean.** Never mean-of-daily-means. In V4 that estimator
  produced +7.12 pt / t=+4.63 on a cell whose pooled mean was -0.36 pt, and a
  combined figure sitting above both of its own subgroups.
- **Standard error: day-block bootstrap, 2,000 resamples**, resampling whole
  session days to absorb intraday dependence.
- Multiple testing: **Benjamini-Hochberg, q = 0.05**, across the full 10-member
  confirmatory family in section 6. The P2 controls in section 7 predict nulls and
  are reported outside the BH family.

---

## 6. CONFIRMATORY FAMILY - 10 HYPOTHESES, DIRECTIONS FIXED

All times ET. Session returns are close-to-close of the boundary bars.

### P1 - exogenous clock and calendar

| # | Hypothesis | Predicted direction |
|---|---|---|
| **H1** | Mean overnight return (18:00 prior day -> 09:29) is positive **and** exceeds mean RTH return. | overnight > 0, overnight > RTH |
| **H2** | Mean RTH return (09:30 -> 16:00) is <= 0. | RTH <= 0 |
| **H3** | Turn-of-month window (last 3 trading days of month M plus first 2 of M+1) has mean daily return above the unconditional mean. | positive |
| **H4** | Overnight return and the following 09:30-10:00 return are negatively correlated (opening reversal). | negative |
| **H5** | Mean return over 15:30-16:00 is positive (drift into the close). | positive |
| **H6** | Mean Monday RTH return is below mean non-Monday RTH return. | Monday < non-Monday |

H1 and H2 are the two halves of the documented equity-index overnight-drift
decomposition and are declared as separate hypotheses because either can fail alone.

### P3 - order flow as a primary signal

Window 2025-11-02 .. 2026-08-18, 279,834 volumetric 1-minute bars. Outcome is
`net_20` unless stated.

| # | Hypothesis | Predicted direction |
|---|---|---|
| **H7** | Bars in the top decile of `barDelta` have positive mean forward return. | positive |
| **H8** | Bars making a new 20-bar high while `cumDeltaChange20` is negative (bearish divergence) have negative mean forward return. | negative |
| **H9** | `buyImbalanceCount - sellImbalanceCount` is positively associated with forward return. | positive |
| **H10** | Close displaced far above the bar POC predicts reversion. | negative |

---

## 7. P2 CONTROLS - PRE-DECLARED NULLS

P2 is a control programme. Its value is in closing a door that would otherwise
haunt every future result: *were V4's fixed 1R/2R exits what killed it?* The
predicted outcome is the null in every case.

| # | Control | Predicted |
|---|---|---|
| **C1** | P(hit +1R before -1R) on an unconditional entry = 0.50 within sampling error. | no deviation |
| **C2** | Across a grid of target/stop ratios spanning 0.5R..5R, no configuration yields positive net expectancy. | none positive |
| **C3** | E[MFE_K] = E[MAE_K] on unconditional entries, using **unclamped** excursions, beyond the drift term. | no asymmetry |
| **C4** | Expectancy does not improve monotonically as the holding-period cap is raised. | no improvement |

**The theorem is the internal control.** Optional stopping says no exit policy
manufactures positive expectancy from a martingale. If any C1-C4 rejects, the
result is not a finding until it is traced to a specific, named path asymmetry.
Absent that trace, a rejection is to be treated as a bug in my own code.

---

## 8. DECISION RULE - FIXED IN ADVANCE

A hypothesis **survives** only if all four hold:

1. BH-significant at q = 0.05 across the 10-member family;
2. effect in the **predicted** direction;
3. same sign independently in DEV, VAL **and** LOCKBOX;
4. same sign in **at least 6 of 7** calendar years.

Conditions 3 and 4 are stricter than V4's rule. That is deliberate: this is a third
programme run partly over history that earlier programmes have already touched, and
strictness is the correct response to that, not optimism.

**Failure classification** uses the same Case A-E taxonomy as V4. Final decision
from the same options A-E.

**Reporting commitment:** the complete family is reported, including every failure,
in the same table as any success. No hypothesis is added, dropped, redefined or
re-directed after this freeze. If something interesting turns up outside this
family it is labelled EXPLORATORY and is not eligible to support a decision.
