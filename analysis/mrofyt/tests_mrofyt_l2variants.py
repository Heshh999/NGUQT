#!/usr/bin/env python3
# MROF-YT-W8-L2VARIANTS-1.0 suite. The test count is exercised on a
# hand-built state, the variant rules and the 5-minute exit on hand-built
# events and paths, and the pipeline end to end on synthetic
# recorder-format runs (mles_v12_synth) with wave six's suite-only
# plumbing L2 detector (synthetic flow never flips, so the frozen L2
# never fires on it), restored afterwards. Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import array
import calendar
import collections
import hashlib
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

import mles_v12_synth as SY      # noqa: E402
import mrofyt_bigmove as BM      # noqa: E402
import mrofyt_l2variants as V    # noqa: E402
import mrofyt_levelbreak as LB   # noqa: E402
import mrofyt_runner as RUN      # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w8_')
A = lambda xs: array.array('d', xs)     # noqa: E731
T0 = float(calendar.timegm((2026, 9, 2, 13, 30, 0)))     # 09:30 ET
assert RUN.sod_seconds(T0) == 9.5 * 3600

# ---------------------------------------------------------------------
# LV1: the test number
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
rr = V.L2VariantRunner(EMPTY)
st = types.SimpleNamespace(instrument='NQ', session='20260902', run_id='r1')
aps = [RUN.Approach(i, lid, 100.0, 0.0, 1, 99.0, 'ask') for i, lid in
       ((1, 'YDAY_HIGH'), (2, 'YDAY_HIGH'), (3, 'OVERNIGHT_LOW'),
        (4, 'YDAY_HIGH'))]
for ap in aps:
    rr._count_test(st, ap)
nos = dict(rr.test_no)
st_m = types.SimpleNamespace(instrument='MNQ', session='20260902')
rr._count_test(st_m, RUN.Approach(9, 'YDAY_HIGH', 100.0, 0.0, 1, 99.0,
                                  'ask'))
counts_before = dict(rr.tests_seen)
rr.tests_seen = collections.Counter({k: v for k, v in rr.tests_seen.items()
                                     if k[0] != 'NQ'})       # as at a close
rr._count_test(st, RUN.Approach(5, 'YDAY_HIGH', 100.0, 0.0, 1, 99.0, 'ask'))
t('LV1: approaches are numbered per instrument, session and level, in '
  'order, whether or not they fire; a new session starts again at 1',
  nos == {('NQ', 1): 1, ('NQ', 2): 2, ('NQ', 3): 1, ('NQ', 4): 3} and
  counts_before[('MNQ', 'YDAY_HIGH')] == 1 and
  rr.test_no[('NQ', 5)] == 1)

# ---------------------------------------------------------------------
# LV2: the variants and the 5-minute exit
# ---------------------------------------------------------------------
ev = lambda no, dt: dict(test_no=no, morning=V.in_morning(T0 + dt))  # noqa
t('LV2: the morning window is 09:30:00-11:29:59 ET; V1 = first test, V2 '
  '= morning, V3 = both, V4 and V0 = every event',
  V.in_morning(T0) and not V.in_morning(T0 - 1) and
  V.in_morning(T0 + 7199) and not V.in_morning(T0 + 7200) and
  [V.takes(v, ev(1, 0)) for v in ('V1', 'V2', 'V3', 'V4', 'V0')] ==
  [True] * 5 and
  [V.takes(v, ev(2, 0)) for v in ('V1', 'V2', 'V3')] ==
  [False, True, False] and
  [V.takes(v, ev(1, 9000)) for v in ('V1', 'V2', 'V3')] ==
  [True, False, False] and V.takes('V4', ev(None, 9000)))

ts, ps = A([0, 100, 299, 301, 600]), A([100, 101, 103, 110, 130])
q = LB.path_exit(ts, ps, 0, 1, 100, 60, limit_s=V.QUICK_S)
f = LB.path_exit(ts, ps, 0, 1, 100, 60)
q2 = LB.path_exit(A([0, 100, 250]), A([100, 120, 150]), 0, 1, 100, 60,
                  limit_s=V.QUICK_S)
q3 = LB.path_exit(A([0, 100]), A([100, 101]), 0, 1, 100, 60,
                  limit_s=V.QUICK_S)
t('LV2b: the quick exit is the last mid at or before 300 s unless the '
  'target or stop came first; a run that ends first is unresolved',
  q == ('TIMEOUT', 12.0, 299) and f == ('TARGET', 100, 600) and
  q2 == ('TARGET', 100, 250) and q3 == ('UNRESOLVED', None, None))

# ---------------------------------------------------------------------
# LV3-LV4: end to end on synthetic tape (plumbing L2)
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
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w8c%d' % i, session=ses,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    rep5, r5 = V.run(D5)
    ev5 = V.variant_events(r5)
    sc5 = V.score_variants(r5, ev5)
    repU, _rU = V.run(D5, unblind=True)
    rB = LB.LevelBreakRunner(D5)
    rB.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
nq = {x['test']: x for x in rep5['tests'].get('NQ', [])}
ids = lambda vid: sorted(x[0]['t'] for x in sc5[vid])   # noqa: E731
per_level = collections.defaultdict(list)
for f5 in r5.w3_fires:
    if f5['family'] == 'L2':
        per_level[(f5['instrument'], f5['session'], f5['level'])].append(
            (f5['t'], f5['test_no']))
mono = all([n for _t, n in sorted(v)] == sorted(n for _t, n in v)
           for v in per_level.values())
t('LV3: end to end: every L2 event carries its test number (>= 1) and '
  'window; test numbers rise through a session at each level; V0 is wave '
  'six\'s T1; V3 = V1 AND V2; V4 takes what V0 takes; the validation '
  'session is refused; the report renders',
  ev5 and all(e['test_no'] and e['test_no'] >= 1 for e in ev5) and mono and
  ids('V0') == sorted(e['t'] for e, *_x in
                      LB.score_events(rB, LB.level_events(rB))['T1']
                      if e['family'] == 'L2') and
  set(ids('V3')) == set(ids('V1')) & set(ids('V2')) and
  len(sc5['V4']) <= len(sc5['V0']) and
  all(x[1] in ('TARGET', 'STOP', 'TIMEOUT') and x[4] <= V.QUICK_S
      for x in sc5['V4']) and
  set(nq) == {'V0', 'V1', 'V2', 'V3', 'V4'} and
  nq['V0']['status'] == 'REFERENCE' and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'V3' in V.text(rep5) and
  all(s > V.DEV_END for s in repU['sessions_evaluated']))

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803')):
    SY.synth_run(D6, n_depth=30000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = V.run(D6, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_bad = V.main([D7, '--holdout'])
    rc_uh = V.main([D5, '--unblind', '--holdout'])
t('LV4: a replay holdout folder is read whole when every session is before '
  '2026-09-01 and STOPPED when it holds a recorded session; --unblind '
  'with --holdout is refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  repH['sessions_refused'] == [] and rc_bad == 2 and rc_uh == 2 and
  'only sessions before 20260901' in buf.getvalue())

# ---------------------------------------------------------------------
# LV5-LV6: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = LB.LevelBreakRunner(D5)
ledA = rA.run()
rC = V.L2VariantRunner(D5)
ledC = rC.run()
strip = lambda fs: [dict((k, v) for k, v in x.items()   # noqa: E731
                         if k != 'test_no') for x in fs]
t('LV5: the wave-eight runner leaves wave six\'s fires (with their '
  'annotations), the grid and the wave-one ledger identical, and the '
  'signal module keeps its pinned hash',
  strip(rC.w3_fires) == rA.w3_fires and rC.grid == rA.grid and
  rC.trapped == rA.trapped and
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
r9a = V.L2VariantRunner(d9a)
r9a.run()
r9b = V.L2VariantRunner(d9b)
r9b.run()
_reg = open(os.path.join(HERE, V.REGISTRATION)).read()
t('LV6: an abandoned run is wound back whole (test numbers and the '
  'per-level counts); the registration states the four variants, the '
  'test count, the holdout rule and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.test_no == r9b.test_no and r9a.tests_seen == r9b.tests_seen and
  r9a.w3_fires == r9b.w3_fires and
  all(w in _reg for w in ('V1 FIRST TEST', 'V2 MORNING',
                          'V3 FIRST TEST + MORNING', 'V4 QUICK',
                          '09:30:00–11:29:59', '300 s', '2026-09-01',
                          'Holm over the four', 'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
