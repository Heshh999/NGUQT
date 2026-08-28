#!/usr/bin/env python3
# ======================================================================
# MOFAD-V1  -  PREDICTOR-ONLY FEASIBILITY COUNTS  (run BEFORE freeze)
# Counts eligible events for the proposed F12/F08 candidates.
# NO forward return, NO outcome, NO P&L, NO feature-outcome relation.
# ======================================================================
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
from cand_spec import load_merged  # noqa: E402

DEV_LAST = '2026-08-17'

B = [b for b in load_merged() if b['day'] <= DEV_LAST]
print('DEV flow bars %d  days %d  %s..%s'
      % (len(B), len(set(b['day'] for b in B)), B[0]['day'], B[-1]['day']))

# tradedate: ET day of the RTH session a bar belongs to; overnight bars
# (>=18:00) belong to the NEXT calendar trading day's session.
bykey = collections.defaultdict(list)
for b in B:
    m = int(b['et'][11:13]) * 60 + int(b['et'][14:16])
    b['mm'] = m
    bykey[b['day']].append(b)

days = sorted(bykey)
di = {d: k for k, d in enumerate(days)}

def win(d, lo, hi):
    return [b for b in bykey.get(d, ()) if lo <= b['mm'] <= hi]

n_on = n_pre = n_cl = n_div = 0
for k, d in enumerate(days):
    if k == 0:
        continue
    prev = days[k - 1]
    # overnight flow: prev day >=18:00  +  current day 00:00-09:00
    on = [b for b in bykey[prev] if b['mm'] >= 1080] + win(d, 0, 540)
    pre = win(d, 480, 569)            # 08:00-09:29
    cl = win(prev, 900, 960)          # prior 15:00-16:00
    rth_open = [b for b in bykey[d] if b['mm'] == 571]
    if not rth_open:
        continue
    vol_on = sum(b['ofTotalVolume'] or 0 for b in on)
    if len(on) >= 300 and vol_on > 0:
        n_on += 1
        dr = sum(b['ofBarDelta'] or 0 for b in on)
        pr = on[-1]['close'] - on[0]['open']
        if dr != 0 and pr != 0 and (dr > 0) != (pr > 0):
            n_div += 1
    if len(pre) >= 60 and sum(b['ofTotalVolume'] or 0 for b in pre) > 0:
        n_pre += 1
    if len(cl) >= 45 and sum(b['ofTotalVolume'] or 0 for b in cl) > 0:
        n_cl += 1

print('C-F12-1 overnight-inventory days eligible : %d' % n_on)
print('C-F12-2 preopen-flow days eligible        : %d' % n_pre)
print('C-F12-3 close-hour-inventory days eligible: %d' % n_cl)
print('C-F12-4 flow-price divergence days        : %d' % n_div)

# F08: non-overlapping 15m evaluation slots in RTH with a valid trailing
# 60-bar window containing >=10 buy and >=10 sell delta bars.
n15 = 0
for d in days:
    bars = [b for b in bykey[d] if 571 <= b['mm'] <= 950]
    k = 60
    while k < len(bars):
        wdw = bars[k - 60:k]
        nb = sum(1 for b in wdw if (b['ofBarDelta'] or 0) > 0)
        ns = sum(1 for b in wdw if (b['ofBarDelta'] or 0) < 0)
        if nb >= 10 and ns >= 10:
            n15 += 1
            k += 15
        else:
            k += 1
print('C-F08 non-overlapping T15 evaluation slots: %d  (T30 ~ half)' % n15)
print('\nPREDICTOR-ONLY COUNTS COMPLETE. No outcome was computed.')
