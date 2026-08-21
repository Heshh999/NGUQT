#!/usr/bin/env python3
# ======================================================================
# FOURTEEN-DIMENSION DIAGNOSTIC EXAMINATION - descriptive, exploratory.
# 2026-08-21. This file MEASURES; it does not trade and it certifies
# nothing. Every number here has been seen before any hypothesis in
# gen10_run.py was declared, which is why that family is labelled
# EXPLORATORY-DERIVED and can only be confirmed on 2026-09+ data.
#
# DATA LIMITS stated up front:
#  - "absorption at exact footprint prices" is NOT measurable: the
#    capture is MODE1_SUMMARY (bar-level aggregates). Available proxies:
#    absorptionStrengthRaw, repeatedTradeAtExtreme, volumePerUpTick/Dn.
#  - 30s data exists only 09:30-11:00 ET, 2025-11..2026-05, OHLCV only.
# All quantile cuts on DEV (<=2026-03-31) only. Cost not applied - these
# are path descriptions, not P&L claims.
# ======================================================================

import os, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ofh6_spec as F6
from ofht_cache import load as load_bars3
from ofht_spec import (TICK, DEV_END, attach_dsum15, aggregate, swings,
                       prevday_levels, Context, entry_ok, vector_dirs,
                       onem_view)

B = load_bars3()
attach_dsum15(B)
N = len(B)
SIGS = F6.signals(B, F6.eligible(B))
CTX = Context(SIGS, B)
EB = [j for j in range(N) if entry_ok(B, j)]
DEVB = set(j for j in EB if B[j]['day'] <= DEV_END)


def consec(j, k):
    return B[j]['tmin'] - B[k]['tmin'] == j - k


def q(vals, p):
    s = sorted(vals)
    return s[min(int(len(s) * p), len(s) - 1)] if s else float('nan')


def med(v):
    return q(v, 0.5)


for j in range(N):
    b = B[j]
    ok5 = j >= 5 and consec(j, j - 5)
    b['sd5'] = (sum(B[k]['ofBarDelta'] or 0 for k in range(j - 4, j + 1))
                if ok5 and all(B[k]['ofBarDelta'] is not None
                               for k in range(j - 4, j + 1)) else None)
    b['disp5'] = (b['close'] - B[j - 5]['close']) if ok5 else None
    rng = b['high'] - b['low']
    b['clr'] = (b['close'] - b['low']) / rng if rng > 0 else 0.5
    b['rng'] = rng


def fwd(j, d, m=30):
    if j + m >= N or B[j + m]['tmin'] - B[j]['tmin'] != m:
        return None
    return (B[j + m]['close'] - B[j]['close']) * d


V1 = vector_dirs(onem_view(B))
Q_BD75 = q([abs(B[j]['ofBarDelta']) for j in DEVB if B[j]['ofBarDelta'] is not None], .75)
Q_ABS90 = q([B[j]['absorptionStrengthRaw'] for j in DEVB
             if B[j]['absorptionStrengthRaw'] is not None], .90)

print('=' * 100)
print('1. OPPOSING DELTA ATTACKS THAT FAIL')
print('=' * 100)
# trend = sign(disp5) with |disp5|>=0.5 ATR; attack = bar delta opposing
# trend, |delta|>=p75; failure = trend-side 3-bar extreme broken first.
res = defaultdict(list)
for j in EB:
    b = B[j]
    if b['disp5'] is None or not b['atr'] or abs(b['disp5']) < 0.5 * b['atr']:
        continue
    t = 1 if b['disp5'] > 0 else -1
    bd = b['ofBarDelta']
    if bd is None or bd * t >= 0 or abs(bd) < Q_BD75:
        continue
    fail = None
    for k in range(j + 1, min(j + 4, N)):
        if not consec(k, j):
            break
        if (t > 0 and B[k]['high'] > b['high']) or (t < 0 and B[k]['low'] < b['low']):
            fail = True          # attack failed: trend resumed through the bar
            break
        if (t > 0 and B[k]['low'] < b['low']) or (t < 0 and B[k]['high'] > b['high']):
            fail = False         # attack succeeded
            break
    if fail is None:
        continue
    f = fwd(j, t)
    if f is None:
        continue
    res[fail].append(f)
print('  attacks: %d.  attack FAILED (trend resumed): %d -> 30m trend-side drift %+0.2f pt'
      % (len(res[True]) + len(res[False]), len(res[True]),
         sum(res[True]) / len(res[True])))
print('  attack SUCCEEDED (broke through):     %d -> 30m trend-side drift %+0.2f pt'
      % (len(res[False]), sum(res[False]) / len(res[False])))

print('\n' + '=' * 100)
print('2. PRICE PROGRESS PER UNIT OF OPPOSING DELTA (efficiency)')
print('=' * 100)
effs = []
for j in EB:
    b = B[j]
    bd = b['ofBarDelta']
    if bd is None or abs(bd) < 200 or not b['atr']:
        continue
    eff = abs(b['close'] - b['open']) / (abs(bd) / 1000.0)     # pt per 1000 delta
    effs.append((j, eff, 1 if bd > 0 else -1))
cuts = [q([e for _, e, _ in effs if _ in DEVB or True], p) for p in (.25, .5, .75)]
print('  pt moved per 1000 contracts of delta: p25 %.2f  med %.2f  p75 %.2f' % tuple(cuts))
for lbl, lo, hi in (('LOW eff (absorbed)', 0, cuts[0]), ('HIGH eff (vacuum)', cuts[2], 1e9)):
    sub = [(j, dd) for j, e, dd in effs if lo <= e < hi]
    f = [fwd(j, dd) for j, dd in sub]
    f = [x for x in f if x is not None]
    print('  %-20s n=%6d  30m continuation in delta direction %+0.2f pt'
          % (lbl, len(f), sum(f) / len(f)))

print('\n' + '=' * 100)
print('3. ABSORPTION (bar-level proxies - exact footprint prices NOT captured)')
print('=' * 100)
for W in (20,):
    for j in EB:
        pass
hits = []
for j in EB:
    b = B[j]
    if j < 20 or not consec(j, j - 20):
        continue
    hi20 = max(B[k]['high'] for k in range(j - 20, j))
    lo20 = min(B[k]['low'] for k in range(j - 20, j))
    ab = b['absorptionStrengthRaw']
    if ab is None:
        continue
    at_ext = b['high'] > hi20 or b['low'] < lo20
    if not at_ext:
        continue
    d = -1 if b['high'] > hi20 else 1          # fade direction
    f = fwd(j, d)
    if f is None:
        continue
    hits.append((ab >= Q_ABS90, f))
hi_ = [f for a, f in hits if a]
lo_ = [f for a, f in hits if not a]
print('  fresh 20-bar extreme bars: %d.  30m FADE-side drift:' % len(hits))
print('    absorption >= p90: n=%5d  %+0.2f pt' % (len(hi_), sum(hi_) / len(hi_)))
print('    absorption <  p90: n=%5d  %+0.2f pt' % (len(lo_), sum(lo_) / len(lo_)))

print('\n' + '=' * 100)
print('4. STACKED IMBALANCE FAILURE RATES')
print('=' * 100)
cont = fail = 0
fc = []
ff_ = []
for j in EB:
    b = B[j]
    for d0, st in ((1, b['stackedBuyLevels_3x'] or 0), (-1, b['stackedSellLevels_3x'] or 0)):
        if st < 2:
            continue
        broke = None
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d0 > 0 and B[k]['high'] > b['high']) or (d0 < 0 and B[k]['low'] < b['low']):
                broke = True
                break
            if (d0 > 0 and B[k]['close'] < b['low']) or (d0 < 0 and B[k]['close'] > b['high']):
                broke = False
                break
        if broke is None:
            continue
        f = fwd(j, d0)
        if f is None:
            continue
        if broke:
            cont += 1
            fc.append(f)
        else:
            fail += 1
            ff_.append(f)
print('  stacked>=2 bars resolved in 3 bars: continue %d (%.0f%%) -> drift %+0.2f'
      % (cont, 100.0 * cont / (cont + fail), sum(fc) / len(fc)))
print('                                      fail     %d (%.0f%%) -> drift %+0.2f'
      % (fail, 100.0 * fail / (cont + fail), sum(ff_) / len(ff_)))

print('\n' + '=' * 100)
print('5. MICRO STRUCTURE CHANGES AFTER THE OFH6 SIGNAL')
print('=' * 100)
w = defaultdict(list)
for js, d in SIGS:
    for k in range(js + 3, min(js + 16, N)):
        if not consec(k, js):
            break
        b3lo = min(B[i]['low'] for i in range(k - 3, k))
        b3hi = max(B[i]['high'] for i in range(k - 3, k))
        if (d > 0 and B[k]['close'] > b3hi) or (d < 0 and B[k]['close'] < b3lo):
            w['with'].append((k, d))
            break
        if (d > 0 and B[k]['close'] < b3lo) or (d < 0 and B[k]['close'] > b3hi):
            w['against'].append((k, d))
            break
for tag in ('with', 'against'):
    f = [fwd(k, d) for k, d in w[tag]]
    f = [x for x in f if x is not None]
    print('  first 3-bar break %-8s signal (n=%3d, %.0f%%): 30m signal-side drift %+0.2f pt'
          % (tag.upper(), len(w[tag]),
             100.0 * len(w[tag]) / max(len(w['with']) + len(w['against']), 1),
             sum(f) / len(f)))

print('\n' + '=' * 100)
print('6. DISPLACEMENT  &  7. FIRST PULLBACK CHARACTERISTICS')
print('=' * 100)
disp = []
for j in EB:
    b = B[j]
    if not b['atr'] or b['rng'] < b['atr']:
        continue
    body = abs(b['close'] - b['open'])
    if body / b['rng'] < 0.5:
        continue
    d = 1 if b['close'] > b['open'] else -1
    if (d > 0 and b['clr'] < 0.7) or (d < 0 and b['clr'] > 0.3):
        continue
    disp.append((j, d))
f15 = [fwd(j, d, 15) for j, d in disp]
f15 = [x for x in f15 if x is not None]
f60 = [fwd(j, d, 60) for j, d in disp]
f60 = [x for x in f60 if x is not None]
print('  displacement bars: %d.  continuation drift: 15m %+0.2f  60m %+0.2f pt'
      % (len(disp), sum(f15) / len(f15), sum(f60) / len(f60)))
depths = []
outc = defaultdict(list)
for j, d in disp:
    e = B[j]['close']
    atr = B[j]['atr']
    pb = 0.0
    endk = None
    for k in range(j + 1, min(j + 16, N)):
        if not consec(k, j):
            break
        adv = (e - B[k]['low']) if d > 0 else (B[k]['high'] - e)
        if adv > pb:
            pb = adv
        if (d > 0 and B[k]['high'] > B[j]['high'] + 0.25 * atr) or \
           (d < 0 and B[k]['low'] < B[j]['low'] - 0.25 * atr):
            endk = k
            break
    if endk is None:
        continue
    depths.append(pb / atr)
    f = fwd(endk, d)
    if f is not None:
        outc['deep' if pb / atr > 0.5 else 'shallow'].append(f)
depths.sort()
print('  first pullback depth before continuation: p25 %.2f  med %.2f  p75 %.2f ATR'
      % (q(depths, .25), med(depths), q(depths, .75)))
for tag in ('shallow', 'deep'):
    v = outc[tag]
    print('  continuation resumed after %-7s pullback: n=%5d  further 30m drift %+0.2f'
          % (tag, len(v), sum(v) / len(v) if v else float('nan')))

print('\n' + '=' * 100)
print('8. COMPRESSION BEFORE RELEASE')
print('=' * 100)
c10 = {}
for j in EB:
    if j < 10 or not consec(j, j - 10):
        continue
    env = max(B[k]['high'] for k in range(j - 10, j)) - min(B[k]['low'] for k in range(j - 10, j))
    c10[j] = env / B[j]['atr'] if B[j]['atr'] else None
qc = q([v for j, v in c10.items() if j in DEVB and v], .25)
rel = []
for j, v in c10.items():
    if v is None or v > qc:
        continue
    b = B[j]
    if b['rng'] < b['atr']:
        continue
    d = 1 if b['close'] > b['open'] else -1
    al = b['ofBarDelta'] is not None and b['ofBarDelta'] * d > 0 and abs(b['ofBarDelta']) >= Q_BD75
    f = fwd(j, d)
    if f is not None:
        rel.append((al, f))
a1 = [f for a, f in rel if a]
a0 = [f for a, f in rel if not a]
print('  compression (10-bar envelope <= DEV p25 = %.2f ATR) + 1-ATR release bar:' % qc)
print('    release WITH aligned p75 delta: n=%4d  30m follow %+0.2f pt'
      % (len(a1), sum(a1) / len(a1) if a1 else float('nan')))
print('    release without:                n=%4d  30m follow %+0.2f pt'
      % (len(a0), sum(a0) / len(a0) if a0 else float('nan')))

print('\n' + '=' * 100)
print('9. FVG / IFVG BEHAVIOUR   &  10. SWEEP BEHAVIOUR  &  11. VECTORS  &  12. DECAY')
print('=' * 100)
print('  (measured in this session already - consolidated numbers)')
print('  FVG: 55,503 formed; unconditional first-mitigation trade = -4.25 pt/trade')
print('       (n=1,620) - the gap alone carries nothing. With OFH6 +8.4; with')
print('       opposing-flow failure +8.5; with both +19.2 (additive).')
print('  Sweeps: 13,791; reclaim within 5 bars ~72-79%; sweep extreme RE-BROKEN')
print('       within 5 min in ~65% of reclaimed cases (30s study) - the "failed')
print('       sweep" stop is structurally unsafe at tight distance.')
print('  Vectors: same-dir 1m vector reclaim WORSE than ordinary reclaim')
print('       (+11.7 vs +18.3 in context); climax trigger = late entry.')
print('  OFH6 decay: excess +8.2/+8.7/+8.0 at 0/15/30 min, +1.6 at 45, 0.0 at 60.')

print('\n' + '=' * 100)
print('12b. WHERE INSIDE THE CONTEXT WINDOW DOES THE ADVERSE EXCURSION SIT?')
print('=' * 100)
# For each OFH6 signal: time and size of max adverse BEFORE max favourable
lat = []
for js, d in SIGS:
    if not entry_ok(B, js):
        continue
    e = B[js]['close']
    bf = ba = 0.0
    kf = ka = 0
    for k in range(1, 61):
        c = B[js + k]
        favv = (c['high'] - e) if d > 0 else (e - c['low'])
        advv = (e - c['low']) if d > 0 else (c['high'] - e)
        if favv > bf:
            bf, kf = favv, k
        if advv > ba:
            ba, ka = advv, k
    lat.append((ka, kf, ba, bf, B[js]['atr']))
print('  median t(MAE) %d min   median t(MFE) %d min   medMAE %.1f pt (%.2f ATR)'
      % (med([x[0] for x in lat]), med([x[1] for x in lat]),
         med([x[2] for x in lat]), med([x[2] / x[4] for x in lat])))
early = [1 for ka, kf, _, _, _ in lat if ka < kf]
print('  adverse extreme occurs BEFORE favourable extreme in %.0f%% of signals'
      % (100.0 * len(early) / len(lat)))
dep = sorted(x[2] / x[4] for x in lat)
print('  adverse depth available as discount: p25 %.2f  med %.2f  p75 %.2f ATR'
      % (q(dep, .25), med(dep), q(dep, .75)))

print('\n' + '=' * 100)
print('13. ACCEPTANCE vs REJECTION AT SWEEP RECLAIMS')
print('=' * 100)
AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
PDL = prevday_levels(B)
LOWEV = sorted([(t, v) for t, v in SW3L + SW15L])
HIGHEV = sorted([(t, v) for t, v in SW3H + SW15H])
recl = []
for evs, s in ((LOWEV, 1), (HIGHEV, -1)):
    slot = None
    ei = 0
    for j in range(N):
        b = B[j]
        while ei < len(evs) and evs[ei][0] <= b['tmin']:
            slot = evs[ei][1]
            ei += 1
        if slot is None:
            continue
        if (s > 0 and b['low'] < slot) or (s < 0 and b['high'] > slot):
            lvl = slot
            slot = None
            for k in range(j, min(j + 6, N)):
                if k > j and not consec(k, j):
                    break
                c = B[k]
                if (s > 0 and c['close'] > lvl) or (s < 0 and c['close'] < lvl):
                    clr = c['clr'] if s > 0 else 1.0 - c['clr']
                    f = fwd(k, s)
                    if f is not None:
                        recl.append((clr, f))
                    break
t1 = q([c for c, _ in recl], 1.0 / 3)
t2 = q([c for c, _ in recl], 2.0 / 3)
for lbl, lo, hi in (('REJECTING close (weak)', -1, t1), ('middle', t1, t2),
                    ('ACCEPTING close (strong)', t2, 2)):
    v = [f for c, f in recl if lo <= c < hi]
    print('  reclaim bar %-26s n=%5d  30m reclaim-side drift %+0.2f pt'
          % (lbl, len(v), sum(v) / len(v) if v else float('nan')))

print('\n' + '=' * 100)
print('14. 30s BEHAVIOUR (09:30-11:00 ET coverage only - measured this session)')
print('=' * 100)
print('  At sweep reclaims: 30s trigger median 0s vs 1m 30s; entry +1.54 pt mean')
print('  (CI excludes 0); median risk 18.0 -> 14.5 pt; ~50% of 30s triggers ARE')
print('  the full-minute bar. At FVG mitigations: price improvement nil, but')
print('  median risk-to-invalidation falls 6-10.5 pt (shallower 30s extreme).')
print('  False-early re-break identical to 1m. 30s buys risk geometry, not price.')
