#!/usr/bin/env python3
# ======================================================================
# MOFAD-V1  -  FROZEN ENGINE
# Implements exactly the five confirmatory candidates of
# MOFAD_V1_PROTOCOL_FREEZE.md. Committed BEFORE any outcome is displayed.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))

DEV_LAST = '2026-08-17'
COST_BASE = 0.87
COST_STRESS = 1.305
SEED_BOOT, SEED_PERM, SEED_CTRL = 20260828, 20260829, 20260830
B_BOOT, P_PERM, N_CTRL = 10000, 10000, 2000


def load_dev():
    """DEV order-flow bars grouped by calendar day, plus stamp index."""
    from cand_spec import load_merged
    B = [b for b in load_merged() if b['day'] <= DEV_LAST]
    for b in B:
        b['mm'] = int(b['et'][11:13]) * 60 + int(b['et'][14:16])
    byday = collections.defaultdict(list)
    for b in B:
        byday[b['day']].append(b)
    for d in byday:
        byday[d].sort(key=lambda b: b['mm'])
    return sorted(byday), dict(byday)


def q7(vals, q):
    """Type-7 (numpy linear) quantile."""
    return float(np.quantile(np.asarray(vals, float), q, method='linear'))


# ---------------------------------------------------------------------
# race: entry at open of bars[j0]; stop race bars j0..jx-1; exit at
# open of bars[jx]. Stop-market, gap-through at worse of stop level and
# bar open. Returns (gross_pts, exit_kind).
# ---------------------------------------------------------------------
def race(bars, j0, jx, d, stop_dist):
    ep = bars[j0]['open']
    sp = ep - d * stop_dist
    for k in range(j0, jx):
        b = bars[k]
        if (d > 0 and b['low'] <= sp) or (d < 0 and b['high'] >= sp):
            fill = min(sp, b['open']) if d > 0 else max(sp, b['open'])
            return d * (fill - ep), 'STOP'
    return d * (bars[jx]['open'] - ep), 'TIME'


def _exit_index(bars, j0, exit_mm):
    """First bar at/after exit_mm strictly after j0; else day-last close."""
    for k in range(j0 + 1, len(bars)):
        if bars[k]['mm'] >= exit_mm:
            return k, 'OPEN'
    return None, 'DAYLAST'


def _atr_before(bars, mm_entry):
    prior = [b for b in bars if b['mm'] < mm_entry and b['atr']]
    return prior[-1]['atr'] if prior else None


def _flow_ratio(win):
    vol = sum(b['ofTotalVolume'] or 0 for b in win)
    if vol <= 0:
        return None
    return sum(b['ofBarDelta'] or 0 for b in win) / vol


# ---------------------------------------------------------------------
# F12 event builders
# ---------------------------------------------------------------------
def build_f12(days, byday, cand, leak=False):
    """cand in {'C-F12-1','C-F12-1b','C-F12-2'}.  leak=True is used ONLY
    by the deliberate leakage test: it extends the signal window past the
    frozen causal close and MUST be caught by the assertion below."""
    H = {'C-F12-1': 30, 'C-F12-1b': 60, 'C-F12-2': 30}[cand]
    ev = []
    for k, d in enumerate(days):
        if k == 0:
            continue
        bars = byday[d]
        if cand in ('C-F12-1', 'C-F12-1b'):
            prev = byday[days[k - 1]]
            hi = 540 if not leak else 571
            win = ([b for b in prev if b['mm'] > 1080]
                   + [b for b in bars if 0 < b['mm'] <= hi])
            need = 300
        else:
            hi = 569 if not leak else 571
            win = [b for b in bars if 480 < b['mm'] <= hi]
            need = 60
        # frozen causality assertion: window must close before entry
        entry_mm = 571
        assert all(b['mm'] < entry_mm or b['day'] < d for b in win), \
            'LEAK: signal window reaches the entry bar'
        if len(win) < need:
            continue
        r = _flow_ratio(win)
        if r is None or r == 0:
            continue
        j0 = next((i for i, b in enumerate(bars) if b['mm'] == entry_mm), None)
        if j0 is None:
            continue
        atr = _atr_before(bars, entry_mm)
        if not atr:
            continue
        dirv = 1 if r > 0 else -1
        jx, ek = _exit_index(bars, j0, entry_mm + H)
        if jx is None:
            g = dirv * (bars[-1]['close'] - bars[j0]['open'])
            kind = 'DAYLAST'
        else:
            g, kind = race(bars, j0, jx, dirv, 1.5 * atr)
        pr_prev = byday[days[k - 1]]
        on_price = (win[-1]['close'] - win[0]['open']) if win else 0.0
        ev.append(dict(cand=cand, day=d, et=bars[j0]['et'], dir=dirv,
                       sig=r, stop=1.5 * atr, gross=g, exit=kind,
                       twin_dir=(1 if on_price > 0 else -1) if on_price else 0,
                       diverg=int(on_price != 0 and (r > 0) != (on_price > 0))))
        del pr_prev
    return ev


# ---------------------------------------------------------------------
# F08 event builder
# ---------------------------------------------------------------------
def _day_A_series(bars):
    """(mm, A, lam_b, lam_s) at every valid evaluation stamp of one day."""
    rth = [b for b in bars if 571 <= b['mm'] <= 960]
    out = []
    for i in range(59, len(rth)):
        w = rth[i - 59:i + 1]
        if w[-1]['mm'] - w[0]['mm'] != 59:
            continue
        dbuy = dsell = pbuy = psell = 0.0
        nb = ns = 0
        for t in range(1, 60):
            dp = w[t]['close'] - w[t - 1]['close']
            dl = w[t]['ofBarDelta'] or 0
            if dl > 0:
                nb += 1; dbuy += dl; pbuy += dp
            elif dl < 0:
                ns += 1; dsell += dl; psell += dp
        if nb < 10 or ns < 10 or dbuy == 0 or dsell == 0:
            continue
        lb, ls = pbuy / dbuy, psell / dsell
        out.append((w[-1]['mm'], lb - ls, lb, ls))
    return out


def build_f08(days, byday, cand):
    H = {'C-F08-1': 15, 'C-F08-2': 30}[cand]
    Aday = {d: _day_A_series(byday[d]) for d in days}
    ev = []
    for k, d in enumerate(days):
        pool = [abs(a) for dd in days[max(0, k - 20):k]
                for (m, a, _, _) in Aday[dd] if 631 <= m and m + 1 + H <= 960]
        if len(pool) < 500:
            continue
        thr = q7(pool, 0.75)
        bars = byday[d]
        idx = {b['mm']: i for i, b in enumerate(bars)}
        nxt = 0
        for (m, a, lb, ls) in Aday[d]:
            if m < max(631, nxt) or m + 1 + H > 960 or abs(a) < thr:
                continue
            j0 = idx.get(m + 1)
            if j0 is None:
                continue
            atr = bars[idx[m]]['atr'] if m in idx else None
            if not atr:
                continue
            dirv = 1 if a > 0 else -1
            jx, _ = _exit_index(bars, j0, m + 1 + H)
            if jx is None:
                g, kind = dirv * (bars[-1]['close'] - bars[j0]['open']), 'DAYLAST'
            else:
                g, kind = race(bars, j0, jx, dirv, 1.5 * atr)
            ev.append(dict(cand=cand, day=d, et=bars[j0]['et'], dir=dirv,
                           sig=a, lam_b=lb, lam_s=ls, stop=1.5 * atr,
                           gross=g, exit=kind, thr=thr))
            nxt = m + H + 1
    return ev


# ---------------------------------------------------------------------
# frozen statistics
# ---------------------------------------------------------------------
def stats_cell(ev):
    g = np.array([e['gross'] for e in ev])
    r = np.array([e['stop'] for e in ev])
    days = np.array([e['day'] for e in ev])
    ud = sorted(set(days))
    base, st = g - COST_BASE, g - COST_STRESS
    out = dict(n=len(ev), days=len(ud),
               gross=float(g.mean()), base=float(base.mean()),
               stressed=float(st.mean()),
               gross_R=float((g / r).mean()), base_R=float((base / r).mean()),
               stressed_R=float((st / r).mean()),
               win_base=float((base > 0).mean()),
               pf_base=_pf(base), pf_stressed=_pf(st),
               payoff_stressed=_payoff(st))
    # day-clustered bootstrap on stressed mean
    rng = np.random.default_rng(SEED_BOOT)
    dmap = collections.defaultdict(list)
    for i, d in enumerate(days):
        dmap[d].append(i)
    idx_by_day = [np.array(dmap[d]) for d in ud]
    means = np.empty(B_BOOT)
    for b in range(B_BOOT):
        pick = rng.integers(0, len(ud), len(ud))
        ii = np.concatenate([idx_by_day[p] for p in pick])
        means[b] = st[ii].mean()
    out['ci_lo'], out['ci_hi'] = (float(np.percentile(means, 2.5)),
                                  float(np.percentile(means, 97.5)))
    # day-blocked sign-flip permutation on gross mean
    rng = np.random.default_rng(SEED_PERM)
    obs = g.mean()
    day_of = np.searchsorted(np.array(ud), days)
    cnt = 0
    for p in range(P_PERM):
        fl = rng.choice([-1.0, 1.0], len(ud))
        if (g * fl[day_of]).mean() >= obs:
            cnt += 1
    out['perm_p'] = (cnt + 1) / (P_PERM + 1)
    # matched random-direction control (day-blocked, identical management)
    rng = np.random.default_rng(SEED_CTRL)
    cm = np.empty(N_CTRL)
    for c in range(N_CTRL):
        fl = rng.choice([-1.0, 1.0], len(ud))
        cm[c] = (g * fl[day_of]).mean()
    out['ctrl_mean'], out['ctrl_sd'] = float(cm.mean()), float(cm.std())
    return out


def _pf(x):
    lo = -x[x < 0].sum()
    return float(x[x > 0].sum() / lo) if lo > 0 else float('inf')


def _payoff(x):
    w, l = x[x > 0], x[x < 0]
    if not len(w) or not len(l):
        return float('nan')
    return float(w.mean() / -l.mean())


def bh(ps):
    """Benjamini-Hochberg q-values."""
    m = len(ps)
    order = sorted(range(m), key=lambda i: ps[i])
    q = [0.0] * m
    prev = 1.0
    for rank in range(m, 0, -1):
        i = order[rank - 1]
        prev = min(prev, ps[i] * m / rank)
        q[i] = prev
    return q
