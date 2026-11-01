#!/usr/bin/env python3
# MROF-YT-W14-L2FIRSTSIGNAL-1.0 suite. The first-signal rule and the
# verdict are exercised on hand-built events and trades with known
# answers, the DEV row is reproduced from the saved DEV report, and the
# pipeline runs end to end on synthetic recorder-format runs
# (mles_v12_synth) with wave six's suite-only plumbing L2 detector
# (synthetic flow never flips, so the frozen L2 never fires on it),
# restored afterwards. Synthetic events verify CODE BEHAVIOR only, never
# market evidence. No order, fill or P&L exists.
import collections
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
import mrofyt_l2firstsignal as FS    # noqa: E402
import mrofyt_l2variants as V        # noqa: E402
import mrofyt_levelbreak as LB       # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w14_')

# ---------------------------------------------------------------------
# FS1: the first signal at a level, by hand
# ---------------------------------------------------------------------
E = lambda inst, ses, t_, *lv: dict(instrument=inst, session=ses,  # noqa
                                    t=float(t_), levels=list(lv))
evs = [E('NQ', '20260902', 10, 'YDAY_HIGH'),
       E('NQ', '20260902', 20, 'YDAY_HIGH'),              # second: no
       E('NQ', '20260902', 30, 'ON_LOW', 'YDAY_LOW'),     # first at both
       E('NQ', '20260902', 40, 'YDAY_LOW'),               # used at 30
       E('NQ', '20260902', 50, 'ON_HIGH', 'YDAY_HIGH'),   # YDAY_HIGH used
       E('NQ', '20260902', 60, 'ON_HIGH'),                # used at 50
       E('NQ', '20260902', 70),                           # no level
       E('NQ', '20260903', 5, 'YDAY_HIGH'),               # new session
       E('MNQ', '20260902', 15, 'YDAY_HIGH')]             # other market
fs = FS.first_signals(list(reversed(evs)))
t('FS1: per instrument and session, in time order, an event is taken '
  'only when none of its levels has had an L2 earlier; every event uses '
  'up all its levels, taken or not; no level, never taken',
  [(e['instrument'], e['session'], e['t']) for e in fs] ==
  [('MNQ', '20260902', 15.0), ('NQ', '20260902', 10.0),
   ('NQ', '20260902', 30.0), ('NQ', '20260903', 5.0)])


# ---------------------------------------------------------------------
# FS2: the verdict, by hand
# ---------------------------------------------------------------------
def trades(pattern, inst='NQ'):
    """pattern: [(session, 'WWL')] -> rows as score_variants gives them."""
    rows, k = [], 0
    for ses, s in pattern:
        for c in s:
            k += 1
            e = dict(instrument=inst, session=ses, t=float(k))
            rows.append((e, 'TARGET' if c == 'W' else 'STOP',
                         100.0 if c == 'W' else -60.0, 60.0, 100.0))
    return rows


ses = ['202609%02d' % d for d in range(1, 31)]
few = FS.verdict(trades([(ses[0], 'W' * 29)]), 'NQ')
good = FS.verdict(trades([(s, 'WWL' if i % 3 else 'WLL')
                          for i, s in enumerate(ses[:12])]), 'NQ')
oneday = FS.verdict(trades([(ses[0], 'W' * 15)] +
                           [(s, 'WLL') for s in ses[1:11]]), 'NQ')
loses = FS.verdict(trades([(s, 'WLL') for s in ses[:12]]), 'NQ')
mnq = FS.verdict(trades([(s, 'WWL') for s in ses[:12]], 'MNQ'), 'MNQ')
t('FS2: under 30 NQ trades no verdict; PASS needs the 95 % range above 0 '
  'and a profit without the best day; one big day, or a loss, is NOT '
  'PROVEN with its reason; MNQ is described, never tested',
  few['status'] == 'NOT ENOUGH TRADES' and
  good['status'] == 'PASS' and good['n'] == 36 and
  good['ci95_net_ticks'][0] > 0 and
  good['without_best_day']['net_points'] > 0 and
  oneday['status'] == 'NOT PROVEN' and oneday['net_points'] > 0 and
  any('one day' in r and ses[0] in r for r in oneday['reasons']) and
  oneday['without_best_day']['session'] == ses[0] and
  loses['status'] == 'NOT PROVEN' and
  loses['reasons'][0] == 'loses after costs' and
  mnq['status'] == 'DESCRIBED (not tested)' and
  sum(d['trades'] for d in good['by_day']) == 36 and
  sum(d['wins'] for d in good['by_day']) == 20)

# ---------------------------------------------------------------------
# FS3: the registration's DEV row from the saved DEV report
# ---------------------------------------------------------------------
w3 = json.load(gzip.open(os.path.join(HERE, 'frozen_dev_20261024',
                                      'w3.json.gz'), 'rt'))
rows3 = CO.scored(w3['events'], 'L2', 'NQ', '60')
ids3 = {id(e) for e in FS.first_signals([e for e, _sc in rows3])}
take3 = CO.one_at_a_time([x for x in rows3 if id(x[0]) in ids3])
net3 = [(sc['value_ticks'] - CO.cost_ticks('NQ', sc['outcome'])) / 4.0
        for _e, sc in take3]
seen3, old3 = collections.Counter(), []
for e, sc in sorted(rows3, key=lambda x: x[0]['t']):
    seen3[(e['session'], tuple(e['levels']))] += 1
    if seen3[(e['session'], tuple(e['levels']))] == 1:
        old3.append(sc)
reg = open(os.path.join(HERE, FS.REGISTRATION)).read()
t('FS3: on the saved DEV report the rule gives the registration\'s row: '
  '12 NQ trades one at a time, 7 won, +9.44 net a trade over 6 sessions; '
  'keyed by the set of levels instead it gives the earlier 13',
  len(take3) == 12 and
  sum(1 for _e, sc in take3 if sc['outcome'] == 'TARGET') == 7 and
  round(sum(net3) / len(net3), 2) == 9.44 and
  len({e['session'] for e, _sc in take3}) == 6 and len(old3) == 13 and
  '| **this rule** (§2) | 12 | 7 (58 %) | +9.44 | 6 |' in reg)

# ---------------------------------------------------------------------
# FS4-FS6: end to end on synthetic tape (plumbing L2)
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
                 trade_every=10, quote_every=5, cid='w14c%d' % i, session=s,
                 seed=i)
BM.l2_sweep_reclaim = _l2_plumbing
_min = FS.MIN_TRADES
try:
    repD, rD = FS.run(D5)
    evD = [e for e in V.variant_events(rD) if e['session'] <= FS.DEV_END]
    scD = V.score_variants(rD, evD)
    repU, _rU = FS.run(D5, unblind=True)
    FS.MIN_TRADES = 1                       # suite only: a verdict shown
    repU1, _rU1 = FS.run(D5, unblind=True)
    rW = V.L2VariantRunner(D5)
    rW.run()
finally:
    BM.l2_sweep_reclaim = _FROZEN_L2
    FS.MIN_TRADES = _min
fsD = FS.first_signals(evD)
keysD = [(e['instrument'], e['session'], lv) for e in fsD
         for lv in e['levels']]
nqD = repD['results']['NQ']['test']
t('FS4: end to end on DEV: the test\'s trades are first signals, each level '
  'at most once a session, one at a time, a subset of every L2; the '
  'beside rows are wave eight\'s V0 and V1; the validation session is '
  'refused; the report renders',
  evD and fsD and len(keysD) == len(set(keysD)) and
  len(fsD) < len(evD) and
  nqD['first_signals'] == sum(1 for e in fsD if e['instrument'] == 'NQ')
  and 0 < nqD['n'] <= nqD['first_signals'] and
  repD['results']['NQ']['every']['n'] == len(V.one_at_a_time(
      [x for x in scD['V0'] if x[0]['instrument'] == 'NQ'])) and
  repD['results']['NQ']['touch']['n'] == len(V.one_at_a_time(
      [x for x in scD['V1'] if x[0]['instrument'] == 'NQ'])) and
  'DEV, seen before the registration' in nqD['status'] and
  repD['sessions_refused'] == ['20260921'] and not repD['withheld'] and
  'FIRST SIGNAL AT A LEVEL (the test)' in FS.text(repD) and
  json.dumps(repD, default=str))

blob = json.dumps(repU, default=str)
nqU1 = repU1['results']['NQ']['test']
t('FS5: a held-out read with fewer than 30 NQ trades shows the count and '
  'days only -- no win rate, points, days or beside rows on screen or in '
  'the file; with enough trades the verdict and the table are shown',
  repU['withheld'] and repU['sessions_evaluated'] == ['20260921'] and
  all(k not in blob for k in ('"hit"', 'net_points', 'by_day', '"every"',
                              '"touch"', 'ci95')) and
  'results withheld until a read holds 30' in FS.text(repU) and
  'won ' not in FS.text(repU) and
  not repU1['withheld'] and nqU1['status'] in ('PASS', 'NOT PROVEN') and
  'VERDICT' in FS.text(repU1) and 'by_day' in nqU1)

buf = io.StringIO()
with redirect_stdout(buf):
    rc_uh = FS.main([D5, '--unblind', '--holdout'])
led = os.path.join(WORK, 'exposed.json')
FS.record_exposure(dict(sessions_inspected=['20260921']), led)
L = json.load(open(led))
t('FS6: wave fourteen\'s runner is wave eight\'s (same fires and grid); '
  '--unblind with --holdout is refused; the exposure ledger names wave '
  'fourteen; the registration states the rule, the verdict and the '
  'withholding',
  rD.w3_fires == rW.w3_fires and rD.grid == rW.grid and
  rD.ledger['wave14']['version'] == FS.W14_VERSION and rc_uh == 2 and
  L['exposed_days'][0]['exposed_by'] == FS.W14_VERSION and
  all(w in reg for w in ('none of its levels has had an L2 event',
                         'One position at a', 'PASS', 'NOT PROVEN',
                         'results withheld', 'Explicitly NOT registered',
                         'Still no\n  live orders')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
