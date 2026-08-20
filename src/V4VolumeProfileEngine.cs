// ======================================================================
// V4VolumeProfileEngine.cs  -  MNQ V4.1
// ======================================================================
// Volume at price: POC, value area, HVN and LVN, built per session from
// the SAME per-price ask/bid volumes the order-flow engine already reads.
//
// THIS FILE SUBMITS NO ORDERS.
//
// Two constraints define this module.
//
// First, coverage. A profile can only be built where per-price volume
// exists, which means the Volumetric series. That is a far shorter history
// than structure has. Profile therefore inherits the order-flow window
// exactly - it does not get the full history - and every row is stamped
// with its data layer so a ten-month profile test is never reported beside
// a seven-year structure test as though they were the same evidence.
//
// Second, purpose. Volume Profile is LOCATION and TARGET context. It is
// not assumed to predict direction, and nothing here returns a direction.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public enum V4ProfileInteraction
    {
        NONE, INSIDE_VALUE, OUTSIDE_ABOVE, OUTSIDE_BELOW,
        ACCEPTED_INTO_VALUE, REJECTED_FROM_VALUE,
        AT_POC, AT_VAH, AT_VAL, AT_HVN, AT_LVN
    }

    /// One completed session's volume-at-price picture.
    public class V4Profile
    {
        public DateTime SessionStartEt = DateTime.MinValue;
        public DateTime AsOfEt = DateTime.MinValue;
        public int DayKey = int.MinValue;

        public double Poc = double.NaN;
        public double PocVolume;
        public double Vah = double.NaN;
        public double Val = double.NaN;
        public double TotalVolume;
        public int LevelCount;

        public readonly List<double> Hvn = new List<double>();
        public readonly List<double> Lvn = new List<double>();

        public bool Ready { get { return V4Num.Ok(Poc) && LevelCount > 0; } }
    }

    /// Accumulates per-price volume and rebuilds the profile on demand.
    ///
    /// The value area is the conventional 70% of traded volume expanded
    /// outward from the POC, taking whichever adjacent side holds more
    /// volume at each step. Stated explicitly because "value area" is used
    /// loosely elsewhere and two different expansions give two different
    /// VAH/VAL for the same data.
    public class V4VolumeProfileEngine
    {
        public double ValueAreaPct = 70.0;
        public double TickSize = 0.25;
        /// A node counts as high volume at this multiple of mean level volume.
        public double HvnMult = 1.75;
        /// ...and as low volume below this multiple.
        public double LvnMult = 0.35;
        public int MaxLevels = 20000;

        private readonly Dictionary<long, double> vol = new Dictionary<long, double>();
        private int curDayKey = int.MinValue;
        private DateTime sessionStart = DateTime.MinValue;
        private DateTime asOf = DateTime.MinValue;

        public V4Profile Current = new V4Profile();
        public V4Profile PriorSession = new V4Profile();

        public long Key(double price) { return (long)Math.Round(price / TickSize); }
        public double PriceOf(long key) { return key * TickSize; }

        /// Add one bar's worth of per-price volume. Called from the
        /// order-flow host, which already has the footprint in hand - there
        /// is no second pass over the data.
        public void AddLevel(double price, double volume, DateTime etClose, int dayKey)
        {
            if (dayKey != curDayKey) RollSession(dayKey, etClose);
            if (!V4Num.Ok(price) || !V4Num.Ok(volume) || volume <= 0) return;
            if (vol.Count >= MaxLevels) return;
            long k = Key(price);
            double cur;
            vol.TryGetValue(k, out cur);
            vol[k] = cur + volume;
            asOf = etClose;
        }

        private void RollSession(int dayKey, DateTime etClose)
        {
            if (curDayKey != int.MinValue && vol.Count > 0)
            {
                PriorSession = Build();
            }
            vol.Clear();
            curDayKey = dayKey;
            sessionStart = etClose;
            Current = new V4Profile();
        }

        /// Rebuild the developing profile from everything traded so far in
        /// this session. Causal by construction - it can only see volume
        /// that has already printed.
        public V4Profile Build()
        {
            V4Profile p = new V4Profile();
            p.DayKey = curDayKey;
            p.SessionStartEt = sessionStart;
            p.AsOfEt = asOf;
            p.LevelCount = vol.Count;
            if (vol.Count == 0) return p;

            List<long> keys = new List<long>(vol.Keys);
            keys.Sort();

            double total = 0, best = -1; long pocKey = keys[0];
            for (int i = 0; i < keys.Count; i++)
            {
                double v = vol[keys[i]];
                total += v;
                if (v > best) { best = v; pocKey = keys[i]; }
            }
            p.TotalVolume = total;
            p.Poc = PriceOf(pocKey);
            p.PocVolume = best;

            // value area: expand out from the POC, taking the heavier side
            double target = total * (ValueAreaPct / 100.0);
            int pocIdx = keys.BinarySearch(pocKey);
            if (pocIdx < 0) pocIdx = 0;
            int lo = pocIdx, hi = pocIdx;
            double acc = best;
            while (acc < target && (lo > 0 || hi < keys.Count - 1))
            {
                double below = lo > 0 ? vol[keys[lo - 1]] : -1;
                double above = hi < keys.Count - 1 ? vol[keys[hi + 1]] : -1;
                if (above >= below && above >= 0) { hi++; acc += above; }
                else if (below >= 0) { lo--; acc += below; }
                else break;
            }
            p.Val = PriceOf(keys[lo]);
            p.Vah = PriceOf(keys[hi]);

            double mean = total / keys.Count;
            for (int i = 0; i < keys.Count; i++)
            {
                double v = vol[keys[i]];
                if (v >= HvnMult * mean) p.Hvn.Add(PriceOf(keys[i]));
                else if (v <= LvnMult * mean) p.Lvn.Add(PriceOf(keys[i]));
            }

            Current = p;
            return p;
        }

        // ---- location queries -------------------------------------------

        public static V4ProfileInteraction Interaction(V4Profile p, V4Bar b, double atr)
        {
            if (p == null || !p.Ready) return V4ProfileInteraction.NONE;
            double band = V4Num.Ok(atr) && atr > 0 ? 0.25 * atr : 0.0;

            if (Near(b, p.Poc, band)) return V4ProfileInteraction.AT_POC;
            if (Near(b, p.Vah, band)) return V4ProfileInteraction.AT_VAH;
            if (Near(b, p.Val, band)) return V4ProfileInteraction.AT_VAL;

            bool inside = b.Close <= p.Vah && b.Close >= p.Val;
            if (inside)
            {
                bool cameFromOutside = b.Open > p.Vah || b.Open < p.Val;
                return cameFromOutside ? V4ProfileInteraction.ACCEPTED_INTO_VALUE
                                       : V4ProfileInteraction.INSIDE_VALUE;
            }
            bool pokedIn = (b.Low < p.Vah && b.High > p.Val);
            if (pokedIn) return V4ProfileInteraction.REJECTED_FROM_VALUE;
            return b.Close > p.Vah ? V4ProfileInteraction.OUTSIDE_ABOVE
                                   : V4ProfileInteraction.OUTSIDE_BELOW;
        }

        private static bool Near(V4Bar b, double lvl, double band)
        {
            if (!V4Num.Ok(lvl)) return false;
            return b.High >= lvl - band && b.Low <= lvl + band;
        }

        /// Nearest profile node of any kind, as a target candidate.
        public static double NearestNode(V4Profile p, double price, int side, out string which)
        {
            which = "";
            if (p == null || !p.Ready) return double.NaN;
            double best = double.NaN, bestD = double.MaxValue;
            Consider(p.Poc, "POC", price, side, ref best, ref bestD, ref which);
            Consider(p.Vah, "VAH", price, side, ref best, ref bestD, ref which);
            Consider(p.Val, "VAL", price, side, ref best, ref bestD, ref which);
            for (int i = 0; i < p.Hvn.Count; i++)
                Consider(p.Hvn[i], "HVN", price, side, ref best, ref bestD, ref which);
            for (int i = 0; i < p.Lvn.Count; i++)
                Consider(p.Lvn[i], "LVN", price, side, ref best, ref bestD, ref which);
            return best;
        }

        private static void Consider(double lvl, string name, double price, int side,
                                     ref double best, ref double bestD, ref string which)
        {
            if (!V4Num.Ok(lvl)) return;
            double d = side > 0 ? lvl - price : price - lvl;
            if (d <= 0) return;                       // must be ahead of the trade
            if (d < bestD) { bestD = d; best = lvl; which = name; }
        }

        public string AuditText(bool volumetricPassed, DateTime firstEt, DateTime lastEt, int sessions)
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("V4.1 VOLUME PROFILE AUDIT");
            sb.AppendLine("======================================================================");
            sb.AppendLine("Construction");
            sb.AppendLine("  per-price volume is taken from the SAME Volumetric read the");
            sb.AppendLine("  order-flow engine performs. There is no second pass and no");
            sb.AppendLine("  reconstruction from OHLCV.");
            sb.AppendLine("  value area  " + ValueAreaPct.ToString("0.#", CultureInfo.InvariantCulture)
                          + "% of session volume, expanded outward from the POC,");
            sb.AppendLine("              taking the heavier adjacent side at each step.");
            sb.AppendLine("  HVN         level volume >= " + HvnMult.ToString("0.##", CultureInfo.InvariantCulture) + " x mean level volume");
            sb.AppendLine("  LVN         level volume <= " + LvnMult.ToString("0.##", CultureInfo.InvariantCulture) + " x mean level volume");
            sb.AppendLine("  session     resets at the CME exchange day boundary, 18:00 ET");
            sb.AppendLine("Coverage");
            sb.AppendLine("  first bar (ET)   " + V4Num.T(firstEt));
            sb.AppendLine("  last bar  (ET)   " + V4Num.T(lastEt));
            sb.AppendLine("  sessions         " + V4Num.I(sessions));
            sb.AppendLine("Dependency");
            sb.AppendLine("  volumetric audit " + (volumetricPassed ? "PASSED" : "FAILED"));
            sb.AppendLine("======================================================================");
            sb.AppendLine(volumetricPassed
                ? "VERDICT: PASSED - profile is built from verified per-price volume."
                : "VERDICT: FAILED - NO USABLE PER-PRICE VOLUME. PROFILE FIELDS ARE NOT VALID.");
            sb.AppendLine("======================================================================");
            sb.AppendLine("NOTE: profile coverage equals volumetric coverage, which is far");
            sb.AppendLine("shorter than the structure history. Never report a profile result");
            sb.AppendLine("beside a full-history structure result as equivalent evidence.");
            return sb.ToString();
        }
    }
}
