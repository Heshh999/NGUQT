#!/usr/bin/env python3
# ======================================================================
# 4H-DVT-V1 - FROZEN SPECIFICATION MODULE
# ======================================================================
# Makes every rule in docs/4H_DVT_V1_PREREGISTRATION.md mechanical.
# This file defines RULES ONLY. It computes NO performance, NO outcome,
# NO return, NO win rate. The companion feasibility script counts events.
#
# SOURCE-AUTHORITATIVE definitions (transcribed, NOT invented):
#   VWAP + bands  src/MnqTwoStrategiesShared.cs  L239-248, L392-399,
#                                                L492-513
#   Vector        src/MnqTwoStrategiesShared.cs  L116-141 (VectorClassifier)
#   EMA(9)        src/MnqTwoStrategiesShared.cs  L159 (BarSnap.Ema9)
#
# DECLARED AS MINE (absent from source, fixed here before any result):
#   4H EMA20 / EMA50, the 4H bar grid, the max test spacing, the
#   invalidation rule, the entry window choice and the structural stop.
#
# SUBMITS NO ORDERS. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

import math

# ---------------------------------------------------------------- source
DAY_START_MIN_ET = 1080      # 18:00 ET exchange-day open (DayStartMinutesEt)
VWAP_BAND_MULT = 1.0         # VwapBandMultiplier, TradingView Band 1 default
VECTOR_CLIMAX_MULT = 2.0     # volume >= 2.0 * avgVol10
VECTOR_MEDIUM_MULT = 1.5     # volume >= 1.5 * avgVol10
VECTOR_LOOKBACK = 10         # previous 10 COMPLETED bars
EMA_FAST_LEN = 9             # 1m EMA(9)

# Eligible vector classes (user-specified): REGULAR is NOT a vector.
GREEN, BLUE, REG_BULL, REG_BEAR, VIOLET, RED = 3, 2, 1, -1, -2, -3
ELIGIBLE_VECTORS = (GREEN, BLUE, VIOLET, RED)

# ---------------------------------------------------------------- mine
EMA_TREND_FAST = 20          # 4H EMA20   (MINE - absent from source)
EMA_TREND_SLOW = 50          # 4H EMA50   (MINE - absent from source)
H4_MINUTES = 240             # 4H grid anchored on DAY_START_MIN_ET
MAX_SPACING_15M = 16         # <= 16 completed 15m bars between tests
                             # = exactly one 4H trend bar, so the 4H context
                             # gating the setup cannot go stale inside the
                             # setup's own lifespan. ONE value, never swept.
ENTRY_START_MIN_ET = 570     # 09:30 ET
ENTRY_END_MIN_ET = 900       # 15:00 ET (frozen RVMR/V4 eligible window;
                             # guarantees a full 60m horizon inside RTH)
HORIZON_MIN = 60             # measurement frame
COST_PTS = 0.87


# =============================================================== EMA
class Ema(object):
    """Standard EMA, alpha = 2/(n+1), seeded with the SMA of the first n
    values. Recursive from COMPLETED closes only."""

    def __init__(self, n):
        self.n = n
        self.a = 2.0 / (n + 1.0)
        self.buf = []
        self.v = None

    def add(self, x):
        if self.v is None:
            self.buf.append(x)
            if len(self.buf) == self.n:
                self.v = sum(self.buf) / float(self.n)
        else:
            self.v = self.a * x + (1.0 - self.a) * self.v
        return self.v

    @property
    def ready(self):
        return self.v is not None


# =============================================================== VWAP
class SessionVwap(object):
    """TradingView built-in Session VWAP + band pair, transcribed from
    src/MnqTwoStrategiesShared.cs.

        src      = hlc3 = (high + low + close) / 3
        vwap     = SUM(src*vol) / SUM(vol)
        variance = SUM(vol*src*src)/SUM(vol) - vwap^2      (floored at 0)
        band     = vwap +/- 1.0 * sqrt(variance)

    Re-anchors at each new exchange day (18:00 ET). Accumulates only when
    volume > 0, exactly as the source does. There is exactly ONE upper
    band (VWAP_BAND_HIGH) and ONE lower band (VWAP_BAND_LOW).
    """

    def __init__(self):
        self.sv = 0.0     # SUM(src*vol)
        self.v = 0.0      # SUM(vol)
        self.ssv = 0.0    # SUM(vol*src*src)
        self.key = None

    def session_key(self, et_minutes_epoch):
        """Exchange-day index: shift back by 18:00 then take the day."""
        return (et_minutes_epoch - DAY_START_MIN_ET) // 1440

    def update(self, et_minutes_epoch, h, l, c, vol):
        k = self.session_key(et_minutes_epoch)
        if k != self.key:
            self.sv = self.v = self.ssv = 0.0
            self.key = k
        if vol > 0:
            src = (h + l + c) / 3.0
            self.sv += src * vol
            self.v += vol
            self.ssv += vol * src * src

    @property
    def vwap(self):
        return (self.sv / self.v) if self.v > 0 else None

    @property
    def stdev(self):
        if self.v <= 0:
            return None
        m = self.sv / self.v
        var = self.ssv / self.v - m * m
        if var < 0:
            var = 0.0
        return math.sqrt(var)

    @property
    def band_high(self):
        m, s = self.vwap, self.stdev
        return None if (m is None or s is None) else m + VWAP_BAND_MULT * s

    @property
    def band_low(self):
        m, s = self.vwap, self.stdev
        return None if (m is None or s is None) else m - VWAP_BAND_MULT * s


# =============================================================== vector
def classify(o, h, l, c, vol, avg_vol10, highest_vol_spread10):
    """VectorClassifier.Classify, transcribed verbatim.
    'Close > Open is bullish. Close == Open follows the bearish branch.'
    'High/climax logic has priority over medium-vector logic.'"""
    bullish = c > o
    vs = vol * (h - l)
    if vol >= VECTOR_CLIMAX_MULT * avg_vol10 or vs >= highest_vol_spread10:
        return GREEN if bullish else RED
    if vol >= VECTOR_MEDIUM_MULT * avg_vol10:
        return BLUE if bullish else VIOLET
    return REG_BULL if bullish else REG_BEAR


def is_vector(v):
    return v in ELIGIBLE_VECTORS


# ======================================================= 15m aggregation
def bucket15(et_minutes_epoch):
    """Index of the 15m interval on the 18:00-ET-anchored grid."""
    return (et_minutes_epoch - DAY_START_MIN_ET) // 15


def bucket4h(et_minutes_epoch):
    """Index of the 4H interval on the 18:00-ET-anchored grid.
    18:00 anchoring divides the CME day into exactly six 4H bars
    (18, 22, 02, 06, 10, 14 ET)."""
    return (et_minutes_epoch - DAY_START_MIN_ET) // H4_MINUTES


# ==================================================== band interaction
# ONE definition, used identically for a COMPLETED 15m candle and for a
# DEVELOPING one. This is what removes the lookahead risk: the developing
# case is not a separate approximation, it is the same function evaluated
# at an earlier 1m bar.
#
#   TOUCHED_UP(t)  = any 1m bar from the interval start through t had
#                    high[i] >= band_high(i)     (band evaluated with data
#                                                 available through bar i)
#   REJECTED_UP(t) = close[t] <  band_high(t)
#   Mirror for the lower band.
#
# Exact boundary contact counts as a touch (>= / <=), per the directive.
def touched_up(hi, band):
    return band is not None and hi >= band


def touched_dn(lo, band):
    return band is not None and lo <= band


def rejected_up(close, band):
    return band is not None and close < band


def rejected_dn(close, band):
    return band is not None and close > band
