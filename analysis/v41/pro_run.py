#!/usr/bin/env python3
# ======================================================================
# PRO-OF-V1  Track A - H1..H8 implementation
# ======================================================================
# Rules exactly as docs/PROOF_PREREGISTRATION.md (committed first).
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, pickle
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import red_lib as R

Q75 = R.Q_BD75            # 511
CD = 586.0                # RED freeze
COOL = 30


def load():
    B = pickle.load(open(R.SCR + '/red_bars.pkl', 'rb'))
    FR = pickle.load(open(R.SCR + '/pro_frozen.pkl', 'rb'))
    return B, FR


def cool(evs):
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x['j']):
        if e['tmin'] - last < COOL:
            continue
        last = e['tmin']
        out.append(e)
    return out


def balances(B, consec, cut):
    """Per bar j: the prior-30-bar balance (hi, lo) when it qualifies."""
    out = [None] * len(B)
    for j in range(30, len(B)):
        if not consec(j - 1, j - 30):
            continue
        w = B[j - 30:j]
        atr = B[j]['atr']
        if not atr or atr <= 0:
            continue
        hi = max(x['high'] for x in w)
        lo = min(x['low'] for x in w)
        if (hi - lo) / atr <= cut:
            out[j] = (hi, lo)
    return out


# ---------------------------------------------------------------- H1
def h1(B, consec, bal, arm='FULL'):
    ev = []
    j = 30
    while j < len(B) - 6:
        b = bal[j]
        if b is None:
            j += 1
            continue
        hi, lo = b
        c = B[j]
        for d, edge in ((1, hi), (-1, lo)):
            brk = (c['close'] > edge) if d > 0 else (c['close'] < edge)
            if not brk:
                continue
            dl = c.get('delta') or 0.0
            if arm in ('DELTA', 'FULL') and dl * d < Q75:
                continue
            if arm in ('ACCEPT', 'FULL'):
                if not consec(j + 5, j):
                    continue
                outs = sum(1 for k in range(j + 1, j + 6)
                           if (B[k]['close'] > edge if d > 0 else B[k]['close'] < edge))
                back = any((B[k]['close'] < edge if d > 0 else B[k]['close'] > edge)
                           for k in range(j + 1, j + 6))
                if outs < 4 or back:
                    continue
                k = j + 5
            else:
                k = j
            if R.entry_ok(B, k):
                ev.append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
            break
        j += 1
    return cool(ev)


# ---------------------------------------------------------------- H2
def h2(B, consec, bal, arm='FULL'):
    ev = []
    for j in range(30, len(B) - 11):
        b = bal[j]
        if b is None:
            continue
        hi, lo = b
        c = B[j]
        for d, edge in ((1, lo), (-1, hi)):     # d = trade direction (reclaim)
            out = (c['close'] < edge) if d > 0 else (c['close'] > edge)
            if not out:
                continue
            # elevated participation outside
            elev = (c.get('relVol') or 0) >= 2.0 or abs(c.get('delta') or 0) >= Q75
            if arm in ('VOL', 'FULL') and not elev:
                continue
            if arm in ('RECLAIM', 'FULL'):
                done = False
                for k in range(j + 1, min(j + 11, len(B))):
                    if not consec(k, j):
                        break
                    ck = B[k]
                    back = (ck['close'] > edge) if d > 0 else (ck['close'] < edge)
                    if back:
                        if R.entry_ok(B, k):
                            ev.append({'j': k, 'd': d, 'tmin': ck['tmin'],
                                       'exc': abs(min(B[m]['low'] for m in range(j, k + 1)) - edge)
                                       if d > 0 else
                                       abs(max(B[m]['high'] for m in range(j, k + 1)) - edge),
                                       'bars_out': k - j})
                        done = True
                        break
                if done:
                    break
            else:
                if R.entry_ok(B, j):
                    ev.append({'j': j, 'd': d, 'tmin': c['tmin']})
                break
    return cool(ev)


# ---------------------------------------------------------------- H3
def h3(B, consec, lo_at, hi_at):
    """Returns (accepted, rejected) arms."""
    acc, rej = [], []
    for j in range(1, len(B) - 11):
        b = B[j]
        if (b.get('relVol') or 0) < 2.0:
            continue
        for d0 in (1, -1):                     # d0 = direction of the RUN
            lv = (hi_at(j) if d0 > 0 else lo_at(j))
            ext = None
            for _, px in lv:
                if d0 > 0 and b['high'] > px:
                    ext = px
                    break
                if d0 < 0 and b['low'] < px:
                    ext = px
                    break
            if ext is None:
                continue
            outs = 0
            resolved = False
            for k in range(j + 1, min(j + 11, len(B))):
                if not consec(k, j):
                    break
                ck = B[k]
                beyond = (ck['close'] > ext) if d0 > 0 else (ck['close'] < ext)
                if beyond:
                    outs += 1
                    if outs >= 3:
                        if R.entry_ok(B, k):
                            acc.append({'j': k, 'd': d0, 'tmin': ck['tmin']})
                        resolved = True
                        break
                else:
                    outs = 0
                    if k <= j + 5:
                        back = (ck['close'] < ext) if d0 > 0 else (ck['close'] > ext)
                        if back:
                            if R.entry_ok(B, k):
                                rej.append({'j': k, 'd': -d0, 'tmin': ck['tmin']})
                            resolved = True
                            break
            if resolved:
                break
    return cool(acc), cool(rej)


# ---------------------------------------------------------------- H4
def h4(B, consec, contracted=True):
    ev = []
    for j in range(5, len(B) - 21):
        if not consec(j, j - 5):
            continue
        atr = B[j]['atr']
        if not atr or atr <= 0:
            continue
        move = B[j]['close'] - B[j - 5]['close']
        d = 1 if move > 0 else -1
        if abs(move) < 1.5 * atr:
            continue
        dsum = sum((B[k].get('delta') or 0.0) for k in range(j - 4, j + 1))
        if dsum * d < Q75:
            continue
        imp_rv = sorted((B[k].get('relVol') or 0.0) for k in range(j - 4, j + 1))[2]
        ext = B[j]['high'] if d > 0 else B[j]['low']
        base = B[j - 5]['close']
        pb_rv, pb_ds = [], 0.0
        entered = False
        for k in range(j + 1, min(j + 21, len(B))):
            if not consec(k, j):
                break
            ck = B[k]
            # invalidation: retrace > 61.8%
            retr = (ext - ck['low']) / max(abs(move), 1e-9) if d > 0 else \
                   (ck['high'] - ext) / max(abs(move), 1e-9)
            if retr > 0.618:
                break
            res = (ck['close'] > ext) if d > 0 else (ck['close'] < ext)
            if res and pb_rv:
                med_rv = sorted(pb_rv)[len(pb_rv) // 2]
                contr = (med_rv <= 0.5 * max(imp_rv, 1e-9)
                         and abs(pb_ds) <= 0.5 * abs(dsum))
                if contr == contracted and R.entry_ok(B, k):
                    ev.append({'j': k, 'd': d, 'tmin': ck['tmin']})
                entered = True
                break
            pb_rv.append(ck.get('relVol') or 0.0)
            dl = ck.get('delta') or 0.0
            if dl * d < 0:
                pb_ds += dl
        if entered:
            continue
    return cool(ev)


# ---------------------------------------------------------------- H5
def h5(B, consec, q99):
    """Returns dict arm -> events. Arms: BAR (control), ACC, REJ."""
    out = {'BAR': [], 'ACC': [], 'REJ': []}
    for j in range(1, len(B) - 6):
        b = B[j]
        dl = b.get('delta')
        if dl is None or abs(dl) < q99:
            continue
        d = 1 if dl > 0 else -1
        if R.entry_ok(B, j):
            out['BAR'].append({'j': j, 'd': d, 'tmin': b['tmin']})
        if not consec(j + 5, j):
            continue
        last = B[j + 5]['close']
        acc = (last > b['high']) if d > 0 else (last < b['low'])
        rej = (last < b['open']) if d > 0 else (last > b['open'])
        k = j + 5
        if acc and R.entry_ok(B, k):
            out['ACC'].append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
        elif rej and R.entry_ok(B, k):
            out['REJ'].append({'j': k, 'd': -d, 'tmin': B[k]['tmin']})
    return {k: cool(v) for k, v in out.items()}


# ---------------------------------------------------------------- H6
def h6(B, consec):
    """Returns (rejectionEvents, acceptanceEvents) at VA edges."""
    rej, acc = [], []
    for j in range(1, len(B) - 6):
        b = B[j]
        if not b.get('profReady'):
            continue
        vah, val = b.get('vah'), b.get('val')
        atr = b['atr']
        if vah is None or val is None or not atr or atr <= 0:
            continue
        prev = B[j - 1]
        for d_edge, edge in ((1, vah), (-1, val)):
            # touch from inside on bar j
            if not prev.get('inVA'):
                continue
            touched = (b['high'] >= edge) if d_edge > 0 else (b['low'] <= edge)
            if not touched:
                continue
            # rejection: within 3 bars a close back inside by >=0.25 ATR
            done = False
            for k in range(j, min(j + 4, len(B))):
                if not consec(k, j):
                    break
                ck = B[k]
                inside = (ck['close'] <= edge - 0.25 * atr) if d_edge > 0 else \
                         (ck['close'] >= edge + 0.25 * atr)
                if inside:
                    if R.entry_ok(B, k):
                        rej.append({'j': k, 'd': -d_edge, 'tmin': ck['tmin']})
                    done = True
                    break
            if not done:
                outs = 0
                for k in range(j, min(j + 6, len(B))):
                    if not consec(k, j):
                        break
                    ck = B[k]
                    o = (ck['close'] > edge) if d_edge > 0 else (ck['close'] < edge)
                    outs = outs + 1 if o else 0
                    if outs >= 3:
                        if R.entry_ok(B, k):
                            acc.append({'j': k, 'd': d_edge, 'tmin': ck['tmin']})
                        break
            break
    return cool(rej), cool(acc)


# ---------------------------------------------------------------- H7 (PROXY)
def h7(B, consec, use_lvn=True):
    """Session volume-at-price via uniform smearing; 25-tick bins.
    PROXY ONLY - labelled as such everywhere."""
    ev = []
    binw = 25 * 0.25
    cur_day = None
    hist = defaultdict(float)
    for j in range(1, len(B) - 1):
        b = B[j]
        if b['day'] != cur_day:
            cur_day = b['day']
            hist = defaultdict(float)
        rng = max(b['high'] - b['low'], 0.25)
        v = b.get('ofVol') or b.get('vol') or 0.0
        b0 = int(b['low'] / binw)
        b1 = int(b['high'] / binw)
        for bin_ in range(b0, b1 + 1):
            hist[bin_] += v / (b1 - b0 + 1)
        if len(hist) < 8:
            continue
        vols = sorted(hist.values())
        med = vols[len(vols) // 2]
        cb = int(b['close'] / binw)
        vol_here = hist.get(cb, 0.0)
        is_lvn = vol_here < 0.25 * med
        if is_lvn != use_lvn:
            continue
        dl = b.get('delta') or 0.0
        if abs(dl) < Q75:
            continue
        d = 1 if dl > 0 else -1
        mv = b['close'] - B[j - 1]['close']
        if mv * d <= 0:
            continue
        if R.entry_ok(B, j):
            ev.append({'j': j, 'd': d, 'tmin': b['tmin']})
    return cool(ev)


# ---------------------------------------------------------------- H8
def h8(B, consec, arm='CONT'):
    """arm: FADE | CONT | MOM (control) | STRUCT (divergence + structure
    failure, fade)"""
    L = pickle.load(open(R.SCR + '/red_levels.pkl', 'rb'))
    lo3 = R.level_lookup(L['lo3'])
    hi3 = R.level_lookup(L['hi3'])
    ev = []
    for j in range(30, len(B)):
        if not consec(j, j - 30):
            continue
        b = B[j]
        atr = b['atr']
        if not atr or atr <= 0:
            continue
        dp = b['close'] - B[j - 30]['close']
        dc = (b.get('cumDelta') or 0.0) - (B[j - 30].get('cumDelta') or 0.0)
        for pd in (1, -1):                     # pd = price direction
            if dp * pd < 1.0 * atr:
                continue
            if arm == 'MOM':
                if dc * pd < CD:
                    continue
                d = pd
            else:
                if dc * pd > -CD:              # cumDelta must OPPOSE price
                    continue
                if arm == 'FADE':
                    d = -pd
                elif arm == 'CONT':
                    d = pd
                else:                          # STRUCT: fade + structure failure
                    lv = (lo3(j) if pd > 0 else hi3(j))
                    if not lv:
                        continue
                    brk = (b['close'] < lv[0][1]) if pd > 0 else (b['close'] > lv[0][1])
                    if not brk:
                        continue
                    d = -pd
            if R.entry_ok(B, j):
                ev.append({'j': j, 'd': d, 'tmin': b['tmin']})
            break
    return cool(ev)
