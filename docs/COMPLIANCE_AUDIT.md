# COMPLIANCE AUDIT — MnqTwoStrategies vs. Master Specification **V5**

Audited against `two_automated_strategies_for_claude_v5_MNQ_ONLY.md` (V5 supersedes V4)
after applying the corrections in `FABLE_5_CORRECTION_PROMPT_MNQ.md`.
The V4 audit this replaces is preserved in git history; the Previous/Corrected table is in
`docs/CHANGELOG_V5.md`.

Legend: ✅ Yes · ⚙️ Yes, governed by an exposed config parameter (spec-ambiguous or
spec-mandated configurable) · ⚠️ Partial / caveat.

Code refs: `Shared` = `src/MnqTwoStrategiesShared.cs`, `FB` = `src/FakeBreakoutEngine.cs`,
`VBR` = `src/VectorBreakRetestEngine.cs`, `Host` = `src/MnqTwoStrategies.cs`,
`Tests` = `tests/Tests.cs` (34/34 passing under Mono against the actual engine sources).

## 0. V5 correction verification (dedicated rows)

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| **FAKE BREAKOUT 1m/3m SHORT: BLUE_VECTOR above key level → REGULAR or RED_VECTOR reclaim below = valid** | ✅ | FB `ProcessLtf` break-candle filter + BLUE-first reclaim branch | Verified by tests `BLUE->REGULAR = VALID`, `BLUE->RED = VALID`; applies to 1m AND 3m (same code path serves both series) |
| BLUE path: VIOLET_VECTOR reclaim NOT valid | ✅ | same reclaim branch | Test `BLUE->VIOLET = NO entry` + "invalid reclaim" diag |
| BLUE path EMA behavior: enter on reclaim close if already below EMA9, else wait for first close below; cancel on completed close above fake-break high; stop at structure HIGH/WICK | ✅ | FB `ProcessLtf` (emaOk/WaitingEma branches, vector-agnostic once structure valid), `TryEnter` stop | Identical machinery as GREEN/REGULAR paths, per V5 §10 |
| BLUE_VECTOR is NOT a valid 15m FB parent initiator | ✅ | FB `TryTrigger` vector filter (GREEN/REGULAR short, RED/REGULAR long only) | Unchanged from V4 |
| FB parent trigger has NO prior-close/cross requirement (Fix 2) | ✅⚙️ | `FbConfig.RequirePriorCloseInside` default **false**; `TryTrigger` | Legacy research param retained, default FALSE, labeled "keep FALSE"; test: trigger with prior close already beyond level |
| VBR parent trigger has NO cross-through/prior-close requirement (Fix 3) | ✅⚙️ | `VbrConfig.RequireCrossThrough` default **false**; `OnFifteenMinuteBar` | Legacy research param, default FALSE; test: low > DO and prior close above DO still triggers |
| Active VBR parent never restarted/replaced/extended by a later vector (Fix 5) | ✅⚙️ | `VbrConfig.RetriggerReplacesActiveSetup` default **false** | Test: one PARENT TRIGGER only; expiry exactly 4 candles after ORIGINAL trigger |
| Traders Reality source ported (Fix 4) | ✅/⚠️ | `KeyLevelEngine` (day roll, `IsInPsySession`, `CalcSydneyDst`) | See §5 rows for detail and the documented caveats |
| No strategy-level forced session-close exit (Fix 6) | ✅ | Host SetDefaults `IsExitOnSessionClose=false`; param relabeled PLATFORM-only, default OFF | 11:30 ET remains a NEW-ENTRY cutoff only; open positions run under stop/target/trail/runner |
| A- = first ACTUALLY-ELIGIBLE entry candle (Fix 7) | ✅ | `FbConfig.GradeBasis=FirstTradableCandle` default; FB `TryEnter` + FirstTradable tracking in `ProcessLtf` | Tests: premarket parent + 9:30–9:45 entry = A- 26% (118 lots); later entry = B+ 10% (45 lots) |
| Equal-price targets: tick-normalize, merge exact equality only (Fix 8) | ✅ | Shared `GetSortedTargets(…, normalizeToTick)` | Tests: 13-name merge at one price; adjacent ticks 100.25/100.50 NOT merged |

## 1. Global / instrument scope

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Only the two named strategies; no extra strategies/filters | ✅ | whole codebase | The two V4-era extra filters (prior-close-cross, VBR cross-through) now default OFF |
| Completed candles for all signal decisions | ✅ | Host `Calculate.OnBarClose`; engines consume completed-bar snapshots | Intrabar prices only in stop orders + configurable VBR "target reached" touch |
| Entry window 9:30–11:30 ET both strategies | ✅ | Host `IsEntryTimeAllowed`; engines `TryEnter` | Signal close ≥ 9:30:00 and ≤ 11:30:00 |
| Premarket 15m candles count toward validity; premarket LTF signals never carried forward | ✅ | pattern-start gates on candle OPEN ≥ 9:30 ET | Test: premarket 1m pattern ignored |
| MNQ only; never NQ; no automatic instrument selection | ✅ | Host DataLoaded instrument gate | Trading disabled on any non-MNQ instrument |
| $2 per index point; DollarRisk = StopPts × $2; never $20 | ✅ | Shared `PositionSizer.MnqDollarsPerPoint` const | Spec example reproduced (5,000/50%/55pts → 22) |

## 2. Architecture / separation

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| `enum StrategyId`; two independent engines; no cross-completion | ✅ | Shared `StrategyId`; FB/VBR separate classes, no mutual reference | |
| Fully separate state (parent, direction, level, counters, LTF state, EMA wait, entry, stop, targets, re-entry, grade, risk, sizing, IDs, logs) | ✅ | FB `FbSlot`/`LtfSetup`; VBR private fields | |
| Shared code read-only utilities only | ✅ | Shared file | No mutable setup object shared |
| StrategyId on every order and log record | ✅ | `FB_*`/`VBR_*` signals; `TradeRecord.Strategy`; `MnqLogger.Diag(id,…)` | |
| Order tags FB_LONG/FB_SHORT/VBR_LONG/VBR_SHORT | ✅ | engine `EntrySignal` properties | |
| Simultaneous-position behavior exposed as a setting | ⚙️ | Host `AllowSimultaneousStrategies` (default false) | Spec-mandated setting; NT netting warning in README |
| Five-question ownership gate before any signal | ✅ | Structural (per-engine levels/timeframes/states/windows) | |

## 3. Key-level ↔ strategy mapping

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| FB triggers only YDay/LWeek H/L; DAILY_OPEN never | ✅ | FB `EligibleLevels` | |
| VBR triggers only DAILY_OPEN; YDay/LWeek never | ✅ | VBR reads only `Levels.DailyOpen` | |
| No cross-strategy level substitution (4 examples) | ✅ | structural | |

## 4. Vector classification (TR calcPvsra)

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| avg vol of previous 10; spread = vol×(high−low); highest spread of previous 10 | ✅ | Host `BuildSnap` (bars [1]..[10]); Shared `VectorClassifier` | Matches supplied `calcPvsra` exactly (sum/10, `ta.highest(volumeSpread[1],10)`) |
| Climax ≥2×avg OR spread ≥ highest → GREEN/RED; medium ≥1.5× → BLUE/VIOLET; else REGULAR | ✅ | `VectorClassifier.Classify` | Same branch order and `close > open` bullish test as the source |
| Close==Open bearish branch; climax priority; completed candles; per-timeframe | ✅ | same | |
| Internal codes ±3/±2/±1 | ✅ | `VectorType` enum values | Matches `getPvsraFlagByColor` |

## 5. Key levels / shared 18-level take-profit engine

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Exactly 18 selectable targets; R2/S3 internal only | ✅ | `TpLevelId` (18); `R2`/`S3` getters not selectable | Test: R2=101.00 never appears as a target event |
| DAILY_OPEN = TR `getdayOpen()` semantics | ✅⚙️ | `KeyLevelEngine` day roll; `DayStartMinutesEt` | Faithful port: `getdayOpen` sets open on `ta.change(time('D'))` = the instrument's new exchange day (TR_MAIN L677 calls it directly). For CME MNQ that boundary is 17:00 CT = **18:00 ET**, the default. The library's "exchange midnight" comment (forex/crypto) is available via the compat value 0. Test: Daily Open stable intraday |
| YDay Hi/Lo per supplied higher-TF retrieval | ✅ | `prevDay` aggregate | **CONFIRMED against TR_MAIN**: `dayHigh/dayLow = f_security(tickerid,'D',high/low,false)` plotted as "YDay Hi"/"YDay Lo" (L309-310, L348-351). The `_repaint=false` wrapper returns the PREVIOUS COMPLETED daily value on both the historical and realtime branches — exactly the implemented prev-day aggregate, non-repainting |
| LWeek Hi/Lo per supplied retrieval | ✅⚙️ | `prevWeek` aggregate; `WeekStartMinutesEt` | **CONFIRMED against TR_MAIN**: `weekHigh/weekLow = f_security(tickerid,'W',...)` plotted as "LWeek Hi"/"LWeek Lo" (L337-338, L353-356) = previous completed weekly bar. Boundary default Sunday 18:00 ET = TradingView weekly-bar open for MNQ |
| Psy levels: port `calcPsyLevels`, not an arbitrary calculation | ✅⚙️ | `IsInPsySession` + accumulation in `OnOneMinuteBar`; `CalcSydneyDst`; `PsyLevelTypeParam` | Direct port. **psyType now CONFIRMED from TR_MAIN L243**: `syminfo.type == 'forex' ? 'forex' : 'crypto'` — MNQ is `futures`, so the **CRYPTO** path is correct (previous default of Forex was wrong and is fixed). Session days follow Pine numbering (1=Sunday): crypto `'2200-0600:1'` = **Sunday 22:00 → Monday 06:00** in GMT+1/GMT by Sydney DST; forex `'0000-0800:2'` = Monday 00:00–08:00 GMT. Init-on-entry, max/min in-session, hold outside. The library's `timestampPreviousDayOfWeek('Saturday',…)` feeds only the line's draw-start (TR_MAIN L654-657), not the values. Tests cover both paths + the Saturday exclusion |
| Pivot/M formulas (PP, R1, S1, R2, S2, R3, S3, M0–M5) | ✅ | `KeyLevelEngine` getters | **CONFIRMED against TR_MAIN**: pivots L316-324 from the same previous-completed-day `f_security` values; `m0C..m5C` L569-574 match the implemented formulas exactly (test asserts M0/M3/M5 identities) |
| `GetNextTakeProfitLevel`: strictly above/below, sorted, chainable | ✅ | `GetSortedTargets` | Test: strict ordering, ref-equal exclusion |
| Equal exact prices = one target event, all names kept; no double-reach | ✅ | tick-normalized exact-equality merge (Fix 8) | Tests in §0 |
| NaN levels ignored; levels equal to reference ignored | ✅ | NaN skip + strict compare | |
| Target-event logging (StrategyId, names, price, distance, reached/broken/trail) | ✅ | FB/VBR diags | |
| Diagnostic print of all 18 levels for a selected date | ✅ | Host `MaybePrintLevelsDiagnostic`, `PrintLevelsDiagnosticDate` param | Fix 4 requirement, plus internal R2/S3 for comparison |

## 6. Position sizing

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| A+ 50% / A− 26% / B+ 10% true account risk; floor rounding | ✅ | `PositionSizer.Contracts`; host params default 50/26/10 | Tests exercise 26% and 10% sizing arithmetic |
| Account balance source | ⚙️ | Host `AccountBalance` | Live cash value / backtest param + compounding (spec silent) |

## 7. Strategy 1 — Fake Breakout (V5)

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| A- = entry within FIRST eligible 15m candle; B+ later; 26%/10% | ✅ | grade block in `TryEnter` (Fix 7 default) | "Eligible" = first candle where a fresh LTF entry may be accepted (≥ 9:30); tests in §0 |
| 15m parent / 3m+1m entry; no 4H | ✅ | engine structure | |
| Trigger levels YDay/LWeek H/L only | ✅ | `EligibleLevels` | |
| EMA(close,9) per 15m/3m/1m | ✅ | Host `EMA(BarsArray[i],9)` | |
| Short parent: trades above + closes above; wick alone insufficient; GREEN/REGULAR initiator | ✅ | `TryTrigger` | No prior-close condition (Fix 2) |
| Long parent mirror; RED/REGULAR initiator; VIOLET not allowed | ✅ | `TryTrigger` long branch | |
| StructuralHigh/Low tracking; freeze on 15m reclaim close | ✅ | `Process15`/`TryReclaim` | |
| 15m reclaim vector participation (short: GREEN→REG/RED/VIOLET, REG→RED/VIOLET; long: RED→REG/GREEN, REG→GREEN; REG+REG invalid) | ✅⚙️ | `TryReclaim` | Invalid-reclaim consequence still not defined by V5 → configurable (default: doesn't count, keep waiting) — unresolved item 4 |
| Validity 4+2, max 6; 11:30 cutoff; premarket candles count | ✅ | `Process15` | |
| §9 LTF long: RED/REGULAR break → GREEN/BLUE reclaim; REGULAR reclaim invalid; EMA wait/cancel; stop at structure LOW/WICK | ✅ | `ProcessLtf` long branches | Unchanged by V5 |
| §10 LTF short paths A (GREEN, reclaim behavior preserved), **B (BLUE → REGULAR/RED only)**, C (REGULAR → RED/VIOLET; REG+REG invalid); EMA wait/cancel; stop at structure HIGH/WICK | ✅ | `ProcessLtf` short branches | §0 dedicated rows + tests |
| Monitor 1m/3m independently; first valid wins; failed LTF cancels only itself; one entry per parent | ✅ | `Ltf1`/`Ltf3`, `TryEnter` | |
| §7 15m EMA confluence before entry | ✅⚙️ | `TryEnter` | Failure handling configurable (cancel default) |
| §11 structural invalidation on completed 1m/3m close beyond frozen extreme | ✅ | `ProcessLtf` breach check | Pre-entry setups; wicks never invalidate |
| §12 profit mgmt: first target from 18-level engine; break → 3m EMA(9) runner; break definition configurable | ✅⚙️ | `OnEntryExecution`, `ManagePosition`, `FbTargetBreakMode` | "First target successfully broken" still not finalized by V5 → remains configurable (unresolved item 1) |

## 8. Strategy 2 — Vector Break Retest (V5)

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| A+ = 50% risk, every valid trade | ✅ | `TryEnter` | |
| 15m + 1m only; DAILY_OPEN only; 1m EMA(9); any 1m candle type may retest | ✅ | engine structure | Host never feeds VBR 3m data |
| Long trigger: completed 15m GREEN_VECTOR closes above Daily Open (nothing else) | ✅ | `OnFifteenMinuteBar` (Fix 3) | Test in §0 |
| Short trigger: RED_VECTOR closes below (nothing else) | ✅ | same | |
| Exactly next 4 completed 15m candles; NO extension; original clock immutable | ✅ | validity clock + Fix 5 | Test: expiry at original candle #4 |
| Patterns A (wick retest + EMA already satisfied; stop at retest wick) and B (close-through + reclaim + EMA condition; stop at structure extreme), both directions | ✅⚙️ | `OnOneMinuteBar` | Pattern-B EMA-failure handling configurable (default no entry) |
| Re-entry after stop-out: same-candle wick/close rule → scan following candle; fresh setup; inside window and 9:30–11:30 | ✅⚙️ | re-entry states | Scan-duration literal reading configurable |
| 50-point chaining; ignore adverse EMA while nearby target active; re-reference on reach; trail when >50 | ✅ | `AdvanceTargetChain` + chain loop | "Reached" definition configurable (unresolved item 2, default intrabar touch) |
| Trail: completed 1m close through EMA9 → 90%; wicks don't count | ✅⚙️ | trail branch | 1-contract case configurable (runner default) |
| Final 10%: completed 1m close through most recent confirmed supporting swing | ✅⚙️ | runner branch + `SwingTracker` | Swing algorithm not defined by V5 → configurable strength-k fractal (unresolved item 3) |

## 9. Global entry-time rule

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Entries only 9:30–11:30 ET; premarket parents allowed; patterns must FORM ≥ 9:30; never bank premarket signals | ✅ | host gates + pattern-start gates | Tests: premarket pattern ignored; spec's 8:45-parent example reproduced in the A- test |
| 11:30 is a NEW-ENTRY cutoff only — no strategy flatten | ✅ | Fix 6 | Platform session-close option exists but defaults OFF and is labeled as platform behavior |

## 10. Implementation notes / logging

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Two modules sharing vectors/time/sizing; suggested state sets | ✅ | `FbState`/`VbrState` | |
| No repainting | ✅ | OnBarClose everywhere | |
| Full logging field list incl. MFE/MAE/R/re-entry #/premarket flags | ✅ | `TradeRecord` CSV + diags | |
| Win/loss + backtest statistics | ✅ | `StrategyStats` per strategy + NT analyzer | |
| No silent filters; ambiguities exposed as parameters | ✅ | all remaining ambiguities parameterized and listed below | |

## Unresolved items (per correction prompt — NOT invented, exposed as parameters)

| # | Item | Status / parameter | Default |
|---|---|---|---|
| U1 | FB "first target successfully broken" exact definition | `FbTargetBreakModeParam` (Touch / 1m close / 3m close) | 3m completed close beyond |
| U2 | VBR "target reached" exact definition | `VbrTargetReachedModeParam` (IntrabarTouch / OneMinuteCloseBeyond) | IntrabarTouch |
| U3 | Final-10% runner swing-confirmation algorithm | `VbrRunnerSwingStrength` (strength-k fractal, confirmed k bars later) | 2 |
| U4 | Invalid 15m reclaim (REG+REG etc.): dies vs. keeps waiting | `FbInvalidReclaimCancelsSetup` | false (keeps waiting) |
| U5 | 15m reclaim/freeze sequencing vs. LTF scanning start | `FbRequire15mReclaimBeforeLtfEntry` | true (scan after freeze, per suggested state list) |
| U6 | Pattern-B reclaim failing the EMA condition | `VbrPatternBWaitForEma` | false (no entry, structure cleared) |
| U7 | Re-entry scan window (only the following candle vs. rest of window) | `VbrReentryScanOnlyFollowingCandle` | true (literal reading) |
| U8 | 90/10 split with 1 contract | `VbrSingleContractBecomesRunner` | true |
| U9 | Simultaneous FB+VBR positions | `AllowSimultaneousStrategies` | false |

## Outstanding caveats — read before calling this "fully compliant"

1. **TR main indicator NOW SUPPLIED — earlier caveat closed.** `TR_MAIN` resolved the two
   open items: YDay/LWeek use `f_security(..., 'D'/'W', ..., false)` = previous completed
   daily/weekly values (matching the implementation), and psyType for a futures symbol is
   `crypto` (previous Forex default corrected). Pivots and M-levels are confirmed verbatim.
2. **One genuinely unverifiable item remains: the psy 4H-grid.** The source tests session
   membership via `time('240', session, gmt)`, so membership is decided on TradingView's
   4-hour bar grid rather than on the chart bar. Reproducing that requires TradingView's
   4H anchor, which cannot be derived from the source — and anchoring it to the exchange-day
   open makes the source's own forex branch fall permanently out of session, so that anchor
   is demonstrably not the intended one. The implementation therefore uses the **literal
   session window** (identical to the 4H reading whenever the grid aligns with the session
   start, which is the MNQ crypto case — asserted by test), with
   `PsyUse4HourGrid` retained as a clearly-named compatibility parameter, default OFF.
   Verify against TradingView with `PrintLevelsDiagnosticDate` before relying on Psy levels.
3. **Day-boundary compatibility.** TR `getdayOpen` follows the instrument's daily-bar
   boundary; for CME MNQ that is 18:00 ET (default). The library's "exchange midnight"
   comment describes forex/crypto; `DayStartMinutesEt = 0` reproduces it.
4. **Engine logic is test-verified (39/39) under Mono; the NinjaTrader host file
   (`MnqTwoStrategies.cs`) still requires an F5 compile inside NT8** — no NT8 runtime exists
   in this environment. Compiling ≠ compliant, which is why the engine-level tests exist.
5. Unresolved items U1–U9 above remain configurable by design; exact-spec compliance for
   those specific definitions cannot be claimed until the spec pins them down.
