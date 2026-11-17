#!/usr/bin/env python3
"""mrofyt_vwapvalue.py - MROF-YT-W23-VWAPVALUE-1.0

MROF_YT_WAVE23_VWAPVALUE_REGISTRATION.md turned into running code: three
rules read from where the order flow put the direction, tested on years
of NQ one-minute bars.

    RUBBER    far from VWAP (|close - VWAP| >= 0.15 x A) and the last 30
              minutes moving back toward it (0.08 x A or more): trade
              toward VWAP; target 25, stop 15
    MOMENTUM  moderately away from VWAP (0.03 to 0.13 x A) and the last
              30 minutes moving further away (0.03 x A or more): trade
              away from VWAP; target 25, stop 15
    ACCEPT    a failed break of the overnight POC, VAH or VAL after 09:30:
              trade WITH the break; target 15, stop 25

    A = the mean session range of the last 14 sessions. 30 minutes at
    most; one trade at a time within each rule; net of costs. Each rule:
    month-clustered, 100+ trades, Holm over the three; two eras, a rule
    confirmed only if it passes in both.

    python3 mrofyt_vwapvalue.py "<NQ minute exports>" --out w23_new.json            # 2019-06 .. 2026-06
    python3 mrofyt_vwapvalue.py "<NQ minute exports>" --unblind --out w23_old.json  # before 2019-06-01

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_context as CX
import mrofyt_ledgers as LG
import mrofyt_minutelevels as ML
import mrofyt_stretchfade as SF

W23_VERSION = 'MROF-YT-W23-VWAPVALUE-1.0'
REGISTRATION = 'MROF_YT_WAVE23_VWAPVALUE_REGISTRATION.md'
HISTORY_LEDGER = ML.HISTORY_LEDGER

RTH_OPEN = float(CX.RTH_OPEN)             # 09:30 ET, as a bar key
ZONE_TO = 15.5 * 3600                     # RUBBER, MOMENTUM: before 15:30
ACCEPT_TO = 17.0 * 3600                   # ACCEPT: before 17:00
ON_FIRST_BY = 18.5 * 3600 - 86400         # an overnight bar by 18:30 ET
ON_LAST_FROM = 9.0 * 3600                 # and one from 09:00 ET
TREND_S, TREND_LATE_S = 1800.0, 2100.0    # 30 minutes, at most 35 back
RUB_FAR, RUB_TREND = 0.15, 0.08
MOM_NEAR, MOM_FAR, MOM_TREND = 0.03, 0.13, 0.03
HOLD_S = float(ML.HOLD_S)                 # 1 800 s
TICK = 0.25
RULES = ('RUBBER', 'MOMENTUM', 'ACCEPT')
BRACKET = dict(RUBBER=(25.0, 15.0), MOMENTUM=(25.0, 15.0),
               ACCEPT=(15.0, 25.0))      # (target, stop) in points
ON_IDS = ('ON_POC', 'ON_VAH', 'ON_VAL')
NAMES = collections.OrderedDict([
    ('RUBBER', 'RUBBER: far from VWAP, turning back: toward VWAP'),
    ('MOMENTUM', 'MOMENTUM: moderately away from VWAP and moving away: '
                 'with it'),
    ('ACCEPT', 'ACCEPT: a failed break of the overnight value area: with '
               'the break')])
MIN_TRADES = ML.MIN_HISTORY               # 100
HOLM_ALPHA = 0.05
ERAS = SF.ERAS


# ---------------------------------------------------------------------
# registration 1: a session's bars in time order, VWAP and the trend
# ---------------------------------------------------------------------
def ordered(bars, vols):
    """(rows [(key, high, low, close)], volumes, VWAP at each close), in
    time order: wave twenty-two's rows_vwap with the volumes beside."""
    rows, vw = SF.rows_vwap(bars, vols)
    order = sorted(range(len(vols)), key=lambda k: bars[4 * k])
    return rows, [vols[k] for k in order], vw


def trend_at(keys, rows, i):
    """The close of bar i minus the close of the last bar at or before 30
    minutes earlier; None if there is none within 35 minutes."""
    k = keys[i] - TREND_S
    j = bisect.bisect_right(keys, k + 1e-9) - 1
    if j < 0 or keys[j] < keys[i] - TREND_LATE_S - 1e-9:
        return None
    return rows[i][3] - rows[j][3]


# ---------------------------------------------------------------------
# registration 2: the three rules
# ---------------------------------------------------------------------
def zone_signals(rows, vw, a):
    """{'RUBBER': [...], 'MOMENTUM': [...]}: the first signal of each
    direction per session, each dict(i, direction, close, d, trend)."""
    out = dict(RUBBER=[], MOMENTUM=[])
    if a is None or a <= 0:
        return out
    keys = [r[0] for r in rows]
    taken = set()
    for i, (k, _h, _lo, c) in enumerate(rows):
        if not RTH_OPEN <= k < ZONE_TO or vw[i] is None:
            continue
        tr = trend_at(keys, rows, i)
        if tr is None:
            continue
        d = c - vw[i]
        side = 1 if d > 0 else (-1 if d < 0 else 0)
        if not side:
            continue
        hits = []
        if abs(d) >= RUB_FAR * a - 1e-9 and -side * tr >= RUB_TREND * a - 1e-9:
            hits.append(('RUBBER', -side))
        if MOM_NEAR * a - 1e-9 <= abs(d) <= MOM_FAR * a + 1e-9 and \
                side * tr >= MOM_TREND * a - 1e-9:
            hits.append(('MOMENTUM', side))
        for rule, direction in hits:
            if (rule, direction) in taken:
                continue
            taken.add((rule, direction))
            out[rule].append(dict(i=i, direction=direction, close=c, d=d,
                                  trend=tr))
    return out


def overnight_value(rows, vols):
    """(POC, VAH, VAL) of the bars before 09:30, each bar's volume spread
    over the 1-point bins from its low to its high; None without a bar by
    18:30 and one from 09:00."""
    on = [(r, v) for r, v in zip(rows, vols) if r[0] < RTH_OPEN]
    if not on or on[0][0][0] > ON_FIRST_BY + 1e-9 or \
            on[-1][0][0] < ON_LAST_FROM - 1e-9:
        return None
    prof = collections.defaultdict(float)
    for (_k, h, lo, _c), v in on:
        if v <= 0:
            continue
        b0, b1 = int(math.floor(lo)), int(math.floor(h))
        share = v / (b1 - b0 + 1)
        for b in range(b0, b1 + 1):
            prof[b] += share
    if not prof:
        return None
    va = CX.value_area(dict(prof))
    return None if va[0] is None else va


def accept_signals(rows, va):
    """Part 16A's failed breaks of the overnight POC, VAH and VAL from
    09:30 to 17:00, the first at each level, each turned WITH the break."""
    if va is None:
        return []
    levels = dict(zip(ON_IDS, va))
    sigs = ML.signals(rows, lambda i: levels if RTH_OPEN <= rows[i][0] <
                      ACCEPT_TO else {})
    out = []
    for sg in ML.first_per_level(sigs):
        out.append(dict(sg, faded=sg['direction'], direction=sg['b']))
    return out


# ---------------------------------------------------------------------
# registration 3: the trades
# ---------------------------------------------------------------------
def outcome(rows, i, d, entry, target, stop):
    """Part 16A's outcome_bars with the rule's bracket: (outcome, gross
    ticks, seconds) from the close of bar i, or None when the session's
    bars end first."""
    k0 = rows[i][0] + 60.0
    t_end = k0 + HOLD_S
    last = None
    for k, h, lo, c in rows[i + 1:]:
        if k >= t_end:
            break
        if d > 0:
            hs, ht = lo <= entry - stop + 1e-9, h >= entry + target - 1e-9
        else:
            hs, ht = h >= entry + stop - 1e-9, lo <= entry - target + 1e-9
        if hs:
            return 'STOP', -stop / TICK, k + 60.0 - k0
        if ht:
            return 'TARGET', target / TICK, k + 60.0 - k0
        last = (k, c)
    if rows[-1][0] + 60.0 < t_end:
        return None
    if last is None:
        return 'TIMEOUT', 0.0, HOLD_S
    return 'TIMEOUT', d * (last[1] - entry) / TICK, last[0] + 60.0 - k0


def take(rows, sigs, session, rule):
    """One position at a time over a rule's signals."""
    target, stop = BRACKET[rule]
    out, busy = [], None
    for sg in sorted(sigs, key=lambda x: x['i']):
        k0 = rows[sg['i']][0] + 60.0
        if busy is not None and k0 < busy:
            continue
        res = outcome(rows, sg['i'], sg['direction'], sg['close'], target,
                      stop)
        if res is None:
            continue
        oc, g, secs = res
        busy = k0 + secs
        out.append(dict(session=session, month=session[:6],
                        year=session[:4], rule=rule, key=k0,
                        direction=sg['direction'], outcome=oc,
                        net=ML.net_points('NQ', oc, g),
                        level_id=sg.get('level_id')))
    return out


def history_trades(days):
    """{rule: trades} and the counts beside them."""
    tr = dict((r, []) for r in RULES)
    counts = dict(signals=dict((r, 0) for r in RULES), no_scale=0,
                  no_value_area=0, sessions=len(days))
    for s in sorted(days):
        day = days[s]
        rows, vols, vw = ordered(day['bars'], day['vols'])
        if not rows:
            continue
        if day['a'] is None:
            counts['no_scale'] += 1
        zs = zone_signals(rows, vw, day['a'])
        va = overnight_value(rows, vols)
        if va is None:
            counts['no_value_area'] += 1
        zs['ACCEPT'] = accept_signals(rows, va)
        for r in RULES:
            counts['signals'][r] += len(zs[r])
            tr[r] += take(rows, zs[r], s, r)
    return tr, counts


# ---------------------------------------------------------------------
# registration 4: the verdicts
# ---------------------------------------------------------------------
def verdicts(tr):
    """[one per rule] with Holm over the three."""
    tests = []
    for r in RULES:
        x = ML.month_verdict([(t['month'], t['net']) for t in tr[r]],
                             MIN_TRADES)
        x.update(test=r, name=NAMES[r])
        tests.append(x)
    rej = BM.holm([x.get('p') if x['status'] != 'NOT ENOUGH TRADES' else None
                   for x in tests], HOLM_ALPHA)
    for x, rj in zip(tests, rej):
        x['holm_rejected'] = rj
        if x['status'] == 'PASS' and not rj:
            x['status'] = 'NOT PROVEN'
            x['reasons'] = x['reasons'] + [
                'could be luck after allowing for three rules (Holm)']
    return tests


def describe(trades):
    n = len(trades)
    if not n:
        return dict(n=0)
    return dict(n=n, won=round(sum(1 for x in trades if x['net'] > 0) / n, 4),
                net_points=round(sum(x['net'] for x in trades) / n, 3),
                total_points=round(sum(x['net'] for x in trades), 2))


# ---------------------------------------------------------------------
# the read
# ---------------------------------------------------------------------
def run(path, unblind=False, stamps_tz='UTC', stamps='end'):
    allow = CX.is_validation if unblind else CX.is_dev
    days, rd, chk = SF.history_sessions(path, allow, stamps_tz, stamps)
    tr, counts = history_trades(days)
    tests = verdicts(tr)
    beside = {}
    for r in RULES:
        t = tr[r]
        b = dict(by_year=collections.OrderedDict(
            (y, describe([x for x in t if x['year'] == y]))
            for y in sorted({x['year'] for x in t})),
            by_direction=dict(
                long=describe([x for x in t if x['direction'] > 0]),
                short=describe([x for x in t if x['direction'] < 0])))
        if r == 'ACCEPT':
            b['by_level'] = dict((lid, describe([x for x in t
                                                 if x['level_id'] == lid]))
                                 for lid in ON_IDS)
        beside[r] = b
    ses = sorted(days)
    era = 'older' if unblind else 'newer'
    return dict(
        wave23=W23_VERSION, registration=REGISTRATION, era=era,
        years=ERAS[era], stamp_check=chk, files=rd.files,
        bad_lines=rd.bad_lines, sessions=len(ses),
        first_session=ses[0] if ses else None,
        last_session=ses[-1] if ses else None,
        sessions_skipped_unread=len(rd.skipped_sessions),
        sessions_refused=len(rd.refused_sessions), counts=counts,
        n_trades=dict((r, len(tr[r])) for r in RULES), tests=tests,
        beside=beside)


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def _line(d):
    if not d.get('n'):
        return '0 trades'
    return '%d trades, won %.0f%%, net %s a trade' % (
        d['n'], 100 * d['won'], _pts(d['net_points']))


def text(rep):
    names = [f['contract'] for f in rep['files']]
    c = rep['counts']
    lines = ['%s  %s' % (rep['wave23'], rep['years']),
             'files read: %d%s' % (len(names), '' if not names else
                                   ' (%s .. %s)' % (names[0], names[-1])),
             'sessions traded: %d (%s .. %s); cash open found at %s' % (
                 rep['sessions'], rep['first_session'], rep['last_session'],
                 rep['stamp_check'].get('open_minute')),
             'sessions without the average range: %d; without an overnight '
             'value area: %d' % (c['no_scale'], c['no_value_area']),
             'A = the average session range of the last 14 sessions; 30 '
             'minutes at most; one trade at a time within each rule; net '
             'after costs']
    for x in rep['tests']:
        r = x['test']
        tg, st = BRACKET[r]
        lines += ['', '%s' % x['name'],
                  '   target %g, stop %g; signals %d; trades %d over %s '
                  'months' % (tg, st, c['signals'][r], x['n'],
                              x.get('clusters', 0))]
        if x['n']:
            ci = x.get('ci95')
            lines.append('   won %.0f%%, net %s a trade, total %s points' % (
                100 * x['won'], _pts(x['net_points']),
                _pts(x['total_points'])))
            lines.append('   95%% range of net a trade: %s   p %s' % (
                '-' if not ci else '%s .. %s' % (_pts(ci[0]), _pts(ci[1])),
                '-' if x.get('p') is None else '%.4f' % x['p']))
            wb = x['without_best']
            lines.append('   without the best month (%s): net %s a trade' % (
                wb['cluster'], _pts(wb['net_points'])))
        lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
            x['reasons'])) if x.get('reasons') else ''))
        b = rep['beside'][r]
        lines.append('   beside: longs %s; shorts %s' % (
            _line(b['by_direction']['long']),
            _line(b['by_direction']['short'])))
        for lid, d in b.get('by_level', {}).items():
            lines.append('   beside: at %-6s %s' % (lid, _line(d)))
        for y, d in b['by_year'].items():
            lines.append('   %s  %s' % (y, _line(d)))
    lines.append('')
    if rep['era'] == 'newer':
        lines.append('A rule is confirmed only if it also passes on the older '
                     'years: run the same command with --unblind.')
    else:
        lines.append('A rule is confirmed only if it passes on the newer '
                     'years as well (the same command without --unblind).')
    lines.append('Minute bars: first touch on highs and lows, a bar touching '
                 'both counted as a stop; costs charged; not P&L. No order '
                 'was placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    out = arg('--out')
    unblind = '--unblind' in argv
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    if unblind:
        print('*** UNBLIND: wave twenty-three on the sessions before %s, '
              'once. ***\n' % CX.VALIDATION_BEFORE)
    try:
        rep = run(argv[0], unblind, stz, stp)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        print('\nwave-twenty-three report -> %s' % out)
    if unblind:
        here = os.path.dirname(os.path.abspath(__file__))
        n = LG.record_history_read(
            dict(rep, n_trades=sum(rep['n_trades'].values())),
            os.path.join(here, HISTORY_LEDGER), W23_VERSION)
        print('history read recorded (%d read(s))' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
