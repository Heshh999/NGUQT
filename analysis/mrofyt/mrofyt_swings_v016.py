#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.6 — CAUSAL SWING CONSTRUCTION (additive)
#
# Bar aggregation, five-bar confirmed fractals, proximity clusters, the
# frozen lifecycle and the feature record. Nothing here asserts that a
# swing has edge: swing levels are hypotheses about WHERE order flow may
# matter. They are never proof of direction, and an entry still requires
# a complete frozen A1-A6 mechanism.
#
# Every rule below is frozen BEFORE outcomes are inspected. No pivot
# width, left/right bar count, tie treatment, timeframe list, acceptance
# count, proximity radius, lifecycle or age cutoff may be changed after
# outcome data is opened; any alternative is a separately numbered wave.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

SPEC_VERSION = 'MROF-YT-OF-01.6'
TICK = 0.25

# Frozen timeframe roles (section 3.3). 1m is diagnostic ONLY: it can
# never create entry eligibility, change a setup grade, or move a stop
# or target in this wave.
TIMEFRAMES = ('1m', '5m', '15m', '60m')
TF_MINUTES = {'1m': 1, '5m': 5, '15m': 15, '60m': 60}
DIAGNOSTIC_TF = ('1m',)
ACTIVE_TF = ('5m', '15m', '60m')
# cluster-anchor tie order (section 3.4)
TF_ANCHOR_ORDER = {'60m': 0, '15m': 1, '5m': 2, '1m': 3}

SWING_FAMILY = 'CAUSAL_SWING'          # ONE family vote for all timeframes
SIDES = ('SWING_HIGH', 'SWING_LOW')

# frozen lifecycle states (section 4)
CONFIRMED_UNTOUCHED = 'CONFIRMED_UNTOUCHED'
ACTIVE_TESTED = 'ACTIVE_TESTED'
BROKEN_PENDING = 'BROKEN_PENDING_ACCEPTANCE'
RECLAIMED_BEFORE = 'RECLAIMED_BEFORE_ACCEPTANCE'
ACCEPTED_BROKEN = 'ACCEPTED_BROKEN'
ROLLED_OFF = 'ROLLED_OFF'
# states that retire a level from NEW entry eligibility in this wave
RETIRED_STATES = (ACCEPTED_BROKEN, ROLLED_OFF)

ACCEPTANCE_CLOSES = 2                  # frozen: two own-timeframe closes


# ---------------------------------------------------------------------
# bars
# ---------------------------------------------------------------------
class Bar(object):
    """A completed bar. `complete` is the source-interval certification;
    an uncertain bar can neither form nor confirm a swing."""

    __slots__ = ('tf', 't_open', 't_close', 'o', 'h', 'l', 'c', 'v',
                 'instrument', 'contract', 'session', 'run', 'complete')

    def __init__(self, tf, t_open, t_close, o, h, l, c, v=0.0,
                 instrument=None, contract=None, session=None, run=None,
                 complete=True):
        self.tf = tf
        self.t_open = float(t_open)
        self.t_close = float(t_close)
        self.o, self.h, self.l, self.c = (float(o), float(h),
                                          float(l), float(c))
        self.v = float(v)
        self.instrument = instrument
        self.contract = contract
        self.session = session
        self.run = run
        self.complete = bool(complete)

    def key(self):
        return (self.instrument, self.contract, self.session, self.run)

    def as_dict(self):
        return dict(tf=self.tf, t_open=self.t_open, t_close=self.t_close,
                    o=self.o, h=self.h, l=self.l, c=self.c, v=self.v,
                    contract=self.contract, session=self.session,
                    run=self.run, complete=self.complete)

    def __repr__(self):
        return 'Bar(%s %s o=%s h=%s l=%s c=%s)' % (
            self.tf, self.t_close, self.o, self.h, self.l, self.c)


def bucket_start(t_open, minutes, tz_offset_fn):
    """Exchange-calendar-aligned bucket start for a 1-minute bar.

    Alignment is on Eastern local minute-of-day, so 5m/15m/60m buckets
    sit on :00/:05/:15/:60 boundaries of the exchange clock rather than
    on an arbitrary offset from the first bar seen."""
    off = tz_offset_fn(t_open)
    loc = t_open + off
    day = loc // 86400
    sod = loc - day * 86400
    b = (int(sod) // (minutes * 60)) * (minutes * 60)
    return day * 86400 + b - off


class BarAggregator(object):
    """1m -> 5m/15m/60m. A higher-timeframe bar is emitted ONLY when
    every constituent minute is present, complete, and shares one
    instrument, contract, session and run.

    A missing minute, an incomplete minute, a maintenance break, a
    holiday-misaligned interval, a mixed run or a contract roll all
    prevent the aggregate from forming at all. They never produce a bar
    built from whatever happened to arrive."""

    def __init__(self, tz_offset_fn, timeframes=ACTIVE_TF):
        self.tz = tz_offset_fn
        self.timeframes = tuple(timeframes)
        self.open = {}        # tf -> (bucket_start, [bars], key)
        self.suppressed = collections.Counter()

    def add_1m(self, bar):
        """Returns the higher-timeframe bars completed BY this minute."""
        out = []
        for tf in self.timeframes:
            m = TF_MINUTES[tf]
            bs = bucket_start(bar.t_open, m, self.tz)
            cur = self.open.get(tf)
            if cur is not None and cur[0] != bs:
                done = self._close(tf, cur)
                if done is not None:
                    out.append(done)
                cur = None
            if cur is None:
                cur = (bs, [], bar.key())
                self.open[tf] = cur
            if bar.key() != cur[2]:
                # mixed contract / session / run inside one bucket: the
                # bucket is void, not partially usable
                self.suppressed['MIXED_SOURCE_' + tf] += 1
                self.open[tf] = (bs, [None], bar.key())
                continue
            cur[1].append(bar)
        return out

    def flush(self):
        """Close every bucket whose scheduled end has been reached by a
        later minute. Buckets still open are NOT emitted: a bar is usable
        only after its scheduled closing timestamp."""
        out = []
        for tf in list(self.open):
            done = self._close(tf, self.open.pop(tf))
            if done is not None:
                out.append(done)
        return out

    def _close(self, tf, cur):
        bs, bars, key = cur
        m = TF_MINUTES[tf]
        if any(b is None for b in bars):
            self.suppressed['VOID_' + tf] += 1
            return None
        if len(bars) != m:
            self.suppressed['INCOMPLETE_INTERVAL_' + tf] += 1
            return None
        if not all(b.complete for b in bars):
            self.suppressed['UNCERTAIN_SOURCE_' + tf] += 1
            return None
        if len({b.key() for b in bars}) != 1:
            self.suppressed['MIXED_SOURCE_' + tf] += 1
            return None
        # contiguity: the minutes must be consecutive with no gap
        for a, b in zip(bars, bars[1:]):
            if abs(b.t_open - a.t_open - 60.0) > 1e-6:
                self.suppressed['GAP_' + tf] += 1
                return None
        if abs(bars[0].t_open - bs) > 1e-6:
            self.suppressed['MISALIGNED_' + tf] += 1
            return None
        return Bar(tf, bars[0].t_open, bars[-1].t_close, bars[0].o,
                   max(b.h for b in bars), min(b.l for b in bars),
                   bars[-1].c, sum(b.v for b in bars),
                   bars[0].instrument, bars[0].contract, bars[0].session,
                   bars[0].run, True)


# ---------------------------------------------------------------------
# confirmed fractals
# ---------------------------------------------------------------------
def is_swing_high(h):
    """Five completed bars j-2..j+2 (highs). Asymmetric tie rule: >= on
    the left, > on the right, which assigns an equal-price plateau to
    its LAST occurrence before price departs. One deterministic swing,
    never a duplicate per plateau bar."""
    return h[2] >= h[1] and h[2] >= h[0] and h[2] > h[3] and h[2] > h[4]


def is_swing_low(l):
    return l[2] <= l[1] and l[2] <= l[0] and l[2] < l[3] and l[2] < l[4]


def swing_id(tf, side, contract, center_t, price):
    """SWING_5M_HIGH|contract|center_t|price_tick"""
    return '%s|%s|%d|%d' % (level_id_prefix(tf, side), contract,
                            int(round(center_t)), int(round(price / TICK)))


def level_id_prefix(tf, side):
    return 'SWING_%s_%s' % (tf.upper(), 'HIGH' if side == 'SWING_HIGH'
                            else 'LOW')


class Swing(object):
    __slots__ = ('swing_id', 'instrument', 'contract', 'session', 'tf',
                 'side', 'center_t', 'price', 'available_t', 'bars',
                 'state', 'transitions', 'touches', 'approach_ids',
                 'closes_beyond', 'cluster_id', 'confirm_session')

    def __init__(self, sid, instrument, contract, session, tf, side,
                 center_t, price, available_t, bars):
        self.swing_id = sid
        self.instrument = instrument
        self.contract = contract
        self.session = session
        self.confirm_session = session
        self.tf = tf
        self.side = side
        self.center_t = center_t
        self.price = price
        self.available_t = available_t
        self.bars = bars                     # the five source bars
        self.state = CONFIRMED_UNTOUCHED
        self.transitions = [(CONFIRMED_UNTOUCHED, available_t)]
        self.touches = 0
        self.approach_ids = []
        self.closes_beyond = 0
        self.cluster_id = None

    @property
    def level_id(self):
        return level_id_prefix(self.tf, self.side)

    @property
    def family(self):
        return SWING_FAMILY

    @property
    def eligible_tf(self):
        """1m is diagnostic only and can never be an entry location."""
        return self.tf in ACTIVE_TF

    def available_at(self, t):
        """Causal availability: nothing before the close of j+2 may use
        this swing for any purpose."""
        return t >= self.available_t

    def eligible(self, t):
        return (self.eligible_tf and self.available_at(t) and
                self.state not in RETIRED_STATES)

    def age(self, t, tf_bars_closed=None, sessions_closed=None):
        return dict(elapsed_s=None if t is None else t - self.available_t,
                    own_tf_bars=tf_bars_closed,
                    completed_sessions=sessions_closed)

    def _to(self, state, t):
        if self.state != state:
            self.state = state
            self.transitions.append((state, t))

    def record(self, t=None, atr20=None, mid=None, overlap_level_ids=(),
               overlap_families=()):
        d = dict(swing_id=self.swing_id, instrument=self.instrument,
                 contract=self.contract, session=self.session,
                 timeframe=self.tf, side=self.side,
                 center_t=self.center_t, price=self.price,
                 available_t=self.available_t,
                 source_bars=[b.as_dict() for b in self.bars],
                 state=self.state, transitions=list(self.transitions),
                 touches=self.touches,
                 approach_ids=list(self.approach_ids),
                 level_id=self.level_id, family=self.family,
                 cluster_id=self.cluster_id,
                 closes_beyond=self.closes_beyond,
                 overlap_level_ids=sorted(overlap_level_ids),
                 overlap_families=sorted(overlap_families))
        d['age'] = self.age(t)
        if mid is not None:
            d['distance_ticks'] = (mid - self.price) / TICK
            d['distance_atr'] = (None if not atr20 else
                                 abs(mid - self.price) / atr20)
        return d


def detect_swings(bars, instrument=None):
    """Confirmed fractals over a list of completed same-timeframe bars.

    A swing at center j becomes available at the CLOSE of j+2, so the
    scan can never look at a bar that has not closed. Bars must already
    be certified complete and homogeneous; a caller that hands in a
    partially formed current bar gets no swing from it, because the
    window always needs two closed bars to its right."""
    out = []
    for j in range(2, len(bars) - 2):
        w = bars[j - 2:j + 3]
        if not all(b.complete for b in w):
            continue
        if len({b.key() for b in w}) != 1:
            continue                       # mixed run/contract/session
        c = w[2]
        for side, ok, px in (
                ('SWING_HIGH', is_swing_high([b.h for b in w]), c.h),
                ('SWING_LOW', is_swing_low([b.l for b in w]), c.l)):
            if not ok:
                continue
            sid = swing_id(c.tf, side, c.contract or '?', c.t_close, px)
            out.append(Swing(sid, instrument or c.instrument, c.contract,
                             c.session, c.tf, side, c.t_close, px,
                             w[4].t_close, list(w)))
    return out


# ---------------------------------------------------------------------
# proximity clusters
# ---------------------------------------------------------------------
def proximity_radius(atr20, tick=TICK):
    """The UNCHANGED MROF proximity window. Not re-tuned here."""
    return max(4 * tick, 0.20 * atr20) if atr20 else 4 * tick


def cluster_swings(swings, atr20, radius=None):
    """Merge SAME-SIDE swings whose prices lie within the proximity
    radius into one physical cluster.

    The anchor is the earliest causally available member; ties break by
    timeframe order 60m, 15m, 5m and then lexically by swing_id. The
    anchor is never moved to a later price, because moving it after the
    fact is how a cluster gets chosen to explain an outcome.

    Opposite-side swings keep their side labels and are never silently
    cancelled, even at the same price."""
    r = proximity_radius(atr20) if radius is None else radius
    out = {}
    for side in SIDES:
        mem = sorted((s for s in swings if s.side == side),
                     key=lambda s: (s.available_t,
                                    TF_ANCHOR_ORDER.get(s.tf, 9),
                                    s.swing_id))
        groups = []
        for s in mem:
            for g in groups:
                if abs(s.price - g[0].price) <= r:
                    g.append(s)
                    break
            else:
                groups.append([s])
        for g in groups:
            anchor = g[0]
            cid = 'SC|%s|%s|%d' % (side, anchor.contract or '?',
                                   int(round(anchor.price / TICK)))
            for s in g:
                s.cluster_id = cid
            out[cid] = dict(cluster_id=cid, side=side,
                            anchor_price=anchor.price,
                            anchor_swing_id=anchor.swing_id,
                            anchor_available_t=anchor.available_t,
                            members=[s.swing_id for s in g],
                            timeframes=sorted({s.tf for s in g}),
                            family=SWING_FAMILY,
                            family_votes=1)   # coincident TFs vote ONCE
    return out


# ---------------------------------------------------------------------
# lifecycle
# ---------------------------------------------------------------------
class SwingLifecycle(object):
    """The frozen causal state machine of section 4.

    Acceptance needs two consecutive completed closes of the swing's OWN
    timeframe beyond the level. A reclaim before the second such close
    is RECLAIMED_BEFORE_ACCEPTANCE, which may condition A4 only when
    every inherited A4 order-flow requirement is also satisfied - this
    class never asserts A4 on its own."""

    def __init__(self, atr20=None):
        self.swings = {}
        self.atr20 = atr20
        self.events = []

    def add(self, swing):
        self.swings[swing.swing_id] = swing
        return swing

    def _beyond(self, s, px):
        return px > s.price if s.side == 'SWING_HIGH' else px < s.price

    def on_price(self, t, px, approach_id=None):
        r = proximity_radius(self.atr20)
        for s in self.swings.values():
            if not s.available_at(t) or s.state in RETIRED_STATES:
                continue
            if abs(px - s.price) <= r:
                if s.state == CONFIRMED_UNTOUCHED:
                    s._to(ACTIVE_TESTED, t)
                    self.events.append((t, s.swing_id, ACTIVE_TESTED))
                if approach_id is not None and \
                        approach_id not in s.approach_ids:
                    s.approach_ids.append(approach_id)
                    s.touches += 1
            # one tick beyond in the break direction
            if self._beyond(s, px) and abs(px - s.price) >= TICK:
                if s.state in (CONFIRMED_UNTOUCHED, ACTIVE_TESTED,
                               RECLAIMED_BEFORE):
                    s._to(BROKEN_PENDING, t)
                    s.closes_beyond = 0
                    self.events.append((t, s.swing_id, BROKEN_PENDING))
            elif s.state == BROKEN_PENDING and not self._beyond(s, px):
                # price returned through the swing before acceptance
                s._to(RECLAIMED_BEFORE, t)
                s.closes_beyond = 0
                self.events.append((t, s.swing_id, RECLAIMED_BEFORE))

    def on_tf_close(self, bar):
        """A completed bar of some timeframe. Only bars of the swing's
        OWN timeframe can advance or reset its acceptance count."""
        for s in self.swings.values():
            if s.tf != bar.tf or s.state in RETIRED_STATES:
                continue
            if not s.available_at(bar.t_close):
                continue
            beyond = (bar.c >= s.price + TICK if s.side == 'SWING_HIGH'
                      else bar.c <= s.price - TICK)
            if beyond:
                s.closes_beyond += 1
                if s.closes_beyond >= ACCEPTANCE_CLOSES:
                    s._to(ACCEPTED_BROKEN, bar.t_close)
                    self.events.append((bar.t_close, s.swing_id,
                                        ACCEPTED_BROKEN))
                elif s.state != BROKEN_PENDING:
                    s._to(BROKEN_PENDING, bar.t_close)
            else:
                if s.state == BROKEN_PENDING and s.closes_beyond >= 1:
                    s._to(RECLAIMED_BEFORE, bar.t_close)
                    self.events.append((bar.t_close, s.swing_id,
                                        RECLAIMED_BEFORE))
                s.closes_beyond = 0

    def on_contract_roll(self, t, new_contract):
        """The exact contract changed: every swing of the prior contract
        retires. It is kept in the ledger for audit and target-path
        reconstruction, never deleted."""
        n = 0
        for s in self.swings.values():
            if s.contract != new_contract and s.state != ROLLED_OFF:
                s._to(ROLLED_OFF, t)
                self.events.append((t, s.swing_id, ROLLED_OFF))
                n += 1
        return n

    def on_data_failure(self, t, reason='CERTIFICATION_FAILED'):
        n = 0
        for s in self.swings.values():
            if s.state != ROLLED_OFF:
                s._to(ROLLED_OFF, t)
                self.events.append((t, s.swing_id, reason))
                n += 1
        return n

    def eligible(self, t):
        """Active experimental entry locations: 5m/15m/60m only, after
        availability, not retired. ACCEPTED_BROKEN never flips polarity
        into support/resistance - that would be a separate hypothesis."""
        return [s for s in self.swings.values() if s.eligible(t)]

    def levels(self, t):
        """{level_id: price} for the eligible pool, keyed per swing so
        every timeframe-specific ID stays available for diagnostics."""
        return {s.swing_id: s.price for s in self.eligible(t)}

    def family_of(self, t):
        return {s.swing_id: SWING_FAMILY for s in self.eligible(t)}


# ---------------------------------------------------------------------
# available-R geometry (thresholds unchanged)
# ---------------------------------------------------------------------
REJECT_BELOW_R = 0.70
A_PLUS_R = 2.0


def available_r(entry_px, direction, stop_px, opposing_levels):
    """Available_R = distance to the next opposing eligible structural
    level / distance to the frozen structural stop.

    A nearer opposing swing can REDUCE available space. A same-direction
    supporting swing is location context only: it can never expand the
    space by ignoring a closer opposing non-swing level, so this
    function takes opposing levels alone."""
    risk = abs(entry_px - stop_px)
    if risk <= 0:
        return None
    ahead = [p for p in opposing_levels
             if (p > entry_px if direction > 0 else p < entry_px)]
    if not ahead:
        return None
    nearest = min(ahead) if direction > 0 else max(ahead)
    return abs(nearest - entry_px) / risk


def grade(r):
    if r is None:
        return 'UNKNOWN'
    if r < REJECT_BELOW_R:
        return 'REJECTED'
    return 'A_PLUS' if r >= A_PLUS_R else 'ELIGIBLE'
