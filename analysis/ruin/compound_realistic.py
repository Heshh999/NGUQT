#!/usr/bin/env python3
# Compounding with the constraints the naive sim ignores:
#  (a) edge decay - historical edge is in-sample; assume it fades
#  (b) a hard cap on contracts (capacity / discipline ceiling)
#  (c) explicit "stop compounding at target" behaviour
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
import re, os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
net = []
for ln in open(os.path.join(HERE, '..', 'ofh13mem', 'EVENT_LISTING.txt')):
    m = re.search(r'\s([+-]\d+\.\d\d)\s+(WIN|LOSS)', ln)
    if m: net.append(float(m.group(1)))
pts = np.array(net); PV = 2.0
START, TARGET, MARGIN, TPM, B, MONTHS = 2500.0, 100000.0, 100.0, 133/12.0, 60000, 120


def run(cap, mult, half_life_yrs, max_ct, seed):
    """half_life_yrs: months until per-trade edge halves (None = never).
    Edge decay is applied by shrinking the mean, keeping the shape."""
    rng = np.random.default_rng(seed)
    base = np.where(pts < 0, pts * mult, pts) * PV
    mu = base.mean(); centered = base - mu
    eq = np.full(B, START); n = np.maximum(1, np.floor(eq/cap)).astype(int)
    alive = np.ones(B, bool); hit = np.zeros(B, bool); hm = np.full(B, -1)
    peak = eq.copy(); maxdd = np.zeros(B)
    for m in range(MONTHS):
        f = 1.0 if half_life_yrs is None else 0.5 ** ((m/12.0)/half_life_yrs)
        k = rng.poisson(TPM, B); mx = max(1, k.max())
        idx = rng.integers(0, len(base), size=(B, mx))
        draws = centered[idx] + mu*f
        mask = np.arange(mx)[None,:] < k[:,None]
        for j in range(mx):
            eq = eq + draws[:,j]*mask[:,j]*n*alive
            alive &= ~(alive & (eq < MARGIN))
            eq = np.where(alive, eq, 0.0)
        peak = np.maximum(peak, eq)
        maxdd = np.maximum(maxdd, (peak-eq)/np.maximum(peak,1e-9))
        newly = alive & ~hit & (eq >= TARGET); hm = np.where(newly, m+1, hm); hit |= newly
        if (m+1) % 6 == 0:
            n = np.clip(np.maximum(1, np.floor(eq/cap)).astype(int), 1, max_ct)
            n = np.where(alive, n, 1)
    med = np.median(hm[hit]) if hit.any() else float('nan')
    return (100*hit.mean(), 100*(~alive).mean(), med,
            np.median(eq), 100*np.median(maxdd))


print('=' * 100)
print('REALISTIC: losses x1.5, edge HALVES every 3 years, max 20 MNQ contracts')
print('=' * 100)
print('  %-26s %10s %8s %12s %12s %9s' %
      ('$ equity per contract', 'reach100k', 'ruin', 'medMonths', 'medEquity10y', 'medMaxDD'))
for cap in (1250, 2500, 3500, 5000, 7500, 10000, 10**9):
    r = run(cap, 1.5, 3.0, 20, 500+min(cap,99999))
    lab = 'never size up (1 ct)' if cap > 10**8 else '$%d' % cap
    print('  %-26s %9.1f%% %7.1f%% %12s %12.0f %8.0f%%'
          % (lab, r[0], r[1], ('%.0f'%r[2]) if r[2]==r[2] else 'n/a', r[3], r[4]))

print()
print('=' * 100)
print('SENSITIVITY: how the answer moves with how good the edge really is')
print('($5,000 per contract, max 20 contracts, no decay vs 3-year half-life)')
print('=' * 100)
print('  %-30s %10s %8s %12s' % ('scenario', 'reach100k', 'ruin', 'medMonths'))
for mult, hl, lab in ((1.0, None, 'in-sample edge, no decay (fantasy)'),
                      (1.0, 5.0,  'in-sample edge, 5y half-life'),
                      (1.25, 3.0, 'losses x1.25, 3y half-life'),
                      (1.5, 3.0,  'losses x1.5,  3y half-life'),
                      (1.5, 1.5,  'losses x1.5,  1.5y half-life'),
                      (1.75, 2.0, 'losses x1.75, 2y half-life')):
    r = run(5000, mult, hl, 20, 909)
    print('  %-30s %9.1f%% %7.1f%% %12s'
          % (lab, r[0], r[1], ('%.0f'%r[2]) if r[2]==r[2] else 'n/a'))
