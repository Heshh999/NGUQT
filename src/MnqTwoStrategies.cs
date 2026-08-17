// ============================================================================
// MnqTwoStrategies.cs
// NinjaTrader 8 host strategy for the TWO independent MNQ-only strategies:
//   1. FAKE_BREAKOUT          (FakeBreakoutEngine.cs)
//   2. VECTOR_BREAK_RETEST    (VectorBreakRetestEngine.cs)
//
// Spec sections implemented here:
//   "CURRENT EXECUTION INSTRUMENT SCOPE - MNQ ONLY" (hard instrument gate,
//    $2/pt sizing lives in PositionSizer)
//   "CRITICAL ARCHITECTURE" (two engines, no shared setup state, StrategyId on
//    every order + log record, unique signal names FB_*/VBR_*)
//   "GLOBAL ENTRY-TIME RULE" (9:30-11:30 ET gates)
//   "IMPLEMENTATION NOTES FOR CLAUDE" (no repainting: Calculate.OnBarClose,
//    completed candles only; logging)
//
// SERIES MAP (BarsInProgress) - indices are assigned in State.Configure in
// AddDataSeries order, so they shift with the optional series:
//   0 = chart series (NEVER used for logic)
//   [ES 1m, ES 3m, YM 1m, YM 3m]  OPTIONAL V7 confirmation markets, added
//       FIRST so a same-timestamp bar is complete before MNQ decides. DATA
//       ONLY - no order is ever routed to these series.
//   1m  (entries/patterns/MFE-MAE/key-level aggregation)
//   3m  (Fake Breakout entry TF + runner)
//   15m (parent setups for both strategies)
//   1-tick (OPTIONAL, added LAST, execution granularity only - carries NO logic)
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
        // SERIES MAP - assigned in State.Configure, in AddDataSeries order.
        //
        // These were compile-time constants before V7. They are now fields
        // because the optional ES/YM confirmation series must be added
        // BEFORE the MNQ series. NinjaTrader processes bars that share a
        // timestamp in the order the series were added, so ES/YM must come
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
        private int BipEs1 = -1, BipEs3 = -1, BipYm1 = -1, BipYm3 = -1;
        private int BipSec30 = -1, BipSec15 = -1, BipSec10 = -1, BipSec5 = -1;
        private int BipFiveMin = -1, BipThirtyMin = -1, BipSixtyMin = -1;   // scalp research context only

        // Series index that ORDERS are submitted against. Signals are unaffected -
        // this only controls how finely NinjaTrader simulates fills in a backtest.
        // NT8 refuses "High" order-fill resolution for multi-series strategies and
        // instructs you to "program directly into your strategy the more granular
        // resolution you would like to simulate order fills with" - that is exactly
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
        // "ES's own yesterday high" / "YM's own yesterday high" - MNQ prices are
        // never compared against ES or YM prices anywhere.
        private KeyLevelEngine esLevels, ymLevels;
        private EMA emaEs1, emaEs3, emaYm1, emaYm3;
        private CrossMarketConfirmDetector esDet1, esDet3, ymDet1, ymDet3;
        private bool crossMarketReady;        // series attached AND carrying bars

        // ---- vector-candle research logger (data only, never trades) ----
        private VectorCandleResearchEngine research;      // 1m
        private VectorCandleResearchEngine research15m, research3m;
        private VectorCandleResearchEngine researchS30, researchS15, researchS10, researchS5;
        private HigherTfStructure htf3m, htf15m;          // shared read-only HTF structure
        private System.IO.StreamWriter researchCsv;

        // ---- scalp research capture (independent of candle classification) ----
        private ScalpResearchEngine scalp1m, scalpS30, scalpS15, scalpS10, scalpS5;
        private HigherTfStructure sHtf3, sHtf5, sHtf15, sHtf30, sHtf60;
        private System.IO.StreamWriter scalpCsv;

        // ==================================================================
        // Parameters - every flagged ambiguity is exposed here instead of
        // being silently hard-coded (spec: "If a coding rule remains
        // ambiguous, expose it as a configurable parameter").
        // ==================================================================

        #region 00. Strategy Selection
        // Each engine can be switched off independently. Disabling one simply stops
        // feeding it bars - its state machine never starts, so it can never signal,
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
        // ES and YM are CONFIRMATION MARKETS ONLY. No order is ever submitted on
        // either one - every order in this strategy is routed to the MNQ series.
        // They change the GRADE and RISK of an MNQ Fake Breakout that has already
        // qualified on the MNQ rules alone. They never create or block a trade.
        [NinjaScriptProperty]
        [Display(Name = "Enable cross-market grading (ES + YM)", GroupName = "00b. Cross-Market Confirmation", Order = 1)]
        public bool EnableCrossMarketConfirmation { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "ES confirmation symbol", GroupName = "00b. Cross-Market Confirmation", Order = 2)]
        public string EsSymbol { get; set; }

        // Confirmation market 2 = YM (CME Dow futures). Data only, never traded.
        [NinjaScriptProperty]
        [Display(Name = "YM confirmation symbol", GroupName = "00b. Cross-Market Confirmation", Order = 3)]
        public string YmSymbol { get; set; }

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
        [Display(Name = "Risk % - A+ (BOTH markets confirm)", GroupName = "00b. Cross-Market Confirmation", Order = 7)]
        public double CmRiskPctAPlus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Risk % - A- (exactly ONE market confirms)", GroupName = "00b. Cross-Market Confirmation", Order = 8)]
        public double CmRiskPctAMinus { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "Risk % - B+ (MNQ alone, NEITHER confirms)", GroupName = "00b. Cross-Market Confirmation", Order = 9)]
        public double CmRiskPctBPlus { get; set; }

        // Confirmation-market key levels are built from each market's own session.
        // from the RTH cash session only, per user specification.


        // V7.1: makes a silent ES/YM data failure impossible to miss.
        //   Summary = one line per market per day (bar counts, levels, near-miss tally)
        //   Verbose = every break / rejected reclaim / expiry / confirmation (LOUD)
        // Confirmation on ES / market 2 is break + reclaim only. Their EMA(9) plays no
        // part (user specification). MNQ's own EMA(9) entry rule is unaffected.
        [NinjaScriptProperty]
        [Display(Name = "Require EMA(9) on confirmation markets too", GroupName = "00b. Cross-Market Confirmation", Order = 10)]
        public bool ConfirmMarketsRequireEma { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Cross-market diagnostics (0=Off 1=Summary 2=Verbose)", GroupName = "00b. Cross-Market Confirmation", Order = 13)]
        [Range(0, 2)]
        public int CrossMarketDiagnostics { get; set; }
        #endregion

        #region 00c. Vector Candle Research (data collection only - NEVER trades)
        // Writes one CSV row per completed 1-minute Traders Reality vector candle with
        // the context known at that moment plus forward-outcome labels. It submits no
        // orders and cannot influence FAKE_BREAKOUT or VECTOR_BREAK_RETEST in any way.
        [NinjaScriptProperty]
        [Display(Name = "Enable vector research logger (no trading effect)", GroupName = "00c. Vector Candle Research", Order = 1)]
        public bool EnableVectorResearch { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Also log REGULAR candles (much larger file)", GroupName = "00c. Vector Candle Research", Order = 2)]
        public bool ResearchIncludeRegularCandles { get; set; }

        // Adds 15m and 3m research streams so higher-timeframe vector context can be
        // studied alongside the 1m stream. Cheap: those series already exist.
        [NinjaScriptProperty]
        [Display(Name = "Research 15m + 3m vector context", GroupName = "00c. Vector Candle Research", Order = 3)]
        public bool ResearchHigherTimeframes { get; set; }

        // Adds 30s/15s/10s/5s series for sub-minute execution research. These are NOT
        // free: NinjaTrader must load and process four extra series, and second-based
        // history is usually far shallower than minute history. The DATA SERIES STATUS
        // block reports exactly what actually loaded - never assume.
        [NinjaScriptProperty]
        [Display(Name = "Research sub-minute execution (30s/15s/10s/5s)", GroupName = "00c. Vector Candle Research", Order = 4)]
        public bool ResearchSubMinute { get; set; }

        // The PLACEBO CONTROL. With "Also log REGULAR candles" on, this keeps only 1 in
        // N of them, so the control group is present without the file becoming
        // unmanageable. Vectors are always kept in full. 10 gives a ~10% sample of
        // regular candles, which is ample for a base-rate comparison.
        [NinjaScriptProperty]
        [Range(1, 500)]
        [Display(Name = "Keep 1 in N regular candles (placebo control sampling)", GroupName = "00c. Vector Candle Research", Order = 5)]
        public int ResearchRegularCandleSampleRate { get; set; }

        // Bars to the right required before a higher-timeframe swing pivot counts as
        // confirmed and may be used. Higher = later confirmation, but a pivot that is
        // less likely to be revised. This directly controls the no-lookahead lag.
        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "HTF swing pivot confirmation bars", GroupName = "00c. Vector Candle Research", Order = 6)]
        public int ResearchHtfPivotConfirmBars { get; set; }

        #endregion

        #region 00d. Scalp Research (structure-based, no candle classification)

        // A SEPARATE capture with no dependency on candle classification of any kind.
        // Its sampling frame is price interacting with structure, plus a sampled
        // control group of bars that interacted with nothing - which is what makes
        // "better at a level than away from one?" an answerable question.
        [NinjaScriptProperty]
        [Display(Name = "Enable scalp research capture (no trading effect)", GroupName = "00d. Scalp Research", Order = 1)]
        public bool EnableScalpResearch { get; set; }

        // Adds 5m/30m/60m purely as CONTEXT structure for the scalp capture. 3m and 15m
        // already exist for the strategies and are reused.
        [NinjaScriptProperty]
        [Display(Name = "Add 5m/30m/60m context structure", GroupName = "00d. Scalp Research", Order = 2)]
        public bool ScalpContextTimeframes { get; set; }

        // Keep 1 in N bars that interacted with NO tracked level. This control group is
        // required for the placebo and incremental-value tests; 0 disables it.
        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "Keep 1 in N no-interaction bars (control group)", GroupName = "00d. Scalp Research", Order = 3)]
        public int ScalpControlSampleRate { get; set; }

        [NinjaScriptProperty]
        [Range(0.25, 100)]
        [Display(Name = "Approach band (points) for level interaction", GroupName = "00d. Scalp Research", Order = 4)]
        public double ScalpApproachBandPoints { get; set; }

        // Round-number levels, in points. 100 tracks 20000/20100/...; 0 disables them.
        [NinjaScriptProperty]
        [Range(0, 1000)]
        [Display(Name = "Round-number level step (points, 0 = off)", GroupName = "00d. Scalp Research", Order = 5)]
        public double ScalpRoundNumberStep { get; set; }

        // Emit only inside this ET window, to keep the file to the session being studied.
        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Emit from (ET minutes, 0=midnight, 570=09:30)", GroupName = "00d. Scalp Research", Order = 6)]
        public int ScalpEmitStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Emit until (ET minutes, 660=11:00, 1440=all)", GroupName = "00d. Scalp Research", Order = 7)]
        public int ScalpEmitEndMinutesEt { get; set; }
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
                // Spec: "Use completed candles for all signal decisions" - no repainting.
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
                YmSymbol = "YM ##-##";       // confirmation market 2 (Dow). Data only - never traded.
                CrossMarketMaxBarsBreakToReclaim = 4;   // user-specified
                CrossMarketToleranceBars = 0;           // exact same completed bar
                CmRiskPctAPlus = 30.0;                  // ES + YM both confirm
                CmRiskPctAMinus = 10.0;                 // ES only
                CmRiskPctBPlus = 5.0;                   // MNQ alone, neither confirms
                ConfirmMarketsRequireEma = false;        // spec: ES/market-2 EMAs do not matter
                CrossMarketDiagnostics = 1;             // Summary

                EntryStartMinutesEt = 570;      // 9:30 ET
                EntryEndMinutesEt = 690;        // 11:30 ET
                AssumeBarTimesAreEastern = false;
                DayStartMinutesEt = 1080;       // 18:00 ET = CME exchange-day open = TR time('D') boundary for MNQ (V5 Fix 4A)
                WeekStartMinutesEt = 1080;      // Sunday 18:00 ET futures week open (TradingView weekly bar for MNQ)
                PsyLevelTypeParam = PsyLevelType.Forex;  // user-confirmed for MNQ (TR overridePsyType path)
                PsyUse4HourGridParam = false;            // compat only - see KeyLevelEngine notes
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

                EnableVectorResearch = false;
                ResearchIncludeRegularCandles = false;
                ResearchHigherTimeframes = false;
                ResearchSubMinute = false;
                ResearchRegularCandleSampleRate = 10;
                ResearchHtfPivotConfirmBars = 2;
                EnableScalpResearch = false;
                ScalpContextTimeframes = true;
                ScalpControlSampleRate = 150;
                ScalpApproachBandPoints = 6.0;
                ScalpRoundNumberStep = 100.0;
                ScalpEmitStartMinutesEt = 0;
                ScalpEmitEndMinutesEt = 1440;
                WriteCsvTradeLog = true;
                VerboseDiagnostics = true;
                UseTickExecutionSeries = true;   // NT8 multi-series fill granularity
                PrintLevelsDiagnosticDate = "";
            }
            else if (State == State.Configure)
            {
                int next = 1;   // BarsInProgress 0 is the chart series

                // ---- V7 confirmation series FIRST -------------------------------
                // Added ahead of the MNQ series so that when ES/YM and MNQ all
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
                    AddDataSeries(YmSymbol, BarsPeriodType.Minute, 1, MarketDataType.Last);
                    BipYm1 = next++;
                    AddDataSeries(YmSymbol, BarsPeriodType.Minute, 3, MarketDataType.Last);
                    BipYm3 = next++;
                }

                // Multi-timeframe architecture (spec: 15m parent, 3m/1m entries).
                AddDataSeries(BarsPeriodType.Minute, 1);
                BipOneMin = next++;
                AddDataSeries(BarsPeriodType.Minute, 3);
                BipThreeMin = next++;
                AddDataSeries(BarsPeriodType.Minute, 15);
                BipFifteenMin = next++;

                // ---- OPTIONAL scalp-research CONTEXT series (data only, no orders) ----
                // 3m and 15m already exist above and are reused rather than duplicated.
                if (EnableScalpResearch && ScalpContextTimeframes)
                {
                    AddDataSeries(BarsPeriodType.Minute, 5);  BipFiveMin = next++;
                    AddDataSeries(BarsPeriodType.Minute, 30); BipThirtyMin = next++;
                    AddDataSeries(BarsPeriodType.Minute, 60); BipSixtyMin = next++;
                }

                // ---- OPTIONAL sub-minute RESEARCH series (data only, no orders) ----
                if ((EnableVectorResearch && ResearchSubMinute) || (EnableScalpResearch && ResearchSubMinute))
                {
                    AddDataSeries(BarsPeriodType.Second, 30); BipSec30 = next++;
                    AddDataSeries(BarsPeriodType.Second, 15); BipSec15 = next++;
                    AddDataSeries(BarsPeriodType.Second, 10); BipSec10 = next++;
                    AddDataSeries(BarsPeriodType.Second, 5);  BipSec5 = next++;
                }

                // Optional execution series (added LAST so the indices above never move).
                // It carries NO strategy logic - OnBarUpdate ignores it entirely.
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
                    // ES is CME, same 18:00 ET exchange day as MNQ - identical config.
                    esLevels = new KeyLevelEngine();
                    esLevels.DayStartMinutesEt = DayStartMinutesEt;
                    esLevels.WeekStartMinutesEt = WeekStartMinutesEt;

                    // specification its levels come from the RTH cash session only,
                    // so the day/week roll is calendar-based and the session filter
                    // discards everything outside 09:30-16:00 ET.
                    // YM is CME, identical exchange day to MNQ and ES.
                    ymLevels = new KeyLevelEngine();
                    ymLevels.DayStartMinutesEt = DayStartMinutesEt;
                    ymLevels.WeekStartMinutesEt = WeekStartMinutesEt;
                    ymLevels.SessionFilterEnabled = false;

                    esDet1 = new CrossMarketConfirmDetector(ConfirmMarket.ES, 1, esLevels);
                    esDet3 = new CrossMarketConfirmDetector(ConfirmMarket.ES, 3, esLevels);
                    ymDet1 = new CrossMarketConfirmDetector(ConfirmMarket.YM, 1, ymLevels);
                    ymDet3 = new CrossMarketConfirmDetector(ConfirmMarket.YM, 3, ymLevels);
                    foreach (CrossMarketConfirmDetector d in new CrossMarketConfirmDetector[] { esDet1, esDet3, ymDet1, ymDet3 })
                    {
                        d.MaxBarsBreakToReclaim = CrossMarketMaxBarsBreakToReclaim;
                        d.SessionStartMinutesEt = EntryStartMinutesEt;
                        d.RequireEmaConfirmation = ConfirmMarketsRequireEma;
                    }
                    esDet1.Label = EsSymbol; esDet3.Label = EsSymbol;
                    ymDet1.Label = YmSymbol; ymDet3.Label = YmSymbol;
                    // V7.2 FIX - do NOT latch readiness on BarsArray[].Count here.
                    // State.DataLoaded is too early to trust a bar count in the Strategy
                    // Analyzer: a series that streams in later would be written off
                    // permanently. Readiness now only asserts the series are ATTACHED;
                    // whether each market can actually be evaluated is decided per query,
                    // live, from the detector's own bar count and level validity.
                    crossMarketReady = BipEs1 > 0 && BipEs3 > 0 && BipYm1 > 0 && BipYm3 > 0
                        && BarsArray.Length > BipYm3
                        && BarsArray[BipEs1] != null && BarsArray[BipEs3] != null
                        && BarsArray[BipYm1] != null && BarsArray[BipYm3] != null;

                    if (CrossMarketDiagnostics > 0)
                    {
                        esDet1.Diag = CmDiag; esDet3.Diag = CmDiag;
                        ymDet1.Diag = CmDiag; ymDet3.Diag = CmDiag;
                        bool verbose = CrossMarketDiagnostics >= 2;
                        esDet1.VerboseEvents = verbose; esDet3.VerboseEvents = verbose;
                        ymDet1.VerboseEvents = verbose; ymDet3.VerboseEvents = verbose;
                    }
                }

                if (EnableVectorResearch)
                {
                    string rpath = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                        string.Format("MnqVectorResearch_{0:yyyyMMdd_HHmmss}.csv", DateTime.Now));
                    researchCsv = new System.IO.StreamWriter(rpath, false);
                    researchCsv.WriteLine(VectorCandleResearchEngine.CsvHeader());
                    Action<string> sink = delegate(string row) { researchCsv.WriteLine(row); };
                    research = new VectorCandleResearchEngine(levels, sink);
                    research.IncludeRegularCandles = ResearchIncludeRegularCandles;
                    research.RegularCandleSampleRate = ResearchRegularCandleSampleRate;
                    research.TimeframeLabel = "1m";

                    // Higher-timeframe structure, shared by every stream. Fed only from
                    // COMPLETED 3m/15m bars, and every read is gated on the swing having
                    // been confirmed before the consuming candle closed.
                    htf3m = new HigherTfStructure("3m");
                    htf15m = new HigherTfStructure("15m");
                    htf3m.ConfirmBars = ResearchHtfPivotConfirmBars;
                    htf15m.ConfirmBars = ResearchHtfPivotConfirmBars;
                    research.Htf3m = htf3m; research.Htf15m = htf15m;

                    // Every non-1m stream reports the ONE-MINUTE EMA200/EMA9 as context,
                    // exactly as the research brief specifies, rather than its own.
                    Func<double> ema200Ctx = delegate() { return research.LocalEma200; };
                    Func<double> ema9Ctx = delegate() { return research.LocalEma9; };

                    if (ResearchHigherTimeframes)
                    {
                        research15m = MakeResearch(sink, "15m", ema200Ctx, ema9Ctx);
                        research3m = MakeResearch(sink, "3m", ema200Ctx, ema9Ctx);
                    }
                    if (ResearchSubMinute)
                    {
                        researchS30 = MakeResearch(sink, "30s", ema200Ctx, ema9Ctx);
                        researchS15 = MakeResearch(sink, "15s", ema200Ctx, ema9Ctx);
                        researchS10 = MakeResearch(sink, "10s", ema200Ctx, ema9Ctx);
                        researchS5 = MakeResearch(sink, "5s", ema200Ctx, ema9Ctx);
                    }
                    PrintLine("VECTOR RESEARCH LOGGER ENABLED - writing " + rpath);
                    PrintLine("  This module submits NO orders and does not affect either strategy.");
                }

                if (EnableScalpResearch)
                {
                    string spath = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                        string.Format("MnqScalpResearch_{0:yyyyMMdd_HHmmss}.csv", DateTime.Now));
                    scalpCsv = new System.IO.StreamWriter(spath, false);
                    scalpCsv.WriteLine(ScalpResearchEngine.CsvHeader());
                    Action<string> ssink = delegate(string row) { scalpCsv.WriteLine(row); };

                    sHtf3 = new HigherTfStructure("3m"); sHtf15 = new HigherTfStructure("15m");
                    if (ScalpContextTimeframes)
                    {
                        sHtf5 = new HigherTfStructure("5m");
                        sHtf30 = new HigherTfStructure("30m");
                        sHtf60 = new HigherTfStructure("60m");
                    }
                    foreach (HigherTfStructure h in new HigherTfStructure[] { sHtf3, sHtf5, sHtf15, sHtf30, sHtf60 })
                        if (h != null) h.ConfirmBars = ResearchHtfPivotConfirmBars;

                    scalp1m = MakeScalp(ssink, "1m");
                    if (ResearchSubMinute)
                    {
                        scalpS30 = MakeScalp(ssink, "30s"); scalpS15 = MakeScalp(ssink, "15s");
                        scalpS10 = MakeScalp(ssink, "10s"); scalpS5 = MakeScalp(ssink, "5s");
                    }
                    PrintLine("SCALP RESEARCH CAPTURE ENABLED - writing " + spath);
                    PrintLine("  Structure-based sampling. No candle classification is used anywhere in it.");
                    PrintLine("  This module submits NO orders and does not affect either strategy.");
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
                fbCfg.BlockEntryWhenCrossMarketUnavailable = true;   // no legacy fallback, ever
                fbCfg.CrossMarketGrades.RiskPctAPlus = CmRiskPctAPlus;
                fbCfg.CrossMarketGrades.RiskPctAMinus = CmRiskPctAMinus;
                fbCfg.CrossMarketGrades.RiskPctBPlus = CmRiskPctBPlus;
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

                // Spec S3 (FB) / S1 (VBR): normal EMA(close, 9) per timeframe.
                ema1m = EMA(BarsArray[BipOneMin], 9);
                ema3m = EMA(BarsArray[BipThreeMin], 9);
                ema15m = EMA(BarsArray[BipFifteenMin], 9);

                if (crossMarketReady)
                {
                    emaEs1 = EMA(BarsArray[BipEs1], 9);
                    emaEs3 = EMA(BarsArray[BipEs3], 9);
                    emaYm1 = EMA(BarsArray[BipYm1], 9);
                    emaYm3 = EMA(BarsArray[BipYm3], 9);
                }

                PrintLine(string.Format("MnqTwoStrategies: FAKE_BREAKOUT={0}, VECTOR_BREAK_RETEST={1}",
                    EnableFakeBreakout ? "ENABLED" : "DISABLED",
                    EnableVectorBreakRetest ? "ENABLED" : "DISABLED"));

                if (!EnableVectorBreakRetest)
                    PrintLine("VECTOR BREAK RETEST DISABLED");

                if (!EnableCrossMarketConfirmation)
                    PrintLine("CROSS-MARKET CONFIRMATION DISABLED - FAKE_BREAKOUT falls back to LEGACY validity-candle grading (A- 26% / B+ 10%)");
                else if (!crossMarketReady)
                {
                    PrintLine("**********************************************************************");
                    PrintLine("***      CROSS-MARKET GRADING UNAVAILABLE - NO TRADES WILL BE TAKEN ***");
                    PrintLine("**********************************************************************");
                    PrintLine("  The ES/YM confirmation series are not attached. A+/A-/B+ cannot be");
                    PrintLine("  produced, and NO legacy grade will be substituted - Fake Breakout");
                    PrintLine("  entries are BLOCKED so the dataset can never mix grading systems.");
                    PrintLine("  See the CROSS-MARKET DATA STATUS block below for per-series detail.");
                    PrintLine("**********************************************************************");
                    PrintLine("  configured: ES='" + EsSymbol + "'   YM='" + YmSymbol + "'");
                    PrintLine("**********************************************************************");
                }
                else
                    PrintLine(string.Format(CultureInfo.InvariantCulture,
                        "CROSS-MARKET CONFIRMATION ENABLED - market1='{0}' market2='{1}'"
                        + "\n  grades: A+={2}% (BOTH agree) | A-={3}% (exactly ONE agrees) | B+={4}% (NEITHER agrees)"
                        + "\n  reclaim window={5} bars, lag tolerance={6} bar(s), confirmation EMA(9): {7}"
                        + "\n  ORDERS ARE MNQ-ONLY. Levels need >=2 sessions of each market's own history."
                        + "\n  Bar counts are reported in the CROSS-MARKET DATA STATUS block on the first MNQ bar.",
                        EsSymbol, YmSymbol, CmRiskPctAPlus, CmRiskPctAMinus, CmRiskPctBPlus,
                        CrossMarketMaxBarsBreakToReclaim, CrossMarketToleranceBars,
                        ConfirmMarketsRequireEma ? "REQUIRED" : "NOT required"));

                if (EnableCrossMarketConfirmation)
                    PrintCrossMarketDataStatus("State.DataLoaded - counts here may be 0 until data streams");

                if (!instrumentOk)
                    PrintLine("MnqTwoStrategies ERROR: instrument '" + master
                        + "' is not MNQ. Spec is MNQ-ONLY - all trading disabled. Apply this strategy to an MNQ chart.");
            }
            else if (State == State.Terminated)
            {
                if (fb != null && logger != null)
                {
                    PrintLine("================ FINAL STATISTICS ================");
                    PrintLine(EnableFakeBreakout
                        ? fb.Stats.Summary("FAKE_BREAKOUT")
                        : "[FAKE_BREAKOUT] DISABLED - did not trade");
                    PrintLine(EnableVectorBreakRetest
                        ? vbr.Stats.Summary("VECTOR_BREAK_RETEST")
                        : "[VECTOR_BREAK_RETEST] DISABLED - did not trade");
                }
                foreach (VectorCandleResearchEngine r in new VectorCandleResearchEngine[]
                         { research15m, research3m, researchS30, researchS15, researchS10, researchS5 })
                    if (r != null) r.Finish();
                if (research != null)
                {
                    research.Finish();
                    PrintLine(string.Format("VECTOR RESEARCH: {0} vector events written to CSV.", research.EventsEmitted));
                    research = null;
                }
                if (researchCsv != null) { researchCsv.Flush(); researchCsv.Close(); researchCsv = null; }

                foreach (ScalpResearchEngine s in new ScalpResearchEngine[]
                         { scalpS30, scalpS15, scalpS10, scalpS5 })
                    if (s != null) s.Finish();
                if (scalp1m != null)
                {
                    scalp1m.Finish();
                    int ev = scalp1m.EventsEmitted, ct = scalp1m.ControlsEmitted;
                    foreach (ScalpResearchEngine s in new ScalpResearchEngine[]
                             { scalpS30, scalpS15, scalpS10, scalpS5 })
                        if (s != null) { ev += s.EventsEmitted; ct += s.ControlsEmitted; }
                    PrintLine(string.Format(
                        "SCALP RESEARCH: {0} structure rows + {1} control rows written to CSV.", ev, ct));
                    scalp1m = null;
                }
                if (scalpCsv != null) { scalpCsv.Flush(); scalpCsv.Close(); scalpCsv = null; }
                if (logger != null) { logger.Close(); logger = null; }
            }
        }

        // ==================================================================
        // Bar dispatch - strict BarsInProgress separation (spec requirement:
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
            // V7 CONFIRMATION SERIES - data only. These branches build ES/YM
            // key levels and run their fake-break detectors. They never call
            // fb/vbr, never size, and never submit an order of any kind.
            // ==============================================================
            if (crossMarketReady && (BarsInProgress == BipEs1 || BarsInProgress == BipEs3
                                     || BarsInProgress == BipYm1 || BarsInProgress == BipYm3))
            {
                bool isEs = BarsInProgress == BipEs1 || BarsInProgress == BipEs3;
                int bip = BarsInProgress;

                // 1m series maintains that market's own key levels
                if (bip == BipEs1 || bip == BipYm1)
                {
                    if (CurrentBars[bip] < 1) return;
                    KeyLevelEngine kl = isEs ? esLevels : ymLevels;
                    DateTime cEtClose = ToEt(Times[bip][0]);
                    bool cNewDay = kl.OnOneMinuteBar(cEtClose.AddMinutes(-1), cEtClose,
                        ToUtc(Times[bip][0]).AddMinutes(-1),
                        Opens[bip][0], Highs[bip][0], Lows[bip][0], Closes[bip][0], Volumes[bip][0]);
                    if (cNewDay)
                    {
                        if (isEs) { esDet1.OnNewDay(); esDet3.OnNewDay(); }
                        else { ymDet1.OnNewDay(); ymDet3.OnNewDay(); }
                        if (CrossMarketDiagnostics > 0) EmitCrossMarketDayReport(isEs, cEtClose);
                    }
                }

                if (CurrentBars[bip] < 11) return;   // vector needs 10 prior completed candles
                cmDiagTime = ToEt(Times[bip][0]);
                int periodMin = (bip == BipEs1 || bip == BipYm1) ? 1 : 3;
                EMA e = bip == BipEs1 ? emaEs1 : bip == BipEs3 ? emaEs3 : bip == BipYm1 ? emaYm1 : emaYm3;
                BarSnap cs = BuildSnap(bip, periodMin, e[0]);
                if (bip == BipEs1) esDet1.OnBar(cs);
                else if (bip == BipEs3) esDet3.OnBar(cs);
                else if (bip == BipYm1) ymDet1.OnBar(cs);
                else ymDet3.OnBar(cs);
                return;   // never falls through to any MNQ trading path
            }

            if (BarsInProgress == BipOneMin)
            {
                if (!statusPrinted && CurrentBars[BipOneMin] >= 0)
                {
                    statusPrinted = true;
                    PrintCrossMarketDataStatus("first MNQ bar - LIVE counts, this is the authoritative one");
                }
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
                            "NEW EXCHANGE DAY - DailyOpen={0:0.00} YH={1:0.00} YL={2:0.00} LWH={3:0.00} LWL={4:0.00} PP={5:0.00}{6}",
                            levels.DailyOpen, levels.YdayHigh, levels.YdayLow, levels.LweekHigh, levels.LweekLow, levels.PP,
                            crossMarketReady
                                ? string.Format(CultureInfo.InvariantCulture,
                                    "\n    {8,-10} YH={0} YL={1} LWH={2} LWL={3}\n    {9,-10} YH={4} YL={5} LWH={6} LWL={7}",
                                    Fmt(esLevels.YdayHigh), Fmt(esLevels.YdayLow), Fmt(esLevels.LweekHigh), Fmt(esLevels.LweekLow),
                                    Fmt(ymLevels.YdayHigh), Fmt(ymLevels.YdayLow), Fmt(ymLevels.LweekHigh), Fmt(ymLevels.LweekLow),
                                    EsSymbol, YmSymbol)
                                : ""));
                    if (EnableFakeBreakout) fb.OnNewDay(etClose);
                    if (EnableVectorBreakRetest) vbr.OnNewDay(etClose);
                }

                // RESEARCH LOGGER: fed the same completed 1m bar the strategies see.
                // It is read-only and its return value is never consulted.
                if (research != null)
                {
                    ResearchBar rb = new ResearchBar();
                    rb.EtClose = etClose; rb.EtOpen = etOpen;
                    rb.Open = Opens[BipOneMin][0]; rb.High = Highs[BipOneMin][0];
                    rb.Low = Lows[BipOneMin][0]; rb.Close = Closes[BipOneMin][0];
                    rb.Volume = Volumes[BipOneMin][0];
                    research.OnBar(rb);
                }
                if (scalp1m != null)
                {
                    ResearchBar sb2 = new ResearchBar();
                    sb2.EtClose = etClose; sb2.EtOpen = etOpen;
                    sb2.Open = Opens[BipOneMin][0]; sb2.High = Highs[BipOneMin][0];
                    sb2.Low = Lows[BipOneMin][0]; sb2.Close = Closes[BipOneMin][0];
                    sb2.Volume = Volumes[BipOneMin][0];
                    scalp1m.OnBar(sb2);
                }

                if (CurrentBars[BipOneMin] < 11) return; // vector needs previous 10 completed candles
                BarSnap snap = BuildSnap(BipOneMin, 1, ema1m[0]);
                if (EnableFakeBreakout) fb.OnOneMinuteBar(snap);
                if (EnableVectorBreakRetest) vbr.OnOneMinuteBar(snap);
            }
            else if (BipSec30 > 0 && (BarsInProgress == BipSec30 || BarsInProgress == BipSec15
                                   || BarsInProgress == BipSec10 || BarsInProgress == BipSec5))
            {
                int sb = BarsInProgress;
                if (CurrentBars[sb] < 1) return;
                int secs = sb == BipSec30 ? 30 : sb == BipSec15 ? 15 : sb == BipSec10 ? 10 : 5;
                ResearchBar rb = MakeResearchBar(sb, secs);
                if (research != null)
                {
                    VectorCandleResearchEngine target =
                        sb == BipSec30 ? researchS30 : sb == BipSec15 ? researchS15
                        : sb == BipSec10 ? researchS10 : researchS5;
                    if (target != null) target.OnBar(rb);
                }
                ScalpResearchEngine starget =
                    sb == BipSec30 ? scalpS30 : sb == BipSec15 ? scalpS15
                    : sb == BipSec10 ? scalpS10 : scalpS5;
                if (starget != null) starget.OnBar(rb);
                return;   // sub-minute series carry NO strategy logic
            }
            else if (BipFiveMin > 0 && (BarsInProgress == BipFiveMin || BarsInProgress == BipThirtyMin
                                     || BarsInProgress == BipSixtyMin))
            {
                // CONTEXT ONLY. These series exist purely so the scalp capture can ask
                // whether a fast move took out structure the slower chart had already
                // confirmed. No strategy logic reads them.
                int sb = BarsInProgress;
                if (CurrentBars[sb] < 1) return;
                int mins = sb == BipFiveMin ? 5 : sb == BipThirtyMin ? 30 : 60;
                HigherTfStructure h = sb == BipFiveMin ? sHtf5 : sb == BipThirtyMin ? sHtf30 : sHtf60;
                if (h != null) h.OnBar(MakeResearchBar(sb, mins * 60));
                return;
            }
            else if (BarsInProgress == BipThreeMin)
            {
                if (htf3m != null && CurrentBars[BipThreeMin] >= 1)
                    htf3m.OnBar(MakeResearchBar(BipThreeMin, 180));
                if (sHtf3 != null && CurrentBars[BipThreeMin] >= 1)
                    sHtf3.OnBar(MakeResearchBar(BipThreeMin, 180));
                if (research3m != null && CurrentBars[BipThreeMin] >= 1)
                    research3m.OnBar(MakeResearchBar(BipThreeMin, 180));
                if (CurrentBars[BipThreeMin] < 11) return;
                if (!EnableFakeBreakout) return;   // 3m series serves FAKE_BREAKOUT only
                BarSnap snap = BuildSnap(BipThreeMin, 3, ema3m[0]);
                fb.OnThreeMinuteBar(snap);
                // VECTOR_BREAK_RETEST uses 15m + 1m ONLY (spec S1) - never fed 3m data.
            }
            else if (BarsInProgress == BipFifteenMin)
            {
                if (htf15m != null && CurrentBars[BipFifteenMin] >= 1)
                    htf15m.OnBar(MakeResearchBar(BipFifteenMin, 900));
                if (sHtf15 != null && CurrentBars[BipFifteenMin] >= 1)
                    sHtf15.OnBar(MakeResearchBar(BipFifteenMin, 900));
                if (research15m != null && CurrentBars[BipFifteenMin] >= 1)
                    research15m.OnBar(MakeResearchBar(BipFifteenMin, 900));
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
        // Execution routing - order names carry the StrategyId prefix, so
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
        // IMnqHost implementation - services the engines call out to
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
        // the OTHER strategy never blocks an entry - EnterPosition routes it through
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

        private VectorCandleResearchEngine MakeResearch(Action<string> sink, string label,
                                                        Func<double> e200, Func<double> e9)
        {
            VectorCandleResearchEngine r = new VectorCandleResearchEngine(levels, sink);
            r.IncludeRegularCandles = ResearchIncludeRegularCandles;
            r.RegularCandleSampleRate = ResearchRegularCandleSampleRate;
            r.TimeframeLabel = label;
            r.Ema200Provider = e200;
            r.Ema9Provider = e9;
            r.Htf3m = htf3m;
            r.Htf15m = htf15m;
            return r;
        }

        private ScalpResearchEngine MakeScalp(Action<string> sink, string label)
        {
            ScalpResearchEngine s = new ScalpResearchEngine(levels, sink);
            s.TimeframeLabel = label;
            s.ControlSampleRate = ScalpControlSampleRate;
            s.ApproachBandPoints = ScalpApproachBandPoints;
            s.RoundNumberStep = ScalpRoundNumberStep;
            s.EmitStartMinutesEt = ScalpEmitStartMinutesEt;
            s.EmitEndMinutesEt = ScalpEmitEndMinutesEt;
            s.AddHtf("3m", sHtf3); s.AddHtf("15m", sHtf15);
            if (sHtf5 != null) { s.AddHtf("5m", sHtf5); s.AddHtf("30m", sHtf30); s.AddHtf("60m", sHtf60); }
            return s;
        }

        private ResearchBar MakeResearchBar(int bip, int periodSeconds)
        {
            ResearchBar rb = new ResearchBar();
            rb.EtClose = ToEt(Times[bip][0]);
            rb.EtOpen = rb.EtClose.AddSeconds(-periodSeconds);
            rb.Open = Opens[bip][0]; rb.High = Highs[bip][0];
            rb.Low = Lows[bip][0]; rb.Close = Closes[bip][0];
            rb.Volume = Volumes[bip][0];
            return rb;
        }

        // Prints the exact status of every data series, including what NinjaTrader
        // actually RESOLVED each symbol to. A zero bar count alone cannot tell you
        // whether the symbol was wrong or the data was missing; the resolved
        // instrument name can.
        private bool statusPrinted;
        private void PrintCrossMarketDataStatus(string when)
        {
            PrintLine("================ CROSS-MARKET DATA STATUS (" + when + ") ================");
            PrintSeriesStatus("MNQ 1m  (control)", BipOneMin);
            PrintSeriesStatus("MNQ 3m  (control)", BipThreeMin);
            PrintSeriesStatus("MNQ 15m (control)", BipFifteenMin);
            PrintSeriesStatus("ES 1m", BipEs1);
            PrintSeriesStatus("ES 3m", BipEs3);
            PrintSeriesStatus("YM 1m", BipYm1);
            PrintSeriesStatus("YM 3m", BipYm3);
            if (BipTick > 0) PrintSeriesStatus("MNQ 1tick (exec)", BipTick);
            if (BipSec30 > 0) PrintSeriesStatus("MNQ 30s", BipSec30);
            if (BipSec15 > 0) PrintSeriesStatus("MNQ 15s", BipSec15);
            if (BipSec10 > 0) PrintSeriesStatus("MNQ 10s", BipSec10);
            if (BipSec5 > 0) PrintSeriesStatus("MNQ 5s", BipSec5);
            PrintLine("  configured symbols: ES='" + EsSymbol + "'  YM='" + YmSymbol + "'");
            PrintLine("  If a confirmation series shows resolved='<unresolved>' the SYMBOL TEXT is wrong.");
            PrintLine("  If it resolves but CurrentBars stays -1/0, NinjaTrader loaded no data for that");
            PrintLine("  instrument over this backtest range (add it in the Strategy Analyzer's data range");
            PrintLine("  or open a chart of that exact contract once so the history is cached).");
            PrintLine("========================================================================");
        }

        private void PrintSeriesStatus(string label, int bip)
        {
            if (bip < 0 || BarsArray == null || bip >= BarsArray.Length || BarsArray[bip] == null)
            {
                PrintLine(string.Format("  {0,-18} BIP=n/a  NOT ATTACHED", label));
                return;
            }
            string resolved = "<unresolved>";
            try
            {
                if (BarsArray[bip].Instrument != null && BarsArray[bip].Instrument.MasterInstrument != null)
                    resolved = BarsArray[bip].Instrument.FullName;
            }
            catch (Exception) { }
            int cb = (CurrentBars != null && bip < CurrentBars.Length) ? CurrentBars[bip] : -1;
            string last = "n/a";
            try { if (cb >= 0) last = ToEt(Times[bip][0]).ToString("yyyy-MM-dd HH:mm", CultureInfo.InvariantCulture) + " ET"; }
            catch (Exception) { }
            string first = "n/a";
            try { if (cb >= 0) first = ToEt(Times[bip][cb]).ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture); }
            catch (Exception) { }
            PrintLine(string.Format(CultureInfo.InvariantCulture,
                "  {0,-18} BIP={1,-3} resolved='{2}'  Count={3}  CurrentBars={4}  first={5}  last={6}",
                label, bip, resolved, BarsArray[bip].Count, cb, first, last));
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
        // this market had no data" - the failure mode that silently mis-graded a
        // whole backtest.
        private void EmitCrossMarketDayReport(bool isEs, DateTime etClose)
        {
            cmDiagTime = etClose;
            KeyLevelEngine kl = isEs ? esLevels : ymLevels;
            CrossMarketConfirmDetector d1 = isEs ? esDet1 : ymDet1;
            CrossMarketConfirmDetector d3 = isEs ? esDet3 : ymDet3;
            string mk = isEs ? EsSymbol : YmSymbol;
            bool levelsOk = !double.IsNaN(kl.YdayHigh) || !double.IsNaN(kl.YdayLow)
                         || !double.IsNaN(kl.LweekHigh) || !double.IsNaN(kl.LweekLow);
            CmDiag(string.Format(CultureInfo.InvariantCulture,
                "{0:yyyy-MM-dd} {1} levels: YH={2} YL={3} LWH={4} LWL={5}{6}",
                etClose, mk, Fmt(kl.YdayHigh), Fmt(kl.YdayLow), Fmt(kl.LweekHigh), Fmt(kl.LweekLow),
                levelsOk ? "" : "   <<< ALL NaN - this market cannot be evaluated, it is NOT declining to confirm"));
            CmDiag("    " + d1.DailyTally());
            CmDiag("    " + d3.DailyTally());
        }

        private static string Fmt(double v)
        {
            return double.IsNaN(v) ? "NaN" : v.ToString("0.00", CultureInfo.InvariantCulture);
        }

        // ==================================================================
        // V7 cross-market confirmation - READ-ONLY host queries.
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
                det = tfMinutes == 1 ? ymDet1 : tfMinutes == 3 ? ymDet3 : null;

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
