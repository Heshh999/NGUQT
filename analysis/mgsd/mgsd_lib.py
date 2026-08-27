#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  shared engine  (protocol freeze v1.0, commit 7062e678)
# Frozen constants only; no discovery decision lives in this file.
# ======================================================================
import os, sys, csv, glob, json, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))
import rvmr_run as RV

SEED = 20260827
BOOT = 10000
PERM = 10000
COST_BASE = 0.87
COST_RTH_STRESS = 1.305
COST_NONRTH_STRESS = 1.740
DEV_LAST_DAY = '2026-08-17'
NAN = float('nan')

STRATA = {'S1': (961, 1020), 'S2': None, 'S3': (121, 480), 'S4': (481, 569),
          'S5': (571, 600), 'S6': (601, 690), 'S7': (691, 840),
          'S8': (841, 930), 'S9': (931, 960)}


def stratum_of(m):
    if 961 <= m <= 1020: return 'S1'
    if m >= 1081 or m <= 120: return 'S2'
    if 121 <= m <= 480: return 'S3'
    if 481 <= m <= 569: return 'S4'
    if 571 <= m <= 600: return 'S5'
    if 601 <= m <= 690: return 'S6'
    if 691 <= m <= 840: return 'S7'
    if 841 <= m <= 930: return 'S8'
    if 931 <= m <= 960: return 'S9'
    return ''


def load():
    """Canonical grid + every frozen causal feature array."""
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    # ---- PARTITION GUARD (frozen): refuse any bar past the DEV boundary
    keepN = sum(1 for d in D['day'] if d <= DEV_LAST_DAY)
    for k in list(D):
        D[k] = D[k][:keepN]
    N = len(D['c'])
    G = {'N': N, 'et': D['et'], 'day': D['day'],
         'o': np.array(D['o']), 'h': np.array(D['h']),
         'l': np.array(D['l']), 'c': np.array(D['c']),
         'v': np.array(D['v']),
         'mod': np.array(D['mod'], dtype=np.int32),
         'em': np.array(D['em'], dtype=np.int64)}
    day, mod, em = G['day'], G['mod'], G['em']
    o, h, l, c, v = G['o'], G['h'], G['l'], G['c'], G['v']

    # contiguity
    step1 = np.zeros(N, bool); step1[1:] = (em[1:] - em[:-1]) == 1
    G['step1'] = step1

    # ---- trade-date assignment (exit-by boundary) ----------------------
    days_all = sorted(set(day))
    rth_days = sorted(set(day[i] for i in range(N) if 571 <= mod[i] <= 960))
    nxt = {}
    for i, d in enumerate(days_all):
        nxt[d] = next((r for r in rth_days if r > d), None)
    td = np.empty(N, dtype=object)
    for i in range(N):
        td[i] = day[i] if mod[i] <= 1020 else (nxt[day[i]] or '9999')
    G['tradedate'] = td

    # ---- per-day RTH-close bar index (stamp 951..960 last available) ---
    closebar = {}
    for i in range(N):
        if 941 <= mod[i] <= 960:
            k = day[i]
            if k not in closebar or mod[i] > mod[closebar[k]]:
                closebar[k] = i
    G['closebar'] = closebar

    # ---- completed 15m aggregation + ATR14(15m), causal at stamp -------
    g15 = collections.defaultdict(list)
    for i in range(N):
        g15[(day[i], (mod[i] - 1) // 15)].append(i)
    atr15 = np.full(N, NAN)
    bar15 = {}                      # key -> (o,h,l,c, last_i)
    tr_prev_close = {}
    # chronological completed 15m bars
    keys = sorted(g15, key=lambda k: g15[k][-1])
    tr_hist = []
    prev_c15 = None
    avail = []                      # (last_1m_index, atr_value)
    for k in keys:
        idx = g15[k]
        if len(idx) != 15 or em[idx[-1]] - em[idx[0]] != 14:
            prev_c15 = c[idx[-1]]
            continue
        hi = h[idx].max(); lo = l[idx].min(); cl = c[idx[-1]]; op = o[idx[0]]
        tr = hi - lo if prev_c15 is None else max(hi - lo, abs(hi - prev_c15),
                                                  abs(lo - prev_c15))
        prev_c15 = cl
        tr_hist.append(tr)
        if len(tr_hist) > 14:
            tr_hist.pop(0)
        aval = sum(tr_hist) / 14.0 if len(tr_hist) == 14 else NAN
        bar15[k] = (op, hi, lo, cl, idx[-1], aval)
        avail.append((idx[-1], aval))
    # forward-fill atr15 by availability index
    ai = 0
    cur = NAN
    av_idx = [a[0] for a in avail]
    av_val = [a[1] for a in avail]
    for i in range(N):
        while ai < len(av_idx) and av_idx[ai] <= i:
            cur = av_val[ai]; ai += 1
        atr15[i] = cur
    G['atr15'] = atr15
    G['bar15'] = bar15

    # completed 3m and 60m bars
    def agg(step):
        gg = collections.defaultdict(list)
        for i in range(N):
            gg[(day[i], (mod[i] - 1) // step)].append(i)
        out = {}
        for k, idx in gg.items():
            if len(idx) == step and em[idx[-1]] - em[idx[0]] == step - 1:
                out[k] = (o[idx[0]], h[idx].max(), l[idx].min(),
                          c[idx[-1]], idx[-1])
        return out
    G['bar3'] = agg(3)
    G['bar60'] = agg(60)

    # ---- session VWAP (RTH, from stamp 571), causal at each close ------
    vwap = np.full(N, NAN)
    accv = accpv = 0.0
    curd = None
    for i in range(N):
        if 571 <= mod[i] <= 960:
            if day[i] != curd:
                curd = day[i]; accv = accpv = 0.0
            px = (h[i] + l[i] + c[i]) / 3.0
            accv += v[i]; accpv += px * v[i]
            if accv > 0:
                vwap[i] = accpv / accv
    G['vwap'] = vwap

    # ---- per-tradedate overnight/premarket/prior-day features ----------
    # prior RTH stats
    rth = collections.defaultdict(list)
    for i in range(N):
        if 571 <= mod[i] <= 960:
            rth[day[i]].append(i)
    pd_feat = {}
    prev = None
    for d in rth_days:
        idx = rth[d]
        pd_feat[d] = {'hi': h[idx].max(), 'lo': l[idx].min(),
                      'close': c[idx[-1]],
                      'rng': h[idx].max() - l[idx].min()}
    G['prior_rth'] = {}
    for i, d in enumerate(rth_days):
        if i:
            G['prior_rth'][d] = pd_feat[rth_days[i - 1]]
    # overnight (18:01 prior evening .. 09:29 of tradedate) per tradedate
    on = collections.defaultdict(lambda: {'hi': -1e18, 'lo': 1e18,
                                          'first': None, 'v0429': 0.0,
                                          'c0800': None, 'c0929': None,
                                          'hi_i': None, 'lo_i': None,
                                          'n': 0})
    for i in range(N):
        m = mod[i]
        if m >= 1081 or m <= 569:
            k = td[i]
            e = on[k]
            e['n'] += 1
            if e['first'] is None:
                e['first'] = o[i]
            if h[i] > e['hi']:
                e['hi'] = h[i]; e['hi_i'] = e['n']
            if l[i] < e['lo']:
                e['lo'] = l[i]; e['lo_i'] = e['n']
            if 241 <= m <= 569:
                e['v0429'] += v[i]
            if m == 480:
                e['c0800'] = c[i]
            if m == 569:
                e['c0929'] = c[i]
    G['overnight'] = dict(on)
    G['rth_days'] = rth_days
    G['rth_idx'] = rth
    return G


# ---------------------------------------------------------------- races
def race_pool(G, slots, dirv, stop_mult, exit_kind, target=None,
              chunk=20000):
    """Vectorized trade race for entry at OPEN of each slot bar.
    exit_kind: 'T30' | 'T120' | 'CLOSE' | 'TGT' (target array, cap CLOSE).
    Returns (netPts_gross, stopDist, exit_ok, ambig) per slot.
    Stop-first inside every bar including the entry bar."""
    N = G['N']
    h_, l_, c_, o_ = G['h'], G['l'], G['c'], G['o']
    mod, em, day = G['mod'], G['em'], G['day']
    closebar = G['closebar']
    ns = len(slots)
    net = np.full(ns, NAN)
    sd = np.full(ns, NAN)
    ok = np.zeros(ns, bool)
    amb = np.zeros(ns, bool)
    maxw = {'T30': 30, 'T120': 120, 'CLOSE': 1330, 'TGT': 390,
            'OPEN': 940}[exit_kind]
    for s0 in range(0, ns, chunk):
        sl = slots[s0:s0 + chunk]
        n = len(sl)
        ent = o_[sl]
        atr = G['atr15'][sl - 1]           # known at signal close (prev bar)
        stopd = stop_mult * atr
        good = ~np.isnan(stopd) & (stopd > 0)
        # exit bar index (inclusive cap)
        if exit_kind in ('T30', 'T120'):
            lastk = np.minimum(sl + ({'T30': 30, 'T120': 120}[exit_kind] - 1),
                               N - 1)
        elif exit_kind == 'OPEN':
            ob = G['open_bar_by_td']
            lastk = np.array([max(int(i), ob.get(G['tradedate'][i], int(i)) - 1)
                              for i in sl])
        else:
            lastk = np.array([closebar.get(G['tradedate'][i], min(i, N - 1))
                              for i in sl])
        lastk = np.maximum(lastk, sl)
        W = int(min(maxw, int((lastk - sl).max()) + 1))
        idx = sl[:, None] + np.arange(W)[None, :]
        np.clip(idx, 0, N - 1, out=idx)
        valid = idx <= lastk[:, None]
        # em contiguity: a gap ends the tradeable window at the gap
        emw = G['em'][idx]
        contig = np.cumprod(
            np.concatenate([np.ones((n, 1), bool),
                            (emw[:, 1:] - emw[:, :-1]) == 1], axis=1), axis=1
        ).astype(bool)
        valid &= contig
        hw, lw = h_[idx], l_[idx]
        if dirv > 0:
            stop_lv = ent - stopd
            hit_stop = (lw <= stop_lv[:, None]) & valid
        else:
            stop_lv = ent + stopd
            hit_stop = (hw >= stop_lv[:, None]) & valid
        if exit_kind == 'TGT':
            tg = target[s0:s0 + chunk]
            if dirv > 0:
                hit_tgt = (hw >= tg[:, None]) & valid
            else:
                hit_tgt = (lw <= tg[:, None]) & valid
        ks = np.where(hit_stop.any(1), hit_stop.argmax(1), 10 ** 6)
        # exit index = last valid bar
        kend = valid.sum(1) - 1
        kend = np.maximum(kend, 0)
        res = np.empty(n)
        if exit_kind == 'TGT':
            kt = np.where(hit_tgt.any(1), hit_tgt.argmax(1), 10 ** 6)
            ambg = (ks == kt) & (ks < 10 ** 6)
            stop_first = (ks <= kt) & (ks < 10 ** 6)     # stop-first on tie
            tgt_first = kt < ks
            res[:] = dirv * (c_[idx[np.arange(n), kend]] - ent)
            res[tgt_first] = (dirv * (tg - ent))[tgt_first]
            res[stop_first] = (dirv * (stop_lv - ent))[stop_first]
            amb[s0:s0 + n] = ambg
        else:
            stopped = ks < 10 ** 6
            if exit_kind == 'OPEN':
                nxt = np.minimum(lastk + 1, N - 1)
                res[:] = dirv * (o_[nxt] - ent)
            else:
                res[:] = dirv * (c_[idx[np.arange(n), kend]] - ent)
            res[stopped] = (dirv * (stop_lv - ent))[stopped]
        res[~good] = np.nan
        net[s0:s0 + n] = res
        sd[s0:s0 + n] = stopd
        ok[s0:s0 + n] = good
    return net, sd, ok, amb
