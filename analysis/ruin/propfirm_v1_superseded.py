#!/usr/bin/env python3
# ======================================================================
# OFH13 UNDER PROP-FIRM RULES (trailing drawdown, daily loss, target)
# Uses the frozen 133 trades incl. MFE so intraday high-water trailing
# can be modelled honestly. Rule values are TYPICAL - verify your firm's.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import json, numpy as np

R = np.load('/tmp/ofh13_rows.npy')          # cols: MFE, MAE, net (points)
DAYS = json.load(open('/tmp/ofh13_days.json'))
PV = 2.0
mfe, net = R[:, 0], R[:, 2]
# per-trade peak open profit is MFE; realised is net. Both in points.
B = 40000
TPD = 133 / 108.0                            # ~1.23 trades per trading day

ACCTS = [
    ('50k',  3000.0, 2500.0, 1100.0),
    ('100k', 6000.0, 3000.0, 2200.0),
    ('150k', 9000.0, 5000.0, 3300.0),
]

def sim(target, trail, daily, n_ct, intraday_trail, seed, max_days=250):
    rng = np.random.default_rng(seed)
    eq = np.zeros(B)                 # P&L relative to start
    peak = np.zeros(B)               # high-water used by the trailing rule
    alive = np.ones(B, bool)
    passed = np.zeros(B, bool)
    pass_day = np.full(B, -1)
    for day in range(max_days):
        k = rng.poisson(TPD, B)
        mx = max(1, k.max())
        idx = rng.integers(0, len(net), size=(B, mx))
        day_pl = np.zeros(B)
        for j in range(mx):
            act = alive & (j < k)
            tn = net[idx[:, j]] * PV * n_ct
            tm = mfe[idx[:, j]] * PV * n_ct
            if intraday_trail:                     # unrealised peak counts
                peak = np.where(act, np.maximum(peak, eq + tm), peak)
            eq = np.where(act, eq + tn, eq)
            day_pl = np.where(act, day_pl + tn, day_pl)
            if not intraday_trail:
                peak = np.maximum(peak, eq)
            # trailing drawdown breach
            alive &= ~(alive & ((peak - eq) >= trail))
            # daily loss limit breach
            alive &= ~(alive & (day_pl <= -daily))
        if not intraday_trail:
            peak = np.where(alive, np.maximum(peak, eq), peak)
        newly = alive & ~passed & (eq >= target)
        pass_day = np.where(newly, day + 1, pass_day)
        passed |= newly
    return passed, pass_day, alive

print('=' * 92)
print('PASS AN EVALUATION  (typical rules; EOD-balance trailing drawdown)')
print('=' * 92)
print('%-6s %-9s %8s %9s %9s %9s' %
      ('acct', 'MNQ cts', 'P(pass)', 'P(blow)', 'medDays', 'risk/trade'))
for name, tgt, trail, daily in ACCTS:
    for ct in (1, 3, 5, 10, 20):
        p, pd, al = sim(tgt, trail, daily, ct, False, 400 + ct)
        md = np.median(pd[p]) if p.any() else float('nan')
        print('%-6s %-9d %7.1f%% %8.1f%% %9s %8s'
              % (name, ct, 100 * p.mean(), 100 * (~al).mean(),
                 ('%.0f' % md) if p.any() else 'n/a', '$%.0f' % (67.66 * ct)))
    print()

print('=' * 92)
print('SAME, BUT INTRADAY HIGH-WATER TRAILING (open profit counts against you)')
print('=' * 92)
print('%-6s %-9s %8s %9s %9s' % ('acct', 'MNQ cts', 'P(pass)', 'P(blow)', 'medDays'))
for name, tgt, trail, daily in ACCTS:
    for ct in (1, 3, 5, 10):
        p, pd, al = sim(tgt, trail, daily, ct, True, 700 + ct)
        md = np.median(pd[p]) if p.any() else float('nan')
        print('%-6s %-9d %7.1f%% %8.1f%% %9s'
              % (name, ct, 100 * p.mean(), 100 * (~al).mean(),
                 ('%.0f' % md) if p.any() else 'n/a'))
    print()
