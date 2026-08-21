#!/usr/bin/env python3
# ======================================================================
# SUB-MINUTE EXECUTION STUDY - OFH6 delta bias + liquidity sweep + reclaim
# Declared 2026-08-21 before first run. EXECUTION-TIMING study only:
# the 1m ordinary-reclaim result (+18.3, ratio 1.407) is ALREADY SEEN and
# nothing here is confirmatory evidence of that edge. The single question:
# does a completed-30s reclaim enter the SAME frozen parent event at a
# better location than the completed-1m reclaim?
#
# DATA AUDIT RESULT (measured, this session):
#   30s bars EXIST: V3 phase-2 capture, 09:30:00-11:00:30 ET close-
#   stamped, complete 182-slot grid on ALL 147 days of the 7 overlap
#   months 2025-11..2026-05, price basis IDENTICAL to the OF capture
#   (3,726/3,726 matched 1m closes, zero offset; 1,800/1,800 exact
#   30s->1m aggregation matches). OHLCV only - no bid/ask at 30s.
#   15s / 10s / 5s / tick: DO NOT EXIST anywhere. Those arms are
#   INSUFFICIENT DATA by audit and are not simulated or interpolated.
#
# FROZEN DECLARATIONS (before any result was seen):
#   Parent = frozen-OFH6 context active (life 30 primary; 15/60
#   sensitivity) + first-breach sweep of SW3/SW15/PDL level (identical
#   machinery to ofht_spec/ofht_run). Sweep MOMENT for this study = close
#   of the first breaching 30s bar (earliest causal observation), located
#   inside the 1m breach bar. Parent eligible only when the full reclaim
#   search window [sweep, sweep+5min] lies inside the 30s coverage.
#   1m arm  = first COMPLETED 1m bar closing back through the level
#             (sweep bar included, NO vector requirement), within the
#             existing frozen window (sweep 1m bar + 5 completed bars)
#             and before the existing 0.5-ATR adverse-close void.
#   30s arm = first COMPLETED 30s bar closing back through the level
#             (breaching 30s bar included), within 5 minutes of the sweep
#             moment (1m/3m reported as sensitivity), before the same
#             1m-evaluated void moment.
#   Both arms also expire with the OFH6 context (entry - activating
#   signal <= life). Arms are searched INDEPENDENTLY - no requirement
#   that both trigger.
#   ATR normalisation = the 1m ATR at the sweep 1m bar (same for both
#   arms). R per arm = entry - (that arm's sweep extreme at entry -+ one
#   tick). Forward path = 30s bars to 11:00:30 then 1m bars (resolution
#   hierarchy documented in every race; same hierarchy for both arms).
#   Races that resolve both levels inside one bar are AMBIGUOUS.
#   Costs: base 0.87 pt RT; sensitivity +1 tick (0.25) and +2 ticks
#   (0.50) additional adverse round-trip.
#   DEV = 2025-11..2026-03, INTERNAL REPLICATION = 2026-04..05.
#   INTERNAL HISTORICAL RESEARCH ONLY. No live trading is authorized.
# ======================================================================

import os, sys, csv, glob, random, datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ofh6_spec as F6
from ofht_cache import load as load_bars3
from ofht_spec import (TICK, DEV_END, attach_dsum15, aggregate, swings,
                       prevday_levels, Context)

random.seed(41)
SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COST = 0.87
LIFE = 30
SEARCH_SEC = 300
VOID_ATR = 0.5
SUB_MONTHS = ('2025-11', '2026-05')

B = load_bars3()
attach_dsum15(B)
N = len(B)
ELIG6 = F6.eligible(B)
SIGS = F6.signals(B, ELIG6)
assert len(SIGS) == 783
CTX = Context(SIGS, B)

AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
PDL = prevday_levels(B)

# ---- 30s grid ---------------------------------------------------------
S30 = defaultdict(dict)        # day -> sec-of-day -> (o,h,l,c)
dupbad = 0
for f in sorted(glob.glob(SCR + '/ph2/V3_30s_*.csv')):
    m = f[-10:-4]
    mm = m[:4] + '-' + m[4:]
    if mm < SUB_MONTHS[0] or mm > SUB_MONTHS[1]:
        continue
    for r in csv.DictReader(open(f)):
        if r['timeframe'] != '30s':
            continue
        h, mi, se = map(int, r['timeEt'].split(':'))
        sec = h * 3600 + mi * 60 + se
        bar = (float(r['open']), float(r['high']), float(r['low']), float(r['close']))
        old = S30[r['date']].get(sec)
        if old is not None and old != bar:
            dupbad += 1
        S30[r['date']][sec] = bar
DAYS30 = set(S30)
print('30s grid: %d days, duplicate-timestamp OHLC conflicts: %d' % (len(DAYS30), dupbad))

# per-day 1m bars (sec-of-day -> index) for the hybrid path
DAY1M = defaultdict(list)
for j in range(N):
    et = B[j]['et']
    h, mi, se = int(et[11:13]), int(et[14:16]), int(et[17:19])
    B[j]['sod'] = h * 3600 + mi * 60 + se
    DAY1M[B[j]['day']].append(j)

# ---- episodes (identical level machinery; entryAny = any close-through)
LOWEV = sorted([(t, lv, 'SW3') for t, lv in SW3L] + [(t, lv, 'SW15') for t, lv in SW15L])
HIGHEV = sorted([(t, hv, 'SW3') for t, hv in SW3H] + [(t, hv, 'SW15') for t, hv in SW15H])
slots = {k: None for k in [(a, b) for a in 'LH' for b in ('SW3', 'SW15', 'PDL')]}
EPIS = []
open_eps = []
li = hi = 0
curday = None
for j in range(N):
    b = B[j]
    if b['day'] != curday:
        curday = b['day']
        pd = PDL.get(curday)
        slots[('H', 'PDL')] = pd[0] if pd else None
        slots[('L', 'PDL')] = pd[1] if pd else None
    while li < len(LOWEV) and LOWEV[li][0] <= b['tmin']:
        slots[('L', LOWEV[li][2])] = LOWEV[li][1]
        li += 1
    while hi < len(HIGHEV) and HIGHEV[hi][0] <= b['tmin']:
        slots[('H', HIGHEV[hi][2])] = HIGHEV[hi][1]
        hi += 1
    for ep in open_eps:
        ep['idx'] += 1
        if ep['idx'] > 5 or B[j]['tmin'] != B[ep['j0']]['tmin'] + ep['idx']:
            ep['dead'] = True
            continue
        s = ep['s']
        ext = b['low'] if s > 0 else b['high']
        if (s > 0 and ext < ep['ext']) or (s < 0 and ext > ep['ext']):
            ep['ext'] = ext
        if not ep['void']:
            if (s > 0 and b['close'] < ep['lvl'] - VOID_ATR * ep['atr0']) or \
               (s < 0 and b['close'] > ep['lvl'] + VOID_ATR * ep['atr0']):
                ep['void'] = True
                ep['voidJ'] = j
        if ep['e1m'] is None and not ep['void']:
            if (s > 0 and b['close'] > ep['lvl']) or (s < 0 and b['close'] < ep['lvl']):
                ep['e1m'] = j
                ep['ext1m'] = ep['ext']
    open_eps = [e for e in open_eps if not e.get('dead')]
    for side, s in (('L', 1), ('H', -1)):
        hit = []
        for typ in ('SW3', 'SW15', 'PDL'):
            lvl = slots[(side, typ)]
            if lvl is None:
                continue
            if (s > 0 and b['low'] < lvl) or (s < 0 and b['high'] > lvl):
                hit.append((typ, lvl))
                slots[(side, typ)] = None
        if not hit:
            continue
        lvl = max(h[1] for h in hit) if s > 0 else min(h[1] for h in hit)
        ep = {'s': s, 'd': s, 'lvl': lvl, 'types': [h[0] for h in hit],
              'j0': j, 'idx': 0, 'atr0': b['atr'] or 0.0,
              'ext': b['low'] if s > 0 else b['high'],
              'void': False, 'voidJ': None, 'e1m': None, 'ext1m': None}
        if ep['atr0'] <= 0:
            continue
        if (s > 0 and b['close'] > lvl) or (s < 0 and b['close'] < lvl):
            ep['e1m'] = j
            ep['ext1m'] = ep['ext']
        EPIS.append(ep)
        open_eps.append(ep)

# ---- parents: context + 30s coverage ---------------------------------
def bars30(day, a, bq):
    g = S30.get(day, {})
    return [(sec, g[sec]) for sec in range(a, bq + 1, 30)
            if sec % 30 == 0 and sec in g]


PARENTS = []
for ep in EPIS:
    d = ep['d']
    j0 = ep['j0']
    day = B[j0]['day']
    if day not in DAYS30:
        continue
    ts = CTX.activating(d, B[j0]['tmin'])
    if ts is None or B[j0]['tmin'] - ts > LIFE:
        continue
    if CTX.opposite_in(d, ts, B[j0]['tmin']):
        continue
    # locate first breaching 30s bar inside the 1m breach bar
    m_end = B[j0]['sod']
    cands = bars30(day, m_end - 30, m_end)
    sw = None
    for sec, (o, h, l, c) in cands:
        if (d > 0 and l < ep['lvl']) or (d < 0 and h > ep['lvl']):
            sw = (sec, (o, h, l, c))
            break
    if sw is None:
        continue                      # breach not visible on 30s grid
    if sw[0] + SEARCH_SEC > 11 * 3600 + 30:
        continue                      # search window leaves 30s coverage
    if len(bars30(day, sw[0], sw[0] + SEARCH_SEC)) < SEARCH_SEC // 30 + 1:
        continue
    PARENTS.append({'ep': ep, 'day': day, 'd': d, 'lvl': ep['lvl'],
                    'ts': ts, 'swSec': sw[0], 'atr0': ep['atr0'],
                    'sp': 'DEV' if day <= DEV_END else 'IR'})

print('eligible parents (ctx sweep, 30s-covered): %d  (of %d ctx sweeps ctx sweeps on covered days)'
      % (len(PARENTS), sum(1 for ep in EPIS if B[ep['j0']]['day'] in DAYS30
           and CTX.activating(ep['d'], B[ep['j0']]['tmin']) is not None
           and B[ep['j0']]['tmin'] - CTX.activating(ep['d'], B[ep['j0']]['tmin']) <= LIFE)))

# ---- arm entries ------------------------------------------------------
for p in PARENTS:
    ep = p['ep']
    d = p['d']
    day = p['day']
    voidSec = B[ep['voidJ']]['sod'] if ep['voidJ'] is not None else 10 ** 9
    # 1m arm (frozen definition; entry must respect ctx life)
    p['e1m'] = None
    if ep['e1m'] is not None:
        te = B[ep['e1m']]['tmin']
        if te - p['ts'] <= LIFE and not CTX.opposite_in(d, p['ts'], te):
            p['e1m'] = {'sec': B[ep['e1m']]['sod'], 'px': B[ep['e1m']]['close'],
                        'ext': ep['ext1m']}
    # 30s arm
    p['e30'] = None
    ext = None
    for sec, (o, h, l, c) in bars30(day, p['swSec'], p['swSec'] + SEARCH_SEC):
        if sec >= voidSec:
            break
        e = l if d > 0 else h
        if ext is None or (d > 0 and e < ext) or (d < 0 and e > ext):
            ext = e
        if (d > 0 and c > p['lvl']) or (d < 0 and c < p['lvl']):
            tmin_e = (B[ep['j0']]['tmin'] - B[ep['j0']]['sod'] // 60) + sec / 60.0
            if tmin_e - p['ts'] > LIFE or CTX.opposite_in(d, p['ts'], int(tmin_e)):
                break
            p['e30'] = {'sec': sec, 'px': c, 'ext': ext}
            break

# ---- hybrid forward path ---------------------------------------------
def hybrid(day, sec0, horizon_sec):
    out = []
    for sec, (o, h, l, c) in bars30(day, sec0 + 30, min(11 * 3600 + 30, sec0 + horizon_sec)):
        out.append((sec, h, l, c, '30s'))
    for j in DAY1M[day]:
        s = B[j]['sod']
        if s > 11 * 3600 + 30 and s <= sec0 + horizon_sec:
            out.append((s, B[j]['high'], B[j]['low'], B[j]['close'], '1m'))
    out.sort()
    return out


def arm_geom(p, e):
    d = p['d']
    atr = p['atr0']
    R = (e['px'] - (e['ext'] - TICK)) if d > 0 else ((e['ext'] + TICK) - e['px'])
    path = hybrid(p['day'], e['sec'], 3600)
    res = {'R': R, 'risk': R, 'mfe': {}, 'mae': {}, 'net': {}}
    ff = {}
    for pair in ((0.25, 0.25), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0)):
        ff[pair] = 0
    rr = {}
    for pair in ((0.5, 1.0), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (3.0, 1.0)):
        rr[pair] = 0
    rebreak = dict((w, 0) for w in (30, 60, 120, 180, 300))
    mfe = mae = 0.0
    hz = [300, 600, 900, 1800, 3600]
    hi = 0
    lastc = e['px']
    for sec, h, l, c, gran in path:
        fav = (h - e['px']) if d > 0 else (e['px'] - l)
        adv = (e['px'] - l) if d > 0 else (h - e['px'])
        if fav > mfe:
            mfe = fav
        if adv > mae:
            mae = adv
        for pair in ff:
            if ff[pair]:
                continue
            hf = fav >= pair[0] * atr
            ha = adv >= pair[1] * atr
            ff[pair] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
        for pair in rr:
            if rr[pair] or R <= 0:
                continue
            hf = fav >= pair[0] * R
            ha = adv >= pair[1] * R
            rr[pair] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
        breach = (l <= e['ext']) if d > 0 else (h >= e['ext'])
        if breach:
            dt = sec - e['sec']
            for w in rebreak:
                if not rebreak[w] and dt <= w:
                    rebreak[w] = 1
        lastc = c
        while hi < len(hz) and sec - e['sec'] >= hz[hi]:
            res['mfe'][hz[hi]] = mfe
            res['mae'][hz[hi]] = mae
            res['net'][hz[hi]] = (c - e['px']) * d
            hi += 1
    while hi < len(hz):
        res['mfe'][hz[hi]] = mfe
        res['mae'][hz[hi]] = mae
        res['net'][hz[hi]] = (lastc - e['px']) * d
        hi += 1
    res['ff'] = ff
    res['rr'] = rr
    res['rebreak'] = rebreak
    return res


for p in PARENTS:
    for arm in ('e1m', 'e30'):
        if p[arm] is not None:
            p[arm]['g'] = arm_geom(p, p[arm])

# ================================================== REPORT
def fmt_ff(gs, key):
    fav = sum(1 for g in gs if g['ff'][key] == 1)
    adv = sum(1 for g in gs if g['ff'][key] == 2)
    amb = sum(1 for g in gs if g['ff'][key] == 3)
    return ('%4.1f%%(amb%2.0f%%)' % (100.0 * fav / (fav + adv), 100.0 * amb / len(gs))
            if fav + adv else '   -')


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


both = [p for p in PARENTS if p['e1m'] and p['e30']]
only30 = [p for p in PARENTS if p['e30'] and not p['e1m']]
only1m = [p for p in PARENTS if p['e1m'] and not p['e30']]
none = [p for p in PARENTS if not p['e1m'] and not p['e30']]
print('\n' + '=' * 108)
print('TRIGGERS   parents %d:  both %d   30s-only %d   1m-only %d   neither %d'
      % (len(PARENTS), len(both), len(only30), len(only1m), len(none)))
print('=' * 108)
for tag, sel in (('LONG', 1), ('SHORT', -1)):
    pp = [p for p in PARENTS if p['d'] == sel]
    print('  %s: parents %d  both %d  30s-only %d  1m-only %d'
          % (tag, len(pp), sum(1 for p in pp if p['e1m'] and p['e30']),
             sum(1 for p in pp if p['e30'] and not p['e1m']),
             sum(1 for p in pp if p['e1m'] and not p['e30'])))

for arm, tag in (('e1m', '1m reclaim'), ('e30', '30s reclaim')):
    gs = [p[arm]['g'] for p in PARENTS if p[arm]]
    ps = [p for p in PARENTS if p[arm]]
    lat = [p[arm]['sec'] - p['swSec'] for p in ps]
    risk = [g['R'] for g in gs]
    riskA = [g['R'] / p['atr0'] for g, p in zip(gs, ps)]
    print('\n--- %s: n=%d (%.0f%% of parents)  latency med %ds mean %ds'
          % (tag, len(gs), 100.0 * len(gs) / len(PARENTS), med(lat),
             sum(lat) / len(lat) if lat else 0))
    print('    risk to sweep-extreme stop: med %.2f pt (%.0f ticks, %.2f ATR)  mean %.2f pt'
          % (med(risk), med(risk) / TICK, med(riskA), sum(risk) / len(risk)))
    for hz, lbl in ((300, '5m'), (600, '10m'), (900, '15m'), (1800, '30m'), (3600, '60m')):
        mf = [g['mfe'][hz] for g in gs]
        ma = [g['mae'][hz] for g in gs]
        print('    %3s: medMFE %6.2f  medMAE %6.2f  ratio %5.3f'
              % (lbl, med(mf), med(ma), med(mf) / med(ma) if med(ma) else float('nan')))
    print('    ATR-first: 0.25 %s  0.5 %s  1.0 %s  1.5/1 %s  2/1 %s'
          % tuple(fmt_ff(gs, k) for k in ((0.25, 0.25), (0.5, 0.5), (1.0, 1.0),
                                          (1.5, 1.0), (2.0, 1.0))))
    def fmt_rr(k):
        fav = sum(1 for g in gs if g['rr'][k] == 1)
        adv = sum(1 for g in gs if g['rr'][k] == 2)
        amb = sum(1 for g in gs if g['rr'][k] == 3)
        return ('%4.1f%%(amb%2.0f%%)' % (100.0 * fav / (fav + adv), 100.0 * amb / len(gs))
                if fav + adv else '   -')
    print('    R-first (sweep stop): 0.5R %s  1R %s  1.5R %s  2R %s  3R %s'
          % tuple(fmt_rr(k) for k in ((0.5, 1.0), (1.0, 1.0), (1.5, 1.0),
                                      (2.0, 1.0), (3.0, 1.0))))
    print('    false-early re-break of sweep extreme within 30s/1m/2m/3m/5m: '
          + '/'.join('%.0f%%' % (100.0 * sum(g['rebreak'][w] for g in gs) / len(gs))
                     for w in (30, 60, 120, 180, 300)))
    for cadd, clbl in ((0.0, 'base 0.87'), (0.25, '+1 tick'), (0.5, '+2 ticks')):
        nets = [g['net'][3600] - COST - cadd for g in gs]
        print('    net @60m, cost %-9s mean %+7.2f  median %+7.2f'
              % (clbl + ':', sum(nets) / len(nets), med(nets)))

# paired comparison
print('\n' + '=' * 108)
print('PAIRED SAME-PARENT COMPARISON (n=%d)   improvement = better price for the trade direction' % len(both))
print('=' * 108)
if both:
    dpx = [( (p['e1m']['px'] - p['e30']['px']) * p['d'] ) for p in both]
    dsec = [p['e1m']['sec'] - p['e30']['sec'] for p in both]
    drisk = [p['e30']['g']['R'] - p['e1m']['g']['R'] for p in both]
    dmae = [p['e30']['g']['mae'][3600] - p['e1m']['g']['mae'][3600] for p in both]
    dmfe = [p['e30']['g']['mfe'][3600] - p['e1m']['g']['mfe'][3600] for p in both]
    dnet = [p['e30']['g']['net'][3600] - p['e1m']['g']['net'][3600] for p in both]
    atr = [p['atr0'] for p in both]
    def q(v, f):
        s = sorted(v)
        return s[int(len(s) * f)]
    print('  entry-price improvement (30s vs 1m): mean %+0.2f  med %+0.2f  p25 %+0.2f  p75 %+0.2f  p90 %+0.2f pt'
          % (sum(dpx) / len(dpx), med(dpx), q(dpx, .25), q(dpx, .75), q(dpx, .90)))
    print('     = %+0.1f ticks median, %+0.3f ATR median; earlier by med %ds; %% entering earlier %.0f%%; %% worse price %.0f%%'
          % (med(dpx) / TICK, med([a / b for a, b in zip(dpx, atr)]),
             med(dsec), 100.0 * sum(1 for x in dsec if x > 0) / len(dsec),
             100.0 * sum(1 for x in dpx if x < 0) / len(dpx)))
    print('  risk delta (30s-1m): mean %+0.2f  med %+0.2f pt' % (sum(drisk) / len(drisk), med(drisk)))
    print('  MAE60 delta: mean %+0.2f med %+0.2f   MFE60 delta: mean %+0.2f med %+0.2f   net60 delta: mean %+0.2f med %+0.2f'
          % (sum(dmae) / len(dmae), med(dmae), sum(dmfe) / len(dmfe), med(dmfe),
             sum(dnet) / len(dnet), med(dnet)))
    byday = defaultdict(list)
    for p, x in zip(both, dpx):
        byday[p['day']].append(x)
    pools = list(byday.values())
    boots = []
    for _ in range(4000):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        boots.append(sum(s) / len(s))
    boots.sort()
    print('  day-clustered paired bootstrap, entry improvement: 95%% CI [%+0.3f, %+0.3f]'
          % (boots[100], boots[3899]))
    byday2 = defaultdict(list)
    for p, x in zip(both, dnet):
        byday2[p['day']].append(x)
    pools2 = list(byday2.values())
    boots2 = []
    for _ in range(4000):
        s = [x for dd in random.choices(pools2, k=len(pools2)) for x in dd]
        boots2.append(sum(s) / len(s))
    boots2.sort()
    print('  day-clustered paired bootstrap, net60 delta:      95%% CI [%+0.3f, %+0.3f]'
          % (boots2[100], boots2[3899]))

# splits / months / sensitivity
print('\n' + '=' * 108)
print('STABILITY')
print('=' * 108)
for arm, tag in (('e1m', '1m'), ('e30', '30s')):
    for sp in ('DEV', 'IR'):
        gs = [p[arm]['g'] for p in PARENTS if p[arm] and p['sp'] == sp]
        if not gs:
            print('  %-4s %s n=0' % (tag, sp))
            continue
        nets = [g['net'][3600] - COST for g in gs]
        mf = med([g['mfe'][3600] for g in gs])
        ma = med([g['mae'][3600] for g in gs])
        print('  %-4s %-3s n=%3d  net60 mean %+7.2f med %+7.2f  ratio %5.3f  ff1 %s'
              % (tag, sp, len(gs), sum(nets) / len(nets), med(nets),
                 mf / ma if ma else float('nan'), fmt_ff(gs, (1.0, 1.0))))
bym = defaultdict(lambda: defaultdict(list))
for p in PARENTS:
    for arm in ('e1m', 'e30'):
        if p[arm]:
            bym[p['day'][:7]][arm].append(p[arm]['g']['net'][3600] - COST)
print('  months (net60 mean, n):')
for m in sorted(bym):
    r = '    %s ' % m
    for arm in ('e1m', 'e30'):
        v = bym[m][arm]
        r += ' %s n=%2d %+7.2f |' % (arm[1:], len(v), sum(v) / len(v) if v else float('nan'))
    print(r)
c30 = [p for p in PARENTS if p['e30']]
for cut, lbl in ((60, '1m'), (180, '3m')):
    sub = [p['e30']['g'] for p in c30 if p['e30']['sec'] - p['swSec'] <= cut]
    if sub:
        nets = [g['net'][3600] - COST for g in sub]
        print('  sensitivity: 30s entries with latency <= %s: n=%d  net60 %+0.2f'
              % (lbl, len(sub), sum(nets) / len(nets)))
tot = sorted((p['e30']['g']['net'][3600] - COST for p in c30), reverse=True)
if tot:
    for pct in (0.01, 0.05):
        k = max(1, int(len(tot) * pct))
        print('  30s concentration: top %2.0f%% (%d tr) = %+0.1f of total %+0.1f'
              % (pct * 100, k, sum(tot[:k]), sum(tot)))

# stop family
print('\n' + '=' * 108)
print('STOP FAMILY (exact race on the hybrid path, 60m cap; stop-first on ambiguous bars)')
print('=' * 108)


def stop_race(p, e, stopdist):
    d = p['d']
    spx = e['px'] - d * stopdist
    for sec, h, l, c, gran in hybrid(p['day'], e['sec'], 3600):
        if (d > 0 and l <= spx) or (d < 0 and h >= spx):
            return -stopdist
    path = hybrid(p['day'], e['sec'], 3600)
    return (path[-1][3] - e['px']) * d if path else 0.0


for arm, tag in (('e1m', '1m'), ('e30', '30s')):
    ps = [p for p in PARENTS if p[arm]]
    row = '  %-4s' % tag
    for mode, lbl in (('sweep', 'sweep-ext'), (1.0, '1.0ATR'), (1.5, '1.5ATR')):
        nets = []
        for p in ps:
            e = p[arm]
            S = e['g']['R'] if mode == 'sweep' else mode * p['atr0']
            if S <= 0:
                continue
            nets.append(stop_race(p, e, S) - COST)
        row += '  %s: mean %+6.2f win%% %4.1f (n=%d)' % (
            lbl, sum(nets) / len(nets) if nets else float('nan'),
            100.0 * sum(1 for x in nets if x > 0) / len(nets) if nets else 0, len(nets))
    print(row)
print('\nNOTE fixed-R target grid: run ONLY if geometry survives - decided in the findings doc.')
