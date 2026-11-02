#!/usr/bin/env python3
"""mrofyt_minutelevels.py - MROF-YT-W16A-MINUTELEVELS-1.0

MROF_YT_WAVE16_REGISTRATION.md, part 16A, turned into running code: L2's
six levels traded WITHOUT order flow, on one-minute bars.

    signal  a bar trades 2 ticks through a level from one side; that bar
            or one of the next 4 closes back: fade at that close. Only
            the first signal at each level per session; one at a time.
    trade   target 25 points, stop 15, 30 minutes; net of costs

    16A-H  history: NQ minute exports, month-clustered; described on
           2019-06 .. 2026-06, judged once on the sessions before
           2019-06-01 (--unblind)
    16A-R  recordings: wave fourteen's L2 first signals (with order flow)
           minus this rule (without) on the same sessions

    python3 mrofyt_minutelevels.py --history "<NQ minute exports>" --out m16a.json
    python3 mrofyt_minutelevels.py --history "<NQ minute exports>" --unblind --out m16a_val.json
    python3 mrofyt_minutelevels.py "<capture>" --out w16a.json            # recordings, DEV
    python3 mrofyt_minutelevels.py "<capture>" --unblind --out w16a_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import array
import bisect
import collections
import datetime as _dt
import json
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_closereclaim as C
import mrofyt_context as CX
import mrofyt_costs as CO
import mrofyt_discover as DI
import mrofyt_l2firstsignal as FS
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG
import mrofyt_smt as SMT

W16A_VERSION = 'MROF-YT-W16A-MINUTELEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE16_REGISTRATION.md'
HISTORY_LEDGER = 'MROF_MINUTE_HISTORY_EXPOSURE.json'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER
TICK = SIG.TICK

LEVEL_IDS = BM.RANGE_LEVELS
ON_IDS = ('OVERNIGHT_HIGH', 'OVERNIGHT_LOW')
BREAK_TICKS = 2
FAIL_BARS = 5
TARGET_PTS, STOP_PTS = LB.TARGET * TICK, LB.FIXED_STOP * TICK
HOLD_S = float(LB.LIMIT_S)
MIN_HISTORY = 100
MIN_TRADES = FS.MIN_TRADES
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


# ---------------------------------------------------------------------
# A3: the signal (pure)
# ---------------------------------------------------------------------
def signals(bars, levels_at):
    """bars: [(time key, high, low, close)] of one session in time order;
    levels_at(i): {level id: price or None} known at bar i. Every
    failed-break signal: [dict(i, level_id, level, b, direction, close)]."""
    state = {}
    out = []
    for i, (_k, h, lo, c) in enumerate(bars):
        for lid, L in levels_at(i).items():
            if L is None:
                continue
            st = state.setdefault(lid, dict(side=0, brk=None))
            s = st['side']
            if st['brk'] is None and s:
                if (s < 0 and h >= L + BREAK_TICKS * TICK - 1e-9) or \
                        (s > 0 and lo <= L - BREAK_TICKS * TICK + 1e-9):
                    st['brk'], st['last'] = i, None
            cs = C.side(c, L)
            if st['brk'] is not None:
                if cs == s:
                    out.append(dict(i=i, level_id=lid, level=L, b=-s,
                                    direction=s, close=c))
                    st['brk'] = None
                    continue
                if i - st['brk'] < FAIL_BARS - 1:
                    if cs:
                        st['last'] = cs
                    continue
                st['brk'] = None                    # held: no signal
                st['side'] = cs or st.get('last') or -s
                continue
            if cs:
                st['side'] = cs
    return out


def first_per_level(sigs):
    """The first signal at each level (one session's signals)."""
    seen, out = set(), []
    for s in sorted(sigs, key=lambda s: s['i']):
        if s['level_id'] not in seen:
            seen.add(s['level_id'])
            out.append(s)
    return out


# ---------------------------------------------------------------------
# A4: the trade on minute bars (pure)
# ---------------------------------------------------------------------
def outcome_bars(rows, i, d, entry):
    """(outcome, gross ticks, seconds) from the close of bar i on the
    following bars, or None when the session's bars end first."""
    k0 = rows[i][0] + 60.0
    t_end = k0 + HOLD_S
    last = None
    for k, h, lo, c in rows[i + 1:]:
        if k >= t_end:
            break
        if d > 0:
            hs, ht = lo <= entry - STOP_PTS + 1e-9, h >= entry + TARGET_PTS - 1e-9
        else:
            hs, ht = h >= entry + STOP_PTS - 1e-9, lo <= entry - TARGET_PTS + 1e-9
        if hs:
            return 'STOP', -float(LB.FIXED_STOP), k + 60.0 - k0
        if ht:
            return 'TARGET', float(LB.TARGET), k + 60.0 - k0
        last = (k, c)
    if rows[-1][0] + 60.0 < t_end:
        return None
    if last is None:
        return 'TIMEOUT', 0.0, HOLD_S
    return 'TIMEOUT', d * (last[1] - entry) / TICK, last[0] + 60.0 - k0


def net_points(inst, outcome, gross_ticks):
    return (gross_ticks - CO.cost_ticks(
        inst, 'STOP' if outcome == 'STOP' else 'TARGET')) / 4.0


def month_verdict(trades, min_n):
    """trades: [(cluster, net points)]. Mean net above 0 with its 95 %
    interval above 0 (clustered), and above 0 without the cluster of the
    largest total net; at least min_n."""
    n = len(trades)
    out = dict(n=n)
    if n:
        st = DI.cluster_stats([(m, x, 0.0, x) for m, x in trades])
        by = collections.defaultdict(float)
        for m, x in trades:
            by[m] += x
        best = max(by, key=lambda m: (by[m], m))
        rest = [x for m, x in trades if m != best]
        out.update(clusters=st.get('sessions', 0),
                   won=round(sum(1 for _m, x in trades if x > 0) / n, 4),
                   net_points=round(sum(x for _m, x in trades) / n, 3),
                   total_points=round(sum(x for _m, x in trades), 2),
                   t=st.get('t'), p=st.get('p'), ci95=st.get('ci95'),
                   without_best=dict(cluster=best, n=len(rest),
                                     net_points=round(sum(rest) / len(rest),
                                                      3) if rest else None))
    if n < min_n:
        out['status'], out['reasons'] = 'NOT ENOUGH TRADES', [
            '%d of the %d needed' % (n, min_n)]
        return out
    reasons = []
    ci = out.get('ci95')
    if out['net_points'] <= 0:
        reasons.append('loses after costs')
    elif not ci or ci[0] <= 0:
        reasons.append('could be luck: the 95 % range reaches zero')
    wb = out['without_best']
    if out['net_points'] > 0 and (wb['net_points'] is None or
                                  wb['net_points'] <= 0):
        reasons.append('rests on one month: without %s it does not make '
                       'money' % wb['cluster'])
    out['status'] = 'NOT PROVEN' if reasons else 'PASS'
    out['reasons'] = reasons
    return out


# ---------------------------------------------------------------------
# A1-A2 history: the context study's reader keeping every bar
# ---------------------------------------------------------------------
class FullDayAgg(CX.DayAgg):
    __slots__ = ('bars', 'fh', 'fl')

    def __init__(self):
        CX.DayAgg.__init__(self)
        self.bars = array.array('d')       # key, high, low, close
        self.fh = self.fl = None

    def add(self, sod, o, h, lo, c, v):
        CX.DayAgg.add(self, sod, o, h, lo, c, v)
        key = sod - 86400 if sod >= CX.SESSION_ROLL else sod
        self.bars.extend((key, h, lo, c))
        self.fh = h if self.fh is None else max(self.fh, h)
        self.fl = lo if self.fl is None else min(self.fl, lo)

    def finalize(self):
        out = CX.DayAgg.finalize(self)
        out.update(bars=self.bars, full_high=self.fh, full_low=self.fl)
        return out


class FullReader(CX.Reader):
    agg_class = FullDayAgg


def _date(ses):
    return _dt.date(int(ses[:4]), int(ses[4:6]), int(ses[6:8]))


def _rows(bars):
    rows = [(bars[k], bars[k + 1], bars[k + 2], bars[k + 3])
            for k in range(0, len(bars), 4)]
    rows.sort(key=lambda r: r[0])
    return rows


def history_sessions(path, allow, stamps_tz='UTC', stamps='end'):
    """{session: dict(contract, bars, yday, lweek)}: the context study's
    front contract and eligible sessions, yesterday complete on the same
    contract (A2)."""
    rd = FullReader('NQ', stamps_tz, stamps, allow)
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
        hl = weeks[c].setdefault(_date(s).isocalendar()[:2],
                                 [d['full_high'], d['full_low']])
        hl[0], hl[1] = max(hl[0], d['full_high']), min(hl[1], d['full_low'])
    out = {}
    for r in recs:
        s, c = r['session'], r['contract']
        prev = before.get(s)
        y = rd.days.get((c, prev)) if prev else None
        if not r['eligible'] or y is None or not y['complete']:
            continue
        wk = (_date(s) - _dt.timedelta(days=7)).isocalendar()[:2]
        out[s] = dict(contract=c, bars=rd.days[(c, s)]['bars'],
                      yday=(y['full_high'], y['full_low']),
                      lweek=tuple(weeks[c][wk]) if wk in weeks[c] else None)
    return out, rd, chk


def session_levels(rows, day):
    """(levels before 09:30, levels from 09:30) of one session."""
    on = [(h, lo) for k, h, lo, _c in rows if k < CX.RTH_OPEN]
    lw = day['lweek'] or (None, None)
    base = dict(YDAY_HIGH=day['yday'][0], YDAY_LOW=day['yday'][1],
                LWEEK_HIGH=lw[0], LWEEK_LOW=lw[1])
    full = dict(base, OVERNIGHT_HIGH=max(h for h, _l in on) if on else None,
                OVERNIGHT_LOW=min(lo for _h, lo in on) if on else None)
    return base, full


def history_trades(days):
    """{'first': [...], 'every': [...]}: each one position at a time per
    session, every trade dict(session, month, year, level_id, direction,
    outcome, net, key)."""
    out = dict(first=[], every=[])
    for s in sorted(days):
        rows = _rows(days[s]['bars'])
        if not rows:
            continue
        base, full = session_levels(rows, days[s])
        sigs = signals(rows, lambda i: full if rows[i][0] >= CX.RTH_OPEN
                       else base)
        for which, chosen in (('first', first_per_level(sigs)),
                              ('every', sigs)):
            busy = None
            for sg in sorted(chosen, key=lambda x: x['i']):
                k0 = rows[sg['i']][0] + 60.0
                if busy is not None and k0 < busy:
                    continue
                res = outcome_bars(rows, sg['i'], sg['direction'],
                                   sg['close'])
                if res is None:
                    continue
                oc, g, secs = res
                busy = k0 + secs
                out[which].append(dict(
                    session=s, month=s[:6], year=s[:4],
                    level_id=sg['level_id'], direction=sg['direction'],
                    outcome=oc, net=net_points('NQ', oc, g), key=k0))
    return out


def run_history(path, unblind=False, stamps_tz='UTC', stamps='end'):
    allow = CX.is_validation if unblind else CX.is_dev
    days, rd, chk = history_sessions(path, allow, stamps_tz, stamps)
    tr = history_trades(days)
    test = month_verdict([(x['month'], x['net']) for x in tr['first']],
                         MIN_HISTORY)
    every = month_verdict([(x['month'], x['net']) for x in tr['every']], 1)
    by_year = collections.defaultdict(list)
    for x in tr['first']:
        by_year[x['year']].append(x['net'])
    if not unblind:
        test['status'] += ' (DEV years: describes)'
    ses = sorted(days)
    rep = dict(wave16a=W16A_VERSION, registration=REGISTRATION,
               part='16A-H history', mode='validation' if unblind else 'dev',
               years=('before %s' % CX.VALIDATION_BEFORE) if unblind else
               ('%s to %s' % (CX.VALIDATION_BEFORE, CX.REFUSE_FROM)),
               stamp_check=chk, sessions=len(ses),
               first_session=ses[0] if ses else None,
               last_session=ses[-1] if ses else None,
               sessions_skipped_unread=len(rd.skipped_sessions),
               n_trades=test['n'], test=test,
               every=dict((k, every.get(k)) for k in
                          ('n', 'won', 'net_points', 'total_points')),
               by_year={y: dict(n=len(v), net_points=round(sum(v) / len(v),
                                                           3))
                        for y, v in sorted(by_year.items())},
               by_level=dict(collections.Counter(
                   x['level_id'] for x in tr['first'])))
    return rep


# ---------------------------------------------------------------------
# A1-A3 recordings: minute bars of the recorded mid
# ---------------------------------------------------------------------
class MinuteLevelsRunner(C.CloseRunner):
    """Wave ten's runner (its grid carries the six levels); unchanged.
    The ledger names part 16A."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        C.CloseRunner.__init__(self, capture_dir, unblind=unblind,
                               holdout=holdout, **kw)
        self.ledger['wave16a'] = dict(version=W16A_VERSION)


def minute_bars(ts, ps):
    """[(minute, high, low, close)] of one run's mid path for every clock
    minute from its first mid to its last; the mid in force at a
    minute's start counts, a minute without a new mid is flat."""
    out = []
    n = len(ts)
    if not n:
        return out
    j, cur = 0, ps[0]
    for m in range(int(ts[0] // 60), int(ts[-1] // 60) + 1):
        end = (m + 1) * 60.0
        h = lo = cur
        while j < n and ts[j] < end:
            p = ps[j]
            if p > h:
                h = p
            if p < lo:
                lo = p
            cur = p
            j += 1
        out.append((m, h, lo, cur))
    return out


def recording_trades(r):
    """[(event, outcome, gross ticks, risk ticks, seconds)]: the first
    minute-bar signal at each level per instrument and session."""
    gby = collections.defaultdict(dict)
    for g in r.grid:
        gby[(g['instrument'], g['run'])][int(round(g['t']))] = g
    paths = V.compressed_paths(r)
    seen = set()
    out = []
    for key in sorted(paths, key=lambda k: (k[0], paths[k][0][0])):
        if key not in gby:
            continue
        inst, run = key
        ts, ps = paths[key]
        chunks = collections.OrderedDict()
        for m, h, lo, c in minute_bars(ts, ps):
            g = gby[key].get((m + 1) * 60)
            if g is None:
                continue
            lv = dict(zip(LEVEL_IDS, g.get('w10_lv') or ()))
            chunks.setdefault(g['session'], []).append(((m * 60.0, h, lo, c),
                                                        lv))
        for ses, items in chunks.items():
            rows = [x[0] for x in items]
            for sg in sorted(signals(rows, lambda i: items[i][1]),
                             key=lambda x: x['i']):
                k = (inst, ses, sg['level_id'])
                if k in seen:
                    continue
                seen.add(k)
                t_sig = rows[sg['i']][0] + 60.0
                i0 = bisect.bisect_right(ts, t_sig) - 1
                if i0 < 0:
                    continue
                res = LB.path_exit(ts, ps, i0, sg['direction'], LB.TARGET,
                                   LB.FIXED_STOP)
                if res[0] == 'UNRESOLVED':
                    continue
                e = dict(instrument=inst, session=ses, run=run, t=t_sig,
                         level_id=sg['level_id'], level=sg['level'],
                         direction=sg['direction'], family='MINUTE')
                out.append((e, res[0], res[1], LB.FIXED_STOP, res[2]))
    return out


def _nets(rows):
    return [(x[0]['session'],
             net_points(x[0]['instrument'], x[1], x[2])) for x in rows]


def run_recordings(capture_dir, unblind=False, holdout=False,
                   max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = MinuteLevelsRunner(capture_dir, unblind=unblind, holdout=holdout,
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
    minute = [x for x in recording_trades(r) if keep(x[0]['session'])]
    ev = [e for e in V.variant_events(r) if keep(e['session'])]
    fs_ids = {id(e) for e in FS.first_signals(ev)}
    l2 = [x for x in V.score_variants(r, ev).get('V0', [])
          if id(x[0]) in fs_ids]
    insts = sorted({x[0]['instrument'] for x in minute + l2} | {PRIMARY})
    results = {}
    for inst in insts:
        a = V.one_at_a_time([x for x in l2 if x[0]['instrument'] == inst])
        b = V.one_at_a_time([x for x in minute
                             if x[0]['instrument'] == inst])
        sa, sb = LB.test_stats(a, inst), LB.test_stats(b, inst)
        diff = SMT.diff_stats(_nets(a), _nets(b))
        res = dict(with_flow=dict(n=sa['n'], hit=sa.get('hit'),
                                  net_points=sa.get('net_points')),
                   without_flow=dict(n=sb['n'], hit=sb.get('hit'),
                                     net_points=sb.get('net_points')),
                   diff=diff, n=min(sa['n'], sb['n']),
                   sessions=len({s for s, _x in _nets(a) + _nets(b)}))
        if inst != PRIMARY:
            res['status'], res['reasons'] = 'DESCRIBED (not tested)', []
        elif res['n'] < MIN_TRADES:
            res['status'], res['reasons'] = 'NOT ENOUGH TRADES', [
                '%d of the %d needed on each side' % (res['n'], MIN_TRADES)]
        else:
            ci = diff.get('ci95')
            if diff.get('diff') is None or diff['diff'] <= 0:
                res['status'], res['reasons'] = 'NOT PROVEN', [
                    'the order flow does not add']
            elif not ci or ci[0] <= 0:
                res['status'], res['reasons'] = 'NOT PROVEN', [
                    'could be luck: the 95 % range reaches zero']
            else:
                res['status'], res['reasons'] = 'PASS', []
        results[inst] = res
    withheld = bool((unblind or holdout) and
                    results[PRIMARY]['n'] < MIN_TRADES)
    if withheld:
        for inst in results:
            x = results[inst]
            results[inst] = dict(
                n=x['n'], sessions=x['sessions'],
                with_flow=dict(n=x['with_flow']['n']),
                without_flow=dict(n=x['without_flow']['n']),
                status=('NOT ENOUGH TRADES: results withheld until a read '
                        'holds %d on each side' % MIN_TRADES
                        if inst == PRIMARY else 'withheld'))
    elif not (unblind or holdout):
        for x in results.values():
            x['status'] += ' (DEV, seen before the registration)'
    rep = dict(wave16a=W16A_VERSION, registration=REGISTRATION,
               part='16A-R recordings', evaluated_on=which,
               unblind=unblind, holdout=holdout, withheld=withheld,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({x[0]['session']
                                          for x in minute + l2}),
               results=results)
    return rep, r


# ---------------------------------------------------------------------
# reports and the command line
# ---------------------------------------------------------------------
def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text_history(rep):
    x = rep['test']
    lines = ['%s  %s  history, %s (%s)' % (rep['wave16a'], rep['mode'],
                                           rep['years'], rep['part']),
             'sessions %d (%s .. %s); stamp check %s' % (
                 rep['sessions'], rep['first_session'], rep['last_session'],
                 rep['stamp_check'].get('open_minute')),
             'rule: a bar 2 ticks through one of the six levels, closed back '
             'within 5 bars; first signal per level per session; 25 / 15 / '
             '30 min; one at a time; net after costs',
             '',
             'TEST  trades %d over %s months' % (x['n'], x.get('clusters',
                                                              0))]
    if x['n']:
        ci = x.get('ci95')
        lines.append('   won %.0f%%, net %s a trade, total %s points' % (
            100 * x['won'], _pts(x['net_points']), _pts(x['total_points'])))
        lines.append('   95%% range of net a trade: %s   p %s' % (
            '-' if not ci else '%s .. %s' % (_pts(ci[0]), _pts(ci[1])),
            '-' if x.get('p') is None else '%.4f' % x['p']))
        wb = x['without_best']
        lines.append('   without the best month (%s): net %s a trade' % (
            wb['cluster'], _pts(wb['net_points'])))
    lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
        x['reasons'])) if x.get('reasons') else ''))
    e = rep['every']
    lines.append('   beside, not tested: every signal %s trades, net %s a '
                 'trade' % (e['n'], _pts(e.get('net_points'))))
    for y, v in rep['by_year'].items():
        lines.append('   %s  %5d trades  net %s a trade' % (
            y, v['n'], _pts(v['net_points'])))
    lines.append('')
    lines.append('Minute bars, costs charged; not P&L. No order was placed.')
    return '\n'.join(lines)


def text_recordings(rep):
    lines = ['%s  %s  (%s)' % (rep['wave16a'], rep['evaluated_on'],
                               rep['part']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'with order flow = wave fourteen\'s first L2 signals; without = '
             'the same levels on minute bars; both 25 / 15 / 30 min, one at '
             'a time, net after costs']
    for inst, x in sorted(rep['results'].items(),
                          key=lambda kv: kv[0] != PRIMARY):
        lines.append('')
        lines.append('%s  ORDER FLOW ADDS?%s' % (
            inst, ' (tested)' if inst == PRIMARY else ''))
        lines.append('   trades: with flow %d, without %d' % (
            x['with_flow']['n'], x['without_flow']['n']))
        if rep['withheld']:
            lines.append('   %s' % x['status'])
            continue
        for k, name in (('with_flow', 'with order flow'),
                        ('without_flow', 'without (minute bars)')):
            v = x[k]
            lines.append('   %-22s %s, net %s a trade' % (
                name, '-' if not v['n'] else 'won %.0f%%' % (100 * v['hit']),
                _pts(v['net_points'])))
        d = x['diff']
        ci = d.get('ci95')
        lines.append('   difference %s a trade, 95%% range %s' % (
            _pts(d.get('diff')), '-' if not ci else '%s .. %s' % (
                _pts(ci[0]), _pts(ci[1]))))
        lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
            x['reasons'])) if x.get('reasons') else ''))
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
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    here = os.path.dirname(os.path.abspath(__file__))
    if '--history' in argv:
        stz = (arg('--stamps-tz') or 'UTC').upper()
        stp = (arg('--stamps') or 'end').lower()
        if unblind:
            print('*** UNBLIND: part 16A on the sessions before %s, once. '
                  '***\n' % CX.VALIDATION_BEFORE)
        try:
            rep = run_history(arg('--history'), unblind, stz, stp)
        except CX.ContextDataError as exc:
            print('STOPPED: %s' % exc)
            return 2
        print(text_history(rep))
        if out:
            json.dump(rep, open(out, 'w'), indent=1, default=str)
            print('\npart-16A history report -> %s' % out)
        if unblind:
            n = LG.record_history_read(rep, os.path.join(here,
                                                         HISTORY_LEDGER),
                                       W16A_VERSION)
            print('history read recorded (%d read(s))' % n)
        return 0
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    if unblind or holdout:
        print('*** %s: this read is part 16A\'s registered test. ***\n'
              % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run_recordings(argv[0], unblind, holdout, ms)
        print(text_recordings(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\npart-16A report -> %s' % out)
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W16A_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W16A_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
