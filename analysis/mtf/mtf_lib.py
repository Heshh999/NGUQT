#!/usr/bin/env python3
# ======================================================================
# MTF-V1  -  FROZEN ENGINE  (committed before any outcome is displayed)
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
SEED_A1, SEED_A2, SEED_B1, SEED_B2_BOOT, SEED_B2_PERM = \
    20260830, 20260831, 20260832, 20260833, 20260834
VUP, EUP, VDN, EDN = '102', '012', '201', '210'   # frozen (confirm2)


def load():
    import rvmr_run as RV
    RV.STAMP_SHIFT = 0
    D = RV.load_bars()
    keep = [i for i in range(len(D['c'])) if D['day'][i] <= DEV_LAST]
    out = {}
    for k in ('et', 'day'):
        out[k] = [D[k][i] for i in keep]
    for k in ('o', 'h', 'l', 'c', 'v'):
        out[k] = np.array([D[k][i] for i in keep], float)
    out['em'] = np.array([D['em'][i] for i in keep], np.int64)
    out['mod'] = np.array([D['mod'][i] for i in keep], np.int32)
    return out


# ---------------------------------------------------------------------
# T-minute bars on the em contiguity clock. A bucket is VALID only if
# all T minutes are present. Returns arrays + bucket ids + day of the
# bucket's LAST minute.
# ---------------------------------------------------------------------
def tbars(D, T):
    b = D['em'] // T
    o, h, l, c, day, bid = [], [], [], [], [], []
    i, N = 0, len(b)
    while i < N:
        j = i
        while j < N and b[j] == b[i]:
            j += 1
        if j - i == T:
            o.append(D['o'][i]); h.append(D['h'][i:j].max())
            l.append(D['l'][i:j].min()); c.append(D['c'][j - 1])
            day.append(D['day'][j - 1]); bid.append(int(b[i]))
        i = j
    return dict(o=np.array(o), h=np.array(h), l=np.array(l),
                c=np.array(c), day=day, bid=np.array(bid, np.int64))


def contiguous_returns(tb):
    """log returns between ADJACENT buckets only; (idx_prev, ret)."""
    r, idx = [], []
    for k in range(1, len(tb['c'])):
        if tb['bid'][k] - tb['bid'][k - 1] == 1:
            r.append(np.log(tb['c'][k] / tb['c'][k - 1]))
            idx.append(k)
    return np.array(idx), np.array(r)


def motif_of(x0, x1, x2):
    order = sorted(range(3), key=lambda j: (x0, x1, x2)[j])
    return '%d%d%d' % (order[0], order[1], order[2])


# ---------------------------------------------------------------------
# frozen bootstrap helpers
# ---------------------------------------------------------------------
def day_boot_mean(vals, days, B, seed):
    ud = sorted(set(days))
    dmap = collections.defaultdict(list)
    for i, d in enumerate(days):
        dmap[d].append(i)
    idx = [np.array(dmap[d]) for d in ud]
    rng = np.random.default_rng(seed)
    v = np.asarray(vals, float)
    m = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(ud), len(ud))
        ii = np.concatenate([idx[p] for p in pick])
        m[b] = v[ii].mean()
    return (float(v.mean()), float(np.percentile(m, 2.5)),
            float(np.percentile(m, 97.5)))


def day_boot_diff(valsA, daysA, valsB, daysB, B, seed):
    """day-blocked bootstrap of mean(A)-mean(B), days resampled jointly
    (same day pick applies to both groups) - confirm2 dblocks pattern."""
    agg = {}
    for v, d in zip(valsA, daysA):
        e = agg.setdefault(d, [0.0, 0, 0.0, 0]); e[0] += v; e[1] += 1
    for v, d in zip(valsB, daysB):
        e = agg.setdefault(d, [0.0, 0, 0.0, 0]); e[2] += v; e[3] += 1
    blocks = list(agg.values())
    sa = sum(e[0] for e in blocks); na = sum(e[1] for e in blocks)
    sb = sum(e[2] for e in blocks); nb = sum(e[3] for e in blocks)
    obs = sa / na - sb / nb
    rng = np.random.default_rng(seed)
    arr = np.array(blocks)
    m = np.empty(B)
    for b in range(B):
        pick = rng.integers(0, len(blocks), len(blocks))
        s = arr[pick].sum(axis=0)
        m[b] = (s[0] / s[1] if s[1] else np.nan) - \
               (s[2] / s[3] if s[3] else np.nan)
    m = m[~np.isnan(m)]
    plo = (m <= 0).mean(); phi = (m >= 0).mean()
    p = 2 * min(plo, phi) + 1.0 / len(m)
    return (float(obs), float(np.percentile(m, 2.5)),
            float(np.percentile(m, 97.5)), float(min(1.0, p)))


def stationary_boot_mean(vals, B, seed, block=20):
    rng = np.random.default_rng(seed)
    v = np.asarray(vals, float); n = len(v)
    m = np.empty(B)
    for b in range(B):
        out = np.empty(n); k = 0
        while k < n:
            s = rng.integers(0, n); L = min(rng.geometric(1.0 / block), n - k)
            seg = np.take(v, np.arange(s, s + L), mode='wrap')
            out[k:k + L] = seg; k += L
        m[b] = out.mean()
    return (float(v.mean()), float(np.percentile(m, 2.5)),
            float(np.percentile(m, 97.5)))


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


# ---------------------------------------------------------------------
# B1  V-TURN events at timeframe T
# ---------------------------------------------------------------------
def vturn_events(D, T):
    tb = tbars(D, T)
    c, bid, day = tb['c'], tb['bid'], tb['day']
    rows = []
    for k in range(2, len(c) - 1):
        if bid[k] - bid[k - 2] != 2 or bid[k + 1] - bid[k] != 1:
            continue
        x0, x1, x2 = c[k - 2], c[k - 1], c[k]
        if x0 == x1 or x1 == x2 or x0 == x2:
            continue
        r1 = np.log(c[k + 1] / c[k])
        m = motif_of(x0, x1, x2)
        lls = 1.0 if x2 > x1 else -1.0
        rows.append(dict(day=day[k + 1], motif=m, ta=lls * r1 * 1e4,
                         price=c[k]))
    return rows


# ---------------------------------------------------------------------
# B2  VWAP-OU-CLOCK event engine (1m grid)
# ---------------------------------------------------------------------
def b2_run(D, q=0.90, exit_min=212, counts_only=False):
    N = len(D['c'])
    byday = collections.defaultdict(list)
    for i in range(N):
        byday[D['day'][i]].append(i)
    days = sorted(byday)
    # per-day RTH vwap + range
    vwap = np.full(N, np.nan)
    rr = {}
    for d in days:
        num = den = 0.0
        hi, lo, nb = -1e18, 1e18, 0
        for i in byday[d]:
            mod = D['mod'][i]
            if 571 <= mod <= 960:
                tp = (D['h'][i] + D['l'][i] + D['c'][i]) / 3.0
                num += tp * D['v'][i]; den += D['v'][i]
                if den > 0:
                    vwap[i] = num / den
                hi = max(hi, D['h'][i]); lo = min(lo, D['l'][i]); nb += 1
        if nb >= 300:
            rr[d] = hi - lo
    # causal base + threshold pools
    base, zpool = {}, {}
    for k, d in enumerate(days):
        prior = [rr[e] for e in days[max(0, k - 60):k] if e in rr]
        if len(prior) >= 40:
            base[d] = float(np.quantile(prior, 0.5, method='linear'))
    ev = []
    pool = collections.deque(maxlen=20)      # per-day |z| lists
    for d in days:
        idx = [i for i in byday[d] if 631 <= D['mod'][i] <= 900
               and vwap[i] == vwap[i]]
        zs = []
        thr = None
        flat = [z for sub in pool for z in sub]
        if d in base and len(flat) >= 2000:
            thr = float(np.quantile(flat, q, method='linear'))
        in_pos = False
        entry_i = jexit = None
        side = 0; ep = sp = risk = 0.0
        for i in idx:
            z = (D['c'][i] - vwap[i]) / base[d] if d in base else np.nan
            if z == z:
                zs.append(abs(z))
            if thr is None or not (z == z):
                continue
            if not in_pos and abs(z) >= thr and i + 1 < N \
                    and D['day'][i + 1] == d:
                dist = abs(D['c'][i] - vwap[i])
                side = -1 if z > 0 else 1          # fade toward vwap
                ep = D['o'][i + 1]
                sp = vwap[i] + (2.0 * dist) * (1 if z > 0 else -1)
                risk = dist
                entry_i = i + 1
                in_pos = True
                if counts_only:
                    ev.append(dict(day=d)); in_pos = False
                continue
            if in_pos and i >= entry_i:
                mod = D['mod'][i]
                stop_hit = (side == 1 and D['l'][i] <= sp) or \
                           (side == -1 and D['h'][i] >= sp)
                touch = D['l'][i] <= vwap[i] <= D['h'][i]
                timeout = (i - entry_i) >= exit_min or mod >= 955
                if stop_hit:
                    fill = min(sp, D['o'][i]) if side == 1 else \
                        max(sp, D['o'][i])
                    ev.append(dict(day=d, gross=side * (fill - ep),
                                   R=risk, kind='STOP'))
                    in_pos = False
                elif touch:
                    ev.append(dict(day=d, gross=side * (vwap[i] - ep),
                                   R=risk, kind='VWAP'))
                    in_pos = False
                elif timeout:
                    ev.append(dict(day=d, gross=side * (D['c'][i] - ep),
                                   R=risk, kind='TIME'))
                    in_pos = False
        if in_pos:      # day ended while open
            ev.append(dict(day=d, gross=side * (D['c'][idx[-1]] - ep),
                           R=risk, kind='EOD'))
        if zs:
            pool.append(zs)
    return ev


def strat_stats(ev, B=10000, P=10000, sb=SEED_B2_BOOT, sp=SEED_B2_PERM):
    g = np.array([e['gross'] for e in ev])
    R = np.array([e['R'] for e in ev])
    days = [e['day'] for e in ev]
    st = g - COST_STRESS
    base = g - COST_BASE
    out = dict(n=len(ev), days=len(set(days)),
               gross=float(g.mean()), base=float(base.mean()),
               stressed=float(st.mean()),
               base_R=float((base / R).mean()),
               stressed_R=float((st / R).mean()),
               win_base=float((base > 0).mean()))
    lo = -st[st < 0].sum()
    out['pf_stressed'] = float(st[st > 0].sum() / lo) if lo > 0 else float('inf')
    lo = -base[base < 0].sum()
    out['pf_base'] = float(base[base > 0].sum() / lo) if lo > 0 else float('inf')
    w, l = st[st > 0], st[st < 0]
    out['payoff'] = float(w.mean() / -l.mean()) if len(w) and len(l) else float('nan')
    _, out['ci_lo'], out['ci_hi'] = day_boot_mean(st, days, B, sb)
    # day-blocked sign-flip permutation on gross
    ud = sorted(set(days))
    di = {d: k for k, d in enumerate(ud)}
    dof = np.array([di[d] for d in days])
    rng = np.random.default_rng(sp)
    obs = g.mean(); cnt = 0
    for _ in range(P):
        fl = rng.choice([-1.0, 1.0], len(ud))
        if (g * fl[dof]).mean() >= obs:
            cnt += 1
    out['perm_p'] = (cnt + 1) / (P + 1)
    per_year = collections.defaultdict(list)
    for e in ev:
        per_year[e['day'][:4]].append(e['gross'] - COST_STRESS)
    out['years'] = {y: (len(v), float(np.mean(v)))
                    for y, v in sorted(per_year.items())}
    return out
