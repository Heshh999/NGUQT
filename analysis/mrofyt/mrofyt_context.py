#!/usr/bin/env python3
"""mrofyt_context.py - MROF-YT-CTX-1.0

MROF_YT_CONTEXT_REGISTRATION.md turned into running code. The question:
by 10:30 ET, does what the day has shown so far (the gap, the first
hour, VWAP, volume, where it opened against yesterday's range and value)
tell you whether the rest of the day favours LONG, SHORT, or neither?

It needs no order book, only one-minute bars, and NinjaTrader keeps
those back to about 2006: thousands of sessions across very different
markets (2008, 2020, 2022), where the order-flow recordings have weeks.

    input     NinjaTrader minute exports, one file per contract, e.g.
              "NQ 12-26.Last.txt": "yyyyMMdd HHmmss;open;high;low;close;
              volume", time stamps in UTC at the END of each bar (how
              NinjaTrader exports). A one-file continuous series works.
    sessions  the front contract each day by the previous session's
              volume (known at the open); a session counts when its cash
              session 09:30-16:00 ET is complete (early closes drop out)
    features  13, fixed, all known at 10:30 ET, scaled by the 14-session
              average true range so 2006 and 2026 compare
    outcome   rest of day: (16:00 close - 10:30 price) / ATR, in the
              rule's direction, against every day's average
    search    676 rules (deciles alone, quintile pairs; long or short),
              month-clustered t, Benjamini-Hochberg, both halves of DEV;
              at most five nominated with numeric cut-points
    split     DEV = 2019-06-01 to 2026-06-30: the years this repository's
              earlier minute-bar studies already used (2019-06-02 on).
              VALIDATION = every session before 2019-06-01, which no
              study here has read. The search never opens a VALIDATION
              bar; the evaluator opens nothing else. Sessions from
              2026-07-01 are never read (the replay window and every
              recorded order-flow session).

    python3 mrofyt_context.py "<folder of exports>" --out ctx.json \\
            --nominated-out ctx_nominated.json
    python3 mrofyt_context.py "<folder>" --evaluate ctx_nominated.json \\
            --out ctx_eval_dev.json             # DEV only: reproduces
    python3 mrofyt_context.py "<folder>" --evaluate ctx_nominated.json \\
            --unblind --out ctx_eval.json       # VALIDATION, once

    --root NQ           contract root to read (default NQ)
    --stamps-tz UTC|ET  how the file's times are stamped (default UTC)
    --stamps end|start  bar stamped at its end (default) or its start
    --calendar FILE     optional "YYYYMMDD,EVENT" lines (FOMC, CPI ...)
                        for a descriptive event-day breakdown
    --days-out FILE     the per-session features as CSV (DEV only in a
                        search; nothing at or after 2026-07-01, ever)

THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. No order is placed.
"""

import array
import bisect
import collections
import datetime as _dt
import json
import os
import re
import sys

import mrofyt_bigmove as BM
import mrofyt_discover as DI

CTX_VERSION = 'MROF-YT-CTX-1.0'
REGISTRATION = 'MROF_YT_CONTEXT_REGISTRATION.md'
REFUSE_FROM = '20260701'
VALIDATION_BEFORE = '20190601'     # registration 5: the untouched years
EXPOSURE_FILE = 'MROF_CONTEXT_EXPOSURE.json'

# registration 1: sessions and windows (ET seconds of day, bar START)
RTH_OPEN, RTH_CLOSE = 9 * 3600 + 1800, 16 * 3600
IB_END = 10 * 3600 + 1800
VWAP_EARLY = 10 * 3600
SHOCK_START, SHOCK_END = 8 * 3600 + 1800, 8 * 3600 + 2100
SESSION_ROLL = 18 * 3600
RTH_MIN_BARS = 370                      # of 390
RTH_FIRST_BY = RTH_OPEN + 60
RTH_LAST_FROM = RTH_CLOSE - 300
PROFILE_BIN = 1.0                       # points
VALUE_SHARE = 0.70

# registration 2: features
SIGNED = ('gap', 'ib_move', 'ib_pos', 'vwap_dist', 'vwap_slope',
          'open_vs_range', 'open_vs_value', 'prev_day_move')
UNSIGNED = ('on_range', 'ib_range_rel', 'rel_vol', 'atr_rel', 'shock830')
FEATURES = SIGNED + UNSIGNED
ATR_N = 14
MED_N = 20
REGIME_N = 100

# registration 3-6
DECILE = ('decile', 0.10)
QUINTILE = ('quintile', 0.20)
DEGENERATE_FACTOR = 1.5
N_RULES = 676
FDR_Q = 0.10
MIN_DAYS = 60
MIN_MONTHS = 24
MIN_HALF = 30
NOMINATE_MAX = 5
NOMINATE_P = 0.05
OVERLAP_MAX = 0.5
HOLM_ALPHA = 0.05
TREND_CL = 0.20                         # close in the outer 20 % of range
PATH_ATR = 0.5                          # descriptive first-touch distance


class ContextDataError(Exception):
    """The exports cannot be read as registered (time zone, stamps,
    format, nothing complete): stop with the reason, never guess."""


# ---------------------------------------------------------------------
# time: UTC -> US Eastern, both DST regimes (2007 rule and 1987-2006)
# ---------------------------------------------------------------------
_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)


def _nth_sunday(year, month, n):
    d = _dt.date(year, month, 1)
    first = d + _dt.timedelta(days=(6 - d.weekday()) % 7)
    return first + _dt.timedelta(days=7 * (n - 1))


def _last_sunday(year, month):
    d = _dt.date(year + (month == 12), month % 12 + 1, 1) - \
        _dt.timedelta(days=1)
    return d - _dt.timedelta(days=(d.weekday() + 1) % 7)


def _dst_window(year):
    if year >= 2007:
        s, e = _nth_sunday(year, 3, 2), _nth_sunday(year, 11, 1)
    else:
        s, e = _nth_sunday(year, 4, 1), _last_sunday(year, 10)
    start = (_dt.datetime(s.year, s.month, s.day, 7,
                          tzinfo=_dt.timezone.utc) - _EPOCH).total_seconds()
    end = (_dt.datetime(e.year, e.month, e.day, 6,
                        tzinfo=_dt.timezone.utc) - _EPOCH).total_seconds()
    return start, end


_dst = {}


def et_offset(epoch, year):
    w = _dst.get(year)
    if w is None:
        w = _dst[year] = _dst_window(year)
    return -4 * 3600 if w[0] <= epoch < w[1] else -5 * 3600


_midnight = {}


def _day_epoch(ymd):
    e = _midnight.get(ymd)
    if e is None:
        d = _dt.datetime(int(ymd[:4]), int(ymd[4:6]), int(ymd[6:8]),
                         tzinfo=_dt.timezone.utc)
        e = _midnight[ymd] = int((d - _EPOCH).total_seconds())
    return e


_dayname = {}


def _day_str(daynum):
    s = _dayname.get(daynum)
    if s is None:
        s = _dayname[daynum] = (_EPOCH.date() +
                                _dt.timedelta(days=daynum)).strftime('%Y%m%d')
    return s


def bar_session(stamp_ymd, stamp_hms, stamps_tz='UTC', stamps='end'):
    """(session YYYYMMDD, ET second of day of the bar START) for one
    exported bar."""
    hh, mm, ss = int(stamp_hms[0:2]), int(stamp_hms[2:4]), int(stamp_hms[4:6])
    t = _day_epoch(stamp_ymd) + hh * 3600 + mm * 60 + ss
    if stamps == 'end':
        t -= 60
    if stamps_tz == 'UTC':
        loc = t + et_offset(t, int(stamp_ymd[:4]))
    else:
        loc = t                                   # already Eastern
    day = loc // 86400
    sod = loc - day * 86400
    if sod >= SESSION_ROLL:
        day += 1
    return _day_str(day), sod


# ---------------------------------------------------------------------
# reading the exports
# ---------------------------------------------------------------------
_CONTRACT = re.compile(r'^(?P<root>[A-Z0-9]+)\s+(?P<mm>\d{2})-(?P<yy>\d{2})')


def contract_of(filename, root):
    """'NQ 12-26.Last.txt' -> 'NQ 12-26'; a file of the root without a
    month (a continuous series) -> 'NQ CONT'; another root -> None."""
    base = os.path.basename(filename)
    m = _CONTRACT.match(base)
    if m:
        return None if m.group('root') != root else \
            '%s %s-%s' % (root, m.group('mm'), m.group('yy'))
    if base.split(' ')[0].split('.')[0] == root:
        return '%s CONT' % root
    return None


class DayAgg(object):
    __slots__ = ('rth_open', 'rth_high', 'rth_low', 'rth_close', 'rth_vol',
                 'rth_n', 'first_sod', 'last_sod', 'ib_high', 'ib_low',
                 'ib_vol', 'p1030', 'vw_num', 'vw_den', 'vwap_1000',
                 'vwap_1030', 'on_high', 'on_low', 'on_vol', 'p0929',
                 's830_high', 's830_low', 'prof', 'post')

    def __init__(self):
        self.rth_open = self.rth_high = self.rth_low = self.rth_close = None
        self.rth_vol = 0.0
        self.rth_n = 0
        self.first_sod = self.last_sod = None
        self.ib_high = self.ib_low = None
        self.ib_vol = 0.0
        self.p1030 = None
        self.vw_num = self.vw_den = 0.0
        self.vwap_1000 = self.vwap_1030 = None
        self.on_high = self.on_low = None
        self.on_vol = 0.0
        self.p0929 = None
        self.s830_high = self.s830_low = None
        self.prof = collections.defaultdict(float)
        self.post = array.array('d')          # high, low pairs after 10:30

    def add(self, sod, o, h, lo, c, v):
        if RTH_OPEN <= sod < RTH_CLOSE:
            if self.rth_open is None:
                self.rth_open = o
                self.first_sod = sod
            self.rth_high = h if self.rth_high is None else max(self.rth_high,
                                                                h)
            self.rth_low = lo if self.rth_low is None else min(self.rth_low,
                                                               lo)
            self.rth_close = c
            self.last_sod = sod
            self.rth_vol += v
            self.rth_n += 1
            self.vw_num += (h + lo + c) / 3.0 * v
            self.vw_den += v
            vw = self.vw_num / self.vw_den if self.vw_den > 0 else None
            if sod < VWAP_EARLY:
                self.vwap_1000 = vw
            if sod < IB_END:
                self.vwap_1030 = vw
                self.p1030 = c
                self.ib_high = h if self.ib_high is None else \
                    max(self.ib_high, h)
                self.ib_low = lo if self.ib_low is None else \
                    min(self.ib_low, lo)
                self.ib_vol += v
            else:
                self.post.append(h)
                self.post.append(lo)
            b0, b1 = int(lo // PROFILE_BIN), int(h // PROFILE_BIN)
            share = v / (b1 - b0 + 1)
            for b in range(b0, b1 + 1):
                self.prof[b] += share
        elif sod < RTH_OPEN or sod >= SESSION_ROLL:
            # the overnight: 18:00 of the previous day to 09:29
            self.on_high = h if self.on_high is None else max(self.on_high, h)
            self.on_low = lo if self.on_low is None else min(self.on_low, lo)
            self.on_vol += v
            if sod < RTH_OPEN:
                self.p0929 = c
            if SHOCK_START <= sod < SHOCK_END:
                self.s830_high = h if self.s830_high is None else \
                    max(self.s830_high, h)
                self.s830_low = lo if self.s830_low is None else \
                    min(self.s830_low, lo)

    def finalize(self):
        va = value_area(self.prof)
        complete = (self.rth_n >= RTH_MIN_BARS and self.first_sod is not None
                    and self.first_sod < RTH_FIRST_BY and
                    self.last_sod >= RTH_LAST_FROM and self.p1030 is not None
                    and self.vwap_1000 is not None)
        return dict(
            complete=complete, rth_open=self.rth_open, rth_high=self.rth_high,
            rth_low=self.rth_low, rth_close=self.rth_close,
            rth_vol=self.rth_vol, rth_n=self.rth_n, ib_high=self.ib_high,
            ib_low=self.ib_low, ib_vol=self.ib_vol, p1030=self.p1030,
            vwap_1000=self.vwap_1000, vwap_1030=self.vwap_1030,
            on_high=self.on_high, on_low=self.on_low, p0929=self.p0929,
            s830=(None if self.s830_high is None
                  else self.s830_high - self.s830_low),
            poc=va[0], vah=va[1], val=va[2], post=self.post)


def value_area(prof, share=VALUE_SHARE, binw=PROFILE_BIN):
    """(POC, VAH, VAL) in price from {bin: volume}: the fullest bin
    (lowest price on a tie), grown one bin at a time toward the fuller
    neighbour (the higher on a tie) until it holds `share` of volume."""
    if not prof:
        return None, None, None
    tot = sum(prof.values())
    poc = min(prof, key=lambda b: (-prof[b], b))
    lo = hi = poc
    acc = prof[poc]
    bmin, bmax = min(prof), max(prof)
    while acc < share * tot and (lo > bmin or hi < bmax):
        up = prof.get(hi + 1, 0.0) if hi < bmax else -1.0
        dn = prof.get(lo - 1, 0.0) if lo > bmin else -1.0
        if up >= dn:
            hi += 1
            acc += max(up, 0.0)
        else:
            lo -= 1
            acc += max(dn, 0.0)
    return ((poc + 0.5) * binw, (hi + 1) * binw, lo * binw)


class Reader(object):
    """Streams every export of the root into per-(contract, session)
    day statistics, and the minute-of-day volume the time-stamp check
    needs. Only sessions `allow` accepts are kept; every other bar is
    dropped the moment its session is known, before anything is
    computed from it. Sessions from REFUSE_FROM on are never kept."""

    def __init__(self, root='NQ', stamps_tz='UTC', stamps='end',
                 allow=None):
        self.root, self.stamps_tz, self.stamps = root, stamps_tz, stamps
        self.allow = allow
        self.days = {}                     # (contract, session) -> stats
        self.files = []
        self.bad_lines = 0
        self.refused_sessions = set()      # from REFUSE_FROM on
        self.skipped_sessions = set()      # outside `allow`
        self.minute_vol = collections.defaultdict(float)
        self.minute_n = collections.defaultdict(int)

    def read_path(self, path):
        paths = []
        for spec in [p.strip().strip('"') for p in str(path).split(';')]:
            if not spec:
                continue
            if os.path.isdir(spec):
                for name in sorted(os.listdir(spec)):
                    full = os.path.join(spec, name)
                    # tick exports (.Bid / .Ask) are not minute bars
                    if '.Bid.' in name or '.Ask.' in name:
                        continue
                    if os.path.isfile(full) and \
                            contract_of(name, self.root) is not None:
                        paths.append(full)
            elif os.path.isfile(spec):
                paths.append(spec)
            else:
                raise ContextDataError('cannot read %s: not a file or folder'
                                       % spec)
        if not paths:
            raise ContextDataError(
                'no %s minute exports found in %s (expected files named '
                'like "%s 12-26.Last.txt")' % (self.root, path, self.root))
        for p in paths:
            self.read_file(p)

    def read_file(self, path):
        contract = contract_of(path, self.root) or '%s CONT' % self.root
        aggs = {}
        n = 0
        with open(path, 'r', errors='replace') as fh:
            for line in fh:
                parts = re.split(r'[;,]', line.strip())
                if len(parts) != 6:
                    if line.strip():
                        self.bad_lines += 1
                    continue
                stamp = parts[0].split()
                if len(stamp) < 2 or len(stamp[0]) != 8 or \
                        len(stamp[1]) != 6 or not stamp[0].isdigit():
                    self.bad_lines += 1           # a header or a stray line
                    continue
                try:
                    o, h, lo, c, v = (float(x) for x in parts[1:])
                except ValueError:
                    self.bad_lines += 1
                    continue
                ses, sod = bar_session(stamp[0], stamp[1], self.stamps_tz,
                                       self.stamps)
                if ses >= REFUSE_FROM:
                    self.refused_sessions.add(ses)
                    continue
                if self.allow is not None and not self.allow(ses):
                    self.skipped_sessions.add(ses)
                    continue
                a = aggs.get(ses)
                if a is None:
                    a = aggs[ses] = DayAgg()
                a.add(sod, o, h, lo, c, v)
                m = int(sod // 60)
                self.minute_vol[m] += v
                self.minute_n[m] += 1
                n += 1
        for ses, a in aggs.items():
            self.days[(contract, ses)] = a.finalize()
        self.files.append(dict(file=os.path.basename(path), contract=contract,
                               bars=n, sessions=len(aggs)))

    def open_minute(self):
        """The ET minute of day with the largest jump in average volume
        over the nearest earlier minute that has bars (at most 10
        minutes before it): 570 (09:30) on correctly stamped exports."""
        best, best_m = None, None
        mins = sorted(m for m in self.minute_vol if self.minute_n[m])
        for prev, m in zip(mins, mins[1:]):
            if m - prev > 10:
                continue
            b = self.minute_vol[prev] / self.minute_n[prev]
            if b <= 0:
                continue
            r = (self.minute_vol[m] / self.minute_n[m]) / b
            if best is None or r > best:
                best, best_m = r, m
        return best_m, best

    def check_stamps(self):
        m, ratio = self.open_minute()
        if m is None:
            raise ContextDataError('no consecutive minutes with volume: '
                                   'cannot check the time stamps')
        if m == 570:
            return dict(open_minute='09:30', jump=round(ratio, 2))
        hint = ''
        if m == 569:
            hint = ' The jump is one minute early: the bars look stamped ' \
                   'at their START; rerun with --stamps start.'
        elif m in (570 + 60 * k for k in (-5, -4, 4, 5, 1, -1)):
            hint = ' The jump is whole hours off: the times are probably ' \
                   'not UTC; rerun with --stamps-tz ET if they are Eastern.'
        raise ContextDataError(
            'the cash-open volume jump appears at %02d:%02d ET, not 09:30.%s '
            'Nothing was computed.' % (m // 60, m % 60, hint))


# ---------------------------------------------------------------------
# sessions, the front contract, features and outcomes
# ---------------------------------------------------------------------
def _median(v):
    v = sorted(v)
    return v[len(v) // 2] if v else None


def build_days(days):
    """[day record] in session order: the front contract (previous
    session's volume), the 13 features at 10:30 and the outcome. A day
    is eligible when complete with ATR known; features needing more
    history are None until it exists."""
    by_ses = collections.defaultdict(dict)
    for (c, s), st in days.items():
        by_ses[s][c] = st
    sessions = sorted(by_ses)
    out = []
    prev_front_vol = None
    trs = []                       # true ranges of earlier front days
    ibr, ibv, s830s = [], [], []
    prev_ses = None
    for s in sessions:
        cand = {c: st for c, st in by_ses[s].items() if st['complete']}
        if not cand:
            prev_ses = s
            continue
        if prev_front_vol:
            front = max(cand, key=lambda c: (prev_front_vol.get(c, -1.0),
                                             cand[c]['rth_vol'], c))
        else:
            front = max(cand, key=lambda c: (cand[c]['rth_vol'], c))
        st = cand[front]
        prv = by_ses.get(prev_ses, {}).get(front) if prev_ses else None
        if prv is not None and not prv['complete']:
            prv = None
        pc = prv['rth_close'] if prv else None
        h, lo = st['rth_high'], st['rth_low']
        tr = (max(h, pc) - min(lo, pc)) if pc is not None else h - lo
        atr = sum(trs[-ATR_N:]) / ATR_N if len(trs) >= ATR_N else None
        rec = dict(session=s, month=s[:6], year=s[:4], contract=front)
        f = dict.fromkeys(FEATURES)
        if atr and atr > 0:
            p = st['p1030']
            f['gap'] = None if pc is None else (st['rth_open'] - pc) / atr
            f['ib_move'] = (p - st['rth_open']) / atr
            ibw = st['ib_high'] - st['ib_low']
            f['ib_pos'] = (p - st['ib_low']) / ibw if ibw > 0 else None
            f['vwap_dist'] = (p - st['vwap_1030']) / atr
            f['vwap_slope'] = (st['vwap_1030'] - st['vwap_1000']) / atr
            if prv is not None:
                rng = prv['rth_high'] - prv['rth_low']
                f['open_vs_range'] = (st['rth_open'] - prv['rth_low']) / rng \
                    if rng > 0 else None
                vaw = (prv['vah'] - prv['val']) if prv['vah'] is not None \
                    else None
                f['open_vs_value'] = (st['rth_open'] - prv['val']) / vaw \
                    if vaw else None
                f['prev_day_move'] = (prv['rth_close'] - prv['rth_open']) / \
                    atr
            if st['on_high'] is not None:
                f['on_range'] = (st['on_high'] - st['on_low']) / atr
            if len(ibr) >= MED_N:
                m = _median(ibr[-MED_N:])
                f['ib_range_rel'] = ibw / m if m else None
                mv = _median(ibv[-MED_N:])
                f['rel_vol'] = st['ib_vol'] / mv if mv else None
            if len(trs) >= REGIME_N:
                mt = _median(trs[-REGIME_N:])
                f['atr_rel'] = atr / mt if mt else None
            if st['s830'] is not None and len(s830s) >= MED_N:
                ms = _median(s830s[-MED_N:])
                f['shock830'] = st['s830'] / ms if ms else None
            rec['eligible'] = True
            rec['atr'] = atr
            rec['price_1030'] = p
            # the outcome: everything after 10:30
            rec['y'] = (st['rth_close'] - p) / atr
            rec['y_points'] = st['rth_close'] - p
            full = h - lo
            rec['close_loc'] = (st['rth_close'] - lo) / full if full > 0 \
                else None
            rec['path'] = first_touch(st['post'], p, PATH_ATR * atr)
        else:
            rec['eligible'] = False
        rec['features'] = f
        out.append(rec)
        trs.append(tr)
        ibr.append(st['ib_high'] - st['ib_low'])
        ibv.append(st['ib_vol'])
        if st['s830'] is not None:
            s830s.append(st['s830'])
        prev_front_vol = {c: x['rth_vol'] for c, x in by_ses[s].items()}
        prev_ses = s
    return out


def first_touch(post, p, dist):
    """Which of p + dist and p - dist the post-10:30 bars reach first:
    'UP', 'DOWN', 'BOTH' (one bar spans both), or 'NONE'."""
    for k in range(0, len(post), 2):
        h, lo = post[k], post[k + 1]
        u, d = h >= p + dist, lo <= p - dist
        if u and d:
            return 'BOTH'
        if u:
            return 'UP'
        if d:
            return 'DOWN'
    return 'NONE'


def is_dev(ses):
    return VALIDATION_BEFORE <= ses < REFUSE_FROM


def is_validation(ses):
    return ses < VALIDATION_BEFORE


# ---------------------------------------------------------------------
# the counted search
# ---------------------------------------------------------------------
def enumerate_rules():
    rules = []
    for f in SIGNED + UNSIGNED:
        for tail in ('top', 'bottom'):
            for d in (1, -1):
                rules.append(dict(family='S', parts=[(f, tail, 'decile')],
                                  direction=d))
    feats = SIGNED + UNSIGNED
    for i, f in enumerate(feats):
        for g in feats[i + 1:]:
            for tf in ('top', 'bottom'):
                for tg in ('top', 'bottom'):
                    for d in (1, -1):
                        rules.append(dict(
                            family='P',
                            parts=[(f, tf, 'quintile'), (g, tg, 'quintile')],
                            direction=d))
    for r in rules:
        r['id'] = '%s:%s:%s' % (r['family'], '+'.join(
            '%s.%s.%s' % (f, t, lv[0]) for f, t, lv in r['parts']),
            'long' if r['direction'] > 0 else 'short')
    return rules


def rule_text(r):
    bits = ['%s in its %s %s' % (f, t, '10%' if lv == 'decile' else '20%')
            for f, t, lv in r['parts']]
    return '%s -> %s for the rest of the day' % (
        ' AND '.join(bits), 'LONG' if r['direction'] > 0 else 'SHORT')


def quantile_cuts(recs):
    cuts = {}
    for f in FEATURES:
        vals = sorted(r['features'][f] for r in recs
                      if r['features'].get(f) is not None)
        n = len(vals)
        if n < 50:
            cuts[f] = dict(n=n)
            continue
        q = lambda p: vals[int(p * (n - 1))]     # noqa: E731
        cuts[f] = dict(n=n, decile=(q(0.10), q(0.90)),
                       quintile=(q(0.20), q(0.80)))
    return cuts


def _cut_for(cuts, f, tail, level):
    c = cuts.get(f, {}).get(level)
    if c is None:
        return None
    return c[1] if tail == 'top' else c[0]


def members(recs, f, tail, level, cut, check=True):
    if cut is None:
        return None
    have = [k for k, r in enumerate(recs) if r['features'].get(f) is not None]
    if tail == 'top':
        mem = [k for k in have if recs[k]['features'][f] >= cut]
    else:
        mem = [k for k in have if recs[k]['features'][f] <= cut]
    nominal = DECILE[1] if level == 'decile' else QUINTILE[1]
    if check and (not have or
                  len(mem) > DEGENERATE_FACTOR * nominal * len(have)):
        return None
    return mem


def rule_days(recs, rule, cuts, cache, check=True):
    sets = []
    for f, tail, level in rule['parts']:
        key = (f, tail, level)
        if key not in cache:
            cache[key] = members(recs, f, tail, level,
                                 _cut_for(cuts, f, tail, level), check)
        if cache[key] is None:
            return None
        sets.append(cache[key])
    if len(sets) == 1:
        return sets[0]
    return sorted(set(sets[0]) & set(sets[1]))


def _halves(recs):
    ses = sorted({r['session'] for r in recs})
    half = (len(ses) + 1) // 2
    return {s: (0 if i < half else 1) for i, s in enumerate(ses)}


def day_stats(recs, ks, d, ybar, half_of=None):
    """Month-clustered lift of d x y over d x (the sample's mean y)."""
    ks = [k for k in ks if 'y' in recs[k]]
    rows = [(recs[k]['month'], d * recs[k]['y'], d * ybar,
             d * recs[k]['y_points']) for k in ks]
    st = DI.cluster_stats(rows)
    out = dict(days=st['n'], months=st.get('sessions', 0),
               mean_move_atr=st.get('hit'), baseline_atr=st.get('baseline'),
               lift_atr=st.get('lift'), t=st.get('t'), p=st.get('p'),
               ci95=st.get('ci95'),
               mean_move_points=(round(sum(x[3] for x in rows) / len(rows),
                                       2) if rows else None))
    if half_of is not None:
        hv = []
        for h in (0, 1):
            hs = DI.cluster_stats([x for x, k in zip(rows, ks)
                                   if half_of.get(recs[k]['session']) == h])
            hv.append(dict(days=hs['n'], lift_atr=hs.get('lift')))
        out['halves'] = hv
        out['both_halves_positive'] = all(
            x['days'] >= MIN_HALF and x['lift_atr'] is not None and
            x['lift_atr'] > 0 for x in hv)
    return out


def _eligible(st):
    return (st.get('days', 0) >= MIN_DAYS and
            st.get('months', 0) >= MIN_MONTHS and
            (st.get('lift_atr') or 0) > 0 and st.get('both_halves_positive'))


def search(recs, rules=None, cuts=None):
    """recs: DEV records with outcomes. Returns (tests, cuts, days_of)."""
    rules = enumerate_rules() if rules is None else rules
    cuts = quantile_cuts(recs) if cuts is None else cuts
    ys = [r['y'] for r in recs]
    ybar = sum(ys) / len(ys)
    half_of = _halves(recs)
    cache, tests, days_of = {}, [], {}
    for rule in rules:
        ks = rule_days(recs, rule, cuts, cache)
        days_of[rule['id']] = ks
        if ks is None:
            tests.append(dict(rule=rule['id'], testable=False, p=None))
            continue
        st = day_stats(recs, ks, rule['direction'], ybar, half_of)
        st.update(rule=rule['id'], testable=True)
        tests.append(st)
    q = DI.bh_q([x.get('p') for x in tests], m=len(tests))
    for x, qq in zip(tests, q):
        x['q'] = qq
        x['status'] = ('CANDIDATE' if (x.get('testable') and qq is not None
                                       and qq <= FDR_Q and _eligible(x))
                       else None)
    return tests, cuts, days_of


def nominate(tests, days_of):
    ok = [x for x in tests if x.get('testable') and x.get('p') is not None
          and x['p'] <= NOMINATE_P and _eligible(x)]
    ok.sort(key=lambda x: (x['status'] != 'CANDIDATE', -x['t'], x['rule']))
    chosen = []
    for x in ok:
        if len(chosen) >= NOMINATE_MAX:
            break
        mine = set(days_of[x['rule']])
        if any(len(mine & set(days_of[c['rule']])) >=
               OVERLAP_MAX * len(mine) for c in chosen):
            continue
        chosen.append(x)
    return chosen


def frozen_rule(rule, test, cuts):
    return dict(rule=rule['id'], text=rule_text(rule), family=rule['family'],
                parts=[dict(feature=f, tail=t, level=lv,
                            cut=_cut_for(cuts, f, t, lv))
                       for f, t, lv in rule['parts']],
                direction=rule['direction'],
                validation_before=VALIDATION_BEFORE,
                dev=dict((k, test.get(k)) for k in
                         ('days', 'months', 'mean_move_atr', 'lift_atr', 't',
                          'p', 'q', 'ci95', 'mean_move_points', 'halves',
                          'status')))


def apply_frozen(recs, fr):
    rule = dict(parts=[(p['feature'], p['tail'], p['level'])
                       for p in fr['parts']], direction=fr['direction'])
    cuts = {}
    for p in fr['parts']:
        lo_hi = cuts.setdefault(p['feature'], {}).setdefault(p['level'],
                                                             [None, None])
        lo_hi[1 if p['tail'] == 'top' else 0] = p['cut']
    cuts = {f: {lv: tuple(v) for lv, v in d.items()} for f, d in cuts.items()}
    ks = rule_days(recs, rule, cuts, {}, check=False)
    return ks or []


# ---------------------------------------------------------------------
# descriptive tables
# ---------------------------------------------------------------------
def anatomy(recs):
    out = {}
    for f in FEATURES:
        rows = sorted(((r['features'][f], r) for r in recs
                       if r['features'].get(f) is not None),
                      key=lambda x: x[0])
        n = len(rows)
        if n < 100:
            out[f] = dict(n=n)
            continue
        dec = []
        for k in range(10):
            part = [r for _v, r in rows[k * n // 10:(k + 1) * n // 10]]
            ys = [r['y'] for r in part]
            tr = [r for r in part if r.get('close_loc') is not None]
            dec.append(dict(
                decile=k + 1, lo=round(rows[k * n // 10][0], 3),
                hi=round(rows[(k + 1) * n // 10 - 1][0], 3), days=len(part),
                mean_y_atr=round(sum(ys) / len(ys), 4),
                up_share=round(sum(1 for y in ys if y > 0) / len(ys), 3),
                trend_day_share=round(sum(
                    1 for r in tr if r['close_loc'] >= 1 - TREND_CL or
                    r['close_loc'] <= TREND_CL) / max(len(tr), 1), 3)))
        out[f] = dict(n=n, deciles=dec)
    return out


def base_rates(recs):
    ys = [r['y'] for r in recs]
    tr = [r for r in recs if r.get('close_loc') is not None]
    by_year = collections.defaultdict(list)
    for r in recs:
        by_year[r['year']].append(r['y'])
    paths = collections.Counter(r.get('path') for r in recs)
    return dict(
        days=len(ys), mean_y_atr=round(sum(ys) / len(ys), 4),
        up_share=round(sum(1 for y in ys if y > 0) / len(ys), 3),
        trend_day_share=round(sum(1 for r in tr if r['close_loc'] >=
                                  1 - TREND_CL or r['close_loc'] <= TREND_CL)
                              / max(len(tr), 1), 3),
        first_touch_half_atr=dict(paths),
        by_year={y: dict(days=len(v), mean_y_atr=round(sum(v) / len(v), 4),
                         up_share=round(sum(1 for x in v if x > 0) / len(v),
                                        3))
                 for y, v in sorted(by_year.items())})


def load_calendar(path):
    ev = collections.defaultdict(list)
    for line in open(path):
        parts = [x.strip() for x in line.strip().split(',')]
        if len(parts) >= 2 and len(parts[0]) == 8 and parts[0].isdigit():
            ev[parts[0]].append(parts[1].upper())
    return dict(ev)


def event_breakdown(recs, cal, nominated=()):
    on = [r for r in recs if r['session'] in cal]
    off = [r for r in recs if r['session'] not in cal]
    out = dict(event_days=len(on), other_days=len(off),
               event_base=base_rates(on) if on else None,
               other_base=base_rates(off) if off else None, rules=[])
    for fr in nominated:
        ks = apply_frozen(recs, fr)
        a = [recs[k] for k in ks if recs[k]['session'] in cal]
        b = [recs[k] for k in ks if recs[k]['session'] not in cal]
        d = fr['direction']
        out['rules'].append(dict(
            rule=fr['rule'],
            event_days=len(a), event_mean_atr=round(
                sum(d * r['y'] for r in a) / len(a), 4) if a else None,
            other_days=len(b), other_mean_atr=round(
                sum(d * r['y'] for r in b) / len(b), 4) if b else None))
    return out


# ---------------------------------------------------------------------
# the two modes
# ---------------------------------------------------------------------
def read_days(path, root='NQ', stamps_tz='UTC', stamps='end', allow=None,
              years=None):
    """Read the exports, keeping only sessions `allow` accepts (None:
    every session before REFUSE_FROM), check the stamps, build the
    days. `years` names the kept range in the stop message."""
    rd = Reader(root, stamps_tz, stamps, allow)
    rd.read_path(path)
    if not rd.days:
        raise ContextDataError(
            'these exports hold no %s session %s: download that range of '
            'NQ minute data in NinjaTrader and export it' % (
                root, years or 'before %s' % REFUSE_FROM))
    chk = rd.check_stamps()
    recs = build_days(rd.days)
    if not any(r['eligible'] for r in recs):
        raise ContextDataError('no complete cash session with 14 sessions of '
                               'history %s: nothing to study'
                               % (years or 'in the exports'))
    return rd, chk, recs


def _input_block(rd, chk, recs):
    el = [r for r in recs if r['eligible']]
    return dict(files=rd.files, bad_lines=rd.bad_lines, stamp_check=chk,
                sessions_read=len(recs), sessions_eligible=len(el),
                first_session=el[0]['session'] if el else None,
                last_session=el[-1]['session'] if el else None,
                sessions_refused_from=REFUSE_FROM,
                sessions_refused=len(rd.refused_sessions),
                sessions_skipped_unread=len(rd.skipped_sessions),
                contracts_used=dict(collections.Counter(r['contract']
                                                        for r in el)))


def run_search(path, root='NQ', stamps_tz='UTC', stamps='end',
               calendar=None):
    """DEV only: every bar before VALIDATION_BEFORE is dropped unread,
    so no validation price, feature or outcome can reach the search."""
    rd, chk, recs = read_days(path, root, stamps_tz, stamps, is_dev,
                              'from %s to %s' % (VALIDATION_BEFORE,
                                                 REFUSE_FROM))
    dev = [r for r in recs if r['eligible']]
    rules = enumerate_rules()
    by_id = {r['id']: r for r in rules}
    tests, cuts, days_of = search(dev, rules)
    rep = dict(context=CTX_VERSION, registration=REGISTRATION, mode='search',
               root=root, dev_from=VALIDATION_BEFORE, dev_to=REFUSE_FROM,
               validation_before=VALIDATION_BEFORE,
               input=_input_block(rd, chk, recs), dev_days=len(dev),
               validation_sessions_skipped_unread=len(rd.skipped_sessions),
               availability={f: round(sum(1 for r in dev if r['features'][f]
                                          is not None) / len(dev), 4)
                             for f in FEATURES},
               n_rules=len(rules), cuts=cuts, base=base_rates(dev))
    rep['tests_untestable'] = sum(1 for x in tests if not x.get('testable'))
    rep['candidates'] = [x for x in tests if x.get('status') == 'CANDIDATE']
    rep['top_by_t'] = sorted((x for x in tests if x.get('t') is not None),
                             key=lambda x: -x['t'])[:25]
    rep['tests'] = tests
    nominated = [frozen_rule(by_id[x['rule']], x, cuts)
                 for x in nominate(tests, days_of)]
    rep['nominated'] = nominated
    rep['anatomy'] = anatomy(dev)
    rep['day_type_by_ib_range'] = _ib_table(dev)
    if calendar:
        rep['events'] = event_breakdown(dev, calendar, nominated)
    return rep, nominated, recs


def _ib_table(dev):
    rows = [(r['features']['ib_range_rel'], r) for r in dev
            if r['features'].get('ib_range_rel') is not None and
            r.get('close_loc') is not None]
    rows.sort(key=lambda x: x[0])
    n = len(rows)
    out = []
    for k in range(5):
        part = [r for _v, r in rows[k * n // 5:(k + 1) * n // 5]]
        if not part:
            continue
        out.append(dict(quintile=k + 1, days=len(part),
                        ib_range_rel=(round(rows[k * n // 5][0], 2),
                                      round(rows[(k + 1) * n // 5 - 1][0], 2)),
                        trend_day_share=round(sum(
                            1 for r in part if r['close_loc'] >= 1 - TREND_CL
                            or r['close_loc'] <= TREND_CL) / len(part), 3)))
    return out


def run_evaluate(path, frozen, unblind=False, root='NQ', stamps_tz='UTC',
                 stamps='end'):
    """unblind: the VALIDATION years only (nothing from VALIDATION_BEFORE
    on is read); otherwise DEV only, a reproduction of the search."""
    vb = {fr.get('validation_before') for fr in frozen}
    if vb != {VALIDATION_BEFORE}:
        raise ContextDataError(
            'the nominated rules do not carry this registration\'s split '
            '(validation before %s); they are not a frozen context set'
            % VALIDATION_BEFORE)
    if unblind:
        allow = is_validation
        which = 'VALIDATION (sessions before %s)' % VALIDATION_BEFORE
    else:
        allow = is_dev
        which = 'DEV (%s to %s), a reproduction check' % (VALIDATION_BEFORE,
                                                        REFUSE_FROM)
    rd, chk, recs = read_days(path, root, stamps_tz, stamps, allow,
                              ('before %s' % VALIDATION_BEFORE) if unblind
                              else ('from %s to %s' % (VALIDATION_BEFORE,
                                                       REFUSE_FROM)))
    sample = [r for r in recs if r['eligible']]
    rep = dict(context=CTX_VERSION, registration=REGISTRATION,
               mode='evaluate', unblind=unblind, evaluated_on=which,
               validation_before=VALIDATION_BEFORE,
               input=_input_block(rd, chk, recs),
               days_evaluated=len(sample),
               first_day=sample[0]['session'] if sample else None,
               last_day=sample[-1]['session'] if sample else None,
               base=base_rates(sample) if sample else None, rules=[])
    ybar = sum(r['y'] for r in sample) / len(sample)
    for fr in frozen:
        ks = apply_frozen(sample, fr)
        st = day_stats(sample, ks, fr['direction'], ybar)
        rep['rules'].append(dict(rule=fr['rule'], text=fr.get('text'),
                                 result=st))
    rej = BM.holm([x['result'].get('p') for x in rep['rules']], HOLM_ALPHA)
    for x, rj in zip(rep['rules'], rej):
        s = x['result']
        if s.get('days', 0) < MIN_DAYS:
            v = 'NOT TESTED'
        elif rj and (s.get('lift_atr') or 0) > 0 and s.get('ci95') and \
                s['ci95'][0] > 0:
            v = 'PROMISING'
        else:
            v = 'NO SIGNAL'
        x['verdict'] = v if unblind else v + ' (DEV reproduction, not a ' \
                                             'verdict)'
    return rep


def record_validation_read(rep, path):
    old = dict(reads=[])
    if os.path.exists(path):
        try:
            old = json.load(open(path))
        except Exception:
            pass
    old.setdefault('reads', []).append(dict(
        version=CTX_VERSION, validation_before=rep['validation_before'],
        first_day=rep['first_day'], last_day=rep['last_day'],
        days=rep['days_evaluated'],
        rules=[x['rule'] for x in rep['rules']],
        at=_dt.datetime.now(_dt.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')))
    old['rule'] = ('The context VALIDATION sessions are read once, with the '
                   'committed nominated rules. A later read of the same '
                   'rules repeats that test; a read of NEW rules on the '
                   'same sessions is not a fresh test.')
    json.dump(old, open(path, 'w'), indent=1)
    return len(old['reads'])


def write_days_csv(recs, path, keep):
    with open(path, 'w') as fh:
        fh.write('session,contract,eligible,atr,price_1030,' +
                 ','.join(FEATURES) + '\n')
        for r in recs:
            if not keep(r['session']) or r['session'] >= REFUSE_FROM:
                continue
            f = r['features']
            fh.write('%s,%s,%d,%s,%s,%s\n' % (
                r['session'], r['contract'], int(r['eligible']),
                '' if r.get('atr') is None else '%.4f' % r['atr'],
                '' if r.get('price_1030') is None else r['price_1030'],
                ','.join('' if f[k] is None else '%.6g' % f[k]
                         for k in FEATURES)))


# ---------------------------------------------------------------------
# text
# ---------------------------------------------------------------------
def _f(x, fmt='%+.3f'):
    return '-' if x is None else fmt % x


def text_search(rep):
    i = rep['input']
    b = rep['base']
    lines = ['%s  search  root=%s  registration=%s' % (
        rep['context'], rep['root'], rep['registration']),
        'read %d files; DEV %s .. %s: %d sessions (%d eligible); stamp '
        'check: cash-open jump at %s (x%s)'
        % (len(i['files']), i['first_session'], i['last_session'],
           i['sessions_read'], i['sessions_eligible'],
           i['stamp_check']['open_minute'], i['stamp_check']['jump']),
        'VALIDATION (before %s): %d sessions dropped UNREAD; from %s: %d '
        'sessions refused unread' % (rep['validation_before'],
                                     rep['validation_sessions_skipped_unread'],
                                     i['sessions_refused_from'],
                                     i['sessions_refused']),
        'outcome: (16:00 close - 10:30 price) / ATR14, in the rule\'s '
        'direction, against the DEV average (%s ATR; up on %.1f%% of days; '
        'trend days %.1f%%)' % (_f(b['mean_y_atr']), 100 * b['up_share'],
                                100 * b['trend_day_share']), '',
        'CANDIDATES (q <= %.2f, both halves positive, %d+ days over %d+ '
        'months): %d' % (FDR_Q, MIN_DAYS, MIN_MONTHS,
                         len(rep['candidates'])), '',
        'TOP 25 BY t (most are luck; read q and the halves):']
    for x in rep['top_by_t']:
        hv = x.get('halves') or []
        lines.append('  %-62s days=%-4d mo=%-3d move=%s lift=%s t=%.2f '
                     'p=%.4f q=%.2f halves=%s' % (
                         x['rule'][:62], x['days'], x['months'],
                         _f(x['mean_move_atr']), _f(x['lift_atr']), x['t'],
                         x['p'], x['q'] if x['q'] is not None else 1.0,
                         '/'.join(_f(h['lift_atr']) for h in hv)))
    lines.append('')
    lines.append('NOMINATED for validation (max %d): %d' % (
        NOMINATE_MAX, len(rep['nominated'])))
    for fr in rep['nominated']:
        d = fr['dev']
        lines.append('  [%s] %s' % (d['status'] or 'LEAD: did not pass the '
                                    'luck correction', fr['text']))
        lines.append('     DEV: %s days, %s months, move %s ATR (%s pts), '
                     'lift %s, t=%s, q=%s' % (
                         d['days'], d['months'], _f(d['mean_move_atr']),
                         _f(d['mean_move_points'], '%+.1f'),
                         _f(d['lift_atr']), d['t'],
                         _f(d['q'], '%.2f')))
        for p in fr['parts']:
            lines.append('     %s %s %s: cut %s' % (p['feature'], p['tail'],
                                                    p['level'], p['cut']))
    lines.append('')
    lines.append('TREND DAYS by first-hour range (descriptive):')
    for row in rep['day_type_by_ib_range']:
        lines.append('  quintile %d  IB/median %s..%s  trend days %.1f%%' % (
            row['quintile'], row['ib_range_rel'][0], row['ib_range_rel'][1],
            100 * row['trend_day_share']))
    lines.append('')
    lines.append('Nothing here is a result. Nominated rules are judged once '
                 'on the VALIDATION sessions. No order was placed.')
    return '\n'.join(lines)


def text_evaluate(rep):
    lines = ['%s  evaluate  unblind=%s  on %s' % (
        rep['context'], rep['unblind'], rep['evaluated_on']),
        'days evaluated: %s (%s .. %s)' % (rep['days_evaluated'],
                                           rep.get('first_day'),
                                           rep.get('last_day'))]
    for x in rep['rules']:
        s = x['result']
        lines.append('  %s' % (x.get('text') or x['rule']))
        lines.append('     days=%s months=%s move=%s ATR (%s pts) lift=%s '
                     'ci95=%s p=%s -> %s' % (
                         s['days'], s['months'], _f(s['mean_move_atr']),
                         _f(s['mean_move_points'], '%+.1f'),
                         _f(s['lift_atr']), s.get('ci95'),
                         _f(s.get('p'), '%.4f'), x['verdict']))
    lines.append('No order was placed.')
    return '\n'.join(lines)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0].startswith('--'):
        print(__doc__)
        return 2
    path = argv[0]
    arg = lambda k: argv[argv.index(k) + 1] if k in argv else None  # noqa
    root = arg('--root') or 'NQ'
    stz = (arg('--stamps-tz') or 'UTC').upper()
    stp = (arg('--stamps') or 'end').lower()
    if stz not in ('UTC', 'ET') or stp not in ('end', 'start'):
        print('--stamps-tz is UTC or ET; --stamps is end or start')
        return 2
    out = arg('--out')
    unblind = '--unblind' in argv
    ev = arg('--evaluate')
    if unblind and not ev:
        print('REFUSED: --unblind is only for --evaluate. The search reads '
              'DEV sessions only.')
        return 2
    cal = load_calendar(arg('--calendar')) if arg('--calendar') else None
    try:
        if ev:
            frozen = json.load(open(ev))
            frozen = frozen.get('nominated', frozen) \
                if isinstance(frozen, dict) else frozen
            if unblind:
                print('*** UNBLIND: this read scores the nominated context '
                      'rules on the VALIDATION sessions, once. ***\n')
            rep = run_evaluate(path, frozen, unblind, root, stz, stp)
            print(text_evaluate(rep))
        else:
            rep, nominated, recs = run_search(path, root, stz, stp, cal)
            print(text_search(rep))
            no = arg('--nominated-out')
            if no:
                json.dump(dict(context=CTX_VERSION, registration=REGISTRATION,
                               validation_before=VALIDATION_BEFORE,
                               nominated=nominated),
                          open(no, 'w'), indent=1)
                print('nominated rules -> %s (%d)' % (no, len(nominated)))
            do = arg('--days-out')
            if do:
                write_days_csv(recs, do, is_dev)
                print('per-session features (DEV) -> %s' % do)
    except ContextDataError as exc:
        print('STOPPED: %s' % exc)
        return 2
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\ncontext report -> %s' % out)
    if ev and unblind:
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         EXPOSURE_FILE)
        n = record_validation_read(rep, p)
        print('context validation read recorded -> %s (%d read(s))' % (p, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
