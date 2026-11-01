#!/usr/bin/env python3
# MROF-YT-W12-L2CONTEXT-1.0 suite. The two filters are exercised on
# hand-built values, the kept-minus-removed test on planted and null
# records, and the pipeline end to end on synthetic recorder-format runs
# (mles_v12_synth) with wave six's suite-only plumbing L2 detector,
# restored afterwards. Synthetic events verify CODE BEHAVIOR only, never
# market evidence. No order, fill or P&L exists.
import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_bigmove as BM      # noqa: E402
import mrofyt_earlylevels as E   # noqa: E402
import mrofyt_l2context as X     # noqa: E402
import mrofyt_l2targets as W     # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w12_')

# ---------------------------------------------------------------------
# CX1: the filters
# ---------------------------------------------------------------------
c = X.classify
t('CX1: TREND removes a fade at least 0.25 x A from VWAP on the far side '
  '(a long below, a short above), keeps it when near VWAP or trading with '
  'the side; BIG DAY removes once the range so far reaches 1.0 x A; no A, '
  'VWAP or range: undecided',
  c(1, 70.0, 100.0, 50.0, 100.0) == dict(TREND='removed', BIG='kept') and
  c(1, 130.0, 100.0, 50.0, 100.0)['TREND'] == 'kept' and
  c(-1, 130.0, 100.0, 50.0, 100.0)['TREND'] == 'removed' and
  c(-1, 120.0, 100.0, 50.0, 100.0)['TREND'] == 'kept' and
  c(-1, 125.0, 100.0, 50.0, 100.0)['TREND'] == 'removed' and
  c(1, 100.0, 100.0, 50.0, 100.0)['TREND'] == 'kept' and
  c(1, 70.0, None, 50.0, 100.0) == dict(TREND=None, BIG='kept') and
  c(1, 70.0, 100.0, 99.9, 100.0)['BIG'] == 'kept' and
  c(1, 70.0, 100.0, 100.0, 100.0)['BIG'] == 'removed' and
  c(1, 70.0, 100.0, None, 100.0)['BIG'] is None and
  c(1, 70.0, 100.0, 50.0, None) == dict(TREND=None, BIG=None))


# ---------------------------------------------------------------------
# CX2: the kept-minus-removed test
# ---------------------------------------------------------------------
def rec(s, k, win, cls):
    o, v = ('TARGET', 100.0) if win else ('STOP', -60.0)
    e = dict(instrument='NQ', session='s%02d' % s, t=1000.0 * s + k,
             test_no=1 if k == 0 else 2, net=W.net_points('NQ', o, v),
             cls=cls)
    return (e, o, v, 60.0, 30.0)


rng = random.Random(4)
planted, null, thin = [], [], []
for s in range(30):
    for k in range(4):
        kept = k % 2 == 0
        cls = dict(TREND='kept' if kept else 'removed', BIG='kept')
        planted.append(rec(s, k, rng.random() < (0.75 if kept else 0.25),
                           cls))
        null.append(rec(s, k, rng.random() < 0.5, cls))
        thin.append(rec(s, k, rng.random() < 0.5,
                        dict(TREND='kept' if k < 3 or s < 12 else 'removed',
                             BIG=None)))
tp = {x['test']: x for x in X.table(planted)['NQ']['tests']}
tn = {x['test']: x for x in X.table(null)['NQ']['tests']}
tt = {x['test']: x for x in X.table(thin)['NQ']['tests']}
t('CX2: the session-clustered kept-minus-removed test finds a planted '
  'filter (FILTER HELPS) and not a null one; fewer than 20 on a side, or '
  'every trade undecided, is NOT TESTED',
  tp['TR-ALL']['status'] == 'FILTER HELPS' and tp['TR-ALL']['diff_points'] > 10
  and tp['TR-ALL']['kept']['n'] == 60 and tp['TR-ALL']['removed']['n'] == 60
  and tn['TR-ALL']['status'] == 'DOES NOT HELP' and
  tp['BD-ALL']['status'] == 'NOT TESTED' and
  tt['TR-ALL']['status'] == 'NOT TESTED' and
  tt['BD-ALL']['undecided'] == 120)

cal_path = os.path.join(WORK, 'events.csv')
open(cal_path, 'w').write('# FOMC\n20260916,FOMC\n\n20260910, CPI\n')
bad_path = os.path.join(WORK, 'bad.csv')
open(bad_path, 'w').write('Sep 16,FOMC\n')
try:
    X.read_calendar(bad_path)
    bad_ok = False
except ValueError:
    bad_ok = True
t('CX3: a calendar is one YYYYMMDD,EVENT line per day (comments and blank '
  'lines skipped); anything else is refused',
  X.read_calendar(cal_path) == {'20260916': 'FOMC', '20260910': 'CPI'} and
  bad_ok)

# ---------------------------------------------------------------------
# CX4-CX5: end to end on synthetic tape (plumbing L2)
# ---------------------------------------------------------------------
_FROZEN_L2 = BM.l2_sweep_reclaim


def _l2_plumbing(fr):
    if fr.get('level_id') not in BM.RANGE_LEVELS:
        return 0
    ad = fr.get('ad')
    if not ad or not fr.get('returned_through_level'):
        return 0
    return -ad


def _path(amp):
    return lambda i: 15000.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260910', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w12c%d' % i, session=ses,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    rep5, r5 = X.run(D5, calendar={'20260909': 'FOMC'})
    ev5 = X.context_events(r5)
    sc5 = X.score(r5, ev5)
    repU, _rU = X.run(D5, unblind=True)
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
late = [x for x in sc5 if x[0]['session'] >= '20260908']
nq = rep5['results']['NQ']
t('CX4: end to end: L2 events carry the session VWAP and range so far; '
  'with 5 closed sessions behind them both filters decide, before that '
  'neither; four tests, the calendar split when given, the validation '
  'session refused, the report renders',
  ev5 and all(e.get('ctx_vwap') is not None and e.get('ctx_range') is not None
              for e in ev5) and
  all(x[0]['cls'] == dict(TREND=None, BIG=None) for x in sc5
      if x[0]['session'] < '20260908') and
  late and all(x[0]['cls']['TREND'] in ('kept', 'removed') and
               x[0]['cls']['BIG'] in ('kept', 'removed') for x in late) and
  [x['test'] for x in nq['tests']] == ['TR-ALL', 'TR-FIRST', 'BD-ALL',
                                       'BD-FIRST'] and
  nq['every_l2']['n'] == len([x for x in sc5 if x[0]['instrument'] == 'NQ'])
  and 'calendar' in nq and nq['calendar']['event_days']['n'] > 0 and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'BD-FIRST' in X.text(rep5) and
  all(s > X.DEV_END for s in repU['sessions_evaluated']))

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803')):
    SY.synth_run(D6, n_depth=30000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = X.run(D6, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_bad = X.main([D7, '--holdout'])
    rc_uh = X.main([D5, '--unblind', '--holdout'])
    rc_cal = X.main([D5, '--calendar', bad_path])
t('CX5: a replay holdout folder is read whole when every session is before '
  '2026-09-01 and STOPPED when it holds a recorded session; --unblind with '
  '--holdout and a malformed calendar are refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  rc_bad == 2 and rc_uh == 2 and rc_cal == 2 and
  'only sessions before 20260901' in buf.getvalue() and
  'calendar file cannot be used' in buf.getvalue())

# ---------------------------------------------------------------------
# CX6-CX7: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = E.LevelsRunner(D5)
ledA = rA.run()
rB = X.ContextRunner(D5)
ledB = rB.run()
strip = lambda fs: [dict((k, v) for k, v in f.items()   # noqa: E731
                         if k not in ('ctx_vwap', 'ctx_range')) for f in fs]
t('CX6: the wave-twelve runner leaves wave eleven\'s fires, grid and '
  'ranges and the wave-one ledger identical, and the signal module keeps '
  'its pinned hash',
  strip(rB.w3_fires) == rA.w3_fires and rB.grid == rA.grid and
  dict(rB.ranges) == dict(rA.ranges) and
  json.dumps({k: ledA.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledB.get(k) for k in _CMP}, sort_keys=True,
             default=str) and
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1')


def _late_corrupt_folder(d, good, bad, **kw):
    for i, ses in enumerate(good):
        SY.synth_run(d, session=ses, cid='g%d' % i, seed=i,
                     price_path=_path(30 + 3 * i), **kw)
    if bad is None:
        return
    mp = SY.synth_run(d, session=bad, cid='bad', seed=99,
                      price_path=_path(45), **kw)
    man = json.load(open(mp))
    dp = os.path.join(d, man['depth']['file'])
    rows = open(dp).read().splitlines(True)
    k = int(len(rows) * 0.9)
    rows[k] = ',' * 3 + ' ' * (len(rows[k]) - 4) + '\n'
    open(dp, 'w').writelines(rows)
    assert os.path.getsize(dp) == man['depth']['bytes']


_G9 = ('20260901', '20260902', '20260903')
d9a, d9b = os.path.join(WORK, 'bad'), os.path.join(WORK, 'ref')
kw9 = dict(n_depth=40000, dt_step=0.05, trade_every=10, quote_every=5)
_late_corrupt_folder(d9a, _G9, '20260904', **kw9)
_late_corrupt_folder(d9b, _G9, None, **kw9)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    r9a = X.ContextRunner(d9a)
    r9a.run()
    r9b = X.ContextRunner(d9b)
    r9b.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
_reg = open(os.path.join(HERE, X.REGISTRATION)).read()
t('CX7: an abandoned run is wound back whole (fires with their context); '
  'the registration states both filters, the four tests, the holdout rule '
  'and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.w3_fires == r9b.w3_fires and
  all(w in _reg for w in ('TREND', 'BIG DAY', '0.25 × A', '1.0 × A',
                          'TR-ALL', 'BD-FIRST', '2026-09-01',
                          'Holm over the four', 'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
