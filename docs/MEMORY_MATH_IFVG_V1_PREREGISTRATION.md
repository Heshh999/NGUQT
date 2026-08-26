# MEMORY-MATH-IFVG-V1 — PREREGISTRATION / MENU FREEZE

Frozen: 2026-08-26 (UTC). Status at freeze: **NO OUTCOME OF ANY MENU
ITEM HAS BEEN COMPUTED.** This document freezes every formula,
definition, control, floor, multiplicity count, ceiling, and gate
BEFORE execution. Execution requires a separate directive.

Mission: (Lane A) find the mathematical conditions that modulate the
strength of the frozen MEMORY-PRED effect; (Lane B) test whether the
IFVG (inversion fair value gap) is a real incremental state-transition
object or a visual name for generic failure/reversal; then evaluate at
most four pre-declared strategy hypotheses on raw geometry only.

Epistemic ceiling: 2019→2026 is fully EXPOSED for MEMORY-derived
research. Everything producible here is EXPLORATORY /
DEVELOPMENT-DERIVED. No historical subset may be called OOS,
prospective, or validated edge. Best possible labels:
DEVELOPMENT-SUPPORTED MATHEMATICAL ANOMALY and EXPLORATORY-DERIVED
STRATEGY CANDIDATE.

Absolute protection (unchanged, restated): MEMORY-PRED-V1, RVMR-V1,
OFH13_PROSPECTIVE_V1, OFH14_PROSPECTIVE_V1, the RVMR forward logger,
the MEMORY prospective lane (start 2026-08-26 00:00:00 ET — no row at
or after that timestamp may be consumed by this study; the frozen grid
ends 2026-08-17), and the NinjaTrader prospective host are not
modified. No orders. Offline research only.
**THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 0. SHARED FROZEN MACHINERY

All Lane-A and Lane-B objects are computed on the canonical grid and
conventions below. Nothing else may be substituted at execution time.

- Grid: `analysis/rvmr/rvmr_run.py::load_bars()`, STAMP_SHIFT = 0,
  close-stamped ET, 2,503,622 bars, 2019-07-04 18:25 → 2026-08-17
  15:16. Contiguity clock `em` (minutes since 2019-01-01). Gaps are
  skipped, never bridged; any object whose window spans a broken `em`
  chain is UNAVAILABLE at that bar.
- Return: `r[t] = log(c[t]/c[t−1])`, requires `em[t]−em[t−1]==1` and
  positive closes. `r[t]==0` carries no sign: any object needing
  `sign(r[t])` excludes/neutralizes such bars (MEMORY-PRED convention).
- RVMR state: `RB[t] = bucket(trailing_ratio(range)[t])`,
  `trailing_ratio[i] = x[i]/mean(x[i−1440..i−1])`, T1 = 1.270,
  T2 = 2.335, W = 1440 (`analysis/rvmr/rvmr_spec.py`). Causal at the
  close of bar t. The underlying score is `rr[t]` (the ratio itself).
- memoryReturn: `m[t] = sign(r[t]) · r[t+1]` in bp (×1e4).
  Continuation indicator uses `r[t+1] ≠ 0` and sign match.
- `atr[t]` = SMA(20) of true range (frozen atr20).
- ToD buckets (frozen): OVERNIGHT `mod ≥ 1081 or ≤ 569`; RTH_AM
  570–750; RTH_PM 751–960.
- Cost: 0.87 pt round turn, frozen. MNQ $2/pt. bp→points conversion
  per event: `points = c[t] · bp / 1e4`; aggregates report the mean.
- Frozen anchors from the MEMORY-PRED-V1 record (development, exposed):
  Δ(HIGH−LOW) memoryReturn ≈ +0.30013 bp; P(cont) LOW 0.4813 / HIGH
  0.5138 (+3.25 pp); standalone effect ≈ 0.648× cost (SUB-COST).
- Inference (frozen): day-cluster percentile bootstrap on the OUTCOME
  bar's day, B = 20,000, **seed 20260826**, 95% CI, two-sided p
  floored at 1/(B+1). Permutation null: within-day CIRCULAR ROTATION
  of the condition-label sequence (programme convention for serially
  dependent labels; preserves run structure, breaks alignment),
  P = 20,000, same seed stream.
- Feature-only cutpoints (A5): where a menu item uses data-derived
  terciles, they are computed OUTCOME-BLIND over the full feature
  distribution at execution start and printed before any outcome join
  (programme precedent: ATR tercile freeze). No outcome ever touches a
  cutpoint.
- Execution engine directory (when authorized): `analysis/memifvg/`.

---

## 1. PART 1 — LINEAGE AUDIT

| Object | Previously tested? | Result | Settled? | What remains open |
|---|---|---|---|---|
| AC-FLIP | Yes (SCAN-V1; CONFIRM-V1 replication) | Replicated incl. adjacency restriction; absorbed as the marginal behind MEMORY-PRED | Yes | Nothing standalone |
| MEMORY-PRED-V1 | Yes (10/10 dev gates) | Real, SUB-COST standalone (0.648× cost) | As standalone, yes | **Conditional amplification — this study (Lane A)** |
| LEVERAGE-V | Yes (scan + CONFIRM-V1) | Calibrated, replicated, forecast-REDUNDANT | Yes | Control use only |
| RVMR state duration / flicker | Characterized descriptively (RVMR-V1 battery) | Dwell/flicker facts only | Descriptively | **Never used to condition MEMORY → A1/A2** |
| Serial correlation | Lag-1: real (MEMORY-PRED). 5m: significantly ANTI-persistent all states (MOM-H1 FAILED). 30m: trend real, RVMR-redundant (MOM-H2) | Mixed, all frozen | Yes at those lags | **Decay profile 1→5m by state → A8** |
| Variance ratios | Not directly tested | — | No | Partially covered by A5/A7; no standalone VR test added (menu discipline) |
| Entropy / sign order | Ordinal 3-bar motifs tested (V-turn) | ORDINAL-V-TURN partially confirmed (13/14; overnight-only ToD fail) — frozen knowledge object | Yes as V-turn | **Flip-count conditioning of MEMORY (A6), with declared incrementality duty vs A4/V-turn** |
| Run structure | Run-age hazard decline (Wave-3 + confirm2 diagnostic); V-turn | Hazard decline real (diagnostic); aged-run reversal drives V-turn | Diagnostically | **Run length as MEMORY conditioner with magnitude controls → A4; hazard motivates A1 boundaries** |
| Shock continuation | Yes (SHOCK-CONT-MEDIUM) | FAILED HOLDOUT | Yes — negative | Excluded. A7 conditions the lag-1 memory on ATR trajectory, declared distinct from large-|return| continuation |
| Ordinal V-turn | Yes (CONFIRM-V2) | PARTIALLY CONFIRMED, overnight; RVMR amplification did NOT replicate | Yes | Not re-run here; A6 must be incremental to it |
| FVG (as such) | Implemented inside OFH13/OFH14 (displacement-qualified, OF grid) | Entry component only; hold-vs-invert never studied | No | **B1/B2** |
| IFVG | Never tested anywhere in the programme | — | No | **B1–B6 (all of Lane B)** |
| FVG mitigation | Yes (OFH13 mechanism, prospective) | Frozen, prospective | Yes | Untouched; Lane B uses no mitigation logic |
| OFH13 FVG mechanics | Yes | Frozen prospective candidate | Yes | **No MEMORY attachment — closed by the OFH13-MEMORY-V1 record (INSUFFICIENT; diagnostic ran opposite). Not revisited here** |
| OFH14 displacement/FVG | Yes | Frozen prospective | Yes | Untouched |

Also excluded (failed/refuted, never re-tested under new names):
MONDAY / MONDAY-RTH, HALF-SESSION-LOW, Donchian position, VWAP
occupancy, OBV divergence, daily TSMOM, simple 5m momentum, simple 30m
trend-extension. No Lane-A or Lane-B object below re-tests any of
these; where adjacency exists it is named and an incrementality duty
is frozen.

---

## 2. LANE A — PURE MEMORY MATHEMATICS (no ICT concepts)

Driving question: the +3.25 pp / +0.30 bp average is an average over
heterogeneous states — which causal conditions concentrate it?
Each module has exactly ONE primary contrast. All conditioning
variables are causal at the close of bar t. Population per module: all
bars where `r[t] ≠ 0`, RB[t] defined, `r[t+1]` defined, plus the
module's own availability rule. Every module reports: memoryReturn
(bp), P(cont), HIGH−LOW separation, and economics (bp / NQ points /
fraction of 0.87 pt).

### A1 — RVMR STATE AGE
`age(t)` = number of consecutive bars ending at t with `RB == RB[t]`,
counted back until state change, contiguity break, or undefined RB;
capped at 240. Groups (frozen; boundaries motivated by the
pre-existing run-age-hazard record, not tuned): FRESH 1–3, YOUNG 4–15,
ESTABLISHED 16–60, MATURE ≥ 61.
**Primary A1: HIGH-state memoryReturn, FRESH minus MATURE.**
Secondary: same in LOW; HIGH−LOW separation by age group.

### A2 — RVMR STATE TRANSITIONS
Label at t: `(RB[t−1] → RB[t])`, requires `em[t]−em[t−1]==1`, both
defined. Nine cells. ARRIVAL = state changed; PERSISTENCE = unchanged.
**Primary A2: memoryReturn in HIGH-ARRIVAL (LOW→HIGH ∪ MED→HIGH)
minus HIGH-PERSISTENCE (HIGH→HIGH).**
Secondary: LOW-ARRIVAL vs LOW-PERSISTENCE; full 9-cell table.
Relation to HARU (declared): the state-arrival law concerned activity
propensity and was forecast-redundant for magnitude; whether arrival
modulates the DIRECTIONAL memory effect was never tested — that is A2.

### A3 — RVMR SCORE VELOCITY
`v(t) = rr[t] − rr[t−5]`, requires `em[t]−em[t−5]==5` and both scores
defined. ONE window (5), no sweep. Categories (fixed numbers, frozen;
±0.10 ≈ 9% of the 1.065 inter-threshold span): RISING v > +0.10,
FALLING v < −0.10, FLAT otherwise.
**Primary A3: HIGH-state memoryReturn, RISING minus FALLING.**
Secondary: LOW-state table; interaction with A2 arrival reported
descriptively only.

### A4 — RUN LENGTH
`runlen(t)` = consecutive bars ending at t with the same nonzero
`sign(r)`; zeros or contiguity breaks end the run. Categories: 1, 2,
≥3. Controls (mandatory, common-weight construction of §5): |r[t]|
tercile × net-run-return-magnitude tercile.
**Primary A4: LOW-state memoryReturn, runlen ≥ 3 minus runlen = 1**
(aged-run reversal; motivation frozen from the ORDINAL-V-TURN record).
Secondary: HIGH-state by runlen; P(cont) by runlen × state.

### A5 — PATH EFFICIENCY
`eff(t) = |c[t] − c[t−10]| / Σ_{i=t−9..t} |c[i] − c[i−1]|`, requires
`em[t]−em[t−10]==10`, denominator > 0. ONE window (10). Categories:
outcome-blind full-sample terciles (§0), printed before any outcome
join.
**Primary A5: HIGH-state memoryReturn, top (efficient) tercile minus
bottom (noisy) tercile, standardised within |r[t]| terciles
(common-weight).**

### A6 — SIGN ORDER / FLIP COUNT
`flips(t)` = sign changes among `r[t−7..t]` (8 returns, all nonzero,
contiguous; else unavailable). Categories: ORDERLY ≤ 2, MIXED 3–4,
CHOPPY ≥ 5. No pattern mining beyond this single statistic.
**Primary A6: HIGH-state memoryReturn, ORDERLY minus CHOPPY.**
Incrementality duty (frozen): A6 is additionally reported standardised
within A4 runlen categories; if the effect vanishes there, A6 is
declared REDUNDANT WITH RUN LENGTH. A6 conditions the standing
memory effect and does not re-score the V-turn contrast.

### A7 — VOLATILITY ACCELERATION
`va(t) = atr[t]/atr[t−15]`, requires `em[t]−em[t−15]==15`, both
defined. Categories (fixed, frozen): EXPANDING ≥ 1.15, CONTRACTING
≤ 1/1.15, STABLE otherwise. ONE window (15).
**Primary A7: HIGH-state memoryReturn, EXPANDING minus STABLE.**
Declared distinct from the failed SHOCK-CONT object: A7 conditions the
lag-1 signed memory on the ATR trajectory; it does not test
large-|return| continuation.

### A8 — PERSISTENCE DECAY
Horizons frozen: H = {1, 2, 3, 5} minutes.
`m_h(t) = sign(r[t]) · (log c[t+h] − log c[t])`, full contiguity to
t+h required. Report per state: cumulative m_h and per-minute
increments `sign(r[t])·r[t+j]`, j = 1..5.
**Primary A8: HIGH-state incremental information beyond the first
minute, `m_3 − m_1`, with CI.**
Consistency note (frozen expectation, not a gate): MOM-H1 found 5m
aggregate anti-persistence; A8 quantifies where the decay completes
per state. A negative increment is knowledge, not failure of A8's
execution.

### Lane-A economics rule
For every reported condition: mean effect in bp, NQ points, and
fraction of 0.87 pt. A condition is flagged MATERIAL only if its
conditional per-event directional effect is ≥ 2× the unconditional
Δ anchor (≥ +0.60 bp) AND ≥ 1.0× cost in point terms at the +1m
horizon. Barely-crossing-cost alone never promotes (gates in §7).

---

## 3. LANE B — IFVG / FAILED-IMBALANCE RESEARCH

### 3.1 Public-concept audit (recorded citations)

Public IFVG teaching (ICT lineage) holds that: (1) a fair value gap is
a three-candle imbalance; (2) an FVG that price closes through —
rather than respects — is "inverted"; (3) the inverted gap flips
role (support↔resistance); (4) traders then watch a retest of the
inverted zone for rejection or acceptance. Sources consulted
2026-08-26 (concept audit only; NO profitability claim from any of
them is treated as evidence; several pages were egress-blocked from
this environment, so the record is the URL + concept summary):

- TradingView — "Inversion Fair Value Gaps [TradingFinder] IFVG ICT
  Signal" (tradingview.com/script/psYi1bbM-…)
- LuxAlgo — "Inversion Fair Value Gaps (IFVG)"
  (luxalgo.com/library/indicator/inversion-fair-value-gaps-ifvg/)
- FXOpen — "What Are Inverse Fair Value Gaps (IFVGs) in Trading?"
  (fxopen.com/blog/en/what-is-an-inverse-fair-value-gap-ifvg-concept-in-trading/)
- TradingFinder — "Inverse Fair Value Gap (IFVG) in ICT; Bullish &
  Bearish" (tradingfinder.com/education/forex/ict-inversion-fair-value-gap/)
- innercircletrader.net — "ICT Inverse Fair Value Gap (IFVG)"
  (innercircletrader.net/tutorials/ict-inversion-fair-value-gap/)
- howtotrade.com — "Inversion Fair Value Gap (iFVG) Trading Guide"
  (howtotrade.com/blog/inverse-fair-value-gap/)

**Declared separation: the mechanical implementation in §3.2 is OURS.
It is a repository-consistent mathematical translation of the public
concept and is NOT claimed to be any official ICT strategy.** Public
refinements (liquidity sweeps, premium/discount) are deliberately NOT
implemented — they would multiply the family.

### 3.2 B1 — FROZEN MATHEMATICAL IFVG (all rules mechanical)

On the §0 grid, for a contiguous bar triple (k−2, k−1, k):

- **Bullish FVG** at k: `h[k−2] < l[k]`. Zone = `[h[k−2], l[k]]`
  (bottom, top). Gap size `l[k] − h[k−2]`.
- **Bearish FVG** at k: `l[k−2] > h[k]`. Zone = `[h[k], l[k−2]]`.
  Gap size `l[k−2] − h[k]`.
- Repository note (declared): OFH13/OFH14 use displacement-QUALIFIED
  FVGs on the order-flow grid. Lane B uses PLAIN price FVGs on the
  2019→2026 grid. Different object, deliberately.
- **Size qualification (primary population):** gap ≥ 0.25·atr[k],
  atr defined. (Secondary, reported once, not promotable: all gaps
  ≥ 1 tick = 0.25 pt.) No other size classes, ever.
- **Formation timestamp** = close of bar k. Causally available then.
- **Lifespan / tracking:** 120 bars after k, bar-by-bar contiguity
  required; a broken `em` chain drops the FVG as UNRESOLVED (counted,
  excluded from outcomes). Overlapping FVGs are tracked independently.
- **Touch** (bullish FVG): first bar j in (k, k+120] with
  `l[j] ≤ zone_top`. Mirror: `h[j] ≥ zone_bottom`.
- **HOLD:** after the first touch, a CLOSE beyond the zone's near
  boundary in the original direction (bullish: `c[j'] > zone_top`)
  occurring BEFORE any inversion close.
- **INVERSION:** a CLOSE through the far boundary (bullish FVG:
  `c[j] < zone_bottom`; bearish: `c[j] > zone_top`) within lifespan.
  The failed bullish FVG becomes a **bearish IFVG** (zone now
  resistance); the failed bearish FVG becomes a **bullish IFVG**.
  **IFVG available timestamp = close of the inverting bar j.**
  Inverted direction `dI`: bearish IFVG → −1, bullish IFVG → +1.
- First of {HOLD-close, INVERSION-close} decides; a single close
  cannot be both (closes are points, boundaries ordered).
- **Retest (single frozen definition, no variants):** after inversion
  at j, within (j, j+60] with contiguity: first bar q where price
  re-enters the zone (bearish IFVG: `h[q] ≥ zone_bottom`; bullish:
  `l[q] ≤ zone_top`), then the first subsequent CLOSE back beyond the
  near boundary in the inverted direction (bearish IFVG:
  `c[q'] < zone_bottom`, q' ≥ q, q' ≤ j+60) = **RETEST-REJECT event**
  at close of q'. Mirror for bullish.
- **Invalidation:** a close back through the zone's far boundary
  AGAINST `dI` (re-inversion) at any point after j kills the IFVG
  (no event; counted). No-return within 60 bars = NO-RETEST (counted).
- One retest event maximum per IFVG (the first). Per-direction 30-bar
  cooldown on retest events to prevent overlapping-zone double counts
  (frozen; matches programme cooldown idiom).

### 3.3 B2 — WHICH FVGS INVERT? (classification)
Population: size-qualified FVGs whose zone is TOUCHED within lifespan
(UNTOUCHED and UNRESOLVED counted, excluded). Outcome: INVERT vs HOLD
(first-close race above). Predictors — ONLY these, all causal at
formation close k: RB[k]; MEMORY implication at k relative to the
FVG's original direction (ALIGNED/OPPOSED/NEUTRAL via §4 rule with
`dF` = original FVG direction); A3 velocity category at k; A4 runlen
at k; A5 efficiency tercile at k.
**Primary B2: inversion-rate difference, MEMORY-OPPOSED minus
MEMORY-ALIGNED (memory against the imbalance predicts failure).**
Secondary: one-way tables for each listed predictor; ONE fixed
logistic regression on exactly these five predictors (reported
descriptively, no selection, no interactions).

### 3.4 B3 — WHAT HAPPENS AFTER INVERSION?
Event: inversion close j, direction `dI`. Frozen horizons +1, +3, +5,
+15 min: signed `dI·(log c[j+h] − log c[j])`; MFE/MAE in points over
15 bars; favorable-first at ±1.0·ATR within 60 min (the repository
ffpct convention transported verbatim: FAV first = 1, ADV first = 2,
same-bar excluded, neither excluded).
**Primary B3: +5m signed post-inversion return > 0 (CI excludes 0).**
Horizon +5m is declared primary NOW, before results.

### 3.5 B4 — IFVG RETEST
Events per §3.2 retest-reject definition. Same outcome set as B3,
measured from the retest-reject close.
**Primary B4: +5m signed post-retest return > 0.**

### 3.6 B5 — MEMORY × IFVG (key interaction)
At the retest-reject close τ: MEMORY implication via §4 (RB[τ],
r[τ]). Classes: M-ALIGNED (implication == dI), M-OPPOSED, M-NEUTRAL.
**Primary B5: Δ(+5m signed return), M-ALIGNED minus M-OPPOSED.**
This is a NEW hypothesis; the answer is not assumed. Floors in §6
apply; if unmet → INSUFFICIENT for B5 (no loosening).

### 3.7 B6 — GENERIC-FAILURE CONTROL (essential; not a hypothesis)
Generic price-only failed-directional-structure event: bar b with
`c[b] > max(h[b−30..b−1])` (30-min close breakout up; contiguity
required), then within 30 bars a close `< l[b]` → FAILURE event at
that close, direction −1. Mirror for down breakouts. First event per
direction with 30-bar cooldown.
Comparison: B3 and B4 event outcomes vs matched generic-failure
outcomes, matched common-weight on ATR tercile × ToD bucket ×
|15m preceding return| tercile (cells ≥ 10 on both sides).
**Redundancy rule (frozen): if the IFVG event drift does not exceed
the matched generic-failure drift (matched difference CI including 0
or negative), the verdict is IFVG REDUNDANT WITH GENERIC
FAILURE/REVERSAL STRUCTURE — regardless of B3/B4 significance.**

---

## 4. FROZEN MEMORY-IMPLICATION RULE (used by B2/B5/S4)

At decision bar t with direction-of-interest d*:
`RB[t] = HIGH` → implication `sign(r[t])`; `RB[t] = LOW` →
implication `−sign(r[t])`; `RB[t] = MEDIUM` → NEUTRAL (the frozen
MEMORY-PRED source assigns MEDIUM no directional meaning — CI includes
0 — and none is invented); `r[t] = 0`, RB undefined, or contiguity
broken → NEUTRAL/UNAVAILABLE. ALIGNED iff implication == d*; OPPOSED
iff implication == −d*. Identical to the OFH13-MEMORY-V1 recorded
causal rule; RB[t] is causal at the close of t.

---

## 5. STRATEGY HYPOTHESES (max 4 — frozen BEFORE any outcome)

Raw geometry ONLY: signed returns at +1/+3/+5/+15m, MFE/MAE (15
bars), FF@±1.0·ATR/60m, and cost-adjusted simple horizon outcome
(gross points − 0.87) at +5m and +15m. NO stop, target, trailing,
breakeven, or partial-exit research. If raw geometry cannot plausibly
clear cost, the strategy fails before management research. Direction
measurement only; no orders.

Amplification conditions are picked NOW, from pre-existing frozen
knowledge, so none can be chosen after seeing Lane-A outcomes:

- **S1 — HIGH MEMORY CONTINUATION.** Bars with RB[t]=HIGH, r[t]≠0,
  AND A1 age(t) ≤ 3 (FRESH). Direction = sign(r[t]).
  Amplifier justification (pre-result): the run-age-hazard record
  shows memory information is spent within ~3 minutes; fresh states
  are where arrival information lives.
- **S2 — LOW MEMORY REVERSAL.** Bars with RB[t]=LOW, r[t]≠0, AND A4
  runlen(t) ≥ 3. Direction = −sign(r[t]).
  Justification (pre-result): the ORDINAL-V-TURN record shows aged
  runs reverse; LOW is the frozen reversal state.
- **S3 — MEMORY STATE-TRANSITION.** Bars where RB[t]=HIGH and
  RB[t−1] ∈ {LOW, MEDIUM} (the A2 HIGH-ARRIVAL object), r[t]≠0.
  Direction = sign(r[t]).
- **S4 — IFVG × MEMORY.** B4 retest-reject events with M-ALIGNED
  classification (§3.6). Direction = dI. Incremental comparisons
  (mandatory): S4 vs IFVG-alone (all B4 events) and S4 vs
  MEMORY-alone (matched non-IFVG bars with the same implication,
  common-weight on ToD × ATR tercile).

No EMA, no VWAP, no discretionary confirmation, no entry delay, no
re-entry logic, anywhere.

---

## 6. CONTROLS, FLOORS, MULTIPLICITY

### Controls (mandatory)
Every Lane-A candidate: last-return-sign alone (unconditional memory);
RVMR state alone; ATR terciles; ToD buckets; |r[t]| magnitude
terciles; 5m-momentum sign. Every Lane-B candidate: IFVG alone;
MEMORY alone; the B6 generic-failure control. Standardisation: the
programme's corrected common-weight difference-of-means (cell weight
= nA+nB; Lane-A cells ≥ 30 both sides, Lane-B cells ≥ 10 both sides).
Placebo: within-day circular rotation permutation (§0) for every
primary.

### Sample floors (frozen; unmet → INSUFFICIENT, never loosened)
- Lane A: every cell entering a primary contrast ≥ 5,000 events and
  ≥ 200 distinct days.
- Lane B: qualified FVGs ≥ 2,000; touched population ≥ 1,000;
  inversions ≥ 500; retest-reject events ≥ 200 on ≥ 120 distinct
  days; B5/S4 arms (M-ALIGNED and M-OPPOSED) ≥ 60 events each on
  ≥ 40 days each.
- S1–S3: ≥ 5,000 events, ≥ 200 days each.

### Multiplicity (frozen family; never-shrink)
- Lane A primaries: A1–A8 = **8**.
- Lane B primaries: B2, B3, B4, B5 = **4** (B6 is a control/verdict
  rule, not a promotable hypothesis).
- Strategy primaries: S1–S4 = **4** (each primary = cost-adjusted +5m
  mean > 0). Hierarchical gatekeeping: a strategy is ELIGIBLE for
  promotion only if its parent object survives (S1←A1, S2←A4,
  S3←A2, S4←B5); geometry is reported for all four regardless.
- **M_math = 12** — BH at q ≤ 0.05 across all 12, binding.
- **M_strat = 4** — BH at q ≤ 0.05 across all 4, binding,
  in addition to the gatekeeping.
- **M_total = 16.** Programme cumulative ledger: 8 prior + 16 = 24
  (reported, non-binding, never shrunk). Failed cells stay in the
  family.

### Candidate ceiling (hard)
At most **2 mathematical anomalies** and **1 strategy hypothesis**
advance, chosen by the frozen gates below — never by narrative. If
IFVG is not among survivors, it is not forced forward.

---

## 7. PROMOTION GATES (frozen)

### Mathematical anomaly — ALL of MA1–MA8
1. MA1 causality: every input available at/ before the decision close;
   availability table printed.
2. MA2 floors met (§6).
3. MA3 effect size: primary contrast ≥ 2× the unconditional Δ anchor
   (≥ +0.60 bp) in the predicted direction.
4. MA4 dependence-aware support: bootstrap CI excludes 0 AND BH q ≤
   .05 (M_math = 12) AND rotation-permutation p ≤ .05.
5. MA5 year stability: effect same sign in ≥ 5 of the 8 exposed years
   (2019–2026, partial years count).
6. MA6 ToD stability: same sign in ≥ 2 of 3 frozen buckets.
7. MA7 controls: survives common-weight standardisation vs ATR, |r|
   magnitude, ToD; and (Lane A) is not absorbed by last-return-sign
   alone or state alone; (Lane B) beats the B6 control per §3.7.
8. MA8 tail robustness: within-condition top-1% and top-5%
   |outcome| trims keep the primary sign and ≥ 50% of magnitude.

### Strategy hypothesis — ALL of SG1–SG12
1. SG1 parent anomaly survived MA1–MA8.
2. SG2 directionality correct (predicted sign observed).
3. SG3 raw geometry favorable: +5m gross mean > 0, CI excludes 0.
4. SG4 MFE/MAE useful: mean MFE/MAE ≥ 1.2 over the 15-bar window.
5. SG5 FF useful: FF@1.0ATR > 50% with CI excluding 50%.
6. SG6 cost: +5m or +15m gross mean ≥ 1.0× cost (0.87 pt) with CI
   lower bound ≥ 0.5× cost. No management may manufacture this.
7. SG7 year stability: net (cost-adjusted) mean same sign ≥ 5/8 years.
8. SG8 ToD stability: gross sign ≥ 2/3 buckets.
9. SG9 tail robustness: top-1%/5% trims keep gross sign.
10. SG10 incremental vs controls: survives every §6 control
    common-weight; S4 additionally beats IFVG-alone and MEMORY-alone.
11. SG11 corrected support: BH q ≤ .05 (M_strat = 4) and permutation
    p ≤ .05 on the cost-adjusted primary.
12. SG12 no management dependency: all of SG1–SG11 achieved on raw
    frozen geometry only.

### Verdict taxonomy (frozen)
Per object: PROMOTED (all gates) / REAL-BUT-SUB-COST (MA passed, SG6
failed) / REDUNDANT (specific control named) / FAILED (failing gates
named) / INSUFFICIENT (floors unmet). Any non-covered failing pattern
maps to FAILED with gates named. If nothing survives:
**"MEMORY-MATH-IFVG-V1 FOUND NO MONETIZABLE MEMORY AMPLIFICATION —
MEMORY-PRED remains REAL PREDICTIVE STRUCTURE BUT SUB-COST
STANDALONE"** and the search does NOT expand. If an anomaly survives
but no strategy does: the mathematics is frozen as knowledge; no
forced monetization. If IFVG survives, the findings must state exactly
WHICH object survived (inversion prediction / post-inversion drift /
retest behavior / MEMORY interaction) — never "IFVG works".

### No-variant rule
If a menu item fails, the named nearby variants are NOT tested:
other age/velocity/efficiency/entropy windows or thresholds, 2m/3m
memory, other RVMR thresholds, other FVG size classes, other
violation/retest definitions, wick-based inversion, other horizons,
side-only versions, different FF thresholds. Any alteration is a new
V2 preregistration.

---

## 8. PROSPECTIVE REQUIREMENT

Historical survival here confirms nothing. Any surviving candidate is
frozen in its own commit; its prospective evaluation start is the
first ET midnight AFTER that freeze commit — never backdated. For a
surviving strategy candidate, prospective evaluation compares every
future qualifying event under ORIGINAL / ALIGNED / OPPOSED / NEUTRAL
(or condition-on/off) classifications WITHOUT altering any live/Sim
execution; a shadow logger is built only under separate authorization.
The MEMORY-PRED Lane A prospective lane (2026-08-26 start) is
untouched and is not this study's confirmation vehicle.

---

## 9. EXECUTION AUTHORIZATION

This document authorizes NOTHING beyond itself. Execution (computing
any Lane-A, Lane-B, or strategy outcome) requires a separate
directive, must verify this file's sha256 first, must run each menu
item exactly once, and must publish all cells including failures.
