// ======================================================================
// MnqV41StructureResearchHost.cs  -  MNQ V4.1
// ======================================================================
// The NinjaTrader 8 host for the structure / vector / level / EMA-fan
// capture. Runs on ordinary OHLCV, so it covers the full history.
//
// THIS STRATEGY SUBMITS NO ORDERS.
// It calls no EnterLong, EnterShort, SubmitOrderUnmanaged, SetStopLoss,
// SetProfitTarget, ExitLong or ExitShort. Nothing in this project
// authorizes live trading.
//
// What the host is responsible for, and what it deliberately is not:
//
//   IS  : owning the series map, driving each engine with COMPLETED bars
//         of its own timeframe only, freezing features at the event
//         instant, opening entry probes, advancing labels on the 1m
//         clock, and writing month-routed CSV.
//
//   IS NOT : deciding anything. It does not rank hypotheses, does not
//         filter on vector colour or EMA state, and does not choose a
//         best architecture. Every candidate architecture is emitted
//         against the SAME parent event so the research layer can compare
//         them; letting the engine pick would be selection with no audit
//         trail.
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
    public class MnqV41StructureResearch : Strategy
    {
        // ==============================================================
        // PARAMETERS
        // ==============================================================

        [NinjaScriptProperty]
        [Display(Name = "File tag", Order = 1, GroupName = "00 Capture",
                 Description = "Appended to every output filename so two runs cannot overwrite each other.")]
        public string FileTag { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Output folder", Order = 2, GroupName = "00 Capture",
                 Description = "Blank writes to the NinjaTrader user data folder.")]
        public string OutputFolder { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Official sample starts (yyyy-MM-dd)", Order = 3, GroupName = "00 Capture",
                 Description = "Rows before this date carry f_isWarmup=TRUE and must be excluded. Blank means every row counts.")]
        public string SampleStartDate { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Write entry probes", Order = 4, GroupName = "00 Capture",
                 Description = "The per-architecture entry file. Turn off for a structure-only pass.")]
        public bool WriteEntries { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Daily", Order = 1, GroupName = "01 Timeframes")]
        public bool UseDaily { get; set; }
        [NinjaScriptProperty]
        [Display(Name = "4 hour", Order = 2, GroupName = "01 Timeframes")]
        public bool Use4h { get; set; }
        [NinjaScriptProperty]
        [Display(Name = "60 minute", Order = 3, GroupName = "01 Timeframes")]
        public bool Use60m { get; set; }
        [NinjaScriptProperty]
        [Display(Name = "15 minute", Order = 4, GroupName = "01 Timeframes")]
        public bool Use15m { get; set; }
        [NinjaScriptProperty]
        [Display(Name = "5 minute", Order = 5, GroupName = "01 Timeframes")]
        public bool Use5m { get; set; }
        [NinjaScriptProperty]
        [Display(Name = "3 minute", Order = 6, GroupName = "01 Timeframes")]
        public bool Use3m { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Pivot confirm bars", Order = 1, GroupName = "02 Swing definition",
                 Description = "Bars that must close to the RIGHT before a swing is knowable.")]
        public int PivotConfirmBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Pivot left bars", Order = 2, GroupName = "02 Swing definition")]
        public int PivotLeftBars { get; set; }

        [NinjaScriptProperty]
        [Range(0.01, 1.0)]
        [Display(Name = "Equality band (ATR)", Order = 3, GroupName = "02 Swing definition",
                 Description = "Two swings within this fraction of ATR count as EQUAL.")]
        public double EqualityBandAtr { get; set; }

        [NinjaScriptProperty]
        [Range(2, 200)]
        [Display(Name = "ATR period", Order = 4, GroupName = "02 Swing definition")]
        public int AtrPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 3.0)]
        [Display(Name = "Approach band (ATR)", Order = 1, GroupName = "03 Level context",
                 Description = "Inside this many ATR of a level counts as interacting.")]
        public double ApproachBandAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 3.0)]
        [Display(Name = "Test cluster exit (ATR)", Order = 2, GroupName = "03 Level context",
                 Description = "Clear of the level by this much closes an open test. Stops a 10-bar chop counting as 10 tests.")]
        public double ClusterExitAtr { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Test cluster gap bars", Order = 3, GroupName = "03 Level context")]
        public int ClusterGapBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Acceptance bars", Order = 4, GroupName = "03 Level context",
                 Description = "Consecutive closes beyond a level that constitute acceptance.")]
        public int AcceptanceBars { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 5.0)]
        [Display(Name = "Trap min range (ATR)", Order = 1, GroupName = "04 Vector")]
        public double TrapMinRangeAtr { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 100.0)]
        [Display(Name = "Trap retrace pct", Order = 2, GroupName = "04 Vector")]
        public double TrapRetracePct { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Trap swift bars", Order = 3, GroupName = "04 Vector")]
        public int TrapSwiftBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, 240)]
        [Display(Name = "Max entry delay (minutes)", Order = 1, GroupName = "05 Entry probes",
                 Description = "A probe that has not triggered inside this window EXPIRES.")]
        public int MaxEntryDelayMinutes { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name = "Control sample rate", Order = 2, GroupName = "05 Entry probes",
                 Description = "Emit one matched non-event control row every N 15m bars. 0 disables controls.")]
        public int ControlSampleRate { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "ARCH-C 1m execution", Order = 4, GroupName = "05 Entry probes",
                 Description = "How the 1m layer executes after the 3m layer confirms. IMMEDIATE makes ARCH-C identical to ARCH-B - it is kept only to reproduce the old behaviour.")]
        public V4LtfExecution LtfExecution { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 3.0)]
        [Display(Name = "ARCH-C pullback (ATR)", Order = 5, GroupName = "05 Entry probes",
                 Description = "Retrace off the best price since confirmation that arms a PULLBACK execution.")]
        public double PullbackAtr { get; set; }

        [NinjaScriptProperty]
        [Range(1, 480)]
        [Display(Name = "Thesis cluster window (minutes)", Order = 3, GroupName = "05 Entry probes",
                 Description = "Events on one timeframe and side inside this window share a ParentEventID.")]
        public int ThesisClusterMinutes { get; set; }

        // ==============================================================
        // STATE
        // ==============================================================

        private int BipDaily = -1, Bip4h = -1, Bip60m = -1, Bip15m = -1, Bip5m = -1, Bip3m = -1, Bip1m = -1;
        private readonly Dictionary<int, string> bipLabel = new Dictionary<int, string>();
        private readonly Dictionary<string, V4StructureTracker> trackers = new Dictionary<string, V4StructureTracker>();
        private readonly Dictionary<string, V4VectorEngine> vectors = new Dictionary<string, V4VectorEngine>();
        private readonly Dictionary<string, V4EmaFan> fans = new Dictionary<string, V4EmaFan>();

        private readonly V4LevelContextBook levels = new V4LevelContextBook();
        private readonly V4LocationBook location = new V4LocationBook();
        private readonly V4RangeBook ranges = new V4RangeBook();
        private readonly V4ValidityFlags validity = new V4ValidityFlags();
        private readonly V4ThesisClusterer clusterer = new V4ThesisClusterer();
        private readonly V4StructureAudit audit = new V4StructureAudit();
        private readonly V4StartupDiagnostic diag = new V4StartupDiagnostic();
        private V4HypothesisRegistry registry;

        private readonly V4Ema ema9_1m = new V4Ema(9);
        private double lastEma9_1m = double.NaN;

        private readonly V4Schema structSchema = new V4Schema("structure");
        private readonly V4Schema entrySchema = new V4Schema("entries");
        private readonly HashSet<string> pathsOpenedThisRun = new HashSet<string>();
        private readonly List<PendingProbe> pending = new List<PendingProbe>();
        private readonly List<PendingProbe> openProbes = new List<PendingProbe>();
        private readonly List<V4OpenEvent> openEvents = new List<V4OpenEvent>();

        /// A parent event whose FEATURES are already frozen as text, waiting
        /// for its forward window to close so the labels can be appended.
        ///
        /// The first sample shipped a structure file with 9 label columns,
        /// all of them vector recovery - so the parent event had no forward
        /// outcome of its own and the B1/B3/B4 ablations (structure vs
        /// vector, vs level, vs EMA fan) had nothing to compare. Freezing
        /// the feature text at the event instant and appending labels later
        /// gives the parent an outcome without ever letting a later value
        /// reach a feature column.

        private TimeZoneInfo etZone;
        private DateTime sampleStartEt = DateTime.MinValue;
        private bool configured, aborted, diagPrinted;
        private int fifteenBarCount;
        private long structRows, entryRows;
        private string outDir = "";

        // Fires once per excursion rather than on every bar price spends
        // beyond a level. See V4BreakGate for what that distinction cost.
        private readonly V4BreakGate breakGate = new V4BreakGate();

        /// One entry probe awaiting a trigger, then awaiting its labels.
        private class PendingProbe
        {
            public V4EventKeys Keys = new V4EventKeys();
            public string Architecture = "";
            public string EntryTf = "";
            public string Trigger = "";
            public int Side;
            public DateTime EventEt;
            public double EventClose;
            public double TriggerLevel;
            public double AtrAtEvent;
            public bool Triggered;
            public bool NeedsConfirm;              // ARCH-C: 3m confirm before 1m execution
            public bool Confirmed;
            public readonly V4LtfExecutionGate Gate = new V4LtfExecutionGate();
            public bool PullbackArmed { get { return Gate.Armed; } }
            public DateTime EntryEt = DateTime.MinValue;
            public double EntryPrice = double.NaN;
            public int MinsToEntry = -1;
            public V4ForwardLabels Labels = new V4ForwardLabels();
            public string ParentVectorId = "";
            public string EventKind = "";
            public V4AblationFlags Flags;
        }

        // ==============================================================
        // LIFECYCLE
        // ==============================================================

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqV41StructureResearch";
                Description = "MNQ V4.1 structure + vector + level + EMA fan research capture. SUBMITS NO ORDERS.";
                Calculate = Calculate.OnBarClose;
                IsOverlay = false;
                BarsRequiredToTrade = 0;
                BarsRequiredToPlot = 0;
                // Infinite lookback: the engines index back through their own
                // history and a truncated series would silently shorten it.
                MaximumBarsLookBack = MaximumBarsLookBack.Infinite;
                IsInstantiatedOnEachOptimizationIteration = false;

                FileTag = "v41";
                OutputFolder = "";
                SampleStartDate = "";
                WriteEntries = true;

                UseDaily = true; Use4h = true; Use60m = true;
                Use15m = true; Use5m = true; Use3m = true;

                PivotConfirmBars = 2;
                PivotLeftBars = 2;
                EqualityBandAtr = 0.10;
                AtrPeriod = 20;

                ApproachBandAtr = 0.35;
                ClusterExitAtr = 0.50;
                ClusterGapBars = 3;
                AcceptanceBars = 3;

                TrapMinRangeAtr = 1.0;
                TrapRetracePct = 50.0;
                TrapSwiftBars = 3;

                MaxEntryDelayMinutes = 60;
                ControlSampleRate = 400;
                ThesisClusterMinutes = 60;
                LtfExecution = V4LtfExecution.PULLBACK;
                PullbackAtr = 0.35;
            }
            else if (State == State.Configure)
            {
                int next = 1;   // BarsInProgress 0 is the chart series and is unused
                if (UseDaily) { AddDataSeries(BarsPeriodType.Day, 1); BipDaily = next++; }
                if (Use4h) { AddDataSeries(BarsPeriodType.Minute, 240); Bip4h = next++; }
                if (Use60m) { AddDataSeries(BarsPeriodType.Minute, 60); Bip60m = next++; }
                if (Use15m) { AddDataSeries(BarsPeriodType.Minute, 15); Bip15m = next++; }
                if (Use5m) { AddDataSeries(BarsPeriodType.Minute, 5); Bip5m = next++; }
                if (Use3m) { AddDataSeries(BarsPeriodType.Minute, 3); Bip3m = next++; }
                // 1m is added LAST and is mandatory. It is the label clock:
                // every forward measurement in the dataset is advanced by it.
                AddDataSeries(BarsPeriodType.Minute, 1); Bip1m = next++;
                configured = true;
            }
            else if (State == State.DataLoaded)
            {
                // A reused instance must not remember which files the PREVIOUS
                // run opened. IsInstantiatedOnEachOptimizationIteration is
                // false, so NinjaTrader may hand this object a second run - and
                // truncate-on-first-touch would then see every path as already
                // touched and append instead of replacing. That is exactly how
                // an earlier version produced duplicate copies of every row.
                pathsOpenedThisRun.Clear();
                pending.Clear(); openProbes.Clear();
                trackers.Clear(); vectors.Clear(); fans.Clear();
                clusterer.Reset();
                structRows = entryRows = 0;
                fifteenBarCount = 0;
                aborted = false; diagPrinted = false;
                breakGate.Reset();
                openEvents.Clear();

                try { etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception)
                {
                    try { etZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
                    catch (Exception) { etZone = null; }
                }

                bipLabel.Clear();
                if (BipDaily > 0) bipLabel[BipDaily] = "1d";
                if (Bip4h > 0) bipLabel[Bip4h] = "4h";
                if (Bip60m > 0) bipLabel[Bip60m] = "60m";
                if (Bip15m > 0) bipLabel[Bip15m] = "15m";
                if (Bip5m > 0) bipLabel[Bip5m] = "5m";
                if (Bip3m > 0) bipLabel[Bip3m] = "3m";
                bipLabel[Bip1m] = "1m";

                foreach (KeyValuePair<int, string> kv in bipLabel)
                {
                    string lab = kv.Value;
                    int mins = MinutesOf(lab);
                    V4StructureTracker t = new V4StructureTracker(lab, mins);
                    t.ConfirmBars = PivotConfirmBars;
                    t.PivotLeftBars = PivotLeftBars;
                    t.EqualityBandAtr = EqualityBandAtr;
                    t.AtrPeriod = AtrPeriod;
                    trackers[lab] = t;

                    V4VectorEngine ve = new V4VectorEngine(SymbolName(), lab, mins);
                    ve.TrapMinRangeAtr = TrapMinRangeAtr;
                    ve.TrapRetracePct = TrapRetracePct;
                    ve.TrapSwiftBars = TrapSwiftBars;
                    ve.EqualityTolAtr = EqualityBandAtr;
                    vectors[lab] = ve;

                    fans[lab] = new V4EmaFan(lab);
                }

                levels.ApproachBandAtr = ApproachBandAtr;
                levels.ClusterExitAtr = ClusterExitAtr;
                levels.ClusterGapBars = ClusterGapBars;
                levels.AcceptanceBars = AcceptanceBars;
                clusterer.ClusterWindowMinutes = ThesisClusterMinutes;

                registry = V4HypothesisRegistry.Default();

                sampleStartEt = DateTime.MinValue;
                if (!string.IsNullOrEmpty(SampleStartDate))
                {
                    DateTime d;
                    if (DateTime.TryParseExact(SampleStartDate, "yyyy-MM-dd",
                            CultureInfo.InvariantCulture, DateTimeStyles.None, out d))
                        sampleStartEt = d;
                }

                outDir = string.IsNullOrEmpty(OutputFolder)
                    ? NinjaTrader.Core.Globals.UserDataDir
                    : OutputFolder;
                try { if (!Directory.Exists(outDir)) Directory.CreateDirectory(outDir); }
                catch (Exception) { }
            }
            else if (State == State.Terminated)
            {
                if (!aborted && configured) Finish();
            }
        }

        private static int MinutesOf(string tf)
        {
            if (tf == "1d") return 1440;
            if (tf == "4h") return 240;
            if (tf == "60m") return 60;
            if (tf == "15m") return 15;
            if (tf == "5m") return 5;
            if (tf == "3m") return 3;
            return 1;
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

        // ==============================================================
        // STARTUP DIAGNOSTIC
        // ==============================================================

        private void PrintStartupDiagnostic()
        {
            diagPrinted = true;
            diag.Instrument = SymbolName();
            diag.MergePolicy = "back-adjusted continuous (assumed) - PSY / round-number family disabled";
            diag.SessionTemplate = "CME US Index Futures RTH+ETH (as configured on the series)";
            diag.TimeZone = etZone == null ? "LOCAL (ET zone NOT resolved - timestamps are local)" : etZone.Id;
            diag.PrimarySeries = "chart series, unused (BarsInProgress 0)";
            diag.FileTag = FileTag;
            diag.VolumetricPrimary = false;
            diag.OrderFlowAvailable = false;
            diag.ProfileAvailable = false;
            diag.DepthAvailable = false;
            diag.SampleStartEt = sampleStartEt;

            // EMA800 on the slowest series drives warm-up. V4Ema needs three
            // periods before it reports a value, so 800 x 3 bars of the
            // slowest fan timeframe is the real requirement.
            int slowest = 1;
            foreach (KeyValuePair<int, string> kv in bipLabel)
            {
                int m = MinutesOf(kv.Value);
                if (m != 1440 && m > slowest) slowest = m;
            }
            diag.RequiredWarmupBars1m = 800 * 3 * slowest;
            diag.WarmupReason = "EMA800 on the " + slowest + "m series needs 2400 completed bars ("
                              + (800 * 3 * slowest / 1440) + " days) before it reports a value";

            foreach (KeyValuePair<int, string> kv in bipLabel)
            {
                int bip = kv.Key;
                int bars = 0; DateTime f = DateTime.MinValue, l = DateTime.MinValue;
                try
                {
                    if (BarsArray != null && bip < BarsArray.Length && BarsArray[bip] != null)
                        bars = BarsArray[bip].Count;
                }
                catch (Exception) { }
                diag.AddSeries(kv.Value, bip, bars, f, l, true, kv.Value + " bars");
            }

            bool ok = diag.Validate();
            PrintLines(diag.Text());
            PrintLines(validity.Summary());
            if (!ok)
            {
                aborted = true;
                Print("V4.1: RUN ABORTED. Fix the series configuration and run again.");
            }
        }

        private void PrintLines(string s)
        {
            if (string.IsNullOrEmpty(s)) return;
            string[] parts = s.Split('\n');
            for (int i = 0; i < parts.Length; i++) Print(parts[i].TrimEnd('\r'));
        }

        // ==============================================================
        // BAR DISPATCH
        // ==============================================================

        protected override void OnBarUpdate()
        {
            if (!configured || aborted) return;
            if (!diagPrinted && CurrentBars[0] >= 0) PrintStartupDiagnostic();
            if (aborted) return;

            int bip = BarsInProgress;
            if (bip == 0) return;                       // chart series is unused
            string tf;
            if (!bipLabel.TryGetValue(bip, out tf)) return;
            if (CurrentBars[bip] < 1) return;

            V4Bar b = new V4Bar();
            // NinjaTrader stamps a COMPLETED bar at its CLOSE, not its open.
            // Reading that stamp as the open put every timestamp in every
            // output file one whole bar-period into the future, and the
            // symptom was unmissable once the data existed: ARCH-A reported a
            // median minsToEntry of MINUS TWELVE, an entry preceding its own
            // event by 12 minutes.
            //
            // The quieter half of the damage mattered more. With 15m events
            // stamped +15 and 1m bars stamped +1, the SnapshotCutoff was
            // wildly permissive, and the only thing still preventing
            // lookahead was the order NinjaTrader happens to deliver series
            // in. That is precisely the dependency SnapshotCutoff was written
            // to eliminate. Reading the stamp correctly puts the guard back
            // where it belongs.
            V4BarStamp.FromNtStamp(ToEt(Times[bip][0]), MinutesOf(tf), out b.EtOpen, out b.EtClose);
            b.Open = Opens[bip][0]; b.High = Highs[bip][0];
            b.Low = Lows[bip][0]; b.Close = Closes[bip][0];
            b.Volume = Volumes[bip][0];

            V4StructureTracker t = trackers[tf];
            t.OnBar(b);
            double atr = t.AtrValue;

            fans[tf].OnBar(b, atr);

            DateTime cutoff = V4ResearchEngine.SnapshotCutoff(b);
            V4Swing kh = t.SwingHighKnownAt(cutoff);
            V4Swing kl = t.SwingLowKnownAt(cutoff);
            V4Swing ph = t.PriorSwingHighKnownAt(cutoff);
            V4Swing pl = t.PriorSwingLowKnownAt(cutoff);
            V4Vector v = vectors[tf].OnBar(b, atr, kh, kl, ph, pl);
            if (tf == "15m") audit.NoteVector(v == null ? V4VectorColor.NONE : v.Color);

            if (bip == Bip1m) On1mBar(b, atr);
            else if (tf == "3m") On3mBar(b, atr);
            else if (tf == "15m") On15mBar(b, atr, t, v, kh, kl);
        }

        // ---- the 3m layer: ARCH-B entries and the ARCH-C confirmation --
        //
        // Without this the whole architecture comparison is dead. The first
        // sample returned 1533 of 1533 entry rows as ARCH-A, because 3m
        // probes were skipped in the 1m loop and nothing ever set the
        // ARCH-C confirmation flag - so two of the three declared
        // architectures could never produce a single row.
        private void On3mBar(V4Bar b, double atr3m)
        {
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                PendingProbe p = pending[i];
                if ((b.EtClose - p.EventEt).TotalMinutes > MaxEntryDelayMinutes)
                { pending.RemoveAt(i); continue; }
                if (b.EtClose <= p.EventEt) continue;

                // ARCH-C: the 3m bar is the SETUP layer. It confirms, and the
                // 1m layer then executes. Confirmation is a close in the
                // event's direction - the same test ARCH-B uses to enter, so
                // the two architectures are separated by execution only.
                if (p.NeedsConfirm && !p.Confirmed)
                {
                    bool go3 = p.Side > 0 ? b.Close > p.EventClose : b.Close < p.EventClose;
                    if (go3) p.Confirmed = true;
                    continue;
                }

                if (p.EntryTf != "3m") continue;
                if (TryTrigger(p, b, atr3m)) { pending.RemoveAt(i); openProbes.Add(p); }
            }
        }

        // ---- the 1m clock: levels, labels, probes ---------------------

        private void On1mBar(V4Bar b, double atr1m)
        {
            ema9_1m.Update(b.Close);
            lastEma9_1m = ema9_1m.Value;

            location.Apply(b);
            int dayKey = location.ExchangeDayKey(b.EtClose);
            int weekKey = location.ExchangeWeekKey(b.EtClose);
            ranges.OnBar(b, dayKey, weekKey);

            RefreshLevelBook(b, dayKey);
            levels.OnBar(b, atr1m, dayKey);
            audit.NoteBar(b, dayKey);

            // trigger any probe still waiting, then advance the ones running
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                PendingProbe p = pending[i];
                double mins = (b.EtClose - p.EventEt).TotalMinutes;
                if (mins > MaxEntryDelayMinutes) { pending.RemoveAt(i); continue; }
                // A bar closing at or before the event instant cannot trigger
                // it. The 3m path already had this guard; the 1m path did
                // not, which is why ARCH-A was the architecture that showed
                // the negative delay while ARCH-B and ARCH-C did not.
                if (b.EtClose <= p.EventEt) continue;
                if (p.EntryTf != "1m") continue;
                if (p.NeedsConfirm && !p.Confirmed) continue;
                // ARCH-A has no 3m layer and enters immediately by definition,
                // so only the confirm-carrying probes consult the gate.
                if (p.NeedsConfirm && !p.Gate.Ready(p.Side, b.High, b.Low, atr1m)) continue;
                if (TryTrigger(p, b, atr1m)) { pending.RemoveAt(i); openProbes.Add(p); }
            }

            for (int i = openProbes.Count - 1; i >= 0; i--)
            {
                PendingProbe p = openProbes[i];
                p.Labels.OnBar(b, lastEma9_1m);
                if (p.Labels.WindowComplete)
                {
                    WriteEntryRow(p);
                    openProbes.RemoveAt(i);
                }
            }

            // parent events advance on the same 1m clock
            for (int i = openEvents.Count - 1; i >= 0; i--)
            {
                V4OpenEvent oe = openEvents[i];
                oe.Labels.OnBar(b, lastEma9_1m);
                if (oe.Labels.WindowComplete)
                {
                    WriteCompletedEvent(oe);
                    openEvents.RemoveAt(i);
                }
            }
        }

        /// Publish every causally-known level into the context book. Called
        /// on the 1m clock so nothing enters the book before it exists.
        private void RefreshLevelBook(V4Bar b, int dayKey)
        {
            DateTime now = b.EtClose;
            Pub("PDH", V4LevelType.PRIOR_DAY_HIGH, location.PriorDayHigh, now);
            Pub("PDL", V4LevelType.PRIOR_DAY_LOW, location.PriorDayLow, now);
            Pub("PWH", V4LevelType.PRIOR_WEEK_HIGH, location.PriorWeekHigh, now);
            Pub("PWL", V4LevelType.PRIOR_WEEK_LOW, location.PriorWeekLow, now);
            Pub("SESS_OPEN", V4LevelType.DAILY_OPEN, location.SessionOpen, now);
            Pub("SESS_HIGH", V4LevelType.SESSION_HIGH, location.SessionHigh, now);
            Pub("SESS_LOW", V4LevelType.SESSION_LOW, location.SessionLow, now);
            Pub("VWAP", V4LevelType.SESSION_VWAP, location.SessionVwap, now);

            foreach (KeyValuePair<string, V4StructureTracker> kv in trackers)
            {
                if (kv.Key == "1d") continue;
                DateTime cutoff = now.AddSeconds(-1);
                V4Swing h = kv.Value.SwingHighKnownAt(cutoff);
                V4Swing l = kv.Value.SwingLowKnownAt(cutoff);
                if (h.Valid) Pub("SWING_" + kv.Key + "_HIGH", V4LevelType.SWING_HIGH, h.Price, h.KnownAtEt, h.FormedAtEt);
                if (l.Valid) Pub("SWING_" + kv.Key + "_LOW", V4LevelType.SWING_LOW, l.Price, l.KnownAtEt, l.FormedAtEt);
            }

            V4VectorEngine ve15;
            if (vectors.TryGetValue("15m", out ve15))
            {
                V4Vector up = ve15.NearestUnrecoveredAbove(b.Close, now);
                V4Vector dn = ve15.NearestUnrecoveredBelow(b.Close, now);
                if (up != null) Pub("VEC15_ABOVE", V4LevelType.VECTOR_ZONE, up.FarEdge, up.CreatedEt, up.CreatedEt);
                if (dn != null) Pub("VEC15_BELOW", V4LevelType.VECTOR_ZONE, dn.FarEdge, dn.CreatedEt, dn.CreatedEt);
            }
        }

        private void Pub(string name, V4LevelType type, double price, DateTime knownEt)
        {
            Pub(name, type, price, knownEt, knownEt);
        }
        private void Pub(string name, V4LevelType type, double price, DateTime knownEt, DateTime formedEt)
        {
            if (!V4Num.Ok(price)) return;
            levels.Publish(name, type, price, formedEt, knownEt);
        }

        // ---- the 15m parent event -------------------------------------

        private void On15mBar(V4Bar b, double atr, V4StructureTracker t, V4Vector v,
                              V4Swing kh, V4Swing kl)
        {
            fifteenBarCount++;
            DateTime cutoff = V4ResearchEngine.SnapshotCutoff(b);

            int side = 0;
            string kind = "";
            double triggerLevel = double.NaN;
            string parentVectorId = "";

            // A parent event is a break of a CONFIRMED swing. Direction comes
            // from which extreme was taken - never from vector colour.
            //
            // The test is on the TRANSITION, not the state. Asking only
            // "is the high above the last confirmed swing high" is true on
            // EVERY bar until a new swing confirms above, so a single trend
            // leg emits an event per bar. Measured on the first sample: 84%
            // of levels were "broken" more than once, mean 4.5 rows each and
            // up to 16, 78% of events landed exactly 15 minutes after the
            // previous one, and 1705 rows came from 306 real theses.
            //
            // So a level fires once per excursion. It can fire again only
            // after price has closed back inside it, or when the confirmed
            // level itself has moved.
            int gated = breakGate.Update(b.High, b.Low, b.Close,
                                        kh.Valid, kh.Valid ? kh.Price : double.NaN,
                                        kl.Valid, kl.Valid ? kl.Price : double.NaN);
            if (gated > 0) { side = 1; kind = "BREAK_HIGH"; triggerLevel = kh.Price; }
            else if (gated < 0) { side = -1; kind = "BREAK_LOW"; triggerLevel = kl.Price; }

            bool isControl = false;
            if (side == 0)
            {
                if (ControlSampleRate <= 0 || (fifteenBarCount % ControlSampleRate) != 0) return;
                // matched placebo: same clock, same volatility, no qualifying event
                isControl = true;
                side = b.Close >= b.Open ? 1 : -1;
                kind = "CONTROL";
                triggerLevel = b.Close;
            }

            if (v != null) parentVectorId = v.VectorId;

            int raw;
            string parentId = clusterer.ParentFor(SymbolName(), "15m", side, b.EtClose, out raw);

            V4EventKeys keys = new V4EventKeys();
            keys.ParentEventId = parentId;
            keys.EventId = V4EventKeys.MakeEventId(parentId, kind, raw);
            keys.RawSignalCount = raw;
            keys.HypothesisId = isControl ? "CONTROL" : PickHypothesisId(v, kind);

            V4AblationFlags flags = new V4AblationFlags();
            flags.HasStructure = true;
            flags.HasVector = v != null;
            flags.HasLevel = levels.Nearest(b.Close, cutoff) != null;
            flags.HasEmaFan = fans["15m"].Ema50Ready;
            flags.HasOrderFlow = false;
            flags.HasProfile = false;
            flags.IsControl = isControl;

            WriteStructureRow(keys, b, atr, t, v, kh, kl, cutoff, flags, isControl, side, kind);

            if (!WriteEntries || isControl) return;

            // Every architecture is emitted against the SAME parent event.
            OpenProbe(keys, "ARCH-A", "1m", "IMMEDIATE", side, b, atr, triggerLevel, parentVectorId, kind, flags, false);
            OpenProbe(keys, "ARCH-B", "3m", "IMMEDIATE", side, b, atr, triggerLevel, parentVectorId, kind, flags, false);
            OpenProbe(keys, "ARCH-C", "1m", "CONFIRM_3M", side, b, atr, triggerLevel, parentVectorId, kind, flags, true);
        }

        private string PickHypothesisId(V4Vector v, string kind)
        {
            if (v == null) return "H0-STRUCTURE-ONLY";
            if (v.BrokeStructure && !v.ClosedBeyondStructure) return "H1-VECTOR-SWEEP-REVERSAL";
            if (v.ClosedBeyondStructure) return "H2-VECTOR-BREAK-CONTINUATION";
            return "H4-VECTOR-AT-LEVEL";
        }

        private void OpenProbe(V4EventKeys keys, string arch, string entryTf, string trigger,
                               int side, V4Bar b, double atr, double triggerLevel,
                               string parentVectorId, string kind, V4AblationFlags flags, bool needsConfirm)
        {
            PendingProbe p = new PendingProbe();
            p.Keys = new V4EventKeys();
            p.Keys.ParentEventId = keys.ParentEventId;
            p.Keys.EventId = keys.EventId;
            p.Keys.HypothesisId = keys.HypothesisId;
            p.Keys.RawSignalCount = keys.RawSignalCount;
            p.Keys.EntryProbeId = V4EventKeys.MakeProbeId(keys.EventId, arch, trigger, entryTf);
            p.Architecture = arch; p.EntryTf = entryTf; p.Trigger = trigger;
            p.Side = side; p.EventEt = b.EtClose; p.EventClose = b.Close;
            p.TriggerLevel = triggerLevel; p.AtrAtEvent = atr;
            p.ParentVectorId = parentVectorId; p.EventKind = kind;
            p.NeedsConfirm = needsConfirm; p.Confirmed = !needsConfirm;
            p.Gate.Mode = LtfExecution; p.Gate.PullbackAtr = PullbackAtr;
            p.Flags = flags;
            pending.Add(p);
        }


        /// A probe triggers on the first 1m close in the event's direction.
        /// Stops and targets are frozen HERE, at the entry instant, from
        /// levels that already exist. A target chosen from a level created
        /// later is the easiest way to fabricate an edge.
        private bool TryTrigger(PendingProbe p, V4Bar b, double atr1m)
        {
            bool go = p.Side > 0 ? b.Close > p.EventClose : b.Close < p.EventClose;
            if (!go) return false;

            p.Triggered = true;
            p.EntryEt = b.EtClose;
            p.EntryPrice = b.Close;
            p.MinsToEntry = (int)(b.EtClose - p.EventEt).TotalMinutes;

            DateTime cutoff = V4ResearchEngine.SnapshotCutoff(b);
            double atr = V4Num.Ok(p.AtrAtEvent) ? p.AtrAtEvent : atr1m;

            V4StructureTracker t15 = trackers["15m"];
            V4Swing sh = t15.SwingHighKnownAt(cutoff);
            V4Swing sl = t15.SwingLowKnownAt(cutoff);

            double tight = p.Side > 0 ? b.Low - 0.25 : b.High + 0.25;
            double medium = p.Side > 0 ? b.Low - 0.5 * atr : b.High + 0.5 * atr;
            double structural = p.Side > 0
                ? (sl.Valid ? sl.Price - 0.25 : medium)
                : (sh.Valid ? sh.Price + 0.25 : medium);

            p.Labels.Stops.Freeze(p.Side, p.EntryPrice, atr, tight, medium, structural);
            p.Labels.RaceStop = V4StopKind.MEDIUM;

            AssignTargets(p.Labels, p.Side, p.EntryPrice, atr, cutoff, sh, sl);

            p.Labels.Open(p.Side, p.EntryPrice, p.EntryEt, atr, lastEma9_1m);
            return true;
        }

        /// The five reference targets, shared by the entry probes and by the
        /// parent structure event.
        ///
        /// The parent event used to be opened with stops and no targets at
        /// all, so on a 659-row structure sample every one of the ten target
        /// columns was constant - hitTarget* FALSE on every row, minsTo* -1
        /// on every row - and the three targetAfterStop* controls were dead
        /// with them, because those read ReferenceTarget(). Thirteen label
        /// columns that could not vary. The probes had the code; the parent
        /// simply never called it.
        private void AssignTargets(V4ForwardLabels L, int side, double refPrice,
                                   double atr, DateTime cutoff, V4Swing sh, V4Swing sl)
        {
            V4VectorEngine ve15 = vectors["15m"];
            V4Vector vz = side > 0
                ? ve15.NearestUnrecoveredAbove(refPrice, cutoff)
                : ve15.NearestUnrecoveredBelow(refPrice, cutoff);
            L.TargetVectorZone = vz == null
                ? V4Target.None()
                : V4Target.Make("VECTOR_ZONE", vz.VectorId, vz.FarEdge, refPrice, side, atr);

            V4LevelRef liq = side > 0
                ? levels.NearestAbove(refPrice, cutoff)
                : levels.NearestBelow(refPrice, cutoff);
            L.TargetLiquidity = liq == null
                ? V4Target.None()
                : V4Target.Make("LIQUIDITY", liq.Name, liq.Price, refPrice, side, atr);

            double swing = side > 0 ? (sh.Valid ? sh.Price : double.NaN)
                                    : (sl.Valid ? sl.Price : double.NaN);
            L.TargetSwing = V4Target.Make("SWING", "15m", swing, refPrice, side, atr);

            V4StructureTracker t60;
            double htf = double.NaN;
            if (trackers.TryGetValue("60m", out t60))
            {
                V4Swing h = side > 0 ? t60.SwingHighKnownAt(cutoff) : t60.SwingLowKnownAt(cutoff);
                if (h.Valid) htf = h.Price;
            }
            L.TargetHtfStruct = V4Target.Make("HTF_STRUCT", "60m", htf, refPrice, side, atr);

            double sess = side > 0 ? location.SessionHigh : location.SessionLow;
            L.TargetSession = V4Target.Make("SESSION", "session extreme", sess, refPrice, side, atr);
        }

        // ==============================================================
        // OUTPUT
        // ==============================================================

        private void WriteStructureRow(V4EventKeys keys, V4Bar b, double atr, V4StructureTracker t,
                                       V4Vector v, V4Swing kh, V4Swing kl, DateTime cutoff,
                                       V4AblationFlags flags, bool isControl, int side, string kind)
        {
            bool warm = sampleStartEt != DateTime.MinValue && b.EtClose < sampleStartEt;
            V4Row r = new V4Row(b.EtClose);

            V4RowBuilder.Keys(r, keys, SymbolName(), "15m",
                isControl ? V4ResearchClass.CONTROL : V4ResearchClass.EXPLORATORY,
                V4HypothesisClass.A_MARKET_EDGE, V4DataLayer.STRUCTURE_VECTOR);

            r.F("isWarmup", warm).F("eventKind", kind).F("side", side);
            V4RowBuilder.Bar(r, b, atr, t.RelVolume());
            V4RowBuilder.Session(r, b.EtClose);
            r.F("featuresAsOfEt", cutoff);

            // structure across every tracked timeframe
            foreach (KeyValuePair<int, string> kv in bipLabel)
            {
                string lab = kv.Value;
                V4StructureTracker tt = trackers[lab];
                r.F("struct_" + lab, tt.StateKnownAt(cutoff).ToString())
                 .F("minsInState_" + lab, tt.MinutesInStateAt(cutoff));
            }
            r.F("swingHighPrice", kh.Valid ? kh.Price : double.NaN)
             .F("swingHighKnownEt", kh.Valid ? kh.KnownAtEt : DateTime.MinValue)
             .F("swingHighLabel", kh.Valid ? kh.Label.ToString() : "")
             .F("swingLowPrice", kl.Valid ? kl.Price : double.NaN)
             .F("swingLowKnownEt", kl.Valid ? kl.KnownAtEt : DateTime.MinValue)
             .F("swingLowLabel", kl.Valid ? kl.Label.ToString() : "")
             .F("compressionRatio", t.CompressionRatio())
             .F("expansionRatio", t.ExpansionRatio())
             .F("tfRangePts", t.RangePtsKnownAt(cutoff))
             .F("tfPosInRange", t.PosInRangeKnownAt(cutoff, b.Close));

            V4RowBuilder.Vector(r, "15m", v, vectors["15m"], cutoff);
            // The 3m vector is reported ONLY when it formed inside this 15m
            // bar. LatestKnownAt returns the most recent 3m vector whenever it
            // happened, which is never null once the run is warm - so
            // f_isVector_3m came back TRUE on every one of the 659 rows in the
            // first clean sample. A column that is always true is not a
            // feature, it is a constant with a misleading name.
            V4VectorEngine ve3 = vectors.ContainsKey("3m") ? vectors["3m"] : null;
            V4Vector v3 = ve3 == null ? null : ve3.LatestKnownAt(cutoff);
            if (v3 != null && v3.CreatedEt <= b.EtOpen) v3 = null;
            V4RowBuilder.Vector(r, "3m", v3, ve3, cutoff);
            // VectorRecoveryLabels is NOT called here. It used to be, and the
            // result was six dead columns: on the bar a vector forms it has
            // by definition recovered 0%, been touched never and reached no
            // threshold - so vectorRecovery_15m read UNRECOVERED on all 285
            // vector rows, recoveryPct 0 on all 285, firstTouchEt blank on
            // all 659, barsTo25/50/100 all -1 and both trap flags all FALSE.
            // The labels are appended in WriteCompletedEvent instead, where
            // the forward window has actually elapsed. H5-UNRECOVERED-VECTOR-
            // DESTINATION is measured entirely from these columns and could
            // not have been tested against the previous output.

            // W / M formation
            V4FormationState fm = vectors["15m"].Formation;
            r.F("formationType", fm.Type.ToString())
             .F("formationStartEt", fm.StartEt)
             .F("formationFirstLegExtreme", fm.FirstLegExtreme)
             .F("formationMiddlePivot", fm.MiddlePivot)
             .F("formationSecondLegExtreme", fm.SecondLegExtreme)
             .F("formationNeckline", fm.Neckline)
             .F("formationSecondLegConfirmed", fm.SecondLegConfirmed)
             .F("formationBreakConfirmed", fm.BreakConfirmed)
             .F("formationRetestConfirmed", fm.RetestConfirmed)
             .F("formationInvalidated", fm.Invalidated)
             .F("barsSinceFormationStart", fm.BarsSinceStart)
             .F("barsSinceSecondLeg", fm.BarsSinceSecondLeg)
             .F("vectorExitsFormation", vectors["15m"].VectorExitsFormation(v));

            // repeated-push state
            int pushCount; V4VectorDir pushDir; double pushNet, pushRange; bool poor;
            vectors["15m"].PushState(cutoff, atr, out pushCount, out pushDir, out pushNet, out pushRange, out poor);
            r.F("vectorPushCount", pushCount)
             .F("vectorPushDirection", pushDir.ToString())
             .F("vectorPushNetProgressAtr", pushNet)
             .F("vectorPushTotalRangeAtr", pushRange)
             .F("vectorPushPoorProgress", poor);

            // EMA fans
            V4RowBuilder.Fan(r, "15m", fans["15m"], b.Close, atr);
            if (fans.ContainsKey("3m")) V4RowBuilder.Fan(r, "3m", fans["3m"], b.Close, atr);
            if (fans.ContainsKey("5m")) V4RowBuilder.Fan(r, "5m", fans["5m"], b.Close, atr);
            r.F("ema9_1m", lastEma9_1m)
             .F("closeVsEma9_1m", V4Num.Ok(lastEma9_1m) ? (b.Close > lastEma9_1m ? 1 : -1) : 0);

            // level context
            V4LevelRef nl = levels.Nearest(b.Close, cutoff);
            V4RowBuilder.Level(r, nl, b.Close, atr, levels, b.EtClose);
            r.F("locationAsOfEt", location.AsOfEt)
             .F("distPdhAtr", V4Num.DistAtr(b.Close, location.PriorDayHigh, atr))
             .F("distPdlAtr", V4Num.DistAtr(b.Close, location.PriorDayLow, atr))
             .F("distVwapAtr", V4Num.DistAtr(b.Close, location.SessionVwap, atr));

            // ADR / AWR
            r.F("adrPeriod", ranges.AdrPeriod).F("adrValuePts", ranges.AdrPts)
             .F("adrConsumedPts", ranges.AdrConsumedPts).F("adrConsumedPct", ranges.AdrConsumedPct)
             .F("awrPeriod", ranges.AwrPeriod).F("awrValuePts", ranges.AwrPts)
             .F("awrConsumedPct", ranges.AwrConsumedPct)
             .F("distAdrHighProjPts", ranges.AdrHighProjection - b.Close)
             .F("distAdrLowProjPts", b.Close - ranges.AdrLowProjection);

            r.Key("ablation", "");
            r.F("hasStructure", flags.HasStructure).F("hasVector", flags.HasVector)
             .F("hasOrderFlow", flags.HasOrderFlow).F("hasLevel", flags.HasLevel)
             .F("hasProfile", flags.HasProfile).F("hasEmaFan", flags.HasEmaFan)
             .F("isControl", flags.IsControl);

            V4RowBuilder.Source(r, V4SourceRegistry.Pvsra);
            V4RowBuilder.Validity(r, validity);

            audit.NoteRow(b.EtClose, cutoff, warm);

            // Features are frozen HERE as text. The row is not written until
            // its forward window closes and the labels are appended, so the
            // parent event carries its own outcome without any later value
            // ever touching a feature column.
            if (!structSchema.Established) structSchema.Establish(BuildStructureSchemaRow(r, b));
            structSchema.Verify(BuildStructureSchemaRow(r, b));

            V4OpenEvent oe = new V4OpenEvent();
            oe.Freeze(r, b.EtClose);
            oe.EventVector = v;
            oe.VectorTfTag = "15m";
            oe.Labels.Stops.Freeze(side, b.Close, atr,
                side > 0 ? b.Low - 0.25 : b.High + 0.25,
                side > 0 ? b.Low - 0.5 * atr : b.High + 0.5 * atr,
                side > 0 ? (kl.Valid ? kl.Price - 0.25 : b.Low - atr)
                         : (kh.Valid ? kh.Price + 0.25 : b.High + atr));
            oe.Labels.RaceStop = V4StopKind.MEDIUM;
            AssignTargets(oe.Labels, side, b.Close, atr, cutoff, kh, kl);
            oe.Labels.Open(side, b.Close, b.EtClose, atr, lastEma9_1m);
            openEvents.Add(oe);
        }

        /// The structure schema is feature columns followed by label
        /// columns, both produced by V4OpenEvent so the header and the
        /// written row can never come from two different definitions.
        private V4Row BuildStructureSchemaRow(V4Row featureRow, V4Bar b)
        {
            return V4OpenEvent.SchemaRow(featureRow, "15m", b.EtClose);
        }

        private void WriteCompletedEvent(V4OpenEvent oe)
        {
            for (int i = 0; i < oe.Labels.Races.Length; i++) audit.NoteRace(oe.Labels.Races[i].Outcome);
            // Recovery state as of window close - the same 240-minute horizon
            // every other label on this row is measured over.
            Append("structure", oe.EventEt, structSchema.Header, oe.CompletedCsv());
            structRows++;
        }

        private void WriteEntryRow(PendingProbe p)
        {
            bool warm = sampleStartEt != DateTime.MinValue && p.EventEt < sampleStartEt;
            V4Row r = new V4Row(p.EntryEt);

            V4RowBuilder.Keys(r, p.Keys, SymbolName(), "15m",
                V4ResearchClass.EXPLORATORY, V4HypothesisClass.C_EXECUTION,
                V4DataLayer.STRUCTURE_VECTOR);

            r.F("isWarmup", warm)
             .F("architecture", p.Architecture)
             .F("entryTf", p.EntryTf)
             .F("trigger", p.Trigger)
             .F("ltfExecution", p.NeedsConfirm ? LtfExecution.ToString() : "N/A")
             .F("pullbackArmed", p.PullbackArmed)
             .F("eventKind", p.EventKind)
             .F("side", p.Side)
             .F("eventEt", p.EventEt)
             .F("eventClose", p.EventClose)
             .F("triggerLevel", p.TriggerLevel)
             .F("parentVectorId", p.ParentVectorId)
             .F("entryEt", p.EntryEt)
             .F("entryPrice", p.EntryPrice)
             .F("minsToEntry", p.MinsToEntry)
             .F("slipFromEventPts", p.Side > 0 ? p.EntryPrice - p.EventClose : p.EventClose - p.EntryPrice)
             .F("atrAtEvent", p.AtrAtEvent)
             .F("ema9AtEntry", p.Labels.EmaExit.EntryWasAboveEma9 ? 1 : -1);

            V4RowBuilder.Session(r, p.EntryEt);
            V4RowBuilder.FrozenTargets(r, p.Labels);
            V4RowBuilder.Labels(r, p.Labels);

            r.F("hasStructure", p.Flags.HasStructure).F("hasVector", p.Flags.HasVector)
             .F("hasOrderFlow", p.Flags.HasOrderFlow).F("hasLevel", p.Flags.HasLevel)
             .F("hasProfile", p.Flags.HasProfile).F("hasEmaFan", p.Flags.HasEmaFan)
             .F("isControl", p.Flags.IsControl);

            V4RowBuilder.Validity(r, validity);

            audit.NoteEntryDelay(p.MinsToEntry);
            for (int i = 0; i < p.Labels.Races.Length; i++) audit.NoteRace(p.Labels.Races[i].Outcome);

            entrySchema.Verify(r);
            Append("entries", p.EventEt, entrySchema.Header, r.Csv());
            entryRows++;
        }

        // ---- month-routed writing --------------------------------------

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
                if (firstTouch && File.Exists(path))
                    Print("  V4.1 writing " + Path.GetFileName(path));
            }
            catch (Exception e) { Print("V4.1 write failed: " + e.Message); }
        }

        // ---- shutdown ---------------------------------------------------

        private void Finish()
        {
            // close every probe still running so its window is honestly
            // marked TIMEOUT rather than left looking unfinished
            for (int i = 0; i < openProbes.Count; i++)
            {
                openProbes[i].Labels.CloseWindow();
                WriteEntryRow(openProbes[i]);
            }
            openProbes.Clear();

            for (int i = 0; i < openEvents.Count; i++)
            {
                openEvents[i].Labels.CloseWindow();
                WriteCompletedEvent(openEvents[i]);
            }
            openEvents.Clear();

            PrintLines(audit.Text());
            Print("  " + structSchema.Describe());
            if (WriteEntries) Print("  " + entrySchema.Describe());
            Print("  structure rows " + structRows + "   entry rows " + entryRows);

            try
            {
                string p = Path.Combine(outDir, "v4_1_STRUCTURE_AUDIT_" + FileTag + ".txt");
                using (StreamWriter w = new StreamWriter(p, false))
                {
                    w.Write(diag.Text());
                    w.Write(validity.Summary());
                    w.Write(audit.Text());
                    w.WriteLine(structSchema.Describe());
                    if (WriteEntries) w.WriteLine(entrySchema.Describe());
                    w.WriteLine();
                    w.WriteLine("PRE-REGISTERED HYPOTHESIS REGISTRY");
                    w.WriteLine(V4Hypothesis.CsvHeader());
                    if (registry != null)
                        for (int i = 0; i < registry.Items.Count; i++) w.WriteLine(registry.Items[i].Csv());
                    w.WriteLine();
                    w.WriteLine("CLASS A market-edge hypotheses: "
                        + (registry == null ? 0 : registry.ClassACount())
                        + "  (the pre-registration limit of 5-10 applies to this count only)");
                }
                Print("  V4.1 audit written: " + Path.GetFileName(p));
            }
            catch (Exception e) { Print("V4.1 audit write failed: " + e.Message); }
        }
    }
}
