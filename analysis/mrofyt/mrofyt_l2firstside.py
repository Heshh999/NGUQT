#!/usr/bin/env python3
"""mrofyt_l2firstside.py - MROF-YT-W19-L2FIRSTSIDE-1.0

MROF_YT_WAVE19_L2FIRSTSIDE_REGISTRATION.md turned into running code: wave
six's L2 trades, the first L2 signal from EACH SIDE of each level per
CME session (at most one short and one long per level), at any hour, one
position at a time; target 25 points, stop 15, 30 minutes, net of costs.
Judged by wave fourteen's verdict, beside it; wave fourteen stays the
headline.

    python3 mrofyt_l2firstside.py "<capture>" --out w19.json             # DEV: describes
    python3 mrofyt_l2firstside.py "<capture>" --unblind --out w19_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import json
import os
import sys

import mrofyt_l2firstsignal as FS
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_runner as RUN

W19_VERSION = 'MROF-YT-W19-L2FIRSTSIDE-1.0'
REGISTRATION = 'MROF_YT_WAVE19_L2FIRSTSIDE_REGISTRATION.md'
DEV_END = FS.DEV_END
HOLDOUT_BEFORE = FS.HOLDOUT_BEFORE
HOLDOUT_LEDGER = FS.HOLDOUT_LEDGER
EXPOSURE_LEDGER = FS.EXPOSURE_LEDGER
PRIMARY = FS.PRIMARY
TEST_NAME = 'FIRST SIGNAL FROM EACH SIDE'


class FirstSideRunner(FS.FirstSignalRunner):
    """Wave fourteen's runner, unchanged; the ledger names wave
    nineteen."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        FS.FirstSignalRunner.__init__(self, capture_dir, unblind=unblind,
                                      holdout=holdout, **kw)
        self.ledger['wave19'] = dict(version=W19_VERSION)


def first_per_side(events):
    """The events that are the first L2 signal in their direction at
    every one of their levels in their instrument's session, in time
    order. Every event uses up all its levels for its own direction,
    taken or not; an event with no level is never taken."""
    used = set()
    out = []
    for e in sorted(events, key=lambda e: (e['instrument'], e['session'],
                                           e['t'])):
        ks = {(e['instrument'], e['session'], lv, e['direction'])
              for lv in (e.get('levels') or ()) if lv is not None}
        if ks and not (ks & used):
            out.append(e)
        used |= ks
    return out


def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = FirstSideRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    ev = [e for e in V.variant_events(r) if keep(e['session'])]
    side_ids = {id(e) for e in first_per_side(ev)}
    level_ids = {id(e) for e in FS.first_signals(ev)}
    sc = V.score_variants(r, ev).get('V0', [])
    insts = sorted({e['instrument'] for e in ev} | {PRIMARY})
    results = {}
    for inst in insts:
        mine = lambda ids: V.one_at_a_time(     # noqa: E731
            [x for x in sc if x[0]['instrument'] == inst and id(x[0]) in ids])
        test_rows = mine(side_ids)
        res = dict(test=FS.verdict(test_rows, inst))
        res['test'].update(name=TEST_NAME, first_per_side=sum(
            1 for e in ev if id(e) in side_ids and e['instrument'] == inst))
        level_rows = mine(level_ids)
        taken = {id(x[0]) for x in level_rows}
        for key, name, rows in (
                ('per_level', 'per level (wave 14)', level_rows),
                ('extra', 'only this rule takes',
                 [x for x in test_rows if id(x[0]) not in taken])):
            b = LB.test_stats(rows, inst)
            res[key] = dict(name=name, n=b['n'], hit=b.get('hit'),
                            net_points=b.get('net_points'))
        results[inst] = res
    withheld = bool((unblind or holdout) and
                    results[PRIMARY]['test']['n'] < FS.MIN_TRADES)
    if withheld:
        for inst, res in results.items():
            results[inst] = dict(test=FS._withhold(res['test']))
            results[inst]['test']['status'] = (
                'NOT ENOUGH TRADES: results withheld until a read holds %d'
                % FS.MIN_TRADES if inst == PRIMARY else 'withheld')
    elif not (unblind or holdout):
        for res in results.values():
            res['test']['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave19=W19_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, min_trades=FS.MIN_TRADES,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in ev}),
               results=results)
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave19'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'rule: the first L2 signal from each side of each level per '
             'session (one short, one long at most), any hour; target 25 '
             'pts, stop 15 pts, 30 min; one trade at a time; net after costs']
    for inst, res in sorted(rep['results'].items(),
                            key=lambda kv: kv[0] != PRIMARY):
        x = res['test']
        lines.append('')
        lines.append('%s  %s%s' % (inst, TEST_NAME,
                                   ' (tested)' if inst == PRIMARY else ''))
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
            lines.append('   95%% range of net a trade: %s   p %s' % (
                '-' if not ci else '%s .. %s points' % (
                    _pts(ci[0] / 4.0), _pts(ci[1] / 4.0)),
                '-' if x.get('p') is None else '%.4f' % x['p']))
            wb = x['without_best_day']
            lines.append('   without the best day (%s): %d trades, net %s a '
                         'trade' % (wb['session'], wb['n'],
                                    _pts(wb['net_points'])))
        lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
            x['reasons'])) if x.get('reasons') else ''))
        for key in ('per_level', 'extra'):
            b = res[key]
            lines.append('   beside, not tested: %-21s %3d trades, %s, net %s '
                         'a trade' % (b['name'], b['n'],
                                      '-' if not b['n'] else
                                      'won %.0f%%' % (100 * b['hit']),
                                      _pts(b['net_points'])))
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
        print('*** %s: this read is wave nineteen\'s registered test. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(argv[0], unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-nineteen report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W19_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W19_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
