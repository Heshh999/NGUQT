#!/usr/bin/env python3
# MROF-YT-W18-SCALEDBRACKET-1.0 suite. The scale, both brackets, the two
# paired tests and the withholding are exercised on hand-built paths and
# records with known answers, and the pipeline end to end on synthetic
# recorder-format runs (mles_v12_synth) with wave six's suite-only
# plumbing L2 detector, restored afterwards. Synthetic data verifies CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import array
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
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_l2targets as W         # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_scaledbracket as SB    # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w18_')
A = lambda xs: array.array('d', xs)     # noqa: E731

# ---------------------------------------------------------------------
# SB1: the scale
# ---------------------------------------------------------------------
t('SB1: k is the recent range over the frozen reference, clamped to wave '
  'nine\'s 0.4 .. 3.0; no recent range, no k',
  SB.scale(644.82, 322.41) == (2.0, False) and
  SB.scale(2000.0, 322.41) == (3.0, True) and
  SB.scale(100.0, 322.41) == (0.4, True) and
  SB.scale(None, 322.41) == (None, False) and
  (SB.K_MIN, SB.K_MAX) == (0.4, 3.0))

# ---------------------------------------------------------------------
# SB2: both brackets on one hand path
# ---------------------------------------------------------------------
# a short at 100: up 20 points (stops the fixed 15, not the scaled 30),
# then down to 50 (the scaled 50-point target with k = 2)
P = (A([0, 60, 120, 600, 3000]), A([100.0, 120.0, 110.0, 50.0, 50.0]))
r2 = types.SimpleNamespace(
    _compressed_paths={('NQ', 'r1'): P},
    recent_range=lambda inst, ses: 644.82 if ses == '20260915' else None)
ev2 = [dict(instrument='NQ', session='20260915', run='r1', t=0.0,
            direction=-1),
       dict(instrument='NQ', session='20260902', run='r1', t=0.0,
            direction=-1)]
rec2, nr2 = SB.brackets(r2, ev2, {'NQ': 322.41})
x = rec2[0]
t('SB2: on the same trade the fixed bracket stops at -15 while the scaled '
  '(k = 2: stop 30, target 50) rides the same swing to its target; each '
  'is net of the same costs, and in R units of its own stop; a session '
  'without a recent range is left out and counted',
  len(rec2) == 1 and nr2 == 1 and x['k'] == 2.0 and
  x['stop_points'] == 30.0 and x['target_points'] == 50.0 and
  x['fixed'] == ('STOP', -15.75) and x['scaled'] == ('TARGET', 49.5) and
  x['fixed_r'] == -1.05 and x['scaled_r'] == 1.65)


# ---------------------------------------------------------------------
# SB3: the two tests
# ---------------------------------------------------------------------
def recs(n_ses, per, gain, inst='NQ'):
    out = []
    for i in range(n_ses):
        for j in range(per):
            f = 24.5 if (i + j) % 2 else -15.75
            s = f + gain(i, j)
            k = 1.2
            out.append(dict(instrument=inst, session='202609%02d' % (i + 1),
                            t=float(j), k=k, clamped=False,
                            stop_points=15 * k, target_points=25 * k,
                            fixed=('TARGET' if f > 0 else 'STOP', f),
                            scaled=('TARGET' if s > 0 else 'STOP', s),
                            fixed_r=f / 15.0, scaled_r=s / (15 * k)))
    return out


steady = SB.tests(recs(12, 3, lambda i, j: 3.0 if i % 3 else 1.0), 'NQ')
worse = SB.tests(recs(12, 3, lambda i, j: -2.0 if i % 2 else -1.0), 'NQ')
oneday = SB.tests(recs(12, 3, lambda i, j: 60.0 if i == 0 else
                       (-0.5 if j else 0.2)), 'NQ')
few = SB.tests(recs(5, 3, lambda i, j: 3.0), 'NQ')
mnq = SB.tests(recs(12, 3, lambda i, j: 3.0, 'MNQ'), 'MNQ')
t('SB3: a steady gain PASSES on points; a loss is NOT PROVEN; a gain from '
  'one day is NOT PROVEN with that reason; the risk-unit test runs beside '
  'with Holm over two; under 30 no verdict; MNQ described',
  steady[0]['status'] == 'PASS' and steady[0]['effect'] > 0 and
  steady[1]['test'] == 'B2' and 'status' in steady[1] and
  worse[0]['status'] == 'NOT PROVEN' and
  worse[0]['reasons'] == ['the scaled bracket does no better'] and
  oneday[0]['status'] == 'NOT PROVEN' and
  any('one day' in m or 'luck' in m for m in oneday[0]['reasons']) and
  all(x['status'] == 'NOT ENOUGH TRADES' for x in few) and
  all(x['status'] == 'DESCRIBED (not tested)' for x in mnq))

# ---------------------------------------------------------------------
# SB4-SB5: end to end on synthetic tape (plumbing L2)
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
for i, s in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w18c%d' % i, session=s,
                 seed=i)
FROZEN = {'a_ref': {'NQ': 50.0, 'MNQ': 50.0}}
BM.l2_sweep_reclaim = _l2_plumbing
try:
    repD, rD = SB.run(D5, FROZEN)
    evD = FS.first_signals([e for e in V.variant_events(rD)
                            if e['session'] <= SB.DEV_END])
    repU, _rU = SB.run(D5, FROZEN, unblind=True)
    rW = W.TargetRunner(D5)
    rW.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
nq = repD['results']['NQ']
t('SB4: end to end on DEV: the trades are wave fourteen\'s first signals '
  'that have a recent range, each scored with both brackets; the runner '
  'is wave nine\'s (same fires and grid); the report renders',
  evD and nq['describe']['n'] + repD['no_recent_range'] <= len(evD) and
  nq['describe']['n'] > 0 and
  [x['test'] for x in nq['tests']] == ['B1', 'B2'] and
  all('DEV, seen before the registration' in x['status']
      for x in nq['tests']) and
  repD['sessions_refused'] == ['20260921'] and
  rD.w3_fires == rW.w3_fires and rD.grid == rW.grid and
  rD.ledger['wave18']['version'] == SB.W18_VERSION and
  'SCALED BRACKET (tested)' in SB.text(repD) and json.dumps(repD,
                                                            default=str))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = SB.main([D5, '--unblind', '--holdout'])
    rc_ref = SB.main([D5])
reg = open(os.path.join(HERE, SB.REGISTRATION)).read()
t('SB5: a held-out read under 30 trades withholds every result; '
  '--unblind with --holdout and a missing A_ref file are refused; the '
  'registration fixes the scale, both brackets, both tests and that the '
  'headline stays on the fixed 25 / 15',
  repU['withheld'] and all(k not in blob for k in (
      '"effect"', 'mean_k', 'net_points', 'ci95')) and
  'results withheld' in SB.text(repU) and rc_uh == 2 and rc_ref == 2 and
  "wave nine's frozen file" in buf.getvalue() and
  all(w in reg for w in ('0.4 .. 3.0', '60 × k ticks', '100 × k ticks',
                         'B1 POINTS', 'B2 RISK', 'Holm over two',
                         'still judged on the fixed', 'Explicitly NOT '
                         'registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
