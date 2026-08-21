#!/usr/bin/env python3
# SUPPLEMENT: does the order-flow magnitude score actually IMPROVE a
# take-profit rule when used to SIZE the target?
#
# The Q1 score (of_targets.py) predicts how far the next 90 minutes
# reach, rho ~ +0.23/+0.26. If that is usable, then on the SAME
# direction-agnostic entries with the SAME 1.5 ATR stop:
#     ADAPTIVE target  = small target when score is low,
#                        large target when score is high
# must capture more of the available MFE, and lose less net, than every
# FIXED target. Tercile cuts and score construction frozen on DEV.
#
# NOTE direction stays unpredictable - nothing here is expected to be
# net positive. The deliverable is the CAPTURE comparison.

import csv, glob, os, pickle, random
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
CACHE = os.path.join(SCR, 'of_bars.pkl')
COST = 0.87
HORIZON = 90
STOP_ATR = 1.5
DEV_END = '2026-03-31'
random.seed(41)

with open(CACHE, 'rb') as fh:
    B = pickle.load(fh)

EV = []
n = len(B)
for i in range(n - HORIZON - 1):
    b = B[i]
    if not b['isRth'] or not b['profileReady']:
        continue
    if b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < 30:
        continue
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
        continue
    if b['tmin'] % 5 != 0 or b['atr'] <= 0:
        continue
    if B[i + HORIZON]['tmin'] - b['tmin'] != HORIZON:
        continue
    EV.append(i)

# the score: the strongest replicated ADDS features from Q1, equal weight.
# signs fixed from Q1 DEV: wide value area, wide delta range, high POC
# distance -> MORE reach; absorption, imbalance count, vol/tick -> LESS.
SC = [('valueWidthAtr', +1), ('deltaRange', +1), ('absDistPocAtr', +1),
      ('absorptionStrengthRaw', -1), ('imbal3x', -1), ('volPerTick', -1)]


def raw(b):
    d = {}
    if b['profileVah'] is None or b['profileVal'] is None:
        return None
    d['valueWidthAtr'] = (b['profileVah'] - b['profileVal']) / b['atr']
    if b['ofMaxDelta'] is None or b['ofMinDelta'] is None or not b['ofTotalVolume']:
        return None
    d['deltaRange'] = (b['ofMaxDelta'] - b['ofMinDelta']) / max(b['ofTotalVolume'], 1.0)
    if b['distPocAtr'] is None:
        return None
    d['absDistPocAtr'] = abs(b['distPocAtr'])
    d['absorptionStrengthRaw'] = b['absorptionStrengthRaw']
    ib, isl = b['buyImbalanceCount_3x'], b['sellImbalanceCount_3x']
    if ib is None or isl is None:
        return None
    d['imbal3x'] = ib + isl
    u, dn = b['volumePerUpTick'], b['volumePerDownTick']
    if u is None or dn is None:
        return None
    d['volPerTick'] = (u + dn) / 2.0
    if any(v is None for v in d.values()):
        return None
    return d


ROWS = []
for i in EV:
    d = raw(B[i])
    if d is None:
        continue
    d['i'] = i
    d['day'] = B[i]['day']
    ROWS.append(d)

DEVR = [r for r in ROWS if r['day'] <= DEV_END]
ref = {k: sorted(r[k] for r in DEVR) for k, _ in SC}


def pct(srt, v):
    lo, hi = 0, len(srt)
    while lo < hi:
        mid = (lo + hi) // 2
        if srt[mid] < v:
            lo = mid + 1
        else:
            hi = mid
    return lo / max(len(srt) - 1, 1)


for r in ROWS:
    r['score'] = sum(s * pct(ref[k], r[k]) for k, s in SC) / len(SC)

sc_dev = sorted(r['score'] for r in DEVR)
t1 = sc_dev[len(sc_dev) // 3]
t2 = sc_dev[2 * len(sc_dev) // 3]
print('events scored: %d DEV / %d VAL   tercile cuts (DEV-frozen) %.3f / %.3f'
      % (len(DEVR), len(ROWS) - len(DEVR), t1, t2))


def race(i, side, stop_px, target_px):
    e = B[i]['close']
    for k in range(1, HORIZON + 1):
        c = B[i + k]
        if side > 0:
            if c['low'] <= stop_px:
                return (stop_px - e) * side
            if target_px is not None and c['high'] >= target_px:
                return (target_px - e) * side
        else:
            if c['high'] >= stop_px:
                return (stop_px - e) * side
            if target_px is not None and c['low'] <= target_px:
                return (target_px - e) * side
    return (B[i + HORIZON]['close'] - e) * side


def mfe(i, side):
    e = B[i]['close']
    if side > 0:
        return max(B[i + k]['high'] for k in range(1, HORIZON + 1)) - e
    return e - min(B[i + k]['low'] for k in range(1, HORIZON + 1))


# adaptive rule, frozen here: low tercile 0.5R, mid 1.0R, high 2.0R
def adaptive_mult(score):
    return 0.5 if score <= t1 else (2.0 if score > t2 else 1.0)


RULES = ['fixed_0.5R', 'fixed_1.0R', 'fixed_1.5R', 'fixed_2.0R',
         'ADAPTIVE', 'ADAPTIVE_inverted']
net = defaultdict(lambda: defaultdict(list))
cap = defaultdict(lambda: defaultdict(list))
hit = defaultdict(lambda: defaultdict(lambda: [0, 0]))
for r in ROWS:
    i = r['i']
    b = B[i]
    sp = 'DEV' if r['day'] <= DEV_END else 'VAL'
    a = b['atr']
    e = b['close']
    S = STOP_ATR * a
    for side in (+1, -1):
        stop_px = e - side * S
        m = mfe(i, side)
        for rule in RULES:
            if rule.startswith('fixed'):
                mult = float(rule.split('_')[1][:-1])
            elif rule == 'ADAPTIVE':
                mult = adaptive_mult(r['score'])
            else:
                mult = adaptive_mult(-r['score'])   # sanity: must be worse
            t = e + side * mult * S
            v = race(i, side, stop_px, t)
            net[rule][sp].append(v - COST)
            if m > 0:
                cap[rule][sp].append(max(v, 0.0) / m)
            h = hit[rule][sp]
            h[1] += 1
            if v >= mult * S - 1e-9:
                h[0] += 1

print('\n%-20s %9s %9s %9s %9s %9s %9s'
      % ('target rule', 'net DEV', 'net VAL', 'capt DEV', 'capt VAL', 'hit% D', 'hit% V'))
for rule in RULES:
    nd, nv = net[rule]['DEV'], net[rule]['VAL']
    cd, cv = cap[rule]['DEV'], cap[rule]['VAL']
    hd, hv = hit[rule]['DEV'], hit[rule]['VAL']
    print('%-20s %+9.3f %+9.3f %9.3f %9.3f %9.1f %9.1f'
          % (rule, sum(nd) / len(nd), sum(nv) / len(nv),
             sum(cd) / len(cd), sum(cv) / len(cv),
             100.0 * hd[0] / hd[1], 100.0 * hv[0] / hv[1]))

# day-block bootstrap on ADAPTIVE minus best fixed (per split)
for sp in ('DEV', 'VAL'):
    fixed_best = max(('fixed_0.5R', 'fixed_1.0R', 'fixed_1.5R', 'fixed_2.0R'),
                     key=lambda rl: sum(net[rl][sp]) / len(net[rl][sp]))
    byday = defaultdict(list)
    k = 0
    for r in ROWS:
        if ('DEV' if r['day'] <= DEV_END else 'VAL') != sp:
            continue
        for _ in (0, 1):
            byday[r['day']].append(net['ADAPTIVE'][sp][k] - net[fixed_best][sp][k])
            k += 1
    days = list(byday.values())
    diffs = [x for dd in days for x in dd]
    mu = sum(diffs) / len(diffs)
    boot = []
    for _ in range(2000):
        s = [x for dd in random.choices(days, k=len(days)) for x in dd]
        boot.append(sum(s) / len(s))
    boot.sort()
    print('\n%s: ADAPTIVE minus best fixed (%s): %+0.3f pt/trade  95%% CI [%+0.3f, %+0.3f]'
          % (sp, fixed_best, mu, boot[50], boot[1949]))
