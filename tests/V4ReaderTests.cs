// ============================================================================
// V4ReaderTests.cs - tests for the volumetric reflection reader.
//
// This exists because the reader failed silently on a series that was
// genuinely Volumetric, and cost three full multi-hour runs to diagnose.
//
// The reader reaches into NinjaTrader types it cannot reference at compile
// time, so nothing about it is checked by the compiler. The only way to test
// it off-platform is to hand it objects shaped the way NinjaTrader's are, and
// assert it finds what it is looking for. These fakes mirror the real API:
//
//   VolumetricBarsType   has  Volumes            -> VolumetricBar[]
//   VolumetricBar        has  GetAskVolumeForPrice(double)
//                             GetBidVolumeForPrice(double)
//
// The original reader expected VolumetricBar to expose a price -> level
// DICTIONARY instead of those methods. It found the array, indexed it
// correctly, got a real bar back, asked for a member that does not exist, and
// returned false without recording why. A test at this level would have caught
// it before the first run rather than after the third.
// ============================================================================

using System;
using System.Collections.Generic;
using NinjaTrader.NinjaScript.Strategies;
using NinjaTrader.NinjaScript.Strategies.MnqV4;

namespace MnqTwoTests
{
    // ---- fakes shaped like the NinjaTrader types -------------------------

    /// Mirrors NinjaTrader's VolumetricBar: per-price figures are reached
    /// through METHODS, not through a public dictionary.
    public class FakeVolumetricBar
    {
        public readonly Dictionary<double, double> Ask = new Dictionary<double, double>();
        public readonly Dictionary<double, double> Bid = new Dictionary<double, double>();
        public double GetAskVolumeForPrice(double price)
        {
            double v; return Ask.TryGetValue(price, out v) ? v : 0;
        }
        public double GetBidVolumeForPrice(double price)
        {
            double v; return Bid.TryGetValue(price, out v) ? v : 0;
        }
    }

    /// Mirrors VolumetricBarsType: Volumes is an ARRAY OF BARS.
    public class FakeVolumetricBarsType
    {
        public FakeVolumetricBar[] Volumes;
    }

    /// Mirrors Bars.
    public class FakeBars
    {
        public object BarsType;
    }

    /// A bars type with no Volumes at all - an ordinary Minute series.
    public class FakePlainBarsType { public int Value; }

    /// A volumetric bar that exposes a price map instead of methods, to prove
    /// the fallback path still works on a build that differs.
    public class FakeDictionaryBar
    {
        public readonly System.Collections.SortedList Volumes = new System.Collections.SortedList();
    }
    public class FakeLevel { public double AskVolume; public double BidVolume; }

    public static class V4ReaderTests
    {
        private static int passed, failed;
        private static void Check(bool c, string name)
        {
            if (c) { passed++; Console.WriteLine("  PASS  " + name); }
            else { failed++; Console.WriteLine("  FAIL  " + name); }
        }

        private static V4FootprintBar Bar(double lo, double hi)
        {
            V4FootprintBar b = new V4FootprintBar();
            b.EtOpen = new DateTime(2026, 3, 2, 9, 30, 0);
            b.EtClose = b.EtOpen.AddMinutes(1);
            b.Open = lo; b.High = hi; b.Low = lo; b.Close = hi; b.Volume = 100;
            return b;
        }

        public static int Run()
        {
            Console.WriteLine();
            Console.WriteLine("V4 VOLUMETRIC READER");
            Console.WriteLine("--------------------");
            passed = 0; failed = 0;

            // ---- the real API shape: methods, not a dictionary -------------
            FakeVolumetricBar vb = new FakeVolumetricBar();
            vb.Ask[20000.00] = 50; vb.Bid[20000.00] = 20;
            vb.Ask[20000.25] = 40; vb.Bid[20000.25] = 10;
            vb.Ask[20000.50] = 5;  vb.Bid[20000.50] = 60;
            FakeVolumetricBarsType bt = new FakeVolumetricBarsType();
            bt.Volumes = new FakeVolumetricBar[] { vb };
            FakeBars bars = new FakeBars(); bars.BarsType = bt;

            V4VolumetricReader r = new V4VolumetricReader();
            V4FootprintBar into = Bar(20000.00, 20000.50);
            bool ok = r.TryRead(bars, 0, into, 0.25);

            Check(ok, "a volumetric bar exposing GetAskVolumeForPrice is read");
            Check(into.HasLevels && into.Levels.Count == 3,
                  "every traded price in the bar's range becomes a level");
            Check(Math.Abs(into.AskTotal - 95) < 1e-9 && Math.Abs(into.BidTotal - 90) < 1e-9,
                  "ask and bid volumes come back as the platform reported them");
            Check(Math.Abs(into.Delta - 5) < 1e-9,
                  "delta is ask minus bid, recomputed from the levels just read");
            Check(r.LastError.Length == 0, "a successful read records no error");
            Check(r.Diagnostics.Contains("GetAskVolumeForPrice"),
                  "the reader reports which accessor it bound to");

            // prices with no trades are skipped, not written as zero rows
            FakeVolumetricBar sparse = new FakeVolumetricBar();
            sparse.Ask[20000.00] = 10; sparse.Bid[20001.00] = 10;
            FakeVolumetricBarsType bt2 = new FakeVolumetricBarsType();
            bt2.Volumes = new FakeVolumetricBar[] { sparse };
            FakeBars bars2 = new FakeBars(); bars2.BarsType = bt2;
            V4FootprintBar into2 = Bar(20000.00, 20001.00);
            new V4VolumetricReader().TryRead(bars2, 0, into2, 0.25);
            Check(into2.Levels.Count == 2,
                  "prices where nothing traded are skipped rather than written as zeros");

            // ---- an ordinary Minute series is refused, and says so ---------
            FakeBars plain = new FakeBars(); plain.BarsType = new FakePlainBarsType();
            V4VolumetricReader r3 = new V4VolumetricReader();
            V4FootprintBar into3 = Bar(20000, 20001);
            Check(!r3.TryRead(plain, 0, into3, 0.25),
                  "a non-volumetric series is refused");
            Check(r3.LastError.Contains("not Volumetric"),
                  "and the refusal names the reason");

            // ---- an out-of-range index is named, not silently false --------
            V4VolumetricReader r4 = new V4VolumetricReader();
            V4FootprintBar into4 = Bar(20000, 20000.5);
            Check(!r4.TryRead(bars, 99, into4, 0.25), "an index past the array fails");
            Check(r4.LastError.Contains("outside the Volumes array")
                  || r4.LastError.Contains("outside"),
                  "and says the index was out of range, pointing at bars look back");

            // Every failure path must leave a reason behind. The whole cost of
            // this bug was three silent returns.
            Check(r4.LastError.Length > 0 && r3.LastError.Length > 0,
                  "no failure path returns false without recording why");

            // ---- the dictionary fallback still works -----------------------
            FakeDictionaryBar db = new FakeDictionaryBar();
            FakeLevel l1 = new FakeLevel(); l1.AskVolume = 30; l1.BidVolume = 12;
            db.Volumes.Add(20000.00, l1);
            object dbt = new DictHolder(db);
            FakeBars bars5 = new FakeBars(); bars5.BarsType = dbt;
            V4VolumetricReader r5 = new V4VolumetricReader();
            V4FootprintBar into5 = Bar(20000, 20000.25);
            bool ok5 = r5.TryRead(bars5, 0, into5, 0.25);
            Check(ok5 && Math.Abs(into5.AskTotal - 30) < 1e-9,
                  "a build exposing a price map instead of methods still reads");

            Console.WriteLine();
            Console.WriteLine(string.Format("V4 READER: {0} passed, {1} failed", passed, failed));
            return failed;
        }

        /// Wraps the dictionary-style bar in an array, like the real BarsType.
        public class DictHolder
        {
            public FakeDictionaryBar[] Volumes;
            public DictHolder(FakeDictionaryBar b) { Volumes = new FakeDictionaryBar[] { b }; }
        }
    }
}
