// ============================================================================
// ScalpTests.cs - deterministic tests for ScalpResearchEngine.
// The assertions that matter here are the lookahead ones: a level must not be
// usable before it was knowable, and a bar must not be judged against a level
// its own print helped create.
// ============================================================================

using System;
using System.Collections.Generic;
using NinjaTrader.NinjaScript.Strategies.MnqTwo;

namespace MnqTwoTests
{
    public static class ScalpTests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        private static ResearchBar B(DateTime etOpen, double o, double h, double l, double c, double v)
        {
            ResearchBar b = new ResearchBar();
            b.EtOpen = etOpen; b.EtClose = etOpen.AddMinutes(1);
            b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = v;
            return b;
        }

        private static KeyLevelEngine Levels()
        {
            KeyLevelEngine lv = new KeyLevelEngine();
            lv.OnOneMinuteBar(new DateTime(2026, 7, 29, 12, 0, 0), new DateTime(2026, 7, 29, 12, 1, 0),
                new DateTime(2026, 7, 29, 16, 0, 0), 20000, 20500, 19500, 20000, 1000);
            lv.OnOneMinuteBar(new DateTime(2026, 8, 3, 19, 0, 0), new DateTime(2026, 8, 3, 19, 1, 0),
                new DateTime(2026, 8, 3, 23, 0, 0), 20000, 20100, 19900, 20000, 1000);
            lv.OnOneMinuteBar(new DateTime(2026, 8, 4, 19, 0, 0), new DateTime(2026, 8, 4, 19, 1, 0),
                new DateTime(2026, 8, 4, 23, 0, 0), 20000, 20010, 19990, 20000, 1000);
            return lv;
        }

        public static int Run()
        {
            Console.WriteLine("SCALP RESEARCH ENGINE:");
            DateTime d = new DateTime(2026, 8, 5);
            string[] hdr = ScalpResearchEngine.CsvHeader().Split(',');

            // ---- the engine cannot trade ----
            {
                Type t = typeof(ScalpResearchEngine);
                string[] banned = new string[] { "EnterLong", "EnterShort", "ExitLong", "ExitShort",
                                                 "SubmitOrder", "EnterPosition", "ExitMarket" };
                bool clean = true;
                foreach (string m in banned) if (t.GetMethod(m) != null) clean = false;
                Check(clean, "the scalp engine exposes NO entry/exit/order method - it cannot trade");
                Check(t.GetMethod("OnBar") != null, "it accepts completed bars and nothing else");
            }

            // ---- premarket freezes at the cash open and resets daily ----
            {
                PremarketTracker pm = new PremarketTracker();
                for (int i = 0; i < 60; i++)                       // 05:00-06:00 ET
                    pm.OnBarClosed(B(d.AddHours(5).AddMinutes(i), 20000, 20000 + i, 19990, 20000 + i, 100));
                Check(pm.High == 20059 && pm.Low == 19990, "premarket high/low accumulate before the open");
                Check(!pm.Complete, "and are not frozen while the premarket is still running");
                Check(pm.TrendPts == 59, "premarket drift is last close minus first close: " + pm.TrendPts);
                pm.OnBarClosed(B(d.AddHours(9).AddMinutes(29), 20080, 20090, 20070, 20085, 100));  // closes 09:30
                Check(pm.Complete, "the premarket freezes at 09:30");
                Check(pm.TrendPts == 85, "and the 09:30 bar still counts toward it: " + pm.TrendPts);
                double frozenHigh = pm.High, frozenTrend = pm.TrendPts;
                pm.OnBarClosed(B(d.AddHours(10), 20000, 21000, 19000, 20900, 100));   // RTH bar
                Check(pm.High == frozenHigh, "an RTH bar cannot change the premarket high afterwards");
                Check(pm.TrendPts == frozenTrend, "nor the premarket drift - it is frozen, not still running");
                pm.OnBarClosed(B(d.AddDays(1).AddHours(5), 21000, 21010, 20990, 21000, 100));
                Check(pm.High == 21010, "a new day rebuilds the premarket from scratch");
            }

            // ---- a level is refused until it is knowable ----
            {
                HigherTfStructure s = new HigherTfStructure("15m");
                s.ConfirmBars = 2; s.PivotLeftBars = 2;
                DateTime t = d.AddHours(9);
                double[] hi = new double[] { 20010, 20020, 20050, 20030, 20025 };
                for (int i = 0; i < 5; i++)
                {
                    ResearchBar hb = new ResearchBar();
                    hb.EtOpen = t.AddMinutes(15 * i); hb.EtClose = hb.EtOpen.AddMinutes(15);
                    hb.Open = hi[i]; hb.High = hi[i]; hb.Low = hi[i]; hb.Close = hi[i]; hb.Volume = 1;
                    s.OnBar(hb);
                }
                HtfSwing sw = s.SwingHighKnownAt(t.AddHours(3));
                Check(sw.Valid, "a 15m swing high is published after confirmation");
                TrackedLevel tl = new TrackedLevel();
                tl.Name = "SWING_15M_HIGH"; tl.Price = sw.Price; tl.KnownAtEt = sw.KnownAtEt;
                Check(!tl.UsableAt(sw.KnownAtEt.AddSeconds(-1)),
                      "a tracked level is UNUSABLE one second before it became knowable");
                Check(tl.UsableAt(sw.KnownAtEt), "and usable from the confirming close onward");
                TrackedLevel nan = new TrackedLevel();
                Check(!nan.UsableAt(DateTime.MaxValue), "a level with no price is never usable, at any time");
            }

            // ---- fine-grained session buckets ----
            {
                Check(ScalpResearchEngine.Bucket(d.AddHours(9).AddMinutes(35)) == ScalpTimeBucket.T0930_0945,
                      "09:35 falls in the 09:30-09:45 bucket");
                Check(ScalpResearchEngine.Bucket(d.AddHours(9).AddMinutes(50)) == ScalpTimeBucket.T0945_1000,
                      "09:50 falls in the 09:45-10:00 bucket");
                Check(ScalpResearchEngine.Bucket(d.AddHours(10).AddMinutes(59)) == ScalpTimeBucket.T1045_1100,
                      "10:59 falls in the 10:45-11:00 bucket");
                Check(ScalpResearchEngine.Bucket(d.AddHours(7).AddMinutes(45)) == ScalpTimeBucket.T0730_0800,
                      "07:45 falls in the premarket 07:30-08:00 bucket");
                Check(ScalpResearchEngine.Bucket(d.AddHours(2)) == ScalpTimeBucket.OVERNIGHT,
                      "02:00 is overnight");
            }

            // ---- end to end: rows are emitted, one per level interaction ----
            {
                List<string> rows = new List<string>();
                ScalpResearchEngine eng = new ScalpResearchEngine(Levels(), rows.Add);
                eng.TimeframeLabel = "1m";
                eng.ControlSampleRate = 0;            // structure rows only, for a clean assertion
                eng.RoundNumberStep = 0;              // keep the level book small in this fixture
                DateTime t = d.AddHours(9);
                // 40 quiet bars to build ATR and the session, then a bar that sweeps 20010
                for (int i = 0; i < 40; i++)
                    eng.OnBar(B(t.AddMinutes(i), 20000, 20002, 19998, 20000, 100));
                eng.OnBar(B(t.AddMinutes(40), 20000, 20015, 19999, 20003, 500));
                for (int i = 41; i < 130; i++)
                    eng.OnBar(B(t.AddMinutes(i), 20003, 20005, 20001, 20003, 100));
                eng.Finish();
                Check(rows.Count > 0, "structure interactions produce rows: " + rows.Count);
                bool widthOk = true;
                foreach (string r in rows) if (r.Split(',').Length != hdr.Length) widthOk = false;
                Check(widthOk, "every row width matches the header exactly (" + hdr.Length + " columns)");

                int li = Array.IndexOf(hdr, "levelName");
                int ki = Array.IndexOf(hdr, "eventKind");
                bool named = true, allStructure = true;
                foreach (string r in rows)
                {
                    string[] c = r.Split(',');
                    if (c[li] == "NONE") named = false;
                    if (c[ki] != "STRUCTURE") allStructure = false;
                }
                Check(named, "every structure row names the level it is about");
                Check(allStructure, "with the control rate at 0, no control rows appear");
                Check(eng.ControlsEmitted == 0, "and the control counter agrees");
            }

            // ---- the control group is what makes 'at a level vs away' testable ----
            {
                List<string> rows = new List<string>();
                ScalpResearchEngine eng = new ScalpResearchEngine(Levels(), rows.Add);
                eng.ControlSampleRate = 2; eng.RoundNumberStep = 0;
                DateTime t = d.AddHours(9);
                for (int i = 0; i < 200; i++)      // drift far from every level
                    eng.OnBar(B(t.AddMinutes(i), 20000 + i * 3, 20002 + i * 3, 19998 + i * 3, 20000 + i * 3, 100));
                eng.Finish();
                Check(eng.ControlsEmitted > 0, "control rows are sampled from bars that touched nothing: "
                      + eng.ControlsEmitted);
                int ki = Array.IndexOf(hdr, "eventKind");
                int li = Array.IndexOf(hdr, "levelName");
                bool ok = true;
                foreach (string r in rows)
                {
                    string[] c = r.Split(',');
                    if (c[ki] == "CONTROL" && c[li] != "NONE") ok = false;
                }
                Check(ok, "a control row carries no level - it is the away-from-structure comparison");
            }

            // ---- labels only ever come from later bars ----
            {
                List<string> rows = new List<string>();
                ScalpResearchEngine eng = new ScalpResearchEngine(Levels(), rows.Add);
                eng.ControlSampleRate = 0; eng.RoundNumberStep = 0;
                DateTime t = d.AddHours(9);
                for (int i = 0; i < 40; i++)
                    eng.OnBar(B(t.AddMinutes(i), 20000, 20002, 19998, 20000, 100));
                eng.OnBar(B(t.AddMinutes(40), 20000, 20015, 19999, 20003, 500));
                Check(rows.Count == 0, "an event is NOT written while its forward horizon is still running");
                Check(eng.EventsPending > 0, "it is held pending instead");
                for (int i = 41; i < 140; i++)
                    eng.OnBar(B(t.AddMinutes(i), 20003, 20060, 20001, 20055, 100));
                Check(rows.Count > 0, "and released only once the horizon has fully elapsed");
                int mi = Array.IndexOf(hdr, "mfeLong_80");
                int bi = Array.IndexOf(hdr, "barsObserved");
                string[] c0 = rows[0].Split(',');
                Check(int.Parse(c0[bi]) == 80, "a released row observed its full 80-bar horizon");
                Check(double.Parse(c0[mi], System.Globalization.CultureInfo.InvariantCulture) > 40,
                      "and its MFE reflects the forward rally: " + c0[mi]);
            }

            Console.WriteLine();
            Console.WriteLine(string.Format("SCALP ENGINE: {0} passed, {1} failed", passed, failed));
            return failed;
        }
    }
}
