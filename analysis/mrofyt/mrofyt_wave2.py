"""mrofyt_wave2.py - MROF-YT-WAVE2-1.0

MROF_YT_WAVE2_REGISTRATION.md turned into running code. Wave one is
UNTOUCHED: this module subclasses the pilot runner and uses only the
runner's observation hooks. Every wave-two family, arm and variant is
evaluated on the SAME decision windows the frozen runner produces, so
every comparison is paired by construction.

    W2-A1        [reg 1.1]  A1 with replenishment observed on EVERY 10 s
                            grid tick (repl10), not only at executions
    W2-A4r       [reg 1]    A4 exactly as it ran: progress_ticks <= 1
    W2-A4f       [reg 1]    A4 with the expected-response residual wired
    W2-A4-OPEN   [reg 2]    W2-A4r, 09:30-10:30 ET, open/overnight levels
    W2-A4r-z15   [reg 3]    W2-A4r with aggr_z >= 1.5
    W2-A4r-HC    [reg 6]    W2-A4r with aggr_z from aggrConf==HIGH trades
    ARM-B1/B2    [reg 4.1]  candle-only triggers on the same approaches
    ARM-C        [reg 4.2]  the whole pipeline on PLACEBO levels
                            (a separate run: mode='placebo')

NOT in this version: the CAUSAL_SWING level comparison [reg 4.3]. It
needs the v01.6 engine integrated as a level provider and the frozen
approach loop to accept ids outside ACTIVE_LEVEL_IDS; that is its own
build and is said so rather than half-done here.

The W2-A4f residual model is the registered FIRST-WAVE MINIMAL form:
per 5-minute-of-day bucket, in the aggressor's frame, a robust fit of
10 s response on |signed delta| (Bartlett three-group slope, median
intercept), fit ONLY on prior sessions, with the adverse tail defined
as the bottom 5% of prior residuals. The registration's fuller
covariate set (intensity, BI3, realized vol, distance to level) is NOT
in this version; every A4f fire record says so (`model` field).

Outcome lock: this module computes no fill, stop, target, R or P&L.
Markouts for wave-two fires use the pilot's step-7 machinery and obey
the same validation blind (BLIND_FROM).

    python3 mrofyt_wave2.py "<capture folder>" --out w2.json
    python3 mrofyt_wave2.py "<capture folder>" --both --out w2.json
                                              # real + placebo, paired
"""

import collections
import json
import math
import random
import sys
import zlib

import mrofyt_levels as LV
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

WAVE2_VERSION = 'MROF-YT-WAVE2-1.0'
FAMILIES = ('W2-A1', 'W2-A4r', 'W2-A4f', 'W2-A4-OPEN', 'W2-A4r-z15',
            'W2-A4r-HC', 'ARM-B1', 'ARM-B2')
OPEN_WINDOW_ET = (9.5 * 3600, 10.5 * 3600)          # 09:30:00-10:30:00
OPEN_LEVELS_W2 = ('CASH_OPEN_0930', 'OVERNIGHT_HIGH', 'OVERNIGHT_LOW')
Z15 = 1.5
REPL_WINDOW_S = RUN.DECISION_S                      # 10 s
TOP_K = 3
RESID_MODEL = 'delta+bucket, aggressor frame, robust; NO intensity/BI3/' \
              'vol/distance in this version'
# placebo: each real level shifted by a per-session, per-level offset
# of +/- [PLACEBO_LO, PLACEBO_HI] radii, kept >= PLACEBO_MIN_SEP radii
# from EVERY real active level (registration 4.2)
PLACEBO_LO, PLACEBO_HI, PLACEBO_MIN_SEP = 6.0, 20.0, 3.0


# ---------------------------------------------------------------------
# W2-A4f: expected-response residual, first-wave minimal form
# ---------------------------------------------------------------------
def _median(xs):
    xs = sorted(xs)
    n = len(xs)
    return xs[n // 2] if n % 2 else 0.5 * (xs[n // 2 - 1] + xs[n // 2])


class ResidualModel(object):
    """Per (5-min bucket): r_a = a + b * |D| in the aggressor frame,
    r_a = sign(D) * r. Fit only on PRIOR sessions; the current session's
    observations join the history at close_session, exactly as the
    frozen BaselineStore does. Adverse tail = residual <= the 5th
    percentile of prior residuals in the bucket."""
    MIN_OBS = 20
    N_SESSIONS = 20

    def __init__(self):
        self.hist = collections.defaultdict(
            lambda: collections.deque(maxlen=self.N_SESSIONS))
        self.cur = collections.defaultdict(list)
        self._fit_cache = {}

    @staticmethod
    def bucket(sod):
        return int(sod // 300)

    def observe(self, sod, D, r):
        if D and r is not None:
            s = 1.0 if D > 0 else -1.0
            self.cur[self.bucket(sod)].append((abs(D), s * r))

    def close_session(self):
        for b, obs in self.cur.items():
            if obs:
                self.hist[b].append(list(obs))
        self.cur = collections.defaultdict(list)
        self._fit_cache = {}

    def fit(self, b):
        if b in self._fit_cache:
            return self._fit_cache[b]
        obs = sorted(o for sess in self.hist[b] for o in sess)
        out = None
        if len(obs) >= self.MIN_OBS:
            # Bartlett three-group slope: medians of the lower and upper
            # thirds by |D|. Robust, deterministic, and unlike a median
            # of r/|D| it does not fold the intercept into the slope.
            k = len(obs) // 3
            lo, hi = obs[:k], obs[-k:]
            d_lo, d_hi = _median([d for d, _ in lo]), _median([d for d, _ in hi])
            if d_hi - d_lo > 0:
                slope = (_median([r for _, r in hi]) -
                         _median([r for _, r in lo])) / (d_hi - d_lo)
                a = _median([r - slope * d for d, r in obs])
                resid = sorted(r - (a + slope * d) for d, r in obs)
                p5 = resid[int(0.05 * (len(resid) - 1))]
                out = dict(a=a, b=slope, p5=p5, n=len(obs))
        self._fit_cache[b] = out
        return out

    def adverse_tail(self, sod, D, r):
        """True/False when the model can speak, None when it cannot."""
        if not D or r is None:
            return None
        f = self.fit(self.bucket(sod))
        if f is None:
            return None
        s = 1.0 if D > 0 else -1.0
        resid = s * r - (f['a'] + f['b'] * abs(D))
        return resid <= f['p5']


# ---------------------------------------------------------------------
# W2 detectors: the frozen detectors with ONE input substituted, or one
# threshold parameterised. a4() at threshold 2.0 must equal the frozen
# A4 on any input; a test pins that.
# ---------------------------------------------------------------------
def a4(f, z_thresh=2.0, resid_key='resid_tail_5pct'):
    if not SIG._ok(f.get('aggr_z'), f.get('opp_flip_z')):
        return 0
    fail = ((f.get(resid_key) is True) or
            (f.get('progress_ticks') is not None and
             f['progress_ticks'] <= 1))
    back = (f.get('returned_through_level') is True) or \
           (f.get('sweep_reclaimed_5s') is True)
    if f['aggr_z'] >= z_thresh and fail and back and f['opp_flip_z'] >= 1.0:
        return -f['aggr_dir']
    return 0


def w2_a1(f):
    g = dict(f, replenish_z=f.get('repl10_z'))
    return SIG.a1_absorption_reversal(g)


def w2_a4r(f):
    return a4(dict(f, resid_tail_5pct=None))


def w2_a4f(f):
    """Evaluated ONLY where the residual model can speak, so its
    population is 'windows with a fitted expectation', not A4r plus
    noise. Returns (direction, resid_only)."""
    if f.get('resid_tail_5pct') is None:
        return 0, False
    d = a4(f)
    if not d:
        return 0, False
    prog_ok = (f.get('progress_ticks') is not None and
               f['progress_ticks'] <= 1)
    return d, (not prog_ok)


def w2_a4_open(f, sod):
    if not (OPEN_WINDOW_ET[0] <= sod < OPEN_WINDOW_ET[1]):
        return 0
    if f.get('level_id') not in OPEN_LEVELS_W2:
        return 0
    return w2_a4r(f)


def w2_a4r_z15(f):
    return a4(dict(f, resid_tail_5pct=None), z_thresh=Z15)


def w2_a4r_hc(f):
    if f.get('aggr_z_hc') is None:
        return 0
    return a4(dict(f, resid_tail_5pct=None, aggr_z=f['aggr_z_hc']))


# ---------------------------------------------------------------------
# ARM B: frozen candle-only rules on the SAME approaches (reg 4.1)
# ---------------------------------------------------------------------
def arm_b1(bar, level_px, ad):
    """Rejection wick: wick beyond the level >= 50% of range AND close
    back on the approach side. Direction: away from the wick (-ad)."""
    _, o, h, l, c, _v = bar[:6]           # bars may carry t_close as [6]
    rng = h - l
    if rng <= 0:
        return 0
    wick = (h - level_px) if ad > 0 else (level_px - l)
    if wick <= 0:
        return 0
    back = (c < level_px) if ad > 0 else (c > level_px)
    return -ad if (wick / rng >= 0.5 and back) else 0


def arm_b2(bar1, bar2, level_px, ad):
    """Engulfing reclaim: bar1 closes THROUGH the level, bar2 closes back
    on the original side. Decision instant is bar2's close. -ad."""
    c1, c2 = bar1[4], bar2[4]
    through = (c1 > level_px) if ad > 0 else (c1 < level_px)
    back = (c2 < level_px) if ad > 0 else (c2 > level_px)
    return -ad if (through and back) else 0


# ---------------------------------------------------------------------
# per-instrument wave-two side state (never stored on the frozen st)
# ---------------------------------------------------------------------
class _W2State(object):
    def __init__(self):
        self.adds = dict(bid=collections.deque(), ask=collections.deque())
        self.execs = dict(bid=collections.deque(), ask=collections.deque())
        self.trades_hc = collections.deque()          # (t, px, sz, sign)
        self.resid = ResidualModel()
        self.bars = collections.deque(maxlen=8)       # (mkey,o,h,l,c,v,t_close)
        self.awaiting_b = []                          # arm-B registrations
        self.placebo_off = {}                         # level_id -> offset
        self.placebo_seed_session = None


def _mkey(t):
    day, sod = RUN.et_parts(t)
    return (day, int(sod // 60))


class Wave2Runner(PI.PilotRunner):
    """The pilot runner plus wave two. Overrides hooks only. mode='real'
    runs on the frozen level set; mode='placebo' replaces every level
    with its seeded offset (ARM-C) and otherwise changes nothing."""

    def __init__(self, capture_dir, mode='real', blind_from=PI.BLIND_FROM,
                 **kw):
        PI.PilotRunner.__init__(self, capture_dir, **kw)
        assert mode in ('real', 'placebo')
        self.mode = mode
        self.blind_from = blind_from
        self.w2 = {i: _W2State() for i in self.instruments}
        self.w2_fires = []
        self.w2_counts = collections.Counter()
        self.ledger['wave2'] = dict(version=WAVE2_VERSION, mode=mode,
                                    resid_model=RESID_MODEL)

    # ---- event hooks -------------------------------------------------
    def _on_depth_event(self, st, t, e):
        if e['action'] in ('ADD', 'UPDATE') and e['level'] < TOP_K:
            side = e['side'].lower()
            dq = self.w2[st.instrument].adds[side]
            dq.append((t, e['sz'] or 0.0))
            while dq and dq[0][0] < t - REPL_WINDOW_S - 0.5:
                dq.popleft()

    def _on_trade_event(self, st, t, e):
        w = self.w2[st.instrument]
        sign = 1 if e['aggr_inf'] == 'BUY' else \
            (-1 if e['aggr_inf'] == 'SELL' else 0)
        px, sz = e['px'], e['sz'] or 0.0
        if sign:
            side = 'ask' if sign > 0 else 'bid'
            book = st.book.ask if side == 'ask' else st.book.bid
            if any(abs(px - bp) < 1e-9 for bp, _ in book[:TOP_K]):
                dq = w.execs[side]
                dq.append((t, sz))
                while dq and dq[0][0] < t - REPL_WINDOW_S - 0.5:
                    dq.popleft()
            if e.get('aggr_conf') == 'HIGH':
                w.trades_hc.append((t, px, sz, sign))
                while w.trades_hc and w.trades_hc[0][0] < t - \
                        RUN.TRADE_RETAIN_S:
                    w.trades_hc.popleft()

    def _on_trade(self, st, t, px, sz, sign):
        before = st.bar
        PI.PilotRunner._on_trade(self, st, t, px, sz, sign)
        if before is not None and st.bar is not None and \
                st.bar[0] != before[0]:
            self._bar_closed(st, tuple(before) + (t,))

    # ---- baselines: the wave-two features mature like delta10 --------
    def _repl10(self, w, side, t):
        adds = sum(s for tt, s in w.adds[side] if tt > t - REPL_WINDOW_S)
        ex = sum(s for tt, s in w.execs[side] if tt > t - REPL_WINDOW_S)
        return adds / (ex + 1.0)

    def _observe_baselines(self, st, te):
        PI.PilotRunner._observe_baselines(self, st, te)
        if not st.ready:
            return
        w = self.w2[st.instrument]
        sod = RUN.sod_seconds(te)
        for side in ('bid', 'ask'):
            st.baseline.observe('repl10_' + side, sod,
                                self._repl10(w, side, te))
        D_hc, _ = SIG.aggr_delta(self._between(w.trades_hc,
                                               te - RUN.DECISION_S, te))
        st.baseline.observe('delta10_hc', sod, D_hc)
        _tr, D, _o, r, _b, _m = self._window_stats(st, te - RUN.DECISION_S,
                                                   te)
        w.resid.observe(sod, D, r)

    def _close_session(self, st):
        PI.PilotRunner._close_session(self, st)
        w = self.w2[st.instrument]
        w.resid.close_session()
        # a registration whose bar never closed inside its session is
        # expired, never carried into the next session's bars
        self.w2_counts['armb_expired'] += len(w.awaiting_b)
        w.awaiting_b = []
        w.bars.clear()

    # ---- ARM-C: placebo levels ----------------------------------------
    def _rebuild_levels(self, st):
        PI.PilotRunner._rebuild_levels(self, st)
        if self.mode != 'placebo' or not st.levels:
            return
        w = self.w2[st.instrument]
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

    # ---- the wave-two window ------------------------------------------
    def _on_window(self, st, ap, te, f):
        PI.PilotRunner._on_window(self, st, ap, te, f)
        w = self.w2[st.instrument]
        self.w2_counts['w2_windows'] += 1
        sod = RUN.sod_seconds(te)
        z = st.baseline.z
        side = ap.blocking                                   # 'ask'/'bid'
        repl10_z = z('repl10_' + side, sod, self._repl10(w, side, te))
        D_hc, _ = SIG.aggr_delta(self._between(w.trades_hc,
                                               te - RUN.DECISION_S, te))
        aggr_z_hc = z('delta10_hc', sod, ap.ad * D_hc)
        _tr, D, _o, r, _b, _m = self._window_stats(st, te - RUN.DECISION_S,
                                                   te)
        resid_tail = w.resid.adverse_tail(sod, D, r)
        f2 = dict(f, repl10_z=repl10_z, aggr_z_hc=aggr_z_hc,
                  resid_tail_5pct=resid_tail)
        for k in ('repl10_z', 'aggr_z_hc', 'resid_tail_5pct'):
            if f2[k] is None:
                self.w2_counts['none_' + k] += 1

        d = w2_a1(f2)
        if d:
            self._w2_fire(st, 'W2-A1', d, te, ap)
        d = w2_a4r(f2)
        if d:
            self._w2_fire(st, 'W2-A4r', d, te, ap)
        d, resid_only = w2_a4f(f2)
        if d:
            self._w2_fire(st, 'W2-A4f', d, te, ap, resid_only=resid_only,
                          model=RESID_MODEL)
        d = w2_a4_open(f2, sod)
        if d:
            self._w2_fire(st, 'W2-A4-OPEN', d, te, ap)
        d = w2_a4r_z15(f2)
        if d:
            self._w2_fire(st, 'W2-A4r-z15', d, te, ap)
        d = w2_a4r_hc(f2)
        if d:
            self._w2_fire(st, 'W2-A4r-HC', d, te, ap)
        # ARM-B registration on the approach's first window
        if ap.windows == 1:
            self._register_arm_b(st, ap)

    def _w2_fire(self, st, fam, direction, t, ap, **extra):
        self.w2_counts[fam] += 1
        rec = dict(instrument=st.instrument, session=st.session,
                   family=fam, run=st.run_id, direction=direction,
                   t=round(t, 3), level=ap.level_id, approach=ap.id,
                   state=ap.wall_state, mode=self.mode)
        rec.update(extra)
        self.w2_fires.append(rec)

    # ---- ARM-B --------------------------------------------------------
    def _register_arm_b(self, st, ap):
        w = self.w2[st.instrument]
        self.w2_counts['armb_registered'] += 1
        reg = dict(ap=ap, mkey=_mkey(ap.t0), level_px=ap.level_px,
                   ad=ap.ad, b2_pending=None)
        # the approach's bar may already have closed (t0 late in the
        # minute, first window 10 s later): evaluate from the cache
        for bar in list(w.bars):
            if bar[0] == reg['mkey']:
                if not self._eval_arm_b(st, reg, bar):
                    w.awaiting_b.append(reg)      # B2 pending
                return
        w.awaiting_b.append(reg)

    def _bar_closed(self, st, bar):
        w = self.w2[st.instrument]
        w.bars.append(bar)
        keep = []
        for reg in w.awaiting_b:
            done = self._eval_arm_b(st, reg, bar)
            if not done:
                keep.append(reg)
        w.awaiting_b = keep

    def _eval_arm_b(self, st, reg, bar):
        """Returns True when this registration is finished. bar[6] is
        the first print after the bar's minute ended, i.e. the earliest
        instant the closed bar was knowable; fires and their markouts
        are stamped there, never at the bar's open."""
        ap, L, ad = reg['ap'], reg['level_px'], reg['ad']
        t_close = bar[6]
        if reg['b2_pending'] is not None:
            self.w2_counts['armb_evaluated_b2'] += 1
            d = arm_b2(reg['b2_pending'], bar, L, ad)
            if d:
                self._w2_fire(st, 'ARM-B2', d, t_close, ap)
            return True
        if bar[0] != reg['mkey']:
            if bar[0] < reg['mkey']:
                return False                      # not there yet
            self.w2_counts['armb_expired'] += 1
            return True                           # its bar never closed
        self.w2_counts['armb_evaluated_b1'] += 1
        d = arm_b1(bar, L, ad)
        if d:
            self._w2_fire(st, 'ARM-B1', d, t_close, ap)
        c = bar[4]
        through = (c > L) if ad > 0 else (c < L)
        if through:
            reg['b2_pending'] = bar               # wait for the next bar
            return False
        return True


# ---------------------------------------------------------------------
# report
# ---------------------------------------------------------------------
def _marks(runner, pop):
    out = {}
    for h in PI.MARKOUT_S:
        vals = []
        for e in pop:
            m = runner.markout(e['instrument'], e.get('run'), e['t'], h)
            if m is not None:
                vals.append(e['direction'] * m)
        out['%gs' % h] = PI._describe(vals)
    return out


def family_block(runner, fam, blind_from):
    fires = [x for x in runner.w2_fires if x['family'] == fam]
    events = PI.dedup_fires(fires, PI.EVENT_COOLDOWN_S)
    vis = [e for e in events if not PI._is_blind(e['session'], blind_from)]
    withheld = [e for e in events if PI._is_blind(e['session'], blind_from)]
    sig = [e for e in vis if e['is_signal_source']]
    blk = dict(raw_fires=len(fires), distinct_events=len(events),
               events_visible=len(vis), events_withheld=len(withheld),
               signal_source_events=len(sig),
               by_session=dict(sorted(collections.Counter(
                   e['session'] for e in events).items())),
               markouts_signal_source=_marks(runner, sig))
    if fam == 'W2-A4f':
        blk['resid_only_fires'] = sum(1 for x in fires if x.get('resid_only'))
        blk['model'] = RESID_MODEL
    return blk


def run_wave2(capture_dir, mode='real', blind_from=PI.BLIND_FROM,
              max_sessions=None):
    r = Wave2Runner(capture_dir, mode=mode, blind_from=blind_from,
                    max_sessions=max_sessions)
    led = r.run()
    rep = dict(wave2=WAVE2_VERSION, mode=mode, blind_from=blind_from,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               wave_one_raw_fires=len(led.get('fires', [])),
               w2_windows=r.w2_counts['w2_windows'],
               w2_input_availability={
                   k: v for k, v in r.w2_counts.items()
                   if k.startswith('none_')},
               arm_b=dict(registered=r.w2_counts['armb_registered'],
                          evaluated_b1=r.w2_counts['armb_evaluated_b1'],
                          evaluated_b2=r.w2_counts['armb_evaluated_b2'],
                          expired=r.w2_counts['armb_expired']),
               families={fam: family_block(r, fam, blind_from)
                         for fam in FAMILIES},
               fires=r.w2_fires,
               not_in_this_version=['CAUSAL_SWING level comparison '
                                    '(registration 4.3)'],
               resid_model=RESID_MODEL)
    return rep, r


def paired_summary(real, placebo, blind_from):
    """Per family: median primary-horizon markout on real levels minus
    on placebo levels, on visible signal-source events, plus the median
    of per-session differences where both exist. Descriptive only."""
    pk = '%gs' % PI.PRIMARY_MARKOUT_S
    out = {}
    for fam in FAMILIES:
        a = real['families'][fam]['markouts_signal_source'].get(pk, {})
        b = placebo['families'][fam]['markouts_signal_source'].get(pk, {})
        out[fam] = dict(
            real_n=a.get('n', 0), placebo_n=b.get('n', 0),
            real_median=a.get('median'), placebo_median=b.get('median'),
            difference=(round(a['median'] - b['median'], 3)
                        if a.get('n') and b.get('n') else None),
            real_ci95_median=a.get('ci95_median'),
            placebo_ci95_median=b.get('ci95_median'))
    return out


def text_summary(rep, paired=None):
    L = ['%s  mode=%s  blind_from=%s' % (rep['wave2'], rep['mode'],
                                        rep['blind_from']),
         'sessions: %s' % ', '.join(rep['sessions_inspected']),
         'wave-one raw fires (unchanged, for reference): %d'
         % rep['wave_one_raw_fires'],
         'w2 windows: %d   input unavailable (None) on: %s'
         % (rep.get('w2_windows', 0), rep['w2_input_availability']),
         'arm B: %s' % rep.get('arm_b'),
         '']
    pk = '%gs' % PI.PRIMARY_MARKOUT_S
    L.append('%-12s %5s %6s %7s %7s %5s  %s' % (
        'family', 'raw', 'events', 'visible', 'withhld', 'NQ', 'markout@%s'
        % pk))
    for fam in FAMILIES:
        b = rep['families'][fam]
        m = b['markouts_signal_source'].get(pk, {})
        ms = ('n=%d med=%+.1f ci=%s' % (m['n'], m['median'],
                                        m.get('ci95_median'))
              if m.get('n') else 'n=0')
        L.append('%-12s %5d %6d %7d %7d %5d  %s' % (
            fam, b['raw_fires'], b['distinct_events'], b['events_visible'],
            b['events_withheld'], b['signal_source_events'], ms))
    a4f = rep['families']['W2-A4f']
    L.append('')
    L.append('W2-A4f resid-only fires: %d   model: %s'
             % (a4f.get('resid_only_fires', 0), a4f.get('model')))
    L.append('not in this version: %s' % rep['not_in_this_version'])
    if paired:
        L.append('')
        L.append('PAIRED real - placebo, primary horizon, visible NQ events:')
        for fam, p in paired.items():
            L.append('  %-12s real n=%-3d med=%-7s  placebo n=%-3d med=%-7s'
                     '  diff=%s' % (fam, p['real_n'], p['real_median'],
                                    p['placebo_n'], p['placebo_median'],
                                    p['difference']))
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    out = argv[argv.index('--out') + 1] if '--out' in argv else None
    ms = (int(argv[argv.index('--max-sessions') + 1])
          if '--max-sessions' in argv else None)
    blind = PI.BLIND_FROM
    if '--blind-from' in argv:
        blind = PI.parse_blind_from(argv[argv.index('--blind-from') + 1])
    both = '--both' in argv
    mode = 'placebo' if '--placebo' in argv else 'real'
    try:
        rep, _r = run_wave2(d, mode=mode, blind_from=blind, max_sessions=ms)
        rep_p = None
        if both:
            rep_p, _rp = run_wave2(d, mode='placebo', blind_from=blind,
                                   max_sessions=ms)
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        # 2026-09-22: this pass printed a clean report of zero fires on
        # zero sessions from an unplugged drive. Never again: no report.
        print('STOPPED: %s' % exc)
        return 2
    paired = None
    if both:
        paired = paired_summary(rep, rep_p, blind)
        rep = dict(real=rep, placebo=rep_p, paired=paired,
                   wave2=rep['wave2'], mode='both', blind_from=blind,
                   sessions_inspected=rep['sessions_inspected'],
                   wave_one_raw_fires=rep['wave_one_raw_fires'],
                   w2_windows=rep['w2_windows'],
                   w2_input_availability=rep['w2_input_availability'],
                   arm_b=rep['arm_b'],
                   families=rep['families'],
                   not_in_this_version=rep['not_in_this_version'])
    print(text_summary(rep, paired))
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-two report -> %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
