#!/usr/bin/env python3
# ======================================================================
# OFH7-OFH10 TIMING FAMILY - PRE-REGISTERED SPECIFICATION AND MACHINERY
# Declared 2026-08-21 BEFORE the first run of ofht_run.py.
# ======================================================================
# PURPOSE. Frozen OFH6 (analysis/v41/ofh6_spec.py) supplies DIRECTIONAL
# CONTEXT ONLY - it is imported, never modified, and never creates an
# entry here. Four pre-declared timing events supply the entry. The
# question under test: does a second causal price/vector/order-flow
# event give a BETTER ENTRY LOCATION (lower MAE, higher MFE/MAE,
# favourable-first ordering) after OFH6 has identified direction?
#
# NAMING NOTE. The retired exploratory scan in ofh.py used the labels
# OFH7/OFH9 for unrelated ideas (effort-result, value reversion). The
# research directive of 2026-08-21 designates THIS timing family
# OFH7-OFH10; the old labels are retired. Where ambiguity matters the
# old ones are cited as x-OFH7 / x-OFH9.
#
# DATA LIMIT. Ten months, no pristine holdout. The two internal
# partitions are called DEV (<= 2026-03-31) and INTERNAL REPLICATION
# (>= 2026-04-01). Neither is called OOS anywhere.
#
# FAMILY SIZE. Exactly four hypotheses. All corrections use M=4.
# No OFH11 will be created from these results; no parameter below is
# changed after results are seen.
#
# ---------------------------------------------------------------------
# FROZEN-AT-DECLARATION PARAMETERS (all fixed before the first run)
# ---------------------------------------------------------------------
# Context (from frozen OFH6 signal stream, cooldown INCLUDED - the
# frozen 783-signal stream is used exactly as frozen):
#   CONTEXT_LIFE_PRIMARY = 30 min. Lifespans 15 and 60 are REPORTED
#   for the primary entries as robustness, never selected.
#   Context valid for direction d at entry time te, given the timing
#   chain began at t0: there exists a frozen d-signal at ts with
#   ts < t0 (chain strictly after the signal; for OFH9 the parent may
#   predate the signal and ts <= te is used), te - ts <= LIFE, and no
#   opposite-direction frozen signal in (ts, te].
#
# 1m PVSRA vectors, computed causally from the capture's own volume
# (matching V4VectorEngine semantics): prior 10 completed bars ->
# avgVol, maxVolxSpread; climax = vol >= 2.0*avgVol OR vol*range >=
# maxVolxSpread; elevated = vol >= 1.5*avgVol; bullish = close > open,
# doji follows the bearish branch. GREEN/BLUE = bullish climax/elevated,
# RED/VIOLET = bearish. 15m vectors identically on clock-aligned 15m
# aggregates (a 15m bar requires 15 consecutive 1m constituents).
#
# Swings: strength-2 pivots on clock-aligned 3m and 15m aggregates,
# strictly below/above both bars on each side, CONFIRMED at the close of
# the second bar after the pivot. Only the MOST RECENT confirmed swing
# of each type is the live reference (per the directive's location
# family). Previous-day level = prior RTH session's high/low, live from
# the session open. A level is consumed by its first breach; the breach
# IS the sweep.
#
# Windows and buffers (declared, not tuned):
#   OFH7  reclaim window = sweep bar + 5 completed 1m bars.
#         sweep void if any close beyond level by 0.5*ATR(sweep bar)
#         in the adverse direction before entry.
#   OFH8  failure window = 3 completed bars after the opposing vector.
#         "meaningful new progress" = 0.25*ATR(vector bar) beyond the
#         vector extreme (voids the setup). Recovery = 50% of the
#         vector range. One evaluation per frozen signal: the FIRST
#         opposing vector after the signal, only.
#   OFH9  parent = completed 15m GREEN/BLUE (long) with lower wick
#         >= 20% of range (20 matches the VEC-H1 precedent). Wick zone
#         = [parentLow, min(open,close)]. Life = 7 subsequent completed
#         15m bars. Any 1m low < parentLow before entry -> parent
#         permanently invalid. One entry per parent.
#   OFH10 the breach bar itself must be an OPPOSING-COLOUR vector
#         (GREEN/BLUE through a high in SHORT context). Entry window =
#         3 completed bars after the breach bar; requires a close back
#         through the level AND >= 50% recovery of the breach vector's
#         range; void if any close beyond the level by 0.25*ATR(breach
#         bar) in the breakout direction first.
#
# Entry eligibility (every entry and every control): RTH, >= 60 min to
# RTH close, ATR > 0, 60 consecutive forward 1-minute bars. Horizon for
# all geometry = 60 minutes. Cost 0.87 pt RT. Excess = raw 60m return
# minus the side- and split-matched mean over ALL entry-eligible bars.
#
# R definition per hypothesis = distance to the mechanical invalidation
# (sweep extreme / opposing-vector extreme / parentLow / trap extreme,
# plus one tick). OFH6-baseline R-races use R = 1.0 ATR and are labeled
# as such. Race ties inside one 1m bar are AMBIGUOUS - counted and
# reported, never resolved by invention.
#
# PRIMARY ENDPOINT (declared): improvement in the 1.0-ATR
# favourable-first rate over the OFH6 immediate-entry baseline,
# one-sided day-clustered bootstrap p, BH-corrected across M=4.
# Secondary: sign-flip-by-day permutation of each hypothesis's own
# favourable-first rate; med-MFE/med-MAE ratio with day-clustered CI.
#
# STOP/TARGET GATE (declared): a stop family is run for a hypothesis
# only if n >= 40, its 1-ATR favourable-first exceeds the OFH6
# baseline, its medMFE/medMAE exceeds the OFH6 baseline, and pooled
# mean excess > 0. Targets only if a stop cell is positive in both
# partitions. Otherwise skipped and said so.
#
# INSUFFICIENT SAMPLE verdict applies below n = 40 pooled.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import bisect
from collections import defaultdict

TICK = 0.25
COST = 0.87
HORIZON = 60
LIFE_PRIMARY = 30
LIFE_FAMILY = (15, 30, 60)
DEV_END = '2026-03-31'
WICK_PCT = 20.0
OFH7_WINDOW = 5
OFH8_WINDOW = 3
OFH10_WINDOW = 3
OFH7_VOID_ATR = 0.5
OFH8_PROG_ATR = 0.25
OFH10_VOID_ATR = 0.25
RECOVERY_FRAC = 0.5
PARENT_LIFE_15M = 7
MIN_N = 40
R_PAIRS = ((0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0), (3.0, 1.0))
ATR_LEVELS = (0.5, 1.0, 2.0)


def attach_dsum15(B, lookback=15):
    for j in range(len(B)):
        if j >= lookback and B[j]['tmin'] - B[j - lookback]['tmin'] == lookback:
            s = 0.0
            bad = False
            for k in range(j - lookback + 1, j + 1):
                v = B[k]['ofBarDelta']
                if v is None:
                    bad = True
                    break
                s += v
            B[j]['dsum15'] = None if bad else s
        else:
            B[j]['dsum15'] = None


def vector_dirs(bars):
    """PVSRA colour direction per bar: +1 GREEN/BLUE, -1 RED/VIOLET, 0."""
    n = len(bars)
    out = [0] * n
    for j in range(n):
        if j < 10:
            continue
        avg = 0.0
        mvs = 0.0
        ok = True
        for k in range(j - 10, j):
            v = bars[k]['vol']
            if v is None:
                ok = False
                break
            avg += v
            vs = v * (bars[k]['h'] - bars[k]['l'])
            if vs > mvs:
                mvs = vs
        if not ok:
            continue
        avg /= 10.0
        v = bars[j]['vol']
        if v is None or avg <= 0:
            continue
        rng = bars[j]['h'] - bars[j]['l']
        climax = v >= 2.0 * avg or (rng > 0 and v * rng >= mvs and mvs > 0)
        elevated = v >= 1.5 * avg
        if not (climax or elevated):
            continue
        bullish = bars[j]['c'] > bars[j]['o']       # doji -> bearish branch
        out[j] = 1 if bullish else -1
    return out


def onem_view(B):
    return [{'o': b['open'], 'h': b['high'], 'l': b['low'], 'c': b['close'],
             'vol': b['ofTotalVolume'], 'tmin': b['tmin']} for b in B]


def aggregate(B, m):
    """Clock-aligned m-minute bars from consecutive 1m bars."""
    out = []
    cur = []
    for j, b in enumerate(B):
        if cur and b['tmin'] != cur[-1][1]['tmin'] + 1:
            cur = []
        cur.append((j, b))
        if b['tmin'] % m == 0:
            if len(cur) >= m:
                grp = cur[-m:]
                out.append({'o': grp[0][1]['open'], 'c': grp[-1][1]['close'],
                            'h': max(x[1]['high'] for x in grp),
                            'l': min(x[1]['low'] for x in grp),
                            'vol': sum(x[1]['ofTotalVolume'] or 0 for x in grp),
                            'tmin': b['tmin'], 'jend': grp[-1][0],
                            'day': b['day']})
            cur = []
    return out


def swings(agg, strength=2):
    """Strength-2 pivots, strict, confirmed at close of pivot+2.
    Returns lists of (confirm_tmin, level) for lows and highs."""
    lows = []
    highs = []
    for k in range(strength, len(agg) - strength):
        lv = agg[k]['l']
        hv = agg[k]['h']
        if all(lv < agg[k + o]['l'] for o in (-2, -1, 1, 2)):
            lows.append((agg[k + strength]['tmin'], lv))
        if all(hv > agg[k + o]['h'] for o in (-2, -1, 1, 2)):
            highs.append((agg[k + strength]['tmin'], hv))
    return lows, highs


def prevday_levels(B):
    """Map day -> (prevRthHigh, prevRthLow)."""
    per = {}
    for b in B:
        if not b['isRth']:
            continue
        d = b['day']
        if d not in per:
            per[d] = [b['high'], b['low']]
        else:
            per[d][0] = max(per[d][0], b['high'])
            per[d][1] = min(per[d][1], b['low'])
    days = sorted(per)
    out = {}
    for i in range(1, len(days)):
        out[days[i]] = (per[days[i - 1]][0], per[days[i - 1]][1])
    return out


class Context(object):
    """Frozen-signal context bookkeeping (or any signal stream)."""

    def __init__(self, sig_rows, B):
        self.t = {1: [], -1: []}
        for j, d in sig_rows:
            self.t[d].append(B[j]['tmin'])

    def activating(self, d, before_t):
        """Latest d-signal strictly before before_t, or None."""
        lst = self.t[d]
        i = bisect.bisect_left(lst, before_t)
        return lst[i - 1] if i else None

    def latest_le(self, d, te):
        lst = self.t[d]
        i = bisect.bisect_right(lst, te)
        return lst[i - 1] if i else None

    def opposite_in(self, d, ts, te):
        lst = self.t[-d]
        i = bisect.bisect_right(lst, ts)
        return i < len(lst) and lst[i] <= te

    def ok(self, d, t0, te, life):
        """Chain began t0 (strictly after signal), entry te."""
        ts = self.activating(d, t0)
        if ts is None or te - ts > life:
            return False
        return not self.opposite_in(d, ts, te)

    def ok_at(self, d, te, life):
        """No chain-ordering constraint (OFH9)."""
        ts = self.latest_le(d, te)
        if ts is None or te - ts > life:
            return False
        return not self.opposite_in(d, ts, te)


def entry_ok(B, j):
    b = B[j]
    if not b['isRth'] or b['atr'] is None or b['atr'] <= 0:
        return False
    if b['minutesToRthClose'] is None or b['minutesToRthClose'] < HORIZON:
        return False
    if j + HORIZON >= len(B):
        return False
    return B[j + HORIZON]['tmin'] - b['tmin'] == HORIZON


def geometry(B, j, d, R, base):
    """Exact 60m path geometry for an entry at close of bar j, side d."""
    e = B[j]['close']
    atr = B[j]['atr']
    sp = 'DEV' if B[j]['day'] <= DEV_END else 'IR'
    mfe = 0.0
    mae = 0.0
    atr_state = {x: 0 for x in ATR_LEVELS}     # 0 unresolved 1 fav 2 adv 3 amb
    r_state = {p: 0 for p in R_PAIRS}
    for k in range(1, HORIZON + 1):
        c = B[j + k]
        fav = (c['high'] - e) if d > 0 else (e - c['low'])
        adv = (e - c['low']) if d > 0 else (c['high'] - e)
        if fav > mfe:
            mfe = fav
        if adv > mae:
            mae = adv
        for x in ATR_LEVELS:
            if atr_state[x]:
                continue
            hf = fav >= x * atr
            ha = adv >= x * atr
            if hf and ha:
                atr_state[x] = 3
            elif hf:
                atr_state[x] = 1
            elif ha:
                atr_state[x] = 2
        if R and R > 0:
            for p in R_PAIRS:
                if r_state[p]:
                    continue
                hf = fav >= p[0] * R
                ha = adv >= p[1] * R
                if hf and ha:
                    r_state[p] = 3
                elif hf:
                    r_state[p] = 1
                elif ha:
                    r_state[p] = 2
    raw = (B[j + HORIZON]['close'] - e) * d
    return {'j': j, 'd': d, 'day': B[j]['day'], 'sp': sp, 'R': R,
            'exc': raw - base[(sp, d)], 'mfe': mfe, 'mae': mae,
            'atr': atr_state, 'r': r_state}
