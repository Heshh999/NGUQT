#!/usr/bin/env python3
"""mrofyt_speed29.py - MROF-YT-W29-SPEED-1.0

MROF_YT_WAVE29_SPEED_REGISTRATION.md turned into running code: the
fastest trade a retail account can win. Does anything on the recorded
tape forecast NQ well enough, between ten seconds and ten minutes, to
pay for a retail account's costs and delay?

    the panel     one row every 5 seconds, 08:00 to 16:15 New York, for
                  NQ and MNQ, from the quote, trade and quality files
                  (the depth files are not opened)
    the forecast  a linear forecast from 48 inputs known at the moment,
                  walked forward by session, for 10 seconds to 10 minutes
    three ways    T take, M join the best price, D rest deep; each
                  filled less easily than in a real book, each paying
                  its commission, the spread and a delay of 0.5 s (1.0 s
                  as the stress)
    the map       reported, never judged: what each speed moves, costs
                  and can be forecast
    the verdict   a way qualifies at 60 seconds or more, 200 trades, a
                  session t of 3.0, both halves and the 1.0 s delay

Only sessions from 2026-09-01 to 2026-11-13 that the exposure ledger
marks EXPOSED_PILOT_DEV are read; any other session is listed and never
opened. Read-only; no order is placed.

    python mrofyt_speed29.py "<capture>" --out w29.json
        reads the tape (about an hour or two), saves the panel beside
        the report (w29_panel.csv.gz) before anything is computed, then
        makes the report; a way that qualifies is frozen (w29_frozen.json)
    python mrofyt_speed29.py --from-panel w29_panel.csv.gz --out w29.json
        the report again, without reading the tape
    python mrofyt_speed29.py "<capture>" --confirm w29_frozen.json
        --out w29_confirm.json
        section 8, once: the frozen ways on the sessions recorded from
        2026-11-16 (the frozen file must be the one the study last
        wrote; the panel is saved as w29_confirm_panel.csv.gz)
    python mrofyt_speed29.py --from-panel w29_confirm_panel.csv.gz
        --confirm w29_frozen.json --out w29_confirm.json
        the confirmation's report again from its saved panel; only
        after the confirmation was made, with the same frozen file
"""
import array
import collections
import csv
import datetime
import gzip
import hashlib
import heapq
import json
import math
import os
import random
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import mles_v12_adapter as AD        # noqa: E402
import mrofyt_confirm25 as W25       # noqa: E402
import mrofyt_context as CX          # noqa: E402
import mrofyt_pilot as PI            # noqa: E402
import mrofyt_runner as RUN          # noqa: E402

W29_VERSION = 'MROF-YT-W29-SPEED-1.0'
REGISTRATION = 'MROF_YT_WAVE29_SPEED_REGISTRATION.md'
EXPOSURE_LEDGER = 'MROF_EXPOSED_PILOT_DEV_DAYS.json'
READS_LEDGER = 'MROF_W29_SPEED_READS.json'
PANEL_KIND = 'MROF-YT-W29 panel'

# registration 1: the data
INSTRUMENTS = ('NQ', 'MNQ')
FIRST_SESSION, LAST_SESSION = '20260901', '20261113'
FRESH_FROM = '20261116'
TICK = 0.25
STEP = 5                               # seconds between rows
PANEL_FROM, PANEL_TO = 8 * 3600, 16 * 3600 + 900       # New York
ROWS = (PANEL_TO - PANEL_FROM) // STEP + 1             # 5,941
MAX_QUOTE_AGE = 10.0
WARMUP_S = 60.0                        # of tape read before the panel
TAIL_S = 12.0                          # after its last row

# registration 2: costs and fills
COMMISSION = 0.25                      # points a round trip, NQ
COMMISSION_MICRO = 0.75                # the same trades as MNQ
DELAY, DELAY_STRESS = 0.5, 1.0
_M_DELAY, _M_STRESS = int(round(2 * DELAY)), int(round(2 * DELAY_STRESS))
#                                    the two delays, in half-second marks
JOIN_LIFE, JOIN_GRACE = 10.0, 0.5

COLS = ('v', 'bid', 'ask', 'bs', 'az', 'b05', 'a05', 'b10', 'a10', 'fb',
        'fs', 'lo', 'hi', 'lob', 'hia', 'ofi', 'buy', 'sell', 'vol', 'nb',
        'ns', 'qi', 'spr', 'qt', 's1', 's2', 'sq', 'sqn', 'pv', 'ofi1',
        'tfi1', 'gap')
COLS_MICRO = ('v', 'bid', 'ask', 'bs', 'az', 'ofi', 'buy', 'sell', 'vol',
              'nb', 'ns', 'qi', 'qt', 'gap')
_ACC = ('ofi', 'buy', 'sell', 'vol', 'nb', 'ns', 'qi', 'spr', 'qt', 's1',
        's2', 'sq', 'sqn', 'pv', 'gap')


class SpeedDataError(Exception):
    """A stop: nothing was computed."""


# ---------------------------------------------------------------------
# registration 1: the clock
# ---------------------------------------------------------------------
def panel_start(session):
    """The moment of 08:00:00 New York on the session's date."""
    day0 = CX._day_epoch(session)
    midnight = day0 - CX.et_offset(day0 + 14 * 3600, int(session[:4]))
    return midnight + PANEL_FROM


def row_time(session, g):
    return panel_start(session) + STEP * g


def sod_of_row(g):
    """New York seconds of day of row g."""
    return PANEL_FROM + STEP * g


def row_of_sod(sod):
    return (sod - PANEL_FROM) // STEP


def _iso(t):
    return datetime.datetime.fromtimestamp(
        int(t), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%S')


# ---------------------------------------------------------------------
# registration 1-2: one contract of one session becomes rows
# ---------------------------------------------------------------------
class Book(object):
    """The panel's rows of one contract in one session, built from its
    quotes and trades in the order the computer received them. With
    `execution`, also the quotes half a second and a second after each
    row and the two passive orders of registration 2."""

    def __init__(self, session, execution):
        self.session = session
        self.exe = execution
        self.t0 = panel_start(session)
        self.col = {}
        for name in (COLS if execution else COLS_MICRO):
            self.col[name] = array.array('d', [0.0]) * ROWS
        if execution:
            for name in ('fb', 'fs'):
                self.col[name] = array.array('d', [-1.0]) * ROWS
        self.q = None                # (t, bid, bid size, ask, ask size)
        self.pq = None               # the quote before, for the imbalance
        self.j = 0                   # next half-second mark
        self.tb = self.t0 - STEP     # its time: t0 - STEP + j / 2
        self.ti = None               # the integrals run to here
        self.acc = dict.fromkeys(_ACC, 0.0)
        self.sec = [0.0, 0.0]        # imbalance, signed volume this second
        self.mid_s = None            # the mid at the last whole second
        self.joins = []              # resting join orders
        self.win = None              # the deep window being watched
        self.volume = 0.0            # in the panel's hours
        self.broken = True           # nothing carries into a run
        self.done = False

    # ---- the quote in force ------------------------------------------
    def _in_force(self, t):
        q = self.q
        return q is not None and t - q[0] <= MAX_QUOTE_AGE

    def _integrate(self, t):
        ti, q = self.ti, self.q
        self.ti = t
        if q is None or ti is None:
            return
        end = q[0] + MAX_QUOTE_AGE
        if end < t:
            t = end
        dt = t - ti
        if dt <= 0.0:
            return
        acc = self.acc
        acc['qt'] += dt
        tot = q[2] + q[4]
        if tot > 0:
            acc['qi'] += dt * (q[2] - q[4]) / tot
        sp = (q[3] - q[1]) / TICK
        acc['spr'] += dt * sp
        if sp < 1.5:
            acc['s1'] += dt
        elif sp < 2.5:
            acc['s2'] += dt

    # ---- the half-second marks ---------------------------------------
    def _advance(self, t):
        while self.tb <= t and not self.done:
            self._mark()

    def _mark(self):
        tb, j = self.tb, self.j
        self._integrate(tb)
        ok = self._in_force(tb)
        q = self.q
        m = j % (2 * STEP)
        g = j // (2 * STEP) - 1                  # the row at or before tb
        col = self.col
        if j % 2 == 0:                           # a whole second
            mid = 0.5 * (q[1] + q[3]) if ok else None
            if mid is not None and self.mid_s is not None:
                d = mid - self.mid_s
                self.acc['sq'] += d * d
                self.acc['sqn'] += 1.0
            self.mid_s = mid
            if m == 0 and 0 <= g < ROWS:         # a row
                if ok:
                    col['v'][g] = 1.0
                    col['bid'][g], col['bs'][g] = q[1], q[2]
                    col['ask'][g], col['az'][g] = q[3], q[4]
                acc = self.acc
                for k in (_ACC if self.exe else COLS_MICRO[5:]):
                    col[k][g] = acc[k]
                if self.exe:
                    col['ofi1'][g], col['tfi1'][g] = self.sec
            if m == 0:
                self.acc = dict.fromkeys(_ACC, 0.0)
            self.sec = [0.0, 0.0]
        if self.exe:
            if m == _M_DELAY:                    # half a second after a row
                self._close_window()
                if 0 <= g < ROWS:
                    if ok:
                        col['b05'][g], col['a05'][g] = q[1], q[3]
                        self.joins.append(
                            [g, 1, q[1], q[2], 0.0, False, False, tb])
                        self.joins.append(
                            [g, -1, q[3], q[4], 0.0, False, False, tb])
                    # low and high trade, low bid, high ask, broken
                    self.win = [g, None, None, q[1] if ok else None,
                                q[3] if ok else None, not ok]
            elif m == _M_STRESS and 0 <= g < ROWS and ok:    # a second on
                col['b10'][g], col['a10'][g] = q[1], q[3]
            if self.joins:
                life = JOIN_LIFE + JOIN_GRACE
                self.joins = [o for o in self.joins if tb - o[7] <= life]
        self.j = j + 1
        self.tb = self.t0 - STEP + 0.5 * self.j
        if g > ROWS + 2:
            self.done = True

    def _close_window(self):
        w = self.win
        self.win = None
        if w is None or w[5]:
            return
        g, col = w[0], self.col
        if w[1] is not None:
            col['lo'][g], col['hi'][g] = w[1], w[2]
        if w[3] is not None:
            col['lob'][g], col['hia'][g] = w[3], w[4]

    # ---- the tape ----------------------------------------------------
    def brk(self, t):
        """The feed was interrupted, or a run begins: no quote is in
        force, nothing is resting, and the row says so."""
        self._advance(t)
        self._integrate(t)
        self.q = self.pq = None
        self.ti = None
        self.mid_s = None
        self.acc['gap'] = 1.0
        self.joins = []
        if self.win is not None:
            self.win[5] = True

    def quote(self, t, b, bs, a, az):
        if self.broken:
            self.broken = False
            self.brk(t)
        self._advance(t)
        self._integrate(t)
        pq = self.pq
        if pq is not None:
            e = 0.0
            if b >= pq[0]:
                e += bs
            if b <= pq[0]:
                e -= pq[1]
            if a <= pq[2]:
                e -= az
            if a >= pq[2]:
                e += pq[3]
            self.acc['ofi'] += e
            self.sec[0] += e
        self.pq = (b, bs, a, az)
        self.q = (t, b, bs, a, az)
        self.ti = t
        w = self.win
        if w is not None:
            if w[3] is None or b < w[3]:
                w[3] = b
            if w[4] is None or a > w[4]:
                w[4] = a
        if self.joins:
            for o in self.joins:
                if not o[6] and ((b < o[2]) if o[1] > 0 else (a > o[2])):
                    o[6] = True
                    if o[5]:
                        self._fill(o, t)
            if any(o[1] == 0 for o in self.joins):
                self.joins = [o for o in self.joins if o[1] != 0]

    def trade(self, t, px, sz, sign):
        if self.broken:
            self.broken = False
            self.brk(t)
        self._advance(t)
        acc = self.acc
        acc['vol'] += sz
        acc['pv'] += px * sz
        if sign > 0:
            acc['buy'] += sz
            acc['nb'] += 1.0
        elif sign < 0:
            acc['sell'] += sz
            acc['ns'] += 1.0
        self.sec[1] += sign * sz
        if 1 <= self.j <= 2 * STEP * (ROWS + 1):
            self.volume += sz
        w = self.win
        if w is not None:
            if w[1] is None or px < w[1]:
                w[1] = px
            if w[2] is None or px > w[2]:
                w[2] = px
        if self.joins:
            for o in self.joins:
                p = o[2]
                if o[1] > 0:                     # a buy resting at p
                    if px < p:
                        o[5] = True
                    elif px == p and sign <= 0:
                        o[4] += sz
                else:                            # a sell resting at p
                    if px > p:
                        o[5] = True
                    elif px == p and sign >= 0:
                        o[4] += sz
                if o[4] >= o[3] + 1.0 or (o[5] and o[6]):
                    self._fill(o, t)
            if any(o[1] == 0 for o in self.joins):
                self.joins = [o for o in self.joins if o[1] != 0]

    def _fill(self, o, t):
        ms = max(0.0, round((t - o[7]) * 1000.0))
        self.col['fb' if o[1] > 0 else 'fs'][o[0]] = ms
        o[1] = 0                                 # filled: taken off

    def finish(self):
        """After the session's last row of tape: the marks to the
        panel's end, so the rows after the last quote say what they
        are."""
        self._advance(self.t0 + STEP * (ROWS + 4))
        self._close_window()


# ---------------------------------------------------------------------
# the tape of one run, inside the panel's hours
# ---------------------------------------------------------------------
def window_events(paths, t_from, t_to, state=None):
    """The quote, trade and quality rows of a run received from t_from
    to t_to, in the recorder's own order, decoded by the adapter's own
    functions; a row that cannot be decoded raises the runner's
    CorruptStream. Rows before t_from are passed over by their time
    stamp's text without being decoded, and a file is left at its first
    row after t_to (state['cut'] then says the run went on). A stamp
    that is not in the recorder's own shape is decoded and compared by
    its value instead."""
    first, final = int(t_from), int(t_to + 1.0)      # whole seconds
    lo, hi = _iso(first), _iso(final)

    def rows(path, kind):
        names = AD.HEADERS[kind]
        n = len(names)
        at = names.index('tRecvUtc')
        k = 0
        with open(path, newline='') as fh:
            rdr = csv.reader(fh)
            try:
                head = next(rdr, None)
                if head is None:
                    raise ValueError('%s is empty' % path)
                AD.check_header(kind, head)
                for raw in rdr:
                    if not raw:
                        continue
                    if len(raw) != n:
                        raise ValueError('expected %d columns, got %d'
                                         % (n, len(raw)))
                    stamp = raw[at][:19]
                    plain = len(stamp) == 19 and stamp[10] == 'T' and \
                        stamp[4] == '-' and stamp[13] == ':' and \
                        raw[at][-1:] == 'Z'
                    if plain:                    # the recorder's own shape
                        if stamp < lo:
                            continue
                        if stamp > hi:
                            if state is not None:
                                state['cut'] = True
                            return
                    d = dict(zip(names, raw))
                    ev = AD._decorate(AD._common(d, kind, True), d, kind)
                    if not plain and ev['t_recv'] is not None:
                        sec = math.floor(ev['t_recv'])
                        if sec < first:
                            continue             # any other shape: by value
                        if sec > final:
                            if state is not None:
                                state['cut'] = True
                            return
                    k += 1
                    yield ev
            except ValueError as exc:
                msg = str(exc)
                for pre in (path + ': ', os.path.basename(path) + ': '):
                    if msg.startswith(pre):
                        msg = msg[len(pre):]
                        break
                raise RUN.CorruptStream(
                    '%s: %s (after %d decoded rows)'
                    % (os.path.basename(path), msg, k))

    return heapq.merge(*[rows(paths[k], k) for k in
                         ('quotes', 'trades', 'quality') if k in paths],
                       key=AD._seq_key)


class SpeedRunner(RUN.Runner):
    """The runner's discovery, its checks of each run's files and its
    handling of a damaged run, unchanged; the stream itself is read
    here, without the depth file and only in the panel's hours, into
    one Book per instrument, contract and session."""

    def __init__(self, capture_dir, allowed, progress=None):
        RUN.Runner.__init__(self, capture_dir, instruments=INSTRUMENTS)
        self.allowed = allowed
        self.progress = progress
        self.done = {}               # (instrument, session, contract)
        self.refused = set()
        self.outside = 0             # runs that end before 08:00
        self.ledger['wave29'] = dict(version=W29_VERSION)

    def plan(self):
        keep = []
        for inst, ses, runs in RUN.Runner.plan(self):
            if self.allowed(ses):
                keep.append((inst, ses, runs))
            else:
                self.refused.add(ses)    # listed, never opened
        if self.progress and keep:
            self.progress(
                '%d recordings of %d sessions to read; a line for each as '
                'it is finished' % (sum(len(r) for _i, _s, r in keep),
                                    len({s for _i, s, _r in keep})))
        return keep

    def _flush(self, st):
        for c, book in getattr(st, 'w29', {}).items():
            book.finish()
            self.done[(st.instrument, st.w29_session, c)] = book

    def finish(self):
        for st in self.states.values():
            self._flush(st)
            st.w29 = {}

    def _process_run(self, st, mp, man):
        man = dict(man)
        man.pop('depth', None)           # the depth file is not opened
        if getattr(st, 'w29_session', None) != st.session:
            self._flush(st)
            st.w29_session, st.w29 = st.session, {}
        st.w29_contract = CX.contract_of(
            str(man.get('contract') or ''), st.instrument) or \
            '%s CONT' % st.instrument
        t0 = panel_start(st.session)
        first = AD.iso_to_epoch(str(man.get('firstRecvUtc') or '')) \
            if man.get('firstRecvUtc') else None
        last = AD.iso_to_epoch(str(man.get('lastRecvUtc') or '')) \
            if man.get('lastRecvUtc') else None
        if (last is not None and last < t0 - STEP - WARMUP_S) or \
                (first is not None and first > t0 + STEP * ROWS + TAIL_S):
            self.outside += 1            # all of it outside the hours
            return
        began = time.time()
        RUN.Runner._process_run(self, st, mp, man)
        if self.progress:
            rec = self.ledger['runs'][-1]
            self.progress('%s %s %s: %s' % (
                st.session, st.w29_contract, rec.get('run_id'),
                'SKIPPED (%s)' % rec['skipped'] if rec.get('skipped')
                else '%d rows in %d s' % (rec.get('events', 0),
                                          round(time.time() - began))))

    def _stream_run(self, st, paths):
        book = st.w29.get(st.w29_contract)
        if book is None:
            book = st.w29[st.w29_contract] = Book(
                st.session, st.instrument == INSTRUMENTS[0])
        book.broken = True               # nothing carries into a run
        n = crossed = quotes = 0
        lat = self.lat[st.instrument]
        t_from = book.t0 - STEP - WARMUP_S
        t_to = book.t0 + STEP * (ROWS - 1) + TAIL_S
        last = None
        state = {}
        for e in window_events(paths, t_from, t_to, state):
            n += 1
            t = e['t_recv']
            if t is None:
                continue
            if last is not None and t < last:
                t = last                 # the marks never run backwards
            last = t
            k = e['stream']
            if k == 'QUALITY':
                if e['kind'] in ('DISCONNECT', 'RECONNECT'):
                    book.brk(t)
                continue
            if e['t_exch'] is not None:
                lat.add((t - e['t_exch']) * 1000.0)
            if k == 'QUOTE':
                quotes += 1
                b, a = e['bid_px'], e['ask_px']
                if b is None or a is None:
                    continue
                if b >= a:
                    crossed += 1
                    continue
                flags = e['flags']
                if 'DATA_SUPPRESSED' in flags or 'DISCONNECTED' in flags:
                    book.brk(t)          # the recorder's word: stale
                    continue
                book.quote(t, b, e['bid_sz'] or 0.0, a, e['ask_sz'] or 0.0)
            elif k == 'TRADE':
                px, sz = e['px'], e['sz']
                if px is None or sz is None:
                    continue
                inf = e['aggr_inf']
                book.trade(t, px, sz,
                           1 if inf == 'BUY' else (-1 if inf == 'SELL'
                                                   else 0))
        if last is not None and not state.get('cut'):
            book.brk(last)               # the run ended: an interruption
            book.broken = True
        return n, crossed, quotes


# ---------------------------------------------------------------------
# registration 1 and 7: the read, and the panel kept as a file
# ---------------------------------------------------------------------
def exposed_sessions(path):
    """The sessions the exposure ledger marks EXPOSED_PILOT_DEV."""
    try:
        with open(path) as fh:
            days = json.load(fh).get('exposed_days', [])
    except (OSError, ValueError):
        return set()
    return {d.get('session') for d in days
            if d.get('label') == PI.EXPOSURE_LABEL}


def _month(contract):
    return contract.split()[-1] if contract else None


def build_panel(done):
    """{session: dict(nq, mnq, cols, mcols)} from the runner's books:
    for each session NQ's contract with the most volume in the panel's
    hours, and MNQ's contract of the same month (None without one)."""
    by = collections.defaultdict(dict)
    for (inst, ses, c), book in done.items():
        by[ses].setdefault(inst, []).append((book.volume, c, book))
    out = collections.OrderedDict()
    for ses in sorted(by):
        nq = by[ses].get(INSTRUMENTS[0])
        if not nq:
            continue                     # a session of MNQ alone
        _v, c, book = max(nq, key=lambda x: (x[0], x[1]))
        if book.volume <= 0:
            continue                     # no trade in the panel's hours
        micro = [x for x in by[ses].get(INSTRUMENTS[1], [])
                 if _month(x[1]) == _month(c) and x[0] > 0]
        mb = max(micro, key=lambda x: (x[0], x[1])) if micro else None
        out[ses] = dict(nq=c, mnq=mb[1] if mb else None, cols=book.col,
                        mcols=mb[2].col if mb else None)
    return out


def read_capture(capture_dir, ledger=None, progress=None, fresh=False):
    """The panel of every session that may be read: the exposed
    sessions of 2026-09-01 to 2026-11-13, or with `fresh` (registration
    8) the sessions from 2026-11-16 that the ledger does not hold."""
    ledger = ledger or os.path.join(HERE, EXPOSURE_LEDGER)
    exposed = exposed_sessions(ledger)
    if not exposed:
        raise RUN.NoCaptureData(
            'the exposure ledger %s names no %s session, so it cannot be '
            'told which sessions may be read. Nothing was read.'
            % (os.path.basename(ledger), PI.EXPOSURE_LABEL))
    if fresh:
        def allowed(s):
            return s >= FRESH_FROM and s not in exposed
    else:
        def allowed(s):
            return FIRST_SESSION <= s <= LAST_SESSION and s in exposed
    r = SpeedRunner(capture_dir, allowed, progress)
    try:
        led = r.run()
    except RUN.NoCaptureData:
        if not r.refused:
            raise
        raise RUN.NoCaptureData(
            'the folder holds %d session(s), none of them %s. Nothing was '
            'read.' % (len(r.refused), 'from 2026-11-16 and unread' if fresh
                       else 'from 2026-09-01 to 2026-11-13 and marked %s in '
                       'the ledger' % PI.EXPOSURE_LABEL))
    r.finish()
    return dict(
        kind=PANEL_KIND, version=W29_VERSION, fresh=bool(fresh),
        sessions=build_panel(r.done), refused_unread=sorted(r.refused),
        runs=len(led['runs']), runs_outside_hours=r.outside,
        runs_skipped=[dict(x) for x in led['skipped_runs']],
        latency_ms=dict(led.get('latency_ms') or {}))


def _fmt(name, x):
    if name in ('bid', 'ask', 'b05', 'a05', 'b10', 'a10', 'lo', 'hi', 'lob',
                'hia'):
        return '%d' % round(x / TICK)
    if name in ('qi', 'spr', 'qt', 's1', 's2'):
        return '%d' % round(x * 1000.0)
    if name == 'sq':                     # squares of eighths of a point
        return '%d' % round(x * 64.0)
    if name == 'pv':
        return '%.2f' % x
    return '%d' % round(x)


def _unfmt(name, s):
    x = float(s)
    if name in ('bid', 'ask', 'b05', 'a05', 'b10', 'a10', 'lo', 'hi', 'lob',
                'hia'):
        return x * TICK
    if name in ('qi', 'spr', 'qt', 's1', 's2'):
        return x / 1000.0
    if name == 'sq':
        return x / 64.0
    return x


def write_panel(panel, path):
    """The panel as one compressed text file: a line of facts, a line
    of column names, then a row a line. Prices, sizes, counts and the
    squared moves are kept exactly; the five time integrals to the
    millisecond. The study is always made from the file as read back,
    so the file alone gives the same report again."""
    meta = dict((k, v) for k, v in panel.items() if k != 'sessions')
    meta['contracts'] = {s: [d['nq'], d['mnq']]
                         for s, d in panel['sessions'].items()}
    head = ['session', 'g'] + list(COLS) + ['m_' + c for c in COLS_MICRO]
    blank = ['0'] * len(COLS_MICRO)
    tmp = path + '.tmp'
    with gzip.open(tmp, 'wt', encoding='ascii', newline='\n') as fh:
        fh.write('# ' + json.dumps(meta, sort_keys=True) + '\n')
        fh.write(','.join(head) + '\n')
        for ses, d in panel['sessions'].items():
            cols, mc = d['cols'], d['mcols']
            for g in range(ROWS):
                row = [ses, '%d' % g] + [_fmt(c, cols[c][g]) for c in COLS]
                row += blank if mc is None else [
                    _fmt(c, mc[c][g]) for c in COLS_MICRO]
                fh.write(','.join(row) + '\n')
    os.replace(tmp, path)


def read_panel(path):
    """A panel back from its file."""
    try:
        with gzip.open(path, 'rt', encoding='ascii') as fh:
            first = fh.readline()
            if not first.startswith('# '):
                raise ValueError('no line of facts')
            meta = json.loads(first[2:])
            if meta.get('kind') != PANEL_KIND or \
                    meta.get('version') != W29_VERSION:
                raise ValueError('not a panel of %s' % W29_VERSION)
            head = fh.readline().strip().split(',')
            want = ['session', 'g'] + list(COLS) + \
                ['m_' + c for c in COLS_MICRO]
            if head != want:
                raise ValueError('other columns than this version writes')
            sessions = collections.OrderedDict()
            nc = len(COLS)
            for line in fh:
                p = line.rstrip('\n').split(',')
                if len(p) != len(want):
                    raise ValueError('a row of %d fields' % len(p))
                d = sessions.get(p[0])
                if d is None:
                    con = meta['contracts'][p[0]]
                    d = sessions[p[0]] = dict(
                        nq=con[0], mnq=con[1],
                        cols={c: array.array('d', [0.0]) * ROWS
                              for c in COLS},
                        mcols=None if con[1] is None else {
                            c: array.array('d', [0.0]) * ROWS
                            for c in COLS_MICRO})
                g = int(p[1])
                cols = d['cols']
                for k, c in enumerate(COLS):
                    cols[c][g] = _unfmt(c, p[2 + k])
                if d['mcols'] is not None:
                    mc = d['mcols']
                    for k, c in enumerate(COLS_MICRO):
                        mc[c][g] = _unfmt(c, p[2 + nc + k])
    except (OSError, EOFError, ValueError, KeyError, IndexError) as exc:
        raise SpeedDataError('%s is not a panel this version can read (%s). '
                             'Nothing was computed.'
                             % (os.path.basename(path), exc))
    out = dict(meta)
    out.pop('contracts', None)
    out['sessions'] = sessions
    return out


# ---------------------------------------------------------------------
# registration 3: volatility, the 48 inputs, what is forecast
# ---------------------------------------------------------------------
HORIZONS = (10, 30, 60, 120, 300, 600)
RTH_OPEN = 9 * 3600 + 1800
ENTRY_FROM, ENTRY_TO = 9 * 3600 + 35 * 60, 15 * 3600 + 55 * 60
SIGMA_S = 600
SIGMA_MIN_STEPS = 300                  # one-second changes it needs
USABLE_MIN = 3000                      # rows that make a session used
CLIP = 5.0
TRAIN_MIN = 20                         # sessions before the first forecast
INNER = 5                              # sessions that choose the penalty
PENALTIES = (0.01, 0.1, 1.0)

FEATURES = (
    'r5', 'r30', 'r120', 'r600', 'r1800',
    'o1', 'o5', 'o30', 'o120', 'o600',
    't1', 't5', 't30', 't120', 't600',
    'c30', 'c120', 'c600', 'z120',
    'q0', 'q5', 'q30',
    's0', 'srel',
    'a30', 'v30',
    'pday', 'dvwap', 'd600',
    'mt5', 'mt30', 'mt120', 'mt600', 'mc120', 'mq0', 'x30', 'x120', 'x600',
    'ma120', 'basis',
    'u1', 'u2',
    'r120u1', 'r120u2', 't120u1', 't120u2', 'r600v30', 'o30a30')
K = len(FEATURES)                      # 48
_FI = {name: k for k, name in enumerate(FEATURES)}


def _clip(x, lim=CLIP):
    return lim if x > lim else (-lim if x < -lim else x)


def _prefix(a):
    out = [0.0] * (len(a) + 1)
    s = 0.0
    for k, x in enumerate(a):
        s += x
        out[k + 1] = s
    return out


def _ratio(a, b):
    return (a - b) / (a + b) if a + b > 0 else 0.0


def _logratio(a, b, lim=3.0):
    return _clip(math.log(a / b), lim) if a > 0 and b > 0 else 0.0


class Session(object):
    """One session ready for the forecast: its usable rows from 09:35
    to 15:55, their 48 inputs column by column, sigma, the spread, what
    followed at each horizon, and the panel's execution columns."""


def derive(name, d):
    """A Session from one session of the panel; None when fewer than
    USABLE_MIN of its rows are usable."""
    c, mc = d['cols'], d['mcols']
    n = ROWS
    v = c['v']
    mid = [0.5 * (c['bid'][g] + c['ask'][g]) if v[g] else None
           for g in range(n)]
    P = {k: _prefix(c[k]) for k in ('ofi', 'buy', 'sell', 'vol', 'nb', 'ns',
                                    'qi', 'qt', 'spr', 'sq', 'sqn', 'gap')}
    P['ofi2'] = _prefix([x * x for x in c['ofi']])
    P['tfi2'] = _prefix([(c['buy'][g] - c['sell'][g]) ** 2
                         for g in range(n)])
    g_open = row_of_sod(RTH_OPEN)
    P['pv'] = _prefix([c['pv'][g] if g > g_open else 0.0 for g in range(n)])
    P['dvol'] = _prefix([c['vol'][g] if g > g_open else 0.0
                         for g in range(n)])
    P['mid'] = _prefix([m if m is not None else 0.0 for m in mid])
    P['midn'] = _prefix([1.0 if m is not None else 0.0 for m in mid])
    if mc is not None:
        M = {k: _prefix(mc[k]) for k in ('buy', 'sell', 'vol', 'nb', 'ns')}

    def win(p, g, w):                    # the sum over the w seconds to g
        k = w // STEP
        lo = g + 1 - k
        return p[g + 1] - p[lo if lo > 0 else 0]

    g_from, g_to = row_of_sod(ENTRY_FROM), row_of_sod(ENTRY_TO)
    ns = SIGMA_S // STEP
    s = Session()
    s.name = name
    s.rows = []
    s.x = [array.array('d') for _ in range(K)]
    s.sigma, s.spread, s.mid_at = [], [], []
    hi = lo = None
    for g in range(g_open, g_to + 1):
        m = mid[g]
        if m is not None:
            hi = m if hi is None or m > hi else hi
            lo = m if lo is None or m < lo else lo
        if g < g_from or m is None or g < ns:
            continue
        if win(P['gap'], g, SIGMA_S) > 0:
            continue
        steps = win(P['sqn'], g, SIGMA_S)
        sq = win(P['sq'], g, SIGMA_S)
        if steps < SIGMA_MIN_STEPS or sq <= 0:
            continue
        sig = math.sqrt(sq / steps)
        f = [0.0] * K
        for w in (5, 30, 120, 600, 1800):
            k = g - w // STEP
            if k >= 0 and mid[k] is not None:
                f[_FI['r%d' % w]] = _clip((m - mid[k]) / (sig * math.sqrt(w)))
        os_ = math.sqrt(win(P['ofi2'], g, SIGMA_S) / ns)
        ts_ = math.sqrt(win(P['tfi2'], g, SIGMA_S) / ns)
        if os_ > 0:
            f[_FI['o1']] = _clip(c['ofi1'][g] / (os_ * math.sqrt(0.2)))
            for w in (5, 30, 120, 600):
                f[_FI['o%d' % w]] = _clip(win(P['ofi'], g, w) /
                                          (os_ * math.sqrt(w / 5.0)))
        if ts_ > 0:
            f[_FI['t1']] = _clip(c['tfi1'][g] / (ts_ * math.sqrt(0.2)))
        for w in (5, 30, 120, 600):
            f[_FI['t%d' % w]] = _ratio(win(P['buy'], g, w),
                                       win(P['sell'], g, w))
        for w in (30, 120, 600):
            f[_FI['c%d' % w]] = _ratio(win(P['nb'], g, w),
                                       win(P['ns'], g, w))
        f[_FI['z120']] = f[_FI['t120']] - f[_FI['c120']]
        f[_FI['q0']] = _ratio(c['bs'][g], c['az'][g])
        for w in (5, 30):
            qt = win(P['qt'], g, w)
            f[_FI['q%d' % w]] = win(P['qi'], g, w) / qt if qt > 0 else 0.0
        sp = (c['ask'][g] - c['bid'][g])
        f[_FI['s0']] = min(sp / TICK, 8.0)
        q30, q600 = win(P['qt'], g, 30), win(P['qt'], g, 600)
        s30, s600 = win(P['spr'], g, 30), win(P['spr'], g, 600)
        if q30 > 0 and q600 > 0 and s600 > 0:
            f[_FI['srel']] = _clip((s30 / q30) / (s600 / q600) - 1.0, 3.0)
        f[_FI['a30']] = _logratio(win(P['vol'], g, 30) / 30.0,
                                  win(P['vol'], g, 600) / 600.0)
        n30 = win(P['sqn'], g, 30)
        if n30 > 0:
            f[_FI['v30']] = _logratio(win(P['sq'], g, 30) / n30, sq / steps)
        if hi is not None and hi > lo:
            f[_FI['pday']] = (m - lo) / (hi - lo) - 0.5
        dv = P['dvol'][g + 1]
        if dv > 0:
            f[_FI['dvwap']] = _clip((m - P['pv'][g + 1] / dv) /
                                    (sig * math.sqrt(1800.0)))
        mn = win(P['midn'], g, 600)
        if mn > 0:
            f[_FI['d600']] = _clip((m - win(P['mid'], g, 600) / mn) /
                                   (sig * math.sqrt(600.0)))
        if mc is not None and mc['v'][g]:
            for w in (5, 30, 120, 600):
                f[_FI['mt%d' % w]] = _ratio(win(M['buy'], g, w),
                                            win(M['sell'], g, w))
            f[_FI['mc120']] = _ratio(win(M['nb'], g, 120),
                                     win(M['ns'], g, 120))
            f[_FI['mq0']] = _ratio(mc['bs'][g], mc['az'][g])
            for w in (30, 120, 600):
                f[_FI['x%d' % w]] = f[_FI['mt%d' % w]] - f[_FI['t%d' % w]]
            f[_FI['ma120']] = _logratio(win(M['vol'], g, 120),
                                        10.0 * win(P['vol'], g, 120))
            f[_FI['basis']] = _clip(
                (0.5 * (mc['bid'][g] + mc['ask'][g]) - m) / TICK, 4.0)
        sod = sod_of_row(g)
        u1 = 1.0 if sod < 10 * 3600 else 0.0
        u2 = 1.0 if sod >= 15 * 3600 else 0.0
        f[_FI['u1']], f[_FI['u2']] = u1, u2
        f[_FI['r120u1']] = f[_FI['r120']] * u1
        f[_FI['r120u2']] = f[_FI['r120']] * u2
        f[_FI['t120u1']] = f[_FI['t120']] * u1
        f[_FI['t120u2']] = f[_FI['t120']] * u2
        f[_FI['r600v30']] = f[_FI['r600']] * f[_FI['v30']]
        f[_FI['o30a30']] = f[_FI['o30']] * f[_FI['a30']]
        s.rows.append(g)
        s.sigma.append(sig)
        s.spread.append(sp)
        s.mid_at.append(m)
        for k in range(K):
            s.x[k].append(f[k])
    if len(s.rows) < USABLE_MIN:
        return None
    s.n = len(s.rows)
    s.pos = array.array('l', [-1]) * n
    for i, g in enumerate(s.rows):
        s.pos[g] = i
    # what followed: None where the outcome is not known
    s.y, s.move = {}, {}
    for h in HORIZONS:
        k = h // STEP
        ys, mv = [], []
        root = math.sqrt(h)
        for i, g in enumerate(s.rows):
            e = g + k
            if sod_of_row(g) > ENTRY_TO - h or e >= n or mid[e] is None or \
                    P['gap'][e + 1] - P['gap'][g + 1] > 0:
                ys.append(None)
                mv.append(None)
            else:
                d_ = mid[e] - s.mid_at[i]
                mv.append(d_)
                ys.append(_clip(d_ / (s.sigma[i] * root)))
        s.y[h], s.move[h] = ys, mv
    s.mid = mid
    s.c = c
    return s


# ---------------------------------------------------------------------
# registration 3: the linear forecast, walked forward by session
# ---------------------------------------------------------------------
def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _sums(cols, y):
    """The sums a linear fit needs from rows given column by column."""
    sxx = [[0.0] * K for _ in range(K)]
    for a in range(K):
        ca = cols[a]
        for b in range(a, K):
            sxx[a][b] = sxx[b][a] = _dot(ca, cols[b])
    return dict(n=float(len(y)), sx=[sum(col) for col in cols], sxx=sxx,
                sy=sum(y), sxy=[_dot(col, y) for col in cols],
                syy=_dot(y, y))


def _zero():
    return dict(n=0.0, sx=[0.0] * K, sxx=[[0.0] * K for _ in range(K)],
                sy=0.0, sxy=[0.0] * K, syy=0.0)


def _plus(a, b, sign=1.0):
    return dict(
        n=a['n'] + sign * b['n'],
        sx=[x + sign * y for x, y in zip(a['sx'], b['sx'])],
        sxx=[[x + sign * y for x, y in zip(ra, rb)]
             for ra, rb in zip(a['sxx'], b['sxx'])],
        sy=a['sy'] + sign * b['sy'],
        sxy=[x + sign * y for x, y in zip(a['sxy'], b['sxy'])],
        syy=a['syy'] + sign * b['syy'])


def session_sums(s):
    """{h: sums} of one session, over the rows whose outcome at h is
    known. The rows known at every horizon are summed once."""
    known = {h: [y is not None for y in s.y[h]] for h in HORIZONS}
    every = [all(known[h][i] for h in HORIZONS) for i in range(s.n)]
    idx = [i for i in range(s.n) if every[i]]
    cols = [[col[i] for i in idx] for col in s.x]
    base = _sums(cols, [0.0] * len(idx))
    out = {}
    for h in HORIZONS:
        y = [s.y[h][i] for i in idx]
        g = dict(base, sy=sum(y), sxy=[_dot(col, y) for col in cols],
                 syy=_dot(y, y))
        rest = [i for i in range(s.n) if known[h][i] and not every[i]]
        if rest:
            g = _plus(g, _sums([[col[i] for i in rest] for col in s.x],
                               [s.y[h][i] for i in rest]))
        out[h] = g
    return out


def solve(a, b):
    """x of a x = b, by elimination with pivoting."""
    n = len(b)
    m = [list(a[i]) + [b[i]] for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda r: abs(m[r][i]))
        if abs(m[p][i]) < 1e-12:
            raise SpeedDataError('the forecast cannot be fitted: its '
                                 'inputs do not vary')
        m[i], m[p] = m[p], m[i]
        piv = m[i][i]
        row = m[i]
        for r in range(i + 1, n):
            f = m[r][i] / piv
            if f:
                mr = m[r]
                for k in range(i, n + 1):
                    mr[k] -= f * row[k]
    x = [0.0] * n
    for i in range(n - 1, -1, -1):
        x[i] = (m[i][n] - sum(m[i][k] * x[k]
                              for k in range(i + 1, n))) / m[i][i]
    return x


def fit(g, lam):
    """The ridge forecast from sums: dict(w, c, lam, n). Inputs are
    standardised on these rows; one that does not vary gets no weight."""
    n = g['n']
    if n < 2:
        raise SpeedDataError('no rows to fit the forecast on')
    my = g['sy'] / n
    mean = [v / n for v in g['sx']]
    var = [g['sxx'][k][k] / n - mean[k] ** 2 for k in range(K)]
    live = [k for k in range(K) if var[k] > 1e-12]
    sd = {k: math.sqrt(var[k]) for k in live}
    a = [[(g['sxx'][i][j] / n - mean[i] * mean[j]) / (sd[i] * sd[j]) +
          (lam if i == j else 0.0) for j in live] for i in live]
    b = [(g['sxy'][i] / n - mean[i] * my) / sd[i] for i in live]
    beta = solve(a, b) if live else []
    w = [0.0] * K
    for i, x in zip(live, beta):
        w[i] = x / sd[i]
    return dict(w=w, c=my - sum(w[k] * mean[k] for k in range(K)),
                lam=lam, n=n)


def sse(model, g):
    """The sum of squared errors of a forecast on rows given as sums."""
    w, c = model['w'], model['c']
    quad = sum(w[i] * sum(g['sxx'][i][j] * w[j] for j in range(K))
               for i in range(K) if w[i])
    return (g['syy'] - 2.0 * c * g['sy'] - 2.0 * _dot(w, g['sxy']) +
            g['n'] * c * c + 2.0 * c * _dot(w, g['sx']) + quad)


def choose(before, last):
    """The penalty that, fitted on `before`, forecasts `last` best (the
    larger one on a tie)."""
    best = None
    for lam in PENALTIES:
        e = sse(fit(before, lam), last)
        if best is None or e <= best[0]:
            best = (e, lam)
    return best[1]


def forecast_model(cum, i):
    """The forecast for session i from the running sums cum[0..i]: the
    penalty chosen on the INNER sessions before it, then fitted on all
    of them."""
    lam = choose(cum[i - INNER], _plus(cum[i], cum[i - INNER], -1.0))
    return fit(cum[i], lam)


def predict(model, s):
    out = [model['c']] * s.n
    for k in range(K):
        w = model['w'][k]
        if w:
            col = s.x[k]
            out = [o + w * x for o, x in zip(out, col)]
    return out


# ---------------------------------------------------------------------
# registration 2 and 4: three ways to trade
# ---------------------------------------------------------------------
DEEP_K = (2, 3, 4)
DEEP_H = (30, 60, 120, 300)
DEEP_MIN = 1.0                         # points from the mid, at least


def _px(c, name, g):
    x = c[name][g] if 0 <= g < ROWS else 0.0
    return x if x > 0 else None


def _close(c, e, side, entry):
    """(net, net at the stress delay) of closing `side` at row e by
    taking; None where the quote to take is missing."""
    x = _px(c, 'b05' if side > 0 else 'a05', e)
    xs = _px(c, 'b10' if side > 0 else 'a10', e)
    return (None if x is None else side * (x - entry) - COMMISSION,
            None if xs is None else side * (xs - entry) - COMMISSION)


def run_take(s, pred, h):
    """T on one session: [(session, row, side, net, net stressed)] and
    the number of trades left open by a missing quote."""
    c, k, root = s.c, h // STEP, math.sqrt(h)
    trades, void, free = [], 0, 0
    for i, g in enumerate(s.rows):
        if g < free or sod_of_row(g) > ENTRY_TO - h:
            continue
        pts = pred[i] * s.sigma[i] * root
        cost = s.spread[i] + COMMISSION
        side = 1 if pts > cost else (-1 if pts < -cost else 0)
        if not side:
            continue
        entry = _px(c, 'a05' if side > 0 else 'b05', g)
        if entry is None:
            continue
        e = g + k
        free = e
        net, _n = _close(c, e, side, entry)
        if net is None:
            void += 1
            continue
        es = _px(c, 'a10' if side > 0 else 'b10', g)
        xs = _px(c, 'b10' if side > 0 else 'a10', e)
        trades.append((s.name, g, side, net,
                       None if es is None or xs is None
                       else side * (xs - es) - COMMISSION))
    return trades, void


def run_join(s, pred, h):
    """M on one session: (trades, voids, orders placed, orders filled)."""
    c, root = s.c, math.sqrt(h)
    life = (JOIN_LIFE + JOIN_GRACE) * 1000.0
    trades, void, free, placed, filled = [], 0, 0, 0, 0
    for i, g in enumerate(s.rows):
        if g < free or sod_of_row(g) > ENTRY_TO - h:
            continue
        pts = pred[i] * s.sigma[i] * root
        cost = 0.5 * s.spread[i] + COMMISSION
        side = 1 if pts > cost else (-1 if pts < -cost else 0)
        if not side:
            continue
        entry = _px(c, 'b05' if side > 0 else 'a05', g)
        if entry is None:
            continue
        placed += 1
        f = c['fb' if side > 0 else 'fs'][g]
        if f < 0 or f > life:
            free = g + int(JOIN_LIFE // STEP)        # the next, 10 s on
            continue
        filled += 1
        e = g + int(math.ceil((DELAY + f / 1000.0 + h) / STEP - 1e-9))
        free = e
        net, nets = _close(c, e, side, entry)
        if net is None:
            void += 1
            continue
        trades.append((s.name, g, side, net, nets))
    return trades, void, placed, filled


def deep_price(mid, sigma, k, side):
    """The price a deep order rests at: k sigma root 5 from the mid, at
    least a point, rounded away from the market."""
    d = max(k * sigma * math.sqrt(STEP), DEEP_MIN)
    if side > 0:
        return math.floor((mid - d) / TICK + 1e-9) * TICK
    return math.ceil((mid + d) / TICK - 1e-9) * TICK


def run_deep(s, k, h):
    """D on one session: (trades, voids)."""
    c, kk = s.c, h // STEP
    lo, hi, lob, hia = c['lo'], c['hi'], c['lob'], c['hia']
    trades, void, free = [], 0, {1: 0, -1: 0}
    for i, g in enumerate(s.rows):
        if sod_of_row(g) > ENTRY_TO - h:
            continue
        b, a = _px(c, 'b05', g), _px(c, 'a05', g)
        if b is None or a is None:
            continue
        for side in (1, -1):
            if g < free[side]:
                continue
            p = deep_price(s.mid_at[i], s.sigma[i], k, side)
            if side > 0:
                if p >= b or not (0 < lo[g] < p and 0 < lob[g] < p):
                    continue
            elif p <= a or not (hi[g] > p and hia[g] > p):
                continue
            e = g + 1 + kk
            free[side] = e
            net, nets = _close(c, e, side, p)
            if net is None:
                void += 1
                continue
            trades.append((s.name, g, side, net, nets))
    return trades, void


# ---------------------------------------------------------------------
# registration 5-6: the statistics, the map, the verdict
# ---------------------------------------------------------------------
QUALIFY_H = 60
QUALIFY_TRADES = 200
QUALIFY_T = 3.0
CONFIRM_SESSIONS = 20
CONFIRM_TRADES = 100
CONFIRM_T = 2.0
TOP_SHARE = 0.05


def _mean(v):
    return sum(v) / len(v)


def _sd(v):
    m = _mean(v)
    return math.sqrt(sum((x - m) ** 2 for x in v) / (len(v) - 1))


def session_t(sums):
    """The mean of the session sums over its standard error."""
    if len(sums) < 3:
        return None
    sd = _sd(sums)
    return _mean(sums) / (sd / math.sqrt(len(sums))) if sd > 0 else None


def summarize(trades, names, void=0):
    """What a way to trade did on the sessions `names`."""
    by = dict.fromkeys(names, 0.0)
    for tr in trades:
        by[tr[0]] += tr[3]
    sums = [by[n] for n in names]
    n = len(trades)
    half = len(names) // 2
    stress = [tr[4] for tr in trades if tr[4] is not None]
    out = dict(
        trades=n, void=void, sessions=len(names),
        per_session=round(n / float(len(names)), 2) if names else None,
        net=round(_mean([tr[3] for tr in trades]), 4) if n else None,
        net_micro=round(_mean([tr[3] for tr in trades]) -
                        (COMMISSION_MICRO - COMMISSION), 4) if n else None,
        sd=round(_sd([tr[3] for tr in trades]), 3) if n > 1 else None,
        won=round(sum(1 for tr in trades if tr[3] > 0) / float(n), 4)
        if n else None,
        session_mean=round(_mean(sums), 4) if sums else None,
        t=session_t(sums),
        first_half=round(sum(sums[:half]), 3),
        second_half=round(sum(sums[half:]), 3),
        net_stress=round(_mean(stress), 4) if stress else None)
    if out['t'] is not None:
        out['t'] = round(out['t'], 3)
    return out


def qualifies(st, h, bar_t=QUALIFY_T, bar_n=QUALIFY_TRADES, halves=True):
    return bool(
        h >= QUALIFY_H and st['trades'] >= bar_n and
        st['session_mean'] is not None and st['session_mean'] > 0 and
        st['t'] is not None and st['t'] >= bar_t and
        (not halves or (st['first_half'] > 0 and st['second_half'] > 0))
        and st['net_stress'] is not None and st['net_stress'] > 0)


def products(x, y):
    """(sum of x y, sum of x x, sum of y y)."""
    return (sum(a * b for a, b in zip(x, y)), sum(a * a for a in x),
            sum(b * b for b in y))


def pooled(parts):
    """[correlation, t, sessions] from one (sum xy, sum xx, sum yy) a
    session, with no average taken off either side: the correlation is
    the sum of the products over the root of the two sums of squares,
    over all sessions together; t is the mean of the sessions' sums of
    products over its standard error.

    Only the sums of products are averaged. Each has expectation zero
    when the input says nothing about what follows, so t is centred. A
    correlation worked out session by session and then averaged is not:
    a session in which price runs one way gives a large sum of products
    and a large sum of squares together, so its ratio is held down,
    while a session that turns back gives a ratio that is not, and the
    average of the ratios falls below zero for any input that follows
    the price."""
    parts = [p for p in parts if p is not None]
    sxy = sum(p[0] for p in parts)
    sxx = sum(p[1] for p in parts)
    syy = sum(p[2] for p in parts)
    if len(parts) < 3 or sxx <= 0 or syy <= 0:
        return [None, None, len(parts)]
    t = session_t([p[0] for p in parts])
    return [round(sxy / math.sqrt(sxx * syy), 5),
            None if t is None else round(t, 3), len(parts)]


def _mt(v):
    """(mean, t) of one figure a session; None without three."""
    v = [x for x in v if x is not None]
    if len(v) < 3:
        return [None, None, len(v)]
    sd = _sd(v)
    return [round(_mean(v), 5),
            round(_mean(v) / (sd / math.sqrt(len(v))), 3) if sd > 0
            else None, len(v)]


def _median(v):
    v = sorted(v)
    n = len(v)
    return v[n // 2] if n % 2 else 0.5 * (v[n // 2 - 1] + v[n // 2])


def input_map(sessions, with_null=False):
    """{input: {h: [correlation, t, sessions]}} of each input with what
    followed, on the rows whose outcome is known at every horizon; with
    `with_null`, also {h: what the best of them reaches by chance}.

    Nothing is ranked within a session and no session's own average is
    taken off: either ties an input that follows the price (its
    distance from the day's VWAP, its place in the day's range) to the
    rest of that day's path, and shows a negative figure on a tape with
    nothing in it. The input is centred on its average over the OTHER
    sessions; the outcome, whose expectation is zero when nothing is
    there, is left as it is; and the sessions are put together as
    pooled() says."""
    idx, sx = [], []
    for s in sessions:
        ix = [i for i in range(s.n)
              if all(s.y[h][i] is not None for h in HORIZONS)]
        idx.append(ix)
        sx.append([sum(col[i] for i in ix) for col in s.x])
    n_all = sum(len(ix) for ix in idx)
    tot = [sum(v[k] for v in sx) for k in range(K)]
    per = {f: {h: [] for h in HORIZONS} for f in FEATURES}
    for s, ix, own in zip(sessions, idx, sx):
        if len(ix) < 30 or n_all - len(ix) < 30:
            continue
        ys = {h: [s.y[h][i] for i in ix] for h in HORIZONS}
        for k, f in enumerate(FEATURES):
            m = (tot[k] - own[k]) / (n_all - len(ix))
            col = s.x[k]
            xc = [col[i] - m for i in ix]
            for h in HORIZONS:
                per[f][h].append(products(xc, ys[h]))
    out = {f: {str(h): pooled(per[f][h]) for h in HORIZONS}
           for f in FEATURES}
    if not with_null:
        return out
    return out, {str(h): best_null([[p[0] for p in per[f][h]]
                                    for f in FEATURES]) for h in HORIZONS}


NULL_DRAWS = 1000


def best_null(sums, draws=None, seed=29):
    """What the best of the inputs looks like when nothing is there: the
    value that the largest |t| among them stays under 19 times in 20
    when each session's sign is drawn at random. `sums` is one list of
    session sums of products for each input, over the same sessions.

    The sums keep their sizes and what ties one input to another; only
    whether a session counts for or against is left to chance, which is
    what a tape with nothing in it would do. A sum of squares does not
    change with the signs, so each draw needs one sum of products an
    input."""
    draws = NULL_DRAWS if draws is None else draws
    n = len(sums[0]) if sums else 0
    live = [(v, sum(x * x for x in v)) for v in sums
            if len(v) == n and any(v)]
    if n < 3 or not live:
        return None
    rng = random.Random(seed)
    best = []
    for _ in range(draws):
        e = [1.0 if rng.random() < 0.5 else -1.0 for _k in range(n)]
        top = 0.0
        for v, q in live:
            d = sum(a * b for a, b in zip(e, v))
            var = (q - d * d / n) / (n - 1)
            if var > 0:
                t = abs(d / n) / math.sqrt(var / n)
                if t > top:
                    top = t
        best.append(top)
    best.sort()
    return round(best[min(draws - 1, int(0.95 * draws))], 3)


def spread_facts(sessions):
    """The spread from 09:30 to 16:00: its average in ticks and the
    share of the time at one tick, at two, at more."""
    g0, g1 = row_of_sod(RTH_OPEN) + 1, row_of_sod(16 * 3600)
    qt = spr = s1 = s2 = 0.0
    for s in sessions:
        c = s.c
        qt += sum(c['qt'][g0:g1 + 1])
        spr += sum(c['spr'][g0:g1 + 1])
        s1 += sum(c['s1'][g0:g1 + 1])
        s2 += sum(c['s2'][g0:g1 + 1])
    if qt <= 0:
        return None
    return dict(mean_ticks=round(spr / qt, 3), one_tick=round(s1 / qt, 4),
                two_ticks=round(s2 / qt, 4),
                more=round(max(0.0, 1.0 - (s1 + s2) / qt), 4))


def join_facts(sessions):
    """A join order with no forecast, on every usable row: how often it
    is filled within its life, and where the mid stood 30, 60 and 300
    seconds after the fill, measured from the fill price in the order's
    favour (before any commission)."""
    life = (JOIN_LIFE + JOIN_GRACE) * 1000.0
    placed = filled = 0
    after = {h: [] for h in (30, 60, 300)}
    for s in sessions:
        c = s.c
        per = {h: [] for h in after}
        for i, g in enumerate(s.rows):
            for side, fill, quote in ((1, 'fb', 'b05'), (-1, 'fs', 'a05')):
                p = _px(c, quote, g)
                if p is None:
                    continue
                placed += 1
                f = c[fill][g]
                if f < 0 or f > life:
                    continue
                filled += 1
                for h in per:
                    e = g + int(math.ceil((DELAY + f / 1000.0 + h) / STEP
                                          - 1e-9))
                    if e < ROWS and s.mid[e] is not None:
                        per[h].append(side * (s.mid[e] - p))
        for h in per:
            after[h].append(_mean(per[h]) if per[h] else None)
    return dict(placed=placed, filled=filled,
                share=round(filled / float(placed), 4) if placed else None,
                after={str(h): _mt(v) for h, v in after.items()})


def used_sessions(panel):
    """(the Sessions that are used, in date order; the names of those
    with too few usable rows)."""
    used, unused = [], []
    for name in sorted(panel['sessions']):
        s = derive(name, panel['sessions'][name])
        if s is None:
            unused.append(name)
        else:
            used.append(s)
    return used, unused


def _running(sums):
    """{h: [the sums of the sessions before i, for i = 0 .. n]}."""
    cum = {h: [_zero()] for h in HORIZONS}
    for g in sums:
        for h in HORIZONS:
            cum[h].append(_plus(cum[h][-1], g[h]))
    return cum


def _top(pred_move):
    """Of (forecast, move) pairs, what the strongest twentieth of the
    forecasts went on to move, in the forecast's direction."""
    if len(pred_move) < 40:
        return None, 0
    cut = sorted(abs(p) for p, _m in pred_move)[
        int(len(pred_move) * (1.0 - TOP_SHARE))]
    v = [(1 if p > 0 else -1) * m for p, m in pred_move
         if abs(p) >= cut and p != 0]
    return (round(_mean(v), 4) if v else None), len(v)


def _base(panel, used, unused):
    return dict(
        wave29=W29_VERSION, registration=REGISTRATION,
        sessions_used=[s.name for s in used], sessions_unused=unused,
        refused_unread=list(panel.get('refused_unread') or []),
        runs=panel.get('runs'), runs_skipped=panel.get('runs_skipped'),
        runs_outside_hours=panel.get('runs_outside_hours'),
        latency_ms=panel.get('latency_ms'),
        micro_sessions=sum(1 for s in used
                           if panel['sessions'][s.name]['mcols']
                           is not None))


def analyze(panel, progress=None):
    """Registration 3 to 6 on the panel of the exposed sessions."""
    def say(x):
        if progress:
            progress(x)
    if panel.get('fresh'):
        raise SpeedDataError(
            'this panel holds the confirmation sessions; it is read with '
            '--confirm and the frozen file, once. Nothing was computed.')
    used, unused = used_sessions(panel)
    if len(used) < TRAIN_MIN + 1:
        raise SpeedDataError(
            'only %d used sessions: the forecast needs %d before its '
            'first. Nothing was computed.' % (len(used), TRAIN_MIN))
    say('%d sessions used; summing' % len(used))
    names = [s.name for s in used]
    cum = _running([session_sums(s) for s in used])
    first = TRAIN_MIN
    oos = names[first:]
    rep = _base(panel, used, unused)
    inputs, chance = input_map(used, with_null=True)
    rep.update(part='dev', forecast_sessions=oos,
               spread=spread_facts(used), join_alone=join_facts(used),
               inputs=inputs, map={}, take={}, join={}, deep={},
               penalties={})
    sig = [x for s in used for x in s.sigma]
    spr = [x for s in used for x in s.spread]
    for h in HORIZONS:
        say('the forecast at %d seconds' % h)
        tk, tv = [], 0
        jn, jv, placed, filled = [], 0, 0, 0
        ic, pm, lams = [], [], collections.Counter()
        for i in range(first, len(used)):
            s = used[i]
            model = forecast_model(cum[h], i)
            lams[model['lam']] += 1
            pred = predict(model, s)
            a, v = run_take(s, pred, h)
            tk += a
            tv += v
            a, v, p, f = run_join(s, pred, h)
            jn += a
            jv += v
            placed += p
            filled += f
            known = [j for j in range(s.n) if s.y[h][j] is not None]
            if len(known) >= 30:
                ic.append(products([pred[j] for j in known],
                                   [s.y[h][j] for j in known]))
            pm += [(pred[j], s.move[h][j]) for j in known]
        top, top_n = _top(pm)
        best = sorted(((abs(v[str(h)][1] or 0.0), f) for f, v in
                       rep['inputs'].items()), reverse=True)[:3]
        rep['map'][str(h)] = dict(
            move=round(_median(sig) * math.sqrt(h), 3),
            cost=round(_median(spr) + COMMISSION, 3),
            forecast=pooled(ic), top_move=top, top_calls=top_n,
            best_inputs=[[f, rep['inputs'][f][str(h)][0],
                          rep['inputs'][f][str(h)][1]] for _a, f in best],
            best_by_chance=chance[str(h)])
        rep['penalties'][str(h)] = {str(k): v for k, v in lams.items()}
        st = summarize(tk, oos, tv)
        st['qualifies'] = qualifies(st, h)
        rep['take'][str(h)] = st
        st = summarize(jn, oos, jv)
        st.update(placed=placed, filled=filled,
                  qualifies=qualifies(st, h))
        rep['join'][str(h)] = st
    for k in DEEP_K:
        for h in DEEP_H:
            tr, void = [], 0
            for s in used:
                a, v = run_deep(s, k, h)
                tr += a
                void += v
            st = summarize(tr, names, void)
            st['qualifies'] = qualifies(st, h)
            rep['deep']['%d/%d' % (k, h)] = st
    say('the verdict')
    ways, rep['qualified'] = [], []
    for style, table in (('T', rep['take']), ('M', rep['join']),
                         ('D', rep['deep'])):
        ok = [(st['t'], n, key) for n, (key, st) in enumerate(table.items())
              if st['qualifies']]
        if not ok:
            continue
        rep['qualified'] += [dict(style=style, key=key, t=t_)
                             for t_, _n, key in ok]
        # the highest t; of two the same, the one listed first
        _t, _n, key = max(ok, key=lambda o: (o[0], -o[1]))
        way = dict(style=style, key=key, t=table[key]['t'])
        if style == 'D':
            way.update(k=int(key.split('/')[0]), h=int(key.split('/')[1]))
        else:
            h = int(key)
            n = len(used)
            lam = choose(cum[h][n - INNER],
                         _plus(cum[h][n], cum[h][n - INNER], -1.0))
            m = fit(cum[h][n], lam)
            way.update(h=h, model=dict(w=m['w'], c=m['c'], lam=lam,
                                       inputs=list(FEATURES)))
        ways.append(way)
    rep['frozen'] = seal(dict(wave29=W29_VERSION, frozen_on=names[-1],
                              sessions=len(names), ways=ways)) \
        if ways else None
    return rep


def seal(frozen):
    """The frozen ways with a fingerprint of themselves."""
    body = dict((k, v) for k, v in frozen.items() if k != 'seal')
    frozen = dict(body)
    frozen['seal'] = hashlib.sha256(
        json.dumps(body, sort_keys=True).encode('ascii')).hexdigest()
    return frozen


def _too_few(n):
    return ('only %d used sessions from 2026-11-16; the confirmation needs '
            '%d. Nothing was computed or recorded: run it again when more '
            'are recorded.' % (n, CONFIRM_SESSIONS))


def confirm(panel, frozen):
    """Registration 8: the frozen ways on the confirmation sessions."""
    if not panel.get('fresh'):
        raise SpeedDataError('the confirmation runs on the sessions from '
                             '2026-11-16 only. Nothing was computed.')
    if not isinstance(frozen, dict) or frozen.get('wave29') != W29_VERSION \
            or not frozen.get('ways') or seal(frozen)['seal'] != \
            frozen.get('seal'):
        raise SpeedDataError('this is not a file frozen by %s, or it was '
                             'changed after it was frozen. Nothing was '
                             'computed.' % W29_VERSION)
    used, unused = used_sessions(panel)
    if len(used) < CONFIRM_SESSIONS:
        raise SpeedDataError(_too_few(len(used)))
    names = [s.name for s in used]
    rep = _base(panel, used, unused)
    rep.update(part='confirm', seal=frozen['seal'], ways=[])
    for way in frozen['ways']:
        tr, void = [], 0
        for s in used:
            if way['style'] == 'D':
                a, v = run_deep(s, way['k'], way['h'])
            else:
                if list(way['model']['inputs']) != list(FEATURES):
                    raise SpeedDataError('the frozen forecast is of other '
                                         'inputs. Nothing was computed.')
                pred = predict(way['model'], s)
                if way['style'] == 'T':
                    a, v = run_take(s, pred, way['h'])
                else:
                    a, v = run_join(s, pred, way['h'])[:2]
            tr += a
            void += v
        st = summarize(tr, names, void)
        st.update(style=way['style'], key=way['key'],
                  confirmed=qualifies(st, way['h'], CONFIRM_T,
                                      CONFIRM_TRADES, halves=False))
        rep['ways'].append(st)
    rep['confirmed'] = [w['style'] + ' ' + w['key'] for w in rep['ways']
                        if w['confirmed']]
    return rep


# ---------------------------------------------------------------------
# text, ledger, command
# ---------------------------------------------------------------------
def _n(x, fmt='%+.2f', none='   n/a'):
    return none if x is None else fmt % x


def _hold(h):
    return '%d s' % h if h < 60 else '%d min' % (h // 60)


def _way_line(key, st, extra=''):
    return '  %-9s %6d %7s  %s  %s  %s  %9s %9s  %s  %s%s' % (
        key, st['trades'], _n(st['per_session'], '%.1f'),
        _n(st['net'], '%+7.2f'), _n(st['net_micro'], '%+7.2f'),
        _n(st['t'], '%+6.2f'), _n(st['first_half'], '%+.1f'),
        _n(st['second_half'], '%+.1f'), _n(st['net_stress'], '%+7.2f'),
        'QUALIFIES' if st.get('qualifies') else (
            'CONFIRMED' if st.get('confirmed') else '-'), extra)


_WAY_HEAD = ('  %-9s %6s %7s  %7s  %7s  %6s  %9s %9s  %7s' % (
    'hold', 'trades', 'a day', 'net', 'as MNQ', 't', 'first', 'second',
    '1.0 s'))


def _tape(rep):
    L = []
    lat = (rep.get('latency_ms') or {}).get(INSTRUMENTS[0]) or {}
    if lat.get('n'):
        L.append('  the computer had half of NQ\'s rows within %s ms of the '
                 'exchange\'s stamp, 19 in 20 within %s ms (the two clocks '
                 'are not known to agree)' % (lat.get('p50'), lat.get('p95')))
    return L


def text(rep):
    used = rep['sessions_used']
    L = ['%s   the fastest trade a retail account can win' % rep['wave29'],
         'sessions used: %d (%s to %s)%s; the micro contract in %d' % (
             len(used), used[0], used[-1],
             '; %d with too few usable rows' % len(rep['sessions_unused'])
             if rep['sessions_unused'] else '', rep['micro_sessions'])]
    if rep['refused_unread']:
        L.append('never opened: %d other session(s) in the folder'
                 % len(rep['refused_unread']))
    if rep.get('runs_skipped'):
        L.append('runs set aside as damaged: %d' % len(rep['runs_skipped']))
    if rep['part'] == 'confirm':
        L += ['', 'THE CONFIRMATION (registration 8): the frozen ways on '
              'sessions nothing had read', _WAY_HEAD]
        for st in rep['ways']:
            L.append(_way_line('%s %s' % (st['style'], st['key']), st))
        L += ['', 'CONFIRMED: %s' % (', '.join(rep['confirmed']) or
                                     'nothing'),
              'Points a trade, one contract, after commission, spread and '
              'delay; not P&L. No order was placed.']
        return '\n'.join(L)
    L.append('the forecast is judged on the last %d, which it was not '
             'fitted on' % len(rep['forecast_sessions']))
    sp = rep['spread']
    L += ['', 'THE TAPE']
    if sp:
        L.append('  NQ\'s spread, 09:30 to 16:00: %.2f ticks on average; one '
                 'tick %.0f %% of the time, two %.0f %%, more %.0f %%' % (
                     sp['mean_ticks'], 100 * sp['one_tick'],
                     100 * sp['two_ticks'], 100 * sp['more']))
    L += _tape(rep)
    L += ['', 'THE MAP (reported, never judged; points)',
          '  %-7s %12s %12s %22s %24s   %s' % (
              'hold', 'a usual move', 'a round trip',
              'forecast\'s corr. (t)', 'its best 1 in 20 moved',
              'best single input')]
    for h in HORIZONS:
        m = rep['map'][str(h)]
        b = m['best_inputs'][0] if m['best_inputs'] else None
        L.append('  %-7s %12.2f %12.2f %13s (%s) %24s   %s' % (
            _hold(h), m['move'], m['cost'], _n(m['forecast'][0], '%+.4f'),
            _n(m['forecast'][1], '%+.1f'), _n(m['top_move'], '%+.2f'),
            '%s (%s, t %s; chance reaches %s)' % (
                b[0], _n(b[1], '%+.4f'), _n(b[2], '%+.1f'),
                _n(m.get('best_by_chance'), '%.1f')) if b else 'n/a'))
    L.append('  A way to trade has to move more than a round trip. "Its '
             'best 1 in 20" is what followed the forecast\'s strongest '
             'calls, before any cost.')
    L.append('  The best single input is the largest of %d, so it always '
             'looks like something: "chance reaches" is the t it gets to '
             'one time in twenty with nothing in the tape (these '
             'sessions\' own sums, each session\'s sign drawn at random).'
             % K)
    ja = rep['join_alone']
    if ja and ja['placed']:
        a = ja['after']
        L += ['', 'A JOIN ORDER WITH NO FORECAST (reported)',
              '  filled within its 10 seconds: %.0f %% of %d. From the fill '
              'price, in the order\'s favour, the mid stood %s points 30 s '
              'later, %s at 60 s, %s at 5 min' % (
                  100 * ja['share'], ja['placed'], _n(a['30'][0], '%+.2f'),
                  _n(a['60'][0], '%+.2f'), _n(a['300'][0], '%+.2f'))]
    L += ['', 'T - TAKE, when the forecast is larger than the spread plus '
          'the commission', _WAY_HEAD]
    for h in HORIZONS:
        L.append(_way_line(_hold(h), rep['take'][str(h)]))
    L += ['', 'M - JOIN the best price, when the forecast is larger than '
          'half the spread plus the commission', _WAY_HEAD]
    for h in HORIZONS:
        st = rep['join'][str(h)]
        L.append(_way_line(_hold(h), st, '   (%d of %d orders filled)' % (
            st['filled'], st['placed'])))
    L += ['', 'D - DEEP: an order resting k usual 5-second moves from the '
          'price, every 5 seconds, no forecast',
          _WAY_HEAD.replace('hold     ', 'k / hold ')]
    for k in DEEP_K:
        for h in DEEP_H:
            L.append(_way_line('%d / %s' % (k, _hold(h)),
                               rep['deep']['%d/%d' % (k, h)]))
    L += ['  net: points a trade after commission, spread and the 0.5 s '
          'delay; as MNQ: with the micro\'s commission; t: of the session '
          'sums; first, second: the halves\' sums; 1.0 s: net at the '
          'stress delay.', '', 'THE VERDICT (registration 6)']
    if rep['qualified']:
        kept = [(w['style'], w['key']) for w in rep['frozen']['ways']]
        for q in rep['qualified']:
            L.append('  QUALIFIES%s: %s %s (t %+.2f)' % (
                ' and is frozen' if (q['style'], q['key']) in kept else
                ' (not frozen: another of its kind has the higher t)',
                q['style'], q['key'], q['t']))
        L.append('  These sessions are exposed: a pass here is not '
                 'evidence. The frozen ways go to the sessions recorded '
                 'from 2026-11-16, once.')
    else:
        L.append('  Nothing qualifies: at 60 seconds or more, no way to '
                 'trade the tape pays for a retail account\'s costs and '
                 'delay on these sessions.')
    L.append('One contract, minute by minute on recorded tape; not P&L. No '
             'order was placed.')
    return '\n'.join(L)


def _ledger(path):
    if not os.path.exists(path):
        return dict(reads=[])
    try:
        with open(path) as fh:
            doc = json.load(fh)
    except (OSError, ValueError):
        doc = None
    if not isinstance(doc, dict) or not isinstance(doc.get('reads'), list):
        raise SpeedDataError('the ledger %s cannot be read: restore it '
                             'before any read is made. Nothing was read.'
                             % os.path.basename(path))
    return doc


def _entries(path, part):
    return [r for r in _ledger(path)['reads']
            if r.get('version') == W29_VERSION and r.get('part') == part]


def confirm_made(path):
    return bool(_entries(path, 'confirm'))


def record(entry, path):
    doc = _ledger(path)
    doc['reads'].append(dict(
        entry, version=W29_VERSION,
        at=datetime.datetime.now(datetime.timezone.utc).strftime(
            '%Y-%m-%dT%H:%M:%SZ')))
    try:
        with open(path, 'w') as fh:
            json.dump(doc, fh, indent=1)
    except OSError as exc:
        raise SpeedDataError('the ledger %s cannot be written (%s): nothing '
                             'is shown before the read is on record.'
                             % (os.path.basename(path), exc))
    return len(doc['reads'])


def _beside(out, tail):
    base = out[:-5] if out.lower().endswith('.json') else out
    return base + tail


def _frozen_file(path):
    """The frozen ways from their file, whole and unchanged."""
    try:
        with open(path) as fh:
            frozen = json.load(fh)
    except (OSError, ValueError) as exc:
        raise SpeedDataError('the frozen file cannot be read (%s). Nothing '
                             'was read.' % exc)
    if not isinstance(frozen, dict) or frozen.get('wave29') != W29_VERSION \
            or not frozen.get('ways') or \
            seal(frozen)['seal'] != frozen.get('seal'):
        raise SpeedDataError('this is not a file frozen by %s, or it was '
                             'changed after it was frozen. Nothing was read.'
                             % W29_VERSION)
    return frozen


_OPTIONS = ('--out', '--confirm', '--from-panel')


def _args(argv):
    """(the capture folder or None, {option: value}), or None when the
    line is not one this command knows: an option it does not have, an
    option without its value or given twice, more than one folder."""
    opts, pos, i = {}, [], 0
    while i < len(argv):
        a = argv[i]
        if a in _OPTIONS:
            if a in opts or i + 1 >= len(argv) or \
                    argv[i + 1].startswith('--'):
                return None
            opts[a] = argv[i + 1]
            i += 2
        elif a.startswith('--'):
            return None
        else:
            pos.append(a)
            i += 1
    if len(pos) > 1:
        return None
    return (pos[0] if pos else None), opts


def main(argv=None, ledger=None, reads=None):
    parsed = _args(list(sys.argv[1:] if argv is None else argv))
    capture, opts = parsed if parsed else (None, {})
    out, frozen_path, from_panel = (opts.get(k) for k in _OPTIONS)
    if not out or bool(from_panel) == bool(capture):
        print(__doc__)
        return 2

    def say(x):
        sys.stderr.write('  %s\n' % x)
        sys.stderr.flush()
    reads = reads or os.path.join(HERE, READS_LEDGER)
    panel_path = _beside(out, '_panel.csv.gz')
    try:
        for p in [out] if from_panel else [out, panel_path]:
            if not W25.can_write(p):
                print('STOPPED: %s cannot be written (does the folder '
                      'exist?). Nothing was read.' % p)
                return 2
        if frozen_path and from_panel:
            # the confirmation's report again, from its own saved panel
            frozen = _frozen_file(frozen_path)
            made = _entries(reads, 'confirm')
            if not made:
                raise SpeedDataError(
                    'the confirmation has not been made. It is made from '
                    'the recordings, once: give the capture folder. '
                    'Nothing was computed.')
            if made[-1].get('seal') != frozen['seal']:
                raise SpeedDataError(
                    'the confirmation was made with another frozen file. '
                    'Nothing was computed.')
            rep = confirm(read_panel(from_panel), frozen)
            if rep['sessions_used'] != made[-1].get('sessions'):
                raise SpeedDataError(
                    'this is not the panel the confirmation was made from '
                    '(other sessions). Nothing is shown.')
            n = record(dict(part='confirm-again', seal=frozen['seal'],
                            sessions=rep['sessions_used']), reads)
        elif frozen_path:
            frozen = _frozen_file(frozen_path)
            if confirm_made(reads):
                print('REFUSED: the confirmation has been made (%s). It is '
                      'made once.' % READS_LEDGER)
                return 2
            study = _entries(reads, 'dev')
            if not study or study[-1].get('seal') != frozen['seal']:
                raise SpeedDataError(
                    'this is not the frozen file the study last wrote (%s). '
                    'Nothing was read.' % (
                        '%s holds no study' % READS_LEDGER if not study
                        else 'the study on record froze nothing'
                        if not study[-1].get('seal')
                        else 'the study on record froze another'))
            panel = read_capture(capture, ledger, say, fresh=True)
            n_used = len(used_sessions(panel)[0])
            if n_used < CONFIRM_SESSIONS:
                raise SpeedDataError(_too_few(n_used))
            write_panel(panel, panel_path)
            say('the panel is saved: %s' % panel_path)
            del panel
            rep = confirm(read_panel(panel_path), frozen)
            n = record(dict(part='confirm', seal=frozen['seal'],
                            sessions=rep['sessions_used'],
                            confirmed=rep['confirmed']), reads)
        else:
            if not from_panel:
                panel = read_capture(capture, ledger, say)
                if not panel['sessions']:
                    print('STOPPED: no session of NQ with trades from 08:00 '
                          'to 16:15 was found. Nothing was computed.')
                    return 2
                write_panel(panel, panel_path)       # before any result
                say('the panel is saved: %s' % panel_path)
                del panel
            # always from the file, so the file gives the same report again
            rep = analyze(read_panel(from_panel or panel_path), say)
            n = record(dict(
                part='dev', sessions=len(rep['sessions_used']),
                from_panel=bool(from_panel),
                qualified=[q['style'] + ' ' + q['key']
                           for q in rep['qualified']],
                frozen=[w['style'] + ' ' + w['key'] for w in
                        (rep['frozen'] or {}).get('ways', [])],
                seal=(rep['frozen'] or {}).get('seal')), reads)
    except (SpeedDataError, RUN.NoCaptureData, RUN.CaptureUnavailable) as exc:
        print('STOPPED: %s' % exc)
        return 2
    with open(out, 'w') as fh:
        json.dump(rep, fh, indent=1, default=str)
    print(text(rep))
    print('\nwave-twenty-nine report -> %s' % out)
    if rep['part'] == 'dev' and rep['frozen']:
        fz = _beside(out, '_frozen.json')
        with open(fz, 'w') as fh:
            json.dump(rep['frozen'], fh, indent=1)
        print('frozen -> %s' % fz)
    print('recorded (%d entries in %s)' % (n, READS_LEDGER))
    return 0


if __name__ == '__main__':
    sys.exit(main())
