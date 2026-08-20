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
    }
}
