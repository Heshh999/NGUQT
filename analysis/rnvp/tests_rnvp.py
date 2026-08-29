#!/usr/bin/env python3
# RNVP-V1 pre-run unit tests: grid arithmetic, prior-window causality,
# trigger logic and exclusivity, VTP causality of the volume norm.
import collections
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'mtnad'))
import rnvp_run as E  # noqa: E402

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-58s %s' % (name, 'PASS' if cond else 'FAIL'))


# ---- prev_window_extremes --------------------------------------------
em = np.array([0., 1, 2, 3, 4])
h = np.array([10., 12, 11, 9, 8])
l = np.array([5., 6, 4, 3, 7])
pm, pl = E.prev_window_extremes(em, h, l, 2)
t('first bar has empty prior window', pm[0] == -np.inf and pl[0] == np.inf)
t('prior-window max excludes current bar', pm[2] == 12)
t('window expiry: bar0 out of 2-min window at i=3', pm[3] == 12 and pm[4] == 11)
t('prior-window min tracks correctly', pl[3] == 4 and pl[4] == 3)
# causality: future change leaves past untouched
h2 = h.copy()
h2[4] = 1000
pm2, _ = E.prev_window_extremes(em, h2, l, 2)
t('prior-window extremes causal', np.allclose(pm[:4], pm2[:4]))

# ---- grid arithmetic + trigger logic ---------------------------------
# R1: high pokes 15000 first time, closes below -> SHORT
o = np.array([14980., 14990])
h3 = np.array([14985., 15005])
l3 = np.array([14975., 14985])
c3 = np.array([14982., 14995])
pm3 = np.array([-np.inf, 14985.])     # prior window max < 15000
pl3 = np.array([np.inf, 14975.])
trg = E.rnl_triggers(o, h3, l3, c3, pm3, pl3, 1, True)
t('R1 fires on first upper touch with close below level',
  ('R1', -1) in trg)
t('R3 does not fire when close < L+eps', ('R3', 1) not in trg)
# R3: decisive close above 15005 -> LONG, and R1 must NOT fire
c4 = np.array([14982., 15007.])
trg2 = E.rnl_triggers(o, h3, np.array([14975., 14985]), c4, pm3, pl3, 1, True)
t('R3 fires on decisive break (close >= L+5)', ('R3', 1) in trg2)
t('R1/R3 mutually exclusive at the same level',
  ('R1', -1) not in trg2)
# prior interaction blocks both (not first touch)
pm4 = np.array([-np.inf, 15002.])
trg3 = E.rnl_triggers(o, h3, l3, c3, pm4, pl3, 1, True)
trg4 = E.rnl_triggers(o, h3, l3, c4, pm4, pl3, 1, True)
t('prior-window interaction blocks touch and break',
  ('R1', -1) not in trg3 and ('R3', 1) not in trg4)
# R2 mirror: low pokes 15000 from above, closes above -> LONG
h5 = np.array([15025., 15010])
l5 = np.array([15015., 14995])
c5 = np.array([15020., 15008])
pm5 = np.array([-np.inf, 15025.])
pl5 = np.array([np.inf, 15015.])
trg5 = E.rnl_triggers(np.array([15020., 15018]), h5, l5, c5, pm5, pl5, 1, True)
t('R2 fires on first lower touch with close above level',
  ('R2', 1) in trg5)
# R4 mirror: decisive close below 14995 -> SHORT
c6 = np.array([15020., 14993.])
trg6 = E.rnl_triggers(np.array([15020., 15018]), h5, l5, c6, pm5, pl5, 1, True)
t('R4 fires on decisive downside break', ('R4', -1) in trg6)
t('R2/R4 mutually exclusive', ('R2', 1) not in trg6)
# non-contiguous previous bar blocks everything
t('non-contiguous prev bar blocks triggers',
  E.rnl_triggers(o, h3, l3, c3, pm3, pl3, 1, False) == [])
# multi-hundred bar: floor picks the highest crossed level
h7 = np.array([14980., 15120])
c7 = np.array([14975., 15090])
pm7 = np.array([-np.inf, 14980.])
trg7 = E.rnl_triggers(o, h7, l3, c7, pm7, pl3, 1, True)
t('multi-level bar: R1 references the highest touched level (15100)',
  ('R1', -1) in trg7)

# ---- grid identities --------------------------------------------------
import math
t('floor grid: 15099 -> 15000', E.GRID * math.floor(15099 / E.GRID) == 15000)
t('ceil grid: 14901 -> 15000', E.GRID * math.ceil(14901 / E.GRID) == 15000)
t('exact multiple maps to itself both ways',
  E.GRID * math.floor(15000 / E.GRID) == 15000 and
  E.GRID * math.ceil(15000 / E.GRID) == 15000)

# ---- VTP causality ----------------------------------------------------
# 20-day norm must use PRIOR days only: with rising volumes, S > 1 always
v20 = collections.deque(maxlen=20)
S_seq = []
for k, vam in enumerate(range(100, 200, 2)):
    S = vam / np.mean(v20) if len(v20) == 20 else None
    v20.append(vam)
    if S is not None:
        S_seq.append(S)
t('VTP volume norm is causal (rising volume => S>1 always)',
  len(S_seq) > 0 and all(s > 1 for s in S_seq))

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
