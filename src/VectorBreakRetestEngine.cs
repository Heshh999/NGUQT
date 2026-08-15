// ============================================================================
// VectorBreakRetestEngine.cs
// STRATEGY 2 — VECTOR BREAK RETEST  (StrategyId = VECTOR_BREAK_RETEST)
//
// Implements the spec sections:
//   "STRATEGY 2 — VECTOR BREAK RETEST" items 1-9
//   "VECTOR_BREAK_RETEST trigger level" (DAILY_OPEN only; YDay/LWeek levels
//    must NOT start a Vector Break Retest setup)
//   "SHARED TAKE-PROFIT KEY-LEVEL ENGINE" section D (50-point chaining rule)
//   "GLOBAL ENTRY-TIME RULE" (9:30-11:30 ET; premarket 1m signals never bank)
//
// Timeframes: 15m parent trigger + 1m entry ONLY (no 3m in this strategy).
// Grade: every valid trade = A+ = 50% account risk.
// Order signal names: VBR_LONG / VBR_SHORT, exits VBR_STOP_* / VBR_TP90_* / VBR_RUN_*.
// Fully independent from FakeBreakoutEngine (spec hard separation rule).
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;

namespace NinjaTrader.NinjaScript.Strategies.MnqTwo
{
    // Spec "Suggested Vector Break Retest states"
    public enum VbrState
    {
        IDLE,
        PARENT_15M_ACTIVE_SEARCHING_1M,
        POSITION_OPEN,
        STOPPED_OUT_REENTRY_ELIGIBILITY_PENDING,
        REENTRY_SCAN
    }

    public class VbrConfig
    {
        public double RiskPctAPlus = 50.0;                // spec: A+ = 50% account risk

        // V5 correction Fix 3: the master rule is ONLY "GREEN_VECTOR closes above
        // Daily Open" / "RED_VECTOR closes below Daily Open" — no cross-through or
        // prior-close condition. LEGACY research parameter, defaults FALSE.
        public bool RequireCrossThrough = false;
        // V5 correction Fix 5: once a VBR parent is active its ORIGINAL trigger
        // and ORIGINAL 4-candle clock are preserved; a later qualifying vector
        // must NOT restart/replace/extend it. LEGACY research parameter,
        // defaults FALSE.
        public bool RetriggerReplacesActiveSetup = false;
        // V6 U2 — LOCKED: a target is REACHED on wick/touch (no close required).
        public TargetReachedMode TargetReached = TargetReachedMode.IntrabarTouch;
        // V6 U6 — LOCKED: Pattern B WAITS for the EMA instead of discarding the
        // structure. Entry requires a completed 1m close beyond BOTH Daily Open and
        // the 1m EMA(9). Must stay TRUE in exact-spec mode.
        public bool PatternBWaitForEma = true;
        // V6 U7 — LOCKED: re-entry permission rolls forward one 15m validity candle
        // at a time inside the ORIGINAL 4-candle clock (not "following candle only").
        // LEGACY research flag, must stay FALSE.
        public bool ReentryScanOnlyFollowingCandle = false;
        // V6 U8 — LOCKED: with a 1-contract position the 1m EMA(9) profit signal
        // exits the ENTIRE contract; the contract does NOT become a runner.
        // LEGACY research flag, must stay FALSE.
        public bool SingleContractBecomesRunner = false;

        public double ChainMaxDistancePoints = 50.0;      // spec §9 / section D: 50-point rule

        // FINAL RULE 1 — HARD parent candle size filter. A 15m vector candle whose
        // total High-Low range is below this many index points can NEVER create a
        // VBR parent: no validity clock, no 1m scanning. 125.00 is valid, 124.75 is not.
        public double ParentMinRangePoints = 125.0;
    }

    // V6 U3 — 1-MINUTE SUPPORTING-STRUCTURE TRACKER (final 10% runner exit).
    //
    // "Do NOT require a strength-2 or multi-bar fractal. A single completed
    //  1-minute candle may establish the current supporting swing-low / swing-high
    //  reference; do not wait for two bars on each side."
    //
    // LONG : the most recent completed 1m candle that made a HIGHER LOW than the
    //        candle before it supplies the supporting reference = that candle's LOW.
    //        The final 10% exits only when a LATER completed 1m candle CLOSES BELOW
    //        that low (a wick below does not count).
    // SHORT: mirror — most recent LOWER HIGH candle supplies its HIGH.
    //
    // Bar indices are tracked so the candle that establishes the reference can
    // never also be the candle that breaks it ("a LATER completed 1m candle").
    public class SupportingStructureTracker
    {
        private double prevHigh = double.NaN;
        private double prevLow = double.NaN;

        public double SupportLow = double.NaN;    // long: most recent higher-low candle's LOW
        public double SupportHigh = double.NaN;   // short: most recent lower-high candle's HIGH
        public int SupportLowBar = -1;
        public int SupportHighBar = -1;
        public int BarIndex = -1;

        public void Add(double high, double low)
        {
            BarIndex++;
            if (!double.IsNaN(prevLow) && low > prevLow)   // higher low established by ONE candle
            {
                SupportLow = low;
                SupportLowBar = BarIndex;
            }
            if (!double.IsNaN(prevHigh) && high < prevHigh) // lower high established by ONE candle
            {
                SupportHigh = high;
                SupportHighBar = BarIndex;
            }
            prevHigh = high;
            prevLow = low;
        }
    }

    public class VectorBreakRetestEngine
    {
        private readonly IMnqHost host;
        private readonly VbrConfig cfg;
        private int tradeSeq;

        public StrategyStats Stats = new StrategyStats();

        // ---- parent setup state (spec §2/§3) ----
        private VbrState state = VbrState.IDLE;
        private bool isLong;
        private VectorType parentVector;
        private DateTime parentTriggerEtClose;
        private double dailyOpenAtTrigger = double.NaN;   // the ONLY trigger level (spec §1)
        private int validityCount;                        // completed 15m candles since trigger
        private bool parentPremarket;

        // ---- 1m Pattern B structure (spec §5/§7) ----
        private bool structActive;
        private double structExtreme = double.NaN;        // long: lowest low below DO; short: highest high above DO
        private bool waitingEmaB;                         // only used when PatternBWaitForEma = true
        private DateTime structStartEt = DateTime.MinValue;   // when THIS local Pattern B structure began

        // ---- re-entry state (spec §8) ----
        private int reentryCount;                         // number of re-entries taken (0 = original)
        private int stopOutFormingCandleNum;              // 15m validity candle containing the stop-out
        private int reentryScanCandleNum;                 // the FOLLOWING candle in which to scan

        // ---- open trade state ----
        private string tradeId;
        private string entryPattern;                      // WICK_RETEST_A / CLOSE_RECLAIM_B
        private DateTime entryEtTime;
        private double intendedEntry;
        private double entryAvg;
        private int qtyTotal;
        private int qtyFilled;
        private int qtyOpen;
        private double stopPrice;
        private double stopPts;
        private double balanceAtEntry;
        private double riskDollars;
        private int validityCandleAtEntry;
        private int reentryNumberAtEntry;
        private double mfeExtreme, maeExtreme;
        private double netPnlDollars;                     // accumulated across exit legs
        private double sumExitLegR;
        private bool anyProfitLeg;

        // ---- 50-point target chain (spec §9 / shared section D) ----
        private double refPrice = double.NaN;
        private TpTarget activeTarget;
        private bool trailActivated;
        private bool tp90Done;

        private SupportingStructureTracker structure;   // V6 U3

        public VectorBreakRetestEngine(IMnqHost host, VbrConfig cfg)
        {
            this.host = host;
            this.cfg = cfg;
            structure = new SupportingStructureTracker();
        }

        public bool HasOpenOrPendingPosition { get { return state == VbrState.POSITION_OPEN; } }

        private string EntrySignal { get { return isLong ? "VBR_LONG" : "VBR_SHORT"; } }
        private string StopSignal { get { return isLong ? "VBR_STOP_L" : "VBR_STOP_S"; } }
        private string Tp90Signal { get { return isLong ? "VBR_TP90_L" : "VBR_TP90_S"; } }
        private string RunSignal { get { return isLong ? "VBR_RUN_L" : "VBR_RUN_S"; } }

        public void OnNewDay(DateTime etTime)
        {
            // Daily Open rolled — a pre-entry parent from the old exchange day no
            // longer references a live level.
            if (state == VbrState.PARENT_15M_ACTIVE_SEARCHING_1M
                || state == VbrState.STOPPED_OUT_REENTRY_ELIGIBILITY_PENDING
                || state == VbrState.REENTRY_SCAN)
            {
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, "setup CANCELLED: new exchange day — Daily Open rolled");
                ResetSetup();
            }
        }

        private void ResetSetup()
        {
            state = VbrState.IDLE;
            validityCount = 0;
            structActive = false;
            waitingEmaB = false;
            structExtreme = double.NaN;
            structStartEt = DateTime.MinValue;
            reentryCount = 0;
            stopOutFormingCandleNum = 0;
            reentryScanCandleNum = 0;
        }

        private void ResetPattern()
        {
            structActive = false;
            waitingEmaB = false;
            structExtreme = double.NaN;
            structStartEt = DateTime.MinValue;
        }

        // ==================================================================
        // 15-MINUTE SERIES — parent trigger (§2/§3), 4-candle validity clock
        // (NO +2 extension), re-entry eligibility (§8)
        // ==================================================================
        public void OnFifteenMinuteBar(BarSnap bar, double prev15Close)
        {
            // ---- validity clock (only ticks while a parent exists) ----
            if (state != VbrState.IDLE)
            {
                validityCount++;

                // ==========================================================
                // FINAL RULE 4 — HARD 15m INVALIDATION.
                // A completed 15m validity candle that CLOSES on the wrong side of
                // Daily Open kills the ENTIRE parent immediately: Pattern A scanning,
                // the Pattern B structure, the Pattern B EMA wait and any pending
                // entry state all die with it (FINAL RULE 10).
                // A WICK through Daily Open does NOT invalidate (FINAL RULE 11).
                // Completed bars only — never intrabar.
                // ==========================================================
                bool invalidatedThisBar = false;
                if (state != VbrState.POSITION_OPEN && !double.IsNaN(dailyOpenAtTrigger) && validityCount <= 4)
                {
                    bool wickCrossedDo = isLong
                        ? bar.Low < dailyOpenAtTrigger
                        : bar.High > dailyOpenAtTrigger;
                    bool closeInvalidated = isLong
                        ? bar.Close < dailyOpenAtTrigger
                        : bar.Close > dailyOpenAtTrigger;

                    host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                        "VBR 15M VALIDITY direction={0} candleNum={1} close={2:0.00} dailyOpen={3:0.00} wickCrossedDO={4} closeInvalidated={5}",
                        isLong ? "LONG" : "SHORT", validityCount, bar.Close, dailyOpenAtTrigger,
                        wickCrossedDo ? "true" : "false", closeInvalidated ? "true" : "false"));

                    if (closeInvalidated)
                    {
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                            "VBR PARENT INVALIDATED reason=15M_CLOSE_WRONG_SIDE_DAILY_OPEN direction={0} candleNum={1} close={2:0.00} dailyOpen={3:0.00}",
                            isLong ? "LONG" : "SHORT", validityCount, bar.Close, dailyOpenAtTrigger));
                        ResetSetup();          // clears pattern A/B state, EMA wait, parent validity
                        invalidatedThisBar = true;
                    }
                }

                if (!invalidatedThisBar)
                {
                if (state == VbrState.STOPPED_OUT_REENTRY_ELIGIBILITY_PENDING
                    && validityCount == stopOutFormingCandleNum)
                {
                    // §8: the SAME 15m candle that contained the stopped 1m attempt
                    // must wick into/through Daily Open and ultimately close back on
                    // the trade side of it.
                    bool eligible = isLong
                        ? (bar.Low <= dailyOpenAtTrigger && bar.Close > dailyOpenAtTrigger)
                        : (bar.High >= dailyOpenAtTrigger && bar.Close < dailyOpenAtTrigger);

                    if (eligible && validityCount < 4)
                    {
                        reentryScanCandleNum = validityCount + 1;
                        state = VbrState.REENTRY_SCAN;
                        ResetPattern();
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                            "RE-ENTRY ELIGIBLE: stop-out candle #{0} wicked DO {1:0.00} and closed {2:0.00} on trade side — scanning fresh 1m setup during candle #{3} (spec §8)",
                            validityCount, dailyOpenAtTrigger, bar.Close, reentryScanCandleNum));
                    }
                    else
                    {
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST, eligible
                            ? "re-entry not possible: original 4-candle window exhausted (spec §8)"
                            : "re-entry NOT eligible: stop-out 15m candle failed the wick/close rule (spec §8) — setup finished");
                        ResetSetup();
                    }
                }
                else if (state == VbrState.REENTRY_SCAN && validityCount >= reentryScanCandleNum)
                {
                    // The authorized scan candle completed with no entry.
                    if (cfg.ReentryScanOnlyFollowingCandle)
                    {
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST,
                            "re-entry scan candle completed with no entry — setup finished (LEGACY flag, not V6)");
                        ResetSetup();
                    }
                    else
                    {
                        // V6 U7 ROLLING RE-QUALIFICATION: permission propagates one
                        // 15m candle at a time inside the ORIGINAL 4-candle clock.
                        // "#4 may scan only if #3 itself closes on the correct side"
                        // — the rolling candle needs only the correct-side close; the
                        // wick-into-Daily-Open test applies to the stop-out candle.
                        bool correctSideClose = isLong
                            ? bar.Close > dailyOpenAtTrigger
                            : bar.Close < dailyOpenAtTrigger;

                        if (!correctSideClose)
                        {
                            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                                "ROLLING RE-ENTRY BROKEN: candle #{0} closed {1:0.00} on the WRONG side of DAILY_OPEN {2:0.00} — no further re-entry (V6 U7)",
                                validityCount, bar.Close, dailyOpenAtTrigger));
                            ResetSetup();
                        }
                        else if (validityCount >= 4)
                        {
                            // clock never restarts or extends
                            host.Diag(StrategyId.VECTOR_BREAK_RETEST,
                                "ORIGINAL 4-candle clock ended — setup EXPIRED (V6 U7: clock never restarts or extends)");
                            ResetSetup();
                        }
                        else
                        {
                            reentryScanCandleNum = validityCount + 1;
                            ResetPattern();
                            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                                "ROLLING RE-ENTRY: candle #{0} closed {1:0.00} on the correct side of DAILY_OPEN — candle #{2} may scan for a FRESH 1m setup (V6 U7)",
                                validityCount, bar.Close, reentryScanCandleNum));
                        }
                    }
                }
                else if (state == VbrState.PARENT_15M_ACTIVE_SEARCHING_1M && validityCount >= 4)
                {
                    // §2/§3: exactly the NEXT 4 completed 15m candles; NO +2 extension.
                    host.Diag(StrategyId.VECTOR_BREAK_RETEST,
                        "parent setup EXPIRED: 4 validity candles completed with no entry (no extension, spec §2/§3)");
                    ResetSetup();
                }
                else if (state != VbrState.POSITION_OPEN && host.IsAfterEntryCutoff(bar.EtClose))
                {
                    host.Diag(StrategyId.VECTOR_BREAK_RETEST, "setup EXPIRED: past 11:30 ET entry cutoff");
                    ResetSetup();
                }
                }
            }

            // ---- parent trigger (§2 long / §3 short) ----
            bool mayTrigger = state == VbrState.IDLE
                || (state == VbrState.PARENT_15M_ACTIVE_SEARCHING_1M && cfg.RetriggerReplacesActiveSetup);
            if (!mayTrigger || !host.InstrumentOk) return;
            if (host.IsAfterEntryCutoff(bar.EtClose)) return; // could never produce an entry today

            double dailyOpen = host.Levels.DailyOpen;
            if (double.IsNaN(dailyOpen)) return;

            bool longTrig = bar.Vector == VectorType.GREEN_VECTOR && bar.Close > dailyOpen;
            bool shortTrig = bar.Vector == VectorType.RED_VECTOR && bar.Close < dailyOpen;
            if (cfg.RequireCrossThrough)
            {
                // VBR-1: the vector candle must actually interact with Daily Open
                bool crossedLong = bar.Low <= dailyOpen || (!double.IsNaN(prev15Close) && prev15Close <= dailyOpen);
                bool crossedShort = bar.High >= dailyOpen || (!double.IsNaN(prev15Close) && prev15Close >= dailyOpen);
                longTrig = longTrig && crossedLong;
                shortTrig = shortTrig && crossedShort;
            }
            if (!longTrig && !shortTrig) return;

            // FINAL RULE 1 — HARD parent candle size filter. Checked AFTER the vector
            // and close-side conditions so the rejection log only fires for candles
            // that would otherwise have become parents.
            double parentRange = bar.High - bar.Low;
            if (parentRange + 1e-9 < cfg.ParentMinRangePoints)
            {
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "VBR PARENT REJECTED reason=PARENT_RANGE_BELOW_125 range={0:0.00} required={1:0.00} direction={2} vector={3} time={4:HH:mm}",
                    parentRange, cfg.ParentMinRangePoints, longTrig ? "LONG" : "SHORT", bar.Vector, bar.EtClose));
                return;   // no parent, no validity clock, no 1m scanning
            }

            bool replacing = state == VbrState.PARENT_15M_ACTIVE_SEARCHING_1M;
            state = VbrState.PARENT_15M_ACTIVE_SEARCHING_1M;
            isLong = longTrig;
            parentVector = bar.Vector;
            parentTriggerEtClose = bar.EtClose;
            dailyOpenAtTrigger = dailyOpen;
            validityCount = 0;
            reentryCount = 0;
            stopOutFormingCandleNum = 0;
            reentryScanCandleNum = 0;
            parentPremarket = !host.IsAtOrAfterSessionStart(bar.EtClose);
            ResetPattern();

            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                "VBR PARENT CREATED{0} direction={1} time={2:yyyy-MM-dd HH:mm} dailyOpen={3:0.00}"
                + " parentOpen={4:0.00} parentHigh={5:0.00} parentLow={6:0.00} parentClose={7:0.00}"
                + " parentRangePoints={8:0.00} vectorType={9} validityWindow=4",
                replacing ? " (replaces active setup, VBR-2)" : "",
                isLong ? "LONG" : "SHORT", bar.EtClose, dailyOpen,
                bar.Open, bar.High, bar.Low, bar.Close, parentRange, parentVector));
        }

        // ==================================================================
        // 1-MINUTE SERIES — entry patterns A/B (§4-§7), position management
        // (§9 + shared section D)
        // ==================================================================
        public void OnOneMinuteBar(BarSnap bar)
        {
            structure.Add(bar.High, bar.Low); // V6 U3 one-candle supporting structure

            if (state == VbrState.POSITION_OPEN)
            {
                ManagePosition(bar);
                return;
            }

            if (state != VbrState.PARENT_15M_ACTIVE_SEARCHING_1M && state != VbrState.REENTRY_SCAN)
                return;

            // entries only during valid 15m candles #1..#4 (§2/§3)
            int formingCandle = validityCount + 1;
            if (formingCandle > 4) return;
            // re-entry scan restricted to its designated following candle (§8/VBR-4)
            // Re-entry scanning is confined to the currently authorized validity
            // candle (V6 U7: permission rolls forward one candle at a time).
            if (state == VbrState.REENTRY_SCAN && formingCandle != reentryScanCandleNum)
                return;

            double dOpen = dailyOpenAtTrigger;

            // ---------- Pattern B in progress ----------
            if (structActive)
            {
                bool reclaim = isLong ? bar.Close > dOpen : bar.Close < dOpen;
                if (!reclaim)
                {
                    // still through Daily Open — extend the structure extreme (§5/§7 stop basis)
                    if (isLong) { if (bar.Low < structExtreme) structExtreme = bar.Low; }
                    else { if (bar.High > structExtreme) structExtreme = bar.High; }
                    return;
                }

                // include the reclaim candle's wick in the structure
                if (isLong) { if (bar.Low < structExtreme) structExtreme = bar.Low; }
                else { if (bar.High > structExtreme) structExtreme = bar.High; }

                // V6 U6: entry requires a completed 1m close beyond BOTH Daily Open
                // and the 1m EMA(9). The reclaim close is already beyond Daily Open
                // here, so only the EMA leg is outstanding.
                bool emaOk = isLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "PATTERN_B_DO_RECLAIM close={0:0.00} ema9={1:0.00} emaConfirmed={2}",
                    bar.Close, bar.Ema9, emaOk ? "true" : "false"));
                if (emaOk)
                {
                    TryEnter(bar, "CLOSE_RECLAIM_B", structExtreme);
                }
                else if (cfg.PatternBWaitForEma)
                {
                    // FINAL RULE 8: keep waiting — but ONLY while the original 15m
                    // parent stays valid. The 15m invalidation in OnFifteenMinuteBar
                    // clears this state outright (FINAL RULE 10).
                    waitingEmaB = true;
                    structActive = false;
                }
                else
                {
                    host.Diag(StrategyId.VECTOR_BREAK_RETEST,
                        "Pattern B reclaim failed the EMA condition — structure cleared (LEGACY flag, not V6)");
                    ResetPattern();
                }
                return;
            }

            // ---------- V6 U6 Pattern B EMA wait ----------
            // Enter only when a later completed 1m candle closes beyond BOTH the
            // Daily Open and the 1m EMA(9). A candle beyond the EMA but on the wrong
            // side of Daily Open is NOT a valid entry (U6 step 7). A candle that
            // closes back through Daily Open re-opens the structure leg (U6 step 1).
            if (waitingEmaB)
            {
                bool backThroughDo = isLong ? bar.Close < dOpen : bar.Close > dOpen;
                if (backThroughDo)
                {
                    // FINAL RULE 9 — ROOT-CAUSE FIX.
                    // A completed 1m close back through Daily Open is a NEW step-1 and
                    // therefore a NEW LOCAL structure. The previous implementation
                    // RESUMED the old extreme here (min/max against the stale value),
                    // so every additional Daily Open excursion ratcheted the stop
                    // further out and one "structure" could span the whole 60-minute
                    // parent window. The extreme is now seeded from THIS candle only.
                    waitingEmaB = false;
                    structActive = true;
                    structExtreme = isLong ? bar.Low : bar.High;   // FRESH — never inherited
                    structStartEt = bar.EtClose;
                    host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                        "PATTERN_B_STRUCTURE_START direction={0} time={1:yyyy-MM-dd HH:mm} dailyOpen={2:0.00} structureExtreme={3:0.00} (fresh excursion — previous structure discarded)",
                        isLong ? "LONG" : "SHORT", bar.EtClose, dOpen, structExtreme));
                    return;
                }

                bool emaOk = isLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
                if (emaOk)
                {
                    TryEnter(bar, "CLOSE_RECLAIM_B", structExtreme);   // beyond DO and beyond EMA9
                }
                else
                {
                    host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                        "PATTERN_B_EMA_WAIT currentClose={0:0.00} dailyOpen={1:0.00} ema9={2:0.00} structureExtreme={3:0.00} parentValidityCandle={4}",
                        bar.Close, dOpen, bar.Ema9, structExtreme, validityCount + 1));
                }
                return;
            }

            // ---------- fresh pattern detection ----------
            bool closedThrough = isLong ? bar.Close < dOpen : bar.Close > dOpen;
            if (closedThrough)
            {
                // §5/§7 step 1: completed 1m close through Daily Open starts Pattern B.
                // GLOBAL ENTRY-TIME RULE: only patterns forming at/after 9:30 ET count.
                if (!host.IsAtOrAfterSessionStart(bar.EtOpen)) return;
                structActive = true;
                structExtreme = isLong ? bar.Low : bar.High;
                structStartEt = bar.EtClose;
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "PATTERN_B_STRUCTURE_START direction={0} time={1:yyyy-MM-dd HH:mm} dailyOpen={2:0.00} structureExtreme={3:0.00}",
                    isLong ? "LONG" : "SHORT", bar.EtClose, dOpen, structExtreme));
                return;
            }

            // §4/§6 Pattern A — wick retest that holds:
            //  long: wick into DO (low <= DO), close back above it, close already above EMA9
            bool wicked = isLong ? (bar.Low <= dOpen && bar.Close > dOpen) : (bar.High >= dOpen && bar.Close < dOpen);
            if (wicked)
            {
                if (!host.IsAtOrAfterSessionStart(bar.EtOpen)) return;
                bool emaOk = isLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
                if (emaOk)
                {
                    // §4/§6 STOP: LOW/WICK (HIGH/WICK) of the qualifying retest candle
                    TryEnter(bar, "WICK_RETEST_A", isLong ? bar.Low : bar.High);
                }
                else
                {
                    host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                        "Pattern A wick retest at DO {0:0.00} but close {1:0.00} not through 1m EMA9 {2:0.00} — no entry (§4/§6)",
                        dOpen, bar.Close, bar.Ema9));
                }
            }
        }

        // ==================================================================
        // Entry — grade A+ / 50% risk (spec GRADE), MNQ sizing, time gates
        // ==================================================================
        private void TryEnter(BarSnap bar, string pattern, double stop)
        {
            // GLOBAL ENTRY-TIME RULE: 9:30-11:30 ET at the signal-candle close
            if (!host.IsEntryTimeAllowed(bar.EtClose))
            {
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(
                    "entry blocked: signal close {0:HH:mm} ET outside 9:30-11:30 window", bar.EtClose));
                ResetPattern();
                if (host.IsAfterEntryCutoff(bar.EtClose)) ResetSetup();
                return;
            }

            // V6 U9: an open FB position does NOT block this entry — the host
            // flattens FB first and submits this order only once flat is confirmed.
            if (!host.CanOpenPosition(StrategyId.VECTOR_BREAK_RETEST))
            {
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, "entry blocked: trading disabled for this instrument");
                ResetPattern();
                return;
            }

            double entryRef = bar.Close;
            double pts = isLong ? entryRef - stop : stop - entryRef;
            if (pts <= 0)
            {
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, "entry blocked: non-positive stop distance");
                ResetPattern();
                return;
            }

            // GRADE: every valid Vector Break Retest = A+ = 50% account risk (spec)
            double balance = host.AccountBalance;
            double rd, rpc;
            int qty = PositionSizer.Contracts(balance, cfg.RiskPctAPlus, pts, out rd, out rpc);
            if (qty < 1)
            {
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "entry blocked: sizing yields 0 contracts (balance={0:0.00} risk%={1} stopPts={2:0.00})",
                    balance, cfg.RiskPctAPlus, pts));
                ResetPattern();
                return;
            }

            // FINAL RULE 12: elapsedMinutes exposes Pattern B structures that stayed
            // alive far longer than the local move actually being traded.
            if (pattern == "CLOSE_RECLAIM_B")
            {
                double elapsed = structStartEt == DateTime.MinValue
                    ? -1 : (bar.EtClose - structStartEt).TotalMinutes;
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "PATTERN_B_ENTRY entry={0:0.00} stop={1:0.00} stopPts={2:0.00} structureStartTime={3:yyyy-MM-dd HH:mm}"
                    + " structureExtreme={4:0.00} entryTime={5:yyyy-MM-dd HH:mm} elapsedMinutes={6:0}",
                    entryRef, stop, pts, structStartEt, stop, bar.EtClose, elapsed));
            }

            tradeSeq++;
            tradeId = string.Format(CultureInfo.InvariantCulture, "VBR-{0:yyyyMMdd}-{1}", bar.EtClose, tradeSeq);
            entryPattern = pattern;
            entryEtTime = bar.EtClose;
            intendedEntry = entryRef;
            stopPrice = stop;
            stopPts = pts;
            balanceAtEntry = balance;
            riskDollars = rd;
            qtyTotal = qty;
            qtyFilled = 0;
            qtyOpen = 0;
            entryAvg = 0;
            validityCandleAtEntry = validityCount + 1;
            reentryNumberAtEntry = reentryCount;
            netPnlDollars = 0;
            sumExitLegR = 0;
            anyProfitLeg = false;
            tp90Done = false;
            trailActivated = false;
            activeTarget = null;
            refPrice = double.NaN;
            state = VbrState.POSITION_OPEN;
            ResetPattern();

            host.EnterPosition(StrategyId.VECTOR_BREAK_RETEST, isLong ? TradeDirection.Long : TradeDirection.Short,
                qty, EntrySignal);

            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                "ENTRY {0} {1} pattern={2} validityCandle={3} grade=A+ reentry#{4} entryRef={5:0.00} stop={6:0.00} stopPts={7:0.00} balance={8:0.00} risk%={9} riskDollars={10:0.00} contracts={11} tradeId={12}",
                isLong ? "LONG" : "SHORT", EntrySignal, pattern, validityCandleAtEntry, reentryNumberAtEntry,
                entryRef, stop, pts, balance, cfg.RiskPctAPlus, rd, qty, tradeId));
        }

        // ==================================================================
        // Position management — spec §9 + shared engine section D:
        // 50-point chaining through the 18-level engine, then 1m EMA(9) trail
        // (90%) and final-10% structure-break runner. Wicks never count.
        // ==================================================================
        private void ManagePosition(BarSnap bar)
        {
            if (qtyOpen <= 0) return; // waiting for entry fill

            // MFE / MAE
            if (isLong)
            {
                if (bar.High > mfeExtreme) mfeExtreme = bar.High;
                if (bar.Low < maeExtreme) maeExtreme = bar.Low;
            }
            else
            {
                if (bar.Low < mfeExtreme) mfeExtreme = bar.Low;
                if (bar.High > maeExtreme) maeExtreme = bar.High;
            }

            // ---- 50-point chain: hold for targets <= 50 pts away (section D) ----
            int guard = 0;
            while (!trailActivated && activeTarget != null && guard++ < 25)
            {
                // "reached" definition is configurable (V5 unresolved item 2)
                bool reached;
                if (cfg.TargetReached == TargetReachedMode.OneMinuteCloseBeyond)
                    reached = isLong ? bar.Close > activeTarget.Price : bar.Close < activeTarget.Price;
                else
                    reached = isLong ? bar.High >= activeTarget.Price : bar.Low <= activeTarget.Price;
                if (!reached) break;

                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "TARGET REACHED {0} @ {1:0.00} (ref was {2:0.00}) — chaining to next level (section D)",
                    activeTarget.NameString(), activeTarget.Price, refPrice));

                // "set that reached target price as the new reference point"
                refPrice = activeTarget.Price;
                AdvanceTargetChain(false);
            }

            // ---- 1m EMA(9) trail mode: take profit on 90% (spec §9 TRAIL MODE) ----
            if (trailActivated && !tp90Done)
            {
                bool emaBreak = isLong ? bar.Close < bar.Ema9 : bar.Close > bar.Ema9; // completed close only
                if (emaBreak)
                {
                    int q90 = (int)Math.Floor(qtyOpen * 0.9);
                    if (q90 >= 1)
                    {
                        tp90Done = true;
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                            "TRAIL EXIT: 1m close {0:0.00} through 1m EMA9 {1:0.00} — taking 90% ({2} of {3} contracts), final {4} runs (spec §9)",
                            bar.Close, bar.Ema9, q90, qtyOpen, qtyOpen - q90));
                        host.ExitMarket(StrategyId.VECTOR_BREAK_RETEST,
                            isLong ? TradeDirection.Long : TradeDirection.Short, q90, Tp90Signal, EntrySignal);
                    }
                    else if (cfg.SingleContractBecomesRunner)
                    {
                        tp90Done = true; // LEGACY research only — not V6 behavior
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST,
                            "TRAIL signal with 1 contract: contract held as runner (LEGACY flag, not V6)");
                    }
                    else
                    {
                        // V6 U8: a 1-contract position cannot be split 90/10 — the 1m
                        // EMA(9) profit signal exits the ENTIRE contract, no runner.
                        tp90Done = true;
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                            "TRAIL EXIT: 1m close {0:0.00} through 1m EMA9 {1:0.00} with a 1-contract position — exiting the ENTIRE contract, no runner (V6 U8)",
                            bar.Close, bar.Ema9));
                        host.ExitMarket(StrategyId.VECTOR_BREAK_RETEST,
                            isLong ? TradeDirection.Long : TradeDirection.Short, qtyOpen, Tp90Signal, EntrySignal);
                    }
                }
            }

            // ---- FINAL 10% RUNNER (V6 U3): exit when a LATER completed 1m candle
            //      CLOSES through the one-candle supporting structure. Wicks do not
            //      count; no multi-bar fractal confirmation is required. ----
            if (tp90Done && qtyOpen > 0)
            {
                double support = isLong ? structure.SupportLow : structure.SupportHigh;
                int supportBar = isLong ? structure.SupportLowBar : structure.SupportHighBar;
                // the establishing candle can never be the breaking candle
                if (!double.IsNaN(support) && structure.BarIndex > supportBar)
                {
                    bool structBreak = isLong ? bar.Close < support : bar.Close > support;
                    if (structBreak)
                    {
                        host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                            "RUNNER EXIT: 1m close {0:0.00} through 1m supporting structure {1:0.00} — exiting final {2} contracts (V6 U3)",
                            bar.Close, support, qtyOpen));
                        host.ExitMarket(StrategyId.VECTOR_BREAK_RETEST,
                            isLong ? TradeDirection.Long : TradeDirection.Short, qtyOpen, RunSignal, EntrySignal);
                    }
                }
            }
        }

        // Compute the next directional target from the CURRENT reference price and
        // decide hold vs trail per the 50-point rule (section D). initial=true on
        // the entry fill.
        private void AdvanceTargetChain(bool initial)
        {
            List<TpTarget> targets = host.Levels.GetSortedTargets(
                isLong ? TradeDirection.Long : TradeDirection.Short, refPrice, host.TpLevelEnabled, host.RoundToTick);

            if (targets.Count == 0)
            {
                activeTarget = null;
                trailActivated = true; // VBR-8: no level left in direction → trail
                host.Diag(StrategyId.VECTOR_BREAK_RETEST,
                    "no further directional take-profit level — 1m EMA(9) TRAIL MODE ACTIVE (VBR-8)");
                return;
            }

            activeTarget = targets[0];
            double dist = Math.Abs(activeTarget.Price - refPrice);
            bool hold = dist <= cfg.ChainMaxDistancePoints;

            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                "{0} target {1} @ {2:0.00} dist={3:0.00}pts from ref {4:0.00} → {5}",
                initial ? "FIRST" : "NEXT", activeTarget.NameString(), activeTarget.Price, dist, refPrice,
                hold ? "HOLD for level (<=50pts: adverse 1m EMA9 closes IGNORED, section D)" : "TRAIL MODE (>50pts, spec §9)"));

            if (!hold)
                trailActivated = true;
        }

        // ==================================================================
        // Execution routing (called by the host strategy)
        // ==================================================================
        public void OnEntryExecution(string orderName, double price, int qty, DateTime etTime)
        {
            if (orderName != EntrySignal || state != VbrState.POSITION_OPEN) return;

            entryAvg = (entryAvg * qtyFilled + price * qty) / Math.Max(1, qtyFilled + qty);
            qtyFilled += qty;
            qtyOpen += qty;

            if (qtyFilled == qty) // first fill
            {
                mfeExtreme = price;
                maeExtreme = price;
                // structure stop, live until cancelled (§4-§7 STOP definitions)
                host.SubmitOrUpdateStop(StrategyId.VECTOR_BREAK_RETEST,
                    isLong ? TradeDirection.Long : TradeDirection.Short,
                    qtyTotal, stopPrice, StopSignal, EntrySignal);

                stopPts = isLong ? entryAvg - stopPrice : stopPrice - entryAvg;

                // section D step 1-2: reference = entry, find next directional level
                refPrice = entryAvg;
                trailActivated = false;
                AdvanceTargetChain(true);

                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                    "FILLED {0} qty={1} avg={2:0.00} stop={3:0.00} stopPts={4:0.00}", orderName, qty, entryAvg, stopPrice, stopPts));
            }
        }

        public void OnExitExecution(string orderName, double price, int qty, DateTime etTime)
        {
            if (state != VbrState.POSITION_OPEN) return;

            string leg;
            string reason;
            if (orderName.Contains("STOP")) { leg = "STOP"; reason = "STOP_LOSS"; }
            else if (orderName.Contains("TP90")) { leg = "TP90"; reason = "TRAIL_90_EMA1M"; }
            else if (orderName.Contains("HANDOFF")) { leg = "HANDOFF_FLATTEN"; reason = "HANDOFF_FLATTEN"; } // V6 U9
            else { leg = "RUNNER"; reason = "RUNNER_STRUCTURE_BREAK"; }

            ApplyExitLeg(price, qty, etTime, leg, reason);
        }

        // V6 U9: flatten this engine's open position so FAKE_BREAKOUT may enter.
        // A handoff flatten is NOT a stop-out, so it never arms the re-entry rule.
        public void FlattenForHandoff()
        {
            if (state != VbrState.POSITION_OPEN || qtyOpen <= 0) return;
            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(
                "HANDOFF FLATTEN: exiting {0} contracts of {1} for FAKE_BREAKOUT (V6 U9)", qtyOpen, EntrySignal));
            host.ExitMarket(StrategyId.VECTOR_BREAK_RETEST,
                isLong ? TradeDirection.Long : TradeDirection.Short,
                qtyOpen, isLong ? "VBR_HANDOFF_L" : "VBR_HANDOFF_S", EntrySignal);
        }

        public void OnSessionCloseExecution(double price, int qty, DateTime etTime)
        {
            if (state != VbrState.POSITION_OPEN || qtyOpen <= 0) return;
            int leg = Math.Min(qty, qtyOpen);
            ApplyExitLeg(price, leg, etTime, "SESSION_CLOSE", "SESSION_CLOSE");
        }

        private void ApplyExitLeg(double price, int qty, DateTime etTime, string leg, string reason)
        {
            qtyOpen -= qty;

            double pnlPts = isLong ? price - entryAvg : entryAvg - price;
            double pnlDollars = pnlPts * PositionSizer.MnqDollarsPerPoint * qty;
            double legR = stopPts > 0 ? pnlPts / stopPts : 0;
            netPnlDollars += pnlDollars;
            if (pnlDollars > 0) anyProfitLeg = true;

            double mfePts = isLong ? mfeExtreme - entryAvg : entryAvg - mfeExtreme;
            double maePts = isLong ? entryAvg - maeExtreme : maeExtreme - entryAvg;

            TradeRecord rec = new TradeRecord();
            rec.Strategy = StrategyId.VECTOR_BREAK_RETEST;
            rec.TradeId = tradeId;
            rec.Grade = "A+";                                     // spec: every valid VBR = A+
            rec.Direction = isLong ? TradeDirection.Long : TradeDirection.Short;
            rec.ParentTriggerTimeEt = parentTriggerEtClose;
            rec.ParentLevelName = KeyLevelId.DAILY_OPEN.ToString();
            rec.ParentLevelPrice = dailyOpenAtTrigger;
            rec.ParentVector = parentVector.ToString();
            rec.ValidityCandleNumber = validityCandleAtEntry;
            rec.EntryTimeframeMinutes = 1;                        // VBR enters on 1m ONLY
            rec.EntryPatternType = entryPattern;
            rec.EntryTimeEt = entryEtTime;
            rec.EntryPrice = entryAvg;
            rec.StopPrice = stopPrice;
            rec.StopDistancePoints = stopPts;
            rec.AccountBalance = balanceAtEntry;
            rec.RiskPercent = cfg.RiskPctAPlus;
            rec.RiskDollars = riskDollars;
            rec.Contracts = qtyFilled;
            rec.TargetLevelNames = activeTarget != null ? activeTarget.NameString() : "";
            rec.TargetPrice = activeTarget != null ? activeTarget.Price : double.NaN;
            rec.TargetDistancePoints = activeTarget != null && !double.IsNaN(refPrice)
                ? Math.Abs(activeTarget.Price - refPrice) : double.NaN;
            rec.ExitLeg = leg;
            rec.ExitQty = qty;
            rec.ExitTimeEt = etTime;
            rec.ExitPrice = price;
            rec.ExitReason = reason;
            rec.PnlPoints = pnlPts;
            rec.PnlDollars = pnlDollars;
            rec.RMultiple = legR;
            rec.MfePoints = mfePts;
            rec.MaePoints = maePts;
            rec.ReentryNumber = reentryNumberAtEntry;
            rec.ParentFormedPremarket = parentPremarket;
            rec.EntryFormedAfter930 = true;                       // enforced structurally
            host.LogTrade(rec);

            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                "EXIT LEG {0} qty={1} @ {2:0.00} reason={3} pnl={4:0.00}pts ${5:0.00} legR={6:0.00}",
                leg, qty, price, reason, pnlPts, pnlDollars, legR));

            if (qtyOpen > 0)
            {
                // keep the structure stop in sync with the remaining quantity
                host.SubmitOrUpdateStop(StrategyId.VECTOR_BREAK_RETEST,
                    isLong ? TradeDirection.Long : TradeDirection.Short,
                    qtyOpen, stopPrice, StopSignal, EntrySignal);
                return;
            }

            // ---- position fully closed ----
            double netR = riskDollars > 0 ? netPnlDollars / riskDollars : 0;
            Stats.AddClosedTrade(netPnlDollars, netR, mfePts, maePts);
            host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(CultureInfo.InvariantCulture,
                "TRADE CLOSED {0} net=${1:0.00} netR={2:0.00} MFE={3:0.00}pts MAE={4:0.00}pts",
                tradeId, netPnlDollars, netR, mfePts, maePts));

            bool fullStopOut = reason == "STOP_LOSS" && !anyProfitLeg && !tp90Done;
            if (fullStopOut)
            {
                // §8: a stop-out does NOT kill the parent and does NOT restart the
                // clock — check the wick/close rule when the current 15m candle completes.
                reentryCount++;
                stopOutFormingCandleNum = validityCount + 1;
                state = VbrState.STOPPED_OUT_REENTRY_ELIGIBILITY_PENDING;
                ResetPattern();
                host.Diag(StrategyId.VECTOR_BREAK_RETEST, string.Format(
                    "STOPPED OUT during validity candle #{0} — re-entry eligibility pending on that candle's close (spec §8)",
                    stopOutFormingCandleNum));
            }
            else
            {
                // profit-managed exit (or stop after profit legs): setup complete (VBR-7)
                ResetSetup();
            }
        }
    }
}
