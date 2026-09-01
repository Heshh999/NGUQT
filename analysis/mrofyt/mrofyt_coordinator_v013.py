#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.3 — FINAL-PROMPT-EXACT SETUP COORDINATOR
# Additive successor. Predecessors f99c521 / 0bf0ec5 / 3aa0f61
# immutable. Implements the archived final prompt (SHA-256 74ff9a99...)
# sections 621 and 715-725 EXACTLY:
#   - no daily/weekly/any trade-count cap; the weekly floor is a
#     research minimum, never a throttle;
#   - re-arm has NO time cooldown: wall/test families reset via the
#     two-tick retreat/new-approach rule; all other families require
#     price to EXIT the proximity band and later RE-ENTER, with every
#     entry condition reforming from data after that exit;
#   - exact-timestamp signal groups: agreeing directions -> ONE
#     position under lowest-family-ID precedence with every agreeing
#     signal tagged; opposing directions -> NO fill, NO position, NO
#     TRADE_OPENED record; no arbitrary 1 ms window exists;
#   - open-position signals are recorded at their original time and
#     can never be entered later;
#   - SETUP_EPISODE_ID is deterministic and callback-order independent.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mrofyt_h1zones as HZ            # noqa: E402 (predecessor, untouched)

TICK = 0.25
SPEC_VERSION = 'MROF-YT-OF-01.3'
WALL_TEST_FAMILIES = ('A1', 'A2', 'A4')   # two-tick retreat/new-approach
FAMILY_ORDER = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6')


# ---------------------------------------------------------------------
# repair 6: strict 20-session control for EVERY baseline incl. H1 slots
# ---------------------------------------------------------------------
class StrictSlotBaseline(HZ.SlotBaseline):
    def __init__(self, n=20):
        super().__init__(n=n)
        self.n = n

    def z(self, slot, tr):
        vals = sorted(self.hist[slot])
        if len(vals) < self.n:
            return None
        med = vals[len(vals) // 2]
        mad = sorted(abs(v - med) for v in vals)[len(vals) // 2]
        if mad <= 0:
            return None
        return (tr - med) / (1.4826 * mad)


class SessionCalendar:
    """Versioned CME session calendar surface: valid hourly opens,
    holidays, maintenance breaks, DST-shifted sessions — supplied as
    data, queried causally."""

    def __init__(self, version, valid_hour_opens, holidays=(),
                 maintenance_hours=()):
        self.version = version
        self.valid = set(valid_hour_opens)
        self.holidays = set(holidays)
        self.maintenance = set(maintenance_hours)

    def bar_valid(self, bar):
        return (bar['t_open'] in self.valid and
                bar['t_open'] not in self.holidays and
                bar['t_open'] not in self.maintenance)


def find_zone_at_v013(bars, trz_strict, i, calendar):
    """Zone formation with EVERY bar of the swing/base/displacement
    window validated against the versioned calendar, exact contract
    identity, hourly alignment, and completed-bar timestamps. trz
    values must come from a StrictSlotBaseline (20 full sessions)."""
    first_needed = max(i - 3 - 5, 0)
    window = bars[first_needed:i + 1]
    contracts = {x.get('contract', '') for x in window}
    if len(contracts) != 1 or '' in contracts or \
            any('CONT' in c.upper() for c in contracts):
        return None
    for k, b in enumerate(window):
        if not calendar.bar_valid(b):
            return None
        if b['t_close'] - b['t_open'] != 3600 or \
                b.get('last_event_t', 1e18) > b['t_close']:
            return None
        if k > 0 and b['t_open'] != window[k - 1]['t_close']:
            return None
    return HZ.find_zone_at(bars, trz_strict, i)


# ---------------------------------------------------------------------
# repair 5: event-driven liquidity — an unchanged repeated quote is
# NOT new liquidity; only genuine executions/replenishment changes add
# ---------------------------------------------------------------------
def fill_event_driven(quotes, decision_t, direction, qty,
                      latency_s=0.150):
    """quotes: [(t, bid, bsz, ask, asz)] time-sorted. Availability =
    the displayed size on the taken side of the FIRST valid quote after
    release, then only POSITIVE changes: a size increase at the same
    price (replenishment) or a new price level. A repeated identical
    quote contributes nothing."""
    rel = decision_t + latency_s
    remaining = float(qty)
    legs = []
    last = None                    # (px, sz) last seen on taken side
    avail = 0.0
    for t, b, bs, a, asz in quotes:
        if t <= rel or remaining <= 0:
            continue
        if bs <= 0 or asz <= 0 or b >= a:
            continue
        px, sz = (a, float(asz)) if direction > 0 else (b, float(bs))
        if last is None:
            avail = sz
        elif px != last[0]:
            avail = sz                       # new level = new liquidity
        elif sz > last[1]:
            avail += sz - last[1]            # genuine replenishment only
        # unchanged or decreased display adds nothing
        take = min(remaining, avail)
        if take > 0:
            legs.append((t, px, take))
            remaining -= take
            avail -= take
        last = (px, sz)
    filled = qty - remaining
    if filled <= 0:
        return dict(filled=0.0, vwap=None, legs=[], missed=True,
                    partial=False)
    return dict(filled=filled,
                vwap=sum(p * q for _, p, q in legs) / filled,
                legs=legs, missed=False, partial=filled < qty)


# ---------------------------------------------------------------------
# repair 7: wall-episode identity + lifecycle
# ---------------------------------------------------------------------
class WallEpisodeRegistryV013:
    """Identity = instrument|contract|session|side|price|approach.
    Opposite-side walls at one price NEVER merge; a later independent
    approach forms a NEW episode with the next approach ordinal."""

    TERMINAL = ('CLOSED_HOLD', 'CLOSED_FLUSH', 'CLOSED_UNRESOLVED',
                'RESET')

    def __init__(self, instrument, contract, session):
        self.meta = (instrument, contract, session)
        self.approach_n = collections.Counter()      # (side,px) -> n
        self.open = {}                               # (side,px) -> episode

    def open_episode(self, side, wall_px):
        key = (side, wall_px)
        if key in self.open:
            return self.open[key], 'ALREADY_OPEN'
        self.approach_n[key] += 1
        eid = 'WE|%s|%s|%s|%s|%.2f|approach%02d' % (
            self.meta[0], self.meta[1], self.meta[2], side, wall_px,
            self.approach_n[key])
        ep = dict(id=eid, side=side, px=wall_px, state='OPEN',
                  approach=self.approach_n[key])
        self.open[key] = ep
        return ep, 'NEW'

    def close_episode(self, side, wall_px, terminal):
        assert terminal in self.TERMINAL
        key = (side, wall_px)
        ep = self.open.pop(key)
        ep['state'] = terminal
        return ep


# ---------------------------------------------------------------------
# the v01.3 coordinator
# ---------------------------------------------------------------------
class CoordinatorV013:
    """Signals are submitted in exact-timestamp groups via
    on_signals(t, [...]); price path events via on_price(t, px) drive
    approach/re-arm state. No time cooldown exists anywhere."""

    def __init__(self, instrument, contract, session_date, levels,
                 family_of, radius, fill_fn=None, qty=1):
        self.instrument = instrument
        self.contract = contract
        self.session = session_date
        self.levels = dict(levels)          # level_id -> px
        self.family_of = dict(family_of)    # level_id -> level family
        self.radius = float(radius)
        self.fill_fn = fill_fn or fill_event_driven
        self.qty = qty
        self.position = None
        self.episodes = {}
        self.log = []
        self._callbacks = set()
        # per reset-key state: 'ARMED' | 'SPENT'
        # reset key (repair 4): (anchor_px, signal family, direction) —
        # canonical cluster identity; display labels never enter.
        self._state = {}
        self._approach_n = collections.Counter()

    # -- canonical cluster identity -----------------------------------
    def _anchor(self, px):
        best = None
        for lid, v in self.levels.items():
            d = abs(v - px)
            if d <= self.radius and (best is None or d < best[0]):
                best = (d, v, lid)
        return best

    def _cluster_id(self, px):
        members = sorted((self.family_of.get(lid, lid),
                          round(v / TICK))
                         for lid, v in self.levels.items()
                         if abs(v - px) <= self.radius)
        h = hashlib.sha256(repr(members).encode()).hexdigest()[:8]
        return 'C%s' % h

    def _reset_key(self, family, direction, anchor_px):
        return (round(anchor_px / TICK), family, direction)

    # -- price path drives approach / re-arm (NO time component) ------
    def on_price(self, t, px):
        for key, st in list(self._state.items()):
            if st['mode'] != 'SPENT':
                continue
            anchor_px = key[0] * TICK
            family = key[1]
            if family in WALL_TEST_FAMILIES:
                # two-tick retreat from the level, then re-approach
                if not st.get('retreated') and \
                        abs(px - anchor_px) >= 2 * TICK:
                    st['retreated'] = True
                    st['t_retreat'] = t
                elif st.get('retreated') and \
                        abs(px - anchor_px) < 2 * TICK:
                    st['mode'] = 'ARMED'
                    st['reformed_after_t'] = st['t_retreat']
            else:
                # exit the proximity band, later re-enter
                if not st.get('exited') and abs(px - anchor_px) > self.radius:
                    st['exited'] = True
                    st['t_exit'] = t
                elif st.get('exited') and abs(px - anchor_px) <= self.radius:
                    st['mode'] = 'ARMED'
                    st['reformed_after_t'] = st['t_exit']

    # -- deterministic, callback-order-independent episode identity ---
    def _episode_id(self, family, cluster_id, approach):
        return 'SE|%s|%s|%s|%s|%s|%s|approach%03d' % (
            SPEC_VERSION, self.instrument, self.contract, self.session,
            family, cluster_id, approach)

    # -- exact-timestamp group resolution -----------------------------
    def on_signals(self, t, signals, quotes):
        """signals: list of dicts(family, direction, trigger_px,
        level_ids, callback_id, formed_from_t). ALL signals sharing an
        exact timestamp must be submitted in one group; resolution is
        independent of list order."""
        sigs = sorted(signals, key=lambda s: (
            FAMILY_ORDER.index(s['family'])
            if s['family'] in FAMILY_ORDER else 99, s['callback_id']))
        live = []
        for s in sigs:
            if s['callback_id'] in self._callbacks:
                self._emit(t, 'DUPLICATE_CALLBACK', s['callback_id'])
                continue
            self._callbacks.add(s['callback_id'])
            if not s.get('data_ok', True):
                self._emit(t, 'DATA_SUPPRESSED', s['callback_id'])
                continue
            if not s.get('risk_ok', True):
                self._emit(t, 'RISK_SUPPRESSED', s['callback_id'])
                continue
            anchor = self._anchor(s['trigger_px'])
            if anchor is None:
                self._emit(t, 'NOT_AT_ACTIVE_LEVEL', s['callback_id'])
                continue
            key = self._reset_key(s['family'], s['direction'], anchor[1])
            st = self._state.setdefault(key, dict(mode='ARMED'))
            if st['mode'] == 'SPENT':
                self._emit(t, 'REARM_PENDING', key)
                continue
            if 'reformed_after_t' in st and \
                    s.get('formed_from_t', t) <= st['reformed_after_t']:
                # entry conditions must reform ENTIRELY from later data
                self._emit(t, 'REARM_PENDING', key)
                continue
            live.append((s, key, anchor))
        if not live:
            return None
        # open-position suppression: recorded at original time, NEVER
        # entered later
        if self.position is not None:
            for s, _, _ in live:
                self._emit(t, 'NOT_FLAT_SUPPRESSED', s['callback_id'])
            return None
        dirs = {s['direction'] for s, _, _ in live}
        if len(dirs) > 1:
            # opposing exact ties: no fill, no position, no TRADE_OPENED
            self._emit(t, 'SIMULTANEOUS_DIRECTION_CONFLICT',
                       [s['callback_id'] for s, _, _ in live])
            return None
        # agreeing ties (or single): ONE position, lowest family ID
        # wins (sigs already family-ordered), every signal tagged
        s0, key0, anchor0 = live[0]
        fill = self.fill_fn(quotes, t, s0['direction'], self.qty)
        self._approach_n[key0] += 1
        cid = self._cluster_id(s0['trigger_px'])
        eid = self._episode_id(s0['family'], cid,
                               self._approach_n[key0])
        rec = dict(id=eid, t_signal=t, family=s0['family'],
                   direction=s0['direction'],
                   trigger_px=s0['trigger_px'], cluster=cid,
                   tagged=[s['callback_id'] for s, _, _ in live],
                   tagged_families=sorted({s['family']
                                           for s, _, _ in live}),
                   filled=fill['filled'], entry_vwap=fill['vwap'],
                   partial=fill.get('partial', False),
                   state='MISSED' if fill['missed'] else 'OPEN')
        self.episodes[eid] = rec
        for _, k, _ in live:
            self._state.setdefault(k, {})['mode'] = 'SPENT'
            self._state[k].pop('retreated', None)
            self._state[k].pop('exited', None)
        if fill['missed']:
            self._emit(t, 'EXECUTION_MISSED', eid)
            return None
        self.position = eid
        self.log.append(dict(t=t, reason='TRADE_OPENED', detail=eid))
        return rec

    def on_exit(self, eid, t_exit, exit_px):
        e = self.episodes[eid]
        assert e['id'] == eid
        e['state'] = 'CLOSED'
        e['t_exit'] = t_exit
        e['exit_px'] = exit_px
        if self.position == eid:
            self.position = None

    def _emit(self, t, reason, detail):
        self.log.append(dict(t=t, reason=reason, detail=detail))

    def trade_opened_records(self):
        return [x for x in self.log if x['reason'] == 'TRADE_OPENED']
