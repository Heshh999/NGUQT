// ======================================================================
// V4EmaFanEngine.cs  -  MNQ V4.1
// ======================================================================
// The 5 / 13 / 50 / 200 / 800 EMA fan per timeframe, the 1m EMA(9) used
// for the primary management hypothesis, fan-state tags, and the
// extension-from-value / return-to-value states the dealer-context
// section asks for.
//
// THIS FILE SUBMITS NO ORDERS.
//
// Nothing here is a gate. A bullish fan is not a long and a bearish fan
// is not a short; the fan is context whose value is exactly what the
// research layer measures it to be. The engine never filters on it.
//
// One practical warning that shapes the whole module: EMA800 needs real
// history. V4Ema reports no value until three periods of bars have gone
// through it, so EMA800 on 15m stays unusable for 2400 completed 15m bars
// - roughly 25 trading weeks. Any run whose warm-up is shorter than that
// simply has no 800 column, and the startup diagnostic says so rather
// than quietly emitting a half-converged number.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// Mechanical fan states. Definitions are fixed here and stated in the
    /// audit file so two runs cannot disagree.
    ///
    ///   BULLISH      : ema5 > ema13 > ema50 > ema200, strictly ordered
    ///   BEARISH      : ema5 < ema13 < ema50 < ema200, strictly ordered
    ///   COMPRESSED   : the 5-to-200 spread is under CompressedAtr ATR
    ///   EXPANDING    : that spread is widening and above CompressedAtr
    ///   TRANSITIONING: was ordered one way within TransitionLookback bars
    ///                  and is no longer ordered that way
    ///   MIXED        : anything else
    ///
    /// EMA800 is deliberately NOT part of the ordering test. It is reported
    /// as its own column because on most timeframes it is unavailable for
    /// long stretches, and letting it into the ordering would silently turn
    /// the whole fan state into UNKNOWN for months at a time.
    public enum V4FanState { UNKNOWN, BULLISH, BEARISH, MIXED, COMPRESSED, EXPANDING, TRANSITIONING }

    /// Where a vector sits relative to the fan envelope.
    public enum V4VectorFanRel { UNKNOWN, ABOVE, BELOW, INSIDE, BREAKS_UP, BREAKS_DOWN, REJECTED, RECLAIMS }

    /// One timeframe's fan. Fed one completed bar at a time.
    public class V4EmaFan
    {
        public double CompressedAtr = 0.75;
        public int TransitionLookback = 10;
        public int SlopeLookback = 10;

        private readonly string tf;
        private readonly V4Ema e5 = new V4Ema(5);
        private readonly V4Ema e13 = new V4Ema(13);
        private readonly V4Ema e50 = new V4Ema(50);
        private readonly V4Ema e200 = new V4Ema(200);
        private readonly V4Ema e800 = new V4Ema(800);

        private readonly V4Roll r5, r13, r50, r200, r800, spread;
        private readonly List<V4FanState> history = new List<V4FanState>();

        private double prevClose = double.NaN;

        private double lastClose = double.NaN;

        public V4EmaFan(string label)
        {
            tf = label;
            r5 = new V4Roll(SlopeLookback); r13 = new V4Roll(SlopeLookback);
            r50 = new V4Roll(SlopeLookback); r200 = new V4Roll(SlopeLookback);
            r800 = new V4Roll(SlopeLookback); spread = new V4Roll(SlopeLookback);
        }

        public string Tf { get { return tf; } }
        public double Ema5 { get { return e5.Value; } }
        public double Ema13 { get { return e13.Value; } }
        public double Ema50 { get { return e50.Value; } }
        public double Ema200 { get { return e200.Value; } }
        public double Ema800 { get { return e800.Value; } }
        public double PrevClose { get { return prevClose; } }
        public bool Ema50Ready { get { return e50.Ready; } }
        public bool Ema800Ready { get { return e800.Ready; } }

        public double Slope5 { get { return r5.Slope(); } }
        public double Slope13 { get { return r13.Slope(); } }
        public double Slope50 { get { return r50.Slope(); } }
        public double Slope200 { get { return r200.Slope(); } }
        public double Slope800 { get { return r800.Slope(); } }

        public void OnBar(V4Bar b, double atr)
        {
            prevClose = lastClose;
            lastClose = b.Close;


            e5.Update(b.Close); e13.Update(b.Close); e50.Update(b.Close);
            e200.Update(b.Close); e800.Update(b.Close);

            r5.Add(e5.Value); r13.Add(e13.Value); r50.Add(e50.Value);
            r200.Add(e200.Value); r800.Add(e800.Value);

            double sp = FanSpreadPts();
            spread.Add(sp);

            history.Add(ComputeState(atr, sp));
            if (history.Count > 200) history.RemoveAt(0);
        }

        /// Distance from the fastest to the slowest ordering member.
        public double FanSpreadPts()
        {
            if (!e5.Ready || !e200.Ready) return double.NaN;
            double hi = Math.Max(Math.Max(e5.Value, e13.Value), Math.Max(e50.Value, e200.Value));
            double lo = Math.Min(Math.Min(e5.Value, e13.Value), Math.Min(e50.Value, e200.Value));
            return hi - lo;
        }

        public double FanHigh
        {
            get
            {
                if (!e5.Ready || !e200.Ready) return double.NaN;
                return Math.Max(Math.Max(e5.Value, e13.Value), Math.Max(e50.Value, e200.Value));
            }
        }
        public double FanLow
        {
            get
            {
                if (!e5.Ready || !e200.Ready) return double.NaN;
                return Math.Min(Math.Min(e5.Value, e13.Value), Math.Min(e50.Value, e200.Value));
            }
        }

        private V4FanState ComputeState(double atr, double sp)
        {
            if (!e5.Ready || !e13.Ready || !e50.Ready || !e200.Ready) return V4FanState.UNKNOWN;

            bool bull = e5.Value > e13.Value && e13.Value > e50.Value && e50.Value > e200.Value;
            bool bear = e5.Value < e13.Value && e13.Value < e50.Value && e50.Value < e200.Value;

            if (V4Num.Ok(sp) && V4Num.Ok(atr) && atr > 0 && sp < CompressedAtr * atr)
                return V4FanState.COMPRESSED;

            if (bull) return V4FanState.BULLISH;
            if (bear) return V4FanState.BEARISH;

            // was it ordered recently, and is it not now?
            int from = Math.Max(0, history.Count - TransitionLookback);
            for (int i = from; i < history.Count; i++)
                if (history[i] == V4FanState.BULLISH || history[i] == V4FanState.BEARISH)
                    return V4FanState.TRANSITIONING;

            if (spread.Count >= 2 && V4Num.Ok(spread.Slope()) && spread.Slope() > 0
                && V4Num.Ok(sp) && V4Num.Ok(atr) && atr > 0 && sp >= CompressedAtr * atr)
                return V4FanState.EXPANDING;

            return V4FanState.MIXED;
        }

        public V4FanState State
        {
            get { return history.Count == 0 ? V4FanState.UNKNOWN : history[history.Count - 1]; }
        }

        /// Where a completed bar sits relative to the fan envelope.
        public V4VectorFanRel RelationOf(V4Bar b, double prevBarClose)
        {
            double hi = FanHigh, lo = FanLow;
            if (!V4Num.Ok(hi) || !V4Num.Ok(lo)) return V4VectorFanRel.UNKNOWN;

            bool prevBelow = V4Num.Ok(prevBarClose) && prevBarClose < lo;
            bool prevAbove = V4Num.Ok(prevBarClose) && prevBarClose > hi;

            if (b.Close > hi)
            {
                if (prevBelow) return V4VectorFanRel.BREAKS_UP;
                if (V4Num.Ok(prevBarClose) && prevBarClose < hi) return V4VectorFanRel.RECLAIMS;
                return V4VectorFanRel.ABOVE;
            }
            if (b.Close < lo)
            {
                if (prevAbove) return V4VectorFanRel.BREAKS_DOWN;
                return V4VectorFanRel.BELOW;
            }
            // closed inside: rejection if it poked out and came back
            if (b.High > hi || b.Low < lo) return V4VectorFanRel.REJECTED;
            return V4VectorFanRel.INSIDE;
        }

        public double DistEma50Atr(double price, double atr) { return V4Num.DistAtr(price, e50.Value, atr); }
        public double DistEma200Atr(double price, double atr) { return V4Num.DistAtr(price, e200.Value, atr); }
        public double DistFanAtr(double price, double atr)
        {
            double hi = FanHigh, lo = FanLow;
            if (!V4Num.Ok(hi) || !V4Num.Ok(lo)) return double.NaN;
            if (price > hi) return V4Num.SafeDiv(price - hi, atr, 1e-9);
            if (price < lo) return V4Num.SafeDiv(price - lo, atr, 1e-9);
            return 0.0;
        }

        public double Dist5to13Pts { get { return Sub(e5, e13); } }
        public double Dist13to50Pts { get { return Sub(e13, e50); } }
        public double Dist50to200Pts { get { return Sub(e50, e200); } }
        public double Dist200to800Pts { get { return Sub(e200, e800); } }
        private static double Sub(V4Ema a, V4Ema b)
        {
            if (!a.Ready || !b.Ready) return double.NaN;
            return a.Value - b.Value;
        }
    }

    // ==================================================================
    // EXTENSION FROM VALUE / RETURN TO VALUE
    // ==================================================================

    /// Tracks price stretching away from EMA50 / EMA200 / VWAP and whether
    /// it then returns or holds. Descriptive, and the two branches are
    /// symmetric on purpose: a strong move away from value is NOT
    /// automatically a trap, and this state does not decide which it was.
    public class V4ExtensionState
    {
        public double ExtendedAtr = 2.0;

        public bool Extended;
        public V4Dir Direction = V4Dir.NONE;
        public double ExtensionFromEma50Atr = double.NaN;
        public double ExtensionFromEma200Atr = double.NaN;
        public double ExtensionFromVwapAtr = double.NaN;
        public DateTime ExtendedAtEt = DateTime.MinValue;

        public bool ReturnedTowardValue;
        public bool ReturnedToEma50;
        public bool ReturnedToEma200;
        public bool ReturnedToVwap;
        public int BarsToReturnEma50 = -1;

        private int barsSinceExtension = -1;

        public void OnBar(V4Bar b, double atr, double ema50, double ema200, double vwap)
        {
            double d50 = V4Num.DistAtr(b.Close, ema50, atr);
            double d200 = V4Num.DistAtr(b.Close, ema200, atr);
            double dvw = V4Num.DistAtr(b.Close, vwap, atr);

            if (!Extended)
            {
                if (V4Num.Ok(d50) && Math.Abs(d50) >= ExtendedAtr)
                {
                    Extended = true;
                    Direction = d50 > 0 ? V4Dir.UP : V4Dir.DOWN;
                    ExtensionFromEma50Atr = d50;
                    ExtensionFromEma200Atr = d200;
                    ExtensionFromVwapAtr = dvw;
                    ExtendedAtEt = b.EtClose;
                    barsSinceExtension = 0;
                    ReturnedTowardValue = ReturnedToEma50 = ReturnedToEma200 = ReturnedToVwap = false;
                    BarsToReturnEma50 = -1;
                }
                return;
            }

            barsSinceExtension++;

            bool touched50 = V4Num.Ok(ema50) && b.Low <= ema50 && b.High >= ema50;
            bool touched200 = V4Num.Ok(ema200) && b.Low <= ema200 && b.High >= ema200;
            bool touchedVwap = V4Num.Ok(vwap) && b.Low <= vwap && b.High >= vwap;

            if (touched50 && !ReturnedToEma50)
            {
                ReturnedToEma50 = true; ReturnedTowardValue = true;
                BarsToReturnEma50 = barsSinceExtension;
            }
            if (touched200) ReturnedToEma200 = true;
            if (touchedVwap) { ReturnedToVwap = true; ReturnedTowardValue = true; }

            // extension resets once value is reached, so the next stretch is
            // measured independently rather than compounding onto this one
            if (ReturnedToEma50) { Extended = false; Direction = V4Dir.NONE; }
        }
    }

    // ==================================================================
    // 1M EMA(9) MANAGEMENT - THE PRIMARY V4.1 EXIT HYPOTHESIS
    // ==================================================================

    /// LONG  : the management event is the first COMPLETED 1m bar closing
    ///         BELOW the 1m EMA(9).
    /// SHORT : the first COMPLETED 1m bar closing ABOVE it.
    ///
    /// The engine records the hypothetical outcome. It submits nothing.
    ///
    /// Two details worth stating because they change the numbers. The EMA
    /// keeps updating on every 1m bar including the entry bar, and the exit
    /// test starts on the bar AFTER entry - a trade cannot be closed by the
    /// bar that opened it. And the exit fills at that bar's CLOSE, not at
    /// the EMA value, because a close-based rule can only be acted on once
    /// the close exists.
    public class V4EmaExitProbe
    {
        public bool Active;
        public int Side;                       // +1 long, -1 short
        public double EntryPrice = double.NaN;
        public DateTime EntryEt = DateTime.MinValue;
        public double StopPts = double.NaN;    // R denominator, for emaExitGrossR

        public bool Resolved;
        public int MinsToExit = -1;
        public double ExitPrice = double.NaN;
        public double GrossPts = double.NaN;
        public double GrossR = double.NaN;
        public double MaxMfePts, MaxMaePts;
        public bool EntryWasAboveEma9;

        private int barsSeen;

        public void Open(int side, double entryPrice, DateTime entryEt, double stopPts, double ema9AtEntry)
        {
            Active = true; Resolved = false;
            Side = side; EntryPrice = entryPrice; EntryEt = entryEt; StopPts = stopPts;
            EntryWasAboveEma9 = V4Num.Ok(ema9AtEntry) && entryPrice > ema9AtEntry;
            MaxMfePts = 0; MaxMaePts = 0; barsSeen = 0;
            MinsToExit = -1; ExitPrice = double.NaN; GrossPts = double.NaN; GrossR = double.NaN;
        }

        /// One completed 1m bar, strictly after the entry bar.
        public void OnBar(V4Bar b, double ema9)
        {
            if (!Active || Resolved) return;
            if (b.EtClose <= EntryEt) return;
            barsSeen++;

            double mfe = Side > 0 ? b.High - EntryPrice : EntryPrice - b.Low;
            double mae = Side > 0 ? EntryPrice - b.Low : b.High - EntryPrice;
            if (mfe > MaxMfePts) MaxMfePts = mfe;
            if (mae > MaxMaePts) MaxMaePts = mae;

            if (!V4Num.Ok(ema9)) return;
            bool exit = Side > 0 ? (b.Close < ema9) : (b.Close > ema9);
            if (!exit) return;

            Resolved = true; Active = false;
            MinsToExit = barsSeen;
            ExitPrice = b.Close;
            GrossPts = Side > 0 ? (ExitPrice - EntryPrice) : (EntryPrice - ExitPrice);
            GrossR = V4Num.SafeDiv(GrossPts, StopPts, 1e-9);
        }
    }
}
