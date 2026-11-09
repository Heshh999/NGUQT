#!/usr/bin/env python3
"""mrofyt_psycheck.py - MROF-YT-PSYCHECK-1.0

The weekly Psy-Hi / Psy-Lo of the Traders Reality indicator (TR_MAIN,
"Psy calc type: forex"), rebuilt from the recordings' NQ trades, so the
level can be matched to the operator's own chart before any test uses it.

The indicator's forex calculation (Traders_Reality_Lib, calcPsyLevels):

    psySession := time('240', '0000-0800:2', "GMT")
    psyHi := math.max(high, psyHi[1]);  psyLo := math.min(low, psyLo[1])

i.e. the highest high and lowest low while "in" Monday 00:00-08:00 GMT,
fixed for the rest of the week. Whether TradingView applies that session
to the chart's own candles or to the 4-hour candles named in the call is
what this check settles, so it prints three candidate windows per week:

    TR_CLOCK  Monday 00:00-08:00 GMT on the chart's candles:
              7 PM-3 AM New York in winter, 8 PM-4 AM in summer
    TR_4H     the CME 4-hour candles (opening 18:00, 22:00, 02:00 ...
              New York) whose open falls in Monday 00:00-08:00 GMT:
              10 PM-6 AM New York all year
    FIRST_8H  the first 8 hours after the Sunday 6 PM New York open (the
              project's own NQ adaptation, MROF_YT_OF01_1 PSY-NQ-01)

    python3 mrofyt_psycheck.py "<capture>" --expect 20261102:28834.50:28666.25

--expect WEEK:HI:LO (repeatable) is the chart's Psy-Hi / Psy-Lo for the
week whose Monday is WEEK; each window's difference is shown, and the
window that gives every expected week exactly is named.

What it reads: the NQ trades (exchange time and price) of Monday
sessions only, and only sessions on or before the DEV end or already
marked EXPOSED in the exposure ledger; a held-out session is listed and
never opened. Trades the recorder flagged DATA_SUPPRESSED or
DISCONNECTED are left out and counted. It computes no outcome, records
nothing in any ledger and places no order.
"""

import csv
import datetime as _dt
import json
import os
import sys

import mles_v12_adapter as AD
import mles_v12_audit as AU
import mrofyt_pilot as PI
import mrofyt_runner as RUN

PSYCHECK_VERSION = 'MROF-YT-PSYCHECK-1.0'
DEV_END = '20260918'
HOLDOUT_BEFORE = '20260901'
HERE = os.path.dirname(os.path.abspath(__file__))
EXPOSURE_LEDGER = os.path.join(HERE, 'MROF_EXPOSED_PILOT_DEV_DAYS.json')
WINDOWS = ('TR_CLOCK', 'TR_4H', 'FIRST_8H')
SUPPRESSED = ('DATA_SUPPRESSED', 'DISCONNECTED')
EDGE_S = 120.0           # first / last trade within 2 min of the edges
GAP_S = 600.0            # no 10-minute hole inside the window
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def _midnight_utc(yyyymmdd):
    d = _dt.date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:]))
    return (_dt.datetime(d.year, d.month, d.day, tzinfo=_dt.timezone.utc)
            - _EPOCH).total_seconds()


def windows(week):
    """{name: (start, end)} epochs for the week whose Monday (GMT and
    CME session date) is week (YYYYMMDD)."""
    mon0 = _midnight_utc(week)
    sun0 = mon0 - 86400.0
    off = RUN.et_offset(sun0 + 22 * 3600)        # Sunday evening, New York
    open_ = sun0 + 18 * 3600 - off               # Sunday 18:00 New York
    bars = [open_ + 4 * 3600 * k for k in range(6)
            if mon0 <= open_ + 4 * 3600 * k < mon0 + 8 * 3600]
    return dict(TR_CLOCK=(mon0, mon0 + 8 * 3600),
                TR_4H=(bars[0], bars[-1] + 4 * 3600),
                FIRST_8H=(open_, open_ + 8 * 3600))


def ny_clock(epoch):
    loc = _dt.datetime.fromtimestamp(epoch + RUN.et_offset(epoch),
                                     _dt.timezone.utc)
    return loc.strftime('%a %H:%M')


def exposed_sessions(path):
    try:
        with open(path) as fh:
            days = json.load(fh).get('exposed_days', [])
    except (OSError, ValueError):
        return set()
    return {d.get('session') for d in days
            if d.get('label') == PI.EXPOSURE_LABEL}


def allowed(session, exposed):
    if session < HOLDOUT_BEFORE:
        return False
    return session <= DEV_END or session in exposed


def is_monday(session):
    try:
        return _dt.date(int(session[:4]), int(session[4:6]),
                        int(session[6:])).weekday() == 0
    except ValueError:
        return False


def monday_runs(capture_dir, instrument='NQ'):
    """{session: [(first recv epoch, trades path, contract, run id)]} of
    every recorded run of the instrument in a Monday session; a run
    carrying two manifests is listed once."""
    out, seen = {}, set()
    for mp in AU.discover_manifests(capture_dir):
        try:
            with open(mp) as fh:
                man = json.load(fh)
        except (OSError, ValueError):
            continue
        if man.get('instrument') != instrument:
            continue
        ses, rid = str(man.get('session') or ''), man.get('runId')
        tr = man.get('trades') or {}
        if not (is_monday(ses) and tr.get('file')) or rid in seen:
            continue
        seen.add(rid)
        first = AD.iso_to_epoch(str(man.get('firstRecvUtc') or '')) or 0.0
        out.setdefault(ses, []).append(
            (first, os.path.join(os.path.dirname(mp), tr['file']),
             man.get('contract'), rid))
    for v in out.values():
        v.sort()
    return out


def week_levels(runs, week):
    """{window: dict(hi, lo, n, first, last, max_gap, status, why)} from
    the trades of one Monday session's runs."""
    win = windows(week)
    lo_t = min(a for a, _b in win.values())
    hi_t = max(b for _a, b in win.values())
    acc = {k: dict(hi=None, lo=None, n=0, first=None, last=None,
                   max_gap=0.0) for k in WINDOWS}
    suppressed = 0
    for _first, path, _contract, _rid in runs:
        with open(path, newline='') as fh:
            rdr = csv.reader(fh)
            head = next(rdr, None)
            if head is None:
                continue
            AD.check_header('trades', head)
            i_ex, i_rv = head.index('tExchUtc'), head.index('tRecvUtc')
            i_px, i_fl = head.index('px'), head.index('flags')
            for row in rdr:
                if len(row) != len(head):
                    continue
                t = AD.iso_to_epoch(row[i_ex].strip()) or \
                    AD.iso_to_epoch(row[i_rv].strip())
                if t is None or not lo_t <= t < hi_t:
                    continue
                if any(f in row[i_fl] for f in SUPPRESSED):
                    suppressed += 1
                    continue
                px = float(row[i_px])
                for k, (a, b) in win.items():
                    if not a <= t < b:
                        continue
                    w = acc[k]
                    if w['n']:
                        w['max_gap'] = max(w['max_gap'], t - w['last'])
                    w['n'] += 1
                    w['first'] = t if w['first'] is None else min(w['first'],
                                                                  t)
                    w['last'] = t if w['last'] is None else max(w['last'], t)
                    w['hi'] = px if w['hi'] is None else max(w['hi'], px)
                    w['lo'] = px if w['lo'] is None else min(w['lo'], px)
    for k, (a, b) in win.items():
        w = acc[k]
        why = []
        if not w['n']:
            why.append('no trades recorded in the window')
        else:
            if w['first'] - a > EDGE_S:
                why.append('first trade %.0f min after the window opens'
                           % ((w['first'] - a) / 60))
            if b - w['last'] > EDGE_S:
                why.append('last trade %.0f min before the window closes'
                           % ((b - w['last']) / 60))
            if w['max_gap'] > GAP_S:
                why.append('a %.0f-minute hole in the trades'
                           % (w['max_gap'] / 60))
        w.update(start=a, end=b, window_ny='%s - %s New York' % (
            ny_clock(a), ny_clock(b)), status='INCOMPLETE' if why else
            'COMPLETE', why=why)
    return acc, suppressed


def run(capture_dir, expect=None, instrument='NQ', ledger=EXPOSURE_LEDGER):
    exposed = exposed_sessions(ledger)
    expect = dict(expect or {})
    weeks, held = [], []
    runs = monday_runs(capture_dir, instrument)
    for ses in sorted(set(runs) | set(expect)):
        if ses not in runs:
            weeks.append(dict(week=ses, recorded=False))
            continue
        if not allowed(ses, exposed):
            held.append(ses)
            continue
        lv, sup = week_levels(runs[ses], ses)
        rec = dict(week=ses, recorded=True,
                   contracts=sorted({c for _f, _p, c, _r in runs[ses]}),
                   suppressed_trades=sup, windows=lv)
        if ses in expect:
            ehi, elo = expect[ses]
            rec['expected'] = dict(hi=ehi, lo=elo)
            for w in lv.values():
                if w['n']:
                    w['d_hi'] = round(w['hi'] - ehi, 2)
                    w['d_lo'] = round(w['lo'] - elo, 2)
                    w['exact'] = w['d_hi'] == 0 and w['d_lo'] == 0
        weeks.append(rec)
    checked = [w for w in weeks if w.get('expected') and w.get('recorded')]
    verdict = None
    if checked:
        exact = {k: sum(1 for w in checked if w['windows'][k].get('exact'))
                 for k in WINDOWS}
        full = [k for k in WINDOWS if exact[k] == len(checked)]
        verdict = dict(weeks_checked=len(checked), exact=exact,
                       matching_window=full[0] if len(full) == 1 else None,
                       ambiguous=len(full) > 1)
    return dict(psycheck=PSYCHECK_VERSION, instrument=instrument,
                weeks=weeks, held_out_not_read=held, verdict=verdict)


def _p(x):
    return '-' if x is None else '{:,.2f}'.format(x)


def text(rep):
    lines = ['%s  %s weekly Psy-Hi / Psy-Lo from the recordings (Traders '
             'Reality forex calc), three candidate windows'
             % (rep['psycheck'], rep['instrument'])]
    for w in rep['weeks']:
        lines.append('')
        if not w.get('recorded'):
            lines.append('week of Monday %s: not in the recordings'
                         % w['week'])
            continue
        lines.append('week of Monday %s (contract %s%s)' % (
            w['week'], ', '.join(c or '?' for c in w['contracts']),
            '; %d flagged trades left out' % w['suppressed_trades']
            if w['suppressed_trades'] else ''))
        if w.get('expected'):
            lines.append('  your chart: Psy-Hi %s  Psy-Lo %s' % (
                _p(w['expected']['hi']), _p(w['expected']['lo'])))
        for k in WINDOWS:
            x = w['windows'][k]
            cmp_ = ''
            if 'exact' in x:
                cmp_ = '  vs chart: Hi %+.2f Lo %+.2f%s' % (
                    x['d_hi'], x['d_lo'], '  EXACT' if x['exact'] else '')
            lines.append('  %-8s %-28s Psy-Hi %10s  Psy-Lo %10s  %6d '
                         'trades  %s%s' % (k, x['window_ny'], _p(x['hi']),
                                           _p(x['lo']), x['n'], x['status'],
                                           cmp_))
            if x['why']:
                lines.append('           %s' % '; '.join(x['why']))
    if rep['held_out_not_read']:
        lines.append('')
        lines.append('held out, not read: %s (read once the registered '
                     'test has used them)' % ', '.join(rep['held_out_not_read']))
    v = rep['verdict']
    if v:
        lines.append('')
        if v['matching_window']:
            lines.append('MATCH: %s gives your chart\'s Psy-Hi and Psy-Lo '
                         'exactly in all %d week(s) checked.'
                         % (v['matching_window'], v['weeks_checked']))
        elif v['ambiguous']:
            lines.append('AMBIGUOUS: more than one window matches every '
                         'week checked; add another week.')
        else:
            lines.append('NO WINDOW MATCHES EXACTLY: exact weeks %s of %d. '
                         'Check the chart numbers and the contract.' % (
                             ', '.join('%s %d' % kv for kv in
                                       v['exact'].items()),
                             v['weeks_checked']))
    lines.append('')
    lines.append('Reads trades only; no outcome is computed and no order is '
                 'placed.')
    return '\n'.join(lines)


def _expect(args):
    out = {}
    for a in args:
        parts = a.split(':')
        if len(parts) != 3 or len(parts[0]) != 8 or not parts[0].isdigit():
            raise ValueError('--expect takes WEEK:HI:LO, e.g. '
                             '20261102:28834.50:28666.25 (got %r)' % a)
        out[parts[0]] = (float(parts[1].replace(',', '')),
                         float(parts[2].replace(',', '')))
    return out


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2
    exp, out, i = [], None, 1
    while i < len(argv):
        if argv[i] == '--expect' and i + 1 < len(argv):
            exp.append(argv[i + 1])
            i += 2
        elif argv[i] == '--out' and i + 1 < len(argv):
            out = argv[i + 1]
            i += 2
        else:
            print('STOPPED: unknown argument %r' % argv[i])
            return 2
    try:
        rep = run(argv[0], _expect(exp))
    except ValueError as exc:
        print('STOPPED: %s' % exc)
        return 2
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        print('\npsy check -> %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
