#!/usr/bin/env python3
# MROF-YT-W13-VALUEAREA-1.0 suite. The profile, the value area, the
# re-entry and the targets are exercised on hand-built trades, grids and
# paths with known answers, and the pipeline end to end on synthetic
# recorder-format runs (mles_v12_synth). Synthetic sessions last under an
# hour, so the end-to-end checks relax, INSIDE THIS SUITE ONLY, the
# completeness rule and the speed and flow conditions (plumbing), and
# restore them afterwards. Synthetic events verify CODE BEHAVIOR only,
# never market evidence. No order, fill or P&L exists.
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
import mrofyt_context as CX      # noqa: E402
import mrofyt_l2context as X     # noqa: E402
import mrofyt_valuearea as VA    # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w13_')
A = lambda xs: array.array('d', xs)     # noqa: E731
T930 = float(calendar.timegm((2026, 9, 2, 13, 30, 0)))      # 09:30 EDT

# ---------------------------------------------------------------------
# VA-1: the profile and the value area
# ---------------------------------------------------------------------
EMPTY = os.path.join(WORK, 'empty')
os.makedirs(EMPTY)
rr = VA.ValueRunner(EMPTY)
for dt, px, sz in ((-60, 15050.0, 99), (0, 15000.25, 10), (60, 15000.75, 30),
                   (120, 15001.5, 5), (3600, 14999.0, 4),
                   (6.5 * 3600 - 1, 15003.0, 1), (6.5 * 3600, 15100.0, 50)):
    rr._add_trade('NQ', '20260902', T930 + dt, px, sz)
prof = rr.profile[('NQ', '20260902')]
rr._finish_profile('NQ', '20260902')
rr._add_trade('NQ', '20260903', T930 + 86400 + 3600 * 1.5, 15000.0, 5)
rr._finish_profile('NQ', '20260903')
t('VA-1: only cash-session trades (09:30-15:59:59 ET) enter the profile, in '
  '1-point bins; the value area is the context study\'s; a session whose '
  'first cash trade is after 10:00 or last before 15:30 has none',
  dict(prof[0]) == {15000: 40.0, 15001: 5.0, 14999: 4.0, 15003: 1.0} and
  prof[1] == 9.5 * 3600 and prof[2] == 16 * 3600 - 1 and
  rr.values['NQ']['20260902'] == CX.value_area(
      {15000: 40.0, 15001: 5.0, 14999: 4.0, 15003: 1.0}) and
  '20260903' not in rr.values['NQ'])
vals = {'20260902': (1, 2, 0), '20260904': (5, 6, 4)}
t('VA-2: yesterday\'s value area is the latest earlier session that has one',
  VA.prev_value(vals, '20260905') == (5, 6, 4) and
  VA.prev_value(vals, '20260903') == (1, 2, 0) and
  VA.prev_value(vals, '20260902') is None)


# ---------------------------------------------------------------------
# VA-3: the event by hand
# ---------------------------------------------------------------------
def runner_with(grid, values):
    r = types.SimpleNamespace(grid=grid, values=values)
    return r


def mk(spec, t0=T930 + 1800):
    return [dict(t=t0 + dt, instrument='NQ', session='20260903', run='r1',
                 mid=m, D=D, z_delta_s=z) for dt, (m, D, z) in
            sorted(spec.items())]


V903 = {'NQ': {'20260902': (100.0, 110.0, 90.0)}}         # POC VAH VAL
base = {dt: (105.0, 0.0, None) for dt in range(0, 400, 10)}
fast = dict(base)
fast[100] = (112.0, 5.0, 0.5)                              # out (>= 2 pts)
fast[110] = (113.0, 5.0, 0.5)
fast[120] = (113.0, 5.0, 0.5)
fast[130] = (112.5, -10.0, 1.0)
fast[140] = (109.0, -30.0, 2.5)                            # back, 4+ in 30 s
slow = dict(fast)
slow[110], slow[120], slow[130] = (112.0, 0, None), (111.0, 0, None), \
    (110.5, 0, None)
slow[140] = (109.75, -30.0, 2.5)                           # moved 2.25 only
weak = dict(fast)
weak[140] = (109.0, -30.0, 1.5)
late = mk(fast, T930 + 6.5 * 3600 - 1800)                  # 15:30 onward
ev_fast = VA.va_events(runner_with(mk(fast), V903))
t('VA-3: out at least 2 points above VAH, back below VAH by a tick after a '
  '4-point move in 30 s with aggression into value at z >= 2: one trade, '
  'short, at that tick, carrying yesterday\'s POC / VAH / VAL; too slow, '
  'too weak, or after 15:30: none',
  [(e['t'], e['direction'], e['b'], e['poc'], e['vah'], e['val'])
   for e in ev_fast] == [(T930 + 1800 + 140, -1, 1, 100.0, 110.0, 90.0)]
  and VA.va_events(runner_with(mk(slow), V903)) == [] and
  VA.va_events(runner_with(mk(weak), V903)) == [] and
  VA.va_events(runner_with(late, V903)) == [] and
  VA.va_events(runner_with(mk(fast), {'NQ': {}})) == [])

# ---------------------------------------------------------------------
# VA-4: targets
# ---------------------------------------------------------------------
t('VA-4: POC and the far edge are targets when at least 2 points ahead '
  '(no cap), else the fixed 25',
  VA.structure_target(-1, 109.0, 100.0) == (36.0, True) and
  VA.structure_target(-1, 109.0, 90.0) == (76.0, True) and
  VA.structure_target(-1, 109.0, 108.0) == (100.0, False) and
  VA.structure_target(1, 91.0, 110.0) == (76.0, True) and
  VA.structure_target(1, 91.0, 85.0) == (100.0, False))

# ---------------------------------------------------------------------
# VA-5..VA-6: end to end (plumbing)
# ---------------------------------------------------------------------


def _path(amp):
    return lambda i: 15000.0 + amp * math.sin(2 * math.pi * (i * 0.05) /
                                              900.0)


SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260909', '20260910', '20260921')
D5 = os.path.join(WORK, 'e2e')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(D5, n_depth=60000, dt_step=0.05, price_path=_path(30 + 3 * i),
                 trade_every=10, quote_every=5, cid='w13c%d' % i, session=ses,
                 seed=i)
_KEEP = (VA.COMPLETE_LAST, VA.SPEED_TICKS, VA.FLOW_Z)
VA.COMPLETE_LAST, VA.SPEED_TICKS, VA.FLOW_Z = 0.0, -1e9, -1e9
try:
    rep5, r5 = VA.run(D5, a_ref={'NQ': 100.0})
    ev5 = VA.va_events(r5)
    sc5 = VA.score(r5, ev5, {'NQ': 100.0})
    repN, _rN = VA.run(D5)
    repU, _rU = VA.run(D5, unblind=True, a_ref={'NQ': 100.0})
finally:
    VA.COMPLETE_LAST, VA.SPEED_TICKS, VA.FLOW_Z = _KEEP
nq = {x['test']: x for x in rep5['tests'].get('NQ', [])}
t('VA-5: end to end: value areas from real trades, re-entries faded into '
  'value, four versions per trade on the same stop; VA1 to VA4 scored; '
  'without --a-ref VA4 is not tested; the validation session refused; the '
  'report renders',
  len(r5.values['NQ']) >= 5 and ev5 and
  all(e['direction'] == -e['b'] and e['val'] <= e['poc'] <= e['vah']
      for e in ev5) and
  sc5 and all(set(res) == {'FIXED', 'POC', 'FAR', 'SCALED'}
              for _e, res, _m in sc5) and
  set(nq) == {'VA1', 'VA2', 'VA3', 'VA4'} and nq['VA1']['n'] == len(
      [x for x in sc5 if x[0]['instrument'] == 'NQ']) and
  'no --a-ref' in {x['test']: x for x in
                   repN['tests']['NQ']}['VA4']['status'] and
  rep5['sessions_refused'] == ['20260921'] and
  json.dumps(rep5, default=str) and 'VA4' in VA.text(rep5) and
  all(s > VA.DEV_END for s in repU['sessions_evaluated']))

D6 = os.path.join(WORK, 'replay')
for i, ses in enumerate(('20260730', '20260731', '20260803')):
    SY.synth_run(D6, n_depth=30000, dt_step=0.05, price_path=_path(30 + i),
                 trade_every=10, quote_every=5, cid='rp%d' % i, session=ses,
                 seed=i)
repH, _rH = VA.run(D6, holdout=True)
D7 = os.path.join(WORK, 'replay_bad')
shutil.copytree(D6, D7)
SY.synth_run(D7, n_depth=20000, dt_step=0.05, price_path=_path(30),
             trade_every=10, quote_every=5, cid='late', session='20260902',
             seed=9)
buf = io.StringIO()
with redirect_stdout(buf):
    rc_bad = VA.main([D7, '--holdout'])
    rc_uh = VA.main([D5, '--unblind', '--holdout'])
    rc_ref = VA.main([D5, '--a-ref', os.devnull])
t('VA-6: a replay holdout folder is read whole when every session is before '
  '2026-09-01 and STOPPED when it holds a recorded session; --unblind with '
  '--holdout and a file that is not wave nine\'s A_ref are refused',
  repH['holdout'] and repH['sessions_inspected'][0] == '20260730' and
  rc_bad == 2 and rc_uh == 2 and rc_ref == 2 and
  'only sessions before 20260901' in buf.getvalue() and
  "not wave nine's frozen file" in buf.getvalue())

# ---------------------------------------------------------------------
# VA-7..VA-8: nothing frozen changed; an abandoned run leaves nothing
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
rA = X.ContextRunner(D5)
ledA = rA.run()
rB = VA.ValueRunner(D5)
ledB = rB.run()
t('VA-7: the wave-thirteen runner leaves wave twelve\'s fires, grid and '
  'ranges and the wave-one ledger identical, and the signal module keeps '
  'its pinned hash',
  rB.w3_fires == rA.w3_fires and rB.grid == rA.grid and
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
VA.COMPLETE_LAST = 0.0
try:
    r9a = VA.ValueRunner(d9a)
    r9a.run()
    r9b = VA.ValueRunner(d9b)
    r9b.run()
finally:
    VA.COMPLETE_LAST = _KEEP[0]
_reg = open(os.path.join(HERE, VA.REGISTRATION)).read()
t('VA-8: an abandoned run\'s trades leave the profile, so the value areas '
  'match the clean folder; the registration states the profile, the '
  'speed and flow rule, the four tests, the holdout rule and Holm',
  r9a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  dict(r9a.values) == dict(r9b.values) and len(r9b.values['NQ']) == 3 and
  all(w in _reg for w in ('09:30:00–15:59:59 ET', '70 %', '2 points',
                          '4 points back toward value over the last 30 s',
                          'z_delta_s >= 2.0', 'VA1', 'VA4', 'SCALED',
                          '2026-09-01', 'Holm over the four',
                          'Explicitly NOT registered')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
