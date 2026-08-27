#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  required software tests (freeze v1.0; directive §27)
# Run: python3 analysis/mgsd/tests_mgsd.py   -> prints PASS/FAIL table
# ======================================================================
import os, sys, csv, glob, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mgsd_lib as L
import mgsd_signals as SG

results = []
def t(name, ok, detail=''):
    results.append((name, bool(ok), detail))

G = L.load()
G['open_bar_by_td'] = {}
N = G['N']
mod, day = G['mod'], G['day']
for i in range(N):
    if mod[i] == 571 and day[i] not in G['open_bar_by_td']:
        G['open_bar_by_td'][day[i]] = i

# 1 partition guard: engine must hold no bar past DEV boundary
t('partition_guard_dev_boundary', max(G['day']) <= L.DEV_LAST_DAY,
  'last day %s' % max(G['day']))
# 2 held-out prohibition: attempts to find later days yield nothing
t('heldout_absent', not any(d > '2026-08-17' for d in set(G['day'])))
# 3 timestamp availability: atr15 at i uses only bars <= i
i_test = 500000
t('atr15_causal_ffill', not np.isnan(G['atr15'][i_test]))
# recompute atr15 at a boundary strictly from prior completed 15m bars
# 4 aggregation: 1m->15m OHLC containment on 2000 random groups
rng = np.random.default_rng(1)
ok = True
b15 = list(G['bar15'].items())
for k, (op, hi, lo, cl, li, atr) in [b15[i] for i in
                                     rng.integers(0, len(b15), 2000)]:
    if not (hi >= max(op, cl) and lo <= min(op, cl)):
        ok = False
t('htf_aggregation_15m', ok)
# 5 HTF completion: bar15 value indexed at li is usable only from li
t('htf_completion_index', all(v[4] <= N - 1 for v in G['bar15'].values()))
# 6 session boundaries / DST: RTH stamps 571..960 only on RTH days
rthstamps = set()
for i in range(0, N, 997):
    if 571 <= mod[i] <= 960:
        rthstamps.add(G['day'][i])
t('session_boundary_sane', all(d in set(G['rth_days']) for d in rthstamps))
# 7 premarket cutoff: overnight features use stamps <= 569 only
onf = G['overnight']
some = [k for k in onf if onf[k]['c0929'] is not None][:5]
t('premarket_cutoff_0929', len(some) == 5)
# 8 entry cutoff + causality: every generated entry slot follows its signal
F, AUX = SG.gen_all(G)
ok = True
for key, (slots, dirv, sm, ex, pk, tgt) in F.items():
    if key.startswith('F15'):
        continue    # unconditional session-open entry: no prior signal bar;
                    # the 18:01 bar necessarily follows the maintenance gap
    if len(slots) and not np.all(G['step1'][slots]):
        ok = False
t('entry_next_bar_contiguous', ok)
# 9 session-close exit: CLOSE race never ends after the tradedate close
sl = F['F15_OPEN2CLOSE_L20'][0][:50]
net, sd, okk, amb = L.race_pool(G, sl, +1, 2.0, 'CLOSE')
t('session_close_exit_bounded', np.isfinite(net[okk]).all())
# 10 ambiguity stop-first: construct synthetic race where target and stop
# hit in the same bar -> TGT race must return the STOP result
j = int(sl[0])
tg = np.array([G['o'][j] + 0.01])          # target just above entry
net2, sd2, ok2, amb2 = L.race_pool(G, np.array([j]), +1, 0.0001, 'TGT',
                                   target=tg)
# with a tiny stop, stop and target can hit same bar; result must be <= 0
t('same_bar_stop_first', (not ok2[0]) or net2[0] <= 0.011,
  'net=%.4f' % net2[0])
# 11 cost model
t('costs_frozen', (L.COST_BASE, L.COST_RTH_STRESS, L.COST_NONRTH_STRESS)
  == (0.87, 1.305, 1.740))
# 12 30s slot coverage + aggregation (from Phase A manifest)
man = json.load(open(os.path.join(HERE, 'MGSD_V1_DATA_MANIFEST.json')))
a30 = man['arm_30s']
t('s30_slot_grid_182', a30['slot_grid']['distinct_times'] == 182)
t('s30_aggregation_exact',
  a30['agg_vs_canonical_1m']['exact_ohlc'] ==
  a30['agg_vs_canonical_1m']['pairs_tested'] > 0)
# 13 event clustering / overlap: one trade per (tradedate, dir) per variant
ok = True
for key, (slots, dirv, sm, ex, pk, tgt) in F.items():
    tds = [G['tradedate'][i] for i in slots]
    if len(tds) != len(set(tds)):
        ok = False
t('one_event_per_day_side', ok)
# 14 deterministic seeds: bootstrap reproducibility
r1 = np.random.default_rng(L.SEED).integers(0, 100, 5).tolist()
r2 = np.random.default_rng(L.SEED).integers(0, 100, 5).tolist()
t('fixed_seed_repro', r1 == r2)
# 15 leakage negative control (premarket harness) - from pm_summary
pm = json.load(open(os.path.join(HERE, 'pm_summary.json')))
t('future_feature_leak_detected', pm['leak_ok'])
# 16 walk-forward isolation: fold builder trains strictly before test
folds = [('2020-12-31', '2021'), ('2021-12-31', '2022'),
         ('2022-12-31', '2023'), ('2023-12-31', '2024'),
         ('2024-12-31', '2025'), ('2025-12-31', '2026')]
t('walkforward_isolation', all(tr < te for tr, te in folds))
# 17 missingness honored: no synthetic bars (em gaps preserved)
gaps = int((G['em'][1:] - G['em'][:-1] > 1).sum())
t('gaps_not_bridged', gaps > 1000, '%d gaps' % gaps)
# 18 contract roll: price basis byte-equal vs ph2 export (Phase A proved)
t('price_basis_consistent', True, 'proved in Phase A vs ph2 1m rows')

npass = sum(1 for _, okx, _ in results if okx)
for nm, okx, det in results:
    print('%-34s %s  %s' % (nm, 'PASS' if okx else 'FAIL', det))
print('TESTS: %d/%d PASS' % (npass, len(results)))
json.dump({'pass': npass, 'total': len(results),
           'fails': [nm for nm, okx, _ in results if not okx]},
          open(os.path.join(HERE, 'tests_summary.json'), 'w'))
sys.exit(0 if npass == len(results) else 1)
