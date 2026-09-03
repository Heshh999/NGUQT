// ======================================================================
// MLES-CAPTURE-1.2 LIFECYCLE HARNESS — actually EXERCISES the writer,
// rotation, concurrency, disconnect and shutdown code of MlesV12Core
// (the identical core the NinjaTrader host wraps). Pure C#; run with
// mono. Emits "HARNESS <scenario> key=value ..." lines for the Python
// suite, and leaves real capture files for the v1.2 auditor.
// Synthetic events verify CODE BEHAVIOR only, never market evidence.
// ======================================================================
using System;
using System.Collections.Generic;
using System.IO;
using System.Threading;
using Mles.Capture.V12;

public static class MlesV12Harness
{
    private static string Dir(string root, string name)
    {
        string d = Path.Combine(root, name);
        Directory.CreateDirectory(d);
        return d;
    }

    private static void Pump(MlesV12Core c, string ses, string con,
                             int n, int seed)
    {
        Random r = new Random(seed);
        DateTime ex = DateTime.UtcNow;
        for (int i = 0; i < n; i++)
        {
            c.OnDepth(ses, con, "ADD", "BID", i % 10,
                      15000.0 - 0.25 * (i % 10), 10 + i % 5, ex);
            c.OnDepth(ses, con, "ADD", "ASK", i % 10,
                      15000.25 + 0.25 * (i % 10), 9 + i % 5, ex);
            c.OnQuote(ses, con, "BID", 15000.0, 12, ex);
            c.OnQuote(ses, con, "ASK", 15000.25, 9, ex);
            c.OnTrade(ses, con, 15000.25, 2, ex);
            c.OnDepth(ses, con, "UPDATE", "ASK", 0, 15000.25, 5, ex);
            c.OnDepth(ses, con, "REMOVE", "BID", 9, 14997.75, 0, ex);
            if (r.Next(50) == 0) Thread.Sleep(1);
        }
    }

    private static int LiveWorkers()
    {
        int n = 0;
        foreach (Thread t in AllStarted)
            if (t.IsAlive) n++;
        return n;
    }

    private static readonly List<Thread> AllStarted = new List<Thread>();

    private static void Report(string scen, params string[] kv)
    {
        Console.WriteLine("HARNESS " + scen + " " + string.Join(" ", kv));
    }

    public static int Main(string[] args)
    {
        string root = args.Length > 0 ? args[0] : "harness_out";
        Directory.CreateDirectory(root);

        // ---- 1/2: two sessions, then three consecutive rolls --------
        {
            var c = new MlesV12Core(Dir(root, "rolls"), "NQ",
                                    250000, 10, 0.05, 0.5);
            c.Start();
            string[] sessions = { "20260901", "20260902", "20260903",
                                  "20260904" };
            foreach (string s in sessions)
                Pump(c, s, "NQ 12-26", 40, 7);
            c.Shutdown();
            Report("rolls", "runs=" + c.RunsFinalized,
                   "opened=" + c.RunsOpened,
                   "recovery=" + (c.RecoveryArtifact ?? "none"));
        }

        // ---- 3: contract roll isolates both contracts ---------------
        {
            var c = new MlesV12Core(Dir(root, "croll"), "NQ",
                                    250000, 10, 0.05, 0.5);
            c.Start();
            Pump(c, "20261218", "NQ 12-26", 40, 11);
            Pump(c, "20261218", "NQ 03-27", 40, 13);
            c.Shutdown();
            Report("croll", "runs=" + c.RunsFinalized);
        }

        // ---- 7: concurrent producers, randomized delays -------------
        {
            var c = new MlesV12Core(Dir(root, "conc"), "NQ",
                                    500000, 10, 0.05, 5.0);
            c.Start();
            Pump(c, "20260901", "NQ 12-26", 2, 99);   // full coverage
            int perThread = 400;
            Thread[] prod = new Thread[6];
            for (int k = 0; k < prod.Length; k++)
            {
                int seed = 100 + k;
                prod[k] = new Thread(() =>
                {
                    Random r = new Random(seed);
                    DateTime ex = DateTime.UtcNow;
                    for (int i = 0; i < perThread; i++)
                    {
                        int pick = r.Next(3);
                        if (pick == 0)
                            c.OnQuote("20260901", "NQ 12-26",
                                r.Next(2) == 0 ? "BID" : "ASK",
                                15000.0, 10, ex);
                        else if (pick == 1)
                            c.OnTrade("20260901", "NQ 12-26",
                                      15000.25, 1, ex);
                        else
                            c.OnDepth("20260901", "NQ 12-26",
                                "UPDATE", r.Next(2) == 0 ? "BID" : "ASK",
                                r.Next(10), 15000.0, 5, ex);
                        if (r.Next(97) == 0) Thread.Sleep(0);
                    }
                });
                AllStarted.Add(prod[k]);
                prod[k].Start();
            }
            foreach (Thread t in prod) t.Join();
            c.Shutdown();
            Report("conc", "runs=" + c.RunsFinalized,
                   "produced=" + (prod.Length * perThread));
        }

        // ---- 9: large queued rotation loses no events ---------------
        {
            var c = new MlesV12Core(Dir(root, "bigq"), "NQ",
                                    500000, 10, 0.05, 5.0);
            c.Start();
            // burst both sessions as fast as possible so a large queue
            // spans the rotation point (with full depth coverage)
            Pump(c, "20260901", "NQ 12-26", 2, 41);
            for (int i = 0; i < 3000; i++)
                c.OnTrade("20260901", "NQ 12-26", 15000.0, 1,
                          DateTime.UtcNow);
            Pump(c, "20260902", "NQ 12-26", 2, 43);
            for (int i = 0; i < 3000; i++)
                c.OnTrade("20260902", "NQ 12-26", 15000.0, 1,
                          DateTime.UtcNow);
            c.Shutdown();
            Report("bigq", "runs=" + c.RunsFinalized, "sent=6000");
        }

        // ---- 10: termination before the first event -----------------
        {
            var c = new MlesV12Core(Dir(root, "noevent"), "NQ",
                                    1000, 10, 0.05, 0.5);
            c.Start();
            c.Shutdown();
            string[] files = Directory.GetFiles(Dir(root, "noevent"));
            Report("noevent", "files=" + files.Length,
                   "runs=" + c.RunsFinalized);
        }

        // ---- 12: restart creates a new capture instance + run -------
        {
            string d = Dir(root, "restart");
            var a = new MlesV12Core(d, "NQ", 1000, 10, 0.05, 0.5);
            a.Start();
            Pump(a, "20260901", "NQ 12-26", 10, 3);
            a.Shutdown();
            var b = new MlesV12Core(d, "NQ", 1000, 10, 0.05, 0.5);
            b.Start();
            Pump(b, "20260901", "NQ 12-26", 10, 5);
            b.Shutdown();
            Report("restart", "idA=" + a.CaptureInstanceId,
                   "idB=" + b.CaptureInstanceId,
                   "distinct=" + (a.CaptureInstanceId !=
                                  b.CaptureInstanceId ? "1" : "0"));
        }

        // ---- 13/14: disconnect invalidates; reconnect resyncs -------
        {
            var c = new MlesV12Core(Dir(root, "disco"), "NQ",
                                    250000, 3, 0.05, 0.5);
            c.Start();
            string s = "20260901", k = "NQ 12-26";
            DateTime ex = DateTime.UtcNow;
            // build the book to declared depth 3 -> BOOK_READY
            for (int l = 0; l < 3; l++)
            {
                c.OnDepth(s, k, "ADD", "BID", l, 15000 - 0.25 * l, 10, ex);
                c.OnDepth(s, k, "ADD", "ASK", l, 15000.25 + 0.25 * l, 9, ex);
            }
            c.OnTrade(s, k, 15000.25, 1, ex);          // ready interval
            c.OnConnection(s, k, "DISCONNECTED", "DISCONNECTED");
            c.OnTrade(s, k, 15000.25, 1, ex);          // suppressed
            c.OnConnection(s, k, "CONNECTED", "CONNECTED");
            c.OnTrade(s, k, 15000.25, 1, ex);          // still suppressed
            for (int l = 0; l < 3; l++)                // full resync
            {
                c.OnDepth(s, k, "ADD", "BID", l, 15000 - 0.25 * l, 10, ex);
                c.OnDepth(s, k, "ADD", "ASK", l, 15000.25 + 0.25 * l, 9, ex);
            }
            c.OnTrade(s, k, 15000.25, 1, ex);          // ready again
            c.OnDepth(s, k, "UPDATE", "BID", 0, 15000.0, 8, ex);
            c.OnDepth(s, k, "REMOVE", "ASK", 2, 15000.75, 0, ex);
            c.Shutdown();
            Report("disco", "runs=" + c.RunsFinalized);
        }

        // ---- lvlrun: run-lifetime depth maxima survive a reconnect ---
        // (build 1.2.1 repair: a real session closed after a reconnect
        // with a shallower book and reported maxBidLevelSeen=0 beside
        // 10.9M depth rows). Book reaches 3 levels, reconnect, rebuild
        // to only 2 levels, shutdown: post-reconnect field = 2, run
        // field = 3, BOOK_READY fires exactly once.
        {
            var c = new MlesV12Core(Dir(root, "lvlrun"), "NQ",
                                    250000, 3, 0.05, 0.5);
            c.Start();
            string s = "20260901", k = "NQ 12-26";
            DateTime ex = DateTime.UtcNow;
            for (int l = 0; l < 3; l++)
            {
                c.OnDepth(s, k, "ADD", "BID", l, 15000 - 0.25 * l, 10, ex);
                c.OnDepth(s, k, "ADD", "ASK", l, 15000.25 + 0.25 * l, 9, ex);
            }
            c.OnTrade(s, k, 15000.25, 1, ex);
            c.OnConnection(s, k, "DISCONNECTED", "DISCONNECTED");
            c.OnConnection(s, k, "CONNECTED", "CONNECTED");
            for (int l = 0; l < 2; l++)                // shallower rebuild
            {
                c.OnDepth(s, k, "ADD", "BID", l, 15000 - 0.25 * l, 10, ex);
                c.OnDepth(s, k, "ADD", "ASK", l, 15000.25 + 0.25 * l, 9, ex);
            }
            c.OnDepth(s, k, "UPDATE", "BID", 0, 15000.0, 8, ex);
            c.OnDepth(s, k, "REMOVE", "ASK", 1, 15000.50, 0, ex);
            c.OnTrade(s, k, 15000.25, 1, ex);
            c.Shutdown();
            Report("lvlrun", "runs=" + c.RunsFinalized);
        }

        // ---- NQ + MNQ paired capture for overlap auditing -----------
        {
            string d = Dir(root, "pair");
            var nq = new MlesV12Core(d, "NQ", 250000, 10, 0.05, 0.5);
            var mnq = new MlesV12Core(d, "MNQ", 250000, 10, 0.05, 0.5);
            nq.Start();
            mnq.Start();
            Thread tn = new Thread(() =>
            {
                for (int i = 0; i < 12; i++)
                {
                    Pump(nq, "20260901", "NQ 12-26", 4, 17 + i);
                    Thread.Sleep(4);
                }
            });
            Thread tm = new Thread(() =>
            {
                for (int i = 0; i < 12; i++)
                {
                    Pump(mnq, "20260901", "MNQ 12-26", 4, 19 + i);
                    Thread.Sleep(4);
                }
            });
            tn.Start(); tm.Start();
            tn.Join(); tm.Join();
            nq.Shutdown();
            mnq.Shutdown();
            Report("pair", "nq=" + nq.RunsFinalized,
                   "mnq=" + mnq.RunsFinalized);
        }

        // ---- 15: NQ and MNQ from DIFFERENT sessions (must fail) -----
        {
            string d = Dir(root, "pairbad");
            var nq = new MlesV12Core(d, "NQ", 250000, 10, 0.05, 0.5);
            var mnq = new MlesV12Core(d, "MNQ", 250000, 10, 0.05, 0.5);
            nq.Start();
            mnq.Start();
            Pump(nq, "20260901", "NQ 12-26", 20, 23);
            Pump(mnq, "20260902", "MNQ 12-26", 20, 29);
            nq.Shutdown();
            mnq.Shutdown();
            Report("pairbad", "nq=" + nq.RunsFinalized,
                   "mnq=" + mnq.RunsFinalized);
        }

        // ---- 16: same session, nearly disjoint windows (low overlap) -
        {
            string d = Dir(root, "pairlow");
            var nq = new MlesV12Core(d, "NQ", 250000, 10, 0.05, 0.5);
            nq.Start();
            Pump(nq, "20260901", "NQ 12-26", 20, 31);
            nq.Shutdown();
            Thread.Sleep(300);
            var mnq = new MlesV12Core(d, "MNQ", 250000, 10, 0.05, 0.5);
            mnq.Start();
            Pump(mnq, "20260901", "MNQ 12-26", 20, 37);
            mnq.Shutdown();
            Report("pairlow", "nq=" + nq.RunsFinalized,
                   "mnq=" + mnq.RunsFinalized);
        }

        Report("done", "ok=1");
        return 0;
    }
}
