#!/usr/bin/env python3
# ======================================================================
# VTBS-V1  -  FROZEN ONE-SHOT RUN  (complete search, no early stop)
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import csv
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vtbs_lib as V  # noqa: E402

CELLS = [('C1', 0.15, 955), ('C2', 0.30, 955),
         ('C3', 0.15, 780), ('C4', 0.30, 780)]


def cell_mean(ev, cost=V.COST_STRESS):
    x = [e['gross'] - cost for e in ev if e['gross'] is not None]
    return (len(x), float(np.mean(x)) if x else float('nan'))


def main():
    days, byday = V.load_days()
    st = V.day_state(days, byday)
    high = sorted(d for d in st if st[d]['p'] >= st[d]['thr'])
    print('VTBS-V1 one-shot  DEV %s..%s  eligible %d  HIGH %d'
          % (days[0], days[-1], len(st), len(high)))
    R, RAW = {}, {}
    for name, k, xm in CELLS:
        ev = V.build(days, byday, st, k, xm, 'HIGH')
        RAW[name] = ev
        s = V.stats_cell(ev)
        # --- diagnostics -------------------------------------------
        uncond = V.build(days, byday, st, k, xm, 'ALL')
        s['uncond'] = cell_mean(uncond)
        s['low'] = cell_mean(V.build(days, byday, st, k, xm, 'LOW'))
        tr = [e for e in ev if e['gross'] is not None]
        s['long'] = cell_mean([e for e in tr if e['side'] > 0])
        s['short'] = cell_mean([e for e in tr if e['side'] < 0])
        s['whipsaw_n'] = sum(1 for e in tr if e['kind'] == 'WHIPSAW')
        s['stop_n'] = sum(1 for e in tr if e['kind'] == 'STOP')
        per_year = collections.defaultdict(list)
        for e in tr:
            per_year[e['day'][:4]].append(e['gross'] - V.COST_STRESS)
        s['years'] = {y: (len(v), float(np.mean(v)))
                      for y, v in sorted(per_year.items())}
        s['delay1'] = cell_mean(V.build(days, byday, st, k, xm, 'HIGH',
                                        entry_shift=1))
        s['neigh'] = {
            'k-20%': cell_mean(V.build(days, byday, st, k, xm, 'HIGH',
                                       band_scale=0.8)),
            'k+20%': cell_mean(V.build(days, byday, st, k, xm, 'HIGH',
                                       band_scale=1.2)),
            'Q70': cell_mean(V.build(days, byday, st, k, xm, 'HIGH',
                                     thr_key='thr70')),
            'Q80': cell_mean(V.build(days, byday, st, k, xm, 'HIGH',
                                     thr_key='thr80')),
        }
        g = np.array([e['gross'] for e in tr]) - V.COST_STRESS
        dsum = collections.defaultdict(float)
        for e in tr:
            dsum[e['day']] += e['gross'] - V.COST_STRESS
        best = max(dsum, key=dsum.get)
        s['drop_best_day'] = float(np.mean([e['gross'] - V.COST_STRESS
                                            for e in tr if e['day'] != best]))
        kk = max(1, int(round(0.01 * len(tr))))
        s['drop_top1pct'] = float(np.sort(g)[:-kk].mean())
        # HIGH-vs-random-state stratified permutation on the uncond pool
        upool = [e for e in uncond if e['gross'] is not None]
        by_year = collections.defaultdict(list)
        for e in upool:
            by_year[e['day'][:4]].append(e['gross'] - V.COST_STRESS)
        hi_by_year = collections.Counter(e['day'][:4] for e in tr)
        rng = np.random.default_rng(V.SEED_STATE)
        obs = float(np.mean([e['gross'] - V.COST_STRESS for e in tr]))
        cnt = 0
        for p in range(V.N_STATE):
            m, n = 0.0, 0
            for y, need in hi_by_year.items():
                pool = by_year[y]
                take = min(need, len(pool))
                ii = rng.integers(0, len(pool), take)
                m += sum(pool[i] for i in ii)
                n += take
            if m / n >= obs:
                cnt += 1
        s['state_perm_p'] = (cnt + 1) / (V.N_STATE + 1)
        R[name] = s

    ps = [R[n]['perm_p'] for n, _, _ in CELLS]
    qs = V.bh(ps)
    for (n, _, _), q in zip(CELLS, qs):
        R[n]['bh_q'] = q

    for name, k, xm in CELLS:
        s = R[name]
        fails = []
        if s['n'] < 200: fails.append('G01 n<200')
        if not (s['base'] > 0 and s['stressed'] > 0):
            fails.append('G05 not positive after costs')
        if s['pf_base'] < 1.30: fails.append('G06 base PF<1.30')
        if s['pf_stressed'] < 1.15: fails.append('G07 stressed PF<1.15')
        if s['base_R'] < 0.10: fails.append('G08 base EV<0.10R')
        if s['stressed_R'] < 0.05: fails.append('G09 stressed EV<0.05R')
        if s['ci_lo'] <= 0: fails.append('G10 CI LB<=0')
        if s['perm_p'] > 0.05: fails.append('G11 perm p>0.05')
        if s['bh_q'] > 0.05: fails.append('G12 BH q>0.05')
        if not (s['stressed'] > s['uncond'][1]):
            fails.append('G13 HIGH does not beat unconditional')
        if s['state_perm_p'] > 0.05:
            fails.append('G13b state-permutation p>0.05')
        ypos = sum(1 for y, (n_, m_) in s['years'].items() if n_ and m_ > 0)
        if ypos < 6: fails.append('G16 <6/8 years positive')
        npos = sum(1 for v in s['neigh'].values() if v[1] > 0)
        if npos < 3: fails.append('G15 neighbors not majority positive')
        if not (s['delay1'][1] > 0): fails.append('G-delay +1bar not positive')
        prof = ((s['win_base'] >= 0.38 and s['payoff_stressed'] >= 2.00)
                or (s['win_base'] >= 0.45 and s['payoff_stressed'] >= 1.50)
                or (s['win_base'] >= 0.55 and s['payoff_stressed'] >= 1.00)
                or (s['win_base'] >= 0.65 and s['payoff_stressed'] >= 0.70))
        if not prof: fails.append('G-profile none met')
        s['gate_fails'] = fails

    with open(os.path.join(HERE, 'VTBS_V1_TRADES.csv'), 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['cell', 'day', 'side', 'kind', 'R_pts', 'gross', 'stressed'])
        for name, _, _ in CELLS:
            for e in RAW[name]:
                if e['gross'] is None:
                    w.writerow([name, e['day'], 0, 'NOTRIG', '%.2f' % e['R'], '', ''])
                else:
                    w.writerow([name, e['day'], e['side'], e['kind'],
                                '%.2f' % e['R'], '%.2f' % e['gross'],
                                '%.2f' % (e['gross'] - V.COST_STRESS)])
    json.dump(R, open(os.path.join(HERE, 'VTBS_V1_RAW.json'), 'w'),
              indent=1, default=str)

    print('\n%-4s %5s %6s %9s %9s %9s %7s %7s %7s %8s %8s %8s' %
          ('cell', 'n', 'notrg', 'gross', 'base', 'stressed', 'PFb', 'PFs',
           'winB', 'perm_p', 'bh_q', 'state_p'))
    for name, k, xm in CELLS:
        s = R[name]
        print('%-4s %5d %6d %9.2f %9.2f %9.2f %7.3f %7.3f %6.1f%% %8.4f %8.4f %8.4f'
              % (name, s['n'], s['notrig'], s['gross'], s['base'],
                 s['stressed'], s['pf_base'], s['pf_stressed'],
                 100 * s['win_base'], s['perm_p'], s['bh_q'],
                 s['state_perm_p']))
        print('     CI[%.2f,%.2f] R(base) %.3f  uncond %.2f  low %.2f  '
              'L %.2f / S %.2f  whip %d  stop %d'
              % (s['ci_lo'], s['ci_hi'], s['base_R'], s['uncond'][1],
                 s['low'][1], s['long'][1], s['short'][1], s['whipsaw_n'],
                 s['stop_n']))
        print('     years ' + '  '.join('%s:%+.1f(%d)' % (y, m_, n_)
                                        for y, (n_, m_) in s['years'].items()))
        print('     neigh ' + '  '.join('%s:%+.1f' % (kk, v[1])
                                        for kk, v in s['neigh'].items())
              + '  delay1:%+.1f  dropbest:%+.1f  droptop1%%:%+.1f'
              % (s['delay1'][1], s['drop_best_day'], s['drop_top1pct']))
        print('     fails: %s' % ('; '.join(s['gate_fails']) or 'NONE'))
    n_pass = sum(1 for n, _, _ in CELLS if not R[n]['gate_fails'])
    print('\ncells passing every gate: %d / 4' % n_pass)
    return n_pass


if __name__ == '__main__':
    main()
