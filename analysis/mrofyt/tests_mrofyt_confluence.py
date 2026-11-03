#!/usr/bin/env python3
# MROF-YT-W17-CONFLUENCE-1.0 suite. The families, the zone and grade, the
# event clustering, the four tests and the sizing ladder are exercised on
# hand-built levels, grid records and trades with known answers, and the
# pipeline end to end on synthetic recorder-format runs (mles_v12_synth)
# whose price pokes through 15,000. Synthetic data verifies CODE BEHAVIOR
# only, never market evidence. No order, fill or P&L exists.
import io
import json
import math
import os
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY          # noqa: E402
import mrofyt_confluence as CF       # noqa: E402
import mrofyt_earlylevels as E       # noqa: E402
import mrofyt_valuearea as VA        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w17_')

# ---------------------------------------------------------------------
# CF1: families
# ---------------------------------------------------------------------
ids = ['YDAY_HIGH', 'OVERNIGHT_LOW', 'LWEEK_HIGH', 'CASH_OPEN_0930',
       'GLOBEX_OPEN', 'VWAP_UPPER', 'R1', 'M3', 'SWING_H_1H@493',
       'SWING_L_4H@120', 'VA_VAH@20260902', 'IB_LOW@20260902',
       'R15000@20260902', 'EQ_HIGH#3']
t('CF1: every level falls in its family; pivot R1 is a pivot, R15000@ a '
  'round number',
  [CF.family_of(i) for i in ids] ==
  ['YDAY', 'OVERNIGHT', 'LWEEK', 'CASH_OPEN', 'GLOBEX_OPEN', 'VWAP',
   'PIVOT', 'PIVOT', 'SWING_1H', 'SWING_4H', 'VALUE', 'IB', 'ROUND',
   'EQUAL'])

# ---------------------------------------------------------------------
# CF2: the zone and the grade
# ---------------------------------------------------------------------
lv = [None] * len(E.FIXED_IDS)
put = dict(YDAY_HIGH=100.0, OVERNIGHT_HIGH=100.25, PP=101.75,
           VWAP_UPPER=102.25, LWEEK_HIGH=150.0)
for k, v in put.items():
    lv[E.FIXED_IDS.index(k)] = v
g = dict(t=1000.0, session='20260902', w11_lv=tuple(lv))
listed = [dict(id='R100@20260902', price=100.0, t_on=0.0, t_off=9e9,
               ses_idx=0),
          dict(id='IB_HIGH@20260902', price=99.0, t_on=0.0, t_off=9e9,
               ses_idx=0),
          dict(id='IB_LOW@20260902', price=98.0, t_on=2000.0, t_off=9e9,
               ses_idx=0)]
fz = CF.zone_families(g, listed, {'20260902': 0}, [100.0])
lone = CF.zone_families(dict(g, w11_lv=(None,) * len(E.FIXED_IDS)), [],
                        {'20260902': 0}, [150.0])
t('CF2: the zone holds every family with a level known at that moment '
  'within 8 ticks (2 points) of the fired level -- yesterday\'s and the '
  'overnight high are two families, a pivot 1.75 away counts, VWAP 2.25 '
  'away and an IB low not yet known do not; 3+ = A+, 2 = A, 1 = B',
  fz == {'YDAY', 'OVERNIGHT', 'PIVOT', 'ROUND', 'IB'} and lone == set() and
  [CF.grade_of(n) for n in (5, 3, 2, 1)] == ['A+', 'A+', 'A', 'B'])

# ---------------------------------------------------------------------
# CF3: one event per zone
# ---------------------------------------------------------------------
S = lambda tt, d, lid: dict(t=float(tt), direction=d, level_id=lid)  # noqa
ev = CF.cluster([S(0, -1, 'YDAY_HIGH'), S(30, -1, 'R100@x'),
                 S(45, 1, 'YDAY_LOW'), S(60, -1, 'PP'), S(61, -1, 'M3'),
                 S(200, -1, 'IB_HIGH@x')])
t('CF3: signals in the same direction within 60 s of the event\'s first '
  'are one event; the other direction and a signal 61 s later start new '
  'ones',
  [[s['level_id'] for s in e] for e in ev] ==
  [['YDAY_HIGH', 'R100@x', 'PP'], ['YDAY_LOW'], ['M3'], ['IB_HIGH@x']])


# ---------------------------------------------------------------------
# CF4: the four tests with Holm
# ---------------------------------------------------------------------
def rows_of(spec):
    """spec: [(session, grade, 'WWL', wide bonus)] -> trade rows."""
    out, k = [], 0
    for ses, grade, pat, bonus in spec:
        for c in pat:
            k += 1
            fx = 24.5 if c == 'W' else -15.75
            e = dict(instrument='NQ', session=ses, t=float(k), grade=grade,
                     fixed_net=fx, wide_net=fx + (bonus if c == 'W' else 0))
            out.append((e, 'TARGET' if c == 'W' else 'STOP',
                        100.0 if c == 'W' else -60.0, 60.0, 100.0))
    return out


ses = ['202609%02d' % d for d in range(1, 29)]
spec = []
for i, s in enumerate(ses[:24]):
    good = 'WWL' if i % 3 else 'WLL'
    spec += [(s, 'A+' if i % 2 else 'A', good, 15.0 if i % 4 else 6.0),
             (s, 'B', 'LLW' if i % 2 else 'LLL', 0.0)]
rows = rows_of(spec)
res = CF.tests(rows, 'NQ')
st = {x['test']: x for x in res}
few = CF.tests(rows[:20], 'NQ')
mnq = CF.tests(rows_of([(s, g_, p, b) for s, g_, p, b in spec[:20]]), 'MNQ')
t('CF4: confluence beating no confluence PASSES C1; A+ no better than A is '
  'NOT PROVEN (C2); a further 40-point target that adds PASSES C3; '
  'confluence trades that make money PASS C4; Holm runs over the four; '
  'under 30 trades no verdict; MNQ described',
  st['C1']['status'] == 'PASS' and st['C1']['effect'] > 0 and
  st['C2']['status'] == 'NOT PROVEN' and st['C3']['status'] == 'PASS' and
  st['C4']['status'] == 'PASS' and st['C1']['n_a'] == 72 and
  st['C1']['n_b'] == 72 and
  all(x['status'] == 'NOT ENOUGH TRADES' for x in few) and
  all(x['status'] == 'DESCRIBED (not tested)' for x in mnq))

# ---------------------------------------------------------------------
# CF5: the sizing ladder
# ---------------------------------------------------------------------
lad = CF.ladder(rows_of([('20260901', 'A+', 'W', 0), ('20260901', 'B', 'L', 0),
                         ('20260902', 'A', 'L', 0), ('20260902', 'B', 'W', 0)]))
t('CF5: the ladder trades 1 / 2 / 3 contracts for B / A / A+ against 1 for '
  'every trade: totals, points a contract and the deepest drawdown from a '
  'running peak',
  lad['flat'] == dict(total_points=17.5, contracts=4, per_contract=4.375,
                      max_drawdown=-31.5) and
  lad['ladder'] == dict(total_points=50.75, contracts=7, per_contract=7.25,
                        max_drawdown=-47.25))      # 73.50-15.75-31.50+24.50

# ---------------------------------------------------------------------
# CF6-CF7: end to end on synthetic tape
# ---------------------------------------------------------------------


def _path(amp):
    # peaks 0-21 points above 15,000: a poke through a round number, and
    # through yesterday's and last week's highs, then back
    return lambda i: 14970.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, s in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w17c%d' % i, session=s,
                 seed=i)
repD, rD = CF.run(D5)
evD = CF.events(rD)
repU, _rU = CF.run(D5, unblind=True)
rV = VA.ValueRunner(D5)
rV.run()
nq = repD['results']['NQ']
t('CF6: end to end: every event is graded from its zone, confluence zones '
  'appear where the swing meets yesterday\'s and last week\'s highs, both '
  'targets are scored, the ladder is reported; the runner is wave '
  'thirteen\'s (same fires and grid); the report renders',
  evD and all(e['grade'] == CF.grade_of(len(e['families'])) for e in evD)
  and any(e['grade'] in ('A+', 'A') for e in evD) and
  any(e['grade'] == 'B' for e in evD) and
  [x['test'] for x in nq['tests']] == ['C1', 'C2', 'C3', 'C4'] and
  all('DEV, seen before the registration' in x['status']
      for x in nq['tests']) and
  isinstance(nq['ladder'], dict) and
  repD['sessions_refused'] == ['20260921'] and
  rD.w3_fires == rV.w3_fires and rD.grid == rV.grid and
  rD.ledger['wave17']['version'] == CF.W17_VERSION and
  'CONFLUENCE (tested)' in CF.text(repD) and json.dumps(repD, default=str))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = CF.main([D5, '--unblind', '--holdout'])
reg = open(os.path.join(HERE, CF.REGISTRATION)).read()
t('CF7: a held-out read withholds every test short of trades and, when C1 '
  'is, the grade means and the ladder; --unblind with --holdout is '
  'refused; the registration fixes the families, the zone, the grades, '
  'the four tests and the ladder rule',
  repU['withheld'] == ['C1', 'C2', 'C3', 'C4'] and
  repU['results']['NQ']['ladder'] == 'withheld' and
  all(k not in blob for k in ('"effect"', 'fixed_net', '"by_grade"',
                              'total_points')) and rc_uh == 2 and
  all(w in reg for w in ('8 ticks (2.00 points)', '3 or more', 'A+',
                         '1 contract for B, 2 for A, 3 for A+',
                         'only if C1 passes', 'Holm over four',
                         'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
