#!/usr/bin/env python3
# ODMC-V1 engine (freeze 9072bd3d; config ODMC_V1_CONFIG.json)
import os, sys, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mgsd'))
import mgsd_lib as L

TICK = 0.25
COST_BASE = 0.87            # repository frozen base
COST_RTH = 1.305            # repository RTH stressed (reported)
COST_STRESS = 2.00          # BINDING: 4 ticks/side opening stress
SEED = 20260904
B0, T5S, ENT, T10S, EXI = 571, 575, 576, 580, 581


def build_events(b0=B0, t5=T5S, ent=ENT, t10=T10S, exi=EXI):
    G = L.load()
    N = G['N']
    mod, day, em = G['mod'], G['day'], G['em']
    o, h, l, c = G['o'], G['h'], G['l'], G['c']
    byday = collections.defaultdict(dict)
    lo_s, hi_s = min(b0, exi), max(b0, exi)
    for i in range(N):
        if lo_s <= mod[i] <= hi_s:
            byday[day[i]][mod[i]] = i
    ev = []
    for d in sorted(byday):
        m = byday[d]
        if any(s not in m for s in range(b0, exi + 1)):
            continue
        if em[m[exi]] - em[m[b0]] != (exi - b0):
            continue
        widx = [m[s] for s in range(ent, t10 + 1)]
        sig = [m[s] for s in range(b0, t5 + 1)]
        ev.append({'day': d, 'i_b0': m[b0], 'i_t5': m[t5], 'i_ent': m[ent],
                   'i_exit': m[exi], 'P0': o[m[b0]], 'P5': c[m[t5]],
                   'M': c[m[t5]] - o[m[b0]], 'entry_open': o[m[ent]],
                   'exit_open': o[m[exi]],
                   'F': o[m[exi]] - o[m[ent]],
                   'sig_rng': max(h[i] for i in sig) - min(l[i] for i in sig),
                   'rng': max(h[i] for i in widx) - min(l[i] for i in widx),
                   'widx': widx})
    return G, ev


def gates_series(ev):
    absM = np.array([abs(e['M']) for e in ev])
    R = np.array([e['rng'] for e in ev])
    n = len(ev)
    thr = np.full(n, np.nan); ss = np.full(n, np.nan)
    for k in range(n):
        lo = max(0, k - 252)
        if k - lo >= 126:
            thr[k] = np.quantile(absM[lo:k], 0.90)     # type-7
        rl = R[max(0, k - 60):k]
        if len(rl) >= 40:
            ss[k] = np.median(rl)
    return thr, ss


def stop_dist(scale):
    return max(TICK, np.ceil(1.5 * scale / TICK) * TICK)


def race(G, e, dirv, sd, slip_ticks=0, widx=None, exit_open=None):
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
