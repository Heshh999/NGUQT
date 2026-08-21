#!/usr/bin/env python3
# ======================================================================
# OFH6 - FROZEN SPECIFICATION.  DO NOT EDIT AFTER 2026-08-21.
# ======================================================================
# This module is the ONE definition of OFH6. Every test imports it. No
# test may redefine the rule, the threshold, the eligibility, the entry,
# the exit or the cost. If a future test needs a different rule, it is a
# DIFFERENT HYPOTHESIS with a different name and its own freeze date.
#
# Frozen 2026-08-21, AFTER the ten-month window was already searched and
# BEFORE the destruction-test battery was run. Status at freeze:
#   internally replicated on 2025-11-02 .. 2026-08-19; NOT externally
#   validated. Family-wise sign-flip p = 0.129 over the nine hypotheses
#   that fired out of the twelve searched.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# MNQ ONLY. MNQ = $2.00 per index point per contract.
# ----------------------------------------------------------------------
#
# THE RULE, in full
#
#   Instrument      MNQ continuous, back-adjusted, 1-minute Volumetric.
#   Signal series   ofBarDelta = (ask-traded volume) - (bid-traded volume)
#                   for the completed 1-minute bar, as produced by
#                   V4OrderFlowV41.cs. Signed, in contracts.
#
#   dsum15(t)       = sum of ofBarDelta over the 15 completed bars
#                     ending at and INCLUDING bar t.
#                     Undefined (no signal) unless all 15 bars are
#                     consecutive clock minutes with non-null delta.
#
#   THRESHOLD       |dsum15| >= 3380.0 contracts.
#                   Origin: the 90th percentile of |dsum15| over the
#                   27,487 eligible bars in 2025-11-02 .. 2026-03-31.
#                   HARDCODED here so it can never be refit.
#
#   DIRECTION       dsum15 > 0  -> LONG.   dsum15 < 0 -> SHORT.
#                   (follow the delta, do not fade it)
#
#   ELIGIBILITY     all of:
#                     - bar is RTH
#                     - minutesFromRthOpen >= 30
#                     - minutesToRthClose  >= 90
#                     - atr > 0
#                     - dsum15 defined
#                     - the 90 minutes after the bar are consecutive
#                       clock minutes (no halt inside the window)
#
#   COOLDOWN        30 minutes. After a signal fires at time t, no new
#                   signal before t+30. Applied across both directions.
#
#   ENTRY           at the CLOSE of the signal bar. The bar is complete
#                   when the decision is made; no repainting.
#
#   PRIMARY EXIT    time exit, 60 minutes after entry.
#
#   COST            0.87 index points per round turn, all-in.
#
#   REPORTING       every result is stated as EXCESS over the
#                   side-matched, split-matched baseline: the mean 60m
#                   return of ALL eligible bars on that side in that
#                   period. Window drift may not be reported as edge.
#
# WHAT MAY STILL VARY (declared here, so it is not a later degree of
# freedom): stop and target geometry is EXPLICITLY UNFROZEN and is the
# subject of the management study. The entry rule above is frozen; the
# management wrapped around it is not, and any management result must be
# reported as a family with its plateau, never as a single best cell.
# ======================================================================

import pickle
from collections import defaultdict

SCRATCH = '/tmp/claude-0/-home-user-NGUQT/fdf51f53-eedc-531d-bbe6-d05384541cce/scratchpad'
CACHE = SCRATCH + '/of_bars2.pkl'

# ---- FROZEN CONSTANTS -------------------------------------------------
DELTA_LOOKBACK = 15
THRESHOLD = 3380.0
COOLDOWN_MIN = 30
ENTRY_MIN_AFTER_RTH_OPEN = 30
ENTRY_MIN_BEFORE_RTH_CLOSE = 90
PRIMARY_EXIT_MIN = 60
FORWARD_WINDOW_MIN = 90
COST_PTS = 0.87
DOLLARS_PER_POINT = 2.0
DEV_END = '2026-03-31'          # labels the internal replication split only
FREEZE_DATE = '2026-08-21'
# -----------------------------------------------------------------------


def load_bars():
    with open(CACHE, 'rb') as fh:
        B = pickle.load(fh)
    n = len(B)
    for j in range(n):
        if j >= DELTA_LOOKBACK and B[j]['tmin'] - B[j - DELTA_LOOKBACK]['tmin'] == DELTA_LOOKBACK:
            s = 0.0
            bad = False
            for k in range(j - DELTA_LOOKBACK + 1, j + 1):
                v = B[k]['ofBarDelta']
                if v is None:
                    bad = True
                    break
                s += v
            B[j]['dsum15'] = None if bad else s
        else:
            B[j]['dsum15'] = None
    return B


def eligible(B):
    out = []
    for j in range(len(B) - FORWARD_WINDOW_MIN - 1):
        b = B[j]
        if not b['isRth']:
            continue
        if b['minutesFromRthOpen'] is None or b['minutesFromRthOpen'] < ENTRY_MIN_AFTER_RTH_OPEN:
            continue
        if b['minutesToRthClose'] is None or b['minutesToRthClose'] < ENTRY_MIN_BEFORE_RTH_CLOSE:
            continue
        if b['atr'] is None or b['atr'] <= 0:
            continue
        if b['dsum15'] is None:
            continue
        if B[j + FORWARD_WINDOW_MIN]['tmin'] - b['tmin'] != FORWARD_WINDOW_MIN:
            continue
        out.append(j)
    return out


def signals(B, elig, threshold=THRESHOLD, cooldown=COOLDOWN_MIN):
    """The frozen rule. threshold/cooldown are arguments ONLY so the
    robustness sweep can perturb them; every headline number uses the
    frozen defaults."""
    out = []
    last = -10 ** 9
    for j in elig:
        v = B[j]['dsum15']
        if abs(v) < threshold:
            continue
        if B[j]['tmin'] - last < cooldown:
            continue
        last = B[j]['tmin']
        out.append((j, +1 if v > 0 else -1))
    return out


def ret(B, j, side, minutes=PRIMARY_EXIT_MIN):
    return (B[j + minutes]['close'] - B[j]['close']) * side


def split_of(day):
    return 'DEV' if day <= DEV_END else 'VAL'


def baselines(B, elig, minutes=PRIMARY_EXIT_MIN):
    base = {}
    for sp in ('DEV', 'VAL'):
        for side in (+1, -1):
            v = [ret(B, j, side, minutes) for j in elig if split_of(B[j]['day']) == sp]
            base[(sp, side)] = sum(v) / len(v)
    return base


def excess(B, rows, base, minutes=PRIMARY_EXIT_MIN):
    return [ret(B, j, d, minutes) - base[(split_of(B[j]['day']), d)] for j, d in rows]


if __name__ == '__main__':
    B = load_bars()
    E = eligible(B)
    S = signals(B, E)
    base = baselines(B, E)
    ex = excess(B, S, base)
    days = sorted(set(B[j]['day'] for j, _ in S))
    print('OFH6 FROZEN SPEC  (freeze date %s)' % FREEZE_DATE)
    print('  threshold |dsum15| >= %.1f   cooldown %d min   exit %d min   cost %.2f pt'
          % (THRESHOLD, COOLDOWN_MIN, PRIMARY_EXIT_MIN, COST_PTS))
    print('  eligible bars %d   signals %d   sessions %d' % (len(E), len(S), len(days)))
    print('  mean excess %+0.3f pt   median %+0.3f pt'
          % (sum(ex) / len(ex), sorted(ex)[len(ex) // 2]))
