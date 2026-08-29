#!/usr/bin/env python3
# ======================================================================
# RNVP-V1  -  FROZEN ONE-SHOT RUN (round-number grid + volume
# participation). Protocol: RNVP_V1_PROTOCOL.md, frozen at 87b81d8
# BEFORE any outcome. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import collections
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mtf'))
sys.path.insert(0, os.path.join(HERE, '..', 'mtnad'))
from mtnad_run import race, q7  # noqa: E402  (house race, unit-tested)

COST_B, COST_S = 0.87, 1.305
SEED_BOOT, SEED_PERM, SEED_MC = 20260930, 20260931, 20260932
GRID = 100.0
EPS = 5.0
WIN = 60


def prev_window_extremes(em, h, l, w):
    """For each bar i: max high / min low over bars j<i with
    em[i]-em[j] <= w. Queried BEFORE inserting bar i (causal, excludes
    the bar itself). Returns (pmax, pmin) arrays (-inf/+inf at start)."""
    n = len(em)
    pmax = np.full(n, -np.inf)
    pmin = np.full(n, np.inf)
    dq_h = collections.deque()
    dq_l = collections.deque()
    for i in range(n):
        # expire, then query (bars < i only), then insert bar i
        while dq_h and em[dq_h[0]] < em[i] - w:
            dq_h.popleft()
        while dq_l and em[dq_l[0]] < em[i] - w:
            dq_l.popleft()
        if dq_h:
            pmax[i] = h[dq_h[0]]     # monotonic: front = window max
        if dq_l:
            pmin[i] = l[dq_l[0]]
        while dq_h and h[dq_h[-1]] <= h[i]:
            dq_h.pop()
        dq_h.append(i)
        while dq_l and l[dq_l[-1]] >= l[i]:
            dq_l.pop()
        dq_l.append(i)
    return pmax, pmin


def rnl_triggers(o, h, l, c, pmax, pmin, i, prev_ok):
    """Return list of (cell, dir) triggered at bar i. prev_ok: bar i-1
    is em-contiguous. pmax/pmin: prior-window extremes (excl. bar i)."""
    out = []
    if not prev_ok:
        return out
    # R1 touch-reject upper
    L = GRID * math.floor(h[i] / GRID)
    if c[i] < L and c[i - 1] < L and pmax[i] < L:
        out.append(('R1', -1))
    # R2 touch-reject lower
    L = GRID * math.ceil(l[i] / GRID)
    if c[i] > L and c[i - 1] > L and pmin[i] > L:
        out.append(('R2', 1))
    # R3 break upper
    L = GRID * math.floor((c[i] - EPS) / GRID)
    if c[i] >= L + EPS and c[i - 1] < L and pmax[i] < L:
        out.append(('R3', 1))
    # R4 break lower
    L = GRID * math.ceil((c[i] + EPS) / GRID)
    if c[i] <= L - EPS and c[i - 1] > L and pmin[i] > L:
        out.append(('R4', -1))
    return out


def main():
    import mtf_lib as M
    t0 = time.time()
    D = M.load()
    N = len(D['c'])
    print('RNVP-V1 one-shot  DEV %s..%s  bars %d'
          % (min(D['day']), max(D['day']), N))
    o = np.array(D['o'], float)
    h = np.array(D['h'], float)
    l = np.array(D['l'], float)
    c = np.array(D['c'], float)
    em = np.array(D['em'], float)

    byday = collections.defaultdict(list)
    for i in range(N):
        byday[D['day'][i]].append(i)
    days = sorted(byday)

    atr = np.full(N, np.nan)
    tr = np.full(N, np.nan)
    for i in range(1, N):
        if D['em'][i] - D['em'][i - 1] == 1:
            tr[i] = max(h[i] - l[i], abs(h[i] - c[i - 1]), abs(l[i] - c[i - 1]))
    alpha = 1.0 / 20
    prev = np.nan
    for i in range(N):
        if tr[i] == tr[i]:
            prev = tr[i] if prev != prev else prev + alpha * (tr[i] - prev)
        atr[i] = prev

    # ------------------------------------------------------------------
    # RNL trigger scan at frozen window + neighbor windows
    # ------------------------------------------------------------------
    PW = {}
    for w in (30, WIN, 120):
        PW[w] = prev_window_extremes(em, h, l, w)
    trig = {w: collections.defaultdict(list) for w in PW}   # w -> day -> [(mod, i, cell, dir)]
    trig_eps = {e: collections.defaultdict(list) for e in (2.5, 10.0)}
    for d in days:
        idx = byday[d]
        for i in idx:
            m = D['mod'][i]
            if not (631 <= m <= 900):
                continue
            prev_ok = i > 0 and D['em'][i] - D['em'][i - 1] == 1
            for w in PW:
                pmax, pmin = PW[w]
                for cell, dv in rnl_triggers(o, h, l, c, pmax, pmin, i, prev_ok):
                    trig[w][d].append((m, i, cell, dv))
            # eps neighbors for break cells at frozen window
            if prev_ok:
                pmax, pmin = PW[WIN]
                for e in trig_eps:
                    L = GRID * math.floor((c[i] - e) / GRID)
                    if c[i] >= L + e and c[i - 1] < L and pmax[i] < L:
                        trig_eps[e][d].append((m, i, 'R3', 1))
                    L = GRID * math.ceil((c[i] + e) / GRID)
                    if c[i] <= L - e and c[i - 1] > L and pmin[i] > L:
                        trig_eps[e][d].append((m, i, 'R4', -1))
    n_frozen = sum(len(v) for v in trig[WIN].values())
    print('RNL raw triggers (W=60): %d' % n_frozen)

    def build_rnl(cell, w=WIN, eps_src=None, exit_min=60, delay=0):
        ev = []
        src = trig_eps[eps_src] if eps_src else trig[w]
        for d in days:
            if d not in src:
                continue
            idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
            ipos = {i: k for k, i in enumerate(idx)}
            next_ok = 0
            for m, i, cl, dv in sorted(src[d]):
                if cl != cell or m < next_ok:
                    continue
                k0 = ipos.get(i)
                if k0 is None or k0 + 1 + delay >= len(idx):
                    continue
                sd = 3.0 * atr[i]
                if not (sd == sd) or sd <= 0:
                    continue
                g, kind = race(D, idx, k0 + 1 + delay, exit_min, dv, sd)
                ref = [j for j in idx if D['mod'][j] <= m - 60]
                disp = c[i] - c[ref[-1] if ref else idx[0]]
                ev.append(dict(day=d, gross=g, R=sd, kind=kind, dir=dv,
                               disp=disp))
                next_ok = m + 60
        return ev

    # ------------------------------------------------------------------
    # VTP state per day
    # ------------------------------------------------------------------
    vrow = []            # (day, S, M, absM, entry_i(list idx), thr_ok)
    v20 = collections.deque(maxlen=20)
    poolS = collections.deque(maxlen=250)
    poolAM = collections.deque(maxlen=250)
    thr_v = {}
    med_am = {}
    for d in days:
        idx = [i for i in byday[d] if 571 <= D['mod'][i] <= 960]
        am = [i for i in idx if D['mod'][i] <= 720]
        bar721 = [i for i in idx if D['mod'][i] == 721]
        if len(am) < 140 or not bar721:
            continue
        vam = float(sum(D['v'][i] for i in am))
        S = vam / np.mean(v20) if len(v20) == 20 else None
        v20.append(vam)
        if S is None:
            continue
        Mv = c[bar721[0]] - o[idx[0]]
        if Mv == 0:
            continue
        if len(poolS) >= 200:
            thr_v[d] = {q: q7(list(poolS), q)
                        for q in (0.20, 0.30, 0.40, 0.60, 0.70, 0.80)}
            med_am[d] = q7(list(poolAM), 0.50)
        poolS.append(S)
        poolAM.append(abs(Mv))
        vrow.append((d, S, Mv, bar721[0], idx))
    print('VTP eligible days %d (thresholded %d)' % (len(vrow), len(thr_v)))

    def build_vtp(sel, delay=False):
        ev = []
        for d, S, Mv, i721, idx in vrow:
            if d not in thr_v:
                continue
            dv = sel(S, Mv, thr_v[d])
            if dv == 0:
                continue
            ipos = {i: k for k, i in enumerate(idx)}
            if delay:
                late = [i for i in idx if D['mod'][i] >= 751]
                if not late:
                    continue
                ent = o[late[0]]
            else:
                k0 = ipos[i721]
                if k0 + 1 >= len(idx):
                    continue
                ent = o[idx[k0 + 1]]
            ev.append(dict(day=d, gross=dv * (c[idx[-1]] - ent),
                           R=float('nan'), kind='PM', dir=dv,
                           disp=abs(Mv) - med_am[d]))
        return ev

    RNL_CELLS = ['R1', 'R2', 'R3', 'R4']
    VTP_CELLS = {
        'V1_hivol_am_up_L':  lambda S, Mv, t: 1 if S >= t[0.70] and Mv > 0 else 0,
        'V2_hivol_am_dn_S':  lambda S, Mv, t: -1 if S >= t[0.70] and Mv < 0 else 0,
        'V3_lovol_am_up_S':  lambda S, Mv, t: -1 if S <= t[0.30] and Mv > 0 else 0,
        'V4_lovol_am_dn_L':  lambda S, Mv, t: 1 if S <= t[0.30] and Mv < 0 else 0,
    }
    VTP_NEIGH = {
        'V1_q60': lambda S, Mv, t: 1 if S >= t[0.60] and Mv > 0 else 0,
        'V1_q80': lambda S, Mv, t: 1 if S >= t[0.80] and Mv > 0 else 0,
        'V2_q60': lambda S, Mv, t: -1 if S >= t[0.60] and Mv < 0 else 0,
        'V2_q80': lambda S, Mv, t: -1 if S >= t[0.80] and Mv < 0 else 0,
        'V3_q40': lambda S, Mv, t: -1 if S <= t[0.40] and Mv > 0 else 0,
        'V3_q20': lambda S, Mv, t: -1 if S <= t[0.20] and Mv > 0 else 0,
        'V4_q40': lambda S, Mv, t: 1 if S <= t[0.40] and Mv < 0 else 0,
        'V4_q20': lambda S, Mv, t: 1 if S <= t[0.20] and Mv < 0 else 0,
    }

    elig_rnl = set(days)
    elig_vtp = set(thr_v)

    def freq_stats(ev, elig):
        import datetime
        wk = lambda dd: datetime.date(*map(int, dd.split('-'))).isocalendar()[:2]
        dpw = collections.Counter(wk(dd) for dd in sorted(elig))
        complete = {w for w, n in dpw.items() if n >= 4}
        tc = collections.Counter(wk(e['day']) for e in ev)
        cnt = np.array([tc.get(w, 0) for w in sorted(complete)], float)
        return dict(weeks=len(cnt), mean=float(cnt.mean()),
                    median=float(np.median(cnt)),
                    zero=float((cnt == 0).mean()),
                    ge1=float((cnt >= 1).mean()))

    def stats(name, ev, elig, is_day=False):
        assert len(ev) > 0, 'cell %s produced zero events' % name
        import mtf_lib as M2
        g = np.array([e['gross'] for e in ev])
        dd = [e['day'] for e in ev]
        st = g - COST_S
        base = g - COST_B
        lo_ = -st[st < 0].sum()
        pfS = st[st > 0].sum() / lo_ if lo_ > 0 else float('inf')
        lo_ = -base[base < 0].sum()
        pfB = base[base > 0].sum() / lo_ if lo_ > 0 else float('inf')
        _, cl, ch = M2.day_boot_mean(st, dd, 10000, SEED_BOOT)
        ud = sorted(set(dd))
        di = {x: k for k, x in enumerate(ud)}
        dof = np.array([di[x] for x in dd])
        rng = np.random.default_rng(SEED_PERM)
        obs = g.mean()
        cnt = sum(1 for _ in range(10000)
                  if (g * rng.choice([-1., 1.], len(ud))[dof]).mean() >= obs)
        p = (cnt + 1) / 10001
        w_, l_ = st[st > 0], st[st < 0]
        payoff = w_.mean() / -l_.mean() if len(w_) and len(l_) else float('nan')
        byy = collections.defaultdict(list)
        for e in ev:
            byy[e['day'][:4]].append(e['gross'] - COST_S)
        years = {y: float(np.mean(v)) for y, v in sorted(byy.items())}
        ypos = sum(1 for v in years.values() if v > 0)
        ysum = {y: sum(v) for y, v in byy.items()}
        tot = sum(ysum.values())
        dom = max(ysum.values()) / tot if tot > 0 else float('nan')
        dsum = collections.defaultdict(float)
        for e in ev:
            dsum[e['day']] += e['gross'] - COST_S
        bd = max(dsum, key=dsum.get)
        st_nb = np.array([e['gross'] - COST_S for e in ev if e['day'] != bd])
        k1 = max(1, int(0.01 * len(st)))
        st_nt = np.sort(st)[:-k1]
        stp = np.array([e['gross'] - COST_S for e in ev if e['disp'] >= 0])
        stn = np.array([e['gross'] - COST_S for e in ev if e['disp'] < 0])
        if not is_day:
            R = np.array([e['R'] for e in ev])
            evR_b, evR_s = float((base / R).mean()), float((st / R).mean())
        else:
            evR_b = evR_s = float('nan')
        fr = freq_stats(ev, elig)
        out = dict(n=len(ev), days=len(ud), gross=float(g.mean()),
                   base=float(base.mean()), stressed=float(st.mean()),
                   pf_base=float(pfB), pf_stressed=float(pfS),
                   win=float((st > 0).mean()), payoff=float(payoff),
                   ci=[cl, ch], perm_p=float(p), years=years,
                   years_pos='%d/%d' % (ypos, len(years)),
                   domination=float(dom),
                   drop_best_day=float(st_nb.mean()),
                   drop_top1pct=float(st_nt.mean()),
                   incr_pos=float(stp.mean()) if len(stp) else float('nan'),
                   incr_neg=float(stn.mean()) if len(stn) else float('nan'),
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
              '  (%d wks)  years: %s'
              % (fr['mean'], fr['median'], 100 * fr['zero'], 100 * fr['ge1'],
                 fr['weeks'],
                 ' '.join('%s:%+.2f' % (y, v) for y, v in years.items())))
        return out

    print('\n' + '=' * 92)
    print('CONFIRMATORY CELLS')
    print('=' * 92)
    OUT, EVS = {}, {}
    for cl_ in RNL_CELLS:
        EVS[cl_] = build_rnl(cl_)
        OUT[cl_] = stats(cl_, EVS[cl_], elig_rnl)
    for name, sel in VTP_CELLS.items():
        EVS[name] = build_vtp(sel)
        OUT[name] = stats(name, EVS[name], elig_vtp, is_day=True)

    # strategy-level frequency for the VTP pairs (frozen pairing)
    for sn, pair in (('V-HI', ('V1_hivol_am_up_L', 'V2_hivol_am_dn_S')),
                     ('V-LO', ('V3_lovol_am_up_S', 'V4_lovol_am_dn_L'))):
        ev = EVS[pair[0]] + EVS[pair[1]]
        fr = freq_stats(ev, elig_vtp)
        stm = float(np.mean([e['gross'] for e in ev]) - COST_S)
        OUT[sn] = dict(n=len(ev), stressed=stm, freq=fr)
        print('%-18s n %5d  stressed %+.3f  freq %.2f/wk  >=1 %.1f%%'
              % (sn, len(ev), stm, fr['mean'], 100 * fr['ge1']))

    names = RNL_CELLS + list(VTP_CELLS)
    srt = sorted((OUT[n]['perm_p'], n) for n in names)
    mq, qs = 1.0, {}
    for rank in range(len(srt), 0, -1):
        pv, n = srt[rank - 1]
        mq = min(mq, pv * len(srt) / rank)
        qs[n] = mq
    for n in names:
        OUT[n]['bh_q'] = qs[n]
    print('\nBH: ' + '  '.join('%s q=%.4f' % (n, qs[n]) for n in names))

    print('\nNEIGHBORS + DELAY + EXITS (stressed mean, diagnostics):')
    NOUT = {}

    def diag(nm, ev):
        m = float(np.mean([e['gross'] for e in ev]) - COST_S) if ev else float('nan')
        NOUT[nm] = dict(n=len(ev), stressed=m)
        print('  %-24s n %5d  %+.3f' % (nm, len(ev), m))

    for cl_ in RNL_CELLS:
        for w in (30, 120):
            diag('%s_W%d' % (cl_, w), build_rnl(cl_, w=w))
        if cl_ in ('R3', 'R4'):
            for e_ in (2.5, 10.0):
                diag('%s_eps%g' % (cl_, e_), build_rnl(cl_, eps_src=e_))
        diag(cl_ + '_delay', build_rnl(cl_, delay=1))
        for xm in (45, 90):
            diag('%s_exit%d' % (cl_, xm), build_rnl(cl_, exit_min=xm))
    for name, sel in VTP_NEIGH.items():
        diag(name, build_vtp(sel))
    for name, sel in VTP_CELLS.items():
        diag(name + '_delay', build_vtp(sel, delay=True))

    print('\n' + '=' * 92)
    print('GATE EVALUATION')
    print('=' * 92)

    def gates(n, o_, is_day):
        g = [('n>=200', o_['n'] >= 200), ('days>=60', o_['days'] >= 60),
             ('base>0', o_['base'] > 0), ('stressed>0', o_['stressed'] > 0),
             ('PF_base>=1.30', o_['pf_base'] >= 1.30),
             ('PF_stressed>=1.15', o_['pf_stressed'] >= 1.15)]
        if not is_day:
            g += [('EV_base>=+0.10R', o_['evR_base'] >= 0.10),
                  ('EV_stressed>=+0.05R', o_['evR_stressed'] >= 0.05)]
        g += [('CI_LB>0', o_['ci'][0] > 0), ('p<=0.05', o_['perm_p'] <= 0.05),
              ('q<=0.05', o_['bh_q'] <= 0.05)]
        ny = len(o_['years'])
        g.append(('years_pos>=%d' % max(ny - 1, 6),
                  int(o_['years_pos'].split('/')[0]) >= max(ny - 1, 6)))
        g.append(('domination<=0.50',
                  o_['domination'] == o_['domination'] and o_['domination'] <= 0.50))
        g.append(('drop_best_day>0', o_['drop_best_day'] > 0))
        g.append(('drop_top1pct>0', o_['drop_top1pct'] > 0))
        g.append(('incrementality_both_strata',
                  o_['incr_pos'] > 0 and o_['incr_neg'] > 0))
        dl = NOUT.get(n + '_delay')
        g.append(('delay_positive', bool(dl and dl['stressed'] > 0)))
        nb = [v for k, v in NOUT.items()
              if k.startswith(n.split('_')[0] + '_') and
              ('_W' in k or '_eps' in k or '_q' in k)]
        g.append(('neighbors_majority_positive',
                  sum(1 for x in nb if x['stressed'] > 0) > len(nb) / 2))
        fq = OUT['V-HI' if n in ('V1_hivol_am_up_L', 'V2_hivol_am_dn_S') else
                 'V-LO' if n in ('V3_lovol_am_up_S', 'V4_lovol_am_dn_L') else
                 n]['freq']
        g.append(('freq>=1.0/wk', fq['mean'] >= 1.0))
        g.append(('weeks_ge1>=60%', fq['ge1'] >= 0.60))
        return g

    passers = []
    for n in names:
        gl = gates(n, OUT[n], n not in RNL_CELLS)
        fails = [nm for nm, ok in gl if not ok]
        OUT[n]['gates_failed'] = fails
        if not fails:
            passers.append(n)
        print('%-18s %s%s' % (n, 'PASS' if not fails else 'FAIL: ',
                              ' '.join(fails)))

    for n in passers:
        print('\nMONTE CARLO (100k day-block paths, 5y-eq): %s' % n)
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
        print('  maxDD pct(50/75/95/99): %s   P(neg 5y) %.4f' %
              (['%.0f' % x for x in OUT[n]['mc']['mdd_pct']],
               OUT[n]['mc']['p_negative']))

    with open(os.path.join(HERE, 'RNVP_V1_RAW.json'), 'w') as fh:
        json.dump(dict(cells=OUT, diagnostics=NOUT), fh, indent=1)
    print('\npassers: %s' % (passers if passers else 'NONE'))
    print('done in %.0fs' % (time.time() - t0))


if __name__ == '__main__':
    main()
