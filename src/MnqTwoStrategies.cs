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
// SERIES MAP (BarsInProgress):
//   0 = chart series (NEVER used for logic)
//   1 = 1-minute   (entries/patterns/MFE-MAE/key-level aggregation)
//   2 = 3-minute   (Fake Breakout entry TF + runner)
//   3 = 15-minute  (parent setups for both strategies)
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
        private const int BipOneMin = 1;
        private const int BipThreeMin = 2;
        private const int BipFifteenMin = 3;

        private KeyLevelEngine levels;
        private FakeBreakoutEngine fb;
        private VectorBreakRetestEngine vbr;
        private MnqLogger logger;
        private TimeZoneInfo etZone;
        private EMA ema1m, ema3m, ema15m;
        private bool instrumentOk;
        private bool instrumentWarned;
        private HandoffCoordinator handoff;   // V6 U9 strategy handoff sequencing

        // ==================================================================
        // Parameters — every flagged ambiguity is exposed here instead of
        // being silently hard-coded (spec: "If a coding rule remains
        // ambiguous, expose it as a configurable parameter").
        // ==================================================================

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
        #endregion

        #region 06. Logging
        [NinjaScriptProperty]
        [Display(Name = "Write CSV trade log", GroupName = "06. Logging", Order = 1)]
        public bool WriteCsvTradeLog { get; set; }

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
                IsExitOnSessionClose = false;
                ExitOnSessionCloseSeconds = 30;
                BarsRequiredToTrade = 30;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                IsInstantiatedOnEachOptimizationIteration = true;

                // ---- defaults ----
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
                PrintLevelsDiagnosticDate = "";
            }
            else if (State == State.Configure)
            {
                // Multi-timeframe architecture (spec: 15m parent, 3m/1m entries).
                AddDataSeries(BarsPeriodType.Minute, 1);   // BarsInProgress 1
                AddDataSeries(BarsPeriodType.Minute, 3);   // BarsInProgress 2
                AddDataSeries(BarsPeriodType.Minute, 15);  // BarsInProgress 3
                IsExitOnSessionClose = ExitOnSessionCloseEnabled;
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

                FbConfig fbCfg = new FbConfig();
                fbCfg.RiskPctAMinus = RiskPctAMinus;
                fbCfg.RiskPctBPlus = RiskPctBPlus;
                fbCfg.RequirePriorCloseInside = FbRequirePriorCloseInside;
                fbCfg.InvalidReclaimCancelsSetup = FbInvalidReclaimCancelsSetup;
                fbCfg.Require15mReclaimBeforeLtfEntry = FbRequire15mReclaimBeforeLtfEntry;
                fbCfg.Require15mEmaConfluence = FbRequire15mEmaConfluence;
                fbCfg.TargetBreakMode = FbTargetBreakModeParam;
                fbCfg.GradeBasis = FbGradeBasisParam;
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

                if (!instrumentOk)
                    PrintLine("MnqTwoStrategies ERROR: instrument '" + master
                        + "' is not MNQ. Spec is MNQ-ONLY — all trading disabled. Apply this strategy to an MNQ chart.");
            }
            else if (State == State.Terminated)
            {
                if (fb != null && logger != null)
                {
                    PrintLine("================ FINAL STATISTICS ================");
                    PrintLine(fb.Stats.Summary("FAKE_BREAKOUT"));
                    PrintLine(vbr.Stats.Summary("VECTOR_BREAK_RETEST"));
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

            if (BarsInProgress == BipOneMin)
            {
                if (CurrentBars[BipOneMin] < 1) return;

                // key-level aggregation always runs (needs full history)
                DateTime etClose = ToEt(Times[BipOneMin][0]);
                DateTime etOpen = etClose.AddMinutes(-1);
                DateTime utcOpen = ToUtc(Times[BipOneMin][0]).AddMinutes(-1); // psy sessions are GMT-defined (TR source)
                bool newDay = levels.OnOneMinuteBar(etOpen, etClose, utcOpen,
                    Opens[BipOneMin][0], Highs[BipOneMin][0], Lows[BipOneMin][0], Closes[BipOneMin][0]);
                MaybePrintLevelsDiagnostic(etClose);
                if (newDay)
                {
                    if (VerboseDiagnostics && logger != null)
                        logger.DiagGlobal(etClose, string.Format(CultureInfo.InvariantCulture,
                            "NEW EXCHANGE DAY — DailyOpen={0:0.00} YH={1:0.00} YL={2:0.00} LWH={3:0.00} LWL={4:0.00} PP={5:0.00}",
                            levels.DailyOpen, levels.YdayHigh, levels.YdayLow, levels.LweekHigh, levels.LweekLow, levels.PP));
                    fb.OnNewDay(etClose);
                    vbr.OnNewDay(etClose);
                }

                if (CurrentBars[BipOneMin] < 11) return; // vector needs previous 10 completed candles
                BarSnap snap = BuildSnap(BipOneMin, 1, ema1m[0]);
                fb.OnOneMinuteBar(snap);
                vbr.OnOneMinuteBar(snap);
            }
            else if (BarsInProgress == BipThreeMin)
            {
                if (CurrentBars[BipThreeMin] < 11) return;
                BarSnap snap = BuildSnap(BipThreeMin, 3, ema3m[0]);
                fb.OnThreeMinuteBar(snap);
                // VECTOR_BREAK_RETEST uses 15m + 1m ONLY (spec §1) — never fed 3m data.
            }
            else if (BarsInProgress == BipFifteenMin)
            {
                if (CurrentBars[BipFifteenMin] < 11) return;
                BarSnap snap = BuildSnap(BipFifteenMin, 15, ema15m[0]);
                double prev15Close = CurrentBars[BipFifteenMin] >= 1 ? Closes[BipFifteenMin][1] : double.NaN;
                fb.OnFifteenMinuteBar(snap, prev15Close);
                vbr.OnFifteenMinuteBar(snap, prev15Close);
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
            handoff.RequestEntry(id, dir, qty, signalName);
            return qty;
        }

        private void SubmitEntryOrder(StrategyId id, TradeDirection dir, int qty, string signalName)
        {
            if (dir == TradeDirection.Long)
                EnterLong(BipOneMin, qty, signalName);
            else
                EnterShort(BipOneMin, qty, signalName);
        }

        private bool StrategyHasPosition(StrategyId id)
        {
            return id == StrategyId.FAKE_BREAKOUT
                ? fb.HasOpenOrPendingPosition
                : vbr.HasOpenOrPendingPosition;
        }

        private void FlattenStrategy(StrategyId id)
        {
            if (id == StrategyId.FAKE_BREAKOUT) fb.FlattenForHandoff();
            else vbr.FlattenForHandoff();
        }

        public void SubmitOrUpdateStop(StrategyId id, TradeDirection dir, int qty, double stopPrice,
            string stopName, string fromEntrySignal)
        {
            if (qty < 1) return;
            double p = RoundToTick(stopPrice);
            if (dir == TradeDirection.Long)
                ExitLongStopMarket(BipOneMin, true, qty, p, stopName, fromEntrySignal);
            else
                ExitShortStopMarket(BipOneMin, true, qty, p, stopName, fromEntrySignal);
        }

        public void ExitMarket(StrategyId id, TradeDirection dir, int qty, string exitName, string fromEntrySignal)
        {
            if (qty < 1) return;
            if (dir == TradeDirection.Long)
                ExitLong(BipOneMin, qty, exitName, fromEntrySignal);
            else
                ExitShort(BipOneMin, qty, exitName, fromEntrySignal);
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
