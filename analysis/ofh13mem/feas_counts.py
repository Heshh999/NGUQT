#!/usr/bin/env python3
# ======================================================================
# OFH13-MEMORY-V1  -  STEP 2  COUNTS-ONLY FEASIBILITY
# ======================================================================
# PREREGISTRATION SUPPORT ONLY. This script prints COUNTS and nothing
# else: no P&L, no MFE, no MAE, no win rate, no favorable-first, no
# outcome of any kind. It exists to establish whether the interaction
# classes are populated enough to justify freezing the study.
#
# Sources (read-only, byte-for-byte unmodified):
#   analysis/v41/cand_spec.py   frozen OFH13 event generator
#   analysis/rvmr/rvmr_run.py   canonical 1m grid loader (STAMP_SHIFT 0)
#   analysis/rvmr/rvmr_spec.py  frozen trailing_ratio / bucket
#
# CAUSAL MEMORY SIGNAL AT ENTRY (candidate definition, frozen by the
# preregistration document, restated here):
#   entry bar close time = e['et'] (OF grid is close-stamped via
#   f_barCloseEt; rvmr grid is close-stamped; mapping is identity)
#   t   = rvmr index with et[t] == e['et']
#   r[t] = log(c[t]/c[t-1])   requires em[t]-em[t-1] == 1
#   RB[t] = bucket(trailing_ratio(range)[t])   (uses rng[t-1440..t-1]
#           denominator and rng[t] numerator - all known at close of t)
#   HIGH   -> predict sign(r[t])      (continuation)
#   LOW    -> predict -sign(r[t])     (reversal)
#   MEDIUM -> NEUTRAL (frozen MEMORY-PRED MEDIUM CI includes 0; the
#             frozen source establishes NO directional meaning)
#   r[t] == 0 -> NEUTRAL-zero ; grid/contiguity/state missing ->
#   UNAVAILABLE (treated as NEUTRAL for the overlay)
#   ALIGNED = predicted direction == OFH13 direction d
#   OPPOSED = predicted direction == -d
#
# NOTE ON RB[t] vs the MEMORY-PRED primary: the frozen MEMORY-PRED
# primary conditions on RB[t] == RB[t+1]; RB[t+1] needs bar t+1's range
# and is NOT available at entry. The deployable causal signal therefore
# uses RB[t] alone. This is declared in the preregistration.
#
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os
import sys
import math
import collections

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))

import rvmr_spec as RS
import rvmr_run as RV
from cand_spec import load_merged, generate

print('=' * 78)
print('OFH13-MEMORY-V1   COUNTS-ONLY FEASIBILITY')
print('  no P&L, no MFE, no MAE, no win rate, no outcome of any kind')
print('=' * 78)

# ---------------------------------------------------------- OFH13 events
B = load_merged()
EV, SIGS, CTX = generate(B)
ev = EV['OFH13']
w = collections.Counter(e['w'] for e in ev)
print('\nOFH13 frozen reproduction')
print('  merged OF bars %d   %s .. %s' % (len(B), B[0]['et'], B[-1]['et']))
print('  OFH6 parent signals %d' % len(SIGS))
print('  OFH13 events %d   UNSEEN %d / DEV %d / IR %d   (expect 16/57/60)'
      % (len(ev), w['UNSEEN'], w['DEV'], w['IR']))
assert (w['UNSEEN'], w['DEV'], w['IR']) == (16, 57, 60), 'REPRO MISMATCH'
assert len(ev) == 133, 'REPRO MISMATCH'

# ---------------------------------------------------------- rvmr grid
RV.STAMP_SHIFT = 0
D = RV.load_bars()
N = len(D['c'])
c, em, et = D['c'], D['em'], D['et']
rng = [D['h'][i] - D['l'][i] for i in range(N)]
rr = RS.trailing_ratio(rng)
RB = [RS.bucket(x) if x is not None else None for x in rr]
IDX = {}
for i in range(N):
    IDX[et[i]] = i
print('\nrvmr 1m grid: %d bars   %s .. %s' % (N, et[0], et[-1]))

# ---------------------------------------------------------- classify
avail = collections.Counter()      # availability reason
state = collections.Counter()      # RB[t] among available
cls = collections.Counter()        # ALIGNED / OPPOSED / NEUTRAL-*
side = collections.Counter()       # LONG / SHORT overall
cxs = collections.Counter()        # (class, side)
cxw = collections.Counter()        # (class, window)
sxw = collections.Counter()        # (state, window)
days = collections.defaultdict(set)

for e in ev:
    d = e['d']
    sd = 'LONG' if d > 0 else 'SHORT'
    side[sd] += 1
    t = IDX.get(e['et'])
    if t is None or t == 0:
        lab = 'NEUTRAL-unavail(nogrid)'
        avail['no rvmr bar at entry stamp'] += 1
    elif em[t] - em[t - 1] != 1 or c[t - 1] <= 0 or c[t] <= 0:
        lab = 'NEUTRAL-unavail(gap)'
        avail['non-contiguous prior minute'] += 1
    elif RB[t] is None:
        lab = 'NEUTRAL-unavail(nostate)'
        avail['RVMR state unavailable'] += 1
    else:
        rt = math.log(c[t] / c[t - 1])
        st = RB[t]
        avail['MEMORY-AVAILABLE'] += 1
        state[st] += 1
        if rt == 0.0:
            lab = 'NEUTRAL-zero'
        elif st == 'MEDIUM':
            lab = 'NEUTRAL-medium'
        else:
            pred = (1 if rt > 0 else -1) if st == 'HIGH' \
                else (-1 if rt > 0 else 1)
            lab = 'ALIGNED' if pred == d else 'OPPOSED'
    cls[lab] += 1
    cxs[(lab, sd)] += 1
    cxw[(lab, e['w'])] += 1
    days[lab].add(e['day'])
    if not lab.startswith('NEUTRAL'):
        sxw[(RB[t], e['w'])] += 1

print('\nTOTAL OFH13 events                 %4d' % len(ev))
print('  LONG %d   SHORT %d' % (side['LONG'], side['SHORT']))
print('\nMEMORY availability at entry')
for k in ('MEMORY-AVAILABLE', 'no rvmr bar at entry stamp',
          'non-contiguous prior minute', 'RVMR state unavailable'):
    print('  %-34s %4d' % (k, avail[k]))
print('\nRB[t] among MEMORY-AVAILABLE')
for s in ('LOW', 'MEDIUM', 'HIGH'):
    print('  %-8s %4d' % (s, state[s]))
print('\nINTERACTION CLASSES')
order = ('ALIGNED', 'OPPOSED', 'NEUTRAL-medium', 'NEUTRAL-zero',
         'NEUTRAL-unavail(nogrid)', 'NEUTRAL-unavail(gap)',
         'NEUTRAL-unavail(nostate)')
for k in order:
    print('  %-26s %4d   unique days %3d' % (k, cls[k], len(days[k])))
print('\nCLASS x SIDE')
for k in order:
    if cls[k]:
        print('  %-26s LONG %3d  SHORT %3d'
              % (k, cxs[(k, 'LONG')], cxs[(k, 'SHORT')]))
print('\nCLASS x PARTITION')
for k in order:
    if cls[k]:
        print('  %-26s UNSEEN %3d  DEV %3d  IR %3d'
              % (k, cxw[(k, 'UNSEEN')], cxw[(k, 'DEV')], cxw[(k, 'IR')]))
print('\nSTATE x PARTITION (directional states only)')
for s in ('LOW', 'HIGH'):
    print('  %-8s UNSEEN %3d  DEV %3d  IR %3d'
          % (s, sxw[(s, 'UNSEEN')], sxw[(s, 'DEV')], sxw[(s, 'IR')]))
print('\nCOUNTS-ONLY FEASIBILITY COMPLETE. No outcomes were computed.')
