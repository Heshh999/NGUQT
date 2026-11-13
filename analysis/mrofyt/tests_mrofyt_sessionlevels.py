#!/usr/bin/env python3
# MROF-YT-W21-SESSIONLEVELS-1.0 suite. The window clocks, the runner's
# trade windows, their completeness, the Psy, Tokyo and London levels,
# the two ADR lines, the signals at them and the verdicts are exercised
# on hand-built trades, grids and paths with known answers, and the
# pipeline end to end on synthetic recorder-format runs (mles_v12_synth),
# each session a Tokyo-hours run, a London-hours run and a cash run.
# Synthetic runs last under an hour, so the end-to-end checks relax,
# INSIDE THIS SUITE ONLY, the two completeness limits; both are restored
# afterwards. Synthetic events verify CODE BEHAVIOR only, never market
# evidence. No order, fill or P&L exists.
import calendar
import collections
import csv
import gc
import io
import json
import math
import os
import shutil
import sys
import tempfile
import types
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_adapter as AD        # noqa: E402
import mles_v12_audit as AU          # noqa: E402
import mles_v12_synth as SY          # noqa: E402
import mrofyt_earlylevels as E       # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_obviouslevels as OL    # noqa: E402
import mrofyt_profilelevels as PL    # noqa: E402
import mrofyt_psycheck as PC         # noqa: E402
import mrofyt_sessionlevels as SL    # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w21_')
H = 3600.0
D1 = 86400.0
NS = types.SimpleNamespace


def ep(*a):
    return float(calendar.timegm(a + (0,) * (6 - len(a))))


def wins(x):
    return dict((k, (a, b)) for k, a, b in SL.windows_at(x))


# ---------------------------------------------------------------------
# SL1: the clocks
# ---------------------------------------------------------------------
M = ep(2026, 9, 7)                   # Monday 00:00 GMT = Sunday 20:00 EDT
O = ep(2026, 10, 26)                 # Monday: London on GMT, New York on EDT
N = ep(2026, 11, 9)                  # Monday: GMT and EST
t('SL1: a trade falls in the Tokyo window 00:00-05:59:59 GMT every day; '
  'on a Monday also in the clock Psy window 00:00-07:59:59 GMT and the '
  '4-hour-candle one, Sunday 22:00 - Monday 05:59:59 New York; in the '
  'London window from 08:00 London time to 09:29:59 New York, in summer, '
  'in the week London is back on GMT before New York, and in winter; '
  'London time changes on the last Sundays of March and October at 01:00 '
  'GMT; a session closes at 17:00 New York',
  wins(M + 0.5 * H) == dict(TOKYO=(M, M + 6 * H), PSYC=(M, M + 8 * H)) and
  wins(M + 2 * H - 1) == dict(TOKYO=(M, M + 6 * H), PSYC=(M, M + 8 * H)) and
  wins(M + 2 * H) == dict(TOKYO=(M, M + 6 * H), PSYC=(M, M + 8 * H),
                          PSYH=(M + 2 * H, M + 10 * H)) and
  wins(M + 6 * H) == dict(PSYC=(M, M + 8 * H),
                          PSYH=(M + 2 * H, M + 10 * H)) and
  wins(M + 7 * H - 1) == wins(M + 6 * H) and
  wins(M + 7 * H) == dict(PSYC=(M, M + 8 * H), PSYH=(M + 2 * H, M + 10 * H),
                          LONDON=(M + 7 * H, M + 13.5 * H)) and
  wins(M + 8 * H) == dict(PSYH=(M + 2 * H, M + 10 * H),
                          LONDON=(M + 7 * H, M + 13.5 * H)) and
  wins(M + 10 * H) == dict(LONDON=(M + 7 * H, M + 13.5 * H)) and
  wins(M + 13.5 * H - 1) == dict(LONDON=(M + 7 * H, M + 13.5 * H)) and
  wins(M + 13.5 * H) == {} and wins(M + 22.5 * H) == {} and
  wins(M + D1 + 0.5 * H) == dict(TOKYO=(M + D1, M + D1 + 6 * H)) and
  wins(M + D1 + 3 * H) == dict(TOKYO=(M + D1, M + D1 + 6 * H)) and
  wins(M + D1 + 7 * H) == dict(LONDON=(M + D1 + 7 * H, M + D1 + 13.5 * H))
  and wins(O + 8 * H - 1) == dict(PSYC=(O, O + 8 * H),
                                  PSYH=(O + 2 * H, O + 10 * H)) and
  wins(O + 8 * H) == dict(PSYH=(O + 2 * H, O + 10 * H),
                          LONDON=(O + 8 * H, O + 13.5 * H)) and
  wins(N + 3 * H - 1) == dict(TOKYO=(N, N + 6 * H), PSYC=(N, N + 8 * H)) and
  wins(N + 3 * H) == dict(TOKYO=(N, N + 6 * H), PSYC=(N, N + 8 * H),
                          PSYH=(N + 3 * H, N + 11 * H)) and
  wins(N + 11 * H - 1) == dict(PSYH=(N + 3 * H, N + 11 * H),
                               LONDON=(N + 8 * H, N + 14.5 * H)) and
  wins(N + 14.5 * H - 1) == dict(LONDON=(N + 8 * H, N + 14.5 * H)) and
  wins(N + 14.5 * H) == {} and
  [SL.uk_offset(x) for x in (ep(2026, 3, 29, 0, 59, 59), ep(2026, 3, 29, 1),
                             ep(2026, 10, 25, 0, 59, 59),
                             ep(2026, 10, 25, 1), ep(2027, 3, 28, 1))] ==
  [0.0, 3600.0, 3600.0, 0.0, 3600.0] and
  SL.session_close(M + 7 * H) == M + 21 * H and
  SL.session_close(M + 22.5 * H) == M + D1 + 21 * H and
  SL.session_close(N + 8 * H) == N + 22 * H)

# ---------------------------------------------------------------------
# SL2: the runner's hooks by hand
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
rr = SL.SessionLevelsRunner(EMPTY)
ref = PL.ProfileLevelsRunner(EMPTY)
for dt, px, sz in ((30.0, 100.0, 1),                 # Tokyo, clock Psy
                   (2 * H + 60, 104.0, 2),           # + candle Psy
                   (6 * H - 10, 98.0, 1),            # Tokyo's last
                   (6 * H, 97.0, 1),                 # both Psy only
                   (6.5 * H, 150.0, 0),              # no size: nothing
                   (6.5 * H, None, 4),               # no price: nothing
                   (7 * H + 10, 105.0, 3),           # both Psy, London
                   (8 * H, 106.0, 1),                # candle Psy, London
                   (10 * H, 96.0, 1),                # London only
                   (13.5 * H - 1, 99.0, 1),          # 09:29:59: London
                   (13.5 * H, 120.0, 9),             # 09:30: none
                   (20 * H, 80.0, 9)):               # 16:00: none
    rr._add_trade('NQ', '20260907', M + dt, px, sz)
    ref._add_trade('NQ', '20260907', M + dt, px, sz)
rr._add_trade('NQ', '', M + H, 500.0, 1)             # no session: nothing
rr._add_trade('NQ', '20260908', M + D1 + H, 101.0, 1)
rr._add_trade('MNQ', '20260908', M + D1 + 7.5 * H, 102.0, 1)
t('SL2: the trades wave twenty\'s profiles are handed also update the '
  'high, low, first and last trade and longest gap of every window they '
  'fall in, per instrument and CME session; a trade outside every window, '
  'without size, price or session changes nothing; a Tuesday has no Psy '
  'window; wave twenty\'s own profiles are unchanged',
  rr.win == {
      ('NQ', 'TOKYO', '20260907'): [104.0, 98.0, M + 30, M + 6 * H - 10,
                                    4 * H - 70, M, M + 6 * H],
      ('NQ', 'PSYC', '20260907'): [105.0, 97.0, M + 30, M + 7 * H + 10,
                                   4 * H - 70, M, M + 8 * H],
      ('NQ', 'PSYH', '20260907'): [106.0, 97.0, M + 2 * H + 60, M + 8 * H,
                                   4 * H - 70, M + 2 * H, M + 10 * H],
      ('NQ', 'LONDON', '20260907'): [106.0, 96.0, M + 7 * H + 10,
                                     M + 13.5 * H - 1, 3.5 * H - 1,
                                     M + 7 * H, M + 13.5 * H],
      ('NQ', 'TOKYO', '20260908'): [101.0, 101.0, M + D1 + H, M + D1 + H,
                                    0.0, M + D1, M + D1 + 6 * H],
      ('MNQ', 'LONDON', '20260908'): [102.0, 102.0, M + D1 + 7.5 * H,
                                      M + D1 + 7.5 * H, 0.0, M + D1 + 7 * H,
                                      M + D1 + 13.5 * H]} and
  dict((k, [dict(v[0])] + v[1:]) for k, v in rr.on_prof.items() if
       k == ('NQ', '20260907')) ==
  dict((k, [dict(v[0])] + v[1:]) for k, v in ref.on_prof.items()) and
  rr.cash_last[('NQ', '20260907')] == ref.cash_last[('NQ', '20260907')] and
  rr.ledger['wave21']['version'] == SL.W21_VERSION and
  rr.ledger['wave20'] == ref.ledger['wave20'])


# ---------------------------------------------------------------------
# SL3: completeness and the levels
# ---------------------------------------------------------------------
def w(hi, lo, start, end, first=0.0, last=0.0, gap=0.0):
    return [hi, lo, start + first, end - last, gap, start, end]


T8 = M + D1
r3 = NS(grid=[dict(instrument='NQ', session=s) for s in
              ('20260904', '20260907', '20260908', '20261109')] +
        [dict(instrument='MNQ', session='20260908')],
        win={('NQ', 'PSYC', '20260907'): w(110.0, 90.0, M, M + 8 * H,
                                           120.0, 120.0, 600.0),
             ('NQ', 'PSYH', '20260907'): w(111.0, 91.0, M + 2 * H,
                                           M + 10 * H),
             ('NQ', 'TOKYO', '20260907'): w(105.0, 95.0, M, M + 6 * H,
                                            first=121.0),
             ('NQ', 'LONDON', '20260907'): w(108.0, 92.0, M + 7 * H,
                                             M + 13.5 * H, last=121.0),
             ('NQ', 'TOKYO', '20260908'): w(105.0, 95.0, T8, T8 + 6 * H,
                                            gap=601.0),
             ('NQ', 'LONDON', '20260908'): w(107.0, 93.0, T8 + 7 * H,
                                             T8 + 13.5 * H),
             ('NQ', 'PSYC', '20261109'): w(210.0, 190.0, N, N + 8 * H),
             ('MNQ', 'TOKYO', '20260908'): w(106.0, 94.0, T8, T8 + 6 * H)})
lv3 = SL.window_levels(r3)
FRI = ep(2026, 9, 11, 21)                            # Friday 17:00 EDT
t('SL3: a window gives its high and low only with its first trade within '
  '120 s of its start, its last within 120 s of its end and no gap over '
  '600 s; a Tokyo level is known from 06:00 GMT and a London level from '
  '09:30 New York, both to 17:00 New York that session; a Psy level from '
  'its window\'s end to Friday 17:00 New York, in summer and in winter',
  [(x['id'], x['kind'], x['group'], x['price'], x['t_on'], x['t_off'],
    x['session'], x['ses_idx']) for x in lv3['NQ']] == [
      ('LONDON_HIGH@20260908', 'LONDON_HIGH', 'LONDON', 107.0,
       T8 + 13.5 * H, T8 + 21 * H, '20260908', 2),
      ('LONDON_LOW@20260908', 'LONDON_LOW', 'LONDON', 93.0,
       T8 + 13.5 * H, T8 + 21 * H, '20260908', 2),
      ('PSYC_HI@20260907', 'PSYC_HI', 'PSYC', 110.0, M + 8 * H, FRI,
       '20260907', 1),
      ('PSYC_LO@20260907', 'PSYC_LO', 'PSYC', 90.0, M + 8 * H, FRI,
       '20260907', 1),
      ('PSYC_HI@20261109', 'PSYC_HI', 'PSYC', 210.0, N + 8 * H,
       ep(2026, 11, 13, 22), '20261109', 3),
      ('PSYC_LO@20261109', 'PSYC_LO', 'PSYC', 190.0, N + 8 * H,
       ep(2026, 11, 13, 22), '20261109', 3),
      ('PSYH_HI@20260907', 'PSYH_HI', 'PSYH', 111.0, M + 10 * H, FRI,
       '20260907', 1),
      ('PSYH_LO@20260907', 'PSYH_LO', 'PSYH', 91.0, M + 10 * H, FRI,
       '20260907', 1)] and
  [(x['id'], x['t_on'], x['t_off'], x['ses_idx']) for x in lv3['MNQ']] == [
      ('TOKYO_HIGH@20260908', T8 + 6 * H, T8 + 21 * H, 0),
      ('TOKYO_LOW@20260908', T8 + 6 * H, T8 + 21 * H, 0)] and
  SL.complete(w(1, 1, 0, 100, 120.0, 120.0, 600.0)) and
  not SL.complete(w(1, 1, 0, 100, gap=600.5)))


# ---------------------------------------------------------------------
# SL4: a Psy level is traded all week, once a session
# ---------------------------------------------------------------------
def recs(ses, run, t0, rows, inst='NQ'):
    """10 s grid records from (mid, D, z_delta_s) rows."""
    return [dict(instrument=inst, session=ses, run=run, t=t0 + 10.0 * i,
                 mid=m, D=d, z_delta_s=z) for i, (m, d, z) in enumerate(rows)]


UP = [(105.0, 0, 0.0), (111.0, 0, 0.0), (109.0, -5, 2.0)]   # break, reclaim
r4 = NS(win={('NQ', 'PSYC', '20260907'): w(110.0, 90.0, M, M + 8 * H)},
        grid=recs('20260907', 'm', M + 7 * H, UP) +            # still forming
        recs('20260909', 'w', M + 2 * D1 + 14 * H, UP + UP[1:]) +
        recs('20260911', 'f', FRI - 30.0, UP + UP[1:]) +       # 16:59:30 Fri
        recs('20260914', 'n', M + 7 * D1 + 14 * H, UP))        # next Monday
ev4 = OL.wick_events(r4, SL.window_levels(r4))
t('SL4: a Psy level gives no signal while its window is still open, then '
  'signals on every later session up to Friday 17:00 New York and none '
  'the week after; the first signal at a level per session is the one '
  'taken; the trade fades the break',
  [(e['session'], e['t'], e['level_id'], e['group'], e['direction'],
    e['level']) for e in ev4] == [
      ('20260909', M + 2 * D1 + 14 * H + 20, 'PSYC_HI@20260907', 'PSYC', -1,
       110.0),
      ('20260909', M + 2 * D1 + 14 * H + 40, 'PSYC_HI@20260907', 'PSYC', -1,
       110.0),
      ('20260911', FRI - 10.0, 'PSYC_HI@20260907', 'PSYC', -1, 110.0)] and
  [e['t'] for e in OL.first_signals(ev4)] == [M + 2 * D1 + 14 * H + 20,
                                              FRI - 10.0])

# ---------------------------------------------------------------------
# SL5: the two ADR lines on each grid record
# ---------------------------------------------------------------------
TA = M + D1 + 14 * H                                  # Tuesday 10:00 EDT
TB = TA + 600.0
r5 = NS(
    grid=recs('20260908', 'a', TA + 10, [(100.0, 0, 0.0), (104.0, 0, 0.0),
                                         (103.0, 0, 0.0)]) +
    recs('20260908', 'b', TB + 10, [(97.0, 0, 0.0), (None, 0, 0.0)]) +
    recs('20260909', 'c', TA + D1, [(100.0, 0, 0.0)]) +
    recs('20260908', 'x', TA + 10, [(50.0, 0, 0.0)], inst='MNQ'),
    series={('NQ', 'a'): ([TA, TA + 5, TA + 10, TA + 14, TA + 20, TA + 30,
                           TA + 35],
                          [101.0, 99.5, 100.0, 106.0, 104.0, 103.0, 95.0]),
            ('NQ', 'b'): ([TB, TB + 10, TB + 20], [98.0, 97.0, 96.0]),
            ('NQ', 'c'): ([TA + D1], [100.0]),
            ('MNQ', 'x'): ([TA + 10], [50.0])},
    recent_range=lambda inst, ses: {('NQ', '20260908'): 40.0}.get(
        (inst, ses)))
g5, have5 = SL.adr_grid(r5, 'NQ', [g for g in r5.grid
                                   if g['instrument'] == 'NQ'])
IH, IL = E.FIXED_IDS.index('YDAY_HIGH'), E.FIXED_IDS.index('YDAY_LOW')
t('SL5: at every grid record ADR_HIGH is the session\'s lowest mid so far '
  'plus wave nine\'s recent range and ADR_LOW its highest so far minus '
  'it; a low or high made between two records counts from the next '
  'record, and one made after a run\'s last record from the session\'s '
  'next run; a session without 5 earlier sessions has no lines',
  have5 == ['20260908'] and sorted(g5) == ['a', 'b'] and
  [(g['t'] - TA, g['w11_lv'][IH], g['w11_lv'][IL]) for g in g5['a']] ==
  [(10.0, 139.5, 61.0), (20.0, 139.5, 66.0), (30.0, 139.5, 66.0)] and
  [(g['t'] - TB, g['mid'], g['w11_lv'][IH], g['w11_lv'][IL])
   for g in g5['b']] == [(10.0, 97.0, 135.0, 66.0),
                         (20.0, None, 135.0, 66.0)] and
  all(sum(1 for x in g['w11_lv'] if x is not None) == 2 and
      g['session'] == '20260908' and g['instrument'] == 'NQ'
      for run in g5.values() for g in run) and
  SL.adr_grid(r5, 'MNQ', [g for g in r5.grid
                          if g['instrument'] == 'MNQ']) == ({}, []))

# ---------------------------------------------------------------------
# SL6: signals at the moving ADR lines
# ---------------------------------------------------------------------
ROWS6 = [(100.0, 0, 0.0),     # lines 120 / 80
         (90.0, 0, 0.0),      # low 90: ADR_HIGH 110
         (111.0, 0, 0.0),     # above 110: a break; high 111: ADR_LOW 91
         (109.0, -5, 2.0),    # back under with selling: SHORT at 110
         (90.5, 0, 0.0),      # under 91: a break
         (92.0, 5, 2.0),      # back over with buying: LONG at 91
         (115.0, 0, 0.0),     # above 110 again; high 115: ADR_LOW 95
         (94.0, -5, 2.0),     # SHORT at 110; under the moved line 95
         (96.0, 5, 2.0)]      # back over 95 with buying: LONG at 95
g6 = recs('20260908', 'a', TA, ROWS6)
r6 = NS(grid=g6 + recs('20260909', 'c', TA + D1, ROWS6),
        series={('NQ', 'a'): ([g['t'] for g in g6], [g['mid'] for g in g6]),
                ('NQ', 'c'): ([g['t'] + D1 for g in g6],
                              [g['mid'] for g in g6])},
        recent_range=lambda inst, ses: 20.0 if ses == '20260908' else None)
ev6, ses6 = SL.adr_events(r6)
fixed6 = OL.wick_events(
    NS(grid=g6), {'NQ': [dict(id='X', kind='X', group='G', price=110.0,
                              t_on=TA + 10, t_off=TA + 1e6,
                              session='20260908', ses_idx=0)]})
t('SL6: the ADR lines are read on each grid record as wave eleven reads '
  'VWAP: a break of the line as it stands and a return through it with '
  'the order flow against the break; where the line does not move the '
  'signals are those of a listed level at the same price; the first per '
  'line per session is the one taken; a session without lines has none',
  [(e['t'] - TA, e['level_id'], e['kind'], e['group'], e['direction'],
    e['level'], e['session']) for e in ev6] == [
      (30.0, 'ADR_HIGH@20260908', 'ADR_HIGH', 'ADR', -1, 110.0, '20260908'),
      (50.0, 'ADR_LOW@20260908', 'ADR_LOW', 'ADR', 1, 91.0, '20260908'),
      (70.0, 'ADR_HIGH@20260908', 'ADR_HIGH', 'ADR', -1, 110.0, '20260908'),
      (80.0, 'ADR_LOW@20260908', 'ADR_LOW', 'ADR', 1, 95.0, '20260908')] and
  ses6 == {'NQ': ['20260908']} and
  [(e['t'], e['direction'], e['level'], e['test_no']) for e in ev6
   if e['kind'] == 'ADR_HIGH'] ==
  [(e['t'], e['direction'], e['level'], e['test_no']) for e in fixed6] and
  len(fixed6) == 2 and
  [e['t'] - TA for e in OL.first_signals(ev6)] == [30.0, 50.0])

# ---------------------------------------------------------------------
# SL7: Holm over the five
# ---------------------------------------------------------------------


def fam(ps):
    rows = [dict(n=40, p=p, status='PASS', reasons=[]) for p in ps] + \
        [dict(n=12, p=0.0001, status='NOT ENOUGH TRADES', reasons=['x'])]
    PL.apply_holm(rows, 'five level groups')
    return rows


f_a = fam([0.0105, 0.012, 0.3, 0.6])
f_b = fam([0.0099, 0.0124, 0.3, 0.6])
t('SL7: the five groups are judged together: a group with 30+ trades '
  'passes only if Holm over the five rejects it (p 0.0105 does not, '
  '0.0099 does and then 0.0124 does); a group under 30 trades keeps NOT '
  'ENOUGH TRADES and still counts as one of the five',
  [x['holm_rejected'] for x in f_a] == [False] * 5 and
  [x['status'] for x in f_a] == ['NOT PROVEN'] * 4 + ['NOT ENOUGH TRADES']
  and all('five level groups' in x['reasons'][-1] for x in f_a[:4]) and
  f_a[4]['reasons'] == ['x'] and
  [x['holm_rejected'] for x in f_b] == [True, True, False, False, False] and
  [x['status'] for x in f_b] == ['PASS', 'PASS', 'NOT PROVEN', 'NOT PROVEN',
                                 'NOT ENOUGH TRADES'] and
  len(SL.GROUPS) == 5 and SL.MIN_TRADES == 30)

# ---------------------------------------------------------------------
# SL8-SL10: end to end (plumbing)
# ---------------------------------------------------------------------
_FROZEN = (SL.EDGE_S, SL.GAP_S)


def _relax():
    SL.EDGE_S, SL.GAP_S = 1e9, 1e9


def _restore():
    SL.EDGE_S, SL.GAP_S = _FROZEN


def _path(b, amp):
    return lambda i: b + amp * math.sin(2 * math.pi * (i * 0.05) / 900.0)


def _epoch(ses, hh, mm):
    return float(calendar.timegm((int(ses[:4]), int(ses[4:6]), int(ses[6:]),
                                  hh, mm, 0)))


def three_runs(d, ses, i, n_small=19000, n_cash=40000, tag='', upto=3):
    """One session around 15 000: a run in Tokyo hours (20:30 New York
    the evening before), one in London hours (03:05) and a cash run
    (09:30), each wider than the one before, and wider every session."""
    out = []
    for k, (hh, mm, amp, n) in enumerate((
            (0, 30, 24 + 2 * i, n_small), (7, 5, 20 + 2 * i, n_small),
            (13, 30, 30 + 3 * i, n_cash))[:upto]):
        out.append(SY.synth_run(
            d, n_depth=n, dt_step=0.05, t0=_epoch(ses, hh, mm),
            price_path=_path(15000.0, amp), trade_every=10, quote_every=5,
            cid='%s%s%d' % (tag, 'tlc'[k], i), session=ses,
            seed=i + 40 * k))
    return out


SESSIONS = ('20260831', '20260901', '20260902', '20260903', '20260904',
            '20260907', '20260908', '20260909', '20260910', '20260921')
DEV = SESSIONS[:9]
MONDAYS = ('20260831', '20260907')
D = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    three_runs(D, ses, i)
gc.collect()     # mles_v12_synth leaves its manifests to the collector
_relax()
try:
    repD, rD = SL.run(D)
    levels = SL.window_levels(rD)
    wick = OL.wick_events(rD, levels)
    adr, adr_ses = SL.adr_events(rD)
    repU, _rU = SL.run(D, unblind=True)
    rP = PL.ProfileLevelsRunner(D)
    ledP = rP.run()
finally:
    _restore()


def plain20(r):
    return (dict((k, [dict(v[0]), v[1], v[2], v[3]])
                 for k, v in r.on_prof.items()),
            dict((i, dict(v)) for i, v in r.cash_bins.items()),
            dict((i, dict(v)) for i, v in r.cash_close.items()),
            dict(r.cash_last), dict((i, dict(v)) for i, v in
                                    r.values.items()))


_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
t('SL8: the wave-twenty-one runner leaves wave twenty\'s fires, grid, '
  'profiles, value areas and ranges and the wave-one ledger identical: '
  'hooks only',
  rD.w3_fires == rP.w3_fires and rD.grid == rP.grid and
  plain20(rD) == plain20(rP) and dict(rD.ranges) == dict(rP.ranges) and
  json.dumps({k: rD.ledger.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledP.get(k) for k in _CMP}, sort_keys=True, default=str))


def raw_trades(d, ses, inst='NQ'):
    """[(exchange epoch, price)] of a session, read from its files."""
    out = []
    for mp in AU.discover_manifests(d):
        with open(mp) as fh:
            man = json.load(fh)
        if man.get('instrument') != inst or str(man.get('session')) != ses:
            continue
        path = os.path.join(os.path.dirname(mp), man['trades']['file'])
        with open(path, newline='') as fh:
            rdr = csv.reader(fh)
            head = next(rdr)
            i_t, i_px = head.index('tExchUtc'), head.index('px')
            out += [(AD.iso_to_epoch(row[i_t].strip()), float(row[i_px]))
                    for row in rdr if len(row) == len(head)]
    return out


def hilo(trs, a, b):
    px = [p for x, p in trs if a <= x < b]
    return (max(px), min(px))


lv_nq = levels['NQ']
by_id = {x['id']: x for x in lv_nq}
ok_px = ok_time = True
for ses in DEV:
    trs, d0 = raw_trades(D, ses), _epoch(ses, 0, 0)
    want = dict(TOKYO=(d0, d0 + 6 * H), LONDON=(d0 + 7 * H, d0 + 13.5 * H))
    if ses in MONDAYS:
        want.update(PSYC=(d0, d0 + 8 * H), PSYH=(d0 + 2 * H, d0 + 10 * H))
        pc = PC.week_levels(PC.monday_runs(D)[ses], ses)[0]
        ok_px = ok_px and \
            (by_id['PSYC_HI@' + ses]['price'],
             by_id['PSYC_LO@' + ses]['price']) == \
            (pc['TR_CLOCK']['hi'], pc['TR_CLOCK']['lo']) and \
            (by_id['PSYH_HI@' + ses]['price'],
             by_id['PSYH_LO@' + ses]['price']) == \
            (pc['TR_4H']['hi'], pc['TR_4H']['lo']) and \
            PC.windows(ses)['TR_CLOCK'] == want['PSYC'] and \
            PC.windows(ses)['TR_4H'] == want['PSYH']
    for kind, (a, b) in want.items():
        group, ids, days = SL.SPEC[kind]
        hi, lo = (by_id['%s@%s' % (k, ses)] for k in ids)
        ok_px = ok_px and (hi['price'], lo['price']) == hilo(trs, a, b)
        ok_time = ok_time and all(
            x['t_on'] == b and x['group'] == group and
            x['t_off'] == d0 + 21 * H + days * D1 for x in (hi, lo))
cnt = collections.Counter((x['group'], x['session']) for x in lv_nq)
res = repD['results']['levels']
nq_n = {g: res[g]['NQ']['test']['n'] for g in SL.GROUPS}
ev_nq = [e for e in wick if e['instrument'] == 'NQ']
adr_nq = [e for e in adr if e['instrument'] == 'NQ']
first = OL.first_signals(ev_nq + adr_nq)


def line_at(e):
    """The ADR line an event was at, re-derived from the session's raw
    mids up to its time."""
    runs = {g['run'] for g in rD.grid if g['instrument'] == 'NQ' and
            g['session'] == e['session']}
    seen = [p for rn in runs for x, p in zip(*rD.series[('NQ', rn)])
            if x <= e['t']]
    a = rD.recent_range('NQ', e['session'])
    return min(seen) + a if e['kind'] == 'ADR_HIGH' else max(seen) - a


def n_taken(g):
    return len(V.one_at_a_time([x for x in OL.score(rD, first)
                                if x[0]['group'] == g]))


t('SL9: end to end on DEV: every session read has its Tokyo and London '
  'high and low and each Monday both Psy pairs, equal to the highest and '
  'lowest trade of the window read straight from the files (the Psy '
  'pairs also equal to mrofyt_psycheck\'s two windows, and differing from '
  'each other), each known from its window\'s end; the ADR lines exist '
  'from the sixth session on; signals come at these levels only, inside '
  'the time each is known, a Psy level also on later days of its week; '
  'every ADR signal is at the line as it stood; the first per level per '
  'session is taken; five tests reported; the validation session refused',
  ok_px and ok_time and
  {s for _g, s in cnt} == set(DEV) and
  all(cnt[('ASIA', s)] == 2 and cnt[('LONDON', s)] == 2 for s in DEV) and
  [s for s in DEV if cnt[('PSYC', s)]] == list(MONDAYS) and
  [s for s in DEV if cnt[('PSYH', s)]] == list(MONDAYS) and
  all(by_id['PSYC_HI@' + s]['price'] > by_id['PSYH_HI@' + s]['price'] and
      by_id['PSYC_HI@' + s]['price'] == by_id['TOKYO_HIGH@' + s]['price']
      and by_id['PSYH_HI@' + s]['price'] == by_id['LONDON_HIGH@' + s]['price']
      for s in MONDAYS) and
  adr_ses['NQ'] == list(DEV[5:]) and
  ev_nq and all(e['level_id'] in by_id and
                by_id[e['level_id']]['t_on'] <= e['t'] <
                by_id[e['level_id']]['t_off'] and
                e['group'] == by_id[e['level_id']]['group'] and
                e['level'] == by_id[e['level_id']]['price']
                for e in ev_nq) and
  all(e['session'] == by_id[e['level_id']]['session'] for e in ev_nq
      if e['group'] in ('ASIA', 'LONDON')) and
  any(e['session'] > by_id[e['level_id']]['session'] for e in ev_nq
      if e['group'] == 'PSYC') and
  any(e['session'] > by_id[e['level_id']]['session'] for e in ev_nq
      if e['group'] == 'PSYH') and
  adr_nq and {e['session'] for e in adr_nq} <= set(DEV[5:]) and
  {e['kind'] for e in adr_nq} == {'ADR_HIGH', 'ADR_LOW'} and
  all(abs(e['level'] - line_at(e)) < 1e-9 and
      e['level_id'] == '%s@%s' % (e['kind'], e['session'])
      for e in adr_nq) and
  len({(e['session'], e['level_id']) for e in first}) == len(first) and
  all(nq_n[g] > 0 and nq_n[g] == n_taken(g) and
      nq_n[g] <= res[g]['NQ']['every']['n'] for g in SL.GROUPS) and
  all(res[g]['NQ']['test']['test'] == g and
      res[g]['NQ']['test']['name'] == SL.GROUP_NAMES[g] and
      'DEV: describes, not a test' in res[g]['NQ']['test']['status'] and
      'holm_rejected' in res[g]['NQ']['test'] and
      res[g]['MNQ']['test']['status'].startswith('DESCRIBED')
      for g in SL.GROUPS) and
  repD['sessions_refused'] == ['20260921'] and
  repD['sessions_evaluated'] == sorted({e['session']
                                        for e in ev_nq + adr_nq}) and
  repD['levels']['NQ'] == dict(PSYC=4, PSYH=4, ASIA=18, LONDON=18, ADR=8)
  and all(nm in SL.text(repD) for nm in SL.GROUP_NAMES.values()) and
  json.dumps(repD, default=str))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc0 = SL.main([])
    rc_uh = SL.main([D, '--unblind', '--holdout'])
_reg = open(os.path.join(HERE, SL.REGISTRATION)).read()
t('SL10: a held-out read shows only the count for every group under 30 NQ '
  'trades; --unblind with --holdout is refused; the registration states '
  'the windows, the completeness rule, the ADR lines, the five tests, '
  'Holm, the withholding and that wave fourteen stays the headline',
  repU['withheld'] == list(SL.GROUPS) and
  all(k not in blob for k in ('"hit"', 'net_points', 'ci95', '"every"',
                              '"p"', 'by_session', 'without_best_day',
                              'outcomes', 'holm')) and
  all('results withheld until a read holds 30' in
      repU['results']['levels'][g]['NQ']['test']['status'] and
      repU['results']['levels'][g]['NQ']['test']['n'] > 0 and
      repU['results']['levels'][g]['MNQ']['test']['status'] == 'withheld'
      for g in SL.GROUPS) and
  'results withheld until a read holds 30' in SL.text(repU) and
  'won ' not in SL.text(repU) and
  repU['sessions_evaluated'] == ['20260921'] and
  repU['levels']['NQ'] == dict(PSYC=2, PSYH=2, ASIA=2, LONDON=2, ADR=2) and
  rc0 == 2 and rc_uh == 2 and
  all(x in _reg for x in (
      'Monday 00:00:00–07:59:59 **GMT**',
      'Sunday 22:00:00 – Monday 05:59:59 **ET**',
      '00:00:00–05:59:59 **GMT**', '08:00:00 **London time** to 09:29:59 ET',
      'Friday 17:00 ET', '**120 s**', '**600 s**',
      'last Sunday of March 01:00 GMT', '**5\n  at least**',
      'lowest mid so far) + A', 'highest mid so far) − A',
      'WICK entry', '**Holm over the five**',
      'Wave fourteen stays the headline', 'mrofyt_psycheck.py',
      'Explicitly NOT registered')))


# ---------------------------------------------------------------------
# SL11: an abandoned run leaves nothing
# ---------------------------------------------------------------------
def _corrupt_late(mp):
    with open(mp) as fh:
        man = json.load(fh)
    dp = os.path.join(os.path.dirname(mp), man['depth']['file'])
    with open(dp) as fh:
        rows = fh.read().splitlines(True)
    k = int(len(rows) * 0.9)
    rows[k] = ',' * 3 + ' ' * (len(rows[k]) - 4) + '\n'
    with open(dp, 'w') as fh:
        fh.writelines(rows)
    assert os.path.getsize(dp) == man['depth']['bytes']


d_bad, d_ref = os.path.join(WORK, 'bad'), os.path.join(WORK, 'ref')
for d in (d_bad, d_ref):
    for i, ses in enumerate(('20260903', '20260904')):
        three_runs(d, ses, i, n_small=8000, n_cash=12000)
    # Monday 7 September: only the run in Tokyo hours is good
    three_runs(d, '20260907', 2, n_small=8000, upto=1)
gc.collect()
bad = SY.synth_run(d_bad, n_depth=8000, dt_step=0.05,
                   t0=_epoch('20260907', 7, 5),
                   price_path=_path(15000.0, 60), trade_every=10,
                   quote_every=5, cid='lbad', session='20260907', seed=77)
gc.collect()
_corrupt_late(bad)
rb = SL.SessionLevelsRunner(d_bad)
rb.run()
rf = SL.SessionLevelsRunner(d_ref)
rf.run()
t('SL11: an abandoned run in London hours on a Monday leaves the clock '
  'Psy and Tokyo windows as the run before left them and no London or '
  'candle Psy window: everything matches the clean folder',
  rb.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  rb.win == rf.win and plain20(rb) == plain20(rf) and
  {k[1] for k in rb.win if k[2] == '20260907'} == {'TOKYO', 'PSYC'} and
  {k[1] for k in rb.win if k[2] == '20260904'} == {'TOKYO', 'LONDON'} and
  (SL.EDGE_S, SL.GAP_S) == (120.0, 600.0))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
