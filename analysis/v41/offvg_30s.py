#!/usr/bin/env python3
# SECONDARY EXECUTION ARM for OFH13 / OFH14: replay the SAME frozen
# parent (same FVG, frozen at its 1m formation) on the 30s grid and ask
# only whether the mitigation trigger can be taken more efficiently.
# 30s may NOT requalify a setup - the parent, the zone and the direction
# all come from the 1m run unchanged. Genuine 30s data covers
# 09:30-11:00:30 ET only, so this runs on the subset that falls inside.

import os, sys, csv, glob
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import offvg_run as M

B, ENT, G, TICK, COST = M.B, M.ENT, M.G, M.TICK, M.COST
SCR = M.SCR

S30 = defaultdict(dict)
for f in sorted(glob.glob(SCR + '/ph2/V3_30s_*.csv')):
    mo = f[-10:-4]
    mm = mo[:4] + '-' + mo[4:]
    if mm < '2025-11' or mm > '2026-05':
        continue
    for r in csv.DictReader(open(f)):
        if r['timeframe'] != '30s':
            continue
        h, mi, se = map(int, r['timeEt'].split(':'))
        S30[r['date']][h * 3600 + mi * 60 + se] = (
            float(r['open']), float(r['high']), float(r['low']), float(r['close']))

for j in range(len(B)):
    et = B[j]['et']
    B[j]['sod'] = int(et[11:13]) * 3600 + int(et[14:16]) * 60


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


print('\n' + '=' * 110)
print('30s EXECUTION ARM - same frozen FVG parent, trigger replayed on 30s bars')
print('=' * 110)
for nm in ('OFH13', 'OFH14'):
    rows = ENT.get(nm, [])
    pairs = []
    for (j, d, R, meta) in rows:
        if 'zLo' not in meta:
            continue
        day = B[j]['day']
        g = S30.get(day)
        if not g:
            continue
        fj = meta['fvgj']
        start = B[fj]['sod'] + 60          # first 30s bar after FVG completes
        end = B[j]['sod']                  # the 1m entry bar's close
        if start < 9 * 3600 + 1800 or end > 11 * 3600:
            continue
        zLo, zHi, mid = meta['zLo'], meta['zHi'], meta['mid']
        touched = False
        ext = None
        e30 = None
        sec = start
        while sec <= end:
            bar = g.get(sec)
            if bar is None:
                break
            o, h, l, c = bar
            if not touched:
                if (d > 0 and l <= zHi) or (d < 0 and h >= zLo):
                    touched = True
                    ext = l if d > 0 else h
            else:
                x = l if d > 0 else h
                if (d > 0 and x < ext) or (d < 0 and x > ext):
                    ext = x
            if touched and ((d > 0 and c > mid) or (d < 0 and c < mid)):
                e30 = (sec, c, ext)
                break
            sec += 30
        if e30 is None:
            continue
        px1 = B[j]['close']
        imp = (px1 - e30[1]) * d
        R30 = (e30[1] - (ext - TICK)) if d > 0 else ((ext + TICK) - e30[1])
        pairs.append((imp, B[j]['sod'] - e30[0], R, R30))
    if len(pairs) < 10:
        print('  %-6s paired events inside 30s coverage: %d -> INSUFFICIENT DATA'
              % (nm, len(pairs)))
        continue
    imp = [p[0] for p in pairs]
    lat = [p[1] for p in pairs]
    dr = [p[3] - p[2] for p in pairs]
    print('  %-6s n=%d paired' % (nm, len(pairs)))
    print('    entry-price improvement (30s vs 1m): mean %+0.2f  med %+0.2f pt (%+0.1f ticks)'
          % (sum(imp) / len(imp), med(imp), med(imp) / TICK))
    print('    earlier by: med %ds  mean %ds' % (med(lat), sum(lat) / len(lat)))
    print('    risk delta (30s - 1m): mean %+0.2f  med %+0.2f pt' % (sum(dr) / len(dr), med(dr)))
    print('    %% entering earlier %.0f%%   %% worse price %.0f%%'
          % (100.0 * sum(1 for x in lat if x > 0) / len(lat),
             100.0 * sum(1 for x in imp if x < 0) / len(imp)))
