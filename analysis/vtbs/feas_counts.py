#!/usr/bin/env python3
# VTBS-V1 predictor-only feasibility counts. NO outcome, NO trigger
# rates, NO P&L - day eligibility and state counts only.
import collections, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
import numpy as np
import rvmr_run as RV
RV.STAMP_SHIFT = 0
D = RV.load_bars()
DEV_LAST = '2026-08-17'
byday = collections.defaultdict(list)
for i in range(len(D['c'])):
    et = D['et'][i]
    if et[:10] > DEV_LAST:
        continue
    mm = int(et[11:13]) * 60 + int(et[14:16])
    byday[et[:10]].append((mm, D['o'][i], D['h'][i], D['l'][i], D['c'][i]))
days = sorted(byday)
rr, on, valid = {}, {}, []
for k, d in enumerate(days):
    rth = [b for b in byday[d] if 571 <= b[0] <= 960]
    if len(rth) >= 300:
        rr[d] = max(b[2] for b in rth) - min(b[3] for b in rth)
    if k == 0:
        continue
    w = ([b for b in byday[days[k-1]] if b[0] >= 1081]
         + [b for b in byday[d] if 0 < b[0] <= 569])
    if len(w) >= 200:
        on[d] = max(b[2] for b in w) - min(b[3] for b in w)
P = {}
hist_rr, hist_P = [], []
n_valid = n_high = 0
for k, d in enumerate(days):
    prior_rr = [rr[e] for e in days[max(0,k-60):k] if e in rr]
    if len(prior_rr) >= 40 and d in on and d in rr and \
       any(b[0] == 571 for b in byday[d]):
        base = float(np.quantile(prior_rr, 0.5))
        p = on[d] / base
        prior_P = [P[e] for e in days[max(0,k-60):k] if e in P]
        P[d] = p
        if len(prior_P) >= 40:
            n_valid += 1
            if p >= float(np.quantile(prior_P, 0.75)):
                n_high += 1
    elif d in on and d in rr:
        P[d] = None; P.pop(d)
print('days total (DEV) %d' % len(days))
print('eligible days (valid base+predictor+entry bar) %d' % n_valid)
print('HIGH-state days (causal Q75)                   %d' % n_high)
print('PREDICTOR-ONLY COUNTS COMPLETE. No outcome computed.')
