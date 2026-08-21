#!/usr/bin/env python3
# N-SERIES - twelve NEW event-class hypotheses on the structure capture.
# EXPLORATORY-DERIVED by construction (the capture has been seen), so the
# rules are: all twelve declared with direction and mechanism BEFORE this
# script was run, all twelve reported, ranked on DEV, checked on VAL, and
# the IDENTICAL search re-run on within-day-shuffled outcomes so "best of
# twelve" has a measured noise floor. HOLD (2024-07 onward) NOT read.
#
# Declared set (direction fixed in this header, not tuned):
#  N1  EQUAL-SWEEP FADE      break of an EQUAL high/low (liquidity pool) -> fade
#  N2  PUSH-EXHAUST FADE     >=3 same-dir vector pushes, poor progress -> fade push dir
#  N3  COMPRESSION GO        tightest-quintile compression + break -> follow
#  N4  EXPANSION FADE        widest-quintile compression + break -> fade
#  N5  QUIET-TAPE GO         no 15m vector for >4h + break -> follow
#  N6  NECKLINE RETEST GO    W/M break confirmed + retest confirmed -> follow formation
#  N7  FIRST-MORNING FADE    day's FIRST break inside 09:30-10:30 ET -> fade
#  N8  ADR-EXHAUST FADE      ADR >=100% consumed + break same way -> fade
#  N9  RANGE-REGIME FADE     4H structure RANGE_* + 15m break -> fade
#  N10 VWAP-STRETCH FADE     |dist to VWAP| >= 2 ATR + break away -> fade
#  N11 WICK-ONLY FADE        vector wicked beyond structure but did NOT close beyond -> fade
#  N12 FAN-ALIGNED GO        15m EMA fan BULLISH + BREAK_HIGH (mirror BEARISH+LOW) -> follow
#
# Metric: event-row y_net_60m (side-signed). FOLLOW ret=+net-cost,
# FADE ret=-net-cost. Base cost 0.87 pt RT. Quintile thresholds for
# N3/N4 computed on DEV only and applied unchanged to VAL.

import csv, glob, os, random
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
COST = 0.87
SPL = [('DEV', '2019-07-01', '2022-12-31'), ('VAL', '2023-01-01', '2024-06-30')]
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

E = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    if f[-11:-4] > '2024-06': continue                    # HOLD sealed
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
            E.append({
                'day': et[:10], 'hhmm': et[11:16], 'kind': k,
                'side': int(row[i['f_side']]), 'net': net,
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
                's4h': row[i['f_struct_4h']],
                'vwap': F(row[i['f_distVwapAtr']]),
                'wick': row[i['f_vectorWickedBeyond_15m']] == 'TRUE',
                'closed': row[i['f_vectorClosedBeyond_15m']] == 'TRUE',
                'fan': row[i['f_emaFanState_15m']],
            })

# DEV-only compression quintiles
devc = sorted(e['comp'] for e in E if e['comp'] is not None and e['day'] <= '2022-12-31')
q20 = devc[int(len(devc) * 0.2)]; q80 = devc[int(len(devc) * 0.8)]

# day -> first morning break flag
firstmorn = {}
for e in sorted(E, key=lambda x: (x['day'], x['hhmm'])):
    if '09:30' <= e['hhmm'] <= '10:30' and e['day'] not in firstmorn:
        firstmorn[e['day']] = id(e)

def member_dir(n, e):
    """returns +1 follow / -1 fade / 0 not a member, per the declared set."""
    s = e['side']
    if n == 'N1':
        if e['kind'] == 'BREAK_HIGH' and e['swHi'] == 'EQUAL_HIGH': return -1
        if e['kind'] == 'BREAK_LOW' and e['swLo'] == 'EQUAL_LOW': return -1
        return 0
    if n == 'N2':
        if not (e['pushPoor'] and e['pushN'] >= 3): return 0
        pd = 1 if e['pushDir'] == 'BULLISH' else (-1 if e['pushDir'] == 'BEARISH' else 0)
        if pd == 0: return 0
        return -1 if pd == s else 0          # fade the push via the aligned break
    if n == 'N3': return +1 if (e['comp'] is not None and e['comp'] <= q20) else 0
    if n == 'N4': return -1 if (e['comp'] is not None and e['comp'] >= q80) else 0
    if n == 'N5': return +1 if (e['msv'] is not None and e['msv'] > 240) else 0
    if n == 'N6':
        if e['finv'] or not (e['fbrk'] and e['fret']): return 0
        want = 1 if e['ft'] == 'W' else (-1 if e['ft'] == 'M' else 0)
        return +1 if want == s else 0        # follow, only when break agrees with formation
    if n == 'N7': return -1 if firstmorn.get(e['day']) == id(e) else 0
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

NAMES = ['N1', 'N2', 'N3', 'N4', 'N5', 'N6', 'N7', 'N8', 'N9', 'N10', 'N11', 'N12']

def day_boot_p(rows, nb=2000):
    byd = defaultdict(list)
    for d, v in rows: byd[d].append(v)
    days = list(byd.values())
    if not days: return float('nan')
    ge = 0
    for _ in range(nb):
        s = [x for dd in random.choices(days, k=len(days)) for x in dd]
        if sum(s) / len(s) <= 0: ge += 1
    return ge / nb

def stats(n, split, net_of=lambda e: e['net']):
    _, a, b = next(s for s in SPL if s[0] == split)
    rows = []
    for e in E:
        if not (a <= e['day'] <= b): continue
        d = member_dir(n, e)
        if d == 0: continue
        rows.append((e['day'], d * net_of(e) - COST, e['day'][:4]))
    if not rows: return None
    mu = sum(v for _, v, _ in rows) / len(rows)
    per = defaultdict(list)
    for _, v, y in rows: per[y].append(v)
    yline = {y: sum(vs) / len(vs) for y, vs in sorted(per.items())}
    return dict(n=len(rows), mu=mu, years=yline,
                allpos=all(m > 0 for m in yline.values()),
                p=day_boot_p([(d, v) for d, v, _ in rows]))

print('=' * 110)
print('N-SERIES: 12 declared hypotheses, net @ 0.87pt cost, 60m horizon.  HOLD not read.')
print('=' * 110)
results = {}
for n in NAMES:
    dv = stats(n, 'DEV'); vl = stats(n, 'VAL')
    results[n] = (dv, vl)
    def fmt(s):
        if s is None: return 'n=0'
        ys = ' '.join('%s:%+.2f' % (y[2:], m) for y, m in s['years'].items())
        return 'n=%5d mu=%+7.3f p=%.3f allYrs=%s | %s' % (s['n'], s['mu'], s['p'],
                                                          'YES' if s['allpos'] else 'no ', ys)
    print('%-4s DEV %s' % (n, fmt(dv)))
    print('     VAL %s' % fmt(vl))

# gates: positive net both splits, p<0.05 DEV, every year positive across DEV+VAL
print('\n#### survivors of the stated ask (net>0 both splits, p_DEV<0.05, every year positive)')
surv = []
for n in NAMES:
    dv, vl = results[n]
    if dv and vl and dv['mu'] > 0 and vl['mu'] > 0 and dv['p'] < 0.05 and dv['allpos'] and vl['allpos']:
        surv.append(n)
print('  survivors: %s' % (surv if surv else 'NONE'))

# ---- THE CONTROL: identical 12-way search on within-day-shuffled outcomes
print('\n#### NOISE FLOOR: the SAME 12-hypothesis search on within-day-shuffled outcomes (200 shuffles)')
# Precompute (index, direction, split, year) per hypothesis ONCE. Membership
# depends only on features, which the outcome shuffle never touches - so the
# control is identical in structure but ~100x cheaper.
MEMB = {}
for n in NAMES:
    lst = []
    for idx, e in enumerate(E):
        d = member_dir(n, e)
        if d == 0: continue
        sp = 'DEV' if e['day'] <= '2022-12-31' else ('VAL' if e['day'] <= '2024-06-30' else None)
        if sp is None: continue
        lst.append((idx, d, sp, e['day'][:4], e['day']))
    MEMB[n] = lst
byday = defaultdict(list)
for idx, e in enumerate(E): byday[e['day']].append(idx)
NS = 200
best_mu = []; n_allpos = []; n_survive = []
orig = [e['net'] for e in E]
for it in range(NS):
    for d, idxs in byday.items():
        vals = [orig[j] for j in idxs]
        random.shuffle(vals)
        for j, v in zip(idxs, vals): E[j]['net'] = v
    bm = -9e9; ap = 0; sv = 0
    for n in NAMES:
        dv = stats(n, 'DEV'); vl = stats(n, 'VAL')
        if dv is None or vl is None: continue
        if dv['mu'] > bm: bm = dv['mu']
        if dv['allpos'] and vl['allpos'] and dv['mu'] > 0 and vl['mu'] > 0:
            ap += 1
            if dv['p'] < 0.05: sv += 1
    best_mu.append(bm); n_allpos.append(ap); n_survive.append(sv)
for j, v in zip(range(len(E)), orig): E[j]['net'] = v
best_mu.sort()
print('  best DEV mean of the 12, on SHUFFLED data: median %+0.3f  p90 %+0.3f  max %+0.3f'
      % (best_mu[NS // 2], best_mu[int(NS * .9)], best_mu[-1]))
print('  shuffles where >=1 hypothesis was positive-every-year in BOTH splits: %d of %d (%.0f%%)'
      % (sum(1 for x in n_allpos if x >= 1), NS, 100.0 * sum(1 for x in n_allpos if x >= 1) / NS))
print('  shuffles where >=1 ALSO passed p_DEV<0.05 (the full stated ask): %d of %d (%.0f%%)'
      % (sum(1 for x in n_survive if x >= 1), NS, 100.0 * sum(1 for x in n_survive if x >= 1) / NS))
