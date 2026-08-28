#!/usr/bin/env python3
# NVQ-V1 follow-up on the BH survivor D_STREAK3_DN, per frozen protocol:
# the ONE frozen translation (next-session open -> close) + declared
# diagnostics (decomposition, years, drop-best, vol regimes). No new
# thresholds. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
import collections, json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mtf'))
import mtf_lib as M

D = M.load(); N = len(D['c'])
byday = collections.defaultdict(list)
for i in range(N): byday[D['day'][i]].append(i)
days = sorted(byday)
dd = []
for d in days:
    idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
    if len(idx) >= 300:
        dd.append(dict(day=d, o=D['o'][idx[0]], c=D['c'][idx[-1]],
                       h=max(D['h'][i] for i in idx),
                       l=min(D['l'][i] for i in idx)))
cl = np.array([x['c'] for x in dd]); op = np.array([x['o'] for x in dd])
rng_ = np.array([x['h'] - x['l'] for x in dd])
lr = np.append(np.diff(np.log(cl)), np.nan) * 1e4          # c2c next-day at t
on_ = np.append((np.log(op[1:] / cl[:-1])), np.nan) * 1e4  # overnight gap at t
id_ = np.append((np.log(cl[1:] / op[1:])), np.nan) * 1e4   # next-day intraday at t

ev = []
for t in range(20, len(dd) - 1):
    r = np.sign(np.diff(np.log(cl[t - 4:t + 1])))
    if len(r) == 4 and r[-1] < 0 and r[-2] < 0 and r[-3] < 0 and r[-4] >= 0:
        if lr[t] == lr[t]:
            ev.append(t)
print('D_STREAK3_DN events (exactly 3 down days): %d' % len(ev))
c2c = np.array([lr[t] for t in ev]); onv = np.array([on_[t] for t in ev])
idv = np.array([id_[t] for t in ev])
px = np.array([cl[t] for t in ev])
yrs = [dd[t]['day'][:4] for t in ev]

print('\nDECOMPOSITION (bp): close-to-close %+.1f = overnight %+.1f + intraday %+.1f'
      % (c2c.mean(), onv.mean(), idv.mean()))
m, lo, hi = M.stationary_boot_mean(list(onv), 5000, 7)
print('  overnight gap : %+7.2f  CI[%+7.2f,%+7.2f]%s' % (m, lo, hi, ' *' if lo>0 or hi<0 else ''))
m, lo, hi = M.stationary_boot_mean(list(idv), 5000, 8)
print('  intraday RTH  : %+7.2f  CI[%+7.2f,%+7.2f]%s' % (m, lo, hi, ' *' if lo>0 or hi<0 else ''))

print('\nBY YEAR (c2c bp, n):')
byy = collections.defaultdict(list)
for y, v in zip(yrs, c2c): byy[y].append(v)
for y in sorted(byy):
    print('  %s  n %3d  %+8.1f' % (y, len(byy[y]), np.mean(byy[y])))
h1 = [v for y, v in zip(yrs, c2c) if y <= '2022']
h2 = [v for y, v in zip(yrs, c2c) if y >= '2023']
print('  halves: 2019-22 %+.1f (n %d)   2023-26 %+.1f (n %d)'
      % (np.mean(h1), len(h1), np.mean(h2), len(h2)))

srt = np.sort(c2c)
print('\nROBUSTNESS: drop best day %+.1f   drop best 3 %+.1f   median %+.1f   win rate %.0f%%'
      % (srt[:-1].mean(), srt[:-3].mean(), np.median(c2c), 100*(c2c>0).mean()))
med = np.median([np.median(rng_[max(0,t-20):t]) for t in ev])
volhi = np.array([np.median(rng_[max(0,t-20):t]) > med for t in ev])
print('  vol regime: high-vol half %+.1f (n %d)   low-vol half %+.1f (n %d)'
      % (c2c[volhi].mean(), volhi.sum(), c2c[~volhi].mean(), (~volhi).sum()))

# control: unconditional and the dead cumulative-sign cousin
print('\nCONTROLS: unconditional next-day %+.2f bp   after ANY down day %+.2f bp'
      % (np.nanmean(lr[20:-1]),
         np.nanmean([lr[t] for t in range(20, len(dd)-1)
                     if cl[t] < cl[t-1] and lr[t]==lr[t]])))

# FROZEN TRANSLATION: enter next session open, exit next session close (RTH only)
pts = idv / 1e4 * px
g = pts
print('\nFROZEN TRANSLATION (next open -> next close, RTH, 1 MNQ):')
for cost, lab in ((0.87, 'base'), (1.305, 'stressed')):
    net = g - cost
    pf = net[net>0].sum() / -net[net<0].sum() if (net<0).any() else float('inf')
    print('  %-8s mean %+7.2f pt  win %4.0f%%  PF %.3f'
          % (lab, net.mean(), 100*(net>0).mean(), pf))
# informational: close-to-close capture (requires overnight hold, 1.740)
g2 = c2c / 1e4 * px
net2 = g2 - 1.740
pf2 = net2[net2>0].sum() / -net2[net2<0].sum() if (net2<0).any() else float('inf')
print('  [info] close->close incl overnight @1.740: mean %+.2f pt  win %.0f%%  PF %.3f'
      % (net2.mean(), 100*(net2>0).mean(), pf2))
json.dump(dict(n=len(ev), c2c=float(c2c.mean()), on=float(onv.mean()),
               intraday=float(idv.mean())), open('NVQ_V1_FOLLOWUP.json','w'))
