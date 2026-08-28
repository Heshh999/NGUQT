#!/usr/bin/env python3
# ======================================================================
# MTF-V1  -  FROZEN ONE-SHOT RUN  (complete search, no early stop)
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mtf_lib as M  # noqa: E402

t0 = time.time()
D = M.load()
print('MTF-V1 one-shot   DEV %s..%s   1m bars %d   (%.0fs)'
      % (min(D['day']), max(D['day']), len(D['c']), time.time() - t0))
OUT = {}

# =====================================================================
# MODULE A  -  descriptive multi-scale map
# =====================================================================
print('\n' + '=' * 88)
print('MODULE A  -  DESCRIPTIVE MULTI-SCALE MAP  (ledgered, never promotable)')
print('=' * 88)
A = {}
pA = []

print('A1  T-bar return autocorrelation (day-clustered CIs)')
for T in (5, 15, 30, 60, 240):
    tb = M.tbars(D, T)
    idx, r = M.contiguous_returns(tb)
    days = [tb['day'][i] for i in idx]
    for lag in (1, 2):
        x, y, dd = [], [], []
        for k in range(lag, len(r)):
            if idx[k] - idx[k - lag] == lag:      # chain contiguity
                x.append(r[k - lag]); y.append(r[k]); dd.append(days[k])
        x = np.array(x); y = np.array(y)
        sx, sy = x.std(), y.std()
        prod = (x - x.mean()) * (y - y.mean()) / (sx * sy)
        ac, lo, hi = M.day_boot_mean(prod, dd, 5000, M.SEED_A1 + T + lag)
        signif = (lo > 0) or (hi < 0)
        key = 'A1_T%d_lag%d' % (T, lag)
        A[key] = dict(n=len(x), ac=ac, lo=lo, hi=hi)
        # crude two-sided p from bootstrap z for BH ledger
        se = (hi - lo) / 3.92 if hi > lo else 1e9
        from math import erf, sqrt
        p = 2 * (1 - 0.5 * (1 + erf(abs(ac) / se / sqrt(2)))) if se > 0 else 1.0
        pA.append((key, p))
        print('   T=%3dm lag%d  n %7d  AC %+0.4f  CI[%+0.4f,%+0.4f] %s'
              % (T, lag, len(x), ac, lo, hi, '*' if signif else ''))

print('A2  daily momentum spectrum (up-minus-down next-day mean, bp)')
byday = {}
for i in range(len(D['c'])):
    if D['mod'][i] <= 960:
        byday[D['day'][i]] = D['c'][i]
days = sorted(byday)
cl = np.array([byday[d] for d in days])
ret1 = np.log(cl[1:] / cl[:-1])                     # next-day returns
for k in (1, 2, 3, 5, 10, 20):
    diffs = []
    for t in range(k, len(cl) - 1):
        s = 1.0 if cl[t] > cl[t - k] else -1.0
        diffs.append(s * ret1[t] * 1e4)
    m, lo, hi = M.stationary_boot_mean(diffs, 5000, M.SEED_A2 + k)
    signif = (lo > 0) or (hi < 0)
    key = 'A2_k%d' % k
    A[key] = dict(n=len(diffs), mean_bp=m, lo=lo, hi=hi)
    se = (hi - lo) / 3.92 if hi > lo else 1e9
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(m) / se / sqrt(2)))) if se > 0 else 1.0
    pA.append((key, p))
    print('   k=%2dd  n %4d  sign-aligned next-day %+7.2f bp  CI[%+7.2f,%+7.2f] %s'
          % (k, len(diffs), m, lo, hi, '*' if signif else ''))

print('A3  cross-scale alignment (15m vs 240m sign -> next 60m, bp)')
tb15 = M.tbars(D, 15); tb240 = M.tbars(D, 240)
i15, r15 = M.contiguous_returns(tb15)
r240_by_end = {}
i240, r240 = M.contiguous_returns(tb240)
for k, i in enumerate(i240):
    r240_by_end[tb240['bid'][i]] = r240[k]
al, cf, ald, cfd = [], [], [], []
last_used_bid15 = -10
for k, i in enumerate(i15):
    b15 = tb15['bid'][i]
    if b15 - last_used_bid15 < 4:                   # non-overlap 60m steps
        continue
    b240 = (b15 * 15) // 240 - 1                    # last COMPLETED 240m
    if b240 not in r240_by_end:
        continue
    # forward 60m = next 4 contiguous 15m returns
    if k + 4 >= len(r15) or i15[k + 4] - i != 4:
        continue
    fwd = float(np.sum(r15[k + 1:k + 5])) * 1e4
    s15, s240 = np.sign(r15[k]), np.sign(r240_by_end[b240])
    if s15 == 0 or s240 == 0:
        continue
    sgn = s15                                        # trade in 15m direction
    if s15 == s240:
        al.append(sgn * fwd); ald.append(tb15['day'][i])
    else:
        cf.append(sgn * fwd); cfd.append(tb15['day'][i])
    last_used_bid15 = b15
obs, lo, hi, p = M.day_boot_diff(al, ald, cf, cfd, 5000, M.SEED_A1)
A['A3_align'] = dict(n_aligned=len(al), n_conflict=len(cf), diff_bp=obs,
                     lo=lo, hi=hi, p=p)
pA.append(('A3_align', p))
print('   aligned n %d (%+.2f bp)  conflicted n %d (%+.2f bp)  '
      'diff %+0.2f  CI[%+0.2f,%+0.2f]  p %.4f'
      % (len(al), np.mean(al), len(cf), np.mean(cf), obs, lo, hi, p))

qsA = M.bh([p for _, p in pA])
A['bh'] = {k: q for (k, _), q in zip(pA, qsA)}
nsigA = sum(1 for q in qsA if q <= 0.05)
print('  Module A BH: %d of %d cells q<=0.05' % (nsigA, len(qsA)))
OUT['A'] = A

# =====================================================================
# MODULE B1  -  V-TURN-SCALE  (confirmatory, 4 cells)
# =====================================================================
print('\n' + '=' * 88)
print('MODULE B1  -  ORDINAL V-TURN AT SCALE   (confirmed-at-1m anomaly, new scales)')
print('=' * 88)
B1 = {}
pB = []
for T in (5, 15, 30, 60):
    ev = M.vturn_events(D, T)
    mot = np.array([e['motif'] for e in ev])
    ta = np.array([e['ta'] for e in ev])
    dd = [e['day'] for e in ev]
    px = np.array([e['price'] for e in ev])
    isV = np.isin(mot, [M.VUP, M.VDN])
    isE = np.isin(mot, [M.EUP, M.EDN])
    obs, lo, hi, p = M.day_boot_diff(
        ta[isV], [d for d, m in zip(dd, isV) if m],
        ta[isE], [d for d, m in zip(dd, isE) if m], 10000, M.SEED_B1 + T)
    evV_bp = float(ta[isV].mean())
    pts = evV_bp / 1e4 * float(px[isV].mean())      # E[ta|V] in points
    B1['T%d' % T] = dict(n=len(ev), nV=int(isV.sum()), nE=int(isE.sum()),
                         dturn_bp=obs, lo=lo, hi=hi, p=p,
                         evV_bp=evV_bp, evV_pts=pts)
    pB.append(('B1_T%d' % T, p))
    print(' T=%3dm  n %7d (V %6d / E %6d)  Dturn %+0.3f bp  '
          'CI[%+0.3f,%+0.3f]  p %.5f   E[ta|V] %+0.3f bp = %+0.3f pts (cost 0.87)'
          % (T, len(ev), isV.sum(), isE.sum(), obs, lo, hi, p, evV_bp, pts))
OUT['B1'] = B1

# =====================================================================
# MODULE B2  -  VWAP-OU-CLOCK  (confirmatory, 1 cell + frozen neighbors)
# =====================================================================
print('\n' + '=' * 88)
print('MODULE B2  -  VWAP REVERSION AT THE MEASURED 106-MIN OU CLOCK')
print('=' * 88)
ev = M.b2_run(D, q=0.90, exit_min=212)
s = M.strat_stats(ev)
kinds = collections.Counter(e['kind'] for e in ev)
print(' PRIMARY q90/212m  n %d  days %d  %s' % (s['n'], s['days'], dict(kinds)))
print('   gross %+0.3f  base %+0.3f  stressed %+0.3f pt   R(base) %+0.3f'
      % (s['gross'], s['base'], s['stressed'], s['base_R']))
print('   PF %0.3f/%0.3f  win %0.1f%%  payoff %0.2f  CI[%+0.3f,%+0.3f]  perm p %.4f'
      % (s['pf_base'], s['pf_stressed'], 100 * s['win_base'], s['payoff'],
         s['ci_lo'], s['ci_hi'], s['perm_p']))
print('   years ' + '  '.join('%s:%+0.2f(%d)' % (y, m_, n_)
                              for y, (n_, m_) in s['years'].items()))
pB.append(('B2', s['perm_p']))
OUT['B2'] = dict(primary=s, kinds=dict(kinds))
for lab, qq, xm in (('q85', 0.85, 212), ('q95', 0.95, 212),
                    ('exit106', 0.90, 106), ('exit318', 0.90, 318)):
    evn = M.b2_run(D, q=qq, exit_min=xm)
    stn = np.mean([e['gross'] for e in evn]) - M.COST_STRESS if evn else float('nan')
    OUT['B2'][lab] = dict(n=len(evn), stressed=float(stn))
    print('   neighbor %-8s n %5d  stressed %+0.3f pt' % (lab, len(evn), stn))

# ---- confirmatory BH family -----------------------------------------
qs = M.bh([p for _, p in pB])
print('\nCONFIRMATORY FAMILY (5 cells) BH:')
verdicts = {}
for (k, p), q in zip(pB, qs):
    verdicts[k] = q
    print('   %-8s p %.5f  q %.5f  %s' % (k, p, q,
          'PASS-q' if q <= 0.05 else 'fail'))
OUT['bh_confirmatory'] = verdicts

json.dump(OUT, open(os.path.join(HERE, 'MTF_V1_RAW.json'), 'w'),
          indent=1, default=str)
print('\ndone in %.0fs' % (time.time() - t0))
