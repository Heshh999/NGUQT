# OFH13-POSTENTRY-V1 — CAUSAL POST-ENTRY STATE + RIGHT-TAIL DEVELOPMENT — PREREGISTRATION

Frozen 2026-08-26 (UTC). **NO OUTCOME HAS BEEN COMPUTED.** No feature
value, no future MFE, no future P&L, no win rate, no tail probability,
no p-value, no ranking exists. Only the checkpoint-eligibility COUNTS
required by the directive were computed (§5), and the sample floors in
§18 were fixed at drafting time before that script was run.

**Question.** Not "which OFH13 winners looked good after entry" — that
is hindsight anatomy. Instead: *at +5 or +15 minutes, using only
information available at that moment, what if anything tells us about
the part of the trade that has not happened yet?*

**Absolute protection (restated, unchanged).** OFH13_PROSPECTIVE_V1,
OFH13 entry logic, OFH13 ATR1.5 stop, OFH13 60-minute exit, the OFH13
prospective logger, OFH14, RVMR-V1, MEMORY-PRED-V1, NinjaTrader strategy
behaviour and all order-submission paths are NOT modified. **No
management rule is created in this study.** Offline research only. No
orders. **THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.**

---

## 1. PHASE 0 — PRIOR-WORK AUDIT (exclusions are binding)

| Object | Exact question asked | Result | Settled? | Overlap with this study |
|---|---|---|---|---|
| OFH13-V2 destruction (~25 tests) | can historical expectancy improve without destroying the tail? | **NO** — every proposal destroyed by its own gate | **SETTLED** | Bounds the whole study; no proposal here may become a management change |
| Winner/loser entry features (12, tercile+monotonicity) | can losers be identified **pre-entry**? | NO — the 2 monotone features (`ext_mid`, `inv`) **invert on IR** | SETTLED | **EXCLUDED** — all pre-entry grading |
| Study 8–9 winner development (3m/5m/10m/60m medians of unrealised / MFE / MAE by eventual class) | do winners announce early? | announce YES, but **76/85 losers also reach +0.25R**; separation is early adverse depth | SETTLED as anatomy | **CONTAMINATES THE BASELINE** — see §2. Not re-run; this study forbids outcome-conditioned anatomy |
| Study 10 early-failure exits (no +0.25R by 10m; by 15m; +0.5R by 20m) | defensive exit on early progress? | **VACUOUS** — fires on 1–2 of 133 | SETTLED | **EXCLUDED** — no early-progress exit rule, no threshold-on-early-return rule |
| Study 11 stop family (1.25/1.0 ATR, STRUCT) | tighter risk? | uniformly worse; STRUCT deletes 4 of the top 10 winners | SETTLED | **EXCLUDED** — no stop change |
| Registry §5–6 fixed-R maps (9 targets × 4 exits × 3 partitions) | fixed-R payoff plateau? | **none anywhere**; OFH13 −0.26…+0.06 R/trade | SETTLED | **EXCLUDED** — no fixed-R target |
| Registry §5–6 stop × time exit (36 cells) | best stop/exit? | ATR1.5 + 60m wins on risk and stability | SETTLED | **EXCLUDED** — no exit-time change |
| G1 delayed/limit entry overlay | better entry price? | **NOT ADOPTED** — per-parent EV B +11.81 vs A +21.04; 23 unfilled events averaged ≈ +107 pt | SETTLED | **EXCLUDED** — no entry modification |
| 30s execution (two genuine studies) | LTF execution improvement? | **wash** (+19.87 → +20.77 per parent, entry median 1.50 pt worse) | SETTLED at 30s | **EXCLUDED**; 5s/15s remains under-sampled and is not this study |
| Quality score / A+A−B+ grading | monotone multi-dimensional grade? | **UNSUPPORTED** — zero dimensions survived IR | SETTLED | **EXCLUDED** |
| RVMR-AVOID-V1 | avoid RVMR HIGH? | HIGH inflates favourable and adverse **in lockstep**; no avoidance rule | SETTLED | RVMR may NOT be used as an entry filter; F4 is post-entry evolution only |
| OFH13-MEMORY-V1 | MEMORY-PRED at OFH13 entry | INSUFFICIENT (ALIGNED n=10); diagnostic ran **opposite** | SETTLED | **EXCLUDED** — no MEMORY feature anywhere |
| Long vs short grading | is the short edge structural? | not explained by any measured entry condition; likely regime | DIRECTION-SPECIFIC, needs validation | Side is a reported split, never a promotable rule |
| PROFIT-TAKING study | why are few points captured? | MFE and MAE are **the same distribution**; every fixed exit ≤ 0 | SETTLED | **EXCLUDED** — no profit-taking rule |
| `cand_audit.path()` per-partition geometry | medMFE/medMAE/tMFE/tMAE/ff0.5/ff1/ff2, net at m=5,10,15,20,30,45,60 | descriptive record | descriptive | **CONTAMINATES** the post-entry path at aggregate level (§2) |

**Nothing above is re-opened, re-named, or re-tested.** Every F-family in
§9–§14 was checked against this table: none is materially equivalent to
a previous failed test. What is genuinely new is **post-entry state as a
predictor of the strictly-future remainder** — the repository has only
ever looked at post-entry path as (a) outcome-conditioned anatomy or
(b) an input to a management rule, never as a causal forward predictor
evaluated on a non-overlapping window.

## 2. PHASE 0B — CONTAMINATION / DATA MAP

| Attribute | Status |
|---|---|
| Date range | 2025-08-18 → 2026-08-19 (OF capture; 355,455 bars) |
| Events | 133 (UNSEEN 16 ≤ 2025-11-01 / DEV 57 ≤ 2026-03-31 / IR 60) |
| OFH13 **outcome** previously viewed? | **YES, exhaustively** — registry §5–6 (36 management cells), OFH13-V2 (~25 tests), and the per-event listing at commit `4cbb81b` (FF / MFE / MAE / P&L / winner-loser for all 133) |
| Post-entry **path** previously inspected? | **YES** — `cand_audit.path()` reports MFE, MAE, time-to-MFE/MAE, favorable-first and net at m = 5, 10, 15, 20, 30, 45, 60; OFH13-V2 Studies 8–9 reported unrealised/MFE/MAE at 3m, 5m, 10m, 60m **split by eventual winner/loser** |
| The **new** feature families (F1–F6) previously inspected? | **NO** — post-entry path efficiency, excursion shape, structural acceptance/reclaim relative to OFH13's own zone, post-entry RVMR evolution, post-entry directional alignment, and T15 acceleration have never been computed on OFH13 in any form |
| Genuinely unexamined hypothesis-specific segment? | **NONE EXISTS** — the registry data-freeze line is 2026-08-19 and the capture ends 2026-08-19 16:59, so there are **zero** post-freeze OFH13 parents |

> **ALL AVAILABLE HISTORICAL DATA IS DEVELOPMENT DATA FOR THIS STUDY.**
> No historical partition — UNSEEN, DEV or IR — may later be called
> independent confirmation. There is no PROTECTED segment to reserve,
> because none exists.

**A second-order contamination that materially weakens any positive
result, stated up front:** the baseline controls this study demands a
feature beat (signed return to T, MFE to T, MAE to T) were **themselves
already viewed conditioned on eventual outcome** in Studies 8–9, at
exactly 5m among other horizons. A feature that "adds information beyond
the baseline" is therefore clearing a bar that is itself contaminated,
and that claim is weaker than it looks. This does not change any gate;
it changes how a survivor must be described.

## 3. CORE CAUSAL PRINCIPLE (binding on every family)

Feature measurement ends at checkpoint **T**. Outcome begins **strictly
after T**. The first T minutes may never appear in both. Every family
must pass an explicit **overlap check**: the engine prints, per family
and checkpoint, the last bar index used by the feature and the first bar
index used by the outcome, and asserts `first_outcome_bar > last_feature_bar`.

## 4. CHECKPOINTS

Exactly two binding checkpoints: **T5 = entry + 5 minutes** and
**T15 = entry + 15 minutes**, measured on the frozen OF 1-minute grid,
with strict `tmin` contiguity from the entry bar (a gap makes the event
unavailable at that checkpoint). **No other checkpoint is tested** — not
1, 2, 3, 4, 6, 7, 8, 10, 12, 20 or 30 minutes. F6 is **T15-only**.

## 5. CHECKPOINT ELIGIBILITY (counts computed; no outcome)

`T-ELIGIBLE` = the position is **still open at +T under the entirely
unchanged frozen OFH13 management** (ATR1.5 stop, no target, 60m exit),
i.e. the stop was not touched in bars entry+1 … entry+T. **The stop and
exit are not altered to increase eligibility.**

This is explicitly a **causal survivor population**: the question is
"given the trade is still open now, what can be known now?" — not "what
happens to an average OFH13 trade". 29% of parents are already gone by
T5 and 45% by T15, so the eligible set is heavily selected, and no
result may be described as applying to all 133 parents.

| population | n | days | LONG | SHORT | UNSEEN / DEV / IR |
|---|---|---|---|---|---|
| all parents | 133 | 108 | 55 | 78 | 16 / 57 / 60 |
| **T5-ELIGIBLE** | **95** | **81** | 38 | 57 | 14 / 36 / 45 |
| **T15-ELIGIBLE** | **73** | **64** | 32 | 41 | 13 / 27 / 33 |

Stopped by +5m: 38. Stopped by +15m: 60. Feature-input availability:
frozen FVG zone recoverable 133/133; 60 forward bars 133/133; entry
stamp present on the RVMR 1m grid **130/133** (the grid ends 2026-08-17,
so three August-2026 entries are unavailable to **F4 only** → F4 works
on 92 at T5 and 71 at T15).

**Structural ToD finding, from counts alone (no outcome exposure).**
OFH13's frozen entry window (RTH, ≥30 min after open, ≥90 min to close)
is strongly AM-concentrated: at T5, RTH_AM 82 vs RTH_PM **13**; at T15,
61 vs **12**. A ToD-robustness gate demanding ≥20 events in both buckets
could therefore *never* fire, on any feature, regardless of the data —
a degenerate gate of exactly the kind this programme has been burned by
before. It is handled in §26 (gate P10) by a pre-declared PM floor of
≥10 with the ToD gate explicitly recorded as **weak for OFH13**. This
adjustment is made on a *structural count*, before any outcome exists,
and is disclosed rather than applied silently.

## 6. PRIMARY FUTURE ENDPOINT (one only, binding)

Let `j` = entry bar, `dir` = OFH13 direction, `c` = close, and let
**`e`** = the frozen exit bar (first bar in 1…60 touching the ATR1.5
stop, else 60). Let `R = 1.5 · atr[j]` (the frozen initial risk).

> **futureMFE(T) = max over k in (T, e] of  dir · (extreme[j+k] − c[j+T]),
> floored at 0**, where `extreme` = high for longs, low for shorts.
> Reported in **NQ points** and in **R**.

Measured **from the checkpoint price `c[j+T]`**, over the **remaining
real life of the trade** under unchanged management. Excursion achieved
before T cannot contribute: the window is strictly `k > T`, and the
origin is the checkpoint price, not the entry price. Requires
`e > T` (guaranteed by eligibility).

*Why this formulation over "new highs beyond the pre-T MFE":* it is the
quantity a post-entry observer at T actually faces, it inherits nothing
from the pre-T path level, and it cannot be manufactured by a trade that
had already run. The alternative — `max(0, MFE_final − MFE_T)`, "new-high
extension" — is frozen as a **secondary** and reported alongside, so the
other reading is on the record and cannot be selected later.

## 7. SECONDARY ENDPOINTS (reported, never promotable alone)

futureMAE(T) (same construction, adverse); remaining frozen P&L from T
(`dir · (c[j+e] − c[j+T])`); eventual original OFH13 net P&L; probability
the ATR1.5 stop is eventually reached after T; future favorable-first
after T at ±1.0·ATR (the frozen `ffpct` convention, re-anchored to
`c[j+T]`); minutes from T to the future MFE; tail-winner probability;
futureMFE/futureMAE ratio; and the "new-high extension" of §6.

## 8. TAIL-WINNER DEFINITION (descriptive, frozen before results)

**TAIL WINNER = one of the 13 events with the largest original frozen
OFH13 net P&L** (top 10% of 133, ties broken by earlier entry
timestamp). This is the repository-consistent convention already used in
the registry ("top 10 trades ≈ 100% of net P&L") and in the commit
`4cbb81b` listing (top 10% = 13). The threshold is fixed by rank, not
chosen to separate anything.

**Remaining-tail-fraction rule (binding for gate P13).** A tail winner
counts as *predicted at T* only if the majority of its move happened
after T:
`(MFE_final − MFE_T) / MFE_final ≥ 0.50`, where both MFE are measured
from entry over the frozen life. A feature may not claim to predict a
large winner that had already largely completed before the feature was
observed.

## 9. F1 — PATH EFFICIENCY

`eff(T) = |c[j+T] − c[j]| / Σ_{i=1..T} |c[j+i] − c[j+i−1]|`

Unsigned, as specified. Zero denominator (all T closes identical) ⇒
`eff` **UNDEFINED**, event excluded from F1 at that checkpoint and
counted. **Critical control: signed return entry→T.** If efficiency adds
nothing beyond net progress ⇒ **REDUNDANT WITH EARLY RETURN**.

## 10. F2 — EXCURSION GEOMETRY (exactly two scalars)

With `MFE_T = max(0, max_{k≤T} dir·(extreme[j+k] − c[j]))` and
`MAE_T = max(0, max_{k≤T} −dir·(extreme_adverse[j+k] − c[j]))`:

- **Primary scalar `G1(T) = MFE_T / max(MAE_T, 0.25)`** (ε = 0.25 pt =
  one MNQ tick).
- **Companion scalar `G2(T) = (1/T) · Σ_{k=1..T} 1[dir·(c[j+k] − c[j]) > 0]`**
  — fraction of completed minutes closing on the favorable side.

`G1` is the binding cell; `G2` is reported and **cannot advance alone**
(§24). **Critical controls: MFE_T and MAE_T (levels).** If shape adds
nothing beyond level ⇒ **REDUNDANT WITH EARLY EXCURSION**.

## 11. F3 — STRUCTURAL ACCEPTANCE (OFH13's own frozen geometry, no new indicator)

Uses only levels the frozen OFH13 event already carries: the
displacement-qualified FVG zone `[zLo, zHi]` (recovered from
`build_fvg` at `meta['fvg_j']`, matched on direction) and the far
boundary `far = struct_ref`. Evaluated on **completed closes**
`c[j+1..j+T]` only:

- **C · RECLAIMED-AGAINST** — some completed close is beyond `far`
  against the trade (`dir·(c[j+k] − far) < 0`). This is verbatim the
  frozen invalidation condition the mitigation scan itself uses
  (`close < zLo` bullish / `close > zHi` bearish).
- **A · ACCEPTED** — no RECLAIMED event by T **and** the close at T is
  beyond the zone in the trade direction (`c[j+T] > zHi` long /
  `c[j+T] < zLo` short).
- **B · ENTANGLED** — neither A nor C: still inside or straddling the
  zone.

**Primary contrast, frozen now to forbid any post-hoc collapse:
A versus (B ∪ C).** The three-state table is reported descriptively.
No subjective term ("clean", "strong", "good rejection") appears
anywhere; every state is computable from completed bars.

## 12. F4 — MOVEMENT-STATE EVOLUTION (post-entry only; RVMR is never an entry filter)

At entry and at T record the frozen RANGE state `RB` and VOLUME state
`VB` (`bucket(trailing_ratio(·))`, T1 1.270 / T2 2.335 / W 1440) and the
continuous range score `rr`. Frozen four-class transition vocabulary:

`EXPANSION` (RB[entry] ∈ {LOW,MED} → RB[T] = HIGH) · `SUSTAINED-HIGH`
(HIGH → HIGH) · `CONTRACTION` (HIGH → {MED,LOW}) · `NO-TRANSITION`
(non-HIGH → non-HIGH).

**Primary contrast: EXPANSION vs NO-TRANSITION** — both conditioned on
the same non-HIGH entry state, so it is a genuine transition test rather
than a state-level test. The full 4-class table and the `VB` transition
are descriptive. **If EXPANSION < 20 events the family is INSUFFICIENT;
there is no fallback contrast.** No permutation search over states.

**Controls: ATR change `atr[j+T]/atr[j]`, realized-range change, volume
change.** If ATR/range/volume explains the effect, **RVMR gets no
incremental credit** ⇒ **REDUNDANT WITH ATR/RANGE**.

## 13. F5 — DIRECTIONAL ORDER / CHOP

- **Primary scalar `align(T) = (1/T) · Σ_{k=1..T} 1[dir·(c[j+k] − c[j+k−1]) > 0]`**
  (zero returns count as not aligned).
- **Companion `flips(T)`** = sign changes among the T completed returns,
  zeros skipped. Reported; **cannot advance alone**.

**Control: signed return entry→T.** If ordering is merely another
representation of net return ⇒ **REDUNDANT WITH EARLY RETURN**. The
closed MEMORY strategy research is not imported in any form.

## 14. F6 — ACCELERATION (T15 only)

`accel = dir·(c[j+15] − c[j+10]) − dir·(c[j+10] − c[j+5])`

Equal 5-minute windows (minutes 11–15 versus 6–10), in points and in R.
**Not created at T5** — insufficient path exists. **Control: total
signed move through T15.**

## 15. BASELINE CONTROLS (compact, frozen)

Continuous, all expressed in **R units** (divided by `R = 1.5·atr[j]`):

1. signed return entry→T
2. MFE_T
3. MAE_T

Reported as stratified splits rather than regressors (to protect
degrees of freedom at n ≈ 73–95): initial stop distance, ATR at entry,
OFH13 direction, broad ToD bucket. Realized range / volume change enter
**only** for F4's incrementality (§12).

**Incrementality test (frozen).** Two constructions must **agree in
sign**: (a) **residualisation** — OLS of the endpoint on the three
continuous controls, then the feature contrast recomputed on the
residual; (b) **matched common-weight** — the contrast standardised over
cells of (signed-return tercile × MFE_T tercile), cells requiring ≥ 5
events on both sides, weight `w = nA + nB`. Disagreement in sign ⇒ the
feature fails P4/P5.

**Feature analysis form.** Every continuous feature (F1, F2-G1, F5-align,
F6) is analysed by **outcome-blind terciles** computed on that
checkpoint's eligible population and **printed before any outcome join** —
the repository's own idiom (OFH13-V2 used tercile scans) — with the
primary contrast **TOP tercile minus BOTTOM tercile of futureMFE**.
Rank analysis also removes any need for an arbitrary cap on `G1`.
F3 and F4 use their frozen two-arm contrasts.

## 16. LOSS-COLLAPSE DEFINITION (secondary family)

Question: at T, does a causal state identify trades whose **remaining**
expectancy has materially deteriorated? For each state, report future
remaining P&L, futureMFE, futureMAE, and eventual-stop probability.

**No exit, breakeven, tightened stop, or partial exit is simulated.** A
LOSS-FAILURE candidate advances only as a *predictive state object*.

## 17. TAIL-DEVELOPMENT DEFINITION

A state at T qualifies as tail-developing only if it identifies trades
producing large right-tail expansion **after** T — enforced by the
remaining-tail-fraction rule of §8 (≥ 50% of the eventual from-entry MFE
must occur after T) applied at gate P13.

## 18. SAMPLE FLOORS (fixed at drafting, before the §5 counts were run; not weakened afterwards)

- T5-eligible ≥ **90** events on ≥ **70** unique days → observed 95 / 81 ✔ (thin margin)
- T15-eligible ≥ **70** events on ≥ **55** unique days → observed 73 / 64 ✔ (thin margin)
- Each compared state / tercile cell ≥ **20** events and ≥ **15** unique days
- F4 EXPANSION ≥ **20** events, else F4 = INSUFFICIENT (no fallback)

If a feature creates cells below these floors ⇒ **INSUFFICIENT**. Floors
are never lowered after seeing a promising subgroup.

**Power statement, made before results.** With 73–95 events, ~24–32 per
tercile cell, BH correction across 11 cells, and an endpoint as
heavy-tailed as OFH13's, this study is **underpowered by construction**.
A null result is the expected outcome and is fully valid. Nothing in
§26 may be relaxed on the grounds that the study turned out to be small —
that was known and accepted at freeze.

## 19. LONG / SHORT

Every serious effect reported **pooled, LONG, SHORT**. A side asymmetry
is recorded as **SIDE-SPECIFIC** and **NOT promoted**; it would require
its own future study. No short-only or long-only rule is created.

## 20. TIME-OF-DAY

Only the broad frozen buckets that OFH13's own entry window produces:
**RTH_AM (mod 570–750)** and **RTH_PM (mod 751–960)**. No new window
search. See §5 for the structural AM concentration and §26 P10 for its
consequence.

## 21. TEMPORAL DESTRUCTION

Existing frozen OFH13 partitions (UNSEEN / DEV / IR) and calendar
quarters where the sample permits. **No period exclusions.** All exposed
periods remain DEVELOPMENT. Report effect sign, sample, effect size and
stability for each.

## 22. TAIL DESTRUCTION (two distinct issues, interpreted separately)

**A · Statistical-artifact test** — does the feature→future relationship
survive removal of the top 1% and top 5% of |futureMFE|, and removal of
the single most influential event?
**B · Tail-identification test** — with the tail restored, does the
feature correctly flag the conditions where major winners develop
(§8 rule)?

A candidate is rejected if one or two events manufacture the
relationship (A), but is **not** automatically rejected merely because
OFH13 is economically tail-dependent (B). Both are reported; neither
alone decides.

## 23. INFERENCE

- **Day-clustered percentile bootstrap**, 20,000 iterations, **seed
  20260826**, 95% CI, two-sided p floored at 1/(B+1), resampling whole
  entry days.
- **Permutation: stratified label permutation preserving OFH13 side and
  frozen partition, day-respecting**, 20,000 iterations, same seed.
  *Declared now, before results:* the programme's usual within-day
  circular rotation is **degenerate here** — OFH13 averages ~1.2 events
  per day, so a rotation cannot break alignment (the D2 defect recorded
  in MEMORY-MATH-IFVG-V1). A stratified label permutation is the correct
  null for a sparse event family and is frozen for that reason.
- **BH correction within each family** (§24).

## 24. MULTIPLICITY — M_binding

One primary scalar or contrast per family per applicable checkpoint:

| family | T5 | T15 | cells |
|---|---|---|---|
| F1 efficiency | ✔ | ✔ | 2 |
| F2 `G1` shape | ✔ | ✔ | 2 |
| F3 acceptance A vs (B∪C) | ✔ | ✔ | 2 |
| F4 EXPANSION vs NO-TRANSITION | ✔ | ✔ | 2 |
| F5 `align` | ✔ | ✔ | 2 |
| F6 acceleration | — | ✔ | 1 |

> **M_binding = 11** on the PRIMARY endpoint (futureMFE), BH across all
> 11. The LOSS-COLLAPSE family is the **same 11 cells** evaluated on
> remaining P&L, BH-corrected **separately**, M_loss = 11.
> **M_total declared = 22**, hierarchical (BH within each family).

Companion scalars (`G2`, `flips`) and every secondary endpoint are
reported but are **not promotable**, do not consume multiplicity, and
may never be substituted for a primary. **No failed cell is removed from
the family afterwards.** Programme cumulative multiplicity (24 before
this study) is reported as **NON-BINDING sensitivity only** and does not
overwrite this study's verdicts.

## 25. CANDIDATE CEILING

At most **ONE TAIL-DEVELOPMENT candidate** and **ONE LOSS-FAILURE
candidate**; **maximum 2 total**. A single feature may occupy both roles
only by independently satisfying every frozen gate for each outcome.
Runner-up features are **not** promoted.

## 26. PROMOTION GATES (all fifteen required; numeric, no subjective override)

| # | Gate | Numeric requirement |
|---|---|---|
| P1 | exact causality | every input from completed bars ≤ T; overlap check asserts `first_outcome_bar > last_feature_bar` |
| P2 | adequate sample | §18 floors met at that checkpoint **and** in every compared cell |
| P3 | outcome strictly after T | endpoint window is `(T, e]` with origin `c[j+T]`; verified, not assumed |
| P4 | incremental beyond signed return | residual and matched constructions **agree in sign** and each retains ≥ **50%** of the raw contrast |
| P5 | incremental beyond MFE_T / MAE_T | same rule on the 3-control residual |
| P6 | dependence-aware support | day-clustered bootstrap 95% CI **excludes 0** |
| P7 | multiplicity | BH **q ≤ 0.05** within its family (M = 11) **and** stratified permutation **p ≤ 0.05** |
| P8 | temporal stability | same sign in ≥ **2 of 3** partitions (UNSEEN/DEV/IR) **and** ≥ **2 of 3** calendar quarters holding ≥ 20 events |
| P9 | long/short | same sign in **both** sides; otherwise SIDE-SPECIFIC and **not promoted** |
| P10 | ToD robustness | same sign in **both** frozen buckets, RTH_AM ≥ 20 events and **RTH_PM ≥ 10** (reduced from 20 on the structural count of §5, disclosed; the ToD gate is **weak for OFH13**) |
| P11 | ATR/range/volume controls | effect retains sign and ≥ **50%** magnitude after common-weight standardisation on ATR-at-entry terciles (binding for F4, applied to all) |
| P12 | no single-event dependence | removing the single most influential event keeps sign and ≥ **70%** magnitude; top-1% and top-5% trims keep sign |
| P13 | tail relevance | ≥ **50%** of the flagged TAIL WINNERS satisfy the §8 remaining-tail-fraction rule |
| P14 | simple interpretable mechanism | exactly one frozen scalar/contrast from F1–F6, with a stated mechanism |
| P15 | actionable only after T | state computable at T from completed bars; **and no management rule is created** |

## 27. ALLOWED VERDICTS

`TAIL-DEVELOPMENT CANDIDATE` · `LOSS-FAILURE CANDIDATE` ·
`POST-ENTRY STATE CANDIDATE` · `REDUNDANT WITH EARLY RETURN` ·
`REDUNDANT WITH EARLY MFE/MAE` · `REDUNDANT WITH ATR/RANGE` ·
`TAIL-DEPENDENT` · `SIDE-SPECIFIC` · `TIME-SPECIFIC` · `INSUFFICIENT` ·
`UNSTABLE` · `NULL`.

**Gap-closure clause:** any failing pattern not covered above maps to
`NULL` with the failing gates named. Precedence: INSUFFICIENT (P2) →
causality (P1/P3) → redundancy (P4/P5/P11) → SIDE-/TIME-SPECIFIC
(P9/P10) → TAIL-DEPENDENT (P12/P13) → UNSTABLE (P8) → NULL.

**If nothing survives**, return
**`OFH13-POSTENTRY-V1 FOUND NO NEW CAUSAL POST-ENTRY SEPARATOR`** and do
**not** change checkpoints, add indicators, change formulas, slice
longs/shorts, change the time window, or lower sample floors. Any such
alteration is a new V2 preregistration.

## 28. PROSPECTIVE REQUIREMENT

Any candidate discovered from this exposed history is **NOT independently
confirmed**. If something survives, freeze **only the mathematical /
predictive state object** — `OFH13-TAILSTATE-V1` or
`OFH13-FAILSTATE-V1` — with status **DEVELOPMENT-SUPPORTED POST-ENTRY
CANDIDATE**. **OFH13 is not modified.**

Its prospective start is the **first valid OFH13 parent after the
candidate's own freeze commit**. Never backdated. No PROTECTED historical
segment exists to reserve (§2), so prospective data is the *only*
possible confirmation instrument.

**Operational constraint recorded now:** the OFH13 prospective logger
currently records only end-of-trade fields (`heldMin, netPts, netUsd, R,
mfe, mae, ratio, ff05, ff1, ff2`, per `docs/NT8_PROSPECTIVE_LOGGING.md`)
— it does **not** record the per-minute post-entry path or any checkpoint
state. Confirming a T5/T15 state object prospectively would therefore
require extending the logger, which is a modification of a protected
object and needs **separate authorization**. This study does not modify
it, and any surviving candidate must carry this constraint on its face.

Any economic translation — exit at T, breakeven, tightened stop, partial
exit, holding longer, removing the time exit, adding contracts, trailing
differently — is **out of scope** and requires a separate
**OFH13-MGMT-HYP-V1** preregistration.

---

## 29. EXECUTION AUTHORIZATION

This document authorizes nothing beyond itself. Running the outcome
study requires a separate directive, must verify this file's sha256
first, must execute each of the 11 binding cells exactly once, and must
publish every cell including failures. **NO ORDERS. THIS PROJECT DOES
NOT AUTHORIZE LIVE TRADING.**
