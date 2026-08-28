#!/usr/bin/env python3
# OFH13 vs REAL 150K prop-firm rule sets (looked up Aug 2026).
# Rules vary and change - verify against the firm before funding.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
import numpy as np
R = np.load('/tmp/ofh13_rows.npy'); PV = 2.0
mfe, net = R[:, 0], R[:, 2]
B = 40000; TPD = 133/108.0

# name, target, trailingDD, dailyLoss(0=none), intradayTrail, minDays
FIRMS = [
 ('Apex 150K (EOD)',        9000., 5000.,    0.,  False, 7),
 ('Apex 150K (intraday)',   9000., 5000.,    0.,  True,  7),
 ('Topstep 150K',           9000., 4500., 3000.,  False, 2),
 ('MyFundedFutures Pro150', 9000., 4500.,    0.,  False, 3),
 ('TakeProfitTrader 150K',  9000., 4500.,    0.,  False, 5),
 ('TPT PRO funded (intra)',    0., 4500.,    0.,  True,  0),
]

def sim(target, trail, daily, ct, intra, seed, days=250, stop_at_target=True):
    rng = np.random.default_rng(seed)
    eq = np.zeros(B); peak = np.zeros(B)
    live = np.ones(B, bool); passed = np.zeros(B, bool); blown = np.zeros(B, bool)
    pd_ = np.full(B, -1); ndays = np.zeros(B, int); best_day = np.zeros(B)
    for day in range(days):
        k = rng.poisson(TPD, B); mx = max(1, k.max())
        idx = rng.integers(0, len(net), size=(B, mx)); dpl = np.zeros(B)
        traded = np.zeros(B, bool)
        for j in range(mx):
            act = live & (j < k)
            tn = net[idx[:, j]]*PV*ct; tm = mfe[idx[:, j]]*PV*ct
            if intra: peak = np.where(act, np.maximum(peak, eq+tm), peak)
            eq = np.where(act, eq+tn, eq); dpl = np.where(act, dpl+tn, dpl)
            traded |= act
            if not intra: peak = np.where(act, np.maximum(peak, eq), peak)
            b = live & (((peak-eq) >= trail) | ((daily > 0) & (dpl <= -daily)))
            blown |= b; live &= ~b
        ndays += traded
        best_day = np.maximum(best_day, dpl)
        if target > 0 and stop_at_target:
            p = live & (eq >= target); passed |= p
            pd_ = np.where(p & (pd_ < 0), day+1, pd_); live &= ~p
    return passed, blown, pd_, live, eq, best_day

print('=' * 100)
print('PASSING A REAL 150K EVALUATION WITH OFH13 (MNQ)')
print('=' * 100)
print('%-26s %4s %8s %8s %9s %s' % ('firm / rule set','ct','pass','blow','medDays','1-day>40% of profit'))
for nm, tgt, tr, dl, intra, mind in FIRMS:
    if tgt == 0: continue
    for ct in (1, 2, 3, 5):
        p, b, pdays, live, eq, bd = sim(tgt, tr, dl, ct, intra, 90+ct)
        # consistency check on passers: biggest day vs target
        cons = (bd[p] > 0.40*tgt).mean() if p.any() else float('nan')
        print('%-26s %4d %7.1f%% %7.1f%% %9s %13.1f%%'
              % (nm, ct, 100*p.mean(), 100*b.mean(),
                 ('%.0f' % np.median(pdays[p])) if p.any() else 'n/a', 100*cons))
    print()

print('=' * 100)
print('FUNDED PHASE - 12 MONTHS, DO YOU SURVIVE THE TRAILING DRAWDOWN?')
print('=' * 100)
print('%-26s %4s %10s %12s' % ('firm / rule set','ct','survive','med gross'))
for nm, tgt, tr, dl, intra, mind in FIRMS:
    for ct in (1, 2, 3):
        _, _, _, live, eq, _ = sim(0, tr, dl, ct, intra, 700+ct, stop_at_target=False)
        print('%-26s %4d %9.1f%% %12s'
              % (nm, ct, 100*live.mean(),
                 ('$%.0f' % np.median(eq[live])) if live.any() else 'n/a'))
    print()
