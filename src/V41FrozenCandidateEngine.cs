// ======================================================================
// V41FrozenCandidateEngine.cs  -  MNQ V4.1 prospective shelf
// ======================================================================
// PURE, NT-FREE, STREAMING port of the CANONICAL FROZEN candidate rules
// in analysis/v41/cand_spec.py (source hash 9bea8f1cafc2b6ea, frozen
// 2026-08-21) and the frozen management in analysis/v41/prospective.py.
//
// THIS FILE SUBMITS NO ORDERS.
//
// Candidates (separate lineages, never combined, never mutually gated):
//   OFH13_PROSPECTIVE_V1  entry = frozen OFH13; mgmt = 1.5 ATR stop,
//                         no target, 60m time exit          (PRIMARY)
//   OFH14_PROSPECTIVE_V1  entry = frozen OFH14; mgmt = STRUCT stop
//                         (FVG far boundary), 60m time exit (SECONDARY)
//   G4_PROSPECTIVE_V1     SIGNAL ONLY - no stop is invented for it
//   G3_PROSPECTIVE_V1     SIGNAL ONLY - no stop is invented for it
//   G1                    execution DIAGNOSTIC arm only, logged per
//                         parent event of OFH13/G4/OFH14. Never primary,
//                         never changes qualification.
//
// EVERY documented spec!=code discrepancy of the frozen Python is
// PRESERVED here, not fixed (see docs/PROSPECTIVE_REGISTRY.md D1-D7):
//   D1 entry eligibility does NOT require >=30 min after RTH open
//   D3 OFH13/14 mitigation expires at SIGNAL time + 30 min
//   D4 G4 entry price is the trigger-bar close (market entry)
//   D5 G1 R/ATR reference is the SIGNAL bar ATR
//   D6 G3 R is 1.0 x ATR of the entry bar
//
// FORWARD-ELIGIBILITY QUIRK (Q-FWD), stated openly: the frozen Python
// population filters require that the 60 minutes after an entry (90
// after an OFH6 signal) exist as consecutive bars. That is a POPULATION
// filter using the future, not entry information. A causal engine
// cannot know it at decision time, so events are emitted immediately
// with FwdResolved=false and finalized when the future bar arrives
// (Eligible=true when tmin+60 lands exactly 60 bars later; false
// otherwise). Divergence from the batch Python is possible ONLY when an
// intraday data gap occurs inside such a window; every such case is
// flagged, counted and reported by the parity comparator rather than
// hidden. The same applies to signals (+90) and their downstream
// effects.
//
// THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
// ======================================================================
using System;
using System.Collections.Generic;
using System.Globalization;

namespace NinjaTrader.NinjaScript.Strategies.MnqV4
{
    public static class V41Frozen
    {
        // ---- constants transcribed from cand_spec.py (frozen) ----------
        public const double Tick = 0.25;
        public const double CostPts = 0.87;
        public const int HorizonMin = 60;
        public const int LifeMin = 30;
        public const int CooldownMin = 30;
        public const double Ofh6Threshold = 3380.0;
        public const int Ofh6Lookback = 15;
        public const int Ofh6MinAfterOpen = 30;
        public const int Ofh6MinToClose = 90;
        public const double QBd75 = 511.0;
        public const double DispAtr = 1.00;
        public const double DispBody = 0.50;
        public const double DispClr = 0.70;
        public const double G1DepthAtr = 0.5;
        public const int G3DelayMin = 20;
        public const double G4TrendAtr = 0.5;
        public const int G4WindowBars = 3;
        public const string FreezeDataEnd = "2026-08-19";
        public const string EngineVersion = "V41-PROSPECTIVE-ENGINE-1.0";
        // sha256[:16] of the frozen Python sources (FROZEN_HASHES.txt)
        public const string HashCandSpec = "9bea8f1cafc2b6ea";
        public const string HashOfh6Spec = "e8145b7c493029de";
        public const string HashOfhtSpec = "272d7bca6402b6d2";
        public const string HashOfhtCache = "376ce829086b5224";
    }

    /// One completed 1m input bar with the features the frozen rules use.
    public class V41InBar
    {
        public DateTime EtClose;
        public long Tmin;               // FROZEN non-calendar minute index (see TminOf)
        public double Open, High, Low, Close;
        public double BarDelta;         // ask-bid, recomputed from levels
        public bool HasDelta;
        public double Atr;              // V4Atr(20) value, NaN until ready
        public bool IsRth;
        public int MinFromRthOpen;      // -1 when unknown
        public int MinToRthClose;

        public static long TminOf(DateTime et)
        {
            // DISCREPANCY D8 (preserved, not fixed): the frozen Python tmin
            // (cand_spec.py line 130) treats every month as 44640 minutes
            // (31 days) but a year as 527040 minutes (366 days), so the index
            // is NON-MONOTONIC across the year boundary: Jan 1-5 of a new
            // year index BELOW late December of the old year (Jan 6 00:00
            // == Dec 31 00:00). Consequence: the OFH6 30-min cooldown after
            // a late-December signal suppresses all early-January signals
            // (verified: 2025-12-30 10:59 suppresses 2026-01-02 10:00/10:41/
            // 11:12/11:52 and 2026-01-05 10:45 in the canonical Python).
            // A true minutes-since-epoch Tmin here produced exactly those 5
            // extra signals and broke parity. THE ACTUAL FROZEN CODE WINS:
            // replicate the frozen arithmetic verbatim.
            return et.Year * 527040L + et.Month * 44640L + et.Day * 1440L
                 + et.Hour * 60L + et.Minute;
        }
    }

    public class V41Event
    {
        public string Cand;             // OFH13 / OFH14 / G4 / G3 / G1
        public string Id;
        public DateTime Et;             // entry bar close (ET)
        public long Tmin;
        public int EntryIdx;
        public int Dir;
        public double EntryPx;
        public double R;                // frozen structural R of the lineage
        public double Atr;              // ATR at entry bar
        public DateTime ParentEt;       // OFH6 signal ET (G4: attack bar ET)
        public double ZLo = double.NaN, ZHi = double.NaN, Mid = double.NaN;
        public double Depth = double.NaN;   // OFH13/14 penetration at trigger
        public bool Flow;                   // OFH13/14 opposing-flow flag
        public string Reason = "";
        // Q-FWD finalization
        public bool FwdResolved;
        public bool Eligible;           // meaningful once FwdResolved
        public bool ParentSignalDivergent;  // parent signal failed fwd-90
    }

    /// OFH6 signal record (context + parent bookkeeping).
    public class V41Signal
    {
        public int Idx;
        public long Tmin;
        public DateTime Et;
        public int Dir;
        public double Atr;
        public double ClosePx;
        public bool FwdResolved;        // +90 consecutive check
        public bool Eligible;
    }

    public class V41FrozenCandidateEngine
    {
        public readonly List<V41InBar> Bars = new List<V41InBar>();
        public readonly List<V41Signal> Signals = new List<V41Signal>();
        public readonly List<V41Event> Events = new List<V41Event>();
        // events/signals awaiting fwd resolution, and counters
        public long FwdDivergentEvents, FwdDivergentSignals;

        private readonly List<long> sigTminLong = new List<long>();
        private readonly List<long> sigTminShort = new List<long>();
        private readonly Dictionary<string, long> lastEmit =
            new Dictionary<string, long>();     // cooldown per candidate
        private long lastSigTmin = -1000000000L;   // NOT long.MinValue: subtraction must not overflow
        private double dsumAcc;                 // running 15-bar delta sum
        private readonly Queue<double> dsumQ = new Queue<double>();

        // pendings -----------------------------------------------------
        private class PendG1 { public V41Signal S; public double Lim; public long NextTmin; public bool Dead; }
        private class PendG3 { public V41Signal S; public long NextTmin; public int Left; public bool Dead; }
        private class PendG4
        {
            public int AttackIdx; public long AttackTmin; public DateTime AttackEt;
            public int Dir; public double AtkHigh, AtkLow; public long NextTmin;
            public int Left; public bool Dead;
        }
        private class PendFvg
        {
            public V41Signal S; public long NextTmin; public bool Dead;
            public int Phase;           // 0 = FVG search, 1 = mitigation
            public double ZLo, ZHi, Mid, FvgAtr; public int FvgIdx;
            public bool Touched, Flow; public double Ext;
        }
        private readonly List<PendG1> pG1 = new List<PendG1>();
        private readonly List<PendG3> pG3 = new List<PendG3>();
        private readonly List<PendG4> pG4 = new List<PendG4>();
        private readonly List<PendFvg> pFvg = new List<PendFvg>();
        private readonly List<V41Event> unresolved = new List<V41Event>();
        private readonly List<V41Signal> unresolvedSig = new List<V41Signal>();

        public delegate void EventHandler2(V41Event e);
        public event EventHandler2 OnEventFinalized;   // fired when Eligible known

        private static bool Ok(double v) { return !double.IsNaN(v) && !double.IsInfinity(v); }

        // entry eligibility, CAUSAL part only (discrepancy D1 preserved:
        // no >=30-min-after-open requirement here).
        private bool EntryOkCausal(V41InBar b)
        {
            if (!b.IsRth || !Ok(b.Atr) || b.Atr <= 0) return false;
            if (b.MinToRthClose < V41Frozen.HorizonMin) return false;
            return true;
        }

        private static string CleanEt(DateTime et)
        {
            return et.ToString("yyyyMMddHHmmss", CultureInfo.InvariantCulture);
        }

        private bool OppositeIn(int dir, long tsExclusive, long teInclusive)
        {
            List<long> lst = dir > 0 ? sigTminShort : sigTminLong;
            // first opposite signal with t > tsExclusive and t <= teInclusive
            int lo = 0, hi = lst.Count;
            while (lo < hi) { int mid = (lo + hi) / 2; if (lst[mid] <= tsExclusive) lo = mid + 1; else hi = mid; }
            return lo < lst.Count && lst[lo] <= teInclusive;
        }

        private bool CtxOkAt(int dir, long te)
        {
            List<long> lst = dir > 0 ? sigTminLong : sigTminShort;
            int lo = 0, hi = lst.Count;
            while (lo < hi) { int mid = (lo + hi) / 2; if (lst[mid] <= te) lo = mid + 1; else hi = mid; }
            if (lo == 0) return false;
            long ts = lst[lo - 1];
            if (te - ts > V41Frozen.LifeMin) return false;
            return !OppositeIn(dir, ts, te);
        }

        private void Emit(string cand, int j, int dir, double px, double R,
                          V41Signal parent, DateTime parentEt, string reason,
                          double zLo, double zHi, double mid, double depth, bool flow)
        {
            V41InBar b = Bars[j];
            if (!EntryOkCausal(b)) return;
            if (!Ok(R) || R <= 0) return;
            bool percand = cand != "G1" && cand != "G3";
            if (percand)
            {
                long last;
                if (lastEmit.TryGetValue(cand, out last) && b.Tmin - last < V41Frozen.CooldownMin)
                    return;
                lastEmit[cand] = b.Tmin;
            }
            V41Event e = new V41Event();
            e.Cand = cand; e.Et = b.EtClose; e.Tmin = b.Tmin; e.EntryIdx = j;
            e.Dir = dir; e.EntryPx = px; e.R = R; e.Atr = b.Atr;
            e.ParentEt = parentEt; e.Reason = reason;
            e.ZLo = zLo; e.ZHi = zHi; e.Mid = mid; e.Depth = depth; e.Flow = flow;
            e.Id = cand + "-" + CleanEt(b.EtClose) + "-" + (dir > 0 ? "+1" : "-1");
            if (parent != null && parent.FwdResolved && !parent.Eligible)
                e.ParentSignalDivergent = true;
            Events.Add(e);
            unresolved.Add(e);
        }

        /// Feed ONE completed 1m bar. Order inside the bar (documented):
        ///   1. resolve fwd-eligibility of old events/signals
        ///   2. detect a NEW OFH6 signal on this bar (so a same-bar
        ///      opposite signal voids fills, matching batch semantics)
        ///   3. advance pendings created on EARLIER bars
        ///   4. detect a new G4 attack / spawn pendings for a new signal
        public void OnBar(V41InBar b)
        {
            b.Tmin = V41InBar.TminOf(b.EtClose);
            Bars.Add(b);
            int j = Bars.Count - 1;

            ResolveForward(j);

            // ---- rolling 15-bar delta sum (consecutive minutes only) ---
            bool consec15 = j >= V41Frozen.Ofh6Lookback
                && Bars[j].Tmin - Bars[j - V41Frozen.Ofh6Lookback].Tmin == V41Frozen.Ofh6Lookback;
            double dsum = double.NaN;
            if (consec15)
            {
                bool all = true; double s = 0;
                for (int k = j - V41Frozen.Ofh6Lookback + 1; k <= j; k++)
                {
                    if (!Bars[k].HasDelta) { all = false; break; }
                    s += Bars[k].BarDelta;
                }
                if (all) dsum = s;
            }

            // ---- 2. OFH6 signal detection ------------------------------
            V41Signal newSig = null;
            if (Ok(dsum) && b.IsRth && Ok(b.Atr) && b.Atr > 0
                && b.MinFromRthOpen >= V41Frozen.Ofh6MinAfterOpen
                && b.MinToRthClose >= V41Frozen.Ofh6MinToClose
                && Math.Abs(dsum) >= V41Frozen.Ofh6Threshold
                && b.Tmin - lastSigTmin >= V41Frozen.CooldownMin)
            {
                lastSigTmin = b.Tmin;
                newSig = new V41Signal();
                newSig.Idx = j; newSig.Tmin = b.Tmin; newSig.Et = b.EtClose;
                newSig.Dir = dsum > 0 ? 1 : -1; newSig.Atr = b.Atr; newSig.ClosePx = b.Close;
                Signals.Add(newSig);
                unresolvedSig.Add(newSig);
                (newSig.Dir > 0 ? sigTminLong : sigTminShort).Add(b.Tmin);
            }

            // ---- 3. advance pendings (skip ones created this bar) ------
            AdvanceG1(j, b);
            AdvanceG3(j, b);
            AdvanceG4(j, b);
            AdvanceFvg(j, b);

            // ---- 4. spawn pendings for the new signal ------------------
            if (newSig != null && EntryOkCausal(b))
            {
                PendG1 g1 = new PendG1();
                g1.S = newSig; g1.NextTmin = b.Tmin + 1;
                g1.Lim = b.Close - newSig.Dir * V41Frozen.G1DepthAtr * b.Atr;
                pG1.Add(g1);
                PendG3 g3 = new PendG3();
                g3.S = newSig; g3.NextTmin = b.Tmin + 1; g3.Left = V41Frozen.G3DelayMin;
                pG3.Add(g3);
            }
            if (newSig != null)
            {
                PendFvg pf = new PendFvg();
                pf.S = newSig; pf.NextTmin = b.Tmin + 1; pf.Phase = 0;
                pFvg.Add(pf);
            }

            // ---- G4 attack detection on THIS bar -----------------------
            DetectG4Attack(j, b);
        }

        private void AdvanceG1(int j, V41InBar b)
        {
            for (int i = pG1.Count - 1; i >= 0; i--)
            {
                PendG1 p = pG1[i];
                if (p.S.Idx == j) continue;                    // created now
                if (b.Tmin != p.NextTmin) { pG1.RemoveAt(i); continue; }  // gap
                p.NextTmin++;
                if (b.Tmin - p.S.Tmin > V41Frozen.LifeMin) { pG1.RemoveAt(i); continue; }
                if (OppositeIn(p.S.Dir, p.S.Tmin, b.Tmin)) { pG1.RemoveAt(i); continue; }
                bool touch = p.S.Dir > 0 ? b.Low <= p.Lim : b.High >= p.Lim;
                if (touch)
                {
                    // D5: R = ATR of the SIGNAL bar
                    Emit("G1", j, p.S.Dir, p.Lim, p.S.Atr, p.S, p.S.Et,
                         "G1 limit touched", double.NaN, double.NaN, double.NaN,
                         double.NaN, false);
                    pG1.RemoveAt(i);
                }
            }
        }

        private void AdvanceG3(int j, V41InBar b)
        {
            for (int i = pG3.Count - 1; i >= 0; i--)
            {
                PendG3 p = pG3[i];
                if (p.S.Idx == j) continue;
                if (b.Tmin != p.NextTmin) { pG3.RemoveAt(i); continue; }
                p.NextTmin++; p.Left--;
                if (p.Left > 0) continue;
                // exactly signal + 20 consecutive minutes
                if (!OppositeIn(p.S.Dir, p.S.Tmin, b.Tmin))
                {
                    bool adverse = p.S.Dir > 0 ? b.Close < p.S.ClosePx : b.Close > p.S.ClosePx;
                    if (adverse)
                        Emit("G3", j, p.S.Dir, b.Close, b.Atr, p.S, p.S.Et,   // D6
                             "G3 still discounted at +20m", double.NaN, double.NaN,
                             double.NaN, double.NaN, false);
                }
                pG3.RemoveAt(i);
            }
        }

        private void DetectG4Attack(int j, V41InBar b)
        {
            if (!EntryOkCausal(b)) return;
            if (j < 5 || Bars[j].Tmin - Bars[j - 5].Tmin != 5) return;
            double disp5 = b.Close - Bars[j - 5].Close;
            if (Math.Abs(disp5) < V41Frozen.G4TrendAtr * b.Atr) return;
            int t = disp5 > 0 ? 1 : -1;
            if (!b.HasDelta) return;
            double bd = b.BarDelta;
            if (bd * t >= 0 || Math.Abs(bd) < V41Frozen.QBd75) return;
            if (!CtxOkAt(t, b.Tmin)) return;
            PendG4 p = new PendG4();
            p.AttackIdx = j; p.AttackTmin = b.Tmin; p.AttackEt = b.EtClose;
            p.Dir = t; p.AtkHigh = b.High; p.AtkLow = b.Low;
            p.NextTmin = b.Tmin + 1; p.Left = V41Frozen.G4WindowBars;
            pG4.Add(p);
        }

        private void AdvanceG4(int j, V41InBar b)
        {
            for (int i = pG4.Count - 1; i >= 0; i--)
            {
                PendG4 p = pG4[i];
                if (p.AttackIdx == j) continue;
                if (b.Tmin != p.NextTmin) { pG4.RemoveAt(i); continue; }
                p.NextTmin++; p.Left--;
                // batch order preserved: adverse break checked FIRST, so a
                // bar breaking both sides kills the pending, never enters.
                bool adverse = p.Dir > 0 ? b.Low < p.AtkLow : b.High > p.AtkHigh;
                if (adverse) { pG4.RemoveAt(i); continue; }
                bool favor = p.Dir > 0 ? b.High > p.AtkHigh : b.Low < p.AtkLow;
                if (favor)
                {
                    double refPx = p.Dir > 0 ? p.AtkLow : p.AtkHigh;      // D4
                    double R = p.Dir > 0 ? b.Close - (refPx - V41Frozen.Tick)
                                         : (refPx + V41Frozen.Tick) - b.Close;
                    Emit("G4", j, p.Dir, b.Close, R, null, p.AttackEt,
                         "G4 attack failed, trend resumed",
                         double.NaN, double.NaN, double.NaN, double.NaN, false);
                    pG4.RemoveAt(i);
                    continue;
                }
                if (p.Left <= 0) pG4.RemoveAt(i);
            }
        }

        private void AdvanceFvg(int j, V41InBar b)
        {
            for (int i = pFvg.Count - 1; i >= 0; i--)
            {
                PendFvg p = pFvg[i];
                if (p.S.Idx == j) continue;
                if (b.Tmin != p.NextTmin) { pFvg.RemoveAt(i); continue; }
                p.NextTmin++;
                if (b.Tmin - p.S.Tmin > V41Frozen.LifeMin) { pFvg.RemoveAt(i); continue; }  // D3
                int d = p.S.Dir;
                if (p.Phase == 0)
                {
                    // displacement FVG completed at THIS bar, aligned with d
                    double zLo, zHi, fvgAtr;
                    if (TryFvgAt(j, d, out zLo, out zHi, out fvgAtr))
                    {
                        p.Phase = 1; p.ZLo = zLo; p.ZHi = zHi;
                        p.Mid = (zLo + zHi) / 2.0; p.FvgAtr = fvgAtr; p.FvgIdx = j;
                        p.Touched = false; p.Flow = false;
                        // first-FVG rule: this parent is now bound to this FVG
                    }
                    continue;
                }
                // ---- mitigation phase (verbatim _mitigate port) --------
                double far = d > 0 ? p.ZLo : p.ZHi;
                bool violated = d > 0 ? b.Close < p.ZLo : b.Close > p.ZHi;
                if (violated) { pFvg.RemoveAt(i); continue; }
                if (!p.Touched)
                {
                    bool touch = d > 0 ? b.Low <= p.ZHi : b.High >= p.ZLo;
                    if (touch) { p.Touched = true; p.Ext = d > 0 ? b.Low : b.High; }
                }
                else
                {
                    double x = d > 0 ? b.Low : b.High;
                    if (d > 0 ? x < p.Ext : x > p.Ext) p.Ext = x;
                }
                if (!p.Touched) continue;
                if (b.HasDelta && Math.Abs(b.BarDelta) >= V41Frozen.QBd75
                    && b.BarDelta * d < 0)
                    p.Flow = true;
                bool trig = d > 0 ? b.Close > p.Mid : b.Close < p.Mid;
                if (!trig) continue;
                double span = p.ZHi - p.ZLo;
                double depth = d > 0 ? (p.ZHi - p.Ext) / span : (p.Ext - p.ZLo) / span;
                if (!OppositeIn(d, p.S.Tmin, b.Tmin))
                {
                    double R = d > 0 ? b.Close - (far - V41Frozen.Tick)
                                     : (far + V41Frozen.Tick) - b.Close;
                    Emit("OFH14", j, d, b.Close, R, p.S, p.S.Et,
                         "FVG mitigated, close beyond midpoint",
                         p.ZLo, p.ZHi, p.Mid, depth, p.Flow);
                    if (p.Flow && depth < 1.0)
                        Emit("OFH13", j, d, b.Close, R, p.S, p.S.Et,
                             "FVG mitigated + opposing-flow failure",
                             p.ZLo, p.ZHi, p.Mid, depth, p.Flow);
                }
                pFvg.RemoveAt(i);
            }
        }

        /// Displacement-qualified FVG completing at bar j, aligned with d.
        private bool TryFvgAt(int j, int d, out double zLo, out double zHi, out double fvgAtr)
        {
            zLo = zHi = fvgAtr = double.NaN;
            if (j < 2 || Bars[j].Tmin - Bars[j - 2].Tmin != 2) return false;
            V41InBar a = Bars[j - 2], c2 = Bars[j - 1], c3 = Bars[j];
            double atr = c2.Atr;
            if (!Ok(atr) || atr <= 0) return false;
            int fd; double lo, hi;
            if (a.High < c3.Low) { fd = 1; lo = a.High; hi = c3.Low; }
            else if (a.Low > c3.High) { fd = -1; lo = c3.High; hi = a.Low; }
            else return false;
            if (fd != d) return false;
            double rng = c2.High - c2.Low;
            if (rng <= 0) return false;
            double body = Math.Abs(c2.Close - c2.Open);
            double clr = (c2.Close - c2.Low) / rng;
            bool disp = rng >= V41Frozen.DispAtr * atr && body / rng >= V41Frozen.DispBody
                && ((fd > 0 && clr >= V41Frozen.DispClr && c3.Close > a.Open)
                    || (fd < 0 && clr <= 1.0 - V41Frozen.DispClr && c3.Close < a.Open));
            if (!disp) return false;
            zLo = lo; zHi = hi; fvgAtr = atr;
            return true;
        }

        // ---- Q-FWD finalization ------------------------------------------
        private void ResolveForward(int j)
        {
            long now = Bars[j].Tmin;
            for (int i = unresolved.Count - 1; i >= 0; i--)
            {
                V41Event e = unresolved[i];
                long want = e.Tmin + V41Frozen.HorizonMin;
                if (now == want)
                {
                    e.FwdResolved = true;
                    e.Eligible = (j - e.EntryIdx) == V41Frozen.HorizonMin;
                    if (!e.Eligible) FwdDivergentEvents++;
                }
                else if (now > want)
                {
                    e.FwdResolved = true; e.Eligible = false; FwdDivergentEvents++;
                }
                else continue;
                unresolved.RemoveAt(i);
                if (OnEventFinalized != null) OnEventFinalized(e);
            }
            for (int i = unresolvedSig.Count - 1; i >= 0; i--)
            {
                V41Signal s = unresolvedSig[i];
                long want = s.Tmin + 90;
                if (now == want)
                {
                    s.FwdResolved = true;
                    s.Eligible = (j - s.Idx) == 90;
                    if (!s.Eligible) FwdDivergentSignals++;
                }
                else if (now > want)
                {
                    s.FwdResolved = true; s.Eligible = false; FwdDivergentSignals++;
                }
                else continue;
                unresolvedSig.RemoveAt(i);
            }
        }

        /// End of data: anything still unresolved is ineligible in the
        /// frozen population (its forward window does not exist yet).
        public void FinishHistory()
        {
            for (int i = 0; i < unresolved.Count; i++)
            {
                unresolved[i].FwdResolved = true;
                unresolved[i].Eligible = false;
            }
            unresolved.Clear();
        }
    }

    // ==================================================================
    // FROZEN MANAGEMENT - verbatim port of prospective.score_one().
    // OFH13_PROSPECTIVE_V1: stop 1.5*ATR(entry bar), no target, 60m exit.
    // OFH14_PROSPECTIVE_V1: stop = frozen structural R, no target, 60m.
    // Management walks bars BY INDEX (gaps ignored) exactly as the frozen
    // scorer does. Time exit = close of the 60th bar after entry.
    // ==================================================================
    public class V41ManagedOutcome
    {
        public string ExitReason = "OPEN";      // STOP / TIME / AMBIGUOUS_STOP
        public double ExitPx = double.NaN, StopPts = double.NaN;
        public int HeldMin;
        public double NetPts = double.NaN, RRes = double.NaN;
        public double Mfe, Mae;
        public int Ff05, Ff1, Ff2;              // 0 unresolved 1 fav 2 adv 3 amb
    }

    public static class V41Management
    {
        public static double StopFor(string version, V41Event e)
        {
            if (version == "OFH13_PROSPECTIVE_V1") return 1.5 * e.Atr;
            if (version == "OFH14_PROSPECTIVE_V1") return e.R;
            return double.NaN;                   // G3/G4: SIGNAL ONLY
        }

        public static V41ManagedOutcome Score(List<V41InBar> bars, V41Event e, double stopPts)
        {
            V41ManagedOutcome o = new V41ManagedOutcome();
            o.StopPts = stopPts;
            int d = e.Dir; double px = e.EntryPx;
            bool hasStop = !double.IsNaN(stopPts) && stopPts > 0;
            double sp = hasStop ? px - d * stopPts : double.NaN;
            int M = V41Frozen.HorizonMin;
            int last = Math.Min(e.EntryIdx + M, bars.Count - 1);
            o.HeldMin = M;
            for (int k = 1; k <= M && e.EntryIdx + k < bars.Count; k++)
            {
                V41InBar c = bars[e.EntryIdx + k];
                double fav = d > 0 ? c.High - px : px - c.Low;
                double adv = d > 0 ? px - c.Low : c.High - px;
                if (fav > o.Mfe) o.Mfe = fav;
                if (adv > o.Mae) o.Mae = adv;
                if (hasStop)
                {
                    if (o.Ff05 == 0) o.Ff05 = Race(fav, adv, 0.5 * stopPts, stopPts);
                    if (o.Ff1 == 0) o.Ff1 = Race(fav, adv, 1.0 * stopPts, stopPts);
                    if (o.Ff2 == 0) o.Ff2 = Race(fav, adv, 2.0 * stopPts, stopPts);
                    bool hs = d > 0 ? c.Low <= sp : c.High >= sp;
                    if (hs)
                    {
                        o.ExitReason = "STOP"; o.ExitPx = sp; o.HeldMin = k;
                        break;
                    }
                }
            }
            if (double.IsNaN(o.ExitPx))
            {
                o.ExitReason = "TIME";
                o.ExitPx = bars[last].Close;
            }
            o.NetPts = (o.ExitPx - px) * d - V41Frozen.CostPts;
            if (hasStop) o.RRes = o.NetPts / stopPts;
            return o;
        }

        private static int Race(double fav, double adv, double favLvl, double advLvl)
        {
            bool hf = fav >= favLvl, ha = adv >= advLvl;
            if (hf && ha) return 3;
            if (hf) return 1;
            if (ha) return 2;
            return 0;
        }

        /// G1 diagnostic B-arm (registry: logged only, never primary).
        /// Verbatim port of prospective.g1_fill: limit at entry-bar close
        /// -/+ 0.5*ATR(entry bar), valid 30 consecutive minutes, every
        /// window bar must itself be entry-eligible; no chase.
        public static bool G1Fill(List<V41InBar> bars, V41Event e,
                                  out int fillIdx, out double fillPx, out string noFill)
        {
            fillIdx = -1; fillPx = double.NaN; noFill = "";
            int d = e.Dir;
            double lim = bars[e.EntryIdx].Close - d * V41Frozen.G1DepthAtr * e.Atr;
            for (int k = e.EntryIdx + 1; k <= e.EntryIdx + V41Frozen.LifeMin && k < bars.Count; k++)
            {
                if (bars[k].Tmin - bars[e.EntryIdx].Tmin != k - e.EntryIdx)
                { noFill = "WINDOW_END"; return false; }
                V41InBar c = bars[k];
                if (!c.IsRth || double.IsNaN(c.Atr) || c.Atr <= 0
                    || c.MinToRthClose < V41Frozen.HorizonMin)
                { noFill = "WINDOW_END"; return false; }
                bool touch = d > 0 ? c.Low <= lim : c.High >= lim;
                if (touch) { fillIdx = k; fillPx = lim; return true; }
            }
            noFill = "NO_FILL_IN_30MIN";
            return false;
        }
    }
}
