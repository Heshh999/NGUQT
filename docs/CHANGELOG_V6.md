# CHANGELOG — V6 Final Rule-Lock Pass

Controlling spec: `two_automated_strategies_for_claude_v6_MNQ_ONLY_FINAL.md` (supersedes V5).
Directives: `CLAUDE_FINAL_V6_CORRECTION_PROMPT.md`.

Existing architecture preserved — no rebuild. Code already matching V6 was left alone;
only V4/V5-era behavior was modified. Deterministic assertions: **102, all passing**
(93 for the U1-U9 locks + 9 for the FINAL FAKE BREAKOUT EMA RULE follow-up below).

## Rule | Previous behavior | Corrected behavior | Code location | Test proving it

| Rule | Previous behavior | Corrected behavior | Code location | Test proving it |
|---|---|---|---|---|
| **U1** FB first target broken | Default `ThreeMinuteCloseBeyond` (completed 3m close) | Completed **1m close** beyond the first target; a wick/touch does not count; then the 3m EMA(9) runner | `FbConfig.TargetBreakMode` default `OneMinuteCloseBeyond`; `FakeBreakoutEngine.ManagePosition`/`ActivateRunner` | `TestU1FbTargetBreak` — wick does NOT activate ✅, 3m close does NOT activate ✅, 1m close DOES ✅, runner exits on 3m close through EMA ✅ |
| **U2** VBR target reached | Already wick/touch (`IntrabarTouch`) — kept | Unchanged; enum re-documented as V6-locked; ≤50-pt chaining and >50-pt trail unchanged | `VbrConfig.TargetReached`; `VectorBreakRetestEngine.ManagePosition` chain loop, `AdvanceTargetChain` | `TestU2TargetChaining` (touch reaches, adverse EMA ignored ≤50) ✅; `TestU2U3U8ProfitManagement` (>50 → trail) ✅ |
| **U3** VBR final 10% structure | `SwingTracker`, strength-2 fractal confirmed k bars later | **`SupportingStructureTracker`**: ONE completed 1m candle making a higher low (long) / lower high (short) sets the reference; exit only when a **later** completed 1m candle closes through it; wicks never count | `SupportingStructureTracker` (new, replaces `SwingTracker`); runner block in `ManagePosition` | `TestU2U3U8ProfitManagement` — wick through structure does NOT exit ✅, later close does ✅ |
| **U4** Invalid 15m FB reclaim | Configurable, already defaulted to "keep waiting" | Unchanged behavior, re-documented as V6-locked; flag relabelled LEGACY | `FbConfig.InvalidReclaimCancelsSetup` (false); `FakeBreakoutEngine.TryReclaim` | `TestU4U5FbReclaim` — reclaim ignored, parent NOT cancelled, later entry still fires ✅ |
| **U5** FB LTF scan before reclaim | `Require15mReclaimBeforeLtfEntry = **true**` — 1m/3m scanning was gated behind a completed 15m reclaim/freeze | **false**: 1m/3m engines scan as soon as a valid 15m parent exists | `FbConfig.Require15mReclaimBeforeLtfEntry` (false); `ProcessLtf` `mayScan` gate | `TestU4U5FbReclaim` — entry with no completed 15m reclaim at all ✅ |
| **U6** VBR Pattern B EMA | `PatternBWaitForEma = **false**` — a reclaim failing the EMA discarded the structure | **true**: entry requires a completed 1m close beyond **BOTH** Daily Open and 1m EMA9; reclaim-then-wait is kept alive; a candle beyond EMA but on the wrong side of DO is not an entry; a close back through DO resumes the structure leg | `VbrConfig.PatternBWaitForEma`; Pattern B + `waitingEmaB` blocks in `OnOneMinuteBar` | `TestU6PatternBWait` (long) ✅ and `TestU6PatternBWaitShort` (mirror) ✅ — 4 assertions each |
| **U7** VBR re-entry window | `ReentryScanOnlyFollowingCandle = **true**` — one following candle then the setup died | **Rolling re-qualification**: stop-out candle needs wick-into-DO + correct-side close to authorize the next candle; thereafter a correct-side close alone rolls permission forward one candle at a time, inside the ORIGINAL 4-candle clock; a wrong-side close ends it; clock never restarts/extends | `VbrConfig.ReentryScanOnlyFollowingCandle` (false); rolling block in `OnFifteenMinuteBar`; scan gate in `OnOneMinuteBar` | `TestU7RollingReentry` (#2→#3→#4, entry in #4, no #5) ✅; `TestU7WrongSideBreaksRolling` ✅ |
| **U8** VBR 1-contract 90/10 | `SingleContractBecomesRunner = **true**` — the lone contract became the runner | **false**: the 1m EMA(9) profit signal exits the ENTIRE contract; no runner for a 1-contract position | `VbrConfig.SingleContractBecomesRunner`; trail block in `ManagePosition` | `TestU8SingleContract` — sized to 1, full exit, no runner ✅ |
| **U9** Simultaneous FB + VBR | `AllowSimultaneousStrategies=false` **blocked** the second strategy's entry | **Strategy handoff**: flatten the open strategy → wait for confirmed flat → then enter the new one. Symmetric FB↔VBR. The replacement order is never submitted before the flat confirmation | **New** `HandoffCoordinator` (shared); `FakeBreakoutEngine.FlattenForHandoff`, `VectorBreakRetestEngine.FlattenForHandoff`; host `EnterPosition`/`SubmitEntryOrder`/`OnPositionUpdate` | `TestU9HandoffFbToVbr` + `TestU9HandoffVbrToFb` — 6 + 5 assertions incl. strict ordering `EXIT → FLAT_CONFIRMED → ENTRY` ✅ |
| **Psy type** | Forex (set in the previous pass) | Unchanged — Forex remains the default per V6 | `KeyLevelEngine.PsyType` | `TestTradersRealityPorts` forex-path assertions ✅ |

## Every file/function changed

### `src/MnqTwoStrategiesShared.cs`
- `FbTargetBreakMode` / `TargetReachedMode` — re-documented; V6-locked members identified.
- **`HandoffCoordinator` (new class)** — owns the U9 exit-first-then-entry sequencing:
  `RequestEntry` submits immediately when the account is free, otherwise parks the order
  and flattens the other engine; `NotifyFlat` is the only path that releases a parked
  entry. Lives in shared code so the NT host and the test host run identical logic.

### `src/FakeBreakoutEngine.cs`
- `FbConfig`: `TargetBreakMode` → `OneMinuteCloseBeyond` (U1); `Require15mReclaimBeforeLtfEntry`
  → `false` (U5); `InvalidReclaimCancelsSetup` re-documented as U4-locked.
- `FbSlot.HandoffSignal` (new) — `FB_HANDOFF_L` / `FB_HANDOFF_S`.
- `FlattenForHandoff()` (new) — U9 flatten of this engine's open position.
- `OnExitExecution` — recognizes the handoff leg (`HANDOFF_FLATTEN` exit reason).
- `TryEnter` — the other strategy's open position no longer blocks entry (U9).

### `src/VectorBreakRetestEngine.cs`
- `VbrConfig`: `PatternBWaitForEma` → `true` (U6); `ReentryScanOnlyFollowingCandle` → `false`
  (U7); `SingleContractBecomesRunner` → `false` (U8); `RunnerSwingStrength` **removed** (U3).
- `SwingTracker` **replaced** by `SupportingStructureTracker` (U3) — one-candle higher-low /
  lower-high reference with bar indices so the establishing candle can't also break it.
- Pattern B (`OnOneMinuteBar`) — rewritten for U6 wait semantics.
- Rolling re-entry block (`OnFifteenMinuteBar`) — rewritten for U7.
- Trail block (`ManagePosition`) — U8 full-contract exit; runner block — U3 structure rule.
- `FlattenForHandoff()` (new) + `HANDOFF_FLATTEN` exit leg (U9); a handoff flatten is not a
  stop-out, so it never arms the re-entry rule.
- `TryEnter` — the other strategy's open position no longer blocks entry (U9).

### `src/MnqTwoStrategies.cs` (NT8 host)
- `handoff` field + construction; `EnterPosition` routes through the coordinator;
  `SubmitEntryOrder` / `StrategyHasPosition` / `FlattenStrategy` helpers (new).
- **`OnPositionUpdate` (new)** — the only place a parked handoff entry is released, on
  `MarketPosition.Flat`.
- `CanOpenPosition` — now only the instrument/enabled gate (U9 replaces blocking).
- Parameters: `AllowSimultaneousStrategies` and `VbrRunnerSwingStrength` **removed**;
  V6-locked flags relabelled `LEGACY … (V6 Ux: keep FALSE/TRUE)`; defaults updated for
  U1/U5/U6/U7/U8.

### `tests/`
- `MockHost` — `WireHandoff()`, `ConfirmFlat()`, and an ordered `Sequence` log so handoff
  ordering is provable; entries route through the same shared coordinator.
- `Tests.cs` — 11 new V6 scenarios (U1, U4/U5, U6 long, U6 short, U2/U3/U8, U2 chaining,
  U8, U7 rolling, U7 wrong-side, U9 FB→VBR, U9 VBR→FB).

## Test scenario corrections made during this pass (engine was right, tests were wrong)

Three initial V6 test scenarios failed against correct engine behavior and were fixed:
- **Target levels.** I had assumed the first target below a 20095 short was `YDAY_LOW`
  (19900). The 18-level engine correctly returns **M3 = (PP+R1)/2 = 20050**, which sits
  between entry and the YDay levels. Same for the long side. Scenarios were rebuilt around
  the real target, and a `FarTargetLevels()` book (degenerate previous day) was added so the
  >50-point trail case can be exercised deliberately.
- **Contract sizing.** The U8 scenario used a balance that floored to 0 contracts; corrected
  to $200 / 40-pt stop → exactly 1 contract.
- **Clock assertion.** "Clock never restarts" was asserted while a position was open, where
  the clock legitimately governs entries only; rebuilt as a no-entry roll to #4 that must
  expire rather than create a #5.

---

## Follow-up: FINAL FAKE BREAKOUT EMA RULE

The 15-minute EMA(9) is **not** an entry gate for Fake Breakout. It must never cancel, delay,
block or invalidate an otherwise valid 1m/3m entry. Only the **same-timeframe** EMA(9)
controls the entry. This supersedes the older "15m EMA confluence before LTF entry" rule.

| Rule | Previous behavior | Corrected behavior | Code location | Test proving it |
|---|---|---|---|---|
| 15m EMA(9) role | `ConfluenceFailCancelsLtfSetup = true` — if the most recent completed 15m close was on the wrong side of the 15m EMA(9), the qualifying 1m/3m setup was **cancelled** at the entry moment | 15m EMA is **informational/context only**. `TryEnter` no longer gates on it; the value is logged as `15mClose / 15mEma9 / 15mConfluence` on the entry record. Replaced by LEGACY flag `Require15mEmaConfluence` (default **false**) | `FbConfig.Require15mEmaConfluence`; `FakeBreakoutEngine.TryEnter`; host param `FbRequire15mEmaConfluence` | `TestFinalFbEmaRule` (9 assertions) |
| SHORT: reclaim already below same-TF EMA9 | entered only if 15m confluence also held | enters on that completed candle regardless of 15m EMA | `ProcessLtf` reclaim branch (unchanged) → `TryEnter` | "1m short already below 1m EMA9 ENTERS…", "3m short… ENTERS…" |
| LONG: reclaim already above same-TF EMA9 | as above | enters on that completed candle regardless of 15m EMA | same | "1m long… ENTERS without any 15m EMA confirmation", "3m long… ENTERS…" |
| Reclaim not yet through same-TF EMA9 | waited, but could then be cancelled by the 15m gate | keeps the LTF setup alive and enters on the first completed same-TF candle closing through EMA9, provided parent + LTF structure remain valid | `ProcessLtf` `WaitingEma` branch (unchanged) | "…WAITS instead of being cancelled", "a later same-timeframe EMA close triggers the entry" |
| 15m EMA alone cancelling a setup | possible | impossible | — | "15m EMA state alone NEVER cancels a valid lower-timeframe Fake Breakout setup" |

Unchanged and still enforced: the §9/§10 structure rule that cancels a waiting LTF setup when
a completed same-timeframe candle closes beyond the fake-break structure extreme.

**Assertion count after this pass: 102 executed, 102 passed, 0 failed.**

### Behavior surfaced by this change (spec-correct, flagged not filtered)

Removing the 15m gate revealed that a single 15m candle can start **both** FB directions at
the same level: the candle that closes back below YDAY_HIGH to reclaim for a short parent
also satisfies the §5 LONG parent trigger at that level (trades below + closes below + RED or
REGULAR initiator). Both slots are independent and both can now produce entries, where the
15m EMA confluence used to suppress the counter-direction one. This is the literal V6 reading
and no filter was added. If opposite-direction FB parents should be mutually exclusive, that
is a NEW rule — tell me and I will add it.
