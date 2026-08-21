#!/usr/bin/env python3
# VEC-H1 CONFIRMATORY TEST - executes docs/VECH1_PREREGISTRATION.md.
# The preregistration was frozen 2026-08-20, BEFORE this capture existed.
#
# Splits: DEV 2019-07-01..2022-12-31, VAL 2023-01-01..2024-06-30.
# HOLD (2024-07-01 onward) IS NOT READ by this script - month files
# after 2024-06 are never opened.
#
# Frozen gates (all required for SUCCESS):
#   symmetry check FIRST, before any expectancy is quoted
#   C mean net_60m > 0 at 0.87pt cost, day-block bootstrap p<0.05 (1-sided)
#   C beats A AND C beats B in DEV and again in VAL
#   permutation p < 0.05
#   BH q=0.05 across the arm-family tests
#   >= 200 independent C events per split

import csv, glob, os, random
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/vh1full'
COSTS = [('gross', 0.0), ('comm', 0.37), ('base', 0.87), ('stress', 1.37)]
SPLITS = [('DEV', '2019-07-01', '2022-12-31'), ('VAL', '2023-01-01', '2024-06-30')]
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

R = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_vech1_*.csv'))):
    mo = os.path.basename(f)[-11:-4]
    if mo > '2024-06': continue                      # HOLD: never opened
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: k for k, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isWarmup']] == 'TRUE': continue
            net = F(row[i['y_net_60m']])
            if net is None: continue
            R.append({'day': row[i['f_entryEt']][:10],
                      'arm': row[i['f_arm']],
                      'side': int(row[i['f_side']]),
                      'net': net,
                      'stop': F(row[i['f_stopMediumPts']]) or 1.0,
                      'mfe': F(row[i['y_maxMfePts']]) or 0.0,
                      'mae': F(row[i['y_maxMaePts']]) or 0.0,
                      'r1': row[i['y_race_1R']], 'r2': row[i['y_race_2R']]})

def rows_in(split, arm=None):
    _, a, b = next(s for s in SPLITS if s[0] == split)
    return [x for x in R if a <= x['day'] <= b and (arm is None or x['arm'] == arm)]

def med(z):
    z = sorted(z); return z[len(z) // 2] if z else float('nan')

def day_boot_mean(rows, nb=2000):
    byd = defaultdict(list)
    for x in rows: byd[x['day']].append(x['net'])
    days = list(byd.values())
    ms = []
    for _ in range(nb):
        s = [v for d in random.choices(days, k=len(days)) for v in d]
        ms.append(sum(s) / len(s))
    ms.sort()
    return ms

def day_boot_diff(rc, ro, nb=2000):
    """C-minus-other difference, resampling DAYS jointly so shared market
    days move together."""
    bc = defaultdict(list); bo = defaultdict(list)
    for x in rc: bc[x['day']].append(x['net'])
    for x in ro: bo[x['day']].append(x['net'])
    days = sorted(set(bc) | set(bo))
    ds = []
    for _ in range(nb):
        pick = random.choices(days, k=len(days))
        c = [v for d in pick for v in bc.get(d, [])]
        o = [v for d in pick for v in bo.get(d, [])]
        if c and o: ds.append(sum(c) / len(c) - sum(o) / len(o))
    ds.sort()
    return ds

def perm_p_c(split, nperm=400):
    """within-day arm-label shuffle: is C's mean high vs random same-size
    draws from the same days' rows?"""
    rows = rows_in(split)
    byd = defaultdict(list)
    cnt = defaultdict(int)
    obs_rows = [x for x in rows if x['arm'] == 'C_FULL']
    obs = sum(x['net'] for x in obs_rows) / len(obs_rows)
    for x in rows: byd[x['day']].append(x['net'])
    for x in obs_rows: cnt[x['day']] += 1
    ge = 0
    for _ in range(nperm):
        tot = 0.0; n = 0
        for d, k in cnt.items():
            pool = byd.get(d)
            if not pool or len(pool) < k: continue
            tot += sum(random.sample(pool, k)); n += k
        if n and tot / n >= obs: ge += 1
    return (ge + 1) / (nperm + 1)

def bh(ps, q=0.05):
    m = len(ps); order = sorted(range(m), key=lambda k: ps[k]); th = 0
    for rank, k in enumerate(order, 1):
        if ps[k] <= q * rank / m: th = rank
    out = [False] * m
    for rank, k in enumerate(order, 1):
        if rank <= th: out[k] = True
    return out

print('=' * 96)
print('VEC-H1 CONFIRMATORY TEST  (preregistration frozen before capture; HOLD never opened)')
print('=' * 96)

print('\n#### STEP 0 - THE SYMMETRY CHECK (mandated first)')
for sp, _, _ in SPLITS:
    for arm in ('C_FULL', 'A_LOCATION_ONLY', 'B_VECTOR_AWAY'):
        rows = rows_in(sp, arm)
        mfeR = [x['mfe'] / x['stop'] for x in rows]
        maeR = [x['mae'] / x['stop'] for x in rows]
        print('  %s %-16s n=%5d  medMFE %5.3f R  medMAE %5.3f R  ratio %5.3f' % (
            sp, arm, len(rows), med(mfeR), med(maeR),
            med(mfeR) / med(maeR) if med(maeR) else float('nan')))

print('\n#### PRIMARY METRIC - mean net points at 60m, by arm and cost')
for sp, _, _ in SPLITS:
    print('  %s' % sp)
    print('  %-16s %6s %6s | %8s %8s %8s %8s' % ('arm', 'n', 'days', 'gross', 'comm', 'base', 'stress'))
    for arm in ('C_FULL', 'A_LOCATION_ONLY', 'B_VECTOR_AWAY'):
        rows = rows_in(sp, arm)
        mu = sum(x['net'] for x in rows) / len(rows)
        nd = len(set(x['day'] for x in rows))
        line = '  %-16s %6d %6d |' % (arm, len(rows), nd)
        for _, c in COSTS: line += ' %+8.3f' % (mu - c)
        print(line)

print('\n#### THE GATES')
overall = True
for sp, _, _ in SPLITS:
    C = rows_in(sp, 'C_FULL'); A = rows_in(sp, 'A_LOCATION_ONLY'); B = rows_in(sp, 'B_VECTOR_AWAY')
    muC = sum(x['net'] for x in C) / len(C)
    muA = sum(x['net'] for x in A) / len(A)
    muB = sum(x['net'] for x in B) / len(B)
    boot = day_boot_mean(C)
    p_pos = sum(1 for m in boot if m - 0.87 <= 0) / len(boot)
    dA = day_boot_diff(C, A); dB = day_boot_diff(C, B)
    p_gtA = sum(1 for d in dA if d <= 0) / len(dA)
    p_gtB = sum(1 for d in dB if d <= 0) / len(dB)
    p_perm = perm_p_c(sp)
    ps = [max(p_pos, 1 / 2001.0), max(p_gtA, 1 / 2001.0), max(p_gtB, 1 / 2001.0)]
    passed = bh(ps)
    nOK = len(C) >= 200
    gates = {
        'n>=200': nOK,
        'C net>0 @base': muC - 0.87 > 0,
        'C>A': muC > muA, 'C>B': muC > muB,
        'p(C net>0)<.05': p_pos < 0.05,
        'p(C>A)<.05': p_gtA < 0.05, 'p(C>B)<.05': p_gtB < 0.05,
        'p_perm<.05': p_perm < 0.05,
        'BH all pass': all(passed),
    }
    ok = all(gates.values())
    overall = overall and ok
    print('  %s  C n=%d  meanC %+0.3f (base %+0.3f)  meanA %+0.3f  meanB %+0.3f' % (
        sp, len(C), muC, muC - 0.87, muA, muB))
    print('      p: C>0 %.4f | C>A %.4f | C>B %.4f | perm %.4f | BH %s' % (
        p_pos, p_gtA, p_gtB, p_perm, passed))
    print('      gates: %s' % {k: ('PASS' if v else 'FAIL') for k, v in gates.items()})
    print('      SPLIT VERDICT: %s' % ('PASS' if ok else 'FAIL'))

print('\n#### DIAGNOSTICS (frozen in prereg as reporting, not gates)')
years = ['2019', '2020', '2021', '2022', '2023', '2024']
line = '  C by year (gross):'
for y in years:
    rows = [x for x in R if x['arm'] == 'C_FULL' and x['day'][:4] == y]
    line += '  %s:%s' % (y, ('%+0.2f/n%d' % (sum(x['net'] for x in rows) / len(rows), len(rows))) if rows else '-')
print(line)
for sp, _, _ in SPLITS:
    for s, tag in ((1, 'long'), (-1, 'short')):
        rows = [x for x in rows_in(sp, 'C_FULL') if x['side'] == s]
        if rows:
            print('  %s C %-5s n=%4d  mean %+0.3f' % (sp, tag, len(rows), sum(x['net'] for x in rows) / len(rows)))
for sp, _, _ in SPLITS:
    C = rows_in(sp, 'C_FULL')
    for rc, tag in (('r1', '1R'), ('r2', '2R')):
        cnt = defaultdict(int)
        for x in C: cnt[x[rc]] += 1
        n = cnt['TARGET'] + cnt['STOP'] + cnt['TIMEOUT']
        print('  %s C race %s: TARGET %d STOP %d TIMEOUT %d AMB %d  win%% %.1f' % (
            sp, tag, cnt['TARGET'], cnt['STOP'], cnt['TIMEOUT'], cnt['AMBIGUOUS'],
            100.0 * cnt['TARGET'] / n if n else 0))

print('\n' + '=' * 96)
print('OVERALL VEC-H1 VERDICT: %s' % ('PASS - HOLD may be opened ONCE' if overall
                                      else 'FAIL - HOLD stays sealed'))
print('=' * 96)
