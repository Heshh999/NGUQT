// ======================================================================
// MLES-V1 MESSAGE CAPTURE HOST  -  CAPTURE ONLY, ZERO ORDERS
// ======================================================================
// Hardened successor to MofadV1MicroCaptureHost.cs (audited, not
// duplicated - see MLES_V1_ANCESTRY_AND_PROTECTION_AUDIT.md section 4
// for the gap-by-gap findings that produced this file). The MOFAD
// recorder remains untouched as a committed research artifact; this
// file supersedes it for all MLES capture.
//
// STRUCTURAL SAFETY
//   NinjaTrader 8 INDICATOR. Indicators have no order API surface at
//   all: no account access, no EnterLong/EnterShort/SubmitOrderUnmanaged,
//   no ATM, no Set/Exit methods. The class cannot place, modify or
//   cancel an order even if instructed to. Verified by grep test in
//   analysis/mles/tests_mles.py.
//
// WHAT IT RECORDS  (one instance per instrument: NQ, ES, MNQ)
//   *_quotes.csv  every BBO change, BOTH sides carried on every row
//   *_trades.csv  every last trade + prevailing full BBO + inferred
//                 aggressor in SEPARATE, clearly-named fields
//   *_depth.csv   every depth update (operation, side, level, px, size)
//   *_quality.csv heartbeats, gaps, reconnects, book resets, locked/
//                 crossed, session state, roll changes
//   *_manifest.json  written ATOMICALLY at finalize: row counts, first/
//                 last timestamps, SHA-256 per file, quality counters
//
// CLOCKS (section 7): every row carries FOUR times -
//   tExch   exchange/source timestamp as delivered by NT8
//   tCb     platform callback timestamp (when NT8 handed us the event)
//   tRecv   UTC receive timestamp
//   tMono   local monotonic ticks (Stopwatch) - immune to wall-clock
//           adjustment, the only safe basis for intra-run deltas
//
// AGGRESSOR PROVENANCE (section 3): NinjaTrader's retail feeds supply
// last-trade and BBO, not an exchange aggressor flag. This recorder
// therefore writes aggrRaw = "" (absent) and records a SEPARATE
// quote-test classification in aggrInf/aggrMethod/aggrConf. Raw source
// fields are NEVER overwritten with derived values.
//
// DEPTH TYPE (section 6): NT8 retail depth is market-by-price. The
// recorder writes bookType=MBP and NEVER implies queue identity. A
// passive-fill claim from this data is not identifiable.
//
// THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. THIS FILE CANNOT TRADE.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.Globalization;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using NinjaTrader.Data;

namespace NinjaTrader.NinjaScript.Indicators
{
    public class MlesV1CaptureHost : Indicator
    {
        public const string SchemaVersion = "MLES-CAPTURE-1.0.0";

        private string dir, sessionId, sym, contract, runId;
        private StreamWriter wq, wt, wd, wc;
        private long seqQ, seqT, seqD;
        private double bidPx = double.NaN, bidSz = double.NaN;
        private double askPx = double.NaN, askSz = double.NaN;
        private DateTime lastMsgUtc = DateTime.MinValue;
        private DateTime lastBeatUtc = DateTime.MinValue;
        private bool connected = true, bookReset = false;
        private readonly Stopwatch mono = new Stopwatch();
        // quality counters, reported in the manifest (counts only - never outcomes)
        private long nGap, nReconnect, nCrossed, nReversal, nBookReset;
        private DateTime lastExch = DateTime.MinValue;
        private DateTime firstRecv = DateTime.MinValue, lastRecv = DateTime.MinValue;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MlesV1CaptureHost";
                Description = "MLES-V1 message capture (zero orders). Attach one per instrument.";
                Calculate = Calculate.OnEachTick;
                IsOverlay = true;
                CaptureFolder = "";
            }
            else if (State == State.Configure)
            {
                mono.Start();
                runId = DateTime.UtcNow.ToString("yyyyMMddHHmmss") + "-" +
                        Math.Abs(Guid.NewGuid().GetHashCode()).ToString("X6");
            }
            else if (State == State.Terminated) CloseSession();
        }

        [NinjaTrader.NinjaScript.NinjaScriptProperty]
        public string CaptureFolder { get; set; }

        // ---- session id: futures session rolls at 18:00 ET, not midnight ----
        private static string SessionOf(DateTime utc)
        {
            DateTime et;
            try
            {
                TimeZoneInfo z;
                try { z = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time"); }
                catch (Exception) { z = TimeZoneInfo.FindSystemTimeZoneById("America/New_York"); }
                et = TimeZoneInfo.ConvertTimeFromUtc(utc, z);
            }
            catch (Exception) { et = utc; }
            DateTime d = et.Hour >= 18 ? et.Date.AddDays(1) : et.Date;
            return d.ToString("yyyyMMdd");
        }

        private void Roll(DateTime utc)
        {
            string s = SessionOf(utc);
            if (s == sessionId && wq != null) return;
            CloseSession();
            sessionId = s;
            sym = Instrument != null && Instrument.MasterInstrument != null
                ? Instrument.MasterInstrument.Name : "UNK";
            contract = Instrument != null ? Instrument.FullName : "UNK";
            string root = string.IsNullOrEmpty(CaptureFolder)
                ? Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "mles_capture")
                : CaptureFolder;
            // never capture into a research/analysis folder (section 8)
            string low = root.Replace('\\', '/').ToLowerInvariant();
            if (low.Contains("/analysis") || low.Contains("/docs") || low.Contains("/scratchpad"))
                root = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "mles_capture");
            dir = root;
            Directory.CreateDirectory(dir);
            seqQ = seqT = seqD = 0;
            nGap = nReconnect = nCrossed = nReversal = nBookReset = 0;
            firstRecv = lastRecv = DateTime.MinValue;
            lastExch = DateTime.MinValue;
            const string common = "schema,runId,session,instrument,contract,stream,seq," +
                                  "tExch,tCb,tRecv,tMono,";
            wq = OpenFile("quotes", common + "side,px,sz,bidPx,bidSz,askPx,askSz,flags");
            wt = OpenFile("trades", common + "px,sz,bidPx,bidSz,askPx,askSz," +
                                "aggrRaw,aggrInf,aggrMethod,aggrConf,flags");
            wd = OpenFile("depth", common + "bookType,operation,side,level,px,sz,flags");
            wc = OpenFile("quality", "schema,runId,session,instrument,tRecv,tMono,kind,detail");
            Q(utc, "SESSION_START", "contract=" + contract + " schema=" + SchemaVersion);
        }

        private StreamWriter OpenFile(string kind, string header)
        {
            string p = Path.Combine(dir, string.Format("MLES_{0}_{1}_{2}.csv", sym, sessionId, kind));
            bool fresh = !File.Exists(p);
            var w = new StreamWriter(p, true, new UTF8Encoding(false));
            w.AutoFlush = false;
            if (fresh) w.WriteLine(header);
            w.Flush();
            return w;
        }

        private static string T(DateTime t)
        {
            return t.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ",
                                                CultureInfo.InvariantCulture);
        }
        private static string D(double v)
        {
            return double.IsNaN(v) ? "" : v.ToString("R", CultureInfo.InvariantCulture);
        }

        private string Prefix(string stream, long seq, DateTime tExch, DateTime tCb, DateTime tRecv)
        {
            return string.Join(",", new string[] { SchemaVersion, runId, sessionId, sym,
                contract, stream, seq.ToString(), T(tExch), T(tCb), T(tRecv),
                mono.ElapsedTicks.ToString() }) + ",";
        }

        private void Q(DateTime utc, string kind, string detail)
        {
            if (wc == null) return;
            wc.WriteLine(string.Join(",", new string[] { SchemaVersion, runId, sessionId, sym,
                T(utc), mono.ElapsedTicks.ToString(), kind, detail }));
            wc.Flush();
        }

        private string Flags()
        {
            var f = new List<string>();
            if (!connected) f.Add("DISCONNECTED");
            if (bookReset) f.Add("BOOKRESET");
            if (!double.IsNaN(bidPx) && !double.IsNaN(askPx) && bidPx >= askPx) f.Add("CROSSED");
            return string.Join("|", f.ToArray());
        }

        private void Beat(DateTime utc)
        {
            if ((utc - lastBeatUtc).TotalSeconds < 30) return;
            if (lastMsgUtc != DateTime.MinValue && (utc - lastMsgUtc).TotalSeconds > 10)
            { nGap++; Q(utc, "GAP", ((utc - lastMsgUtc).TotalSeconds).ToString("F1")); }
            Q(utc, "HEARTBEAT", "q=" + seqQ + " t=" + seqT + " d=" + seqD);
            lastBeatUtc = utc;
            if (wq != null) { wq.Flush(); wt.Flush(); wd.Flush(); }
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            DateTime recv = DateTime.UtcNow, cb = DateTime.UtcNow;
            Roll(recv);
            Beat(recv);
            lastMsgUtc = recv;
            if (firstRecv == DateTime.MinValue) firstRecv = recv;
            lastRecv = recv;
            if (lastExch != DateTime.MinValue && e.Time < lastExch)
            { nReversal++; Q(recv, "TS_REVERSAL", T(e.Time) + "<" + T(lastExch)); }
            lastExch = e.Time;

            if (e.MarketDataType == MarketDataType.Bid ||
                e.MarketDataType == MarketDataType.Ask)
            {
                bool isBid = e.MarketDataType == MarketDataType.Bid;
                if (isBid) { bidPx = e.Price; bidSz = e.Volume; }
                else { askPx = e.Price; askSz = e.Volume; }
                if (!double.IsNaN(bidPx) && !double.IsNaN(askPx) && bidPx >= askPx) nCrossed++;
                wq.WriteLine(Prefix("QUOTE", ++seqQ, e.Time, cb, recv) +
                    string.Join(",", new string[] { isBid ? "B" : "A", D(e.Price), D(e.Volume),
                    D(bidPx), D(bidSz), D(askPx), D(askSz), Flags() }));
            }
            else if (e.MarketDataType == MarketDataType.Last)
            {
                // quote-test classification, recorded as INFERRED and versioned.
                // Raw exchange aggressor flag is not supplied by this feed:
                // aggrRaw stays empty rather than being filled with a guess.
                string inf = "", meth = "", conf = "";
                if (!double.IsNaN(bidPx) && !double.IsNaN(askPx) && bidPx < askPx)
                {
                    meth = "QUOTE_TEST_v1";
                    if (e.Price >= askPx) { inf = "BUY"; conf = "HIGH"; }
                    else if (e.Price <= bidPx) { inf = "SELL"; conf = "HIGH"; }
                    else
                    {
                        double mid = 0.5 * (bidPx + askPx);
                        inf = e.Price > mid ? "BUY" : (e.Price < mid ? "SELL" : "UNKNOWN");
                        conf = e.Price == mid ? "NONE" : "LOW";
                    }
                }
                wt.WriteLine(Prefix("TRADE", ++seqT, e.Time, cb, recv) +
                    string.Join(",", new string[] { D(e.Price), D(e.Volume), D(bidPx), D(bidSz),
                    D(askPx), D(askSz), "", inf, meth, conf, Flags() }));
            }
        }

        protected override void OnMarketDepth(MarketDepthEventArgs e)
        {
            DateTime recv = DateTime.UtcNow, cb = DateTime.UtcNow;
            Roll(recv);
            lastMsgUtc = recv;
            lastRecv = recv;
            wd.WriteLine(Prefix("DEPTH", ++seqD, e.Time, cb, recv) +
                string.Join(",", new string[] { "MBP", e.Operation.ToString(),
                e.MarketDataType.ToString(), e.Position.ToString(), D(e.Price), D(e.Volume),
                Flags() }));
            if (bookReset) { bookReset = false; }
        }

        protected override void OnConnectionStatusUpdate(ConnectionStatusEventArgs e)
        {
            DateTime utc = DateTime.UtcNow;
            bool up = e.Status == ConnectionStatus.Connected;
            if (up != connected)
            {
                connected = up;
                if (up) { nReconnect++; nBookReset++; bookReset = true; Q(utc, "RECONNECT", e.Status.ToString()); }
                else Q(utc, "DISCONNECT", e.Status.ToString());
            }
        }

        protected override void OnBarUpdate() { }

        // ---- atomic close + manifest ----------------------------------
        private void CloseSession()
        {
            if (wq == null) return;
            DateTime utc = DateTime.UtcNow;
            Q(utc, "SESSION_END", "q=" + seqQ + " t=" + seqT + " d=" + seqD);
            foreach (var w in new StreamWriter[] { wq, wt, wd, wc })
                if (w != null) { w.Flush(); w.Close(); }
            var sb = new StringBuilder();
            sb.Append("{\n \"schema\": \"" + SchemaVersion + "\",\n \"runId\": \"" + runId + "\",\n");
            sb.Append(" \"session\": \"" + sessionId + "\",\n \"instrument\": \"" + sym + "\",\n");
            sb.Append(" \"contract\": \"" + contract + "\",\n \"bookType\": \"MBP\",\n");
            sb.Append(" \"aggressorSource\": \"INFERRED_QUOTE_TEST_v1 (no exchange flag supplied)\",\n");
            sb.Append(" \"firstRecvUtc\": \"" + (firstRecv == DateTime.MinValue ? "" : T(firstRecv)) + "\",\n");
            sb.Append(" \"lastRecvUtc\": \"" + (lastRecv == DateTime.MinValue ? "" : T(lastRecv)) + "\",\n");
            sb.Append(" \"rows\": {\"quotes\": " + seqQ + ", \"trades\": " + seqT + ", \"depth\": " + seqD + "},\n");
            sb.Append(" \"quality\": {\"gaps\": " + nGap + ", \"reconnects\": " + nReconnect +
                      ", \"crossed\": " + nCrossed + ", \"tsReversals\": " + nReversal +
                      ", \"bookResets\": " + nBookReset + "},\n");
            sb.Append(" \"files\": {\n");
            string[] kinds = { "quotes", "trades", "depth", "quality" };
            for (int i = 0; i < kinds.Length; i++)
            {
                string p = Path.Combine(dir, string.Format("MLES_{0}_{1}_{2}.csv", sym, sessionId, kinds[i]));
                string hash = "";
                if (File.Exists(p))
                {
                    using (var sha = SHA256.Create())
                    using (var fs = File.OpenRead(p))
                        hash = BitConverter.ToString(sha.ComputeHash(fs)).Replace("-", "").ToLowerInvariant();
                }
                sb.Append("  \"" + kinds[i] + "\": \"" + hash + "\"" + (i < kinds.Length - 1 ? "," : "") + "\n");
            }
            sb.Append(" }\n}\n");
            // atomic: write temp then move into place
            string final = Path.Combine(dir, string.Format("MLES_{0}_{1}_manifest.json", sym, sessionId));
            string tmp = final + ".tmp";
            File.WriteAllText(tmp, sb.ToString());
            if (File.Exists(final)) File.Delete(final);
            File.Move(tmp, final);
            wq = wt = wd = wc = null;
        }
    }
}
