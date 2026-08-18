// ============================================================================
// V4StructureEngine.cs
//
// RESEARCH MODULE - SUBMITS NO ORDERS, EVER.
//
// V4: MULTI-TIMEFRAME MARKET STRUCTURE.
//
// This is a NEW research programme, deliberately kept in its own namespace and
// its own files. It does not import, extend or reuse the V3 price-action
// capture. V3 remains a clean test of the information set it was built on.
//
// WHAT THIS ENGINE IS FOR
//   The research brief's most important sentence is the last one:
//
//     "Does this structural event contain genuinely useful predictive
//      information BEFORE the trade, or are we merely describing price
//      movement after it already occurred?"
//
//   Almost every market-structure claim is easy to make on a finished chart.
//   The only way to keep the question honest is to separate, in the data
//   itself, what was KNOWABLE at the moment the structure break completed from
//   what happened AFTERWARDS. This engine therefore splits every row into:
//
//     FEATURES  frozen at the close of the bar that made the break knowable,
//               computed only from bars that had already closed by then.
//     LABELS    filled in exclusively from bars that arrived later.
//
//   A row is not written until its full forward horizon has elapsed. Nothing
//   in the feature block can be contaminated by the label block, because the
//   feature block is sealed before the first label bar is seen.
//
// WHY LABELS ARE MEASURED IN MINUTES
//   Structure is tracked on Daily / 4H / 60m / 15m / 5m / 3m / 1m. If forward
//   returns were measured in BARS of the event's own timeframe, a "20-bar"
//   outcome would mean 20 minutes on 1m and two months on Daily, and no
//   timeframe could be compared against another. Every forward label here is
//   measured on the 1-MINUTE stream, in MINUTES from the instant the break
//   became knowable. That is exactly the brief's question: "at the exact
//   moment the structure break becomes knowable, what happens over the next 5,
//   15, 30, 60 minutes?"
//
// NO-LOOKAHEAD CONTRACT
//   - A swing pivot is published only after ConfirmBars bars have closed to
//     its right. It carries KnownAtEt and is refused before it.
//   - Every cross-timeframe read is gated one second BEFORE the consuming
//     bar's close. Gating on the close would admit a swing confirmed at the
//     very same instant - including, on the event's own timeframe, one the
//     event bar itself confirmed, so a bar could break a level it created.
//   - Structure states of other timeframes are snapshotted at that same
//     instant, so the alignment recorded is the alignment a live system had,
//     and is independent of the order NinjaTrader delivers equal-timestamp
//     series in.
//   - Candidate stops come from information available at event time. R is
//     never manufactured by choosing a stop after seeing the outcome.
//
// NO VECTOR CANDLES. No PVSRA, no candle colour classification of any kind,
// not as a feature, a filter, a context variable or an explanation.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// One completed bar of any timeframe, as V4 sees it.
    public struct V4Bar
    {
        public DateTime EtOpen, EtClose;
        public double Open, High, Low, Close, Volume;
    }

    public enum V4SwingKind { HIGH, LOW }

    /// How a confirmed swing compares to the previous confirmed swing of the
    /// same kind. This is the HH / HL / LH / LL vocabulary, made mechanical.
    public enum V4SwingLabel { UNKNOWN, HH, LH, EQUAL_HIGH, HL, LL, EQUAL_LOW }

    /// Direction, used for alignment arithmetic. NONE is a real answer, not a
    /// missing value: a range has no direction.
    public enum V4Dir { NONE, UP, DOWN }

    /// Structure state of ONE timeframe, derived only from the labels of the
    /// last confirmed swing high and the last confirmed swing low.
    ///
    ///   HH + HL -> BULLISH
    ///   LH + LL -> BEARISH
    ///   LH + HL -> RANGE_CONTRACTING   (inside bars of structure: coiling)
    ///   HH + LL -> RANGE_EXPANDING     (broadening: both extremes extending)
    ///
    /// Nothing subjective enters this. Two researchers with the same bars and
    /// the same ConfirmBars/PivotLeftBars get the same states.
    public enum V4StructureState
    {
        UNKNOWN, BULLISH, BEARISH, RANGE_CONTRACTING, RANGE_EXPANDING
    }

    /// A confirmed swing point together with the instant it became knowable.
    public struct V4Swing
    {
        public bool Valid;
        public V4SwingKind Kind;
        public double Price;
        public DateTime FormedAtEt;   // close time of the pivot bar itself
        public DateTime KnownAtEt;    // close time of the bar that confirmed it
        public V4SwingLabel Label;
    }

    /// What the bar that touched a prior structural level actually did, judged
    /// ONLY from that bar. Every value here is knowable at the bar's close.
    ///
    /// The brief lists eight break outcomes. Five of them are properties of the
    /// break bar and belong here. The other three - immediately rejected,
    /// accepted beyond, retested - can only be known later, so they live in
    /// V4FollowState and are LABELS, not features. Keeping them apart is the
    /// whole point of the exercise.
    public enum V4BreakOutcome
    {
        NO_TOUCH,                    // never reached the level
        APPROACHED,                  // came inside the approach band, no trade through
        TOUCHED,                     // touched exactly, no penetration
        WICKED_BEYOND,               // poked through by less than the wick threshold, closed back
        TRADED_BEYOND_NO_CLOSE,      // traded meaningfully beyond, still closed back
        CLOSED_BEYOND_WEAK,          // closed beyond, without displacement
        CLOSED_BEYOND_DISPLACEMENT   // closed beyond with displacement
    }

    /// What happened AFTER the break. Resolved from later bars only. This is a
    /// LABEL. It must never be used as an input to anything.
    public enum V4FollowState
    {
        UNRESOLVED,
        IMMEDIATE_REJECTION,     // closed back on the original side almost at once
        FAILED_BREAK,            // closed back and was still back at the end of the window
        ACCEPTED_NO_RETEST,      // stayed beyond, never came back to the level
        ACCEPTED_RETEST_HELD,    // came back to the level, held it, extended again
        RETEST_FAILED,           // came back to the level and closed through it
        DRIFT                    // beyond the level but with no acceptance and no failure
    }

    /// Agreement of the higher timeframes with the direction of the event.
    public enum V4Alignment
    {
        UNKNOWN, FULLY_ALIGNED, PARTIALLY_ALIGNED, CONFLICTING, TRANSITIONING
    }

    /// A simple mean-of-true-range over completed bars. No smoothing state that
    /// could survive a gap, so it is reproducible from any starting point.
    public class V4Atr
    {
        private readonly int period;
        private readonly List<double> tr = new List<double>();
        private double prevClose = double.NaN;

        public V4Atr(int p) { period = p; }

        public void Add(V4Bar b)
        {
            double t = b.High - b.Low;
            if (!double.IsNaN(prevClose))
            {
                double a = Math.Abs(b.High - prevClose);
                double c = Math.Abs(b.Low - prevClose);
                if (a > t) t = a;
                if (c > t) t = c;
            }
            prevClose = b.Close;
            tr.Add(t);
            if (tr.Count > period) tr.RemoveAt(0);
        }

        public bool Ready { get { return tr.Count >= period; } }

        public double Value
        {
            get
            {
                if (tr.Count < period) return double.NaN;
                double s = 0;
                for (int i = 0; i < tr.Count; i++) s += tr[i];
                return s / tr.Count;
            }
        }
    }

    // ========================================================================
    /// Mechanical swing structure for ONE timeframe.
    ///
    /// Feed it completed bars of that timeframe, in order, and it maintains:
    ///   - confirmed swing highs and lows, each with a KnownAtEt
    ///   - the HH / HL / LH / LL label of each
    ///   - the structure state implied by the last high and last low
    ///   - the current structural range
    ///   - compression and expansion measures
    ///
    /// It holds no strategy state and submits no orders.
    // ========================================================================
    public class V4StructureTracker
    {
        public readonly string Label;              // "1m", "3m", "15m", "60m", "4h", "1d"
        public readonly int MinutesPerBar;         // used only to report label horizons

        /// Bars required to the RIGHT of a pivot before it may be published.
        /// This is the single most important robustness knob in V4 - the brief
        /// demands that any edge survive "nearby swing-definition parameters",
        /// so it is a parameter and never a constant.
        public int ConfirmBars = 2;
        /// Bars to the LEFT the pivot must strictly exceed.
        public int PivotLeftBars = 2;
        /// Bars used for the ATR that scales everything on this timeframe.
        public int AtrPeriod = 20;
        /// Window for the compression measure.
        public int CompressionLookback = 10;
        /// Fast/slow windows for the expansion measure.
        public int ExpansionFast = 5;
        /// Two confirmed swings within this fraction of ATR count as EQUAL
        /// rather than as a higher high or a lower low. Without it, a one-tick
        /// difference is treated as a structural event, which is noise.
        public double EqualityBandAtr = 0.10;

        private readonly List<V4Bar> bars = new List<V4Bar>();
        private readonly List<V4Swing> highs = new List<V4Swing>();
        private readonly List<V4Swing> lows = new List<V4Swing>();
        // Built on the FIRST bar, not in the constructor.
        //
        // These used to be constructed eagerly, which read AtrPeriod and
        // ExpansionFast before the caller had set them - so a host that
        // configured AtrPeriod after construction got the default 20 and never
        // knew. On short timeframes that silently delayed the point at which
        // any event could be recorded at all. Deferring construction to the
        // first bar makes the configured value the one that is actually used.
        private V4Atr atr;
        private V4Atr atrFast;

        /// State transitions, each stamped with when the state became knowable.
        private V4StructureState state = V4StructureState.UNKNOWN;
        private DateTime stateSinceEt = DateTime.MinValue;
        private DateTime lastBarCloseEt = DateTime.MinValue;
        private long barCount;

        public V4StructureTracker(string label, int minutesPerBar)
        {
            Label = label;
            MinutesPerBar = minutesPerBar;
        }

        private void EnsureAtr()
        {
            if (atr == null) { atr = new V4Atr(AtrPeriod); atrFast = new V4Atr(ExpansionFast); }
        }

        public long BarCount { get { return barCount; } }
        public int SwingHighCount { get { return highs.Count; } }
        public int SwingLowCount { get { return lows.Count; } }
        public DateTime LastBarCloseEt { get { return lastBarCloseEt; } }

        // -- feed ------------------------------------------------------------

        /// Feed one COMPLETED bar of this timeframe, in order.
        public void OnBar(V4Bar b)
        {
            EnsureAtr();
            barCount++;
            bars.Add(b);
            if (bars.Count > 600) bars.RemoveAt(0);
            atr.Add(b);
            atrFast.Add(b);
            lastBarCloseEt = b.EtClose;

            // The candidate pivot sits ConfirmBars back from the bar just closed.
            int ci = bars.Count - 1 - ConfirmBars;
            if (ci < PivotLeftBars) return;
            V4Bar c = bars[ci];

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

            // KnownAtEt is the close of the bar that COMPLETED the confirmation,
            // which is the bar just fed in - never the pivot bar's own time.
            if (isHigh) Publish(V4SwingKind.HIGH, c.High, c.EtClose, b.EtClose);
            if (isLow) Publish(V4SwingKind.LOW, c.Low, c.EtClose, b.EtClose);
            if (isHigh || isLow) Recompute(b.EtClose);
        }

        private void Publish(V4SwingKind kind, double price, DateTime formed, DateTime known)
        {
            List<V4Swing> src = kind == V4SwingKind.HIGH ? highs : lows;
            V4Swing s = new V4Swing();
            s.Valid = true; s.Kind = kind; s.Price = price;
            s.FormedAtEt = formed; s.KnownAtEt = known;
            s.Label = LabelAgainstPrevious(src, kind, price);
            src.Add(s);
            if (src.Count > 200) src.RemoveAt(0);
        }

        private V4SwingLabel LabelAgainstPrevious(List<V4Swing> src, V4SwingKind kind, double price)
        {
            if (src.Count == 0) return V4SwingLabel.UNKNOWN;
            double prev = src[src.Count - 1].Price;
            double a = atr == null ? double.NaN : atr.Value;
            double band = double.IsNaN(a) ? 0 : a * EqualityBandAtr;
            double d = price - prev;
            if (Math.Abs(d) <= band)
                return kind == V4SwingKind.HIGH ? V4SwingLabel.EQUAL_HIGH : V4SwingLabel.EQUAL_LOW;
            if (kind == V4SwingKind.HIGH) return d > 0 ? V4SwingLabel.HH : V4SwingLabel.LH;
            return d > 0 ? V4SwingLabel.HL : V4SwingLabel.LL;
        }

        /// Structure state from the labels of the most recent confirmed high and
        /// low. EQUAL_* is treated as "not a new extreme in either direction",
        /// which keeps the four-way table total.
        private void Recompute(DateTime knownAt)
        {
            V4StructureState next = V4StructureState.UNKNOWN;
            if (highs.Count > 0 && lows.Count > 0)
            {
                V4SwingLabel h = highs[highs.Count - 1].Label;
                V4SwingLabel l = lows[lows.Count - 1].Label;
                bool higherHigh = h == V4SwingLabel.HH;
                bool lowerHigh = h == V4SwingLabel.LH;
                bool higherLow = l == V4SwingLabel.HL;
                bool lowerLow = l == V4SwingLabel.LL;

                if (higherHigh && higherLow) next = V4StructureState.BULLISH;
                else if (lowerHigh && lowerLow) next = V4StructureState.BEARISH;
                else if (lowerHigh && higherLow) next = V4StructureState.RANGE_CONTRACTING;
                else if (higherHigh && lowerLow) next = V4StructureState.RANGE_EXPANDING;
                else next = state;   // an EQUAL swing does not by itself change the state
            }
            if (next != state)
            {
                state = next;
                stateSinceEt = knownAt;
            }
        }

        // -- queries (all gated on the CONSUMER's decision time) --------------

        /// The structure state that was already knowable at cutoffEt. Refusing a
        /// state stamped later than the cutoff is what makes cross-timeframe
        /// alignment honest rather than retrospective.
        public V4StructureState StateKnownAt(DateTime cutoffEt)
        {
            return stateSinceEt != DateTime.MinValue && stateSinceEt <= cutoffEt
                ? state : V4StructureState.UNKNOWN;
        }

        public DateTime StateSinceEt { get { return stateSinceEt; } }

        /// Minutes the current state has been in force as of cutoffEt, or -1.
        public int MinutesInStateAt(DateTime cutoffEt)
        {
            if (stateSinceEt == DateTime.MinValue || stateSinceEt > cutoffEt) return -1;
            return (int)(cutoffEt - stateSinceEt).TotalMinutes;
        }

        public static V4Dir DirOf(V4StructureState s)
        {
            if (s == V4StructureState.BULLISH) return V4Dir.UP;
            if (s == V4StructureState.BEARISH) return V4Dir.DOWN;
            return V4Dir.NONE;
        }

        public V4Swing SwingHighKnownAt(DateTime cutoffEt) { return Latest(highs, cutoffEt, 0); }
        public V4Swing SwingLowKnownAt(DateTime cutoffEt) { return Latest(lows, cutoffEt, 0); }
        /// The swing one before the most recent - the other side of "higher high".
        public V4Swing PriorSwingHighKnownAt(DateTime cutoffEt) { return Latest(highs, cutoffEt, 1); }
        public V4Swing PriorSwingLowKnownAt(DateTime cutoffEt) { return Latest(lows, cutoffEt, 1); }

        private static V4Swing Latest(List<V4Swing> src, DateTime cutoffEt, int back)
        {
            int seen = 0;
            for (int i = src.Count - 1; i >= 0; i--)
            {
                if (src[i].KnownAtEt > cutoffEt) continue;
                if (seen == back) return src[i];
                seen++;
            }
            return new V4Swing();   // Valid == false
        }

        public double AtrValue { get { return atr == null ? double.NaN : atr.Value; } }
        public bool AtrReady { get { return atr != null && atr.Ready; } }

        /// Range between the most recent confirmed swing high and swing low that
        /// were both knowable at cutoffEt. NaN when structure is not yet formed.
        public double RangePtsKnownAt(DateTime cutoffEt)
        {
            V4Swing h = SwingHighKnownAt(cutoffEt), l = SwingLowKnownAt(cutoffEt);
            if (!h.Valid || !l.Valid) return double.NaN;
            return h.Price - l.Price;
        }

        /// Where a price sits inside that range, 0 = swing low, 100 = swing high.
        public double PosInRangeKnownAt(DateTime cutoffEt, double price)
        {
            V4Swing h = SwingHighKnownAt(cutoffEt), l = SwingLowKnownAt(cutoffEt);
            if (!h.Valid || !l.Valid || h.Price <= l.Price) return double.NaN;
            return 100.0 * (price - l.Price) / (h.Price - l.Price);
        }

        /// Range of the last CompressionLookback bars divided by ATR. Low values
        /// mean coiled, high values mean already expanding.
        public double CompressionRatio()
        {
            double a = AtrValue;
            if (double.IsNaN(a) || a <= 0 || bars.Count < CompressionLookback) return double.NaN;
            double hi = double.MinValue, lo = double.MaxValue;
            for (int i = bars.Count - CompressionLookback; i < bars.Count; i++)
            {
                if (bars[i].High > hi) hi = bars[i].High;
                if (bars[i].Low < lo) lo = bars[i].Low;
            }
            return (hi - lo) / a;
        }

        /// Fast ATR over slow ATR. Above 1 means volatility is expanding right
        /// now relative to its own recent norm.
        public double ExpansionRatio()
        {
            double a = AtrValue, f = atrFast == null ? double.NaN : atrFast.Value;
            if (double.IsNaN(a) || double.IsNaN(f) || a <= 0) return double.NaN;
            return f / a;
        }

        /// Volume of the newest bar divided by the mean of the 20 before it.
        /// The divisor excludes the newest bar, so a high-volume bar cannot
        /// deflate its own reading.
        public double RelVolume()
        {
            int n = bars.Count;
            if (n < 21) return double.NaN;
            double s = 0;
            for (int i = n - 21; i < n - 1; i++) s += bars[i].Volume;
            double avg = s / 20.0;
            return avg > 0 ? bars[n - 1].Volume / avg : double.NaN;
        }

        /// Highest high / lowest low of the last n COMPLETED bars, excluding the
        /// most recent one. Used for structural stops, so the bar that triggered
        /// an event cannot supply its own stop.
        public bool PriorExtremes(int n, out double hi, out double lo)
        {
            hi = double.NaN; lo = double.NaN;
            int end = bars.Count - 1;                 // exclude the newest bar
            int start = end - n;
            if (start < 0) start = 0;
            if (end <= start) return false;
            hi = double.MinValue; lo = double.MaxValue;
            for (int i = start; i < end; i++)
            {
                if (bars[i].High > hi) hi = bars[i].High;
                if (bars[i].Low < lo) lo = bars[i].Low;
            }
            return true;
        }
    }

    // ========================================================================
    /// Classification of ONE bar against ONE prior structural level.
    ///
    /// Pure function of the bar and the level. Deterministic, testable, and
    /// with no access to anything that happened afterwards.
    // ========================================================================
    public static class V4BreakClassifier
    {
        /// dir = +1 when the level is a prior HIGH being challenged from below,
        ///       -1 when the level is a prior LOW being challenged from above.
        ///
        /// approachBandAtr - inside this many ATR of the level counts as APPROACHED
        /// wickMaxAtr      - penetration up to this many ATR, closing back, is a wick
        /// dispBodyAtr     - body of at least this many ATR is displacement
        /// dispCloseAtr    - AND the close must be at least this many ATR beyond
        public static V4BreakOutcome Classify(V4Bar b, double level, int dir, double atr,
                                              double approachBandAtr, double wickMaxAtr,
                                              double dispBodyAtr, double dispCloseAtr)
        {
            if (double.IsNaN(level) || double.IsNaN(atr) || atr <= 0) return V4BreakOutcome.NO_TOUCH;

            double extreme = dir > 0 ? b.High : b.Low;
            double beyond = dir > 0 ? extreme - level : level - extreme;      // penetration
            double closeBeyond = dir > 0 ? b.Close - level : level - b.Close;

            if (beyond < 0)
                return (-beyond) <= approachBandAtr * atr ? V4BreakOutcome.APPROACHED : V4BreakOutcome.NO_TOUCH;
            if (beyond == 0 && closeBeyond <= 0) return V4BreakOutcome.TOUCHED;

            if (closeBeyond <= 0)
                return beyond <= wickMaxAtr * atr
                    ? V4BreakOutcome.WICKED_BEYOND
                    : V4BreakOutcome.TRADED_BEYOND_NO_CLOSE;

            double body = Math.Abs(b.Close - b.Open);
            bool displaced = body >= dispBodyAtr * atr && closeBeyond >= dispCloseAtr * atr;
            return displaced ? V4BreakOutcome.CLOSED_BEYOND_DISPLACEMENT : V4BreakOutcome.CLOSED_BEYOND_WEAK;
        }

        /// TRUE for the two outcomes that mean price actually closed through.
        public static bool IsCloseThrough(V4BreakOutcome o)
        {
            return o == V4BreakOutcome.CLOSED_BEYOND_WEAK || o == V4BreakOutcome.CLOSED_BEYOND_DISPLACEMENT;
        }

        /// TRUE for the two outcomes that traded through without closing through.
        public static bool IsWickThrough(V4BreakOutcome o)
        {
            return o == V4BreakOutcome.WICKED_BEYOND || o == V4BreakOutcome.TRADED_BEYOND_NO_CLOSE;
        }

        /// TRUE for anything that penetrated the level at all.
        public static bool IsAnyBreak(V4BreakOutcome o)
        {
            return IsCloseThrough(o) || IsWickThrough(o);
        }
    }
}
