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
            Check(b1r > 1, "+1R was reached only later (bar " + b1r + ") - the race order is preserved");

            // ---- the engine NEVER submits an order: it has no order surface at all ----
            bool hasOrderApi = false;
            foreach (var m in typeof(VectorCandleResearchEngine).GetMethods())
                if (m.Name.IndexOf("Enter", StringComparison.OrdinalIgnoreCase) >= 0
                 || m.Name.IndexOf("Exit", StringComparison.OrdinalIgnoreCase) >= 0
                 || m.Name.IndexOf("Order", StringComparison.OrdinalIgnoreCase) >= 0) hasOrderApi = true;
            Check(!hasOrderApi, "the research engine exposes NO entry/exit/order method - it cannot trade");

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

            // ---- multi-timeframe: one CSV, rows tagged by timeframe, 1m EMA200 as context ----
            {
                List<string> rows4 = new List<string>();
                VectorCandleResearchEngine oneMin = new VectorCandleResearchEngine(Levels(), rows4.Add);
                oneMin.TimeframeLabel = "1m";
                VectorCandleResearchEngine fifteenSec = new VectorCandleResearchEngine(Levels(), rows4.Add);
                fifteenSec.TimeframeLabel = "15s";
                // the sub-minute stream reports the 1m EMA200, not its own
                fifteenSec.Ema200Provider = delegate() { return 12345.0; };
                fifteenSec.Ema9Provider = delegate() { return 999.0; };

                WarmUp(fifteenSec, d);
                fifteenSec.OnBar(RB(d.AddHours(9).AddMinutes(41), 20000, 20020, 19999, 20015, 300));
                fifteenSec.Finish();

                Check(rows4.Count == 1, "the sub-minute stream emitted its event");
                string[] c4 = rows4[0].Split(',');
                Func<string, string> g4 = name =>
                {
                    for (int i = 0; i < hdr.Length; i++) if (hdr[i] == name) return c4[i];
                    return "<missing>";
                };
                Check(g4("timeframe") == "15s", "the row is tagged with its own timeframe");
                Check(g4("ema200") == "12345", "a sub-minute row carries the SUPPLIED 1m EMA200, not its own");
                Check(g4("ema9") == "999", "same for EMA9 context");
                Check(g4("timeEt").Length == 8, "sub-minute rows carry seconds in the timestamp: " + g4("timeEt"));
            }

            // ================================================================
            // HIGHER-TIMEFRAME STRUCTURE - the no-lookahead contract
            // ================================================================
            {
                Func<DateTime, double, double, double, double, ResearchBar> HB =
                    delegate(DateTime open, double o, double h, double l, double c)
                    {
                        ResearchBar b = new ResearchBar();
                        b.EtOpen = open; b.EtClose = open.AddMinutes(3);
                        b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = 1000;
                        return b;
                    };
                HigherTfStructure s = new HigherTfStructure("3m");
                s.ConfirmBars = 2; s.PivotLeftBars = 2;
                DateTime t = d.AddHours(9);
                // bars 0..1 rising, bar 2 is the peak, bars 3..4 confirm it
                double[] highs = new double[] { 20010, 20020, 20050, 20030, 20025 };
                double[] lows = new double[] { 20000, 20005, 20040, 20015, 20010 };
                for (int i = 0; i < 5; i++)
                    s.OnBar(HB(t.AddMinutes(3 * i), lows[i], highs[i], lows[i], highs[i]));

                HtfSwing sw = s.SwingHighKnownAt(t.AddHours(2));
                Check(sw.Valid && sw.Price == 20050, "a 3m swing high is published once bars to its right confirm it");
                Check(sw.FormedAtEt == t.AddMinutes(6).AddMinutes(3),
                      "the swing records the close of the PIVOT bar as its formation time");
                Check(sw.KnownAtEt == t.AddMinutes(12).AddMinutes(3),
                      "the swing becomes KNOWN only at the close of the 2nd confirming bar");
                Check(sw.KnownAtEt > sw.FormedAtEt, "confirmation always lags formation - never the reverse");

                // the decisive lookahead test: query BEFORE confirmation completed
                HtfSwing early = s.SwingHighKnownAt(sw.FormedAtEt);
                Check(!early.Valid,
                      "querying at the pivot's own close returns NOTHING - the pivot was not knowable yet");
                HtfSwing justBefore = s.SwingHighKnownAt(sw.KnownAtEt.AddSeconds(-1));
                Check(!justBefore.Valid, "one second before confirmation the swing is still invisible");
                HtfSwing exactly = s.SwingHighKnownAt(sw.KnownAtEt);
                Check(exactly.Valid, "at the confirming close, and not before, the swing becomes usable");

                // overlapping-bar guard: an HTF bar closing at 09:15 must NOT be visible
                // to a 1m candle that opened at 09:14, because it contains that candle
                Check(double.IsNaN(s.LastBarHighKnownAt(t.AddMinutes(14))),
                      "a 3m bar closing at 09:15 is invisible to a candle that opened at 09:14 (it contains it)");
                Check(!double.IsNaN(s.LastBarHighKnownAt(t.AddMinutes(15))),
                      "the same 3m bar IS visible to a candle opening at 09:15, after it closed");

                // sweep classification
                Check(HigherTfStructure.ClassifyAgainstHigh(20060, 20040, 20050, 10) == HtfSweepEvent.SWEEP_CLOSE_BACK,
                      "trading through a 3m high and closing back under it is a SWEEP");
                Check(HigherTfStructure.ClassifyAgainstHigh(20060, 20055, 20050, 10) == HtfSweepEvent.BREAK_CLOSE_THROUGH,
                      "closing beyond the high is a BREAK, not a sweep");
                Check(HigherTfStructure.ClassifyAgainstHigh(20045, 20043, 20050, 10) == HtfSweepEvent.APPROACHED,
                      "coming within the band without trading through is APPROACHED");
                Check(HigherTfStructure.ClassifyAgainstHigh(20020, 20018, 20050, 10) == HtfSweepEvent.NONE,
                      "staying outside the band is NONE");
                Check(HigherTfStructure.ClassifyAgainstLow(19990, 20010, 20000, 10) == HtfSweepEvent.SWEEP_CLOSE_BACK,
                      "the mirror case below a 3m low is also a SWEEP");
                Check(HigherTfStructure.ClassifyAgainstHigh(20060, 20055, double.NaN, 10) == HtfSweepEvent.NONE,
                      "with no known level there is no event - never a guessed one");
            }

            // ---- placebo control: regular-candle sampling ----
            //
            // The quiet bars must have STRICTLY DECREASING volume*spread. Constant bars
            // all tie the 10-bar volume-spread maximum and every one of them classifies
            // as a VOLSPREAD_MAX vector - real Traders Reality behaviour, but it makes a
            // useless control fixture. This is the same trap the warm-up helper avoids.
            Action<VectorCandleResearchEngine> quiet = delegate(VectorCandleResearchEngine en)
            {
                for (int i = 0; i < 20; i++)
                    en.OnBar(RB(d.AddHours(10).AddMinutes(i), 20000, 20002, 19998, 20000, 99 - i));
            };
            {
                List<string> rowsOff = new List<string>();
                VectorCandleResearchEngine off = new VectorCandleResearchEngine(Levels(), rowsOff.Add);
                off.IncludeRegularCandles = false;
                WarmUp(off, d); quiet(off); off.Finish();
                Check(rowsOff.Count == 0,
                      "control OFF: not one regular candle is logged - this is exactly why the 2026 dataset "
                      + "has no placebo group (" + rowsOff.Count + " rows)");

                List<string> rowsAll = new List<string>();
                VectorCandleResearchEngine all = new VectorCandleResearchEngine(Levels(), rowsAll.Add);
                all.IncludeRegularCandles = true; all.RegularCandleSampleRate = 1;
                WarmUp(all, d); quiet(all); all.Finish();
                Check(rowsAll.Count >= 20, "control ON at 1-in-1: every regular candle is logged (" + rowsAll.Count + ")");

                List<string> rows5 = new List<string>();
                VectorCandleResearchEngine s5 = new VectorCandleResearchEngine(Levels(), rows5.Add);
                s5.IncludeRegularCandles = true; s5.RegularCandleSampleRate = 5;
                WarmUp(s5, d); quiet(s5); s5.Finish();
                Check(rows5.Count > 0, "1-in-5 sampling still produces a control group");
                Check(rows5.Count <= rowsAll.Count / 4,
                      "1-in-5 sampling really does thin the control group: " + rows5.Count + " vs " + rowsAll.Count);
                bool anyRegular = false;
                foreach (string r in rows5) if (r.Contains("REGULAR_")) anyRegular = true;
                Check(anyRegular, "the sampled rows really are REGULAR candles - a usable control group");
            }

            // ---- the new columns exist and stay aligned with the header ----
            {
                string[] h2 = VectorCandleResearchEngine.CsvHeader().Split(',');
                Check(Array.IndexOf(h2, "h3SwingHigh") >= 0, "CSV exposes h3SwingHigh");
                Check(Array.IndexOf(h2, "h15SwingLowEvent") >= 0, "CSV exposes h15SwingLowEvent");
                Check(Array.IndexOf(h2, "htfSweepSummary") >= 0, "CSV exposes the htfSweepSummary roll-up");

                List<string> rowsH = new List<string>();
                VectorCandleResearchEngine eh = new VectorCandleResearchEngine(Levels(), rowsH.Add);
                WarmUp(eh, d);
                eh.OnBar(RB(d.AddHours(9).AddMinutes(41), 20000, 20020, 19999, 20015, 300));
                eh.Finish();
                Check(rowsH.Count == 1, "an event is still emitted with the HTF columns added");
                Check(rowsH[0].Split(',').Length == h2.Length,
                      "row width still matches the header exactly: " + rowsH[0].Split(',').Length + " vs " + h2.Length);
                int hi = Array.IndexOf(h2, "htfSweepSummary");
                Check(rowsH[0].Split(',')[hi] == "NONE",
                      "with no HTF structure attached the sweep column is NONE, not a fabricated level");
            }

            Console.WriteLine();
            Console.WriteLine(string.Format("RESEARCH ENGINE: {0} passed, {1} failed", passed, failed));
            return failed;
        }
    }
}
