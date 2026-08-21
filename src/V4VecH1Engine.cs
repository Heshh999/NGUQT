// ======================================================================
// V4VecH1Engine.cs  -  VEC-H1, the parent-wick retrace hypothesis
// ======================================================================
// THIS ENGINE SUBMITS NO ORDERS. It emits research rows only.
//
// FROZEN DEFINITION (transcribed from the build prompt, not invented):
//
//   A completed 15-minute vector candle creates a meaningful wick.
//   ONLY during the immediately following 15-minute candle, price
//   retraces toward that parent vector's wick extreme. A 1-minute
//   vector candle in the same intended direction appears near that
//   extreme and is the entry trigger.
//
//   LONG : parent 15m GREEN or BLUE vector with a noticeable LOWER
//          wick; next candle trades down toward the frozen LOW; a
//          completed 1m GREEN or BLUE vector fires at/near it.
//   SHORT: exact mirror - RED or VIOLET parent, UPPER wick, next
//          candle trades up toward the frozen HIGH, 1m RED or VIOLET
//          vector fires at/near it.
//
//   Wick rule (primary, frozen): relevant wick >= 20% of the parent's
//   total range. Raw size is also recorded in points, fraction and ATR
//   so alternatives can be measured WITHOUT re-running the capture.
//
//   Proximity rule (primary, frozen): the trigger bar must either
//   trade into the parent wick zone, OR come within 0.10 x parent ATR
//   of the frozen extreme. Both components are recorded separately.
//
// CAUSALITY - the prompt states this as an explicit rejection rule:
//   "No 1m trigger may occur before the parent 15m candle has CLOSED.
//    If entryTime < parent15mCloseTime, that row is a LOOKAHEAD
//    VIOLATION and must be rejected."
// The equality case (a 1m bar closing AT the parent close - the last
// minute INSIDE the parent candle) is EXPECTED once per parent and is
// counted as BoundaryExcluded; only strictly-before counts as a
// violation. Both are visible in the audit rather than hidden.
//
// MATCHED ARMS - all three are emitted against the SAME parent so that
// none can be chosen after the outcomes are known:
//
//   A_LOCATION_ONLY  price reached the wick zone, but the first bar to
//                    do so was NOT a qualifying same-direction vector.
//   B_VECTOR_AWAY    a qualifying same-direction 1m vector fired inside
//                    the window, but AWAY from the wick extreme.
//   C_FULL           qualifying same-direction 1m vector AT/NEAR the
//                    extreme - the hypothesis itself.
//
//   C vs A isolates the VECTOR. C vs B isolates the LOCATION. That
//   separation is the whole point: without it a result only shows that
//   same-colour vectors tend to follow one another.
//
// Retrace gating: A and C require RetraceSeen, because both are claims
// about price coming BACK to the extreme. B is not gated on it - B asks
// whether the vector alone carries information - but every row records
// f_retraceSeen so a fully matched subset can still be formed in
// analysis without recapturing.
// ======================================================================
using System;
using System.Collections.Generic;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public enum V4VecH1Arm { NONE, A_LOCATION_ONLY, B_VECTOR_AWAY, C_FULL }

    /// A completed 15m vector whose wick qualifies, with the one-candle
    /// search window that follows it. Everything here is frozen at the
    /// parent's close and never rewritten.
    public class V4VecH1Parent
    {
        public string ParentId = "";
        public DateTime CloseEt;          // parent close == window open
        public DateTime WindowEndEt;      // close + WindowMinutes
        public int Side;                  // +1 long, -1 short
        public V4VectorColor Color;
        public V4VectorTier Tier;
        public double Open, High, Low, Close;
        public double RangePts, Atr, RelVolume;
        public double WickPts, WickPctOfRange, WickAtr;
        public double Extreme;            // Low for long, High for short
        public double WickInnerEdge;      // body edge bounding the wick
        public double ProximityBand;      // ProximityAtrMult * Atr

        // window state
        public bool WindowOpened;
        public double WindowOpenPrice;
        public bool RetraceSeen;
        public int BarsSeen;
        public bool FiredA, FiredB, FiredC;

        public bool Contains(DateTime et) { return et > CloseEt && et <= WindowEndEt; }

        /// The price at or beyond which a bar counts as "at/near" the
        /// extreme. The frozen rule is an OR of two conditions, which is
        /// exactly a single threshold at the looser of the two.
        public double NearThreshold()
        {
            double band = Side > 0 ? Extreme + ProximityBand : Extreme - ProximityBand;
            if (Side > 0) return Math.Max(WickInnerEdge, band);
            return Math.Min(WickInnerEdge, band);
        }
    }

    public class V4VecH1Signal
    {
        public V4VecH1Arm Arm;
        public V4VecH1Parent Parent;
        public V4Bar TriggerBar;
        public V4Vector TriggerVector;      // null on arm A by construction
        public double EntryPrice;
        public DateTime EntryEt;
        public int MinsFromParentClose;
        public int BarIndexInWindow;
        public double DistToExtremePts, DistToExtremeAtr;
        public bool TouchedExtreme, TradedIntoWick, WithinAtrBand;
        public bool RetraceSeen;
    }

    public class V4VecH1Engine
    {
        // ---- frozen primaries; exposed so perturbation tests can move
        // ---- them WITHOUT the engine ever choosing a value itself
        public double MinWickPctOfRange = 20.0;
        public double ProximityAtrMult = 0.10;
        public int WindowMinutes = 15;

        public V4VecH1Parent Active;
        public long ParentsCreated, ParentsExpired;
        /// A 1m bar closing at EXACTLY the parent's close - the last minute
        /// INSIDE the parent candle, delivered at the same stamp. Correctly
        /// excluded, EXPECTED once per parent. The field-observed count was
        /// 430 exclusions against 431 parents, which is this artifact, not
        /// leakage: the CSV itself showed 0 of 546 entries at or before
        /// their parent close.
        public long BoundaryExcluded;
        /// A 1m bar closing STRICTLY BEFORE the parent's close while the
        /// window is active. Bars arrive in time order, so this can only
        /// happen if the 1m clock is genuinely out of order. MUST be 0.
        public long LookaheadRejected;
        public long FiredA, FiredB, FiredC;

        private int seq;
        private readonly string symbol;

        public V4VecH1Engine(string symbolIn) { symbol = symbolIn ?? "MNQ"; }

        public void Clear()
        {
            Active = null; seq = 0;
            ParentsCreated = ParentsExpired = 0;
            BoundaryExcluded = LookaheadRejected = 0;
            FiredA = FiredB = FiredC = 0;
        }

        public static int SideOf(V4VectorColor c)
        {
            if (c == V4VectorColor.GREEN || c == V4VectorColor.BLUE) return 1;
            if (c == V4VectorColor.RED || c == V4VectorColor.VIOLET) return -1;
            return 0;
        }

        public static bool ColorQualifies(V4VectorColor c, int side)
        {
            return side != 0 && SideOf(c) == side;
        }

        /// Fold a COMPLETED 15m bar. A qualifying parent replaces any
        /// previous one: windows are exactly one candle long and cannot
        /// overlap, so at most one is ever live.
        public V4VecH1Parent On15mBar(V4Bar b, V4Vector v, double atr)
        {
            if (Active != null && b.EtClose >= Active.WindowEndEt)
            { ParentsExpired++; Active = null; }

            if (v == null) return null;
            int side = SideOf(v.Color);
            if (side == 0) return null;
            double range = v.High - v.Low;
            if (!V4Num.Ok(range) || range <= 0) return null;

            double wick = side > 0 ? (v.BodyLow - v.Low) : (v.High - v.BodyHigh);
            if (!V4Num.Ok(wick) || wick < 0) wick = 0;
            double pct = 100.0 * wick / range;
            if (pct < MinWickPctOfRange) return null;

            seq++;
            V4VecH1Parent p = new V4VecH1Parent();
            p.ParentId = symbol + "-VECH1-" + b.EtClose.ToString("yyyyMMddHHmmss") + "-" + seq;
            p.CloseEt = b.EtClose;
            p.WindowEndEt = b.EtClose.AddMinutes(WindowMinutes);
            p.Side = side; p.Color = v.Color; p.Tier = v.Tier;
            p.Open = v.Open; p.High = v.High; p.Low = v.Low; p.Close = v.Close;
            p.RangePts = range; p.Atr = atr; p.RelVolume = v.RelVolume;
            p.WickPts = wick; p.WickPctOfRange = pct;
            p.WickAtr = (V4Num.Ok(atr) && atr > 0) ? wick / atr : double.NaN;
            p.Extreme = side > 0 ? v.Low : v.High;
            p.WickInnerEdge = side > 0 ? v.BodyLow : v.BodyHigh;
            p.ProximityBand = (V4Num.Ok(atr) && atr > 0) ? ProximityAtrMult * atr : 0.0;

            Active = p; ParentsCreated++;
            return p;
        }

        /// Fold a COMPLETED 1m bar. Returns every arm that fired on this
        /// bar (at most one; arms are mutually exclusive per bar).
        public List<V4VecH1Signal> On1mBar(V4Bar b, V4Vector v1m)
        {
            List<V4VecH1Signal> outp = new List<V4VecH1Signal>();
            V4VecH1Parent p = Active;
            if (p == null) return outp;

            // Hard causality gate. The prompt's rejection rule: no trigger
            // at or before the parent's close. The two cases are counted
            // apart because they mean opposite things - equality is the
            // boundary bar (expected, once per parent), strictly-before is
            // a broken clock (never acceptable).
            if (b.EtClose == p.CloseEt) { BoundaryExcluded++; return outp; }
            if (b.EtClose < p.CloseEt) { LookaheadRejected++; return outp; }
            if (b.EtClose > p.WindowEndEt) { ParentsExpired++; Active = null; return outp; }

            p.BarsSeen++;
            if (!p.WindowOpened) { p.WindowOpened = true; p.WindowOpenPrice = b.Open; }

            // retrace: price moved away from the window's opening area,
            // back toward the frozen extreme
            if (p.Side > 0 ? b.Low < p.WindowOpenPrice : b.High > p.WindowOpenPrice)
                p.RetraceSeen = true;

            double probe = p.Side > 0 ? b.Low : b.High;
            bool intoWick = p.Side > 0 ? probe <= p.WickInnerEdge : probe >= p.WickInnerEdge;
            bool inBand = p.Side > 0 ? probe <= p.Extreme + p.ProximityBand
                                     : probe >= p.Extreme - p.ProximityBand;
            bool near = intoWick || inBand;
            bool touched = p.Side > 0 ? probe <= p.Extreme : probe >= p.Extreme;

            bool vecOk = v1m != null && ColorQualifies(v1m.Color, p.Side);

            V4VecH1Arm arm = V4VecH1Arm.NONE;
            if (vecOk && near && p.RetraceSeen && !p.FiredC) arm = V4VecH1Arm.C_FULL;
            else if (vecOk && !near && !p.FiredB) arm = V4VecH1Arm.B_VECTOR_AWAY;
            else if (!vecOk && near && p.RetraceSeen && !p.FiredA) arm = V4VecH1Arm.A_LOCATION_ONLY;
            if (arm == V4VecH1Arm.NONE) return outp;

            V4VecH1Signal s = new V4VecH1Signal();
            s.Arm = arm; s.Parent = p; s.TriggerBar = b;
            s.TriggerVector = arm == V4VecH1Arm.A_LOCATION_ONLY ? null : v1m;
            s.EntryPrice = b.Close; s.EntryEt = b.EtClose;
            s.MinsFromParentClose = (int)(b.EtClose - p.CloseEt).TotalMinutes;
            s.BarIndexInWindow = p.BarsSeen;
            s.DistToExtremePts = Math.Abs(probe - p.Extreme);
            s.DistToExtremeAtr = (V4Num.Ok(p.Atr) && p.Atr > 0)
                ? s.DistToExtremePts / p.Atr : double.NaN;
            s.TouchedExtreme = touched; s.TradedIntoWick = intoWick;
            s.WithinAtrBand = inBand; s.RetraceSeen = p.RetraceSeen;

            if (arm == V4VecH1Arm.C_FULL) { p.FiredC = true; FiredC++; }
            else if (arm == V4VecH1Arm.B_VECTOR_AWAY) { p.FiredB = true; FiredB++; }
            else { p.FiredA = true; FiredA++; }

            outp.Add(s);
            return outp;
        }

        /// Stop references for one signal, frozen at entry.
        ///
        /// MEDIUM is the PRIMARY and the race stop, and it is 1.5 x the
        /// parent ATR rather than a candle edge. That is a measured
        /// choice, not a preference: across 33,929 DEV and 15,215 VAL
        /// probes the whole spread between eight stop families was
        /// 0.59 pt - less than the cost of trading - and ATR-scaled
        /// stops at 1.0-2.0x were the only family ranking well in BOTH
        /// splits. The 1m candle edge was hit on 82% of trades.
        public static void StopRefs(V4VecH1Signal s, double tickSize,
                                    out double tight, out double medium, out double structural)
        {
            int side = s.Parent.Side;
            double tk = tickSize > 0 ? tickSize : 0.25;
            tight = side > 0 ? s.TriggerBar.Low - tk : s.TriggerBar.High + tk;
            double atr = V4Num.Ok(s.Parent.Atr) && s.Parent.Atr > 0 ? s.Parent.Atr : 0.0;
            medium = side > 0 ? s.EntryPrice - 1.5 * atr : s.EntryPrice + 1.5 * atr;
            structural = side > 0 ? s.Parent.Extreme - tk : s.Parent.Extreme + tk;
        }
    }
}
