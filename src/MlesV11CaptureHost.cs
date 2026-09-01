#region Using declarations
using System;
using System.Collections.Concurrent;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
#endregion

// ======================================================================
// MLES-CAPTURE-1.1  -  ADDITIVE SUCCESSOR RECORDER
// Predecessor src/MlesV1CaptureHost.cs (MLES-CAPTURE-1.0.0, Freeze A
// c40f39a) is IMMUTABLE and untouched; this is a separate host.
//
// Repairs over 1.0.0:
//   A. identity/storage - instrument, exact contract, session, runId and
//      connectionSegmentId in EVERY row and in the file path; a restart
//      always mints a new runId + its own manifest; .partial files are
//      atomically finalized; a finalized file is never appended to and a
//      manifest is never overwritten; old/new contract capture is
//      isolated by path.
//   B. causal ordering - ONE globally monotonic eventSeq assigned at
//      callback receipt via an atomic counter across quote/trade/depth/
//      connection/quality; per-stream sequences retained as secondary;
//      every disk write serialized through ONE ordered writer thread;
//      callback receive UTC + exchange UTC (ISO-8601 round-trip) on
//      every row; queue overflow, dropped rows and write failures
//      counted.
//   C. manifests - filenames, SHA-256, byte sizes, row counts, first/
//      last global and per-stream sequences, first/last timestamps,
//      exact contract, runId, connection segments, gaps, duplicates,
//      reversals, drops, write errors, depth side counts and depth
//      action counts.
//
// READ-ONLY: this is an Indicator. It contains no account access and no
// order-submission API of any kind - no EnterLong/EnterShort/
// SubmitOrderUnmanaged/ChangeOrder/CancelOrder/Account. Recording is not
// permission to trade. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
// ======================================================================

namespace NinjaTrader.NinjaScript.Indicators
{
    public class MlesV11CaptureHost : Indicator
    {
        public const string SchemaVersion = "MLES-CAPTURE-1.1";
        private const int MaxQueue = 250000;
        private const string TsFmt = "yyyy-MM-ddTHH:mm:ss.fffffffZ";

        // ---- identity ----------------------------------------------
        private string dir, sessionId, sym, contract, runId;
        private long segId;                       // connection segment
        private readonly Stopwatch mono = new Stopwatch();

        // ---- ordered writer ----------------------------------------
        private readonly ConcurrentQueue<string[]> q =
            new ConcurrentQueue<string[]>();
        private Thread writer;
        private volatile bool running;
        private long qDepth;
        private StreamWriter wq, wt, wd, wc;
        private string pq, pt, pd, pc;            // .partial paths

        // ---- sequences ---------------------------------------------
        private long eventSeq;                    // GLOBAL, atomic
        private long seqQuote, seqTrade, seqDepth, seqQual;
        private long firstEventSeq = -1, lastEventSeq = -1;
        private long firstQ = -1, lastQ = -1, firstT = -1, lastT = -1;
        private long firstD = -1, lastD = -1, firstC = -1, lastC = -1;
        private long rowsQ, rowsT, rowsD, rowsC;

        // ---- quality counters --------------------------------------
        private long nGap, nDup, nReversal, nOverflow, nDropped;
        private long nWriteErr, nReconnect, nCrossed, nBookReset;
        private long nDepthBid, nDepthAsk;
        private long nDepthAdd, nDepthUpdate, nDepthRemove;
        private long lastSeenEventSeq;

        // ---- book / state ------------------------------------------
        private double bidPx = double.NaN, bidSz = double.NaN;
        private double askPx = double.NaN, askSz = double.NaN;
        private DateTime firstRecv = DateTime.MinValue;
        private DateTime lastRecv = DateTime.MinValue;
        private DateTime lastExch = DateTime.MinValue;
        private DateTime lastBeatUtc = DateTime.MinValue;
        private bool connected = true;

        [NinjaTrader.NinjaScript.NinjaScriptProperty]
        public string CaptureFolder { get; set; }

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MlesV11CaptureHost";
                Description = "MLES-CAPTURE-1.1 message capture " +
                              "(zero orders). One instance per instrument.";
                Calculate = Calculate.OnEachTick;
                IsOverlay = true;
                CaptureFolder = "";
            }
            else if (State == State.Configure)
            {
                mono.Start();
                // A: every (re)start mints a NEW runId, so a restarted
                // run can never share a path with a finalized file.
                runId = DateTime.UtcNow.ToString("yyyyMMddHHmmssfff",
                            CultureInfo.InvariantCulture) + "-" +
                        Math.Abs(Guid.NewGuid().GetHashCode())
                            .ToString("X6", CultureInfo.InvariantCulture);
                segId = 1;
                StartWriter();
            }
            else if (State == State.Terminated)
            {
                CloseSession();
            }
        }

        // ================= ordered writer (B) ========================
        private void StartWriter()
        {
            running = true;
            writer = new Thread(WriterLoop);
            writer.IsBackground = true;
            writer.Start();
        }

        private void WriterLoop()
        {
            while (running || Interlocked.Read(ref qDepth) > 0)
            {
                string[] row;
                if (q.TryDequeue(out row))
                {
                    Interlocked.Decrement(ref qDepth);
                    WriteRow(row);
                }
                else
                {
                    Thread.Sleep(2);
                }
            }
        }

        // row[0] = stream tag; the remainder is the CSV payload.
        private void WriteRow(string[] row)
        {
            try
            {
                StreamWriter w = null;
                if (row[0] == "QUOTE") w = wq;
                else if (row[0] == "TRADE") w = wt;
                else if (row[0] == "DEPTH") w = wd;
                else w = wc;
                if (w == null)
                {
                    Interlocked.Increment(ref nDropped);
                    return;
                }
                StringBuilder sb = new StringBuilder();
                for (int i = 1; i < row.Length; i++)
                {
                    if (i > 1) sb.Append(',');
                    sb.Append(row[i]);
                }
                w.WriteLine(sb.ToString());
            }
            catch (Exception)
            {
                Interlocked.Increment(ref nWriteErr);
            }
        }

        private void Enqueue(string[] row)
        {
            if (Interlocked.Read(ref qDepth) >= MaxQueue)
            {
                Interlocked.Increment(ref nOverflow);
                Interlocked.Increment(ref nDropped);
                return;
            }
            q.Enqueue(row);
            Interlocked.Increment(ref qDepth);
        }

        private static string Iso(DateTime utc)
        {
            return utc.ToUniversalTime()
                      .ToString(TsFmt, CultureInfo.InvariantCulture);
        }

        private static string N(double v)
        {
            return double.IsNaN(v)
                ? ""
                : v.ToString("0.##########", CultureInfo.InvariantCulture);
        }

        // Common identity prefix carried by EVERY row (A + B).
        private string[] Head(string stream, long streamSeq,
                              DateTime recvUtc, DateTime exchUtc)
        {
            long ev = Interlocked.Increment(ref eventSeq);
            if (Interlocked.Read(ref firstEventSeq) < 0)
                Interlocked.Exchange(ref firstEventSeq, ev);
            Interlocked.Exchange(ref lastEventSeq, ev);
            long prev = Interlocked.Exchange(ref lastSeenEventSeq, ev);
            if (prev > 0)
            {
                if (ev == prev) Interlocked.Increment(ref nDup);
                else if (ev < prev) Interlocked.Increment(ref nReversal);
                else if (ev > prev + 1) Interlocked.Increment(ref nGap);
            }
            if (firstRecv == DateTime.MinValue) firstRecv = recvUtc;
            lastRecv = recvUtc;
            if (exchUtc != DateTime.MinValue)
            {
                if (lastExch != DateTime.MinValue && exchUtc < lastExch)
                    Interlocked.Increment(ref nReversal);
                lastExch = exchUtc;
            }
            return new string[]
            {
                stream,
                SchemaVersion, runId,
                segId.ToString(CultureInfo.InvariantCulture),
                sessionId == null ? "" : sessionId,
                sym == null ? "" : sym,
                contract == null ? "" : contract,
                stream,
                ev.ToString(CultureInfo.InvariantCulture),
                streamSeq.ToString(CultureInfo.InvariantCulture),
                Iso(recvUtc),
                exchUtc == DateTime.MinValue ? "" : Iso(exchUtc),
                mono.ElapsedTicks.ToString(CultureInfo.InvariantCulture)
            };
        }

        private static string[] Concat(string[] a, string[] b)
        {
            string[] r = new string[a.Length + b.Length];
            Array.Copy(a, 0, r, 0, a.Length);
            Array.Copy(b, 0, r, a.Length, b.Length);
            return r;
        }

        // ================= session lifecycle (A) =====================
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

        private static string Safe(string s)
        {
            if (string.IsNullOrEmpty(s)) return "UNK";
            StringBuilder sb = new StringBuilder();
            foreach (char c in s)
                sb.Append(char.IsLetterOrDigit(c) || c == '-' ? c : '_');
            return sb.ToString();
        }

        // A: never open a finalized file for append; never reuse a name.
        private static StreamWriter NewPartial(string path)
        {
            FileStream fs = new FileStream(path, FileMode.CreateNew,
                                           FileAccess.Write, FileShare.Read);
            StreamWriter w = new StreamWriter(fs);
            w.AutoFlush = false;
            return w;
        }

        private string Base(string stream)
        {
            // instrument + EXACT contract + session + runId in the path,
            // so old-contract and new-contract capture are isolated and
            // a restart can never target a previous file.
            return Path.Combine(dir, "MLES11_" + Safe(sym) + "_" +
                Safe(contract) + "_" + sessionId + "_" + runId + "_" +
                stream);
        }

        private void Roll(DateTime utc)
        {
            string s = SessionOf(utc);
            string c = Instrument != null ? Instrument.FullName : "UNK";
            if (s == sessionId && c == contract && wq != null) return;
            CloseSession();
            sessionId = s;
            contract = c;
            sym = Instrument != null && Instrument.MasterInstrument != null
                ? Instrument.MasterInstrument.Name : "UNK";
            dir = string.IsNullOrEmpty(CaptureFolder)
                ? Path.Combine(Environment.GetFolderPath(
                      Environment.SpecialFolder.MyDocuments),
                      "MLES_Capture")
                : CaptureFolder;
            string low = dir.ToLowerInvariant();
            if (low.Contains("analysis") || low.Contains("docs") ||
                low.Contains("scratchpad"))
                throw new InvalidOperationException(
                    "refusing to write capture into a research folder");
            Directory.CreateDirectory(dir);
            pq = Base("quotes") + ".csv.partial";
            pt = Base("trades") + ".csv.partial";
            pd = Base("depth") + ".csv.partial";
            pc = Base("quality") + ".csv.partial";
            wq = NewPartial(pq);
            wt = NewPartial(pt);
            wd = NewPartial(pd);
            wc = NewPartial(pc);
            string head = "schema,runId,segId,session,instrument," +
                          "contract,stream,eventSeq,streamSeq,tRecvUtc," +
                          "tExchUtc,tMono";
            wq.WriteLine(head + ",side,px,sz,bidPx,bidSz,askPx,askSz,flags");
            wt.WriteLine(head + ",px,sz,bidPx,bidSz,askPx,askSz," +
                         "aggrRaw,aggrInf,aggrMethod,aggrConf,flags");
            wd.WriteLine(head + ",bookType,action,side,level,px,sz,flags");
            wc.WriteLine(head + ",kind,detail");
            Quality(utc, "SESSION_START", "runId=" + runId +
                    " seg=" + segId.ToString(CultureInfo.InvariantCulture));
        }

        private void Quality(DateTime utc, string kind, string detail)
        {
            long s = Interlocked.Increment(ref seqQual);
            if (firstC < 0) firstC = s;
            lastC = s;
            Interlocked.Increment(ref rowsC);
            Enqueue(Concat(Head("QUALITY", s, utc, DateTime.MinValue),
                           new string[] { kind, detail }));
        }

        // ================= market callbacks ==========================
        protected override void OnMarketData(MarketDataEventArgs e)
        {
            DateTime utc = DateTime.UtcNow;
            Roll(utc);
            DateTime ex = e.Time.ToUniversalTime();
            if (e.MarketDataType == MarketDataType.Bid)
            {
                bidPx = e.Price; bidSz = e.Volume;
                QuoteRow(utc, ex, "BID", e.Price, e.Volume);
            }
            else if (e.MarketDataType == MarketDataType.Ask)
            {
                askPx = e.Price; askSz = e.Volume;
                QuoteRow(utc, ex, "ASK", e.Price, e.Volume);
            }
            else if (e.MarketDataType == MarketDataType.Last)
            {
                TradeRow(utc, ex, e.Price, e.Volume);
            }
            Heartbeat(utc);
        }

        private void QuoteRow(DateTime utc, DateTime ex, string side,
                              double px, double sz)
        {
            long s = Interlocked.Increment(ref seqQuote);
            if (firstQ < 0) firstQ = s;
            lastQ = s;
            Interlocked.Increment(ref rowsQ);
            string flags = "";
            if (!connected) flags += "DISCONNECTED";
            if (!double.IsNaN(bidPx) && !double.IsNaN(askPx) &&
                bidPx > askPx)
            {
                Interlocked.Increment(ref nCrossed);
                flags += (flags.Length > 0 ? "|" : "") + "CROSSED";
            }
            Enqueue(Concat(Head("QUOTE", s, utc, ex), new string[]
            {
                side, N(px), N(sz), N(bidPx), N(bidSz), N(askPx),
                N(askSz), flags
            }));
        }

        private void TradeRow(DateTime utc, DateTime ex, double px,
                              double sz)
        {
            long s = Interlocked.Increment(ref seqTrade);
            if (firstT < 0) firstT = s;
            lastT = s;
            Interlocked.Increment(ref rowsT);
            // aggrRaw stays EMPTY: this feed supplies no exchange flag.
            string inf = "", conf = "NONE";
            if (!double.IsNaN(askPx) && px >= askPx) { inf = "BUY"; conf = "HIGH"; }
            else if (!double.IsNaN(bidPx) && px <= bidPx) { inf = "SELL"; conf = "HIGH"; }
            else if (!double.IsNaN(bidPx) && !double.IsNaN(askPx))
            {
                double mid = 0.5 * (bidPx + askPx);
                if (px > mid) { inf = "BUY"; conf = "LOW"; }
                else if (px < mid) { inf = "SELL"; conf = "LOW"; }
            }
            Enqueue(Concat(Head("TRADE", s, utc, ex), new string[]
            {
                N(px), N(sz), N(bidPx), N(bidSz), N(askPx), N(askSz),
                "", inf, "QUOTE_TEST_v1", conf,
                connected ? "" : "DISCONNECTED"
            }));
        }

        protected override void OnMarketDepth(MarketDepthEventArgs e)
        {
            DateTime utc = DateTime.UtcNow;
            Roll(utc);
            DateTime ex = e.Time.ToUniversalTime();
            string side = e.MarketDataType == MarketDataType.Bid
                ? "BID" : "ASK";
            if (side == "BID") Interlocked.Increment(ref nDepthBid);
            else Interlocked.Increment(ref nDepthAsk);
            string action;
            if (e.Operation == Operation.Insert)
            {
                action = "ADD";
                Interlocked.Increment(ref nDepthAdd);
            }
            else if (e.Operation == Operation.Update)
            {
                action = "UPDATE";
                Interlocked.Increment(ref nDepthUpdate);
            }
            else
            {
                action = "REMOVE";
                Interlocked.Increment(ref nDepthRemove);
            }
            long s = Interlocked.Increment(ref seqDepth);
            if (firstD < 0) firstD = s;
            lastD = s;
            Interlocked.Increment(ref rowsD);
            Enqueue(Concat(Head("DEPTH", s, utc, ex), new string[]
            {
                "MBP", action, side,
                e.Position.ToString(CultureInfo.InvariantCulture),
                N(e.Price), N(e.Volume),
                connected ? "" : "DISCONNECTED"
            }));
            Heartbeat(utc);
        }

        protected override void OnConnectionStatusUpdate(
            ConnectionStatusEventArgs e)
        {
            DateTime utc = DateTime.UtcNow;
            if (e.Status == ConnectionStatus.Connected)
            {
                if (!connected)
                {
                    // A/B: a reconnect opens a NEW connection segment;
                    // the segment id is stamped on every later row.
                    Interlocked.Increment(ref segId);
                    Interlocked.Increment(ref nReconnect);
                    Quality(utc, "RECONNECT", "seg=" +
                        segId.ToString(CultureInfo.InvariantCulture));
                }
                connected = true;
            }
            else if (e.Status == ConnectionStatus.Disconnected)
            {
                connected = false;
                Quality(utc, "DISCONNECT", "seg=" +
                    segId.ToString(CultureInfo.InvariantCulture));
            }
        }

        private void Heartbeat(DateTime utc)
        {
            if ((utc - lastBeatUtc).TotalSeconds < 30) return;
            lastBeatUtc = utc;
            Quality(utc, "HEARTBEAT",
                "ev=" + Interlocked.Read(ref eventSeq)
                    .ToString(CultureInfo.InvariantCulture) +
                " q=" + Interlocked.Read(ref rowsQ)
                    .ToString(CultureInfo.InvariantCulture) +
                " t=" + Interlocked.Read(ref rowsT)
                    .ToString(CultureInfo.InvariantCulture) +
                " d=" + Interlocked.Read(ref rowsD)
                    .ToString(CultureInfo.InvariantCulture) +
                " dBid=" + Interlocked.Read(ref nDepthBid)
                    .ToString(CultureInfo.InvariantCulture) +
                " dAsk=" + Interlocked.Read(ref nDepthAsk)
                    .ToString(CultureInfo.InvariantCulture) +
                " ovf=" + Interlocked.Read(ref nOverflow)
                    .ToString(CultureInfo.InvariantCulture) +
                " drop=" + Interlocked.Read(ref nDropped)
                    .ToString(CultureInfo.InvariantCulture) +
                " werr=" + Interlocked.Read(ref nWriteErr)
                    .ToString(CultureInfo.InvariantCulture));
        }

        // ================= finalization + manifest (A + C) ===========
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

        // A: atomic finalization; a pre-existing final name is NEVER
        // overwritten - the collision is recorded under a new name.
        private static string Finalize(string partial)
        {
            if (partial == null || !File.Exists(partial)) return null;
            string final = partial.Substring(0,
                partial.Length - ".partial".Length);
            if (File.Exists(final))
            {
                int n = 1;
                while (File.Exists(final + ".collision-" + n)) n++;
                final = final + ".collision-" + n;
            }
            File.Move(partial, final);
            return final;
        }

        private static void J(StringBuilder sb, string k, string v,
                              bool last)
        {
            sb.Append(" \"").Append(k).Append("\": \"")
              .Append(v == null ? "" : v.Replace("\\", "/")
                                         .Replace("\"", "'"))
              .Append(last ? "\"\n" : "\",\n");
        }

        private static void JN(StringBuilder sb, string k, long v,
                               bool last)
        {
            sb.Append(" \"").Append(k).Append("\": ")
              .Append(v.ToString(CultureInfo.InvariantCulture))
              .Append(last ? "\n" : ",\n");
        }

        private static void JFile(StringBuilder sb, string label,
                                  string path, long rows, bool last)
        {
            sb.Append(" \"").Append(label).Append("\": {");
            if (path == null || !File.Exists(path))
            {
                sb.Append("\"present\": false}").Append(last ? "\n" : ",\n");
                return;
            }
            FileInfo fi = new FileInfo(path);
            sb.Append("\"present\": true, \"file\": \"")
              .Append(fi.Name).Append("\", \"bytes\": ")
              .Append(fi.Length.ToString(CultureInfo.InvariantCulture))
              .Append(", \"rows\": ")
              .Append(rows.ToString(CultureInfo.InvariantCulture))
              .Append(", \"sha256\": \"").Append(Sha256(path))
              .Append("\"}").Append(last ? "\n" : ",\n");
        }

        private void CloseSession()
        {
            if (wq == null && wt == null && wd == null && wc == null)
                return;
            DateTime utc = DateTime.UtcNow;
            Quality(utc, "SESSION_END", "runId=" + runId);
            running = false;
            try { if (writer != null) writer.Join(5000); }
            catch (Exception) { }
            // drain anything the loop did not take before it exited
            string[] row;
            while (q.TryDequeue(out row))
            {
                Interlocked.Decrement(ref qDepth);
                WriteRow(row);
            }
            try { if (wq != null) { wq.Flush(); wq.Close(); } } catch (Exception) { }
            try { if (wt != null) { wt.Flush(); wt.Close(); } } catch (Exception) { }
            try { if (wd != null) { wd.Flush(); wd.Close(); } } catch (Exception) { }
            try { if (wc != null) { wc.Flush(); wc.Close(); } } catch (Exception) { }
            wq = null; wt = null; wd = null; wc = null;
            string fq = Finalize(pq), ft = Finalize(pt);
            string fd = Finalize(pd), fc = Finalize(pc);

            StringBuilder sb = new StringBuilder();
            sb.Append("{\n");
            J(sb, "schema", SchemaVersion, false);
            J(sb, "runId", runId, false);
            JN(sb, "connectionSegments", Interlocked.Read(ref segId), false);
            J(sb, "session", sessionId, false);
            J(sb, "instrument", sym, false);
            J(sb, "contract", contract, false);
            J(sb, "bookType", "MBP", false);
            J(sb, "aggressorSource",
              "ABSENT-feed; inferred QUOTE_TEST_v1", false);
            J(sb, "firstRecvUtc", firstRecv == DateTime.MinValue
                ? "" : Iso(firstRecv), false);
            J(sb, "lastRecvUtc", lastRecv == DateTime.MinValue
                ? "" : Iso(lastRecv), false);
            J(sb, "lastExchUtc", lastExch == DateTime.MinValue
                ? "" : Iso(lastExch), false);
            JN(sb, "firstEventSeq", Interlocked.Read(ref firstEventSeq), false);
            JN(sb, "lastEventSeq", Interlocked.Read(ref lastEventSeq), false);
            JN(sb, "firstQuoteSeq", firstQ, false);
            JN(sb, "lastQuoteSeq", lastQ, false);
            JN(sb, "firstTradeSeq", firstT, false);
            JN(sb, "lastTradeSeq", lastT, false);
            JN(sb, "firstDepthSeq", firstD, false);
            JN(sb, "lastDepthSeq", lastD, false);
            JN(sb, "firstQualitySeq", firstC, false);
            JN(sb, "lastQualitySeq", lastC, false);
            JN(sb, "gaps", Interlocked.Read(ref nGap), false);
            JN(sb, "duplicates", Interlocked.Read(ref nDup), false);
            JN(sb, "reversals", Interlocked.Read(ref nReversal), false);
            JN(sb, "queueOverflows", Interlocked.Read(ref nOverflow), false);
            JN(sb, "droppedRows", Interlocked.Read(ref nDropped), false);
            JN(sb, "writeErrors", Interlocked.Read(ref nWriteErr), false);
            JN(sb, "reconnects", Interlocked.Read(ref nReconnect), false);
            JN(sb, "crossed", Interlocked.Read(ref nCrossed), false);
            JN(sb, "bookResets", Interlocked.Read(ref nBookReset), false);
            JN(sb, "depthBid", Interlocked.Read(ref nDepthBid), false);
            JN(sb, "depthAsk", Interlocked.Read(ref nDepthAsk), false);
            JN(sb, "depthAdd", Interlocked.Read(ref nDepthAdd), false);
            JN(sb, "depthUpdate", Interlocked.Read(ref nDepthUpdate), false);
            JN(sb, "depthRemove", Interlocked.Read(ref nDepthRemove), false);
            JFile(sb, "quotes", fq, Interlocked.Read(ref rowsQ), false);
            JFile(sb, "trades", ft, Interlocked.Read(ref rowsT), false);
            JFile(sb, "depth", fd, Interlocked.Read(ref rowsD), false);
            JFile(sb, "quality", fc, Interlocked.Read(ref rowsC), true);
            sb.Append("}\n");

            try
            {
                string mf = Path.Combine(dir, "MLES11_" + Safe(sym) + "_" +
                    Safe(contract) + "_" + sessionId + "_" + runId +
                    "_manifest.json");
                if (File.Exists(mf))
                {
                    int n = 1;
                    while (File.Exists(mf + ".collision-" + n)) n++;
                    mf = mf + ".collision-" + n;   // never overwrite
                }
                string tmp = mf + ".tmp";
                File.WriteAllText(tmp, sb.ToString());
                File.Move(tmp, mf);                // atomic finalization
            }
            catch (Exception)
            {
                Interlocked.Increment(ref nWriteErr);
            }
        }
    }
}
