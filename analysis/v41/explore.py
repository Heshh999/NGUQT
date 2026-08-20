#!/usr/bin/env python3
# Lane 2 - bounded exploratory pass, DEV ONLY (2019-07-01..2022-12-31).
# Pre-declared family-level cells, all counted, all reported, none
# promoted. 16 cells total:
#   A. 4 broad time-of-day windows x ARCH-B probes
#   B. 8 level-interaction states x ARCH-B probes
#   C. 4 vector-color parents x ARCH-B probes
# Metric: gross mean y_net_60m (probe-side). Noise-floor framing: the
# V5 conjunction search found best-of-8329 = +20.6pt on real data vs
# +16.6 mean (max +26.1) on within-day-SHUFFLED data. A best-of-16 cell
# must be read against that lesson, not celebrated.

import csv, glob, os
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
A, B = '2019-07-01', '2022-12-31'

def F(v):
    try: return float(v)
    except: return None

par = {}
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE': continue
            pid = row[i['parentEventId']]; et = row[i['f_barCloseEt']]
            if pid in par and par[pid][0] <= et: continue
            par[pid] = (et, row[i['f_interaction']], row[i['f_vectorColor_15m']])

cells = defaultdict(list)
for f in sorted(glob.glob(os.path.join(D, 'v4_1_entries_MNQ_v41_*.csv'))):
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isWarmup']] == 'TRUE': continue
            day = row[i['f_eventEt']][:10]
            if not (A <= day <= B): continue
            if row[i['f_architecture']] != 'ARCH-B': continue
            net = F(row[i['y_net_60m']])
            if net is None: continue
            hhmm = row[i['f_eventEt']][11:16]
            tod = ('ASIA' if hhmm >= '18:00' or hhmm < '03:00'
                   else 'LONDON' if hhmm < '09:30'
                   else 'RTH_AM' if hhmm < '12:00' else 'RTH_PM')
            cells[('TOD', tod)].append(net)
            p = par.get(row[i['parentEventId']])
            if p:
                cells[('INTER', p[1])].append(net)
                if p[2] != 'NONE': cells[('VCOLOR', p[2])].append(net)

print('LANE 2 EXPLORATORY (DEV only, ARCH-B probes, gross mean net_60m) - 16 pre-declared cells')
print('%-10s %-24s %6s %8s' % ('family', 'cell', 'n', 'mean'))
tested = 0
for k in sorted(cells):
    v = cells[k]; tested += 1
    print('%-10s %-24s %6d %+8.3f' % (k[0], k[1], len(v), sum(v) / len(v)))
print('cells tested: %d  (logged against multiplicity; none promoted)' % tested)
print('EVERY cell above is EXPLORATORY - NOT YET CONFIRMED. Any candidate')
print('drawn from it requires a frozen rule and fresh validation it has')
print('never touched. The identically-constructed confirmatory families')
print('just showed a hard DEV->VAL sign flip; treat these accordingly.')
