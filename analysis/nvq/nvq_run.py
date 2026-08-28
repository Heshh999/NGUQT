#!/usr/bin/env python3
# ======================================================================
# NVQ-V1  -  FROZEN ONE-SHOT RUN  (novel question classes)
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mtf'))
import mtf_lib as M  # noqa: E402  (loader + bootstrap helpers reused)

t0 = time.time()
D = M.load()
N = len(D['c'])
print('NVQ-V1 one-shot   DEV %s..%s   1m bars %d'
      % (min(D['day']), max(D['day']), N))

byday = collections.defaultdict(list)
for i in range(N):
    byday[D['day'][i]].append(i)
days = sorted(byday)
OUT = {}
cells = []            # (name, effect_desc, p)

# =====================================================================
# MODULE V  -  volume-clock structure
# =====================================================================
print('\n' + '=' * 86)
print('MODULE V  -  VOLUME-CLOCK STRUCTURE  (first use of event-time sampling)')
print('=' * 86)

# per-day RTH volume + causal targets
rthvol = {}
for d in days:
    v = sum(D['v'][i] for i in byday[d] if 571 <= D['mod'][i] <= 960)
    nb = sum(1 for i in byday[d] if 571 <= D['mod'][i] <= 960)
    if nb >= 300:
        rthvol[d] = v

for K in (78, 26):
    # build volume bars per day
    rets, retdays = [], []          # adjacent-bar log returns
    day_sums = []                   # for VR(6): per-day non-overlap 6-sums
    for k, d in enumerate(days):
        prior = [rthvol[e] for e in days[max(0, k - 20):k] if e in rthvol]
        if len(prior) < 10 or d not in rthvol:
            continue
        target = np.mean(prior) / K
        closes = []
        acc = 0.0
        for i in byday[d]:
            if not (571 <= D['mod'][i] <= 960):
                continue
            acc += D['v'][i]
            if acc >= target:
                closes.append(D['c'][i])
                acc = 0.0
        r = np.diff(np.log(closes)) if len(closes) > 2 else np.array([])
        for x in r:
            rets.append(x); retdays.append(d)
        if len(r) >= 6:
            q = 6
            m = len(r) // q
            sums = r[:m * q].reshape(m, q).sum(axis=1)
            day_sums.append((d, r, sums))
    rets = np.array(rets)
    # lag-1 / lag-2 AC within day
    for lag in (1, 2):
        prod, pd_ = [], []
        # recompute within-day products
        idx = 0
        by_d = collections.defaultdict(list)
        for x, d in zip(rets, retdays):
            by_d[d].append(x)
        mu = rets.mean(); sd = rets.std()
        for d, xs in by_d.items():
            xs = np.array(xs)
            for j in range(lag, len(xs)):
                prod.append((xs[j] - mu) * (xs[j - lag] - mu) / (sd * sd))
                pd_.append(d)
        ac, lo, hi = M.day_boot_mean(prod, pd_, 5000, 20260901 + K + lag)
        se = (hi - lo) / 3.92 if hi > lo else 1e9
        from math import erf, sqrt
        p = 2 * (1 - 0.5 * (1 + erf(abs(ac) / se / sqrt(2)))) if se > 0 else 1.0
        cells.append(('V_K%d_lag%d' % (K, lag), '%+.4f' % ac, p))
        print('  K=%2d lag%d  n %7d  AC %+0.4f  CI[%+0.4f,%+0.4f]%s'
              % (K, lag, len(prod), ac, lo, hi,
                 ' *' if (lo > 0 or hi < 0) else ''))
    # VR(6): per-day variance of 6-sums vs 6x variance of singles
    vr_terms, vr_days = [], []
    gmu = rets.mean()
    gv = rets.var()
    for d, r, sums in day_sums:
        for s in sums:
            vr_terms.append(((s - 6 * gmu) ** 2) / (6 * gv))
            vr_days.append(d)
    vr, lo, hi = M.day_boot_mean(vr_terms, vr_days, 5000, 20260905 + K)
    se = (hi - lo) / 3.92 if hi > lo else 1e9
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(vr - 1) / se / sqrt(2)))) if se > 0 else 1.0
    cells.append(('V_K%d_VR6' % K, '%.4f' % vr, p))
    print('  K=%2d VR(6)  n %6d  VR %0.4f  CI[%0.4f,%0.4f]%s'
          % (K, len(vr_terms), vr, lo, hi,
             ' *' if (lo > 1 or hi < 1) else ''))

# =====================================================================
# MODULE D  -  day-type taxonomy
# =====================================================================
print('\n' + '=' * 86)
print('MODULE D  -  DAY-TYPE TAXONOMY  (NR7 / inside / outside / trend / streaks)')
print('=' * 86)
# daily RTH OHLC
dd = []
for d in days:
    idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
    if len(idx) < 300:
        continue
    dd.append(dict(day=d, o=D['o'][idx[0]],
                   h=max(D['h'][i] for i in idx),
                   l=min(D['l'][i] for i in idx),
                   c=D['c'][idx[-1]]))
print('  daily rows %d' % len(dd))
cl = np.array([x['c'] for x in dd])
ret1 = np.append(np.diff(np.log(cl)) * 1e4, np.nan)     # next-day, bp at t
rng_ = np.array([x['h'] - x['l'] for x in dd])

types = collections.defaultdict(list)   # name -> list of t indices
for t in range(20, len(dd) - 1):
    r7 = rng_[t - 6:t + 1]
    med20 = np.median(rng_[t - 20:t])
    if rng_[t] == r7.min():
        types['NR7'].append(t)
    if rng_[t] == r7.max():
        types['WR7'].append(t)
    inside = dd[t]['h'] < dd[t - 1]['h'] and dd[t]['l'] > dd[t - 1]['l']
    outside = dd[t]['h'] > dd[t - 1]['h'] and dd[t]['l'] < dd[t - 1]['l']
    if inside:
        types['INSIDE'].append(t)
        if rng_[t] == r7.min():
            types['INSIDE_NR7'].append(t)
    if outside:
        types['OUTSIDE'].append(t)
    loc = (dd[t]['c'] - dd[t]['l']) / rng_[t] if rng_[t] > 0 else 0.5
    if loc >= 0.9 and rng_[t] >= med20:
        types['TREND_UP'].append(t)
    if loc <= 0.1 and rng_[t] >= med20:
        types['TREND_DN'].append(t)
    # streaks (signed AGAINST the streak = reversal convention, frozen)
    s = np.sign(np.diff(np.log(cl[max(0, t - 6):t + 1])))
    def streak_len(s):
        n = 0
        for x in s[::-1]:
            if x == s[-1] and x != 0:
                n += 1
            else:
                break
        return n, s[-1]
    sl, sgn = streak_len(s)
    if sl == 3:
        types['STREAK3_UP' if sgn > 0 else 'STREAK3_DN'].append(t)
    if sl >= 4:
        types['STREAK4PLUS'].append(t)

uncond = np.nanmean(ret1[20:len(dd) - 1])
print('  unconditional next-day mean %+0.2f bp' % uncond)
ORDER = ['NR7', 'WR7', 'INSIDE', 'OUTSIDE', 'TREND_UP', 'TREND_DN',
         'INSIDE_NR7', 'STREAK3_UP', 'STREAK3_DN', 'STREAK4PLUS']
for name in ORDER:
    ts = types[name]
    if name == 'STREAK3_UP':
        vals = [-ret1[t] for t in ts if ret1[t] == ret1[t]]      # reversal
        lab = 'reversal bp'
    elif name == 'STREAK3_DN':
        vals = [ret1[t] for t in ts if ret1[t] == ret1[t]]       # reversal
        lab = 'reversal bp'
    elif name == 'STREAK4PLUS':
        vals = []
        for t in ts:
            if ret1[t] == ret1[t]:
                s = np.sign(np.log(cl[t] / cl[t - 1]))
                vals.append(-s * ret1[t])
        lab = 'reversal bp'
    else:
        vals = [ret1[t] for t in ts if ret1[t] == ret1[t]]
        lab = 'next-day bp'
    if len(vals) < 30:
        print('  %-12s n %4d  INSUFFICIENT (<30)' % (name, len(vals)))
        continue
    m_, lo, hi = M.stationary_boot_mean(vals, 5000, 20260902 + hash(name) % 1000)
    se = (hi - lo) / 3.92 if hi > lo else 1e9
    from math import erf, sqrt
    p = 2 * (1 - 0.5 * (1 + erf(abs(m_) / se / sqrt(2)))) if se > 0 else 1.0
    pts_ = m_ / 1e4 * float(np.mean(cl))
    cells.append(('D_' + name, '%+.1f bp' % m_, p))
    print('  %-12s n %4d  %s %+7.2f  CI[%+7.2f,%+7.2f]  (%+.1f pts vs 0.87 cost)%s'
          % (name, len(vals), lab, m_, lo, hi, pts_,
             ' *' if (lo > 0 or hi < 0) else ''))

# =====================================================================
# BH across the family
# =====================================================================
qs = M.bh([p for _, _, p in cells])
print('\nBH FAMILY (%d cells):' % len(cells))
nsig = 0
for (name, eff, p), q in zip(cells, qs):
    flag = 'PASS-q' if q <= 0.05 else ''
    nsig += q <= 0.05
    print('  %-14s  effect %-10s p %.5f  q %.5f  %s' % (name, eff, p, q, flag))
print('\ncells surviving BH q<=0.05: %d of %d' % (nsig, len(cells)))
json.dump(dict(cells=[(n, e, p, q) for (n, e, p), q in zip(cells, qs)]),
          open(os.path.join(HERE, 'NVQ_V1_RAW.json'), 'w'), indent=1)
print('done in %.0fs' % (time.time() - t0))
