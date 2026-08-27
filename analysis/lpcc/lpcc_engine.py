#!/usr/bin/env python3
# ======================================================================
# LPCC-V1 engine (protocol freeze f08396b1; config LPCC_V1_CONFIG.json)
# Pure mechanism: event table, gates, races, costs. No discovery choice.
# ======================================================================
import os, sys, json, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L

CFG = json.load(open(os.path.join(HERE, 'LPCC_V1_CONFIG.json')))
TICK = 0.25
COST_BASE = 0.87
COST_STRESS = 1.74
SEED = 20260829


def build_events():
    """One row per eligible day; NO gate or outcome decisions here."""
    G = L.load()
    N = G['N']
    mod, day, em = G['mod'], G['day'], G['em']
    o, h, l, c = G['o'], G['h'], G['l'], G['c']
    # locate per-day stamp indices 480..511
    byday = collections.defaultdict(dict)
    for i in range(N):
        if 480 <= mod[i] <= 511:
            byday[day[i]][mod[i]] = i
    ev = []
    for d in sorted(byday):
        m = byday[d]
        if any(s not in m for s in range(480, 512)):
            continue
        i480 = m[480]
        if em[m[511]] - em[i480] != 31:          # strict contiguity
            continue
        pr = G['prior_rth'].get(d)
        if not pr:
            continue
        widx = [m[s] for s in range(481, 511)]   # the 30 window bars
        ev.append({'day': d, 'i_dec': i480, 'i_ent': m[481], 'i_exit': m[511],
                   'prevclose': pr['close'], 'dec_close': c[i480],
                   'D': c[i480] - pr['close'],
                   'entry_open': o[m[481]], 'exit_open': o[m[511]],
                   'F': o[m[511]] - o[m[481]],
                   'rng': max(h[i] for i in widx) - min(l[i] for i in widx),
                   'widx': widx})
    return G, ev


def gates_series(ev):
    """Causal per-day gate state; day k uses rows < k only."""
    absD = np.array([abs(e['D']) for e in ev])
    D = np.array([e['D'] for e in ev])
    F = np.array([e['F'] for e in ev])
    R = np.array([e['rng'] for e in ev])
    n = len(ev)
    thr = np.full(n, np.nan)
    beta = np.full(n, np.nan)
    stop_scale = np.full(n, np.nan)
    for k in range(n):
        lo = max(0, k - 252)
        hist = absD[lo:k]
        if len(hist) >= 126:
            thr[k] = np.quantile(hist, 0.90)     # type-7 linear (frozen)
        if k >= 126:
            x = D[k - 126:k]; y = F[k - 126:k]
            vx = x - x.mean()
            den = (vx ** 2).sum()
            if den > 0:
                beta[k] = (vx * (y - y.mean())).sum() / den
        rl = R[max(0, k - 60):k]
        if len(rl) >= 40:
            stop_scale[k] = np.median(rl)
    return thr, beta, stop_scale


def stop_dist(scale):
    d = 1.5 * scale
    return max(TICK, np.ceil(d / TICK) * TICK)


def race(G, e, dirv, sd, slip_ticks):
    """Stop-market race over the 30 window bars; time exit at exit_open.
    Adverse slippage slip_ticks per side. Returns net points."""
    o, h, l = G['o'], G['h'], G['l']
    ent = e['entry_open'] + dirv * slip_ticks * TICK
    stop = ent - dirv * sd
    for i in e['widx']:
        if (dirv > 0 and o[i] <= stop) or (dirv < 0 and o[i] >= stop):
            fill = o[i] - dirv * slip_ticks * TICK      # gap-through: worse open
            return dirv * (fill - ent), True
        if (dirv > 0 and l[i] <= stop) or (dirv < 0 and h[i] >= stop):
            fill = stop - dirv * slip_ticks * TICK
            return dirv * (fill - ent), True
    fill = e['exit_open'] - dirv * slip_ticks * TICK
    return dirv * (fill - ent), False


def mfe_mae(G, e, dirv):
    h, l = G['h'], G['l']
    ent = e['entry_open']
    fav = max((h[i] - ent) if dirv > 0 else (ent - l[i]) for i in e['widx'])
    adv = max((ent - l[i]) if dirv > 0 else (h[i] - ent) for i in e['widx'])
    return max(fav, 0.0), max(adv, 0.0)
