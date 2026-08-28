#!/usr/bin/env python3
# ======================================================================
# RMA-V1  -  FROZEN ONE-SHOT RUN  (realized moment asymmetry)
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mtf'))
import mtf_lib as M  # noqa: E402

COST_B, COST_S = 0.87, 1.305
STAMPS = [631, 661, 691, 721, 751, 781, 811, 841, 871]

t0 = time.time()
D = M.load()
N = len(D['c'])
print('RMA-V1 one-shot  DEV %s..%s  bars %d' % (min(D['day']), max(D['day']), N))

byday = collections.defaultdict(list)
for i in range(N):
    byday[D['day'][i]].append(i)
days = sorted(byday)

# ATR20 on 1m (contiguous TR), per confirm2 convention
atr = np.full(N, np.nan)
tr = np.full(N, np.nan)
for i in range(1, N):
    if D['em'][i] - D['em'][i - 1] == 1:
        tr[i] = max(D['h'][i] - D['l'][i], abs(D['h'][i] - D['c'][i - 1]),
                    abs(D['l'][i] - D['c'][i - 1]))
alpha = 1.0 / 20
prev = np.nan
for i in range(N):
    if tr[i] == tr[i]:
        prev = tr[i] if prev != prev else prev + alpha * (tr[i] - prev)
    atr[i] = prev

# ---------------------------------------------------------------------
# features at evaluation stamps
# ---------------------------------------------------------------------
feat = []          # (day, stamp, idx_of_stamp_bar, RSV, SKW)
for d in days:
    idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
    pos = {D['mod'][i]: i for i in idx}
    # RTH 1m returns of the day, contiguous only
    rets = {}
    for k in range(1, len(idx)):
        i0, i1 = idx[k - 1], idx[k]
        if D['em'][i1] - D['em'][i0] == 1:
            rets[D['mod'][i1]] = np.log(D['c'][i1] / D['c'][i0])
    for m in STAMPS:
        if m not in pos:
            continue
        w = [rets[x] for x in range(m - 179, m + 1) if x in rets]
        if len(w) < 150:
            continue
        w = np.array(w)
        tot = (w * w).sum()
        if tot <= 0:
            continue
        rsv = (w[w < 0] ** 2).sum() / tot
        sd = w.std()
        skw = ((w - w.mean()) ** 3).mean() / (sd ** 3) if sd > 0 else 0.0
        feat.append((d, m, pos[m], rsv, skw))
print('feature evaluations %d over %d days  (%.0fs)'
      % (len(feat), len(set(f[0] for f in feat)), time.time() - t0))

# causal decile thresholds: prior 60 days' pooled values
byd_feat = collections.defaultdict(list)
for f in feat:
    byd_feat[f[0]].append(f)
thr = {}
pool_r, pool_s = collections.deque(maxlen=60), collections.deque(maxlen=60)
for d in days:
    fr = [x for x in (pool_r[i] for i in range(len(pool_r))) for x in x]
    fs = [x for x in (pool_s[i] for i in range(len(pool_s))) for x in x]
    if len(fr) >= 1000:
        thr[d] = dict(r90=M.q7(fr, 0.90), r10=M.q7(fr, 0.10),
                      s90=M.q7(fs, 0.90), s10=M.q7(fs, 0.10),
                      r85=M.q7(fr, 0.85), r95=M.q7(fr, 0.95),
                      s85=M.q7(fs, 0.85), s95=M.q7(fs, 0.95))
    if d in byd_feat:
        pool_r.append([f[3] for f in byd_feat[d]])
        pool_s.append([f[4] for f in byd_feat[d]])


def race(bars_idx, j0, exit_min, dirv, stop_dist):
    ep = D['o'][bars_idx[j0]]
    sp = ep - dirv * stop_dist
    entry_mod = D['mod'][bars_idx[j0]]
    jx = None
    for k in range(j0 + 1, len(bars_idx)):
        if D['mod'][bars_idx[k]] >= entry_mod + exit_min:
            jx = k
            break
    end = jx if jx is not None else len(bars_idx)
    for k in range(j0, end):
        i = bars_idx[k]
        if (dirv > 0 and D['l'][i] <= sp) or (dirv < 0 and D['h'][i] >= sp):
            fill = min(sp, D['o'][i]) if dirv > 0 else max(sp, D['o'][i])
            return dirv * (fill - ep), 'STOP'
    if jx is not None:
        return dirv * (D['o'][bars_idx[jx]] - ep), 'TIME'
    return dirv * (D['c'][bars_idx[-1]] - ep), 'EOD'


def build(sel, exit_min=60, delay=0, key='primary'):
    """sel(frow, th) -> dirv or 0. One position at a time; 60m cooldown."""
    ev = []
    for d in days:
        if d not in thr or d not in byd_feat:
            continue
        th = thr[d]
        idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
        ipos = {i: k for k, i in enumerate(idx)}
        next_ok = 0
        for f in sorted(byd_feat[d], key=lambda x: x[1]):
            _, m, ib, rsv, skw = f
            if m < next_ok:
                continue
            dirv = sel(f, th)
            if dirv == 0:
                continue
            k0 = ipos.get(ib)
            if k0 is None or k0 + 1 + delay >= len(idx):
                continue
            j0 = k0 + 1 + delay
            sd = 3.0 * atr[idx[k0]]
            if not (sd == sd) or sd <= 0:
                continue
            g, kind = race(idx, j0, exit_min, dirv, sd)
            ev.append(dict(day=d, gross=g, R=sd, kind=kind, dir=dirv))
            next_ok = m + 60
    return ev


CELLS = {
    'C1_RSVhi_L': lambda f, t: 1 if f[3] >= t['r90'] else 0,
    'C2_RSVlo_S': lambda f, t: -1 if f[3] <= t['r10'] else 0,
    'C3_SKWlo_L': lambda f, t: 1 if f[4] <= t['s10'] else 0,
    'C4_SKWhi_S': lambda f, t: -1 if f[4] >= t['s90'] else 0,
}
NEIGH = {
    'C1_q85': lambda f, t: 1 if f[3] >= t['r85'] else 0,
    'C1_q95': lambda f, t: 1 if f[3] >= t['r95'] else 0,
    'C4_q85': lambda f, t: -1 if f[4] >= t['s85'] else 0,
    'C4_q95': lambda f, t: -1 if f[4] >= t['s95'] else 0,
}

print('\n' + '=' * 92)
print('CONFIRMATORY CELLS  (variance-composition reversion, next 60m)')
print('=' * 92)
OUT = {}
ps = []
for name, sel in CELLS.items():
    ev = build(sel)
    s = M.strat_stats if False else None
    g = np.array([e['gross'] for e in ev])
    R = np.array([e['R'] for e in ev])
    dd = [e['day'] for e in ev]
    st = g - COST_S
    base = g - COST_B
    lo_ = -st[st < 0].sum()
    pfS = st[st > 0].sum() / lo_ if lo_ > 0 else float('inf')
    lo_ = -base[base < 0].sum()
    pfB = base[base > 0].sum() / lo_ if lo_ > 0 else float('inf')
    _, cl, ch = M.day_boot_mean(st, dd, 10000, 20260910)
    ud = sorted(set(dd))
    di = {x: k for k, x in enumerate(ud)}
    dof = np.array([di[x] for x in dd])
    rng = np.random.default_rng(20260911)
    obs = g.mean()
    cnt = sum(1 for _ in range(10000)
              if (g * rng.choice([-1., 1.], len(ud))[dof]).mean() >= obs)
    p = (cnt + 1) / 10001
    ps.append(p)
    w, l = st[st > 0], st[st < 0]
    payoff = w.mean() / -l.mean() if len(w) and len(l) else float('nan')
    byy = collections.defaultdict(list)
    for e in ev:
        byy[e['day'][:4]].append(e['gross'] - COST_S)
    ypos = sum(1 for v in byy.values() if np.mean(v) > 0)
    OUT[name] = dict(n=len(ev), days=len(ud), gross=float(g.mean()),
                     base=float(base.mean()), stressed=float(st.mean()),
                     base_R=float((base / R).mean()),
                     pf_base=float(pfB), pf_stressed=float(pfS),
                     win=float((base > 0).mean()), payoff=float(payoff),
                     ci=[cl, ch], perm_p=p, years_pos='%d/%d' % (ypos, len(byy)),
                     years={y: (len(v), float(np.mean(v))) for y, v in sorted(byy.items())})
    print('%-11s n %5d days %4d  gross %+6.3f base %+6.3f stressed %+6.3f pt  '
          'PF %5.3f/%5.3f  win %4.1f%%  payoff %4.2f'
          % (name, len(ev), len(ud), g.mean(), base.mean(), st.mean(),
             pfB, pfS, 100 * (base > 0).mean(), payoff))
    print('            CI[%+6.3f,%+6.3f]  perm p %.4f  years+ %d/%d  %s'
          % (cl, ch, p, ypos, len(byy),
             ' '.join('%s:%+.2f' % (y, np.mean(v)) for y, v in sorted(byy.items()))))

qs = M.bh(ps)
print('\nBH:', ' '.join('%s q=%.4f%s' % (n, q, ' PASS' if q <= .05 else '')
                        for n, q in zip(CELLS, qs)))
for n, q in zip(CELLS, qs):
    OUT[n]['bh_q'] = q

print('\nNEIGHBORS + DELAY (stressed mean, diagnostics):')
for name, sel in NEIGH.items():
    ev = build(sel)
    st = np.mean([e['gross'] for e in ev]) - COST_S if ev else float('nan')
    OUT.setdefault('neigh', {})[name] = dict(n=len(ev), stressed=float(st))
    print('  %-8s n %5d  %+0.3f' % (name, len(ev), st))
for name, sel in CELLS.items():
    ev = build(sel, delay=1)
    st = np.mean([e['gross'] for e in ev]) - COST_S if ev else float('nan')
    OUT.setdefault('delay1', {})[name] = float(st)
    print('  %-8s delay+1  %+0.3f' % (name, st))
for name, sel in CELLS.items():
    for xm in (45, 90):
        ev = build(sel, exit_min=xm)
        st = np.mean([e['gross'] for e in ev]) - COST_S if ev else float('nan')
        OUT.setdefault('exits', {})['%s_%dm' % (name, xm)] = float(st)
        print('  %-8s exit %2dm  %+0.3f' % (name, xm, st))

# ---------------------------------------------------------------------
# descriptive extreme-time map (6 cells, own BH; never promotable)
# ---------------------------------------------------------------------
print('\n' + '=' * 92)
print('DESCRIPTIVE  -  session extreme-time map')
print('=' * 92)
hi_t, lo_t, on_sign = [], [], []
for k, d in enumerate(days):
    idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
    if len(idx) < 300 or k == 0:
        continue
    hs = [D['h'][i] for i in idx]
    ls = [D['l'][i] for i in idx]
    hi_t.append(D['mod'][idx[int(np.argmax(hs))]])
    lo_t.append(D['mod'][idx[int(np.argmin(ls))]])
    prevc = [i for i in byday[days[k - 1]] if D['mod'][i] <= 960]
    on_sign.append(1 if D['o'][idx[0]] > D['c'][prevc[-1]] else -1
                   if prevc else 0)
hi_t = np.array(hi_t); lo_t = np.array(lo_t); on_sign = np.array(on_sign)
print('  P(high in first hour) %.3f   P(low in first hour) %.3f'
      % ((hi_t <= 631).mean(), (lo_t <= 631).mean()))
print('  P(high in last hour)  %.3f   P(low in last hour)  %.3f'
      % ((hi_t >= 900).mean(), (lo_t >= 900).mean()))
print('  gap-up days:  P(low first hour) %.3f | gap-down: P(high first hour) %.3f'
      % ((lo_t[on_sign > 0] <= 631).mean(), (hi_t[on_sign < 0] <= 631).mean()))
OUT['extreme_time'] = dict(
    p_hi_first=float((hi_t <= 631).mean()), p_lo_first=float((lo_t <= 631).mean()),
    p_hi_last=float((hi_t >= 900).mean()), p_lo_last=float((lo_t >= 900).mean()))

json.dump(OUT, open(os.path.join(HERE, 'RMA_V1_RAW.json'), 'w'),
          indent=1, default=str)
print('\ndone in %.0fs' % (time.time() - t0))
