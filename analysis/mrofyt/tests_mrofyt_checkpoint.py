#!/usr/bin/env python3
# MROF-YT-CHECKPOINT-1.0 suite. The one-read checkpoint is checked
# against every wave's own command on the same synthetic recorder-format
# runs (mles_v12_synth) with wave six's suite-only plumbing L2 detector,
# restored afterwards: each wave's report must be byte-identical, on DEV
# and on an unblind read. Synthetic data verifies CODE BEHAVIOR only,
# never market evidence. No order, fill or P&L exists.
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
import mrofyt_checkpoint as CP       # noqa: E402
import mrofyt_closereclaim as C      # noqa: E402
import mrofyt_confluence as CF       # noqa: E402
import mrofyt_earlylevels as E       # noqa: E402
import mrofyt_l2context as X         # noqa: E402
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_l2targets as W         # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_levelbreak as LB       # noqa: E402
import mrofyt_limitentry as LE       # noqa: E402
import mrofyt_minutelevels as ML     # noqa: E402
import mrofyt_obviouslevels as OL    # noqa: E402
import mrofyt_scaledbracket as SB    # noqa: E402
import mrofyt_valuearea as VA        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_cp_')
CLASSES = [(LB, 'LevelBreakRunner'), (V, 'L2VariantRunner'),
           (W, 'TargetRunner'), (C, 'CloseRunner'), (E, 'LevelsRunner'),
           (X, 'ContextRunner'), (VA, 'ValueRunner'),
           (FS, 'FirstSignalRunner'), (OL, 'ObviousLevelsRunner'),
           (ML, 'MinuteLevelsRunner'), (LE, 'LimitRunner'),
           (CF, 'ConfluenceRunner'), (SB, 'ScaledBracketRunner')]
REAL = [getattr(m, c) for m, c in CLASSES]


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
    SY.synth_run(D5, n_depth=40000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='cp%d' % i, session=s,
                 seed=i)
W6 = {'trapped_cut': {'NQ': 0.0, 'MNQ': 0.0}}
W9 = {'a_ref': {'NQ': 100.0, 'MNQ': 100.0}}
CAL = X.read_calendar(CP.CALENDAR)
dump = lambda x: json.dumps(x, sort_keys=True, default=str)   # noqa: E731


def alone(u):
    a = W9['a_ref']
    return {'wave 6': LB.run_evaluate(D5, W6, u)[0],
            'wave 8': V.run(D5, u)[0],
            'wave 9': W.run_evaluate(D5, W9, u)[0],
            'wave 10': C.run(D5, u)[0],
            'wave 11': E.run(D5, u, a_ref=a)[0],
            'wave 12': X.run(D5, u, calendar=CAL)[0],
            'wave 13': VA.run(D5, u, a_ref=a)[0],
            'wave 14': FS.run(D5, u)[0],
            'wave 15': OL.run(D5, u)[0],
            '16A': ML.run_recordings(D5, u)[0],
            '16B': LE.run(D5, u)[0],
            'wave 17': CF.run(D5, u)[0],
            'wave 18': SB.run(D5, W9, u)[0]}


_FROZEN_L2 = BM.l2_sweep_reclaim
BM.l2_sweep_reclaim = _l2_plumbing
try:
    repD, txD, rD = CP.run(D5, w6_frozen=W6, w9_frozen=W9, calendar=CAL)
    aloneD = alone(False)
    repU, txU, _rU = CP.run(D5, unblind=True, w6_frozen=W6, w9_frozen=W9,
                            calendar=CAL)
    aloneU = alone(True)
    repN, _tN, _rN = CP.run(D5, w6_frozen=W6, calendar=CAL)
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
restored = [getattr(m, c) for m, c in CLASSES] == REAL and \
    BM.l2_sweep_reclaim is _FROZEN_L2

t('CP1: on DEV, every wave\'s report from the one read is byte-identical '
  'to its own command (waves 6, 8-15, 16A, 16B, 17, 18), and the runner '
  'classes '
  'are restored afterwards',
  set(repD['reports']) == set(aloneD) and
  all(dump(repD['reports'][k]) == dump(aloneD[k]) for k in aloneD) and
  restored and repD['waves'][0] == 'wave 6' and
  repD['sessions_refused'] == ['20260921'])
t('CP2: on an unblind read too, so each wave\'s withholding and verdicts '
  'are its own',
  all(dump(repU['reports'][k]) == dump(aloneU[k]) for k in aloneU) and
  repU['reports']['wave 14']['withheld'] and
  repU['mode'] == 'unblind')

rows = [x for v in repD['scorecard'].values() for x in v]
head = repD['reports']['wave 14']['results']['NQ']['test']
txt = CP.text(repD, txD)
t('CP3: the headline is wave fourteen\'s NQ verdict; the scorecard lists '
  'every NQ row with its status and counts the tests apart from '
  'references and descriptions; wave seven and the minute-export parts '
  'are named as not in the read; every wave\'s own report follows',
  repD['summary']['headline']['status'] == head['status'] and
  repD['summary']['headline']['n'] == head['n'] and
  repD['summary']['tests'] == sum(1 for x in rows if CP.is_test(x[3])) and
  any(x[3] == 'REFERENCE' for x in rows) and
  all(lab.upper() in txt for lab in repD['waves']) and
  'HEADLINE' in txt and 'wave 7' in ' '.join(repD['not_run']) and
  '16C' in ' '.join(repD['not_run']) and
  'wave 9' not in repN['waves'] and 'wave 18' not in repN['waves'] and
  any(x.startswith('waves 9 and 18') for x in repN['not_run']))

bad = os.path.join(WORK, 'not_w9.json')
json.dump({'x': 1}, open(bad, 'w'))
buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = CP.main([D5, '--unblind', '--holdout'])
    rc_bad = CP.main([D5, '--a-ref', bad])
    rc_w6 = CP.main([D5, '--w6', os.path.join(WORK, 'missing.json')])
t('CP4: --unblind with --holdout is refused; a file that is not wave '
  'nine\'s frozen file, or a missing wave-six cut, stops before anything '
  'is read',
  rc_uh == 2 and rc_bad == 2 and rc_w6 == 2 and
  "not wave nine's frozen file" in buf.getvalue() and
  'wave six\'s frozen cut' in buf.getvalue())

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
