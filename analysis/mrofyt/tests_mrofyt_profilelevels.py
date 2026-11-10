#!/usr/bin/env python3
# MROF-YT-W20-PROFILELEVELS-1.0 suite. The overnight profile, the weekly
# value area, yesterday's close and midpoint, wave thirteen's event
# against another value area, the untested POCs and their targets and
# the verdicts are exercised on hand-built trades, grids and paths with
# known answers, and the pipeline end to end on synthetic recorder-format
# runs (mles_v12_synth), each session an overnight run and a cash run.
# Synthetic sessions last under an hour, so the end-to-end checks relax,
# INSIDE THIS SUITE ONLY, the completeness rules and wave thirteen's
# speed and flow conditions, and use wave six's suite-only plumbing L2
# detector; all are restored afterwards. Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import bisect
import calendar
import collections
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

import mles_v12_synth as SY          # noqa: E402
import mrofyt_bigmove as BM          # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_earlylevels as E       # noqa: E402
import mrofyt_l2targets as W         # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_levelbreak as LB       # noqa: E402
import mrofyt_obviouslevels as OL    # noqa: E402
import mrofyt_profilelevels as PL    # noqa: E402
import mrofyt_valuearea as VA        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w20_')
H = 3600.0
NS = types.SimpleNamespace
T930 = float(calendar.timegm((2026, 9, 2, 13, 30, 0)))      # Wed 09:30 EDT

# ---------------------------------------------------------------------
# PL1: the runner's hooks by hand
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
rr = PL.ProfileLevelsRunner(EMPTY)
for dt, px, sz in ((-15.5 * H, 15010.25, 5),        # 18:00:00 the evening before
                   (-11.5 * H, 15011.0, 7),         # 22:00
                   (-6.5 * H, 15010.75, 3),         # 03:00
                   (-1.0, 15012.5, 2),              # 09:29:59
                   (0.0, 15000.25, 10),             # 09:30:00: cash
                   (6.5 * H - 30, 15003.0, 1),      # 15:59:30: the close
                   (6.5 * H, 15100.0, 50),          # 16:00:00: neither
                   (7.0 * H, 15100.0, 50)):         # 16:30: neither
    rr._add_trade('NQ', '20260902', T930 + dt, px, sz)
on = rr.on_prof[('NQ', '20260902')]
on_seen = (dict(on[0]), on[1], on[2], on[3])
rr._finish_profile('NQ', '20260902')
D1 = 86400.0
for dt, px, sz in ((-14.5 * H, 15020.0, 4),         # 19:00: too late a start
                   (-1200.0, 15021.0, 2),           # 09:10
                   (900.0, 15020.0, 4),             # 09:45: cash
                   (6.5 * H - 120, 15021.0, 1)):    # 15:58:00: before 15:59
    rr._add_trade('NQ', '20260903', T930 + D1 + dt, px, sz)
rr._finish_profile('NQ', '20260903')
onv = PL.on_values(rr, 'NQ')
t('PL1: the trades wave thirteen\'s profile is handed also fill the '
  'session\'s overnight profile (18:00-09:29:59 ET, 1-point bins) or are '
  'kept as its last cash trade; at the close the complete cash bins and a '
  'close at or after 15:59 are kept; the overnight value area is known '
  'from that session\'s 09:30; a 19:00 start gives none; wave thirteen\'s '
  'own value area is unchanged',
  on_seen == ({15010: 8.0, 15011: 7.0, 15012: 2.0}, 0.0, 15.5 * H - 1,
              T930 - 1) and
  rr.cash_bins['NQ']['20260902'] == {15000: 10.0, 15003: 1.0} and
  rr.cash_close['NQ'] == {'20260902': 15003.0} and
  rr.cash_bins['NQ']['20260903'] == {15020: 4.0, 15021: 1.0} and
  onv == {'20260902': CX.value_area({15010: 8.0, 15011: 7.0, 15012: 2.0})
          + (T930,)} and
  rr.values['NQ']['20260902'] == CX.value_area({15000: 10.0, 15003: 1.0})
  and not rr.cash_last and
  rr.ledger['wave20']['version'] == PL.W20_VERSION)

# ---------------------------------------------------------------------
# PL2: last week's value area and yesterday's close
# ---------------------------------------------------------------------
WK36 = {'20260831': {100: 5.0}, '20260901': {100: 1.0, 101: 9.0},
        '20260902': {102: 2.0}}
r2 = NS(cash_bins={'NQ': dict(WK36, **{'20260908': {200: 1.0},
                                       '20260909': {201: 1.0}})},
        cash_close={'NQ': {'20260904': 15001.0, '20260909': 15002.0}})
wk = PL.week_values(r2, 'NQ', ['20260904', '20260908', '20260910',
                               '20260914', '20260921'])
t('PL2: last week\'s value area is the value area of the summed complete '
  'cash profiles of the ISO week before, with 3 or more of them (two: '
  'none; the same week: none); yesterday\'s close is the latest earlier '
  'close no more than 4 calendar days before',
  wk == {'20260908': CX.value_area({100: 6.0, 101: 9.0, 102: 2.0}),
         '20260910': CX.value_area({100: 6.0, 101: 9.0, 102: 2.0})} and
  PL.prev_close(r2, 'NQ', '20260908') == 15001.0 and
  PL.prev_close(r2, 'NQ', '20260910') == 15002.0 and
  PL.prev_close(r2, 'NQ', '20260914') is None and
  PL.prev_close(r2, 'NQ', '20260904') is None and
  PL.prev_close(r2, 'MNQ', '20260908') is None)


# ---------------------------------------------------------------------
# PL3: the four groups' levels
# ---------------------------------------------------------------------
def lv_tuple(yh, yl):
    x = [None] * len(E.FIXED_IDS)
    x[E.FIXED_IDS.index('YDAY_HIGH')] = yh
    x[E.FIXED_IDS.index('YDAY_LOW')] = yl
    return tuple(x)


T0908 = float(calendar.timegm((2026, 9, 7, 22, 0, 0)))      # Mon 18:00 EDT
T930_8 = float(calendar.timegm((2026, 9, 8, 13, 30, 0)))
ONB = {15010: 8.0, 15011: 7.0, 15012: 2.0}
g3 = [dict(instrument='NQ', session='20260908', run='r8', t=T0908,
           mid=15000.0, w11_lv=lv_tuple(None, None))]
g3 += [dict(instrument='NQ', session='20260908', run='r8', t=T0908 + 10.0 * k,
            mid=15000.0, w11_lv=lv_tuple(110.0, 90.5)) for k in (1, 2, 3)]
g3 += [dict(instrument='NQ', session='20260909', run='r9',
            t=T0908 + D1 + 10.0 * k, mid=15000.0,
            w11_lv=lv_tuple(120.0, 100.0)) for k in (0, 1)]
r3 = NS(grid=g3, cash_bins={'NQ': WK36},
        cash_close={'NQ': {'20260904': 15001.25}},
        on_prof={('NQ', '20260908'): [dict(ONB), 0.0, 15.5 * H - 1,
                                      T930_8 - 1]})
by3 = {x['id']: x for x in PL.levels_by_instrument(r3)['NQ']}
va_on, va_wk = CX.value_area(ONB), CX.value_area({100: 6.0, 101: 9.0,
                                                  102: 2.0})
t('PL3: ONVA is known from 09:30 to 17:00 ET of its session; WKVA, CLOSE '
  'and MID for the whole session; MID is halfway between the runner\'s '
  'YDAY_HIGH and YDAY_LOW; a session without an overnight, or with a close '
  '5 days old, has no ONVA, no CLOSE',
  set(by3) == {'ON_POC@20260908', 'ON_VAH@20260908', 'ON_VAL@20260908',
               'LW_POC@20260908', 'LW_VAH@20260908', 'LW_VAL@20260908',
               'YDAY_CLOSE@20260908', 'YDAY_MID@20260908',
               'LW_POC@20260909', 'LW_VAH@20260909', 'LW_VAL@20260909',
               'YDAY_MID@20260909'} and
  tuple(by3['ON_%s@20260908' % k]['price'] for k in ('POC', 'VAH', 'VAL'))
  == va_on and
  all((by3['ON_%s@20260908' % k]['t_on'], by3['ON_%s@20260908' % k]['t_off'],
       by3['ON_%s@20260908' % k]['group']) ==
      (T930_8, T930_8 + 7.5 * H, 'ONVA') for k in ('POC', 'VAH', 'VAL')) and
  tuple(by3['LW_%s@20260909' % k]['price'] for k in ('POC', 'VAH', 'VAL'))
  == va_wk and
  (by3['LW_VAH@20260908']['t_on'], by3['LW_VAH@20260908']['t_off']) ==
  (T0908, T0908 + 31.0) and
  (by3['YDAY_CLOSE@20260908']['price'], by3['YDAY_CLOSE@20260908']['group'])
  == (15001.25, 'CLOSE') and
  by3['YDAY_MID@20260908']['price'] == 100.25 and
  by3['YDAY_MID@20260909']['price'] == 110.0 and
  by3['YDAY_MID@20260908']['ses_idx'] == 0 and
  by3['YDAY_MID@20260909']['ses_idx'] == 1)


# ---------------------------------------------------------------------
# PL4: wave thirteen's event against another value area
# ---------------------------------------------------------------------
def mk(spec, t0=T930 + 1800):
    return [dict(t=t0 + dt, instrument='NQ', session='20260903', run='r1',
                 mid=m, D=D, z_delta_s=z) for dt, (m, D, z) in
            sorted(spec.items())]


V903 = {'NQ': {'20260902': (100.0, 110.0, 90.0)}}         # POC VAH VAL
base = {dt: (105.0, 0.0, None) for dt in range(0, 400, 10)}
fast = dict(base)
fast[100] = (112.0, 5.0, 0.5)                              # out (>= 2 pts)
fast[110] = (113.0, 5.0, 0.5)
fast[120] = (113.0, 5.0, 0.5)
fast[130] = (112.5, -10.0, 1.0)
fast[140] = (109.0, -30.0, 2.5)                            # back, 4+ in 30 s
slow = dict(fast)
slow[110], slow[120], slow[130] = (112.0, 0, None), (111.0, 0, None), \
    (110.5, 0, None)
slow[140] = (109.75, -30.0, 2.5)
weak = dict(fast)
weak[140] = (109.0, -30.0, 1.5)
NEVER = float('-inf')


def yday(known=NEVER):
    def f(inst, ses):
        va = VA.prev_value(V903.get(inst, {}), ses)
        return None if va is None else va + (known,)
    return f


def strip(evs):
    return [dict((k, v) for k, v in e.items() if k != 'family') for e in evs]


same = all(strip(PL.reentry_events(NS(grid=mk(sp), values=V903), yday(),
                                   'X')) ==
           strip(VA.va_events(NS(grid=mk(sp), values=V903)))
           for sp in (fast, slow, weak, base))
ev4 = PL.reentry_events(NS(grid=mk(fast)), yday(), 'ONVA')
t0_4 = T930 + 1800
t('PL4: handed yesterday\'s value, the event is wave thirteen\'s own, tick '
  'for tick (the fast return trades; too slow or too weak does not); a '
  'value area known only after the move out began still sees the later '
  'out ticks; one known only after price is back gives no trade',
  same and len(ev4) == 1 and
  (ev4[0]['t'], ev4[0]['direction'], ev4[0]['family']) ==
  (t0_4 + 140, -1, 'ONVA') and
  len(PL.reentry_events(NS(grid=mk(fast)), yday(t0_4 + 105), 'X')) == 1 and
  PL.reentry_events(NS(grid=mk(fast)), yday(t0_4 + 135), 'X') == [] and
  PL.reentry_events(NS(grid=mk(fast)), lambda i, s: None, 'X') == [])

# ---------------------------------------------------------------------
# PL5: untested POCs and the target
# ---------------------------------------------------------------------
S = ['20260901', '20260902', '20260903', '20260904', '20260908', '20260909',
     '20260910', '20260911']
g5 = [dict(instrument='NQ', session=s, run='r%d' % k, t=1000.0 * k)
      for k, s in enumerate(S)]
p5 = {('NQ', 'r0'): ([0.0, 1.0], [100.5, 101.0]),
      ('NQ', 'r1'): ([1000.0, 1001.0, 1002.0], [110.0, 105.0, 108.0]),
      ('NQ', 'r2'): ([2000.0, 2001.0, 2002.0], [107.0, 100.5, 99.0]),
      ('NQ', 'r3'): ([3000.0, 3001.0], [99.0, 121.0]),
      ('NQ', 'r4'): ([4000.0, 4500.0, 4510.0, 4520.0, 4530.0, 4540.0],
                     [150.0, 40.0, 45.0, 50.0, 60.0, 65.0]),
      ('NQ', 'r5'): ([5000.0, 5001.0], [250.0, 251.0]),
      ('MNQ', 'm1'): ([1000.0], [50.5])}
v5 = {'NQ': {'20260901': (100.5, 0, 0), '20260902': (120.5, 0, 0),
             '20260903': (30.5, 0, 0), '20260904': (200.5, 0, 0)}}
r5 = NS(values=v5, _compressed_paths=p5)
pocs = PL.naked_pocs(r5, 'NQ', g5)
NT = PL.naked_target
t('PL5: a POC is untested until a later session\'s mid is at it (2001) or '
  'the mids since the next session began have been on both sides of it: '
  'through it within a run (3001) or across the gap between two runs '
  '(5000); its own session and another instrument never count; one never '
  'reached stays untested',
  [(p['session'], p['price'], p['ses_idx'], p['t_touch']) for p in pocs] ==
  [('20260901', 100.5, 0, 2001.0), ('20260902', 120.5, 1, 3001.0),
   ('20260903', 30.5, 2, None), ('20260904', 200.5, 3, 5000.0)])
t('PL6: the target is 2 ticks short of the nearest untested POC 10 or more '
  'points ahead in the trade\'s direction, from the 5 sessions before; '
  'nearer than 10 points, already tested, behind the trade, from the '
  'trade\'s own session or older than 5 sessions: the fixed 25',
  NT(-1, 110.0, 1500.0, S[1], 1, pocs) == (100.0, False) and
  NT(-1, 111.0, 1500.0, S[1], 1, pocs) == (40.0, True) and
  NT(-1, 111.0, 2500.0, S[2], 2, pocs) == (100.0, False) and
  NT(1, 105.0, 2500.0, S[2], 2, pocs) == (60.0, True) and
  NT(-1, 40.5, 4500.0, S[4], 4, pocs) == (38.0, True) and
  NT(1, 40.0, 4500.0, S[4], 4, pocs) == (640.0, True) and
  NT(1, 190.0, 3500.0, S[3], 3, pocs) == (100.0, False) and
  NT(-1, 40.5, 9000.0, '20260914', 8, pocs) == (100.0, False))

ev6 = [dict(instrument='NQ', run='r4', session=S[4], t=4500.0, direction=1),
       dict(instrument='NQ', run='r4', session=S[4], t=4500.0, direction=-1),
       dict(instrument='NQ', run='zz', session=S[4], t=4500.0, direction=1),
       dict(instrument='NQ', run='r5', session=S[5], t=5000.0, direction=1)]
pocs6 = [dict(session=S[3], price=50.5, ses_idx=3, t_touch=None)]
sc6 = PL.score_naked(NS(_compressed_paths=p5), ev6, {'NQ': pocs6},
                     {'NQ': S})
t('PL7: both versions run on the same entry and stop: the POC target 2 '
  'ticks short (40 ticks) is hit first, the fixed 25 later; a trade whose '
  'run is not in the read, or that either version leaves unresolved, is '
  'dropped; a trade with no POC ahead keeps the fixed target for both',
  len(sc6) == 2 and sc6[0][0] is ev6[0] and
  sc6[0][1] == {'FIXED': ('TARGET', 100.0, 100.0, True),
                'NAKED': ('TARGET', 40.0, 40.0, True)} and
  sc6[1][0] is ev6[1] and sc6[1][1]['NAKED'][2:] == (100.0, False) and
  sc6[1][1]['NAKED'][:2] == sc6[1][1]['FIXED'][:2])


# ---------------------------------------------------------------------
# PL8: the paired verdict and Holm
# ---------------------------------------------------------------------
def rows_of(spec, inst='NQ'):
    """spec: [(session, n, fixed (outcome, ticks), naked (outcome, ticks),
    real)]."""
    out = []
    for ses, n, fx, nk, real in spec:
        for j in range(n):
            out.append((dict(session=ses, instrument=inst),
                        dict(FIXED=fx + (100.0, True),
                             NAKED=(nk[0], nk[1] + (j % 3), 160.0, real)),
                        None))
    return out


good = rows_of([(s, 6, ('STOP', -60.0), ('TARGET', 150.0 + 4 * k), True)
                for k, s in enumerate(S[:6])] +
               [(S[6], 5, ('STOP', -60.0), ('STOP', -60.0), False)])
one_day = rows_of([(s, 6, ('TARGET', 100.0), ('STOP', -60.0), True)
                   for s in S[:5]] +
                  [(S[5], 6, ('STOP', -60.0), ('TARGET', 4000.0), True)])
pv_good = PL.paired_verdict(good, 'NQ', 'NP-ALL')
pv_day = PL.paired_verdict(one_day, 'NQ', 'NP-ALL')
pv_few = PL.paired_verdict(good[:12], 'NQ', 'NP-FIRST')
pv_mnq = PL.paired_verdict(good, 'MNQ', 'NP-ALL')
pv_none = PL.paired_verdict([], 'NQ', 'NP-ALL')
d_hand = W.net_points('NQ', 'TARGET', 151.0) - W.net_points('NQ', 'STOP',
                                                           -60.0)
fam = [dict(n=40, p=0.001, status='PASS', reasons=[]),
       dict(n=40, p=0.04, status='PASS', reasons=[]),
       dict(n=10, p=0.0001, status='NOT ENOUGH TRADES', reasons=['x'])]
PL.apply_holm(fam, 'three things')
t('PL8: only trades with an untested POC ahead are compared (the others '
  'counted beside); PASS needs 30+ of them, the mean difference and its '
  '95 % range above 0 and a difference that stands without the best day; '
  'one day carrying it: NOT PROVEN; under 30: NOT ENOUGH TRADES; MNQ is '
  'described; Holm turns an unrejected 30+ test into NOT PROVEN and never '
  'counts a test under 30',
  pv_good['n'] == 36 and pv_good['without_poc'] == 5 and
  pv_good['status'] == 'PASS' and pv_good['reasons'] == [] and
  pv_good['mean_diff_points'] > 50 and pv_good['ci95_diff_points'][0] > 0
  and pv_good['without_best_day']['session'] == S[5] and
  pv_good['without_best_day']['n'] == 30 and
  abs(min(W.net_points('NQ', x[1]['NAKED'][0], x[1]['NAKED'][1]) -
          W.net_points('NQ', x[1]['FIXED'][0], x[1]['FIXED'][1])
          for x in good[:6]) - (d_hand - 0.25)) < 1e-9 and
  pv_day['status'] == 'NOT PROVEN' and
  any('rests on one day' in m for m in pv_day['reasons']) and
  pv_day['without_best_day']['session'] == S[5] and
  pv_few['status'] == 'NOT ENOUGH TRADES' and
  pv_few['reasons'] == ['12 of the 30 trades needed'] and
  pv_mnq['status'] == 'DESCRIBED (not tested)' and
  (pv_none['n'], pv_none['status']) == (0, 'NOT ENOUGH TRADES') and
  [x['holm_rejected'] for x in fam] == [True, False, False] and
  [x['status'] for x in fam] == ['PASS', 'NOT PROVEN',
                                 'NOT ENOUGH TRADES'] and
  'three things' in fam[1]['reasons'][0] and fam[2]['reasons'] == ['x'])

# ---------------------------------------------------------------------
# PL9-PL11: end to end (plumbing)
# ---------------------------------------------------------------------
_FROZEN = (PL.ON_FIRST_X, PL.ON_LAST_X, PL.CLOSE_FROM, VA.COMPLETE_LAST,
           VA.SPEED_TICKS, VA.FLOW_Z, BM.l2_sweep_reclaim)


def _l2_plumbing(fr):
    if fr.get('level_id') not in BM.RANGE_LEVELS:
        return 0
    ad = fr.get('ad')
    if not ad or not fr.get('returned_through_level'):
        return 0
    return -ad


def _relax():
    PL.ON_FIRST_X, PL.ON_LAST_X, PL.CLOSE_FROM = 1e9, 0.0, 0.0
    VA.COMPLETE_LAST, VA.SPEED_TICKS, VA.FLOW_Z = 0.0, -1e9, -1e9
    BM.l2_sweep_reclaim = _l2_plumbing


def _restore():
    (PL.ON_FIRST_X, PL.ON_LAST_X, PL.CLOSE_FROM, VA.COMPLETE_LAST,
     VA.SPEED_TICKS, VA.FLOW_Z, BM.l2_sweep_reclaim) = _FROZEN


def _path(b, amp):
    return lambda i: b + amp * math.sin(2 * math.pi * (i * 0.05) / 900.0)


def _epoch(ses, hh, mm):
    return float(calendar.timegm((int(ses[:4]), int(ses[4:6]), int(ses[6:]),
                                  hh, mm, 0)))


def two_runs(d, ses, i, n_on=20000, n_cash=60000, park=False, tag=''):
    """One session: an overnight run from 03:00 ET and a cash run from
    09:30 ET; `park` ends the cash run 60 points lower, where later
    sessions never trade, so that its POC stays untested."""
    b = 15000.0 + 12.0 * i
    cash = _path(b, 30 + 3 * i)
    if park:
        cash = (lambda f: lambda k: f(k) if k * 0.05 < 2400 else b - 60.0)(
            cash)
    a = SY.synth_run(d, n_depth=n_on, dt_step=0.05, t0=_epoch(ses, 7, 0),
                     price_path=_path(b, 20 + 2 * i), trade_every=10,
                     quote_every=5, cid='%so%d' % (tag, i), session=ses,
                     seed=i)
    c = SY.synth_run(d, n_depth=n_cash, dt_step=0.05, t0=_epoch(ses, 13, 30),
                     price_path=cash, trade_every=10, quote_every=5,
                     cid='%sc%d' % (tag, i), session=ses, seed=i + 50)
    return a, c


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260908',
            '20260909', '20260910', '20260921')
D = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    two_runs(D, ses, i, park=(i == 4))
gc.collect()     # mles_v12_synth leaves its manifests to the collector
_relax()
try:
    repD, rD = PL.run(D)
    levels = PL.levels_by_instrument(rD)
    wick = OL.wick_events(rD, levels)
    grid_nq = PL.grid_by_instrument(rD)['NQ']
    ses_nq = sorted({g['session'] for g in grid_nq})
    onv_nq = PL.on_values(rD, 'NQ')
    re_on = PL.reentry_events(rD, lambda i_, s: onv_nq.get(s)
                              if i_ == 'NQ' else None, 'ONVA')
    pocs_nq = PL.naked_pocs(rD, 'NQ', grid_nq)
    l2 = [e for e in V.variant_events(rD) if e['session'] <= PL.DEV_END]
    np_sc = PL.score_naked(rD, l2, {'NQ': pocs_nq}, {'NQ': ses_nq})
    repU, _rU = PL.run(D, unblind=True)
    rA = VA.ValueRunner(D)
    ledA = rA.run()
finally:
    _restore()

_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
t('PL9: the wave-twenty runner leaves wave thirteen\'s fires, grid, value '
  'areas and ranges and the wave-one ledger identical: hooks only',
  rD.w3_fires == rA.w3_fires and rD.grid == rA.grid and
  dict(rD.values) == dict(rA.values) and
  dict(rD.ranges) == dict(rA.ranges) and
  json.dumps({k: rD.ledger.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledA.get(k) for k in _CMP}, sort_keys=True, default=str))

lv_nq = levels['NQ']
by_id = {x['id']: x for x in lv_nq}
cnt = collections.Counter((x['group'], x['session']) for x in lv_nq)
DEV = SESSIONS[:7]
res = repD['results']
nq_n = {k: res[f][k]['NQ']['test']['n'] for f, ids, _l in PL.FAMILIES
        for k in ids}
first = OL.first_signals([e for e in wick if e['instrument'] == 'NQ'])


def nearest_ahead(e):
    """The registered target, re-derived without the module's helper."""
    ts, ps = V.compressed_paths(rD)[('NQ', e['run'])]
    p0 = ps[bisect.bisect_right(ts, e['t']) - 1]
    si = ses_nq.index(e['session'])
    ds = [e['direction'] * (p['price'] - p0) / 0.25 for p in pocs_nq
          if p['session'] < e['session'] and si - p['ses_idx'] <= 5 and
          (p['t_touch'] is None or p['t_touch'] > e['t'])]
    ds = [x for x in ds if x >= 40.0]
    return (min(ds) - 2.0, True) if ds else (100.0, False)


t('PL10: end to end on DEV: every session read has its three overnight '
  'levels from its own 09:30 (the refused validation session has none), '
  'last week\'s value area exists in the second week only, yesterday\'s '
  'close and midpoint from the second session on; signals come at '
  'these levels only, inside the time each is known, the first per level '
  'taken; overnight re-entries start at 09:30; every L2 trade\'s POC '
  'target is the nearest untested one 10+ points ahead, some real; eight '
  'tests reported; the validation session refused',
  {s for _g, s in cnt} == set(DEV) and
  all(cnt[('ONVA', s)] == 3 for s in DEV) and
  all(by_id['ON_VAH@%s' % s]['t_on'] == _epoch(s, 13, 30) and
      by_id['ON_VAH@%s' % s]['t_off'] == _epoch(s, 13, 30) + 7.5 * H
      for s in DEV) and
  [s for s in DEV if cnt[('WKVA', s)]] == ['20260908', '20260909',
                                          '20260910'] and
  [s for s in DEV if cnt[('CLOSE', s)]] == list(DEV[1:]) and
  [s for s in DEV if cnt[('MID', s)]] == list(DEV[1:]) and
  wick and all(e['level_id'] in by_id and
               by_id[e['level_id']]['t_on'] <= e['t'] <
               by_id[e['level_id']]['t_off'] and
               e['group'] == by_id[e['level_id']]['group'] and
               e['session'] == by_id[e['level_id']]['session']
               for e in wick if e['instrument'] == 'NQ') and
  len({(e['session'], e['level_id']) for e in first}) == len(first) and
  re_on and all(e['t'] >= onv_nq[e['session']][3] and
                e['direction'] == -e['b'] and e['val'] <= e['poc'] <= e['vah']
                for e in re_on) and
  np_sc and all(x[1]['NAKED'][2:] == nearest_ahead(x[0]) for x in np_sc) and
  any(x[1]['NAKED'][3] for x in np_sc) and
  nq_n['NP-ALL'] == sum(1 for x in np_sc if x[1]['NAKED'][3]) and
  res['targets']['NP-ALL']['NQ']['test']['without_poc'] ==
  sum(1 for x in np_sc if not x[1]['NAKED'][3]) and
  all(nq_n[k] > 0 for k in ('ONVA', 'WKVA', 'CLOSE', 'MID', 'RE-ON',
                            'NP-ALL', 'NP-FIRST')) and
  all(res['levels'][g]['NQ']['test']['n'] <=
      res['levels'][g]['NQ']['every']['n'] for g in PL.GROUPS) and
  all(res[f][k]['NQ']['test']['test'] == k and
      'DEV: describes, not a test' in res[f][k]['NQ']['test']['status'] and
      res[f][k]['MNQ']['test']['status'].startswith('DESCRIBED')
      for f, ids, _l in PL.FAMILIES for k in ids) and
  repD['sessions_refused'] == ['20260921'] and
  repD['levels']['NQ'] == {'ONVA': 21, 'WKVA': 9, 'CLOSE': 6, 'MID': 6} and
  all(nm in PL.text(repD) for nm in PL.NAMES.values()) and
  json.dumps(repD, default=str))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc0 = PL.main([])
    rc_uh = PL.main([D, '--unblind', '--holdout'])
_reg = open(os.path.join(HERE, PL.REGISTRATION)).read()
t('PL11: a held-out read shows only the count for every test under 30 NQ '
  'trades; --unblind with --holdout is refused; the registration states '
  'the levels, the completeness rules, the three kinds of test, Holm, the '
  'withholding and that wave fourteen stays the headline',
  repU['withheld'] == list(PL.GROUPS + PL.REENTRY + PL.TARGETS) and
  all(k not in blob for k in ('"hit"', 'net_points', 'ci95', '"every"',
                              '"win"', 'mean_diff', 'by_session',
                              'without_best_day', 'outcomes')) and
  all('results withheld until a read holds 30' in
      repU['results'][f][k]['NQ']['test']['status']
      for f, ids, _l in PL.FAMILIES for k in ids) and
  'results withheld until a read holds 30' in PL.text(repU) and
  all(s > PL.DEV_END for s in repU['sessions_evaluated']) and
  rc0 == 2 and rc_uh == 2 and
  all(w in _reg for w in (
      '18:00:00–09:29:59 ET', 'previous ISO week', '15:59:00 ET',
      '4 calendar days', '(YDAY_HIGH + YDAY_LOW) / 2', 'RE-ON', 'RE-WK',
      'NP-ALL', 'NP-FIRST', '40 ticks (10 points)', '2 ticks short',
      'Holm', 'Wave fourteen stays the headline',
      'Explicitly NOT registered')))


# ---------------------------------------------------------------------
# PL12: an abandoned run leaves nothing
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
kw = dict(n_on=8000, n_cash=20000)
for d in (d_bad, d_ref):
    for i, ses in enumerate(SESSIONS[:3]):
        two_runs(d, ses, i, **kw)
    # 4 September: a good overnight run, then a cash run
    SY.synth_run(d, n_depth=8000, dt_step=0.05, t0=_epoch('20260904', 7, 0),
                 price_path=_path(15036.0, 26), trade_every=10,
                 quote_every=5, cid='o4', session='20260904', seed=3)
gc.collect()
bad_cash = SY.synth_run(d_bad, n_depth=20000, dt_step=0.05,
                        t0=_epoch('20260904', 13, 30),
                        price_path=_path(15036.0, 39), trade_every=10,
                        quote_every=5, cid='c4bad', session='20260904',
                        seed=53)
bad_on = SY.synth_run(d_bad, n_depth=8000, dt_step=0.05,
                      t0=_epoch('20260908', 7, 0),
                      price_path=_path(15048.0, 28), trade_every=10,
                      quote_every=5, cid='o8bad', session='20260908',
                      seed=4)
gc.collect()
_corrupt_late(bad_cash)
_corrupt_late(bad_on)
_relax()
try:
    rb = PL.ProfileLevelsRunner(d_bad)
    rb.run()
    rf = PL.ProfileLevelsRunner(d_ref)
    rf.run()
finally:
    _restore()


def plain(r):
    return (dict((k, [dict(v[0]), v[1], v[2], v[3]])
                 for k, v in r.on_prof.items()),
            dict((i, dict(v)) for i, v in r.cash_bins.items()),
            dict((i, dict(v)) for i, v in r.cash_close.items()),
            dict(r.cash_last), dict((i, dict(v)) for i, v in
                                    r.values.items()))


t('PL12: an abandoned cash run leaves the session\'s overnight profile as '
  'it was and no cash close; an abandoned overnight run leaves no '
  'overnight profile: everything matches the clean folder',
  rb.ledger['totals'].get('runs_skipped_corrupt') == 2 and
  plain(rb) == plain(rf) and
  ('NQ', '20260904') in rf.on_prof and
  ('NQ', '20260908') not in rb.on_prof and
  '20260904' not in rb.cash_close['NQ'] and
  len(rf.cash_bins['NQ']) == 3 and
  (PL.ON_FIRST_X, PL.ON_LAST_X, PL.CLOSE_FROM, VA.COMPLETE_LAST,
   VA.SPEED_TICKS, VA.FLOW_Z, BM.l2_sweep_reclaim) == _FROZEN)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
