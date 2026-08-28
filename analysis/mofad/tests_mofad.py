#!/usr/bin/env python3
# MOFAD-V1 engine tests. Run green BEFORE any outcome is displayed.
# Synthetic-data tests never touch real outcomes; real-data tests touch
# eligibility/causality/partition properties only.
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mofad_lib as M  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-62s %s' % (name, 'PASS' if cond else 'FAIL'))


def mkbar(day, mm, o, h, lo, c, delta=0, vol=100, atr=10.0):
    return dict(day=day, et='%s %02d:%02d:00' % (day, mm // 60, mm % 60),
                mm=mm, open=o, high=h, low=lo, close=c,
                ofBarDelta=delta, ofTotalVolume=vol, atr=atr)


print('race semantics (synthetic)')
bars = [mkbar('2026-01-05', 571 + i, 100 + i, 101 + i, 99 + i, 100.5 + i)
        for i in range(40)]
g, k = M.race(bars, 0, 30, 1, 1000.0)      # never stopped
t('time exit at open of exit bar', k == 'TIME' and abs(g - 30.0) < 1e-9)
bars2 = list(bars)
bars2[5] = mkbar('2026-01-05', 576, 105, 106, 80, 105)   # crash through stop
g, k = M.race(bars2, 0, 30, 1, 10.0)
t('stop hit fills at stop level', k == 'STOP' and abs(g - (-10.0)) < 1e-9)
bars3 = list(bars)
bars3[5] = mkbar('2026-01-05', 576, 85, 86, 80, 85)      # gap-through open
g, k = M.race(bars3, 0, 30, 1, 10.0)
t('gap-through fills at worse open', k == 'STOP' and abs(g - (-15.0)) < 1e-9)
g, k = M.race(bars2, 0, 30, -1, 1000.0)   # crash bar must not stop a short
t('short side unaffected by long-side crash bar', k == 'TIME')
g, k = M.race(bars, 0, 30, -1, 10.0)      # uptrend hits the 110 short stop
t('short stop hit by uptrend at high>=stop', k == 'STOP' and abs(g - (-10.0)) < 1e-9)
bars4 = list(bars)
bars4[0] = mkbar('2026-01-05', 571, 100, 101, 89, 100)   # stop in entry bar
g, k = M.race(bars4, 0, 30, 1, 10.0)
t('stop can hit inside the entry bar (stop-first)', k == 'STOP')

print('F12 signal math (synthetic)')
day1, day2 = '2026-01-05', '2026-01-06'
prev = [mkbar(day1, 1081 + i, 100, 101, 99, 100, delta=(3 if i % 2 else -1),
              vol=10) for i in range(200)]
cur = ([mkbar(day2, 1 + i, 100, 101, 99, 100, delta=1, vol=10)
        for i in range(200)]
       + [mkbar(day2, 571 + i, 100 + i, 101 + i, 99 + i, 100 + i)
          for i in range(120)])
byday = {day1: prev, day2: sorted(cur, key=lambda b: b['mm'])}
ev = M.build_f12([day1, day2], byday, 'C-F12-1')
# hand value: prev deltas 100*3 + 100*(-1) = 200 ; cur first 200 bars: +200
# wait: cur window is mm 1..540 -> 200 bars delta +1 = +200 ; vol = 400*10
r_hand = (100 * 3 + 100 * -1 + 200 * 1) / (400 * 10)
t('R_on matches hand computation', len(ev) == 1 and abs(ev[0]['sig'] - r_hand) < 1e-12)
t('direction = sign(R_on)', ev[0]['dir'] == 1)
t('entry at first RTH bar', ev[0]['et'].endswith('09:31:00'))
try:
    M.build_f12([day1, day2], byday, 'C-F12-1', leak=True)
    caught = False
except AssertionError:
    caught = True
t('deliberate future-leak injection is caught', caught)

print('F08 lambda math (synthetic)')
d = '2026-01-07'
seq = []
px = 100.0
deltas = ([50, -40] * 30)[:60]
for i in range(70):
    dl = deltas[i % 60]
    px2 = px + (0.5 if dl > 0 else -0.25)
    seq.append(mkbar(d, 571 + i, px, max(px, px2), min(px, px2), px2,
                     delta=dl, vol=abs(dl)))
    px = px2
A = M._day_A_series(seq)
t('valid evaluation stamps produced', len(A) >= 1)
m, a, lb, ls = A[0]
# window bars 0..59; t=1..59 pairs: buys are indices with delta>0
w = seq[:60]
dbuy = sum(w[t]['ofBarDelta'] for t in range(1, 60) if w[t]['ofBarDelta'] > 0)
pbuy = sum(w[t]['close'] - w[t - 1]['close'] for t in range(1, 60)
           if w[t]['ofBarDelta'] > 0)
t('lambda_buy matches hand computation', abs(lb - pbuy / dbuy) < 1e-12)
t('A = lambda_buy - lambda_sell', abs(a - (lb - ls)) < 1e-12)

print('quantile + BH')
v = list(range(1, 101))
t('type-7 quantile matches numpy linear',
  abs(M.q7(v, 0.75) - np.quantile(v, 0.75)) < 1e-12)
q = M.bh([0.01, 0.04, 0.03, 0.20, 0.50])
t('BH q monotone in p order', q[0] <= q[2] <= q[1] <= q[3] <= q[4])
t('BH matches hand value for smallest p', abs(q[0] - 0.05) < 1e-12)

print('stats reproducibility (synthetic)')
rng = np.random.default_rng(7)
evs = [dict(cand='X', day='2026-01-%02d' % (1 + i // 5), et='e', dir=1,
            sig=1.0, stop=10.0, gross=float(rng.normal(0.5, 3)), exit='TIME')
       for i in range(60)]
s1, s2 = M.stats_cell(evs), M.stats_cell(evs)
t('bootstrap/permutation/control reproducible with frozen seeds', s1 == s2)
t('permutation p in (0,1]', 0 < s1['perm_p'] <= 1)

print('real-data eligibility properties (no outcomes displayed)')
days, byday = M.load_dev()
t('partition guard: no day beyond DEV_LAST', days[-1] <= M.DEV_LAST)
t('no buffer day loaded', all(not ('2026-08-18' <= d <= '2026-08-31')
                              for d in days))
E1 = M.build_f12(days, byday, 'C-F12-1')
E2 = M.build_f12(days, byday, 'C-F12-2')
E8 = M.build_f08(days, byday, 'C-F08-1')
t('C-F12-1 events match feasibility count band', 200 <= len(E1) <= 256)
t('one event per day (F12)', len(E1) == len(set(e['day'] for e in E1)))
t('F12 signal windows close before entry (assert ran)', True)
byd = {}
for e in E8:
    byd.setdefault(e['day'], []).append(int(e['et'][11:13]) * 60
                                        + int(e['et'][14:16]))
t('F08 non-overlap: same-day entries >= H+1 apart',
  all(b - a >= 16 for v in byd.values() for a, b in zip(v, v[1:])))
t('F08 threshold pool excludes the current day (warmup exists)',
  min(e['day'] for e in E8) > days[0])

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
