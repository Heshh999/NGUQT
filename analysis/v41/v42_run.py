#!/usr/bin/env python3
# ======================================================================
# V4.2 FVG + ORDER-FLOW FAILURE FAMILY - implementation
# ======================================================================
# Rules exactly as docs/V42_PREREGISTRATION.md (committed first).
# Canonical machinery (build_fvg, _mitigate semantics, Q_BD75, entry
# gate) is IMPORTED from cand_spec, never re-derived. The mirror walker
# used where the aggression-bar index is needed is asserted equal to
# canonical _mitigate on the full FVG population.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, pickle
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS
import red_lib as R

E2_CUT = 15.9608          # frozen in the RED phase (DEV q75), reused
LIFE30 = 30               # formation+30 primary FVG life
LIFE120 = 120             # observation life for freshness / iFVG / G4-FVG
REEXP_WIN = 10            # bars from touch to continuation trigger (frozen)
SWEEP_WIN = 10            # sweep -> FVG formation window (F3)
G4_SWEEP_WIN = 15         # sweep -> G4 entry window
COOLDOWN = 30


def load():
    B = pickle.load(open(R.SCR + '/red_bars.pkl', 'rb'))
    for b in B:                                   # canonical field alias
        b['ofBarDelta'] = b.get('delta')
    return B


def cooldown(evs):
    out, last = [], -10 ** 9
    for e in sorted(evs, key=lambda x: x['j']):
        if e['tmin'] - last < COOLDOWN:
            continue
        last = e['tmin']
        out.append(e)
    return out


# ---------------------------------------------------------------- walker
def walk_mit(B, f, start_j, expire_tmin):
    """Mirror of canonical _mitigate that ALSO reports the first
    opposing-aggression bar. Same invalidation / touch / trigger."""
    N = len(B)
    d, zLo, zHi, mid = f['d'], f['zLo'], f['zHi'], f['mid']
    touched = False
    ext = None
    flow_ok = False
    agg_j = None
    prev = None
    for k in range(start_j, N):
        if prev is not None and B[k]['tmin'] != prev + 1:
            return None
        prev = B[k]['tmin']
        if B[k]['tmin'] > expire_tmin:
            return None
        c = B[k]
        if (d > 0 and c['close'] < zLo) or (d < 0 and c['close'] > zHi):
            return None
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
        if bd is not None and abs(bd) >= CS.Q_BD75 and bd * d < 0:
            flow_ok = True
            if agg_j is None:
                agg_j = k
        if (d > 0 and c['close'] > mid) or (d < 0 and c['close'] < mid):
            return {'j': k, 'flow': flow_ok, 'agg_j': agg_j, 'ext': ext,
                    'touch': True}
    return None


def assert_walker(B, fvgs_at):
    n = bad = 0
    for j, lst in fvgs_at.items():
        for f in lst:
            exp = B[j]['tmin'] + LIFE30
            a = CS._mitigate(B, f, j + 1, exp)
            b = walk_mit(B, f, j + 1, exp)
            n += 1
            if (a is None) != (b is None):
                bad += 1
            elif a is not None and (a['j'] != b['j'] or a['flow'] != b['flow']):
                bad += 1
    return n, bad


def fail_ok(B, medabs, agg_j, d):
    """Frozen E2 failure test on the first aggression bar (opposing side)."""
    if agg_j is None:
        return False
    r = R.effort_result(B, agg_j, -d, medabs, 'E2')
    return r is not None and r[2] >= E2_CUT


# ---------------------------------------------------------------- F1
def f1(B, fvgs_at, medabs, arm='FULL'):
    ev = []
    for j in sorted(fvgs_at):
        for f in fvgs_at[j]:
            m = walk_mit(B, f, j + 1, B[j]['tmin'] + LIFE30)
            if m is None or not R.entry_ok(B, m['j']):
                continue
            if arm in ('B', 'FULL') and not m['flow']:
                continue
            if arm == 'FULL' and not fail_ok(B, medabs, m['agg_j'], f['d']):
                continue
            ev.append({'j': m['j'], 'd': f['d'], 'tmin': B[m['j']]['tmin'],
                       'fvg_j': j, 'zLo': f['zLo'], 'zHi': f['zHi'],
                       'atr0': f['atr']})
    return cooldown(ev)


# ---------------------------------------------------------------- F2
def episodes(B, f, start_j, expire_tmin, max_ep=6):
    """Causal touch episodes; far-side close kills the zone."""
    N = len(B)
    d, zLo, zHi, mid = f['d'], f['zLo'], f['zHi'], f['mid']
    prev = None
    inside = False
    eps = []
    cur = None
    for k in range(start_j, N):
        if prev is not None and B[k]['tmin'] != prev + 1:
            break
        prev = B[k]['tmin']
        if B[k]['tmin'] > expire_tmin:
            break
        c = B[k]
        if (d > 0 and c['close'] < zLo) or (d < 0 and c['close'] > zHi):
            break
        touch = (c['low'] <= zHi) if d > 0 else (c['high'] >= zLo)
        if touch and not inside:
            inside = True
            cur = {'touch_j': k, 'agg_j': None, 'trig_j': None}
        if inside:
            bd = c['ofBarDelta']
            if bd is not None and abs(bd) >= CS.Q_BD75 and bd * d < 0 \
                    and cur['agg_j'] is None:
                cur['agg_j'] = k
            trig = (c['close'] > mid) if d > 0 else (c['close'] < mid)
            if trig:
                cur['trig_j'] = k
                eps.append(cur)
                inside = False
                cur = None
                if len(eps) >= max_ep:
                    break
                continue
        if inside and not touch:
            outside = (c['low'] > zHi) if d > 0 else (c['high'] < zLo)
            if outside:
                eps.append(cur)
                inside = False
                cur = None
                if len(eps) >= max_ep:
                    break
    return eps


def f2(B, fvgs_at, medabs):
    """FULL-F1 logic per touch episode; returns events tagged ep=1,2,3+."""
    ev = []
    for j in sorted(fvgs_at):
        for f in fvgs_at[j]:
            for i, ep in enumerate(episodes(B, f, j + 1, B[j]['tmin'] + LIFE120)):
                if ep['trig_j'] is None or ep['agg_j'] is None:
                    continue
                if not fail_ok(B, medabs, ep['agg_j'], f['d']):
                    continue
                k = ep['trig_j']
                if not R.entry_ok(B, k):
                    continue
                ev.append({'j': k, 'd': f['d'], 'tmin': B[k]['tmin'],
                           'ep': min(i + 1, 3)})
    byep = defaultdict(list)
    for e in cooldown(ev):
        byep[e['ep']].append(e)
    return byep


# ---------------------------------------------------------------- F3
def f3(B, fvgs_at, medabs, lo_at, hi_at, arm='FULL'):
    """arm: SWEEP_ONLY | SWEEP_FVG | FULL   (F1-FULL is the no-sweep ctl)"""
    # sweep bars: low under a causally-known 3m swing low
    ev = []
    fj_sorted = sorted(fvgs_at)
    for j, b in enumerate(B):
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
            if arm == 'SWEEP_ONLY':
                # first close back beyond the swept level within 10 bars
                for k in range(j + 1, min(j + 1 + SWEEP_WIN, len(B))):
                    if B[k]['tmin'] - B[j]['tmin'] != k - j:
                        break
                    if (d > 0 and B[k]['close'] > swept) or \
                       (d < 0 and B[k]['close'] < swept):
                        if R.entry_ok(B, k):
                            ev.append({'j': k, 'd': d, 'tmin': B[k]['tmin']})
                        break
                continue
            # FVG of direction d forming within SWEEP_WIN bars after j
            for fj in range(j + 1, min(j + 1 + SWEEP_WIN, len(B))):
                if fj not in fvgs_at:
                    continue
                for f in fvgs_at[fj]:
                    if f['d'] != d:
                        continue
                    m = walk_mit(B, f, fj + 1, B[fj]['tmin'] + LIFE30)
                    if m is None or not R.entry_ok(B, m['j']):
                        continue
                    if arm == 'FULL':
                        if not m['flow'] or not fail_ok(B, medabs, m['agg_j'], d):
                            continue
                    ev.append({'j': m['j'], 'd': d, 'tmin': B[m['j']]['tmin']})
    return cooldown(ev)


# ---------------------------------------------------------------- F4
def f4(B, fvgs_at, medabs, arm='FULL'):
    """iFVG: bearish FVG converted by a close above its top (mirror for
    shorts). arm: RETEST | RETEST_AGG | FULL"""
    ev = []
    for j in sorted(fvgs_at):
        for f in fvgs_at[j]:
            d0 = f['d']
            d = -d0                     # inverse direction
            zLo, zHi = f['zLo'], f['zHi']
            conv = None
            prev = None
            for k in range(j + 1, min(j + 1 + LIFE120, len(B))):
                if prev is not None and B[k]['tmin'] != prev + 1:
                    break
                prev = B[k]['tmin']
                if d0 > 0 and B[k]['close'] < zLo:
                    conv = k
                    break
                if d0 < 0 and B[k]['close'] > zHi:
                    conv = k
                    break
            if conv is None:
                continue
            g = {'d': d, 'zLo': zLo, 'zHi': zHi, 'mid': (zLo + zHi) / 2.0,
                 'atr': f['atr']}
            m = walk_mit(B, g, conv + 1, B[conv]['tmin'] + LIFE30)
            if m is None or not R.entry_ok(B, m['j']):
                continue
            if arm in ('RETEST_AGG', 'FULL') and not m['flow']:
                continue
            if arm == 'FULL' and not fail_ok(B, medabs, m['agg_j'], d):
                continue
            ev.append({'j': m['j'], 'd': d, 'tmin': B[m['j']]['tmin']})
    return cooldown(ev)


# ---------------------------------------------------------------- G4-FVG / G4-SWEEP
def active_fvg(B, fvgs_at, j, d, life=LIFE120):
    """Is bar j touching a live same-direction FVG zone?"""
    t = B[j]['tmin']
    for fj in range(max(0, j - life), j):
        if fj not in fvgs_at:
            continue
        for f in fvgs_at[fj]:
            if f['d'] != d or t - B[fj]['tmin'] > life:
                continue
            # far-side invalidation before j?
            dead = False
            for k in range(fj + 1, j):
                if (d > 0 and B[k]['close'] < f['zLo']) or \
                   (d < 0 and B[k]['close'] > f['zHi']):
                    dead = True
                    break
            if dead:
                continue
            b = B[j]
            if (d > 0 and b['low'] <= f['zHi']) or (d < 0 and b['high'] >= f['zLo']):
                return True
    return False


def swept_recent(B, j, d, lo_at, hi_at, win=G4_SWEEP_WIN):
    for k in range(max(0, j - win), j + 1):
        lv = (lo_at(k) if d > 0 else hi_at(k))
        for _, px in lv:
            if d > 0 and B[k]['low'] < px:
                return True
            if d < 0 and B[k]['high'] > px:
                return True
    return False


# ---------------------------------------------------------------- WEAK-PB
def weak_pb(B, fvgs_at, arm='FULL'):
    """arm: ANY | FULL(weak) | STRONG"""
    ev = []
    for j in sorted(fvgs_at):
        for f in fvgs_at[j]:
            d = f['d']
            imp = sum((B[k].get('ofBarDelta') or 0.0) for k in (j - 2, j - 1, j))
            if d > 0 and imp < CS.Q_BD75:
                continue
            if d < 0 and imp > -CS.Q_BD75:
                continue
            eps = episodes(B, f, j + 1, B[j]['tmin'] + LIFE120, max_ep=1)
            if not eps:
                continue
            tj = eps[0]['touch_j']
            pb = abs(B[tj].get('ofBarDelta') or 0.0)
            weak = pb <= 0.5 * abs(imp)
            if arm == 'FULL' and not weak:
                continue
            if arm == 'STRONG' and weak:
                continue
            # continuation trigger: close beyond zone extreme within REEXP_WIN
            for k in range(tj, min(tj + REEXP_WIN + 1, len(B))):
                if B[k]['tmin'] - B[tj]['tmin'] != k - tj:
                    break
                c = B[k]
                if (d > 0 and c['close'] < f['zLo']) or (d < 0 and c['close'] > f['zHi']):
                    break
                trig = (c['close'] > f['zHi']) if d > 0 else (c['close'] < f['zLo'])
                if trig:
                    if R.entry_ok(B, k):
                        ev.append({'j': k, 'd': d, 'tmin': c['tmin']})
                    break
    return cooldown(ev)


# ---------------------------------------------------------------- ER buckets
def er_events(B, fvgs_at, medabs):
    """F1-B events with their E2 score attached (no cut)."""
    ev = []
    for j in sorted(fvgs_at):
        for f in fvgs_at[j]:
            m = walk_mit(B, f, j + 1, B[j]['tmin'] + LIFE30)
            if m is None or not m['flow'] or m['agg_j'] is None:
                continue
            if not R.entry_ok(B, m['j']):
                continue
            r = R.effort_result(B, m['agg_j'], -f['d'], medabs, 'E2')
            if r is None:
                continue
            b = B[m['agg_j']]
            raw = abs(b['ofBarDelta']) / medabs[m['agg_j']] \
                if medabs[m['agg_j']] else None
            ev.append({'j': m['j'], 'd': f['d'], 'tmin': B[m['j']]['tmin'],
                       'e2': r[2], 'raw': raw})
    return cooldown(ev)
