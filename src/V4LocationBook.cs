// ============================================================================
// V4LocationBook.cs
//
// RESEARCH MODULE - SUBMITS NO ORDERS, EVER.
//
// The "LOCATION" half of the brief's STRUCTURE + LOCATION question:
//
//   "Test structural breaks occurring at or around meaningful levels
//    separately from arbitrary structure breaks. Determine whether
//    STRUCTURE + LOCATION contains more information than either feature
//    independently."
//
// Answering that requires a level book that is independent of the structure
// tracker, so the two features can be crossed rather than confounded. This is
// that book. It is fed the 1-minute stream and nothing else.
//
// LEVELS TRACKED (all independently justified, none invented here)
//   prior day high / low        the CME exchange day, rolling at 18:00 ET
//   prior week high / low       week rolling at Sunday 18:00 ET
//   session high / low          the RTH session so far
//   session open                the 09:30 ET open
//   session VWAP                volume-weighted from the RTH open
//
// WHAT IS DELIBERATELY ABSENT
//   Round numbers. MNQ history is a BACK-ADJUSTED continuous contract: the
//   absolute price in 2019 is offset from the price that actually traded by
//   thousands of points, and that offset changes at every roll. A "21000
//   round number" in back-adjusted history was never a round number to anyone
//   who traded it. Round-number levels are therefore not tracked at all
//   rather than tracked and quietly wrong. Session VWAP and the day/week
//   extremes are RELATIVE measures and survive back-adjustment intact.
//
// NO-LOOKAHEAD CONTRACT
//   The book is fed with a ONE-BAR DELAY by the research engine, so at the
//   moment any event is described the book contains only bars that closed
//   STRICTLY BEFORE the most recent minute. Every row records the book's own
//   as-of timestamp so that this can be verified from the data rather than
//   taken on trust. Session extremes therefore never include the bar being
//   described, and "did this break the session high" stays a real question.
// ============================================================================

using System;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public class V4LocationBook
    {
        /// CME exchange day boundary, in ET minutes. 18:00 ET.
        public int DayStartMinutesEt = 1080;
        /// RTH window, in ET minutes. 09:30 - 16:00.
        public int RthStartMinutesEt = 570;
        public int RthEndMinutesEt = 960;

        // -- exchange day / week accumulators --------------------------------
        private int curDayKey = int.MinValue;
        private int curWeekKey = int.MinValue;
        private double dayHigh = double.NaN, dayLow = double.NaN;
        private double weekHigh = double.NaN, weekLow = double.NaN;

        public double PriorDayHigh = double.NaN, PriorDayLow = double.NaN;
        public double PriorWeekHigh = double.NaN, PriorWeekLow = double.NaN;

        // -- RTH session accumulators ----------------------------------------
        private DateTime curSessionDate = DateTime.MinValue;
        private double pvSum, volSum;

        public double SessionHigh = double.NaN, SessionLow = double.NaN;
        public double SessionOpen = double.NaN;
        public double SessionVwap = double.NaN;

        /// Close time of the most recent bar actually folded into this book.
        /// Emitted with every research row so the no-lookahead claim is checkable.
        public DateTime AsOfEt = DateTime.MinValue;

        /// The exchange day a timestamp belongs to. Anything at or after 18:00 ET
        /// belongs to the NEXT calendar day's session, which is why a bare
        /// calendar date is the wrong key for futures.
        public int ExchangeDayKey(DateTime et)
        {
            DateTime d = et.Date;
            if (et.Hour * 60 + et.Minute >= DayStartMinutesEt) d = d.AddDays(1);
            return d.Year * 10000 + d.Month * 100 + d.Day;
        }

        /// The exchange week a timestamp belongs to, keyed by the date of the
        /// Sunday 18:00 ET open that started it.
        public int ExchangeWeekKey(DateTime et)
        {
            DateTime d = et.Date;
            if (et.Hour * 60 + et.Minute >= DayStartMinutesEt) d = d.AddDays(1);
            // walk back to the Monday of that session week; the week that opens
            // Sunday 18:00 ET is the week whose first session day is Monday.
            int dow = (int)d.DayOfWeek;              // Sunday = 0
            int back = dow == 0 ? 6 : dow - 1;       // Sunday session day belongs to prior Monday week
            DateTime mon = d.AddDays(-back);
            return mon.Year * 10000 + mon.Month * 100 + mon.Day;
        }

        /// Fold one COMPLETED 1-minute bar into the book.
        public void Apply(V4Bar b)
        {
            AsOfEt = b.EtClose;
            int dk = ExchangeDayKey(b.EtClose);
            int wk = ExchangeWeekKey(b.EtClose);

            if (dk != curDayKey)
            {
                if (curDayKey != int.MinValue) { PriorDayHigh = dayHigh; PriorDayLow = dayLow; }
                curDayKey = dk;
                dayHigh = double.NaN; dayLow = double.NaN;
            }
            if (wk != curWeekKey)
            {
                if (curWeekKey != int.MinValue) { PriorWeekHigh = weekHigh; PriorWeekLow = weekLow; }
                curWeekKey = wk;
                weekHigh = double.NaN; weekLow = double.NaN;
            }

            if (double.IsNaN(dayHigh) || b.High > dayHigh) dayHigh = b.High;
            if (double.IsNaN(dayLow) || b.Low < dayLow) dayLow = b.Low;
            if (double.IsNaN(weekHigh) || b.High > weekHigh) weekHigh = b.High;
            if (double.IsNaN(weekLow) || b.Low < weekLow) weekLow = b.Low;

            // ---- RTH session ------------------------------------------------
            int m = b.EtClose.Hour * 60 + b.EtClose.Minute;
            DateTime sessDate = b.EtClose.Date;
            if (sessDate != curSessionDate)
            {
                curSessionDate = sessDate;
                SessionHigh = double.NaN; SessionLow = double.NaN;
                SessionOpen = double.NaN; SessionVwap = double.NaN;
                pvSum = 0; volSum = 0;
            }
            if (m <= RthStartMinutesEt || m > RthEndMinutesEt) return;

            if (double.IsNaN(SessionOpen)) SessionOpen = b.Open;
            if (double.IsNaN(SessionHigh) || b.High > SessionHigh) SessionHigh = b.High;
            if (double.IsNaN(SessionLow) || b.Low < SessionLow) SessionLow = b.Low;

            double tp = (b.High + b.Low + b.Close) / 3.0;
            pvSum += tp * b.Volume;
            volSum += b.Volume;
            SessionVwap = volSum > 0 ? pvSum / volSum : double.NaN;
        }

        /// Signed distance from a price to a level, expressed in ATR. Positive
        /// means the price is ABOVE the level.
        public static double DistAtr(double price, double level, double atr)
        {
            if (double.IsNaN(level) || double.IsNaN(atr) || atr <= 0) return double.NaN;
            return (price - level) / atr;
        }

        /// Name and absolute ATR distance of the closest tracked level to a price.
        /// The brief's STRUCTURE + LOCATION cross needs one categorical answer to
        /// "was this break AT a level", not six separate distances, so this
        /// produces it deterministically: nearest wins, ties broken by the fixed
        /// order below.
        public void Nearest(double price, double atr, out string name, out double distAtr)
        {
            name = "NONE"; distAtr = double.NaN;
            if (double.IsNaN(atr) || atr <= 0) return;
            Consider("PRIOR_DAY_HIGH", PriorDayHigh, price, atr, ref name, ref distAtr);
            Consider("PRIOR_DAY_LOW", PriorDayLow, price, atr, ref name, ref distAtr);
            Consider("PRIOR_WEEK_HIGH", PriorWeekHigh, price, atr, ref name, ref distAtr);
            Consider("PRIOR_WEEK_LOW", PriorWeekLow, price, atr, ref name, ref distAtr);
            Consider("SESSION_HIGH", SessionHigh, price, atr, ref name, ref distAtr);
            Consider("SESSION_LOW", SessionLow, price, atr, ref name, ref distAtr);
            Consider("SESSION_OPEN", SessionOpen, price, atr, ref name, ref distAtr);
            Consider("SESSION_VWAP", SessionVwap, price, atr, ref name, ref distAtr);
        }

        private static void Consider(string n, double level, double price, double atr,
                                     ref string bestName, ref double bestDist)
        {
            if (double.IsNaN(level)) return;
            double d = Math.Abs(price - level) / atr;
            if (double.IsNaN(bestDist) || d < bestDist) { bestDist = d; bestName = n; }
        }
    }
}
