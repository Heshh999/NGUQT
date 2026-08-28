#!/usr/bin/env python3
# ======================================================================
# VTBS-V1  -  FROZEN ENGINE  (committed before any outcome is displayed)
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))

DEV_LAST = '2026-08-17'
COST_BASE = 0.87
COST_STRESS = 1.305
SEED_BOOT, SEED_PERM, SEED_STATE = 20260901, 20260902, 20260903
B_BOOT = P_PERM = N_STATE = 10000


def q7(v, q):
    return float(np.quantile(np.asarray(v, float), q, method='linear'))


def load_days():
    """Calendar-day bar lists (mm, o, h, l, c) from the canonical grid."""
    import rvmr_run as RV
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    byday = collections.defaultdict(list)
    for i in range(len(D['c'])):
        et = D['et'][i]
        if et[:10] > DEV_LAST:
            continue
        mm = int(et[11:13]) * 60 + int(et[14:16])
        byday[et[:10]].append((mm, D['o'][i], D['h'][i], D['l'][i], D['c'][i]))
    return sorted(byday), dict(byday)


def day_state(days, byday, leak=False):
    """Per-day causal predictor state. leak=True (leak test only)
    extends the overnight window into the RTH open and MUST be caught."""
    rr, on = {}, {}
    hi = 569 if not leak else 601
    for k, d in enumerate(days):
        rth = [b for b in byday[d] if 571 <= b[0] <= 960]
        if len(rth) >= 300:
            rr[d] = max(b[2] for b in rth) - min(b[3] for b in rth)
        if k == 0:
            continue
        same_day = [b for b in byday[d] if 0 < b[0] <= hi]
        w = [b for b in byday[days[k - 1]] if b[0] >= 1081] + same_day
        # causality guard: no same-day bar at/after the 09:31 entry stamp
        # may enter the predictor window (the deliberate leak test trips it)
        if any(b[0] >= 571 for b in same_day):
            raise AssertionError('LEAK: overnight window reaches RTH')
        if len(w) >= 200:
            on[d] = max(b[2] for b in w) - min(b[3] for b in w)
    P, out = {}, {}
    for k, d in enumerate(days):
        prior_rr = [rr[e] for e in days[max(0, k - 60):k] if e in rr]
        entry = next((b for b in byday[d] if b[0] == 571), None)
        if len(prior_rr) < 40 or d not in on or d not in rr or entry is None:
            continue
        base = q7(prior_rr, 0.5)
        p = on[d] / base
        prior_P = [P[e] for e in days[max(0, k - 60):k] if e in P]
        P[d] = p
        if len(prior_P) < 40:
            continue
        out[d] = dict(base=base, p=p, thr=q7(prior_P, 0.75),
                      thr70=q7(prior_P, 0.70), thr80=q7(prior_P, 0.80),
                      lo=q7(prior_P, 0.25), open=entry[1])
    return out


def bracket(bars, O, w_up, w_dn, exit_mm, entry_shift=0):
    """One day's bracket. Returns (gross, side, kind) or None if no
    trigger by 15:00. Frozen semantics per VTBS_V1_PROTOCOL.md."""
    rth = [b for b in bars if 571 <= b[0] <= 960]
    trig = None
    for i, b in enumerate(rth):
        if b[0] > 900:
            break
        up_t, dn_t = b[2] >= w_up, b[3] <= w_dn
        if up_t and dn_t:
            return -(w_up - w_dn), 0, 'WHIPSAW'
        if up_t or dn_t:
            trig = (i, 1 if up_t else -1)
            break
    if trig is None:
        return None
    i0, side = trig
    i0 += entry_shift
    if i0 >= len(rth):
        return None
    b0 = rth[i0]
    if entry_shift == 0:
        ep = max(w_up, b0[1]) if side > 0 else min(w_dn, b0[1])
    else:
        ep = b0[1]
    sp = w_dn if side > 0 else w_up
    jx = next((j for j in range(i0 + 1, len(rth)) if rth[j][0] >= exit_mm),
              None)
    end = jx if jx is not None else len(rth)
    for j in range(i0, end):
        b = rth[j]
        if (side > 0 and b[3] <= sp) or (side < 0 and b[2] >= sp):
            fill = min(sp, b[1]) if side > 0 else max(sp, b[1])
            return side * (fill - ep), side, 'STOP'
    if jx is not None:
        return side * (rth[jx][1] - ep), side, 'TIME'
    return side * (rth[-1][4] - ep), side, 'DAYLAST'


def build(days, byday, st, k, exit_mm, sel='HIGH', entry_shift=0,
          band_scale=1.0, thr_key='thr'):
    ev = []
    for d in days:
        s = st.get(d)
        if s is None:
            continue
        if sel == 'HIGH' and not s['p'] >= s[thr_key]:
            continue
        if sel == 'LOW' and not s['p'] <= s['lo']:
            continue
        w = k * band_scale * s['base']
        r = bracket(byday[d], s['open'], s['open'] + w, s['open'] - w,
                    exit_mm, entry_shift)
        if r is None:
            ev.append(dict(day=d, gross=None, side=0, kind='NOTRIG', R=2 * w))
            continue
        g, side, kind = r
        ev.append(dict(day=d, gross=g, side=side, kind=kind, R=2 * w))
    return ev


def stats_cell(ev):
    tr = [e for e in ev if e['gross'] is not None]
    g = np.array([e['gross'] for e in tr])
    R = np.array([e['R'] for e in tr])
    base, stx = g - COST_BASE, g - COST_STRESS
    out = dict(n=len(tr), days=len(tr), notrig=len(ev) - len(tr),
               gross=float(g.mean()), base=float(base.mean()),
               stressed=float(stx.mean()),
               base_R=float((base / R).mean()),
               stressed_R=float((stx / R).mean()),
               win_base=float((base > 0).mean()),
               pf_base=_pf(base), pf_stressed=_pf(stx),
               payoff_stressed=_payoff(stx))
    rng = np.random.default_rng(SEED_BOOT)
    m = np.empty(B_BOOT)
    for b in range(B_BOOT):
        m[b] = stx[rng.integers(0, len(tr), len(tr))].mean()
    out['ci_lo'], out['ci_hi'] = (float(np.percentile(m, 2.5)),
                                  float(np.percentile(m, 97.5)))
    rng = np.random.default_rng(SEED_PERM)
    obs = g.mean()
    cnt = 0
    for p in range(P_PERM):
        fl = rng.choice([-1.0, 1.0], len(tr))
        if (g * fl).mean() >= obs:
            cnt += 1
    out['perm_p'] = (cnt + 1) / (P_PERM + 1)
    return out


def _pf(x):
    lo = -x[x < 0].sum()
    return float(x[x > 0].sum() / lo) if lo > 0 else float('inf')


def _payoff(x):
    w, l = x[x > 0], x[x < 0]
    return float(w.mean() / -l.mean()) if len(w) and len(l) else float('nan')


def bh(ps):
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, ps[i] * m / rank)
        q[i] = prev
    return q
