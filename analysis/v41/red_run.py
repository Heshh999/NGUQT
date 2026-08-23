#!/usr/bin/env python3
# ======================================================================
# RED-H1 / RED-H2 / RED-H6 / RED-H10  -  event generation + controls
# ======================================================================
# Rules exactly as pre-registered in docs/RED_PREREGISTRATION.md.
# Thresholds were frozen on DEV before any outcome was computed.
# Every feature is causal; no future bar creates an earlier signal.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, pickle, math
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import red_lib as R

ATTACK_WIN = 10      # bars between the failed attack and the reclaim.
                     # Fixed a priori (~1/3 of the 30-min signal life used
                     # throughout this project). NOT searched.
COOLDOWN = 30        # minutes, per hypothesis+variant, applied chronologically
NEAR_EDGE = 0.25     # ATR, "at" a level
NEAR_LOC = 0.5       # ATR, FVG-to-location proximity


def load():
    B = pickle.load(open(R.SCR + '/red_bars.pkl', 'rb'))
    FR = pickle.load(open(R.SCR + '/red_frozen.pkl', 'rb'))
    return B, FR


def micro_swings(B, consec, left=2, right=2):
    """1m micro pivots, known at the close of the confirming bar."""
    hi, lo = [], []
    for i in range(left, len(B) - right):
        if not consec(i + right, i - left):
            continue
        w = B[i - left:i + right + 1]
        if all(B[i]['high'] >= x['high'] for x in w) and any(B[i]['high'] > x['high'] for x in w):
            hi.append((i + right, B[i]['high']))
        if all(B[i]['low'] <= x['low'] for x in w) and any(B[i]['low'] < x['low'] for x in w):
            lo.append((i + right, B[i]['low']))
    return hi, lo


def cooldown_filter(evs):
    """Chronological, per (name, dir-agnostic) - matches the frozen work."""
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x['j']):
        if e['tmin'] - last < COOLDOWN:
            continue
        last = e['tmin']
        out.append(e)
    return out


# ====================================================================
# RED-H1/VE  value-edge defence + trapped aggression
# ====================================================================
def red_h1(B, FR, medabs, consec, variant='FULL'):
    """variants: TOUCH | TOUCH_AGG | TOUCH_AGG_FAIL | FULL | AWAY (failed
    aggression away from the value edge) """
    ev = []
    for j in range(ATTACK_WIN + 1, len(B)):
        b = B[j]
        if not R.entry_ok(B, j) or not b.get('profReady'):
            continue
        atr = b['atr']
        val, vah = b.get('val'), b.get('vah')
        if val is None or vah is None:
            continue
        for d in (1, -1):
            edge = val if d > 0 else vah
            # find the attack bar within the window
            hit = None
            for k in range(j - ATTACK_WIN, j + 1):
                if k < 1 or not consec(j, k):
                    continue
                bk = B[k]
                ek = bk.get('val') if d > 0 else bk.get('vah')
                if ek is None:
                    continue
                near = (bk['low'] <= ek + NEAR_EDGE * atr) if d > 0 else \
                       (bk['high'] >= ek - NEAR_EDGE * atr)
                away = (bk['low'] > ek + 1.5 * atr) if d > 0 else \
                       (bk['high'] < ek - 1.5 * atr)
                if variant == 'AWAY':
                    if not away:
                        continue
                else:
                    if not near:
                        continue
                dk = bk.get('delta')
                agg = dk is not None and ((dk <= -R.Q_BD75) if d > 0 else (dk >= R.Q_BD75))
                if variant in ('TOUCH_AGG', 'TOUCH_AGG_FAIL', 'FULL', 'AWAY') and not agg:
                    continue
                if variant in ('TOUCH_AGG_FAIL', 'FULL', 'AWAY'):
                    er = R.effort_result(B, k, -d, medabs, 'E2')
                    if er is None or er[2] < FR['E2_FAIL']:
                        continue
                hit = k
                break
            if hit is None:
                continue
            if variant in ('FULL', 'AWAY'):
                # completed reclaim back above/below the edge on bar j
                if d > 0 and not (b['close'] > edge):
                    continue
                if d < 0 and not (b['close'] < edge):
                    continue
                if hit == j:
                    continue
            ev.append({'j': j, 'd': d, 'tmin': b['tmin'], 'attack_j': hit})
            break
    return cooldown_filter(ev)


# ====================================================================
# RED-H2  CVD nonconfirmation at a causal extreme
# ====================================================================
def red_h2(B, FR, consec, lows_at, highs_at, mhi_at, mlo_at, cdat,
           variant='FULL'):
    """variants: CVD_ONLY | EXTREME_CVD | EXTREME_CONF (no CVD) | FULL"""
    ev = []
    for j in range(3, len(B)):
        b = B[j]
        if not R.entry_ok(B, j):
            continue
        atr = b['atr']
        cd = b.get('cumDelta')
        if cd is None:
            continue
        for d in (1, -1):
            lv = (lows_at(j) if d > 0 else highs_at(j))
            if variant != 'CVD_ONLY':
                if not lv:
                    continue
                # nearest causally-known level being retested
                cand = None
                for (kj, px) in lv:
                    if d > 0 and abs(b['low'] - px) <= NEAR_EDGE * atr:
                        cand = (kj, px)
                        break
                    if d < 0 and abs(b['high'] - px) <= NEAR_EDGE * atr:
                        cand = (kj, px)
                        break
                if cand is None:
                    continue
                kj, px = cand
                then = cdat(kj)
                if then is None:
                    continue
                # 3. price nonconfirmation: shallow undercut or reclaim
                if d > 0:
                    under = px - b['low']
                    if not (under < NEAR_EDGE * atr or b['close'] > px):
                        continue
                else:
                    under = b['high'] - px
                    if not (under < NEAR_EDGE * atr or b['close'] < px):
                        continue
            else:
                then, px = None, None
            if variant in ('CVD_ONLY', 'EXTREME_CVD', 'FULL'):
                if variant == 'CVD_ONLY':
                    # plain divergence: cumDelta 30-bar change opposes price
                    if j < 30 or not consec(j, j - 30):
                        continue
                    prev = B[j - 30].get('cumDelta')
                    if prev is None:
                        continue
                    if d > 0 and not (cd < prev - FR['CD'] and b['close'] >= B[j - 30]['close']):
                        continue
                    if d < 0 and not (cd > prev + FR['CD'] and b['close'] <= B[j - 30]['close']):
                        continue
                else:
                    if d > 0 and not (cd < then - FR['CD']):
                        continue
                    if d < 0 and not (cd > then + FR['CD']):
                        continue
            if variant in ('EXTREME_CONF', 'FULL'):
                # confirmation: close beyond the most recent known micro pivot
                mv = (mhi_at(j) if d > 0 else mlo_at(j))
                if not mv:
                    continue
                trig = mv[0][1]
                if d > 0 and not (b['close'] > trig):
                    continue
                if d < 0 and not (b['close'] < trig):
                    continue
            ev.append({'j': j, 'd': d, 'tmin': b['tmin']})
            break
    return cooldown_filter(ev)


# ====================================================================
# RED-H6  compression + delta alignment -> release
# ====================================================================
def red_h6(B, FR, consec, variant='FULL'):
    """variants: BREAK_ONLY | DELTA_ONLY | OPPOSITE | FULL"""
    ev = []
    for j in range(7, len(B)):
        b = B[j]
        if not R.entry_ok(B, j):
            continue
        atr = b['atr']
        if not consec(j - 1, j - 6):
            continue
        w = B[j - 6:j - 1]                       # 5 compression bars, all < j
        chi = max(x['high'] for x in w)
        clo = min(x['low'] for x in w)
        comp = (chi - clo) / atr
        dsum = sum((x.get('delta') or 0.0) for x in w)
        for d in (1, -1):
            brk = (b['close'] > chi) if d > 0 else (b['close'] < clo)
            if not brk:
                continue
            # not already broken before this bar
            prior = B[j - 1]
            if d > 0 and prior['close'] > chi:
                continue
            if d < 0 and prior['close'] < clo:
                continue
            if variant in ('BREAK_ONLY', 'FULL', 'OPPOSITE'):
                if comp > FR['COMP']:
                    continue
            if variant == 'FULL':
                if d > 0 and not (dsum >= R.Q_BD75):
                    continue
                if d < 0 and not (dsum <= -R.Q_BD75):
                    continue
            if variant == 'OPPOSITE':
                if d > 0 and not (dsum <= -R.Q_BD75):
                    continue
                if d < 0 and not (dsum >= R.Q_BD75):
                    continue
            if variant == 'DELTA_ONLY':
                if d > 0 and not (dsum >= R.Q_BD75):
                    continue
                if d < 0 and not (dsum <= -R.Q_BD75):
                    continue
            ev.append({'j': j, 'd': d, 'tmin': b['tmin'], 'chi': chi, 'clo': clo})
            break
    return cooldown_filter(ev)


# ====================================================================
# RED-H10  FVG + failed aggression + contextual location
# ====================================================================
def red_h10(B, FR, medabs, consec, fvgs, locfn, variant='E', loc_name='ANY'):
    """variants: A (FVG only) | B (FVG+loc) | C (FVG+failed agg)
                 | D (loc+failed agg, no FVG) | E (FULL)"""
    ev = []
    if variant == 'D':
        for j in range(1, len(B)):
            b = B[j]
            if not R.entry_ok(B, j):
                continue
            atr = b['atr']
            for d in (1, -1):
                near = locfn(j, d, b['low'] if d > 0 else b['high'], atr)
                if not near:
                    continue
                dk = b.get('delta')
                if dk is None or ((dk > -R.Q_BD75) if d > 0 else (dk < R.Q_BD75)):
                    continue
                er = R.effort_result(B, j, -d, medabs, 'E2')
                if er is None or er[2] < FR['E2_FAIL']:
                    continue
                ev.append({'j': j, 'd': d, 'tmin': b['tmin']})
                break
        return cooldown_filter(ev)

    for f in fvgs:
        d = f['dir']
        lo, hi = f['lo'], f['hi']
        mid = 0.5 * (lo + hi)
        j0 = f['j']
        atr0 = B[j0]['atr']
        if not atr0 or atr0 <= 0:
            continue
        if variant in ('B', 'E'):
            if not locfn(j0, d, mid, atr0):
                continue
        # first mitigation, then (for C/E) failed aggression, then reclaim
        attack = None
        for k in range(j0 + 1, min(j0 + 1 + 120, len(B))):
            if not consec(k, j0):
                break
            bk = B[k]
            touched = (bk['low'] <= hi) if d > 0 else (bk['high'] >= lo)
            if not touched:
                continue
            if variant == 'A':
                if R.entry_ok(B, k):
                    ev.append({'j': k, 'd': d, 'tmin': bk['tmin']})
                break
            dk = bk.get('delta')
            agg = dk is not None and ((dk <= -R.Q_BD75) if d > 0 else (dk >= R.Q_BD75))
            if variant == 'B':
                if R.entry_ok(B, k):
                    ev.append({'j': k, 'd': d, 'tmin': bk['tmin']})
                break
            if not agg:
                break                        # first mitigation only
            er = R.effort_result(B, k, -d, medabs, 'E2')
            if er is None or er[2] < FR['E2_FAIL']:
                break
            attack = k
            break
        if attack is None:
            continue
        if variant == 'C':
            if R.entry_ok(B, attack):
                ev.append({'j': attack, 'd': d, 'tmin': B[attack]['tmin']})
            continue
        for k in range(attack + 1, min(attack + 1 + ATTACK_WIN, len(B))):
            if not consec(k, attack):
                break
            bk = B[k]
            back = (bk['close'] > mid) if d > 0 else (bk['close'] < mid)
            if back:
                if R.entry_ok(B, k):
                    ev.append({'j': k, 'd': d, 'tmin': bk['tmin'], 'fvg': (lo, hi)})
                break
    return cooldown_filter(ev)
