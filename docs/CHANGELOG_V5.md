# CHANGELOG — V5 Correction Pass

Controlling spec: `two_automated_strategies_for_claude_v5_MNQ_ONLY.md` (supersedes V4).
Correction directives: `FABLE_5_CORRECTION_PROMPT_MNQ.md`.
Supplied Traders Reality source: the TR **library** (`Traders_Reality_Lib`, Pine v5) and the
TR **main indicator** (`TR_MAIN`) — both ported. The first two uploads were byte-identical
copies of the library; `TR_MAIN` was supplied afterwards and closed the two items that had
been documented as unverified equivalents. See the "TR_MAIN follow-up pass" section below.

Existing architecture preserved — no rebuild. Every change below is a modification of the
V4 implementation.

## Every file/function changed

### `src/MnqTwoStrategiesShared.cs`
| Function/Section | Change |
|---|---|
| `FbGradeBasis` enum | Re-documented: `FirstTradableCandle` is now the V5-mandated default (Fix 7); `ValidityCandleNumber` demoted to legacy research |
| `TargetReachedMode` enum | **New** — VBR "target reached" definition kept configurable (unresolved item 2) |
| `PsyLevelType` enum | **New** — TR `calcPsyLevels` psyType; default **Forex** (user-confirmed for MNQ; TR `overridePsyType` selector) |
| `KeyLevelEngine` header + fields | Rewritten for the faithful TR port; removed the generic "first 8 hours of week" psy fields; `DayStartMinutesEt` default now 1080 (18:00 ET = CME exchange-day open = TR `time('D')` boundary for MNQ; 0 reproduces the library's literal "exchange midnight" comment) |
| `KeyLevelEngine.CalcSydneyDst` | **New** — direct port of TR `calcDst()` Sydney-DST branch |
| `KeyLevelEngine.IsInPsySession` | **New** — port of `calcPsyLevels` session windows: forex `'0000-0800:2'` GMT (Monday 00:00–08:00 GMT); crypto `'2200-0600:1'` GMT+1/GMT by Sydney DST |
| `KeyLevelEngine.OnOneMinuteBar` | Signature gains `utcOpen`; psy hi/lo now initialize on session entry, extend by max/min in-session, hold last value out-of-session (exact `calcPsyLevels` behavior); old week-anchored psy accumulation deleted |
| `KeyLevelEngine.GetSortedTargets` | Fix 8: takes a `normalizeToTick` delegate instead of a tolerance; every level price and the reference are tick-normalized first; merging happens ONLY on exact equality of normalized prices |

### `src/FakeBreakoutEngine.cs`
| Function/Section | Change |
|---|---|
| `FbConfig.RequirePriorCloseInside` | Fix 2: default **false**, documented as LEGACY research (exact-spec mode = off) |
| `FbConfig.GradeBasis` | Fix 7: default **FirstTradableCandle** |
| `ProcessLtf` break-candle filter | Fix 1: short-side break candle now accepts **BLUE_VECTOR** in addition to GREEN_VECTOR/REGULAR (1m and 3m — the same function serves both series) |
| `ProcessLtf` reclaim-vector rules | Fix 1: new BLUE-first path — reclaim valid only if REGULAR or RED_VECTOR (VIOLET explicitly NOT valid on this path); GREEN-first path behavior preserved (any reclaim close below); REGULAR-first path unchanged (RED/VIOLET) |
| `OnEntryExecution` | Passes `host.RoundToTick` into `GetSortedTargets` (Fix 8 signature) |

EMA wait/cancel behavior and the structure-wick stop needed **no change** for the BLUE path:
they were already vector-agnostic once a structure exists, which is exactly what V5 §10
prescribes (wait for first close below EMA9; cancel on completed close above the fake-break
high; stop at the structure HIGH/WICK).

### `src/VectorBreakRetestEngine.cs`
| Function/Section | Change |
|---|---|
| `VbrConfig.RequireCrossThrough` | Fix 3: default **false**, LEGACY research |
| `VbrConfig.RetriggerReplacesActiveSetup` | Fix 5: default **false**, LEGACY research — an active parent keeps its ORIGINAL trigger and ORIGINAL 4-candle clock |
| `VbrConfig.TargetReached` | **New** config (unresolved item 2), default `IntrabarTouch` |
| `ManagePosition` chain loop | "Reached" test now dispatches on `TargetReached` mode |
| `AdvanceTargetChain` | Passes `host.RoundToTick` into `GetSortedTargets` (Fix 8) |

### `src/MnqTwoStrategies.cs`
| Function/Section | Change |
|---|---|
| Parameters | `DayStartMinutesEt` default 1080; `PsyWindowHours` **removed**, replaced by `PsyLevelTypeParam`; `FbRequirePriorCloseInside`/`VbrRequireCrossThrough`/`VbrRetriggerReplacesSetup` defaults false + relabeled "LEGACY research (keep FALSE)"; `FbGradeBasisParam` default FirstTradableCandle; `VbrTargetReachedModeParam` **new**; `PrintLevelsDiagnosticDate` **new**; `ExitOnSessionCloseEnabled` default **false** + relabeled "PLATFORM flatten (NOT a strategy rule)" |
| `OnStateChange/SetDefaults` | `IsExitOnSessionClose = false` (Fix 6); all defaults above |
| `OnStateChange/DataLoaded` | Wires `PsyType` and `TargetReached` into the engines |
| `OnBarUpdate` (1m branch) | Computes `utcOpen` and passes it to `levels.OnOneMinuteBar`; calls `MaybePrintLevelsDiagnostic` |
| `ToUtc` | **New** helper (psy sessions are GMT-defined in the TR source) |
| `MaybePrintLevelsDiagnostic` | **New** — Fix 4 requirement: prints all 18 target levels (plus internal R2/S3) at the first 1m close ≥ 9:30 ET on a configured historical date for TradingView comparison |

### `tests/` (new)
`MockHost.cs`, `Tests.cs` — deterministic scenario tests compiled against the actual engine
sources (the engines have no NinjaTrader dependency by design). 41 assertions, all passing;
see `docs/COMPLIANCE_AUDIT.md` §Corrections for the mapping.

## Previous vs corrected behavior (with tests)

| # | Previous behavior (V4 build) | Corrected behavior (V5) | Code file/function | Test performed |
|---|---|---|---|---|
| 1 | FB LTF short break candle: GREEN or REGULAR only; a BLUE break candle was silently ignored | BLUE_VECTOR is a valid short break candle; reclaim valid iff REGULAR or RED_VECTOR (VIOLET rejected on this path); same EMA wait/cancel and structure-wick stop; applies identically to 1m and 3m; 15m parent initiators unchanged (no BLUE) | `FakeBreakoutEngine.ProcessLtf` (break + reclaim filters) | `BLUE->REGULAR = VALID` ✅, `BLUE->RED = VALID` ✅, `BLUE->VIOLET = NO entry` ✅ (`tests/Tests.cs`) |
| 2 | FB parent trigger required previous 15m close inside the level (default true) | Trigger = trades beyond + closes beyond + allowed candle type, nothing else; legacy parameter defaults FALSE | `FbConfig.RequirePriorCloseInside`, `FakeBreakoutEngine.TryTrigger` | Trigger fires with prior close already beyond the level ✅ |
| 3 | VBR trigger required a cross-through of Daily Open (default true) | GREEN/RED vector close beyond Daily Open is sufficient; legacy parameter defaults FALSE | `VbrConfig.RequireCrossThrough`, `VectorBreakRetestEngine.OnFifteenMinuteBar` | Trigger fires with low > DO and prior close above DO ✅ |
| 4 | Daily Open at midnight ET; Psy = high/low of first 8 hours of week (generic) | Daily Open = open of the 18:00-ET exchange day (TR `time('D')` boundary for MNQ, compat param for literal midnight); Psy = ported `calcPsyLevels` GMT sessions + ported `calcDst`; YDay/LWeek non-repainting prev-completed aggregates (later CONFIRMED against TR_MAIN) | `KeyLevelEngine` (day roll, `IsInPsySession`, `CalcSydneyDst`), host `ToUtc`/`MaybePrintLevelsDiagnostic` | Daily-Open stability, YDay/LWeek, psy in/out-of-session accumulation, calcDst flags, diagnostic print ✅ |
| 5 | A new qualifying vector replaced/restarted an active flat VBR parent (default true) | Original trigger + original 4-candle clock preserved; legacy parameter defaults FALSE | `VbrConfig.RetriggerReplacesActiveSetup`, `OnFifteenMinuteBar` | Second qualifying vector ignored; expiry exactly 4 candles after ORIGINAL trigger ✅ |
| 6 | NT exit-on-session-close defaulted ON | Defaults OFF; parameter relabeled as platform behavior, not a strategy rule; positions entered before 11:30 run under stop/target/trail/runner | `MnqTwoStrategies` SetDefaults/param | Default inspection (no strategy-side flatten path exists other than the platform option) |
| 7 | A- = literal validity candle #1, so premarket parents could never grade A- | A- = entry in FIRST candle in which a fresh LTF entry is actually eligible (≥ 9:30); later entries B+ | `FbConfig.GradeBasis` default, `FakeBreakoutEngine.TryEnter`/`ProcessLtf` FirstTradable tracking | Premarket parent, entry 9:30–9:45 → A- @ 26% (118 lots on $10k/11pt); later entry → B+ @ 10% (45 lots) ✅ |
| 8 | Equal-price merge used a ±1-tick tolerance band | Prices tick-normalized first; merge ONLY on exact equality of normalized prices | `KeyLevelEngine.GetSortedTargets` | Coincident levels merge keeping 13 names; adjacent ticks 100.25/100.50 do NOT merge; R2 never selectable; strict ordering ✅ |

---

## TR_MAIN follow-up pass (main indicator supplied)

The Traders Reality **main indicator** was supplied after the corrections above. It resolved
both remaining caveats and exposed one real defect in the psy port.

### Confirmed correct — no code change required

| Item | TR_MAIN evidence | Implementation |
|---|---|---|
| YDay Hi / YDay Lo | L309-310 `dayHigh/dayLow = f_security(tickerid,'D',high/low,false)`, plotted with titles `"YDay Hi"/"YDay Lo"` (L348-351). The `_repaint=false` wrapper (L252-253) returns the PREVIOUS COMPLETED daily value on both the historical and realtime branch | `KeyLevelEngine.prevDay.H/L` — previous completed exchange day, non-repainting ✅ |
| LWeek Hi / LWeek Lo | L337-338 `weekHigh/weekLow = f_security(tickerid,'W',...)`, titles `"LWeek Hi"/"LWeek Lo"` (L353-356) | `KeyLevelEngine.prevWeek.H/L` ✅ |
| Pivots | L316-324 computed from the same previous-completed-day values | `PP/R1/S1/R2/S2/R3/S3` getters ✅ |
| M-levels | L569-574 `m0C=(pivS2+pivS3)/2 … m5C=(pivR2+pivR3)/2` | `M0..M5` getters ✅ (test asserts the identities) |
| Daily Open | L677 `dailyOpen = trLib.getdayOpen()` | 18:00-ET exchange-day open ✅ |
| R2/S3 not selectable targets | R2/S3 exist as pivot plots in TR but the V5 spec excludes them from the target list | internal-only ✅ |

### Defect found and fixed

| Previous behavior | Corrected behavior | Code file/function | Test performed |
|---|---|---|---|
| Only one psy path implemented as usable | Both TR paths ported and selectable. TR_MAIN's *automatic* derivation (L243) would give `crypto` for a futures symbol, but L241-242 expose `overridePsyType` + a manual selector; **the user runs the FOREX path for MNQ**, which is the default. Forex window = Mon 00:00-08:00 GMT = Sun 20:00 → Mon 04:00 ET, fully inside CME hours year-round, no DST dependency | `KeyLevelEngine.PsyType`, `MnqTwoStrategies.PsyLevelTypeParam` | forex-path accumulation + boundary exclusions ✅; crypto path also covered ✅ |
| Crypto session read as **Saturday** 22:00 → Sunday 06:00 | Pine session days are 1=Sunday and name the day the session STARTS, so `'2200-0600:1'` = **Sunday 22:00 → Monday 06:00** (GMT+1 while Sydney DST, else GMT). Decisive check: the Saturday window lies entirely inside the CME weekend closure, so it would leave Psy Hi/Lo NaN forever; the Sunday window starts exactly at the Sunday 18:00 ET futures reopen | `KeyLevelEngine.IsInPsySession` | Saturday bar excluded ✅; crypto window non-empty for MNQ ✅; forex path unaffected ✅ |
| (new) 4H-grid session evaluation | The source tests membership via `time('240', session, gmt)`. The anchor cannot be derived from the source, and anchoring to the exchange-day open makes the source's own forex branch fall permanently out of session — so the literal session window is the default and the grid is a clearly-named compat parameter, default OFF | `KeyLevelEngine.PsyUse4HourGrid`, `PsyUse4HourGridParam` | compat mode agrees with the literal window on the aligned MNQ case ✅ |
| Doc claims | "documented equivalent, not a line-for-line port" caveats replaced with CONFIRMED rows citing TR_MAIN line numbers | `docs/COMPLIANCE_AUDIT.md` §5 | — |

Test count after this pass: **41 assertions, all passing**.
