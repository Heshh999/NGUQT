#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.4 — ENGINE BOUNDARY: SIGNAL GROUP BUFFER, COORDINATOR,
# FIRST-EXECUTABLE-BOOK FILLS, EPISODE LEDGER
# Additive successor. Predecessors f99c521/0bf0ec5/3aa0f61/4f821f1
# immutable. Supersedes (never edits) the v01.2/v01.3 coordinators:
# THIS module is the research engine's execution path.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import hashlib
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

TICK = 0.25
SPEC_VERSION = 'MROF-YT-OF-01.4'
FAMILY_ORDER = ('A1', 'A2', 'A3', 'A4', 'A5', 'A6')
FILL_WINDOW_S = 5.0            # frozen marketable window (v01.2 lineage)
LATENCY_S = 0.150

# Frozen reset-type table (requirement 8): behavior is dispatched on
# the episode's reset TYPE, never on a hardcoded family list. Wall/test
# families reset by two-tick retreat + re-approach; the rest by
# proximity-band exit + re-entry (final prompt sec. 719). Autonomous
# families register their frozen type here before outcomes.
RESET_TYPES = dict(A1='RETREAT_REAPPROACH', A2='RETREAT_REAPPROACH',
                   A3='BAND_EXIT_REENTER', A4='RETREAT_REAPPROACH',
                   A5='BAND_EXIT_REENTER', A6='BAND_EXIT_REENTER')


# ---------------------------------------------------------------------
# requirement 5: first-executable-book fill — one snapshot, no
# indefinite accumulation, remainder cancelled/unfilled
# ---------------------------------------------------------------------
def fill_first_book(quotes, decision_t, direction, qty,
                    latency_s=LATENCY_S, window_s=FILL_WINDOW_S):
    """At the FIRST valid book snapshot strictly after decision+latency
    (and inside the frozen marketable window), fill only against the
    genuinely available synchronized depth of THAT snapshot. The
    remainder is cancelled. A later quote can never fill this signal."""
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
                    cancelled=float(qty) - take,
                    partial=take < qty, missed=False)
    return dict(filled=0.0, vwap=None, snapshot_t=None,
                cancelled=float(qty), partial=False, missed=True)


# ---------------------------------------------------------------------
# requirement 1: exact-completion-timestamp grouping at the boundary
# ---------------------------------------------------------------------
class SignalGroupBuffer:
    """Individual raw callbacks are buffered and grouped by their exact
    causal completion timestamp BEFORE any fill attempt. A group is
    released only when a strictly later submission (or an explicit
    flush) proves the timestamp is complete."""

    def __init__(self, coordinator, quotes_fn):
        self.co = coordinator
        self.quotes_fn = quotes_fn
        self._pending = []            # (completion_t, signal)

    def submit(self, completion_t, signal):
        if self._pending and completion_t < self._pending[-1][0]:
            raise ValueError('out-of-order submission')
        if self._pending and completion_t > self._pending[0][0]:
            self.flush()
        self._pending.append((completion_t, signal))

    def flush(self):
        if not self._pending:
            return None
        t = self._pending[0][0]
        group = [s for _, s in self._pending]
        self._pending = []
        return self.co.on_group(t, group, self.quotes_fn(t))


# ---------------------------------------------------------------------
# the v01.4 coordinator
# ---------------------------------------------------------------------
class CoordinatorV014:
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
        self.episodes = {}            # ledger: EVERY outcome gets a row
        self.log = []
        self._callbacks = set()
        self._key = {}                # reset-key state

    # -- helpers -------------------------------------------------------
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

    def _kstate(self, key):
        return self._key.setdefault(key, dict(
            mode='ARMED', phase=None, reset_t=float('-inf'),
            approach_n=0, approach_open=False, awaiting_flat=False,
            terminal_t=float('-inf')))

    def _reset_key(self, family, direction, anchor_px):
        return (round(anchor_px / TICK), family, direction)

    # -- requirement 2 + 6: price path drives approach + reset ---------
    def on_price(self, t, px):
        # requirement 2: NOTHING re-arm-related advances while a
        # position is open, and never before the terminal timestamp.
        if self.position is not None:
            return
        for key, st in self._key.items():
            if t <= st['terminal_t']:
                continue
            anchor_px = key[0] * TICK
            rtype = self.reset_types.get(key[1], 'BAND_EXIT_REENTER')
            if rtype == 'RETREAT_REAPPROACH':
                out_thr, in_thr = 2 * TICK, 2 * TICK
                away = abs(px - anchor_px) >= out_thr
                near = abs(px - anchor_px) < in_thr
            else:
                away = abs(px - anchor_px) > self.radius
                near = abs(px - anchor_px) <= self.radius
            if st['mode'] == 'SPENT' and not st['awaiting_flat']:
                if st['phase'] is None and away:
                    st['phase'] = ('AWAY', t)
                elif st['phase'] and st['phase'][0] == 'AWAY' and near:
                    # reset completes; the NEW physical approach begins
                    # HERE (requirement 6) - before any fill attempt
                    st['mode'] = 'ARMED'
                    st['reset_t'] = st['phase'][1]
                    st['phase'] = None
                    st['approach_n'] += 1
                    st['approach_open'] = True

    # -- ledger --------------------------------------------------------
    def _episode_id(self, family, cluster, approach):
        return 'SE|%s|%s|%s|%s|%s|%s|approach%03d' % (
            SPEC_VERSION, self.instrument, self.contract, self.session,
            family, cluster, approach)

    def _ledger(self, t, family, direction, trigger_px, state, reason,
                cluster, approach, level_ids, tagged=None,
                tagged_families=None, fill=None):
        eid = self._episode_id(family, cluster, approach)
        rec = dict(id=eid, t_signal=t, family=family,
                   direction=direction, trigger_px=trigger_px,
                   instrument=self.instrument, contract=self.contract,
                   session=self.session, cluster=cluster,
                   approach=approach, level_ids=level_ids,
                   level_families=sorted({self.family_of.get(l, l)
                                          for l in level_ids}),
                   tagged=tagged or [],
                   tagged_families=tagged_families or [],
                   state=state, reason=reason,
                   filled=(fill or {}).get('filled', 0.0),
                   cancelled=(fill or {}).get('cancelled', 0.0),
                   entry_vwap=(fill or {}).get('vwap'),
                   partial=(fill or {}).get('partial', False))
        # suppressions may repeat within one approach; keep first id,
        # suffix repeats deterministically by count
        if eid in self.episodes:
            n = sum(1 for k in self.episodes if k.startswith(eid))
            eid = '%s#%d' % (eid, n + 1)
            rec['id'] = eid
        self.episodes[eid] = rec
        self.log.append(dict(t=t, reason=reason, detail=eid))
        return rec

    # -- group resolution ---------------------------------------------
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
            key = self._reset_key(s['family'], s['direction'], anchor[1])
            st = self._kstate(key)
            if st['approach_n'] == 0:
                st['approach_n'] = 1        # first observed approach
                st['approach_open'] = True
            cluster = self._cluster_id(s['trigger_px'])
            lids = self._levels_at(s['trigger_px'])
            ctx = (key, st, anchor, cluster, lids)
            # requirement 4: reset_t < formed_from_t <= t
            f = s.get('formed_from_t', t)
            if f > t:
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'CAUSALITY_FAILURE', cluster,
                             st['approach_n'], lids)
                continue
            if not s.get('data_ok', True):
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'DATA_SUPPRESSED', cluster,
                             st['approach_n'], lids)
                continue
            if not s.get('risk_ok', True):
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'RISK_SUPPRESSED', cluster,
                             st['approach_n'], lids)
                continue
            if st['mode'] == 'SPENT':
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'REARM_PENDING', cluster,
                             st['approach_n'], lids)
                continue
            if f <= st['reset_t']:
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'DATA_SUPPRESSED', cluster,
                             st['approach_n'], lids)
                continue
            live.append((s, ctx))
        if not live:
            return None
        if self.position is not None:
            # requirement 3: OVERLAP_SUPPRESSED, permanently consumed
            # for this physical episode; re-arms only with the open
            # position's exit as terminal anchor
            for s, (key, st, anchor, cluster, lids) in live:
                st['mode'] = 'SPENT'
                st['awaiting_flat'] = True
                st['approach_open'] = False
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'OVERLAP_SUPPRESSED', cluster,
                             st['approach_n'], lids)
            return None
        dirs = {s['direction'] for s, _ in live}
        if len(dirs) > 1:
            for s, (key, st, anchor, cluster, lids) in live:
                self._ledger(t, s['family'], s['direction'],
                             s['trigger_px'], 'SUPPRESSED',
                             'SIMULTANEOUS_DIRECTION_CONFLICT',
                             cluster, st['approach_n'], lids)
            return None
        s0, (key0, st0, anchor0, cluster0, lids0) = live[0]
        fill = self.fill_fn(quotes, t, s0['direction'], self.qty)
        tagged = [s['callback_id'] for s, _ in live]
        tfams = sorted({s['family'] for s, _ in live})
        # consume every participating key
        for s, (key, st, _, _, _) in live:
            st['mode'] = 'SPENT'
            st['approach_open'] = False
            st['awaiting_flat'] = True
        if fill['missed']:
            rec = self._ledger(t, s0['family'], s0['direction'],
                               s0['trigger_px'], 'MISSED',
                               'EXECUTION_MISSED', cluster0,
                               st0['approach_n'], lids0, tagged, tfams,
                               fill)
            # a miss is terminal immediately; keys re-arm from now
            for s, (key, st, _, _, _) in live:
                st['awaiting_flat'] = False
                st['terminal_t'] = t
            return None
        rec = self._ledger(t, s0['family'], s0['direction'],
                           s0['trigger_px'], 'OPEN', 'TRADE_OPENED',
                           cluster0, st0['approach_n'], lids0, tagged,
                           tfams, fill)
        self.position = rec['id']
        return rec

    def on_exit(self, eid, t_exit, exit_px):
        e = self.episodes[eid]
        e['state'] = 'CLOSED'
        e['t_exit'] = t_exit
        e['exit_px'] = exit_px
        if self.position == eid:
            self.position = None
        # requirement 2: terminal + flat is when re-arm tracking begins
        for st in self._key.values():
            if st['awaiting_flat']:
                st['awaiting_flat'] = False
                st['terminal_t'] = t_exit

    def trade_opened_records(self):
        return [x for x in self.log if x['reason'] == 'TRADE_OPENED']


# ---------------------------------------------------------------------
# requirement 9: the wired research engine (the ONLY executable path)
# ---------------------------------------------------------------------
class ResearchEngineV014:
    """Raw callbacks -> SignalGroupBuffer -> CoordinatorV014 ->
    first-executable-book fill -> episode ledger."""

    def __init__(self, instrument, contract, session, levels, family_of,
                 radius, quotes_fn, **kw):
        self.co = CoordinatorV014(instrument, contract, session, levels,
                                  family_of, radius, **kw)
        self.buf = SignalGroupBuffer(self.co, quotes_fn)

    def on_raw_callback(self, completion_t, family, direction,
                        trigger_px, callback_id, formed_from_t,
                        data_ok=True, risk_ok=True):
        self.buf.submit(completion_t, dict(
            family=family, direction=direction, trigger_px=trigger_px,
            callback_id=callback_id, formed_from_t=formed_from_t,
            data_ok=data_ok, risk_ok=risk_ok))

    def on_price(self, t, px):
        self.buf.flush()
        self.co.on_price(t, px)

    def flush(self):
        return self.buf.flush()

    def ledger(self):
        return dict(self.co.episodes)
