#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.2 — UNCAPPED INDEPENDENT-SETUP COORDINATOR
#                    + PRE-OUTCOME SPECIFICATION REPAIRS
# Additive successor module. Predecessors f99c521 / 0bf0ec5 immutable.
# No outcome ranking; classification remains INSUFFICIENT_DATA.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mrofyt_signals as SIG           # noqa: E402  (predecessor, untouched)
from mrofyt_signals import TICK        # noqa: E402

EPS = 1e-9

# frozen coordinator constants (v01.2; no variants may be searched)
REARM_SECONDS = 60.0          # same setup key re-arms 60s after flat, or
REARM_TICKS = 4               # ... at a trigger >= 4 ticks away
FILL_TIMEOUT_S = 5.0          # marketable window before EXECUTION_MISSED
SIMULT_EPS_S = 0.001          # signals within 1ms are simultaneous

SUPPRESS = ('OVERLAP_SUPPRESSED', 'SIMULTANEOUS_DIRECTION_CONFLICT',
            'RISK_SUPPRESSED', 'DATA_SUPPRESSED', 'EXECUTION_MISSED',
            'DUPLICATE_CALLBACK', 'NOT_FLAT_SUPPRESSED',
            'NOT_AT_ACTIVE_LEVEL', 'REARM_PENDING')


# ---------------------------------------------------------------------
# repair 1: strict baseline — ALL 20 prior completed sessions required
# ---------------------------------------------------------------------
class StrictBaseline(SIG.BaselineStore):
    """Standardized features are unavailable until the full 20-session
    causal history exists for the bucket (predecessor allowed >=5)."""

    def z(self, feat, second_of_day, value):
        vals = sorted(self.hist[(feat, self.bucket(second_of_day))])
        if len(vals) < self.n:
            return None
        med = vals[len(vals) // 2]
        mad = sorted(abs(v - med) for v in vals)[len(vals) // 2]
        return SIG.robust_z(value, med, mad)


# ---------------------------------------------------------------------
# repair 2+3: strict H1 construction — contract identity and hourly
# session alignment enforced INSIDE formation; no zone spans a roll
# ---------------------------------------------------------------------
def find_zone_at_strict(bars, trz, i):
    import mrofyt_h1zones as HZ
    b = bars[i]
    lo = i - 1
    # base can reach back at most 3 compact bars; swing 5 more
    first_needed = max(i - 3 - 5, 0)
    window = bars[first_needed:i + 1]
    contracts = {x.get('contract', '') for x in window}
    if len(contracts) != 1 or '' in contracts or \
            any('CONT' in c.upper() for c in contracts):
        return None                       # roll or identity failure
    for k in range(first_needed + 1, i + 1):
        if bars[k]['t_open'] != bars[k - 1]['t_open'] + 3600:
            return None                   # session/calendar misalignment
        if bars[k]['t_close'] - bars[k]['t_open'] != 3600 or \
                bars[k].get('last_event_t', 1e18) > bars[k]['t_close']:
            return None                   # incomplete/misaligned bar
    _ = lo
    return HZ.find_zone_at(bars, trz, i)


# ---------------------------------------------------------------------
# repair 4: liquidity-aware fills — requested quantity vs displayed
# size, partial fills across quotes, EXECUTION_MISSED on timeout
# ---------------------------------------------------------------------
def fill_with_liquidity(quotes, decision_t, direction, qty,
                        latency_s=SIG.LATENCY_BASE_S,
                        timeout_s=FILL_TIMEOUT_S):
    """Marketable sweep: each VALID quote strictly after
    decision+latency fills min(remaining, displayed size on the taken
    side). Returns dict(filled, vwap, legs, missed, first_t, last_t)."""
    rel = decision_t + latency_s
    deadline = decision_t + latency_s + timeout_s
    remaining = float(qty)
    legs = []
    for t, b, bs, a, asz in quotes:
        if t <= rel or remaining <= 0:
            continue
        if t > deadline:
            break
        if bs <= 0 or asz <= 0 or b >= a:
            continue
        px, avail = (a, asz) if direction > 0 else (b, bs)
        take = min(remaining, float(avail))
        legs.append((t, px, take))
        remaining -= take
    filled = qty - remaining
    if filled <= 0:
        return dict(filled=0.0, vwap=None, legs=[], missed=True,
                    partial=False)
    vwap = sum(p * q for _, p, q in legs) / filled
    return dict(filled=filled, vwap=vwap, legs=legs, missed=False,
                partial=filled < qty, first_t=legs[0][0],
                last_t=legs[-1][0])


# ---------------------------------------------------------------------
# repair 5: 30-minute cap has absolute precedence over any later signal
# ---------------------------------------------------------------------
def simulate_capped(quotes, entry_px, entry_t, direction, stop_px,
                    check_10s, check_control_loss,
                    max_hold_s=SIG.MAX_HOLD_S):
    """Wraps the predecessor management rules with a hard precedence:
    any event at or beyond the deadline exits TIME_30M before any
    window logic at that event can fire."""
    deadline = entry_t + max_hold_s
    pre = [q for q in quotes if q[0] < deadline]
    post = [q for q in quotes if q[0] >= deadline]
    res = SIG.simulate(pre, entry_px, entry_t, direction, stop_px,
                       check_10s, check_control_loss, max_hold_s)
    if res['exit'] != 'DATA_END':
        return res
    if post:
        t, b, bs, a, asz = post[0]
        px = b if direction > 0 else a
        risk = abs(entry_px - stop_px)
        return dict(exit='TIME_30M', px=px, t=t,
                    R=direction * (px - entry_px) / risk)
    return res


# ---------------------------------------------------------------------
# repair 6: bounded adverse large-print share in [0,1]
# ---------------------------------------------------------------------
def adverse_large_print_polarity(trades, position_dir, z_of_size):
    """The predecessor's signed value in [-1,+1], under its honest
    name. Kept verbatim via the v01.1 implementation."""
    import mrofyt_wall_engine as WE
    return WE.adverse_large_print_share(trades, position_dir, z_of_size)


def adverse_large_print_share_bounded(trades, position_dir, z_of_size):
    """Actual adverse-volume share: adverse large volume / total large
    volume, bounded [0,1]."""
    adv = tot = 0.0
    n = 0
    for _, _, sz, s in trades:
        z = z_of_size(sz)
        if z is None or z < 2.0:
            continue
        tot += sz
        n += 1
        if s * position_dir < 0:
            adv += sz
    if tot <= 0:
        return dict(share=None, count=0)
    return dict(share=adv / tot, count=n)


# ---------------------------------------------------------------------
# the uncapped independent-setup coordinator
# ---------------------------------------------------------------------
class SetupCoordinator:
    """One position at a time; while FLAT every independent valid setup
    may trade — there is NO daily or weekly trade-count cap. Episode
    IDs are immutable; duplicate callbacks, overlapping-level labels of
    one physical episode, simultaneous opposite-direction signals, risk
    and data failures, and missed executions are suppressed/recorded
    with explicit reasons. Active-level eligibility is enforced HERE,
    not by caller assumption."""

    def __init__(self, active_levels, radius, fill_fn=None, qty=1):
        self.levels = dict(active_levels)       # {level_id: px}
        self.radius = float(radius)
        self.fill_fn = fill_fn or fill_with_liquidity
        self.qty = qty
        self.seq = 0
        self.position = None                    # open episode id
        self.episodes = {}                      # id -> record (id immutable)
        self.log = []
        self._callbacks = set()
        self._last_flat = {}                    # setup_key -> (t, trigger_px)
        self._pending = []                      # same-timestamp buffer

    # -- internal ------------------------------------------------------
    def _emit(self, t, reason, detail):
        self.log.append(dict(t=t, reason=reason, detail=detail))
        return None

    def _setup_key(self, family, direction, level_id):
        return (family, direction, level_id)

    def _nearest_level(self, px):
        best = None
        for lid, v in self.levels.items():
            d = abs(v - px)
            if d <= self.radius and (best is None or d < best[0]):
                best = (d, lid)
        return best[1] if best else None

    # -- API -----------------------------------------------------------
    def on_signal(self, t, family, direction, trigger_px, level_ids,
                  callback_id, quotes, data_ok=True, risk_ok=True):
        """Returns the episode record for a NEW trade, else None (the
        decision log carries the exact suppression reason)."""
        if callback_id in self._callbacks:
            return self._emit(t, 'DUPLICATE_CALLBACK', callback_id)
        self._callbacks.add(callback_id)
        if not data_ok:
            return self._emit(t, 'DATA_SUPPRESSED', callback_id)
        if not risk_ok:
            return self._emit(t, 'RISK_SUPPRESSED', callback_id)
        lid = self._nearest_level(trigger_px)
        if lid is None:
            return self._emit(t, 'NOT_AT_ACTIVE_LEVEL', trigger_px)
        # simultaneous opposite-direction conflict (1ms window)
        for e in self.episodes.values():
            if abs(e['t_signal'] - t) <= SIMULT_EPS_S and \
                    e['direction'] == -direction and \
                    abs(e['trigger_px'] - trigger_px) <= self.radius:
                e['conflict'] = True
                if self.position == e['id']:
                    self.position = None       # both stand down
                e['state'] = 'SIMULTANEOUS_DIRECTION_CONFLICT'
                return self._emit(t, 'SIMULTANEOUS_DIRECTION_CONFLICT',
                                  (callback_id, e['id']))
        # overlapping-level suppression: one physical episode, N labels
        for e in self.episodes.values():
            if e['state'] in ('OPEN', 'FILLING') and \
                    e['direction'] == direction and \
                    abs(e['trigger_px'] - trigger_px) <= self.radius and \
                    t - e['t_signal'] <= REARM_SECONDS:
                e['level_ids'] = sorted(set(e['level_ids']) |
                                        set(level_ids) | {lid})
                return self._emit(t, 'OVERLAP_SUPPRESSED', e['id'])
        if self.position is not None:
            return self._emit(t, 'NOT_FLAT_SUPPRESSED', callback_id)
        # frozen re-arm: same setup key needs 60s after flat OR a
        # trigger displaced >= 4 ticks from the last one
        key = self._setup_key(family, direction, lid)
        lf = self._last_flat.get(key)
        if lf is not None and t - lf[0] < REARM_SECONDS and \
                abs(trigger_px - lf[1]) < REARM_TICKS * TICK:
            return self._emit(t, 'REARM_PENDING', key)
        # attempt execution (liquidity-aware; partial/missed modeled)
        fill = self.fill_fn(quotes, t, direction, self.qty)
        self.seq += 1
        eid = 'SE-%012.3f-%s-%+d-%05d' % (t, family, direction, self.seq)
        rec = dict(id=eid, t_signal=t, family=family, direction=direction,
                   trigger_px=trigger_px,
                   level_ids=sorted(set(level_ids) | {lid}),
                   filled=fill['filled'], entry_vwap=fill['vwap'],
                   partial=fill.get('partial', False),
                   state='MISSED' if fill['missed'] else 'OPEN',
                   conflict=False)
        self.episodes[eid] = rec
        if fill['missed']:
            self._emit(t, 'EXECUTION_MISSED', eid)
            return None
        self.position = eid
        self.log.append(dict(t=t, reason='TRADE_OPENED', detail=eid))
        return rec

    def on_exit(self, eid, t_exit, exit_px):
        e = self.episodes[eid]
        assert e['id'] == eid                   # immutable identity
        e['state'] = 'CLOSED'
        e['t_exit'] = t_exit
        e['exit_px'] = exit_px
        if self.position == eid:
            self.position = None
        key = self._setup_key(e['family'], e['direction'],
                              e['level_ids'][0])
        self._last_flat[key] = (t_exit, e['trigger_px'])

    def trades(self):
        return [e for e in self.episodes.values()
                if e['state'] in ('OPEN', 'CLOSED')]


# ---------------------------------------------------------------------
# repair 9: active-level eligibility + episode dedup INSIDE the wall
# engine path (not caller-enforced)
# ---------------------------------------------------------------------
class IntegratedWallGate:
    """Wraps the v01.1 wall engine: refuses any episode whose wall is
    outside the active-level eligibility radius and deduplicates one
    physical wall episode across overlapping level labels."""

    def __init__(self, active_levels, radius):
        self.levels = dict(active_levels)
        self.radius = float(radius)
        self._open = {}                         # wall_px -> episode

    def open_episode(self, wall_px, initial, wall_z, break_dir,
                     level_ids):
        import mrofyt_wall_engine as WE
        if not any(abs(v - wall_px) <= self.radius
                   for v in self.levels.values()):
            return None, 'NOT_AT_ACTIVE_LEVEL'
        if wall_px in self._open:
            ep = self._open[wall_px]
            ep.level_ids = sorted(set(ep.level_ids) | set(level_ids))
            return ep, 'OVERLAP_SUPPRESSED'
        ep = WE.WallEpisode(wall_px, initial, wall_z, break_dir)
        ep.level_ids = sorted(level_ids)
        self._open[wall_px] = ep
        return ep, 'NEW'


# ---------------------------------------------------------------------
# repair 8: genuine toggle-off parity harness — the same fixture run
# through the predecessor path and through the coordinator in
# passthrough mode must produce bit-identical signals/fills/P&L
# ---------------------------------------------------------------------
def run_predecessor(fix):
    px, ft = SIG.entry_fill(fix['quotes'], fix['t'], fix['dir'])
    if px is None:
        return dict(trade=None)
    res = SIG.simulate(fix['quotes'], px, ft, fix['dir'], fix['stop'],
                       fix['check_10s'], fix['check_cl'])
    y = SIG.y_dollars(fix['dir'], px, res['px']) if res['px'] else None
    return dict(trade=dict(entry=px, t=ft, exit=res['exit'],
                           exit_px=res['px'], y=y))


def run_through_coordinator_passthrough(fix):
    """Passthrough: single-quantity fill against full displayed size,
    predecessor simulate, no v01.2 module engaged beyond routing."""
    def fill_like_predecessor(quotes, t, d, qty):
        px, ft = SIG.entry_fill(quotes, t, d)
        if px is None:
            return dict(filled=0.0, vwap=None, legs=[], missed=True,
                        partial=False)
        return dict(filled=qty, vwap=px, legs=[(ft, px, qty)],
                    missed=False, partial=False, first_t=ft, last_t=ft)

    co = SetupCoordinator({'L': fix['level']}, 10.0,
                          fill_fn=fill_like_predecessor)
    rec = co.on_signal(fix['t'], 'A2', fix['dir'], fix['level'], ['L'],
                       'cb1', fix['quotes'])
    if rec is None:
        return dict(trade=None)
    _, ft = SIG.entry_fill(fix['quotes'], fix['t'], fix['dir'])
    res = SIG.simulate(fix['quotes'], rec['entry_vwap'], ft, fix['dir'],
                       fix['stop'], fix['check_10s'], fix['check_cl'])
    y = SIG.y_dollars(fix['dir'], rec['entry_vwap'], res['px']) \
        if res['px'] else None
    return dict(trade=dict(entry=rec['entry_vwap'], t=ft,
                           exit=res['exit'], exit_px=res['px'], y=y))


def digest(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True,
                                     default=str).encode()).hexdigest()
