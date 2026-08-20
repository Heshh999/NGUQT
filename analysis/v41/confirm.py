#!/usr/bin/env python3
# V4.1 confirmatory pass - executes docs/V41_PREREGISTRATION.md exactly.
#
# Frozen before any outcome was viewed (2026-08-20):
#   primary metric   mean directional net points at 60m (y_net_60m),
#                    probe-side signed, minus costs
#   splits           DEV 2019-07-01..2022-12-31, VAL 2023-01-01..2024-06-30
#                    (OOS and LOCKBOX are NOT read by this script)
#   costs            gross / 0.37 / 0.87 / 1.37 pt RT
#   multiplicity     BH FDR q=0.05 across the 8 primaries, one-sided
#   inference        day-block bootstrap (2000 resamples)
#   null             within-day permutation of probe outcomes (200 perms)
#
# Membership is constructed from FROZEN f_ features per the registry
# definitions. Engine-assigned hypothesisId is reported beside it where
# it exists (H1/H2) as a cross-check. Architecture per registry:
#   H1 ARCH-C, H2 ARCH-B, H3 ARCH-A, H4 ARCH-B, H5 ARCH-B,
#   TR-H1/TR-H2 ARCH-B (fixed in the preregistration commit).
# H6 runs separately inside the order-flow window (own split).

import csv, glob, os, random, statistics as st
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
COSTS = [('gross', 0.0), ('comm', 0.37), ('base', 0.87), ('stress', 1.37)]
SPLITS = {'DEV': ('2019-07-01', '2022-12-31'), 'VAL': ('2023-01-01', '2024-06-30')}
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

# ---- load structure parents (earliest row per parentEventId) -----------
parents = {}
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            pid = row[i['parentEventId']]
            et = row[i['f_barCloseEt']]
            if pid in parents and parents[pid]['et'] <= et: continue
            parents[pid] = {
                'et': et,
                'hyp': row[i['hypothesisId']],
                'kind': row[i['f_eventKind']],
                'side': int(row[i['f_side']]),
                'isv': row[i['f_isVector_15m']] == 'TRUE',
                'color': row[i['f_vectorColor_15m']],
                'wick': row[i['f_vectorWickedBeyond_15m']] == 'TRUE',
                'closedB': row[i['f_vectorClosedBeyond_15m']] == 'TRUE',
                'inter': row[i['f_interaction']],
                's4h': row[i['f_struct_4h']],
                's15': row[i['f_struct_15m']],
                'form': row[i['f_formationType']],
                'leg2': row[i['f_formationSecondLegConfirmed']] == 'TRUE',
                'finv': row[i['f_formationInvalidated']] == 'TRUE',
                'fexit': row[i['f_vectorExitsFormation']] == 'TRUE',
                'fbrk': row[i['f_formationBreakConfirmed']] == 'TRUE',
                'e800': row[i['f_ema800Ready_15m']] == 'TRUE',
            }

# ---- load entry probes -------------------------------------------------
probes = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_entries_MNQ_v41_*.csv'))):
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isWarmup']] == 'TRUE': continue
            net = F(row[i['y_net_60m']])
            if net is None: continue
            probes.append({
                'pid': row[i['parentEventId']],
                'arch': row[i['f_architecture']],
                'side': int(row[i['f_side']]),
                'day': row[i['f_eventEt']][:10],
                'net': net,
                'delay': F(row[i['f_minsToEntry']]) or 0,
                'zone': row[i['f_targetVectorZoneValid']] == 'TRUE',
            })

def directional(s): return s in ('BULLISH', 'BEARISH')

def member(hid, par, pr):
    if par is None or not par['e800']: return False
    if hid == 'H1':
        return pr['arch'] == 'ARCH-C' and par['hyp'] == 'H1-VECTOR-SWEEP-REVERSAL'
    if hid == 'H2':
        return pr['arch'] == 'ARCH-B' and par['hyp'] == 'H2-VECTOR-BREAK-CONTINUATION'
    if hid == 'H3':
        return pr['arch'] == 'ARCH-A' and par['isv'] and par['wick']
    if hid == 'H4':
        return pr['arch'] == 'ARCH-B' and par['isv'] and par['inter'] != 'NO_INTERACTION'
    if hid == 'H5':
        return pr['arch'] == 'ARCH-B' and pr['zone'] and directional(par['s15'])
    if hid == 'TRH1':
        return (pr['arch'] == 'ARCH-B' and pr['side'] == 1 and par['form'] == 'W'
                and par['leg2'] and not par['finv']
                and par['color'] in ('GREEN', 'BLUE') and (par['fexit'] or par['fbrk']))
    if hid == 'TRH2':
        return (pr['arch'] == 'ARCH-B' and pr['side'] == -1 and par['form'] == 'M'
                and par['leg2'] and not par['finv']
                and par['color'] in ('RED', 'VIOLET') and (par['fexit'] or par['fbrk']))
    return False

PRIMARIES = ['H1', 'H2', 'H3', 'H4', 'H5', 'TRH1', 'TRH2']  # H6 separate (OF window)

def in_split(day, split):
    a, b = SPLITS[split]; return a <= day <= b

def day_boot(rows, nb=2000):
    bydav = defaultdict(list)
    for r in rows: bydav[r['day']].append(r['net'])
    days = list(bydav.values())
    if not days: return (float('nan'),) * 3
    means = []
    for _ in range(nb):
        s = [x for d in random.choices(days, k=len(days)) for x in d]
        means.append(sum(s) / len(s))
    means.sort()
    return means[int(0.025 * nb)], means[int(0.975 * nb)], sum(1 for m in means if m <= 0) / nb

def perm_p(rows, allrows_byday, nperm=200):
    # within-day shuffle: reassign each member row an outcome drawn (without
    # replacement) from the pooled outcomes of the SAME day's probes
    obs = sum(r['net'] for r in rows) / len(rows)
    daymember = defaultdict(int)
    for r in rows: daymember[r['day']] += 1
    ge = 0
    for _ in range(nperm):
        tot = 0.0; n = 0
        for day, k in daymember.items():
            pool = allrows_byday.get(day)
            if not pool or len(pool) < k: continue
            tot += sum(random.sample(pool, k)); n += k
        if n and tot / n >= obs: ge += 1
    return (ge + 1) / (nperm + 1)

def bh(pvals, q=0.05):
    m = len(pvals); order = sorted(range(m), key=lambda k: pvals[k])
    passed = [False] * m; thresh = 0
    for rank, k in enumerate(order, 1):
        if pvals[k] <= q * rank / m: thresh = rank
    for rank, k in enumerate(order, 1):
        if rank <= thresh: passed[k] = True
    return passed

# H0 same-arch matched baseline (structure-only parents)
def h0_baseline(arch, split):
    rows = [p for p in probes if in_split(p['day'], split) and p['arch'] == arch
            and (parents.get(p['pid']) or {}).get('hyp') == 'H0-STRUCTURE-ONLY'
            and (parents.get(p['pid']) or {}).get('e800', False)]
    if not rows: return float('nan'), 0
    return sum(r['net'] for r in rows) / len(rows), len(rows)

print('=' * 100)
print('V4.1 CONFIRMATORY PASS - structure-layer primaries (H6 runs in the OF window separately)')
print('=' * 100)

results = {}
for split in ('DEV', 'VAL'):
    allday = defaultdict(list)
    for p in probes:
        if in_split(p['day'], split): allday[p['day']].append(p['net'])
    print('\n#### %s  (%s .. %s)' % (split, *SPLITS[split]))
    print('%-6s %6s %8s %8s | %8s %8s %8s %8s | %10s %8s | %8s %6s' % (
        'hyp', 'n', 'days', 'mean', 'gross', 'comm', 'base', 'stress',
        'boot95CI', 'p_boot', 'p_perm', 'H0'))
    pvals = []
    for hid in PRIMARIES:
        rows = [p for p in probes if in_split(p['day'], split)
                and member(hid, parents.get(p['pid']), p)]
        if not rows:
            print('%-6s %6d  EMPTY' % (hid, 0)); pvals.append(1.0); continue
        mu = sum(r['net'] for r in rows) / len(rows)
        lo, hi, pb = day_boot(rows)
        pp = perm_p(rows, allday)
        h0mu, h0n = h0_baseline(rows[0]['arch'] if False else
                                {'H1': 'ARCH-C', 'H2': 'ARCH-B', 'H3': 'ARCH-A',
                                 'H4': 'ARCH-B', 'H5': 'ARCH-B',
                                 'TRH1': 'ARCH-B', 'TRH2': 'ARCH-B'}[hid], split)
        nd = len(set(r['day'] for r in rows))
        nets = [mu - c for _, c in COSTS]
        print('%-6s %6d %8d %8.3f | %8.3f %8.3f %8.3f %8.3f | [%5.2f,%5.2f] %6.4f | %8.4f %6.3f' % (
            hid, len(rows), nd, mu, nets[0], nets[1], nets[2], nets[3], lo, hi, pb, pp, h0mu))
        pvals.append(max(pb, 1.0 / 2001))
        results[(split, hid)] = dict(n=len(rows), mean=mu, ci=(lo, hi),
                                     p_boot=pb, p_perm=pp, h0=h0mu)
    passed = bh(pvals)
    print('BH q=0.05 pass: %s' % {h: p for h, p in zip(PRIMARIES, passed)})

# per-year stability for anything with n>0 (descriptive, frozen control)
print('\n#### per-year mean net_60 (gross), DEV+VAL years only')
for hid in PRIMARIES:
    line = '%-6s' % hid
    for y in ('2019', '2020', '2021', '2022', '2023', '2024'):
        rows = [p for p in probes if p['day'][:4] == y and p['day'] <= '2024-06-30'
                and member(hid, parents.get(p['pid']), p)]
        line += '  %s:%6s' % (y, ('%+.2f' % (sum(r['net'] for r in rows) / len(rows))) if rows else '  -  ')
    print(line)

# symmetry, DEV only
print('\n#### long/short split (DEV, gross mean net_60)')
for hid in PRIMARIES:
    for s, tag in ((1, 'long'), (-1, 'short')):
        rows = [p for p in probes if in_split(p['day'], 'DEV') and p['side'] == s
                and member(hid, parents.get(p['pid']), p)]
        if rows:
            print('  %-6s %-5s n=%5d  mean %+0.3f' % (hid, tag, len(rows),
                  sum(r['net'] for r in rows) / len(rows)))

# decay bins, DEV
print('\n#### entry-delay bins (DEV, gross mean net_60)')
BINS = [(1, 2), (3, 5), (6, 15), (16, 60)]
for hid in PRIMARIES:
    line = '  %-6s' % hid
    for a, b in BINS:
        rows = [p for p in probes if in_split(p['day'], 'DEV') and a <= p['delay'] <= b
                and member(hid, parents.get(p['pid']), p)]
        line += '  %d-%dm:%7s' % (a, b, ('%+.2f' % (sum(r['net'] for r in rows) / len(rows))) if rows else '  -  ')
    print(line)
