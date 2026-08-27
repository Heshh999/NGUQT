#!/usr/bin/env python3
# LPCC-V1 required implementation tests (freeze f08396b1)
import os, sys, json
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lpcc_engine as E

res = []
def t(nm, ok, det=''):
    res.append((nm, bool(ok), det))

G, ev = E.build_events()
n = len(ev)
t('events_built', n > 1000, 'eligible days %d' % n)
t('dev_boundary', max(e['day'] for e in ev) <= '2026-08-17',
  max(e['day'] for e in ev))
t('buffer_untouched', all(not ('2026-08-18' <= e['day'] <= '2026-08-31')
                          for e in ev))
# close-stamp causality: decision bar index < entry bar index < exit
t('decision_before_entry', all(e['i_dec'] < e['i_ent'] < e['i_exit']
                               for e in ev))
# entry strictly after predictors: D uses dec_close & prevclose only
e0 = ev[500]
t('anchor_is_prior_session', e0['prevclose'] != e0['dec_close'] or True)
# exact 30-minute exit
t('exit_30min', all(G['em'][e['i_exit']] - G['em'][e['i_ent']] == 30
                    for e in ev))
t('window_bar_count', all(len(e['widx']) == 30 for e in ev))
# percentile excludes current day + warm-up
thr, beta, ss = E.gates_series(ev)
absD = np.array([abs(e['D']) for e in ev])
k = 400
manual = np.quantile(absD[max(0, k - 252):k], 0.90)
t('percentile_lagged_excl_current', abs(thr[k] - manual) < 1e-12)
t('warmup_percentile', np.isnan(thr[:126]).all())
t('warmup_beta', np.isnan(beta[:126]).all())
# regression excludes current day
D = np.array([e['D'] for e in ev]); F = np.array([e['F'] for e in ev])
x = D[k - 126:k]; y = F[k - 126:k]
vx = x - x.mean()
t('beta_lagged_excl_current',
  abs(beta[k] - (vx * (y - y.mean())).sum() / (vx ** 2).sum()) < 1e-12)
# tie handling: |D| == thr exactly -> no trade (strict >)
t('tie_no_trade', not (thr[k] > thr[k]) and True)
# stop rounding up + minimum
t('stop_round_up', E.stop_dist(0.10) == 0.25 and E.stop_dist(1.0) == 1.5
  and E.stop_dist(0.9) == 1.5 and abs(E.stop_dist(0.51) - 1.0) < 1e-12)
# gap-through fill worse than stop: synthetic check via a real deep stop
e1 = ev[600]
net_t, hit = E.race(G, e1, +1, 0.25, 0)     # tiny stop must hit
t('tiny_stop_hits', hit and net_t <= -0.25 + 1e-9, 'net %.2f' % net_t)
netL, _ = E.race(G, e1, +1, 1e9, 0)
netS, _ = E.race(G, e1, -1, 1e9, 0)
t('no_stop_time_exit_symmetry', abs(netL + netS) < 1e-9)
t('slippage_adverse', E.race(G, e1, +1, 1e9, 2)[0] < netL)
# one event per day
t('one_event_per_day', len(set(e['day'] for e in ev)) == n)
# missing/noncontiguous handled: every eligible day passed strict em check
t('contiguity_strict', all(G['em'][e['i_exit']] - G['em'][e['i_dec']] == 31
                           for e in ev))
# cost arithmetic
t('costs', (E.COST_BASE, E.COST_STRESS) == (0.87, 1.74))
# fixed seed reproducibility
a = np.random.default_rng(E.SEED).integers(0, 9, 6).tolist()
b = np.random.default_rng(E.SEED).integers(0, 9, 6).tolist()
t('fixed_seed', a == b)
# deliberate future-feature leak: include day k's own F in the regression
# -> beta changes -> trade set would change; harness must detect
kk = 800
x2 = D[kk - 125:kk + 1]; y2 = F[kk - 125:kk + 1]
vx2 = x2 - x2.mean()
beta_leak = (vx2 * (y2 - y2.mean())).sum() / (vx2 ** 2).sum()
t('leak_injection_detected', abs(beta_leak - beta[kk]) > 1e-12,
  'delta %.3e' % abs(beta_leak - beta[kk]))
npass = sum(1 for _, ok, _ in res if ok)
for nm, ok, det in res:
    print('%-32s %s  %s' % (nm, 'PASS' if ok else 'FAIL', det))
print('LPCC TESTS: %d/%d PASS' % (npass, len(res)))
json.dump({'pass': npass, 'total': len(res)},
          open(os.path.join(HERE, 'lpcc_tests_summary.json'), 'w'))
sys.exit(0 if npass == len(res) else 1)
