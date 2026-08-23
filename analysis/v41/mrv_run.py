#!/usr/bin/env python3
# ======================================================================
# MRV-V1  MR-H1..H8, V-H1..V-H2  (V-H3..V-H10: NOT SPECIFIED, truncated)
# ======================================================================
# Rules exactly as docs/MRV_PREREGISTRATION.md (committed first).
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, pickle
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import red_lib as R

Q75 = R.Q_BD75
E2_CUT = 15.9608
CD = 586.0
COOL = 30


def load():
    B = pickle.load(open(R.SCR + '/red_bars.pkl', 'rb'))
    S = pickle.load(open(R.SCR + '/mrv_sess.pkl', 'rb'))
    FR = pickle.load(open(R.SCR + '/mrv_frozen.pkl', 'rb'))
    return B, S, FR


def cool(evs):
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x['j']):
        if e['tmin'] - last < COOL:
            continue
        last = e['tmin']
        out.append(e)
    return out


def er(B, k, d, medabs):
    """opposing effort/result/failure on bar k for trade direction d."""
    b = B[k]
    atr, ms, dl = b['atr'], medabs[k], b.get('delta')
    if not atr or not ms or dl is None:
        return None
    if d > 0:
        if dl >= 0:
            return None
        eff = -dl / ms
        t = b.get('dnTicks')
    else:
        if dl <= 0:
            return None
        eff = dl / ms
        t = b.get('upTicks')
    if t is None:
        return None
    res = t * 0.25 / atr
    return eff, res, eff / max(res, 1e-6)


def confirm(B, consec, j0, d, win=10):
    """First completed close beyond the prior bar's extreme, within win."""
    for k in range(j0 + 1, min(j0 + 1 + win, len(B))):
        if not consec(k, j0):
            return None
        c, p = B[k], B[k - 1]
        if (d > 0 and c['close'] > p['high']) or (d < 0 and c['close'] < p['low']):
            return k
    return None


# ---------------------------------------------------------------- MR-H1
def mr_h1(B, consec, S, FR, medabs, arm='FULL', level='LARGE'):
    vwap = S['vwap']
    cut = FR['VEXT75'] if level == 'LARGE' else FR['VEXT90']
    ev = []
    j = 1
    while j < len(B):
        b = B[j]
        v = vwap[j - 1]
        atr = b['atr']
        if v is None or not atr:
            j += 1
            continue
        d = 1 if b['close'] < v else -1
        if abs(b['close'] - v) / atr < cut:
            j += 1
            continue
        if arm in ('ATTACK', 'FAIL', 'FULL'):
            dl = b.get('delta') or 0
            if dl * d > -Q75:
                j += 1
                continue
        if arm in ('FAIL', 'FULL'):
            e = er(B, j, d, medabs)
            if e is None or e[2] < E2_CUT:
                j += 1
                continue
        if arm == 'EXT':
            k = j
        else:
            k = confirm(B, consec, j, d)
            if k is None:
                j += 1
                continue
        if R.entry_ok(B, k):
            ev.append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
        j += 1
    return cool(ev)


# ---------------------------------------------------------------- MR-H2
def mr_h2(B, consec, S):
    slo, shi = S['slo'], S['shi']
    ev = []
    for j in range(31, len(B) - 6):
        b = B[j]
        if (b.get('mfo') or -1) < 30:
            continue
        for d, ext in ((1, slo[j - 1]), (-1, shi[j - 1])):
            if ext is None:
                continue
            out = (b['low'] < ext and b['close'] < ext) if d > 0 else \
                  (b['high'] > ext and b['close'] > ext)
            if not out:
                continue
            outs = 0
            for k in range(j + 1, min(j + 6, len(B))):
                if not consec(k, j):
                    break
                c = B[k]
                o = (c['close'] < ext) if d > 0 else (c['close'] > ext)
                outs = outs + 1 if o else 0
                if outs >= 3:
                    break
                back = (c['close'] > ext) if d > 0 else (c['close'] < ext)
                if back:
                    if R.entry_ok(B, k):
                        ev.append({'j': k, 'd': d, 'tmin': c['tmin']})
                    break
            break
    return cool(ev)


# ---------------------------------------------------------------- MR-H3
def mr_h3(B, consec, medabs, lo_at, hi_at, arm='FULL'):
    ev = []
    for j in range(1, len(B) - 6):
        b = B[j]
        for d in (1, -1):
            lv = (lo_at(j) if d > 0 else hi_at(j))
            swept = None
            for _, px in lv:
                if d > 0 and b['low'] < px:
                    swept = px
                    break
                if d < 0 and b['high'] > px:
                    swept = px
                    break
            if swept is None:
                continue
            if arm != 'SWEEP' and (b.get('relVol') or 0) < 2.0:
                continue
            if arm == 'SWEEP' or arm == 'VOL':
                if R.entry_ok(B, j):
                    ev.append({'j': j, 'd': d, 'tmin': b['tmin']})
                break
            done = False
            failed = False
            for k in range(j, min(j + 6, len(B))):
                if k > j and not consec(k, j):
                    break
                c = B[k]
                below = (c['close'] < swept) if d > 0 else (c['close'] > swept)
                if below and arm in ('FAILCONT', 'FULL'):
                    e = er(B, k, d, medabs)
                    if e is not None and e[2] >= E2_CUT:
                        failed = True
                back = (c['close'] > swept) if d > 0 else (c['close'] < swept)
                if k > j and back:
                    if arm in ('FAILCONT', 'FULL') and not failed:
                        done = True
                        break
                    if R.entry_ok(B, k):
                        ev.append({'j': k, 'd': d, 'tmin': c['tmin']})
                    done = True
                    break
            if done:
                break
    return cool(ev)


# ---------------------------------------------------------------- MR-H4
def mr_h4(B, consec, FR, medabs, arm='FULL'):
    ev = []
    for j in range(30, len(B)):
        if not consec(j, j - 30):
            continue
        b = B[j]
        atr = b['atr']
        if not atr:
            continue
        mv = (b['close'] - B[j - 30]['close']) / atr
        d = 1 if mv < 0 else -1
        if abs(mv) < FR['MOV90']:
            continue
        if arm == 'EXT':
            k = confirm(B, consec, j, d)
            if k and R.entry_ok(B, k):
                ev.append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
            continue
        # last three opposing attack bars in the 30-bar window
        atk = []
        for k in range(j - 29, j + 1):
            e = er(B, k, d, medabs)
            dl = B[k].get('delta') or 0
            if e is not None and dl * d < -Q75:
                atk.append(e)
        if len(atk) < 3:
            continue
        e1, e2_, e3 = atk[-3], atk[-2], atk[-1]
        det = e1[1] > e2_[1] > e3[1]
        eff = e3[0] >= 0.9 * e1[0]
        if arm == 'RESULT' and not det:
            continue
        if arm == 'EFFORT' and not eff:
            continue
        if arm == 'FULL' and not (det and eff):
            continue
        k = confirm(B, consec, j, d)
        if k and R.entry_ok(B, k):
            ev.append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
    return cool(ev)


# ---------------------------------------------------------------- MR-H5
def mr_h5(B, consec, FR):
    """Returns dict: BAR (climax itself), REJ (fade on rejection)."""
    out = {'BAR': [], 'REJ': [], 'CONT': []}
    for j in range(1, len(B) - 6):
        b = B[j]
        rv = b.get('relVol') or 0
        dl = b.get('delta') or 0
        if rv < FR['RV99'] or abs(dl) < Q75:
            continue
        d = 1 if dl > 0 else -1              # climax direction
        if R.entry_ok(B, j):
            out['BAR'].append({'j': j, 'd': d, 'tmin': b['tmin']})
        mid = (b['high'] + b['low']) / 2.0
        for k in range(j + 1, min(j + 6, len(B))):
            if not consec(k, j):
                break
            c = B[k]
            rej = (c['close'] < mid) if d > 0 else (c['close'] > mid)
            ext = (c['close'] > b['high']) if d > 0 else (c['close'] < b['low'])
            if rej:
                if R.entry_ok(B, k):
                    out['REJ'].append({'j': k, 'd': -d, 'tmin': c['tmin']})
                break
            if ext:
                if R.entry_ok(B, k):
                    out['CONT'].append({'j': k, 'd': d, 'tmin': c['tmin']})
                break
    return {k: cool(v) for k, v in out.items()}


# ---------------------------------------------------------------- MR-H6
def mr_h6(B, consec, arm='FULL'):
    ev = []
    for j in range(1, len(B) - 6):
        b = B[j]
        if not b.get('profReady'):
            continue
        vah, val = b.get('vah'), b.get('val')
        if vah is None or val is None:
            continue
        for d, edge in ((1, val), (-1, vah)):
            out = (b['close'] < edge) if d > 0 else (b['close'] > edge)
            if not out:
                continue
            if arm == 'TOUCH':
                if R.entry_ok(B, j):
                    ev.append({'j': j, 'd': d, 'tmin': b['tmin']})
                break
            volout = (b.get('relVol') or 0) >= 2.0
            outs = 0
            for k in range(j + 1, min(j + 6, len(B))):
                if not consec(k, j):
                    break
                c = B[k]
                if (c.get('relVol') or 0) >= 2.0:
                    volout = True
                o = (c['close'] < edge) if d > 0 else (c['close'] > edge)
                outs = outs + 1 if o else 0
                if outs >= 3:
                    break
                back = (c['close'] > edge) if d > 0 else (c['close'] < edge)
                if back:
                    if arm == 'FULL' and not volout:
                        break
                    if R.entry_ok(B, k):
                        ev.append({'j': k, 'd': d, 'tmin': c['tmin']})
                    break
            break
    return cool(ev)


# ---------------------------------------------------------------- MR-H7
def mr_h7(B, consec, FR, fast=True):
    ev = []
    for j in range(10, len(B) - 6):
        if not consec(j, j - 10):
            continue
        b = B[j]
        atr = b['atr']
        if not atr:
            continue
        best = None
        for k in (3, 5, 10):
            dist = (b['close'] - B[j - k]['close']) / atr
            if abs(dist) >= 2.0:
                sp = abs(dist) / k
                if best is None or sp > best[0]:
                    best = (sp, 1 if dist < 0 else -1, abs(dist))
        if best is None:
            continue
        sp, d, dist = best
        if fast and sp < FR['SPD90']:
            continue
        if not fast and sp >= FR['SPD50']:
            continue
        # rejection within 5 bars: retrace >= 38.2%
        for k in range(j + 1, min(j + 6, len(B))):
            if not consec(k, j):
                break
            c = B[k]
            retr = (c['close'] - b['close']) * d / (dist * atr)
            if retr >= 0.382:
                kk = confirm(B, consec, k, d)
                if kk and R.entry_ok(B, kk):
                    ev.append({'j': kk, 'd': d, 'tmin': B[kk]['tmin']})
                break
    return cool(ev)


# ---------------------------------------------------------------- MR-H8
def mr_h8(B, consec, medabs, arm='FULL'):
    """arm: WEAK (weak-effort 2nd) | HELR (high-effort low-result) |
    CONT (efficient continuation control)"""
    ev = []
    for j in range(30, len(B) - 31):
        b = B[j]
        atr = b['atr']
        if not atr:
            continue
        for d in (1, -1):
            dl = b.get('delta') or 0
            if dl * d > -Q75:
                continue
            ext1 = b['low'] if d > 0 else b['high']
            is_ext = all((B[k]['low'] > ext1 if d > 0 else B[k]['high'] < ext1)
                         for k in range(j - 30, j))
            if not is_ext:
                continue
            e1 = er(B, j, d, medabs)
            if e1 is None:
                continue
            bounced = False
            done = False
            for k in range(j + 1, min(j + 31, len(B))):
                if not consec(k, j):
                    break
                c = B[k]
                if not bounced:
                    bd = (c['close'] - ext1) * d
                    if bd >= 0.5 * atr:
                        bounced = True
                    continue
                near = (c['low'] <= ext1 + 0.1 * atr) if d > 0 else \
                       (c['high'] >= ext1 - 0.1 * atr)
                if not near:
                    continue
                beyond = (ext1 - c['low']) if d > 0 else (c['high'] - ext1)
                if arm == 'CONT':
                    if beyond <= 0.5 * atr:
                        break
                else:
                    if beyond > 0.25 * atr:
                        break
                e2_ = er(B, k, d, medabs)
                if e2_ is None:
                    break
                if arm == 'WEAK' and not (e2_[0] <= 0.75 * e1[0]):
                    break
                if arm == 'HELR' and not (e2_[0] >= 0.9 * e1[0] and e2_[2] >= E2_CUT):
                    break
                kk = confirm(B, consec, k, d)
                if kk and R.entry_ok(B, kk):
                    ev.append({'j': kk, 'd': d, 'tmin': B[kk]['tmin']})
                done = True
                break
            if done:
                break
    return cool(ev)


# ---------------------------------------------------------------- V-H1/V-H2
def flushes(B, consec):
    out = []
    for j in range(5, len(B)):
        if not consec(j, j - 5):
            continue
        atr = B[j]['atr']
        if not atr:
            continue
        for n in (2, 3, 4, 5):
            mv = B[j]['close'] - B[j - n]['close']
            d = 1 if mv < 0 else -1          # d = recovery direction
            if abs(mv) < 1.5 * atr:
                continue
            if max((B[k].get('relVol') or 0) for k in range(j - n + 1, j + 1)) < 2.0:
                continue
            out.append({'j': j, 'n': n, 'd': d, 'dist': abs(mv), 'atr': atr,
                        'start': j - n})
            break
    return out


def v_h1(B, consec, mode='FAST'):
    ev = []
    for f in flushes(B, consec):
        j, d, dist = f['j'], f['d'], f['dist']
        ext = B[j]['low'] if d > 0 else B[j]['high']
        base = B[f['start']]['close']
        win = 3 if mode == 'FAST' else 10
        lo_k = 1 if mode == 'FAST' else 4
        for k in range(j + 1, min(j + 1 + win, len(B))):
            if not consec(k, j):
                break
            c = B[k]
            rec = (c['close'] - ext) * d / dist
            if rec >= 0.5:
                if mode == 'SLOW' and k - j < lo_k:
                    break
                if R.entry_ok(B, k):
                    ev.append({'j': k, 'd': d, 'tmin': c['tmin'],
                               'start': f['start']})
                break
    return cool(ev)


def v_h2(B, consec, persistent=True):
    ev = []
    for f in flushes(B, consec):
        j, d, dist = f['j'], f['d'], f['dist']
        ext = B[j]['low'] if d > 0 else B[j]['high']
        for k in range(j + 1, min(j + 4, len(B))):
            if not consec(k, j):
                break
            c = B[k]
            rec = (c['close'] - ext) * d / dist
            if rec >= 0.5:
                cd0 = B[f['start']].get('cumDelta')
                cd1 = c.get('cumDelta')
                if cd0 is None or cd1 is None:
                    break
                dcd = (cd1 - cd0) * d
                opp = dcd <= -CD
                if opp == persistent and R.entry_ok(B, k):
                    ev.append({'j': k, 'd': d, 'tmin': c['tmin']})
                break
    return cool(ev)
