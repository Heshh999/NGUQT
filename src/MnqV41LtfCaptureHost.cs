// ======================================================================
// MnqV41LtfCaptureHost.cs - genuine 5s/15s/30s Market Replay capture
// ======================================================================
// Captures REAL lower-timeframe bars as NinjaTrader closes them, during
// Market Replay (or live data). Primary series = 1m Volumetric: it runs
// the FROZEN V41 candidate engine so every lower-timeframe row carries
// the current frozen parent state. Secondary series (5s/15s/30s) are
// added in code and provide OHLCV ONLY - NinjaTrader standard Second
// series carry no per-price bid/ask, so the delta columns are written
// EMPTY. Nothing is interpolated, split, or inherited from 1m.
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
using System.Text;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Strategies.MnqV4;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class MnqV41LtfCaptureHost : Strategy
    {
        [NinjaScriptProperty]
        [Display(Name = "Output folder", Order = 1, GroupName = "01 Capture",
                 Description = "Folder for LTF capture CSVs. Blank = Documents.")]
        public string OutputFolder { get; set; }

        private readonly V41FrozenCandidateEngine engine = new V41FrozenCandidateEngine();
        private readonly V4VolumetricReader reader = new V4VolumetricReader();
        private readonly V4Atr atr = new V4Atr(20);
        private TimeZoneInfo etZone;
        private bool configured, dataWasLoaded, diagPrinted, hasVol;
        private DateTime lastProgress = DateTime.MinValue;
        private StreamWriter wtr;
        private string wtrDay = "";
        private string dir;
        private long rows5, rows15, rows30, rows1m, days;
        // current parent state (latest eligible OFH13 event, frozen rules)
        private V41Event parent;
        private DateTime parentAvail = DateTime.MinValue;

        // ---------------- GENUINENESS PROBE (see Decide) -------------------
        // NinjaTrader builds a Second series from the finest data it holds.
        // With tick data it produces real 5s/15s/30s bars. WITHOUT tick data
        // it falls back to the minute records and hands back one bar per
        // MINUTE, still labelled 5s. Those are not genuine lower-timeframe
        // bars and must never reach disk. A genuine 5s bar closes on the 5s
        // grid, so only 1 in 12 lands on :00 (15s: 1 in 4; 30s: 1 in 2). A
        // minute-built fake lands on :00 every single time. Each Second
        // series is therefore buffered until ProbeBars bars have closed and
        // is written only if it passes.
        private const int ProbeBars = 24;
        private class Pending { public string Day; public string Line; }
        private readonly List<Pending>[] probe = new List<Pending>[4];
        private readonly int[] probeN = new int[4];
        private readonly int[] probeZero = new int[4];
        private readonly int[] verdict = new int[4];   // 0 undecided 1 real -1 fake

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
                Name = "MnqV41LtfCaptureHost";
                Description = "Genuine 5s/15s/30s capture with frozen parent state. NO ORDERS.";
                Calculate = Calculate.OnBarClose;
                IsInstantiatedOnEachOptimizationIteration = false;
                OutputFolder = "";
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
                AddDataSeries(BarsPeriodType.Second, 30);   // BarsInProgress 1
                AddDataSeries(BarsPeriodType.Second, 15);   // BarsInProgress 2
                AddDataSeries(BarsPeriodType.Second, 5);    // BarsInProgress 3
            }
            else if (State == State.DataLoaded)
            {
                dataWasLoaded = true;
                dir = string.IsNullOrEmpty(OutputFolder)
                    ? Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments)
                    : OutputFolder;
                dir = Path.Combine(dir, "V41_ltf");
                try { Directory.CreateDirectory(dir); } catch (Exception) { }
            }
            else if (State == State.Terminated)
            {
                if (configured && dataWasLoaded)
                {
                    Print("======================================================");
                    Print("LTF CAPTURE COMPLETE");
                    // a short run may end before a series proved itself
                    for (int i = 1; i <= 3; i++)
                        if (verdict[i] == 0 && probeN[i] > 0)
                            Decide(i, i == 1 ? "30s" : (i == 2 ? "15s" : "5s"));
                    Print("  1m  bars " + rows1m);
                    Print("  30s bars " + rows30 + Verdict(1));
                    Print("  15s bars " + rows15 + Verdict(2));
                    Print("  5s  bars " + rows5 + Verdict(3));
                    Print("  day files " + days);
                    Print("  parent state " + (hasVol ? "RECORDED (volumetric primary)"
                                                      : "EMPTY (primary not volumetric)"));
                    Print("  files in " + dir);
                    if (rows5 == 0 || rows15 == 0)
                        Print("  WARNING: a second-series produced 0 bars - there is no"
                              + " tick / Market Replay data loaded for this period.");
                    Print("======================================================");
                }
                if (wtr != null) { try { wtr.Flush(); wtr.Close(); } catch (Exception) { } }
            }
        }

        private string Verdict(int bip)
        {
            if (verdict[bip] < 0) return "  seen, 0 WRITTEN - REJECTED AS NOT GENUINE";
            if (verdict[bip] > 0) return "  (genuine)";
            return "";
        }

        private DateTime ToEt(DateTime t)
        {
            if (etZone == null) return t;
            try { return TimeZoneInfo.ConvertTime(t, TimeZoneInfo.Local, etZone); }
            catch (Exception) { return t; }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBars[BarsInProgress] < 1) return;

            if (BarsInProgress == 0)
            {
                // 1m Volumetric primary: run the frozen engine, refresh parent
                V4FootprintBar fb = new V4FootprintBar();
                fb.EtClose = ToEt(Times[0][0]);
                fb.Open = Opens[0][0]; fb.High = Highs[0][0]; fb.Low = Lows[0][0];
                fb.Close = Closes[0][0]; fb.Volume = Volumes[0][0];
                double tick = TickSize > 0 ? TickSize : 0.25;
                bool read = reader.TryRead(BarsArray[0], CurrentBars[0], fb, tick);
                if (!diagPrinted)
                {
                    diagPrinted = true;
                    Print("======================================================");
                    Print("MNQ V4.1 LOWER-TIMEFRAME CAPTURE - SUBMITS NO ORDERS");
                    Print("  output folder   " + dir);
                    Print("  series captured 1m + 30s + 15s + 5s (genuine bars only)");
                    Print("  volumetric read " + read
                          + (read ? "  -> parent state WILL be recorded"
                                  : "  -> LTF bars still captured; parent columns EMPTY"));
                    Print("  engine          " + V41Frozen.EngineVersion);
                    Print("  NOTE: 5s/15s/30s series carry NO bid/ask in NinjaTrader,");
                    Print("        so their delta columns are written EMPTY by design.");
                    Print("======================================================");
                }
                hasVol = read;

                V4Bar vb = new V4Bar();
                vb.EtOpen = fb.EtClose.AddMinutes(-1); vb.EtClose = fb.EtClose;
                vb.Open = fb.Open; vb.High = fb.High; vb.Low = fb.Low;
                vb.Close = fb.Close; vb.Volume = fb.Volume;
                atr.Add(vb);
                double askS = 0, bidS = 0;
                if (fb.HasLevels)
                    for (int i = 0; i < fb.Levels.Count; i++)
                    { askS += fb.Levels[i].AskVolume; bidS += fb.Levels[i].BidVolume; }
                V41InBar b = new V41InBar();
                b.EtClose = fb.EtClose;
                b.Open = fb.Open; b.High = fb.High; b.Low = fb.Low; b.Close = fb.Close;
                b.BarDelta = askS - bidS; b.HasDelta = fb.HasLevels;
                b.Atr = atr.Ready ? atr.Value : double.NaN;
                b.IsRth = V4SessionMap.IsRth(fb.EtClose);
                b.MinFromRthOpen = (int)V4SessionMap.MinutesFromRthOpen(fb.EtClose);
                b.MinToRthClose = (int)V4SessionMap.MinutesToRthClose(fb.EtClose);
                int before = engine.Events.Count;
                engine.OnBar(b);
                for (int i = before; i < engine.Events.Count; i++)
                {
                    V41Event e = engine.Events[i];
                    if (e.Cand == "OFH13")          // primary parent per spec
                    { parent = e; parentAvail = e.Et; }
                }
                // parent expiry: 30 min after entry, or far-side 1m close
                if (parent != null)
                {
                    bool expired = (fb.EtClose - parent.Et).TotalMinutes > 30;
                    bool broken = parent.Dir > 0 ? fb.Close < parent.ZLo
                                                 : fb.Close > parent.ZHi;
                    if (expired || broken) parent = null;
                }
                Write("1m", 0, Times[0][0], Opens[0][0], Highs[0][0], Lows[0][0],
                      Closes[0][0], Volumes[0][0], bidS, askS, fb.HasLevels);
                rows1m++;
                return;
            }
            string tf = BarsInProgress == 1 ? "30s" : (BarsInProgress == 2 ? "15s" : "5s");
            int bip = BarsInProgress;
            Write(tf, bip, Times[bip][0], Opens[bip][0], Highs[bip][0], Lows[bip][0],
                  Closes[bip][0], Volumes[bip][0], 0, 0, false);
            if (bip == 1) rows30++; else if (bip == 2) rows15++; else rows5++;
            DateTime nowEt = ToEt(Times[bip][0]);
            if ((nowEt - lastProgress).TotalMinutes >= 30)
            {
                lastProgress = nowEt;
                Print("  capture " + nowEt.ToString("yyyy-MM-dd HH:mm")
                      + "   1m " + rows1m + "  30s " + rows30
                      + "  15s " + rows15 + "  5s " + rows5);
            }
        }

        private void Write(string tf, int bip, DateTime t, double o, double h, double l,
                           double c, double v, double bidS, double askS, bool hasOf)
        {
            CultureInfo ci = CultureInfo.InvariantCulture;
            DateTime et = ToEt(t);
            try
            {
                string pc = "", pid = "", pd = "", pav = "", pet = "", ppx = "",
                       patr = "", flo = "", fhi = "", inv = "", valid = "FALSE";
                if (parent != null)
                {
                    pc = parent.Cand; pid = parent.Id;
                    pd = parent.Dir > 0 ? "1" : "-1";
                    pav = parentAvail.ToString("yyyy-MM-dd HH:mm:ss", ci);
                    pet = parent.Et.ToString("yyyy-MM-dd HH:mm:ss", ci);
                    ppx = parent.EntryPx.ToString("R", ci);
                    patr = parent.Atr.ToString("R", ci);
                    flo = double.IsNaN(parent.ZLo) ? "" : parent.ZLo.ToString("R", ci);
                    fhi = double.IsNaN(parent.ZHi) ? "" : parent.ZHi.ToString("R", ci);
                    inv = parent.Dir > 0 ? flo : fhi;
                    valid = "TRUE";
                }
                // delta columns: written ONLY when genuinely read (1m volumetric)
                string bidv = hasOf ? bidS.ToString("R", ci) : "";
                string askv = hasOf ? askS.ToString("R", ci) : "";
                string dl = hasOf ? (askS - bidS).ToString("R", ci) : "";
                string dp = (hasOf && (askS + bidS) > 0)
                    ? (100.0 * (askS - bidS) / (askS + bidS)).ToString("0.####", ci) : "";
                string line = string.Join(",", new string[] {
                    et.ToString("yyyy-MM-dd HH:mm:ss", ci),
                    Instrument == null ? "MNQ" : Instrument.MasterInstrument.Name,
                    Instrument == null ? "" : Instrument.FullName,
                    tf, o.ToString("R", ci), h.ToString("R", ci), l.ToString("R", ci),
                    c.ToString("R", ci), v.ToString("R", ci),
                    bidv, askv, dl, dp,
                    pc, pid, pd, pav, pet, ppx, patr, flo, fhi, inv, valid,
                    V41Frozen.EngineVersion });
                string day = et.ToString("yyyyMMdd", ci);

                if (bip == 0) { Sink(day, line); return; }   // 1m primary, always real
                if (verdict[bip] > 0) { Sink(day, line); return; }
                if (verdict[bip] < 0) return;                // fake series, never written

                if (probe[bip] == null) probe[bip] = new List<Pending>();
                Pending pn = new Pending(); pn.Day = day; pn.Line = line;
                probe[bip].Add(pn);
                probeN[bip]++;
                if (et.Second == 0) probeZero[bip]++;
                if (probeN[bip] >= ProbeBars) Decide(bip, tf);
            }
            catch (Exception ex) { Print("LTF capture write failed: " + ex.Message); }
        }

        /// Pass or fail one Second series on the timestamp-grid test, then
        /// either flush its buffer to disk or discard it permanently.
        private void Decide(int bip, string tf)
        {
            int n = probeN[bip], z = probeZero[bip];
            double frac = n > 0 ? (double)z / n : 0.0;
            double expected = bip == 1 ? 0.5 : (bip == 2 ? 0.25 : 1.0 / 12.0);
            bool fake = n >= 8 && frac > 0.9;
            verdict[bip] = fake ? -1 : 1;
            Print("  " + tf + " genuineness  bars " + n + "  on :00 " + z
                  + " (" + (100.0 * frac).ToString("0.0") + "%, real series expects ~"
                  + (100.0 * expected).ToString("0.0") + "%)  -> "
                  + (fake ? "FAKE" : "GENUINE"));
            if (fake)
            {
                Print("  *** " + tf + " REJECTED: NinjaTrader is building this series from"
                      + " MINUTE records, not ticks - every bar lands on :00, i.e. one bar"
                      + " per minute mislabelled " + tf + ".");
                Print("  *** No " + tf + " row will be written. Download tick / Market"
                      + " Replay data for these dates and re-run.");
                probe[bip] = null;
                return;
            }
            List<Pending> buf = probe[bip];
            probe[bip] = null;
            if (buf != null) for (int i = 0; i < buf.Count; i++) Sink(buf[i].Day, buf[i].Line);
        }

        /// One file per ET calendar day: a multi-day run rolls the writer
        /// instead of piling every day into the first day's file.
        private void Sink(string day, string line)
        {
            try
            {
                if (wtr == null || day != wtrDay)
                {
                    if (wtr != null) { wtr.Flush(); wtr.Close(); wtr = null; }
                    try { Directory.CreateDirectory(dir); } catch (Exception) { }
                    string p = Path.Combine(dir, "V41_LTF_" +
                        (Instrument == null ? "MNQ" : Instrument.MasterInstrument.Name)
                        + "_" + day + ".csv");
                    bool fresh = !File.Exists(p);
                    wtr = new StreamWriter(p, true);
                    if (fresh) wtr.WriteLine(Header);
                    wtrDay = day;
                    days++;
                }
                wtr.WriteLine(line);
            }
            catch (Exception ex) { Print("LTF capture write failed: " + ex.Message); }
        }
    }
}
