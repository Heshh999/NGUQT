// ======================================================================
// V4VectorEngine.cs  -  MNQ V4.1
// ======================================================================
// Traders Reality / PVSRA vector classification and everything built on
// top of it: vector zones, causal recovery state, W / M formations,
// trap candidates, repeated-push candidates, and the trigger-vector tag.
//
// THIS FILE SUBMITS NO ORDERS.
//
// The one thing to be clear about before reading any of it:
//
//   VECTOR COLOUR IS NOT A TRADING DIRECTION.
//
// A red vector is not a short. A green vector is not a long. Colour is an
// activity classification - how much volume traded, and whether the bar
// closed up or down. Whether that carries information is the question the
// research layer answers, and V4.1's own measured history says the prior
// should be low. Nothing in this file assumes otherwise, and no method
// here returns a trade direction.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public enum V4VectorColor { NONE, GREEN, RED, BLUE, VIOLET }
    public enum V4VectorTier { NONE, CLIMAX, ELEVATED }
    public enum V4VectorDir { NONE, BULLISH, BEARISH }

    /// How far price has traded back into a vector's zone. Ordered, so a
    /// later state implies every earlier one was reached.
    public enum V4VectorRecovery
    {
        UNRECOVERED,
        FIRST_TOUCH,
        RECOVERED_25,
        RECOVERED_50,
        RECOVERED_BODY_EDGE,
        RECOVERED_75,
        RECOVERED_100
    }

    public enum V4Formation { NONE, W, M }

    // ==================================================================
    // CLASSIFICATION
    // ==================================================================

    /// The canonical PVSRA rule, carried over unchanged from this project's
    /// existing implementation rather than reinvented. Documented here in
    /// full because the prompt requires the formula, lookback, thresholds
    /// and colour assignment to be stated before any code depends on them.
    ///
    ///   lookback           : the 10 PREVIOUS completed bars
    ///   avgVol10           : mean(volume[1..10])
    ///   highestVolSpread10 : max over i in 1..10 of volume[i] * (high[i]-low[i])
    ///   bullish            : close > open. A doji (close == open) follows
    ///                        the BEARISH branch - stated because it is the
    ///                        one genuinely arbitrary choice in the rule.
    ///
    ///   CLIMAX   : volume >= 2.0 * avgVol10  OR  volume*(high-low) >= highestVolSpread10
    ///              -> GREEN if bullish, RED if bearish
    ///   ELEVATED : volume >= 1.5 * avgVol10
    ///              -> BLUE if bullish, VIOLET if bearish
    ///   otherwise: not a vector
    ///
    /// Climax is tested first and wins outright, so an elevated-volume bar
    /// that also sets a new volume*spread high is GREEN or RED, never BLUE
    /// or VIOLET.
    public static class V4VectorClassifier
    {
        public const double ClimaxVolumeMult = 2.0;
        public const double ElevatedVolumeMult = 1.5;
        public const int Lookback = 10;

        public static V4VectorColor Classify(double open, double high, double low, double close,
                                             double volume, double avgVol10, double highestVolSpread10)
        {
            if (!V4Num.Ok(volume) || !V4Num.Ok(avgVol10) || avgVol10 <= 0) return V4VectorColor.NONE;

            bool bullish = close > open;
            double volumeSpread = volume * (high - low);

            if (volume >= ClimaxVolumeMult * avgVol10
                || (V4Num.Ok(highestVolSpread10) && highestVolSpread10 > 0 && volumeSpread >= highestVolSpread10))
                return bullish ? V4VectorColor.GREEN : V4VectorColor.RED;

            if (volume >= ElevatedVolumeMult * avgVol10)
                return bullish ? V4VectorColor.BLUE : V4VectorColor.VIOLET;

            return V4VectorColor.NONE;
        }

        public static V4VectorTier TierOf(V4VectorColor c)
        {
            if (c == V4VectorColor.GREEN || c == V4VectorColor.RED) return V4VectorTier.CLIMAX;
            if (c == V4VectorColor.BLUE || c == V4VectorColor.VIOLET) return V4VectorTier.ELEVATED;
            return V4VectorTier.NONE;
        }

        /// The bar's own up/down classification. This is NOT a trade
        /// direction and must never be used as one.
        public static V4VectorDir DirOf(V4VectorColor c)
        {
            if (c == V4VectorColor.GREEN || c == V4VectorColor.BLUE) return V4VectorDir.BULLISH;
            if (c == V4VectorColor.RED || c == V4VectorColor.VIOLET) return V4VectorDir.BEARISH;
            return V4VectorDir.NONE;
        }

        public static bool IsVector(V4VectorColor c) { return c != V4VectorColor.NONE; }
    }

    // ==================================================================
    // A SINGLE VECTOR AND ITS ZONE
    // ==================================================================

    /// One vector candle, its frozen zone geometry, and the causal record
    /// of how far price has since traded back into it.
    ///
    /// Zone convention, fixed before any outcome was examined so that it
    /// cannot be chosen after the fact:
    ///
    ///   A BEARISH vector's zone is measured from its LOW. 0% recovered
    ///   means price has not come back up at all; 100% means price has
    ///   traded back to the vector's HIGH.
    ///
    ///   A BULLISH vector's zone is mirrored: 0% at its HIGH, 100% when
    ///   price has traded back down to its LOW.
    ///
    /// "Body edge" is the body boundary on the recovery side - the open for
    /// a bearish vector, the close for a bullish one - so it always sits
    /// between the 0% and 100% edges.
    public class V4Vector
    {
        public string VectorId = "";
        public string Tf = "";
        public int TfMinutes;
        public DateTime CreatedEt;

        public V4VectorColor Color;
        public V4VectorTier Tier;
        public V4VectorDir Dir;

        public double Open, High, Low, Close, Volume;
        public double BodyHigh, BodyLow;
        public double RelVolume;
        public double RangePts;
        public double VolumeXRange;
        public double AtrAtCreation;

        // structural relation, all judged at creation from causally known swings
        public bool TookSwingHigh, TookSwingLow;
        public bool BrokeStructure, WickedBeyondStructure, ClosedBeyondStructure;

        // causal recovery record
        public V4VectorRecovery Recovery = V4VectorRecovery.UNRECOVERED;
        public double RecoveryPct;                 // 0..100, monotone high-water mark
        public DateTime FirstTouchEt = DateTime.MinValue;
        public DateTime Recovered50Et = DateTime.MinValue;
        public DateTime RecoveredFullEt = DateTime.MinValue;
        public int BarsTo25 = -1, BarsTo50 = -1, BarsTo100 = -1;
        public int AgeBars;

        // trap candidacy, resolved from later bars - this is a LABEL
        public bool TrapCandidate;
        public double TrapRetracePct;
        public bool TrapSwift50;
        public bool TrapReturnedInsideOrigin;

        public bool IsBearish { get { return Dir == V4VectorDir.BEARISH; } }

        /// Price at a given recovery percentage of this vector's zone.
        public double PriceAtRecoveryPct(double pct)
        {
            double span = High - Low;
            if (!V4Num.Ok(span) || span <= 0) return double.NaN;
            double f = pct / 100.0;
            return IsBearish ? Low + span * f : High - span * f;
        }

        /// The 0%-recovered edge: where price left the vector behind.
        public double OriginEdge { get { return IsBearish ? Low : High; } }
        /// The 100%-recovered edge.
        public double FarEdge { get { return IsBearish ? High : Low; } }
        /// Body boundary on the recovery side.
        public double BodyEdge { get { return IsBearish ? BodyLow : BodyHigh; } }

        public double BodyEdgePct
        {
            get
            {
                double span = High - Low;
                if (!V4Num.Ok(span) || span <= 0) return double.NaN;
                return IsBearish ? (BodyEdge - Low) / span * 100.0 : (High - BodyEdge) / span * 100.0;
            }
        }

        /// Fold one later completed bar in and advance the recovery
        /// high-water mark. Monotone by construction: recovery never
        /// un-happens, which is what makes the state reproducible.
        public void ApplyLaterBar(V4Bar b, int barsSinceCreation)
        {
            AgeBars = barsSinceCreation;
            double span = High - Low;
            if (!V4Num.Ok(span) || span <= 0) return;

            double reached = IsBearish
                ? (b.High - Low) / span * 100.0      // bearish recovers upward
                : (High - b.Low) / span * 100.0;     // bullish recovers downward
            if (!V4Num.Ok(reached)) return;
            if (reached < 0) reached = 0;
            if (reached > 100) reached = 100;
            if (reached <= RecoveryPct) return;

            RecoveryPct = reached;
            if (FirstTouchEt == DateTime.MinValue && reached > 0)
            {
                FirstTouchEt = b.EtClose;
                if (Recovery < V4VectorRecovery.FIRST_TOUCH) Recovery = V4VectorRecovery.FIRST_TOUCH;
            }
            if (reached >= 25 && BarsTo25 < 0) BarsTo25 = barsSinceCreation;
            if (reached >= 50 && BarsTo50 < 0) { BarsTo50 = barsSinceCreation; Recovered50Et = b.EtClose; }
            if (reached >= 100 && BarsTo100 < 0) { BarsTo100 = barsSinceCreation; RecoveredFullEt = b.EtClose; }

            // Pick the state by the HIGHEST threshold actually passed.
            //
            // The body edge sits at a VARIABLE percentage of the zone: for a
            // vector that closed on its own extreme it is 0%. An if/else
            // ladder that tested it before the fixed thresholds therefore let
            // an 8% retrace report RECOVERED_BODY_EDGE, which is both wrong
            // and flattering. Making every threshold compete on its real
            // position is what fixes it.
            double be = BodyEdgePct;
            V4VectorRecovery r = V4VectorRecovery.FIRST_TOUCH;
            double bestThr = 0.0;
            if (reached >= 25 && 25 > bestThr) { bestThr = 25; r = V4VectorRecovery.RECOVERED_25; }
            if (reached >= 50 && 50 > bestThr) { bestThr = 50; r = V4VectorRecovery.RECOVERED_50; }
            if (V4Num.Ok(be) && be > 0 && reached >= be && be > bestThr)
            { bestThr = be; r = V4VectorRecovery.RECOVERED_BODY_EDGE; }
            if (reached >= 75 && 75 > bestThr) { bestThr = 75; r = V4VectorRecovery.RECOVERED_75; }
            if (reached >= 100 && 100 > bestThr) { bestThr = 100; r = V4VectorRecovery.RECOVERED_100; }
            if (r > Recovery) Recovery = r;
        }

        public bool IsUnrecovered { get { return Recovery == V4VectorRecovery.UNRECOVERED; } }
    }

    // ==================================================================
    // W / M FORMATION
    // ==================================================================

    /// A W or M built only from CONFIRMED swings. Nothing is recognised
    /// before its required pivots are knowable, which is why the engine
    /// takes swings from V4StructureTracker's KnownAt queries rather than
    /// reading pivots directly off the bar array.
    ///
    ///   W : low -> high -> low, second low within EqualityTolAtr of the
    ///       first or above it. Neckline is the middle high.
    ///   M : high -> low -> high, second high within tolerance of the first
    ///       or below it. Neckline is the middle low.
    public class V4FormationState
    {
        public V4Formation Type = V4Formation.NONE;
        public DateTime StartEt = DateTime.MinValue;
        public double FirstLegExtreme = double.NaN;
        public double MiddlePivot = double.NaN;
        public double SecondLegExtreme = double.NaN;
        public double Neckline = double.NaN;
        public bool SecondLegConfirmed;
        public bool BreakConfirmed;
        public bool RetestConfirmed;
        public bool Invalidated;
        public DateTime SecondLegEt = DateTime.MinValue;
        public int BarsSinceStart = -1;
        public int BarsSinceSecondLeg = -1;

        public void Clear()
        {
            Type = V4Formation.NONE; StartEt = DateTime.MinValue;
            FirstLegExtreme = MiddlePivot = SecondLegExtreme = Neckline = double.NaN;
            SecondLegConfirmed = BreakConfirmed = RetestConfirmed = Invalidated = false;
            SecondLegEt = DateTime.MinValue; BarsSinceStart = -1; BarsSinceSecondLeg = -1;
        }
    }

    // ==================================================================
    // THE ENGINE - ONE PER TIMEFRAME
    // ==================================================================

    public class V4VectorEngine
    {
        // ---- configuration, all declared rather than tuned -------------
        public int MaxVectorsTracked = 400;
        /// A vector must be at least this many ATR wide to be a trap candidate.
        public double TrapMinRangeAtr = 1.0;
        /// Retracement of the vector's own range that makes it a trap candidate.
        public double TrapRetracePct = 50.0;
        /// Bars within which that retracement counts as "swift".
        public int TrapSwiftBars = 3;
        /// Window over which repeated same-direction vectors are counted.
        public int PushWindowBars = 10;
        /// Net progress below this many ATR across the window is "no progress".
        public double PushPoorProgressAtr = 0.5;
        public double EqualityTolAtr = 0.15;

        private readonly string tf;
        private readonly int tfMinutes;
        private readonly string symbol;

        private readonly List<V4Bar> bars = new List<V4Bar>();
        private readonly List<V4Vector> vectors = new List<V4Vector>();
        private readonly List<V4Vector> live = new List<V4Vector>();   // not yet fully recovered

        private V4VectorColor lastColor = V4VectorColor.NONE;
        private V4VectorColor prevColor = V4VectorColor.NONE;
        private int sameDirRun;

        public readonly V4FormationState Formation = new V4FormationState();

        public V4VectorEngine(string symbolIn, string label, int minutesPerBar)
        {
            symbol = symbolIn; tf = label; tfMinutes = minutesPerBar;
        }

        public string Tf { get { return tf; } }
        public int BarCount { get { return bars.Count; } }
        public V4VectorColor LastColor { get { return lastColor; } }
        public V4VectorColor PrevColor { get { return prevColor; } }
        public int SameDirectionRun { get { return sameDirRun; } }

        // ---- the per-bar entry point ----------------------------------

        /// Fold one COMPLETED bar of this timeframe in. Returns the vector
        /// created by this bar, or null when the bar was not a vector.
        ///
        /// Order matters and is deliberate: existing vectors are advanced
        /// with this bar BEFORE the bar is classified, so a vector can
        /// never recover itself on the bar that created it.
        public V4Vector OnBar(V4Bar b, double atr, V4Swing knownHigh, V4Swing knownLow,
                              V4Swing priorHigh, V4Swing priorLow)
        {
            AdvanceRecovery(b);

            bars.Add(b);
            if (bars.Count > 5000) bars.RemoveAt(0);

            double avgVol10, hiVolSpread10;
            if (!PriorVolumeStats(out avgVol10, out hiVolSpread10))
            {
                prevColor = lastColor; lastColor = V4VectorColor.NONE; sameDirRun = 0;
                return null;
            }

            V4VectorColor c = V4VectorClassifier.Classify(b.Open, b.High, b.Low, b.Close,
                                                          b.Volume, avgVol10, hiVolSpread10);
            V4VectorDir dir = V4VectorClassifier.DirOf(c);
            V4VectorDir prevDir = V4VectorClassifier.DirOf(lastColor);
            sameDirRun = (dir != V4VectorDir.NONE && dir == prevDir) ? sameDirRun + 1 : (dir == V4VectorDir.NONE ? 0 : 1);
            prevColor = lastColor; lastColor = c;

            UpdateFormation(knownHigh, knownLow, priorHigh, priorLow, atr, b);

            if (c == V4VectorColor.NONE) return null;

            V4Vector v = new V4Vector();
            v.VectorId = symbol + "-" + tf + "-V-" + b.EtClose.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture);
            v.Tf = tf; v.TfMinutes = tfMinutes; v.CreatedEt = b.EtClose;
            v.Color = c; v.Tier = V4VectorClassifier.TierOf(c); v.Dir = dir;
            v.Open = b.Open; v.High = b.High; v.Low = b.Low; v.Close = b.Close; v.Volume = b.Volume;
            v.BodyHigh = Math.Max(b.Open, b.Close);
            v.BodyLow = Math.Min(b.Open, b.Close);
            v.RangePts = b.High - b.Low;
            v.VolumeXRange = b.Volume * v.RangePts;
            v.RelVolume = V4Num.SafeDiv(b.Volume, avgVol10, 1e-9);
            v.AtrAtCreation = atr;

            // structural relation, judged only from swings already knowable
            if (knownHigh.Valid)
            {
                v.TookSwingHigh = b.High > knownHigh.Price;
                if (v.TookSwingHigh)
                {
                    v.ClosedBeyondStructure = b.Close > knownHigh.Price;
                    v.WickedBeyondStructure = !v.ClosedBeyondStructure;
                    v.BrokeStructure = true;
                }
            }
            if (knownLow.Valid)
            {
                v.TookSwingLow = b.Low < knownLow.Price;
                if (v.TookSwingLow)
                {
                    bool closedBelow = b.Close < knownLow.Price;
                    v.ClosedBeyondStructure = v.ClosedBeyondStructure || closedBelow;
                    if (!closedBelow) v.WickedBeyondStructure = true;
                    v.BrokeStructure = true;
                }
            }

            vectors.Add(v);
            live.Add(v);
            if (vectors.Count > MaxVectorsTracked) vectors.RemoveAt(0);
            TrimLive();
            return v;
        }

        /// Advance every live vector with a newly completed bar and resolve
        /// trap candidacy. Trap status needs later bars, so it is a LABEL.
        private void AdvanceRecovery(V4Bar b)
        {
            for (int i = 0; i < live.Count; i++)
            {
                V4Vector v = live[i];
                if (b.EtClose <= v.CreatedEt) continue;
                int age = v.AgeBars + 1;
                v.ApplyLaterBar(b, age);

                if (!v.TrapCandidate && V4Num.Ok(v.AtrAtCreation) && v.AtrAtCreation > 0)
                {
                    double rangeAtr = v.RangePts / v.AtrAtCreation;
                    if (rangeAtr >= TrapMinRangeAtr && v.RecoveryPct >= TrapRetracePct)
                    {
                        v.TrapCandidate = true;
                        v.TrapRetracePct = v.RecoveryPct;
                        v.TrapSwift50 = (v.BarsTo50 >= 0 && v.BarsTo50 <= TrapSwiftBars);
                        v.TrapReturnedInsideOrigin = v.RecoveryPct >= 100.0;
                    }
                }
            }
            TrimLive();
        }

        private void TrimLive()
        {
            for (int i = live.Count - 1; i >= 0; i--)
                if (live[i].Recovery == V4VectorRecovery.RECOVERED_100) live.RemoveAt(i);
            while (live.Count > MaxVectorsTracked) live.RemoveAt(0);
        }

        /// Mean volume and max volume*spread over the 10 bars BEFORE the one
        /// just added. Returns false until 11 bars exist, which keeps an
        /// unformed baseline from classifying anything.
        private bool PriorVolumeStats(out double avgVol10, out double hiVolSpread10)
        {
            avgVol10 = double.NaN; hiVolSpread10 = double.NaN;
            int n = bars.Count;
            if (n < V4VectorClassifier.Lookback + 1) return false;
            double sum = 0, mx = 0;
            for (int i = n - 1 - V4VectorClassifier.Lookback; i <= n - 2; i++)
            {
                V4Bar p = bars[i];
                sum += p.Volume;
                double vs = p.Volume * (p.High - p.Low);
                if (vs > mx) mx = vs;
            }
            avgVol10 = sum / V4VectorClassifier.Lookback;
            hiVolSpread10 = mx;
            return avgVol10 > 0;
        }

        // ---- queries used by the recorder ------------------------------

        /// Nearest unrecovered vector zone strictly above a price.
        public V4Vector NearestUnrecoveredAbove(double price, DateTime cutoffEt)
        {
            V4Vector best = null; double bestD = double.MaxValue;
            for (int i = 0; i < live.Count; i++)
            {
                V4Vector v = live[i];
                if (v.CreatedEt > cutoffEt) continue;
                double edge = v.FarEdge;
                if (!V4Num.Ok(edge) || edge <= price) continue;
                double d = edge - price;
                if (d < bestD) { bestD = d; best = v; }
            }
            return best;
        }

        public V4Vector NearestUnrecoveredBelow(double price, DateTime cutoffEt)
        {
            V4Vector best = null; double bestD = double.MaxValue;
            for (int i = 0; i < live.Count; i++)
            {
                V4Vector v = live[i];
                if (v.CreatedEt > cutoffEt) continue;
                double edge = v.FarEdge;
                if (!V4Num.Ok(edge) || edge >= price) continue;
                double d = price - edge;
                if (d < bestD) { bestD = d; best = v; }
            }
            return best;
        }

        /// Most recent vector knowable at the cutoff.
        public V4Vector LatestKnownAt(DateTime cutoffEt)
        {
            for (int i = vectors.Count - 1; i >= 0; i--)
                if (vectors[i].CreatedEt <= cutoffEt) return vectors[i];
            return null;
        }

        /// Zones still open - created, knowable, and not yet fully recovered.
        ///
        /// This deliberately matches what NearestUnrecoveredAbove/Below
        /// iterate. The previous version used the STRICT never-touched
        /// definition instead, and since AdvanceRecovery marks FIRST_TOUCH on
        /// any bar that grazes the zone, the count was 0 on all 659 rows of
        /// the first clean sample - which made H5, a Class A hypothesis about
        /// unrecovered zones, untestable from the data it depended on.
        public int UnrecoveredCount(DateTime cutoffEt)
        {
            int n = 0;
            for (int i = 0; i < live.Count; i++)
                if (live[i].CreatedEt <= cutoffEt) n++;
            return n;
        }

        /// The strict reading: created, knowable, and never touched at all.
        /// Kept because it is a different and also meaningful question.
        public int UntouchedCount(DateTime cutoffEt)
        {
            int n = 0;
            for (int i = 0; i < live.Count; i++)
                if (live[i].CreatedEt <= cutoffEt && live[i].IsUnrecovered) n++;
            return n;
        }

        // ---- repeated-push state ---------------------------------------

        /// Repeated same-direction vector aggression with poor net progress.
        /// Descriptive only. Public material discusses this qualitatively
        /// without publishing mechanics, so this is our declared translation
        /// and it carries the HEURISTIC-adjacent ADAPTED source class.
        ///
        /// It does NOT mean reversal. Continuation and failure are both live
        /// branches and only the research layer may separate them.
        public void PushState(DateTime cutoffEt, double atr,
                              out int pushCount, out V4VectorDir dir,
                              out double netProgressAtr, out double totalRangeAtr,
                              out bool poorProgress)
        {
            pushCount = 0; dir = V4VectorDir.NONE;
            netProgressAtr = double.NaN; totalRangeAtr = double.NaN; poorProgress = false;

            int n = bars.Count;
            if (n < 2 || !V4Num.Ok(atr) || atr <= 0) return;

            int from = Math.Max(0, n - PushWindowBars);
            double firstClose = double.NaN, lastClose = double.NaN, totalRange = 0;
            int bull = 0, bear = 0;

            for (int i = from; i < n; i++)
            {
                if (bars[i].EtClose > cutoffEt) break;
                if (!V4Num.Ok(firstClose)) firstClose = bars[i].Open;
                lastClose = bars[i].Close;
            }
            for (int i = 0; i < vectors.Count; i++)
            {
                V4Vector v = vectors[i];
                if (v.CreatedEt > cutoffEt) continue;
                if (n - from <= 0) continue;
                if (bars[from].EtClose > v.CreatedEt) continue;
                pushCount++;
                totalRange += v.RangePts;
                if (v.Dir == V4VectorDir.BULLISH) bull++; else if (v.Dir == V4VectorDir.BEARISH) bear++;
            }
            if (pushCount == 0) return;
            dir = bull > bear ? V4VectorDir.BULLISH : (bear > bull ? V4VectorDir.BEARISH : V4VectorDir.NONE);
            netProgressAtr = V4Num.SafeDiv(lastClose - firstClose, atr, 1e-9);
            totalRangeAtr = V4Num.SafeDiv(totalRange, atr, 1e-9);
            poorProgress = V4Num.Ok(netProgressAtr) && Math.Abs(netProgressAtr) < PushPoorProgressAtr && pushCount >= 2;
        }

        // ---- W / M -----------------------------------------------------

        /// Rebuild the formation from the last THREE confirmed swings, every
        /// bar, from scratch.
        ///
        /// The previous version was stateful and only re-seeded when the
        /// formation was NONE or invalidated - so once an M was confirmed it
        /// stuck forever. The first clean sample proved it: across 659 rows
        /// spanning two months, formationStartEt and formationNeckline each
        /// had exactly ONE distinct value, and no W was ever produced at all.
        ///
        /// Re-deriving from the swings themselves cannot get stuck, because
        /// it carries no memory to get stuck in.
        ///
        ///   ends on a HIGH -> M candidate: priorHigh, latestLow, latestHigh
        ///   ends on a LOW  -> W candidate: priorLow,  latestHigh, latestLow
        ///
        /// Break and retest DO need memory - they are about what price did
        /// after the shape completed - so those are the only carried fields,
        /// and they reset whenever the shape's own pivots change.
        private void UpdateFormation(V4Swing knownHigh, V4Swing knownLow,
                                     V4Swing priorHigh, V4Swing priorLow, double atr, V4Bar b)
        {
            if (!knownHigh.Valid || !knownLow.Valid || !V4Num.Ok(atr) || atr <= 0) return;

            double tol = EqualityTolAtr * atr;
            bool endsOnHigh = knownHigh.KnownAtEt >= knownLow.KnownAtEt;

            V4Formation type = V4Formation.NONE;
            double first = double.NaN, mid = double.NaN, second = double.NaN;
            DateTime startEt = DateTime.MinValue, secondEt = DateTime.MinValue;
            bool secondConfirmed = false;

            if (endsOnHigh && priorHigh.Valid
                && priorHigh.KnownAtEt <= knownLow.KnownAtEt
                && knownLow.KnownAtEt <= knownHigh.KnownAtEt)
            {
                type = V4Formation.M;
                first = priorHigh.Price; mid = knownLow.Price; second = knownHigh.Price;
                startEt = priorHigh.KnownAtEt; secondEt = knownHigh.KnownAtEt;
                // the second high must not exceed the first by more than tolerance
                secondConfirmed = second <= first + tol;
            }
            else if (!endsOnHigh && priorLow.Valid
                     && priorLow.KnownAtEt <= knownHigh.KnownAtEt
                     && knownHigh.KnownAtEt <= knownLow.KnownAtEt)
            {
                type = V4Formation.W;
                first = priorLow.Price; mid = knownHigh.Price; second = knownLow.Price;
                startEt = priorLow.KnownAtEt; secondEt = knownLow.KnownAtEt;
                // the second low must not undercut the first by more than tolerance
                secondConfirmed = second >= first - tol;
            }

            bool shapeChanged = Formation.Type != type
                             || Formation.StartEt != startEt
                             || Formation.SecondLegEt != secondEt;

            if (shapeChanged)
            {
                Formation.Clear();
                Formation.Type = type;
                Formation.StartEt = startEt;
                Formation.FirstLegExtreme = first;
                Formation.MiddlePivot = mid;
                Formation.SecondLegExtreme = second;
                Formation.SecondLegEt = secondEt;
                Formation.SecondLegConfirmed = secondConfirmed;
                Formation.Neckline = secondConfirmed ? mid : double.NaN;
                Formation.Invalidated = (type != V4Formation.NONE) && !secondConfirmed;
            }

            if (Formation.Type == V4Formation.NONE) return;

            // break and retest, judged from bars AFTER the shape completed
            if (Formation.SecondLegConfirmed && V4Num.Ok(Formation.Neckline))
            {
                if (!Formation.BreakConfirmed)
                {
                    if (Formation.Type == V4Formation.W && b.Close > Formation.Neckline)
                        Formation.BreakConfirmed = true;
                    else if (Formation.Type == V4Formation.M && b.Close < Formation.Neckline)
                        Formation.BreakConfirmed = true;
                }
                else if (!Formation.RetestConfirmed)
                {
                    if (Formation.Type == V4Formation.W && b.Low <= Formation.Neckline)
                        Formation.RetestConfirmed = true;
                    else if (Formation.Type == V4Formation.M && b.High >= Formation.Neckline)
                        Formation.RetestConfirmed = true;
                }
            }

            if (Formation.StartEt != DateTime.MinValue)
                Formation.BarsSinceStart = CountBarsSince(Formation.StartEt);
            if (Formation.SecondLegEt != DateTime.MinValue)
                Formation.BarsSinceSecondLeg = CountBarsSince(Formation.SecondLegEt);
        }

        private int CountBarsSince(DateTime et)
        {
            int n = 0;
            for (int i = bars.Count - 1; i >= 0; i--) { if (bars[i].EtClose <= et) break; n++; }
            return n;
        }

        /// Does a completed vector break away from the frozen W/M boundary?
        /// Mechanical and declared: the vector's CLOSE must be beyond the
        /// neckline in the formation's own direction. Note the prompt's own
        /// caution - a vector is NOT required to exit a W/M for the setup to
        /// be tradeable. That is a hypothesis, not a gate.
        public bool VectorExitsFormation(V4Vector v)
        {
            if (v == null || Formation.Type == V4Formation.NONE || !V4Num.Ok(Formation.Neckline)) return false;
            if (Formation.Type == V4Formation.W) return v.Close > Formation.Neckline;
            return v.Close < Formation.Neckline;
        }

        // ---- trigger vector --------------------------------------------

        /// Descriptive tag for a vector forming around structure and the
        /// 50 EMA. Public material discusses a "trigger candle" without
        /// publishing mechanics, so this records the relationship and makes
        /// no claim about what follows.
        public static void TriggerVectorContext(V4Vector v, double ema50, double prevClose,
                                                out bool failedToBreak, out bool held,
                                                out bool broke, out bool reclaimed)
        {
            failedToBreak = held = broke = reclaimed = false;
            if (v == null || !V4Num.Ok(ema50)) return;

            if (v.Dir == V4VectorDir.BULLISH)
            {
                broke = v.Close > ema50 && prevClose <= ema50;
                failedToBreak = v.High > ema50 && v.Close <= ema50;
                held = v.Low <= ema50 && v.Close > ema50;
                reclaimed = prevClose < ema50 && v.Close > ema50;
            }
            else if (v.Dir == V4VectorDir.BEARISH)
            {
                broke = v.Close < ema50 && prevClose >= ema50;
                failedToBreak = v.Low < ema50 && v.Close >= ema50;
                held = v.High >= ema50 && v.Close < ema50;
                reclaimed = prevClose > ema50 && v.Close < ema50;
            }
        }
    }
}
