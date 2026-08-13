// ============================================================================
// Tests.cs — deterministic scenario tests required by the V5 correction prompt.
//
// Covers:
//   1. FB 1m/3m SHORT: BLUE_VECTOR above -> REGULAR reclaim below  = VALID
//   2. FB 1m/3m SHORT: BLUE_VECTOR above -> RED_VECTOR reclaim below = VALID
//   3. FB 1m/3m SHORT: BLUE_VECTOR above -> VIOLET reclaim = INVALID for BLUE path
//   4. FB parent trigger works WITHOUT prior-close-cross requirement (Fix 2)
//   5. VBR parent trigger works WITHOUT cross-through requirement (Fix 3)
//   6. Active VBR parent is NOT restarted by a later qualifying vector (Fix 5)
//   7. Premarket parent + first executable entry 9:30-9:45 grades A- (Fix 7)
//      (+ a later entry grades B+; premarket 1m patterns are never banked)
//   8. 18-level target sorting, tick normalization, exact-equal merging (Fix 8)
//   9. Traders Reality port diagnostics: Daily Open / YDay / LWeek / Psy (Fix 4)
//
// Run: mcs -out:run_tests.exe ../src/MnqTwoStrategiesShared.cs \
//        ../src/FakeBreakoutEngine.cs ../src/VectorBreakRetestEngine.cs \
//        MockHost.cs Tests.cs && mono run_tests.exe
// ============================================================================

using System;
using System.Collections.Generic;
using NinjaTrader.NinjaScript.Strategies.MnqTwo;

namespace MnqTwoTests
{
    public static class Tests
    {
        private static int passed;
        private static int failed;

        private static void Check(bool cond, string name)
        {
            if (cond) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        // ---- helpers -------------------------------------------------------

        private static BarSnap Bar(DateTime etOpen, int period, double o, double h, double l, double c,
                                   VectorType v, double ema)
        {
            BarSnap s = new BarSnap();
            s.EtOpen = etOpen;
            s.EtClose = etOpen.AddMinutes(period);
            s.Open = o; s.High = h; s.Low = l; s.Close = c;
            s.Volume = 1000;
            s.Vector = v;
            s.Ema9 = ema;
            s.PeriodMinutes = period;
            return s;
        }

        private static void Feed(KeyLevelEngine lv, DateTime etOpen, double o, double h, double l, double c)
        {
            // ET -> UTC during US DST (+4h); the seed dates are mid-week so they
            // never fall inside a psy session window
            lv.OnOneMinuteBar(etOpen, etOpen.AddMinutes(1), etOpen.AddHours(4), o, h, l, c);
        }

        // Feed a bar by its ET open, converting to UTC with a fixed +4h (EDT).
        private static void FeedEt(KeyLevelEngine lv, DateTime etOpen, double h, double l)
        {
            lv.OnOneMinuteBar(etOpen, etOpen.AddMinutes(1), etOpen.AddHours(4), (h + l) / 2, h, l, (h + l) / 2);
        }

        // Standard level book:
        //   LWEEK_HIGH 20500 / LWEEK_LOW 19500 (prev week)
        //   YDAY_HIGH 20100 / YDAY_LOW 19900, prev day close 20000
        //   DAILY_OPEN 20000 (open of the 18:00-ET exchange day containing Wed morning)
        private static KeyLevelEngine StdLevels()
        {
            KeyLevelEngine lv = new KeyLevelEngine();
            Feed(lv, new DateTime(2026, 7, 29, 12, 0, 0), 20000, 20500, 19500, 20000); // prev week
            Feed(lv, new DateTime(2026, 8, 3, 19, 0, 0), 20000, 20100, 19900, 20000);  // "yesterday" (Mon 19:00 ET)
            Feed(lv, new DateTime(2026, 8, 4, 19, 0, 0), 20000, 20010, 19990, 20000);  // today's exchange day opens Tue 18:00+ ET
            return lv;
        }

        private static readonly DateTime Wed = new DateTime(2026, 8, 5); // trading morning (same exchange day as Tue 19:00 bar)

        private static DateTime At(int h, int m) { return Wed.AddHours(h).AddMinutes(m); }

        // Drive a FakeBreakoutEngine into the frozen-short-searching state at
        // YDAY_HIGH = 20100. triggerCloseEt / reclaimCloseEt are 15m bar CLOSE times.
        private static FakeBreakoutEngine FbFrozenShort(MockHost host, DateTime triggerCloseEt, DateTime reclaimCloseEt,
                                                        double prev15Close)
        {
            host.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(host, new FbConfig());
            // 15m GREEN trigger: trades above 20100 and closes above it
            fb.OnFifteenMinuteBar(Bar(triggerCloseEt.AddMinutes(-15), 15, 20080, 20120, 20070, 20110,
                VectorType.GREEN_VECTOR, 20100), prev15Close);
            // 15m RED reclaim closes back below 20100 -> structure frozen;
            // its close 20095 < its EMA 20100 also satisfies short confluence (§7)
            fb.OnFifteenMinuteBar(Bar(reclaimCloseEt.AddMinutes(-15), 15, 20110, 20115, 20090, 20095,
                VectorType.RED_VECTOR, 20100), 20110);
            return fb;
        }

        private static void FbBluePath(FakeBreakoutEngine fb, VectorType reclaimVector)
        {
            // 1m BLUE_VECTOR closes above/through 20100 (V5 §10.B break candle)
            fb.OnOneMinuteBar(Bar(At(9, 31), 1, 20096, 20106, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            // subsequent 1m reclaim closes back below 20100, already below 1m EMA9
            fb.OnOneMinuteBar(Bar(At(9, 33), 1, 20104, 20105, 20092, 20095, reclaimVector, 20099));
        }

        // ---- 1/2/3: BLUE vector short paths ---------------------------------

        private static void TestBlueShortPaths()
        {
            Console.WriteLine("FB BLUE_VECTOR short paths (V5 Fix 1):");

            MockHost h1 = new MockHost();
            FakeBreakoutEngine f1 = FbFrozenShort(h1, At(9, 15), At(9, 30), 20090);
            FbBluePath(f1, VectorType.REGULAR_BEARISH);
            Check(h1.Entries.Count == 1 && h1.Entries[0].StartsWith("FB_SHORT"),
                "BLUE above -> REGULAR below = VALID short entry");
            // A- (26% of 10000 = 2600; stop 20106-20095 = 11 pts -> $22/contract -> 118)
            Check(h1.Entries.Count == 1 && h1.Entries[0] == "FB_SHORT 118",
                "BLUE->REGULAR sized at 26% A- risk (118 contracts)");
            Check(h1.AnyDiagContains("grade=A-"), "BLUE->REGULAR graded A-");

            MockHost h2 = new MockHost();
            FakeBreakoutEngine f2 = FbFrozenShort(h2, At(9, 15), At(9, 30), 20090);
            FbBluePath(f2, VectorType.RED_VECTOR);
            Check(h2.Entries.Count == 1 && h2.Entries[0].StartsWith("FB_SHORT"),
                "BLUE above -> RED_VECTOR below = VALID short entry");

            MockHost h3 = new MockHost();
            FakeBreakoutEngine f3 = FbFrozenShort(h3, At(9, 15), At(9, 30), 20090);
            FbBluePath(f3, VectorType.VIOLET_VECTOR);
            Check(h3.Entries.Count == 0, "BLUE above -> VIOLET below = NO entry (invalid for BLUE path)");
            Check(h3.AnyDiagContains("invalid"), "BLUE->VIOLET logged as invalid reclaim");
        }

        // ---- 4: FB trigger without prior-close-cross ------------------------

        private static void TestFbNoCross()
        {
            Console.WriteLine("FB parent trigger without prior-close-cross (V5 Fix 2):");
            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(h, new FbConfig());
            // previous 15m close was ALREADY ABOVE the level (20110 > 20100):
            // V4 build would have suppressed this trigger; V5 must accept it.
            fb.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20105, 20120, 20101, 20110,
                VectorType.GREEN_VECTOR, 20100), 20110);
            Check(h.AnyDiagContains("PARENT SETUP START"),
                "trigger accepted with prior 15m close already beyond the level");
        }

        // ---- 5/6: VBR trigger without cross; no restart ----------------------

        private static void TestVbrNoCrossAndNoRestart()
        {
            Console.WriteLine("VBR trigger without cross + no restart (V5 Fixes 3/5):");
            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels(); // DAILY_OPEN = 20000
            VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());

            // GREEN vector that never traded at/below Daily Open (low 20010 > 20000)
            // and whose prior 15m close was also above it — must still trigger.
            vbr.OnFifteenMinuteBar(Bar(At(8, 45), 15, 20040, 20060, 20010, 20050,
                VectorType.GREEN_VECTOR, 20030), 20040);
            Check(h.CountDiagContains("PARENT TRIGGER") == 1,
                "trigger accepted without any cross-through condition");

            // validity candle #1 is ANOTHER qualifying green vector — must NOT restart
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20050, 20080, 20030, 20070,
                VectorType.GREEN_VECTOR, 20040), 20050);
            Check(h.CountDiagContains("PARENT TRIGGER") == 1,
                "later qualifying vector did not restart/replace the active parent");

            // candles #2..#4 (regular) — expiry must come exactly 4 candles after
            // the ORIGINAL trigger (proves the original clock was preserved)
            vbr.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20070, 20075, 20060, 20065, VectorType.REGULAR_BEARISH, 20050), 20070);
            vbr.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20065, 20070, 20055, 20060, VectorType.REGULAR_BEARISH, 20055), 20065);
            Check(!h.AnyDiagContains("EXPIRED"), "not expired before candle #4 completes");
            vbr.OnFifteenMinuteBar(Bar(At(9, 45), 15, 20060, 20065, 20050, 20055, VectorType.REGULAR_BEARISH, 20058), 20060);
            Check(h.AnyDiagContains("EXPIRED"), "expired exactly after 4 candles from ORIGINAL trigger");
            Check(h.CountDiagContains("PARENT TRIGGER") == 1, "still only one parent trigger overall");
        }

        // ---- 7: premarket parent -> first executable candle grades A- -------

        private static void TestPremarketAMinusGrading()
        {
            Console.WriteLine("FB A- grading on first actually-eligible candle (V5 Fix 7):");
            MockHost h = new MockHost();
            // parent trigger completes 8:45 premarket; reclaim completes 9:00
            FakeBreakoutEngine fb = FbFrozenShort(h, At(8, 45), At(9, 0), 20090);
            // neutral 15m candles #2 (9:00-9:15) and #3 (9:15-9:30) complete premarket
            fb.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20095, 20096, 20094, 20095, VectorType.REGULAR_BEARISH, 20100), 20095);
            fb.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20095, 20096, 20094, 20095, VectorType.REGULAR_BEARISH, 20100), 20095);

            // premarket 1m fake-break pattern must NOT be banked (forms 9:20-9:22)
            fb.OnOneMinuteBar(Bar(At(9, 20), 1, 20096, 20106, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            fb.OnOneMinuteBar(Bar(At(9, 22), 1, 20104, 20105, 20092, 20095, VectorType.REGULAR_BEARISH, 20099));
            Check(h.Entries.Count == 0, "premarket 1m pattern ignored (never banked)");

            // fresh pattern during 9:30-9:45 = validity candle #4 = FIRST candle in
            // which an entry is actually eligible -> A- (26%), not B+
            FbBluePath(fb, VectorType.REGULAR_BEARISH);
            Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 118",
                "entry in 9:30-9:45 sized at A- 26% risk (118 contracts)");
            Check(h.AnyDiagContains("grade=A-"), "entry in first eligible candle graded A- not B+");
        }

        private static void TestLaterEntryGradesBPlus()
        {
            Console.WriteLine("FB later entry grades B+ (V5 Fix 7 counterpart):");
            MockHost h = new MockHost();
            FakeBreakoutEngine fb = FbFrozenShort(h, At(9, 15), At(9, 30), 20090);
            // neutral 1m during candle #2 marks it as the first eligible candle
            fb.OnOneMinuteBar(Bar(At(9, 31), 1, 20094, 20096, 20093, 20095, VectorType.REGULAR_BEARISH, 20100));
            // candle #2 completes without an entry
            fb.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20095, 20096, 20093, 20095, VectorType.REGULAR_BEARISH, 20100), 20095);
            // pattern during candle #3 -> second eligible candle -> B+ (10%)
            fb.OnOneMinuteBar(Bar(At(9, 46), 1, 20096, 20106, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            fb.OnOneMinuteBar(Bar(At(9, 48), 1, 20104, 20105, 20092, 20095, VectorType.REGULAR_BEARISH, 20099));
            Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 45",
                "later entry sized at B+ 10% risk (45 contracts)");
            Check(h.AnyDiagContains("grade=B+"), "later entry graded B+");
        }

        // ---- 8: 18-level sorting / tick normalization / exact merge ----------

        private static Func<double, double> Tick = delegate(double p) { return Math.Round(p / 0.25) * 0.25; };
        private static Func<TpLevelId, bool> AllOn = delegate(TpLevelId id) { return true; };

        private static void TestTargetSortingAndMerging()
        {
            Console.WriteLine("18-level sorting + equal-price merging (V5 Fix 8):");

            // Degenerate previous day H=L=C=100 -> every pivot/M level = 100.
            KeyLevelEngine lv = new KeyLevelEngine();
            Feed(lv, new DateTime(2026, 7, 29, 12, 0, 0), 100, 110, 80, 100);   // prev week H 110 / L 80
            Feed(lv, new DateTime(2026, 8, 3, 19, 0, 0), 100, 100, 100, 100);   // degenerate yesterday
            Feed(lv, new DateTime(2026, 8, 4, 19, 0, 0), 90, 90, 90, 90);       // today open 90

            List<TpTarget> up = lv.GetSortedTargets(TradeDirection.Long, 90.0, AllOn, Tick);
            Check(up.Count == 2, "degenerate day: 14 coincident levels collapse to 2 events above ref");
            Check(up.Count == 2 && up[0].Price == 100.0 && up[0].Names.Count == 13,
                "one event at 100.00 keeps all 13 names (M0-M5, PP, R1, R3, S1, S2, YDAY_H, YDAY_L)");
            Check(up.Count == 2 && up[1].Price == 110.0 && up[1].Names[0] == TpLevelId.LWEEK_HIGH,
                "second event is LWEEK_HIGH at 110.00");
            List<TpTarget> dn = lv.GetSortedTargets(TradeDirection.Short, 90.0, AllOn, Tick);
            Check(dn.Count == 1 && dn[0].Price == 80.0,
                "short side: DAILY_OPEN==ref excluded, only LWEEK_LOW 80.00 below");

            // Adjacent distinct ticks must NOT merge (no broad tolerance).
            KeyLevelEngine lv2 = new KeyLevelEngine();
            Feed(lv2, new DateTime(2026, 7, 29, 12, 0, 0), 100, 200, 50, 100);
            Feed(lv2, new DateTime(2026, 8, 3, 19, 0, 0), 100, 100.5, 99.5, 100); // PP=100 R1=100.5 M3=100.25 ...
            Feed(lv2, new DateTime(2026, 8, 4, 19, 0, 0), 95, 95, 95, 95);

            List<TpTarget> up2 = lv2.GetSortedTargets(TradeDirection.Long, 100.0, AllOn, Tick);
            Check(up2.Count >= 2 && up2[0].Price == 100.25 && up2[1].Price == 100.5,
                "adjacent ticks 100.25 (M3) and 100.50 (R1) stay separate events");
            Check(up2.Count >= 2 && up2[1].Names.Count == 2
                && up2[1].Names.Contains(TpLevelId.R1) && up2[1].Names.Contains(TpLevelId.YDAY_HIGH),
                "exactly-equal normalized prices (R1 = YDAY_HIGH = 100.50) merge with both names");
            bool r2Leaked = false;
            foreach (TpTarget t in up2) if (t.Price == 101.0) r2Leaked = true; // R2 = 101 internal only
            Check(!r2Leaked, "internal R2 (101.00) is not a selectable target event");
            for (int i = 1; i < up2.Count; i++)
                if (up2[i].Price <= up2[i - 1].Price) { Check(false, "ascending order"); return; }
            Check(true, "long targets strictly ascending");
        }

        // ---- 9: Traders Reality port diagnostics ------------------------------

        private static void TestTradersRealityPorts()
        {
            Console.WriteLine("Traders Reality ports: Daily Open / YDay / LWeek / Psy (V5 Fix 4):");

            KeyLevelEngine lv = StdLevels();
            // trading-morning bar on the same exchange day must not move Daily Open
            Feed(lv, new DateTime(2026, 8, 5, 9, 30, 0), 20050, 20060, 20040, 20055);
            Check(lv.DailyOpen == 20000.0,
                "getdayOpen port: Daily Open = open of first bar of the 18:00-ET exchange day, stable intraday");
            Check(lv.YdayHigh == 20100.0 && lv.YdayLow == 19900.0,
                "YDay Hi/Lo = previous completed exchange day (non-repainting)");
            Check(lv.LweekHigh == 20500.0 && lv.LweekLow == 19500.0,
                "LWeek Hi/Lo = previous completed week (non-repainting)");
            Check(lv.PP == 20000.0 && lv.R1 == 20100.0 && lv.S1 == 19900.0 && lv.R3 == 20300.0,
                "pivot formulas from previous day H/L/C");

            // ---- calcPsyLevels CRYPTO path (TR_MAIN L243: MNQ is 'futures' -> crypto) ----
            // Session = Sunday 22:00 -> Monday 06:00 GMT (Sydney DST off in August).
            // Realistic MNQ week: CME reopens Sunday 18:00 ET = Sunday 22:00 UTC.
            KeyLevelEngine psy = new KeyLevelEngine(); // defaults: Crypto + 4H grid
            FeedEt(psy, new DateTime(2026, 8, 1, 12, 0, 0), 99999, 1);      // Saturday: market shut in reality; must NOT count
            Check(double.IsNaN(psy.PsyHigh), "Saturday bar is NOT in the psy session (Pine day 1 = Sunday)");

            FeedEt(psy, new DateTime(2026, 8, 2, 18, 0, 0), 20010, 19990);  // Sun 18:00 ET = 22:00 UTC — session opens
            FeedEt(psy, new DateTime(2026, 8, 2, 23, 0, 0), 20050, 19980);  // Sun 23:00 ET = Mon 03:00 UTC — in session
            Check(psy.PsyHigh == 20050.0 && psy.PsyLow == 19980.0,
                "crypto path: hi/lo accumulate from the Sunday 22:00 GMT futures-week open");

            FeedEt(psy, new DateTime(2026, 8, 3, 9, 30, 0), 21000, 19000);  // Mon 09:30 ET = 13:30 UTC — out of session
            Check(psy.PsyHigh == 20050.0 && psy.PsyLow == 19980.0,
                "psy levels hold their last values outside the psy session");
            Check(!double.IsNaN(psy.PsyHigh),
                "crypto window is non-empty for MNQ (the Saturday reading would leave it NaN forever)");

            // ---- calcPsyLevels FOREX path: Monday 00:00-08:00 GMT ----
            KeyLevelEngine psyFx = new KeyLevelEngine();
            psyFx.PsyType = PsyLevelType.Forex;
            DateTime monUtc = new DateTime(2026, 8, 3, 0, 30, 0); // Monday 00:30 GMT
            psyFx.OnOneMinuteBar(monUtc.AddHours(-4), monUtc.AddHours(-4).AddMinutes(1), monUtc, 20000, 20010, 19990, 20005);
            psyFx.OnOneMinuteBar(monUtc.AddHours(-4).AddMinutes(30), monUtc.AddHours(-4).AddMinutes(31), monUtc.AddMinutes(30), 20005, 20050, 19980, 20040);
            Check(psyFx.PsyHigh == 20050.0 && psyFx.PsyLow == 19980.0,
                "forex path ('0000-0800:2' = Monday) still accumulates correctly");

            // The 4H-grid compatibility mode must agree with the literal window on
            // the aligned MNQ crypto case (grid start == session start == Sun 22:00 UTC)
            KeyLevelEngine psyGrid = new KeyLevelEngine();
            psyGrid.PsyUse4HourGrid = true;
            FeedEt(psyGrid, new DateTime(2026, 8, 2, 18, 0, 0), 20010, 19990);
            FeedEt(psyGrid, new DateTime(2026, 8, 2, 23, 0, 0), 20050, 19980);
            FeedEt(psyGrid, new DateTime(2026, 8, 3, 9, 30, 0), 21000, 19000);
            Check(psyGrid.PsyHigh == psy.PsyHigh && psyGrid.PsyLow == psy.PsyLow,
                "4H-grid compat mode agrees with the literal window on the aligned MNQ case");

            // calcDst port: Sydney DST flag (southern hemisphere)
            Check(KeyLevelEngine.CalcSydneyDst(new DateTime(2026, 1, 15)) == true, "calcDst: January -> Sydney DST on");
            Check(KeyLevelEngine.CalcSydneyDst(new DateTime(2026, 7, 1)) == false, "calcDst: July -> Sydney DST off");
            Check(KeyLevelEngine.CalcSydneyDst(new DateTime(2026, 12, 1)) == true, "calcDst: December -> Sydney DST on");

            // M-levels exactly as TR_MAIN lines 569-574
            Check(lv.M3 == (lv.PP + lv.R1) / 2 && lv.M0 == (lv.S2 + lv.S3) / 2 && lv.M5 == (lv.R2 + lv.R3) / 2,
                "M-level formulas match TR_MAIN m0C..m5C");

            // diagnostic comparison print (the values to check against TradingView)
            Console.WriteLine(string.Format(
                "  DIAG  DailyOpen={0:0.00} YdayHigh={1:0.00} YdayLow={2:0.00} LWeekHigh={3:0.00} LWeekLow={4:0.00} PP={5:0.00} R1={6:0.00} S1={7:0.00} R2(int)={8:0.00} S3(int)={9:0.00} M3={10:0.00} PsyHi={11:0.00} PsyLo={12:0.00}",
                lv.DailyOpen, lv.YdayHigh, lv.YdayLow, lv.LweekHigh, lv.LweekLow,
                lv.PP, lv.R1, lv.S1, lv.R2, lv.S3, lv.M3, psy.PsyHigh, psy.PsyLow));
        }

        // ---- main ------------------------------------------------------------

        public static int Main()
        {
            TestBlueShortPaths();
            TestFbNoCross();
            TestVbrNoCrossAndNoRestart();
            TestPremarketAMinusGrading();
            TestLaterEntryGradesBPlus();
            TestTargetSortingAndMerging();
            TestTradersRealityPorts();

            Console.WriteLine();
            Console.WriteLine(string.Format("RESULT: {0} passed, {1} failed", passed, failed));
            return failed == 0 ? 0 : 1;
        }
    }
}
