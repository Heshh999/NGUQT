// Deterministic tests for VectorCandleResearchEngine.
// The critical property is the NO-LOOKAHEAD CONTRACT: a feature column must never
// be able to see a bar that arrived after the event bar.
using System;
using System.Collections.Generic;
using System.Globalization;
using NinjaTrader.NinjaScript.Strategies.MnqTwo;

namespace MnqTwoTests
{
    public static class ResearchTests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        private static ResearchBar RB(DateTime etOpen, double o, double h, double l, double c, double v)
        {
            ResearchBar b = new ResearchBar();
            b.EtOpen = etOpen; b.EtClose = etOpen.AddMinutes(1);
            b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = v;
            return b;
        }

        private static KeyLevelEngine Levels()
        {
            KeyLevelEngine lv = new KeyLevelEngine();
            // prev week, then "yesterday", then today's exchange day
            lv.OnOneMinuteBar(new DateTime(2026, 7, 29, 12, 0, 0), new DateTime(2026, 7, 29, 12, 1, 0),
                new DateTime(2026, 7, 29, 16, 0, 0), 20000, 20500, 19500, 20000, 1000);
            lv.OnOneMinuteBar(new DateTime(2026, 8, 3, 19, 0, 0), new DateTime(2026, 8, 3, 19, 1, 0),
                new DateTime(2026, 8, 3, 23, 0, 0), 20000, 20100, 19900, 20000, 1000);
            lv.OnOneMinuteBar(new DateTime(2026, 8, 4, 19, 0, 0), new DateTime(2026, 8, 4, 19, 1, 0),
                new DateTime(2026, 8, 4, 23, 0, 0), 20000, 20010, 19990, 20000, 1000);
            return lv;
        }

        /// Warm-up with strictly decreasing volume*spread so no bar ties the 10-bar
        /// maximum. Identical bars would all tie it and every one would classify as a
        /// vector - that is real Traders Reality behaviour, not an engine bug, but it
        /// makes for a useless fixture.
        private static void WarmUp(VectorCandleResearchEngine eng, DateTime d)
        {
            for (int i = 0; i < 11; i++)
                eng.OnBar(RB(d.AddHours(9).AddMinutes(30 + i), 20000, 20002, 19998, 20000, 200 - i * 10));
        }

        public static int Run()
        {
            Console.WriteLine("VECTOR CANDLE RESEARCH ENGINE:");
            DateTime d = new DateTime(2026, 8, 5);
            List<string> rows = new List<string>();

            // ---- warm-up: 10 quiet bars establish avgVol10 and highestVolSpread10 ----
            VectorCandleResearchEngine eng = new VectorCandleResearchEngine(Levels(), rows.Add);
            WarmUp(eng, d);
            Check(eng.EventsPending == 0, "quiet warm-up bars produce no vector events");

            // ---- a genuine GREEN vector: volume 3x the 10-bar average, bullish ----
            eng.OnBar(RB(d.AddHours(9).AddMinutes(41), 20000, 20020, 19999, 20015, 300));
            Check(eng.EventsPending == 1, "a high-volume bullish candle creates one pending event");
            Check(rows.Count == 0, "the event is NOT written before its forward horizon elapses");

            // ---- NO-LOOKAHEAD: drive 60 forward bars straight up ----
            for (int i = 0; i < 60; i++)
                eng.OnBar(RB(d.AddHours(9).AddMinutes(42 + i), 20015 + i, 20019 + i, 20013 + i, 20016 + i, 40));
            Check(rows.Count == 1, "the event is written exactly once, after 60 forward bars");

            string[] hdr = VectorCandleResearchEngine.CsvHeader().Split(',');
            string[] col = rows[0].Split(',');
            Check(hdr.Length == col.Length,
                "header and row have identical column counts (" + hdr.Length + " vs " + col.Length + ")");

            Func<string, string> get = name =>
            {
                for (int i = 0; i < hdr.Length; i++) if (hdr[i] == name) return col[i];
                return "<missing>";
            };

            Check(get("vectorType") == "GREEN_VECTOR", "classified GREEN_VECTOR by the Traders Reality rule");
            Check(get("classificationTrigger") == "VOLUME_2X", "the triggering branch is recorded");
            Check(get("direction") == "BULL", "candle direction recorded");

            // FEATURES must describe the EVENT bar only
            Check(get("close") == "20015", "the close column is the EVENT bar's close, not a later bar");
            Check(get("high") == "20020", "the high column is the EVENT bar's high");
            // warm-up volumes are 200,190,...,100; the previous TEN completed bars for
            // the event are 190..100, whose mean is 145.
            double relVol = double.Parse(get("relVolume"), CultureInfo.InvariantCulture);
            Check(Math.Abs(relVol - 300.0 / 145.0) < 1e-4,
                "relative volume = 300 / avg(previous 10) = 300/145 = " + relVol.ToString("0.000"));
            Check(Math.Abs(double.Parse(get("avgVol10"), CultureInfo.InvariantCulture) - 145.0) < 1e-6,
                "avgVol10 uses exactly the previous 10 COMPLETED bars, never the event bar");

            // LABELS must reflect the forward path
            double mfe60 = double.Parse(get("mfeLong_60"), CultureInfo.InvariantCulture);
            Check(mfe60 > 50, "60-bar MFE captured the forward rally (" + mfe60 + " pts)");
            Check(double.Parse(get("maeLong_60"), CultureInfo.InvariantCulture) < 10,
                "60-bar MAE stayed small on a one-way rally");
            Check(int.Parse(get("barToStopLong")) == -1, "the long stop was never hit on a one-way rally");
            Check(int.Parse(get("barToLong_1R")) > 0, "the +1R level was reached, and the bar index is recorded");
            Check(int.Parse(get("barsObserved")) == 60, "the full 60-bar horizon was observed");

            // ---- R-race ordering is exact, not inferred ----
            // A bar that dips to the stop BEFORE rallying must record the stop first.
            List<string> rows2 = new List<string>();
            VectorCandleResearchEngine e2 = new VectorCandleResearchEngine(Levels(), rows2.Add);
            WarmUp(e2, d);
            e2.OnBar(RB(d.AddHours(9).AddMinutes(41), 20000, 20020, 20000, 20010, 300)); // stop = 10 pts below close
            e2.OnBar(RB(d.AddHours(9).AddMinutes(42), 20010, 20012, 19995, 20005, 40)); // hits stop on bar 1
            for (int i = 0; i < 59; i++)
                e2.OnBar(RB(d.AddHours(9).AddMinutes(43 + i), 20005 + i, 20040 + i, 20004 + i, 20035 + i, 40));
            string[] c2 = rows2[0].Split(',');
            Func<string, string> g2 = name =>
            {
                for (int i = 0; i < hdr.Length; i++) if (hdr[i] == name) return c2[i];
                return "<missing>";
            };
            Check(int.Parse(g2("barToStopLong")) == 1, "the stop is recorded on the exact bar it was hit (bar 1)");
            int b1r = int.Parse(g2("barToLong_1R"));
            Check(b1r > 1, "+1R was reached only later (bar " + b1r + ") — the race order is preserved");

            // ---- the engine NEVER submits an order: it has no order surface at all ----
            bool hasOrderApi = false;
            foreach (var m in typeof(VectorCandleResearchEngine).GetMethods())
                if (m.Name.IndexOf("Enter", StringComparison.OrdinalIgnoreCase) >= 0
                 || m.Name.IndexOf("Exit", StringComparison.OrdinalIgnoreCase) >= 0
                 || m.Name.IndexOf("Order", StringComparison.OrdinalIgnoreCase) >= 0) hasOrderApi = true;
            Check(!hasOrderApi, "the research engine exposes NO entry/exit/order method — it cannot trade");

            // ---- level interaction is classified against the market's OWN levels ----
            Check(get("YDAY_HIGH_interaction") != "<missing>", "per-level interaction columns are present");
            Check(get("YDAY_HIGH_testNumberToday") != "<missing>", "per-level test counter is present");
            Check(get("ema200Regime") != "<missing>", "EMA200 regime column is present");
            Check(get("timeBucket") == "T0930_1000", "time-of-day bucket is correct for a 09:42 event");

            // ---- Finish() flushes partially observed events rather than losing them ----
            List<string> rows3 = new List<string>();
            VectorCandleResearchEngine e3 = new VectorCandleResearchEngine(Levels(), rows3.Add);
            WarmUp(e3, d);
            e3.OnBar(RB(d.AddHours(9).AddMinutes(41), 20000, 20020, 19999, 20015, 300));
            e3.OnBar(RB(d.AddHours(9).AddMinutes(42), 20015, 20025, 20014, 20020, 40));
            Check(rows3.Count == 0, "a partially observed event is not emitted mid-stream");
            e3.Finish();
            Check(rows3.Count == 1, "Finish() flushes it");
            string[] c3 = rows3[0].Split(',');
            Func<string, string> g3 = name =>
            {
                for (int i = 0; i < hdr.Length; i++) if (hdr[i] == name) return c3[i];
                return "<missing>";
            };
            Check(int.Parse(g3("barsObserved")) == 1,
                "barsObserved marks it as a 1-bar observation so short-horizon rows can be filtered out");

            Console.WriteLine();
            Console.WriteLine(string.Format("RESEARCH ENGINE: {0} passed, {1} failed", passed, failed));
            return failed;
        }
    }
}
