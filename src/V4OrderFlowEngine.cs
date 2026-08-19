// ============================================================================
// V4OrderFlowEngine.cs
//
// RESEARCH MODULE - SUBMITS NO ORDERS, EVER.
//
// V4 ORDER FLOW: EXECUTED FLOW ONLY.
//
// SEPARATION IS THE POINT
//   The brief is explicit: "Do NOT silently mix order-flow data into the
//   current V3 price-action research." It applies just as much to V4's own
//   structure work. This engine therefore shares NO state with
//   V4ResearchEngine, writes its OWN file, and is joined to the structure
//   dataset only in analysis, on timestamp. There is no code path by which an
//   order-flow value can reach a structure row. If order flow turns out to add
//   nothing, deleting this file changes not one number in the structure study.
//
// EXECUTED FLOW, NOT RESTING LIQUIDITY
//   Everything here comes from volume that actually TRADED: bid/ask executed
//   volume per price, bar delta, cumulative delta. No DOM, no depth, no book.
//   Resting liquidity can be added, cancelled, moved or spoofed and is not
//   reliably reconstructable from historical bars - so it is absent rather
//   than approximated.
//
// NOTHING HERE IS ASSUMED PREDICTIVE
//   Positive delta is not recorded as "bullish". Aggressive buying is not
//   recorded as "long". Every value is a measurement; whether continuation,
//   absorption, failure or reversal follows is a question for the labels in
//   the structure dataset, answered by joining, not by naming.
//
// THE DATA-QUALITY GATE
//   Historical volumetric data is reconstructed by the platform and is not
//   always complete or reproducible. V4OrderFlowAudit accumulates the exact
//   checks the brief lists - coverage, bid/ask classification consistency,
//   missing levels, timestamp gaps, session boundaries, whether ask+bid
//   reconciles to bar volume - and produces a verdict. Every row also carries
//   its own per-bar quality flag, so a partially bad history can be filtered
//   rather than discarded or, worse, trusted.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    /// Executed volume at one price inside one bar.
    public struct V4FootprintLevel
    {
        public double Price;
        public double AskVolume;   // traded at the offer  (aggressive buying)
        public double BidVolume;   // traded at the bid    (aggressive selling)
    }

    /// One volumetric / footprint bar, in a form that does not depend on the
    /// NinjaTrader API, so the whole engine is testable off-platform.
    public class V4FootprintBar
    {
        public DateTime EtOpen, EtClose;
        public double Open, High, Low, Close, Volume;
        /// TRUE when the platform actually supplied per-price volumes for this
        /// bar. FALSE is a data fact worth recording, not a reason to guess.
        public bool HasLevels;
        public readonly List<V4FootprintLevel> Levels = new List<V4FootprintLevel>();

        public double AskTotal
        {
            get { double s = 0; for (int i = 0; i < Levels.Count; i++) s += Levels[i].AskVolume; return s; }
        }
        public double BidTotal
        {
            get { double s = 0; for (int i = 0; i < Levels.Count; i++) s += Levels[i].BidVolume; return s; }
        }
        /// Bar delta computed HERE from the per-price volumes rather than read
        /// from the platform, so the value in the file is always reproducible
        /// from the other columns in the same file.
        public double Delta { get { return AskTotal - BidTotal; } }
    }

    public enum V4FlowQuality { OK, NO_LEVELS, ZERO_VOLUME, VOLUME_MISMATCH, TIME_GAP }

    // ========================================================================
    /// The brief's ORDER-FLOW DATA-QUALITY GATE, accumulated over a run.
    ///
    /// It answers, with counts rather than adjectives:
    ///   - exact historical coverage           FirstEt / LastEt / SessionDays
    ///   - missing data                        BarsNoLevels, BarsZeroVolume
    ///   - bid/ask classification methodology  BarsVolumeMismatch and its size
    ///   - timestamp precision / gaps          BarsAfterGap
    ///   - session boundaries                  SessionDays, GapsOverHalt
    ///   - whether values are causally
    ///     reconstructable                     delta is recomputed from levels
    ///   - deterministic cumulative-delta
    ///     reset                               the reset rule is stated, not
    ///                                         inherited from the platform
    // ========================================================================
    public class V4OrderFlowAudit
    {
        public long Bars;
        public long BarsWithLevels;
        public long BarsNoLevels;
        public long BarsZeroVolume;
        public long BarsVolumeMismatch;
        public long BarsAfterGap;
        public double WorstMismatchPct;
        public double SumAbsMismatchPct;
        public DateTime FirstEt = DateTime.MinValue, LastEt = DateTime.MinValue;
        private readonly Dictionary<int, bool> days = new Dictionary<int, bool>();
        private DateTime prevClose = DateTime.MinValue;
        public long BarsOffTickGrid;

        /// ask+bid may differ from bar volume by at most this fraction before the
        /// bar is counted as a classification mismatch.
        public double VolumeTolerancePct = 1.0;
        /// Minutes between consecutive 1m bars beyond which a gap is recorded.
        public int GapMinutes = 2;

        /// A gap that ENDS at the session open is a session boundary, not
        /// missing data. This is deliberately expressed as a property of the
        /// bar AFTER the gap rather than the bar before it.
        ///
        /// The first version of this check asked whether the bar BEFORE the gap
        /// closed at 16:59 ET. NinjaTrader stamps a bar with its CLOSE time, so
        /// the last bar before the daily halt is stamped 17:00, not 16:59 - the
        /// test never fired, and every single normal trading day was counted as
        /// missing data. On the first MNQ month that was 22 of 22 gaps reported
        /// as data loss when the true figure was zero.
        ///
        /// Anchoring on the reopen also covers the weekend and the early closes
        /// around holidays with one rule, instead of a holiday calendar that
        /// would need maintaining and would be wrong the first year it wasn't.
        public int SessionOpenHourEt = 18;
        public int SessionOpenGraceMinutes = 5;

        /// CME equity index futures also pause 16:15-16:30 ET, every weekday,
        /// separately from the 17:00-18:00 halt. The first version of this check
        /// knew only about the 18:00 reopen, so the afternoon pause was reported
        /// as data loss on essentially every trading day: on a real MNQ sample,
        /// 436 gaps of exactly 16:15 -> 16:31, all of them scheduled.
        public int MaintenanceHaltEndMinutesEt = 990;   // 16:30 ET

        /// Below this many minutes, a gap is a minute in which nothing traded
        /// rather than a minute that went missing.
        ///
        /// NinjaTrader does not print a bar for a minute with no volume, so in
        /// thin overnight hours the series legitimately skips. Counting those as
        /// missing data conflates "the market was quiet" with "the history is
        /// broken", which are opposite conclusions about whether the data can be
        /// trusted. They are now counted and reported separately.
        public int ShortGapMinutes = 5;

        /// Gaps that are quiet minutes rather than lost ones. Reported, but not
        /// treated as a defect.
        public long ShortNoTradeGaps;

        /// TRUE when the bar AFTER a gap is the first bar of a scheduled
        /// session, so the gap before it was scheduled too.
        public bool IsSessionBoundary(DateTime barAfterGapEt)
        {
            if (barAfterGapEt.Hour == SessionOpenHourEt
                && barAfterGapEt.Minute <= SessionOpenGraceMinutes) return true;
            int m = barAfterGapEt.Hour * 60 + barAfterGapEt.Minute;
            return m > MaintenanceHaltEndMinutesEt
                && m <= MaintenanceHaltEndMinutesEt + SessionOpenGraceMinutes;
        }

        // -- gate thresholds -------------------------------------------------
        public double MinLevelCoveragePct = 98.0;
        public double MaxVolumeMismatchPct = 2.0;
        public long MinBars = 20000;

        public void Observe(V4FootprintBar b, double tickSize)
        {
            Bars++;
            if (FirstEt == DateTime.MinValue) FirstEt = b.EtClose;
            LastEt = b.EtClose;
            days[b.EtClose.Year * 10000 + b.EtClose.Month * 100 + b.EtClose.Day] = true;

            if (prevClose != DateTime.MinValue)
            {
                double gap = (b.EtClose - prevClose).TotalMinutes;
                if (gap > GapMinutes && !IsSessionBoundary(b.EtClose))
                {
                    if (gap < ShortGapMinutes) ShortNoTradeGaps++;
                    else BarsAfterGap++;
                }
            }
            prevClose = b.EtClose;

            if (b.Volume <= 0) BarsZeroVolume++;
            if (!b.HasLevels || b.Levels.Count == 0) { BarsNoLevels++; return; }
            BarsWithLevels++;

            double classified = b.AskTotal + b.BidTotal;
            if (b.Volume > 0)
            {
                double pct = 100.0 * Math.Abs(classified - b.Volume) / b.Volume;
                SumAbsMismatchPct += pct;
                if (pct > WorstMismatchPct) WorstMismatchPct = pct;
                if (pct > VolumeTolerancePct) BarsVolumeMismatch++;
            }

            // price levels must sit on the instrument's tick grid; if they do
            // not, the reconstruction is not the one that traded.
            if (tickSize > 0)
            {
                for (int i = 0; i < b.Levels.Count; i++)
                {
                    double r = b.Levels[i].Price / tickSize;
                    if (Math.Abs(r - Math.Round(r)) > 1e-6) { BarsOffTickGrid++; break; }
                }
            }
        }

        public double LevelCoveragePct { get { return Bars > 0 ? 100.0 * BarsWithLevels / Bars : 0; } }
        public double MismatchPct { get { return BarsWithLevels > 0 ? 100.0 * BarsVolumeMismatch / BarsWithLevels : 0; } }
        public double MeanMismatchPct { get { return BarsWithLevels > 0 ? SumAbsMismatchPct / BarsWithLevels : 0; } }
        public int SessionDays { get { return days.Count; } }

        /// The gate. FALSE means the history is not good enough to support any
        /// claim about an order-flow edge - which is a valid, reportable result,
        /// not a reason to lower the thresholds.
        public bool Passed
        {
            get
            {
                return Bars >= MinBars
                    && LevelCoveragePct >= MinLevelCoveragePct
                    && MismatchPct <= MaxVolumeMismatchPct
                    && BarsOffTickGrid == 0;
            }
        }

        public string Report()
        {
            StringBuilder sb = new StringBuilder();
            CultureInfo ci = CultureInfo.InvariantCulture;
            sb.AppendLine("======================================================================");
            sb.AppendLine("V4 ORDER-FLOW DATA-QUALITY AUDIT");
            sb.AppendLine("======================================================================");
            sb.AppendLine("Coverage");
            sb.AppendLine("  first bar (ET)          " + (FirstEt == DateTime.MinValue ? "-" : FirstEt.ToString("yyyy-MM-dd HH:mm:ss", ci)));
            sb.AppendLine("  last bar  (ET)          " + (LastEt == DateTime.MinValue ? "-" : LastEt.ToString("yyyy-MM-dd HH:mm:ss", ci)));
            sb.AppendLine("  bars observed           " + Bars.ToString(ci));
            sb.AppendLine("  session days            " + SessionDays.ToString(ci));
            sb.AppendLine("Completeness");
            sb.AppendLine("  bars WITH price levels  " + BarsWithLevels.ToString(ci)
                          + "  (" + LevelCoveragePct.ToString("0.00", ci) + "%)");
            sb.AppendLine("  bars WITHOUT levels     " + BarsNoLevels.ToString(ci));
            sb.AppendLine("  bars with zero volume   " + BarsZeroVolume.ToString(ci));
            sb.AppendLine("  unexplained gaps        " + BarsAfterGap.ToString(ci)
                          + "  (>= " + ShortGapMinutes.ToString(ci)
                          + "m, outside the 16:15-16:30 and 17:00-18:00 ET halts)");
            sb.AppendLine("  quiet minutes (no trade)" + ShortNoTradeGaps.ToString(ci)
                          + "  (< " + ShortGapMinutes.ToString(ci)
                          + "m; NinjaTrader prints no bar when nothing trades)");
            sb.AppendLine("Bid/ask classification");
            sb.AppendLine("  bars where |ask+bid - volume| > " + VolumeTolerancePct.ToString("0.##", ci) + "%   "
                          + BarsVolumeMismatch.ToString(ci) + "  (" + MismatchPct.ToString("0.00", ci) + "%)");
            sb.AppendLine("  mean absolute mismatch  " + MeanMismatchPct.ToString("0.000", ci) + "%");
            sb.AppendLine("  worst single bar        " + WorstMismatchPct.ToString("0.000", ci) + "%");
            sb.AppendLine("  price levels off the tick grid (bars)  " + BarsOffTickGrid.ToString(ci));
            sb.AppendLine("Reproducibility");
            sb.AppendLine("  bar delta is RECOMPUTED from the per-price ask/bid volumes in this");
            sb.AppendLine("  same file, not read from the platform, so every delta column can be");
            sb.AppendLine("  rederived from the columns beside it.");
            sb.AppendLine("  cumulative delta resets at the CME exchange day boundary (18:00 ET).");
            sb.AppendLine("  That rule is stated here and applied in code; it is not inherited");
            sb.AppendLine("  from an indicator setting that could differ between historical and");
            sb.AppendLine("  real-time calculation.");
            sb.AppendLine("Thresholds");
            sb.AppendLine("  require bars >= " + MinBars.ToString(ci)
                          + ", level coverage >= " + MinLevelCoveragePct.ToString("0.##", ci)
                          + "%, mismatch <= " + MaxVolumeMismatchPct.ToString("0.##", ci)
                          + "%, off-grid bars = 0");
            sb.AppendLine("======================================================================");
            sb.AppendLine(Passed
                ? "VERDICT: PASSED - order-flow history is complete enough to research."
                : "VERDICT: FAILED - DO NOT USE THIS DATA TO CLAIM AN ORDER-FLOW EDGE.");
            sb.AppendLine("======================================================================");
            if (!Passed)
            {
                sb.AppendLine("A failed gate is a result, not an obstacle. Report it as");
                sb.AppendLine("'order-flow history insufficient' rather than relaxing the");
                sb.AppendLine("thresholds until it passes.");
            }
            return sb.ToString();
        }
    }

    // ========================================================================
    /// Turns volumetric bars into one measurement row per bar.
    ///
    /// Holds only what a live system would have: the bar just closed and a
    /// bounded history of bars before it. Nothing is revised after the fact.
    // ========================================================================
    public class V4OrderFlowEngine
    {
        /// Diagonal imbalance factor. Ask volume at price P counts as a buy
        /// imbalance when it is at least this multiple of the bid volume one
        /// tick BELOW it. 3.0 is the conventional footprint default and is a
        /// parameter precisely because conventions are not evidence.
        public double ImbalanceFactor = 3.0;
        /// Ignore imbalance comparisons where both sides are below this volume;
        /// a 3-versus-1 contract "imbalance" is noise, not participation.
        public double ImbalanceMinVolume = 10;
        /// Lookback for the price/delta divergence comparison, in bars.
        public int DivergenceLookback = 20;
        /// Exchange-day boundary at which cumulative delta resets, ET minutes.
        public int DayStartMinutesEt = 1080;   // 18:00 ET
        public double TickSize = 0.25;
        public string Symbol = "MNQ";
        public int EmitStartMinutesEt = 0;
        public int EmitEndMinutesEt = 1440;

        public readonly V4OrderFlowAudit Audit = new V4OrderFlowAudit();

        private readonly Action<string> sink;
        private readonly List<double> priceHist = new List<double>();
        private readonly List<double> cumHist = new List<double>();
        private readonly List<double> highHist = new List<double>();
        private readonly List<double> lowHist = new List<double>();
        private double cumDelta;
        private int curDayKey = int.MinValue;
        private DateTime prevClose = DateTime.MinValue;
        public long RowsEmitted { get; private set; }

        public V4OrderFlowEngine(Action<string> rowSink) { sink = rowSink; }

        private int DayKey(DateTime et)
        {
            DateTime d = et.Date;
            if (et.Hour * 60 + et.Minute >= DayStartMinutesEt) d = d.AddDays(1);
            return d.Year * 10000 + d.Month * 100 + d.Day;
        }

        /// Feed one COMPLETED volumetric bar, in order.
        public void OnBar(V4FootprintBar b)
        {
            Audit.Observe(b, TickSize);

            int dk = DayKey(b.EtClose);
            if (dk != curDayKey) { curDayKey = dk; cumDelta = 0; }

            double delta = b.HasLevels ? b.Delta : double.NaN;
            if (!double.IsNaN(delta)) cumDelta += delta;

            V4FlowQuality q = V4FlowQuality.OK;
            if (!b.HasLevels || b.Levels.Count == 0) q = V4FlowQuality.NO_LEVELS;
            else if (b.Volume <= 0) q = V4FlowQuality.ZERO_VOLUME;
            else if (100.0 * Math.Abs(b.AskTotal + b.BidTotal - b.Volume) / b.Volume > Audit.VolumeTolerancePct)
                q = V4FlowQuality.VOLUME_MISMATCH;
            else if (prevClose != DateTime.MinValue
                     && (b.EtClose - prevClose).TotalMinutes > Audit.GapMinutes
                     && !Audit.IsSessionBoundary(b.EtClose))
                q = V4FlowQuality.TIME_GAP;

            // ---- features computed from THIS bar only ----------------------
            double pocPrice = double.NaN, pocVol = -1;
            double deltaAtHigh = double.NaN, deltaAtLow = double.NaN;
            double volAtHigh = double.NaN, volAtLow = double.NaN;
            int buyImb = 0, sellImb = 0;
            if (b.HasLevels && b.Levels.Count > 0)
            {
                List<V4FootprintLevel> ls = new List<V4FootprintLevel>(b.Levels);
                ls.Sort(delegate(V4FootprintLevel x, V4FootprintLevel y) { return x.Price.CompareTo(y.Price); });
                for (int i = 0; i < ls.Count; i++)
                {
                    double v = ls[i].AskVolume + ls[i].BidVolume;
                    if (v > pocVol) { pocVol = v; pocPrice = ls[i].Price; }
                }
                deltaAtLow = ls[0].AskVolume - ls[0].BidVolume;
                volAtLow = ls[0].AskVolume + ls[0].BidVolume;
                deltaAtHigh = ls[ls.Count - 1].AskVolume - ls[ls.Count - 1].BidVolume;
                volAtHigh = ls[ls.Count - 1].AskVolume + ls[ls.Count - 1].BidVolume;

                // Diagonal imbalance, the standard footprint comparison: ask
                // volume at a price against bid volume one tick BELOW it. The
                // diagonal is the point - comparing a price against itself
                // compares two sides of the same trade.
                for (int i = 1; i < ls.Count; i++)
                {
                    if (Math.Abs(ls[i].Price - ls[i - 1].Price - TickSize) > TickSize * 0.5) continue;
                    double a = ls[i].AskVolume, bd = ls[i - 1].BidVolume;
                    if (a + bd < ImbalanceMinVolume) continue;
                    if (bd > 0 && a >= ImbalanceFactor * bd) buyImb++;
                    else if (a > 0 && bd >= ImbalanceFactor * a) sellImb++;
                }
            }

            // ---- features that need history --------------------------------
            double priceSlope = double.NaN, cumSlope = double.NaN;
            bool newHigh = false, newLow = false;
            double cumAtPriorHigh = double.NaN, cumAtPriorLow = double.NaN;
            int n = priceHist.Count;
            if (n >= DivergenceLookback)
            {
                priceSlope = b.Close - priceHist[n - DivergenceLookback];
                cumSlope = cumDelta - cumHist[n - DivergenceLookback];
                double hh = double.MinValue, ll = double.MaxValue;
                int hi = -1, li = -1;
                for (int i = n - DivergenceLookback; i < n; i++)
                {
                    if (highHist[i] > hh) { hh = highHist[i]; hi = i; }
                    if (lowHist[i] < ll) { ll = lowHist[i]; li = i; }
                }
                newHigh = b.High > hh;
                newLow = b.Low < ll;
                if (hi >= 0) cumAtPriorHigh = cumHist[hi];
                if (li >= 0) cumAtPriorLow = cumHist[li];
            }

            if (InWindow(b.EtClose))
            {
                StringBuilder sb = new StringBuilder(400);
                CultureInfo ci = CultureInfo.InvariantCulture;
                sb.Append(Symbol).Append("-1m-").Append(b.EtClose.ToString("yyyyMMddHHmmss", ci)).Append(',')
                  .Append(Symbol).Append(',')
                  .Append(b.EtClose.ToString("yyyy-MM-dd", ci)).Append(',')
                  .Append(b.EtClose.ToString("HH:mm:ss", ci)).Append(',');
                sb.Append(F(b.Open)).Append(',').Append(F(b.High)).Append(',').Append(F(b.Low)).Append(',')
                  .Append(F(b.Close)).Append(',').Append(F(b.Volume)).Append(',');
                sb.Append(q).Append(',').Append(b.HasLevels ? "TRUE" : "FALSE").Append(',')
                  .Append(b.Levels.Count).Append(',');
                sb.Append(F(b.HasLevels ? b.AskTotal : double.NaN)).Append(',')
                  .Append(F(b.HasLevels ? b.BidTotal : double.NaN)).Append(',')
                  .Append(F(delta)).Append(',')
                  .Append(F(b.Volume > 0 && !double.IsNaN(delta) ? 100.0 * delta / b.Volume : double.NaN)).Append(',')
                  .Append(F(cumDelta)).Append(',');
                sb.Append(F(pocPrice)).Append(',').Append(F(pocVol < 0 ? double.NaN : pocVol)).Append(',')
                  .Append(F(deltaAtHigh)).Append(',').Append(F(volAtHigh)).Append(',')
                  .Append(F(deltaAtLow)).Append(',').Append(F(volAtLow)).Append(',')
                  .Append(buyImb).Append(',').Append(sellImb).Append(',');
                sb.Append(F(priceSlope)).Append(',').Append(F(cumSlope)).Append(',')
                  .Append(newHigh ? "TRUE" : "FALSE").Append(',').Append(newLow ? "TRUE" : "FALSE").Append(',')
                  .Append(F(cumAtPriorHigh)).Append(',').Append(F(cumAtPriorLow)).Append(',');
                sb.Append(F(b.High - b.Close)).Append(',').Append(F(b.Close - b.Low));
                sink(sb.ToString());
                RowsEmitted++;
            }

            priceHist.Add(b.Close); cumHist.Add(cumDelta);
            highHist.Add(b.High); lowHist.Add(b.Low);
            if (priceHist.Count > 500)
            {
                priceHist.RemoveAt(0); cumHist.RemoveAt(0);
                highHist.RemoveAt(0); lowHist.RemoveAt(0);
            }
            prevClose = b.EtClose;
        }

        private bool InWindow(DateTime et)
        {
            int m = et.Hour * 60 + et.Minute;
            return m >= EmitStartMinutesEt && m <= EmitEndMinutesEt;
        }

        private static string F(double v)
        {
            return double.IsNaN(v) || double.IsInfinity(v) ? "" : v.ToString("0.####", CultureInfo.InvariantCulture);
        }

        /// Column names. Deliberately descriptive rather than interpretive:
        /// "deltaAtHigh", not "sellersTrapped".
        public static string CsvHeader()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("eventId,symbol,date,timeEt,open,high,low,close,volume,");
            sb.Append("quality,hasLevels,levelCount,");
            sb.Append("askVolume,bidVolume,barDelta,deltaPctOfVolume,cumDeltaDay,");
            sb.Append("pocPrice,pocVolume,deltaAtBarHigh,volumeAtBarHigh,deltaAtBarLow,volumeAtBarLow,");
            sb.Append("buyImbalanceCount,sellImbalanceCount,");
            sb.Append("priceChange20,cumDeltaChange20,newHigh20,newLow20,cumDeltaAtPriorHigh20,cumDeltaAtPriorLow20,");
            sb.Append("closeOffHighPts,closeOffLowPts");
            return sb.ToString();
        }
    }
}
