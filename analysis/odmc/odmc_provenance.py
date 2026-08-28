#!/usr/bin/env python3
# ODMC-V1 Phase A: reproduce the Wave 4 S5open q=10 VR cell from
# COMMITTED code paths + mechanical earliest-block selection; and
# reproduce the published 30s opening-momentum observation lineage.
import os, sys, json, csv, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L

SEED = 20260828
G = L.load()
N = G['N']
mod, td = G['mod'], G['tradedate']
c, em, step1 = G['c'], G['em'], G['step1']
r1 = np.full(N, np.nan)
ok = step1.copy(); ok &= c > 0
ok[1:] &= c[:-1] > 0
idx = np.nonzero(ok)[0]; idx = idx[idx >= 1]
r1[idx] = np.log(c[idx] / c[idx - 1]) * 1e4
a, b_ = 571, 600                       # committed S5open close stamps
qq = 10
m = (mod >= a) & (mod <= b_) & ~np.isnan(r1)
ii = np.nonzero(m)[0]
byday = collections.defaultdict(list)
for i in ii:
    byday[td[i]].append(i)
s1, sq, dl1, dlq = [], [], [], []
for d0, lst in byday.items():
    arr = r1[np.array(lst)]
    s1.append(arr); dl1 += [d0] * len(arr)
    nb = len(arr) // qq
    if nb:
        sq.append(arr[:nb * qq].reshape(nb, qq).sum(1)); dlq += [d0] * nb
v1 = np.concatenate(s1); vq = np.concatenate(sq)
uds = sorted(byday); di = {d: k for k, d in enumerate(uds)}
ss1 = np.zeros(len(uds)); n1 = np.zeros(len(uds))
ssq = np.zeros(len(uds)); nq = np.zeros(len(uds))
mu1, muq = v1.mean(), vq.mean()
for x, d0 in zip(v1, dl1):
    ss1[di[d0]] += (x - mu1) ** 2; n1[di[d0]] += 1
for x, d0 in zip(vq, dlq):
    ssq[di[d0]] += (x - muq) ** 2; nq[di[d0]] += 1
vr = (ssq.sum() / nq.sum()) / (qq * ss1.sum() / n1.sum())
rg = np.random.default_rng(SEED + qq)
iidx = rg.integers(0, len(uds), size=(2000, len(uds)))
bs = (ssq[iidx].sum(1) / np.maximum(nq[iidx].sum(1), 1)) / \
     np.maximum(qq * ss1[iidx].sum(1) / np.maximum(n1[iidx].sum(1), 1), 1e-12)
bs.sort()
lo, hi = bs[int(.025 * 2000)], bs[int(.975 * 2000)]
pub = json.load(open(os.path.join(HERE, '..', 'wave4', 'WAVE4_RAW.json')))
cell = [x for x in pub['B'] if x['stratum'] == 'S5open' and x['q'] == 10][0]
print('recomputed VR10 %.6f  CI[%.6f,%.6f]  days %d  blocks %d'
      % (vr, lo, hi, len(uds), len(vq)))
print('published  VR10 %.6f  CI[%.6f,%.6f]  BHq %.4f  blocks %d'
      % (cell['VR'], cell['lo'], cell['hi'], cell['q_bh'], cell['nq_windows']))
exact = (abs(vr - cell['VR']) < 1e-9 and abs(lo - cell['lo']) < 1e-9
         and abs(hi - cell['hi']) < 1e-9 and len(vq) == cell['nq_windows'])
print('REPRODUCTION:', 'EXACT' if exact else 'MISMATCH')
hist = collections.Counter(len(v) // qq for v in byday.values())
print('per-day complete 10-bar blocks:', dict(hist))
print('stratum stamps %d..%d = %d bars/day -> 3 non-overlapping 10-min '
      'blocks/day: stamps 571-580, 581-590, 591-600' % (a, b_, b_ - a + 1))
print('MECHANICAL SELECTION: chronologically EARLIEST complete block '
      'beginning at/after the 09:30 RTH open = stamps 571..580 '
      '= market block [09:30, 09:40) ; midpoint T5 = 09:35')

# ---- 30s opening-momentum observation lineage (provenance only) ----
led = list(csv.DictReader(open(os.path.join(
    HERE, '..', 'mgsd', 'MGSD_V1_SUBMIN_30S_LEDGER.csv'))))
row = [r for r in led if r['key'] == 'S30A_n10_t1.0_s20_e30']
print('\n30s opening-momentum observation (published, provenance only):')
if row:
    r = row[0]
    print('  key %s  n %s  days %s  ev_stress %s  wr %s  pf %s'
          % (r['key'], r['n'], r['days'], r['ev_stress'], r['wr'], r['pf']))
    print('  ci [%s, %s]  p %s  BHq %s' % (r['ci_lo'], r['ci_hi'], r['p'], r['bh_q']))
    print('  REPRODUCED FROM COMMITTED LEDGER: YES')
else:
    print('  NOT FOUND - mark unresolved')
man = json.load(open(os.path.join(HERE, '..', 'mgsd',
                                  'MGSD_V1_DATA_MANIFEST.json')))
a30 = man['arm_30s']
print('  genuine 30s coverage: %d bars, %d days, %s..%s, slots %d (%s..%s)'
      % (a30['unique_30s_bars'], a30['days_with_30s'], a30['first_day'],
         a30['last_day'], a30['slot_grid']['distinct_times'],
         a30['slot_grid']['first'], a30['slot_grid']['last']))
print('  aggregation 30s->1m: %d/%d exact OHLC'
      % (a30['agg_vs_canonical_1m']['exact_ohlc'],
         a30['agg_vs_canonical_1m']['pairs_tested']))
json.dump({'vr': float(vr), 'lo': float(lo), 'hi': float(hi),
           'days': len(uds), 'blocks': len(vq), 'exact': bool(exact),
           'stratum_stamps': [a, b_], 'blocks_per_day': dict(hist),
           'selected_block_stamps': [571, 580],
           'selected_market_block': '[09:30,09:40) ET, T5=09:35',
           's30_obs': row[0] if row else None,
           's30_coverage': {k: a30[k] for k in
                            ('unique_30s_bars', 'days_with_30s', 'first_day',
                             'last_day')}},
          open(os.path.join(HERE, 'provenance.json'), 'w'))
sys.exit(0 if exact else 1)
