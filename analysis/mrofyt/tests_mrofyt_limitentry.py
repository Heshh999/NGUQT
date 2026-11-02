#!/usr/bin/env python3
# MROF-YT-W16B-LIMITENTRY-1.0 suite. The limit fill and its bracket are
# exercised on hand-built mid paths with known answers, the comparison and
# the verdicts on hand-built records, and the pipeline end to end on
# synthetic recorder-format runs (mles_v12_synth) with wave six's
# suite-only plumbing L2 detector, restored afterwards. Synthetic data
# verifies CODE BEHAVIOR only, never market evidence. No order, fill or
# P&L exists.
import array
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
import mrofyt_bigmove as BM          # noqa: E402
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_limitentry as LE       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w16b_')
A = lambda xs: array.array('d', xs)     # noqa: E731

# ---------------------------------------------------------------------
# LE1: the fill and the bracket
# ---------------------------------------------------------------------
fill_tgt = LE.limit_result(A([0, 10, 20, 30, 100, 200]),
                           A([100, 100.5, 100.75, 99, 75.5, 75]), 0, -1, 2)
at_only = LE.limit_result(A([0, 10, 59, 61, 3000]),
                          A([100, 100.5, 100.5, 101, 101]), 0, -1, 2)
stop = LE.limit_result(A([0, 20, 50, 3000]), A([100, 100.75, 115.5, 115.5]),
                       0, -1, 2)
ended = LE.limit_result(A([0, 10, 30]), A([100, 100.25, 100.5]), 0, -1, 2)
long4 = LE.limit_result(A([0, 30, 40, 2000]), A([100, 98.75, 99.5, 101]),
                        0, 1, 4)
t('LE1: a limit 2 or 4 ticks better fills only when the mid trades a full '
  'tick through it within 60 s (touching it is not enough), at the limit '
  'price; the bracket runs from that price; a path that ends first is '
  'unresolved',
  fill_tgt == ('TARGET', 100.0, 80.0) and at_only == ('UNFILLED', 0.0, 0.0)
  and stop == ('STOP', -60.0, 30.0) and ended[0] == 'UNRESOLVED' and
  long4 == ('TIMEOUT', 2.0, 10.0) and           # last mid by 30 min: 99.50
  LE.net_points('NQ', 'UNFILLED', 0.0) == 0.0 and
  LE.net_points('NQ', 'TARGET', 100.0) == 24.5)


# ---------------------------------------------------------------------
# LE2: the comparison and the verdicts
# ---------------------------------------------------------------------
def recs(n_ses, per, lim2, lim4, inst='NQ'):
    out = []
    for i in range(n_ses):
        for j in range(per):
            mk = ('TARGET', 24.5) if (i + j) % 2 else ('STOP', -15.75)
            out.append(dict(e=dict(session='202609%02d' % (i + 1),
                                   instrument=inst),
                            MARKET=mk, LIM2=lim2(i, j, mk),
                            LIM4=lim4(i, j, mk)))
    return out


better = lambda i, j, mk: (mk[0], mk[1] + (1.0 if i % 3 else 0.5))  # noqa
worse = lambda i, j, mk: ('UNFILLED', 0.0) if mk[0] == 'TARGET' else mk  # noqa
R = recs(12, 3, better, worse)
ver = LE.verdicts([LE.variant_stats(R, v) for v, _k in LE.OFFSETS], 'NQ')
few = LE.verdicts([LE.variant_stats(R[:20], v) for v, _k in LE.OFFSETS],
                  'NQ')
mnq = LE.verdicts([LE.variant_stats(recs(12, 3, better, worse, 'MNQ'), v)
                   for v, _k in LE.OFFSETS], 'MNQ')
t('LE2: each signal\'s limit result minus its market result, '
  'session-clustered, Holm over the two: a steady gain PASSES; missing the '
  'winners is NOT PROVEN, with the fill rate and the missed winners '
  'counted; under 30 signals no verdict; MNQ described',
  ver[0]['status'] == 'PASS' and ver[0]['fill_rate'] == 1.0 and
  abs(ver[0]['improvement'] - 0.8333) < 1e-3 and
  ver[1]['status'] == 'NOT PROVEN' and ver[1]['missed_winners'] == 18 and
  ver[1]['fill_rate'] == 0.5 and ver[1]['filled_net_points'] == -15.75 and
  all(x['status'] == 'NOT ENOUGH TRADES' for x in few) and
  all(x['status'] == 'DESCRIBED (not tested)' for x in mnq))

# ---------------------------------------------------------------------
# LE3-LE4: end to end on synthetic tape (plumbing L2)
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
                 trade_every=10, quote_every=5, cid='w16b%d' % i, session=s,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
try:
    repD, rD = LE.run(D5)
    evD = FS.first_signals([e for e in V.variant_events(rD)
                            if e['session'] <= LE.DEV_END])
    rcD = LE.signal_records(rD, evD)
    repU, _rU = LE.run(D5, unblind=True)
    rF = FS.FirstSignalRunner(D5)
    rF.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
nq = repD['results']['NQ']
t('LE3: end to end on DEV: the signals are wave fourteen\'s first L2 '
  'signals, each with MARKET, LIM2 and LIM4; the market column is wave '
  'fourteen\'s entry; the runner is wave fourteen\'s (same fires and '
  'grid); the report renders',
  rcD and nq['market']['n'] == len([x for x in rcD
                                     if x['e']['instrument'] == 'NQ']) and
  all(set(x) == {'e', 'MARKET', 'LIM2', 'LIM4'} for x in rcD) and
  [x['test'] for x in nq['tests']] == ['LIM2', 'LIM4'] and
  all('DEV, seen before the registration' in x['status']
      for x in nq['tests']) and
  repD['sessions_refused'] == ['20260921'] and
  rD.w3_fires == rF.w3_fires and rD.grid == rF.grid and
  rD.ledger['wave16b']['version'] == LE.W16B_VERSION and
  'LIMIT ENTRY (tested)' in LE.text(repD) and json.dumps(repD, default=str))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = LE.main([D5, '--unblind', '--holdout'])
reg = open(os.path.join(HERE, LE.REGISTRATION)).read()
t('LE4: a held-out read under 30 signals withholds every result; '
  '--unblind with --holdout is refused; the registration fixes part 16B',
  repU['withheld'] and all(k not in blob for k in (
      'improvement', 'fill_rate', 'net_points', 'missed_winners')) and
  'results withheld' in LE.text(repU) and rc_uh == 2 and
  all(w in reg for w in ('Part 16B', '2 ticks / 4 ticks', 'live for **60 s**',
                         'a full tick through', 'Holm over LIM2 and LIM4',
                         'no spread saving is credited')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
