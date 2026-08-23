#!/usr/bin/env python3
# ======================================================================
# RED-* FAMILY - shared causal data layer
# ======================================================================
# Loads the SAME merged order-flow history the frozen work uses and
# derives ONLY causal features. Every derived level carries the time it
# became knowable; nothing is visible before that time.
#
# EXPLORATORY-DERIVED: these hypotheses were written after the 12-month
# history had been examined. No partition here is externally clean.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, csv, glob, math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import cand_spec as CS

SCR = CS.SCR
SPLIT_UNSEEN = '2025-11-01'          # same merge boundary as cand_spec
DEV_END = '2026-03-31'               # DEV / IR split (established convention)
COST = 0.87                          # frozen MNQ round-trip, points
TICK = 0.25
DOLLARS_PER_POINT = 2.0
Q_BD75 = 511.0                       # PREVIOUSLY FROZEN |delta| 75th pct

F_NUM = ['f_open', 'f_high', 'f_low', 'f_close', 'f_atr', 'f_volume',
         'f_ofTotalVolume', 'f_ofBidVolume', 'f_ofAskVolume', 'f_ofBarDelta',
         'f_ofDeltaPct', 'f_ofCumDelta', 'f_ofMinDelta', 'f_ofMaxDelta',
         'f_stackedBuyLevels_3x', 'f_stackedSellLevels_3x',
         'f_buyImbalanceCount_3x', 'f_sellImbalanceCount_3x',
         'f_aggressiveBuyVolume', 'f_aggressiveSellVolume',
         'f_priceProgressUpTicks', 'f_priceProgressDownTicks',
         'f_volumePerUpTick', 'f_volumePerDownTick', 'f_absorptionStrengthRaw',
         'f_profilePoc', 'f_profileVah', 'f_profileVal',
         'f_profileHvnCount', 'f_profileLvnCount', 'f_relVolume',
         'f_minutesFromRthOpen', 'f_minutesToRthClose']
F_BOOL = ['f_isRth', 'f_profileReady', 'f_insideValueArea',
          'f_absorptionBuyCandidate', 'f_absorptionSellCandidate']

SHORT = {'f_open': 'open', 'f_high': 'high', 'f_low': 'low', 'f_close': 'close',
         'f_atr': 'atr', 'f_volume': 'vol', 'f_ofTotalVolume': 'ofVol',
         'f_ofBidVolume': 'bidVol', 'f_ofAskVolume': 'askVol',
         'f_ofBarDelta': 'delta', 'f_ofDeltaPct': 'deltaPct',
         'f_ofCumDelta': 'cumDelta', 'f_ofMinDelta': 'minDelta',
         'f_ofMaxDelta': 'maxDelta', 'f_stackedBuyLevels_3x': 'stkBuy',
         'f_stackedSellLevels_3x': 'stkSell',
         'f_buyImbalanceCount_3x': 'imbBuy', 'f_sellImbalanceCount_3x': 'imbSell',
         'f_aggressiveBuyVolume': 'aggBuy', 'f_aggressiveSellVolume': 'aggSell',
         'f_priceProgressUpTicks': 'upTicks', 'f_priceProgressDownTicks': 'dnTicks',
         'f_volumePerUpTick': 'volPerUp', 'f_volumePerDownTick': 'volPerDn',
         'f_absorptionStrengthRaw': 'absStr', 'f_profilePoc': 'poc',
         'f_profileVah': 'vah', 'f_profileVal': 'val',
         'f_profileHvnCount': 'hvnCnt', 'f_profileLvnCount': 'lvnCnt',
         'f_relVolume': 'relVol', 'f_minutesFromRthOpen': 'mfo',
         'f_minutesToRthClose': 'mtc', 'f_isRth': 'isRth',
         'f_profileReady': 'profReady', 'f_insideValueArea': 'inVA',
         'f_absorptionBuyCandidate': 'absBuy', 'f_absorptionSellCandidate': 'absSell'}


def _f(s):
    try:
        v = float(s)
        return None if v != v else v
    except (TypeError, ValueError):
        return None


def _mk(row, ix):
    et = row[ix['f_barCloseEt']]
    d = {'et': et, 'day': et[:10]}
    for k in F_NUM:
        if k in ix:
            d[SHORT[k]] = _f(row[ix[k]])
    for k in F_BOOL:
        if k in ix:
            d[SHORT[k]] = (row[ix[k]] == 'TRUE')
    for need in ('open', 'high', 'low', 'close', 'atr'):
        if d.get(need) is None:
            return None
    d['tmin'] = (int(et[:4]) * 527040 + int(et[5:7]) * 44640 + int(et[8:10]) * 1440
                 + int(et[11:13]) * 60 + int(et[14:16]))
    return d


def load_bars():
    """Merged capture, identical merge rule to cand_spec.load_merged."""
    B = []
    for f in sorted(glob.glob(SCR + '/ofnew/v4_1_orderflow_MNQ_v41of_*.csv')):
        with open(f, newline='') as fh:
            r = csv.reader(fh)
            h = next(r)
            ix = {c: k for k, c in enumerate(h)}
            for row in r:
                if len(row) != len(h):
                    continue
                if row[ix['f_barCloseEt']][:10] > SPLIT_UNSEEN:
                    continue
                b = _mk(row, ix)
                if b:
                    B.append(b)
    for f in sorted(glob.glob(SCR + '/of2/v4_1_orderflow_MNQ_v41of_*.csv')):
        with open(f, newline='') as fh:
            r = csv.reader(fh)
            h = next(r)
            ix = {c: k for k, c in enumerate(h)}
            for row in r:
                if len(row) != len(h):
                    continue
                if row[ix['f_barCloseEt']][:10] <= SPLIT_UNSEEN:
                    continue
                b = _mk(row, ix)
                if b:
                    B.append(b)
    B.sort(key=lambda b: b['et'])
    out, seen = [], set()
    for b in B:
        if b['et'] in seen:
            continue
        seen.add(b['et'])
        out.append(b)
    return out


def partition(day):
    if day <= SPLIT_UNSEEN:
        return 'U'
    if day <= DEV_END:
        return 'DEV'
    return 'IR'


# ---------------------------------------------------------------- causality
def make_consec(B):
    def consec(j, k):
        return B[j]['tmin'] - B[k]['tmin'] == j - k
    return consec


def fwd_ok(B, j, mins):
    return j + mins < len(B) and B[j + mins]['tmin'] - B[j]['tmin'] == mins


# ------------------------------------------------------- derived causal levels
def build_swings(B, tf, left=2, right=2):
    """Aggregate 1m -> tf bars on clock boundaries, find pivots with `right`
    bars of confirmation. Returns two lists of (known_j, price) where known_j
    is the 1m index at which the level FIRST becomes knowable."""
    groups, cur, curkey = [], [], None
    for j, b in enumerate(B):
        key = (b['day'], (int(b['et'][11:13]) * 60 + int(b['et'][14:16])) // tf)
        if key != curkey:
            if cur:
                groups.append(cur)
            cur, curkey = [], key
        cur.append(j)
    if cur:
        groups.append(cur)
    gb = []
    for g in groups:
        gb.append({'hi': max(B[j]['high'] for j in g),
                   'lo': min(B[j]['low'] for j in g),
                   'end_j': g[-1]})
    lows, highs = [], []
    for i in range(left, len(gb) - right):
        w = gb[i - left:i + right + 1]
        if all(gb[i]['lo'] <= x['lo'] for x in w) and any(gb[i]['lo'] < x['lo'] for x in w):
            lows.append((gb[i + right]['end_j'], gb[i]['lo']))
        if all(gb[i]['hi'] >= x['hi'] for x in w) and any(gb[i]['hi'] > x['hi'] for x in w):
            highs.append((gb[i + right]['end_j'], gb[i]['hi']))
    return lows, highs


def level_lookup(levels):
    """levels: sorted [(known_j, price)]. Returns fn(j) -> list of prices
    knowable at or before j, most recent first."""
    ks = sorted(levels)

    def at(j, n=6):
        out = []
        lo, hi = 0, len(ks)
        while lo < hi:
            mid = (lo + hi) // 2
            if ks[mid][0] <= j:
                lo = mid + 1
            else:
                hi = mid
        for i in range(lo - 1, max(-1, lo - 1 - n), -1):
            out.append(ks[i])
        return out
    return at


def prior_day_levels(B):
    """Prior TRADING DAY's RTH high/low, knowable from the next day onward."""
    byday = {}
    for b in B:
        if not b.get('isRth'):
            continue
        d = byday.setdefault(b['day'], [b['high'], b['low']])
        d[0] = max(d[0], b['high'])
        d[1] = min(d[1], b['low'])
    days = sorted(byday)
    prev = {}
    for i in range(1, len(days)):
        prev[days[i]] = byday[days[i - 1]]
    return prev


def build_fvg(B, consec):
    """Causal completed 3-candle FVG. Returns list of dicts with the index at
    which the gap is KNOWN (close of candle 3)."""
    out = []
    for j in range(2, len(B)):
        if not consec(j, j - 2):
            continue
        a, c3 = B[j - 2], B[j]
        if a['high'] < c3['low']:
            out.append({'j': j, 'dir': 1, 'lo': a['high'], 'hi': c3['low']})
        elif a['low'] > c3['high']:
            out.append({'j': j, 'dir': -1, 'lo': c3['high'], 'hi': a['low']})
    return out


# ------------------------------------------------------------- effort / result
def rolling_med_absdelta(B, win=60):
    """Causal rolling median |delta| (scale for effort normalisation)."""
    out = [None] * len(B)
    buf = []
    for j, b in enumerate(B):
        if j >= win:
            pass
        d = b.get('delta')
        buf.append(abs(d) if d is not None else 0.0)
        if len(buf) > win:
            buf.pop(0)
        if len(buf) == win:
            s = sorted(buf)
            out[j] = s[win // 2]
    return out


def effort_result(B, j, side, medabs, form='E2'):
    """Causal effort-vs-result on bar j only.
      side=-1 -> SELLING effort vs DOWNSIDE result   (long setups)
      side=+1 -> BUYING  effort vs UPSIDE   result   (short setups)
    Returns (effort, result, failure_score); higher score = more opposing
    effort for less price result.

      E1 NATIVE : capture's volume-per-tick-of-progress, scaled by its own
                  causal rolling median (uses a different volume basis from
                  E2/E3, verified non-redundant)
      E2 PRIMARY: |opposing delta| / rolling median |delta|
                  divided by adverse tick progress in ATR units
      E3        : same effort, divided by adverse RANGE in ATR units

    E2 is the frozen primary: it is the most direct reading of the stated
    mechanism (aggression per unit of price achieved). E1/E3 are reported
    as robustness, never as selectors.
    """
    b = B[j]
    atr = b['atr']
    ms = medabs[j]
    d = b.get('delta')
    if not atr or atr <= 0 or not ms or ms <= 0 or d is None:
        return None
    if side < 0:                                  # selling effort
        if d >= 0:
            return None
        effort = -d / ms
        ticks = b.get('dnTicks')
        adverse_pts = max(b['open'] - b['low'], 0.0)
        native = b.get('volPerDn')
        nat_med = medabs[j]                       # placeholder, replaced below
    else:                                         # buying effort
        if d <= 0:
            return None
        effort = d / ms
        ticks = b.get('upTicks')
        adverse_pts = max(b['high'] - b['open'], 0.0)
        native = b.get('volPerUp')
        nat_med = medabs[j]
    if form == 'E1':
        if native is None or native <= 0:
            return None
        return effort, 1.0 / native, native       # native score: higher = more volume per tick
    if form == 'E2':
        if ticks is None:
            return None
        result = (float(ticks) * TICK) / atr
        return effort, result, effort / max(result, 1e-6)
    result = adverse_pts / atr                    # E3
    return effort, result, effort / max(result, 1e-6)


# ------------------------------------------------------------------- outcomes
HORIZONS = (5, 10, 15, 30, 60)


def outcome(B, j, d, horizons=HORIZONS, ff_pairs=((0.25, 0.25), (0.5, 0.5),
                                                  (1.0, 1.0), (1.5, 1.0), (2.0, 1.0))):
    """Forward path metrics from entry at close of bar j, direction d.
    Requires consecutive bars; returns None if the window is broken."""
    px, atr = B[j]['close'], B[j]['atr']
    if not atr or atr <= 0:
        return None
    hmax = max(horizons)
    if j + hmax >= len(B) or B[j + hmax]['tmin'] - B[j]['tmin'] != hmax:
        return None
    mfe = {h: 0.0 for h in horizons}
    mae = {h: 0.0 for h in horizons}
    net = {}
    ff = {}
    pend = dict((p, None) for p in ff_pairs)
    run_f = run_a = 0.0
    for k in range(1, hmax + 1):
        c = B[j + k]
        fav = (c['high'] - px) if d > 0 else (px - c['low'])
        adv = (px - c['low']) if d > 0 else (c['high'] - px)
        run_f = max(run_f, fav)
        run_a = max(run_a, adv)
        for (fu, au) in ff_pairs:
            if pend[(fu, au)] is not None:
                continue
            hf, ha = fav >= fu * atr, adv >= au * atr
            if hf and ha:
                pend[(fu, au)] = 'AMBIGUOUS'
            elif hf:
                pend[(fu, au)] = 'FAV'
            elif ha:
                pend[(fu, au)] = 'ADV'
        if k in mfe:
            mfe[k] = run_f
            mae[k] = run_a
            net[k] = (B[j + k]['close'] - px) * d - COST
    for p in ff_pairs:
        ff['ff_%g_%g' % p] = pend[p] or 'NEITHER'
    return {'mfe': mfe, 'mae': mae, 'net': net, 'ff': ff,
            'atr': atr, 'entry_px': px, 'dir': d, 'j': j,
            'et': B[j]['et'], 'day': B[j]['day'], 'part': partition(B[j]['day'])}


def entry_ok(B, j):
    """Frozen entry gate: RTH, >=60 min before the close (so the 60-minute
    horizon lies inside the session), ATR valid. Deliberately identical in
    spirit to the frozen work's gate."""
    b = B[j]
    if not b.get('isRth'):
        return False
    if b.get('mtc') is None or b['mtc'] < 60:
        return False
    if not b['atr'] or b['atr'] <= 0:
        return False
    return True


def qtile(xs, q):
    s = sorted(x for x in xs if x is not None)
    if not s:
        return None
    i = int(q * (len(s) - 1))
    return s[i]
