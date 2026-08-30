#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01 — LEVEL HIERARCHY, CLUSTERING, GEOMETRY ENGINE
# Frozen per MROF_YT_OF01_WAVE_FREEZE.md. Deterministic; no outcome
# computation. THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import math

TICK = 0.25

ACTIVE_FAMILIES = ('YDAY_RANGE', 'LWEEK_RANGE', 'OVERNIGHT_RANGE',
                   'OPEN', 'VWAP', 'PIVOT')
CONTEXT_FAMILIES = ('ADR', 'RUNNING_SESSION_EXTREME')
EXPERIMENTAL_FAMILIES = ('PSYCHOLOGICAL_RANGE',)

# level_id -> family (frozen map; each family counts at most once)
FAMILY_OF = {
    'YDAY_HIGH': 'YDAY_RANGE', 'YDAY_LOW': 'YDAY_RANGE',
    'LWEEK_HIGH': 'LWEEK_RANGE', 'LWEEK_LOW': 'LWEEK_RANGE',
    'OVERNIGHT_HIGH': 'OVERNIGHT_RANGE', 'OVERNIGHT_LOW': 'OVERNIGHT_RANGE',
    'GLOBEX_OPEN': 'OPEN', 'CASH_OPEN_0930': 'OPEN',
    'SESSION_VWAP': 'VWAP', 'VWAP_UPPER': 'VWAP', 'VWAP_LOWER': 'VWAP',
    'PP': 'PIVOT', 'M2': 'PIVOT', 'M3': 'PIVOT',
    'ADR_HIGH': 'ADR', 'ADR_LOW': 'ADR',
    'ADR_50_HIGH': 'ADR', 'ADR_50_LOW': 'ADR',
    'RUNNING_SESSION_HIGH': 'RUNNING_SESSION_EXTREME',
    'RUNNING_SESSION_LOW': 'RUNNING_SESSION_EXTREME',
    'PSY_HIGH': 'PSYCHOLOGICAL_RANGE', 'PSY_LOW': 'PSYCHOLOGICAL_RANGE',
}

ACTIVE_LEVEL_IDS = ('YDAY_HIGH', 'YDAY_LOW', 'LWEEK_HIGH', 'LWEEK_LOW',
                    'OVERNIGHT_HIGH', 'OVERNIGHT_LOW', 'GLOBEX_OPEN',
                    'CASH_OPEN_0930', 'SESSION_VWAP', 'VWAP_UPPER',
                    'VWAP_LOWER', 'PP', 'M2', 'M3')


# ---------------------------------------------------------------------
# pivot family (from the preceding COMPLETED session; S1/R1 are
# intermediate calculations only, never active entry locations)
# ---------------------------------------------------------------------
def pivots(yday_high, yday_low, yday_close):
    pp = (yday_high + yday_low + yday_close) / 3.0
    s1 = 2 * pp - yday_high
    r1 = 2 * pp - yday_low
    return dict(PP=pp, S1=s1, R1=r1, M2=(pp + s1) / 2.0, M3=(pp + r1) / 2.0)


# ---------------------------------------------------------------------
# opens and overnight extremes (Globex open != 09:30 cash open)
# ---------------------------------------------------------------------
def session_opens(events, globex_open_t, cash_open_t):
    """events: [(t, price)] time-sorted. GLOBEX_OPEN = first valid event
    at/after the official session start; CASH_OPEN_0930 = first valid
    event at/after 09:30:00 ET. Distinct by construction."""
    g = next((p for t, p in events if t >= globex_open_t), None)
    c = next((p for t, p in events if t >= cash_open_t), None)
    return dict(GLOBEX_OPEN=g, CASH_OPEN_0930=c)


def overnight_extremes(events, globex_open_t, cash_open_t, now_t):
    """High/low from Globex open through 09:29:59.999; FIXED at 09:30.
    Before 09:30 the values are still forming and are NOT available
    as frozen levels (returns available=False)."""
    win = [p for t, p in events if globex_open_t <= t < cash_open_t]
    if not win:
        return dict(available=False, OVERNIGHT_HIGH=None, OVERNIGHT_LOW=None)
    return dict(available=now_t >= cash_open_t,
                OVERNIGHT_HIGH=max(win), OVERNIGHT_LOW=min(win))


# ---------------------------------------------------------------------
# session VWAP + the ONE frozen band pair (VWAP +/- 2.0 sigma_w)
# ---------------------------------------------------------------------
class SessionVwap:
    """Causal running session VWAP with volume-weighted deviation
    bands. Reset exactly at the governing session boundary."""

    def __init__(self):
        self.sv = 0.0     # sum(v)
        self.svp = 0.0    # sum(v*p)
        self.svp2 = 0.0   # sum(v*p^2)

    def update(self, price, vol):
        self.sv += vol
        self.svp += vol * price
        self.svp2 += vol * price * price

    def state(self):
        if self.sv <= 0:
            return dict(SESSION_VWAP=None, VWAP_UPPER=None, VWAP_LOWER=None)
        vw = self.svp / self.sv
        var = max(self.svp2 / self.sv - vw * vw, 0.0)
        sd = math.sqrt(var)
        return dict(SESSION_VWAP=vw, VWAP_UPPER=vw + 2.0 * sd,
                    VWAP_LOWER=vw - 2.0 * sd)


# ---------------------------------------------------------------------
# ADR (UNVERIFIED_CONTEXT: barred from entry/grading/promotion until
# certified against the saved indicator; computed for the ledger only)
# ---------------------------------------------------------------------
ADR_STATUS = 'UNVERIFIED_CONTEXT'


def adr_state(prev14_ranges, run_high, run_low):
    if len(prev14_ranges) != 14:
        return dict(status='INSUFFICIENT_HISTORY')
    adr14 = sum(prev14_ranges) / 14.0
    return dict(status=ADR_STATUS, ADR14=adr14,
                ADR_HIGH=run_low + adr14, ADR_LOW=run_high - adr14,
                ADR_50_HIGH=run_low + 0.5 * adr14,
                ADR_50_LOW=run_high - 0.5 * adr14,
                ADR_USED=(run_high - run_low) / adr14 if adr14 > 0 else None)


# ---------------------------------------------------------------------
# PSY-NQ-01 weekly construction (futures-native adaptation)
# ---------------------------------------------------------------------
def psy_nq_week(events, sunday_open_t, tradable_seconds=8 * 3600):
    """PSY high/low = extremes of the first 8 TRADABLE hours after the
    official Sunday Globex weekly open. events: [(t, price)] with t in
    seconds; tradable time excludes halts by construction when the
    caller supplies only tradable-session events. The level is
    UNAVAILABLE until the full window has elapsed."""
    t_end = sunday_open_t + tradable_seconds
    win = [p for t, p in events if sunday_open_t <= t < t_end]
    have_end = any(t >= t_end for t, _ in events)
    if not win or not have_end:
        return dict(available=False, PSY_HIGH=None, PSY_LOW=None,
                    available_from=None)
    return dict(available=True, PSY_HIGH=max(win), PSY_LOW=min(win),
                available_from=t_end)


def psy_nq_audit(contract_ids, gap_seconds, window_seconds=8 * 3600,
                 max_gap=600):
    """Deterministic pre-outcome audit: exact single front-contract
    identity and no material gap in the construction window. A
    continuous/back-adjusted series FAILS (no contract identity)."""
    if len(set(contract_ids)) != 1 or '' in contract_ids or \
            any('CONT' in c.upper() for c in contract_ids):
        return 'PSY_NQ_UNVERIFIED'
    if any(g > max_gap for g in gap_seconds):
        return 'PSY_NQ_INSUFFICIENT_DATA'
    return 'PSY_NQ_VERIFIED'


# ---------------------------------------------------------------------
# clustering: each family counts AT MOST once inside the radius
# ---------------------------------------------------------------------
def family_counts(levels, price, radius):
    """levels: {level_id: value}. Returns the frozen counts. PSY is
    reported separately and never joins either base count here."""
    fams = set()
    for lid, v in levels.items():
        if v is None or lid not in FAMILY_OF:
            continue
        if abs(v - price) <= radius:
            fams.add(FAMILY_OF[lid])
    active = len([f for f in fams if f in ACTIVE_FAMILIES])
    allctx = len([f for f in fams if f in ACTIVE_FAMILIES + CONTEXT_FAMILIES])
    return dict(active_family_count=active,
                all_context_family_count=allctx,
                psy_experimental_present='PSYCHOLOGICAL_RANGE' in fams,
                families=sorted(fams))


def eligibility_radius(atr20_1m):
    """Common event-eligibility radius: max(4 ticks, 0.20 x ATR20-1m)."""
    return max(4 * TICK, 0.20 * atr20_1m)


# ---------------------------------------------------------------------
# target-space geometry and role gates
# ---------------------------------------------------------------------
def available_R(entry, stop, direction, levels, cluster_radius):
    """Transparent Available_R: nearest causally known registered level
    AHEAD of the trade, excluding levels inside the entry cluster.
    Frozen roles: <0.70 REJECT_GEOMETRY; >=2.00 A+ eligible."""
    risk = abs(entry - stop)
    if risk <= 0:
        return dict(Available_R=None, role='REJECT_GEOMETRY',
                    reason='zero risk distance')
    ahead = []
    for lid, v in levels.items():
        if v is None or lid not in FAMILY_OF:
            continue
        if abs(v - entry) <= cluster_radius:
            continue                       # inside entry cluster: excluded
        if (direction > 0 and v > entry) or (direction < 0 and v < entry):
            ahead.append((abs(v - entry), lid, v))
    if not ahead:
        return dict(Available_R=2.0, role='A_PLUS_ELIGIBLE',
                    reason='no opposing registered level before 2R',
                    next_opposing=None)
    d, lid, v = min(ahead)
    ar = d / risk
    role = ('REJECT_GEOMETRY' if ar < 0.70 else
            'A_PLUS_ELIGIBLE' if ar >= 2.00 else 'A_MINUS_B_PLUS_ONLY')
    return dict(Available_R=ar, role=role, next_opposing=lid,
                next_opposing_px=v, reason='')
