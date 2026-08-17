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
    // V6.1 - the take-profit universe grows from 18 to 21 selectable levels with the
    // addition of TradingView's built-in Session VWAP and its band pair. This is a
    // deliberate SPEC CHANGE requested by the user, not a fix.
    public enum TpLevelId
    {
        M0, M1, M2, M3, M4, M5,
        PP,
        DAILY_OPEN,
        YDAY_HIGH, YDAY_LOW,
        LWEEK_HIGH, LWEEK_LOW,
        R1, R3,
        S1, S2,
        PSY_HIGH, PSY_LOW,
        VWAP, VWAP_BAND_HIGH, VWAP_BAND_LOW
    }

    public enum TradeDirection { Long, Short }

    // V6 U1 - LOCKED: the Fake Breakout first target is "successfully broken" ONLY
    // by a COMPLETED 1-MINUTE CLOSE beyond it in the trade direction; a wick/touch
    // does NOT count. OneMinuteCloseBeyond is therefore the exact-spec default; the
    // other members are retained for research only.
    public enum FbTargetBreakMode
    {
        Touch,                    // LEGACY research: price touches the level (1m high/low)
        OneMinuteCloseBeyond,     // V6 U1 exact-spec: completed 1m close beyond the target
        ThreeMinuteCloseBeyond    // LEGACY research: completed 3m close beyond the target
    }

    // FB grade basis. V5 correction Fix 7 makes FirstTradableCandle the mandated
    // default: A- = entry in the FIRST 15m candle in which a fresh lower-timeframe
    // entry is actually eligible (premarket candles cannot host an entry).
    public enum FbGradeBasis
    {
        ValidityCandleNumber,     // LEGACY research: literal validity candle #1
        FirstTradableCandle       // V5 default: first candle where entries are permitted
    }

    // V6 U2 - LOCKED: a VBR key level is REACHED on a wick/touch of the target
    // price; a completed close beyond it is NOT required. IntrabarTouch is the
    // exact-spec default.
    public enum TargetReachedMode
    {
        IntrabarTouch,            // V6 U2 exact-spec: 1m high/low touches the target price
        OneMinuteCloseBeyond      // LEGACY research: completed 1m close beyond the target
    }

    // Traders Reality calcPsyLevels psyType ('forex' vs 'crypto' path in the
    // supplied library source). MNQ uses the forex path by default.
    public enum PsyLevelType
    {
        Forex,                    // Monday 00:00-08:00 GMT session (library source)
        Crypto                    // Saturday 22:00-06:00 GMT/GMT+1 by Sydney DST
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
    // V5 correction Fix 4 - faithful port of the SUPPLIED Traders Reality
    // library (Traders_Reality_Lib, Pine v5):
    //
    //   DAILY_OPEN - TR getdayOpen(): dlyOpen := open on ta.change(time('D')),
    //     i.e. the open of the first bar of the instrument's new exchange day.
    //     For CME MNQ on TradingView the daily bar boundary is the session open
    //     at 17:00 CT = 18:00 ET, so the faithful default here is 18:00 ET
    //     (DayStartMinutesEt = 1080). The library's "basically exchange
    //     midnight" comment describes forex/crypto symbols; set the
    //     compatibility parameter to 0 to reproduce that literal behavior.
    //
    //   YDAY_HIGH/LOW, LWEEK_HIGH/LOW - CONFIRMED against TR_MAIN (main indicator):
    //     dayHigh/dayLow = f_security(tickerid,'D',high/low,false) plotted as
    //     "YDay Hi"/"YDay Lo" (lines 309-310, 348-351); weekHigh/weekLow =
    //     f_security(tickerid,'W',...) plotted as "LWeek Hi"/"LWeek Lo"
    //     (lines 337-338, 353-356). The non-repainting wrapper
    //         request.security(sym,res,src[isrealtime?1:0])[isrealtime?0:1]
    //     returns the PREVIOUS COMPLETED daily/weekly value on both the
    //     historical and realtime branches - i.e. exactly these prev-day /
    //     prev-week aggregates, changing only at the boundary.
    //
    //   PSY_HIGH/LOW - direct port of calcPsyLevels(), with psyType taken from
    //     TR_MAIN line 243: syminfo.type == 'forex' ? 'forex' : 'crypto'. MNQ is
    //     'futures', so the CRYPTO path is the faithful default. See
    //     IsInPsySession for the session windows and the 4H-grid note.
    //     psyHi/psyLo initialize on the first bar of the session, extend with
    //     max(high)/min(low) while in session, and hold their last value outside
    //     it. Sydney DST comes from a port of calcDst().
    //
    //   Pivots/M-levels - CONFIRMED against TR_MAIN: pivotPoint/R/S computed from
    //     the same previous-completed-day f_security values (lines 316-324) and
    //     m0C..m5C (lines 569-574) match the implemented formulas exactly.
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

        // ---- Session VWAP + bands (TradingView built-in "VWAP", Anchor = Session) ----
        // TradingView computes, cumulatively from the session anchor:
        //     vwap     = SUM(src*vol) / SUM(vol)                      (src = hlc3 by default)
        //     variance = SUM(vol*src*src)/SUM(vol) - vwap^2   (floored at 0)
        //     band     = vwap +/- multiplier * sqrt(variance)
        // For an ETH futures symbol the Session anchor resets at the exchange-day
        // open (18:00 ET), which is the same boundary DayStartMinutesEt already uses.
        private double vwapSumSrcVol;
        private double vwapSumVol;
        private double vwapSumSrcSrcVol;

        // Psy-level state (TR calcPsyLevels port)
        private bool wasInPsySession;
        private double psyHigh = double.NaN;
        private double psyLow = double.NaN;

        // Configuration (set once by the host strategy before data starts)
        public int DayStartMinutesEt = 1080;    // 18:00 ET = CME exchange-day open (TR time('D') boundary for MNQ); 0 = literal "exchange midnight"
        public int WeekStartMinutesEt = 1080;   // Sunday 18:00 ET = futures week open (TradingView weekly bar boundary for MNQ)
        // TR_MAIN psyType. The AUTOMATIC derivation (L243) is
        //     syminfo.type == 'forex' ? 'forex' : 'crypto'
        // which would give 'crypto' for MNQ, but TR_MAIN also exposes
        // overridePsyType + a manual psyType selector (L241-242) for exactly this
        // case, and the user runs the FOREX path for MNQ psy levels. That is the
        // configured default here.
        // Practical note: the forex window (Monday 00:00-08:00 GMT = Sun 20:00 ->
        // Mon 04:00 ET) sits fully inside CME trading hours year-round and has no
        // DST dependency; the crypto window opens ~2h before the Sunday 18:00 ET
        // futures reopen while Sydney is in DST.
        public PsyLevelType PsyType = PsyLevelType.Forex;
        // COMPATIBILITY ONLY (default OFF): TR tests session membership through
        // time('240', session, gmt). Reproducing that needs TradingView's 4H-bar
        // anchor, which cannot be verified from the source alone - and anchoring
        // the grid to the exchange-day open makes the source's own forex branch
        // ('0000-0800:2' GMT) fall permanently out of session, which cannot be the
        // intended behavior. The literal session window is therefore the default;
        // it is identical to the 4H reading whenever the grid aligns with the
        // session start (the MNQ crypto-path case). See docs/COMPLIANCE_AUDIT.md.
        public bool PsyUse4HourGrid = false;

        // TradingView VWAP band multiplier. Enabling Band 1 in the built-in
        // indicator defaults to 1.0 standard deviation.
        public double VwapBandMultiplier = 1.0;

        // ---- V7: optional intraday session filter -------------------------------
        // OFF by default, so MNQ and ES (both CME, 18:00 ET exchange day) aggregate
        // exactly as before - this is a strict no-op for every pre-V7 caller.
        // It exists for a cash/ETF confirmation market with no 18:00 ET exchange day: the
        // user specified its key levels come from the RTH cash session only
        // (09:30-16:00 ET). Bars whose OPEN falls outside the window are ignored
        // entirely for day/week aggregation.
        public bool SessionFilterEnabled = false;
        public int SessionFilterStartMinutesEt = 570;   // 09:30 ET
        public int SessionFilterEndMinutesEt = 960;     // 16:00 ET (exclusive)

        // ---- port of Traders Reality calcDst(): Sydney DST flag ----
        // Pine: previousSunday = dayofmonth - dayofweek + 1  (dayofweek 1=Sun..7=Sat)
        public static bool CalcSydneyDst(DateTime date)
        {
            int month = date.Month;
            int previousSunday = date.Day - ((int)date.DayOfWeek + 1) + 1;
            if (month < 3 || month > 11) return true;
            if (month > 4 && month < 10) return false;
            if (month == 3) return true;
            if (month == 4) return previousSunday <= 0;
            if (month == 10) return previousSunday >= 0;
            return true; // month == 11
        }

        // ---- port of the calcPsyLevels session windows ----
        // Pine session-string day numbers are 1=Sunday .. 7=Saturday, and for a
        // session spanning midnight the day list names the day the session STARTS.
        //   forex : psySession := time('240', '0000-0800:2', "GMT")
        //           -> day 2 = MONDAY 00:00 -> 08:00 GMT
        //           (tooltip: "Forex calculations start with the Tokyo session on
        //            Monday morning")
        //   crypto: psySession := time('240', '2200-0600:1', "GMT+1"/"GMT")
        //           -> day 1 = SUNDAY 22:00 -> Monday 06:00 in that GMT offset
        //           (GMT+1 while Sydney is in DST, else GMT)
        // NOTE: the library's timestampPreviousDayOfWeek('Saturday', 22, ...) call
        // feeds psySessionStartTime only, which TR_MAIN uses purely to decide where
        // to START DRAWING the psy line (main indicator lines 654-657). It does not
        // participate in the psyHi/psyLo values.
        private bool IsInPsySession(DateTime utc, DateTime etForDst)
        {
            if (PsyType == PsyLevelType.Forex)
                return utc.DayOfWeek == DayOfWeek.Monday && utc.TimeOfDay.TotalHours < 8.0;

            // crypto path: shift into the session's offset timezone, then test
            // Sunday 22:00 -> Monday 06:00
            DateTime t = CalcSydneyDst(etForDst) ? utc.AddHours(1) : utc;
            if (t.DayOfWeek == DayOfWeek.Sunday && t.TimeOfDay.TotalHours >= 22.0) return true;
            if (t.DayOfWeek == DayOfWeek.Monday && t.TimeOfDay.TotalHours < 6.0) return true;
            return false;
        }

        // Feed one COMPLETED 1m bar. Returns true when a new exchange day started.
        // utcOpen is the bar's open time in UTC (needed by the psy-session port,
        // whose sessions are defined in GMT in the supplied source).
        public bool OnOneMinuteBar(DateTime etOpen, DateTime etClose, DateTime utcOpen, double o, double h, double l, double c, double volume)
        {
            bool newDay = false;

            // ---- V7 session filter (no-op unless explicitly enabled) ----
            if (SessionFilterEnabled)
            {
                int minOfDay = etOpen.Hour * 60 + etOpen.Minute;
                if (minOfDay < SessionFilterStartMinutesEt || minOfDay >= SessionFilterEndMinutesEt)
                    return false;
            }

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
                // Session VWAP re-anchors with the new exchange day
                vwapSumSrcVol = 0; vwapSumVol = 0; vwapSumSrcSrcVol = 0;
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
            }
            else
            {
                if (curWeek == null) { curWeek = new Agg(); curWeek.O = o; curWeek.H = h; curWeek.L = l; curWeek.Valid = true; }
                if (h > curWeek.H) curWeek.H = h;
                if (l < curWeek.L) curWeek.L = l;
                curWeek.C = c;
            }

            // ---- Session VWAP accumulation (TradingView built-in VWAP) ----
            if (volume > 0)
            {
                double vwapSrc = (h + l + c) / 3.0;   // hlc3 = TradingView's default source
                vwapSumSrcVol += vwapSrc * volume;
                vwapSumVol += volume;
                vwapSumSrcSrcVol += volume * vwapSrc * vwapSrc;
            }

            // ---- Traders Reality calcPsyLevels port (V5 Fix 4D) ----
            // "When entering a new psy session, initialize hi/lo. After
            //  initialization, calculate psy hi/lo [max/min]. When not in the
            //  psy session, use the last value of psyHi and psyLo."
            //
            // The source tests membership with time('240', session, gmt): the
            // session is evaluated on the instrument's 4-HOUR bar grid, not on the
            // chart bar itself ("because the session is 8 hours and we are looking
            // at a 4 hour resolution we only need ... 2 bars"). TradingView anchors
            // intraday aggregation to the exchange day start, so the grid is
            // reproduced here from DayStartMinutesEt. With PsyUse4HourGrid = false
            // the literal session window is used instead (identical whenever the
            // grid aligns to the session start, which is the MNQ summer case).
            DateTime sessionProbeUtc = utcOpen;
            if (PsyUse4HourGrid)
            {
                DateTime dayStartEt = dayKey.AddMinutes(DayStartMinutesEt);
                double minsSinceDayStart = (etOpen - dayStartEt).TotalMinutes;
                if (minsSinceDayStart < 0) minsSinceDayStart = 0;
                int gridIdx = (int)Math.Floor(minsSinceDayStart / 240.0);
                DateTime gridOpenEt = dayStartEt.AddMinutes(gridIdx * 240.0);
                sessionProbeUtc = gridOpenEt.Add(utcOpen - etOpen); // same UTC offset as this bar
            }
            bool inPsy = IsInPsySession(sessionProbeUtc, etOpen);
            if (inPsy)
            {
                if (!wasInPsySession) { psyHigh = h; psyLow = l; }
                else
                {
                    if (h > psyHigh || double.IsNaN(psyHigh)) psyHigh = h;
                    if (l < psyLow || double.IsNaN(psyLow)) psyLow = l;
                }
            }
            // outside the session psyHigh/psyLow simply hold their last values
            wasInPsySession = inPsy;

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

        public double Vwap
        {
            get { return vwapSumVol > 0 ? vwapSumSrcVol / vwapSumVol : double.NaN; }
        }
        private double VwapStdev
        {
            get
            {
                if (vwapSumVol <= 0) return double.NaN;
                double v = vwapSumSrcVol / vwapSumVol;
                double variance = vwapSumSrcSrcVol / vwapSumVol - v * v;
                if (variance < 0) variance = 0;      // TradingView floors negatives
                return Math.Sqrt(variance);
            }
        }
        public double VwapBandHigh
        {
            get { double v = Vwap, sd = VwapStdev; return (double.IsNaN(v) || double.IsNaN(sd)) ? double.NaN : v + VwapBandMultiplier * sd; }
        }
        public double VwapBandLow
        {
            get { double v = Vwap, sd = VwapStdev; return (double.IsNaN(v) || double.IsNaN(sd)) ? double.NaN : v - VwapBandMultiplier * sd; }
        }

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
                case TpLevelId.VWAP: return Vwap;
                case TpLevelId.VWAP_BAND_HIGH: return VwapBandHigh;
                case TpLevelId.VWAP_BAND_LOW: return VwapBandLow;
            }
            return double.NaN;
        }

        // ---- Spec section C: NEXT-KEY-LEVEL SELECTION ALGORITHM ------------------
        // LONG : all valid levels STRICTLY ABOVE referencePrice, sorted low->high.
        // SHORT: all valid levels STRICTLY BELOW referencePrice, sorted high->low.
        //
        // V5 correction Fix 8: every level price (and the reference) is first
        // NORMALIZED to MNQ tick size via the supplied delegate; levels are then
        // merged into one target-price event ONLY when the normalized prices are
        // exactly equal. Distinct normalized prices are never merged by a broad
        // tolerance. NaN levels and levels equal to the reference are ignored.
        public List<TpTarget> GetSortedTargets(TradeDirection direction, double referencePrice,
                                               Func<TpLevelId, bool> levelEnabled, Func<double, double> normalizeToTick)
        {
            List<TpTarget> result = new List<TpTarget>();
            Array all = Enum.GetValues(typeof(TpLevelId));
            List<KeyValuePair<TpLevelId, double>> candidates = new List<KeyValuePair<TpLevelId, double>>();

            double refNorm = normalizeToTick != null ? normalizeToTick(referencePrice) : referencePrice;

            foreach (TpLevelId id in all)
            {
                if (levelEnabled != null && !levelEnabled(id)) continue;
                double p = GetTpLevelPrice(id);
                if (double.IsNaN(p)) continue;
                if (normalizeToTick != null) p = normalizeToTick(p);

                if (direction == TradeDirection.Long)
                {
                    if (p > refNorm)
                        candidates.Add(new KeyValuePair<TpLevelId, double>(id, p));
                }
                else
                {
                    if (p < refNorm)
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
                if (result.Count > 0 && result[result.Count - 1].Price == kv.Value)
                {
                    result[result.Count - 1].Names.Add(kv.Key); // exact same normalized price = one event
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
    // Spec: "GLOBAL: POSITION SIZING" - MNQ ONLY, $2 per index point.
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
    // V6 U9 - STRATEGY HANDOFF
    //
    // FAKE_BREAKOUT and VECTOR_BREAK_RETEST must never hold MNQ positions at the
    // same time. When one strategy is open and the OTHER produces a fully valid
    // entry, the sequence is strictly:
    //     1. flatten the currently open strategy completely
    //     2. wait for the flatten fill / account-flat confirmation
    //     3. only then submit the newly signalled strategy's entry
    //
    // The replacement order must NEVER be submitted before the flat confirmation
    // (NinjaTrader would net the two positions and contaminate both engines'
    // state). This coordinator owns that ordering and lives in shared code so the
    // NinjaTrader host and the deterministic test host execute the SAME logic.
    //
    // Note this is pure execution sequencing: no setup state, grade, stop, size or
    // target is shared between the engines - the replacement strategy uses only
    // its own values (V6 U9).
    // ------------------------------------------------------------------
    public class HandoffCoordinator
    {
        private class PendingEntry
        {
            public StrategyId Id;
            public TradeDirection Dir;
            public int Qty;
            public string Signal;
        }

        private readonly Func<StrategyId, bool> hasPosition;                    // does this engine hold a position?
        private readonly Action<StrategyId> flattenStrategy;                    // flatten that engine's position
        private readonly Action<StrategyId, TradeDirection, int, string> submit; // actually place the entry order
        private readonly Action<StrategyId, string> diag;

        private PendingEntry pending;
        private StrategyId awaitingFlatOf;

        public HandoffCoordinator(Func<StrategyId, bool> hasPosition,
                                  Action<StrategyId> flattenStrategy,
                                  Action<StrategyId, TradeDirection, int, string> submit,
                                  Action<StrategyId, string> diag)
        {
            this.hasPosition = hasPosition;
            this.flattenStrategy = flattenStrategy;
            this.submit = submit;
            this.diag = diag;
        }

        /// True while a flatten has been sent and the replacement entry is parked.
        public bool HandoffInProgress { get { return pending != null; } }

        public static StrategyId Other(StrategyId id)
        {
            return id == StrategyId.FAKE_BREAKOUT ? StrategyId.VECTOR_BREAK_RETEST : StrategyId.FAKE_BREAKOUT;
        }

        /// Entry request from an engine. Submits immediately when the account is
        /// free, otherwise starts the handoff and defers the order.
        public void RequestEntry(StrategyId id, TradeDirection dir, int qty, string signal)
        {
            StrategyId other = Other(id);
            bool otherOpen = hasPosition != null && hasPosition(other);

            if (!otherOpen && !HandoffInProgress)
            {
                submit(id, dir, qty, signal);
                return;
            }

            // V6 U9: park the entry, flatten the other strategy, wait for flat.
            pending = new PendingEntry { Id = id, Dir = dir, Qty = qty, Signal = signal };
            awaitingFlatOf = other;
            if (diag != null)
                diag(id, string.Format(CultureInfo.InvariantCulture,
                    "HANDOFF: {0} holds an open position - flattening it first; {1} entry ({2} x{3}) is PARKED until flat is confirmed (V6 U9)",
                    other, signal, dir, qty));
            if (otherOpen)
                flattenStrategy(other);
        }

        /// Called by the host once the ACCOUNT is confirmed flat (position update /
        /// exit fill). Releases the parked replacement entry - and only then.
        public void NotifyFlat()
        {
            if (pending == null) return;
            PendingEntry p = pending;
            pending = null;
            if (diag != null)
                diag(p.Id, string.Format(CultureInfo.InvariantCulture,
                    "HANDOFF: {0} flat confirmed - submitting parked {1} entry ({2} x{3}) (V6 U9)",
                    awaitingFlatOf, p.Signal, p.Dir, p.Qty));
            submit(p.Id, p.Dir, p.Qty, p.Signal);
        }
    }

    // ------------------------------------------------------------------
    // Host services the engines need from the NinjaTrader strategy.
    // Engines only call OUT through this interface; they never touch each
    // other or the other engine's orders (spec hard separation rule).
    // ------------------------------------------------------------------
    // ======================================================================
    // V7 - CROSS-MARKET CONFIRMATION (FAKE BREAKOUT ONLY)
    //
    // ES and YM are CONFIRMATION markets. They never produce a setup, never
    // size a trade and never receive an order - the traded instrument is MNQ
    // and nothing here can submit anything. Their only job is to answer one
    // question at the moment an already-valid MNQ Fake Breakout entry fires:
    //
    //   "on the SAME completed bar timestamp, on the SAME timeframe, at YOUR
    //    OWN equivalent named key level, are you showing the same directional
    //    fake-break + reclaim + EMA(9) confirmation?"
    //
    // The answer sets the grade and risk. It never creates or blocks a trade.
    //
    // Timeframe isolation is STRUCTURAL, not conditional: one detector instance
    // exists per (market, timeframe), so a 3m confirmation physically cannot be
    // read when grading a 1m signal. There is no code path that mixes them.
    //
    // VECTOR_BREAK_RETEST never touches any of this.
    // ======================================================================
    public enum ConfirmMarket { ES, YM }

    /// Which stage of the research programme a run belongs to. This is not a label -
    /// it decides which data series are loaded, because loading sub-minute and tick
    /// history is what makes a multi-year capture expensive, and neither belongs in
    /// signal discovery.
    ///
    ///   PHASE1_DISCOVERY  60m / 15m / 3m / 1m. Broad multi-year parent-behaviour search.
    ///   PHASE2_EXECUTION  adds sub-minute, around frozen Phase-1 events only.
    ///   PHASE3_TICK       adds 1-tick, for fill sequencing and slippage realism only.
    public enum ResearchPhase { PHASE1_DISCOVERY, PHASE2_EXECUTION, PHASE3_TICK }

    public struct CrossMarketConfirm
    {
        public bool Confirmed;
        /// TRUE when this market could not be evaluated at all (no bars, or its own
        /// equivalent level was not computable). Confirmed==false with Unavailable==true
        /// means UNKNOWN - it must never be graded as "this market did not confirm".
        public bool Unavailable;
        public DateTime BarEtClose;      // bar on which reclaim+EMA completed
        public KeyLevelId LevelId;       // that market's OWN equivalent level
        public double LevelPrice;        // that market's OWN price for it
        public VectorType BreakVector;
        public VectorType ReclaimVector;
        public double Close;
        public double Ema9;
        public string Reason;            // why it confirmed, or why it did not
    }

    // ----------------------------------------------------------------------
    // The complete FB grade table (user specification, 2026-08-14).
    //
    // The grade is decided by HOW MANY confirmation markets agree with MNQ,
    // not by WHICH one. ES and market 2 are interchangeable votes.
    //
    //   markets agreeing -> grade  risk
    //   both (ES + M2)      A+     30%
    //   exactly one         A-     10%
    //   neither             B+      5%
    //
    // Every case is enumerated here and nowhere else, so nothing can fall
    // through to an invented default. There is no fourth grade: the old
    // "B / neither" tier is now B+ by the user's definition.
    // ----------------------------------------------------------------------
    public class FbCrossMarketGradeTable
    {
        public double RiskPctAPlus = 30.0;   // ES + market 2 both confirm
        public double RiskPctAMinus = 10.0;  // exactly one confirms (either one)
        public double RiskPctBPlus = 5.0;    // MNQ alone, neither confirms

        public void Resolve(bool esConfirm, bool market2Confirm, out string grade, out double riskPct)
        {
            int agreeing = (esConfirm ? 1 : 0) + (market2Confirm ? 1 : 0);
            if (agreeing == 2)      { grade = "A+"; riskPct = RiskPctAPlus; }
            else if (agreeing == 1) { grade = "A-"; riskPct = RiskPctAMinus; }
            else                    { grade = "B+"; riskPct = RiskPctBPlus; }
        }
    }

    // ----------------------------------------------------------------------
    // One (market, timeframe) fake-break detector.
    //
    // The break/reclaim/vector/EMA rules are a deliberate mirror of the MNQ
    // Fake Breakout lower-timeframe logic in FakeBreakoutEngine.ProcessLtf.
    // What is NOT mirrored, per the specification:
    //   - no 15m parent setup is required (or consulted) for ES/YM
    //   - no validity-candle counting
    //   - no entry-time window (this produces no entries)
    // What IS mirrored:
    //   - break candle vector rules       (long: RED/REGULAR, short: GREEN/BLUE/REGULAR)
    //   - reclaim candle vector rules     (incl. the break-vector-dependent short paths)
    //   - structure extreme + wick extension
    //   - same-timeframe EMA(9) confirmation, with the post-reclaim EMA wait
    //   - the >= 09:30 ET session-start gate on the BREAK candle
    // Plus one bound the MNQ engine gets from its parent and this does not:
    //   - the reclaim must arrive within MaxBarsBreakToReclaim bars of the break.
    // ----------------------------------------------------------------------
    public class CrossMarketConfirmDetector
    {
        private static readonly KeyLevelId[] Eligible = new KeyLevelId[]
        {
            KeyLevelId.YDAY_HIGH, KeyLevelId.YDAY_LOW, KeyLevelId.LWEEK_HIGH, KeyLevelId.LWEEK_LOW
        };

        private class Str
        {
            public bool Active;
            public bool WaitingEma;
            public VectorType BreakVector;
            public VectorType ReclaimVector;
            public double StructExtreme = double.NaN;
            public int BarsSinceBreak;
            public void Reset()
            {
                Active = false; WaitingEma = false; BarsSinceBreak = 0;
                StructExtreme = double.NaN;
            }
        }

        public readonly ConfirmMarket Market;
        public readonly int TfMinutes;
        /// Display name used in EVERY log line and reason string. Defaults to the
        /// slot name but the host overwrites it with the actually-configured symbol,
        /// so a detector always reports the contract actually configured.
        public string Label;

        // Bound on break -> reclaim. User-specified 2026-08-14: 4 bars.
        public int MaxBarsBreakToReclaim = 4;
        // User specification 2026-08-14: "for es and ym the emas dont matter".
        // Confirmation is break + reclaim only. The MNQ engine's own EMA(9) rule is
        // untouched - this flag applies solely to the confirmation markets. Left
        // configurable so the stricter behavior can be restored without a code change.
        public bool RequireEmaConfirmation = false;
        // Mirrors the MNQ rule "premarket LTF patterns are never banked".
        public int SessionStartMinutesEt = 570;   // 09:30 ET

        // ---- DIAGNOSTICS (V7.1) -------------------------------------------
        // A "no confirmation" answer has two completely different meanings:
        //   (a) evaluated, and the market genuinely did not do it, or
        //   (b) never evaluated, because this market had no bars / no levels.
        // Reporting (b) as (a) is exactly how the first cross-market backtest
        // silently graded 59 trades off inputs that were never populated.
        // These counters keep the two apart.
        public Action<string> Diag;         // optional sink; null = no logging
        public bool VerboseEvents;          // per-event logging (loud)
        public long BarsSeen;               // total bars this detector processed
        public long TotalConfirms;
        public int DayBarsNoLevels;         // bars where NO eligible level existed
        public int DayBreaks;               // fake-break structures started
        public int DayReclaimRejectedVector;// reclaim arrived but wrong vector
        public int DayWindowExpired;        // no reclaim inside MaxBarsBreakToReclaim
        public int DayAwaitingEma;          // valid reclaim, waiting on same-TF EMA9
        public int DayConfirms;

        /// True once this detector's market has produced at least one usable
        /// eligible level. False means every answer it has ever given is "unknown",
        /// not "no".
        public bool HasEverHadLevels;

        public bool AnyLevelAvailableNow
        {
            get
            {
                for (int i = 0; i < Eligible.Length; i++)
                    if (!double.IsNaN(levels.GetTriggerLevelPrice(Eligible[i]))) return true;
                return false;
            }
        }

        /// One-line daily summary. Call on the market's day roll, then counters reset.
        public string DailyTally()
        {
            string s = string.Format(CultureInfo.InvariantCulture,
                "{0} {1}m: bars={2} noLevelBars={3} breaks={4} reclaimRejected={5} windowExpired={6} awaitingEma={7} CONFIRMS={8}",
                Label, TfMinutes, BarsSeen, DayBarsNoLevels, DayBreaks,
                DayReclaimRejectedVector, DayWindowExpired, DayAwaitingEma, DayConfirms);
            DayBarsNoLevels = 0; DayBreaks = 0; DayReclaimRejectedVector = 0;
            DayWindowExpired = 0; DayAwaitingEma = 0; DayConfirms = 0;
            return s;
        }

        private void Ev(string msg)
        {
            if (VerboseEvents && Diag != null) Diag(msg);
        }

        private readonly KeyLevelEngine levels;   // this market's OWN levels
        private readonly Str[,] st = new Str[4, 2];              // [level, 0=long 1=short]
        private readonly CrossMarketConfirm[,] last = new CrossMarketConfirm[4, 2];

        public CrossMarketConfirmDetector(ConfirmMarket market, int tfMinutes, KeyLevelEngine ownLevels)
        {
            Market = market;
            TfMinutes = tfMinutes;
            Label = market.ToString();
            levels = ownLevels;
            for (int i = 0; i < 4; i++)
                for (int d = 0; d < 2; d++)
                    st[i, d] = new Str();
        }

        public void OnNewDay()
        {
            for (int i = 0; i < 4; i++)
                for (int d = 0; d < 2; d++)
                {
                    st[i, d].Reset();
                    last[i, d] = default(CrossMarketConfirm);
                }
        }

        private static int IndexOf(KeyLevelId id)
        {
            for (int i = 0; i < Eligible.Length; i++)
                if (Eligible[i] == id) return i;
            return -1;
        }

        // Feed one COMPLETED bar of this market on this timeframe.
        public void OnBar(BarSnap bar)
        {
            if (bar.PeriodMinutes != TfMinutes) return;   // hard timeframe isolation
            BarsSeen++;
            int usable = 0;
            for (int i = 0; i < Eligible.Length; i++)
            {
                double lvl = levels.GetTriggerLevelPrice(Eligible[i]);
                if (double.IsNaN(lvl)) continue;   // level not computable -> UNKNOWN, not "no"
                usable++;
                Process(i, true, lvl, bar);    // bullish confirmation candidate
                Process(i, false, lvl, bar);   // bearish confirmation candidate
            }
            if (usable == 0) DayBarsNoLevels++;
            else HasEverHadLevels = true;
        }

        private void Process(int li, bool isLong, double lvl, BarSnap bar)
        {
            int di = isLong ? 0 : 1;
            Str s = st[li, di];

            if (!s.Active)
            {
                // ---- break candle (mirror of FB S9/S10 break rules) ----
                bool breakClose = isLong ? bar.Close < lvl : bar.Close > lvl;
                if (!breakClose) return;
                bool breakVecOk = isLong
                    ? (bar.Vector == VectorType.RED_VECTOR || VectorClassifier.IsRegular(bar.Vector))
                    : (bar.Vector == VectorType.GREEN_VECTOR || bar.Vector == VectorType.BLUE_VECTOR
                       || VectorClassifier.IsRegular(bar.Vector));
                if (!breakVecOk) return;

                int minOfDay = bar.EtOpen.Hour * 60 + bar.EtOpen.Minute;
                if (minOfDay < SessionStartMinutesEt) return;   // premarket never banked

                s.Active = true;
                s.WaitingEma = false;
                s.BreakVector = bar.Vector;
                s.StructExtreme = isLong ? bar.Low : bar.High;
                s.BarsSinceBreak = 0;
                DayBreaks++;
                Ev(string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m {2}: fake-break started at {3} ({4:0.00}) - {5} close {6:0.00}, awaiting reclaim within {7} bars [{8:HH:mm}]",
                    Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", Eligible[li], lvl,
                    bar.Vector, bar.Close, MaxBarsBreakToReclaim, bar.EtClose));
                return;
            }

            if (!s.WaitingEma)
            {
                bool reclaimClose = isLong ? bar.Close > lvl : bar.Close < lvl;
                if (!reclaimClose)
                {
                    // still beyond the level - extend the structure, but the reclaim
                    // window is finite (this is what the 15m parent bounds on MNQ).
                    if (isLong) { if (bar.Low < s.StructExtreme) s.StructExtreme = bar.Low; }
                    else { if (bar.High > s.StructExtreme) s.StructExtreme = bar.High; }
                    if (++s.BarsSinceBreak > MaxBarsBreakToReclaim)
                    {
                        s.Reset(); DayWindowExpired++;
                        Ev(string.Format(CultureInfo.InvariantCulture,
                            "{0} {1}m {2}: NO CONFIRM - never reclaimed {3} ({4:0.00}) within {5} bars [{6:HH:mm}]",
                            Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", Eligible[li], lvl,
                            MaxBarsBreakToReclaim, bar.EtClose));
                    }
                    return;
                }
                if (++s.BarsSinceBreak > MaxBarsBreakToReclaim)
                {
                    s.Reset(); DayWindowExpired++;
                    Ev(string.Format(CultureInfo.InvariantCulture,
                        "{0} {1}m {2}: NO CONFIRM - reclaimed {3} ({4:0.00}) but {5} bars after the break (limit {6}) [{7:HH:mm}]",
                        Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", Eligible[li], lvl,
                        s.BarsSinceBreak, MaxBarsBreakToReclaim, bar.EtClose));
                    return;
                }

                // ---- reclaim candle vector rules (mirror of FB S9/S10) ----
                bool reclaimVecOk;
                if (isLong)
                    reclaimVecOk = bar.Vector == VectorType.GREEN_VECTOR || bar.Vector == VectorType.BLUE_VECTOR;
                else if (s.BreakVector == VectorType.GREEN_VECTOR)
                    reclaimVecOk = true;
                else if (s.BreakVector == VectorType.BLUE_VECTOR)
                    reclaimVecOk = VectorClassifier.IsRegular(bar.Vector) || bar.Vector == VectorType.RED_VECTOR;
                else
                    reclaimVecOk = bar.Vector == VectorType.RED_VECTOR || bar.Vector == VectorType.VIOLET_VECTOR;

                if (!reclaimVecOk)
                {
                    Ev(string.Format(CultureInfo.InvariantCulture,
                        "{0} {1}m {2}: NO CONFIRM - reclaimed {3} ({4:0.00}) but reclaim vector {5} invalid after break vector {6} [{7:HH:mm}]",
                        Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", Eligible[li], lvl,
                        bar.Vector, s.BreakVector, bar.EtClose));
                    s.Reset(); DayReclaimRejectedVector++; return;
                }

                if (isLong) { if (bar.Low < s.StructExtreme) s.StructExtreme = bar.Low; }
                else { if (bar.High > s.StructExtreme) s.StructExtreme = bar.High; }

                s.ReclaimVector = bar.Vector;
                bool emaOk = isLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
                if (!RequireEmaConfirmation || emaOk) Record(li, di, isLong, lvl, s, bar);
                else
                {
                    s.WaitingEma = true; DayAwaitingEma++;
                    Ev(string.Format(CultureInfo.InvariantCulture,
                        "{0} {1}m {2}: valid reclaim of {3} ({4:0.00}) but close {5:0.00} not yet through EMA9 {6:0.00} - waiting [{7:HH:mm}]",
                        Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", Eligible[li], lvl,
                        bar.Close, bar.Ema9, bar.EtClose));
                }
                return;
            }

            // ---- waiting for the same-timeframe EMA(9) after a valid reclaim ----
            bool structBreach = isLong ? bar.Close < s.StructExtreme : bar.Close > s.StructExtreme;
            if (structBreach) { s.Reset(); return; }
            if (isLong) { if (bar.Low < s.StructExtreme) s.StructExtreme = bar.Low; }
            else { if (bar.High > s.StructExtreme) s.StructExtreme = bar.High; }

            bool ema2 = isLong ? bar.Close > bar.Ema9 : bar.Close < bar.Ema9;
            if (ema2) Record(li, di, isLong, lvl, s, bar);
        }

        private void Record(int li, int di, bool isLong, double lvl, Str s, BarSnap bar)
        {
            CrossMarketConfirm c = new CrossMarketConfirm();
            c.Confirmed = true;
            c.BarEtClose = bar.EtClose;
            c.LevelId = Eligible[li];
            c.LevelPrice = lvl;
            c.BreakVector = s.BreakVector;
            c.ReclaimVector = s.ReclaimVector;
            c.Close = bar.Close;
            c.Ema9 = bar.Ema9;
            c.Reason = RequireEmaConfirmation
                ? string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m {2} fake-break {3} -> reclaim {4} through {5:0.00}, close {6:0.00} {7} ema9 {8:0.00}",
                    Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", s.BreakVector, s.ReclaimVector,
                    lvl, bar.Close, isLong ? ">" : "<", bar.Ema9)
                : string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m {2} fake-break {3} -> reclaim {4} through {5:0.00}, close {6:0.00} (EMA not required)",
                    Label, TfMinutes, isLong ? "BULLISH" : "BEARISH", s.BreakVector, s.ReclaimVector,
                    lvl, bar.Close);
            last[li, di] = c;
            DayConfirms++; TotalConfirms++;
            Ev(string.Format(CultureInfo.InvariantCulture,
                "{0} {1}m: *** CONFIRMED *** {2} [{3:HH:mm}]",
                Label, TfMinutes, c.Reason, bar.EtClose));
            s.Reset();
        }

        // Read-only query made at the MNQ entry decision. toleranceBars = 0 means
        // the confirmation must sit on EXACTLY the same completed bar timestamp.
        public CrossMarketConfirm Query(bool isLong, KeyLevelId id, DateTime barEtClose, int toleranceBars)
        {
            CrossMarketConfirm miss = new CrossMarketConfirm();
            miss.LevelId = id;
            miss.LevelPrice = levels.GetTriggerLevelPrice(id);

            int li = IndexOf(id);
            if (li < 0)
            {
                miss.Reason = string.Format("{0} {1}m: {2} is not a Fake Breakout eligible level", Label, TfMinutes, id);
                return miss;
            }
            // UNKNOWN vs NO. If this market has no bars, or cannot compute its own
            // equivalent level, then nothing was ever evaluated and the honest answer
            // is "unknown". It must never be reported as "this market did not confirm".
            if (BarsSeen == 0)
            {
                miss.Unavailable = true;
                miss.Reason = string.Format("{0} {1}m: UNKNOWN - this series delivered ZERO bars (no data loaded)", Label, TfMinutes);
                return miss;
            }
            if (double.IsNaN(miss.LevelPrice))
            {
                miss.Unavailable = true;
                miss.Reason = string.Format(
                    "{0} {1}m: UNKNOWN - {2} could not be computed for {0} (level is NaN; needs >=2 sessions of {0} history)",
                    Label, TfMinutes, id);
                return miss;
            }

            int di = isLong ? 0 : 1;
            CrossMarketConfirm c = last[li, di];
            if (!c.Confirmed)
            {
                miss.Reason = string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m: no {2} fake-break confirmation recorded at {3} ({4:0.00}) - evaluated, did not occur",
                    Label, TfMinutes, isLong ? "bullish" : "bearish", id, miss.LevelPrice);
                return miss;
            }

            double diffMin = (barEtClose - c.BarEtClose).TotalMinutes;
            if (diffMin < 0)
            {
                // The stored confirmation is LATER than the MNQ decision bar. Using it
                // would be lookahead. Never allowed, at any tolerance.
                miss.Reason = string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m: confirmation at {2:HH:mm} is AFTER the MNQ decision bar {3:HH:mm} - rejected (no lookahead)",
                    Label, TfMinutes, c.BarEtClose, barEtClose);
                return miss;
            }
            if (diffMin > (double)toleranceBars * TfMinutes)
            {
                miss.Reason = string.Format(CultureInfo.InvariantCulture,
                    "{0} {1}m: confirmation at {2:HH:mm} is stale for MNQ decision bar {3:HH:mm} (tolerance {4} bar(s))",
                    Label, TfMinutes, c.BarEtClose, barEtClose, toleranceBars);
                return miss;
            }
            return c;
        }
    }

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

        // V7 cross-market confirmation (FAKE_BREAKOUT grading only, read-only).
        // False when the feature is switched off or the ES/YM series are not attached.
        bool CrossMarketEnabled { get; }
        CrossMarketConfirm QueryCrossMarket(ConfirmMarket market, bool isLong, KeyLevelId levelId,
                                            int tfMinutes, DateTime barEtClose);

        int  EnterPosition(StrategyId id, TradeDirection dir, int qty, string signalName);
        void SubmitOrUpdateStop(StrategyId id, TradeDirection dir, int qty, double stopPrice,
                                string stopName, string fromEntrySignal);
        void ExitMarket(StrategyId id, TradeDirection dir, int qty, string exitName, string fromEntrySignal);

        void Diag(StrategyId id, string msg);
        void LogTrade(TradeRecord rec);
        double RoundToTick(double price);
    }
}
