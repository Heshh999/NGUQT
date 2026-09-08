#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.7 — LIQUIDITY-TARGET AND FLOW-CONTROLLED EXIT EXPERIMENT
#
# Additive. v01.6 took the swing identifier, so the exit wave is v01.7.
#
# Three arms, and only three:
#   E0  parent parity        - the frozen baseline exits, unchanged
#   E1  liquidity hybrid     - parent stop/invalidation/flat/timeout, the
#                              fixed target REPLACED by a frozen
#                              opposing-wall trigger one tick in front
#   E2  flow-controlled      - parent stop/invalidation/flat/timeout, the
#                              fixed target REMOVED, exit on confirmed
#                              opposing control
#
# No scaling-in, partial-profit, breakeven, trailing-stop or runner
# variant is introduced. Entries, entry eligibility, initial protective
# stops, sizing, session windows and the 30-minute cap are UNCHANGED.
#
# NQ carries flow and control features; MNQ carries the executable
# liquidity target and every fill. An NQ wall price is never transferred
# into an MNQ order: no such mapping experiment is authorized.
#
# Market-outcome research over genuine captures is gated by the
# inherited State-C readiness lock (see research_driver). The arms
# themselves are pure functions so their behaviour can be proved on
# fixtures without opening outcomes.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

import mrof_engine as ME               # noqa: E402
import mrofyt_signals as SIG           # noqa: E402

SPEC_VERSION = 'MROF-YT-OF-01.7'
TICK = SIG.TICK
LATENCY_S = SIG.LATENCY_BASE_S
MAX_HOLD_S = SIG.MAX_HOLD_S

ARMS = ('E0', 'E0_EXEC', 'E1', 'E2')

# ---- frozen E1 wall-selection constants (initial research choices,
# ---- NOT established optimal settings; not to be tuned on results) ----
WALL_Z_MIN = 2.0           # displayed size at selection time
WALL_PERSIST_S = 2.0       # continuous visibility at the same price
WALL_PERSIST_Z_MIN = 1.5   # z throughout the persistence interval
TRIGGER_OFFSET_TICKS = 1   # take profit ONE tick before the wall

# ---- frozen E2 constants (inherited window and persistence grid) -----
E2_CONTROL_Z_MIN = 1.0
E2_SUBWINDOWS_REQUIRED = 3   # of four
E2_SUBWINDOWS_TOTAL = 4
E2_ADVERSE_TICKS_MIN = 1     # NQ ticks, completed window
DECISION_S = 10.0

# selection outcome labels — a fallback is NEVER a liquidity-target trade
TARGET_SELECTED = 'LIQUIDITY_TARGET_SELECTED'
NO_QUALIFYING = 'NO_QUALIFYING_LIQUIDITY_TARGET'
DATA_UNAVAILABLE = 'TARGET_DATA_UNAVAILABLE'

# book-accounting attributions kept SEPARATE; MBP changes do not always
# identify a cancellation, so ambiguity is recorded as unknown
BOOK_EVENTS = ('EXECUTED', 'DISPLAYED_ADD', 'NET_SIZE_CHANGE', 'REMOVED',
               'VISIBILITY_LOST', 'UNKNOWN_ATTRIBUTION')


# ---------------------------------------------------------------------
# book helpers
# ---------------------------------------------------------------------
def side_for(direction):
    """A long takes profit into the ASK; a short into the BID."""
    return 'ask' if direction > 0 else 'bid'


def levels_at(snapshot, side):
    """[(rank, price, size)] for one side of one snapshot."""
    return [(i, px, sz) for i, (px, sz) in enumerate(snapshot.get(side, []))]


def wall_feat(side, rank):
    """Baseline slot: instrument-scoped store, keyed by side and depth
    rank. Slot definitions are frozen before any research."""
    return 'wall|%s|%d' % (side, rank)


def visible_at(snapshot, side, price):
    for i, (px, sz) in enumerate(snapshot.get(side, [])):
        if abs(px - price) < TICK / 2.0:
            return i, sz
    return None, None


# ---------------------------------------------------------------------
# frozen E1 wall selection
# ---------------------------------------------------------------------
def select_liquidity_target(snapshots, t_init, entry_px, direction,
                            baseline, sod_of, parent_target,
                            z_min=WALL_Z_MIN, persist_s=WALL_PERSIST_S,
                            persist_z_min=WALL_PERSIST_Z_MIN):
    """Choose the nearest qualifying opposing MNQ wall at the parent's
    target-initialization time, using the latest valid book available
    THEN. Returns a frozen selection dict; it never moves afterwards.

    A candidate must lie strictly beyond the actual entry fill in the
    profitable direction, sit inside the currently supported visible
    depth, carry displayed size at robust time-of-day z >= 2.0, and have
    been continuously visible at the SAME price for the preceding two
    seconds with z >= 1.5 throughout the supported observations.

    Missing baselines or a zero MAD make a candidate unavailable. No
    outcome-tuned epsilon is added to rescue one."""
    side = side_for(direction)
    cur = [s for s in snapshots if s['t'] <= t_init]
    if not cur:
        return dict(status=DATA_UNAVAILABLE, reason='NO_BOOK_AT_T_INIT',
                    trigger=None, target=parent_target, wall=None)
    snap = cur[-1]
    if not snap.get('healthy', True):
        # an unhealthy or disconnected book is not the same thing as a
        # valid level that simply has not changed recently
        return dict(status=DATA_UNAVAILABLE, reason='FEED_UNHEALTHY',
                    trigger=None, target=parent_target, wall=None)
    window = [s for s in snapshots
              if t_init - persist_s <= s['t'] <= t_init]
    if not window or window[0]['t'] > t_init - persist_s + 1e-9:
        return dict(status=DATA_UNAVAILABLE,
                    reason='INCOMPLETE_PERSISTENCE_HISTORY',
                    trigger=None, target=parent_target, wall=None)
    if any(not s.get('healthy', True) for s in window):
        return dict(status=DATA_UNAVAILABLE, reason='FEED_UNHEALTHY',
                    trigger=None, target=parent_target, wall=None)

    sod = sod_of(t_init)
    cands = []
    for rank, px, sz in levels_at(snap, side):
        beyond = px > entry_px if direction > 0 else px < entry_px
        if not beyond:
            continue                       # must be profitable-direction
        z = baseline.z(wall_feat(side, rank), sod, sz)
        if z is None or z < z_min:
            continue                       # no baseline, zero MAD, or small
        ok = True
        for s in window:
            r2, sz2 = visible_at(s, side, px)
            if r2 is None:
                ok = False                 # not continuously visible
                break
            z2 = baseline.z(wall_feat(side, r2), sod_of(s['t']), sz2)
            if z2 is None or z2 < persist_z_min:
                ok = False
                break
        if not ok:
            continue
        cands.append((abs(px - entry_px), px, rank, sz, z))
    if not cands:
        return dict(status=NO_QUALIFYING, reason='NO_CANDIDATE',
                    trigger=None, target=parent_target, wall=None)
    _d, px, rank, sz, z = min(cands)
    trig = px - TRIGGER_OFFSET_TICKS * TICK * (1 if direction > 0 else -1)
    still_beyond = trig > entry_px if direction > 0 else trig < entry_px
    if not still_beyond:
        # one tick in front of the wall is not beyond entry: there is no
        # profitable trigger here, so this is a fallback, not a target
        return dict(status=NO_QUALIFYING, reason='TRIGGER_NOT_BEYOND_ENTRY',
                    trigger=None, target=parent_target, wall=px)
    return dict(status=TARGET_SELECTED, reason=None, wall=px, side=side,
                rank=rank, size=sz, z=z, trigger=trig,
                selected_t=t_init, observation_window=[window[0]['t'],
                                                       t_init],
                target=trig, frozen=True)


def track_wall(snapshots, sel, t_from, t_to):
    """Diagnostic only. Subsequent wall changes are recorded; the frozen
    trigger is never chased, extended or reselected."""
    if not sel or sel.get('status') != TARGET_SELECTED:
        return []
    out = []
    for s in snapshots:
        if not (t_from <= s['t'] <= t_to):
            continue
        rank, sz = visible_at(s, sel['side'], sel['wall'])
        out.append(dict(t=s['t'], visible=rank is not None, rank=rank,
                        size=sz,
                        event='VISIBILITY_LOST' if rank is None
                        else 'NET_SIZE_CHANGE'))
    return out


# ---------------------------------------------------------------------
# exit execution
# ---------------------------------------------------------------------
def market_exit(quotes, decision_t, direction, qty, latency_s=LATENCY_S,
                consumed=None, slippage_ticks=0.0, window_s=None):
    """Simulated MARKET exit through the latency/fill engine.

    Closing a long sells into the bid; closing a short lifts the ask.
    Available quantity is respected, partial fills are real, and a
    snapshot already consumed is never filled against twice. An unfilled
    remainder is returned as still open - it is not cancelled and the
    trade is not pretended flat."""
    consumed = consumed if consumed is not None else set()
    rel = decision_t + latency_s
    deadline = None if window_s is None else rel + window_s
    remaining = float(qty)
    fills = []
    for t, b, bs, a, asz in quotes:
        if t <= rel:
            continue
        if deadline is not None and t > deadline:
            break
        if t in consumed:
            continue                       # never re-fill a used snapshot
        if bs <= 0 or asz <= 0 or b >= a:
            continue                       # crossed or empty book
        px, avail = (b, float(bs)) if direction > 0 else (a, float(asz))
        px = px - direction * slippage_ticks * TICK
        take = min(remaining, avail)
        if take <= 0:
            continue
        consumed.add(t)
        fills.append(dict(t=t, px=px, qty=take))
        remaining -= take
        if remaining <= 1e-12:
            break
    filled = sum(f['qty'] for f in fills)
    vwap = (sum(f['px'] * f['qty'] for f in fills) / filled) if filled \
        else None
    return dict(fills=fills, filled=filled, remaining=remaining,
                vwap=vwap, t_first=fills[0]['t'] if fills else None,
                t_last=fills[-1]['t'] if fills else None,
                unresolved=remaining > 1e-12,
                decision_t=decision_t)


# ---------------------------------------------------------------------
# E2 opposing-control condition
# ---------------------------------------------------------------------
def opposing_control_exit(control_z_opposing, subwindows_opposing,
                          nq_adverse_ticks):
    """All three must hold at a COMPLETED 10-second window:

      1. the signed control score favours the direction OPPOSITE the
         position at magnitude z >= 1.0 (signed control, never unsigned
         intensity);
      2. at least three of the four subwindows favour that opposing
         direction;
      3. NQ price progress across the completed window is adverse to the
         position by at least one NQ tick.

    A missing feature is UNKNOWN, not zero and not favourable control,
    so it returns False rather than an exit."""
    if control_z_opposing is None or subwindows_opposing is None or \
            nq_adverse_ticks is None:
        return False
    return (control_z_opposing >= E2_CONTROL_Z_MIN and
            subwindows_opposing >= E2_SUBWINDOWS_REQUIRED and
            nq_adverse_ticks >= E2_ADVERSE_TICKS_MIN)


# ---------------------------------------------------------------------
# the arms
# ---------------------------------------------------------------------
class Trade(object):
    """One frozen parent entry. Entry fill, quantity, initial stop and
    initial risk are IDENTICAL across arms by construction."""

    __slots__ = ('entry_px', 'entry_t', 'direction', 'qty', 'stop_px',
                 'atr20', 'session_flat_t', 'id')

    def __init__(self, tid, entry_px, entry_t, direction, stop_px, qty=1,
                 atr20=None, session_flat_t=None):
        self.id = tid
        self.entry_px = float(entry_px)
        self.entry_t = float(entry_t)
        self.direction = int(direction)
        self.qty = float(qty)
        self.stop_px = float(stop_px)
        self.atr20 = atr20
        self.session_flat_t = session_flat_t

    @property
    def risk(self):
        return abs(self.entry_px - self.stop_px)

    @property
    def parent_target(self):
        return self.entry_px + self.direction * 2.0 * self.risk


def run_e0(trade, quotes, check_10s, check_control_loss,
           max_hold_s=MAX_HOLD_S):
    """E0 parity: the authoritative parent exits, unchanged.

    This delegates to mrofyt_signals.simulate rather than restating it,
    so the arm cannot drift away from the parent it is supposed to
    reproduce. Note that the parent's own convention resolves an exit AT
    the decision price with no latency and no partial fill."""
    r = SIG.simulate(quotes, trade.entry_px, trade.entry_t,
                     trade.direction, trade.stop_px, check_10s,
                     check_control_loss, max_hold_s)
    return dict(arm='E0', trade=trade.id, exit=r['exit'], px=r['px'],
                t=r['t'], R=r['R'], filled=trade.qty, remaining=0.0,
                unresolved=False, parity_source='mrofyt_signals.simulate')


def _exec_result(arm, trade, reason, decision_t, fill, extra=None):
    px = fill['vwap']
    R = (None if px is None or trade.risk <= 0 else
         trade.direction * (px - trade.entry_px) / trade.risk)
    d = dict(arm=arm, trade=trade.id, exit=reason, px=px,
             t=fill['t_last'], decision_t=decision_t, R=R,
             filled=fill['filled'], remaining=fill['remaining'],
             unresolved=fill['unresolved'], fills=fill['fills'])
    if extra:
        d.update(extra)
    return d


def run_arm(arm, trade, quotes, check_10s, check_control_loss,
            e2_check=None, target_sel=None, latency_s=LATENCY_S,
            max_hold_s=MAX_HOLD_S, consumed=None, slippage_ticks=0.0):
    """E0_EXEC / E1 / E2 on a common event loop.

    Everything protective is shared and unchanged: the initial stop,
    the parent's 10-second early invalidation, its later control-loss
    exit, session flattening and the 30-minute cap. The arms differ ONLY
    in the profit-taking rule:

      E0_EXEC  the parent's fixed 2R target
      E1       the frozen liquidity trigger (or the parent's target when
               selection fell back, which is labelled, never reported as
               a liquidity-target trade)
      E2       no fixed target at all; exit on confirmed opposing control

    At a common decision timestamp protective exits take precedence over
    profit-taking, and every reason is recorded."""
    if arm not in ('E0_EXEC', 'E1', 'E2'):
        raise ValueError('run_arm handles E0_EXEC/E1/E2; E0 is run_e0')
    consumed = consumed if consumed is not None else set()
    d = trade.direction
    risk = trade.risk
    target = None
    if arm == 'E0_EXEC':
        target = trade.parent_target
    elif arm == 'E1':
        target = (target_sel or {}).get('target', trade.parent_target)
    confirmed = False
    next_10s = trade.entry_t + DECISION_S
    reasons = []
    for t, b, bs, a, asz in quotes:
        if t <= trade.entry_t:
            continue
        exec_px = b if d > 0 else a
        # ---- protective first, always -------------------------------
        hit_stop = (b <= trade.stop_px) if d > 0 else (a >= trade.stop_px)
        hit_target = target is not None and (
            (b >= target) if d > 0 else (a <= target))
        if hit_stop:
            if hit_target:
                reasons.append('TARGET_ALSO_TOUCHED')
            f = market_exit(quotes, t, d, trade.qty, latency_s, consumed,
                            slippage_ticks)
            return _exec_result(arm, trade, 'STOP', t, f,
                                dict(also=reasons, target=target))
        # ---- completed 10-second windows ----------------------------
        fired = None
        while t >= next_10s:
            if not confirmed:
                fav, agree = check_10s(next_10s)
                if fav is not None and agree is not None and \
                        fav < 1 and agree < 3:
                    fired = ('EARLY_INVALIDATION', next_10s)
                    break
                confirmed = True
            else:
                opp_z, crossed = check_control_loss(next_10s)
                if opp_z is not None and opp_z >= 1.0 and crossed:
                    fired = ('CONTROL_LOSS', next_10s)
                    break
                if arm == 'E2' and e2_check is not None:
                    cz, subs, adv = e2_check(next_10s)
                    if opposing_control_exit(cz, subs, adv):
                        fired = ('OPPOSING_CONTROL', next_10s)
                        break
            next_10s += DECISION_S
        if fired:
            # a completed-window condition can never exit at the window's
            # beginning: the decision time is the window END.
            # Protective and control exits take precedence over profit
            # taking at a common timestamp; the target touch is still
            # recorded so the reason is never lost.
            if hit_target:
                reasons.append('TARGET_ALSO_TOUCHED')
            f = market_exit(quotes, fired[1], d, trade.qty, latency_s,
                            consumed, slippage_ticks)
            return _exec_result(arm, trade, fired[0], fired[1], f,
                                dict(also=reasons, target=target))
        # ---- profit taking ------------------------------------------
        if hit_target:
            f = market_exit(quotes, t, d, trade.qty, latency_s, consumed,
                            slippage_ticks)
            lbl = 'TARGET_2R' if arm == 'E0_EXEC' else (
                'LIQUIDITY_TARGET'
                if (target_sel or {}).get('status') == TARGET_SELECTED
                else 'PARENT_TARGET_FALLBACK')
            return _exec_result(arm, trade, lbl, t, f,
                                dict(target=target,
                                     selection=(target_sel or {}
                                                ).get('status')))
        # ---- session flatten and hard timeout -----------------------
        flat = trade.session_flat_t is not None and t >= trade.session_flat_t
        if flat or t - trade.entry_t >= max_hold_s:
            dec = (trade.session_flat_t if flat
                   else trade.entry_t + max_hold_s)
            f = market_exit(quotes, dec, d, trade.qty, latency_s,
                            consumed, slippage_ticks)
            return _exec_result(
                arm, trade, 'SESSION_FLAT' if flat else 'TIME_30M', dec, f,
                dict(target=target,
                     deadline_fill_is_later=bool(
                         f['t_last'] is not None and f['t_last'] > dec)))
    return dict(arm=arm, trade=trade.id, exit='DATA_END', px=None, t=None,
                R=None, filled=0.0, remaining=trade.qty, unresolved=True,
                target=target)


# ---------------------------------------------------------------------
# the two evaluations
# ---------------------------------------------------------------------
def paired_attribution(trades, quotes_of, checks_of, selections=None):
    """Evaluation 1. Each frozen parent entry is replayed with IDENTICAL
    entry fill, quantity, initial stop and initial risk in isolated
    shadow trades, one per arm. This isolates the exits.

    These hypothetical trades may overlap in time. This is NOT a
    deployable portfolio equity curve, and liquidity consumed by one arm
    is never added to another's."""
    out = []
    for tr in trades:
        q = quotes_of(tr)
        c10, cctl, ce2 = checks_of(tr)
        sel = (selections or {}).get(tr.id)
        row = dict(trade=tr.id, entry_px=tr.entry_px, entry_t=tr.entry_t,
                   direction=tr.direction, stop_px=tr.stop_px,
                   qty=tr.qty, risk=tr.risk, selection=sel)
        row['E0'] = run_e0(tr, q, c10, cctl)
        for arm in ('E0_EXEC', 'E1', 'E2'):
            row[arm] = run_arm(arm, tr, q, c10, cctl, ce2, sel,
                               consumed=set())   # isolated per arm
        out.append(row)
    return dict(evaluation='PAIRED_EXIT_ATTRIBUTION', rows=out,
                caveat='Isolated shadow trades may overlap; this is not '
                       'a deployable equity curve and cross-arm '
                       'liquidity is not summed.')


def sequential_replay(arm, entries, quotes_of, checks_of, selections=None,
                      one_position=True):
    """Evaluation 2. One complete arm run independently under identical
    account limits, one-position gating and genuine re-arm rules.

    A faster or slower exit admits or suppresses different SUBSEQUENT
    entries, so the entry sets legitimately diverge between arms. That
    divergence is reported, not assumed away."""
    consumed = set()
    taken, skipped = [], []
    busy_until = None
    for tr in sorted(entries, key=lambda x: x.entry_t):
        if one_position and busy_until is not None and \
                tr.entry_t < busy_until:
            skipped.append(dict(trade=tr.id, reason='POSITION_OPEN',
                                blocked_until=busy_until))
            continue
        q = quotes_of(tr)
        c10, cctl, ce2 = checks_of(tr)
        sel = (selections or {}).get(tr.id)
        r = (run_e0(tr, q, c10, cctl) if arm == 'E0'
             else run_arm(arm, tr, q, c10, cctl, ce2, sel,
                          consumed=consumed))
        taken.append(r)
        busy_until = r.get('t') if r.get('t') is not None else busy_until
    return dict(evaluation='DEPLOYABLE_SEQUENTIAL_REPLAY', arm=arm,
                trades=taken, suppressed=skipped,
                entries_taken=len(taken), entries_suppressed=len(skipped),
                note='Entry sets differ between arms by design; exit '
                     'speed changes which later setups are reachable.')


# ---------------------------------------------------------------------
# research driver (State-C gated)
# ---------------------------------------------------------------------
PRIMARY_COMPARISONS = ('E1_minus_E0', 'E2_minus_E0')
SECONDARY_DIAGNOSTICS = ('E1_vs_E2', 'by_wall_size', 'by_side',
                         'by_time_of_day')
PRIMARY_ECONOMIC_METRIC = 'net_expectancy_per_trade_after_costs'
INFERENCE_METHOD = ('session-block resample; the two primary comparisons '
                    'are corrected jointly under the governing protocol')


def research_driver(*_a, **_k):
    """The only entrypoint that would open market outcomes over genuine
    captures. Locked until the committed State-C readiness freeze."""
    if not ME.research_unlocked():
        raise RuntimeError(
            'STATE-C LOCKED: exit-arm outcome research requires a '
            'committed readiness freeze (MROF_V1_STATE_C_AUTHORIZED.json).')
    raise NotImplementedError(
        'State-C exit research is a separate, later freeze; the arms and '
        'their fixtures are implemented, the study is not run.')
