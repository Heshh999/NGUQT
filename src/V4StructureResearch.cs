// ============================================================================
// V4StructureResearch.cs
//
// RESEARCH MODULE - SUBMITS NO ORDERS, EVER.
//
// Assembles the V4 multi-timeframe market-structure dataset.
//
// TWO OUTPUT FILES, JOINED ON eventId
//
//   STRUCTURE FILE  one row per structure-break event (or sampled control),
//                   on any of Daily / 4H / 60m / 15m / 5m / 3m / 1m, carrying
//                   the full cross-timeframe state at the instant the break
//                   became knowable, and the forward outcome measured in
//                   MINUTES on the 1-minute stream.
//
//   ENTRY FILE      one row per (event, entry timeframe, entry trigger). This
//                   is the brief's ENTRY RESOLUTION section made testable:
//                   the timeframe that IDENTIFIES a behaviour need not be the
//                   timeframe that EXECUTES it, and the only way to know is to
//                   price every candidate execution against the same frozen
//                   parent event.
//
// THE SEPARATION THAT MATTERS
//   Every column in the feature block is sealed at the close of the event bar.
//   Every column in the label block comes from bars that arrived afterwards.
//   Nothing crosses. That is what allows the brief's final question - "does
//   this contain useful information BEFORE the trade, or are we describing
//   price after the fact" - to be answered rather than assumed.
//
// CONTROLS
//   A structure-break dataset with no non-break observations can only ever say
//   what happens after breaks, never whether breaks are DIFFERENT. A 1-in-N
//   sample of bars that broke nothing is therefore emitted on every timeframe,
//   in both directions, with an identical feature and label block.
//
// NO VECTOR CANDLES. NO ORDER FLOW. Order-flow research is a separate engine
// behind a separate data-quality gate, exactly as the brief requires.
// ============================================================================

using System;
using System.Collections.Generic;
using System.Globalization;
using System.Text;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public enum V4EntryTrigger { IMMEDIATE, PULLBACK_RECLAIM }
    public enum V4ProbeState { ARMED, WAITING_RECLAIM, TRIGGERED, INVALIDATED, EXPIRED }

    /// One candidate execution of one frozen parent event.
    public class V4EntryProbe
    {
        public string EntryTf;
        public V4EntryTrigger Trigger;
        public V4ProbeState State = V4ProbeState.ARMED;

        public bool PullbackSeen;
        public DateTime EntryEt = DateTime.MinValue;
        public double EntryPrice = double.NaN;
        public double StopPrice = double.NaN;
        public double StopPts = double.NaN;
        public int MinutesToEntry = -1;

        public double RunMfePts, RunMaePts;
        public int MinutesToStop = -1;
        public int[] MinutesToR;
        public double[] NetAtMin;
        public int MinutesObserved;

        public V4EntryProbe(int rGrid, int horizons)
        {
            MinutesToR = new int[rGrid];
            for (int i = 0; i < rGrid; i++) MinutesToR[i] = -1;
            NetAtMin = new double[horizons];
            for (int i = 0; i < horizons; i++) NetAtMin[i] = double.NaN;
        }
    }

    /// One structure-break observation, or one sampled control.
    public class V4Event
    {
        // ---- identity ----------------------------------------------------
        public string EventId = "";
        public string Symbol = "MNQ";
        public string EventKind = "BREAK";      // BREAK or CONTROL
        public bool IsWarmup;
        public string Tf = "";
        public int TfMinutes;
        public DateTime EtOpen, EtClose;
        public long BarIndex;

        // ---- the break itself (all knowable at EtClose) --------------------
        public int Dir;                          // +1 broke a prior high, -1 broke a prior low
        public string LevelName = "NONE";        // SWING_HIGH / SWING_LOW / NONE for controls
        public double LevelPrice = double.NaN;
        public DateTime LevelFormedEt = DateTime.MinValue;
        public DateTime LevelKnownEt = DateTime.MinValue;
        public int LevelAgeMinutes = -1;
        public string PriorSwingLabel = "UNKNOWN";   // the HH/HL/LH/LL label of the level itself
        public V4BreakOutcome Outcome = V4BreakOutcome.NO_TOUCH;
        public double PenetrationPts = double.NaN, PenetrationAtr = double.NaN;
        public double CloseBeyondPts = double.NaN, CloseBeyondAtr = double.NaN;

        // ---- the break bar -------------------------------------------------
        public double Open, High, Low, Close, Volume;
        public double BodyPts, BodyAtr, BarRangePts, BarRangeAtr, RelVolume = double.NaN;

        // ---- event-timeframe context --------------------------------------
        public double TfAtr = double.NaN;
        public double TfCompression = double.NaN, TfExpansion = double.NaN;
        public double TfRangePts = double.NaN, TfPosInRange = double.NaN;

        // ---- cross-timeframe structure, snapshotted at SnapshotCutoff ------
        public V4StructureState[] States;
        public int[] MinutesInState;

        public int AlignAgree, AlignOppose, AlignNone, AlignTransitioning;
        public V4Alignment Alignment = V4Alignment.UNKNOWN;
        public V4Dir HtfDir = V4Dir.NONE;

        public bool ArchA, ArchB, ArchC;

        // ---- location ------------------------------------------------------
        public DateTime LocAsOfEt = DateTime.MinValue;
        public double DistPdhAtr = double.NaN, DistPdlAtr = double.NaN;
        public double DistPwhAtr = double.NaN, DistPwlAtr = double.NaN;
        public double DistSessHighAtr = double.NaN, DistSessLowAtr = double.NaN;
        public double DistSessOpenAtr = double.NaN, DistVwapAtr = double.NaN;
        public string NearestLevel = "NONE";
        public double NearestLevelAtr = double.NaN;
        public bool AtLocation;

        // ---- candidate structural stops, chosen at event time --------------
        public double StopSwingPts = double.NaN;   // opposite confirmed swing
        public double StopBarPts = double.NaN;     // the break bar's own far side
        public double StopAtrPts = double.NaN;     // volatility-scaled

        // ---- sequence context ----------------------------------------------
        public int BreaksTodayThisTf;
        public bool PriorFailedBreakThisTf;

        // ---- LABELS: nothing below here is knowable at EtClose --------------
        public int MinutesObserved;
        public double[] NetAtMin;                  // signed by Dir, in points
        public double[] MfeAtMin;                  // favourable, in points
        public double[] MaeAtMin;                  // adverse, positive magnitude
        public double RunMfePts, RunMaePts;
        public double ContMaxPts = 0, ContMaxAtr = double.NaN;
        public int[] MinutesToCont;                // per ATR grid step beyond the level
        public bool Retested;
        public int MinutesToRetest = -1;
        public double RetestDepthPct = double.NaN;
        public bool RetestClosedBack;
        public int ClosesBeyondFirst30, ClosesBeyondFirst60;
        public bool FailedBreak;
        public int MinutesToFail = -1;
        public bool Reversal;
        public int MinutesToReversal = -1;
        public double VolExpansion = double.NaN;
        public V4FollowState Follow = V4FollowState.UNRESOLVED;
        public int MinutesToStop = -1;
        public int[] MinutesToR;

        // running helpers for label resolution
        public double PeakBeyondPrice = double.NaN;   // best excursion in Dir since the break
        public double TroughAfterPeak = double.NaN;   // deepest retrace after that peak
        public double Atr1mAtBreak = double.NaN;
        public double Tr1mSumNext30;
        public int Tr1mCountNext30;
        public bool ClosedBackOnce;

        public readonly List<V4EntryProbe> Probes = new List<V4EntryProbe>();
        public bool Complete;
    }

    // ========================================================================
    public class V4ResearchEngine
    {
        /// Forward horizons, in MINUTES from the instant the break became
        /// knowable. Minutes rather than bars, so a Daily break and a 1m break
        /// are measured on the same ruler and can be compared at all.
        public static readonly int[] HorizonMinutes = new int[] { 5, 15, 30, 60, 120, 240 };
        /// Continuation distances, in multiples of the EVENT timeframe's ATR,
        /// measured beyond the broken level.
        public static readonly double[] ContAtrGrid = new double[] { 0.5, 1.0, 1.5, 2.0, 3.0 };
        /// R multiples raced against the structural stop.
        public static readonly double[] RGrid = new double[] { 0.5, 1.0, 1.5, 2.0, 3.0 };

        /// Column order for the cross-timeframe structure snapshot. Fixed, so
        /// the CSV shape never depends on which series happened to load.
        public static readonly string[] TfOrder = new string[] { "1d", "4h", "60m", "15m", "5m", "3m", "1m" };
        /// The timeframes whose agreement defines ALIGNMENT.
        public static readonly string[] AlignOrder = new string[] { "1d", "4h", "60m", "15m" };
        /// Timeframes eligible to host an entry.
        public static readonly string[] EntryTfOrder = new string[] { "15m", "5m", "3m", "1m" };

        private const int MaxHorizonMinutes = 240;

        // -- configuration ----------------------------------------------------
        public string Symbol = "MNQ";
        /// Inside this many ATR of a level counts as APPROACHED.
        public double ApproachBandAtr = 0.5;
        /// Penetration up to this many ATR, closing back, is a wick rather than
        /// a genuine trade beyond.
        public double WickMaxAtr = 0.25;
        /// Displacement requires BOTH a body of this many ATR and a close this
        /// many ATR beyond the level.
        public double DisplacementBodyAtr = 1.0;
        public double DisplacementCloseAtr = 0.35;
        /// Coming back inside this many ATR of the level counts as a retest.
        public double RetestBandAtr = 0.25;
        /// Closing this many ATR back on the original side counts as failure.
        public double FailBufferAtr = 0.10;
        /// Travelling this many ATR against the break, measured from the level,
        /// counts as a reversal.
        public double ReversalAtr = 1.0;
        /// Buffer beyond the structural reference for a candidate stop.
        public double StopBufferAtr = 0.15;
        /// ATR multiple for the volatility-scaled candidate stop.
        public double AtrStopMultiple = 1.0;
        /// A state younger than this many bars of its own timeframe counts as
        /// TRANSITIONING rather than settled.
        public int TransitionBars = 2;
        /// A break within this many ATR of a tracked location counts as AT it.
        public double AtLocationAtr = 0.35;
        /// Keep 1 in N bars that broke nothing, per timeframe, as controls.
        /// 0 disables the control group entirely.
        public int ControlSampleRate = 400;
        /// Emission window in ET minutes, applied to the EVENT bar's close.
        public int EmitStartMinutesEt = 0;
        public int EmitEndMinutesEt = 1440;
        /// Rows closing before this are flagged isWarmup=TRUE. Fully processed
        /// so context is warm, but excluded from every statistic.
        public DateTime TargetSampleStartEt = DateTime.MinValue;
        /// Emit entry-resolution rows at all.
        public bool EmitEntries = true;

        // -- state ------------------------------------------------------------
        private readonly Dictionary<string, V4StructureTracker> trackers =
            new Dictionary<string, V4StructureTracker>();
        private readonly Dictionary<string, long> barCounters = new Dictionary<string, long>();
        private readonly Dictionary<string, bool> emitEvents = new Dictionary<string, bool>();
        private readonly Dictionary<string, double> lastBrokenHigh = new Dictionary<string, double>();
        private readonly Dictionary<string, double> lastBrokenLow = new Dictionary<string, double>();
        private readonly Dictionary<string, int> breaksToday = new Dictionary<string, int>();
        private readonly Dictionary<string, bool> failedBreakToday = new Dictionary<string, bool>();
        private readonly List<V4Event> pending = new List<V4Event>();
        private readonly Action<string> structureSink;
        private readonly Action<string> entrySink;
        private readonly Random ctrlRng = new Random(20240401);
        private readonly V4Atr atr1m = new V4Atr(20);

        private V4Bar queued1m;
        private bool has1mQueued;
        private double prev1mClose = double.NaN;
        private int curDayKey = int.MinValue;

        public readonly V4LocationBook Location = new V4LocationBook();

        public int BreaksEmitted { get; private set; }
        public int ControlsEmitted { get; private set; }
        public int EntryRowsEmitted { get; private set; }
        public int EventsPending { get { return pending.Count; } }

        public V4ResearchEngine(Action<string> structureRowSink, Action<string> entryRowSink)
        {
            structureSink = structureRowSink;
            entrySink = entryRowSink;
        }

        /// The instant every cross-timeframe read is gated on: strictly BEFORE
        /// the event bar closes.
        ///
        /// This one line decides whether the whole dataset is honest, so it is
        /// worth being explicit about why it is not simply the bar's open or
        /// its close.
        ///
        ///   Using the bar's CLOSE would admit a swing confirmed by a bar that
        ///   closed at the very same instant - including, on the event's own
        ///   timeframe, a swing the event bar itself confirmed. A bar cannot be
        ///   allowed to break a level it helped create.
        ///
        ///   Using the bar's OPEN would throw away everything that became known
        ///   DURING the bar, which for a Daily event means discarding an entire
        ///   day of legitimately known lower-timeframe structure. That is not
        ///   caution, it is just wrong data.
        ///
        ///   One second before the close admits everything genuinely knowable
        ///   beforehand and nothing simultaneous. It is also independent of the
        ///   order NinjaTrader happens to deliver equal-timestamp series in,
        ///   which means the dataset does not silently change if AddDataSeries
        ///   ordering is ever edited.
        public static DateTime SnapshotCutoff(V4Bar b) { return b.EtClose.AddSeconds(-1); }

        public void AddTracker(V4StructureTracker t)
        {
            trackers[t.Label] = t;
            barCounters[t.Label] = 0;
            emitEvents[t.Label] = true;
            breaksToday[t.Label] = 0;
            failedBreakToday[t.Label] = false;
        }

        /// Whether a timeframe may produce EVENTS of its own.
        ///
        /// Turning this off still runs the timeframe's tracker in full - its
        /// structure state, its swings and its entry probes all keep working -
        /// it simply stops that timeframe from being a source of break rows.
        ///
        /// This exists for one reason the brief states directly: "Do not search
        /// for a 1-minute pattern simply because 1-minute data exists." The 1m
        /// series has to be loaded regardless, because it is the label clock, so
        /// without this switch the mere fact of needing 1m for measurement would
        /// flood the dataset with 1m hypotheses nobody asked for.
        public void SetEventEmission(string label, bool on)
        {
            if (trackers.ContainsKey(label)) emitEvents[label] = on;
        }

        public V4StructureTracker Tracker(string label)
        {
            V4StructureTracker t;
            return trackers.TryGetValue(label, out t) ? t : null;
        }

        /// Deterministic id. Depends on nothing run-local, so re-running the
        /// capture or splitting it into monthly files produces the same ids and
        /// the entry file still joins.
        public static string MakeEventId(string symbol, string tf, DateTime etClose, int dir)
        {
            return symbol + "-" + tf + "-" + etClose.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture)
                 + "-" + (dir > 0 ? "U" : "D");
        }

        /// Month a row belongs to, read from the timestamp inside its eventId.
        /// Rows are emitted LATE - only once the forward horizon has elapsed -
        /// so a monthly writer must route on the row's own timestamp, not on
        /// whatever the clock says when the row is written.
        public static string MonthKeyFromRow(string row)
        {
            if (row == null) return "unknown";
            int i = row.IndexOf('-');
            if (i < 0) return "unknown";
            int j = row.IndexOf('-', i + 1);
            if (j < 0 || row.Length < j + 7) return "unknown";
            string digits = row.Substring(j + 1, 6);
            for (int k = 0; k < digits.Length; k++)
                if (digits[k] < '0' || digits[k] > '9') return "unknown";
            return digits.Substring(0, 4) + "-" + digits.Substring(4, 2);
        }

        // ====================================================================
        // FEED
        // ====================================================================

        /// Feed one COMPLETED bar of a tracked structure timeframe, in order.
        /// This both advances that timeframe's structure and, if the bar broke a
        /// prior confirmed swing, creates the event.
        public void OnStructureBar(string tfLabel, V4Bar b)
        {
            V4StructureTracker t;
            if (!trackers.TryGetValue(tfLabel, out t)) return;

            // The level book must be read BEFORE this bar updates the tracker,
            // otherwise the bar could break a swing it helped confirm.
            DateTime cut = SnapshotCutoff(b);
            V4Swing refHigh = t.SwingHighKnownAt(cut);
            V4Swing refLow = t.SwingLowKnownAt(cut);
            double tfAtr = t.AtrValue;
            bool ready = t.AtrReady;

            barCounters[tfLabel] = barCounters[tfLabel] + 1;

            // entry probes on this timeframe see the bar before it is consumed
            // by structure, which is the order a live system would see it in.
            if (EmitEntries) AdvanceProbes(tfLabel, b);

            bool mayEmit;
            if (!emitEvents.TryGetValue(tfLabel, out mayEmit)) mayEmit = true;

            bool madeEvent = false;
            if (ready && mayEmit && InEmitWindow(b.EtClose))
            {
                madeEvent = TryBreak(t, b, refHigh, +1, tfAtr)
                          | TryBreak(t, b, refLow, -1, tfAtr);

                if (!madeEvent && ControlSampleRate > 0 && ctrlRng.Next(ControlSampleRate) == 0)
                {
                    NewEvent(t, b, +1, tfAtr, null, V4BreakOutcome.NO_TOUCH, true);
                    NewEvent(t, b, -1, tfAtr, null, V4BreakOutcome.NO_TOUCH, true);
                }
            }

            t.OnBar(b);
        }

        private bool TryBreak(V4StructureTracker t, V4Bar b, V4Swing lvl, int dir, double tfAtr)
        {
            if (!lvl.Valid) return false;
            V4BreakOutcome o = V4BreakClassifier.Classify(b, lvl.Price, dir, tfAtr,
                ApproachBandAtr, WickMaxAtr, DisplacementBodyAtr, DisplacementCloseAtr);
            if (!V4BreakClassifier.IsAnyBreak(o)) return false;

            // Emit ONE event per distinct level price per side. Bars 2..n poking
            // the same swing are the RETEST of the first break, and are captured
            // as labels on it rather than as fresh independent events - which
            // would multiply-count a single structural fact.
            string key = t.Label + (dir > 0 ? "H" : "L");
            Dictionary<string, double> seen = dir > 0 ? lastBrokenHigh : lastBrokenLow;
            double prev;
            if (seen.TryGetValue(key, out prev) && Math.Abs(prev - lvl.Price) < 1e-9) return false;
            seen[key] = lvl.Price;

            NewEvent(t, b, dir, tfAtr, new V4Swing?(lvl), o, false);
            return true;
        }

        /// Feed one COMPLETED 1-minute bar. This is the label clock: every
        /// forward measurement in the dataset is advanced here and nowhere else.
        ///
        /// The location book is folded in with a ONE-BAR DELAY, so whatever
        /// order NinjaTrader happens to deliver equal-timestamp series in, the
        /// location context of an event is always strictly older than the event.
        public void OnOneMinuteBar(V4Bar b)
        {
            int dk = Location.ExchangeDayKey(b.EtClose);
            if (dk != curDayKey)
            {
                curDayKey = dk;
                List<string> keys = new List<string>(breaksToday.Keys);
                for (int i = 0; i < keys.Count; i++)
                {
                    breaksToday[keys[i]] = 0;
                    failedBreakToday[keys[i]] = false;
                }
            }

            atr1m.Add(b);
            UpdatePending(b);

            if (has1mQueued) Location.Apply(queued1m);
            queued1m = b; has1mQueued = true;
            prev1mClose = b.Close;

            FlushComplete();
        }

        /// Close out every open event. Rows whose horizon never completed are
        /// still written, with minutesObserved saying how far they actually got,
        /// so a truncated tail is visible in the data instead of silently absent.
        public void Finish()
        {
            for (int i = 0; i < pending.Count; i++) { Resolve(pending[i]); pending[i].Complete = true; }
            FlushComplete();
        }

        private bool InEmitWindow(DateTime et)
        {
            int m = et.Hour * 60 + et.Minute;
            return m >= EmitStartMinutesEt && m <= EmitEndMinutesEt;
        }

        // ====================================================================
        // EVENT CONSTRUCTION - everything here is sealed at the bar's close
        // ====================================================================

        private void NewEvent(V4StructureTracker t, V4Bar b, int dir, double tfAtr,
                              V4Swing? lvl, V4BreakOutcome o, bool isControl)
        {
            V4Event e = new V4Event();
            e.Symbol = Symbol;
            e.EventKind = isControl ? "CONTROL" : "BREAK";
            e.Tf = t.Label; e.TfMinutes = t.MinutesPerBar;
            e.EtOpen = b.EtOpen; e.EtClose = b.EtClose;
            e.BarIndex = barCounters[t.Label];
            e.Dir = dir;
            e.EventId = MakeEventId(Symbol, t.Label, b.EtClose, dir)
                      + (isControl ? "-C" : "");
            e.IsWarmup = b.EtClose < TargetSampleStartEt;

            e.Open = b.Open; e.High = b.High; e.Low = b.Low; e.Close = b.Close; e.Volume = b.Volume;
            e.BarRangePts = b.High - b.Low;
            e.BodyPts = Math.Abs(b.Close - b.Open);
            e.TfAtr = tfAtr;
            if (tfAtr > 0) { e.BarRangeAtr = e.BarRangePts / tfAtr; e.BodyAtr = e.BodyPts / tfAtr; }
            e.RelVolume = t.RelVolume();
            e.TfCompression = t.CompressionRatio();
            e.TfExpansion = t.ExpansionRatio();
            DateTime cut = SnapshotCutoff(b);
            e.TfRangePts = t.RangePtsKnownAt(cut);
            e.TfPosInRange = t.PosInRangeKnownAt(cut, b.Close);

            if (lvl.HasValue)
            {
                V4Swing s = lvl.Value;
                e.LevelName = dir > 0 ? "SWING_HIGH" : "SWING_LOW";
                e.LevelPrice = s.Price;
                e.LevelFormedEt = s.FormedAtEt;
                e.LevelKnownEt = s.KnownAtEt;
                e.LevelAgeMinutes = (int)(b.EtClose - s.FormedAtEt).TotalMinutes;
                e.PriorSwingLabel = s.Label.ToString();
                e.Outcome = o;
                double extreme = dir > 0 ? b.High : b.Low;
                e.PenetrationPts = dir > 0 ? extreme - s.Price : s.Price - extreme;
                e.CloseBeyondPts = dir > 0 ? b.Close - s.Price : s.Price - b.Close;
                if (tfAtr > 0)
                {
                    e.PenetrationAtr = e.PenetrationPts / tfAtr;
                    e.CloseBeyondAtr = e.CloseBeyondPts / tfAtr;
                }
                breaksToday[t.Label] = breaksToday[t.Label] + 1;
            }
            else
            {
                // A control has no level. Anchoring its labels on the bar close
                // keeps the label arithmetic identical to a break's.
                e.LevelPrice = b.Close;
            }
            e.BreaksTodayThisTf = breaksToday[t.Label];
            e.PriorFailedBreakThisTf = failedBreakToday[t.Label];

            // ---- cross-timeframe snapshot, gated on the event bar's OPEN ----
            e.States = new V4StructureState[TfOrder.Length];
            e.MinutesInState = new int[TfOrder.Length];
            for (int i = 0; i < TfOrder.Length; i++)
            {
                V4StructureTracker o2;
                if (trackers.TryGetValue(TfOrder[i], out o2))
                {
                    e.States[i] = o2.StateKnownAt(cut);
                    e.MinutesInState[i] = o2.MinutesInStateAt(cut);
                }
                else { e.States[i] = V4StructureState.UNKNOWN; e.MinutesInState[i] = -1; }
            }
            ComputeAlignment(e, cut, dir);
            ComputeArchitectures(e, cut, dir);

            // ---- location ----------------------------------------------------
            double refPrice = lvl.HasValue ? lvl.Value.Price : b.Close;
            e.LocAsOfEt = Location.AsOfEt;
            e.DistPdhAtr = V4LocationBook.DistAtr(refPrice, Location.PriorDayHigh, tfAtr);
            e.DistPdlAtr = V4LocationBook.DistAtr(refPrice, Location.PriorDayLow, tfAtr);
            e.DistPwhAtr = V4LocationBook.DistAtr(refPrice, Location.PriorWeekHigh, tfAtr);
            e.DistPwlAtr = V4LocationBook.DistAtr(refPrice, Location.PriorWeekLow, tfAtr);
            e.DistSessHighAtr = V4LocationBook.DistAtr(refPrice, Location.SessionHigh, tfAtr);
            e.DistSessLowAtr = V4LocationBook.DistAtr(refPrice, Location.SessionLow, tfAtr);
            e.DistSessOpenAtr = V4LocationBook.DistAtr(refPrice, Location.SessionOpen, tfAtr);
            e.DistVwapAtr = V4LocationBook.DistAtr(refPrice, Location.SessionVwap, tfAtr);
            Location.Nearest(refPrice, tfAtr, out e.NearestLevel, out e.NearestLevelAtr);
            e.AtLocation = !double.IsNaN(e.NearestLevelAtr) && e.NearestLevelAtr <= AtLocationAtr;

            // ---- candidate structural stops ---------------------------------
            double buf = tfAtr > 0 ? StopBufferAtr * tfAtr : 0;
            V4Swing opp = dir > 0 ? t.SwingLowKnownAt(cut) : t.SwingHighKnownAt(cut);
            if (opp.Valid)
                e.StopSwingPts = dir > 0 ? (b.Close - (opp.Price - buf)) : ((opp.Price + buf) - b.Close);
            e.StopBarPts = dir > 0 ? (b.Close - (b.Low - buf)) : ((b.High + buf) - b.Close);
            e.StopAtrPts = tfAtr > 0 ? tfAtr * AtrStopMultiple : double.NaN;

            // ---- label containers -------------------------------------------
            e.NetAtMin = new double[HorizonMinutes.Length];
            e.MfeAtMin = new double[HorizonMinutes.Length];
            e.MaeAtMin = new double[HorizonMinutes.Length];
            for (int i = 0; i < HorizonMinutes.Length; i++)
            { e.NetAtMin[i] = double.NaN; e.MfeAtMin[i] = double.NaN; e.MaeAtMin[i] = double.NaN; }
            e.MinutesToCont = new int[ContAtrGrid.Length];
            for (int i = 0; i < ContAtrGrid.Length; i++) e.MinutesToCont[i] = -1;
            e.MinutesToR = new int[RGrid.Length];
            for (int i = 0; i < RGrid.Length; i++) e.MinutesToR[i] = -1;
            e.Atr1mAtBreak = atr1m.Value;
            e.PeakBeyondPrice = b.Close;
            e.TroughAfterPeak = b.Close;

            if (EmitEntries && !isControl) ArmProbes(e, t);
            pending.Add(e);
        }

        private void ComputeAlignment(V4Event e, DateTime cut, int dir)
        {
            V4Dir want = dir > 0 ? V4Dir.UP : V4Dir.DOWN;
            int agree = 0, oppose = 0, none = 0, trans = 0, avail = 0;
            for (int i = 0; i < AlignOrder.Length; i++)
            {
                V4StructureTracker t;
                if (!trackers.TryGetValue(AlignOrder[i], out t)) continue;
                V4StructureState s = t.StateKnownAt(cut);
                if (s == V4StructureState.UNKNOWN) continue;
                avail++;
                int mins = t.MinutesInStateAt(cut);
                if (mins >= 0 && mins < TransitionBars * t.MinutesPerBar) trans++;
                V4Dir d = V4StructureTracker.DirOf(s);
                if (d == want) agree++;
                else if (d == V4Dir.NONE) none++;
                else oppose++;
            }
            e.AlignAgree = agree; e.AlignOppose = oppose; e.AlignNone = none;
            e.AlignTransitioning = trans;

            // TRANSITIONING is reported first because the brief treats it as its
            // own regime, not as a degraded version of alignment. The raw counts
            // are emitted alongside so the categorical can always be re-cut.
            if (avail == 0) e.Alignment = V4Alignment.UNKNOWN;
            else if (trans > 0) e.Alignment = V4Alignment.TRANSITIONING;
            else if (agree == avail) e.Alignment = V4Alignment.FULLY_ALIGNED;
            else if (oppose > 0 && agree > 0) e.Alignment = V4Alignment.CONFLICTING;
            else if (agree > 0) e.Alignment = V4Alignment.PARTIALLY_ALIGNED;
            else if (oppose > 0) e.Alignment = V4Alignment.CONFLICTING;
            else e.Alignment = V4Alignment.UNKNOWN;

            e.HtfDir = agree > oppose ? want
                     : oppose > agree ? (want == V4Dir.UP ? V4Dir.DOWN : V4Dir.UP)
                     : V4Dir.NONE;
        }

        /// The three architectures the brief asks to be compared objectively.
        /// They are recorded as qualification FLAGS on the event, not as
        /// strategies: the entry half of each chain lives in the entry file, so
        /// "4H -> 60m -> 15m event -> 3m/1m entry" is a join, not an assumption.
        private void ComputeArchitectures(V4Event e, DateTime cut, int dir)
        {
            V4Dir want = dir > 0 ? V4Dir.UP : V4Dir.DOWN;
            V4Dir d4h = DirAt("4h", cut), d60 = DirAt("60m", cut), d15 = DirAt("15m", cut);

            // ARCH_A  4H structure -> 60m direction -> 15m event -> 3m/1m entry
            e.ArchA = e.Tf == "15m" && d4h == want && d60 == want;
            // ARCH_B  60m structure -> 15m setup -> 3m entry
            e.ArchB = e.Tf == "15m" && d60 == want;
            // ARCH_C  15m structure -> 1m entry
            e.ArchC = e.Tf == "1m" && d15 == want;
        }

        private V4Dir DirAt(string label, DateTime cut)
        {
            V4StructureTracker t;
            if (!trackers.TryGetValue(label, out t)) return V4Dir.NONE;
            return V4StructureTracker.DirOf(t.StateKnownAt(cut));
        }

        private void ArmProbes(V4Event e, V4StructureTracker eventTf)
        {
            for (int i = 0; i < EntryTfOrder.Length; i++)
            {
                V4StructureTracker et;
                if (!trackers.TryGetValue(EntryTfOrder[i], out et)) continue;
                // Executing on a timeframe COARSER than the one that found the
                // event cannot improve trade location; it can only delay it.
                if (et.MinutesPerBar > eventTf.MinutesPerBar) continue;

                V4EntryProbe imm = new V4EntryProbe(RGrid.Length, HorizonMinutes.Length);
                imm.EntryTf = et.Label; imm.Trigger = V4EntryTrigger.IMMEDIATE;
                V4EntryProbe pb = new V4EntryProbe(RGrid.Length, HorizonMinutes.Length);
                pb.EntryTf = et.Label; pb.Trigger = V4EntryTrigger.PULLBACK_RECLAIM;
                pb.State = V4ProbeState.WAITING_RECLAIM;
                e.Probes.Add(imm); e.Probes.Add(pb);
            }

            // Same-timeframe IMMEDIATE execution fills at the close of the break
            // bar itself, which is the honest price for "act on the signal". Any
            // other treatment would credit the strategy with a better price than
            // the signal it acted on.
            if (V4BreakClassifier.IsCloseThrough(e.Outcome))
            {
                for (int i = 0; i < e.Probes.Count; i++)
                {
                    V4EntryProbe p = e.Probes[i];
                    if (p.Trigger != V4EntryTrigger.IMMEDIATE || p.EntryTf != e.Tf) continue;
                    V4Bar bar = new V4Bar();
                    bar.EtOpen = e.EtOpen; bar.EtClose = e.EtClose;
                    bar.Open = e.Open; bar.High = e.High; bar.Low = e.Low; bar.Close = e.Close;
                    FillProbe(e, p, bar);
                }
            }
        }

        // ====================================================================
        // ENTRY PROBES
        // ====================================================================

        private void AdvanceProbes(string tfLabel, V4Bar b)
        {
            for (int i = 0; i < pending.Count; i++)
            {
                V4Event e = pending[i];
                if (e.Complete || e.EventKind == "CONTROL") continue;
                if (b.EtClose <= e.EtClose) continue;
                double atr = e.TfAtr;
                if (double.IsNaN(atr) || atr <= 0) continue;

                for (int k = 0; k < e.Probes.Count; k++)
                {
                    V4EntryProbe p = e.Probes[k];
                    if (p.EntryTf != tfLabel) continue;
                    if (p.State == V4ProbeState.TRIGGERED || p.State == V4ProbeState.INVALIDATED
                        || p.State == V4ProbeState.EXPIRED) continue;

                    bool up = e.Dir > 0;
                    double lvl = e.LevelPrice;
                    bool closedBeyond = up ? b.Close > lvl : b.Close < lvl;
                    bool closedBack = up ? b.Close < lvl - FailBufferAtr * atr
                                         : b.Close > lvl + FailBufferAtr * atr;

                    if (p.Trigger == V4EntryTrigger.IMMEDIATE)
                    {
                        if (closedBeyond) FillProbe(e, p, b);
                        continue;
                    }

                    // PULLBACK_RECLAIM: price must first come back to the broken
                    // level, then reclaim it in the direction of the break. A
                    // close back through before the reclaim voids the probe -
                    // the structural premise is gone, and pretending otherwise
                    // would quietly turn a failed break into a winning entry.
                    if (!p.PullbackSeen)
                    {
                        bool touched = up ? b.Low <= lvl + RetestBandAtr * atr
                                          : b.High >= lvl - RetestBandAtr * atr;
                        if (closedBack) { p.State = V4ProbeState.INVALIDATED; continue; }
                        if (touched) p.PullbackSeen = true;
                        continue;
                    }
                    if (closedBack) { p.State = V4ProbeState.INVALIDATED; continue; }
                    if (closedBeyond) FillProbe(e, p, b);
                }
            }
        }

        private void FillProbe(V4Event e, V4EntryProbe p, V4Bar b)
        {
            double atr = e.TfAtr;
            double buf = double.IsNaN(atr) || atr <= 0 ? 0 : StopBufferAtr * atr;
            p.State = V4ProbeState.TRIGGERED;
            p.EntryEt = b.EtClose;
            p.EntryPrice = b.Close;
            p.MinutesToEntry = (int)(b.EtClose - e.EtClose).TotalMinutes;
            if (e.Dir > 0)
            {
                double anchor = Math.Min(b.Low, e.LevelPrice);
                p.StopPrice = anchor - buf;
                p.StopPts = p.EntryPrice - p.StopPrice;
            }
            else
            {
                double anchor = Math.Max(b.High, e.LevelPrice);
                p.StopPrice = anchor + buf;
                p.StopPts = p.StopPrice - p.EntryPrice;
            }
        }

        // ====================================================================
        // LABELS - fed only by 1-minute bars that arrived AFTER the event
        // ====================================================================

        private void UpdatePending(V4Bar b)
        {
            for (int i = 0; i < pending.Count; i++)
            {
                V4Event e = pending[i];
                if (e.Complete) continue;
                if (b.EtClose <= e.EtClose) continue;

                int mins = (int)(b.EtClose - e.EtClose).TotalMinutes;
                e.MinutesObserved = mins;
                bool up = e.Dir > 0;
                double lvl = e.LevelPrice;
                double atr = e.TfAtr;

                // ---- excursions, signed by the direction of the break --------
                double fav = up ? b.High - e.Close : e.Close - b.Low;
                double adv = up ? e.Close - b.Low : b.High - e.Close;
                if (fav > e.RunMfePts) e.RunMfePts = fav;
                if (adv > e.RunMaePts) e.RunMaePts = adv;
                for (int h = 0; h < HorizonMinutes.Length; h++)
                {
                    if (mins <= HorizonMinutes[h])
                    {
                        e.MfeAtMin[h] = e.RunMfePts; e.MaeAtMin[h] = e.RunMaePts;
                        if (mins == HorizonMinutes[h]) e.NetAtMin[h] = up ? b.Close - e.Close : e.Close - b.Close;
                    }
                }

                // ---- continuation beyond the broken level --------------------
                double beyond = up ? b.High - lvl : lvl - b.Low;
                if (beyond > e.ContMaxPts) e.ContMaxPts = beyond;
                if (!double.IsNaN(atr) && atr > 0)
                    for (int g = 0; g < ContAtrGrid.Length; g++)
                        if (e.MinutesToCont[g] < 0 && beyond >= ContAtrGrid[g] * atr)
                            e.MinutesToCont[g] = mins;

                // ---- retest: back to the level after having gone beyond ------
                double peakBeyond = up ? Math.Max(e.PeakBeyondPrice, b.High)
                                       : Math.Min(e.PeakBeyondPrice, b.Low);
                bool newPeak = Math.Abs(peakBeyond - e.PeakBeyondPrice) > 1e-9;
                if (newPeak) { e.PeakBeyondPrice = peakBeyond; e.TroughAfterPeak = peakBeyond; }
                double trough = up ? Math.Min(e.TroughAfterPeak, b.Low)
                                   : Math.Max(e.TroughAfterPeak, b.High);
                e.TroughAfterPeak = trough;

                if (!e.Retested && !double.IsNaN(atr) && atr > 0)
                {
                    bool back = up ? b.Low <= lvl + RetestBandAtr * atr
                                   : b.High >= lvl - RetestBandAtr * atr;
                    // only counts as a retest once price has actually left the level
                    bool wentAway = up ? e.PeakBeyondPrice > lvl + RetestBandAtr * atr
                                       : e.PeakBeyondPrice < lvl - RetestBandAtr * atr;
                    if (back && wentAway)
                    {
                        e.Retested = true;
                        e.MinutesToRetest = mins;
                        double impulse = up ? e.PeakBeyondPrice - lvl : lvl - e.PeakBeyondPrice;
                        double give = up ? e.PeakBeyondPrice - e.TroughAfterPeak
                                         : e.TroughAfterPeak - e.PeakBeyondPrice;
                        e.RetestDepthPct = impulse > 0 ? 100.0 * give / impulse : double.NaN;
                        e.RetestClosedBack = up ? b.Close < lvl : b.Close > lvl;
                    }
                }

                // ---- acceptance: how much of the next hour closed beyond -----
                bool closeBeyond = up ? b.Close > lvl : b.Close < lvl;
                if (mins <= 30 && closeBeyond) e.ClosesBeyondFirst30++;
                if (mins <= 60 && closeBeyond) e.ClosesBeyondFirst60++;

                // ---- failure and reversal ------------------------------------
                double fb = double.IsNaN(atr) || atr <= 0 ? 0 : FailBufferAtr * atr;
                bool back2 = up ? b.Close < lvl - fb : b.Close > lvl + fb;
                if (back2)
                {
                    e.ClosedBackOnce = true;
                    if (!e.FailedBreak) { e.FailedBreak = true; e.MinutesToFail = mins; }
                }
                if (!e.Reversal && !double.IsNaN(atr) && atr > 0)
                {
                    double against = up ? lvl - b.Low : b.High - lvl;
                    if (against >= ReversalAtr * atr) { e.Reversal = true; e.MinutesToReversal = mins; }
                }

                // ---- volatility expansion after the break --------------------
                if (mins <= 30 && !double.IsNaN(prev1mClose))
                {
                    double tr = b.High - b.Low;
                    e.Tr1mSumNext30 += tr; e.Tr1mCountNext30++;
                }

                // ---- R race against the structural swing stop ----------------
                double sl = e.StopSwingPts;
                if (!double.IsNaN(sl) && sl > 0)
                {
                    if (e.MinutesToStop < 0)
                    {
                        bool hit = up ? b.Low <= e.Close - sl : b.High >= e.Close + sl;
                        if (hit) e.MinutesToStop = mins;
                    }
                    for (int g = 0; g < RGrid.Length; g++)
                        if (e.MinutesToR[g] < 0)
                        {
                            bool hit = up ? b.High >= e.Close + RGrid[g] * sl
                                          : b.Low <= e.Close - RGrid[g] * sl;
                            if (hit) e.MinutesToR[g] = mins;
                        }
                }

                // ---- entry probes --------------------------------------------
                for (int k = 0; k < e.Probes.Count; k++)
                {
                    V4EntryProbe p = e.Probes[k];
                    if (p.State != V4ProbeState.TRIGGERED) continue;
                    if (b.EtClose <= p.EntryEt) continue;
                    p.MinutesObserved = (int)(b.EtClose - p.EntryEt).TotalMinutes;
                    double pf = up ? b.High - p.EntryPrice : p.EntryPrice - b.Low;
                    double pa = up ? p.EntryPrice - b.Low : b.High - p.EntryPrice;
                    if (pf > p.RunMfePts) p.RunMfePts = pf;
                    if (pa > p.RunMaePts) p.RunMaePts = pa;
                    for (int h = 0; h < HorizonMinutes.Length; h++)
                        if (p.MinutesObserved == HorizonMinutes[h])
                            p.NetAtMin[h] = up ? b.Close - p.EntryPrice : p.EntryPrice - b.Close;
                    if (!double.IsNaN(p.StopPts) && p.StopPts > 0)
                    {
                        if (p.MinutesToStop < 0)
                        {
                            bool hit = up ? b.Low <= p.StopPrice : b.High >= p.StopPrice;
                            if (hit) p.MinutesToStop = p.MinutesObserved;
                        }
                        for (int g = 0; g < RGrid.Length; g++)
                            if (p.MinutesToR[g] < 0)
                            {
                                bool hit = up ? b.High >= p.EntryPrice + RGrid[g] * p.StopPts
                                              : b.Low <= p.EntryPrice - RGrid[g] * p.StopPts;
                                if (hit) p.MinutesToR[g] = p.MinutesObserved;
                            }
                    }
                }

                if (mins >= MaxHorizonMinutes) { Resolve(e); e.Complete = true; }
            }
        }

        /// Turn the running measurements into the categorical follow state.
        /// Called once, when the horizon closes. Uses only label data.
        private void Resolve(V4Event e)
        {
            if (e.Tr1mCountNext30 > 0 && !double.IsNaN(e.Atr1mAtBreak) && e.Atr1mAtBreak > 0)
                e.VolExpansion = (e.Tr1mSumNext30 / e.Tr1mCountNext30) / e.Atr1mAtBreak;
            if (!double.IsNaN(e.TfAtr) && e.TfAtr > 0) e.ContMaxAtr = e.ContMaxPts / e.TfAtr;

            for (int i = 0; i < e.Probes.Count; i++)
                if (e.Probes[i].State == V4ProbeState.ARMED
                    || e.Probes[i].State == V4ProbeState.WAITING_RECLAIM)
                    e.Probes[i].State = V4ProbeState.EXPIRED;

            if (e.EventKind == "CONTROL") { e.Follow = V4FollowState.UNRESOLVED; return; }

            bool everBeyond = e.ClosesBeyondFirst60 > 0 || V4BreakClassifier.IsCloseThrough(e.Outcome);
            if (e.FailedBreak && e.MinutesToFail >= 0 && e.MinutesToFail <= 5)
                e.Follow = V4FollowState.IMMEDIATE_REJECTION;
            else if (e.FailedBreak && e.ClosesBeyondFirst60 < 30)
                e.Follow = V4FollowState.FAILED_BREAK;
            else if (e.Retested && e.RetestClosedBack)
                e.Follow = V4FollowState.RETEST_FAILED;
            else if (e.Retested && e.ClosesBeyondFirst60 >= 30)
                e.Follow = V4FollowState.ACCEPTED_RETEST_HELD;
            else if (!e.Retested && e.ClosesBeyondFirst60 >= 45)
                e.Follow = V4FollowState.ACCEPTED_NO_RETEST;
            else if (everBeyond)
                e.Follow = V4FollowState.DRIFT;
            else
                e.Follow = V4FollowState.UNRESOLVED;

            if (e.Follow == V4FollowState.FAILED_BREAK || e.Follow == V4FollowState.IMMEDIATE_REJECTION)
                failedBreakToday[e.Tf] = true;
        }

        private void FlushComplete()
        {
            for (int i = pending.Count - 1; i >= 0; i--)
            {
                V4Event e = pending[i];
                if (!e.Complete) continue;
                structureSink(StructureCsv(e));
                if (e.EventKind == "CONTROL") ControlsEmitted++; else BreaksEmitted++;
                if (EmitEntries && entrySink != null)
                    for (int k = 0; k < e.Probes.Count; k++)
                    { entrySink(EntryCsv(e, e.Probes[k])); EntryRowsEmitted++; }
                pending.RemoveAt(i);
            }
        }

        // ====================================================================
        // CSV
        // ====================================================================

        public static string StructureCsvHeader()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("eventId,symbol,eventKind,isWarmup,date,timeEt,tf,tfMinutes,barIndex,");
            sb.Append("side,levelName,levelPrice,levelFormedEt,levelKnownEt,levelAgeMin,priorSwingLabel,");
            sb.Append("outcome,penetrationPts,penetrationAtr,closeBeyondPts,closeBeyondAtr,");
            sb.Append("open,high,low,close,volume,bodyPts,bodyAtr,barRangePts,barRangeAtr,relVolume,");
            sb.Append("tfAtr,tfCompression,tfExpansion,tfRangePts,tfPosInRange,");
            for (int i = 0; i < TfOrder.Length; i++) sb.Append("struct_").Append(TfOrder[i]).Append(',');
            for (int i = 0; i < TfOrder.Length; i++) sb.Append("minsInState_").Append(TfOrder[i]).Append(',');
            sb.Append("alignState,alignAgree,alignOppose,alignNone,alignTransitioning,htfDir,");
            sb.Append("archA_4h60m15m,archB_60m15m,archC_15m1m,");
            sb.Append("locAsOfEt,distPdhAtr,distPdlAtr,distPwhAtr,distPwlAtr,");
            sb.Append("distSessHighAtr,distSessLowAtr,distSessOpenAtr,distVwapAtr,");
            sb.Append("nearestLevel,nearestLevelAtr,atLocation,");
            sb.Append("breaksTodayThisTf,priorFailedBreakThisTf,");
            sb.Append("stopSwingPts,stopBarPts,stopAtrPts,");
            for (int i = 0; i < HorizonMinutes.Length; i++)
            {
                string h = HorizonMinutes[i].ToString(CultureInfo.InvariantCulture);
                sb.Append("net_").Append(h).Append("m,mfe_").Append(h).Append("m,mae_").Append(h).Append("m,");
            }
            sb.Append("contMaxPts,contMaxAtr,");
            for (int i = 0; i < ContAtrGrid.Length; i++)
                sb.Append("minsToCont_").Append(ContAtrGrid[i].ToString("0.##", CultureInfo.InvariantCulture)).Append("atr,");
            sb.Append("retested,minsToRetest,retestDepthPct,retestClosedBack,");
            sb.Append("closesBeyondFirst30,closesBeyondFirst60,");
            sb.Append("failedBreak,minsToFail,reversal,minsToReversal,volExpansion,followState,");
            sb.Append("minsToStop,");
            for (int i = 0; i < RGrid.Length; i++)
                sb.Append("minsTo_").Append(RGrid[i].ToString("0.##", CultureInfo.InvariantCulture)).Append("R,");
            sb.Append("minutesObserved");
            return sb.ToString();
        }

        public static string EntryCsvHeader()
        {
            StringBuilder sb = new StringBuilder();
            sb.Append("eventId,symbol,eventTf,side,entryTf,trigger,probeState,");
            sb.Append("entryTimeEt,minsToEntry,entryPrice,stopPrice,stopPts,slipFromBreakClosePts,");
            for (int i = 0; i < HorizonMinutes.Length; i++)
                sb.Append("netR_").Append(HorizonMinutes[i].ToString(CultureInfo.InvariantCulture)).Append("m,");
            sb.Append("mfeR,maeR,minsToStop,");
            for (int i = 0; i < RGrid.Length; i++)
                sb.Append("minsTo_").Append(RGrid[i].ToString("0.##", CultureInfo.InvariantCulture)).Append("R,");
            sb.Append("minutesObserved");
            return sb.ToString();
        }

        private static string F(double v)
        {
            return double.IsNaN(v) || double.IsInfinity(v) ? "" : v.ToString("0.####", CultureInfo.InvariantCulture);
        }
        private static string B(bool v) { return v ? "TRUE" : "FALSE"; }
        private static string T(DateTime d)
        {
            return d == DateTime.MinValue || d == DateTime.MaxValue
                ? "" : d.ToString("yyyy-MM-dd HH:mm:ss", CultureInfo.InvariantCulture);
        }

        public static string StructureCsv(V4Event e)
        {
            CultureInfo ci = CultureInfo.InvariantCulture;
            StringBuilder sb = new StringBuilder(1200);
            sb.Append(e.EventId).Append(',').Append(e.Symbol).Append(',').Append(e.EventKind).Append(',')
              .Append(B(e.IsWarmup)).Append(',')
              .Append(e.EtClose.ToString("yyyy-MM-dd", ci)).Append(',')
              .Append(e.EtClose.ToString("HH:mm:ss", ci)).Append(',')
              .Append(e.Tf).Append(',').Append(e.TfMinutes).Append(',').Append(e.BarIndex).Append(',');
            sb.Append(e.Dir > 0 ? "UP" : "DOWN").Append(',').Append(e.LevelName).Append(',')
              .Append(F(e.LevelPrice)).Append(',').Append(T(e.LevelFormedEt)).Append(',')
              .Append(T(e.LevelKnownEt)).Append(',').Append(e.LevelAgeMinutes).Append(',')
              .Append(e.PriorSwingLabel).Append(',');
            sb.Append(e.Outcome).Append(',').Append(F(e.PenetrationPts)).Append(',')
              .Append(F(e.PenetrationAtr)).Append(',').Append(F(e.CloseBeyondPts)).Append(',')
              .Append(F(e.CloseBeyondAtr)).Append(',');
            sb.Append(F(e.Open)).Append(',').Append(F(e.High)).Append(',').Append(F(e.Low)).Append(',')
              .Append(F(e.Close)).Append(',').Append(F(e.Volume)).Append(',')
              .Append(F(e.BodyPts)).Append(',').Append(F(e.BodyAtr)).Append(',')
              .Append(F(e.BarRangePts)).Append(',').Append(F(e.BarRangeAtr)).Append(',')
              .Append(F(e.RelVolume)).Append(',');
            sb.Append(F(e.TfAtr)).Append(',').Append(F(e.TfCompression)).Append(',')
              .Append(F(e.TfExpansion)).Append(',').Append(F(e.TfRangePts)).Append(',')
              .Append(F(e.TfPosInRange)).Append(',');
            for (int i = 0; i < e.States.Length; i++) sb.Append(e.States[i]).Append(',');
            for (int i = 0; i < e.MinutesInState.Length; i++) sb.Append(e.MinutesInState[i]).Append(',');
            sb.Append(e.Alignment).Append(',').Append(e.AlignAgree).Append(',').Append(e.AlignOppose).Append(',')
              .Append(e.AlignNone).Append(',').Append(e.AlignTransitioning).Append(',').Append(e.HtfDir).Append(',');
            sb.Append(B(e.ArchA)).Append(',').Append(B(e.ArchB)).Append(',').Append(B(e.ArchC)).Append(',');
            sb.Append(T(e.LocAsOfEt)).Append(',').Append(F(e.DistPdhAtr)).Append(',').Append(F(e.DistPdlAtr)).Append(',')
              .Append(F(e.DistPwhAtr)).Append(',').Append(F(e.DistPwlAtr)).Append(',')
              .Append(F(e.DistSessHighAtr)).Append(',').Append(F(e.DistSessLowAtr)).Append(',')
              .Append(F(e.DistSessOpenAtr)).Append(',').Append(F(e.DistVwapAtr)).Append(',')
              .Append(e.NearestLevel).Append(',').Append(F(e.NearestLevelAtr)).Append(',')
              .Append(B(e.AtLocation)).Append(',');
            sb.Append(e.BreaksTodayThisTf).Append(',').Append(B(e.PriorFailedBreakThisTf)).Append(',');
            sb.Append(F(e.StopSwingPts)).Append(',').Append(F(e.StopBarPts)).Append(',')
              .Append(F(e.StopAtrPts)).Append(',');
            for (int i = 0; i < HorizonMinutes.Length; i++)
                sb.Append(F(e.NetAtMin[i])).Append(',').Append(F(e.MfeAtMin[i])).Append(',')
                  .Append(F(e.MaeAtMin[i])).Append(',');
            sb.Append(F(e.ContMaxPts)).Append(',').Append(F(e.ContMaxAtr)).Append(',');
            for (int i = 0; i < e.MinutesToCont.Length; i++) sb.Append(e.MinutesToCont[i]).Append(',');
            sb.Append(B(e.Retested)).Append(',').Append(e.MinutesToRetest).Append(',')
              .Append(F(e.RetestDepthPct)).Append(',').Append(B(e.RetestClosedBack)).Append(',');
            sb.Append(e.ClosesBeyondFirst30).Append(',').Append(e.ClosesBeyondFirst60).Append(',');
            sb.Append(B(e.FailedBreak)).Append(',').Append(e.MinutesToFail).Append(',')
              .Append(B(e.Reversal)).Append(',').Append(e.MinutesToReversal).Append(',')
              .Append(F(e.VolExpansion)).Append(',').Append(e.Follow).Append(',');
            sb.Append(e.MinutesToStop).Append(',');
            for (int i = 0; i < e.MinutesToR.Length; i++) sb.Append(e.MinutesToR[i]).Append(',');
            sb.Append(e.MinutesObserved);
            return sb.ToString();
        }

        public static string EntryCsv(V4Event e, V4EntryProbe p)
        {
            StringBuilder sb = new StringBuilder(400);
            sb.Append(e.EventId).Append(',').Append(e.Symbol).Append(',').Append(e.Tf).Append(',')
              .Append(e.Dir > 0 ? "UP" : "DOWN").Append(',')
              .Append(p.EntryTf).Append(',').Append(p.Trigger).Append(',').Append(p.State).Append(',');
            sb.Append(T(p.EntryEt)).Append(',').Append(p.MinutesToEntry).Append(',')
              .Append(F(p.EntryPrice)).Append(',').Append(F(p.StopPrice)).Append(',')
              .Append(F(p.StopPts)).Append(',');
            double slip = double.IsNaN(p.EntryPrice) ? double.NaN
                : (e.Dir > 0 ? p.EntryPrice - e.Close : e.Close - p.EntryPrice);
            sb.Append(F(slip)).Append(',');
            bool haveR = !double.IsNaN(p.StopPts) && p.StopPts > 0;
            for (int i = 0; i < HorizonMinutes.Length; i++)
                sb.Append(haveR ? F(p.NetAtMin[i] / p.StopPts) : "").Append(',');
            sb.Append(haveR ? F(p.RunMfePts / p.StopPts) : "").Append(',')
              .Append(haveR ? F(p.RunMaePts / p.StopPts) : "").Append(',')
              .Append(p.MinutesToStop).Append(',');
            for (int i = 0; i < p.MinutesToR.Length; i++) sb.Append(p.MinutesToR[i]).Append(',');
            sb.Append(p.MinutesObserved);
            return sb.ToString();
        }
    }
}
