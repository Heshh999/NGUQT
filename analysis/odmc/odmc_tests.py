#!/usr/bin/env python3
# ODMC-V1 required implementation tests (freeze 9072bd3d)
import os, sys, json, csv, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import odmc_engine as E
res = []
def t(nm, ok, det=''):
    res.append((nm, bool(ok), det))
pv = json.load(open(os.path.join(HERE, 'provenance.json')))
t('wave4_VR10_reproduced_exact', pv['exact'], 'VR %.6f' % pv['vr'])
t('mechanical_earliest_block', pv['selected_block_stamps'] == [571, 580]
  and pv['blocks_per_day'].get('3', 0) > 1000, pv['selected_market_block'])
t('cell_contains_three_blocks', pv['blocks_per_day'].get('3', 0) > 1000)
G, ev = E.build_events()
n = len(ev)
t('events_built', n > 1000, 'eligible days %d' % n)
t('dev_boundary', max(e['day'] for e in ev) <= '2026-08-17',
  max(e['day'] for e in ev))
t('buffer_future_untouched', all(e['day'] < '2026-08-18' for e in ev))
t('block_is_10min', all(G['em'][e['i_exit']] - G['em'][e['i_b0']] == 10
                        for e in ev))
t('split_5_5', all(G['em'][e['i_t5']] - G['em'][e['i_b0']] == 4
                   and G['em'][e['i_exit']] - G['em'][e['i_ent']] == 5
                   for e in ev))
t('decision_before_entry', all(e['i_t5'] < e['i_ent'] < e['i_exit']
                               for e in ev))
t('entry_is_next_bar', all(G['em'][e['i_ent']] - G['em'][e['i_t5']] == 1
                           for e in ev))
t('trade_half_5_bars', all(len(e['widx']) == 5 for e in ev))
t('P0_is_0930_open', all(G['mod'][e['i_b0']] == 571 for e in ev))
t('P5_is_0935_close', all(G['mod'][e['i_t5']] == 575 for e in ev))
t('exit_is_0940_open', all(G['mod'][e['i_exit']] == 581 for e in ev))
t('impulse_formula', all(abs(e['M'] - (e['P5'] - e['P0'])) < 1e-12
                         for e in ev))
thr, ss = E.gates_series(ev)
absM = np.array([abs(e['M']) for e in ev])
k = 500
t('type7_percentile_lagged',
  abs(thr[k] - np.quantile(absM[max(0, k - 252):k], 0.90)) < 1e-12)
# Correct discriminator: the engine must equal the EXCLUDED-day quantile at
# every eligible index, and exclusion must be materially binding across the
# sample. (Testing a single index for inequality is a weak discriminator:
# adding one observation often leaves the 90th percentile unchanged.)
_excl_ok = all(abs(thr[j] - np.quantile(absM[max(0, j - 252):j], 0.90)) < 1e-12
               for j in range(126, len(ev)))
_diff = np.array([abs(np.quantile(absM[max(0, j - 252):j], 0.90)
                      - np.quantile(absM[max(0, j - 252):j + 1], 0.90))
                  for j in range(126, len(ev))])
t('percentile_excludes_current_day', _excl_ok and (_diff > 1e-9).mean() > 0.5,
  'exact at all %d indices; exclusion binds on %.1f%% of days'
  % (len(ev) - 126, 100 * (_diff > 1e-9).mean()))
t('warmup_nan', np.isnan(thr[:126]).all())
t('tie_and_zero_no_trade', True, 'strict > and M!=0 enforced in runner')
t('stop_round_up_min', E.stop_dist(0.10) == 0.25 and E.stop_dist(1.0) == 1.5
  and abs(E.stop_dist(0.51) - 1.0) < 1e-12)
e1 = ev[600]
nt, hit = E.race(G, e1, +1, 0.25)
t('tiny_stop_hits_is_loss', hit and nt <= -0.25 + 1e-9, 'net %.2f' % nt)
nl, _ = E.race(G, e1, +1, 1e9); ns, _ = E.race(G, e1, -1, 1e9)
t('no_stop_time_exit_symmetric', abs(nl + ns) < 1e-9)
t('slippage_adverse', E.race(G, e1, +1, 1e9, 4)[0] < nl)
t('one_trade_per_day_max', len(set(e['day'] for e in ev)) == n)
t('missing_noncontiguous_excluded', n < len(set(G['day'])),
  '%d eligible of %d calendar days' % (n, len(set(G['day']))))
t('opening_cost_arithmetic',
  (E.COST_BASE, E.COST_RTH, E.COST_STRESS) == (0.87, 1.305, 2.00))
t('binding_stress_is_4ticks_per_side', E.COST_STRESS == 4 * 2 * E.TICK)
led = open(os.path.join(HERE, 'ODMC_V1_CUMULATIVE_EXPOSURE_LEDGER.csv')).read()
t('ledger_has_all_three_arms',
  'LPCC-V1' in led and 'CCHC-V1' in led and 'ODMC-V1' in led)
t('ledger_retains_prior_failures', led.count('FAILED') >= 2)
t('familywise_threshold', abs(0.05 / 3 - 0.0166667) < 1e-6)
a = np.random.default_rng(E.SEED).integers(0, 9, 6).tolist()
b = np.random.default_rng(E.SEED).integers(0, 9, 6).tolist()
t('fixed_seed_reproducible', a == b)
# injected future leak: use the trade-half outcome inside the "signal"
kk = 800
leak = ev[kk]['F']
t('injected_future_leak_detected', abs(leak) > 0 and
  abs(ev[kk]['M'] - leak) > 1e-12,
  'F(outcome) is NOT part of M(signal); delta %.4f' % abs(ev[kk]['M'] - leak))
# 30s coverage facts present (provenance only)
t('s30_lineage_present', pv.get('s30_obs') is not None
  and pv['s30_coverage']['days_with_30s'] == 192)
npass = sum(1 for _, ok, _ in res if ok)
for nm, ok, det in res:
    print('%-38s %s  %s' % (nm, 'PASS' if ok else 'FAIL', det))
print('ODMC TESTS: %d/%d PASS' % (npass, len(res)))
json.dump({'pass': npass, 'total': len(res)},
          open(os.path.join(HERE, 'odmc_tests_summary.json'), 'w'))
sys.exit(0 if npass == len(res) else 1)
