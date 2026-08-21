#!/usr/bin/env python3
# CAN WE PREDICT WHICH TRADES RUN?
#
# Every test so far targeted DIRECTION (signed return). This targets
# MAGNITUDE - how far the trade travels in its favour, regardless of
# which way. Those are different questions and in finance the second is
# usually far more predictable than the first (volatility clusters).
#
# Two questions, in order, because the second only matters if the first
# succeeds:
#   Q1  Is MFE_R (favourable excursion / stop) predictable from causal
#       pre-entry features?
#   Q2  IF it is - does the DIRECTIONAL edge differ across predicted-
#       excursion strata? A "runner" detector only makes money if
#       expectancy is not flat across it.
#
# Features are pre-declared below, all causal, all already in the
# capture. Fit on DEV, checked on VAL. HOLD (2024-07+) NOT read.

import csv, glob, os, random
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
COST = 0.87
random.seed(41)

def F(v):
    try: return float(v)
    except: return None

FEATS = ['relVolume', 'rangeAtr', 'bodyAtr', 'compressionRatio', 'expansionRatio',
         'atr', 'adrConsumedPct', 'minutesSinceVector_15m', 'tfPosInRange',
         'absVwapAtr', 'minsInState_15m', 'bodyPctOfRange', 'closeLocationInRange',
         'minutesFromSessionOpen']

E = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    if f[-11:-4] > '2024-06': continue
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: k for k, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isWarmup']] == 'TRUE': continue
            if row[i['f_eventKind']] not in ('BREAK_HIGH', 'BREAK_LOW'): continue
            mfp = F(row[i['y_maxMfePts']]); mfr = F(row[i['y_maxMfeR']])
            mae = F(row[i['y_maxMaePts']]); n240 = F(row[i['y_net_240m']])
            if not mfp or not mfr or mae is None or n240 is None: continue
            stop = mfp / mfr
            d = {'day': row[i['f_barCloseEt']][:10], 'stop': stop,
                 'mfeR': mfp / stop, 'maeR': mae / stop, 'netR': n240 / stop,
                 'netPt': n240, 'side': int(row[i['f_side']])}
            ok = True
            for name in FEATS:
                if name == 'absVwapAtr':
                    v = F(row[i['f_distVwapAtr']]); v = abs(v) if v is not None else None
                else:
                    v = F(row[i['f_' + name]])
                if v is None: ok = False; break
                d[name] = v
            if ok: E.append(d)

DEV = [e for e in E if e['day'] <= '2022-12-31']
VAL = [e for e in E if e['day'] > '2022-12-31']
print('events with full features: DEV %d  VAL %d' % (len(DEV), len(VAL)))

def ranks(vals):
    order = sorted(range(len(vals)), key=lambda k: vals[k])
    r = [0.0] * len(vals)
    for pos, k in enumerate(order): r[k] = pos
    return r

def spearman(xs, ys):
    rx, ry = ranks(xs), ranks(ys)
    n = len(xs); mx = (n - 1) / 2.0
    num = sum((a - mx) * (b - mx) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - mx) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0

print('\n### Q1 - is EXCURSION MAGNITUDE (MFE_R) predictable?')
print('%-26s %9s %9s   %9s %9s' % ('feature', 'rho DEV', 'rho VAL', 'rho|netR|DEV', 'rho netR DEV'))
keep = []
for name in FEATS:
    rd = spearman([e[name] for e in DEV], [e['mfeR'] for e in DEV])
    rv = spearman([e[name] for e in VAL], [e['mfeR'] for e in VAL])
    ra = spearman([e[name] for e in DEV], [abs(e['netR']) for e in DEV])
    rs = spearman([e[name] for e in DEV], [e['netR'] for e in DEV])
    flag = 'KEEP' if abs(rd) >= 0.10 and rd * rv > 0 and abs(rv) >= 0.05 else ''
    if flag: keep.append((name, 1.0 if rd > 0 else -1.0))
    print('%-26s %+9.3f %+9.3f   %+9.3f %+9.3f  %s' % (name, rd, rv, ra, rs, flag))

print('\nfeatures kept (same sign both splits, |rho_DEV|>=0.10): %s'
      % [k[0] for k in keep])

if not keep:
    print('no stable magnitude predictor -> Q2 is moot')
    raise SystemExit

# composite: mean of DEV-standardised ranks, signed by DEV direction
def build_score(rows, ref):
    out = []
    cols = {}
    for name, sgn in keep:
        vals = [e[name] for e in ref]
        srt = sorted(vals)
        cols[name] = (srt, sgn)
    for e in rows:
        tot = 0.0
        for name, sgn in keep:
            srt, s = cols[name]
            lo, hi = 0, len(srt)
            while lo < hi:
                mid = (lo + hi) // 2
                if srt[mid] < e[name]: lo = mid + 1
                else: hi = mid
            pct = lo / max(len(srt) - 1, 1)
            tot += s * pct
        out.append(tot / len(keep))
    return out

sd = build_score(DEV, DEV); sv = build_score(VAL, DEV)
print('composite score rho with MFE_R:  DEV %+0.3f   VAL %+0.3f'
      % (spearman(sd, [e['mfeR'] for e in DEV]), spearman(sv, [e['mfeR'] for e in VAL])))

print('\n### Q2 - does the DIRECTIONAL edge vary across predicted-excursion deciles?')
print('If the runner-detector works but this column is flat, magnitude is')
print('predictable and direction still is not - and no exit rule can help.')
for tag, rows, sc in (('DEV', DEV, sd), ('VAL', VAL, sv)):
    idx = sorted(range(len(rows)), key=lambda k: sc[k])
    dec = [idx[len(idx) * k // 10: len(idx) * (k + 1) // 10] for k in range(10)]
    print('  %s  %-6s %8s %8s %8s %10s %10s' % (tag, 'decile', 'n', 'medMFE_R', 'medMAE_R',
                                                'mean netPt', 'net-cost'))
    for k, grp in enumerate(dec):
        mf = sorted(rows[j]['mfeR'] for j in grp)
        ma = sorted(rows[j]['maeR'] for j in grp)
        np_ = sum(rows[j]['netPt'] for j in grp) / len(grp)
        print('       %-6d %8d %8.2f %8.2f %10.2f %10.2f'
              % (k + 1, len(grp), mf[len(mf) // 2], ma[len(ma) // 2], np_, np_ - COST))

# directional-edge monotonicity control
print('\n### control: same deciles, but outcomes shuffled within day (100x)')
byday = defaultdict(list)
for j, e in enumerate(DEV): byday[e['day']].append(j)
orig = [e['netPt'] for e in DEV]
idx = sorted(range(len(DEV)), key=lambda k: sd[k])
d1 = idx[:len(idx) // 10]; d10 = idx[9 * len(idx) // 10:]
real_gap = (sum(DEV[j]['netPt'] for j in d10) / len(d10)
            - sum(DEV[j]['netPt'] for j in d1) / len(d1))
gaps = []
for _ in range(100):
    for _, ii in byday.items():
        vv = [orig[j] for j in ii]; random.shuffle(vv)
        for j, v in zip(ii, vv): DEV[j]['netPt'] = v
    gaps.append(sum(DEV[j]['netPt'] for j in d10) / len(d10)
                - sum(DEV[j]['netPt'] for j in d1) / len(d1))
for j, v in enumerate(orig): DEV[j]['netPt'] = v
gaps.sort()
print('  top-decile minus bottom-decile mean netPt:  real %+0.2f' % real_gap)
print('  shuffled: p5 %+0.2f  median %+0.2f  p95 %+0.2f' % (gaps[5], gaps[50], gaps[94]))
