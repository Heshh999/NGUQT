// ======================================================================
// V4LevelContext.cs  -  MNQ V4.1
// ======================================================================
// The level / location layer the prompt asks not to throw away: what
// levels exist, which one price is nearest, how price is interacting with
// it, what sequence of interactions has already happened, and how many
// DISTINCT tests that makes today.
//
// THIS FILE SUBMITS NO ORDERS.
//
// The hard part here is not the vocabulary, it is the clustering. A ten
// bar chop sitting on a level is one test, not ten. Counting it as ten
// would inflate every "repeat test" statistic by an order of magnitude
// and would do it silently. So a test opens when price first interacts,
// and does not close until price has been clear of the level by
// ClusterExitAtr for ClusterGapBars consecutive bars. Only then can a new
// test begin.
//
// Everything is causal. A level enters the book at the moment it becomes
// knowable and carries that timestamp; queries take a cutoff and refuse
// anything published later.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// What kind of thing the level is. Kept separate from its name so the
    /// research layer can group by type without string parsing.
    public enum V4LevelType
    {
        UNKNOWN,
        PRIOR_DAY_HIGH, PRIOR_DAY_LOW,
        PRIOR_WEEK_HIGH, PRIOR_WEEK_LOW,
        DAILY_OPEN,
        PREMARKET_HIGH, PREMARKET_LOW,
        OPENING_RANGE_HIGH, OPENING_RANGE_LOW,
        SESSION_HIGH, SESSION_LOW,
        SESSION_VWAP, VWAP_BAND_UP, VWAP_BAND_DOWN,
        SWING_HIGH, SWING_LOW,
        VECTOR_ZONE,
        PROFILE_POC, PROFILE_VAH, PROFILE_VAL, PROFILE_HVN, PROFILE_LVN
    }

    /// How price is interacting with the nearest meaningful level, judged
    /// only from the completed bar and what came before it.
    ///
    ///   APPROACHING_*   : inside the approach band, never traded through
    ///   TOUCH           : the bar's range reached the level exactly
    ///   WICK_THROUGH    : traded through, closed back on the original side
    ///   BREAK_CLOSE     : closed through the level
    ///   RECLAIM         : closed back through, having previously closed beyond
    ///   REJECTION       : traded through and closed back beyond the approach band
    ///   ACCEPTED_ABOVE  : closed above for AcceptanceBars consecutive bars
    ///   ACCEPTED_BELOW  : mirror
    ///   RETEST_FROM_*   : came back to the level after a break, from the new side
    ///   NO_INTERACTION  : outside the approach band
    public enum V4Interaction
    {
        NO_INTERACTION,
        APPROACHING_FROM_BELOW, APPROACHING_FROM_ABOVE,
        TOUCH, WICK_THROUGH, BREAK_CLOSE, RECLAIM, REJECTION,
        ACCEPTED_ABOVE, ACCEPTED_BELOW,
        RETEST_FROM_ABOVE, RETEST_FROM_BELOW
    }

    /// The causal sequence of interactions with the SAME level. Never uses
    /// anything the future would be needed to know.
    public enum V4SeqState
    {
        NONE,
        FIRST_APPROACH, FIRST_BREAK, FIRST_RECLAIM, FIRST_RETEST,
        SECOND_TEST, REPEATED_TEST,
        BREAK_THEN_RECLAIM, RECLAIM_THEN_RETEST,
        ACCEPTANCE_SEQUENCE, FAILURE_SEQUENCE
    }

    /// One tracked level plus its causal interaction history for the
    /// current exchange day.
    public class V4LevelRef
    {
        public string Name = "";
        public V4LevelType Type = V4LevelType.UNKNOWN;
        public double Price = double.NaN;
        public DateTime FormedEt = DateTime.MinValue;
        public DateTime KnownEt = DateTime.MinValue;

        // per-exchange-day causal state
        public int TestNumberToday;
        public int InteractionCountSession;
        public DateTime LastInteractionEt = DateTime.MinValue;
        public V4SeqState Seq = V4SeqState.NONE;
        public V4Interaction LastInteraction = V4Interaction.NO_INTERACTION;

        public bool EverClosedAbove, EverClosedBelow;
        public bool Crossed, Reclaimed, AcceptedBeyond, RejectedFrom;
        public int ConsecutiveBeyondBars;
        public int SideOfLevel;                 // +1 price above, -1 below, 0 straddling

        // clustering bookkeeping
        internal bool TestOpen;
        internal int BarsClearOfLevel;

        public void ResetForNewDay()
        {
            TestNumberToday = 0; InteractionCountSession = 0;
            LastInteractionEt = DateTime.MinValue;
            Seq = V4SeqState.NONE; LastInteraction = V4Interaction.NO_INTERACTION;
            EverClosedAbove = EverClosedBelow = false;
            Crossed = Reclaimed = AcceptedBeyond = RejectedFrom = false;
            ConsecutiveBeyondBars = 0; TestOpen = false; BarsClearOfLevel = 0;
        }
    }

    /// Holds the level book and drives the interaction state machine.
    public class V4LevelContextBook
    {
        /// Inside this many ATR of a level counts as "approaching".
        public double ApproachBandAtr = 0.35;
        /// Clear of the level by this much, for ClusterGapBars bars, closes a test.
        public double ClusterExitAtr = 0.50;
        public int ClusterGapBars = 3;
        /// Consecutive closes beyond that constitute acceptance.
        public int AcceptanceBars = 3;

        private readonly Dictionary<string, V4LevelRef> book = new Dictionary<string, V4LevelRef>();
        private int currentDayKey = int.MinValue;

        public DateTime AsOfEt = DateTime.MinValue;

        public IEnumerable<V4LevelRef> Levels { get { return book.Values; } }
        public int Count { get { return book.Count; } }

        /// Publish or update a level. KnownEt is when it became knowable and
        /// is what queries filter on - not FormedEt, which can be earlier.
        public void Publish(string name, V4LevelType type, double price,
                            DateTime formedEt, DateTime knownEt)
        {
            if (!V4Num.Ok(price)) return;
            V4LevelRef r;
            if (!book.TryGetValue(name, out r))
            {
                r = new V4LevelRef();
                r.Name = name; r.Type = type;
                book[name] = r;
            }
            // a moved level is a different level: its interaction history
            // no longer describes the price now being tracked
            if (V4Num.Ok(r.Price) && Math.Abs(r.Price - price) > 1e-9) r.ResetForNewDay();
            r.Price = price; r.Type = type;
            r.FormedEt = formedEt; r.KnownEt = knownEt;
        }

        public void Remove(string name) { if (book.ContainsKey(name)) book.Remove(name); }

        /// Fold one completed bar in and advance every level's state.
        public void OnBar(V4Bar b, double atr, int exchangeDayKey)
        {
            AsOfEt = b.EtClose;

            if (exchangeDayKey != currentDayKey)
            {
                currentDayKey = exchangeDayKey;
                foreach (KeyValuePair<string, V4LevelRef> kv in book) kv.Value.ResetForNewDay();
            }

            if (!V4Num.Ok(atr) || atr <= 0) return;
            double band = ApproachBandAtr * atr;
            double clear = ClusterExitAtr * atr;

            foreach (KeyValuePair<string, V4LevelRef> kv in book)
            {
                V4LevelRef r = kv.Value;
                if (!V4Num.Ok(r.Price) || r.KnownEt > b.EtClose) continue;
                Advance(r, b, band, clear);
            }
        }

        private void Advance(V4LevelRef r, V4Bar b, double band, double clear)
        {
            double lvl = r.Price;
            bool through = b.High > lvl && b.Low < lvl;
            bool touched = (b.High >= lvl && b.Low <= lvl);
            bool closedAbove = b.Close > lvl;
            bool closedBelow = b.Close < lvl;
            double dist = Math.Min(Math.Abs(b.High - lvl), Math.Abs(b.Low - lvl));
            bool near = touched || dist <= band;

            r.SideOfLevel = touched ? 0 : (b.Close > lvl ? 1 : -1);

            // ---- clustering: does this bar belong to an open test? -----
            if (near)
            {
                r.BarsClearOfLevel = 0;
                if (!r.TestOpen)
                {
                    r.TestOpen = true;
                    r.TestNumberToday++;
                }
                r.InteractionCountSession++;
                r.LastInteractionEt = b.EtClose;
            }
            else
            {
                double away = Math.Min(Math.Abs(b.Low - lvl), Math.Abs(b.High - lvl));
                if (away >= clear)
                {
                    r.BarsClearOfLevel++;
                    if (r.TestOpen && r.BarsClearOfLevel >= ClusterGapBars) r.TestOpen = false;
                }
                r.LastInteraction = V4Interaction.NO_INTERACTION;
                if (!r.TestOpen) return;
            }

            // ---- interaction --------------------------------------------
            V4Interaction it;
            bool priorAbove = r.EverClosedAbove, priorBelow = r.EverClosedBelow;

            if (!near) it = V4Interaction.NO_INTERACTION;
            else if (through && closedAbove && priorBelow) it = V4Interaction.RECLAIM;
            else if (through && closedBelow && priorAbove) it = V4Interaction.RECLAIM;
            else if (through && (closedAbove || closedBelow))
            {
                bool cameFromBelow = V4Num.Ok(b.Open) && b.Open < lvl;
                bool closedBack = (cameFromBelow && closedBelow) || (!cameFromBelow && closedAbove);
                if (closedBack) it = Math.Abs(b.Close - lvl) > band ? V4Interaction.REJECTION : V4Interaction.WICK_THROUGH;
                else it = V4Interaction.BREAK_CLOSE;
            }
            else if (touched) it = V4Interaction.TOUCH;
            else it = b.Close < lvl ? V4Interaction.APPROACHING_FROM_BELOW : V4Interaction.APPROACHING_FROM_ABOVE;

            // acceptance: consecutive closes on one side
            if (closedAbove && priorBelow) r.ConsecutiveBeyondBars = 1;
            else if (closedBelow && priorAbove) r.ConsecutiveBeyondBars = 1;
            else if (it == V4Interaction.BREAK_CLOSE) r.ConsecutiveBeyondBars = 1;
            else if (r.ConsecutiveBeyondBars > 0 && (closedAbove || closedBelow)) r.ConsecutiveBeyondBars++;

            if (r.ConsecutiveBeyondBars >= AcceptanceBars)
            {
                it = closedAbove ? V4Interaction.ACCEPTED_ABOVE : V4Interaction.ACCEPTED_BELOW;
                r.AcceptedBeyond = true;
            }

            // retest: back at the level after having broken it
            if (near && r.Crossed && it == V4Interaction.TOUCH)
                it = closedAbove ? V4Interaction.RETEST_FROM_ABOVE : V4Interaction.RETEST_FROM_BELOW;

            if (through) r.Crossed = true;
            if (it == V4Interaction.RECLAIM) r.Reclaimed = true;
            if (it == V4Interaction.REJECTION) r.RejectedFrom = true;
            if (closedAbove) r.EverClosedAbove = true;
            if (closedBelow) r.EverClosedBelow = true;

            r.LastInteraction = it;
            r.Seq = NextSeq(r, it);
        }

        /// Sequence transitions. Ordered so that an earlier, more specific
        /// state is not overwritten by a later generic one.
        private static V4SeqState NextSeq(V4LevelRef r, V4Interaction it)
        {
            V4SeqState s = r.Seq;
            switch (it)
            {
                case V4Interaction.APPROACHING_FROM_ABOVE:
                case V4Interaction.APPROACHING_FROM_BELOW:
                case V4Interaction.TOUCH:
                    if (s == V4SeqState.NONE) return V4SeqState.FIRST_APPROACH;
                    if (r.TestNumberToday == 2) return V4SeqState.SECOND_TEST;
                    if (r.TestNumberToday > 2) return V4SeqState.REPEATED_TEST;
                    return s;

                case V4Interaction.BREAK_CLOSE:
                    return s == V4SeqState.NONE || s == V4SeqState.FIRST_APPROACH
                        ? V4SeqState.FIRST_BREAK : s;

                case V4Interaction.RECLAIM:
                    if (s == V4SeqState.FIRST_BREAK) return V4SeqState.BREAK_THEN_RECLAIM;
                    return s == V4SeqState.NONE ? V4SeqState.FIRST_RECLAIM : s;

                case V4Interaction.RETEST_FROM_ABOVE:
                case V4Interaction.RETEST_FROM_BELOW:
                    if (s == V4SeqState.BREAK_THEN_RECLAIM || s == V4SeqState.FIRST_RECLAIM)
                        return V4SeqState.RECLAIM_THEN_RETEST;
                    return V4SeqState.FIRST_RETEST;

                case V4Interaction.ACCEPTED_ABOVE:
                case V4Interaction.ACCEPTED_BELOW:
                    return V4SeqState.ACCEPTANCE_SEQUENCE;

                case V4Interaction.REJECTION:
                    return V4SeqState.FAILURE_SEQUENCE;
            }
            return s;
        }

        // ---- queries ---------------------------------------------------

        /// Nearest level knowable at the cutoff. Ties are broken by name so
        /// two runs over the same bars pick the same level.
        public V4LevelRef Nearest(double price, DateTime cutoffEt)
        {
            V4LevelRef best = null; double bestD = double.MaxValue;
            foreach (KeyValuePair<string, V4LevelRef> kv in book)
            {
                V4LevelRef r = kv.Value;
                if (!V4Num.Ok(r.Price) || r.KnownEt > cutoffEt) continue;
                double d = Math.Abs(price - r.Price);
                if (d < bestD || (d == bestD && best != null
                                  && string.CompareOrdinal(r.Name, best.Name) < 0))
                { bestD = d; best = r; }
            }
            return best;
        }

        public V4LevelRef NearestAbove(double price, DateTime cutoffEt)
        {
            V4LevelRef best = null; double bestD = double.MaxValue;
            foreach (KeyValuePair<string, V4LevelRef> kv in book)
            {
                V4LevelRef r = kv.Value;
                if (!V4Num.Ok(r.Price) || r.KnownEt > cutoffEt || r.Price <= price) continue;
                double d = r.Price - price;
                if (d < bestD) { bestD = d; best = r; }
            }
            return best;
        }

        public V4LevelRef NearestBelow(double price, DateTime cutoffEt)
        {
            V4LevelRef best = null; double bestD = double.MaxValue;
            foreach (KeyValuePair<string, V4LevelRef> kv in book)
            {
                V4LevelRef r = kv.Value;
                if (!V4Num.Ok(r.Price) || r.KnownEt > cutoffEt || r.Price >= price) continue;
                double d = price - r.Price;
                if (d < bestD) { bestD = d; best = r; }
            }
            return best;
        }

        public int MinutesSinceInteraction(V4LevelRef r, DateTime nowEt)
        {
            if (r == null || r.LastInteractionEt == DateTime.MinValue) return -1;
            return (int)(nowEt - r.LastInteractionEt).TotalMinutes;
        }
    }

    // ==================================================================
    // ADR / AWR
    // ==================================================================

    /// Average Daily and Weekly Range, both causal.
    ///
    /// Definition, stated because the prompt requires one: the mean of the
    /// last N COMPLETED exchange-day ranges. The current day is excluded -
    /// including a partly-formed range would leak information about the day
    /// still in progress, which is exactly the kind of leak that is easy to
    /// miss and impossible to see afterwards.
    ///
    /// Projections are the day's own open plus and minus the ADR, so they
    /// are fixed the moment the session opens and never move.
    public class V4RangeBook
    {
        public int AdrPeriod = 20;
        public int AwrPeriod = 8;

        private readonly V4Roll dayRanges;
        private readonly V4Roll weekRanges;

        private int curDayKey = int.MinValue, curWeekKey = int.MinValue;
        private double dayHigh = double.NaN, dayLow = double.NaN, dayOpen = double.NaN;
        private double weekHigh = double.NaN, weekLow = double.NaN;

        public V4RangeBook()
        {
            dayRanges = new V4Roll(AdrPeriod);
            weekRanges = new V4Roll(AwrPeriod);
        }

        public double AdrPts { get { return dayRanges.Full ? dayRanges.Mean() : double.NaN; } }
        public double AwrPts { get { return weekRanges.Full ? weekRanges.Mean() : double.NaN; } }
        public double DayOpen { get { return dayOpen; } }
        public double DayHigh { get { return dayHigh; } }
        public double DayLow { get { return dayLow; } }

        public void OnBar(V4Bar b, int dayKey, int weekKey)
        {
            if (dayKey != curDayKey)
            {
                if (V4Num.Ok(dayHigh) && V4Num.Ok(dayLow)) dayRanges.Add(dayHigh - dayLow);
                curDayKey = dayKey;
                dayHigh = b.High; dayLow = b.Low; dayOpen = b.Open;
            }
            else
            {
                if (b.High > dayHigh) dayHigh = b.High;
                if (b.Low < dayLow) dayLow = b.Low;
            }

            if (weekKey != curWeekKey)
            {
                if (V4Num.Ok(weekHigh) && V4Num.Ok(weekLow)) weekRanges.Add(weekHigh - weekLow);
                curWeekKey = weekKey;
                weekHigh = b.High; weekLow = b.Low;
            }
            else
            {
                if (b.High > weekHigh) weekHigh = b.High;
                if (b.Low < weekLow) weekLow = b.Low;
            }
        }

        public double AdrConsumedPts
        {
            get
            {
                if (!V4Num.Ok(dayHigh) || !V4Num.Ok(dayLow)) return double.NaN;
                return dayHigh - dayLow;
            }
        }
        public double AdrConsumedPct { get { return V4Num.Pct(AdrConsumedPts, AdrPts); } }
        public double AwrConsumedPts
        {
            get
            {
                if (!V4Num.Ok(weekHigh) || !V4Num.Ok(weekLow)) return double.NaN;
                return weekHigh - weekLow;
            }
        }
        public double AwrConsumedPct { get { return V4Num.Pct(AwrConsumedPts, AwrPts); } }

        public double AdrHighProjection
        {
            get { return (V4Num.Ok(dayOpen) && V4Num.Ok(AdrPts)) ? dayOpen + AdrPts : double.NaN; }
        }
        public double AdrLowProjection
        {
            get { return (V4Num.Ok(dayOpen) && V4Num.Ok(AdrPts)) ? dayOpen - AdrPts : double.NaN; }
        }
    }
}
