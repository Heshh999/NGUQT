#!/usr/bin/env python3
# ======================================================================
# OFH11-OFH14 - LIQUIDITY / FVG / IFVG / ORDER-FLOW TIMING FAMILY
# Declared 2026-08-21 BEFORE the first run. One pre-declared family of
# four. No fifth hypothesis will be created from these results.
#
# PROVENANCE. These are RESEARCH TRANSLATIONS inspired by publicly
# discussed PB Trading / ICT concepts (liquidity sweep, displacement,
# fair value gap, inverse fair value gap, mitigation). They are NOT
# claimed to be any official PB Trading or ICT strategy: no primary
# source was consulted for exact mechanical rules, so every threshold
# below is my own frozen mechanical choice, not a sourced definition.
#
# ROLE SPLIT UNDER TEST:
#   OFH6 (frozen, unmodified)  = DIRECTION
#   liquidity / FVG / IFVG     = LOCATION
#   price delivery / order flow = ENTRY TIMING
#
# FROZEN OFH6: imported from ofh6_spec.py. 15-bar cumulative delta,
# threshold 3380, direction rule, cooldown, causal construction - all
# untouched. Context life PRIMARY = 30 minutes, not re-optimised: no
# entry may occur more than 30 minutes after its activating signal, and
# an opposite-direction signal in between kills the context.
#
# ---------------------------------------------------------------------
# FROZEN MECHANICAL DEFINITIONS (fixed before any result was seen)
# ---------------------------------------------------------------------
# FVG (causal, 3 completed 1m candles c1,c2,c3 ending at bar j):
#   bullish  c1.high < c3.low  -> zone [c1.high, c3.low]
#   bearish  c1.low  > c3.high -> zone [c3.high, c1.low]
#   CE / midpoint = (zLo+zHi)/2. Frozen at the close of c3.
#
# DISPLACEMENT (one definition, four conditions, on c2, using ATR(c2)):
#   range >= 1.00 * ATR ; body/range >= 0.50 ;
#   close-location >= 0.70 (bullish) or <= 0.30 (bearish) ;
#   leg direction agrees: c3.close > c1.open (bullish) / < (bearish).
#
# INVERSION (IFVG): a completed 1m candle CLOSES beyond the OPPOSITE
#   boundary of the FVG (bearish FVG -> close > zHi gives a bullish
#   IFVG; mirror for bearish). The IFVG zone is the same price band.
#
# MITIGATION + TRIGGER (identical for every hypothesis):
#   first touch of the zone, then the FIRST completed 1m candle closing
#   back beyond the zone midpoint in the trade direction. The touching
#   candle itself qualifies if it also closes beyond the midpoint.
#   Entry at that completed close.
#
# OPPOSING-FLOW FAILURE (OFH13 only, two conditions):
#   (a) elevated opposing aggression: at least one mitigation bar whose
#       barDelta opposes the trade with |barDelta| >= DEV p75 of
#       |barDelta|;  AND
#   (b) poor result: the FVG is not fully filled at trigger
#       (penetration depth < 1.0 of the zone).
#
# FIRST-TOUCH / FIRST-FVG RULE (non-negotiable): per parent event the
#   FIRST eligible FVG, FIRST mitigation and FIRST trigger are used.
#   Later FVGs are counted but never used for primary results.
#
# INVALIDATION while waiting (thesis-based, not P&L-based):
#   OFH11/OFH12 - the sweep extreme must hold until entry.
#   OFH13/OFH14 - a completed close beyond the far FVG boundary kills it.
#   All hypotheses - OFH6 context expiry at 30 minutes.
#
# MEASUREMENT: 60-minute horizon; excess over the side- AND
#   split-matched mean of all entry-eligible bars; cost 0.87 pt RT;
#   RTH, >=30 min after open, >=60 min to close; 30-min per-hypothesis
#   cooldown applied CHRONOLOGICALLY after all scanners finish (the
#   defect found in ofn_run.py is not repeated).
#   R = distance from entry to the stated structural invalidation +1 tick.
#   Exact first-touch races at +-0.25/0.5/1.0 ATR and +1.5/-1.0,
#   +2.0/-1.0 ATR, plus the same ladder in R. Ties inside one 1m bar are
#   AMBIGUOUS and counted, never resolved by assumption.
#   DEV = 2025-11..2026-03. INTERNAL REPLICATION = 2026-04..08.
#   Neither is true OOS. M=4 family: sign-flip-by-day p, BH q, max-stat.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, random, datetime
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ofh6_spec as F6
from ofht_cache import load as load_bars3
from ofht_spec import (TICK, DEV_END, attach_dsum15, aggregate, swings,
                       prevday_levels, Context, entry_ok)

random.seed(41)
SCR = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
COST = 0.87
HORIZON = 60
LIFE = 30
COOL = 30
DISP_ATR = 1.00
DISP_BODY = 0.50
DISP_CLR = 0.70
SWEEP_LOOKBACK_FVG = 20          # OFH12: bearish FVG within 20 bars of the sweep
ATR_PAIRS = ((0.25, 0.25), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0))
R_PAIRS = ((0.5, 1.0), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (3.0, 1.0))

B = load_bars3()
attach_dsum15(B)
N = len(B)
ELIG6 = F6.eligible(B)
SIGS = F6.signals(B, ELIG6)
assert len(SIGS) == 783, 'frozen OFH6 stream changed: %d' % len(SIGS)
CTX = Context(SIGS, B)

EB = [j for j in range(N) if entry_ok(B, j)]
BASE = {}
for sp in ('DEV', 'IR'):
    for d in (1, -1):
        v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in EB
             if ('DEV' if B[j]['day'] <= DEV_END else 'IR') == sp]
        BASE[(sp, d)] = sum(v) / len(v)

DEVB = [j for j in EB if B[j]['day'] <= DEV_END]
_bd = sorted(abs(B[j]['ofBarDelta']) for j in DEVB if B[j]['ofBarDelta'] is not None)
Q_BD75 = _bd[int(len(_bd) * 0.75)]

AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
PDL = prevday_levels(B)
print('bars %d  OFH6 signals %d  DEV p75|barDelta| = %.0f' % (N, len(SIGS), Q_BD75))
print('baseline 60m DEV L/S %+.3f/%+.3f   IR L/S %+.3f/%+.3f'
      % (BASE[('DEV', 1)], BASE[('DEV', -1)], BASE[('IR', 1)], BASE[('IR', -1)]))


def consec(j, k):
    return B[j]['tmin'] - B[k]['tmin'] == j - k


# ------------------------------------------------------------- FVG list
FVG = []
FVG_AT = defaultdict(list)
for j in range(2, N):
    if not consec(j, j - 2):
        continue
    a, c2, c3 = B[j - 2], B[j - 1], B[j]
    atr = c2['atr']
    if not atr or atr <= 0:
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
    disp = (rng >= DISP_ATR * atr and body / rng >= DISP_BODY
            and ((d > 0 and clr >= DISP_CLR and c3['close'] > a['open'])
                 or (d < 0 and clr <= 1.0 - DISP_CLR and c3['close'] < a['open'])))
    f = {'j': j, 'd': d, 'zLo': zLo, 'zHi': zHi, 'mid': (zLo + zHi) / 2.0,
         'size': zHi - zLo, 'sizeAtr': (zHi - zLo) / atr, 'disp': disp,
         'dispRangeAtr': rng / atr, 'bodyFrac': body / rng,
         'vol': c2['ofTotalVolume'], 'delta': c2['ofBarDelta'], 'atr': atr}
    FVG.append(f)
    FVG_AT[j].append(f)
nb = sum(1 for f in FVG if f['d'] > 0)
print('FVGs: %d (%d bullish / %d bearish); displacement-qualified %d'
      % (len(FVG), nb, len(FVG) - nb, sum(1 for f in FVG if f['disp'])))

# displacement bars that produced NO FVG (control for OFH11)
DISP_NOFVG = []
for j in range(2, N):
    if not consec(j, j - 2) or FVG_AT.get(j):
        continue
    c2 = B[j - 1]
    a, c3 = B[j - 2], B[j]
    atr = c2['atr']
    rng = c2['high'] - c2['low']
    if not atr or atr <= 0 or rng <= 0:
        continue
    body = abs(c2['close'] - c2['open'])
    clr = (c2['close'] - c2['low']) / rng
    for d in (1, -1):
        ok = (rng >= DISP_ATR * atr and body / rng >= DISP_BODY
              and ((d > 0 and clr >= DISP_CLR and c3['close'] > a['open'])
                   or (d < 0 and clr <= 1.0 - DISP_CLR and c3['close'] < a['open'])))
        if ok:
            DISP_NOFVG.append({'j': j, 'd': d, 'ext': c2['low'] if d > 0 else c2['high']})


def mitigate(f, start_j, expire_tmin, hard_invalid=None, want_flow=False):
    """First touch of the zone then first completed close beyond the CE.
    Returns dict or None. hard_invalid: price that must not be traded."""
    d, zLo, zHi, mid = f['d'], f['zLo'], f['zHi'], f['mid']
    touched = False
    ext = None
    flow_ok = False
    prev = None
    for k in range(start_j, N):
        if prev is not None and B[k]['tmin'] != prev + 1:
            return None
        prev = B[k]['tmin']
        if B[k]['tmin'] > expire_tmin:
            return None
        c = B[k]
        if hard_invalid is not None:
            if (d > 0 and c['low'] <= hard_invalid) or (d < 0 and c['high'] >= hard_invalid):
                return None
        if (d > 0 and c['close'] < zLo) or (d < 0 and c['close'] > zHi):
            return None                                   # zone violated
        if not touched:
            if (d > 0 and c['low'] <= zHi) or (d < 0 and c['high'] >= zLo):
                touched = True
                ext = c['low'] if d > 0 else c['high']
        else:
            e = c['low'] if d > 0 else c['high']
            if (d > 0 and e < ext) or (d < 0 and e > ext):
                ext = e
        if not touched:
            continue
        bd = c['ofBarDelta']
        if bd is not None and abs(bd) >= Q_BD75 and bd * d < 0:
            flow_ok = True
        if (d > 0 and c['close'] > mid) or (d < 0 and c['close'] < mid):
            span = zHi - zLo
            depth = ((zHi - ext) / span) if d > 0 else ((ext - zLo) / span)
            if want_flow and not (flow_ok and depth < 1.0):
                return None
            return {'j': k, 'depth': depth, 'ext': ext, 'flow': flow_ok}
    return None


# ------------------------------------------------------- sweep episodes
LOWEV = sorted([(t, v, 'SW3') for t, v in SW3L] + [(t, v, 'SW15') for t, v in SW15L])
HIGHEV = sorted([(t, v, 'SW3') for t, v in SW3H] + [(t, v, 'SW15') for t, v in SW15H])
slots = {(s, t): None for s in 'LH' for t in ('SW3', 'SW15', 'PDL')}
SWEEPS = []
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
    for side, s in (('L', 1), ('H', -1)):
        hit = []
        for typ in ('SW3', 'SW15', 'PDL'):
            lv = slots[(side, typ)]
            if lv is None:
                continue
            if (s > 0 and b['low'] < lv) or (s < 0 and b['high'] > lv):
                hit.append((typ, lv))
                slots[(side, typ)] = None
        if not hit:
            continue
        lvl = max(h[1] for h in hit) if s > 0 else min(h[1] for h in hit)
        if not b['atr'] or b['atr'] <= 0:
            continue
        SWEEPS.append({'j': j, 'd': s, 'lvl': lvl, 'types': [h[0] for h in hit],
                       'atr': b['atr']})
print('sweep episodes: %d low / %d high'
      % (sum(1 for e in SWEEPS if e['d'] > 0), sum(1 for e in SWEEPS if e['d'] < 0)))

RAW = defaultdict(list)


def add(name, j, d, stop_ref, meta=None):
    if not entry_ok(B, j):
        return
    e = B[j]['close']
    R = (e - (stop_ref - TICK)) if d > 0 else ((stop_ref + TICK) - e)
    if R <= 0:
        return
    RAW[name].append((j, d, R, meta or {}))


# ============================== OFH11 + controls =======================
# state machine per sweep: reclaim -> first displacement FVG -> mitigation
for ep in SWEEPS:
    d, j0, lvl = ep['d'], ep['j'], ep['lvl']
    ts = CTX.activating(d, B[j0]['tmin'])
    has_ctx = (ts is not None and B[j0]['tmin'] - ts <= LIFE
               and not CTX.opposite_in(d, ts, B[j0]['tmin']))
    expire = (ts + LIFE) if ts is not None else -1
    swext = B[j0]['low'] if d > 0 else B[j0]['high']
    reclaimed = (B[j0]['close'] > lvl) if d > 0 else (B[j0]['close'] < lvl)
    rec_j = j0 if reclaimed else None
    prev = B[j0]['tmin']
    for k in range(j0 + 1, N):
        if B[k]['tmin'] != prev + 1:
            break
        prev = B[k]['tmin']
        if B[k]['tmin'] > B[j0]['tmin'] + 45:
            break
        c = B[k]
        e = c['low'] if d > 0 else c['high']
        if (d > 0 and e < swext) or (d < 0 and e > swext):
            break                                   # sweep extreme broken
        if rec_j is None:
            if (d > 0 and c['close'] > lvl) or (d < 0 and c['close'] < lvl):
                rec_j = k
            continue
        for f in FVG_AT.get(k, ()):
            if f['d'] != d or not f['disp']:
                continue
            exp2 = expire if has_ctx else B[j0]['tmin'] + 45
            m = mitigate(f, k + 1, exp2, hard_invalid=swext)
            if m is None:
                break
            meta = {'depth': m['depth'], 'sizeAtr': f['sizeAtr'],
                    'lvl': ep['types'][0], 'sweepext': swext,
                    'fvgfar': f['zLo'] if d > 0 else f['zHi'],
                    'atr': ep['atr']}
            te = B[m['j']]['tmin']
            if has_ctx and te - ts <= LIFE and not CTX.opposite_in(d, ts, te):
                add('OFH11', m['j'], d, swext, meta)
            else:
                add('C11_noOFH6', m['j'], d, swext, meta)
            break
        else:
            continue
        break
    # control: sweep + immediate ordinary reclaim (no FVG wait)
    if rec_j is not None and has_ctx:
        te = B[rec_j]['tmin']
        if te - ts <= LIFE and not CTX.opposite_in(d, ts, te):
            add('C11_reclaim', rec_j, d, swext, {'atr': ep['atr']})

# control: OFH6 + sweep + displacement but NO FVG
for ep in SWEEPS:
    d, j0 = ep['d'], ep['j']
    ts = CTX.activating(d, B[j0]['tmin'])
    if ts is None or B[j0]['tmin'] - ts > LIFE or CTX.opposite_in(d, ts, B[j0]['tmin']):
        continue
    swext = B[j0]['low'] if d > 0 else B[j0]['high']
    for dn in DISP_NOFVG:
        if dn['j'] <= j0 or dn['d'] != d:
            continue
        if B[dn['j']]['tmin'] - B[j0]['tmin'] > 45:
            break
        te = B[dn['j']]['tmin']
        if te - ts <= LIFE and not CTX.opposite_in(d, ts, te):
            add('C11_dispNoFVG', dn['j'], d, swext, {'atr': ep['atr']})
        break

# ============================== OFH12 + controls =======================
for ep in SWEEPS:
    d, j0 = ep['d'], ep['j']              # d>0: low swept -> look for bullish IFVG
    ts = CTX.activating(d, B[j0]['tmin'])
    has_ctx = (ts is not None and B[j0]['tmin'] - ts <= LIFE
               and not CTX.opposite_in(d, ts, B[j0]['tmin']))
    swext = B[j0]['low'] if d > 0 else B[j0]['high']
    src = None
    for k in range(max(0, j0 - SWEEP_LOOKBACK_FVG), j0 + 1):
        for f in FVG_AT.get(k, ()):
            if f['d'] == -d:
                src = f
    if src is None:
        continue
    zLo, zHi = src['zLo'], src['zHi']
    inv_j = None
    prev = B[j0]['tmin']
    for k in range(j0 + 1, N):
        if B[k]['tmin'] != prev + 1:
            break
        prev = B[k]['tmin']
        if B[k]['tmin'] > B[j0]['tmin'] + 45:
            break
        c = B[k]
        e = c['low'] if d > 0 else c['high']
        if (d > 0 and e < swext) or (d < 0 and e > swext):
            break
        if (d > 0 and c['close'] > zHi) or (d < 0 and c['close'] < zLo):
            inv_j = k
            break
    if inv_j is None:
        continue
    ifvg = {'d': d, 'zLo': zLo, 'zHi': zHi, 'mid': (zLo + zHi) / 2.0,
            'sizeAtr': src['sizeAtr']}
    exp2 = (ts + LIFE) if has_ctx else B[j0]['tmin'] + 45
    m = mitigate(ifvg, inv_j + 1, exp2, hard_invalid=swext)
    if m is None:
        continue
    meta = {'depth': m['depth'], 'sizeAtr': src['sizeAtr'], 'lvl': ep['types'][0],
            'sweepext': swext, 'fvgfar': zLo if d > 0 else zHi, 'atr': ep['atr']}
    te = B[m['j']]['tmin']
    if has_ctx and te - ts <= LIFE and not CTX.opposite_in(d, ts, te):
        add('OFH12', m['j'], d, swext, meta)
    else:
        add('C12_noOFH6', m['j'], d, swext, meta)

# control: OFH6 + IFVG WITHOUT a liquidity sweep
INVSEEN = set()
for f in FVG:
    d = -f['d']
    zLo, zHi = f['zLo'], f['zHi']
    inv_j = None
    prev = B[f['j']]['tmin']
    for k in range(f['j'] + 1, min(f['j'] + 31, N)):
        if B[k]['tmin'] != prev + 1:
            break
        prev = B[k]['tmin']
        c = B[k]
        if (d > 0 and c['close'] > zHi) or (d < 0 and c['close'] < zLo):
            inv_j = k
            break
    if inv_j is None:
        continue
    near_sweep = any(abs(B[s['j']]['tmin'] - B[inv_j]['tmin']) <= 20 and s['d'] == d
                     for s in SWEEPS if abs(s['j'] - inv_j) <= 40)
    if near_sweep:
        continue
    ts = CTX.activating(d, B[inv_j]['tmin'])
    if ts is None or B[inv_j]['tmin'] - ts > LIFE or CTX.opposite_in(d, ts, B[inv_j]['tmin']):
        continue
    ifvg = {'d': d, 'zLo': zLo, 'zHi': zHi, 'mid': (zLo + zHi) / 2.0}
    m = mitigate(ifvg, inv_j + 1, ts + LIFE)
    if m is None:
        continue
    te = B[m['j']]['tmin']
    if te - ts <= LIFE and not CTX.opposite_in(d, ts, te):
        add('C12_noSweep', m['j'], d, zLo if d > 0 else zHi,
            {'depth': m['depth'], 'atr': f['atr']})

# ======================= OFH13 / OFH14 + ablation ======================
# OFH14 = OFH6 + first displacement FVG after the signal + first
# mitigation.  OFH13 = the SAME event stream with the opposing-flow
# failure condition added, so the four-cell ablation is exact.
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
            if f['d'] == d and f['disp']:
                got = f
                break
        if got is None:
            continue
        far = got['zLo'] if d > 0 else got['zHi']
        m = mitigate(got, k + 1, ts + LIFE)
        if m is not None:
            te = B[m['j']]['tmin']
            if not CTX.opposite_in(d, ts, te):
                meta = {'depth': m['depth'], 'sizeAtr': got['sizeAtr'],
                        'fvgfar': far, 'atr': got['atr'], 'flow': m['flow'],
                        'fvgj': got['j'], 'zLo': got['zLo'], 'zHi': got['zHi'],
                        'mid': got['mid']}
                add('OFH14', m['j'], d, far, meta)
                if m['flow'] and m['depth'] < 1.0:
                    add('OFH13', m['j'], d, far, meta)
        break                                  # FIRST FVG only

# ablation cells without OFH6: every displacement FVG, first mitigation
for f in FVG:
    if not f['disp']:
        continue
    d = f['d']
    far = f['zLo'] if d > 0 else f['zHi']
    m = mitigate(f, f['j'] + 1, B[f['j']]['tmin'] + LIFE)
    if m is None:
        continue
    meta = {'depth': m['depth'], 'sizeAtr': f['sizeAtr'], 'atr': f['atr']}
    add('A_FVGonly', m['j'], d, far, meta)
    if m['flow'] and m['depth'] < 1.0:
        add('A_FVGflow', m['j'], d, far, meta)

# ------------------------------------------------- chronological cooldown
ENT = defaultdict(list)
for name, lst in RAW.items():
    lst.sort(key=lambda x: B[x[0]]['tmin'])
    last = -10 ** 9
    for j, d, R, meta in lst:
        if B[j]['tmin'] - last < COOL:
            continue
        last = B[j]['tmin']
        ENT[name].append((j, d, R, meta))


# ------------------------------------------------------------- geometry
def geo(j, d, R, meta=None):
    e = B[j]['close']
    atr = B[j]['atr']
    sp = 'DEV' if B[j]['day'] <= DEV_END else 'IR'
    mfe = mae = 0.0
    ast = {p: 0 for p in ATR_PAIRS}
    rst = {p: 0 for p in R_PAIRS}
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        fav = (c['high'] - e) if d > 0 else (e - c['low'])
        adv = (e - c['low']) if d > 0 else (c['high'] - e)
        if fav > mfe:
            mfe = fav
        if adv > mae:
            mae = adv
        for p in ATR_PAIRS:
            if ast[p]:
                continue
            hf, ha = fav >= p[0] * atr, adv >= p[1] * atr
            ast[p] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
        if R and R > 0:
            for p in R_PAIRS:
                if rst[p]:
                    continue
                hf, ha = fav >= p[0] * R, adv >= p[1] * R
                rst[p] = 3 if (hf and ha) else (1 if hf else (2 if ha else 0))
    raw = (B[j + HORIZON]['close'] - e) * d
    return {'j': j, 'd': d, 'R': R, 'day': B[j]['day'], 'sp': sp, 'atr': atr,
            'exc': raw - BASE[(sp, d)], 'mfe': mfe, 'mae': mae,
            'a': ast, 'r': rst, 'meta': meta or {}}


G = {}
GF = {}
for name in ENT:
    G[name] = [geo(j, d, R, m) for j, d, R, m in ENT[name]]
    GF[name] = [geo(j, -d, None, m) for j, d, R, m in ENT[name]]
G6 = [geo(j, d, B[j]['atr']) for j, d in SIGS if entry_ok(B, j)]


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def ffr(gs, p):
    f = sum(1 for g in gs if g['a'][p] == 1)
    a = sum(1 for g in gs if g['a'][p] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


def amb(gs, p):
    return 100.0 * sum(1 for g in gs if g['a'][p] == 3) / len(gs) if gs else 0.0


def rfr(gs, p):
    f = sum(1 for g in gs if g['r'][p] == 1)
    a = sum(1 for g in gs if g['r'][p] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


def line(tag, gs):
    if not gs:
        print('  %-28s n=0' % tag)
        return
    ex = [g['exc'] for g in gs]
    mf, ma = med([g['mfe'] for g in gs]), med([g['mae'] for g in gs])
    print('  %-28s n=%4d exc%+7.2f net%+7.2f medMFE%6.1f medMAE%6.1f ratio%6.3f '
          'ff.25 %4.1f ff.5 %4.1f ff1 %4.1f ff1.5 %4.1f ff2 %4.1f'
          % (tag, len(gs), sum(ex) / len(ex), sum(ex) / len(ex) - COST, mf, ma,
             mf / ma if ma else float('nan'),
             ffr(gs, (0.25, 0.25)), ffr(gs, (0.5, 0.5)), ffr(gs, (1.0, 1.0)),
             ffr(gs, (1.5, 1.0)), ffr(gs, (2.0, 1.0))))


print('\n' + '=' * 126)
print('BASELINE: frozen OFH6 immediate entry (R = 1 ATR)')
print('=' * 126)
line('OFH6 immediate', G6)
FF6 = ffr(G6, (1.0, 1.0))
RATIO6 = med([g['mfe'] for g in G6]) / med([g['mae'] for g in G6])
print('  advantage MFE-MAE: mean %+0.2f  median %+0.2f pt'
      % (sum(g['mfe'] - g['mae'] for g in G6) / len(G6),
         med([g['mfe'] - g['mae'] for g in G6])))

PRIM = ['OFH11', 'OFH12', 'OFH13', 'OFH14']
CTRLS = {'OFH11': ['C11_reclaim', 'C11_dispNoFVG', 'C11_noOFH6', 'OFH14'],
         'OFH12': ['C12_noOFH6', 'C12_noSweep'],
         'OFH13': ['A_FVGonly', 'OFH14', 'A_FVGflow'],
         'OFH14': ['A_FVGonly']}
LABEL = {'C11_reclaim': 'OFH6+sweep+ordinary reclaim',
         'C11_dispNoFVG': 'OFH6+sweep+disp, NO FVG',
         'C11_noOFH6': 'sweep+FVG, NO OFH6',
         'OFH14': 'OFH6+FVG, NO sweep (=OFH14)',
         'C12_noOFH6': 'sweep+IFVG, NO OFH6',
         'C12_noSweep': 'OFH6+IFVG, NO sweep',
         'A_FVGonly': 'FVG only (no OFH6, no flow)',
         'A_FVGflow': 'FVG + flow-failure, no OFH6'}

for nm in PRIM:
    gs = G.get(nm, [])
    print('\n' + '=' * 126)
    print('%s  %s' % (nm, {'OFH11': 'sweep + displacement FVG + first mitigation',
                           'OFH12': 'sweep + inverse FVG + first retest',
                           'OFH13': 'FVG mitigation + opposing order-flow failure',
                           'OFH14': 'displacement + first FVG pullback (no sweep)'}[nm]))
    print('=' * 126)
    line(nm, gs)
    if gs:
        print('    R-races: ' + '  '.join('+%.1fR/-%.1fR %4.1f%%(amb%2.0f%%)'
                                          % (p[0], p[1], rfr(gs, p),
                                             100.0 * sum(1 for g in gs if g['r'][p] == 3) / len(gs))
                                          for p in R_PAIRS))
        print('    ATR-race ambiguity: ' + ' '.join('%.2f:%.0f%%' % (p[0], amb(gs, p))
                                                    for p in ATR_PAIRS))
        print('    advantage MFE-MAE: mean %+0.2f  median %+0.2f pt'
              % (sum(g['mfe'] - g['mae'] for g in gs) / len(gs),
                 med([g['mfe'] - g['mae'] for g in gs])))
        rr = [g['R'] for g in gs]
        print('    risk to structural invalidation: med %.2f pt (%.2f ATR)  1ATR=%.1f 1.5ATR=%.1f'
              % (med(rr), med([g['R'] / g['atr'] for g in gs]),
                 med([g['atr'] for g in gs]), med([1.5 * g['atr'] for g in gs])))
        ff = [g['meta'].get('fvgfar') for g in gs if g['meta'].get('fvgfar') is not None]
        if ff:
            dd = [abs(B[g['j']]['close'] - g['meta']['fvgfar'])
                  for g in gs if g['meta'].get('fvgfar') is not None]
            print('    distance to FVG far boundary: med %.2f pt' % med(dd))
        dep = [g['meta']['depth'] for g in gs if 'depth' in g['meta']]
        if dep:
            bk = [('edge <25%', 0, .25), ('25-50%', .25, .5), ('50-75%', .5, .75),
                  ('75-100%', .75, 1.0), ('full fill >=100%', 1.0, 9e9)]
            print('    FVG penetration depth at trigger:')
            for lb, lo, hiq in bk:
                sub = [g for g in gs if 'depth' in g['meta'] and lo <= g['meta']['depth'] < hiq]
                if sub:
                    print('      %-18s n=%3d  exc %+7.2f  ff1 %4.1f'
                          % (lb, len(sub), sum(x['exc'] for x in sub) / len(sub),
                             ffr(sub, (1.0, 1.0))))
        for sp in ('DEV', 'IR'):
            line('   %s' % sp, [g for g in gs if g['sp'] == sp])
        line('   LONG', [g for g in gs if g['d'] > 0])
        line('   SHORT', [g for g in gs if g['d'] < 0])
        bym = defaultdict(list)
        for g in gs:
            bym[g['day'][:7]].append(g['exc'] - COST)
        print('    months: ' + ' '.join('%s%+0.1f(%d)' % (m[2:], sum(v) / len(v), len(v))
                                        for m, v in sorted(bym.items())))
        byw = defaultdict(float)
        for g in gs:
            y, mo, dy = int(g['day'][:4]), int(g['day'][5:7]), int(g['day'][8:10])
            byw[datetime.date(y, mo, dy).isocalendar()[:2]] += g['exc'] - COST
        wk = sorted(byw.values(), reverse=True)
        net = sorted((g['exc'] - COST for g in gs), reverse=True)
        print('    weeks %d/%d positive; months %d/%d positive; trades/wk %.2f  trades/mo %.1f'
              % (sum(1 for v in wk if v > 0), len(wk),
                 sum(1 for v in bym.values() if sum(v) / len(v) > 0), len(bym),
                 len(gs) / 42.0, len(gs) / 10.0))
        print('    median trade %+0.2f  top1%% %+0.1f  top5%% %+0.1f  of total %+0.1f'
              % (med(net), sum(net[:max(1, len(net) // 100)]),
                 sum(net[:max(1, len(net) // 20)]), sum(net)))
    for c in CTRLS[nm]:
        if c == nm:
            continue
        line('  ctrl ' + LABEL.get(c, c), G.get(c, []))

print('\n' + '=' * 126)
print('OFH13 FOUR-CELL ABLATION - does order flow add TIMING beyond correct delta bias?')
print('=' * 126)
for cell, nm in (('FVG only', 'A_FVGonly'), ('OFH6 + FVG', 'OFH14'),
                 ('FVG + flow-failure', 'A_FVGflow'),
                 ('OFH6 + FVG + flow-failure', 'OFH13')):
    line(cell, G.get(nm, []))

# ------------------------------------------------------------ statistics
print('\n' + '=' * 126)
print('FAMILY STATISTICS (M=4 declared; sign-flip by day; excess endpoint)')
print('=' * 126)
NS = 4000
praw = {}
ffp = {}
for nm in PRIM:
    gs, gf = G.get(nm, []), GF.get(nm, [])
    if len(gs) < 10:
        continue
    real = sum(g['exc'] for g in gs) / len(gs)
    realff = ffr(gs, (1.0, 1.0))
    days = sorted(set(g['day'] for g in gs))
    ge = gf_ = 0
    for _ in range(NS):
        fl = {d: (1 if random.random() < 0.5 else -1) for d in days}
        acc = 0.0
        f1 = a1 = 0
        for g, h in zip(gs, gf):
            u = g if fl[g['day']] > 0 else h
            acc += u['exc']
            st = u['a'][(1.0, 1.0)]
            if st == 1:
                f1 += 1
            elif st == 2:
                a1 += 1
        if acc / len(gs) >= real:
            ge += 1
        if f1 + a1 and 100.0 * f1 / (f1 + a1) >= realff:
            gf_ += 1
    praw[nm] = ge / float(NS)
    ffp[nm] = gf_ / float(NS)
    bd = defaultdict(list)
    for g in gs:
        bd[g['day']].append(g['exc'])
    pools = list(bd.values())
    bs = []
    for _ in range(2000):
        s = [x for dd in random.choices(pools, k=len(pools)) for x in dd]
        bs.append(sum(s) / len(s))
    bs.sort()
    print('  %-6s n=%4d  exc %+7.2f  CI [%+7.2f,%+7.2f]  p_exc %.4f | ff1 %4.1f (OFH6 %4.1f) '
          'p_ff %.4f | ratio %5.3f (OFH6 %5.3f)'
          % (nm, len(gs), real, bs[50], bs[1949], praw[nm], realff, FF6, ffp[nm],
             med([g['mfe'] for g in gs]) / med([g['mae'] for g in gs]), RATIO6))
if praw:
    order = sorted(praw, key=lambda k: praw[k])
    prev = 1.0
    bh = {}
    for i in range(len(order) - 1, -1, -1):
        nm = order[i]
        qv = praw[nm] * 4.0 / (i + 1)
        prev = min(prev, qv)
        bh[nm] = prev
    print('  BH q (M=4): ' + '  '.join('%s %.3f' % (nm, bh[nm]) for nm in order))
    alld = sorted(set(g['day'] for nm in praw for g in G[nm]))
    fam = []
    for _ in range(2000):
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
          % (rb, best, fam[1000], fam[1899],
             sum(1 for x in fam if x >= rb) / 2000.0))

# --------------------------------------------- 30s execution (secondary)
S30 = defaultdict(dict)
for f in sorted(glob.glob(SCR + '/ph2/V3_30s_*.csv')):
    mo = f[-10:-4]
    mm = mo[:4] + '-' + mo[4:]
    if mm < '2025-11' or mm > '2026-05':
        continue
    for r in csv.DictReader(open(f)):
        if r['timeframe'] != '30s':
            continue
        h, mi, se = map(int, r['timeEt'].split(':'))
        S30[r['date']][h * 3600 + mi * 60 + se] = (
            float(r['open']), float(r['high']), float(r['low']), float(r['close']))
print('\n' + '=' * 126)
print('SECONDARY: 30s EXECUTION on the SAME frozen parents (30s may not requalify a setup)')
print('=' * 126)
for nm in PRIM:
    gs = G.get(nm, [])
    pairs = []
    for g in gs:
        j = g['j']
        day = B[j]['day']
        if day not in S30:
            continue
        et = B[j]['et']
        sod = int(et[11:13]) * 3600 + int(et[14:16]) * 60
        if sod - 60 < 9 * 3600 + 30 * 60 or sod > 11 * 3600:
            continue
        mid = g['meta'].get('mid')
        pairs.append(g)
    print('  %-6s entries inside 30s coverage window: %d (of %d)' % (nm, len(pairs), len(gs)))
print('  Coverage is 09:30-11:00 ET on 147 days; these families concentrate outside it.')
print('  Where n is this small no execution comparison is meaningful -> INSUFFICIENT DATA.')
