#!/usr/bin/env python3
# OFH11-OFH14 follow-up: does the improved MFE/MAE RATIO convert into a
# stopped, targeted trade?
#
# The main run produced a contradiction that has to be resolved before
# any verdict: medMFE/medMAE rose from 1.026 (OFH6) to 1.41 (OFH13) and
# 2.80 (OFH12), while 1-ATR favourable-first stayed at 46-49% - i.e. no
# better than OFH6 and no better than a coin. Those two facts are only
# compatible if the extra favourable excursion arrives AFTER an adverse
# excursion of similar size. A stop finds out.
#
# Frozen here before running: structural stop = the hypothesis's own R
# (FVG far boundary / sweep extreme + 1 tick), plus 1.0 and 1.5 ATR
# benchmarks; target grid 0.5..4.0 R; exact chronological first touch on
# 1m bars; 60m cap; cost 0.87.
#
# AMBIGUITY IS NOT RESOLVED BY ASSUMPTION. When stop and target both
# fall inside one 1m bar the outcome is AMBIGUOUS and reported three
# ways: conservative (stop first), optimistic (target first), and the
# ambiguous share itself. Genuine 30s data exists only 09:30-11:00 ET
# and covers a minority of these entries, so it cannot resolve the grid.

import os, sys, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import offvg_run as M          # re-uses the frozen run (imports execute it)

B, G, ENT, COST, HORIZON, TICK = M.B, M.G, M.ENT, M.COST, M.HORIZON, M.TICK
BASE, DEV_END = M.BASE, M.DEV_END
random.seed(41)

TARGETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]


def race(j, d, stop_dist, tgt_dist):
    """Exact chronological first touch. Returns (outcome, ambiguous)."""
    e = B[j]['close']
    sp = e - d * stop_dist
    tp = e + d * tgt_dist if tgt_dist else None
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        hs = (c['low'] <= sp) if d > 0 else (c['high'] >= sp)
        ht = tp is not None and ((c['high'] >= tp) if d > 0 else (c['low'] <= tp))
        if hs and ht:
            return (-stop_dist, tgt_dist), True
        if hs:
            return (-stop_dist, -stop_dist), False
        if ht:
            return (tgt_dist, tgt_dist), False
    v = (B[j + HORIZON]['close'] - e) * d
    return (v, v), False


print('\n' + '=' * 118)
print('STOP TEST - does the ratio convert?  (net pt/trade after %.2f cost)' % COST)
print('=' * 118)
print('  %-8s %-14s %s' % ('hyp', 'stop', 'DEV net / IR net   |  stop-hit%  |  med risk pt'))
BASE6 = [(j, d, B[j]['atr']) for j, d in M.SIGS if M.entry_ok(B, j)]
sets = [('OFH6', BASE6)] + [(nm, [(j, d, R) for j, d, R, _ in ENT.get(nm, [])])
                            for nm in ('OFH11', 'OFH12', 'OFH13', 'OFH14')]
for nm, rows in sets:
    if len(rows) < 10:
        print('  %-8s n=%d - too few for a stop test' % (nm, len(rows)))
        continue
    for mode in ('struct', 1.0, 1.5):
        out = {'DEV': [], 'IR': []}
        hits = 0
        risks = []
        for j, d, R in rows:
            S = R if mode == 'struct' else mode * B[j]['atr']
            if S <= 0:
                continue
            risks.append(S)
            sp = 'DEV' if B[j]['day'] <= DEV_END else 'IR'
            (v, _), _a = race(j, d, S, None)
            if v <= -S + 1e-9:
                hits += 1
            out[sp].append(v - BASE[(sp, d)] - COST)
        rk = sorted(risks)
        print('  %-8s %-14s %+7.2f / %+7.2f      %5.1f%%        %6.2f'
              % (nm, str(mode), sum(out['DEV']) / len(out['DEV']) if out['DEV'] else float('nan'),
                 sum(out['IR']) / len(out['IR']) if out['IR'] else float('nan'),
                 100.0 * hits / len(risks), rk[len(rk) // 2]))

print('\n' + '=' * 118)
print('FIXED-R GRID on the structural stop - conservative | optimistic | ambiguous share')
print('=' * 118)
for nm in ('OFH13', 'OFH14', 'OFH6'):
    rows = BASE6 if nm == 'OFH6' else [(j, d, R) for j, d, R, _ in ENT.get(nm, [])]
    if len(rows) < 40:
        print('  %s: n=%d, below the n>=40 reporting floor' % (nm, len(rows)))
        continue
    print('  %s (n=%d, stop = %s)' % (nm, len(rows),
                                      '1 ATR' if nm == 'OFH6' else 'structural R'))
    print('    %-6s %10s %10s %8s   %s' % ('target', 'conserv', 'optimist', 'amb%', 'DEV/IR conserv'))
    for t in TARGETS:
        cons = []
        opt = []
        na = 0
        bysp = {'DEV': [], 'IR': []}
        for j, d, R in rows:
            S = R
            (vc, vo), a = race(j, d, S, t * S)
            sp = 'DEV' if B[j]['day'] <= DEV_END else 'IR'
            c = vc - BASE[(sp, d)] - COST
            o = vo - BASE[(sp, d)] - COST
            cons.append(c)
            opt.append(o)
            bysp[sp].append(c)
            if a:
                na += 1
        print('    %-6.2f %+10.2f %+10.2f %8.1f   %+7.2f / %+7.2f'
              % (t, sum(cons) / len(cons), sum(opt) / len(opt), 100.0 * na / len(cons),
                 sum(bysp['DEV']) / len(bysp['DEV']) if bysp['DEV'] else float('nan'),
                 sum(bysp['IR']) / len(bysp['IR']) if bysp['IR'] else float('nan')))

print('\n' + '=' * 118)
print('WHY THE RATIO DOES NOT CONVERT - timing of the excursions')
print('=' * 118)
print('  %-8s %10s %10s %10s %10s' % ('hyp', 'medMFE', 'medMAE', 'med t(MFE)', 'med t(MAE)'))
for nm, rows in sets:
    if len(rows) < 40:
        continue
    tf = []
    ta = []
    for j, d, R in rows:
        e = B[j]['close']
        bf = ba = 0.0
        kf = ka = 0
        for k in range(1, HORIZON + 1):
            c = B[j + k]
            fav = (c['high'] - e) if d > 0 else (e - c['low'])
            adv = (e - c['low']) if d > 0 else (c['high'] - e)
            if fav > bf:
                bf, kf = fav, k
            if adv > ba:
                ba, ka = adv, k
        tf.append(kf)
        ta.append(ka)
    gs = G.get(nm, []) if nm != 'OFH6' else M.G6
    mf = sorted(g['mfe'] for g in gs)
    ma = sorted(g['mae'] for g in gs)
    tf.sort()
    ta.sort()
    print('  %-8s %10.1f %10.1f %10d %10d'
          % (nm, mf[len(mf) // 2], ma[len(ma) // 2], tf[len(tf) // 2], ta[len(ta) // 2]))
print('  (t = minutes to the extreme, median. If t(MAE) <= t(MFE) the adverse')
print('   move arrives first and no stop can be placed inside the ratio.)')
