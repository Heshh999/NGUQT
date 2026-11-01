#!/usr/bin/env python3
"""mrofyt_l2firstsignal.py - MROF-YT-W14-L2FIRSTSIGNAL-1.0

MROF_YT_WAVE14_L2FIRSTSIGNAL_REGISTRATION.md turned into running code:
wave six's L2 trades, only the first L2 signal at each level per CME
session, at any hour, one position at a time; target 25 points, stop 15
points, 30 minutes, net of costs. The one test the unseen days decide
(NQ):

    PASS         30+ trades, mean net > 0 with its 95 % interval above 0
                 (session-clustered), and still > 0 without the best day
    NOT PROVEN   anything else, with the reason
    fewer than 30 trades on a held-out read: the count only; every
    result is withheld until a read holds 30

    python3 mrofyt_l2firstsignal.py "<capture>" --out w14.json            # DEV: describes
    python3 mrofyt_l2firstsignal.py "<capture>" --unblind --out w14_eval.json  # THE TEST
    python3 mrofyt_l2firstsignal.py "<replay folder>" --holdout --out w14_replay.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import collections
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_pilot as PI
import mrofyt_runner as RUN

W14_VERSION = 'MROF-YT-W14-L2FIRSTSIGNAL-1.0'
REGISTRATION = 'MROF_YT_WAVE14_L2FIRSTSIGNAL_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
MIN_TRADES = 30
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT
TEST_NAME = 'FIRST SIGNAL AT A LEVEL'
BESIDE = (('EVERY', 'every L2', 'V0'), ('TOUCH', 'strict first touch', 'V1'))


class FirstSignalRunner(V.L2VariantRunner):
    """Wave eight's runner, unchanged; the ledger names wave fourteen."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        V.L2VariantRunner.__init__(self, capture_dir, unblind=unblind,
                                   holdout=holdout, **kw)
        self.ledger['wave14'] = dict(version=W14_VERSION)


# ---------------------------------------------------------------------
# registration 2: the first signal at a level
# ---------------------------------------------------------------------
def first_signals(events):
    """The events that are the first L2 signal at every one of their
    levels in their instrument's session, in time order. Every event uses
    up all its levels, taken or not; an event with no level is never
    taken."""
    used = set()
    out = []
    for e in sorted(events, key=lambda e: (e['instrument'], e['session'],
                                           e['t'])):
        ks = {(e['instrument'], e['session'], lv)
              for lv in (e.get('levels') or ()) if lv is not None}
        if ks and not (ks & used):
            out.append(e)
        used |= ks
    return out


# ---------------------------------------------------------------------
# registration 4: the verdict
# ---------------------------------------------------------------------
def verdict(rows, inst):
    """rows: one instrument's trades, one at a time. The test's numbers
    and, on NQ with 30 or more trades, PASS or NOT PROVEN with reasons."""
    st = LB.test_stats(rows, inst)
    st['trades'] = st['n']
    if st['n']:
        st['total_net_points'] = round(sum(st['by_session'].values()), 2)
        by_day = collections.defaultdict(lambda: [0, 0, 0.0])
        for e, oc, g, _r, _s in rows:
            d = by_day[e['session']]
            d[0] += 1
            d[1] += oc == 'TARGET'
        for s, v in st['by_session'].items():
            by_day[s][2] = v
        st['by_day'] = [dict(session=s, trades=v[0], wins=v[1],
                             net_points=v[2]) for s, v in sorted(by_day.items())]
        best = max(st['by_session'], key=lambda s: (st['by_session'][s], s))
        rest = LB.test_stats([x for x in rows if x[0]['session'] != best],
                             inst)
        st['without_best_day'] = dict(session=best, n=rest['n'],
                                      net_points=rest.get('net_points'))
    if inst != PRIMARY:
        st['status'], st['reasons'] = 'DESCRIBED (not tested)', []
        return st
    if st['n'] < MIN_TRADES:
        st['status'], st['reasons'] = 'NOT ENOUGH TRADES', [
            '%d of the %d trades needed' % (st['n'], MIN_TRADES)]
        return st
    reasons = []
    ci = st.get('ci95_net_ticks')
    if st['net_points'] <= 0:
        reasons.append('loses after costs')
    elif not ci or ci[0] <= 0:
        reasons.append('could be luck: the 95 % range reaches zero')
    wb = st['without_best_day']
    if not wb['n'] or wb['net_points'] is None or wb['net_points'] <= 0:
        reasons.append('rests on one day: without %s it does not make '
                       'money' % wb['session'])
    st['status'] = 'NOT PROVEN' if reasons else 'PASS'
    st['reasons'] = reasons
    return st


_KEEP_WITHHELD = ('n', 'sessions', 'trades', 'status', 'reasons')


def _withhold(st):
    return dict((k, st[k]) for k in _KEEP_WITHHELD if k in st)


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = FirstSignalRunner(capture_dir, unblind=unblind, holdout=holdout,
                          max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s): THE TEST' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s): describes, not a test' % DEV_END
    ev = [e for e in V.variant_events(r) if keep(e['session'])]
    firsts = first_signals(ev)
    first_ids = {id(e) for e in firsts}
    sc = V.score_variants(r, ev)
    rows = dict(TEST=[x for x in sc.get('V0', []) if id(x[0]) in first_ids])
    for key, _name, vid in BESIDE:
        rows[key] = sc.get(vid, [])
    insts = sorted({e['instrument'] for e in ev} | {PRIMARY})
    results = {}
    for inst in insts:
        mine = lambda k: V.one_at_a_time(       # noqa: E731
            [x for x in rows[k] if x[0]['instrument'] == inst])
        res = dict(test=verdict(mine('TEST'), inst))
        res['test'].update(name=TEST_NAME,
                           first_signals=sum(1 for e in firsts
                                             if e['instrument'] == inst))
        for key, name, _vid in BESIDE:
            b = LB.test_stats(mine(key), inst)
            res[key.lower()] = dict(name=name, n=b['n'],
                                    sessions=b.get('sessions', 0),
                                    hit=b.get('hit'),
                                    net_points=b.get('net_points'))
        results[inst] = res
    primary_n = results[PRIMARY]['test']['n']
    withheld = bool((unblind or holdout) and primary_n < MIN_TRADES)
    if withheld:
        for inst, res in results.items():
            results[inst] = dict(test=_withhold(res['test']))
            results[inst]['test']['status'] = (
                'NOT ENOUGH TRADES: results withheld until a read holds %d'
                % MIN_TRADES if inst == PRIMARY else 'withheld')
    elif not (unblind or holdout):
        for res in results.values():
            res['test']['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave14=W14_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, min_trades=MIN_TRADES,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in ev}),
               results=results)
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave14'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'rule: the first L2 signal at each level per session, any hour; '
             'target 25 pts, stop 15 pts, 30 min; one trade at a time; net = '
             'after commission, a tick of spread and a tick of slip on stops']
    for inst, res in sorted(rep['results'].items(),
                            key=lambda kv: kv[0] != PRIMARY):
        x = res['test']
        lines.append('')
        lines.append('%s  %s%s' % (inst, TEST_NAME,
                                   ' (the test)' if inst == PRIMARY else ''))
        lines.append('   trades %d over %d days' % (x['n'],
                                                     x.get('sessions', 0)))
        if rep['withheld']:
            lines.append('   %s' % x['status'])
            continue
        if x['n']:
            ci = x.get('ci95_net_ticks')
            lines.append('   won %.0f%%, net %s a trade, total %s points' % (
                100 * x['hit'], _pts(x['net_points']),
                _pts(x.get('total_net_points'))))
            lines.append('   95%% range of net a trade: %s' % (
                '-' if not ci else '%s .. %s points' % (
                    _pts(ci[0] / 4.0), _pts(ci[1] / 4.0))) +
                '   t %s  p %s' % (
                '-' if x.get('t') is None else '%.2f' % x['t'],
                '-' if x.get('p') is None else '%.4f' % x['p']))
            wb = x['without_best_day']
            lines.append('   without the best day (%s): %d trades, net %s a '
                         'trade' % (wb['session'], wb['n'],
                                    _pts(wb['net_points'])))
        lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
            x['reasons'])) if x.get('reasons') else ''))
        if x['n']:
            lines.append('   %-10s %6s %5s %10s' % ('day', 'trades', 'wins',
                                                 'net pts'))
            for d in x['by_day']:
                lines.append('   %-10s %6d %5d %10s' % (
                    d['session'], d['trades'], d['wins'],
                    _pts(d['net_points'])))
        for key, _name, _vid in BESIDE:
            b = res[key.lower()]
            lines.append('   beside, not tested: %-18s %3d trades, %s, net %s '
                         'a trade' % (b['name'], b['n'],
                                      '-' if not b['n'] else
                                      'won %.0f%%' % (100 * b['hit']),
                                      _pts(b['net_points'])))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def record_holdout_read(rep, path):
    return LG.record_holdout_read(rep, path, W14_VERSION)


def record_exposure(rep, path):
    return LG.record_exposure(rep, path, W14_VERSION)


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
        print('*** %s: this read is the registered test of the first L2 '
              'signal at a level. ***\n' % ('UNBLIND' if unblind
                                           else 'HOLDOUT'))
    try:
        rep, _r = run(d, unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-fourteen report -> %s' % out)
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
