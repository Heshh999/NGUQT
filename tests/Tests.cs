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
        { Feed(lv, etOpen, o, h, l, c, 1000); }

        private static void Feed(KeyLevelEngine lv, DateTime etOpen, double o, double h, double l, double c, double vol)
        {
            // ET -> UTC during US DST (+4h); the seed dates are mid-week so they
            // never fall inside a psy session window
            lv.OnOneMinuteBar(etOpen, etOpen.AddMinutes(1), etOpen.AddHours(4), o, h, l, c, vol);
        }

        // Feed a bar by its ET open, converting to UTC with a fixed +4h (EDT).
        private static void FeedEt(KeyLevelEngine lv, DateTime etOpen, double h, double l)
        {
            lv.OnOneMinuteBar(etOpen, etOpen.AddMinutes(1), etOpen.AddHours(4), (h + l) / 2, h, l, (h + l) / 2, 1000);
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
            Check(h1.AnyDiagContains("GRADE=A-"), "BLUE->REGULAR graded A-");

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
            vbr.OnFifteenMinuteBar(Bar(At(8, 45), 15, 20040, 20140, 20010, 20050,
                VectorType.GREEN_VECTOR, 20030), 20040);
            Check(h.CountDiagContains("VBR PARENT CREATED") == 1,
                "trigger accepted without any cross-through condition");

            // validity candle #1 is ANOTHER qualifying green vector — must NOT restart
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20050, 20160, 20030, 20070,
                VectorType.GREEN_VECTOR, 20040), 20050);
            Check(h.CountDiagContains("VBR PARENT CREATED") == 1,
                "later qualifying vector did not restart/replace the active parent");

            // candles #2..#4 (regular) — expiry must come exactly 4 candles after
            // the ORIGINAL trigger (proves the original clock was preserved)
            vbr.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20070, 20075, 20060, 20065, VectorType.REGULAR_BEARISH, 20050), 20070);
            vbr.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20065, 20070, 20055, 20060, VectorType.REGULAR_BEARISH, 20055), 20065);
            Check(!h.AnyDiagContains("EXPIRED"), "not expired before candle #4 completes");
            vbr.OnFifteenMinuteBar(Bar(At(9, 45), 15, 20060, 20065, 20050, 20055, VectorType.REGULAR_BEARISH, 20058), 20060);
            Check(h.AnyDiagContains("EXPIRED"), "expired exactly after 4 candles from ORIGINAL trigger");
            Check(h.CountDiagContains("VBR PARENT CREATED") == 1, "still only one parent trigger overall");
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
            Check(h.AnyDiagContains("GRADE=A-"), "entry in first eligible candle graded A- not B+");
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
            // NOTE: the 9:15-9:30 candle that reclaims below YDAY_HIGH for the short
            // slot also satisfies the §5 LONG parent trigger at the same level, so an
            // independent FB long can also fire here. That is spec-correct; the old
            // 15m EMA confluence gate used to mask it. This assertion targets the
            // SHORT entry specifically.
            Check(h.Entries.Contains("FB_SHORT 45"),
                "later short entry sized at B+ 10% risk (45 contracts)");
            Check(h.AnyDiagContains("GRADE=B+"), "later entry graded B+");
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

            // ---- calcPsyLevels FOREX path — the configured default for MNQ ----
            // Session '0000-0800:2' GMT = Monday 00:00-08:00 GMT
            //   = Sunday 20:00 ET -> Monday 04:00 ET (EDT), fully inside CME hours.
            KeyLevelEngine psy = new KeyLevelEngine(); // default: Forex
            FeedEt(psy, new DateTime(2026, 8, 1, 12, 0, 0), 99999, 1);      // Saturday — must NOT count
            FeedEt(psy, new DateTime(2026, 8, 2, 18, 0, 0), 88888, 2);      // Sun 18:00 ET = 22:00 UTC Sun — before window
            Check(double.IsNaN(psy.PsyHigh),
                "forex path: Saturday and pre-window Sunday bars are outside the psy session");

            FeedEt(psy, new DateTime(2026, 8, 2, 20, 0, 0), 20010, 19990);  // Sun 20:00 ET = Mon 00:00 UTC — session opens
            FeedEt(psy, new DateTime(2026, 8, 2, 23, 0, 0), 20050, 19980);  // Sun 23:00 ET = Mon 03:00 UTC — in session
            Check(psy.PsyHigh == 20010.0 || psy.PsyHigh == 20050.0, "forex path: session initialized");
            Check(psy.PsyHigh == 20050.0 && psy.PsyLow == 19980.0,
                "forex path: hi/lo accumulate across Monday 00:00-08:00 GMT");

            FeedEt(psy, new DateTime(2026, 8, 3, 9, 30, 0), 21000, 19000);  // Mon 09:30 ET = 13:30 UTC — out of session
            Check(psy.PsyHigh == 20050.0 && psy.PsyLow == 19980.0,
                "psy levels hold their last values outside the psy session");
            Check(!double.IsNaN(psy.PsyHigh) && !double.IsNaN(psy.PsyLow),
                "forex window is fully populated for MNQ (inside CME hours year-round, no DST dependency)");

            // ---- calcPsyLevels CRYPTO path (available via the type parameter) ----
            // Session '2200-0600:1' = Sunday 22:00 -> Monday 06:00 GMT (Sydney DST off in August)
            KeyLevelEngine psyCr = new KeyLevelEngine();
            psyCr.PsyType = PsyLevelType.Crypto;
            FeedEt(psyCr, new DateTime(2026, 8, 1, 12, 0, 0), 99999, 1);     // Saturday
            Check(double.IsNaN(psyCr.PsyHigh), "crypto path: Saturday bar excluded (Pine day 1 = Sunday)");
            FeedEt(psyCr, new DateTime(2026, 8, 2, 18, 0, 0), 20010, 19990); // Sun 18:00 ET = 22:00 UTC — session opens
            FeedEt(psyCr, new DateTime(2026, 8, 2, 23, 0, 0), 20050, 19980); // Mon 03:00 UTC — in session
            FeedEt(psyCr, new DateTime(2026, 8, 3, 9, 30, 0), 21000, 19000); // out of session
            Check(psyCr.PsyHigh == 20050.0 && psyCr.PsyLow == 19980.0,
                "crypto path: hi/lo accumulate from the Sunday 22:00 GMT futures-week open");

            // The 4H-grid compatibility mode must agree with the literal window on
            // the aligned MNQ crypto case (grid start == session start == Sun 22:00 UTC)
            KeyLevelEngine psyGrid = new KeyLevelEngine();
            psyGrid.PsyType = PsyLevelType.Crypto;
            psyGrid.PsyUse4HourGrid = true;
            FeedEt(psyGrid, new DateTime(2026, 8, 2, 18, 0, 0), 20010, 19990);
            FeedEt(psyGrid, new DateTime(2026, 8, 2, 23, 0, 0), 20050, 19980);
            FeedEt(psyGrid, new DateTime(2026, 8, 3, 9, 30, 0), 21000, 19000);
            Check(psyGrid.PsyHigh == psyCr.PsyHigh && psyGrid.PsyLow == psyCr.PsyLow,
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

        // ======================================================================
        // V6 FINAL RULE LOCKS — U1..U9
        // ======================================================================

        // Drive an FB short to a filled position at YDAY_HIGH=20100, entry ~20095.
        // Returns the host; first target below entry is YDAY_LOW = 19900.
        private static MockHost FbShortInPosition(out FakeBreakoutEngine fb)
        {
            MockHost host = new MockHost();
            fb = FbFrozenShort(host, At(9, 15), At(9, 30), 20090);
            FbBluePath(fb, VectorType.REGULAR_BEARISH);
            // fill the entry
            fb.OnEntryExecution("FB_SHORT", 20095, 118, At(9, 34));
            return host;
        }

        // ---- U1: FB first target broken only by a completed 1m CLOSE ----------

        private static void TestU1FbTargetBreak()
        {
            Console.WriteLine("V6 U1 — FB first target break (completed 1m close, not a wick):");

            FakeBreakoutEngine fb;
            MockHost h = FbShortInPosition(out fb);
            // short from 20095: nearest directional 18-level target is M3 = (PP+R1)/2 = 20050
            Check(h.AnyDiagContains("first target M3 @ 20050"),
                "first target = nearest directional 18-level target (M3 @ 20050)");

            // wick THROUGH the target but close above it -> must NOT activate runner
            fb.OnOneMinuteBar(Bar(At(9, 40), 1, 20070, 20075, 20045, 20060, VectorType.REGULAR_BEARISH, 20080));
            Check(!h.AnyDiagContains("FIRST TARGET BROKEN"),
                "wick through the first target does NOT activate the runner (V6 U1)");
            // a 3m close beyond must ALSO not activate it (V6 U1 is a 1-MINUTE rule)
            fb.OnThreeMinuteBar(Bar(At(9, 42), 3, 20060, 20062, 20040, 20045, VectorType.REGULAR_BEARISH, 20080));
            Check(!h.AnyDiagContains("FIRST TARGET BROKEN"),
                "3m close beyond the target does NOT activate the runner under V6 U1");

            // completed 1m CLOSE below the target -> runner activates
            fb.OnOneMinuteBar(Bar(At(9, 45), 1, 20055, 20056, 20040, 20045, VectorType.REGULAR_BEARISH, 20070));
            Check(h.AnyDiagContains("FIRST TARGET BROKEN"),
                "completed 1m close beyond the first target activates the 3m EMA(9) runner");

            // runner exits on completed 3m close above 3m EMA9
            int exitsBefore = h.Exits.Count;
            fb.OnThreeMinuteBar(Bar(At(9, 48), 3, 20045, 20080, 20044, 20075, VectorType.GREEN_VECTOR, 20060));
            Check(h.Exits.Count == exitsBefore + 1 && h.Exits[h.Exits.Count - 1].StartsWith("FB_RUN_S"),
                "SHORT runner exits on a completed 3m close above the 3m EMA9");
        }

        // ---- U4 / U5: FB reclaim rules ----------------------------------------

        private static void TestU4U5FbReclaim()
        {
            Console.WriteLine("V6 U4/U5 — FB invalid reclaim keeps parent; LTF scan before reclaim:");

            // U5: parent trigger ONLY — no 15m candle has closed back below the level,
            // so no reclaim/freeze exists. A 1m BLUE->REGULAR short must still enter.
            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(h, new FbConfig());
            // 15m GREEN parent trigger closes 20110 ABOVE YDAY_HIGH 20100 (no reclaim);
            // close 20110 < 15m EMA 20130 satisfies the §7 short confluence.
            fb.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20080, 20120, 20070, 20110, VectorType.GREEN_VECTOR, 20130), 20090);
            Check(h.AnyDiagContains("PARENT SETUP START"), "15m short parent trigger created");
            Check(!h.AnyDiagContains("15m RECLAIM confirmed"),
                "no completed 15m reclaim has occurred (price never closed back below the level)");
            FbBluePath(fb, VectorType.REGULAR_BEARISH);
            Check(h.Entries.Count == 1 && h.Entries[0].StartsWith("FB_SHORT"),
                "U5: 1m/3m entry allowed BEFORE any completed 15m reclaim");

            // U4: an INVALID 15m reclaim must not cancel the parent
            MockHost h2 = new MockHost();
            h2.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb2 = new FakeBreakoutEngine(h2, new FbConfig());
            // REGULAR breakout above the level
            fb2.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20095, 20120, 20090, 20110, VectorType.REGULAR_BULLISH, 20100), 20090);
            Check(h2.AnyDiagContains("PARENT SETUP START"), "REGULAR 15m parent started");
            // REGULAR reclaim below the level = REGULAR+REGULAR = invalid
            fb2.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20110, 20112, 20090, 20095, VectorType.REGULAR_BEARISH, 20100), 20110);
            Check(h2.AnyDiagContains("reclaim IGNORED"), "invalid 15m reclaim is ignored");
            Check(!h2.AnyDiagContains("CANCELLED"), "U4: invalid 15m reclaim does NOT cancel the parent setup");
            // parent still alive -> a later valid LTF entry still works
            fb2.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20095, 20096, 20090, 20094, VectorType.REGULAR_BEARISH, 20100), 20095);
            FbBluePath(fb2, VectorType.RED_VECTOR);
            Check(h2.Entries.Count == 1, "parent survived the invalid reclaim and still produced an entry");
        }

        // ---- VBR helpers -------------------------------------------------------

        // Level book where the previous day is degenerate (H=L=C=20000) so every
        // pivot/M/YDay level collapses onto 20000. From a long entry at ~20005 the
        // ONLY directional target above is LWEEK_HIGH 20500 — comfortably >50 points
        // away, which is what activates the 1m EMA(9) trail (V6 U2).
        private static KeyLevelEngine FarTargetLevels()
        {
            KeyLevelEngine lv = new KeyLevelEngine();
            Feed(lv, new DateTime(2026, 7, 29, 12, 0, 0), 20000, 20500, 19500, 20000); // prev week
            Feed(lv, new DateTime(2026, 8, 3, 19, 0, 0), 20000, 20000, 20000, 20000);  // degenerate prev day
            Feed(lv, new DateTime(2026, 8, 4, 19, 0, 0), 20000, 20000, 20000, 20000);  // today: DAILY_OPEN 20000
            return lv;
        }

        // Parent long trigger at 9:15 (DAILY_OPEN = 20000), so validity candles are
        // #1 = 9:15-9:30, #2 = 9:30-9:45, #3 = 9:45-10:00, #4 = 10:00-10:15.
        private static VectorBreakRetestEngine VbrLongParent(MockHost host, VbrConfig cfg)
        {
            host.LevelsEngine = StdLevels();
            VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(host, cfg ?? new VbrConfig());
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20040, 20140, 20010, 20050, VectorType.GREEN_VECTOR, 20030), 20040);
            return vbr;
        }

        // ---- U6: Pattern B waits for EMA, needs BOTH DO and EMA ---------------

        private static void TestU6PatternBWait()
        {
            Console.WriteLine("V6 U6 — VBR Pattern B waits for EMA; entry needs BOTH DO and EMA9:");

            MockHost h = new MockHost();
            VectorBreakRetestEngine vbr = VbrLongParent(h, null);
            // 1. completed 1m close BELOW Daily Open (20000)
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            // 2. close back ABOVE Daily Open but BELOW EMA9 -> must WAIT, not discard
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20008, 19988, 20005, VectorType.REGULAR_BULLISH, 20010));
            Check(h.Entries.Count == 0, "reclaim above DO but below EMA9 does not enter");
            Check(h.AnyDiagContains("PATTERN_B_DO_RECLAIM") && h.AnyDiagContains("emaConfirmed=false"),
                "U6: structure is kept and the engine WAITS for the EMA");
            // 3. a candle above EMA9 but BELOW Daily Open is NOT a valid entry
            vbr.OnOneMinuteBar(Bar(At(9, 35), 1, 20005, 20006, 19990, 19995, VectorType.REGULAR_BEARISH, 19990));
            Check(h.Entries.Count == 0, "U6 step 7: above EMA9 but below Daily Open is NOT a long entry");
            // 4. later candle closing above BOTH -> ENTER
            vbr.OnOneMinuteBar(Bar(At(9, 37), 1, 19995, 20030, 19994, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h.Entries.Count == 1 && h.Entries[0].StartsWith("VBR_LONG"),
                "U6: entry on a later 1m close above BOTH Daily Open and 1m EMA9");
        }

        private static void TestU6PatternBWaitShort()
        {
            Console.WriteLine("V6 U6 — mirror short:");

            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels();
            VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());
            // short parent: 15m RED_VECTOR closes below DAILY_OPEN 20000
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 19960, 20070, 19940, 19950, VectorType.RED_VECTOR, 19970), 19960);
            // 1. completed 1m close ABOVE Daily Open
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 19995, 20015, 19994, 20010, VectorType.REGULAR_BULLISH, 19990));
            // 2. close back BELOW Daily Open but ABOVE EMA9 -> WAIT
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 20010, 20012, 19992, 19995, VectorType.REGULAR_BEARISH, 19990));
            Check(h.Entries.Count == 0 && h.AnyDiagContains("PATTERN_B_DO_RECLAIM") && h.AnyDiagContains("emaConfirmed=false"),
                "short: rejection below DO but above EMA9 waits");
            // 3. below EMA9 but ABOVE Daily Open is not valid
            vbr.OnOneMinuteBar(Bar(At(9, 35), 1, 19995, 20012, 19994, 20008, VectorType.REGULAR_BULLISH, 20015));
            Check(h.Entries.Count == 0, "short: below EMA9 but above Daily Open is NOT an entry");
            // 4. close below BOTH -> ENTER SHORT
            vbr.OnOneMinuteBar(Bar(At(9, 37), 1, 20005, 20006, 19970, 19975, VectorType.RED_VECTOR, 19990));
            Check(h.Entries.Count == 1 && h.Entries[0].StartsWith("VBR_SHORT"),
                "short: entry on a later 1m close below BOTH Daily Open and 1m EMA9");
        }

        // ---- U2 / U3 / U8: VBR profit management ------------------------------

        private static void TestU2U3U8ProfitManagement()
        {
            Console.WriteLine("V6 U2/U3/U8 — target reach by touch, 50-pt chain, 1m structure runner:");

            // Long VBR filled at 20005 with 20 contracts. Nearest levels above:
            // YDAY_HIGH 20100 (95 pts away -> >50 -> trail activates immediately).
            MockHost h = new MockHost();
            VectorBreakRetestEngine vbr = VbrLongParent(h, null);
            h.LevelsEngine = FarTargetLevels();   // nearest target above = LWEEK_HIGH 20500
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h.Entries.Count == 1, "VBR long entered");
            vbr.OnEntryExecution("VBR_LONG", 20005, 20, At(9, 33));
            Check(h.AnyDiagContains("TRAIL MODE (>50pts"),
                "U2: next target > 50 points away activates the 1m EMA(9) trail immediately");

            // trail: completed 1m close below EMA9 -> take 90% (18 of 20)
            vbr.OnOneMinuteBar(Bar(At(9, 40), 1, 20050, 20055, 20040, 20042, VectorType.REGULAR_BEARISH, 20048));
            Check(h.Exits.Count == 1 && h.Exits[0] == "VBR_TP90_L 18",
                "90% profit exit on a completed 1m close below EMA9 (18 of 20)");
            vbr.OnExitExecution("VBR_TP90_L", 20042, 18, At(9, 40));

            // U3: ONE completed 1m candle establishes the supporting higher low.
            // 9:41 low 20030; 9:42 low 20035 (higher low -> support = 20035).
            vbr.OnOneMinuteBar(Bar(At(9, 41), 1, 20042, 20045, 20030, 20040, VectorType.REGULAR_BEARISH, 20044));
            vbr.OnOneMinuteBar(Bar(At(9, 42), 1, 20040, 20048, 20035, 20046, VectorType.REGULAR_BULLISH, 20044));
            // a wick below 20035 that closes above it must NOT exit
            vbr.OnOneMinuteBar(Bar(At(9, 43), 1, 20046, 20047, 20020, 20040, VectorType.REGULAR_BEARISH, 20044));
            Check(h.Exits.Count == 1, "U3: wick below the 1m supporting structure does NOT exit the final 10%");
            // a later completed close BELOW 20035 exits the final 10%
            vbr.OnOneMinuteBar(Bar(At(9, 44), 1, 20040, 20041, 20020, 20025, VectorType.REGULAR_BEARISH, 20040));
            Check(h.Exits.Count == 2 && h.Exits[1] == "VBR_RUN_L 2",
                "U3: later completed 1m close through the one-candle structure exits the final 10%");
            Check(h.AnyDiagContains("(V6 U3)"), "runner exit is attributed to the V6 U3 structure rule");
        }

        private static void TestU2TargetChaining()
        {
            Console.WriteLine("V6 U2 — wick/touch reaches a target and advances the chain:");

            // Build levels so the first target above entry is ~25 pts away (<=50 -> hold).
            KeyLevelEngine lv = new KeyLevelEngine();
            Feed(lv, new DateTime(2026, 7, 29, 12, 0, 0), 20000, 20500, 19500, 20000);
            Feed(lv, new DateTime(2026, 8, 3, 19, 0, 0), 20000, 20030, 19970, 20000); // YDAY_HIGH 20030
            Feed(lv, new DateTime(2026, 8, 4, 19, 0, 0), 20000, 20010, 19990, 20000); // DAILY_OPEN 20000

            MockHost h = new MockHost();
            h.LevelsEngine = lv;
            VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20005, 20125, 19995, 20015, VectorType.GREEN_VECTOR, 20005), 20005);
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 20002, 20003, 19985, 19990, VectorType.REGULAR_BEARISH, 20008));
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20012, 19988, 20010, VectorType.GREEN_VECTOR, 20005));
            vbr.OnEntryExecution("VBR_LONG", 20005, 10, At(9, 33));
            Check(h.AnyDiagContains("HOLD for level (<=50pts"),
                "first target within 50 points -> HOLD and ignore adverse EMA closes");

            // adverse EMA close while the nearby target is active must NOT take profit
            vbr.OnOneMinuteBar(Bar(At(9, 35), 1, 20010, 20012, 20004, 20006, VectorType.REGULAR_BEARISH, 20009));
            Check(h.Exits.Count == 0, "U2: adverse 1m EMA close ignored while a <=50pt target is active");

            // WICK/TOUCH of the target (high 20030, close below it) -> reached, chain advances
            vbr.OnOneMinuteBar(Bar(At(9, 36), 1, 20006, 20030, 20005, 20020, VectorType.REGULAR_BULLISH, 20010));
            Check(h.AnyDiagContains("TARGET REACHED"),
                "U2: a wick/touch REACHES the target (no completed close required)");
        }

        private static void TestU8SingleContract()
        {
            Console.WriteLine("V6 U8 — 1-contract VBR position exits fully on the EMA signal:");

            MockHost h = new MockHost();
            VectorBreakRetestEngine vbr = VbrLongParent(h, null);
            h.LevelsEngine = FarTargetLevels();   // ensures the EMA trail can activate
            // stop 19985 vs entry close 20025 = 40 pts => $80/contract;
            // 50% of $200 = $100 => floor(100/80) = exactly 1 contract
            h.Balance = 200;
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h.Entries.Count == 1 && h.Entries[0] == "VBR_LONG 1", "sizing produced exactly 1 contract");
            vbr.OnEntryExecution("VBR_LONG", 20005, 1, At(9, 33));
            vbr.OnOneMinuteBar(Bar(At(9, 40), 1, 20050, 20055, 20040, 20042, VectorType.REGULAR_BEARISH, 20048));
            Check(h.Exits.Count == 1 && h.Exits[0] == "VBR_TP90_L 1",
                "U8: the EMA profit signal exits the ENTIRE 1-contract position");
            Check(h.AnyDiagContains("no runner (V6 U8)"), "U8: no runner is held for a 1-contract position");
        }

        // ---- U7: rolling re-entry re-qualification ----------------------------

        // Stop a VBR long out during validity candle #2 and return the engine.
        private static VectorBreakRetestEngine VbrStoppedInCandle2(MockHost host)
        {
            VectorBreakRetestEngine vbr = VbrLongParent(host, null);
            // candle #1 completes (9:15-9:30)
            vbr.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20050, 20060, 20040, 20055, VectorType.REGULAR_BULLISH, 20040), 20050);
            // enter during candle #2 (9:30-9:45)
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            vbr.OnEntryExecution("VBR_LONG", 20005, 10, At(9, 33));
            // stopped out inside candle #2
            vbr.OnExitExecution("VBR_STOP_L", 19985, 10, At(9, 36));
            return vbr;
        }

        private static void TestU7RollingReentry()
        {
            Console.WriteLine("V6 U7 — rolling re-entry re-qualification inside the ORIGINAL clock:");

            MockHost h = new MockHost();
            VectorBreakRetestEngine vbr = VbrStoppedInCandle2(h);
            Check(h.AnyDiagContains("STOPPED OUT during validity candle #2"), "stop-out recorded in candle #2");

            // candle #2 completes: wicks into DO and closes above it -> #3 may scan
            vbr.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20020, 20040, 19995, 20030, VectorType.REGULAR_BULLISH, 20010), 20020);
            Check(h.AnyDiagContains("candle #3"), "U7: qualifying candle #2 authorizes candle #3 to scan");

            // no entry during #3, but #3 closes on the correct side -> #4 may scan
            vbr.OnFifteenMinuteBar(Bar(At(9, 45), 15, 20030, 20045, 20025, 20040, VectorType.REGULAR_BULLISH, 20020), 20030);
            Check(h.AnyDiagContains("candle #4 may scan") || h.AnyDiagContains("candle #4"),
                "U7: correct-side close in #3 rolls the permission to candle #4");
            Check(!h.AnyDiagContains("setup finished"), "U7: rolling permission did not end the setup after one candle");

            // a fresh 1m pattern during #4 may still enter
            vbr.OnOneMinuteBar(Bar(At(10, 1), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(10, 3), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h.Entries.Count == 2, "U7: fresh 1m pattern in candle #4 produced the re-entry");

            // Separate run: roll all the way to #4, take NO entry there, and close #4
            // on the correct side. The ORIGINAL clock must still end the setup — the
            // rolling permission can never create a candle #5.
            MockHost h2 = new MockHost();
            VectorBreakRetestEngine vbr2 = VbrStoppedInCandle2(h2);
            vbr2.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20020, 20040, 19995, 20030, VectorType.REGULAR_BULLISH, 20010), 20020); // #2 qualifies -> #3
            vbr2.OnFifteenMinuteBar(Bar(At(9, 45), 15, 20030, 20045, 20025, 20040, VectorType.REGULAR_BULLISH, 20020), 20030); // #3 rolls -> #4
            vbr2.OnFifteenMinuteBar(Bar(At(10, 0), 15, 20040, 20050, 20030, 20045, VectorType.REGULAR_BULLISH, 20030), 20040); // #4 correct side, no entry
            Check(h2.AnyDiagContains("ORIGINAL 4-candle clock ended"),
                "U7: the ORIGINAL 4-candle clock never restarts or extends (no candle #5)");
            int before2 = h2.Entries.Count;
            vbr2.OnOneMinuteBar(Bar(At(10, 16), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr2.OnOneMinuteBar(Bar(At(10, 18), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h2.Entries.Count == before2, "U7: no entry is possible after the original clock ends");
        }

        private static void TestU7WrongSideBreaksRolling()
        {
            Console.WriteLine("V6 U7 — a wrong-side close breaks the rolling permission:");

            MockHost h = new MockHost();
            VectorBreakRetestEngine vbr = VbrStoppedInCandle2(h);
            // candle #2 qualifies -> #3 may scan
            vbr.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20020, 20040, 19995, 20030, VectorType.REGULAR_BULLISH, 20010), 20020);
            Check(h.AnyDiagContains("candle #3"), "candle #3 authorized");
            // #3 completes with NO entry and closes BELOW Daily Open (wrong side)
            vbr.OnFifteenMinuteBar(Bar(At(9, 45), 15, 20010, 20015, 19960, 19970, VectorType.REGULAR_BEARISH, 20000), 20010);
            Check(h.AnyDiagContains("VBR PARENT INVALIDATED reason=15M_CLOSE_WRONG_SIDE_DAILY_OPEN"),
                "a completed 15m close on the wrong side of Daily Open invalidates the parent outright"
                + " — this now takes precedence over the rolling re-entry permission");
            // and no further entry can occur
            int before = h.Entries.Count;
            vbr.OnOneMinuteBar(Bar(At(10, 1), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(10, 3), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h.Entries.Count == before, "no re-entry after the rolling permission is broken");
        }

        // ---- U9: strategy handoff ---------------------------------------------

        private static void TestU9HandoffFbToVbr()
        {
            Console.WriteLine("V6 U9 — FB open + valid VBR entry => flatten FB first:");

            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(h, new FbConfig());
            VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());
            h.Fb = fb; h.Vbr = vbr; h.WireHandoff();

            // FB short parent + entry, filled
            fb.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20080, 20120, 20070, 20110, VectorType.GREEN_VECTOR, 20130), 20090);
            fb.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20110, 20115, 20090, 20095, VectorType.RED_VECTOR, 20100), 20110);
            FbBluePath(fb, VectorType.REGULAR_BEARISH);
            Check(h.Entries.Count == 1 && h.Entries[0].StartsWith("FB_SHORT"), "FB entered first");
            fb.OnEntryExecution("FB_SHORT", 20095, 118, At(9, 34));

            // now a valid VBR long forms
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20040, 20140, 20010, 20050, VectorType.GREEN_VECTOR, 20030), 20040);
            vbr.OnOneMinuteBar(Bar(At(9, 36), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(9, 38), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));

            Check(h.AnyDiagContains("HANDOFF"), "U9: handoff initiated instead of blocking the VBR entry");
            Check(h.Exits.Count >= 1 && h.Exits[h.Exits.Count - 1].StartsWith("FB_HANDOFF"),
                "U9: FB position is flattened");
            Check(h.Entries.Count == 1,
                "U9: the VBR replacement order is NOT submitted before the flatten is confirmed");

            // flatten fills -> account flat -> replacement entry released
            fb.OnExitExecution("FB_HANDOFF_S", 20090, 118, At(9, 38));
            h.ConfirmFlat();
            Check(h.Entries.Count == 2 && h.Entries[1].StartsWith("VBR_LONG"),
                "U9: VBR entry submitted only after flat confirmation");

            int exitIdx = h.Sequence.FindIndex(delegate(string x) { return x.StartsWith("EXIT FB_HANDOFF"); });
            int flatIdx = h.Sequence.IndexOf("FLAT_CONFIRMED");
            int entIdx = h.Sequence.FindIndex(delegate(string x) { return x.StartsWith("ENTRY VBR_LONG"); });
            Check(exitIdx >= 0 && flatIdx > exitIdx && entIdx > flatIdx,
                "U9 ordering: FB exit -> flat confirmed -> VBR entry");
        }

        private static void TestU9HandoffVbrToFb()
        {
            Console.WriteLine("V6 U9 — VBR open + valid FB entry => flatten VBR first:");

            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(h, new FbConfig());
            VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());
            h.Fb = fb; h.Vbr = vbr; h.WireHandoff();

            // VBR long entered and filled
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20040, 20140, 20010, 20050, VectorType.GREEN_VECTOR, 20030), 20040);
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20006, 19985, 19990, VectorType.REGULAR_BEARISH, 20010));
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h.Entries.Count == 1 && h.Entries[0].StartsWith("VBR_LONG"), "VBR entered first");
            vbr.OnEntryExecution("VBR_LONG", 20005, 10, At(9, 33));

            // now a valid FB short forms
            fb.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20080, 20120, 20070, 20110, VectorType.GREEN_VECTOR, 20130), 20090);
            fb.OnFifteenMinuteBar(Bar(At(9, 30), 15, 20110, 20115, 20090, 20095, VectorType.RED_VECTOR, 20100), 20110);
            FbBluePath(fb, VectorType.REGULAR_BEARISH);

            Check(h.Exits.Count >= 1 && h.Exits[h.Exits.Count - 1].StartsWith("VBR_HANDOFF"),
                "U9: VBR position is flattened");
            Check(h.Entries.Count == 1,
                "U9: the FB replacement order is NOT submitted before the flatten is confirmed");

            vbr.OnExitExecution("VBR_HANDOFF_L", 20020, 10, At(9, 34));
            h.ConfirmFlat();
            Check(h.Entries.Count == 2 && h.Entries[1].StartsWith("FB_SHORT"),
                "U9: FB entry submitted only after flat confirmation");

            int exitIdx = h.Sequence.FindIndex(delegate(string x) { return x.StartsWith("EXIT VBR_HANDOFF"); });
            int flatIdx = h.Sequence.IndexOf("FLAT_CONFIRMED");
            int entIdx = h.Sequence.FindIndex(delegate(string x) { return x.StartsWith("ENTRY FB_SHORT"); });
            Check(exitIdx >= 0 && flatIdx > exitIdx && entIdx > flatIdx,
                "U9 ordering: VBR exit -> flat confirmed -> FB entry");
        }

        // ======================================================================
        // FINAL FAKE BREAKOUT EMA RULE
        // The 15m EMA(9) is informational only: it must never gate, cancel, delay
        // or invalidate a valid 1m/3m Fake Breakout entry. Only the SAME-TIMEFRAME
        // EMA(9) controls the entry.
        // ======================================================================

        // 15m SHORT parent at YDAY_HIGH 20100 whose 15m EMA is DELIBERATELY on the
        // wrong side: close 20110 > 15m EMA 20090, so the old confluence gate would
        // have blocked/cancelled every short entry underneath it.
        private static FakeBreakoutEngine FbShortParentBad15mEma(MockHost host)
        {
            host.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(host, new FbConfig());
            fb.OnFifteenMinuteBar(Bar(At(9, 15), 15, 20080, 20120, 20070, 20110,
                VectorType.GREEN_VECTOR, 20090), 20090);   // 20110 > 20090 => short confluence FAILS
            return fb;
        }

        // 15m LONG parent at YDAY_LOW 19900 whose 15m EMA is on the wrong side:
        // close 19890 < 15m EMA 19920, so long confluence FAILS.
        private static FakeBreakoutEngine FbLongParentBad15mEma(MockHost host)
        {
            host.LevelsEngine = StdLevels();
            FakeBreakoutEngine fb = new FakeBreakoutEngine(host, new FbConfig());
            fb.OnFifteenMinuteBar(Bar(At(9, 15), 15, 19910, 19915, 19880, 19890,
                VectorType.RED_VECTOR, 19920), 19910);     // 19890 < 19920 => long confluence FAILS
            return fb;
        }

        private static void TestFinalFbEmaRule()
        {
            Console.WriteLine("FINAL FB EMA RULE — 15m EMA(9) is context only, never an entry gate:");

            // 1m SHORT already below the 1m EMA9, 15m EMA on the wrong side
            MockHost h1 = new MockHost();
            FakeBreakoutEngine f1 = FbShortParentBad15mEma(h1);
            f1.OnOneMinuteBar(Bar(At(9, 31), 1, 20096, 20106, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            f1.OnOneMinuteBar(Bar(At(9, 33), 1, 20104, 20105, 20092, 20095, VectorType.REGULAR_BEARISH, 20099));
            Check(h1.Entries.Count == 1 && h1.Entries[0].StartsWith("FB_SHORT"),
                "1m short already below 1m EMA9 ENTERS while the 15m candle is not below the 15m EMA9");
            Check(h1.AnyDiagContains("15mConfluence=False"),
                "the failing 15m confluence is logged as context only, not as a block");

            // 3m SHORT already below the 3m EMA9, 15m EMA condition absent
            MockHost h2 = new MockHost();
            FakeBreakoutEngine f2 = FbShortParentBad15mEma(h2);
            f2.OnThreeMinuteBar(Bar(At(9, 33), 3, 20096, 20108, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            f2.OnThreeMinuteBar(Bar(At(9, 36), 3, 20104, 20106, 20090, 20094, VectorType.RED_VECTOR, 20099));
            Check(h2.Entries.Count == 1 && h2.Entries[0].StartsWith("FB_SHORT"),
                "3m short already below 3m EMA9 ENTERS with the 15m EMA condition absent");

            // 1m LONG already above the 1m EMA9, no 15m EMA confirmation
            MockHost h3 = new MockHost();
            FakeBreakoutEngine f3 = FbLongParentBad15mEma(h3);
            f3.OnOneMinuteBar(Bar(At(9, 31), 1, 19905, 19906, 19888, 19894, VectorType.RED_VECTOR, 19900));
            f3.OnOneMinuteBar(Bar(At(9, 33), 1, 19895, 19912, 19893, 19908, VectorType.GREEN_VECTOR, 19902));
            Check(h3.Entries.Count == 1 && h3.Entries[0].StartsWith("FB_LONG"),
                "1m long already above 1m EMA9 ENTERS without any 15m EMA confirmation");

            // 3m LONG already above the 3m EMA9, no 15m EMA confirmation
            MockHost h4 = new MockHost();
            FakeBreakoutEngine f4 = FbLongParentBad15mEma(h4);
            f4.OnThreeMinuteBar(Bar(At(9, 33), 3, 19905, 19907, 19886, 19893, VectorType.RED_VECTOR, 19900));
            f4.OnThreeMinuteBar(Bar(At(9, 36), 3, 19894, 19914, 19892, 19910, VectorType.GREEN_VECTOR, 19903));
            Check(h4.Entries.Count == 1 && h4.Entries[0].StartsWith("FB_LONG"),
                "3m long already above 3m EMA9 ENTERS without any 15m EMA confirmation");

            // Reclaim NOT yet through the same-timeframe EMA -> WAIT, do not cancel
            MockHost h5 = new MockHost();
            FakeBreakoutEngine f5 = FbShortParentBad15mEma(h5);
            f5.OnOneMinuteBar(Bar(At(9, 31), 1, 20096, 20106, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            // reclaim closes below the level (20095 < 20100) but ABOVE the 1m EMA9 (20090)
            f5.OnOneMinuteBar(Bar(At(9, 33), 1, 20104, 20105, 20092, 20095, VectorType.REGULAR_BEARISH, 20090));
            Check(h5.Entries.Count == 0, "reclaim not yet through the same-timeframe EMA9 does NOT enter");
            Check(!h5.AnyDiagContains("LTF setup cancelled") && !h5.AnyDiagContains("setup CANCELLED"),
                "reclaim awaiting the same-timeframe EMA WAITS instead of being cancelled");
            // later 1m close BELOW the 1m EMA9 (and inside the structure) -> ENTER
            f5.OnOneMinuteBar(Bar(At(9, 35), 1, 20095, 20098, 20080, 20085, VectorType.REGULAR_BEARISH, 20090));
            Check(h5.Entries.Count == 1 && h5.Entries[0].StartsWith("FB_SHORT"),
                "a later same-timeframe EMA close triggers the entry while the setup is still valid");

            // The 15m EMA state alone never cancels a valid LTF setup
            Check(!h1.AnyDiagContains("15m EMA confluence failed")
               && !h2.AnyDiagContains("15m EMA confluence failed")
               && !h3.AnyDiagContains("15m EMA confluence failed")
               && !h4.AnyDiagContains("15m EMA confluence failed")
               && !h5.AnyDiagContains("15m EMA confluence failed"),
                "15m EMA state alone NEVER cancels a valid lower-timeframe Fake Breakout setup");
        }

        // ======================================================================
        // Session VWAP + bands (TradingView built-in "VWAP", Anchor = Session)
        // ======================================================================

        private static void TestSessionVwap()
        {
            Console.WriteLine("Session VWAP + bands (TradingView built-in math):");

            KeyLevelEngine lv = new KeyLevelEngine();   // day starts 18:00 ET
            // two equal-volume bars at hlc3 = 100 and 200 inside one exchange day
            Feed(lv, new DateTime(2026, 8, 4, 19, 0, 0), 100, 100, 100, 100, 100);
            Check(lv.Vwap == 100.0, "VWAP of a single bar equals that bar's hlc3");

            Feed(lv, new DateTime(2026, 8, 4, 19, 1, 0), 200, 200, 200, 200, 100);
            // vwap = (100*100 + 200*100)/200 = 150
            // variance = (100*100^2 + 100*200^2)/200 - 150^2 = 25000 - 22500 = 2500 -> sd = 50
            Check(lv.Vwap == 150.0, "VWAP is volume-weighted across the session");
            Check(lv.VwapBandHigh == 200.0 && lv.VwapBandLow == 100.0,
                "bands = VWAP +/- 1.0 * volume-weighted stdev (TradingView Band 1 default)");

            // volume weighting must actually weight
            KeyLevelEngine lw = new KeyLevelEngine();
            Feed(lw, new DateTime(2026, 8, 4, 19, 0, 0), 100, 100, 100, 100, 300);
            Feed(lw, new DateTime(2026, 8, 4, 19, 1, 0), 200, 200, 200, 200, 100);
            Check(lw.Vwap == 125.0, "heavier volume pulls VWAP toward that bar (300/100 split -> 125)");

            // multiplier is honoured
            lw.VwapBandMultiplier = 2.0;
            double sd = lw.VwapBandHigh - lw.Vwap;
            lw.VwapBandMultiplier = 1.0;
            Check(Math.Abs(sd - 2.0 * (lw.VwapBandHigh - lw.Vwap)) < 1e-9,
                "band multiplier scales the band distance linearly");

            // re-anchors on the new exchange day
            Feed(lv, new DateTime(2026, 8, 5, 19, 0, 0), 500, 500, 500, 500, 50);
            Check(lv.Vwap == 500.0, "Session VWAP re-anchors at the 18:00 ET exchange-day open");

            // and it participates in the target engine
            List<TpTarget> ups = lv.GetSortedTargets(TradeDirection.Long, 499.0, AllOn, Tick);
            bool sawVwap = false;
            foreach (TpTarget t in ups) if (t.Names.Contains(TpLevelId.VWAP)) sawVwap = true;
            Check(sawVwap, "VWAP is selectable by the take-profit engine");
            Check(Enum.GetValues(typeof(TpLevelId)).Length == 21,
                "target universe is now 21 selectable levels (18 + VWAP + 2 bands)");
        }

        // ==================================================================
        // V7 — CROSS-MARKET CONFIRMATION GRADING (FAKE BREAKOUT ONLY)
        //
        // MNQ short setup throughout: parent at YDAY_HIGH = 20100, entry 20095,
        // structure stop 20106 -> 11 pts -> $22/contract on MNQ ($2/pt).
        //   30% of 10,000 = 3000 -> 136 contracts   (A+  = BOTH agree)
        //   10%           = 1000 ->  45 contracts   (A-  = exactly ONE agrees)
        //    5%           =  500 ->  22 contracts   (B+  = NEITHER agrees)
        // ES and QQQ trade at COMPLETELY different prices (5600 / 480) on
        // purpose: if any code path ever compared MNQ prices to theirs, every
        // one of these tests would fail.
        // ==================================================================

        private static void SetupEsLevels(MockHost h)
        {
            // ES is CME — same 18:00 ET exchange day as MNQ (engine defaults).
            Feed(h.EsLevels, new DateTime(2026, 7, 29, 12, 0, 0), 5500, 5700, 5400, 5500); // prev week
            Feed(h.EsLevels, new DateTime(2026, 8, 3, 19, 0, 0), 5590, 5600, 5580, 5590);  // "yesterday"
            Feed(h.EsLevels, new DateTime(2026, 8, 4, 19, 0, 0), 5590, 5592, 5588, 5590);  // today
        }

        private static void SetupQqqLevels(MockHost h)
        {
            // QQQ is an ETF: RTH cash session only (09:30-16:00 ET), calendar day roll.
            h.YmLevels.DayStartMinutesEt = 0;
            h.YmLevels.WeekStartMinutesEt = 0;
            h.YmLevels.SessionFilterEnabled = true;
            h.YmLevels.SessionFilterStartMinutesEt = 570;
            h.YmLevels.SessionFilterEndMinutesEt = 960;
            Feed(h.YmLevels, new DateTime(2026, 8, 4, 10, 0, 0), 479, 480, 478, 479);     // Tue RTH
            Feed(h.YmLevels, new DateTime(2026, 8, 5, 8, 0, 0), 500, 505, 495, 500);      // Wed PREMARKET (must be ignored)
            Feed(h.YmLevels, new DateTime(2026, 8, 5, 9, 30, 0), 479, 479.5, 478.5, 479); // Wed RTH -> rolls the day
        }

        // ES bearish fake-break + reclaim at ES's OWN YDAY_HIGH (5600).
        private static void EsConfirmShort(MockHost h, int tf)
        {
            CrossMarketConfirmDetector d = tf == 1 ? h.EsDet1 : h.EsDet3;
            DateTime b0 = tf == 1 ? At(9, 31) : At(9, 30);
            DateTime b1 = tf == 1 ? At(9, 33) : At(9, 33);
            d.OnBar(Bar(b0, tf, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
            d.OnBar(Bar(b1, tf, 5604, 5605, 5593, 5595, VectorType.REGULAR_BEARISH, 5599));
        }

        // QQQ bearish fake-break + reclaim at QQQ's OWN YDAY_HIGH (480).
        private static void QqqConfirmShort(MockHost h, int tf)
        {
            CrossMarketConfirmDetector d = tf == 1 ? h.YmDet1 : h.YmDet3;
            DateTime b0 = tf == 1 ? At(9, 31) : At(9, 30);
            DateTime b1 = tf == 1 ? At(9, 33) : At(9, 33);
            d.OnBar(Bar(b0, tf, 479.5, 481.5, 479.4, 481, VectorType.BLUE_VECTOR, 480));
            d.OnBar(Bar(b1, tf, 480.8, 481, 478.5, 479, VectorType.REGULAR_BEARISH, 479.8));
        }

        // MNQ 3m fake-break + reclaim (entry decision bar closes 09:36).
        private static void FbBluePath3m(FakeBreakoutEngine fb)
        {
            fb.OnThreeMinuteBar(Bar(At(9, 30), 3, 20096, 20106, 20094, 20105, VectorType.BLUE_VECTOR, 20100));
            fb.OnThreeMinuteBar(Bar(At(9, 33), 3, 20104, 20105, 20092, 20095, VectorType.REGULAR_BEARISH, 20099));
        }

        // Feed one PREMARKET bar to every detector. Bars before 09:30 can never start
        // a fake-break structure (the session gate), so this changes no signal — it
        // only establishes that the market was actually being watched. Without it a
        // silent market reads as UNKNOWN rather than "evaluated, did not confirm",
        // which is precisely the V7.1 distinction.
        private static void CmWarmup(MockHost h)
        {
            h.EsDet1.OnBar(Bar(At(9, 20), 1, 5590, 5592, 5588, 5590, VectorType.REGULAR_BULLISH, 5590));
            h.EsDet3.OnBar(Bar(At(9, 18), 3, 5590, 5592, 5588, 5590, VectorType.REGULAR_BULLISH, 5590));
            h.YmDet1.OnBar(Bar(At(9, 20), 1, 479, 479.2, 478.8, 479, VectorType.REGULAR_BULLISH, 479));
            h.YmDet3.OnBar(Bar(At(9, 18), 3, 479, 479.2, 478.8, 479, VectorType.REGULAR_BULLISH, 479));
        }

        private static MockHost CmHost(out FakeBreakoutEngine fb)
        {
            MockHost h = new MockHost();
            h.WireCrossMarket(4);          // user-specified 4-bar reclaim window
            SetupEsLevels(h);
            SetupQqqLevels(h);
            CmWarmup(h);
            fb = FbFrozenShort(h, At(9, 15), At(9, 30), 20090);
            return h;
        }

        private static void TestCrossMarketGrading()
        {
            Console.WriteLine("V7 — cross-market confirmation grading (FAKE BREAKOUT only):");

            // ---- sanity: each market uses its OWN level, at its own price ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h); SetupQqqLevels(h); CmWarmup(h);
                Check(Math.Abs(h.EsLevels.YdayHigh - 5600) < 1e-9,
                    "ES uses its OWN YDAY_HIGH (5600), not MNQ's");
                Check(Math.Abs(h.YmLevels.YdayHigh - 480) < 1e-9,
                    "QQQ uses its OWN YDAY_HIGH (480) from the RTH session — the 505 premarket high is excluded");
            }

            // ---- TEST 1: MNQ 1m + ES 1m + YM 1m -> A+ / 30% ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 1);
                QqqConfirmShort(h, 1);
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                Check(h.AnyDiagContains("GRADE=A+ riskPct=30"), "TEST 1: MNQ 1m + ES 1m + YM 1m -> A+ @ 30%");
                Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 136", "TEST 1: A+ sized at 30% (136 contracts)");
                Check(h.AnyDiagContains("ES_confirm=True") && h.AnyDiagContains("YM_confirm=True"),
                    "TEST 1: both confirmations logged true");
            }

            // ---- TEST 2: MNQ 1m + ES 1m only -> A- / 10% ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 1);
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                Check(h.AnyDiagContains("GRADE=A- riskPct=10"), "TEST 2: MNQ 1m + ES 1m only -> A- @ 10%");
                Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 45", "TEST 2: A- sized at 10% (45 contracts)");
            }

            // ---- TEST 3: MNQ 1m + YM 1m only -> B+ / 5% ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                QqqConfirmShort(h, 1);
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                Check(h.AnyDiagContains("GRADE=A- riskPct=10"),
                    "TEST 3: MNQ 1m + market-2 1m only -> A- @ 10% (either single confirmation is A-)");
                Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 45", "TEST 3: A- sized at 10% (45 contracts)");
            }

            // ---- TEST 4: MNQ 3m + ES 3m + YM 3m -> A+ / 30% ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 3);
                QqqConfirmShort(h, 3);
                FbBluePath3m(fb);
                Check(h.AnyDiagContains("GRADE=A+ riskPct=30"), "TEST 4: MNQ 3m + ES 3m + YM 3m -> A+ @ 30%");
                Check(h.AnyDiagContains("entryTf=3m"), "TEST 4: graded on the 3m entry timeframe");
                Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 136", "TEST 4: A+ sized at 30% (136 contracts)");
            }

            // ---- TEST 5: MNQ 1m + ES 1m + YM 3m -> QQQ must NOT count ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 1);
                QqqConfirmShort(h, 3);     // 3m confirmation only
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                Check(h.AnyDiagContains("YM_confirm=False"), "TEST 5: a YM 3m confirmation does NOT count for a 1m MNQ signal");
                Check(h.AnyDiagContains("GRADE=A- riskPct=10"), "TEST 5: grade is A- (ES only), not A+");
            }

            // ---- TEST 6: MNQ 3m + ES 1m + YM 3m -> ES must NOT count ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 1);      // 1m confirmation only
                QqqConfirmShort(h, 3);
                FbBluePath3m(fb);
                Check(h.AnyDiagContains("ES_confirm=False"), "TEST 6: an ES 1m confirmation does NOT count for a 3m MNQ signal");
                Check(h.AnyDiagContains("GRADE=A- riskPct=10"), "TEST 6: grade is A- (market 2 only), not A+");
            }

            // ---- TEST 7: ES/QQQ 15m is irrelevant ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 1);
                QqqConfirmShort(h, 1);
                CrossMarketConfirm es15 = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 15, At(9, 34));
                CrossMarketConfirm qq15 = h.QueryCrossMarket(ConfirmMarket.YM, false, KeyLevelId.YDAY_HIGH, 15, At(9, 34));
                Check(!es15.Confirmed && !qq15.Confirmed, "TEST 7: no 15m ES/QQQ confirmation channel exists at all");
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                Check(h.AnyDiagContains("GRADE=A+ riskPct=30"),
                    "TEST 7: the grade is decided purely by the 1m confirmations — 15m cannot affect it");
            }

            // ---- TEST 11: no lookahead ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h);
                // ES confirms on the 09:36 bar, AFTER a 09:34 MNQ decision
                h.EsDet1.OnBar(Bar(At(9, 33), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
                h.EsDet1.OnBar(Bar(At(9, 35), 1, 5604, 5605, 5593, 5595, VectorType.REGULAR_BEARISH, 5599));
                CrossMarketConfirm early = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 34));
                Check(!early.Confirmed, "TEST 11: a confirmation from a LATER bar is never visible to an earlier MNQ decision");
                Check(early.Reason.Contains("no lookahead"), "TEST 11: the rejection is logged explicitly as a lookahead guard");
                CrossMarketConfirm onTime = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 36));
                Check(onTime.Confirmed, "TEST 11: the same confirmation IS visible on its own bar");
            }

            // ---- TEST 12: undefined case is explicit, never invented ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                // neither market confirms
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                Check(h.AnyDiagContains("ES_confirm=False") && h.AnyDiagContains("YM_confirm=False"),
                    "TEST 12: the no-confirmation case is logged explicitly");
                Check(!h.AnyDiagContains("GRADE=A- "), "TEST 12: zero agreement is never promoted to A-");
                Check(h.AnyDiagContains("GRADE=B+ riskPct=5"),
                    "TEST 12: MNQ alone with NEITHER market agreeing resolves to B+ @ 5%");
                Check(!h.AnyDiagContains("GRADE=A- riskPct=26"),
                    "TEST 12: the legacy 26% A- grade can never leak into cross-market mode");
                Check(h.Entries.Count == 1 && h.Entries[0] == "FB_SHORT 22", "TEST 12: sized at 5% (22 contracts)");
            }

            // ---- the reclaim window is bounded (user-specified 4 bars) ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h);
                h.EsDet1.OnBar(Bar(At(9, 31), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
                for (int i = 32; i <= 36; i++)   // 5 bars beyond the level = window expires
                    h.EsDet1.OnBar(Bar(At(9, i), 1, 5604, 5607, 5602, 5605, VectorType.REGULAR_BULLISH, 5600));
                h.EsDet1.OnBar(Bar(At(9, 37), 1, 5604, 5605, 5593, 5595, VectorType.REGULAR_BEARISH, 5599));
                CrossMarketConfirm late = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 38));
                Check(!late.Confirmed, "a reclaim later than 4 bars after the break does NOT confirm");
            }

            // ---- TEST 10: ES/QQQ never place an order ----
            {
                FakeBreakoutEngine fb;
                MockHost h = CmHost(out fb);
                EsConfirmShort(h, 1); EsConfirmShort(h, 3);
                QqqConfirmShort(h, 1); QqqConfirmShort(h, 3);
                Check(h.Entries.Count == 0 && h.Exits.Count == 0 && h.Stops.Count == 0,
                    "TEST 10: feeding ES/QQQ bars alone submits no order of any kind");
                FbBluePath(fb, VectorType.REGULAR_BEARISH);
                bool allMnq = h.OrderInstruments.Count > 0;
                foreach (string s in h.OrderInstruments) if (!s.StartsWith("MNQ:")) allMnq = false;
                Check(allMnq, "TEST 10: every order that IS placed is routed to MNQ");
                foreach (string sig in h.Entries)
                    Check(sig.StartsWith("FB_"), "TEST 10: entry signal carries the FB_ tag (" + sig + ")");
            }

            // ---- entry qualification is UNCHANGED by cross-market grading ----
            {
                FakeBreakoutEngine fbA, fbB;
                MockHost a = CmHost(out fbA);                 // no confirmations
                FbBluePath(fbA, VectorType.REGULAR_BEARISH);
                MockHost b = CmHost(out fbB);
                EsConfirmShort(b, 1); QqqConfirmShort(b, 1);  // full confirmation
                FbBluePath(fbB, VectorType.REGULAR_BEARISH);
                Check(a.Entries.Count == 1 && b.Entries.Count == 1,
                    "cross-market state changes the SIZE but never whether the trade is taken");

                // and an invalid MNQ reclaim is still rejected even with full confirmation
                FakeBreakoutEngine fbC;
                MockHost c = CmHost(out fbC);
                EsConfirmShort(c, 1); QqqConfirmShort(c, 1);
                FbBluePath(fbC, VectorType.VIOLET_VECTOR);   // invalid on the BLUE path
                Check(c.Entries.Count == 0,
                    "a full ES+QQQ confirmation can NEVER rescue an invalid MNQ setup");
            }
        }

        // ==================================================================
        // V7.1 — "UNKNOWN is not NO"
        // Regression tests for the defect that silently graded 59 live backtest
        // trades off ES/QQQ levels that were permanently NaN.
        // ==================================================================
        private static void TestUnknownIsNotNo()
        {
            Console.WriteLine("V7.1 — a market that cannot be evaluated is never graded as \"did not confirm\":");

            // ---- A. detector fed ZERO bars ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h); SetupQqqLevels(h);      // levels fine, but no bars fed
                CrossMarketConfirm c = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 34));
                Check(!c.Confirmed && c.Unavailable, "zero bars -> Unavailable (UNKNOWN), not a negative answer");
                Check(c.Reason.Contains("ZERO bars"), "the reason names the zero-bar cause");
            }

            // ---- B. bars flowing but the market's own levels are NaN ----
            // This is the EXACT production failure: series attached, bars arriving,
            // but no history to build YDAY_HIGH from, so every level reads NaN.
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                // deliberately do NOT seed EsLevels -> all eligible levels are NaN
                h.EsDet1.OnBar(Bar(At(9, 31), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
                h.EsDet1.OnBar(Bar(At(9, 33), 1, 5604, 5605, 5593, 5595, VectorType.REGULAR_BEARISH, 5599));
                Check(h.EsDet1.BarsSeen == 2, "detector counted the bars it received");
                Check(h.EsDet1.DayBarsNoLevels == 2, "both bars are recorded as having NO usable level");
                Check(!h.EsDet1.HasEverHadLevels, "detector reports it has never had a usable level");
                CrossMarketConfirm c = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 34));
                Check(!c.Confirmed && c.Unavailable, "NaN level -> Unavailable (UNKNOWN), not 'did not confirm'");
                Check(c.Reason.Contains("UNKNOWN"), "the reason says UNKNOWN explicitly");
            }

            // ---- C. FB refuses the cross-market grade when either side is unknown ----
            {
                FakeBreakoutEngine fb;
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h);           // ES fine
                                            // QQQ deliberately unseeded -> NaN levels
                h.YmDet1.OnBar(Bar(At(9, 31), 1, 479.5, 481.5, 479.4, 481, VectorType.BLUE_VECTOR, 480));
                EsConfirmShort(h, 1);
                fb = FbFrozenShort(h, At(9, 15), At(9, 30), 20090);
                FbBluePath(fb, VectorType.REGULAR_BEARISH);

                Check(h.AnyDiagContains("CROSS-MARKET GRADING UNAVAILABLE"),
                    "FB refuses to grade when a confirmation market could not be evaluated");
                Check(!h.AnyDiagContains("GRADE=B+ riskPct=5"),
                    "the 'neither confirms' grade is NEVER produced from unevaluated data");
                Check(h.Entries.Count == 0,
                    "the entry is BLOCKED — no legacy fallback, so a legacy grade can never masquerade as a new one");
                Check(!h.AnyDiagContains("using LEGACY validity-candle grade"),
                    "the legacy validity-candle grading path is never entered");
            }

            // ---- D. a REAL negative is still a real negative ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h);
                // ES has levels and bars, but simply never breaks/reclaims
                for (int i = 31; i <= 36; i++)
                    h.EsDet1.OnBar(Bar(At(9, i), 1, 5590, 5592, 5588, 5590, VectorType.REGULAR_BULLISH, 5591));
                CrossMarketConfirm c = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 37));
                Check(!c.Confirmed && !c.Unavailable, "evaluated-and-declined stays a genuine NO, not UNKNOWN");
                Check(c.Reason.Contains("evaluated, did not occur"), "the reason distinguishes it from UNKNOWN");
                Check(h.EsDet1.HasEverHadLevels && h.EsDet1.DayBarsNoLevels == 0, "levels were usable throughout");
            }

            // ---- E. near-miss counters separate the failure modes ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h);
                // break, then reclaim with an INVALID vector for the BLUE path
                h.EsDet1.OnBar(Bar(At(9, 31), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
                h.EsDet1.OnBar(Bar(At(9, 33), 1, 5604, 5605, 5593, 5595, VectorType.VIOLET_VECTOR, 5599));
                // NOTE: one bar can break several of the 4 eligible levels at once
                // (a close at 5605 is beyond YDAY_HIGH 5600, YDAY_LOW 5580 and
                // LWEEK_LOW 5400), so these are counts of EVENTS, not of trades.
                Check(h.EsDet1.DayBreaks >= 1, "a started fake-break is counted");
                Check(h.EsDet1.DayReclaimRejectedVector >= 1, "a reclaim rejected on vector rules is counted separately");
                Check(h.EsDet1.DayWindowExpired == 0, "a vector rejection is NOT miscounted as a window expiry");
                Check(h.EsDet1.DayConfirms == 0, "no confirmation recorded");
                string tally = h.EsDet1.DailyTally();
                Check(tally.Contains("reclaimRejected=1") && tally.Contains("CONFIRMS=0"),
                    "the daily tally separates the near-miss reasons: " + tally);
                Check(h.EsDet1.DayBreaks == 0, "tally resets the daily counters");
            }

            // ---- F. window expiry is counted and distinguishable ----
            {
                MockHost h = new MockHost();
                h.WireCrossMarket(4);
                SetupEsLevels(h);
                h.EsDet1.OnBar(Bar(At(9, 31), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
                for (int i = 32; i <= 37; i++)
                    h.EsDet1.OnBar(Bar(At(9, i), 1, 5604, 5607, 5602, 5605, VectorType.REGULAR_BULLISH, 5600));
                Check(h.EsDet1.DayWindowExpired >= 1, "an expired reclaim window is counted");
                Check(h.EsDet1.DayReclaimRejectedVector == 0, "an expiry is NOT miscounted as a vector rejection");
                Check(h.EsDet1.DayConfirms == 0, "an expired window produces no confirmation");
            }
        }

        // ---- confirmation market 2 as a CME FUTURES contract (YM) -------------
        private static void TestFuturesConfirmMarket2()
        {
            Console.WriteLine("V7.2 — confirmation market 2 as CME futures (YM) instead of an ETF:");

            // YM is CME: same 18:00 ET exchange day as MNQ/ES, no RTH filter.
            MockHost h = new MockHost();
            h.WireCrossMarket(4);
            h.YmLevels.DayStartMinutesEt = 1080;    // 18:00 ET, as the host now configures it
            h.YmLevels.WeekStartMinutesEt = 1080;
            h.YmLevels.SessionFilterEnabled = false;
            h.YmDet1.Label = "YM ##-##"; h.YmDet3.Label = "YM ##-##";

            // "yesterday" is the CME exchange day that OPENED Mon 18:00 ET
            Feed(h.YmLevels, new DateTime(2026, 8, 3, 19, 0, 0), 45000, 45120, 44900, 45000);
            // an overnight bar must COUNT for a futures market (it would be discarded under RTH)
            Feed(h.YmLevels, new DateTime(2026, 8, 4, 2, 0, 0), 45050, 45200, 45040, 45060);
            Feed(h.YmLevels, new DateTime(2026, 8, 4, 19, 0, 0), 45100, 45110, 45090, 45100);

            Check(Math.Abs(h.YmLevels.YdayHigh - 45200) < 1e-9,
                "futures market 2 includes the overnight session in YDAY_HIGH (45200, not the 45120 day-session high)");
            Check(!double.IsNaN(h.YmLevels.YdayLow), "futures market 2 computes YDAY_LOW");

            // it confirms on its OWN level at its own price scale
            h.YmDet1.OnBar(Bar(At(9, 31), 1, 45190, 45260, 45185, 45250, VectorType.BLUE_VECTOR, 45200));
            h.YmDet1.OnBar(Bar(At(9, 33), 1, 45240, 45245, 45150, 45170, VectorType.REGULAR_BEARISH, 45195));
            CrossMarketConfirm c = h.QueryCrossMarket(ConfirmMarket.YM, false, KeyLevelId.YDAY_HIGH, 1, At(9, 34));
            Check(c.Confirmed, "YM confirms a bearish fake-break at its OWN YDAY_HIGH (45200)");
            Check(Math.Abs(c.LevelPrice - 45200) < 1e-9, "the confirmation is anchored to YM's own level price");
            Check(c.Reason.Contains("YM ##-##"),
                "logs report the ACTUAL configured symbol, never a stale 'QQQ' label: " + c.Reason);
        }

        // ---- confirmation markets ignore their own EMA(9) ---------------------
        private static void TestConfirmMarketsIgnoreEma()
        {
            Console.WriteLine("V7.3 — ES / market 2 confirm on break+reclaim ALONE (their EMA9 does not matter):");

            // reclaim closes back below the level but is still ABOVE its own EMA9,
            // which under the old rule would have blocked/delayed the confirmation.
            MockHost h = new MockHost();
            h.WireCrossMarket(4);
            SetupEsLevels(h);
            h.EsDet1.OnBar(Bar(At(9, 31), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
            h.EsDet1.OnBar(Bar(At(9, 33), 1, 5604, 5605, 5593, 5595, VectorType.REGULAR_BEARISH, 5570));
            CrossMarketConfirm c = h.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 34));
            Check(c.Confirmed, "confirms on the reclaim bar even though close 5595 is ABOVE its ema9 5570");
            Check(c.Reason.Contains("EMA not required"), "the log states the EMA was not part of the test");
            Check(h.EsDet1.DayAwaitingEma == 0, "no EMA wait state is ever entered");

            // and the stricter behavior is still available if it is ever wanted back
            MockHost h2 = new MockHost();
            h2.WireCrossMarket(4);
            SetupEsLevels(h2);
            h2.EsDet1.RequireEmaConfirmation = true;
            h2.EsDet1.OnBar(Bar(At(9, 31), 1, 5598, 5606, 5597, 5605, VectorType.BLUE_VECTOR, 5600));
            h2.EsDet1.OnBar(Bar(At(9, 33), 1, 5604, 5605, 5593, 5595, VectorType.REGULAR_BEARISH, 5570));
            CrossMarketConfirm c2 = h2.QueryCrossMarket(ConfirmMarket.ES, false, KeyLevelId.YDAY_HIGH, 1, At(9, 34));
            Check(!c2.Confirmed, "with the EMA toggle ON the same sequence does NOT confirm");
            Check(h2.EsDet1.DayAwaitingEma >= 1, "it waits for the EMA instead");
        }

        // ---- the grade table counts AGREEING MARKETS, not which one ------------
        private static void TestGradeTableCountsAgreement()
        {
            Console.WriteLine("V7.3 — grade is set by HOW MANY markets agree, not WHICH:");
            FbCrossMarketGradeTable t = new FbCrossMarketGradeTable();
            string g; double r;
            t.Resolve(true, true, out g, out r);
            Check(g == "A+" && Math.Abs(r - 30) < 1e-9, "both agree -> A+ @ 30%");
            t.Resolve(true, false, out g, out r);
            Check(g == "A-" && Math.Abs(r - 10) < 1e-9, "ES alone -> A- @ 10%");
            t.Resolve(false, true, out g, out r);
            Check(g == "A-" && Math.Abs(r - 10) < 1e-9, "market 2 alone -> A- @ 10% (interchangeable with ES)");
            t.Resolve(false, false, out g, out r);
            Check(g == "B+" && Math.Abs(r - 5) < 1e-9, "neither agrees -> B+ @ 5%");
        }

        // ---- TEST 8 / TEST 9: VECTOR_BREAK_RETEST enable switch --------------

        private static void TestVbrEnableSwitch()
        {
            Console.WriteLine("V7 — EnableVBR switch:");

            // TEST 8: VBR disabled == never fed a bar (exactly what the host does).
            // FB must be completely unaffected and no VBR artifact may appear.
            {
                MockHost h = new MockHost();
                h.Fb = null; h.Vbr = null;
                FakeBreakoutEngine fb = FbFrozenShort(h, At(9, 15), At(9, 30), 20090);
                VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());
                // the 15m/1m bars that WOULD have built a VBR parent are simply not delivered
                FbBluePath(fb, VectorType.REGULAR_BEARISH);

                Check(h.Entries.Count == 1 && h.Entries[0].StartsWith("FB_SHORT"),
                    "TEST 8: FAKE_BREAKOUT still enters normally with VBR disabled");
                Check(!vbr.HasOpenOrPendingPosition, "TEST 8: disabled VBR holds no position");
                int vbrEntries = 0;
                foreach (string e in h.Entries) if (e.StartsWith("VBR_")) vbrEntries++;
                Check(vbrEntries == 0, "TEST 8: zero VBR entries");
                foreach (string s in h.Sequence)
                    Check(!s.Contains("VBR_"), "TEST 8: no VBR order appears in the execution sequence");
                Check(!h.AnyDiagContains("HANDOFF"), "TEST 8: zero handoffs — FB is never flattened for VBR");
            }

            // TEST 9: VBR enabled behaves exactly as before (V6 U9 handoff intact).
            {
                MockHost h = new MockHost();
                h.LevelsEngine = StdLevels();
                VectorBreakRetestEngine vbr = new VectorBreakRetestEngine(h, new VbrConfig());
                vbr.OnFifteenMinuteBar(Bar(At(8, 45), 15, 20040, 20140, 20010, 20050,
                    VectorType.GREEN_VECTOR, 20030), 20040);
                Check(h.CountDiagContains("VBR PARENT CREATED") == 1,
                    "TEST 9: re-enabled VBR builds its parent setup exactly as before");
            }
        }

        // ==================================================================
        // VBR FINAL RULES — parent size filter, hard 15m invalidation,
        // Pattern B locality.  DAILY_OPEN = 20000 in StdLevels().
        // ==================================================================
        private const double DO = 20000;

        /// A 15m parent candle with an explicit range, closing on the requested side.
        private static BarSnap VbrParent(DateTime etClose, bool isLong, double range, double close)
        {
            double high = isLong ? close + range * 0.25 : close + range * 0.75;
            double low = high - range;
            return Bar(etClose.AddMinutes(-15), 15, close, high, low, close,
                       isLong ? VectorType.GREEN_VECTOR : VectorType.RED_VECTOR, close);
        }

        /// A 15m validity candle: closes where asked, optionally wicking through DO.
        private static BarSnap VbrValidity(DateTime etClose, double close, double high, double low)
        {
            return Bar(etClose.AddMinutes(-15), 15, close, high, low, close,
                       VectorType.REGULAR_BULLISH, close);
        }

        private static MockHost VbrHost(out VectorBreakRetestEngine vbr)
        {
            MockHost h = new MockHost();
            h.LevelsEngine = StdLevels();
            vbr = new VectorBreakRetestEngine(h, new VbrConfig());
            return h;
        }

        private static void TestVbrParentSizeFilter()
        {
            Console.WriteLine("VBR RULE 1 — 15m parent candle must span >= 125 points:");

            // TEST 1 — range 124.75 -> NO parent
            VectorBreakRetestEngine v1; MockHost h1 = VbrHost(out v1);
            v1.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 124.75, 20050), 20040);
            Check(h1.AnyDiagContains("VBR PARENT REJECTED reason=PARENT_RANGE_BELOW_125"),
                "TEST 1: range 124.75 is REJECTED");
            Check(!h1.AnyDiagContains("VBR PARENT CREATED"), "TEST 1: no parent is created");
            // and the validity clock never starts: a later 1m Pattern B cannot enter
            v1.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20006, 19980, 19990, VectorType.REGULAR_BEARISH, 20010));
            v1.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h1.Entries.Count == 0, "TEST 1: an undersized parent can never produce a 1m entry");

            // TEST 2 — range exactly 125.00 -> valid parent
            VectorBreakRetestEngine v2; MockHost h2 = VbrHost(out v2);
            v2.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 125.00, 20050), 20040);
            Check(h2.AnyDiagContains("VBR PARENT CREATED"), "TEST 2: range exactly 125.00 is ACCEPTED");
            Check(h2.AnyDiagContains("parentRangePoints=125.00"), "TEST 2: the logged range is 125.00");
            Check(h2.AnyDiagContains("validityWindow=4"), "TEST 2: the 4-candle validity window is logged");
        }

        private static void TestVbrFifteenMinuteInvalidation()
        {
            Console.WriteLine("VBR RULE 4/11 — only a completed 15m CLOSE on the wrong side invalidates:");

            // TEST 3 — LONG, validity #1 WICKS below DO but closes above -> still valid
            VectorBreakRetestEngine v3; MockHost h3 = VbrHost(out v3);
            v3.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v3.OnFifteenMinuteBar(VbrValidity(At(9, 15), 20030, 20060, 19950), 20050);  // low 19950 < DO
            Check(h3.AnyDiagContains("wickCrossedDO=true"), "TEST 3: the wick below Daily Open is logged");
            Check(h3.AnyDiagContains("closeInvalidated=false"), "TEST 3: a wick does NOT invalidate");
            Check(!h3.AnyDiagContains("VBR PARENT INVALIDATED"), "TEST 3: parent stays alive after a wick");

            // TEST 4 — LONG, validity #2 CLOSES below DO -> immediate invalidation
            v3.OnFifteenMinuteBar(VbrValidity(At(9, 30), 19980, 20010, 19960), 20030);
            Check(h3.AnyDiagContains("VBR PARENT INVALIDATED reason=15M_CLOSE_WRONG_SIDE_DAILY_OPEN"),
                "TEST 4: a completed 15m close below Daily Open invalidates the LONG parent");
            Check(h3.AnyDiagContains("candleNum=2"), "TEST 4: the invalidating candle number is logged");
            int before4 = h3.Entries.Count;
            v3.OnOneMinuteBar(Bar(At(9, 46), 1, 20005, 20006, 19980, 19990, VectorType.REGULAR_BEARISH, 20010));
            v3.OnOneMinuteBar(Bar(At(9, 48), 1, 19990, 20030, 19988, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h3.Entries.Count == before4, "TEST 4: no 1m entry is possible after invalidation");

            // TEST 5 — SHORT, wick ABOVE DO but closes below -> still valid
            VectorBreakRetestEngine v5; MockHost h5 = VbrHost(out v5);
            v5.OnFifteenMinuteBar(VbrParent(At(9, 0), false, 130, 19950), 19960);
            v5.OnFifteenMinuteBar(VbrValidity(At(9, 15), 19970, 20080, 19940), 19950);  // high 20080 > DO
            Check(h5.AnyDiagContains("wickCrossedDO=true") && h5.AnyDiagContains("closeInvalidated=false"),
                "TEST 5: SHORT wick above Daily Open does NOT invalidate");
            Check(!h5.AnyDiagContains("VBR PARENT INVALIDATED"), "TEST 5: SHORT parent stays alive");

            // TEST 6 — SHORT, close ABOVE DO -> invalidation
            v5.OnFifteenMinuteBar(VbrValidity(At(9, 30), 20030, 20050, 20010), 19970);
            Check(h5.AnyDiagContains("VBR PARENT INVALIDATED reason=15M_CLOSE_WRONG_SIDE_DAILY_OPEN"),
                "TEST 6: a completed 15m close above Daily Open invalidates the SHORT parent");

            // TEST 7 — validity candle never touches Daily Open at all -> alive, clock ticks
            VectorBreakRetestEngine v7; MockHost h7 = VbrHost(out v7);
            v7.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v7.OnFifteenMinuteBar(VbrValidity(At(9, 15), 20120, 20140, 20100), 20050);  // never near DO
            Check(h7.AnyDiagContains("wickCrossedDO=false") && h7.AnyDiagContains("closeInvalidated=false"),
                "TEST 7: a candle that never touches Daily Open keeps the parent alive");
            Check(h7.AnyDiagContains("candleNum=1"), "TEST 7: the validity clock still advances");

            // TEST 8 — four candles, no entry, no invalidation -> expiry, NO fifth candle
            v7.OnFifteenMinuteBar(VbrValidity(At(9, 30), 20125, 20145, 20105), 20120);
            v7.OnFifteenMinuteBar(VbrValidity(At(9, 45), 20130, 20150, 20110), 20125);
            Check(!h7.AnyDiagContains("EXPIRED"), "TEST 8: not expired before candle #4 completes");
            v7.OnFifteenMinuteBar(VbrValidity(At(10, 0), 20135, 20155, 20115), 20130);
            Check(h7.AnyDiagContains("EXPIRED"), "TEST 8: parent expires after the 4th validity candle");
            Check(h7.CountDiagContains("VBR 15M VALIDITY") == 4, "TEST 8: exactly 4 validity candles, no fifth");

            // TEST 14 — the parent candle itself is not validity candle #1
            VectorBreakRetestEngine v14; MockHost h14 = VbrHost(out v14);
            v14.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            Check(h14.CountDiagContains("VBR 15M VALIDITY") == 0,
                "TEST 14: the parent candle is NOT counted as validity candle #1");
            v14.OnFifteenMinuteBar(VbrValidity(At(9, 15), 20120, 20140, 20100), 20050);
            Check(h14.AnyDiagContains("candleNum=1"), "TEST 14: the NEXT completed candle is #1");

            // TEST 15 — the 4-candle clock never restarts on a later qualifying vector
            VectorBreakRetestEngine v15; MockHost h15 = VbrHost(out v15);
            v15.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v15.OnFifteenMinuteBar(VbrParent(At(9, 15), true, 130, 20120), 20050);   // another green vector
            Check(h15.CountDiagContains("VBR PARENT CREATED") == 1,
                "TEST 15: a later qualifying vector does NOT create a second parent");
            v15.OnFifteenMinuteBar(VbrValidity(At(9, 30), 20125, 20145, 20105), 20120);
            v15.OnFifteenMinuteBar(VbrValidity(At(9, 45), 20130, 20150, 20110), 20125);
            v15.OnFifteenMinuteBar(VbrValidity(At(10, 0), 20135, 20155, 20115), 20130);
            Check(h15.AnyDiagContains("EXPIRED"),
                "TEST 15: expiry is measured from the ORIGINAL trigger — the clock never restarts");
        }

        private static void TestVbrPatternBLocality()
        {
            Console.WriteLine("VBR RULES 7/8/9/10 — Pattern B structure must stay LOCAL:");

            // TEST 9 — immediate EMA confirmation; stop = local structure low
            VectorBreakRetestEngine v9; MockHost h9 = VbrHost(out v9);
            v9.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v9.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20008, 19985, 19990, VectorType.REGULAR_BEARISH, 20012));
            Check(h9.AnyDiagContains("PATTERN_B_STRUCTURE_START"), "TEST 9: structure starts on the close below DO");
            v9.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20030, 19989, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h9.Entries.Count == 1 && h9.Entries[0].StartsWith("VBR_LONG"), "TEST 9: immediate LONG entry");
            Check(h9.AnyDiagContains("PATTERN_B_ENTRY"), "TEST 9: PATTERN_B_ENTRY is logged");
            Check(h9.AnyDiagContains("stop=19985.00"), "TEST 9: stop = LOCAL structure low 19985, not an older extreme");
            Check(h9.AnyDiagContains("elapsedMinutes=2"), "TEST 9: elapsedMinutes reports the structure age");

            // TEST 10 — EMA wait, then confirmation while the parent is still valid
            VectorBreakRetestEngine v10; MockHost h10 = VbrHost(out v10);
            v10.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v10.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20008, 19985, 19990, VectorType.REGULAR_BEARISH, 20012));
            v10.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20008, 19989, 20005, VectorType.REGULAR_BULLISH, 20010));
            Check(h10.Entries.Count == 0, "TEST 10: reclaim above DO but below EMA9 does NOT enter");
            Check(h10.AnyDiagContains("emaConfirmed=false"), "TEST 10: the failed EMA leg is logged");
            v10.OnOneMinuteBar(Bar(At(9, 35), 1, 20005, 20030, 20004, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h10.Entries.Count == 1, "TEST 10: a later close beyond BOTH DO and EMA9 enters");
            Check(h10.AnyDiagContains("stop=19985.00"), "TEST 10: stop is still the LOCAL structure low");

            // TEST 11 — 15m invalidation during the EMA wait MUST kill the setup
            VectorBreakRetestEngine v11; MockHost h11 = VbrHost(out v11);
            v11.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v11.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20008, 19985, 19990, VectorType.REGULAR_BEARISH, 20012));
            v11.OnOneMinuteBar(Bar(At(9, 33), 1, 19990, 20008, 19989, 20005, VectorType.REGULAR_BULLISH, 20010));
            Check(h11.Entries.Count == 0, "TEST 11: waiting for EMA");
            v11.OnFifteenMinuteBar(VbrValidity(At(9, 45), 19970, 20010, 19960), 20050);   // closes BELOW DO
            Check(h11.AnyDiagContains("VBR PARENT INVALIDATED"), "TEST 11: the 15m close invalidates the parent");
            v11.OnOneMinuteBar(Bar(At(9, 50), 1, 20005, 20030, 20004, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h11.Entries.Count == 0,
                "TEST 11: a later EMA confirmation MUST NOT enter — Pattern B state was cleared");

            // TEST 12 — mirror: SHORT Pattern B
            VectorBreakRetestEngine v12; MockHost h12 = VbrHost(out v12);
            v12.OnFifteenMinuteBar(VbrParent(At(9, 0), false, 130, 19950), 19960);
            v12.OnOneMinuteBar(Bar(At(9, 31), 1, 19995, 20015, 19994, 20010, VectorType.REGULAR_BULLISH, 19988));
            Check(h12.AnyDiagContains("PATTERN_B_STRUCTURE_START"), "TEST 12: SHORT structure starts above DO");
            v12.OnOneMinuteBar(Bar(At(9, 33), 1, 20010, 20011, 19970, 19975, VectorType.RED_VECTOR, 19990));
            Check(h12.Entries.Count == 1 && h12.Entries[0].StartsWith("VBR_SHORT"), "TEST 12: SHORT entry");
            Check(h12.AnyDiagContains("stop=20015.00"), "TEST 12: stop = LOCAL structure high 20015");

            // TEST 13 — wick alone never invalidates (explicit, both directions covered above)
            VectorBreakRetestEngine v13; MockHost h13 = VbrHost(out v13);
            v13.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);
            v13.OnFifteenMinuteBar(VbrValidity(At(9, 15), 20040, 20060, 19900), 20050);  // deep wick below DO
            v13.OnFifteenMinuteBar(VbrValidity(At(9, 30), 20045, 20065, 19905), 20040);  // again
            Check(!h13.AnyDiagContains("VBR PARENT INVALIDATED"),
                "TEST 13: repeated deep wicks below Daily Open never invalidate a LONG parent");
            v13.OnOneMinuteBar(Bar(At(9, 46), 1, 20005, 20008, 19985, 19990, VectorType.REGULAR_BEARISH, 20012));
            v13.OnOneMinuteBar(Bar(At(9, 48), 1, 19990, 20030, 19989, 20025, VectorType.GREEN_VECTOR, 20010));
            Check(h13.Entries.Count == 1, "TEST 13: the parent still trades normally after wicks");
        }

        private static void TestVbrOversizedStopRootCause()
        {
            Console.WriteLine("VBR ROOT CAUSE — a new Daily Open excursion must NOT inherit an old extreme:");

            // Reproduces the oversized-stop mechanism exactly.
            // Excursion 1 runs deep (low 19850). Price reclaims but misses the EMA, so
            // the engine waits. Price then dips back through DO on a SHALLOW excursion
            // (low 19985) and confirms. The stop must come from the SHALLOW structure.
            VectorBreakRetestEngine v; MockHost h = VbrHost(out v);
            v.OnFifteenMinuteBar(VbrParent(At(9, 0), true, 130, 20050), 20040);

            v.OnOneMinuteBar(Bar(At(9, 31), 1, 20005, 20008, 19850, 19900, VectorType.REGULAR_BEARISH, 20012));
            v.OnOneMinuteBar(Bar(At(9, 33), 1, 19900, 20008, 19899, 20005, VectorType.REGULAR_BULLISH, 20010));
            Check(h.Entries.Count == 0, "deep excursion reclaimed but is below EMA9 — waiting");

            v.OnOneMinuteBar(Bar(At(9, 35), 1, 20005, 20006, 19985, 19995, VectorType.REGULAR_BEARISH, 20010));
            Check(h.CountDiagContains("PATTERN_B_STRUCTURE_START") == 2,
                "the new excursion starts a SECOND, independent structure");
            v.OnOneMinuteBar(Bar(At(9, 37), 1, 19995, 20030, 19994, 20025, VectorType.GREEN_VECTOR, 20010));

            Check(h.Entries.Count == 1, "entry taken on the fresh excursion");
            Check(h.AnyDiagContains("stop=19985.00"),
                "stop = 19985 from the LOCAL structure (40 pts), NOT 19850 from the stale one (175 pts)");
            Check(!h.AnyDiagContains("stop=19850.00"), "the stale deep extreme is never used as the stop");
            Check(h.AnyDiagContains("elapsedMinutes=2"),
                "elapsedMinutes reflects the LOCAL structure age, not the whole parent window");
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

            // ---- V6 FINAL RULE LOCKS ----
            TestU1FbTargetBreak();
            TestU4U5FbReclaim();
            TestU6PatternBWait();
            TestU6PatternBWaitShort();
            TestU2U3U8ProfitManagement();
            TestU2TargetChaining();
            TestU8SingleContract();
            TestU7RollingReentry();
            TestU7WrongSideBreaksRolling();
            TestU9HandoffFbToVbr();
            TestU9HandoffVbrToFb();

            // ---- FINAL FAKE BREAKOUT EMA RULE ----
            TestFinalFbEmaRule();
            TestSessionVwap();

            // ---- V7 CROSS-MARKET CONFIRMATION + VBR SWITCH ----
            TestCrossMarketGrading();
            TestUnknownIsNotNo();
            TestFuturesConfirmMarket2();
            TestConfirmMarketsIgnoreEma();
            TestGradeTableCountsAgreement();
            TestVbrEnableSwitch();

            // ---- VBR FINAL RULES ----
            TestVbrParentSizeFilter();
            TestVbrFifteenMinuteInvalidation();
            TestVbrPatternBLocality();
            TestVbrOversizedStopRootCause();

            Console.WriteLine();
            Console.WriteLine(string.Format("RESULT: {0} passed, {1} failed", passed, failed));
            return failed == 0 ? 0 : 1;
        }
    }
}
