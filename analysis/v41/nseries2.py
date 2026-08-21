#!/usr/bin/env python3
# N-SERIES part 2 - the noise-floor control, plus the autopsy the user
# asked for: take the best hypotheses and find out WHY they lose, and
# whether any stop / horizon / R:R choice repairs them.
#
# Exact method for the stop x horizon grid (no ordering ambiguity):
# with a STOP + TIME EXIT there is no stop-vs-target race, so
#   FOLLOW trade: stopped within H iff y_mae_H >= S ; else outcome +y_net_H
#   FADE   trade: stopped within H iff y_mfe_H >= S ; else outcome -y_net_H
# because a fade's adverse excursion IS the event's favourable one.
#
# HOLD (2024-07 onward) is not read.

import csv, glob, os, random
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
COST = 0.87
random.seed(41)
HOR = [15, 30, 60, 120, 240]

def F(v):
    try: return float(v)
    except: return None

E = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    if f[-11:-4] > '2024-06': continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: k for k, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            k = row[i['f_eventKind']]
            if k not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            net = F(row[i['y_net_60m']])
            if net is None: continue
            et = row[i['f_barCloseEt']]
            d = {'day': et[:10], 'yr': et[:4], 'hhmm': et[11:16], 'kind': k,
                 'side': int(row[i['f_side']]), 'net': net,
                 'atr': F(row[i['f_atr']]) or 0.0,
                 'swHi': row[i['f_swingHighLabel']], 'swLo': row[i['f_swingLowLabel']],
                 'pushN': F(row[i['f_vectorPushCount']]) or 0,
                 'pushDir': row[i['f_vectorPushDirection']],
                 'pushPoor': row[i['f_vectorPushPoorProgress']] == 'TRUE',
                 'comp': F(row[i['f_compressionRatio']]),
                 'msv': F(row[i['f_minutesSinceVector_15m']]),
                 'ft': row[i['f_formationType']],
                 'fbrk': row[i['f_formationBreakConfirmed']] == 'TRUE',
                 'fret': row[i['f_formationRetestConfirmed']] == 'TRUE',
                 'finv': row[i['f_formationInvalidated']] == 'TRUE',
                 'adr': F(row[i['f_adrConsumedPct']]),
                 's4h': row[i['f_struct_4h']], 'vwap': F(row[i['f_distVwapAtr']]),
                 'wick': row[i['f_vectorWickedBeyond_15m']] == 'TRUE',
                 'closed': row[i['f_vectorClosedBeyond_15m']] == 'TRUE',
                 'fan': row[i['f_emaFanState_15m']],
                 'mfeP': F(row[i['y_maxMfePts']]) or 0.0,
                 'maeP': F(row[i['y_maxMaePts']]) or 0.0}
            for H in HOR:
                d['net%d' % H] = F(row[i['y_net_%dm' % H]])
                d['mfe%d' % H] = F(row[i['y_mfe_%dm' % H]])
                d['mae%d' % H] = F(row[i['y_mae_%dm' % H]])
            E.append(d)

devc = sorted(e['comp'] for e in E if e['comp'] is not None and e['day'] <= '2022-12-31')
q20 = devc[int(len(devc) * .2)]; q80 = devc[int(len(devc) * .8)]
firstmorn = {}
for idx, e in enumerate(sorted(range(len(E)), key=lambda j: (E[j]['day'], E[j]['hhmm']))):
    ev = E[e]
    if '09:30' <= ev['hhmm'] <= '10:30' and ev['day'] not in firstmorn:
        firstmorn[ev['day']] = e

def member_dir(n, j):
    e = E[j]; s = e['side']
    if n == 'N1':
        if e['kind'] == 'BREAK_HIGH' and e['swHi'] == 'EQUAL_HIGH': return -1
        if e['kind'] == 'BREAK_LOW' and e['swLo'] == 'EQUAL_LOW': return -1
        return 0
    if n == 'N2':
        if not (e['pushPoor'] and e['pushN'] >= 3): return 0
        pd = 1 if e['pushDir'] == 'BULLISH' else (-1 if e['pushDir'] == 'BEARISH' else 0)
        return -1 if (pd and pd == s) else 0
    if n == 'N3': return +1 if (e['comp'] is not None and e['comp'] <= q20) else 0
    if n == 'N4': return -1 if (e['comp'] is not None and e['comp'] >= q80) else 0
    if n == 'N5': return +1 if (e['msv'] is not None and e['msv'] > 240) else 0
    if n == 'N6':
        if e['finv'] or not (e['fbrk'] and e['fret']): return 0
        want = 1 if e['ft'] == 'W' else (-1 if e['ft'] == 'M' else 0)
        return +1 if want == s else 0
    if n == 'N7': return -1 if firstmorn.get(e['day']) == j else 0
    if n == 'N8': return -1 if (e['adr'] is not None and e['adr'] >= 100) else 0
    if n == 'N9': return -1 if e['s4h'] in ('RANGE_CONTRACTING', 'RANGE_EXPANDING') else 0
    if n == 'N10':
        if e['vwap'] is None: return 0
        if e['kind'] == 'BREAK_HIGH' and e['vwap'] >= 2: return -1
        if e['kind'] == 'BREAK_LOW' and e['vwap'] <= -2: return -1
        return 0
    if n == 'N11': return -1 if (e['wick'] and not e['closed']) else 0
    if n == 'N12':
        if e['fan'] == 'BULLISH' and e['kind'] == 'BREAK_HIGH': return +1
        if e['fan'] == 'BEARISH' and e['kind'] == 'BREAK_LOW': return +1
        return 0
    return 0

NAMES = ['N%d' % k for k in range(1, 13)]
def split_of(day): return 'DEV' if day <= '2022-12-31' else 'VAL'

# membership is a FEATURE property - the outcome shuffle never changes it
MEMB = {n: [(j, member_dir(n, j)) for j in range(len(E)) if member_dir(n, j) != 0]
        for n in NAMES}

def boot_p(rows, nb=800):
    byd = defaultdict(list)
    for d, v in rows: byd[d].append(v)
    days = list(byd.values())
    if not days: return 1.0
    ge = 0
    for _ in range(nb):
        s = [x for dd in random.choices(days, k=len(days)) for x in dd]
        if sum(s) / len(s) <= 0: ge += 1
    return ge / nb

print('=' * 104)
print('NOISE FLOOR - the identical 12-way search run on within-day-SHUFFLED outcomes')
print('=' * 104)
byday = defaultdict(list)
for j, e in enumerate(E): byday[e['day']].append(j)
orig = [e['net'] for e in E]
NS = 200
best = []; anyall = 0
for it in range(NS):
    for _, idxs in byday.items():
        vals = [orig[j] for j in idxs]
        random.shuffle(vals)
        for j, v in zip(idxs, vals): E[j]['net'] = v
    bm = -9e9; hit = False
    for n in NAMES:
        agg = defaultdict(list)
        for j, d in MEMB[n]:
            e = E[j]; agg[(split_of(e['day']), e['yr'])].append(d * e['net'] - COST)
        dev = [v for k, vs in agg.items() if k[0] == 'DEV' for v in vs]
        val = [v for k, vs in agg.items() if k[0] == 'VAL' for v in vs]
        if not dev or not val: continue
        mud = sum(dev) / len(dev)
        if mud > bm: bm = mud
        yrs = [sum(vs) / len(vs) for vs in agg.values()]
        if all(y > 0 for y in yrs) and mud > 0 and sum(val) / len(val) > 0: hit = True
    best.append(bm)
    if hit: anyall += 1
for j, v in enumerate(orig): E[j]['net'] = v
best.sort()
print('best DEV mean of 12, on PURE NOISE: median %+0.3f  p90 %+0.3f  max %+0.3f pt'
      % (best[NS // 2], best[int(NS * .9)], best[-1]))
print('shuffles where >=1 of 12 was positive EVERY YEAR in both splits: %d of %d (%.0f%%)'
      % (anyall, NS, 100.0 * anyall / NS))
print('-> on real data the best of 12 was +1.509 (N7) and ZERO were positive every year.')

# ------------------------------------------------------------------
print('\n' + '=' * 104)
print('AUTOPSY - the five best on DEV: why they lose, and whether any stop/horizon repairs them')
print('=' * 104)
TOP = ['N7', 'N2', 'N6', 'N12', 'N9']
STOPS = [('none', None), ('1.0atr', 1.0), ('1.5atr', 1.5), ('2.0atr', 2.0), ('3.0atr', 3.0)]

for n in TOP:
    rows = [(j, d) for j, d in MEMB[n]]
    print('\n#### %s   n=%d' % (n, len(rows)))
    # 1. excursion asymmetry IN THE TRADED DIRECTION
    for sp in ('DEV', 'VAL'):
        fav = []; adv = []
        for j, d in rows:
            e = E[j]
            if split_of(e['day']) != sp or e['atr'] <= 0: continue
            # follow: fav=mfe adv=mae ; fade: fav=mae adv=mfe
            f_, a_ = (e['mfeP'], e['maeP']) if d > 0 else (e['maeP'], e['mfeP'])
            fav.append(f_ / e['atr']); adv.append(a_ / e['atr'])
        if not fav: continue
        fav.sort(); adv.sort()
        mf = fav[len(fav) // 2]; ma = adv[len(adv) // 2]
        print('  %s excursion in traded dir: medFav %5.2f ATR  medAdv %5.2f ATR  ratio %5.3f'
              % (sp, mf, ma, mf / ma if ma else float('nan')))
    # 2. stop x horizon grid
    print('  net pts/trade after cost   [DEV | VAL]')
    print('  %-8s %s' % ('stop', ''.join('%18s' % ('H=%dm' % H) for H in HOR)))
    bestcell = None
    for tag, mult in STOPS:
        line = '  %-8s' % tag
        for H in HOR:
            out = {}
            for sp in ('DEV', 'VAL'):
                acc = []
                for j, d in rows:
                    e = E[j]
                    if split_of(e['day']) != sp: continue
                    nh = e['net%d' % H]
                    if nh is None: continue
                    if mult is None:
                        v = d * nh
                    else:
                        S = mult * e['atr']
                        adv = e['mae%d' % H] if d > 0 else e['mfe%d' % H]
                        v = -S if (S > 0 and adv is not None and adv >= S) else d * nh
                    acc.append(v - COST)
                out[sp] = sum(acc) / len(acc) if acc else float('nan')
            line += '%9.2f|%8.2f' % (out['DEV'], out['VAL'])
            if out['DEV'] > 0 and out['VAL'] > 0:
                if bestcell is None or out['DEV'] + out['VAL'] > bestcell[2]:
                    bestcell = (tag, H, out['DEV'] + out['VAL'], out['DEV'], out['VAL'])
        print(line)
    if bestcell:
        print('  BEST cell positive in BOTH splits: stop %s, horizon %dm  ->  DEV %+0.2f  VAL %+0.2f'
              % (bestcell[0], bestcell[1], bestcell[3], bestcell[4]))
    else:
        print('  NO stop x horizon cell is positive in both splits (25 tried).')
