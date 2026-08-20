// ======================================================================
// V4HypothesisEngine.cs  -  MNQ V4.1
// ======================================================================
// The pre-registration surface: a fixed registry of hypotheses, the
// four-level event hierarchy, and the ablation flags that let matched
// comparisons be constructed later without duplicating one market thesis
// into eight unrelated trades.
//
// THIS FILE SUBMITS NO ORDERS.
//
// What this module deliberately does NOT do is rank anything. It never
// scores a hypothesis, never compares them, never decides which fired
// "best". The engine captures; the backtesting layer controls multiple
// testing. Ranking here would smuggle selection into data capture, where
// no audit could ever see it.
//
// The 5-10 pre-registered limit applies to CLASS A market-edge hypotheses
// only. That limit is load-bearing rather than paperwork: earlier work in
// this project measured that a search over 8,329 feature conjunctions
// produced a best "setup" worth +16.6 points per trade ON SHUFFLED
// OUTCOMES, ranging as high as +26.1. The noise floor rises with the size
// of the search, and V4.1 has a much larger feature space than the run
// that produced that number.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// Which direction a hypothesis predicts, fixed BEFORE any outcome is
    /// examined. A hypothesis with no declared direction is not a
    /// hypothesis, it is a fishing licence.
    public enum V4PredictedDir { NONE, LONG, SHORT, EITHER }

    /// One frozen hypothesis definition.
    public class V4Hypothesis
    {
        public string HypothesisId = "";
        public V4HypothesisClass Class = V4HypothesisClass.A_MARKET_EDGE;
        public string ParentEvent = "";
        public string Architecture = "";          // ARCH-A / ARCH-B / ARCH-C
        public string RequiredStructure = "";
        public string RequiredVector = "";
        public string RequiredLevel = "";
        public string RequiredOrderFlow = "";
        public V4PredictedDir Predicted = V4PredictedDir.NONE;
        public string EntryTrigger = "";
        public V4StopKind StopFamily = V4StopKind.MEDIUM;
        public string ManagementFamily = "";
        public V4DataLayer RequiredLayer = V4DataLayer.STRUCTURE_ONLY;
        public string Notes = "";

        public string Csv()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append(V4Num.S(HypothesisId)).Append(',')
              .Append(Class).Append(',')
              .Append(V4Num.S(ParentEvent)).Append(',')
              .Append(V4Num.S(Architecture)).Append(',')
              .Append(V4Num.S(RequiredStructure)).Append(',')
              .Append(V4Num.S(RequiredVector)).Append(',')
              .Append(V4Num.S(RequiredLevel)).Append(',')
              .Append(V4Num.S(RequiredOrderFlow)).Append(',')
              .Append(Predicted).Append(',')
              .Append(V4Num.S(EntryTrigger)).Append(',')
              .Append(StopFamily).Append(',')
              .Append(V4Num.S(ManagementFamily)).Append(',')
              .Append(RequiredLayer).Append(',')
              .Append(V4Num.S(Notes));
            return sb.ToString();
        }
        public static string CsvHeader()
        {
            return "hypothesisId,class,parentEvent,architecture,requiredStructure,"
                 + "requiredVector,requiredLevel,requiredOrderFlow,predictedDir,"
                 + "entryTrigger,stopFamily,managementFamily,requiredLayer,notes";
        }
    }

    /// The registry. Populated once, at State.Configure, and never altered
    /// while a run is in flight.
    ///
    /// The entries below are the EVENT FAMILIES the prompt names. They are
    /// hypothesis SLOTS with declared directions, not claims that any of
    /// them works - the engine does not declare anything profitable, and
    /// V4.1's own predecessors returned 0 of 8 and 0 of 10 on families that
    /// looked at least as plausible as these.
    public class V4HypothesisRegistry
    {
        private readonly List<V4Hypothesis> items = new List<V4Hypothesis>();
        public IList<V4Hypothesis> Items { get { return items; } }

        public int ClassACount()
        {
            int n = 0;
            for (int i = 0; i < items.Count; i++)
                if (items[i].Class == V4HypothesisClass.A_MARKET_EDGE) n++;
            return n;
        }

        public void Add(V4Hypothesis h) { items.Add(h); }

        public V4Hypothesis Find(string id)
        {
            for (int i = 0; i < items.Count; i++)
                if (items[i].HypothesisId == id) return items[i];
            return null;
        }

        /// Build the default V4.1 family. Six CLASS A market-edge slots -
        /// inside the 5-10 limit with room to spare - plus the CLASS B
        /// ablations that are mandatory diagnostics around them.
        public static V4HypothesisRegistry Default()
        {
            V4HypothesisRegistry r = new V4HypothesisRegistry();

            r.Add(Make("H1-VECTOR-SWEEP-REVERSAL", V4HypothesisClass.A_MARKET_EDGE,
                "confirmed structural extreme swept by a 15m vector, acceptance fails, LTF reclaims",
                "ARCH-C", "15m break of confirmed swing", "15m vector RED|VIOLET (low) or GREEN|BLUE (high)",
                "at or near a tracked level", "", V4PredictedDir.EITHER,
                "vector-extreme take then reclaim", V4StopKind.TIGHT, "1m EMA9",
                V4DataLayer.STRUCTURE_VECTOR,
                "direction comes from which extreme was swept, never from vector colour"));

            r.Add(Make("H2-VECTOR-BREAK-CONTINUATION", V4HypothesisClass.A_MARKET_EDGE,
                "4H and 15m aligned, 15m vector closes beyond confirmed structure, LTF accepts",
                "ARCH-B", "4H aligned with 15m", "15m vector closing beyond structure",
                "", "", V4PredictedDir.EITHER,
                "acceptance beyond vector extreme", V4StopKind.STRUCTURAL, "1m EMA9",
                V4DataLayer.STRUCTURE_VECTOR, ""));

            r.Add(Make("H3-LTF-TAKES-15M-WICK", V4HypothesisClass.A_MARKET_EDGE,
                "15m vector creates an extreme, 1m/3m takes that exact extreme",
                "ARCH-A", "", "15m vector with a wick extreme", "", "", V4PredictedDir.EITHER,
                "both branches emitted: reclaim/failure AND acceptance/continuation",
                V4StopKind.TIGHT, "1m EMA9", V4DataLayer.STRUCTURE_VECTOR,
                "BOTH branches are captured against the same parent so neither can be chosen after the fact"));

            r.Add(Make("H4-VECTOR-AT-LEVEL", V4HypothesisClass.A_MARKET_EDGE,
                "vector occurs while interacting with a tracked level",
                "ARCH-B", "", "any vector", "interaction != NO_INTERACTION", "",
                V4PredictedDir.EITHER, "rejection vs acceptance branch", V4StopKind.MEDIUM,
                "1m EMA9", V4DataLayer.STRUCTURE_VECTOR, ""));

            r.Add(Make("H5-UNRECOVERED-VECTOR-DESTINATION", V4HypothesisClass.A_MARKET_EDGE,
                "structure points toward an older unrecovered vector zone",
                "ARCH-B", "structure directional", "unrecovered vector zone ahead of price",
                "", "", V4PredictedDir.EITHER, "structure break toward the zone",
                V4StopKind.STRUCTURAL, "vector-zone target", V4DataLayer.STRUCTURE_VECTOR,
                "measures probability, time and path of recovery, not just hit/miss"));

            r.Add(Make("H6-OF-ABSORPTION-REVERSAL", V4HypothesisClass.A_MARKET_EDGE,
                "new structural extreme, cumulative delta fails to confirm, aggression shows poor progress",
                "ARCH-C", "new structural extreme", "", "at or near a tracked level",
                "absorption candidate + delta divergence", V4PredictedDir.EITHER,
                "reclaim after absorption", V4StopKind.TIGHT, "1m EMA9",
                V4DataLayer.STRUCTURE_ORDERFLOW,
                "VOLUMETRIC WINDOW ONLY - far shorter history than the structure hypotheses"));

            // ---- CLASS B ablations, mandatory diagnostics ---------------
            r.Add(Make("B1-STRUCTURE-VS-VECTOR", V4HypothesisClass.B_INCREMENTAL,
                "does adding vector state change the parent event outcome", "", "", "", "", "",
                V4PredictedDir.NONE, "", V4StopKind.MEDIUM, "", V4DataLayer.STRUCTURE_VECTOR, ""));
            r.Add(Make("B2-STRUCTURE-VS-ORDERFLOW", V4HypothesisClass.B_INCREMENTAL,
                "does adding executed order flow change the parent event outcome", "", "", "", "", "",
                V4PredictedDir.NONE, "", V4StopKind.MEDIUM, "", V4DataLayer.STRUCTURE_ORDERFLOW, ""));
            r.Add(Make("B3-STRUCTURE-VS-LEVEL", V4HypothesisClass.B_INCREMENTAL,
                "does level context change the parent event outcome", "", "", "", "", "",
                V4PredictedDir.NONE, "", V4StopKind.MEDIUM, "", V4DataLayer.STRUCTURE_ONLY, ""));
            r.Add(Make("B4-EMA-FAN-ADDITION", V4HypothesisClass.B_INCREMENTAL,
                "does EMA fan alignment change the parent event outcome", "", "", "", "", "",
                V4PredictedDir.NONE, "", V4StopKind.MEDIUM, "", V4DataLayer.STRUCTURE_ONLY, ""));

            // ---- CLASS C / D -------------------------------------------
            r.Add(Make("C1-ARCH-COMPARISON", V4HypothesisClass.C_EXECUTION,
                "ARCH-A vs ARCH-B vs ARCH-C against the SAME parent event", "", "", "", "", "",
                V4PredictedDir.NONE, "", V4StopKind.MEDIUM, "", V4DataLayer.STRUCTURE_ONLY,
                "execution research may not manufacture a market edge"));
            r.Add(Make("D1-EMA9-VS-FIXED-R", V4HypothesisClass.D_RISK_MANAGEMENT,
                "1m EMA9 management against the fixed-R grid on identical entries", "", "", "", "", "",
                V4PredictedDir.NONE, "", V4StopKind.MEDIUM, "1m EMA9 vs fixed R",
                V4DataLayer.STRUCTURE_ONLY,
                "decision-relevant only after a parent Class A shows credible information"));

            return r;
        }

        private static V4Hypothesis Make(string id, V4HypothesisClass cls, string parent,
            string arch, string structure, string vector, string level, string of,
            V4PredictedDir dir, string trigger, V4StopKind stop, string mgmt,
            V4DataLayer layer, string notes)
        {
            V4Hypothesis h = new V4Hypothesis();
            h.HypothesisId = id; h.Class = cls; h.ParentEvent = parent; h.Architecture = arch;
            h.RequiredStructure = structure; h.RequiredVector = vector; h.RequiredLevel = level;
            h.RequiredOrderFlow = of; h.Predicted = dir; h.EntryTrigger = trigger;
            h.StopFamily = stop; h.ManagementFamily = mgmt; h.RequiredLayer = layer; h.Notes = notes;
            return h;
        }
    }

    // ==================================================================
    // EVENT HIERARCHY
    // ==================================================================

    /// One market thesis can produce many bars, many probes and many
    /// triggers. Without a hierarchy those all look like independent
    /// observations, and the sample size is silently inflated - measured at
    /// 7.4x clustering on 60m events in this project's earlier work.
    ///
    ///   ParentEventID : the market thesis. One per underlying move.
    ///   EventID       : one qualifying event within it.
    ///   EntryProbeID  : one architecture/trigger combination on that event.
    ///   HypothesisID  : which frozen hypothesis this row belongs to.
    ///
    /// rawSignalCount is emitted alongside so the analysis layer can
    /// compute an effective independent count instead of trusting the row
    /// count.
    public class V4EventKeys
    {
        public string ParentEventId = "";
        public string EventId = "";
        public string EntryProbeId = "";
        public string HypothesisId = "";
        public int RawSignalCount;
        public int ProbeIndex;

        public static string MakeParentId(string symbol, string tf, DateTime etClose, int dir)
        {
            return symbol + "-P-" + tf + "-"
                 + etClose.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture)
                 + (dir > 0 ? "-U" : (dir < 0 ? "-D" : "-N"));
        }
        public static string MakeEventId(string parentId, string kind, int seq)
        {
            return parentId + "-E" + seq.ToString(CultureInfo.InvariantCulture) + "-" + kind;
        }
        public static string MakeProbeId(string eventId, string arch, string trigger, string entryTf)
        {
            return eventId + "-" + arch + "-" + entryTf + "-" + trigger;
        }
    }

    /// Groups events belonging to one underlying move so overlapping
    /// triggers do not count as independent evidence.
    public class V4ThesisClusterer
    {
        /// Events on the same timeframe and side within this many minutes
        /// belong to one parent thesis.
        public int ClusterWindowMinutes = 60;

        private readonly Dictionary<string, string> lastParent = new Dictionary<string, string>();
        private readonly Dictionary<string, DateTime> lastEt = new Dictionary<string, DateTime>();
        private readonly Dictionary<string, int> counts = new Dictionary<string, int>();

        /// Returns the parent id for a new event, opening a new thesis only
        /// when the previous one has aged out.
        public string ParentFor(string symbol, string tf, int dir, DateTime etClose, out int rawSignalCount)
        {
            string key = tf + "|" + (dir > 0 ? "U" : "D");
            string parent;
            DateTime prev = DateTime.MinValue;
            bool have = lastParent.TryGetValue(key, out parent) & lastEt.TryGetValue(key, out prev);

            if (!have || (etClose - prev).TotalMinutes > ClusterWindowMinutes)
            {
                parent = V4EventKeys.MakeParentId(symbol, tf, etClose, dir);
                lastParent[key] = parent;
                counts[parent] = 0;
            }
            lastEt[key] = etClose;
            int c;
            counts.TryGetValue(parent, out c);
            c++;
            counts[parent] = c;
            rawSignalCount = c;
            return parent;
        }

        public void Reset() { lastParent.Clear(); lastEt.Clear(); counts.Clear(); }
    }

    // ==================================================================
    // ABLATION FLAGS
    // ==================================================================

    /// Emitted on every row so matched comparisons can be constructed
    /// afterwards without the engine having to write the same event out
    /// eight times.
    public struct V4AblationFlags
    {
        public bool HasStructure;
        public bool HasVector;
        public bool HasOrderFlow;
        public bool HasLevel;
        public bool HasProfile;
        public bool HasEmaFan;
        public bool IsControl;          // matched placebo row, no qualifying event

        public string Csv()
        {
            return V4Num.B(HasStructure) + "," + V4Num.B(HasVector) + ","
                 + V4Num.B(HasOrderFlow) + "," + V4Num.B(HasLevel) + ","
                 + V4Num.B(HasProfile) + "," + V4Num.B(HasEmaFan) + ","
                 + V4Num.B(IsControl);
        }
        public static string CsvHeader()
        {
            return "f_hasStructure,f_hasVector,f_hasOrderFlow,f_hasLevel,"
                 + "f_hasProfile,f_hasEmaFan,f_isControl";
        }
    }

    /// Signal-decay probe: the SAME frozen parent signal, entered later.
    /// If information does not survive a few minutes of delay it will not
    /// survive real execution either.
    ///
    /// Note the constraint the prompt puts on this and the engine honours:
    /// a delayed probe does not create a new thesis. It carries the parent's
    /// id and its own delay, so the comparison is like for like.
    public class V4DecayProbe
    {
        public static readonly int[] DelaysMinutes = new int[] { 0, 1, 2, 3, 5 };

        public int SignalDelayMinutes;
        public double DelayedEntryPrice = double.NaN;
        public bool StillValid;
        public double DelayedMfe = double.NaN;
        public double DelayedMae = double.NaN;
        public double DelayedForwardReturn = double.NaN;
    }
}
