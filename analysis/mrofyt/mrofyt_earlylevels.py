#!/usr/bin/env python3
"""mrofyt_earlylevels.py - MROF-YT-W11-EARLYLEVELS-1.0

MROF_YT_WAVE11_EARLY_LEVELS_REGISTRATION.md turned into running code.

    EARLY   a one-minute close through a level (a real break), then entry
            at the first 10 s tick within 5 candles where price is back
            through and that tick's aggression is against the break
            (z >= 1.0) -- earlier than wave ten's reclaim close
    groups  MAIN (the six daily range levels), A (confirmed 1-hour and
            4-hour swings), B (09:30 open, Globex open), C (VWAP and its
            bands), D (PP, R1, S1, M2, M3), each judged apart with three
            entries: WICK (a 10 s close through), EARLY, CLOSE (wave ten)

    MAIN  E1 EARLY every break, E2 first test; Holm over two; L2, wave
          ten and WICK beside
    A     WICK / EARLY / CLOSE, every break and first test; Holm over six
    B C D WICK / EARLY / CLOSE, every break; Holm over three each

Every trade: target 25 points, stop 15, 30 minutes, after costs (the
tests); the same trades with wave nine's scaled target beside, when its
frozen A_ref file is given.

    python3 mrofyt_earlylevels.py "<capture>" --a-ref w9_frozen.json --out w11.json
    python3 mrofyt_earlylevels.py "<replay folder>" --holdout --a-ref w9_frozen.json
    python3 mrofyt_earlylevels.py "<capture>" --unblind --a-ref w9_frozen.json  # CHECKPOINT

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_closereclaim as C
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_levels as LV
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W11_VERSION = 'MROF-YT-W11-EARLYLEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE11_EARLY_LEVELS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
TICK = SIG.TICK

GROUPS = collections.OrderedDict([
    ('MAIN', BM.RANGE_LEVELS),
    ('B', ('CASH_OPEN_0930', 'GLOBEX_OPEN')),
    ('C', ('SESSION_VWAP', 'VWAP_UPPER', 'VWAP_LOWER')),
    ('D', ('PP', 'R1', 'S1', 'M2', 'M3')),
])
FIXED_IDS = tuple(k for ids in GROUPS.values() for k in ids)
GROUP_OF = {k: g for g, ids in GROUPS.items() for k in ids}
GROUP_NAMES = dict(MAIN='MAIN: the six daily range levels',
                   A='A: 1-hour and 4-hour swings', B='B: opens',
                   C='C: VWAP and bands', D='D: pivots')

SWING_SIDE = 2
SWING_SESSIONS = 5
WICK_WINDOW_S = 300.0
CANDLES = 5
FLIP_Z = 1.0
MODES = ('WICK', 'EARLY', 'CLOSE')
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# the runner: wave ten's, plus every group's levels on each grid record
# ---------------------------------------------------------------------
class LevelsRunner(C.CloseRunner):
    """Wave ten's runner; every 10 s grid record also carries the MAIN,
    B, C and D levels the runner holds at that instant (R1 and S1 from
    the same pivots as PP). Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        C.CloseRunner.__init__(self, capture_dir, unblind=unblind,
                               holdout=holdout, **kw)
        self.ledger['wave11'] = dict(version=W11_VERSION)

    def _observe_baselines(self, st, te):
        n0 = len(self.grid)
        C.CloseRunner._observe_baselines(self, st, te)
        if len(self.grid) == n0:
            return
        lv = dict(st.levels)
        if st.yday:
            p = LV.pivots(*st.yday)
            lv['R1'], lv['S1'] = p['R1'], p['S1']
        self.grid[-1]['w11_lv'] = tuple(lv.get(k) for k in FIXED_IDS)


# ---------------------------------------------------------------------
# group A: confirmed higher-timeframe swings
# ---------------------------------------------------------------------
_OFF = {}


def _offset(t):
    k = int(t // 3600)
    if k not in _OFF:
        _OFF[k] = RUN.et_offset(t)
    return _OFF[k]


def bucket(t, hours):
    """The Eastern-time candle a time falls in: hours (1) or 4-hour
    candles starting 18:00, 22:00, ... ET."""
    h = int((t + _offset(t)) // 3600)
    return h if hours == 1 else (h - 18) // 4


def bucket_end(k, hours, t_ref):
    """Epoch at which candle k closes (the Eastern offset taken near
    t_ref, a time inside it)."""
    loc = (k + 1) * 3600 if hours == 1 else (18 + 4 * (k + 1)) * 3600
    return float(loc - _offset(t_ref))


def candles(paths, hours):
    """{candle: [high, low, close, last time]} of one instrument's mids,
    paths time-ordered."""
    out = {}
    for ts, ps in paths:
        for t, p in zip(ts, ps):
            k = bucket(t, hours)
            c = out.get(k)
            if c is None:
                out[k] = [p, p, p, t]
            else:
                if p > c[0]:
                    c[0] = p
                if p < c[1]:
                    c[1] = p
                c[2], c[3] = p, t
    return out


def htf_swings(cands, hours):
    """[swing dicts]: a candle's high above the 2 before and not below
    the 2 after (lows mirrored), five consecutive recorded candles; a
    level from the close of the 2nd after until a later candle of the
    same timeframe closes beyond it (t_off; inf when none)."""
    ks = sorted(cands)
    out = []
    for i in range(SWING_SIDE, len(ks) - SWING_SIDE):
        k = ks[i]
        if ks[i - SWING_SIDE:i + SWING_SIDE + 1] != \
                list(range(k - SWING_SIDE, k + SWING_SIDE + 1)):
            continue
        h, lo = cands[k][0], cands[k][1]
        before = [cands[k - j] for j in range(1, SWING_SIDE + 1)]
        after = [cands[k + j] for j in range(1, SWING_SIDE + 1)]
        k_on = k + SWING_SIDE
        t_on = bucket_end(k_on, hours, cands[k_on][3])
        for kind, px, ok, beyond in (
                ('SWING_H', h, h > max(c[0] for c in before) and
                 h >= max(c[0] for c in after),
                 lambda c, px=h: c[2] >= px + TICK - 1e-9),
                ('SWING_L', lo, lo < min(c[1] for c in before) and
                 lo <= min(c[1] for c in after),
                 lambda c, px=lo: c[2] <= px - TICK + 1e-9)):
            if not ok:
                continue
            t_off = float('inf')
            for k2 in ks[i + SWING_SIDE + 1:]:
                if beyond(cands[k2]):
                    t_off = bucket_end(k2, hours, cands[k2][3])
                    break
            out.append(dict(id='%s_%dH@%d' % (kind, hours, k), kind=kind,
                            hours=hours, price=px, t_on=t_on, t_off=t_off))
    return out


def swings_by_instrument(r):
    """{instrument: [swings]} with each swing's confirming session."""
    by = collections.defaultdict(list)
    for (inst, run), (ts, ps) in r.series.items():
        if len(ts):
            by[inst].append(BM.compress(ts, ps))
    out = {}
    for inst, paths in by.items():
        paths.sort(key=lambda p: p[0][0])
        sw = htf_swings(candles(paths, 1), 1) + htf_swings(candles(paths, 4), 4)
        for s in sw:
            s['session'] = RUN.session_id(s['t_on'])
        out[inst] = sw
    return out


# ---------------------------------------------------------------------
# the three entries
# ---------------------------------------------------------------------
def flip(g, b):
    D, z = g.get('D'), g.get('z_delta_s')
    return bool(D) and z is not None and (1 if D > 0 else -1) == -b and \
        z >= FLIP_Z


def _levels_at(g, swings, ses_index):
    """[(key, level id, group, price)] at one grid record."""
    out = []
    lv = g.get('w11_lv') or ()
    for k, lid in enumerate(FIXED_IDS):
        px = lv[k] if k < len(lv) else None
        if px is not None:
            out.append(((g['session'], lid), lid, GROUP_OF[lid], px))
    si = ses_index.get(g['session'])
    for s in swings:
        if s['t_on'] <= g['t'] < s['t_off'] and si is not None and \
                si <= s['ses_idx'] + SWING_SESSIONS:
            out.append((s['id'], s['id'], 'A', s['price']))
    return out


def _count_key(inst, key, g):
    return (inst, key) if isinstance(key, str) else (inst,) + tuple(key)


def run_episodes(grid, gmap, swings, ses_index, counts, mode):
    """Events of one mode over one run's time-ordered grid records."""
    state = {}
    out = []
    for g in grid:
        t, mid = g['t'], g.get('mid')
        if mid is None:
            continue
        is_close = int(round(t)) % 60 == 0
        if mode == 'CLOSE' and not is_close:
            continue
        for key, lid, grp, L in _levels_at(g, swings, ses_index):
            s = C.side(mid, L)
            st = state.setdefault(key, dict(last=0, brk=None))
            ev = None
            if mode == 'WICK':
                if st['brk'] is not None:
                    b, tb, no = st['brk']
                    if t - tb <= WICK_WINDOW_S:
                        if s == -b and flip(g, b):
                            ev = (b, no)
                            st['brk'], st['last'] = None, s
                        if ev is None:
                            continue
                    else:
                        st['brk'] = None
                        if s != 0:
                            st['last'] = s
                        continue
                if ev is None:
                    if s != 0 and st['last'] == -s:
                        ck = _count_key(g['instrument'], key, g)
                        counts[ck] += 1
                        st['brk'] = (s, t, counts[ck])
                    if s != 0:
                        st['last'] = s
            elif mode == 'EARLY':
                if st['brk'] is not None:
                    b, tb, no = st['brk']
                    if t <= tb + CANDLES * 60:
                        if t > tb and s == -b and flip(g, b):
                            ev = (b, no)
                            st['brk'], st['last'] = None, -b
                    else:
                        st['brk'] = None
                if ev is None and is_close and s != 0:
                    if st['brk'] is None and st['last'] == -s:
                        ck = _count_key(g['instrument'], key, g)
                        counts[ck] += 1
                        st['brk'] = (s, t, counts[ck])
                    st['last'] = s
            else:                                         # CLOSE
                m = int(round(t)) // 60 - 1
                if st['brk'] is not None:
                    b, mb, no = st['brk']
                    if m - mb <= CANDLES:
                        if s == -b:
                            if C.flow_ok(gmap, m, b):
                                ev = (b, no)
                            st['brk'], st['last'] = None, s
                        if ev is None:
                            continue
                    else:
                        st['brk'], st['last'] = None, b
                if ev is None:
                    if s != 0 and st['last'] == -s:
                        ck = _count_key(g['instrument'], key, g)
                        counts[ck] += 1
                        st['brk'] = (s, m, counts[ck])
                    if s != 0:
                        st['last'] = s
            if ev is not None:
                b, no = ev
                out.append(dict(instrument=g['instrument'], session=g['session'],
                                run=g['run'], group=grp, level_id=lid,
                                level=L, b=b, direction=-b, t=t, mode=mode,
                                test_no=no))
    return out


def all_events(r):
    """Every entry of every mode and group in the read."""
    sw = swings_by_instrument(r)
    runs = collections.defaultdict(list)
    for g in r.grid:
        runs[(g['instrument'], g['run'])].append(g)
    order = sorted(runs, key=lambda k: (k[0], min(g['t'] for g in runs[k])))
    sessions = collections.defaultdict(set)
    for g in r.grid:
        sessions[g['instrument']].add(g['session'])
    for inst, lst in sw.items():
        ses_list = sorted(sessions[inst])
        for s in lst:
            # the swing's own session, or the next one recorded after it
            s['ses_idx'] = bisect.bisect_left(ses_list, s['session'])
    out = []
    for mode in MODES:
        counts = collections.Counter()
        for key in order:
            inst = key[0]
            grid = sorted(runs[key], key=lambda g: g['t'])
            gmap = {int(round(g['t'])): g for g in grid}
            ses_index = {s: i for i, s in enumerate(sorted(sessions[inst]))}
            t0, t1 = grid[0]['t'], grid[-1]['t']
            swings = [s for s in sw.get(inst, [])
                      if s['t_on'] <= t1 and s['t_off'] > t0]
            out += run_episodes(grid, gmap, swings, ses_index, counts, mode)
    return out


# ---------------------------------------------------------------------
# scoring and tables
# ---------------------------------------------------------------------
def score(r, events, a_ref=None):
    """[(event, outcome, gross ticks, risk ticks, seconds)], each event
    also carrying its scaled-target net points (or None)."""
    paths = {k: BM.compress(ts, ps) for k, (ts, ps) in r.series.items()
             if len(ts)}
    out = []
    for e in events:
        key = (e['instrument'], e['run'])
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        res = LB.path_exit(ts, ps, i, e['direction'], LB.TARGET,
                           LB.FIXED_STOP)
        if res[0] == 'UNRESOLVED':
            continue
        e = dict(e, scaled_net=None)
        ref = (a_ref or {}).get(e['instrument'])
        tgt, real = W.scaled_target(r.recent_range(e['instrument'],
                                                   e['session']), ref)
        if real:
            o, v, _s = LB.path_exit(ts, ps, i, e['direction'], tgt,
                                    LB.FIXED_STOP)
            if o != 'UNRESOLVED':
                e['scaled_net'] = W.net_points(e['instrument'], o, v)
        out.append((e, res[0], res[1], LB.FIXED_STOP, res[2]))
    return out


def row(rows, inst, tid, name):
    st = LB.test_stats(rows, inst)
    one = LB.test_stats(V.one_at_a_time(rows), inst)
    sc = [x[0]['scaled_net'] for x in rows
          if x[0].get('scaled_net') is not None]
    st.update(test=tid, name=name, one_at_a_time=dict(
        (k, one.get(k)) for k in ('n', 'hit', 'net_points')),
        scaled_net_points=round(sum(sc) / len(sc), 3) if sc else None,
        scaled_n=len(sc))
    return st


def _verdicts(tests):
    rej = BM.holm([x.get('p') for x in tests], HOLM_ALPHA)
    for x, rj in zip(tests, rej):
        if x['n'] < MIN_EVENTS:
            x['status'] = 'NOT TESTED'
        elif rj and x['net_points'] > 0 and x.get('ci95_net_ticks') and \
                x['ci95_net_ticks'][0] > 0:
            x['status'] = 'PROMISING'
        else:
            x['status'] = 'NO SIGNAL'


def tables(scored, refs, keep=None):
    """{instrument: {family: [rows]}}: MAIN's two tests and references,
    then A, B, C and D, each with its own Holm."""
    insts = sorted({x[0]['instrument'] for x in scored} |
                   {x[0]['instrument'] for v in refs.values() for x in v})
    out = {}
    for inst in insts:
        mine = [x for x in scored if x[0]['instrument'] == inst and
                (keep is None or keep(x[0]['session']))]
        ref = {k: [x for x in v if x[0]['instrument'] == inst and
                   (keep is None or keep(x[0]['session']))]
               for k, v in refs.items()}
        sel = lambda grp, mode, first=False: [   # noqa: E731
            x for x in mine if x[0]['group'] == grp and x[0]['mode'] == mode
            and (not first or x[0]['test_no'] == 1)]
        fam = collections.OrderedDict()
        main = [row(sel('MAIN', 'EARLY'), inst, 'E1', 'EARLY'),
                row(sel('MAIN', 'EARLY', True), inst, 'E2', 'EARLY, 1st')]
        _verdicts(main)
        for tid, name, rows in (
                ('L2', 'L2 wick (V0)', ref.get('V0', [])),
                ('L2F', 'L2 wick, 1st (V1)', ref.get('V1', [])),
                ('C1', 'CLOSE, wave ten', ref.get('C1', [])),
                ('C2', 'CLOSE, wave ten, 1st', ref.get('C2', [])),
                ('WM', 'WICK on 10 s closes', sel('MAIN', 'WICK'))):
            x = row(rows, inst, tid, name)
            x['status'] = 'REFERENCE'
            main.append(x)
        fam['MAIN'] = main
        for grp in ('A', 'B', 'C', 'D'):
            tests = []
            for mode in MODES:
                tests.append(row(sel(grp, mode), inst, '%s-%s' % (grp, mode),
                                 mode))
                if grp == 'A':
                    tests.append(row(sel(grp, mode, True), inst,
                                     '%s-%s1' % (grp, mode), mode + ', 1st'))
            _verdicts(tests)
            fam[grp] = tests
        out[inst] = fam
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, a_ref=None,
        max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = LevelsRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    ev = all_events(r)
    sc = score(r, ev, a_ref)
    close = C.score_close(r, C.close_events(r))
    refs = dict(V.score_variants(r, V.variant_events(r)))
    refs['C1'] = [x for x in close if x[0]['flow']]
    refs['C2'] = [x for x in close if x[0]['flow'] and x[0]['test_no'] == 1]
    tab = tables(sc, refs, keep)
    if not (unblind or holdout):
        for fam in tab.values():
            for rows in fam.values():
                for x in rows:
                    if x['status'] != 'REFERENCE':
                        x['status'] += ' (DEV, seen before the registration)'
    mine = [e for e in ev if keep(e['session'])]
    rep = dict(wave11=W11_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               a_ref=a_ref, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in mine}),
               entries=dict(sorted(collections.Counter(
                   '%s %s %s' % (e['instrument'], e['group'], e['mode'])
                   for e in mine).items())),
               tables=tab)
    return rep, r


def text(rep):
    lines = ['%s  %s' % (rep['wave11'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'target 25 pts, stop 15 pts, 30 min, after costs (the tests); '
             '"scaled" = the same trades with the volatility-scaled target%s'
             % ('' if rep.get('a_ref') else ' (not shown: no --a-ref file)')]
    for inst, fam in rep['tables'].items():
        for grp, rows in fam.items():
            lines.append('')
            lines.append('%s  %s' % (inst, GROUP_NAMES[grp]))
            lines.append('     %-8s %-22s %5s %4s %6s %8s %8s %7s %8s  %-13s %s'
                         % ('id', 'entry', 'n', 'ses', 'win', 'net pts',
                            'scaled', 't', 'p', 'one-at-a-time', 'status'))
            for x in rows:
                one = x['one_at_a_time']
                lines.append(
                    '     %-8s %-22s %5d %4d %6s %+8.2f %8s %7s %8s  %-13s %s'
                    % (x['test'], x['name'], x['n'], x['sessions'],
                       '-' if not x['n'] else '%.0f%%' % (100 * x['hit']),
                       x.get('net_points') or 0.0,
                       '-' if x.get('scaled_net_points') is None else
                       '%+.2f' % x['scaled_net_points'],
                       '-' if x.get('t') is None else '%.2f' % x['t'],
                       '-' if x.get('p') is None else '%.4f' % x['p'],
                       '-' if not one.get('n') else '%d %+.2f' % (
                           one['n'], one['net_points']),
                       x['status']))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def record_holdout_read(rep, path):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            old = json.load(open(path))
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=W11_VERSION, sessions=rep['sessions_inspected']))
    old['rule'] = ('Replay holdout sessions are read once by each '
                   'registered wave; a later read of NEW rules on them is '
                   'not a fresh test.')
    json.dump(old, open(path, 'w'), indent=1)
    return len(old['reads'])


def record_exposure(rep, path):
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
                         exposed_by=W11_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W11_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W11_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W11_VERSION)
    days = sorted(by.values(), key=lambda d: d['session'])
    json.dump(dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)


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
        print('*** %s: this read scores the registered tests once. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, a_ref, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-eleven report -> %s' % out)
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
