// ======================================================================
// V41Bar1mCaptureHost.cs - 1-MINUTE ONLY multi-year bar capture
// ======================================================================
// Instrument-agnostic: it captures whatever the chart holds (ES, NQ, MNQ,
// MES ...) as completed 1-minute bars, and NOTHING ELSE.
//
// WHY THIS EXISTS: MnqV41LtfCaptureHost also adds 30s/15s/5s series,
// which forces a TICK data download. For multi-year history that is an
// enormous download and often unavailable far back. This host adds NO
// secondary series, so it runs on MINUTE data alone - which is all the
// ES-NQ cross-market study needs.
//
// Output schema is deliberately identical to the LTF capture files, so
// analysis/xmarket/es_nq_data_spec.py reads it with no changes.
//
// THIS STRATEGY SUBMITS NO ORDERS.
// THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
// ======================================================================
#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Globalization;
using System.IO;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class V41Bar1mCaptureHost : Strategy
    {
        [NinjaScriptProperty]
        [Display(Name = "Output folder", Order = 1, GroupName = "01 Capture",
                 Description = "Folder for 1m capture CSVs. Blank = Documents.")]
        public string OutputFolder { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "File tag", Order = 2, GroupName = "01 Capture",
                 Description = "Optional tag in the filename, e.g. ES or NQ. "
                             + "Blank = the instrument's own name.")]
        public string FileTag { get; set; }

        private TimeZoneInfo etZone;
        private bool configured, dataWasLoaded, diagPrinted;
        private StreamWriter wtr;
        private string wtrDay = "", dir;
        private long rows, days;
        private int sinceFlush;
        private DateTime lastProgress = DateTime.MinValue;
        private const int FlushEvery = 500;

        private const string Header =
            "timestampET,instrument,contract,timeframe,open,high,low,close,volume,"
            + "bidVolume,askVolume,delta,deltaPercent,"
            + "parentCandidate,parentEventId,parentDirection,parentAvailableTime,"
            + "parentEntryTime,parentEntryPrice,parentATR,fvgLow,fvgHigh,"
            + "structuralInvalidation,parentStillValid,engineVersion";

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "V41Bar1mCaptureHost";
                Description = "1-minute only bar capture, any instrument. NO ORDERS.";
                Calculate = Calculate.OnBarClose;
                IsInstantiatedOnEachOptimizationIteration = false;
                OutputFolder = "";
                FileTag = "";
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
                // NO AddDataSeries. That is the entire point: minute data only.
            }
            else if (State == State.DataLoaded)
            {
                dataWasLoaded = true;
                dir = string.IsNullOrEmpty(OutputFolder)
                    ? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
                    : OutputFolder;
                dir = Path.Combine(dir, "V41_bar1m");
                try { Directory.CreateDirectory(dir); } catch (Exception) { }
            }
            else if (State == State.Terminated)
            {
                if (configured && dataWasLoaded)
                {
                    Print("======================================================");
                    Print("1-MINUTE CAPTURE COMPLETE");
                    Print("  instrument  " + Tag());
                    Print("  1m bars     " + rows);
                    Print("  day files   " + days);
                    Print("  files in    " + dir);
                    if (rows == 0)
                        Print("  WARNING: 0 bars - no minute data loaded for this range.");
                    Print("======================================================");
                }
                if (wtr != null) { try { wtr.Flush(); wtr.Close(); } catch (Exception) { } }
            }
        }

        private string Tag()
        {
            if (!string.IsNullOrEmpty(FileTag)) return FileTag;
            return Instrument == null ? "UNKNOWN" : Instrument.MasterInstrument.Name;
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
            CultureInfo ci = CultureInfo.InvariantCulture;
            DateTime et = ToEt(Time[0]);
            if (!diagPrinted)
            {
                diagPrinted = true;
                Print("======================================================");
                Print("V4.1 1-MINUTE CAPTURE - SUBMITS NO ORDERS");
                Print("  instrument    " + Tag()
                      + (Instrument == null ? "" : "  (" + Instrument.FullName + ")"));
                Print("  output folder " + dir);
                Print("  series        1m ONLY - no tick data required");
                Print("  first bar ET  " + et.ToString("yyyy-MM-dd HH:mm:ss", ci));
                Print("======================================================");
            }
            try
            {
                string day = et.ToString("yyyyMMdd", ci);
                if (wtr == null || day != wtrDay)
                {
                    if (wtr != null) { wtr.Flush(); wtr.Close(); wtr = null; }
                    try { Directory.CreateDirectory(dir); } catch (Exception) { }
                    string p = Path.Combine(dir, "V41_BAR1M_" + Tag().Replace(" ", "")
                                            + "_" + day + ".csv");
                    bool fresh = !File.Exists(p);
                    wtr = new StreamWriter(p, true);
                    if (fresh) wtr.WriteLine(Header);
                    wtrDay = day;
                    days++;
                }
                wtr.WriteLine(string.Join(",", new string[] {
                    et.ToString("yyyy-MM-dd HH:mm:ss", ci),
                    Tag(),
                    Instrument == null ? "" : Instrument.FullName,
                    "1m",
                    Open[0].ToString("R", ci), High[0].ToString("R", ci),
                    Low[0].ToString("R", ci), Close[0].ToString("R", ci),
                    Volume[0].ToString("R", ci),
                    "", "", "", "",
                    "", "", "", "", "", "", "", "", "", "", "FALSE",
                    "V41-BAR1M-CAPTURE-1.0" }));
                rows++;
                if (++sinceFlush >= FlushEvery) { sinceFlush = 0; wtr.Flush(); }
                if ((et - lastProgress).TotalDays >= 30)
                {
                    lastProgress = et;
                    Print("  capture " + et.ToString("yyyy-MM-dd", ci)
                          + "   1m bars " + rows + "   day files " + days);
                }
            }
            catch (Exception ex) { Print("1m capture write failed: " + ex.Message); }
        }
    }
}
