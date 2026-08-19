// ============================================================================
// MnqV4StructureResearchHost.cs
//
// NinjaTrader 8 host for the V4 multi-timeframe market-structure capture.
//
// THIS STRATEGY SUBMITS NO ORDERS.
//   It contains no EnterLong, EnterShort, ExitLong, ExitShort, SetStopLoss,
//   SetProfitTarget or any other order method. It cannot open a position under
//   any parameter combination, on any account, in any state. It is a data
//   capture and nothing else.
//
// WHY IT IS A SEPARATE STRATEGY
//   The V3 host already carries eight parameter groups and two live engines.
//   Bolting a third research programme into it would make every V4 run depend
//   on V3 toggles that have nothing to do with it - which is precisely the
//   failure that produced a Phase-2 capture with no sub-minute data in it.
//   V4 gets its own strategy, its own parameters and its own files.
//
// SERIES ORDER
//   Structure series are added COARSEST FIRST so that when several close on
//   the same timestamp NinjaTrader processes the higher timeframe first. The
//   dataset does not DEPEND on that - every cross-timeframe read is gated one
//   second before the consuming bar's close, which is order-independent - but
//   processing coarse-to-fine keeps the live path and the capture path in the
//   same sequence, which is one less thing to reason about.
//
// WHAT TO RUN IT ON
//   Any 1-minute MNQ chart. The primary series is not used for logic; every
//   timeframe the engine reads is added explicitly below, so the chart's own
//   period cannot silently change the results.
// ============================================================================

using System;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqV4StructureResearch : Strategy
    {
        // ---- series map, assigned in State.Configure ----------------------
        private int BipDaily = -1, Bip4h = -1, Bip60m = -1, Bip15m = -1;
        private int Bip5m = -1, Bip3m = -1, Bip1m = -1;

        private V4ResearchEngine engine;
        private TimeZoneInfo etZone;
        private StreamWriter structCsv, entryCsv;
        private string structStem, entryStem, structMonth = "", entryMonth = "";
        private DateTime targetSampleStart = DateTime.MinValue;
        private bool configured;

        private readonly Dictionary<int, string> bipLabel = new Dictionary<int, string>();

        #region 00. Capture
        [NinjaScriptProperty]
        [Display(Name = "File tag", GroupName = "00. Capture", Order = 1,
                 Description = "Appended to the output filenames. Use it to keep perturbation runs apart.")]
        public string FileTag { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Write one file per month", GroupName = "00. Capture", Order = 2,
                 Description = "Rows are routed by their OWN date, not by when they were written.")]
        public bool MonthlyFiles { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Write entry-resolution file", GroupName = "00. Capture", Order = 3,
                 Description = "One row per (event, entry timeframe, trigger). Off makes the capture much smaller.")]
        public bool EmitEntryFile { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Target sample start (yyyy-MM-dd)", GroupName = "00. Capture", Order = 4,
                 Description = "Rows before this date are flagged isWarmup=TRUE. Blank means every row counts.")]
        public string TargetSampleStartDate { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Verbose diagnostics", GroupName = "00. Capture", Order = 5)]
        public bool VerboseDiagnostics { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Bar times are already Eastern", GroupName = "00. Capture", Order = 6,
                 Description = "Tick if the NinjaTrader instance is set to ET, so no conversion is applied.")]
        public bool AssumeBarTimesAreEastern { get; set; }
        #endregion

        #region 01. Timeframes
        [NinjaScriptProperty]
        [Display(Name = "Daily structure", GroupName = "01. Timeframes", Order = 1)]
        public bool UseDaily { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "4-hour structure", GroupName = "01. Timeframes", Order = 2)]
        public bool Use4h { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "60-minute structure", GroupName = "01. Timeframes", Order = 3)]
        public bool Use60m { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "15-minute structure", GroupName = "01. Timeframes", Order = 4)]
        public bool Use15m { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "5-minute structure", GroupName = "01. Timeframes", Order = 5)]
        public bool Use5m { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "3-minute structure", GroupName = "01. Timeframes", Order = 6)]
        public bool Use3m { get; set; }

        // The 1-minute series is always loaded - it is the label clock, and every
        // forward measurement in the dataset is advanced by it. This switch is
        // about whether 1m may also be a SOURCE OF EVENTS.
        //
        // It defaults to OFF because of a line in the brief: "Do not search for a
        // 1-minute pattern simply because 1-minute data exists." 1m breaks are by
        // far the most numerous events available and would dominate the capture on
        // count alone. Turn it on deliberately, to test a stated 1m hypothesis -
        // for instance the "15m structure -> 1m entry" architecture, which needs
        // 1m events to exist.
        [NinjaScriptProperty]
        [Display(Name = "Capture 1-minute break events", GroupName = "01. Timeframes", Order = 7,
                 Description = "1m is always loaded as the label clock. This decides whether it also produces events.")]
        public bool Capture1mEvents { get; set; }
        #endregion

        #region 02. Swing definition
        // The brief requires any structural edge to survive "nearby swing-definition
        // parameters". These are that knob. Nothing here is a constant in the code.
        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Pivot confirm bars (right)", GroupName = "02. Swing definition", Order = 1,
                 Description = "Bars that must close to the RIGHT before a pivot is published. This is the confirmation lag.")]
        public int PivotConfirmBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Pivot left bars", GroupName = "02. Swing definition", Order = 2)]
        public int PivotLeftBars { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 1.0)]
        [Display(Name = "Equality band (ATR)", GroupName = "02. Swing definition", Order = 3,
                 Description = "Two swings within this many ATR are EQUAL rather than a higher high or lower low.")]
        public double EqualityBandAtr { get; set; }

        [NinjaScriptProperty]
        [Range(5, 200)]
        [Display(Name = "ATR period", GroupName = "02. Swing definition", Order = 4)]
        public int AtrPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(3, 100)]
        [Display(Name = "Compression lookback", GroupName = "02. Swing definition", Order = 5)]
        public int CompressionLookback { get; set; }
        #endregion

        #region 03. Break classification
        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Approach band (ATR)", GroupName = "03. Break classification", Order = 1)]
        public double ApproachBandAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 2.0)]
        [Display(Name = "Wick threshold (ATR)", GroupName = "03. Break classification", Order = 2,
                 Description = "Penetration up to this many ATR, closing back, is a WICK rather than a trade beyond.")]
        public double WickMaxAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Displacement body (ATR)", GroupName = "03. Break classification", Order = 3)]
        public double DisplacementBodyAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Displacement close beyond (ATR)", GroupName = "03. Break classification", Order = 4)]
        public double DisplacementCloseAtr { get; set; }
        #endregion

        #region 04. Outcome definitions
        [NinjaScriptProperty]
        [Range(0.0, 2.0)]
        [Display(Name = "Retest band (ATR)", GroupName = "04. Outcome definitions", Order = 1)]
        public double RetestBandAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 2.0)]
        [Display(Name = "Failure buffer (ATR)", GroupName = "04. Outcome definitions", Order = 2)]
        public double FailBufferAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Reversal distance (ATR)", GroupName = "04. Outcome definitions", Order = 3)]
        public double ReversalAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 2.0)]
        [Display(Name = "Stop buffer (ATR)", GroupName = "04. Outcome definitions", Order = 4)]
        public double StopBufferAtr { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "ATR stop multiple", GroupName = "04. Outcome definitions", Order = 5)]
        public double AtrStopMultiple { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Transition bars", GroupName = "04. Outcome definitions", Order = 6,
                 Description = "A structure state younger than this many of its own bars counts as TRANSITIONING.")]
        public int TransitionBars { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "At-location band (ATR)", GroupName = "04. Outcome definitions", Order = 7)]
        public double AtLocationAtr { get; set; }

        [NinjaScriptProperty]
        [Range(1, 240)]
        [Display(Name = "Max entry delay (minutes)", GroupName = "04. Outcome definitions", Order = 8,
                 Description = "How long after the break a candidate entry may still fill. Past this the probe expires.")]
        public int MaxEntryDelayMinutes { get; set; }
        #endregion

        #region 05. Sampling window
        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Control sample rate (1 in N)", GroupName = "05. Sampling window", Order = 1,
                 Description = "Bars that broke nothing, kept as the control group. 0 disables controls entirely.")]
        public int ControlSampleRate { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Emit from (ET minutes)", GroupName = "05. Sampling window", Order = 2,
                 Description = "570 = 09:30. The default 0 captures the whole session; narrow it only with a stated reason.")]
        public int EmitStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Emit to (ET minutes)", GroupName = "05. Sampling window", Order = 3,
                 Description = "660 = 11:00.")]
        public int EmitEndMinutesEt { get; set; }
        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqV4StructureResearch";
                Description = "V4 multi-timeframe market-structure research capture. Submits no orders.";
                Calculate = Calculate.OnBarClose;
                IsOverlay = false;
                EntriesPerDirection = 1;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 1;
                IsInstantiatedOnEachOptimizationIteration = false;

                FileTag = "v4";
                MonthlyFiles = true;
                EmitEntryFile = true;
                TargetSampleStartDate = "";
                VerboseDiagnostics = true;
                AssumeBarTimesAreEastern = false;

                UseDaily = true; Use4h = true; Use60m = true;
                Use15m = true; Use5m = true; Use3m = true;
                Capture1mEvents = false;

                PivotConfirmBars = 2;
                PivotLeftBars = 2;
                EqualityBandAtr = 0.10;
                AtrPeriod = 20;
                CompressionLookback = 10;

                ApproachBandAtr = 0.5;
                WickMaxAtr = 0.25;
                DisplacementBodyAtr = 1.0;
                DisplacementCloseAtr = 0.35;

                RetestBandAtr = 0.25;
                FailBufferAtr = 0.10;
                ReversalAtr = 1.0;
                StopBufferAtr = 0.15;
                AtrStopMultiple = 1.0;
                TransitionBars = 2;
                AtLocationAtr = 0.35;
                MaxEntryDelayMinutes = 60;

                ControlSampleRate = 400;
                EmitStartMinutesEt = 0;
                EmitEndMinutesEt = 1440;
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
                // 1m is added LAST and is mandatory: it is the label clock. Every
                // forward measurement in the dataset is advanced by this series.
                AddDataSeries(BarsPeriodType.Minute, 1); Bip1m = next++;
                configured = true;
            }
            else if (State == State.DataLoaded)
            {
                // A reused strategy instance must not remember which files the
                // PREVIOUS run opened. IsInstantiatedOnEachOptimizationIteration
                // is false, so NinjaTrader may hand the same object a second
                // run - and the truncate-on-first-touch rule then sees every
                // path as already touched and appends instead of replacing.
                // That is exactly how a re-run produced two identical copies of
                // every row. DataLoaded fires at the start of every run, so
                // clearing here is what makes "this run" mean this run.
                pathsOpenedThisRun.Clear();
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

                if (!string.IsNullOrEmpty(TargetSampleStartDate))
                {
                    DateTime d;
                    if (DateTime.TryParseExact(TargetSampleStartDate, "yyyy-MM-dd",
                        CultureInfo.InvariantCulture, DateTimeStyles.None, out d))
                        targetSampleStart = d;
                    else
                        PrintLine("V4: TargetSampleStartDate '" + TargetSampleStartDate
                                  + "' is not yyyy-MM-dd - every row will count as sample.");
                }

                string sym = Instrument != null && Instrument.MasterInstrument != null
                    ? Instrument.MasterInstrument.Name : "UNKNOWN";

                structStem = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                    "v4_structure_" + sym + "_" + Safe(FileTag));
                entryStem = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                    "v4_entries_" + sym + "_" + Safe(FileTag));

                engine = new V4ResearchEngine(WriteStructRow, EmitEntryFile ? new Action<string>(WriteEntryRow) : null);
                engine.Symbol = sym;
                engine.ApproachBandAtr = ApproachBandAtr;
                engine.WickMaxAtr = WickMaxAtr;
                engine.DisplacementBodyAtr = DisplacementBodyAtr;
                engine.DisplacementCloseAtr = DisplacementCloseAtr;
                engine.RetestBandAtr = RetestBandAtr;
                engine.FailBufferAtr = FailBufferAtr;
                engine.ReversalAtr = ReversalAtr;
                engine.StopBufferAtr = StopBufferAtr;
                engine.AtrStopMultiple = AtrStopMultiple;
                engine.TransitionBars = TransitionBars;
                engine.AtLocationAtr = AtLocationAtr;
                engine.MaxEntryDelayMinutes = MaxEntryDelayMinutes;
                engine.ControlSampleRate = ControlSampleRate;
                engine.EmitStartMinutesEt = EmitStartMinutesEt;
                engine.EmitEndMinutesEt = EmitEndMinutesEt;
                engine.TargetSampleStartEt = targetSampleStart;
                engine.EmitEntries = EmitEntryFile;

                AddTracker("1d", 1440); AddTracker("4h", 240); AddTracker("60m", 60);
                AddTracker("15m", 15); AddTracker("5m", 5); AddTracker("3m", 3);
                AddTracker("1m", 1);
                engine.SetEventEmission("1m", Capture1mEvents);

                if (!MonthlyFiles)
                {
                    structCsv = new StreamWriter(structStem + ".csv", false);
                    structCsv.WriteLine(V4ResearchEngine.StructureCsvHeader());
                    if (EmitEntryFile)
                    {
                        entryCsv = new StreamWriter(entryStem + ".csv", false);
                        entryCsv.WriteLine(V4ResearchEngine.EntryCsvHeader());
                    }
                }
                PrintHeader(sym);
            }
            else if (State == State.Terminated)
            {
                try { if (engine != null) engine.Finish(); }
                catch (Exception ex) { PrintLine("V4: Finish() failed: " + ex.Message); }
                PrintSummary();
                if (structCsv != null) { structCsv.Flush(); structCsv.Close(); structCsv = null; }
                if (entryCsv != null) { entryCsv.Flush(); entryCsv.Close(); entryCsv = null; }
            }
        }

        private void AddTracker(string label, int minutes)
        {
            // A tracker is only created for a timeframe whose series was actually
            // added. Creating one that never receives bars would put a column of
            // UNKNOWN in every row and quietly look like "no structure" rather
            // than "not loaded".
            bool loaded = false;
            foreach (KeyValuePair<int, string> kv in bipLabel) if (kv.Value == label) loaded = true;
            if (!loaded) return;

            V4StructureTracker t = new V4StructureTracker(label, minutes);
            t.ConfirmBars = PivotConfirmBars;
            t.PivotLeftBars = PivotLeftBars;
            t.EqualityBandAtr = EqualityBandAtr;
            t.AtrPeriod = AtrPeriod;
            t.CompressionLookback = CompressionLookback;
            engine.AddTracker(t);
        }

        protected override void OnBarUpdate()
        {
            if (!configured || engine == null) return;
            int bip = BarsInProgress;
            if (bip <= 0) return;                       // chart series carries no logic
            if (CurrentBars[bip] < 1) return;

            string label;
            if (!bipLabel.TryGetValue(bip, out label)) return;

            V4Bar b = ReadBar(bip, label);

            // The 1-minute series is BOTH a structure timeframe and the label
            // clock. Structure first, so a 1m break created on this bar is not
            // immediately advanced by the very bar that created it - the label
            // updater refuses bars at or before the event's close, but doing it
            // in this order makes that guarantee visible rather than incidental.
            engine.OnStructureBar(label, b);
            if (bip == Bip1m) engine.OnOneMinuteBar(b);
        }

        /// Builds a V4Bar from series bip. NinjaTrader stamps a bar with its
        /// CLOSE time, so the open time is derived from the period length. It is
        /// carried for reference only: nothing in the engine gates on it.
        private V4Bar ReadBar(int bip, string label)
        {
            V4Bar b = new V4Bar();
            b.EtClose = ToEt(Times[bip][0]);
            int mins = label == "1d" ? 1440 : label == "4h" ? 240 : label == "60m" ? 60
                     : label == "15m" ? 15 : label == "5m" ? 5 : label == "3m" ? 3 : 1;
            b.EtOpen = b.EtClose.AddMinutes(-mins);
            b.Open = Opens[bip][0]; b.High = Highs[bip][0];
            b.Low = Lows[bip][0]; b.Close = Closes[bip][0];
            b.Volume = Volumes[bip][0];
            return b;
        }

        // ---- output routing -------------------------------------------------


        /// Paths this RUN has already opened. Empty at the start of every run.
        ///
        /// Monthly rotation has to REOPEN a file it wrote earlier - rows are
        /// emitted late, once their forward horizon elapses, so a month can be
        /// revisited at a month boundary. That forced append mode, and append
        /// mode meant re-running the same date range appended a second complete
        /// copy of the data instead of replacing it.
        ///
        /// That is worse than it sounds. Duplicated rows do not look wrong: the
        /// means and medians of a tripled file are identical to the original, so
        /// nothing looks off, while every count triples and every standard error
        /// shrinks by sqrt(3). A result at t=1.7 reads as t=2.9 purely because a
        /// run was repeated. It happened on the first order-flow capture - three
        /// identical copies of all 31,498 bars.
        ///
        /// Tracking paths per run fixes it without breaking rotation: the first
        /// time a run touches a path it truncates, every reopen after that
        /// appends. Re-running replaces; rotation still accumulates.
        private readonly HashSet<string> pathsOpenedThisRun = new HashSet<string>();

        /// Opens a monthly file, truncating it if this run has not written to it
        /// before. Returns a writer positioned to append.
        private StreamWriter OpenMonthly(string path, string header)
        {
            bool firstTouchThisRun = !pathsOpenedThisRun.Contains(path);
            if (firstTouchThisRun) pathsOpenedThisRun.Add(path);
            bool append = !firstTouchThisRun;
            bool needHeader = firstTouchThisRun || !File.Exists(path);
            StreamWriter w = new StreamWriter(path, append);
            if (needHeader) w.WriteLine(header);
            if (firstTouchThisRun && File.Exists(path))
                PrintLine("  (replacing " + Path.GetFileName(path) + " from a previous run)");
            return w;
        }

        private void WriteStructRow(string row)
        {
            if (!MonthlyFiles) { if (structCsv != null) structCsv.WriteLine(row); return; }
            string month = V4ResearchEngine.MonthKeyFromRow(row);
            if (month != structMonth)
            {
                if (structCsv != null) { structCsv.Flush(); structCsv.Close(); }
                string path = structStem + "_" + month + ".csv";
                structCsv = OpenMonthly(path, V4ResearchEngine.StructureCsvHeader());
                structMonth = month;
                PrintLine("  V4 STRUCTURE: writing " + Path.GetFileName(path));
            }
            structCsv.WriteLine(row);
        }

        private void WriteEntryRow(string row)
        {
            if (!MonthlyFiles) { if (entryCsv != null) entryCsv.WriteLine(row); return; }
            string month = V4ResearchEngine.MonthKeyFromRow(row);
            if (month != entryMonth)
            {
                if (entryCsv != null) { entryCsv.Flush(); entryCsv.Close(); }
                string path = entryStem + "_" + month + ".csv";
                entryCsv = OpenMonthly(path, V4ResearchEngine.EntryCsvHeader());
                entryMonth = month;
                PrintLine("  V4 ENTRIES: writing " + Path.GetFileName(path));
            }
            entryCsv.WriteLine(row);
        }

        // ---- diagnostics ----------------------------------------------------

        private void PrintHeader(string sym)
        {
            PrintLine("======================================================================");
            PrintLine("V4 MULTI-TIMEFRAME MARKET-STRUCTURE RESEARCH CAPTURE");
            PrintLine("THIS STRATEGY SUBMITS NO ORDERS.");
            PrintLine("======================================================================");
            PrintLine("  instrument            " + sym);
            PrintLine("  structure timeframes  " + LoadedList());
            PrintLine("  1m break events       " + (Capture1mEvents ? "CAPTURED"
                      : "not captured - 1m is loaded as the label clock only"));
            PrintLine("  swing definition      confirm=" + PivotConfirmBars + " left=" + PivotLeftBars
                      + " equalityBand=" + EqualityBandAtr.ToString("0.##", CultureInfo.InvariantCulture) + " ATR");
            PrintLine("  break classification  wick<=" + WickMaxAtr.ToString("0.##", CultureInfo.InvariantCulture)
                      + " ATR, displacement body>=" + DisplacementBodyAtr.ToString("0.##", CultureInfo.InvariantCulture)
                      + " ATR and close>=" + DisplacementCloseAtr.ToString("0.##", CultureInfo.InvariantCulture) + " ATR");
            PrintLine("  forward horizons      5/15/30/60/120/240 MINUTES, measured on the 1m series");
            PrintLine("  entry window          " + MaxEntryDelayMinutes
                      + " minutes after the break; each fill then gets its own full 240m");
            PrintLine("  control sample        1 in " + ControlSampleRate + " per timeframe, both directions"
                      + (ControlSampleRate <= 0 ? "  *** DISABLED - breaks will have nothing to be compared against ***" : ""));
            PrintLine("  emit window (ET min)  " + EmitStartMinutesEt + " to " + EmitEndMinutesEt);
            PrintLine("  warm-up boundary      " + (targetSampleStart == DateTime.MinValue
                      ? "none - every row counts" : targetSampleStart.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture)));
            PrintLine("  files                 " + Path.GetFileName(structStem) + "*.csv"
                      + (EmitEntryFile ? " and " + Path.GetFileName(entryStem) + "*.csv" : " (no entry file)"));
            PrintLine("======================================================================");
        }

        private string LoadedList()
        {
            string s = "";
            string[] order = new string[] { "1d", "4h", "60m", "15m", "5m", "3m", "1m" };
            for (int i = 0; i < order.Length; i++)
            {
                bool have = false;
                foreach (KeyValuePair<int, string> kv in bipLabel) if (kv.Value == order[i]) have = true;
                if (have) s += (s.Length > 0 ? " " : "") + order[i];
            }
            return s;
        }

        private void PrintSummary()
        {
            if (engine == null) return;
            PrintLine("======================================================================");
            PrintLine("V4 CAPTURE COMPLETE");
            PrintLine("  break events      " + engine.BreaksEmitted);
            PrintLine("  control events    " + engine.ControlsEmitted);
            PrintLine("  entry rows        " + engine.EntryRowsEmitted);
            PrintLine("  still pending     " + engine.EventsPending);
            // A series that loaded nothing is the single most common cause of a
            // capture that looks fine and answers nothing, so it is named here
            // rather than inferred later from a column of empty cells.
            foreach (KeyValuePair<int, string> kv in bipLabel)
            {
                V4StructureTracker t = engine.Tracker(kv.Value);
                long n = t == null ? 0 : t.BarCount;
                PrintLine("  " + kv.Value.PadRight(4) + " bars " + n
                          + (n == 0 ? "   *** ZERO BARS - THIS TIMEFRAME CONTRIBUTED NOTHING ***" : "")
                          + (t != null ? "   swings " + t.SwingHighCount + "H/" + t.SwingLowCount + "L" : ""));
            }
            PrintLine("======================================================================");
        }

        private static string Safe(string s)
        {
            if (string.IsNullOrEmpty(s)) return "run";
            char[] bad = Path.GetInvalidFileNameChars();
            for (int i = 0; i < bad.Length; i++) s = s.Replace(bad[i], '_');
            return s;
        }

        private DateTime ToEt(DateTime barTime)
        {
            if (AssumeBarTimesAreEastern || etZone == null) return barTime;
            try { return TimeZoneInfo.ConvertTime(barTime, TimeZoneInfo.Local, etZone); }
            catch (Exception) { return barTime; }
        }

        private void PrintLine(string s) { if (VerboseDiagnostics) Print(s); }
    }
}
