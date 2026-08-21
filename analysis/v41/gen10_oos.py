#!/usr/bin/env python3
# ======================================================================
# G-FAMILY RE-TEST ON THE EXTENDED HISTORY
# ======================================================================
# The order-flow capture now spans 2025-08-18 .. 2026-08-19 (~12 months)
# after the backward extension. This re-runs ALL TEN G hypotheses
# (gen10_run.py) with EVERY THRESHOLD UNCHANGED, and reports them on
# three disjoint windows:
#
#   UNSEEN  2025-08-18 .. 2025-11-01   never touched by any fit or design
#   DEV     2025-11-02 .. 2026-03-31   the original threshold fit window
#   IR      2026-04-01 .. 2026-08-19   the original replication window
#
# UNSEEN is the only honest test: the G-family was designed while looking
# at DEV+IR, so those two are in-sample by construction. UNSEEN is still
# EARLIER data, not forward data - a regime difference remains a live
# alternative explanation for anything that fails there.
#
# Thresholds are RECOMPUTED on the original DEV slice and asserted equal
# to the values frozen in gen10_run.py, so this file cannot silently
# refit. Baselines are side-matched WITHIN each window.
# ======================================================================

import os, sys, csv, glob, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ofht_cache import NEED, load as load_old
from ofht_spec import TICK, attach_dsum15, aggregate, swings, Context

random.seed(41)
SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COST, HORIZON, LIFE, COOL = 0.87, 60, 30, 30
SPLIT_NEW = '2025-11-01'        # UNSEEN is <= this
DEV_END = '2026-03-31'
FROZEN = {'bd75': 511.0, 'sd90': 2111.0, 'abs90': 72.4, 'env25': 2.46}


def F(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


# ---- merged history: new capture for <=2025-11-01, existing after ----
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
            if et[:10] > SPLIT_NEW:
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
nnew = len(B)
B.extend(b for b in load_old() if b['day'] > SPLIT_NEW)
B.sort(key=lambda b: b['et'])
N = len(B)
attach_dsum15(B)
print('merged history: %d bars (%d from the new capture)  %s .. %s'
      % (N, nnew, B[0]['et'], B[-1]['et']))


def win(day):
    if day <= SPLIT_NEW:
        return 'UNSEEN'
    return 'DEV' if day <= DEV_END else 'IR'


def consec(j, k):
    return B[j]['tmin'] - B[k]['tmin'] == j - k


def entry_ok(j):
    # MUST match ofht_spec.entry_ok EXACTLY - that is the predicate every
    # original G/N/OFH run used, so it defines the eligible population the
    # frozen thresholds were fitted on. NOTE it does NOT enforce the
    # ">=30 min after RTH open" rule that the ofht_spec header describes;
    # only ofh6_spec.eligible() (the OFH6 signal gate) enforces that. The
    # mismatch is documented here rather than silently corrected, because
    # changing it would refit every frozen quantile.
    b = B[j]
    if not b['isRth'] or b['atr'] is None or b['atr'] <= 0:
        return False
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
        return False
    if j + HORIZON >= N:
        return False
    return B[j + HORIZON]['tmin'] - b['tmin'] == HORIZON


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

EB = [j for j in range(N) if entry_ok(j)]
BASE = {}
for w in ('UNSEEN', 'DEV', 'IR'):
    for d in (1, -1):
        v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in EB if win(B[j]['day']) == w]
        BASE[(w, d)] = sum(v) / len(v)

ENVR = {}
for j in EB:
    if j >= 10 and consec(j, j - 10):
        ENVR[j] = (max(B[k]['high'] for k in range(j - 10, j))
                   - min(B[k]['low'] for k in range(j - 10, j))) / B[j]['atr']


def q(vals, p):
    s = sorted(vals)
    return s[min(int(len(s) * p), len(s) - 1)] if s else float('nan')


DEVB = [j for j in EB if win(B[j]['day']) == 'DEV']
TH = {'bd75': q([abs(B[j]['ofBarDelta']) for j in DEVB if B[j]['ofBarDelta'] is not None], .75),
      'sd90': q([abs(B[j]['sd5']) for j in DEVB if B[j]['sd5'] is not None], .90),
      'abs90': q([B[j]['absorptionStrengthRaw'] for j in DEVB
                  if B[j]['absorptionStrengthRaw'] is not None], .90),
      'env25': q([ENVR[j] for j in DEVB if j in ENVR], .25)}
print('thresholds recomputed on the original DEV slice: ' +
      '  '.join('%s %.2f (frozen %.2f)' % (k, TH[k], FROZEN[k]) for k in TH))
for k in TH:
    assert abs(TH[k] - FROZEN[k]) < max(0.02 * abs(FROZEN[k]), 0.05), \
        'threshold drift on %s: %.3f vs frozen %.3f' % (k, TH[k], FROZEN[k])
print('  -> all within tolerance of the frozen values; no refit occurred.')
Q_BD75, Q_SD90, Q_ABS90, Q_ENV25 = TH['bd75'], TH['sd90'], TH['abs90'], TH['env25']

# ---------------- frozen OFH6 stream on merged history -----------------
SIGS = []
last = -10 ** 9
for j in range(N):
    b = B[j]
    if (not b['isRth'] or b['dsum15'] is None or not b['atr'] or b['atr'] <= 0
            or b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < 30
            or b['minutesToRthClose'] is None or b['minutesToRthClose'] < 90):
        continue
    if j + 90 >= N or B[j + 90]['tmin'] - b['tmin'] != 90:
        continue
    if abs(b['dsum15']) < 3380.0 or b['tmin'] - last < 30:
        continue
    last = b['tmin']
    SIGS.append((j, 1 if b['dsum15'] > 0 else -1))
CTX = Context(SIGS, B)
sw = defaultdict(int)
for j, d in SIGS:
    sw[win(B[j]['day'])] += 1
print('frozen OFH6 signals: %d total  (UNSEEN %d / DEV %d / IR %d)'
      % (len(SIGS), sw['UNSEEN'], sw['DEV'], sw['IR']))

RAW = defaultdict(list)


def add(name, j, d, px=None, R=None):
    if not entry_ok(j):
        return
    if R is None:
        R = B[j]['atr']
    if R <= 0:
        return
    RAW[name].append((j, d, px, R))


# ---------------- G1 / G2 / G3 ----------------
FILLS = defaultdict(lambda: defaultdict(int))
for js, d in SIGS:
    if not entry_ok(js):
        continue
    w = win(B[js]['day'])
    e0, atr = B[js]['close'], B[js]['atr']
    for name, depth in (('G1', 0.5), ('G2', 1.0)):
        lim = e0 - d * depth * atr
        for k in range(js + 1, min(js + LIFE + 1, N)):
            if not consec(k, js) or CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
                break
            c = B[k]
            if (d > 0 and c['low'] <= lim) or (d < 0 and c['high'] >= lim):
                FILLS[name][w] += 1
                add(name, k, d, lim, atr)
                break
    k = js + 20
    if k < N and consec(k, js) and not CTX.opposite_in(d, B[js]['tmin'], B[k]['tmin']):
        if (d > 0 and B[k]['close'] < e0) or (d < 0 and B[k]['close'] > e0):
            FILLS['G3'][w] += 1
            add('G3', k, d, B[k]['close'], B[k]['atr'])

# ---------------- G4 attack failure ----------------
for j in EB:
    b = B[j]
    if b['disp5'] is None or abs(b['disp5']) < 0.5 * b['atr']:
        continue
    t = 1 if b['disp5'] > 0 else -1
    bd = b['ofBarDelta']
    if bd is None or bd * t >= 0 or abs(bd) < Q_BD75 or not CTX.ok_at(t, b['tmin'], LIFE):
        continue
    for k in range(j + 1, min(j + 4, N)):
        if not consec(k, j):
            break
        if (t > 0 and B[k]['low'] < b['low']) or (t < 0 and B[k]['high'] > b['high']):
            break
        if (t > 0 and B[k]['high'] > b['high']) or (t < 0 and B[k]['low'] < b['low']):
            ref = b['low'] if t > 0 else b['high']
            add('G4', k, t, None, (B[k]['close'] - (ref - TICK)) if t > 0
                else ((ref + TICK) - B[k]['close']))
            break

# ---------------- G5 / G6 stacked resolution ----------------
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
                    add('G6', k, d0, None, (B[k]['close'] - (ref - TICK)) if d0 > 0
                        else ((ref + TICK) - B[k]['close']))
                break
            if (d0 > 0 and B[k]['close'] < b['low']) or (d0 < 0 and B[k]['close'] > b['high']):
                dd = -d0
                ref = b['high'] if d0 > 0 else b['low']
                add('G5', k, dd, None, ((ref + TICK) - B[k]['close']) if dd < 0
                    else (B[k]['close'] - (ref - TICK)))
                break

# ---------------- G7 compression release ----------------
for j in EB:
    v = ENVR.get(j)
    b = B[j]
    if v is None or v > Q_ENV25 or b['rng'] < b['atr']:
        continue
    d = 1 if b['close'] > b['open'] else -1
    bd = b['ofBarDelta']
    if bd is None or bd * d <= 0 or abs(bd) < Q_BD75:
        continue
    ref = b['low'] if d > 0 else b['high']
    add('G7', j, d, None, (b['close'] - (ref - TICK)) if d > 0 else ((ref + TICK) - b['close']))

# ---------------- G8 absorption continuation ----------------
for j in EB:
    b = B[j]
    if j < 20 or not consec(j, j - 20):
        continue
    ab = b['absorptionStrengthRaw']
    if ab is None or ab < Q_ABS90:
        continue
    hi20 = max(B[k]['high'] for k in range(j - 20, j))
    lo20 = min(B[k]['low'] for k in range(j - 20, j))
    if b['high'] > hi20:
        add('G8', j, 1, None, b['atr'])
    elif b['low'] < lo20:
        add('G8', j, -1, None, b['atr'])

# ---------------- G9 impulse pullback into its own FVG ----------------
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
        impd = abs(b['sd5'])
        opp = 0.0
        touched = fired = False
        for k in range(j + 1, min(j + 11, N)):
            if not consec(k, j):
                break
            c = B[k]
            bd = c['ofBarDelta'] or 0
            if bd * d < 0:
                opp += abs(bd)
            if opp > 0.3 * impd:
                break
            if not touched:
                if (d > 0 and c['low'] <= zone[1]) or (d < 0 and c['high'] >= zone[0]):
                    touched = True
            if touched and ((d > 0 and bd > 0 and c['close'] > B[k - 1]['high'])
                            or (d < 0 and bd < 0 and c['close'] < B[k - 1]['low'])):
                far = zone[0] if d > 0 else zone[1]
                add('G9', k, d, None, (c['close'] - (far - TICK)) if d > 0
                    else ((far + TICK) - c['close']))
                fired = True
                break
        j += 5 if fired else 1

# ---------------- G10 accepting sweep reclaim ----------------
AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
G10RAW = []
devclr = []
for evs, s in ((sorted(SW3L + SW15L), 1), (sorted(SW3H + SW15H), -1)):
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
                    if win(B[k]['day']) == 'DEV':
                        devclr.append(clr)
                    G10RAW.append((k, s, clr, ext))
                    break
Q_CLR = q(devclr, 2.0 / 3)
for k, s, clr, ext in G10RAW:
    if clr < Q_CLR or not CTX.ok_at(s, B[k]['tmin'], LIFE):
        continue
    add('G10', k, s, None, (B[k]['close'] - (ext - TICK)) if s > 0
        else ((ext + TICK) - B[k]['close']))
print('G10 acceptance tercile from DEV reclaims: %.4f' % Q_CLR)

# ---------------- chronological cooldown ----------------
ENT = defaultdict(list)
for name, lst in RAW.items():
    lst.sort(key=lambda x: B[x[0]]['tmin'])
    last = -10 ** 9
    for j, d, px, R in lst:
        if name not in ('G1', 'G2', 'G3'):
            if B[j]['tmin'] - last < COOL:
                continue
            last = B[j]['tmin']
        ENT[name].append((j, d, px, R))

ATR_PAIRS = ((0.5, 0.5), (1.0, 1.0), (2.0, 1.0))


def geo(j, d, px, R):
    px = B[j]['close'] if px is None else px
    atr = B[j]['atr']
    w = win(B[j]['day'])
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
    return {'j': j, 'd': d, 'day': B[j]['day'], 'w': w, 'exc': raw - BASE[(w, d)],
            'mfe': mfe, 'mae': mae, 'a': st}


NAMES = ['G%d' % k for k in range(1, 11)]
G = {nm: [geo(*e) for e in ENT.get(nm, [])] for nm in NAMES}
GF = {nm: [geo(j, -d, None, R) for j, d, px, R in ENT.get(nm, [])] for nm in NAMES}
SIG6 = [geo(j, d, None, B[j]['atr']) for j, d in SIGS if entry_ok(j)]


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def ffr(gs, p=(1.0, 1.0)):
    f = sum(1 for g in gs if g['a'][p] == 1)
    a = sum(1 for g in gs if g['a'][p] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


def stat(gs):
    if not gs:
        return None
    ex = [g['exc'] for g in gs]
    mf, ma = med([g['mfe'] for g in gs]), med([g['mae'] for g in gs])
    return (len(gs), sum(ex) / len(ex), med(ex) - COST,
            mf / ma if ma else float('nan'), ffr(gs))


print('\n' + '=' * 122)
print('G-FAMILY ON THE EXTENDED HISTORY - frozen rules, three disjoint windows')
print('=' * 122)
print('  %-5s | %-28s | %-28s | %-28s' % ('', 'UNSEEN 2025-08..11-01',
                                          'DEV 2025-11..2026-03', 'IR 2026-04..08'))
print('  %-5s | %5s %7s %7s %5s | %5s %7s %7s %5s | %5s %7s %7s %5s'
      % ('hyp', 'n', 'exc', 'ratio', 'ff1', 'n', 'exc', 'ratio', 'ff1',
         'n', 'exc', 'ratio', 'ff1'))
s6 = {w: stat([g for g in SIG6 if g['w'] == w]) for w in ('UNSEEN', 'DEV', 'IR')}
row = '  %-5s |' % 'OFH6'
for w in ('UNSEEN', 'DEV', 'IR'):
    s = s6[w]
    row += ' %5d %+7.2f %7.3f %5.1f |' % (s[0], s[1], s[3], s[4]) if s else '   n/a |'
print(row)
for nm in NAMES:
    row = '  %-5s |' % nm
    for w in ('UNSEEN', 'DEV', 'IR'):
        s = stat([g for g in G[nm] if g['w'] == w])
        row += ' %5d %+7.2f %7.3f %5.1f |' % (s[0], s[1], s[3], s[4]) if s else '     0       -       -     - |'
    print(row)

print('\n' + '=' * 122)
print('UNSEEN-WINDOW VERDICT (the only out-of-sample column)')
print('=' * 122)
NS = 4000
praw = {}
for nm in NAMES:
    gs = [g for g in G[nm] if g['w'] == 'UNSEEN']
    gf = [h for g, h in zip(G[nm], GF[nm]) if g['w'] == 'UNSEEN']
    if len(gs) < 15:
        print('  %-5s n=%d - too few on the unseen window to judge' % (nm, len(gs)))
        continue
    mu = sum(g['exc'] for g in gs) / len(gs)
    dys = sorted(set(g['day'] for g in gs))
    ge = 0
    for _ in range(NS):
        fl = {d: (1 if random.random() < 0.5 else -1) for d in dys}
        acc = 0.0
        for g, h in zip(gs, gf):
            acc += (g if fl[g['day']] > 0 else h)['exc']
        if acc / len(gs) >= mu:
            ge += 1
    praw[nm] = ge / float(NS)
    bd = defaultdict(list)
    for g in gs:
        bd[g['day']].append(g['exc'])
    pools = list(bd.values())
    bs = []
    for _ in range(2000):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        bs.append(sum(s) / len(s))
    bs.sort()
    seen = [g for g in G[nm] if g['w'] != 'UNSEEN']
    seenmu = sum(g['exc'] for g in seen) / len(seen) if seen else float('nan')
    print('  %-5s n=%4d  exc %+7.2f (seen %+7.2f)  net %+7.2f  CI [%+7.2f,%+7.2f]  p %.4f  %s'
          % (nm, len(gs), mu, seenmu, mu - COST, bs[50], bs[1949], praw[nm],
             'HOLDS' if mu > 0 and seenmu > 0 else 'FAILS'))
if praw:
    order = sorted(praw, key=lambda k: praw[k])
    prev = 1.0
    bh = {}
    for i in range(len(order) - 1, -1, -1):
        nm = order[i]
        qv = praw[nm] * len(order) / (i + 1)
        prev = min(prev, qv)
        bh[nm] = prev
    print('  BH q (M=%d): ' % len(order)
          + '  '.join('%s %.3f' % (nm, bh[nm]) for nm in order))

print('\n  limit-family per-SIGNAL EV (unfilled counted as 0):')
for nm in ('G1', 'G2', 'G3'):
    for w in ('UNSEEN', 'DEV', 'IR'):
        gs = [g for g in G[nm] if g['w'] == w]
        ns = sw[w]
        base6 = [g for g in SIG6 if g['w'] == w]
        if not gs or not ns:
            continue
        print('    %-3s %-6s fill %3d/%3d = %3.0f%%   per-signal %+6.2f   (OFH6 immediate %+6.2f)'
              % (nm, w, FILLS[nm][w], ns, 100.0 * FILLS[nm][w] / ns,
                 sum(g['exc'] - COST for g in gs) / ns,
                 sum(g['exc'] - COST for g in base6) / len(base6)))
