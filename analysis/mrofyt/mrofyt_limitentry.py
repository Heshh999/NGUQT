#!/usr/bin/env python3
"""mrofyt_limitentry.py - MROF-YT-W16B-LIMITENTRY-1.0

MROF_YT_WAVE16_REGISTRATION.md, part 16B, turned into running code: on
wave fourteen's signals (the first L2 signal at each level per session),
a resting limit order 2 or 4 ticks better than the signal mid, live for
60 s, against entering at the signal.

    fill    only when the mid trades a full tick THROUGH the limit within
            60 s (every order ahead in the queue fills first); the trade
            is at the limit price, then 25 / 15 / 30 min from there
    missed  no trade, 0 points
    test    each signal's limit result minus its market result, mean
            above 0, session-clustered, Holm over LIM2 and LIM4 (NQ)

    python3 mrofyt_limitentry.py "<capture>" --out w16b.json              # DEV: describes
    python3 mrofyt_limitentry.py "<capture>" --unblind --out w16b_eval.json

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
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W16B_VERSION = 'MROF-YT-W16B-LIMITENTRY-1.0'
REGISTRATION = 'MROF_YT_WAVE16_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
TICK = SIG.TICK
OFFSETS = (('LIM2', 2), ('LIM4', 4))
LIFE_S = 60.0
MIN_SIGNALS = FS.MIN_TRADES
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


class LimitRunner(FS.FirstSignalRunner):
    """Wave fourteen's runner, unchanged; the ledger names part 16B."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        FS.FirstSignalRunner.__init__(self, capture_dir, unblind=unblind,
                                      holdout=holdout, **kw)
        self.ledger['wave16b'] = dict(version=W16B_VERSION)


def limit_result(ts, ps, i0, d, k, life=LIFE_S, target=LB.TARGET,
                 stop=LB.FIXED_STOP, limit_s=LB.LIMIT_S):
    """(outcome, gross ticks, seconds) of a limit k ticks better than the
    mid at i0: UNFILLED (0), the bracket from the limit price (TARGET,
    STOP, TIMEOUT), or UNRESOLVED when the path ends first."""
    t0 = ts[i0]
    px = ps[i0] - d * k * TICK
    n = len(ps)
    j = i0 + 1
    while j < n and ts[j] <= t0 + life:
        if d * (ps[j] - px) <= -TICK + 1e-9:
            break
        j += 1
    else:
        if ts[-1] < t0 + life:
            return 'UNRESOLVED', None, None
        return 'UNFILLED', 0.0, 0.0
    tf = ts[j]
    t_end = tf + limit_s
    jj = j
    while jj < n and ts[jj] <= t_end:
        x = d * (ps[jj] - px) / TICK
        if x <= -stop:
            return 'STOP', -float(stop), ts[jj] - tf
        if x >= target:
            return 'TARGET', float(target), ts[jj] - tf
        jj += 1
    if ts[-1] < t_end:
        return 'UNRESOLVED', None, None
    kx = bisect.bisect_right(ts, t_end) - 1
    return 'TIMEOUT', d * (ps[kx] - px) / TICK, ts[kx] - tf


def net_points(inst, outcome, gross_ticks):
    if outcome == 'UNFILLED':
        return 0.0
    return (gross_ticks - CO.cost_ticks(
        inst, 'STOP' if outcome == 'STOP' else 'TARGET')) / 4.0


def signal_records(r, events):
    """One record per signal both versions resolve: the market result
    and each limit's (outcome, net points)."""
    ids = {id(e) for e in events}
    market = {id(x[0]): x for x in V.score_variants(r, events).get('V0', [])
              if id(x[0]) in ids}
    paths = V.compressed_paths(r)
    out = []
    for e in events:
        m = market.get(id(e))
        if m is None:
            continue
        ts, ps = paths[(e['instrument'], e['run'])]
        i0 = bisect.bisect_right(ts, e['t']) - 1
        rec = dict(e=e, MARKET=(m[1], net_points(e['instrument'], m[1],
                                                 m[2])))
        for vid, k in OFFSETS:
            oc, g, _s = limit_result(ts, ps, i0, e['direction'], k)
            if oc == 'UNRESOLVED':
                break
            rec[vid] = (oc, net_points(e['instrument'], oc, g))
        else:
            out.append(rec)
    return out


def variant_stats(recs, vid):
    d = [(x['e']['session'], x[vid][1] - x['MARKET'][1]) for x in recs]
    st = DI.cluster_stats([(s, v, 0.0, v) for s, v in d])
    filled = [x for x in recs if x[vid][0] != 'UNFILLED']
    n = len(recs)
    return dict(
        test=vid, n=n, sessions=st.get('sessions', 0),
        improvement=st.get('lift'), t=st.get('t'), p=st.get('p'),
        ci95=st.get('ci95'),
        fill_rate=round(len(filled) / n, 4) if n else None,
        missed_winners=sum(1 for x in recs if x[vid][0] == 'UNFILLED' and
                           x['MARKET'][0] == 'TARGET'),
        net_points=round(sum(x[vid][1] for x in recs) / n, 3) if n else None,
        filled_net_points=round(sum(x[vid][1] for x in filled) /
                                len(filled), 3) if filled else None)


def verdicts(tests, inst):
    if inst != PRIMARY:
        for x in tests:
            x['status'], x['reasons'] = 'DESCRIBED (not tested)', []
        return tests
    rej = BM.holm([x['p'] if x['n'] >= MIN_SIGNALS else None
                   for x in tests], HOLM_ALPHA)
    for x, rj in zip(tests, rej):
        if x['n'] < MIN_SIGNALS:
            x['status'], x['reasons'] = 'NOT ENOUGH TRADES', [
                '%d of the %d signals needed' % (x['n'], MIN_SIGNALS)]
        elif x['improvement'] is None or x['improvement'] <= 0:
            x['status'], x['reasons'] = 'NOT PROVEN', [
                'the limit does no better than the market entry']
        elif not rj or not x.get('ci95') or x['ci95'][0] <= 0:
            x['status'], x['reasons'] = 'NOT PROVEN', [
                'could be luck after allowing for two versions (Holm)']
        else:
            x['status'], x['reasons'] = 'PASS', []
    return tests


_KEEP = ('test', 'n', 'sessions', 'status')


def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = LimitRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    recs = signal_records(r, ev)
    insts = sorted({x['e']['instrument'] for x in recs} | {PRIMARY})
    results = {}
    for inst in insts:
        mine = [x for x in recs if x['e']['instrument'] == inst]
        mk = [x['MARKET'][1] for x in mine]
        results[inst] = dict(
            market=dict(n=len(mk), net_points=round(sum(mk) / len(mk), 3)
                        if mk else None),
            tests=verdicts([variant_stats(mine, vid) for vid, _k in OFFSETS],
                           inst))
    withheld = bool((unblind or holdout) and
                    len([x for x in recs if x['e']['instrument'] ==
                         PRIMARY]) < MIN_SIGNALS)
    if withheld:
        for inst in results:
            results[inst] = dict(
                market=dict(n=results[inst]['market']['n']),
                tests=[dict((k, x[k]) for k in _KEEP)
                       for x in results[inst]['tests']])
            for x in results[inst]['tests']:
                x['status'] = ('NOT ENOUGH TRADES: results withheld until a '
                               'read holds %d' % MIN_SIGNALS
                               if inst == PRIMARY else 'withheld')
    elif not (unblind or holdout):
        for res in results.values():
            for x in res['tests']:
                x['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave16b=W16B_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({x['e']['session'] for x in recs}),
               results=results)
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave16b'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'signals: wave fourteen\'s first L2 signal at each level; MARKET '
             'enters at the signal mid; LIM2 / LIM4 rest 2 / 4 ticks better '
             'for 60 s, fill only when price trades a tick through; missed = '
             '0; 25 / 15 / 30 min; net after costs']
    for inst, res in sorted(rep['results'].items(),
                            key=lambda kv: kv[0] != PRIMARY):
        lines.append('')
        lines.append('%s  LIMIT ENTRY%s   signals %d' % (
            inst, ' (tested)' if inst == PRIMARY else '',
            res['market']['n']))
        if rep['withheld']:
            lines.append('   %s' % res['tests'][0]['status'])
            continue
        lines.append('   MARKET   net %s a signal' % _pts(
            res['market'].get('net_points')))
        for x in res['tests']:
            ci = x.get('ci95')
            lines.append(
                '   %-6s   net %s a signal; filled %s, missed winners %d, '
                'on filled %s' % (
                    x['test'], _pts(x['net_points']),
                    '-' if x['fill_rate'] is None else
                    '%.0f%%' % (100 * x['fill_rate']), x['missed_winners'],
                    _pts(x['filled_net_points'])))
            lines.append('            vs MARKET %s a signal, 95%% range %s, '
                         'p %s -> %s%s' % (
                             _pts(x['improvement']),
                             '-' if not ci else '%s .. %s' % (
                                 _pts(ci[0]), _pts(ci[1])),
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
    if unblind or holdout:
        print('*** %s: this read is part 16B\'s registered test. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(argv[0], unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\npart-16B report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W16B_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W16B_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
