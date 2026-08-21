#!/usr/bin/env python3
# ======================================================================
# UNSEEN-WINDOW EVALUATION - 2025-08-18 .. 2025-11-01
# ======================================================================
# The new capture (2025-08-18 .. 2025-11-28) extends the order-flow
# history BACKWARD. Everything before 2025-11-02 is data that no rule,
# threshold or design decision in this repository has ever touched:
# every DEV quantile was fit on 2025-11..2026-03 and every hypothesis
# was designed while looking at 2025-11..2026-08.
#
# WHAT THIS IS:  a genuine unseen holdout for the frozen shelf.
# WHAT IT IS NOT: prospective validation. It is earlier data, so a
#   regime difference is a live alternative explanation for any result,
#   and it cannot rule out that the hypotheses suit 2025-2026 markets
#   in general. Only 2026-09+ months can do that.
#
# INTEGRITY (verified before running): the 26,488 overlapping November
# bars are byte-identical between the old and new captures on price,
# volume, bid/ask, delta and ATR-independent columns. Differences exist
# only in f_atr (19 bars, warm-up) and f_profileVah/Val (value-area
# tie-breaking, 1-2 ticks). No shelved hypothesis reads profile columns.
#
# RULE: every threshold below is the ORIGINAL frozen value from the
# 2025-11..2026-03 DEV fit. NOTHING is refit on this window. Baseline is
# side-matched within the unseen window itself, so its own drift cannot
# pose as edge.
# ======================================================================

import os, sys, csv, glob, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ofh6_spec as F6
from ofht_cache import NEED
from ofht_spec import (TICK, attach_dsum15, aggregate, swings, prevday_levels,
                       Context)

random.seed(41)
SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COST = 0.87
HORIZON = 60
LIFE = 30
COOL = 30
UNSEEN_END = '2025-11-01'

# ---- FROZEN constants, copied verbatim from the original fits --------
THR_OFH6 = 3380.0          # ofh6_spec.THRESHOLD
Q_BD75 = 511.0             # DEV p75 |barDelta|      (ofn_run / offvg_run)
Q_SD90 = 2111.0            # DEV p90 |5-bar delta|   (ofn_run)
Q_ABS90 = 72.4             # DEV p90 absorption      (ofn_run)
Q_ENV25 = 2.46             # DEV p25 10-bar envelope in ATR (gen10_run)
DISP_ATR, DISP_BODY, DISP_CLR = 1.00, 0.50, 0.70


def F(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


B = []
for f in sorted(glob.glob(SCR + '/ofnew/v4_1_orderflow_MNQ_v41of_*.csv')):
    with open(f, newline='') as fh:
        r = csv.reader(fh)
        h = next(r)
        i = {c: k for k, c in enumerate(h)}
        for row in r:
            if len(row) != len(h):
                continue
            et = row[i['f_barCloseEt']]
            if et[:10] > UNSEEN_END:
                continue
            d = {}
            for c in NEED:
                v = row[i[c]]
                d[c[2:]] = (v == 'TRUE') if v in ('TRUE', 'FALSE') else F(v)
            if d['high'] is None or d['atr'] is None or d['close'] is None:
                continue
            d['et'] = et
            d['day'] = et[:10]
            d['tmin'] = (int(et[:4]) * 527040 + int(et[5:7]) * 44640
                         + int(et[8:10]) * 1440 + int(et[11:13]) * 60 + int(et[14:16]))
            B.append(d)
B.sort(key=lambda b: b['et'])
N = len(B)
attach_dsum15(B)
days = sorted(set(b['day'] for b in B))
print('UNSEEN WINDOW: %d bars, %d calendar days, %s .. %s'
      % (N, len(days), B[0]['et'], B[-1]['et']))


def consec(j, k):
    return B[j]['tmin'] - B[k]['tmin'] == j - k


def entry_ok(j):
    b = B[j]
    if not b['isRth'] or not b['atr'] or b['atr'] <= 0:
        return False
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
        return False
    if b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < 30:
        return False
    if j + HORIZON >= N:
        return False
    return B[j + HORIZON]['tmin'] - b['tmin'] == HORIZON


EB = [j for j in range(N) if entry_ok(j)]
BASE = {}
for d in (1, -1):
    v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in EB]
    BASE[d] = sum(v) / len(v)
print('eligible entry bars %d   side-matched 60m baseline L %+0.3f / S %+0.3f'
      % (len(EB), BASE[1], BASE[-1]))

for j in range(N):
    b = B[j]
    ok5 = j >= 5 and consec(j, j - 5)
    b['sd5'] = (sum(B[k]['ofBarDelta'] or 0 for k in range(j - 4, j + 1))
                if ok5 and all(B[k]['ofBarDelta'] is not None
                               for k in range(j - 4, j + 1)) else None)
    b['disp5'] = (b['close'] - B[j - 5]['close']) if ok5 else None
    rng = b['high'] - b['low']
    b['rng'] = rng
    b['clr'] = (b['close'] - b['low']) / rng if rng > 0 else 0.5
    b['stB'] = b['stackedBuyLevels_3x'] or 0
    b['stS'] = b['stackedSellLevels_3x'] or 0

# ------------------------------------------------ frozen OFH6 stream
SIGS = []
last = -10 ** 9
for j in range(N):
    b = B[j]
    if not b['isRth'] or b['dsum15'] is None or not b['atr'] or b['atr'] <= 0:
        continue
    if b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < 30:
        continue
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < 90:
        continue
    if j + 90 >= N or B[j + 90]['tmin'] - b['tmin'] != 90:
        continue
    if abs(b['dsum15']) < THR_OFH6 or b['tmin'] - last < 30:
        continue
    last = b['tmin']
    SIGS.append((j, 1 if b['dsum15'] > 0 else -1))
CTX = Context(SIGS, B)
print('frozen OFH6 signals in the unseen window: %d' % len(SIGS))

ATR_PAIRS = ((0.5, 0.5), (1.0, 1.0), (2.0, 1.0))


def geo(j, d, px=None, R=None):
    px = B[j]['close'] if px is None else px
    atr = B[j]['atr']
    mfe = mae = 0.0
    if abs(px - B[j]['close']) > 1e-9:
        mae = max(mae, (px - B[j]['low']) if d > 0 else (B[j]['high'] - px))
    st = {p: 0 for p in ATR_PAIRS}
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        fav = (c['high'] - px) if d > 0 else (px - c['low'])
        adv = (px - c['low']) if d > 0 else (c['high'] - px)
        mfe = max(mfe, fav)
        mae = max(mae, adv)
        for p in ATR_PAIRS:
            if st[p]:
                continue
            hf, ha = fav >= p[0] * atr, adv >= p[1] * atr
            st[p] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
    raw = (B[j + HORIZON]['close'] - px) * d
    return {'j': j, 'd': d, 'day': B[j]['day'], 'exc': raw - BASE[d],
            'mfe': mfe, 'mae': mae, 'a': st, 'R': R}


RAW = defaultdict(list)


def add(name, j, d, px=None, R=None):
    if not entry_ok(j):
        return
    RAW[name].append((j, d, px, R))


# ---------------- OFH6 immediate ----------------
for j, d in SIGS:
    add('OFH6', j, d)

# ---------------- G1 / G2 limit entries ----------------
FILLS = {'G1': 0, 'G2': 0}
for js, d in SIGS:
    if not entry_ok(js):
        continue
    e0, atr = B[js]['close'], B[js]['atr']
    for name, depth in (('G1', 0.5), ('G2', 1.0)):
        lim = e0 - d * depth * atr
        for k in range(js + 1, min(js + LIFE + 1, N)):
            if not consec(k, js) or CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
                break
            c = B[k]
            if (d > 0 and c['low'] <= lim) or (d < 0 and c['high'] >= lim):
                FILLS[name] += 1
                add(name, k, d, lim, atr)
                break

# ---------------- G4 attack failure ----------------
for j in EB:
    b = B[j]
    if b['disp5'] is None or abs(b['disp5']) < 0.5 * b['atr']:
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
            break
        if (t > 0 and B[k]['high'] > b['high']) or (t < 0 and B[k]['low'] < b['low']):
            ref = b['low'] if t > 0 else b['high']
            add('G4', k, t, None,
                (B[k]['close'] - (ref - TICK)) if t > 0 else ((ref + TICK) - B[k]['close']))
            break

# ---------------- G6 stacked continuation + OFH6 ----------------
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
                    add('G6', k, d0, None,
                        (B[k]['close'] - (ref - TICK)) if d0 > 0
                        else ((ref + TICK) - B[k]['close']))
                break
            if (d0 > 0 and B[k]['close'] < b['low']) or (d0 < 0 and B[k]['close'] > b['high']):
                break

# ---------------- OF-N3 absorption at fresh swing extreme ----------------
AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
for evs, d in ((sorted(SW3H + SW15H), -1), (sorted(SW3L + SW15L), 1)):
    ei = 0
    active = []
    for j in range(N):
        b = B[j]
        while ei < len(evs) and evs[ei][0] <= b['tmin']:
            active.append(evs[ei][1])
            ei += 1
        if len(active) > 12:
            active = active[-12:]
        if not b['atr'] or b['atr'] <= 0:
            continue
        hitl = [lv for lv in active
                if (d < 0 and b['high'] >= lv) or (d > 0 and b['low'] <= lv)]
        if not hitl:
            continue
        active = [lv for lv in active if lv not in hitl]
        ab = b['absorptionStrengthRaw']
        if ab is None or ab < Q_ABS90:
            continue
        if not ((b['close'] < max(hitl)) if d < 0 else (b['close'] > min(hitl))):
            continue
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d < 0 and B[k]['close'] < b['low']) or (d > 0 and B[k]['close'] > b['high']):
                ref = (max(B[i]['high'] for i in range(j, k + 1)) if d < 0
                       else min(B[i]['low'] for i in range(j, k + 1)))
                add('N3', k, d, None,
                    (B[k]['close'] - (ref - TICK)) if d > 0 else ((ref + TICK) - B[k]['close']))
                break

# ---------------- OF-N6 impulse / weak pullback / re-expansion ----------
for d in (1, -1):
    j = 60
    while j < N:
        b = B[j]
        if (b['sd5'] is None or b['disp5'] is None or not b['atr']
                or not ((b['sd5'] >= Q_SD90 and b['disp5'] >= b['atr']) if d > 0
                        else (b['sd5'] <= -Q_SD90 and b['disp5'] <= -b['atr']))):
            j += 1
            continue
        impd = abs(b['sd5'])
        pb = None
        opp = 0.0
        fired = False
        for k in range(j + 1, min(j + 11, N)):
            if not consec(k, j):
                break
            c = B[k]
            e = c['low'] if d > 0 else c['high']
            if pb is None or (d > 0 and e < pb) or (d < 0 and e > pb):
                pb = e
            bd = c['ofBarDelta'] or 0
            if bd * d < 0:
                opp += abs(bd)
            depth = (b['close'] - pb) if d > 0 else (pb - b['close'])
            if opp > 0.3 * impd:
                break
            if depth < 0.3 * b['atr']:
                continue
            if (d > 0 and bd > 0 and c['close'] > B[k - 1]['high']) or \
               (d < 0 and bd < 0 and c['close'] < B[k - 1]['low']):
                add('N6', k, d, None,
                    (c['close'] - (pb - TICK)) if d > 0 else ((pb + TICK) - c['close']))
                fired = True
                break
        j += 5 if fired else 1

# ---------------- OFH13 / OFH14 FVG mitigation ----------------
FVG_AT = defaultdict(list)
for j in range(2, N):
    if not consec(j, j - 2):
        continue
    a, c2, c3 = B[j - 2], B[j - 1], B[j]
    if not c2['atr'] or c2['atr'] <= 0:
        continue
    if a['high'] < c3['low']:
        d, zLo, zHi = 1, a['high'], c3['low']
    elif a['low'] > c3['high']:
        d, zLo, zHi = -1, c3['high'], a['low']
    else:
        continue
    rng = c2['high'] - c2['low']
    if rng <= 0:
        continue
    body = abs(c2['close'] - c2['open'])
    clr = (c2['close'] - c2['low']) / rng
    if not (rng >= DISP_ATR * c2['atr'] and body / rng >= DISP_BODY
            and ((d > 0 and clr >= DISP_CLR and c3['close'] > a['open'])
                 or (d < 0 and clr <= 1 - DISP_CLR and c3['close'] < a['open']))):
        continue
    FVG_AT[j].append({'j': j, 'd': d, 'zLo': zLo, 'zHi': zHi,
                      'mid': (zLo + zHi) / 2.0})

for js, d in SIGS:
    ts = B[js]['tmin']
    prev = ts
    for k in range(js + 1, N):
        if B[k]['tmin'] != prev + 1:
            break
        prev = B[k]['tmin']
        if B[k]['tmin'] - ts > LIFE:
            break
        got = None
        for f in FVG_AT.get(k, ()):
            if f['d'] == d:
                got = f
                break
        if got is None:
            continue
        zLo, zHi, mid = got['zLo'], got['zHi'], got['mid']
        far = zLo if d > 0 else zHi
        touched = False
        ext = None
        flow = False
        p2 = B[k]['tmin']
        for m in range(k + 1, N):
            if B[m]['tmin'] != p2 + 1:
                break
            p2 = B[m]['tmin']
            if B[m]['tmin'] - ts > LIFE:
                break
            c = B[m]
            if (d > 0 and c['close'] < zLo) or (d < 0 and c['close'] > zHi):
                break
            if not touched:
                if (d > 0 and c['low'] <= zHi) or (d < 0 and c['high'] >= zLo):
                    touched = True
                    ext = c['low'] if d > 0 else c['high']
            else:
                x = c['low'] if d > 0 else c['high']
                if (d > 0 and x < ext) or (d < 0 and x > ext):
                    ext = x
            if not touched:
                continue
            bd = c['ofBarDelta']
            if bd is not None and abs(bd) >= Q_BD75 and bd * d < 0:
                flow = True
            if (d > 0 and c['close'] > mid) or (d < 0 and c['close'] < mid):
                span = zHi - zLo
                depth = ((zHi - ext) / span) if d > 0 else ((ext - zLo) / span)
                R = (c['close'] - (far - TICK)) if d > 0 else ((far + TICK) - c['close'])
                add('OFH14', m, d, None, R)
                if flow and depth < 1.0:
                    add('OFH13', m, d, None, R)
                break
        break

# ---------------- chronological cooldown ----------------
ENT = defaultdict(list)
for name, lst in RAW.items():
    lst.sort(key=lambda x: B[x[0]]['tmin'])
    last = -10 ** 9
    for j, d, px, R in lst:
        if name in ('G4', 'G6', 'N3', 'N6', 'OFH13', 'OFH14'):
            if B[j]['tmin'] - last < COOL:
                continue
            last = B[j]['tmin']
        ENT[name].append((j, d, px, R))

G = {nm: [geo(j, d, px, R) for j, d, px, R in ENT.get(nm, [])]
     for nm in ('OFH6', 'G1', 'G2', 'G4', 'G6', 'N3', 'N6', 'OFH13', 'OFH14')}
GF = {nm: [geo(j, -d, None, None) for j, d, px, R in ENT.get(nm, [])] for nm in G}


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def ffr(gs, p=(1.0, 1.0)):
    f = sum(1 for g in gs if g['a'][p] == 1)
    a = sum(1 for g in gs if g['a'][p] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


PRIOR = {'OFH6': 8.19, 'G1': 10.66, 'G2': 9.63, 'G4': 14.65, 'G6': 6.67,
         'N3': 15.48, 'N6': 6.49, 'OFH13': 19.19, 'OFH14': 8.43}
PRIORFF = {'OFH6': 48.1, 'G1': 52.6, 'G2': 54.7, 'G4': 41.4, 'G6': 46.5,
           'N3': 52.5, 'N6': 48.9, 'OFH13': 46.2, 'OFH14': 49.2}

print('\n' + '=' * 118)
print('FROZEN SHELF SCORED ON THE UNSEEN WINDOW (nothing refit)')
print('=' * 118)
print('  %-7s %6s %9s %9s %9s %8s %8s %8s %8s'
      % ('hyp', 'n', 'exc NEW', 'exc SEEN', 'net NEW', 'med', 'ratio', 'ff1 NEW', 'ff1 SEEN'))
NS = 4000
rows = []
for nm in ('OFH6', 'G1', 'G2', 'G4', 'G6', 'N3', 'N6', 'OFH13', 'OFH14'):
    gs = G[nm]
    if not gs:
        print('  %-7s n=0' % nm)
        continue
    ex = [g['exc'] for g in gs]
    mu = sum(ex) / len(ex)
    mf, ma = med([g['mfe'] for g in gs]), med([g['mae'] for g in gs])
    print('  %-7s %6d %+9.2f %+9.2f %+9.2f %+8.2f %8.3f %8.1f %8.1f'
          % (nm, len(gs), mu, PRIOR[nm], mu - COST, med(ex) - COST,
             mf / ma if ma else float('nan'), ffr(gs), PRIORFF[nm]))
    rows.append((nm, gs, GF[nm], mu))

print('\n  sign-flip p and day-clustered CI on the unseen window:')
for nm, gs, gf, mu in rows:
    dys = sorted(set(g['day'] for g in gs))
    ge = 0
    for _ in range(NS):
        fl = {d: (1 if random.random() < 0.5 else -1) for d in dys}
        acc = 0.0
        for g, h in zip(gs, gf):
            acc += (g if fl[g['day']] > 0 else h)['exc']
        if acc / len(gs) >= mu:
            ge += 1
    bd = defaultdict(list)
    for g in gs:
        bd[g['day']].append(g['exc'])
    pools = list(bd.values())
    bs = []
    for _ in range(2000):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        bs.append(sum(s) / len(s))
    bs.sort()
    print('    %-7s p %.4f   CI [%+7.2f, %+7.2f]   %s'
          % (nm, ge / float(NS), bs[50], bs[1949],
             'sign HOLDS' if mu > 0 else 'sign FLIPS vs seen window'))

print('\n  per-SIGNAL EV for the limit family (unfilled = 0), %d signals:' % len(SIGS))
for nm in ('G1', 'G2'):
    gs = G[nm]
    if gs:
        print('    %-3s fill %d/%d = %.0f%%   per-signal EV %+0.2f pt   (OFH6 immediate %+0.2f)'
              % (nm, FILLS[nm], len(SIGS), 100.0 * FILLS[nm] / len(SIGS),
                 sum(g['exc'] - COST for g in gs) / len(SIGS),
                 sum(g['exc'] - COST for g in G['OFH6']) / len(SIGS)))

print('\n  month-by-month net (unseen window):')
for nm, gs, _, _ in rows:
    bym = defaultdict(list)
    for g in gs:
        bym[g['day'][:7]].append(g['exc'] - COST)
    print('    %-7s ' % nm + '  '.join('%s %+7.2f(%d)' % (m[2:], sum(v) / len(v), len(v))
                                       for m, v in sorted(bym.items())))
