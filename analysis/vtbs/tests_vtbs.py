#!/usr/bin/env python3
# VTBS-V1 engine tests - green BEFORE any outcome is displayed.
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import vtbs_lib as V  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-62s %s' % (name, 'PASS' if cond else 'FAIL'))


def bar(mm, o, h, lo, c):
    return (mm, o, h, lo, c)


print('bracket semantics (synthetic)')
# flat then breakout up at bar 3, runs to exit
bars = [bar(571 + i, 100, 101, 99, 100) for i in range(3)]
bars += [bar(574 + i, 100 + 5 * i, 106 + 5 * i, 99 + 5 * i, 105 + 5 * i)
         for i in range(300)]
g, side, kind = V.bracket(bars, 100, 105, 95, 780)
# trigger bar mm=574+? first bar with high>=105 is i=0 of the ramp (high 106)
# entry at max(105, open=100) = 105 ; exit at open of first bar mm>=780
exp_bar = next(b for b in bars if b[0] >= 780)
t('long trigger fills at band (stop-entry)', side == 1 and kind == 'TIME'
  and abs(g - (exp_bar[1] - 105)) < 1e-9)
# gap-open beyond band -> fill at open (worse)
bars2 = [bar(571, 100, 101, 99, 100), bar(572, 110, 111, 109, 110)] + \
        [bar(573 + i, 110, 111, 109, 110) for i in range(300)]
g, side, kind = V.bracket(bars2, 100, 105, 95, 780)
t('gap-through entry fills at worse open', side == 1 and
  abs(g - (next(b for b in bars2 if b[0] >= 780)[1] - 110)) < 1e-9)
# both bands in one bar with no prior trigger = adverse whipsaw
bars3 = [bar(571, 100, 106, 94, 100)] + \
        [bar(572 + i, 100, 101, 99, 100) for i in range(300)]
g, side, kind = V.bracket(bars3, 100, 105, 95, 780)
t('both-touch bar = adverse whipsaw loss', kind == 'WHIPSAW'
  and abs(g - (-10)) < 1e-9)
# stop at opposite band after long entry
bars4 = [bar(571, 100, 106, 99, 105)] + \
        [bar(572 + i, 105 - i, 106 - i, 104 - i, 105 - i) for i in range(20)] + \
        [bar(592 + i, 100, 101, 99, 100) for i in range(300)]
g, side, kind = V.bracket(bars4, 100, 105, 95, 780)
t('stop at opposite band', kind == 'STOP' and side == 1
  and abs(g - (95 - 105)) < 1e-9)
# no trigger by 15:00
bars5 = [bar(571 + i, 100, 100.5, 99.5, 100) for i in range(380)]
t('no trigger by 15:00 -> None', V.bracket(bars5, 100, 105, 95, 780) is None)
# late trigger after 15:00 must not count
bars6 = [bar(571 + i, 100, 100.5, 99.5, 100) for i in range(335)] + \
        [bar(906 + i, 100, 110, 99, 109) for i in range(50)]
t('trigger after 15:00 ignored', V.bracket(bars6, 100, 105, 95, 955) is None)

print('day_state causality (synthetic + leak injection)')
days = ['2026-01-%02d' % k for k in range(1, 32)] + \
       ['2026-02-%02d' % k for k in range(1, 29)] + \
       ['2026-03-%02d' % k for k in range(1, 32)] + \
       ['2026-04-%02d' % k for k in range(1, 21)]
rng = np.random.default_rng(3)
byday = {}
for d in days:
    on = [bar(1081 + i, 100, 100 + rng.uniform(0, 2), 99, 100)
          for i in range(250)]
    rth = [bar(571 + i, 100, 100 + rng.uniform(0, 9), 99, 100)
           for i in range(390)]
    pre = [bar(1 + i, 100, 100.5, 99.5, 100) for i in range(300)]
    byday[d] = on + pre + rth
st = V.day_state(days, byday)
t('warmup respected (no state before 80 valid days) ',
  all(d not in st for d in days[:80]) and len(st) > 0)
try:
    V.day_state(days, byday, leak=True)
    caught = False
except AssertionError:
    caught = True
t('deliberate leak (window into RTH) is caught', caught)

print('stats reproducibility')
ev = [dict(day='2026-01-%02d' % (1 + i % 28), gross=float(rng.normal(1, 20)),
           side=1, kind='TIME', R=30.0) for i in range(120)]
s1, s2 = V.stats_cell(ev), V.stats_cell(ev)
t('bootstrap/permutation reproducible', s1 == s2)
t('BH monotone', V.bh([0.01, 0.5])[0] <= V.bh([0.01, 0.5])[1])

print('real-data eligibility (no outcomes displayed)')
rdays, rbyday = V.load_days()
t('partition: no day beyond DEV cap', rdays[-1] <= V.DEV_LAST)
rst = V.day_state(rdays, rbyday)
high = [d for d in rst if rst[d]['p'] >= rst[d]['thr']]
t('eligible day count matches feasibility (1689)', len(rst) == 1689)
t('HIGH count matches feasibility (468)', len(high) == 468)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
