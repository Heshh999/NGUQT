#!/usr/bin/env python3
# OFH7-OFH10 TIMING FAMILY - the run. Every parameter comes from
# ofht_spec.py (declared before this file first ran) and ofh6_spec.py
# (frozen). Nothing here is tuned after results.

import os, sys, csv, math, random, bisect, datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ofh6_spec as F6
from ofht_cache import load as load_bars3
from ofht_spec import (TICK, COST, HORIZON, LIFE_PRIMARY, LIFE_FAMILY,
                       DEV_END, WICK_PCT, OFH7_WINDOW, OFH8_WINDOW,
                       OFH10_WINDOW, OFH7_VOID_ATR, OFH8_PROG_ATR,
                       OFH10_VOID_ATR, RECOVERY_FRAC, PARENT_LIFE_15M,
                       MIN_N, R_PAIRS, ATR_LEVELS, attach_dsum15,
                       vector_dirs, onem_view, aggregate, swings,
                       prevday_levels, Context, entry_ok, geometry)

random.seed(41)
SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'

B = load_bars3()
attach_dsum15(B)
N = len(B)
ELIG6 = F6.eligible(B)
SIGS = F6.signals(B, ELIG6)
assert len(SIGS) == 783, 'frozen signal stream mismatch: %d' % len(SIGS)

# entry-eligible baseline (60m horizon)
BASE = {}
_eb = [j for j in range(N) if entry_ok(B, j)]
for sp in ('DEV', 'IR'):
    for d in (1, -1):
        v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in _eb
             if ('DEV' if B[j]['day'] <= DEV_END else 'IR') == sp]
        BASE[(sp, d)] = sum(v) / len(v)

V1 = vector_dirs(onem_view(B))
AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
V15 = vector_dirs(AGG15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
PDL = prevday_levels(B)
CTX = Context(SIGS, B)

# price-momentum context: |15-bar price change| threshold matched to 783
# signals under the same eligibility and 30-min cooldown. Mechanical.
pm = {}
for j in ELIG6:
    if j >= 15 and B[j]['tmin'] - B[j - 15]['tmin'] == 15:
        pm[j] = B[j]['close'] - B[j - 15]['close']
pv = sorted(abs(v) for v in pm.values())


def pm_sigs(thr):
    out = []
    last = -10 ** 9
    for j in ELIG6:
        v = pm.get(j)
        if v is None or abs(v) < thr:
            continue
        if B[j]['tmin'] - last < 30:
            continue
        last = B[j]['tmin']
        out.append((j, 1 if v > 0 else -1))
    return out


best = None
for q in range(850, 995):
    thr = pv[min(int(len(pv) * q / 1000.0), len(pv) - 1)]
    s = pm_sigs(thr)
    if best is None or abs(len(s) - 783) < abs(len(best[1]) - 783):
        best = (thr, s)
PM_THR, PM_SIGS = best
CTXP = Context(PM_SIGS, B)
print('bars %d  frozen signals %d  pm-context thr %.2f pt -> %d signals'
      % (N, len(SIGS), PM_THR, len(PM_SIGS)))
print('baseline 60m (DEV L/S, IR L/S): %+.3f %+.3f / %+.3f %+.3f'
      % (BASE[('DEV', 1)], BASE[('DEV', -1)], BASE[('IR', 1)], BASE[('IR', -1)]))

# ---------------------------------------------------------------- episodes
# One context-free pass builds every sweep/trap episode; hypotheses and
# controls are then classifications of the same episodes.
LOWEV = sorted([(t, lv, 'SW3') for t, lv in SW3L] + [(t, lv, 'SW15') for t, lv in SW15L])
HIGHEV = sorted([(t, hv, 'SW3') for t, hv in SW3H] + [(t, hv, 'SW15') for t, hv in SW15H])
EPIS = []


slots = {('L', 'SW3'): None, ('L', 'SW15'): None, ('L', 'PDL'): None,
         ('H', 'SW3'): None, ('H', 'SW15'): None, ('H', 'PDL'): None}
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
    # advance open episodes with this bar
    for ep in open_eps:
        ep['idx'] += 1
        idx = ep['idx']
        if idx > OFH7_WINDOW:
            ep['dead'] = True
            continue
        if B[j]['tmin'] != B[ep['startJ']]['tmin'] + idx:
            ep['dead'] = True
            continue
        s = 1 if ep['side'] == 'L' else -1
        ext = b['low'] if s > 0 else b['high']
        if (s > 0 and ext < ep['extreme']) or (s < 0 and ext > ep['extreme']):
            ep['extreme'] = ext
        lvl = ep['level']
        # OFH7-style void
        if not ep['void7']:
            if (s > 0 and b['close'] < lvl - OFH7_VOID_ATR * ep['atr0']) or \
               (s < 0 and b['close'] > lvl + OFH7_VOID_ATR * ep['atr0']):
                ep['void7'] = True
        # OFH10-style void
        if not ep['void10']:
            if (s > 0 and b['close'] < lvl - OFH10_VOID_ATR * ep['atr0']) or \
               (s < 0 and b['close'] > lvl + OFH10_VOID_ATR * ep['atr0']):
                ep['void10'] = True
        reclaimed = (b['close'] > lvl) if s > 0 else (b['close'] < lvl)
        if reclaimed and not ep['void7']:
            if ep['entryOrd'] is None and V1[j] != s:
                ep['entryOrd'] = j
                ep['extOrd'] = ep['extreme']
            if ep['entryVec'] is None and V1[j] == s:
                ep['entryVec'] = j
                ep['extVec'] = ep['extreme']
        # OFH10 trap entry (window 3, breach bar must be opposite vector)
        if (ep['entry10'] is None and idx <= OFH10_WINDOW and not ep['void10']
                and ep['breachVec'] == -s):
            if s > 0:
                rec = b['high'] >= ep['vExt'] + RECOVERY_FRAC * ep['vRange']
                if b['close'] > lvl and rec:
                    ep['entry10'] = j
                    ep['ext10'] = ep['extreme']
            else:
                rec = b['low'] <= ep['vExt'] - RECOVERY_FRAC * ep['vRange']
                if b['close'] < lvl and rec:
                    ep['entry10'] = j
                    ep['ext10'] = ep['extreme']
    open_eps = [ep for ep in open_eps if not ep.get('dead')]
    # breach detection -> new episodes
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
        ep = {'side': side, 'level': lvl, 'types': [h[0] for h in hit],
              'startJ': j, 'startT': b['tmin'], 'idx': 0,
              'atr0': b['atr'] or 0.0,
              'extreme': b['low'] if s > 0 else b['high'],
              'breachVec': V1[j],
              'vExt': b['low'] if s > 0 else b['high'],   # breach-bar breakout extreme
              'vRange': b['high'] - b['low'],
              'void7': False, 'void10': False,
              'entryVec': None, 'entryOrd': None, 'entry10': None,
              'extVec': None, 'extOrd': None, 'ext10': None}
        if ep['atr0'] <= 0:
            continue
        # sweep bar itself may reclaim (OFH7)
        reclaimed = (b['close'] > lvl) if s > 0 else (b['close'] < lvl)
        if reclaimed:
            if V1[j] == s:
                ep['entryVec'] = j
                ep['extVec'] = ep['extreme']
            else:
                ep['entryOrd'] = j
                ep['extOrd'] = ep['extreme']
        EPIS.append(ep)
        open_eps.append(ep)

print('episodes: %d low-sweep, %d high-sweep'
      % (sum(1 for e in EPIS if e['side'] == 'L'),
         sum(1 for e in EPIS if e['side'] == 'H')))


def no_ctx(te):
    a = CTX.latest_le(1, te)
    bq = CTX.latest_le(-1, te)
    return (a is None or te - a > 60) and (bq is None or te - bq > 60)


def mkgeo(j, d, R):
    return geometry(B, j, d, R, BASE)


def R_of(entry_j, d, extreme):
    e = B[entry_j]['close']
    return (e - (extreme - TICK)) if d > 0 else ((extreme + TICK) - e)


# ------------------------------------------------------------ OFH7 sets
def ofh7_sets(ctx, life):
    prim, ords, noctx, per_type = [], [], [], defaultdict(list)
    for ep in EPIS:
        d = 1 if ep['side'] == 'L' else -1
        je = ep['entryVec']
        if je is not None and entry_ok(B, je):
            R = R_of(je, d, ep['extVec'])
            if R > 0:
                if ctx.ok(d, ep['startT'], B[je]['tmin'], life):
                    g = mkgeo(je, d, R)
                    prim.append(g)
                    for t in ep['types']:
                        per_type[t].append(g)
                if ctx is CTX and no_ctx(B[je]['tmin']):
                    noctx.append(mkgeo(je, d, R))
        jo = ep['entryOrd']
        if jo is not None and entry_ok(B, jo) and ctx.ok(d, ep['startT'], B[jo]['tmin'], life):
            R = R_of(jo, d, ep['extOrd'])
            if R > 0:
                ords.append(mkgeo(jo, d, R))
    return prim, ords, noctx, per_type


# vector-without-sweep control: same-dir 1m vector during context with no
# sweep episode open or started in the prior 5 bars. 15-min spacing.
def vec_no_sweep(ctx, life):
    recent = defaultdict(lambda: -10 ** 9)      # side -> last episode start
    starts = sorted((ep['startT'], 1 if ep['side'] == 'L' else -1) for ep in EPIS)
    out = []
    last = -10 ** 9
    si = 0
    lastep = {1: -10 ** 9, -1: -10 ** 9}
    for j in range(N):
        t = B[j]['tmin']
        while si < len(starts) and starts[si][0] <= t:
            lastep[starts[si][1]] = starts[si][0]
            si += 1
        d = V1[j]
        if d == 0 or not entry_ok(B, j):
            continue
        if t - lastep[d] <= 5:
            continue
        if not ctx.ok_at(d, t, life):
            continue
        if t - last < 15:
            continue
        last = t
        out.append(mkgeo(j, d, B[j]['atr']))
    return out


# ------------------------------------------------------------ OFH8 sets
AVGRNG = [None] * N
_acc = []
for j in range(N):
    if len(_acc) == 10:
        AVGRNG[j] = sum(_acc) / 10.0
    _acc.append(B[j]['high'] - B[j]['low'])
    if len(_acc) > 10:
        _acc.pop(0)


def ofh8_from(sig_rows, ctx, life, trigger='vector'):
    prim = []
    primD = []
    for js, d in sig_rows:
        ts = B[js]['tmin']
        jv = None
        for j in range(js + 1, min(js + life + 1, N)):
            if B[j]['tmin'] - ts > life:
                break
            if trigger == 'vector':
                if V1[j] == -d:
                    jv = j
                    break
            else:
                if V1[j] == 0 and AVGRNG[j] and \
                        (B[j]['high'] - B[j]['low']) >= 1.5 * AVGRNG[j] and \
                        ((d > 0 and B[j]['close'] < B[j]['open'])
                         or (d < 0 and B[j]['close'] > B[j]['open'])):
                    jv = j
                    break
        if jv is None:
            continue
        vH, vL = B[jv]['high'], B[jv]['low']
        vR = vH - vL
        vMid = (vH + vL) / 2.0
        atrV = B[jv]['atr'] or 0.0
        if vR <= 0 or atrV <= 0:
            continue
        recovered = False
        entry = None
        for k in range(1, OFH8_WINDOW + 1):
            j = jv + k
            if j >= N or B[j]['tmin'] != B[jv]['tmin'] + k:
                break
            c = B[j]
            if d > 0:
                if c['low'] < vL - OFH8_PROG_ATR * atrV:
                    break
                if c['high'] >= vL + RECOVERY_FRAC * vR:
                    recovered = True
                if recovered and c['close'] > vMid:
                    entry = j
                    break
            else:
                if c['high'] > vH + OFH8_PROG_ATR * atrV:
                    break
                if c['low'] <= vH - RECOVERY_FRAC * vR:
                    recovered = True
                if recovered and c['close'] < vMid:
                    entry = j
                    break
        if entry is None or not entry_ok(B, entry):
            continue
        te = B[entry]['tmin']
        if te - ts > life or ctx.opposite_in(d, ts, te):
            continue
        ext = vL if d > 0 else vH
        R = R_of(entry, d, ext)
        if R <= 0:
            continue
        g = mkgeo(entry, d, R)
        prim.append(g)
        if V1[entry] == d:
            primD.append(g)
    return prim, primD


def ofh8_noctx(life=30):
    out = []
    last = -10 ** 9
    for jv in range(N):
        dv = V1[jv]
        if dv == 0:
            continue
        d = -dv
        t = B[jv]['tmin']
        if not no_ctx(t) or t - last < 15:
            continue
        vH, vL = B[jv]['high'], B[jv]['low']
        vR = vH - vL
        vMid = (vH + vL) / 2.0
        atrV = B[jv]['atr'] or 0.0
        if vR <= 0 or atrV <= 0:
            continue
        recovered = False
        entry = None
        for k in range(1, OFH8_WINDOW + 1):
            j = jv + k
            if j >= N or B[j]['tmin'] != t + k:
                break
            c = B[j]
            if d > 0:
                if c['low'] < vL - OFH8_PROG_ATR * atrV:
                    break
                if c['high'] >= vL + RECOVERY_FRAC * vR:
                    recovered = True
                if recovered and c['close'] > vMid:
                    entry = j
                    break
            else:
                if c['high'] > vH + OFH8_PROG_ATR * atrV:
                    break
                if c['low'] <= vH - RECOVERY_FRAC * vR:
                    recovered = True
                if recovered and c['close'] < vMid:
                    entry = j
                    break
        if entry is None or not entry_ok(B, entry):
            continue
        ext = vL if d > 0 else vH
        R = R_of(entry, d, ext)
        if R <= 0:
            continue
        last = t
        out.append(mkgeo(entry, d, R))
    return out


# ------------------------------------------------------------ OFH9 sets
def parents(vec_required=True):
    out = []
    for k, a in enumerate(AGG15):
        d = V15[k]
        if vec_required:
            if d == 0:
                continue
        else:
            if d != 0:
                continue
            d = 1 if a['c'] > a['o'] else (-1 if a['c'] < a['o'] else 0)
            if d == 0:
                continue
        rng = a['h'] - a['l']
        if rng <= 0:
            continue
        wick = (min(a['o'], a['c']) - a['l']) if d > 0 else (a['h'] - max(a['o'], a['c']))
        if wick < WICK_PCT / 100.0 * rng:
            continue
        out.append({'d': d, 'jend': a['jend'], 'tmin': a['tmin'],
                    'low': a['l'], 'high': a['h'],
                    'wickTop': min(a['o'], a['c']) if d > 0 else None,
                    'wickBot': max(a['o'], a['c']) if d < 0 else None})
    return out


ZONE = set()


def ofh9_sets(ctx, life, plist, mark_zone=False):
    prim, ordz, noctx = [], [], []
    for p in plist:
        d = p['d']
        lifeEnd = p['tmin'] + PARENT_LIFE_15M * 15
        gotP = gotO = gotN = False
        for j in range(p['jend'] + 1, N):
            b = B[j]
            if b['tmin'] > lifeEnd:
                break
            if d > 0 and b['low'] < p['low']:
                break
            if d < 0 and b['high'] > p['high']:
                break
            inzone = (b['low'] <= p['wickTop']) if d > 0 else (b['high'] >= p['wickBot'])
            if inzone and mark_zone:
                ZONE.add((j, d))
            if not inzone or not entry_ok(B, j):
                continue
            ext = p['low'] if d > 0 else p['high']
            R = R_of(j, d, ext)
            if R <= 0:
                continue
            if V1[j] == d:
                if not gotP and ctx.ok_at(d, b['tmin'], life):
                    prim.append(mkgeo(j, d, R))
                    gotP = True
                if not gotN and ctx is CTX and no_ctx(b['tmin']):
                    noctx.append(mkgeo(j, d, R))
                    gotN = True
            else:
                if not gotO and ctx.ok_at(d, b['tmin'], life):
                    ordz.append(mkgeo(j, d, R))
                    gotO = True
            if gotP and gotO and gotN:
                break
    return prim, ordz, noctx


# --------------------------------------------------- generic controls C
def bucket_of(j):
    b = B[j]
    a = b['atr']
    r = b['relVolume'] or 0
    t = int((b['minutesFromRthOpen'] or 0) // 90)
    return (min(int(a / 2.0), 8), min(int(r), 4), min(t, 4))


POOLC = defaultdict(list)
for j in _eb:
    POOLC[bucket_of(j)].append(j)


def matched(entries):
    out = []
    for g in entries:
        cand = POOLC.get(bucket_of(g['j']))
        if not cand:
            continue
        k = random.choice(cand)
        out.append(mkgeo(k, g['d'], B[k]['atr']))
    return out


# ------------------------------------------------------------ summaries
def ffrate(gs, x=1.0):
    fav = sum(1 for g in gs if g['atr'][x] == 1)
    adv = sum(1 for g in gs if g['atr'][x] == 2)
    amb = sum(1 for g in gs if g['atr'][x] == 3)
    n = len(gs)
    rate = 100.0 * fav / (fav + adv) if fav + adv else float('nan')
    return rate, 100.0 * amb / n if n else 0.0


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def summ(gs):
    if not gs:
        return None
    exc = [g['exc'] for g in gs]
    mfe = [g['mfe'] for g in gs]
    mae = [g['mae'] for g in gs]
    f05 = ffrate(gs, 0.5)
    f10 = ffrate(gs, 1.0)
    f20 = ffrate(gs, 2.0)
    return dict(n=len(gs), mexc=sum(exc) / len(exc), net=sum(exc) / len(exc) - COST,
                mednet=med(exc) - COST, medmfe=med(mfe), medmae=med(mae),
                ratio=med(mfe) / med(mae) if med(mae) else float('nan'),
                mmfe=sum(mfe) / len(mfe), mmae=sum(mae) / len(mae),
                f05=f05, f10=f10, f20=f20)


def line(tag, gs):
    s = summ(gs)
    if s is None:
        print('  %-34s n=0' % tag)
        return
    print('  %-34s n=%4d exc%+7.2f net%+7.2f medMFE %5.1f medMAE %5.1f ratio %5.3f'
          ' ff05 %4.1f ff1 %4.1f ff2 %4.1f'
          % (tag, s['n'], s['mexc'], s['net'], s['medmfe'], s['medmae'],
             s['ratio'], s['f05'][0], s['f10'][0], s['f20'][0]))


def rrace_line(gs):
    if not gs:
        return
    parts = []
    for p in R_PAIRS:
        fav = sum(1 for g in gs if g['r'][p] == 1)
        adv = sum(1 for g in gs if g['r'][p] == 2)
        amb = sum(1 for g in gs if g['r'][p] == 3)
        tot = fav + adv
        parts.append('+%.1fR/-%.1fR %4.1f%%(amb %.0f%%)'
                     % (p[0], p[1], 100.0 * fav / tot if tot else float('nan'),
                        100.0 * amb / len(gs)))
    print('    R-races: ' + '  '.join(parts))


def detail(name, gs):
    """splits, months, sides, weeks, concentration for a primary set."""
    for sp in ('DEV', 'IR'):
        line('%s %s' % (name, sp), [g for g in gs if g['sp'] == sp])
    line('%s LONG' % name, [g for g in gs if g['d'] > 0])
    line('%s SHORT' % name, [g for g in gs if g['d'] < 0])
    bym = defaultdict(list)
    for g in gs:
        bym[g['day'][:7]].append(g)
    row = []
    for m in sorted(bym):
        s = summ(bym[m])
        row.append('%s n=%d net%+0.1f ff1 %.0f' % (m[2:], s['n'], s['net'], s['f10'][0]))
    print('    months: ' + ' | '.join(row))
    byw = defaultdict(float)
    for g in gs:
        y, m, d = int(g['day'][:4]), int(g['day'][5:7]), int(g['day'][8:10])
        byw[datetime.date(y, m, d).isocalendar()[:2]] += g['exc'] - COST
    wk = sorted(byw.values(), reverse=True)
    tot = sum(wk)
    pos = sum(1 for v in wk if v > 0)
    print('    weeks: %d/%d positive; best week %+0.1f of total %+0.1f'
          % (pos, len(wk), wk[0] if wk else 0.0, tot))
    net = sorted((g['exc'] - COST for g in gs), reverse=True)
    for pct in (0.01, 0.05):
        k = max(1, int(len(net) * pct))
        print('    top %2.0f%% (%d tr): %+0.1f pt of total %+0.1f'
              % (pct * 100, k, sum(net[:k]), sum(net)))
    print('    trades/week %.1f  trades/month %.1f' % (len(gs) / 42.0, len(gs) / 10.0))


# ---------------------------------------------------------------- stats
def boot_ff_diff(gsA, gsB, x=1.0, nb=2000):
    """P(one-sided) that ff_x(A) <= ff_x(B), day-clustered."""
    days = sorted(set(g['day'] for g in gsA) | set(g['day'] for g in gsB))
    byA = defaultdict(list)
    byB = defaultdict(list)
    for g in gsA:
        byA[g['day']].append(g['atr'][x])
    for g in gsB:
        byB[g['day']].append(g['atr'][x])
    le = 0
    for _ in range(nb):
        pick = random.choices(days, k=len(days))
        fa = aa = fb = ab = 0
        for d in pick:
            for st in byA.get(d, ()):
                if st == 1:
                    fa += 1
                elif st == 2:
                    aa += 1
            for st in byB.get(d, ()):
                if st == 1:
                    fb += 1
                elif st == 2:
                    ab += 1
        ra = fa / float(fa + aa) if fa + aa else 0.5
        rb = fb / float(fb + ab) if fb + ab else 0.5
        if ra <= rb:
            le += 1
    return le / float(nb)


def signflip_ff(gs, x=1.0, nb=2000):
    flip_geo = {}
    for g in gs:
        flip_geo[id(g)] = geometry(B, g['j'], -g['d'], None, BASE)
    real, _ = ffrate(gs, x)
    days = sorted(set(g['day'] for g in gs))
    ge = 0
    for _ in range(nb):
        fl = {d: (1 if random.random() < 0.5 else -1) for d in days}
        fav = adv = 0
        for g in gs:
            st = (g if fl[g['day']] > 0 else flip_geo[id(g)])['atr'][x]
            if st == 1:
                fav += 1
            elif st == 2:
                adv += 1
        r = 100.0 * fav / (fav + adv) if fav + adv else 50.0
        if r >= real:
            ge += 1
    return ge / float(nb)


def dayboot_mean(gs, nb=2000):
    bd = defaultdict(list)
    for g in gs:
        bd[g['day']].append(g['exc'])
    pools = list(bd.values())
    ms = []
    for _ in range(nb):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        ms.append(sum(s) / len(s))
    ms.sort()
    return ms[int(nb * .025)], ms[int(nb * .975)], sum(1 for x in ms if x <= 0) / nb


# ============================================================== BASELINE
print('\n' + '=' * 112)
print('BASELINE A: OFH6 immediate entry (R = 1.0 ATR, labeled as such)')
print('=' * 112)
G6 = [geometry(B, j, d, B[j]['atr'], BASE) for j, d in SIGS if entry_ok(B, j)]
line('OFH6 immediate', G6)
rrace_line(G6)
S6 = summ(G6)
FF6 = S6['f10'][0]

print('\nCONTEXT DECAY - excess and ff1 entering in OFH6 direction Δ min late:')
for delta in (0, 15, 30, 45, 60):
    gs = []
    for j, d in SIGS:
        k = j + delta
        if k < N and B[k]['tmin'] - B[j]['tmin'] == delta and entry_ok(B, k):
            gs.append(geometry(B, k, d, B[k]['atr'], BASE))
    s = summ(gs)
    print('  +%2d min  n=%3d  exc %+6.2f  ff1 %4.1f' % (delta, s['n'], s['mexc'], s['f10'][0]))

# ============================================================== FAMILY
RESULTS = {}
P7 = {}
for L in LIFE_FAMILY:
    P7[L] = ofh7_sets(CTX, L)
prim7, ord7, noctx7, types7 = P7[LIFE_PRIMARY]
vns7 = vec_no_sweep(CTX, LIFE_PRIMARY)
pm7 = ofh7_sets(CTXP, LIFE_PRIMARY)[0]

print('\n' + '=' * 112)
print('OFH7  DELTA BIAS + LIQUIDITY SWEEP + VECTOR RECLAIM')
print('=' * 112)
line('OFH7 primary (L=30)', prim7)
rrace_line(prim7)
for L in (15, 60):
    line('  lifespan %d' % L, P7[L][0])
for t in ('SW3', 'SW15', 'PDL'):
    line('  location %s' % t, types7.get(t, []))
line('ctrl OFH6+sweep+ORDINARY reclaim', ord7)
line('ctrl sweep+vector, NO OFH6', noctx7)
line('ctrl OFH6+vector, NO sweep', vns7)
line('ctrl matched random', matched(prim7))
line('ctrl PM-context', pm7)
if prim7:
    detail('OFH7', prim7)
RESULTS['OFH7'] = prim7

prim8, prim8D = ofh8_from(SIGS, CTX, LIFE_PRIMARY, 'vector')
p8_15, _ = ofh8_from(SIGS, CTX, 15, 'vector')
p8_60, _ = ofh8_from(SIGS, CTX, 60, 'vector')
ord8, _ = ofh8_from(SIGS, CTX, LIFE_PRIMARY, 'candle')
noctx8 = ofh8_noctx()
pm8, _ = ofh8_from(PM_SIGS, CTXP, LIFE_PRIMARY, 'vector')

print('\n' + '=' * 112)
print('OFH8  DELTA BIAS + OPPOSING VECTOR FAILURE')
print('=' * 112)
line('OFH8 primary (L=30)', prim8)
rrace_line(prim8)
line('  lifespan 15', p8_15)
line('  lifespan 60', p8_60)
line('  variant D: reclaim is same-dir vec', prim8D)
line('ctrl ordinary opposing candle', ord8)
line('ctrl opposing vector, NO OFH6', noctx8)
line('ctrl matched random', matched(prim8))
line('ctrl PM-context', pm8)
if prim8:
    detail('OFH8', prim8)
RESULTS['OFH8'] = prim8

PARV = parents(True)
PARN = parents(False)
P9 = {L: ofh9_sets(CTX, L, PARV, mark_zone=(L == LIFE_PRIMARY)) for L in LIFE_FAMILY}
prim9, ord9, noctx9 = P9[LIFE_PRIMARY]


def vec_away_from_zone(ctx, life):
    out = []
    last = -10 ** 9
    for j in range(N):
        d = V1[j]
        if d == 0 or (j, d) in ZONE or not entry_ok(B, j):
            continue
        t = B[j]['tmin']
        if not ctx.ok_at(d, t, life) or t - last < 15:
            continue
        last = t
        out.append(mkgeo(j, d, B[j]['atr']))
    return out


away9 = vec_away_from_zone(CTX, LIFE_PRIMARY)
nonv9, _, _ = ofh9_sets(CTX, LIFE_PRIMARY, PARN)
pm9, _, _ = ofh9_sets(CTXP, LIFE_PRIMARY, PARV)

print('\n' + '=' * 112)
print('OFH9  DELTA BIAS + FRESH 15M VECTOR WICK DEFENSE   (%d vector parents, %d non-vector)'
      % (len(PARV), len(PARN)))
print('=' * 112)
line('OFH9 primary (L=30)', prim9)
rrace_line(prim9)
for L in (15, 60):
    line('  lifespan %d' % L, P9[L][0])
line('ctrl wick+vector, NO OFH6', noctx9)
line('ctrl OFH6+wick, ORDINARY 1m bar', ord9)
line('ctrl OFH6+vector AWAY from wick', away9)
line('ctrl NON-vector parent wick', nonv9)
line('ctrl matched random', matched(prim9))
line('ctrl PM-context', pm9)
if prim9:
    detail('OFH9', prim9)
RESULTS['OFH9'] = prim9


def ofh10_sets(ctx, life):
    prim, noctx = [], []
    for ep in EPIS:
        d = 1 if ep['side'] == 'L' else -1     # trap trades WITH context d
        je = ep['entry10']
        if je is None or not entry_ok(B, je):
            continue
        R = R_of(je, d, ep['ext10'])
        if R <= 0:
            continue
        if ctx.ok(d, ep['startT'], B[je]['tmin'], life):
            prim.append(mkgeo(je, d, R))
        if ctx is CTX and no_ctx(B[je]['tmin']):
            noctx.append(mkgeo(je, d, R))
    return prim, noctx


P10 = {L: ofh10_sets(CTX, L) for L in LIFE_FAMILY}
prim10, noctx10 = P10[LIFE_PRIMARY]
pm10, _ = ofh10_sets(CTXP, LIFE_PRIMARY)

print('\n' + '=' * 112)
print('OFH10 DELTA BIAS + VECTOR TRAP AT LIQUIDITY EXTREME   (TR-INSPIRED / RESEARCH TRANSLATION)')
print('=' * 112)
line('OFH10 primary (L=30)', prim10)
rrace_line(prim10)
for L in (15, 60):
    line('  lifespan %d' % L, P10[L][0])
line('ctrl trap, NO OFH6', noctx10)
line('ctrl matched random', matched(prim10))
line('ctrl PM-context', pm10)
if prim10:
    detail('OFH10', prim10)
RESULTS['OFH10'] = prim10

# ---------------------------------------------------------- family stats
print('\n' + '=' * 112)
print('FAMILY STATISTICS  (primary endpoint: ff1 improvement over OFH6 baseline %.1f%%)' % FF6)
print('=' * 112)
praw = {}
for nm, gs in RESULTS.items():
    if len(gs) < MIN_N:
        print('  %-6s n=%d < %d  -> INSUFFICIENT SAMPLE for the endpoint' % (nm, len(gs), MIN_N))
        continue
    p_imp = boot_ff_diff(gs, G6)
    p_flip = signflip_ff(gs)
    lo, hi, p_exc = dayboot_mean(gs)
    praw[nm] = p_imp
    s = summ(gs)
    print('  %-6s n=%4d  ff1 %4.1f (Δ %+4.1f pp, p_boot %.3f)  signflip-p %.3f  '
          'exc CI [%+0.2f,%+0.2f] p %.3f'
          % (nm, s['n'], s['f10'][0], s['f10'][0] - FF6, p_imp, p_flip, lo, hi, p_exc))
if praw:
    order = sorted(praw, key=lambda k: praw[k])
    print('  BH (M=4):')
    prev = 1.0
    bh = {}
    for i in range(len(order) - 1, -1, -1):
        nm = order[i]
        q = praw[nm] * 4.0 / (i + 1)
        prev = min(prev, q)
        bh[nm] = prev
    for nm in order:
        print('    %-6s p_raw %.3f  BH q %.3f' % (nm, praw[nm], bh[nm]))

# overlap between primaries
names = list(RESULTS)
print('\n  entry-bar overlap between primaries:')
for i in range(len(names)):
    for k in range(i + 1, len(names)):
        a = set((g['j'], g['d']) for g in RESULTS[names[i]])
        bset = set((g['j'], g['d']) for g in RESULTS[names[k]])
        print('    %s ∩ %s = %d' % (names[i], names[k], len(a & bset)))

# ------------------------------------------------- stop family (gated)
print('\n' + '=' * 112)
print('STOP FAMILY (declared gate: n>=%d, ff1>OFH6, ratio>OFH6, pooled exc>0)' % MIN_N)
print('=' * 112)


def stop_run(gs, mode):
    outs = defaultdict(list)
    for g in gs:
        j, d = g['j'], g['d']
        e = B[j]['close']
        S = g['R'] if mode == 'struct' else (float(mode) * B[j]['atr'])
        if S is None or S <= 0:
            continue
        spx = e - d * S
        res = None
        mae = 0.0
        for k in range(1, HORIZON + 1):
            c = B[j + k]
            adv = (e - c['low']) if d > 0 else (c['high'] - e)
            if adv > mae:
                mae = adv
            if (d > 0 and c['low'] <= spx) or (d < 0 and c['high'] >= spx):
                res = -S
                break
        if res is None:
            res = (B[j + HORIZON]['close'] - e) * d
        outs[g['sp']].append((res - COST, mae))
    return outs


for nm, gs in RESULTS.items():
    s = summ(gs)
    if s is None or s['n'] < MIN_N or not (s['f10'][0] > FF6 and s['ratio'] > S6['ratio']
                                           and s['mexc'] > 0):
        print('  %-6s gate NOT passed -> stop family skipped' % nm)
        continue
    print('  %-6s gate passed:' % nm)
    for mode in ('struct', '1.0', '1.5'):
        outs = stop_run(gs, mode)
        row = '    stop %-7s' % mode
        for sp in ('DEV', 'IR'):
            v = outs.get(sp, [])
            if not v:
                row += '  %s n=0' % sp
                continue
            nets = [x[0] for x in v]
            maes = sorted(x[1] for x in v)
            row += '  %s n=%3d net%+7.2f win%% %4.1f p95MAE %5.1f' % (
                sp, len(v), sum(nets) / len(nets),
                100.0 * sum(1 for x in nets if x > 0) / len(nets),
                maes[int(len(maes) * .95)] if maes else float('nan'))
        print(row)

# ---------------------------------------------------- diagnostics dump
DIAG = ['ofBarDelta', 'ofDeltaPct', 'dsum15', 'ofTotalVolume', 'ofBidVolume',
        'ofAskVolume', 'ofMinDelta', 'ofMaxDelta', 'absorptionStrengthRaw',
        'volumePerUpTick', 'volumePerDownTick', 'buyImbalanceCount_3x',
        'sellImbalanceCount_3x', 'stackedBuyLevels_3x', 'stackedSellLevels_3x',
        'relVolume', 'atr', 'distPocAtr', 'distVahAtr', 'distValAtr',
        'profilePoc', 'profileVah', 'profileVal']
for nm, gs in RESULTS.items():
    path = os.path.join(SCR, 'ofht_entries_%s.csv' % nm)
    with open(path, 'w', newline='') as fh:
        w = csv.writer(fh)
        w.writerow(['et', 'dir', 'R', 'excess60m', 'mfe', 'mae'] + DIAG)
        for g in gs:
            b = B[g['j']]
            w.writerow([b['et'], g['d'], '%.2f' % (g['R'] or 0), '%.3f' % g['exc'],
                        '%.2f' % g['mfe'], '%.2f' % g['mae']]
                       + [b.get(c) for c in DIAG])
print('\nentry diagnostics written to %s/ofht_entries_*.csv' % SCR)
print('(VWAP distance is NOT in the order-flow capture and is recorded as absent)')
