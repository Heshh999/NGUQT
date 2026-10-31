#!/usr/bin/env python3
"""mrofyt_l2variants.py - MROF-YT-W8-L2VARIANTS-1.0

MROF_YT_WAVE8_L2VARIANTS_REGISTRATION.md turned into running code: wave
three's L2 (fade a failed break of a daily range level), exactly as wave
six scores it, restricted the two ways a trader would, or held briefly.

    V1  FIRST TEST     the first approach to that level this session
    V2  MORNING        first fire 09:30:00-11:29:59 ET
    V3  BOTH           V1 and V2 (the operator's pick)
    V4  QUICK          every L2, out at the mid after 5 minutes
    V0  every L2, wave six's T1 -- reference, not tested

Every variant: target 100 ticks (25 points), stop 60 ticks (15 points),
1800 s (V4: 300 s), mid-to-mid, then mrofyt_costs's round trip. The
test is the mean NET result per trade above zero, session-clustered,
Holm over the four on NQ. Nothing is frozen from DEV: every setting is
in the registration.

    python3 mrofyt_l2variants.py "<capture>" --out w8.json      # DEV: describes
    python3 mrofyt_l2variants.py "<replay folder>" --holdout --out w8_replay.json
    python3 mrofyt_l2variants.py "<capture>" --unblind --out w8_eval.json  # CHECKPOINT ONLY

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import copy
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_costs as CO
import mrofyt_discover as DI
import mrofyt_levelbreak as LB
import mrofyt_pilot as PI
import mrofyt_runner as RUN

W8_VERSION = 'MROF-YT-W8-L2VARIANTS-1.0'
REGISTRATION = 'MROF_YT_WAVE8_L2VARIANTS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'

MORNING_FROM, MORNING_TO = 9.5 * 3600, 11.5 * 3600
QUICK_S = 300.0
VARIANTS = (('V1', 'FIRST TEST'), ('V2', 'MORNING'),
            ('V3', 'FIRST TEST + MORNING'), ('V4', 'QUICK 5 MIN'))
REFERENCE = ('V0', 'EVERY L2 (wave six T1)')
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


def in_morning(t):
    return MORNING_FROM <= RUN.sod_seconds(t) < MORNING_TO


# ---------------------------------------------------------------------
# the runner: wave six's, plus the test number of every approach
# ---------------------------------------------------------------------
class L2VariantRunner(LB.LevelBreakRunner):
    """Wave six's runner; every approach is numbered within its level and
    session, and every L2/L4 fire carries its approach's number. Hooks
    only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        LB.LevelBreakRunner.__init__(self, capture_dir, unblind=unblind,
                                     holdout=holdout, **kw)
        self.tests_seen = collections.Counter()   # (inst, level) -> n
        self.test_no = {}                          # (inst, approach) -> n
        self.ledger['wave8'] = dict(version=W8_VERSION)

    def _count_test(self, st, ap):
        k = (st.instrument, ap.level_id)
        self.tests_seen[k] += 1
        self.test_no[(st.instrument, ap.id)] = self.tests_seen[k]

    def _select_wall(self, st, ap, t):
        # the runner calls this exactly once, when it opens an approach
        self._count_test(st, ap)
        LB.LevelBreakRunner._select_wall(self, st, ap, t)

    def _close_session(self, st):
        LB.LevelBreakRunner._close_session(self, st)
        for k in [k for k in self.tests_seen if k[0] == st.instrument]:
            del self.tests_seen[k]

    def _mark_run(self, st):
        mark = LB.LevelBreakRunner._mark_run(self, st)
        mark['w8'] = (collections.Counter(self.tests_seen),
                      copy.copy(self.test_no))
        return mark

    def _unwind_run(self, st, mark):
        LB.LevelBreakRunner._unwind_run(self, st, mark)
        self.tests_seen, self.test_no = mark['w8']

    def _w3_fire(self, st, pat, direction, t, ap, g):
        LB.LevelBreakRunner._w3_fire(self, st, pat, direction, t, ap, g)
        if ap is not None and pat in LB.FAMILIES:
            self.w3_fires[-1]['test_no'] = self.test_no.get(
                (st.instrument, ap.id))


# ---------------------------------------------------------------------
# events and scoring
# ---------------------------------------------------------------------
def variant_events(r):
    """Wave six's de-duplicated L2 events, each with its first fire's
    test number and whether it came in the morning window."""
    first = {}
    for f in r.w3_fires:
        if f['family'] == 'L2':
            first.setdefault((f['instrument'], f['session'], f['family'],
                              f['direction'], f['t']), f)
    out = []
    for e in LB.level_events(r):
        if e['family'] != 'L2':
            continue
        f = first[(e['instrument'], e['session'], e['family'],
                   e['direction'], e['t'])]
        e = dict(e, test_no=f.get('test_no'), morning=in_morning(e['t']))
        out.append(e)
    return out


def takes(vid, e):
    if vid == 'V1':
        return e['test_no'] == 1
    if vid == 'V2':
        return e['morning']
    if vid == 'V3':
        return e['test_no'] == 1 and e['morning']
    return True                                    # V4 and V0


def score_variants(r, events):
    """{variant id: [(event, outcome, gross ticks, risk ticks, seconds)]}."""
    paths = {k: BM.compress(ts, ps) for k, (ts, ps) in r.series.items()
             if len(ts)}
    out = collections.defaultdict(list)
    for e in events:
        key = (e['instrument'], e.get('run'))
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        d = e['direction']
        fixed = LB.path_exit(ts, ps, i, d, LB.TARGET, LB.FIXED_STOP)
        quick = LB.path_exit(ts, ps, i, d, LB.TARGET, LB.FIXED_STOP,
                             limit_s=QUICK_S)
        for vid in ('V0', 'V1', 'V2', 'V3', 'V4'):
            res = quick if vid == 'V4' else fixed
            if not takes(vid, e) or res[0] == 'UNRESOLVED':
                continue
            out[vid].append((e, res[0], res[1], LB.FIXED_STOP, res[2]))
    return out


def one_at_a_time(rows):
    taken, busy = [], None
    for x in sorted(rows, key=lambda x: x[0]['t']):
        if busy is not None and x[0]['t'] < busy:
            continue
        taken.append(x)
        busy = x[0]['t'] + x[4]
    return taken


def table(scored, keep=None):
    """{instrument: [V0 reference, V1..V4 tests]}; Holm over V1..V4."""
    insts = sorted({x[0]['instrument'] for rows in scored.values()
                    for x in rows})
    out = {}
    for inst in insts:
        rows_of = {}
        for vid in ('V0', 'V1', 'V2', 'V3', 'V4'):
            rows_of[vid] = [x for x in scored.get(vid, [])
                            if x[0]['instrument'] == inst and
                            (keep is None or keep(x[0]['session']))]
        tests = []
        for vid, name in (REFERENCE,) + VARIANTS:
            st = LB.test_stats(rows_of[vid], inst)
            one = LB.test_stats(one_at_a_time(rows_of[vid]), inst)
            st.update(test=vid, name=name,
                      one_at_a_time=dict((k, one.get(k)) for k in
                                         ('n', 'hit', 'net_points')))
            tests.append(st)
        rej = BM.holm([x.get('p') for x in tests[1:]], HOLM_ALPHA)
        tests[0]['status'] = 'REFERENCE'
        for x, rj in zip(tests[1:], rej):
            if x['n'] < MIN_EVENTS:
                x['status'] = 'NOT TESTED'
            elif rj and x['net_points'] > 0 and x.get('ci95_net_ticks') and \
                    x['ci95_net_ticks'][0] > 0:
                x['status'] = 'PROMISING'
            else:
                x['status'] = 'NO SIGNAL'
        out[inst] = tests
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = L2VariantRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    ev = variant_events(r)
    tab = table(score_variants(r, ev), keep)
    if not (unblind or holdout):
        for tests in tab.values():
            for x in tests[1:]:
                x['status'] += ' (DEV, seen before the registration)'
    mine = [e for e in ev if keep(e['session'])]
    rep = dict(wave8=W8_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in mine}),
               events=dict(sorted(collections.Counter(
                   '%s test %s%s' % (e['instrument'],
                                     e['test_no'] if e['test_no'] and
                                     e['test_no'] < 3 else '3+',
                                     ' morning' if e['morning'] else '')
                   for e in mine).items())),
               tests=tab)
    return rep, r


def text(rep):
    lines = ['%s  %s' % (rep['wave8'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'L2 events: %s' % (', '.join('%s %d' % kv for kv in
                                          rep['events'].items()) or '-'),
             'target 25 pts, stop 15 pts, 30 min (V4: 5 min); net = after '
             'commission, a tick of spread and a tick of slip on stops']
    for inst, tests in rep['tests'].items():
        lines.append('')
        lines.append('%-4s %-4s %-22s %5s %4s %6s %8s %7s %8s  %-11s %s' % (
            inst, 'id', 'variant', 'n', 'ses', 'win', 'net pts', 't', 'p',
            'one-at-a-time', 'status'))
        for x in tests:
            one = x['one_at_a_time']
            lines.append('     %-4s %-22s %5d %4d %6s %+8.2f %7s %8s  %-13s %s'
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
        version=W8_VERSION, sessions=rep['sessions_inspected']))
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
                         exposed_by=W8_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W8_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W8_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W8_VERSION)
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
        print('*** %s: this read scores the four registered variants '
              'once. ***\n' % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-eight report -> %s' % out)
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
