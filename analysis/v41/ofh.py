#!/usr/bin/env python3
# OF-H SERIES - twelve DIRECTIONAL order-flow hypotheses on the
# volumetric capture. The magnitude result (of_targets.py) says order
# flow predicts HOW FAR; this asks the only question that pays: does any
# order-flow event predict WHICH WAY?
#
# Honesty header, before any result:
#   - the OF window is ten months (2025-11 .. 2026-08) and its holdout is
#     already spent, so DEV (thru 2026-03) / VAL (2026-04+) is a
#     within-window replication split, NOT out-of-sample. Any survivor is
#     PROVISIONAL and would need confirmation on months captured AFTER
#     today (2026-08) - which arrive naturally as the capture grows.
#   - all twelve declared with direction and mechanism IN THIS HEADER
#     before the script ran; all twelve reported; identical search re-run
#     on within-day-shuffled outcomes for the noise floor.
#
# Declared set (direction fixed here, engine semantics verified in
# V4OrderFlowV41.cs before declaring - absorptionBuyCandidate means
# aggressive BUYERS were absorbed at an extreme, i.e. bearish):
#  OFH1  DIVERGENCE FADE     price new 20-bar high, cum delta not -> SHORT (mirror LONG)
#  OFH2  CONFIRMED BREAK GO  price new extreme AND cum delta new extreme -> follow
#  OFH3  ABSORPTION REVERSAL absorptionBuyCandidate -> SHORT; sell -> LONG
#  OFH4  STACKED IMBAL GO    >=2 stacked 3x buy levels & positive delta -> LONG (mirror)
#  OFH5  IMBAL EXHAUST FADE  maxImbalRatio>=4 at the matching new extreme -> fade
#  OFH6  CUM-DELTA TREND GO  15-bar delta sum in DEV top/bottom decile -> follow its sign
#  OFH7  EFFORT-RESULT GO    up bar (body>25%) on NEGATIVE delta -> LONG (price is
#                            truth; opposing aggression was absorbed). mirror SHORT
#  OFH8  VALUE REJECTION GO  REJECTED_FROM_VALUE -> away from value (sign close-POC)
#  OFH9  VALUE REVERSION     |distPocAtr|>=2 -> back toward POC
#  OFH10 ACCEPTANCE ROTATION ACCEPTED_INTO_VALUE -> toward POC
#  OFH11 DELTA CLIMAX FADE   |deltaPct|>=60 & relVol>=2 -> fade the delta sign
#  OFH12 REPEAT-EXTREME FADE repeatedTradeAtExtreme >= DEV p90 at a new extreme -> fade
#
# Rules of engagement: RTH only, >=30 min after RTH open, >=90 min before
# RTH close; entry at signal bar close; 30-min cooldown per hypothesis;
# management A = flat 60m time exit, management B = 1.5 ATR stop + 90m cap
# (exact 1m race); cost 0.87 pt RT. DEV-derived thresholds frozen for VAL.

import csv, glob, os, pickle, random
from collections import defaultdict

SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
D = os.path.join(SCR, 'of2')
CACHE = os.path.join(SCR, 'of_bars2.pkl')
COST = 0.87
HORIZON = 90
STOP_ATR = 1.5
COOLDOWN = 30
DEV_END = '2026-03-31'
random.seed(41)


def F(v):
    try:
        x = float(v)
        return x if x == x else None
    except Exception:
        return None


NEED = ['f_open', 'f_high', 'f_low', 'f_close', 'f_atr', 'f_isRth',
        'f_minutesToRthClose', 'f_minutesFromRthOpen', 'f_bodyPctOfRange',
        'f_relVolume', 'f_ofBarDelta', 'f_ofDeltaPct', 'f_ofTotalVolume',
        'f_stackedBuyLevels_3x', 'f_stackedSellLevels_3x',
        'f_maxBuyImbalanceRatio', 'f_maxSellImbalanceRatio',
        'f_buyImbalanceNearHigh', 'f_sellImbalanceNearLow',
        'f_repeatedTradeAtExtreme', 'f_absorptionBuyCandidate',
        'f_absorptionSellCandidate', 'f_priceNewHigh', 'f_priceNewLow',
        'f_bullishDeltaDivergenceCandidate', 'f_bearishDeltaDivergenceCandidate',
        'f_deltaConfirmsBreak', 'f_profileReady', 'f_distPocAtr',
        'f_closeMinusPocPts', 'f_profileInteraction']


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
                    if c == 'f_profileInteraction':
                        d['pi'] = v
                    else:
                        d[c[2:]] = (v == 'TRUE') if v in ('TRUE', 'FALSE') else F(v)
                if d['high'] is None or d['atr'] is None:
                    continue
                et = row[i['f_barCloseEt']]
                d['et'] = et
                d['day'] = et[:10]
                d['tmin'] = (int(et[:4]) * 527040 + int(et[5:7]) * 44640
                             + int(et[8:10]) * 1440 + int(et[11:13]) * 60
                             + int(et[14:16]))
                bars.append(d)
    bars.sort(key=lambda b: b['et'])
    with open(CACHE, 'wb') as fh:
        pickle.dump(bars, fh, 2)
    return bars


B = load()
n = len(B)
print('bars: %d   %s -> %s' % (n, B[0]['et'], B[-1]['et']))

# rolling 15-bar delta sum (contiguous minutes only)
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

# eligibility: RTH, inside-window, contiguous forward path
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
print('eligible RTH bars: %d' % len(ELIG))

# DEV-frozen thresholds
dev_dsum = sorted(abs(B[j]['dsum15']) for j in ELIG
                  if B[j]['day'] <= DEV_END and B[j]['dsum15'] is not None)
DSUM_P90 = dev_dsum[int(len(dev_dsum) * 0.9)]
dev_rep = sorted(B[j]['repeatedTradeAtExtreme'] for j in ELIG
                 if B[j]['day'] <= DEV_END and B[j]['repeatedTradeAtExtreme'] is not None)
REP_P90 = dev_rep[int(len(dev_rep) * 0.9)]
print('DEV-frozen thresholds: |dsum15| p90 = %.0f   repeatedTradeAtExtreme p90 = %.0f'
      % (DSUM_P90, REP_P90))


def sig(name, b):
    """returns +1 long / -1 short / 0 no signal, per the declared set."""
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
    if name == 'OFH8':
        if b['pi'] != 'REJECTED_FROM_VALUE' or b['closeMinusPocPts'] is None:
            return 0
        return +1 if b['closeMinusPocPts'] > 0 else -1
    if name == 'OFH9':
        d = b['distPocAtr']
        if d is None or not b['profileReady']:
            return 0
        if d >= 2:
            return -1
        if d <= -2:
            return +1
        return 0
    if name == 'OFH10':
        if b['pi'] != 'ACCEPTED_INTO_VALUE' or b['closeMinusPocPts'] is None:
            return 0
        return -1 if b['closeMinusPocPts'] > 0 else +1
    if name == 'OFH11':
        dp, rv, bd = b['ofDeltaPct'], b['relVolume'], b['ofBarDelta']
        if dp is None or rv is None or bd is None:
            return 0
        if abs(dp) >= 60 and rv >= 2:
            return -1 if bd > 0 else +1
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


NAMES = ['OFH%d' % k for k in range(1, 13)]

# build membership with per-hypothesis 30-min cooldown
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


def race_stop(j, side):
    """1.5 ATR stop, 90m time cap. Exact walk."""
    e = B[j]['close']
    S = STOP_ATR * B[j]['atr']
    stop_px = e - side * S
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        if (side > 0 and c['low'] <= stop_px) or (side < 0 and c['high'] >= stop_px):
            return (stop_px - e) * side
    return (B[j + HORIZON]['close'] - e) * side


def net60(j, side):
    return (B[j + 60]['close'] - B[j]['close']) * side


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


def boot_p(day_vals, nb=2000):
    days = list(day_vals.values())
    if not days:
        return float('nan')
    ge = 0
    for _ in range(nb):
        s = [x for dd in random.choices(days, k=len(days)) for x in dd]
        if sum(s) / len(s) <= 0:
            ge += 1
    return ge / nb


print('\n' + '=' * 108)
print('OF-H SERIES  -  net pt/trade @ %.2f cost.  A = 60m time exit.  B = %.1f ATR stop + %dm cap.'
      % (COST, STOP_ATR, HORIZON))
print('=' * 108)
RES = {}
for name in NAMES:
    out = {}
    for sp in ('DEV', 'VAL'):
        rowsA = []
        rowsB = []
        byday = defaultdict(list)
        bymon = defaultdict(list)
        for j, d in MEMB[name]:
            if split_of(B[j]['day']) != sp:
                continue
            vA = net60(j, d) - COST
            vB = race_stop(j, d) - COST
            rowsA.append(vA)
            rowsB.append(vB)
            byday[B[j]['day']].append(vA)
            bymon[B[j]['day'][:7]].append(vA)
        if not rowsA:
            out[sp] = None
            continue
        mons = {m: sum(v) / len(v) for m, v in sorted(bymon.items())}
        out[sp] = dict(n=len(rowsA),
                       muA=sum(rowsA) / len(rowsA),
                       muB=sum(rowsB) / len(rowsB),
                       p=boot_p(byday),
                       posm=sum(1 for v in mons.values() if v > 0),
                       nm=len(mons), mons=mons)
    RES[name] = out
    for sp in ('DEV', 'VAL'):
        s = out[sp]
        if s is None:
            print('%-6s %s  n=0' % (name, sp))
            continue
        print('%-6s %s  n=%5d  A=%+8.3f  B=%+8.3f  p(A)=%.3f  posMonths=%d/%d'
              % (name, sp, s['n'], s['muA'], s['muB'], s['p'], s['posm'], s['nm']))

print('\n#### survivors (A>0 both splits, p_DEV<0.05, and majority of months positive in both)')
surv = []
for name in NAMES:
    dv, vl = RES[name]['DEV'], RES[name]['VAL']
    if (dv and vl and dv['muA'] > 0 and vl['muA'] > 0 and dv['p'] < 0.05
            and dv['posm'] * 2 > dv['nm'] and vl['posm'] * 2 > vl['nm']):
        surv.append(name)
print('  survivors: %s' % (surv if surv else 'NONE'))

# ---------------- noise floor: same search, within-day shuffled outcomes
print('\n#### NOISE FLOOR - identical 12-way search on within-day-shuffled 60m outcomes (200x)')
allidx = sorted(set(j for name in NAMES for j, _ in MEMB[name]))
byday_i = defaultdict(list)
for j in allidx:
    byday_i[B[j]['day']].append(j)
orig = {j: net60(j, +1) for j in allidx}   # raw long-side forward return
cur = dict(orig)
NS = 200
best = []
anyboth = 0
for it in range(NS):
    for _, idxs in byday_i.items():
        vals = [cur[j] for j in idxs]
        random.shuffle(vals)
        for j, v in zip(idxs, vals):
            cur[j] = v
    bm = -9e9
    hit = False
    for name in NAMES:
        agg = {'DEV': [], 'VAL': []}
        for j, d in MEMB[name]:
            agg[split_of(B[j]['day'])].append(d * cur[j] - COST)
        if not agg['DEV'] or not agg['VAL']:
            continue
        mud = sum(agg['DEV']) / len(agg['DEV'])
        muv = sum(agg['VAL']) / len(agg['VAL'])
        if mud > bm:
            bm = mud
        if mud > 0 and muv > 0:
            hit = True
    best.append(bm)
    if hit:
        anyboth += 1
best.sort()
real_best = max(RES[nm]['DEV']['muA'] for nm in NAMES if RES[nm]['DEV'])
print('  best DEV mean of 12 on NOISE: median %+0.3f  p90 %+0.3f  max %+0.3f'
      % (best[NS // 2], best[int(NS * 0.9)], best[-1]))
print('  real best DEV mean: %+0.3f' % real_best)
print('  shuffles where >=1 of 12 was positive in BOTH splits: %d of %d (%.0f%%)'
      % (anyboth, NS, 100.0 * anyboth / NS))
