#!/usr/bin/env python3
# AUTOPSY - why the best five lose, and whether ANY management change
# repairs them. Asked directly by the user: better stop? better R:R?
# hold longer? confluences?
#
# Method notes (honest about approximation):
#  - Loss anatomy uses favourable/adverse excursion IN THE TRADED
#    DIRECTION (a fade's favourable excursion is the event's MAE).
#  - Breakeven and partial sims need ORDER, which OHLC cannot give
#    exactly. y_minsToMaxMfe / y_minsToMaxMae are used as the ordering
#    proxy: the +1R is treated as reachable-first only when the
#    favourable extreme timestamp precedes the adverse one. This is an
#    APPROXIMATION and is labelled as such wherever it is reported.
#  - Stop = 1.5 x ATR throughout (the stop-family study's pick), so no
#    stop is selected per-hypothesis after seeing results.
#
# HOLD (2024-07 onward) NOT read.

import csv, glob, os, random
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
COST = 0.87
STOP_MULT = 1.5
random.seed(41)

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
            if row[i['f_eventKind']] not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            n60 = F(row[i['y_net_60m']]); n240 = F(row[i['y_net_240m']])
            if n60 is None or n240 is None: continue
            et = row[i['f_barCloseEt']]
            E.append({'day': et[:10], 'yr': et[:4], 'hhmm': et[11:16],
                      'kind': row[i['f_eventKind']], 'side': int(row[i['f_side']]),
                      'atr': F(row[i['f_atr']]) or 0.0,
                      'n60': n60, 'n240': n240,
                      'mfeP': F(row[i['y_maxMfePts']]) or 0.0,
                      'maeP': F(row[i['y_maxMaePts']]) or 0.0,
                      'tMfe': F(row[i['y_minsToMaxMfe']]) or 999,
                      'tMae': F(row[i['y_minsToMaxMae']]) or 999,
                      'swHi': row[i['f_swingHighLabel']], 'swLo': row[i['f_swingLowLabel']],
                      'pushN': F(row[i['f_vectorPushCount']]) or 0,
                      'pushDir': row[i['f_vectorPushDirection']],
                      'pushPoor': row[i['f_vectorPushPoorProgress']] == 'TRUE',
                      'ft': row[i['f_formationType']],
                      'fbrk': row[i['f_formationBreakConfirmed']] == 'TRUE',
                      'fret': row[i['f_formationRetestConfirmed']] == 'TRUE',
                      'finv': row[i['f_formationInvalidated']] == 'TRUE',
                      's4h': row[i['f_struct_4h']], 's15': row[i['f_struct_15m']],
                      'fan': row[i['f_emaFanState_15m']],
                      'inter': row[i['f_interaction']],
                      'tests': F(row[i['f_levelInteractionCountSession']]) or 0,
                      'relvol': F(row[i['f_relVolume']]) or 1.0})

def sp(d): return 'DEV' if d <= '2022-12-31' else 'VAL'

firstmorn = {}
for j in sorted(range(len(E)), key=lambda k: (E[k]['day'], E[k]['hhmm'])):
    e = E[j]
    if '09:30' <= e['hhmm'] <= '10:30' and e['day'] not in firstmorn:
        firstmorn[e['day']] = j

def mdir(n, j):
    e = E[j]; s = e['side']
    if n == 'N7': return -1 if firstmorn.get(e['day']) == j else 0
    if n == 'N2':
        if not (e['pushPoor'] and e['pushN'] >= 3): return 0
        pd = 1 if e['pushDir'] == 'BULLISH' else (-1 if e['pushDir'] == 'BEARISH' else 0)
        return -1 if (pd and pd == s) else 0
    if n == 'N6':
        if e['finv'] or not (e['fbrk'] and e['fret']): return 0
        want = 1 if e['ft'] == 'W' else (-1 if e['ft'] == 'M' else 0)
        return +1 if want == s else 0
    if n == 'N12':
        if e['fan'] == 'BULLISH' and e['kind'] == 'BREAK_HIGH': return +1
        if e['fan'] == 'BEARISH' and e['kind'] == 'BREAK_LOW': return +1
        return 0
    if n == 'N9': return -1 if e['s4h'] in ('RANGE_CONTRACTING', 'RANGE_EXPANDING') else 0
    return 0

TOP = ['N7', 'N2', 'N6', 'N12', 'N9']
MEMB = {n: [(j, mdir(n, j)) for j in range(len(E)) if mdir(n, j) != 0] for n in TOP}

def trade(j, d, H):
    """(final_net_after_cost, favourable_pts, adverse_pts, stop_pts, fav_first)"""
    e = E[j]; S = STOP_MULT * e['atr']
    fav = e['mfeP'] if d > 0 else e['maeP']
    adv = e['maeP'] if d > 0 else e['mfeP']
    favfirst = (e['tMfe'] < e['tMae']) if d > 0 else (e['tMae'] < e['tMfe'])
    raw = d * (e['n60'] if H == 60 else e['n240'])
    if S > 0 and adv >= S: raw = -S
    return raw - COST, fav, adv, S, favfirst

print('=' * 100)
print('AUTOPSY OF THE TOP 5   (stop 1.5xATR fixed, cost %.2f pt)' % COST)
print('=' * 100)

for n in TOP:
    rows = MEMB[n]
    print('\n#### %s   n=%d' % (n, len(rows)))
    for H in (60, 240):
        for split in ('DEV', 'VAL'):
            sel = [(j, d) for j, d in rows if sp(E[j]['day']) == split]
            if not sel: continue
            outs = [trade(j, d, H) for j, d in sel]
            net = [o[0] for o in outs]
            losers = [o for o in outs if o[0] < 0]
            wins = [o for o in outs if o[0] > 0]
            never = sum(1 for o in losers if o[1] < 0.5 * o[3])
            gave = sum(1 for o in losers if o[1] >= 1.0 * o[3])
            mid = len(losers) - never - gave
            # MFE capture on winners
            cap = [o[0] / o[1] for o in wins if o[1] > 0]
            cap.sort()
            print('  H=%3dm %s  mean %+6.2f  win%% %4.1f  | LOSERS n=%4d: never-worked %4.1f%%  '
                  'gave-back-1R %4.1f%%  middling %4.1f%%  | winner MFE capture med %4.1f%%'
                  % (H, split, sum(net) / len(net), 100.0 * len(wins) / len(net), len(losers),
                     100.0 * never / max(len(losers), 1), 100.0 * gave / max(len(losers), 1),
                     100.0 * mid / max(len(losers), 1),
                     100.0 * cap[len(cap) // 2] if cap else 0))

print('\n' + '=' * 100)
print('DOES ANY MANAGEMENT CHANGE REPAIR THEM?   (H=240m; BE/partial use the')
print('timestamp ordering proxy and are APPROXIMATE - flagged, not hidden)')
print('=' * 100)
print('%-5s %-22s %9s %9s' % ('id', 'management', 'DEV', 'VAL'))
for n in TOP:
    rows = MEMB[n]
    variants = {}
    for tag in ('plain 1.5R stop', 'breakeven after +1R', 'partial 50% @1R + runner',
                'trail: exit at +1R', 'no stop at all'):
        for split in ('DEV', 'VAL'):
            sel = [(j, d) for j, d in rows if sp(E[j]['day']) == split]
            acc = []
            for j, d in sel:
                e = E[j]; S = STOP_MULT * e['atr']
                fav = e['mfeP'] if d > 0 else e['maeP']
                adv = e['maeP'] if d > 0 else e['mfeP']
                favfirst = (e['tMfe'] < e['tMae']) if d > 0 else (e['tMae'] < e['tMfe'])
                raw = d * e['n240']
                stopped = S > 0 and adv >= S
                if tag == 'plain 1.5R stop':
                    v = -S if stopped else raw
                elif tag == 'no stop at all':
                    v = raw
                elif tag == 'breakeven after +1R':
                    if fav >= S and favfirst: v = 0.0            # BE saves it
                    elif stopped: v = -S
                    else: v = raw
                elif tag == 'trail: exit at +1R':
                    if fav >= S and favfirst: v = S
                    elif stopped: v = -S
                    else: v = raw
                else:  # partial 50% at 1R then runner to horizon
                    if fav >= S and favfirst:
                        run = -S if stopped else raw
                        v = 0.5 * S + 0.5 * run
                    elif stopped: v = -S
                    else: v = raw
                acc.append(v - COST)
            variants[(tag, split)] = sum(acc) / len(acc) if acc else float('nan')
    for tag in ('plain 1.5R stop', 'breakeven after +1R', 'partial 50% @1R + runner',
                'trail: exit at +1R', 'no stop at all'):
        print('%-5s %-22s %+9.3f %+9.3f' % (n, tag, variants[(tag, 'DEV')], variants[(tag, 'VAL')]))

print('\n' + '=' * 100)
print('CONFLUENCE SCAN - 7 pre-declared conditions x 5 hypotheses (35 cells), H=240m')
print('=' * 100)
CONF = [
    ('RTH only', lambda e: '09:30' <= e['hhmm'] < '16:00'),
    ('overnight only', lambda e: not ('09:30' <= e['hhmm'] < '16:00')),
    ('high relVolume', lambda e: e['relvol'] >= 1.5),
    ('4H aligned w/ 15m', lambda e: e['s4h'] == e['s15']),
    ('at a level', lambda e: e['inter'] != 'NO_INTERACTION'),
    ('first test today', lambda e: e['tests'] <= 1),
    ('long side only', lambda e: e['side'] == 1),
]
hits = []
print('%-5s %-20s %6s %9s %9s %s' % ('id', 'confluence', 'nDEV', 'DEV', 'VAL', 'both+?'))
for n in TOP:
    for tag, fn in CONF:
        res = {}
        for split in ('DEV', 'VAL'):
            sel = [(j, d) for j, d in MEMB[n] if sp(E[j]['day']) == split and fn(E[j])]
            if len(sel) < 50: res[split] = None; continue
            acc = [trade(j, d, 240)[0] for j, d in sel]
            res[split] = (len(acc), sum(acc) / len(acc))
        if res['DEV'] is None or res['VAL'] is None: continue
        both = res['DEV'][1] > 0 and res['VAL'][1] > 0
        if both: hits.append((n, tag, res['DEV'][1], res['VAL'][1]))
        print('%-5s %-20s %6d %+9.3f %+9.3f %s' % (n, tag, res['DEV'][0], res['DEV'][1],
                                                   res['VAL'][1], 'YES' if both else ''))
print('\ncells positive in BOTH splits: %d of ~35' % len(hits))
for h in hits: print('   %s + %s : DEV %+0.3f  VAL %+0.3f' % h)

# noise floor for the confluence scan
print('\n#### NOISE FLOOR for this 35-cell confluence scan (100 within-day shuffles)')
byday = defaultdict(list)
for j, e in enumerate(E): byday[e['day']].append(j)
o60 = [e['n60'] for e in E]; o240 = [e['n240'] for e in E]
omfe = [e['mfeP'] for e in E]; omae = [e['maeP'] for e in E]
cnt = []
for _ in range(100):
    for _, idxs in byday.items():
        perm = idxs[:]; random.shuffle(perm)
        vals = [(o60[k], o240[k], omfe[k], omae[k]) for k in perm]
        for j, v in zip(idxs, vals):
            E[j]['n60'], E[j]['n240'], E[j]['mfeP'], E[j]['maeP'] = v
    c = 0
    for n in TOP:
        for tag, fn in CONF:
            ok = True; vals2 = {}
            for split in ('DEV', 'VAL'):
                sel = [(j, d) for j, d in MEMB[n] if sp(E[j]['day']) == split and fn(E[j])]
                if len(sel) < 50: ok = False; break
                acc = [trade(j, d, 240)[0] for j, d in sel]
                vals2[split] = sum(acc) / len(acc)
            if ok and vals2['DEV'] > 0 and vals2['VAL'] > 0: c += 1
    cnt.append(c)
for j in range(len(E)):
    E[j]['n60'], E[j]['n240'], E[j]['mfeP'], E[j]['maeP'] = o60[j], o240[j], omfe[j], omae[j]
cnt.sort()
print('  cells passing "positive in both splits" on SHUFFLED data:')
print('    median %d   p90 %d   max %d   (real data: %d)'
      % (cnt[50], cnt[90], cnt[-1], len(hits)))
