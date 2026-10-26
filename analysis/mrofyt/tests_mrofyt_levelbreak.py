#!/usr/bin/env python3
# MROF-YT-W6-LEVELBREAK-1.0 suite. The exits are exercised on hand-built
# paths and grids, the trapped-volume hook on a hand-built state, and the
# pipeline end to end on synthetic recorder-format runs (mles_v12_synth).
# Synthetic flow never flips, so the frozen L2 detector never fires on
# it; the end-to-end checks therefore swap in, INSIDE THIS SUITE ONLY, a
# plumbing detector (L2 without its flow condition), and restore the
# frozen one afterwards. Synthetic events verify CODE BEHAVIOR only,
# never market evidence. No order, fill or P&L exists anywhere.
import array
import collections
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
import mrofyt_levelbreak as LB   # noqa: E402
import mrofyt_pilot as PI        # noqa: E402
import mrofyt_runner as RUN      # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w6_')
TK = 0.25
A = lambda xs: array.array('d', xs)     # noqa: E731

# ---------------------------------------------------------------------
# LB1: the path exit
# ---------------------------------------------------------------------
ts, ps = A([0, 10, 20, 30, 40]), A([100, 101, 99, 95, 130])
c1 = LB.path_exit(ts, ps, 0, 1, 100, 60)
c2 = LB.path_exit(ts, ps, 0, 1, 100, 60, exit_t=25, exit_px=99.5)
c3 = LB.path_exit(A([0, 10, 20]), A([100, 96, 84]), 0, 1, 100, 60,
                  exit_t=25, exit_px=90.0)
c4 = LB.path_exit(A([0, 900, 1799, 1800, 1900]),
                  A([100, 101, 102, 103, 200]), 0, 1, 100, 60)
c5 = LB.path_exit(A([0, 100]), A([100, 101]), 0, 1, 100, 60)
c6 = LB.path_exit(A([0, 100, 4000]), A([100, 101, 101]), 0, -1, 100, 60,
                  exit_t=500, exit_px=102.0)
t('LB1: target, an outside exit that comes first, a stop that comes '
  'before the outside exit, the timeout on the last mid at 1800 s, the '
  'unresolved run, and an outside exit between path points',
  c1 == ('TARGET', 100, 40) and c2 == ('INVALIDATED', -2.0, 25) and
  c3 == ('STOP', -60, 20) and c4 == ('TIMEOUT', 12.0, 1800) and
  c5 == ('UNRESOLVED', None, None) and c6 == ('INVALIDATED', -8.0, 500))

rng = random.Random(11)
mism = checks = 0
for trial in range(60):
    tt, p = 0.0, 15000.0
    T, P = A([]), A([])
    for _ in range(rng.choice([50, 400, 1500])):
        tt += rng.choice([0.5, 2.0, 15.0, 60.0])
        p += rng.choice([-1, 1]) * TK * rng.choice([1, 2, 4, 12, 30])
        T.append(tt)
        P.append(p)
    cT, cP = BM.compress(T, P)
    for i in rng.sample(range(len(cP)), min(10, len(cP))):
        for d in (1, -1):
            checks += 1
            if LB.path_exit(cT, cP, i, d, 100, 60)[0] != \
                    BM.score_path_brute(cT, cP, cT[i], d, 60):
                mism += 1
t('LB1b: with no outside exit, path_exit labels every trade exactly as '
  'wave three\'s reference scan on %d random-walk checks' % checks,
  checks > 1000 and mism == 0)

# ---------------------------------------------------------------------
# LB2-LB3: the structural stop and the flow invalidation
# ---------------------------------------------------------------------
t('LB2: the structural stop is 2 ticks beyond the sweep\'s extreme, '
  'clamped to 12..60 ticks, for both break directions',
  LB.structural_stop(1, 110.0, 105.0) == 22.0 and
  LB.structural_stop(1, 105.5, 105.0) == 12.0 and
  LB.structural_stop(1, 130.0, 105.0) == 60.0 and
  LB.structural_stop(-1, 95.0, 100.0) == 22.0 and
  LB.structural_stop(1, None, 100.0) is None)

G = [(10, dict(D=50, z_delta_s=3.0, mid=101.0)),     # at/before t0
     (20, dict(D=50, z_delta_s=1.0, mid=101.0)),     # z too small
     (30, dict(D=-50, z_delta_s=3.0, mid=101.0)),    # wrong side
     (40, dict(D=50, z_delta_s=2.0, mid=100.0)),     # not back through
     (50, dict(D=50, z_delta_s=2.0, mid=100.25)),    # all three
     (60, dict(D=50, z_delta_s=4.0, mid=102.0))]
t('LB3: the flow invalidation is the FIRST grid tick strictly after the '
  'entry with the push back (sign and z >= 1.5) AND price a tick back '
  'through the level; none inside the limit is None',
  LB.flow_invalidation(G, 10, 1, 100.0) == (50, 100.25) and
  LB.flow_invalidation(G, 10, 1, 100.0, limit_s=30) is None and
  LB.flow_invalidation(G, 10, -1, 100.0) is None)

# ---------------------------------------------------------------------
# LB4: the trapped-volume hook and the fire annotation
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
rr = LB.LevelBreakRunner(EMPTY)
ap = RUN.Approach(7, 'YDAY_HIGH', 100.0, 0.0, 1, 99.0, 'ask')
ap2 = RUN.Approach(8, 'YDAY_LOW', 90.0, 0.0, -1, 91.0, 'bid')
ap2.active = False
st = types.SimpleNamespace(instrument='NQ', session='20260902', run_id='r1',
                           trades=collections.deque(),
                           approaches={'YDAY_HIGH': ap, 'YDAY_LOW': ap2})
for tr in [(1.0, 100.25, 5, 1), (2.0, 100.0, 9, 1), (3.0, 101.0, 4, -1),
           (4.0, 102.0, 3, 1), (5.0, 80.0, 50, -1)]:
    st.trades.append(tr)
    rr._on_trade_event(st, tr[0], {})
ap.touch = 102.0
rr._w3_fire(st, 'L2', -1, 6.0, ap, None)
f = rr.w3_fires[-1]
t('LB4: trapped volume counts only aggressive contracts in the break '
  'direction traded a tick or more beyond the level of an ACTIVE '
  'approach (5 + 3 = 8), and an L2 fire carries level, direction, sweep '
  'extreme and trapped volume',
  rr.trapped == {('NQ', 7): 8.0} and f['level_px'] == 100.0 and
  f['ad'] == 1 and f['touch'] == 102.0 and f['trapped'] == 8.0)

# ---------------------------------------------------------------------
# LB5-LB9: end to end on synthetic tape (plumbing detector)
# ---------------------------------------------------------------------
_FROZEN_L2 = BM.l2_sweep_reclaim


def _l2_plumbing(f):
    if f.get('level_id') not in BM.RANGE_LEVELS:
        return 0
    ad = f.get('ad')
    if not ad or not f.get('returned_through_level'):
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
                 trade_every=10, quote_every=5, cid='w6c%d' % i, session=ses,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    rep5, frz5, r5 = LB.run_dev(D5)
    ev5 = LB.level_events(r5)
    repE, _rE = LB.run_evaluate(D5, frz5, unblind=False)
    repU, _rU = LB.run_evaluate(D5, frz5, unblind=True)
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
l2 = [e for e in ev5 if e['family'] == 'L2']
nq = {x['test']: x for x in rep5['tests'].get('NQ', [])}
cut = sorted(e['trapped'] for e in l2 if e['instrument'] == 'NQ')
t('LB5: end to end: L2 events carry level, direction, sweep extreme and '
  'trapped volume; the five tests are scored; the trapped cut is the '
  'median of the NQ L2 events; the validation session is refused; the '
  'report serializes and renders',
  l2 and all(e.get(k) is not None for e in l2
             for k in ('level_px', 'ad', 'touch', 'trapped')) and
  set(nq) == {'T1', 'T2', 'T3', 'T4', 'T5'} and nq['T1']['n'] > 0 and
  rep5['trapped_cut']['NQ'] == cut[len(cut) // 2] and
  frz5['trapped_cut'] == rep5['trapped_cut'] and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'T3' in LB.text(rep5))
sc5 = LB.score_events(r5, ev5)
t1nq = [x for x in sc5['T1'] if x[0]['instrument'] == 'NQ']
t('LB5b: the trapped filter keeps exactly the T1 trades at or above the '
  'cut; every structural risk lies in 12..60 ticks; the flow exit risks '
  'its 80-tick emergency stop',
  nq['T5']['n'] == sum(1 for x in t1nq
                       if x[0]['trapped'] >= rep5['trapped_cut']['NQ']) and
  all(12 <= x[3] <= 60 for x in sc5['T2']) and
  all(x[3] == 80 for x in sc5['T3']) and sc5['T2'] and sc5['T3'])
eT1 = {x['test']: x for x in repE['tests']['NQ']}['T1']
t('LB6: --evaluate on DEV reproduces the DEV numbers and says so; with '
  '--unblind it evaluates only sessions after 20260918',
  eT1['n'] == nq['T1']['n'] and eT1['net_points'] == nq['T1']['net_points']
  and 'reproduction' in eT1['status'] and
  all(s > LB.DEV_END for s in repU['sessions_evaluated']))

# holdout: a replay folder of July-August sessions only, then one that
# holds a recorded session
D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260727', '20260728', '20260729', '20260730',
                         '20260731', '20260803')):
    SY.synth_run(D6, n_depth=40000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = LB.run_evaluate(D6, frz5, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_null = LB.main([D7, '--evaluate', os.devnull, '--holdout'])
fz = os.path.join(WORK, 'frozen.json')
json.dump(frz5, open(fz, 'w'))
with redirect_stdout(buf):
    rc_bad = LB.main([D7, '--evaluate', fz, '--holdout'])
    rc_u = LB.main([D5, '--unblind'])
    rc_h = LB.main([D5, '--holdout'])
    rc_uh = LB.main([D5, '--evaluate', fz, '--unblind', '--holdout'])
t('LB7: a replay holdout folder is read whole as validation when every '
  'session is before 2026-09-01, and STOPPED when it holds a recorded '
  'session; a file that is not the frozen cut is refused; --unblind / '
  '--holdout without --evaluate, or together, are refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260727' and
  repH['sessions_refused'] == [] and rc_bad == 2 and rc_null == 2 and
  'not a wave-six frozen file' in buf.getvalue() and
  'only sessions before 20260901' in buf.getvalue() and
  rc_u == 2 and rc_h == 2 and rc_uh == 2)

# LB8: nothing frozen changed
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = BM.BigMoveRunner(D5)
ledA = rA.run()
rB = LB.LevelBreakRunner(D5)
ledB = rB.run()
strip = lambda fs: [dict((k, v) for k, v in f.items() if k not in  # noqa
                         ('level_px', 'ad', 'touch', 'trapped')) for f in fs]
t('LB8: with the frozen detectors restored, the wave-six runner leaves '
  'wave three\'s fires and grid and the wave-one ledger identical, and '
  'the signal module keeps its pinned hash',
  strip(rB.w3_fires) == rA.w3_fires and rB.grid == rA.grid and
  json.dumps({k: ledA.get(k) for k in _CMP}, sort_keys=True,
             default=str) ==
  json.dumps({k: ledB.get(k) for k in _CMP}, sort_keys=True,
             default=str) and
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1')


# LB9: an abandoned run leaves nothing
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
    r9a = LB.LevelBreakRunner(d9a)
    r9a.run()
    r9b = LB.LevelBreakRunner(d9b)
    r9b.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
_reg = open(os.path.join(HERE, 'MROF_YT_WAVE6_LEVELBREAK_REGISTRATION.md')
            ).read()
t('LB9: an abandoned run is wound back whole in wave six (fires with '
  'their annotations, trapped volume); the registration states the five '
  'tests, the stops, the trapped rule, the holdout rule and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.w3_fires == r9b.w3_fires and r9a.trapped == r9b.trapped and
  'STRUCTURAL' in _reg and 'FLOW-INVALIDATION' in _reg and
  'TRAPPED' in _reg and '2026-09-01' in _reg and 'Holm' in _reg and
  'Explicitly NOT registered' in _reg)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
