// ============================================================================
// MnqTwoStrategies.cs
// NinjaTrader 8 host strategy for the TWO independent MNQ-only strategies:
//   1. FAKE_BREAKOUT          (FakeBreakoutEngine.cs)
//   2. VECTOR_BREAK_RETEST    (VectorBreakRetestEngine.cs)
//
// Spec sections implemented here:
//   "CURRENT EXECUTION INSTRUMENT SCOPE — MNQ ONLY" (hard instrument gate,
//    $2/pt sizing lives in PositionSizer)
//   "CRITICAL ARCHITECTURE" (two engines, no shared setup state, StrategyId on
//    every order + log record, unique signal names FB_*/VBR_*)
//   "GLOBAL ENTRY-TIME RULE" (9:30-11:30 ET gates)
//   "IMPLEMENTATION NOTES FOR CLAUDE" (no repainting: Calculate.OnBarClose,
//    completed candles only; logging)
//
// SERIES MAP (BarsInProgress) — indices are assigned in State.Configure in
// AddDataSeries order, so they shift with the optional series:
//   0 = chart series (NEVER used for logic)
//   [ES 1m, ES 3m, QQQ 1m, QQQ 3m]  OPTIONAL V7 confirmation markets, added
//       FIRST so a same-timestamp bar is complete before MNQ decides. DATA
//       ONLY — no order is ever routed to these series.
//   1m  (entries/patterns/MFE-MAE/key-level aggregation)
//   3m  (Fake Breakout entry TF + runner)
//   15m (parent setups for both strategies)
//   1-tick (OPTIONAL, added LAST, execution granularity only — carries NO logic)
// Each engine only ever receives snapshots built inside the matching
// BarsInProgress branch, so cross-series contamination is impossible.
//
// Apply to an MNQ chart. The strategy refuses to trade any other instrument.
// ============================================================================

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies.MnqTwo;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqTwoStrategies : Strategy, IMnqHost
    {
        // ==================================================================
        // SERIES MAP — assigned in State.Configure, in AddDataSeries order.
        //
        // These were compile-time constants before V7. They are now fields
        // because the optional ES/QQQ confirmation series must be added
        // BEFORE the MNQ series. NinjaTrader processes bars that share a
        // timestamp in the order the series were added, so ES/QQQ must come
        // first for their 10:03 bar to be complete when MNQ's 10:03 bar makes
        // the entry decision. Adding them last would make every same-bar
        // confirmation arrive one bar too late.
        //
        // This is NOT lookahead: both bars close at the same instant, and the
        // detector only ever sees COMPLETED bars. The Query() call additionally
        // rejects any confirmation timestamped after the MNQ decision bar.
        // ==================================================================
        private int BipOneMin = 1;
        private int BipThreeMin = 2;
        private int BipFifteenMin = 3;
        private int BipTick = -1;             // execution-granularity series only (no logic)
        private int BipEs1 = -1, BipEs3 = -1, BipQqq1 = -1, BipQqq3 = -1;

        // Series index that ORDERS are submitted against. Signals are unaffected —
        // this only controls how finely NinjaTrader simulates fills in a backtest.
        // NT8 refuses "High" order-fill resolution for multi-series strategies and
        // instructs you to "program directly into your strategy the more granular
        // resolution you would like to simulate order fills with" — that is exactly
        // what the optional 1-tick series below does.
        // NOTE: initialized to a literal, not to BipOneMin. The series indices are
        // instance fields as of V7 and C# forbids one field initializer referencing
        // another. The real value is assigned in State.Configure either way.
        private int bipExec = 1;

        private KeyLevelEngine levels;
        private FakeBreakoutEngine fb;
        private VectorBreakRetestEngine vbr;
        private MnqLogger logger;
        private TimeZoneInfo etZone;
        private EMA ema1m, ema3m, ema15m;
        private bool instrumentOk;
        private bool instrumentWarned;
        private HandoffCoordinator handoff;   // V6 U9 strategy handoff sequencing

        // ---- V7 cross-market confirmation (FAKE_BREAKOUT grading only) ----
        // Each confirmation market gets its OWN KeyLevelEngine, so YDAY_HIGH means
        // "ES's own yesterday high" / "QQQ's own yesterday high" — MNQ prices are
        // never compared against ES or QQQ prices anywhere.
        private KeyLevelEngine esLevels, qqqLevels;
        private EMA emaEs1, emaEs3, emaQqq1, emaQqq3;
        private CrossMarketConfirmDetector esDet1, esDet3, qqqDet1, qqqDet3;
        private bool crossMarketReady;        // series attached AND carrying bars
        private int esBars1, esBars3, qqqBars1, qqqBars3;   // loaded bar counts (V7.1 diagnostic)

        // ==================================================================
        // Parameters — every flagged ambiguity is exposed here instead of
        // being silently hard-coded (spec: "If a coding rule remains
        // ambiguous, expose it as a configurable parameter").
        // ==================================================================

        #region 00. Strategy Selection
        // Each engine can be switched off independently. Disabling one simply stops
        // feeding it bars — its state machine never starts, so it can never signal,
        // size, order or hand off. The other engine is completely unaffected
        // (spec: the two engines share no setup state).
        [NinjaScriptProperty]
        [Display(Name = "Enable FAKE_BREAKOUT", GroupName = "00. Strategy Selection", Order = 1)]
        public bool EnableFakeBreakout { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable VECTOR_BREAK_RETEST", GroupName = "00. Strategy Selection", Order = 2)]
        public bool EnableVectorBreakRetest { get; set; }
        #endregion

        #region 00b. Cross-Market Confirmation (FAKE_BREAKOUT grading only)
        // ES and QQQ are CONFIRMATION MARKETS ONLY. No order is ever submitted on
        // either one — every order in this strategy is routed to the MNQ series.
        // They change the GRADE and RISK of an MNQ Fake Breakout that has already
        // qualified on the MNQ rules alone. They never create or block a trade.
        [NinjaScriptProperty]
        [Display(Name = "Enable cross-market grading (ES/QQQ)", GroupName = "00b. Cross-Market Confirmation", Order = 1)]
        public bool EnableCrossMarketConfirmation { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "ES confirmation symbol", GroupName = "00b. Cross-Market Confirmation", Order = 2)]
        public string EsSymbol { get; set; }

        // Confirmation market 2. Originally QQQ; the property name is kept so saved
        // NinjaTrader templates are not invalidated, but the slot accepts ANY symbol.
        // A futures contract (YM ##-##, RTY ##-##) needs the CME exchange day; an ETF
        // (QQQ) needs the RTH cash session. Confirm2UsesRthSession selects which.
        [NinjaScriptProperty]
        [Display(Name = "Confirmation market 2 symbol", GroupName = "00b. Cross-Market Confirmation", Order = 3)]
        public string QqqSymbol { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Market 2 is an ETF (use RTH session for its levels)", GroupName = "00b. Cross-Market Confirmation", Order = 4)]
        public bool Confirm2UsesRthSession { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Max bars from break to reclaim (confirmation markets)", GroupName = "00b. Cross-Market Confirmation", Order = 5)]
        public int CrossMarketMaxBarsBreakToReclaim { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10)]
        [Display(Name = "Confirmation lag tolerance (bars, 0 = exact same bar)", GroupName = "00b. Cross-Market Confirmation", Order = 6)]
        public int CrossMarketToleranceBars { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Risk % — A+ (ES + market 2 confirm)", GroupName = "00b. Cross-Market Confirmation", Order = 7)]
        public double CmRiskPctAPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Risk % — A- (ES only)", GroupName = "00b. Cross-Market Confirmation", Order = 8)]
        public double CmRiskPctAMinus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Risk % — B+ (market 2 only)", GroupName = "00b. Cross-Market Confirmation", Order = 9)]
        public double CmRiskPctBPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Risk % — B (neither confirms)", GroupName = "00b. Cross-Market Confirmation", Order = 10)]
        public double CmRiskPctNone { get; set; }

        // QQQ is an ETF: it has no 18:00 ET exchange day. Its key levels are built
        // from the RTH cash session only, per user specification.
        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Market 2 ETF session start (ET minutes, 570 = 09:30)", GroupName = "00b. Cross-Market Confirmation", Order = 11)]
        public int QqqSessionStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Range(1, 1440)]
        [Display(Name = "Market 2 ETF session end (ET minutes, 960 = 16:00)", GroupName = "00b. Cross-Market Confirmation", Order = 12)]
        public int QqqSessionEndMinutesEt { get; set; }

        // V7.1: makes a silent ES/QQQ data failure impossible to miss.
        //   Summary = one line per market per day (bar counts, levels, near-miss tally)
        //   Verbose = every break / rejected reclaim / expiry / confirmation (LOUD)
        [NinjaScriptProperty]
        [Display(Name = "Cross-market diagnostics (0=Off 1=Summary 2=Verbose)", GroupName = "00b. Cross-Market Confirmation", Order = 13)]
        [Range(0, 2)]
        public int CrossMarketDiagnostics { get; set; }
        #endregion

        #region 01. Session / Time
        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Entry window start (minutes ET, 570=9:30)", GroupName = "01. Session / Time", Order = 1)]
        public int EntryStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Entry window end (minutes ET, 690=11:30)", GroupName = "01. Session / Time", Order = 2)]
        public int EntryEndMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Bar times already US-Eastern (SH-6)", GroupName = "01. Session / Time", Order = 3)]
        public bool AssumeBarTimesAreEastern { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1439)]
        [Display(Name = "Exchange day start (min ET; 1080=18:00 CME session=TR time('D') for MNQ, 0=lit. midnight)", GroupName = "01. Session / Time", Order = 4)]
        public int DayStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10079)]
        [Display(Name = "Week start (minutes ET from Sunday 00:00, 1080=Sun 18:00)", GroupName = "01. Session / Time", Order = 5)]
        public int WeekStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Psy level type (TR overridePsyType; Forex confirmed for MNQ)", GroupName = "01. Session / Time", Order = 6)]
        public PsyLevelType PsyLevelTypeParam { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "COMPAT: evaluate psy session on 4H grid (unverified; keep FALSE)", GroupName = "01. Session / Time", Order = 8)]
        public bool PsyUse4HourGridParam { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "PLATFORM flatten on session close (NOT a strategy rule; V5 Fix 6 default OFF)", GroupName = "01. Session / Time", Order = 7)]
        public bool ExitOnSessionCloseEnabled { get; set; }
        #endregion

        #region 02. Account / Risk
        [NinjaScriptProperty]
        [Display(Name = "Live: use account cash value (SH-3)", GroupName = "02. Account / Risk", Order = 1)]
        public bool UseAccountCashValueLive { get; set; }

        [NinjaScriptProperty]
        [Range(1, double.MaxValue)]
        [Display(Name = "Backtest starting balance $", GroupName = "02. Account / Risk", Order = 2)]
        public double SimAccountBalance { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Backtest: compound realized PnL", GroupName = "02. Account / Risk", Order = 3)]
        public bool CompoundSimBalance { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 100)]
        [Display(Name = "A+ risk % (VBR)", GroupName = "02. Account / Risk", Order = 4)]
        public double RiskPctAPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 100)]
        [Display(Name = "A- risk % (FB first candle)", GroupName = "02. Account / Risk", Order = 5)]
        public double RiskPctAMinus { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 100)]
        [Display(Name = "B+ risk % (FB candles 2-6)", GroupName = "02. Account / Risk", Order = 6)]
        public double RiskPctBPlus { get; set; }

        #endregion

        #region 03. Fake Breakout
        [NinjaScriptProperty]
        [Display(Name = "LEGACY research: require prior 15m close inside level (V5 Fix 2: keep FALSE)", GroupName = "03. Fake Breakout", Order = 1)]
        public bool FbRequirePriorCloseInside { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "LEGACY: invalid 15m reclaim cancels setup (V6 U4: keep FALSE)", GroupName = "03. Fake Breakout", Order = 2)]
        public bool FbInvalidReclaimCancelsSetup { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "LEGACY: require 15m reclaim before 1m/3m scan (V6 U5: keep FALSE)", GroupName = "03. Fake Breakout", Order = 3)]
        public bool FbRequire15mReclaimBeforeLtfEntry { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "LEGACY: require 15m EMA confluence (FINAL RULE: keep FALSE)", GroupName = "03. Fake Breakout", Order = 4)]
        public bool FbRequire15mEmaConfluence { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "First-target break definition (V6 U1: 1m close beyond)", GroupName = "03. Fake Breakout", Order = 5)]
        public FbTargetBreakMode FbTargetBreakModeParam { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "A- grade basis (V6: first actually-eligible entry candle)", GroupName = "03. Fake Breakout", Order = 6)]
        public FbGradeBasis FbGradeBasisParam { get; set; }
        #endregion

        #region 04. Vector Break Retest
        [NinjaScriptProperty]
        [Display(Name = "LEGACY research: vector must cross through Daily Open (V5 Fix 3: keep FALSE)", GroupName = "04. Vector Break Retest", Order = 1)]
        public bool VbrRequireCrossThrough { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "LEGACY research: new vector replaces active flat setup (V5 Fix 5: keep FALSE)", GroupName = "04. Vector Break Retest", Order = 2)]
        public bool VbrRetriggerReplacesSetup { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Target 'reached' definition (V6 U2: wick/touch)", GroupName = "04. Vector Break Retest", Order = 8)]
        public TargetReachedMode VbrTargetReachedModeParam { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Pattern B waits for EMA after reclaim (V6 U6: keep TRUE)", GroupName = "04. Vector Break Retest", Order = 3)]
        public bool VbrPatternBWaitForEma { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "LEGACY: re-entry only following candle (V6 U7 rolling: keep FALSE)", GroupName = "04. Vector Break Retest", Order = 4)]
        public bool VbrReentryScanOnlyFollowingCandle { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "LEGACY: single contract becomes runner (V6 U8: keep FALSE)", GroupName = "04. Vector Break Retest", Order = 6)]
        public bool VbrSingleContractBecomesRunner { get; set; }

        [NinjaScriptProperty]
        [Range(1, 500)]
        [Display(Name = "Chain max distance points (spec: 50)", GroupName = "04. Vector Break Retest", Order = 7)]
        public double VbrChainMaxDistancePoints { get; set; }
        #endregion

        #region 05. Take-Profit Levels (18 selectable)
        [NinjaScriptProperty] [Display(Name = "M0", GroupName = "05. Take-Profit Levels", Order = 1)] public bool TpEnableM0 { get; set; }
        [NinjaScriptProperty] [Display(Name = "M1", GroupName = "05. Take-Profit Levels", Order = 2)] public bool TpEnableM1 { get; set; }
        [NinjaScriptProperty] [Display(Name = "M2", GroupName = "05. Take-Profit Levels", Order = 3)] public bool TpEnableM2 { get; set; }
        [NinjaScriptProperty] [Display(Name = "M3", GroupName = "05. Take-Profit Levels", Order = 4)] public bool TpEnableM3 { get; set; }
        [NinjaScriptProperty] [Display(Name = "M4", GroupName = "05. Take-Profit Levels", Order = 5)] public bool TpEnableM4 { get; set; }
        [NinjaScriptProperty] [Display(Name = "M5", GroupName = "05. Take-Profit Levels", Order = 6)] public bool TpEnableM5 { get; set; }
        [NinjaScriptProperty] [Display(Name = "PP", GroupName = "05. Take-Profit Levels", Order = 7)] public bool TpEnablePP { get; set; }
        [NinjaScriptProperty] [Display(Name = "Daily Open", GroupName = "05. Take-Profit Levels", Order = 8)] public bool TpEnableDailyOpen { get; set; }
        [NinjaScriptProperty] [Display(Name = "YDay High", GroupName = "05. Take-Profit Levels", Order = 9)] public bool TpEnableYdayHigh { get; set; }
        [NinjaScriptProperty] [Display(Name = "YDay Low", GroupName = "05. Take-Profit Levels", Order = 10)] public bool TpEnableYdayLow { get; set; }
        [NinjaScriptProperty] [Display(Name = "LWeek High", GroupName = "05. Take-Profit Levels", Order = 11)] public bool TpEnableLweekHigh { get; set; }
        [NinjaScriptProperty] [Display(Name = "LWeek Low", GroupName = "05. Take-Profit Levels", Order = 12)] public bool TpEnableLweekLow { get; set; }
        [NinjaScriptProperty] [Display(Name = "R1", GroupName = "05. Take-Profit Levels", Order = 13)] public bool TpEnableR1 { get; set; }
        [NinjaScriptProperty] [Display(Name = "R3", GroupName = "05. Take-Profit Levels", Order = 14)] public bool TpEnableR3 { get; set; }
        [NinjaScriptProperty] [Display(Name = "S1", GroupName = "05. Take-Profit Levels", Order = 15)] public bool TpEnableS1 { get; set; }
        [NinjaScriptProperty] [Display(Name = "S2", GroupName = "05. Take-Profit Levels", Order = 16)] public bool TpEnableS2 { get; set; }
        [NinjaScriptProperty] [Display(Name = "Psy High", GroupName = "05. Take-Profit Levels", Order = 17)] public bool TpEnablePsyHigh { get; set; }
        [NinjaScriptProperty] [Display(Name = "Psy Low", GroupName = "05. Take-Profit Levels", Order = 18)] public bool TpEnablePsyLow { get; set; }
        [NinjaScriptProperty] [Display(Name = "VWAP (session)", GroupName = "05. Take-Profit Levels", Order = 19)] public bool TpEnableVwap { get; set; }
        [NinjaScriptProperty] [Display(Name = "VWAP band high", GroupName = "05. Take-Profit Levels", Order = 20)] public bool TpEnableVwapBandHigh { get; set; }
        [NinjaScriptProperty] [Display(Name = "VWAP band low", GroupName = "05. Take-Profit Levels", Order = 21)] public bool TpEnableVwapBandLow { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10)]
        [Display(Name = "VWAP band multiplier (TradingView Band 1 default = 1.0)", GroupName = "05. Take-Profit Levels", Order = 22)]
        public double VwapBandMultiplierParam { get; set; }
        #endregion

        #region 06. Logging
        [NinjaScriptProperty]
        [Display(Name = "Write CSV trade log", GroupName = "06. Logging", Order = 1)]
        public bool WriteCsvTradeLog { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Use 1-tick execution series (accurate backtest stop fills)", GroupName = "07. Execution", Order = 1)]
        public bool UseTickExecutionSeries { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Verbose diagnostics", GroupName = "06. Logging", Order = 2)]
        public bool VerboseDiagnostics { get; set; }

        // V5 Fix 4 requirement: print all 18 target levels for a selected
        // historical date so they can be compared with the Traders Reality
        // TradingView indicator. Format yyyy-MM-dd (ET date); empty = off.
        [NinjaScriptProperty]
        [Display(Name = "Print 18 levels on ET date (yyyy-MM-dd, empty=off)", GroupName = "06. Logging", Order = 3)]
        public string PrintLevelsDiagnosticDate { get; set; }
        #endregion

        // ==================================================================
        // Lifecycle
        // ==================================================================
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqTwoStrategies";
                Description = "Two independent MNQ-only strategies: FAKE_BREAKOUT + VECTOR_BREAK_RETEST (Traders Reality vectors/levels)";
                // Spec: "Use completed candles for all signal decisions" — no repainting.
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.UniqueEntries; // FB_* and VBR_* independent
                // V5 Fix 6: 11:30 ET is a NEW-ENTRY cutoff only; no strategy-level
                // forced flatten. Platform session-close exit defaults OFF.
                IsExitOnSessionCloseStrategy = false;
                ExitOnSessionCloseSeconds = 30;
                BarsRequiredToTrade = 30;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                IsInstantiatedOnEachOptimizationIteration = true;

                // ---- defaults ----
                EnableFakeBreakout = true;
                EnableVectorBreakRetest = true;   // ON by default; switch OFF for a pure FB backtest

                // ---- V7 cross-market confirmation ----
                EnableCrossMarketConfirmation = true;
                EsSymbol = "ES ##-##";            // NT8 front-month syntax
                QqqSymbol = "YM ##-##";       // confirmation market 2 (Dow). Data only — never traded.
                Confirm2UsesRthSession = false;  // YM is CME futures: same 18:00 ET exchange day as MNQ/ES
                CrossMarketMaxBarsBreakToReclaim = 4;   // user-specified
                CrossMarketToleranceBars = 0;           // exact same completed bar
                CmRiskPctAPlus = 30.0;                  // ES + QQQ
                CmRiskPctAMinus = 10.0;                 // ES only
                CmRiskPctBPlus = 5.0;                   // QQQ only
                CmRiskPctNone = 5.0;                    // neither (user-specified)
                QqqSessionStartMinutesEt = 570;         // 09:30 ET
                QqqSessionEndMinutesEt = 960;           // 16:00 ET
                CrossMarketDiagnostics = 1;             // Summary

                EntryStartMinutesEt = 570;      // 9:30 ET
                EntryEndMinutesEt = 690;        // 11:30 ET
                AssumeBarTimesAreEastern = false;
                DayStartMinutesEt = 1080;       // 18:00 ET = CME exchange-day open = TR time('D') boundary for MNQ (V5 Fix 4A)
                WeekStartMinutesEt = 1080;      // Sunday 18:00 ET futures week open (TradingView weekly bar for MNQ)
                PsyLevelTypeParam = PsyLevelType.Forex;  // user-confirmed for MNQ (TR overridePsyType path)
                PsyUse4HourGridParam = false;            // compat only — see KeyLevelEngine notes
                ExitOnSessionCloseEnabled = false;      // V5 Fix 6

                UseAccountCashValueLive = true;
                SimAccountBalance = 5000;
                CompoundSimBalance = true;
                RiskPctAPlus = 50;              // spec GLOBAL POSITION SIZING
                RiskPctAMinus = 26;
                RiskPctBPlus = 10;

                FbRequirePriorCloseInside = false;          // V5 Fix 2 (legacy, keep FALSE)
                FbInvalidReclaimCancelsSetup = false;
                FbRequire15mReclaimBeforeLtfEntry = false;   // V6 U5
                FbRequire15mEmaConfluence = false;          // FINAL FB EMA RULE: 15m EMA is context only
                FbTargetBreakModeParam = FbTargetBreakMode.OneMinuteCloseBeyond; // V6 U1
                FbGradeBasisParam = FbGradeBasis.FirstTradableCandle; // V5 Fix 7

                VbrRequireCrossThrough = false;             // V5 Fix 3 (legacy, keep FALSE)
                VbrRetriggerReplacesSetup = false;          // V5 Fix 5 (legacy, keep FALSE)
                VbrTargetReachedModeParam = TargetReachedMode.IntrabarTouch;
                VbrPatternBWaitForEma = true;                // V6 U6
                VbrReentryScanOnlyFollowingCandle = false;   // V6 U7 rolling
                VbrSingleContractBecomesRunner = false;      // V6 U8
                VbrChainMaxDistancePoints = 50;

                TpEnableM0 = true; TpEnableM1 = true; TpEnableM2 = true; TpEnableM3 = true;
                TpEnableM4 = true; TpEnableM5 = true; TpEnablePP = true; TpEnableDailyOpen = true;
                TpEnableYdayHigh = true; TpEnableYdayLow = true; TpEnableLweekHigh = true;
                TpEnableLweekLow = true; TpEnableR1 = true; TpEnableR3 = true; TpEnableS1 = true;
                TpEnableS2 = true; TpEnablePsyHigh = true; TpEnablePsyLow = true;

                WriteCsvTradeLog = true;
                VerboseDiagnostics = true;
                UseTickExecutionSeries = true;   // NT8 multi-series fill granularity
                PrintLevelsDiagnosticDate = "";
            }
            else if (State == State.Configure)
            {
                int next = 1;   // BarsInProgress 0 is the chart series

                // ---- V7 confirmation series FIRST -------------------------------
                // Added ahead of the MNQ series so that when ES/QQQ and MNQ all
                // close a bar on the same timestamp, the confirmation markets are
                // processed first and their completed bar is available to the MNQ
                // entry decision on that same timestamp. No orders are ever routed
                // to these series.
                if (EnableCrossMarketConfirmation)
                {
                    AddDataSeries(EsSymbol, BarsPeriodType.Minute, 1, MarketDataType.Last);
                    BipEs1 = next++;
                    AddDataSeries(EsSymbol, BarsPeriodType.Minute, 3, MarketDataType.Last);
                    BipEs3 = next++;
                    AddDataSeries(QqqSymbol, BarsPeriodType.Minute, 1, MarketDataType.Last);
                    BipQqq1 = next++;
                    AddDataSeries(QqqSymbol, BarsPeriodType.Minute, 3, MarketDataType.Last);
                    BipQqq3 = next++;
                }

                // Multi-timeframe architecture (spec: 15m parent, 3m/1m entries).
                AddDataSeries(BarsPeriodType.Minute, 1);
                BipOneMin = next++;
                AddDataSeries(BarsPeriodType.Minute, 3);
                BipThreeMin = next++;
                AddDataSeries(BarsPeriodType.Minute, 15);
                BipFifteenMin = next++;

                // Optional execution series (added LAST so the indices above never move).
                // It carries NO strategy logic — OnBarUpdate ignores it entirely.
                // Its only job is to give the backtester tick-by-tick granularity for
                // entry fills and, critically, for the structure stops.
                if (UseTickExecutionSeries)
                {
                    AddDataSeries(BarsPeriodType.Tick, 1);
                    BipTick = next++;
                    bipExec = BipTick;
                }
                else
                {
                    bipExec = BipOneMin;
                }

                IsExitOnSessionCloseStrategy = ExitOnSessionCloseEnabled;
            }
            else if (State == State.DataLoaded)
            {
                // ---- MNQ-ONLY enforcement (spec: "Do NOT submit NQ contracts") ----
                string master = Instrument != null && Instrument.MasterInstrument != null
                    ? Instrument.MasterInstrument.Name : "";
                instrumentOk = master.Equals("MNQ", StringComparison.OrdinalIgnoreCase);

                try { etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception)
                {
                    try { etZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
                    catch (Exception) { etZone = null; }
                }

                levels = new KeyLevelEngine();
                levels.DayStartMinutesEt = DayStartMinutesEt;
                levels.WeekStartMinutesEt = WeekStartMinutesEt;
                levels.PsyType = PsyLevelTypeParam;
                levels.PsyUse4HourGrid = PsyUse4HourGridParam;
                levels.VwapBandMultiplier = VwapBandMultiplierParam;

                // ---- V7: each confirmation market keeps its OWN key levels ----
                if (EnableCrossMarketConfirmation)
                {
                    // ES is CME, same 18:00 ET exchange day as MNQ — identical config.
                    esLevels = new KeyLevelEngine();
                    esLevels.DayStartMinutesEt = DayStartMinutesEt;
                    esLevels.WeekStartMinutesEt = WeekStartMinutesEt;

                    // QQQ is an ETF with no 18:00 ET exchange day. Per user
                    // specification its levels come from the RTH cash session only,
                    // so the day/week roll is calendar-based and the session filter
                    // discards everything outside 09:30-16:00 ET.
                    qqqLevels = new KeyLevelEngine();
                    if (Confirm2UsesRthSession)
                    {
                        // ETF (QQQ): no exchange day, so calendar roll + RTH-only aggregation.
                        qqqLevels.DayStartMinutesEt = 0;
                        qqqLevels.WeekStartMinutesEt = 0;
                        qqqLevels.SessionFilterEnabled = true;
                        qqqLevels.SessionFilterStartMinutesEt = QqqSessionStartMinutesEt;
                        qqqLevels.SessionFilterEndMinutesEt = QqqSessionEndMinutesEt;
                    }
                    else
                    {
                        // CME futures (YM/RTY): identical exchange day to MNQ and ES,
                        // so its YDAY/LWEEK levels roll on the same 18:00 ET boundary.
                        qqqLevels.DayStartMinutesEt = DayStartMinutesEt;
                        qqqLevels.WeekStartMinutesEt = WeekStartMinutesEt;
                        qqqLevels.SessionFilterEnabled = false;
                    }

                    esDet1 = new CrossMarketConfirmDetector(ConfirmMarket.ES, 1, esLevels);
                    esDet3 = new CrossMarketConfirmDetector(ConfirmMarket.ES, 3, esLevels);
                    qqqDet1 = new CrossMarketConfirmDetector(ConfirmMarket.QQQ, 1, qqqLevels);
                    qqqDet3 = new CrossMarketConfirmDetector(ConfirmMarket.QQQ, 3, qqqLevels);
                    foreach (CrossMarketConfirmDetector d in new CrossMarketConfirmDetector[] { esDet1, esDet3, qqqDet1, qqqDet3 })
                    {
                        d.MaxBarsBreakToReclaim = CrossMarketMaxBarsBreakToReclaim;
                        d.SessionStartMinutesEt = EntryStartMinutesEt;
                    }
                    esDet1.Label = EsSymbol; esDet3.Label = EsSymbol;
                    qqqDet1.Label = QqqSymbol; qqqDet3.Label = QqqSymbol;
                    // V7.1 FIX. The previous check only proved the series were ATTACHED.
                    // A series with ZERO loaded bars passed it, which is how an entire
                    // backtest was graded off ES/QQQ levels that were permanently NaN.
                    // Readiness now requires every confirmation series to actually
                    // carry bars, and the counts are printed either way.
                    bool attached = BipEs1 > 0 && BipEs3 > 0 && BipQqq1 > 0 && BipQqq3 > 0
                        && BarsArray.Length > BipQqq3
                        && BarsArray[BipEs1] != null && BarsArray[BipEs3] != null
                        && BarsArray[BipQqq1] != null && BarsArray[BipQqq3] != null;
                    if (attached)
                    {
                        esBars1 = BarsArray[BipEs1].Count; esBars3 = BarsArray[BipEs3].Count;
                        qqqBars1 = BarsArray[BipQqq1].Count; qqqBars3 = BarsArray[BipQqq3].Count;
                    }
                    crossMarketReady = attached && esBars1 > 0 && esBars3 > 0 && qqqBars1 > 0 && qqqBars3 > 0;

                    if (CrossMarketDiagnostics > 0)
                    {
                        esDet1.Diag = CmDiag; esDet3.Diag = CmDiag;
                        qqqDet1.Diag = CmDiag; qqqDet3.Diag = CmDiag;
                        bool verbose = CrossMarketDiagnostics >= 2;
                        esDet1.VerboseEvents = verbose; esDet3.VerboseEvents = verbose;
                        qqqDet1.VerboseEvents = verbose; qqqDet3.VerboseEvents = verbose;
                    }
                }

                FbConfig fbCfg = new FbConfig();
                fbCfg.RiskPctAMinus = RiskPctAMinus;
                fbCfg.RiskPctBPlus = RiskPctBPlus;
                fbCfg.RequirePriorCloseInside = FbRequirePriorCloseInside;
                fbCfg.InvalidReclaimCancelsSetup = FbInvalidReclaimCancelsSetup;
                fbCfg.Require15mReclaimBeforeLtfEntry = FbRequire15mReclaimBeforeLtfEntry;
                fbCfg.Require15mEmaConfluence = FbRequire15mEmaConfluence;
                fbCfg.TargetBreakMode = FbTargetBreakModeParam;
                fbCfg.GradeBasis = FbGradeBasisParam;
                fbCfg.UseCrossMarketGrading = EnableCrossMarketConfirmation;
                fbCfg.CrossMarketToleranceBars = CrossMarketToleranceBars;
                fbCfg.CrossMarketGrades.RiskPctAPlus = CmRiskPctAPlus;
                fbCfg.CrossMarketGrades.RiskPctAMinus = CmRiskPctAMinus;
                fbCfg.CrossMarketGrades.RiskPctBPlus = CmRiskPctBPlus;
                fbCfg.CrossMarketGrades.RiskPctNone = CmRiskPctNone;
                fb = new FakeBreakoutEngine(this, fbCfg);

                VbrConfig vbrCfg = new VbrConfig();
                vbrCfg.RiskPctAPlus = RiskPctAPlus;
                vbrCfg.RequireCrossThrough = VbrRequireCrossThrough;
                vbrCfg.RetriggerReplacesActiveSetup = VbrRetriggerReplacesSetup;
                vbrCfg.PatternBWaitForEma = VbrPatternBWaitForEma;
                vbrCfg.ReentryScanOnlyFollowingCandle = VbrReentryScanOnlyFollowingCandle;
                vbrCfg.SingleContractBecomesRunner = VbrSingleContractBecomesRunner;
                vbrCfg.ChainMaxDistancePoints = VbrChainMaxDistancePoints;
                vbrCfg.TargetReached = VbrTargetReachedModeParam;
                vbr = new VectorBreakRetestEngine(this, vbrCfg);

                // V6 U9: shared handoff coordinator (same class the tests exercise)
                handoff = new HandoffCoordinator(StrategyHasPosition, FlattenStrategy,
                    SubmitEntryOrder, delegate(StrategyId sid, string msg) { Diag(sid, msg); });

                string csvPath = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                    string.Format("MnqTwoStrategies_trades_{0:yyyyMMdd_HHmmss}.csv", DateTime.Now));
                logger = new MnqLogger(PrintLine, csvPath, WriteCsvTradeLog);

                // Spec §3 (FB) / §1 (VBR): normal EMA(close, 9) per timeframe.
                ema1m = EMA(BarsArray[BipOneMin], 9);
                ema3m = EMA(BarsArray[BipThreeMin], 9);
                ema15m = EMA(BarsArray[BipFifteenMin], 9);

                if (crossMarketReady)
                {
                    emaEs1 = EMA(BarsArray[BipEs1], 9);
                    emaEs3 = EMA(BarsArray[BipEs3], 9);
                    emaQqq1 = EMA(BarsArray[BipQqq1], 9);
                    emaQqq3 = EMA(BarsArray[BipQqq3], 9);
                }

                PrintLine(string.Format("MnqTwoStrategies: FAKE_BREAKOUT={0}, VECTOR_BREAK_RETEST={1}",
                    EnableFakeBreakout ? "ENABLED" : "DISABLED",
                    EnableVectorBreakRetest ? "ENABLED" : "DISABLED"));

                if (!EnableVectorBreakRetest)
                    PrintLine("VECTOR BREAK RETEST DISABLED");

                if (!EnableCrossMarketConfirmation)
                    PrintLine("CROSS-MARKET CONFIRMATION DISABLED — FAKE_BREAKOUT falls back to LEGACY validity-candle grading (A- 26% / B+ 10%)");
                else if (!crossMarketReady)
                {
                    PrintLine("**********************************************************************");
                    PrintLine("*** CROSS-MARKET CONFIRMATION IS ENABLED BUT UNUSABLE — NO GRADING ***");
                    PrintLine("**********************************************************************");
                    PrintLine(string.Format(CultureInfo.InvariantCulture,
                        "  bars loaded:  ES('{0}') 1m={1} 3m={2}   |   QQQ('{3}') 1m={4} 3m={5}",
                        EsSymbol, esBars1, esBars3, QqqSymbol, qqqBars1, qqqBars3));
                    if (esBars1 == 0 || esBars3 == 0)
                        PrintLine("  -> ES delivered ZERO bars. Open a 1-minute chart of '" + EsSymbol
                            + "' over this date range; if it is blank, your data feed has no history for it.");
                    if (qqqBars1 == 0 || qqqBars3 == 0)
                        PrintLine("  -> Confirmation market 2 ('" + QqqSymbol + "') delivered ZERO bars. If this is an ETF "
                            + "(QQQ), futures-only feeds carry no equities and will always report 0 — switch it to a "
                            + "CME futures symbol such as YM ##-## and untick the ETF session box.");
                    PrintLine("  A+/A-/B+/B grades CANNOT be produced. Every FAKE_BREAKOUT trade will use the");
                    PrintLine("  LEGACY validity-candle grade instead, and will say so on its entry line.");
                    PrintLine("**********************************************************************");
                }
                else
                    PrintLine(string.Format(CultureInfo.InvariantCulture,
                        "CROSS-MARKET CONFIRMATION ENABLED — ES='{0}' QQQ='{1}' | grades: A+={2}% (ES+QQQ), A-={3}% (ES only), B+={4}% (QQQ only), B={5}% (neither) "
                        + "| reclaim window={6} bars, lag tolerance={7} bar(s) | ORDERS ARE MNQ-ONLY"
                        + "\n  bars loaded: ES 1m={8} 3m={9} | QQQ 1m={10} 3m={11}"
                        + "\n  NOTE: levels need >=2 sessions of each market's own history before they can be computed.",
                        EsSymbol, QqqSymbol, CmRiskPctAPlus, CmRiskPctAMinus, CmRiskPctBPlus, CmRiskPctNone,
                        CrossMarketMaxBarsBreakToReclaim, CrossMarketToleranceBars,
                        esBars1, esBars3, qqqBars1, qqqBars3));

                if (!instrumentOk)
                    PrintLine("MnqTwoStrategies ERROR: instrument '" + master
                        + "' is not MNQ. Spec is MNQ-ONLY — all trading disabled. Apply this strategy to an MNQ chart.");
            }
            else if (State == State.Terminated)
            {
                if (fb != null && logger != null)
                {
                    PrintLine("================ FINAL STATISTICS ================");
                    PrintLine(EnableFakeBreakout
                        ? fb.Stats.Summary("FAKE_BREAKOUT")
                        : "[FAKE_BREAKOUT] DISABLED — did not trade");
                    PrintLine(EnableVectorBreakRetest
                        ? vbr.Stats.Summary("VECTOR_BREAK_RETEST")
                        : "[VECTOR_BREAK_RETEST] DISABLED — did not trade");
                }
                if (logger != null) { logger.Close(); logger = null; }
            }
        }

        // ==================================================================
        // Bar dispatch — strict BarsInProgress separation (spec requirement:
        // 15m/3m/1m signals can never use data from the wrong series).
        // ==================================================================
        protected override void OnBarUpdate()
        {
            if (!instrumentOk)
            {
                if (!instrumentWarned) { instrumentWarned = true; }
                return;
            }
            if (fb == null || vbr == null) return;

            // ==============================================================
            // V7 CONFIRMATION SERIES — data only. These branches build ES/QQQ
            // key levels and run their fake-break detectors. They never call
            // fb/vbr, never size, and never submit an order of any kind.
            // ==============================================================
            if (crossMarketReady && (BarsInProgress == BipEs1 || BarsInProgress == BipEs3
                                     || BarsInProgress == BipQqq1 || BarsInProgress == BipQqq3))
            {
                bool isEs = BarsInProgress == BipEs1 || BarsInProgress == BipEs3;
                int bip = BarsInProgress;

                // 1m series maintains that market's own key levels
                if (bip == BipEs1 || bip == BipQqq1)
                {
                    if (CurrentBars[bip] < 1) return;
                    KeyLevelEngine kl = isEs ? esLevels : qqqLevels;
                    DateTime cEtClose = ToEt(Times[bip][0]);
                    bool cNewDay = kl.OnOneMinuteBar(cEtClose.AddMinutes(-1), cEtClose,
                        ToUtc(Times[bip][0]).AddMinutes(-1),
                        Opens[bip][0], Highs[bip][0], Lows[bip][0], Closes[bip][0], Volumes[bip][0]);
                    if (cNewDay)
                    {
                        if (isEs) { esDet1.OnNewDay(); esDet3.OnNewDay(); }
                        else { qqqDet1.OnNewDay(); qqqDet3.OnNewDay(); }
                        if (CrossMarketDiagnostics > 0) EmitCrossMarketDayReport(isEs, cEtClose);
                    }
                }

                if (CurrentBars[bip] < 11) return;   // vector needs 10 prior completed candles
                cmDiagTime = ToEt(Times[bip][0]);
                int periodMin = (bip == BipEs1 || bip == BipQqq1) ? 1 : 3;
                EMA e = bip == BipEs1 ? emaEs1 : bip == BipEs3 ? emaEs3 : bip == BipQqq1 ? emaQqq1 : emaQqq3;
                BarSnap cs = BuildSnap(bip, periodMin, e[0]);
                if (bip == BipEs1) esDet1.OnBar(cs);
                else if (bip == BipEs3) esDet3.OnBar(cs);
                else if (bip == BipQqq1) qqqDet1.OnBar(cs);
                else qqqDet3.OnBar(cs);
                return;   // never falls through to any MNQ trading path
            }

            if (BarsInProgress == BipOneMin)
            {
                if (CurrentBars[BipOneMin] < 1) return;

                // key-level aggregation always runs (needs full history)
                DateTime etClose = ToEt(Times[BipOneMin][0]);
                DateTime etOpen = etClose.AddMinutes(-1);
                DateTime utcOpen = ToUtc(Times[BipOneMin][0]).AddMinutes(-1); // psy sessions are GMT-defined (TR source)
                bool newDay = levels.OnOneMinuteBar(etOpen, etClose, utcOpen,
                    Opens[BipOneMin][0], Highs[BipOneMin][0], Lows[BipOneMin][0], Closes[BipOneMin][0],
                    Volumes[BipOneMin][0]);
                MaybePrintLevelsDiagnostic(etClose);
                if (newDay)
                {
                    if (VerboseDiagnostics && logger != null)
                        logger.DiagGlobal(etClose, string.Format(CultureInfo.InvariantCulture,
                            "NEW EXCHANGE DAY — DailyOpen={0:0.00} YH={1:0.00} YL={2:0.00} LWH={3:0.00} LWL={4:0.00} PP={5:0.00}{6}",
                            levels.DailyOpen, levels.YdayHigh, levels.YdayLow, levels.LweekHigh, levels.LweekLow, levels.PP,
                            crossMarketReady
                                ? string.Format(CultureInfo.InvariantCulture,
                                    "\n    {8,-10} YH={0} YL={1} LWH={2} LWL={3}\n    {9,-10} YH={4} YL={5} LWH={6} LWL={7}",
                                    Fmt(esLevels.YdayHigh), Fmt(esLevels.YdayLow), Fmt(esLevels.LweekHigh), Fmt(esLevels.LweekLow),
                                    Fmt(qqqLevels.YdayHigh), Fmt(qqqLevels.YdayLow), Fmt(qqqLevels.LweekHigh), Fmt(qqqLevels.LweekLow),
                                    EsSymbol, QqqSymbol)
                                : ""));
                    if (EnableFakeBreakout) fb.OnNewDay(etClose);
                    if (EnableVectorBreakRetest) vbr.OnNewDay(etClose);
                }

                if (CurrentBars[BipOneMin] < 11) return; // vector needs previous 10 completed candles
                BarSnap snap = BuildSnap(BipOneMin, 1, ema1m[0]);
                if (EnableFakeBreakout) fb.OnOneMinuteBar(snap);
                if (EnableVectorBreakRetest) vbr.OnOneMinuteBar(snap);
            }
            else if (BarsInProgress == BipThreeMin)
            {
                if (CurrentBars[BipThreeMin] < 11) return;
                if (!EnableFakeBreakout) return;   // 3m series serves FAKE_BREAKOUT only
                BarSnap snap = BuildSnap(BipThreeMin, 3, ema3m[0]);
                fb.OnThreeMinuteBar(snap);
                // VECTOR_BREAK_RETEST uses 15m + 1m ONLY (spec §1) — never fed 3m data.
            }
            else if (BarsInProgress == BipFifteenMin)
            {
                if (CurrentBars[BipFifteenMin] < 11) return;
                BarSnap snap = BuildSnap(BipFifteenMin, 15, ema15m[0]);
                double prev15Close = CurrentBars[BipFifteenMin] >= 1 ? Closes[BipFifteenMin][1] : double.NaN;
                if (EnableFakeBreakout) fb.OnFifteenMinuteBar(snap, prev15Close);
                if (EnableVectorBreakRetest) vbr.OnFifteenMinuteBar(snap, prev15Close);
            }
        }

        // Build the completed-candle snapshot for the CURRENT BarsInProgress
        // series only. Vector math per spec: previous 10 completed candles.
        private BarSnap BuildSnap(int bip, int periodMinutes, double emaValue)
        {
            double avgVol = 0;
            double highestSpread = 0;
            for (int i = 1; i <= 10; i++)
            {
                avgVol += Volumes[bip][i];
                double spread = Volumes[bip][i] * (Highs[bip][i] - Lows[bip][i]);
                if (spread > highestSpread) highestSpread = spread;
            }
            avgVol /= 10.0;

            BarSnap s = new BarSnap();
            s.EtClose = ToEt(Times[bip][0]);
            s.EtOpen = s.EtClose.AddMinutes(-periodMinutes);
            s.Open = Opens[bip][0];
            s.High = Highs[bip][0];
            s.Low = Lows[bip][0];
            s.Close = Closes[bip][0];
            s.Volume = Volumes[bip][0];
            s.Vector = VectorClassifier.Classify(s.Open, s.High, s.Low, s.Close, s.Volume, avgVol, highestSpread);
            s.Ema9 = emaValue;
            s.PeriodMinutes = periodMinutes;
            return s;
        }

        // ==================================================================
        // Execution routing — order names carry the StrategyId prefix, so
        // fills can never be attributed to the wrong engine.
        // ==================================================================
        protected override void OnExecutionUpdate(Execution execution, string executionId, double price,
            int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution == null || execution.Order == null || fb == null || vbr == null) return;
            string name = execution.Order.Name;
            DateTime etTime = ToEt(time);

            if (name == "FB_LONG" || name == "FB_SHORT")
                fb.OnEntryExecution(name, price, quantity, etTime);
            else if (name.StartsWith("FB_"))
                fb.OnExitExecution(name, price, quantity, etTime);
            else if (name == "VBR_LONG" || name == "VBR_SHORT")
                vbr.OnEntryExecution(name, price, quantity, etTime);
            else if (name.StartsWith("VBR_"))
                vbr.OnExitExecution(name, price, quantity, etTime);
            else if (name == "Exit on session close")
            {
                fb.OnSessionCloseExecution(price, quantity, etTime);
                vbr.OnSessionCloseExecution(price, quantity, etTime);
            }
        }

        // V6 U9: the ONLY place a parked handoff entry is released. NinjaTrader
        // reports the strategy position as Flat once the flatten fill is processed;
        // the replacement order is submitted at that point and never before.
        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            if (handoff == null) return;
            if (marketPosition == MarketPosition.Flat && handoff.HandoffInProgress)
                handoff.NotifyFlat();
        }

        protected override void OnOrderUpdate(Order order, double limitPrice, double stopPrice,
            int quantity, int filled, double averageFillPrice, OrderState orderState,
            DateTime time, ErrorCode error, string comment)
        {
            if (order == null) return;
            if (orderState == OrderState.Rejected)
                PrintLine(string.Format(CultureInfo.InvariantCulture,
                    "ORDER REJECTED name={0} error={1} comment={2}", order.Name, error, comment));
        }

        // ==================================================================
        // IMnqHost implementation — services the engines call out to
        // ==================================================================
        public KeyLevelEngine Levels { get { return levels; } }
        double IMnqHost.TickSize { get { return TickSize; } }
        public bool InstrumentOk { get { return instrumentOk; } }

        // SH-3: live = account cash value; backtest = SimAccountBalance plus
        // (optionally) realized cumulative PnL so sizing compounds.
        public double AccountBalance
        {
            get
            {
                if (State == State.Realtime && UseAccountCashValueLive && Account != null)
                {
                    double cash = Account.Get(AccountItem.CashValue, Currency.UsDollar);
                    if (cash > 0) return cash;
                }
                double b = SimAccountBalance;
                if (CompoundSimBalance && SystemPerformance != null && SystemPerformance.AllTrades != null)
                    b += SystemPerformance.AllTrades.TradesPerformance.Currency.CumProfit;
                return b;
            }
        }

        // GLOBAL ENTRY-TIME RULE: 9:30 <= signal close <= 11:30 ET
        public bool IsEntryTimeAllowed(DateTime etTime)
        {
            double m = etTime.TimeOfDay.TotalMinutes;
            return m >= EntryStartMinutesEt && m <= EntryEndMinutesEt;
        }

        public bool IsAtOrAfterSessionStart(DateTime etTime)
        {
            return etTime.TimeOfDay.TotalMinutes >= EntryStartMinutesEt;
        }

        public bool IsAfterEntryCutoff(DateTime etTime)
        {
            return etTime.TimeOfDay.TotalMinutes > EntryEndMinutesEt;
        }

        // V6 U9: this is only the instrument/enabled gate. An open position held by
        // the OTHER strategy never blocks an entry — EnterPosition routes it through
        // the handoff coordinator (flatten first, confirm flat, then enter).
        public bool CanOpenPosition(StrategyId id)
        {
            return instrumentOk;
        }

        public bool TpLevelEnabled(TpLevelId id)
        {
            switch (id)
            {
                case TpLevelId.M0: return TpEnableM0;
                case TpLevelId.M1: return TpEnableM1;
                case TpLevelId.M2: return TpEnableM2;
                case TpLevelId.M3: return TpEnableM3;
                case TpLevelId.M4: return TpEnableM4;
                case TpLevelId.M5: return TpEnableM5;
                case TpLevelId.PP: return TpEnablePP;
                case TpLevelId.DAILY_OPEN: return TpEnableDailyOpen;
                case TpLevelId.YDAY_HIGH: return TpEnableYdayHigh;
                case TpLevelId.YDAY_LOW: return TpEnableYdayLow;
                case TpLevelId.LWEEK_HIGH: return TpEnableLweekHigh;
                case TpLevelId.LWEEK_LOW: return TpEnableLweekLow;
                case TpLevelId.R1: return TpEnableR1;
                case TpLevelId.R3: return TpEnableR3;
                case TpLevelId.S1: return TpEnableS1;
                case TpLevelId.S2: return TpEnableS2;
                case TpLevelId.PSY_HIGH: return TpEnablePsyHigh;
                case TpLevelId.PSY_LOW: return TpEnablePsyLow;
                case TpLevelId.VWAP: return TpEnableVwap;
                case TpLevelId.VWAP_BAND_HIGH: return TpEnableVwapBandHigh;
                case TpLevelId.VWAP_BAND_LOW: return TpEnableVwapBandLow;
            }
            return false;
        }

        // V6 U9 STRATEGY HANDOFF: entries are routed through the coordinator. If the
        // other engine holds a position, it is flattened FIRST and this order is
        // parked until the account is confirmed flat (see OnPositionUpdate).
        // All orders go against the 1m series (finest execution granularity);
        // signal names carry the strategy prefix.
        public int EnterPosition(StrategyId id, TradeDirection dir, int qty, string signalName)
        {
            if (!instrumentOk || qty < 1) return 0;
            if (id == StrategyId.FAKE_BREAKOUT && !EnableFakeBreakout) return 0;
            if (id == StrategyId.VECTOR_BREAK_RETEST && !EnableVectorBreakRetest) return 0;
            handoff.RequestEntry(id, dir, qty, signalName);
            return qty;
        }

        private void SubmitEntryOrder(StrategyId id, TradeDirection dir, int qty, string signalName)
        {
            if (dir == TradeDirection.Long)
                EnterLong(bipExec, qty, signalName);
            else
                EnterShort(bipExec, qty, signalName);
        }

        // V7.1 diagnostics sink for the confirmation detectors.
        // cmDiagTime carries the ET timestamp of the confirmation bar currently being
        // processed, so detector events are stamped with real bar times rather than
        // the wall clock (which would be meaningless in a backtest).
        private DateTime cmDiagTime = DateTime.MinValue;
        private void CmDiag(string msg)
        {
            if (logger != null) logger.DiagGlobal(cmDiagTime, "[XMKT] " + msg);
            else PrintLine("[XMKT] " + msg);
        }

        // V7.1: one line per confirmation market per day. Makes "no confirmation
        // because nothing happened" visually distinct from "no confirmation because
        // this market had no data" — the failure mode that silently mis-graded a
        // whole backtest.
        private void EmitCrossMarketDayReport(bool isEs, DateTime etClose)
        {
            cmDiagTime = etClose;
            KeyLevelEngine kl = isEs ? esLevels : qqqLevels;
            CrossMarketConfirmDetector d1 = isEs ? esDet1 : qqqDet1;
            CrossMarketConfirmDetector d3 = isEs ? esDet3 : qqqDet3;
            string mk = isEs ? EsSymbol : QqqSymbol;
            bool levelsOk = !double.IsNaN(kl.YdayHigh) || !double.IsNaN(kl.YdayLow)
                         || !double.IsNaN(kl.LweekHigh) || !double.IsNaN(kl.LweekLow);
            CmDiag(string.Format(CultureInfo.InvariantCulture,
                "{0:yyyy-MM-dd} {1} levels: YH={2} YL={3} LWH={4} LWL={5}{6}",
                etClose, mk, Fmt(kl.YdayHigh), Fmt(kl.YdayLow), Fmt(kl.LweekHigh), Fmt(kl.LweekLow),
                levelsOk ? "" : "   <<< ALL NaN — this market cannot be evaluated, it is NOT declining to confirm"));
            CmDiag("    " + d1.DailyTally());
            CmDiag("    " + d3.DailyTally());
        }

        private static string Fmt(double v)
        {
            return double.IsNaN(v) ? "NaN" : v.ToString("0.00", CultureInfo.InvariantCulture);
        }

        // ==================================================================
        // V7 cross-market confirmation — READ-ONLY host queries.
        // Nothing here can submit, size, cancel or modify an order.
        // ==================================================================
        public bool CrossMarketEnabled
        {
            get { return EnableCrossMarketConfirmation && crossMarketReady; }
        }

        public CrossMarketConfirm QueryCrossMarket(ConfirmMarket market, bool isLong, KeyLevelId levelId,
                                                   int tfMinutes, DateTime barEtClose)
        {
            CrossMarketConfirm miss = new CrossMarketConfirm();
            miss.LevelId = levelId;
            miss.LevelPrice = double.NaN;

            if (!CrossMarketEnabled)
            {
                miss.Reason = "cross-market confirmation not available";
                return miss;
            }

            // Timeframe isolation: a 1m signal can only ever reach a 1m detector,
            // a 3m signal only a 3m detector. There is no path between them.
            CrossMarketConfirmDetector det;
            if (market == ConfirmMarket.ES)
                det = tfMinutes == 1 ? esDet1 : tfMinutes == 3 ? esDet3 : null;
            else
                det = tfMinutes == 1 ? qqqDet1 : tfMinutes == 3 ? qqqDet3 : null;

            if (det == null)
            {
                miss.Reason = string.Format("{0}: no {1}m confirmation series exists", market, tfMinutes);
                return miss;
            }
            return det.Query(isLong, levelId, barEtClose, CrossMarketToleranceBars);
        }

        // A DISABLED engine is reported as permanently flat and can never be asked
        // to flatten. Combined with never being fed a bar, that makes it impossible
        // for it to park an entry, trigger a handoff, or flatten the other engine.
        private bool StrategyHasPosition(StrategyId id)
        {
            if (id == StrategyId.FAKE_BREAKOUT)
                return EnableFakeBreakout && fb.HasOpenOrPendingPosition;
            return EnableVectorBreakRetest && vbr.HasOpenOrPendingPosition;
        }

        private void FlattenStrategy(StrategyId id)
        {
            if (id == StrategyId.FAKE_BREAKOUT) { if (EnableFakeBreakout) fb.FlattenForHandoff(); }
            else { if (EnableVectorBreakRetest) vbr.FlattenForHandoff(); }
        }

        public void SubmitOrUpdateStop(StrategyId id, TradeDirection dir, int qty, double stopPrice,
            string stopName, string fromEntrySignal)
        {
            if (qty < 1) return;
            double p = RoundToTick(stopPrice);
            if (dir == TradeDirection.Long)
                ExitLongStopMarket(bipExec, true, qty, p, stopName, fromEntrySignal);
            else
                ExitShortStopMarket(bipExec, true, qty, p, stopName, fromEntrySignal);
        }

        public void ExitMarket(StrategyId id, TradeDirection dir, int qty, string exitName, string fromEntrySignal)
        {
            if (qty < 1) return;
            if (dir == TradeDirection.Long)
                ExitLong(bipExec, qty, exitName, fromEntrySignal);
            else
                ExitShort(bipExec, qty, exitName, fromEntrySignal);
        }

        public void Diag(StrategyId id, string msg)
        {
            if (!VerboseDiagnostics || logger == null) return;
            DateTime et = CurrentBars.Length > BipOneMin && CurrentBars[BipOneMin] >= 0
                ? ToEt(Times[BipOneMin][0]) : DateTime.MinValue;
            logger.Diag(id, et, msg);
        }

        public void LogTrade(TradeRecord rec)
        {
            if (logger != null) logger.Trade(rec);
        }

        public double RoundToTick(double price)
        {
            return Instrument != null ? Instrument.MasterInstrument.RoundToTickSize(price) : price;
        }

        // ==================================================================
        // helpers
        // ==================================================================
        private DateTime ToEt(DateTime barTime)
        {
            if (AssumeBarTimesAreEastern || etZone == null) return barTime;
            try { return TimeZoneInfo.ConvertTime(barTime, TimeZoneInfo.Local, etZone); }
            catch (Exception) { return barTime; }
        }

        private DateTime ToUtc(DateTime barTime)
        {
            try
            {
                DateTime t = DateTime.SpecifyKind(barTime, DateTimeKind.Unspecified);
                if (AssumeBarTimesAreEastern && etZone != null)
                    return TimeZoneInfo.ConvertTimeToUtc(t, etZone);
                return TimeZoneInfo.ConvertTimeToUtc(t, TimeZoneInfo.Local);
            }
            catch (Exception) { return barTime; }
        }

        // V5 Fix 4: print all 18 target-level values (plus trigger levels) at the
        // first 1m close at/after 9:30 ET on the configured diagnostic date so
        // they can be compared with the Traders Reality TradingView indicator.
        private DateTime lastLevelsDiagDate = DateTime.MinValue;
        private void MaybePrintLevelsDiagnostic(DateTime etClose)
        {
            if (string.IsNullOrEmpty(PrintLevelsDiagnosticDate) || logger == null) return;
            DateTime target;
            if (!DateTime.TryParseExact(PrintLevelsDiagnosticDate, "yyyy-MM-dd",
                CultureInfo.InvariantCulture, System.Globalization.DateTimeStyles.None, out target)) return;
            if (etClose.Date != target.Date || etClose.TimeOfDay.TotalMinutes < EntryStartMinutesEt) return;
            if (lastLevelsDiagDate == etClose.Date) return;
            lastLevelsDiagDate = etClose.Date;

            System.Text.StringBuilder sb = new System.Text.StringBuilder();
            sb.Append("TR LEVEL DIAGNOSTIC ").Append(etClose.ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture)).Append(" ET | ");
            foreach (TpLevelId id in Enum.GetValues(typeof(TpLevelId)))
                sb.Append(id).Append("=").Append(levels.GetTpLevelPrice(id).ToString("0.00", CultureInfo.InvariantCulture)).Append(" ");
            sb.Append("| internal R2=").Append(levels.R2.ToString("0.00", CultureInfo.InvariantCulture));
            sb.Append(" S3=").Append(levels.S3.ToString("0.00", CultureInfo.InvariantCulture));
            logger.DiagGlobal(etClose, sb.ToString());
        }

        private void PrintLine(string s)
        {
            Print(s);
        }
    }
}
