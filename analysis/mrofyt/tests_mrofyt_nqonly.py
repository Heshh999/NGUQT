#!/usr/bin/env python3
# MROF-YT-CHECKPOINT-1.1 --nq-only and MROF-YT-CPCOMPARE-1.0 suite. A
# two-instrument synthetic capture (mles_v12_synth: NQ and MNQ every
# session, plus a session MNQ alone recorded) is read by the one-read
# checkpoint in full and NQ-only, on DEV and on an unblind read, with
# wave six's suite-only plumbing L2 detector (restored afterwards); the
# NQ results must agree value for value. Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
import copy
import gc
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
import mrofyt_cpcompare as CC        # noqa: E402
import mrofyt_l2context as X         # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_nq_')
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
D = os.path.join(WORK, 'two')
for i, s in enumerate(SESSIONS):
    for inst, off in (('NQ', 0), ('MNQ', 7)):
        SY.synth_run(D, n_depth=40000, dt_step=0.05, instrument=inst,
                     price_path=_path(30 + 3 * i + off), trade_every=10,
                     quote_every=5, cid='%s%d' % (inst, i), session=s,
                     seed=i + off)
SY.synth_run(D, n_depth=40000, dt_step=0.05, instrument='MNQ',
             price_path=_path(44), trade_every=10, quote_every=5,
             cid='MNQonly', session='20260910', seed=99)
# mles_v12_synth leaves each manifest to be closed when collected;
# collect now, so a Python without reference counting (PyPy) has
# written them before they are read
gc.collect()
W6 = {'trapped_cut': {'NQ': 0.0, 'MNQ': 0.0}}
W9 = {'a_ref': {'NQ': 100.0, 'MNQ': 100.0}}
CAL = X.read_calendar(CP.CALENDAR)
dump = lambda x: json.dumps(x, sort_keys=True, default=str)   # noqa: E731

BM.l2_sweep_reclaim = _l2_plumbing
try:
    fullD, _tf, _rf = CP.run(D, w6_frozen=W6, w9_frozen=W9, calendar=CAL)
    nqD, txD, rnq = CP.run(D, w6_frozen=W6, w9_frozen=W9, calendar=CAL,
                           instruments=('NQ',))
    fullU, _tu, _ru = CP.run(D, unblind=True, w6_frozen=W6, w9_frozen=W9,
                             calendar=CAL)
    nqU, _tnu, _rnu = CP.run(D, unblind=True, w6_frozen=W6, w9_frozen=W9,
                             calendar=CAL, instruments=('NQ',))
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2

def mnq_keys(x, path=''):
    """Paths of keys naming MNQ, outside the frozen DEV inputs every
    report echoes (wave six's trapped cut, wave nine's A_ref)."""
    out = []
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ('trapped_cut', 'a_ref'):
                continue
            if 'MNQ' in str(k):
                out.append(path + '/' + str(k))
            out += mnq_keys(v, path + '/' + str(k))
    elif isinstance(x, list):
        for v in x:
            out += mnq_keys(v, path)
    return out


resD = CC.compare(fullD, nqD)
mnq_runs = [x for x in rnq.ledger.get('runs', []) if 'MNQ' in str(x)]
t('NQ1: on DEV, the NQ-only read gives every NQ value of the full read '
  '(the comparison sees MATCH over the reports, the scorecard and the '
  'headline); MNQ is not read at all; the day MNQ alone recorded is the '
  'one session missing and is named in a note',
  resD['match'] and resD['compared'] > 500 and
  dump(fullD['scorecard']) == dump(nqD['scorecard']) and
  dump(fullD['summary']) == dump(nqD['summary']) and
  nqD['instruments'] == ['NQ'] and fullD['instruments'] == ['NQ', 'MNQ'] and
  rnq.instruments == ('NQ',) and not mnq_runs and
  not mnq_keys(nqD['reports']) and mnq_keys(fullD['reports']) and
  set(fullD['sessions_inspected']) - set(nqD['sessions_inspected'])
  == {'20260910'} and
  any('20260910' in x for x in resD['notes']) and
  'NQ only: MNQ, never tested, not read' in CP.text(nqD, txD))

resU = CC.compare(fullU, nqU)
t('NQ2: on an unblind read too: MATCH, the same tests withheld, the same '
  'headline; a DEV report is never compared with an unblind one',
  resU['match'] and fullU['mode'] == nqU['mode'] == 'unblind' and
  dump(fullU['summary']) == dump(nqU['summary']) and
  [fullU['reports'][k].get('withheld') for k in sorted(fullU['reports'])]
  == [nqU['reports'][k].get('withheld') for k in sorted(nqU['reports'])]
  and fullU['reports']['wave 14']['withheld'])

# ---------------------------------------------------------------------
# NQ3: the comparison finds what it must and ignores what it must
# ---------------------------------------------------------------------
planted = copy.deepcopy(nqD)
planted['reports']['wave 14']['results']['NQ']['test']['n'] += 1
mnq_only = copy.deepcopy(fullD)
for v in mnq_only['reports'].values():
    for key in ('results', 'tests'):
        if isinstance(v.get(key), dict) and 'MNQ' in v[key]:
            v[key]['MNQ'] = {'changed': True}
noise = copy.deepcopy(nqD)
h = noise['reports']['wave 14']['results']['NQ']['test']
h['net_points'] = (h['net_points'] or 0.0) * (1 + 1e-13)
r_planted = CC.compare(fullD, planted)
# a report from a package before the last wave was added
LAST = fullD['waves'][-1]
older = copy.deepcopy(fullD)
del older['reports'][LAST], older['scorecard'][LAST]
older['waves'].remove(LAST)
older['summary']['tests'] -= sum(1 for x in fullD['scorecard'][LAST]
                                 if CP.is_test(x[3]))
r_older = CC.compare(older, nqD)
r_older_bad = CC.compare(older, planted)
try:
    CC.compare(fullD, fullU)
    refused = False
except ValueError as exc:
    refused = 'not the same kind of read' in str(exc)
t('NQ3: a changed NQ number is DIFFERENT and named by its path; a changed '
  'MNQ result is not compared; a last-digit float difference (another '
  'Python) is the same value; DEV against unblind is refused; a report '
  'from before the last wave was added is compared on the waves both '
  'hold, the missing wave named, a changed number still found',
  not r_planted['match'] and len(r_planted['diffs']) == 1 and
  r_planted['diffs'][0][0] == 'reports/wave 14/results/NQ/test/n' and
  'DIFFERENT: 1 of' in CC.text(r_planted) and
  CC.compare(fullD, mnq_only)['match'] and
  CC.compare(nqD, noise)['match'] and refused and
  r_older['match'] and any(LAST in x and 'not compared' in x
                           for x in r_older['notes']) and
  not r_older_bad['match'] and
  [d[0] for d in r_older_bad['diffs']] ==
  ['reports/wave 14/results/NQ/test/n'])

# ---------------------------------------------------------------------
# NQ4: the two commands
# ---------------------------------------------------------------------
p_full = os.path.join(WORK, 'cp_full.json')
p_nq = os.path.join(WORK, 'cp_nq.json')
p_bad = os.path.join(WORK, 'cp_bad.json')
p_u = os.path.join(WORK, 'cp_u.json')
w6p = os.path.join(WORK, 'w6.json')
w9p = os.path.join(WORK, 'w9.json')
for path, doc in ((w6p, W6), (w9p, W9), (p_bad, planted), (p_u, fullU)):
    with open(path, 'w') as fh:
        json.dump(doc, fh, default=str)
buf = io.StringIO()
BM.l2_sweep_reclaim = _l2_plumbing
try:
    with redirect_stdout(buf):
        rc_f = CP.main([D, '--w6', w6p, '--a-ref', w9p, '--out', p_full])
        rc_n = CP.main([D, '--w6', w6p, '--a-ref', w9p, '--nq-only',
                        '--out', p_nq])
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
out_cp = buf.getvalue()
buf = io.StringIO()
with redirect_stdout(buf):
    rc_m = CC.main([p_full, p_nq])
    rc_d = CC.main([p_full, p_bad])
    rc_k = CC.main([p_full, p_u])
    rc_x = CC.main([p_full, os.path.join(WORK, 'missing.json')])
out_cc = buf.getvalue()
t('NQ4: `--nq-only` reads NQ alone and says so; the compare command exits '
  '0 on MATCH, 1 on DIFFERENT, 2 on a different kind of read or an '
  'unreadable file; neither writes a ledger on DEV',
  rc_f == rc_n == 0 and
  CP._load(p_nq, 'the NQ-only report')['instruments'] == ['NQ'] and
  'NQ only: MNQ\'s recordings are not read.' in out_cp and
  rc_m == 0 and rc_d == 1 and rc_k == 2 and rc_x == 2 and
  'MATCH: every NQ value agrees' in out_cc and
  'DIFFERENT: 1 of' in out_cc and 'not the same kind of read' in out_cc and
  not os.path.exists(os.path.join(WORK, CP.EXPOSURE_LEDGER)))

# ---------------------------------------------------------------------
# NQ5: the exposure ledger survives the checkpoint's run of records
# ---------------------------------------------------------------------
import mrofyt_ledgers as LG          # noqa: E402
led = os.path.join(WORK, 'exposed.json')
with open(led, 'w') as fh:
    json.dump(dict(exposed_days=[dict(session='20260901', label='X',
                                      exposed_by='pilot',
                                      bulk_csv_present=True)]), fh)
after = []
for k in range(16):
    n = LG.record_exposure(dict(sessions_inspected=['20260901', '20260921',
                                                   '20260922']),
                           led, 'W%02d' % k)
    with open(led) as fh:
        after.append((n, json.load(fh)))
days = {d['session']: d for d in after[-1][1]['exposed_days']}
raw = open(led).read()
t('NQ5: sixteen records in a row, as the checkpoint writes them, each read '
  'back the one before: every earlier day and version kept, the file '
  'complete after every call, the bytes those of json.dump',
  all(n == 3 for n, _d in after) and set(days) == {'20260901', '20260921',
                                                   '20260922'} and
  days['20260901']['bulk_csv_present'] is True and
  days['20260921']['also_exposed_by'] == ['W%02d' % k for k in range(16)]
  and raw == json.dumps(after[-1][1], indent=1))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
