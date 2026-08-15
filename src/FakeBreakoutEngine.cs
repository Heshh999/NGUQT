// ============================================================================
// FakeBreakoutEngine.cs
// STRATEGY 1 - FAKE BREAKOUT  (StrategyId = FAKE_BREAKOUT)
//
// Implements the spec sections:
//   "STRATEGY 1 - FAKE BREAKOUT" items 1-12
//   "FAKE_BREAKOUT trigger levels" (YDAY_HIGH, YDAY_LOW, LWEEK_HIGH, LWEEK_LOW;
//    DAILY_OPEN must NOT start a Fake Breakout setup)
//   "SHARED TAKE-PROFIT KEY-LEVEL ENGINE" section E (first target + 3m EMA runner)
//   "GLOBAL ENTRY-TIME RULE" (9:30-11:30 ET; premarket LTF signals never bank)
//
// This engine's state, counters, orders, grades, sizing, trade IDs and logs are
// fully independent of VectorBreakRetestEngine (spec hard separation rule).
// Order signal names: FB_LONG / FB_SHORT, exits FB_STOP_* / FB_RUN_*.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;

namespace NinjaTrader.NinjaScript.Strategies.MnqTwo
{
    // Spec "Suggested Fake Breakout states" (WAITING_FOR_LOWER_TF_EMA lives inside
    // each lower-timeframe sub-setup; INVALIDATED/EXPIRED collapse back to IDLE).
    public enum FbState
    {
        IDLE,
        BREAKOUT_15M_ACTIVE,        // waiting for the 15m reclaim (structure tracking)
        STRUCTURE_FROZEN_SEARCHING, // reclaim confirmed; scanning 1m/3m for entry
        POSITION_OPEN,
        RUNNER_MODE
    }

    public class FbConfig
    {
        public double RiskPctAMinus = 26.0;   // spec: A- = 26% account risk
        public double RiskPctBPlus = 10.0;    // spec: B+ = 10% account risk

        // V5 correction Fix 2: the master rule is ONLY "trades beyond + closes
        // beyond + allowed candle type". The prior-close-inside condition is a
        // LEGACY research parameter and must default FALSE (exact-spec mode).
        public bool RequirePriorCloseInside = false;
        // V6 U4 - LOCKED: an invalid 15m reclaim does NOT cancel the parent setup.
        // Ignore it and keep waiting for another valid 15m reclaim while the parent
        // is inside its validity clock. LEGACY research flag, must stay FALSE.
        public bool InvalidReclaimCancelsSetup = false;
        // V6 U5 - LOCKED: a completed 15m reclaim/freeze is NOT required before the
        // 1m/3m entry engine may scan or enter. The 1m/3m engines scan as soon as a
        // valid 15m parent exists. Must be FALSE in exact-spec mode.
        public bool Require15mReclaimBeforeLtfEntry = false;
        // FINAL FAKE BREAKOUT EMA RULE - LOCKED:
        // The 15-minute EMA(9) is NOT an entry gate. It must never cancel, delay,
        // block or invalidate an otherwise valid 1m/3m Fake Breakout entry. Only the
        // LOWER-TIMEFRAME EMA(9) controls the actual entry. The 15m EMA is kept for
        // context/logging only. LEGACY research flag, must stay FALSE in exact-spec
        // mode; when TRUE it restores the old confluence gate (cancels the LTF setup).
        public bool Require15mEmaConfluence = false;
        // V6 U1 - LOCKED: first target is broken ONLY by a completed 1m close beyond
        // it (a wick/touch does not count). Then the 3m EMA(9) runner activates.
        public FbTargetBreakMode TargetBreakMode = FbTargetBreakMode.OneMinuteCloseBeyond;
        // V5 correction Fix 7: A- = entry in the FIRST 15m candle in which a
        // fresh lower-timeframe entry is actually eligible (premarket validity
        // candles, where entries are forbidden, cannot be the A- opportunity).
        public FbGradeBasis GradeBasis = FbGradeBasis.FirstTradableCandle;

        // ---- V7 CROSS-MARKET GRADING ----------------------------------------
        // When TRUE, grade and risk come from the ES + YM confirmation table and the
        // validity-candle A-/B+ system above is BYPASSED ENTIRELY. The two never run
        // together: RiskPctAMinus / RiskPctBPlus / GradeBasis are dead on this path.
        public bool UseCrossMarketGrading = true;
        // 0 = the ES/YM confirmation must sit on EXACTLY the MNQ entry bar's
        // completed timestamp. Higher values allow that many bars of lag.
        public int CrossMarketToleranceBars = 0;
        // USER RULE (2026-08-14): there is NO legacy fallback. If cross-market grading
        // is switched on but a confirmation market cannot be evaluated, the trade is
        // BLOCKED and logged. A legacy grade must never be dressed up as a new one,
        // and a research dataset must never mix the two grading systems.
        public bool BlockEntryWhenCrossMarketUnavailable = true;
        public FbCrossMarketGradeTable CrossMarketGrades = new FbCrossMarketGradeTable();
    }

    public class FakeBreakoutEngine
    {
        // Spec: FakeBreakoutEligibleLevels = { YDAY_HIGH, YDAY_LOW, LWEEK_HIGH, LWEEK_LOW }
        private static readonly KeyLevelId[] EligibleLevels = new KeyLevelId[]
        {
            KeyLevelId.YDAY_HIGH, KeyLevelId.YDAY_LOW, KeyLevelId.LWEEK_HIGH, KeyLevelId.LWEEK_LOW
        };

        // ---- one lower-timeframe (1m or 3m) fake-break sub-setup (spec S9/S10) ----
        private class LtfSetup
        {
            public int TfMinutes;
            public bool StructureActive;   // break candle seen, waiting for reclaim
            public bool WaitingEma;        // valid reclaim seen, waiting for EMA close
            public double StructExtreme;   // long: lowest low; short: highest high
            public VectorType BreakVector;
            public DateTime StructStartEtOpen;

            public void Reset()
            {
                StructureActive = false;
                WaitingEma = false;
                StructExtreme = double.NaN;
            }
        }

        // ---- one directional parent-setup slot (spec S4 short / S5 long) ----
        private class FbSlot
        {
            public bool IsLong;
            public FbState State = FbState.IDLE;

            // parent setup
            public KeyLevelId ActiveLevelId;
            public double ActiveLevelPrice;
            public VectorType BreakoutVector;
            public DateTime BreakoutEtClose;       // OriginalBreakoutTime (spec S4)
            public int ValidityCount;              // completed 15m candles since breakout candle
            public double StructExtreme15;         // StructuralHigh / StructuralLow (spec S4/S5)
            public bool Frozen;
            public double FrozenExtreme;
            public bool ParentPremarket;
            public int FirstTradableFormingNum;    // for FbGradeBasis.FirstTradableCandle

            public LtfSetup Ltf1 = new LtfSetup();
            public LtfSetup Ltf3 = new LtfSetup();

            // trade
            public string TradeId;
            public string Grade;
            public double RiskPct;
            public double RiskDollars;
            public double BalanceAtEntry;
            public int EntryTf;
            public int ValidityCandleAtEntry;
            public DateTime EntryEtTime;
            public double IntendedEntry;
            public double EntryAvg;
            public int QtyTotal;
            public int QtyOpen;
            public int QtyFilled;
            public double StopPrice;
            public double StopPts;
            public string TargetNames = "";
            public double TargetPrice = double.NaN;
            public double TargetDistance = double.NaN;
            public bool TargetBroken;
            public double MfeExtreme;              // long: max high since entry; short: min low
            public double MaeExtreme;              // long: min low since entry;  short: max high
            public double ExitAvg;
            public int ExitQtyAccum;

            public bool HasPosition { get { return State == FbState.POSITION_OPEN || State == FbState.RUNNER_MODE; } }

            public string EntrySignal { get { return IsLong ? "FB_LONG" : "FB_SHORT"; } }
            public string StopSignal { get { return IsLong ? "FB_STOP_L" : "FB_STOP_S"; } }
            public string RunSignal { get { return IsLong ? "FB_RUN_L" : "FB_RUN_S"; } }
            // V6 U9 strategy handoff flatten (this position is closed so VBR may enter)
            public string HandoffSignal { get { return IsLong ? "FB_HANDOFF_L" : "FB_HANDOFF_S"; } }

            public void ResetAll()
            {
                State = FbState.IDLE;
                ValidityCount = 0;
                Frozen = false;
                FrozenExtreme = double.NaN;
                StructExtreme15 = double.NaN;
                FirstTradableFormingNum = 0;
                Ltf1.Reset();
                Ltf3.Reset();
                TradeId = null;
                Grade = null;
                QtyTotal = 0; QtyOpen = 0; QtyFilled = 0;
                EntryAvg = 0; ExitAvg = 0; ExitQtyAccum = 0;
                TargetBroken = false;
                TargetNames = "";
                TargetPrice = double.NaN;
                TargetDistance = double.NaN;
            }
        }

        private readonly IMnqHost host;
        private readonly FbConfig cfg;
        private readonly FbSlot longSlot;
        private readonly FbSlot shortSlot;
        private double last15Close = double.NaN;   // most recent COMPLETED 15m close (spec S7)
        private double last15Ema = double.NaN;     // most recent COMPLETED 15m EMA(9)
        private int tradeSeq;

        public StrategyStats Stats = new StrategyStats();

        public FakeBreakoutEngine(IMnqHost host, FbConfig cfg)
        {
            this.host = host;
            this.cfg = cfg;
            longSlot = new FbSlot(); longSlot.IsLong = true;
            shortSlot = new FbSlot(); shortSlot.IsLong = false;
            longSlot.ResetAll();
            shortSlot.ResetAll();
        }

        public bool HasOpenOrPendingPosition
        {
            get { return longSlot.HasPosition || shortSlot.HasPosition; }
        }

        // Cancel pre-entry setups when the exchange day rolls (key levels change).
        public void OnNewDay(DateTime etTime)
        {
            CancelPreEntry(longSlot, etTime, "new exchange day - key levels rolled, pre-entry setup cancelled");
            CancelPreEntry(shortSlot, etTime, "new exchange day - key levels rolled, pre-entry setup cancelled");
        }

        private void CancelPreEntry(FbSlot slot, DateTime etTime, string reason)
        {
            if (slot.State == FbState.BREAKOUT_15M_ACTIVE || slot.State == FbState.STRUCTURE_FROZEN_SEARCHING)
            {
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format("{0} setup CANCELLED: {1}", slot.IsLong ? "LONG" : "SHORT", reason));
                slot.ResetAll();
            }
        }

        // ==================================================================
        // 15-MINUTE SERIES (parent setup, reclaim, structure, validity clock,
        // EMA confluence source) - spec S1, S4, S5, S6, S7
        // ==================================================================
        public void OnFifteenMinuteBar(BarSnap bar, double prev15Close)
        {
            Process15(longSlot, bar, prev15Close);
            Process15(shortSlot, bar, prev15Close);

            // Spec S7: confluence compares the most recent COMPLETED 15m close to the
            // 15m EMA(9). Updated after slot processing so entries during the NEXT
            // forming candle read this candle's values.
            last15Close = bar.Close;
            last15Ema = bar.Ema9;
        }

        private void Process15(FbSlot slot, BarSnap bar, double prev15Close)
        {
            switch (slot.State)
            {
                case FbState.IDLE:
                    TryTrigger(slot, bar, prev15Close);
                    break;

                case FbState.BREAKOUT_15M_ACTIVE:
                case FbState.STRUCTURE_FROZEN_SEARCHING:
                    // Spec S6: this completed candle is validity candle #ValidityCount
                    slot.ValidityCount++;

                    if (!slot.Frozen)
                    {
                        // Spec S4/S5: StructuralHigh/Low tracks every subsequent completed 15m extreme
                        if (slot.IsLong) { if (bar.Low < slot.StructExtreme15) slot.StructExtreme15 = bar.Low; }
                        else { if (bar.High > slot.StructExtreme15) slot.StructExtreme15 = bar.High; }
                        TryReclaim(slot, bar);
                    }

                    // Spec S6: primary 4 candles + 2 extension, max 6; expire after
                    // candle #6 completes with no entry.
                    if ((slot.State == FbState.BREAKOUT_15M_ACTIVE || slot.State == FbState.STRUCTURE_FROZEN_SEARCHING)
                        && slot.ValidityCount >= 6)
                    {
                        host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                            "{0} setup EXPIRED after 6 validity candles (level {1} @ {2:0.00}, spec S6)",
                            slot.IsLong ? "LONG" : "SHORT", slot.ActiveLevelId, slot.ActiveLevelPrice));
                        slot.ResetAll();
                    }
                    // Spec S6: "11:30 AM ET entry cutoff overrides remaining time"
                    else if ((slot.State == FbState.BREAKOUT_15M_ACTIVE || slot.State == FbState.STRUCTURE_FROZEN_SEARCHING)
                        && host.IsAfterEntryCutoff(bar.EtClose))
                    {
                        host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                            "{0} setup EXPIRED: past 11:30 ET entry cutoff (spec S6)", slot.IsLong ? "LONG" : "SHORT"));
                        slot.ResetAll();
                    }
                    break;

                case FbState.POSITION_OPEN:
                case FbState.RUNNER_MODE:
                    break; // position management runs on 1m/3m
            }
        }

        // Spec S4 (short) / S5 (long): parent trigger on a COMPLETED 15m candle.
        private void TryTrigger(FbSlot slot, BarSnap bar, double prev15Close)
        {
            if (!host.InstrumentOk) return;
            // A setup starting after the 11:30 cutoff can never produce an entry today.
            if (host.IsAfterEntryCutoff(bar.EtClose)) return;

            // Initiating candle vector rules:
            //  short (S4): GREEN_VECTOR or REGULAR;  long (S5): RED_VECTOR or REGULAR
            //  (VIOLET explicitly not allowed to initiate a long; BLUE not listed -> not allowed)
            bool vectorOk = slot.IsLong
                ? (bar.Vector == VectorType.RED_VECTOR || VectorClassifier.IsRegular(bar.Vector))
                : (bar.Vector == VectorType.GREEN_VECTOR || VectorClassifier.IsRegular(bar.Vector));
            if (!vectorOk) return;

            KeyLevelId bestId = KeyLevelId.YDAY_HIGH;
            double bestPrice = double.NaN;
            bool found = false;

            foreach (KeyLevelId id in EligibleLevels)
            {
                double lvl = host.Levels.GetTriggerLevelPrice(id);
                if (double.IsNaN(lvl)) continue;

                bool trig;
                if (slot.IsLong)
                {
                    // S5: trades below AND closes below the level (wick alone insufficient)
                    trig = bar.Low < lvl && bar.Close < lvl
                        && (!cfg.RequirePriorCloseInside || (!double.IsNaN(prev15Close) && prev15Close >= lvl));
                }
                else
                {
                    // S4: trades above AND closes above the level
                    trig = bar.High > lvl && bar.Close > lvl
                        && (!cfg.RequirePriorCloseInside || (!double.IsNaN(prev15Close) && prev15Close <= lvl));
                }
                if (!trig) continue;

                // FB-9: multiple levels broken by one candle -> take the deepest broken
                // level (highest for a short breakout above / lowest for a long below).
                if (!found
                    || (slot.IsLong && lvl < bestPrice)
                    || (!slot.IsLong && lvl > bestPrice))
                {
                    found = true; bestId = id; bestPrice = lvl;
                }
            }
            if (!found) return;

            slot.State = FbState.BREAKOUT_15M_ACTIVE;
            slot.ActiveLevelId = bestId;
            slot.ActiveLevelPrice = bestPrice;
            slot.BreakoutVector = bar.Vector;
            slot.BreakoutEtClose = bar.EtClose;                       // OriginalBreakoutTime
            slot.StructExtreme15 = slot.IsLong ? bar.Low : bar.High;  // initiating candle extreme
            slot.Frozen = false;
            slot.ValidityCount = 0;
            slot.ParentPremarket = !host.IsAtOrAfterSessionStart(bar.EtClose);
            slot.FirstTradableFormingNum = 0;
            slot.Ltf1.Reset(); slot.Ltf3.Reset();

            // Spec diagnostic list: when parent setup started / which key level /
            // strategy / direction / vector type
            host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                "PARENT SETUP START dir={0} level={1}@{2:0.00} breakoutVector={3} breakoutClose={4:0.00} struct15={5:0.00} premarket={6} time={7:HH:mm}",
                slot.IsLong ? "LONG" : "SHORT", bestId, bestPrice, bar.Vector, bar.Close,
                slot.StructExtreme15, slot.ParentPremarket, bar.EtClose));
        }

        // Spec S4/S5: 15m reclaim close back through the level freezes the structure.
        private void TryReclaim(FbSlot slot, BarSnap bar)
        {
            bool reclaimClose = slot.IsLong
                ? bar.Close > slot.ActiveLevelPrice     // S5: CLOSES BACK ABOVE
                : bar.Close < slot.ActiveLevelPrice;    // S4: CLOSES BACK BELOW
            if (!reclaimClose) return;

            // 15m vector participation (spec S4/S5):
            bool valid;
            if (slot.IsLong)
            {
                // RED breakout -> reclaim may be REGULAR or GREEN
                // REGULAR breakout -> reclaim MUST be GREEN; REGULAR+REGULAR invalid
                if (slot.BreakoutVector == VectorType.RED_VECTOR)
                    valid = bar.Vector == VectorType.GREEN_VECTOR || VectorClassifier.IsRegular(bar.Vector);
                else
                    valid = bar.Vector == VectorType.GREEN_VECTOR;
            }
            else
            {
                // GREEN breakout -> reclaim may be REGULAR, RED or VIOLET
                // REGULAR breakout -> reclaim MUST be RED or VIOLET; REGULAR+REGULAR invalid
                if (slot.BreakoutVector == VectorType.GREEN_VECTOR)
                    valid = VectorClassifier.IsRegular(bar.Vector)
                         || bar.Vector == VectorType.RED_VECTOR || bar.Vector == VectorType.VIOLET_VECTOR;
                else
                    valid = bar.Vector == VectorType.RED_VECTOR || bar.Vector == VectorType.VIOLET_VECTOR;
            }

            if (valid)
            {
                slot.Frozen = true;
                slot.FrozenExtreme = slot.StructExtreme15;   // freeze incl. this candle's extreme
                slot.State = FbState.STRUCTURE_FROZEN_SEARCHING;
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "15m RECLAIM confirmed dir={0} reclaimVector={1} close={2:0.00} frozen{3}={4:0.00} validityCandle={5} - searching 1m/3m entry",
                    slot.IsLong ? "LONG" : "SHORT", bar.Vector, bar.Close,
                    slot.IsLong ? "StructLow" : "StructHigh", slot.FrozenExtreme, slot.ValidityCount));
            }
            else
            {
                if (cfg.InvalidReclaimCancelsSetup)
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                        "{0} setup CANCELLED: invalid 15m reclaim vector {1} after {2} breakout (REGULAR+REGULAR rule, config)",
                        slot.IsLong ? "LONG" : "SHORT", bar.Vector, slot.BreakoutVector));
                    slot.ResetAll();
                }
                else
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                        "{0} 15m reclaim IGNORED: vector {1} not valid after {2} breakout (spec S4/S5) - still waiting",
                        slot.IsLong ? "LONG" : "SHORT", bar.Vector, slot.BreakoutVector));
                }
            }
        }

        // ==================================================================
        // 3-MINUTE SERIES - entry scanning (S8-S10), structural invalidation
        // (S11), first-target break (3m mode) and 3m EMA(9) runner (S12/E)
        // ==================================================================
        public void OnThreeMinuteBar(BarSnap bar)
        {
            ProcessLtf(longSlot, longSlot.Ltf3, bar);
            ProcessLtf(shortSlot, shortSlot.Ltf3, bar);
        }

        // ==================================================================
        // 1-MINUTE SERIES - entry scanning (S8-S10), structural invalidation
        // (S11), MFE/MAE, Touch/1m-close target-break modes
        // ==================================================================
        public void OnOneMinuteBar(BarSnap bar)
        {
            ProcessLtf(longSlot, longSlot.Ltf1, bar);
            ProcessLtf(shortSlot, shortSlot.Ltf1, bar);
        }

        private void ProcessLtf(FbSlot slot, LtfSetup s, BarSnap bar)
        {
            // ---------- open position management ----------
            if (slot.HasPosition)
            {
                ManagePosition(slot, bar);
                return;
            }

            // ---------- FB-6 alt-grade bookkeeping (1m only) ----------
            if (bar.PeriodMinutes == 1 && slot.State != FbState.IDLE && slot.FirstTradableFormingNum == 0
                && host.IsAtOrAfterSessionStart(bar.EtOpen))
                slot.FirstTradableFormingNum = slot.ValidityCount + 1;

            bool mayScan = slot.State == FbState.STRUCTURE_FROZEN_SEARCHING
                        || (slot.State == FbState.BREAKOUT_15M_ACTIVE && !cfg.Require15mReclaimBeforeLtfEntry);
            if (!mayScan) return;

            // ---------- S11 overall 15m structural invalidation ----------
            // (completed 1m OR 3m close beyond the FROZEN structural extreme
            //  cancels the ENTIRE parent setup; wicks do not invalidate)
            if (slot.Frozen)
            {
                bool breach = slot.IsLong ? bar.Close < slot.FrozenExtreme : bar.Close > slot.FrozenExtreme;
                if (breach)
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                        "{0} setup INVALIDATED: completed {1}m close {2:0.00} beyond frozen structural {3} {4:0.00} (spec S11)",
                        slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, bar.Close,
                        slot.IsLong ? "low" : "high", slot.FrozenExtreme));
                    slot.ResetAll();
                    return;
                }
            }

            // ---------- S9 (long) / S10 (short) lower-timeframe fake break ----------
            double lvl = slot.ActiveLevelPrice;

            if (!s.StructureActive && !s.WaitingEma)
            {
                // Break candle:
                //  long S9 : RED_VECTOR or REGULAR closes below/through the level
                //  short S10 (V5): three paths -
                //    A. GREEN_VECTOR closes above/through   (any reclaim below)
                //    B. BLUE_VECTOR closes above/through    (V5 Fix 1: reclaim must
                //       be REGULAR or RED_VECTOR; VIOLET NOT valid on this path)
                //    C. REGULAR closes above/through        (RED/VIOLET reclaim)
                bool breakClose = slot.IsLong ? bar.Close < lvl : bar.Close > lvl;
                if (!breakClose) return;
                bool breakVecOk = slot.IsLong
                    ? (bar.Vector == VectorType.RED_VECTOR || VectorClassifier.IsRegular(bar.Vector))
                    : (bar.Vector == VectorType.GREEN_VECTOR || bar.Vector == VectorType.BLUE_VECTOR
                       || VectorClassifier.IsRegular(bar.Vector));
                if (!breakVecOk) return;

                // GLOBAL ENTRY-TIME RULE: premarket LTF patterns are never banked -
                // only patterns whose candles FORM at/after 9:30 ET are tracked.
                if (!host.IsAtOrAfterSessionStart(bar.EtOpen)) return;

                s.StructureActive = true;
                s.WaitingEma = false;
                s.BreakVector = bar.Vector;
                s.StructExtreme = slot.IsLong ? bar.Low : bar.High;
                s.StructStartEtOpen = bar.EtOpen;
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m fake-break structure started: {2} close {3:0.00} through level {4:0.00}, structExtreme={5:0.00}",
                    slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, bar.Vector, bar.Close, lvl, s.StructExtreme));
                return;
            }

            if (s.StructureActive && !s.WaitingEma)
            {
                bool reclaimClose = slot.IsLong ? bar.Close > lvl : bar.Close < lvl;
                if (!reclaimClose)
                {
                    // still on the far side of the level -> extend the fake-break structure
                    if (slot.IsLong) { if (bar.Low < s.StructExtreme) s.StructExtreme = bar.Low; }
                    else { if (bar.High > s.StructExtreme) s.StructExtreme = bar.High; }
                    return;
                }

                // Reclaim candle vector rules:
                //  long S9 : GREEN_VECTOR or BLUE_VECTOR only (REGULAR reclaim NOT valid)
                //  short S10 (V5):
                //    path A GREEN-first  -> preserve existing behavior: any close back below counts
                //    path B BLUE-first   -> V5 Fix 1: REGULAR or RED_VECTOR only
                //                          (VIOLET_VECTOR NOT valid on the BLUE path)
                //    path C REGULAR-first-> RED_VECTOR or VIOLET_VECTOR required
                //                          (REGULAR + REGULAR = invalid)
                bool reclaimVecOk;
                if (slot.IsLong)
                    reclaimVecOk = bar.Vector == VectorType.GREEN_VECTOR || bar.Vector == VectorType.BLUE_VECTOR;
                else if (s.BreakVector == VectorType.GREEN_VECTOR)
                    reclaimVecOk = true;
                else if (s.BreakVector == VectorType.BLUE_VECTOR)
                    reclaimVecOk = VectorClassifier.IsRegular(bar.Vector) || bar.Vector == VectorType.RED_VECTOR;
                else
                    reclaimVecOk = bar.Vector == VectorType.RED_VECTOR || bar.Vector == VectorType.VIOLET_VECTOR;

                if (!reclaimVecOk)
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                        "{0} {1}m reclaim vector {2} invalid (breakVector={3}) - LTF setup cancelled, keep scanning (spec S8)",
                        slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, bar.Vector, s.BreakVector));
                    s.Reset();
                    return;
                }

                // include the reclaim candle's wick in the structure extreme
                if (slot.IsLong) { if (bar.Low < s.StructExtreme) s.StructExtreme = bar.Low; }
                else { if (bar.High > s.StructExtreme) s.StructExtreme = bar.High; }

                // S9/S10 EMA step: enter now if already through that timeframe's EMA9,
                // else wait for the first completed close through it.
                bool emaOk = slot.IsLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m fake-break RECLAIM: {2} close {3:0.00} back through {4:0.00}, ema9={5:0.00}, emaConfirmed={6}",
                    slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, bar.Vector, bar.Close, lvl, bar.Ema9, emaOk));
                if (emaOk)
                    TryEnter(slot, s, bar);
                else
                    s.WaitingEma = true;
                return;
            }

            if (s.WaitingEma)
            {
                // S9/S10: while waiting, a completed close beyond the fake-break
                // structure extreme cancels this LTF setup only.
                bool structBreach = slot.IsLong ? bar.Close < s.StructExtreme : bar.Close > s.StructExtreme;
                if (structBreach)
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                        "{0} {1}m LTF setup cancelled: close {2:0.00} beyond fake-break structure {3:0.00} before EMA confirmation (spec S9/S10)",
                        slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, bar.Close, s.StructExtreme));
                    s.Reset();
                    return;
                }
                // extend structure extreme with wicks while waiting (stop = structure wick)
                if (slot.IsLong) { if (bar.Low < s.StructExtreme) s.StructExtreme = bar.Low; }
                else { if (bar.High > s.StructExtreme) s.StructExtreme = bar.High; }

                bool emaOk = slot.IsLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
                if (emaOk)
                    TryEnter(slot, s, bar); // "enter on FIRST completed candle" through EMA9
            }
        }

        // ==================================================================
        // Entry submission - grade (spec GRADE), sizing (GLOBAL POSITION
        // SIZING), 15m EMA confluence (S7), entry-time gate (GLOBAL RULE)
        // ==================================================================
        private void TryEnter(FbSlot slot, LtfSetup s, BarSnap bar)
        {
            // FINAL FAKE BREAKOUT EMA RULE:
            // The 15m EMA(9) is INFORMATIONAL ONLY. The entry has already been
            // confirmed by the LOWER-TIMEFRAME EMA(9) in ProcessLtf, so the 15m EMA
            // state must not gate, cancel, postpone or invalidate it here. It is only
            // recorded as context on the entry log below.
            bool confluence15m = slot.IsLong ? last15Close > last15Ema : last15Close < last15Ema;
            if (double.IsNaN(last15Close) || double.IsNaN(last15Ema)) confluence15m = false;

            if (cfg.Require15mEmaConfluence && !confluence15m)
            {
                // LEGACY research path only - never active in exact-spec mode.
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "{0} entry blocked: 15m EMA confluence failed (close {1:0.00} vs ema {2:0.00}) - LTF setup cancelled (LEGACY flag, not exact-spec)",
                    slot.IsLong ? "LONG" : "SHORT", last15Close, last15Ema));
                s.Reset();
                return;
            }

            // GLOBAL ENTRY-TIME RULE: 9:30-11:30 ET at the signal-candle close
            if (!host.IsEntryTimeAllowed(bar.EtClose))
            {
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                    "entry blocked: signal close {0:HH:mm} ET outside 9:30-11:30 window", bar.EtClose));
                s.Reset();
                if (host.IsAfterEntryCutoff(bar.EtClose)) { slot.ResetAll(); }
                return;
            }

            // V6 U9: a VBR position open at this moment does NOT block the entry -
            // the host flattens VBR first and then submits this order (handoff).
            // CanOpenPosition is only the instrument/enabled gate.
            if (!host.CanOpenPosition(StrategyId.FAKE_BREAKOUT))
            {
                host.Diag(StrategyId.FAKE_BREAKOUT, "entry blocked: trading disabled for this instrument - LTF setup cancelled");
                s.Reset();
                return;
            }

            double stop = s.StructExtreme;               // S9/S10 INITIAL STOP = structure wick
            double entryRef = bar.Close;
            double stopPts = slot.IsLong ? entryRef - stop : stop - entryRef;
            if (stopPts <= 0)
            {
                host.Diag(StrategyId.FAKE_BREAKOUT, "entry blocked: non-positive stop distance - LTF setup cancelled");
                s.Reset();
                return;
            }

            // ==============================================================
            // GRADE. Exactly ONE of the two systems below runs - never both.
            //
            // V7 (default): ES + YM cross-market confirmation at the SAME level
            //   name, on the SAME timeframe, on the SAME completed bar. This
            //   only sets grade/risk - the entry above already qualified on the
            //   MNQ rules alone and is not affected by what ES/YM do.
            // LEGACY: validity-candle A-/B+ (26%/10%), used only when the V7
            //   system is switched off or its data is unavailable.
            // ==============================================================
            int formingCandle = slot.ValidityCount + 1;
            string grade;
            double riskPct;

            if (cfg.UseCrossMarketGrading && host.CrossMarketEnabled)
            {
                CrossMarketConfirm es = host.QueryCrossMarket(ConfirmMarket.ES, slot.IsLong,
                    slot.ActiveLevelId, bar.PeriodMinutes, bar.EtClose);
                CrossMarketConfirm ym = host.QueryCrossMarket(ConfirmMarket.YM, slot.IsLong,
                    slot.ActiveLevelId, bar.PeriodMinutes, bar.EtClose);

                // USER RULE: a market that could not be EVALUATED is not a market that
                // DECLINED. There is NO legacy fallback - the trade is refused outright
                // so no legacy grade can ever be mistaken for a correlation grade.
                if (es.Unavailable || ym.Unavailable)
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                        "*** CROSS-MARKET GRADING UNAVAILABLE - ENTRY BLOCKED ***"
                        + "\n    A valid MNQ Fake Breakout qualified but could NOT be graded, and no legacy"
                        + "\n    grade is permitted. No order was submitted."
                        + "\n    direction={0} entryTf={1}m level={2} at {3:yyyy-MM-dd HH:mm} ET"
                        + "\n    ES : {4}\n    YM : {5}",
                        slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, slot.ActiveLevelId, bar.EtClose,
                        es.Reason, ym.Reason));
                    if (cfg.BlockEntryWhenCrossMarketUnavailable) { s.Reset(); return; }
                    grade = "UNGRADED"; riskPct = 0;
                }
                else
                {
                cfg.CrossMarketGrades.Resolve(es.Confirmed, ym.Confirmed, out grade, out riskPct);

                // RESEARCH-ONLY subtype. The official grade stays "A-"; the subtype
                // only records WHICH single market agreed, for later subgroup analysis.
                string subtype = "";
                if (grade == "A-") subtype = es.Confirmed ? "  A-_subtype=ES" : "  A-_subtype=YM";

                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "FAKE BREAKOUT CONFIRMATION | tradeId=(pending) direction={0} entryTf={1}m confirmBar={3:yyyy-MM-dd HH:mm} ET"
                    + " | MNQ_confirm=TRUE ES_confirm={4} YM_confirm={5} | GRADE={6} riskPct={7}{18}"
                    + "\n    MNQ_level_name={2} MNQ_level_price={8:0.00} MNQ_close={9:0.00} MNQ_ema9={10:0.00} MNQ_vector={11}"
                    + "\n    ES_level_name={12}  ES_level_price={13:0.00}  ES_confirm={4}  ES_reason={14}"
                    + "\n    YM_level_name={15}  YM_level_price={16:0.00}  YM_confirm={5}  YM_reason={17}",
                    slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, slot.ActiveLevelId, bar.EtClose,
                    es.Confirmed, ym.Confirmed, grade, riskPct,
                    slot.ActiveLevelPrice, bar.Close, bar.Ema9, bar.Vector,
                    es.LevelId, es.LevelPrice, es.Reason,
                    ym.LevelId, ym.LevelPrice, ym.Reason, subtype));
                }
            }
            else
            {
                // LEGACY grading (spec): A- = entry within FIRST eligible 15m
                // candle (26%); B+ = candles 2-4 or +2 extension (10%).
                int gradeCandle = formingCandle;
                if (cfg.GradeBasis == FbGradeBasis.FirstTradableCandle && slot.FirstTradableFormingNum > 0)
                    gradeCandle = formingCandle - slot.FirstTradableFormingNum + 1;
                grade = gradeCandle <= 1 ? "A-" : "B+";
                riskPct = grade == "A-" ? cfg.RiskPctAMinus : cfg.RiskPctBPlus;

                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "FAKE BREAKOUT CONFIRMATION | cross-market grading OFF ({0}) - using LEGACY validity-candle grade"
                    + " | direction={1} entryTf={2}m level={3} gradeCandle={4} GRADE={5} riskPct={6}",
                    cfg.UseCrossMarketGrading ? "confirmation series not attached" : "switched off in settings",
                    slot.IsLong ? "LONG" : "SHORT", bar.PeriodMinutes, slot.ActiveLevelId,
                    gradeCandle, grade, riskPct));
            }

            double balance = host.AccountBalance;
            double riskDollars, riskPerContract;
            int qty = PositionSizer.Contracts(balance, riskPct, stopPts, out riskDollars, out riskPerContract);
            if (qty < 1)
            {
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                    "entry blocked: sizing yields 0 contracts (balance={0:0.00} risk%={1} stopPts={2:0.00}) - LTF setup cancelled",
                    balance, riskPct, stopPts));
                s.Reset();
                return;
            }

            tradeSeq++;
            slot.TradeId = string.Format(CultureInfo.InvariantCulture, "FB-{0:yyyyMMdd}-{1}", bar.EtClose, tradeSeq);
            slot.Grade = grade;
            slot.RiskPct = riskPct;
            slot.RiskDollars = riskDollars;
            slot.BalanceAtEntry = balance;
            slot.EntryTf = bar.PeriodMinutes;
            slot.ValidityCandleAtEntry = formingCandle;
            slot.EntryEtTime = bar.EtClose;
            slot.IntendedEntry = entryRef;
            slot.StopPrice = stop;
            slot.StopPts = stopPts;
            slot.QtyTotal = qty;
            slot.QtyOpen = 0;      // set on fill
            slot.QtyFilled = 0;
            slot.EntryAvg = 0;
            slot.State = FbState.POSITION_OPEN;
            // S8: once a trade is entered, stop looking for another entry for this parent
            slot.Ltf1.Reset();
            slot.Ltf3.Reset();

            host.EnterPosition(StrategyId.FAKE_BREAKOUT, slot.IsLong ? TradeDirection.Long : TradeDirection.Short,
                qty, slot.EntrySignal);

            // Spec diagnostics: entry price/stop/distance/balance/risk%/contracts/etc.
            host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                "ENTRY {0} {1} tf={2}m pattern=FAKE_BREAK_RECLAIM validityCandle={3} grade={4} entryRef={5:0.00} ltfEma9={6:0.00} stop={7:0.00} stopPts={8:0.00} balance={9:0.00} risk%={10} riskDollars={11:0.00} contracts={12} tradeId={13} | context only: 15mClose={14:0.00} 15mEma9={15:0.00} 15mConfluence={16}",
                slot.IsLong ? "LONG" : "SHORT", slot.EntrySignal, bar.PeriodMinutes, formingCandle, grade,
                entryRef, bar.Ema9, stop, stopPts, balance, riskPct, riskDollars, qty, slot.TradeId,
                last15Close, last15Ema, confluence15m));
        }

        // ==================================================================
        // Position management - spec S12 + shared engine section E:
        // first target from the 18-level engine; once "broken" (configurable
        // definition) activate the 3m EMA(9) runner. Stop stays at structure.
        // ==================================================================
        private void ManagePosition(FbSlot slot, BarSnap bar)
        {
            if (slot.QtyOpen <= 0) return; // waiting for entry fill

            if (bar.PeriodMinutes == 1)
            {
                // MFE / MAE tracking (spec logging requirements)
                if (slot.IsLong)
                {
                    if (bar.High > slot.MfeExtreme) slot.MfeExtreme = bar.High;
                    if (bar.Low < slot.MaeExtreme) slot.MaeExtreme = bar.Low;
                }
                else
                {
                    if (bar.Low < slot.MfeExtreme) slot.MfeExtreme = bar.Low;
                    if (bar.High > slot.MaeExtreme) slot.MaeExtreme = bar.High;
                }

                // first-target break: Touch / 1m-close modes
                if (slot.State == FbState.POSITION_OPEN && !slot.TargetBroken && !double.IsNaN(slot.TargetPrice))
                {
                    bool broken = false;
                    if (cfg.TargetBreakMode == FbTargetBreakMode.Touch)
                        broken = slot.IsLong ? bar.High >= slot.TargetPrice : bar.Low <= slot.TargetPrice;
                    else if (cfg.TargetBreakMode == FbTargetBreakMode.OneMinuteCloseBeyond)
                        broken = slot.IsLong ? bar.Close > slot.TargetPrice : bar.Close < slot.TargetPrice;
                    if (broken) ActivateRunner(slot, bar);
                }
            }
            else if (bar.PeriodMinutes == 3)
            {
                // first-target break: 3m-close mode (default)
                if (slot.State == FbState.POSITION_OPEN && !slot.TargetBroken && !double.IsNaN(slot.TargetPrice)
                    && cfg.TargetBreakMode == FbTargetBreakMode.ThreeMinuteCloseBeyond)
                {
                    bool broken = slot.IsLong ? bar.Close > slot.TargetPrice : bar.Close < slot.TargetPrice;
                    if (broken) ActivateRunner(slot, bar);
                }

                // S12/E runner: LONG exits on completed 3m close below 3m EMA9;
                // SHORT exits on completed 3m close above 3m EMA9.
                if (slot.State == FbState.RUNNER_MODE)
                {
                    bool exit = slot.IsLong ? bar.Close < bar.Ema9 : bar.Close > bar.Ema9;
                    if (exit)
                    {
                        host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                            "RUNNER EXIT signal: 3m close {0:0.00} through 3m EMA9 {1:0.00} - exiting {2} contracts",
                            bar.Close, bar.Ema9, slot.QtyOpen));
                        host.ExitMarket(StrategyId.FAKE_BREAKOUT,
                            slot.IsLong ? TradeDirection.Long : TradeDirection.Short,
                            slot.QtyOpen, slot.RunSignal, slot.EntrySignal);
                    }
                }
            }
        }

        private void ActivateRunner(FbSlot slot, BarSnap bar)
        {
            slot.TargetBroken = true;
            slot.State = FbState.RUNNER_MODE;
            host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                "FIRST TARGET BROKEN ({0} @ {1:0.00}, mode={2}) - 3m EMA(9) runner ACTIVE (spec S12/E)",
                slot.TargetNames, slot.TargetPrice, cfg.TargetBreakMode));
        }

        // ==================================================================
        // Execution routing (called by the host strategy)
        // ==================================================================
        public void OnEntryExecution(string orderName, double price, int qty, DateTime etTime)
        {
            FbSlot slot = orderName == "FB_LONG" ? longSlot : orderName == "FB_SHORT" ? shortSlot : null;
            if (slot == null || slot.State == FbState.IDLE) return;

            slot.EntryAvg = (slot.EntryAvg * slot.QtyFilled + price * qty) / Math.Max(1, slot.QtyFilled + qty);
            slot.QtyFilled += qty;
            slot.QtyOpen += qty;

            if (slot.QtyFilled == qty) // first fill
            {
                slot.MfeExtreme = price;
                slot.MaeExtreme = price;
                // structure stop, live until cancelled (spec S9/S10 INITIAL STOP)
                host.SubmitOrUpdateStop(StrategyId.FAKE_BREAKOUT,
                    slot.IsLong ? TradeDirection.Long : TradeDirection.Short,
                    slot.QtyTotal, slot.StopPrice, slot.StopSignal, slot.EntrySignal);

                // recompute stop distance off the actual fill
                slot.StopPts = slot.IsLong ? slot.EntryAvg - slot.StopPrice : slot.StopPrice - slot.EntryAvg;

                // Shared engine section E: nearest directional level = first target
                List<TpTarget> targets = host.Levels.GetSortedTargets(
                    slot.IsLong ? TradeDirection.Long : TradeDirection.Short,
                    slot.EntryAvg, host.TpLevelEnabled, host.RoundToTick);
                if (targets.Count > 0)
                {
                    slot.TargetNames = targets[0].NameString();
                    slot.TargetPrice = targets[0].Price;
                    slot.TargetDistance = Math.Abs(targets[0].Price - slot.EntryAvg);
                    host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                        "FILLED {0} qty={1} avg={2:0.00} | first target {3} @ {4:0.00} dist={5:0.00}pts (18-level engine)",
                        orderName, qty, slot.EntryAvg, slot.TargetNames, slot.TargetPrice, slot.TargetDistance));
                }
                else
                {
                    host.Diag(StrategyId.FAKE_BREAKOUT,
                        "FILLED " + orderName + " - WARNING: no directional take-profit level available; only the structure stop manages this trade");
                }
            }
        }

        public void OnExitExecution(string orderName, double price, int qty, DateTime etTime)
        {
            FbSlot slot = orderName.EndsWith("_L") ? longSlot : orderName.EndsWith("_S") ? shortSlot : null;
            if (slot == null || !slot.HasPosition) return;

            string leg;
            if (orderName.Contains("STOP")) leg = "STOP";
            else if (orderName.Contains("HANDOFF")) leg = "HANDOFF_FLATTEN"; // V6 U9
            else leg = "RUNNER_EMA3M";
            string reason = leg == "STOP" ? "STOP_LOSS" : leg;
            ApplyExit(slot, price, qty, etTime, reason, leg);
        }

        // V6 U9: flatten this engine's open position so the OTHER strategy may enter.
        // Called by the host's handoff coordinator; the replacement entry is only
        // submitted after this fill confirms the account flat.
        public void FlattenForHandoff()
        {
            FbSlot[] slots = new FbSlot[] { longSlot, shortSlot };
            foreach (FbSlot slot in slots)
            {
                if (!slot.HasPosition || slot.QtyOpen <= 0) continue;
                host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(
                    "HANDOFF FLATTEN: exiting {0} contracts of {1} for VECTOR_BREAK_RETEST (V6 U9)",
                    slot.QtyOpen, slot.EntrySignal));
                host.ExitMarket(StrategyId.FAKE_BREAKOUT,
                    slot.IsLong ? TradeDirection.Long : TradeDirection.Short,
                    slot.QtyOpen, slot.HandoffSignal, slot.EntrySignal);
            }
        }

        public void OnSessionCloseExecution(double price, int qty, DateTime etTime)
        {
            // NT flattens the whole strategy; attribute this engine's open quantity.
            FbSlot[] slots = new FbSlot[] { longSlot, shortSlot };
            int remaining = qty;
            foreach (FbSlot slot in slots)
            {
                if (remaining <= 0) break;
                if (!slot.HasPosition || slot.QtyOpen <= 0) continue;
                int leg = Math.Min(remaining, slot.QtyOpen);
                remaining -= leg;
                ApplyExit(slot, price, leg, etTime, "SESSION_CLOSE", "SESSION_CLOSE");
            }
        }

        private void ApplyExit(FbSlot slot, double price, int qty, DateTime etTime, string reason, string legName)
        {
            slot.ExitAvg = (slot.ExitAvg * slot.ExitQtyAccum + price * qty) / Math.Max(1, slot.ExitQtyAccum + qty);
            slot.ExitQtyAccum += qty;
            slot.QtyOpen -= qty;
            if (slot.QtyOpen > 0) return; // partial fill of the exit order - wait for the rest

            double pnlPts = slot.IsLong ? slot.ExitAvg - slot.EntryAvg : slot.EntryAvg - slot.ExitAvg;
            double pnlDollars = pnlPts * PositionSizer.MnqDollarsPerPoint * slot.QtyFilled;
            double r = slot.StopPts > 0 ? pnlPts / slot.StopPts : 0;
            double mfePts = slot.IsLong ? slot.MfeExtreme - slot.EntryAvg : slot.EntryAvg - slot.MfeExtreme;
            double maePts = slot.IsLong ? slot.EntryAvg - slot.MaeExtreme : slot.MaeExtreme - slot.EntryAvg;

            TradeRecord rec = new TradeRecord();
            rec.Strategy = StrategyId.FAKE_BREAKOUT;
            rec.TradeId = slot.TradeId;
            rec.Grade = slot.Grade;
            rec.Direction = slot.IsLong ? TradeDirection.Long : TradeDirection.Short;
            rec.ParentTriggerTimeEt = slot.BreakoutEtClose;
            rec.ParentLevelName = slot.ActiveLevelId.ToString();
            rec.ParentLevelPrice = slot.ActiveLevelPrice;
            rec.ParentVector = slot.BreakoutVector.ToString();
            rec.ValidityCandleNumber = slot.ValidityCandleAtEntry;
            rec.EntryTimeframeMinutes = slot.EntryTf;
            rec.EntryPatternType = "FAKE_BREAK_RECLAIM";
            rec.EntryTimeEt = slot.EntryEtTime;
            rec.EntryPrice = slot.EntryAvg;
            rec.StopPrice = slot.StopPrice;
            rec.StopDistancePoints = slot.StopPts;
            rec.AccountBalance = slot.BalanceAtEntry;
            rec.RiskPercent = slot.RiskPct;
            rec.RiskDollars = slot.RiskDollars;
            rec.Contracts = slot.QtyFilled;
            rec.TargetLevelNames = slot.TargetNames;
            rec.TargetPrice = slot.TargetPrice;
            rec.TargetDistancePoints = slot.TargetDistance;
            rec.ExitLeg = legName;
            rec.ExitQty = slot.ExitQtyAccum;
            rec.ExitTimeEt = etTime;
            rec.ExitPrice = slot.ExitAvg;
            rec.ExitReason = reason;
            rec.PnlPoints = pnlPts;
            rec.PnlDollars = pnlDollars;
            rec.RMultiple = r;
            rec.MfePoints = mfePts;
            rec.MaePoints = maePts;
            rec.ReentryNumber = 0;                    // FB has no re-entry (spec S8)
            rec.ParentFormedPremarket = slot.ParentPremarket;
            rec.EntryFormedAfter930 = true;           // enforced structurally
            host.LogTrade(rec);
            Stats.AddClosedTrade(pnlDollars, r, mfePts, maePts);

            host.Diag(StrategyId.FAKE_BREAKOUT, string.Format(CultureInfo.InvariantCulture,
                "TRADE CLOSED {0} reason={1} exit={2:0.00} pnl={3:0.00}pts ${4:0.00} R={5:0.00} MFE={6:0.00} MAE={7:0.00}",
                slot.TradeId, reason, slot.ExitAvg, pnlPts, pnlDollars, r, mfePts, maePts));

            // S8: parent setup is finished after its one trade - back to IDLE so a
            // NEW parent breakout may start fresh later.
            slot.ResetAll();
        }
    }
}
