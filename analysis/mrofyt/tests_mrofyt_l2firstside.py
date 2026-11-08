#!/usr/bin/env python3
# MROF-YT-W19-L2FIRSTSIDE-1.0 suite. The per-side rule is exercised on
# hand-built events, the registration's DEV row is reproduced from the
# saved DEV report, and the pipeline runs end to end on synthetic
# recorder-format runs (mles_v12_synth) with wave six's suite-only
# plumbing L2 detector, restored afterwards. Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import gc
import gzip
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
import mrofyt_costs as CO            # noqa: E402
import mrofyt_l2firstside as FD      # noqa: E402
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_l2variants as V        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w19_')

# ---------------------------------------------------------------------
# FD1: the first signal from each side, by hand
# ---------------------------------------------------------------------
E = lambda inst, ses, t_, d, *lv: dict(instrument=inst, session=ses,  # noqa
                                       t=float(t_), direction=d,
                                       levels=list(lv))
evs = [E('NQ', '20260902', 10, -1, 'YDAY_HIGH'),     # first short
       E('NQ', '20260902', 20, -1, 'YDAY_HIGH'),     # second short: no
       E('NQ', '20260902', 30, 1, 'YDAY_HIGH'),      # first long: yes
       E('NQ', '20260902', 40, 1, 'YDAY_HIGH', 'ON_HIGH'),   # long used
       E('NQ', '20260902', 50, 1, 'ON_HIGH'),        # used at 40
       E('NQ', '20260902', 60, -1, 'ON_HIGH'),       # first short there
       E('NQ', '20260902', 70, 1),                   # no level
       E('NQ', '20260903', 5, -1, 'YDAY_HIGH'),      # new session
       E('MNQ', '20260902', 15, -1, 'YDAY_HIGH')]    # other market
fd = FD.first_per_side(list(reversed(evs)))
fl = FS.first_signals(list(evs))
t('FD1: per instrument, session and direction, an event is taken only '
  'when none of its levels has had an L2 that way earlier; each level '
  'gives at most one short and one long; wave fourteen\'s single trade per '
  'level is always among them',
  [(e['instrument'], e['session'], e['t']) for e in fd] ==
  [('MNQ', '20260902', 15.0), ('NQ', '20260902', 10.0),
   ('NQ', '20260902', 30.0), ('NQ', '20260902', 60.0),
   ('NQ', '20260903', 5.0)] and
  {id(e) for e in fl} <= {id(e) for e in fd})

# ---------------------------------------------------------------------
# FD2: the registration's DEV rows from the saved DEV report
# ---------------------------------------------------------------------
w3 = json.load(gzip.open(os.path.join(HERE, 'frozen_dev_20261024',
                                      'w3.json.gz'), 'rt'))
rows3 = sorted(CO.scored(w3['events'], 'L2', 'NQ', '60'),
               key=lambda x: x[0]['t'])


def take(ids):
    sel = CO.one_at_a_time([x for x in rows3 if id(x[0]) in ids])
    v = [(sc['value_ticks'] - CO.cost_ticks('NQ', sc['outcome'])) / 4.0
         for _e, sc in sel]
    return sel, v


side_sel, side_v = take({id(e) for e in
                         FD.first_per_side([e for e, _ in rows3])})
lvl_sel, lvl_v = take({id(e) for e in
                       FS.first_signals([e for e, _ in rows3])})
lvl_ids = {id(e) for e, _ in lvl_sel}
extra = [v for (e, _sc), v in zip(side_sel, side_v) if id(e) not in lvl_ids]
nofed = [v for (e, _sc), v in zip(side_sel, side_v)
         if e['session'] != '20260916']
reg = open(os.path.join(HERE, FD.REGISTRATION)).read()
t('FD2: on the saved DEV report the rule gives the registration\'s rows: '
  '16 trades, 11 won, +13.20 a trade; 5 trades only this rule takes '
  '(+16.45); 10 trades and +10.45 without 16 September',
  len(side_v) == 16 and
  sum(1 for _e, sc in side_sel if sc['outcome'] == 'TARGET') == 11 and
  round(sum(side_v) / 16, 2) == 13.2 and len(lvl_v) == 12 and
  len(extra) == 5 and round(sum(extra) / 5, 2) == 16.45 and
  len(nofed) == 10 and round(sum(nofed) / 10, 2) == 10.45 and
  '| **first signal per side** (§2) | 16 | 11 (69 %) | +13.20 | +211.25 |'
  in reg)

# ---------------------------------------------------------------------
# FD3-FD4: end to end on synthetic tape (plumbing L2)
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
                 trade_every=10, quote_every=5, cid='w19c%d' % i, session=s,
                 seed=i)
# mles_v12_synth leaves each manifest to be closed when collected;
# collect now, so a Python without reference counting (PyPy) has
# written them before they are read
gc.collect()
BM.l2_sweep_reclaim = _l2_plumbing
try:
    repD, rD = FD.run(D5)
    evD = [e for e in V.variant_events(rD) if e['session'] <= FD.DEV_END]
    repU, _rU = FD.run(D5, unblind=True)
    rF = FS.FirstSignalRunner(D5)
    rF.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
fdD = FD.first_per_side(evD)
keys = [(e['instrument'], e['session'], lv, e['direction']) for e in fdD
        for lv in e['levels']]
nq = repD['results']['NQ']
t('FD3: end to end on DEV: each level and direction at most once a '
  'session, wave fourteen\'s first signals among them, one at a time; '
  'wave fourteen\'s rows and the extra trades beside; the runner is wave '
  'fourteen\'s (same fires and grid); the report renders',
  fdD and len(keys) == len(set(keys)) and
  {id(e) for e in FS.first_signals(evD)} <= {id(e) for e in fdD} and
  0 < nq['test']['n'] <= nq['test']['first_per_side'] and
  nq['per_level']['n'] > 0 and
  'DEV, seen before the registration' in nq['test']['status'] and
  repD['sessions_refused'] == ['20260921'] and
  rD.w3_fires == rF.w3_fires and rD.grid == rF.grid and
  rD.ledger['wave19']['version'] == FD.W19_VERSION and
  'FIRST SIGNAL FROM EACH SIDE (tested)' in FD.text(repD) and
  json.dumps(repD, default=str))

blob = json.dumps(repU['results'], default=str)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = FD.main([D5, '--unblind', '--holdout'])
t('FD4: a held-out read under 30 NQ trades shows the counts only; '
  '--unblind with --holdout is refused; the registration fixes the side, '
  'the rule, the verdict and that wave fourteen stays the headline',
  repU['withheld'] and all(k not in blob for k in (
      '"hit"', 'net_points', 'per_level', '"extra"', 'ci95')) and
  'results withheld until a read holds 30' in FD.text(repU) and
  rc_uh == 2 and
  all(w in reg for w in ('the side price comes from',
                         'one short and one long', 'Wave fourteen stays '
                         'the headline', 'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
