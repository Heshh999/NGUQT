#region Using declarations
using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
#endregion

// ======================================================================
// MrofBarExport.cs  -  MROF-BAR-EXPORT-1.0
//
// Every contract of one market, written in one go, instead of one
// manual export per contract in the Historical Data window.
//
// Put this indicator on any chart of the market (for instance
// "ES 12-26"). It takes the market's contract months from NinjaTrader's
// own table, asks for the one-minute bars of each contract ON ITS OWN
// (not merged with the others), and writes one file per contract in
// exactly the format of the Historical Data window's export:
//
//     Documents\MROF_Export\<ROOT>\<ROOT> MM-yy.Last.txt
//     yyyyMMdd HHmmss;open;high;low;close;volume      (UTC, bar end)
//
// The MROF minute-bar tools read these files as they read the manual
// exports. MROF_EXPORT_<ROOT>.txt in the same folder lists each
// contract with its number of bars; it is written last, so a folder
// without it is an export that did not finish.
//
// The export starts when the chart has loaded the indicator and ends
// with "MROF EXPORT COMPLETE" in the Output window. Each run writes its
// files anew. Remove the indicator from the chart afterwards.
//
// READ-ONLY: an Indicator. There is no account access and no order API
// of any kind. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
//
// NOT compiled against NinjaTrader here: the F5 compile and the first
// real run are the operator's. The only NinjaTrader members used are
// BarsRequest (with BarsPeriod, TradingHours, Request, Bars.Count and
// Bars.GetTime/GetOpen/GetHigh/GetLow/GetClose/GetVolume; MergePolicy
// and LookupPolicy are set by name), MasterInstrument.RolloverCollection
// (ContractMonth, read by name), Instrument.GetInstrument and
// Core.Globals.GeneralOptions.TimeZoneInfo.
// ======================================================================
namespace NinjaTrader.NinjaScript.Indicators
{
    // No NinjaTrader namespace is imported: every NinjaTrader type below
    // is written out in full, and every other type that a NinjaTrader
    // namespace might also hold (Timer, Type ...) is too.
    public class MrofBarExport : Indicator
    {
        [NinjaTrader.NinjaScript.NinjaScriptProperty]
        public int FromYear { get; set; }

        [NinjaTrader.NinjaScript.NinjaScriptProperty]
        public string OutputFolder { get; set; }

        private const string Version = "MROF-BAR-EXPORT-1.0";
        private const int MonthsBefore = 7;      // of the contract month
        private int answerSeconds = 300;         // per contract

        private readonly object gate = new object();
        private readonly List<string> names = new List<string>();
        private readonly List<DateTime> months = new List<DateTime>();
        private readonly List<string> report = new List<string>();
        private int[] state;                 // 0 asked, 1 answered, 2 done
        private int current = -1;
        private System.Threading.Timer watchdog;
        private volatile bool stop;
        private bool begun, finished, onItsOwn = true, fromFeed = true;
        private string root = "UNKNOWN", dir = "";
        private TimeZoneInfo appZone;
        private long totalBars;
        private int withBars, withoutBars, notFound, failed;

        protected override void OnStateChange()
        {
            if (State == NinjaTrader.NinjaScript.State.SetDefaults)
            {
                Name = "MrofBarExport";
                Description = Version + ": writes the one-minute bars " +
                              "of every contract of the chart's market " +
                              "(zero orders).";
                Calculate = NinjaTrader.NinjaScript.Calculate.OnBarClose;
                IsOverlay = true;
                FromYear = 2016;
                OutputFolder = "";
            }
            else if (State == NinjaTrader.NinjaScript.State.DataLoaded)
            {
                Begin();
            }
            else if (State == NinjaTrader.NinjaScript.State.Terminated)
            {
                stop = true;
                StopWatchdog();
            }
        }

        private void Begin()
        {
            if (begun) return;
            begun = true;
            if (Instrument == null || Instrument.MasterInstrument == null)
            {
                Print("MROF EXPORT: the chart has no instrument. " +
                      "Nothing is written.");
                return;
            }
            root = Instrument.MasterInstrument.Name;
            string top = string.IsNullOrEmpty(OutputFolder)
                ? Path.Combine(Environment.GetFolderPath(
                      Environment.SpecialFolder.MyDocuments), "MROF_Export")
                : OutputFolder;
            dir = Path.Combine(top, root);
            try
            {
                Directory.CreateDirectory(dir);
                string old = Path.Combine(dir, "MROF_EXPORT_" + root + ".txt");
                if (File.Exists(old)) File.Delete(old);
            }
            catch (Exception ex)
            {
                Print("MROF EXPORT: cannot use the folder " + dir + ": " +
                      ex.Message + ". Nothing is written.");
                return;
            }
            try
            {
                appZone = NinjaTrader.Core.Globals.GeneralOptions.TimeZoneInfo;
            }
            catch (Exception) { appZone = null; }
            if (appZone == null) appZone = TimeZoneInfo.Local;

            // the contract months of this market, from NinjaTrader's table
            DateTime first = new DateTime(FromYear, 1, 1);
            DateTime last = DateTime.Now.Date.AddMonths(4);
            List<DateTime> found = new List<DateTime>();
            try
            {
                foreach (object r in (System.Collections.IEnumerable)
                         Instrument.MasterInstrument.RolloverCollection)
                {
                    DateTime cm = System.Convert.ToDateTime(
                        Member(r, "ContractMonth"),
                        CultureInfo.InvariantCulture);
                    cm = new DateTime(cm.Year, cm.Month, 1);
                    if (cm >= first && cm <= last && !found.Contains(cm))
                        found.Add(cm);
                }
            }
            catch (Exception ex)
            {
                Print("MROF EXPORT: cannot read the contract months of " +
                      root + ": " + ex.Message);
            }
            found.Sort();
            foreach (DateTime cm in found)
            {
                months.Add(cm);
                names.Add(root + " " + cm.ToString(
                    "MM-yy", CultureInfo.InvariantCulture));
            }
            Print("==============================================");
            Print("MROF EXPORT " + root + "  -  no orders  -  " + Version);
            Print("  folder     " + dir);
            Print("  contracts  " + names.Count +
                  (names.Count > 0
                   ? "  (" + names[0] + " to " + names[names.Count - 1] + ")"
                   : ""));
            Print("  Old contracts come from your data feed: stay " +
                  "connected until COMPLETE appears.");
            Print("==============================================");
            if (names.Count == 0)
            {
                Print("MROF EXPORT: " + root + " has no contract months " +
                      "from " + FromYear + " on. Is this a futures chart?");
                return;
            }
            state = new int[names.Count];
            RequestNext();
        }

        // The types of NinjaTrader's rollover table and of the two
        // request policies are never named: their namespaces are not
        // the same in every build, and a wrong guess fails the compile.
        // Their members are read and set by name.
        private static object Member(object o, string name)
        {
            System.Type t = o.GetType();
            System.Reflection.PropertyInfo p = t.GetProperty(name);
            if (p != null) return p.GetValue(o, null);
            System.Reflection.FieldInfo f = t.GetField(name);
            if (f != null) return f.GetValue(o);
            throw new System.MissingMemberException(t.Name, name);
        }

        private static bool SetEnum(object o, string name, string value)
        {
            try
            {
                System.Type t = o.GetType();
                System.Reflection.PropertyInfo p = t.GetProperty(name);
                if (p != null && p.PropertyType.IsEnum)
                {
                    p.SetValue(o, System.Enum.Parse(p.PropertyType, value),
                               null);
                    return true;
                }
                System.Reflection.FieldInfo f = t.GetField(name);
                if (f != null && f.FieldType.IsEnum)
                {
                    f.SetValue(o, System.Enum.Parse(f.FieldType, value));
                    return true;
                }
            }
            catch (Exception) { }
            return false;
        }

        // An existing instrument; else, where this NinjaTrader has the
        // (name, create) form, the same contract created on the fly.
        private static NinjaTrader.Cbi.Instrument Find(string name)
        {
            NinjaTrader.Cbi.Instrument ins = null;
            try { ins = NinjaTrader.Cbi.Instrument.GetInstrument(name); }
            catch (Exception) { ins = null; }
            if (ins != null) return ins;
            try
            {
                System.Reflection.MethodInfo m =
                    typeof(NinjaTrader.Cbi.Instrument).GetMethod(
                        "GetInstrument",
                        new System.Type[] { typeof(string), typeof(bool) });
                if (m != null)
                    ins = m.Invoke(null, new object[] { name, true })
                          as NinjaTrader.Cbi.Instrument;
            }
            catch (Exception) { ins = null; }
            return ins;
        }

        private DateTime ToUtc(DateTime t)
        {
            try
            {
                return TimeZoneInfo.ConvertTimeToUtc(
                    DateTime.SpecifyKind(t, DateTimeKind.Unspecified),
                    appZone);
            }
            catch (Exception) { return t.ToUniversalTime(); }
        }

        private void StopWatchdog()
        {
            System.Threading.Timer w = watchdog;
            watchdog = null;
            if (w != null)
            {
                try { w.Dispose(); }
                catch (Exception) { }
            }
        }

        private void RequestNext()
        {
            int i;
            lock (gate)
            {
                current++;
                i = current;
            }
            if (stop) return;
            if (i >= names.Count) { Finish(); return; }
            string name = names[i];
            NinjaTrader.Cbi.Instrument ins = Find(name);
            if (ins == null)
            {
                Done(i, "NOT FOUND", 0, "", "",
                     "NinjaTrader does not know this contract");
                return;
            }
            DateTime start = months[i].AddMonths(-MonthsBefore);
            DateTime end = months[i].AddMonths(1);
            DateTime tomorrow = DateTime.Now.Date.AddDays(1);
            if (end > tomorrow) end = tomorrow;
            try
            {
                NinjaTrader.Data.BarsRequest req =
                    new NinjaTrader.Data.BarsRequest(ins, start, end);
                req.BarsPeriod = new NinjaTrader.Data.BarsPeriod
                {
                    BarsPeriodType = NinjaTrader.Data.BarsPeriodType.Minute,
                    Value = 1
                };
                req.TradingHours =
                    NinjaTrader.Data.TradingHours.Get("Default 24 x 7");
                // each contract on its own: merged with the others, a
                // file would hold bars that are not its contract's
                if (!SetEnum(req, "MergePolicy", "DoNotMerge"))
                {
                    onItsOwn = false;
                    Done(i, "ERROR", 0, "", "",
                         "this NinjaTrader gives no way to ask for a " +
                         "contract on its own (MergePolicy)");
                    return;
                }
                // from the data feed, not only what is on this computer
                if (!SetEnum(req, "LookupPolicy", "Provider"))
                    fromFeed = false;
                StopWatchdog();
                watchdog = new System.Threading.Timer(delegate(object o)
                {
                    bool mine;
                    lock (gate)
                    {
                        mine = state[i] == 0;
                        if (mine) state[i] = 2;
                    }
                    if (mine)
                        Note(i, "NO ANSWER", 0, "", "",
                             "no answer in " + answerSeconds + " seconds",
                             true);
                }, null, answerSeconds * 1000,
                   System.Threading.Timeout.Infinite);
                req.Request((bars, errorCode, errorMessage) =>
                {
                    lock (gate)
                    {
                        if (state[i] != 0) return;      // given up already
                        state[i] = 1;
                    }
                    string status = "OK", first = "", last = "", why = "";
                    long n = 0;
                    try
                    {
                        if (errorCode.ToString() != "NoError")
                        {
                            status = "ERROR";
                            why = errorCode + " " + errorMessage;
                        }
                        else if (stop)
                        {
                            status = "STOPPED";
                        }
                        else
                        {
                            n = Write(name, bars, out first, out last);
                            if (n == 0) status = "NO BARS";
                        }
                    }
                    catch (Exception ex)
                    {
                        status = "ERROR";
                        why = ex.Message;
                    }
                    try
                    {
                        System.IDisposable d = bars as System.IDisposable;
                        if (d != null) d.Dispose();
                    }
                    catch (Exception) { }
                    Done(i, status, n, first, last, why);
                });
            }
            catch (Exception ex)
            {
                Done(i, "ERROR", 0, "", "", ex.Message);
            }
        }

        // One contract's bars to its file; the number written.
        private long Write(string name, NinjaTrader.Data.BarsRequest bars,
                           out string first, out string last)
        {
            first = "";
            last = "";
            CultureInfo ci = CultureInfo.InvariantCulture;
            int count = bars.Bars == null ? 0 : bars.Bars.Count;
            string path = Path.Combine(dir, name + ".Last.txt");
            if (count == 0)
            {
                if (File.Exists(path)) File.Delete(path);
                return 0;
            }
            long n = 0;
            DateTime nowUtc = DateTime.UtcNow;
            using (StreamWriter w = new StreamWriter(path, false))
            {
                for (int k = 0; k < count; k++)
                {
                    DateTime utc = ToUtc(bars.Bars.GetTime(k));
                    if (utc > nowUtc) continue;       // a bar still forming
                    string stamp = utc.ToString("yyyyMMdd HHmmss", ci);
                    w.WriteLine(stamp + ";" +
                        bars.Bars.GetOpen(k).ToString("R", ci) + ";" +
                        bars.Bars.GetHigh(k).ToString("R", ci) + ";" +
                        bars.Bars.GetLow(k).ToString("R", ci) + ";" +
                        bars.Bars.GetClose(k).ToString("R", ci) + ";" +
                        System.Convert.ToInt64(
                            bars.Bars.GetVolume(k)).ToString(ci));
                    if (n == 0) first = stamp;
                    last = stamp;
                    n++;
                }
            }
            if (n == 0 && File.Exists(path)) File.Delete(path);
            return n;
        }

        private void Done(int i, string status, long n, string first,
                          string last, string why)
        {
            lock (gate)
            {
                if (state[i] == 2) return;
                state[i] = 2;
            }
            Note(i, status, n, first, last, why, true);
        }

        private void Note(int i, string status, long n, string first,
                          string last, string why, bool goOn)
        {
            StopWatchdog();
            lock (gate)
            {
                report.Add("contract;" + names[i] + ";" + status + ";" + n +
                           ";" + first + ";" + last + ";" +
                           why.Replace(";", ",").Replace("\r", " ")
                              .Replace("\n", " "));
                totalBars += n;
                if (status == "OK") withBars++;
                else if (status == "NO BARS") withoutBars++;
                else if (status == "NOT FOUND") notFound++;
                else failed++;
            }
            Print("  MROF export  " + names[i] + "  " + status +
                  (n > 0 ? "  bars " + n + "  " + first + " .. " + last : "") +
                  (why.Length > 0 ? "  (" + why + ")" : "") +
                  "   [" + (i + 1) + "/" + names.Count + "]");
            if (goOn && !stop) RequestNext();
        }

        private void Finish()
        {
            lock (gate)
            {
                if (finished) return;
                finished = true;
            }
            StopWatchdog();
            CultureInfo ci = CultureInfo.InvariantCulture;
            try
            {
                using (StreamWriter s = new StreamWriter(Path.Combine(
                    dir, "MROF_EXPORT_" + root + ".txt"), false))
                {
                    s.WriteLine(Version);
                    s.WriteLine("market;" + root);
                    s.WriteLine("written_utc;" + DateTime.UtcNow.ToString(
                        "yyyyMMdd HHmmss", ci));
                    s.WriteLine("time_zone;" + appZone.Id);
                    s.WriteLine("merge_policy;" +
                                (onItsOwn ? "DoNotMerge" : "NOT SET"));
                    s.WriteLine("lookup_policy;" +
                                (fromFeed ? "Provider" : "NOT SET"));
                    s.WriteLine("contracts;" + names.Count.ToString(ci));
                    s.WriteLine("with_bars;" + withBars.ToString(ci));
                    s.WriteLine("bars;" + totalBars.ToString(ci));
                    foreach (string line in report) s.WriteLine(line);
                    s.WriteLine("complete");
                }
            }
            catch (Exception ex)
            {
                Print("MROF EXPORT: the summary could not be written: " +
                      ex.Message);
            }
            Print("==============================================");
            Print("MROF EXPORT COMPLETE  " + root);
            Print("  contracts with bars  " + withBars + " of " +
                  names.Count);
            Print("  bars                 " + totalBars);
            if (withoutBars > 0)
                Print("  without bars         " + withoutBars +
                      "  (normal for a contract not yet trading)");
            if (notFound > 0)
                Print("  NOT FOUND            " + notFound);
            if (failed > 0)
                Print("  ERROR / NO ANSWER    " + failed);
            if (!fromFeed)
                Print("  NOTE: this NinjaTrader gave no way to ask the " +
                      "data feed (LookupPolicy); only bars already on " +
                      "this computer were written.");
            Print("  folder               " + dir);
            Print("==============================================");
        }
    }
}
