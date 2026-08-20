#!/usr/bin/env python3
# $1,000 ACCOUNT FEASIBILITY - May, June, July 2026.
#
# LEDGER NOTE: June-July 2026 are inside OF-OOS. The user was shown the
# cost and chose on 2026-08-20 to open them as a P&L ILLUSTRATION.
# OF-OOS IS THEREFORE SPENT and must never again be described as
# untouched or used as confirmatory evidence for any rule.
#
# This is NOT a strategy backtest. No strategy survived validation, so
# there is nothing to trade. This computes what the measured stop
# distances mean for a $1,000 account, and shows May 2026 (already
# viewed in OF-VAL) as an illustration of the arithmetic.
#
# MNQ = $2.00 per index point per contract.

import csv, glob, os
from collections import defaultdict

SP = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
DOLLAR_PER_PT = 2.0
ACCT = 1000.0
COST_PT = 0.87                      # provisional round-turn, in points

def F(v):
    try: return float(v)
    except: return None

OF = {}
for f in sorted(glob.glob(os.path.join(SP, 'of1', 'v4_1_orderflow_MNQ_v41of_*.csv'))):
    if f[-11:-4] not in ('2026-05', '2026-06', '2026-07'): continue
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

def score(o, s):
    sc = 0
    if o['confirm']: sc += 1
    if (o['delta'] > 0) == (s > 0) and o['delta'] != 0: sc += 1
    if (o['sb3'] if s > 0 else o['ss3']) >= 3: sc += 1
    if o['relvol'] >= 1.5: sc += 1
    if (o['absB'] if s > 0 else o['absS']): sc -= 1
    if (o['divBear'] if s > 0 else o['divBull']): sc -= 1
    return sc

EV = []
for mf in ('2026-05', '2026-06', '2026-07'):
  with open(os.path.join(SP, 'full', 'v4_1_structure_MNQ_v41_%s.csv' % mf), newline='') as fh:
    r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
    RACE = [(0.5, 'y_race_0.5R'), (1.0, 'y_race_1R'), (1.5, 'y_race_1.5R'),
            (2.0, 'y_race_2R'), (3.0, 'y_race_3R')]
    for row in r:
        if len(row) != len(h): continue
        if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
        if row[i['f_eventKind']] not in ('BREAK_HIGH', 'BREAK_LOW'): continue
        et = row[i['f_barCloseEt']]; o = OF.get(et)
        if o is None: continue
        mfeP, mfeR = F(row[i['y_maxMfePts']]), F(row[i['y_maxMfeR']])
        net = F(row[i['y_net_60m']])
        if not mfeP or not mfeR or net is None: continue
        side = int(row[i['f_side']])
        EV.append({'et': et, 'day': et[:10], 'side': side, 'net': net,
                   'stop': mfeP / mfeR, 'grade': score(o, side),
                   'races': {m: row[i[c]] for m, c in RACE},
                   'net240': F(row[i['y_net_240m']]) or 0.0})

print('=' * 88)
print('$1,000 ACCOUNT FEASIBILITY - MNQ at $%.2f/point' % DOLLAR_PER_PT)
print('Data: May-July 2026.  June-July are OF-OOS, opened by user decision.')
print('=' * 88)

allev = EV
aplus = [e for e in EV if e['grade'] >= 3]
print('\nMay-Jul 2026 break events with order-flow join: %d   of which A+ : %d' % (len(allev), len(aplus)))

print('\n### 1. STOP SIZE vs A $1,000 ACCOUNT  (1 contract, the minimum)')
print('%-22s %8s %9s %10s %12s' % ('population', 'n', 'medStop', 'stop $', '% of $1000'))
for tag, rows in (('all break events', allev), ('A+ graded only', aplus)):
    if not rows: continue
    st = sorted(e['stop'] for e in rows)
    med = st[len(st) // 2]; mean = sum(st) / len(st)
    print('%-22s %8d %8.1fpt %9.0f$ %11.1f%%' % (
        tag, len(rows), med, med * DOLLAR_PER_PT, 100 * med * DOLLAR_PER_PT / ACCT))
    print('%-22s %8s %8.1fpt %9.0f$ %11.1f%%   (mean)' % (
        '', '', mean, mean * DOLLAR_PER_PT, 100 * mean * DOLLAR_PER_PT / ACCT))
print('\n  Prudent risk per trade is 1-2%% of account = $%.0f-$%.0f = %.1f-%.1f MNQ points.'
      % (ACCT * .01, ACCT * .02, ACCT * .01 / DOLLAR_PER_PT, ACCT * .02 / DOLLAR_PER_PT))
print('  One contract at the median stop above already exceeds that by several times.')
print('  There is no fractional contract: 1 MNQ is the smallest position that exists.')

print('\n### 2. MAY-JUL 2026 P&L, 1 CONTRACT, FIXED-R EXITS (A+ events)')
print('%-8s %5s %5s %5s %6s %10s %10s %10s %9s' % (
    'target', 'n', 'W', 'L', 'win%', 'gross $', 'net $', 'maxDD $', 'end %acct'))
for m in (0.5, 1.0, 1.5, 2.0, 3.0):
    seq = []
    w = l = 0
    for e in sorted(aplus, key=lambda x: x['et']):
        o = e['races'][m]
        costD = COST_PT * DOLLAR_PER_PT
        if o == 'TARGET': pts = m * e['stop']; w += 1
        elif o == 'STOP': pts = -e['stop']; l += 1
        elif o == 'AMBIGUOUS': continue
        else: pts = e['net240']
        seq.append(pts * DOLLAR_PER_PT - costD)
    if not seq: continue
    gross = sum(seq) + len(seq) * COST_PT * DOLLAR_PER_PT
    net = sum(seq)
    peak = cum = dd = 0.0
    for x in seq:
        cum += x
        if cum > peak: peak = cum
        if peak - cum > dd: dd = peak - cum
    n = len(seq)
    print('%-8s %5d %5d %5d %5.1f%% %+10.0f %+10.0f %10.0f %8.1f%%' % (
        ('%gR' % m), n, w, l, 100.0 * w / n, gross, net, dd, 100 * (ACCT + net) / ACCT))

print('\n### 3. WHAT THE DRAWDOWN MEANS')
if aplus:
    st = sorted(e['stop'] for e in aplus)
    med = st[len(st) // 2]
    print('  1R at the median A+ stop = %.0f pt = $%.0f = %.1f%% of a $1,000 account.'
          % (med, med * DOLLAR_PER_PT, 100 * med * DOLLAR_PER_PT / ACCT))
    print('  The measured TR-H1 max drawdown at 2R was 23 R over DEV.')
    print('  23 R at this stop size = $%.0f  -> a $1,000 account is wiped out'
          % (23 * med * DOLLAR_PER_PT))
    print('  long before the sample completes, even if the edge were real.')
    nloss = 0
    run = best = 0
    for e in sorted(aplus, key=lambda x: x['et']):
        if e['races'][1.0] == 'STOP':
            run += 1; best = max(best, run)
        else: run = 0
    print('  Longest consecutive 1R-stop run: %d  = $%.0f = %.0f%% of account.'
          % (best, best * med * DOLLAR_PER_PT, 100 * best * med * DOLLAR_PER_PT / ACCT))

print('\n### 4. SEQUENTIAL ACCOUNT SIMULATION - $1,000, 1 contract, in trade order')
print('%-8s %6s %10s %10s %10s %8s %s' % ('target','trades','end equity','peak','trough','maxDD%','outcome'))
for m in (0.5, 1.0, 1.5, 2.0, 3.0):
    eq = ACCT; peak = ACCT; trough = ACCT; dd = 0.0; dead = None; k = 0
    for e in sorted(aplus, key=lambda x: x['et']):
        o = e['races'][m]
        if o == 'AMBIGUOUS': continue
        if o == 'TARGET': pts = m * e['stop']
        elif o == 'STOP': pts = -e['stop']
        else: pts = e['net240']
        eq += pts * DOLLAR_PER_PT - COST_PT * DOLLAR_PER_PT
        k += 1
        if eq > peak: peak = eq
        if eq < trough: trough = eq
        if peak - eq > dd: dd = peak - eq
        if eq <= 0 and dead is None: dead = k
    out = ('BLOWN UP at trade %d' % dead) if dead else 'survived'
    print('%-8s %6d %10.0f %10.0f %10.0f %7.0f%% %s' % (
        ('%gR' % m), k, eq, peak, trough, 100 * dd / peak if peak else 0, out))
print('\n  Per-month A+ counts:')
mc = {}
for e in aplus: mc[e['et'][:7]] = mc.get(e['et'][:7], 0) + 1
for k2 in sorted(mc): print('    %s  n=%d' % (k2, mc[k2]))
