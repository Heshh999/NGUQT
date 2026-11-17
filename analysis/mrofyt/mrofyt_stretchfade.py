#!/usr/bin/env python3
"""mrofyt_stretchfade.py - MROF-YT-W22-STRETCHFADE-1.0

MROF_YT_WAVE22_STRETCHFADE_REGISTRATION.md turned into running code: on
years of NQ one-minute bars, does fading a failed break work when the
price is stretched far from VWAP and the fade trades back toward it?

    signal     part 16A's: a bar trades 2 ticks through yesterday's, last
               week's or the overnight high or low; that bar or one of
               the next 4 closes back: fade at that close. Every signal.
    STRETCHED  the close is at least 0.25 x A from the session VWAP and
               the fade trades back toward it (A = the mean range of the
               last 14 sessions; wave twelve's rule, unchanged)
    REST       every other signal
    trade      target 25 points, stop 15, 30 minutes; one at a time
               within each group; net of costs

    ST1  the stretched fade makes money (month-clustered, 100+ trades)
    ST2  STRETCHED minus REST is above zero

Two eras, each a test; the rule is confirmed only if ST1 passes in both.

    python3 mrofyt_stretchfade.py "<NQ minute exports>" --out w22_new.json            # 2019-06 .. 2026-06
    python3 mrofyt_stretchfade.py "<NQ minute exports>" --unblind --out w22_old.json  # before 2019-06-01

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import array
import collections
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_context as CX
import mrofyt_l2context as X
import mrofyt_l2targets as W
import mrofyt_ledgers as LG
import mrofyt_minutelevels as ML
import mrofyt_smt as SMT

W22_VERSION = 'MROF-YT-W22-STRETCHFADE-1.0'
REGISTRATION = 'MROF_YT_WAVE22_STRETCHFADE_REGISTRATION.md'
HISTORY_LEDGER = ML.HISTORY_LEDGER
STRETCH_K = X.TREND_K                 # 0.25: wave twelve's, unchanged
RANGE_SESSIONS, RANGE_MIN_SESSIONS = W.RANGE_SESSIONS, W.RANGE_MIN_SESSIONS
MIN_TRADES = ML.MIN_HISTORY           # 100
HOLM_ALPHA = 0.05
GROUPS = ('STRETCHED', 'REST')


def _ymd(s):
    return '%s-%s-%s' % (s[:4], s[4:6], s[6:8])


ERAS = dict(newer='NEWER YEARS (from %s, before %s)' % (
    _ymd(CX.VALIDATION_BEFORE), _ymd(CX.REFUSE_FROM)),
    older='OLDER YEARS (before %s)' % _ymd(CX.VALIDATION_BEFORE))


# ---------------------------------------------------------------------
# registration 1: part 16A's bars, with each bar's volume and the scale
# ---------------------------------------------------------------------
class VolDayAgg(ML.FullDayAgg):
    __slots__ = ('vols',)

    def __init__(self):
        ML.FullDayAgg.__init__(self)
        self.vols = array.array('d')       # one per bar, in file order

    def add(self, sod, o, h, lo, c, v):
        ML.FullDayAgg.add(self, sod, o, h, lo, c, v)
        self.vols.append(v)

    def finalize(self):
        out = ML.FullDayAgg.finalize(self)
        out['vols'] = self.vols
        return out


class VolReader(CX.Reader):
    agg_class = VolDayAgg


def history_sessions(path, allow, stamps_tz='UTC', stamps='end'):
    """Part 16A's history_sessions, with each bar's volume and the day's
    scale: {session: dict(contract, bars, vols, yday, lweek, a)}. `a` is
    the mean full-session range of the last 14 earlier sessions that
    have a complete cash session (5 at least), each on its own front
    contract."""
    rd = VolReader('NQ', stamps_tz, stamps, allow)
    rd.read_path(path)
    if not rd.days:
        raise CX.ContextDataError(CX._nothing_read(
            rd, 'NQ', 'in the years this mode reads'))
    chk = rd.check_stamps()
    recs = CX.build_days(rd.days)
    every = sorted({s for _c, s in rd.days})
    before = dict(zip(every[1:], every[:-1]))
    weeks = collections.defaultdict(dict)
    for (c, s), d in rd.days.items():
        if d['full_high'] is None:
            continue
        hl = weeks[c].setdefault(ML._date(s).isocalendar()[:2],
                                 [d['full_high'], d['full_low']])
        hl[0], hl[1] = max(hl[0], d['full_high']), min(hl[1], d['full_low'])
    ranges, out = [], {}
    for r in recs:
        s, c = r['session'], r['contract']
        d = rd.days[(c, s)]
        prev = ranges[-RANGE_SESSIONS:]
        a = sum(prev) / len(prev) if len(prev) >= RANGE_MIN_SESSIONS \
            else None
        if d['full_high'] is not None:
            ranges.append(d['full_high'] - d['full_low'])
        p = before.get(s)
        y = rd.days.get((c, p)) if p else None
        if not r['eligible'] or y is None or not y['complete']:
            continue
        wk = (ML._date(s) - ML._dt.timedelta(days=7)).isocalendar()[:2]
        out[s] = dict(contract=c, bars=d['bars'], vols=d['vols'],
                      yday=(y['full_high'], y['full_low']),
                      lweek=tuple(weeks[c][wk]) if wk in weeks[c] else None,
                      a=a)
    return out, rd, chk


# ---------------------------------------------------------------------
# registration 3: the session VWAP on bars, and the split
# ---------------------------------------------------------------------
def rows_vwap(bars, vols):
    """([(key, high, low, close)] in time order, the session VWAP at each
    bar's close). VWAP = sum((high + low + close) / 3 x volume) / sum
    (volume) from the session's first bar, bars with volume only; None
    until one has traded."""
    order = sorted(range(len(vols)), key=lambda k: bars[4 * k])
    rows, vw = [], []
    num = den = 0.0
    for k in order:
        key, h, lo, c = bars[4 * k:4 * k + 4]
        v = vols[k]
        if v > 0:
            num += (h + lo + c) / 3.0 * v
            den += v
        rows.append((key, h, lo, c))
        vw.append(num / den if den > 0 else None)
    return rows, vw


def group_of(direction, close, vwap, a):
    """'STRETCHED', 'REST' or None (no A or no VWAP): wave twelve's
    classify, STRETCHED being the trades its TREND filter removed."""
    cls = X.classify(direction, close, vwap, None, a)['TREND']
    return {'removed': 'STRETCHED', 'kept': 'REST'}.get(cls)


def session_signals(day):
    """(rows, part 16A's signals of one session, each with its group,
    its distance from VWAP and whether it is the first at its level)."""
    rows, vw = rows_vwap(day['bars'], day['vols'])
    if not rows:
        return rows, []
    base, full = ML.session_levels(rows, day)
    sigs = ML.signals(rows, lambda i: full if rows[i][0] >= CX.RTH_OPEN
                      else base)
    first = {id(s) for s in ML.first_per_level(sigs)}
    for sg in sigs:
        v = vw[sg['i']]
        sg.update(group=group_of(sg['direction'], sg['close'], v, day['a']),
                  dist=None if v is None else sg['close'] - v,
                  first=id(sg) in first)
    return rows, sigs


# ---------------------------------------------------------------------
# registration 4: the trade (part 16A's loop)
# ---------------------------------------------------------------------
def take(rows, sigs, session):
    """One position at a time over these signals: part 16A's loop."""
    out, busy = [], None
    for sg in sorted(sigs, key=lambda x: x['i']):
        k0 = rows[sg['i']][0] + 60.0
        if busy is not None and k0 < busy:
            continue
        res = ML.outcome_bars(rows, sg['i'], sg['direction'], sg['close'])
        if res is None:
            continue
        oc, g, secs = res
        busy = k0 + secs
        out.append(dict(session=session, month=session[:6],
                        year=session[:4], level_id=sg['level_id'],
                        direction=sg['direction'], outcome=oc,
                        net=ML.net_points('NQ', oc, g), key=k0,
                        group=sg['group'], dist=sg['dist']))
    return out


SETS = ('STRETCHED', 'REST', 'EVERY', 'FIRST_STRETCHED', 'FIRST_REST')


def history_trades(days):
    """{set: trades} and the signal counts. STRETCHED and REST are the
    tested groups; EVERY is part 16A's unsplit 'every'; the FIRST sets
    split the first signal at each level only."""
    out = dict((k, []) for k in SETS)
    n_sig = unsplit = 0
    for s in sorted(days):
        rows, sigs = session_signals(days[s])
        n_sig += len(sigs)
        unsplit += sum(1 for x in sigs if x['group'] is None)
        for g in GROUPS:
            mine = [x for x in sigs if x['group'] == g]
            out[g] += take(rows, mine, s)
            out['FIRST_' + g] += take(rows, [x for x in mine if x['first']],
                                      s)
        out['EVERY'] += take(rows, sigs, s)
    return out, dict(signals=n_sig, unsplit=unsplit)


# ---------------------------------------------------------------------
# registration 5: the two tests
# ---------------------------------------------------------------------
def describe(trades):
    n = len(trades)
    if not n:
        return dict(n=0)
    return dict(n=n, won=round(sum(1 for x in trades if x['net'] > 0) / n, 4),
                net_points=round(sum(x['net'] for x in trades) / n, 3),
                total_points=round(sum(x['net'] for x in trades), 2))


def separation(stretched, rest):
    """ST2: mean net of STRETCHED minus REST, month-clustered over both
    groups at once."""
    a = [(x['month'], x['net']) for x in stretched]
    b = [(x['month'], x['net']) for x in rest]
    out = dict(test='ST2', name='the stretch separates: STRETCHED minus REST',
               n=len(a), n_rest=len(b))
    out.update(SMT.diff_stats(a, b))
    if len(a) < MIN_TRADES or len(b) < MIN_TRADES:
        out['status'], out['reasons'] = 'NOT ENOUGH TRADES', [
            '%d and %d of the %d needed on each side' % (len(a), len(b),
                                                        MIN_TRADES)]
        return out
    reasons = []
    ci = out.get('ci95')
    if out['diff'] <= 0:
        reasons.append('the stretched trades do no better than the rest')
    elif not ci or ci[0] <= 0:
        reasons.append('could be luck: the 95 % range reaches zero')
    out['status'] = 'NOT PROVEN' if reasons else 'PASS'
    out['reasons'] = reasons
    return out


def verdicts(tr):
    """[ST1, ST2] with Holm over the two."""
    st1 = ML.month_verdict([(x['month'], x['net']) for x in tr['STRETCHED']],
                           MIN_TRADES)
    st1.update(test='ST1', name='the stretched fade makes money')
    tests = [st1, separation(tr['STRETCHED'], tr['REST'])]
    rej = BM.holm([x.get('p') if x['status'] != 'NOT ENOUGH TRADES' else None
                   for x in tests], HOLM_ALPHA)
    for x, rj in zip(tests, rej):
        x['holm_rejected'] = rj
        if x['status'] == 'PASS' and not rj:
            x['status'] = 'NOT PROVEN'
            x['reasons'] = x['reasons'] + [
                'could be luck after allowing for two tests (Holm)']
    return tests


# ---------------------------------------------------------------------
# the read
# ---------------------------------------------------------------------
def run(path, unblind=False, stamps_tz='UTC', stamps='end'):
    allow = CX.is_validation if unblind else CX.is_dev
    days, rd, chk = history_sessions(path, allow, stamps_tz, stamps)
    tr, counts = history_trades(days)
    tests = verdicts(tr)
    by_year = collections.OrderedDict()
    for y in sorted({x['year'] for g in GROUPS for x in tr[g]}):
        by_year[y] = dict((g.lower(), describe([x for x in tr[g]
                                               if x['year'] == y]))
                          for g in GROUPS)
    st = tr['STRETCHED']
    ses = sorted(days)
    era = 'older' if unblind else 'newer'
    return dict(
        wave22=W22_VERSION, registration=REGISTRATION, era=era,
        years=ERAS[era], stretch_k=STRETCH_K, stamp_check=chk,
        files=rd.files, bad_lines=rd.bad_lines, sessions=len(ses),
        first_session=ses[0] if ses else None,
        last_session=ses[-1] if ses else None,
        sessions_skipped_unread=len(rd.skipped_sessions),
        sessions_refused=len(rd.refused_sessions),
        signals=counts['signals'], unsplit=counts['unsplit'],
        n_trades=len(st), tests=tests,
        beside=dict(
            rest=describe(tr['REST']), every=describe(tr['EVERY']),
            first=dict(stretched=describe(tr['FIRST_STRETCHED']),
                       rest=describe(tr['FIRST_REST'])),
            by_year=by_year,
            by_direction=dict(
                long=describe([x for x in st if x['direction'] > 0]),
                short=describe([x for x in st if x['direction'] < 0])),
            by_level=dict((lid, describe([x for x in st
                                          if x['level_id'] == lid]))
                          for lid in ML.LEVEL_IDS)))


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def _line(d):
    if not d.get('n'):
        return '0 trades'
    return '%d trades, won %.0f%%, net %s a trade' % (
        d['n'], 100 * d['won'], _pts(d['net_points']))


def text(rep):
    b = rep['beside']
    names = [f['contract'] for f in rep['files']]
    lines = ['%s  %s' % (rep['wave22'], rep['years']),
             'files read: %d%s' % (len(names), '' if not names else
                                   ' (%s .. %s)' % (names[0], names[-1])),
             'sessions traded: %d (%s .. %s); cash open found at %s' % (
                 rep['sessions'], rep['first_session'], rep['last_session'],
                 rep['stamp_check'].get('open_minute')),
             'rule: a failed break of yesterday\'s, last week\'s or the '
             'overnight high or low on one-minute bars, faded, when the '
             'close is at least %.2f x the average session range from VWAP '
             'and the fade trades back toward it; target 25, stop 15, 30 '
             'min; one trade at a time; net after costs' % rep['stretch_k'],
             'signals: %d (%d without a range or a VWAP, in neither group)'
             % (rep['signals'], rep['unsplit'])]
    st1, st2 = rep['tests']
    lines += ['', 'ST1  %s' % st1['name'],
              '   trades %d over %s months' % (st1['n'],
                                               st1.get('clusters', 0))]
    if st1['n']:
        ci = st1.get('ci95')
        lines.append('   won %.0f%%, net %s a trade, total %s points' % (
            100 * st1['won'], _pts(st1['net_points']),
            _pts(st1['total_points'])))
        lines.append('   95%% range of net a trade: %s   p %s' % (
            '-' if not ci else '%s .. %s' % (_pts(ci[0]), _pts(ci[1])),
            '-' if st1.get('p') is None else '%.4f' % st1['p']))
        wb = st1['without_best']
        lines.append('   without the best month (%s): net %s a trade' % (
            wb['cluster'], _pts(wb['net_points'])))
    lines.append('   VERDICT: %s%s' % (st1['status'], (': ' + '; '.join(
        st1['reasons'])) if st1.get('reasons') else ''))
    lines += ['', 'ST2  %s' % st2['name'],
              '   stretched %d trades, the rest %d' % (st2['n'],
                                                       st2['n_rest'])]
    if st2.get('diff') is not None:
        ci = st2.get('ci95')
        lines.append('   net a trade: stretched %s, the rest %s, difference '
                     '%s' % (_pts(st2['mean_a']), _pts(st2['mean_b']),
                             _pts(st2['diff'])))
        lines.append('   95%% range of the difference: %s   p %s' % (
            '-' if not ci else '%s .. %s' % (_pts(ci[0]), _pts(ci[1])),
            '-' if st2.get('p') is None else '%.4f' % st2['p']))
    lines.append('   VERDICT: %s%s' % (st2['status'], (': ' + '; '.join(
        st2['reasons'])) if st2.get('reasons') else ''))
    lines += ['', 'beside, not tested:',
              '   the rest: %s' % _line(b['rest']),
              '   every signal, not split: %s' % _line(b['every']),
              '   first signal at each level only: stretched %s; the rest %s'
              % (_line(b['first']['stretched']), _line(b['first']['rest'])),
              '   stretched longs: %s' % _line(b['by_direction']['long']),
              '   stretched shorts: %s' % _line(b['by_direction']['short'])]
    for lid, d in b['by_level'].items():
        lines.append('   stretched at %-15s %s' % (lid + ':', _line(d)))
    for y, d in b['by_year'].items():
        lines.append('   %s  stretched %s | the rest %s' % (
            y, _line(d['stretched']), _line(d['rest'])))
    lines.append('')
    if rep['era'] == 'newer':
        lines.append('The rule is confirmed only if ST1 also passes on the '
                     'older years: run the same command with --unblind.')
    else:
        lines.append('The rule is confirmed only if ST1 passes on the newer '
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
        print('*** UNBLIND: wave twenty-two on the sessions before %s, once. '
              '***\n' % CX.VALIDATION_BEFORE)
    try:
        rep = run(argv[0], unblind, stz, stp)
    except CX.ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    print(text(rep))
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        print('\nwave-twenty-two report -> %s' % out)
    if unblind:
        here = os.path.dirname(os.path.abspath(__file__))
        n = LG.record_history_read(rep, os.path.join(here, HISTORY_LEDGER),
                                   W22_VERSION)
        print('history read recorded (%d read(s))' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
