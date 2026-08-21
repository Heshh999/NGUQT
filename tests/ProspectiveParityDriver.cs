// ======================================================================
// ProspectiveParityDriver.cs - off-platform parity harness
// ======================================================================
// Feeds the SAME merged capture history that cand_spec.load_merged()
// uses through the pure V41FrozenCandidateEngine (the exact class the
// NT8 host runs) and exports events + managed outcomes in the parity
// schema. compare_nt8_parity.py then diffs this against the canonical
// Python events. This proves the C# LOGIC reproduces the frozen Python
// before NinjaTrader is involved; the NT8 run then only has to prove
// the PLATFORM feeds the same features.
//
// Usage: mono parity_driver.exe <ofnew_dir> <of2_dir> <out_dir>
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

public static class ProspectiveParityDriver
{
    private class Row { public string Et; public V41InBar B; }

    public static int Main(string[] args)
    {
        if (args.Length < 3)
        {
            Console.WriteLine("usage: parity_driver <ofnew_dir> <of2_dir> <out_dir>");
            return 2;
        }
        List<Row> rows = new List<Row>();
        foreach (string f in Sorted(args[0]))
            Load(f, rows, true);            // new capture: day <= 2025-11-01
        foreach (string f in Sorted(args[1]))
            Load(f, rows, false);           // old capture: day >  2025-11-01
        rows.Sort(delegate(Row a, Row b) { return string.CompareOrdinal(a.Et, b.Et); });
        List<V41InBar> bars = new List<V41InBar>();
        HashSet<string> seen = new HashSet<string>();
        foreach (Row r in rows)
        {
            if (seen.Contains(r.Et)) continue;      // first-wins, as Python
            seen.Add(r.Et);
            bars.Add(r.B);
        }
        Console.WriteLine("driver: " + bars.Count + " bars  " +
                          bars[0].EtClose + " .. " + bars[bars.Count - 1].EtClose);

        V41FrozenCandidateEngine eng = new V41FrozenCandidateEngine();
        foreach (V41InBar b in bars) eng.OnBar(b);
        eng.FinishHistory();
        Console.WriteLine("driver: signals " + eng.Signals.Count
                          + "  events " + eng.Events.Count
                          + "  fwdDivergentEvents " + eng.FwdDivergentEvents
                          + "  fwdDivergentSignals " + eng.FwdDivergentSignals);

        CultureInfo ci = CultureInfo.InvariantCulture;
        Directory.CreateDirectory(args[2]);
        using (StreamWriter w = new StreamWriter(Path.Combine(args[2], "nt8_signals.csv"), false))
        {
            w.WriteLine("et,dir,eligible");
            foreach (V41Signal sg in eng.Signals)
                w.WriteLine(sg.Et.ToString("yyyy-MM-dd HH:mm:ss", ci) + "," + sg.Dir
                            + "," + ((sg.FwdResolved && sg.Eligible) ? "1" : "0"));
        }
        using (StreamWriter w = new StreamWriter(Path.Combine(args[2], "nt8_events.csv"), false))
        {
            w.WriteLine("cand,eventId,et,dir,entryPx,R,atr,parentEt,zLo,zHi,mid,depth,flow,eligible");
            foreach (V41Event e in eng.Events)
                w.WriteLine(string.Join(",", new string[] {
                    e.Cand, e.Id, e.Et.ToString("yyyy-MM-dd HH:mm:ss", ci),
                    e.Dir.ToString(ci), N(e.EntryPx), N(e.R), N(e.Atr),
                    e.ParentEt == DateTime.MinValue ? ""
                        : e.ParentEt.ToString("yyyy-MM-dd HH:mm:ss", ci),
                    N(e.ZLo), N(e.ZHi), N(e.Mid), N(e.Depth),
                    e.Flow ? "1" : "0", e.Eligible ? "1" : "0" }));
        }
        using (StreamWriter w = new StreamWriter(Path.Combine(args[2], "nt8_trades.csv"), false))
        {
            w.WriteLine("cand,version,eventId,arm,entryPx,stopPts,exitReason,exitPx,heldMin,netPts,mfe,mae,noFill");
            foreach (V41Event e in eng.Events)
            {
                if (!e.Eligible) continue;
                if (e.Cand == "OFH13" || e.Cand == "OFH14")
                {
                    string ver = e.Cand + "_PROSPECTIVE_V1";
                    V41ManagedOutcome o = V41Management.Score(
                        eng.Bars, e, V41Management.StopFor(ver, e));
                    Trade(w, e, ver, "A_ORIGINAL", e.EntryPx, o, "");
                }
                if (e.Cand == "OFH13" || e.Cand == "OFH14" || e.Cand == "G4")
                {
                    int fj; double fpx; string nofill;
                    string ver = e.Cand + "_PROSPECTIVE_V1";
                    if (V41Management.G1Fill(eng.Bars, e, out fj, out fpx, out nofill))
                    {
                        V41Event be = new V41Event();
                        be.Cand = e.Cand; be.Id = e.Id; be.Et = eng.Bars[fj].EtClose;
                        be.EntryIdx = fj; be.Dir = e.Dir; be.EntryPx = fpx;
                        be.R = e.R; be.Atr = e.Atr;
                        V41ManagedOutcome o = V41Management.Score(
                            eng.Bars, be, V41Management.StopFor(ver, e));
                        Trade(w, be, ver, "B_G1_DISCOUNT", fpx, o, "");
                    }
                    else
                    {
                        V41ManagedOutcome o = new V41ManagedOutcome();
                        o.ExitReason = "NO_FILL"; o.NetPts = 0;
                        Trade(w, e, ver, "B_G1_DISCOUNT", double.NaN, o, nofill);
                    }
                }
            }
        }
        Console.WriteLine("driver: wrote nt8_events.csv / nt8_trades.csv");
        return 0;
    }

    private static void Trade(StreamWriter w, V41Event e, string ver, string arm,
                              double px, V41ManagedOutcome o, string nofill)
    {
        w.WriteLine(string.Join(",", new string[] {
            e.Cand, ver, e.Id, arm, N(px), N(o.StopPts), o.ExitReason, N(o.ExitPx),
            o.HeldMin.ToString(CultureInfo.InvariantCulture),
            N(o.NetPts), N(o.Mfe), N(o.Mae), nofill }));
    }

    private static string N(double v)
    {
        return double.IsNaN(v) ? "" : v.ToString("R", CultureInfo.InvariantCulture);
    }

    private static List<string> Sorted(string dir)
    {
        List<string> fs = new List<string>(Directory.GetFiles(dir, "*.csv"));
        fs.Sort(StringComparer.Ordinal);
        return fs;
    }

    private static void Load(string path, List<Row> rows, bool newCapture)
    {
        using (StreamReader r = new StreamReader(path))
        {
            string header = r.ReadLine();
            if (header == null) return;
            string[] h = header.Split(',');
            Dictionary<string, int> ix = new Dictionary<string, int>();
            for (int i = 0; i < h.Length; i++) ix[h[i]] = i;
            int cEt = ix["f_barCloseEt"], cO = ix["f_open"], cH = ix["f_high"],
                cL = ix["f_low"], cC = ix["f_close"], cA = ix["f_atr"],
                cD = ix["f_ofBarDelta"], cR = ix["f_isRth"],
                cFo = ix["f_minutesFromRthOpen"], cTc = ix["f_minutesToRthClose"];
            string line;
            while ((line = r.ReadLine()) != null)
            {
                string[] p = line.Split(',');
                if (p.Length != h.Length) continue;
                string et = p[cEt];
                string day = et.Length >= 10 ? et.Substring(0, 10) : "";
                // replicate load_merged's split exactly
                if (newCapture && string.CompareOrdinal(day, "2025-11-01") > 0) continue;
                if (!newCapture && string.CompareOrdinal(day, "2025-11-01") <= 0) continue;
                double o, hi, lo, c, atr;
                if (!D(p[cO], out o) || !D(p[cH], out hi) || !D(p[cL], out lo)
                    || !D(p[cC], out c) || !D(p[cA], out atr)) continue;  // _mk drops
                V41InBar b = new V41InBar();
                b.EtClose = DateTime.ParseExact(et, "yyyy-MM-dd HH:mm:ss",
                                                CultureInfo.InvariantCulture);
                b.Open = o; b.High = hi; b.Low = lo; b.Close = c; b.Atr = atr;
                double bd;
                b.HasDelta = D(p[cD], out bd);
                b.BarDelta = b.HasDelta ? bd : 0;
                b.IsRth = p[cR] == "TRUE";
                double mfo, mtc;
                b.MinFromRthOpen = D(p[cFo], out mfo) ? (int)mfo : -100000;
                b.MinToRthClose = D(p[cTc], out mtc) ? (int)mtc : -100000;
                Row row = new Row(); row.Et = et; row.B = b;
                rows.Add(row);
            }
        }
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
