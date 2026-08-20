// ======================================================================
// V4ForwardLabelEngine.cs  -  MNQ V4.1
// ======================================================================
// Everything that needs bars which have not closed yet. Every field this
// file produces is a LABEL and is written with a y_ prefix. Nothing here
// may ever be read back into feature or event construction.
//
// THIS FILE SUBMITS NO ORDERS.
//
// The important part of this module is the part that refuses to answer.
//
// When a single 1-minute bar's low reaches the stop and its high reaches
// the target, OHLC cannot say which came first. Earlier work in this
// project measured what that costs: across 2.28 million resolved 1R
// races, assuming stop-first gives P(target first) = 0.4869 and assuming
// target-first gives 0.5290, each with a +-0.0006 interval. The modelling
// choice is roughly fifty times the statistical uncertainty, and 0.50 sits
// inside the bracket. Picking a convention silently would have
// manufactured a spectacular and entirely fake edge.
//
// So this engine marks those races AMBIGUOUS and emits BOTH bounds. Those
// events are the ones that would justify a later 30s or tick pass, and
// they are flagged so that pass can find them.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// How a stop/target race ended.
    public enum V4RaceOutcome
    {
        UNRESOLVED,     // window still open
        TARGET,         // target reached, stop untouched, unambiguous
        STOP,           // stop reached, target untouched, unambiguous
        AMBIGUOUS,      // one bar spanned both - OHLC cannot order them
        TIMEOUT         // neither reached inside the window
    }

    /// Which stop in the declared family. No optimized distances: three
    /// mechanically-defined invalidation points, and the research layer
    /// decides between them.
    public enum V4StopKind { TIGHT, MEDIUM, STRUCTURAL }

    /// A frozen target, identified and priced AT ENTRY. A target chosen
    /// from a level that did not exist yet is the single easiest way to
    /// fabricate an edge, so identity and price are both captured at entry
    /// and never revisited.
    public struct V4Target
    {
        public string Kind;          // VECTOR_ZONE / LIQUIDITY / SWING / HTF_STRUCT / SESSION / FIXED_R
        public string Detail;        // level or vector id
        public double Price;
        public double DistancePts;
        public double DistanceAtr;
        public bool Valid;

        public static V4Target None()
        {
            V4Target t = new V4Target();
            t.Kind = ""; t.Detail = ""; t.Price = double.NaN;
            t.DistancePts = double.NaN; t.DistanceAtr = double.NaN; t.Valid = false;
            return t;
        }
        public static V4Target Make(string kind, string detail, double price,
                                    double entry, int side, double atr)
        {
            V4Target t = new V4Target();
            t.Kind = kind; t.Detail = detail; t.Price = price;
            if (!V4Num.Ok(price)) { t.Valid = false; t.DistancePts = t.DistanceAtr = double.NaN; return t; }
            double d = side > 0 ? price - entry : entry - price;
            t.DistancePts = d;
            t.DistanceAtr = V4Num.SafeDiv(d, atr, 1e-9);
            // a target behind the entry is not a target
            t.Valid = d > 0;
            return t;
        }
    }

    /// The three declared stops, frozen at entry.
    public class V4StopSet
    {
        public double TightPrice = double.NaN, TightPts = double.NaN, TightAtr = double.NaN;
        public double MediumPrice = double.NaN, MediumPts = double.NaN, MediumAtr = double.NaN;
        public double StructuralPrice = double.NaN, StructuralPts = double.NaN, StructuralAtr = double.NaN;

        public bool HitTight, HitMedium, HitStructural;
        public int MinsToTight = -1, MinsToMedium = -1, MinsToStructural = -1;

        /// Whether price later reached the reference target AFTER the stop
        /// would have been hit. This is what exposes a stop that is
        /// systematically too tight, and it cannot be recovered from the
        /// P&L alone.
        public bool TargetReachedAfterTight, TargetReachedAfterMedium, TargetReachedAfterStructural;

        public void Freeze(int side, double entry, double atr,
                           double tightRef, double mediumRef, double structuralRef)
        {
            TightPrice = tightRef; MediumPrice = mediumRef; StructuralPrice = structuralRef;
            TightPts = Dist(side, entry, tightRef);
            MediumPts = Dist(side, entry, mediumRef);
            StructuralPts = Dist(side, entry, structuralRef);
            TightAtr = V4Num.SafeDiv(TightPts, atr, 1e-9);
            MediumAtr = V4Num.SafeDiv(MediumPts, atr, 1e-9);
            StructuralAtr = V4Num.SafeDiv(StructuralPts, atr, 1e-9);
        }
        private static double Dist(int side, double entry, double stop)
        {
            if (!V4Num.Ok(stop)) return double.NaN;
            double d = side > 0 ? entry - stop : stop - entry;
            return d > 0 ? d : double.NaN;    // a stop on the wrong side is not a stop
        }

        public double PtsFor(V4StopKind k)
        {
            if (k == V4StopKind.TIGHT) return TightPts;
            if (k == V4StopKind.MEDIUM) return MediumPts;
            return StructuralPts;
        }
        public double PriceFor(V4StopKind k)
        {
            if (k == V4StopKind.TIGHT) return TightPrice;
            if (k == V4StopKind.MEDIUM) return MediumPrice;
            return StructuralPrice;
        }
    }

    /// One R-multiple race against one stop, resolved on 1m bars.
    public class V4RRace
    {
        public double Multiple;
        public V4RaceOutcome Outcome = V4RaceOutcome.UNRESOLVED;
        public int MinsToResolve = -1;
        /// Both bounds, so an ambiguous race is still usable as an interval.
        public bool WouldWinIfTargetFirst;
        public bool WouldLoseIfStopFirst;
    }

    /// The complete forward-label bundle for one entry probe.
    public class V4ForwardLabels
    {
        /// The prompt's horizon grid. 1m is the common fine clock.
        public static readonly int[] Horizons =
            new int[] { 1, 2, 3, 5, 10, 15, 30, 60, 80, 120, 240 };

        /// The prompt's R grid. Nothing is optimized around one target.
        public static readonly double[] RGrid =
            new double[] { 0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0 };

        public int Side;
        public double EntryPrice = double.NaN;
        public DateTime EntryEt = DateTime.MinValue;
        public double AtrAtEntry = double.NaN;

        public readonly double[] Net = new double[Horizons.Length];
        public readonly double[] Mfe = new double[Horizons.Length];
        public readonly double[] Mae = new double[Horizons.Length];

        public double MaxMfePts, MaxMaePts;
        public int MinsToMaxMfe = -1, MinsToMaxMae = -1;
        public double MaxMfeR = double.NaN, MaxMaeR = double.NaN;

        public int MinutesObserved;
        public bool WindowComplete;

        public readonly V4StopSet Stops = new V4StopSet();
        public V4RRace[] Races;                 // RGrid x the chosen stop
        public V4StopKind RaceStop = V4StopKind.MEDIUM;

        public V4Target TargetVectorZone = V4Target.None();
        public V4Target TargetLiquidity = V4Target.None();
        public V4Target TargetSwing = V4Target.None();
        public V4Target TargetHtfStruct = V4Target.None();
        public V4Target TargetSession = V4Target.None();

        public bool HitTargetVectorZone, HitTargetLiquidity, HitTargetSwing;
        public bool HitTargetHtfStruct, HitTargetSession;
        public int MinsToTargetVectorZone = -1, MinsToTargetLiquidity = -1;
        public int MinsToTargetSwing = -1, MinsToTargetHtfStruct = -1, MinsToTargetSession = -1;

        /// Vector-zone recovery objectives, all emitted rather than one
        /// chosen. Picking the best percentage in engine code would be
        /// choosing an answer before the question was asked.
        public bool HitVecFirstTouch, HitVec25, HitVec50, HitVecBodyEdge, HitVec100;
        public int MinsToVec50 = -1, MinsToVec100 = -1;

        public readonly V4EmaExitProbe EmaExit = new V4EmaExitProbe();

        private int barsSeen;
        private double runMaxHigh = double.NaN, runMinLow = double.NaN;

        public V4ForwardLabels()
        {
            for (int i = 0; i < Horizons.Length; i++)
            { Net[i] = double.NaN; Mfe[i] = double.NaN; Mae[i] = double.NaN; }
            Races = new V4RRace[RGrid.Length];
            for (int i = 0; i < RGrid.Length; i++)
            {
                Races[i] = new V4RRace();
                Races[i].Multiple = RGrid[i];
            }
        }

        public void Open(int side, double entryPrice, DateTime entryEt, double atr, double ema9AtEntry)
        {
            Side = side; EntryPrice = entryPrice; EntryEt = entryEt; AtrAtEntry = atr;
            barsSeen = 0; MinutesObserved = 0; WindowComplete = false;
            MaxMfePts = 0; MaxMaePts = 0;
            runMaxHigh = entryPrice; runMinLow = entryPrice;
            EmaExit.Open(side, entryPrice, entryEt, Stops.PtsFor(RaceStop), ema9AtEntry);
        }

        /// Fold one COMPLETED 1-minute bar strictly after the entry bar.
        public void OnBar(V4Bar b, double ema9_1m)
        {
            if (WindowComplete) return;
            if (b.EtClose <= EntryEt) return;

            barsSeen++;
            MinutesObserved = barsSeen;

            if (b.High > runMaxHigh || double.IsNaN(runMaxHigh)) runMaxHigh = b.High;
            if (b.Low < runMinLow || double.IsNaN(runMinLow)) runMinLow = b.Low;

            double mfe = Side > 0 ? b.High - EntryPrice : EntryPrice - b.Low;
            double mae = Side > 0 ? EntryPrice - b.Low : b.High - EntryPrice;
            if (mfe > MaxMfePts) { MaxMfePts = mfe; MinsToMaxMfe = barsSeen; }
            if (mae > MaxMaePts) { MaxMaePts = mae; MinsToMaxMae = barsSeen; }

            for (int i = 0; i < Horizons.Length; i++)
            {
                if (barsSeen != Horizons[i]) continue;
                Net[i] = Side > 0 ? b.Close - EntryPrice : EntryPrice - b.Close;
                Mfe[i] = MaxMfePts;
                Mae[i] = MaxMaePts;
            }

            ResolveStops(b);
            ResolveRaces(b);
            ResolveTargets(b);
            EmaExit.OnBar(b, ema9_1m);

            if (barsSeen >= Horizons[Horizons.Length - 1])
            {
                WindowComplete = true;
                double denom = Stops.PtsFor(RaceStop);
                MaxMfeR = V4Num.SafeDiv(MaxMfePts, denom, 1e-9);
                MaxMaeR = V4Num.SafeDiv(MaxMaePts, denom, 1e-9);
            }
        }

        private void ResolveStops(V4Bar b)
        {
            Check(V4StopKind.TIGHT, b, ref Stops.HitTight, ref Stops.MinsToTight);
            Check(V4StopKind.MEDIUM, b, ref Stops.HitMedium, ref Stops.MinsToMedium);
            Check(V4StopKind.STRUCTURAL, b, ref Stops.HitStructural, ref Stops.MinsToStructural);

            // did the reference target arrive only AFTER the stop?
            V4Target t = ReferenceTarget();
            if (t.Valid)
            {
                bool reached = Side > 0 ? b.High >= t.Price : b.Low <= t.Price;
                if (reached)
                {
                    if (Stops.HitTight && Stops.MinsToTight >= 0 && barsSeen > Stops.MinsToTight)
                        Stops.TargetReachedAfterTight = true;
                    if (Stops.HitMedium && Stops.MinsToMedium >= 0 && barsSeen > Stops.MinsToMedium)
                        Stops.TargetReachedAfterMedium = true;
                    if (Stops.HitStructural && Stops.MinsToStructural >= 0 && barsSeen > Stops.MinsToStructural)
                        Stops.TargetReachedAfterStructural = true;
                }
            }
        }

        private void Check(V4StopKind k, V4Bar b, ref bool hit, ref int mins)
        {
            if (hit) return;
            double p = Stops.PriceFor(k);
            if (!V4Num.Ok(p)) return;
            bool touched = Side > 0 ? b.Low <= p : b.High >= p;
            if (touched) { hit = true; mins = barsSeen; }
        }

        /// The R races, and the only place in the package that is allowed
        /// to answer "we cannot tell".
        private void ResolveRaces(V4Bar b)
        {
            double stopPts = Stops.PtsFor(RaceStop);
            double stopPrice = Stops.PriceFor(RaceStop);
            if (!V4Num.Ok(stopPts) || stopPts <= 0 || !V4Num.Ok(stopPrice)) return;

            bool stopTouched = Side > 0 ? b.Low <= stopPrice : b.High >= stopPrice;

            for (int i = 0; i < Races.Length; i++)
            {
                V4RRace r = Races[i];
                if (r.Outcome != V4RaceOutcome.UNRESOLVED) continue;

                double tgt = Side > 0
                    ? EntryPrice + r.Multiple * stopPts
                    : EntryPrice - r.Multiple * stopPts;
                bool tgtTouched = Side > 0 ? b.High >= tgt : b.Low <= tgt;

                if (tgtTouched && stopTouched)
                {
                    // one bar reached both. OHLC cannot order them and this
                    // engine will not pretend otherwise.
                    r.Outcome = V4RaceOutcome.AMBIGUOUS;
                    r.MinsToResolve = barsSeen;
                    r.WouldWinIfTargetFirst = true;
                    r.WouldLoseIfStopFirst = true;
                }
                else if (tgtTouched)
                {
                    r.Outcome = V4RaceOutcome.TARGET; r.MinsToResolve = barsSeen;
                    r.WouldWinIfTargetFirst = true;
                }
                else if (stopTouched)
                {
                    r.Outcome = V4RaceOutcome.STOP; r.MinsToResolve = barsSeen;
                    r.WouldLoseIfStopFirst = true;
                }
            }
        }

        private void ResolveTargets(V4Bar b)
        {
            Hit(TargetVectorZone, b, ref HitTargetVectorZone, ref MinsToTargetVectorZone);
            Hit(TargetLiquidity, b, ref HitTargetLiquidity, ref MinsToTargetLiquidity);
            Hit(TargetSwing, b, ref HitTargetSwing, ref MinsToTargetSwing);
            Hit(TargetHtfStruct, b, ref HitTargetHtfStruct, ref MinsToTargetHtfStruct);
            Hit(TargetSession, b, ref HitTargetSession, ref MinsToTargetSession);
        }

        private void Hit(V4Target t, V4Bar b, ref bool hit, ref int mins)
        {
            if (hit || !t.Valid) return;
            bool reached = Side > 0 ? b.High >= t.Price : b.Low <= t.Price;
            if (reached) { hit = true; mins = barsSeen; }
        }

        private V4Target ReferenceTarget()
        {
            if (TargetSwing.Valid) return TargetSwing;
            if (TargetVectorZone.Valid) return TargetVectorZone;
            if (TargetLiquidity.Valid) return TargetLiquidity;
            if (TargetHtfStruct.Valid) return TargetHtfStruct;
            return TargetSession;
        }

        /// Count of races this probe could not resolve. A high rate here is
        /// a signal that the study needs finer bars, not that the edge is
        /// real.
        public int AmbiguousRaceCount()
        {
            int n = 0;
            for (int i = 0; i < Races.Length; i++)
                if (Races[i].Outcome == V4RaceOutcome.AMBIGUOUS) n++;
            return n;
        }

        public static string OutcomeName(V4RaceOutcome o)
        {
            switch (o)
            {
                case V4RaceOutcome.TARGET: return "TARGET";
                case V4RaceOutcome.STOP: return "STOP";
                case V4RaceOutcome.AMBIGUOUS: return "AMBIGUOUS";
                case V4RaceOutcome.TIMEOUT: return "TIMEOUT";
            }
            return "UNRESOLVED";
        }

        /// Close the window at end of data, marking unresolved races TIMEOUT
        /// rather than leaving them looking unfinished.
        public void CloseWindow()
        {
            for (int i = 0; i < Races.Length; i++)
                if (Races[i].Outcome == V4RaceOutcome.UNRESOLVED)
                    Races[i].Outcome = V4RaceOutcome.TIMEOUT;
            WindowComplete = true;
            double denom = Stops.PtsFor(RaceStop);
            MaxMfeR = V4Num.SafeDiv(MaxMfePts, denom, 1e-9);
            MaxMaeR = V4Num.SafeDiv(MaxMaePts, denom, 1e-9);
        }
    }
}
