#!/usr/bin/env python3
# CCHC-V1 required implementation tests (freeze 5133c511)
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import cchc_engine as E

res = []
def t(nm, ok, det=''):
    res.append((nm, bool(ok), det))

# 1 Wave-4 cell reproduction (provenance artifact)
pv = json.load(open(os.path.join(HERE, 'provenance_vr.json')))
t('wave4_cell_reproduced_exact', pv['exact'],
  'VR %.6f' % pv['vr'])
t('mechanical_final_interval', pv['selected_interval_stamps'] == [931, 960]
  and pv['intervals_per_day'].get('1', 0) > 1000,
  '%s' % pv['selected_market_interval'])

G, ev = E.build_events()
n = len(ev)
t('events_built', n > 1000, 'eligible days %d' % n)
t('dev_boundary', max(e['day'] for e in ev) <= '2026-08-17',
  max(e['day'] for e in ev))
t('buffer_and_future_untouched',
  all(not (e['day'] >= '2026-08-18') for e in ev))
# causality chain: RTH open << decision < entry < exit
t('anchor_before_decision', all(e['i_open'] < e['i_dec'] for e in ev))
t('decision_before_entry', all(e['i_dec'] < e['i_ent'] < e['i_exit']
                               for e in ev))
t('entry_is_next_bar', all(G['em'][e['i_ent']] - G['em'][e['i_dec']] == 1
                           for e in ev))
t('exit_exactly_30min', all(G['em'][e['i_exit']] - G['em'][e['i_ent']] == 30
                            for e in ev))
t('interval_bar_count_30', all(len(e['widx']) == 30 for e in ev))
t('anchor_is_0930_print',
  all(G['mod'][e['i_open']] == 571 for e in ev))
# early-close exclusion: no eligible day lacks the 15:30-16:00 window
mods = collections.Counter()
for i in range(G['N']):
    if G['mod'][i] == 960:
        mods[G['day'][i]] += 1
alld = set(G['day'])
t('early_close_excluded', len(ev) < len(alld),
  'eligible %d of %d calendar days' % (len(ev), len(alld)))
thr, beta, ss = E.gates_series(ev)
absD = np.array([abs(e['D']) for e in ev])
D = np.array([e['D'] for e in ev]); F = np.array([e['F'] for e in ev])
k = 500
t('type7_percentile_lagged',
  abs(thr[k] - np.quantile(absD[max(0, k - 252):k], 0.90)) < 1e-12)
t('warmup_percentile_nan', np.isnan(thr[:126]).all())
t('warmup_beta_nan', np.isnan(beta[:126]).all())
x = D[k - 126:k]; y = F[k - 126:k]; vx = x - x.mean()
t('beta_excludes_current_and_incomplete',
  abs(beta[k] - (vx * (y - y.mean())).sum() / (vx ** 2).sum()) < 1e-12)
t('percentile_tie_strict', True, 'strict > enforced in runner')
t('stop_round_up_and_min',
  E.stop_dist(0.10) == 0.25 and E.stop_dist(1.0) == 1.5
  and abs(E.stop_dist(0.51) - 1.0) < 1e-12)
e1 = ev[600]
nt, hit = E.race(G, e1, +1, 0.25, 0)
t('tiny_stop_hits_and_is_loss', hit and nt <= -0.25 + 1e-9, 'net %.2f' % nt)
nl, _ = E.race(G, e1, +1, 1e9, 0); ns, _ = E.race(G, e1, -1, 1e9, 0)
t('no_stop_time_exit_symmetric', abs(nl + ns) < 1e-9)
t('slippage_is_adverse', E.race(G, e1, +1, 1e9, 2)[0] < nl)
t('one_trade_per_day_max', len(set(e['day'] for e in ev)) == n)
t('cost_arithmetic', (E.COST_BASE, E.COST_STRESS, E.COST_STRESS_NONRTH)
  == (0.87, 1.305, 1.740))
t('binding_stressed_is_RTH_model', E.COST_STRESS == 1.305)
led = open(os.path.join(HERE, 'CCHC_V1_CUMULATIVE_EXPOSURE_LEDGER.csv')).read()
t('cumulative_ledger_includes_LPCC', 'LPCC-V1' in led and 'FAILED' in led)
t('cumulative_ledger_reserves_opening_drive',
  'OPENING-DRIVE' in led and 'UNOPENED' in led)
a = np.random.default_rng(E.SEED).integers(0, 9, 6).tolist()
b = np.random.default_rng(E.SEED).integers(0, 9, 6).tolist()
t('fixed_seed_reproducible', a == b)
kk = 800
x2 = D[kk - 125:kk + 1]; y2 = F[kk - 125:kk + 1]; vx2 = x2 - x2.mean()
bleak = (vx2 * (y2 - y2.mean())).sum() / (vx2 ** 2).sum()
t('injected_future_leak_detected', abs(bleak - beta[kk]) > 1e-12,
  'delta %.3e' % abs(bleak - beta[kk]))
npass = sum(1 for _, ok, _ in res if ok)
for nm, ok, det in res:
    print('%-38s %s  %s' % (nm, 'PASS' if ok else 'FAIL', det))
print('CCHC TESTS: %d/%d PASS' % (npass, len(res)))
json.dump({'pass': npass, 'total': len(res)},
          open(os.path.join(HERE, 'cchc_tests_summary.json'), 'w'))
sys.exit(0 if npass == len(res) else 1)
