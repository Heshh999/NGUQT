#!/usr/bin/env python3
# TEN-MONTH PROTOCOL, CORRECTED. Two defects in power10.py are fixed here
# and both changed the answer.
#
# DEFECT 1 - the MDE table was wrong by roughly 6x.
#   I measured the day-clustering inflation on the FULL 53,914-bar
#   eligible set, where each session contributes ~260 heavily overlapping
#   observations, then applied that same x7.50 factor to trade sets of
#   ~800. A strategy taking ~4 trades a day has nothing like that overlap.
#   The measured day-block CI on the real OFH6 trade set already implied
#   SE ~3.8 pt at n=783, i.e. MDE ~11 pt - not the 68 pt I printed.
#   Fixed by measuring the SE EMPIRICALLY at each trade count, on trade
#   sets drawn the way a strategy actually draws them.
#
# DEFECT 2 - the within-day shuffle is the wrong null for this claim.
#   Permuting returns inside a day leaves the DAY'S OWN DIRECTION intact,
#   and then hands it to the null for free. A rule that is long on up-days
#   scores well under that null because the null already knows which days
#   were up-days. That is why the "noise" median came out at +11.6 - the
#   null was not null. It is future information leaking into the control.
#   The correct null for a DIRECTIONAL claim is a SIGN-FLIP: same bars,
#   same times, same trade count, direction randomised. Flipped by DAY, so
#   within-day correlation survives. Under it the expectation is exactly
#   zero by construction.
#
# Everything is measured as EXCESS over the side-matched, split-matched
# baseline, so window drift cannot pose as edge.
#
# SELECTION remains in force: OFH6 was chosen as best-of-twelve on this
# window. The family-wise number below is the honest one.

import pickle, random, math
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
CACHE = SCR + '/of_bars2.pkl'
COST = 0.87
HORIZON = 90
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
    if b['dsum15'] is None:
        continue
    ELIG.append(j)


def net60(j, side):
    return (B[j + 60]['close'] - B[j]['close']) * side


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


base = {}
for sp in ('DEV', 'VAL'):
    for side in (+1, -1):
        v = [net60(j, side) for j in ELIG if split_of(B[j]['day']) == sp]
        base[(sp, side)] = sum(v) / len(v)

DAYS = sorted(set(B[j]['day'] for j in ELIG))
MON = sorted(set(d[:7] for d in DAYS))
print('eligible bars %d   days %d   months %d  (%s .. %s)'
      % (len(ELIG), len(DAYS), len(MON), MON[0], MON[-1]))

dev_abs = sorted(abs(B[j]['dsum15']) for j in ELIG if B[j]['day'] <= DEV_END)


def q(p):
    return dev_abs[min(int(len(dev_abs) * p), len(dev_abs) - 1)]


def trades_at(pct, cooldown=30):
    thr = q(pct)
    out = []
    last = -10 ** 9
    for j in ELIG:
        v = B[j]['dsum15']
        if abs(v) < thr or B[j]['tmin'] - last < cooldown:
            continue
        last = B[j]['tmin']
        out.append((j, +1 if v > 0 else -1))
    return out


def excess(rows):
    return [net60(j, d) - base[(split_of(B[j]['day']), d)] for j, d in rows]


# ============================================ 1. EMPIRICAL MDE (corrected)
print('\n' + '=' * 100)
print('1.  MINIMUM DETECTABLE EDGE - measured, not assumed  (corrects power10.py)')
print('=' * 100)
print('  SE is bootstrapped by DAY on trade sets of the given size, drawn')
print('  the way a strategy draws them: spread across all %d sessions.' % len(DAYS))


def se_at(ntr, reps=6, nb=300):
    ses = []
    for _ in range(reps):
        pick = random.sample(ELIG, min(ntr, len(ELIG)))
        bd = defaultdict(list)
        for j in pick:
            d = +1 if random.random() < 0.5 else -1
            bd[B[j]['day']].append(net60(j, d) - base[(split_of(B[j]['day']), d)])
        pools = list(bd.values())
        ms = []
        for _ in range(nb):
            s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
            ms.append(sum(s) / len(s))
        m = sum(ms) / len(ms)
        ses.append((sum((v - m) ** 2 for v in ms) / (len(ms) - 1)) ** 0.5)
    return sum(ses) / len(ses)


print('\n  %10s %10s %14s %14s' % ('trades', 'SE pt', 'MDE pt/trade', 'MDE $/trade'))
for ntr in (250, 500, 800, 1500, 3000, 6000, 12000):
    se = se_at(ntr)
    print('  %10d %10.3f %14.2f %14.2f' % (ntr, se, 2.80 * se, 2.80 * se * 2.0))
print('\n  So ten months CAN certify an edge of roughly 8-12 pt/trade at')
print('  ~1000-3000 trades. That is a large edge, but it is not the 68 pt')
print('  my earlier table claimed. The window is usable; it just cannot')
print('  resolve small edges.')

# ================================================ 2. CORRECT NULL: SIGN-FLIP
print('\n' + '=' * 100)
print('2.  SIGN-FLIP NULL - same bars, same times, direction randomised by DAY')
print('=' * 100)

rows90 = trades_at(0.90, 30)
real90 = sum(excess(rows90)) / len(rows90)
print('  OFH6 at the declared p90/30min: n=%d  excess %+0.3f pt' % (len(rows90), real90))


def signflip_dist(rows, NS=2000):
    daylist = sorted(set(B[j]['day'] for j, _ in rows))
    out = []
    for _ in range(NS):
        flip = {d: (1 if random.random() < 0.5 else -1) for d in daylist}
        acc = 0.0
        for j, d in rows:
            dd = d * flip[B[j]['day']]
            acc += net60(j, dd) - base[(split_of(B[j]['day']), dd)]
        out.append(acc / len(rows))
    out.sort()
    return out


dist = signflip_dist(rows90)
NS = len(dist)
ge = sum(1 for x in dist if x >= real90)
print('  sign-flip null: median %+0.3f  p95 %+0.3f  SE %0.3f'
      % (dist[NS // 2], dist[int(NS * .95)],
         (sum((v - sum(dist) / NS) ** 2 for v in dist) / (NS - 1)) ** 0.5))
print('  single-hypothesis p (STILL NOT VALID - OFH6 was selected) = %.4f' % (ge / NS))

# ---------------- family-wise, under the same correct null
print('\n  family-wise: the SAME sign-flip applied to all nine firing')
print('  hypotheses, statistic = the family MAX. This is the honest test.')

REP_P90 = sorted(B[j]['repeatedTradeAtExtreme'] for j in ELIG
                 if B[j]['day'] <= DEV_END and B[j]['repeatedTradeAtExtreme'] is not None)
REP_P90 = REP_P90[int(len(REP_P90) * 0.9)]


def sig(name, b):
    if name == 'OFH1':
        return -1 if b['bearishDeltaDivergenceCandidate'] else (
            +1 if b['bullishDeltaDivergenceCandidate'] else 0)
    if name == 'OFH2':
        if b['deltaConfirmsBreak'] and b['priceNewHigh']:
            return +1
        if b['deltaConfirmsBreak'] and b['priceNewLow']:
            return -1
        return 0
    if name == 'OFH3':
        return -1 if b['absorptionBuyCandidate'] else (+1 if b['absorptionSellCandidate'] else 0)
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
        return 0 if (v is None or abs(v) < q(0.90)) else (+1 if v > 0 else -1)
    if name == 'OFH7':
        bd = b['ofBarDelta']
        if bd is None or b['bodyPctOfRange'] is None or b['bodyPctOfRange'] < 25:
            return 0
        up = b['close'] > b['open']
        return +1 if (up and bd < 0) else (-1 if ((not up) and bd > 0) else 0)
    if name == 'OFH9':
        d = b['distPocAtr']
        if d is None or not b['profileReady']:
            return 0
        return -1 if d >= 2 else (+1 if d <= -2 else 0)
    if name == 'OFH12':
        r = b['repeatedTradeAtExtreme']
        if r is None or r < REP_P90:
            return 0
        return -1 if b['priceNewHigh'] else (+1 if b['priceNewLow'] else 0)
    return 0


FAM = ['OFH1', 'OFH2', 'OFH3', 'OFH4', 'OFH5', 'OFH6', 'OFH7', 'OFH9', 'OFH12']
MEMB = {}
for name in FAM:
    lst = []
    last = -10 ** 9
    for j in ELIG:
        d = sig(name, B[j])
        if d == 0 or B[j]['tmin'] - last < 30:
            continue
        last = B[j]['tmin']
        lst.append((j, d))
    MEMB[name] = lst

real_fam = {}
for name in FAM:
    ex = excess(MEMB[name])
    real_fam[name] = sum(ex) / len(ex)
best_name = max(real_fam, key=lambda k: real_fam[k])
print('  real family max = %+0.3f (%s)' % (real_fam[best_name], best_name))

NSF = 1000
famdist = []
for _ in range(NSF):
    flip = {d: (1 if random.random() < 0.5 else -1) for d in DAYS}
    bm = -9e9
    for name in FAM:
        rows = MEMB[name]
        acc = 0.0
        for j, d in rows:
            dd = d * flip[B[j]['day']]
            acc += net60(j, dd) - base[(split_of(B[j]['day']), dd)]
        m = acc / len(rows)
        if m > bm:
            bm = m
    famdist.append(bm)
famdist.sort()
gef = sum(1 for x in famdist if x >= real_fam[best_name])
print('  family-max null: median %+0.3f  p90 %+0.3f  p95 %+0.3f  max %+0.3f'
      % (famdist[NSF // 2], famdist[int(NSF * .9)], famdist[int(NSF * .95)], famdist[-1]))
print('  FAMILY-WISE p = %.4f   <-- the number that decides it' % (gef / NSF))

# ============================================ 3. DOSE-RESPONSE, tested
print('\n' + '=' * 100)
print('3.  DOSE-RESPONSE, with the slope tested against the same null')
print('=' * 100)
PCTS = [0.50, 0.60, 0.70, 0.80, 0.90, 0.95, 0.98]
SETS = {p: trades_at(p, 30) for p in PCTS}
print('  %8s %8s %12s' % ('pctile', 'trades', 'excess'))
obs = []
for p in PCTS:
    ex = excess(SETS[p])
    m = sum(ex) / len(ex)
    obs.append(m)
    print('  %8.2f %8d %+12.3f' % (p, len(SETS[p]), m))


def slope(ys):
    xs = PCTS
    mx = sum(xs) / len(xs)
    my = sum(ys) / len(ys)
    num = sum((a - mx) * (b - my) for a, b in zip(xs, ys))
    den = sum((a - mx) ** 2 for a in xs)
    return num / den


real_slope = slope(obs)
sl = []
for _ in range(NSF):
    flip = {d: (1 if random.random() < 0.5 else -1) for d in DAYS}
    ys = []
    for p in PCTS:
        acc = 0.0
        rows = SETS[p]
        for j, d in rows:
            dd = d * flip[B[j]['day']]
            acc += net60(j, dd) - base[(split_of(B[j]['day']), dd)]
        ys.append(acc / len(rows))
    sl.append(slope(ys))
sl.sort()
ges = sum(1 for x in sl if x >= real_slope)
print('\n  monotone slope (excess per unit percentile): real %+0.2f' % real_slope)
print('  sign-flip null slope: median %+0.2f  p95 %+0.2f   p = %.4f'
      % (sl[NSF // 2], sl[int(NSF * .95)], ges / NSF))
print('  NOTE the dose cells are NESTED (p98 trades are inside p90), so')
print('  this is one correlated shape, not seven independent confirmations.')

# ============================================ 4. WHAT A FORWARD TEST COSTS
print('\n' + '=' * 100)
print('4.  IF OFH6 IS REAL AT ITS OBSERVED SIZE, HOW LONG TO PROVE IT FORWARD?')
print('=' * 100)
per_month = len(rows90) / len(MON)
se1 = se_at(int(round(per_month)) * 1, reps=4)
print('  OFH6 generates ~%.0f trades/month.' % per_month)
print('  %8s %10s %10s %14s' % ('months', 'trades', 'SE pt', 'detectable edge'))
for mth in (3, 6, 9, 12, 18, 24):
    ntr = int(per_month * mth)
    se = se_at(ntr, reps=4)
    print('  %8d %10d %10.3f %14.2f' % (mth, ntr, se, 2.80 * se))
print('\n  At the observed +8.3 pt excess, a pre-registered forward test')
print('  needs roughly the number of months where the detectable edge')
print('  column drops below ~8 pt. That is the honest price of proof.')
