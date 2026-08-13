# SPEC ANALYSIS — Two Automated MNQ-Only Strategies (NinjaTrader 8)

> **HISTORICAL (V4).** This analysis was written against the V4 spec. The controlling
> specification is now **V5** (`two_automated_strategies_for_claude_v5_MNQ_ONLY.md`);
> see `docs/CHANGELOG_V5.md` for the corrections and `docs/COMPLIANCE_AUDIT.md` for the
> current V5 audit. Notable V5 changes: BLUE_VECTOR 1m/3m FB short path added; no
> prior-close/cross conditions on either trigger; A- grading uses the first actually
> eligible entry candle; TR library source supplied and ported; no session-close flatten
> default; tick-exact target merging.

Source of truth: `two_automated_strategies_for_claude_v4_MNQ_ONLY_3.md` (the master specification).
This document is the pre-implementation deliverable requested by the user:

- A. Understanding of FAKE_BREAKOUT
- B. Understanding of VECTOR_BREAK_RETEST
- C. Shared Traders Reality / key-level components
- D. Ambiguities that are not deterministic enough to code exactly (with the configurable
     default chosen for each — nothing was silently invented)
- E. Proposed NinjaTrader multi-timeframe architecture + anti-repaint design
- F. Rule-by-rule implementation checklist

---

## A. FAKE_BREAKOUT — understanding

`StrategyId = FAKE_BREAKOUT`. A 15-minute *failed breakout* (stop-run) reversal strategy at
yesterday's / last week's extremes, entered on a 1m/3m fake-break + EMA(9) confirmation.

1. **Trigger levels (only):** YDAY_HIGH, YDAY_LOW, LWEEK_HIGH, LWEEK_LOW. DAILY_OPEN never
   starts a Fake Breakout setup.
2. **Short parent setup:** a COMPLETED 15m candle trades above an eligible level AND closes
   above it (wick alone is not enough). Initiating candle must be GREEN_VECTOR or REGULAR.
   Track `StructuralHigh` = max of the initiating candle high and every subsequent completed
   15m high. Freeze `StructuralHigh` when a completed 15m candle closes back BELOW the level.
   Vector participation for the reclaim: GREEN breakout → reclaim may be REGULAR / RED / VIOLET;
   REGULAR breakout → reclaim MUST be RED or VIOLET; REGULAR + REGULAR = invalid.
3. **Long parent setup:** mirror below the level. Initiating candle RED_VECTOR or REGULAR
   (VIOLET explicitly NOT allowed as initiator). Freeze `StructuralLow` on a completed 15m
   close back ABOVE the level. RED breakout → reclaim REGULAR or GREEN; REGULAR breakout →
   reclaim MUST be GREEN; REGULAR + REGULAR = invalid.
4. **Validity:** 4 completed 15m candles after the breakout candle, +2 extension if no entry,
   max 6; 11:30 ET entry cutoff overrides; premarket 15m candles count toward the clock but
   premarket lower-timeframe signals never carry forward.
5. **15m EMA(9) confluence:** before the actual lower-TF entry, the most recent completed 15m
   close must be below (short) / above (long) the 15m EMA(9). No fresh crossover required.
6. **Lower-TF entry (1m and 3m monitored independently, first valid entry wins):**
   - LONG: RED_VECTOR or REGULAR closes below/through the ActiveKeyLevel, then a GREEN_VECTOR
     or BLUE_VECTOR closes back above it (REGULAR reclaim is NOT valid). If the reclaim close
     is above that timeframe's EMA9 → enter; otherwise wait and enter on the FIRST completed
     candle closing above EMA9; while waiting, a completed close below the fake-break
     structure low cancels that lower-TF setup. Initial stop = structure LOW/WICK.
   - SHORT: GREEN_VECTOR closes above/through the level then price closes back below
     (any candle type for the reclaim in the GREEN-first case); REGULAR-first breakout
     requires RED or VIOLET reclaim; REGULAR + REGULAR invalid. EMA wait mirrored; cancel if
     a completed candle closes above the fake-break high before EMA confirmation.
     Initial stop = structure HIGH/WICK.
   - A failed lower-TF setup cancels only itself; scanning continues while the parent lives.
     Once a trade is entered, no further entries for that parent setup.
7. **Structural invalidation (after freeze, pre-entry):** completed 1m OR 3m close beyond the
   frozen structural extreme cancels the ENTIRE parent setup. Wicks do not invalidate.
8. **Grade / risk:** A- (26%) if the valid entry occurs within the FIRST eligible 15m validity
   candle; B+ (10%) in candles 2–4 or the +2 extension.
9. **Profit management:** nearest directional level from the shared 18-level engine = first
   target. Once the first target is "successfully broken" (break definition kept configurable
   per the spec), activate the 3m EMA(9) runner: LONG exits on a completed 3m close below
   3m EMA9, SHORT on a completed 3m close above it. No partial-profit rule is defined for
   Fake Breakout, so none was added. Stop stays at the initial structure price (no
   breakeven/trailing-stop rule is defined, so none was added).

## B. VECTOR_BREAK_RETEST — understanding

`StrategyId = VECTOR_BREAK_RETEST`. A 15m vector-candle break of the Daily Open, entered on a
1m retest of the Daily Open. 15m + 1m only. Every valid trade is A+ = 50% account risk.

1. **Trigger level (only):** DAILY_OPEN (Traders Reality day-open semantics).
2. **Long parent:** completed 15m GREEN_VECTOR closes ABOVE Daily Open. **Short parent:**
   completed 15m RED_VECTOR closes BELOW Daily Open. Exactly the NEXT 4 completed 15m candles
   are valid for a 1m entry. NO +2 extension. Premarket 15m candles count; premarket 1m
   signals never carry forward.
3. **Long Pattern A (wick retest):** during a valid 15m candle, any 1m candle trades/wicks
   into Daily Open and closes back above it; if that close is already above 1m EMA9 → enter
   on that close. Stop = LOW/WICK of that retest candle.
4. **Long Pattern B (close-through & reclaim):** completed 1m close BELOW Daily Open →
   completed 1m close BACK ABOVE Daily Open with the bullish EMA condition (reclaim close
   above 1m EMA9 / price already above it) → enter. Stop = LOW of the 1m structure created
   below Daily Open.
5. **Short Patterns A/B:** exact mirrors above/below Daily Open.
6. **Re-entry after stop-out:** the stop-out does NOT kill the parent and does NOT restart
   the 4-candle clock. The SAME 15m candle that contained the stopped 1m attempt must
   wick into/through Daily Open and ultimately close back on the trade side of it
   (above for long, below for short); if so, during the FOLLOWING 15m candle scan for a
   NEW fresh 1m setup. All re-entries stay inside the original 4-candle window and the
   9:30–11:30 ET window.
7. **Profit management (50-point chaining):** next directional level from the shared
   18-level engine, measured from the current reference price (entry initially).
   Gap ≤ 50 index points → hold for that level and IGNORE adverse 1m EMA9 closes.
   When reached → that target price becomes the new reference; repeat while gaps stay ≤ 50.
   When the next gap is > 50 points → activate 1m EMA(9) trail: completed 1m close through
   EMA9 against the trade → take profit on 90%. Final 10% runner is held until a completed
   1m close through the most recent confirmed 1m supporting swing (higher low for longs /
   lower high for shorts). Wicks never count anywhere.

## C. Shared Traders Reality / key-level components (read-only utilities)

- **Vector classification** (per timeframe, completed candles only):
  `AverageVolume` = mean volume of previous 10 completed candles; `VolumeSpread` =
  volume × (high − low); `HighestVolumeSpread` = max VolumeSpread of previous 10 candles.
  Climax: volume ≥ 2×avg OR spread ≥ highest-spread → GREEN (close>open) / RED (else).
  Medium: volume ≥ 1.5×avg → BLUE / VIOLET. Else REGULAR_BULLISH / REGULAR_BEARISH.
  Close == Open follows the bearish branch. Climax has priority over medium.
- **Key levels:** Daily Open (open at start of new exchange day), YDay Hi/Lo (previous
  completed day), LWeek Hi/Lo (previous completed week), Traders Reality pivots
  PP/R1/S1/R2/S2/R3/S3 and M0–M5 from previous day H/L/C (R2 and S3 computed internally but
  NOT selectable targets), Psy-Hi/Psy-Lo (weekly psychological range).
- **Shared 18-level take-profit engine:** M0, M1, M2, M3, M4, M5, PP, DAILY_OPEN, YDAY_HIGH,
  YDAY_LOW, LWEEK_HIGH, LWEEK_LOW, R1, R3, S1, S2, PSY_HIGH, PSY_LOW — each individually
  selectable. `GetSortedTargets(direction, referencePrice)`: LONG → all valid levels strictly
  above the reference sorted ascending; SHORT → strictly below sorted descending; equal-price
  levels merge into one target event keeping all names; NaN levels ignored. Targets only —
  never expands either strategy's trigger universe.
- **Position sizing (MNQ only, $2/pt):** `RiskDollars = Balance × RiskPercent`;
  `RiskPerContract = StopDistancePoints × $2`; `Contracts = floor(RiskDollars/RiskPerContract)`.
  A+ 50%, A- 26%, B+ 10%. Never NQ's $20/pt.
- **Session/time helpers, logging, MFE/MAE/R tracking.**

No active setup object is shared. Each engine owns its own state machine, counters, orders
(`FB_LONG`/`FB_SHORT`/`VBR_LONG`/`VBR_SHORT` + strategy-prefixed exits), grading, sizing,
trade IDs, and log records.

## D. Ambiguities (flagged — each is a configurable parameter, none silently invented)

See the numbered list FB-1 … SH-6 in `docs/COMPLIANCE_AUDIT.md` §Ambiguities and the
chat summary. Highlights: breakout "crossing" semantics, whether the 15m reclaim must precede
lower-TF scanning, REGULAR+REGULAR reclaim consequence, grade basis for premarket parents,
first-target "break" definition (spec itself says keep configurable), VBR trigger
cross-through requirement, Pattern-B EMA-failure handling, re-entry scan duration, runner
swing definition, 1-contract 90/10 split, day/week/psy boundaries (Traders Reality source
library was NOT attached), simultaneous-position policy (spec says expose a setting),
account-balance source, and end-of-session handling.

## E. NinjaTrader architecture & anti-repaint design

- Single NT8 strategy `MnqTwoStrategies` hosting two fully independent engine classes
  (`FakeBreakoutEngine`, `VectorBreakRetestEngine`) plus read-only shared utilities.
- **Series:** `AddDataSeries(Minute,1)` → BarsInProgress 1, `AddDataSeries(Minute,3)` → BIP 2,
  `AddDataSeries(Minute,15)` → BIP 3. BIP 0 (the chart series) is never used for logic, so the
  chart the strategy is applied to cannot contaminate signals. `OnBarUpdate` dispatches
  strictly on `BarsInProgress`; each engine receives immutable `BarSnap` snapshots (OHLCV,
  vector, EMA9, ET open/close times) built only inside the matching BIP branch — 15m logic can
  never read 1m data and vice versa.
- **Ordering at shared boundaries:** at e.g. 9:45 the 1m bar processes before the 3m and 15m
  bars (series processed in the order added), so a 1m signal in validity candle #4 is
  evaluated before the 15m candle-count rolls — matching the spec's candle-numbering examples.
- **No look-ahead / no repainting:** `Calculate = Calculate.OnBarClose` everywhere; every
  vector, EMA, reclaim, structure break, target-break, and trail decision uses the just-closed
  candle of its own series. Vector math uses volumes/ranges of bars [1]..[10] (previous 10
  completed) exactly as specified. EMA values are cached per-series inside that series' own
  BIP branch, never read cross-series mid-bar. Intrabar data is used ONLY where the spec
  demands price *touching* something (stop orders held server/engine-side as real stop orders,
  target "reached" checks on completed 1m high/low). Entries are market orders submitted at
  signal-candle close (filled at next tick / next bar open in backtest — standard NT8
  OnBarClose semantics).
- **Key levels** are aggregated from the 1m series with configurable exchange-day /
  week / psy-window boundaries (defaults documented), so historical backtests and live runs
  compute identical values from the same data.
- **Orders:** managed approach, `EntriesPerDirection = 1` with `EntryHandling.UniqueEntries`,
  unique signal names per strategy+direction; structure stops as live-until-cancelled
  stop-market orders tied to their entry signal; partial exits (VBR 90/10) as scoped
  market exits with the stop quantity re-synced on fill.
- **MNQ-only enforcement:** the strategy refuses to arm unless the instrument's master
  instrument is MNQ; $2/pt is a hard constant in the sizer per the spec.

## F. Rule-by-rule implementation checklist

The full `Specification Rule | Implemented? | Function/Code Section | Notes` table lives in
`docs/COMPLIANCE_AUDIT.md` (post-implementation audit). The pre-implementation checklist used
to drive the code is the same row set; every spec line was mapped to a code location before
being marked complete.
