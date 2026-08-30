#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01 — EVENT-TIER FEATURES, A1–A6 DETECTORS, EXECUTION SIM
# Frozen per MROF_YT_OF01_WAVE_FREEZE.md. Consumes MLES-CAPTURE-1.0.0
# events (see analysis/mrof/mrof_engine.py). NO outcome ranking exists
# here; the MROF State-C lock governs research use.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))

TICK = 0.25
MNQ_TICK_VALUE = 0.50           # $ per tick per contract
LATENCY_BASE_S = 0.150          # frozen; 0.300 / 0.500 are stresses
MAX_HOLD_S = 30 * 60            # 30-minute hard cap


# ---------------------------------------------------------------------
# MBP book reconstruction (levels indexed from 0 = best)
# ---------------------------------------------------------------------
class KLevelBook:
    def __init__(self, k=10):
        self.k = k
        self.bid = []            # list of [px, sz], best first
        self.ask = []

    def apply(self, op, side, level, px, sz):
        book = self.bid if side == 'bid' else self.ask
        if op == 'ADD':
            book.insert(level, [px, sz])
        elif op == 'UPDATE':
            if level < len(book):
                book[level] = [px, sz]
        elif op == 'REMOVE':
            if level < len(book):
                book.pop(level)
        del book[self.k:]

    def depth(self, side, k):
        book = self.bid if side == 'bid' else self.ask
        return sum(sz for _, sz in book[:k])

    def bi(self, k):
        b, a = self.depth('bid', k), self.depth('ask', k)
        return (b - a) / (b + a) if b + a > 0 else None


# ---------------------------------------------------------------------
# causal robust baselines: median/MAD over the SAME 5-minute
# time-of-day bucket from the PREVIOUS 20 completed sessions.
# ---------------------------------------------------------------------
def robust_z(x, med, mad):
    if mad is None or mad <= 0:
        return None
    return (x - med) / (1.4826 * mad)


class BaselineStore:
    def __init__(self, n_sessions=20):
        self.n = n_sessions
        self.hist = collections.defaultdict(
            lambda: collections.deque(maxlen=self.n))   # (feat,bucket)->vals
        self.cur = collections.defaultdict(list)         # current session

    @staticmethod
    def bucket(second_of_day):
        return int(second_of_day // 300)

    def observe(self, feat, second_of_day, value):
        self.cur[(feat, self.bucket(second_of_day))].append(value)

    def close_session(self):
        for key, vals in self.cur.items():
            if vals:
                self.hist[key].append(sorted(vals)[len(vals) // 2])
        self.cur = collections.defaultdict(list)

    def z(self, feat, second_of_day, value):
        vals = sorted(self.hist[(feat, self.bucket(second_of_day))])
        if len(vals) < 5:
            return None                       # insufficient causal history
        med = vals[len(vals) // 2]
        mad = sorted(abs(v - med) for v in vals)[len(vals) // 2]
        return robust_z(value, med, mad)


# ---------------------------------------------------------------------
# window feature calculators
# trades: [(t, px, sz, sign)]  quotes: [(t, bid, bsz, ask, asz)]
# ---------------------------------------------------------------------
def window(trades, t0, t1):
    return [x for x in trades if t0 <= x[0] < t1]


def aggr_delta(trades):
    d = sum(s * sz for _, _, sz, s in trades)
    q = sum(sz for _, _, sz, _ in trades)
    return d, (d / q if q > 0 else 0.0)


def intensity(trades, w):
    n = len(trades)
    q = sum(sz for _, _, sz, _ in trades)
    return n / w, q / w


def acceleration(trades, t_now, w):
    cur = sum(sz for x in window(trades, t_now - w, t_now) for sz in [x[2]])
    prev = sum(sz for x in window(trades, t_now - 2 * w, t_now - w)
               for sz in [x[2]])
    if prev <= 0 or cur <= 0:
        return None
    return math.log(cur / prev)


def price_response(mid_t0, mid_t1):
    return (mid_t1 - mid_t0) / TICK


def flow_efficiency(D, r_ticks, eps=1e-9):
    return math.copysign(1.0, D) * r_ticks / (abs(D) + eps) if D else 0.0


def replenishment_ratio(depth_added_after_exec, executed_at_level, eps=1e-9):
    return depth_added_after_exec / (executed_at_level + eps)


def depletion_ratio(executed_at_level, initial_depth, added_depth, eps=1e-9):
    return executed_at_level / (initial_depth + added_depth + eps)


def nontrade_withdrawal(depth_removed, executed_matched):
    """Removed size not explained by matched executions. MBP cannot
    prove cancellation; report the unmatched remainder, never intent."""
    return max(depth_removed - executed_matched, 0.0)


def vacuum_event(tgt_drop_frac, opp_drop_frac):
    """A3 structural condition: target-side 3-level depth falls >=60%
    within 2s without matched executions; opposite side falls <=20%."""
    return tgt_drop_frac >= 0.60 and opp_drop_frac <= 0.20


def resiliency(depleted_t, restored_t, censor_s=30.0):
    """Time until 50% of depleted 3-level depth restores; right-censored."""
    if restored_t is None or restored_t - depleted_t > censor_s:
        return dict(censored=True, time_s=censor_s)
    return dict(censored=False, time_s=restored_t - depleted_t)


def control_score(z_delta, z_ofi, z_bi3, z_resp):
    """Equal-weight frozen composite; None inputs disqualify."""
    zs = [z_delta, z_ofi, z_bi3, z_resp]
    if any(z is None for z in zs):
        return None
    return sum(zs) / 4.0


def persistence(trades, t0, direction, sub_s=2.5, n_sub=4):
    """3-of-4 same-direction subwindows inside the 10s decision window.
    Returns (n_agree, decay = final/first absolute intensity ratio)."""
    agree = 0
    first_q = last_q = None
    for i in range(n_sub):
        sub = window(trades, t0 + i * sub_s, t0 + (i + 1) * sub_s)
        d, _ = aggr_delta(sub)
        q = sum(sz for _, _, sz, _ in sub)
        if i == 0:
            first_q = q
        if i == n_sub - 1:
            last_q = q
        if d * direction > 0:
            agree += 1
    decay = (last_q / first_q) if first_q else None
    return agree, decay


def sweep(trades, max_span_s=1.0, min_levels=3):
    """Same-direction sequence consuming >= min_levels consecutive
    price levels inside one second. Returns None or the sweep record."""
    for i in range(len(trades)):
        px_seen = [trades[i][1]]
        for j in range(i + 1, len(trades)):
            if trades[j][0] - trades[i][0] > max_span_s:
                break
            if trades[j][3] != trades[i][3] or trades[i][3] == 0:
                break
            if trades[j][1] != px_seen[-1]:
                step = trades[j][1] - px_seen[-1]
                if abs(abs(step) - TICK) > 1e-9 or \
                        (len(px_seen) > 1 and
                         math.copysign(1, step) != math.copysign(
                             1, px_seen[-1] - px_seen[-2])):
                    break
                px_seen.append(trades[j][1])
            if len(px_seen) >= min_levels:
                return dict(t0=trades[i][0], dir=trades[i][3],
                            levels=len(px_seen), pre_px=px_seen[0],
                            end_px=px_seen[-1])
    return None


def sweep_reclaimed(swp, mids, within_s=5.0):
    """Price reclaims the pre-sweep level inside 5 seconds."""
    for t, m in mids:
        if swp['t0'] < t <= swp['t0'] + within_s:
            if (swp['dir'] > 0 and m <= swp['pre_px']) or \
                    (swp['dir'] < 0 and m >= swp['pre_px']):
                return True
    return False


def spread_dominance(quotes_before, quotes_after, p95_spread):
    """When spread > causal p95: which side closes it, time to close,
    signed mid change. Context/diagnostic only."""
    if not quotes_before or not quotes_after:
        return None
    t0, b0, _, a0, _ = quotes_before[-1]
    if (a0 - b0) / TICK <= p95_spread:
        return None
    for t, b, _, a, _ in quotes_after:
        if (a - b) / TICK <= p95_spread:
            side = 'BID_UP' if b - b0 >= a0 - a else 'ASK_DOWN'
            return dict(side=side, close_s=t - t0,
                        mid_chg=((a + b) - (a0 + b0)) / 2.0 / TICK)
    return dict(side='UNCLOSED', close_s=None, mid_chg=None)


def pause_quality(impulse_q, pause_q, adverse_z):
    """Frozen low-volume pause: pause quantity <= 50% of the preceding
    equal-duration impulse AND no adverse-flow z >= 1.0."""
    if impulse_q <= 0:
        return False
    return pause_q <= 0.50 * impulse_q and \
        (adverse_z is None or adverse_z < 1.0)


# ---------------------------------------------------------------------
# A1–A6 detectors — pure threshold composition of prepared features.
# Each input is already causally computed/z-scored; a None disqualifies.
# ---------------------------------------------------------------------
def _ok(*vals):
    return all(v is not None for v in vals)


def a1_absorption_reversal(f):
    if not _ok(f.get('aggr_z'), f.get('progress_ticks'),
               f.get('replenish_z'), f.get('approaches_60s'),
               f.get('opp_flip_z'), f.get('retreat_ticks')):
        return 0
    if f['aggr_z'] >= 2.0 and f['progress_ticks'] <= 1 and \
            f['replenish_z'] >= 1.5 and f['approaches_60s'] >= 2 and \
            f['opp_flip_z'] >= 1.0 and f['retreat_ticks'] >= 1:
        return -f['aggr_dir']            # trade AWAY from absorbed side
    return 0


def a2_depletion_continuation(f):
    if not _ok(f.get('wall_z'), f.get('exec_vs_displayed'),
               f.get('replenish_ratio'), f.get('cleared_held_5s'),
               f.get('persist_agree'), f.get('post_clear_z')):
        return 0
    if f['wall_z'] >= 2.0 and f['exec_vs_displayed'] >= 1.5 and \
            f['replenish_ratio'] < 0.25 and f['cleared_held_5s'] and \
            f['persist_agree'] >= 3 and f['post_clear_z'] >= 1.0:
        return f['break_dir']
    return 0


def a3_vacuum_continuation(f):
    if not f.get('actions_distinguishable'):
        return 0                          # family unavailable on this feed
    if not _ok(f.get('tgt_drop_frac'), f.get('opp_drop_frac'),
               f.get('delta_z'), f.get('advance_ticks')):
        return 0
    if vacuum_event(f['tgt_drop_frac'], f['opp_drop_frac']) and \
            f['delta_z'] >= 1.0 and f['advance_ticks'] >= 1:
        return f['vacuum_dir']
    return 0


def a4_response_failure_reversal(f):
    if not _ok(f.get('aggr_z'), f.get('opp_flip_z')):
        return 0
    fail = ((f.get('resid_tail_5pct') is True) or
            (f.get('progress_ticks') is not None and
             f['progress_ticks'] <= 1))
    back = (f.get('returned_through_level') is True) or \
           (f.get('sweep_reclaimed_5s') is True)
    if f['aggr_z'] >= 2.0 and fail and back and f['opp_flip_z'] >= 1.0:
        return -f['aggr_dir']
    return 0


def a5_pullback_resumption(f):
    if not _ok(f.get('trend_dir'), f.get('adverse_z'),
               f.get('adverse_progress_ticks'), f.get('replenish_z'),
               f.get('trend_flip_z')):
        return 0
    if f['trend_dir'] != 0 and f['adverse_z'] >= 2.0 and \
            f['adverse_progress_ticks'] <= 1 and \
            f['replenish_z'] >= 1.5 and f['trend_flip_z'] >= 1.0:
        return f['trend_dir']
    return 0


def a6_open_continuation(f):
    if not f.get('in_0930_0945'):
        return 0
    if not _ok(f.get('control_z'), f.get('clean_cross'),
               f.get('held_5s'), f.get('persist_agree'),
               f.get('opp_replenish_z')):
        return 0
    if f['control_z'] >= 2.0 and f['clean_cross'] and f['held_5s'] and \
            f['persist_agree'] >= 3 and f['opp_replenish_z'] < 1.5:
        return f['break_dir']
    return 0


DETECTORS = dict(A1=a1_absorption_reversal, A2=a2_depletion_continuation,
                 A3=a3_vacuum_continuation, A4=a4_response_failure_reversal,
                 A5=a5_pullback_resumption, A6=a6_open_continuation)


# ---------------------------------------------------------------------
# execution state machine (one position; frozen exits)
# quotes: [(t, bid, bsz, ask, asz)] strictly time-sorted
# ---------------------------------------------------------------------
def entry_fill(quotes, signal_t, direction, latency_s=LATENCY_BASE_S,
               slippage_ticks=0.0):
    """First executable quote STRICTLY after signal_t + latency."""
    rel = signal_t + latency_s
    for t, b, bs, a, asz in quotes:
        if t <= rel or bs <= 0 or asz <= 0 or b >= a:
            continue
        px = a if direction > 0 else b
        return px + direction * slippage_ticks * TICK, t
    return None, None


def structural_stop(event_extreme, direction, atr20_1m):
    """Beyond the event-window extreme + max(2 ticks, 0.10 x ATR20-1m)."""
    pad = max(2 * TICK, 0.10 * atr20_1m)
    return event_extreme - direction * pad


def simulate(quotes, entry_px, entry_t, direction, stop_px,
             check_10s, check_control_loss, max_hold_s=MAX_HOLD_S):
    """Frozen management: stop / 2R target / 10s early-invalidation /
    later control-loss / 30-minute cap — whichever executable first.
    check_10s(t_win_end) -> (fav_excursion_ticks, persist_agree)
    check_control_loss(t_win_end) -> (opp_control_z, crossed_entry)"""
    risk = abs(entry_px - stop_px)
    target = entry_px + direction * 2.0 * risk
    confirmed = False
    next_10s = entry_t + 10.0
    for t, b, bs, asz_b, asz in quotes:
        if t <= entry_t:
            continue
        exec_px = b if direction > 0 else asz_b     # executable side
        # stop first (adverse), then target — frozen conservative order
        if (direction > 0 and b <= stop_px) or \
                (direction < 0 and asz_b >= stop_px):
            return dict(exit='STOP', px=min(stop_px, b) if direction > 0
                        else max(stop_px, asz_b), t=t, R=-1.0)
        if (direction > 0 and b >= target) or \
                (direction < 0 and asz_b <= target):
            return dict(exit='TARGET_2R', px=target, t=t, R=2.0)
        while t >= next_10s:
            fav, agree = check_10s(next_10s)
            if not confirmed:
                if fav < 1 and agree < 3:
                    return dict(exit='EARLY_INVALIDATION', px=exec_px,
                                t=t, R=direction * (exec_px - entry_px) / risk)
                confirmed = True
            else:
                opp_z, crossed = check_control_loss(next_10s)
                if opp_z is not None and opp_z >= 1.0 and crossed:
                    return dict(exit='CONTROL_LOSS', px=exec_px, t=t,
                                R=direction * (exec_px - entry_px) / risk)
            next_10s += 10.0
        if t - entry_t >= max_hold_s:
            return dict(exit='TIME_30M', px=exec_px, t=t,
                        R=direction * (exec_px - entry_px) / risk)
    return dict(exit='DATA_END', px=None, t=None, R=None)


def y_dollars(direction, entry_px, exit_px, qty=1,
              commissions=0.37 * 2, fees=0.0, slippage_usd=0.0,
              tick_value=MNQ_TICK_VALUE):
    """Y_j = dir x ((exit-entry)/tick) x tick_value x qty - costs."""
    ticks = direction * (exit_px - entry_px) / TICK
    return ticks * tick_value * qty - commissions - fees - slippage_usd
