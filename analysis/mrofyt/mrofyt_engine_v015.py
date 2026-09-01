#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.5 — EXECUTABLE RESEARCH ENGINE (sole entrypoint)
# Additive successor. v01.2/v01.3/v01.4 coordinators are superseded and
# immutable; nothing executable imports them.
#
# Repairs over v01.4 (requirement F):
#   F1 open-position state is checked BEFORE consumed/re-arm state, so
#      every valid signal arriving while a position is open is recorded
#      OVERLAP_SUPPRESSED (never REARM_PENDING).
#   F2 an adjudicated occurrence (conflict, risk suppression, data
#      suppression, missed execution, overlap suppression, trade) is
#      consumed; it can never be retried from stale data - a causal
#      reset AND later-formed conditions are required.
#   F3 physical approach IDs are minted at the PRICE EVENT that begins
#      the approach, before any signal or fill exists.
#   F4 the union of every agreeing signal's level IDs, level families
#      and signal families is preserved on the episode.
#   F5 exact-time callbacks are buffered until event time ADVANCES or an
#      explicit timestamp-completion event arrives; a same-time price
#      callback never flushes the group early.
#   F6 conflicting signals produce zero fill, zero position and no
#      TRADE_OPENED record.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TICK = 0.25
SPEC_VERSION = 'MROF-YT-OF-01.5'
EXECUTABLE_ENTRYPOINT = True
FAMILY_ORDER = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6')
LATENCY_S = 0.150
FILL_WINDOW_S = 5.0

# Frozen reset-type table (inherited unchanged from v01.4).
RESET_TYPES = dict(A1='RETREAT_REAPPROACH', A2='RETREAT_REAPPROACH',
                   A3='BAND_EXIT_REENTER', A4='RETREAT_REAPPROACH',
                   A5='BAND_EXIT_REENTER', A6='BAND_EXIT_REENTER')

# every adjudication consumes the occurrence (F2)
CONSUMING = ('SIMULTANEOUS_DIRECTION_CONFLICT', 'RISK_SUPPRESSED',
             'DATA_SUPPRESSED', 'CAUSALITY_FAILURE', 'EXECUTION_MISSED',
             'OVERLAP_SUPPRESSED', 'TRADE_OPENED')


def fill_first_book(quotes, decision_t, direction, qty,
                    latency_s=LATENCY_S, window_s=FILL_WINDOW_S):
    """First-executable-book rule (inherited from v01.4): fill only
    against the synchronized depth of the FIRST valid snapshot after
    latency; cancel the remainder; a later quote never fills."""
    rel = decision_t + latency_s
    deadline = rel + window_s
    for t, b, bs, a, asz in quotes:
        if t <= rel:
            continue
        if t > deadline:
            break
        if bs <= 0 or asz <= 0 or b >= a:
            continue
        px, avail = (a, float(asz)) if direction > 0 else (b, float(bs))
        take = min(float(qty), avail)
        return dict(filled=take, vwap=px, snapshot_t=t,
                    cancelled=float(qty) - take, partial=take < qty,
                    missed=False)
    return dict(filled=0.0, vwap=None, snapshot_t=None,
                cancelled=float(qty), partial=False, missed=True)


class SignalGroupBufferV015:
    """F5: groups callbacks by exact completion timestamp. Flushes only
    when event time strictly advances or on an explicit completion."""

    def __init__(self, coordinator, quotes_fn):
        self.co = coordinator
        self.quotes_fn = quotes_fn
        self._t = None
        self._pending = []

    def pending_t(self):
        return self._t

    def submit(self, completion_t, signal):
        if self._t is not None and completion_t < self._t:
            raise ValueError('out-of-order submission')
        if self._t is not None and completion_t > self._t:
            self.flush()
        self._t = completion_t
        self._pending.append(signal)

    def time_advanced(self, t):
        """A clock/price event at time t. Flushes ONLY if t strictly
        exceeds the pending completion timestamp."""
        if self._t is not None and t > self._t:
            return self.flush()
        return None

    def complete_timestamp(self):
        return self.flush()

    def flush(self):
        if not self._pending:
            self._t = None
            return None
        t, group = self._t, self._pending
        self._t, self._pending = None, []
        return self.co.on_group(t, group, self.quotes_fn(t))


class CoordinatorV015:
    def __init__(self, instrument, contract, session_date, levels,
                 family_of, radius, fill_fn=None, qty=1,
                 reset_types=None):
        self.instrument = instrument
        self.contract = contract
        self.session = session_date
        self.levels = dict(levels)
        self.family_of = dict(family_of)
        self.radius = float(radius)
        self.fill_fn = fill_fn or fill_first_book
        self.qty = qty
        self.reset_types = dict(RESET_TYPES)
        if reset_types:
            self.reset_types.update(reset_types)
        self.position = None
        self.episodes = {}
        self.log = []
        self._callbacks = set()
        self._key = {}       # (anchor_tick, family, dir) -> reset state
        self._appr = {}      # anchor_tick -> physical approach state

    # ---- identity helpers -------------------------------------------
    def _anchor(self, px):
        best = None
        for lid, v in self.levels.items():
            d = abs(v - px)
            if d <= self.radius and (best is None or d < best[0]):
                best = (d, v, lid)
        return best

    def _cluster_id(self, px):
        members = sorted((self.family_of.get(lid, lid), round(v / TICK))
                         for lid, v in self.levels.items()
                         if abs(v - px) <= self.radius)
        return 'C%s' % hashlib.sha256(repr(members).encode()
                                      ).hexdigest()[:8]

    def _levels_at(self, px):
        return sorted(lid for lid, v in self.levels.items()
                      if abs(v - px) <= self.radius)

    def _appr_state(self, anchor_tick):
        return self._appr.setdefault(anchor_tick,
                                     dict(n=0, inside=False,
                                          minted='NONE'))

    def _kstate(self, key):
        return self._key.setdefault(key, dict(
            mode='ARMED', phase=None, reset_t=float('-inf'),
            awaiting_flat=False, terminal_t=float('-inf')))

    # ---- F3: physical approach minted at the price event -------------
    def on_price(self, t, px):
        for lid, v in self.levels.items():
            at = round(v / TICK)
            a = self._appr_state(at)
            inside = abs(px - v) <= self.radius
            if inside and not a['inside']:
                a['n'] += 1
                a['minted'] = 'PRICE_EVENT'
            a['inside'] = inside
        if self.position is not None:
            return                      # nothing re-arms while in a trade
        for key, st in self._key.items():
            if t <= st['terminal_t'] or st['awaiting_flat']:
                continue
            if st['mode'] != 'SPENT':
                continue
            anchor_px = key[0] * TICK
            rtype = self.reset_types.get(key[1], 'BAND_EXIT_REENTER')
            if rtype == 'RETREAT_REAPPROACH':
                away = abs(px - anchor_px) >= 2 * TICK
                near = abs(px - anchor_px) < 2 * TICK
            else:
                away = abs(px - anchor_px) > self.radius
                near = abs(px - anchor_px) <= self.radius
            if st['phase'] is None and away:
                st['phase'] = ('AWAY', t)
            elif st['phase'] and st['phase'][0] == 'AWAY' and near:
                st['mode'] = 'ARMED'
                st['reset_t'] = st['phase'][1]
                st['phase'] = None

    # ---- ledger -------------------------------------------------------
    def _episode_id(self, family, cluster, approach):
        return 'SE|%s|%s|%s|%s|%s|%s|approach%03d' % (
            SPEC_VERSION, self.instrument, self.contract, self.session,
            family, cluster, approach)

    def _ledger(self, t, family, direction, trigger_px, state, reason,
                cluster, approach, minted, level_ids, level_families,
                tagged=None, tagged_families=None, fill=None):
        eid = self._episode_id(family, cluster, approach)
        if eid in self.episodes:
            n = sum(1 for k in self.episodes if k.split('#')[0] == eid)
            eid = '%s#%d' % (eid, n + 1)
        rec = dict(id=eid, t_signal=t, family=family, direction=direction,
                   trigger_px=trigger_px, instrument=self.instrument,
                   contract=self.contract, session=self.session,
                   cluster=cluster, approach=approach,
                   approach_minted=minted, level_ids=level_ids,
                   level_families=level_families, tagged=tagged or [],
                   tagged_families=tagged_families or [], state=state,
                   reason=reason,
                   filled=(fill or {}).get('filled', 0.0),
                   cancelled=(fill or {}).get('cancelled', 0.0),
                   entry_vwap=(fill or {}).get('vwap'),
                   partial=(fill or {}).get('partial', False))
        self.episodes[eid] = rec
        self.log.append(dict(t=t, reason=reason, detail=eid))
        return rec

    def _consume(self, st, t, in_trade):
        st['mode'] = 'SPENT'
        st['phase'] = None
        if in_trade:
            st['awaiting_flat'] = True
        else:
            st['awaiting_flat'] = False
            st['terminal_t'] = t

    # ---- group adjudication -------------------------------------------
    def on_group(self, t, signals, quotes):
        sigs = sorted(signals, key=lambda s: (
            FAMILY_ORDER.index(s['family'])
            if s['family'] in FAMILY_ORDER else 99, s['callback_id']))
        live = []
        for s in sigs:
            if s['callback_id'] in self._callbacks:
                self.log.append(dict(t=t, reason='DUPLICATE_CALLBACK',
                                     detail=s['callback_id']))
                continue
            self._callbacks.add(s['callback_id'])
            anchor = self._anchor(s['trigger_px'])
            if anchor is None:
                self.log.append(dict(t=t, reason='NOT_AT_ACTIVE_LEVEL',
                                     detail=s['callback_id']))
                continue
            at = round(anchor[1] / TICK)
            ap = self._appr_state(at)
            if ap['n'] == 0:                 # no price event ever seen
                ap['n'] = 1
                ap['minted'] = 'SIGNAL_FALLBACK'
            key = (at, s['family'], s['direction'])
            st = self._kstate(key)
            cl = self._cluster_id(s['trigger_px'])
            lids = self._levels_at(s['trigger_px'])
            lfam = sorted({self.family_of.get(l, l) for l in lids})
            ctx = dict(key=key, st=st, cluster=cl, approach=ap['n'],
                       minted=ap['minted'], lids=lids, lfam=lfam)

            def drop(reason, in_trade=False):
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED', reason, cl,
                             ap['n'], ap['minted'], lids, lfam)
                if reason in CONSUMING:
                    self._consume(st, t, in_trade)

            f = s.get('formed_from_t', t)
            if f > t:
                drop('CAUSALITY_FAILURE')
                continue
            if not s.get('data_ok', True):
                drop('DATA_SUPPRESSED')
                continue
            if not s.get('risk_ok', True):
                drop('RISK_SUPPRESSED')
                continue
            # F1: open-position state is checked BEFORE consumed/re-arm
            if self.position is not None:
                drop('OVERLAP_SUPPRESSED', in_trade=True)
                continue
            if st['mode'] == 'SPENT':
                drop('REARM_PENDING')
                continue
            if f <= st['reset_t']:
                drop('DATA_SUPPRESSED')
                continue
            live.append((s, ctx))

        if not live:
            return None
        dirs = {s['direction'] for s, _ in live}
        if len(dirs) > 1:
            # F6: zero fill, zero position, no TRADE_OPENED record
            for s, c in live:
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'SIMULTANEOUS_DIRECTION_CONFLICT',
                             c['cluster'], c['approach'], c['minted'],
                             c['lids'], c['lfam'])
                self._consume(c['st'], t, False)
            return None

        s0, c0 = live[0]
        fill = self.fill_fn(quotes, t, s0['direction'], self.qty)
        # F4: union across every agreeing signal
        u_lids, u_lfam, u_fam, tagged = set(), set(), set(), []
        for s, c in live:
            u_lids.update(c['lids'])
            u_lfam.update(c['lfam'])
            u_fam.add(s['family'])
            tagged.append(s['callback_id'])
        if fill['missed']:
            for s, c in live:
                self._consume(c['st'], t, False)
            self._ledger(t, s0['family'], s0['direction'],
                         s0['trigger_px'], 'MISSED', 'EXECUTION_MISSED',
                         c0['cluster'], c0['approach'], c0['minted'],
                         sorted(u_lids), sorted(u_lfam), tagged,
                         sorted(u_fam), fill)
            return None
        rec = self._ledger(t, s0['family'], s0['direction'],
                           s0['trigger_px'], 'OPEN', 'TRADE_OPENED',
                           c0['cluster'], c0['approach'], c0['minted'],
                           sorted(u_lids), sorted(u_lfam), tagged,
                           sorted(u_fam), fill)
        for s, c in live:
            self._consume(c['st'], t, True)
        self.position = rec['id']
        return rec

    def on_exit(self, eid, t_exit, exit_px):
        e = self.episodes[eid]
        e['state'] = 'CLOSED'
        e['t_exit'] = t_exit
        e['exit_px'] = exit_px
        if self.position == eid:
            self.position = None
        for st in self._key.values():
            if st['awaiting_flat']:
                st['awaiting_flat'] = False
                st['terminal_t'] = t_exit

    def trade_opened_records(self):
        return [x for x in self.log if x['reason'] == 'TRADE_OPENED']


class ResearchEngineV015:
    """THE executable entrypoint: raw callbacks -> exact-timestamp
    grouping -> coordinator -> first-executable-book fill -> ledger."""

    def __init__(self, instrument, contract, session, levels, family_of,
                 radius, quotes_fn, **kw):
        self.co = CoordinatorV015(instrument, contract, session, levels,
                                  family_of, radius, **kw)
        self.buf = SignalGroupBufferV015(self.co, quotes_fn)

    def on_raw_callback(self, completion_t, family, direction,
                        trigger_px, callback_id, formed_from_t,
                        data_ok=True, risk_ok=True):
        self.buf.submit(completion_t, dict(
            family=family, direction=direction, trigger_px=trigger_px,
            callback_id=callback_id, formed_from_t=formed_from_t,
            data_ok=data_ok, risk_ok=risk_ok))

    def on_price(self, t, px):
        # F5: a same-time price callback must NOT flush the group.
        self.buf.time_advanced(t)
        self.co.on_price(t, px)

    def complete_timestamp(self):
        return self.buf.complete_timestamp()

    def on_exit(self, eid, t_exit, exit_px):
        self.co.on_exit(eid, t_exit, exit_px)

    def ledger(self):
        return dict(self.co.episodes)
