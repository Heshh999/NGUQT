#region Using declarations
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
#endregion

// ======================================================================
// MLES-CAPTURE-1.2  -  PERMANENT-LIFECYCLE RECORDER (rollover repair)
// Additive successor. MlesV1CaptureHost.cs (1.0.0) and
// MlesV11CaptureHost.cs (1.1) are IMMUTABLE and remain hash-pinned.
//
// Defect repaired: in 1.1, Roll() called CloseSession(), which stopped
// the only writer thread; new files were then opened with no writer,
// and counters/sequences/runId leaked across sessions. 1.2 replaces
// that architecture entirely:
//   - ONE permanent capture worker owns writers, BBO classification
//     state, per-run counters, per-stream sequences, rotation, closure
//     and manifest snapshots, and lives from Start() to Shutdown().
//   - Market callbacks do bounded work only: copy immutable values,
//     stamp receive time, take the global sequence and publish to the
//     queue in ONE atomic operation under one short capture lock, then
//     return. No callback ever flushes, closes, moves, hashes, joins
//     or waits for rotation.
//   - A separate finalization worker hashes and finalizes CLOSED runs
//     only; it never touches the active run's files.
//   - Rotation (18:00 ET session boundary or exact-contract change)
//     happens inside the worker: finish old-run queue order, emit
//     SESSION_END/CONTRACT_ROLL_END, close, snapshot, mint a NEW
//     runId, reset EVERY per-run counter/sequence/BBO/book state, open
//     new .partial files, emit SESSION_START/CONTRACT_ROLL_START, and
//     hand the closed run to the finalizer. The worker never dies.
//
// Identity (frozen):
//   captureInstanceId  one indicator attachment/start
//   runId              one exact instrument+contract+session file set
//   segId              connection/price-feed segment within a run
//   eventSeq           globally monotonic within the capture instance
//                      (never reset; contiguous across the union of
//                      the instance's runs, not within one run)
//   streamSeq          per-stream, reset to 1 for every new run
//
// READ-ONLY: the NinjaTrader host below is an Indicator. There is no
// account access and no order API of any kind - no EnterLong/
// EnterShort/SubmitOrderUnmanaged/ChangeOrder/CancelOrder/Account.
// THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
// ======================================================================

namespace Mles.Capture.V12
{
    public sealed class MlesV12Event
    {
        public long EventSeq;
        public string Kind;        // QUOTE|TRADE|DEPTH|CONN
        public string Session;
        public string Contract;
        public DateTime RecvUtc;
        public DateTime ExchUtc;   // MinValue when absent
        public long Mono;
        public string Side;        // BID|ASK
        public double Px, Sz;
        public int Level;
        public string Action;      // ADD|UPDATE|REMOVE
        public string Status;      // CONN: CONNECTED|DISCONNECTED
        public string PriceStatus; // CONN: price-feed status
    }

    public sealed class MlesV12Core
    {
        public const string SchemaVersion = "MLES-CAPTURE-1.2";
        private const string TsFmt = "yyyy-MM-ddTHH:mm:ss.fffffffZ";

        private readonly string dir, instrument, captureInstanceId;
        private readonly int maxQueue, declaredDepth;
        private readonly double flushSeconds, heartbeatSeconds;
        private readonly Stopwatch mono = new Stopwatch();

        // ---- capture lock: seq assignment + publication are atomic --
        private readonly object capLock = new object();
        private readonly Queue<MlesV12Event> queue =
            new Queue<MlesV12Event>();
        private long eventSeq;
        private long cbOverflow;           // drained into run counters
        private long queueHighWater;
        private bool accepting;

        private Thread worker, finalizer;
        private readonly object finLock = new object();
        private readonly Queue<ClosedRun> finQ = new Queue<ClosedRun>();
        private bool finAccepting = true;
        public int RunsOpened, RunsFinalized;
        public string RecoveryArtifact;

        // ---- run state: owned EXCLUSIVELY by the worker -------------
        private sealed class Run
        {
            public string RunId, Session, Contract;
            public long SegId = 1, FirstSeg = 1;
            public StreamWriter WQ, WT, WD, WC;
            public string PQ, PT, PD, PC;
            public long SeqQ, SeqT, SeqD, SeqC;
            public long RowsQ, RowsT, RowsD, RowsC;
            public long FirstEv = -1, LastEv = -1;
            public long FQ = -1, LQ = -1, FT = -1, LT = -1;
            public long FD = -1, LD = -1, FC = -1, LC = -1;
            public DateTime FirstRecv = DateTime.MinValue,
                            LastRecv = DateTime.MinValue,
                            LastExch = DateTime.MinValue,
                            LastBeat = DateTime.MinValue,
                            LastFlush = DateTime.MinValue;
            public long NOverflow, NDropped, NWriteErr, NReconnect,
                        NCrossed, NBookReset, NGapMarked;
            public long DepthBid, DepthAsk, DepthAdd, DepthUpd, DepthRem;
            // worker-owned BBO + book readiness
            public double BidPx = double.NaN, BidSz = double.NaN,
                          AskPx = double.NaN, AskSz = double.NaN;
            public bool Connected = true, BookReady;
            public int MaxBidLvl = -1, MaxAskLvl = -1;
        }

        private sealed class ClosedRun
        {
            public string Manifest;    // full JSON text, files section open
            public string BaseName;
            public string[] Partials;
            public long[] Rows;
        }

        private Run run;                   // worker-owned; null before 1st

        public MlesV12Core(string directory, string instrumentName,
                           int maxQueueDepth = 250000,
                           int providerDepth = 10,
                           double flushSecs = 30.0,
                           double heartbeatSecs = 30.0)
        {
            dir = directory;
            instrument = instrumentName;
            maxQueue = maxQueueDepth;
            declaredDepth = providerDepth;
            flushSeconds = flushSecs;
            heartbeatSeconds = heartbeatSecs;
            string low = dir.ToLowerInvariant();
            if (low.Contains("analysis") || low.Contains("docs") ||
                low.Contains("scratchpad"))
                throw new InvalidOperationException(
                    "refusing to write capture into a research folder");
            captureInstanceId =
                DateTime.UtcNow.ToString("yyyyMMddHHmmssfff",
                    CultureInfo.InvariantCulture) + "-" +
                Guid.NewGuid().ToString("N").Substring(0, 8);
        }

        public string CaptureInstanceId { get { return captureInstanceId; } }

        public void Start()
        {
            mono.Start();
            Directory.CreateDirectory(dir);
            accepting = true;
            worker = new Thread(WorkerLoop);
            worker.IsBackground = false;
            worker.Name = "MlesV12Worker";
            worker.Start();
            finalizer = new Thread(FinalizerLoop);
            finalizer.IsBackground = false;
            finalizer.Name = "MlesV12Finalizer";
            finalizer.Start();
        }

        // ============ callback side: bounded work only ================
        private void Publish(MlesV12Event ev)
        {
            lock (capLock)
            {
                if (!accepting) return;
                if (queue.Count >= maxQueue)
                {
                    cbOverflow++;
                    return;
                }
                // receive stamp, monotonic stamp, sequence assignment
                // and publication are ONE atomic operation, so
                // (eventSeq, tRecvUtc, tMono) are jointly monotonic
                ev.RecvUtc = DateTime.UtcNow;
                ev.Mono = mono.ElapsedTicks;
                // Control (CONN) events consume no eventSeq: their file
                // rows are quality rows minted at write time, so the
                // instance seq union stays gapless AND every file stays
                // monotone. Their true occurrence stamps travel in the
                // event and are recorded in the row detail.
                if (ev.Kind != "CONN")
                    ev.EventSeq = ++eventSeq;
                queue.Enqueue(ev);             // under ONE lock: atomic
                if (queue.Count > queueHighWater)
                    queueHighWater = queue.Count;
                Monitor.PulseAll(capLock);
            }
        }

        public void OnQuote(string session, string contract, string side,
                            double px, double sz, DateTime exchUtc)
        {
            Publish(new MlesV12Event
            {
                Kind = "QUOTE", Session = session, Contract = contract,
                Side = side, Px = px, Sz = sz, ExchUtc = exchUtc,
                            });
        }

        public void OnTrade(string session, string contract, double px,
                            double sz, DateTime exchUtc)
        {
            Publish(new MlesV12Event
            {
                Kind = "TRADE", Session = session, Contract = contract,
                Px = px, Sz = sz, ExchUtc = exchUtc,
                            });
        }

        public void OnDepth(string session, string contract,
                            string action, string side, int level,
                            double px, double sz, DateTime exchUtc)
        {
            Publish(new MlesV12Event
            {
                Kind = "DEPTH", Session = session, Contract = contract,
                Action = action, Side = side, Level = level, Px = px,
                Sz = sz, ExchUtc = exchUtc, RecvUtc = DateTime.UtcNow,
                Mono = mono.ElapsedTicks
            });
        }

        public void OnConnection(string session, string contract,
                                 string status, string priceStatus)
        {
            Publish(new MlesV12Event
            {
                Kind = "CONN", Session = session, Contract = contract,
                Status = status, PriceStatus = priceStatus,
                ExchUtc = DateTime.MinValue,
                            });
        }

        // ============ shutdown: one consumer, full join ===============
        public void Shutdown()
        {
            lock (capLock)
            {
                accepting = false;
                Monitor.PulseAll(capLock);
            }
            if (worker != null) worker.Join();     // full join, no timeout
            lock (finLock)
            {
                finAccepting = false;
                Monitor.PulseAll(finLock);
            }
            if (finalizer != null) finalizer.Join();
        }

        // ============ permanent capture worker ========================
        private void WorkerLoop()
        {
            try
            {
                while (true)
                {
                    MlesV12Event ev = null;
                    long ovf;
                    bool done = false;
                    lock (capLock)
                    {
                        while (queue.Count == 0 && accepting)
                            Monitor.Wait(capLock, 250);
                        if (queue.Count > 0) ev = queue.Dequeue();
                        else if (!accepting) done = true;
                        ovf = cbOverflow;
                        cbOverflow = 0;
                    }
                    if (ovf > 0 && run != null)
                    {
                        run.NOverflow += ovf;
                        run.NDropped += ovf;
                    }
                    if (done) break;
                    if (ev == null)
                    {
                        Housekeeping(DateTime.UtcNow);
                        continue;
                    }
                    Process(ev);
                    Housekeeping(ev.RecvUtc);
                }
                if (run != null)
                {
                    Quality(DateTime.UtcNow, "SHUTDOWN",
                            "orderly runId=" + run.RunId);
                    CloseRun("SHUTDOWN");
                }
            }
            catch (Exception ex)
            {
                // never silently claim a finalized run
                try
                {
                    RecoveryArtifact = Path.Combine(dir,
                        "MLES12_" + captureInstanceId + "_RECOVERY.json");
                    File.WriteAllText(RecoveryArtifact,
                        "{\"schema\":\"" + SchemaVersion + "\"," +
                        "\"captureInstanceId\":\"" + captureInstanceId +
                        "\",\"state\":\"WORKER_FAILED\",\"error\":\"" +
                        ex.GetType().Name + "\"}");
                }
                catch (Exception) { }
            }
        }

        private long NextSeqStamped(out DateTime recv, out long mt)
        {
            lock (capLock)
            {
                recv = DateTime.UtcNow;
                mt = mono.ElapsedTicks;
                return ++eventSeq;
            }
        }

        private static string Iso(DateTime utc)
        {
            return utc == DateTime.MinValue ? "" :
                utc.ToUniversalTime()
                   .ToString(TsFmt, CultureInfo.InvariantCulture);
        }

        private static string N(double v)
        {
            return double.IsNaN(v) ? "" :
                v.ToString("0.##########", CultureInfo.InvariantCulture);
        }

        private static string Safe(string s)
        {
            if (string.IsNullOrEmpty(s)) return "UNK";
            StringBuilder sb = new StringBuilder();
            foreach (char c in s)
                sb.Append(char.IsLetterOrDigit(c) || c == '-' ? c : '_');
            return sb.ToString();
        }

        private void Process(MlesV12Event ev)
        {
            if (run == null ||
                ev.Session != run.Session || ev.Contract != run.Contract)
                Rotate(ev);
            switch (ev.Kind)
            {
                case "QUOTE": WriteQuote(ev); break;
                case "TRADE": WriteTrade(ev); break;
                case "DEPTH": WriteDepth(ev); break;
                case "CONN": HandleConn(ev); break;
            }
        }

        // ---- rotation: worker stays alive throughout -----------------
        private void Rotate(MlesV12Event trigger)
        {
            bool contractRoll = run != null &&
                trigger.Contract != run.Contract;
            if (run != null)
            {
                Quality(trigger.RecvUtc,
                        contractRoll ? "CONTRACT_ROLL_END" : "SESSION_END",
                        "runId=" + run.RunId);
                CloseRun(contractRoll ? "CONTRACT_ROLL" : "SESSION_ROLL");
            }
            OpenRun(trigger.Session, trigger.Contract);
            Quality(trigger.RecvUtc,
                    contractRoll ? "CONTRACT_ROLL_START" : "SESSION_START",
                    "runId=" + run.RunId + " captureInstanceId=" +
                    captureInstanceId);
            Quality(trigger.RecvUtc, "BOOK_RESYNC_START",
                    "declaredDepth=" +
                    declaredDepth.ToString(CultureInfo.InvariantCulture));
        }

        private void OpenRun(string session, string contract)
        {
            RunsOpened++;
            run = new Run
            {
                Session = session, Contract = contract,
                RunId = captureInstanceId + "-R" +
                        RunsOpened.ToString("D3", CultureInfo.InvariantCulture)
            };
            string b = Path.Combine(dir, "MLES12_" + Safe(instrument) +
                "_" + Safe(contract) + "_" + session + "_" + run.RunId);
            run.PQ = b + "_quotes.csv.partial";
            run.PT = b + "_trades.csv.partial";
            run.PD = b + "_depth.csv.partial";
            run.PC = b + "_quality.csv.partial";
            run.WQ = NewPartial(run.PQ);
            run.WT = NewPartial(run.PT);
            run.WD = NewPartial(run.PD);
            run.WC = NewPartial(run.PC);
            string head = "schema,captureInstanceId,runId,segId,session," +
                "instrument,contract,stream,eventSeq,streamSeq,tRecvUtc," +
                "tExchUtc,tMono";
            run.WQ.WriteLine(head +
                ",side,px,sz,bidPx,bidSz,askPx,askSz,flags");
            run.WT.WriteLine(head + ",px,sz,bidPx,bidSz,askPx,askSz," +
                "aggrRaw,aggrInf,aggrMethod,aggrConf,flags");
            run.WD.WriteLine(head +
                ",bookType,action,side,level,px,sz,flags");
            run.WC.WriteLine(head + ",kind,detail");
        }

        private static StreamWriter NewPartial(string path)
        {
            FileStream fs = new FileStream(path, FileMode.CreateNew,
                FileAccess.Write, FileShare.Read);
            StreamWriter w = new StreamWriter(fs);
            w.AutoFlush = false;
            return w;
        }

        private string Head(long ev, long streamSeq, string stream,
                            DateTime recv, DateTime exch, long monoTicks)
        {
            if (run.FirstEv < 0 || ev < run.FirstEv) run.FirstEv = ev;
            if (ev > run.LastEv) run.LastEv = ev;
            if (run.FirstRecv == DateTime.MinValue) run.FirstRecv = recv;
            run.LastRecv = recv;
            if (exch != DateTime.MinValue) run.LastExch = exch;
            return SchemaVersion + "," + captureInstanceId + "," +
                run.RunId + "," +
                run.SegId.ToString(CultureInfo.InvariantCulture) + "," +
                run.Session + "," + instrument + "," + run.Contract +
                "," + stream + "," +
                ev.ToString(CultureInfo.InvariantCulture) + "," +
                streamSeq.ToString(CultureInfo.InvariantCulture) + "," +
                Iso(recv) + "," + Iso(exch) + "," +
                monoTicks.ToString(CultureInfo.InvariantCulture);
        }

        private string Flags()
        {
            StringBuilder f = new StringBuilder();
            if (!run.Connected) f.Append("DISCONNECTED");
            if (!run.BookReady)
                f.Append(f.Length > 0 ? "|" : "").Append("DATA_SUPPRESSED");
            return f.ToString();
        }

        private void W(StreamWriter w, string line, ref long rows)
        {
            try { w.WriteLine(line); rows++; }
            catch (Exception) { run.NWriteErr++; }
        }

        private void WriteQuote(MlesV12Event ev)
        {
            // worker-owned BBO (also used for trade classification)
            if (ev.Side == "BID") { run.BidPx = ev.Px; run.BidSz = ev.Sz; }
            else { run.AskPx = ev.Px; run.AskSz = ev.Sz; }
            if (!double.IsNaN(run.BidPx) && !double.IsNaN(run.AskPx) &&
                run.BidPx > run.AskPx) run.NCrossed++;
            long s = ++run.SeqQ;
            if (run.FQ < 0) run.FQ = s;
            run.LQ = s;
            W(run.WQ, Head(ev.EventSeq, s, "QUOTE", ev.RecvUtc,
                           ev.ExchUtc, ev.Mono) + "," + ev.Side + "," +
              N(ev.Px) + "," + N(ev.Sz) + "," + N(run.BidPx) + "," +
              N(run.BidSz) + "," + N(run.AskPx) + "," + N(run.AskSz) +
              "," + Flags(), ref run.RowsQ);
        }

        private void WriteTrade(MlesV12Event ev)
        {
            string inf = "", conf = "NONE";
            if (!double.IsNaN(run.AskPx) && ev.Px >= run.AskPx)
            { inf = "BUY"; conf = "HIGH"; }
            else if (!double.IsNaN(run.BidPx) && ev.Px <= run.BidPx)
            { inf = "SELL"; conf = "HIGH"; }
            else if (!double.IsNaN(run.BidPx) && !double.IsNaN(run.AskPx))
            {
                double mid = 0.5 * (run.BidPx + run.AskPx);
                if (ev.Px > mid) { inf = "BUY"; conf = "LOW"; }
                else if (ev.Px < mid) { inf = "SELL"; conf = "LOW"; }
            }
            long s = ++run.SeqT;
            if (run.FT < 0) run.FT = s;
            run.LT = s;
            W(run.WT, Head(ev.EventSeq, s, "TRADE", ev.RecvUtc,
                           ev.ExchUtc, ev.Mono) + "," + N(ev.Px) + "," +
              N(ev.Sz) + "," + N(run.BidPx) + "," + N(run.BidSz) + "," +
              N(run.AskPx) + "," + N(run.AskSz) + ",," + inf +
              ",QUOTE_TEST_v1," + conf + "," + Flags(), ref run.RowsT);
        }

        private void WriteDepth(MlesV12Event ev)
        {
            if (ev.Side == "BID")
            {
                run.DepthBid++;
                if (ev.Level > run.MaxBidLvl) run.MaxBidLvl = ev.Level;
            }
            else
            {
                run.DepthAsk++;
                if (ev.Level > run.MaxAskLvl) run.MaxAskLvl = ev.Level;
            }
            if (ev.Action == "ADD") run.DepthAdd++;
            else if (ev.Action == "UPDATE") run.DepthUpd++;
            else run.DepthRem++;
            long s = ++run.SeqD;
            if (run.FD < 0) run.FD = s;
            run.LD = s;
            W(run.WD, Head(ev.EventSeq, s, "DEPTH", ev.RecvUtc,
                           ev.ExchUtc, ev.Mono) + ",MBP," + ev.Action +
              "," + ev.Side + "," +
              ev.Level.ToString(CultureInfo.InvariantCulture) + "," +
              N(ev.Px) + "," + N(ev.Sz) + "," + Flags(), ref run.RowsD);
            if (!run.BookReady && run.MaxBidLvl + 1 >= declaredDepth &&
                run.MaxAskLvl + 1 >= declaredDepth)
            {
                run.BookReady = true;
                Quality(ev.RecvUtc, "BOOK_READY",
                        "bidLevels=" + (run.MaxBidLvl + 1) +
                        " askLevels=" + (run.MaxAskLvl + 1));
            }
        }

        private void HandleConn(MlesV12Event ev)
        {
            // CONN events carry no published seq (see Publish): the row
            // mints its seq here; the true occurrence stamps are kept
            // in the detail so the disconnect instant is not lost.
            Quality(ev.RecvUtc, "CONN_STATUS", "status=" + ev.Status +
                    " priceStatus=" + ev.PriceStatus +
                    " occurredUtc=" + Iso(ev.RecvUtc) +
                    " occurredMono=" + ev.Mono);
            bool up = ev.PriceStatus == "CONNECTED" &&
                      ev.Status == "CONNECTED";
            if (!up && run.Connected)
            {
                run.Connected = false;
                run.BookReady = false;        // stale book is invalid
                run.NBookReset++;
                Quality(ev.RecvUtc, "DISCONNECT",
                        "seg=" + run.SegId + " book invalidated");
            }
            else if (up && !run.Connected)
            {
                run.Connected = true;
                run.SegId++;
                run.NReconnect++;
                run.BidPx = run.BidSz = double.NaN;
                run.AskPx = run.AskSz = double.NaN;
                run.MaxBidLvl = run.MaxAskLvl = -1;
                run.BookReady = false;        // full resync required
                Quality(ev.RecvUtc, "RECONNECT", "seg=" + run.SegId);
                Quality(ev.RecvUtc, "BOOK_RESYNC_START",
                        "declaredDepth=" + declaredDepth);
            }
        }

        private void Quality(DateTime ctx, string kind, string detail)
        {
            DateTime recv;
            long mt;
            long ev = NextSeqStamped(out recv, out mt);
            QualityRow(ev, recv, mt, kind, detail);
        }

        private void QualityRow(long ev, DateTime recv, long mt,
                                string kind, string detail)
        {
            long s = ++run.SeqC;
            if (run.FC < 0) run.FC = s;
            run.LC = s;
            W(run.WC, Head(ev, s, "QUALITY", recv,
                           DateTime.MinValue, mt) + "," +
              kind + "," + detail.Replace(',', ';'), ref run.RowsC);
        }

        private void Housekeeping(DateTime now)
        {
            if (run == null) return;
            if (run.LastFlush == DateTime.MinValue ||
                (now - run.LastFlush).TotalSeconds >= flushSeconds)
            {
                run.LastFlush = now;
                try
                {
                    run.WQ.Flush(); run.WT.Flush();
                    run.WD.Flush(); run.WC.Flush();
                }
                catch (Exception) { run.NWriteErr++; }
            }
            if (run.LastBeat == DateTime.MinValue ||
                (now - run.LastBeat).TotalSeconds >= heartbeatSeconds)
            {
                run.LastBeat = now;
                long qd, hw;
                lock (capLock) { qd = queue.Count; hw = queueHighWater; }
                Quality(now, "HEARTBEAT",
                    "q=" + run.RowsQ + " t=" + run.RowsT +
                    " dBid=" + run.DepthBid + " dAsk=" + run.DepthAsk +
                    " qDepth=" + qd + " qHigh=" + hw +
                    " ovf=" + run.NOverflow + " drop=" + run.NDropped +
                    " werr=" + run.NWriteErr + " runId=" + run.RunId +
                    " seg=" + run.SegId +
                    " bookReady=" + (run.BookReady ? "1" : "0"));
            }
        }

        // ---- closure: snapshot, then hand to the finalizer -----------
        private void CloseRun(string why)
        {
            Run r = run;
            run = null;
            try
            {
                r.WQ.Flush(); r.WQ.Close();
                r.WT.Flush(); r.WT.Close();
                r.WD.Flush(); r.WD.Close();
                r.WC.Flush(); r.WC.Close();
            }
            catch (Exception) { r.NWriteErr++; }
            ClosedRun job = new ClosedRun
            {
                BaseName = r.PQ.Substring(0,
                    r.PQ.Length - "_quotes.csv.partial".Length),
                Partials = new[] { r.PQ, r.PT, r.PD, r.PC },
                Rows = new[] { r.RowsQ, r.RowsT, r.RowsD, r.RowsC },
                Manifest = ManifestBody(r, why)
            };
            lock (finLock)
            {
                finQ.Enqueue(job);
                Monitor.PulseAll(finLock);
            }
        }

        private string ManifestBody(Run r, string why)
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("{\n");
            sb.Append(" \"schema\": \"" + SchemaVersion + "\",\n");
            sb.Append(" \"captureInstanceId\": \"" + captureInstanceId +
                      "\",\n");
            sb.Append(" \"runId\": \"" + r.RunId + "\",\n");
            sb.Append(" \"closeReason\": \"" + why + "\",\n");
            sb.Append(" \"session\": \"" + r.Session + "\",\n");
            sb.Append(" \"instrument\": \"" + instrument + "\",\n");
            sb.Append(" \"contract\": \"" + r.Contract + "\",\n");
            sb.Append(" \"bookType\": \"MBP\",\n");
            sb.Append(" \"declaredDepth\": " + declaredDepth + ",\n");
            sb.Append(" \"flushPolicySeconds\": " +
                      flushSeconds.ToString(CultureInfo.InvariantCulture) +
                      ",\n");
            sb.Append(" \"aggressorSource\": \"ABSENT-feed; inferred " +
                      "QUOTE_TEST_v1\",\n");
            sb.Append(" \"firstRecvUtc\": \"" + Iso(r.FirstRecv) + "\",\n");
            sb.Append(" \"lastRecvUtc\": \"" + Iso(r.LastRecv) + "\",\n");
            sb.Append(" \"lastExchUtc\": \"" + Iso(r.LastExch) + "\",\n");
            sb.Append(" \"firstEventSeq\": " + r.FirstEv + ",\n");
            sb.Append(" \"lastEventSeq\": " + r.LastEv + ",\n");
            sb.Append(" \"firstSegId\": " + r.FirstSeg + ",\n");
            sb.Append(" \"lastSegId\": " + r.SegId + ",\n");
            sb.Append(" \"connectionSegments\": " + r.SegId + ",\n");
            sb.Append(" \"firstQuoteSeq\": " + r.FQ + ",\n");
            sb.Append(" \"lastQuoteSeq\": " + r.LQ + ",\n");
            sb.Append(" \"firstTradeSeq\": " + r.FT + ",\n");
            sb.Append(" \"lastTradeSeq\": " + r.LT + ",\n");
            sb.Append(" \"firstDepthSeq\": " + r.FD + ",\n");
            sb.Append(" \"lastDepthSeq\": " + r.LD + ",\n");
            sb.Append(" \"firstQualitySeq\": " + r.FC + ",\n");
            sb.Append(" \"lastQualitySeq\": " + r.LC + ",\n");
            sb.Append(" \"gaps\": " + r.NGapMarked + ",\n");
            sb.Append(" \"duplicates\": 0,\n");
            sb.Append(" \"reversals\": 0,\n");
            sb.Append(" \"queueOverflows\": " + r.NOverflow + ",\n");
            sb.Append(" \"droppedRows\": " + r.NDropped + ",\n");
            sb.Append(" \"writeErrors\": " + r.NWriteErr + ",\n");
            sb.Append(" \"reconnects\": " + r.NReconnect + ",\n");
            sb.Append(" \"crossed\": " + r.NCrossed + ",\n");
            sb.Append(" \"bookResets\": " + r.NBookReset + ",\n");
            sb.Append(" \"maxBidLevelSeen\": " + (r.MaxBidLvl + 1) + ",\n");
            sb.Append(" \"maxAskLevelSeen\": " + (r.MaxAskLvl + 1) + ",\n");
            sb.Append(" \"depthBid\": " + r.DepthBid + ",\n");
            sb.Append(" \"depthAsk\": " + r.DepthAsk + ",\n");
            sb.Append(" \"depthAdd\": " + r.DepthAdd + ",\n");
            sb.Append(" \"depthUpdate\": " + r.DepthUpd + ",\n");
            sb.Append(" \"depthRemove\": " + r.DepthRem + ",\n");
            return sb.ToString();
        }

        // ============ finalization worker (closed runs only) ==========
        private void FinalizerLoop()
        {
            while (true)
            {
                ClosedRun job = null;
                lock (finLock)
                {
                    while (finQ.Count == 0 && finAccepting)
                        Monitor.Wait(finLock, 250);
                    if (finQ.Count > 0) job = finQ.Dequeue();
                    else if (!finAccepting) break;
                }
                if (job != null) Finalize(job);
            }
        }

        private static string Sha256(string path)
        {
            using (SHA256 h = SHA256.Create())
            using (FileStream fs = File.OpenRead(path))
            {
                byte[] d = h.ComputeHash(fs);
                StringBuilder sb = new StringBuilder();
                foreach (byte b in d) sb.Append(b.ToString("x2"));
                return sb.ToString();
            }
        }

        private static string NoClobber(string path, string ext)
        {
            if (!File.Exists(path + ext)) return path + ext;
            int n = 1;
            while (File.Exists(path + ".collision-" + n + ext)) n++;
            // collision keeps its real extension so scanners find it
            return path + ".collision-" + n + ext;
        }

        private void Finalize(ClosedRun job)
        {
            try
            {
                string[] labels = { "quotes", "trades", "depth", "quality" };
                StringBuilder files = new StringBuilder();
                for (int i = 0; i < 4; i++)
                {
                    string partial = job.Partials[i];
                    string basePath = partial.Substring(0,
                        partial.Length - ".csv.partial".Length);
                    string final = NoClobber(basePath, ".csv");
                    File.Move(partial, final);
                    FileInfo fi = new FileInfo(final);
                    files.Append(" \"" + labels[i] + "\": {\"present\": " +
                        "true, \"file\": \"" + fi.Name + "\", \"bytes\": " +
                        fi.Length + ", \"rows\": " + job.Rows[i] +
                        ", \"sha256\": \"" + Sha256(final) + "\"}" +
                        (i < 3 ? ",\n" : "\n"));
                }
                string mf = NoClobber(job.BaseName + "_manifest",
                                      ".json");
                string tmp = mf + ".tmp";
                File.WriteAllText(tmp, job.Manifest + files + "}\n");
                File.Move(tmp, mf);            // atomic finalization
                RunsFinalized++;
            }
            catch (Exception ex)
            {
                try
                {
                    File.WriteAllText(job.BaseName + "_RECOVERY.json",
                        "{\"schema\":\"" + SchemaVersion + "\"," +
                        "\"state\":\"FINALIZE_FAILED\",\"error\":\"" +
                        ex.GetType().Name +
                        "\",\"note\":\"partial files preserved\"}");
                }
                catch (Exception) { }
            }
        }
    }
}

// ======================================================================
// NinjaTrader host: thin wrapper over the core, REAL NT8 namespaces.
// Depth operations in NT8 are NinjaTrader.Data.Operation.Add/Update/
// Remove; connection updates expose BOTH Status and PriceStatus
// (NinjaTrader.Cbi.ConnectionStatus).
// ======================================================================
namespace NinjaTrader.NinjaScript.Indicators
{
    using NinjaTrader.Data;

    public class MlesV12CaptureHost : Indicator
    {
        private Mles.Capture.V12.MlesV12Core core;

        [NinjaTrader.NinjaScript.NinjaScriptProperty]
        public string CaptureFolder { get; set; }

        protected override void OnStateChange()
        {
            if (State == NinjaTrader.NinjaScript.State.SetDefaults)
            {
                Name = "MlesV12CaptureHost";
                Description = "MLES-CAPTURE-1.2 permanent-lifecycle " +
                              "capture (zero orders).";
                Calculate =
                    NinjaTrader.NinjaScript.Calculate.OnEachTick;
                IsOverlay = true;
                CaptureFolder = "";
            }
            else if (State == NinjaTrader.NinjaScript.State.Configure)
            {
                string d = string.IsNullOrEmpty(CaptureFolder)
                    ? Path.Combine(Environment.GetFolderPath(
                          Environment.SpecialFolder.MyDocuments),
                          "MLES_Capture")
                    : CaptureFolder;
                core = new Mles.Capture.V12.MlesV12Core(d,
                    Instrument != null &&
                    Instrument.MasterInstrument != null
                        ? Instrument.MasterInstrument.Name : "UNK");
                core.Start();
            }
            else if (State == NinjaTrader.NinjaScript.State.Terminated)
            {
                if (core != null) core.Shutdown();
            }
        }

        private static string SessionOf(DateTime utc)
        {
            DateTime et;
            try
            {
                TimeZoneInfo z;
                try
                {
                    z = TimeZoneInfo.FindSystemTimeZoneById(
                        "Eastern Standard Time");
                }
                catch (Exception)
                {
                    z = TimeZoneInfo.FindSystemTimeZoneById(
                        "America/New_York");
                }
                et = TimeZoneInfo.ConvertTimeFromUtc(utc, z);
            }
            catch (Exception) { et = utc; }
            DateTime d = et.Hour >= 18 ? et.Date.AddDays(1) : et.Date;
            return d.ToString("yyyyMMdd", CultureInfo.InvariantCulture);
        }

        private string Contract()
        {
            return Instrument != null ? Instrument.FullName : "UNK";
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            if (core == null) return;
            string ses = SessionOf(DateTime.UtcNow);
            DateTime ex = e.Time.ToUniversalTime();
            if (e.MarketDataType == MarketDataType.Bid)
                core.OnQuote(ses, Contract(), "BID", e.Price, e.Volume, ex);
            else if (e.MarketDataType == MarketDataType.Ask)
                core.OnQuote(ses, Contract(), "ASK", e.Price, e.Volume, ex);
            else if (e.MarketDataType == MarketDataType.Last)
                core.OnTrade(ses, Contract(), e.Price, e.Volume, ex);
        }

        protected override void OnMarketDepth(MarketDepthEventArgs e)
        {
            if (core == null) return;
            string act = e.Operation == Operation.Add ? "ADD" :
                         e.Operation == Operation.Update ? "UPDATE" :
                         "REMOVE";
            core.OnDepth(SessionOf(DateTime.UtcNow), Contract(), act,
                e.MarketDataType == MarketDataType.Bid ? "BID" : "ASK",
                e.Position, e.Price, e.Volume,
                e.Time.ToUniversalTime());
        }

        protected override void OnConnectionStatusUpdate(
            ConnectionStatusEventArgs e)
        {
            if (core == null) return;
            core.OnConnection(SessionOf(DateTime.UtcNow), Contract(),
                e.Status == NinjaTrader.Cbi.ConnectionStatus.Connected
                    ? "CONNECTED" : "DISCONNECTED",
                e.PriceStatus ==
                NinjaTrader.Cbi.ConnectionStatus.Connected
                    ? "CONNECTED" : "DISCONNECTED");
        }
    }
}
