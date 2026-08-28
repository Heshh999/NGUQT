#!/usr/bin/env python3
# ======================================================================
# MTNAD-V1  -  FROZEN ONE-SHOT RUN  (duration / hazard / renewal)
# Protocol: MTNAD_V1_PROTOCOL.md, frozen at commit 7deabd8 BEFORE any
# outcome. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. NO ORDERS.
# ======================================================================
import collections
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mtf'))

COST_B, COST_S = 0.87, 1.305
STAMPS = [631, 661, 691, 721, 751, 781, 811, 841, 871]
SEED_BOOT, SEED_PERM, SEED_MC = 20260920, 20260921, 20260922


def q7(v, q):
    return float(np.quantile(np.asarray(v, float), q, method='linear'))


# ---------------------------------------------------------------------
# age primitives (unit-tested in tests_mtnad.py)
# ---------------------------------------------------------------------
def running_ages(em, h, l):
    """Running (anchored) extreme refresh ages. Refresh bar = most
    recent bar whose high equals the running max (ties refresh).
    Returns (age_hi, age_lo) arrays in em units."""
    n = len(em)
    age_hi = np.zeros(n)
    age_lo = np.zeros(n)
    mx, mn = -np.inf, np.inf
    ih = il = 0
    for i in range(n):
        if h[i] >= mx:
            mx, ih = h[i], i
        if l[i] <= mn:
            mn, il = l[i], i
        age_hi[i] = em[i] - em[ih]
        age_lo[i] = em[i] - em[il]
    return age_hi, age_lo


def vol_ages(em, h, l, v):
    """Session extreme ages measured in cumulative traded volume
    strictly after the refresh bar (refresh bar's own volume excluded)."""
    n = len(em)
    cv = np.concatenate([[0.0], np.cumsum(np.asarray(v, float))])
    va_hi = np.zeros(n)
    va_lo = np.zeros(n)
    mx, mn = -np.inf, np.inf
    ih = il = 0
    for i in range(n):
        if h[i] >= mx:
            mx, ih = h[i], i
        if l[i] <= mn:
            mn, il = l[i], i
        va_hi[i] = cv[i + 1] - cv[ih + 1]
        va_lo[i] = cv[i + 1] - cv[il + 1]
    return va_hi, va_lo


def rolling_extreme_ages(em, h, l, window):
    """Rolling-window extreme refresh ages over trailing `window` em
    minutes (bars j with em[i]-em[j] < window, j<=i). Monotonic deques;
    on ties the LATER bar is the refresh bar. Returns (age_hi, age_lo)."""
    n = len(em)
    age_hi = np.full(n, np.nan)
    age_lo = np.full(n, np.nan)
    dq_h = collections.deque()   # indices, h strictly decreasing
    dq_l = collections.deque()   # indices, l strictly increasing
    for i in range(n):
        while dq_h and h[dq_h[-1]] <= h[i]:
            dq_h.pop()
        dq_h.append(i)
        while dq_l and l[dq_l[-1]] >= l[i]:
            dq_l.pop()
        dq_l.append(i)
        while dq_h and em[dq_h[0]] <= em[i] - window:
            dq_h.popleft()
        while dq_l and em[dq_l[0]] <= em[i] - window:
            dq_l.popleft()
        age_hi[i] = em[i] - em[dq_h[0]]
        age_lo[i] = em[i] - em[dq_l[0]]
    return age_hi, age_lo


def daily_dh_dl(dhigh, dlow, t):
    """At the close of day index t-1: DH = trade-days since the most
    recent day among the last 20 (t-20..t-1) whose high equals that
    window's max; DL likewise for lows. Requires t >= 20."""
    w_h = dhigh[t - 20:t]
    w_l = dlow[t - 20:t]
    mh = max(w_h)
    ml = min(w_l)
    sh = max(k for k in range(20) if w_h[k] == mh)
    sl = max(k for k in range(20) if w_l[k] == ml)
    return 19 - sh, 19 - sl


def race(D, bars_idx, j0, exit_min, dirv, stop_dist):
    """House race: stop-first same-bar ambiguity, gap-through at worse
    open, exit at open of the bar exit_min minutes after entry."""
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


# ---------------------------------------------------------------------
def main():
    import mtf_lib as M
    t0 = time.time()
    D = M.load()
    N = len(D['c'])
    print('MTNAD-V1 one-shot  DEV %s..%s  bars %d'
          % (min(D['day']), max(D['day']), N))

    byday = collections.defaultdict(list)
    for i in range(N):
        byday[D['day'][i]].append(i)
    days = sorted(byday)

    # ATR20 on 1m (contiguous TR), house convention
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

    # S2 rolling-240m ages over the full bar array
    em_all = np.array(D['em'], dtype=float)
    h_all = np.array(D['h'], float)
    l_all = np.array(D['l'], float)
    s2_hi, s2_lo = rolling_extreme_ages(em_all, h_all, l_all, 240)

    # ------------------------------------------------------------------
    # intraday features per scale: (day, stamp, idx, AR)
    # ------------------------------------------------------------------
    feat = {'S1': [], 'S2': [], 'S1V': []}
    disp60 = {}                     # (day,stamp) -> trailing-60m displacement
    for d in days:
        idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
        if not idx:
            continue
        pos = {D['mod'][i]: i for i in idx}
        em_d = np.array([D['em'][i] for i in idx], float)
        h_d = np.array([D['h'][i] for i in idx], float)
        l_d = np.array([D['l'][i] for i in idx], float)
        v_d = np.array([D['v'][i] for i in idx], float)
        a_hi, a_lo = running_ages(em_d, h_d, l_d)
        va_hi, va_lo = vol_ages(em_d, h_d, l_d, v_d)
        kpos = {D['mod'][i]: k for k, i in enumerate(idx)}
        for m in STAMPS:
            if m not in pos:
                continue
            k = kpos[m]
            i = pos[m]
            s = a_hi[k] + a_lo[k]
            if s > 0:
                feat['S1'].append((d, m, i, (a_lo[k] - a_hi[k]) / s))
            s = va_hi[k] + va_lo[k]
            if s > 0:
                feat['S1V'].append((d, m, i, (va_lo[k] - va_hi[k]) / s))
            s = s2_hi[i] + s2_lo[i]
            if s == s and s > 0:
                feat['S2'].append((d, m, i, (s2_lo[i] - s2_hi[i]) / s))
            # displacement benchmark: close now minus close ~60m ago
            ref = [j for j in idx if D['mod'][j] <= m - 60]
            base_i = ref[-1] if ref else idx[0]
            disp60[(d, m)] = D['c'][i] - D['c'][base_i]
    for sc in feat:
        print('%s features %d' % (sc, len(feat[sc])))

    # daily series (RTH)
    drow = []                       # (day, open, close, high, low)
    for d in days:
        idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
        if not idx:
            continue
        drow.append((d, D['o'][idx[0]], D['c'][idx[-1]],
                     max(D['h'][i] for i in idx), min(D['l'][i] for i in idx),
                     idx))
    dhigh = [r[3] for r in drow]
    dlow = [r[4] for r in drow]
    dclose = [r[2] for r in drow]
    dfeat = []                      # (t, day, ARd, disp20_sign)
    for t in range(21, len(drow)):
        dh, dl = daily_dh_dl(dhigh, dlow, t)
        s = dh + dl
        if s == 0:
            continue
        ard = (dl - dh) / s
        d20 = dclose[t - 1] - dclose[t - 21]
        dfeat.append((t, drow[t][0], ard, 1 if d20 >= 0 else -1))
    print('S3 daily features %d' % len(dfeat))

    # ------------------------------------------------------------------
    # causal thresholds: pooled prior-250-day values, floors per protocol
    # ------------------------------------------------------------------
    QS_I = [0.05, 0.10, 0.15, 0.85, 0.90, 0.95]
    thr = {sc: {} for sc in ('S1', 'S2', 'S1V')}
    for sc in ('S1', 'S2', 'S1V'):
        byd = collections.defaultdict(list)
        for f in feat[sc]:
            byd[f[0]].append(f[3])
        pool = collections.deque(maxlen=250)
        for d in days:
            flat = [x for chunk in pool for x in chunk]
            if len(flat) >= 1000:
                thr[sc][d] = {q: q7(flat, q) for q in QS_I}
            if d in byd:
                pool.append(byd[d])
    QS_D = [0.15, 0.20, 0.25, 0.75, 0.80, 0.85]
    thr_d = {}
    pool = collections.deque(maxlen=250)
    for t, d, ard, _ in dfeat:
        if len(pool) >= 200:
            vals = list(pool)
            thr_d[d] = {q: q7(vals, q) for q in QS_D}
        pool.append(ard)

    byd_feat = {sc: collections.defaultdict(list) for sc in feat}
    for sc in feat:
        for f in feat[sc]:
            byd_feat[sc][f[0]].append(f)

    # ------------------------------------------------------------------
    def build(sc, sel, exit_min=60, delay=0):
        """Per-cell standalone build, 60m cooldown (house convention)."""
        ev = []
        for d in days:
            if d not in thr[sc] or d not in byd_feat[sc]:
                continue
            th = thr[sc][d]
            idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
            ipos = {i: k for k, i in enumerate(idx)}
            next_ok = 0
            for f in sorted(byd_feat[sc][d], key=lambda x: x[1]):
                _, m, ib, ar = f
                if m < next_ok:
                    continue
                dirv = sel(ar, th)
                if dirv == 0:
                    continue
                k0 = ipos.get(ib)
                if k0 is None or k0 + 1 + delay >= len(idx):
                    continue
                sd = 3.0 * atr[idx[k0]]
                if not (sd == sd) or sd <= 0:
                    continue
                g, kind = race(D, idx, k0 + 1 + delay, exit_min, dirv, sd)
                ev.append(dict(day=d, gross=g, R=sd, kind=kind, dir=dirv,
                               disp=disp60[(d, m)]))
                next_ok = m + 60
        return ev

    def build_day(sel, delay=False):
        ev = []
        for t, d, ard, d20 in dfeat:
            if d not in thr_d:
                continue
            dirv = sel(ard, thr_d[d])
            if dirv == 0:
                continue
            _, o, c, _, _, idx = drow[t]
            ep = o
            if delay:
                late = [i for i in idx if D['mod'][i] >= 601]
                if not late:
                    continue
                ep = D['o'][late[0]]
            ev.append(dict(day=d, gross=dirv * (c - ep), R=float('nan'),
                           kind='DAY', dir=dirv, disp=d20))
        return ev

    CELLS = {
        'C1_S1_fresh_hi_L':  ('S1', lambda a, t: 1 if a >= t[0.90] else 0),
        'C2_S1_fresh_lo_S':  ('S1', lambda a, t: -1 if a <= t[0.10] else 0),
        'C3_S2_fresh_hi_L':  ('S2', lambda a, t: 1 if a >= t[0.90] else 0),
        'C4_S2_fresh_lo_S':  ('S2', lambda a, t: -1 if a <= t[0.10] else 0),
        'C5_S1V_fresh_hi_L': ('S1V', lambda a, t: 1 if a >= t[0.90] else 0),
        'C6_S1V_fresh_lo_S': ('S1V', lambda a, t: -1 if a <= t[0.10] else 0),
    }
    DAY_CELLS = {
        'C7_S3_fresh_hi_L': lambda a, t: 1 if a >= t[0.80] else 0,
        'C8_S3_fresh_lo_S': lambda a, t: -1 if a <= t[0.20] else 0,
    }
    NEIGH = {
        'C1_q85': ('S1', lambda a, t: 1 if a >= t[0.85] else 0),
        'C1_q95': ('S1', lambda a, t: 1 if a >= t[0.95] else 0),
        'C2_q15': ('S1', lambda a, t: -1 if a <= t[0.15] else 0),
        'C2_q05': ('S1', lambda a, t: -1 if a <= t[0.05] else 0),
        'C3_q85': ('S2', lambda a, t: 1 if a >= t[0.85] else 0),
        'C3_q95': ('S2', lambda a, t: 1 if a >= t[0.95] else 0),
        'C4_q15': ('S2', lambda a, t: -1 if a <= t[0.15] else 0),
        'C4_q05': ('S2', lambda a, t: -1 if a <= t[0.05] else 0),
        'C5_q85': ('S1V', lambda a, t: 1 if a >= t[0.85] else 0),
        'C5_q95': ('S1V', lambda a, t: 1 if a >= t[0.95] else 0),
        'C6_q15': ('S1V', lambda a, t: -1 if a <= t[0.15] else 0),
        'C6_q05': ('S1V', lambda a, t: -1 if a <= t[0.05] else 0),
    }
    DAY_NEIGH = {
        'C7_q75': lambda a, t: 1 if a >= t[0.75] else 0,
        'C7_q85': lambda a, t: 1 if a >= t[0.85] else 0,
        'C8_q25': lambda a, t: -1 if a <= t[0.25] else 0,
        'C8_q15': lambda a, t: -1 if a <= t[0.15] else 0,
    }

    def freq_stats(ev):
        """Trades/week over complete eligible weeks (>=4 eligible days)."""
        import datetime
        elig_days = sorted(set(d for sc in thr for d in thr[sc])
                           | set(thr_d))
        wk = lambda d: datetime.date(*map(int, d.split('-'))).isocalendar()[:2]
        days_per_week = collections.Counter(wk(d) for d in elig_days)
        complete = {w for w, c in days_per_week.items() if c >= 4}
        tcount = collections.Counter(wk(e['day']) for e in ev)
        counts = [tcount.get(w, 0) for w in sorted(complete)]
        counts = np.array(counts, float)
        return dict(weeks=len(counts), mean=float(counts.mean()),
                    median=float(np.median(counts)),
                    zero=float((counts == 0).mean()),
                    one=float((counts == 1).mean()),
                    two=float((counts == 2).mean()),
                    three_plus=float((counts >= 3).mean()),
                    ge1=float((counts >= 1).mean()))

    def stats(name, ev, is_day=False):
        assert len(ev) > 0, 'cell %s produced zero events' % name
        g = np.array([e['gross'] for e in ev])
        dd = [e['day'] for e in ev]
        st = g - COST_S
        base = g - COST_B
        lo_ = -st[st < 0].sum()
        pfS = st[st > 0].sum() / lo_ if lo_ > 0 else float('inf')
        lo_ = -base[base < 0].sum()
        pfB = base[base > 0].sum() / lo_ if lo_ > 0 else float('inf')
        import mtf_lib as M
        _, cl, ch = M.day_boot_mean(st, dd, 10000, SEED_BOOT)
        ud = sorted(set(dd))
        di = {x: k for k, x in enumerate(ud)}
        dof = np.array([di[x] for x in dd])
        rng = np.random.default_rng(SEED_PERM)
        obs = g.mean()
        cnt = sum(1 for _ in range(10000)
                  if (g * rng.choice([-1., 1.], len(ud))[dof]).mean() >= obs)
        p = (cnt + 1) / 10001
        w, l = st[st > 0], st[st < 0]
        payoff = w.mean() / -l.mean() if len(w) and len(l) else float('nan')
        byy = collections.defaultdict(list)
        for e in ev:
            byy[e['day'][:4]].append(e['gross'] - COST_S)
        years = {y: float(np.mean(v)) for y, v in sorted(byy.items())}
        ypos = sum(1 for v in years.values() if v > 0)
        # domination: largest positive year's share of total (if total>0)
        ysum = {y: sum(v) for y, v in byy.items()}
        tot = sum(ysum.values())
        dom = max(ysum.values()) / tot if tot > 0 else float('nan')
        # best-day and top-1% removal
        dsum = collections.defaultdict(float)
        for e in ev:
            dsum[e['day']] += e['gross'] - COST_S
        bd = max(dsum, key=dsum.get)
        st_nobest = np.array([e['gross'] - COST_S for e in ev
                              if e['day'] != bd])
        k1 = max(1, int(0.01 * len(st)))
        st_notop = np.sort(st)[:-k1]
        # incrementality strata by displacement benchmark sign
        stp = np.array([e['gross'] - COST_S for e in ev if e['disp'] >= 0])
        stn = np.array([e['gross'] - COST_S for e in ev if e['disp'] < 0])
        # R-based EV (intraday only)
        if not is_day:
            R = np.array([e['R'] for e in ev])
            evR_b = float((base / R).mean())
            evR_s = float((st / R).mean())
        else:
            evR_b = evR_s = float('nan')
        fr = freq_stats(ev)
        out = dict(n=len(ev), days=len(ud), gross=float(g.mean()),
                   base=float(base.mean()), stressed=float(st.mean()),
                   pf_base=float(pfB), pf_stressed=float(pfS),
                   win=float((st > 0).mean()), payoff=float(payoff),
                   ci=[cl, ch], perm_p=float(p),
                   years=years, years_pos='%d/%d' % (ypos, len(years)),
                   domination=float(dom),
                   drop_best_day=float(st_nobest.mean()),
                   drop_top1pct=float(st_notop.mean()),
                   incr_pos=float(stp.mean()) if len(stp) else float('nan'),
                   incr_neg=float(stn.mean()) if len(stn) else float('nan'),
                   n_incr=[int(len(stp)), int(len(stn))],
                   evR_base=evR_b, evR_stressed=evR_s, freq=fr)
        print('%-18s n %5d days %4d  gross %+.3f base %+.3f stressed %+.3f'
              '  PF %.3f/%.3f  win %.1f%%  payoff %.2f'
              % (name, out['n'], out['days'], out['gross'], out['base'],
                 out['stressed'], pfB, pfS, 100 * out['win'], payoff))
        print('    CI[%+.3f,%+.3f]  perm p %.4f  years+ %s  dom %.2f'
              '  dropBest %+.3f  dropTop1 %+.3f  incr[%+.3f|%+.3f]'
              % (cl, ch, p, out['years_pos'], dom, out['drop_best_day'],
                 out['drop_top1pct'], out['incr_pos'], out['incr_neg']))
        print('    freq: %.2f/wk med %.1f  zero %.1f%%  >=1 %.1f%%'
              '  (%d complete weeks)  years: %s'
              % (fr['mean'], fr['median'], 100 * fr['zero'], 100 * fr['ge1'],
                 fr['weeks'],
                 ' '.join('%s:%+.2f' % (y, v) for y, v in years.items())))
        return out

    print('\n' + '=' * 92)
    print('CONFIRMATORY CELLS  (continuation toward the fresh extreme)')
    print('=' * 92)
    OUT = {}
    EVS = {}
    for name, (sc, sel) in CELLS.items():
        EVS[name] = build(sc, sel)
        OUT[name] = stats(name, EVS[name])
    for name, sel in DAY_CELLS.items():
        EVS[name] = build_day(sel)
        OUT[name] = stats(name, EVS[name], is_day=True)

    # BH across the 8 cells
    names = list(CELLS) + list(DAY_CELLS)
    ps = [(OUT[n]['perm_p'], n) for n in names]
    srt = sorted(ps)
    mq = 1.0
    qs = {}
    for rank in range(len(srt), 0, -1):
        pv, n = srt[rank - 1]
        mq = min(mq, pv * len(srt) / rank)
        qs[n] = mq
    for n in names:
        OUT[n]['bh_q'] = qs[n]
    print('\nBH: ' + '  '.join('%s q=%.4f' % (n, qs[n]) for n in names))

    print('\nNEIGHBORS + DELAY + EXITS (stressed mean, diagnostics):')
    NOUT = {}
    for nm, (sc, sel) in NEIGH.items():
        ev = build(sc, sel)
        m = float(np.mean([e['gross'] for e in ev]) - COST_S) if ev else float('nan')
        NOUT[nm] = dict(n=len(ev), stressed=m)
        print('  %-22s n %5d  %+.3f' % (nm, len(ev), m))
    for nm, sel in DAY_NEIGH.items():
        ev = build_day(sel)
        m = float(np.mean([e['gross'] for e in ev]) - COST_S) if ev else float('nan')
        NOUT[nm] = dict(n=len(ev), stressed=m)
        print('  %-22s n %5d  %+.3f' % (nm, len(ev), m))
    for name, (sc, sel) in CELLS.items():
        ev = build(sc, sel, delay=1)
        m = float(np.mean([e['gross'] for e in ev]) - COST_S) if ev else float('nan')
        NOUT[name + '_delay1'] = dict(n=len(ev), stressed=m)
        print('  %-22s n %5d  %+.3f' % (name + ' delay+1', len(ev), m))
        for xm in (45, 90):
            ev = build(sc, sel, exit_min=xm)
            m = float(np.mean([e['gross'] for e in ev]) - COST_S) if ev else float('nan')
            NOUT['%s_exit%d' % (name, xm)] = dict(n=len(ev), stressed=m)
            print('  %-22s n %5d  %+.3f' % ('%s exit %dm' % (name, xm),
                                            len(ev), m))
    for name, sel in DAY_CELLS.items():
        ev = build_day(sel, delay=True)
        m = float(np.mean([e['gross'] for e in ev]) - COST_S) if ev else float('nan')
        NOUT[name + '_open30'] = dict(n=len(ev), stressed=m)
        print('  %-22s n %5d  %+.3f' % (name + ' open+30m', len(ev), m))

    # ------------------------------------------------------------------
    # gate evaluation + MC only for full passers
    # ------------------------------------------------------------------
    def gates(n, o, is_day):
        g = []
        g.append(('n>=200', o['n'] >= 200))
        g.append(('days>=60', o['days'] >= 60))
        g.append(('base>0', o['base'] > 0))
        g.append(('stressed>0', o['stressed'] > 0))
        g.append(('PF_base>=1.30', o['pf_base'] >= 1.30))
        g.append(('PF_stressed>=1.15', o['pf_stressed'] >= 1.15))
        if not is_day:
            g.append(('EV_base>=+0.10R', o['evR_base'] >= 0.10))
            g.append(('EV_stressed>=+0.05R', o['evR_stressed'] >= 0.05))
        g.append(('CI_LB>0', o['ci'][0] > 0))
        g.append(('p<=0.05', o['perm_p'] <= 0.05))
        g.append(('q<=0.05', o['bh_q'] <= 0.05))
        ny = len(o['years'])
        g.append(('years_pos>=%d' % max(ny - 1, 6),
                  int(o['years_pos'].split('/')[0]) >= max(ny - 1, 6)))
        g.append(('domination<=0.50',
                  o['domination'] == o['domination'] and o['domination'] <= 0.50))
        g.append(('drop_best_day>0', o['drop_best_day'] > 0))
        g.append(('drop_top1pct>0', o['drop_top1pct'] > 0))
        g.append(('incrementality_both_strata',
                  o['incr_pos'] > 0 and o['incr_neg'] > 0))
        dl = NOUT.get(n + ('_open30' if is_day else '_delay1'))
        g.append(('delay_positive', bool(dl and dl['stressed'] > 0)))
        if is_day:
            nb = [NOUT[k] for k in DAY_NEIGH if k.startswith(n.split('_')[0])]
        else:
            nb = [NOUT[k] for k in NEIGH if k.startswith(n.split('_')[0])]
        g.append(('neighbors_majority_positive',
                  sum(1 for x in nb if x['stressed'] > 0) > len(nb) / 2))
        g.append(('freq>=1.0/wk', o['freq']['mean'] >= 1.0))
        g.append(('weeks_ge1>=60%', o['freq']['ge1'] >= 0.60))
        return g

    print('\n' + '=' * 92)
    print('GATE EVALUATION')
    print('=' * 92)
    passers = []
    for n in names:
        is_day = n in DAY_CELLS
        gl = gates(n, OUT[n], is_day)
        fails = [nm for nm, ok in gl if not ok]
        OUT[n]['gates_failed'] = fails
        ok = not fails
        if ok:
            passers.append(n)
        print('%-18s %s%s' % (n, 'PASS' if ok else 'FAIL: ',
                              '' if ok else ' '.join(fails)))

    for n in passers:
        print('\nMONTE CARLO (100k day-block paths, 5y-equivalent): %s' % n)
        dsum = collections.defaultdict(float)
        for e in EVS[n]:
            dsum[e['day']] += e['gross'] - COST_S
        dv = np.array(list(dsum.values()))
        rng = np.random.default_rng(SEED_MC)
        npaths, plen, blk = 100000, 1260, 5
        nblk = plen // blk
        starts = rng.integers(0, len(dv), size=(npaths, nblk))
        idxm = (starts[:, :, None] + np.arange(blk)[None, None, :]) % len(dv)
        paths = dv[idxm].reshape(npaths, plen)
        cum = paths.cumsum(axis=1)
        term = cum[:, -1]
        peak = np.maximum.accumulate(cum, axis=1)
        mdd = (peak - cum).max(axis=1)
        OUT[n]['mc'] = dict(
            term_pct=[float(np.percentile(term, x)) for x in (1, 5, 25, 50, 75, 95, 99)],
            mdd_pct=[float(np.percentile(mdd, x)) for x in (50, 75, 95, 99)],
            p_negative=float((term <= 0).mean()))
        print('  terminal pts pct(1/5/25/50/75/95/99): %s' %
              ['%.0f' % x for x in OUT[n]['mc']['term_pct']])
        print('  maxDD pts pct(50/75/95/99): %s   P(neg 5y) %.4f' %
              (['%.0f' % x for x in OUT[n]['mc']['mdd_pct']],
               OUT[n]['mc']['p_negative']))

    with open(os.path.join(HERE, 'MTNAD_V1_RAW.json'), 'w') as fh:
        json.dump(dict(cells=OUT, diagnostics=NOUT), fh, indent=1)
    print('\npassers: %s' % (passers if passers else 'NONE'))
    print('done in %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
