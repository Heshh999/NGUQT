// ============================================================================
// VecH1Tests.cs - deterministic tests for the VEC-H1 engine.
//
// VEC-H1 is the first hypothesis in this programme to be tested BEFORE its
// outcomes are seen, so these tests exist to pin the frozen rule while it is
// still honest to do so. Every one of them asserts a clause of the written
// definition, not an observed behaviour.
//
// The causality clause is the one that matters most. The prompt states it as
// a rejection rule: a 1m trigger at or before the parent's close is a
// LOOKAHEAD VIOLATION. That is tested directly, and the engine counts such
// attempts rather than silently dropping them.
// ============================================================================

using System;
using System.Collections.Generic;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace MnqTwoTests
{
    public static class VecH1Tests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        private static V4Bar B(DateTime open, int mins, double o, double h, double l, double c)
        {
            V4Bar b = new V4Bar();
            b.EtOpen = open; b.EtClose = open.AddMinutes(mins);
            b.Open = o; b.High = h; b.Low = l; b.Close = c; b.Volume = 1000;
            return b;
        }

        /// A parent 15m vector: bullish, range 100..120, body 110..118,
        /// so the LOWER wick is 110-100 = 10 pt = 50% of the 20 pt range.
        private static V4Vector Parent(DateTime createdEt, V4VectorColor col,
                                       double o, double h, double l, double c,
                                       double bodyHi, double bodyLo)
        {
            V4Vector v = new V4Vector();
            v.VectorId = "P1"; v.Tf = "15m"; v.TfMinutes = 15;
            v.CreatedEt = createdEt; v.Color = col;
            v.Tier = V4VectorClassifier.TierOf(col);
            v.Dir = V4VectorClassifier.DirOf(col);
            v.Open = o; v.High = h; v.Low = l; v.Close = c;
            v.BodyHigh = bodyHi; v.BodyLow = bodyLo;
            v.RangePts = h - l;
            return v;
        }

        private static V4Vector Trigger(V4VectorColor col)
        {
            V4Vector v = new V4Vector();
            v.VectorId = "T"; v.Tf = "1m"; v.TfMinutes = 1; v.Color = col;
            v.Tier = V4VectorClassifier.TierOf(col);
            v.Dir = V4VectorClassifier.DirOf(col);
            return v;
        }

        public static int Run()
        {
            passed = failed = 0;
            Console.WriteLine("VEC-H1 ENGINE TESTS");

            WickRule();
            Causality();
            WindowBounds();
            Proximity();
            Arms();
            ShortMirror();
            Stops();

            Console.WriteLine("VEC-H1: " + passed + " passed, " + failed + " failed");
            return failed;
        }

        // ------------------------------------------------------------------
        private static void WickRule()
        {
            Console.WriteLine(" wick rule (primary: >= 20% of parent range)");
            DateTime t0 = new DateTime(2026, 3, 2, 10, 0, 0);
            V4VecH1Engine e = new V4VecH1Engine("MNQ");

            // lower wick 10 of 20 pt range = 50%
            V4Vector big = Parent(t0, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            Check(e.On15mBar(B(t0.AddMinutes(-15), 15, 110, 120, 100, 118), big, 40) != null,
                  "50% lower wick on a GREEN parent qualifies");

            // lower wick 1 of 20 = 5%
            e.Clear();
            V4Vector tiny = Parent(t0, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 101);
            Check(e.On15mBar(B(t0.AddMinutes(-15), 15, 110, 120, 100, 118), tiny, 40) == null,
                  "5% lower wick is rejected");

            // exactly 20% must qualify - the rule is >=, not >
            e.Clear();
            V4Vector exact = Parent(t0, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 104);
            Check(e.On15mBar(B(t0.AddMinutes(-15), 15, 110, 120, 100, 118), exact, 40) != null,
                  "exactly 20% qualifies (the rule is >=)");

            // a non-vector parent never qualifies however large the wick
            e.Clear();
            V4Vector none = Parent(t0, V4VectorColor.NONE, 110, 120, 100, 118, 118, 110);
            Check(e.On15mBar(B(t0.AddMinutes(-15), 15, 110, 120, 100, 118), none, 40) == null,
                  "a non-vector parent never opens a window");

            // for a BULLISH parent the LOWER wick is the relevant one:
            // a big UPPER wick with a small lower wick must be rejected
            e.Clear();
            V4Vector upper = Parent(t0, V4VectorColor.GREEN, 102, 120, 100, 108, 108, 101);
            Check(e.On15mBar(B(t0.AddMinutes(-15), 15, 102, 120, 100, 108), upper, 40) == null,
                  "a GREEN parent is judged on its LOWER wick, not its upper");
        }

        // ------------------------------------------------------------------
        private static void Causality()
        {
            Console.WriteLine(" causality (the prompt's explicit rejection rule)");
            DateTime pc = new DateTime(2026, 3, 2, 10, 15, 0);   // parent close
            V4VecH1Engine e = new V4VecH1Engine("MNQ");
            V4Vector p = Parent(pc, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);

            // a 1m bar closing exactly AT the parent close is the last
            // minute INSIDE the parent candle - the BOUNDARY bar. Expected
            // once per parent (the field run showed 430 of these against
            // 431 parents and zero actual violations in the CSV).
            List<V4VecH1Signal> s = e.On1mBar(B(pc.AddMinutes(-1), 1, 105, 106, 100, 105),
                                              Trigger(V4VectorColor.GREEN));
            Check(s.Count == 0, "a 1m bar closing AT the parent close cannot trigger");
            Check(e.BoundaryExcluded == 1 && e.LookaheadRejected == 0,
                  "...and is counted as a BOUNDARY exclusion, NOT a violation");

            s = e.On1mBar(B(pc.AddMinutes(-5), 1, 105, 106, 100, 105), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 0 && e.LookaheadRejected == 1 && e.BoundaryExcluded == 1,
                  "a 1m bar closing STRICTLY BEFORE the close is a VIOLATION and counted apart");

            // the first legal bar closes one minute after the parent
            s = e.On1mBar(B(pc, 1, 118, 118, 100, 112), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 1, "the first bar closing AFTER the parent close may trigger");
            Check(e.LookaheadRejected == 1 && e.BoundaryExcluded == 1,
                  "...and adds to neither counter");
        }

        // ------------------------------------------------------------------
        private static void WindowBounds()
        {
            Console.WriteLine(" window = the immediately-following 15m candle only");
            DateTime pc = new DateTime(2026, 3, 2, 10, 15, 0);
            V4VecH1Engine e = new V4VecH1Engine("MNQ");
            V4Vector p = Parent(pc, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);

            Check(e.Active.WindowEndEt == pc.AddMinutes(15), "window ends 15 minutes after the parent close");

            // walk to the last legal minute without qualifying
            for (int i = 0; i < 14; i++)
                e.On1mBar(B(pc.AddMinutes(i), 1, 119, 119.5, 118.5, 119), null);
            List<V4VecH1Signal> s = e.On1mBar(B(pc.AddMinutes(14), 1, 118, 118, 100, 112),
                                              Trigger(V4VectorColor.GREEN));
            Check(s.Count == 1, "the bar closing exactly at the window end still counts");

            // one minute past the end, the parent expires
            e.Clear();
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);
            s = e.On1mBar(B(pc.AddMinutes(15), 1, 118, 118, 100, 112), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 0, "a bar past the window end cannot trigger");
            Check(e.Active == null, "...and the parent is expired");

            // a NEW qualifying 15m vector replaces the old parent
            e.Clear();
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);
            V4Vector p2 = Parent(pc.AddMinutes(15), V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            e.On15mBar(B(pc, 15, 110, 120, 100, 118), p2, 40);
            Check(e.Active != null && e.Active.CloseEt == pc.AddMinutes(15),
                  "a new qualifying parent replaces the previous one - windows never overlap");
        }

        // ------------------------------------------------------------------
        private static void Proximity()
        {
            Console.WriteLine(" proximity (into the wick zone OR within 0.10 x ATR)");
            DateTime pc = new DateTime(2026, 3, 2, 10, 15, 0);
            // parent low 100, body low 110, ATR 40 -> band = 4 -> threshold
            // = max(110, 104) = 110, i.e. the wick edge is the looser test
            V4VecH1Engine e = new V4VecH1Engine("MNQ");
            V4Vector p = Parent(pc, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);
            Check(Math.Abs(e.Active.NearThreshold() - 110) < 1e-9,
                  "threshold is the LOOSER of wick edge and ATR band");

            // a bar whose low stops at 112 is not near
            List<V4VecH1Signal> s = e.On1mBar(B(pc, 1, 118, 118, 112, 115), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.B_VECTOR_AWAY,
                  "a vector stopping above the wick zone is ARM B, not ARM C");

            // a later bar reaching 108 is inside the wick zone
            s = e.On1mBar(B(pc.AddMinutes(1), 1, 115, 115, 108, 112), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.C_FULL,
                  "a vector trading into the wick zone is ARM C");
            Check(s[0].TradedIntoWick && !s[0].TouchedExtreme,
                  "...recorded as into-wick but NOT a touch of the extreme");
            Check(Math.Abs(s[0].DistToExtremePts - 8) < 1e-9, "distance to extreme recorded in points");
            Check(Math.Abs(s[0].DistToExtremeAtr - 0.2) < 1e-9, "...and in ATR units");

            // when the ATR band is the looser test it governs instead
            V4VecH1Engine e2 = new V4VecH1Engine("MNQ");
            V4Vector tightBody = Parent(pc, V4VectorColor.GREEN, 104, 120, 100, 118, 118, 104);
            e2.On15mBar(B(pc.AddMinutes(-15), 15, 104, 120, 100, 118), tightBody, 100);
            Check(Math.Abs(e2.Active.NearThreshold() - 110) < 1e-9,
                  "with ATR 100 the 0.10 band (=10) is looser than the wick edge (=104)");
        }

        // ------------------------------------------------------------------
        private static void Arms()
        {
            Console.WriteLine(" matched arms A / B / C against the same parent");
            DateTime pc = new DateTime(2026, 3, 2, 10, 15, 0);
            V4VecH1Engine e = new V4VecH1Engine("MNQ");
            V4Vector p = Parent(pc, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);

            // bar 1: opens the window at 119, no retrace yet, no vector
            List<V4VecH1Signal> s = e.On1mBar(B(pc, 1, 119, 119.5, 119, 119.2), null);
            Check(s.Count == 0, "no retrace and no vector fires nothing");
            Check(!e.Active.RetraceSeen, "retrace not yet seen");

            // bar 2: trades down into the wick zone, NOT a vector -> ARM A
            s = e.On1mBar(B(pc.AddMinutes(1), 1, 119, 119, 108, 112), null);
            Check(e.Active.RetraceSeen, "trading below the window open sets retraceSeen");
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.A_LOCATION_ONLY,
                  "reaching the zone without a qualifying vector is ARM A");

            // bar 3: a qualifying vector in the zone -> ARM C on the SAME parent
            s = e.On1mBar(B(pc.AddMinutes(2), 1, 112, 113, 106, 111), Trigger(V4VectorColor.BLUE));
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.C_FULL,
                  "a BLUE vector in the zone is ARM C (GREEN or BLUE both qualify long)");

            // bar 4: another qualifying vector in the zone - C already fired
            s = e.On1mBar(B(pc.AddMinutes(3), 1, 111, 112, 107, 110), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 0, "each arm fires at most ONCE per parent");

            // wrong-direction vector never qualifies
            V4VecH1Engine e3 = new V4VecH1Engine("MNQ");
            e3.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);
            e3.On1mBar(B(pc, 1, 119, 119, 119, 119), null);
            s = e3.On1mBar(B(pc.AddMinutes(1), 1, 119, 119, 108, 112), Trigger(V4VectorColor.RED));
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.A_LOCATION_ONLY,
                  "a RED vector on a LONG parent does not qualify - it falls to ARM A");

            Check(V4VecH1Engine.ColorQualifies(V4VectorColor.GREEN, 1)
                  && V4VecH1Engine.ColorQualifies(V4VectorColor.BLUE, 1)
                  && !V4VecH1Engine.ColorQualifies(V4VectorColor.RED, 1)
                  && !V4VecH1Engine.ColorQualifies(V4VectorColor.NONE, 1),
                  "long qualifies on GREEN|BLUE only");
            Check(V4VecH1Engine.ColorQualifies(V4VectorColor.RED, -1)
                  && V4VecH1Engine.ColorQualifies(V4VectorColor.VIOLET, -1)
                  && !V4VecH1Engine.ColorQualifies(V4VectorColor.GREEN, -1),
                  "short qualifies on RED|VIOLET only");

            // ARM A requires the retrace; ARM B does not
            V4VecH1Engine e4 = new V4VecH1Engine("MNQ");
            e4.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);
            s = e4.On1mBar(B(pc, 1, 119, 121, 119, 120), Trigger(V4VectorColor.GREEN));
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.B_VECTOR_AWAY && !s[0].RetraceSeen,
                  "ARM B can fire without a retrace, and records retraceSeen=false");
        }

        // ------------------------------------------------------------------
        private static void ShortMirror()
        {
            Console.WriteLine(" short mirror");
            DateTime pc = new DateTime(2026, 3, 2, 10, 15, 0);
            V4VecH1Engine e = new V4VecH1Engine("MNQ");
            // bearish parent: range 100..120, body 102..110, UPPER wick 10 = 50%
            V4Vector p = Parent(pc, V4VectorColor.RED, 110, 120, 100, 102, 110, 102);
            V4VecH1Parent got = e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 102), p, 40);
            Check(got != null && got.Side == -1, "a RED parent with a 50% UPPER wick opens a SHORT window");
            Check(Math.Abs(got.Extreme - 120) < 1e-9, "the frozen extreme is the parent HIGH");
            Check(Math.Abs(got.WickPctOfRange - 50) < 1e-9, "upper wick measured as 50% of range");

            e.On1mBar(B(pc, 1, 101, 101.5, 101, 101.2), null);
            List<V4VecH1Signal> s = e.On1mBar(B(pc.AddMinutes(1), 1, 101, 112, 101, 108),
                                              Trigger(V4VectorColor.VIOLET));
            Check(e.Active.RetraceSeen, "trading above the window open sets retraceSeen on a short");
            Check(s.Count == 1 && s[0].Arm == V4VecH1Arm.C_FULL,
                  "a VIOLET vector into the upper wick zone is ARM C");
            Check(Math.Abs(s[0].DistToExtremePts - 8) < 1e-9, "short distance measured from the HIGH");
        }

        // ------------------------------------------------------------------
        private static void Stops()
        {
            Console.WriteLine(" stop references (primary = 1.5 x parent ATR)");
            DateTime pc = new DateTime(2026, 3, 2, 10, 15, 0);
            V4VecH1Engine e = new V4VecH1Engine("MNQ");
            V4Vector p = Parent(pc, V4VectorColor.GREEN, 110, 120, 100, 118, 118, 110);
            e.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 118), p, 40);
            e.On1mBar(B(pc, 1, 119, 119, 119, 119), null);
            List<V4VecH1Signal> s = e.On1mBar(B(pc.AddMinutes(1), 1, 119, 119, 108, 112),
                                              Trigger(V4VectorColor.GREEN));
            Check(s.Count == 1, "signal fired");

            double t, m, st;
            V4VecH1Engine.StopRefs(s[0], 0.25, out t, out m, out st);
            Check(Math.Abs(t - 107.75) < 1e-9, "TIGHT = 1m trigger low - one tick");
            Check(Math.Abs(m - (112 - 60)) < 1e-9, "MEDIUM = entry - 1.5 x parent ATR (the race stop)");
            Check(Math.Abs(st - 99.75) < 1e-9, "STRUCTURAL = parent extreme - one tick");
            Check(m < t, "the ATR stop is WIDER than the candle stop - the measured choice");

            // short mirror
            V4VecH1Engine e2 = new V4VecH1Engine("MNQ");
            V4Vector ps = Parent(pc, V4VectorColor.RED, 110, 120, 100, 102, 110, 102);
            e2.On15mBar(B(pc.AddMinutes(-15), 15, 110, 120, 100, 102), ps, 40);
            e2.On1mBar(B(pc, 1, 101, 101, 101, 101), null);
            List<V4VecH1Signal> s2 = e2.On1mBar(B(pc.AddMinutes(1), 1, 101, 112, 101, 108),
                                                Trigger(V4VectorColor.VIOLET));
            V4VecH1Engine.StopRefs(s2[0], 0.25, out t, out m, out st);
            Check(Math.Abs(t - 112.25) < 1e-9, "short TIGHT = trigger high + one tick");
            Check(Math.Abs(m - (108 + 60)) < 1e-9, "short MEDIUM = entry + 1.5 x ATR");
            Check(Math.Abs(st - 120.25) < 1e-9, "short STRUCTURAL = parent high + one tick");
        }
    }
}
