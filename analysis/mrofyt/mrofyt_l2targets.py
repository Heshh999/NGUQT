#!/usr/bin/env python3
"""mrofyt_l2targets.py - MROF-YT-W9-L2TARGETS-1.0

MROF_YT_WAVE9_L2TARGETS_REGISTRATION.md turned into running code: wave
eight's L2 trades with the same 15-point stop and 30-minute limit, and
three targets side by side on the same trades.

    FIXED       25 points, as before
    NEXT LEVEL  the nearest of yesterday's high / low, the overnight high
                / low, last week's high / low and the session VWAP that is
                at least 10 points ahead; 2 ticks short of it; no cap;
                none: 25 points
    SCALED      25 points x (recent average daily range / its DEV
                median), 10-75 points; under 5 recent sessions: 25

    N-ALL / S-ALL      every L2: NEXT LEVEL / SCALED minus FIXED
    N-FIRST / S-FIRST  first test of the level (wave eight's V1)

The test is the per-trade net difference against FIXED, its mean above
zero, session-clustered, Holm over the four on NQ. Beside it, not
tested: how far each trade ran in its favour (MFE) without a target.

    python3 mrofyt_l2targets.py "<capture>" --out w9.json \\
            --frozen-out w9_frozen.json           # DEV: describes, freezes A_ref
    python3 mrofyt_l2targets.py "<replay folder>" --evaluate w9_frozen.json \\
            --holdout --out w9_replay.json
    python3 mrofyt_l2targets.py "<capture>" --evaluate w9_frozen.json \\
            --unblind --out w9_eval.json          # CHECKPOINT ONLY

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
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W9_VERSION = 'MROF-YT-W9-L2TARGETS-1.0'
REGISTRATION = 'MROF_YT_WAVE9_L2TARGETS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
TICK = SIG.TICK

FIXED = LB.TARGET                        # 100 ticks
STOP = LB.FIXED_STOP                     # 60 ticks
TARGET_LEVELS = BM.RANGE_LEVELS + ('SESSION_VWAP',)
NEXT_MIN_TICKS = 40.0
NEXT_SHORT_TICKS = 2.0
RANGE_SESSIONS, RANGE_MIN_SESSIONS = 14, 5
SCALED_MIN, SCALED_MAX = 40.0, 300.0
MFE_MARKS = (25, 40, 60, 100)            # points

TESTS = (('N-ALL', 'ALL', 'NEXT'), ('S-ALL', 'ALL', 'SCALED'),
         ('N-FIRST', 'FIRST', 'NEXT'), ('S-FIRST', 'FIRST', 'SCALED'))
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# the targets
# ---------------------------------------------------------------------
def next_level_target(direction, p0, levels):
    """Ticks to 2 ticks short of the nearest level at least 40 ticks
    ahead; FIXED when there is none. levels: prices (None ignored)."""
    ahead = sorted(direction * (px - p0) / TICK for px in levels
                   if px is not None and
                   direction * (px - p0) / TICK >= NEXT_MIN_TICKS - 1e-9)
    if not ahead:
        return FIXED, False
    return ahead[0] - NEXT_SHORT_TICKS, True


def scaled_target(a, a_ref):
    """100 ticks x A / A_ref, clamped to 40..300; FIXED without A."""
    if a is None or not a_ref:
        return FIXED, False
    return min(SCALED_MAX, max(SCALED_MIN, FIXED * a / a_ref)), True


def mfe(ts, ps, i, d, stop=STOP, limit_s=LB.LIMIT_S):
    """Ticks of the furthest mid in the trade's favour from entry i until
    the stop is touched or the limit passes, never stopped at a target;
    None when the run ends before either."""
    t_end = ts[i] + limit_s
    p0, best = ps[i], 0.0
    j = i + 1
    while j < len(ps) and ts[j] <= t_end:
        x = d * (ps[j] - p0) / TICK
        if x <= -stop:
            return best
        if x > best:
            best = x
        j += 1
    if ts[-1] < t_end:
        return None
    return best


# ---------------------------------------------------------------------
# the runner: wave eight's, plus the levels and recent range at a fire
# ---------------------------------------------------------------------
class TargetRunner(V.L2VariantRunner):
    """Wave eight's runner; every session's high-to-low range is kept
    at its close, and every L2/L4 fire carries the target levels the
    runner holds and the recent average range. Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        V.L2VariantRunner.__init__(self, capture_dir, unblind=unblind,
                                   holdout=holdout, **kw)
        self.ranges = collections.defaultdict(list)   # inst -> [(ses, pts)]
        self.ledger['wave9'] = dict(version=W9_VERSION)

    def _record_range(self, st):
        if st.session and st.run_high is not None and \
                st.run_low is not None:
            self.ranges[st.instrument].append(
                (st.session, st.run_high - st.run_low))

    def recent_range(self, inst, session):
        prev = [r for s, r in self.ranges[inst] if s < session]
        prev = prev[-RANGE_SESSIONS:]
        if len(prev) < RANGE_MIN_SESSIONS:
            return None
        return sum(prev) / len(prev)

    def _close_session(self, st):
        self._record_range(st)
        V.L2VariantRunner._close_session(self, st)

    def _mark_run(self, st):
        mark = V.L2VariantRunner._mark_run(self, st)
        mark['w9'] = copy.deepcopy(self.ranges)
        return mark

    def _unwind_run(self, st, mark):
        V.L2VariantRunner._unwind_run(self, st, mark)
        self.ranges = mark['w9']

    def _w3_fire(self, st, pat, direction, t, ap, g):
        V.L2VariantRunner._w3_fire(self, st, pat, direction, t, ap, g)
        if ap is not None and pat in LB.FAMILIES:
            self.w3_fires[-1].update(
                target_levels=[st.levels.get(k) for k in TARGET_LEVELS],
                recent_range=self.recent_range(st.instrument, st.session))


# ---------------------------------------------------------------------
# events and scoring
# ---------------------------------------------------------------------
def target_events(r):
    """Wave eight's L2 events, each with its first fire's target levels
    and recent average range."""
    first = {}
    for f in r.w3_fires:
        if f['family'] == 'L2':
            first.setdefault((f['instrument'], f['session'], f['family'],
                              f['direction'], f['t']), f)
    out = []
    for e in V.variant_events(r):
        f = first[(e['instrument'], e['session'], e['family'],
                   e['direction'], e['t'])]
        out.append(dict(e, target_levels=f.get('target_levels') or [],
                        recent_range=f.get('recent_range')))
    return out


def a_ref(events, inst):
    """The DEV median recent range of one instrument's L2 events."""
    vals = sorted(e['recent_range'] for e in events
                  if e['instrument'] == inst and
                  e.get('recent_range') is not None)
    return vals[len(vals) // 2] if vals else None


def score_targets(r, events, refs):
    """[(event, {FIXED|NEXT|SCALED: (outcome, ticks, target, real)},
    mfe ticks)] for every event whose three versions all resolved."""
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
        d, p0 = e['direction'], ps[i]
        tn, real_n = next_level_target(d, p0, e['target_levels'])
        tsc, real_s = scaled_target(e['recent_range'],
                                    refs.get(e['instrument']))
        res = {}
        for name, tgt, real in (('FIXED', FIXED, True), ('NEXT', tn, real_n),
                                ('SCALED', tsc, real_s)):
            o, v, _s = LB.path_exit(ts, ps, i, d, tgt, STOP)
            res[name] = (o, v, tgt, real)
        if any(x[0] == 'UNRESOLVED' for x in res.values()):
            continue
        out.append((e, res, mfe(ts, ps, i, d)))
    return out


def net_points(inst, outcome, ticks):
    return (ticks - CO.cost_ticks(inst, 'STOP' if outcome == 'STOP'
                                  else 'TARGET')) * TICK


def paired_stats(rows, inst, name):
    """rows: [(event, res, mfe)]; the session-clustered mean of
    net(name) - net(FIXED), in points."""
    if not rows:
        return dict(n=0, sessions=0)
    cl, own, base = [], [], []
    for e, res, _m in rows:
        a = net_points(inst, res[name][0], res[name][1])
        b = net_points(inst, res['FIXED'][0], res['FIXED'][1])
        own.append((a, res[name][0], res[name][2], res[name][3]))
        base.append(b)
        cl.append((e['session'], a - b, 0.0, a - b))
    st = DI.cluster_stats(cl)
    n = len(rows)
    return dict(
        n=n, sessions=st.get('sessions', 0),
        mean_diff_points=st.get('lift'), t=st.get('t'), p=st.get('p'),
        ci95_diff_points=st.get('ci95'),
        net_points=round(sum(x[0] for x in own) / n, 3),
        win=round(sum(1 for x in own if x[1] == 'TARGET') / n, 4),
        fixed_net_points=round(sum(base) / n, 3),
        mean_target_points=round(sum(x[2] for x in own) / n * TICK, 2),
        fell_back_to_25=sum(1 for x in own if not x[3]),
        outcomes=dict(collections.Counter(x[1] for x in own)))


def mfe_table(rows):
    vals = [m for _e, _r, m in rows if m is not None]
    if not vals:
        return dict(n=0)
    out = dict(n=len(vals))
    for mk in MFE_MARKS:
        out['reach_%d' % mk] = round(
            sum(1 for v in vals if v * TICK >= mk) / len(vals), 3)
    s = sorted(vals)
    out['median_points'] = s[len(s) // 2] * TICK
    return out


def table(scored, keep=None):
    """{instrument: dict(tests=[...], mfe=...)}; Holm over the four."""
    out = {}
    for inst in sorted({e['instrument'] for e, _r, _m in scored}):
        mine = [x for x in scored if x[0]['instrument'] == inst and
                (keep is None or keep(x[0]['session']))]
        sets = dict(ALL=mine,
                    FIRST=[x for x in mine if x[0].get('test_no') == 1])
        tests = []
        for tid, which, name in TESTS:
            st = paired_stats(sets[which], inst, name)
            st.update(test=tid, trades=which, target=name)
            tests.append(st)
        rej = BM.holm([x.get('p') for x in tests], HOLM_ALPHA)
        for x, rj in zip(tests, rej):
            if x['n'] < MIN_EVENTS:
                x['status'] = 'NOT TESTED'
            elif rj and x['mean_diff_points'] > 0 and \
                    x.get('ci95_diff_points') and \
                    x['ci95_diff_points'][0] > 0:
                x['status'] = 'BEATS 25'
            else:
                x['status'] = 'NO BETTER'
        out[inst] = dict(tests=tests, mfe=dict(
            ALL=mfe_table(sets['ALL']), FIRST=mfe_table(sets['FIRST'])))
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run_dev(capture_dir, max_sessions=None):
    r = TargetRunner(capture_dir, max_sessions=max_sessions)
    led = r.run()
    ev = target_events(r)
    refs = {i: a_ref(ev, i) for i in sorted({e['instrument'] for e in ev})}
    frozen = dict(wave9=W9_VERSION, registration=REGISTRATION, a_ref=refs,
                  rule='A_ref = the median recent average daily range (the '
                       'last 14 sessions at most, 5 at least) of the DEV L2 '
                       'events per instrument, in points; registration §2')
    rep = dict(wave9=W9_VERSION, registration=REGISTRATION, mode='dev',
               evaluated_on='DEV (<= %s): describes, not a test' % DEV_END,
               note='DEV sessions were seen before this registration: '
                    'these numbers describe, they do not test',
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               a_ref=refs, results=table(score_targets(r, ev, refs)))
    return rep, frozen, r


def run_evaluate(capture_dir, frozen, unblind=False, holdout=False,
                 max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = TargetRunner(capture_dir, unblind=unblind, holdout=holdout,
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
        which = 'DEV (<= %s), a reproduction check' % DEV_END
    ev = target_events(r)
    res = table(score_targets(r, ev, frozen['a_ref']), keep)
    if not (unblind or holdout):
        for v in res.values():
            for x in v['tests']:
                x['status'] += ' (DEV reproduction, not a verdict)'
    rep = dict(wave9=W9_VERSION, registration=REGISTRATION, mode='evaluate',
               evaluated_on=which, unblind=unblind, holdout=holdout,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in ev
                                          if keep(e['session'])}),
               a_ref=frozen['a_ref'], results=res)
    return rep, r


def text(rep):
    lines = ['%s  %s' % (rep['wave9'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-')]
    if rep.get('note'):
        lines.append('NOTE: ' + rep['note'])
    lines.append('typical recent daily range (A_ref, points): %s'
                 % rep['a_ref'])
    lines.append('stop 15 pts, 30 min; net = after commission, a tick of '
                 'spread and a tick of slip on stops; diff = net minus the '
                 'fixed 25 on the same trades')
    for inst, v in rep['results'].items():
        lines.append('')
        lines.append('%-4s %-8s %5s %4s %6s %8s %8s %8s %8s %7s %8s  %s' % (
            inst, 'test', 'n', 'ses', 'win', 'avg tgt', 'net pts',
            'fixed', 'diff', 't', 'p', 'status'))
        for x in v['tests']:
            if not x['n']:
                lines.append('     %-8s     0' % x['test'])
                continue
            lines.append('     %-8s %5d %4d %5.0f%% %8.1f %+8.2f %+8.2f '
                         '%+8.2f %7s %8s  %s' % (
                             x['test'], x['n'], x['sessions'],
                             100 * x['win'], x['mean_target_points'],
                             x['net_points'], x['fixed_net_points'],
                             x['mean_diff_points'] or 0.0,
                             '-' if x.get('t') is None else '%.2f' % x['t'],
                             '-' if x.get('p') is None else '%.4f' % x['p'],
                             x['status']))
        for which in ('ALL', 'FIRST'):
            m = v['mfe'][which]
            if not m.get('n'):
                continue
            lines.append('  how far %s trades ran in their favour before '
                         'the stop or 30 min (no target): n=%d, median %.1f '
                         'pts; reached 25 / 40 / 60 / 100 pts: %s' % (
                             which, m['n'], m['median_points'],
                             ' / '.join('%.0f%%' % (100 * m['reach_%d' % k])
                                        for k in MFE_MARKS)))
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
        version=W9_VERSION, sessions=rep['sessions_inspected']))
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
                         exposed_by=W9_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W9_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W9_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W9_VERSION)
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
    ev = arg('--evaluate')
    if (unblind or holdout) and not ev:
        print('REFUSED: --unblind and --holdout are only for --evaluate with '
              'the frozen file. A plain run reads DEV sessions only.')
        return 2
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    try:
        if ev:
            try:
                frozen = json.load(open(ev))
                if not isinstance(frozen.get('a_ref'), dict):
                    raise ValueError
            except (OSError, ValueError, AttributeError):
                print('STOPPED: %s is not a wave-nine frozen file (the '
                      '--frozen-out of the DEV run)' % ev)
                return 2
            if unblind or holdout:
                print('*** %s: this read scores the four registered tests '
                      'once. ***\n' % ('UNBLIND' if unblind else 'HOLDOUT'))
            rep, _r = run_evaluate(d, frozen, unblind, holdout, ms)
        else:
            rep, frozen, _r = run_dev(d, ms)
            fo = arg('--frozen-out')
            if fo:
                json.dump(frozen, open(fo, 'w'), indent=1)
                print('frozen A_ref -> %s' % fo)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-nine report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if ev and holdout:
        n = record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER))
        print('replay holdout read recorded (%d read(s))' % n)
    if ev and unblind:
        n = record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER))
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
