#!/usr/bin/env python3
# ======================================================================
# RVMR-V1 - FROZEN SPECIFICATIONS
#   RANGE-REGIME-V1   (verbatim MAG_ALT_RNG)
#   VOLUME-REGIME-V1  (verbatim MAG_ALT_VOL)
# ======================================================================
# SOURCE OF TRUTH (read, not remembered), sha256 prefixes at freeze:
#   analysis/mag/mag_lib.py        c1b2a961cb2cd464   feature formulas
#   analysis/mag/mag_h3.py         a7cd3d0b057b2fe0   universe, buckets,
#                                                     labels, tables
#   analysis/mag/mag_h3_perm.py    54fe03d8b5c0de9d   day-clustered stats
#   analysis/mag/MAG_H3_OUTPUT.txt dc705ea8a4abdcd6   reproduction target
#   docs/MAG_PREREGISTRATION.md    0041f47e8ff5f37e   original freeze
#   src/V4Shared.cs (V4SessionMap) RthStartEt=570, RthEndEt=960
#
# EXACT FROZEN DEFINITIONS
#   trailing_ratio(x, W=1440):  x[i] / mean(x[i-1440 .. i-1])
#       - window is 1440 BARS (not wall-clock minutes), over the FULL
#         merged series including overnight bars
#       - the current bar is EXCLUDED from its own normaliser
#       - None until 1440 prior bars exist; None when the mean is <= 0
#   RANGE-REGIME-V1  = trailing_ratio(high - low)
#   VOLUME-REGIME-V1 = trailing_ratio(volume)
#   BUCKETS (identical numeric thresholds for BOTH tools - the original
#   implementation applied MAG_SCORE's U-partition terciles to the
#   benchmark scores too; that construction is preserved verbatim, NOT
#   recalibrated, era by era or ever):
#       LOW    score <  1.270
#       MEDIUM 1.270 <= score <= 2.335
#       HIGH   score >  2.335
#   UNIVERSE (per bar j, close-stamped ET):
#       - RTH:  570 <= hour*60+min <= 960          (09:30 .. 16:00)
#       - minutesToRthClose = 960 - minuteOfDay >= 60   (=> stamp <= 15:00)
#       - ATR(20) = SMA of true range over the 20 bars ending at j,
#         available and > 0  (same definition Phase 0 verified for the
#         V3 'atr' column: median abs err 0.0000, corr 1.00000)
#       - both regime scores non-None
#       - the next 60 bars exist and are minute-contiguous
#   LABELS at horizons H = (5, 10, 15, 30, 60), from close[j]:
#       abs_h = |close[j+h] - close[j]|
#       rng_h = max(close[j], high[j+1..j+h]) - min(close[j], low[j+1..j+h])
#       exc_h = MFE_h + MAE_h   (both from close[j], each floored at 0
#               implicitly by the running max construction)
#   PRIMARY STATISTICS (dependence-aware; a minute is never treated as
#   an independent trial):
#       - full-sample Spearman: POINT ESTIMATE only
#       - day-level Spearman: per-day median score vs per-day median
#         abs_30, Spearman across days; permutation p by shuffling whole
#         days (20,000); day bootstrap CI on bucket means (20,000)
#       - the day is the cluster unit; overlapping 60m windows inside a
#         day are handled by resampling whole days
#
# BASIS TRANSLATIONS for the five-year OHLCV data (each one reported,
# none of them changes the tool):
#   T1  volume = V3 bar volume (canonical year used ofTotalVolume from
#       the Volumetric feed) - agreement measured in the overlap year
#   T2  universe gate 'both scores non-None' replaces the canonical
#       'MAG_SCORE non-None' (MAG_SCORE needs delta, which does not
#       exist before 2025-08) - impact measured by Gate B
#   T3  bar contiguity uses real minute arithmetic rather than the
#       frozen D8 tmin quirk; provably identical on RTH windows, which
#       never span a month boundary
#
# DO NOT RECALIBRATE. If the tool fails on five years, it fails.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================

T1, T2 = 1.270, 2.335
W = 1440
HOR = (5, 10, 15, 30, 60)
SEED = 20260824
DISCOVERY_START = '2025-08-18'      # canonical capture begins here
RTH_START, RTH_END = 570, 960


def bucket(v):
    if v is None:
        return None
    return 'LOW' if v < T1 else ('MEDIUM' if v <= T2 else 'HIGH')


def trailing_ratio(vals, w=W):
    out = [None] * len(vals)
    s = 0.0
    for i, v in enumerate(vals):
        if i >= w:
            m = s / w
            out[i] = (v / m) if m > 0 else None
            s -= vals[i - w]
        s += v
    return out


def atr20(bars):
    """SMA(20) of true range - the definition Phase 0 verified exact
    against the V3 'atr' column. bars: list of (et,o,h,l,c,v) tuples."""
    out = [None] * len(bars)
    tr = []
    prev = None
    for i, b in enumerate(bars):
        t = b[2] - b[3] if prev is None else max(
            b[2] - b[3], abs(b[2] - prev), abs(b[3] - prev))
        tr.append(t)
        prev = b[4]
        if len(tr) > 20:
            tr.pop(0)
        if len(tr) == 20:
            out[i] = sum(tr) / 20.0
    return out
