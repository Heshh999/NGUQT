// ============================================================================
// ScalpResearchEngine.cs
//
// RESEARCH MODULE - SUBMITS NO ORDERS, EVER.
//
// A general MNQ scalping research capture. It has NO dependency on candle
// classification of any kind: it does not know what a vector candle is and
// never asks. Its sampling frame is PRICE INTERACTING WITH STRUCTURE.
//
// WHY THE SAMPLING FRAME MATTERS
//   Logging every bar of several years at 5-second resolution is not a file
//   anyone can move. Logging only bars that pass some classifier makes the
//   classifier a hidden filter on every downstream result. This engine takes
//   the middle path: it emits a row whenever a bar INTERACTS with a tracked
//   level, plus a 1-in-N random sample of bars that interacted with nothing.
//   That control group is what makes "is this pattern better at a level than
//   away from one?" an answerable question rather than an assumption.
//
// ONE ROW PER (BAR, LEVEL) INTERACTION
//   A bar that sweeps yesterday's high while also breaking the opening-range
//   high produces TWO rows, one per level. Comparing levels against each
//   other is then a group-by rather than a reshape, and no level is silently
//   shadowed by another.
//
// STRICT NO-LOOKAHEAD CONTRACT
//   - Every feature is frozen when the event bar completes.
//   - Every label is filled in only from bars that arrive afterwards.
//   - A row is not written until its full forward horizon has elapsed.
//   - Session extremes exclude the describing bar, so "did this bar take the
//     session high" is a real question rather than a tautology.
//   - Higher-timeframe swings carry the timestamp at which they became
//     confirmed, and are refused before it.
//   - Candidate stops come from information available at event time. R is
//     never manufactured by choosing a stop after seeing the outcome.
//
// Independent of FakeBreakoutEngine and VectorBreakRetestEngine. Shares only
// read-only utilities.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqTwo
{
    // How a lower-timeframe candle interacted with a HIGHER-timeframe structural level.
    // This is the "1m vector takes out a known 3m high" question, made explicit.
    public enum HtfSweepEvent
    {
        NONE,                  // no level known, or the candle never came near it
        APPROACHED,            // came within the approach band but never traded through
        TOUCHED,               // touched the level exactly, no penetration
        SWEEP_CLOSE_BACK,      // traded THROUGH the level and closed back on the original side
        BREAK_CLOSE_THROUGH    // traded through and closed beyond it
    }

    /// A swing point together with the instant it became OBJECTIVELY KNOWN.
    /// A pivot is not knowable when it forms - only after enough bars have closed
    /// to its right to confirm it. Consuming it any earlier is lookahead, so
    /// KnownAtEt is carried with the price and enforced at query time.
    public struct HtfSwing
    {
        public double Price;
        public DateTime FormedAtEt;    // close time of the pivot bar itself
        public DateTime KnownAtEt;     // close time of the last confirming bar
        public bool Valid;
    }

    /// Intraday session context: the reference points most discretionary scalping
    /// frameworks are built on. Opening range, session extremes so far, how compressed
    /// recent range is, and how deep the current pullback is.
    ///
    /// NO-LOOKAHEAD CONTRACT
    ///   - Session extremes are the extremes of bars that closed BEFORE the bar being
    ///     described, so "did this candle break the session high" is a real question
    ///     rather than a tautology.
    ///   - The opening range is reported as incomplete, and its levels withheld, until
    ///     the opening-range window has actually finished.
    ///   - Everything resets on the RTH open, not the exchange day, because that is the
    ///     session these reference points belong to.
    ///
    /// Read-only. Submits no orders.
    public class SessionContext
    {
        public int RthStartMinutesEt = 570;      // 09:30
        public int RthEndMinutesEt = 960;        // 16:00
        public int OpeningRangeMinutes = 15;
        public int CompressionLookback = 10;

        private DateTime curDay = DateTime.MinValue;
        private readonly List<double> recentHigh = new List<double>();
        private readonly List<double> recentLow = new List<double>();

        public double OrHigh = double.NaN, OrLow = double.NaN;
        public bool OrComplete;
        /// Extremes of RTH bars that have ALREADY CLOSED - excludes the bar being described.
        public double SessHigh = double.NaN, SessLow = double.NaN;
        public bool InRth;

        private static int MinOfDay(DateTime et) { return et.Hour * 60 + et.Minute; }

        /// Feed one COMPLETED bar, in order, AFTER it has been used to describe itself.
        public void OnBarClosed(ResearchBar b)
        {
            DateTime day = b.EtClose.Date;
            if (day != curDay)
            {
                curDay = day;
                OrHigh = double.NaN; OrLow = double.NaN; OrComplete = false;
                SessHigh = double.NaN; SessLow = double.NaN;
                recentHigh.Clear(); recentLow.Clear();
            }
            int m = MinOfDay(b.EtClose);
            if (m <= RthStartMinutesEt || m > RthEndMinutesEt) return;   // RTH only

            // opening range accumulates until its window closes
            if (m <= RthStartMinutesEt + OpeningRangeMinutes)
            {
                if (double.IsNaN(OrHigh) || b.High > OrHigh) OrHigh = b.High;
                if (double.IsNaN(OrLow) || b.Low < OrLow) OrLow = b.Low;
                if (m == RthStartMinutesEt + OpeningRangeMinutes) OrComplete = true;
            }
            else OrComplete = true;

            if (double.IsNaN(SessHigh) || b.High > SessHigh) SessHigh = b.High;
            if (double.IsNaN(SessLow) || b.Low < SessLow) SessLow = b.Low;

            recentHigh.Add(b.High); recentLow.Add(b.Low);
            if (recentHigh.Count > CompressionLookback) { recentHigh.RemoveAt(0); recentLow.RemoveAt(0); }
        }

        /// Called BEFORE OnBarClosed for the same bar, so it describes the state the bar
        /// arrived into rather than the state it created.
        public void Describe(ResearchBar b, double atr, out double posInRange,
                             out double compression, out double pullbackPct)
        {
            InRth = MinOfDay(b.EtClose) > RthStartMinutesEt && MinOfDay(b.EtClose) <= RthEndMinutesEt;
            posInRange = double.NaN; pullbackPct = double.NaN; compression = double.NaN;

            if (!double.IsNaN(SessHigh) && !double.IsNaN(SessLow) && SessHigh > SessLow)
            {
                double rng = SessHigh - SessLow;
                posInRange = 100.0 * (b.Close - SessLow) / rng;
                // how far price has retraced from whichever extreme it set most recently
                double fromHigh = 100.0 * (SessHigh - b.Close) / rng;
                double fromLow = 100.0 * (b.Close - SessLow) / rng;
                pullbackPct = fromHigh < fromLow ? fromHigh : fromLow;
            }
            if (recentHigh.Count >= CompressionLookback && atr > 0)
            {
                double hi = recentHigh[0], lo = recentLow[0];
                for (int i = 1; i < recentHigh.Count; i++)
                {
                    if (recentHigh[i] > hi) hi = recentHigh[i];
                    if (recentLow[i] < lo) lo = recentLow[i];
                }
                compression = (hi - lo) / atr;   // low = coiled, high = expanding
            }
        }
    }

    /// Tracks confirmed swing highs and lows on ONE higher timeframe.
    ///
    /// NO-LOOKAHEAD CONTRACT
    ///   - A pivot at bar i is published only after ConfirmBars bars to its RIGHT
    ///     have completed. KnownAtEt is the close time of the last of those bars.
    ///   - Every query takes the consumer's decision time and refuses to return a
    ///     swing whose KnownAtEt is later than it.
    ///   - Only COMPLETED higher-timeframe bars are ever fed in.
    ///
    /// Submits no orders and holds no strategy state.
    public class HigherTfStructure
    {
        public readonly string Label;          // "3m", "15m"
        public int ConfirmBars = 2;            // bars to the right required to confirm a pivot
        public int PivotLeftBars = 2;          // bars to the left the pivot must exceed

        private readonly List<ResearchBar> bars = new List<ResearchBar>();
        private readonly List<HtfSwing> swingHighs = new List<HtfSwing>();
        private readonly List<HtfSwing> swingLows = new List<HtfSwing>();

        // Last fully COMPLETED bar on this timeframe - knowable with no confirmation lag.
        public double LastBarHigh = double.NaN;
        public double LastBarLow = double.NaN;
        public DateTime LastBarCloseEt = DateTime.MinValue;

        public HigherTfStructure(string label) { Label = label; }

        public int SwingHighCount { get { return swingHighs.Count; } }
        public int SwingLowCount { get { return swingLows.Count; } }

        /// Feed one COMPLETED higher-timeframe bar, in order.
        public void OnBar(ResearchBar b)
        {
            bars.Add(b);
            if (bars.Count > 400) bars.RemoveAt(0);
            LastBarHigh = b.High; LastBarLow = b.Low; LastBarCloseEt = b.EtClose;

            // The candidate pivot sits ConfirmBars back from the bar just closed.
            int ci = bars.Count - 1 - ConfirmBars;
            if (ci < PivotLeftBars) return;
            ResearchBar c = bars[ci];

            bool isHigh = true, isLow = true;
            for (int i = ci - PivotLeftBars; i < ci; i++)
            {
                if (bars[i].High >= c.High) isHigh = false;
                if (bars[i].Low <= c.Low) isLow = false;
            }
            for (int i = ci + 1; i < bars.Count; i++)
            {
                if (bars[i].High >= c.High) isHigh = false;
                if (bars[i].Low <= c.Low) isLow = false;
            }

            // KnownAtEt is the close of the bar that completed the confirmation, which
            // is the bar just fed in - never the pivot bar's own time.
            DateTime known = b.EtClose;
            if (isHigh)
            {
                HtfSwing s = new HtfSwing();
                s.Price = c.High; s.FormedAtEt = c.EtClose; s.KnownAtEt = known; s.Valid = true;
                swingHighs.Add(s);
                if (swingHighs.Count > 100) swingHighs.RemoveAt(0);
            }
            if (isLow)
            {
                HtfSwing s = new HtfSwing();
                s.Price = c.Low; s.FormedAtEt = c.EtClose; s.KnownAtEt = known; s.Valid = true;
                swingLows.Add(s);
                if (swingLows.Count > 100) swingLows.RemoveAt(0);
            }
        }

        // ---- Query gate -------------------------------------------------------
        //
        // The cutoff passed in by every query below is the consuming candle's OPEN
        // time, NOT its close time. That is deliberate and it matters:
        //
        //   A 15m bar closing at 09:45 CONTAINS the 1m bar closing at 09:45. Asking
        //   "did the 1m candle sweep the 15m high?" against a 15m bar that includes
        //   that very candle is circular - the 1m high helped set the 15m high.
        //   Requiring the higher-timeframe bar to have closed at or before the 1m
        //   bar OPENED removes every overlapping bar, so the comparison is always
        //   against structure that was finished and on the chart beforehand.
        //
        // This also makes the result independent of the order NinjaTrader happens to
        // deliver equal-timestamp series in, rather than relying on AddDataSeries
        // ordering staying the way it is today.

        /// Most recent swing high already confirmed before cutoffEt. Invalid if none.
        public HtfSwing SwingHighKnownAt(DateTime cutoffEt) { return Latest(swingHighs, cutoffEt); }
        public HtfSwing SwingLowKnownAt(DateTime cutoffEt) { return Latest(swingLows, cutoffEt); }

        private static HtfSwing Latest(List<HtfSwing> src, DateTime cutoffEt)
        {
            for (int i = src.Count - 1; i >= 0; i--)
                if (src[i].KnownAtEt <= cutoffEt) return src[i];
            return new HtfSwing();   // Valid == false
        }

        /// High of the last higher-timeframe bar that had already closed by cutoffEt.
        public double LastBarHighKnownAt(DateTime cutoffEt)
        {
            return LastBarCloseEt <= cutoffEt && LastBarCloseEt != DateTime.MinValue
                ? LastBarHigh : double.NaN;
        }
        public double LastBarLowKnownAt(DateTime cutoffEt)
        {
            return LastBarCloseEt <= cutoffEt && LastBarCloseEt != DateTime.MinValue
                ? LastBarLow : double.NaN;
        }

        /// Classify how a candle interacted with a level ABOVE it (a high being swept).
        public static HtfSweepEvent ClassifyAgainstHigh(double high, double close, double level, double band)
        {
            if (double.IsNaN(level)) return HtfSweepEvent.NONE;
            if (high > level) return close > level ? HtfSweepEvent.BREAK_CLOSE_THROUGH : HtfSweepEvent.SWEEP_CLOSE_BACK;
            if (high == level) return HtfSweepEvent.TOUCHED;
            return (level - high) <= band ? HtfSweepEvent.APPROACHED : HtfSweepEvent.NONE;
        }

        /// Classify how a candle interacted with a level BELOW it (a low being swept).
        public static HtfSweepEvent ClassifyAgainstLow(double low, double close, double level, double band)
        {
            if (double.IsNaN(level)) return HtfSweepEvent.NONE;
            if (low < level) return close < level ? HtfSweepEvent.BREAK_CLOSE_THROUGH : HtfSweepEvent.SWEEP_CLOSE_BACK;
            if (low == level) return HtfSweepEvent.TOUCHED;
            return (low - level) <= band ? HtfSweepEvent.APPROACHED : HtfSweepEvent.NONE;
        }
    }

    public enum TimeBucket { PREMARKET, T0930_1000, T1000_1030, T1030_1100, T1100_1130, AFTER_1130 }

    /// Self-contained recursive EMA over completed closes.
    public class RollingEma
    {
        private readonly double k;
        private double value = double.NaN;
        private int count;
        public readonly int Period;
        public RollingEma(int period) { Period = period; k = 2.0 / (period + 1.0); }
        public double Value { get { return count >= Period ? value : double.NaN; } }
        public bool Ready { get { return count >= Period; } }
        public void Add(double close)
        {
            count++;
            value = double.IsNaN(value) ? close : value + k * (close - value);
        }
    }

    /// One 1-minute bar as the research engine sees it.
    public struct ResearchBar
    {
        public DateTime EtOpen, EtClose;
        public double Open, High, Low, Close, Volume;
    }


    /// Fine-grained session buckets, as the research brief specifies them.
    public enum ScalpTimeBucket
    {
        OVERNIGHT, T0730_0800, T0800_0830, T0830_0900, T0900_0929,
        T0930_0945, T0945_1000, T1000_1015, T1015_1030, T1030_1045, T1045_1100,
        T1100_1130, T1130_1300, T1300_1600, AFTER_1600
    }

    /// Contemporaneous day classification. Nothing here may look forward - a day is
    /// described by what has already happened in it, so the label a bar carries is the
    /// label a live system would have had at that instant.
    public enum TrendState { UP, DOWN, CHOP, UNKNOWN }
    public enum VolState { LOW, NORMAL, HIGH, UNKNOWN }
    public enum RangeState { COMPRESSED, NORMAL, EXPANDING, UNKNOWN }

    /// Where the bar sat relative to a level BEFORE it printed, so break/retest and
    /// reclaim sequences can be identified without peeking forward.
    public enum LevelSeqState
    {
        UNTESTED,             // level has not been interacted with yet today
        FIRST_TEST,           // this is the first interaction
        RETEST_AFTER_BREAK,   // price broke through earlier and has come back to it
        RECLAIM_AFTER_BREAK,  // price broke through earlier and has closed back inside
        REPEAT_TEST           // has been tested before, no break in between
    }

    /// Premarket structure, accumulated causally between the overnight open and 09:30.
    public class PremarketTracker
    {
        public int PremarketStartMinutesEt = 240;    // 04:00 ET
        public int RthStartMinutesEt = 570;          // 09:30 ET
        private DateTime curDay = DateTime.MinValue;
        private double firstClose = double.NaN;
        public double High = double.NaN, Low = double.NaN, LastClose = double.NaN;
        public bool Complete;

        public double RangePts { get { return double.IsNaN(High) || double.IsNaN(Low) ? double.NaN : High - Low; } }
        /// Signed drift across the premarket window, in points. Positive = premarket rallied.
        public double TrendPts { get { return double.IsNaN(firstClose) || double.IsNaN(LastClose) ? double.NaN : LastClose - firstClose; } }

        public void OnBarClosed(ResearchBar b)
        {
            DateTime day = b.EtClose.Date;
            if (day != curDay)
            {
                curDay = day;
                High = double.NaN; Low = double.NaN; firstClose = double.NaN; LastClose = double.NaN;
                Complete = false;
            }
            int m = b.EtClose.Hour * 60 + b.EtClose.Minute;
            if (m < PremarketStartMinutesEt) return;
            if (m > RthStartMinutesEt) { Complete = true; return; }   // frozen once the cash session opens
            if (double.IsNaN(High) || b.High > High) High = b.High;
            if (double.IsNaN(Low) || b.Low < Low) Low = b.Low;
            if (double.IsNaN(firstClose)) firstClose = b.Close;
            LastClose = b.Close;
            if (m == RthStartMinutesEt) Complete = true;
        }
    }

    /// One structural level the engine watches, with everything needed to ask both
    /// "did this bar interact with it" and "what had already happened to it".
    public class TrackedLevel
    {
        public string Name;
        public double Price = double.NaN;
        public DateTime KnownAtEt = DateTime.MaxValue;  // MaxValue = not knowable yet
        public DateTime CreatedAtEt = DateTime.MinValue;
        public int TestsToday;
        public bool BrokenToday;
        public bool LastCloseAbove;
        public bool HasPriorClose;

        public bool UsableAt(DateTime et)
        {
            return !double.IsNaN(Price) && KnownAtEt <= et;
        }
    }

    /// A single (bar, level) interaction, or a control observation with no level.
    public class ScalpEvent
    {
        // identity
        public DateTime EtClose;
        public long BarIndex;
        public string Timeframe;
        public string EventKind;            // STRUCTURE or CONTROL
        public double Open, High, Low, Close, Volume;
        public double RangePts, BodyPts, BodyPctOfRange, UpperWickPts, LowerWickPts;
        public string BarDir;

        // the level this row is about
        public string LevelName = "NONE";
        public double LevelPrice = double.NaN;
        public double DistLevelPts = double.NaN, DistLevelAtr = double.NaN;
        public HtfSweepEvent Interaction = HtfSweepEvent.NONE;
        public LevelSeqState SeqState = LevelSeqState.UNTESTED;
        public int TestNumberToday;
        public double PenetrationPts = double.NaN;
        public int LevelAgeMinutes = -1;

        // context
        public double Ema9, Ema20, Ema200, Vwap, Atr;
        public double DistEma9Atr, DistEma20Atr, DistEma200Atr, DistVwapAtr;
        public double Ema200SlopePts;
        public string EmaStack = "UNKNOWN";     // e.g. 9>20>200 = STACK_UP
        public TrendState Trend; public VolState Vol; public RangeState Rng;
        public double CompressionRatio, PosInSessRange, PullbackPct, SessRangePts;
        public double PremarketHigh, PremarketLow, PremarketRangePts, PremarketTrendPts;
        public double DistPmHighAtr, DistPmLowAtr;
        public ScalpTimeBucket Bucket;
        public double RelVolume;

        // candidate structural stops, chosen at event time
        public double StopMicroSwingLong, StopMicroSwingShort;
        public double StopBarExtremeLong, StopBarExtremeShort;
        public double StopLevelBufferLong, StopLevelBufferShort;
        public double StopAtrLong, StopAtrShort;

        // labels
        public int BarsSeen;
        public double[] MfeLongAt = new double[6];   // horizons 3,5,10,20,40,80
        public double[] MaeLongAt = new double[6];
        public double[] NetAt = new double[6];
        public int[] BarsToRLong = new int[10];      // .5 .75 1 1.25 1.5 2 2.5 3 4 5
        public int[] BarsToRShort = new int[10];
        public int BarToStopLong = -1, BarToStopShort = -1;
        public double RunMfeLong, RunMaeLong;
        public bool Complete;
    }

    /// Builds the scalping research dataset. Feed it completed bars of ONE timeframe,
    /// in order. It watches a book of structural levels and emits a row every time a
    /// bar interacts with one, plus a sampled control group of bars that interacted
    /// with nothing.
    ///
    /// Submits no orders. Exposes no entry, exit or order method of any kind.
    public class ScalpResearchEngine
    {
        public static readonly int[] Horizons = new int[] { 3, 5, 10, 20, 40, 80 };
        public static readonly double[] RGrid = new double[] { 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0 };
        private const int MaxHorizon = 80;
        private const int SwingLookback = 8;
        private const int AtrLookback = 20;
        private const int SlopeLookback = 20;

        private readonly KeyLevelEngine levels;
        private readonly Action<string> writeRow;
        private readonly List<ResearchBar> window = new List<ResearchBar>();
        private readonly List<ScalpEvent> pending = new List<ScalpEvent>();
        private readonly List<double> ema200History = new List<double>();
        private readonly RollingEma ema9 = new RollingEma(9);
        private readonly RollingEma ema20 = new RollingEma(20);
        private readonly RollingEma ema200 = new RollingEma(200);
        private readonly Dictionary<string, TrackedLevel> book = new Dictionary<string, TrackedLevel>();
        private readonly Random ctrlRng;
        private long barIndex;
        private DateTime curDay = DateTime.MinValue;

        public readonly SessionContext Session = new SessionContext();
        public readonly PremarketTracker Premarket = new PremarketTracker();

        /// Higher-timeframe structure sources, keyed by label ("3m", "5m", "15m", "30m", "60m").
        public readonly Dictionary<string, HigherTfStructure> Htf = new Dictionary<string, HigherTfStructure>();

        public string TimeframeLabel = "1m";
        /// Points within which a bar counts as having APPROACHED a level.
        public double ApproachBandPoints = 6.0;
        /// Buffer beyond a level for the "level + buffer" candidate stop.
        public double LevelStopBufferPoints = 2.0;
        /// ATR multiple for the volatility-scaled candidate stop.
        public double AtrStopMultiple = 1.0;
        /// Keep 1 in N bars that interacted with NOTHING, as the control group.
        /// This is what makes "at a level versus away from one" testable at all.
        public int ControlSampleRate = 200;
        /// Round-number levels to track, in points. 0 disables that level.
        public double RoundNumberStep = 100.0;
        /// Restrict emission to a session window, in ET minutes. Defaults to everything.
        public int EmitStartMinutesEt = 0;
        public int EmitEndMinutesEt = 1440;

        public int EventsEmitted { get; private set; }
        public int ControlsEmitted { get; private set; }
        public int EventsPending { get { return pending.Count; } }

        public ScalpResearchEngine(KeyLevelEngine levelEngine, Action<string> rowSink)
        {
            levels = levelEngine; writeRow = rowSink; ctrlRng = new Random(12345);
        }

        public void AddHtf(string label, HigherTfStructure s) { Htf[label] = s; }

        /// Feed one COMPLETED bar of this engine's timeframe, in order.
        public void OnBar(ResearchBar b)
        {
            barIndex++;
            if (b.EtClose.Date != curDay) { curDay = b.EtClose.Date; OnNewDay(); }

            // 1. advance labels on open events using ONLY this new bar
            UpdatePending(b);

            // 2. features from history that already existed
            window.Add(b);
            if (window.Count > 400) window.RemoveAt(0);
            ema9.Add(b.Close); ema20.Add(b.Close); ema200.Add(b.Close);
            ema200History.Add(ema200.Value);
            if (ema200History.Count > 500) ema200History.RemoveAt(0);

            if (window.Count > AtrLookback && InEmitWindow(b.EtClose))
                BuildRows(b);

            // 3. roll structural state AFTER the bar described itself
            Session.OnBarClosed(b);
            Premarket.OnBarClosed(b);
            RollLevelState(b);
            FlushComplete();
        }

        public void Finish()
        {
            foreach (ScalpEvent e in pending) e.Complete = true;
            FlushComplete();
        }

        private bool InEmitWindow(DateTime et)
        {
            int m = et.Hour * 60 + et.Minute;
            return m >= EmitStartMinutesEt && m <= EmitEndMinutesEt;
        }

        private void OnNewDay()
        {
            foreach (KeyValuePair<string, TrackedLevel> kv in book)
            { kv.Value.TestsToday = 0; kv.Value.BrokenToday = false; kv.Value.HasPriorClose = false; }
        }

        // ------------------------------------------------------------------
        /// Refresh the level book with everything knowable at this bar's OPEN. The
        /// cutoff is the bar's open, not its close, so no level this bar helped create
        /// can be used to judge the bar.
        private void RefreshBook(ResearchBar b)
        {
            DateTime cut = b.EtOpen;
            Put("YDAY_HIGH", levels.YdayHigh, cut); Put("YDAY_LOW", levels.YdayLow, cut);
            Put("LWEEK_HIGH", levels.LweekHigh, cut); Put("LWEEK_LOW", levels.LweekLow, cut);
            Put("DAILY_OPEN", levels.DailyOpen, cut);
            Put("VWAP", levels.Vwap, cut);
            Put("VWAP_UPPER", levels.VwapBandHigh, cut); Put("VWAP_LOWER", levels.VwapBandLow, cut);
            Put("PREMARKET_HIGH", Premarket.Complete ? Premarket.High : double.NaN, cut);
            Put("PREMARKET_LOW", Premarket.Complete ? Premarket.Low : double.NaN, cut);
            Put("OR_HIGH", Session.OrComplete ? Session.OrHigh : double.NaN, cut);
            Put("OR_LOW", Session.OrComplete ? Session.OrLow : double.NaN, cut);
            Put("SESS_HIGH", Session.SessHigh, cut); Put("SESS_LOW", Session.SessLow, cut);

            if (RoundNumberStep > 0)
            {
                double up = Math.Ceiling(b.Open / RoundNumberStep) * RoundNumberStep;
                double dn = Math.Floor(b.Open / RoundNumberStep) * RoundNumberStep;
                Put("ROUND_ABOVE", up, cut); Put("ROUND_BELOW", dn, cut);
            }

            foreach (KeyValuePair<string, HigherTfStructure> kv in Htf)
            {
                HtfSwing hi = kv.Value.SwingHighKnownAt(cut);
                HtfSwing lo = kv.Value.SwingLowKnownAt(cut);
                PutSwing("SWING_" + kv.Key.ToUpperInvariant() + "_HIGH", hi, cut);
                PutSwing("SWING_" + kv.Key.ToUpperInvariant() + "_LOW", lo, cut);
            }
        }

        private void Put(string name, double price, DateTime knownAt)
        {
            TrackedLevel t;
            if (!book.TryGetValue(name, out t)) { t = new TrackedLevel(); t.Name = name; book[name] = t; }
            if (double.IsNaN(price)) { t.Price = double.NaN; t.KnownAtEt = DateTime.MaxValue; return; }
            if (double.IsNaN(t.Price) || Math.Abs(t.Price - price) > 1e-9)
            {
                // the level moved, so it is a NEW level: reset its history rather than
                // carrying the old one's test count onto a different price
                t.Price = price; t.CreatedAtEt = knownAt; t.TestsToday = 0;
                t.BrokenToday = false; t.HasPriorClose = false;
            }
            t.KnownAtEt = knownAt;
        }

        private void PutSwing(string name, HtfSwing s, DateTime cut)
        {
            if (!s.Valid) { Put(name, double.NaN, cut); return; }
            TrackedLevel t;
            if (!book.TryGetValue(name, out t)) { t = new TrackedLevel(); t.Name = name; book[name] = t; }
            if (double.IsNaN(t.Price) || Math.Abs(t.Price - s.Price) > 1e-9)
            {
                t.Price = s.Price; t.TestsToday = 0; t.BrokenToday = false; t.HasPriorClose = false;
            }
            t.CreatedAtEt = s.FormedAtEt;
            t.KnownAtEt = s.KnownAtEt;   // the confirmation time, enforced by UsableAt
        }

        private void RollLevelState(ResearchBar b)
        {
            foreach (KeyValuePair<string, TrackedLevel> kv in book)
            {
                TrackedLevel t = kv.Value;
                if (!t.UsableAt(b.EtClose)) continue;
                bool touched = b.High >= t.Price && b.Low <= t.Price;
                if (touched) t.TestsToday++;
                if (t.HasPriorClose && ((b.Close > t.Price) != t.LastCloseAbove)) t.BrokenToday = true;
                t.LastCloseAbove = b.Close > t.Price;
                t.HasPriorClose = true;
            }
        }

        // ------------------------------------------------------------------
        private void BuildRows(ResearchBar b)
        {
            RefreshBook(b);
            double atr = Atr();
            bool any = false;
            foreach (KeyValuePair<string, TrackedLevel> kv in book)
            {
                TrackedLevel t = kv.Value;
                if (!t.UsableAt(b.EtOpen)) continue;
                bool above = t.Price > b.Close;
                HtfSweepEvent ev = above
                    ? HigherTfStructure.ClassifyAgainstHigh(b.High, b.Close, t.Price, ApproachBandPoints)
                    : HigherTfStructure.ClassifyAgainstLow(b.Low, b.Close, t.Price, ApproachBandPoints);
                // a level sitting inside the bar is interacted with from whichever side it was approached
                if (ev == HtfSweepEvent.NONE && b.High >= t.Price && b.Low <= t.Price)
                    ev = HtfSweepEvent.TOUCHED;
                if (ev == HtfSweepEvent.NONE) continue;
                any = true;
                pending.Add(MakeEvent(b, atr, t, ev));
            }
            if (!any && ControlSampleRate > 0 && ctrlRng.Next(ControlSampleRate) == 0)
                pending.Add(MakeEvent(b, atr, null, HtfSweepEvent.NONE));
        }

        private ScalpEvent MakeEvent(ResearchBar b, double atr, TrackedLevel t, HtfSweepEvent ev)
        {
            ScalpEvent e = new ScalpEvent();
            e.EtClose = b.EtClose; e.BarIndex = barIndex; e.Timeframe = TimeframeLabel;
            e.EventKind = t == null ? "CONTROL" : "STRUCTURE";
            e.Open = b.Open; e.High = b.High; e.Low = b.Low; e.Close = b.Close; e.Volume = b.Volume;
            e.RangePts = b.High - b.Low; e.BodyPts = Math.Abs(b.Close - b.Open);
            e.BodyPctOfRange = e.RangePts > 0 ? 100.0 * e.BodyPts / e.RangePts : 0;
            e.UpperWickPts = b.High - Math.Max(b.Open, b.Close);
            e.LowerWickPts = Math.Min(b.Open, b.Close) - b.Low;
            e.BarDir = b.Close > b.Open ? "UP" : b.Close < b.Open ? "DOWN" : "FLAT";
            e.Atr = atr;

            if (t != null)
            {
                e.LevelName = t.Name; e.LevelPrice = t.Price;
                e.DistLevelPts = b.Close - t.Price;
                e.DistLevelAtr = atr > 0 ? e.DistLevelPts / atr : double.NaN;
                e.Interaction = ev;
                e.TestNumberToday = t.TestsToday;
                e.PenetrationPts = t.Price > b.Close ? Math.Max(0, b.High - t.Price) : Math.Max(0, t.Price - b.Low);
                e.LevelAgeMinutes = t.CreatedAtEt == DateTime.MinValue ? -1
                    : (int)(b.EtClose - t.CreatedAtEt).TotalMinutes;
                e.SeqState = Sequence(t, b, ev);
                e.StopLevelBufferLong = b.Close - (t.Price - LevelStopBufferPoints);
                e.StopLevelBufferShort = (t.Price + LevelStopBufferPoints) - b.Close;
            }

            e.Ema9 = ema9.Value; e.Ema20 = ema20.Value; e.Ema200 = ema200.Value; e.Vwap = levels.Vwap;
            if (atr > 0)
            {
                e.DistEma9Atr = (b.Close - e.Ema9) / atr;
                e.DistEma20Atr = (b.Close - e.Ema20) / atr;
                e.DistEma200Atr = (b.Close - e.Ema200) / atr;
                e.DistVwapAtr = (b.Close - e.Vwap) / atr;
            }
            int hn = ema200History.Count;
            e.Ema200SlopePts = hn > SlopeLookback && !double.IsNaN(ema200History[hn - 1 - SlopeLookback])
                ? ema200History[hn - 1] - ema200History[hn - 1 - SlopeLookback] : double.NaN;
            e.EmaStack = double.IsNaN(e.Ema9) || double.IsNaN(e.Ema20) || double.IsNaN(e.Ema200) ? "UNKNOWN"
                : (e.Ema9 > e.Ema20 && e.Ema20 > e.Ema200) ? "STACK_UP"
                : (e.Ema9 < e.Ema20 && e.Ema20 < e.Ema200) ? "STACK_DOWN" : "MIXED";

            double pos, comp, pull;
            Session.Describe(b, atr, out pos, out comp, out pull);
            e.PosInSessRange = pos; e.CompressionRatio = comp; e.PullbackPct = pull;
            e.SessRangePts = double.IsNaN(Session.SessHigh) || double.IsNaN(Session.SessLow)
                ? double.NaN : Session.SessHigh - Session.SessLow;

            e.PremarketHigh = Premarket.High; e.PremarketLow = Premarket.Low;
            e.PremarketRangePts = Premarket.RangePts; e.PremarketTrendPts = Premarket.TrendPts;
            if (atr > 0)
            {
                e.DistPmHighAtr = (b.Close - Premarket.High) / atr;
                e.DistPmLowAtr = (b.Close - Premarket.Low) / atr;
            }

            e.Trend = ClassifyTrend(b, e); e.Vol = ClassifyVol(atr); e.Rng = ClassifyRange(comp);
            e.Bucket = Bucket(b.EtClose);
            e.RelVolume = RelVolume(b);

            // candidate structural stops
            double swingLow = b.Low, swingHigh = b.High;
            int n = window.Count;
            for (int i = Math.Max(0, n - 1 - SwingLookback); i < n - 1; i++)
            {
                if (window[i].Low < swingLow) swingLow = window[i].Low;
                if (window[i].High > swingHigh) swingHigh = window[i].High;
            }
            e.StopMicroSwingLong = b.Close - swingLow;
            e.StopMicroSwingShort = swingHigh - b.Close;
            e.StopBarExtremeLong = b.Close - b.Low;
            e.StopBarExtremeShort = b.High - b.Close;
            e.StopAtrLong = atr * AtrStopMultiple;
            e.StopAtrShort = atr * AtrStopMultiple;

            for (int i = 0; i < RGrid.Length; i++) { e.BarsToRLong[i] = -1; e.BarsToRShort[i] = -1; }
            return e;
        }

        private static LevelSeqState Sequence(TrackedLevel t, ResearchBar b, HtfSweepEvent ev)
        {
            if (t.TestsToday == 0 && !t.BrokenToday) return LevelSeqState.UNTESTED;
            if (t.BrokenToday)
            {
                bool closeBackInside = t.HasPriorClose && ((b.Close > t.Price) != t.LastCloseAbove);
                return closeBackInside ? LevelSeqState.RECLAIM_AFTER_BREAK : LevelSeqState.RETEST_AFTER_BREAK;
            }
            return t.TestsToday <= 1 ? LevelSeqState.FIRST_TEST : LevelSeqState.REPEAT_TEST;
        }

        private double Atr()
        {
            int n = window.Count; if (n < AtrLookback + 1) return double.NaN;
            double s = 0;
            for (int i = n - AtrLookback; i < n; i++)
            {
                double pc = window[i - 1].Close;
                double tr = Math.Max(window[i].High - window[i].Low,
                            Math.Max(Math.Abs(window[i].High - pc), Math.Abs(window[i].Low - pc)));
                s += tr;
            }
            return s / AtrLookback;
        }

        private double RelVolume(ResearchBar b)
        {
            int n = window.Count; if (n < 21) return double.NaN;
            double s = 0; for (int i = n - 21; i < n - 1; i++) s += window[i].Volume;
            double avg = s / 20.0;
            return avg > 0 ? b.Volume / avg : double.NaN;
        }

        private TrendState ClassifyTrend(ResearchBar b, ScalpEvent e)
        {
            if (double.IsNaN(e.Ema200SlopePts) || double.IsNaN(e.Ema200) || e.Atr <= 0) return TrendState.UNKNOWN;
            double slopeAtr = e.Ema200SlopePts / e.Atr;
            if (slopeAtr > 0.5 && b.Close > e.Ema200) return TrendState.UP;
            if (slopeAtr < -0.5 && b.Close < e.Ema200) return TrendState.DOWN;
            return TrendState.CHOP;
        }

        private readonly List<double> atrHistory = new List<double>();
        private VolState ClassifyVol(double atr)
        {
            if (double.IsNaN(atr)) return VolState.UNKNOWN;
            atrHistory.Add(atr);
            if (atrHistory.Count > 500) atrHistory.RemoveAt(0);
            if (atrHistory.Count < 100) return VolState.UNKNOWN;
            List<double> sorted = new List<double>(atrHistory); sorted.Sort();
            double lo = sorted[(int)(sorted.Count * 0.33)], hi = sorted[(int)(sorted.Count * 0.67)];
            return atr < lo ? VolState.LOW : atr > hi ? VolState.HIGH : VolState.NORMAL;
        }

        private static RangeState ClassifyRange(double comp)
        {
            if (double.IsNaN(comp)) return RangeState.UNKNOWN;
            return comp < 3.0 ? RangeState.COMPRESSED : comp > 6.0 ? RangeState.EXPANDING : RangeState.NORMAL;
        }

        public static ScalpTimeBucket Bucket(DateTime et)
        {
            int m = et.Hour * 60 + et.Minute;
            if (m < 450) return ScalpTimeBucket.OVERNIGHT;
            if (m < 480) return ScalpTimeBucket.T0730_0800;
            if (m < 510) return ScalpTimeBucket.T0800_0830;
            if (m < 540) return ScalpTimeBucket.T0830_0900;
            if (m < 570) return ScalpTimeBucket.T0900_0929;
            if (m <= 585) return ScalpTimeBucket.T0930_0945;
            if (m <= 600) return ScalpTimeBucket.T0945_1000;
            if (m <= 615) return ScalpTimeBucket.T1000_1015;
            if (m <= 630) return ScalpTimeBucket.T1015_1030;
            if (m <= 645) return ScalpTimeBucket.T1030_1045;
            if (m <= 660) return ScalpTimeBucket.T1045_1100;
            if (m <= 690) return ScalpTimeBucket.T1100_1130;
            if (m <= 780) return ScalpTimeBucket.T1130_1300;
            if (m <= 960) return ScalpTimeBucket.T1300_1600;
            return ScalpTimeBucket.AFTER_1600;
        }

        // ------------------------------------------------------------------
        private void UpdatePending(ResearchBar b)
        {
            for (int idx = 0; idx < pending.Count; idx++)
            {
                ScalpEvent e = pending[idx];
                if (e.Complete) continue;
                e.BarsSeen++;
                double up = b.High - e.Close, dn = e.Close - b.Low;
                if (up > e.RunMfeLong) e.RunMfeLong = up;
                if (dn > e.RunMaeLong) e.RunMaeLong = dn;
                for (int h = 0; h < Horizons.Length; h++)
                {
                    if (e.BarsSeen <= Horizons[h])
                    {
                        e.MfeLongAt[h] = e.RunMfeLong; e.MaeLongAt[h] = e.RunMaeLong;
                        if (e.BarsSeen == Horizons[h]) e.NetAt[h] = b.Close - e.Close;
                    }
                }
                // R-race against the MICRO SWING stop - the structural one
                double sl = e.StopMicroSwingLong;
                if (sl > 0)
                {
                    if (e.BarToStopLong < 0 && b.Low <= e.Close - sl) e.BarToStopLong = e.BarsSeen;
                    for (int i = 0; i < RGrid.Length; i++)
                        if (e.BarsToRLong[i] < 0 && b.High >= e.Close + RGrid[i] * sl) e.BarsToRLong[i] = e.BarsSeen;
                }
                double ss = e.StopMicroSwingShort;
                if (ss > 0)
                {
                    if (e.BarToStopShort < 0 && b.High >= e.Close + ss) e.BarToStopShort = e.BarsSeen;
                    for (int i = 0; i < RGrid.Length; i++)
                        if (e.BarsToRShort[i] < 0 && b.Low <= e.Close - RGrid[i] * ss) e.BarsToRShort[i] = e.BarsSeen;
                }
                if (e.BarsSeen >= MaxHorizon) e.Complete = true;
            }
        }

        private void FlushComplete()
        {
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                if (!pending[i].Complete) continue;
                writeRow(ToCsv(pending[i]));
                if (pending[i].EventKind == "CONTROL") ControlsEmitted++; else EventsEmitted++;
                pending.RemoveAt(i);
            }
        }

        // ------------------------------------------------------------------
        public static string CsvHeader()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("date,timeEt,timeframe,barIndex,eventKind,barDir,open,high,low,close,volume,");
            sb.Append("rangePts,bodyPts,bodyPctOfRange,upperWickPts,lowerWickPts,relVolume,atr,");
            sb.Append("levelName,levelPrice,distLevelPts,distLevelAtr,interaction,seqState,testNumberToday,");
            sb.Append("penetrationPts,levelAgeMinutes,");
            sb.Append("ema9,ema20,ema200,vwap,distEma9Atr,distEma20Atr,distEma200Atr,distVwapAtr,");
            sb.Append("ema200SlopePts,emaStack,trendState,volState,rangeState,");
            sb.Append("compressionRatio,posInSessRange,pullbackPct,sessRangePts,");
            sb.Append("premarketHigh,premarketLow,premarketRangePts,premarketTrendPts,distPmHighAtr,distPmLowAtr,");
            sb.Append("timeBucket,");
            sb.Append("stopMicroSwingLong,stopMicroSwingShort,stopBarExtremeLong,stopBarExtremeShort,");
            sb.Append("stopLevelBufferLong,stopLevelBufferShort,stopAtrLong,stopAtrShort,");
            foreach (int h in Horizons) sb.Append("mfeLong_" + h + ",maeLong_" + h + ",net_" + h + ",");
            sb.Append("barToStopLong,barToStopShort,");
            foreach (double r in RGrid) sb.Append("barToLong_" + r.ToString("0.##", CultureInfo.InvariantCulture) + "R,");
            foreach (double r in RGrid) sb.Append("barToShort_" + r.ToString("0.##", CultureInfo.InvariantCulture) + "R,");
            sb.Append("barsObserved");
            return sb.ToString();
        }

        private static string F(double v)
        {
            return double.IsNaN(v) || double.IsInfinity(v) ? "" : v.ToString("0.####", CultureInfo.InvariantCulture);
        }

        public static string ToCsv(ScalpEvent e)
        {
            CultureInfo ci = CultureInfo.InvariantCulture;
            StringBuilder sb = new StringBuilder(600);
            sb.Append(e.EtClose.ToString("yyyy-MM-dd", ci)).Append(',')
              .Append(e.EtClose.ToString("HH:mm:ss", ci)).Append(',')
              .Append(e.Timeframe).Append(',').Append(e.BarIndex).Append(',')
              .Append(e.EventKind).Append(',').Append(e.BarDir).Append(',');
            sb.Append(F(e.Open)).Append(',').Append(F(e.High)).Append(',').Append(F(e.Low)).Append(',')
              .Append(F(e.Close)).Append(',').Append(F(e.Volume)).Append(',');
            sb.Append(F(e.RangePts)).Append(',').Append(F(e.BodyPts)).Append(',').Append(F(e.BodyPctOfRange)).Append(',')
              .Append(F(e.UpperWickPts)).Append(',').Append(F(e.LowerWickPts)).Append(',')
              .Append(F(e.RelVolume)).Append(',').Append(F(e.Atr)).Append(',');
            sb.Append(e.LevelName).Append(',').Append(F(e.LevelPrice)).Append(',')
              .Append(F(e.DistLevelPts)).Append(',').Append(F(e.DistLevelAtr)).Append(',')
              .Append(e.Interaction).Append(',').Append(e.SeqState).Append(',')
              .Append(e.TestNumberToday).Append(',').Append(F(e.PenetrationPts)).Append(',')
              .Append(e.LevelAgeMinutes).Append(',');
            sb.Append(F(e.Ema9)).Append(',').Append(F(e.Ema20)).Append(',').Append(F(e.Ema200)).Append(',')
              .Append(F(e.Vwap)).Append(',').Append(F(e.DistEma9Atr)).Append(',').Append(F(e.DistEma20Atr)).Append(',')
              .Append(F(e.DistEma200Atr)).Append(',').Append(F(e.DistVwapAtr)).Append(',')
              .Append(F(e.Ema200SlopePts)).Append(',').Append(e.EmaStack).Append(',')
              .Append(e.Trend).Append(',').Append(e.Vol).Append(',').Append(e.Rng).Append(',');
            sb.Append(F(e.CompressionRatio)).Append(',').Append(F(e.PosInSessRange)).Append(',')
              .Append(F(e.PullbackPct)).Append(',').Append(F(e.SessRangePts)).Append(',');
            sb.Append(F(e.PremarketHigh)).Append(',').Append(F(e.PremarketLow)).Append(',')
              .Append(F(e.PremarketRangePts)).Append(',').Append(F(e.PremarketTrendPts)).Append(',')
              .Append(F(e.DistPmHighAtr)).Append(',').Append(F(e.DistPmLowAtr)).Append(',');
            sb.Append(e.Bucket).Append(',');
            sb.Append(F(e.StopMicroSwingLong)).Append(',').Append(F(e.StopMicroSwingShort)).Append(',')
              .Append(F(e.StopBarExtremeLong)).Append(',').Append(F(e.StopBarExtremeShort)).Append(',')
              .Append(F(e.StopLevelBufferLong)).Append(',').Append(F(e.StopLevelBufferShort)).Append(',')
              .Append(F(e.StopAtrLong)).Append(',').Append(F(e.StopAtrShort)).Append(',');
            for (int h = 0; h < Horizons.Length; h++)
                sb.Append(F(e.MfeLongAt[h])).Append(',').Append(F(e.MaeLongAt[h])).Append(',').Append(F(e.NetAt[h])).Append(',');
            sb.Append(e.BarToStopLong).Append(',').Append(e.BarToStopShort).Append(',');
            for (int i = 0; i < RGrid.Length; i++) sb.Append(e.BarsToRLong[i]).Append(',');
            for (int i = 0; i < RGrid.Length; i++) sb.Append(e.BarsToRShort[i]).Append(',');
            sb.Append(e.BarsSeen);
            return sb.ToString();
        }
    }
}
