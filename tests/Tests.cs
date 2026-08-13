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
            // NOTE: the 9:15-9:30 candle that reclaims below YDAY_HIGH for the short
            // slot also satisfies the §5 LONG parent trigger at the same level, so an
            // independent FB long can also fire here. That is spec-correct; the old
            // 15m EMA confluence gate used to mask it. This assertion targets the
            // SHORT entry specifically.
            Check(h.Entries.Contains("FB_SHORT 45"),
                "later short entry sized at B+ 10% risk (45 contracts)");
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
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20040, 20060, 20010, 20050, VectorType.GREEN_VECTOR, 20030), 20040);
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
            Check(h.AnyDiagContains("WAITING for a later 1m close beyond BOTH"),
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
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 19960, 19990, 19940, 19950, VectorType.RED_VECTOR, 19970), 19960);
            // 1. completed 1m close ABOVE Daily Open
            vbr.OnOneMinuteBar(Bar(At(9, 31), 1, 19995, 20015, 19994, 20010, VectorType.REGULAR_BULLISH, 19990));
            // 2. close back BELOW Daily Open but ABOVE EMA9 -> WAIT
            vbr.OnOneMinuteBar(Bar(At(9, 33), 1, 20010, 20012, 19992, 19995, VectorType.REGULAR_BEARISH, 19990));
            Check(h.Entries.Count == 0 && h.AnyDiagContains("WAITING for a later 1m close beyond BOTH"),
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
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20005, 20020, 19995, 20015, VectorType.GREEN_VECTOR, 20005), 20005);
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
            Check(h.AnyDiagContains("ROLLING RE-ENTRY BROKEN"),
                "U7: wrong-side close ends the rolling re-entry permission");
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
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20040, 20060, 20010, 20050, VectorType.GREEN_VECTOR, 20030), 20040);
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
            vbr.OnFifteenMinuteBar(Bar(At(9, 0), 15, 20040, 20060, 20010, 20050, VectorType.GREEN_VECTOR, 20030), 20040);
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

            Console.WriteLine();
            Console.WriteLine(string.Format("RESULT: {0} passed, {1} failed", passed, failed));
            return failed == 0 ? 0 : 1;
        }
    }
}
