#!/usr/bin/env python3
# MROF-YT-W3-BIGMOVE-1.0 suite. Wave three is exercised on synthetic
# recorder-format runs (mles_v12_synth), random walks and hand-built
# feature dicts. Synthetic events verify CODE BEHAVIOR only, never market
# evidence. No order, fill or P&L exists anywhere.
import array
import hashlib
import json
import math
import os
import random
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mles_v12_synth as SY      # noqa: E402
import mrofyt_bigmove as BM      # noqa: E402
import mrofyt_pilot as PI        # noqa: E402
import mrofyt_wave2 as W2        # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-72s %s' % (name[:72], 'PASS' if cond else 'FAIL'))


WORK = tempfile.mkdtemp(prefix='mrofyt_w3_')

# ---------------------------------------------------------------------
# B1: the path score against a plain forward scan
# ---------------------------------------------------------------------
rng = random.Random(20261003)
mism = checks = 0
ex_mism = 0
for trial in range(60):
    n = rng.choice([30, 300, 2500])
    tt, p = 0.0, 15000.0
    ts, ps = array.array('d'), array.array('d')
    for _ in range(n):
        tt += rng.choice([0.05, 0.5, 2.0, 15.0, 60.0])
        p += rng.choice([-1, 0, 0, 1]) * 0.25 * rng.choice([1, 1, 2, 6, 25, 60])
        ts.append(tt)
        ps.append(p)
    cts, cps = BM.compress(ts, ps)
    want = set(rng.sample(range(len(cps)), min(30, len(cps))))
    px = BM.PathIndex(cts, cps, want)
    for i in want:
        for d in (1, -1):
            for s in BM.STOPS_TICKS:
                checks += 1
                if px.score(i, d, s)['outcome'] != \
                        BM.score_path_brute(cts, cps, cts[i], d, s):
                    mism += 1
    ex = BM.window_extremes(cts, cps, want)
    for i in want:
        k = [j for j in range(i + 1, len(cts))
             if cts[j] <= cts[i] + BM.LIMIT_S]
        done = cts[-1] >= cts[i] + BM.LIMIT_S
        if not done:
            if i in ex:
                ex_mism += 1
            continue
        up = max([0.0] + [(cps[j] - cps[i]) / 0.25 for j in k])
        dn = max([0.0] + [(cps[i] - cps[j]) / 0.25 for j in k])
        if i not in ex or abs(ex[i][0] - up) > 1e-9 or \
                abs(ex[i][1] - dn) > 1e-9:
            ex_mism += 1
t('B1: the Fenwick first-touch score equals a plain forward scan on '
  '%d random-walk checks (target, three stops, both directions, '
  'timeout, unresolved)' % checks, checks > 5000 and mism == 0)
t('B1b: the monotonic-deque window extremes equal a plain scan, and an '
  'index whose 1800 s window runs past the run end is left out',
  ex_mism == 0)

# hand cases: a path that goes +60 ticks, then -50, then +120 within 1800 s
ts = array.array('d', [0, 10, 20, 30, 40, 2000])
ps = array.array('d', [15000, 15015, 14987.5, 15030, 15031, 15031])
px = BM.PathIndex(ts, ps, {0})
sc = {s: px.score(0, 1, s, excursions=True) for s in BM.STOPS_TICKS}
t('B2: hand path (+60, -50, +120 ticks): stop 40 is hit by the -50 dip '
  'before the target; stops 60 and 80 survive it and reach the target; '
  'the winner records its -50 tick adverse excursion and its seconds',
  sc[40.0]['outcome'] == 'STOP' and sc[40.0]['value_ticks'] == -40.0 and
  sc[60.0]['outcome'] == 'TARGET' and sc[80.0]['outcome'] == 'TARGET' and
  sc[60.0]['value_ticks'] == 100.0 and sc[60.0]['mae_ticks'] == 50.0 and
  sc[60.0]['seconds'] == 30.0 and sc[60.0]['mfe_ticks'] == 120.0)
sc_short = px.score(0, -1, 60.0)
t('B2b: the same path read short is a STOP at the +60 rise for every '
  'stop, and the first touch is the one that counts',
  sc_short['outcome'] == 'STOP' and px.score(0, -1, 80.0)['outcome'] ==
  'STOP' and sc_short['seconds'] == 10.0)
ts2 = array.array('d', [0, 100, 1700, 1900, 2000])
ps2 = array.array('d', [15000, 15005, 15010, 15040, 15040])
px2 = BM.PathIndex(ts2, ps2, {0})
to = px2.score(0, 1, 40.0)
ts3 = array.array('d', [0, 100, 900])
ps3 = array.array('d', [15000, 15005, 15010])
px3 = BM.PathIndex(ts3, ps3, {0})
un = px3.score(0, 1, 40.0)
t('B2c: a touch after 1800 s is a TIMEOUT carrying the 1800 s markout '
  '(+40 ticks here), and a run that ends before 1800 s with no touch is '
  'UNRESOLVED with no value',
  to['outcome'] == 'TIMEOUT' and to['value_ticks'] == 40.0 and
  un['outcome'] == 'UNRESOLVED' and un['value_ticks'] is None)
ts4 = array.array('d', [0, 5, 10])
ps4 = array.array('d', [15000, 15000 - 10.0, 15000 + 25.0])
px4 = BM.PathIndex(ts4, ps4, {0})
t('B2d: the stop is checked before the target in time order: a -40 tick '
  'print one update before a +100 tick print is a STOP',
  px4.score(0, 1, 40.0)['outcome'] == 'STOP' and
  px4.score(0, 1, 60.0)['outcome'] == 'TARGET')

# ---------------------------------------------------------------------
# B3: the pattern functions on crafted inputs, each condition load-bearing
# ---------------------------------------------------------------------
g = dict(s=1, z_delta_s=3.2, resp=5.0, agree_s=3, control_s=2.5)
t('B3: G1 fires with the flow (z>=3, response>=4 ticks with it, 3 of 4) '
  'and every dropped condition silences it',
  BM.g1_flow_shock_go(g) == 1 and
  BM.g1_flow_shock_go(dict(g, s=-1, resp=-5.0)) == -1 and
  BM.g1_flow_shock_go(dict(g, z_delta_s=2.9)) == 0 and
  BM.g1_flow_shock_go(dict(g, resp=3.5)) == 0 and
  BM.g1_flow_shock_go(dict(g, agree_s=2)) == 0 and
  BM.g1_flow_shock_go(dict(g, z_delta_s=None)) == 0 and
  BM.g1_flow_shock_go(dict(g, s=0)) == 0)
t('B3b: G2 fires against the flow (z>=3, |response|<=1 tick) and not '
  'when price actually moved',
  BM.g2_flow_shock_fade(dict(g, resp=0.5)) == -1 and
  BM.g2_flow_shock_fade(dict(g, resp=-1.0, s=-1)) == 1 and
  BM.g2_flow_shock_fade(dict(g, resp=1.5)) == 0 and
  BM.g2_flow_shock_fade(dict(g, resp=0.0, z_delta_s=2.0)) == 0)
prev = dict(s=1, control_s=2.1)
t('B3c: G3 needs control >= 2.0 on this tick AND the previous one with '
  'the same flow sign',
  BM.g3_control_run(g, prev) == 1 and
  BM.g3_control_run(g, None) == 0 and
  BM.g3_control_run(g, dict(prev, s=-1)) == 0 and
  BM.g3_control_run(g, dict(prev, control_s=1.9)) == 0 and
  BM.g3_control_run(dict(g, control_s=1.5), prev) == 0)
f = dict(level_id='OVERNIGHT_HIGH', ad=1, clean_cross=True, held_5s=True,
         persist_agree=3, aggr_dir=1, aggr_z=1.6, opp_flip_z=1.2,
         returned_through_level=False, progress_ticks=0.0)
sod_open = 9.5 * 3600 + 600
t('B3d: L1 fires inside 09:30-10:00 at an overnight/yday level on a '
  'held clean cross with flow, not at 10:00, not at VWAP, not without '
  'the hold',
  BM.l1_open_break(f, sod_open) == 1 and
  BM.l1_open_break(f, 10.0 * 3600) == 0 and
  BM.l1_open_break(dict(f, level_id='SESSION_VWAP'), sod_open) == 0 and
  BM.l1_open_break(dict(f, held_5s=False), sod_open) == 0 and
  BM.l1_open_break(dict(f, aggr_z=1.4), sod_open) == 0 and
  BM.l1_open_break(dict(f, aggr_dir=-1), sod_open) == 0 and
  BM.l1_open_break(dict(f, persist_agree=2), sod_open) == 0)
t('B3e: L2 fires back through a reclaimed range level with an opposing '
  'flip, and not at a pivot or without the reclaim',
  BM.l2_sweep_reclaim(dict(f, returned_through_level=True)) == -1 and
  BM.l2_sweep_reclaim(dict(f, returned_through_level=True, ad=-1)) == 1 and
  BM.l2_sweep_reclaim(f) == 0 and
  BM.l2_sweep_reclaim(dict(f, returned_through_level=True,
                           level_id='PP')) == 0 and
  BM.l2_sweep_reclaim(dict(f, returned_through_level=True,
                           opp_flip_z=0.9)) == 0)
t('B3f: L3 fires only from outside a VWAP band coming back with flow',
  BM.l3_vwap_snapback(dict(f, level_id='VWAP_UPPER', ad=-1,
                           aggr_dir=-1)) == -1 and
  BM.l3_vwap_snapback(dict(f, level_id='VWAP_LOWER', ad=1)) == 1 and
  BM.l3_vwap_snapback(dict(f, level_id='VWAP_UPPER', ad=1)) == 0 and
  BM.l3_vwap_snapback(dict(f, level_id='VWAP_LOWER', ad=1,
                           aggr_z=1.0)) == 0 and
  BM.l3_vwap_snapback(dict(f, level_id='SESSION_VWAP', ad=1)) == 0)
t('B3g: L4 fires in the direction of the earlier held break when a '
  'retest from the far side fails to progress, and never without the '
  'memory',
  BM.l4_break_retest(dict(f, ad=-1, aggr_dir=-1), 1) == 1 and
  BM.l4_break_retest(dict(f, ad=1, aggr_dir=1), -1) == -1 and
  BM.l4_break_retest(dict(f, ad=-1, aggr_dir=-1), None) == 0 and
  BM.l4_break_retest(dict(f, ad=1, aggr_dir=1), 1) == 0 and
  BM.l4_break_retest(dict(f, ad=-1, aggr_dir=-1, progress_ticks=2.0),
                     1) == 0 and
  BM.l4_break_retest(dict(f, ad=-1, aggr_dir=-1, level_id='M2'), 1) == 0)
subs = [50.0, 40.0, -5.0, 30.0, 20.0, 10.0]
t('B3h: D1 fires with a 15+ point move from the cash open when the '
  'flow sum and 4 of 6 ten-minute sums agree, and not otherwise',
  BM.d1_trend_1030(15016.0, 15000.0, subs) == 1 and
  BM.d1_trend_1030(14984.0, 15000.0, [-x for x in subs]) == -1 and
  BM.d1_trend_1030(15014.0, 15000.0, subs) == 0 and
  BM.d1_trend_1030(15016.0, 15000.0, [-x for x in subs]) == 0 and
  BM.d1_trend_1030(15016.0, 15000.0, [90, -1, -1, -1, 5, 5]) == 0 and
  BM.d1_trend_1030(15016.0, None, subs) == 0)

# ---------------------------------------------------------------------
# B4: Holm and multiplicity
# ---------------------------------------------------------------------
t('B4: Holm step-down rejects [0.001, 0.01] of [0.001, 0.01, 0.03, 0.2] '
  'at 0.05 and stops at the first failure; a None p-value counts toward '
  'm and is never rejected; the registration fixes 24 tests',
  BM.holm([0.001, 0.01, 0.03, 0.2]) == [True, True, False, False] and
  BM.holm([0.2, 0.001, None, 0.01]) == [False, True, False, True] and
  BM.N_TESTS == 24 and len(BM.PATTERNS) == 8 and
  BM.STOPS_TICKS == (40.0, 60.0, 80.0) and BM.TARGET_TICKS == 100.0 and
  BM.LIMIT_S == 1800.0 and BM.DEV_END == '20260918')

# ---------------------------------------------------------------------
# B5-B9: end to end on synthetic tape, with a validation session present
# ---------------------------------------------------------------------
d5 = os.path.join(WORK, 'e2e')
path5 = lambda i: 15000.0 + 30.0 * math.sin(2 * math.pi * (i * 0.05) / 900.0)  # noqa: E731
SESSIONS = ('20260901', '20260902', '20260903', '20260904', '20260905',
            '20260908', '20260921')
for i, ses in enumerate(SESSIONS):
    SY.synth_run(d5, n_depth=40000, dt_step=0.05, price_path=path5,
                 trade_every=10, quote_every=5, cid='w3c%d' % i,
                 session=ses, seed=i)
rep, r5 = BM.run_bigmove(d5)
t('B5: the default mode REFUSES the validation session (20260921) and '
  'lists it, reads every DEV session, and the report says so',
  rep['sessions_refused'] == ['20260921'] and
  rep['sessions_inspected'] == list(SESSIONS[:-1]) and
  '20260921' not in rep['sessions_inspected'] and
  not any(e['session'] > BM.DEV_END for e in rep['events']) and
  not any(g['session'] > BM.DEV_END for g in r5.grid) and
  rep['unblind'] is False)
t('B5b: the report carries every registered block: 24 tests on NQ, '
  'eight patterns x two instruments x three stops, hour-matched '
  'baseline cells, the census, the score rule, and it serializes',
  len(rep['tests']) == 24 and
  all(set(rep['patterns'][p]) == {'NQ', 'MNQ'} for p in BM.PATTERNS) and
  all(set(rep['patterns'][p]['NQ']['stops']) == {'40', '60', '80'}
      for p in BM.PATTERNS) and
  rep['grid_ticks'] > 0 and rep['baseline_cells'] and
  all(v['n'] > 0 for cell in rep['baseline_cells'].values()
      for v in cell.values()) and
  rep['census']['n'] > 0 and 'base_rate' in rep['census'] and
  rep['score_rule']['tie'] == 'STOP' and
  json.dumps(rep, default=str))
raw = sum(rep['raw_fires'].values())
t('B5c: fires exist on the synthetic tape, are de-duplicated at 60 s by '
  'the pilot rule into no more events than raw fires, every event is '
  'scored at all three stops, and the hour cell of each event matches '
  'its grid hour',
  raw > 0 and 0 < len(rep['events']) <= raw and
  all(set(e['scores']) == {'40', '60', '80'} for e in rep['events']) and
  all(e['hour'] == int(PI.RUN.sod_seconds(e['t']) // 3600)
      for e in rep['events']))
blk = rep['patterns']['G2']['NQ']
t('B5d: a pattern block reports counts, hit rate, matched baseline, lift '
  'with a seeded interval and p above five events, expectancy in ticks '
  'and points, and winners\' adverse excursion',
  blk['events'] > 0 and
  all(k in blk['stops']['40'] for k in
      ('counts', 'n_resolved', 'hit_rate', 'matched_baseline_hit',
       'lift', 'expectancy_ticks_before_costs',
       'expectancy_points_before_costs')) and
  (blk['stops']['40']['n_resolved'] < 5 or
   'ci95' in blk['stops']['40']['lift']) and
  abs(blk['stops']['40']['expectancy_points_before_costs'] -
      blk['stops']['40']['expectancy_ticks_before_costs'] / 4.0) < 0.02)
# the lift is observed minus the hour-matched expectation, recomputed
# here from the report's own cells
d40 = blk['stops']['40']
evs = [e for e in rep['events'] if e['family'] == 'G2' and
       e['instrument'] == 'NQ' and e['scores']['40']['outcome'] !=
       'UNRESOLVED']
exp = [rep['baseline_cells']['NQ@%02d' % e['hour']]['40']['hit']
       for e in evs]
obs = [1.0 if e['scores']['40']['outcome'] == 'TARGET' else 0.0 for e in evs]
t('B5e: the lift equals the observed hit rate minus the mean of the '
  'events\' own (instrument, hour) baseline cells',
  evs and abs(d40['lift']['lift'] - (sum(obs) / len(obs) -
                                     sum(exp) / len(exp))) < 1e-3 and
  abs(d40['matched_baseline_hit'] - sum(exp) / len(exp)) < 1e-3)

# B6: placebo mode uses the wave-two offset rule exactly
rep_p, rp = BM.run_bigmove(d5, mode='placebo')
# the wave-two runner reads all seven sessions; cap it at the six DEV
# sessions this tool reads so both end on the same session's offsets
rw2 = W2.Wave2Runner(d5, mode='placebo', max_sessions=6)
rw2.run()
t('B6: placebo levels are the wave-two ARM-C levels: identical offsets '
  'per (session, level) to Wave2Runner on the same six sessions, and '
  'the paired table reports L1-L4 real against placebo',
  rp.w3['NQ'].placebo_off == rw2.w2['NQ'].placebo_off and
  rp.w3['NQ'].placebo_off and
  set(BM.paired_placebo(rep, rep_p)) == set(BM.LEVEL_PATTERNS))

# B7: unblind reads the validation session and exposes it, monotone
rep_u, ru = BM.run_bigmove(d5, unblind=True)
led = os.path.join(WORK, 'ledger.json')
json.dump(dict(exposed_days=[
    dict(session='20260901', label=PI.EXPOSURE_LABEL,
         exposed_by='MROF-YT-PILOT-1.0'),
    dict(session='20260921', label=PI.BLIND_LABEL,
         exposed_by='MROF-YT-PILOT-1.2')]), open(led, 'w'))
n = BM.write_exposure_on_unblind(rep_u, led)
days = {d['session']: d for d in json.load(open(led))['exposed_days']}
t('B7: --unblind reads 20260921, refuses nothing, and the ledger marks '
  'it exposed by this wave with previously_blind, keeps the pilot\'s '
  'own exposure on 20260901 and adds this wave beside it',
  '20260921' in rep_u['sessions_inspected'] and
  rep_u['sessions_refused'] == [] and n == 7 and
  days['20260921']['label'] == PI.EXPOSURE_LABEL and
  days['20260921']['exposed_by'] == BM.W3_VERSION and
  days['20260921'].get('previously_blind') is True and
  days['20260901']['exposed_by'] == 'MROF-YT-PILOT-1.0' and
  BM.W3_VERSION in days['20260901']['also_exposed_by'])
# a folder holding ONLY validation sessions stops with nothing read
d6 = os.path.join(WORK, 'valonly')
SY.synth_run(d6, n_depth=3000, cid='v1', session='20260925')
stopped = False
try:
    BM.run_bigmove(d6)
except PI.RUN.NoCaptureData:
    stopped = True
t('B7b: a folder whose every session is validation stops with '
  'NoCaptureData and nothing read, rather than a clean empty report',
  stopped)

# B8: outcome lock of waves one and two untouched; wording on every line
txt = BM.text_summary(rep)
t('B8: the wave-one ledger still says outcomes=LOCKED and carries no '
  'wave-three score; the summary names the refused sessions and states '
  'on its face that nothing is P&L and no order was placed',
  rep['outcomes_wave_one'] == 'LOCKED' and
  'wave3' in r5.ledger and 'scores' not in json.dumps(r5.ledger['fires']) and
  'REFUSED' in txt and '20260921' in txt and 'not P&L' in txt and
  'No order was placed' in txt and 'tie=STOP' in txt)

# B9: subclassing changed nothing frozen
_CMP = ('fires', 'totals', 'feature_none', 'sessions', 'runs',
        'skipped_runs', 'baseline_sessions', 'regime_at_window', 'outcomes')
r1 = PI.PilotRunner(d5, max_sessions=6)
_led1 = r1.run()
t('B9: the wave-one ledger (fires, totals, feature_none, sessions, runs, '
  'baselines, regimes, outcomes) is byte-identical whether produced by '
  'the pilot runner or the wave-three runner on the same six sessions',
  json.dumps({k: _led1.get(k) for k in _CMP}, sort_keys=True) ==
  json.dumps({k: r5.ledger.get(k) for k in _CMP}, sort_keys=True) and
  bool(_led1.get('totals')) and len(_led1['sessions']) == 6)

# B10: the frozen signal module and the registration are pinned
_reg = open(os.path.join(HERE, 'MROF_YT_WAVE3_BIGMOVE_REGISTRATION.md')).read()
t('B10: registering wave three changed NO wave-one detector -- the '
  'frozen signal module is still the hash tests_mles_v12 pins -- and '
  'the registration states the target, stops, limit, DEV end, Holm and '
  'the refusal rule',
  hashlib.sha256(open(os.path.join(HERE, 'mrofyt_signals.py'),
                      'rb').read()).hexdigest() ==
  '06ce854a40717a2398231eb8c5120d8e709c18fd8f7cb8d1ac2cc4ecc640a8e1' and
  '100 ticks' in _reg and '40, 60, 80' in _reg and '1800 s' in _reg and
  '20260918' in _reg and 'Holm' in _reg and 'refuses' in _reg and
  'NOT TESTED' in _reg and 'Explicitly NOT registered' in _reg)

# B11: the census is a decile table against the base rate, nothing more
c = rep['census']
t('B11: the census tabulates deciles of each grid feature against the '
  'share reaching +100/-100 ticks, carries the base rate and the '
  '"diagnostic only" note, and names no verdict',
  all(feat in c for feat in BM.CENSUS_FEATURES) and
  'diagnostic only' in c['note'] and 'verdict' not in json.dumps(
      {k: v for k, v in c.items() if k != 'note'}) and
  all(0.0 <= c['base_rate'][k] <= 1.0 for k in ('up', 'down')))

shutil.rmtree(WORK, ignore_errors=True)
n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
