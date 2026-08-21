// ======================================================================
// MnqV41VecH1ResearchHost.cs  -  VEC-H1 capture
// ======================================================================
// THIS STRATEGY SUBMITS NO ORDERS.
// It calls no EnterLong, EnterShort, SubmitOrderUnmanaged, SetStopLoss,
// SetProfitTarget, ExitLong or ExitShort. Nothing in this project
// authorizes live trading.
//
// Two series only: 15m (parent vectors, ATR, swings) and 1m (trigger
// vectors and the label clock). Deliberately narrow - VEC-H1 is a
// different EVENT from the break population, and mixing the two
// capture paths is how a hypothesis quietly inherits another one's
// selection.
//
// The host owns no decisions. It does not rank arms, does not filter on
// colour, and emits A, B and C against the SAME parent so none can be
// chosen after the outcomes are known.
// ======================================================================
using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqV41VecH1Research : Strategy
    {
        [NinjaScriptProperty]
        [Display(Name = "File tag", Order = 1, GroupName = "00 Capture")]
        public string FileTag { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Output folder", Order = 2, GroupName = "00 Capture",
                 Description = "Blank writes to the NinjaTrader user data folder.")]
        public string OutputFolder { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Official sample starts (yyyy-MM-dd)", Order = 3, GroupName = "00 Capture",
                 Description = "Rows before this date carry f_isWarmup=TRUE. About 40 days after your data begins is enough.")]
        public string SampleStartDate { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 90.0)]
        [Display(Name = "Min wick pct of range", Order = 1, GroupName = "01 VEC-H1 frozen rule",
                 Description = "PRIMARY = 20. Perturb only as a robustness test, never to find a better number.")]
        public double MinWickPct { get; set; }

        [NinjaScriptProperty]
        [Range(0.01, 2.0)]
        [Display(Name = "Proximity band (ATR)", Order = 2, GroupName = "01 VEC-H1 frozen rule",
                 Description = "PRIMARY = 0.10. The trigger must trade into the wick zone OR come within this many ATR of the extreme.")]
        public double ProximityAtr { get; set; }

        [NinjaScriptProperty]
        [Range(1, 120)]
        [Display(Name = "Search window (minutes)", Order = 3, GroupName = "01 VEC-H1 frozen rule",
                 Description = "PRIMARY = 15, i.e. the immediately-following 15m candle ONLY.")]
        public int WindowMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(2, 200)]
        [Display(Name = "ATR period (15m)", Order = 4, GroupName = "01 VEC-H1 frozen rule")]
        public int AtrPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Pivot confirm bars", Order = 5, GroupName = "01 VEC-H1 frozen rule")]
        public int PivotConfirmBars { get; set; }

        // ==============================================================
        private int Bip15m = 1, Bip1m = 2;
        private TimeZoneInfo etZone;
        private DateTime sampleStartEt = DateTime.MinValue;
        private bool configured, diagPrinted, dataWasLoaded;
        private string outDir = "";
        private long rows;

        private V4VecH1Engine engine;
        private V4VectorEngine vec15, vec1;
        private V4StructureTracker t15;
        private V4Atr atr15;
        private readonly V4StartupDiagnostic diag = new V4StartupDiagnostic();
        private readonly V4ValidityFlags validity = new V4ValidityFlags();
        private readonly V4Schema schema = new V4Schema("vech1");
        private readonly HashSet<string> pathsOpenedThisRun = new HashSet<string>();
        private readonly List<V4OpenEvent> open = new List<V4OpenEvent>();
        private double lastEma9_1m = double.NaN;
        private V4Ema ema9;

        private long armA, armB, armC, parents, lookahead;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqV41VecH1Research";
                Description = "MNQ VEC-H1 parent-wick retrace capture. SUBMITS NO ORDERS.";
                Calculate = Calculate.OnBarClose;
                IsOverlay = false;
                BarsRequiredToTrade = 0;
                BarsRequiredToPlot = 0;
                MaximumBarsLookBack = MaximumBarsLookBack.Infinite;
                IsInstantiatedOnEachOptimizationIteration = false;

                FileTag = "vech1";
                OutputFolder = "";
                SampleStartDate = "";
                MinWickPct = 20.0;
                ProximityAtr = 0.10;
                WindowMinutes = 15;
                AtrPeriod = 20;
                PivotConfirmBars = 2;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Minute, 15); Bip15m = 1;
                AddDataSeries(BarsPeriodType.Minute, 1); Bip1m = 2;
                configured = true;
            }
            else if (State == State.DataLoaded)
            {
                dataWasLoaded = true;
                pathsOpenedThisRun.Clear();
                open.Clear();
                rows = armA = armB = armC = parents = lookahead = 0;
                diagPrinted = false;
                lastEma9_1m = double.NaN;

                engine = new V4VecH1Engine(SymbolName());
                engine.MinWickPctOfRange = MinWickPct;
                engine.ProximityAtrMult = ProximityAtr;
                engine.WindowMinutes = WindowMinutes;

                vec15 = new V4VectorEngine(SymbolName(), "15m", 15);
                vec1 = new V4VectorEngine(SymbolName(), "1m", 1);
                t15 = new V4StructureTracker("15m", 15);
                t15.ConfirmBars = PivotConfirmBars;
                t15.AtrPeriod = AtrPeriod;
                atr15 = new V4Atr(AtrPeriod);
                ema9 = new V4Ema(9);

                try { etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception)
                {
                    try { etZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
                    catch (Exception) { etZone = null; }
                }

                sampleStartEt = DateTime.MinValue;
                DateTime tmp;
                if (!string.IsNullOrEmpty(SampleStartDate) &&
                    DateTime.TryParse(SampleStartDate, CultureInfo.InvariantCulture,
                                      System.Globalization.DateTimeStyles.None, out tmp))
                    sampleStartEt = tmp;

                outDir = string.IsNullOrEmpty(OutputFolder)
                    ? NinjaTrader.Core.Globals.UserDataDir : OutputFolder;
                try { if (!Directory.Exists(outDir)) Directory.CreateDirectory(outDir); }
                catch (Exception) { }
            }
            else if (State == State.Terminated)
            {
                // Same ghost-instance rule as every other host: only an
                // instance that actually LOADED DATA may write anything.
                if (configured && dataWasLoaded) Finish();
            }
        }

        private string SymbolName()
        {
            try
            {
                if (Instrument != null && Instrument.MasterInstrument != null
                    && !string.IsNullOrEmpty(Instrument.MasterInstrument.Name))
                    return Instrument.MasterInstrument.Name;
            }
            catch (Exception) { }
            return "MNQ";
        }

        private DateTime ToEt(DateTime t)
        {
            if (etZone == null) return t;
            try { return TimeZoneInfo.ConvertTime(t, TimeZoneInfo.Local, etZone); }
            catch (Exception) { return t; }
        }

        private V4Bar MakeBar(int minutes)
        {
            V4Bar b = new V4Bar();
            DateTime o, c;
            V4BarStamp.FromNtStamp(ToEt(Time[0]), minutes, out o, out c);
            b.EtOpen = o; b.EtClose = c;
            b.Open = Open[0]; b.High = High[0]; b.Low = Low[0];
            b.Close = Close[0]; b.Volume = Volume[0];
            return b;
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 1) return;
            if (!diagPrinted) PrintStartupDiagnostic();

            if (BarsInProgress == Bip15m) On15m();
            else if (BarsInProgress == Bip1m) On1m();
        }

        private void On15m()
        {
            V4Bar b = MakeBar(15);
            atr15.Add(b);
            double a = atr15.Ready ? atr15.Value : double.NaN;
            t15.OnBar(b);
            DateTime cutoff = V4ResearchEngine.SnapshotCutoff(b);
            V4Swing kh = t15.SwingHighKnownAt(cutoff), kl = t15.SwingLowKnownAt(cutoff);
            V4Vector v = vec15.OnBar(b, a, kh, kl, kh, kl);
            if (engine.On15mBar(b, v, a) != null) parents++;
        }

        private void On1m()
        {
            V4Bar b = MakeBar(1);
            ema9.Update(b.Close);
            lastEma9_1m = ema9.Ready ? ema9.RawValue : double.NaN;

            // advance every open window BEFORE evaluating new triggers
            for (int i = open.Count - 1; i >= 0; i--)
            {
                open[i].Labels.OnBar(b, lastEma9_1m);
                if (open[i].Labels.WindowComplete) { WriteCompleted(open[i]); open.RemoveAt(i); }
            }

            V4Swing dummy = new V4Swing();
            V4Vector v1 = vec1.OnBar(b, double.NaN, dummy, dummy, dummy, dummy);

            List<V4VecH1Signal> sigs = engine.On1mBar(b, v1);
            for (int i = 0; i < sigs.Count; i++) OpenSignal(sigs[i], b);
            lookahead = engine.LookaheadRejected;
        }

        private void OpenSignal(V4VecH1Signal s, V4Bar b)
        {
            V4VecH1Parent p = s.Parent;
            bool warm = sampleStartEt != DateTime.MinValue && s.EntryEt < sampleStartEt;

            V4EventKeys keys = new V4EventKeys();
            keys.ParentEventId = p.ParentId;
            keys.EventId = p.ParentId + "-" + s.Arm.ToString();
            keys.EntryProbeId = keys.EventId;
            keys.HypothesisId = "VEC-H1";
            keys.RawSignalCount = 1;

            V4Row r = new V4Row(s.EntryEt);
            V4RowBuilder.Keys(r, keys, SymbolName(), "1m", V4ResearchClass.CONFIRMATORY,
                              V4HypothesisClass.A_MARKET_EDGE, V4DataLayer.STRUCTURE_VECTOR);

            r.F("isWarmup", warm)
             .F("arm", s.Arm.ToString())
             .F("side", p.Side)
             .F("parentCloseEt", p.CloseEt)
             .F("parentColor", p.Color.ToString())
             .F("parentTier", p.Tier.ToString())
             .F("parentOpen", p.Open).F("parentHigh", p.High)
             .F("parentLow", p.Low).F("parentClose", p.Close)
             .F("parentRangePts", p.RangePts).F("parentAtr", p.Atr)
             .F("parentRelVolume", p.RelVolume)
             .F("parentWickPts", p.WickPts)
             .F("parentWickPctOfRange", p.WickPctOfRange)
             .F("parentWickAtr", p.WickAtr)
             .F("parentExtreme", p.Extreme)
             .F("parentWickInnerEdge", p.WickInnerEdge)
             .F("proximityBandPts", p.ProximityBand)
             .F("windowEndEt", p.WindowEndEt)
             .F("windowOpenPrice", p.WindowOpenPrice)
             .F("retraceSeen", s.RetraceSeen)
             .F("barIndexInWindow", s.BarIndexInWindow)
             .F("minsFromParentClose", s.MinsFromParentClose)
             .F("distToExtremePts", s.DistToExtremePts)
             .F("distToExtremeAtr", s.DistToExtremeAtr)
             .F("touchedExtreme", s.TouchedExtreme)
             .F("tradedIntoWick", s.TradedIntoWick)
             .F("withinAtrBand", s.WithinAtrBand)
             .F("hasTriggerVector", s.TriggerVector != null)
             .F("triggerColor", s.TriggerVector == null ? "NONE" : s.TriggerVector.Color.ToString())
             .F("triggerTier", s.TriggerVector == null ? "NONE" : s.TriggerVector.Tier.ToString())
             .F("triggerRelVolume", s.TriggerVector == null ? double.NaN : s.TriggerVector.RelVolume)
             .F("entryEt", s.EntryEt)
             .F("entryPrice", s.EntryPrice)
             .F("triggerHigh", b.High).F("triggerLow", b.Low)
             .F("triggerRangePts", b.High - b.Low)
             .F("ema9_1m", lastEma9_1m)
             .F("closeVsEma9_1m", V4Num.Ok(lastEma9_1m) ? (b.Close > lastEma9_1m ? 1 : -1) : 0);
            V4RowBuilder.Session(r, s.EntryEt);

            V4OpenEvent oe = new V4OpenEvent();
            oe.EventVector = null;              // recovery block not used by this host
            oe.VectorTfTag = "15m";

            double tight, medium, structural;
            V4VecH1Engine.StopRefs(s, TickSize, out tight, out medium, out structural);
            double atr = V4Num.Ok(p.Atr) && p.Atr > 0 ? p.Atr : 1.0;
            oe.Labels.Stops.Freeze(p.Side, s.EntryPrice, atr, tight, medium, structural);
            oe.Labels.RaceStop = V4StopKind.MEDIUM;

            // targets that this host can compute causally
            DateTime cutoff = V4ResearchEngine.SnapshotCutoff(b);
            V4Vector vz = p.Side > 0
                ? vec15.NearestUnrecoveredAbove(s.EntryPrice, cutoff)
                : vec15.NearestUnrecoveredBelow(s.EntryPrice, cutoff);
            oe.Labels.TargetVectorZone = vz == null ? V4Target.None()
                : V4Target.Make("VECTOR_ZONE", vz.VectorId, vz.FarEdge, s.EntryPrice, p.Side, atr);
            V4Swing sh = t15.SwingHighKnownAt(cutoff), sl = t15.SwingLowKnownAt(cutoff);
            double swing = p.Side > 0 ? (sh.Valid ? sh.Price : double.NaN)
                                      : (sl.Valid ? sl.Price : double.NaN);
            oe.Labels.TargetSwing = V4Target.Make("SWING", "15m", swing, s.EntryPrice, p.Side, atr);

            V4RowBuilder.FrozenTargets(r, oe.Labels);

            if (!schema.Established) schema.Establish(V4OpenEvent.SchemaRow(r, "15m", s.EntryEt));
            schema.Verify(V4OpenEvent.SchemaRow(r, "15m", s.EntryEt));

            oe.Freeze(r, s.EntryEt);
            oe.Labels.Open(p.Side, s.EntryPrice, s.EntryEt, atr, lastEma9_1m);
            open.Add(oe);

            if (s.Arm == V4VecH1Arm.A_LOCATION_ONLY) armA++;
            else if (s.Arm == V4VecH1Arm.B_VECTOR_AWAY) armB++;
            else armC++;
        }

        private void WriteCompleted(V4OpenEvent oe)
        {
            Append("vech1", oe.EventEt, schema.Header, oe.CompletedCsv());
            rows++;
        }

        private void Append(string kind, DateTime rowEt, string header, string line)
        {
            string path = Path.Combine(outDir,
                "v4_1_" + kind + "_" + SymbolName() + "_" + FileTag + "_"
                + rowEt.ToString("yyyy-MM", CultureInfo.InvariantCulture) + ".csv");
            try
            {
                bool firstTouch = !pathsOpenedThisRun.Contains(path);
                if (firstTouch) pathsOpenedThisRun.Add(path);
                bool needHeader = firstTouch || !File.Exists(path);
                using (StreamWriter w = new StreamWriter(path, !firstTouch))
                {
                    if (needHeader) w.WriteLine(header);
                    w.WriteLine(line);
                }
                if (firstTouch) Print("  VEC-H1 writing " + Path.GetFileName(path));
            }
            catch (Exception e) { Print("VEC-H1 write failed: " + e.Message); }
        }

        private void PrintStartupDiagnostic()
        {
            diagPrinted = true;
            diag.Instrument = SymbolName();
            diag.MergePolicy = "back-adjusted continuous (assumed)";
            diag.SessionTemplate = "CME US Index Futures ETH (the full 24h session, as configured)";
            diag.TimeZone = etZone == null ? "UNRESOLVED" : etZone.Id;
            diag.PrimarySeries = "chart series, unused (BarsInProgress 0)";
            diag.FileTag = FileTag;
            diag.SampleStartEt = sampleStartEt;
            diag.RequiredWarmupBars1m = 800 * 3 * 15;
            diag.WarmupReason = "EMA800 is not used by VEC-H1; the binding warm-up is the "
                              + AtrPeriod + "-bar 15m ATR and the 10-bar PVSRA baseline";
            int b15 = 0, b1 = 0;
            try { if (BarsArray != null && BarsArray.Length > Bip15m) b15 = BarsArray[Bip15m].Count; }
            catch (Exception) { }
            try { if (BarsArray != null && BarsArray.Length > Bip1m) b1 = BarsArray[Bip1m].Count; }
            catch (Exception) { }
            diag.AddSeries("15m", Bip15m, b15, DateTime.MinValue, DateTime.MinValue, true, "15m bars");
            diag.AddSeries("1m", Bip1m, b1, DateTime.MinValue, DateTime.MinValue, true, "1m bars");
            diag.Validate();
            PrintLines(diag.Text());
            PrintLines(validity.Summary());
        }

        private void PrintLines(string s)
        {
            if (string.IsNullOrEmpty(s)) return;
            string[] parts = s.Split('\n');
            for (int i = 0; i < parts.Length; i++) Print(parts[i].TrimEnd('\r'));
        }

        private void Finish()
        {
            if (!diagPrinted)
            {
                diag.Instrument = SymbolName();
                diag.FileTag = FileTag;
                diag.PrimarySeries = "SERIES LOADED ZERO BARS";
                diag.AddSeries("15m", Bip15m, 0, DateTime.MinValue, DateTime.MinValue, true, "15m bars");
                diag.Validate();
                PrintLines(diag.Text());
                Print("NO BARS ARRIVED: check instrument, date range and strategy selection.");
            }
            // windows still open at the end of the run never completed;
            // they are dropped rather than written with partial labels
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("VEC-H1 CAPTURE AUDIT");
            sb.AppendLine("======================================================================");
            sb.AppendLine("  qualifying parents        " + parents);
            sb.AppendLine("  ARM C  full VEC-H1        " + armC);
            sb.AppendLine("  ARM B  vector away        " + armB);
            sb.AppendLine("  ARM A  location, no vec   " + armA);
            sb.AppendLine("  rows written              " + rows);
            sb.AppendLine("  windows dropped unclosed  " + open.Count);
            sb.AppendLine("  LOOKAHEAD REJECTED        " + lookahead
                        + "   (triggers at or before the parent close; must be 0 in a");
            sb.AppendLine("                              clean run - any value above zero means the");
            sb.AppendLine("                              1m clock is not strictly after the 15m close)");
            sb.AppendLine("  frozen rule: wick >= " + MinWickPct.ToString("0.#", CultureInfo.InvariantCulture)
                        + "% of parent range, proximity "
                        + ProximityAtr.ToString("0.##", CultureInfo.InvariantCulture)
                        + " x ATR, window " + WindowMinutes + " min");
            sb.AppendLine("  PRIMARY STOP = 1.5 x parent 15m ATR (the race stop).");
            sb.AppendLine("  Arms A, B and C are emitted against the SAME parent. C vs A");
            sb.AppendLine("  isolates the vector; C vs B isolates the location. Reporting");
            sb.AppendLine("  C alone would not distinguish the hypothesis from the fact");
            sb.AppendLine("  that same-colour vectors tend to follow one another.");
            sb.AppendLine("======================================================================");
            PrintLines(sb.ToString());
            try
            {
                string p = Path.Combine(outDir, "v4_1_VECH1_AUDIT_" + FileTag + ".txt");
                using (StreamWriter w = new StreamWriter(p, false))
                {
                    w.Write(diag.Text()); w.Write(validity.Summary()); w.Write(sb.ToString());
                    w.WriteLine(schema.Describe());
                }
            }
            catch (Exception e) { Print("VEC-H1 audit write failed: " + e.Message); }
        }
    }
}
