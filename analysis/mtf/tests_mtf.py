#!/usr/bin/env python3
# MTF-V1 engine tests - green BEFORE any outcome is displayed.
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mtf_lib as M  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-64s %s' % (name, 'PASS' if cond else 'FAIL'))


def mkD(mins, price=None, day='2026-01-05', mod0=571):
    n = len(mins)
    p = price if price is not None else [100.0 + i for i in range(n)]
    return dict(o=np.array(p, float), h=np.array(p, float) + 0.5,
                l=np.array(p, float) - 0.5, c=np.array(p, float),
                v=np.ones(n), em=np.array(mins, np.int64),
                mod=np.array([mod0 + (m - mins[0]) for m in mins], np.int32),
                day=[day] * n, et=['x'] * n)


print('T-bar construction')
D = mkD(list(range(1000, 1010)))                # 10 contiguous minutes
tb = M.tbars(D, 5)
t('two complete 5m bars from 10 minutes', len(tb['c']) == 2)
t('T-bar close = last minute close', tb['c'][0] == D['c'][4]
  and tb['c'][1] == D['c'][9])
t('T-bar high/low aggregate', tb['h'][0] == D['h'][:5].max()
  and tb['l'][1] == D['l'][5:].min())
D2 = mkD([1000, 1001, 1002, 1003, 1005, 1006, 1007, 1008, 1009])  # 1004 gone
tb2 = M.tbars(D2, 5)
t('incomplete bucket (missing minute) is dropped', len(tb2['c']) == 1)
idx, r = M.contiguous_returns(tb)
t('adjacent-bucket returns only', len(r) == 1
  and abs(r[0] - np.log(tb['c'][1] / tb['c'][0])) < 1e-12)
D3 = mkD(list(range(1000, 1005)) + list(range(1010, 1015)))       # gap
tb3 = M.tbars(D3, 5)
_, r3 = M.contiguous_returns(tb3)
t('non-adjacent buckets yield no return', len(r3) == 0)

print('motif encoding (frozen ids)')
t('VUP 102: down then strong up', M.motif_of(2, 1, 3) == M.VUP)
t('EUP 012: monotone up', M.motif_of(1, 2, 3) == M.EUP)
t('VDN 201: up then strong down', M.motif_of(2, 3, 1) == M.VDN)
t('EDN 210: monotone down', M.motif_of(3, 2, 1) == M.EDN)

print('v-turn events (synthetic)')
# closes: 102 pattern then next bar up
px = [10, 9, 11, 12, 12, 12]                    # x0>x1<x2, then +
D4 = mkD(list(range(2000, 2000 + 6 * 5)), price=None)
# build price at 5m grid directly: use T=1 on em grid for simplicity
D5 = mkD(list(range(3000, 3006)), price=px)
ev = M.vturn_events(D5, 1)
t('events found on clean series', len(ev) >= 1)
e0 = [e for e in ev if e['motif'] == M.VUP]
t('VUP event present with ta = +100*log(12/11)bp',
  len(e0) == 1 and abs(e0[0]['ta'] - np.log(12 / 11) * 1e4) < 1e-6)
pxe = [10, 11, 12, 13, 13, 13]
D6 = mkD(list(range(4000, 4006)), price=pxe)
eve = M.vturn_events(D6, 1)
t('EUP ta aligned with last leg',
  any(e['motif'] == M.EUP and abs(e['ta'] - np.log(13 / 12) * 1e4) < 1e-6
      for e in eve))
t('ties are skipped', all(e['motif'] not in ('tie',) for e in ev))

print('bootstrap / permutation determinism')
rng = np.random.default_rng(1)
v = list(rng.normal(0, 1, 300))
d = ['2026-01-%02d' % (1 + i % 25) for i in range(300)]
a1 = M.day_boot_mean(v, d, 500, 42)
a2 = M.day_boot_mean(v, d, 500, 42)
t('day bootstrap reproducible', a1 == a2)
b1 = M.day_boot_diff(v[:150], d[:150], v[150:], d[150:], 500, 42)
b2 = M.day_boot_diff(v[:150], d[:150], v[150:], d[150:], 500, 42)
t('diff bootstrap reproducible', b1 == b2)
t('BH monotone', M.bh([0.01, 0.5])[0] <= M.bh([0.01, 0.5])[1])
q = M.bh([0.01, 0.02, 0.03, 0.5])
t('BH smallest q correct', abs(q[0] - 0.04) < 1e-12)

print('B2 event engine (synthetic day)')
# one RTH day: price rises far above vwap then reverts to it
mods = list(range(571, 961))
n = len(mods)
p = [100.0] * n
for k in range(60, 80):
    p[k] = 100.0 + (k - 59) * 2.0        # run-up to 140 by idx 79
for k in range(80, n):
    p[k] = max(100.0, 140.0 - (k - 79) * 1.0)
DD = dict(o=np.array(p), h=np.array(p) + 0.2, l=np.array(p) - 0.2,
          c=np.array(p), v=np.ones(n),
          em=np.array(range(10000, 10000 + n), np.int64),
          mod=np.array(mods, np.int32), day=['2026-01-05'] * n,
          et=['x'] * n)
# no causal base/threshold history -> engine must produce NO events
ev0 = M.b2_run(DD)
t('no events without causal base/threshold warmup', len(ev0) == 0)

print('real-data structural checks (counts only, no outcomes shown)')
D = M.load()
t('DEV cap respected', max(D['day']) <= M.DEV_LAST)
tb60 = M.tbars(D, 60)
t('60m bars in plausible range (>20k)', len(tb60['c']) > 20000)
ev5 = M.vturn_events(D, 5)
t('5m v-turn events plentiful (>100k)', len(ev5) > 100000)
mot = set(e['motif'] for e in ev5)
t('all six motifs occur', mot == {'012', '021', '102', '120', '201', '210'})

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
