#!/usr/bin/env python3
# ORDER-FLOW SETUP GRADING STUDY  (A+ / A- / B+ / B-)
#
# Question: does executed order flow AT THE EVENT stratify the forward
# outcome of a structure break? This is the pre-registered B2 ablation
# (STRUCTURE vs STRUCTURE+ORDERFLOW) expressed as a grade.
#
# v2 CORRECTION (defect fix, not an outcome-driven tweak): v1 double
# counted two ingredients. The engine sets CumDeltaSlope = CumDeltaChange
# = cumDelta - prevCumDelta = BarDelta, so f_ofCumDeltaSlope is an EXACT
# ALIAS of f_ofBarDelta - "delta agrees" scored +2. And DeltaFailsBreak =
# bullish OR bearish divergence, so "fails" and "divergence against"
# overlap - the failure side scored -2. Double-counting both tails
# mechanically widens the A+ to B- spread. v2 uses SIX independent
# ingredients. Outcomes are also reported in R units, because points are
# not a stable unit.
#
# ANTI-SEARCH DISCIPLINE - the score is NOT fitted:
# every ingredient's sign is taken from the pre-registered H-OF library
# (H-OF3/H-OF4 continuation-confirmation; H-OF5/H-OF6/H-OF9
# divergence/absorption failure), NOT from whichever direction scores
# best. Ingredients: 8, fixed. Directions searched: 0. Bin edges: one
# fixed set, declared below before any grade outcome was printed.
#
# Splits: OF-DEV 2025-11-02..2026-02-28, OF-VAL 2026-03-01..2026-05-31.
# OF-OOS (Jun-Aug 2026) IS NOT READ.
#
# Population: non-control structure BREAK events joined to the 1m
# volumetric bar closing at the event minute (99.7% join). Outcome:
# probe-side signed net points at 60m, the frozen primary metric.

import csv, glob, os, random
from collections import defaultdict

SP = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
SPLITS = {'OF-DEV': ('2025-11-02', '2026-02-28'), 'OF-VAL': ('2026-03-01', '2026-05-31')}
BASE_COST = 0.87
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

# ---------- order flow at each minute ----------
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
                'slope': F(row[i['f_ofCumDeltaSlope']]) or 0.0,
                'relvol': F(row[i['f_ofRelVolume']]) or 0.0,
                'sb3': F(row[i['f_stackedBuyLevels_3x']]) or 0.0,
                'ss3': F(row[i['f_stackedSellLevels_3x']]) or 0.0,
                'confirm': row[i['f_deltaConfirmsBreak']] == 'TRUE',
                'fails': row[i['f_deltaFailsBreak']] == 'TRUE',
                'absB': row[i['f_absorptionBuyCandidate']] == 'TRUE',
                'absS': row[i['f_absorptionSellCandidate']] == 'TRUE',
                'divBull': row[i['f_bullishDeltaDivergenceCandidate']] == 'TRUE',
                'divBear': row[i['f_bearishDeltaDivergenceCandidate']] == 'TRUE',
            }

# ---------- structure events ----------
EV = []
for f in sorted(glob.glob(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_*.csv'))):
    m = f[-11:-4]
    if not ('2025-11' <= m <= '2026-05'): continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            kind = row[i['f_eventKind']]
            if kind not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            et = row[i['f_barCloseEt']]
            of = OF.get(et)
            if of is None: continue
            net = F(row[i['y_net_60m']])
            if net is None: continue
            side = int(row[i['f_side']])
            EV.append({'et': et, 'day': et[:10], 'side': side, 'net': net,
                       'mfeR': F(row[i['y_maxMfeR']]),
                       'maeR': F(row[i['y_maxMaeR']]),
                       'mfeP': F(row[i['y_maxMfePts']]),
                       'of': of, 'kind': kind})

# ---------- the frozen score ----------
def score(e):
    """+1 per pre-declared continuation confirmation, -1 per pre-declared
    failure signal. Sign of every term comes from the H-OF library."""
    o = e['of']; s = e['side']; sc = 0
    # H-OF3/H-OF4: order flow confirms the break -> continuation
    if o['confirm']: sc += 1
    if (o['delta'] > 0) == (s > 0) and o['delta'] != 0: sc += 1
    # slope term REMOVED: exact alias of delta (engine sets slope=barDelta)
    same_stack = o['sb3'] if s > 0 else o['ss3']
    if same_stack >= 3: sc += 1
    if o['relvol'] >= 1.5: sc += 1                      # participation
    # H-OF5/H-OF6/H-OF9: non-confirmation / absorption -> failure
    # 'fails' term REMOVED: it is (bullDiv OR bearDiv), overlapping the
    # side-oriented divergence term below.
    if (o['absB'] if s > 0 else o['absS']): sc -= 1     # absorption against the break
    if (o['divBear'] if s > 0 else o['divBull']): sc -= 1
    return sc

# fixed bin edges, declared before any grade outcome was viewed
def grade(sc):
    if sc >= 3: return 'A+'
    if sc >= 1: return 'A-'
    if sc == 0: return 'B+'
    return 'B-'

ORDER = ['A+', 'A-', 'B+', 'B-']

def rows_for(split):
    a, b = SPLITS[split]; return [e for e in EV if a <= e['day'] <= b]

def boot(vals, days, nb=2000):
    byd = defaultdict(list)
    for v, d in zip(vals, days): byd[d].append(v)
    dd = list(byd.values())
    if not dd: return float('nan'), float('nan')
    ms = []
    for _ in range(nb):
        s = [x for g in random.choices(dd, k=len(dd)) for x in g]
        ms.append(sum(s) / len(s))
    ms.sort()
    return ms[int(.025 * nb)], ms[int(.975 * nb)]

print('=' * 96)
print('ORDER-FLOW SETUP GRADING  -  8 fixed ingredients, 0 directions searched, 1 bin set')
print('OF-OOS (Jun-Aug 2026) NOT READ')
print('=' * 96)
print('joined break events: %d   OF minutes: %d' % (len(EV), len(OF)))

res = {}
for split in SPLITS:
    rows = rows_for(split)
    a, b = SPLITS[split]
    print('\n#### %s  (%s .. %s)   n=%d  days=%d' % (split, a, b, len(rows),
                                                     len(set(e['day'] for e in rows))))
    print('%-4s %6s %7s %9s %9s %8s %9s %8s %8s' % (
        'grade', 'n', 'share', 'meanNet', 'net@base', 'win%', 'boot95CI', 'medMFE_R', 'medMAE_R') + '  meanNetR  mean|net|')
    by = defaultdict(list)
    for e in rows: by[grade(score(e))].append(e)
    for g in ORDER:
        v = by.get(g, [])
        if not v:
            print('%-4s %6d   --' % (g, 0)); continue
        nets = [e['net'] for e in v]
        mu = sum(nets) / len(nets)
        lo, hi = boot(nets, [e['day'] for e in v])
        wr = sum(1 for x in nets if x > 0) / len(nets)
        mfeR = sorted(e['mfeR'] for e in v if e['mfeR'] is not None)
        maeR = sorted(e['maeR'] for e in v if e['maeR'] is not None)
        med = lambda z: z[len(z) // 2] if z else float('nan')
        netRs = [e['net'] / (e['mfeP'] / e['mfeR']) for e in v
                 if e['mfeR'] and e['mfeP'] and e['mfeR'] != 0]
        muR = sum(netRs) / len(netRs) if netRs else float('nan')
        absnet = sum(abs(x) for x in nets) / len(nets)
        print('%-4s %6d %6.1f%% %+9.3f %+9.3f %7.1f%% [%+.2f,%+.2f] %8.2f %8.2f %+8.3f %8.1f' % (
            g, len(v), 100 * len(v) / len(rows), mu, mu - BASE_COST, 100 * wr, lo, hi,
            med(mfeR), med(maeR), muR, absnet))
        res[(split, g)] = mu
    # monotonicity + spread
    have = [g for g in ORDER if (split, g) in res]
    if len(have) >= 2:
        seq = [res[(split, g)] for g in have]
        mono = all(seq[i] >= seq[i + 1] for i in range(len(seq) - 1))
        print('  monotone A+>=A->=B+>=B- : %s    spread(top-bottom) %+0.3f pt'
              % (mono, seq[0] - seq[-1]))

# ---------- permutation control on the SPREAD ----------
print('\n#### permutation control (within-day shuffled outcomes, 300 perms)')
for split in SPLITS:
    rows = rows_for(split)
    byd = defaultdict(list)
    for e in rows: byd[e['day']].append(e['net'])
    gl = [grade(score(e)) for e in rows]
    days = [e['day'] for e in rows]
    real = defaultdict(list)
    for g, e in zip(gl, rows): real[g].append(e['net'])
    if 'A+' not in real or 'B-' not in real:
        print('  %s: a grade bin is empty, spread undefined' % split); continue
    obs = sum(real['A+']) / len(real['A+']) - sum(real['B-']) / len(real['B-'])
    ge = 0; spreads = []
    for _ in range(300):
        pool = {d: random.sample(v, len(v)) for d, v in byd.items()}
        ptr = defaultdict(int)
        sim = defaultdict(list)
        for g, d in zip(gl, days):
            sim[g].append(pool[d][ptr[d]]); ptr[d] += 1
        sp = sum(sim['A+']) / len(sim['A+']) - sum(sim['B-']) / len(sim['B-'])
        spreads.append(sp)
        if sp >= obs: ge += 1
    spreads.sort()
    print('  %-7s observed A+ minus B- spread %+0.3f pt   shuffled: med %+0.3f  p95 %+0.3f  max %+0.3f   p=%.3f'
          % (split, obs, spreads[150], spreads[285], spreads[-1], (ge + 1) / 301))

# ---------- single-ingredient incremental read ----------
print('\n#### single-ingredient separation (OF-DEV, mean net when TRUE vs FALSE)')
rows = rows_for('OF-DEV')
def flag(e, name):
    o = e['of']; s = e['side']
    return {'confirm': o['confirm'], 'fails': o['fails'],
            'absorb_against': (o['absB'] if s > 0 else o['absS']),
            'div_against': (o['divBear'] if s > 0 else o['divBull']),
            'delta_agrees': (o['delta'] > 0) == (s > 0) and o['delta'] != 0,
            'slope_agrees': (o['slope'] > 0) == (s > 0) and o['slope'] != 0,
            'stack3_same': (o['sb3'] if s > 0 else o['ss3']) >= 3,
            'relvol>=1.5': o['relvol'] >= 1.5}[name]
for name in ['confirm', 'fails', 'absorb_against', 'div_against', 'delta_agrees',
             'stack3_same', 'relvol>=1.5']:
    t = [e['net'] for e in rows if flag(e, name)]
    f = [e['net'] for e in rows if not flag(e, name)]
    if not t or not f: continue
    print('  %-16s TRUE n=%4d %+7.3f   FALSE n=%4d %+7.3f   diff %+7.3f'
          % (name, len(t), sum(t) / len(t), len(f), sum(f) / len(f),
             sum(t) / len(t) - sum(f) / len(f)))
