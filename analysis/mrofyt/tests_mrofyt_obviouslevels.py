#!/usr/bin/env python3
# MROF-YT-W15-OBVIOUSLEVELS-1.0 suite. The three level groups, the
# signal, the first-signal rule and the verdicts are exercised on
# hand-built paths, candles, swings, grids and trades with known
# answers, and the pipeline end to end on synthetic recorder-format runs
# (mles_v12_synth; the synthetic price pokes through 15,000 and back, so
# the ROUND group fires; its sessions are under an hour, so IB and EQUAL are
# checked by hand only). Synthetic events verify CODE BEHAVIOR only,
# never market evidence. No order, fill or P&L exists.
import array
import calendar
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
import mrofyt_earlylevels as E       # noqa: E402
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_obviouslevels as OL    # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w15_')
A = lambda xs: array.array('d', xs)     # noqa: E731


# ---------------------------------------------------------------------
# OL1: the initial balance
# ---------------------------------------------------------------------
def ib_path(t930, start=-600, gap=None):
    ts, ps = [], []
    for dt in range(start, 4200, 5):
        if gap and gap[0] < dt < gap[1]:
            continue
        p = 100.0
        if dt == 600:
            p = 110.0
        elif dt == 1800:
            p = 90.0
        elif dt == 3700:
            p = 120.0                     # after 10:30: not in the IB
        ts.append(t930 + dt)
        ps.append(p)
    return [(A(ts), A(ps))]


T930 = float(calendar.timegm((2026, 9, 2, 13, 30, 0)))     # EDT
T930N = float(calendar.timegm((2026, 11, 2, 14, 30, 0)))   # EST
ok_lv = OL.ib_levels(OL.scan(ib_path(T930))[1])
nov_lv = OL.ib_levels(OL.scan(ib_path(T930N))[1])
late = OL.ib_levels(OL.scan(ib_path(T930, start=120))[1])
holed = OL.ib_levels(OL.scan(ib_path(T930, gap=(1000, 1200)))[1])
t('OL1: the IB is the 09:30-10:29:59 ET high and low, known 10:30 to '
  '17:00 ET, in summer and winter time; a recording that starts after '
  '09:31 or has a 2-minute hole in the window gives none',
  [(x['kind'], x['price'], x['t_on'] - T930, x['t_off'] - T930,
    x['session']) for x in ok_lv] ==
  [('IB_HIGH', 110.0, 3600.0, 27000.0, '20260902'),
   ('IB_LOW', 90.0, 3600.0, 27000.0, '20260902')] and
  [x['t_on'] - T930N for x in nov_lv] == [3600.0, 3600.0] and
  nov_lv[0]['session'] == '20261102' and late == [] and holed == [])

# ---------------------------------------------------------------------
# OL2: round numbers
# ---------------------------------------------------------------------
G2 = ([dict(session='20260902', t=T930 + i, mid=m) for i, m in
       enumerate((21040.0, 21260.0, 21100.0))] +
      [dict(session='20260903', t=T930 + 86400 + i, mid=m) for i, m in
       enumerate((21330.0, 21390.0, None))])
rl = OL.round_levels(G2)
t('OL2: every multiple of 100 points between a session\'s lowest and '
  'highest mid, one step beyond each, for that session only',
  [(x['session'], x['price']) for x in rl] ==
  [('20260902', p) for p in (20900.0, 21000.0, 21100.0, 21200.0, 21300.0,
                             21400.0)] +
  [('20260903', p) for p in (21200.0, 21300.0, 21400.0, 21500.0)] and
  rl[0]['t_on'] == T930 and rl[0]['t_off'] == T930 + 3)

# ---------------------------------------------------------------------
# OL3: equal highs and lows
# ---------------------------------------------------------------------
TB = float(calendar.timegm((2026, 9, 2, 14, 0, 0)))         # 10:00 EDT
OFF = E.et_offset_hourly(TB)
K0 = int((TB + OFF) // 900)
end15 = lambda i: (K0 + i + 1) * 900 - OFF                   # noqa: E731


def cands(highs, closes=None):
    out = {}
    for i, h in enumerate(highs):
        lo = h - 1.0
        c = closes[i] if closes else lo + 0.25
        out[K0 + i] = [h, lo, c, end15(i) - 1.0]
    return out


H = [98, 98.5, 99, 100.0, 99, 98.5, 98, 98.5, 99, 100.75, 99, 98.5, 98,
     98.5, 99.5, 101.5]
CL = [h - 0.75 for h in H]
CL[15] = 101.25                                     # closes beyond 100.75
SI = {'20260902': 0}
eq = OL.equal_levels(OL.swings15(cands(H, CL)), SI)
H_far = list(H)
H_far[9] = 101.5                                    # 6 ticks: not equal
eq_far = OL.equal_levels(OL.swings15(cands(H_far, CL)), SI)
sw = lambda px, t_on, ses, kind='SWING_H': dict(     # noqa: E731
    kind=kind, price=px, t_on=t_on, t_off=float('inf'), session=ses)
SI2 = dict(('202609%02d' % d, i) for i, d in enumerate(range(1, 12)))
eq_hand = OL.equal_levels([
    sw(100.0, 1, '20260901'), sw(100.75, 2, '20260901'),
    sw(100.5, 3, '20260901'),                        # merges: no new level
    sw(102.0, 4, '20260902'), sw(102.25, 5, '20260902'),
    sw(105.0, 6, '20260901'), sw(105.0, 7, '20260908')], SI2)
t('OL3: two 15-minute swing highs within 4 ticks make an equal high at '
  'the higher price from the second\'s confirmation until a candle closes '
  'a tick beyond it (lows mirrored); 6 ticks apart is not equal; one '
  'within 2 ticks of an active level is not added again; an earlier swing '
  'more than 5 sessions back does not count',
  [(x['kind'], x['price'], x['t_on'], x['t_off']) for x in eq] ==
  [('EQ_HIGH', 100.75, end15(11), end15(15)),
   ('EQ_LOW', 97.0, end15(14), float('inf'))] and
  [x['kind'] for x in eq_far] == ['EQ_LOW'] and
  [(x['price'], x['t_on']) for x in eq_hand] == [(100.75, 2), (102.25, 5)])

# ---------------------------------------------------------------------
# OL4: the signal and the first signal at a level
# ---------------------------------------------------------------------
T0 = T930 + 3600 * 2


def grid4():
    g = []
    for dt in range(0, 900, 10):
        m, D, z = 20999.0, 0.0, None
        if dt in (60, 400):
            m, D, z = 21000.5, 10.0, 0.5           # 10 s close above
        elif 60 < dt < 90 or 400 < dt < 430:
            m, D, z = 21000.5, 5.0, 0.5
        elif dt in (90, 430):
            m, D, z = 20999.5, -20.0, 1.5          # back, sellers: fade
        g.append(dict(t=T0 + dt, instrument='NQ', session='20260902',
                      run='r1', mid=m, D=D, z_delta_s=z))
    return g


LV4 = {'NQ': [dict(id='R21000@20260902', group='ROUND', price=21000.0,
                   t_on=T0, t_off=T0 + 10000, session='20260902', ses_idx=0),
              dict(id='IB_HIGH@20260902', group='IB', price=21000.0,
                   t_on=T0 + 5000, t_off=T0 + 10000, session='20260902',
                   ses_idx=0)]}
ev4 = OL.wick_events(types.SimpleNamespace(grid=grid4()), LV4)
fs4 = OL.first_signals(ev4)
t('OL4: wave eleven\'s WICK entry at these levels only: a 10 s close a '
  'tick through, back within 300 s with the aggression against it; a '
  'level not yet known gives nothing; only the first signal at a level a '
  'session is taken',
  [(e['t'] - T0, e['direction'], e['group'], e['test_no']) for e in ev4] ==
  [(90.0, -1, 'ROUND', 1), (430.0, -1, 'ROUND', 2)] and
  [e['t'] - T0 for e in fs4] == [90.0])


# ---------------------------------------------------------------------
# OL5: the verdicts with Holm over the three groups
# ---------------------------------------------------------------------
def trades(pattern, inst='NQ'):
    rows, k = [], 0
    for ses, s in pattern:
        for c in s:
            k += 1
            rows.append((dict(instrument=inst, session=ses, t=float(k)),
                         'TARGET' if c == 'W' else 'STOP',
                         100.0 if c == 'W' else -60.0, 60.0, 100.0))
    return rows


ses = ['202609%02d' % d for d in range(1, 31)]
strong = trades([(s, 'WWL' if i % 3 else 'WLL')
                 for i, s in enumerate(ses[:12])])
border = trades([(s, ('WWL', 'WLL', 'WLL', 'WWWL')[i % 4])
                 for i, s in enumerate(ses[:12])])
alone = FS.verdict(border, 'NQ')
gv = OL.group_verdicts(dict(IB=strong, ROUND=border,
                            EQUAL=trades([(ses[0], 'W' * 10)]), _inst='NQ'))
gm = OL.group_verdicts(dict(IB=strong, ROUND=border, EQUAL=[], _inst='MNQ'))
t('OL5: each group gets wave fourteen\'s verdict, then Holm over the '
  'three: a group that passes alone (p 0.03) but not after allowing for '
  'three groups is NOT PROVEN; a group under 30 trades is NOT ENOUGH; '
  'MNQ is described only',
  gv['IB']['status'] == 'PASS' and gv['IB']['holm_rejected'] and
  alone['status'] == 'PASS' and 0.025 < alone['p'] < 0.05 and
  gv['ROUND']['status'] == 'NOT PROVEN' and
  gv['ROUND']['reasons'][-1].endswith('(Holm)') and
  gv['EQUAL']['status'] == 'NOT ENOUGH TRADES' and
  all(gm[g]['status'] == 'DESCRIBED (not tested)' for g in OL.GROUPS))

# ---------------------------------------------------------------------
# OL6-OL7: end to end on synthetic tape
# ---------------------------------------------------------------------


def _path(amp):
    # peaks 0-21 points above 15,000 for about 2-4.5 minutes: a poke
    # through a round number and back, what the WICK entry looks for
    return lambda i: 14970.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, s in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w15c%d' % i, session=s,
                 seed=i)
repD, rD = OL.run(D5)
lvD = OL.levels_by_instrument(rD)
evD = [e for e in OL.wick_events(rD, lvD) if e['session'] <= OL.DEV_END]
fsD = OL.first_signals(evD)
nqR = repD['groups']['ROUND']['NQ']
repU, _rU = OL.run(D5, unblind=True)
_min = (FS.MIN_TRADES, OL.MIN_TRADES)
FS.MIN_TRADES = OL.MIN_TRADES = 1                     # suite only
try:
    repU1, _rU1 = OL.run(D5, unblind=True)
finally:
    FS.MIN_TRADES, OL.MIN_TRADES = _min
rF = FS.FirstSignalRunner(D5)
rF.run()
t('OL6: end to end on DEV: round numbers through the synthetic swing give '
  'WICK signals; the test takes the first per level and session, one at '
  'a time; every signal is beside; the validation session is refused; '
  'the runner is wave fourteen\'s (same fires and grid); the report renders',
  any(x['group'] == 'ROUND' and x['price'] == 15000.0
      for x in lvD.get('NQ', [])) and
  evD and {e['group'] for e in evD} == {'ROUND'} and
  len({(e['session'], e['level_id']) for e in fsD}) == len(fsD) and
  0 < nqR['test']['n'] <= len(fsD) <= len(evD) and
  nqR['every']['n'] >= nqR['test']['n'] and
  'DEV, seen before the registration' in nqR['test']['status'] and
  repD['sessions_refused'] == ['20260921'] and not repD['withheld'] and
  rD.w3_fires == rF.w3_fires and rD.grid == rF.grid and
  rD.ledger['wave15']['version'] == OL.W15_VERSION and
  'ROUND: every 100 points (tested)' in OL.text(repD) and
  json.dumps(repD, default=str))

blob = json.dumps(repU['groups'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = OL.main([D5, '--unblind', '--holdout'])
led = os.path.join(WORK, 'exposed.json')
OL.record_exposure(dict(sessions_inspected=['20260921']), led)
reg = open(os.path.join(HERE, OL.REGISTRATION)).read()
t('OL7: a held-out read withholds every group under 30 NQ trades (count '
  'only, on screen and in the file) and shows a group that has them; '
  '--unblind with --holdout is refused; the ledger names wave fifteen; '
  'the registration fixes the three levels, the signal, Holm and the '
  'withholding',
  repU['withheld'] == list(OL.GROUPS) and
  all(k not in blob for k in ('"hit"', 'net_points', 'by_day', '"every"',
                              'ci95')) and
  'results withheld until a read holds 30' in OL.text(repU) and
  'ROUND' not in repU1['withheld'] and
  'VERDICT' in OL.text(repU1) and rc_uh == 2 and
  json.load(open(led))['exposed_days'][0]['exposed_by'] == OL.W15_VERSION
  and all(w in reg for w in ('09:30–10:30', 'whole multiple of 100.00',
                             '4 ticks (1.00 point)', 'Holm over the three',
                             'WICK', 'results withheld',
                             'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
