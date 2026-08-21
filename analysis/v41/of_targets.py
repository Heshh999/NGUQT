#!/usr/bin/env python3
# CAN ORDER FLOW OR LIQUIDITY ZONES HELP WITH TAKE-PROFITS?
#
# Two separate questions, deliberately kept apart:
#
#   Q1  Do the VOLUMETRIC features predict MAGNITUDE (how far a trade
#       runs) beyond what plain bar shape already predicts? The structure
#       work established bar shape gets rho ~0.23 against MFE. The only
#       thing worth reporting here is the INCREMENT over that, so every
#       order-flow feature is scored against the RESIDUAL after bar shape
#       has been taken out.
#
#   Q2  Do liquidity zones (developing-session POC / VAH / VAL) behave
#       like magnets or barriers - i.e. is a target that sits ON a level
#       reached more often, or continued through less often, than a
#       target at the SAME DISTANCE that does not sit on a level?
#
# Q2 is the whole reason this is not a trivial test. Touch probability is
# dominated by distance. "Price hits the POC 70% of the time" is not
# evidence of anything if the POC happens to sit 0.4 ATR away. So every
# comparison here is DISTANCE-MATCHED: within a distance bucket, targets
# that coincide with a level are compared against targets that do not.
# And the whole thing is re-run with every level SHIFTED by a fixed
# offset - a placebo level. If the shifted levels look like magnets too,
# the effect is geometry, not liquidity.
#
# This capture is a raw 1m path, so first-touch and stop-vs-target races
# are EXACT here. No ordering proxy - that mistake is not repeated.
#
# LEDGER: the order-flow layer has no sealed holdout left. It was spent
# on the $1,000 P&L illustration by explicit user decision on 2026-08-20.
# DEV/VAL below is a within-window replication check, NOT out-of-sample.
# The structure HOLD (2024-07 onward) is not touched by this script.

import csv, glob, os, pickle, random, math
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
D = os.path.join(SCR, 'of2')
CACHE = os.path.join(SCR, 'of_bars.pkl')
COST = 0.87
HORIZON = 90          # minutes of forward path
STOP_ATR = 1.5        # frozen from the earlier stop-family work
random.seed(41)

DEV_END = '2026-03-31'


def F(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


NEED = ['f_barCloseEt', 'f_open', 'f_high', 'f_low', 'f_close', 'f_atr',
        'f_isRth', 'f_minutesToRthClose', 'f_minutesFromRthOpen',
        'f_bodyPctOfRange', 'f_bodyAtr', 'f_rangeAtr', 'f_relVolume',
        'f_ofDeltaPct', 'f_ofCumDeltaSlope', 'f_ofMinDelta', 'f_ofMaxDelta',
        'f_ofRelVolume', 'f_ofBarDelta', 'f_ofTotalVolume',
        'f_buyImbalanceCount_3x', 'f_sellImbalanceCount_3x',
        'f_stackedBuyLevels_3x', 'f_stackedSellLevels_3x',
        'f_maxBuyImbalanceRatio', 'f_maxSellImbalanceRatio',
        'f_absorptionStrengthRaw', 'f_repeatedTradeAtExtreme',
        'f_volumePerUpTick', 'f_volumePerDownTick',
        'f_closeMinusPocPts', 'f_profileReady', 'f_profilePoc',
        'f_profileVah', 'f_profileVal', 'f_profileHvnCount',
        'f_profileLvnCount', 'f_distPocAtr', 'f_insideValueArea']


def load():
    if os.path.exists(CACHE):
        with open(CACHE, 'rb') as fh:
            return pickle.load(fh)
    bars = []
    for f in sorted(glob.glob(os.path.join(D, 'v4_1_orderflow_MNQ_v41of_*.csv'))):
        with open(f, newline='') as fh:
            r = csv.reader(fh)
            h = next(r)
            i = {c: k for k, c in enumerate(h)}
            for row in r:
                if len(row) != len(h):
                    continue
                d = {}
                for c in NEED:
                    v = row[i[c]]
                    d[c[2:]] = (v == 'TRUE') if v in ('TRUE', 'FALSE') else F(v)
                if d['high'] is None or d['atr'] is None:
                    continue
                et = row[i['f_barCloseEt']]
                d['et'] = et
                d['day'] = et[:10]
                # minutes since epoch-ish, for contiguity checks
                d['tmin'] = (int(et[:4]) * 527040 + int(et[5:7]) * 44640
                             + int(et[8:10]) * 1440 + int(et[11:13]) * 60
                             + int(et[14:16]))
                bars.append(d)
    bars.sort(key=lambda b: b['et'])
    with open(CACHE, 'wb') as fh:
        pickle.dump(bars, fh, 2)
    return bars


B = load()
print('bars loaded: %d   %s -> %s' % (len(B), B[0]['et'], B[-1]['et']))

# ---------------------------------------------------------------- events
# Declared BEFORE running: every RTH bar close on a 5-minute boundary,
# at least 30 min into RTH (so the developing profile means something)
# and at least HORIZON minutes before the RTH close (so the whole window
# is inside RTH and no halt sits in it). Both sides evaluated. This is a
# deliberately ENTRY-AGNOSTIC sample: the question is about exits, so the
# entries must not smuggle in an edge.
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
    # forward window must be exactly consecutive minutes
    if B[i + HORIZON]['tmin'] - b['tmin'] != HORIZON:
        continue
    EV.append(i)

print('events (bars): %d   -> event-sides: %d' % (len(EV), 2 * len(EV)))


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


# precompute forward running extremes for each event, once
FWD = {}
for i in EV:
    hi = []
    lo = []
    h = -1e18
    l = 1e18
    for k in range(1, HORIZON + 1):
        c = B[i + k]
        if c['high'] > h:
            h = c['high']
        if c['low'] < l:
            l = c['low']
        hi.append(h)
        lo.append(l)
    FWD[i] = (hi, lo)


def mfe_mae(i, side):
    hi, lo = FWD[i]
    e = B[i]['close']
    if side > 0:
        return hi[-1] - e, e - lo[-1]
    return e - lo[-1], hi[-1] - e


def first_touch(i, side, target):
    """Exact first-touch minute of a price level, or None. side>0 -> above."""
    hi, lo = FWD[i]
    seq = hi if side > 0 else lo
    for k in range(HORIZON):
        if (seq[k] >= target) if side > 0 else (seq[k] <= target):
            return k + 1
    return None


# ===================================================================== Q1
print('\n' + '=' * 100)
print('Q1  DOES ORDER FLOW PREDICT MAGNITUDE BEYOND BAR SHAPE?')
print('=' * 100)

SHAPE = ['bodyPctOfRange', 'bodyAtr', 'rangeAtr']
OF = ['ofRelVolume', 'absDeltaPct', 'absCumDeltaSlope', 'deltaRange',
      'stacked3x', 'imbal3x', 'maxImbalRatio', 'absorptionStrengthRaw',
      'repeatedTradeAtExtreme', 'volPerTick', 'absDistPocAtr',
      'profileHvnCount', 'profileLvnCount', 'valueWidthAtr']


def feats(b):
    d = {}
    for s in SHAPE:
        d[s] = b[s]
    d['ofRelVolume'] = b['ofRelVolume']
    d['absDeltaPct'] = abs(b['ofDeltaPct']) if b['ofDeltaPct'] is not None else None
    d['absCumDeltaSlope'] = abs(b['ofCumDeltaSlope']) if b['ofCumDeltaSlope'] is not None else None
    if b['ofMaxDelta'] is not None and b['ofMinDelta'] is not None and b['ofTotalVolume']:
        d['deltaRange'] = (b['ofMaxDelta'] - b['ofMinDelta']) / max(b['ofTotalVolume'], 1.0)
    else:
        d['deltaRange'] = None
    sb, ss = b['stackedBuyLevels_3x'], b['stackedSellLevels_3x']
    d['stacked3x'] = (sb + ss) if (sb is not None and ss is not None) else None
    ib, isl = b['buyImbalanceCount_3x'], b['sellImbalanceCount_3x']
    d['imbal3x'] = (ib + isl) if (ib is not None and isl is not None) else None
    mb, ms = b['maxBuyImbalanceRatio'], b['maxSellImbalanceRatio']
    d['maxImbalRatio'] = max(mb, ms) if (mb is not None and ms is not None) else None
    d['absorptionStrengthRaw'] = b['absorptionStrengthRaw']
    d['repeatedTradeAtExtreme'] = b['repeatedTradeAtExtreme']
    u, dn = b['volumePerUpTick'], b['volumePerDownTick']
    d['volPerTick'] = (u + dn) / 2.0 if (u is not None and dn is not None) else None
    d['absDistPocAtr'] = abs(b['distPocAtr']) if b['distPocAtr'] is not None else None
    d['profileHvnCount'] = b['profileHvnCount']
    d['profileLvnCount'] = b['profileLvnCount']
    if b['profileVah'] is not None and b['profileVal'] is not None:
        d['valueWidthAtr'] = (b['profileVah'] - b['profileVal']) / b['atr']
    else:
        d['valueWidthAtr'] = None
    return d


ROWS = []
for i in EV:
    b = B[i]
    d = feats(b)
    if any(d[k] is None for k in SHAPE + OF):
        continue
    mfL, _ = mfe_mae(i, +1)
    mfS, _ = mfe_mae(i, -1)
    d['i'] = i
    d['day'] = b['day']
    d['atr'] = b['atr']
    # magnitude target: the unsigned reach of the next 90 minutes, in ATR.
    # averaging the two sides removes the drift component so this is a
    # pure "how much room was there" number.
    d['mfeAtr'] = (mfL + mfS) / 2.0 / b['atr']
    ROWS.append(d)

DEVR = [r for r in ROWS if split_of(r['day']) == 'DEV']
VALR = [r for r in ROWS if split_of(r['day']) == 'VAL']
print('rows with complete features:  DEV %d   VAL %d' % (len(DEVR), len(VALR)))


def ranks(vals):
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    r = [0.0] * len(vals)
    for pos, k in enumerate(order):
        r[k] = float(pos)
    return r


def spearman(xs, ys):
    if len(xs) < 3:
        return 0.0
    rx, ry = ranks(xs), ranks(ys)
    nn = len(xs)
    m = (nn - 1) / 2.0
    num = sum((a - m) * (b - m) for a, b in zip(rx, ry))
    den = (sum((a - m) ** 2 for a in rx) * sum((b - m) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


# bar-shape baseline, and the residual order flow has to beat
print('\n  bar-shape baseline (the bar already known to carry rho ~0.23):')
for s in SHAPE:
    print('    %-24s rho DEV %+0.3f   VAL %+0.3f'
          % (s, spearman([r[s] for r in DEVR], [r['mfeAtr'] for r in DEVR]),
             spearman([r[s] for r in VALR], [r['mfeAtr'] for r in VALR])))


def rank_pct(ref_sorted, v):
    lo, hi = 0, len(ref_sorted)
    while lo < hi:
        mid = (lo + hi) // 2
        if ref_sorted[mid] < v:
            lo = mid + 1
        else:
            hi = mid
    return lo / max(len(ref_sorted) - 1, 1)


shape_ref = {s: sorted(r[s] for r in DEVR) for s in SHAPE}
shape_sign = {s: (1.0 if spearman([r[s] for r in DEVR],
                                  [r['mfeAtr'] for r in DEVR]) > 0 else -1.0)
              for s in SHAPE}
for rows in (DEVR, VALR):
    for r in rows:
        r['shape'] = sum(shape_sign[s] * rank_pct(shape_ref[s], r[s]) for s in SHAPE) / len(SHAPE)
print('    %-24s rho DEV %+0.3f   VAL %+0.3f'
      % ('SHAPE COMPOSITE', spearman([r['shape'] for r in DEVR], [r['mfeAtr'] for r in DEVR]),
         spearman([r['shape'] for r in VALR], [r['mfeAtr'] for r in VALR])))

# residualise MFE on the shape composite by subtracting the bucket mean
def residualise(rows, nb=25):
    idx = sorted(range(len(rows)), key=lambda k: rows[k]['shape'])
    for k in range(nb):
        grp = idx[len(idx) * k // nb: len(idx) * (k + 1) // nb]
        if not grp:
            continue
        mu = sum(rows[j]['mfeAtr'] for j in grp) / len(grp)
        for j in grp:
            rows[j]['resid'] = rows[j]['mfeAtr'] - mu


residualise(DEVR)
residualise(VALR)

print('\n  %-26s %10s %10s   %10s %10s' % ('order-flow feature', 'rho raw D', 'rho raw V',
                                           'rho RESID D', 'rho RESID V'))
keep = []
for s in OF:
    rd = spearman([r[s] for r in DEVR], [r['mfeAtr'] for r in DEVR])
    rv = spearman([r[s] for r in VALR], [r['mfeAtr'] for r in VALR])
    ed = spearman([r[s] for r in DEVR], [r['resid'] for r in DEVR])
    ev = spearman([r[s] for r in VALR], [r['resid'] for r in VALR])
    flag = ''
    if abs(ed) >= 0.05 and ed * ev > 0 and abs(ev) >= 0.03:
        flag = 'ADDS'
        keep.append((s, 1.0 if ed > 0 else -1.0))
    print('  %-26s %+10.3f %+10.3f   %+10.3f %+10.3f  %s' % (s, rd, rv, ed, ev, flag))
print('\n  order-flow features that ADD over bar shape: %s'
      % ([k[0] for k in keep] if keep else 'NONE'))

if keep:
    of_ref = {s: sorted(r[s] for r in DEVR) for s, _ in keep}
    for rows in (DEVR, VALR):
        for r in rows:
            r['ofsc'] = sum(g * rank_pct(of_ref[s], r[s]) for s, g in keep) / len(keep)
            r['both'] = 0.5 * r['shape'] + 0.5 * r['ofsc']
    print('  combined SHAPE+OF score vs MFE:  DEV %+0.3f   VAL %+0.3f'
          % (spearman([r['both'] for r in DEVR], [r['mfeAtr'] for r in DEVR]),
             spearman([r['both'] for r in VALR], [r['mfeAtr'] for r in VALR])))

# ===================================================================== Q2
print('\n' + '=' * 100)
print('Q2  ARE LIQUIDITY ZONES MAGNETS OR BARRIERS? (distance-matched)')
print('=' * 100)
print('For each event-side and each target distance d, the target price is')
print('marked ON-LEVEL if a developing POC/VAH/VAL sits within 0.10 ATR of')
print('it. Hit rates are then compared WITHIN the same distance bucket, so')
print('distance cannot explain a difference. PLACEBO repeats it with every')
print('level shifted +0.37 ATR - a price that is not a level.')

DISTS = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0]
BAND = 0.10
SHIFT = 0.37


def levels_of(b, shift=0.0):
    out = []
    for nm in ('profilePoc', 'profileVah', 'profileVal'):
        v = b[nm]
        if v is not None:
            out.append(v + shift * b['atr'])
    return out


def magnet(shift, tag):
    # bucket -> split -> (on-level hits, on-level n, off-level hits, off n)
    acc = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    cont = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for i in EV:
        b = B[i]
        sp = split_of(b['day'])
        lv = levels_of(b, shift)
        if not lv:
            continue
        e = b['close']
        a = b['atr']
        for side in (+1, -1):
            for d in DISTS:
                T = e + side * d * a
                on = any(abs(L - T) <= BAND * a for L in lv)
                k = first_touch(i, side, T)
                cell = acc[d][sp]
                if on:
                    cell[1] += 1
                    if k:
                        cell[0] += 1
                else:
                    cell[3] += 1
                    if k:
                        cell[2] += 1
                # continuation: given the target was reached, did price go
                # a further 0.5 ATR beyond it inside the same window?
                if k:
                    T2 = e + side * (d + 0.5) * a
                    k2 = first_touch(i, side, T2)
                    c = cont[d][sp]
                    if on:
                        c[1] += 1
                        if k2:
                            c[0] += 1
                    else:
                        c[3] += 1
                        if k2:
                            c[2] += 1
    print('\n  --- %s ---' % tag)
    print('  %6s %6s %22s %22s %10s' % ('dist', 'split', 'ON-level hit%  (n)',
                                        'OFF-level hit%  (n)', 'diff pp'))
    for d in DISTS:
        for sp in ('DEV', 'VAL'):
            h1, n1, h0, n0 = acc[d][sp]
            if n1 < 100 or n0 < 100:
                print('  %6.2f %6s %22s %22s %10s'
                      % (d, sp, '(n=%d too few)' % n1, '(n=%d)' % n0, '-'))
                continue
            p1, p0 = 100.0 * h1 / n1, 100.0 * h0 / n0
            print('  %6.2f %6s %14.1f (%6d) %14.1f (%6d) %10.2f'
                  % (d, sp, p1, n1, p0, n0, p1 - p0))
    print('\n  continuation +0.5 ATR BEYOND the target, given the target was reached')
    print('  (if levels are BARRIERS, ON-level continuation must be LOWER)')
    print('  %6s %6s %22s %22s %10s' % ('dist', 'split', 'ON-level cont% (n)',
                                        'OFF-level cont% (n)', 'diff pp'))
    for d in DISTS:
        for sp in ('DEV', 'VAL'):
            h1, n1, h0, n0 = cont[d][sp]
            if n1 < 100 or n0 < 100:
                continue
            p1, p0 = 100.0 * h1 / n1, 100.0 * h0 / n0
            print('  %6.2f %6s %14.1f (%6d) %14.1f (%6d) %10.2f'
                  % (d, sp, p1, n1, p0, n0, p1 - p0))
    return acc, cont


real = magnet(0.0, 'REAL LEVELS (POC / VAH / VAL)')
plac = magnet(SHIFT, 'PLACEBO LEVELS (same levels shifted +%.2f ATR)' % SHIFT)

# ================================================================== Q2c
print('\n' + '=' * 100)
print('Q2c  EXIT-RULE COMPARISON - exact 1m race, stop frozen at %.1f ATR' % STOP_ATR)
print('=' * 100)
print('Same entries, same stop, only the TARGET changes. When one bar')
print('contains both stop and target the STOP is taken (conservative).')
print('Entries are direction-agnostic, so nothing here should be')
print('profitable - the question is purely which target captures MORE.')


def race(i, side, stop_px, target_px):
    """Exact bar-by-bar race. Returns realised points (signed, pre-cost)."""
    e = B[i]['close']
    for k in range(1, HORIZON + 1):
        c = B[i + k]
        if side > 0:
            hit_stop = c['low'] <= stop_px
            hit_tgt = target_px is not None and c['high'] >= target_px
        else:
            hit_stop = c['high'] >= stop_px
            hit_tgt = target_px is not None and c['low'] <= target_px
        if hit_stop:
            return (stop_px - e) * side
        if hit_tgt:
            return (target_px - e) * side
    c = B[i + HORIZON]
    return (c['close'] - e) * side


def nearest_level_ahead(b, side, shift=0.0):
    e = b['close']
    best = None
    for L in levels_of(b, shift):
        d = (L - e) * side
        if d <= 0:
            continue
        if best is None or d < best[1]:
            best = (L, d)
    return best


EXITS = ['time_90m', 'fixed_1.0R', 'fixed_1.5R', 'fixed_2.0R', 'LEVEL', 'LEVEL_placebo']
res = defaultdict(lambda: defaultdict(list))
capt = defaultdict(lambda: defaultdict(list))
for i in EV:
    b = B[i]
    sp = split_of(b['day'])
    a = b['atr']
    e = b['close']
    for side in (+1, -1):
        S = STOP_ATR * a
        stop_px = e - side * S
        mfe, _ = mfe_mae(i, side)
        for name in EXITS:
            if name == 'time_90m':
                t = None
            elif name.startswith('fixed'):
                t = e + side * float(name.split('_')[1][:-1]) * S
            else:
                sh = SHIFT if name.endswith('placebo') else 0.0
                nl = nearest_level_ahead(b, side, sh)
                # only comparable when the level is a plausible target
                if nl is None or nl[1] < 0.3 * a or nl[1] > 3.0 * a:
                    continue
                t = nl[0]
            v = race(i, side, stop_px, t)
            res[name][sp].append(v - COST)
            if mfe > 0:
                capt[name][sp].append(max(v, 0.0) / mfe)

print('\n  %-16s %10s %10s %10s %10s %10s'
      % ('exit rule', 'n DEV', 'net DEV', 'net VAL', 'capt DEV', 'capt VAL'))
for name in EXITS:
    dv, vl = res[name]['DEV'], res[name]['VAL']
    if not dv or not vl:
        continue
    cd, cv = capt[name]['DEV'], capt[name]['VAL']
    print('  %-16s %10d %+10.3f %+10.3f %10.3f %10.3f'
          % (name, len(dv), sum(dv) / len(dv), sum(vl) / len(vl),
             sum(cd) / len(cd), sum(cv) / len(cv)))

# LEVEL vs matched fixed target on the IDENTICAL subset
print('\n  LEVEL vs the closest fixed-R target, on the IDENTICAL event subset')
pair = {'LEVEL': [], 'matched_fixed': [], 'LEVEL_placebo': []}
byday = defaultdict(list)
for i in EV:
    b = B[i]
    a = b['atr']
    e = b['close']
    for side in (+1, -1):
        S = STOP_ATR * a
        nl = nearest_level_ahead(b, side, 0.0)
        npl = nearest_level_ahead(b, side, SHIFT)
        if nl is None or nl[1] < 0.3 * a or nl[1] > 3.0 * a:
            continue
        if npl is None or npl[1] < 0.3 * a or npl[1] > 3.0 * a:
            continue
        stop_px = e - side * S
        vl_ = race(i, side, stop_px, nl[0]) - COST
        # matched fixed target: SAME distance, but not a level
        vm = race(i, side, stop_px, e + side * nl[1]) - COST   # identical by construction
        vp = race(i, side, stop_px, npl[0]) - COST
        pair['LEVEL'].append(vl_)
        pair['matched_fixed'].append(vm)
        pair['LEVEL_placebo'].append(vp)
        byday[b['day']].append(vl_ - vp)
for k in ('LEVEL', 'LEVEL_placebo'):
    v = pair[k]
    print('    %-16s n=%d  mean %+0.3f pt' % (k, len(v), sum(v) / len(v)))
diff = [a - b_ for a, b_ in zip(pair['LEVEL'], pair['LEVEL_placebo'])]
mu = sum(diff) / len(diff)
days = list(byday.values())
boot = []
for _ in range(2000):
    s = [x for dd in random.choices(days, k=len(days)) for x in dd]
    boot.append(sum(s) / len(s))
boot.sort()
print('    LEVEL minus PLACEBO: %+0.3f pt/trade   day-block 95%% CI [%+0.3f, %+0.3f]'
      % (mu, boot[50], boot[1949]))
print('    (a real level effect requires this interval to exclude zero)')
