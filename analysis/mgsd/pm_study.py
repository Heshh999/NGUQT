#!/usr/bin/env python3
# ======================================================================
# MGSD-V1  9A  PREMARKET -> OPEN INFLUENCE STUDY  (freeze v1.0 §7)
# Day-level: 8 predictors (end <= 09:29 stamp) x 4 outcomes = 32 tests.
# Controls, date-shift/random-pairing placebos, negative leak control.
# ======================================================================
import os, sys, csv, json, collections
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mgsd_lib as L

G = L.load()
N = G['N']
mod, day, td = G['mod'], G['day'], G['tradedate']
o, h, l, c, v = G['o'], G['h'], G['l'], G['c'], G['v']

rows = []
volhist = collections.deque(maxlen=20)
for d in G['rth_days']:
    onf = G['overnight'].get(d)
    pr = G['prior_rth'].get(d)
    idx = G['rth_idx'][d]
    ob = [i for i in idx if mod[i] == 571]
    i1000 = [i for i in idx if mod[i] == 600]
    i1130 = [i for i in idx if mod[i] == 690]
    cb = G['closebar'].get(d)
    if (not onf or not pr or not ob or not i1000 or not i1130 or cb is None
            or onf['c0929'] is None or onf['c0800'] is None
            or onf['first'] is None or onf['n'] < 500 or pr['rng'] <= 0):
        continue
    a = G['atr15'][ob[0] - 1]
    if a != a or a <= 0:
        continue
    onrng = onf['hi'] - onf['lo']
    relvol = (onf['v0429'] / np.mean(volhist)) if len(volhist) == 20 else np.nan
    volhist.append(max(onf['v0429'], 1.0))
    op = o[ob[0]]
    or15hi = max(h[i] for i in idx if 571 <= mod[i] <= 585)
    or15lo = min(l[i] for i in idx if 571 <= mod[i] <= 585)
    brk = 0
    for i in idx:
        if 586 <= mod[i] <= 690:
            if c[i] > or15hi: brk = 1; break
            if c[i] < or15lo: brk = -1; break
    rows.append({
        'day': d, 'weekday': int(np.datetime64(d).astype('datetime64[D]')
                                 .astype(object).weekday()),
        'atr': a,
        # predictors (all known by 09:29 stamp; gap uses prior close + 09:29
        # premarket close as proxy? NO: gap uses the 09:30 open print, which
        # is NOT known at 09:29 -> frozen: PM-gap proxy = c0929 - prior close
        'p_on_ret': (onf['c0929'] - onf['first']) / a,
        'p_gap': (onf['c0929'] - pr['close']) / a,
        'p_on_rng': onrng / pr['rng'],
        'p_pm_ret': (onf['c0929'] - (onf['c0800'] if onf['c0800'] else onf['first'])) / a,
        'p_latepm_ret': (onf['c0929'] - onf['c0800']) / a,
        'p_pos_in_on': ((onf['c0929'] - onf['lo']) / onrng) if onrng > 0 else np.nan,
        'p_relvol': relvol,
        'p_extreme_time': (max(onf['hi_i'], onf['lo_i']) / onf['n']),
        # outcomes (>= 09:30)
        'o_0930_1000': (c[i1000[0]] - op) / a,
        'o_0930_1130': (c[i1130[0]] - op) / a,
        'o_open_close': (c[cb] - op) / a,
        'o_or15_break': brk,
        # leak negative control: the outcome itself
        'p_LEAK': (c[i1000[0]] - op) / a})

D = rows
nd = len(D)
preds = ['p_on_ret', 'p_gap', 'p_on_rng', 'p_pm_ret', 'p_latepm_ret',
         'p_pos_in_on', 'p_relvol', 'p_extreme_time']
outs = ['o_0930_1000', 'o_0930_1130', 'o_open_close', 'o_or15_break']
X = {p: np.array([r[p] for r in D]) for p in preds + ['p_LEAK']}
Y = {q: np.array([r[q] for r in D]) for q in outs}
WD = np.array([r['weekday'] for r in D])
rng = np.random.default_rng(L.SEED)


def spear(a, b):
    m = ~np.isnan(a) & ~np.isnan(b)
    if m.sum() < 50:
        return np.nan, 0
    ra = np.argsort(np.argsort(a[m])); rb = np.argsort(np.argsort(b[m]))
    return float(np.corrcoef(ra, rb)[0, 1]), int(m.sum())


def block_perm_p(a, b, obs, iters=2000, block=5):
    """Blocked permutation: circularly shift predictor by random multiples
    of `block` days."""
    m = ~np.isnan(a) & ~np.isnan(b)
    aa, bb = a[m], b[m]
    n = len(aa)
    hits = 0
    for _ in range(iters):
        s = int(rng.integers(1, n // block)) * block
        rho, _n = spear(np.roll(aa, s), bb)
        if abs(rho) >= abs(obs):
            hits += 1
    return (1 + hits) / (iters + 1.0)


res = []
for p in preds:
    for q_ in outs:
        rho, n_ = spear(X[p], Y[q_])
        pp = block_perm_p(X[p], Y[q_], rho) if rho == rho else np.nan
        # controls: residualize outcome on gap + on_ret + on_rng + relvol +
        # weekday dummies (excluding the predictor itself if in controls)
        ctrl = [cc for cc in ('p_gap', 'p_on_ret', 'p_on_rng', 'p_relvol')
                if cc != p]
        m = ~np.isnan(X[p]) & ~np.isnan(Y[q_])
        for cc in ctrl:
            m &= ~np.isnan(X[cc])
        rho_r = np.nan
        if m.sum() > 100:
            A = np.column_stack([np.ones(m.sum())] +
                                [X[cc][m] for cc in ctrl] +
                                [(WD[m] == w).astype(float) for w in range(4)])
            beta, *_ = np.linalg.lstsq(A, Y[q_][m], rcond=None)
            resid = Y[q_][m] - A @ beta
            rho_r, _ = spear(X[p][m], resid)
        # placebos
        sh1, _ = spear(X[p][:-1], Y[q_][1:])
        sh5, _ = spear(X[p][:-5], Y[q_][5:])
        rp = []
        m2 = ~np.isnan(X[p]) & ~np.isnan(Y[q_])
        av, bv = X[p][m2], Y[q_][m2]
        for _ in range(200):
            rp.append(spear(av, bv[rng.permutation(len(bv))])[0])
        res.append({'predictor': p, 'outcome': q_, 'n': n_,
                    'spearman': rho, 'perm_p': pp,
                    'resid_spearman': rho_r,
                    'retention': (rho_r / rho) if rho and rho == rho and rho_r == rho_r else np.nan,
                    'shift1': sh1, 'shift5': sh5,
                    'randpair_absmean': float(np.nanmean(np.abs(rp)))})

# BH within study (32 tests)
pv = np.array([r['perm_p'] if r['perm_p'] == r['perm_p'] else 1.0 for r in res])
order = np.argsort(pv); qv = np.empty(len(pv)); prev = 1.0
for rank in range(len(pv) - 1, -1, -1):
    i = order[rank]
    prev = min(prev, len(pv) * pv[i] / (rank + 1))
    qv[i] = prev
for r, q_ in zip(res, qv):
    r['bh_q'] = float(q_)

# leak negative control
leak_rho, _ = spear(X['p_LEAK'], Y['o_0930_1000'])
leak_ok = abs(leak_rho) > 0.99

with open(os.path.join(HERE, 'MGSD_V1_PREMARKET_OPEN_RESULTS.csv'), 'w',
          newline='') as f:
    w = csv.DictWriter(f, fieldnames=list(res[0].keys()))
    w.writeheader()
    for r in res:
        w.writerow({k: ('%.4f' % v if isinstance(v, float) else v)
                    for k, v in r.items()})
print('days %d   tests %d   leak-control detected: %s (rho=%.3f)'
      % (nd, len(res), leak_ok, leak_rho))
sig = [r for r in res if r['bh_q'] <= 0.05]
print('BH q<=0.05 cells: %d' % len(sig))
for r in sig:
    print('  %-16s -> %-13s rho %+.3f  q %.4f  resid %+.3f  sh1 %+.3f'
          % (r['predictor'], r['outcome'], r['spearman'], r['bh_q'],
             r['resid_spearman'], r['shift1']))
json.dump({'days': nd, 'leak_ok': bool(leak_ok), 'n_sig': len(sig)},
          open(os.path.join(HERE, 'pm_summary.json'), 'w'))
