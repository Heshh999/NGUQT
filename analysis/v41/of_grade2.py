#!/usr/bin/env python3
# FOCUSED FOLLOW-UP: is the A+ vs B+ contrast real, or a volatility proxy?
#
# MULTIPLICITY ON THE RECORD. Tests run in this grading study so far:
#   1. v1 score (double-counted) x 2 splits
#   2. v2 score (corrected)      x 2 splits
#   3. this A+ vs B+ contrast    x 2 splits
# The A+/B+ contrast was CHOSEN AFTER seeing the v2 table because it
# looked most stable. That is a search over contrasts. Everything below
# is EXPLORATORY - NOT YET CONFIRMED, and is reported as such.
#
# Controls applied:
#   - permutation on the CONTRAST (not the whole spread)
#   - day-block bootstrap on the A+ minus B+ difference
#   - ATR-matched comparison: does A+ still beat B+ inside the same
#     volatility bucket? (A+ has visibly lower MAE_R - the grade may be
#     a quiet-trend proxy rather than order-flow information)
#   - per-month stability
#   - costs in R
# OF-OOS (Jun-Aug 2026) IS NOT READ.

import csv, glob, os, random
from collections import defaultdict

SP = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
SPLITS = {'OF-DEV': ('2025-11-02', '2026-02-28'), 'OF-VAL': ('2026-03-01', '2026-05-31')}
BASE_COST = 0.87
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

OF = {}
for f in sorted(glob.glob(os.path.join(SP, 'of1', 'v4_1_orderflow_MNQ_v41of_*.csv'))):
    m = f[-11:-4]
    if not ('2025-11' <= m <= '2026-05'): continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            OF[row[i['f_barCloseEt']]] = {
                'delta': F(row[i['f_ofBarDelta']]) or 0.0,
                'relvol': F(row[i['f_ofRelVolume']]) or 0.0,
                'sb3': F(row[i['f_stackedBuyLevels_3x']]) or 0.0,
                'ss3': F(row[i['f_stackedSellLevels_3x']]) or 0.0,
                'confirm': row[i['f_deltaConfirmsBreak']] == 'TRUE',
                'absB': row[i['f_absorptionBuyCandidate']] == 'TRUE',
                'absS': row[i['f_absorptionSellCandidate']] == 'TRUE',
                'divBull': row[i['f_bullishDeltaDivergenceCandidate']] == 'TRUE',
                'divBear': row[i['f_bearishDeltaDivergenceCandidate']] == 'TRUE'}

EV = []
for f in sorted(glob.glob(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_*.csv'))):
    m = f[-11:-4]
    if not ('2025-11' <= m <= '2026-05'): continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            if row[i['f_eventKind']] not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            et = row[i['f_barCloseEt']]; of = OF.get(et)
            if of is None: continue
            net = F(row[i['y_net_60m']]); mfeR = F(row[i['y_maxMfeR']]); mfeP = F(row[i['y_maxMfePts']])
            if net is None or not mfeR or not mfeP: continue
            EV.append({'day': et[:10], 'mon': et[:7], 'side': int(row[i['f_side']]),
                       'net': net, 'stop': mfeP / mfeR, 'atr': F(row[i['f_atr']]) or 0.0,
                       's15': row[i['f_struct_15m']], 'of': of})

def score(e):
    o = e['of']; s = e['side']; sc = 0
    if o['confirm']: sc += 1
    if (o['delta'] > 0) == (s > 0) and o['delta'] != 0: sc += 1
    if (o['sb3'] if s > 0 else o['ss3']) >= 3: sc += 1
    if o['relvol'] >= 1.5: sc += 1
    if (o['absB'] if s > 0 else o['absS']): sc -= 1
    if (o['divBear'] if s > 0 else o['divBull']): sc -= 1
    return sc

def grade(sc): return 'A+' if sc >= 3 else 'A-' if sc >= 1 else 'B+' if sc == 0 else 'B-'
def rows_for(sp):
    a, b = SPLITS[sp]; return [e for e in EV if a <= e['day'] <= b]
def netR(e): return e['net'] / e['stop']

print('=' * 92)
print('A+ vs B+ CONTRAST  -  EXPLORATORY, contrast chosen after seeing the v2 table')
print('=' * 92)

for sp in SPLITS:
    rows = rows_for(sp)
    A = [e for e in rows if grade(score(e)) == 'A+']
    B = [e for e in rows if grade(score(e)) == 'B+']
    costR = lambda e: BASE_COST / e['stop']
    aR = [netR(e) - costR(e) for e in A]
    bR = [netR(e) - costR(e) for e in B]
    da = sum(aR) / len(aR); db = sum(bR) / len(bR)
    print('\n#### %s   A+ n=%d  B+ n=%d' % (sp, len(A), len(B)))
    print('  net R/trade @base   A+ %+0.4f   B+ %+0.4f   diff %+0.4f' % (da, db, da - db))
    print('  mean ATR at event   A+ %6.2f   B+ %6.2f' % (
        sum(e['atr'] for e in A) / len(A), sum(e['atr'] for e in B) / len(B)))
    print('  mean stop (pt)      A+ %6.2f   B+ %6.2f' % (
        sum(e['stop'] for e in A) / len(A), sum(e['stop'] for e in B) / len(B)))

    # day-block bootstrap on the DIFFERENCE
    byd = defaultdict(lambda: ([], []))
    for e in A: byd[e['day']][0].append(netR(e) - costR(e))
    for e in B: byd[e['day']][1].append(netR(e) - costR(e))
    days = list(byd.values()); diffs = []
    for _ in range(2000):
        s = random.choices(days, k=len(days))
        aa = [x for g in s for x in g[0]]; bb = [x for g in s for x in g[1]]
        if aa and bb: diffs.append(sum(aa) / len(aa) - sum(bb) / len(bb))
    diffs.sort()
    print('  bootstrap diff 95%% CI [%+0.4f, %+0.4f]   P(diff<=0) %.4f' % (
        diffs[int(.025 * len(diffs))], diffs[int(.975 * len(diffs))],
        sum(1 for d in diffs if d <= 0) / len(diffs)))

    # permutation on the contrast
    pool = defaultdict(list)
    for e in rows: pool[e['day']].append(netR(e) - costR(e))
    lab = [(grade(score(e)), e['day']) for e in rows]
    obs = da - db; ge = 0; NP = 500
    for _ in range(NP):
        sh = {d: random.sample(v, len(v)) for d, v in pool.items()}
        ptr = defaultdict(int); sa = []; sb = []
        for g, d in lab:
            x = sh[d][ptr[d]]; ptr[d] += 1
            if g == 'A+': sa.append(x)
            elif g == 'B+': sb.append(x)
        if sa and sb and (sum(sa) / len(sa) - sum(sb) / len(sb)) >= obs: ge += 1
    print('  permutation p (A+ minus B+) = %.4f   [%d perms]' % ((ge + 1) / (NP + 1), NP))

    # ATR-matched: same volatility tercile
    at = sorted(e['atr'] for e in rows)
    q1, q2 = at[len(at) // 3], at[2 * len(at) // 3]
    print('  ATR-matched (does A+ still beat B+ at equal volatility?)')
    for tag, lo, hi in (('low', -1e9, q1), ('mid', q1, q2), ('high', q2, 1e9)):
        aa = [netR(e) - costR(e) for e in A if lo <= e['atr'] < hi]
        bb = [netR(e) - costR(e) for e in B if lo <= e['atr'] < hi]
        if len(aa) >= 15 and len(bb) >= 15:
            print('    %-5s ATR  A+ n=%3d %+0.4f   B+ n=%3d %+0.4f   diff %+0.4f' % (
                tag, len(aa), sum(aa) / len(aa), len(bb), sum(bb) / len(bb),
                sum(aa) / len(aa) - sum(bb) / len(bb)))
        else:
            print('    %-5s ATR  n too small (A+ %d, B+ %d)' % (tag, len(aa), len(bb)))

print('\n#### per-month A+ net R/trade @base (stability)')
months = sorted(set(e['mon'] for e in EV))
for sp in SPLITS:
    a, b = SPLITS[sp]
    line = '  %-7s' % sp
    for mo in months:
        rows = [e for e in EV if e['mon'] == mo and a <= e['day'] <= b
                and grade(score(e)) == 'A+']
        if rows:
            line += '  %s:%+0.3f/n%d' % (mo[-2:], sum(netR(e) - BASE_COST / e['stop']
                                                      for e in rows) / len(rows), len(rows))
    print(line)
