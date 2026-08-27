#!/usr/bin/env python3
# LPCC-V1 Phase A - deterministic reproduction of the Wave 4
# S4latePM q=30 variance-ratio cell from COMMITTED code paths only.
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L

SEED = 20260828                      # Wave 4 committed seed
G = L.load()
N = G['N']
mod, td = G['mod'], G['tradedate']
c, em, step1 = G['c'], G['em'], G['step1']
r1 = np.full(N, np.nan)
ok = step1.copy(); ok &= c > 0
ok[1:] &= c[:-1] > 0
idx = np.nonzero(ok)[0]; idx = idx[idx >= 1]
r1[idx] = np.log(c[idx] / c[idx - 1]) * 1e4
a, b_ = 481, 569                     # committed S4latePM close stamps
qq = 30
m = (mod >= a) & (mod <= b_) & ~np.isnan(r1)
ii = np.nonzero(m)[0]
byday = collections.defaultdict(list)
for i in ii:
    byday[td[i]].append(i)
s1 = []; sq = []; dl1 = []; dlq = []
for d0, lst in byday.items():
    arr = r1[np.array(lst)]
    s1.append(arr); dl1 += [d0] * len(arr)
    nb = len(arr) // qq
    if nb:
        sq.append(arr[:nb * qq].reshape(nb, qq).sum(1))
        dlq += [d0] * nb
v1 = np.concatenate(s1); vq = np.concatenate(sq)
uds = sorted(byday); di = {d: k for k, d in enumerate(uds)}
ss1 = np.zeros(len(uds)); n1 = np.zeros(len(uds))
ssq = np.zeros(len(uds)); nq = np.zeros(len(uds))
mu1 = v1.mean(); muq = vq.mean()
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
cell = [x for x in pub['B'] if x['stratum'] == 'S4latePM' and x['q'] == 30][0]
print('recomputed  VR30 %.6f  CI [%.6f, %.6f]  days %d  q-windows %d'
      % (vr, lo, hi, len(uds), len(vq)))
print('published   VR30 %.6f  CI [%.6f, %.6f]  BH q %.4f  n %d'
      % (cell['VR'], cell['lo'], cell['hi'], cell['q_bh'],
         cell['nq_windows']))
exact = (abs(vr - cell['VR']) < 1e-9 and abs(lo - cell['lo']) < 1e-9
         and abs(hi - cell['hi']) < 1e-9 and len(vq) == cell['nq_windows'])
print('REPRODUCTION:', 'EXACT' if exact else 'MISMATCH')
# window bookkeeping for the freeze
per_day_windows = collections.Counter()
for d0, lst in byday.items():
    per_day_windows[len(lst) // qq] += 1
print('per-day complete 30-bar windows histogram:', dict(per_day_windows))
json.dump({'vr': vr, 'lo': float(lo), 'hi': float(hi), 'days': len(uds),
           'windows': len(vq), 'exact': bool(exact),
           'stratum_stamps': [a, b_], 'first_window_stamps': [481, 510]},
          open(os.path.join(HERE, 'provenance_vr.json'), 'w'))
sys.exit(0 if exact else 1)
