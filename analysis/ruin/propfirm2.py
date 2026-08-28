#!/usr/bin/env python3
# Phase 1: EVALUATION - path stops the moment the target is hit.
# Phase 2: FUNDED   - survive 12 months and take payouts.
import json, numpy as np
R = np.load('/tmp/ofh13_rows.npy'); PV = 2.0
mfe, net = R[:, 0], R[:, 2]
B = 40000; TPD = 133 / 108.0
ACCTS = [('50k', 3000., 2500., 1100.), ('100k', 6000., 3000., 2200.),
         ('150k', 9000., 5000., 3300.)]

def evaluate(target, trail, daily, ct, intra, seed, max_days=250):
    rng = np.random.default_rng(seed)
    eq = np.zeros(B); peak = np.zeros(B)
    live = np.ones(B, bool)          # still attempting
    passed = np.zeros(B, bool); blown = np.zeros(B, bool)
    pd_ = np.full(B, -1)
    for day in range(max_days):
        k = rng.poisson(TPD, B); mx = max(1, k.max())
        idx = rng.integers(0, len(net), size=(B, mx)); dpl = np.zeros(B)
        for j in range(mx):
            act = live & (j < k)
            tn = net[idx[:, j]] * PV * ct; tm = mfe[idx[:, j]] * PV * ct
            if intra: peak = np.where(act, np.maximum(peak, eq + tm), peak)
            eq = np.where(act, eq + tn, eq); dpl = np.where(act, dpl + tn, dpl)
            if not intra: peak = np.where(act, np.maximum(peak, eq), peak)
            b = live & (((peak - eq) >= trail) | (dpl <= -daily))
            blown |= b; live &= ~b
            p = live & (eq >= target)
            passed |= p; pd_ = np.where(p & (pd_ < 0), day + 1, pd_); live &= ~p
    return passed, blown, pd_

def funded(trail, daily, ct, intra, seed, days=250):
    """After funding: survive a year, measure payout-able profit."""
    rng = np.random.default_rng(seed)
    eq = np.zeros(B); peak = np.zeros(B); live = np.ones(B, bool)
    for day in range(days):
        k = rng.poisson(TPD, B); mx = max(1, k.max())
        idx = rng.integers(0, len(net), size=(B, mx)); dpl = np.zeros(B)
        for j in range(mx):
            act = live & (j < k)
            tn = net[idx[:, j]] * PV * ct; tm = mfe[idx[:, j]] * PV * ct
            if intra: peak = np.where(act, np.maximum(peak, eq + tm), peak)
            eq = np.where(act, eq + tn, eq); dpl = np.where(act, dpl + tn, dpl)
            if not intra: peak = np.where(act, np.maximum(peak, eq), peak)
            live &= ~(live & (((peak - eq) >= trail) | (dpl <= -daily)))
    return live, eq

print('=' * 88)
print('PHASE 1 - EVALUATION (stops at target). EOD trailing | intraday trailing')
print('=' * 88)
print('%-6s %-8s %19s %19s' % ('acct', 'MNQ ct', 'EOD  pass/fail/days', 'INTRA pass/fail/days'))
for nm, tgt, tr, dl in ACCTS:
    for ct in (1, 2, 3, 5, 10):
        a = evaluate(tgt, tr, dl, ct, False, 11 + ct)
        b = evaluate(tgt, tr, dl, ct, True, 33 + ct)
        f = lambda r: '%5.1f%% %5.1f%% %4s' % (100*r[0].mean(), 100*r[1].mean(),
              ('%.0f' % np.median(r[2][r[0]])) if r[0].any() else 'n/a')
        print('%-6s %-8d %19s %19s' % (nm, ct, f(a), f(b)))
    print()

print('=' * 88)
print('PHASE 2 - FUNDED, 12 MONTHS (survive the trailing drawdown, keep trading)')
print('=' * 88)
print('%-6s %-8s %10s %12s %12s' % ('acct', 'MNQ ct', 'survive', 'med profit', 'p25 profit'))
for nm, tgt, tr, dl in ACCTS:
    for ct in (1, 2, 3, 5):
        live, eq = funded(tr, dl, ct, False, 55 + ct)
        e = eq[live]
        print('%-6s %-8d %9.1f%% %12s %12s'
              % (nm, ct, 100*live.mean(),
                 ('$%.0f' % np.median(e)) if live.any() else 'n/a',
                 ('$%.0f' % np.percentile(e, 25)) if live.any() else 'n/a'))
    print()
