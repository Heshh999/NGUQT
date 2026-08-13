# COMPLIANCE AUDIT — MnqTwoStrategies vs. Master Specification **V6**

Audited against `two_automated_strategies_for_claude_v6_MNQ_ONLY_FINAL.md` (controlling).
Supersedes `docs/COMPLIANCE_AUDIT.md` (V5). Changes in this pass: `docs/CHANGELOG_V6.md`.

**Deterministic assertions: 93 executed, 93 passed, 0 failed** (Mono, run against the actual
engine sources — see "How to run" below).

Legend: ✅ implemented and test-proven · ⚙️ implemented, behavior exposed as a parameter
(V6-locked value is the default) · ⚠️ caveat.

Code refs: `Shared` = `src/MnqTwoStrategiesShared.cs`, `FB` = `src/FakeBreakoutEngine.cs`,
`VBR` = `src/VectorBreakRetestEngine.cs`, `Host` = `src/MnqTwoStrategies.cs`,
`Tests` = `tests/Tests.cs`.

## 0. V6 FINAL RULE LOCKS (U1–U9) — all resolved, none ambiguous

| Rule | Implemented? | Code location | Test proving it | Notes |
|---|---|---|---|---|
| **U1** First target broken = completed **1m close** beyond it; wick/touch does NOT count; then 3m EMA(9) runner | ✅ | FB `ManagePosition` (1m branch) → `ActivateRunner`; `FbConfig.TargetBreakMode = OneMinuteCloseBeyond` | `TestU1FbTargetBreak` (5 assertions) | Target itself comes from the shared 18-level engine; a 3m close beyond is explicitly proven NOT to activate it |
| **U1** LONG runner exit on completed 3m close below 3m EMA9 / SHORT above | ✅ | FB `ManagePosition` (3m branch) | `TestU1FbTargetBreak` runner-exit assertion | |
| **U2** VBR target REACHED on wick/touch (no close required) | ✅ | VBR `ManagePosition` chain loop; `TargetReached = IntrabarTouch` | `TestU2TargetChaining` | |
| **U2** Reached target becomes new reference; ≤50-pt gaps keep chaining and adverse 1m EMA signals are ignored | ✅ | VBR `AdvanceTargetChain` + chain loop | `TestU2TargetChaining` (HOLD + adverse-EMA-ignored assertions) | |
| **U2** Next gap > 50 pts activates the 1m EMA(9) trail; completed 1m close through EMA9 takes 90% | ✅ | VBR `AdvanceTargetChain` (`trailActivated`), trail block | `TestU2U3U8ProfitManagement` (trail activates, 18-of-20 exit) | |
| **U3** Final 10%: NO strength-2/multi-bar fractal; ONE completed 1m candle establishes the supporting swing; a LATER completed 1m close through it exits; wicks don't count | ✅ | `SupportingStructureTracker` (VBR file) + runner block in `ManagePosition` | `TestU2U3U8ProfitManagement` (wick no-exit, later close exits) | Bar indices prevent the establishing candle from also being the breaking candle |
| **U4** Invalid 15m FB reclaim does NOT cancel the parent; keep waiting | ✅⚙️ | FB `TryReclaim`; `InvalidReclaimCancelsSetup = false` | `TestU4U5FbReclaim` (ignored + not cancelled + later entry) | Legacy flag retained, must stay FALSE |
| **U4** A 15m reclaim is not an entry; entries are 1m/3m only with same-TF EMA(9) | ✅ | FB entries exist only in `ProcessLtf`/`TryEnter` | all FB entry tests | |
| **U5** LTF scanning/entry allowed BEFORE any completed 15m reclaim | ✅⚙️ | FB `ProcessLtf` `mayScan`; `Require15mReclaimBeforeLtfEntry = false` | `TestU4U5FbReclaim` (entry with zero reclaims) | |
| **U6** Pattern B long entry requires a completed 1m close above **BOTH** DO and 1m EMA9 | ✅ | VBR Pattern B + `waitingEmaB` blocks | `TestU6PatternBWait` | |
| **U6** Reclaim below EMA9 ⇒ WAIT (do not discard); later close beyond both enters | ✅⚙️ | same; `PatternBWaitForEma = true` | `TestU6PatternBWait` | |
| **U6** A candle beyond EMA9 but on the wrong side of DO is NOT an entry | ✅ | `waitingEmaB` branch | `TestU6PatternBWait` step-7 assertion | |
| **U6** Short mirror | ✅ | same code, short branch | `TestU6PatternBWaitShort` | |
| **U7** Re-entry permission rolls ONE 15m candle at a time inside the ORIGINAL clock | ✅⚙️ | VBR rolling block in `OnFifteenMinuteBar`; `ReentryScanOnlyFollowingCandle = false` | `TestU7RollingReentry` | |
| **U7** Stop-out candle needs wick-into/through-DO **and** correct-side close | ✅ | `STOPPED_OUT_REENTRY_ELIGIBILITY_PENDING` branch | `TestU7RollingReentry` (#2 → #3) | |
| **U7** No entry in #3 + correct-side #3 close ⇒ #4 may scan | ✅ | rolling block | `TestU7RollingReentry` (#3 → #4) | |
| **U7** Wrong-side close ends rolling permission | ✅ | rolling block | `TestU7WrongSideBreaksRolling` | |
| **U7** Every re-entry needs a FRESH 1m pattern; clock never restarts/extends | ✅ | `ResetPattern` on roll; clock never reset outside `ResetSetup` | `TestU7RollingReentry` (entry in #4; no #5) | |
| **U8** 1-contract VBR: EMA profit signal exits the ENTIRE contract, no runner | ✅⚙️ | VBR trail block; `SingleContractBecomesRunner = false` | `TestU8SingleContract` (3 assertions) | |
| **U8** Larger positions keep 90% / final-10% behavior | ✅ | same block | `TestU2U3U8ProfitManagement` (18 of 20, then 2) | |
| **U9** Never hold FB and VBR simultaneously | ✅ | `HandoffCoordinator` | both U9 tests | |
| **U9** Flatten open strategy → confirm flat → then enter (never before) | ✅ | `HandoffCoordinator.RequestEntry`/`NotifyFlat`; Host `OnPositionUpdate`; engine `FlattenForHandoff` | `TestU9HandoffFbToVbr`, `TestU9HandoffVbrToFb` — ordering asserted `EXIT → FLAT_CONFIRMED → ENTRY` | |
| **U9** Symmetric FB↔VBR | ✅ | same | both U9 tests | |
| **U9** Replacement uses ONLY its own stop/grade/risk/size/target/runner; no merged state | ✅ | engines keep private state; coordinator carries only (id, dir, qty, signal) | both U9 tests | |
| **U9** Replacement must still satisfy its own time/validity rules at handoff initiation | ✅ | engine `TryEnter` gates run before `EnterPosition` | structural | |
| **Psy type** = Forex for this MNQ setup | ✅⚙️ | `KeyLevelEngine.PsyType = Forex` | `TestTradersRealityPorts` | |

## 1. Fake Breakout — explicit V6 verification list

| Rule | Implemented? | Code location | Test proving it | Notes |
|---|---|---|---|---|
| YDay High/Low + LWeek High/Low are the ONLY parent trigger levels | ✅ | FB `EligibleLevels` | structural (DAILY_OPEN absent) | |
| 15m parent setup; 1m and 3m actual entries | ✅ | `OnFifteenMinuteBar` / `OnOneMinuteBar` / `OnThreeMinuteBar` | all FB tests | |
| LTF scanning may begin immediately; 15m reclaim NOT required | ✅ | see U5 | `TestU4U5FbReclaim` | |
| Invalid 15m reclaim keeps the parent alive | ✅ | see U4 | `TestU4U5FbReclaim` | |
| **BLUE above → REGULAR below = valid short** | ✅ | FB `ProcessLtf` BLUE-first reclaim branch | `TestBlueShortPaths` | |
| **BLUE above → RED_VECTOR below = valid short** | ✅ | same | `TestBlueShortPaths` | |
| **BLUE above → VIOLET below = INVALID for the BLUE path** | ✅ | same | `TestBlueShortPaths` | |
| BLUE is NOT a valid 15m FB parent initiator | ✅ | FB `TryTrigger` vector filter | structural (GREEN/REGULAR short, RED/REGULAR long) | |
| Same-timeframe EMA(9) confirmation (enter if already beyond, else wait for first close beyond; cancel on structure break) | ✅ | FB `ProcessLtf` emaOk / `WaitingEma` branches | `TestBlueShortPaths`, `TestU4U5FbReclaim` | |
| A- = first actually executable/eligible entry candle; B+ later | ✅⚙️ | `FbGradeBasis.FirstTradableCandle`; `TryEnter` | `TestPremarketAMinusGrading`, `TestLaterEntryGradesBPlus` | 26% / 10% risk asserted via contract counts |
| 4 primary 15m candles + 2 extension (max 6) | ✅ | FB `Process15` | structural | |
| First target broken only by completed 1m close; wick doesn't count | ✅ | see U1 | `TestU1FbTargetBreak` | |
| After confirmation activate the 3m EMA(9) runner | ✅ | see U1 | `TestU1FbTargetBreak` | |

## 2. Vector Break Retest — explicit V6 verification list

| Rule | Implemented? | Code location | Test proving it | Notes |
|---|---|---|---|---|
| Daily Open is the ONLY parent trigger level | ✅ | VBR reads only `Levels.DailyOpen` | structural | |
| 15m GREEN_VECTOR close above DO = long parent | ✅ | `OnFifteenMinuteBar` | `TestVbrNoCrossAndNoRestart` | |
| 15m RED_VECTOR close below DO = short parent | ✅ | same | `TestU6PatternBWaitShort` | |
| No prior-close or cross-through requirement | ✅⚙️ | `RequireCrossThrough = false` | `TestVbrNoCrossAndNoRestart` | |
| 1m entry only (no 3m) | ✅ | engine has no 3m handler; host never feeds it 3m | structural | |
| Original 4-candle clock never restarts or extends | ✅ | `RetriggerReplacesActiveSetup = false`; rolling block | `TestVbrNoCrossAndNoRestart`, `TestU7RollingReentry` | |
| Pattern B long: close above BOTH DO and 1m EMA9 | ✅ | see U6 | `TestU6PatternBWait` | |
| Pattern B short: close below BOTH | ✅ | see U6 | `TestU6PatternBWaitShort` | |
| Pattern B: reclaim before EMA ⇒ wait while setup valid | ✅ | see U6 | both U6 tests | |
| Target reached by wick/touch | ✅ | see U2 | `TestU2TargetChaining` | |
| Chain while next gap ≤ 50 points | ✅ | see U2 | `TestU2TargetChaining` | |
| Gap > 50 points ⇒ 1m EMA9 90% trail | ✅ | see U2 | `TestU2U3U8ProfitManagement` | |
| Final 10% uses the V6 one-candle structure rule (no strength-2 fractal) | ✅ | see U3 | `TestU2U3U8ProfitManagement` | |
| 1 MNQ contract ⇒ EMA signal exits the whole contract | ✅ | see U8 | `TestU8SingleContract` | |
| Rolling 15m re-qualification inside the original clock | ✅ | see U7 | `TestU7RollingReentry`, `TestU7WrongSideBreaksRolling` | |

## 3. Strategy handoff, instrument scope, separation

| Rule | Implemented? | Code location | Test proving it | Notes |
|---|---|---|---|---|
| Flatten open strategy → wait for flat confirmation → enter new strategy | ✅ | `HandoffCoordinator`; Host `OnPositionUpdate` | both U9 tests (ordering asserted) | |
| Never hold both; never submit replacement before confirmed flat | ✅ | `HandoffCoordinator.NotifyFlat` is the only release path | both U9 tests | |
| Strategies remain fully independent apart from the handoff | ✅ | separate engines/state; coordinator carries no setup state | structural + U9 tests | |
| MNQ only; never NQ; $2 per index point | ✅ | Host instrument gate; `PositionSizer.MnqDollarsPerPoint = 2.0` | sizing assertions throughout | |
| Shared utilities only (vectors, TR levels, EMA, session/time, sizing, handoff sequencing) | ✅ | `Shared` file | — | |
| 9:30–11:30 ET new entries; premarket 15m candles count; premarket LTF signals never banked | ✅ | host gates + pattern-start gates | `TestPremarketAMinusGrading` | |
| Traders Reality vector classification + level calculations preserved | ✅ | `VectorClassifier`, `KeyLevelEngine` | `TestTradersRealityPorts`, `TestTargetSortingAndMerging` | Confirmed against TR_MAIN in the previous pass |
| 18 selectable targets; R2/S3 internal only; tick-exact equal-price merging | ✅ | `TpLevelId`, `GetSortedTargets` | `TestTargetSortingAndMerging` | |

## 4. Remaining implementation issues (NOT V6 trading-rule ambiguities)

The V6 U1–U9 locks are implemented; none of them is ambiguous any more. What remains:

1. **NinjaTrader host runtime is still unverified.** `src/MnqTwoStrategies.cs` has never been
   compiled or executed inside NinjaTrader 8 — no NT8 runtime exists in this environment.
   The 93 assertions exercise the strategy *engines* and the shared handoff coordinator, not
   the NT host wiring. **No NinjaTrader runtime verification is claimed.** Press F5 in the
   NinjaScript editor and send any compiler output.
2. **Handoff flat-confirmation hook is host-specific.** The release path is
   `OnPositionUpdate(... MarketPosition.Flat ...)`. The sequencing logic itself is
   test-proven via the shared coordinator, but that NinjaTrader callback firing as expected
   can only be confirmed in NT8 (live or Playback). Worth watching on the first handoff.
3. **One FB behavior is not locked by V6** (flagged rather than invented): what happens when
   the 15m EMA(9) confluence (§7) fails at the instant of a lower-timeframe entry signal.
   Default = cancel that LTF setup and keep scanning for a fresh one while the parent lives
   (`FbConfluenceFailCancelsLtfSetup`). Tell me if it should instead wait for a later 15m close.
*(Closed by user decision: the Psy 4H-grid compatibility flag stays OFF — the literal
session window is the accepted behavior and no TradingView cross-check is required. Not an
open issue.)*

## How to run the tests

```
cd tests
mcs -out:run_tests.exe ../src/MnqTwoStrategiesShared.cs ../src/FakeBreakoutEngine.cs \
    ../src/VectorBreakRetestEngine.cs MockHost.cs Tests.cs
mono run_tests.exe
```
Expected final line: `RESULT: 93 passed, 0 failed`.
