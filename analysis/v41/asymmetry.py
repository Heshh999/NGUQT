#!/usr/bin/env python3
# EXCURSION ASYMMETRY SCAN - the direct answer to "what has good R:R?"
#
# Good risk-to-reward is not a target choice. It is a property of the
# event: does price travel further in your favour than against you,
# before either happens? That is medMFE_R vs medMAE_R. If MFE ~= MAE,
# no stop/target geometry can manufacture an edge - which is exactly
# what killed TR-H1.
#
# This scans every causal partition available on the 7-year structure
# capture and ranks by asymmetry. DEV 2019-07..2022-12 builds the list,
# VAL 2023-01..2024-06 checks it. Structure OOS/LOCKBOX (2024-07 ->)
# IS NOT READ.
#
# MULTIPLICITY: every cell scanned is counted and printed. This is a
# SCAN, not a confirmatory test. Nothing here is promoted.

import csv, glob, os
from collections import defaultdict

SP = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COST = 0.87
SPL = [('DEV', '2019-07-01', '2022-12-31'), ('VAL', '2023-01-01', '2024-06-30')]

def F(v):
    try: return float(v)
    except: return None

EV = []
for f in sorted(glob.glob(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_*.csv'))):
    if f[-11:-4] > '2024-06': continue          # HOLD not read
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            if row[i['f_eventKind']] not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            mfeR, maeR = F(row[i['y_maxMfeR']]), F(row[i['y_maxMaeR']])
            mp = F(row[i['y_maxMfePts']]); net = F(row[i['y_net_60m']])
            if not mfeR or maeR is None or not mp or net is None: continue
            et = row[i['f_barCloseEt']]; hhmm = et[11:16]
            EV.append({
                'day': et[:10], 'mfeR': mfeR, 'maeR': maeR,
                'netR': net / (mp / mfeR) - COST / (mp / mfeR),
                'kind': row[i['f_eventKind']],
                'inter': row[i['f_interaction']],
                'vcol': row[i['f_vectorColor_15m']],
                'form': row[i['f_formationType']],
                's4h': row[i['f_struct_4h']], 's15': row[i['f_struct_15m']],
                'tod': ('ASIA' if hhmm >= '18:00' or hhmm < '03:00'
                        else 'LONDON' if hhmm < '09:30'
                        else 'RTH_AM' if hhmm < '12:00' else 'RTH_PM'),
                'adr': ('adr_low' if (F(row[i['f_adrConsumedPct']]) or 0) < 50
                        else 'adr_mid' if (F(row[i['f_adrConsumedPct']]) or 0) < 100
                        else 'adr_high'),
                'align': 'aligned' if row[i['f_struct_4h']] == row[i['f_struct_15m']] else 'conflict',
            })

def med(z):
    z = sorted(z); return z[len(z) // 2] if z else float('nan')

FAMS = ['kind', 'inter', 'vcol', 'form', 's4h', 's15', 'tod', 'adr', 'align']
cells = 0
table = {}
for tag, a, b in SPL:
    rows = [e for e in EV if a <= e['day'] <= b]
    for fam in FAMS:
        vals = sorted(set(e[fam] for e in rows))
        for v in vals:
            sub = [e for e in rows if e[fam] == v]
            if len(sub) < 120: continue
            mf, ma = med([e['mfeR'] for e in sub]), med([e['maeR'] for e in sub])
            table[(tag, fam, v)] = (len(sub), mf, ma, mf / ma if ma else float('nan'),
                                    sum(e['netR'] for e in sub) / len(sub))
            if tag == 'DEV': cells += 1

print('=' * 104)
print('EXCURSION ASYMMETRY SCAN  -  medMFE_R / medMAE_R, ranked on DEV, checked on VAL')
print('cells scanned (n>=120): %d   |  structure OOS/LOCKBOX not read' % cells)
print('=' * 104)
print('%-8s %-22s %7s %7s %7s %8s %9s | %6s %7s %8s %9s' % (
    'family', 'cell', 'n_DEV', 'MFE_R', 'MAE_R', 'ratio', 'netR_DEV',
    'n_VAL', 'ratio', 'netR_VAL', 'ratio dif'))
rank = sorted([k for k in table if k[0] == 'DEV'],
              key=lambda k: -table[k][3])
for k in rank:
    _, fam, v = k
    n, mf, ma, ra, nr = table[k]
    vk = ('VAL', fam, v)
    if vk in table:
        n2, mf2, ma2, ra2, nr2 = table[vk]
        print('%-8s %-22s %7d %7.2f %7.2f %8.3f %+9.4f | %6d %7.3f %+8.4f %+9.3f' % (
            fam, v, n, mf, ma, ra, nr, n2, ra2, nr2, ra2 - ra))
    else:
        print('%-8s %-22s %7d %7.2f %7.2f %8.3f %+9.4f | %6s' % (fam, v, n, mf, ma, ra, nr, '-'))

print('\nPOOLED BASELINE')
for tag, a, b in SPL:
    rows = [e for e in EV if a <= e['day'] <= b]
    mf, ma = med([e['mfeR'] for e in rows]), med([e['maeR'] for e in rows])
    print('  %-4s n=%6d  medMFE %.3f R  medMAE %.3f R  ratio %.3f  netR %+0.4f' % (
        tag, len(rows), mf, ma, mf / ma, sum(e['netR'] for e in rows) / len(rows)))

print('\nHOW MANY CELLS CLEAR A USEFUL BAR?')
for thr in (1.10, 1.20, 1.30):
    both = [k for k in rank if ('VAL', k[1], k[2]) in table
            and table[k][3] >= thr and table[('VAL', k[1], k[2])][3] >= thr]
    pos = [k for k in both if table[k][4] > 0 and table[('VAL', k[1], k[2])][4] > 0]
    print('  ratio >= %.2f in BOTH splits: %d cells   of which net R > 0 in both: %d'
          % (thr, len(both), len(pos)))
    for k in pos: print('      %s / %s' % (k[1], k[2]))
