# V4.1 MANDATORY PRE-CODE AUDIT

Per `V4_1_MASTER_ENGINE_PROMPT_FINAL_FREEZE`: *"Do NOT code until this audit is
complete."* This is that audit. No V4.1 code has been written.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. The package submits no orders.

---

## 0. FIVE GATING FINDINGS

These change what V4.1 can legitimately contain. They are evidence-based, not
preferences.

### G1. PSY / whole / half-number levels: PRICE-INTEGRITY AUDIT **FAILS**

The prompt requires this audit before enabling round-number features. The data is a
**back-adjusted continuous contract** - established in V4 and unchanged. Back
adjustment shifts historical absolute prices by the accumulated roll spread, so the
price grid a 2019 round number sat on no longer exists in the series.

**Verdict: `psyLevelPriceIntegrityPass = FALSE`.** Per the prompt's own rule, the
PSY / whole / half / quarter-number feature family **must not be emitted as valid
research features**. Enabling it would require non-back-adjusted contract data,
which this project does not have.

### G2. Market depth: **DEPTH VERDICT = FAILED**

NinjaTrader 8 does not persist historical Level 2 depth for backtest. DOM is
realtime or Market-Replay only, and Market Replay data is downloaded per-day with
limited retention. There is no seven-year historical depth series to audit.

**Verdict: no depth module, no depth-derived features, no depth hypotheses.** The
prompt's own instruction applies: *"FAILED historical depth audit -> DO NOT use
depth-derived features."* The `V4DepthEngine` in the desired module list should not
be built until reliable timestamped depth exists.

### G3. Two-speed coverage - order flow and profile cannot span the structure history

| layer | coverage | source |
|---|---|---|
| Structure / vector / location / EMA | **2019-07 -> 2026-08 (7 years)** | 1m OHLCV |
| Order flow (footprint, delta, CVD, imbalance, absorption) | **2025-11-02 -> 2026-08-18 (10 months)** | Volumetric series |
| Volume Profile (POC/VAH/VAL/HVN/LVN) | **same 10 months** | derived from the same per-price data |

Volume Profile is built from per-price ask/bid volume, which only exists where the
Volumetric series exists. **Profile inherits the order-flow window exactly** - it
does not get seven years.

Consequence: every Class B ablation of the form *structure vs structure + order
flow* or *structure + profile* is a **10-month test**, while *structure only* and
*structure + vector* are seven-year tests. These are not comparable sample sizes and
must never be reported as if they were. The engine must stamp every row with the
data-layer availability so the analysis layer cannot silently mix them.

### G4. Same-bar stop/target ambiguity is **not handled anywhere today**

Zero occurrences of any ambiguity marking in the V4 source. `minsToStop` and
`minsTo_<X>R` are emitted independently, leaving the consumer to resolve the race
and giving them no way to know it was unresolvable.

This is not hypothetical. Measured in V5 across 2.28M resolved 1R races:

| convention | P(+1R before -1R) | 95% CI |
|---|---|---|
| stop-first | 0.4869 | +-0.0006 |
| target-first | 0.5290 | +-0.0006 |

The modelling ambiguity is roughly **50x** the statistical uncertainty, and 0.50
sits inside the bracket. Choosing a convention silently would have manufactured a
spectacular fake edge. V4.1 must emit `AMBIGUOUS` exactly as the prompt requires,
plus both bounds, and flag those events as candidates for 30s/tick resolution.

### G5. EMA(9) 1m management: **entirely absent**

Zero occurrences of EMA9 anywhere in the V4 package. The prompt names 1m EMA(9) as
the PRIMARY V4.1 management hypothesis. This is 100% new build, not an extension.

---

## 1. COMPONENT INVENTORY AND VERDICTS

### Existing V4 package

| file | LOC | verdict |
|---|---|---|
| `V4StructureEngine.cs` | 526 | **MODIFY** |
| `V4LocationBook.cs` | 181 | **MODIFY** (substantial) |
| `V4StructureResearch.cs` | 1,143 | **MODIFY** (substantial) |
| `V4OrderFlowEngine.cs` | 478 | **MODIFY** |
| `MnqV4StructureResearchHost.cs` | 612 | **MODIFY** |
| `MnqV4OrderFlowResearchHost.cs` | 523 | **MODIFY** |
| `tests/V4Tests.cs` | 973 (97 assertions) | **MODIFY** (extend) |
| `tests/V4ReaderTests.cs` | 177 (13 assertions) | **KEEP AS-IS** |
| `tests/NtStubs.cs` + `mcs`/`mono` harness | 167 | **KEEP AS-IS** |

### Prior-generation files - source only, not part of V4.1

| file | role in V4.1 |
|---|---|
| `MnqTwoStrategiesShared.cs` | **HARVEST** `VectorClassifier` (see 3.1). Do not link the rest. |
| `VectorCandleResearchEngine.cs` | Reference for vector event shape. Do not reuse V2 assumptions. |
| `VectorBreakRetestEngine.cs`, `FakeBreakoutEngine.cs`, `ScalpResearchEngine.cs`, `MnqTwoStrategies.cs` | **OUT OF SCOPE.** V3-era. Leave untouched so V3 conclusions stay uncontaminated. |

### New modules required

| module | why |
|---|---|
| `V4VectorEngine.cs` | vectors, zones, recovery, W/M, trap, push, trigger-vector |
| `V4EmaFanEngine.cs` | EMA 5/13/50/200/800 across 15m/5m/3m/1m + fan states |
| `V4VolumeProfileEngine.cs` | POC/VAH/VAL/HVN/LVN, gated to the volumetric window |
| `V4HypothesisEngine.cs` | HypothesisID registry, Class A/B/C/D, CONFIRMATORY/EXPLORATORY |
| `V4FeatureRecorder.cs` | `f_*` / `y_*` schema emission and enforcement |
| `V4ForwardLabelEngine.cs` | extract labels from `V4StructureResearch`, extend grid, ambiguity |
| `V4AuditEngine.cs` | startup diagnostic, fail-fast, per-layer audits |
| `V4Shared.cs` | shared enums/consts across the above |

**Not to be built:** `V4DepthEngine.cs` (G2).

---

## 2. AUDIT OF EVERY ITEM THE PROMPT LISTS

### Namespace
`NinjaTrader.NinjaScript.Strategies.MnqV4` for engines; hosts sit in
`NinjaTrader.NinjaScript.Strategies`. **KEEP AS-IS.** V4.1 modules join the same
engine namespace.

### Primary and secondary series / BarsInProgress mapping

`MnqV4StructureResearchHost.cs:300-309`. BIP 0 is the chart series and is
deliberately unused; added series are assigned sequentially and conditionally:

```
int next = 1;                                    // BIP 0 = chart, unused
if (UseDaily) { AddDataSeries(Day, 1);      BipDaily = next++; }
if (Use4h)    { AddDataSeries(Minute, 240); Bip4h    = next++; }
if (Use60m)   { AddDataSeries(Minute, 60);  Bip60m   = next++; }
if (Use15m)   { AddDataSeries(Minute, 15);  Bip15m   = next++; }
if (Use5m)    { AddDataSeries(Minute, 5);   Bip5m    = next++; }
if (Use3m)    { AddDataSeries(Minute, 3);   Bip3m    = next++; }
                AddDataSeries(Minute, 1);   Bip1m    = next++;
```

**KEEP AS-IS.** Dynamic index assignment is correct and already survived the
"indices are not `const`" regression. V4.1 adds no new series - the prompt forbids
adding 2m/sub-minute globally, and every V4.1 layer runs off existing series.

Order-flow host gates on `BarsInProgress != 0` and reads the Volumetric primary.
**MODIFY** only to add the profile hook.

### Session template, time zone, merge/rollover

Everything is stamped in ET via `V4Bar.EtOpen` / `EtClose`. Exchange day rolls at
18:00 ET (`V4LocationBook.DayStartMinutesEt = 1080`); exchange week keys off the
Sunday 18:00 open. RTH is 570-960 ET minutes. The 16:15-16:30 maintenance halt and
17:00-18:00 daily halt are recognised in the order-flow gap classifier.
**KEEP AS-IS** - this was corrected once already after 436 of 463 "gaps" turned out
to be the scheduled equity-index pause.

Merge/rollover: back-adjusted continuous. **KEEP AS-IS as a fact, but see G1** - it
is what disqualifies the PSY family.

### EventID logic

`MakeEventId(symbol, tf, etClose, dir)` -> `MNQ-15m-20260817143000-1`. Month routing
reads the timestamp back out of the eventId (`MonthOf`), so a row always lands in
the month of its own event.

**MODIFY.** V4.1 needs the four-level hierarchy the prompt specifies:
`ParentEventID` / `EventID` / `EntryProbeID` / `HypothesisID`, plus `rawSignalCount`
and enough clustering to compute `effectiveIndependentEventCount`. The current
single flat EventID cannot express "one market thesis, many probes" - and V4's
audit already measured **7.4x event clustering at 60m**, which is exactly the
inflation this hierarchy exists to expose.

### Feature / label separation

Conceptually present - `V4StructureResearch.cs:142` marks *"LABELS: nothing below
here is knowable at EtClose"* - and enforced at capture by
`SnapshotCutoff(b) = b.EtClose.AddSeconds(-1)`, an order-independent gate that
verified clean across 196,799 rows on three causal timestamps.

**MODIFY.** The *schema* does not carry it: **0 occurrences of `f_` or `y_`
prefixes**. Every column must be renamed per the prompt. This is mechanical but
touches every writer and every downstream analysis script.

### Structure definitions and pivot confirmation

`V4StructureEngine.cs`. A pivot is published only after `ConfirmBars` (default 2)
bars close to its right; it carries `KnownAtEt` and queries refuse it before that
instant (`if (src[i].KnownAtEt > cutoffEt) continue;`). States: BULLISH / BEARISH /
RANGE_CONTRACTING / RANGE_EXPANDING. Equal-high/low tolerance is an ATR fraction.

**KEEP the confirmation machinery AS-IS** - it is the single most important
no-lookahead guarantee in the package and it is correct.

**MODIFY the state vocabulary**: the prompt requires BULLISH / BEARISH / RANGE /
**TRANSITIONING** / **UNDEFINED**. Current RANGE_CONTRACTING and RANGE_EXPANDING
are a different axis (compression/expansion) and should be split out from the
trend state rather than conflated with it.

### Location-book logic

`V4LocationBook.cs` tracks prior day/week extremes, session high/low/open, session
VWAP, `AsOfEt`, nearest level + ATR distance.

**MODIFY, substantially.** The prompt demands a much richer vocabulary that the V4
book does not have: `interaction` (11 states), `seqState` (10 states),
`testNumberToday` with **interaction clustering** so a 10-bar chop at a level counts
as one test, `firstTest`/`repeatTest`, `sideOfLevel`, `crossedLevel`,
`reclaimedLevel`, `acceptedBeyondLevel`, `rejectedFromLevel`,
`minutesSinceLevelInteraction`, `levelInteractionCountSession`.

Note: the **V3 engine already has** `interaction`, `seqState` and `testNumberToday`
with working vocabularies (`SWEEP_CLOSE_BACK`, `APPROACHED`, `TOUCHED`, `NONE`;
`UNTESTED`, `RETEST_AFTER_BREAK`, `RECLAIM_AFTER_BREAK`, `FIRST_TEST`,
`REPEAT_TEST`). Those are a starting vocabulary to extend to the prompt's fuller
list - not something to reinvent.

Also required: 4H/60m/15m/5m/3m confirmed swings as levels, Daily Open, Premarket
H/L, Opening Range H/L, VWAP bands, unrecovered vector zones, profile levels.
Currently absent.

### Forward-label logic

| grid | current | prompt requires | gap |
|---|---|---|---|
| horizons (min) | 5, 15, 30, 60, 120, 240 | 1, 2, 3, 5, 10, 15, 30, 60, 80, 120, 240 | **add 1, 2, 3, 10, 80** |
| R multiples | 0.5, 1, 1.5, 2, 3 | 0.5, 0.75, 1, 1.25, 1.5, 2, 2.5, 3, 4, 5 | **add 0.75, 1.25, 2.5, 4, 5** |
| stop family | `stopSwingPts`, `stopBarPts`, `stopAtrPts` | TIGHT / MEDIUM / STRUCTURAL, each with price+pts+atr, `hitStop*`, `minsToStop*` | **restructure** |
| target family | fixed-R only | vector zone, liquidity/volume zone, confirmed swing, HTF structural, prior day/week/session, fixed-R - **frozen at entry** | **new** |
| right tail | `mfeR`, `maeR` | + `maxRBeforeEmaExit`, `maxRBeforeStructuralExit`, `maxRBeforeVectorTarget`, `timeTo1R..5R` | **extend** |
| ambiguity | none | `AMBIGUOUS` | **G4 - new** |

**MODIFY, substantially.** Extract into `V4ForwardLabelEngine.cs`.

One measured caution carried forward from the V5 audit: R must be guarded. The V3
micro-swing stop ranged **0.00 to 1266.50 pt with 1.13% of bars at exactly 0**,
making R-multiples undefined. V4.1 must emit R in points alongside every R-multiple
and refuse to compute a multiple on a degenerate stop.

### Order-flow data-quality checks

`V4OrderFlowEngine.cs` audits coverage, level completeness, zero-volume bars,
gap classification against both scheduled halts, quiet minutes, bid+ask vs volume
reconciliation, tick-grid validity, and states the CVD reset rule (18:00 ET) in the
audit text rather than inheriting it from an indicator setting. Last run: 279,834
bars, 100.00% level coverage, 0.0000% mismatch, **PASSED**.

**MODIFY** - three things:
1. Verdict is binary; prompt requires **PASSED / FAILED / NEEDS REVIEW**.
2. Imbalance is a single `ImbalanceFactor = 3.0` with `ImbalanceMinVolume = 10`,
   emitting only `buyImbalanceCount` / `sellImbalanceCount`. Prompt requires a small
   **predeclared parameter family**, plus `maxBuy/SellImbalanceRatio`,
   `stackedBuy/SellImbalanceLevels`, `imbalanceNearHigh/Low`, `persistence`,
   `failure`.
3. Absorption raw fields (`aggressiveBuy/SellVolume`, `volumePerUp/DownTick`,
   `repeatedTradeAtExtreme`, `absorption*Candidate`, `absorptionStrengthRaw`) are
   absent.

Add MODE 1 (summary, all bars) / MODE 2 (event-window footprint detail) as the
prompt specifies, so full per-price cells are only written around frozen EventIDs.

### Volumetric-series assumptions

`V4VolumetricReader` binds by reflection to
`NinjaTrader.NinjaScript.BarsTypes.VolumetricData`, calling
`GetAskVolumeForPrice(double)` / `GetBidVolumeForPrice(double)` per tick-grid price,
with `MaximumBarsLookBack.Infinite` required for array indexing. Every failure path
records a reason - added after three full runs were lost to silent `false` returns.

**KEEP AS-IS.** This is hard-won and correct. Extend only to feed the profile
engine off the same per-price data (no second pass).

### Current audit files

`v4_orderflow_MNQ_v4of_AUDIT.txt` only. **MODIFY / EXTEND** to the prompt's four:
`v4_1_STRUCTURE_AUDIT.txt`, `v4_1_ORDERFLOW_AUDIT.txt`, `v4_1_PROFILE_AUDIT.txt`.
No `DEPTH_AUDIT` (G2).

Startup diagnostic with **FAIL FAST on any zero-bar series** does not exist.
**NEW.**

### Monthly file routing

`OpenMonthly(path, header)` with a `pathsOpenedThisRun` set, cleared in
`State.DataLoaded` because NT8 reuses the strategy instance when
`IsInstantiatedOnEachOptimizationIteration = false`. First touch truncates, later
touches append.

**KEEP AS-IS.** This took three iterations to get right - append duplication, then
the dedup set never clearing across runs. Do not refactor it.

### Warm-up handling

`isWarmup = EtClose < TargetSampleStartEt`; warm-up rows are fully processed so
state is correct, and flagged for exclusion. **KEEP AS-IS.** Matches the prompt.

Note for V4.1: **EMA800 changes the warm-up requirement materially.** On 15m,
800 bars is ~200 trading hours (8+ sessions). On 4H it is ~133 days. The host must
compute required warm-up from the longest EMA on the slowest series and refuse to
emit official rows before it. Whether EMAs reset at session boundaries must be
declared explicitly, not left to a default.

### Existing tests

97 assertions in `V4Tests.cs`, 13 in `V4ReaderTests.cs`, run under `mcs`/`mono`
with `langversion:5` against `NtStubs.cs`. Deterministic and off-platform.

**KEEP the harness AS-IS. MODIFY to extend** with every test family the prompt
lists - notably all four vector colours plus non-vector, vector recovery
25/50/body/100, exact 1m EMA9 values on a known sequence, both EMA9 exit events,
level `interaction`/`seqState`/`testNumberToday` clustering, targets-frozen-at-entry,
and same-bar ambiguity marked rather than guessed.

---

## 3. SOURCE-VERIFICATION FINDINGS

### 3.1 PVSRA vector formula: **VERIFIED AND REUSABLE**

`MnqTwoStrategiesShared.cs:116` already implements the canonical Traders Reality /
PVSRA classification:

```
avgVol10           = mean(volume[1..10])                  // previous 10 completed
highestVolSpread10 = max(volume[i] * (high[i]-low[i])), i=1..10
bullish            = close > open                          // doji follows bearish branch

climax   : volume >= 2.0 * avgVol10  OR  volume*(high-low) >= highestVolSpread10
           -> GREEN (bullish) / RED (bearish)
elevated : volume >= 1.5 * avgVol10
           -> BLUE  (bullish) / VIOLET (bearish)
otherwise-> REGULAR_BULLISH / REGULAR_BEARISH
```

Lookback 10, thresholds 2.0x and 1.5x, spread condition as shown. This matches the
prompt's intended tiers exactly. **`vectorSourceVerified = TRUE`.** No formula needs
inventing, and none should be.

### 3.2 Concepts that CANNOT be source-verified

The prompt is explicit that unverified concepts must not be dressed as official.
On the evidence available, these have **no published exact algorithm**:

| concept | flag |
|---|---|
| First Vector strategy | `firstVectorSourceVerified = FALSE` - do not manufacture a rule |
| Brinks Box | do not implement an "official" version |
| Stopping volume | store raw ingredients only; any derived candidate tagged `RESEARCH_HEURISTIC` |
| Dealer / market-maker strategy | `sourceConceptClass = ADAPTED` or `HEURISTIC`, never `PUBLICLY_SOURCED` |
| Pivot / M-level | `pivotDefinitionVerified` / `mLevelDefinitionVerified = FALSE` until a specific formula is chosen and regression-tested |

W/M formation, vector trap, vector push, trade-into-wick, V-shape and
first-move-away-from-EMA are all describable qualitatively in public material but
lack published mechanics. They will be built as **declared mechanical translations**
with `mechanicalTranslationVersion`, per the prompt.

---

## 4. ONE MEASURED RISK THIS BUILD CARRIES

V4.1 multiplies the feature space by roughly an order of magnitude - vectors, a
five-EMA fan across four timeframes, W/M states, dealer context, profile, ADR/AWR.

V5 measured what that costs. A search over 8,329 conjunctions of 47 predicates,
run on outcomes **shuffled within day** so that no relationship existed, produced a
best "setup" of **+16.6 pt/trade on average, ranging to +26.1**. The real data's
best was +20.6 and sat inside that distribution (p = 0.143). Forward decay agreed:
top-50 DEV winners retained **-5.3%** of their effect on VAL.

The noise floor scales with the size of the search. V4.1's protections against this
are the prompt's own and they are the right ones: the **5-10 Class A limit**,
pre-registration before outcomes, mandatory ablation, and preserved
date/session/EventID so permutation is possible. Those are load-bearing, not
paperwork. The engine must therefore emit `researchClass` and
`researchHypothesisClass` on every row, and must not rank hypotheses internally.

---

## 5. BUILD ORDER

1. `V4Shared.cs` + `V4AuditEngine.cs` - startup diagnostic, fail-fast, layer stamps
2. `V4FeatureRecorder.cs` - `f_*` / `y_*` schema; migrate existing writers
3. `V4StructureEngine.cs` MODIFY - TRANSITIONING/UNDEFINED, split compression axis
4. `V4LocationBook.cs` MODIFY - interaction / seqState / testNumberToday clustering
5. `V4VectorEngine.cs` NEW - classifier harvest, zones, recovery, W/M, trap, push
6. `V4EmaFanEngine.cs` NEW - 5/13/50/200/800 + fan states + EMA9 1m management
7. `V4ForwardLabelEngine.cs` NEW - extended grids, stop/target families, AMBIGUOUS
8. `V4OrderFlowEngine.cs` MODIFY - imbalance family, absorption, MODE 1/2, 3-verdict
9. `V4VolumeProfileEngine.cs` NEW - gated to the volumetric window
10. `V4HypothesisEngine.cs` NEW - HypothesisID, Class A/B/C/D
11. Hosts MODIFY; `tests/V4Tests.cs` extended throughout

Steps 1-7 run on seven years of history. Steps 8-9 are limited to the 10-month
volumetric window (G3) and must be stamped as such.

---

## AUDIT VERDICT

The V4 package is a sound foundation. Its no-lookahead machinery, monthly routing,
warm-up handling, volumetric reader and test harness are correct and were each
fixed the hard way; none should be rewritten.

What V4.1 needs is **breadth**, not repair - plus five things the current package
genuinely cannot do: the `f_*`/`y_*` schema, the four-level EventID hierarchy,
same-bar ambiguity marking, EMA(9) management, and the vector/EMA-fan/profile
layers.

Two feature families requested by the prompt **must not be built**: PSY /
round-number (G1) and market depth (G2), each failing the prompt's own
data-validity gate.

No code has been written. Awaiting go-ahead on the build order in section 5.
