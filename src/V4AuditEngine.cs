// ======================================================================
// V4AuditEngine.cs  -  MNQ V4.1
// ======================================================================
// The startup diagnostic, the fail-fast gate, and the structure-side data
// audit.
//
// THIS FILE SUBMITS NO ORDERS.
//
// The point of this module is to make a broken run look broken. A research
// engine that quietly produces a plausible-looking CSV from a misconfigured
// chart is worse than one that crashes, because the CSV will be analysed
// and believed. Earlier stages of this project lost three full multi-year
// runs to silent failures - a volumetric reader returning false with no
// reason recorded, and a session-boundary test that reported 436 scheduled
// halts as missing data. Both were invisible until someone went looking.
//
// So: if a required series has zero bars, this fails the run rather than
// writing a file. Every audit states its thresholds before its verdict,
// and a FAILED verdict never silently lowers them.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public enum V4Verdict { PASSED, FAILED, NEEDS_REVIEW }

    /// One added data series as the host sees it.
    public struct V4SeriesInfo
    {
        public string Label;
        public int BarsInProgress;
        public int Bars;
        public DateTime FirstEt, LastEt;
        public bool Required;
        public string PeriodDesc;
    }

    /// Startup diagnostic. Printed before any row is written so that a
    /// misconfigured Strategy Analyzer is obvious in the output window
    /// rather than three hours later in the data.
    public class V4StartupDiagnostic
    {
        public string Instrument = "";
        public string MergePolicy = "";
        public string SessionTemplate = "";
        public string TimeZone = "";
        public string PrimarySeries = "";
        public string FileTag = "";
        public bool VolumetricPrimary;
        public string VolumetricType = "";
        public bool OrderFlowAvailable;
        public bool ProfileAvailable;
        public bool DepthAvailable;             // always false: NT8 keeps no historical L2
        public DateTime WarmupStartEt = DateTime.MinValue;
        public DateTime SampleStartEt = DateTime.MinValue;
        public DateTime SampleEndEt = DateTime.MinValue;
        public int RequiredWarmupBars1m;
        public string WarmupReason = "";

        public readonly List<V4SeriesInfo> Series = new List<V4SeriesInfo>();
        public readonly List<string> Failures = new List<string>();

        public void AddSeries(string label, int bip, int bars, DateTime first, DateTime last,
                              bool required, string periodDesc)
        {
            V4SeriesInfo s = new V4SeriesInfo();
            s.Label = label; s.BarsInProgress = bip; s.Bars = bars;
            s.FirstEt = first; s.LastEt = last; s.Required = required; s.PeriodDesc = periodDesc;
            Series.Add(s);
        }

        /// FAIL FAST. A required series with zero bars means the run cannot
        /// produce valid research, and producing an apparently valid file
        /// anyway is the failure mode this exists to prevent.
        public bool Validate()
        {
            Failures.Clear();
            for (int i = 0; i < Series.Count; i++)
            {
                V4SeriesInfo s = Series[i];
                if (s.Required && s.Bars <= 0)
                    Failures.Add("REQUIRED SERIES HAS ZERO BARS: " + s.Label
                               + " (BarsInProgress " + V4Num.I(s.BarsInProgress) + ", " + s.PeriodDesc + ")");
            }
            if (VolumetricPrimary && !OrderFlowAvailable)
                Failures.Add("PRIMARY SERIES IS NOT VOLUMETRIC - order-flow capture cannot run.");
            return Failures.Count == 0;
        }

        public string Text()
        {
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("MNQ V4.1 RESEARCH ENGINE - STARTUP DIAGNOSTIC");
            sb.AppendLine("THIS STRATEGY SUBMITS NO ORDERS.");
            sb.AppendLine("======================================================================");
            sb.AppendLine("  instrument         " + Instrument);
            sb.AppendLine("  merge policy       " + MergePolicy);
            sb.AppendLine("  session template   " + SessionTemplate);
            sb.AppendLine("  time zone          " + TimeZone);
            sb.AppendLine("  primary series     " + PrimarySeries);
            sb.AppendLine("  file tag           " + FileTag);
            sb.AppendLine("----------------------------------------------------------------------");
            sb.AppendLine("  SERIES / BarsInProgress MAP");
            sb.AppendLine("  bip  label     period            bars        first ET             last ET");
            for (int i = 0; i < Series.Count; i++)
            {
                V4SeriesInfo s = Series[i];
                sb.AppendLine("  " + Pad(V4Num.I(s.BarsInProgress), 4)
                            + " " + Pad(s.Label, 9)
                            + " " + Pad(s.PeriodDesc, 17)
                            + " " + Pad(V4Num.I(s.Bars), 11)
                            + " " + Pad(V4Num.T(s.FirstEt), 20)
                            + " " + V4Num.T(s.LastEt));
            }
            sb.AppendLine("----------------------------------------------------------------------");
            sb.AppendLine("  DATA LAYERS");
            sb.AppendLine("  volumetric primary " + V4Num.B(VolumetricPrimary)
                        + (VolumetricType.Length > 0 ? "   (" + VolumetricType + ")" : ""));
            sb.AppendLine("  order flow         " + (OrderFlowAvailable ? "AVAILABLE" : "NOT AVAILABLE"));
            sb.AppendLine("  volume profile     " + (ProfileAvailable ? "AVAILABLE" : "NOT AVAILABLE")
                        + "   (inherits the volumetric window exactly)");
            sb.AppendLine("  market depth       NOT AVAILABLE   (NT8 keeps no historical L2 for backtest");
            sb.AppendLine("                                      -> DEPTH VERDICT = FAILED, no depth features)");
            sb.AppendLine("----------------------------------------------------------------------");
            sb.AppendLine("  WARM-UP");
            sb.AppendLine("  required 1m bars   " + V4Num.I(RequiredWarmupBars1m));
            if (WarmupReason.Length > 0) sb.AppendLine("  driven by          " + WarmupReason);
            sb.AppendLine("  warm-up starts     " + V4Num.T(WarmupStartEt));
            sb.AppendLine("  official sample    " + V4Num.T(SampleStartEt) + "  ->  " + V4Num.T(SampleEndEt));
            sb.AppendLine("  rows before the official start are written with f_isWarmup=TRUE");
            sb.AppendLine("  and must be excluded from every official sample.");
            sb.AppendLine("======================================================================");
            if (Failures.Count == 0)
            {
                sb.AppendLine("STARTUP DIAGNOSTIC: PASS");
            }
            else
            {
                sb.AppendLine("STARTUP DIAGNOSTIC: FAIL - RUN ABORTED, NO FILES WRITTEN");
                for (int i = 0; i < Failures.Count; i++) sb.AppendLine("  " + Failures[i]);
            }
            sb.AppendLine("======================================================================");
            return sb.ToString();
        }

        private static string Pad(string s, int n)
        {
            if (s == null) s = "";
            if (s.Length >= n) return s.Substring(0, n);
            return s.PadRight(n);
        }
    }

    // ==================================================================
    // STRUCTURE-SIDE DATA AUDIT
    // ==================================================================

    /// Coverage and causality audit for the structure capture. Answers the
    /// question the analysis layer will otherwise have to assume: is this
    /// history complete enough, and did anything leak?
    public class V4StructureAudit
    {
        public long Rows;
        public long WarmupRows;
        public DateTime FirstEt = DateTime.MaxValue, LastEt = DateTime.MinValue;
        public int SessionDays;

        public long ScheduledHaltGaps;
        public long WeekendGaps;
        public long UnexplainedGaps;
        public long QuietMinutes;
        public double WorstUnexplainedGapMinutes;
        public DateTime WorstGapAtEt = DateTime.MinValue;

        /// Every row is checked: no feature timestamp may exceed the event
        /// timestamp. A single violation invalidates the capture.
        public long LookaheadViolations;
        public long AmbiguousRaces;
        public long ResolvedRaces;

        public long VectorsGreen, VectorsRed, VectorsBlue, VectorsViolet, NonVectorBars;
        public long Ema800UnavailableRows;

        public int MinRowsRequired = 20000;
        public double MaxUnexplainedGapPct = 0.5;

        private readonly HashSet<int> days = new HashSet<int>();
        private DateTime prevBarEt = DateTime.MinValue;
        public int ShortGapMinutes = 5;
        /// How late the first print after a reopen may be and still count as
        /// a quiet session rather than missing data. Thin early-MNQ overnight
        /// sessions routinely take this long to trade.
        public int ReopenGraceMinutes = 30;

        public void NoteBar(V4Bar b, int dayKey)
        {
            if (b.EtClose < FirstEt) FirstEt = b.EtClose;
            if (b.EtClose > LastEt) LastEt = b.EtClose;
            days.Add(dayKey);
            SessionDays = days.Count;

            if (prevBarEt != DateTime.MinValue)
            {
                double gap = (b.EtClose - prevBarEt).TotalMinutes;
                if (gap > 1.0 && gap < ShortGapMinutes) QuietMinutes++;
                else if (gap >= ShortGapMinutes)
                {
                    // Order matters. Weekend is tested FIRST because a Sunday
                    // reopen also lands in the 18:00 halt window, and testing
                    // the halt first swallowed every weekend into the halt
                    // count - the first sample reported 68 halts and ONE
                    // weekend across 36 session days.
                    //
                    // The grace is wide because NinjaTrader prints no bar when
                    // nothing trades. Early MNQ overnight sessions are thin
                    // enough that the first print can be a quarter of an hour
                    // after the reopen, which is a quiet market, not a hole in
                    // the data. That same confusion once made this project
                    // report 436 of 463 scheduled halts as data loss.
                    if (b.EtClose.DayOfWeek == DayOfWeek.Sunday) WeekendGaps++;
                    else if (V4SessionMap.IsScheduledHaltBoundary(b.EtClose, ReopenGraceMinutes))
                        ScheduledHaltGaps++;
                    else
                    {
                        UnexplainedGaps++;
                        if (gap > WorstUnexplainedGapMinutes)
                        { WorstUnexplainedGapMinutes = gap; WorstGapAtEt = b.EtClose; }
                    }
                }
            }
            prevBarEt = b.EtClose;
        }

        public void NoteVector(V4VectorColor c)
        {
            switch (c)
            {
                case V4VectorColor.GREEN: VectorsGreen++; break;
                case V4VectorColor.RED: VectorsRed++; break;
                case V4VectorColor.BLUE: VectorsBlue++; break;
                case V4VectorColor.VIOLET: VectorsViolet++; break;
                default: NonVectorBars++; break;
            }
        }

        /// Called per emitted row. featureAsOf must never exceed eventEt.
        public void NoteRow(DateTime eventEt, DateTime featureAsOfEt, bool isWarmup)
        {
            Rows++;
            if (isWarmup) WarmupRows++;
            if (featureAsOfEt != DateTime.MinValue && featureAsOfEt > eventEt) LookaheadViolations++;
        }

        public void NoteRace(V4RaceOutcome o)
        {
            if (o == V4RaceOutcome.AMBIGUOUS) AmbiguousRaces++;
            else if (o == V4RaceOutcome.TARGET || o == V4RaceOutcome.STOP) ResolvedRaces++;
        }

        public V4Verdict Verdict()
        {
            if (LookaheadViolations > 0) return V4Verdict.FAILED;
            if (Rows < MinRowsRequired) return V4Verdict.NEEDS_REVIEW;
            long bigGaps = UnexplainedGaps + ScheduledHaltGaps + WeekendGaps;
            double pct = bigGaps > 0 ? 100.0 * UnexplainedGaps / bigGaps : 0.0;
            if (pct > MaxUnexplainedGapPct) return V4Verdict.NEEDS_REVIEW;
            return V4Verdict.PASSED;
        }

        public string Text()
        {
            long totalVec = VectorsGreen + VectorsRed + VectorsBlue + VectorsViolet;
            long allBars = totalVec + NonVectorBars;
            StringBuilder sb = new StringBuilder();
            sb.AppendLine("======================================================================");
            sb.AppendLine("V4.1 STRUCTURE / VECTOR DATA AUDIT");
            sb.AppendLine("======================================================================");
            sb.AppendLine("Coverage");
            sb.AppendLine("  first event (ET)        " + V4Num.T(FirstEt));
            sb.AppendLine("  last event  (ET)        " + V4Num.T(LastEt));
            sb.AppendLine("  rows written            " + V4Num.I((int)Rows));
            sb.AppendLine("  of which warm-up        " + V4Num.I((int)WarmupRows) + "  (excluded from official samples)");
            sb.AppendLine("  session days            " + V4Num.I(SessionDays));
            sb.AppendLine("Gaps");
            sb.AppendLine("  scheduled halts         " + V4Num.I((int)ScheduledHaltGaps)
                        + "  (16:15-16:30 and 17:00-18:00 ET - NOT data loss)");
            sb.AppendLine("  weekend                 " + V4Num.I((int)WeekendGaps));
            sb.AppendLine("  UNEXPLAINED             " + V4Num.I((int)UnexplainedGaps));
            if (UnexplainedGaps > 0)
                sb.AppendLine("  worst unexplained       "
                    + WorstUnexplainedGapMinutes.ToString("0", CultureInfo.InvariantCulture)
                    + " min at " + V4Num.T(WorstGapAtEt));
            sb.AppendLine("  quiet minutes           " + V4Num.I((int)QuietMinutes)
                        + "  (< " + V4Num.I(ShortGapMinutes) + "m; NinjaTrader prints no bar when nothing trades)");
            sb.AppendLine("  reopen grace            " + V4Num.I(ReopenGraceMinutes) + " min after a scheduled reopen");
            sb.AppendLine("Causality");
            sb.AppendLine("  lookahead violations    " + V4Num.I((int)LookaheadViolations)
                        + "   (any value above zero INVALIDATES this capture)");
            sb.AppendLine("  every feature timestamp is checked against its own event timestamp.");
            sb.AppendLine("Stop/target race resolution");
            sb.AppendLine("  resolved                " + V4Num.I((int)ResolvedRaces));
            sb.AppendLine("  AMBIGUOUS               " + V4Num.I((int)AmbiguousRaces));
            sb.AppendLine("  An ambiguous race is one 1m bar reaching BOTH stop and target.");
            sb.AppendLine("  OHLC cannot order them, so the engine records both bounds and");
            sb.AppendLine("  refuses to pick. These rows are the candidates for a 30s pass.");
            sb.AppendLine("Vector classification (PVSRA, lookback 10, climax 2.0x, elevated 1.5x)");
            sb.AppendLine("  GREEN                   " + V4Num.I((int)VectorsGreen));
            sb.AppendLine("  RED                     " + V4Num.I((int)VectorsRed));
            sb.AppendLine("  BLUE                    " + V4Num.I((int)VectorsBlue));
            sb.AppendLine("  VIOLET                  " + V4Num.I((int)VectorsViolet));
            sb.AppendLine("  non-vector bars         " + V4Num.I((int)NonVectorBars)
                        + "  (retained as ablation controls)");
            if (allBars > 0)
                sb.AppendLine("  vector rate             "
                    + (100.0 * totalVec / allBars).ToString("0.00", CultureInfo.InvariantCulture) + "%");
            sb.AppendLine("Thresholds");
            sb.AppendLine("  require rows >= " + V4Num.I(MinRowsRequired)
                        + ", lookahead violations = 0, unexplained gaps <= "
                        + MaxUnexplainedGapPct.ToString("0.#", CultureInfo.InvariantCulture) + "% of all gaps");
            sb.AppendLine("======================================================================");
            V4Verdict v = Verdict();
            if (v == V4Verdict.PASSED)
                sb.AppendLine("VERDICT: PASSED - structure/vector history is complete enough to research.");
            else if (v == V4Verdict.NEEDS_REVIEW)
                sb.AppendLine("VERDICT: NEEDS REVIEW - usable, but read the gap and row counts above first.");
            else
                sb.AppendLine("VERDICT: FAILED - DO NOT USE THIS CAPTURE. See lookahead violations above.");
            sb.AppendLine("======================================================================");
            return sb.ToString();
        }
    }
}
