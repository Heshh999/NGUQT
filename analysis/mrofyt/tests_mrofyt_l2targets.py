#!/usr/bin/env python3
# MROF-YT-W9-L2TARGETS-1.0 suite. The targets, the uncapped excursion
# and the recent range are exercised by hand, the paired test on planted
# and null records, and the pipeline end to end on synthetic
# recorder-format runs (mles_v12_synth) with wave six's suite-only
# plumbing L2 detector, restored afterwards. Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import array
import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
import types
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_bigmove as BM      # noqa: E402
import mrofyt_l2targets as W     # noqa: E402
import mrofyt_l2variants as V    # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w9_')
A = lambda xs: array.array('d', xs)     # noqa: E731

# ---------------------------------------------------------------------
# LT1-LT3: the targets and the excursion
# ---------------------------------------------------------------------
t('LT1: NEXT LEVEL aims 2 ticks short of the nearest level at least 10 '
  'points ahead (nearer ones and those behind are passed over, None '
  'ignored, no cap); no such level: the fixed 25',
  W.next_level_target(1, 100.0, [105.0, 112.0, 130.0, None, 90.0]) ==
  (46.0, True) and
  W.next_level_target(1, 100.0, [110.0]) == (38.0, True) and
  W.next_level_target(1, 100.0, [109.75, 95.0]) == (100.0, False) and
  W.next_level_target(-1, 100.0, [95.0, 88.0, 150.0]) == (46.0, True) and
  W.next_level_target(1, 100.0, [400.0]) == (1198.0, True) and
  W.next_level_target(1, 100.0, []) == (100.0, False))
t('LT2: SCALED = 25 points x A / A_ref, clamped to 10-75 points; without A '
  'or A_ref: the fixed 25',
  W.scaled_target(300.0, 300.0) == (100.0, True) and
  W.scaled_target(450.0, 300.0) == (150.0, True) and
  W.scaled_target(60.0, 300.0) == (40.0, True) and
  W.scaled_target(1200.0, 300.0) == (300.0, True) and
  W.scaled_target(None, 300.0) == (100.0, False) and
  W.scaled_target(300.0, None) == (100.0, False))
t('LT3: the excursion is the furthest mid in the trade\'s favour until the '
  'stop or 1800 s, never stopped at a target; a run that ends first: None',
  W.mfe(A([0, 10, 20, 30, 40, 50]), A([100, 110, 104, 130, 84, 200]),
        0, 1) == 120.0 and
  W.mfe(A([0, 10, 1799, 1801]), A([100, 105, 140, 200]), 0, 1) == 160.0 and
  W.mfe(A([0, 10, 20]), A([100, 90, 116]), 0, -1) == 40.0 and
  W.mfe(A([0, 10]), A([100, 110]), 0, 1) is None)

# ---------------------------------------------------------------------
# LT4: the recent range
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
rr = W.TargetRunner(EMPTY)
for k in range(20):
    st = types.SimpleNamespace(instrument='NQ', session='202609%02d' % (k + 1),
                               run_high=1000.0 + k, run_low=900.0)
    rr._record_range(st)
rr._record_range(types.SimpleNamespace(instrument='NQ', session='20260930',
                                       run_high=None, run_low=None))
t('LT4: a session\'s high-to-low is kept at its close; the recent range is '
  'the mean of the previous 14 at most, 5 at least, never the session '
  'itself',
  rr.recent_range('NQ', '20260905') is None and
  rr.recent_range('NQ', '20260906') == sum(100.0 + k for k in range(5)) / 5
  and rr.recent_range('NQ', '20260921') ==
  sum(100.0 + k for k in range(6, 20)) / 14 and
  len(rr.ranges['NQ']) == 20 and rr.recent_range('MNQ', '20260921') is None)

# ---------------------------------------------------------------------
# LT5: the paired test
# ---------------------------------------------------------------------
rng = random.Random(5)
planted, null = [], []
for s in range(30):
    for _ in range(4):
        fx = rng.choice([('TARGET', 100.0), ('STOP', -60.0)])
        better = ('TARGET', 160.0) if fx[0] == 'TARGET' and \
            rng.random() < 0.7 else fx
        e = dict(session='s%02d' % s, instrument='NQ')
        planted.append((e, dict(FIXED=fx + (100.0, True),
                                NEXT=better + (160.0, True)), None))
        null.append((e, dict(FIXED=fx + (100.0, True),
                             NEXT=fx + (100.0, False)), None))
sp, sn = W.paired_stats(planted, 'NQ', 'NEXT'), W.paired_stats(null, 'NQ',
                                                               'NEXT')
t('LT5: the paired test finds a planted improvement over the fixed 25 on '
  'the same trades, and an identical target gives a zero difference with '
  'no p-value (never a verdict)',
  sp['mean_diff_points'] > 3 and sp['p'] < 0.001 and
  sp['ci95_diff_points'][0] > 0 and sp['n'] == 120 and
  sn['mean_diff_points'] == 0 and sn.get('p') is None and
  sn['fell_back_to_25'] == 120)

# ---------------------------------------------------------------------
# LT6-LT7: end to end on synthetic tape (plumbing L2)
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
                 trade_every=10, quote_every=5, cid='w9c%d' % i, session=ses,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    rep5, frz5, r5 = W.run_dev(D5)
    ev5 = W.target_events(r5)
    sc5 = W.score_targets(r5, ev5, frz5['a_ref'])
    repE, _rE = W.run_evaluate(D5, frz5)
    repU, _rU = W.run_evaluate(D5, frz5, unblind=True)
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
nq = {x['test']: x for x in rep5['results']['NQ']['tests']}
rr_vals = sorted(e['recent_range'] for e in ev5
                 if e['instrument'] == 'NQ' and e['recent_range'] is not None)
late = [e for e in ev5 if e['session'] >= '20260908']
t('LT6: end to end: events carry the seven target levels and the recent '
  'range (none before 5 closed sessions); A_ref is the median; the four '
  'tests compare each target with the fixed 25 on the same trades; FIRST '
  'is the first-test subset; the validation session is refused',
  ev5 and all(len(e['target_levels']) == 7 for e in ev5) and
  all(e['recent_range'] is None for e in ev5 if e['session'] < '20260908')
  and late and all(e['recent_range'] is not None for e in late) and
  frz5['a_ref']['NQ'] == rr_vals[len(rr_vals) // 2] and
  set(nq) == {'N-ALL', 'S-ALL', 'N-FIRST', 'S-FIRST'} and
  nq['N-ALL']['n'] == len([x for x in sc5 if x[0]['instrument'] == 'NQ'])
  and nq['N-FIRST']['n'] == len([x for x in sc5 if x[0]['instrument'] ==
                                 'NQ' and x[0]['test_no'] == 1]) and
  all(set(res) == {'FIXED', 'NEXT', 'SCALED'} for _e, res, _m in sc5) and
  all(40 <= res['SCALED'][2] <= 300 for _e, res, _m in sc5) and
  rep5['sessions_refused'] == ['20260921'] and
  rep5['results']['NQ']['mfe']['ALL']['n'] > 0 and
  json.dumps(rep5, default=str) and 'S-FIRST' in W.text(rep5))
eG = {x['test']: x for x in repE['results']['NQ']['tests']}
t('LT6b: --evaluate on DEV with the frozen A_ref reproduces the DEV numbers '
  'and says so; with --unblind it evaluates only sessions after 20260918',
  all(eG[k]['n'] == nq[k]['n'] and
      eG[k].get('mean_diff_points') == nq[k].get('mean_diff_points')
      for k in nq) and
  all('reproduction' in x['status'] for x in eG.values()) and
  all(s > W.DEV_END for s in repU['sessions_evaluated']))

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803')):
    SY.synth_run(D6, n_depth=30000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = W.run_evaluate(D6, frz5, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
fz = os.path.join(WORK, 'frozen.json')
json.dump(frz5, open(fz, 'w'))
buf = io.StringIO()
with redirect_stdout(buf):
    rc_null = W.main([D7, '--evaluate', os.devnull, '--holdout'])
    rc_bad = W.main([D7, '--evaluate', fz, '--holdout'])
    rc_u = W.main([D5, '--unblind'])
    rc_uh = W.main([D5, '--evaluate', fz, '--unblind', '--holdout'])
t('LT7: a replay holdout folder is read whole when every session is before '
  '2026-09-01 and STOPPED when it holds a recorded session; a file that is '
  'not the frozen A_ref is refused; --unblind without --evaluate, or with '
  '--holdout, is refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  rc_null == 2 and rc_bad == 2 and rc_u == 2 and rc_uh == 2 and
  'not a wave-nine frozen file' in buf.getvalue() and
  'only sessions before 20260901' in buf.getvalue())

# ---------------------------------------------------------------------
# LT8-LT9: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = V.L2VariantRunner(D5)
ledA = rA.run()
rC = W.TargetRunner(D5)
ledC = rC.run()
strip = lambda fs: [dict((k, v) for k, v in x.items()   # noqa: E731
                         if k not in ('target_levels', 'recent_range'))
                    for x in fs]
t('LT8: the wave-nine runner leaves wave eight\'s fires (with their test '
  'numbers), the grid and the wave-one ledger identical, and the signal '
  'module keeps its pinned hash',
  strip(rC.w3_fires) == rA.w3_fires and rC.grid == rA.grid and
  rC.test_no == rA.test_no and
  json.dumps({k: ledA.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledC.get(k) for k in _CMP}, sort_keys=True,
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
r9a = W.TargetRunner(d9a)
r9a.run()
r9b = W.TargetRunner(d9b)
r9b.run()
_reg = open(os.path.join(HERE, W.REGISTRATION)).read()
t('LT9: an abandoned run is wound back whole (the fires with their levels '
  'and range); the registration states the three targets, the four tests, '
  'the holdout rule and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.w3_fires == r9b.w3_fires and r9a.test_no == r9b.test_no and
  dict(r9a.ranges) == dict(r9b.ranges) and
  all(w in _reg for w in ('NEXT LEVEL', 'SCALED', 'FIXED', 'N-ALL',
                          'S-FIRST', '40 ticks (10 points)', '2 ticks short',
                          '40–300 ticks', '2026-09-01', 'Holm over the four',
                          'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
