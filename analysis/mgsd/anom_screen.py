#!/usr/bin/env python3
# MGSD-V1 anomaly screen layer: 19 family conditions x 9 horizons,
# direction-signed forward close returns, day-clustered bootstrap p,
# BH across 171. DESCRIPTIVE (report-only, frozen).
import os, sys, csv, json, collections
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mgsd_lib as L, mgsd_signals as SG

G = L.load()
G['open_bar_by_td'] = {}
mod, day, td = G['mod'], G['day'], G['tradedate']
for i in range(G['N']):
    if mod[i] == 571 and day[i] not in G['open_bar_by_td']:
        G['open_bar_by_td'][day[i]] = i
F, AUX = SG.gen_all(G)
c = G['c']; N = G['N']
HOR = [1, 3, 5, 10, 15, 30, 60, 120, 'CLOSE']
# one representative signal set per family: first frozen threshold,
# stop/exit-independent -> use the L10_T30-style key's slots for both dirs
fams = {}
for key, spec in F.items():
    fam = key.split('_')[0]
    if fam in fams or fam == 'F05BASE':
        continue
    # gather all variants of this family sharing the FIRST threshold token
    toks = key.split('_')
    sel = [k for k in F if k.split('_')[0] == fam]
    first_thr = sorted(set(k.split('_')[1] for k in sel
                           if not k.split('_')[1][0] in 'LS'))
    base = [k for k in sel if (not first_thr or
                               k.split('_')[1] == first_thr[0])]
    ev = {}
    for k in base:
        slots, dirv, sm, ex, pk, tgt = F[k]
        for j in slots:
            ev[(j, dirv)] = 1
    fams[fam] = sorted(ev)
rng = np.random.default_rng(L.SEED)
rows = []
for fam, ev in fams.items():
    if not ev:
        continue
    sl = np.array([j for j, d in ev]); dv = np.array([d for j, d in ev])
    for hz in HOR:
        if hz == 'CLOSE':
            tgt_i = np.array([G['closebar'].get(td[j], j) for j in sl])
        else:
            tgt_i = np.minimum(sl + hz, N - 1)
        ok = tgt_i > sl
        r = dv[ok] * (c[tgt_i[ok]] - c[sl[ok] - 1])
        dd = [td[j] for j in sl[ok]]
        uds = sorted(set(dd)); di = {d: k for k, d in enumerate(uds)}
        ds = np.zeros(len(uds)); dc = np.zeros(len(uds))
        for x, d0 in zip(r, dd):
            ds[di[d0]] += x; dc[di[d0]] += 1
        if len(uds) < 30:
            rows.append({'family': fam, 'horizon': str(hz), 'n': int(ok.sum()),
                         'mean_pts': float(r.mean()) if len(r) else np.nan,
                         'p': np.nan})
            continue
        idx = rng.integers(0, len(uds), size=(4000, len(uds)))
        bs = ds[idx].sum(1) / np.maximum(dc[idx].sum(1), 1)
        bs.sort()
        le = int((bs <= 0).sum()); ge = int((bs >= 0).sum())
        p = max(2 * min(le, ge) / 4000, 1 / 4001)
        rows.append({'family': fam, 'horizon': str(hz), 'n': int(ok.sum()),
                     'mean_pts': float(r.mean()), 'p': float(p)})
pv = np.array([r['p'] if r['p'] == r['p'] else 1.0 for r in rows])
o = np.argsort(pv); q = np.empty(len(pv)); prev = 1.0
for rank in range(len(pv) - 1, -1, -1):
    i = o[rank]; prev = min(prev, len(pv) * pv[i] / (rank + 1)); q[i] = prev
for r, qq in zip(rows, q):
    r['bh_q'] = float(qq)
with open(os.path.join(HERE, 'anom_screen.csv'), 'w', newline='') as f:
    w = csv.DictWriter(f, fieldnames=['family', 'horizon', 'n', 'mean_pts',
                                      'p', 'bh_q'])
    w.writeheader()
    for r in rows:
        w.writerow({k: ('%.4f' % v if isinstance(v, float) else v)
                    for k, v in r.items()})
sig = [r for r in rows if r['bh_q'] <= 0.05]
print('anomaly cells:', len(rows), ' BH q<=0.05:', len(sig))
for r in sorted(sig, key=lambda r: r['bh_q'])[:14]:
    print('  %-5s h=%-6s n %6d  mean %+8.3f pt  q %.4f'
          % (r['family'], r['horizon'], r['n'], r['mean_pts'], r['bh_q']))
