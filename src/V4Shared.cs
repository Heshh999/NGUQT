// ======================================================================
// V4Shared.cs  -  MNQ V4.1 Structure + Vector + Order Flow Research
// ======================================================================
// Vocabulary shared by every V4.1 module: research classes, source
// traceability, data-validity flags, session context, and the small
// numeric helpers the other engines lean on.
//
// THIS FILE SUBMITS NO ORDERS. NOTHING IN THIS PROJECT AUTHORIZES LIVE
// TRADING.
//
// Two rules govern everything here.
//
//   1. A field is either a FEATURE, knowable at or before the event
//      timestamp, or a LABEL, which needs bars that have not closed yet.
//      The schema carries the distinction in the column name: f_ or y_.
//      V4FeatureRecorder enforces it; this file only supplies the names.
//
//   2. A concept whose exact public rule could not be verified is never
//      dressed as official. It carries sourceConceptClass = ADAPTED or
//      HEURISTIC, and a failed data-validity flag disqualifies its whole
//      family from confirmatory use.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    // ------------------------------------------------------------------
    // RESEARCH CLASSIFICATION
    // ------------------------------------------------------------------

    /// Keeping edge, execution and management apart is what stops a
    /// management tweak from being mistaken for a market edge. The 5-10
    /// pre-registered hypothesis limit applies to A_MARKET_EDGE alone.
    public enum V4HypothesisClass
    {
        A_MARKET_EDGE,        // causal state predicting future direction/path
        B_INCREMENTAL,        // does a feature add information to a parent event
        C_EXECUTION,          // how to enter an already-defined thesis
        D_RISK_MANAGEMENT     // how to monetize an already-demonstrated edge
    }

    /// CONFIRMATORY rows belong to a frozen pre-registered hypothesis.
    /// EXPLORATORY rows are everything else and can never support a
    /// decision on their own.
    public enum V4ResearchClass { CONFIRMATORY, EXPLORATORY, CONTROL }

    /// Where a concept's mechanical definition actually came from.
    /// PUBLICLY_SOURCED is reserved for rules whose exact public formula
    /// was verified. Everything else is ours and is labelled as ours.
    public enum V4SourceClass { PUBLICLY_SOURCED, ADAPTED, HEURISTIC }

    /// Which data layer a row's features could draw on. Order flow and
    /// volume profile exist only where the Volumetric series exists, which
    /// is a far shorter history than structure. Stamping this on every row
    /// is what stops a 10-month test being reported beside a 7-year one.
    public enum V4DataLayer
    {
        STRUCTURE_ONLY,          // 1m OHLCV derived - full history
        STRUCTURE_VECTOR,        // + PVSRA vectors - full history
        STRUCTURE_ORDERFLOW,     // + executed flow - volumetric window only
        FULL                     // + volume profile - volumetric window only
    }

    // ------------------------------------------------------------------
    // SOURCE TRACEABILITY
    // ------------------------------------------------------------------

    /// Attached to every Traders Reality-inspired tag so the backtest report
    /// can separate a published concept from our reading of it.
    public struct V4SourceTag
    {
        public string ConceptId;
        public string ConceptName;
        public V4SourceClass Class;
        public string TranslationVersion;

        public static V4SourceTag Make(string id, string name, V4SourceClass cls, string ver)
        {
            V4SourceTag t = new V4SourceTag();
            t.ConceptId = id; t.ConceptName = name; t.Class = cls; t.TranslationVersion = ver;
            return t;
        }
    }

    /// The registry of every concept V4.1 implements, with an honest verdict
    /// on whether its exact rule was verifiable.
    ///
    /// PVSRA is the one entry marked PUBLICLY_SOURCED. Its formula was found
    /// already implemented in this project's V2-era shared code and matches
    /// the canonical description: lookback 10, climax at 2.0x average volume
    /// or a volume*spread new high, elevated at 1.5x.
    ///
    /// The rest describe ideas that public material discusses qualitatively
    /// without publishing mechanics. They are implemented as declared
    /// translations, not as anybody's official algorithm.
    public static class V4SourceRegistry
    {
        public const string TranslationVersion = "v4.1.0";

        public static readonly V4SourceTag Pvsra = V4SourceTag.Make(
            "TR-PVSRA", "PVSRA vector candle classification",
            V4SourceClass.PUBLICLY_SOURCED, TranslationVersion);

        public static readonly V4SourceTag EmaFan = V4SourceTag.Make(
            "TR-EMAFAN", "EMA fan 5/13/50/200/800",
            V4SourceClass.ADAPTED, TranslationVersion);

        public static readonly V4SourceTag WmFormation = V4SourceTag.Make(
            "TR-WM", "W / M formation from confirmed swings",
            V4SourceClass.ADAPTED, TranslationVersion);

        public static readonly V4SourceTag VectorTrap = V4SourceTag.Make(
            "TR-TRAP", "Vector trap: aggressive push then swift recovery",
            V4SourceClass.ADAPTED, TranslationVersion);

        public static readonly V4SourceTag VectorPush = V4SourceTag.Make(
            "TR-PUSH", "Repeated vector aggression without progress",
            V4SourceClass.ADAPTED, TranslationVersion);

        public static readonly V4SourceTag TriggerVector = V4SourceTag.Make(
            "TR-TRIGGER", "Trigger vector around structure and EMA50",
            V4SourceClass.ADAPTED, TranslationVersion);

        public static readonly V4SourceTag StoppingVolume = V4SourceTag.Make(
            "TR-STOPVOL", "Stopping volume - RESEARCH_HEURISTIC, raw ingredients only",
            V4SourceClass.HEURISTIC, TranslationVersion);

        public static readonly V4SourceTag Dealer = V4SourceTag.Make(
            "TR-DEALER", "Dealer / market-maker extension and return to value",
            V4SourceClass.ADAPTED, TranslationVersion);

        public static readonly V4SourceTag FalseMove = V4SourceTag.Make(
            "TR-FALSEMOVE", "False move / trap at a known boundary",
            V4SourceClass.ADAPTED, TranslationVersion);
    }

    // ------------------------------------------------------------------
    // DATA-VALIDITY FLAGS
    // ------------------------------------------------------------------

    /// A failed flag must prevent its feature family from being treated as
    /// confirmatory evidence. Two of these are false on the evidence and
    /// stay false until the underlying data changes.
    public class V4ValidityFlags
    {
        /// PVSRA formula verified against the canonical description.
        public bool VectorSourceVerified = true;

        /// The fan is a declared translation, not a published algorithm.
        public bool EmaFanSourceVerified = false;

        /// No public source publishes exact First Vector mechanics, so no
        /// firstVectorCandidate is manufactured. The prompt is explicit.
        public bool FirstVectorSourceVerified = false;

        /// FALSE on a back-adjusted continuous contract. Back adjustment
        /// shifts historical absolute prices by the accumulated roll spread,
        /// so the price grid a 2019 round number sat on no longer exists.
        /// While this is false the PSY / whole / half-number family is not
        /// emitted at all.
        public bool PsyLevelPriceIntegrityPass = false;

        /// ADR/AWR use a plainly documented causal method: mean of the last
        /// N completed exchange-day ranges, N declared, current day excluded.
        public bool AdrAwrDefinitionVerified = true;

        /// No specific published pivot / M-level formula was selected, so
        /// none is called official and none is emitted.
        public bool PivotDefinitionVerified = false;
        public bool MLevelDefinitionVerified = false;

        /// NinjaTrader 8 keeps no historical Level 2 depth for backtest.
        /// There is nothing to audit, so no depth feature is emitted.
        public bool DepthHistoryAvailable = false;

        /// Set by the order-flow audit at runtime.
        public bool OrderFlowAuditPassed = false;
        public bool ProfileAuditPassed = false;

        public string Summary()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("SOURCE / DATA-VALIDITY FLAGS");
            sb.AppendLine("  vectorSourceVerified          " + B(VectorSourceVerified));
            sb.AppendLine("  emaFanSourceVerified          " + B(EmaFanSourceVerified) + "   (declared translation)");
            sb.AppendLine("  firstVectorSourceVerified     " + B(FirstVectorSourceVerified) + "   (no public mechanics - family NOT emitted)");
            sb.AppendLine("  psyLevelPriceIntegrityPass    " + B(PsyLevelPriceIntegrityPass) + "   (back-adjusted series - family NOT emitted)");
            sb.AppendLine("  adrAwrDefinitionVerified      " + B(AdrAwrDefinitionVerified));
            sb.AppendLine("  pivotDefinitionVerified       " + B(PivotDefinitionVerified) + "   (family NOT emitted)");
            sb.AppendLine("  mLevelDefinitionVerified      " + B(MLevelDefinitionVerified) + "   (family NOT emitted)");
            sb.AppendLine("  depthHistoryAvailable         " + B(DepthHistoryAvailable) + "   (NT8 keeps no historical L2 - DEPTH VERDICT = FAILED)");
            return sb.ToString();
        }
        private static string B(bool v) { return v ? "TRUE " : "FALSE"; }
    }

    // ------------------------------------------------------------------
    // SESSION CONTEXT
    // ------------------------------------------------------------------

    public enum V4Session { ASIA, LONDON, NEWYORK_RTH, NEWYORK_POST, UNKNOWN }

    /// Deterministic session windows in ET minutes-of-day. These are the
    /// project's definitions, stated here rather than inherited from a
    /// chart template that could differ between runs.
    ///
    /// The CME exchange day opens 18:00 ET. Two halts punctuate it: the
    /// equity-index maintenance pause 16:15-16:30 ET and the daily halt
    /// 17:00-18:00 ET. Both are scheduled, so a gap across either is not
    /// missing data - an earlier version of this project reported 436 of
    /// 463 "gaps" as data loss before that was fixed.
    public static class V4SessionMap
    {
        public const int ExchangeOpenEt = 1080;      // 18:00
        public const int AsiaEndEt = 180;            // 03:00
        public const int LondonEndEt = 570;          // 09:30
        public const int RthStartEt = 570;           // 09:30
        public const int RthEndEt = 960;             // 16:00
        public const int MaintStartEt = 975;         // 16:15
        public const int MaintEndEt = 990;           // 16:30
        public const int DailyHaltStartEt = 1020;    // 17:00

        public static int MinutesOfDay(DateTime et) { return et.Hour * 60 + et.Minute; }

        public static V4Session Classify(DateTime et)
        {
            int m = MinutesOfDay(et);
            if (m >= ExchangeOpenEt || m < AsiaEndEt) return V4Session.ASIA;
            if (m < LondonEndEt) return V4Session.LONDON;
            if (m < RthEndEt) return V4Session.NEWYORK_RTH;
            if (m < DailyHaltStartEt) return V4Session.NEWYORK_POST;
            return V4Session.UNKNOWN;
        }

        /// Minutes since this session's own open, or -1 when undefined.
        public static int MinutesFromSessionOpen(DateTime et)
        {
            int m = MinutesOfDay(et);
            switch (Classify(et))
            {
                case V4Session.ASIA:
                    return m >= ExchangeOpenEt ? m - ExchangeOpenEt : m + (1440 - ExchangeOpenEt);
                case V4Session.LONDON: return m - AsiaEndEt;
                case V4Session.NEWYORK_RTH: return m - RthStartEt;
                case V4Session.NEWYORK_POST: return m - RthEndEt;
            }
            return -1;
        }

        public static int MinutesFromRthOpen(DateTime et) { return MinutesOfDay(et) - RthStartEt; }
        public static int MinutesToRthClose(DateTime et) { return RthEndEt - MinutesOfDay(et); }
        public static bool IsRth(DateTime et)
        {
            int m = MinutesOfDay(et); return m >= RthStartEt && m <= RthEndEt;
        }

        /// True when a gap landing on this bar is a scheduled halt rather
        /// than missing data.
        public static bool IsScheduledHaltBoundary(DateTime barAfterGapEt, int graceMinutes)
        {
            int m = MinutesOfDay(barAfterGapEt);
            if (m >= ExchangeOpenEt && m <= ExchangeOpenEt + graceMinutes) return true;
            if (m > MaintEndEt && m <= MaintEndEt + graceMinutes) return true;
            return false;
        }
    }

    // ------------------------------------------------------------------
    // SMALL NUMERIC HELPERS
    // ------------------------------------------------------------------

    public static class V4Num
    {
        public static bool Ok(double v) { return !double.IsNaN(v) && !double.IsInfinity(v); }

        /// Divide, refusing to return a number when the denominator is too
        /// small to mean anything. Guarding this is not pedantry: an earlier
        /// stage of this project had 0.078% of rows carrying more than the
        /// entire dataset's signal because a near-zero ATR denominator was
        /// allowed through.
        public static double SafeDiv(double num, double den, double minDen)
        {
            if (!Ok(num) || !Ok(den) || Math.Abs(den) < minDen) return double.NaN;
            return num / den;
        }

        /// Distance in ATR units. Positive means price is above the level.
        public static double DistAtr(double price, double level, double atr)
        {
            return SafeDiv(price - level, atr, 1e-9);
        }

        public static double Pct(double part, double whole)
        {
            return SafeDiv(part, whole, 1e-12) * 100.0;
        }

        public static string F(double v)
        {
            return Ok(v) ? v.ToString("0.####", CultureInfo.InvariantCulture) : "";
        }
        public static string B(bool v) { return v ? "TRUE" : "FALSE"; }
        public static string T(DateTime d)
        {
            return (d == DateTime.MinValue || d == DateTime.MaxValue)
                ? "" : d.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        }
        public static string I(int v) { return v.ToString(CultureInfo.InvariantCulture); }

        /// A CSV cell that can never break the row, whatever the input.
        public static string S(string v)
        {
            if (string.IsNullOrEmpty(v)) return "";
            if (v.IndexOf(',') < 0 && v.IndexOf('"') < 0 && v.IndexOf('\n') < 0) return v;
            return "\"" + v.Replace("\"", "\"\"") + "\"";
        }
    }

    /// Exponential moving average of close, updated once per completed bar.
    /// Seeded with the first value rather than an SMA so that two runs over
    /// the same bars agree exactly; the warm-up guard below is what keeps an
    /// unconverged value out of the official sample.
    public class V4Ema
    {
        private readonly int period;
        private readonly double k;
        private double value = double.NaN;
        private int n;

        public V4Ema(int p)
        {
            period = p < 1 ? 1 : p;
            k = 2.0 / (period + 1.0);
        }

        public void Update(double close)
        {
            n++;
            if (double.IsNaN(value)) { value = close; return; }
            value = close * k + value * (1.0 - k);
        }

        public int Period { get { return period; } }
        public int Count { get { return n; } }
        public double Value { get { return Ready ? value : double.NaN; } }
        public double RawValue { get { return value; } }

        /// An EMA is treated as usable only after three periods of bars have
        /// gone through it. EMA800 on 15m therefore needs 2400 completed 15m
        /// bars - about 25 trading weeks - before it reports a value at all.
        public bool Ready { get { return n >= period * 3; } }
    }

    /// A rolling window of the last N values with slope and percentile.
    public class V4Roll
    {
        private readonly int cap;
        private readonly List<double> v = new List<double>();
        public V4Roll(int capacity) { cap = capacity < 1 ? 1 : capacity; }

        public void Add(double x)
        {
            if (!V4Num.Ok(x)) return;
            v.Add(x);
            if (v.Count > cap) v.RemoveAt(0);
        }
        public int Count { get { return v.Count; } }
        public bool Full { get { return v.Count >= cap; } }
        public double Last { get { return v.Count == 0 ? double.NaN : v[v.Count - 1]; } }

        public double Mean()
        {
            if (v.Count == 0) return double.NaN;
            double s = 0; for (int i = 0; i < v.Count; i++) s += v[i];
            return s / v.Count;
        }
        public double Max()
        {
            if (v.Count == 0) return double.NaN;
            double m = v[0]; for (int i = 1; i < v.Count; i++) if (v[i] > m) m = v[i];
            return m;
        }
        public double Min()
        {
            if (v.Count == 0) return double.NaN;
            double m = v[0]; for (int i = 1; i < v.Count; i++) if (v[i] < m) m = v[i];
            return m;
        }
        /// Change across the window, per bar.
        public double Slope()
        {
            if (v.Count < 2) return double.NaN;
            return (v[v.Count - 1] - v[0]) / (v.Count - 1);
        }
        /// Fraction of the window at or below x, in [0,1].
        public double PercentileOf(double x)
        {
            if (v.Count == 0 || !V4Num.Ok(x)) return double.NaN;
            int le = 0; for (int i = 0; i < v.Count; i++) if (v[i] <= x) le++;
            return (double)le / v.Count;
        }
        public double ValueAt(int idxFromOldest)
        {
            if (idxFromOldest < 0 || idxFromOldest >= v.Count) return double.NaN;
            return v[idxFromOldest];
        }
    }

    // ------------------------------------------------------------------
    // BREAK TRANSITION GATE
    // ------------------------------------------------------------------

    /// Turns "price is beyond the level" into "price just BROKE the level".
    ///
    /// This exists because the difference is not cosmetic. Testing the state
    /// rather than the transition makes a single trend leg emit one event per
    /// bar: on the first V4.1 sample, 84% of confirmed swing levels were
    /// "broken" more than once - mean 4.5 times, up to 16 - 78% of events
    /// landed exactly one bar after the previous one, and 1,705 rows came
    /// from 306 actual theses.
    ///
    /// The rule: a level fires ONCE per excursion. It can fire again only
    /// after price has closed back inside it, or once the confirmed level
    /// itself has moved to a different price.
    public class V4BreakGate
    {
        private double lastBrokeHigh = double.NaN, lastBrokeLow = double.NaN;
        private bool highReentered = true, lowReentered = true;

        public void Reset()
        {
            lastBrokeHigh = lastBrokeLow = double.NaN;
            highReentered = lowReentered = true;
        }

        /// Fold one completed bar in. Returns +1 for a fresh high break, -1
        /// for a fresh low break, 0 for neither. Call once per bar and in
        /// order - it carries state by design.
        public int Update(double barHigh, double barLow, double barClose,
                          bool haveHigh, double swingHigh,
                          bool haveLow, double swingLow)
        {
            // Decide using the state as it stood ENTERING this bar, then
            // update re-entry from this bar's close for the NEXT one.
            //
            // The other order looks equivalent and is not: a bar that pokes
            // above the level and closes back below would re-arm the gate and
            // then immediately fire on itself, so one bar counts as both the
            // re-entry and the next break.
            bool newHighLevel = haveHigh
                && (!V4Num.Ok(lastBrokeHigh) || Math.Abs(swingHigh - lastBrokeHigh) > 1e-9);
            bool newLowLevel = haveLow
                && (!V4Num.Ok(lastBrokeLow) || Math.Abs(swingLow - lastBrokeLow) > 1e-9);

            int fired = 0;
            if (haveHigh && barHigh > swingHigh && (newHighLevel || highReentered))
            {
                lastBrokeHigh = swingHigh; highReentered = false;
                fired = 1;
            }
            else if (haveLow && barLow < swingLow && (newLowLevel || lowReentered))
            {
                lastBrokeLow = swingLow; lowReentered = false;
                fired = -1;
            }

            if (haveHigh && barClose < swingHigh && fired != 1) highReentered = true;
            if (haveLow && barClose > swingLow && fired != -1) lowReentered = true;
            return fired;
        }
    }

    // ------------------------------------------------------------------
    // BAR TIMESTAMP CONVENTION
    // ------------------------------------------------------------------

    /// Builds a bar's open/close pair from the single timestamp NinjaTrader
    /// gives for a completed bar.
    ///
    /// This is a two-line function that lives in its own class for one
    /// reason: when it was inline in the host, it was WRONG for two builds
    /// and no test could see it. NinjaTrader stamps a completed bar at its
    /// CLOSE. Reading that stamp as the OPEN and adding the bar period put
    /// every timestamp in every output file one whole bar-period into the
    /// future.
    public static class V4BarStamp
    {
        /// CORRECT: the stamp IS the close; the open is derived backwards.
        public static void FromNtStamp(DateTime stampEt, int minutesPerBar,
                                       out DateTime etOpen, out DateTime etClose)
        {
            etClose = stampEt;
            etOpen = stampEt.AddMinutes(-minutesPerBar);
        }

        /// The defect, kept ONLY so a regression test can demonstrate it
        /// still reproduces the field-observed symptom. Never call this.
        public static void FromNtStampAsOpen_DEFECT(DateTime stampEt, int minutesPerBar,
                                                    out DateTime etOpen, out DateTime etClose)
        {
            etOpen = stampEt;
            etClose = stampEt.AddMinutes(minutesPerBar);
        }
    }

    // ------------------------------------------------------------------
    // LOWER-TIMEFRAME EXECUTION FAMILY
    // ------------------------------------------------------------------

    /// How ARCH-C's 1-minute layer executes AFTER the 3-minute layer has
    /// confirmed the setup.
    ///
    /// This is a declared family rather than a fixed rule because the build
    /// prompt specifies "15m event -> 3m setup/confirmation -> 1m execution"
    /// without saying what the 1m trigger is. Guessing one silently is
    /// exactly what the project's standing rule forbids.
    ///
    /// It matters, and the first clean sample showed why. With IMMEDIATE,
    /// the 3m confirmation and the 1m trigger are the SAME test - a close
    /// beyond the event close - and a 3m bar closing at time T contains a 1m
    /// bar closing at T with the identical close. So ARCH-C fired at the same
    /// instant as ARCH-B on 99.4% of events, at the same price on 99.6%.
    /// Three architectures, two of them one architecture.
    public enum V4LtfExecution
    {
        /// Enter on the first 1m close beyond the event close. Reproduces the
        /// collapse above - kept only so the old behaviour is reachable.
        IMMEDIATE,

        /// Wait for a retrace of at least PullbackAtr x ATR back off the best
        /// price seen since confirmation, THEN enter on the first 1m close in
        /// the event's direction. Gives the 1m layer a real job: a better
        /// price, at the risk of never filling.
        PULLBACK,

        /// Enter on the first 1m bar that exceeds the PREVIOUS 1m bar's
        /// extreme in the event's direction - a micro break of structure.
        MICRO_BREAK
    }

    /// The ARCH-C 1m execution gate, extracted so it can be tested.
    ///
    /// Left inline in the host it would be exactly as unverifiable as the
    /// bar-timestamp convention was - and that one shipped broken twice.
    public class V4LtfExecutionGate
    {
        public V4LtfExecution Mode = V4LtfExecution.PULLBACK;
        public double PullbackAtr = 0.35;

        private double best = double.NaN;
        private double prevHigh = double.NaN, prevLow = double.NaN;
        private bool armed;

        public bool Armed { get { return armed; } }
        public double BestSinceConfirm { get { return best; } }

        public void Reset() { best = prevHigh = prevLow = double.NaN; armed = false; }

        /// Returns true when the 1m layer may execute on THIS bar.
        /// Call once per completed 1m bar, in order, only after the 3m layer
        /// has confirmed.
        public bool Ready(int side, double barHigh, double barLow, double atr)
        {
            bool ok;
            if (Mode == V4LtfExecution.IMMEDIATE) ok = true;
            else if (Mode == V4LtfExecution.MICRO_BREAK)
            {
                ok = V4Num.Ok(prevHigh) && V4Num.Ok(prevLow)
                     && (side > 0 ? barHigh > prevHigh : barLow < prevLow);
            }
            else
            {
                if (armed) ok = true;
                else if (!V4Num.Ok(best) || !V4Num.Ok(atr) || atr <= 0) ok = false;
                else
                {
                    double retrace = side > 0 ? best - barLow : barHigh - best;
                    if (retrace >= PullbackAtr * atr) { armed = true; ok = true; }
                    else ok = false;
                }
            }

            prevHigh = barHigh; prevLow = barLow;
            double b = side > 0 ? barHigh : barLow;
            if (!V4Num.Ok(best)) best = b;
            else if (side > 0 ? b > best : b < best) best = b;
            return ok;
        }
    }
}
