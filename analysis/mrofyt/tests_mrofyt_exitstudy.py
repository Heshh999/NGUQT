#!/usr/bin/env python3
# MROF-YT-W5-EXIT-1.0 suite. The exit study is exercised on hand-built
# paths and records, on planted-effect datasets and pure noise, and the
# runner on synthetic recorder-format runs (mles_v12_synth). Synthetic
# events verify CODE BEHAVIOR only, never market evidence. No order,
# fill or P&L exists anywhere.
import array
import hashlib
import io
import json
import math
import os
import random
import shutil
import sys
import tempfile
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_exitstudy as EX    # noqa: E402
import mrofyt_pilot as PI        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w5_')
TK = 0.25

# ---------------------------------------------------------------------
# E1: the reference hold
# ---------------------------------------------------------------------
ts = array.array('d', [0, 10, 20, 30, 40, 50])
ps = array.array('d', [100.0, 105.0, 110.0, 104.0, 99.75, 120.0])
a = EX.trail_hold(ts, ps, 0, 1)
b = EX.trail_hold(array.array('d', [0, 10, 20]),
                  array.array('d', [100.0, 104.0, 80.0]), 0, 1)
c = EX.trail_hold(array.array('d', [0, 900, 1799, 1800, 1900]),
                  array.array('d', [100.0, 103.0, 101.0, 102.0, 50.0]), 0, 1)
d_ = EX.trail_hold(array.array('d', [0, 100, 200]),
                   array.array('d', [100.0, 102.0, 101.0]), 0, 1)
e_ = EX.trail_hold(ts, array.array('d', [100.0, 95.0, 90.0, 96.0, 100.25,
                                         80.0]), 0, -1)
t('E1: the 10-point trail exits at the first mid 40 ticks off the best '
  '(a gap exits at the mid that crossed), times out at 1800 s on the '
  'last mid at or before it, is UNRESOLVED when the run ends first, and '
  'mirrors for shorts',
  a == ('TRAIL', -1.0, 40.0) and b == ('TRAIL', -80.0, 20.0) and
  c == ('TIMEOUT', 8.0, 1800.0) and d_ == ('UNRESOLVED', None, None) and
  e_ == ('TRAIL', -1.0, 40.0))


def brute_trail(ts, ps, i, d):
    best = ps[i]
    for j in range(i + 1, len(ps)):
        if ts[j] > ts[i] + EX.HOLD_LIMIT_S:
            break
        if d * (ps[j] - best) > 0:
            best = ps[j]
        elif d * (best - ps[j]) >= 40 * TK - 1e-9:
            return ('TRAIL', d * (ps[j] - ps[i]) / TK)
    if ts[-1] < ts[i] + EX.HOLD_LIMIT_S:
        return ('UNRESOLVED', None)
    k = max(j for j in range(len(ts)) if ts[j] <= ts[i] + EX.HOLD_LIMIT_S)
    return ('TIMEOUT', d * (ps[k] - ps[i]) / TK)


rng = random.Random(5)
mism = checks = 0
for trial in range(80):
    tt, p = 0.0, 20000.0
    T, P = array.array('d'), array.array('d')
    for _ in range(rng.choice([50, 400, 1500])):
        tt += rng.choice([0.5, 2.0, 15.0, 60.0])
        p += rng.choice([-1, 1]) * TK * rng.choice([1, 1, 2, 4, 12])
        T.append(tt)
        P.append(p)
    for i in rng.sample(range(len(P)), min(10, len(P))):
        for d in (1, -1):
            checks += 1
            x = EX.trail_hold(T, P, i, d)
            if (x[0], x[1]) != brute_trail(T, P, i, d):
                mism += 1
t('E1b: trail_hold equals a plain re-implementation on %d random-walk '
  'checks, both directions' % checks, checks > 1000 and mism == 0)

# ---------------------------------------------------------------------
# E2: being in a run
# ---------------------------------------------------------------------
up = [(k * 10, 15000.0 + 20.0 * k / 180.0) for k in range(181)]
rs = EX.run_state(up, 1800, up[-1][1])
t('E2: a steady 20-point rise over 30 minutes is a long run at its best '
  '(gain 80 ticks, stall 0, anchored at the start)',
  rs == (1, 80.0, 0, 0))
t('E2b: fewer than 171 grid mids in the window is never a run',
  EX.run_state(up[-170:], 1800, up[-1][1])[0] == 0)
back = up[:150] + [(k * 10, up[149][1] - 6.0) for k in range(150, 181)]
t('E2c: 6 points off the best is outside the 5-point band: not in a run',
  EX.run_state(back, 1800, back[-1][1])[0] == 0)
dn = [(k, 2 * 15000.0 - m) for k, m in up]
rd = EX.run_state(dn, 1800, dn[-1][1])
t('E2d: the mirror image is a short run', rd == (-1, 80.0, 0, 0))
flat_top = [(k * 10, 15000.0 + 25.0 * min(k, 119) / 119.0)
            for k in range(181)]
fs = EX.run_state(flat_top, 1800, flat_top[-1][1])
t('E2e: the stall counts from the EARLIEST tick at the best, and a tie '
  'at the low anchors at the LATEST tick',
  fs[0] == 1 and fs[1] == 100.0 and fs[2] == 1800 - 1190 and
  EX.run_state([(0, 100.0), (5, 100.0)] + [(k * 10, 100.0 + 25.0 * k / 180)
                                            for k in range(1, 181)],
               1800, 125.0)[3] == 5)

# ---------------------------------------------------------------------
# E3: the eight signs
# ---------------------------------------------------------------------
cuts = dict(absorb=50.0, other=40.0, book=0.3, climax=100.0, biglot=30.0)
base = dict(D=0.0, D60=10.0, n10=20.0, n10_prev_mean=20.0, resp=4.0,
            bi3=0.0, stall_s=0, n10_prev6_max=20.0, lot_up=1.0, lot_dn=1.0)


def fires(**kw):
    g = dict(base)
    g.update(kw)
    return sorted(k for k, v in EX.signs_at(g, 1, cuts).items() if v)


t('E3: each sign fires on its own condition and nothing else does: X1 '
  'delta turns, X2 tape halves, X3 heavy buying without progress, X4 '
  'heavy selling, X5 book leans against, X6 120 s stall, X7 climax then '
  'quiet at a fresh best, X8 a large lot against',
  fires() == [] and fires(D60=0.0) == ['X1'] and
  fires(n10=10.0) == ['X2'] and fires(D=60.0, resp=1.0) == ['X3'] and
  fires(D=60.0, resp=2.0) == [] and fires(D=-45.0) == ['X4'] and
  fires(bi3=-0.4) == ['X5'] and fires(stall_s=120) == ['X6'] and
  fires(n10_prev6_max=120.0, n10=60.0, stall_s=30) == ['X7'] and
  fires(n10_prev6_max=120.0, n10=60.0, stall_s=90) == [] and
  fires(lot_dn=30.0) == ['X8'] and fires(lot_up=99.0) == [])
t('E3b: a missing input never fires (None, not False)',
  EX.signs_at(dict(base, D60=None), 1, cuts)['X1'] is None and
  EX.signs_at(dict(base, bi3=None), 1, cuts)['X5'] is None and
  EX.signs_at(base, 1, {})['X4'] is None)


# ---------------------------------------------------------------------
# E4-E5: the engine on planted effects and on noise
# ---------------------------------------------------------------------
def make(planted, seed=3, n_ses=14, per=500):
    rg = random.Random(seed)
    recs, holds = [], []
    for s in range(n_ses):
        ses = '202609%02d' % (s + 1)
        for k in range(per):
            g = dict(session=ses, t=1e9 + s * 86400 + k * 10.0,
                     hour=10 + (k % 5), instrument='NQ', run='r%d' % s,
                     run_dir=rg.choice([1, -1]) if rg.random() < 0.6 else 0,
                     D=rg.gauss(0, 20), D60=rg.gauss(5, 30),
                     n10=float(rg.randint(5, 40)),
                     n10_prev_mean=float(rg.randint(15, 30)),
                     resp=rg.gauss(1, 3), bi3=rg.uniform(-1, 1),
                     stall_s=rg.choice([0, 10, 30, 60, 90, 130, 200]),
                     n10_prev6_max=float(rg.randint(10, 60)),
                     lot_up=float(rg.randint(1, 20)),
                     lot_dn=float(rg.randint(1, 20)))
            v = rg.gauss(0, 30)
            if planted and g['run_dir'] and g['stall_s'] >= 120:
                v -= 25.0
            recs.append(g)
            holds.append(('TRAIL', v, 60.0) if g['run_dir'] else None)
    return EX.ExitData(recs, holds)


dsP = make(True)
cutP = EX.quantile_cuts(dsP.recs, dsP.moments)
testsP = EX.study(dsP, cutP)
byP = {x['sign']: x for x in testsP}
nomP = EX.nominate(testsP)
t('E4: a planted exit edge (holding after a 120 s stall is worth 25 '
  'ticks less) is found: X6 is an EXIT SIGN with negative lift in both '
  'halves, and it is nominated first',
  byP['X6']['status'] == 'EXIT SIGN' and byP['X6']['lift_ticks'] < -15 and
  byP['X6']['both_halves_negative'] and nomP and nomP[0]['sign'] == 'X6')
dsN = make(False, seed=8)
testsN = EX.study(dsN, EX.quantile_cuts(dsN.recs, dsN.moments))
t('E5: on pure noise no sign survives Holm and nothing is nominated',
  not any(x['survives_holm'] for x in testsN) and
  EX.nominate(testsN) == [])
evX6 = EX.sign_events(dsP, 'X6', cutP)
gap_ok = True
last = {}
for k, d in evX6:
    g = dsP.recs[k]
    key = (g['session'], d)
    if key in last and g['t'] - last[key] <= EX.COOLDOWN_S:
        gap_ok = False
    last[key] = g['t']
t('E5b: sign events are de-duplicated with the anchored 300 s cooldown '
  'per (session, direction)', evX6 and gap_ok)

# ---------------------------------------------------------------------
# E6-E9: the runner end to end on synthetic tape
# ---------------------------------------------------------------------
d6 = os.path.join(WORK, 'e2e')
path6 = lambda i: 15000.0 + 30.0 * math.sin(2 * math.pi * (i * 0.05) / 900.0)  # noqa: E731
SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260921')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(d6, n_depth=60000, dt_step=0.05, price_path=path6,
                 trade_every=10, quote_every=5, cid='w5c%d' % i,
                 session=ses, seed=i)
buf = io.StringIO()
with redirect_stdout(buf):
    rc = EX.main([d6, '--unblind', '--out', os.path.join(WORK, 'x.json')])
t('E6: --unblind without --evaluate is refused before anything is read',
  rc == 2 and 'REFUSED' in buf.getvalue() and
  not os.path.exists(os.path.join(WORK, 'x.json')))
rep, nom, r6 = EX.run_study(d6)
keys5 = ('n10', 'lot_up', 'lot_dn', 'bi3', 'n10_prev_mean',
         'n10_prev6_max', 'run_dir', 'run_gain', 'stall_s', 'run_anchor')
inrun = [g for g in r6.grid if g.get('run_dir')]
t('E6b: the study reads DEV only (the validation session is refused), '
  'every grid record carries the run state and sign inputs, in-run '
  'moments exist, the report states eight tests and serializes, and its '
  'text renders',
  rep['sessions_refused'] == ['20260921'] and
  not any(g['session'] > EX.DEV_END for g in r6.grid) and
  all(k in g for g in r6.grid for k in keys5) and len(inrun) > 100 and
  len(rep['instruments']['NQ']['tests']) == 8 and
  rep['rules']['n_tests'] == 8 and json.dumps(rep, default=str) and
  'HALF-LIFE' in EX.text_study(rep))

# E7: causality
d7 = os.path.join(WORK, 'cut')
for i, ses in enumerate(SESSIONS[:-1]):
    SY.synth_run(d7, n_depth=(30000 if ses == '20260908' else 60000),
                 dt_step=0.05, price_path=path6, trade_every=10,
                 quote_every=5, cid='w5c%d' % i, session=ses, seed=i)
r7 = EX.ExitRunner(d7)
r7.run()
full = {(g['session'], g['t']): g for g in r6.grid
        if g['session'] == '20260908'}
cut = [g for g in r7.grid if g['session'] == '20260908']
t('E7: causal by construction -- with the last DEV session cut in half, '
  'the run state and every sign input of every tick that still exists '
  'is identical to the full tape\'s',
  cut and len(cut) < len(full) and
  all((g['session'], g['t']) in full and
      all(g.get(k) == full[(g['session'], g['t'])].get(k) for k in keys5)
      for g in cut))


# E8: an abandoned run leaves nothing
def _late_corrupt_folder(d, good, bad, path, **kw):
    for i, ses in enumerate(good):
        SY.synth_run(d, session=ses, cid='g%d' % i, seed=i, price_path=path,
                     **kw)
    if bad is None:
        return
    mp = SY.synth_run(d, session=bad, cid='bad', seed=99, price_path=path,
                      **kw)
    man = json.load(open(mp))
    dp = os.path.join(d, man['depth']['file'])
    rows = open(dp).read().splitlines(True)
    k = int(len(rows) * 0.9)
    rows[k] = ',' * 3 + ' ' * (len(rows[k]) - 4) + '\n'
    open(dp, 'w').writelines(rows)
    assert os.path.getsize(dp) == man['depth']['bytes']


_G8 = ('20260901', '20260902', '20260903')
d8a, d8b = os.path.join(WORK, 'e8_bad'), os.path.join(WORK, 'e8_ref')
kw8 = dict(n_depth=40000, dt_step=0.05, trade_every=10, quote_every=5)
_late_corrupt_folder(d8a, _G8, '20260904', path6, **kw8)
_late_corrupt_folder(d8b, _G8, None, path6, **kw8)
r8a = EX.ExitRunner(d8a)
r8a.run()
r8b = EX.ExitRunner(d8b)
r8b.run()
t('E8: an abandoned run is wound back whole in wave five -- grid records '
  'with the run state, the wave-five history and wave four\'s equal a '
  'pass that never saw the run',
  r8a.ledger['totals'].get('runs_skipped_corrupt') == 1 and
  r8a.grid == r8b.grid and
  vars(r8a.w5hist['NQ']) == vars(r8b.w5hist['NQ']) and
  vars(r8a.w4hist['NQ']) == vars(r8b.w4hist['NQ']))

# E9: evaluate mode
fr = [dict(sign='X1', name=EX.SIGN_NAMES['X1'], cuts=rep['cuts'])]
repE, _rE = EX.run_evaluate(d6, fr, unblind=False)
repU, _rU = EX.run_evaluate(d6, fr, unblind=True)
st_dev = [x for x in rep['instruments']['NQ']['tests'] if x['sign'] == 'X1'][0]
ev_dev = repE['signs'][0]['result']['NQ']
led = os.path.join(WORK, 'ledger.json')
json.dump(dict(exposed_days=[dict(session='20260921',
                                  label=PI.BLIND_LABEL)]), open(led, 'w'))
EX.write_exposure_on_unblind(repU, led)
days = {x['session']: x for x in json.load(open(led))['exposed_days']}
t('E9: --evaluate on DEV reproduces the study\'s numbers for a frozen '
  'sign and calls it a reproduction; with --unblind it evaluates ONLY '
  'the validation session and the ledger marks it exposed by wave five',
  ev_dev['n'] == st_dev['n'] and ev_dev['lift_ticks'] == st_dev['lift_ticks']
  and 'reproduction' in repE['signs'][0]['verdict'] and
  repU['sessions_evaluated'] == ['20260921'] and
  days['20260921']['label'] == PI.EXPOSURE_LABEL and
  days['20260921']['exposed_by'] == EX.W5_VERSION and
  days['20260921'].get('previously_blind') is True)

# E10: half-life curves equal the pilot's own markout
hl = [c for c in rep['half_life'] if c['family'] == 'IN_RUN' and
      c['instrument'] == 'NQ'][0]
cells = EX._grid_markout_cells(r6, (60,))
ds6 = EX._by_inst(r6, EX.hold_values(r6))['NQ']
mom = [dict(instrument='NQ', run=ds6.recs[k]['run'], t=ds6.recs[k]['t'],
            direction=d, session=ds6.recs[k]['session'])
       for k, d in ds6.moments][::3]
man_n = man_s = 0.0
for e in mom:
    m = r6.markout('NQ', e['run'], e['t'], 60)
    h = int(EX.RUN.sod_seconds(e['t']) // 3600)
    b = cells.get(('NQ', h), {}).get(60)
    if m is None or b is None:
        continue
    man_n += 1
    man_s += e['direction'] * (m - b)
row60 = [x for x in hl['curve'] if x['horizon_s'] == 60][0]
t('E10: the half-life curve at 60 s equals a hand computation from the '
  'pilot\'s markout() against the hour cell',
  row60['n'] == man_n and
  abs(row60['lift_points'] - round(man_s / man_n / 4.0, 3)) < 1e-9)

# ---------------------------------------------------------------------
# E11: nothing frozen changed
# ---------------------------------------------------------------------
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
_led1 = PI.PilotRunner(d6, max_sessions=6).run()
_reg = open(os.path.join(HERE, 'MROF_YT_WAVE5_EXIT_REGISTRATION.md')).read()
t('E11: the wave-one ledger is byte-identical through the wave-five '
  'runner, the frozen signal module keeps its pinned hash, and the '
  'registration states the run, the trail, the eight signs, the '
  'cooldown, Holm over eight and the replay-folder rule',
  json.dumps({k: _led1.get(k) for k in _CMP}, sort_keys=True) ==
  json.dumps({k: r6.ledger.get(k) for k in _CMP}, sort_keys=True) and
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1' and
  '80 ticks' in _reg and '10-point' in _reg and 'BIG_LOT_AGAINST' in _reg
  and '300 s' in _reg and 'Holm over the **8**' in _reg and
  'Replay recordings' in _reg and 'Explicitly NOT registered' in _reg)

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
