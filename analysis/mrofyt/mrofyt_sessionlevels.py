#!/usr/bin/env python3
"""mrofyt_sessionlevels.py - MROF-YT-W21-SESSIONLEVELS-1.0

MROF_YT_WAVE21_SESSIONLEVELS_REGISTRATION.md turned into running code:
three level kinds of the Traders Reality indicator, each judged alone.

    PSYC    the weekly Psy high and low, Monday 00:00-08:00 GMT
    PSYH    the same from the 4-hour candles: Sunday 22:00 - Monday
            06:00 ET (mrofyt_psycheck.py says which is the chart's)
    ASIA    the Tokyo session (00:00-06:00 GMT) high and low
    LONDON  the London high and low, 08:00 London time to 09:30 ET
    ADR     the session's low so far plus the average daily range, and
            its high so far minus it

The first L2-style (WICK) signal at each level per session; target 25
points, stop 15, 30 minutes, one position at a time per group, net of
costs. NQ: PASS needs 30+ trades, Holm over the five groups, the 95 %
interval above 0 and a profit without the best day. A held-out read
shows only the count for a group under 30 trades.

    python3 mrofyt_sessionlevels.py "<capture>" --out w21.json            # DEV: describes
    python3 mrofyt_sessionlevels.py "<capture>" --unblind --out w21_eval.json

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import datetime as _dt
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_earlylevels as E
import mrofyt_l2firstsignal as FS
import mrofyt_l2variants as V
import mrofyt_levelbreak as LB
import mrofyt_ledgers as LG
import mrofyt_obviouslevels as OL
import mrofyt_pilot as PI
import mrofyt_profilelevels as PL
import mrofyt_runner as RUN

W21_VERSION = 'MROF-YT-W21-SESSIONLEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE21_SESSIONLEVELS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = LB.HOLDOUT_BEFORE
HOLDOUT_LEDGER = LB.HOLDOUT_LEDGER
EXPOSURE_LEDGER = V.EXPOSURE_LEDGER

DAY = 86400.0
TOKYO_LEN = 6 * 3600.0                # 00:00-06:00 GMT
PSY_LEN = 8 * 3600.0                  # 8 hours
PSYH_FROM = 22 * 3600.0               # Sunday 22:00 ET
LONDON_FROM = 8 * 3600.0              # 08:00 London time
NY_OPEN = 9.5 * 3600.0                # 09:30 ET
NO_WINDOW_FROM = 14.5 * 3600.0        # GMT: no window holds a later trade
EDGE_S = 120.0
GAP_S = 600.0

GROUPS = ('PSYC', 'PSYH', 'ASIA', 'LONDON', 'ADR')
GROUP_NAMES = collections.OrderedDict([
    ('PSYC', 'PSYC: the Psy high and low, Monday 00:00-08:00 GMT'),
    ('PSYH', 'PSYH: the Psy high and low, Sunday 22:00 - Monday 06:00 ET'),
    ('ASIA', 'ASIA: the Tokyo session high and low'),
    ('LONDON', 'LONDON: the London high and low up to 09:30 ET'),
    ('ADR', 'ADR: the session low plus, and high minus, the average range')])
# window kind -> (group, (high id, low id), days it lasts past its session)
SPEC = dict(TOKYO=('ASIA', ('TOKYO_HIGH', 'TOKYO_LOW'), 0),
            LONDON=('LONDON', ('LONDON_HIGH', 'LONDON_LOW'), 0),
            PSYC=('PSYC', ('PSYC_HI', 'PSYC_LO'), 4),
            PSYH=('PSYH', ('PSYH_HI', 'PSYH_LO'), 4))
MIN_TRADES = FS.MIN_TRADES
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT
_IH = E.FIXED_IDS.index('YDAY_HIGH')
_IL = E.FIXED_IDS.index('YDAY_LOW')
_SLOT = {'YDAY_HIGH': 'ADR_HIGH', 'YDAY_LOW': 'ADR_LOW'}
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


# ---------------------------------------------------------------------
# clocks
# ---------------------------------------------------------------------
def _uk_summer(year):
    """(start, end) epochs of British Summer Time: the last Sundays of
    March and October, 01:00 GMT."""
    def last_sunday(month):
        d = _dt.date(year, month, 31)
        d -= _dt.timedelta(days=(d.weekday() + 1) % 7)
        return (_dt.datetime(d.year, d.month, d.day, 1,
                             tzinfo=_dt.timezone.utc) - _EPOCH
                ).total_seconds()
    return last_sunday(3), last_sunday(10)


_UK = {}


def uk_offset(t):
    """Seconds to ADD to GMT for London time, looked up once per hour."""
    k = int(t // 3600)
    v = _UK.get(k)
    if v is None:
        a, b = _uk_summer(_dt.datetime.fromtimestamp(
            t, _dt.timezone.utc).year)
        v = _UK[k] = 3600.0 if a <= t < b else 0.0
    return v


def windows_at(t):
    """[(kind, start, end)] of the registered windows a trade at t is in."""
    day = math.floor(t / DAY)
    sod = t - day * DAY                              # GMT second of day
    if sod >= NO_WINDOW_FROM:
        return ()
    out = []
    if sod < TOKYO_LEN:
        out.append(('TOKYO', day * DAY, day * DAY + TOKYO_LEN))
    if sod < PSY_LEN and (day + 3) % 7 == 0:         # a Monday in GMT
        out.append(('PSYC', day * DAY, day * DAY + PSY_LEN))
    loc = t + E.et_offset_hourly(t)
    lday = math.floor(loc / DAY)
    lsod = loc - lday * DAY                          # New York second of day
    wd = (lday + 3) % 7                              # Monday 0 .. Sunday 6
    x = None
    if wd == 6 and lsod >= PSYH_FROM:
        x = lsod - PSYH_FROM
    elif wd == 0 and lsod < PSYH_FROM + PSY_LEN - DAY:
        x = lsod + DAY - PSYH_FROM
    if x is not None:
        out.append(('PSYH', t - x, t - x + PSY_LEN))
    if lsod < NY_OPEN:
        lon = t + uk_offset(t)
        lon_sod = lon - math.floor(lon / DAY) * DAY
        if lon_sod >= LONDON_FROM:
            out.append(('LONDON', t - (lon_sod - LONDON_FROM),
                        t + (NY_OPEN - lsod)))
    return out


def session_close(t):
    """The 17:00 ET that ends the CME session holding t."""
    off = RUN.et_offset(t)
    loc = t + off
    c = math.floor(loc / DAY) * DAY + 17 * 3600.0
    if loc >= c + 3600.0:
        c += DAY
    return c - off


# ---------------------------------------------------------------------
# the runner: wave twenty's, plus the registered windows' trade extremes
# ---------------------------------------------------------------------
class SessionLevelsRunner(PL.ProfileLevelsRunner):
    """Wave twenty's runner. The trades it hands to its profiles also
    update the high, low, first and last trade and longest gap of every
    registered window they fall in. Hooks only: nothing an earlier wave
    reads is touched."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        PL.ProfileLevelsRunner.__init__(self, capture_dir, unblind=unblind,
                                        holdout=holdout, **kw)
        # (inst, kind, session) -> [high, low, first, last, gap, start, end]
        self.win = {}
        self.ledger['wave21'] = dict(version=W21_VERSION)

    def _add_trade(self, inst, session, t, px, sz):
        PL.ProfileLevelsRunner._add_trade(self, inst, session, t, px, sz)
        if px is None or not sz or not session:
            return
        for kind, start, end in windows_at(t):
            key = (inst, kind, session)
            w = self.win.get(key)
            if w is None:
                self.win[key] = [px, px, t, t, 0.0, start, end]
                continue
            if px > w[0]:
                w[0] = px
            if px < w[1]:
                w[1] = px
            if t < w[2]:
                w[2] = t
            if t > w[3]:
                if t - w[3] > w[4]:
                    w[4] = t - w[3]
                w[3] = t

    def _mark_run(self, st):
        mark = PL.ProfileLevelsRunner._mark_run(self, st)
        keys = [(st.instrument, kind, st.session) for kind in SPEC]
        mark['w21'] = dict((k, list(self.win[k])) for k in keys
                           if k in self.win)
        return mark

    def _unwind_run(self, st, mark):
        PL.ProfileLevelsRunner._unwind_run(self, st, mark)
        for kind in SPEC:
            self.win.pop((st.instrument, kind, st.session), None)
        self.win.update((k, list(v)) for k, v in mark['w21'].items())


# ---------------------------------------------------------------------
# registration 1: the levels
# ---------------------------------------------------------------------
def complete(w):
    """Registration 1.2: the window's first and last trade within 120 s
    of its edges and no 10-minute hole."""
    return w[2] - w[5] <= EDGE_S and w[6] - w[3] <= EDGE_S and w[4] <= GAP_S


def window_levels(r):
    """{instrument: [level dicts with ses_idx]}: the Psy, Tokyo and
    London highs and lows of every complete window."""
    grid_of = PL.grid_by_instrument(r)
    out = {}
    for inst in sorted(grid_of):
        ses_list = sorted({g['session'] for g in grid_of[inst]})
        lv = []
        for (i, kind, ses), w in sorted(r.win.items()):
            if i != inst or not complete(w):
                continue
            group, ids, days = SPEC[kind]
            t_on = w[6]
            t_off = session_close(t_on) + days * DAY
            for name, px in zip(ids, (w[0], w[1])):
                lv.append(dict(id='%s@%s' % (name, ses), kind=name,
                               group=group, price=px, t_on=t_on, t_off=t_off,
                               session=ses,
                               ses_idx=bisect.bisect_left(ses_list, ses)))
        out[inst] = lv
    return out


def adr_grid(r, inst, grid):
    """({run: [grid records carrying the two ADR lines]}, sessions that
    have them). ADR_HIGH = the session's lowest mid so far + A and
    ADR_LOW = its highest so far - A, A wave nine's recent range; the
    lines sit in wave eleven's YDAY_HIGH / YDAY_LOW slots of each record,
    read there by its run_episodes as it reads VWAP."""
    by_ses = collections.defaultdict(list)
    for g in grid:
        by_ses[g['session']].append(g)
    paths = V.compressed_paths(r)
    out, have = collections.defaultdict(list), []
    for ses, recs in sorted(by_ses.items()):
        a = r.recent_range(inst, ses)
        if a is None:
            continue
        have.append(ses)
        lo = hi = None
        # every run of the session, each read once up to the record's time
        pos = dict.fromkeys(sorted({g['run'] for g in recs}), 0)
        for g in sorted(recs, key=lambda g: g['t']):
            mid = g.get('mid')
            seen = [] if mid is None else [mid]
            for rn in pos:
                ts, ps = paths.get((inst, rn), ((), ()))
                j = pos[rn]
                k = bisect.bisect_right(ts, g['t'], j)
                if k > j:
                    seen.append(min(ps[j:k]))
                    seen.append(max(ps[j:k]))
                    pos[rn] = k
            if seen:
                a_lo, a_hi = min(seen), max(seen)
                lo = a_lo if lo is None or a_lo < lo else lo
                hi = a_hi if hi is None or a_hi > hi else hi
            if lo is None:
                continue
            slots = [None] * len(E.FIXED_IDS)
            slots[_IH], slots[_IL] = lo + a, hi - a
            out[g['run']].append(dict(
                t=g['t'], mid=mid, D=g.get('D'),
                z_delta_s=g.get('z_delta_s'), instrument=inst, session=ses,
                run=g['run'], w11_lv=tuple(slots)))
    return out, have


def adr_events(r):
    """(wave eleven's WICK entries at the two ADR lines, {instrument:
    sessions that had the lines})."""
    counts = collections.Counter()
    out, sessions = [], {}
    for inst, grid in sorted(PL.grid_by_instrument(r).items()):
        runs, sessions[inst] = adr_grid(r, inst, grid)
        ses_index = {s: i for i, s in
                     enumerate(sorted({g['session'] for g in grid}))}
        for run in sorted(runs, key=lambda k: runs[k][0]['t']):
            for e in E.run_episodes(runs[run], {}, [], ses_index, counts,
                                    'WICK'):
                name = _SLOT[e['level_id']]
                e.update(level_id='%s@%s' % (name, e['session']), kind=name,
                         group='ADR')
                out.append(e)
    return out, sessions


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
def run(capture_dir, unblind=False, holdout=False, max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = SessionLevelsRunner(capture_dir, unblind=unblind, holdout=holdout,
                            max_sessions=max_sessions)
    led = r.run()
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE       # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END              # noqa: E731
        which = 'validation (> %s): secondary tests' % DEV_END
    else:
        keep = lambda s: s <= DEV_END             # noqa: E731
        which = 'DEV (<= %s): describes, not a test' % DEV_END
    levels = window_levels(r)
    adr, adr_ses = adr_events(r)
    ev = [e for e in OL.wick_events(r, levels) + adr if keep(e['session'])]
    first_ids = {id(e) for e in OL.first_signals(ev)}
    scored = OL.score(r, ev)
    insts = sorted(set(r.instruments) | {PRIMARY})
    groups = {g: {} for g in GROUPS}
    for inst in insts:
        for g in GROUPS:
            mine = lambda firsts: V.one_at_a_time(   # noqa: E731
                [x for x in scored if x[0]['instrument'] == inst and
                 x[0]['group'] == g and (not firsts or id(x[0]) in first_ids)])
            ver = FS.verdict(mine(True), inst)
            ver.update(test=g, name=GROUP_NAMES[g])
            b = LB.test_stats(mine(False), inst)
            groups[g][inst] = dict(test=ver, every=dict(
                n=b['n'], sessions=b.get('sessions', 0), hit=b.get('hit'),
                net_points=b.get('net_points')))
    PL.apply_holm([groups[g][PRIMARY]['test'] for g in GROUPS],
                  'five level groups')
    withheld = []
    for g in GROUPS:
        rows = groups[g]
        if (unblind or holdout) and rows[PRIMARY]['test']['n'] < MIN_TRADES:
            withheld.append(g)
            for inst in rows:
                x = PL._withhold(rows[inst]['test'])
                x['status'] = (
                    'NOT ENOUGH TRADES: results withheld until a read holds '
                    '%d' % MIN_TRADES if inst == PRIMARY else 'withheld')
                rows[inst] = dict(test=x)
        elif not (unblind or holdout):
            for inst in rows:
                rows[inst]['test']['status'] += ' (DEV: describes, not a test)'
    built = {}
    for inst, lv in levels.items():
        c = collections.Counter(x['group'] for x in lv if keep(x['session']))
        c['ADR'] = 2 * sum(1 for s in adr_ses.get(inst, ()) if keep(s))
        built[inst] = dict((g, c.get(g, 0)) for g in GROUPS)
    rep = dict(wave21=W21_VERSION, registration=REGISTRATION,
               evaluated_on=which, unblind=unblind, holdout=holdout,
               withheld=withheld, min_trades=MIN_TRADES,
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in ev}),
               levels=built, results=dict(levels=groups))
    return rep, r


def _pts(x):
    return '-' if x is None else '%+.2f' % x


def text(rep):
    lines = ['%s  %s' % (rep['wave21'], rep['evaluated_on']),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-'),
             'levels built: %s' % ('; '.join(
                 '%s %s' % (inst, ', '.join('%s %d' % (g, c.get(g, 0))
                                            for g in GROUPS))
                 for inst, c in sorted(rep['levels'].items())) or '-'),
             'rule: the first 10 s L2-style signal (WICK) at each level per '
             'session; target 25 pts, stop 15 pts, 30 min; one trade at a '
             'time per group; net after costs']
    for g in GROUPS:
        for inst, res in sorted(rep['results']['levels'][g].items(),
                                key=lambda kv: kv[0] != PRIMARY):
            x = res['test']
            lines.append('')
            lines.append('%s  %s%s' % (inst, GROUP_NAMES[g], ' (tested)'
                                       if inst == PRIMARY else ''))
            lines.append('   trades %d over %d days' % (
                x['n'], x.get('sessions', 0)))
            if g in rep['withheld']:
                lines.append('   %s' % x['status'])
                continue
            if x['n']:
                ci = x.get('ci95_net_ticks')
                lines.append('   won %.0f%%, net %s a trade, total %s points'
                             % (100 * x['hit'], _pts(x['net_points']),
                                _pts(x.get('total_net_points'))))
                lines.append('   95%% range of net a trade: %s   p %s' % (
                    '-' if not ci else '%s .. %s points' % (
                        _pts(ci[0] / 4.0), _pts(ci[1] / 4.0)),
                    '-' if x.get('p') is None else '%.4f' % x['p']))
                wb = x['without_best_day']
                lines.append('   without the best day (%s): %d trades, net '
                             '%s a trade' % (wb['session'], wb['n'],
                                             _pts(wb['net_points'])))
            lines.append('   VERDICT: %s%s' % (x['status'], (': ' + '; '.join(
                x['reasons'])) if x.get('reasons') else ''))
            b = res['every']
            lines.append('   beside, not tested: every signal %d trades, %s, '
                         'net %s a trade' % (
                             b['n'], '-' if not b['n'] else
                             'won %.0f%%' % (100 * b['hit']),
                             _pts(b['net_points'])))
    lines.append('')
    lines.append('Of PSYC and PSYH, mrofyt_psycheck.py says which is the '
                 'chart\'s Psy line.')
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
        print('*** %s: this read is wave twenty-one\'s registered tests. '
              '***\n' % ('UNBLIND' if unblind else 'HOLDOUT'))
    try:
        rep, _r = run(argv[0], unblind, holdout, ms)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        with open(out, 'w') as fh:
            json.dump(rep, fh, indent=1, default=str)
        print('\nwave-twenty-one report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if holdout:
        n = LG.record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER),
                                   W21_VERSION)
        print('replay holdout read recorded (%d read(s))' % n)
    if unblind:
        n = LG.record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER),
                               W21_VERSION)
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
