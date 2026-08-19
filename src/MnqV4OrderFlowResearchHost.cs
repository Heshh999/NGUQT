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
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace NinjaTrader.NinjaScript.Strategies
{
    /// Pulls per-price executed volume out of a NinjaTrader volumetric series
    /// without compile-time knowledge of its types.
    ///
    /// WHY THIS IS METHOD-BASED
    ///   The first version looked for a member called "Volumes" on the
    ///   individual volumetric bar and expected a dictionary of price ->
    ///   level. NinjaTrader does not expose one. VolumetricBarsType.Volumes is
    ///   an ARRAY of bars, and each bar publishes its per-price figures through
    ///   METHODS - GetAskVolumeForPrice(price), GetBidVolumeForPrice(price) -
    ///   not through a public dictionary.
    ///
    ///   So the read found the array, indexed it correctly, got a real bar
    ///   back, then asked it for a member that does not exist and quietly
    ///   returned false. Every bar came out NO_LEVELS on a series that was
    ///   genuinely volumetric, and because the failure was silent the audit
    ///   blamed the data instead of the reader.
    ///
    ///   It now walks the bar's own price range a tick at a time and asks the
    ///   documented methods, falling back to a dictionary member only if some
    ///   NinjaTrader build happens to expose one.
    ///
    /// EVERY FAILURE IS NOW NAMED
    ///   The old code had three paths that returned false without recording
    ///   anything. That is what made this cost three full runs to diagnose.
    ///   Each one now writes a reason, and the first failure captures the type
    ///   name and its public members so the next mismatch is readable rather
    ///   than guessed at.
    public class V4VolumetricReader
    {
        private bool resolved, failed;
        private object barsTypeObj;
        private MethodInfo askMethod, bidMethod;
        private bool methodsProbed;
        public string LastError = "";
        public string Diagnostics = "";

        /// Hard cap on the ticks walked per bar. A 1-minute MNQ bar spans a few
        /// hundred ticks at most; anything wilder means the range is wrong and
        /// should not turn into a million-iteration loop.
        public int MaxLevelsPerBar = 4000;

        public bool TryRead(object bars, int barIndex, V4FootprintBar into, double tickSize)
        {
            if (failed) return false;
            try
            {
                if (!resolved)
                {
                    if (bars == null) { Fail("series is null"); return false; }
                    object bt = GetMember(bars, "BarsType");
                    if (bt == null) { Fail("series has no BarsType"); return false; }
                    barsTypeObj = bt;
                    resolved = true;
                }

                Array volumesArray = GetMember(barsTypeObj, "Volumes") as Array;
                if (volumesArray == null)
                {
                    Fail("BarsType has no Volumes array - the series is not Volumetric");
                    return false;
                }
                if (barIndex < 0 || barIndex >= volumesArray.Length)
                {
                    LastError = "bar index " + barIndex + " outside Volumes array of "
                              + volumesArray.Length + " - check Maximum bars look back is Infinite";
                    return false;
                }
                object vb = volumesArray.GetValue(barIndex);
                if (vb == null) { LastError = "Volumes[" + barIndex + "] was null"; return false; }

                if (!methodsProbed) ProbeMethods(vb);

                if (askMethod != null && bidMethod != null && tickSize > 0)
                    return ReadByPrice(vb, into, tickSize);

                return ReadByDictionary(vb, into);
            }
            catch (Exception ex)
            {
                Fail(ex.GetType().Name + ": " + ex.Message);
                return false;
            }
        }

        /// The documented path: ask the bar for each price in its own range.
        private bool ReadByPrice(object vb, V4FootprintBar into, double tickSize)
        {
            if (double.IsNaN(into.Low) || double.IsNaN(into.High) || into.High < into.Low) return false;
            int steps = (int)Math.Round((into.High - into.Low) / tickSize) + 1;
            if (steps < 1 || steps > MaxLevelsPerBar)
            {
                LastError = "bar spans " + steps + " ticks, outside the sane range";
                return false;
            }
            object[] arg = new object[1];
            for (int i = 0; i < steps; i++)
            {
                double price = into.Low + i * tickSize;
                arg[0] = price;
                double ask = ToDouble(askMethod.Invoke(vb, arg));
                double bid = ToDouble(bidMethod.Invoke(vb, arg));
                if (ask == 0 && bid == 0) continue;      // nothing traded at this price
                V4FootprintLevel l = new V4FootprintLevel();
                l.Price = price; l.AskVolume = ask; l.BidVolume = bid;
                into.Levels.Add(l);
            }
            into.HasLevels = into.Levels.Count > 0;
            if (!into.HasLevels) LastError = "no traded price levels returned for a bar with volume";
            return into.HasLevels;
        }

        /// Fallback for any build that does expose a price -> level map.
        private bool ReadByDictionary(object vb, V4FootprintBar into)
        {
            string[] names = new string[] { "Volumes", "Levels", "PriceLevels" };
            IDictionary levels = null;
            for (int i = 0; i < names.Length && levels == null; i++)
                levels = GetMember(vb, names[i]) as IDictionary;
            if (levels == null || levels.Count == 0)
            {
                LastError = "volumetric bar exposes neither GetAskVolumeForPrice nor a price map";
                return false;
            }
            foreach (DictionaryEntry kv in levels)
            {
                V4FootprintLevel l = new V4FootprintLevel();
                l.Price = Convert.ToDouble(kv.Key, CultureInfo.InvariantCulture);
                l.AskVolume = Num(kv.Value, "AskVolume");
                l.BidVolume = Num(kv.Value, "BidVolume");
                into.Levels.Add(l);
            }
            into.HasLevels = into.Levels.Count > 0;
            return into.HasLevels;
        }

        /// Finds the per-price accessors once, and records what the type
        /// actually offers so a future mismatch is diagnosable from the audit.
        private void ProbeMethods(object vb)
        {
            methodsProbed = true;
            Type t = vb.GetType();
            askMethod = FindOne(t, new string[] { "GetAskVolumeForPrice", "GetAskVolume" });
            bidMethod = FindOne(t, new string[] { "GetBidVolumeForPrice", "GetBidVolume" });

            StringBuilder sb = new StringBuilder();
            sb.Append("volumetric bar type: ").Append(t.FullName);
            sb.Append("  ask accessor: ").Append(askMethod == null ? "NOT FOUND" : askMethod.Name);
            sb.Append("  bid accessor: ").Append(bidMethod == null ? "NOT FOUND" : bidMethod.Name);
            if (askMethod == null || bidMethod == null)
            {
                sb.Append(Environment.NewLine).Append("  members seen: ");
                MemberInfo[] ms = t.GetMembers(BindingFlags.Public | BindingFlags.Instance);
                for (int i = 0; i < ms.Length && i < 40; i++) sb.Append(ms[i].Name).Append(' ');
            }
            Diagnostics = sb.ToString();
        }

        private static MethodInfo FindOne(Type t, string[] names)
        {
            for (int i = 0; i < names.Length; i++)
            {
                MethodInfo m = t.GetMethod(names[i], new Type[] { typeof(double) });
                if (m != null) return m;
            }
            return null;
        }

        private void Fail(string why) { failed = true; LastError = why; }

        private static double ToDouble(object o)
        {
            if (o == null) return 0;
            try { return Convert.ToDouble(o, CultureInfo.InvariantCulture); }
            catch (Exception) { return 0; }
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

        private static double Num(object o, string name) { return ToDouble(GetMember(o, name)); }
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
            if (reader.TryRead(BarsArray[0], CurrentBar, b, engine.TickSize)) barsWithLevels++;

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
            if (reader != null && reader.Diagnostics.Length > 0)
                report += reader.Diagnostics + Environment.NewLine;
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
