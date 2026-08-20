#!/usr/bin/env python3
# WHAT ACTUALLY SEPARATES OUTCOMES - a disciplined pass over the
# candidates the data itself pointed at, rather than the ones we
# preregistered and already rejected.
#
# STATUS: EXPLORATORY-DERIVED. Outcomes have been seen. Directions,
# however, are NOT fitted - each comes from the pre-registered H-OF
# library (H-OF5/H-OF6: price extreme + CVD non-confirmation -> failure;
# H-OF9: aggression without result -> trapped aggressor).
#
# Candidates tested (4, all reported, none dropped):
#   C1  FADE a break that shows delta divergence against it   (OF window)
#   C2  FADE a break where order flow "fails" it              (OF window)
#   C3  AVOID breaks with NO level interaction                (7 years)
#   C4  AVOID breaks on repeat level tests                    (7 years)
#
# OF splits: OF-DEV Nov25-Feb26, OF-VAL Mar-May26, OF-LATE Jun-Jul26
# (OF-LATE was spent as a P&L illustration on 2026-08-20 and is shown
# here for completeness, NOT as clean confirmatory evidence).
# Structure splits: DEV 2019-07..2022-12, VAL 2023-01..2024-06,
# HOLD 2024-07..2026-08 (structure OOS/lockbox - still untouched, NOT read).

import csv, glob, os, random
from collections import defaultdict

SP = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COST = 0.87
random.seed(41)
OFM = ['2025-11', '2025-12', '2026-01', '2026-02', '2026-03', '2026-04', '2026-05',
       '2026-06', '2026-07']
OF_SPLITS = [('OF-DEV', '2025-11-01', '2026-02-28'), ('OF-VAL', '2026-03-01', '2026-05-31'),
             ('OF-LATE*', '2026-06-01', '2026-07-31')]
ST_SPLITS = [('DEV', '2019-07-01', '2022-12-31'), ('VAL', '2023-01-01', '2024-06-30')]

def F(v):
    try: return float(v)
    except: return None

def dayboot(rows, nb=2000):
    byd = defaultdict(list)
    for d, v in rows: byd[d].append(v)
    dd = list(byd.values())
    if not dd: return float('nan'), float('nan'), float('nan')
    ms = []
    for _ in range(nb):
        s = [x for g in random.choices(dd, k=len(dd)) for x in g]
        ms.append(sum(s) / len(s))
    ms.sort()
    return ms[int(.025 * nb)], ms[int(.975 * nb)], sum(1 for m in ms if m <= 0) / nb

def permp(sel, allpool, nperm=400):
    """sel: [(day, value)] chosen rows. allpool: {day: [values]} of the
    eligible population. Tests whether the selection beats a random
    same-size selection from the same days."""
    if not sel: return 1.0
    obs = sum(v for _, v in sel) / len(sel)
    cnt = defaultdict(int)
    for d, _ in sel: cnt[d] += 1
    ge = 0
    for _ in range(nperm):
        tot = 0.0; n = 0
        for d, k in cnt.items():
            pool = allpool.get(d)
            if not pool or len(pool) < k: continue
            tot += sum(random.sample(pool, k)); n += k
        if n and tot / n >= obs: ge += 1
    return (ge + 1) / (nperm + 1)

# ---------------- order flow window ----------------
OF = {}
for mf in OFM:
    p = os.path.join(SP, 'of1', 'v4_1_orderflow_MNQ_v41of_%s.csv' % mf)
    with open(p, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            OF[row[i['f_barCloseEt']]] = (
                row[i['f_bullishDeltaDivergenceCandidate']] == 'TRUE',
                row[i['f_bearishDeltaDivergenceCandidate']] == 'TRUE',
                row[i['f_deltaFailsBreak']] == 'TRUE')

OFEV = []
for mf in OFM:
    with open(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_%s.csv' % mf), newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            k = row[i['f_eventKind']]
            if k not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            et = row[i['f_barCloseEt']]; o = OF.get(et)
            if o is None: continue
            mp, mr = F(row[i['y_maxMfePts']]), F(row[i['y_maxMfeR']])
            net = F(row[i['y_net_60m']])
            if not mp or not mr or net is None: continue
            stop = mp / mr
            OFEV.append({'day': et[:10], 'mon': et[:7], 'side': int(row[i['f_side']]),
                         'net': net, 'stop': stop,
                         'mfeP': mp, 'maeP': F(row[i['y_maxMaePts']]) or 0.0,
                         'divBull': o[0], 'divBear': o[1], 'fails': o[2], 'kind': k})

def div_against(e):
    return e['divBear'] if e['side'] > 0 else e['divBull']

print('=' * 98)
print('CANDIDATE SCAN - directions taken from the H-OF library, not fitted')
print('=' * 98)

for cid, name, pick in (
        ('C1', 'FADE break with delta divergence against it', div_against),
        ('C2', 'FADE break flagged deltaFailsBreak', lambda e: e['fails'])):
    print('\n#### %s  %s' % (cid, name))
    print('  %-9s %6s %6s %9s %9s %9s %8s %8s %8s' % (
        'split', 'n', 'days', 'fadeR', 'net@cost', 'boot95', 'p_boot', 'p_perm', 'win%'))
    for tag, a, b in OF_SPLITS:
        rows = [e for e in OFEV if a <= e['day'] <= b]
        pool = defaultdict(list)
        for e in rows: pool[e['day']].append(-e['net'] / e['stop'] - COST / e['stop'])
        sel = [(e['day'], -e['net'] / e['stop'] - COST / e['stop']) for e in rows if pick(e)]
        if len(sel) < 10:
            print('  %-9s %6d   too few' % (tag, len(sel))); continue
        mu = sum(v for _, v in sel) / len(sel)
        lo, hi, pb = dayboot(sel)
        pp = permp(sel, pool)
        wr = sum(1 for _, v in sel if v > 0) / len(sel)
        print('  %-9s %6d %6d %+9.4f %+9.4f [%+.2f,%+.2f] %8.4f %8.4f %7.1f%%' % (
            tag, len(sel), len(set(d for d, _ in sel)), mu + COST / 1e9, mu, lo, hi, pb, pp, 100 * wr))
    # R:R profile of the fade side (break MAE becomes fade MFE)
    rows = [e for e in OFEV if pick(e)]
    if rows:
        fm = sorted(e['maeP'] / e['stop'] for e in rows)   # fade favourable
        fa = sorted(e['mfeP'] / e['stop'] for e in rows)   # fade adverse
        q = lambda z, p: z[int((len(z) - 1) * p)]
        print('  fade-side excursion (R): MFE med %.2f p75 %.2f p90 %.2f | MAE med %.2f p75 %.2f'
              % (q(fm, .5), q(fm, .75), q(fm, .9), q(fa, .5), q(fa, .75)))

# ---------------- 7-year structure window ----------------
SEV = []
for f in sorted(glob.glob(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_*.csv'))):
    mo = f[-11:-4]
    if mo > '2024-06': continue          # HOLD (structure OOS/lockbox) NOT READ
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            if row[i['f_eventKind']] not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            mp, mr = F(row[i['y_maxMfePts']]), F(row[i['y_maxMfeR']])
            net = F(row[i['y_net_60m']])
            if not mp or not mr or net is None: continue
            et = row[i['f_barCloseEt']]
            SEV.append({'day': et[:10], 'net': net, 'stop': mp / mr,
                        'inter': row[i['f_interaction']],
                        'tests': F(row[i['f_levelInteractionCountSession']]) or 0})

print('\n\n#### C3 / C4  AVOIDANCE CONDITIONS on the 7-year structure window')
print('  (net R at 60m, cost-adjusted, break side as the engine armed it)')
for cid, name, pick in (
        ('C3', 'breaks with NO level interaction', lambda e: e['inter'] == 'NO_INTERACTION'),
        ('C4', 'breaks on a repeat level test (>=3 today)', lambda e: e['tests'] >= 3)):
    print('\n  %s  %s' % (cid, name))
    print('    %-5s %8s %10s %10s %10s %9s' % ('split', 'n', 'IN mean', 'OUT mean', 'diff', 'p_boot(IN)'))
    for tag, a, b in ST_SPLITS:
        rows = [e for e in SEV if a <= e['day'] <= b]
        IN = [(e['day'], e['net'] / e['stop'] - COST / e['stop']) for e in rows if pick(e)]
        OUT = [(e['day'], e['net'] / e['stop'] - COST / e['stop']) for e in rows if not pick(e)]
        if len(IN) < 30 or len(OUT) < 30:
            print('    %-5s   too few' % tag); continue
        mi = sum(v for _, v in IN) / len(IN); mo_ = sum(v for _, v in OUT) / len(OUT)
        _, _, pb = dayboot(IN)
        print('    %-5s %8d %+10.4f %+10.4f %+10.4f %9.4f' % (tag, len(IN), mi, mo_, mi - mo_, pb))

print('\n\n#### per-month C1 (fade divergent break), net R after cost')
byq = defaultdict(list)
for e in OFEV:
    if div_against(e): byq[e['mon']].append(-e['net'] / e['stop'] - COST / e['stop'])
for m in sorted(byq):
    v = byq[m]
    print('  %s  n=%3d  %+0.4f' % (m, len(v), sum(v) / len(v)))
