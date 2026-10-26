#!/usr/bin/env python3
"""mrofyt_exitstudy.py - MROF-YT-W5-EXIT-1.0

MROF_YT_WAVE5_EXIT_REGISTRATION.md turned into running code. The
question an intraday trader asks when a trade is working: price has run
20 points my way and momentum looks like it is dying -- take it, or
hold? This wave measures it on the tape, for EVERY run on the tape, not
only for the waves' own entries.

    in a run      on the frozen 10 s grid, price is 20+ points (80 ticks)
                  from its 30-minute extreme and within 5 points of the
                  best it has made since, in that direction
    hold value    what holding is worth from that moment, by a plain
                  reference rule: a 10-point trailing stop from the best
                  mid since, at most 30 minutes, mid-to-mid. Exiting now
                  is worth 0 by definition, and both choices pay one exit,
                  so costs cancel.
    eight signs   X1 DELTA_FADE  X2 TAPE_SLOW  X3 ABSORPTION  X4 OTHER_SIDE
                  X5 BOOK_TURNS  X6 STALL  X7 CLIMAX  X8 BIG_LOT_AGAINST
    a good exit   holding after the sign is worth LESS than holding at an
    sign          ordinary in-run moment of the same hour and direction
                  (negative lift), across sessions, after Holm over eight

It also writes the half-life curves: for every wave-one and wave-three
family, and for in-run moments themselves, the average move in the
signal's direction at 5 s ... 3 h against the same hour's baseline, so a
signal's natural holding time is measured, not guessed.

    python3 mrofyt_exitstudy.py "<capture>" --out w5.json \\
            --nominated-out w5_nominated.json
    python3 mrofyt_exitstudy.py "<capture>" --evaluate w5_nominated.json \\
            --out w5_eval_dev.json            # DEV only: reproduces
    python3 mrofyt_exitstudy.py "<capture>" --evaluate w5_nominated.json \\
            --unblind --out w5_eval.json      # CHECKPOINT ONLY

The runner subclasses wave four's, which subclasses wave three's and the
pilot's; hooks only. DEV sessions (<= 20260918) only, unless --unblind
with --evaluate, which announces itself and exposes permanently.

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import copy
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_discover as DI
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W5_VERSION = 'MROF-YT-W5-EXIT-1.0'
REGISTRATION = 'MROF_YT_WAVE5_EXIT_REGISTRATION.md'
DEV_END = BM.DEV_END
TICK = SIG.TICK

# registration 1: being in a run
RUN_WINDOW_S = 1800
RUN_MIN_GRID = 171                   # of the 181 grid ticks in 30 minutes
RUN_GAIN_TICKS = 80.0                # 20 points from the 30-minute extreme
NEAR_BEST_TICKS = 20.0               # within 5 points of the run's best

# registration 2: the reference hold
TRAIL_TICKS = 40.0                   # 10-point trailing stop
HOLD_LIMIT_S = 1800.0

# registration 3: the eight signs
SIGNS = ('X1', 'X2', 'X3', 'X4', 'X5', 'X6', 'X7', 'X8')
SIGN_NAMES = dict(X1='DELTA_FADE', X2='TAPE_SLOW', X3='ABSORPTION',
                  X4='OTHER_SIDE', X5='BOOK_TURNS', X6='STALL',
                  X7='CLIMAX', X8='BIG_LOT_AGAINST')
TAPE_LOOKBACK = 30                   # grid ticks (5 minutes)
TAPE_MIN = 25
TAPE_SLOW_RATIO = 0.5
ABSORB_Q = 0.80                      # with-run 10 s delta, top quintile
ABSORB_RESP_MAX = 1.0                # ...and at most 1 tick of progress
OTHER_Q = 0.90                       # against-run 10 s delta, top decile
BOOK_Q = 0.80                        # against-run book imbalance, top quintile
STALL_S = 120.0
CLIMAX_LOOKBACK = 6                  # previous grid ticks (1 minute)
CLIMAX_Q = 0.95                      # 10 s trade count, top 5 % of the grid
CLIMAX_DROP = 0.5
CLIMAX_FRESH_S = 60.0
BIGLOT_Q = 0.99                      # largest single trade per 10 s

# registration 4-6
COOLDOWN_S = 300.0
MIN_EVENTS = 30
MIN_SESSIONS = 6
MIN_HALF = 10
NOMINATE_MAX = 3
NOMINATE_P = 0.05
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT
HORIZONS = (5, 30, 60, 120, 300, 600, 1800, 3600, 7200, 10800)


# ---------------------------------------------------------------------
# pure pieces: run state, the reference hold, the signs
# ---------------------------------------------------------------------
def run_state(entries, key, mid):
    """entries: [(key, mid)] of this recording run's grid over the last
    30 minutes INCLUDING the current tick (mid may be None). Returns
    (direction, gain_ticks, stall_s, anchor_key) or (0, None, None,
    None). Direction +1: up 20+ points from the window's low and within
    5 points of the best since that low; -1 mirrored."""
    pts = [(k, m) for k, m in entries if m is not None and
           k >= key - RUN_WINDOW_S]
    if mid is None or len(pts) < RUN_MIN_GRID:
        return 0, None, None, None
    for d in (1, -1):
        ext = min(d * m for _k, m in pts)
        anchor = max(k for k, m in pts if d * m == ext)   # latest extreme
        since = [(k, m) for k, m in pts if k >= anchor]
        best = max(d * m for _k, m in since)
        t_best = min(k for k, m in since if d * m == best)
        gain = (d * mid - ext) / TICK
        if gain >= RUN_GAIN_TICKS and (best - d * mid) / TICK <= \
                NEAR_BEST_TICKS:
            return d, gain, key - t_best, anchor
    return 0, None, None, None


def trail_hold(ts, ps, i, d, trail_ticks=TRAIL_TICKS, limit_s=HOLD_LIMIT_S):
    """The reference hold from compressed index i in direction d:
    exit at the first mid `trail_ticks` worse than the best mid since
    i; at most `limit_s`. Returns (outcome, value_ticks, seconds) with
    outcome TRAIL / TIMEOUT / UNRESOLVED (value None)."""
    t0, p0 = ts[i], ps[i]
    best = p0
    t_end = t0 + limit_s
    lim = trail_ticks * TICK - 1e-9
    n = len(ps)
    j = i + 1
    while j < n and ts[j] <= t_end:
        x = ps[j]
        if d * (x - best) > 0:
            best = x
        elif d * (best - x) >= lim:
            return 'TRAIL', d * (x - p0) / TICK, ts[j] - t0
        j += 1
    if ts[-1] < t_end:
        return 'UNRESOLVED', None, None
    k = bisect.bisect_right(ts, t_end) - 1
    return 'TIMEOUT', d * (ps[k] - p0) / TICK, ts[k] - t0


def sign_values(g, d):
    """The raw quantities the quantile signs are cut on, for run
    direction d: with-run 10 s delta, against-run 10 s delta, against-run
    book imbalance."""
    D = g.get('D')
    bi3 = g.get('bi3')
    return dict(absorb=None if D is None else d * D,
                other=None if D is None else -d * D,
                book=None if bi3 is None else -d * bi3)


def signs_at(g, d, cuts):
    """{sign: True/False/None} at in-run record g (None: input missing
    or cut unknown)."""
    v = sign_values(g, d)
    out = {}
    D60 = g.get('D60')
    out['X1'] = None if D60 is None else d * D60 <= 0
    pm = g.get('n10_prev_mean')
    out['X2'] = None if (pm is None or pm <= 0 or g.get('n10') is None) \
        else g['n10'] <= TAPE_SLOW_RATIO * pm
    c = cuts.get('absorb')
    r = g.get('resp')
    out['X3'] = None if (c is None or v['absorb'] is None or r is None) \
        else (v['absorb'] >= c and d * r <= ABSORB_RESP_MAX)
    c = cuts.get('other')
    out['X4'] = None if (c is None or v['other'] is None) \
        else v['other'] >= c
    c = cuts.get('book')
    out['X5'] = None if (c is None or v['book'] is None) else v['book'] >= c
    s = g.get('stall_s')
    out['X6'] = None if s is None else s >= STALL_S
    c = cuts.get('climax')
    mx = g.get('n10_prev6_max')
    out['X7'] = None if (c is None or mx is None or g.get('n10') is None
                         or s is None) else (
        mx >= c and g['n10'] <= CLIMAX_DROP * mx and s <= CLIMAX_FRESH_S)
    c = cuts.get('biglot')
    lot = g.get('lot_dn') if d > 0 else g.get('lot_up')
    out['X8'] = None if (c is None or lot is None) else lot >= c
    return out


def _q(vals, p):
    vals = sorted(vals)
    if len(vals) < 20:
        return None
    return vals[int(p * (len(vals) - 1))]


def quantile_cuts(recs, moments):
    """Cut-points on ONE instrument's DEV sample. `moments` are the
    in-run (record index, direction) pairs; the climax and big-lot cuts
    use every grid record."""
    vals = collections.defaultdict(list)
    for k, d in moments:
        for name, x in sign_values(recs[k], d).items():
            if x is not None:
                vals[name].append(x)
    n10 = [g['n10'] for g in recs if g.get('n10') is not None]
    lots = [max(g.get('lot_up') or 0.0, g.get('lot_dn') or 0.0)
            for g in recs if g.get('lot_up') is not None]
    return dict(absorb=_q(vals['absorb'], ABSORB_Q),
                other=_q(vals['other'], OTHER_Q),
                book=_q(vals['book'], BOOK_Q),
                climax=_q(n10, CLIMAX_Q), biglot=_q(lots, BIGLOT_Q))


# ---------------------------------------------------------------------
# the runner: wave four's plus run state and the sign inputs
# ---------------------------------------------------------------------
class _W5Hist(object):
    def __init__(self):
        self.reset(None, None)

    def reset(self, run, session):
        self.run, self.session = run, session
        self.entries = collections.deque()       # (key, mid, n10)

    def add(self, key, mid, n10):
        self.entries.append((key, mid, n10))
        while self.entries and self.entries[0][0] < key - RUN_WINDOW_S:
            self.entries.popleft()


class ExitRunner(DI.DiscoverRunner):
    """Wave four's runner plus, on every grid record: the 10 s trade
    count, the largest single trade each side, the top-3 book imbalance,
    the run state and the history the signs need. Hooks only."""

    def __init__(self, capture_dir, unblind=False, **kw):
        DI.DiscoverRunner.__init__(self, capture_dir, unblind=unblind, **kw)
        self.w5hist = {i: _W5Hist() for i in self.instruments}
        self.ledger['wave5'] = dict(version=W5_VERSION)

    def _close_session(self, st):
        DI.DiscoverRunner._close_session(self, st)
        self.w5hist[st.instrument].reset(None, None)

    def _mark_run(self, st):
        mark = DI.DiscoverRunner._mark_run(self, st)
        mark['w5'] = copy.deepcopy(self.w5hist[st.instrument])
        return mark

    def _unwind_run(self, st, mark):
        DI.DiscoverRunner._unwind_run(self, st, mark)
        self.w5hist[st.instrument] = mark['w5']

    def _observe_baselines(self, st, te):
        n0 = len(self.grid)
        DI.DiscoverRunner._observe_baselines(self, st, te)
        if len(self.grid) == n0:
            return
        g = self.grid[-1]
        tr = self._between(st.trades, te - RUN.DECISION_S, te)
        g['n10'] = float(len(tr))
        g['lot_up'] = max([sz for _t, _p, sz, s in tr if s > 0] or [0.0])
        g['lot_dn'] = max([sz for _t, _p, sz, s in tr if s < 0] or [0.0])
        g['bi3'] = st.book.bi(3)
        h = self.w5hist[st.instrument]
        if h.run != g['run'] or h.session != st.session:
            h.reset(g['run'], st.session)
        key = int(round(te))
        prev = list(h.entries)
        last = [x[2] for x in prev[-TAPE_LOOKBACK:] if x[2] is not None]
        g['n10_prev_mean'] = (sum(last) / len(last)) if \
            len(last) >= TAPE_MIN else None
        six = [x[2] for x in prev[-CLIMAX_LOOKBACK:] if x[2] is not None]
        g['n10_prev6_max'] = max(six) if len(six) == CLIMAX_LOOKBACK \
            else None
        h.add(key, g.get('mid'), g['n10'])
        d, gain, stall, anchor = run_state(
            [(k, m) for k, m, _n in h.entries], key, g.get('mid'))
        g['run_dir'] = d
        g['run_gain'] = gain
        g['stall_s'] = stall
        g['run_anchor'] = anchor


# ---------------------------------------------------------------------
# scoring a finished runner
# ---------------------------------------------------------------------
def _paths(r):
    return {k: BM.compress(ts, ps) for k, (ts, ps) in r.series.items()
            if len(ts)}


def hold_values(r, paths=None):
    """[None or (outcome, value_ticks, seconds)] aligned with r.grid; an
    answer only for in-run records (run_dir != 0)."""
    paths = _paths(r) if paths is None else paths
    out = []
    for g in r.grid:
        d = g.get('run_dir') or 0
        key = (g['instrument'], g['run'])
        if not d or key not in paths:
            out.append(None)
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, g['t']) - 1
        out.append(None if i < 0 else trail_hold(ts, ps, i, d))
    return out


class ExitData(object):
    """One instrument's grid records and hold values, with the hour
    cells of the baseline hold and the DEV halves."""

    def __init__(self, recs, holds, sessions=None):
        self.recs, self.holds = recs, holds
        self.sessions = sorted(sessions if sessions is not None else
                               {g['session'] for g in recs})
        half = (len(self.sessions) + 1) // 2
        self.half_of = {s: (0 if i < half else 1)
                        for i, s in enumerate(self.sessions)}
        self.moments = [(k, g['run_dir']) for k, g in enumerate(recs)
                        if g.get('run_dir')]
        cell = collections.defaultdict(lambda: [0.0, 0])
        for k, d in self.moments:
            h = holds[k]
            if h is None or h[0] == 'UNRESOLVED':
                continue
            c = cell[(recs[k]['hour'], d)]
            c[0] += h[1]
            c[1] += 1
        self.cells = {k: v[0] / v[1] for k, v in cell.items() if v[1]}

    def baseline(self):
        vals = [self.holds[k][1] for k, _d in self.moments
                if self.holds[k] and self.holds[k][0] != 'UNRESOLVED']
        return dict(moments=len(self.moments), resolved=len(vals),
                    mean_hold_ticks=round(sum(vals) / len(vals), 3)
                    if vals else None,
                    mean_hold_points=round(sum(vals) / len(vals) / 4.0, 3)
                    if vals else None)


def sign_events(ds, sign, cuts):
    """In-run moments where the sign fires, de-duplicated with an
    anchored 300 s cooldown per (session, direction)."""
    hits = []
    for k, d in ds.moments:
        if signs_at(ds.recs[k], d, cuts).get(sign):
            hits.append((k, d))
    hits.sort(key=lambda kd: (ds.recs[kd[0]]['session'], ds.recs[kd[0]]['t']))
    anchor, out = {}, []
    for k, d in hits:
        g = ds.recs[k]
        a = anchor.get((g['session'], d))
        if a is None or g['t'] - a > COOLDOWN_S:
            anchor[(g['session'], d)] = g['t']
            out.append((k, d))
    return out


def sign_stats(ds, events):
    rows = []
    for k, d in events:
        h = ds.holds[k]
        if h is None or h[0] == 'UNRESOLVED':
            continue
        exp = ds.cells.get((ds.recs[k]['hour'], d))
        if exp is None:
            continue
        rows.append((ds.recs[k]['session'], h[1], exp, h[1]))

    def pack(st):
        return dict(n=st['n'], sessions=st.get('sessions', 0),
                    mean_hold_ticks=st.get('hit'),
                    baseline_hold_ticks=st.get('baseline'),
                    lift_ticks=st.get('lift'),
                    lift_points=None if st.get('lift') is None
                    else round(st['lift'] / 4.0, 3),
                    t=st.get('t'), p=st.get('p'), ci95=st.get('ci95'))
    out = pack(DI.cluster_stats(rows))
    halves = []
    for hf in (0, 1):
        hs = DI.cluster_stats([x for x in rows if ds.half_of.get(x[0]) == hf])
        halves.append(dict(n=hs['n'], lift_ticks=hs.get('lift')))
    out['halves'] = halves
    out['both_halves_negative'] = all(
        x['n'] >= MIN_HALF and x['lift_ticks'] is not None and
        x['lift_ticks'] < 0 for x in halves)
    return out


def study(ds, cuts):
    """The eight tests on one instrument, Holm over the eight."""
    tests = []
    for s in SIGNS:
        ev = sign_events(ds, s, cuts)
        st = sign_stats(ds, ev)
        st.update(sign=s, name=SIGN_NAMES[s], events=len(ev))
        tests.append(st)
    rej = BM.holm([x.get('p') for x in tests], HOLM_ALPHA)
    for x, rj in zip(tests, rej):
        enough = x['n'] >= MIN_EVENTS and x['sessions'] >= MIN_SESSIONS
        x['survives_holm'] = bool(rj and enough)
        if not enough:
            x['status'] = 'NOT TESTED'
        elif rj and x['lift_ticks'] < 0:
            x['status'] = 'EXIT SIGN'          # holding after it is worse
        elif rj and x['lift_ticks'] > 0:
            x['status'] = 'HOLD SIGN'          # holding after it is better
        else:
            x['status'] = 'NO SIGNAL'
    return tests


def nominate(tests):
    """At most three: Holm survivors with negative lift first, then by
    t (most negative); each needs p <= 0.05, both halves negative and
    30+ events on 6+ sessions."""
    ok = [x for x in tests if x.get('p') is not None and
          x['p'] <= NOMINATE_P and x['lift_ticks'] is not None and
          x['lift_ticks'] < 0 and x['both_halves_negative'] and
          x['n'] >= MIN_EVENTS and x['sessions'] >= MIN_SESSIONS]
    ok.sort(key=lambda x: (x['status'] != 'EXIT SIGN', x['t'], x['sign']))
    return ok[:NOMINATE_MAX]


# ---------------------------------------------------------------------
# half-life curves (descriptive)
# ---------------------------------------------------------------------
def _grid_markout_cells(r, horizons=HORIZONS):
    """{(instrument, hour): {h: mean up-markout ticks}} over grid ticks."""
    acc = collections.defaultdict(lambda: collections.defaultdict(
        lambda: [0.0, 0]))
    for g in r.grid:
        for hz in horizons:
            m = r.markout(g['instrument'], g['run'], g['t'], hz)
            if m is None:
                continue
            a = acc[(g['instrument'], g['hour'])][hz]
            a[0] += m
            a[1] += 1
    return {k: {hz: (v[0] / v[1]) for hz, v in per.items() if v[1]}
            for k, per in acc.items()}


def curve(r, events, cells, horizons=HORIZONS):
    """events: [dict(instrument, run, t, direction, session)]. Mean move
    in the event's direction and the same over its hour's baseline."""
    rows = []
    for hz in horizons:
        n = 0
        s_raw = s_lift = 0.0
        ses = set()
        for e in events:
            m = r.markout(e['instrument'], e.get('run'), e['t'], hz)
            if m is None:
                continue
            hour = int(RUN.sod_seconds(e['t']) // 3600)
            base = cells.get((e['instrument'], hour), {}).get(hz)
            if base is None:
                continue
            d = e['direction']
            n += 1
            s_raw += d * m
            s_lift += d * (m - base)
            ses.add(e['session'])
        rows.append(dict(horizon_s=hz, n=n, sessions=len(ses),
                         move_points=round(s_raw / n / 4.0, 3) if n else None,
                         lift_points=round(s_lift / n / 4.0, 3) if n
                         else None))
    return rows


def half_life(r, led, by_inst, cuts_by_inst, horizons=HORIZONS):
    cells = _grid_markout_cells(r, horizons)
    fams = collections.defaultdict(list)
    for e in PI.dedup_fires(led.get('fires', []), PI.EVENT_COOLDOWN_S):
        fams[('wave1', e['family'], e['instrument'])].append(e)
    for e in PI.dedup_fires(r.w3_fires, PI.EVENT_COOLDOWN_S):
        fams[('wave3', e['family'], e['instrument'])].append(e)
    for inst, ds in by_inst.items():
        mom = []
        for k, d in ds.moments:
            g = ds.recs[k]
            mom.append(dict(instrument=inst, run=g['run'], t=g['t'],
                            direction=d, session=g['session']))
        fams[('wave5', 'IN_RUN', inst)] = mom[::3]      # every 30 s
        for s in SIGNS:
            fams[('wave5', s, inst)] = [
                dict(instrument=inst, run=ds.recs[k]['run'],
                     t=ds.recs[k]['t'], direction=d,
                     session=ds.recs[k]['session'])
                for k, d in sign_events(ds, s, cuts_by_inst[inst])]
    out = []
    for (wave, fam, inst), evs in sorted(fams.items()):
        if not evs:
            continue
        out.append(dict(wave=wave, family=fam, instrument=inst,
                        events=len(evs), curve=curve(r, evs, cells,
                                                     horizons)))
    return out


# ---------------------------------------------------------------------
# the two modes
# ---------------------------------------------------------------------
def _by_inst(r, holds, keep=None):
    by = collections.defaultdict(lambda: ([], []))
    for g, h in zip(r.grid, holds):
        if keep is not None and not keep(g['session']):
            continue
        by[g['instrument']][0].append(g)
        by[g['instrument']][1].append(h)
    return {inst: ExitData(recs, hh) for inst, (recs, hh) in by.items()}


def _registration_block():
    return dict(run=dict(window_s=RUN_WINDOW_S, gain_ticks=RUN_GAIN_TICKS,
                         near_best_ticks=NEAR_BEST_TICKS),
                hold=dict(trail_ticks=TRAIL_TICKS, limit_s=HOLD_LIMIT_S,
                          basis='mid-to-mid; exit-now is 0; costs cancel'),
                cooldown_s=COOLDOWN_S, n_tests=len(SIGNS))


def run_study(capture_dir, max_sessions=None):
    r = ExitRunner(capture_dir, max_sessions=max_sessions)
    led = r.run()
    holds = hold_values(r)
    by = _by_inst(r, holds)
    rep = dict(wave5=W5_VERSION, registration=REGISTRATION, mode='study',
               dev_end=DEV_END, runner=led['runner'],
               outcomes_wave_one=led['outcomes'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               rules=_registration_block())
    cuts = {inst: quantile_cuts(ds.recs, ds.moments) for inst, ds in
            by.items()}
    rep['cuts'] = cuts
    rep['instruments'] = {}
    for inst, ds in sorted(by.items()):
        rep['instruments'][inst] = dict(
            grid_ticks=len(ds.recs), baseline_hold=ds.baseline(),
            halves=[[s for s in ds.sessions if ds.half_of[s] == h]
                    for h in (0, 1)],
            tests=study(ds, cuts[inst]))
    nominated = []
    if PRIMARY in rep['instruments']:
        for x in nominate(rep['instruments'][PRIMARY]['tests']):
            nominated.append(dict(sign=x['sign'], name=x['name'],
                                  status=x['status'], cuts=cuts,
                                  dev=dict((k, x.get(k)) for k in
                                           ('n', 'sessions', 'lift_ticks',
                                            't', 'p', 'ci95', 'halves'))))
    rep['nominated'] = nominated
    rep['half_life'] = half_life(r, led, by, cuts)
    return rep, nominated, r


def run_evaluate(capture_dir, frozen, unblind=False, max_sessions=None):
    r = ExitRunner(capture_dir, unblind=unblind, max_sessions=max_sessions)
    led = r.run()
    holds = hold_values(r)
    if unblind:
        keep = lambda s: s > DEV_END          # noqa: E731
        which = 'validation (> %s)' % DEV_END
    else:
        keep = lambda s: s <= DEV_END         # noqa: E731
        which = 'DEV (<= %s), a reproduction check' % DEV_END
    by = _by_inst(r, holds, keep)
    rep = dict(wave5=W5_VERSION, registration=REGISTRATION, mode='evaluate',
               unblind=unblind, evaluated_on=which, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({g['session'] for g in r.grid
                                          if keep(g['session'])}),
               signs=[])
    for fr in frozen:
        per = {}
        for inst, ds in by.items():
            c = fr['cuts'].get(inst)
            if c is None:
                continue
            ev = sign_events(ds, fr['sign'], c)
            st = sign_stats(ds, ev)
            st['events'] = len(ev)
            per[inst] = st
        rep['signs'].append(dict(sign=fr['sign'], name=fr.get('name'),
                                 result=per))
    ps = [x['result'].get(PRIMARY, {}).get('p') for x in rep['signs']]
    rej = BM.holm(ps, HOLM_ALPHA)
    for x, rj in zip(rep['signs'], rej):
        s = x['result'].get(PRIMARY, {})
        if s.get('n', 0) < MIN_EVENTS:
            v = 'NOT TESTED'
        elif rj and s.get('lift_ticks', 0) < 0 and s.get('ci95') and \
                s['ci95'][1] < 0:
            v = 'PROMISING'
        else:
            v = 'NO SIGNAL'
        x['verdict'] = v if unblind else v + ' (DEV reproduction, not a ' \
                                             'verdict)'
    return rep, r


def write_exposure_on_unblind(rep, path):
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
                         exposed_by=W5_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W5_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W5_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W5_VERSION)
    days = sorted(by.values(), key=lambda d: d['session'])
    json.dump(dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded, which is permanent.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)


# ---------------------------------------------------------------------
# text
# ---------------------------------------------------------------------
def _fmt(x, f='%+.2f'):
    return '-' if x is None else f % x


def text_study(rep):
    lines = ['%s  study  registration=%s' % (rep['wave5'],
                                             rep['registration']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED (validation, > %s): %s' % (
                 rep['dev_end'], ', '.join(rep['sessions_refused']) or '-'),
             'in a run = 20+ pts from the 30-min extreme, within 5 pts of '
             'the best; hold = 10-pt trailing stop, 30 min max, mid-to-mid;'
             ' exit now = 0', '']
    for inst, x in rep['instruments'].items():
        b = x['baseline_hold']
        lines.append('%s: %d grid ticks, %d in-run moments; holding with the '
                     '10-pt trail from an in-run moment is worth %s pts on '
                     'average' % (inst, x['grid_ticks'], b['moments'],
                                  _fmt(b['mean_hold_points'])))
        lines.append('  %-4s %-16s %5s %4s %9s %9s %9s %7s %8s  %s' % (
            'sign', 'name', 'n', 'ses', 'hold', 'base', 'lift', 't', 'p',
            'status'))
        for t_ in x['tests']:
            lines.append('  %-4s %-16s %5d %4d %9s %9s %9s %7s %8s  %s' % (
                t_['sign'], t_['name'], t_['n'], t_['sessions'],
                _fmt(None if t_['mean_hold_ticks'] is None
                     else t_['mean_hold_ticks'] / 4.0),
                _fmt(None if t_['baseline_hold_ticks'] is None
                     else t_['baseline_hold_ticks'] / 4.0),
                _fmt(t_['lift_points']), _fmt(t_['t'], '%.2f'),
                _fmt(t_['p'], '%.4f'), t_['status']))
        lines.append('  (hold, base, lift in points; negative lift = '
                     'holding after the sign is worse = an exit sign)')
        lines.append('')
    lines.append('NOMINATED for validation (max %d): %d' % (
        NOMINATE_MAX, len(rep['nominated'])))
    for n in rep['nominated']:
        d = n['dev']
        lines.append('  %s %s  [%s]  n=%s ses=%s lift=%s ticks t=%s p=%s' % (
            n['sign'], n['name'], n['status'], d['n'], d['sessions'],
            d['lift_ticks'], d['t'], d['p']))
    lines.append('')
    lines.append('HALF-LIFE (descriptive): average move in the signal\'s '
                 'direction over its hour\'s baseline, points')
    hz = HORIZONS
    lines.append('  %-6s %-16s %-4s %6s ' % ('wave', 'family', 'inst', 'n') +
                 ' '.join('%7s' % _hz(h) for h in hz))
    for c in rep['half_life']:
        if c['instrument'] != PRIMARY:
            continue
        lines.append('  %-6s %-16s %-4s %6d ' % (
            c['wave'], c['family'], c['instrument'], c['events']) +
            ' '.join('%7s' % _fmt(row['lift_points'])
                     for row in c['curve']))
    lines.append('')
    lines.append('Nothing here is a result. Nominated signs are judged once '
                 'on the validation sessions. No order was placed.')
    return '\n'.join(lines)


def _hz(h):
    return ('%ds' % h) if h < 60 else (('%dm' % (h // 60)) if h < 3600
                                       else '%dh' % (h // 3600))


def text_evaluate(rep):
    lines = ['%s  evaluate  unblind=%s  on %s' % (
        rep['wave5'], rep['unblind'], rep['evaluated_on']),
        'sessions evaluated: %s' % (', '.join(rep['sessions_evaluated'])
                                    or '-')]
    for x in rep['signs']:
        s = x['result'].get(PRIMARY, {})
        lines.append('  %s %-16s n=%s ses=%s lift=%s ticks ci95=%s p=%s -> '
                     '%s' % (x['sign'], x.get('name'), s.get('n'),
                             s.get('sessions'), s.get('lift_ticks'),
                             s.get('ci95'), s.get('p'), x['verdict']))
    lines.append('No order was placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind = '--unblind' in argv
    ev = arg('--evaluate')
    if unblind and not ev:
        print('REFUSED: --unblind is only for --evaluate at the checkpoint. '
              'The study reads DEV sessions only.')
        return 2
    try:
        if ev:
            frozen = json.load(open(ev))
            frozen = frozen.get('nominated', frozen) \
                if isinstance(frozen, dict) else frozen
            if unblind:
                print('*** UNBLIND: this read scores the nominated signs on '
                      'the validation sessions (> %s). Every session read '
                      'is labelled exposed, permanently. This is the '
                      'checkpoint read. ***\n' % DEV_END)
            rep, _r = run_evaluate(d, frozen, unblind=unblind,
                                   max_sessions=ms)
            print(text_evaluate(rep))
        else:
            rep, nominated, _r = run_study(d, max_sessions=ms)
            print(text_study(rep))
            no = arg('--nominated-out')
            if no:
                json.dump(dict(wave5=W5_VERSION, registration=REGISTRATION,
                               nominated=nominated), open(no, 'w'),
                          indent=1, default=str)
                print('nominated signs -> %s (%d)' % (no, len(nominated)))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-five report -> %s' % out)
    if ev and unblind:
        led = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'MROF_EXPOSED_PILOT_DEV_DAYS.json')
        n = write_exposure_on_unblind(rep, led)
        print('exposure ledger -> %s (%d days)' % (led, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
