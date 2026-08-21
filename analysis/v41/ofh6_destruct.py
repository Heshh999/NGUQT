#!/usr/bin/env python3
# OFH6 DESTRUCTION BATTERY. The rule is frozen in ofh6_spec.py and is
# imported, never redefined. Nothing here may change OFH6; every test
# either survives or does not.
#
# Tests, in the order requested:
#   1  P&L concentration (top 1/5/10% share) - diagnostic, not pass/fail
#   2  blocked month-by-month, longs and shorts separately, day-clustered
#      bootstrap; plus whether one or two WEEKS carry the result
#   3  multiple-testing correction across the twelve ideas ACTUALLY
#      searched - max-statistic, Bonferroni and BH, no retrofitting
#   4  threshold-neighbourhood robustness (plateau vs spike)
#   5  matched controls: same volatility / volume / time-of-day / range,
#      and a 15-bar PRICE-momentum competitor
#   6  MFE vs MAE and favourable-first ordering - exact on the 1m path
#   7  stop x target family - looking for a plateau, not a best cell
#
# All excesses are over the side-matched, split-matched baseline.

import sys, os, random, math
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ofh6_spec import (load_bars, eligible, signals, ret, split_of, baselines,
                       excess, THRESHOLD, COST_PTS, DOLLARS_PER_POINT,
                       PRIMARY_EXIT_MIN, FORWARD_WINDOW_MIN, COOLDOWN_MIN)

random.seed(41)
B = load_bars()
ELIG = eligible(B)
BASE = baselines(B, ELIG)
ROWS = signals(B, ELIG)
EX = excess(B, ROWS, BASE)
DAYS = sorted(set(B[j]['day'] for j in ELIG))
NET = [v - COST_PTS for v in EX]

print('OFH6 destruction battery.  n=%d trades, %d sessions, frozen thr=%.0f'
      % (len(ROWS), len(set(B[j]['day'] for j, _ in ROWS)), THRESHOLD))


def dayboot(pairs, nb=4000):
    """pairs: [(day, value)]. Returns (mean, lo, hi, p_le_zero)."""
    bd = defaultdict(list)
    for d, v in pairs:
        bd[d].append(v)
    pools = list(bd.values())
    if not pools:
        return float('nan'), float('nan'), float('nan'), float('nan')
    ms = []
    for _ in range(nb):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        ms.append(sum(s) / len(s))
    ms.sort()
    mu = sum(v for _, v in pairs) / len(pairs)
    return mu, ms[int(nb * .025)], ms[int(nb * .975)], sum(1 for x in ms if x <= 0) / nb


# ================================================== 1. P&L CONCENTRATION
print('\n' + '=' * 100)
print('1.  P&L CONCENTRATION - diagnostic')
print('=' * 100)
srt = sorted(NET, reverse=True)
tot = sum(srt)
pos_tot = sum(v for v in srt if v > 0)
print('  total net %+0.1f pt   mean %+0.3f   median %+0.3f   win%% %.1f'
      % (tot, tot / len(srt), sorted(NET)[len(NET) // 2],
         100.0 * sum(1 for v in NET if v > 0) / len(NET)))
for pct in (0.01, 0.05, 0.10, 0.25):
    k = max(1, int(len(srt) * pct))
    share = sum(srt[:k]) / tot * 100.0 if tot else float('nan')
    print('  top %4.0f%% of trades (%3d trades): %+8.1f pt = %6.1f%% of total net'
          % (pct * 100, k, sum(srt[:k]), share))
print('  share of GROSS WINNINGS from the top 5%% of winners: %.1f%%'
      % (sum(srt[:max(1, int(len(srt) * .05))]) / pos_tot * 100.0))
print('  ->  a positive median (%+0.2f pt) with %.0f%% winners means the'
      % (sorted(NET)[len(NET) // 2], 100.0 * sum(1 for v in NET if v > 0) / len(NET)))
print('      centre of the distribution carries weight, not only the tail.')

# ============================================ 2. BLOCKED MONTH / WEEK
print('\n' + '=' * 100)
print('2.  BLOCKED STABILITY - month by month, longs and shorts apart')
print('=' * 100)
bymon = defaultdict(list)
for (j, d), v in zip(ROWS, EX):
    bymon[B[j]['day'][:7]].append((B[j]['day'], d, v))
print('  %-9s %6s %10s %20s %8s %6s %9s %6s %9s'
      % ('month', 'n', 'excess', 'day-block 95% CI', 'p', 'nL', 'longs', 'nS', 'shorts'))
mpos = 0
for m, lst in sorted(bymon.items()):
    mu, lo, hi, p = dayboot([(d, v) for d, _, v in lst])
    L = [v for _, s, v in lst if s > 0]
    S = [v for _, s, v in lst if s < 0]
    if mu > 0:
        mpos += 1
    print('  %-9s %6d %+10.3f   [%+7.2f,%+7.2f] %8.3f %6d %+9.2f %6d %+9.2f'
          % (m, len(lst), mu, lo, hi, p, len(L), sum(L) / len(L) if L else float('nan'),
             len(S), sum(S) / len(S) if S else float('nan')))
print('  months with positive excess: %d of %d' % (mpos, len(bymon)))

allL = [(B[j]['day'], v) for (j, d), v in zip(ROWS, EX) if d > 0]
allS = [(B[j]['day'], v) for (j, d), v in zip(ROWS, EX) if d < 0]
for tag, lst in (('LONGS', allL), ('SHORTS', allS)):
    mu, lo, hi, p = dayboot(lst)
    print('  %-6s pooled n=%4d  excess %+0.3f  CI [%+0.2f, %+0.2f]  p=%.3f'
          % (tag, len(lst), mu, lo, hi, p))


def isoweek(day):
    y, m, d = int(day[:4]), int(day[5:7]), int(day[8:10])
    import datetime
    return datetime.date(y, m, d).isocalendar()[:2]


byweek = defaultdict(list)
for (j, d), v in zip(ROWS, EX):
    byweek[isoweek(B[j]['day'])].append(v)
wk = sorted(((sum(v), k, len(v)) for k, v in byweek.items()), reverse=True)
tot_ex = sum(EX)
print('\n  DO ONE OR TWO WEEKS CARRY IT?  %d trading weeks in the window.' % len(byweek))
print('  total excess %+0.1f pt' % tot_ex)
for k in (1, 2, 3, 5):
    drop = sum(s for s, _, _ in wk[:k])
    rest = [v for key, vs in byweek.items()
            if key not in [x[1] for x in wk[:k]] for v in vs]
    print('  drop best %d week(s): removes %+7.1f pt (%5.1f%%); remaining %4d trades mean %+0.3f'
          % (k, drop, 100.0 * drop / tot_ex, len(rest), sum(rest) / len(rest)))
wpos = sum(1 for s, _, _ in wk if s > 0)
print('  weeks with positive total excess: %d of %d' % (wpos, len(wk)))

# ========================================== 3. MULTIPLE-TESTING CORRECTION
print('\n' + '=' * 100)
print('3.  MULTIPLE TESTING ACROSS THE TWELVE IDEAS ACTUALLY SEARCHED')
print('=' * 100)
print('  OFH6 was hypothesis #6 of 12 declared and was chosen because it')
print('  scored best. It is not treated as #1 anywhere below.')

REP_P90 = sorted(B[j]['repeatedTradeAtExtreme'] for j in ELIG
                 if B[j]['day'] <= '2026-03-31' and B[j]['repeatedTradeAtExtreme'] is not None)
REP_P90 = REP_P90[int(len(REP_P90) * 0.9)]


def sig12(name, b):
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
        return 0 if (v is None or abs(v) < THRESHOLD) else (+1 if v > 0 else -1)
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


FIRED = ['OFH1', 'OFH2', 'OFH3', 'OFH4', 'OFH5', 'OFH6', 'OFH7', 'OFH9', 'OFH12']
SILENT = ['OFH8', 'OFH10', 'OFH11']
MEMB = {}
for name in FIRED:
    lst = []
    last = -10 ** 9
    for j in ELIG:
        d = sig12(name, B[j])
        if d == 0 or B[j]['tmin'] - last < COOLDOWN_MIN:
            continue
        last = B[j]['tmin']
        lst.append((j, d))
    MEMB[name] = lst

RET = {}
for name in FIRED:
    for j, d in MEMB[name]:
        for dd in (+1, -1):
            RET[(j, dd)] = ret(B, j, dd) - BASE[(split_of(B[j]['day']), dd)]

realmu = {nm: sum(RET[(j, d)] for j, d in MEMB[nm]) / len(MEMB[nm]) for nm in FIRED}
NS = 4000
persist = {nm: 0 for nm in FIRED}
maxdist = []
for _ in range(NS):
    flip = {d: (1 if random.random() < 0.5 else -1) for d in DAYS}
    bm = -9e9
    for nm in FIRED:
        acc = 0.0
        for j, d in MEMB[nm]:
            acc += RET[(j, d * flip[B[j]['day']])]
        m = acc / len(MEMB[nm])
        if m >= realmu[nm]:
            persist[nm] += 1
        if m > bm:
            bm = m
    maxdist.append(bm)
maxdist.sort()
praw = {nm: persist[nm] / float(NS) for nm in FIRED}
print('\n  %-7s %7s %10s %10s %12s' % ('hyp', 'n', 'excess', 'p raw', 'BH q'))
order = sorted(FIRED, key=lambda k: praw[k])
M = 12                                   # all twelve were searched
bh = {}
prev = 1.0
for i in range(len(order) - 1, -1, -1):
    nm = order[i]
    q = praw[nm] * M / (i + 1)
    prev = min(prev, q)
    bh[nm] = min(prev, 1.0)
for nm in order:
    print('  %-7s %7d %+10.3f %10.4f %12.4f' % (nm, len(MEMB[nm]), realmu[nm], praw[nm], bh[nm]))
for nm in SILENT:
    print('  %-7s %7d %10s %10s %12s' % (nm, 0, 'n/a', 'n/a', 'n/a'))
ge = sum(1 for x in maxdist if x >= realmu['OFH6'])
print('\n  max-statistic family-wise p for OFH6 = %.4f  (accounts for the' % (ge / float(NS)))
print('    correlation between hypotheses; the correct correction here)')
print('  Bonferroni over 12: %.4f x 12 = %.4f' % (praw['OFH6'], min(1.0, praw['OFH6'] * 12)))
print('  Benjamini-Hochberg q for OFH6 (M=12): %.4f' % bh['OFH6'])

# =========================================== 4. THRESHOLD NEIGHBOURHOOD
print('\n' + '=' * 100)
print('4.  THRESHOLD NEIGHBOURHOOD - plateau or spike?')
print('=' * 100)
print('  Frozen threshold is 3380. Perturbed +/-40%% in 10%% steps.')
print('  %10s %8s %10s %10s %20s %8s' % ('threshold', 'trades', 'excess', 'median', '95% CI', 'p'))
for mult in (0.6, 0.7, 0.8, 0.9, 1.0, 1.1, 1.2, 1.3, 1.4):
    thr = THRESHOLD * mult
    rr = signals(B, ELIG, threshold=thr)
    ee = excess(B, rr, BASE)
    mu, lo, hi, p = dayboot([(B[j]['day'], v) for (j, _), v in zip(rr, ee)])
    star = '  <-- FROZEN' if abs(mult - 1.0) < 1e-9 else ''
    print('  %10.0f %8d %+10.3f %+10.3f   [%+7.2f,%+7.2f] %8.3f%s'
          % (thr, len(rr), mu, sorted(ee)[len(ee) // 2], lo, hi, p, star))
print('\n  cooldown perturbation (frozen = 30 min)')
print('  %10s %8s %10s %8s' % ('cooldown', 'trades', 'excess', 'p'))
for cd in (5, 10, 15, 30, 45, 60):
    rr = signals(B, ELIG, cooldown=cd)
    ee = excess(B, rr, BASE)
    mu, lo, hi, p = dayboot([(B[j]['day'], v) for (j, _), v in zip(rr, ee)])
    print('  %10d %8d %+10.3f %8.3f%s' % (cd, len(rr), mu, p,
                                          '  <-- FROZEN' if cd == 30 else ''))

# ================================================== 5. MATCHED CONTROLS
print('\n' + '=' * 100)
print('5.  MATCHED CONTROLS - is it delta, or is it just volatile bars?')
print('=' * 100)


def qcut(vals, k):
    s = sorted(vals)
    return [s[int(len(s) * i / k)] for i in range(1, k)]


atr_c = qcut([B[j]['atr'] for j in ELIG], 5)
vol_c = qcut([B[j]['relVolume'] for j in ELIG if B[j]['relVolume'] is not None], 5)


def bucket(j):
    b = B[j]
    a = sum(1 for c in atr_c if b['atr'] > c)
    v = sum(1 for c in vol_c if (b['relVolume'] or 0) > c)
    t = min(int((b['minutesFromRthOpen'] or 0) // 90), 3)
    return (a, v, t)


sigset = set(j for j, _ in ROWS)
pool = defaultdict(list)
for j in ELIG:
    if j in sigset:
        continue
    pool[bucket(j)].append(j)

matched = []
miss = 0
for j, d in ROWS:
    cand = pool.get(bucket(j), [])
    if not cand:
        miss += 1
        continue
    k = random.choice(cand)
    dd = +1 if B[k]['dsum15'] > 0 else -1        # same rule, sub-threshold bar
    matched.append((B[k]['day'], ret(B, k, dd) - BASE[(split_of(B[k]['day']), dd)]))
mu0, lo0, hi0, p0 = dayboot([(B[j]['day'], v) for (j, _), v in zip(ROWS, EX)])
mu1, lo1, hi1, p1 = dayboot(matched)
print('  OFH6 (above threshold)          n=%4d  excess %+0.3f  CI [%+0.2f,%+0.2f]'
      % (len(ROWS), mu0, lo0, hi0))
print('  matched sub-threshold controls  n=%4d  excess %+0.3f  CI [%+0.2f,%+0.2f]'
      % (len(matched), mu1, lo1, hi1))
print('  matched on ATR quintile x relVolume quintile x 90-min RTH block'
      + ('   (%d signals had no match)' % miss if miss else ''))
print('  DIFFERENCE %+0.3f pt  -> delta magnitude adds this much over bars'
      % (mu0 - mu1))
print('     that merely look the same in volatility, volume and time.')

# --- competitor: 15-bar PRICE momentum, matched trade count
pm = []
for j in ELIG:
    if B[j - 15]['tmin'] != B[j]['tmin'] - 15:
        continue
    pm.append((j, B[j]['close'] - B[j - 15]['close']))
pmv = sorted(abs(v) for _, v in pm)
# choose the percentile that yields the same number of trades as OFH6
target_n = len(ROWS)
best = None
for pct in [x / 200.0 for x in range(150, 200)]:
    thr = pmv[min(int(len(pmv) * pct), len(pmv) - 1)]
    rr = []
    last = -10 ** 9
    for j, v in pm:
        if abs(v) < thr or B[j]['tmin'] - last < COOLDOWN_MIN:
            continue
        last = B[j]['tmin']
        rr.append((j, +1 if v > 0 else -1))
    if best is None or abs(len(rr) - target_n) < abs(best[1] - target_n):
        best = (rr, len(rr), thr)
rr = best[0]
ee = excess(B, rr, BASE)
mu2, lo2, hi2, p2 = dayboot([(B[j]['day'], v) for (j, _), v in zip(rr, ee)])
print('\n  COMPETITOR: 15-bar PRICE momentum, same cooldown, matched trade count')
print('  price-momentum n=%4d  excess %+0.3f  CI [%+0.2f,%+0.2f]  p=%.3f'
      % (len(rr), mu2, lo2, hi2, p2))
print('  OFH6 minus price-momentum: %+0.3f pt' % (mu0 - mu2))
overlap = len(set(j for j, _ in rr) & sigset)
print('  bar overlap between the two signal sets: %d of %d (%.0f%%)'
      % (overlap, len(rr), 100.0 * overlap / len(rr)))

# ======================================= 6. MFE vs MAE, FAVOURABLE FIRST
print('\n' + '=' * 100)
print('6.  EXCURSION ASYMMETRY AND FAVOURABLE-FIRST ORDERING (exact on 1m path)')
print('=' * 100)


def excursions(j, side, cap):
    e = B[j]['close']
    mfe = 0.0
    mae = 0.0
    for k in range(1, cap + 1):
        c = B[j + k]
        f = (c['high'] - e) if side > 0 else (e - c['low'])
        a = (e - c['low']) if side > 0 else (c['high'] - e)
        if f > mfe:
            mfe = f
        if a > mae:
            mae = a
    return mfe, mae


for cap in (60, 90):
    mf = []
    ma = []
    mfa = []
    maa = []
    for j, d in ROWS:
        f, a = excursions(j, d, cap)
        mf.append(f)
        ma.append(a)
        mfa.append(f / B[j]['atr'])
        maa.append(a / B[j]['atr'])
    mf.sort()
    ma.sort()
    mfa.sort()
    maa.sort()
    print('  %dm  medMFE %6.2f pt (%4.2f ATR)   medMAE %6.2f pt (%4.2f ATR)   ratio %5.3f'
          % (cap, mf[len(mf) // 2], mfa[len(mfa) // 2], ma[len(ma) // 2], maa[len(maa) // 2],
             mf[len(mf) // 2] / ma[len(ma) // 2]))

print('\n  FAVOURABLE-FIRST: fraction reaching +X ATR before -X ATR')
print('  (exact first-touch race on the 1-minute path; ties -> adverse)')
print('  %8s %8s %12s %14s %10s' % ('X (ATR)', 'resolved', 'fav-first %', 'sign-flip null', 'p'))
for X in (0.5, 1.0, 1.5, 2.0, 3.0):
    def favfirst(j, side):
        e = B[j]['close']
        a = B[j]['atr'] * X
        for k in range(1, FORWARD_WINDOW_MIN + 1):
            c = B[j + k]
            up = c['high'] - e
            dn = e - c['low']
            hf = (up >= a) if side > 0 else (dn >= a)
            ha = (dn >= a) if side > 0 else (up >= a)
            if hf and ha:
                return 0
            if hf:
                return 1
            if ha:
                return 0
        return None
    res = [(B[j]['day'], favfirst(j, d), j, d) for j, d in ROWS]
    res = [(day, v, j, d) for day, v, j, d in res if v is not None]
    if not res:
        continue
    pct = 100.0 * sum(v for _, v, _, _ in res) / len(res)
    nd = []
    for _ in range(2000):
        flip = {dd: (1 if random.random() < 0.5 else -1) for dd in DAYS}
        acc = 0
        cnt = 0
        for day, _, j, d in res:
            v = favfirst(j, d * flip[day])
            if v is not None:
                acc += v
                cnt += 1
        nd.append(100.0 * acc / cnt)
    nd.sort()
    p = sum(1 for x in nd if x >= pct) / float(len(nd))
    print('  %8.1f %8d %12.1f %14.1f %10.3f' % (X, len(res), pct, nd[len(nd) // 2], p))

# ================================================ 7. STOP x TARGET FAMILY
print('\n' + '=' * 100)
print('7.  STOP x TARGET FAMILY - looking for a PLATEAU, not a best cell')
print('=' * 100)


def race(j, side, stop_m, tgt_m):
    e = B[j]['close']
    a = B[j]['atr']
    sp = e - side * stop_m * a
    tp = e + side * tgt_m * a if tgt_m else None
    for k in range(1, FORWARD_WINDOW_MIN + 1):
        c = B[j + k]
        hs = (c['low'] <= sp) if side > 0 else (c['high'] >= sp)
        ht = tp is not None and ((c['high'] >= tp) if side > 0 else (c['low'] <= tp))
        if hs:
            return (sp - e) * side               # stop wins ties: conservative
        if ht:
            return (tp - e) * side
    return (B[j + FORWARD_WINDOW_MIN]['close'] - e) * side


STOPS = [1.0, 1.5, 2.0, 2.5, 3.0, 4.0]
TGTS = [1.0, 1.5, 2.0, 3.0, None]
print('  net pt/trade after %.2f cost, excess over side-matched baseline' % COST_PTS)
hdr = '  %-8s' % 'stop\\tgt'
for t in TGTS:
    hdr += '%12s' % (('%.1fR' % t) if t else 'none')
print(hdr)
plateau = 0
cells = 0
for s in STOPS:
    line = '  %-8s' % ('%.1f ATR' % s)
    for t in TGTS:
        acc = []
        for j, d in ROWS:
            v = race(j, d, s, t) - BASE[(split_of(B[j]['day']), d)] - COST_PTS
            acc.append(v)
        m = sum(acc) / len(acc)
        cells += 1
        if m > 0:
            plateau += 1
        line += '%12.2f' % m
    print(line)
print('  cells positive after cost: %d of %d' % (plateau, cells))
print('  (a real payoff region is a contiguous BLOCK of positive cells;')
print('   one isolated positive cell is a coincidence)')
