#!/usr/bin/env python3
# ======================================================================
# G-FAMILY: TEN EXPLORATORY-DERIVED HYPOTHESES  (G1..G10)
# Declared 2026-08-21, after diag14.py was examined and before this file
# first ran. Because the designs were informed by measurements on THIS
# window, results here are hypothesis-generating regardless of p-values;
# the confirming data can only be capture months 2026-09 onward.
#
# Derivations (what each is built on):
#   G1/G2 RT-050 / RT-100  - diag 12b: adverse extreme median 2.83 ATR,
#         arrives at t=24min vs MFE t=32min; p25 depth 1.35 ATR, so a
#         0.5-1.0 ATR discount limit should fill in most signals.
#         G1: OFH6 signal -> resting limit at close -/+ 0.5*ATR(signal),
#         valid 30 min, fill on first touch, exit 60m after fill.
#         G2: same at 1.0*ATR. (Two-member declared depth family.)
#   G3 DL-20 - enter at market signal+20min ONLY if price is then on the
#         adverse side of the signal close (the discount persisted).
#   G4 ATK-FAIL - diag 1 (+17.5 vs -7.6): OFH6 ctx; opposing attack bar
#         (delta against 5-bar trend, |delta|>=p75) whose FAILURE
#         resolves (trend-side extreme of the attack bar broken within
#         3 bars) -> enter at the resolution bar close, trend direction.
#         R = attack-bar adverse extreme.
#   G5 STK-FADE - diag 4 (fail branch -16.8 for the imbalance side):
#         stacked>=2 bar; within 3 bars a close beyond its OPPOSITE
#         side with no prior continuation -> enter AGAINST the
#         imbalance at that close. Standalone order-flow setup.
#         R = imbalance-side extreme of the stacked bar.
#   G6 STK-GO - continuation branch (+6.2) gated by OFH6 agreement:
#         stacked>=2, extreme broken within 3 bars, direction = OFH6
#         ctx direction -> enter at the continuation bar close.
#         R = stacked bar opposite extreme.
#   G7 CMP-REL - diag 8 (+0.80 vs -0.95): 10-bar envelope <= DEV p25
#         (in ATR) then a release bar (range>=1 ATR, aligned
#         |delta|>=p75) -> follow at its close. Standalone.
#         R = release bar opposite extreme.
#   G8 ABS-GO - diag 3 INVERTS the folklore: high bar-level absorption
#         at a fresh 20-bar extreme precedes CONTINUATION, not
#         reversal. absorption>=p90 at fresh extreme -> follow the
#         breakout side at that close. R = 1 ATR (no structure).
#   G9 N6F - marries the two prior best survivors: N6 impulse (5-bar
#         delta>=p90, displacement>=1 ATR) whose pullback (opposing
#         participation <=30% of impulse) TOUCHES a bullish FVG formed
#         inside the impulse leg -> re-expansion trigger close.
#         R = FVG far boundary.
#   G10 ACC-SWP - diag 13 (monotone acceptance): OFH6 ctx sweep reclaim
#         where the reclaim bar close-location is in the DEV top
#         tercile (accepting) -> entry at reclaim close.
#         R = sweep extreme.
#
# Frozen numbers: p75 |barDelta| and p90 |sd5| from DEV; envelope p25
# from DEV; acceptance tercile from DEV reclaim bars; discount depths
# 0.5/1.0 ATR; DL delay 20 min; all windows 3 bars unless stated; OFH6
# life 30 min; cooldown 30 min chronological; horizon 60m; cost 0.87;
# excess vs side/split baseline; DEV/IR as before; M=10 corrections.
# Limit fills (G1/G2): entry price = the limit; the touch bar
# contributes only ADVERSE residual beyond the limit (favourable inside
# the touch bar is unknowable at 1m and is NOT credited); fill-rate and
# per-signal EV both reported. THIS PROJECT DOES NOT AUTHORIZE LIVE
# TRADING.
# ======================================================================

import os, sys, random, datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ofh6_spec as F6
from ofht_cache import load as load_bars3
from ofht_spec import (TICK, DEV_END, attach_dsum15, aggregate, swings,
                       prevday_levels, Context, entry_ok)

random.seed(41)
COST = 0.87
HORIZON = 60
LIFE = 30
COOL = 30
NAMES = ['G1', 'G2', 'G3', 'G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10']

B = load_bars3()
attach_dsum15(B)
N = len(B)
SIGS = F6.signals(B, F6.eligible(B))
assert len(SIGS) == 783
CTX = Context(SIGS, B)
EB = [j for j in range(N) if entry_ok(B, j)]
DEVB = set(j for j in EB if B[j]['day'] <= DEV_END)


def consec(j, k):
    return B[j]['tmin'] - B[k]['tmin'] == j - k


def q(vals, p):
    s = sorted(vals)
    return s[min(int(len(s) * p), len(s) - 1)] if s else float('nan')


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
    b['stB'] = b['stackedBuyLevels_3x'] or 0
    b['stS'] = b['stackedSellLevels_3x'] or 0

Q_BD75 = q([abs(B[j]['ofBarDelta']) for j in DEVB if B[j]['ofBarDelta'] is not None], .75)
Q_SD90 = q([abs(B[j]['sd5']) for j in DEVB if B[j]['sd5'] is not None], .90)
Q_ABS90 = q([B[j]['absorptionStrengthRaw'] for j in DEVB
             if B[j]['absorptionStrengthRaw'] is not None], .90)

ENV = {}
for j in EB:
    if j >= 10 and consec(j, j - 10) and B[j]['atr']:
        ENV[j] = (max(B[k]['high'] for k in range(j - 10, j))
                  - min(B[k]['low'] for k in range(j - 10, j))) / B[j]['atr']
Q_ENV25 = q([v for j, v in ENV.items() if j in DEVB], .25)

BASE = {}
for sp in ('DEV', 'IR'):
    for d in (1, -1):
        v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in EB
             if ('DEV' if B[j]['day'] <= DEV_END else 'IR') == sp]
        BASE[(sp, d)] = sum(v) / len(v)

print('frozen: bd75 %.0f  sd90 %.0f  abs90 %.1f  env25 %.2f ATR'
      % (Q_BD75, Q_SD90, Q_ABS90, Q_ENV25))

RAW = defaultdict(list)     # name -> (entry_bar_j, d, entry_price, R, is_limit)


def add(name, j, d, px, R):
    if not entry_ok(B, j):
        return
    if R is None:
        R = B[j]['atr']
    if R <= 0:
        return
    RAW[name].append((j, d, px, R))


# ---------------- G1 / G2 / G3 (per-signal, no extra cooldown) --------
FILLS = {'G1': 0, 'G2': 0, 'G3': 0}
for js, d in SIGS:
    if not entry_ok(B, js):
        continue
    e0 = B[js]['close']
    atr = B[js]['atr']
    for name, depth in (('G1', 0.5), ('G2', 1.0)):
        lim = e0 - d * depth * atr
        for k in range(js + 1, min(js + LIFE + 1, N)):
            if not consec(k, js):
                break
            if CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
                break
            c = B[k]
            if (d > 0 and c['low'] <= lim) or (d < 0 and c['high'] >= lim):
                FILLS[name] += 1
                add(name, k, d, lim, atr)
                break
    k = js + 20
    if k < N and consec(k, js) and not CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
        c = B[k]
        if (d > 0 and c['close'] < e0) or (d < 0 and c['close'] > e0):
            FILLS['G3'] += 1
            add('G3', k, d, c['close'], B[k]['atr'])

# ---------------- G4 attack failure -----------------------------------
for j in EB:
    b = B[j]
    if b['disp5'] is None or not b['atr'] or abs(b['disp5']) < 0.5 * b['atr']:
        continue
    t = 1 if b['disp5'] > 0 else -1
    bd = b['ofBarDelta']
    if bd is None or bd * t >= 0 or abs(bd) < Q_BD75:
        continue
    if not CTX.ok_at(t, b['tmin'], LIFE):
        continue
    for k in range(j + 1, min(j + 4, N)):
        if not consec(k, j):
            break
        if (t > 0 and B[k]['low'] < b['low']) or (t < 0 and B[k]['high'] > b['high']):
            break                                    # attack succeeded
        if (t > 0 and B[k]['high'] > b['high']) or (t < 0 and B[k]['low'] < b['low']):
            ref = b['low'] if t > 0 else b['high']
            add('G4', k, t, B[k]['close'],
                (B[k]['close'] - (ref - TICK)) if t > 0 else ((ref + TICK) - B[k]['close']))
            break

# ---------------- G5 / G6 stacked resolution ---------------------------
for j in EB:
    b = B[j]
    for d0, st in ((1, b['stB']), (-1, b['stS'])):
        if st < 2:
            continue
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d0 > 0 and B[k]['high'] > b['high']) or (d0 < 0 and B[k]['low'] < b['low']):
                if CTX.ok_at(d0, B[k]['tmin'], LIFE):
                    ref = b['low'] if d0 > 0 else b['high']
                    add('G6', k, d0, B[k]['close'],
                        (B[k]['close'] - (ref - TICK)) if d0 > 0
                        else ((ref + TICK) - B[k]['close']))
                break
            if (d0 > 0 and B[k]['close'] < b['low']) or (d0 < 0 and B[k]['close'] > b['high']):
                dd = -d0
                ref = b['high'] if d0 > 0 else b['low']
                add('G5', k, dd, B[k]['close'],
                    ((ref + TICK) - B[k]['close']) if dd < 0
                    else (B[k]['close'] - (ref - TICK)))
                break

# ---------------- G7 compression release -------------------------------
for j in EB:
    v = ENV.get(j)
    b = B[j]
    if v is None or v > Q_ENV25 or b['rng'] < b['atr']:
        continue
    d = 1 if b['close'] > b['open'] else -1
    bd = b['ofBarDelta']
    if bd is None or bd * d <= 0 or abs(bd) < Q_BD75:
        continue
    ref = b['low'] if d > 0 else b['high']
    add('G7', j, d, b['close'],
        (b['close'] - (ref - TICK)) if d > 0 else ((ref + TICK) - b['close']))

# ---------------- G8 absorption continuation ---------------------------
for j in EB:
    b = B[j]
    if j < 20 or not consec(j, j - 20) or not b['atr']:
        continue
    ab = b['absorptionStrengthRaw']
    if ab is None or ab < Q_ABS90:
        continue
    hi20 = max(B[k]['high'] for k in range(j - 20, j))
    lo20 = min(B[k]['low'] for k in range(j - 20, j))
    if b['high'] > hi20:
        add('G8', j, 1, b['close'], b['atr'])
    elif b['low'] < lo20:
        add('G8', j, -1, b['close'], b['atr'])

# ---------------- G9 impulse pullback into its own FVG -----------------
for d in (1, -1):
    j = 60
    while j < N:
        b = B[j]
        if (b['sd5'] is None or not b['atr'] or b['disp5'] is None
                or not (abs(b['sd5']) >= Q_SD90 and b['sd5'] * d > 0
                        and b['disp5'] * d >= 1.0 * b['atr'])):
            j += 1
            continue
        zone = None
        for jj in range(j - 4, j + 1):
            if jj < 2 or not consec(jj, jj - 2):
                continue
            a, c3 = B[jj - 2], B[jj]
            if d > 0 and a['high'] < c3['low']:
                zone = (a['high'], c3['low'])
            if d < 0 and a['low'] > c3['high']:
                zone = (c3['high'], a['low'])
        if zone is None:
            j += 1
            continue
        impdelta = abs(b['sd5'])
        opp = 0.0
        touched = False
        fired = False
        for k in range(j + 1, min(j + 11, N)):
            if not consec(k, j):
                break
            c = B[k]
            bd = c['ofBarDelta'] or 0
            if bd * d < 0:
                opp += abs(bd)
            if opp > 0.3 * impdelta:
                break
            if not touched:
                if (d > 0 and c['low'] <= zone[1]) or (d < 0 and c['high'] >= zone[0]):
                    touched = True
            if touched and ((d > 0 and bd > 0 and c['close'] > B[k - 1]['high'])
                            or (d < 0 and bd < 0 and c['close'] < B[k - 1]['low'])):
                far = zone[0] if d > 0 else zone[1]
                add('G9', k, d, c['close'],
                    (c['close'] - (far - TICK)) if d > 0 else ((far + TICK) - c['close']))
                fired = True
                break
        j += 5 if fired else 1

# ---------------- G10 accepting sweep reclaim --------------------------
AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
PDL = prevday_levels(B)
LOWEV = sorted([(t, v) for t, v in SW3L + SW15L])
HIGHEV = sorted([(t, v) for t, v in SW3H + SW15H])
recl_clr_dev = []
G10RAW = []
for evs, s in ((LOWEV, 1), (HIGHEV, -1)):
    slot = None
    ei = 0
    for j in range(N):
        b = B[j]
        while ei < len(evs) and evs[ei][0] <= b['tmin']:
            slot = evs[ei][1]
            ei += 1
        pd = PDL.get(b['day'])
        lvl_pd = (pd[1] if s > 0 else pd[0]) if pd else None
        for lvl_src in (slot,):
            if lvl_src is None:
                continue
            if (s > 0 and b['low'] < lvl_src) or (s < 0 and b['high'] > lvl_src):
                lvl = lvl_src
                slot = None
                ext = b['low'] if s > 0 else b['high']
                for k in range(j, min(j + 6, N)):
                    if k > j and not consec(k, j):
                        break
                    c = B[k]
                    x = c['low'] if s > 0 else c['high']
                    if (s > 0 and x < ext) or (s < 0 and x > ext):
                        ext = x
                    if (s > 0 and c['close'] > lvl) or (s < 0 and c['close'] < lvl):
                        clr = c['clr'] if s > 0 else 1.0 - c['clr']
                        if B[k]['day'] <= DEV_END:
                            recl_clr_dev.append(clr)
                        G10RAW.append((k, s, clr, ext))
                        break
                break
Q_CLR = q(recl_clr_dev, 2.0 / 3)
for k, s, clr, ext in G10RAW:
    if clr < Q_CLR:
        continue
    if not CTX.ok_at(s, B[k]['tmin'], LIFE):
        continue
    add('G10', k, s, B[k]['close'],
        (B[k]['close'] - (ext - TICK)) if s > 0 else ((ext + TICK) - B[k]['close']))

# ---------------- chronological cooldown (event families) --------------
ENT = defaultdict(list)
for name, lst in RAW.items():
    lst.sort(key=lambda x: B[x[0]]['tmin'])
    last = -10 ** 9
    for j, d, px, R in lst:
        if name in ('G4', 'G5', 'G6', 'G7', 'G8', 'G9', 'G10'):
            if B[j]['tmin'] - last < COOL:
                continue
            last = B[j]['tmin']
        ENT[name].append((j, d, px, R))

# ------------------------------------------------------------- geometry
ATR_PAIRS = ((0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0))


def geo(j, d, px, R):
    atr = B[j]['atr']
    sp = 'DEV' if B[j]['day'] <= DEV_END else 'IR'
    mfe = mae = 0.0
    lim = abs(px - B[j]['close']) > 1e-9
    if lim:                       # touch-bar adverse residual only
        resid = (px - B[j]['low']) if d > 0 else (B[j]['high'] - px)
        mae = max(mae, resid)
    ast = {p: 0 for p in ATR_PAIRS}
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        fav = (c['high'] - px) if d > 0 else (px - c['low'])
        adv = (px - c['low']) if d > 0 else (c['high'] - px)
        if fav > mfe:
            mfe = fav
        if adv > mae:
            mae = adv
        for p in ATR_PAIRS:
            if ast[p]:
                continue
            hf, ha = fav >= p[0] * atr, adv >= p[1] * atr
            ast[p] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
    raw = (B[j + HORIZON]['close'] - px) * d
    return {'j': j, 'd': d, 'day': B[j]['day'], 'sp': sp, 'R': R,
            'exc': raw - BASE[(sp, d)], 'mfe': mfe, 'mae': mae, 'a': ast}


G = {nm: [geo(*e) for e in ENT.get(nm, [])] for nm in NAMES}
GF = {nm: [geo(j, -d, B[j]['close'], None or B[j]['atr'])
           for j, d, px, R in ENT.get(nm, [])] for nm in NAMES}
G6b = [geo(j, d, B[j]['close'], B[j]['atr']) for j, d in SIGS if entry_ok(B, j)]


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def ffr(gs, p=(1.0, 1.0)):
    f = sum(1 for g in gs if g['a'][p] == 1)
    a = sum(1 for g in gs if g['a'][p] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


def line(tag, gs):
    if not gs:
        print('  %-24s n=0' % tag)
        return
    ex = [g['exc'] for g in gs]
    mf, ma = med([g['mfe'] for g in gs]), med([g['mae'] for g in gs])
    print('  %-24s n=%5d exc%+8.2f net%+8.2f med%+7.2f ratio%6.3f '
          'ff.5 %4.1f ff1 %4.1f ff2 %4.1f'
          % (tag, len(gs), sum(ex) / len(ex), sum(ex) / len(ex) - COST,
             med(ex) - COST, mf / ma if ma else float('nan'),
             ffr(gs, (0.5, 0.5)), ffr(gs, (1.0, 1.0)), ffr(gs, (2.0, 1.0))))


print('\n' + '=' * 116)
print('G-FAMILY (exploratory-derived; M=10).  OFH6 baseline for reference:')
print('=' * 116)
line('OFH6 immediate', G6b)
for nm in NAMES:
    gs = G[nm]
    line(nm, gs)
    if not gs:
        continue
    for sp in ('DEV', 'IR'):
        line('   ' + sp, [g for g in gs if g['sp'] == sp])
    line('   LONG', [g for g in gs if g['d'] > 0])
    line('   SHORT', [g for g in gs if g['d'] < 0])
    bym = defaultdict(list)
    for g in gs:
        bym[g['day'][:7]].append(g['exc'] - COST)
    pos = sum(1 for v in bym.values() if sum(v) / len(v) > 0)
    net = sorted((g['exc'] - COST for g in gs), reverse=True)
    k5 = max(1, len(net) // 20)
    print('    months %d/%d positive | top5%%(%d tr) %+0.1f of %+0.1f | trades/wk %.1f'
          % (pos, len(bym), k5, sum(net[:k5]), sum(net), len(gs) / 42.0))
    if nm in FILLS:
        print('    fill rate %d/783 = %.0f%%;  per-SIGNAL EV (unfilled=0): %+0.2f pt'
              % (FILLS[nm], 100.0 * FILLS[nm] / 783,
                 sum(g['exc'] - COST for g in gs) / 783.0))

# -------------------------------------------------------------- stats
print('\n' + '=' * 116)
print('FAMILY STATISTICS (M=10, sign-flip by day)')
print('=' * 116)
NS = 2000
praw = {}
for nm in NAMES:
    gs, gf = G[nm], GF[nm]
    if len(gs) < 20:
        continue
    real = sum(g['exc'] for g in gs) / len(gs)
    days = sorted(set(g['day'] for g in gs))
    ge = 0
    for _ in range(NS):
        fl = {d: (1 if random.random() < 0.5 else -1) for d in days}
        acc = 0.0
        for g, h in zip(gs, gf):
            acc += (g if fl[g['day']] > 0 else h)['exc']
        if acc / len(gs) >= real:
            ge += 1
    praw[nm] = ge / float(NS)
order = sorted(praw, key=lambda k: praw[k])
prev = 1.0
bh = {}
for i in range(len(order) - 1, -1, -1):
    nm = order[i]
    qv = praw[nm] * 10.0 / (i + 1)
    prev = min(prev, qv)
    bh[nm] = prev
print('  %-5s %6s %9s %9s %9s' % ('hyp', 'n', 'exc', 'p raw', 'BH q'))
for nm in order:
    gs = G[nm]
    print('  %-5s %6d %+9.2f %9.4f %9.4f'
          % (nm, len(gs), sum(g['exc'] for g in gs) / len(gs), praw[nm], bh[nm]))
alld = sorted(set(g['day'] for nm in praw for g in G[nm]))
fam = []
for _ in range(1000):
    fl = {d: (1 if random.random() < 0.5 else -1) for d in alld}
    bm = -9e9
    for nm in praw:
        acc = 0.0
        for g, h in zip(G[nm], GF[nm]):
            acc += (g if fl[g['day']] > 0 else h)['exc']
        bm = max(bm, acc / len(G[nm]))
    fam.append(bm)
fam.sort()
best = max(praw, key=lambda k: sum(g['exc'] for g in G[k]) / len(G[k]))
rb = sum(g['exc'] for g in G[best]) / len(G[best])
print('  family max: real %+0.2f (%s)  null med %+0.2f p95 %+0.2f  FAMILY-WISE p = %.4f'
      % (rb, best, fam[500], fam[949], sum(1 for x in fam if x >= rb) / 1000.0))
print('\nREMINDER: exploratory-derived family. Confirmation = 2026-09+ months only.')
