#!/usr/bin/env python3
# ======================================================================
# MAG-AUC-V1 - shared causal feature layer
# ======================================================================
# Frozen by docs/MAG_PREREGISTRATION.md. Every feature here is causal:
# it uses bar j and bars strictly before it, never after.
#
# NOTHING IN THIS FILE USES ORDER-FLOW SIGN FOR THE MAGNITUDE STATE.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import os, sys, math, random, statistics, collections, bisect

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'v41'))
import cand_spec as CS

COST = 0.87
TICK = 0.25
SEED = 20260824
W = 1440                       # trailing normalisation window, minutes
BAL_N = 30                     # balance window, minutes
EFF_K = 5                      # price-efficiency lookback, minutes
SPLIT_U = '2025-11-01'
DEV_END = '2026-03-31'


def part(day):
    if day <= SPLIT_U:
        return 'U'
    if day <= DEV_END:
        return 'DEV'
    return 'IR'


# ------------------------------------------------------------ MAG_SCORE
def trailing_ratio(vals, w=W):
    """x_t / mean(x_{t-w..t-1}). Strictly causal: the current bar is
    excluded from its own normaliser. None until the window is full."""
    out = [None] * len(vals)
    s = 0.0
    for i, v in enumerate(vals):
        if i >= w:
            m = s / w
            out[i] = (v / m) if m > 0 else None
            s -= vals[i - w]
        s += v
    return out


def build_features(B):
    """Attach the frozen MAG_SCORE and its two declared diagnostics.

    PRIMARY  MAG_SCORE = mean of three trailing-normalised, SIGN-FREE
    activity ratios:
        a  |ofBarDelta|                      order-flow imbalance intensity
        b  ofTotalVolume                     participation
        c  buyImbalance + sellImbalance      microstructure activity (counts,
                                             summed so the SIGN cancels)

    BAR RANGE IS DELIBERATELY EXCLUDED from the primary score. MAG-H3
    asks whether MAG_SCORE predicts FUTURE absolute movement; including
    the current bar's range would make that partly a volatility-
    persistence tautology. Range enters only as MAG_ALT_RNG, the
    skeptical benchmark the primary must beat to be interesting.

    NOT USED, AND WHY: ofMinDelta / ofMaxDelta are SESSION-RUNNING
    cumulative-delta extremes, not intrabar excursion - verified in the
    source audit, they are constant across consecutive bars. A per-bar
    'delta range' does not exist in this data and is not fabricated.
    """
    a = trailing_ratio([abs(b['ofBarDelta']) for b in B])
    b_ = trailing_ratio([b['ofTotalVolume'] for b in B])
    c = trailing_ratio([(b['buyImbalanceCount_3x'] or 0)
                        + (b['sellImbalanceCount_3x'] or 0) for b in B])
    r = trailing_ratio([b['rng'] for b in B])
    for i, bar in enumerate(B):
        p = [x[i] for x in (a, b_, c)]
        bar['mag'] = (sum(p) / 3.0) if all(x is not None for x in p) else None
        bar['mag_vol'] = b_[i]
        bar['mag_rng'] = r[i]
    # price efficiency: net movement / path length over EFF_K bars
    for i, bar in enumerate(B):
        bar['eff'] = None
        bar['eff_dir'] = 0
        if i < EFF_K:
            continue
        if B[i]['tmin'] - B[i - EFF_K]['tmin'] != EFF_K:
            continue
        path = sum(B[k]['rng'] for k in range(i - EFF_K + 1, i + 1))
        if path <= 0:
            continue
        net = B[i]['close'] - B[i - EFF_K]['close']
        bar['eff'] = abs(net) / path
        bar['eff_dir'] = 1 if net > 0 else (-1 if net < 0 else 0)
    return B


def balance(B, j, n=BAL_N):
    """Causal n-minute balance ending at bar j, plus a DIMENSIONALLY
    COHERENT compression ratio.

    An n-minute range is compared to a 1-minute ATR scaled by sqrt(n),
    which is the random-walk scaling that makes the two commensurable.
    BRK-H2 died because it compared a 5-minute range to an unscaled
    1-minute ATR and demanded the range be a third of it - impossible by
    construction. This is the corrected form and it is a NEW hypothesis,
    not a silent repair of the old one."""
    if j < n or B[j]['tmin'] - B[j - n + 1]['tmin'] != n - 1:
        return None
    win = B[j - n + 1:j + 1]
    hi = max(x['high'] for x in win)
    lo = min(x['low'] for x in win)
    atr = B[j]['atr']
    if not atr or atr <= 0:
        return None
    return {'hi': hi, 'lo': lo, 'rng': hi - lo,
            'ratio': (hi - lo) / (atr * math.sqrt(n))}


def eligible(b):
    """RTH, >= 60 min before the RTH close, ATR valid - the frozen gate."""
    return bool(b.get('isRth') and b.get('minutesToRthClose') is not None
                and b['minutesToRthClose'] >= 60 and b.get('atr') and b['atr'] > 0)


def consec(B, j, n):
    return j + n < len(B) and B[j + n]['tmin'] - B[j]['tmin'] == n


# ------------------------------------------------------- outcome labels
FF_PAIRS = ((0.25, 0.25), (0.5, 0.5), (1.0, 1.0), (1.5, 1.0), (2.0, 1.0))
HORIZONS = (5, 10, 15, 30, 60)


def outcome(B, j, d, atr=None):
    """Causal forward labels from entry at B[j] close in direction d.
    Same-bar ordering is never guessed: it is recorded AMBIGUOUS."""
    atr = atr or B[j]['atr']
    px = B[j]['close']
    if not consec(B, j, max(HORIZONS)):
        return None
    ret, mfe, mae, absmove, trng = {}, {}, {}, {}, {}
    run_mfe = run_mae = 0.0
    hi = lo = px
    ff = {p: None for p in FF_PAIRS}
    for k in range(1, max(HORIZONS) + 1):
        c = B[j + k]
        up = (c['high'] - px) * d
        dn = (px - c['low']) * d
        run_mfe = max(run_mfe, up)
        run_mae = max(run_mae, dn)
        hi = max(hi, c['high'])
        lo = min(lo, c['low'])
        for (fu, fd) in FF_PAIRS:
            if ff[(fu, fd)] is not None:
                continue
            tu, td = fu * atr, fd * atr
            hu, hd = up >= tu, dn >= td
            if hu and hd:
                ff[(fu, fd)] = 'AMBIGUOUS'
            elif hu:
                ff[(fu, fd)] = 'FAV'
            elif hd:
                ff[(fu, fd)] = 'ADV'
        if k in HORIZONS:
            ret[k] = (c['close'] - px) * d
            mfe[k] = run_mfe
            mae[k] = run_mae
            absmove[k] = abs(c['close'] - px)
            trng[k] = hi - lo
    return {'ret': ret, 'mfe': mfe, 'mae': mae, 'abs': absmove, 'trng': trng,
            'ff': ff, 'atr': atr, 'px': px, 'd': d,
            'day': B[j]['day'], 'part': part(B[j]['day']), 'j': j}
