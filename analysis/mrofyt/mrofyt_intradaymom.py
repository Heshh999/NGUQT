#!/usr/bin/env python3
"""mrofyt_intradaymom.py - MROF-YT-W16C-INTRADAYMOM-1.0

MROF_YT_WAVE16_REGISTRATION.md, part 16C, turned into running code:
intraday momentum (Gao, Han, Li and Zhou, Journal of Financial
Economics, 2018) on NQ one-minute bars.

    signal  r = the 10:00 ET price (close of the 09:59 bar) minus the
            previous session's cash close (its 15:59 bar), same contract
    trade   long when r > 0, short when r < 0: in at the close of the
            15:29 bar, out at the close of the 15:59 bar; no stop, no
            target; net of mrofyt_costs' round trip
    test    mean net points a day above 0, month-clustered, its 95 %
            interval above 0 and still above 0 without the best month;
            at least 250 days

Described on 2019-06-01 .. 2026-06-30; judged once on the sessions
before 2019-06-01 (--unblind). Exports as for mrofyt_context.py.

    python3 mrofyt_intradaymom.py "<NQ minute exports>" --out m16c.json
    python3 mrofyt_intradaymom.py "<NQ minute exports>" --unblind --out m16c_val.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import collections
import json
import os
import sys

import mrofyt_context as CX
import mrofyt_costs as CO
import mrofyt_ledgers as LG
import mrofyt_minutelevels as ML

W16C_VERSION = 'MROF-YT-W16C-INTRADAYMOM-1.0'
REGISTRATION = 'MROF_YT_WAVE16_REGISTRATION.md'
HISTORY_LEDGER = ML.HISTORY_LEDGER
SIGNAL_BAR = 9 * 3600 + 59 * 60          # bar START times, ET
ENTRY_BAR = 15 * 3600 + 29 * 60
EXIT_BAR = 15 * 3600 + 59 * 60
MARKS = (SIGNAL_BAR, ENTRY_BAR, EXIT_BAR)
MIN_DAYS = 250


class MomDayAgg(CX.DayAgg):
    __slots__ = ('marks',)

    def __init__(self):
        CX.DayAgg.__init__(self)
        self.marks = {}

    def add(self, sod, o, h, lo, c, v):
        CX.DayAgg.add(self, sod, o, h, lo, c, v)
        if sod in MARKS:
            self.marks[sod] = c

    def finalize(self):
        out = CX.DayAgg.finalize(self)
        out['marks'] = dict(self.marks)
        return out


class MomReader(CX.Reader):
    agg_class = MomDayAgg


def cost_points(inst='NQ'):
    return CO.cost_ticks(inst, 'TIMEOUT') / 4.0


def momentum_days(path, allow, stamps_tz='UTC', stamps='end'):
    """[day dict]: the context study's eligible sessions with yesterday
    complete on the same contract and the three bars present."""
    rd = MomReader('NQ', stamps_tz, stamps, allow)
    rd.read_path(path)
    if not rd.days:
        raise CX.ContextDataError(CX._nothing_read(
            rd, 'NQ', 'in the years this mode reads'))
    chk = rd.check_stamps()
    recs = CX.build_days(rd.days)
    every = sorted({s for _c, s in rd.days})
    before = dict(zip(every[1:], every[:-1]))
    out = []
    for r in recs:
        s, c = r['session'], r['contract']
        prev = before.get(s)
        y = rd.days.get((c, prev)) if prev else None
        if not r['eligible'] or y is None or not y['complete']:
            continue
        mk = rd.days[(c, s)]['marks']
        if any(k not in mk for k in MARKS):
            continue
        ret = mk[SIGNAL_BAR] - y['rth_close']
        if ret == 0:
            continue
        d = 1 if ret > 0 else -1
        gross = d * (mk[EXIT_BAR] - mk[ENTRY_BAR])
        out.append(dict(session=s, month=s[:6], year=s[:4], direction=d,
                        r=round(ret, 2), gross=round(gross, 2),
                        net=round(gross - cost_points(), 4)))
    return out, rd, chk


def run(path, unblind=False, stamps_tz='UTC', stamps='end'):
    allow = CX.is_validation if unblind else CX.is_dev
    days, rd, chk = momentum_days(path, allow, stamps_tz, stamps)
    test = ML.month_verdict([(x['month'], x['net']) for x in days],
                            MIN_DAYS)
    if not unblind:
        test['status'] += ' (DEV years: describes)'
    by_year = collections.defaultdict(list)
    for x in days:
        by_year[x['year']].append(x['net'])
    sides = {}
    for d, name in ((1, 'long'), (-1, 'short')):
        v = [x['net'] for x in days if x['direction'] == d]
        sides[name] = dict(n=len(v), net_points=round(sum(v) / len(v), 3)
                           if v else None)
    ses = [x['session'] for x in days]
    return dict(wave16c=W16C_VERSION, registration=REGISTRATION,
                mode='validation' if unblind else 'dev',
                years=('before %s' % CX.VALIDATION_BEFORE) if unblind else
                ('%s to %s' % (CX.VALIDATION_BEFORE, CX.REFUSE_FROM)),
                stamp_check=chk, first_session=min(ses) if ses else None,
                last_session=max(ses) if ses else None,
                sessions_skipped_unread=len(rd.skipped_sessions),
                cost_points=cost_points(), n_trades=test['n'], test=test,
                sides=sides,
                by_year={y: dict(n=len(v), net_points=round(sum(v) / len(v),
                                                            3))
                         for y, v in sorted(by_year.items())})


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    x = rep['test']
    lines = ['%s  %s (%s)' % (rep['wave16c'], rep['mode'], rep['years']),
             'days %d (%s .. %s); stamp check %s; cost %.2f points a day' % (
                 x['n'], rep['first_session'], rep['last_session'],
                 rep['stamp_check'].get('open_minute'), rep['cost_points']),
             'rule: the move from yesterday\'s 16:00 close to 10:00 sets the '
             'side; in at 15:30, out at 16:00',
             '']
    if x['n']:
        ci = x.get('ci95')
        lines.append('TEST  won %.0f%% of days, net %s a day, total %s points'
                     % (100 * x['won'], _pts(x['net_points']),
                        _pts(x['total_points'])))
        lines.append('   95%% range of net a day: %s   p %s' % (
            '-' if not ci else '%s .. %s' % (_pts(ci[0]), _pts(ci[1])),
            '-' if x.get('p') is None else '%.4f' % x['p']))
        wb = x['without_best']
        lines.append('   without the best month (%s): net %s a day' % (
            wb['cluster'], _pts(wb['net_points'])))
    lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
        x['reasons'])) if x.get('reasons') else ''))
    for name, v in rep['sides'].items():
        lines.append('   %-5s %5d days, net %s a day' % (
            name, v['n'], _pts(v['net_points'])))
    for y, v in rep['by_year'].items():
        lines.append('   %s  %4d days  net %s a day' % (
            y, v['n'], _pts(v['net_points'])))
    lines.append('')
    lines.append('Minute-bar closes, costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    unblind = '--unblind' in argv
    if unblind:
        print('*** UNBLIND: part 16C on the sessions before %s, once. ***\n'
              % CX.VALIDATION_BEFORE)
    try:
        rep = run(argv[0], unblind, stz, stp)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    out = arg('--out')
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\npart-16C report -> %s' % out)
    if unblind:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         HISTORY_LEDGER)
        print('history read recorded (%d read(s))'
              % LG.record_history_read(rep, p, W16C_VERSION))
    return 0


if __name__ == '__main__':
    sys.exit(main())
