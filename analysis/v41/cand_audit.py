#!/usr/bin/env python3
# ======================================================================
# CANDIDATE SHELF AUDIT - reproducibility, geometry, management
# 2026-08-21. Diagnostic only. Entry rules are NEVER modified here.
# Partitions are always reported separately; nothing is pooled into a
# single headline. UNSEEN (2025-08..11-01) is SPENT - it was used in the
# prior pass and is reported here as historical evidence, not as a fresh
# holdout.
# ======================================================================

import os, sys, random, datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cand_spec import (load_merged, generate, make_ctx, window_of, TICK, COST,
                       HORIZON, COOL, CANDIDATES, OVERLAY, G1_DEPTH_ATR, LIFE,
                       DOLLARS_PER_POINT)

random.seed(41)
B = load_merged()
N = len(B)
consec, entry_ok = make_ctx(B)
EV, SIGS, CTX = generate(B)
WINS = ('UNSEEN', 'DEV', 'IR')
IDX = {}
for j in range(N):
    IDX[B[j]['et']] = j

# side/window-matched baseline over eligible bars
EB = [j for j in range(N) if entry_ok(j)]
BASE = {}
for w in WINS:
    for d in (1, -1):
        v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in EB
             if window_of(B[j]['day']) == w]
        BASE[(w, d)] = sum(v) / len(v)

HIST = {'OFH13': (16, 57, 60), 'G4': (36, 79, 103), 'G3': (82, 194, 201),
        'OFH14': (70, 177, 215), 'G1': (150, 326, 369)}

print('=' * 118)
print('STEP 1 - REPRODUCIBILITY AUDIT')
print('=' * 118)
print('  merged history %d bars  %s .. %s   OFH6 signals %d'
      % (N, B[0]['et'], B[-1]['et'], len(SIGS)))
print('  %-7s %-22s %-22s %s' % ('cand', 'canonical U/D/I', 'historical U/D/I', 'match'))
allok = True
for c in list(CANDIDATES) + [OVERLAY]:
    w = defaultdict(int)
    for e in EV[c]:
        w[e['w']] += 1
    got = (w['UNSEEN'], w['DEV'], w['IR'])
    ok = got == HIST[c]
    allok &= ok
    print('  %-7s %-22s %-22s %s' % (c, '%d / %d / %d' % got,
                                     '%d / %d / %d' % HIST[c], 'EXACT' if ok else 'MISMATCH'))
# integrity
probs = []
for c in list(CANDIDATES) + [OVERLAY]:
    ids = [e['id'] for e in EV[c]]
    if len(set(ids)) != len(ids):
        probs.append('%s duplicate event ids' % c)
    prev = None
    for e in EV[c]:
        t = B[e['j']]['tmin']
        if prev is not None and t < prev:
            probs.append('%s out of chronological order' % c)
        if c not in ('G1', 'G3') and prev is not None and t - prev < COOL:
            probs.append('%s cooldown violation' % c)
        prev = t
        for key in ('sig_j', 'fvg_j', 'attack_j'):
            if key in e['meta'] and e['meta'][key] > e['j']:
                probs.append('%s causality: %s after entry' % (c, key))
        if e['R'] <= 0:
            probs.append('%s non-positive R' % c)
        if e['d'] > 0 and e['entry_px'] > B[e['j']]['high'] + 1e-9:
            probs.append('%s long entry above bar high' % c)
        if e['d'] < 0 and e['entry_px'] < B[e['j']]['low'] - 1e-9:
            probs.append('%s short entry below bar low' % c)
print('  integrity: %s' % ('CLEAN - no duplicates, no causality or cooldown violations'
                           if not probs else sorted(set(probs))))
print('  VERDICT: %s' % ('PASS - all five reproduce exactly' if allok and not probs
                         else 'FAIL - stop and fix before proceeding'))


# ---------------------------------------------------------------- paths
def path(j, d, px):
    """Forward path facts from an entry."""
    atr = B[j]['atr']
    mfe = mae = 0.0
    tf = ta = 0
    ff = {}
    for x in (0.5, 1.0, 1.5, 2.0):
        ff[x] = 0
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        fav = (c['high'] - px) if d > 0 else (px - c['low'])
        adv = (px - c['low']) if d > 0 else (c['high'] - px)
        if fav > mfe:
            mfe, tf = fav, k
        if adv > mae:
            mae, ta = adv, k
        for x in ff:
            if ff[x]:
                continue
            hf, ha = fav >= x * atr, adv >= 1.0 * atr if x > 1.0 else adv >= x * atr
            ff[x] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
    net = {}
    for m in (5, 10, 15, 20, 30, 45, 60):
        net[m] = (B[j + m]['close'] - px) * d
    return {'mfe': mfe, 'mae': mae, 'tmfe': tf, 'tmae': ta, 'ff': ff, 'net': net}


for c in list(CANDIDATES) + [OVERLAY]:
    for e in EV[c]:
        e['p'] = path(e['j'], e['d'], e['entry_px'])
        e['exc'] = e['p']['net'][HORIZON] - BASE[(e['w'], e['d'])]


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def ffpct(evs, x):
    f = sum(1 for e in evs if e['p']['ff'][x] == 1)
    a = sum(1 for e in evs if e['p']['ff'][x] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


print('\n' + '=' * 118)
print('STEP 3 - PATH GEOMETRY PER CANDIDATE, PER PARTITION (frozen entries)')
print('=' * 118)
for c in CANDIDATES:
    print('\n  ---- %s ----' % c)
    print('   %-7s %4s %8s %8s %8s %7s %7s %6s %6s %6s %6s %5s %5s'
          % ('win', 'n', 'meanNet', 'medNet', 'excess', 'medMFE', 'medMAE',
             'ratio', 'ff0.5', 'ff1', 'ff2', 'tMFE', 'tMAE'))
    for w in WINS + ('ALL',):
        evs = EV[c] if w == 'ALL' else [e for e in EV[c] if e['w'] == w]
        if not evs:
            print('   %-7s %4d' % (w, 0))
            continue
        nets = [e['p']['net'][HORIZON] - COST for e in evs]
        mf, ma = med([e['p']['mfe'] for e in evs]), med([e['p']['mae'] for e in evs])
        print('   %-7s %4d %+8.2f %+8.2f %+8.2f %7.1f %7.1f %6.3f %6.1f %6.1f %6.1f %5d %5d'
              % (w, len(evs), sum(nets) / len(nets), med(nets),
                 sum(e['exc'] for e in evs) / len(evs), mf, ma,
                 mf / ma if ma else float('nan'), ffpct(evs, 0.5), ffpct(evs, 1.0),
                 ffpct(evs, 2.0), med([e['p']['tmfe'] for e in evs]),
                 med([e['p']['tmae'] for e in evs])))
    ev = EV[c]
    L = [e for e in ev if e['d'] > 0]
    S = [e for e in ev if e['d'] < 0]
    bym = defaultdict(list)
    byw = defaultdict(float)
    for e in ev:
        bym[e['day'][:7]].append(e['p']['net'][HORIZON] - COST)
        y, mo, dy = int(e['day'][:4]), int(e['day'][5:7]), int(e['day'][8:10])
        byw[datetime.date(y, mo, dy).isocalendar()[:2]] += e['p']['net'][HORIZON] - COST
    nets = sorted((e['p']['net'][HORIZON] - COST for e in ev), reverse=True)
    maes = sorted(e['p']['mae'] for e in ev)
    print('   LONG n=%d mean %+0.2f | SHORT n=%d mean %+0.2f | months %d/%d + | weeks %d/%d +'
          % (len(L), sum(e['p']['net'][HORIZON] - COST for e in L) / len(L) if L else float('nan'),
             len(S), sum(e['p']['net'][HORIZON] - COST for e in S) / len(S) if S else float('nan'),
             sum(1 for v in bym.values() if sum(v) / len(v) > 0), len(bym),
             sum(1 for v in byw.values() if v > 0), len(byw)))
    print('   top1%% %+0.1f  top5%% %+0.1f  of total %+0.1f | maxMAE %.1f  p95MAE %.1f  medR %.2f'
          % (sum(nets[:max(1, len(nets) // 100)]), sum(nets[:max(1, len(nets) // 20)]),
             sum(nets), maes[-1], maes[int(len(maes) * .95)], med([e['R'] for e in ev])))

# ---------------------------------------------------------------- stops
print('\n' + '=' * 118)
print('STEP 4/5 - STOP FAMILY and FIXED-R PAYOFF MAP (exact chronology; ties = AMBIGUOUS)')
print('=' * 118)
TARGETS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0]


def stop_dist(e, kind):
    if kind == 'STRUCT':
        return e['R']
    if kind == 'TRIG':
        b = B[e['j']]
        ref = b['low'] if e['d'] > 0 else b['high']
        return (e['entry_px'] - (ref - TICK)) if e['d'] > 0 else ((ref + TICK) - e['entry_px'])
    if kind == 'ATR1.0':
        return 1.0 * e['atr']
    if kind == 'ATR1.5':
        return 1.5 * e['atr']
    return None


def race(e, S, T):
    """Exact chronological race. Returns (R_result, ambiguous, minutes)."""
    d, px = e['d'], e['entry_px']
    sp = px - d * S
    tp = px + d * T if T else None
    for k in range(1, HORIZON + 1):
        c = B[e['j'] + k]
        hs = (c['low'] <= sp) if d > 0 else (c['high'] >= sp)
        ht = tp is not None and ((c['high'] >= tp) if d > 0 else (c['low'] <= tp))
        if hs and ht:
            return (-1.0, True, k)              # AMBIGUOUS -> counted as stop
        if hs:
            return (-1.0, False, k)
        if ht:
            return (T / S, False, k)
    v = (B[e['j'] + HORIZON]['close'] - px) * d
    return (v / S, False, HORIZON)


STOPS = {'OFH13': ['STRUCT', 'TRIG', 'ATR1.0', 'ATR1.5'],
         'OFH14': ['STRUCT', 'TRIG', 'ATR1.0', 'ATR1.5'],
         'G4': ['STRUCT', 'TRIG', 'ATR1.0', 'ATR1.5'],
         'G3': ['TRIG', 'ATR1.0', 'ATR1.5']}   # G3 STRUCT == ATR1.0 (D6)

for c in CANDIDATES:
    print('\n  ---- %s ----   (stop sizes in points, median)' % c)
    for kind in STOPS[c]:
        ss = [stop_dist(e, kind) for e in EV[c]]
        ss = [s for s in ss if s and s > 0]
        if not ss:
            continue
        hit = 0
        for e in EV[c]:
            S = stop_dist(e, kind)
            if not S or S <= 0:
                continue
            r, _a, _k = race(e, S, None)
            if r <= -1.0 + 1e-9:
                hit += 1
        print('   stop %-7s med %6.2f pt (%4.2f ATR)   stop-hit (no target) %5.1f%%'
              % (kind, med(ss), med([stop_dist(e, kind) / e['atr'] for e in EV[c]
                                     if stop_dist(e, kind)]), 100.0 * hit / len(EV[c])))
    # payoff map on the primary stop for this candidate
    primary = STOPS[c][0]
    print('   fixed-R map on stop=%s   [R/trade | win%% | ambig%%]  n(U/D/I)=%d/%d/%d'
          % (primary, sum(1 for e in EV[c] if e['w'] == 'UNSEEN'),
             sum(1 for e in EV[c] if e['w'] == 'DEV'),
             sum(1 for e in EV[c] if e['w'] == 'IR')))
    print('   %-6s %-24s %-24s %-24s' % ('tgt', 'UNSEEN', 'DEV', 'IR'))
    for T in TARGETS:
        row = '   %-6.2f' % T
        for w in WINS:
            evs = [e for e in EV[c] if e['w'] == w]
            rs = []
            amb = 0
            for e in evs:
                S = stop_dist(e, primary)
                if not S or S <= 0:
                    continue
                r, a, _k = race(e, S, T * S)
                cost_r = COST / S
                rs.append(r - cost_r)
                amb += 1 if a else 0
            if not rs:
                row += ' %-24s' % 'n/a'
                continue
            wins_ = sum(1 for x in rs if x > 0)
            row += ' %+7.3f %5.1f%% %5.1f%%   ' % (sum(rs) / len(rs),
                                                   100.0 * wins_ / len(rs),
                                                   100.0 * amb / len(rs))
        print(row)
    # plateau + full-history summary at the primary stop
    print('   full-history at stop=%s:  %-8s %8s %8s %8s %8s %9s'
          % (primary, 'target', 'R/trade', 'PF', 'medR', 'totR', 'maxDD_R'))
    for T in TARGETS:
        rs = []
        for e in EV[c]:
            S = stop_dist(e, primary)
            if not S or S <= 0:
                continue
            r, a, _k = race(e, S, T * S)
            rs.append(r - COST / S)
        pos = sum(x for x in rs if x > 0)
        neg = -sum(x for x in rs if x < 0)
        cum = 0.0
        peak = 0.0
        dd = 0.0
        for x in rs:
            cum += x
            peak = max(peak, cum)
            dd = min(dd, cum - peak)
        print('   %-8s %8s %+8.3f %8.2f %+8.3f %+8.1f %9.1f'
              % ('', '%.2fR' % T, sum(rs) / len(rs), pos / neg if neg else float('inf'),
                 med(rs), sum(rs), -dd))

# ------------------------------------------------------------ time exit
print('\n' + '=' * 118)
print('STEP 6 - TIME EXIT DIAGNOSTIC (no stop; net pt/trade after cost)')
print('=' * 118)
print('  %-7s %-6s %s' % ('cand', 'win', ''.join('%9s' % ('%dm' % m)
                                                 for m in (5, 10, 15, 20, 30, 45, 60))))
for c in CANDIDATES:
    for w in WINS:
        evs = [e for e in EV[c] if e['w'] == w]
        if not evs:
            continue
        row = '  %-7s %-6s' % (c, w)
        for m in (5, 10, 15, 20, 30, 45, 60):
            row += '%+9.2f' % (sum(e['p']['net'][m] - COST for e in evs) / len(evs))
        print(row)

# ------------------------------------------------------- G1 A/B overlay
print('\n' + '=' * 118)
print('STEP 7/9 - G1 EXECUTION OVERLAY, MATCHED A/B ON THE SAME PARENT EVENTS')
print('=' * 118)
print('  B-arm: limit at trigger close -/+ %.2f ATR(trigger bar), valid %d min,'
      % (G1_DEPTH_ATR, LIFE))
print('  no chase. Parent qualification is UNCHANGED - same EventIDs.')


def g1_arm(e, fill_ticks):
    """fill_ticks: 0 = touch, 1 = 1 tick through, 2 = 2+ ticks through."""
    d, atr = e['d'], e['atr']
    lim = B[e['j']]['close'] - d * G1_DEPTH_ATR * atr
    need = lim - fill_ticks * TICK * d
    for k in range(e['j'] + 1, min(e['j'] + LIFE + 1, N)):
        if not consec(k, e['j']):
            return None
        if not entry_ok(k):
            return None
        c = B[k]
        if (d > 0 and c['low'] <= need) or (d < 0 and c['high'] >= need):
            return {'j': k, 'px': lim}
    return None


for c in ('OFH13', 'G4', 'OFH14'):
    print('\n  ---- %s ----' % c)
    for ft, lbl in ((0, 'TOUCH'), (1, '1 tick through'), (2, '2 ticks through')):
        pairs = []
        for e in EV[c]:
            g = g1_arm(e, ft)
            if g is None:
                continue
            p = path(g['j'], e['d'], g['px'])
            pairs.append((e, g, p))
        if not pairs:
            print('   %-16s no fills' % lbl)
            continue
        imp = [(e['entry_px'] - g['px']) * e['d'] for e, g, p in pairs]
        na = [p['net'][HORIZON] - COST for e, g, p in pairs]
        nb = [e['p']['net'][HORIZON] - COST for e, g, p in pairs]
        mfb = med([p['mfe'] for e, g, p in pairs])
        mab = med([p['mae'] for e, g, p in pairs])
        fb = sum(1 for e, g, p in pairs if p['ff'][1.0] == 1)
        ab = sum(1 for e, g, p in pairs if p['ff'][1.0] == 2)
        print('   %-16s fill %3d/%3d = %3.0f%%  improve mean %+5.2f med %+5.2f pt  '
              'B net %+7.2f vs A %+7.2f  B ratio %5.3f  B ff1 %4.1f'
              % (lbl, len(pairs), len(EV[c]), 100.0 * len(pairs) / len(EV[c]),
                 sum(imp) / len(imp), med(imp), sum(na) / len(na), sum(nb) / len(nb),
                 mfb / mab if mab else float('nan'),
                 100.0 * fb / (fb + ab) if fb + ab else float('nan')))
        if ft == 0:
            perev = sum(na) / len(EV[c])
            print('   %-16s per-PARENT-EVENT EV (no-fill = 0): B %+0.2f   A %+0.2f'
                  % ('', perev, sum(e['p']['net'][HORIZON] - COST for e in EV[c]) / len(EV[c])))

# G3 / G1 overlap check
print('\n  ---- G3 vs G1 conceptual overlap (is a G1 arm duplicative?) ----')
ov = []
for e in EV['G3']:
    sj = e['meta']['sig_j']
    disc = (B[sj]['close'] - e['entry_px']) * e['d']
    ov.append(disc / B[sj]['atr'])
ov.sort()
deep = sum(1 for x in ov if x >= G1_DEPTH_ATR)
print('   G3 entry discount vs its own signal close, in ATR: p25 %.2f  med %.2f  p75 %.2f'
      % (ov[len(ov) // 4], ov[len(ov) // 2], ov[3 * len(ov) // 4]))
print('   G3 entries already >= %.2f ATR discounted: %d of %d (%.0f%%)'
      % (G1_DEPTH_ATR, deep, len(ov), 100.0 * deep / len(ov)))
print('   -> G3 IS a discount mechanism by construction; a G1 arm on top would')
print('      stack two discounts on the same parent. NOT run, per instruction.')
