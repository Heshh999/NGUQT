#!/usr/bin/env python3
# ======================================================================
# OFH13 RISK-OF-RUIN / MINIMUM-ACCOUNT STUDY
# Inputs: the 133 frozen OFH13 net-point outcomes (exploratory history).
# Output: survival probabilities by starting balance, 1 MNQ contract.
# Sizing analysis only. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import re, os, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, '..', 'ofh13mem', 'EVENT_LISTING.txt')
net = []
for ln in open(SRC):
    m = re.search(r'\s([+-]\d+\.\d\d)\s+(WIN|LOSS)', ln)
    if m:
        net.append(float(m.group(1)))
net = np.array(net)
assert len(net) == 133, len(net)

PV = 2.0                      # MNQ $ per point
d = net * PV                  # per-trade $ (cost 0.87pt already inside)
wins, losses = d[d > 0], d[d < 0]
print('OFH13 frozen trade distribution (n=%d, $2/pt, cost included)' % len(d))
print('  win rate        %.1f%%' % (100 * (d > 0).mean()))
print('  mean/trade      $%+.2f' % d.mean())
print('  median          $%+.2f' % np.median(d))
print('  avg win  $%+.2f   avg loss $%+.2f   payoff %.2f'
      % (wins.mean(), losses.mean(), wins.mean() / -losses.mean()))
print('  worst trade     $%.2f' % d.min())
print('  best trade      $%+.2f' % d.max())
print('  profit factor   %.2f' % (wins.sum() / -losses.sum()))
print('  trades/year     ~%d  (133 over ~12 months)' % 133)

# observed worst peak-to-trough on the actual sequence
eq = np.cumsum(d); dd = np.maximum.accumulate(np.r_[0, eq]) - np.r_[0, eq]
print('  worst realized drawdown (actual order)  $%.2f' % dd.max())

def ruin(bal, n_trades, mult, floor, B=200000, seed=7):
    """Bootstrap trade order. Ruin = equity dips below `floor` at any
    point (can no longer meet margin + buffer). mult scales losses to
    stress a worse-than-historical future."""
    rng = np.random.default_rng(seed)
    pool = np.where(d < 0, d * mult, d)
    draws = rng.choice(pool, size=(B, n_trades), replace=True)
    eq = bal + np.cumsum(draws, axis=1)
    low = np.minimum.accumulate(eq, axis=1)[:, -1]
    ruined = (low <= floor).mean()
    final = eq[:, -1]
    mdd = (np.maximum.accumulate(np.c_[np.full(B, bal), eq], axis=1)
           - np.c_[np.full(B, bal), eq]).max(axis=1)
    return ruined, np.percentile(mdd, [50, 95, 99]), (final < bal).mean()

DAY_MARGIN = 100.0            # typical MNQ intraday margin; broker-dependent
print('\n' + '=' * 70)
print('ONE YEAR (133 trades), 1 MNQ contract, ruin = equity < margin+buffer')
print('assumed intraday margin $%.0f; floor = margin (cannot open a trade)' % DAY_MARGIN)
print('=' * 70)
print('%9s | %-28s | %-28s' % ('', 'AS-OBSERVED', 'STRESSED (losses x1.5)'))
print('%9s | %8s %8s %8s | %8s %8s %8s'
      % ('balance', 'ruin%', 'medDD', 'p95DD', 'ruin%', 'medDD', 'p95DD'))
for bal in (500, 1000, 1500, 2000, 2500, 3000, 4000, 5000, 7500, 10000):
    r1, dd1, _ = ruin(bal, 133, 1.0, DAY_MARGIN)
    r2, dd2, _ = ruin(bal, 133, 1.5, DAY_MARGIN)
    print('%9s | %7.1f%% %8.0f %8.0f | %7.1f%% %8.0f %8.0f'
          % ('$%d' % bal, 100 * r1, dd1[0], dd1[1],
             100 * r2, dd2[0], dd2[1]))

print('\nsolve: smallest balance with ruin <= 1%% over one year')
for label, mult in (('as-observed', 1.0), ('stressed x1.5', 1.5)):
    lo, hi = 200, 40000
    while hi - lo > 50:
        mid = (lo + hi) // 2
        r, _, _ = ruin(mid, 133, mult, DAY_MARGIN, B=60000)
        if r <= 0.01: hi = mid
        else: lo = mid
    print('  %-14s $%d' % (label, hi))

print('\nsolve: smallest balance with ruin <= 1%% over THREE years (399 trades)')
for label, mult in (('as-observed', 1.0), ('stressed x1.5', 1.5)):
    lo, hi = 200, 60000
    while hi - lo > 50:
        mid = (lo + hi) // 2
        r, _, _ = ruin(mid, 399, mult, DAY_MARGIN, B=60000)
        if r <= 0.01: hi = mid
        else: lo = mid
    print('  %-14s $%d' % (label, hi))

print('\nZERO-EDGE CONTROL (edge fails forward: mean forced to 0)')
d0 = d - d.mean()
def ruin0(bal, n=133, B=200000, seed=11):
    rng = np.random.default_rng(seed)
    eq = bal + np.cumsum(rng.choice(d0, size=(B, n), replace=True), axis=1)
    return (np.minimum.accumulate(eq, axis=1)[:, -1] <= DAY_MARGIN).mean()
for bal in (1000, 2500, 5000, 7500, 10000, 15000):
    print('  $%-6d ruin %.1f%%' % (bal, 100 * ruin0(bal)))
