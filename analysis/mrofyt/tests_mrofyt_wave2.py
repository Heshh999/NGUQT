#!/usr/bin/env python3
# MROF-YT-WAVE2-1.0 suite. Wave two is exercised on synthetic
# recorder-format runs (mles_v12_synth) plus hand-built feature dicts
# and bars. Synthetic events verify CODE BEHAVIOR only, never market
# evidence. No outcome, R or P&L exists anywhere.
import hashlib
import json
import math
import os
import random
import re
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_pilot as PI        # noqa: E402
import mrofyt_signals as SIG     # noqa: E402
import mrofyt_wave2 as W2        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w2_')
path = lambda i: 15000.0 + 3.0 * math.sin(2 * math.pi * (i * 0.0005) / 20.0)  # noqa: E731

# ---------------------------------------------------------------------
# W1: detectors are the frozen detectors with one input swapped
# ---------------------------------------------------------------------
rng = random.Random(7)


def rand_f():
    return dict(aggr_z=rng.choice([None, 0.5, 1.7, 2.0, 2.5, 3.1]),
                aggr_dir=rng.choice([1, -1]),
                progress_ticks=rng.choice([None, 0, 1, 2, 5]),
                opp_flip_z=rng.choice([None, 0.2, 1.0, 1.4]),
                returned_through_level=rng.choice([True, False]),
                sweep_reclaimed_5s=rng.choice([True, False]),
                replenish_z=rng.choice([None, 1.0, 1.5, 2.2]),
                approaches_60s=rng.choice([1, 2, 3]),
                retreat_ticks=rng.choice([None, 0, 1, 2]),
                resid_tail_5pct=None)


fs = [rand_f() for _ in range(2000)]
t('W1: W2-A4r equals the frozen A4 on 2000 random inputs (resid None), '
  'so "A4 as it ran" is exactly that',
  all(W2.w2_a4r(f) == SIG.a4_response_failure_reversal(f) for f in fs))

t('W1b: the parameterised a4() at threshold 2.0 IS the frozen A4, and '
  'with the residual key wired it honours a True tail exactly as the '
  'frozen detector does',
  all(W2.a4(f) == SIG.a4_response_failure_reversal(f) for f in fs) and
  all(W2.a4(dict(f, resid_tail_5pct=True)) ==
      SIG.a4_response_failure_reversal(dict(f, resid_tail_5pct=True))
      for f in fs))

t('W1c: W2-A1 is the frozen A1 with replenish_z replaced by repl10_z '
  'and nothing else',
  all(W2.w2_a1(dict(f, repl10_z=f['replenish_z'])) ==
      SIG.a1_absorption_reversal(f) for f in fs) and
  all(W2.w2_a1(dict(f, repl10_z=None, replenish_z=2.5)) == 0 for f in fs))

base = dict(aggr_z=1.7, aggr_dir=1, progress_ticks=0, opp_flip_z=1.2,
            returned_through_level=True, sweep_reclaimed_5s=False,
            resid_tail_5pct=None, level_id='CASH_OPEN_0930')
t('W1d: W2-A4r-z15 fires at aggr_z=1.7 where W2-A4r (2.0) does not, and '
  'both agree at 2.5',
  W2.w2_a4r(base) == 0 and W2.w2_a4r_z15(base) == -1 and
  W2.w2_a4r(dict(base, aggr_z=2.5)) == W2.w2_a4r_z15(dict(base, aggr_z=2.5))
  == -1)

hi = dict(base, aggr_z=2.5)
t('W1e: W2-A4-OPEN fires only inside 09:30-10:30 ET and only at the '
  'open/overnight levels',
  W2.w2_a4_open(hi, 9.5 * 3600 + 60) == -1 and
  W2.w2_a4_open(hi, 10.5 * 3600 + 1) == 0 and
  W2.w2_a4_open(hi, 9.0 * 3600) == 0 and
  W2.w2_a4_open(dict(hi, level_id='SESSION_VWAP'), 9.6 * 3600) == 0 and
  W2.w2_a4_open(dict(hi, level_id='OVERNIGHT_LOW'), 9.6 * 3600) == -1)

t('W1f: W2-A4r-HC reads aggr_z_hc, never aggr_z, and is silent when the '
  'HC baseline cannot speak',
  W2.w2_a4r_hc(dict(hi, aggr_z_hc=None)) == 0 and
  W2.w2_a4r_hc(dict(base, aggr_z_hc=2.4)) == -1 and
  W2.w2_a4r_hc(dict(hi, aggr_z_hc=1.0)) == 0)

# ---------------------------------------------------------------------
# W2: the residual model - prior sessions only, adverse tail
# ---------------------------------------------------------------------
rm = W2.ResidualModel()
r0 = random.Random(1)
# two prior sessions: r = 2 + 0.5*|D| + noise, aggressor frame
for _ses in range(2):
    for _ in range(60):
        D = r0.choice([-1, 1]) * r0.uniform(20, 200)
        r = (2.0 + 0.5 * abs(D) + r0.gauss(0, 1.0)) * (1 if D > 0 else -1)
        rm.observe(600.0, D, r)
    rm.close_session()
fit = rm.fit(rm.bucket(600.0))
t('W2: the model fits a robust slope/intercept close to the generating '
  'ones on prior data (b~0.5, a~2)',
  fit is not None and abs(fit['b'] - 0.5) < 0.1 and abs(fit['a'] - 2.0) < 1.5)

t('W2b: a response far BELOW expectation for its flow is in the adverse '
  'tail; one at expectation is not; the seller frame mirrors the buyer',
  rm.adverse_tail(600.0, 100.0, 52.0 - 30.0) is True and
  rm.adverse_tail(600.0, 100.0, 52.0) is False and
  rm.adverse_tail(600.0, -100.0, -(52.0 - 30.0)) is True and
  rm.adverse_tail(600.0, -100.0, -52.0) is False)

rm2 = W2.ResidualModel()
for _ in range(100):
    rm2.observe(600.0, 50.0, 30.0)               # current session only
t('W2c: observations from the CURRENT session never enter the fit until '
  'close_session, and below MIN_OBS the model says None rather than '
  'guessing',
  rm2.adverse_tail(600.0, 50.0, 0.0) is None and
  rm.adverse_tail(1200.0, 50.0, 0.0) is None)     # empty bucket

# ---------------------------------------------------------------------
# W3: W2-A4f population and resid_only accounting
# ---------------------------------------------------------------------
f_prog = dict(hi, resid_tail_5pct=False, progress_ticks=0)
f_resid = dict(hi, resid_tail_5pct=True, progress_ticks=4)
f_none = dict(hi, resid_tail_5pct=None, progress_ticks=0)
t('W3: W2-A4f fires on progress alone (resid_only=False), on the tail '
  'alone (resid_only=True), and NOT where the model cannot speak - '
  'even though A4r would',
  W2.w2_a4f(f_prog) == (-1, False) and W2.w2_a4f(f_resid) == (-1, True)
  and W2.w2_a4f(f_none) == (0, False) and W2.w2_a4r(f_none) == -1)

# ---------------------------------------------------------------------
# W4: ARM-B candle rules
# ---------------------------------------------------------------------
L = 15010.0
big_wick = ('k', 15000.0, 15016.0, 14999.0, 15003.0, 100)   # wick 6/17=.35
t('W4: B1 needs the wick beyond the level to be >= 50% of the range AND '
  'a close back on the approach side',
  W2.arm_b1(('k', 15000.0, 15020.0, 15005.0, 15006.0, 1), L, 1) == -1 and
  W2.arm_b1(big_wick, L, 1) == 0 and
  W2.arm_b1(('k', 15000.0, 15020.0, 15005.0, 15012.0, 1), L, 1) == 0 and
  W2.arm_b1(('k', 15020.0, 15021.0, 14996.0, 15014.0, 1), L, -1) == 1 and
  W2.arm_b1(('k', 15020.0, 15021.0, 15000.0, 15014.0, 1), L, -1) == 0 and
  W2.arm_b1(('k', 15000.0, 15020.0, 15005.0, 15006.0, 1, 12345.0), L, 1)
  == -1)                                  # 7-tuple from the runner cache

t('W4b: B2 needs bar1 to close THROUGH and bar2 to close back; direction '
  'is back toward the original side',
  W2.arm_b2(('k', 0, 0, 0, 15012.0, 0), ('k', 0, 0, 0, 15008.0, 0), L, 1)
  == -1 and
  W2.arm_b2(('k', 0, 0, 0, 15008.0, 0), ('k', 0, 0, 0, 15008.0, 0), L, 1)
  == 0 and
  W2.arm_b2(('k', 0, 0, 0, 15008.0, 0), ('k', 0, 0, 0, 15012.0, 0), L, -1)
  == 1)

# ---------------------------------------------------------------------
# W4c: the arm-B pipeline (register -> bar close -> fire) driven
# directly, so B1 and B2 fires are exercised without a cooperative tape
# ---------------------------------------------------------------------
import types                                                    # noqa: E402
d4 = os.path.join(WORK, 'armb')
SY.synth_run(d4, n_depth=2000, cid='b', session='20260902', seed=3)
stb = types.SimpleNamespace(instrument='NQ', session='20260902',
                            run_id='b-R001')
T0 = 1_788_000_000.0                       # on a minute boundary: minute M
M = W2._mkey(T0)
M1 = (M[0], M[1] + 1)


def ap_at(i, t0, ad=1, L=15010.0):
    return types.SimpleNamespace(t0=t0, level_px=L, ad=ad,
                                 level_id='SESSION_VWAP', id='ap%d' % i,
                                 wall_state='NONE', windows=1)


# A: two registrations wait for bar M; it closes with a rejection wick
# over 15010 (h 15020, range 15, close 15006 back below) -> B1 short for
# ad=+1; the ad=-1 registration at 15003 has no wick below and no close
# through -> silent and finished
rb = W2.Wave2Runner(d4)
rb._register_arm_b(stb, ap_at(1, T0 + 5))
rb._register_arm_b(stb, ap_at(2, T0 + 5, ad=-1, L=15003.0))
n_wait = len(rb.w2['NQ'].awaiting_b)
rb._bar_closed(stb, (M, 15000.0, 15020.0, 15005.0, 15006.0, 50, T0 + 61))
f1 = [x for x in rb.w2_fires if x['family'] == 'ARM-B1']
t('W4c: registrations wait for their bar, B1 fires on the rejection '
  'wick at the first print after the bar (direction -ad), the ad=-1 '
  'registration is silent, and both are finished',
  n_wait == 2 and len(f1) == 1 and f1[0]['direction'] == -1 and
  f1[0]['approach'] == 'ap1' and f1[0]['t'] == T0 + 61 and
  rb.w2['NQ'].awaiting_b == [] and rb.w2_counts['armb_evaluated_b1'] == 2)

# B: bar M closes THROUGH (15012 > L), next bar closes back (15007)
rb = W2.Wave2Runner(d4)
rb._register_arm_b(stb, ap_at(3, T0 + 5))
rb._bar_closed(stb, (M, 15000.0, 15013.0, 15000.0, 15012.0, 50, T0 + 61))
pend = (len(rb.w2['NQ'].awaiting_b) == 1 and
        rb.w2['NQ'].awaiting_b[0]['b2_pending'] is not None)
rb._bar_closed(stb, (M1, 15012.0, 15014.0, 15006.0, 15007.0, 50, T0 + 121))
f2 = [x for x in rb.w2_fires if x['family'] == 'ARM-B2']
t('W4d: a close through the level leaves the registration pending, the '
  'next bar closing back fires B2 at that bar\'s first-after print, '
  'and the registration is then finished',
  pend and len(f2) == 1 and f2[0]['direction'] == -1 and
  f2[0]['t'] == T0 + 121 and rb.w2['NQ'].awaiting_b == [] and
  rb.w2_counts['armb_evaluated_b2'] == 1)

# C: the approach's bar never closes (bar M1 arrives with no bar M) ->
# expired; a registration for the now-cached bar M1 evaluates at once
rb = W2.Wave2Runner(d4)
rb._register_arm_b(stb, ap_at(4, T0 + 5))
rb._bar_closed(stb, (M1, 15000.0, 15001.0, 14999.0, 15000.0, 50, T0 + 121))
exp_ok = (rb.w2_counts['armb_expired'] == 1 and
          rb.w2['NQ'].awaiting_b == [] and not rb.w2_fires)
rb._register_arm_b(stb, ap_at(5, T0 + 65))          # minute M1, cached
t('W4e: a registration whose bar never closed expires without firing, '
  'and a registration for a bar already in the cache is evaluated '
  'immediately from the cache without waiting',
  exp_ok and rb.w2['NQ'].awaiting_b == [] and
  rb.w2_counts['armb_evaluated_b1'] == 1 and not rb.w2_fires)

# ---------------------------------------------------------------------
# W5: end-to-end on synthetic capture, real mode
# ---------------------------------------------------------------------
d5 = os.path.join(WORK, 'e2e')
# dt_step=0.05 -> ~33 minutes per session, so 1-min bars close, arm-B
# registrations are evaluated and the residual model sees ~25 grid
# observations per 5-min bucket per session (MIN_OBS=20)
path5 = lambda i: 15000.0 + 3.0 * math.sin(2 * math.pi * (i * 0.05) / 900.0)  # noqa: E731
for i, ses in enumerate(('20260901', '20260902', '20260903', '20260904',
                         '20260905', '20260908', '20260921')):
    SY.synth_run(d5, n_depth=40000, dt_step=0.05, price_path=path5,
                 trade_every=10, quote_every=5, cid='w2c%d' % i,
                 session=ses, seed=i)
rep, r5 = W2.run_wave2(d5, mode='real')
w = r5.w2['NQ']
t('W5: the event hooks populate wave-two state from a real ingest - '
  'top-3 adds, top-3 execs and HIGH-confidence trades all observed',
  sum(len(v) for v in w.adds.values()) > 0 and
  len(w.trades_hc) > 0 and r5.ledger['wave2']['mode'] == 'real')

t('W5a: bars closed inside the sessions, every arm-B registration was '
  'evaluated or expired (none carried across a session close), and the '
  'report accounts for all of them',
  r5.states['NQ'].bars_in_session > 10 and
  rep['arm_b']['registered'] > 0 and rep['arm_b']['evaluated_b1'] > 0 and
  w.awaiting_b == [] and
  rep['arm_b']['evaluated_b1'] + rep['arm_b']['expired'] ==
  rep['arm_b']['registered'] and
  rep['w2_windows'] > rep['arm_b']['registered'])

t('W5b: the report carries every registered family, the fires carry the '
  'keys the pilot de-duplication needs, and the blind withholds the '
  '20260921 session',
  set(rep['families']) == set(W2.FAMILIES) and
  all({'instrument', 'session', 'family', 'direction', 't', 'run',
       'approach', 'level', 'state'} <= set(x) for x in rep['fires']) and
  rep['blind_from'] == PI.BLIND_FROM and
  all(b['events_withheld'] == sum(
      1 for e in PI.dedup_fires([x for x in rep['fires']
                                 if x['family'] == fam])
      if e['session'] >= PI.BLIND_FROM)
      for fam, b in rep['families'].items()))

_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
_led1 = PI.PilotRunner(d5).run()
t('W5c: the wave-one ledger (fires, totals, feature_none, sessions, '
  'runs, baselines, regimes) is byte-identical whether produced by the '
  'pilot runner or the wave-two runner - subclassing changed nothing '
  'frozen - and the comparison is not vacuous',
  json.dumps({k: _led1.get(k) for k in _CMP}, sort_keys=True) ==
  json.dumps({k: r5.ledger.get(k) for k in _CMP}, sort_keys=True) and
  bool(_led1.get('totals')) and len(_led1['sessions']) == 7)

t('W5d: the new wave-two baselines (repl10_bid/ask, delta10_hc) were '
  'observed on the grid, so they mature like delta10 instead of only '
  'at executions',
  any(k[0] == 'repl10_ask' for k in r5.states['NQ'].baseline.hist) and
  any(k[0] == 'delta10_hc' for k in r5.states['NQ'].baseline.hist))

t('W5e: the residual model saw prior sessions close, has a fit in at '
  'least one bucket, and resid_tail_5pct was therefore NOT None on '
  'every window (W2-A4f had a population to evaluate)',
  any(len(v) > 0 for v in w.resid.hist.values()) and
  any(w.resid.fit(b) is not None for b in w.resid.hist) and
  0 < rep['w2_input_availability'].get('none_resid_tail_5pct', 0)
  < rep['w2_windows'])

# ---------------------------------------------------------------------
# W6: ARM-C placebo levels
# ---------------------------------------------------------------------
rep_p, rp = W2.run_wave2(d5, mode='placebo')
st = rp.states['NQ']
real_levels = dict(r5.states['NQ'].levels)      # same last session
rad = rp._radius(st)
plc = dict(st.levels)
t('W6: every placebo level is >= %g radii from EVERY real level, and the '
  'placebo dict uses the same ids so nothing downstream can tell'
  % W2.PLACEBO_MIN_SEP,
  bool(plc) and set(plc) <= set(real_levels) and
  all(abs(p - q) >= W2.PLACEBO_MIN_SEP * rad - 1e-9
      for p in plc.values() for q in real_levels.values()))

rp2 = W2.Wave2Runner(d5, mode='placebo')
rp2.run()
t('W6b: placebo offsets are deterministic per session and level (same '
  'run twice -> identical), so ARM-C is reproducible',
  rp2.w2['NQ'].placebo_off == rp.w2['NQ'].placebo_off and
  dict(rp2.states['NQ'].levels) == plc)

t('W6c: the placebo run reports mode=placebo and paired_summary lines '
  'up families with real vs placebo medians and a difference',
  rep_p['mode'] == 'placebo' and
  set(W2.paired_summary(rep, rep_p, PI.BLIND_FROM)) == set(W2.FAMILIES))

# ---------------------------------------------------------------------
# W7: guarantees
# ---------------------------------------------------------------------
src = open(os.path.join(HERE, 'mrofyt_wave2.py')).read()
t('W7: no order API, no fill/stop/target/simulate/P&L call anywhere in '
  'the wave-two module',
  not re.search(r'\b(SubmitOrder|ChangeOrder|CancelOrder|EnterLong|'
                r'EnterShort|ExitLong|ExitShort)\b', src) and
  not re.search(r'\b(entry_fill|structural_stop|simulate|y_dollars|'
                r'compute_outcomes)\s*\(', src))

t('W7b: the frozen signal module is untouched by wave two - still the '
  'hash the v12 suite pins',
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1')

reg = open(os.path.join(HERE, 'MROF_YT_WAVE2_REGISTRATION.md')).read()
t('W7c: every family this module implements is named in the '
  'registration, and the one it does NOT implement is declared',
  all(fam in reg for fam in W2.FAMILIES if not fam.startswith('ARM-')) and
  'Arm B' in reg and 'B1' in reg and 'B2' in reg and
  'CAUSAL_SWING' in rep['not_in_this_version'][0])

t('W7d: the residual model version is stamped on the report and on '
  'every W2-A4f fire, and says what it leaves out',
  rep['resid_model'] == W2.RESID_MODEL and
  'NO intensity/BI3/vol/distance' in W2.RESID_MODEL and
  all(x.get('model') == W2.RESID_MODEL for x in rep['fires']
      if x['family'] == 'W2-A4f'))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
