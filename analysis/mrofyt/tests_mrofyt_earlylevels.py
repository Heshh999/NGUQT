#!/usr/bin/env python3
# MROF-YT-W11-EARLYLEVELS-1.0 suite. Candle buckets, the confirmed
# swings and the three entries are exercised on hand-built candles and
# grids with known answers, and the pipeline end to end on synthetic
# recorder-format runs (mles_v12_synth). Synthetic events verify CODE
# BEHAVIOR only, never market evidence. No order, fill or P&L exists.
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
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_closereclaim as C  # noqa: E402
import mrofyt_earlylevels as E   # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w11_')
T0 = float(calendar.timegm((2026, 9, 2, 14, 30, 0)))     # 10:30 EDT

# ---------------------------------------------------------------------
# EL1-EL2: candles and confirmed swings
# ---------------------------------------------------------------------
k1, k4 = E.bucket(T0, 1), E.bucket(T0, 4)
t('EL1: 1-hour candles are Eastern hours and 4-hour candles start at '
  '18:00, 22:00, 02:00, 06:00, 10:00 and 14:00 ET: 10:30 EDT falls in the '
  '10:00 hour (ends 11:00) and the 10:00-14:00 block (ends 14:00)',
  E.bucket_end(k1, 1, T0) == T0 + 1800 and
  E.bucket_end(k4, 4, T0) == T0 + 3.5 * 3600 and
  E.bucket(T0 - 1800 - 1, 4) == k4 - 1 and E.bucket(T0 - 1800, 4) == k4)

K0 = E.bucket(T0 - 1800, 1)                  # the 10:00 ET hour
H0 = T0 - 1800
hi = [10, 11, 15, 12, 11, 12, 16, 9]
lo = [9, 10, 14, 11, 8, 10, 13, 8.5]
cl = [9.5, 10.5, 14.5, 11.5, 9, 12, 15.5, 9]
cands = {K0 + j: [hi[j], lo[j], cl[j], H0 + j * 3600 + 100]
         for j in range(8)}
sw = {s['kind']: s for s in E.htf_swings(cands, 1)}
gap = dict(cands)
del gap[K0 + 3]
t('EL2: a candle high above the 2 before and not below the 2 after is a '
  'swing high, a level from the close of the 2nd candle after until a '
  'later candle closes a tick beyond it; lows mirrored, never expiring '
  'here; a missing candle among the five gives no swing',
  set(sw) == {'SWING_H', 'SWING_L'} and sw['SWING_H']['price'] == 15 and
  sw['SWING_H']['t_on'] == H0 + 5 * 3600 and
  sw['SWING_H']['t_off'] == H0 + 7 * 3600 and
  sw['SWING_L']['price'] == 8 and sw['SWING_L']['t_on'] == H0 + 7 * 3600
  and sw['SWING_L']['t_off'] == float('inf') and
  not any(s['kind'] == 'SWING_H' and s['price'] == 15
          for s in E.htf_swings(gap, 1)))

g_sw = dict(t=H0 + 6 * 3600, session='20260902', w11_lv=())
lev = E._levels_at(g_sw, [dict(sw['SWING_H'], session='20260902',
                               ses_idx=0)], {'20260902': 0})
lev_late = E._levels_at(dict(g_sw, session='20260910'),
                        [dict(sw['SWING_H'], session='20260902', ses_idx=0,
                              t_off=float('inf'))],
                        {'20260902': 0, '20260910': 6})
t('EL2b: a swing counts as a group-A level while confirmed, not yet closed '
  'beyond, and within 5 more sessions of the one it was confirmed in',
  len(lev) == 1 and lev[0][2] == 'A' and lev[0][3] == 15 and
  lev_late == [])


# ---------------------------------------------------------------------
# EL3: the three entries by hand
# ---------------------------------------------------------------------
def mkgrid(spec):
    """spec: {t: (mid, D, z)} -> records with YDAY_HIGH = 100.0."""
    lv = tuple(100.0 if k == 'YDAY_HIGH' else None for k in E.FIXED_IDS)
    return [dict(t=float(tt), instrument='NQ', session='20260902', run='r1',
                 mid=m, D=D, z_delta_s=z, w11_lv=lv)
            for tt, (m, D, z) in sorted(spec.items())]


base = {tt: (99.0, 0.0, None) for tt in range(600, 1500, 10)}
spec1 = dict(base)
spec1[660] = (100.5, 10.0, 0.5)
for tt in range(670, 1500, 10):
    spec1[tt] = (99.5, -20.0, 1.5)
g1 = mkgrid(spec1)
gm1 = {int(g['t']): g for g in g1}
got = {m: E.run_episodes(g1, gm1, [], {'20260902': 0},
                         collections.Counter(), m) for m in E.MODES}
spec2 = dict(base)
spec2[660] = (100.5, 10.0, 0.5)
for tt in range(670, 1500, 10):
    spec2[tt] = (99.5, 5.0, 0.5)
spec2[990] = (99.5, -20.0, 2.0)
g2 = mkgrid(spec2)
gm2 = {int(g['t']): g for g in g2}
got2 = {m: E.run_episodes(g2, gm2, [], {'20260902': 0},
                          collections.Counter(), m) for m in E.MODES}
t('EL3: after a 10 s / one-minute close through at 660 and the flow '
  'flipping at 670: WICK and EARLY enter at 670, CLOSE at the reclaim '
  'close 720, all faded and first tests; with the flow only after the '
  'windows (990) none enters',
  [(e['t'], e['direction'], e['test_no'], e['group'], e['level_id'])
   for e in got['WICK']] == [(670.0, -1, 1, 'MAIN', 'YDAY_HIGH')] and
  [e['t'] for e in got['EARLY']] == [670.0] and
  [e['t'] for e in got['CLOSE']] == [720.0] and
  all(not v for v in got2.values()))

# ---------------------------------------------------------------------
# EL4-EL6: end to end on synthetic tape
# ---------------------------------------------------------------------


def _path(amp):
    return lambda i: 15000.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w11c%d' % i, session=ses,
                 seed=i)
rep5, r5 = E.run(D5, a_ref={'NQ': 100.0})
ev5 = E.all_events(r5)
mc = sorted((e['t'], e['level_id'], e['direction']) for e in ev5
            if e['group'] == 'MAIN' and e['mode'] == 'CLOSE')
wc = sorted((e['t'], e['level_id'], e['direction'])
            for e in C.close_events(r5) if e['flow'])
t('EL4: on the six MAIN levels the CLOSE entry is exactly wave ten\'s '
  'filtered reclaim (same instants, levels and sides)',
  mc == wc)
fam = rep5['tables']['NQ']
t('EL5: end to end: entries of every mode on the MAIN levels and on '
  'groups C and D (VWAP and pivots move through the synthetic swing); MAIN '
  'holds E1, E2 and five references; A six tests, B, C and D three; the '
  'scaled column is filled when A_ref is given; the validation session is '
  'refused; the report renders',
  {e['mode'] for e in ev5 if e['group'] == 'MAIN'} >= {'WICK', 'EARLY'} and
  {e['group'] for e in ev5} >= {'MAIN', 'C', 'D'} and
  all(e['direction'] == -e['b'] and e['test_no'] >= 1 for e in ev5) and
  [x['test'] for x in fam['MAIN']] == ['E1', 'E2', 'L2', 'L2F', 'C1', 'C2',
                                       'WM'] and
  len(fam['A']) == 6 and len(fam['B']) == len(fam['C']) ==
  len(fam['D']) == 3 and
  fam['MAIN'][0]['scaled_n'] > 0 and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'pivots' in E.text(rep5))
repN, _rN = E.run(D5)
repU, _rU = E.run(D5, unblind=True)
t('EL6: without A_ref the scaled column is empty and the tests unchanged; '
  'with --unblind only sessions after 20260918 are evaluated',
  repN['tables']['NQ']['MAIN'][0]['scaled_n'] == 0 and
  repN['tables']['NQ']['MAIN'][0]['n'] == fam['MAIN'][0]['n'] and
  all(s > E.DEV_END for s in repU['sessions_evaluated']))

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803')):
    SY.synth_run(D6, n_depth=30000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = E.run(D6, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_bad = E.main([D7, '--holdout'])
    rc_uh = E.main([D5, '--unblind', '--holdout'])
    rc_ref = E.main([D5, '--a-ref', os.devnull])
t('EL7: a replay holdout folder is read whole when every session is before '
  '2026-09-01 and STOPPED when it holds a recorded session; --unblind with '
  '--holdout and a file that is not wave nine\'s frozen A_ref are refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  rc_bad == 2 and rc_uh == 2 and rc_ref == 2 and
  'only sessions before 20260901' in buf.getvalue() and
  "not wave nine's frozen file" in buf.getvalue())

# ---------------------------------------------------------------------
# EL8-EL9: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = C.CloseRunner(D5)
ledA = rA.run()
rB = E.LevelsRunner(D5)
ledB = rB.run()
strip = lambda gs: [dict((k, v) for k, v in g.items()   # noqa: E731
                         if k != 'w11_lv') for g in gs]
t('EL8: the wave-eleven runner leaves wave ten\'s grid (with its levels), '
  'the fires and ranges and the wave-one ledger identical, and the signal '
  'module keeps its pinned hash',
  strip(rB.grid) == rA.grid and rB.w3_fires == rA.w3_fires and
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
r9a = E.LevelsRunner(d9a)
r9a.run()
r9b = E.LevelsRunner(d9b)
r9b.run()
_reg = open(os.path.join(HERE, E.REGISTRATION)).read()
t('EL9: an abandoned run is wound back whole (grid records with every '
  'group\'s levels), so it adds no entry; the registration states the '
  'groups, the swing rule, the three entries, the tests and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r9a.grid == r9b.grid and
  json.dumps(E.all_events(r9a), sort_keys=True) ==
  json.dumps(E.all_events(r9b), sort_keys=True) and
  all(w in _reg for w in ('HIGHER-TIMEFRAME SWINGS', 'OPENS', 'VWAP',
                          'PIVOTS', 'R1', '2 candles before it',
                          'more sessions', 'WICK', 'EARLY', 'CLOSE',
                          'E1', 'E2', '2026-09-01', 'Holm',
                          'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
