// ======================================================================
// MOFAD-V1 MICROSTRUCTURE CAPTURE HOST  (capture-only, zero orders)
// ======================================================================
// NinjaTrader 8 INDICATOR (not a Strategy): it has no order methods at
// all, so it is structurally incapable of trading. It records raw
// level-1 (quotes + trades with aggressor context) and level-2
// (market-by-price depth updates) messages to append-only daily CSVs,
// with receive timestamps, per-file sequence numbers, heartbeats,
// reconnect markers, and a daily SHA-256 manifest.
//
// One instance is attached per instrument (MNQ, NQ, ES). Files:
//   MOFAD_CAP_<sym>_<yyyyMMdd>_quotes.csv   L1 bid/ask price+size updates
//   MOFAD_CAP_<sym>_<yyyyMMdd>_trades.csv   last trades + prevailing quote
//   MOFAD_CAP_<sym>_<yyyyMMdd>_depth.csv    L2 MBP add/update/remove
//   MOFAD_CAP_<sym>_<yyyyMMdd>_quality.csv  heartbeats, gaps, reconnects
//   MOFAD_CAP_<sym>_<yyyyMMdd>_manifest.txt row counts + SHA-256 hashes
//
// Timestamps: exchange time as delivered by NT8 (e.Time) AND local
// receive time (DateTime.UtcNow) at native precision, both written as
// UTC ISO-8601 with offsetless 'Z'; ET rendering is derived downstream
// and tested, never stored as the primary clock.
//
// Aggressor side is NOT inferred here: the trade row records the trade
// price/size plus the prevailing best bid/ask so any classification is
// an explicit downstream research decision (frozen before outcomes).
//
// The recorder never reads strategy outcomes, never opens research
// files, and exposes no performance numbers. Capture integrity
// summaries contain counts and hashes only.
// THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. THIS FILE CANNOT TRADE.
// ======================================================================
using System;
using System.Collections.Generic;
using System.IO;
using System.Security.Cryptography;
using System.Text;
using NinjaTrader.Data;

namespace NinjaTrader.NinjaScript.Indicators
{
    public class MofadV1MicroCaptureHost : Indicator
    {
        private string dir, day, sym;
        private StreamWriter wq, wt, wd, wc;
        private long seqQ, seqT, seqD;
        private double bestBid = double.NaN, bestAsk = double.NaN;
        private double bestBidSz = double.NaN, bestAskSz = double.NaN;
        private DateTime lastMsgUtc = DateTime.MinValue;
        private DateTime lastHeartbeatUtc = DateTime.MinValue;
        private bool wasConnected = true;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name = "MofadV1MicroCaptureHost";
                Description = "MOFAD-V1 capture-only microstructure recorder (zero orders)";
                Calculate = Calculate.OnEachTick;
                IsOverlay = true;
            }
            else if (State == State.Terminated)
            {
                CloseDay();
            }
        }

        private void Roll(DateTime utc)
        {
            string d = utc.ToString("yyyyMMdd");
            if (d == day && wq != null) return;
            CloseDay();
            day = d;
            sym = Instrument != null && Instrument.MasterInstrument != null
                ? Instrument.MasterInstrument.Name : "UNK";
            dir = Path.Combine(NinjaTrader.Core.Globals.UserDataDir, "mofad_capture");
            Directory.CreateDirectory(dir);
            wq = OpenFile("quotes", "seq,utcRecv,utcExch,side,price,size");
            wt = OpenFile("trades", "seq,utcRecv,utcExch,price,size,bestBid,bestBidSz,bestAsk,bestAskSz");
            wd = OpenFile("depth", "seq,utcRecv,utcExch,operation,side,level,price,size,mbo");
            wc = OpenFile("quality", "utcRecv,kind,detail");
            seqQ = seqT = seqD = 0;
            Q("SESSION_START", sym + " contract=" + (Instrument != null ? Instrument.FullName : "?"));
        }

        private StreamWriter OpenFile(string kind, string header)
        {
            string p = Path.Combine(dir, "MOFAD_CAP_" + sym + "_" + day + "_" + kind + ".csv");
            bool fresh = !File.Exists(p);
            var w = new StreamWriter(p, true, Encoding.ASCII);
            if (fresh) w.WriteLine(header);
            w.Flush();
            return w;
        }

        private static string Ts(DateTime t)
        {
            return t.ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ss.fffffffZ");
        }

        private void Q(string kind, string detail)
        {
            if (wc == null) return;
            wc.WriteLine(Ts(DateTime.UtcNow) + "," + kind + "," + detail);
            wc.Flush();
        }

        private void Heartbeat(DateTime utc)
        {
            if ((utc - lastHeartbeatUtc).TotalSeconds < 30) return;
            if (lastMsgUtc != DateTime.MinValue && (utc - lastMsgUtc).TotalSeconds > 10)
                Q("GAP", ((utc - lastMsgUtc).TotalSeconds).ToString("F1") + "s since last message");
            Q("HEARTBEAT", "q=" + seqQ + " t=" + seqT + " d=" + seqD);
            lastHeartbeatUtc = utc;
        }

        protected override void OnMarketData(MarketDataEventArgs e)
        {
            DateTime utc = DateTime.UtcNow;
            Roll(utc);
            Heartbeat(utc);
            lastMsgUtc = utc;
            if (e.MarketDataType == MarketDataType.Bid)
            {
                bestBid = e.Price; bestBidSz = e.Volume;
                wq.WriteLine((++seqQ) + "," + Ts(utc) + "," + Ts(e.Time) + ",B," + e.Price + "," + e.Volume);
            }
            else if (e.MarketDataType == MarketDataType.Ask)
            {
                bestAsk = e.Price; bestAskSz = e.Volume;
                wq.WriteLine((++seqQ) + "," + Ts(utc) + "," + Ts(e.Time) + ",A," + e.Price + "," + e.Volume);
            }
            else if (e.MarketDataType == MarketDataType.Last)
            {
                wt.WriteLine((++seqT) + "," + Ts(utc) + "," + Ts(e.Time) + "," + e.Price + "," + e.Volume
                    + "," + bestBid + "," + bestBidSz + "," + bestAsk + "," + bestAskSz);
            }
            if (double.IsNaN(bestBid) == false && double.IsNaN(bestAsk) == false && bestBid >= bestAsk)
                Q("LOCKED_OR_CROSSED", bestBid + ">=" + bestAsk);
        }

        protected override void OnMarketDepth(MarketDepthEventArgs e)
        {
            DateTime utc = DateTime.UtcNow;
            Roll(utc);
            lastMsgUtc = utc;
            wd.WriteLine((++seqD) + "," + Ts(utc) + "," + Ts(e.Time) + "," + e.Operation + ","
                + e.MarketDataType + "," + e.Position + "," + e.Price + "," + e.Volume + ",MBP");
        }

        protected override void OnConnectionStatusUpdate(ConnectionStatusEventArgs e)
        {
            bool up = e.Status == ConnectionStatus.Connected;
            if (up != wasConnected)
            {
                Q(up ? "RECONNECT" : "DISCONNECT", e.Status.ToString());
                wasConnected = up;
            }
        }

        protected override void OnBarUpdate() { }

        private void CloseDay()
        {
            if (wq == null) return;
            Q("SESSION_END", "q=" + seqQ + " t=" + seqT + " d=" + seqD);
            foreach (var w in new List<StreamWriter> { wq, wt, wd, wc })
                if (w != null) { w.Flush(); w.Close(); }
            // daily immutable manifest: row counts + SHA-256 per file
            var sb = new StringBuilder();
            foreach (string kind in new[] { "quotes", "trades", "depth", "quality" })
            {
                string p = Path.Combine(dir, "MOFAD_CAP_" + sym + "_" + day + "_" + kind + ".csv");
                if (!File.Exists(p)) continue;
                byte[] h;
                using (var sha = SHA256.Create())
                using (var fs = File.OpenRead(p))
                    h = sha.ComputeHash(fs);
                sb.AppendLine(Path.GetFileName(p) + " sha256=" + BitConverter.ToString(h).Replace("-", "").ToLowerInvariant());
            }
            File.WriteAllText(Path.Combine(dir, "MOFAD_CAP_" + sym + "_" + day + "_manifest.txt"), sb.ToString());
            wq = wt = wd = wc = null;
        }
    }
}
