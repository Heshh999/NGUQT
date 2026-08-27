#!/usr/bin/env python3
# ======================================================================
# CCHC-V1 engine  (protocol freeze 5133c511; config CCHC_V1_CONFIG.json)
# Mechanism only: events, causal gates, races, costs. No search choice.
# ======================================================================
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L

CFG = json.load(open(os.path.join(HERE, 'CCHC_V1_CONFIG.json')))
TICK = 0.25
COST_BASE = 0.87
COST_STRESS = 1.305          # BINDING: repository RTH stressed model
COST_STRESS_NONRTH = 1.740   # supplementary conservatism check
SEED = 20260901
DEC, ENT, EXI = 930, 931, 961


def build_events():
    """One row per eligible day. No gate/outcome decision here."""
    G = L.load()
    N = G['N']
    mod, day, em = G['mod'], G['day'], G['em']
    o, h, l, c = G['o'], G['h'], G['l'], G['c']
    byday = collections.defaultdict(dict)
    for i in range(N):
        if mod[i] == 571 or DEC <= mod[i] <= EXI:
            byday[day[i]][mod[i]] = i
    ev = []
    for d in sorted(byday):
        m = byday[d]
        if 571 not in m:
            continue
        if any(s not in m for s in range(DEC, EXI + 1)):
            continue                       # early close / missing bars
        if em[m[EXI]] - em[m[DEC]] != (EXI - DEC):
            continue                       # strict contiguity
        widx = [m[s] for s in range(ENT, EXI)]   # the 30 interval bars
        ev.append({'day': d, 'i_open': m[571], 'i_dec': m[DEC],
                   'i_ent': m[ENT], 'i_exit': m[EXI],
                   'rth_open': o[m[571]], 'dec_close': c[m[DEC]],
                   'D': c[m[DEC]] - o[m[571]],
                   'entry_open': o[m[ENT]], 'exit_open': o[m[EXI]],
                   'F': o[m[EXI]] - o[m[ENT]],
                   'rng': max(h[i] for i in widx) - min(l[i] for i in widx),
                   'widx': widx})
    return G, ev


def gates_series(ev):
    """Causal per-day gate state; row k uses rows < k only."""
    absD = np.array([abs(e['D']) for e in ev])
    D = np.array([e['D'] for e in ev])
    F = np.array([e['F'] for e in ev])
    R = np.array([e['rng'] for e in ev])
    n = len(ev)
    thr = np.full(n, np.nan); beta = np.full(n, np.nan)
    ss = np.full(n, np.nan)
    for k in range(n):
        lo = max(0, k - 252)
        if k - lo >= 126:
            thr[k] = np.quantile(absD[lo:k], 0.90)     # type-7
        if k >= 126:
            x = D[k - 126:k]; y = F[k - 126:k]
            vx = x - x.mean(); den = (vx ** 2).sum()
            if den > 0:
                beta[k] = (vx * (y - y.mean())).sum() / den
        rl = R[max(0, k - 60):k]
        if len(rl) >= 40:
            ss[k] = np.median(rl)
    return thr, beta, ss


def stop_dist(scale):
    return max(TICK, np.ceil(1.5 * scale / TICK) * TICK)


def race(G, e, dirv, sd, slip_ticks, widx=None, exit_open=None):
    """Stop-market race; time exit at exit_open. Adverse slippage both
    sides. Gap-through fills at the worse bar open."""
    o, h, l = G['o'], G['h'], G['l']
    widx = e['widx'] if widx is None else widx
    exo = e['exit_open'] if exit_open is None else exit_open
    ent = e['entry_open'] + dirv * slip_ticks * TICK
    stop = ent - dirv * sd
    for i in widx:
        if (dirv > 0 and o[i] <= stop) or (dirv < 0 and o[i] >= stop):
            return dirv * ((o[i] - dirv * slip_ticks * TICK) - ent), True
        if (dirv > 0 and l[i] <= stop) or (dirv < 0 and h[i] >= stop):
            return dirv * ((stop - dirv * slip_ticks * TICK) - ent), True
    return dirv * ((exo - dirv * slip_ticks * TICK) - ent), False


def mfe_mae(G, e, dirv):
    h, l = G['h'], G['l']
    ent = e['entry_open']
    fav = max((h[i] - ent) if dirv > 0 else (ent - l[i]) for i in e['widx'])
    adv = max((ent - l[i]) if dirv > 0 else (h[i] - ent) for i in e['widx'])
    return max(fav, 0.0), max(adv, 0.0)
