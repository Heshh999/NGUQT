#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.6 — EXECUTABLE RESEARCH ENGINE (sole v01.6 entrypoint)
#
# Additive successor to v01.5. It INHERITS the authoritative v01.5
# coordinator rather than copying an older one; v01.2/v01.3/v01.4
# coordinators stay superseded and nothing executable imports them.
#
# What v01.6 adds, and only this:
#   - an EXPERIMENTAL active-location branch carrying CAUSAL_SWING
#     levels alongside the unchanged parent pool;
#   - four deterministic toggles selecting which pool is active;
#   - a confluence branch that requires a parent family AND CAUSAL_SWING
#     in the same frozen proximity cluster.
#
# SWINGS_OFF_PARENT is bit-for-bit identical to v01.5 BY CONSTRUCTION:
# in that mode this module constructs an unmodified ResearchEngineV015
# and delegates to it. There is no mirrored copy of the v01.5 path here
# that could drift away from it.
#
# No branch may choose a favorable label after the trade: the complete
# set of available level IDs and families is logged at first proximity,
# signal completion, entry release, fill, early exit and terminal exit.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mrofyt_engine_v015 as V15        # noqa: E402
import mrofyt_swings_v016 as SW         # noqa: E402

SPEC_VERSION = 'MROF-YT-OF-01.6'
EXECUTABLE_ENTRYPOINT = True
TICK = V15.TICK

SWINGS_OFF_PARENT = 'SWINGS_OFF_PARENT'
SWINGS_ONLY = 'SWINGS_ONLY'
PARENT_PLUS_SWINGS = 'PARENT_PLUS_SWINGS'
PARENT_AND_SWING_OVERLAP = 'PARENT_AND_SWING_OVERLAP'
TOGGLES = (SWINGS_OFF_PARENT, SWINGS_ONLY, PARENT_PLUS_SWINGS,
           PARENT_AND_SWING_OVERLAP)

# observation points at which the full level/family set is recorded
OBSERVE_POINTS = ('FIRST_PROXIMITY', 'SIGNAL_COMPLETION', 'ENTRY_RELEASE',
                  'FILL', 'EARLY_EXIT', 'TERMINAL_EXIT')


class CoordinatorV016(V15.CoordinatorV015):
    """v01.5 adjudication, unchanged, plus the swing branch rules.

    Only two things are added: a per-toggle admissibility test applied
    BEFORE the inherited pipeline runs, and full level/family
    observation records. No inherited threshold, reset type, conflict
    rule, fill rule or consumption rule is touched."""

    def __init__(self, *a, **kw):
        self.toggle = kw.pop('toggle', PARENT_PLUS_SWINGS)
        if self.toggle not in TOGGLES:
            raise ValueError('unknown toggle %r' % (self.toggle,))
        self.parent_levels = dict(kw.pop('parent_levels', {}) or {})
        self.swing_levels = dict(kw.pop('swing_levels', {}) or {})
        V15.CoordinatorV015.__init__(self, *a, **kw)
        self.observations = []
        self.branch_drops = []

    # ---- identity ---------------------------------------------------
    def _episode_id(self, family, cluster, approach):
        return 'SE|%s|%s|%s|%s|%s|%s|approach%03d' % (
            SPEC_VERSION, self.instrument, self.contract, self.session,
            family, cluster, approach)

    # ---- branch bookkeeping -----------------------------------------
    def _split(self, px):
        """Level IDs inside the proximity radius, split by origin."""
        lids = self._levels_at(px)
        par = [x for x in lids if x in self.parent_levels]
        sw = [x for x in lids if x in self.swing_levels]
        return par, sw

    def observe(self, point, t, px, extra=None):
        par, sw = self._split(px)
        rec = dict(point=point, t=t, px=px, toggle=self.toggle,
                   parent_level_ids=par, swing_level_ids=sw,
                   level_ids=sorted(par + sw),
                   level_families=sorted(
                       {self.family_of.get(x, x) for x in par + sw}),
                   swing_family_votes=1 if sw else 0)
        if extra:
            rec.update(extra)
        self.observations.append(rec)
        return rec

    def _admissible(self, px):
        """(ok, reason). The toggle decides which locations may trade.

        A swing is a location hypothesis, so every branch still requires
        a complete frozen A1-A6 signal; nothing here creates a signal."""
        par, sw = self._split(px)
        if self.toggle == SWINGS_ONLY:
            if not sw:
                return False, 'NO_ACTIVE_SWING'
            return True, None
        if self.toggle == PARENT_PLUS_SWINGS:
            if not par and not sw:
                return False, 'NOT_AT_ACTIVE_LEVEL'
            return True, None
        if self.toggle == PARENT_AND_SWING_OVERLAP:
            if not (par and sw):
                return False, 'NO_PARENT_SWING_OVERLAP'
            return True, None
        return bool(par), (None if par else 'NOT_AT_ACTIVE_LEVEL')

    def on_price(self, t, px):
        for lid, v in self.levels.items():
            at = round(v / TICK)
            a = self._appr_state(at)
            if abs(px - v) <= self.radius and not a['inside']:
                self.observe('FIRST_PROXIMITY', t, px, dict(level_id=lid))
        V15.CoordinatorV015.on_price(self, t, px)

    def on_group(self, t, signals, quotes):
        keep = []
        for s in signals:
            self.observe('SIGNAL_COMPLETION', t, s['trigger_px'],
                         dict(family=s['family'],
                              callback_id=s['callback_id']))
            ok, why = self._admissible(s['trigger_px'])
            if not ok:
                # A branch rejection is recorded, never silent, and it
                # happens BEFORE any fill so it cannot be chosen later.
                self.branch_drops.append(
                    dict(t=t, callback_id=s['callback_id'], reason=why,
                         toggle=self.toggle, trigger_px=s['trigger_px']))
                self.log.append(dict(t=t, reason='BRANCH_' + why,
                                     detail=s['callback_id']))
                continue
            keep.append(s)
        if not keep:
            return None
        rec = V15.CoordinatorV015.on_group(self, t, keep, quotes)
        if rec is not None:
            self.observe('ENTRY_RELEASE', t, rec['trigger_px'],
                         dict(episode=rec['id']))
            self.observe('FILL', t, rec['trigger_px'],
                         dict(episode=rec['id'], filled=rec['filled'],
                              entry_vwap=rec['entry_vwap']))
        return rec

    def on_exit(self, eid, t_exit, exit_px, early=False):
        self.observe('EARLY_EXIT' if early else 'TERMINAL_EXIT', t_exit,
                     exit_px, dict(episode=eid))
        V15.CoordinatorV015.on_exit(self, eid, t_exit, exit_px)


class ResearchEngineV016(object):
    """THE v01.6 executable entrypoint.

    In SWINGS_OFF_PARENT mode this holds a genuine, unmodified
    ResearchEngineV015 and forwards to it, so that branch runs the same
    code objects as v01.5 and is identical by construction rather than
    by resemblance."""

    def __init__(self, instrument, contract, session, parent_levels,
                 family_of, radius, quotes_fn, toggle=PARENT_PLUS_SWINGS,
                 swing_levels=None, swing_family_of=None, **kw):
        if toggle not in TOGGLES:
            raise ValueError('unknown toggle %r' % (toggle,))
        self.toggle = toggle
        self.parent_levels = dict(parent_levels)
        self.swing_levels = dict(swing_levels or {})
        self.swing_family_of = dict(
            swing_family_of or {k: SW.SWING_FAMILY
                                for k in self.swing_levels})
        self.parity = toggle == SWINGS_OFF_PARENT
        if self.parity:
            # the v01.5 path itself, with the v01.5 pool and nothing else
            self._v15 = V15.ResearchEngineV015(
                instrument, contract, session, self.parent_levels,
                family_of, radius, quotes_fn, **kw)
            self.co = self._v15.co
            self.buf = self._v15.buf
            return
        self._v15 = None
        pool = dict(self.parent_levels)
        fam = dict(family_of)
        if toggle == SWINGS_ONLY:
            pool = dict(self.swing_levels)
            fam = dict(self.swing_family_of)
        else:
            pool.update(self.swing_levels)
            fam.update(self.swing_family_of)
        self.co = CoordinatorV016(instrument, contract, session, pool,
                                  fam, radius, toggle=toggle,
                                  parent_levels=self.parent_levels,
                                  swing_levels=self.swing_levels, **kw)
        self.buf = V15.SignalGroupBufferV015(self.co, quotes_fn)

    # ---- the v01.5 interface, unchanged ------------------------------
    def on_raw_callback(self, completion_t, family, direction, trigger_px,
                        callback_id, formed_from_t, data_ok=True,
                        risk_ok=True):
        if self.parity:
            return self._v15.on_raw_callback(
                completion_t, family, direction, trigger_px, callback_id,
                formed_from_t, data_ok, risk_ok)
        self.buf.submit(completion_t, dict(
            family=family, direction=direction, trigger_px=trigger_px,
            callback_id=callback_id, formed_from_t=formed_from_t,
            data_ok=data_ok, risk_ok=risk_ok))

    def on_price(self, t, px):
        if self.parity:
            return self._v15.on_price(t, px)
        self.buf.time_advanced(t)
        self.co.on_price(t, px)

    def complete_timestamp(self):
        if self.parity:
            return self._v15.complete_timestamp()
        return self.buf.complete_timestamp()

    def on_exit(self, eid, t_exit, exit_px, early=False):
        if self.parity:
            return self._v15.on_exit(eid, t_exit, exit_px)
        self.co.on_exit(eid, t_exit, exit_px, early=early)

    def ledger(self):
        if self.parity:
            return self._v15.ledger()
        return dict(self.co.episodes)

    def observations(self):
        return [] if self.parity else list(self.co.observations)

    def branch_drops(self):
        return [] if self.parity else list(self.co.branch_drops)
