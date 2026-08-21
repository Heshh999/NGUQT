#!/usr/bin/env python3
# ======================================================================
# OF-N FAMILY - twelve declared order-flow event hypotheses, OF-N1..N12.
# Declared 2026-08-21 before first run. Directions and mechanisms are the
# user's; every mechanical parameter below is frozen HERE, before any
# result was seen, and none is changed afterwards.
#
# STANDING PROTOCOL (docs/TEN_MONTH_PROTOCOL.md):
#   - M=12 family; sign-flip-by-day null; max-statistic family-wise p;
#     BH over 12; excess over side- and split-matched baseline.
#   - DEV = 2025-11..2026-03, INTERNAL REPLICATION (IR) = 2026-04..08.
#   - The measured family-wise noise bar at this width on this window is
#     roughly +9..+12 pt/trade (power10b famdist). Smaller effects
#     cannot be certified here regardless of what the means show.
#   - Decisive criterion (per the whole programme): entry ORDERING -
#     medMFE/medMAE and 1-ATR favourable-first vs the sign-flip null.
#
# FROZEN MECHANICAL PARAMETERS (all quantiles computed on DEV eligible
# bars only, applied unchanged to IR):
#   "unusually strong" = p90;  "extreme" volume/tick = p95;
#   "heavy delta" = p75 of |barDelta|;  aggression window = 5 bars;
#   "very little progress" = <= 0.25 ATR over the window;
#   reaction/trigger windows = 3 completed 1m bars unless stated;
#   N2 pullback >= 0.5 ATR, push2 progress <= 0.15 ATR, gap <= 30 bars,
#      trigger window 5 bars, structure break = close beyond last-3-bar
#      extreme;
#   N5 continuation window 3 bars, pullback window 10 bars, "shallow" =
#      no close past the imbalance bar midpoint;
#   N6 impulse = 5-bar delta >= p90 with >= 1.0 ATR displacement;
#      pullback depth >= 0.3 ATR, opposing participation <= 30% of the
#      impulse delta, window 10 bars;
#   N7 extremes = fresh 60-bar price extreme, CVD compared per-extreme
#      within the same session, trigger window 5 bars;
#   N8 flip = post-breach delta sum <= -1x |breach-bar delta| AND close
#      back inside, window 3 bars;
#   N9 vpt = volume / range-in-ticks, p95; fresh extreme = 20-bar;
#   N10 deltaRange = (maxDelta-minDelta)/volume p90; directional close =
#      close location >= 0.8 (or <= 0.2); displacement = range >= 1 ATR;
#   N11 migration = POC(now) >= POC(30 bars ago)+0.5 ATR AND >= POC(60
#      bars ago)+1.0 ATR; pullback touch = low within 0.25 ATR of POC
#      with close still beyond; aggression = positive delta + >=1
#      stacked level; trigger = close beyond prior bar extreme;
#   N12 break = close beyond VAH/VAL with |barDelta| >= p75 same-sign;
#      failure = close back inside within 3 bars with no intervening
#      close beyond level+0.25 ATR.
#   Stacked "multiple" = >= 2 levels (3x tier).
#   Entry always at a COMPLETED 1m close; RTH; >=30 min after open;
#   >=60 min to close; 60m horizon; 30-min per-hypothesis cooldown;
#   cost 0.87 pt RT. R = distance to the stated structural stop + 1
#   tick; stop family only for gate passers (declared gate: n>=40,
#   pooled excess>0 in BOTH splits, ff1>50% in BOTH splits).
#   THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, random
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ofht_cache import load as load_bars3
from ofht_spec import (TICK, DEV_END, attach_dsum15, aggregate, swings,
                       prevday_levels, entry_ok, geometry, ATR_LEVELS)

random.seed(41)
COST = 0.87
HORIZON = 60
COOL = 30
NAMES = ['N%d' % k for k in range(1, 13)]

B = load_bars3()
attach_dsum15(B)
N = len(B)

BASE = {}
_eb = [j for j in range(N) if entry_ok(B, j)]
for sp in ('DEV', 'IR'):
    for d in (1, -1):
        v = [(B[j + HORIZON]['close'] - B[j]['close']) * d for j in _eb
             if ('DEV' if B[j]['day'] <= DEV_END else 'IR') == sp]
        BASE[(sp, d)] = sum(v) / len(v)

# ---------------- rolling features (causal, consecutive-minute checked)
for j in range(N):
    b = B[j]
    ok5 = j >= 5 and B[j]['tmin'] - B[j - 5]['tmin'] == 5
    b['sd5'] = (sum(B[k]['ofBarDelta'] or 0 for k in range(j - 4, j + 1))
                if ok5 and all(B[k]['ofBarDelta'] is not None
                               for k in range(j - 4, j + 1)) else None)
    b['disp5'] = (b['close'] - B[j - 5]['close']) if ok5 else None
    rng = b['high'] - b['low']
    b['vpt'] = (b['ofTotalVolume'] / max(rng / TICK, 1.0)
                if b['ofTotalVolume'] else None)
    b['clr'] = (b['close'] - b['low']) / rng if rng > 0 else 0.5
    if b['ofMaxDelta'] is not None and b['ofMinDelta'] is not None and b['ofTotalVolume']:
        b['drng'] = (b['ofMaxDelta'] - b['ofMinDelta']) / max(b['ofTotalVolume'], 1.0)
    else:
        b['drng'] = None
    b['stB'] = b['stackedBuyLevels_3x'] or 0
    b['stS'] = b['stackedSellLevels_3x'] or 0

# rolling 20 & 60 bar prior extremes
for W in (20, 60):
    hh = []
    ll = []
    for j in range(N):
        if j >= W and B[j]['tmin'] - B[j - W]['tmin'] == W:
            B[j]['hi%d' % W] = max(B[k]['high'] for k in range(j - W, j))
            B[j]['lo%d' % W] = min(B[k]['low'] for k in range(j - W, j))
        else:
            B[j]['hi%d' % W] = None
            B[j]['lo%d' % W] = None

DEVB = [j for j in _eb if B[j]['day'] <= DEV_END]
def q(vals, p):
    s = sorted(vals)
    return s[min(int(len(s) * p), len(s) - 1)]

Q_SD5 = q([abs(B[j]['sd5']) for j in DEVB if B[j]['sd5'] is not None], 0.90)
Q_ABS = q([B[j]['absorptionStrengthRaw'] for j in DEVB
           if B[j]['absorptionStrengthRaw'] is not None], 0.90)
Q_VPT = q([B[j]['vpt'] for j in DEVB if B[j]['vpt'] is not None], 0.95)
Q_DRG = q([B[j]['drng'] for j in DEVB if B[j]['drng'] is not None], 0.90)
Q_BD75 = q([abs(B[j]['ofBarDelta']) for j in DEVB
            if B[j]['ofBarDelta'] is not None], 0.75)
Q_RATR = q([(B[j]['high'] - B[j]['low']) / B[j]['atr'] for j in DEVB
            if B[j]['atr']], 0.50)
print('frozen DEV thresholds: sd5p90 %.0f  absorb90 %.1f  vpt95 %.0f  drng90 %.3f  bd75 %.0f'
      % (Q_SD5, Q_ABS, Q_VPT, Q_DRG, Q_BD75))

AGG3 = aggregate(B, 3)
AGG15 = aggregate(B, 15)
SW3L, SW3H = swings(AGG3)
SW15L, SW15H = swings(AGG15)
PDL = prevday_levels(B)

RAW = defaultdict(list)          # name -> [(j, d, R)] pre-cooldown
ENT = defaultdict(list)


def fire(name, j, d, stop_ref):
    # DEFECT FIX (first run): the original fire() applied the cooldown
    # inline, but several scanners run each direction as a separate full
    # pass - the stale timestamp from pass 1 then silently blocked
    # essentially every entry in pass 2 (N6 fired 490 long / 2 short on
    # data with 3,484 / 3,705 balanced candidates). The declared rule
    # was always a CHRONOLOGICAL 30-min per-hypothesis cooldown; it is
    # now applied once, in time order, after all scanners finish.
    if not entry_ok(B, j):
        return
    e = B[j]['close']
    R = (e - (stop_ref - TICK)) if d > 0 else ((stop_ref + TICK) - e)
    if R <= 0:
        return
    RAW[name].append((j, d, R))


def apply_cooldown():
    for name, lst in RAW.items():
        lst.sort(key=lambda x: B[x[0]]['tmin'])
        last = -10 ** 9
        for j, d, R in lst:
            if B[j]['tmin'] - last < COOL:
                continue
            last = B[j]['tmin']
            ENT[name].append((j, d, R))


def consec(j, k):
    return B[j]['tmin'] - B[k]['tmin'] == j - k


# ---------------- N1 aggression failure -------------------------------
for j in range(5, N):
    b = B[j]
    if b['sd5'] is None or b['atr'] is None or b['atr'] <= 0:
        continue
    stk = sum(B[k]['stB'] for k in range(j - 4, j + 1))
    stkS = sum(B[k]['stS'] for k in range(j - 4, j + 1))
    for d, sd_ok, st_ok in ((-1, b['sd5'] >= Q_SD5, stk >= 2),
                            (+1, b['sd5'] <= -Q_SD5, stkS >= 2)):
        if not (sd_ok and st_ok):
            continue
        prog = (b['close'] - B[j - 5]['close']) * (-d)      # aggression dir = -d
        if prog > 0.25 * b['atr']:
            continue
        if d < 0:
            micro = min(B[k]['low'] for k in range(j - 4, j + 1))
            ref = max(B[k]['high'] for k in range(j - 4, j + 1))
        else:
            micro = max(B[k]['high'] for k in range(j - 4, j + 1))
            ref = min(B[k]['low'] for k in range(j - 4, j + 1))
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d < 0 and B[k]['close'] < micro) or (d > 0 and B[k]['close'] > micro):
                fire('N1', k, d, ref)
                break

# ---------------- N2 two-push delta exhaustion ------------------------
for d in (+1, -1):
    push = None                 # (idx, extreme, legDelta)
    pb_ext = None
    pb_idx = None
    leg_delta = 0.0
    for j in range(60, N):
        b = B[j]
        hiW = b['hi20'] if d > 0 else b['lo20']
        if hiW is None or b['atr'] is None or b['atr'] <= 0:
            push = None
            continue
        new_ext = (b['high'] > hiW) if d > 0 else (b['low'] < hiW)
        if push is not None:
            e = b['low'] if d > 0 else b['high']
            if pb_ext is None or (d > 0 and e < pb_ext) or (d < 0 and e > pb_ext):
                pb_ext = e
                pb_idx = j
                leg_delta = 0.0
            leg_delta += b['ofBarDelta'] or 0
        if new_ext:
            ext = b['high'] if d > 0 else b['low']
            if push is not None and pb_ext is not None and j - push[0] <= 30 \
                    and (push[1] - pb_ext) * d >= 0.5 * b['atr'] * (1 if d > 0 else -1) * d:
                depth = (push[1] - pb_ext) if d > 0 else (pb_ext - push[1])
                prog = (ext - push[1]) if d > 0 else (push[1] - ext)
                d2 = leg_delta * d
                if depth >= 0.5 * b['atr'] and d2 >= push[2] and prog <= 0.15 * b['atr']:
                    for k in range(j + 1, min(j + 6, N)):
                        if not consec(k, j):
                            break
                        if k < 3:
                            continue
                        brk = (min(B[i]['low'] for i in range(k - 3, k))
                               if d > 0 else max(B[i]['high'] for i in range(k - 3, k)))
                        if (d > 0 and B[k]['close'] < brk) or (d < 0 and B[k]['close'] > brk):
                            fire('N2', k, -d, ext)
                            break
            push = (j, ext, leg_delta * d if push is not None else 0.0)
            pb_ext = None
            leg_delta = 0.0

# ---------------- N3 absorption at fresh swing extreme ----------------
for evs, d in (([(t, v) for t, v in SW3H + SW15H], -1),
               ([(t, v) for t, v in SW3L + SW15L], +1)):
    evs = sorted(evs)
    ei = 0
    active = []
    for j in range(N):
        b = B[j]
        while ei < len(evs) and evs[ei][0] <= b['tmin']:
            active.append(evs[ei][1])
            ei += 1
        if len(active) > 12:
            active = active[-12:]
        if b['atr'] is None or b['atr'] <= 0:
            continue
        hitl = [lv for lv in active
                if (d < 0 and b['high'] >= lv) or (d > 0 and b['low'] <= lv)]
        if not hitl:
            continue
        active = [lv for lv in active if lv not in hitl]
        ab = b['absorptionStrengthRaw']
        if ab is None or ab < Q_ABS:
            continue
        closed_ok = (b['close'] < max(hitl)) if d < 0 else (b['close'] > min(hitl))
        if not closed_ok:
            continue
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d < 0 and B[k]['close'] < b['low']) or (d > 0 and B[k]['close'] > b['high']):
                ref = (max(B[i]['high'] for i in range(j, k + 1)) if d < 0
                       else min(B[i]['low'] for i in range(j, k + 1)))
                fire('N3', k, d, ref)
                break

# ---------------- N4 / N5 stacked imbalance fail / accept -------------
for j in range(N):
    b = B[j]
    for d0, st in ((+1, b['stB']), (-1, b['stS'])):     # d0 = imbalance dir
        if st < 2:
            continue
        # N4: no continuation through extreme, then break opposite side
        broke = False
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d0 > 0 and B[k]['high'] > b['high']) or (d0 < 0 and B[k]['low'] < b['low']):
                broke = True                      # continued -> N4 dead
            if not broke and ((d0 > 0 and B[k]['close'] < b['low'])
                              or (d0 < 0 and B[k]['close'] > b['high'])):
                fire('N4', k, -d0, b['high'] if d0 > 0 else b['low'])
                break
        # N5: acceptance -> shallow pullback -> renewed aggression
        acc = None
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d0 > 0 and B[k]['close'] > b['high']) or (d0 < 0 and B[k]['close'] < b['low']):
                acc = k
                break
        if acc is None:
            continue
        mid = (b['high'] + b['low']) / 2.0
        pb = None
        dead = False
        for k in range(acc + 1, min(acc + 11, N)):
            if not consec(k, acc):
                break
            c = B[k]
            if (d0 > 0 and c['close'] < mid) or (d0 < 0 and c['close'] > mid):
                dead = True
                break
            if pb is None:
                if (d0 > 0 and c['low'] < B[k - 1]['low']) or \
                   (d0 < 0 and c['high'] > B[k - 1]['high']):
                    pb = k
                continue
            bd = c['ofBarDelta'] or 0
            if (d0 > 0 and bd > 0 and c['close'] > B[k - 1]['high']) or \
               (d0 < 0 and bd < 0 and c['close'] < B[k - 1]['low']):
                ref = (min(B[i]['low'] for i in range(pb, k + 1)) if d0 > 0
                       else max(B[i]['high'] for i in range(pb, k + 1)))
                fire('N5', k, d0, ref)
                break

# ---------------- N6 impulse / weak pullback / re-expansion -----------
for d in (+1, -1):
    j = 60
    while j < N:
        b = B[j]
        if (b['sd5'] is None or b['atr'] is None or b['atr'] <= 0
                or b['disp5'] is None):
            j += 1
            continue
        imp = (b['sd5'] >= Q_SD5 and b['disp5'] >= 1.0 * b['atr']) if d > 0 else \
              (b['sd5'] <= -Q_SD5 and b['disp5'] <= -1.0 * b['atr'])
        if not imp:
            j += 1
            continue
        impdelta = abs(b['sd5'])
        pb_ext = None
        opp = 0.0
        fired = False
        for k in range(j + 1, min(j + 11, N)):
            if not consec(k, j):
                break
            c = B[k]
            e = c['low'] if d > 0 else c['high']
            if pb_ext is None or (d > 0 and e < pb_ext) or (d < 0 and e > pb_ext):
                pb_ext = e
            bd = c['ofBarDelta'] or 0
            if bd * d < 0:
                opp += abs(bd)
            depth = (b['close'] - pb_ext) if d > 0 else (pb_ext - b['close'])
            if depth < 0.3 * b['atr'] or opp > 0.3 * impdelta:
                if opp > 0.3 * impdelta:
                    break
                continue
            if (d > 0 and bd > 0 and c['close'] > B[k - 1]['high']) or \
               (d < 0 and bd < 0 and c['close'] < B[k - 1]['low']):
                fire('N6', k, d, pb_ext)
                fired = True
                break
        j = j + 5 if fired else j + 1

# ---------------- N7 CVD nonconfirmation at fresh extremes ------------
for d in (+1, -1):
    prev_cvd = None
    curday = None
    for j in range(N):
        b = B[j]
        if b['day'] != curday:
            curday = b['day']
            prev_cvd = None
        w = b['hi60'] if d > 0 else b['lo60']
        if w is None or b['ofCumDelta'] is None:
            continue
        newex = (b['high'] > w) if d > 0 else (b['low'] < w)
        if not newex:
            continue
        cvd = b['ofCumDelta']
        div = prev_cvd is not None and ((d > 0 and cvd < prev_cvd)
                                        or (d < 0 and cvd > prev_cvd))
        prev_cvd = cvd
        if not div:
            continue
        ext = b['high'] if d > 0 else b['low']
        for k in range(j + 1, min(j + 6, N)):
            if not consec(k, j) or k < 3:
                break
            brk = (min(B[i]['low'] for i in range(k - 3, k)) if d > 0
                   else max(B[i]['high'] for i in range(k - 3, k)))
            if (d > 0 and B[k]['close'] < brk) or (d < 0 and B[k]['close'] > brk):
                fire('N7', k, -d, ext)
                break

# ---------------- N8 delta flip at a sweep ----------------------------
LOWEV = sorted([(t, v) for t, v in SW3L + SW15L])
HIGHEV = sorted([(t, v) for t, v in SW3H + SW15H])
for evs, side in ((HIGHEV, -1), (LOWEV, +1)):    # side = trade dir on failure
    slot = {}
    ei = 0
    for j in range(N):
        b = B[j]
        while ei < len(evs) and evs[ei][0] <= b['tmin']:
            slot['SW'] = evs[ei][1]
            ei += 1
        pd = PDL.get(b['day'])
        if pd:
            slot.setdefault('PDLDAY_' + b['day'], None)
            slot['PDL'] = pd[0] if side < 0 else pd[1]
        breached = []
        for key in ('SW', 'PDL'):
            lv = slot.get(key)
            if lv is None:
                continue
            if (side < 0 and b['high'] > lv) or (side > 0 and b['low'] < lv):
                breached.append(lv)
                slot[key] = None
        if not breached:
            continue
        lvl = min(breached) if side < 0 else max(breached)
        bd0 = b['ofBarDelta'] or 0
        if bd0 * (-side) <= 0:                   # breakout delta must agree
            continue
        post = 0.0
        ext = b['high'] if side < 0 else b['low']
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            c = B[k]
            ext = max(ext, c['high']) if side < 0 else min(ext, c['low'])
            post += c['ofBarDelta'] or 0
            flip = (post <= -abs(bd0)) if side < 0 else (post >= abs(bd0))
            inside = (c['close'] < lvl) if side < 0 else (c['close'] > lvl)
            if flip and inside:
                fire('N8', k, side, ext)
                break

# ---------------- N9 volume-per-tick exhaustion (+ control) -----------
CTRL9 = []
for j in range(N):
    b = B[j]
    if b['vpt'] is None or b['vpt'] < Q_VPT or b['atr'] is None or b['atr'] <= 0:
        continue
    for d, fresh in ((-1, b['hi20'] is not None and b['high'] > b['hi20']),
                     (+1, b['lo20'] is not None and b['low'] < b['lo20'])):
        if not fresh:
            continue
        big = (b['high'] - b['low']) / b['atr'] >= Q_RATR
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            if (d < 0 and B[k]['close'] < b['low']) or (d > 0 and B[k]['close'] > b['high']):
                if big:
                    if entry_ok(B, k):
                        e = B[k]['close']
                        ref = b['high'] if d < 0 else b['low']
                        R = (e - (ref - TICK)) if d > 0 else ((ref + TICK) - e)
                        if R > 0:
                            CTRL9.append((k, d, R))
                else:
                    fire('N9', k, d, b['high'] if d < 0 else b['low'])
                break

# ---------------- N10 delta-range + directional close (+ control) -----
CTRL10 = []
for j in range(N):
    b = B[j]
    if b['drng'] is None or b['drng'] < Q_DRG or b['atr'] is None or b['atr'] <= 0:
        continue
    disp = (b['high'] - b['low']) >= 1.0 * b['atr']
    if b['clr'] >= 0.8 and b['close'] > b['open'] and disp:
        fire('N10', j, +1, b['low'])
    elif b['clr'] <= 0.2 and b['close'] < b['open'] and disp:
        fire('N10', j, -1, b['high'])
    elif 0.35 <= b['clr'] <= 0.65 and disp and entry_ok(B, j):
        d = 1 if (b['ofBarDelta'] or 0) > 0 else -1
        e = b['close']
        ref = b['low'] if d > 0 else b['high']
        R = (e - (ref - TICK)) if d > 0 else ((ref + TICK) - e)
        if R > 0:
            CTRL10.append((j, d, R))

# ---------------- N11 value migration + aggression --------------------
for j in range(60, N):
    b = B[j]
    if not b['profileReady'] or b['profilePoc'] is None or b['atr'] is None or b['atr'] <= 0:
        continue
    p30 = B[j - 30]['profilePoc'] if consec(j, j - 30) else None
    p60 = B[j - 60]['profilePoc'] if consec(j, j - 60) else None
    if p30 is None or p60 is None:
        continue
    for d in (+1, -1):
        mig = (b['profilePoc'] >= p30 + 0.5 * b['atr']
               and b['profilePoc'] >= p60 + 1.0 * b['atr']) if d > 0 else \
              (b['profilePoc'] <= p30 - 0.5 * b['atr']
               and b['profilePoc'] <= p60 - 1.0 * b['atr'])
        if not mig:
            continue
        touch = (b['low'] <= b['profilePoc'] + 0.25 * b['atr']
                 and b['close'] > b['profilePoc']) if d > 0 else \
                (b['high'] >= b['profilePoc'] - 0.25 * b['atr']
                 and b['close'] < b['profilePoc'])
        bd = b['ofBarDelta'] or 0
        agg = (bd > 0 and b['stB'] >= 1) if d > 0 else (bd < 0 and b['stS'] >= 1)
        if not (touch and agg):
            continue
        k = j + 1
        if k < N and consec(k, j):
            if (d > 0 and B[k]['close'] > b['high']) or (d < 0 and B[k]['close'] < b['low']):
                fire('N11', k, d, b['low'] if d > 0 else b['high'])

# ---------------- N12 value break failure with trapped delta ----------
for j in range(N):
    b = B[j]
    if not b['profileReady'] or b['profileVah'] is None or b['profileVal'] is None:
        continue
    if b['atr'] is None or b['atr'] <= 0 or b['ofBarDelta'] is None:
        continue
    for d, lvl, out in ((-1, b['profileVah'], b['close'] > b['profileVah']
                         and b['ofBarDelta'] >= Q_BD75),
                        (+1, b['profileVal'], b['close'] < b['profileVal']
                         and b['ofBarDelta'] <= -Q_BD75)):
        if not out:
            continue
        ext = b['high'] if d < 0 else b['low']
        dead = False
        for k in range(j + 1, min(j + 4, N)):
            if not consec(k, j):
                break
            c = B[k]
            ext = max(ext, c['high']) if d < 0 else min(ext, c['low'])
            if (d < 0 and c['close'] > lvl + 0.25 * b['atr']) or \
               (d > 0 and c['close'] < lvl - 0.25 * b['atr']):
                dead = True
                break
            if (d < 0 and c['close'] < lvl) or (d > 0 and c['close'] > lvl):
                fire('N12', k, d, ext)
                break
        if dead:
            continue

apply_cooldown()

# ================================================================ stats
def split_of(day):
    return 'DEV' if day <= DEV_END else 'IR'


GEO = {}
GEOF = {}
for nm in NAMES:
    GEO[nm] = [geometry(B, j, d, R, BASE) for j, d, R in ENT[nm]]
    GEOF[nm] = [geometry(B, j, -d, None, BASE) for j, d, R in ENT[nm]]
GC9 = [geometry(B, j, d, R, BASE) for j, d, R in CTRL9]
GC10 = [geometry(B, j, d, R, BASE) for j, d, R in CTRL10]


def med(v):
    s = sorted(v)
    return s[len(s) // 2] if s else float('nan')


def ff(gs, x=1.0):
    f = sum(1 for g in gs if g['atr'][x] == 1)
    a = sum(1 for g in gs if g['atr'][x] == 2)
    return 100.0 * f / (f + a) if f + a else float('nan')


def line(tag, gs):
    if not gs:
        print('  %-26s n=0' % tag)
        return
    exc = [g['exc'] for g in gs]
    print('  %-26s n=%5d  exc %+7.2f  net %+7.2f  ratio %5.3f  ff05 %4.1f ff1 %4.1f ff2 %4.1f'
          % (tag, len(gs), sum(exc) / len(exc), sum(exc) / len(exc) - COST,
             med([g['mfe'] for g in gs]) / med([g['mae'] for g in gs])
             if med([g['mae'] for g in gs]) else float('nan'),
             ff(gs, 0.5), ff(gs, 1.0), ff(gs, 2.0)))


DAYS = sorted(set(B[j]['day'] for j in _eb))
print('\n' + '=' * 110)
print('OF-N FAMILY  (60m horizon, excess over side/split-matched baseline, cost %.2f)' % COST)
print('=' * 110)
for nm in NAMES:
    gs = GEO[nm]
    line('OF-' + nm, gs)
    if not gs:
        continue
    for sp in ('DEV', 'IR'):
        line('   %s' % sp, [g for g in gs if g['sp'] == sp])
    line('   LONG', [g for g in gs if g['d'] > 0])
    line('   SHORT', [g for g in gs if g['d'] < 0])
    bym = defaultdict(list)
    for g in gs:
        bym[g['day'][:7]].append(g['exc'] - COST)
    print('   months: ' + ' '.join('%s%+0.1f(%d)' % (m[2:], sum(v) / len(v), len(v))
                                   for m, v in sorted(bym.items())))
    net = sorted((g['exc'] - COST for g in gs), reverse=True)
    k5 = max(1, len(net) // 20)
    print('   top5%%=%d trades carry %+0.1f of total %+0.1f'
          % (k5, sum(net[:k5]), sum(net)))
line('CTRL N9 big-range', GC9)
line('CTRL N10 mid-close', GC10)

# ---------------- family-wise sign-flip -------------------------------
print('\n' + '=' * 110)
print('FAMILY STATISTICS  (sign-flip by day; M=12 declared)')
print('=' * 110)
realmu = {}
for nm in NAMES:
    gs = GEO[nm]
    if gs:
        realmu[nm] = sum(g['exc'] for g in gs) / len(gs)
NS = 2000
praw = {}
for nm in realmu:
    gs = GEO[nm]
    gf = GEOF[nm]
    days = sorted(set(g['day'] for g in gs))
    ge = 0
    for _ in range(NS):
        fl = {d: (1 if random.random() < 0.5 else -1) for d in days}
        acc = 0.0
        for g, f2 in zip(gs, gf):
            acc += (g if fl[g['day']] > 0 else f2)['exc']
        if acc / len(gs) >= realmu[nm]:
            ge += 1
    praw[nm] = ge / float(NS)

NSF = 1000
famdist = []
alldays = sorted(set(g['day'] for nm in realmu for g in GEO[nm]))
for _ in range(NSF):
    fl = {d: (1 if random.random() < 0.5 else -1) for d in alldays}
    bm = -9e9
    for nm in realmu:
        acc = 0.0
        for g, f2 in zip(GEO[nm], GEOF[nm]):
            acc += (g if fl[g['day']] > 0 else f2)['exc']
        m = acc / len(GEO[nm])
        if m > bm:
            bm = m
    famdist.append(bm)
famdist.sort()
best = max(realmu, key=lambda k: realmu[k])
gef = sum(1 for x in famdist if x >= realmu[best])
order = sorted(praw, key=lambda k: praw[k])
print('  %-6s %7s %9s %9s %10s' % ('hyp', 'n', 'exc', 'p raw', 'BH q (M=12)'))
prev = 1.0
bh = {}
for i in range(len(order) - 1, -1, -1):
    nm = order[i]
    qv = praw[nm] * 12.0 / (i + 1)
    prev = min(prev, qv)
    bh[nm] = prev
for nm in order:
    print('  %-6s %7d %+9.2f %9.4f %10.4f' % (nm, len(GEO[nm]), realmu[nm], praw[nm], bh[nm]))
print('  family max: real %+0.2f (%s)  null median %+0.2f  p90 %+0.2f  p95 %+0.2f'
      % (realmu[best], best, famdist[NSF // 2], famdist[int(NSF * .9)], famdist[int(NSF * .95)]))
print('  FAMILY-WISE p = %.4f' % (gef / float(NSF)))

# ---------------- gate + stop family ----------------------------------
print('\nSTOP FAMILY (gate: n>=40, exc>0 both splits, ff1>50 both splits)')
for nm in NAMES:
    gs = GEO[nm]
    if len(gs) < 40:
        continue
    okgate = True
    for sp in ('DEV', 'IR'):
        sub = [g for g in gs if g['sp'] == sp]
        if not sub or sum(g['exc'] for g in sub) / len(sub) <= 0 or ff(sub, 1.0) <= 50:
            okgate = False
    if not okgate:
        continue
    print('  %s passes the gate:' % nm)
    for mode in ('struct', 1.0, 1.5):
        outs = {'DEV': [], 'IR': []}
        for (j, d, R), g in zip(ENT[nm], gs):
            S = R if mode == 'struct' else mode * B[j]['atr']
            spx = B[j]['close'] - d * S
            res = None
            for k in range(1, HORIZON + 1):
                c = B[j + k]
                if (d > 0 and c['low'] <= spx) or (d < 0 and c['high'] >= spx):
                    res = -S
                    break
            if res is None:
                res = (B[j + HORIZON]['close'] - B[j]['close']) * d
            outs[g['sp']].append(res - COST)
        row = '    stop %-7s' % str(mode)
        for sp in ('DEV', 'IR'):
            v = outs[sp]
            row += '  %s n=%3d net %+7.2f win%% %4.1f' % (
                sp, len(v), sum(v) / len(v) if v else float('nan'),
                100.0 * sum(1 for x in v if x > 0) / len(v) if v else 0)
        print(row)
print('\n(hypotheses failing the gate get no stop/target work - by declaration)')
