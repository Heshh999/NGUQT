// ============================================================================
// V4Tests.cs - deterministic tests for the V4 market-structure engines.
//
// The assertions that matter most here are the ones that would let a lookahead
// bug through unnoticed:
//
//   - a bar must not be able to break a swing that its own print confirmed
//   - a swing must not be visible before its confirmation bar closed
//   - a forward label must not move on a bar at or before the event's close
//   - a break bar that CLOSED beyond a level must never be filed as a wick
//
// That last one is a direct regression test against the V3 defect where the
// side-of-level test was taken against the close, which made the "closed
// through" outcome unreachable and buried every real break inside the sweep
// bucket. The V4 classifier is a pure function precisely so this class of bug
// is checkable rather than inferable.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace MnqTwoTests
{
    public static class V4Tests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        private static V4Bar B(DateTime etOpen, int minutes, double o, double h, double l, double c)
        {
            return B(etOpen, minutes, o, h, l, c, 1000);
        }

        private static V4Bar B(DateTime etOpen, int minutes, double o, double h, double l, double c, double v)
        {
            V4Bar b = new V4Bar();
            b.EtOpen = etOpen; b.EtClose = etOpen.AddMinutes(minutes);
            b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = v;
            return b;
        }

        public static int Run()
        {
            Console.WriteLine();
            Console.WriteLine("V4 MULTI-TIMEFRAME MARKET STRUCTURE");
            Console.WriteLine("-----------------------------------");
            passed = 0; failed = 0;

            Classifier();
            SwingConfirmation();
            SwingLabelsAndStates();
            LocationBookTests();
            EngineNoLookahead();
            EngineLabels();
            EntryProbes();
            CsvShape();
            HorizonsAcrossGaps();
            OrderFlow();
            SessionBoundaries();
            EntryWindowGuard();

            Console.WriteLine();
            Console.WriteLine(string.Format("V4 ENGINES: {0} passed, {1} failed", passed, failed));
            return failed;
        }

        // ====================================================================
        private static void Classifier()
        {
            DateTime t = new DateTime(2026, 3, 2, 9, 30, 0);
            double atr = 10.0, level = 20000;

            // never reached
            Check(V4BreakClassifier.Classify(B(t, 1, 19970, 19980, 19960, 19975), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.NO_TOUCH,
                  "far below a prior high is NO_TOUCH");

            // inside the approach band
            Check(V4BreakClassifier.Classify(B(t, 1, 19993, 19997, 19990, 19996), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.APPROACHED,
                  "within the approach band is APPROACHED");

            // exact touch
            Check(V4BreakClassifier.Classify(B(t, 1, 19993, 20000, 19990, 19996), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.TOUCHED,
                  "high exactly at the level is TOUCHED");

            // small poke, closed back -> wick
            Check(V4BreakClassifier.Classify(B(t, 1, 19993, 20001, 19990, 19996), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.WICKED_BEYOND,
                  "1pt poke on a 10pt ATR, closing back, is WICKED_BEYOND");

            // big poke, still closed back -> traded beyond
            Check(V4BreakClassifier.Classify(B(t, 1, 19993, 20008, 19990, 19996), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.TRADED_BEYOND_NO_CLOSE,
                  "8pt poke closing back is TRADED_BEYOND_NO_CLOSE, not a wick");

            // closed beyond, small body -> weak
            Check(V4BreakClassifier.Classify(B(t, 1, 19996, 20005, 19995, 20004), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.CLOSED_BEYOND_WEAK,
                  "closed beyond with an 8pt body on a 10pt ATR is CLOSED_BEYOND_WEAK");

            // closed beyond, big body and far beyond -> displacement
            Check(V4BreakClassifier.Classify(B(t, 1, 19990, 20006, 19989, 20005), level, +1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.CLOSED_BEYOND_DISPLACEMENT,
                  "closed 5pt beyond with a 15pt body is CLOSED_BEYOND_DISPLACEMENT");

            // ---- the V3 regression -----------------------------------------
            // Sweep a range of bars that all CLOSE beyond the level and assert
            // that not one of them is ever filed as a wick or a failed trade
            // through. This is the exact defect that made 47.6% of one V3
            // bucket the opposite behaviour from the one it was named for.
            bool anyCloseThroughFiledAsWick = false;
            for (int i = 1; i <= 60; i++)
            {
                double close = level + i * 0.25;
                V4BreakOutcome o = V4BreakClassifier.Classify(
                    B(t, 1, level - 5, close + 2, level - 6, close), level, +1, atr, 0.5, 0.25, 1.0, 0.35);
                if (V4BreakClassifier.IsWickThrough(o)) anyCloseThroughFiledAsWick = true;
            }
            Check(!anyCloseThroughFiledAsWick,
                  "a bar that CLOSED beyond the level is never filed as a wick or failed break");

            // and the mirror for lows: same shapes, same answers
            Check(V4BreakClassifier.Classify(B(t, 1, 20001, 20002, 19994, 19996), level, -1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.CLOSED_BEYOND_WEAK,
                  "closing below a prior low with a 5pt body is CLOSED_BEYOND_WEAK");
            Check(V4BreakClassifier.Classify(B(t, 1, 20005, 20006, 19994, 19995), level, -1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.CLOSED_BEYOND_DISPLACEMENT,
                  "closing 5pt below with a 10pt body on a 10pt ATR is displacement");
            Check(V4BreakClassifier.Classify(B(t, 1, 20005, 20006, 19999, 20003), level, -1, atr,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.WICKED_BEYOND,
                  "a 1pt poke below a prior low, closing back, is WICKED_BEYOND");

            // an unusable ATR must not produce a confident classification
            Check(V4BreakClassifier.Classify(B(t, 1, 19990, 20010, 19989, 20009), level, +1, double.NaN,
                    0.5, 0.25, 1.0, 0.35) == V4BreakOutcome.NO_TOUCH,
                  "with no ATR the classifier refuses rather than guesses");
        }

        // ====================================================================
        private static void SwingConfirmation()
        {
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 2; t.PivotLeftBars = 2; t.AtrPeriod = 3;
            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);

            // a clean peak at index 2, then two lower bars to confirm it
            t.OnBar(B(s.AddMinutes(0), 1, 100, 102, 99, 101));
            t.OnBar(B(s.AddMinutes(1), 1, 101, 104, 100, 103));
            t.OnBar(B(s.AddMinutes(2), 1, 103, 110, 102, 109));   // the pivot
            t.OnBar(B(s.AddMinutes(3), 1, 109, 108, 105, 106));
            DateTime beforeConfirm = s.AddMinutes(4);             // close of bar 3
            t.OnBar(B(s.AddMinutes(4), 1, 106, 107, 103, 104));
            DateTime afterConfirm = s.AddMinutes(5);              // close of bar 4

            V4Swing early = t.SwingHighKnownAt(beforeConfirm);
            V4Swing late = t.SwingHighKnownAt(afterConfirm);
            Check(!early.Valid, "a pivot is invisible until its confirmation bar has closed");
            Check(late.Valid && Math.Abs(late.Price - 110) < 1e-9,
                  "the pivot becomes visible at the close of the confirming bar, at the right price");
            Check(late.KnownAtEt == afterConfirm && late.FormedAtEt == s.AddMinutes(3),
                  "KnownAtEt is the confirming bar's close, FormedAtEt is the pivot bar's own close");
            Check(late.KnownAtEt > late.FormedAtEt,
                  "a swing is never knowable at the moment it forms");
        }

        // ====================================================================
        private static void SwingLabelsAndStates()
        {
            // Build an unambiguous higher-high / higher-low zigzag.
            //
            // Each element is ONE bar. Adjacent bars must differ in high and in
            // low or nothing is a pivot at all: the pivot test is strict on both
            // sides, so a fixture whose neighbouring bars share an extreme
            // produces no swings and would make every assertion below vacuous.
            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            double[] upH = { 100, 120, 105, 130, 112, 145, 120, 160, 130 };
            double[] upL = {  90, 108,  92, 118, 100, 132, 108, 148, 118 };
            V4StructureTracker t = Zig("1m", upH, upL, s);
            DateTime end = s.AddMinutes(upH.Length + 10);

            Check(t.SwingHighKnownAt(end).Valid && t.SwingLowKnownAt(end).Valid,
                  "an alternating zigzag produces confirmed swing highs and swing lows");
            Check(t.SwingHighKnownAt(end).Label == V4SwingLabel.HH,
                  "a peak above the previous peak is labelled HH");
            Check(t.SwingLowKnownAt(end).Label == V4SwingLabel.HL,
                  "a trough above the previous trough is labelled HL");
            Check(t.StateKnownAt(end) == V4StructureState.BULLISH,
                  "higher highs with higher lows is BULLISH");

            // the mirror
            double[] dnH = { 160, 145, 155, 130, 140, 115, 125, 100, 110 };
            double[] dnL = { 148, 130, 138, 118, 125, 100, 112,  88,  98 };
            V4StructureTracker d = Zig("1m", dnH, dnL, s);
            Check(d.SwingHighKnownAt(end).Label == V4SwingLabel.LH,
                  "a peak below the previous peak is labelled LH");
            Check(d.SwingLowKnownAt(end).Label == V4SwingLabel.LL,
                  "a trough below the previous trough is labelled LL");
            Check(d.StateKnownAt(end) == V4StructureState.BEARISH,
                  "lower highs with lower lows is BEARISH");

            // a range: lower highs but higher lows
            double[] rH = { 100, 140, 105, 130, 108, 120, 106 };
            double[] rL = {  90,  95,  60,  98,  70, 100,  80 };
            V4StructureTracker rg = Zig("1m", rH, rL, s);
            Check(rg.StateKnownAt(end) == V4StructureState.RANGE_CONTRACTING,
                  "lower highs with higher lows is RANGE_CONTRACTING, not a direction");
            Check(V4StructureTracker.DirOf(rg.StateKnownAt(end)) == V4Dir.NONE,
                  "a contracting range has no direction, and that is a real answer");

            // the state is refused before it was knowable
            Check(t.StateKnownAt(s.AddMinutes(-1)) == V4StructureState.UNKNOWN,
                  "a structure state is UNKNOWN before the bar that established it");
            Check(V4StructureTracker.DirOf(V4StructureState.BULLISH) == V4Dir.UP
                  && V4StructureTracker.DirOf(V4StructureState.BEARISH) == V4Dir.DOWN,
                  "only the two directional states carry a direction");

            // equality band: a quarter-point higher high is not a higher high
            double[] eH = { 100, 120, 105, 120.25, 105 };
            double[] eL = {  90, 108,  92, 108, 92 };
            V4StructureTracker eq = Zig("1m", eH, eL, s, 1.0);
            V4Swing last = eq.SwingHighKnownAt(end);
            Check(last.Valid && last.Label == V4SwingLabel.EQUAL_HIGH,
                  "a quarter-point higher high inside the equality band is EQUAL, not HH");

            // and with the band switched off it IS a higher high, which is what
            // makes the band a real parameter rather than a rounding accident
            V4StructureTracker eq0 = Zig("1m", eH, eL, s, 0.0);
            Check(eq0.SwingHighKnownAt(end).Label == V4SwingLabel.HH,
                  "with the equality band at zero the same quarter-point is a higher high");
        }

        /// Feeds a zigzag of single bars into a fresh tracker.
        private static V4StructureTracker Zig(string label, double[] highs, double[] lows,
                                              DateTime start)
        {
            return Zig(label, highs, lows, start, 0.0);
        }

        private static V4StructureTracker Zig(string label, double[] highs, double[] lows,
                                              DateTime start, double equalityBandAtr)
        {
            V4StructureTracker t = new V4StructureTracker(label, 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 3;
            t.EqualityBandAtr = equalityBandAtr;
            for (int i = 0; i < highs.Length; i++)
            {
                double mid = (highs[i] + lows[i]) / 2.0;
                t.OnBar(B(start.AddMinutes(i), 1, mid, highs[i], lows[i], mid));
            }
            return t;
        }

        // ====================================================================
        private static void LocationBookTests()
        {
            V4LocationBook lb = new V4LocationBook();

            // 18:00 ET rolls the exchange day forward
            Check(lb.ExchangeDayKey(new DateTime(2026, 3, 2, 17, 59, 0)) == 20260302,
                  "17:59 ET belongs to that calendar day's session");
            Check(lb.ExchangeDayKey(new DateTime(2026, 3, 2, 18, 0, 0)) == 20260303,
                  "18:00 ET belongs to the NEXT session, as CME defines the day");
            Check(lb.ExchangeDayKey(new DateTime(2026, 3, 3, 9, 30, 0)) == 20260303,
                  "the cash open belongs to the session that started the evening before");

            // prior-day extremes appear only after the day rolls
            DateTime d1 = new DateTime(2026, 3, 2, 10, 0, 0);
            for (int i = 0; i < 5; i++)
                lb.Apply(B(d1.AddMinutes(i), 1, 100 + i, 105 + i, 95 + i, 101 + i));
            Check(double.IsNaN(lb.PriorDayHigh),
                  "there is no prior day until a day boundary has been crossed");
            lb.Apply(B(new DateTime(2026, 3, 2, 18, 30, 0), 1, 110, 111, 109, 110));
            Check(Math.Abs(lb.PriorDayHigh - 109) < 1e-9 && Math.Abs(lb.PriorDayLow - 95) < 1e-9,
                  "prior day high/low are the extremes of the session that just ended");

            // session VWAP accumulates only inside RTH
            V4LocationBook v = new V4LocationBook();
            v.Apply(B(new DateTime(2026, 3, 3, 9, 0, 0), 1, 100, 100, 100, 100, 1000));
            Check(double.IsNaN(v.SessionVwap), "premarket volume does not enter the session VWAP");
            v.Apply(B(new DateTime(2026, 3, 3, 9, 30, 0), 1, 200, 200, 200, 200, 100));
            Check(Math.Abs(v.SessionVwap - 200) < 1e-9,
                  "the session VWAP starts at the first RTH bar");
            Check(Math.Abs(v.SessionHigh - 200) < 1e-9 && Math.Abs(v.SessionOpen - 200) < 1e-9,
                  "session extremes and open come from RTH bars only");

            // nearest-level selection is deterministic
            string name; double dist;
            v.Nearest(201, 10, out name, out dist);
            Check(name != "NONE" && dist >= 0, "the nearest tracked level is named and measured");
            v.Nearest(201, double.NaN, out name, out dist);
            Check(name == "NONE", "with no ATR there is no location answer, rather than a wrong one");
        }

        // ====================================================================
        /// Drives the full engine and checks the properties that a lookahead
        /// bug would break.
        private static void EngineNoLookahead()
        {
            List<string> rows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(delegate(string r) { rows.Add(r); }, null);
            eng.ControlSampleRate = 0;
            eng.EmitEntries = false;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);

            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            // A rising staircase with one clean peak, then a bar that takes it out.
            double[] highs = { 100, 104, 112, 108, 106, 105, 104, 103, 102, 101, 120 };
            double[] lows = { 95, 99, 107, 103, 101, 100, 99, 98, 97, 96, 100 };
            double[] closes = { 99, 103, 111, 105, 103, 102, 101, 100, 99, 98, 119 };
            for (int i = 0; i < highs.Length; i++)
                eng.OnStructureBar("1m", B(s.AddMinutes(i), 1, closes[i] - 1, highs[i], lows[i], closes[i]));

            Check(rows.Count == 0, "no row is written before its forward horizon has elapsed");

            // The cutoff rule: a bar cannot break a swing confirmed at its own close.
            V4Bar probe = B(s.AddMinutes(10), 1, 100, 120, 100, 119);
            Check(V4ResearchEngine.SnapshotCutoff(probe) < probe.EtClose,
                  "the cross-timeframe cutoff is strictly before the consuming bar's close");

            // Feed the label clock past the event budget (horizon + entry window)
            // and let one event resolve.
            for (int i = 0; i <= 320; i++)
                eng.OnOneMinuteBar(B(s.AddMinutes(11 + i), 1, 119, 121, 118, 120));
            Check(rows.Count > 0, "an event is written once its 240-minute horizon has elapsed");
            Check(eng.BreaksEmitted > 0, "the staircase peak was recorded as a break");
        }

        // ====================================================================
        private static void EngineLabels()
        {
            List<string> rows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(delegate(string r) { rows.Add(r); }, null);
            eng.ControlSampleRate = 0;
            eng.EmitEntries = false;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);

            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            double[] hi = { 100, 104, 112, 108, 106, 105, 104, 103, 102, 101, 120 };
            double[] lo = { 95, 99, 107, 103, 101, 100, 99, 98, 97, 96, 100 };
            double[] cl = { 99, 103, 111, 105, 103, 102, 101, 100, 99, 98, 119 };
            for (int i = 0; i < hi.Length; i++)
            {
                V4Bar b = B(s.AddMinutes(i), 1, cl[i] - 1, hi[i], lo[i], cl[i]);
                eng.OnStructureBar("1m", b);
                eng.OnOneMinuteBar(b);
            }
            // straight up for four hours
            for (int i = 0; i < 245; i++)
            {
                V4Bar b = B(s.AddMinutes(11 + i), 1, 119 + i, 121 + i, 118 + i, 120 + i);
                eng.OnStructureBar("1m", b);
                eng.OnOneMinuteBar(b);
            }
            eng.Finish();

            Check(rows.Count > 0, "the run produced rows");
            string[] hdr = V4ResearchEngine.StructureCsvHeader().Split(',');
            int iSide = Array.IndexOf(hdr, "side");
            int iNet60 = Array.IndexOf(hdr, "net_60m");
            int iMfe60 = Array.IndexOf(hdr, "mfe_60m");
            int iMae60 = Array.IndexOf(hdr, "mae_60m");
            int iMfe15 = Array.IndexOf(hdr, "mfe_15m");
            int iMae15 = Array.IndexOf(hdr, "mae_15m");
            int iKind = Array.IndexOf(hdr, "eventKind");
            int iFollow = Array.IndexOf(hdr, "followState");
            int iOut = Array.IndexOf(hdr, "outcome");

            bool sawUpBreak = false, netPositive = false;
            bool mfeMonotone = true, maeMonotone = true, everFailed = false;
            for (int r = 0; r < rows.Count; r++)
            {
                string[] c = rows[r].Split(',');
                if (c[iKind] != "BREAK") continue;
                if (c[iSide] != "UP") continue;
                sawUpBreak = true;
                double n60 = Num(c[iNet60]);
                if (n60 > 0) netPositive = true;
                double m15 = Num(c[iMfe15]), m60 = Num(c[iMfe60]);
                double a15 = Num(c[iMae15]), a60 = Num(c[iMae60]);
                if (!double.IsNaN(m15) && !double.IsNaN(m60) && m60 < m15 - 1e-9) mfeMonotone = false;
                if (!double.IsNaN(a15) && !double.IsNaN(a60) && a60 < a15 - 1e-9) maeMonotone = false;
                if (c[iFollow] == "FAILED_BREAK" || c[iFollow] == "IMMEDIATE_REJECTION") everFailed = true;
                if (!V4BreakClassifier.IsAnyBreak(
                        (V4BreakOutcome)Enum.Parse(typeof(V4BreakOutcome), c[iOut])))
                    Check(false, "a BREAK row carries a break outcome");
            }
            Check(sawUpBreak, "an upside break was captured");
            Check(netPositive, "net return after a break into a rising market is positive");
            Check(mfeMonotone, "MFE never decreases as the horizon lengthens");
            Check(maeMonotone, "MAE never decreases as the horizon lengthens - it is a magnitude");
            Check(!everFailed, "a break followed by four hours of continuation is not a failed break");

            // ---- the mirror: a break that immediately gives up --------------
            List<string> rows2 = new List<string>();
            V4ResearchEngine e2 = new V4ResearchEngine(delegate(string r) { rows2.Add(r); }, null);
            e2.ControlSampleRate = 0; e2.EmitEntries = false;
            V4StructureTracker t2 = new V4StructureTracker("1m", 1);
            t2.ConfirmBars = 1; t2.PivotLeftBars = 1; t2.AtrPeriod = 5;
            e2.AddTracker(t2);
            for (int i = 0; i < hi.Length; i++)
            {
                V4Bar b = B(s.AddMinutes(i), 1, cl[i] - 1, hi[i], lo[i], cl[i]);
                e2.OnStructureBar("1m", b);
                e2.OnOneMinuteBar(b);
            }
            for (int i = 0; i < 245; i++)
            {
                double p = 119 - i * 0.5;
                V4Bar b = B(s.AddMinutes(11 + i), 1, p + 1, p + 1, p - 1, p);
                e2.OnStructureBar("1m", b);
                e2.OnOneMinuteBar(b);
            }
            e2.Finish();
            bool sawFail = false;
            for (int r = 0; r < rows2.Count; r++)
            {
                string[] c = rows2[r].Split(',');
                if (c[iKind] != "BREAK" || c[iSide] != "UP") continue;
                if (c[iFollow] == "FAILED_BREAK" || c[iFollow] == "IMMEDIATE_REJECTION") sawFail = true;
            }
            Check(sawFail, "a break that reverses straight back through the level is a failed break");
        }

        // ====================================================================
        private static void EntryProbes()
        {
            List<string> srows = new List<string>(), erows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(
                delegate(string r) { srows.Add(r); }, delegate(string r) { erows.Add(r); });
            eng.ControlSampleRate = 0;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);

            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            double[] hi = { 100, 104, 112, 108, 106, 105, 104, 103, 102, 101, 120 };
            double[] lo = { 95, 99, 107, 103, 101, 100, 99, 98, 97, 96, 100 };
            double[] cl = { 99, 103, 111, 105, 103, 102, 101, 100, 99, 98, 119 };
            for (int i = 0; i < hi.Length; i++)
            {
                V4Bar b = B(s.AddMinutes(i), 1, cl[i] - 1, hi[i], lo[i], cl[i]);
                eng.OnStructureBar("1m", b);
                eng.OnOneMinuteBar(b);
            }
            // pull back to the broken level, then reclaim and run
            double[] path = { 116, 113, 112.5, 114, 116, 119, 123, 127 };
            int mm = 11;
            for (int i = 0; i < path.Length; i++, mm++)
            {
                V4Bar b = B(s.AddMinutes(mm), 1, path[i], path[i] + 0.5, path[i] - 0.5, path[i]);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            for (int i = 0; i < 245; i++, mm++)
            {
                V4Bar b = B(s.AddMinutes(mm), 1, 127 + i, 128 + i, 126 + i, 127 + i);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            eng.Finish();

            string[] ehdr = V4ResearchEngine.EntryCsvHeader().Split(',');
            int iTrig = Array.IndexOf(ehdr, "trigger");
            int iState = Array.IndexOf(ehdr, "probeState");
            int iMins = Array.IndexOf(ehdr, "minsToEntry");
            int iStop = Array.IndexOf(ehdr, "stopPts");
            int iEntry = Array.IndexOf(ehdr, "entryPrice");

            bool immediateAtZero = false, pullbackLater = false, allStopsPositive = true;
            for (int r = 0; r < erows.Count; r++)
            {
                string[] c = erows[r].Split(',');
                if (c[iState] != "TRIGGERED") continue;
                double sp = Num(c[iStop]);
                if (!double.IsNaN(sp) && sp <= 0) allStopsPositive = false;
                if (c[iTrig] == "IMMEDIATE" && c[iMins] == "0") immediateAtZero = true;
                if (c[iTrig] == "PULLBACK_RECLAIM" && Num(c[iMins]) > 0) pullbackLater = true;
                Check(!double.IsNaN(Num(c[iEntry])), "a triggered probe has an entry price");
            }
            Check(erows.Count > 0, "entry-resolution rows were written");
            Check(immediateAtZero,
                  "same-timeframe IMMEDIATE execution fills at the close of the break bar, not later");
            Check(pullbackLater,
                  "PULLBACK_RECLAIM fills only after price returned to the level and reclaimed it");
            Check(allStopsPositive, "every structural stop is a positive distance from the entry");

            // no entry row may claim a fill before its parent event
            string[] shdr = V4ResearchEngine.StructureCsvHeader().Split(',');
            int iEid = Array.IndexOf(shdr, "eventId");
            Dictionary<string, bool> known = new Dictionary<string, bool>();
            for (int r = 0; r < srows.Count; r++) known[srows[r].Split(',')[iEid]] = true;
            bool allJoin = true;
            for (int r = 0; r < erows.Count; r++)
                if (!known.ContainsKey(erows[r].Split(',')[0])) allJoin = false;
            Check(allJoin, "every entry row joins to a structure row on eventId");
        }

        // ====================================================================
        /// A capture whose header and rows disagree by even one column silently
        /// shifts every downstream statistic, so the shape is asserted directly.
        private static void CsvShape()
        {
            List<string> srows = new List<string>(), erows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(
                delegate(string r) { srows.Add(r); }, delegate(string r) { erows.Add(r); });
            eng.ControlSampleRate = 3;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);
            V4StructureTracker t15 = new V4StructureTracker("15m", 15);
            t15.ConfirmBars = 1; t15.PivotLeftBars = 1; t15.AtrPeriod = 5;
            eng.AddTracker(t15);

            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            Random rng = new Random(7);
            double p = 20000;
            for (int i = 0; i < 400; i++)
            {
                p += rng.Next(-8, 9);
                V4Bar b = B(s.AddMinutes(i), 1, p, p + 4, p - 4, p + rng.Next(-3, 4));
                eng.OnStructureBar("1m", b);
                if (i % 15 == 14)
                    eng.OnStructureBar("15m", B(s.AddMinutes(i - 14), 15, p, p + 12, p - 12, p));
                eng.OnOneMinuteBar(b);
            }
            eng.Finish();

            int sCols = V4ResearchEngine.StructureCsvHeader().Split(',').Length;
            int eCols = V4ResearchEngine.EntryCsvHeader().Split(',').Length;
            bool sOk = srows.Count > 0, eOk = erows.Count > 0;
            for (int r = 0; r < srows.Count; r++) if (srows[r].Split(',').Length != sCols) sOk = false;
            for (int r = 0; r < erows.Count; r++) if (erows[r].Split(',').Length != eCols) eOk = false;
            Check(sOk, "every structure row has exactly as many fields as the header");
            Check(eOk, "every entry row has exactly as many fields as the header");

            // controls must exist and must exist on BOTH sides, or "is a break
            // different from a non-break" is not an answerable question
            string[] hdr = V4ResearchEngine.StructureCsvHeader().Split(',');
            int iKind = Array.IndexOf(hdr, "eventKind"), iSide = Array.IndexOf(hdr, "side");
            bool cUp = false, cDn = false;
            for (int r = 0; r < srows.Count; r++)
            {
                string[] c = srows[r].Split(',');
                if (c[iKind] != "CONTROL") continue;
                if (c[iSide] == "UP") cUp = true; else cDn = true;
            }
            Check(cUp && cDn, "controls are emitted in both directions");
            Check(eng.ControlsEmitted > 0 && eng.BreaksEmitted > 0,
                  "the capture contains both breaks and controls");

            // the month router must read the row's OWN date, not the clock
            Check(V4ResearchEngine.MonthKeyFromRow("MNQ-15m-20260302093000-U,MNQ,BREAK") == "2026-03",
                  "a row is routed to the month inside its own eventId");
            Check(V4ResearchEngine.MonthKeyFromRow("garbage") == "unknown",
                  "an unrecognised row is routed to 'unknown' rather than guessed at");

            // no duplicate ids within one direction on one timeframe
            int iEid = Array.IndexOf(hdr, "eventId");
            Dictionary<string, int> seen = new Dictionary<string, int>();
            bool dup = false;
            for (int r = 0; r < srows.Count; r++)
            {
                string id = srows[r].Split(',')[iEid];
                if (seen.ContainsKey(id)) dup = true;
                seen[id] = 1;
            }
            Check(!dup, "event ids are unique within a capture");
        }

        // ====================================================================
        /// Regression tests for two defects found on the first real MNQ capture.
        ///
        /// DEFECT 1  net_H was filled only when the elapsed minute count EQUALLED
        ///           the horizon exactly. Any session gap - the 17:00 ET halt, a
        ///           weekend, a holiday - stepped the counter straight over the
        ///           mark and left the column empty. In a live month that emptied
        ///           net_240m on 79% of entry rows, and the hole was concentrated
        ///           near session boundaries, so it was biased as well as missing.
        ///
        /// DEFECT 2  A probe stayed armed for the parent's whole forward window,
        ///           so an entry could fill on the far side of a weekend - one did
        ///           so 3181 minutes after its break - and a probe that filled
        ///           late had its own measurement window truncated to whatever
        ///           the parent had left.
        private static void HorizonsAcrossGaps()
        {
            List<string> srows = new List<string>(), erows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(
                delegate(string r) { srows.Add(r); }, delegate(string r) { erows.Add(r); });
            eng.ControlSampleRate = 0;
            eng.MaxEntryDelayMinutes = 60;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);

            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            double[] hi = { 100, 104, 112, 108, 106, 105, 104, 103, 102, 101, 120 };
            double[] lo = { 95, 99, 107, 103, 101, 100, 99, 98, 97, 96, 100 };
            double[] cl = { 99, 103, 111, 105, 103, 102, 101, 100, 99, 98, 119 };
            for (int i = 0; i < hi.Length; i++)
            {
                V4Bar b = B(s.AddMinutes(i), 1, cl[i] - 1, hi[i], lo[i], cl[i]);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            // Ten minutes of trading, then a HOLE that jumps clean over every
            // remaining horizon - exactly what a weekend does to the clock.
            for (int i = 0; i < 10; i++)
            {
                V4Bar b = B(s.AddMinutes(11 + i), 1, 119 + i, 121 + i, 118 + i, 120 + i);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            for (int i = 0; i < 5; i++)
            {
                V4Bar b = B(s.AddMinutes(4000 + i), 1, 200, 202, 198, 201);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            eng.Finish();

            string[] hdr = V4ResearchEngine.StructureCsvHeader().Split(',');
            int iKind = Array.IndexOf(hdr, "eventKind");
            int[] hcol = new int[V4ResearchEngine.HorizonMinutes.Length];
            for (int i = 0; i < hcol.Length; i++)
                hcol[i] = Array.IndexOf(hdr, "net_" + V4ResearchEngine.HorizonMinutes[i] + "m");

            bool everyHorizonFilled = srows.Count > 0;
            for (int r = 0; r < srows.Count; r++)
            {
                string[] c = srows[r].Split(',');
                if (c[iKind] != "BREAK") continue;
                for (int i = 0; i < hcol.Length; i++)
                    if (c[hcol[i]].Length == 0) everyHorizonFilled = false;
            }
            Check(everyHorizonFilled,
                  "every net_H column is filled even when a session gap steps over the horizon");

            string[] ehdr = V4ResearchEngine.EntryCsvHeader().Split(',');
            int iState = Array.IndexOf(ehdr, "probeState");
            int iMins = Array.IndexOf(ehdr, "minsToEntry");
            int iObs = Array.IndexOf(ehdr, "minutesObserved");
            int iNet240 = Array.IndexOf(ehdr, "netR_240m");

            bool noLateFill = true, fullWindow = erows.Count > 0, net240Filled = erows.Count > 0;
            for (int r = 0; r < erows.Count; r++)
            {
                string[] c = erows[r].Split(',');
                if (c[iState] != "TRIGGERED") continue;
                if (Num(c[iMins]) > 60) noLateFill = false;
                if (Num(c[iObs]) < 240) fullWindow = false;
                if (c[iNet240].Length == 0) net240Filled = false;
            }
            Check(noLateFill,
                  "no probe fills after the entry window, however long the gap that follows");
            Check(fullWindow,
                  "a probe that fills inside the window still gets its own full 240 minutes");
            Check(net240Filled,
                  "netR_240m is populated on every triggered probe, not only exact-minute ones");
        }

        // ====================================================================
        private static void OrderFlow()
        {
            List<string> rows = new List<string>();
            V4OrderFlowEngine of = new V4OrderFlowEngine(delegate(string r) { rows.Add(r); });
            of.TickSize = 0.25;
            of.Audit.MinBars = 3;
            of.ImbalanceMinVolume = 0;

            DateTime s = new DateTime(2026, 3, 2, 9, 30, 0);
            V4FootprintBar b1 = Foot(s, 20000, 20001, 19999.5, 20000.75, 300);
            AddLvl(b1, 19999.5, 20, 60);
            AddLvl(b1, 19999.75, 30, 40);
            AddLvl(b1, 20000.0, 50, 20);
            AddLvl(b1, 20000.25, 40, 10);
            AddLvl(b1, 20000.5, 20, 5);
            AddLvl(b1, 20000.75, 5, 0);
            of.OnBar(b1);

            Check(Math.Abs(b1.Delta - (b1.AskTotal - b1.BidTotal)) < 1e-9,
                  "bar delta is exactly ask minus bid, recomputed from the levels in the file");
            Check(rows.Count == 1, "one row per volumetric bar");

            string[] hdr = V4OrderFlowEngine.CsvHeader().Split(',');
            string[] c = rows[0].Split(',');
            Check(c.Length == hdr.Length, "the order-flow row matches its header exactly");
            int iDelta = Array.IndexOf(hdr, "barDelta");
            int iCum = Array.IndexOf(hdr, "cumDeltaDay");
            int iQ = Array.IndexOf(hdr, "quality");
            int iPoc = Array.IndexOf(hdr, "pocPrice");
            Check(Math.Abs(Num(c[iDelta]) - b1.Delta) < 1e-6, "the delta column is the recomputed delta");
            Check(Math.Abs(Num(c[iCum]) - b1.Delta) < 1e-6, "cumulative delta starts from the day's first bar");
            Check(Math.Abs(Num(c[iPoc]) - 19999.5) < 1e-9, "the POC is the price with the most executed volume");
            Check(c[iQ] == "VOLUME_MISMATCH" || c[iQ] == "OK",
                  "each bar carries its own data-quality flag");

            // cumulative delta resets at 18:00 ET, deterministically
            V4FootprintBar b2 = Foot(new DateTime(2026, 3, 2, 18, 1, 0), 20000, 20001, 19999, 20000, 100);
            AddLvl(b2, 20000, 60, 40);
            of.OnBar(b2);
            string[] c2 = rows[rows.Count - 1].Split(',');
            Check(Math.Abs(Num(c2[iCum]) - 20) < 1e-6,
                  "cumulative delta resets at the 18:00 ET exchange-day boundary");

            // ---- the gate ---------------------------------------------------
            V4OrderFlowEngine bad = new V4OrderFlowEngine(delegate(string r) { });
            bad.Audit.MinBars = 2;
            for (int i = 0; i < 5; i++)
            {
                V4FootprintBar nb = Foot(s.AddMinutes(i), 20000, 20001, 19999, 20000, 100);
                nb.HasLevels = false;              // the platform gave nothing
                bad.OnBar(nb);
            }
            Check(!bad.Audit.Passed,
                  "a history with no per-price volume FAILS the data-quality gate");
            Check(bad.Audit.BarsNoLevels == 5 && bad.Audit.LevelCoveragePct == 0,
                  "the audit counts missing levels rather than skipping them");
            Check(bad.Audit.Report().Contains("FAILED"),
                  "the audit report states the verdict in words, not only in numbers");

            V4OrderFlowEngine good = new V4OrderFlowEngine(delegate(string r) { });
            good.TickSize = 0.25; good.Audit.MinBars = 5;
            for (int i = 0; i < 10; i++)
            {
                V4FootprintBar nb = Foot(s.AddMinutes(i), 20000, 20001, 19999, 20000, 100);
                AddLvl(nb, 20000, 60, 40);
                good.OnBar(nb);
            }
            Check(good.Audit.Passed, "a complete, reconciling history PASSES the gate");
            Check(good.Audit.Report().Contains("PASSED"), "a passing audit says so");

            // off-grid prices are a reconstruction failure, not a rounding detail
            V4OrderFlowEngine grid = new V4OrderFlowEngine(delegate(string r) { });
            grid.TickSize = 0.25; grid.Audit.MinBars = 1;
            V4FootprintBar og = Foot(s, 20000, 20001, 19999, 20000, 100);
            AddLvl(og, 20000.13, 60, 40);
            grid.OnBar(og);
            Check(grid.Audit.BarsOffTickGrid == 1 && !grid.Audit.Passed,
                  "price levels off the instrument's tick grid fail the gate");
        }

        // ====================================================================
        /// The daily halt and the weekend are not missing data.
        ///
        /// The first version of this check asked whether the bar BEFORE the gap
        /// closed at 16:59 ET. NinjaTrader stamps a bar with its CLOSE time, so
        /// the last bar before the halt is stamped 17:00 - the test never fired.
        /// On the first real MNQ month it reported 22 gaps as missing data when
        /// the true count was zero: every ordinary trading day, plus the
        /// weekends, plus a holiday early close.
        private static void SessionBoundaries()
        {
            // Each scenario gets its OWN engine. Sharing one would make the jump
            // BETWEEN scenarios look like a gap and score the case it was meant
            // to test - the fixture would be measuring itself.
            Check(GapsFor(new DateTime(2026, 7, 1, 16, 59, 0),
                          new DateTime(2026, 7, 1, 18, 0, 0)) == 0,
                  "the 17:00-18:00 ET daily halt is a session boundary, not missing data");

            Check(GapsFor(new DateTime(2026, 7, 3, 16, 59, 0),
                          new DateTime(2026, 7, 5, 18, 0, 0)) == 0,
                  "the weekend is a session boundary too");

            Check(GapsFor(new DateTime(2026, 7, 3, 12, 59, 0),
                          new DateTime(2026, 7, 5, 18, 0, 0)) == 0,
                  "an early close before a holiday needs no calendar - the reopen identifies it");

            Check(GapsFor(new DateTime(2026, 7, 6, 10, 0, 0),
                          new DateTime(2026, 7, 6, 10, 30, 0)) == 1,
                  "a 30-minute hole inside the session is still reported as missing data");

            // The CME equity-index afternoon pause, 16:15-16:30 ET. On real MNQ
            // data this fires on essentially every weekday - 436 gaps of exactly
            // 16:15 -> 16:31 in one sample - so failing to recognise it reported
            // the whole history as broken.
            Check(GapsFor(new DateTime(2026, 7, 6, 16, 14, 0),
                          new DateTime(2026, 7, 6, 16, 30, 0)) == 0,
                  "the 16:15-16:30 ET maintenance halt is a session boundary");

            // A quiet overnight minute is not a missing one. NinjaTrader prints
            // no bar when nothing trades, so a three-minute skip at 02:00 means
            // the market was silent, not that the history lost anything.
            Check(GapsFor(new DateTime(2026, 7, 7, 2, 0, 0),
                          new DateTime(2026, 7, 7, 2, 3, 0)) == 0,
                  "a sub-5-minute overnight skip is a quiet minute, not missing data");
            Check(QuietFor(new DateTime(2026, 7, 7, 2, 0, 0),
                           new DateTime(2026, 7, 7, 2, 3, 0)) == 1,
                  "quiet minutes are still counted, just counted separately");

            Check(GapsFor(new DateTime(2026, 7, 6, 10, 0, 0),
                          new DateTime(2026, 7, 6, 10, 1, 0)) == 0,
                  "consecutive bars are not a gap");

            V4OrderFlowAudit a = new V4OrderFlowAudit();
            Check(a.IsSessionBoundary(new DateTime(2026, 7, 6, 18, 0, 0))
                  && a.IsSessionBoundary(new DateTime(2026, 7, 6, 18, 5, 0))
                  && !a.IsSessionBoundary(new DateTime(2026, 7, 6, 19, 0, 0))
                  && !a.IsSessionBoundary(new DateTime(2026, 7, 6, 17, 0, 0)),
                  "the boundary test keys on the reopen hour, not on the bar before the gap");
        }

        // ====================================================================
        /// A probe must never fill outside the entry window, whatever path the
        /// fill arrives by.
        ///
        /// The caller-side expiry was correct and still ran, but it needed a bar
        /// to arrive on some tracked timeframe between the event and the fill.
        /// On a holiday half-day the market closes early and the next bar is the
        /// Sunday reopen, so the first bar the probe saw after the event WAS the
        /// fill candidate - and it filled, 3,446 minutes later, on a break from
        /// the previous Friday morning. 6.8% of real fills were beyond the
        /// window this way. The guard now sits inside the fill itself.
        private static void EntryWindowGuard()
        {
            List<string> srows = new List<string>(), erows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(
                delegate(string r) { srows.Add(r); }, delegate(string r) { erows.Add(r); });
            eng.ControlSampleRate = 0;
            eng.MaxEntryDelayMinutes = 60;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);

            DateTime s = new DateTime(2026, 4, 3, 9, 30, 0);   // a Friday
            double[] hi = { 100, 104, 112, 108, 106, 105, 104, 103, 102, 101, 120 };
            double[] lo = {  95,  99, 107, 103, 101, 100,  99,  98,  97,  96, 100 };
            double[] cl = {  99, 103, 111, 105, 103, 102, 101, 100,  99,  98, 119 };
            for (int i = 0; i < hi.Length; i++)
            {
                V4Bar b = B(s.AddMinutes(i), 1, cl[i] - 1, hi[i], lo[i], cl[i]);
                eng.OnStructureBar("1m", b);
                eng.OnOneMinuteBar(b);
            }

            // The market now closes early. The NEXT bar is the Sunday reopen,
            // two and a half days later - and it closes beyond the broken level,
            // so it is a fill candidate for every still-armed probe.
            DateTime reopen = new DateTime(2026, 4, 5, 18, 1, 0);
            for (int i = 0; i < 300; i++)
            {
                V4Bar b = B(reopen.AddMinutes(i), 1, 125 + i, 126 + i, 124 + i, 125 + i);
                eng.OnStructureBar("1m", b);
                eng.OnOneMinuteBar(b);
            }
            eng.Finish();

            string[] hdr = V4ResearchEngine.EntryCsvHeader().Split(',');
            int iState = Array.IndexOf(hdr, "probeState");
            int iMins = Array.IndexOf(hdr, "minsToEntry");
            int worst = -1, filled = 0;
            for (int r = 0; r < erows.Count; r++)
            {
                string[] c = erows[r].Split(',');
                if (c[iState] != "TRIGGERED") continue;
                filled++;
                int m = int.Parse(c[iMins]);
                if (m > worst) worst = m;
            }
            Check(erows.Count > 0, "the holiday-gap fixture produced entry rows");
            Check(worst <= 60,
                  "no probe fills across a weekend gap - the entry window is enforced at the fill");
            Check(filled == 0 || worst >= 0,
                  "a fill that does happen still reports a sane delay");

            // and the ordinary case still fills
            Check(GapFillMinutes(30) == 30, "a fill 30 minutes after the break is allowed");
            Check(GapFillMinutes(90) < 0, "a fill 90 minutes after the break is refused");
        }

        /// Builds a break, then offers the first fill candidate delayMin later.
        /// Returns the delay actually recorded, or -1 if nothing filled.
        private static int GapFillMinutes(int delayMin)
        {
            List<string> erows = new List<string>();
            V4ResearchEngine eng = new V4ResearchEngine(
                delegate(string r) { }, delegate(string r) { erows.Add(r); });
            eng.ControlSampleRate = 0;
            eng.MaxEntryDelayMinutes = 60;
            V4StructureTracker t = new V4StructureTracker("1m", 1);
            t.ConfirmBars = 1; t.PivotLeftBars = 1; t.AtrPeriod = 5;
            eng.AddTracker(t);

            DateTime s = new DateTime(2026, 4, 6, 9, 30, 0);
            // The break bar WICKS through and closes back. A bar that closed
            // beyond would fill the same-timeframe IMMEDIATE probe at its own
            // close, minsToEntry 0, and the fixture could never observe a delay
            // at all - it would be measuring the wrong thing and passing.
            double[] hi = { 100, 104, 112, 108, 106, 105, 104, 103, 102, 101, 120 };
            double[] lo = {  95,  99, 107, 103, 101, 100,  99,  98,  97,  96, 100 };
            double[] cl = {  99, 103, 111, 105, 103, 102, 101, 100,  99,  98, 108 };
            for (int i = 0; i < hi.Length; i++)
            {
                V4Bar b = B(s.AddMinutes(i), 1, cl[i] - 1, hi[i], lo[i], cl[i]);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            // sit below the level so nothing fills, then pop above it
            for (int i = 0; i < delayMin - 1; i++)
            {
                V4Bar b = B(s.AddMinutes(11 + i), 1, 108, 109, 107, 108);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            for (int i = 0; i < 300; i++)
            {
                V4Bar b = B(s.AddMinutes(11 + delayMin - 1 + i), 1, 125 + i, 126 + i, 124 + i, 125 + i);
                eng.OnStructureBar("1m", b); eng.OnOneMinuteBar(b);
            }
            eng.Finish();

            string[] hdr = V4ResearchEngine.EntryCsvHeader().Split(',');
            int iState = Array.IndexOf(hdr, "probeState"), iMins = Array.IndexOf(hdr, "minsToEntry");
            int iTrig = Array.IndexOf(hdr, "trigger");
            for (int r = 0; r < erows.Count; r++)
            {
                string[] c = erows[r].Split(',');
                if (c[iState] == "TRIGGERED" && c[iTrig] == "IMMEDIATE")
                {
                    int m = int.Parse(c[iMins]);
                    if (m > 0) return m;
                }
            }
            return -1;
        }

        /// Quiet-minute count for the same two-bar fixture.
        private static long QuietFor(DateTime a, DateTime b)
        {
            V4OrderFlowEngine of = new V4OrderFlowEngine(delegate(string r) { });
            of.OnBar(Foot(a, 100, 101, 99, 100, 10));
            of.OnBar(Foot(b, 100, 101, 99, 100, 10));
            return of.Audit.ShortNoTradeGaps;
        }

        /// Feeds exactly two bars to a fresh engine and returns the gap count.
        private static long GapsFor(DateTime firstBarOpen, DateTime secondBarOpen)
        {
            V4OrderFlowEngine of = new V4OrderFlowEngine(delegate(string r) { });
            of.OnBar(Foot(firstBarOpen, 100, 101, 99, 100, 10));
            of.OnBar(Foot(secondBarOpen, 100, 101, 99, 100, 10));
            return of.Audit.BarsAfterGap;
        }

        private static V4FootprintBar Foot(DateTime open, double o, double h, double l, double c, double v)
        {
            V4FootprintBar b = new V4FootprintBar();
            b.EtOpen = open; b.EtClose = open.AddMinutes(1);
            b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = v;
            return b;
        }

        private static void AddLvl(V4FootprintBar b, double price, double ask, double bid)
        {
            V4FootprintLevel l = new V4FootprintLevel();
            l.Price = price; l.AskVolume = ask; l.BidVolume = bid;
            b.Levels.Add(l);
            b.HasLevels = true;
        }

        private static double Num(string s)
        {
            double d;
            return double.TryParse(s, NumberStyles.Float, CultureInfo.InvariantCulture, out d)
                ? d : double.NaN;
        }
    }
}
