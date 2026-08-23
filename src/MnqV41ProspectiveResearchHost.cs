// ======================================================================
// MnqV41ProspectiveResearchHost.cs  -  MNQ V4.1 prospective shelf host
// ======================================================================
// NinjaTrader 8 host for the FROZEN candidate shelf. Wraps the pure
// V41FrozenCandidateEngine (exact port of cand_spec.py) with the same
// data plumbing the order-flow capture host used, so every input
// feature is produced by the code that produced the research capture:
//   - Volumetric 1m primary series (REQUIRED; validated at startup)
//   - BarDelta = per-price ask volume - bid volume (V4VolumetricReader)
//   - ATR = V4Atr(20), identical to the capture's f_atr
//   - session fields = V4SessionMap on the ET close
//
// MODES
//   HISTORICAL_PARITY  replay history, export one row per candidate
//                      event + managed outcomes, for the Python
//                      comparator. DEFAULT for the first run.
//   PROSPECTIVE_LOG    record events/trades with day > 2026-08-19 into
//                      prospective monthly CSVs. No orders.
//
// ORDERS: THIS VERSION SUBMITS NO ORDERS IN ANY MODE. EnableSim101Orders
// exists (default FALSE) but in this engine version it only PRINTS the
// order it would have submitted, tagged DRY-RUN, and only when the
// account name contains "Sim101". Real Sim101 order wiring is
// DELIBERATELY DEFERRED until the parity and Playback gates pass, per
// the phase plan. There is NO live-trading path.
//
// THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
// ======================================================================
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies.MnqV4;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqV41ProspectiveResearchHost : Strategy
    {
        #region Parameters
        [NinjaScriptProperty]
        [Display(Name = "Mode (PARITY or PROSPECTIVE)", Order = 1, GroupName = "01 Mode",
                 Description = "HISTORICAL_PARITY exports events for the Python comparator. PROSPECTIVE_LOG records only days after 2026-08-19.")]
        public string Mode { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Output folder", Order = 2, GroupName = "01 Mode",
                 Description = "Folder for CSV/audit output. Blank = Documents.")]
        public string OutputFolder { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Enable Sim101 orders (DRY-RUN only in this version)",
                 Order = 3, GroupName = "02 Safety",
                 Description = "Default FALSE. Even when TRUE this engine version submits nothing; it prints DRY-RUN order intents, and only on an account whose name contains Sim101.")]
        public bool EnableSim101Orders { get; set; }
        #endregion

        private readonly V41FrozenCandidateEngine engine = new V41FrozenCandidateEngine();
        private readonly V4VolumetricReader reader = new V4VolumetricReader();
        private readonly V4Atr atr = new V4Atr(20);
        private V41ProspectiveRecorder rec;
        private TimeZoneInfo etZone;
        private bool configured, dataWasLoaded, aborted, diagPrinted;
        private DateTime firstEt = DateTime.MaxValue, lastEt = DateTime.MinValue;
        private long barsSeen, barsNoLevels;
        private readonly List<V41Event> pendingTrades = new List<V41Event>();
        // provenance: was the bar that produced each event loaded as chart
        // history or received from the real-time stream? (audit only)
        private string curSource = "HISTORICAL_LOAD";
        private readonly Dictionary<string, string> evSource = new Dictionary<string, string>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqV41ProspectiveResearchHost";
                Description = "V4.1 frozen prospective shelf - research/logging only. SUBMITS NO ORDERS.";
                Calculate = Calculate.OnBarClose;
                IsInstantiatedOnEachOptimizationIteration = false;
                Mode = "HISTORICAL_PARITY";
                OutputFolder = "";
                EnableSim101Orders = false;
            }
            else if (State == State.Configure)
            {
                configured = true;
                try { etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception)
                {
                    try { etZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
                    catch (Exception) { etZone = null; }
                }
                // Primary series itself must be Volumetric 1m - no extra series.
            }
            else if (State == State.DataLoaded)
            {
                dataWasLoaded = true;
                rec = new V41ProspectiveRecorder(ResolveDir(), Instrument == null
                    ? "MNQ" : Instrument.MasterInstrument.Name, Mode,
                    delegate(string m) { Print(m); });
            }
            else if (State == State.Terminated)
            {
                if (!aborted && configured && dataWasLoaded) Finish();
            }
        }

        private string ResolveDir()
        {
            if (!string.IsNullOrEmpty(OutputFolder)) return OutputFolder;
            return Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        }

        private DateTime ToEt(DateTime t)
        {
            if (etZone == null) return t;
            try { return TimeZoneInfo.ConvertTime(t, TimeZoneInfo.Local, etZone); }
            catch (Exception) { return t; }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0 || CurrentBar < 1) return;

            V4FootprintBar fb = new V4FootprintBar();
            fb.EtClose = ToEt(Time[0]);
            fb.Open = Open[0]; fb.High = High[0]; fb.Low = Low[0];
            fb.Close = Close[0]; fb.Volume = Volume[0];
            double tick = TickSize > 0 ? TickSize : 0.25;
            bool read = reader.TryRead(BarsArray[0], CurrentBar, fb, tick);

            if (!diagPrinted) PrintStartupDiagnostic(read);
            if (aborted) return;
            curSource = State == State.Realtime ? "REALTIME" : "HISTORICAL_LOAD";

            barsSeen++;
            if (fb.EtClose < firstEt) firstEt = fb.EtClose;
            if (fb.EtClose > lastEt) lastEt = fb.EtClose;

            V4Bar vb = new V4Bar();
            vb.EtOpen = fb.EtClose.AddMinutes(-1); vb.EtClose = fb.EtClose;
            vb.Open = fb.Open; vb.High = fb.High; vb.Low = fb.Low;
            vb.Close = fb.Close; vb.Volume = fb.Volume;
            atr.Add(vb);

            double askSum = 0, bidSum = 0;
            bool hasLevels = fb.HasLevels;
            if (hasLevels)
                for (int i = 0; i < fb.Levels.Count; i++)
                { askSum += fb.Levels[i].AskVolume; bidSum += fb.Levels[i].BidVolume; }
            else barsNoLevels++;

            V41InBar b = new V41InBar();
            b.EtClose = fb.EtClose;
            b.Open = fb.Open; b.High = fb.High; b.Low = fb.Low; b.Close = fb.Close;
            b.BarDelta = askSum - bidSum;      // identical to capture ofBarDelta
            b.HasDelta = hasLevels;
            b.Atr = atr.Ready ? atr.Value : double.NaN;
            b.IsRth = V4SessionMap.IsRth(fb.EtClose);
            b.MinFromRthOpen = (int)V4SessionMap.MinutesFromRthOpen(fb.EtClose);
            b.MinToRthClose = (int)V4SessionMap.MinutesToRthClose(fb.EtClose);

            int before = engine.Events.Count;
            engine.OnBar(b);
            for (int i = before; i < engine.Events.Count; i++)
                OnNewEvent(engine.Events[i]);
            ScorePendingTrades(false);
        }

        private bool ProspectiveOnly { get { return Mode != null && Mode.StartsWith("PROSPECTIVE"); } }

        private void OnNewEvent(V41Event e)
        {
            if (ProspectiveOnly &&
                string.CompareOrdinal(e.Et.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
                                      V41Frozen.FreezeDataEnd) <= 0)
            {
                rec.NotePreCutoff(e.Id);       // warmup/initialization - counted, never recorded
                return;                        // spent history is never re-logged
            }
            evSource[e.Id] = curSource;
            rec.WriteEvent(e, curSource);
            if (e.Cand == "OFH13" || e.Cand == "OFH14" || e.Cand == "G4")
                pendingTrades.Add(e);          // OFH13/14 managed; G4/OFH13/OFH14 get G1 B-arm
            if (EnableSim101Orders && IsSimAccount() && !ProspectiveOnly)
                Print("DRY-RUN (no order submitted): " + e.Cand + " " +
                      (e.Dir > 0 ? "LONG" : "SHORT") + " @ " + e.EntryPx + " id=" + e.Id);
        }

        private string SourceOf(string id)
        {
            string src;
            return evSource.TryGetValue(id, out src) ? src : "";
        }

        private bool IsSimAccount()
        {
            try { return Account != null && Account.Name != null && Account.Name.Contains("Sim101"); }
            catch (Exception) { return false; }
        }

        private void ScorePendingTrades(bool final)
        {
            int lastIdx = engine.Bars.Count - 1;
            for (int i = pendingTrades.Count - 1; i >= 0; i--)
            {
                V41Event e = pendingTrades[i];
                // fill window (30) + management horizon (60) fully known at +90
                if (!final && lastIdx - e.EntryIdx < 90) continue;
                if (e.Cand == "OFH13" || e.Cand == "OFH14")
                {
                    string ver = e.Cand + "_PROSPECTIVE_V1";
                    double stop = V41Management.StopFor(ver, e);
                    V41ManagedOutcome o = V41Management.Score(engine.Bars, e, stop);
                    rec.WriteTrade(ver, e, "A_ORIGINAL", e.EntryPx, o, "MARKET_AT_CLOSE", "",
                                   SourceOf(e.Id));
                }
                // G1 diagnostic B-arm per registry - logged only, never primary
                int fj; double fpx; string nofill;
                if (V41Management.G1Fill(engine.Bars, e, out fj, out fpx, out nofill))
                {
                    V41Event be = new V41Event();
                    be.Cand = e.Cand; be.Id = e.Id; be.Et = engine.Bars[fj].EtClose;
                    be.EntryIdx = fj; be.Dir = e.Dir; be.EntryPx = fpx;
                    be.R = e.R; be.Atr = e.Atr; be.ParentEt = e.ParentEt;
                    string ver2 = e.Cand + "_PROSPECTIVE_V1";
                    double stop2 = V41Management.StopFor(ver2, e);
                    V41ManagedOutcome ob = V41Management.Score(engine.Bars, be, stop2);
                    rec.WriteTrade(ver2, be, "B_G1_DISCOUNT", fpx, ob, "LIMIT_TOUCH_0.5ATR", "",
                                   SourceOf(e.Id));
                }
                else
                    rec.WriteNoFill(e, nofill, SourceOf(e.Id));
                pendingTrades.RemoveAt(i);
            }
        }

        private void PrintStartupDiagnostic(bool volumetricOk)
        {
            diagPrinted = true;
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("MNQ V4.1 PROSPECTIVE RESEARCH HOST - STARTUP DIAGNOSTIC");
            sb.AppendLine("THIS STRATEGY SUBMITS NO ORDERS (all order paths are DRY-RUN).");
            sb.AppendLine("======================================================================");
            sb.AppendLine("  instrument         " + (Instrument == null ? "?" : Instrument.MasterInstrument.Name));
            sb.AppendLine("  primary series     must be VOLUMETRIC 1 Minute (ticks/level 1)");
            sb.AppendLine("  volumetric read    " + (volumetricOk ? "TRUE" : "FALSE"));
            sb.AppendLine("  bid/ask available  " + (volumetricOk ? "TRUE" : "FALSE"));
            sb.AppendLine("  time zone          Eastern (" + (etZone == null ? "FALLBACK-LOCAL" : etZone.Id) + ")");
            sb.AppendLine("  mode               " + Mode);
            sb.AppendLine("  output folder      " + (rec == null ? ResolveDir() : rec.Dir));
            sb.AppendLine("  orders enabled     " + EnableSim101Orders + "  (DRY-RUN only in this version)");
            sb.AppendLine("  engine version     " + V41Frozen.EngineVersion);
            sb.AppendLine("  frozen hashes      cand_spec " + V41Frozen.HashCandSpec
                          + "  ofh6 " + V41Frozen.HashOfh6Spec);
            sb.AppendLine("                     ofht_spec " + V41Frozen.HashOfhtSpec
                          + "  cache " + V41Frozen.HashOfhtCache);
            sb.AppendLine("  prospective cutoff day > " + V41Frozen.FreezeDataEnd);
            if (Mode != null && Mode.StartsWith("PROSPECTIVE") && rec != null)
                sb.AppendLine("  ledger preload     " + rec.PreloadSummary
                              + "  (duplicate protection active)");
            sb.AppendLine("  candidates         OFH13_PROSPECTIVE_V1 (PRIMARY, 1.5 ATR stop, 60m)");
            sb.AppendLine("                     OFH14_PROSPECTIVE_V1 (STRUCT stop, 60m)");
            sb.AppendLine("                     G4 / G3 SIGNAL-ONLY;  G1 = diagnostic B-arm only");
            sb.AppendLine("  warm-up            ATR(20)=20 bars, dsum15=15, FVG=3, disp5=5 -> 20 1m bars");
            sb.AppendLine("======================================================================");
            if (!volumetricOk)
            {
                sb.AppendLine("  STARTUP DIAGNOSTIC: FAIL - primary series is not Volumetric.");
                sb.AppendLine("  HARD FAIL: order-flow candidates cannot run on OHLCV proxies.");
                aborted = true;
            }
            else sb.AppendLine("  STARTUP DIAGNOSTIC: PASS");
            Print(sb.ToString());
            if (rec != null) rec.WriteDiag(sb.ToString());
        }

        private void Finish()
        {
            engine.FinishHistory();
            ScorePendingTrades(true);
            if (rec != null)
                rec.Close(engine, firstEt, lastEt, barsSeen, barsNoLevels);
            Print("V4.1 prospective host: " + engine.Events.Count + " candidate events recorded.");
        }
    }
}

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// CSV + audit recorder. Events, managed trades and the parity export
    /// share fixed schemas so the Python comparator never guesses.
    public class V41ProspectiveRecorder
    {
        public const string EventHeader =
            "candidateId,version,eventId,timestampET,direction,entryTime,entryPrice,atr,"
            + "stopPrice,targetPrice,timeExitMin,parentEt,fvgHigh,fvgLow,fvgMid,depth,flow,"
            + "reasonQualified,fwdEligible,parentSignalDivergent,engineVersion,"
            + "candSpecHash,ofh6Hash,barSource";
        public const string TradeHeader =
            "candidateId,version,eventId,arm,timestampET,direction,entryPrice,stopPts,"
            + "exitReason,exitPrice,heldMin,netPts,netUsd,R,mfe,mae,ratio,ff05,ff1,ff2,"
            + "fillAssumption,noFillReason,month,isoWeek,engineVersion,barSource";

        private readonly string dir, tag, mode;
        private readonly Dictionary<string, bool> touched = new Dictionary<string, bool>();
        private readonly Action<string> log;
        private int writeFailures;
        // ---- prospective ledger protection (recording-only; no rule logic) --
        // Existing event/trade keys are preloaded from the output folder at
        // startup so a strategy reload, chart refresh, reconnect or workspace
        // reopen can never append the same EventID twice. Duplicates are
        // logged as DUPLICATE_SUPPRESSED, never silently dropped.
        private readonly HashSet<string> knownEvents = new HashSet<string>();
        private readonly HashSet<string> knownTrades = new HashSet<string>();
        private int dupEvents, dupTrades, preCutoffSkipped, preloadEvents, preloadTrades;
        public int EventsWritten, TradesWritten;

        public int WriteFailures { get { return writeFailures; } }
        public string Dir { get { return dir; } }

        public V41ProspectiveRecorder(string baseDir, string instrument, string mode,
                                      Action<string> log)
        {
            this.mode = mode ?? "HISTORICAL_PARITY";
            this.log = log;
            tag = instrument;
            dir = Path.Combine(baseDir, this.mode.StartsWith("PROSPECTIVE")
                ? "V41_prospective" : "V41_parity");
            EnsureDir();
            if (this.mode.StartsWith("PROSPECTIVE")) PreloadLedger();
        }

        /// Read every existing prospective file once so this session knows
        /// which EventIDs the ledger already holds. Deterministic: the key is
        /// the frozen EventID (candidate + entry-bar ET + direction), so the
        /// same market event always maps to the same key across restarts.
        private void PreloadLedger()
        {
            try
            {
                foreach (string f in Directory.GetFiles(dir, "V41_PROSPECTIVE_EVENTS_*.csv"))
                    foreach (string id in ReadCol(f, 2, -1))
                    { if (knownEvents.Add(id)) preloadEvents++; }
                foreach (string f in Directory.GetFiles(dir, "V41_PROSPECTIVE_TRADES_*.csv"))
                    foreach (string k in ReadCol(f, 2, 3))
                    { if (knownTrades.Add(k)) preloadTrades++; }
            }
            catch (Exception ex) { Fail(dir, ex); }
        }

        private static List<string> ReadCol(string path, int ix, int ix2)
        {
            List<string> outp = new List<string>();
            using (StreamReader r = new StreamReader(path))
            {
                string line = r.ReadLine();          // header
                while ((line = r.ReadLine()) != null)
                {
                    string[] p = line.Split(',');
                    if (p.Length <= ix) continue;
                    outp.Add(ix2 < 0 ? p[ix] : p[ix] + "|" + (p.Length > ix2 ? p[ix2] : ""));
                }
            }
            return outp;
        }

        public string PreloadSummary
        {
            get { return preloadEvents + " events / " + preloadTrades + " trade rows"; }
        }

        /// A frozen-rule event on a bar at or before the prospective cutoff
        /// (warm-up / historical initialization). Counted and logged, never
        /// recorded - and never silently invisible.
        public void NotePreCutoff(string id)
        {
            preCutoffSkipped++;
            if (log != null && preCutoffSkipped <= 20)
                log("PRE-CUTOFF (warmup) event skipped, not prospective: " + id);
        }

        /// The output folder can vanish mid-run (a user clearing it between
        /// runs while the strategy is still loaded). Re-create it before
        /// every write rather than only at construction, and NEVER swallow a
        /// write failure silently - a missing file with no error was the
        /// single most confusing failure mode in the field.
        private bool EnsureDir()
        {
            try { Directory.CreateDirectory(dir); return true; }
            catch (Exception ex) { Fail(dir, ex); return false; }
        }

        private void Fail(string path, Exception ex)
        {
            writeFailures++;
            if (log != null)
                log("V41 RECORDER WRITE FAILED (" + writeFailures + "): " + path
                    + " : " + ex.Message);
        }

        private void Append(string file, string header, string line)
        {
            if (!EnsureDir()) return;
            string path = Path.Combine(dir, file);
            bool first = !touched.ContainsKey(path) && !File.Exists(path);
            touched[path] = true;
            try
            {
                using (StreamWriter w = new StreamWriter(path, true))
                {
                    if (first) w.WriteLine(header);
                    w.WriteLine(line);
                }
            }
            catch (Exception ex) { Fail(path, ex); }
        }

        private static string F(double v)
        {
            return double.IsNaN(v) ? "" : v.ToString("0.####", CultureInfo.InvariantCulture);
        }

        private string EventsFile(DateTime et)
        {
            return mode.StartsWith("PROSPECTIVE")
                ? "V41_PROSPECTIVE_EVENTS_" + et.ToString("yyyy-MM") + ".csv"
                : "V41_PARITY_EVENTS_" + tag + ".csv";
        }

        private string TradesFile(DateTime et)
        {
            return mode.StartsWith("PROSPECTIVE")
                ? "V41_PROSPECTIVE_TRADES_" + et.ToString("yyyy-MM") + ".csv"
                : "V41_PARITY_TRADES_" + tag + ".csv";
        }

        public void WriteEvent(V41Event e, string barSource)
        {
            if (mode.StartsWith("PROSPECTIVE") && !knownEvents.Add(e.Id))
            {
                dupEvents++;
                if (log != null)
                    log("DUPLICATE_SUPPRESSED event " + e.Id
                        + " (already in the prospective ledger)");
                return;
            }
            string ver = e.Cand == "OFH13" || e.Cand == "OFH14"
                ? e.Cand + "_PROSPECTIVE_V1"
                : e.Cand + "_PROSPECTIVE_V1_SIGNAL_ONLY";
            double stop = V41Management.StopFor(e.Cand + "_PROSPECTIVE_V1", e);
            Append(EventsFile(e.Et), EventHeader, string.Join(",", new string[] {
                e.Cand, ver, e.Id,
                e.Et.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                e.Dir > 0 ? "1" : "-1",
                e.Et.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                F(e.EntryPx), F(e.Atr),
                double.IsNaN(stop) ? "" : F(e.EntryPx - e.Dir * stop),
                "",                                    // no targets in registry
                V41Frozen.HorizonMin.ToString(),
                e.ParentEt == DateTime.MinValue ? ""
                    : e.ParentEt.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                F(e.ZHi), F(e.ZLo), F(e.Mid), F(e.Depth), e.Flow ? "TRUE" : "FALSE",
                (e.Reason ?? "").Replace(',', ';'),
                e.FwdResolved ? (e.Eligible ? "TRUE" : "FALSE") : "PENDING",
                e.ParentSignalDivergent ? "TRUE" : "FALSE",
                V41Frozen.EngineVersion, V41Frozen.HashCandSpec, V41Frozen.HashOfh6Spec,
                barSource ?? "" }));
            EventsWritten++;
        }

        public void WriteTrade(string version, V41Event e, string arm, double entryPx,
                               V41ManagedOutcome o, string fillAssumption, string noFill,
                               string barSource)
        {
            if (mode.StartsWith("PROSPECTIVE") && !knownTrades.Add(e.Id + "|" + arm))
            {
                dupTrades++;
                if (log != null)
                    log("DUPLICATE_SUPPRESSED trade " + e.Id + " " + arm);
                return;
            }
            System.Globalization.Calendar cal = CultureInfo.InvariantCulture.Calendar;
            int week = cal.GetWeekOfYear(e.Et, CalendarWeekRule.FirstFourDayWeek, DayOfWeek.Monday);
            Append(TradesFile(e.Et), TradeHeader, string.Join(",", new string[] {
                e.Cand, version, e.Id, arm,
                e.Et.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                e.Dir > 0 ? "1" : "-1", F(entryPx), F(o.StopPts),
                o.ExitReason, F(o.ExitPx), o.HeldMin.ToString(),
                F(o.NetPts), F(o.NetPts * 2.0), F(o.RRes), F(o.Mfe), F(o.Mae),
                o.Mae > 0 ? F(o.Mfe / o.Mae) : "",
                o.Ff05.ToString(), o.Ff1.ToString(), o.Ff2.ToString(),
                fillAssumption, noFill,
                e.Et.ToString("yyyy-MM", CultureInfo.InvariantCulture),
                e.Et.Year + "-W" + week.ToString("00"),
                V41Frozen.EngineVersion, barSource ?? "" }));
            TradesWritten++;
        }

        public void WriteNoFill(V41Event e, string reason, string barSource)
        {
            V41ManagedOutcome o = new V41ManagedOutcome();
            o.ExitReason = "NO_FILL"; o.NetPts = 0; o.HeldMin = 0;
            WriteTrade(e.Cand + "_PROSPECTIVE_V1", e, "B_G1_DISCOUNT",
                       double.NaN, o, "LIMIT_TOUCH_0.5ATR", reason, barSource);
        }

        public void WriteDiag(string text)
        {
            if (!EnsureDir()) return;
            string path = Path.Combine(dir, "V41_PROSPECTIVE_DIAG_" + tag + ".txt");
            try
            {
                using (StreamWriter w = new StreamWriter(path, false))
                    w.Write(text);
            }
            catch (Exception ex) { Fail(path, ex); }
        }

        /// Event rows are written at EMIT time, so their fwdEligible column
        /// is necessarily PENDING (the 60/90-minute forward window has not
        /// happened yet) and parentSignalDivergent is necessarily FALSE.
        /// This file carries the FINALIZED values, keyed by eventId, and is
        /// the column the Python population filter must join on. Written
        /// once at the end of the run, in both modes.
        public const string ResolutionHeader =
            "eventId,candidateId,timestampET,sigEt,fwdEligible,parentSignalDivergent,engineVersion";

        private void WriteResolution(V41FrozenCandidateEngine eng)
        {
            Dictionary<string, bool> sigDiv = new Dictionary<string, bool>();
            for (int i = 0; i < eng.Signals.Count; i++)
            {
                V41Signal s = eng.Signals[i];
                sigDiv[s.Et.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture)] =
                    s.FwdResolved && !s.Eligible;
            }
            if (!EnsureDir()) return;
            bool prospective = mode.StartsWith("PROSPECTIVE");
            // rows produced by THIS session, keyed by eventId
            Dictionary<string, string> rows = new Dictionary<string, string>();
            Dictionary<string, string> monthOf = new Dictionary<string, string>();
            for (int i = 0; i < eng.Events.Count; i++)
            {
                V41Event e = eng.Events[i];
                string day = e.Et.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                // no historical contamination: warm-up / pre-cutoff events
                // never enter a prospective output file
                if (prospective && string.CompareOrdinal(day, V41Frozen.FreezeDataEnd) <= 0)
                    continue;
                string sig = e.SigEt == DateTime.MinValue ? ""
                    : e.SigEt.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
                bool div;
                if (!sigDiv.TryGetValue(sig, out div)) div = false;
                rows[e.Id] = string.Join(",", new string[] {
                    e.Id, e.Cand,
                    e.Et.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture),
                    sig,
                    e.FwdResolved ? (e.Eligible ? "TRUE" : "FALSE") : "PENDING",
                    div ? "TRUE" : "FALSE",
                    V41Frozen.EngineVersion });
                monthOf[e.Id] = e.Et.ToString("yyyy-MM", CultureInfo.InvariantCulture);
            }
            if (!prospective)
            {
                string path = Path.Combine(dir, "V41_PARITY_RESOLUTION_" + tag + ".csv");
                try
                {
                    using (StreamWriter w = new StreamWriter(path, false))
                    {
                        w.WriteLine(ResolutionHeader);
                        foreach (KeyValuePair<string, string> kv in rows) w.WriteLine(kv.Value);
                    }
                }
                catch (Exception ex) { Fail(path, ex); }
                return;
            }
            // prospective: one file per month, MERGED with what earlier
            // sessions wrote. A row from this session replaces the stored row
            // for the same eventId (finalization only improves); rows from
            // earlier sessions this run never saw are preserved.
            HashSet<string> months = new HashSet<string>(monthOf.Values);
            foreach (string mon in months)
            {
                string path = Path.Combine(dir, "V41_PROSPECTIVE_RESOLUTION_" + mon + ".csv");
                Dictionary<string, string> merged = new Dictionary<string, string>();
                List<string> order = new List<string>();
                try
                {
                    if (File.Exists(path))
                        using (StreamReader r = new StreamReader(path))
                        {
                            string line = r.ReadLine();      // header
                            while ((line = r.ReadLine()) != null)
                            {
                                int c = line.IndexOf(',');
                                if (c <= 0) continue;
                                string id = line.Substring(0, c);
                                if (!merged.ContainsKey(id)) order.Add(id);
                                merged[id] = line;
                            }
                        }
                    foreach (KeyValuePair<string, string> kv in rows)
                    {
                        if (monthOf[kv.Key] != mon) continue;
                        if (!merged.ContainsKey(kv.Key)) order.Add(kv.Key);
                        merged[kv.Key] = kv.Value;
                    }
                    using (StreamWriter w = new StreamWriter(path, false))
                    {
                        w.WriteLine(ResolutionHeader);
                        foreach (string id in order) w.WriteLine(merged[id]);
                    }
                }
                catch (Exception ex) { Fail(path, ex); }
            }
        }

        public void Close(V41FrozenCandidateEngine eng, DateTime firstEt, DateTime lastEt,
                          long bars, long noLevels)
        {
            WriteResolution(eng);
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("V4.1 PROSPECTIVE HOST - RUN AUDIT");
            sb.AppendLine("======================================================================");
            sb.AppendLine("  mode              " + mode);
            sb.AppendLine("  first bar (ET)    " + firstEt.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
            sb.AppendLine("  last bar  (ET)    " + lastEt.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture));
            sb.AppendLine("  bars observed     " + bars + "  (no-level bars " + noLevels + ")");
            sb.AppendLine("  OFH6 signals      " + eng.Signals.Count);
            Dictionary<string, int> n = new Dictionary<string, int>();
            for (int i = 0; i < eng.Events.Count; i++)
            {
                V41Event e = eng.Events[i];
                if (e.FwdResolved && !e.Eligible) continue;
                int c; n.TryGetValue(e.Cand, out c); n[e.Cand] = c + 1;
            }
            foreach (KeyValuePair<string, int> kv in n)
                sb.AppendLine("  events " + kv.Key.PadRight(8) + kv.Value.ToString());
            if (mode.StartsWith("PROSPECTIVE"))
            {
                sb.AppendLine("  ledger preloaded  " + preloadEvents + " events / "
                              + preloadTrades + " trade rows");
                sb.AppendLine("  written this run  " + EventsWritten + " events / "
                              + TradesWritten + " trade rows");
                sb.AppendLine("  DUPLICATE_SUPPRESSED  " + dupEvents + " events / "
                              + dupTrades + " trade rows");
                sb.AppendLine("  pre-cutoff warmup events skipped  " + preCutoffSkipped);
            }
            sb.AppendLine("  Q-FWD divergent events   " + eng.FwdDivergentEvents);
            sb.AppendLine("  Q-FWD divergent signals  " + eng.FwdDivergentSignals);
            sb.AppendLine("  engine  " + V41Frozen.EngineVersion);
            sb.AppendLine("  hashes  cand_spec " + V41Frozen.HashCandSpec
                          + " ofh6 " + V41Frozen.HashOfh6Spec
                          + " ofht " + V41Frozen.HashOfhtSpec
                          + " cache " + V41Frozen.HashOfhtCache);
            if (writeFailures > 0)
                sb.AppendLine("  WARNING  " + writeFailures + " file write(s) FAILED this run"
                              + " - output is incomplete. See the Output window.");
            sb.AppendLine("======================================================================");
            EnsureDir();
            string apath = Path.Combine(dir, "V41_PROSPECTIVE_AUDIT_" + tag + ".txt");
            try
            {
                using (StreamWriter w = new StreamWriter(apath, false))
                    w.Write(sb.ToString());
            }
            catch (Exception ex) { Fail(apath, ex); }
            if (log != null)
                log("V41 recorder: output folder " + dir + "  (write failures: "
                    + writeFailures + ")");
        }
    }
}
