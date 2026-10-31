#!/usr/bin/env python3
"""mrofyt_closereclaim.py - MROF-YT-W10-CLOSERECLAIM-1.0

MROF_YT_WAVE10_CLOSERECLAIM_REGISTRATION.md turned into running code:
break and reclaim on one-minute candle CLOSES at the six big daily
levels, the reclaim confirmed by the order flow; L2 (the wick version)
reported beside it from the same read.

    break    a one-minute close at least 1 tick through yesterday's high
             / low, the overnight high / low or last week's high / low,
             coming from the other side
    reclaim  within the next 5 one-minute candles, a close back on the
             original side; none: the break held, no trade
    filter   the reclaim candle's net aggression is with the reclaim AND
             the 10 s ending at its close shows it (z >= 1.0)
    trade    fade the break at the reclaim close: 25-point target,
             15-point stop, 30 minutes, after costs

    C1  every filtered reclaim       C2  the first test of the level only
    references (not tested): no filter, all / first test; L2 V0 / V1

    python3 mrofyt_closereclaim.py "<capture>" --out w10.json     # DEV: describes
    python3 mrofyt_closereclaim.py "<replay folder>" --holdout --out w10_replay.json
    python3 mrofyt_closereclaim.py "<capture>" --unblind --out w10_eval.json  # CHECKPOINT

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W10_VERSION = 'MROF-YT-W10-CLOSERECLAIM-1.0'
REGISTRATION = 'MROF_YT_WAVE10_CLOSERECLAIM_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
TICK = SIG.TICK

LEVEL_IDS = BM.RANGE_LEVELS
SIDE_TICKS = 1.0
RECLAIM_BARS = 5
FLIP_Z = 1.0
TESTS = (('C1', 'CLOSE RECLAIM, FLOW'), ('C2', 'CLOSE RECLAIM, FLOW, 1st'))
REFS = (('C0', 'CLOSE RECLAIM, NO FILTER'),
        ('C0F', 'CLOSE RECLAIM, NO FILTER, 1st'),
        ('L2', 'L2 WICK (V0)'), ('L2F', 'L2 WICK, 1st (V1)'))
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# the runner: wave nine's, plus the six levels on every grid record
# ---------------------------------------------------------------------
class CloseRunner(W.TargetRunner):
    """Wave nine's runner; every 10 s grid record also carries the six
    range levels the runner holds at that instant. Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        W.TargetRunner.__init__(self, capture_dir, unblind=unblind,
                                holdout=holdout, **kw)
        self.ledger['wave10'] = dict(version=W10_VERSION)

    def _observe_baselines(self, st, te):
        n0 = len(self.grid)
        W.TargetRunner._observe_baselines(self, st, te)
        if len(self.grid) == n0:
            return
        self.grid[-1]['w10_lv'] = tuple(st.levels.get(k) for k in LEVEL_IDS)


# ---------------------------------------------------------------------
# candles, the event, the filter
# ---------------------------------------------------------------------
def side(close, level):
    """+1 a tick or more above the level, -1 a tick or more below, 0 at."""
    if close is None or level is None:
        return 0
    x = (close - level) / TICK
    if x >= SIDE_TICKS - 1e-9:
        return 1
    if x <= -SIDE_TICKS + 1e-9:
        return -1
    return 0


def minute_closes(ts, ps):
    """[(minute, close)] for every clock minute from a run's first mid to
    its last: the last mid before the minute ends."""
    if not len(ts):
        return []
    out = []
    for m in range(int(ts[0] // 60), int(ts[-1] // 60) + 1):
        i = bisect.bisect_left(ts, (m + 1) * 60.0) - 1
        if i >= 0:
            out.append((m, ps[i]))
    return out


def flow_ok(gmap, m, b):
    """The reclaim candle's net aggression is against the break (-b) and
    the 10 s grid tick ending at its close shows it with z >= 1.0."""
    net = 0.0
    for j in range(1, 7):
        g = gmap.get(m * 60 + 10 * j)
        if g is not None:
            net += -b * (g.get('D') or 0.0)
    g = gmap.get((m + 1) * 60)
    if g is None or not g.get('D') or g.get('z_delta_s') is None:
        return False
    return net > 0 and (1 if g['D'] > 0 else -1) == -b and \
        g['z_delta_s'] >= FLIP_Z


def episodes(closes, gmap, counts):
    """Break-and-reclaim events of one run. closes: [(minute, close)];
    gmap: {grid time: record} of the run; counts: breaks so far per
    (instrument, session, level), shared by a session's runs."""
    state = {}
    out = []
    for m, c in closes:
        g = gmap.get((m + 1) * 60)
        if g is None:
            continue
        lv = g.get('w10_lv') or ()
        for k, lid in enumerate(LEVEL_IDS):
            L = lv[k] if k < len(lv) else None
            if L is None:
                continue
            st = state.setdefault((g['session'], lid),
                                  dict(last=0, brk=None))
            s = side(c, L)
            if st['brk'] is not None:
                b, mb, no = st['brk']
                if m - mb <= RECLAIM_BARS:
                    if s == -b:
                        out.append(dict(
                            instrument=g['instrument'], session=g['session'],
                            run=g['run'], level_id=lid, level=L, b=b,
                            direction=-b, family='CLOSE', m_break=mb,
                            m_reclaim=m, t=(m + 1) * 60.0, test_no=no,
                            flow=flow_ok(gmap, m, b)))
                        st['brk'] = None
                        st['last'] = s
                    continue
                st['brk'] = None                 # held: no trade
                st['last'] = b
            if s != 0 and st['last'] == -s:
                ck = (g['instrument'], g['session'], lid)
                counts[ck] += 1
                st['brk'] = (s, m, counts[ck])
            if s != 0:
                st['last'] = s
    return out


def close_events(r):
    gby = collections.defaultdict(dict)
    for g in r.grid:
        gby[(g['instrument'], g['run'])][int(round(g['t']))] = g
    counts = collections.Counter()
    out = []
    keys = sorted((k for k in r.series if len(r.series[k][0])),
                  key=lambda k: (k[0], r.series[k][0][0]))
    for key in keys:
        if key not in gby:
            continue
        cts, cps = BM.compress(*r.series[key])
        out += episodes(minute_closes(cts, cps), gby[key], counts)
    return out


def score_close(r, events):
    """[(event, outcome, gross ticks, risk ticks, seconds)], wave six's
    T1 exit from the reclaim close; unresolved trades dropped."""
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
        out.append((e, res[0], res[1], LB.FIXED_STOP, res[2]))
    return out


def table(rows, l2, keep=None):
    """{instrument: [C1, C2 tests, then the references]}; Holm over two."""
    insts = sorted({x[0]['instrument'] for x in rows} |
                   {x[0]['instrument'] for v in l2.values() for x in v})
    out = {}
    for inst in insts:
        mine = [x for x in rows if x[0]['instrument'] == inst and
                (keep is None or keep(x[0]['session']))]
        mine_l2 = {k: [x for x in v if x[0]['instrument'] == inst and
                       (keep is None or keep(x[0]['session']))]
                   for k, v in l2.items()}
        sets = dict(
            C1=[x for x in mine if x[0]['flow']],
            C2=[x for x in mine if x[0]['flow'] and x[0]['test_no'] == 1],
            C0=mine, C0F=[x for x in mine if x[0]['test_no'] == 1],
            L2=mine_l2.get('V0', []), L2F=mine_l2.get('V1', []))
        tests = []
        for tid, name in TESTS + REFS:
            st = LB.test_stats(sets[tid], inst)
            one = LB.test_stats(V.one_at_a_time(sets[tid]), inst)
            st.update(test=tid, name=name, one_at_a_time=dict(
                (k, one.get(k)) for k in ('n', 'hit', 'net_points')))
            tests.append(st)
        rej = BM.holm([x.get('p') for x in tests[:2]], HOLM_ALPHA)
        for x, rj in zip(tests[:2], rej):
            if x['n'] < MIN_EVENTS:
                x['status'] = 'NOT TESTED'
            elif rj and x['net_points'] > 0 and x.get('ci95_net_ticks') and \
                    x['ci95_net_ticks'][0] > 0:
                x['status'] = 'PROMISING'
            else:
                x['status'] = 'NO SIGNAL'
        for x in tests[2:]:
            x['status'] = 'REFERENCE'
        out[inst] = tests
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = CloseRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    ev = close_events(r)
    tab = table(score_close(r, ev),
                V.score_variants(r, V.variant_events(r)), keep)
    if not (unblind or holdout):
        for tests in tab.values():
            for x in tests[:2]:
                x['status'] += ' (DEV, seen before the registration)'
    mine = [e for e in ev if keep(e['session'])]
    rep = dict(wave10=W10_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in mine}),
               reclaims=dict(sorted(collections.Counter(
                   '%s %s' % (e['instrument'],
                              'passed the filter' if e['flow']
                              else 'filtered out')
                   for e in mine).items())),
               tests=tab)
    return rep, r


def text(rep):
    lines = ['%s  %s' % (rep['wave10'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'candle-close reclaims: %s' % (', '.join(
                 '%s %d' % kv for kv in rep['reclaims'].items()) or '-'),
             'target 25 pts, stop 15 pts, 30 min; net = after commission, a '
             'tick of spread and a tick of slip on stops']
    for inst, tests in rep['tests'].items():
        lines.append('')
        lines.append('%-4s %-4s %-30s %5s %4s %6s %8s %7s %8s  %-13s %s' % (
            inst, 'id', 'version', 'n', 'ses', 'win', 'net pts', 't', 'p',
            'one-at-a-time', 'status'))
        for x in tests:
            one = x['one_at_a_time']
            lines.append('     %-4s %-30s %5d %4d %6s %+8.2f %7s %8s  %-13s %s'
                         % (x['test'], x['name'], x['n'], x['sessions'],
                            '-' if not x['n'] else '%.0f%%' % (100 * x['hit']),
                            x.get('net_points') or 0.0,
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
        version=W10_VERSION, sessions=rep['sessions_inspected']))
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
                         exposed_by=W10_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W10_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W10_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W10_VERSION)
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
    if unblind or holdout:
        print('*** %s: this read scores the two registered tests once. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-ten report -> %s' % out)
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
