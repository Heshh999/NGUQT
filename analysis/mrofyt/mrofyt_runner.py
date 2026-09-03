#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01 — OUTCOME-BLIND STREAMING INGEST RUNNER (Phase 2:
# "≥20 complete sessions parsed for pipeline verification, no outcome
# reads"). Build 1.2.1.
#
# Streams MLES-CAPTURE-1.2 runs (four files heap-merged by eventSeq,
# O(1) memory), reconstructs BBO / 10-level MBP book / tape / 1-minute
# bars, builds the FROZEN level hierarchy (mrofyt_levels), the causal
# 20-session baselines (mrofyt_signals.BaselineStore), the causal
# feature dictionary where its definition is fully specified in frozen
# code, the key-level wall state machine (mrofyt_wall_engine), the
# RVMR-V1 regime tag (rvmr_spec), and evaluates the six FROZEN
# detectors (mrofyt_signals.DETECTORS) on completed 10-second decision
# windows. It emits a compact signal ledger: counts, states, feature
# availability, regime tags, latency. Nothing else.
#
# THE RUNNER COMPUTES NO OUTCOME. No forward return, markout, fill,
# stop, target, R or P&L exists here. compute_outcomes() is a locked
# door that opens only after the committed State-C readiness freeze
# (mrof_engine.research_unlocked()). Two frozen inputs whose exact
# construction is NOT in frozen code are passed as None so their
# detectors disqualify by design, and the ledger names them:
#   resid_tail_5pct  (A4 expected-response residual model, feature 5)
#   trend_dir        (A5 "already-frozen MROF multi-timeframe state")
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import collections
import datetime as _dt
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', 'mrof'))
sys.path.insert(0, os.path.join(HERE, '..', 'rvmr'))

import mles_v12_adapter as AD          # noqa: E402
import mles_v12_audit as AU            # noqa: E402
import mrof_engine as ME               # noqa: E402
import mrofyt_levels as LV             # noqa: E402
import mrofyt_signals as SIG           # noqa: E402
import mrofyt_wall_engine as WALL      # noqa: E402
import rvmr_spec as RV                 # noqa: E402

RUNNER_VERSION = 'MROF-YT-RUNNER-1.2.1'
TICK = SIG.TICK
BOOK_K = 10                            # frozen primary book depth
DECISION_S = 10.0                      # frozen decision window
SUB_S = 2.5                            # frozen persistence subwindow
TRADE_RETAIN_S = 180.0                 # longest frozen context horizon
RADIUS_FALLBACK_TICKS = 4              # eligibility floor when ATR unknown
NOT_WIRED = {
    'resid_tail_5pct': 'A4 expected-response residual model (feature 5) '
                       'is fit-on-prior-data and not in frozen code',
    'trend_dir': 'A5 requires the already-frozen MROF multi-timeframe '
                 'state; none exists in code',
}
OPEN_LEVELS = ('OVERNIGHT_HIGH', 'OVERNIGHT_LOW', 'YDAY_HIGH', 'YDAY_LOW',
               'GLOBEX_OPEN', 'CASH_OPEN_0930')
OUTCOMES_LOCKED = not ME.research_unlocked()


# ---------------------------------------------------------------------
# outcome lock
# ---------------------------------------------------------------------
def compute_outcomes(*_a, **_k):
    """The only outcome entrypoint. Locked in State A/B."""
    if not ME.research_unlocked():
        raise RuntimeError('STATE-C LOCKED: outcome computation requires '
                           'a committed readiness freeze '
                           '(MROF_V1_STATE_C_AUTHORIZED.json).')
    raise NotImplementedError('State-C outcome stage is a separate, '
                              'later freeze; not part of this runner.')


# ---------------------------------------------------------------------
# US Eastern clock (stdlib only; no tzdata dependency on Windows)
# ---------------------------------------------------------------------
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def _nth_sunday(year, month, n):
    d = _dt.date(year, month, 1)
    first_sun = d + _dt.timedelta(days=(6 - d.weekday()) % 7)
    return first_sun + _dt.timedelta(days=7 * (n - 1))


def _dst_window(year):
    s = _nth_sunday(year, 3, 2)           # 2nd Sunday March, 02:00 EST
    e = _nth_sunday(year, 11, 1)          # 1st Sunday Nov,   02:00 EDT
    start = (_dt.datetime(s.year, s.month, s.day, 7, tzinfo=_dt.timezone.utc)
             - _EPOCH).total_seconds()
    end = (_dt.datetime(e.year, e.month, e.day, 6, tzinfo=_dt.timezone.utc)
           - _EPOCH).total_seconds()
    return start, end


_dst_cache = {}


def et_offset(epoch):
    """Seconds to ADD to UTC epoch to get US Eastern local time."""
    year = _dt.datetime.utcfromtimestamp(epoch).year
    w = _dst_cache.get(year)
    if w is None:
        w = _dst_cache[year] = _dst_window(year)
    return -4 * 3600 if w[0] <= epoch < w[1] else -5 * 3600


def et_parts(epoch):
    """(YYYYMMDD local date, local second-of-day)."""
    loc = epoch + et_offset(epoch)
    day = int(loc // 86400)
    d = _EPOCH.date() + _dt.timedelta(days=day)
    return d.strftime('%Y%m%d'), loc - day * 86400


def session_id(epoch):
    """CME session date: 18:00 ET rolls to the next calendar date
    (identical to the recorder's SessionOf)."""
    day, sod = et_parts(epoch)
    if sod >= 18 * 3600:
        d = _dt.datetime.strptime(day, '%Y%m%d').date() + _dt.timedelta(1)
        return d.strftime('%Y%m%d')
    return day


def sod_seconds(epoch):
    return et_parts(epoch)[1]


# ---------------------------------------------------------------------
# rolling helpers (frozen definitions, streaming form)
# ---------------------------------------------------------------------
class RollingTrailingRatio:
    """rvmr_spec.trailing_ratio in streaming form: value / mean of the
    previous W values (current excluded); None until W prior values."""

    def __init__(self, w=RV.W):
        self.w = w
        self.q = collections.deque()
        self.s = 0.0

    def push(self, v):
        out = None
        if len(self.q) == self.w:
            m = self.s / self.w
            out = (v / m) if m > 0 else None
            self.s -= self.q.popleft()
        self.q.append(v)
        self.s += v
        return out


class RollingATR20:
    def __init__(self):
        self.tr = collections.deque(maxlen=20)
        self.prev_close = None

    def push(self, h, l, c):
        if self.prev_close is None:
            tr = h - l
        else:
            tr = max(h - l, abs(h - self.prev_close),
                     abs(l - self.prev_close))
        self.tr.append(tr)
        self.prev_close = c
        return sum(self.tr) / 20.0 if len(self.tr) == 20 else None


class Hist:
    """Fixed 1 ms latency histogram (no per-event storage)."""

    def __init__(self, bins=5000):
        self.h = [0] * (bins + 1)
        self.n = 0

    def add(self, ms):
        ms = 0 if ms < 0 else min(int(ms), len(self.h) - 1)
        self.h[ms] += 1
        self.n += 1

    def pct(self, p):
        if not self.n:
            return None
        want = p * self.n
        cum = 0
        for i, c in enumerate(self.h):
            cum += c
            if cum >= want:
                return i
        return len(self.h) - 1


# ---------------------------------------------------------------------
# per-level approach state
# ---------------------------------------------------------------------
class Approach:
    __slots__ = ('id', 'level_id', 'level_px', 't0', 'ad', 'touch', 'mid0',
                 'windows', 'next_te', 'crossed', 'returned', 'blocking',
                 'episode', 'clear_t', 'wall_state', 'exec_at', 'add_at',
                 'exec_before_add', 'state_hist', 'active', 'end_t')

    def __init__(self, aid, level_id, level_px, t0, ad, mid0, blocking):
        self.id = aid
        self.level_id = level_id
        self.level_px = level_px
        self.t0 = t0
        self.ad = ad                     # +1 approaching from below
        self.touch = mid0                # extreme toward the level
        self.mid0 = mid0
        self.windows = 0
        self.next_te = t0 + DECISION_S
        self.crossed = False
        self.returned = False
        self.blocking = blocking         # 'ask' if ad>0 else 'bid'
        self.episode = None              # WallEpisode when a wall exists
        self.clear_t = None
        self.wall_state = 'NO_QUALIFYING_WALL'
        self.exec_at = 0.0               # executed at level (±2 ticks)
        self.add_at = 0.0                # depth added at level after exec
        self.exec_before_add = False
        self.state_hist = collections.Counter()
        self.active = True
        self.end_t = None                # set when the retreat ends it


# ---------------------------------------------------------------------
# instrument state (carried across sessions; reset per session where
# the frozen definition says so)
# ---------------------------------------------------------------------
class InstrumentState:
    def __init__(self, instrument):
        self.instrument = instrument
        self.baseline = SIG.BaselineStore(20)
        self.baseline_sessions = 0
        self.rng_ratio = RollingTrailingRatio()
        self.vol_ratio = RollingTrailingRatio()
        self.atr = RollingATR20()
        self.atr20 = None
        self.yday = None                 # (high, low, close)
        self.week_hl = {}                # iso-week -> [high, low]
        self.session = None
        self.reset_session(None)

    def reset_session(self, ses):
        self.session = ses
        self.vwap = LV.SessionVwap()
        self.opens = dict(GLOBEX_OPEN=None, CASH_OPEN_0930=None)
        self.on_high = self.on_low = None
        self.on_fixed = False
        self.run_high = self.run_low = None
        self.close = None
        self.bar = None                  # [minute_key, o, h, l, c, v]
        self.bars_in_session = 0
        self.regime = dict(range=None, volume=None)
        self.levels = {}
        self.approach_times = collections.defaultdict(collections.deque)
        self.approaches = {}             # level_id -> Approach (active)
        self.finishing = []              # ended, decision windows pending
        self.next_aid = 0
        self.reset_run()

    def reset_run(self):
        self.book = SIG.KLevelBook(BOOK_K)
        self.bid = self.ask = self.bsz = self.asz = None
        self.prev_q = None
        self.ready = False
        self.trades = collections.deque()          # (t, px, sz, sign)
        self.mids = collections.deque()            # (t, mid)
        self.ofi = collections.deque()             # (t, e)
        self.d3 = collections.deque()              # (t, d3_bid, d3_ask)
        self.exec3 = collections.deque()           # (t, side, qty)
        self.grid10 = None
        self.grid25 = None


# ---------------------------------------------------------------------
# the runner
# ---------------------------------------------------------------------
class Runner:
    def __init__(self, capture_dir, instruments=('NQ', 'MNQ'),
                 max_sessions=None, verbose=False):
        self.dir = capture_dir
        self.instruments = tuple(instruments)
        self.max_sessions = max_sessions
        self.verbose = verbose
        self.states = {i: InstrumentState(i) for i in self.instruments}
        self.ledger = dict(runner=RUNNER_VERSION, outcomes='LOCKED',
                           not_wired=dict(NOT_WIRED),
                           evaluation='10s decision windows from approach '
                                      'start, evaluated on the frozen 2.5s '
                                      'persistence grid',
                           sessions={}, totals=collections.Counter(),
                           feature_none=collections.Counter(),
                           fires=[], states=collections.Counter(),
                           regime_at_window=collections.Counter(),
                           latency_ms={}, runs=[])
        self.lat = {i: Hist() for i in self.instruments}

    # ---- discovery ------------------------------------------------
    def plan(self):
        """[(instrument, session, [manifest paths sorted by start])]"""
        by = collections.defaultdict(list)
        for mp in AU.discover_manifests(self.dir):
            try:
                man = json.load(open(mp))
            except Exception:
                continue
            inst = man.get('instrument')
            if inst not in self.instruments or \
                    man.get('schema') != AD.SCHEMA:
                continue
            by[(inst, man.get('session'))].append(
                (man.get('firstRecvUtc') or '', mp, man))
        plan = []
        for (inst, ses), lst in by.items():
            lst.sort()
            plan.append((inst, ses, [(mp, man) for _, mp, man in lst]))
        plan.sort(key=lambda x: (x[1], x[0]))
        return plan

    # ---- main -------------------------------------------------------
    def run(self):
        plan = self.plan()
        seen_sessions = []
        for inst, ses, runs in plan:
            if ses not in seen_sessions:
                seen_sessions.append(ses)
                if self.max_sessions and len(seen_sessions) > \
                        self.max_sessions:
                    break
            st = self.states[inst]
            if st.session != ses:
                if st.session is not None:
                    self._close_session(st)
                st.reset_session(ses)
            for mp, man in runs:
                self._process_run(st, mp, man)
            self.ledger['sessions'].setdefault(ses, {})[inst] = \
                self._session_summary(st)
        for st in self.states.values():
            if st.session is not None:
                self._close_session(st)
        for inst, h in self.lat.items():
            self.ledger['latency_ms'][inst] = dict(
                p50=h.pct(0.5), p95=h.pct(0.95), n=h.n)
        self.ledger['baseline_sessions'] = {
            i: s.baseline_sessions for i, s in self.states.items()}
        return self.ledger

    def _close_session(self, st):
        # a decision window is FROZEN at 10 s: partial windows at the
        # session close are never evaluated, only counted
        pend = sum(1 for ap in st.approaches.values() if ap.active)
        pend += len(st.finishing)
        self.ledger['totals']['windows_incomplete_at_close'] += pend
        st.baseline.close_session()
        st.baseline_sessions += 1
        if st.run_high is not None and st.close is not None:
            st.yday = (st.run_high, st.run_low, st.close)
        if st.run_high is not None and st.session:
            d = _dt.datetime.strptime(st.session, '%Y%m%d').date()
            wk = d.isocalendar()[:2]
            hl = st.week_hl.setdefault(wk, [st.run_high, st.run_low])
            hl[0] = max(hl[0], st.run_high)
            hl[1] = min(hl[1], st.run_low)

    # ---- one run ------------------------------------------------------
    def _process_run(self, st, mp, man):
        base = os.path.dirname(os.path.abspath(mp))
        paths = AD.run_paths(man, base)
        st.reset_run()
        n = 0
        crossed = 0
        quotes = 0
        rec = dict(instrument=st.instrument, session=st.session,
                   run_id=man.get('runId'), build=man.get('recorderBuild',
                                                          '1.2.0'))
        self._rebuild_levels(st)
        for e in AD.merge_run(paths, lite=True):
            n += 1
            k = e['stream']
            t = e['t_recv']
            if t is None:
                continue
            suppressed = 'DATA_SUPPRESSED' in e['flags']
            if k == 'QUALITY':
                if e['kind'] == 'BOOK_READY':
                    st.ready = True
                elif e['kind'] in ('DISCONNECT', 'RECONNECT',
                                   'BOOK_RESYNC_START'):
                    st.ready = False
                continue
            if e['t_exch'] is not None:
                self.lat[st.instrument].add((t - e['t_exch']) * 1000.0)
            if k == 'QUOTE':
                quotes += 1
                b, bs, a, asz = e['bid_px'], e['bid_sz'], e['ask_px'], \
                    e['ask_sz']
                if b is None or a is None:
                    continue
                if b >= a:
                    crossed += 1
                    continue
                if st.prev_q is not None:
                    inc = ME.ofi_increment(st.prev_q, dict(
                        bidPx=b, bidSz=bs or 0, askPx=a, askSz=asz or 0))
                    st.ofi.append((t, inc))
                st.prev_q = dict(bidPx=b, bidSz=bs or 0, askPx=a,
                                 askSz=asz or 0)
                st.bid, st.ask, st.bsz, st.asz = b, bs, a, asz
                mid = (a + b) / 2.0
                st.mids.append((t, mid))
                if not suppressed:
                    self._on_mid(st, t, mid)
            elif k == 'TRADE':
                px, sz = e['px'], e['sz']
                if px is None or sz is None:
                    continue
                sign = 1 if e['aggr_inf'] == 'BUY' else \
                    (-1 if e['aggr_inf'] == 'SELL' else 0)
                st.trades.append((t, px, sz, sign))
                self._on_trade(st, t, px, sz, sign)
                if sign and st.approaches:
                    self._exec_at_levels(st, t, px, sz, sign)
            elif k == 'DEPTH':
                st.book.apply(e['action'], e['side'].lower(), e['level'],
                              e['px'], e['sz'] or 0.0)
                if st.approaches and e['action'] in ('ADD', 'UPDATE'):
                    self._add_at_levels(st, t, e)
                st.d3.append((t, st.book.depth('bid', 3),
                              st.book.depth('ask', 3)))
            self._evict(st, t)
            self._grid(st, t)
        rec.update(events=n, quotes=quotes, crossed_quotes=crossed)
        self.ledger['runs'].append(rec)
        self.ledger['totals']['events'] += n

    # ---- eviction of bounded deques ----------------------------------
    @staticmethod
    def _evict(st, t):
        while st.trades and st.trades[0][0] < t - TRADE_RETAIN_S:
            st.trades.popleft()
        while st.mids and st.mids[0][0] < t - 60.0:
            st.mids.popleft()
        while st.ofi and st.ofi[0][0] < t - DECISION_S:
            st.ofi.popleft()
        while st.d3 and st.d3[0][0] < t - 2.0:
            st.d3.popleft()
        while st.exec3 and st.exec3[0][0] < t - 2.0:
            st.exec3.popleft()

    # ---- bars, opens, extremes, VWAP, RVMR ----------------------------
    def _on_trade(self, st, t, px, sz, sign):
        day, sod = et_parts(t)
        mkey = (day, int(sod // 60))
        if st.opens['GLOBEX_OPEN'] is None:
            st.opens['GLOBEX_OPEN'] = px
        if sod >= 9.5 * 3600 and st.opens['CASH_OPEN_0930'] is None \
                and sod < 18 * 3600:
            st.opens['CASH_OPEN_0930'] = px
        if sod < 9.5 * 3600 or sod >= 18 * 3600:
            st.on_high = px if st.on_high is None else max(st.on_high, px)
            st.on_low = px if st.on_low is None else min(st.on_low, px)
        elif not st.on_fixed:
            st.on_fixed = True
        st.run_high = px if st.run_high is None else max(st.run_high, px)
        st.run_low = px if st.run_low is None else min(st.run_low, px)
        st.close = px
        st.vwap.update(px, sz)
        if st.bar is None or st.bar[0] != mkey:
            if st.bar is not None:
                _, o, h, l, c, v = st.bar
                st.atr20 = st.atr.push(h, l, c)
                st.regime = dict(range=RV.bucket(st.rng_ratio.push(h - l)),
                                 volume=RV.bucket(st.vol_ratio.push(v)))
                st.bars_in_session += 1
                self._rebuild_levels(st)
            st.bar = [mkey, px, px, px, px, sz]
        else:
            b = st.bar
            b[2] = max(b[2], px)
            b[3] = min(b[3], px)
            b[4] = px
            b[5] += sz
        if sign:
            side = 'ask' if sign > 0 else 'bid'
            st.exec3.append((t, side, sz))

    def _rebuild_levels(self, st):
        lv = {}
        if st.yday:
            yh, yl, yc = st.yday
            lv['YDAY_HIGH'], lv['YDAY_LOW'] = yh, yl
            lv.update({k: v for k, v in LV.pivots(yh, yl, yc).items()
                       if k in ('PP', 'M2', 'M3')})
        if st.session:
            d = _dt.datetime.strptime(st.session, '%Y%m%d').date()
            wk = (d - _dt.timedelta(days=7)).isocalendar()[:2]
            if wk in st.week_hl:
                lv['LWEEK_HIGH'], lv['LWEEK_LOW'] = st.week_hl[wk]
        if st.on_fixed and st.on_high is not None:
            lv['OVERNIGHT_HIGH'], lv['OVERNIGHT_LOW'] = st.on_high, st.on_low
        for k, v in st.opens.items():
            if v is not None:
                lv[k] = v
        lv.update({k: v for k, v in st.vwap.state().items()
                   if v is not None})
        st.levels = lv

    # ---- mid updates: approach detection --------------------------------
    def _radius(self, st):
        if st.atr20 is None:
            return RADIUS_FALLBACK_TICKS * TICK
        return LV.eligibility_radius(st.atr20)

    def _on_mid(self, st, t, mid):
        rad = self._radius(st)
        for lid, L in st.levels.items():
            if lid not in LV.ACTIVE_LEVEL_IDS:
                continue
            ap = st.approaches.get(lid)
            inside = abs(mid - L) <= rad
            if ap is None or not ap.active:
                if inside:
                    # re-arm rule: previous approach must have ended by
                    # a >=2-tick retreat beyond the radius (frozen)
                    if ap is not None and not ap.returned:
                        continue
                    ad = 1 if L > mid else (-1 if L < mid else 0)
                    if ad == 0:
                        continue
                    st.next_aid += 1
                    ap = Approach(st.next_aid, lid, L, t, ad, mid,
                                  'ask' if ad > 0 else 'bid')
                    st.approaches[lid] = ap
                    q = st.approach_times[lid]
                    q.append(t)
                    while q and q[0] < t - 60.0:
                        q.popleft()
                    self._select_wall(st, ap, t)
                    self.ledger['totals']['approaches'] += 1
                    self.ledger['totals']['approach_' +
                                          LV.FAMILY_OF.get(lid, '?')] += 1
                continue
            # active approach: track touch extreme, cross, return
            if (ap.ad > 0 and mid > ap.touch) or (ap.ad < 0 and mid < ap.touch):
                ap.touch = mid
            beyond = (mid - L) * ap.ad
            if beyond >= TICK:
                ap.crossed = True
            elif ap.crossed and beyond <= -TICK:
                ap.returned = True
            if not inside and abs(mid - L) > rad + 2 * TICK:
                ap.active = False
                ap.returned = True           # retreat re-arms (frozen)
                ap.end_t = t
                st.finishing.append(ap)      # its windows still complete

    def _select_wall(self, st, ap, t):
        book = st.book.ask if ap.blocking == 'ask' else st.book.bid
        sod = sod_seconds(t)
        w = WALL.select_wall([(px, sz) for px, sz in book], ap.level_px,
                             lambda sz: st.baseline.z('disp_size', sod, sz))
        if w:
            px, sz, z = w
            ap.episode = WALL.WallEpisode(px, sz, z, ap.ad)

    def _exec_at_levels(self, st, t, px, sz, sign):
        for ap in st.approaches.values():
            if not ap.active:
                continue
            if abs(px - ap.level_px) <= 2 * TICK and sign == ap.ad:
                ap.exec_at += sz
                ap.exec_before_add = True
                if ap.episode and abs(px - ap.episode.wall_px) < 1e-9:
                    ap.episode.on_execute(sz)

    def _add_at_levels(self, st, t, e):
        for ap in st.approaches.values():
            if not ap.active or e['side'].lower() != ap.blocking:
                continue
            if abs(e['px'] - ap.level_px) <= 2 * TICK and ap.exec_before_add:
                ap.add_at += e['sz'] or 0.0
                if ap.episode and abs(e['px'] - ap.episode.wall_px) < 1e-9:
                    ap.episode.on_add(e['sz'] or 0.0)

    # ---- grids: baselines every 10s / 2.5s, decisions per approach ----
    def _grid(self, st, t):
        g10 = math.floor(t / DECISION_S)
        if st.grid10 is None:
            st.grid10 = g10
        elif g10 > st.grid10:
            te = g10 * DECISION_S
            self._observe_baselines(st, te)
            st.grid10 = g10
        g25 = math.floor(t / SUB_S)
        if st.grid25 is None:
            st.grid25 = g25
        elif g25 > st.grid25:
            st.grid25 = g25
            # VWAP/opens/extremes move inside a minute; refresh the level
            # dictionary on the grid, not only at 1m bar close
            self._rebuild_levels(st)
            self._decisions(st, g25 * SUB_S)

    @staticmethod
    def _between(dq, t0, t1):
        """Items of a time-ordered deque with t0 <= t < t1, scanning
        from the right (windows are recent)."""
        out = []
        for x in reversed(dq):
            tt = x[0]
            if tt >= t1:
                continue
            if tt < t0:
                break
            out.append(x)
        out.reverse()
        return out

    def _window_stats(self, st, t0, t1):
        tr = self._between(st.trades, t0, t1)
        D, d = SIG.aggr_delta(tr)
        ofi = sum(e for _, e in self._between(st.ofi, t0, t1))
        m0 = m1 = None
        for tt, m in reversed(st.mids):
            if tt < t1 and m1 is None:
                m1 = m
            if tt < t0:
                m0 = m
                break
        if m0 is None:
            m0 = m1
        r = SIG.price_response(m0, m1) if (m0 is not None and
                                           m1 is not None) else None
        bi3 = st.book.bi(3)
        return tr, D, ofi, r, bi3, m1

    def _observe_baselines(self, st, te):
        if not st.ready:
            return
        sod = sod_seconds(te)
        # displayed-size baseline: the resting top-3 each side at the
        # grid (not every depth update — 20M/session would not be flat)
        for side in ('bid', 'ask'):
            book = st.book.bid if side == 'bid' else st.book.ask
            for _, sz in book[:3]:
                if sz > 0:
                    st.baseline.observe('disp_size', sod, float(sz))
        tr, D, ofi, r, bi3, _m = self._window_stats(st, te - DECISION_S, te)
        st.baseline.observe('delta10', sod, D)
        st.baseline.observe('ofi10', sod, ofi)
        if r is not None:
            st.baseline.observe('resp10', sod, r)
        if bi3 is not None:
            st.baseline.observe('bi3', sod, bi3)
        tr2, D2, ofi2, r2, _b, _m = self._window_stats(st, te - SUB_S, te)
        st.baseline.observe('delta2', sod, D2)
        st.baseline.observe('ofi2', sod, ofi2)
        if r2 is not None:
            st.baseline.observe('resp2', sod, r2)
        if st.regime['range'] is not None:
            self.ledger['regime_at_window'][
                'range_' + st.regime['range']] += 1

    def _control(self, st, sod, direction, D, ofi, r, bi3):
        z = st.baseline.z
        return SIG.control_score(z('delta10', sod, direction * D),
                                 z('ofi10', sod, direction * ofi),
                                 None if bi3 is None else
                                 z('bi3', sod, direction * bi3),
                                 None if r is None else
                                 z('resp10', sod, direction * r))

    def _control2(self, st, sod, direction, D, ofi, r, bi3):
        z = st.baseline.z
        return SIG.control_score(z('delta2', sod, direction * D),
                                 z('ofi2', sod, direction * ofi),
                                 None if bi3 is None else
                                 z('bi3', sod, direction * bi3),
                                 None if r is None else
                                 z('resp2', sod, direction * r))

    def _decisions(self, st, now):
        for ap in list(st.approaches.values()):
            if not ap.active:
                continue
            while ap.next_te <= now:
                te = ap.next_te
                ap.next_te += DECISION_S
                ap.windows += 1
                self._evaluate(st, ap, te)
            # A3 is a 2s trigger: evaluate on the 2.5s grid while active
            if st.ready:
                self._evaluate_a3(st, ap, now)
        # ended approaches: the decision window containing the retreat
        # still completes (the retreat IS the A1/A4 observation)
        keep = []
        for ap in st.finishing:
            last_te = ap.end_t + DECISION_S
            while ap.next_te <= now and ap.next_te <= last_te:
                te = ap.next_te
                ap.next_te += DECISION_S
                ap.windows += 1
                self._evaluate(st, ap, te)
            if ap.next_te <= last_te:
                keep.append(ap)
        st.finishing = keep

    def _evaluate(self, st, ap, te):
        if not st.ready:
            self.ledger['totals']['windows_suppressed'] += 1
            return
        self.ledger['totals']['windows'] += 1
        sod = sod_seconds(te)
        ad = ap.ad
        z = st.baseline.z
        tr, D, ofi, r, bi3, m_end = self._window_stats(
            st, te - DECISION_S, te)
        aggr_z = z('delta10', sod, ad * D)
        aggr_dir = ad if D * ad > 0 else (-ad if D else 0)
        progress = None
        if m_end is not None and r is not None and aggr_dir:
            progress = aggr_dir * r
        rr = SIG.replenishment_ratio(ap.add_at, ap.exec_at) \
            if ap.exec_at > 0 else None
        if rr is not None:
            st.baseline.observe('rr', sod, rr)
        replenish_z = z('rr', sod, rr) if rr is not None else None
        tr2, D2, ofi2, r2, bi3_2, _m = self._window_stats(st, te - SUB_S, te)
        opp_flip_z = self._control2(st, sod, -ad, D2, ofi2, r2, bi3_2)
        retreat = None
        if m_end is not None:
            retreat = ad * (ap.touch - m_end) / TICK
        agree, decay = SIG.persistence(tr, te - DECISION_S, ad)
        swp = SIG.sweep(tr)
        reclaimed = SIG.sweep_reclaimed(swp, list(st.mids)) if swp else False
        control_z = self._control(st, sod, ad, D, ofi, r, bi3)
        # wall features
        wall_z = ap.episode.wall_z if ap.episode else None
        exec_vs = (ap.episode.executed / (ap.episode.initial + WALL.EPS)) \
            if ap.episode else None
        book = st.book.ask if ap.blocking == 'ask' else st.book.bid
        wall_disp = None
        if ap.episode:
            wall_disp = sum(sz for px, sz in book
                            if abs(px - ap.episode.wall_px) < 1e-9)
            if wall_disp <= 0 and ap.clear_t is None:
                ap.clear_t = te
            elif wall_disp > 0:
                ap.clear_t = None
        cleared_held = bool(ap.clear_t is not None and
                            te - ap.clear_t >= 5.0)
        post_clear_z = None
        post_done = False
        if ap.clear_t is not None and te >= ap.clear_t + 5.0:
            post_done = True
            trc, Dc, ofic, rc, bic, _m = self._window_stats(
                st, ap.clear_t, ap.clear_t + 5.0)
            post_clear_z = self._control2(st, sod, ad, Dc, ofic, rc, bic)
        opp_rr = replenish_z            # opposing-side refill after cross
        in_open = 9.5 * 3600 <= sod < 9.75 * 3600
        held_5s = bool(ap.crossed and not ap.returned and m_end is not None
                       and (m_end - ap.level_px) * ad >= TICK and
                       te - ap.t0 >= 5.0)
        f = dict(
            level_id=ap.level_id, approach_id=ap.id, ad=ad,
            aggr_z=aggr_z, aggr_dir=aggr_dir, progress_ticks=progress,
            replenish_z=replenish_z,
            approaches_60s=len(st.approach_times[ap.level_id]),
            opp_flip_z=opp_flip_z, retreat_ticks=retreat,
            wall_z=wall_z, exec_vs_displayed=exec_vs,
            replenish_ratio=rr, cleared_held_5s=cleared_held,
            persist_agree=agree, post_clear_z=post_clear_z,
            break_dir=ad, sweep_reclaimed_5s=reclaimed,
            returned_through_level=ap.returned,
            resid_tail_5pct=None,                    # NOT WIRED (A4)
            trend_dir=None, adverse_z=None,           # NOT WIRED (A5)
            adverse_progress_ticks=None, trend_flip_z=None,
            in_0930_0945=in_open and ap.level_id in OPEN_LEVELS,
            control_z=control_z, clean_cross=ap.crossed and not ap.returned,
            held_5s=held_5s, opp_replenish_z=opp_rr,
            actions_distinguishable=True, tgt_drop_frac=None,
            opp_drop_frac=None, delta_z=None, advance_ticks=None,
            vacuum_dir=0,
            # wall state machine inputs
            data_ok=True, rr=rr, opp_control_z=opp_flip_z,
            exec_vs_display=exec_vs, crossed_1tick=ap.crossed,
            tgt_drop_2s=None, opp_drop_2s=None,
            withdrawal_classifiable=True, post_clear_done=post_done,
            same_control_z=control_z, reclaimed_5s=reclaimed)
        for k in ('aggr_z', 'replenish_z', 'opp_flip_z', 'wall_z',
                  'post_clear_z', 'control_z', 'progress_ticks',
                  'resid_tail_5pct', 'trend_dir'):
            if f.get(k) is None:
                self.ledger['feature_none'][k] += 1
        # wall state (overlay; armed states never enter)
        ap.wall_state = WALL.wall_state(ap.wall_state, f)
        ap.state_hist[ap.wall_state] += 1
        self.ledger['states'][ap.wall_state] += 1
        # frozen detectors (A3 handled on its own 2s grid)
        for fam in ('A1', 'A2', 'A4', 'A5', 'A6'):
            d = SIG.DETECTORS[fam](f)
            if d:
                self._fire(st, fam, d, te, ap)

    def _evaluate_a3(self, st, ap, now):
        if len(st.d3) < 2:
            return
        t_old, b_old, a_old = st.d3[0]
        _, b_new, a_new = st.d3[-1]
        if now - t_old < 1.0:
            return
        ex_ask = sum(q for tt, s, q in st.exec3 if s == 'ask')
        ex_bid = sum(q for tt, s, q in st.exec3 if s == 'bid')
        self.ledger['totals']['a3_checks'] += 1
        for vdir, tgt_old, tgt_new, tgt_ex, opp_old, opp_new in (
                (+1, a_old, a_new, ex_ask, b_old, b_new),
                (-1, b_old, b_new, ex_bid, a_old, a_new)):
            if tgt_old <= 0 or opp_old <= 0:
                continue
            tgt_drop = max(tgt_old - tgt_new - tgt_ex, 0.0) / tgt_old
            opp_drop = max(opp_old - opp_new, 0.0) / opp_old
            if not SIG.vacuum_event(tgt_drop, opp_drop):
                continue
            self.ledger['totals']['vacuum_events'] += 1
            sod = sod_seconds(now)
            tr2, D2, ofi2, r2, _b, _m = self._window_stats(st, now - 2.0, now)
            delta_z = st.baseline.z('delta2', sod, vdir * D2)
            adv = None if r2 is None else vdir * r2
            f = dict(actions_distinguishable=True, tgt_drop_frac=tgt_drop,
                     opp_drop_frac=opp_drop, delta_z=delta_z,
                     advance_ticks=adv, vacuum_dir=vdir)
            if delta_z is None:
                self.ledger['feature_none']['delta_z'] += 1
            d = SIG.DETECTORS['A3'](f)
            if d:
                self._fire(st, 'A3', d, now, ap)

    def _fire(self, st, fam, direction, t, ap):
        self.ledger['totals']['fires'] += 1
        self.ledger['totals']['fires_' + fam] += 1
        if len(self.ledger['fires']) < 5000:
            self.ledger['fires'].append(dict(
                instrument=st.instrument, session=st.session, family=fam,
                direction=direction, t=round(t, 3), level=ap.level_id,
                approach=ap.id, regime=dict(st.regime),
                state=ap.wall_state))

    def _session_summary(self, st):
        return dict(bars=st.bars_in_session, levels=sorted(st.levels),
                    atr20=st.atr20, regime=dict(st.regime),
                    baseline_sessions_before=st.baseline_sessions)


# ---------------------------------------------------------------------
# reporting
# ---------------------------------------------------------------------
def summary(ledger):
    tot = ledger['totals']
    lines = ['%s  outcomes=%s' % (ledger['runner'], ledger['outcomes']),
             'sessions=%d runs=%d events=%d'
             % (len(ledger['sessions']), len(ledger['runs']),
                tot.get('events', 0)),
             'baseline sessions: %s' % ledger.get('baseline_sessions'),
             'approaches=%d windows=%d (suppressed %d) fires=%d '
             'vacuum_events=%d'
             % (tot.get('approaches', 0), tot.get('windows', 0),
                tot.get('windows_suppressed', 0), tot.get('fires', 0),
                tot.get('vacuum_events', 0))]
    fam = ', '.join('%s=%d' % (k[6:], v) for k, v in sorted(tot.items())
                    if k.startswith('fires_'))
    lines.append('fires by family: %s' % (fam or 'none'))
    app = ', '.join('%s=%d' % (k[9:], v) for k, v in sorted(tot.items())
                    if k.startswith('approach_'))
    lines.append('approaches by family: %s' % (app or 'none'))
    lines.append('wall states: %s' % dict(ledger['states']))
    lines.append('feature None counts: %s' % dict(ledger['feature_none']))
    lines.append('regime at windows: %s' % dict(ledger['regime_at_window']))
    lines.append('latency ms: %s' % ledger['latency_ms'])
    lines.append('NOT WIRED (detectors disqualify by design): %s'
                 % ', '.join(sorted(ledger['not_wired'])))
    return '\n'.join(lines)


def main(argv=None):
    import argparse
    p = argparse.ArgumentParser(description=RUNNER_VERSION)
    p.add_argument('capture_dir')
    p.add_argument('--out', default=None, help='ledger JSON path')
    p.add_argument('--instruments', default='NQ,MNQ')
    p.add_argument('--sessions', type=int, default=None)
    p.add_argument('--outcomes', action='store_true',
                   help='attempt the State-C outcome stage (locked)')
    a = p.parse_args(argv)
    if a.outcomes:
        compute_outcomes()
    r = Runner(a.capture_dir, a.instruments.split(','), a.sessions)
    led = r.run()
    print(summary(led))
    if a.out:
        json.dump(led, open(a.out, 'w'), default=str, indent=1)
        print('ledger ->', a.out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
