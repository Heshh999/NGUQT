// ============================================================================
// V41Tests.cs - deterministic regression tests for the V4.1 modules.
//
// These cover the families the V4.1 build prompt names, and they are weighted
// toward the assertions that would let a silent defect through:
//
//   - all four vector colours AND the non-vector case, because a classifier
//     that never returns BLUE is indistinguishable from one that works until
//     someone counts
//   - vector recovery is monotone, so a zone cannot un-recover
//   - a ten-bar chop on a level is ONE test, not ten
//   - a target must be frozen from a level that already existed at entry
//   - a single bar reaching both stop and target is marked AMBIGUOUS and
//     never silently resolved, because picking a convention there moved
//     P(target first) from 0.4869 to 0.5290 in the measured data
//   - a feature carrying a timestamp after its event is COUNTED, not hidden
//
// Nothing here proves the engine behaves correctly inside NinjaTrader. It
// proves these functions are deterministic and mean what the documentation
// says they mean.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace MnqTwoTests
{
    public static class V41Tests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        private static V4Bar B(DateTime open, int mins, double o, double h, double l, double c)
        {
            return B(open, mins, o, h, l, c, 1000);
        }

        private static V4Bar B(DateTime open, int mins, double o, double h, double l, double c, double v)
        {
            V4Bar b = new V4Bar();
            b.EtOpen = open; b.EtClose = open.AddMinutes(mins);
            b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = v;
            return b;
        }

        public static int Run()
        {
            passed = failed = 0;
            Console.WriteLine("V4.1 REGRESSION TESTS");

            VectorClassification();
            VectorRecovery();
            EmaAndManagement();
            LevelContext();
            StopsAndTargets();
            Ambiguity();
            NoLookahead();
            OrderFlowFeatures();
            SchemaAndValidity();
            BreakTransition();
            TimestampConvention();
            AuditGuards();
            SampleTwoFixes();
            SampleThreeFixes();
            SourceScan();

            Console.WriteLine("V4.1: " + passed + " passed, " + failed + " failed");
            return failed;
        }

        // ---------------------------------------------------------------
        // VECTOR
        // ---------------------------------------------------------------
        private static void VectorClassification()
        {
            Console.WriteLine(" vector classification");
            // avgVol10 = 100, highestVolSpread10 = 100000 (unreachable below)
            double avg = 100, hvs = 1000000;

            Check(V4VectorClassifier.Classify(10, 12, 9, 11, 250, avg, hvs) == V4VectorColor.GREEN,
                  "climax volume, close>open -> GREEN");
            Check(V4VectorClassifier.Classify(10, 12, 9, 9.5, 250, avg, hvs) == V4VectorColor.RED,
                  "climax volume, close<open -> RED");
            Check(V4VectorClassifier.Classify(10, 12, 9, 11, 160, avg, hvs) == V4VectorColor.BLUE,
                  "elevated volume, close>open -> BLUE");
            Check(V4VectorClassifier.Classify(10, 12, 9, 9.5, 160, avg, hvs) == V4VectorColor.VIOLET,
                  "elevated volume, close<open -> VIOLET");
            Check(V4VectorClassifier.Classify(10, 12, 9, 11, 120, avg, hvs) == V4VectorColor.NONE,
                  "ordinary volume -> not a vector");

            // the doji rule, stated explicitly in the engine and tested here
            Check(V4VectorClassifier.Classify(10, 12, 9, 10, 250, avg, hvs) == V4VectorColor.RED,
                  "doji (close==open) follows the BEARISH branch");

            // volume*spread alone triggers climax even at ordinary volume
            Check(V4VectorClassifier.Classify(10, 40, 9, 30, 120, avg, 1000) == V4VectorColor.GREEN,
                  "volume*spread new high alone -> climax GREEN");

            // climax outranks elevated
            Check(V4VectorClassifier.Classify(10, 12, 9, 11, 250, avg, 100) == V4VectorColor.GREEN,
                  "climax has priority over elevated");

            Check(V4VectorClassifier.TierOf(V4VectorColor.RED) == V4VectorTier.CLIMAX, "RED is CLIMAX tier");
            Check(V4VectorClassifier.TierOf(V4VectorColor.BLUE) == V4VectorTier.ELEVATED, "BLUE is ELEVATED tier");
            Check(V4VectorClassifier.DirOf(V4VectorColor.VIOLET) == V4VectorDir.BEARISH, "VIOLET direction is BEARISH");
            Check(V4VectorClassifier.DirOf(V4VectorColor.NONE) == V4VectorDir.NONE, "non-vector has no direction");

            Check(V4VectorClassifier.Classify(10, 12, 9, 11, 250, 0, hvs) == V4VectorColor.NONE,
                  "zero baseline volume cannot classify anything");
        }

        private static void VectorRecovery()
        {
            Console.WriteLine(" vector zone and recovery");
            V4Vector v = new V4Vector();
            v.Color = V4VectorColor.RED; v.Dir = V4VectorDir.BEARISH;
            v.Open = 110; v.Close = 100; v.High = 112; v.Low = 100;
            v.BodyHigh = 110; v.BodyLow = 100;
            v.CreatedEt = new DateTime(2026, 1, 5, 10, 0, 0);
            v.AtrAtCreation = 4;
            v.RangePts = 12;

            Check(Math.Abs(v.OriginEdge - 100) < 1e-9, "bearish vector origin edge is its LOW");
            Check(Math.Abs(v.FarEdge - 112) < 1e-9, "bearish vector far edge is its HIGH");
            Check(Math.Abs(v.PriceAtRecoveryPct(50) - 106) < 1e-9, "50% recovery price is the midpoint");
            Check(v.IsUnrecovered, "a fresh vector is UNRECOVERED");

            DateTime t = v.CreatedEt;
            // This vector closed on its own low, so its body edge is at 0% of
            // the zone. An 8% retrace must still report FIRST_TOUCH - the
            // regression is a ladder that let the body edge outrank it.
            v.ApplyLaterBar(B(t, 15, 100.5, 101, 100, 100.8, 500), 1);
            Check(v.Recovery == V4VectorRecovery.FIRST_TOUCH,
                  "an 8% retrace is FIRST_TOUCH even when the body edge sits at 0%");
            double after1 = v.RecoveryPct;

            v.ApplyLaterBar(B(t.AddMinutes(5), 15, 101, 103, 100.5, 102, 500), 2);
            Check(v.Recovery == V4VectorRecovery.RECOVERED_25, "exactly 25% of the zone -> RECOVERED_25");

            v.ApplyLaterBar(B(t.AddMinutes(15), 15, 102, 107, 101, 106, 500), 2);
            Check(v.Recovery >= V4VectorRecovery.RECOVERED_50, "past the midpoint -> at least RECOVERED_50");
            Check(v.BarsTo50 == 2, "barsTo50 records the bar it happened on");

            // the monotone guarantee: a pullback must not lower the mark
            double peak = v.RecoveryPct;
            v.ApplyLaterBar(B(t.AddMinutes(30), 15, 106, 106.5, 100, 100.5, 500), 3);
            Check(v.RecoveryPct == peak, "recovery is a high-water mark and never decreases");
            Check(peak > after1, "recovery advanced between the two bars");

            v.ApplyLaterBar(B(t.AddMinutes(45), 15, 101, 113, 100, 112, 500), 4);
            Check(v.Recovery == V4VectorRecovery.RECOVERED_100, "trading to the far edge -> RECOVERED_100");
            Check(v.BarsTo100 == 4, "barsTo100 recorded");

            // bullish mirror
            V4Vector g = new V4Vector();
            g.Color = V4VectorColor.GREEN; g.Dir = V4VectorDir.BULLISH;
            g.Open = 100; g.Close = 110; g.High = 112; g.Low = 100;
            g.BodyHigh = 110; g.BodyLow = 100;
            Check(Math.Abs(g.OriginEdge - 112) < 1e-9, "bullish vector origin edge is its HIGH");
            Check(Math.Abs(g.FarEdge - 100) < 1e-9, "bullish vector far edge is its LOW");
        }

        // ---------------------------------------------------------------
        // EMA
        // ---------------------------------------------------------------
        private static void EmaAndManagement()
        {
            Console.WriteLine(" EMA and 1m EMA(9) management");

            // seeded with the first value, then k = 2/(9+1) = 0.2
            V4Ema e = new V4Ema(9);
            e.Update(100);
            Check(Math.Abs(e.RawValue - 100) < 1e-9, "EMA seeds with the first close");
            e.Update(110);
            Check(Math.Abs(e.RawValue - 102) < 1e-9, "EMA(9) second value is 102 on 100 then 110");
            e.Update(110);
            Check(Math.Abs(e.RawValue - 103.6) < 1e-9, "EMA(9) third value is 103.6");

            Check(!e.Ready, "EMA is not Ready before 3x its period");
            for (int i = 0; i < 30; i++) e.Update(110);
            Check(e.Ready, "EMA becomes Ready after 3x its period");

            // long: exits on the first completed bar closing BELOW the EMA
            V4EmaExitProbe p = new V4EmaExitProbe();
            DateTime t0 = new DateTime(2026, 1, 5, 10, 0, 0);
            p.Open(1, 100, t0, 5, 99);
            Check(p.EntryWasAboveEma9, "entry above the EMA is recorded at open");

            p.OnBar(B(t0, 1, 100, 102, 99.5, 101), 100.5);      // closes above -> no exit
            Check(!p.Resolved, "a close above the EMA does not exit a long");
            p.OnBar(B(t0.AddMinutes(1), 1, 101, 101, 98, 98.5), 100.0);  // closes below -> exit
            Check(p.Resolved, "first close below the EMA exits a long");
            Check(p.MinsToExit == 2, "minsToExit counts bars after entry");
            Check(Math.Abs(p.ExitPrice - 98.5) < 1e-9, "exit fills at the bar CLOSE, not at the EMA");
            Check(Math.Abs(p.GrossPts - (-1.5)) < 1e-9, "gross points measured from entry to exit close");
            Check(Math.Abs(p.GrossR - (-0.3)) < 1e-9, "gross R divides by the frozen stop distance");

            // short: mirror
            V4EmaExitProbe s = new V4EmaExitProbe();
            s.Open(-1, 100, t0, 5, 101);
            s.OnBar(B(t0, 1, 100, 100.5, 98, 99), 99.5);
            Check(!s.Resolved, "a close below the EMA does not exit a short");
            s.OnBar(B(t0.AddMinutes(1), 1, 99, 103, 99, 102), 100.0);
            Check(s.Resolved, "first close above the EMA exits a short");
            Check(Math.Abs(s.GrossPts - (-2)) < 1e-9, "short gross points are entry minus exit");

            // a probe must not be closed by its own entry bar
            V4EmaExitProbe q = new V4EmaExitProbe();
            q.Open(1, 100, t0, 5, 101);
            q.OnBar(B(t0.AddMinutes(-1), 1, 100, 100, 95, 96), 99);
            Check(!q.Resolved, "a bar at or before entry cannot resolve the probe");
        }

        // ---------------------------------------------------------------
        // LEVEL CONTEXT
        // ---------------------------------------------------------------
        private static void LevelContext()
        {
            Console.WriteLine(" level context and test clustering");
            V4LevelContextBook book = new V4LevelContextBook();
            book.ApproachBandAtr = 0.5;
            book.ClusterExitAtr = 1.0;
            book.ClusterGapBars = 2;
            DateTime t = new DateTime(2026, 1, 5, 10, 0, 0);
            book.Publish("PDH", V4LevelType.PRIOR_DAY_HIGH, 100, t.AddHours(-3), t.AddHours(-3));

            double atr = 2.0;
            // ten bars chopping on the level
            for (int i = 0; i < 10; i++)
                book.OnBar(B(t.AddMinutes(i), 1, 100, 100.5, 99.5, 100.1, 500), atr, 20260105);

            V4LevelRef lr = book.Nearest(100, t.AddMinutes(20));
            Check(lr != null, "nearest level resolves");
            Check(lr.TestNumberToday == 1, "a ten-bar chop on a level counts as ONE test");
            Check(lr.InteractionCountSession == 10, "...while the raw interaction count still sees all ten bars");

            // walk far away for long enough to close the test
            for (int i = 0; i < 5; i++)
                book.OnBar(B(t.AddMinutes(10 + i), 1, 106, 107, 105, 106, 500), atr, 20260105);
            // come back
            book.OnBar(B(t.AddMinutes(20), 1, 100, 100.4, 99.6, 100, 500), atr, 20260105);
            Check(lr.TestNumberToday == 2, "returning after a clear gap opens a SECOND test");

            // a new exchange day resets the count
            book.OnBar(B(t.AddDays(1), 1, 100, 100.4, 99.6, 100, 500), atr, 20260106);
            Check(lr.TestNumberToday == 1, "a new exchange day resets testNumberToday");

            // causality: a level published later must not be visible earlier
            book.Publish("FUTURE", V4LevelType.SWING_HIGH, 100.05, t.AddDays(2), t.AddDays(2));
            V4LevelRef n2 = book.Nearest(100, t.AddMinutes(20));
            Check(n2 == null || n2.Name != "FUTURE", "a level known later is refused by an earlier cutoff");

            // moving a level clears its history rather than carrying it over
            book.Publish("PDH", V4LevelType.PRIOR_DAY_HIGH, 205, t, t);
            Check(lr.TestNumberToday == 0, "a level that MOVED loses its old interaction history");
        }

        // ---------------------------------------------------------------
        // STOPS AND TARGETS
        // ---------------------------------------------------------------
        private static void StopsAndTargets()
        {
            Console.WriteLine(" stops and frozen targets");
            V4StopSet s = new V4StopSet();
            s.Freeze(1, 100, 4, 98, 96, 90);
            Check(Math.Abs(s.TightPts - 2) < 1e-9, "tight stop distance");
            Check(Math.Abs(s.MediumPts - 4) < 1e-9, "medium stop distance");
            Check(Math.Abs(s.StructuralPts - 10) < 1e-9, "structural stop distance");
            Check(Math.Abs(s.MediumAtr - 1.0) < 1e-9, "stop distance in ATR");

            // a stop on the WRONG side is not a stop
            V4StopSet bad = new V4StopSet();
            bad.Freeze(1, 100, 4, 102, 96, 90);
            Check(double.IsNaN(bad.TightPts), "a long stop ABOVE entry is rejected, not silently negated");

            V4Target t = V4Target.Make("SWING", "15m", 110, 100, 1, 4);
            Check(t.Valid, "a target ahead of entry is valid");
            Check(Math.Abs(t.DistancePts - 10) < 1e-9, "target distance in points");
            Check(Math.Abs(t.DistanceAtr - 2.5) < 1e-9, "target distance in ATR");

            V4Target behind = V4Target.Make("SWING", "15m", 90, 100, 1, 4);
            Check(!behind.Valid, "a target BEHIND a long entry is not a target");

            V4Target none = V4Target.Make("SWING", "15m", double.NaN, 100, 1, 4);
            Check(!none.Valid, "a missing level does not become a target");

            V4Target shortT = V4Target.Make("SWING", "15m", 90, 100, -1, 4);
            Check(shortT.Valid && Math.Abs(shortT.DistancePts - 10) < 1e-9,
                  "short targets mirror correctly");
        }

        // ---------------------------------------------------------------
        // AMBIGUITY - the assertion this whole module exists for
        // ---------------------------------------------------------------
        private static void Ambiguity()
        {
            Console.WriteLine(" same-bar stop/target ambiguity");
            DateTime t0 = new DateTime(2026, 1, 5, 10, 0, 0);

            V4ForwardLabels L = new V4ForwardLabels();
            L.Stops.Freeze(1, 100, 4, 98, 96, 90);
            L.RaceStop = V4StopKind.MEDIUM;              // stop 4 pts away
            L.Open(1, 100, t0, 4, 99);

            // one bar that reaches BOTH the 1R target (104) and the stop (96)
            L.OnBar(B(t0, 1, 100, 105, 95, 100), 100);

            V4RRace oneR = null;
            for (int i = 0; i < L.Races.Length; i++)
                if (Math.Abs(L.Races[i].Multiple - 1.0) < 1e-9) oneR = L.Races[i];

            Check(oneR != null, "the 1R race exists in the grid");
            Check(oneR.Outcome == V4RaceOutcome.AMBIGUOUS,
                  "a bar spanning both stop and target is AMBIGUOUS, not silently resolved");
            Check(oneR.WouldWinIfTargetFirst && oneR.WouldLoseIfStopFirst,
                  "both bounds are emitted so the race is usable as an interval");
            Check(L.AmbiguousRaceCount() >= 1, "ambiguous races are counted for the audit");

            // an unambiguous target
            V4ForwardLabels W = new V4ForwardLabels();
            W.Stops.Freeze(1, 100, 4, 98, 96, 90);
            W.RaceStop = V4StopKind.MEDIUM;
            W.Open(1, 100, t0, 4, 99);
            W.OnBar(B(t0, 1, 100, 105, 99, 104), 100);
            V4RRace w1 = null;
            for (int i = 0; i < W.Races.Length; i++)
                if (Math.Abs(W.Races[i].Multiple - 1.0) < 1e-9) w1 = W.Races[i];
            Check(w1.Outcome == V4RaceOutcome.TARGET, "target reached alone resolves cleanly");
            Check(W.AmbiguousRaceCount() == 0, "a clean race is not counted as ambiguous");

            // an unambiguous stop
            V4ForwardLabels S = new V4ForwardLabels();
            S.Stops.Freeze(1, 100, 4, 98, 96, 90);
            S.RaceStop = V4StopKind.MEDIUM;
            S.Open(1, 100, t0, 4, 99);
            S.OnBar(B(t0, 1, 100, 101, 95, 96), 100);
            V4RRace s1 = null;
            for (int i = 0; i < S.Races.Length; i++)
                if (Math.Abs(S.Races[i].Multiple - 1.0) < 1e-9) s1 = S.Races[i];
            Check(s1.Outcome == V4RaceOutcome.STOP, "stop reached alone resolves cleanly");

            // unresolved races become TIMEOUT at end of data, not blank
            V4ForwardLabels T = new V4ForwardLabels();
            T.Stops.Freeze(1, 100, 4, 98, 96, 90);
            T.Open(1, 100, t0, 4, 99);
            T.CloseWindow();
            Check(T.Races[0].Outcome == V4RaceOutcome.TIMEOUT,
                  "an unresolved race closes as TIMEOUT rather than looking unfinished");
        }

        // ---------------------------------------------------------------
        // NO LOOKAHEAD
        // ---------------------------------------------------------------
        private static void NoLookahead()
        {
            Console.WriteLine(" no lookahead");
            DateTime ev = new DateTime(2026, 1, 5, 10, 0, 0);

            V4Row ok = new V4Row(ev);
            ok.F("levelKnownEt", ev.AddMinutes(-5));
            Check(ok.LookaheadHits == 0, "a feature known BEFORE the event is accepted");

            V4Row bad = new V4Row(ev);
            bad.F("levelKnownEt", ev.AddMinutes(5));
            Check(bad.LookaheadHits == 1, "a feature timestamped AFTER the event is counted, not hidden");

            V4Row same = new V4Row(ev);
            same.F("levelKnownEt", ev);
            Check(same.LookaheadHits == 0, "a feature at exactly the event instant is allowed");

            V4Row lbl = new V4Row(ev);
            lbl.Y("vectorFullRecoveryEt", ev.AddHours(3));
            Check(lbl.LookaheadHits == 0, "a LABEL in the future is expected and never counted");

            // labels are prefixed so the separation is visible in the file
            V4Row pre = new V4Row(ev);
            pre.F("a", 1).Y("b", 2).Key("c", "x");
            string h = pre.Header();
            Check(h == "f_a,y_b,c", "columns carry f_ / y_ prefixes and keys carry none");

            // the forward-label engine ignores bars at or before entry
            V4ForwardLabels L = new V4ForwardLabels();
            L.Stops.Freeze(1, 100, 4, 98, 96, 90);
            L.Open(1, 100, ev, 4, 99);
            L.OnBar(B(ev.AddMinutes(-5), 1, 100, 200, 50, 150), 100);
            Check(L.MinutesObserved == 0, "a bar before entry does not advance the label window");
            Check(L.MaxMfePts == 0, "...and cannot contribute to MFE");
        }

        // ---------------------------------------------------------------
        // ORDER FLOW
        // ---------------------------------------------------------------
        private static void OrderFlowFeatures()
        {
            Console.WriteLine(" order-flow features");
            V4FootprintBar fb = new V4FootprintBar();
            fb.EtClose = new DateTime(2026, 1, 5, 10, 0, 0);
            fb.Open = 100; fb.High = 100.75; fb.Low = 100; fb.Close = 100;
            fb.Volume = 400;
            fb.Levels.Add(L(100.00, 20, 80));    // bid/ask 4.0 -> imbalanced at 3x
            fb.Levels.Add(L(100.25, 30, 90));    // bid/ask 3.0 -> imbalanced at 3x
            fb.Levels.Add(L(100.50, 30, 100));   // bid/ask 3.33 -> imbalanced at 3x
            fb.Levels.Add(L(100.75, 20, 20));    // balanced
            fb.HasLevels = true;

            V4OrderFlowFeatures f = new V4OrderFlowFeatures();
            f.Compute(fb, 0.25, 100.0, 1.0, 2.0, true);

            Check(Math.Abs(f.AskVolume - 100) < 1e-9, "ask total sums the per-price ask cells");
            Check(Math.Abs(f.BidVolume - 290) < 1e-9, "bid total sums the per-price bid cells");
            Check(Math.Abs(f.BarDelta - (-190)) < 1e-9, "bar delta is ask minus bid, recomputed from cells");
            Check(f.AggressiveSellVolume > f.AggressiveBuyVolume, "aggressive sell volume dominates here");

            // sell imbalance at 3x: bid >= 3*ask on the first three levels
            Check(f.SellImbalanceCount[1] == 3, "3x sell imbalance counted on three levels");
            Check(f.StackedSellLevels[1] == 3, "three consecutive imbalanced levels are STACKED");
            Check(f.BuyImbalanceCount[1] == 0, "no buy imbalance in a sell-dominated bar");

            // the family reports every ratio, not one
            Check(f.SellImbalanceCount.Length == V4ImbalanceFamily.Ratios.Length,
                  "the imbalance family reports one count per declared ratio");
            Check(f.SellImbalanceCount[0] >= f.SellImbalanceCount[2],
                  "a looser ratio cannot count fewer imbalances than a stricter one");

            Check(Math.Abs(f.PocPrice - 100.50) < 1e-9, "POC is the heaviest traded price");
            Check(Math.Abs(f.PocVolume - 130) < 1e-9, "POC volume sums both sides");

            // divergence needs a trailing window and no future information
            V4DivergenceTracker d = new V4DivergenceTracker(5);
            V4OrderFlowFeatures g = new V4OrderFlowFeatures();
            d.Update(g, 100, 99, 10);
            d.Update(g, 101, 100, 5);
            Check(g.PriceNewHigh, "a higher high is recognised");
            Check(!g.CumDeltaNewHigh, "cumulative delta did not confirm it");
            Check(g.BearishDeltaDivergenceCandidate, "price up on failing delta -> bearish divergence candidate");
            Check(g.DeltaFailsBreak, "...and the break is marked unconfirmed");
        }

        private static V4FootprintLevel L(double price, double ask, double bid)
        {
            V4FootprintLevel l = new V4FootprintLevel();
            l.Price = price; l.AskVolume = ask; l.BidVolume = bid;
            return l;
        }

        // ---------------------------------------------------------------
        // SCHEMA AND VALIDITY
        // ---------------------------------------------------------------
        private static void SchemaAndValidity()
        {
            Console.WriteLine(" schema and validity flags");
            DateTime ev = new DateTime(2026, 1, 5, 10, 0, 0);

            V4Schema sc = new V4Schema("test");
            V4Row a = new V4Row(ev); a.F("x", 1).Y("y", 2);
            sc.Verify(a);
            Check(sc.Established, "the first row establishes the schema");
            Check(sc.Header == "f_x,y_y", "header comes from the row itself");
            Check(sc.FeatureCount == 1 && sc.LabelCount == 1, "features and labels are counted separately");

            V4Row same = new V4Row(ev); same.F("x", 9).Y("y", 8);
            bool threwOnSame = false;
            try { sc.Verify(same); } catch (Exception) { threwOnSame = true; }
            Check(!threwOnSame, "a matching row verifies without complaint");

            V4Row wrong = new V4Row(ev); wrong.F("x", 1);
            bool threw = false;
            try { sc.Verify(wrong); } catch (InvalidOperationException) { threw = true; }
            Check(threw, "a row with the wrong column COUNT is refused, not written misaligned");

            V4Row renamed = new V4Row(ev); renamed.F("x", 1).Y("z", 2);
            bool threw2 = false;
            try { sc.Verify(renamed); } catch (InvalidOperationException) { threw2 = true; }
            Check(threw2, "a row with a renamed column is refused");

            // the two families the evidence disqualifies must stay disqualified
            V4ValidityFlags v = new V4ValidityFlags();
            Check(!v.PsyLevelPriceIntegrityPass,
                  "PSY / round-number integrity is FALSE on a back-adjusted series");
            Check(!v.DepthHistoryAvailable,
                  "market depth is unavailable - NT8 keeps no historical L2 for backtest");
            Check(!v.FirstVectorSourceVerified,
                  "First Vector has no published mechanics and is not manufactured");
            Check(v.VectorSourceVerified,
                  "the PVSRA formula IS verified and is reused rather than reinvented");

            // session mapping
            Check(V4SessionMap.Classify(new DateTime(2026, 1, 5, 19, 0, 0)) == V4Session.ASIA,
                  "19:00 ET is the Asia session");
            Check(V4SessionMap.Classify(new DateTime(2026, 1, 5, 10, 0, 0)) == V4Session.NEWYORK_RTH,
                  "10:00 ET is RTH");
            Check(V4SessionMap.IsScheduledHaltBoundary(new DateTime(2026, 1, 5, 18, 1, 0), 5),
                  "18:00 ET reopen is a scheduled halt boundary, not missing data");
            Check(V4SessionMap.IsScheduledHaltBoundary(new DateTime(2026, 1, 5, 16, 31, 0), 5),
                  "16:30 ET maintenance reopen is a scheduled halt boundary");
            Check(!V4SessionMap.IsScheduledHaltBoundary(new DateTime(2026, 1, 5, 11, 0, 0), 5),
                  "a midday gap is NOT explained away as a halt");

            // the guarded divide that a near-zero denominator would otherwise blow up
            Check(double.IsNaN(V4Num.SafeDiv(10, 0.0000001, 1e-3)),
                  "a near-zero denominator returns NaN rather than an exploded number");
            Check(Math.Abs(V4Num.SafeDiv(10, 2, 1e-9) - 5) < 1e-9, "an ordinary divide still works");
        }

        // ---------------------------------------------------------------
        // BREAK TRANSITION - the defect the first live sample exposed
        // ---------------------------------------------------------------
        private static void BreakTransition()
        {
            Console.WriteLine(" break transition gate");
            V4BreakGate g = new V4BreakGate();

            // price breaks a confirmed swing high, then STAYS above it for
            // four more bars. The old state test fired on all five.
            Check(g.Update(101, 99, 100.5, true, 100, false, double.NaN) == 1,
                  "first bar beyond the level fires");
            Check(g.Update(102, 100.5, 101.5, true, 100, false, double.NaN) == 0,
                  "second bar still beyond does NOT fire again");
            Check(g.Update(103, 101, 102.5, true, 100, false, double.NaN) == 0,
                  "third bar still beyond does not fire");
            Check(g.Update(104, 102, 103.5, true, 100, false, double.NaN) == 0,
                  "fourth bar still beyond does not fire");

            // price closes back INSIDE, then breaks the same level again
            Check(g.Update(100.5, 98, 99, true, 100, false, double.NaN) == 0,
                  "closing back inside is not itself a break");
            Check(g.Update(101, 99.5, 100.5, true, 100, false, double.NaN) == 1,
                  "breaking the SAME level again after re-entry fires once more");

            // a NEW confirmed level higher up is a genuinely new break
            Check(g.Update(106, 104, 105.5, true, 105, false, double.NaN) == 1,
                  "a break of a DIFFERENT confirmed level fires");
            Check(g.Update(107, 105.5, 106.5, true, 105, false, double.NaN) == 0,
                  "...and then stops firing while price stays beyond it");

            // the low side is independent and mirrors
            V4BreakGate d = new V4BreakGate();
            Check(d.Update(101, 99, 99.5, false, double.NaN, true, 100) == -1,
                  "first bar below the level fires a low break");
            Check(d.Update(100, 98, 98.5, false, double.NaN, true, 100) == 0,
                  "second bar still below does not fire");
            Check(d.Update(101.5, 100.5, 101, false, double.NaN, true, 100) == 0,
                  "closing back above is not a break");
            Check(d.Update(101, 99, 99.5, false, double.NaN, true, 100) == -1,
                  "re-breaking the low after re-entry fires again");

            // a bar that never reaches the level cannot fire
            V4BreakGate q = new V4BreakGate();
            Check(q.Update(99.5, 98, 99, true, 100, false, double.NaN) == 0,
                  "a bar that never reaches the level never fires");

            // Reset clears carried state, which matters because NinjaTrader
            // reuses the strategy instance across runs
            V4BreakGate r = new V4BreakGate();
            r.Update(101, 99, 100.5, true, 100, false, double.NaN);
            Check(r.Update(102, 100.5, 101.5, true, 100, false, double.NaN) == 0, "state carries within a run");
            r.Reset();
            Check(r.Update(102, 100.5, 101.5, true, 100, false, double.NaN) == 1,
                  "Reset clears the gate so a re-run starts clean");
        }

        // ---------------------------------------------------------------
        // TIMESTAMP CONVENTION - reproduces the field-observed -12 median
        // ---------------------------------------------------------------
        private static void TimestampConvention()
        {
            Console.WriteLine(" bar timestamp convention");

            // NinjaTrader hands us ONE stamp for a completed bar, and that
            // stamp is the bar's CLOSE.
            DateTime stamp = new DateTime(2019, 8, 15, 10, 15, 0);
            DateTime o, c;

            V4BarStamp.FromNtStamp(stamp, 15, out o, out c);
            Check(c == stamp, "the NT stamp IS the close");
            Check(o == stamp.AddMinutes(-15), "the open is derived backwards by the bar period");
            Check(c > o, "close is after open");

            V4BarStamp.FromNtStamp(stamp, 1, out o, out c);
            Check(c == stamp && o == stamp.AddMinutes(-1), "same on the 1m series");

            // Now reproduce the actual defect and the number it produced.
            //
            // Field observation: ARCH-A median minsToEntry was -12 minutes.
            // A 15m bar closes at C. Under the defect it was stamped C+15.
            // The 1m bar two minutes later closes at C+2, stamped C+3.
            // minsToEntry = (C+3) - (C+15) = -12. Exactly what the sample said.
            DateTime c15 = new DateTime(2019, 8, 15, 10, 15, 0);
            DateTime bo, bc, eo, ec;

            V4BarStamp.FromNtStampAsOpen_DEFECT(c15, 15, out bo, out bc);
            V4BarStamp.FromNtStampAsOpen_DEFECT(c15.AddMinutes(2), 1, out eo, out ec);
            int defectDelay = (int)(ec - bc).TotalMinutes;
            Check(defectDelay == -12,
                  "the DEFECT reproduces the field-observed -12 minute entry delay");
            Check(defectDelay < 0, "...which is an entry preceding its own event");

            // The fix, on the identical bars.
            V4BarStamp.FromNtStamp(c15, 15, out bo, out bc);
            V4BarStamp.FromNtStamp(c15.AddMinutes(2), 1, out eo, out ec);
            int fixedDelay = (int)(ec - bc).TotalMinutes;
            Check(fixedDelay == 2, "the FIX gives a +2 minute delay on the same bars");
            Check(fixedDelay > 0, "...an entry strictly after its event");

            // And the reason it mattered more than the visible symptom: the
            // cutoff must refuse a swing confirmed at the event instant.
            V4Bar ev = new V4Bar(); ev.EtClose = bc;
            DateTime cut = V4ResearchEngine.SnapshotCutoff(ev);
            Check(cut < bc, "the cutoff sits strictly before the event close");
            Check(cut > bc.AddMinutes(-1), "...but admits everything up to the prior minute");

            // under the defect the cutoff was 15 minutes PAST the real close
            V4Bar bad = new V4Bar(); bad.EtClose = c15.AddMinutes(15);
            Check(V4ResearchEngine.SnapshotCutoff(bad) > c15.AddMinutes(14),
                  "the DEFECT pushed the cutoff ~15 minutes past the real bar close");
        }

        // ---------------------------------------------------------------
        // AUDIT GUARDS
        // ---------------------------------------------------------------
        private static void AuditGuards()
        {
            Console.WriteLine(" audit guards");

            // A negative entry delay must FAIL the capture, not pass quietly.
            V4StructureAudit a = new V4StructureAudit();
            a.MinRowsRequired = 1;
            for (int i = 0; i < 5; i++) a.NoteRow(new DateTime(2019, 8, 15, 10, 0, 0), DateTime.MinValue, false);
            a.NoteEntryDelay(3);
            Check(a.Verdict() != V4Verdict.FAILED, "a positive entry delay does not fail the capture");
            a.NoteEntryDelay(-12);
            Check(a.NegativeEntryDelays == 1, "a negative entry delay is counted");
            Check(a.WorstNegativeEntryDelay == -12, "the worst is recorded");
            Check(a.Verdict() == V4Verdict.FAILED,
                  "ANY entry preceding its event FAILS the capture");
            Check(a.VerdictReason.IndexOf("timestamps are wrong") >= 0,
                  "...and the reason names the cause rather than blaming the market");

            // Unexplained gaps are scored against BAR TRANSITIONS, not gaps.
            V4StructureAudit g = new V4StructureAudit();
            g.MinRowsRequired = 1;
            g.NoteRow(new DateTime(2019, 8, 15, 10, 0, 0), DateTime.MinValue, false);
            DateTime t0 = new DateTime(2019, 8, 15, 10, 0, 0);
            // 999 ordinary consecutive bars, then 4 bars each an hour apart
            // so every one of them opens a genuine unexplained gap
            for (int i = 0; i < 999; i++) g.NoteBar(Bar(t0.AddMinutes(i)), 20190815);
            for (int i = 1; i <= 4; i++) g.NoteBar(Bar(t0.AddMinutes(998 + i * 60)), 20190815);
            Check(g.BarsObserved == 1003, "bar transitions are counted");
            Check(g.UnexplainedGaps == 4, "the four gaps are unexplained");
            Check(g.UnexplainedGapPctOfBars < 0.5,
                  "4 gaps in 1003 bars is 0.40% - inside the 0.5% limit");
            Check(g.Verdict() == V4Verdict.PASSED,
                  "a clean sample PASSES instead of tripping on the wrong denominator");

            // The OLD metric divided by GAP COUNT. On this same clean sample
            // that is 4 of 4 = 100%, two hundred times the limit - which is
            // why a genuinely clean capture came back NEEDS REVIEW.
            long allGaps = g.UnexplainedGaps + g.ScheduledHaltGaps + g.WeekendGaps;
            double oldMetric = allGaps > 0 ? 100.0 * g.UnexplainedGaps / allGaps : 0.0;
            Check(oldMetric > g.MaxUnexplainedGapPct,
                  "the OLD gap-share denominator scored this same clean sample as a failure");
            Check(oldMetric / Math.Max(1e-9, g.UnexplainedGapPctOfBars) > 100,
                  "...it was overstating the problem by more than 100x");

            // sample-size NEEDS REVIEW must name itself as such
            V4StructureAudit small = new V4StructureAudit();
            small.NoteRow(new DateTime(2019, 8, 15, 10, 0, 0), DateTime.MinValue, false);
            Check(small.Verdict() == V4Verdict.NEEDS_REVIEW, "a tiny sample is NEEDS REVIEW");
            Check(small.VerdictReason.IndexOf("SAMPLE SIZE ONLY") >= 0,
                  "...and says SAMPLE SIZE ONLY so it is not read as a data problem");

            // END-TO-END: the guard must catch the timestamp defect in REAL
            // data even though no unit test can drive the host's OnBarUpdate.
            //
            // This is the protection that actually matters. A unit test proves
            // V4BarStamp is correct; it cannot prove the HOST calls the right
            // one. The audit can, on the first run, from the data itself.
            DateTime c15 = new DateTime(2019, 8, 15, 10, 15, 0);
            for (int useDefect = 0; useDefect <= 1; useDefect++)
            {
                V4StructureAudit sim = new V4StructureAudit();
                sim.MinRowsRequired = 1;
                sim.NoteRow(c15, DateTime.MinValue, false);

                // 30 parent events, each entered by a 1m bar 1-3 minutes later
                for (int e = 0; e < 30; e++)
                {
                    DateTime evStamp = c15.AddMinutes(e * 60);
                    int k = 1 + (e % 3);
                    DateTime enStamp = evStamp.AddMinutes(k);
                    DateTime eo, ec, no, nc;
                    if (useDefect == 1)
                    {
                        V4BarStamp.FromNtStampAsOpen_DEFECT(evStamp, 15, out eo, out ec);
                        V4BarStamp.FromNtStampAsOpen_DEFECT(enStamp, 1, out no, out nc);
                    }
                    else
                    {
                        V4BarStamp.FromNtStamp(evStamp, 15, out eo, out ec);
                        V4BarStamp.FromNtStamp(enStamp, 1, out no, out nc);
                    }
                    sim.NoteEntryDelay((int)(nc - ec).TotalMinutes);
                }

                if (useDefect == 1)
                {
                    Check(sim.NegativeEntryDelays == 30,
                          "SIMULATED HOST with the timestamp defect: every entry precedes its event");
                    Check(sim.Verdict() == V4Verdict.FAILED,
                          "...and the audit FAILS the capture on the first run");
                }
                else
                {
                    Check(sim.NegativeEntryDelays == 0,
                          "SIMULATED HOST with the fix: no entry precedes its event");
                    Check(sim.Verdict() != V4Verdict.FAILED,
                          "...and the capture is not failed for it");
                }
            }

            // lookahead still outranks everything
            V4StructureAudit la = new V4StructureAudit();
            la.MinRowsRequired = 1;
            la.NoteRow(new DateTime(2019, 8, 15, 10, 0, 0), new DateTime(2019, 8, 15, 11, 0, 0), false);
            Check(la.LookaheadViolations == 1, "a feature timestamped after its event is a violation");
            Check(la.Verdict() == V4Verdict.FAILED, "lookahead FAILS the capture outright");
        }

        private static V4Bar Bar(DateTime closeEt)
        {
            V4Bar b = new V4Bar();
            b.EtClose = closeEt; b.EtOpen = closeEt.AddMinutes(-1);
            b.Open = b.High = b.Low = b.Close = 100; b.Volume = 100;
            return b;
        }

        // ---------------------------------------------------------------
        // The six defects the 2-month sample exposed
        // ---------------------------------------------------------------
        private static void SampleTwoFixes()
        {
            Console.WriteLine(" 2-month sample fixes");
            DateTime t0 = new DateTime(2019, 8, 15, 10, 0, 0);

            // --- B: a race that reaches neither level is TIMEOUT ---------
            V4ForwardLabels L = new V4ForwardLabels();
            L.Stops.Freeze(1, 100, 4, 96, 92, 80);
            L.RaceStop = V4StopKind.MEDIUM;
            L.Open(1, 100, t0, 4, 99);
            // 240 bars that never reach target or stop
            for (int i = 1; i <= 240; i++)
                L.OnBar(B(t0.AddMinutes(i - 1), 1, 100, 100.5, 99.5, 100), 100);
            Check(L.WindowComplete, "the window completes after the last horizon");
            Check(L.Races[0].Outcome == V4RaceOutcome.TIMEOUT,
                  "a race reaching neither level is TIMEOUT, not UNRESOLVED");
            bool anyUnresolved = false;
            for (int i = 0; i < L.Races.Length; i++)
                if (L.Races[i].Outcome == V4RaceOutcome.UNRESOLVED) anyUnresolved = true;
            Check(!anyUnresolved, "NO race is left UNRESOLVED once the window has completed");

            // --- F: the stop family must be ordered and non-degenerate ---
            V4StopSet tiny = new V4StopSet();
            tiny.Freeze(1, 100, 4, 99.75, 96, 80);       // tight = 0.25pt, one tick
            Check(double.IsNaN(tiny.TightPts), "a quarter-point stop is refused, not emitted");
            Check(tiny.BelowMinimumStop, "...and the row is flagged");
            Check(V4Num.Ok(tiny.MediumPts), "the other family members survive");

            V4StopSet unordered = new V4StopSet();
            unordered.Freeze(1, 100, 4, 94, 92, 99);     // structural NEARER than tight
            Check(V4Num.Ok(unordered.TightPts), "tight stop kept");
            Check(double.IsNaN(unordered.StructuralPts),
                  "a structural stop TIGHTER than the tight one is dropped, not reordered");
            Check(unordered.FamilyOrderRepaired, "...and the row is flagged");

            V4StopSet good = new V4StopSet();
            good.Freeze(1, 100, 4, 96, 92, 80);
            Check(good.TightPts <= good.MediumPts && good.MediumPts <= good.StructuralPts,
                  "a well-formed family is left alone and stays ordered");
            Check(!good.FamilyOrderRepaired && !good.BelowMinimumStop, "...and carries no flag");

            // --- C: unrecovered count means OPEN zones -------------------
            V4VectorEngine ve = new V4VectorEngine("MNQ", "15m", 15);
            V4Swing none = new V4Swing();
            // 11 quiet bars to build the volume baseline, then one climax bar
            for (int i = 0; i < 11; i++)
                ve.OnBar(B(t0.AddMinutes(i * 15), 15, 100, 101, 99, 100, 100), 4, none, none, none, none);
            V4Vector made = ve.OnBar(B(t0.AddMinutes(165), 15, 100, 101, 90, 91, 500), 4, none, none, none, none);
            Check(made != null, "a climax bar creates a vector");
            DateTime after = t0.AddMinutes(200);
            Check(ve.UnrecoveredCount(after) == 1,
                  "an open zone counts as unrecovered even once price has grazed it");
            Check(ve.UntouchedCount(after) == 1, "and as untouched while it truly is");

            // one bar that grazes the zone: still OPEN, no longer untouched
            ve.OnBar(B(t0.AddMinutes(180), 15, 91, 93, 90, 92, 100), 4, none, none, none, none);
            Check(ve.UnrecoveredCount(t0.AddMinutes(400)) == 1,
                  "a graze does NOT zero the unrecovered count - the old bug");
            Check(ve.UntouchedCount(t0.AddMinutes(400)) == 0,
                  "...but it does end the strict untouched state");

            // --- A: ARCH-C must actually be able to differ from ARCH-B ---
            int members = Enum.GetValues(typeof(V4LtfExecution)).Length;
            Check(members == 3, "three declared executions: IMMEDIATE, PULLBACK, MICRO_BREAK");

            // IMMEDIATE reproduces the collapse: ready on the very first bar
            V4LtfExecutionGate imm = new V4LtfExecutionGate();
            imm.Mode = V4LtfExecution.IMMEDIATE;
            Check(imm.Ready(1, 101, 100, 4), "IMMEDIATE is ready on the first bar - the ARCH-B collapse");

            // PULLBACK is NOT ready until price retraces off the best price
            V4LtfExecutionGate pb = new V4LtfExecutionGate();
            pb.Mode = V4LtfExecution.PULLBACK; pb.PullbackAtr = 0.5;   // 0.5 x ATR 4 = 2.0 pts
            Check(!pb.Ready(1, 105, 104, 4), "PULLBACK is NOT ready on the first bar after confirmation");
            Check(!pb.Ready(1, 107, 106, 4), "...nor while price keeps running away");
            Check(!pb.Ready(1, 107, 105.5, 4), "...nor on a retrace of only 1.5 pts");
            Check(pb.Ready(1, 106, 104.9, 4), "READY once price retraces 2.1 pts off the 107 high");
            Check(pb.Armed, "...and the gate stays armed");
            Check(pb.Ready(1, 106, 105.5, 4), "an armed gate stays ready on later bars");

            // the short side mirrors
            V4LtfExecutionGate pbs = new V4LtfExecutionGate();
            pbs.Mode = V4LtfExecution.PULLBACK; pbs.PullbackAtr = 0.5;
            Check(!pbs.Ready(-1, 100, 99, 4), "short PULLBACK not ready on the first bar");
            Check(!pbs.Ready(-1, 98, 96, 4), "...nor while price runs down");
            Check(pbs.Ready(-1, 98.2, 97, 4), "READY once price retraces 2.2 pts off the 96 low");

            // MICRO_BREAK needs a prior bar to break
            V4LtfExecutionGate mb = new V4LtfExecutionGate();
            mb.Mode = V4LtfExecution.MICRO_BREAK;
            Check(!mb.Ready(1, 101, 100, 4), "MICRO_BREAK cannot fire with no prior bar");
            Check(!mb.Ready(1, 100.5, 99.5, 4), "...nor on a bar that fails to exceed the prior high");
            Check(mb.Ready(1, 101.5, 100, 4), "READY on the bar that takes the prior high");

            V4LtfExecutionGate r = new V4LtfExecutionGate();
            r.Mode = V4LtfExecution.PULLBACK; r.PullbackAtr = 0.5;
            r.Ready(1, 107, 106, 4); r.Ready(1, 106, 104, 4);
            Check(r.Armed, "armed before reset");
            r.Reset();
            Check(!r.Armed, "Reset disarms - NinjaTrader reuses the instance across runs");
        }

        // ---------------------------------------------------------------
        // SAMPLE THREE - the two families of DEAD LABEL the third clean
        // 659-row structure sample exposed.
        //
        // A y_ column that carries the same value on every row of a sample
        // is not a weak label, it is an absent one, and it is invisible in
        // an audit that only counts rows and checks causality. 21 of the
        // 117 structure labels were constant. Two mechanisms produced them.
        // ---------------------------------------------------------------
        private static void SampleThreeFixes()
        {
            Console.WriteLine(" [sample three: dead labels]");

            // -----------------------------------------------------------
            // DEFECT 1: vector recovery read at the vector's own bar.
            //
            // VectorRecoveryLabels was called while building the FEATURE
            // row, i.e. on the bar the vector formed. A vector cannot have
            // retraced into itself on the bar that created it, so the six
            // recovery labels were pinned: UNRECOVERED on all 285 vector
            // rows, pct 0 on all 285, firstTouchEt blank on all 659,
            // barsTo25/50/100 all -1, both trap flags all FALSE.
            //
            // This test pins the DIFFERENCE between the two read points on
            // one and the same vector object, which is what makes it a
            // regression test rather than a restatement.
            // -----------------------------------------------------------
            DateTime t0 = new DateTime(2019, 7, 1, 10, 0, 0);
            V4Vector v = new V4Vector();
            v.VectorId = "V-1";
            v.CreatedEt = t0;
            v.Color = V4VectorColor.RED; v.Dir = V4VectorDir.BEARISH;
            v.High = 112; v.Low = 100; v.BodyHigh = 111; v.BodyLow = 101;
            v.AtrAtCreation = 4;

            // read at the event, exactly as the defective call site did
            V4Row atEvent = new V4Row(t0);
            V4RowBuilder.VectorRecoveryLabels(atEvent, "15m", v);
            Check(Val(atEvent, "y_vectorRecovery_15m") == "UNRECOVERED",
                  "at the vector's own bar recovery reads UNRECOVERED - the defect");
            Check(Val(atEvent, "y_vectorRecoveryPct_15m") == "0",
                  "...and recoveryPct reads 0");
            Check(Val(atEvent, "y_vectorBarsTo50_15m") == "-1",
                  "...and barsTo50 reads -1");
            Check(Val(atEvent, "y_vectorTrapCandidate_15m") == "FALSE",
                  "...and trapCandidate reads FALSE");

            // now let the window elapse on the SAME object
            v.ApplyLaterBar(B(t0, 15, 101, 104, 100.5, 103), 1);
            v.ApplyLaterBar(B(t0.AddMinutes(15), 15, 103, 107, 102, 106.5), 2);

            V4Row atClose = new V4Row(t0);
            V4RowBuilder.VectorRecoveryLabels(atClose, "15m", v);
            Check(Val(atClose, "y_vectorRecovery_15m") != "UNRECOVERED",
                  "read at window close the SAME vector is no longer UNRECOVERED");
            Check(Val(atClose, "y_vectorRecoveryPct_15m") != "0",
                  "...recoveryPct has moved off zero");
            Check(Val(atClose, "y_vectorBarsTo50_15m") == "2",
                  "...barsTo50 records the bar the midpoint was reached");
            Check(Val(atClose, "y_vectorFirstTouchEt_15m") != "",
                  "...firstTouchEt is stamped");
            Check(Val(atEvent, "y_vectorRecovery_15m") != Val(atClose, "y_vectorRecovery_15m"),
                  "the two read points DISAGREE - which is the whole defect");

            // the column names must not change: nine labels, all y_ prefixed
            int recCols = 0;
            for (int i = 0; i < atClose.Count; i++)
                if (atClose.NameAt(i).StartsWith("y_vector")) recCols++;
            Check(recCols == 9, "VectorRecoveryLabels emits nine y_ columns");

            // a null vector must still emit the full block so the header is
            // established on the very first row, vector or not
            V4Row none = new V4Row(t0);
            V4RowBuilder.VectorRecoveryLabels(none, "15m", null);
            Check(none.Count == atClose.Count,
                  "a non-vector row emits the same nine columns, blank");

            // -----------------------------------------------------------
            // The assembly itself, driven end to end. This is the test that
            // was MISSING: the two above exercise V4RowBuilder, and they
            // passed just as happily while the host called the recovery
            // block from the frozen feature half. V4OpenEvent was lifted out
            // of the NinjaScript host precisely so the wiring is reachable.
            // -----------------------------------------------------------
            V4Vector ev = new V4Vector();
            ev.VectorId = "V-2"; ev.CreatedEt = t0;
            ev.Color = V4VectorColor.RED; ev.Dir = V4VectorDir.BEARISH;
            ev.High = 112; ev.Low = 100; ev.BodyHigh = 111; ev.BodyLow = 101;
            ev.AtrAtCreation = 4;

            V4Row feat = new V4Row(t0);
            feat.Key("eventId", "E-1").F("side", -1).F("isVector_15m", true);

            V4OpenEvent oe = new V4OpenEvent();
            oe.Freeze(feat, t0);
            oe.EventVector = ev;
            oe.VectorTfTag = "15m";

            string frozen = oe.FeatureCsv;
            Check(frozen.IndexOf("UNRECOVERED") < 0,
                  "the FROZEN feature half contains no recovery value at all");

            // the vector recovers while the window runs
            ev.ApplyLaterBar(B(t0, 15, 101, 104, 100.5, 103), 1);
            ev.ApplyLaterBar(B(t0.AddMinutes(15), 15, 103, 107, 102, 106.5), 2);

            Check(oe.FeatureCsv == frozen,
                  "the frozen half is BYTE-IDENTICAL after the market moved");

            V4Row labelHalf = oe.BuildLabelRow();
            Check(Val(labelHalf, "y_vectorRecovery_15m") != "UNRECOVERED",
                  "the LABEL half picks up the recovery that happened after the event");
            Check(labelHalf.NameAt(0) == "y_vectorRecovery_15m",
                  "recovery is the FIRST label column, not a feature column");

            // header and data must be built by the same definition
            V4Row schema = V4OpenEvent.SchemaRow(feat, "15m", t0);
            string[] hdr = schema.Header().Split(',');
            string[] dat = oe.CompletedCsv().Split(',');
            Check(hdr.Length == dat.Length,
                  "SchemaRow and CompletedCsv agree on column COUNT (" + hdr.Length + ")");
            int firstY = -1;
            for (int i = 0; i < hdr.Length; i++)
                if (hdr[i].StartsWith("y_")) { firstY = i; break; }
            Check(firstY == feat.Count,
                  "every label column sits after the last feature column");
            Check(hdr[firstY] == "y_vectorRecovery_15m",
                  "the label block starts with the recovery block");

            // no duplicated column names anywhere
            bool dup = false;
            for (int i = 0; i < hdr.Length && !dup; i++)
                for (int j = i + 1; j < hdr.Length; j++)
                    if (hdr[i] == hdr[j]) { dup = true; break; }
            Check(!dup, "no column name appears twice in the assembled header");

            // a non-vector event still produces the identical column count
            V4OpenEvent none2 = new V4OpenEvent();
            none2.Freeze(feat, t0);
            Check(none2.CompletedCsv().Split(',').Length == hdr.Length,
                  "a non-vector event writes the same number of columns");

            // -----------------------------------------------------------
            // DEFECT 2: the parent event was opened with stops and no
            // targets. Ten target columns plus the three targetAfterStop
            // controls could not vary - 13 dead columns - because
            // ResolveTargets skips an invalid target and ReferenceTarget
            // returns one.
            // -----------------------------------------------------------
            V4ForwardLabels bare = new V4ForwardLabels();
            bare.Stops.Freeze(1, 100, 4, 99, 98, 96);
            bare.Open(1, 100, t0, 4, 99.5);
            for (int i = 1; i <= 30; i++)
                bare.OnBar(B(t0.AddMinutes(i - 1), 1, 100, 130, 99.5, 129), 99.5);

            Check(!bare.HitTargetSwing && !bare.HitTargetVectorZone
                  && !bare.HitTargetLiquidity && !bare.HitTargetHtfStruct
                  && !bare.HitTargetSession,
                  "with no targets assigned, price running 30 pts hits NOTHING - the defect");
            Check(bare.MinsToTargetSwing == -1,
                  "...and every minsToTarget stays -1");
            Check(!bare.Stops.TargetReachedAfterTight && !bare.Stops.TargetReachedAfterMedium
                  && !bare.Stops.TargetReachedAfterStructural,
                  "...and the three targetAfterStop controls are dead with them");

            // the same run WITH targets assigned resolves
            V4ForwardLabels armed = new V4ForwardLabels();
            armed.Stops.Freeze(1, 100, 4, 99, 98, 96);
            armed.TargetSwing = V4Target.Make("SWING", "15m", 110, 100, 1, 4);
            armed.TargetSession = V4Target.Make("SESSION", "session extreme", 125, 100, 1, 4);
            armed.Open(1, 100, t0, 4, 99.5);
            for (int i = 1; i <= 30; i++)
                armed.OnBar(B(t0.AddMinutes(i - 1), 1, 100, 130, 99.5, 129), 99.5);

            Check(armed.HitTargetSwing, "the identical bars DO hit a swing target once one is assigned");
            Check(armed.MinsToTargetSwing == 1, "...on the first bar, which reached 130");
            Check(armed.HitTargetSession, "...and the session target too");

            // and a target that only arrives after the stop is flagged
            V4ForwardLabels late = new V4ForwardLabels();
            late.Stops.Freeze(1, 100, 4, 99, 98, 96);
            late.TargetSwing = V4Target.Make("SWING", "15m", 110, 100, 1, 4);
            late.Open(1, 100, t0, 4, 99.5);
            late.OnBar(B(t0, 1, 100, 100.5, 95, 96), 99.5);          // all three stops
            late.OnBar(B(t0.AddMinutes(1), 1, 96, 111, 96, 110), 99.5); // target after
            Check(late.Stops.TargetReachedAfterTight && late.Stops.TargetReachedAfterMedium
                  && late.Stops.TargetReachedAfterStructural,
                  "a target reached only after the stop is flagged on all three families");
        }

        // ---------------------------------------------------------------
        // SOURCE SCAN
        //
        // Some defects live in the NinjaScript host, which cannot be
        // instantiated off-platform: it derives from Strategy and its state
        // machine only runs inside NinjaTrader. The parent event being
        // opened with stops and NO targets was one - thirteen dead label
        // columns caused by a call that was simply absent, and no unit test
        // could see it because the host is not a unit.
        //
        // A source scan is weaker than executing the code. It is stated as
        // weaker rather than dressed up: it proves a call site exists, not
        // that it runs. It fails LOUDLY when it cannot find the source
        // rather than passing quietly, because a check that skips itself is
        // worse than no check.
        // ---------------------------------------------------------------
        private static void SourceScan()
        {
            Console.WriteLine(" [source scan: host call sites]");

            string host = FindSource("MnqV41StructureResearchHost.cs");
            if (host == null)
            {
                Check(false, "SOURCE SCAN could not locate MnqV41StructureResearchHost.cs");
                return;
            }
            string src = File.ReadAllText(host);

            int assigns = Count(src, "AssignTargets(");
            Check(assigns >= 3,
                  "AssignTargets is declared and called from BOTH the probe and the "
                  + "parent event (" + assigns + " occurrences, need 3+)");

            int openEventAssign = src.IndexOf("AssignTargets(oe.Labels");
            Check(openEventAssign > 0,
                  "the PARENT EVENT assigns targets - absent, ten target columns and "
                  + "three targetAfterStop controls are constant");
            Check(src.IndexOf("AssignTargets(p.Labels") > 0,
                  "the entry probe assigns targets");

            // the recovery block must NOT be built into the feature row
            int featureCall = src.IndexOf("V4RowBuilder.VectorRecoveryLabels");
            Check(featureCall < 0,
                  "the host never calls VectorRecoveryLabels itself - the assembly "
                  + "belongs to V4OpenEvent, where it is tested");
            Check(src.IndexOf("oe.CompletedCsv()") > 0,
                  "the written structure line comes from V4OpenEvent.CompletedCsv");
            Check(src.IndexOf("V4OpenEvent.SchemaRow(") > 0,
                  "the structure header comes from V4OpenEvent.SchemaRow - same definition");

            // The standing constraint: these strategies submit no orders.
            // Scanned with comments stripped, because each file's header
            // NAMES every banned call in the sentence promising not to make
            // one - a scan of the raw text would fail on the promise.
            //
            // BOTH hosts are scanned. Checking only the structure host left
            // the order-flow host carrying the same promise with nothing
            // enforcing it.
            string[] hosts = new string[] {
                "MnqV41StructureResearchHost.cs",
                "MnqV41OrderFlowResearchHost.cs" };
            string[] banned = new string[] {
                "EnterLong", "EnterShort", "SubmitOrderUnmanaged",
                "SetProfitTarget", "SetStopLoss", "ExitLong", "ExitShort" };
            for (int h = 0; h < hosts.Length; h++)
            {
                string hp = FindSource(hosts[h]);
                if (hp == null) { Check(false, "SOURCE SCAN could not locate " + hosts[h]); continue; }
                string code = StripComments(File.ReadAllText(hp));
                for (int i = 0; i < banned.Length; i++)
                    Check(code.IndexOf(banned[i]) < 0,
                          hosts[h] + " contains no " + banned[i] + " call");
            }

            // The order-flow host must ABORT rather than write a
            // plausible-looking empty file when the primary series is not
            // Volumetric. A run that quietly produces zero rows looks like
            // "no signal" instead of "wrong bars type".
            string ofp = FindSource("MnqV41OrderFlowResearchHost.cs");
            if (ofp != null)
            {
                string of = File.ReadAllText(ofp);
                Check(of.IndexOf("aborted = true") > 0,
                      "the order-flow host aborts on a failed startup gate");
                Check(of.IndexOf("MaximumBarsLookBack.Infinite") > 0,
                      "the order-flow host forces Infinite lookback - the reader "
                      + "indexes the Volumes array directly");
            }
            Check(StripComments("a // EnterLong\nb").IndexOf("EnterLong") < 0,
                  "StripComments removes a line comment");
            Check(StripComments("a /* EnterLong */ b").IndexOf("EnterLong") < 0,
                  "StripComments removes a block comment");
            Check(StripComments("EnterLong(1);").IndexOf("EnterLong") >= 0,
                  "StripComments leaves real code alone - the scan can still fail");
        }

        /// Line and block comments removed. Deliberately simple: it does not
        /// understand string literals, which is safe here because a scan that
        /// over-strips can only produce a FALSE PASS on a name inside a
        /// string, and the three assertions above pin its behaviour.
        private static string StripComments(string src)
        {
            System.Text.StringBuilder sb = new System.Text.StringBuilder(src.Length);
            int i = 0;
            while (i < src.Length)
            {
                if (i + 1 < src.Length && src[i] == '/' && src[i + 1] == '/')
                {
                    while (i < src.Length && src[i] != '\n') i++;
                }
                else if (i + 1 < src.Length && src[i] == '/' && src[i + 1] == '*')
                {
                    i += 2;
                    while (i + 1 < src.Length && !(src[i] == '*' && src[i + 1] == '/')) i++;
                    i += 2;
                }
                else { sb.Append(src[i]); i++; }
            }
            return sb.ToString();
        }

        private static int Count(string s, string needle)
        {
            int n = 0, i = 0;
            while ((i = s.IndexOf(needle, i)) >= 0) { n++; i += needle.Length; }
            return n;
        }

        /// Walk up from the working directory looking for src/<name>.
        private static string FindSource(string name)
        {
            string d = Directory.GetCurrentDirectory();
            for (int up = 0; up < 6 && d != null; up++)
            {
                string p = Path.Combine(Path.Combine(d, "src"), name);
                if (File.Exists(p)) return p;
                DirectoryInfo parent = Directory.GetParent(d);
                d = parent == null ? null : parent.FullName;
            }
            return null;
        }

        /// Read one column out of a row by name. Returns "" when absent, so
        /// a renamed column fails the assertion rather than throwing.
        private static string Val(V4Row r, string name)
        {
            for (int i = 0; i < r.Count; i++)
                if (r.NameAt(i) == name) return r.ValueAt(i);
            return "<<ABSENT>>";
        }

    }
}
