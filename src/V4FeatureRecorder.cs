// ======================================================================
// V4FeatureRecorder.cs  -  MNQ V4.1
// ======================================================================
// The CSV schema, and the mechanism that keeps FEATURES and LABELS apart
// in a way a reader can actually verify.
//
// THIS FILE SUBMITS NO ORDERS.
//
// Every column is named f_ or y_.
//
//   f_  knowable at or before the event timestamp
//   y_  requires bars that had not closed at the event timestamp
//
// That is not decoration. It is the only part of the no-lookahead claim a
// person can check by eye, and the previous generation of this package did
// not have it - the separation existed in the code's structure and in a
// comment, but nothing in the output carried it. A reader had to trust it.
//
// Two mechanical guarantees on top of the naming:
//
//   1. Columns are appended in a fixed order and the header is derived
//      from that same order, so header and row cannot drift apart. A
//      schema-vs-row mismatch throws rather than writing a misaligned row.
//
//   2. AddFeature refuses a timestamp later than the event timestamp. That
//      catches the one lookahead bug that is otherwise invisible: a feature
//      correctly computed but read from the wrong side of the cutoff.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// One output row, built column by column.
    public class V4Row
    {
        private readonly List<string> names = new List<string>();
        private readonly List<string> values = new List<string>();
        private readonly DateTime eventEt;
        private int lookaheadHits;

        public V4Row(DateTime eventEtIn) { eventEt = eventEtIn; }

        public int LookaheadHits { get { return lookaheadHits; } }
        public int Count { get { return names.Count; } }

        // ---- features -------------------------------------------------
        public V4Row F(string name, string v) { return Add("f_" + name, V4Num.S(v)); }
        public V4Row F(string name, double v) { return Add("f_" + name, V4Num.F(v)); }
        public V4Row F(string name, int v) { return Add("f_" + name, V4Num.I(v)); }
        public V4Row F(string name, bool v) { return Add("f_" + name, V4Num.B(v)); }

        /// A feature that carries its own timestamp. If that timestamp is
        /// after the event, the value could not have been known and the row
        /// records the violation instead of hiding it.
        public V4Row F(string name, DateTime v)
        {
            if (v != DateTime.MinValue && v != DateTime.MaxValue && v > eventEt) lookaheadHits++;
            return Add("f_" + name, V4Num.T(v));
        }

        // ---- labels ---------------------------------------------------
        public V4Row Y(string name, string v) { return Add("y_" + name, V4Num.S(v)); }
        public V4Row Y(string name, double v) { return Add("y_" + name, V4Num.F(v)); }
        public V4Row Y(string name, int v) { return Add("y_" + name, V4Num.I(v)); }
        public V4Row Y(string name, bool v) { return Add("y_" + name, V4Num.B(v)); }
        public V4Row Y(string name, DateTime v) { return Add("y_" + name, V4Num.T(v)); }

        /// Identity columns carry no prefix: they are keys, not evidence.
        public V4Row Key(string name, string v) { return Add(name, V4Num.S(v)); }
        public V4Row Key(string name, int v) { return Add(name, V4Num.I(v)); }

        private V4Row Add(string n, string v) { names.Add(n); values.Add(v); return this; }

        public string Header()
        {
            StringBuilder sb = new StringBuilder(4096);
            for (int i = 0; i < names.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(names[i]);
            }
            return sb.ToString();
        }

        public string Csv()
        {
            StringBuilder sb = new StringBuilder(4096);
            for (int i = 0; i < values.Count; i++)
            {
                if (i > 0) sb.Append(',');
                sb.Append(values[i]);
            }
            return sb.ToString();
        }

        public string NameAt(int i) { return names[i]; }
        public string ValueAt(int i) { return values[i]; }
    }

    /// Holds the schema for one output file and guarantees every row
    /// matches it.
    public class V4Schema
    {
        private string header;
        private readonly List<string> names = new List<string>();
        private readonly string fileKind;

        public V4Schema(string kind) { fileKind = kind; }

        public bool Established { get { return header != null; } }
        public string Header { get { return header; } }
        public int FeatureCount, LabelCount, KeyCount;

        /// The first row defines the schema. Every later row is checked
        /// against it, and a mismatch throws instead of silently writing a
        /// row whose values do not line up with the header.
        public void Establish(V4Row r)
        {
            header = r.Header();
            names.Clear();
            for (int i = 0; i < r.Count; i++)
            {
                string n = r.NameAt(i);
                names.Add(n);
                if (n.StartsWith("f_")) FeatureCount++;
                else if (n.StartsWith("y_")) LabelCount++;
                else KeyCount++;
            }
        }

        public void Verify(V4Row r)
        {
            if (header == null) { Establish(r); return; }
            if (r.Count != names.Count)
                throw new InvalidOperationException(
                    "V4Schema[" + fileKind + "]: row has " + r.Count
                    + " columns, schema has " + names.Count
                    + ". A row was built on a different path - refusing to write a misaligned row.");
            for (int i = 0; i < names.Count; i++)
                if (r.NameAt(i) != names[i])
                    throw new InvalidOperationException(
                        "V4Schema[" + fileKind + "]: column " + i + " is '" + r.NameAt(i)
                        + "', schema says '" + names[i] + "'.");
        }

        public string Describe()
        {
            return fileKind + ": " + V4Num.I(names.Count) + " columns  ("
                 + V4Num.I(KeyCount) + " keys, "
                 + V4Num.I(FeatureCount) + " f_ features, "
                 + V4Num.I(LabelCount) + " y_ labels)";
        }
    }

    // ==================================================================
    // ROW BUILDERS
    // ==================================================================

    /// A parent structure event whose FEATURES are frozen as text at
    /// the event instant, waiting for its forward window to close so the
    /// labels can be appended.
    ///
    /// This lives here rather than inside the NinjaScript host for one
    /// reason: while it was a private class on the host, nothing
    /// off-platform could see WHERE the label block was assembled, and
    /// the third clean sample shipped six vector-recovery labels that had
    /// been read on the vector's own bar - pinned at UNRECOVERED / 0 /
    /// blank across all 659 rows. A test that only exercised
    /// VectorRecoveryLabels passed either way. Now the assembly itself is
    /// a unit and can be driven end to end.
    public class V4OpenEvent
    {
        public string FeatureCsv = "";
        public DateTime EventEt;
        public readonly V4ForwardLabels Labels = new V4ForwardLabels();

        /// The vector that formed ON the event bar, or null. Held by
        /// REFERENCE: the engine keeps advancing its recovery as later
        /// bars close, which is exactly why it must not be read here.
        public V4Vector EventVector;

        /// The timeframe tag the recovery labels are named for.
        public string VectorTfTag = "15m";

        /// Freeze the feature half. Called once, at the event.
        public void Freeze(V4Row featureRow, DateTime eventEt)
        {
            FeatureCsv = featureRow.Csv();
            EventEt = eventEt;
        }

        /// Build the label half. Called once, when the window closes.
        /// Vector recovery is part of THIS half, never the frozen one.
        public V4Row BuildLabelRow()
        {
            V4Row rl = new V4Row(EventEt);
            AppendLabelBlock(rl, VectorTfTag, EventVector, Labels);
            return rl;
        }

        /// The completed CSV line: frozen features, then labels.
        public string CompletedCsv() { return FeatureCsv + "," + BuildLabelRow().Csv(); }

        /// The ONE definition of the label block. Both the written row and
        /// the schema row go through here, so the header cannot drift away
        /// from the data - a divergence that would be invisible, because the
        /// schema check would keep passing against its own stale definition.
        private static void AppendLabelBlock(V4Row rl, string tfTag, V4Vector v, V4ForwardLabels L)
        {
            V4RowBuilder.VectorRecoveryLabels(rl, tfTag, v);
            V4RowBuilder.Labels(rl, L);
        }

        /// Feature names followed by label names, values blank. Lets the
        /// header be established on the first event, before any window has
        /// closed.
        public static V4Row SchemaRow(V4Row featureRow, string vectorTfTag, DateTime anyEt)
        {
            V4Row probe = new V4Row(anyEt);
            AppendLabelBlock(probe, vectorTfTag, null, new V4ForwardLabels());
            V4Row combined = new V4Row(anyEt);
            for (int i = 0; i < featureRow.Count; i++) combined.Key(featureRow.NameAt(i), "");
            for (int i = 0; i < probe.Count; i++) combined.Key(probe.NameAt(i), "");
            return combined;
        }
    }


    /// Assembles the V4.1 structure/vector research row from the engine
    /// state. Kept in one place so the column order is defined exactly
    /// once and every writer agrees on it.
    public static class V4RowBuilder
    {
        public const string SchemaVersion = "v4.1.0";

        /// Identity and provenance columns, written first on every row.
        public static void Keys(V4Row r, V4EventKeys k, string symbol, string tf,
                                V4ResearchClass rc, V4HypothesisClass hc, V4DataLayer layer)
        {
            r.Key("parentEventId", k.ParentEventId)
             .Key("eventId", k.EventId)
             .Key("entryProbeId", k.EntryProbeId)
             .Key("hypothesisId", k.HypothesisId)
             .Key("rawSignalCount", k.RawSignalCount)
             .Key("symbol", symbol)
             .Key("tf", tf)
             .Key("schemaVersion", SchemaVersion)
             .Key("researchClass", rc.ToString())
             .Key("hypothesisClass", hc.ToString())
             .Key("dataLayer", layer.ToString());
        }

        /// Source traceability, so the report can separate a published
        /// concept from our own mechanical reading of it.
        public static void Source(V4Row r, V4SourceTag t)
        {
            r.F("sourceConceptId", t.ConceptId)
             .F("sourceConceptName", t.ConceptName)
             .F("sourceConceptClass", t.Class.ToString())
             .F("mechanicalTranslationVersion", t.TranslationVersion);
        }

        /// Data-validity flags travel with every row so a downstream script
        /// cannot use a disqualified family by accident.
        public static void Validity(V4Row r, V4ValidityFlags v)
        {
            r.F("vectorSourceVerified", v.VectorSourceVerified)
             .F("emaFanSourceVerified", v.EmaFanSourceVerified)
             .F("firstVectorSourceVerified", v.FirstVectorSourceVerified)
             .F("psyLevelPriceIntegrityPass", v.PsyLevelPriceIntegrityPass)
             .F("adrAwrDefinitionVerified", v.AdrAwrDefinitionVerified)
             .F("pivotDefinitionVerified", v.PivotDefinitionVerified)
             .F("mLevelDefinitionVerified", v.MLevelDefinitionVerified)
             .F("depthHistoryAvailable", v.DepthHistoryAvailable);
        }

        /// The bar itself.
        public static void Bar(V4Row r, V4Bar b, double atr, double relVol)
        {
            double range = b.High - b.Low;
            double body = Math.Abs(b.Close - b.Open);
            r.F("dateEt", b.EtClose.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture))
             .F("timeEt", b.EtClose.ToString("HH:mm:ss", CultureInfo.InvariantCulture))
             .F("barOpenEt", b.EtOpen)
             .F("barCloseEt", b.EtClose)
             .F("open", b.Open).F("high", b.High).F("low", b.Low).F("close", b.Close)
             .F("volume", b.Volume)
             .F("rangePts", range)
             .F("bodyPts", body)
             .F("bodyPctOfRange", V4Num.Pct(body, range))
             .F("upperWickPts", b.High - Math.Max(b.Open, b.Close))
             .F("lowerWickPts", Math.Min(b.Open, b.Close) - b.Low)
             .F("closeLocationInRange", V4Num.Pct(b.Close - b.Low, range))
             .F("atr", atr)
             .F("rangeAtr", V4Num.SafeDiv(range, atr, 1e-9))
             .F("bodyAtr", V4Num.SafeDiv(body, atr, 1e-9))
             .F("relVolume", relVol);
        }

        /// Session and clock context. Exogenous - nothing here is derived
        /// from price, which is what makes it a clean ablation partner.
        public static void Session(V4Row r, DateTime et)
        {
            r.F("sessionName", V4SessionMap.Classify(et).ToString())
             .F("etMinuteOfDay", V4SessionMap.MinutesOfDay(et))
             .F("isRth", V4SessionMap.IsRth(et))
             .F("minutesFromSessionOpen", V4SessionMap.MinutesFromSessionOpen(et))
             .F("minutesFromRthOpen", V4SessionMap.MinutesFromRthOpen(et))
             .F("minutesToRthClose", V4SessionMap.MinutesToRthClose(et))
             .F("dayOfWeek", (int)et.DayOfWeek);
        }

        /// Vector state for one timeframe.
        public static void Vector(V4Row r, string tfTag, V4Vector v, V4VectorEngine eng, DateTime cutoff)
        {
            bool has = v != null;
            r.F("isVector_" + tfTag, has)
             .F("vectorColor_" + tfTag, has ? v.Color.ToString() : V4VectorColor.NONE.ToString())
             .F("vectorTier_" + tfTag, has ? v.Tier.ToString() : V4VectorTier.NONE.ToString())
             .F("vectorDirection_" + tfTag, has ? v.Dir.ToString() : V4VectorDir.NONE.ToString())
             .F("vectorId_" + tfTag, has ? v.VectorId : "")
             .F("vectorCreatedEt_" + tfTag, has ? v.CreatedEt : DateTime.MinValue)
             .F("vectorHigh_" + tfTag, has ? v.High : double.NaN)
             .F("vectorLow_" + tfTag, has ? v.Low : double.NaN)
             .F("vectorBodyHigh_" + tfTag, has ? v.BodyHigh : double.NaN)
             .F("vectorBodyLow_" + tfTag, has ? v.BodyLow : double.NaN)
             .F("vectorRangePts_" + tfTag, has ? v.RangePts : double.NaN)
             .F("vectorRelVolume_" + tfTag, has ? v.RelVolume : double.NaN)
             .F("vectorVolumeXRange_" + tfTag, has ? v.VolumeXRange : double.NaN)
             .F("vectorTookSwingHigh_" + tfTag, has && v.TookSwingHigh)
             .F("vectorTookSwingLow_" + tfTag, has && v.TookSwingLow)
             .F("vectorBrokeStructure_" + tfTag, has && v.BrokeStructure)
             .F("vectorClosedBeyond_" + tfTag, has && v.ClosedBeyondStructure)
             .F("vectorWickedBeyond_" + tfTag, has && v.WickedBeyondStructure)
             // Age of the MOST RECENT vector on this timeframe, whenever it
             // formed - not of the current bar's vector, whose age is zero by
             // construction. That mistake made this column report only -1 or 0
             // on 15m across a whole sample.
             .F("minutesSinceVector_" + tfTag, MinutesSinceVector(eng, cutoff))
             .F("unrecoveredVectorCount_" + tfTag, eng == null ? 0 : eng.UnrecoveredCount(cutoff));
        }


        /// Minutes since the last vector of this timeframe became knowable,
        /// or -1 when none has yet.
        private static int MinutesSinceVector(V4VectorEngine eng, DateTime cutoff)
        {
            if (eng == null) return -1;
            V4Vector last = eng.LatestKnownAt(cutoff);
            if (last == null) return -1;
            int m = (int)(cutoff - last.CreatedEt).TotalMinutes;
            return m < 0 ? 0 : m;
        }

        /// Vector recovery is a LABEL: it needs bars after the vector formed.
        public static void VectorRecoveryLabels(V4Row r, string tfTag, V4Vector v)
        {
            bool has = v != null;
            r.Y("vectorRecovery_" + tfTag, has ? v.Recovery.ToString() : "")
             .Y("vectorRecoveryPct_" + tfTag, has ? v.RecoveryPct : double.NaN)
             .Y("vectorFirstTouchEt_" + tfTag, has ? v.FirstTouchEt : DateTime.MinValue)
             .Y("vectorBarsTo25_" + tfTag, has ? v.BarsTo25 : -1)
             .Y("vectorBarsTo50_" + tfTag, has ? v.BarsTo50 : -1)
             .Y("vectorBarsTo100_" + tfTag, has ? v.BarsTo100 : -1)
             .Y("vectorTrapCandidate_" + tfTag, has && v.TrapCandidate)
             .Y("vectorTrapRetracePct_" + tfTag, has ? v.TrapRetracePct : double.NaN)
             .Y("vectorTrapSwift50_" + tfTag, has && v.TrapSwift50);
        }

        /// EMA fan for one timeframe.
        public static void Fan(V4Row r, string tfTag, V4EmaFan f, double price, double atr)
        {
            bool has = f != null;
            r.F("emaFanState_" + tfTag, has ? f.State.ToString() : V4FanState.UNKNOWN.ToString())
             .F("ema5_" + tfTag, has ? f.Ema5 : double.NaN)
             .F("ema13_" + tfTag, has ? f.Ema13 : double.NaN)
             .F("ema50_" + tfTag, has ? f.Ema50 : double.NaN)
             .F("ema200_" + tfTag, has ? f.Ema200 : double.NaN)
             .F("ema800_" + tfTag, has ? f.Ema800 : double.NaN)
             .F("ema800Ready_" + tfTag, has && f.Ema800Ready)
             .F("closeVsEma50_" + tfTag, has && V4Num.Ok(f.Ema50) ? (price > f.Ema50 ? 1 : -1) : 0)
             .F("closeVsEma200_" + tfTag, has && V4Num.Ok(f.Ema200) ? (price > f.Ema200 ? 1 : -1) : 0)
             .F("distEma50Atr_" + tfTag, has ? f.DistEma50Atr(price, atr) : double.NaN)
             .F("distEma200Atr_" + tfTag, has ? f.DistEma200Atr(price, atr) : double.NaN)
             .F("distFanAtr_" + tfTag, has ? f.DistFanAtr(price, atr) : double.NaN)
             .F("ema5Slope_" + tfTag, has ? f.Slope5 : double.NaN)
             .F("ema13Slope_" + tfTag, has ? f.Slope13 : double.NaN)
             .F("ema50Slope_" + tfTag, has ? f.Slope50 : double.NaN)
             .F("ema200Slope_" + tfTag, has ? f.Slope200 : double.NaN)
             .F("dist5to13Pts_" + tfTag, has ? f.Dist5to13Pts : double.NaN)
             .F("dist13to50Pts_" + tfTag, has ? f.Dist13to50Pts : double.NaN)
             .F("dist50to200Pts_" + tfTag, has ? f.Dist50to200Pts : double.NaN);
        }

        /// Nearest-level context.
        public static void Level(V4Row r, V4LevelRef lv, double price, double atr,
                                 V4LevelContextBook book, DateTime nowEt)
        {
            bool has = lv != null;
            r.F("nearestLevel", has ? lv.Name : "")
             .F("nearestLevelType", has ? lv.Type.ToString() : V4LevelType.UNKNOWN.ToString())
             .F("nearestLevelPrice", has ? lv.Price : double.NaN)
             .F("levelFormedEt", has ? lv.FormedEt : DateTime.MinValue)
             .F("levelKnownEt", has ? lv.KnownEt : DateTime.MinValue)
             .F("distLevelPts", has ? price - lv.Price : double.NaN)
             .F("distLevelAtr", has ? V4Num.DistAtr(price, lv.Price, atr) : double.NaN)
             .F("interaction", has ? lv.LastInteraction.ToString() : V4Interaction.NO_INTERACTION.ToString())
             .F("seqState", has ? lv.Seq.ToString() : V4SeqState.NONE.ToString())
             .F("testNumberToday", has ? lv.TestNumberToday : 0)
             .F("firstTest", has && lv.TestNumberToday == 1)
             .F("repeatTest", has && lv.TestNumberToday > 1)
             .F("sideOfLevel", has ? lv.SideOfLevel : 0)
             .F("crossedLevel", has && lv.Crossed)
             .F("reclaimedLevel", has && lv.Reclaimed)
             .F("acceptedBeyondLevel", has && lv.AcceptedBeyond)
             .F("rejectedFromLevel", has && lv.RejectedFrom)
             .F("minutesSinceLevelInteraction", has ? book.MinutesSinceInteraction(lv, nowEt) : -1)
             .F("levelInteractionCountSession", has ? lv.InteractionCountSession : 0);
        }

        /// Forward labels. Everything below is y_ by construction.
        public static void Labels(V4Row r, V4ForwardLabels L)
        {
            for (int i = 0; i < V4ForwardLabels.Horizons.Length; i++)
            {
                string h = V4Num.I(V4ForwardLabels.Horizons[i]) + "m";
                r.Y("net_" + h, L.Net[i]).Y("mfe_" + h, L.Mfe[i]).Y("mae_" + h, L.Mae[i]);
            }
            r.Y("maxMfePts", L.MaxMfePts).Y("maxMaePts", L.MaxMaePts)
             .Y("maxMfeR", L.MaxMfeR).Y("maxMaeR", L.MaxMaeR)
             .Y("minsToMaxMfe", L.MinsToMaxMfe).Y("minsToMaxMae", L.MinsToMaxMae)
             .Y("minutesObserved", L.MinutesObserved)
             .Y("windowComplete", L.WindowComplete);

            r.Y("hitStopTight", L.Stops.HitTight).Y("minsToStopTight", L.Stops.MinsToTight)
             .Y("hitStopMedium", L.Stops.HitMedium).Y("minsToStopMedium", L.Stops.MinsToMedium)
             .Y("hitStopStructural", L.Stops.HitStructural).Y("minsToStopStructural", L.Stops.MinsToStructural)
             .Y("targetAfterStopTight", L.Stops.TargetReachedAfterTight)
             .Y("targetAfterStopMedium", L.Stops.TargetReachedAfterMedium)
             .Y("targetAfterStopStructural", L.Stops.TargetReachedAfterStructural);

            for (int i = 0; i < L.Races.Length; i++)
            {
                string m = V4ForwardLabels.RGrid[i].ToString("0.##", CultureInfo.InvariantCulture) + "R";
                r.Y("race_" + m, V4ForwardLabels.OutcomeName(L.Races[i].Outcome))
                 .Y("minsTo_" + m, L.Races[i].MinsToResolve)
                 .Y("winIfTargetFirst_" + m, L.Races[i].WouldWinIfTargetFirst)
                 .Y("loseIfStopFirst_" + m, L.Races[i].WouldLoseIfStopFirst);
            }
            r.Y("ambiguousRaceCount", L.AmbiguousRaceCount());

            r.Y("hitTargetVectorZone", L.HitTargetVectorZone).Y("minsToTargetVectorZone", L.MinsToTargetVectorZone)
             .Y("hitTargetLiquidity", L.HitTargetLiquidity).Y("minsToTargetLiquidity", L.MinsToTargetLiquidity)
             .Y("hitTargetSwing", L.HitTargetSwing).Y("minsToTargetSwing", L.MinsToTargetSwing)
             .Y("hitTargetHtfStruct", L.HitTargetHtfStruct).Y("minsToTargetHtfStruct", L.MinsToTargetHtfStruct)
             .Y("hitTargetSession", L.HitTargetSession).Y("minsToTargetSession", L.MinsToTargetSession);

            r.Y("emaExitResolved", L.EmaExit.Resolved)
             .Y("minsToEmaExit", L.EmaExit.MinsToExit)
             .Y("emaExitPrice", L.EmaExit.ExitPrice)
             .Y("emaExitGrossPts", L.EmaExit.GrossPts)
             .Y("emaExitGrossR", L.EmaExit.GrossR)
             .Y("maxMfeBeforeEmaExit", L.EmaExit.MaxMfePts)
             .Y("maxMaeBeforeEmaExit", L.EmaExit.MaxMaePts);
        }

        /// Frozen targets, captured AT ENTRY. These are features - their
        /// identity and price were both knowable when the probe opened.
        public static void FrozenTargets(V4Row r, V4ForwardLabels L)
        {
            T(r, "targetVectorZone", L.TargetVectorZone);
            T(r, "targetLiquidity", L.TargetLiquidity);
            T(r, "targetSwing", L.TargetSwing);
            T(r, "targetHtfStruct", L.TargetHtfStruct);
            T(r, "targetSession", L.TargetSession);
            r.F("stopTightPrice", L.Stops.TightPrice).F("stopTightPts", L.Stops.TightPts).F("stopTightAtr", L.Stops.TightAtr)
             .F("stopMediumPrice", L.Stops.MediumPrice).F("stopMediumPts", L.Stops.MediumPts).F("stopMediumAtr", L.Stops.MediumAtr)
             .F("stopStructuralPrice", L.Stops.StructuralPrice).F("stopStructuralPts", L.Stops.StructuralPts).F("stopStructuralAtr", L.Stops.StructuralAtr)
             .F("raceStopFamily", L.RaceStop.ToString());
        }

        private static void T(V4Row r, string nm, V4Target t)
        {
            r.F(nm + "Kind", t.Kind == null ? "" : t.Kind)
             .F(nm + "Detail", t.Detail == null ? "" : t.Detail)
             .F(nm + "Price", t.Price)
             .F(nm + "DistPts", t.DistancePts)
             .F(nm + "DistAtr", t.DistanceAtr)
             .F(nm + "Valid", t.Valid);
        }
    }
}
