#!/usr/bin/env python3
"""mrofyt_scaledbracket.py - MROF-YT-W18-SCALEDBRACKET-1.0

MROF_YT_WAVE18_SCALEDBRACKET_REGISTRATION.md turned into running code: on
wave fourteen's trades (the first L2 signal at each level per session),
the stop AND the target scaled by k = recent range / A_ref (wave nine's
measure and frozen reference, clamped 0.4 .. 3.0), against the fixed
25 / 15 on the same trades.

    B1 POINTS  scaled minus fixed, net points a contract
    B2 RISK    scaled minus fixed, net in units of each trade's own stop
               (the same dollars risked on every trade)
    session-clustered, Holm over two on NQ

    python3 mrofyt_scaledbracket.py "<capture>" --a-ref w9_frozen.json --out w18.json
    python3 mrofyt_scaledbracket.py "<capture>" --unblind --a-ref w9_frozen.json --out w18_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_costs as CO
import mrofyt_discover as DI
import mrofyt_l2firstsignal as FS
import mrofyt_l2targets as W
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W18_VERSION = 'MROF-YT-W18-SCALEDBRACKET-1.0'
REGISTRATION = 'MROF_YT_WAVE18_SCALEDBRACKET_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
TICK = SIG.TICK
K_MIN, K_MAX = W.SCALED_MIN / W.FIXED, W.SCALED_MAX / W.FIXED   # 0.4, 3.0
MIN_TRADES = FS.MIN_TRADES
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


class ScaledBracketRunner(W.TargetRunner):
    """Wave nine's runner (it keeps every session's range), unchanged; the
    ledger names wave eighteen."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        W.TargetRunner.__init__(self, capture_dir, unblind=unblind,
                                holdout=holdout, **kw)
        self.ledger['wave18'] = dict(version=W18_VERSION)


def scale(a, a_ref):
    """(k, clamped) for a recent range a; (None, False) without one."""
    if a is None or not a_ref:
        return None, False
    raw = a / a_ref
    k = min(K_MAX, max(K_MIN, raw))
    return k, k != raw


def net_points(inst, outcome, gross_ticks):
    return (gross_ticks - CO.cost_ticks(
        inst, 'STOP' if outcome == 'STOP' else 'TARGET')) * TICK


def brackets(r, events, a_ref):
    """One record per trade both brackets resolve, and the count left out
    for want of a recent range."""
    paths = V.compressed_paths(r)
    out, no_range = [], 0
    for e in events:
        inst = e['instrument']
        k, clamped = scale(r.recent_range(inst, e['session']),
                           (a_ref or {}).get(inst))
        if k is None:
            no_range += 1
            continue
        key = (inst, e.get('run'))
        if key not in paths:
            continue
        ts, ps = paths[key]
        i = bisect.bisect_right(ts, e['t']) - 1
        if i < 0:
            continue
        stop_t, tgt_t = round(LB.FIXED_STOP * k), round(LB.TARGET * k)
        fx = LB.path_exit(ts, ps, i, e['direction'], LB.TARGET,
                          LB.FIXED_STOP)
        sc = LB.path_exit(ts, ps, i, e['direction'], tgt_t, stop_t)
        if fx[0] == 'UNRESOLVED' or sc[0] == 'UNRESOLVED':
            continue
        fn, sn = net_points(inst, fx[0], fx[1]), net_points(inst, sc[0], sc[1])
        out.append(dict(
            instrument=inst, session=e['session'], t=e['t'],
            k=round(k, 4), clamped=clamped, stop_points=stop_t * TICK,
            target_points=tgt_t * TICK, fixed=(fx[0], round(fn, 4)),
            scaled=(sc[0], round(sn, 4)),
            fixed_r=round(fn / (LB.FIXED_STOP * TICK), 4),
            scaled_r=round(sn / (stop_t * TICK), 4)))
    return out, no_range


def _diff_test(recs, a_key, b_key, name):
    d = [(x['session'], x[a_key] - x[b_key]) for x in recs]
    st = DI.cluster_stats([(s, v, 0.0, v) for s, v in d])
    by = collections.defaultdict(float)
    for s, v in d:
        by[s] += v
    out = dict(test=name, n=len(d), sessions=st.get('sessions', 0),
               effect=st.get('lift'), ci95=st.get('ci95'), p=st.get('p'))
    if by:
        best = max(by, key=lambda s: (by[s], s))
        rest = [v for s, v in d if s != best]
        out['without_best_day'] = dict(
            session=best, n=len(rest),
            effect=round(sum(rest) / len(rest), 4) if rest else None)
    return out


def tests(recs, inst):
    for x in recs:
        x['_fs'], x['_ss'] = x['fixed'][1], x['scaled'][1]
    out = [_diff_test(recs, '_ss', '_fs', 'B1'),
           _diff_test(recs, 'scaled_r', 'fixed_r', 'B2')]
    for x in recs:
        del x['_fs'], x['_ss']
    out[0]['name'] = 'POINTS: scaled minus fixed, a contract'
    out[1]['name'] = 'RISK: scaled minus fixed, in stops (R)'
    if inst != PRIMARY:
        for x in out:
            x['status'], x['reasons'] = 'DESCRIBED (not tested)', []
        return out
    rej = BM.holm([x['p'] if x['n'] >= MIN_TRADES else None for x in out],
                  HOLM_ALPHA)
    for x, rj in zip(out, rej):
        if x['n'] < MIN_TRADES:
            x['status'], x['reasons'] = 'NOT ENOUGH TRADES', [
                '%d of the %d needed' % (x['n'], MIN_TRADES)]
            continue
        reasons = []
        if x['effect'] is None or x['effect'] <= 0:
            reasons.append('the scaled bracket does no better')
        elif not x['ci95'] or x['ci95'][0] <= 0:
            reasons.append('could be luck: the 95 % range reaches zero')
        elif not rj:
            reasons.append('could be luck after allowing for two tests '
                           '(Holm)')
        wb = x.get('without_best_day') or {}
        if not reasons and (wb.get('effect') is None or wb['effect'] <= 0):
            reasons.append('rests on one day: without %s it is no better'
                           % wb.get('session'))
        x['status'] = 'NOT PROVEN' if reasons else 'PASS'
        x['reasons'] = reasons
    return out


def describe(recs):
    n = len(recs)
    if not n:
        return dict(n=0)

    def side(key):
        return dict(won=round(sum(1 for x in recs if x[key][0] == 'TARGET')
                              / n, 4),
                    net_points=round(sum(x[key][1] for x in recs) / n, 3))
    return dict(n=n, mean_k=round(sum(x['k'] for x in recs) / n, 3),
                clamped=sum(1 for x in recs if x['clamped']),
                mean_stop_points=round(sum(x['stop_points'] for x in recs)
                                       / n, 2),
                mean_target_points=round(sum(x['target_points']
                                             for x in recs) / n, 2),
                fixed=side('fixed'), scaled=side('scaled'))


_KEEP = ('test', 'name', 'n', 'status')


def run(capture_dir, frozen, unblind=False, holdout=False,
        max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    a_ref = (frozen or {}).get('a_ref')
    if not isinstance(a_ref, dict):
        raise ValueError('wave eighteen needs wave nine\'s frozen file '
                         '(--a-ref w9_frozen.json)')
    r = ScaledBracketRunner(capture_dir, unblind=unblind, holdout=holdout,
                            max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s): secondary test' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s): describes, not a test' % DEV_END
    ev = FS.first_signals([e for e in V.variant_events(r)
                           if keep(e['session'])])
    recs, no_range = brackets(r, ev, a_ref)
    insts = sorted({x['instrument'] for x in recs} | {PRIMARY})
    results = {}
    for inst in insts:
        mine = [x for x in recs if x['instrument'] == inst]
        results[inst] = dict(tests=tests(mine, inst),
                             describe=describe(mine))
    final = unblind or holdout
    withheld = bool(final and len([x for x in recs if x['instrument'] ==
                                   PRIMARY]) < MIN_TRADES)
    if withheld:
        for inst, res in results.items():
            res['tests'] = [dict((k, x[k]) for k in _KEEP)
                            for x in res['tests']]
            for x in res['tests']:
                x['status'] = ('NOT ENOUGH TRADES: results withheld until a '
                               'read holds %d' % MIN_TRADES
                               if inst == PRIMARY else 'withheld')
            res['describe'] = dict(n=res['describe']['n'])
    elif not final:
        for res in results.values():
            for x in res['tests']:
                x['status'] += ' (DEV, seen before the registration)'
    return dict(wave18=W18_VERSION, registration=REGISTRATION,
                evaluated_on=which, unblind=unblind, holdout=holdout,
                withheld=withheld, a_ref=a_ref, no_recent_range=no_range,
                runner=led['runner'],
                sessions_inspected=sorted(led['sessions']),
                sessions_refused=list(r.refused_sessions),
                sessions_evaluated=sorted({x['session'] for x in recs}),
                results=results), r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave18'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'trades: wave fourteen\'s first L2 signals; FIXED 25 / 15 against '
             'SCALED: stop 15 x k and target 25 x k, k = recent 14-session '
             'range / A_ref (0.4 .. 3.0); net after costs; %d left out for '
             'want of a recent range' % rep['no_recent_range']]
    for inst, res in sorted(rep['results'].items(),
                            key=lambda kv: kv[0] != PRIMARY):
        d = res['describe']
        lines.append('')
        lines.append('%s  SCALED BRACKET%s   trades %d' % (
            inst, ' (tested)' if inst == PRIMARY else '', d['n']))
        if rep['withheld']:
            lines.append('   %s' % res['tests'][0]['status'])
            continue
        if d['n']:
            lines.append('   k %.2f on average (clamped %d); stop %.2f, '
                         'target %.2f points on average' % (
                             d['mean_k'], d['clamped'],
                             d['mean_stop_points'], d['mean_target_points']))
            for k, name in (('fixed', 'FIXED 25 / 15'),
                            ('scaled', 'SCALED')):
                lines.append('   %-14s won %.0f%%, net %s a trade' % (
                    name, 100 * d[k]['won'], _pts(d[k]['net_points'])))
        for x in res['tests']:
            ci = x.get('ci95')
            lines.append('   %s %-40s n %3d  %s  95%% %s  p %s -> %s%s' % (
                x['test'], x['name'], x['n'], _pts(x.get('effect')),
                '-' if not ci else '%s..%s' % (_pts(ci[0]), _pts(ci[1])),
                '-' if x.get('p') is None else '%.4f' % x['p'],
                x['status'], (': ' + '; '.join(x['reasons']))
                if x.get('reasons') else ''))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    try:
        frozen = json.load(open(arg('--a-ref'))) if arg('--a-ref') else None
        if not isinstance((frozen or {}).get('a_ref'), dict):
            raise ValueError
    except (OSError, ValueError, TypeError):
        print('STOPPED: wave eighteen needs wave nine\'s frozen file '
              '(--a-ref w9_frozen.json, the --frozen-out of its DEV run)')
        return 2
    if unblind or holdout:
        print('*** %s: this read is wave eighteen\'s registered test. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(argv[0], frozen, unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-eighteen report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W18_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W18_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
