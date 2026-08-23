// ======================================================================
// ProspectiveLogHarness.cs - PROSPECTIVE_LOG plumbing test (off-platform)
// ======================================================================
// Exercises the RECORDING plumbing of PROSPECTIVE_LOG mode without
// NinjaTrader: prospective-cutoff gating, restart duplicate suppression,
// crashed-session trade recovery, and the monthly merged resolution file.
//
// DATA: real capture bars for 2026-08-18/19 are fed as PRE-CUTOFF
// warm-up; the same bars DATE-SHIFTED +7 days (-> 2026-08-25/26) stand
// in for post-cutoff days. The shifted bars are SYNTHETIC and exist
// ONLY to drive the file plumbing in a scratch folder - they are never
// evidence, never enter any ledger, and validate no market behaviour.
//
// Session A feeds warm-up + "08-25" and then CRASHES (no final flush).
// Session B (fresh engine + recorder, same folder) reloads "08-25" and
// continues through "08-26", then finishes cleanly. Expected:
//   - zero pre-cutoff rows in any prospective file
//   - every 08-25 event suppressed as DUPLICATE in session B
//   - 08-25 trades missing after the crash are recovered exactly once
//   - resolution file holds each eventId once, finalized
//
// Usage: mono prolog_harness.exe <of2_dir> <out_dir>
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using NinjaTrader.NinjaScript.Strategies;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

public static class ProspectiveLogHarness
{
    // minimal replica of the host glue (cutoff gate -> recorder), identical
    // in ordering to MnqV41ProspectiveResearchHost.OnNewEvent/ScorePendingTrades
    private class HostSim
    {
        public readonly V41FrozenCandidateEngine Eng = new V41FrozenCandidateEngine();
        public readonly V41ProspectiveRecorder Rec;
        private readonly List<V41Event> pending = new List<V41Event>();
        public int PreCutoff;

        public HostSim(string outDir)
        {
            Rec = new V41ProspectiveRecorder(outDir, "MNQ", "PROSPECTIVE_LOG",
                delegate(string m) { Console.WriteLine("  [rec] " + m); });
        }

        public void Bar(V41InBar b)
        {
            int before = Eng.Events.Count;
            Eng.OnBar(b);
            for (int i = before; i < Eng.Events.Count; i++)
            {
                V41Event e = Eng.Events[i];
                string day = e.Et.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
                if (string.CompareOrdinal(day, V41Frozen.FreezeDataEnd) <= 0)
                { Rec.NotePreCutoff(e.Id); PreCutoff++; continue; }
                Rec.WriteEvent(e, "HARNESS");
                if (e.Cand == "OFH13" || e.Cand == "OFH14" || e.Cand == "G4")
                    pending.Add(e);
            }
            Score(false);
        }

        public void Score(bool final)
        {
            int last = Eng.Bars.Count - 1;
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                V41Event e = pending[i];
                if (!final && last - e.EntryIdx < 90) continue;
                if (e.Cand == "OFH13" || e.Cand == "OFH14")
                {
                    string ver = e.Cand + "_PROSPECTIVE_V1";
                    V41ManagedOutcome o = V41Management.Score(
                        Eng.Bars, e, V41Management.StopFor(ver, e));
                    Rec.WriteTrade(ver, e, "A_ORIGINAL", e.EntryPx, o, "MARKET_AT_CLOSE", "", "HARNESS");
                }
                int fj; double fpx; string nofill;
                string v2 = e.Cand + "_PROSPECTIVE_V1";
                if (V41Management.G1Fill(Eng.Bars, e, out fj, out fpx, out nofill))
                {
                    V41Event be = new V41Event();
                    be.Cand = e.Cand; be.Id = e.Id; be.Et = Eng.Bars[fj].EtClose;
                    be.EntryIdx = fj; be.Dir = e.Dir; be.EntryPx = fpx;
                    be.R = e.R; be.Atr = e.Atr;
                    V41ManagedOutcome ob = V41Management.Score(
                        Eng.Bars, be, V41Management.StopFor(v2, e));
                    Rec.WriteTrade(v2, be, "B_G1_DISCOUNT", fpx, ob, "LIMIT_TOUCH_0.5ATR", "", "HARNESS");
                }
                else
                    Rec.WriteNoFill(e, nofill, "HARNESS");
                pending.RemoveAt(i);
            }
        }

        public void FinishClean(DateTime first, DateTime last, long bars)
        {
            Eng.FinishHistory();
            Score(true);
            Rec.Close(Eng, first, last, bars, 0);
        }
    }

    public static int Main(string[] args)
    {
        string of2 = args[0], outDir = args[1];
        List<V41InBar> real = Load(of2, "2026-08-17", "2026-08-19");
        Console.WriteLine("harness: " + real.Count + " real bars 08-17..19 (pre-cutoff warmup)");
        List<V41InBar> shifted = new List<V41InBar>();
        foreach (V41InBar b in real)
        {
            V41InBar c = new V41InBar();
            c.EtClose = b.EtClose.AddDays(7);   // 08-24..26, post-cutoff SYNTHETIC
            c.Open = b.Open; c.High = b.High; c.Low = b.Low; c.Close = b.Close;
            c.Atr = b.Atr; c.BarDelta = b.BarDelta; c.HasDelta = b.HasDelta;
            c.IsRth = b.IsRth; c.MinFromRthOpen = b.MinFromRthOpen;
            c.MinToRthClose = b.MinToRthClose;
            shifted.Add(c);
        }
        string d25 = "2026-08-25", d26 = "2026-08-26";

        Console.WriteLine("\n=== SESSION A: warmup (pre-cutoff) + " + d25 + ", then CRASH ===");
        HostSim a = new HostSim(outDir);
        foreach (V41InBar b in real)
            if (Day(b) == "2026-08-18" || Day(b) == "2026-08-19") a.Bar(b);
        foreach (V41InBar b in shifted)
            if (Day(b) == d25) a.Bar(b);
        Console.WriteLine("  session A pre-cutoff events skipped: " + a.PreCutoff);
        Console.WriteLine("  session A CRASH: no final flush, no Close(), trades for late "
                          + d25 + " events remain unwritten");

        Console.WriteLine("\n=== SESSION B: restart, reload " + d25 + " + stream " + d26 + " ===");
        HostSim bh = new HostSim(outDir);
        DateTime first = DateTime.MaxValue, last = DateTime.MinValue;
        long n = 0;
        foreach (V41InBar b in shifted)
            if (Day(b) == d25 || Day(b) == d26)
            {
                bh.Bar(b); n++;
                if (b.EtClose < first) first = b.EtClose;
                if (b.EtClose > last) last = b.EtClose;
            }
        bh.FinishClean(first, last, n);
        Console.WriteLine("\nharness done - inspect " + outDir);
        return 0;
    }

    private static string Day(V41InBar b)
    {
        return b.EtClose.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
    }

    private static List<V41InBar> Load(string dir, string d0, string d1)
    {
        List<V41InBar> outp = new List<V41InBar>();
        List<string> fs = new List<string>(Directory.GetFiles(dir, "*.csv"));
        fs.Sort(StringComparer.Ordinal);
        foreach (string f in fs)
            using (StreamReader r = new StreamReader(f))
            {
                string header = r.ReadLine();
                if (header == null) continue;
                string[] h = header.Split(',');
                Dictionary<string, int> ix = new Dictionary<string, int>();
                for (int i = 0; i < h.Length; i++) ix[h[i]] = i;
                string line;
                while ((line = r.ReadLine()) != null)
                {
                    string[] p = line.Split(',');
                    if (p.Length != h.Length) continue;
                    string et = p[ix["f_barCloseEt"]];
                    string day = et.Substring(0, 10);
                    if (string.CompareOrdinal(day, d0) < 0 || string.CompareOrdinal(day, d1) > 0)
                        continue;
                    double o, hi, lo, c, atrv;
                    if (!D(p[ix["f_open"]], out o) || !D(p[ix["f_high"]], out hi)
                        || !D(p[ix["f_low"]], out lo) || !D(p[ix["f_close"]], out c)
                        || !D(p[ix["f_atr"]], out atrv)) continue;
                    V41InBar b = new V41InBar();
                    b.EtClose = DateTime.ParseExact(et, "yyyy-MM-dd HH:mm:ss",
                                                    CultureInfo.InvariantCulture);
                    b.Open = o; b.High = hi; b.Low = lo; b.Close = c; b.Atr = atrv;
                    double bd;
                    b.HasDelta = D(p[ix["f_ofBarDelta"]], out bd);
                    b.BarDelta = b.HasDelta ? bd : 0;
                    b.IsRth = p[ix["f_isRth"]] == "TRUE";
                    double mfo, mtc;
                    b.MinFromRthOpen = D(p[ix["f_minutesFromRthOpen"]], out mfo) ? (int)mfo : -100000;
                    b.MinToRthClose = D(p[ix["f_minutesToRthClose"]], out mtc) ? (int)mtc : -100000;
                    outp.Add(b);
                }
            }
        return outp;
    }

    private static bool D(string s, out double v)
    {
        v = double.NaN;
        if (string.IsNullOrEmpty(s)) return false;
        if (!double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out v))
            return false;
        return !double.IsNaN(v);
    }
}
