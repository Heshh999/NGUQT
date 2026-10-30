#!/usr/bin/env python3
"""mrofyt_flowlevels.py - MROF-YT-W7-FLOWLEVELS-1.0

MROF_YT_WAVE7_FLOWLEVELS_REGISTRATION.md turned into running code. The
one mechanism with support -- traders trapped on a break are forced out
-- moved off the six daily levels (which a normal day rarely reaches)
onto levels the tape builds every day, graded, with four exits.

    levels   SWING highs/lows of one-minute mid bars (5 bars each side),
             ABSORPTION prices (10 s aggression z >= 3 with <= 1 tick of
             progress), yesterday's POC / VAH / VAL; each active from the
             moment it is known, one trade attempt per level
    entries  FAILED: price breaks the level by 2 ticks, comes back through
             it by a tick within 120 s, and the 10 s flow turns to the
             other side (z >= 1.0) within 20 s: fade it. HELD: it stays
             beyond for 120 s with net flow in the break direction:
             follow it. Entries 09:30-15:30 ET only; flat by 15:59 ET.
    grade    one point each: TRAPPED volume (at or above the DEV median),
             ABSORPTION at the level, STRONG turn (z >= 2), FRESH level,
             CONFLUENCE with a daily level. 4-5 A+, 3 A, 2 B, 0-1 skip.
    stop     structural: 2 ticks beyond the sweep's extreme (FAILED) or
             back through the level (HELD), 12..60 ticks
    exits    E1 NEXT LEVEL: the nearest level beyond the entry, if it is
                at least 1.5 x the stop away (no cap); a nearer level is
                in the way: no E1 trade; no level at all: max(0.2 x daily
                range, 1.5 x stop)
             E2 TAPE: no target; out at the first 10 s tick where 2 of 4
                tape signs say the move is dying (60 s flow faded, the
                other side hitting hard, our side absorbed, a 120 s stall)
             E3 HYBRID: half at E1's target, half on E2
             E4 BASELINE: the original 25-point target, 15-point stop
    tests    FAILED and HELD at grade A or A+, each exit (8), and whether
             a higher grade earns more (1); net R after costs, one
             position at a time, session-clustered, Holm over nine

    python3 mrofyt_flowlevels.py "<capture>" --out w7.json \\
            --frozen-out w7_frozen.json           # DEV: seen days, not a test
    python3 mrofyt_flowlevels.py "<replay folder>" --evaluate w7_frozen.json \\
            --holdout --out w7_replay.json        # untouched replay days
    python3 mrofyt_flowlevels.py "<capture>" --evaluate w7_frozen.json \\
            --unblind --out w7_eval.json          # CHECKPOINT ONLY

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import bisect
import collections
import json
import math
import os
import sys

import mrofyt_bigmove as BM
import mrofyt_context as CX
import mrofyt_costs as CO
import mrofyt_discover as DI
import mrofyt_pilot as PI
import mrofyt_runner as RUN
import mrofyt_signals as SIG

W7_VERSION = 'MROF-YT-W7-FLOWLEVELS-1.0'
REGISTRATION = 'MROF_YT_WAVE7_FLOWLEVELS_REGISTRATION.md'
DEV_END = BM.DEV_END
HOLDOUT_BEFORE = '20260901'
HOLDOUT_LEDGER = 'MROF_REPLAY_HOLDOUT_EXPOSURE.json'
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
TICK = SIG.TICK

# registration 1: levels
SWING_N = 5                      # one-minute bars each side
SWING_MIN_SIDE = 4               # of which at least this many recorded
ABS_Z = 3.0
ABS_RESP = 1.0                   # ticks
MERGE_TICKS = 2.0
DAILY_KEYS = ('YDAY_HIGH', 'YDAY_LOW', 'OVERNIGHT_HIGH', 'OVERNIGHT_LOW',
              'LWEEK_HIGH', 'LWEEK_LOW', 'SESSION_VWAP')

# registration 2: entries
BREAK_TICKS = 2.0
RECLAIM_TICKS = 1.0
RECLAIM_S = 120.0
HOLD_S = 120.0
CONFIRM_S = 20.0
FLIP_Z = 1.0
ENTRY_FROM, ENTRY_TO = 9.5 * 3600, 15.5 * 3600
FLAT_AT = 15 * 3600 + 59 * 60
FRESH_TICKS = 2.0
FRESH_GAP_S = 60.0

# registration 3: grade
STRONG_Z = 2.0
ABSORB_Z = 2.0
ABSORB_LOOKBACK_S = 600.0
ABSORB_NEAR_TICKS = 2.0
CONFLUENCE_TICKS = 8.0
GRADES = ((4, 'A+'), (3, 'A'), (2, 'B'), (0, 'SKIP'))

# registration 4: stops and exits
STOP_MIN, STOP_MAX = 12.0, 60.0
STOP_BUFFER = 2.0
NEXT_LEVEL_MIN_R = 1.5
VOL_TARGET_RANGE = 0.20
RANGE_SESSIONS, RANGE_MIN_SESSIONS = 14, 5
TAPE_NEED = 2
STALL_S = 120.0
BIG_D_Q = 0.90
BASE_TARGET, BASE_STOP = 100.0, 60.0
MAX_HOLD_S = 3 * 3600.0

# registration 5: tests
KINDS = ('FAILED', 'HELD')
EXITS = ('E1', 'E2', 'E3', 'E4')
MIN_POINTS = 3
MIN_EVENTS = 30
HOLM_ALPHA = 0.05
PRIMARY = PI.SIGNAL_SOURCE_INSTRUMENT


def grade_of(points):
    for floor, g in GRADES:
        if points >= floor:
            return g
    return 'SKIP'


def _sgn(x):
    return 1 if x > 0 else (-1 if x < 0 else 0)


# ---------------------------------------------------------------------
# a range-max / range-min tree with first-crossing search
# ---------------------------------------------------------------------
class Tree(object):
    """Over one run's compressed mid path: max and min of any index
    range, and the first index in a range at or beyond a price, each in
    O(log n)."""

    def __init__(self, ps):
        n = len(ps)
        size = 1
        while size < max(n, 1):
            size *= 2
        self.n, self.size = n, size
        mx = [-math.inf] * (2 * size)
        mn = [math.inf] * (2 * size)
        mx[size:size + n] = ps
        mn[size:size + n] = ps
        for k in range(size - 1, 0, -1):
            a, b = 2 * k, 2 * k + 1
            mx[k] = mx[a] if mx[a] >= mx[b] else mx[b]
            mn[k] = mn[a] if mn[a] <= mn[b] else mn[b]
        self.mx, self.mn = mx, mn

    def range_max(self, lo, hi):
        return self._range(lo, hi, self.mx, max, -math.inf)

    def range_min(self, lo, hi):
        return self._range(lo, hi, self.mn, min, math.inf)

    def _range(self, lo, hi, arr, f, ident):
        lo, hi = max(lo, 0), min(hi, self.n - 1)
        if lo > hi:
            return ident
        lo += self.size
        hi += self.size + 1
        out = ident
        while lo < hi:
            if lo & 1:
                out = f(out, arr[lo])
                lo += 1
            if hi & 1:
                hi -= 1
                out = f(out, arr[hi])
            lo //= 2
            hi //= 2
        return out

    def first_ge(self, lo, hi, x):
        """First index j in [lo, hi] with price >= x, or None."""
        return self._first(lo, hi, lambda k: self.mx[k] >= x)

    def first_le(self, lo, hi, x):
        return self._first(lo, hi, lambda k: self.mn[k] <= x)

    def _first(self, lo, hi, ok):
        lo, hi = max(lo, 0), min(hi, self.n - 1)
        if lo > hi:
            return None
        stack = [(1, 0, self.size - 1)]
        while stack:
            k, nl, nr = stack.pop()
            if nr < lo or nl > hi or not ok(k):
                continue
            if nl == nr:
                return nl
            mid = (nl + nr) // 2
            stack.append((2 * k + 1, mid + 1, nr))     # right after left
            stack.append((2 * k, nl, mid))
        return None

    def first_beyond(self, lo, hi, d, x):
        """First j in [lo, hi] with d * price >= d * x."""
        return self.first_ge(lo, hi, x) if d > 0 else \
            self.first_le(lo, hi, x)

    def best(self, lo, hi, d):
        """The furthest price in direction d over [lo, hi]."""
        return self.range_max(lo, hi) if d > 0 else self.range_min(lo, hi)


# ---------------------------------------------------------------------
# the runner: wave four's grid plus the two inputs wave seven needs
# ---------------------------------------------------------------------
class FlowRunner(DI.DiscoverRunner):
    """Wave four's runner; every grid record also carries its 10 s traded
    volume and the daily levels known at that instant. Hooks only."""

    def __init__(self, capture_dir, unblind=False, holdout=False, **kw):
        DI.DiscoverRunner.__init__(self, capture_dir, unblind=unblind, **kw)
        self.holdout = holdout
        self.ledger['wave7'] = dict(version=W7_VERSION)

    def plan(self):
        if not self.holdout:
            return DI.DiscoverRunner.plan(self)
        plan = PI.PilotRunner.plan(self)
        late = sorted({ses for _i, ses, _r in plan if ses >= HOLDOUT_BEFORE})
        if late:
            raise RUN.NoCaptureData(
                'a replay holdout folder may hold only sessions before %s; '
                '%s holds %s. Nothing was read.' % (
                    HOLDOUT_BEFORE, self.dir, ', '.join(late)))
        return plan

    def _observe_baselines(self, st, te):
        n0 = len(self.grid)
        DI.DiscoverRunner._observe_baselines(self, st, te)
        if len(self.grid) == n0:
            return
        g = self.grid[-1]
        tr = self._between(st.trades, te - RUN.DECISION_S, te)
        g['vol10'] = float(sum(x[2] for x in tr))
        g['w7_lv'] = tuple(st.levels.get(k) for k in DAILY_KEYS)


# ---------------------------------------------------------------------
# registration 1: levels
# ---------------------------------------------------------------------
def swing_levels(ts, ps):
    """[(t_on, price, 'SWING_H' | 'SWING_L')] from one run's mid path:
    one-minute bars of the mid; a bar whose high is above the 5 bars
    before it and not below the 5 after it is a swing high, known at the
    end of the 5th bar after it."""
    bars = collections.OrderedDict()
    for t, p in zip(ts, ps):
        m = int(t // 60)
        b = bars.get(m)
        if b is None:
            bars[m] = [p, p]
        else:
            if p > b[0]:
                b[0] = p
            if p < b[1]:
                b[1] = p
    out = []
    for m, (h, lo) in bars.items():
        left = [bars[k] for k in range(m - SWING_N, m) if k in bars]
        right = [bars[k] for k in range(m + 1, m + SWING_N + 1) if k in bars]
        if len(left) < SWING_MIN_SIDE or len(right) < SWING_MIN_SIDE:
            continue
        t_on = (m + SWING_N + 1) * 60.0
        if h > max(x[0] for x in left) and h >= max(x[0] for x in right):
            out.append((t_on, h, 'SWING_H'))
        if lo < min(x[1] for x in left) and lo <= min(x[1] for x in right):
            out.append((t_on, lo, 'SWING_L'))
    return out


def absorption_levels(grid):
    """Grid ticks where the 10 s aggression was extreme (z >= 3) and the
    price moved a tick or less: the grid mid is a level from then."""
    out = []
    for g in grid:
        z, r, mid = g.get('z_delta_s'), g.get('resp'), g.get('mid')
        if z is None or r is None or mid is None:
            continue
        if z >= ABS_Z and abs(r) <= ABS_RESP:
            out.append((g['t'], mid, 'ABSORPTION'))
    return out


def value_levels(prev_grid, t_on):
    """The previous session's POC, VAH and VAL from its 10 s volume at
    the grid mid (1-point bins, the context study's value area), active
    from t_on."""
    prof = collections.defaultdict(float)
    for g in prev_grid:
        if g.get('mid') is not None and g.get('vol10'):
            prof[int(math.floor(g['mid']))] += g['vol10']
    poc, vah, val = CX.value_area(prof)
    if poc is None:
        return []
    return [(t_on, poc, 'POC'), (t_on, vah, 'VAH'), (t_on, val, 'VAL')]


def merge_levels(levels):
    """In time order; a level within 2 ticks of an earlier one is the
    same level."""
    out = []
    for t_on, px, typ in sorted(levels):
        if any(abs(px - q[1]) <= MERGE_TICKS * TICK + 1e-9 for q in out):
            continue
        out.append((t_on, px, typ))
    return out


# ---------------------------------------------------------------------
# registration 2: the event at one level
# ---------------------------------------------------------------------
def _i_at(ts, t):
    return bisect.bisect_right(ts, t) - 1


def _side(level, ts, ps, tree):
    """(index, b): where the level starts to count and which way a break
    goes (+1 up through it). A swing high is broken upward, a swing low
    downward; any other level by whichever side price first leaves it
    to, 2 ticks away."""
    t_on, L, typ = level
    i_on = _i_at(ts, t_on)
    if i_on < 0:
        return None, 0
    if typ == 'SWING_H':
        return i_on, 1
    if typ == 'SWING_L':
        return i_on, -1
    if abs(ps[i_on] - L) >= BREAK_TICKS * TICK:
        return i_on, (1 if L > ps[i_on] else -1)
    n = len(ps)
    up = tree.first_ge(i_on + 1, n - 1, L + BREAK_TICKS * TICK)
    dn = tree.first_le(i_on + 1, n - 1, L - BREAK_TICKS * TICK)
    if up is None and dn is None:
        return None, 0
    if dn is None or (up is not None and up < dn):
        return up, -1                      # left upward: it breaks down
    return dn, 1


def detect(level, path, grid, gt):
    """One trade attempt at one level inside one recording run: the
    first 2-tick break after the level is known decides FAILED, HELD or
    nothing. Returns an event dict or None."""
    t_on, L, typ = level
    ts, ps, tree = path
    n = len(ps)
    i_ref, b = _side(level, ts, ps, tree)
    if i_ref is None:
        return None
    ib = tree.first_beyond(i_ref + 1, n - 1, b, L + b * BREAK_TICKS * TICK)
    if ib is None:
        return None
    t_break = ts[ib]
    # FRESH: nothing came within 2 ticks of it before the approach
    ifr = _i_at(ts, t_break - FRESH_GAP_S)
    fresh = True
    if ifr > i_ref:
        fresh = b * (L - tree.best(i_ref + 1, ifr, b)) > FRESH_TICKS * TICK
    i_end = _i_at(ts, t_break + RECLAIM_S)
    ir = tree.first_beyond(ib + 1, i_end, -b, L - b * RECLAIM_TICKS * TICK)
    if ir is not None:
        # FAILED: back through, and the flow turns within 20 s
        k = bisect.bisect_left(gt, ts[ir])
        g = None
        while k < len(grid) and grid[k]['t'] <= ts[ir] + CONFIRM_S:
            x = grid[k]
            if x.get('D') and _sgn(x['D']) == -b and \
                    x.get('z_delta_s') is not None and \
                    x['z_delta_s'] >= FLIP_Z:
                g = x
                break
            k += 1
        if g is None:
            return None
        kind, d, flip_z = 'FAILED', -b, g['z_delta_s']
        extreme = tree.best(ib, ir, b)
        trap_side, stop_ref = b, extreme
    else:
        # HELD: still beyond after 120 s, net flow with the break
        if ts[-1] < t_break + HOLD_S:
            return None                    # the run ended first
        k = bisect.bisect_left(gt, t_break + HOLD_S)
        if k >= len(grid) or grid[k]['t'] > t_break + HOLD_S + CONFIRM_S:
            return None
        g = grid[k]
        k0 = bisect.bisect_left(gt, t_break)
        if sum(b * (x.get('D') or 0.0) for x in grid[k0:k + 1]) <= 0:
            return None
        kind, d, extreme = 'HELD', b, None
        flip_z = g['z_delta_s'] if (g.get('D') and _sgn(g['D']) == b) \
            else None
        trap_side, stop_ref = -b, L
    t_entry = g['t']
    sod = RUN.sod_seconds(t_entry)
    if not ENTRY_FROM <= sod < ENTRY_TO:
        return None
    i0 = _i_at(ts, t_entry)
    p0 = ps[i0]
    stop = min(STOP_MAX, max(STOP_MIN,
                             d * (p0 - stop_ref) / TICK + STOP_BUFFER))
    # TRAPPED: aggressive contracts of the side now caught, break to entry
    k0 = bisect.bisect_left(gt, t_break)
    k1 = bisect.bisect_right(gt, t_entry)
    trapped = sum(max(0.0, trap_side * (x.get('D') or 0.0))
                  for x in grid[k0:k1])
    # ABSORPTION: the caught side pushed hard at the level and got nowhere
    ka = bisect.bisect_left(gt, t_break - ABSORB_LOOKBACK_S)
    absorbed = any(
        x.get('mid') is not None and x.get('D') and
        x.get('z_delta_s') is not None and x.get('resp') is not None and
        abs(x['mid'] - L) <= ABSORB_NEAR_TICKS * TICK + 1e-9 and
        _sgn(x['D']) == trap_side and
        x['z_delta_s'] >= ABSORB_Z and abs(x['resp']) <= ABS_RESP
        for x in grid[ka:k1])
    return dict(t_on=t_on, level=L, type=typ, kind=kind, b=b, direction=d,
                t_break=t_break, t_entry=t_entry, sod=sod, i0=i0, p0=p0,
                extreme=extreme, stop_ticks=stop, trapped=trapped,
                absorbed=absorbed, flip_z=flip_z, fresh=fresh,
                daily=[x for x in (g.get('w7_lv') or ()) if x is not None])


# ---------------------------------------------------------------------
# registration 3: the grade
# ---------------------------------------------------------------------
def confluence(ev, prior_values):
    """Within 8 ticks of a daily level known at the entry or of the
    previous session's value area (the level itself excluded)."""
    near = list(ev['daily'])
    near += [px for _t, px, ty in prior_values
             if not (ty == ev['type'] and px == ev['level'])]
    return any(abs(ev['level'] - x) <= CONFLUENCE_TICKS * TICK + 1e-9
               for x in near)


def points(ev, trapped_cut):
    return sum((
        trapped_cut is not None and ev['trapped'] >= trapped_cut,
        bool(ev['absorbed']),
        ev['flip_z'] is not None and ev['flip_z'] >= STRONG_Z,
        bool(ev['fresh']),
        bool(ev['confluence'])))


# ---------------------------------------------------------------------
# registration 4: exits
# ---------------------------------------------------------------------
def _limit_t(ev):
    return min(ev['t_entry'] + MAX_HOLD_S,
               ev['t_entry'] + (FLAT_AT - ev['sod']))


def bracket(path, ev, stop, target):
    """A fixed stop and target from the entry: (outcome, ticks, exit t);
    the first path point at or beyond either decides."""
    ts, ps, tree = path
    i0, p0, d = ev['i0'], ev['p0'], ev['direction']
    il = _i_at(ts, _limit_t(ev))
    js = tree.first_beyond(i0 + 1, il, -d, p0 - d * stop * TICK)
    jt = None if target is None else \
        tree.first_beyond(i0 + 1, il, d, p0 + d * target * TICK)
    if js is not None and (jt is None or js <= jt):
        return 'STOP', -stop, ts[js]
    if jt is not None:
        return 'TARGET', target, ts[jt]
    return 'TIME', d * (ps[il] - p0) / TICK, ts[il]


def tape_exit(path, ev, grid, gt, big_d, t_until):
    """The first grid tick after the entry, up to t_until, where at
    least 2 of the 4 tape signs say the move is dying: (t, mid) or None.
        FADE      the 60 s flow is no longer with the trade
        AGAINST   the other side hit at least the DEV 90th percentile
        ABSORBED  our side hit that hard and price moved a tick or less
        STALL     120 s or more since the trade's best price"""
    ts, ps, tree = path
    d = ev['direction']
    best, t_best, i_prev = d * ev['p0'], ev['t_entry'], ev['i0']
    k = bisect.bisect_right(gt, ev['t_entry'])
    while k < len(grid) and grid[k]['t'] <= t_until:
        g = grid[k]
        k += 1
        ig = _i_at(ts, g['t'])
        if ig > i_prev:
            px = tree.best(i_prev + 1, ig, d)
            if d * px > best:
                best = d * px
                t_best = ts[tree.first_beyond(i_prev + 1, ig, d, px)]
            i_prev = ig
        D, D60, r, mid = g.get('D'), g.get('D60'), g.get('resp'), g.get('mid')
        if mid is None:
            continue
        signs = sum((
            D60 is not None and d * D60 <= 0,
            D is not None and big_d is not None and -d * D >= big_d,
            D is not None and big_d is not None and r is not None and
            d * D >= big_d and d * r <= ABS_RESP,
            g['t'] - t_best >= STALL_S))
        if signs >= TAPE_NEED:
            return g['t'], mid
    return None


def next_target(ev, levels_ahead, day_range):
    """E1's target in ticks: the nearest level beyond the entry if it is
    at least 1.5 x the stop away; None (no E1 trade) when a nearer level
    is in the way; max(0.2 x the daily range, 1.5 x stop) with no level."""
    d, p0, stop = ev['direction'], ev['p0'], ev['stop_ticks']
    ahead = sorted(d * (px - p0) / TICK for px in levels_ahead
                   if d * (px - p0) > 0)
    if ahead:
        return ahead[0] if ahead[0] >= NEXT_LEVEL_MIN_R * stop else None
    vol = VOL_TARGET_RANGE * day_range / TICK if day_range else 0.0
    return max(vol, NEXT_LEVEL_MIN_R * stop)


def exits(ev, path, grid, gt, big_d):
    """{exit: (outcome, ticks, risk ticks, exit t)}; E1 and E3 are
    absent when E1 has no target."""
    ts, ps, tree = path
    stop, d, p0 = ev['stop_ticks'], ev['direction'], ev['p0']
    il = _i_at(ts, _limit_t(ev))
    js = tree.first_beyond(ev['i0'] + 1, il, -d, p0 - d * stop * TICK)
    t_stop = ts[js] if js is not None else None
    tape = tape_exit(path, ev, grid, gt, big_d,
                     t_stop if t_stop is not None else ts[il])
    if tape is not None and (t_stop is None or tape[0] < t_stop):
        e2 = ('TAPE', d * (tape[1] - p0) / TICK, stop, tape[0])
    elif t_stop is not None:
        e2 = ('STOP', -stop, stop, t_stop)
    else:
        e2 = ('TIME', d * (ps[il] - p0) / TICK, stop, ts[il])
    out = dict(E2=e2)
    if ev['target_e1'] is not None:
        o, v, tx = bracket(path, ev, stop, ev['target_e1'])
        out['E1'] = (o, v, stop, tx)
        out['E3'] = ('%s/%s' % (o, e2[0]), 0.5 * v + 0.5 * e2[1], stop,
                     max(tx, e2[3]))
    o, v, tx = bracket(path, ev, BASE_STOP, BASE_TARGET)
    out['E4'] = (o, v, BASE_STOP, tx)
    return out


# ---------------------------------------------------------------------
# the whole read -> events with exits
# ---------------------------------------------------------------------
def build(r, cuts=None):
    """Every event of the read with its grade and exits. DEV computes
    the two cuts (trapped median per instrument and kind, the 90th
    percentile of |10 s delta| per instrument) from the same read;
    evaluation uses the frozen ones. Returns (events, cuts)."""
    by_ses = collections.defaultdict(list)
    for g in r.grid:
        by_ses[(g['instrument'], g['session'])].append(g)
    for v in by_ses.values():
        v.sort(key=lambda g: g['t'])
    sessions = collections.defaultdict(list)
    for inst, ses in sorted(by_ses):
        sessions[inst].append(ses)
    if cuts:
        big_d = dict(cuts['big_d'])
    else:
        big_d = {}
        for inst, ss in sessions.items():
            ds = sorted(abs(g['D']) for s in ss for g in by_ses[(inst, s)]
                        if g.get('D'))
            big_d[inst] = ds[int(BIG_D_Q * (len(ds) - 1))] if ds else None
    events = []
    for inst in sorted(sessions):
        ss = sessions[inst]
        ranges = []
        for si, ses in enumerate(ss):
            day = by_ses[(inst, ses)]
            prev = by_ses[(inst, ss[si - 1])] if si else []
            recent = ranges[-RANGE_SESSIONS:]
            day_range = sum(recent) / len(recent) \
                if len(recent) >= RANGE_MIN_SESSIONS else None
            prior_values = value_levels(prev, day[0]['t']) if prev else []
            runs = collections.OrderedDict()
            for g in day:
                runs.setdefault(g['run'], []).append(g)
            for run, grid in runs.items():
                raw = r.series.get((inst, run))
                if not raw or not len(raw[0]):
                    continue
                ts, ps = BM.compress(*raw)
                path = (ts, ps, Tree(list(ps)))
                gt = [g['t'] for g in grid]
                lv = merge_levels(swing_levels(ts, ps) +
                                  absorption_levels(grid) +
                                  [x for x in prior_values if x[0] <= ts[-1]])
                for level in lv:
                    ev = detect(level, path, grid, gt)
                    if ev is None:
                        continue
                    ev.update(instrument=inst, session=ses, run=run,
                              day_range=day_range)
                    ev['confluence'] = confluence(ev, prior_values)
                    ahead = [px for t_on, px, _ty in lv
                             if t_on <= ev['t_entry'] and px != ev['level']]
                    ev['target_e1'] = next_target(ev, ahead + ev['daily'],
                                                  day_range)
                    ev['exits'] = exits(ev, path, grid, gt, big_d.get(inst))
                    events.append(ev)
            mids = [g['mid'] for g in day if g.get('mid') is not None]
            if mids:
                ranges.append(max(mids) - min(mids))
    if cuts:
        tcut = {tuple(k.split('|')): v for k, v in cuts['trapped'].items()}
    else:
        tcut = {}
        by = collections.defaultdict(list)
        for ev in events:
            by[(ev['instrument'], ev['kind'])].append(ev['trapped'])
        for k, v in by.items():
            v.sort()
            tcut[k] = v[len(v) // 2]
    for ev in events:
        ev['points'] = points(ev, tcut.get((ev['instrument'], ev['kind'])))
        ev['grade'] = grade_of(ev['points'])
    return events, dict(big_d=big_d, trapped={'%s|%s' % k: v
                                              for k, v in tcut.items()})


# ---------------------------------------------------------------------
# registration 5: statistics
# ---------------------------------------------------------------------
def one_at_a_time(rows):
    """rows: [(event, exit)] of one instrument; an event whose entry
    comes before the taken trade's exit is skipped."""
    taken, busy = [], None
    for ev, x in sorted(rows, key=lambda r: r[0]['t_entry']):
        if busy is not None and ev['t_entry'] < busy:
            continue
        taken.append((ev, x))
        busy = x[3]
    return taken


def net_r(ev, x):
    """(net R, net points) of one exit after costs: commission and the
    spread on every trade, a tick of slip on a stop; the hybrid's two
    halves are charged half each."""
    legs = x[0].split('/')
    c = sum(CO.cost_ticks(ev['instrument'],
                          'STOP' if o == 'STOP' else 'TARGET')
            for o in legs) / len(legs)
    return (x[1] - c) / x[2], (x[1] - c) * TICK


def test_mean(rows):
    if not rows:
        return dict(n=0, sessions=0)
    vals = [(ev['session'],) + net_r(ev, x) + (x[0],) for ev, x in rows]
    st = DI.cluster_stats([(s, r, 0.0, r) for s, r, _p, _o in vals])
    n = len(vals)
    wins = sum(1 for _s, r, _p, _o in vals if r > 0)
    return dict(n=n, sessions=st['sessions'], mean_net_r=st['lift'],
                t=st.get('t'), p=st.get('p'), ci95=st.get('ci95'),
                win_rate=round(wins / n, 3),
                net_points=round(sum(p for _s, _r, p, _o in vals) / n, 3),
                outcomes=dict(collections.Counter(o for *_x, o in vals)))


def test_slope(rows):
    """Session-clustered least-squares slope of net R on the grade
    points (0-5)."""
    xs = [(ev['session'], float(ev['points']), net_r(ev, x)[0])
          for ev, x in rows]
    n = len(xs)
    out = dict(n=n, sessions=len({s for s, _x, _y in xs}))
    if n < 3:
        return out
    mx = sum(x for _s, x, _y in xs) / n
    my = sum(y for _s, _x, y in xs) / n
    sxx = sum((x - mx) ** 2 for _s, x, _y in xs)
    if sxx <= 0:
        return out
    beta = sum((x - mx) * (y - my) for _s, x, y in xs) / sxx
    infl = collections.defaultdict(float)
    for s, x, y in xs:
        infl[s] += (x - mx) * (y - my - beta * (x - mx)) / sxx
    G = len(infl)
    out['slope_r_per_point'] = round(beta, 4)
    if G >= 2:
        se = math.sqrt(G / (G - 1.0) * sum(v * v for v in infl.values()))
        if se > 1e-9:
            t = beta / se
            tc = DI.t_crit(G - 1)
            out.update(t=round(t, 3), p=DI.t_p_two_sided(t, G - 1),
                       ci95=(round(beta - tc * se, 4),
                             round(beta + tc * se, 4)))
    return out


def tests(events, keep=None):
    """The nine tests per instrument (NQ carries the verdict), Holm over
    the nine; plus every grade's E4 average, described, not tested."""
    ev = [e for e in events if keep is None or keep(e['session'])]
    out = {}
    for inst in sorted({e['instrument'] for e in ev}):
        mine = [e for e in ev if e['instrument'] == inst]
        rows = []
        for kind in KINDS:
            for ex in EXITS:
                sel = [(e, e['exits'][ex]) for e in mine
                       if e['kind'] == kind and e['points'] >= MIN_POINTS
                       and ex in e['exits']]
                st = test_mean(one_at_a_time(sel))
                st.update(test='%s%s' % (kind[0], ex[1]), kind=kind, exit=ex)
                rows.append(st)
        st = test_slope([(e, e['exits']['E4']) for e in mine])
        st.update(test='G', kind='ALL', exit='E4')
        rows.append(st)
        rej = BM.holm([x.get('p') for x in rows], HOLM_ALPHA)
        for x, rj in zip(rows, rej):
            eff = x.get('mean_net_r', x.get('slope_r_per_point'))
            if x.get('n', 0) < MIN_EVENTS:
                x['status'] = 'NOT TESTED'
            elif rj and eff is not None and eff > 0 and x.get('ci95') and \
                    x['ci95'][0] > 0:
                x['status'] = 'PROMISING'
            else:
                x['status'] = 'NO SIGNAL'
        out[inst] = dict(tests=rows, by_grade=_by_grade(mine))
    return out


def _by_grade(evs):
    out = {}
    for kind in KINDS:
        for g in ('A+', 'A', 'B', 'SKIP'):
            rs = [net_r(e, e['exits']['E4'])[0] for e in evs
                  if e['grade'] == g and e['kind'] == kind]
            if rs:
                out['%s %s' % (kind, g)] = dict(
                    n=len(rs), mean_net_r_e4=round(sum(rs) / len(rs), 4))
    return out


# ---------------------------------------------------------------------
# modes
# ---------------------------------------------------------------------
_SLIM = ('instrument', 'session', 'kind', 'type', 'level', 'direction',
         't_entry', 'p0', 'stop_ticks', 'target_e1', 'trapped', 'absorbed',
         'flip_z', 'fresh', 'confluence', 'points', 'grade', 'exits')


def run_dev(capture_dir, max_sessions=None):
    r = FlowRunner(capture_dir, max_sessions=max_sessions)
    led = r.run()
    events, frozen = build(r)
    frozen.update(wave7=W7_VERSION, registration=REGISTRATION)
    rep = dict(wave7=W7_VERSION, registration=REGISTRATION, mode='dev',
               note='DEV sessions were seen before this registration: '
                    'these numbers describe, they do not test',
               runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               events=dict(sorted(collections.Counter(
                   '%s %s %s' % (e['instrument'], e['kind'], e['grade'])
                   for e in events).items())),
               frozen=frozen, results=tests(events),
               event_list=[dict((k, e[k]) for k in _SLIM) for e in events])
    return rep, frozen, r


def run_evaluate(capture_dir, frozen, unblind=False, holdout=False,
                 max_sessions=None):
    if unblind and holdout:
        raise ValueError('--unblind and --holdout are separate reads')
    r = FlowRunner(capture_dir, unblind=unblind, holdout=holdout,
                   max_sessions=max_sessions)
    led = r.run()
    events, _c = build(r, frozen)
    if holdout:
        keep = lambda s: s < HOLDOUT_BEFORE      # noqa: E731
        which = 'REPLAY HOLDOUT (sessions before %s)' % HOLDOUT_BEFORE
    elif unblind:
        keep = lambda s: s > DEV_END             # noqa: E731
        which = 'validation (> %s)' % DEV_END
    else:
        keep = lambda s: s <= DEV_END            # noqa: E731
        which = 'DEV (<= %s), a reproduction check' % DEV_END
    res = tests(events, keep)
    if not (unblind or holdout):
        for v in res.values():
            for x in v['tests']:
                x['status'] += ' (DEV reproduction, not a verdict)'
    rep = dict(wave7=W7_VERSION, registration=REGISTRATION,
               mode='evaluate', evaluated_on=which, unblind=unblind,
               holdout=holdout, runner=led['runner'],
               sessions_inspected=sorted(led['sessions']),
               sessions_refused=list(r.refused_sessions),
               sessions_evaluated=sorted({e['session'] for e in events
                                          if keep(e['session'])}),
               frozen=frozen, results=res)
    return rep, r


def text(rep):
    lines = ['%s  %s  %s' % (rep['wave7'], rep['mode'],
                             rep.get('evaluated_on', '')),
             'sessions read: %s' % ', '.join(rep['sessions_inspected']),
             'sessions REFUSED: %s' % (', '.join(rep['sessions_refused'])
                                       or '-')]
    if rep.get('note'):
        lines.append('NOTE: ' + rep['note'])
    if rep.get('events'):
        lines.append('events: ' + ', '.join('%s %d' % kv for kv in
                                            rep['events'].items()))
    lines.append('E1 next level (>= 1.5 x stop, no cap)  E2 tape exit  '
                 'E3 half and half  E4 the original 25/15')
    lines.append('net R after costs, one position at a time, grade A or '
                 'A+ only (G: every event, E4)')
    for inst, v in rep['results'].items():
        lines.append('')
        lines.append('%-4s %-5s %-6s %-4s %5s %4s %6s %8s %8s %7s %8s  %s' % (
            inst, 'test', 'kind', 'exit', 'n', 'ses', 'win', 'net R',
            'net pts', 't', 'p', 'status'))
        for x in v['tests']:
            eff = x.get('mean_net_r', x.get('slope_r_per_point'))
            lines.append('     %-5s %-6s %-4s %5s %4s %6s %8s %8s %7s %8s  %s'
                         % (x['test'], x['kind'], x['exit'], x.get('n', 0),
                            x.get('sessions', 0),
                            '-' if x.get('win_rate') is None else
                            '%.0f%%' % (100 * x['win_rate']),
                            '-' if eff is None else '%+.3f' % eff,
                            '-' if x.get('net_points') is None else
                            '%+.2f' % x['net_points'],
                            '-' if x.get('t') is None else '%.2f' % x['t'],
                            '-' if x.get('p') is None else '%.4f' % x['p'],
                            x['status']))
        lines.append('  by grade (E4, every event, described): ' + (', '.join(
            '%s n=%d R=%+.3f' % (k, g['n'], g['mean_net_r_e4'])
            for k, g in v['by_grade'].items()) or '-'))
    lines.append('')
    lines.append('Mid-to-mid paths with costs charged; not P&L. No order was '
                 'placed.')
    return '\n'.join(lines)


def record_holdout_read(rep, path):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            old = json.load(open(path))
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=W7_VERSION, sessions=rep['sessions_inspected']))
    old['rule'] = ('Replay holdout sessions are read once by each '
                   'registered wave; a later read of NEW rules on them is '
                   'not a fresh test.')
    json.dump(old, open(path, 'w'), indent=1)
    return len(old['reads'])


def record_exposure(rep, path):
    """Every session an --unblind read inspected becomes EXPOSED_PILOT_DEV
    for good (the ledger the earlier waves keep)."""
    old = []
    if os.path.exists(path):
        try:
            old = json.load(open(path)).get('exposed_days', [])
        except Exception:
            old = []
    by = {d['session']: d for d in old}
    for s in rep['sessions_inspected']:
        cur = by.get(s)
        if cur is None:
            by[s] = dict(session=s, label=PI.EXPOSURE_LABEL,
                         exposed_by=W7_VERSION, bulk_csv_present=None)
        elif cur.get('label') != PI.EXPOSURE_LABEL:
            cur.update(label=PI.EXPOSURE_LABEL, exposed_by=W7_VERSION,
                       previously_blind=True)
        by[s].setdefault('also_exposed_by', [])
        if W7_VERSION not in by[s]['also_exposed_by']:
            by[s]['also_exposed_by'].append(W7_VERSION)
    days = sorted(by.values(), key=lambda d: d['session'])
    json.dump(dict(label=PI.EXPOSURE_LABEL, blind_label=PI.BLIND_LABEL,
                   rule='EXPOSED days may remain in later DEV/training where '
                        'the governing protocol permits; they can never '
                        'become untouched prospective validation. BLIND '
                        'days had fire counts read and markouts withheld; '
                        'they remain valid validation until explicitly '
                        'unblinded.',
                   exposed_days=days), open(path, 'w'), indent=1)
    return len(days)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]

    def arg(k):
        return argv[argv.index(k) + 1] if k in argv else None
    out = arg('--out')
    ms = int(arg('--max-sessions')) if arg('--max-sessions') else None
    unblind, holdout = '--unblind' in argv, '--holdout' in argv
    ev = arg('--evaluate')
    if (unblind or holdout) and not ev:
        print('REFUSED: --unblind and --holdout are only for --evaluate with '
              'the frozen file. A plain run reads DEV sessions only.')
        return 2
    if unblind and holdout:
        print('REFUSED: --unblind and --holdout are separate reads.')
        return 2
    try:
        if ev:
            try:
                frozen = json.load(open(ev))
                if not (isinstance(frozen.get('trapped'), dict) and
                        isinstance(frozen.get('big_d'), dict)):
                    raise ValueError
            except (OSError, ValueError, AttributeError):
                print('STOPPED: %s is not a wave-seven frozen file (the '
                      '--frozen-out of the DEV run)' % ev)
                return 2
            if unblind or holdout:
                print('*** %s: this read scores the nine registered tests '
                      'once. ***\n' % ('UNBLIND' if unblind else 'HOLDOUT'))
            rep, _r = run_evaluate(d, frozen, unblind, holdout, ms)
        else:
            rep, frozen, _r = run_dev(d, ms)
            fo = arg('--frozen-out')
            if fo:
                json.dump(frozen, open(fo, 'w'), indent=1)
                print('frozen cuts -> %s' % fo)
        print(text(rep))
    except (RUN.CaptureUnavailable, RUN.NoCaptureData) as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nwave-seven report -> %s' % out)
    here = os.path.dirname(os.path.abspath(__file__))
    if ev and holdout:
        n = record_holdout_read(rep, os.path.join(here, HOLDOUT_LEDGER))
        print('replay holdout read recorded (%d read(s))' % n)
    if ev and unblind:
        n = record_exposure(rep, os.path.join(here, EXPOSURE_LEDGER))
        print('exposure ledger -> %d days' % n)
    return 0


if __name__ == '__main__':
    sys.exit(main())
