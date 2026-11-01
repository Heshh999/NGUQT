#!/usr/bin/env python3
"""mrofyt_valuearea.py - MROF-YT-W13-VALUEAREA-1.0

MROF_YT_WAVE13_VALUEAREA_REGISTRATION.md turned into running code: back
into yesterday's value area with speed, confirmed by the order flow,
with targets from value itself and the quant target beside the fixed 25.

    value    yesterday's cash-session (09:30-16:00 ET) volume profile from
             real trades, 1-point bins, 70 %: POC, VAH, VAL
    out      a 10 s mid at least 2 points beyond VAH or VAL
    back in  the first 10 s tick back inside by a tick, after a move of at
             least 4 points back over the last 30 s, with that tick's
             aggression into value at z >= 2.0; entries 09:30-15:30 ET
    trade    into value; stop 15 points, 30 minutes

    VA1  fixed 25: mean net above zero
    VA2  POC target    minus fixed 25, same trades
    VA3  far edge      minus fixed 25
    VA4  scaled target minus fixed 25 (needs --a-ref, wave nine's file)

    python3 mrofyt_valuearea.py "<capture>" --a-ref w9_frozen.json --out w13.json
    python3 mrofyt_valuearea.py "<replay folder>" --holdout --a-ref w9_frozen.json
    python3 mrofyt_valuearea.py "<capture>" --unblind --a-ref w9_frozen.json  # CHECKPOINT

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_context as CX
import mrofyt_earlylevels as E
import mrofyt_l2context as X
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W13_VERSION = 'MROF-YT-W13-VALUEAREA-1.0'
REGISTRATION = 'MROF_YT_WAVE13_VALUEAREA_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
TICK = SIG.TICK

CASH_FROM, CASH_TO = 9.5 * 3600, 16 * 3600
COMPLETE_FIRST, COMPLETE_LAST = 10 * 3600, 15.5 * 3600
OUT_TICKS = 8.0                       # 2 points
SPEED_TICKS = 16.0                    # 4 points
SPEED_S = 30
FLOW_Z = 2.0
ENTRY_FROM, ENTRY_TO = 9.5 * 3600, 15.5 * 3600
MIN_AHEAD_TICKS = 8.0                 # 2 points
TARGETS = ('POC', 'FAR', 'SCALED')
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# the runner: wave twelve's, plus each session's cash volume profile
# ---------------------------------------------------------------------
class ValueRunner(X.ContextRunner):
    """Wave twelve's runner; every cash-session trade is added to its
    session's profile, and the value area is kept at the session's
    close. Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        X.ContextRunner.__init__(self, capture_dir, unblind=unblind,
                                 holdout=holdout, **kw)
        self.profile = {}            # (inst, session) -> [bins, first, last]
        self.values = collections.defaultdict(dict)   # inst -> {ses: va}
        self.ledger['wave13'] = dict(version=W13_VERSION)

    def _add_trade(self, inst, session, t, px, sz):
        if px is None or not sz or not session:
            return
        sod = (t + E.et_offset_hourly(t)) % 86400
        if not CASH_FROM <= sod < CASH_TO:
            return
        p = self.profile.get((inst, session))
        if p is None:
            p = self.profile[(inst, session)] = [
                collections.defaultdict(float), sod, sod]
        p[0][int(math.floor(px))] += sz
        if sod < p[1]:
            p[1] = sod
        if sod > p[2]:
            p[2] = sod

    def _finish_profile(self, inst, session):
        p = self.profile.pop((inst, session), None)
        if p is None or p[1] > COMPLETE_FIRST or p[2] < COMPLETE_LAST:
            return
        poc, vah, val = CX.value_area(dict(p[0]))
        if poc is not None:
            self.values[inst][session] = (poc, vah, val)

    def _on_trade_event(self, st, t, e):
        X.ContextRunner._on_trade_event(self, st, t, e)
        if st.trades:
            tt, px, sz, _s = st.trades[-1]
            self._add_trade(st.instrument, st.session, tt, px, sz)

    def _close_session(self, st):
        self._finish_profile(st.instrument, st.session)
        X.ContextRunner._close_session(self, st)

    def _mark_run(self, st):
        mark = X.ContextRunner._mark_run(self, st)
        p = self.profile.get((st.instrument, st.session))
        mark['w13'] = None if p is None else [dict(p[0]), p[1], p[2]]
        return mark

    def _unwind_run(self, st, mark):
        X.ContextRunner._unwind_run(self, st, mark)
        key = (st.instrument, st.session)
        m = mark['w13']
        if m is None:
            self.profile.pop(key, None)
        else:
            self.profile[key] = [collections.defaultdict(float, m[0]),
                                 m[1], m[2]]


def prev_value(values, session):
    """The value area of the latest earlier session that has one."""
    earlier = sorted(s for s in values if s < session)
    return values[earlier[-1]] if earlier else None


# ---------------------------------------------------------------------
# the event
# ---------------------------------------------------------------------
def into_value(g, b):
    D, z = g.get('D'), g.get('z_delta_s')
    return bool(D) and z is not None and (1 if D > 0 else -1) == -b and \
        z >= FLOW_Z


def va_events(r):
    """Back-into-value events of the read, in time order per run."""
    runs = collections.defaultdict(list)
    for g in r.grid:
        runs[(g['instrument'], g['run'])].append(g)
    out = []
    for (inst, run), grid in sorted(runs.items(),
                                    key=lambda kv: (kv[0][0],
                                                    min(g['t'] for g in kv[1]))):
        grid.sort(key=lambda g: g['t'])
        gmap = {int(round(g['t'])): g for g in grid}
        state, va_of = {}, {}
        for g in grid:
            mid = g.get('mid')
            if g['session'] not in va_of:
                va_of[g['session']] = prev_value(r.values[inst], g['session'])
            va = va_of[g['session']]
            if mid is None or va is None:
                continue
            poc, vah, val = va
            ses = g['session']
            b = state.get(ses)
            if b is None:
                if mid >= vah + OUT_TICKS * TICK - 1e-9:
                    state[ses] = 1
                elif mid <= val - OUT_TICKS * TICK + 1e-9:
                    state[ses] = -1
                continue
            back = mid <= vah - TICK + 1e-9 if b > 0 else \
                mid >= val + TICK - 1e-9
            if not back:
                continue
            state[ses] = None
            if not ENTRY_FROM <= RUN.sod_seconds(g['t']) < ENTRY_TO:
                continue
            g0 = gmap.get(int(round(g['t'])) - SPEED_S)
            if g0 is None or g0.get('mid') is None:
                continue
            if b * (g0['mid'] - mid) < SPEED_TICKS * TICK - 1e-9:
                continue
            if not into_value(g, b):
                continue
            out.append(dict(instrument=inst, session=ses, run=run, b=b,
                            direction=-b, t=g['t'], poc=poc, vah=vah,
                            val=val, family='VALUE'))
    return out


# ---------------------------------------------------------------------
# targets, scoring and the tests
# ---------------------------------------------------------------------
def structure_target(direction, p0, px):
    """Ticks to px if it is at least 2 points ahead; FIXED otherwise."""
    dist = direction * (px - p0) / TICK
    if dist >= MIN_AHEAD_TICKS - 1e-9:
        return dist, True
    return LB.TARGET, False


def score(r, events, a_ref=None):
    """[(event, {FIXED|POC|FAR|SCALED: (outcome, ticks, target, real)},
    None)] for events whose four versions all resolved; the event keeps
    its fixed exit's seconds."""
    paths = V.compressed_paths(r)
    out = []
    for e in events:
        key = (e['instrument'], e['run'])
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        d, p0 = e['direction'], ps[i]
        far = e['val'] if e['b'] > 0 else e['vah']
        ref = (a_ref or {}).get(e['instrument'])
        tg = dict(FIXED=(LB.TARGET, True),
                  POC=structure_target(d, p0, e['poc']),
                  FAR=structure_target(d, p0, far),
                  SCALED=W.scaled_target(
                      r.recent_range(e['instrument'], e['session']), ref))
        res, secs = {}, None
        for name, (tgt, real) in tg.items():
            o, v, s = LB.path_exit(ts, ps, i, d, tgt, LB.FIXED_STOP)
            res[name] = (o, v, tgt, real)
            if name == 'FIXED':
                secs = s
        if any(x[0] == 'UNRESOLVED' for x in res.values()):
            continue
        out.append((dict(e, p0=p0, seconds=secs), res, None))
    return out


def table(scored, keep=None, has_ref=False):
    out = {}
    for inst in sorted({x[0]['instrument'] for x in scored}):
        mine = [x for x in scored if x[0]['instrument'] == inst and
                (keep is None or keep(x[0]['session']))]
        fixed = [(e, res['FIXED'][0], res['FIXED'][1], LB.FIXED_STOP,
                  e['seconds']) for e, res, _m in mine]
        st = LB.test_stats(fixed, inst)
        one = LB.test_stats(V.one_at_a_time(fixed), inst)
        va1 = dict(test='VA1', name='fixed 25: makes money?', n=st['n'],
                   sessions=st['sessions'], win=st.get('hit'),
                   net_points=st.get('net_points'), t=st.get('t'),
                   p=st.get('p'), ci95=st.get('ci95_net_ticks'),
                   one_at_a_time=dict((k, one.get(k)) for k in
                                      ('n', 'hit', 'net_points')))
        tests = [va1]
        for tid, name in (('VA2', 'POC'), ('VA3', 'FAR'), ('VA4', 'SCALED')):
            x = W.paired_stats(mine, inst, name)
            x.update(test=tid, name='%s minus fixed 25' % name)
            if name == 'SCALED' and not has_ref:
                x['p'] = None
            tests.append(x)
        rej = BM.holm([x.get('p') for x in tests], HOLM_ALPHA)
        for x, rj in zip(tests, rej):
            eff = x.get('net_points') if x['test'] == 'VA1' else \
                x.get('mean_diff_points')
            ci = x.get('ci95') if x['test'] == 'VA1' else \
                x.get('ci95_diff_points')
            if x['test'] == 'VA4' and not has_ref:
                x['status'] = 'NOT TESTED (no --a-ref)'
            elif x['n'] < MIN_EVENTS:
                x['status'] = 'NOT TESTED'
            elif rj and eff is not None and eff > 0 and ci and ci[0] > 0:
                x['status'] = 'PROMISING' if x['test'] == 'VA1' else \
                    'BEATS 25'
            else:
                x['status'] = 'NO SIGNAL' if x['test'] == 'VA1' else \
                    'NO BETTER'
        out[inst] = tests
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, a_ref=None,
        max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = ValueRunner(capture_dir, unblind=unblind, holdout=holdout,
                    max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s)' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s): describes, not a test' % DEV_END
    sc = score(r, va_events(r), a_ref)
    tab = table(sc, keep, has_ref=bool(a_ref))
    if not (unblind or holdout):
        for tests in tab.values():
            for x in tests:
                x['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave13=W13_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               a_ref=a_ref, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({x[0]['session'] for x in sc
                                          if keep(x[0]['session'])}),
               value_areas={i: dict(v) for i, v in r.values.items()},
               tests=tab)
    return rep, r


def text(rep):
    lines = ['%s  %s' % (rep['wave13'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'sessions with a complete value area: %s' % ', '.join(
                 '%s %d' % (i, len(v)) for i, v in
                 rep['value_areas'].items()),
             'stop 15 pts, 30 min, after costs; diff = net minus the fixed 25 '
             'on the same trades']
    for inst, tests in rep['tests'].items():
        lines.append('')
        lines.append('%-4s %-4s %-24s %5s %4s %6s %8s %8s %7s %8s  %s' % (
            inst, 'id', 'question', 'n', 'ses', 'win', 'net pts', 'diff',
            't', 'p', 'status'))
        for x in tests:
            lines.append('     %-4s %-24s %5d %4d %6s %8s %8s %7s %8s  %s' % (
                x['test'], x['name'], x['n'], x.get('sessions', 0),
                '-' if x.get('win') is None else '%.0f%%' % (100 * x['win']),
                '-' if x.get('net_points') is None else
                '%+.2f' % x['net_points'],
                '-' if x.get('mean_diff_points') is None else
                '%+.2f' % x['mean_diff_points'],
                '-' if x.get('t') is None else '%.2f' % x['t'],
                '-' if x.get('p') is None else '%.4f' % x['p'],
                x['status']))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def record_holdout_read(rep, path):
    return LG.record_holdout_read(rep, path, W13_VERSION)


def record_exposure(rep, path):
    return LG.record_exposure(rep, path, W13_VERSION)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    a_ref = None
    if arg('--a-ref'):
        try:
            a_ref = json.load(open(arg('--a-ref')))['a_ref']
            if not isinstance(a_ref, dict):
                raise ValueError
        except (OSError, ValueError, KeyError, TypeError):
            print('STOPPED: %s is not wave nine\'s frozen file (the '
                  '--frozen-out of its DEV run)' % arg('--a-ref'))
            return 2
    if unblind or holdout:
        print('*** %s: this read scores the four registered tests once. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, a_ref, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-thirteen report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER))
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER))
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
