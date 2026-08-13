# COMPLIANCE AUDIT — MnqTwoStrategies vs. Master Specification

Second-pass audit performed after implementation, comparing the finished NinjaScript against
every rule in `two_automated_strategies_for_claude_v4_MNQ_ONLY_3.md`.

Legend for **Implemented?**: ✅ Yes · ⚙️ Yes, behavior governed by an exposed config parameter
(because the spec is ambiguous or explicitly says "configurable") · ⚠️ Partial / caveat.

Code references: `Shared` = `src/MnqTwoStrategiesShared.cs`, `FB` = `src/FakeBreakoutEngine.cs`,
`VBR` = `src/VectorBreakRetestEngine.cs`, `Host` = `src/MnqTwoStrategies.cs`.

## 1. Global / instrument scope

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Only the two named strategies; no extra strategies/filters | ✅ | whole codebase | Nothing else trades; no silent filters added |
| Completed candles for all signal decisions | ✅ | Host `Calculate.OnBarClose`; engines consume completed-bar `BarSnap`s | Intrabar price used only for stop orders + "target reached" touch (see VBR-9) |
| Entry window 9:30–11:30 ET for both strategies | ✅ | Host `IsEntryTimeAllowed`, engines `TryEnter` | Inclusive of a signal candle closing exactly 11:30:00 (SH-5) |
| Premarket 15m candles count toward validity; premarket LTF signals never carried forward | ✅ | FB/VBR pattern starts gated by `IsAtOrAfterSessionStart(bar.EtOpen)`; 15m clocks run premarket | Pattern-forming candles must OPEN ≥ 9:30 ET |
| Trade MNQ only; never submit NQ | ✅ | Host `State.DataLoaded` instrument gate; single-instrument strategy | Refuses to trade unless MasterInstrument == "MNQ" |
| No automatic instrument selection; NQ/MNQ not interchangeable | ✅ | same | Instrument comes only from the chart it is applied to, and must be MNQ |
| $2 per index point per contract; never $20 | ✅ | Shared `PositionSizer.MnqDollarsPerPoint = 2.0` (const) | Hard constant; P&L math uses the same constant |
| DollarRiskPerMNQContract = StopDistancePoints × $2 | ✅ | Shared `PositionSizer.Contracts` | Matches spec example (5,000 / 50% / 55pts → 22 contracts) |

## 2. Critical architecture / separation

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| `enum StrategyId { FAKE_BREAKOUT, VECTOR_BREAK_RETEST }` | ✅ | Shared `StrategyId` | Exact enum |
| Two independent strategy engines; no cross-completion of setups | ✅ | FB and VBR are separate classes with private state; they hold no reference to each other | Engines communicate only outward via `IMnqHost` |
| Separate parent state, direction, key level, validity counter, LTF state, EMA wait, entry, stop, targets, re-entry, grade, risk %, sizing, trade ID, logging | ✅ | FB `FbSlot`/`LtfSetup`; VBR private fields | Every listed item exists per engine; nothing shared |
| Shared code only read-only utilities (vectors, EMA, time, key levels, sizing) | ✅ | Shared file | No mutable setup object is shared |
| Every order and log record carries StrategyId | ✅ | Order names `FB_*`/`VBR_*`; `TradeRecord.Strategy`; `MnqLogger.Diag(id,…)` | |
| Order tags FB_LONG/FB_SHORT/VBR_LONG/VBR_SHORT | ✅ | FB `EntrySignal`, VBR `EntrySignal` | Exits: FB_STOP_*/FB_RUN_*, VBR_STOP_*/VBR_TP90_*/VBR_RUN_* |
| Simultaneous-position behavior exposed as configurable setting | ⚙️ | Host `AllowSimultaneousStrategies` (default false), `CanOpenPosition` | SH-2. Spec explicitly asks for a setting. Note: NT nets opposite-direction positions inside one strategy — see README warning |
| Five-question gate before processing any signal (owner / level eligibility / parent active / timeframe / validity window) | ✅ | Structural: each engine only scans its own levels, its own timeframes, inside its own state machine and window checks | Enforced by construction, not by a literal 5-question function |

## 3. Key-level ↔ strategy mapping

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| `enum KeyLevelId { YDAY_HIGH, YDAY_LOW, LWEEK_HIGH, LWEEK_LOW, DAILY_OPEN }` | ✅ | Shared `KeyLevelId` | Exact enum |
| FB triggers only YDay/ LWeek H/L; DAILY_OPEN never starts FB | ✅ | FB `EligibleLevels` static array | DAILY_OPEN absent from the array |
| VBR triggers only DAILY_OPEN; YDay/LWeek never start VBR | ✅ | VBR trigger reads only `Levels.DailyOpen` | No other level is consulted for triggering |
| No cross-strategy level substitution (4 spec examples) | ✅ | Structural consequence of the two rows above | 1m DO retests only reach VBR; 1m/3m fake-breaks only reach FB |
| Shared level calculator does not make levels valid triggers for both | ✅ | `KeyLevelEngine` is read-only; trigger filtering lives inside each engine | |

## 4. Traders Reality vector classification

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Vectors computed independently per timeframe | ✅ | Host `BuildSnap` runs per BarsInProgress | 1m/3m/15m each classify from their own series |
| AverageVolume = mean of previous 10 completed candles | ✅ | Host `BuildSnap` loop `i=1..10` | Uses bars [1]..[10] — completed candles only |
| VolumeSpread = volume × (high − low); HighestVolumeSpread = max of previous 10 | ✅ | same | |
| Climax: vol ≥ 2×avg OR spread ≥ highest → GREEN/RED by close vs open | ✅ | Shared `VectorClassifier.Classify` | |
| Medium: vol ≥ 1.5×avg → BLUE/VIOLET | ✅ | same | |
| Else REGULAR_BULLISH/REGULAR_BEARISH | ✅ | same | |
| Close == Open follows bearish branch; climax priority over medium; completed candles only | ✅ | same (`bullish = close > open`; if-order) | |
| Internal codes +3/−3/+2/−2/+1/−1 | ✅ | Shared `VectorType` enum values | |

## 5. Shared 18-level take-profit engine

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Trigger levels ≠ take-profit levels; targets never expand trigger universes | ✅ | Target engine used only post-entry (`OnEntryExecution` / `AdvanceTargetChain`) | |
| Exactly 18 selectable target levels (M0–M5, PP, DAILY_OPEN, YDAY_H/L, LWEEK_H/L, R1, R3, S1, S2, PSY_H/L) | ✅ | Shared `TpLevelId` (18 members); Host 18 enable checkboxes | Each level individually selectable, default all on |
| Daily Open = TR getdayOpen (open at start of new exchange day / exchange midnight) | ⚙️ | Shared `KeyLevelEngine.OnOneMinuteBar` day roll | SH-1: TR source not supplied; day boundary = configurable minutes-ET offset, default midnight ET |
| YDay Hi/Lo = previous completed day | ✅ | `prevDay` aggregate | |
| LWeek Hi/Lo = previous completed week | ⚙️ | `prevWeek` aggregate | SH-1: week boundary configurable, default Sunday 18:00 ET (futures week) |
| Psy levels: port TR calcPsyLevels, not arbitrary numbers | ⚠️⚙️ | psy window in `KeyLevelEngine` | SH-1: TR source was NOT attached. Best-effort port: high/low of first N hours (default 8) of the new week. Supply the TR source for an exact port |
| PP=(H+L+C)/3; R1=2PP−L; S1=2PP−H; R2=PP−S1+R1; S2=PP−R1+S1; R3=2PP+H−2L; S3=2PP−(2H−L) | ✅ | `KeyLevelEngine` pivot getters | Formulas verbatim, from previous completed day |
| M0=(S2+S3)/2 … M5=(R2+R3)/2 | ✅ | `M0`..`M5` getters | Verbatim |
| R2/S3 computed internally but NOT selectable targets | ✅ | `R2`,`S3` exist; absent from `TpLevelId` | |
| `GetNextTakeProfitLevel(direction, referencePrice)` — strictly above (long) sorted asc / strictly below (short) sorted desc | ✅ | Shared `GetSortedTargets` | Returns the full sorted chain; first element = next key level |
| Equal-price levels = one target event, all names kept/logged | ✅ | merge step in `GetSortedTargets` (tick-size tolerance) | |
| Ignore NaN levels and levels equal to reference | ✅ | NaN skip + strict half-tick comparison | |
| Target events log StrategyId, names, price, distance, reached/broken/trail | ✅ | FB `ActivateRunner`/fill diag; VBR `AdvanceTargetChain`/`ManagePosition` diags | |

## 6. Position sizing

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| A+ 50%, A− 26%, B+ 10% true account risk at stop | ✅ | Host risk% params (defaults 50/26/10) → engine configs | Exposed as parameters but default exactly to spec |
| Contracts = floor(RiskDollars / (StopPts × 2)); always round DOWN | ✅ | Shared `PositionSizer.Contracts` | `Math.Floor`; 0 contracts → entry blocked and logged |
| Account balance source | ⚙️ | Host `AccountBalance` | SH-3: live = account cash value; backtest = starting balance param + optional realized-PnL compounding (spec silent on source) |

## 7. Strategy 1 — Fake Breakout

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| A− if valid entry within FIRST eligible 15m candle; B+ in candles 2–4 or +2 ext | ⚙️ | FB `TryEnter` grade block | FB-6: "first eligible" defaults to literal validity candle #1 (`FbGradeBasis` config for first-tradable alternative) |
| A− 26% / B+ 10% | ✅ | `FbConfig` ← host params | |
| Timeframes 15m parent / 3m + 1m entry & invalidation; no 4H filter | ✅ | engine method structure | No 4H series exists |
| Eligible levels: YDay H/L, LWeek H/L only | ✅ | `EligibleLevels` | |
| EMA(close,9) separately on 15m/3m/1m | ✅ | Host `EMA(BarsArray[i], 9)` per series | |
| Short parent: completed 15m trades above AND closes above level | ✅ | FB `TryTrigger` (`High > lvl && Close > lvl`) | FB-1: prior-close-inside requirement is a config (default on) so "breakout" means crossing |
| Wick above without close above does not start it | ✅ | close condition required | |
| Short initiating candle: GREEN_VECTOR or REGULAR | ✅ | `TryTrigger` vector filter | BLUE/VIOLET excluded (not listed in spec) — flagged FB-4 |
| StructuralHigh = initiating high, then max of subsequent completed 15m highs | ✅ | `TryTrigger` + `Process15` | |
| Freeze StructuralHigh on completed 15m close back below level | ✅ | `TryReclaim` | Freeze includes the reclaim candle's extreme |
| Short reclaim vectors: GREEN→REGULAR/RED/VIOLET; REGULAR→RED/VIOLET; REG+REG invalid | ✅⚙️ | `TryReclaim` | FB-3: invalid reclaim defaults to "does not count, keep waiting" (config to cancel instead) |
| Long parent mirror (trades below + closes below; RED or REGULAR initiator; VIOLET not allowed) | ✅ | `TryTrigger` long branch | |
| Long reclaim vectors: RED→REGULAR/GREEN; REGULAR→GREEN; REG+REG invalid | ✅⚙️ | `TryReclaim` long branch | |
| Validity: 4 primary + 2 extension, max 6; 11:30 cutoff overrides; premarket candles count | ✅ | `Process15` count/expiry | Extension is automatic when no entry occurred (spec wording) |
| Premarket LTF signals ignored; new pattern must form ≥ 9:30 | ✅ | `ProcessLtf` structure-start gate on `bar.EtOpen` | |
| 15m EMA confluence (close vs 15m EMA9) before actual LTF entry; no fresh crossover needed | ✅⚙️ | `TryEnter` confluence check on last completed 15m | FB-5: failure cancels that LTF setup by default (config: wait) |
| Monitor 1m and 3m independently; first valid entry wins | ✅ | `Ltf1`/`Ltf3` independent sub-machines | Whichever fires `TryEnter` first enters |
| Failed LTF setup cancels only itself; keep scanning while parent alive | ✅ | `s.Reset()` paths | |
| Once entered, stop looking for another entry for that parent | ✅ | `TryEnter` resets both LTF setups; slot leaves scanning states | FB has no re-entry |
| LTF long combos: RED/REGULAR break below → GREEN/BLUE reclaim above; REGULAR reclaim NOT valid | ✅ | `ProcessLtf` break/reclaim vector filters | Invalid reclaim cancels that LTF attempt (price is back above level without a valid signal) |
| Long EMA step: enter if reclaim close > EMA9 else wait for first close > EMA9; cancel if close < structure low while waiting | ✅ | `ProcessLtf` WaitingEma branch | Structure extreme extended by wicks while waiting (stop = full structure wick) |
| Long initial stop = LOW/WICK of fake-break structure | ✅ | `TryEnter` (`stop = s.StructExtreme`) | Live-until-cancelled stop-market at structure |
| LTF short: GREEN break above → close back below (any type); REGULAR-first → RED/VIOLET reclaim; REG+REG invalid | ✅ | `ProcessLtf` short branch | |
| Short EMA wait + cancel above fake-break high; stop = HIGH/WICK | ✅ | mirrored branches | |
| Structural invalidation: completed 1m OR 3m close beyond frozen extreme cancels ENTIRE setup; wicks don't | ✅ | `ProcessLtf` breach check | Applies pre-entry (it cancels the *setup*; positions are governed by stop/runner) — FB-10 |
| Profit mgmt: nearest directional level from shared engine = first target | ✅ | `OnEntryExecution` → `GetSortedTargets` | Logged with names/price/distance |
| First target "successfully broken" → 3m EMA(9) runner; LONG exit 3m close < EMA9, SHORT close > EMA9 | ✅⚙️ | `ManagePosition`/`ActivateRunner` | Break definition configurable (Touch / 1m close / 3m close, default 3m close) exactly as the spec instructs |
| Don't invent target universe or break definition | ✅ | targets only from 18-level engine; break mode config | No partial-profit rule invented for FB (FB-8) |

## 8. Strategy 2 — Vector Break Retest

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Every valid VBR = A+ = 50% risk | ✅ | `TryEnter` (grade fixed "A+", `RiskPctAPlus`) | |
| 15m + 1m only; Daily Open only; 1m EMA(9) | ✅ | engine has no 3m handler; Host never feeds VBR 3m bars | |
| Any 1m candle type may perform retest/reclaim | ✅ | no vector filter in VBR pattern code | |
| Long trigger: completed 15m GREEN_VECTOR closes above Daily Open | ✅⚙️ | `OnFifteenMinuteBar` trigger | VBR-1: cross-through requirement is a config (default on) |
| Short trigger: completed 15m RED_VECTOR closes below Daily Open | ✅⚙️ | same | |
| Exactly NEXT 4 completed 15m candles valid; NO +2 extension | ✅ | validity clock, expiry at count ≥ 4 | |
| Premarket 15m candles count; premarket 1m signals don't carry | ✅ | clock runs premarket; pattern start gated ≥ 9:30 | |
| Long Pattern A: 1m wicks into DO, holds back above; enter if close already above 1m EMA9; no fresh crossover needed; stop = retest candle LOW/WICK | ✅ | `OnOneMinuteBar` Pattern A branch | Close ≤ EMA9 → no entry, keep scanning (Pattern A defines no wait) — VBR-3a |
| Long Pattern B: 1m close below DO → close back above + EMA condition → enter; stop = LOW of the 1m structure below DO | ✅⚙️ | Pattern B branch (`structExtreme` incl. reclaim wick) | VBR-3: EMA-failure default = no entry/structure cleared (config: wait mode) |
| Short Patterns A/B mirrored | ✅ | same branches, short side | |
| Stop-out does not kill parent; clock continues; not restarted | ✅ | `ApplyExitLeg` full-stop-out path | |
| Re-entry: same 15m candle of stopped attempt must wick into/through DO and close back on trade side → scan NEW 1m setup during FOLLOWING candle; fresh setup required | ✅⚙️ | `OnFifteenMinuteBar` re-entry eligibility; `REENTRY_SCAN` state | VBR-4: scan restricted to that single following candle by default (config) |
| Re-entries inside original 4-candle window and 9:30–11:30 | ✅ | `validityCount < 4` check + entry time gate | |
| Profit mgmt: next level from shared engine; ≤ 50 pts → hold, ignore adverse 1m EMA9; on reach → new reference → repeat; > 50 pts → 1m EMA9 trail | ✅ | `AdvanceTargetChain` + chain loop in `ManagePosition` | "Reached" = intrabar touch of the level (VBR-9); chaining handles multiple levels in one bar |
| Trail: completed 1m close through EMA9 against trade → take 90% | ✅⚙️ | trail branch | VBR-6: 1-contract case → whole contract becomes runner by default (floor(0.9)=0) |
| Final 10%: hold until completed 1m close through most recent confirmed supporting swing → exit | ✅⚙️ | runner branch + `SwingTracker` | VBR-5: swing strength configurable (default 2); "higher low" read as most-recent confirmed swing |
| Wicks through EMA / beyond structure do not count | ✅ | all exit checks use `bar.Close` | |

## 9. Global entry-time rule

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Entries only 9:30–11:30 ET | ✅ | `IsEntryTimeAllowed` at signal close | |
| Premarket parent activity allowed; premarket candles count toward validity | ✅ | 15m clocks run regardless of time | |
| Never bank premarket LTF setups; entry pattern must itself form ≥ 9:30 | ✅ | pattern-start gates on candle OPEN time | Matches the spec's 8:45-parent example: signals in candles #1–#3 ignored; candle #4 needs a fresh pattern |

## 10. Implementation notes / logging

| Specification Rule | Implemented? | Function/Code Section | Notes |
|---|---|---|---|
| Two distinct modules sharing vectors/time/sizing | ✅ | file layout | |
| Suggested FB states | ✅ | `FbState` (+ per-LTF wait flags) | WAITING_FOR_15M_RECLAIM ≡ BREAKOUT_15M_ACTIVE; INVALIDATED/EXPIRED collapse to IDLE after logging |
| Suggested VBR states | ✅ | `VbrState` | TRAIL_MODE is a flag inside POSITION_OPEN (`trailActivated`) |
| No repainting: vectors, closes, EMA entries, structure breaks on completed candles | ✅ | Calculate.OnBarClose everywhere | |
| Full logging list (strategy, grade, date/time, direction, parent time, validity candle, entry TF, pattern, entry, stop, stop pts, balance, risk %, contracts, target, exit, reason, P&L $, P&L pts, R, MFE, MAE, re-entry #, premarket parent, entry-after-9:30) | ✅ | Shared `TradeRecord` (CSV + Output window) + per-event diags | Every listed field is a column |
| MFE / MAE | ✅ | engines track per-1m-bar extremes vs entry | |
| R-multiple reporting | ✅ | per leg + net-R per trade | |
| Win/loss + backtest statistics | ✅ | Shared `StrategyStats`, printed per strategy at State.Terminated; NT's own Strategy Analyzer stats also apply | |
| Do NOT silently add filters; ambiguities exposed as parameters | ✅ | every FB-*/VBR-*/SH-* item is a named parameter with the default documented | |

## Ambiguities register (all exposed as parameters — confirm or change defaults)

| # | Question | Default behavior |
|---|---|---|
| FB-1 | Does a 15m candle beyond an already-broken level re-trigger, or must it cross (prior close inside)? | Must cross (prior 15m close inside the level) |
| FB-2 | Must the 15m reclaim/freeze occur before 1m/3m entry scanning starts? (Suggested state list implies yes) | Yes |
| FB-3 | REGULAR breakout + REGULAR reclaim "invalid": setup dies, or reclaim just doesn't count? | Reclaim doesn't count; keep waiting |
| FB-4 | BLUE/VIOLET vectors as 15m initiating candles, and BLUE as short reclaim — spec doesn't list them | Excluded (only listed vectors allowed) — fixed, not a parameter; say if wrong |
| FB-5 | 15m EMA confluence fails at the LTF entry moment | Cancel that LTF setup |
| FB-6 | "A− within FIRST eligible 15m candle" when parent formed premarket | Literal validity candle #1 (premarket entry impossible ⇒ A− unreachable for early premarket parents) |
| FB-7 | "First target successfully broken" definition | Configurable per spec; default completed 3m close beyond target |
| FB-8 | No partial profit is defined for FB at the first target | None implemented (full position → runner) — confirm |
| FB-9 | One 15m candle breaks two eligible levels | Deepest broken level chosen; one setup per direction |
| FB-10 | Structural invalidation applies to setups, not open positions | Pre-entry only — confirm |
| VBR-1 | Must the trigger vector actually break through Daily Open? | Yes (traded through it, or prior close on other side) |
| VBR-2 | New qualifying vector while a flat parent is active | Replaces/restarts the parent; ignored while position open or in re-entry states |
| VBR-3 | Pattern B reclaim close fails the EMA condition | No entry, structure cleared (no wait) |
| VBR-4 | Re-entry scan duration | Only the single FOLLOWING 15m candle |
| VBR-5 | "Most recent confirmed 1m higher low / swing low" definition | Strength-2 fractal swing (bars each side), configurable |
| VBR-6 | 90% exit with 1 contract (floor = 0) | The contract becomes the runner |
| VBR-7 | Stop hit after the 90% was already taken | Trade complete; re-entry NOT armed (re-entry only after full stop-out) |
| VBR-8 | No directional target level remains | Trail mode activates immediately |
| VBR-9 | Target "reached" | Intrabar touch of the level price (1m high/low) |
| SH-1 | TR source library not attached: day boundary, week boundary, psy calculation | Midnight ET day / Sunday 18:00 ET week / first 8 hours psy window — all configurable |
| SH-2 | Simultaneous FB+VBR positions | Blocked (second entry skipped + logged); NT netting warning in README |
| SH-3 | Account balance source | Live: account cash value; backtest: parameter + compounded realized PnL |
| SH-4 | Position still open at session end (no rule in spec) | NT exit-on-session-close ON (configurable OFF) |
| SH-5 | Window boundary inclusivity | Signal close ≥ 9:30:00 and ≤ 11:30:00; pattern candles open ≥ 9:30:00 |
| SH-6 | Bar-time timezone | Converted machine-local → US-Eastern; toggle if NT is already set to ET |

## Outstanding caveats (not claiming finished until acknowledged)

1. **Psy levels are a best-effort port** — the Traders Reality source library referenced by the
   spec ("supplied source", getdayOpen, calcPsyLevels) was not attached to this task. Vector
   math and pivot/M-level formulas are fully specified in the spec itself and implemented
   verbatim, but Psy-Hi/Psy-Lo and the exact day/week boundary semantics need the TR source
   (or your confirmation of the defaults) for an exact port.
2. **This code has not been compiled inside NinjaTrader 8** — no NT8 runtime exists in this
   environment. It is written strictly against the documented NT8 managed-approach API in
   conservative C#; compile with F5 in the NinjaScript editor and report any errors.
3. **Session-close attribution edge case**: if `AllowSimultaneousStrategies=true` and both
   engines hold positions into the session-close flatten with partial fills, per-engine P&L
   attribution of that flatten can be approximate. Default config (false) avoids it entirely.
4. All FB-*/VBR-*/SH-* defaults above are choices you should confirm.
