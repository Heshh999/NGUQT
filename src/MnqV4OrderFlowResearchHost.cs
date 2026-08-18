// ============================================================================
// MnqV4OrderFlowResearchHost.cs
//
// NinjaTrader 8 host for the V4 EXECUTED-ORDER-FLOW capture.
//
// THIS STRATEGY SUBMITS NO ORDERS.
//
// HOW TO RUN IT
//   Apply it to a chart whose PRIMARY series is a 1-minute VOLUMETRIC series
//   (Bars type "Volumetric", period 1 Minute, Ticks Per Level 1). The primary
//   series is read directly, so no AddVolumetric call is needed and the
//   capture cannot silently disagree with what is on the chart.
//
//   If the primary series is NOT volumetric, the capture still runs and still
//   writes the audit - it simply records every bar as NO_LEVELS and the audit
//   FAILS. That is the correct outcome: "the data was not there" is a result,
//   not an error to be worked around.
//
// WHY REFLECTION
//   VolumetricBarsType lives in an assembly that only exists inside
//   NinjaTrader. Binding to it directly would make the whole V4 codebase
//   uncompilable outside the platform, including the deterministic test suite
//   that checks the audit arithmetic. The volumetric read is therefore done
//   through reflection and cached after the first success. Nothing else in V4
//   uses reflection.
//
// SEPARATE FILE, SEPARATE RUN, SEPARATE VERDICT
//   This host shares no state with the structure capture. The two datasets are
//   joined in analysis on (symbol, timestamp), never in code. That is what
//   makes the incremental-value test - base price structure versus base plus
//   order flow - an actual comparison rather than an assumption baked into the
//   capture.
// ============================================================================

using System;
using System.Collections;
using System.Collections.Generic;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Reflection;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace NinjaTrader.NinjaScript.Strategies
{
    /// Pulls per-price executed volume out of a NinjaTrader volumetric series
    /// without compile-time knowledge of its types. Every failure mode returns
    /// FALSE and is recorded as missing data rather than substituted for.
    public class V4VolumetricReader
    {
        private bool resolved, failed;
        private object barsTypeObj;
        private Array volumesArray;
        public string LastError = "";

        /// Fill the per-price levels of bar barIndex from series bars. Returns
        /// FALSE when the series is not volumetric or the bar has no levels.
        public bool TryRead(object bars, int barIndex, V4FootprintBar into)
        {
            if (failed) return false;
            try
            {
                if (!resolved)
                {
                    if (bars == null) { failed = true; LastError = "series is null"; return false; }
                    object bt = GetMember(bars, "BarsType");
                    if (bt == null) { failed = true; LastError = "series has no BarsType"; return false; }
                    barsTypeObj = bt;
                    resolved = true;
                }
                object vols = GetMember(barsTypeObj, "Volumes");
                volumesArray = vols as Array;
                if (volumesArray == null)
                {
                    failed = true;
                    LastError = "BarsType has no Volumes array - the series is not Volumetric";
                    return false;
                }
                if (barIndex < 0 || barIndex >= volumesArray.Length) return false;
                object vb = volumesArray.GetValue(barIndex);
                if (vb == null) return false;

                IDictionary levels = GetMember(vb, "Volumes") as IDictionary;
                if (levels == null || levels.Count == 0) return false;

                foreach (DictionaryEntry kv in levels)
                {
                    V4FootprintLevel l = new V4FootprintLevel();
                    l.Price = Convert.ToDouble(kv.Key, CultureInfo.InvariantCulture);
                    object v = kv.Value;
                    l.AskVolume = Num(v, "AskVolume");
                    l.BidVolume = Num(v, "BidVolume");
                    into.Levels.Add(l);
                }
                into.HasLevels = into.Levels.Count > 0;
                return into.HasLevels;
            }
            catch (Exception ex)
            {
                failed = true;
                LastError = ex.GetType().Name + ": " + ex.Message;
                return false;
            }
        }

        private static object GetMember(object o, string name)
        {
            if (o == null) return null;
            Type t = o.GetType();
            PropertyInfo p = t.GetProperty(name);
            if (p != null && p.CanRead) return p.GetValue(o, null);
            FieldInfo f = t.GetField(name);
            return f != null ? f.GetValue(o) : null;
        }

        private static double Num(object o, string name)
        {
            object v = GetMember(o, name);
            if (v == null) return 0;
            try { return Convert.ToDouble(v, CultureInfo.InvariantCulture); }
            catch (Exception) { return 0; }
        }
    }

    public class MnqV4OrderFlowResearch : Strategy
    {
        private V4OrderFlowEngine engine;
        private V4VolumetricReader reader;
        private TimeZoneInfo etZone;
        private StreamWriter csv;
        private string stem, curMonth = "";
        private long barsSeen, barsWithLevels;

        #region 00. Capture
        [NinjaScriptProperty]
        [Display(Name = "File tag", GroupName = "00. Capture", Order = 1)]
        public string FileTag { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Write one file per month", GroupName = "00. Capture", Order = 2)]
        public bool MonthlyFiles { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Verbose diagnostics", GroupName = "00. Capture", Order = 3)]
        public bool VerboseDiagnostics { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Bar times are already Eastern", GroupName = "00. Capture", Order = 4)]
        public bool AssumeBarTimesAreEastern { get; set; }
        #endregion

        #region 01. Flow measurement
        [NinjaScriptProperty]
        [Range(1.0, 20.0)]
        [Display(Name = "Imbalance factor", GroupName = "01. Flow measurement", Order = 1,
                 Description = "Ask volume must be this multiple of the bid volume one tick below to count as a buy imbalance.")]
        public double ImbalanceFactor { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name = "Imbalance minimum volume", GroupName = "01. Flow measurement", Order = 2,
                 Description = "Ignore imbalance comparisons below this combined volume. A 3-versus-1 contract ratio is noise.")]
        public int ImbalanceMinVolume { get; set; }

        [NinjaScriptProperty]
        [Range(2, 500)]
        [Display(Name = "Divergence lookback (bars)", GroupName = "01. Flow measurement", Order = 3)]
        public int DivergenceLookback { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Emit from (ET minutes)", GroupName = "01. Flow measurement", Order = 4)]
        public int EmitStartMinutesEt { get; set; }

        [NinjaScriptProperty]
        [Range(0, 1440)]
        [Display(Name = "Emit to (ET minutes)", GroupName = "01. Flow measurement", Order = 5)]
        public int EmitEndMinutesEt { get; set; }
        #endregion

        #region 02. Data-quality gate
        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Require level coverage (%)", GroupName = "02. Data-quality gate", Order = 1)]
        public double MinLevelCoveragePct { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Allow volume mismatch (% of bars)", GroupName = "02. Data-quality gate", Order = 2)]
        public double MaxVolumeMismatchPct { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name = "Per-bar volume tolerance (%)", GroupName = "02. Data-quality gate", Order = 3,
                 Description = "How far ask+bid may differ from bar volume before that bar counts as misclassified.")]
        public double VolumeTolerancePct { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000000)]
        [Display(Name = "Require at least N bars", GroupName = "02. Data-quality gate", Order = 4)]
        public int MinBars { get; set; }
        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqV4OrderFlowResearch";
                Description = "V4 executed-order-flow capture with a data-quality gate. Submits no orders.";
                Calculate = Calculate.OnBarClose;
                IsOverlay = false;
                EntriesPerDirection = 1;
                IsExitOnSessionCloseStrategy = false;
                BarsRequiredToTrade = 1;
                IsInstantiatedOnEachOptimizationIteration = false;

                FileTag = "v4of";
                MonthlyFiles = true;
                VerboseDiagnostics = true;
                AssumeBarTimesAreEastern = false;

                ImbalanceFactor = 3.0;
                ImbalanceMinVolume = 10;
                DivergenceLookback = 20;
                EmitStartMinutesEt = 0;
                EmitEndMinutesEt = 1440;

                MinLevelCoveragePct = 98.0;
                MaxVolumeMismatchPct = 2.0;
                VolumeTolerancePct = 1.0;
                MinBars = 20000;
            }
            else if (State == State.DataLoaded)
            {
                try { etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception)
                {
                    try { etZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
                    catch (Exception) { etZone = null; }
                }

                string sym = Instrument != null && Instrument.MasterInstrument != null
                    ? Instrument.MasterInstrument.Name : "UNKNOWN";
                stem = Path.Combine(NinjaTrader.Core.Globals.UserDataDir,
                    "v4_orderflow_" + sym + "_" + Safe(FileTag));

                reader = new V4VolumetricReader();
                engine = new V4OrderFlowEngine(WriteRow);
                engine.Symbol = sym;
                engine.ImbalanceFactor = ImbalanceFactor;
                engine.ImbalanceMinVolume = ImbalanceMinVolume;
                engine.DivergenceLookback = DivergenceLookback;
                engine.EmitStartMinutesEt = EmitStartMinutesEt;
                engine.EmitEndMinutesEt = EmitEndMinutesEt;
                engine.TickSize = Instrument != null && Instrument.MasterInstrument != null
                                  && Instrument.MasterInstrument.TickSize > 0
                    ? Instrument.MasterInstrument.TickSize : TickSize;
                engine.Audit.MinLevelCoveragePct = MinLevelCoveragePct;
                engine.Audit.MaxVolumeMismatchPct = MaxVolumeMismatchPct;
                engine.Audit.VolumeTolerancePct = VolumeTolerancePct;
                engine.Audit.MinBars = MinBars;

                if (!MonthlyFiles)
                {
                    csv = new StreamWriter(stem + ".csv", false);
                    csv.WriteLine(V4OrderFlowEngine.CsvHeader());
                }

                PrintLine("======================================================================");
                PrintLine("V4 EXECUTED-ORDER-FLOW RESEARCH CAPTURE");
                PrintLine("THIS STRATEGY SUBMITS NO ORDERS.");
                PrintLine("======================================================================");
                PrintLine("  instrument   " + sym + "   tick size "
                          + engine.TickSize.ToString("0.####", CultureInfo.InvariantCulture));
                PrintLine("  REQUIRES a PRIMARY series of Bars type VOLUMETRIC, 1 Minute,");
                PrintLine("  Ticks Per Level 1. Anything else is captured as missing data and");
                PrintLine("  the audit will fail - which is the honest answer, not a bug.");
                PrintLine("======================================================================");
            }
            else if (State == State.Terminated)
            {
                WriteAudit();
                if (csv != null) { csv.Flush(); csv.Close(); csv = null; }
            }
        }

        protected override void OnBarUpdate()
        {
            if (engine == null) return;
            if (BarsInProgress != 0) return;
            if (CurrentBar < 1) return;

            V4FootprintBar b = new V4FootprintBar();
            b.EtClose = ToEt(Time[0]);
            b.EtOpen = b.EtClose.AddMinutes(-1);
            b.Open = Open[0]; b.High = High[0]; b.Low = Low[0];
            b.Close = Close[0]; b.Volume = Volume[0];

            barsSeen++;
            if (reader.TryRead(BarsArray[0], CurrentBar, b)) barsWithLevels++;

            engine.OnBar(b);
        }


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

        private void WriteRow(string row)
        {
            if (!MonthlyFiles) { if (csv != null) csv.WriteLine(row); return; }
            string month = V4ResearchEngine.MonthKeyFromRow(row);
            if (month != curMonth)
            {
                if (csv != null) { csv.Flush(); csv.Close(); }
                string path = stem + "_" + month + ".csv";
                csv = OpenMonthly(path, V4OrderFlowEngine.CsvHeader());
                curMonth = month;
                PrintLine("  V4 ORDER FLOW: writing " + Path.GetFileName(path));
            }
            csv.WriteLine(row);
        }

        /// The audit is written to disk AND printed, because the verdict is the
        /// part of this capture that decides whether any of the rest of it may
        /// be used at all.
        private void WriteAudit()
        {
            if (engine == null) return;
            string report = engine.Audit.Report();
            if (reader != null && reader.LastError.Length > 0)
                report += "Volumetric read error: " + reader.LastError + Environment.NewLine;
            report += "Rows written: " + engine.RowsEmitted.ToString(CultureInfo.InvariantCulture)
                      + Environment.NewLine;
            try
            {
                File.WriteAllText(stem + "_AUDIT.txt", report);
            }
            catch (Exception ex) { PrintLine("V4: could not write audit file: " + ex.Message); }
            Print(report);
            if (barsSeen > 0 && barsWithLevels == 0)
            {
                Print("V4 ORDER FLOW: not one bar carried per-price volume. The primary series");
                Print("is almost certainly not a Volumetric series. Nothing in this capture may");
                Print("be used to support an order-flow claim.");
            }
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
