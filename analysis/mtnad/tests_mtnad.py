#!/usr/bin/env python3
# MTNAD-V1 pre-run unit tests: age primitives, causality, race.
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mtnad_run as E  # noqa: E402  (import only; main() not executed)

OK = []


def t(name, cond):
    OK.append((name, bool(cond)))
    print('  %-58s %s' % (name, 'PASS' if cond else 'FAIL'))


# ---- running_ages -----------------------------------------------------
em = np.array([0., 1, 2, 3, 4])
h = np.array([5., 6, 4, 7, 3])
l = np.array([1., 2, 0, 3, 1])
ah, al = E.running_ages(em, h, l)
t('running max refresh at idx3 -> age 1 at idx4', ah[4] == 1)
t('running min refresh at idx2 -> age 2 at idx4', al[4] == 2)
t('age zero on refresh bar itself', ah[3] == 0 and al[2] == 0)
ah2, _ = E.running_ages(np.array([0., 1]), np.array([5., 5]),
                        np.array([1., 0]))
t('equal high refreshes (tie -> later bar)', ah2[1] == 0)

# ---- vol_ages ---------------------------------------------------------
v = np.array([10., 20, 30, 40, 50])
vh, vl = E.vol_ages(em, h, l, v)
# high refresh at idx3: volume strictly after idx3 through idx4 = 50
t('vol age of high at idx4 = 50', vh[4] == 50)
# low refresh at idx2: volume after idx2 = 40+50
t('vol age of low at idx4 = 90', vl[4] == 90)
t('vol age zero on refresh bar', vh[3] == 0)

# ---- rolling_extreme_ages --------------------------------------------
em3 = np.array([0., 1, 2, 3])
h3 = np.array([10., 9, 8, 7])
l3 = np.array([0., 1, 2, 3])
ah3, al3 = E.rolling_extreme_ages(em3, h3, l3, 2)
# window at idx2: bars with em > 0 -> idx1..2, max 9 at idx1
t('rolling window max age (expiry works)', ah3[2] == 1)
t('rolling window min age (rising lows)', al3[2] == 1)
# ties: later bar is the refresh
h4 = np.array([5., 5, 5])
l4 = np.array([5., 5, 5])
ah4, al4 = E.rolling_extreme_ages(np.array([0., 1, 2]), h4, l4, 10)
t('rolling tie -> later refresh bar (max)', ah4[2] == 0)
t('rolling tie -> later refresh bar (min)', al4[2] == 0)
# em gaps: ages measured in em units, window in em units
em5 = np.array([0., 10, 11])
h5 = np.array([9., 5, 4])
ah5, _ = E.rolling_extreme_ages(em5, h5, np.zeros(3), 5)
t('em-gap: old max expired from 5-min window', ah5[1] == 0)

# ---- causality: future bars cannot change past ages -------------------
emc = np.arange(6, dtype=float)
hc = np.array([5., 6, 4, 7, 3, 2])
lc = np.array([1., 2, 0, 3, 1, 1])
a1, b1 = E.rolling_extreme_ages(emc, hc, lc, 240)
hc2 = hc.copy()
hc2[5] = 1000.0
a2, b2 = E.rolling_extreme_ages(emc, hc2, lc, 240)
t('rolling ages causal (future spike leaves past unchanged)',
  np.allclose(a1[:5], a2[:5]) and np.allclose(b1[:5], b2[:5]))
a1r, _ = E.running_ages(emc, hc, lc)
a2r, _ = E.running_ages(emc, hc2, lc)
t('running ages causal', np.allclose(a1r[:5], a2r[:5]))

# ---- daily_dh_dl ------------------------------------------------------
dh_up = list(range(1, 30))          # strictly rising highs
dl_up = list(range(1, 30))          # rising lows too
DH, DL = E.daily_dh_dl(dh_up, dl_up, 25)
t('rising highs: DH=0 (yesterday is the 20d high)', DH == 0)
t('rising lows: DL=19 (oldest window day is the low)', DL == 19)
dh_v = [10] * 20 + [5] * 9          # old plateau then drop
DH2, DL2 = E.daily_dh_dl(dh_v, [0] * 29, 25)
# window days 5..24 -> highs: idx5..19 are 10 (latest at window pos 14)
t('plateau high: latest tying day is the refresh', DH2 == 19 - 14)

# ---- race -------------------------------------------------------------
D = dict(o=np.array([100., 101, 99, 98]), h=np.array([101., 102, 100, 99]),
         l=np.array([99.5, 100, 95, 97]), c=np.array([101., 100, 96, 98]),
         mod=np.array([600, 601, 602, 603]), em=np.array([0, 1, 2, 3]))
g, kind = E.race(D, [0, 1, 2, 3], 1, 60, 1, 3.0)   # long at 101, stop 98
t('stop-first same-bar ambiguity (long stopped in crash bar)',
  kind == 'STOP' and g == -3.0)
D2 = dict(o=np.array([100., 101, 94, 98]), h=np.array([101., 102, 95, 99]),
          l=np.array([99.5, 100, 93, 97]), c=np.array([101., 100, 94, 98]),
          mod=np.array([600, 601, 602, 603]), em=np.array([0, 1, 2, 3]))
g2, k2 = E.race(D2, [0, 1, 2, 3], 1, 60, 1, 3.0)   # gap through stop 98
t('gap-through fills at worse open (94, not 98)',
  k2 == 'STOP' and g2 == 94 - 101)
D3 = dict(o=np.array([100., 101, 102, 103]), h=np.array([101., 102, 103, 104]),
          l=np.array([100., 101, 102, 103]), c=np.array([101., 102, 103, 104]),
          mod=np.array([600, 601, 602, 661]), em=np.array([0, 1, 2, 61]))
g3, k3 = E.race(D3, [0, 1, 2, 3], 1, 60, 1, 3.0)
t('time exit at open of first bar >= entry+60m', k3 == 'TIME' and g3 == 2.0)

# ---- AR normalization -------------------------------------------------
ar = lambda alo, ahi: (alo - ahi) / (alo + ahi)
t('AR=+1 when low maximally stale (high fresh)', ar(100, 0) == 1)
t('AR=-1 when high maximally stale', ar(0, 100) == -1)

n_fail = sum(1 for _, ok in OK if not ok)
print('\n%d/%d tests passed' % (len(OK) - n_fail, len(OK)))
sys.exit(1 if n_fail else 0)
