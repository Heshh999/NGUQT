// ============================================================================
// MnqTwoStrategiesShared.cs
// Shared READ-ONLY utilities for the two independent MNQ-only strategies:
//   FAKE_BREAKOUT and VECTOR_BREAK_RETEST
//
// Spec sections implemented here:
//   - "CRITICAL ARCHITECTURE: KEEP THE TWO STRATEGIES COMPLETELY SEPARATE"
//     (enums StrategyId; shared code restricted to read-only utilities)
//   - "CRITICAL KEY-LEVEL ENGINE / STRATEGY-TO-LEVEL MAPPING" (KeyLevelId)
//   - "GLOBAL: TRADERS REALITY VECTOR CLASSIFICATION" (VectorClassifier)
//   - "SHARED TAKE-PROFIT KEY-LEVEL ENGINE" sections A/B/C (KeyLevelEngine)
//   - "GLOBAL: POSITION SIZING" (PositionSizer)
//   - "IMPLEMENTATION NOTES FOR CLAUDE" logging list (TradeRecord/MnqLogger)
//
// NOTE: Per the spec's hard separation rule, NO active setup object lives in
// this file. Engines never share mutable state.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqTwo
{
    // ------------------------------------------------------------------
    // Spec: "Create an explicit strategy identifier"
    // ------------------------------------------------------------------
    public enum StrategyId
    {
        FAKE_BREAKOUT,
        VECTOR_BREAK_RETEST
    }

    // Spec: "Optional internal codes" GREEN=+3 RED=-3 BLUE=+2 VIOLET=-2 REG=+1/-1
    public enum VectorType
    {
        GREEN_VECTOR = 3,
        BLUE_VECTOR = 2,
        REGULAR_BULLISH = 1,
        REGULAR_BEARISH = -1,
        VIOLET_VECTOR = -2,
        RED_VECTOR = -3
    }

    // Spec: "Define explicit level identifiers" (setup-trigger levels)
    public enum KeyLevelId
    {
        YDAY_HIGH,
        YDAY_LOW,
        LWEEK_HIGH,
        LWEEK_LOW,
        DAILY_OPEN
    }

    // Spec: "The shared take-profit engine contains exactly 18 SELECTABLE target levels"
    public enum TpLevelId
    {
        M0, M1, M2, M3, M4, M5,
        PP,
        DAILY_OPEN,
        YDAY_HIGH, YDAY_LOW,
        LWEEK_HIGH, LWEEK_LOW,
        R1, R3,
        S1, S2,
        PSY_HIGH, PSY_LOW
    }

    public enum TradeDirection { Long, Short }

    // Spec (Fake Breakout section 12 / shared engine section E):
    // 'If the exact definition of "first target successfully broken" has not been
    //  finalized, keep that break-confirmation method configurable.'
    public enum FbTargetBreakMode
    {
        Touch,                    // price touches the target level (1m high/low)
        OneMinuteCloseBeyond,     // completed 1m close beyond the target
        ThreeMinuteCloseBeyond    // completed 3m close beyond the target
    }

    // Ambiguity FB-6: meaning of "FIRST eligible 15-minute candle" for the A- grade.
    public enum FbGradeBasis
    {
        ValidityCandleNumber,     // literal: validity candle #1 after the breakout candle
        FirstTradableCandle       // first validity candle at/after 9:30 ET
    }

    // ------------------------------------------------------------------
    // Spec: "GLOBAL: TRADERS REALITY VECTOR CLASSIFICATION"
    // ------------------------------------------------------------------
    public static class VectorClassifier
    {
        // avgVol10          = SUM(volume[1]..volume[10]) / 10       (previous 10 completed)
        // highestVolSpread10= max(volume[i]*(high[i]-low[i])) i=1..10
        public static VectorType Classify(double open, double high, double low, double close,
                                          double volume, double avgVol10, double highestVolSpread10)
        {
            // Spec: "Close > Open is bullish. Close == Open follows the bearish branch."
            bool bullish = close > open;
            double volumeSpread = volume * (high - low);

            // Spec: "High/climax logic has priority over medium-vector logic."
            if (volume >= 2.0 * avgVol10 || volumeSpread >= highestVolSpread10)
                return bullish ? VectorType.GREEN_VECTOR : VectorType.RED_VECTOR;

            if (volume >= 1.5 * avgVol10)
                return bullish ? VectorType.BLUE_VECTOR : VectorType.VIOLET_VECTOR;

            return bullish ? VectorType.REGULAR_BULLISH : VectorType.REGULAR_BEARISH;
        }

        public static bool IsRegular(VectorType v)
        {
            return v == VectorType.REGULAR_BULLISH || v == VectorType.REGULAR_BEARISH;
        }
    }

    // ------------------------------------------------------------------
    // Immutable completed-candle snapshot handed to the engines.
    // Built ONLY inside the matching BarsInProgress branch so no engine can
    // accidentally read data from the wrong series (spec: no repainting,
    // completed candles only).
    // ------------------------------------------------------------------
    public class BarSnap
    {
        public DateTime EtOpen;     // bar open time, US-Eastern
        public DateTime EtClose;    // bar close time, US-Eastern
        public double Open;
        public double High;
        public double Low;
        public double Close;
        public double Volume;
        public VectorType Vector;   // Traders Reality vector of this completed candle
        public double Ema9;         // EMA(close,9) of this series at this completed candle
        public int PeriodMinutes;   // 1, 3 or 15
    }

    // ------------------------------------------------------------------
    // One take-profit target event. Equal-price levels are merged into one
    // event keeping all names (spec, shared engine section C).
    // ------------------------------------------------------------------
    public class TpTarget
    {
        public double Price;
        public List<TpLevelId> Names;

        public TpTarget() { Names = new List<TpLevelId>(); }

        public string NameString()
        {
            StringBuilder sb = new StringBuilder();
            for (int i = 0; i < Names.Count; i++)
            {
                if (i > 0) sb.Append("+");
                sb.Append(Names[i].ToString());
            }
            return sb.ToString();
        }
    }

    // ------------------------------------------------------------------
    // Spec: "SHARED TAKE-PROFIT KEY-LEVEL ENGINE" sections A + B + C, and the
    // trigger-level values for both strategies.
    //
    // Levels are aggregated from completed 1-minute bars:
    //   DAILY_OPEN  = open of the first 1m bar of the exchange day
    //                 (TR getdayOpen: "open at the start of a new exchange day /
    //                  exchange midnight" — day boundary configurable, SH-1)
    //   YDAY_HIGH/LOW   = previous completed exchange day's high/low
    //   LWEEK_HIGH/LOW  = previous completed week's high/low (futures week,
    //                     boundary configurable, default Sunday 18:00 ET)
    //   Pivots/M-levels = Traders Reality formulas from previous day H/L/C
    //   PSY_HIGH/LOW    = high/low of the first PsyWindowHours of the new week
    //                     (best-effort port; TR source not supplied — SH-1)
    // ------------------------------------------------------------------
    public class KeyLevelEngine
    {
        private class Agg
        {
            public double O; public double H; public double L; public double C;
            public bool Valid;
        }

        private Agg curDay;
        private Agg prevDay;
        private Agg curWeek;
        private Agg prevWeek;
        private DateTime curDayKey = DateTime.MinValue;
        private DateTime curWeekKey = DateTime.MinValue;
        private double dailyOpen = double.NaN;

        // Psy-level tracking (weekly window)
        private DateTime weekAnchorEt = DateTime.MinValue;
        private double psyHiAccum = double.NaN;
        private double psyLoAccum = double.NaN;
        private bool psyWindowClosed;
        private double psyHigh = double.NaN;
        private double psyLow = double.NaN;

        // Configuration (set once by the host strategy before data starts)
        public int DayStartMinutesEt = 0;       // 0 = exchange midnight ET (TR getdayOpen semantics)
        public int WeekStartMinutesEt = 1080;   // Sunday 18:00 ET = futures week open
        public int PsyWindowHours = 8;          // first 8 hours of the week (TR psy behavior)

        // Feed one COMPLETED 1m bar. Returns true when a new exchange day started.
        public bool OnOneMinuteBar(DateTime etOpen, DateTime etClose, double o, double h, double l, double c)
        {
            bool newDay = false;

            // ---- day roll ----
            DateTime dayShift = etOpen.AddMinutes(-DayStartMinutesEt);
            DateTime dayKey = dayShift.Date;
            if (dayKey != curDayKey)
            {
                if (curDay != null && curDay.Valid)
                    prevDay = curDay;
                curDay = new Agg();
                curDay.O = o; curDay.H = h; curDay.L = l; curDay.C = c; curDay.Valid = true;
                dailyOpen = o;                       // TR getdayOpen
                curDayKey = dayKey;
                newDay = true;
            }
            else
            {
                if (curDay == null) { curDay = new Agg(); curDay.O = o; curDay.H = h; curDay.L = l; curDay.Valid = true; }
                if (h > curDay.H) curDay.H = h;
                if (l < curDay.L) curDay.L = l;
                curDay.C = c;
            }

            // ---- week roll ----
            DateTime weekShift = etOpen.AddMinutes(-WeekStartMinutesEt);
            DateTime weekKey = weekShift.Date.AddDays(-(int)weekShift.Date.DayOfWeek); // back to Sunday
            if (weekKey != curWeekKey)
            {
                if (curWeek != null && curWeek.Valid)
                    prevWeek = curWeek;
                curWeek = new Agg();
                curWeek.O = o; curWeek.H = h; curWeek.L = l; curWeek.C = c; curWeek.Valid = true;
                curWeekKey = weekKey;

                // new psy window
                weekAnchorEt = weekKey.AddMinutes(WeekStartMinutesEt);
                psyHiAccum = h; psyLoAccum = l;
                psyWindowClosed = false;
                psyHigh = double.NaN; psyLow = double.NaN;
            }
            else
            {
                if (curWeek == null) { curWeek = new Agg(); curWeek.O = o; curWeek.H = h; curWeek.L = l; curWeek.Valid = true; }
                if (h > curWeek.H) curWeek.H = h;
                if (l < curWeek.L) curWeek.L = l;
                curWeek.C = c;
            }

            // ---- psy window (first PsyWindowHours of the week) ----
            if (!psyWindowClosed && weekAnchorEt != DateTime.MinValue)
            {
                if (etOpen < weekAnchorEt.AddHours(PsyWindowHours))
                {
                    if (double.IsNaN(psyHiAccum) || h > psyHiAccum) psyHiAccum = h;
                    if (double.IsNaN(psyLoAccum) || l < psyLoAccum) psyLoAccum = l;
                }
                else
                {
                    psyWindowClosed = true;
                    psyHigh = psyHiAccum;
                    psyLow = psyLoAccum;
                }
            }

            return newDay;
        }

        // ---- Trigger-level values ------------------------------------------------
        public double DailyOpen { get { return dailyOpen; } }
        public double YdayHigh { get { return prevDay != null && prevDay.Valid ? prevDay.H : double.NaN; } }
        public double YdayLow { get { return prevDay != null && prevDay.Valid ? prevDay.L : double.NaN; } }
        public double LweekHigh { get { return prevWeek != null && prevWeek.Valid ? prevWeek.H : double.NaN; } }
        public double LweekLow { get { return prevWeek != null && prevWeek.Valid ? prevWeek.L : double.NaN; } }

        public double GetTriggerLevelPrice(KeyLevelId id)
        {
            switch (id)
            {
                case KeyLevelId.YDAY_HIGH: return YdayHigh;
                case KeyLevelId.YDAY_LOW: return YdayLow;
                case KeyLevelId.LWEEK_HIGH: return LweekHigh;
                case KeyLevelId.LWEEK_LOW: return LweekLow;
                case KeyLevelId.DAILY_OPEN: return DailyOpen;
            }
            return double.NaN;
        }

        // ---- Spec section B: Traders Reality pivot / M-level formulas ------------
        // PP = (dayHigh + dayLow + dayClose) / 3      (previous completed day)
        // R1 = 2*PP - dayLow          S1 = 2*PP - dayHigh
        // R2 = PP - S1 + R1           S2 = PP - R1 + S1
        // R3 = 2*PP + dayHigh - 2*dayLow
        // S3 = 2*PP - (2*dayHigh - dayLow)
        // M0=(S2+S3)/2 M1=(S1+S2)/2 M2=(PP+S1)/2 M3=(PP+R1)/2 M4=(R1+R2)/2 M5=(R2+R3)/2
        // R2/S3 are calculated internally but are NOT selectable targets (spec).
        public double PP
        {
            get
            {
                if (prevDay == null || !prevDay.Valid) return double.NaN;
                return (prevDay.H + prevDay.L + prevDay.C) / 3.0;
            }
        }
        public double R1 { get { double pp = PP; return double.IsNaN(pp) ? double.NaN : 2.0 * pp - prevDay.L; } }
        public double S1 { get { double pp = PP; return double.IsNaN(pp) ? double.NaN : 2.0 * pp - prevDay.H; } }
        public double R2 { get { double pp = PP; return double.IsNaN(pp) ? double.NaN : pp - S1 + R1; } }
        public double S2 { get { double pp = PP; return double.IsNaN(pp) ? double.NaN : pp - R1 + S1; } }
        public double R3 { get { double pp = PP; return double.IsNaN(pp) ? double.NaN : 2.0 * pp + prevDay.H - 2.0 * prevDay.L; } }
        public double S3 { get { double pp = PP; return double.IsNaN(pp) ? double.NaN : 2.0 * pp - (2.0 * prevDay.H - prevDay.L); } }
        public double M0 { get { double a = S2, b = S3; return (double.IsNaN(a) || double.IsNaN(b)) ? double.NaN : (a + b) / 2.0; } }
        public double M1 { get { double a = S1, b = S2; return (double.IsNaN(a) || double.IsNaN(b)) ? double.NaN : (a + b) / 2.0; } }
        public double M2 { get { double a = PP, b = S1; return (double.IsNaN(a) || double.IsNaN(b)) ? double.NaN : (a + b) / 2.0; } }
        public double M3 { get { double a = PP, b = R1; return (double.IsNaN(a) || double.IsNaN(b)) ? double.NaN : (a + b) / 2.0; } }
        public double M4 { get { double a = R1, b = R2; return (double.IsNaN(a) || double.IsNaN(b)) ? double.NaN : (a + b) / 2.0; } }
        public double M5 { get { double a = R2, b = R3; return (double.IsNaN(a) || double.IsNaN(b)) ? double.NaN : (a + b) / 2.0; } }
        public double PsyHigh { get { return psyHigh; } }
        public double PsyLow { get { return psyLow; } }

        public double GetTpLevelPrice(TpLevelId id)
        {
            switch (id)
            {
                case TpLevelId.M0: return M0;
                case TpLevelId.M1: return M1;
                case TpLevelId.M2: return M2;
                case TpLevelId.M3: return M3;
                case TpLevelId.M4: return M4;
                case TpLevelId.M5: return M5;
                case TpLevelId.PP: return PP;
                case TpLevelId.DAILY_OPEN: return DailyOpen;
                case TpLevelId.YDAY_HIGH: return YdayHigh;
                case TpLevelId.YDAY_LOW: return YdayLow;
                case TpLevelId.LWEEK_HIGH: return LweekHigh;
                case TpLevelId.LWEEK_LOW: return LweekLow;
                case TpLevelId.R1: return R1;
                case TpLevelId.R3: return R3;
                case TpLevelId.S1: return S1;
                case TpLevelId.S2: return S2;
                case TpLevelId.PSY_HIGH: return PsyHigh;
                case TpLevelId.PSY_LOW: return PsyLow;
            }
            return double.NaN;
        }

        // ---- Spec section C: NEXT-KEY-LEVEL SELECTION ALGORITHM ------------------
        // LONG : all valid levels STRICTLY ABOVE referencePrice, sorted low->high.
        // SHORT: all valid levels STRICTLY BELOW referencePrice, sorted high->low.
        // Equal-price levels are one target event (all names kept).
        // NaN levels and levels exactly equal to the reference are ignored.
        public List<TpTarget> GetSortedTargets(TradeDirection direction, double referencePrice,
                                               Func<TpLevelId, bool> levelEnabled, double mergeTolerance)
        {
            List<TpTarget> result = new List<TpTarget>();
            Array all = Enum.GetValues(typeof(TpLevelId));
            List<KeyValuePair<TpLevelId, double>> candidates = new List<KeyValuePair<TpLevelId, double>>();

            foreach (TpLevelId id in all)
            {
                if (levelEnabled != null && !levelEnabled(id)) continue;
                double p = GetTpLevelPrice(id);
                if (double.IsNaN(p)) continue;
                if (direction == TradeDirection.Long)
                {
                    if (p > referencePrice + mergeTolerance * 0.5)
                        candidates.Add(new KeyValuePair<TpLevelId, double>(id, p));
                }
                else
                {
                    if (p < referencePrice - mergeTolerance * 0.5)
                        candidates.Add(new KeyValuePair<TpLevelId, double>(id, p));
                }
            }

            candidates.Sort(delegate(KeyValuePair<TpLevelId, double> a, KeyValuePair<TpLevelId, double> b)
            {
                return direction == TradeDirection.Long
                    ? a.Value.CompareTo(b.Value)
                    : b.Value.CompareTo(a.Value);
            });

            foreach (KeyValuePair<TpLevelId, double> kv in candidates)
            {
                if (result.Count > 0 && Math.Abs(result[result.Count - 1].Price - kv.Value) <= mergeTolerance)
                {
                    result[result.Count - 1].Names.Add(kv.Key); // same price = one target event
                }
                else
                {
                    TpTarget t = new TpTarget();
                    t.Price = kv.Value;
                    t.Names.Add(kv.Key);
                    result.Add(t);
                }
            }
            return result;
        }
    }

    // ------------------------------------------------------------------
    // Spec: "GLOBAL: POSITION SIZING" — MNQ ONLY, $2 per index point.
    // ------------------------------------------------------------------
    public static class PositionSizer
    {
        // Spec: "Never use NQ's $20-per-point contract value in this version."
        public const double MnqDollarsPerPoint = 2.0;

        // RiskDollars = AccountBalance * RiskPercent
        // RiskPerContract = StopDistancePoints * 2
        // Contracts = floor(RiskDollars / RiskPerContract)   (always round DOWN)
        public static int Contracts(double accountBalance, double riskPercent, double stopDistancePoints,
                                    out double riskDollars, out double riskPerContract)
        {
            riskDollars = accountBalance * (riskPercent / 100.0);
            riskPerContract = stopDistancePoints * MnqDollarsPerPoint;
            if (stopDistancePoints <= 0 || accountBalance <= 0 || riskPercent <= 0)
                return 0;
            return (int)Math.Floor(riskDollars / riskPerContract);
        }
    }

    // ------------------------------------------------------------------
    // Spec: logging list under "IMPLEMENTATION NOTES FOR CLAUDE".
    // One record is written per exit leg (VBR can exit in TP90 + runner + stop
    // legs); legs of the same trade share TradeId.
    // ------------------------------------------------------------------
    public class TradeRecord
    {
        public StrategyId Strategy;
        public string TradeId;
        public string Grade;                    // A+ / A- / B+
        public TradeDirection Direction;
        public DateTime ParentTriggerTimeEt;
        public string ParentLevelName;
        public double ParentLevelPrice;
        public string ParentVector;
        public int ValidityCandleNumber;
        public int EntryTimeframeMinutes;
        public string EntryPatternType;
        public DateTime EntryTimeEt;
        public double EntryPrice;
        public double StopPrice;
        public double StopDistancePoints;
        public double AccountBalance;
        public double RiskPercent;
        public double RiskDollars;
        public int Contracts;                   // total entry quantity
        public string TargetLevelNames;         // first/active target at entry
        public double TargetPrice;
        public double TargetDistancePoints;
        public string ExitLeg;                  // STOP / TP90 / RUNNER / RUNNER_EMA3M / SESSION_CLOSE
        public int ExitQty;
        public DateTime ExitTimeEt;
        public double ExitPrice;
        public string ExitReason;
        public double PnlPoints;                // per contract, this leg
        public double PnlDollars;               // this leg total
        public double RMultiple;                // this leg points / stop distance points
        public double MfePoints;
        public double MaePoints;
        public int ReentryNumber;               // 0 = original entry
        public bool ParentFormedPremarket;
        public bool EntryFormedAfter930;

        public static string CsvHeader()
        {
            return "Strategy,TradeId,Grade,Direction,ParentTriggerTimeEt,ParentLevel,ParentLevelPrice,ParentVector,"
                 + "ValidityCandle,EntryTf,EntryPattern,EntryTimeEt,EntryPrice,StopPrice,StopDistPts,"
                 + "AccountBalance,RiskPct,RiskDollars,Contracts,TargetLevels,TargetPrice,TargetDistPts,"
                 + "ExitLeg,ExitQty,ExitTimeEt,ExitPrice,ExitReason,PnlPoints,PnlDollars,RMultiple,"
                 + "MFEpts,MAEpts,ReentryNumber,ParentPremarket,EntryAfter930";
        }

        public string ToCsv()
        {
            CultureInfo ci = CultureInfo.InvariantCulture;
            return string.Join(",", new string[]
            {
                Strategy.ToString(), TradeId, Grade, Direction.ToString(),
                ParentTriggerTimeEt.ToString("yyyy-MM-dd HH:mm", ci),
                ParentLevelName, ParentLevelPrice.ToString("0.00", ci), ParentVector,
                ValidityCandleNumber.ToString(ci), EntryTimeframeMinutes.ToString(ci), EntryPatternType,
                EntryTimeEt.ToString("yyyy-MM-dd HH:mm", ci),
                EntryPrice.ToString("0.00", ci), StopPrice.ToString("0.00", ci), StopDistancePoints.ToString("0.00", ci),
                AccountBalance.ToString("0.00", ci), RiskPercent.ToString("0.##", ci), RiskDollars.ToString("0.00", ci),
                Contracts.ToString(ci), TargetLevelNames, TargetPrice.ToString("0.00", ci), TargetDistancePoints.ToString("0.00", ci),
                ExitLeg, ExitQty.ToString(ci),
                ExitTimeEt.ToString("yyyy-MM-dd HH:mm", ci),
                ExitPrice.ToString("0.00", ci), ExitReason,
                PnlPoints.ToString("0.00", ci), PnlDollars.ToString("0.00", ci), RMultiple.ToString("0.00", ci),
                MfePoints.ToString("0.00", ci), MaePoints.ToString("0.00", ci),
                ReentryNumber.ToString(ci),
                ParentFormedPremarket ? "1" : "0", EntryFormedAfter930 ? "1" : "0"
            });
        }
    }

    // ------------------------------------------------------------------
    // Per-strategy win/loss + R + MFE/MAE statistics (spec: "Win/loss and
    // backtest statistics", "R-multiple reporting", "MFE / MAE").
    // ------------------------------------------------------------------
    public class StrategyStats
    {
        public int ClosedTrades;
        public int Wins;
        public int Losses;
        public double NetDollars;
        public double TotalR;
        public double SumMfePoints;
        public double SumMaePoints;
        public double LargestWin;
        public double LargestLoss;

        public void AddClosedTrade(double netPnlDollars, double netR, double mfePts, double maePts)
        {
            ClosedTrades++;
            if (netPnlDollars > 0) Wins++; else Losses++;
            NetDollars += netPnlDollars;
            TotalR += netR;
            SumMfePoints += mfePts;
            SumMaePoints += maePts;
            if (netPnlDollars > LargestWin) LargestWin = netPnlDollars;
            if (netPnlDollars < LargestLoss) LargestLoss = netPnlDollars;
        }

        public string Summary(string name)
        {
            double winRate = ClosedTrades > 0 ? 100.0 * Wins / ClosedTrades : 0;
            double avgR = ClosedTrades > 0 ? TotalR / ClosedTrades : 0;
            double avgMfe = ClosedTrades > 0 ? SumMfePoints / ClosedTrades : 0;
            double avgMae = ClosedTrades > 0 ? SumMaePoints / ClosedTrades : 0;
            return string.Format(CultureInfo.InvariantCulture,
                "[{0}] trades={1} wins={2} losses={3} winRate={4:0.0}% net=${5:0.00} totalR={6:0.00} avgR={7:0.00} avgMFE={8:0.00}pts avgMAE={9:0.00}pts largestWin=${10:0.00} largestLoss=${11:0.00}",
                name, ClosedTrades, Wins, Losses, winRate, NetDollars, TotalR, avgR, avgMfe, avgMae, LargestWin, LargestLoss);
        }
    }

    // ------------------------------------------------------------------
    // Diagnostic + CSV trade logger. Every line carries the StrategyId
    // (spec: "Every order and every log record must contain StrategyId").
    // ------------------------------------------------------------------
    public class MnqLogger
    {
        private readonly Action<string> print;
        private StreamWriter csv;

        public MnqLogger(Action<string> printAction, string csvPath, bool enableCsv)
        {
            print = printAction;
            if (enableCsv && !string.IsNullOrEmpty(csvPath))
            {
                try
                {
                    bool exists = File.Exists(csvPath);
                    csv = new StreamWriter(csvPath, true);
                    if (!exists)
                        csv.WriteLine(TradeRecord.CsvHeader());
                    csv.Flush();
                }
                catch (Exception)
                {
                    csv = null; // logging must never kill the strategy
                }
            }
        }

        public void Diag(StrategyId id, DateTime etTime, string msg)
        {
            if (print != null)
                print(string.Format(CultureInfo.InvariantCulture, "{0:yyyy-MM-dd HH:mm} ET [{1}] {2}", etTime, id, msg));
        }

        public void DiagGlobal(DateTime etTime, string msg)
        {
            if (print != null)
                print(string.Format(CultureInfo.InvariantCulture, "{0:yyyy-MM-dd HH:mm} ET [GLOBAL] {1}", etTime, msg));
        }

        public void Trade(TradeRecord r)
        {
            if (print != null)
                print("TRADE " + r.ToCsv());
            if (csv != null)
            {
                try { csv.WriteLine(r.ToCsv()); csv.Flush(); }
                catch (Exception) { }
            }
        }

        public void Close()
        {
            if (csv != null)
            {
                try { csv.Flush(); csv.Close(); } catch (Exception) { }
                csv = null;
            }
        }
    }

    // ------------------------------------------------------------------
    // Host services the engines need from the NinjaTrader strategy.
    // Engines only call OUT through this interface; they never touch each
    // other or the other engine's orders (spec hard separation rule).
    // ------------------------------------------------------------------
    public interface IMnqHost
    {
        KeyLevelEngine Levels { get; }
        double AccountBalance { get; }
        double TickSize { get; }
        bool InstrumentOk { get; }

        // 9:30-11:30 ET gate applied to the SIGNAL time (entry submission)
        bool IsEntryTimeAllowed(DateTime etTime);
        // >= 9:30 ET gate applied to pattern-forming bar OPEN times
        bool IsAtOrAfterSessionStart(DateTime etTime);
        // past the 11:30 cutoff (used to fast-expire setups that can no longer enter)
        bool IsAfterEntryCutoff(DateTime etTime);

        // simultaneous-position policy (spec: expose as configurable setting)
        bool CanOpenPosition(StrategyId id);

        bool TpLevelEnabled(TpLevelId id);

        int  EnterPosition(StrategyId id, TradeDirection dir, int qty, string signalName);
        void SubmitOrUpdateStop(StrategyId id, TradeDirection dir, int qty, double stopPrice,
                                string stopName, string fromEntrySignal);
        void ExitMarket(StrategyId id, TradeDirection dir, int qty, string exitName, string fromEntrySignal);

        void Diag(StrategyId id, string msg);
        void LogTrade(TradeRecord rec);
        double RoundToTick(double price);
    }
}
