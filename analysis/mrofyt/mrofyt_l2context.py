#!/usr/bin/env python3
"""mrofyt_l2context.py - MROF-YT-W12-L2CONTEXT-1.0

MROF_YT_WAVE12_L2CONTEXT_REGISTRATION.md turned into running code: skip
L2 on the wrong kind of day, using only what the recording shows at the
moment of each trade (any hour, the morning included).

    A        the recent average daily range (wave nine's measure)
    TREND    remove a fade against a strong day trend: price at least
             0.25 x A from the session VWAP and the trade against it
    BIG DAY  remove a trade once the session's range so far is at least
             1.0 x A

    TR-ALL / TR-FIRST / BD-ALL / BD-FIRST: kept minus removed, net
    points per trade, session-clustered, Holm over four on NQ

    python3 mrofyt_l2context.py "<capture>" --out w12.json       # DEV: describes
    python3 mrofyt_l2context.py "<replay folder>" --holdout --out w12_replay.json
    python3 mrofyt_l2context.py "<capture>" --unblind --out w12_eval.json  # CHECKPOINT
    (--calendar events.csv adds an event-day split, described only)

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_earlylevels as E
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_smt as SMT

W12_VERSION = 'MROF-YT-W12-L2CONTEXT-1.0'
REGISTRATION = 'MROF_YT_WAVE12_L2CONTEXT_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'

TREND_K = 0.25
BIG_K = 1.0
MIN_SIDE = 20
FILTERS = (('TREND', 'strong trend against the fade'),
           ('BIG', 'big day so far'))
TESTS = (('TR-ALL', 'ALL', 'TREND'), ('TR-FIRST', 'FIRST', 'TREND'),
         ('BD-ALL', 'ALL', 'BIG'), ('BD-FIRST', 'FIRST', 'BIG'))
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# the runner: wave eleven's, plus the day's context on every L2 fire
# ---------------------------------------------------------------------
class ContextRunner(E.LevelsRunner):
    """Wave eleven's runner; every L2 / L4 fire also carries the session
    VWAP and the session's high-to-low so far. Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        E.LevelsRunner.__init__(self, capture_dir, unblind=unblind,
                                holdout=holdout, **kw)
        self.ledger['wave12'] = dict(version=W12_VERSION)

    def _w3_fire(self, st, pat, direction, t, ap, g):
        E.LevelsRunner._w3_fire(self, st, pat, direction, t, ap, g)
        if ap is not None and pat in LB.FAMILIES:
            rng = None
            if st.run_high is not None and st.run_low is not None:
                rng = st.run_high - st.run_low
            self.w3_fires[-1].update(ctx_vwap=st.levels.get('SESSION_VWAP'),
                                     ctx_range=rng)


# ---------------------------------------------------------------------
# the filters
# ---------------------------------------------------------------------
def classify(direction, mid, vwap, day_range, a):
    """{'TREND': 'kept' | 'removed' | None, 'BIG': ...}; None when the
    filter cannot decide (no A, no VWAP, no range so far)."""
    out = dict(TREND=None, BIG=None)
    if a is None or a <= 0:
        return out
    if vwap is not None and mid is not None:
        dev = mid - vwap
        strong = abs(dev) >= TREND_K * a - 1e-9
        against = (dev > 0 and direction < 0) or (dev < 0 and direction > 0)
        out['TREND'] = 'removed' if strong and against else 'kept'
    if day_range is not None:
        out['BIG'] = 'removed' if day_range >= BIG_K * a - 1e-9 else 'kept'
    return out


def context_events(r):
    """Wave nine's L2 events (test number, recent range) with the first
    fire's VWAP and range so far."""
    first = {}
    for f in r.w3_fires:
        if f['family'] == 'L2':
            first.setdefault((f['instrument'], f['session'], f['family'],
                              f['direction'], f['t']), f)
    out = []
    for e in W.target_events(r):
        f = first[(e['instrument'], e['session'], e['family'],
                   e['direction'], e['t'])]
        out.append(dict(e, ctx_vwap=f.get('ctx_vwap'),
                        ctx_range=f.get('ctx_range')))
    return out


def score(r, events):
    """[(event + its classes and net points, outcome, gross ticks, risk
    ticks, seconds)] with wave six's T1 exit; unresolved dropped."""
    paths = {k: BM.compress(ts, ps) for k, (ts, ps) in r.series.items()
             if len(ts)}
    out = []
    for e in events:
        key = (e['instrument'], e.get('run'))
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        o, v, s = LB.path_exit(ts, ps, i, e['direction'], LB.TARGET,
                               LB.FIXED_STOP)
        if o == 'UNRESOLVED':
            continue
        e = dict(e, p0=ps[i], net=W.net_points(e['instrument'], o, v),
                 cls=classify(e['direction'], ps[i], e['ctx_vwap'],
                              e['ctx_range'], e['recent_range']))
        out.append((e, o, v, LB.FIXED_STOP, s))
    return out


def _side_stats(rows, inst):
    st = LB.test_stats(rows, inst)
    one = LB.test_stats(V.one_at_a_time(rows), inst)
    return dict(n=st['n'], win=st.get('hit'), net_points=st.get('net_points'),
                one_at_a_time=dict((k, one.get(k)) for k in
                                   ('n', 'hit', 'net_points')))


def diff_row(rows, inst, flt):
    kept = [x for x in rows if x[0]['cls'][flt] == 'kept']
    removed = [x for x in rows if x[0]['cls'][flt] == 'removed']
    d = SMT.diff_stats([(x[0]['session'], x[0]['net']) for x in kept],
                       [(x[0]['session'], x[0]['net']) for x in removed])
    return dict(diff_points=d.get('diff'), t=d.get('t'), p=d.get('p'),
                ci95=d.get('ci95'), sessions=d.get('months', 0),
                kept=_side_stats(kept, inst),
                removed=_side_stats(removed, inst),
                undecided=sum(1 for x in rows if x[0]['cls'][flt] is None))


def table(scored, keep=None, calendar=None):
    out = {}
    for inst in sorted({x[0]['instrument'] for x in scored}):
        mine = [x for x in scored if x[0]['instrument'] == inst and
                (keep is None or keep(x[0]['session']))]
        sets = dict(ALL=mine, FIRST=[x for x in mine
                                     if x[0].get('test_no') == 1])
        tests = []
        for tid, which, flt in TESTS:
            row = diff_row(sets[which], inst, flt)
            row.update(test=tid, trades=which, filter=flt)
            tests.append(row)
        rej = BM.holm([x.get('p') for x in tests], HOLM_ALPHA)
        for x, rj in zip(tests, rej):
            if x['kept']['n'] < MIN_SIDE or x['removed']['n'] < MIN_SIDE:
                x['status'] = 'NOT TESTED'
            elif rj and (x['diff_points'] or 0) > 0 and x.get('ci95') and \
                    x['ci95'][0] > 0:
                x['status'] = 'FILTER HELPS'
            else:
                x['status'] = 'DOES NOT HELP'
        res = dict(tests=tests, every_l2=_side_stats(mine, inst))
        if calendar:
            res['calendar'] = dict(
                event_days=_side_stats([x for x in mine
                                        if x[0]['session'] in calendar], inst),
                other_days=_side_stats([x for x in mine
                                        if x[0]['session'] not in calendar],
                                       inst))
        out[inst] = res
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def read_calendar(path):
    out = {}
    for line in open(path, encoding='utf-8-sig'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        day, _sep, what = line.partition(',')
        day = day.strip()
        if len(day) != 8 or not day.isdigit():
            raise ValueError('not YYYYMMDD,EVENT: %r' % line)
        out[day] = what.strip() or 'event'
    return out


def run(capture_dir, unblind=False, holdout=False, calendar=None,
        max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = ContextRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    sc = score(r, context_events(r))
    tab = table(sc, keep, calendar)
    if not (unblind or holdout):
        for v in tab.values():
            for x in v['tests']:
                x['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave12=W12_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({x[0]['session'] for x in sc
                                          if keep(x[0]['session'])}),
               calendar_days=sorted(calendar) if calendar else None,
               results=tab)
    return rep, r


def _fmt(s):
    if not s.get('n'):
        return 'n=0'
    one = s['one_at_a_time']
    return 'n=%d win %.0f%% net %+.2f (one at a time %d, %+.2f)' % (
        s['n'], 100 * s['win'], s['net_points'], one.get('n') or 0,
        one.get('net_points') or 0.0)


def text(rep):
    lines = ['%s  %s' % (rep['wave12'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'L2 trades, 25 / 15 / 30 min after costs; diff = kept minus '
             'removed, net points per trade']
    names = dict(FILTERS)
    for inst, v in rep['results'].items():
        lines.append('')
        lines.append('%s  every L2: %s' % (inst, _fmt(v['every_l2'])))
        for x in v['tests']:
            lines.append('  %-8s %-5s %-34s diff %s  t %s  p %s  %s' % (
                x['test'], x['trades'], names[x['filter']],
                '-' if x['diff_points'] is None else
                '%+.2f' % x['diff_points'],
                '-' if x.get('t') is None else '%.2f' % x['t'],
                '-' if x.get('p') is None else '%.4f' % x['p'],
                x['status']))
            lines.append('           kept:    %s' % _fmt(x['kept']))
            lines.append('           removed: %s   (undecided %d)' % (
                _fmt(x['removed']), x['undecided']))
        if v.get('calendar'):
            lines.append('  event days: %s' % _fmt(v['calendar']['event_days']))
            lines.append('  other days: %s' % _fmt(v['calendar']['other_days']))
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
        version=W12_VERSION, sessions=rep['sessions_inspected']))
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
                         exposed_by=W12_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W12_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W12_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W12_VERSION)
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
    cal = None
    if arg('--calendar'):
        try:
            cal = read_calendar(arg('--calendar'))
        except (OSError, ValueError) as exc:
            print('STOPPED: the calendar file cannot be used (%s). One line '
                  'per day: YYYYMMDD,EVENT' % exc)
            return 2
    if unblind or holdout:
        print('*** %s: this read scores the four registered tests once. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, cal, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-twelve report -> %s' % out)
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
