#!/usr/bin/env python3
# TR-H1 CLASS D MANAGEMENT PASS - payoff/R:R profile of the FROZEN
# TR-H1 entries. DEV + VAL only. OOS and LOCKBOX are not read.
#
# Entry definition: byte-identical membership function to confirm.py
# (the run that produced DEV n=299 +1.21, VAL n=131 +2.99):
#   ARCH-B probe, side=+1, parent W formation, second leg confirmed,
#   not invalidated, 15m vector GREEN|BLUE, vector exits formation OR
#   formation break confirmed, EMA800 warm, not warmup, not control.
#
# PRIMARY STOP = MEDIUM (frozen in the preregistration for TR-H1 and
# the only stop the engine's race grid was computed against:
# f_raceStopFamily = MEDIUM on every row). TIGHT and STRUCTURAL are
# reported with what the capture records for them; their full fixed-R
# races were NOT captured and are not fabricated here.
#
# Race semantics (engine): TARGET = +kR before stop, STOP = stop first,
# AMBIGUOUS = same 1m bar reached both (excluded from EV, bounded),
# TIMEOUT = neither within 240m (EV uses the 240m residual net / stop).

import csv, glob, os
from collections import defaultdict

D = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad/full'
SPLITS = {'DEV': ('2019-07-01', '2022-12-31'), 'VAL': ('2023-01-01', '2024-06-30')}
MULTS = [0.5, 0.75, 1.0, 1.25, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]
BASE_COST = 0.87            # pt per round turn (provisional, user-unconfirmed)
EXTRA = [0.0, 0.5, 1.0]     # extra slippage: +1 tick/side, +2 ticks/side

def F(v):
    try: return float(v)
    except: return None

def mname(m):
    s = ('%g' % m); return s + 'R'

# frozen parent features
par = {}
for f in sorted(glob.glob(os.path.join(D, 'v4_1_structure_MNQ_v41_*.csv'))):
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isControl']] == 'TRUE' or row[i['f_isWarmup']] == 'TRUE': continue
            pid = row[i['parentEventId']]; et = row[i['f_barCloseEt']]
            if pid in par and par[pid][0] <= et: continue
            par[pid] = (et,
                        row[i['f_formationType']],
                        row[i['f_formationSecondLegConfirmed']] == 'TRUE',
                        row[i['f_formationInvalidated']] == 'TRUE',
                        row[i['f_vectorColor_15m']],
                        row[i['f_vectorExitsFormation']] == 'TRUE',
                        row[i['f_formationBreakConfirmed']] == 'TRUE',
                        row[i['f_ema800Ready_15m']] == 'TRUE')

T = []
for f in sorted(glob.glob(os.path.join(D, 'v4_1_entries_MNQ_v41_*.csv'))):
    with open(f, newline='') as fh:
        r = csv.reader(fh); h = next(r); i = {c: n for n, c in enumerate(h)}
        for row in r:
            if len(row) != len(h): continue
            if row[i['f_isWarmup']] == 'TRUE': continue
            if row[i['f_architecture']] != 'ARCH-B': continue
            if row[i['f_side']] != '1': continue
            p = par.get(row[i['parentEventId']])
            if p is None: continue
            et, form, leg2, finv, color, fexit, fbrk, e800 = p
            if not (form == 'W' and leg2 and not finv and color in ('GREEN', 'BLUE')
                    and (fexit or fbrk) and e800): continue
            sm = F(row[i['f_stopMediumPts']])
            if sm is None or sm <= 0: continue
            t = {'pid': row[i['parentEventId']],
                 'et': row[i['f_entryEt']], 'day': row[i['f_entryEt']][:10],
                 'sm': sm,
                 'st': F(row[i['f_stopTightPts']]),
                 'ss': F(row[i['f_stopStructuralPts']]),
                 'net240': F(row[i['y_net_240m']]) or 0.0,
                 'mfe': F(row[i['y_maxMfePts']]) or 0.0,
                 'mae': F(row[i['y_maxMaePts']]) or 0.0,
                 'hitT': row[i['y_hitStopTight']] == 'TRUE',
                 'hitM': row[i['y_hitStopMedium']] == 'TRUE',
                 'hitS': row[i['y_hitStopStructural']] == 'TRUE',
                 'taT': row[i['y_targetAfterStopTight']] == 'TRUE',
                 'taM': row[i['y_targetAfterStopMedium']] == 'TRUE',
                 'taS': row[i['y_targetAfterStopStructural']] == 'TRUE',
                 'emaR': F(row[i['y_emaExitGrossR']]),
                 'emaMins': F(row[i['y_minsToEmaExit']]),
                 'swHit': row[i['y_hitTargetSwing']] == 'TRUE',
                 'swMin': F(row[i['y_minsToTargetSwing']]),
                 'swPts': F(row[i['f_targetSwingDistPts']]),
                 'vzValid': row[i['f_targetVectorZoneValid']] == 'TRUE',
                 'vzHit': row[i['y_hitTargetVectorZone']] == 'TRUE',
                 'vzPts': F(row[i['f_targetVectorZoneDistPts']]),
                 'races': {}, 'mins': {}}
            for m in MULTS:
                t['races'][m] = row[i['y_race_' + mname(m)]]
                t['mins'][m] = F(row[i['y_minsTo_' + mname(m)]])
            T.append(t)

def split_rows(s):
    a, b = SPLITS[s]; return [t for t in T if a <= t['day'] <= b]

def pct(v, q):
    if not v: return float('nan')
    v = sorted(v); k = (len(v) - 1) * q
    lo = int(k); hi = min(lo + 1, len(v) - 1)
    return v[lo] + (v[hi] - v[lo]) * (k - lo)

print('=' * 100)
print('STEP 1 - ENTRY SAMPLE (frozen; membership function byte-identical to confirm.py)')
for s in SPLITS:
    rows = split_rows(s)
    ds = sorted(set(t['day'] for t in rows))
    pids = set(t['pid'] for t in rows)
    ets = sorted(t['et'] for t in rows)
    print('%s  n=%d  parents=%d  days=%d  first=%s  last=%s  long-only=YES' % (
        s, len(rows), len(pids), len(ds), ets[0] if ets else '-', ets[-1] if ets else '-'))
    # same-day multiplicity (thesis overlap watch)
    perday = defaultdict(int)
    for t in rows: perday[t['day']] += 1
    multi = sum(1 for v in perday.values() if v > 1)
    print('      days with >1 entry: %d (max %d)' % (multi, max(perday.values()) if perday else 0))

print('\nSTEP 2 - STOP DEFINITIONS (as frozen/captured; averages over DEV+VAL)')
allr = split_rows('DEV') + split_rows('VAL')
for tag, key in (('TIGHT', 'st'), ('MEDIUM (PRIMARY, frozen)', 'sm'), ('STRUCTURAL', 'ss')):
    v = [t[key] for t in allr if t[key]]
    if v:
        print('  %-26s n=%3d  mean %6.2f pt  median %6.2f pt' % (tag, len(v), sum(v)/len(v), pct(v, 0.5)))
print('  Fixed-R races were captured against MEDIUM only (f_raceStopFamily=MEDIUM).')
print('  TIGHT/STRUCTURAL get hit-rate + later-target diagnostics, not fabricated races.')

def ev_table(rows, m, extra):
    """returns dict of stats for one R multiple at MEDIUM stop."""
    w = l = a = to = 0; res = []; netsum = 0.0; hold = []
    seq = []
    for t in sorted(rows, key=lambda x: x['et']):
        costR = (BASE_COST + extra) / t['sm']
        o = t['races'][m]
        if o == 'TARGET':
            w += 1; r = m
            hold.append(t['mins'][m] or 0)
        elif o == 'STOP':
            l += 1; r = -1.0
            hold.append(t['mins'][m] or 0)
        elif o == 'AMBIGUOUS':
            a += 1; continue
        else:
            to += 1; r = t['net240'] / t['sm']; hold.append(240)
        res.append(r - costR); netsum += r - costR
        seq.append(r - costR)
    n = w + l + to
    if n == 0: return None
    ev = netsum / n
    peak = dd = cum = 0.0
    for x in seq:
        cum += x
        if cum > peak: peak = cum
        if peak - cum > dd: dd = peak - cum
    posR = sum(x for x in res if x > 0); negR = -sum(x for x in res if x < 0)
    return dict(n=n, w=w, l=l, amb=a, to=to,
                win=w / n, ev=ev, tot=netsum,
                pf=(posR / negR if negR > 0 else float('inf')),
                med=pct(res, 0.5), dd=dd,
                hold=sum(hold) / len(hold) if hold else 0)

for s in SPLITS:
    rows = split_rows(s)
    print('\nSTEP 3 - FIXED R:R AT MEDIUM STOP - %s  (base cost %.2f pt RT; EV in R/trade)' % (s, BASE_COST))
    print('%6s %5s %4s %4s %4s %4s %6s %8s %8s %6s %7s %8s %7s' % (
        'target', 'n', 'W', 'L', 'amb', 'TO', 'win%', 'netEV_R', 'totR', 'PF', 'medR', 'maxDD_R', 'hold_m'))
    for m in MULTS:
        e = ev_table(rows, m, 0.0)
        if e is None: continue
        print('%6s %5d %4d %4d %4d %4d %5.1f%% %+8.3f %+8.1f %6.2f %+7.2f %8.1f %7.0f' % (
            mname(m), e['n'], e['w'], e['l'], e['amb'], e['to'],
            100 * e['win'], e['ev'], e['tot'], e['pf'], e['med'], e['dd'], e['hold']))

print('\nSTEP 4 - MFE / MAE DISTRIBUTION (R vs MEDIUM stop)')
for s in SPLITS:
    rows = split_rows(s)
    mfeR = [t['mfe'] / t['sm'] for t in rows]
    maeR = [t['mae'] / t['sm'] for t in rows]
    for tag, v in (('MFE', mfeR), ('MAE', maeR)):
        print('  %s %-3s  p25 %5.2f  med %5.2f  p75 %5.2f  p90 %5.2f  p95 %5.2f  max %6.2f' % (
            s, tag, pct(v, .25), pct(v, .5), pct(v, .75), pct(v, .9), pct(v, .95), max(v)))
    line = '  %s reach-before-stop:' % s
    for m in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 4.0, 5.0]:
        res = [t['races'][m] for t in rows]
        n = sum(1 for o in res if o in ('TARGET', 'STOP', 'TIMEOUT'))
        wn = sum(1 for o in res if o == 'TARGET')
        line += '  +%gR:%4.1f%%' % (m, 100.0 * wn / n if n else 0)
    print(line)

print('\nSTEP 5 - STOPPED, THEN LATER REACHED (MFE after the MEDIUM stop, same 240m window)')
for s in SPLITS:
    rows = split_rows(s)
    stopped1 = [t for t in rows if t['races'][1.0] == 'STOP']
    print('  %s stopped@1R n=%d' % (s, len(stopped1)))
    for m in [1.0, 1.5, 2.0, 3.0]:
        k = sum(1 for t in rows if t['races'][m] == 'STOP' and t['mfe'] / t['sm'] >= m)
        ns = sum(1 for t in rows if t['races'][m] == 'STOP')
        print('    stopped@%gR then reached +%gR: %3d of %3d (%.1f%%)' % (
            m, m, k, ns, 100.0 * k / ns if ns else 0))
    print('    reference-target-after-stop flags: tight %d  medium %d  structural %d' % (
        sum(t['taT'] for t in rows), sum(t['taM'] for t in rows), sum(t['taS'] for t in rows)))

print('\nSTEP 2b - OTHER STOP FAMILIES (captured diagnostics only)')
for s in SPLITS:
    rows = split_rows(s)
    for tag, key, hit in (('TIGHT', 'st', 'hitT'), ('MEDIUM', 'sm', 'hitM'), ('STRUCTURAL', 'ss', 'hitS')):
        v = [t for t in rows if t[key]]
        if not v: continue
        hr = sum(t[hit] for t in v) / len(v)
        maeR = [t['mae'] / t[key] for t in v]
        print('  %s %-10s n=%3d  stop-hit-in-window %5.1f%%  medMAE %5.2fR' % (
            s, tag, len(v), 100 * hr, pct(maeR, .5)))

print('\nSTEP 7 - YEAR-BY-YEAR (MEDIUM stop, net EV R/trade @ base cost)')
years = ['2019', '2020', '2021', '2022', '2023', '2024']
for m in [1.0, 1.5, 2.0, 2.5, 3.0]:
    line = '  %-5s' % mname(m)
    for y in years:
        rows = [t for t in T if t['day'][:4] == y and t['day'] <= '2024-06-30']
        e = ev_table(rows, m, 0.0)
        line += ' %s:%s' % (y, ('%+0.2f/n%d' % (e['ev'], e['n'])) if e else '   -   ')
    print(line)

print('\nSTEP 9 - COST SENSITIVITY (net EV R/trade, DEV | VAL)')
for m in [1.0, 1.5, 2.0, 2.5, 3.0]:
    line = '  %-5s' % mname(m)
    for ex, tag in zip(EXTRA, ['base', '+1tick/side', '+2ticks/side']):
        ed = ev_table(split_rows('DEV'), m, ex)
        ev = ev_table(split_rows('VAL'), m, ex)
        line += '  %s: %+0.3f|%+0.3f' % (tag, ed['ev'] if ed else 0, ev['ev'] if ev else 0)
    print(line)

print('\nSTEP 10 - CLASS D MANAGEMENT EXPLORATION (same frozen entries, MEDIUM-stop R units)')
for s in SPLITS:
    rows = split_rows(s)
    cost = [(BASE_COST) / t['sm'] for t in rows]
    # unconditional EMA9 (captured management representation)
    ema = [t['emaR'] - c for t, c in zip(rows, cost) if t['emaR'] is not None]
    # structural swing target: hit -> +dist/stop else residual 240m
    sw = []
    for t, c in zip(rows, cost):
        if t['swPts'] and t['swPts'] > 0:
            sw.append((t['swPts'] / t['sm'] if t['swHit'] else t['net240'] / t['sm']) - c)
    vz = []
    for t, c in zip(rows, cost):
        if t['vzValid'] and t['vzPts'] and t['vzPts'] > 0:
            vz.append((t['vzPts'] / t['sm'] if t['vzHit'] else t['net240'] / t['sm']) - c)
    for tag, v in (('1m EMA9 trail (uncond.)', ema), ('structural swing target', sw),
                   ('pre-existing vector zone', vz)):
        if v:
            print('  %s %-26s n=%3d  mean %+0.3f R  med %+0.3f R' % (s, tag, len(v), sum(v)/len(v), pct(v, .5)))
print('  NOTE: the preregistered conditional-EMA9 variant (only in strong 1m trend)')
print('  is NOT computable: no causal 1m trend-state feature was frozen into the')
print('  capture. Reported EMA9 is unconditional. A trend-gated version would need')
print('  a new preregistered feature and fresh data.')
