#!/usr/bin/env python3
# H6-OF-ABSORPTION-REVERSAL - confirmatory test inside the order-flow
# window only, per the frozen preregistration (OF-DEV Nov 2025..Feb 2026,
# OF-VAL Mar..May 2026; OF-OOS untouched).
#
# Membership (frozen registry definition, constructed from frozen
# features): a structural BREAK event at/near a tracked level
# (interaction != NO_INTERACTION) whose 1m order-flow bar at the event
# minute shows delta non-confirmation AND an absorption candidate
# against the break side.
#
# Measurement note, on the record: engine probes are armed on the BREAK
# side only, so the reversal is measured on the PARENT event's own
# forward window - metric = -(y_net_60m) of the break-side row, i.e.
# the reversal-signed 60m net. This is the registry's baseline
# representation for a reversal hypothesis absent reclaim-side probes.

import csv, glob, os, random
from collections import defaultdict

SP = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COSTS = [('gross', 0.0), ('comm', 0.37), ('base', 0.87), ('stress', 1.37)]
SPLITS = {'OF-DEV': ('2025-11-02', '2026-02-28'), 'OF-VAL': ('2026-03-01', '2026-05-31')}
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

# order-flow features by minute timestamp
of = {}
for f in sorted(glob.glob(os.path.join(SP, 'of1', 'v4_1_orderflow_MNQ_v41of_*.csv'))):
    m = f[-11:-4]
    if not ('2025-11' <= m <= '2026-05'): continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            of[row[i['f_barCloseEt']]] = (
                row[i['f_absorptionBuyCandidate']] == 'TRUE',
                row[i['f_absorptionSellCandidate']] == 'TRUE',
                row[i['f_bullishDeltaDivergenceCandidate']] == 'TRUE',
                row[i['f_bearishDeltaDivergenceCandidate']] == 'TRUE')

rows = []
alld = defaultdict(list)
for f in sorted(glob.glob(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_*.csv'))):
    m = f[-11:-4]
    if not ('2025-11' <= m <= '2026-05'): continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE': continue
            et = row[i['f_barCloseEt']]; day = et[:10]
            net = F(row[i['y_net_60m']])
            if net is None: continue
            kind = row[i['f_eventKind']]
            if kind not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            alld[day].append(-net)   # reversal-signed pool for permutation
            o = of.get(et)
            if o is None: continue
            near = row[i['f_interaction']] != 'NO_INTERACTION'
            if not near: continue
            absorbBuy, absorbSell, divBull, divBear = o
            if kind == 'BREAK_HIGH' and divBear and absorbBuy:
                rows.append({'day': day, 'net': -net})   # predict bearish reversal
            elif kind == 'BREAK_LOW' and divBull and absorbSell:
                rows.append({'day': day, 'net': -net})   # predict bullish reversal

def day_boot(rr, nb=2000):
    byd = defaultdict(list)
    for x in rr: byd[x['day']].append(x['net'])
    days = list(byd.values())
    if not days: return float('nan'), float('nan'), float('nan')
    means = []
    for _ in range(nb):
        s = [v for d in random.choices(days, k=len(days)) for v in d]
        means.append(sum(s) / len(s))
    means.sort()
    return means[int(0.025 * nb)], means[int(0.975 * nb)], sum(1 for m in means if m <= 0) / nb

print('H6-OF-ABSORPTION-REVERSAL  (order-flow window; reversal-signed 60m net on parent events)')
for split, (a, b) in SPLITS.items():
    rr = [x for x in rows if a <= x['day'] <= b]
    pool = {d: v for d, v in alld.items() if a <= d <= b}
    if not rr:
        print('%-8s n=0  EMPTY (event+OF conjunction produced no rows)' % split); continue
    mu = sum(x['net'] for x in rr) / len(rr)
    lo, hi, pb = day_boot(rr)
    dm = defaultdict(int)
    for x in rr: dm[x['day']] += 1
    ge = 0; NP = 200
    for _ in range(NP):
        tot = 0.0; n = 0
        for d, k in dm.items():
            p = pool.get(d)
            if not p or len(p) < k: continue
            tot += sum(random.sample(p, k)); n += k
        if n and tot / n >= mu: ge += 1
    print('%-8s n=%3d days=%3d  mean %+0.3f  net(base) %+0.3f  CI[%+.2f,%+.2f]  p_boot %.4f  p_perm %.4f'
          % (split, len(rr), len(dm), mu, mu - 0.87, lo, hi, pb, (ge + 1) / (NP + 1)))
print('eligible break events with OF join: %d  (matched minutes %d)'
      % (sum(len(v) for v in alld.values()), len(of)))
