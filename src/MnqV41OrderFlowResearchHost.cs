// ======================================================================
// MnqV41OrderFlowResearchHost.cs  -  MNQ V4.1
// ======================================================================
// The NinjaTrader 8 host for executed order flow and volume profile.
//
// THIS STRATEGY SUBMITS NO ORDERS.
//
// REQUIRES a PRIMARY series of Bars type VOLUMETRIC, 1 Minute,
// Ticks Per Level 1. Anything else is captured as missing data and the
// audit FAILS - which is the honest answer, not a bug.
//
// Coverage is the thing to keep in mind while reading any result this
// produces. Volumetric history is far shorter than OHLCV history. Every
// row is stamped STRUCTURE_ORDERFLOW, and the profile audit says the same
// in words, because the failure mode here is not a crash - it is someone
// putting a ten-month order-flow number next to a seven-year structure
// number in the same table.
//
// Two output modes, as the prompt requires:
//   MODE 1 SUMMARY      compact per-bar features, every bar
//   MODE 2 EVENT DETAIL full per-price footprint cells, only inside an
//                       event window, because dumping every price level
//                       for every bar for years is not a research need
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
    public class MnqV41OrderFlowResearch : Strategy
    {
        [NinjaScriptProperty]
        [Display(Name = "File tag", Order = 1, GroupName = "00 Capture")]
        public string FileTag { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Output folder", Order = 2, GroupName = "00 Capture",
                 Description = "Blank writes to the NinjaTrader user data folder.")]
        public string OutputFolder { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "MODE 2 event detail", Order = 3, GroupName = "00 Capture",
                 Description = "Write full per-price footprint cells inside event windows. Off keeps output compact.")]
        public bool WriteEventDetail { get; set; }

        [NinjaScriptProperty]
        [Range(1, 240)]
        [Display(Name = "MODE 2 window (minutes)", Order = 4, GroupName = "00 Capture",
                 Description = "Minutes of footprint detail written around each qualifying event.")]
        public int EventDetailWindowMinutes { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Build volume profile", Order = 5, GroupName = "00 Capture",
                 Description = "POC / VAH / VAL / HVN / LVN from the same per-price read. No second pass.")]
        public bool BuildProfile { get; set; }

        [NinjaScriptProperty]
        [Range(2, 200)]
        [Display(Name = "ATR period", Order = 1, GroupName = "01 Definitions")]
        public int AtrPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(2, 200)]
        [Display(Name = "Divergence lookback (bars)", Order = 2, GroupName = "01 Definitions")]
        public int DivergenceLookback { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 20.0)]
        [Display(Name = "Absorption vol-per-tick multiple", Order = 3, GroupName = "01 Definitions",
                 Description = "Aggressive volume per tick of progress, as a multiple of the bar's mean, to flag an absorption CANDIDATE.")]
        public double AbsorptionVolPerTickMult { get; set; }

        [NinjaScriptProperty]
        [Range(50.0, 95.0)]
        [Display(Name = "Value area pct", Order = 4, GroupName = "01 Definitions")]
        public double ValueAreaPct { get; set; }

        // ---- state ----------------------------------------------------
        private readonly V4VolumetricReader reader = new V4VolumetricReader();
        private readonly V4OrderFlowAudit ofAudit = new V4OrderFlowAudit();
        private readonly V4VolumeProfileEngine profile = new V4VolumeProfileEngine();
        private readonly V4ValidityFlags validity = new V4ValidityFlags();
        private readonly V4StartupDiagnostic diag = new V4StartupDiagnostic();
        private readonly V4Atr atr = new V4Atr(20);
        private readonly V4Roll volRoll = new V4Roll(20);
        private V4DivergenceTracker divergence;

        private readonly V4Schema summarySchema = new V4Schema("orderflow");
        private readonly V4Schema detailSchema = new V4Schema("footprint_detail");
        private readonly HashSet<string> pathsOpenedThisRun = new HashSet<string>();

        private TimeZoneInfo etZone;
        private double cumDelta, prevCumDelta, dayMinDelta, dayMaxDelta;
        private int curDayKey = int.MinValue;
        private double prevClose = double.NaN;
        private double sessionHigh = double.NaN, sessionLow = double.NaN;
        private DateTime detailUntilEt = DateTime.MinValue;
        private long rows, detailRows;
        private bool aborted, diagPrinted;
        private string outDir = "";
        private DateTime firstEt = DateTime.MaxValue, lastEt = DateTime.MinValue;
        private readonly HashSet<int> profileDays = new HashSet<int>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MnqV41OrderFlowResearch";
                Description = "MNQ V4.1 executed order flow + volume profile. SUBMITS NO ORDERS. "
                            + "Requires a VOLUMETRIC primary series, 1 Minute, Ticks Per Level 1.";
                Calculate = Calculate.OnBarClose;
                IsOverlay = false;
                BarsRequiredToTrade = 0;
                BarsRequiredToPlot = 0;
                // Infinite is REQUIRED: the volumetric reader indexes the
                // BarsType.Volumes array directly, and a truncated lookback
                // makes that index fall outside the array.
                MaximumBarsLookBack = MaximumBarsLookBack.Infinite;
                IsInstantiatedOnEachOptimizationIteration = false;

                FileTag = "v41of";
                OutputFolder = "";
                WriteEventDetail = false;
                EventDetailWindowMinutes = 30;
                BuildProfile = true;
                AtrPeriod = 20;
                DivergenceLookback = 20;
                AbsorptionVolPerTickMult = 2.0;
                ValueAreaPct = 70.0;
            }
            else if (State == State.DataLoaded)
            {
                pathsOpenedThisRun.Clear();
                rows = detailRows = 0;
                cumDelta = prevCumDelta = 0;
                dayMinDelta = dayMaxDelta = 0;
                curDayKey = int.MinValue;
                prevClose = double.NaN;
                sessionHigh = sessionLow = double.NaN;
                firstEt = DateTime.MaxValue; lastEt = DateTime.MinValue;
                profileDays.Clear();
                aborted = false; diagPrinted = false;

                divergence = new V4DivergenceTracker(DivergenceLookback);
                profile.ValueAreaPct = ValueAreaPct;
                profile.TickSize = TickSize > 0 ? TickSize : 0.25;

                try { etZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception)
                {
                    try { etZone = TimeZoneInfo.FindSystemTimeZoneById("US Eastern Standard Time"); }
                    catch (Exception) { etZone = null; }
                }

                outDir = string.IsNullOrEmpty(OutputFolder)
                    ? NinjaTrader.Core.Globals.UserDataDir
                    : OutputFolder;
                try { if (!Directory.Exists(outDir)) Directory.CreateDirectory(outDir); }
                catch (Exception) { }
            }
            else if (State == State.Terminated)
            {
                if (!aborted) Finish();
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

        private static int ExchangeDayKey(DateTime et)
        {
            DateTime d = et.Hour >= 18 ? et.Date.AddDays(1) : et.Date;
            return d.Year * 10000 + d.Month * 100 + d.Day;
        }

        protected override void OnBarUpdate()
        {
            if (aborted) return;
            if (BarsInProgress != 0) return;
            if (CurrentBar < 1) return;

            V4FootprintBar fb = new V4FootprintBar();
            fb.EtClose = ToEt(Time[0]);
            fb.Open = Open[0]; fb.High = High[0]; fb.Low = Low[0];
            fb.Close = Close[0]; fb.Volume = Volume[0];

            double tick = TickSize > 0 ? TickSize : 0.25;
            bool read = reader.TryRead(BarsArray[0], CurrentBar, fb, tick);

            if (!diagPrinted) PrintStartupDiagnostic(read);
            if (aborted) return;

            ofAudit.Observe(fb, tick);
            if (fb.EtClose < firstEt) firstEt = fb.EtClose;
            if (fb.EtClose > lastEt) lastEt = fb.EtClose;

            V4Bar b = new V4Bar();
            b.EtOpen = fb.EtClose.AddMinutes(-1); b.EtClose = fb.EtClose;
            b.Open = fb.Open; b.High = fb.High; b.Low = fb.Low;
            b.Close = fb.Close; b.Volume = fb.Volume;
            atr.Add(b);
            volRoll.Add(fb.Volume);

            int dayKey = ExchangeDayKey(fb.EtClose);
            if (dayKey != curDayKey)
            {
                // Cumulative delta resets at the CME exchange day boundary.
                // That rule is applied here in code and stated in the audit,
                // rather than inherited from an indicator setting that could
                // differ between historical and real-time calculation.
                curDayKey = dayKey;
                cumDelta = 0; prevCumDelta = 0;
                dayMinDelta = 0; dayMaxDelta = 0;
                sessionHigh = fb.High; sessionLow = fb.Low;
            }
            else
            {
                if (fb.High > sessionHigh) sessionHigh = fb.High;
                if (fb.Low < sessionLow) sessionLow = fb.Low;
            }

            if (!fb.HasLevels)
            {
                prevClose = fb.Close;
                return;                     // audit already counted it as missing
            }

            double bandTicks = 2 * tick;
            bool atExtreme = (fb.High >= sessionHigh - bandTicks) || (fb.Low <= sessionLow + bandTicks);

            V4OrderFlowFeatures f = new V4OrderFlowFeatures();
            double relVol = V4Num.SafeDiv(fb.Volume, volRoll.Mean(), 1e-9);
            f.Compute(fb, tick, prevClose, relVol, AbsorptionVolPerTickMult, atExtreme);

            prevCumDelta = cumDelta;
            cumDelta += f.BarDelta;
            f.CumDelta = cumDelta;
            f.CumDeltaChange = cumDelta - prevCumDelta;
            if (cumDelta < dayMinDelta) dayMinDelta = cumDelta;
            if (cumDelta > dayMaxDelta) dayMaxDelta = cumDelta;
            f.MinDelta = dayMinDelta; f.MaxDelta = dayMaxDelta;
            f.CumDeltaSlope = f.CumDeltaChange;

            divergence.Update(f, fb.High, fb.Low, cumDelta);

            if (BuildProfile)
            {
                for (int i = 0; i < fb.Levels.Count; i++)
                    profile.AddLevel(fb.Levels[i].Price,
                                     fb.Levels[i].AskVolume + fb.Levels[i].BidVolume,
                                     fb.EtClose, dayKey);
                profileDays.Add(dayKey);
            }

            WriteSummaryRow(fb, b, f, dayKey);

            // MODE 2: a qualifying event opens a detail window
            if (WriteEventDetail)
            {
                bool qualifies = f.AbsorptionBuyCandidate || f.AbsorptionSellCandidate
                              || f.DeltaFailsBreak || f.StackedBuyLevels[1] > 0 || f.StackedSellLevels[1] > 0;
                if (qualifies) detailUntilEt = fb.EtClose.AddMinutes(EventDetailWindowMinutes);
                if (fb.EtClose <= detailUntilEt) WriteDetailRows(fb, dayKey);
            }

            prevClose = fb.Close;
        }

        private void PrintStartupDiagnostic(bool volumetricRead)
        {
            diagPrinted = true;
            diag.Instrument = SymbolName();
            diag.MergePolicy = "back-adjusted continuous (assumed)";
            diag.SessionTemplate = "as configured on the primary series";
            diag.TimeZone = etZone == null ? "LOCAL (ET zone NOT resolved)" : etZone.Id;
            diag.PrimarySeries = "VOLUMETRIC 1 Minute, Ticks Per Level 1 (REQUIRED)";
            diag.FileTag = FileTag;
            diag.VolumetricPrimary = true;
            diag.OrderFlowAvailable = volumetricRead;
            diag.ProfileAvailable = volumetricRead && BuildProfile;
            diag.DepthAvailable = false;
            diag.VolumetricType = reader.Diagnostics;
            diag.RequiredWarmupBars1m = Math.Max(AtrPeriod, DivergenceLookback) * 3;
            diag.WarmupReason = "ATR and divergence windows";

            int bars = 0;
            try { if (BarsArray != null && BarsArray[0] != null) bars = BarsArray[0].Count; }
            catch (Exception) { }
            diag.AddSeries("1m-vol", 0, bars, DateTime.MinValue, DateTime.MinValue, true,
                           "Volumetric 1 Minute");

            bool ok = diag.Validate();
            PrintLines(diag.Text());
            if (!volumetricRead)
            {
                Print("  volumetric read FAILED: " + reader.LastError);
                Print("  Set the primary series Bars type to VOLUMETRIC, 1 Minute,");
                Print("  Ticks Per Level 1, and Maximum bars look back to Infinite.");
            }
            PrintLines(validity.Summary());
            if (!ok) { aborted = true; Print("V4.1 ORDER FLOW: RUN ABORTED."); }
        }

        /// Why every number below is zero, stated once, most likely cause
        /// first. The audits that follow fail on "bars >= 20000", which is
        /// true but is a symptom.
        private string NoBarsExplanation()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("WHY EVERY NUMBER BELOW IS ZERO");
            sb.AppendLine("======================================================================");
            sb.AppendLine("The primary series loaded NO BARS, so not one bar reached the");
            sb.AppendLine("engine. Probable causes, most likely first:");
            sb.AppendLine("  1. NO TICK DATA for this instrument over the requested range.");
            sb.AppendLine("     Volumetric bars are built from tick data. Minute history goes");
            sb.AppendLine("     back years; most providers keep tick history for only a");
            sb.AppendLine("     limited recent window.");
            sb.AppendLine("  2. The date range does not overlap the contract's life. A single");
            sb.AppendLine("     expiry trades for months, not years, with real volume only in");
            sb.AppendLine("     its final quarter.");
            sb.AppendLine("  3. Not connected to the data provider while the Analyzer loaded.");
            sb.AppendLine("What to do:");
            sb.AppendLine("  - connect to the data feed, then check TICK coverage for this");
            sb.AppendLine("    contract in Tools > Historical Data Manager");
            sb.AppendLine("  - set the range to a recent 2-4 weeks inside the contract's life");
            sb.AppendLine("  - re-run: the startup diagnostic must show a NON-ZERO bar count");
            sb.AppendLine("    before any longer window is worth attempting");
            sb.AppendLine("======================================================================");
            return sb.ToString();
        }

        private void PrintLines(string s)
        {
            if (string.IsNullOrEmpty(s)) return;
            string[] parts = s.Split('\n');
            for (int i = 0; i < parts.Length; i++) Print(parts[i].TrimEnd('\r'));
        }

        private void WriteSummaryRow(V4FootprintBar fb, V4Bar b, V4OrderFlowFeatures f, int dayKey)
        {
            V4Row r = new V4Row(fb.EtClose);
            r.Key("eventId", SymbolName() + "-1m-"
                    + fb.EtClose.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture))
             .Key("symbol", SymbolName())
             .Key("tf", "1m")
             .Key("schemaVersion", V4RowBuilder.SchemaVersion)
             .Key("researchClass", V4ResearchClass.EXPLORATORY.ToString())
             .Key("hypothesisClass", V4HypothesisClass.B_INCREMENTAL.ToString())
             .Key("dataLayer", (BuildProfile ? V4DataLayer.FULL : V4DataLayer.STRUCTURE_ORDERFLOW).ToString());

            r.F("outputMode", "MODE1_SUMMARY")
             .F("quality", fb.HasLevels ? "OK" : "NO_LEVELS")
             .F("hasLevels", fb.HasLevels)
             .F("levelCount", fb.Levels == null ? 0 : fb.Levels.Count);

            V4RowBuilder.Bar(r, b, atr.Value, f.RelVolume);
            V4RowBuilder.Session(r, fb.EtClose);
            f.Write(r);

            if (BuildProfile)
            {
                V4Profile p = profile.Build();
                r.F("profileReady", p.Ready)
                 .F("profilePoc", p.Poc).F("profileVah", p.Vah).F("profileVal", p.Val)
                 .F("profileHvnCount", p.Hvn.Count).F("profileLvnCount", p.Lvn.Count)
                 .F("distPocAtr", V4Num.DistAtr(fb.Close, p.Poc, atr.Value))
                 .F("distVahAtr", V4Num.DistAtr(fb.Close, p.Vah, atr.Value))
                 .F("distValAtr", V4Num.DistAtr(fb.Close, p.Val, atr.Value))
                 .F("profileInteraction", V4VolumeProfileEngine.Interaction(p, b, atr.Value).ToString())
                 .F("insideValueArea", p.Ready && fb.Close <= p.Vah && fb.Close >= p.Val);
            }

            V4RowBuilder.Source(r, V4SourceRegistry.Dealer);
            V4RowBuilder.Validity(r, validity);

            summarySchema.Verify(r);
            Append("orderflow", fb.EtClose, summarySchema.Header, r.Csv());
            rows++;
        }

        /// MODE 2. One row per PRICE LEVEL, not per bar - which is exactly
        /// why it is confined to event windows.
        private void WriteDetailRows(V4FootprintBar fb, int dayKey)
        {
            if (fb.Levels == null) return;
            for (int i = 0; i < fb.Levels.Count; i++)
            {
                V4FootprintLevel lv = fb.Levels[i];
                V4Row r = new V4Row(fb.EtClose);
                r.Key("eventId", SymbolName() + "-1m-"
                        + fb.EtClose.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture))
                 .Key("symbol", SymbolName())
                 .Key("schemaVersion", V4RowBuilder.SchemaVersion);
                r.F("outputMode", "MODE2_EVENT_DETAIL")
                 .F("barCloseEt", fb.EtClose)
                 .F("priceLevel", lv.Price)
                 .F("askExecutedVolumeAtPrice", lv.AskVolume)
                 .F("bidExecutedVolumeAtPrice", lv.BidVolume)
                 .F("deltaAtPrice", lv.AskVolume - lv.BidVolume)
                 .F("levelIsBarHigh", Math.Abs(lv.Price - fb.High) < 1e-9)
                 .F("levelIsBarLow", Math.Abs(lv.Price - fb.Low) < 1e-9);
                detailSchema.Verify(r);
                Append("footprint_detail", fb.EtClose, detailSchema.Header, r.Csv());
                detailRows++;
            }
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
                if (firstTouch) Print("  V4.1 writing " + Path.GetFileName(path));
            }
            catch (Exception e) { Print("V4.1 write failed: " + e.Message); }
        }

        private void Finish()
        {
            string noBars = "";
            if (!diagPrinted)
            {
                // OnBarUpdate never fired: the primary series loaded ZERO
                // bars, so the startup gate never got the chance to run.
                // Before this block existed, Finish() wrote an UNPOPULATED
                // diagnostic whose empty checklist printed PASS above four
                // FAILED audit blocks - and the one fact explaining all of
                // them went unstated. Populate what is knowable, let the
                // diagnostic fail loudly, and say the cause once.
                diag.Instrument = SymbolName();
                diag.FileTag = FileTag;
                diag.PrimarySeries = "PRIMARY SERIES LOADED ZERO BARS";
                diag.VolumetricPrimary = true;
                diag.OrderFlowAvailable = false;
                diag.ProfileAvailable = false;
                diag.AddSeries("1m-vol", 0, 0, DateTime.MinValue, DateTime.MinValue, true,
                               "Volumetric 1 Minute");
                diag.Validate();
                noBars = NoBarsExplanation();
                PrintLines(diag.Text());
                PrintLines(noBars);
            }

            string ofReport = ofAudit.Report();
            PrintLines(ofReport);
            validity.OrderFlowAuditPassed = ofAudit.Passed;
            validity.ProfileAuditPassed = ofAudit.Passed && BuildProfile;

            string profReport = BuildProfile
                ? profile.AuditText(ofAudit.Passed, firstEt, lastEt, profileDays.Count)
                : "";
            if (BuildProfile) PrintLines(profReport);

            Print("  " + summarySchema.Describe());
            if (WriteEventDetail) Print("  " + detailSchema.Describe());
            Print("  summary rows " + rows + "   detail rows " + detailRows);
            Print("  volumetric: " + reader.Diagnostics);

            try
            {
                string p = Path.Combine(outDir, "v4_1_ORDERFLOW_AUDIT_" + FileTag + ".txt");
                using (StreamWriter w = new StreamWriter(p, false))
                {
                    w.Write(diag.Text());
                    if (noBars.Length > 0) w.Write(noBars);
                    w.Write(validity.Summary());
                    w.Write(ofReport);
                    w.WriteLine(summarySchema.Describe());
                    w.WriteLine("volumetric: " + reader.Diagnostics);
                    w.WriteLine();
                    w.WriteLine("IMBALANCE FAMILY (all reported, none chosen)");
                    for (int i = 0; i < V4ImbalanceFamily.Ratios.Length; i++)
                        w.WriteLine("  ratio " + V4ImbalanceFamily.Ratios[i].ToString("0.#", CultureInfo.InvariantCulture)
                                  + "x, minimum level volume " + V4ImbalanceFamily.MinVolume
                                  + ", stacked at " + V4ImbalanceFamily.StackedMin + " consecutive levels");
                    w.WriteLine();
                    w.WriteLine("ABSORPTION DEFINITION");
                    w.WriteLine("  aggressive volume per tick of progress >= "
                              + AbsorptionVolPerTickMult.ToString("0.##", CultureInfo.InvariantCulture)
                              + " x the bar's mean volume per tick,");
                    w.WriteLine("  AND no progress in the aggressor's direction,");
                    w.WriteLine("  AND price at or within 2 ticks of the session extreme.");
                    w.WriteLine("  Every ingredient is emitted raw so this can be rebuilt or");
                    w.WriteLine("  rejected without recapturing.");
                }
                if (BuildProfile)
                {
                    string pp = Path.Combine(outDir, "v4_1_PROFILE_AUDIT_" + FileTag + ".txt");
                    using (StreamWriter w = new StreamWriter(pp, false)) w.Write(profReport);
                }
                Print("  V4.1 audits written.");
            }
            catch (Exception e) { Print("V4.1 audit write failed: " + e.Message); }
        }
    }
}
