// Harness for MrofBarExport.cs on nt8_stubs_export.cs: NOT NinjaTrader.
// Builds the fake market a scenario file describes, attaches the
// indicator as a chart would, and reports what it asked for, printed
// and wrote. The suite reads the files it leaves behind.
//
//   mono harness.exe <scenario file> <output folder>
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Threading;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;

public static class MrofExportHarness
{
    public static int Main(string[] args)
    {
        CultureInfo ci = CultureInfo.InvariantCulture;
        string root = "ES", chart = "";
        int fromYear = 2016, answer = 300, terminateAfter = -1;
        int waitSeconds = 60;
        MasterInstrument master = new MasterInstrument();
        List<string> known = new List<string>();
        foreach (string raw in File.ReadAllLines(args[0]))
        {
            string[] p = raw.Trim().Split(';');
            if (p.Length < 2) continue;
            if (p[0] == "zone")
                NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo =
                    TimeZoneInfo.FindSystemTimeZoneById(p[1]);
            else if (p[0] == "root") root = p[1];
            else if (p[0] == "chart") chart = p[1];
            else if (p[0] == "fromyear") fromYear = int.Parse(p[1], ci);
            else if (p[0] == "answer") answer = int.Parse(p[1], ci);
            else if (p[0] == "wait") waitSeconds = int.Parse(p[1], ci);
            else if (p[0] == "terminate_after_ms")
                terminateAfter = int.Parse(p[1], ci);
            else if (p[0] == "month")
                master.RolloverCollection.Add(new Rollover
                {
                    ContractMonth = DateTime.ParseExact(
                        p[1], "yyyy-MM", ci),
                    Date = DateTime.ParseExact(p[1], "yyyy-MM", ci)
                               .AddDays(-20)
                });
            else if (p[0] == "known") known.Add(p[1]);
            else if (p[0] == "behavior") BarsRequest.Behavior[p[1]] = p[2];
            else if (p[0] == "bars")
            {
                List<FeedBar> bars = new List<FeedBar>();
                foreach (string line in File.ReadAllLines(p[2]))
                {
                    string[] q = line.Trim().Split(';');
                    if (q.Length != 6) continue;
                    bars.Add(new FeedBar
                    {
                        Time = q[0] == "FUTURE"
                            ? TimeZoneInfo.ConvertTimeFromUtc(
                                DateTime.UtcNow.AddMinutes(30), NinjaTrader
                                .Core.Globals.GeneralOptions.TimeZoneInfo
                                ?? TimeZoneInfo.Local)
                            : DateTime.ParseExact(
                                q[0], "yyyy-MM-dd HH:mm:ss", ci),
                        Ohlc = new double[] {
                            double.Parse(q[1], ci), double.Parse(q[2], ci),
                            double.Parse(q[3], ci), double.Parse(q[4], ci) },
                        Volume = long.Parse(q[5], ci)
                    });
                }
                BarsRequest.Feed[p[1]] = bars;
            }
        }
        master.Name = root;
        Instrument.Masters[root] = master;
        foreach (string name in known)
            Instrument.Known[name] = new Instrument
                { FullName = name, MasterInstrument = master };
        if (chart.Length == 0) chart = root + " 12-26";
        Instrument onChart;
        if (!Instrument.Known.TryGetValue(chart, out onChart))
            onChart = new Instrument { FullName = chart,
                                       MasterInstrument = master };
        if (root == "NONE") onChart.MasterInstrument = null;

        MrofBarExport ind = new MrofBarExport();
        ind.SetState(State.SetDefaults);
        bool defaults = ind.FromYear == 2016 && ind.OutputFolder == "" &&
                        ind.Name == "MrofBarExport" && ind.IsOverlay &&
                        ind.Calculate == Calculate.OnBarClose;
        ind.FromYear = fromYear;
        ind.OutputFolder = args[1];
        ind.Instrument = onChart;
        typeof(MrofBarExport).GetField("answerSeconds",
            BindingFlags.NonPublic | BindingFlags.Instance)
            .SetValue(ind, answer);
        ind.SetState(State.Configure);
        ind.SetState(State.DataLoaded);
        ind.SetState(State.DataLoaded);        // a second call starts nothing
        if (terminateAfter >= 0)
        {
            Thread.Sleep(terminateAfter);
            ind.SetState(State.Terminated);
            Thread.Sleep(4000);                // a late answer arrives
        }
        else
        {
            DateTime until = DateTime.UtcNow.AddSeconds(waitSeconds);
            while (DateTime.UtcNow < until)
            {
                bool over;
                lock (NinjaScriptBase.Printed)
                    over = NinjaScriptBase.Printed.Exists(delegate(string s)
                        { return s.Contains("MROF EXPORT COMPLETE") ||
                                 s.Contains("Nothing is written") ||
                                 s.Contains("has no contract months"); });
                if (over) break;
                Thread.Sleep(20);
            }
            Thread.Sleep(300);
            ind.SetState(State.Terminated);
        }
        lock (BarsRequest.Log)
            foreach (string s in BarsRequest.Log)
                Console.WriteLine("HARNESS " + s);
        lock (NinjaScriptBase.Printed)
            foreach (string s in NinjaScriptBase.Printed)
                Console.WriteLine("HARNESS print " + s);
        Console.WriteLine("HARNESS done ok=1 defaults=" +
            (defaults ? "1" : "0") + " created=" + Instrument.Created +
            " disposed=" + BarsRequest.Disposed);
        return 0;
    }
}
