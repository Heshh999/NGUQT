#!/usr/bin/env python3
# OF-H SERIES part 2 - three jobs:
#  1. DIAGNOSE the three hypotheses that never fired (OFH8/10/11). A
#     declared hypothesis with n=0 is a defect in the declaration or the
#     data and gets explained, not skipped.
#  2. OFH6 (cum-delta trend go) deep dive: months, sides, outlier
#     sensitivity - the decile-1 lesson says a mean carried by 5% of
#     trades is a lottery ticket, not an edge.
#  3. A cheap but correct FAMILY-LEVEL noise floor: for each within-day
#     shuffle, take max over the 12 hypotheses of min(muDEV, muVAL) -
#     the "picked the family best and required both splits positive"
#     statistic - and place the real OFH6 value in that distribution.

import pickle, random
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
CACHE = SCR + '/of_bars2.pkl'
COST = 0.87
HORIZON = 90
COOLDOWN = 30
DEV_END = '2026-03-31'
random.seed(41)

with open(CACHE, 'rb') as fh:
    B = pickle.load(fh)
n = len(B)

for j in range(n):
    if j >= 15 and B[j]['tmin'] - B[j - 15]['tmin'] == 15:
        s = 0.0
        bad = False
        for k in range(j - 14, j + 1):
            v = B[k]['ofBarDelta']
            if v is None:
                bad = True
                break
            s += v
        B[j]['dsum15'] = None if bad else s
    else:
        B[j]['dsum15'] = None

ELIG = []
for j in range(n - HORIZON - 1):
    b = B[j]
    if not b['isRth']:
        continue
    if b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < 30:
        continue
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
        continue
    if b['atr'] is None or b['atr'] <= 0:
        continue
    if B[j + HORIZON]['tmin'] - b['tmin'] != HORIZON:
        continue
    ELIG.append(j)

# ------------------------------------------------ 1. the silent three
print('=' * 100)
print('1.  WHY OFH8 / OFH10 / OFH11 NEVER FIRED')
print('=' * 100)
pi = defaultdict(int)
for j in ELIG:
    pi[B[j]['pi']] += 1
print('  profileInteraction value counts over the %d eligible RTH bars:' % len(ELIG))
for k, v in sorted(pi.items(), key=lambda kv: -kv[1]):
    print('    %-22s %7d' % (k, v))
c60 = sum(1 for j in ELIG if B[j]['ofDeltaPct'] is not None and abs(B[j]['ofDeltaPct']) >= 60)
c2 = sum(1 for j in ELIG if B[j]['relVolume'] is not None and B[j]['relVolume'] >= 2)
cb = sum(1 for j in ELIG if B[j]['ofDeltaPct'] is not None and B[j]['relVolume'] is not None
         and abs(B[j]['ofDeltaPct']) >= 60 and B[j]['relVolume'] >= 2)
print('  OFH11 components: |deltaPct|>=60 on %d bars, relVol>=2 on %d bars, BOTH on %d bars'
      % (c60, c2, cb))

# ------------------------------------------------ shared membership
DSUM_P90 = sorted(abs(B[j]['dsum15']) for j in ELIG
                  if B[j]['day'] <= DEV_END and B[j]['dsum15'] is not None)
DSUM_P90 = DSUM_P90[int(len(DSUM_P90) * 0.9)]
REP_P90 = sorted(B[j]['repeatedTradeAtExtreme'] for j in ELIG
                 if B[j]['day'] <= DEV_END and B[j]['repeatedTradeAtExtreme'] is not None)
REP_P90 = REP_P90[int(len(REP_P90) * 0.9)]


def sig(name, b):
    if name == 'OFH1':
        if b['bearishDeltaDivergenceCandidate']:
            return -1
        if b['bullishDeltaDivergenceCandidate']:
            return +1
        return 0
    if name == 'OFH2':
        if b['deltaConfirmsBreak'] and b['priceNewHigh']:
            return +1
        if b['deltaConfirmsBreak'] and b['priceNewLow']:
            return -1
        return 0
    if name == 'OFH3':
        if b['absorptionBuyCandidate']:
            return -1
        if b['absorptionSellCandidate']:
            return +1
        return 0
    if name == 'OFH4':
        sb, ss, bd = b['stackedBuyLevels_3x'], b['stackedSellLevels_3x'], b['ofBarDelta']
        if sb is None or ss is None or bd is None:
            return 0
        if sb >= 2 and ss == 0 and bd > 0:
            return +1
        if ss >= 2 and sb == 0 and bd < 0:
            return -1
        return 0
    if name == 'OFH5':
        mb, ms = b['maxBuyImbalanceRatio'], b['maxSellImbalanceRatio']
        if mb is not None and mb >= 4 and b['buyImbalanceNearHigh'] and b['priceNewHigh']:
            return -1
        if ms is not None and ms >= 4 and b['sellImbalanceNearLow'] and b['priceNewLow']:
            return +1
        return 0
    if name == 'OFH6':
        v = b['dsum15']
        if v is None or abs(v) < DSUM_P90:
            return 0
        return +1 if v > 0 else -1
    if name == 'OFH7':
        bd = b['ofBarDelta']
        if bd is None or b['bodyPctOfRange'] is None or b['bodyPctOfRange'] < 25:
            return 0
        up = b['close'] > b['open']
        if up and bd < 0:
            return +1
        if (not up) and bd > 0:
            return -1
        return 0
    if name == 'OFH9':
        d = b['distPocAtr']
        if d is None or not b['profileReady']:
            return 0
        if d >= 2:
            return -1
        if d <= -2:
            return +1
        return 0
    if name == 'OFH12':
        r = b['repeatedTradeAtExtreme']
        if r is None or r < REP_P90:
            return 0
        if b['priceNewHigh']:
            return -1
        if b['priceNewLow']:
            return +1
        return 0
    return 0


NAMES = ['OFH1', 'OFH2', 'OFH3', 'OFH4', 'OFH5', 'OFH6', 'OFH7', 'OFH9', 'OFH12']
MEMB = {}
for name in NAMES:
    lst = []
    last = -10 ** 9
    for j in ELIG:
        d = sig(name, B[j])
        if d == 0:
            continue
        if B[j]['tmin'] - last < COOLDOWN:
            continue
        last = B[j]['tmin']
        lst.append((j, d))
    MEMB[name] = lst


def net60(j, side):
    return (B[j + 60]['close'] - B[j]['close']) * side


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


# ------------------------------------------------ 2. OFH6 deep dive
print('\n' + '=' * 100)
print('2.  OFH6 (15-bar cum-delta trend, top DEV decile, follow) - ANATOMY')
print('=' * 100)
rows = [(j, d, net60(j, d) - COST) for j, d in MEMB['OFH6']]
for sp in ('DEV', 'VAL'):
    sub = [(j, d, v) for j, d, v in rows if split_of(B[j]['day']) == sp]
    vs = sorted(v for _, _, v in sub)
    mu = sum(vs) / len(vs)
    med = vs[len(vs) // 2]
    lon = [v for _, d, v in sub if d > 0]
    sho = [v for _, d, v in sub if d < 0]
    print('\n  %s  n=%d  mean %+0.2f  median %+0.2f  win%% %.1f' % (
        sp, len(vs), mu, med, 100.0 * sum(1 for v in vs if v > 0) / len(vs)))
    print('    long  n=%4d mean %+0.2f   short n=%4d mean %+0.2f'
          % (len(lon), sum(lon) / len(lon) if lon else float('nan'),
             len(sho), sum(sho) / len(sho) if sho else float('nan')))
    k5 = max(1, len(vs) // 20)
    print('    remove best 5%% (%d trades): mean %+0.2f    remove worst 5%%: mean %+0.2f'
          % (k5, sum(vs[:-k5]) / (len(vs) - k5), sum(vs[k5:]) / (len(vs) - k5)))
    bymon = defaultdict(list)
    for j, d, v in sub:
        bymon[B[j]['day'][:7]].append(v)
    print('    months: ' + '  '.join('%s %+0.2f(n=%d)' % (m, sum(v) / len(v), len(v))
                                     for m, v in sorted(bymon.items())))

# ------------------------------------------------ 3. family noise floor
print('\n' + '=' * 100)
print('3.  FAMILY NOISE FLOOR - max over 9 firing hypotheses of min(muDEV, muVAL), 500 shuffles')
print('=' * 100)
allidx = sorted(set(j for name in NAMES for j, _ in MEMB[name]))
byday_i = defaultdict(list)
for j in allidx:
    byday_i[B[j]['day']].append(j)
orig = {j: net60(j, +1) for j in allidx}
cur = dict(orig)


def fam_stat():
    bm = -9e9
    who = ''
    for name in NAMES:
        agg = {'DEV': [], 'VAL': []}
        for j, d in MEMB[name]:
            agg[split_of(B[j]['day'])].append(d * cur[j] - COST)
        if not agg['DEV'] or not agg['VAL']:
            continue
        m = min(sum(agg['DEV']) / len(agg['DEV']), sum(agg['VAL']) / len(agg['VAL']))
        if m > bm:
            bm = m
            who = name
    return bm, who


real, who = fam_stat()
print('  REAL: best min(DEV,VAL) = %+0.3f  (%s)' % (real, who))
NS = 500
dist = []
for it in range(NS):
    for _, idxs in byday_i.items():
        vals = [cur[j] for j in idxs]
        random.shuffle(vals)
        for j, v in zip(idxs, vals):
            cur[j] = v
    dist.append(fam_stat()[0])
for j, v in orig.items():
    cur[j] = v
dist.sort()
ge = sum(1 for x in dist if x >= real)
print('  NOISE: median %+0.3f  p90 %+0.3f  p95 %+0.3f  max %+0.3f'
      % (dist[NS // 2], dist[int(NS * .9)], dist[int(NS * .95)], dist[-1]))
print('  family-wise p(real vs noise) = %.3f  (%d of %d shuffles >= real)'
      % (ge / NS, ge, NS))
