// ============================================================================
// VectorCandleResearchEngine.cs
//
// RESEARCH MODULE - SUBMITS NO ORDERS, EVER.
//
// Purpose: build an UNBIASED event dataset of every completed MNQ 1-minute
// Traders Reality vector candle, with the context that was known AT THAT
// MOMENT, plus future-outcome labels attached afterwards.
//
// It exists because the existing strategy logs only contain setups the old
// engines happened to notice. That is a biased sample and cannot answer
// "what do vector candles actually do?".
//
// STRICT NO-LOOKAHEAD CONTRACT
//   - Every FEATURE column is frozen at the instant the event bar completes.
//   - Every LABEL column is filled in only from bars that arrive afterwards.
//   - An event is not written to the CSV until its full forward horizon has
//     elapsed, so a feature can never be contaminated by a label.
//   - Candidate stops are chosen from information available at event time.
//     R is never manufactured by picking a stop after seeing the future.
//
// This file is completely independent of FakeBreakoutEngine and
// VectorBreakRetestEngine. It shares only read-only utilities.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqTwo
{
    // How a candle interacted with one specific key level.
    public enum LevelInteraction
    {
        NEVER_TOUCHED,          // whole candle on one side, not close to the level
        APPROACHED,             // came within the approach band but never traded through
        FIRST_TOUCH,            // touched the level exactly, no penetration
        WICK_THROUGH_CLOSE_INSIDE,   // traded through, closed back on the original side
        WICK_THROUGH_CLOSE_OUTSIDE,  // traded through and closed on the far side
        OPEN_ONE_SIDE_CLOSE_OTHER,   // opened one side, closed the other
        CLOSED_THROUGH          // closed beyond the level having opened beyond it too
    }

    // Position of this candle in a run of candles through the level.
    public enum LevelSequenceRole
    {
        NONE,
        FIRST_CANDLE_THROUGH,
        CONTINUATION_THROUGH,   // 2nd/3rd+ consecutive candle beyond the level
        RETEST_AFTER_BREAK,     // came back to the level after a prior break
        RECLAIM_AFTER_BREAK     // closed back inside after a prior break (fake-break leg)
    }

    public enum EmaRegime { ABOVE_RISING, ABOVE_FALLING, BELOW_RISING, BELOW_FALLING, TOUCHING, CROSSING, UNKNOWN }

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

    /// A vector event: features frozen at event time, labels filled in later.
    public class VectorEvent
    {
        // ---- IDENTITY (frozen) ----
        public DateTime EtClose;
        public long BarIndex;
        public VectorType Vector;
        public string Direction;          // BULL / BEAR (candle direction, not a trade)
        public double Open, High, Low, Close, Volume;
        public double RangePts, BodyPts, BodyPctOfRange, UpperWickPts, LowerWickPts;
        public double AvgVol10, RelVolume, VolumeSpread, HighestVolSpread10, VolSpreadRatio;
        public string ClassificationTrigger;   // VOLUME_2X / VOLSPREAD_MAX / VOLUME_1_5X / NONE

        // ---- LOCATION (frozen) ----
        public double YdayHigh, YdayLow, LweekHigh, LweekLow, DailyOpen, Ema200, Ema9, Vwap;
        public double DistYdayHigh, DistYdayLow, DistLweekHigh, DistLweekLow, DistEma200, DistDailyOpen;
        public double Ema200SlopePts;      // EMA200 now minus EMA200 20 bars ago
        public string Ema200Slope;         // RISING / FALLING / FLAT
        public EmaRegime Ema200Regime;
        public double AtrProxy;            // mean true range of the last 20 bars, for normalisation
        public double DistEma200Atr;       // distance to EMA200 in ATR units

        // ---- LEVEL INTERACTION (frozen), one set per eligible level ----
        public Dictionary<KeyLevelId, LevelInteraction> Interaction = new Dictionary<KeyLevelId, LevelInteraction>();
        public Dictionary<KeyLevelId, LevelSequenceRole> SeqRole = new Dictionary<KeyLevelId, LevelSequenceRole>();
        public Dictionary<KeyLevelId, double> PenetrationPts = new Dictionary<KeyLevelId, double>();
        public Dictionary<KeyLevelId, double> CloseDistFromLevel = new Dictionary<KeyLevelId, double>();
        public Dictionary<KeyLevelId, bool> PriorCloseOppositeSide = new Dictionary<KeyLevelId, bool>();
        public Dictionary<KeyLevelId, int> TestNumberToday = new Dictionary<KeyLevelId, int>();
        public LevelInteraction Ema200Interaction;

        // ---- SEQUENCE (frozen) ----
        public VectorType PrevVector, PrevPrevVector;
        public string PrevCandleKind;      // includes REGULAR_* so vector->regular chains are visible
        public int SameDirectionVectorRun;

        public TimeBucket Bucket;
        public string TimeframeLabel = "1m";

        // ---- CANDIDATE STOPS (frozen, chosen without future data) ----
        public double StopVectorWickLongPts, StopVectorWickShortPts;
        public double StopLocalSwingLongPts, StopLocalSwingShortPts;
        public double StopLevelBufferLongPts, StopLevelBufferShortPts;
        public double StopExcursionLongPts, StopExcursionShortPts;

        // ---- LABELS (future only) ----
        public int BarsSeen;
        public double[] MfeLongAt = new double[8];   // horizons 1,2,3,5,10,15,30,60
        public double[] MaeLongAt = new double[8];
        public double[] NetAt = new double[8];
        public double RunMfeLong, RunMaeLong;
        public int BarsToMfeLong, BarsToMaeLong;
        // R-race against the primary (vector wick) stop, in the candle's own direction
        // and in the opposite direction. -1 = never reached inside the horizon.
        public int[] BarsToRLong = new int[9];       // +0.5,0.75,1,1.25,1.5,2,2.5,3,4 R
        public int BarToStopLong = -1;
        public int[] BarsToRShort = new int[9];
        public int BarToStopShort = -1;
        public bool Complete;
    }

    /// Builds the event dataset. Feed it completed 1-minute bars in order.
    public class VectorCandleResearchEngine
    {
        public static readonly int[] Horizons = new int[] { 1, 2, 3, 5, 10, 15, 30, 60 };
        public static readonly double[] RGrid = new double[] { 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0 };
        private const int MaxHorizon = 60;
        private const int SwingLookback = 10;
        private const int SlopeLookback = 20;
        private const int AtrLookback = 20;

        private static readonly KeyLevelId[] Levels = new KeyLevelId[]
        {
            KeyLevelId.YDAY_HIGH, KeyLevelId.YDAY_LOW, KeyLevelId.LWEEK_HIGH, KeyLevelId.LWEEK_LOW
        };

        private readonly KeyLevelEngine levels;
        private readonly Action<string> writeRow;
        private readonly List<ResearchBar> window = new List<ResearchBar>();   // recent bars for features
        private readonly List<VectorEvent> pending = new List<VectorEvent>();
        private readonly List<double> ema200History = new List<double>();

        private readonly RollingEma ema200 = new RollingEma(200);
        private readonly RollingEma ema9 = new RollingEma(9);

        private long barIndex;
        private VectorType prevVector = VectorType.REGULAR_BULLISH;
        private VectorType prevPrevVector = VectorType.REGULAR_BULLISH;
        private string prevKind = "NONE";
        private int sameDirRun;
        private DateTime currentDay = DateTime.MinValue;

        // per-level state that must not use future data
        private readonly Dictionary<KeyLevelId, int> testsToday = new Dictionary<KeyLevelId, int>();
        private readonly Dictionary<KeyLevelId, int> consecutiveBeyond = new Dictionary<KeyLevelId, int>();
        private readonly Dictionary<KeyLevelId, bool> brokenEarlierToday = new Dictionary<KeyLevelId, bool>();
        private readonly Dictionary<KeyLevelId, bool> prevCloseAbove = new Dictionary<KeyLevelId, bool>();

        /// Band, in points, within which a candle counts as having APPROACHED a level.
        public double ApproachBandPoints = 10.0;
        /// Buffer used by the "key level + buffer" candidate stop.
        public double LevelStopBufferPoints = 2.0;
        /// Log EVERY candle, not only vectors. Off by default: the dataset is about vectors.
        public bool IncludeRegularCandles = false;

        /// Which series this instance is observing ("15m", "3m", "1m", "30s", "15s", ...).
        /// Emitted as a column so one CSV can hold every timeframe.
        public string TimeframeLabel = "1m";

        /// The research brief specifies the ONE-MINUTE EMA200 as context for every
        /// event, including sub-minute events. When these are supplied the engine
        /// reports them instead of its own per-series EMA, so a 15s row still carries
        /// the 1m EMA200. Left null, it falls back to its own internally computed EMA.
        public Func<double> Ema200Provider;
        public Func<double> Ema9Provider;

        /// This instance's OWN internally computed EMAs. The 1m instance exposes these
        /// so every other timeframe can report the ONE-MINUTE EMA200 as context.
        public double LocalEma200 { get { return ema200.Value; } }
        public double LocalEma9 { get { return ema9.Value; } }

        public int EventsEmitted { get; private set; }
        public int EventsPending { get { return pending.Count; } }

        public VectorCandleResearchEngine(KeyLevelEngine levelEngine, Action<string> rowSink)
        {
            levels = levelEngine;
            writeRow = rowSink;
            foreach (KeyLevelId id in Levels)
            {
                testsToday[id] = 0; consecutiveBeyond[id] = 0;
                brokenEarlierToday[id] = false; prevCloseAbove[id] = true;
            }
        }

        public void OnNewDay()
        {
            foreach (KeyLevelId id in Levels)
            {
                testsToday[id] = 0; consecutiveBeyond[id] = 0; brokenEarlierToday[id] = false;
            }
        }

        /// Feed one COMPLETED 1-minute bar. Order matters: labels for older events are
        /// updated from this bar BEFORE this bar is allowed to create a new event, so an
        /// event can never see its own future.
        public void OnBar(ResearchBar b)
        {
            barIndex++;
            DateTime day = b.EtClose.Date;
            if (day != currentDay) { currentDay = day; OnNewDay(); }

            // ---- 1. advance labels on already-open events (uses ONLY this new bar) ----
            UpdatePending(b);

            // ---- 2. features for this bar, computed from history that already existed ----
            window.Add(b);
            if (window.Count > 300) window.RemoveAt(0);

            double avgVol10 = 0, highestVolSpread10 = 0;
            int n = window.Count;
            if (n >= 11)
            {
                for (int i = n - 11; i <= n - 2; i++)   // the previous 10 COMPLETED bars
                {
                    avgVol10 += window[i].Volume;
                    double vs = window[i].Volume * (window[i].High - window[i].Low);
                    if (vs > highestVolSpread10) highestVolSpread10 = vs;
                }
                avgVol10 /= 10.0;
            }

            VectorType vec = n >= 11
                ? VectorClassifier.Classify(b.Open, b.High, b.Low, b.Close, b.Volume, avgVol10, highestVolSpread10)
                : VectorType.REGULAR_BULLISH;

            // EMA state BEFORE adding this close would be look-behind; the strategies use
            // the EMA value of the completed bar, so this bar is included, matching them.
            ema200.Add(b.Close);
            ema9.Add(b.Close);
            ema200History.Add(ema200.Value);
            if (ema200History.Count > 400) ema200History.RemoveAt(0);

            bool isVector = !VectorClassifier.IsRegular(vec);
            if (n >= 11 && (isVector || IncludeRegularCandles))
                pending.Add(BuildEvent(b, vec, avgVol10, highestVolSpread10));

            // ---- 3. roll sequence state AFTER the event was built ----
            prevPrevVector = prevVector;
            prevVector = vec;
            prevKind = vec.ToString();
            if (isVector)
            {
                bool bull = vec == VectorType.GREEN_VECTOR || vec == VectorType.BLUE_VECTOR;
                bool prevBull = prevPrevVector == VectorType.GREEN_VECTOR || prevPrevVector == VectorType.BLUE_VECTOR;
                sameDirRun = (VectorClassifier.IsRegular(prevPrevVector) || bull != prevBull) ? 1 : sameDirRun + 1;
            }
            else sameDirRun = 0;

            UpdateLevelState(b);
            FlushComplete();
        }

        /// Call once at the end of the run so partially-labelled events are not lost.
        public void Finish()
        {
            foreach (VectorEvent e in pending) { e.Complete = true; }
            FlushComplete();
        }

        // ------------------------------------------------------------------
        private VectorEvent BuildEvent(ResearchBar b, VectorType vec, double avgVol10, double hvs10)
        {
            VectorEvent e = new VectorEvent();
            e.EtClose = b.EtClose;
            e.BarIndex = barIndex;
            e.Vector = vec;
            e.Direction = b.Close > b.Open ? "BULL" : "BEAR";
            e.Open = b.Open; e.High = b.High; e.Low = b.Low; e.Close = b.Close; e.Volume = b.Volume;
            e.RangePts = b.High - b.Low;
            e.BodyPts = Math.Abs(b.Close - b.Open);
            e.BodyPctOfRange = e.RangePts > 0 ? 100.0 * e.BodyPts / e.RangePts : 0;
            e.UpperWickPts = b.High - Math.Max(b.Open, b.Close);
            e.LowerWickPts = Math.Min(b.Open, b.Close) - b.Low;
            e.AvgVol10 = avgVol10;
            e.RelVolume = avgVol10 > 0 ? b.Volume / avgVol10 : 0;
            e.VolumeSpread = b.Volume * e.RangePts;
            e.HighestVolSpread10 = hvs10;
            e.VolSpreadRatio = hvs10 > 0 ? e.VolumeSpread / hvs10 : 0;
            e.ClassificationTrigger =
                (avgVol10 > 0 && b.Volume >= 2.0 * avgVol10) ? "VOLUME_2X"
                : (hvs10 > 0 && e.VolumeSpread >= hvs10) ? "VOLSPREAD_MAX"
                : (avgVol10 > 0 && b.Volume >= 1.5 * avgVol10) ? "VOLUME_1_5X" : "NONE";

            e.YdayHigh = levels.YdayHigh; e.YdayLow = levels.YdayLow;
            e.LweekHigh = levels.LweekHigh; e.LweekLow = levels.LweekLow;
            e.DailyOpen = levels.DailyOpen; e.Vwap = levels.Vwap;
            e.Ema200 = Ema200Provider != null ? Ema200Provider() : ema200.Value;
            e.Ema9 = Ema9Provider != null ? Ema9Provider() : ema9.Value;
            e.DistYdayHigh = b.Close - e.YdayHigh;
            e.DistYdayLow = b.Close - e.YdayLow;
            e.DistLweekHigh = b.Close - e.LweekHigh;
            e.DistLweekLow = b.Close - e.LweekLow;
            e.DistDailyOpen = b.Close - e.DailyOpen;
            e.DistEma200 = b.Close - e.Ema200;

            // EMA200 slope over the last SlopeLookback bars
            int hn = ema200History.Count;
            if (hn > SlopeLookback && !double.IsNaN(ema200History[hn - 1 - SlopeLookback]))
                e.Ema200SlopePts = ema200History[hn - 1] - ema200History[hn - 1 - SlopeLookback];
            else e.Ema200SlopePts = double.NaN;
            e.Ema200Slope = double.IsNaN(e.Ema200SlopePts) ? "UNKNOWN"
                : e.Ema200SlopePts > 1.0 ? "RISING" : e.Ema200SlopePts < -1.0 ? "FALLING" : "FLAT";

            e.AtrProxy = AtrProxy();
            e.DistEma200Atr = e.AtrProxy > 0 && !double.IsNaN(e.DistEma200) ? e.DistEma200 / e.AtrProxy : double.NaN;
            e.Ema200Interaction = Classify(b, e.Ema200);
            e.Ema200Regime = Regime(b, e);

            foreach (KeyLevelId id in Levels)
            {
                double lvl = levels.GetTriggerLevelPrice(id);
                e.Interaction[id] = Classify(b, lvl);
                e.PenetrationPts[id] = Penetration(b, lvl);
                e.CloseDistFromLevel[id] = double.IsNaN(lvl) ? double.NaN : b.Close - lvl;
                e.PriorCloseOppositeSide[id] = PriorOpposite(b, lvl, id);
                e.TestNumberToday[id] = testsToday.ContainsKey(id) ? testsToday[id] : 0;
                e.SeqRole[id] = SequenceRole(b, lvl, id, e.Interaction[id]);
            }

            e.PrevVector = prevVector;
            e.PrevPrevVector = prevPrevVector;
            e.PrevCandleKind = prevKind;
            e.SameDirectionVectorRun = sameDirRun;
            e.Bucket = BucketOf(b.EtClose);
            e.TimeframeLabel = TimeframeLabel;

            // ---- candidate stops, all chosen from information available NOW ----
            e.StopVectorWickLongPts = b.Close - b.Low;
            e.StopVectorWickShortPts = b.High - b.Close;

            double swingLow = double.MaxValue, swingHigh = double.MinValue;
            int from = Math.Max(0, window.Count - SwingLookback);
            for (int i = from; i < window.Count; i++)
            {
                if (window[i].Low < swingLow) swingLow = window[i].Low;
                if (window[i].High > swingHigh) swingHigh = window[i].High;
            }
            e.StopLocalSwingLongPts = b.Close - swingLow;
            e.StopLocalSwingShortPts = swingHigh - b.Close;

            double nearest = NearestLevel(b.Close);
            e.StopLevelBufferLongPts = double.IsNaN(nearest) ? double.NaN
                : Math.Max(0, b.Close - (nearest - LevelStopBufferPoints));
            e.StopLevelBufferShortPts = double.IsNaN(nearest) ? double.NaN
                : Math.Max(0, (nearest + LevelStopBufferPoints) - b.Close);

            // "excursion extreme": how far the CURRENT run beyond the nearest level has gone
            e.StopExcursionLongPts = e.StopLocalSwingLongPts;
            e.StopExcursionShortPts = e.StopLocalSwingShortPts;

            e.RunMfeLong = 0; e.RunMaeLong = 0;
            e.BarsToMfeLong = 0; e.BarsToMaeLong = 0;
            for (int i = 0; i < RGrid.Length; i++) { e.BarsToRLong[i] = -1; e.BarsToRShort[i] = -1; }
            return e;
        }

        private void UpdatePending(ResearchBar b)
        {
            for (int idx = 0; idx < pending.Count; idx++)
            {
                VectorEvent e = pending[idx];
                if (e.Complete) continue;
                e.BarsSeen++;

                double upPts = b.High - e.Close;      // favourable for a long
                double dnPts = e.Close - b.Low;       // favourable for a short
                if (upPts > e.RunMfeLong) { e.RunMfeLong = upPts; e.BarsToMfeLong = e.BarsSeen; }
                if (dnPts > e.RunMaeLong) { e.RunMaeLong = dnPts; e.BarsToMaeLong = e.BarsSeen; }

                for (int h = 0; h < Horizons.Length; h++)
                {
                    if (e.BarsSeen <= Horizons[h])
                    {
                        e.MfeLongAt[h] = e.RunMfeLong;
                        e.MaeLongAt[h] = e.RunMaeLong;
                        if (e.BarsSeen == Horizons[h]) e.NetAt[h] = b.Close - e.Close;
                    }
                }

                // R-race against the vector-wick stop, in BOTH directions, walking bars in
                // order so "reached +XR before -1R" is exact rather than inferred.
                double sl = e.StopVectorWickLongPts;
                if (sl > 0)
                {
                    if (e.BarToStopLong < 0 && b.Low <= e.Close - sl) e.BarToStopLong = e.BarsSeen;
                    for (int i = 0; i < RGrid.Length; i++)
                        if (e.BarsToRLong[i] < 0 && b.High >= e.Close + RGrid[i] * sl)
                            e.BarsToRLong[i] = e.BarsSeen;
                }
                double ss = e.StopVectorWickShortPts;
                if (ss > 0)
                {
                    if (e.BarToStopShort < 0 && b.High >= e.Close + ss) e.BarToStopShort = e.BarsSeen;
                    for (int i = 0; i < RGrid.Length; i++)
                        if (e.BarsToRShort[i] < 0 && b.Low <= e.Close - RGrid[i] * ss)
                            e.BarsToRShort[i] = e.BarsSeen;
                }

                if (e.BarsSeen >= MaxHorizon) e.Complete = true;
            }
        }

        private void FlushComplete()
        {
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                if (!pending[i].Complete) continue;
                if (writeRow != null) writeRow(ToCsv(pending[i]));
                EventsEmitted++;
                pending.RemoveAt(i);
            }
        }

        private void UpdateLevelState(ResearchBar b)
        {
            foreach (KeyLevelId id in Levels)
            {
                double lvl = levels.GetTriggerLevelPrice(id);
                if (double.IsNaN(lvl)) continue;
                bool touched = b.Low <= lvl && b.High >= lvl;
                if (touched) testsToday[id] = testsToday[id] + 1;
                bool above = b.Close > lvl;
                bool wasAbove = prevCloseAbove.ContainsKey(id) && prevCloseAbove[id];
                if (above != wasAbove) { consecutiveBeyond[id] = 1; brokenEarlierToday[id] = true; }
                else consecutiveBeyond[id] = consecutiveBeyond[id] + 1;
                prevCloseAbove[id] = above;
            }
        }

        // ---- feature helpers -------------------------------------------------
        private LevelInteraction Classify(ResearchBar b, double lvl)
        {
            if (double.IsNaN(lvl)) return LevelInteraction.NEVER_TOUCHED;
            bool openAbove = b.Open > lvl, closeAbove = b.Close > lvl;
            bool traded = b.Low <= lvl && b.High >= lvl;
            if (!traded)
            {
                double d = Math.Min(Math.Abs(b.High - lvl), Math.Abs(b.Low - lvl));
                return d <= ApproachBandPoints ? LevelInteraction.APPROACHED : LevelInteraction.NEVER_TOUCHED;
            }
            if (b.High == lvl || b.Low == lvl) if (openAbove == closeAbove) return LevelInteraction.FIRST_TOUCH;
            if (openAbove != closeAbove) return LevelInteraction.OPEN_ONE_SIDE_CLOSE_OTHER;
            // opened and closed the same side, but traded through -> a wick rejection
            return openAbove == closeAbove
                ? LevelInteraction.WICK_THROUGH_CLOSE_INSIDE
                : LevelInteraction.WICK_THROUGH_CLOSE_OUTSIDE;
        }

        private double Penetration(ResearchBar b, double lvl)
        {
            if (double.IsNaN(lvl)) return double.NaN;
            if (b.High >= lvl && b.Close <= lvl) return b.High - lvl;
            if (b.Low <= lvl && b.Close >= lvl) return lvl - b.Low;
            return 0;
        }

        private bool PriorOpposite(ResearchBar b, double lvl, KeyLevelId id)
        {
            if (double.IsNaN(lvl) || !prevCloseAbove.ContainsKey(id)) return false;
            bool nowAbove = b.Close > lvl;
            return prevCloseAbove[id] != nowAbove;
        }

        private LevelSequenceRole SequenceRole(ResearchBar b, double lvl, KeyLevelId id, LevelInteraction li)
        {
            if (double.IsNaN(lvl)) return LevelSequenceRole.NONE;
            bool broke = brokenEarlierToday.ContainsKey(id) && brokenEarlierToday[id];
            if (li == LevelInteraction.OPEN_ONE_SIDE_CLOSE_OTHER)
                return broke ? LevelSequenceRole.RECLAIM_AFTER_BREAK : LevelSequenceRole.FIRST_CANDLE_THROUGH;
            if (li == LevelInteraction.WICK_THROUGH_CLOSE_INSIDE)
                return broke ? LevelSequenceRole.RETEST_AFTER_BREAK : LevelSequenceRole.NONE;
            int run = consecutiveBeyond.ContainsKey(id) ? consecutiveBeyond[id] : 0;
            if (run >= 2) return LevelSequenceRole.CONTINUATION_THROUGH;
            return LevelSequenceRole.NONE;
        }

        private EmaRegime Regime(ResearchBar b, VectorEvent e)
        {
            if (double.IsNaN(e.Ema200)) return EmaRegime.UNKNOWN;
            bool crosses = b.Low <= e.Ema200 && b.High >= e.Ema200;
            bool openAbove = b.Open > e.Ema200, closeAbove = b.Close > e.Ema200;
            if (crosses && openAbove != closeAbove) return EmaRegime.CROSSING;
            if (crosses) return EmaRegime.TOUCHING;
            if (e.Ema200Slope == "RISING") return closeAbove ? EmaRegime.ABOVE_RISING : EmaRegime.BELOW_RISING;
            if (e.Ema200Slope == "FALLING") return closeAbove ? EmaRegime.ABOVE_FALLING : EmaRegime.BELOW_FALLING;
            return closeAbove ? EmaRegime.ABOVE_RISING : EmaRegime.BELOW_FALLING;
        }

        private double AtrProxy()
        {
            int n = window.Count;
            if (n < 2) return double.NaN;
            int from = Math.Max(1, n - AtrLookback);
            double sum = 0; int c = 0;
            for (int i = from; i < n; i++)
            {
                double tr = Math.Max(window[i].High - window[i].Low,
                            Math.Max(Math.Abs(window[i].High - window[i - 1].Close),
                                     Math.Abs(window[i].Low - window[i - 1].Close)));
                sum += tr; c++;
            }
            return c > 0 ? sum / c : double.NaN;
        }

        private double NearestLevel(double price)
        {
            double best = double.NaN, bestD = double.MaxValue;
            foreach (KeyLevelId id in Levels)
            {
                double lvl = levels.GetTriggerLevelPrice(id);
                if (double.IsNaN(lvl)) continue;
                double d = Math.Abs(price - lvl);
                if (d < bestD) { bestD = d; best = lvl; }
            }
            return best;
        }

        private static TimeBucket BucketOf(DateTime et)
        {
            int m = et.Hour * 60 + et.Minute;
            if (m < 570) return TimeBucket.PREMARKET;
            if (m < 600) return TimeBucket.T0930_1000;
            if (m < 630) return TimeBucket.T1000_1030;
            if (m < 660) return TimeBucket.T1030_1100;
            if (m <= 690) return TimeBucket.T1100_1130;
            return TimeBucket.AFTER_1130;
        }

        // ---- CSV -------------------------------------------------------------
        public static string CsvHeader()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("date,timeEt,timeframe,barIndex,vectorType,direction,open,high,low,close,volume,");
            sb.Append("rangePts,bodyPts,bodyPctOfRange,upperWickPts,lowerWickPts,");
            sb.Append("avgVol10,relVolume,volumeSpread,highestVolSpread10,volSpreadRatio,classificationTrigger,");
            sb.Append("ydayHigh,distYdayHigh,ydayLow,distYdayLow,lweekHigh,distLweekHigh,lweekLow,distLweekLow,");
            sb.Append("dailyOpen,distDailyOpen,vwap,ema9,ema200,distEma200,ema200SlopePts,ema200Slope,ema200Regime,");
            sb.Append("atrProxy,distEma200Atr,ema200Interaction,");
            foreach (KeyLevelId id in Levels)
                sb.Append(id + "_interaction," + id + "_seqRole," + id + "_penetrationPts," +
                          id + "_closeDist," + id + "_priorCloseOpposite," + id + "_testNumberToday,");
            sb.Append("prevVector,prevPrevVector,prevCandleKind,sameDirVectorRun,timeBucket,");
            sb.Append("stopVectorWickLongPts,stopVectorWickShortPts,stopLocalSwingLongPts,stopLocalSwingShortPts,");
            sb.Append("stopLevelBufferLongPts,stopLevelBufferShortPts,");
            foreach (int h in Horizons) sb.Append("mfeLong_" + h + ",maeLong_" + h + ",net_" + h + ",");
            sb.Append("barsToMfeLong,barsToMaeLong,barToStopLong,barToStopShort,");
            foreach (double r in RGrid) sb.Append("barToLong_" + r.ToString("0.##", CultureInfo.InvariantCulture) + "R,");
            foreach (double r in RGrid) sb.Append("barToShort_" + r.ToString("0.##", CultureInfo.InvariantCulture) + "R,");
            sb.Append("barsObserved");
            return sb.ToString();
        }

        private static string F(double v)
        {
            return double.IsNaN(v) ? "" : v.ToString("0.####", CultureInfo.InvariantCulture);
        }

        public static string ToCsv(VectorEvent e)
        {
            CultureInfo ci = CultureInfo.InvariantCulture;
            StringBuilder sb = new StringBuilder();
            sb.Append(e.EtClose.ToString("yyyy-MM-dd", ci)).Append(',');
            sb.Append(e.EtClose.ToString("HH:mm:ss", ci)).Append(',');
            sb.Append(e.TimeframeLabel).Append(',');
            sb.Append(e.BarIndex).Append(',').Append(e.Vector).Append(',').Append(e.Direction).Append(',');
            sb.Append(F(e.Open)).Append(',').Append(F(e.High)).Append(',').Append(F(e.Low)).Append(',')
              .Append(F(e.Close)).Append(',').Append(F(e.Volume)).Append(',');
            sb.Append(F(e.RangePts)).Append(',').Append(F(e.BodyPts)).Append(',').Append(F(e.BodyPctOfRange)).Append(',')
              .Append(F(e.UpperWickPts)).Append(',').Append(F(e.LowerWickPts)).Append(',');
            sb.Append(F(e.AvgVol10)).Append(',').Append(F(e.RelVolume)).Append(',').Append(F(e.VolumeSpread)).Append(',')
              .Append(F(e.HighestVolSpread10)).Append(',').Append(F(e.VolSpreadRatio)).Append(',')
              .Append(e.ClassificationTrigger).Append(',');
            sb.Append(F(e.YdayHigh)).Append(',').Append(F(e.DistYdayHigh)).Append(',')
              .Append(F(e.YdayLow)).Append(',').Append(F(e.DistYdayLow)).Append(',')
              .Append(F(e.LweekHigh)).Append(',').Append(F(e.DistLweekHigh)).Append(',')
              .Append(F(e.LweekLow)).Append(',').Append(F(e.DistLweekLow)).Append(',');
            sb.Append(F(e.DailyOpen)).Append(',').Append(F(e.DistDailyOpen)).Append(',').Append(F(e.Vwap)).Append(',')
              .Append(F(e.Ema9)).Append(',').Append(F(e.Ema200)).Append(',').Append(F(e.DistEma200)).Append(',')
              .Append(F(e.Ema200SlopePts)).Append(',').Append(e.Ema200Slope).Append(',').Append(e.Ema200Regime).Append(',');
            sb.Append(F(e.AtrProxy)).Append(',').Append(F(e.DistEma200Atr)).Append(',').Append(e.Ema200Interaction).Append(',');
            foreach (KeyLevelId id in Levels)
            {
                sb.Append(e.Interaction[id]).Append(',').Append(e.SeqRole[id]).Append(',')
                  .Append(F(e.PenetrationPts[id])).Append(',').Append(F(e.CloseDistFromLevel[id])).Append(',')
                  .Append(e.PriorCloseOppositeSide[id] ? "1" : "0").Append(',').Append(e.TestNumberToday[id]).Append(',');
            }
            sb.Append(e.PrevVector).Append(',').Append(e.PrevPrevVector).Append(',').Append(e.PrevCandleKind).Append(',')
              .Append(e.SameDirectionVectorRun).Append(',').Append(e.Bucket).Append(',');
            sb.Append(F(e.StopVectorWickLongPts)).Append(',').Append(F(e.StopVectorWickShortPts)).Append(',')
              .Append(F(e.StopLocalSwingLongPts)).Append(',').Append(F(e.StopLocalSwingShortPts)).Append(',')
              .Append(F(e.StopLevelBufferLongPts)).Append(',').Append(F(e.StopLevelBufferShortPts)).Append(',');
            for (int h = 0; h < Horizons.Length; h++)
                sb.Append(F(e.MfeLongAt[h])).Append(',').Append(F(e.MaeLongAt[h])).Append(',').Append(F(e.NetAt[h])).Append(',');
            sb.Append(e.BarsToMfeLong).Append(',').Append(e.BarsToMaeLong).Append(',')
              .Append(e.BarToStopLong).Append(',').Append(e.BarToStopShort).Append(',');
            for (int i = 0; i < RGrid.Length; i++) sb.Append(e.BarsToRLong[i]).Append(',');
            for (int i = 0; i < RGrid.Length; i++) sb.Append(e.BarsToRShort[i]).Append(',');
            sb.Append(e.BarsSeen);
            return sb.ToString();
        }
    }
}
