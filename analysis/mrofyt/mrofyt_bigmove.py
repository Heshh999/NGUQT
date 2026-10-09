#!/usr/bin/env python3
"""mrofyt_bigmove.py - MROF-YT-W3-BIGMOVE-1.0

MROF_YT_WAVE3_BIGMOVE_REGISTRATION.md turned into running code. Waves one
and two are UNTOUCHED: this module subclasses the pilot runner and uses
only its observation hooks. Every pattern is evaluated on the frozen
runner's own grid ticks and approach windows.

    G1  FLOW_SHOCK_GO     grid: delta z >= 3, response >= 4 ticks with it,
                                persistence 3 of 4            -> with flow
    G2  FLOW_SHOCK_FADE   grid: delta z >= 3, |response| <= 1  -> against
    G3  CONTROL_RUN       grid: control >= 2.0 two ticks running -> with
    L1  OPEN_BREAK        09:30-10:00 clean cross of an overnight/yday
                          level, held 5 s, flow with it         -> with
    L2  SWEEP_RECLAIM     range level crossed and reclaimed, opposing
                          flow flip                             -> back
    L3  VWAP_SNAPBACK     outside a VWAP band, flow back toward VWAP
    L4  BREAK_RETEST      retest of a held break from the far side fails
    D1  TREND_1030        10:30 ET: 15+ points from the cash open with
                          flow agreeing                         -> with

Path score (registration 2): target 100 ticks, stops 40/60/80 ticks,
1800 s limit, tie is a stop, mid-to-mid, no fill model. Scored on
sessions <= DEV_END only; later sessions are REFUSED unless --unblind.

    python3 mrofyt_bigmove.py "<capture folder>" --out w3.json
    python3 mrofyt_bigmove.py "<capture folder>" --both --out w3.json
                                              # real + placebo levels
    python3 mrofyt_bigmove.py "<capture folder>" --unblind --out w3.json
                                              # CHECKPOINT ONLY: reads and
                                              # permanently exposes the
                                              # validation sessions

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import array
import bisect
import collections
import json
import math
import os
import random
import sys
import zlib

import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W3_VERSION = 'MROF-YT-W3-BIGMOVE-1.0'
REGISTRATION = 'MROF_YT_WAVE3_BIGMOVE_REGISTRATION.md'
DEV_END = '20260918'                     # registration 8: last DEV session
EXPOSED_BY_W3 = 'EXPOSED_W3_BIGMOVE_CHECKPOINT'

PATTERNS = ('G1', 'G2', 'G3', 'L1', 'L2', 'L3', 'L4', 'D1')
PATTERN_NAMES = dict(G1='FLOW_SHOCK_GO', G2='FLOW_SHOCK_FADE',
                     G3='CONTROL_RUN', L1='OPEN_BREAK', L2='SWEEP_RECLAIM',
                     L3='VWAP_SNAPBACK', L4='BREAK_RETEST', D1='TREND_1030')
LEVEL_PATTERNS = ('L1', 'L2', 'L3', 'L4')

# registration 1: thresholds
Z_SHOCK = 3.0
GO_RESP_TICKS = 4.0
FADE_RESP_TICKS = 1.0
Z_CONTROL = 2.0
PERSIST_MIN = 3
Z_AGGR_LEVEL = 1.5
Z_OPP_FLIP = 1.0
RETEST_PROGRESS_MAX = 1.0
TREND_MOVE_POINTS = 15.0
TREND_SUBS_MIN = 4
OPEN_WINDOW = (9.5 * 3600, 10.0 * 3600)          # 09:30:00-09:59:59 ET
TREND_SOD = 10.5 * 3600                          # 10:30:00 ET
OPEN_LEVELS = ('OVERNIGHT_HIGH', 'OVERNIGHT_LOW', 'YDAY_HIGH', 'YDAY_LOW')
RANGE_LEVELS = ('YDAY_HIGH', 'YDAY_LOW', 'OVERNIGHT_HIGH', 'OVERNIGHT_LOW',
                'LWEEK_HIGH', 'LWEEK_LOW')

# registration 2: the path score
TARGET_TICKS = 100.0
STOPS_TICKS = (40.0, 60.0, 80.0)
LIMIT_S = 1800.0
HALF_TICK = SIG.TICK / 2.0                       # mids sit on half ticks

# registration 5: multiplicity
N_TESTS = len(PATTERNS) * len(STOPS_TICKS)
ALPHA = 0.05
MIN_EVENTS = 30

# registration 4: placebo (identical to wave two ARM-C)
PLACEBO_LO, PLACEBO_HI, PLACEBO_MIN_SEP = 6.0, 20.0, 3.0

CENSUS_FEATURES = ('z_delta', 'z_ofi', 'resp', 'z_bi3', 'z_n10')
POINT = 4.0                                      # ticks per point


# ---------------------------------------------------------------------
# the pattern functions: pure, on dicts, so the suite can pin them
# ---------------------------------------------------------------------
def g1_flow_shock_go(g):
    """g: grid record dict. Returns direction or 0."""
    s, z, r, agree = g.get('s'), g.get('z_delta_s'), g.get('resp'), \
        g.get('agree_s')
    if not s or z is None or r is None or agree is None:
        return 0
    if z >= Z_SHOCK and s * r >= GO_RESP_TICKS and agree >= PERSIST_MIN:
        return s
    return 0


def g2_flow_shock_fade(g):
    s, z, r = g.get('s'), g.get('z_delta_s'), g.get('resp')
    if not s or z is None or r is None:
        return 0
    if z >= Z_SHOCK and abs(r) <= FADE_RESP_TICKS:
        return -s
    return 0


def g3_control_run(g, prev):
    """prev: the previous grid record of the same instrument, or None."""
    s, c = g.get('s'), g.get('control_s')
    if not s or c is None or prev is None:
        return 0
    if prev.get('s') != s or prev.get('control_s') is None:
        return 0
    if c >= Z_CONTROL and prev['control_s'] >= Z_CONTROL:
        return s
    return 0


def l1_open_break(f, sod):
    if not (OPEN_WINDOW[0] <= sod < OPEN_WINDOW[1]):
        return 0
    if f.get('level_id') not in OPEN_LEVELS:
        return 0
    ad = f.get('ad')
    if not ad or not f.get('clean_cross') or not f.get('held_5s'):
        return 0
    if (f.get('persist_agree') or 0) < PERSIST_MIN:
        return 0
    if f.get('aggr_dir') != ad or f.get('aggr_z') is None or \
            f['aggr_z'] < Z_AGGR_LEVEL:
        return 0
    return ad


def l2_sweep_reclaim(f):
    if f.get('level_id') not in RANGE_LEVELS:
        return 0
    ad = f.get('ad')
    if not ad or not f.get('returned_through_level'):
        return 0
    z = f.get('opp_flip_z')
    if z is None or z < Z_OPP_FLIP:
        return 0
    return -ad


def l3_vwap_snapback(f):
    ad, lid = f.get('ad'), f.get('level_id')
    if not ((lid == 'VWAP_UPPER' and ad == -1) or
            (lid == 'VWAP_LOWER' and ad == 1)):
        return 0
    if f.get('aggr_dir') != ad or f.get('aggr_z') is None or \
            f['aggr_z'] < Z_AGGR_LEVEL:
        return 0
    return ad


def l4_break_retest(f, broke):
    """broke: direction of an earlier held break of this level in this
    session, or None."""
    if f.get('level_id') not in RANGE_LEVELS or not broke:
        return 0
    ad = f.get('ad')
    if ad != -broke:
        return 0
    if f.get('aggr_dir') != ad or f.get('aggr_z') is None or \
            f['aggr_z'] < Z_AGGR_LEVEL:
        return 0
    p = f.get('progress_ticks')
    if p is None or p > RETEST_PROGRESS_MAX:
        return 0
    return broke


def d1_trend_1030(mid, cash_open, sub_sums):
    """sub_sums: the six 10-minute aggressor-delta sums of 09:30-10:30."""
    if mid is None or cash_open is None or len(sub_sums) != 6:
        return 0
    move = mid - cash_open
    if abs(move) < TREND_MOVE_POINTS:
        return 0
    s = 1 if move > 0 else -1
    if s * sum(sub_sums) <= 0:
        return 0
    if sum(1 for x in sub_sums if s * x > 0) < TREND_SUBS_MIN:
        return 0
    return s


# ---------------------------------------------------------------------
# the path score (registration 2)
# ---------------------------------------------------------------------
class _MinFenwick(object):
    """Prefix-minimum Fenwick tree; values only ever decrease, which is
    exactly the sweep below (indices are inserted in decreasing order)."""
    __slots__ = ('n', 'a')

    def __init__(self, n):
        self.n = n
        self.a = [1 << 60] * (n + 1)

    def update(self, i, v):
        i += 1
        a = self.a
        n = self.n
        while i <= n:
            if a[i] > v:
                a[i] = v
            i += i & -i

    def query(self, i):
        """min over [0, i] inclusive; i may be < 0 (-> sentinel)."""
        i += 1
        if i <= 0:
            return 1 << 60
        a = self.a
        best = 1 << 60
        while i > 0:
            if a[i] < best:
                best = a[i]
            i -= i & -i
        return best


def compress(ts, ps):
    """(t, p) at every price CHANGE, plus the last point so the series'
    end is known. Mids repeat for most quote updates."""
    ct, cp = array.array('d'), array.array('d')
    last = None
    n = len(ps)
    for i in range(n):
        p = ps[i]
        if p != last:
            ct.append(ts[i])
            cp.append(p)
            last = p
    if n and (not ct or ct[-1] != ts[-1]):
        ct.append(ts[-1])
        cp.append(ps[-1])
    return ct, cp


class PathIndex(object):
    """For one run's compressed mid path: the first index after i whose
    price is at least `up` half-ticks above, or at least `dn` below,
    p[i] -- for the target and every stop, both directions -- answered
    by one right-to-left sweep over two Fenwick trees keyed by price.
    Queries are answered only at the indices asked for (grid ticks and
    fires), updates happen for every point."""

    def __init__(self, ts, ps, want):
        self.ts, self.ps = ts, ps
        n = len(ps)
        self.n = n
        self.first = {}                    # i -> dict(thr_halfticks -> j)
        if n == 0:
            return
        lo = min(ps)
        bins = [int(round((p - lo) / HALF_TICK)) for p in ps]
        m = max(bins) + 1
        thr = sorted({int(round(TARGET_TICKS * 2))} |
                     {int(round(s * 2)) for s in STOPS_TICKS})
        want = set(want)
        up = _MinFenwick(m)                # over reversed bins: suffix min
        dn = _MinFenwick(m)                # over bins: prefix min
        for i in range(n - 1, -1, -1):
            b = bins[i]
            if i in want:
                d = {}
                for h in thr:
                    j = up.query(m - 1 - (b + h))      # bins >= b+h
                    d[('up', h)] = None if j >= (1 << 60) else j
                    j = dn.query(b - h)                 # bins <= b-h
                    d[('dn', h)] = None if j >= (1 << 60) else j
                self.first[i] = d
            up.update(m - 1 - b, i)
            dn.update(b, i)

    def index_at(self, t0):
        i = bisect.bisect_right(self.ts, t0) - 1
        return None if i < 0 else i

    def score(self, i, d, stop_ticks, excursions=False):
        """One event at compressed index i, direction d. Returns a dict
        with outcome TARGET/STOP/TIMEOUT/UNRESOLVED (and, for events,
        the descriptive excursions), or None when i has no answer (not
        asked for). A stop touched on the same mid as the target is a
        STOP (registration 2)."""
        q = self.first.get(i)
        if q is None:
            return None
        ts, ps = self.ts, self.ps
        t0, p0 = ts[i], ps[i]
        ht, hs = int(round(TARGET_TICKS * 2)), int(round(stop_ticks * 2))
        jt = q[('up', ht)] if d > 0 else q[('dn', ht)]
        js = q[('dn', hs)] if d > 0 else q[('up', hs)]
        t_end = t0 + LIMIT_S
        jt_ok = jt is not None and ts[jt] <= t_end
        js_ok = js is not None and ts[js] <= t_end
        if js_ok and (not jt_ok or js <= jt):
            out, j_res, val = 'STOP', js, -stop_ticks
        elif jt_ok:
            out, j_res, val = 'TARGET', jt, TARGET_TICKS
        elif ts[-1] < t_end:
            out, j_res, val = 'UNRESOLVED', self.n - 1, None
        else:
            k = bisect.bisect_right(ts, t_end) - 1
            out, j_res = 'TIMEOUT', k
            val = d * (ps[k] - p0) / SIG.TICK
        rec = dict(outcome=out, value_ticks=val,
                   seconds=round(ts[j_res] - t0, 3))
        if excursions:
            mae = mfe = 0.0
            for k in range(i + 1, j_res + 1):
                x = d * (ps[k] - p0) / SIG.TICK
                if x < mae:
                    mae = x
                if x > mfe:
                    mfe = x
            rec.update(mae_ticks=-mae, mfe_ticks=mfe)   # both magnitudes
        return rec


def window_extremes(ts, ps, want):
    """{i: (max up ticks, max down ticks)} over (i, i + 1800 s] for the
    asked-for indices, by one monotonic-deque sweep; an index whose
    window runs past the end of the run is left out (UNRESOLVED)."""
    out = {}
    n = len(ps)
    if not n:
        return out
    want = sorted(want)
    hi = collections.deque()               # indices, prices decreasing
    lo = collections.deque()               # indices, prices increasing
    k = 0                                  # last index pushed
    for i in want:
        t_end = ts[i] + LIMIT_S
        if ts[-1] < t_end:
            break                          # every later i is unresolved too
        while k + 1 < n and ts[k + 1] <= t_end:
            k += 1
            p = ps[k]
            while hi and ps[hi[-1]] <= p:
                hi.pop()
            hi.append(k)
            while lo and ps[lo[-1]] >= p:
                lo.pop()
            lo.append(k)
        while hi and hi[0] <= i:
            hi.popleft()
        while lo and lo[0] <= i:
            lo.popleft()
        p0 = ps[i]
        up = max(0.0, (ps[hi[0]] - p0) / SIG.TICK) if hi else 0.0
        dn = max(0.0, (p0 - ps[lo[0]]) / SIG.TICK) if lo else 0.0
        out[i] = (up, dn)
    return out


def score_path_brute(ts, ps, t0, d, stop_ticks):
    """Reference implementation for the suite: a plain forward scan."""
    i = bisect.bisect_right(ts, t0) - 1
    if i < 0:
        return None
    p0 = ps[i]
    t_end = ts[i] + LIMIT_S
    for j in range(i + 1, len(ps)):
        if ts[j] > t_end:
            break
        x = d * (ps[j] - p0) / SIG.TICK
        if x <= -stop_ticks:
            return 'STOP'
        if x >= TARGET_TICKS:
            return 'TARGET'
    if ts[-1] < t_end:
        return 'UNRESOLVED'
    return 'TIMEOUT'


# ---------------------------------------------------------------------
# statistics (registration 3 and 5)
# ---------------------------------------------------------------------
def holm(pvals, alpha=ALPHA):
    """Holm step-down. Returns [bool] rejected, same order as pvals;
    None p-values are never rejected and count toward m."""
    m = len(pvals)
    order = sorted(range(m), key=lambda i: (pvals[i] is None,
                                            pvals[i] if pvals[i] is not None
                                            else 0.0))
    rejected = [False] * m
    for rank, i in enumerate(order):
        p = pvals[i]
        if p is None or p > alpha / (m - rank):
            break
        rejected[i] = True
    return rejected


def _lift_stats(obs, exp, seed=PI.BOOTSTRAP_SEED, n_boot=PI.BOOTSTRAP_N):
    """obs: per-event 1/0 hit; exp: per-event matched baseline rate.
    Returns lift, its bootstrap 95% interval and a two-sided p."""
    n = len(obs)
    if n == 0:
        return dict(n=0)
    lift = sum(obs) / n - sum(exp) / n
    if n < PI.BOOTSTRAP_MIN_N:
        return dict(n=n, lift=round(lift, 4))
    rng = random.Random(seed)
    draws = []
    idx = range(n)
    for _ in range(n_boot):
        pick = [rng.choice(idx) for _ in idx]
        draws.append(sum(obs[k] for k in pick) / n -
                     sum(exp[k] for k in pick) / n)
    draws.sort()
    lo = draws[int(0.025 * (n_boot - 1))]
    hi = draws[int(0.975 * (n_boot - 1))]
    le = sum(1 for x in draws if x <= 0.0) / n_boot
    ge = sum(1 for x in draws if x >= 0.0) / n_boot
    p = min(1.0, 2.0 * min(le, ge))
    p = max(p, 1.0 / n_boot)
    return dict(n=n, lift=round(lift, 4), ci95=(round(lo, 4), round(hi, 4)),
                p=round(p, 4))


# ---------------------------------------------------------------------
# the runner: pilot runner plus wave three, hooks only
# ---------------------------------------------------------------------
class _W3State(object):
    def __init__(self):
        self.prev_grid = None              # last grid record (G3)
        self.fired = set()                 # (pattern, approach id)
        self.broke = {}                    # level_id -> held break dir
        self.trend_subs = [0.0] * 6        # 09:30-10:30 ten-minute sums
        self.trend_done = False
        self.placebo_off = {}
        self.placebo_seed_session = None


class BigMoveRunner(PI.PilotRunner):
    """Overrides hooks only. mode='placebo' shifts every level by the
    wave-two ARM-C rule and changes nothing else."""

    def __init__(self, capture_dir, mode='real', unblind=False, **kw):
        PI.PilotRunner.__init__(self, capture_dir, **kw)
        assert mode in ('real', 'placebo')
        self.mode = mode
        self.unblind = unblind
        self.w3 = {i: _W3State() for i in self.instruments}
        self.w3_fires = []
        self.w3_counts = collections.Counter()
        self.grid = []                     # grid records (census, baseline)
        self.refused_sessions = []
        self.ledger['wave3'] = dict(version=W3_VERSION, mode=mode)

    # ---- registration 8: the gate ----------------------------------------
    def plan(self):
        plan = PI.PilotRunner.plan(self)
        if self.unblind:
            return plan
        keep = []
        for inst, ses, runs in plan:
            if ses > DEV_END:
                if ses not in self.refused_sessions:
                    self.refused_sessions.append(ses)
                continue
            keep.append((inst, ses, runs))
        self.refused_sessions.sort()
        if plan and not keep:
            raise RUN.NoCaptureData(
                'every session in %s is later than %s (validation); this '
                'tool reads DEV sessions only. Nothing was read.'
                % (self.dir, DEV_END))
        return keep

    # ---- memory: the observation buffers unwind with an abandoned run ----
    def _mark_run(self, st):
        mark = PI.PilotRunner._mark_run(self, st)
        mark['w3'] = dict(fires=len(self.w3_fires), grid=len(self.grid))
        return mark

    def _unwind_run(self, st, mark):
        PI.PilotRunner._unwind_run(self, st, mark)
        del self.w3_fires[mark['w3']['fires']:]
        del self.grid[mark['w3']['grid']:]

    # ---- placebo levels (wave two ARM-C, same seed rule) ----------------
    def _rebuild_levels(self, st):
        PI.PilotRunner._rebuild_levels(self, st)
        if self.mode != 'placebo' or not st.levels:
            return
        w = self.w3[st.instrument]
        rad = self._radius(st)
        real = dict(st.levels)
        if w.placebo_seed_session != st.session:
            w.placebo_off = {}
            w.placebo_seed_session = st.session
        placebo = {}
        for lid, px in real.items():
            if lid not in w.placebo_off:
                rng = random.Random(int(st.session or 0) * 1000003 +
                                    zlib.crc32(lid.encode()))
                mag = rng.uniform(PLACEBO_LO, PLACEBO_HI)
                w.placebo_off[lid] = mag if rng.random() < 0.5 else -mag
            p = px + w.placebo_off[lid] * rad
            if all(abs(p - rp) >= PLACEBO_MIN_SEP * rad
                   for rp in real.values()):
                placebo[lid] = p
        st.levels = placebo

    def _close_session(self, st):
        PI.PilotRunner._close_session(self, st)
        w = self.w3[st.instrument]
        w.prev_grid = None
        w.broke = {}
        w.trend_subs = [0.0] * 6
        w.trend_done = False

    # ---- the grid: G1-G3, D1, census and baseline records ----------------
    def _observe_baselines(self, st, te):
        PI.PilotRunner._observe_baselines(self, st, te)
        if not st.ready:
            return
        w = self.w3[st.instrument]
        sod = RUN.sod_seconds(te)
        z = st.baseline.z
        tr, D, ofi, r, bi3, m_end = self._window_stats(
            st, te - RUN.DECISION_S, te)
        n10 = float(len(tr))
        st.baseline.observe('n10', sod, n10)     # own key; frozen keys untouched
        s = 1 if D > 0 else (-1 if D < 0 else 0)
        agree = None
        control_s = None
        if s:
            agree, _decay = SIG.persistence(tr, te - RUN.DECISION_S, s)
            control_s = self._control(st, sod, s, D, ofi, r, bi3)
        g = dict(instrument=st.instrument, session=st.session,
                 run=self._cur[1] if self._cur else None, t=te, sod=sod,
                 hour=int(sod // 3600), s=s, D=D,
                 z_delta=z('delta10', sod, D),
                 z_delta_s=(z('delta10', sod, s * D) if s else None),
                 z_ofi=z('ofi10', sod, ofi), resp=r,
                 z_bi3=(None if bi3 is None else z('bi3', sod, bi3)),
                 z_n10=z('n10', sod, n10),
                 agree_s=agree, control_s=control_s, mid=m_end)
        self.grid.append(g)
        self.w3_counts['grid'] += 1
        # G1-G3
        d = g1_flow_shock_go(g)
        if d:
            self._w3_fire(st, 'G1', d, te, None, g)
        d = g2_flow_shock_fade(g)
        if d:
            self._w3_fire(st, 'G2', d, te, None, g)
        d = g3_control_run(g, w.prev_grid)
        if d:
            self._w3_fire(st, 'G3', d, te, None, g)
        w.prev_grid = g
        # D1: accumulate 09:30-10:30, decide once at or after 10:30
        if 9.5 * 3600 <= sod < TREND_SOD:
            k = int((sod - 9.5 * 3600) // 600)
            if 0 <= k < 6:
                w.trend_subs[k] += D
        elif sod >= TREND_SOD and not w.trend_done and sod < 18 * 3600:
            w.trend_done = True
            d = d1_trend_1030(m_end, st.opens.get('CASH_OPEN_0930'),
                              w.trend_subs)
            if d:
                self._w3_fire(st, 'D1', d, te, None, g)

    # ---- the approach windows: L1-L4 -------------------------------------
    def _on_window(self, st, ap, te, f):
        PI.PilotRunner._on_window(self, st, ap, te, f)
        w = self.w3[st.instrument]
        self.w3_counts['windows'] += 1
        sod = RUN.sod_seconds(te)
        ff = dict(f, level_id=ap.level_id, ad=ap.ad)
        for pat, d in (('L1', l1_open_break(ff, sod)),
                       ('L2', l2_sweep_reclaim(ff)),
                       ('L3', l3_vwap_snapback(ff)),
                       ('L4', l4_break_retest(ff, w.broke.get(ap.level_id)))):
            if d and (pat, ap.id) not in w.fired:
                w.fired.add((pat, ap.id))
                self._w3_fire(st, pat, d, te, ap, None)
        # L4 memory: a held clean break of a range level, in this session
        if ap.level_id in RANGE_LEVELS and f.get('clean_cross') and \
                f.get('held_5s'):
            w.broke[ap.level_id] = ap.ad

    def _w3_fire(self, st, pat, direction, t, ap, g):
        self.w3_counts[pat] += 1
        rec = dict(instrument=st.instrument, session=st.session,
                   family=pat, run=st.run_id, direction=direction,
                   t=round(t, 3),
                   level=ap.level_id if ap is not None else None,
                   approach=ap.id if ap is not None else None,
                   state=ap.wall_state if ap is not None else None,
                   hour=int(RUN.sod_seconds(t) // 3600), mode=self.mode)
        if g is not None:
            rec['grid'] = dict((k, g.get(k)) for k in
                               ('z_delta_s', 'resp', 'agree_s', 'control_s'))
        self.w3_fires.append(rec)


# ---------------------------------------------------------------------
# scoring a finished run of the runner
# ---------------------------------------------------------------------
def _hours_cell(e):
    # (instrument, ET hour, direction): a long event is compared with
    # longs at that hour, a short with shorts, so a sample that drifted
    # one way does not flatter every pattern trading that way
    # (registration 3, corrected 2026-10-09 before any recorded run)
    return (e['instrument'], e['hour'], e['direction'])


def score_runner(r):
    """Builds one PathIndex per recording run, scores every grid tick
    (baseline, both directions) and every event, and returns the blocks
    the report needs."""
    # which indices are asked for, per run
    by_run = collections.defaultdict(set)
    paths = {}
    for key, (ts, ps) in r.series.items():
        if len(ts):
            paths[key] = compress(ts, ps)
    grid_idx = []
    for g in r.grid:
        key = (g['instrument'], g['run'])
        if key not in paths:
            grid_idx.append(None)
            continue
        i = bisect.bisect_right(paths[key][0], g['t']) - 1
        grid_idx.append(i if i >= 0 else None)
        if i >= 0:
            by_run[key].add(i)
    events_all = PI.dedup_fires(r.w3_fires, PI.EVENT_COOLDOWN_S)
    ev_idx = []
    for e in events_all:
        key = (e['instrument'], e.get('run'))
        if key not in paths:
            ev_idx.append(None)
            continue
        i = bisect.bisect_right(paths[key][0], e['t']) - 1
        ev_idx.append(i if i >= 0 else None)
        if i >= 0:
            by_run[key].add(i)
    index = {key: PathIndex(paths[key][0], paths[key][1], by_run[key])
             for key in by_run}

    # baseline cells: (instrument, hour, direction) -> per stop -> counts
    cells = collections.defaultdict(
        lambda: {s: collections.Counter() for s in STOPS_TICKS})
    census_rows = []
    grid_by_run = collections.defaultdict(set)
    for g, i in zip(r.grid, grid_idx):
        if i is not None:
            grid_by_run[(g['instrument'], g['run'])].add(i)
    extremes = {key: window_extremes(paths[key][0], paths[key][1], idxs)
                for key, idxs in grid_by_run.items()}
    for g, i in zip(r.grid, grid_idx):
        if i is None:
            continue
        key = (g['instrument'], g['run'])
        px = index[key]
        for d in (1, -1):
            cell = cells[(g['instrument'], g['hour'], d)]
            for s in STOPS_TICKS:
                sc = px.score(i, d, s)
                if sc is not None:
                    cell[s][sc['outcome']] += 1
        ex = extremes[key].get(i)
        if ex is not None:
            census_rows.append((g, ex))
    base = {}
    for key, per in cells.items():
        base[key] = {}
        for s, c in per.items():
            n = c['TARGET'] + c['STOP'] + c['TIMEOUT']
            base[key][s] = dict(n=n, unresolved=c['UNRESOLVED'],
                                hit=(c['TARGET'] / n) if n else None)

    # events
    scored = []
    for e, i in zip(events_all, ev_idx):
        rec = dict(e)
        rec['scores'] = {}
        if i is not None:
            px = index[(e['instrument'], e['run'])]
            for s in STOPS_TICKS:
                rec['scores']['%g' % s] = px.score(i, e['direction'], s,
                                                   excursions=True)
        rec['hour'] = int(RUN.sod_seconds(e['t']) // 3600)
        scored.append(rec)
    return dict(events=scored, baseline=base, census_rows=census_rows,
                n_runs_indexed=len(index))


def pattern_block(scored, base, pat, instrument):
    evs = [e for e in scored if e['family'] == pat and
           e['instrument'] == instrument]
    blk = dict(pattern=pat, name=PATTERN_NAMES[pat], instrument=instrument,
               events=len(evs),
               by_session=dict(sorted(collections.Counter(
                   e['session'] for e in evs).items())),
               by_hour=dict(sorted(collections.Counter(
                   e['hour'] for e in evs).items())),
               directions=dict(collections.Counter(
                   e['direction'] for e in evs)),
               stops={})
    for s in STOPS_TICKS:
        k = '%g' % s
        res = [(e, e['scores'].get(k)) for e in evs]
        res = [(e, sc) for e, sc in res if sc is not None]
        counts = collections.Counter(sc['outcome'] for _e, sc in res)
        resolved = [(e, sc) for e, sc in res
                    if sc['outcome'] != 'UNRESOLVED']
        n = len(resolved)
        d = dict(counts=dict(counts), n_resolved=n)
        if n:
            obs = [1.0 if sc['outcome'] == 'TARGET' else 0.0
                   for _e, sc in resolved]
            exp = []
            for e, _sc in resolved:
                cell = base.get(_hours_cell(e), {}).get(s)
                exp.append(cell['hit'] if cell and cell['hit'] is not None
                           else float('nan'))
            ok = [k for k in range(n) if exp[k] == exp[k]]
            d['hit_rate'] = round(sum(obs) / n, 4)
            d['expectancy_ticks_before_costs'] = round(
                sum(sc['value_ticks'] for _e, sc in resolved) / n, 2)
            d['expectancy_points_before_costs'] = round(
                d['expectancy_ticks_before_costs'] / POINT, 2)
            if ok:
                st = _lift_stats([obs[k] for k in ok], [exp[k] for k in ok])
                d['matched_baseline_hit'] = round(
                    sum(exp[k] for k in ok) / len(ok), 4)
                d['lift'] = st
            wins = [sc for _e, sc in resolved if sc['outcome'] == 'TARGET']
            if wins:
                mae = sorted(w['mae_ticks'] for w in wins)
                secs = sorted(w['seconds'] for w in wins)
                d['winners'] = dict(
                    n=len(wins),
                    mae_ticks_median=mae[len(mae) // 2],
                    mae_ticks_p75=mae[int(0.75 * (len(mae) - 1))],
                    seconds_to_target_median=secs[len(secs) // 2])
        blk['stops'][k] = d
    return blk


def census(rows):
    """Registration 7: deciles of each grid feature against the share of
    ticks that reach +100 / -100 ticks inside 1800 s. Diagnostic."""
    out = dict(n=len(rows))
    if not rows:
        return out
    up_all = sum(1 for _g, (u, _d) in rows if u >= TARGET_TICKS)
    dn_all = sum(1 for _g, (_u, d) in rows if d >= TARGET_TICKS)
    out['base_rate'] = dict(up=round(up_all / len(rows), 4),
                            down=round(dn_all / len(rows), 4))
    for feat in CENSUS_FEATURES:
        vals = [(g[feat], ex) for g, ex in rows if g.get(feat) is not None]
        if len(vals) < 50:
            out[feat] = dict(n=len(vals), note='too few values')
            continue
        vals.sort(key=lambda x: x[0])
        n = len(vals)
        dec = []
        for k in range(10):
            part = vals[k * n // 10:(k + 1) * n // 10]
            if not part:
                continue
            dec.append(dict(
                decile=k + 1, n=len(part),
                lo=round(part[0][0], 3), hi=round(part[-1][0], 3),
                up=round(sum(1 for _v, (u, _d) in part
                             if u >= TARGET_TICKS) / len(part), 4),
                down=round(sum(1 for _v, (_u, d) in part
                               if d >= TARGET_TICKS) / len(part), 4)))
        out[feat] = dict(n=n, deciles=dec)
    out['note'] = ('diagnostic only: not a test, produces no verdict; a '
                   'rule drawn from it is a wave-four registration on '
                   'sessions not yet recorded')
    return out


# ---------------------------------------------------------------------
# the report
# ---------------------------------------------------------------------
def run_bigmove(capture_dir, mode='real', unblind=False, max_sessions=None):
    r = BigMoveRunner(capture_dir, mode=mode, unblind=unblind,
                      max_sessions=max_sessions)
    led = r.run()
    return report_from_runner(r, led), r


def report_from_runner(r, led):
    """The wave-three report of a finished BigMoveRunner (or subclass).
    Split out of run_bigmove so a successor wave that subclasses the
    runner gets this report from the SAME read of the tape."""
    mode, unblind = r.mode, r.unblind
    sc = score_runner(r)
    blocks = {}
    for pat in PATTERNS:
        blocks[pat] = {inst: pattern_block(sc['events'], sc['baseline'],
                                           pat, inst)
                       for inst in r.instruments}
    # registration 5: Holm over the 24 (pattern, stop) tests on NQ
    tests = []
    for pat in PATTERNS:
        for s in STOPS_TICKS:
            d = blocks[pat][PI.SIGNAL_SOURCE_INSTRUMENT]['stops']['%g' % s]
            p = d.get('lift', {}).get('p')
            tests.append(dict(pattern=pat, stop_ticks=s, p=p,
                              n=d.get('n_resolved', 0)))
    rej = holm([t['p'] for t in tests])
    for t_, rj in zip(tests, rej):
        t_['survives_holm'] = bool(rj) and t_['n'] >= MIN_EVENTS
        t_['enough_events'] = t_['n'] >= MIN_EVENTS
    base_out = {'%s@%02d@%+d' % k: {'%g' % s: v for s, v in per.items()}
                for k, per in sc['baseline'].items()}
    rep = dict(wave3=W3_VERSION, registration=REGISTRATION, mode=mode,
               unblind=unblind, dev_end=DEV_END,
               runner=led['runner'], outcomes_wave_one=led['outcomes'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               wave_one_raw_fires=len(led.get('fires', [])),
               grid_ticks=r.w3_counts['grid'],
               windows=r.w3_counts['windows'],
               raw_fires=dict((p, r.w3_counts[p]) for p in PATTERNS),
               score_rule=dict(target_ticks=TARGET_TICKS,
                               stops_ticks=list(STOPS_TICKS),
                               limit_s=LIMIT_S, tie='STOP',
                               basis='mid-to-mid first touch inside one '
                                     'recording run; no fill, spread, '
                                     'slippage or commission; not P&L'),
               patterns=blocks, tests=tests, n_tests=N_TESTS,
               baseline_cells=base_out,
               census=census(sc['census_rows']),
               events=sc['events'], fires=r.w3_fires)
    return rep


def paired_placebo(real, placebo):
    out = {}
    inst = PI.SIGNAL_SOURCE_INSTRUMENT
    for pat in LEVEL_PATTERNS:
        out[pat] = {}
        for s in STOPS_TICKS:
            k = '%g' % s
            a = real['patterns'][pat][inst]['stops'][k]
            b = placebo['patterns'][pat][inst]['stops'][k]
            out[pat][k] = dict(
                real_n=a.get('n_resolved', 0), placebo_n=b.get('n_resolved', 0),
                real_lift=a.get('lift', {}).get('lift'),
                placebo_lift=b.get('lift', {}).get('lift'),
                real_hit=a.get('hit_rate'), placebo_hit=b.get('hit_rate'))
    return out


def text_summary(rep, paired=None):
    inst = PI.SIGNAL_SOURCE_INSTRUMENT
    L = ['%s  mode=%s  unblind=%s  registration=%s'
         % (rep['wave3'], rep['mode'], rep['unblind'], rep['registration']),
         'sessions read: %s' % ', '.join(rep['sessions_inspected']),
         'sessions REFUSED (validation, > %s): %s'
         % (rep['dev_end'], ', '.join(rep['sessions_refused']) or 'none'),
         'wave-one raw fires (unchanged, for reference): %d; wave-one '
         'outcomes: %s' % (rep['wave_one_raw_fires'],
                            rep['outcomes_wave_one']),
         'grid ticks: %d   approach windows: %d'
         % (rep['grid_ticks'], rep['windows']),
         'score: target %g ticks, stops %s, limit %g s, tie=STOP, %s'
         % (rep['score_rule']['target_ticks'],
            rep['score_rule']['stops_ticks'], rep['score_rule']['limit_s'],
            rep['score_rule']['basis']),
         '']
    L.append('%-4s %-16s %-4s %4s  %5s  %6s  %6s  %7s  %7s  %s' % (
        'id', 'pattern', 'inst', 'ev', 'stop', 'hit', 'base', 'lift',
        'p', 'expect(pts)'))
    for pat in PATTERNS:
        for ins in (inst, 'MNQ'):
            b = rep['patterns'][pat].get(ins)
            if not b:
                continue
            for s in STOPS_TICKS:
                d = b['stops']['%g' % s]
                if not d.get('n_resolved'):
                    L.append('%-4s %-16s %-4s %4d  %5g  %s' % (
                        pat, b['name'], ins, b['events'], s, 'n=0'))
                    continue
                lf = d.get('lift', {})
                L.append('%-4s %-16s %-4s %4d  %5g  %6.3f  %6s  %7s  %7s  %s'
                         % (pat, b['name'], ins, d['n_resolved'], s,
                            d['hit_rate'],
                            ('%.3f' % d['matched_baseline_hit'])
                            if 'matched_baseline_hit' in d else '-',
                            ('%+.3f' % lf['lift']) if 'lift' in lf else '-',
                            ('%.4f' % lf['p']) if 'p' in lf else '-',
                            '%+.2f' % d['expectancy_points_before_costs']))
    L.append('')
    surv = [t for t in rep['tests'] if t['survives_holm']]
    L.append('Holm over %d tests (NQ): %s'
             % (rep['n_tests'],
                ', '.join('%s@%g' % (t['pattern'], t['stop_ticks'])
                          for t in surv) or 'nothing survives'))
    few = [t for t in rep['tests'] if not t['enough_events']]
    L.append('tests with fewer than %d resolved NQ events (NOT TESTED): %d '
             'of %d' % (MIN_EVENTS, len(few), rep['n_tests']))
    c = rep['census']
    if c.get('base_rate'):
        L.append('')
        L.append('census (diagnostic): %d grid ticks; base rate of a '
                 '+100-tick move inside 1800 s: %.3f, -100: %.3f'
                 % (c['n'], c['base_rate']['up'], c['base_rate']['down']))
        for feat in CENSUS_FEATURES:
            f = c.get(feat, {})
            if f.get('deciles'):
                lo, hi = f['deciles'][0], f['deciles'][-1]
                L.append('  %-8s decile 1 [%s..%s]: up %.3f down %.3f | '
                         'decile 10 [%s..%s]: up %.3f down %.3f'
                         % (feat, lo['lo'], lo['hi'], lo['up'], lo['down'],
                            hi['lo'], hi['hi'], hi['up'], hi['down']))
    if paired:
        L.append('')
        L.append('PLACEBO (level patterns, NQ): real vs shifted levels')
        for pat, per in paired.items():
            for k, p in per.items():
                L.append('  %-4s stop %3s  real n=%-3d hit=%-6s lift=%-7s  '
                         'placebo n=%-3d hit=%-6s lift=%s'
                         % (pat, k, p['real_n'], p['real_hit'],
                            p['real_lift'], p['placebo_n'], p['placebo_hit'],
                            p['placebo_lift']))
    L.append('')
    L.append('No order was placed. No fill, slippage or commission was '
             'modelled. Expectancy is mid-to-mid and is not P&L.')
    return '\n'.join(L)


def write_exposure_on_unblind(rep, path):
    """Checkpoint only: every session read is exposed by this wave,
    permanently. Monotone, like the pilot's ledger."""
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get('exposed_days', [])
        except Exception:
            old = []
    by = {d['session']: d for d in old}
    for s in rep['sessions_inspected']:
        cur = by.get(s)
        if cur is None:
            by[s] = dict(session=s, label=PI.EXPOSURE_LABEL,
                         exposed_by=W3_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W3_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W3_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W3_VERSION)
    days = sorted(by.values(), key=lambda d: d['session'])
    doc = dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
               rule='EXPOSED days may remain in later DEV/training where '
                    'the governing protocol permits; they can never '
                    'become untouched prospective validation. BLIND '
                    'days had fire counts read and markouts withheld; '
                    'they remain valid validation until explicitly '
                    'unblinded, which is permanent.',
               exposed_days=days)
    json.dump(doc, open(path, 'w'), indent=1)
    return len(days)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    out = argv[argv.index('--out') + 1] if '--out' in argv else None
    ms = (int(argv[argv.index('--max-sessions') + 1])
          if '--max-sessions' in argv else None)
    both = '--both' in argv
    unblind = '--unblind' in argv
    if unblind:
        print('*** UNBLIND: this read includes the validation sessions '
              '(> %s). Every session read is labelled exposed, '
              'permanently. This is the checkpoint read. ***\n' % DEV_END)
    try:
        rep, _r = run_bigmove(d, mode='real', unblind=unblind,
                              max_sessions=ms)
        rep_p = None
        if both:
            rep_p, _rp = run_bigmove(d, mode='placebo', unblind=unblind,
                                     max_sessions=ms)
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    paired = None
    if both:
        paired = paired_placebo(rep, rep_p)
        rep = dict(rep, placebo=rep_p, paired=paired, mode='both')
    print(text_summary(rep, paired))
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-three report -> %s' % out)
    if unblind:
        led = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'MROF_EXPOSED_PILOT_DEV_DAYS.json')
        n = write_exposure_on_unblind(rep, led)
        print('exposure ledger -> %s (%d days)' % (led, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
