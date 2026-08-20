#!/usr/bin/env python3
# STOP FAMILY RE-TEST - Class D. Entry definitions are UNCHANGED and
# frozen; only the stop varies.
#
# Method is exact, not approximated: with a STOP + TIME EXIT there is no
# stop-vs-target race, so a stop of size S is hit within the horizon iff
# y_mae_60m >= S. The capture records max adverse excursion at each
# horizon, so every stop below can be resolved without ordering
# assumptions and without the AMBIGUOUS problem.
#
# Stop families (distance from entry, in points):
#   NONE        no stop at all - pure 60m time exit (the drift baseline)
#   CANDLE_1M   1m entry candle low/high +/- 1 tick  ("end of the candle")
#   CANDLE_15M  parent 15m event candle low/high     (the wide reading)
#   C15+0.25A   parent 15m candle + 0.25 ATR buffer
#   ATR_1.0 / ATR_1.5 / ATR_2.0     volatility-scaled
#   STRUCTURAL  beyond the parent thesis swing
#
# Metric is NET POINTS per trade after cost. R is NOT comparable across
# stop families (the unit itself changes), so points is the only honest
# common denominator; R is shown beside it for reference only.
#
# Structure OOS/LOCKBOX (2024-07 onward) NOT READ.

import csv, glob, os
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
COST = 0.87
SPL = [('DEV', '2019-07-01', '2022-12-31'), ('VAL', '2023-01-01', '2024-06-30')]

def F(v):
    try: return float(v)
    except: return None

par = {}
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    if f[-11:-4] > '2024-06': continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            pid = row[i['parentEventId']]; et = row[i['f_barCloseEt']]
            if pid in par and par[pid]['et'] <= et: continue
            par[pid] = {'et': et, 'hyp': row[i['hypothesisId']],
                        'hi': F(row[i['f_high']]), 'lo': F(row[i['f_low']]),
                        'atr': F(row[i['f_atr']]) or 0.0,
                        'isv': row[i['f_isVector_15m']] == 'TRUE',
                        'wick': row[i['f_vectorWickedBeyond_15m']] == 'TRUE',
                        'inter': row[i['f_interaction']],
                        's15': row[i['f_struct_15m']],
                        'form': row[i['f_formationType']],
                        'leg2': row[i['f_formationSecondLegConfirmed']] == 'TRUE',
                        'finv': row[i['f_formationInvalidated']] == 'TRUE',
                        'col': row[i['f_vectorColor_15m']],
                        'fex': row[i['f_vectorExitsFormation']] == 'TRUE',
                        'fbr': row[i['f_formationBreakConfirmed']] == 'TRUE',
                        'e8': row[i['f_ema800Ready_15m']] == 'TRUE'}

T = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_entries_MNQ_v41_*.csv'))):
    if f[-11:-4] > '2024-06': continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isWarmup']] == 'TRUE': continue
            p = par.get(row[i['parentEventId']])
            if p is None or not p['e8']: continue
            ep = F(row[i['f_entryPrice']]); mae = F(row[i['y_mae_60m']])
            net = F(row[i['y_net_60m']])
            if ep is None or mae is None or net is None: continue
            side = int(row[i['f_side']])
            st = F(row[i['f_stopTightPrice']]); ss = F(row[i['f_stopStructuralPrice']])
            c1 = abs(ep - st) if st else None
            c15 = (ep - p['lo']) if side > 0 else (p['hi'] - ep)
            sstr = abs(ep - ss) if ss else None
            T.append({'day': row[i['f_eventEt']][:10], 'arch': row[i['f_architecture']],
                      'side': side, 'net': net, 'mae': mae, 'atr': p['atr'],
                      'pid': row[i['parentEventId']], 'p': p,
                      'c1': c1, 'c15': c15 if c15 and c15 > 0 else None, 'sstr': sstr})

def stops(t):
    a = t['atr']
    return [('NONE', None), ('CANDLE_1M', t['c1']), ('CANDLE_15M', t['c15']),
            ('C15+0.25A', (t['c15'] + 0.25 * a) if t['c15'] else None),
            ('ATR_1.0', a if a > 0 else None), ('ATR_1.5', 1.5 * a if a > 0 else None),
            ('ATR_2.0', 2.0 * a if a > 0 else None), ('STRUCTURAL', t['sstr'])]

def member(hid, t):
    p = t['p']
    if hid == 'ALL-BREAKS': return True
    if hid == 'H1': return t['arch'] == 'ARCH-C' and p['hyp'] == 'H1-VECTOR-SWEEP-REVERSAL'
    if hid == 'H2': return t['arch'] == 'ARCH-B' and p['hyp'] == 'H2-VECTOR-BREAK-CONTINUATION'
    if hid == 'H3': return t['arch'] == 'ARCH-A' and p['isv'] and p['wick']
    if hid == 'H4': return t['arch'] == 'ARCH-B' and p['isv'] and p['inter'] != 'NO_INTERACTION'
    if hid == 'H5': return t['arch'] == 'ARCH-B' and p['s15'] in ('BULLISH', 'BEARISH')
    if hid == 'TRH1': return (t['arch'] == 'ARCH-B' and t['side'] == 1 and p['form'] == 'W'
                              and p['leg2'] and not p['finv'] and p['col'] in ('GREEN', 'BLUE')
                              and (p['fex'] or p['fbr']))
    if hid == 'TRH2': return (t['arch'] == 'ARCH-B' and t['side'] == -1 and p['form'] == 'M'
                              and p['leg2'] and not p['finv'] and p['col'] in ('RED', 'VIOLET')
                              and (p['fex'] or p['fbr']))
    return False

HYPS = ['ALL-BREAKS', 'H1', 'H2', 'H3', 'H4', 'H5', 'TRH1', 'TRH2']
NAMES = [n for n, _ in stops(T[0])]

print('=' * 108)
print('STOP FAMILY RE-TEST  -  net POINTS per trade after %.2f pt cost, 60m time exit' % COST)
print('entries frozen and unchanged; only the stop varies. OOS/LOCKBOX not read.')
print('=' * 108)

for hid in HYPS:
    print('\n#### %s' % hid)
    print('  %-11s | %7s %8s %8s | %7s %8s %8s' % (
        'stop', 'n_DEV', 'netPt', 'stopped', 'n_VAL', 'netPt', 'stopped'))
    for si, sname in enumerate(NAMES):
        cells = []
        for tag, a, b in SPL:
            rows = [t for t in T if a <= t['day'] <= b and member(hid, t)]
            vals = []; hit = 0
            for t in rows:
                S = stops(t)[si][1]
                if sname != 'NONE' and (S is None or S <= 0): continue
                if sname == 'NONE':
                    o = t['net']
                elif t['mae'] >= S:
                    o = -S; hit += 1
                else:
                    o = t['net']
                vals.append(o - COST)
            cells.append((len(vals), (sum(vals) / len(vals)) if vals else float('nan'),
                          (100.0 * hit / len(vals)) if vals else float('nan')))
        (n1, m1, h1), (n2, m2, h2) = cells
        if n1 < 30: continue
        print('  %-11s | %7d %+8.3f %7.1f%% | %7d %+8.3f %7.1f%%' % (
            sname, n1, m1, h1, n2, m2, h2))

print('\n\n#### mean stop distance by family (points, DEV+VAL, ALL-BREAKS)')
for si, sname in enumerate(NAMES):
    if sname == 'NONE': continue
    v = [stops(t)[si][1] for t in T if stops(t)[si][1] and stops(t)[si][1] > 0]
    if v:
        v.sort()
        print('  %-11s n=%6d  mean %7.2f  median %7.2f  ($%.0f per MNQ contract at median)'
              % (sname, len(v), sum(v) / len(v), v[len(v) // 2], 2 * v[len(v) // 2]))
