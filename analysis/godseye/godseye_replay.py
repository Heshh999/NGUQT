#!/usr/bin/env python3
# ======================================================================
# MROF GOD'S EYE VIEW — BOUNDED REPLAY READER (exposed sessions only)
#
# Reads a short window of raw recorder rows around a decision window,
# never a whole file: each stream is binary-searched by byte offset on
# tRecvUtc (rows are written in receive order; the auditor checks it),
# then read forward under a hard row cap. Every read is read-only and
# every call is refused by the policy unless the session is EXPOSED.
#
# The depth book is rebuilt with the runner's own frozen KLevelBook, so
# what is displayed is what the detectors saw. A level the warm-up
# never touched is reported as unknown, never invented; a row flagged
# DATA_SUPPRESSED or DISCONNECTED is reported as a gap.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
for _p in ('..', '../mrofyt', '../mrof', '../rvmr'):
    sys.path.insert(0, os.path.normpath(os.path.join(HERE, _p)))

import mles_v12_adapter as AD          # noqa: E402
import mrofyt_signals as SIG           # noqa: E402

REPLAY_VERSION = 'MROF-GODSEYE-REPLAY-1.0'
MAX_ROWS_PER_STREAM = 250000      # hard cap; a 2-minute NQ depth window
#                                  is ~120k rows, so this is not a limit
#                                  in normal use and a wall in abuse
SNAP_S = 0.25                     # depth snapshot cadence
PRE_S = 60.0                      # warm-up and context before the window
POST_S = 60.0
CANDLE_CONTEXT_S = 15 * 60.0      # 1-minute candles either side
BOOK_K = 10
_RECV = AD.HEADER_COMMON.index('tRecvUtc')


class ReplayError(ValueError):
    pass


# ---------------------------------------------------------------------
# byte-offset search
# ---------------------------------------------------------------------
def _row_at(fh, pos, size):
    """(line_start, line_bytes) of the first complete line at or after
    byte `pos`; (None, None) at end of file."""
    fh.seek(pos)
    if pos:
        fh.readline()                     # discard the cut line
    start = fh.tell()
    if start >= size:
        return None, None
    return start, fh.readline()


def _recv_of(line, ncols):
    try:
        row = next(csv.reader([line.rstrip(b'\r\n').decode()]), None)
        if row is None or len(row) != ncols:
            return None
        return AD.iso_to_epoch(row[_RECV].strip())
    except Exception:
        return None


def find_offset(path, kind, t_target):
    """Byte offset of the first data row whose tRecvUtc >= t_target
    (or of the row just before if timestamps are missing there).
    O(log n) seeks, each reading one line."""
    ncols = len(AD.HEADERS[kind])
    size = os.path.getsize(path)
    with open(path, 'rb') as fh:
        head = fh.readline()
        lo, hi = len(head), size
        best = size                       # nothing at or after the target
        while lo < hi:
            mid = (lo + hi) // 2
            start, line = _row_at(fh, mid, size)
            if start is None or start >= hi:
                hi = mid
                continue
            t = _recv_of(line, ncols)
            if t is None:
                # unparseable line (mid-write, corrupt): search left; the
                # forward read skips rows before the target anyway
                hi = mid
                continue
            if t < t_target:
                lo = start + len(line)
            else:
                best = start
                hi = mid
        return best


def read_rows(path, kind, t0, t1, max_rows=MAX_ROWS_PER_STREAM):
    """Parsed rows with t0 <= tRecvUtc <= t1, bounded. Returns
    (rows, info) where info says how many bytes were read and whether
    the cap cut the read short."""
    names = AD.HEADERS[kind]
    n = len(names)
    off = find_offset(path, kind, t0)
    rows = []
    nbytes = 0
    truncated = False
    with open(path, 'rb') as fh:
        fh.seek(off)
        for raw in fh:
            nbytes += len(raw)
            try:
                cols = next(csv.reader([raw.rstrip(b'\r\n').decode()]), None)
            except Exception:
                continue
            if cols is None or len(cols) != n:
                continue                  # a cut or corrupt line: skip
            d = dict(zip(names, cols))
            try:
                ev = AD._decorate(AD._common(d, kind, lite=True), d, kind)
            except (AD.UnknownEnumError, ValueError, KeyError):
                continue
            t = ev['t_recv']
            if t is None or t < t0:
                continue
            if t > t1:
                break
            rows.append(ev)
            if len(rows) >= max_rows:
                truncated = True
                break
    return rows, dict(bytes_read=nbytes, rows=len(rows), truncated=truncated,
                      offset=off)


# ---------------------------------------------------------------------
# bundle: what the replay view shows for one decision window
# ---------------------------------------------------------------------
def _gaps(rows):
    """Intervals whose rows carry DATA_SUPPRESSED or DISCONNECTED."""
    out = []
    cur = None
    for e in rows:
        f = e.get('flags') or ''
        bad = 'DATA_SUPPRESSED' in f or 'DISCONNECTED' in f
        if bad:
            if cur is None:
                cur = [e['t_recv'], e['t_recv']]
            else:
                cur[1] = e['t_recv']
        elif cur is not None:
            out.append(cur)
            cur = None
    if cur is not None:
        out.append(cur)
    return out


def _candles(trades, minute_s=60.0):
    bars = []
    cur = None
    for e in trades:
        m = int(e['t_recv'] // minute_s)
        px, sz = e['px'], e['sz'] or 0.0
        if px is None:
            continue
        if cur is None or cur['m'] != m:
            if cur is not None:
                bars.append(cur)
            cur = dict(m=m, t_open=m * minute_s, o=px, h=px, l=px, c=px,
                       v=sz, n=1)
        else:
            cur['h'] = max(cur['h'], px)
            cur['l'] = min(cur['l'], px)
            cur['c'] = px
            cur['v'] += sz
            cur['n'] += 1
    if cur is not None:
        bars.append(cur)
    return bars


def _book_snapshot(book):
    def side(lv):
        return [[px, sz] for px, sz in lv[:BOOK_K]]
    return side(book.bid), side(book.ask)


def build_bundle(paths, t_start, t_end, pre_s=PRE_S, post_s=POST_S,
                 candle_context_s=CANDLE_CONTEXT_S, snap_s=SNAP_S,
                 max_rows=MAX_ROWS_PER_STREAM):
    """paths: {kind: path} for ONE run. The caller has already passed
    the policy check for that run's session."""
    t0, t1 = t_start - pre_s, t_end + post_s
    info = {}
    trades, info['trades'] = read_rows(paths['trades'], 'trades',
                                       t_start - candle_context_s,
                                       t_end + candle_context_s, max_rows)
    quotes, info['quotes'] = read_rows(paths['quotes'], 'quotes', t0, t1,
                                       max_rows)
    depth, info['depth'] = read_rows(paths['depth'], 'depth', t0, t1,
                                     max_rows)
    quality, info['quality'] = read_rows(paths['quality'], 'quality',
                                         t0 - 600, t1, max_rows)

    # tape and quotes inside the display window only
    tape = [[round(e['t_recv'], 3), e['px'], e['sz'], e.get('aggr_inf'),
             e.get('aggr_conf'), e.get('flags') or '']
            for e in trades if t0 <= e['t_recv'] <= t1 and e['px'] is not None]
    bbo = []
    last = None
    for e in quotes:
        cur = (e['bid_px'], e['bid_sz'], e['ask_px'], e['ask_sz'])
        if cur != last:
            bbo.append([round(e['t_recv'], 3)] + list(cur))
            last = cur
    # depth: the frozen book, snapshotted on a fixed cadence
    book = SIG.KLevelBook(BOOK_K)
    snaps = []
    next_snap = t0
    seen_levels = dict(bid=set(), ask=set())
    for e in depth:
        while e['t_recv'] >= next_snap and next_snap <= t1:
            b, a = _book_snapshot(book)
            snaps.append([round(next_snap, 3), b, a])
            next_snap += snap_s
        side = e['side'].lower()
        book.apply(e['action'], side, e['level'], e['px'], e['sz'] or 0.0)
        seen_levels[side].add(e['level'])
    while next_snap <= t1:
        b, a = _book_snapshot(book)
        snaps.append([round(next_snap, 3), b, a])
        next_snap += snap_s
    qual = [[round(e['t_recv'], 3), e['kind'], e.get('detail', '')[:120]]
            for e in quality]
    return dict(
        replay=REPLAY_VERSION,
        window=dict(t_start=t_start, t_end=t_end, display_from=t0,
                    display_to=t1, decision_s=t_end - t_start),
        candles=_candles(trades),
        tape=tape, bbo=bbo, depth_snapshots=snaps,
        depth_levels_seen=dict(bid=sorted(seen_levels['bid']),
                               ask=sorted(seen_levels['ask'])),
        depth_note='book rebuilt with the runner\'s frozen KLevelBook from '
                   '%.0f s before the window; a level never updated in that '
                   'time is absent, not invented' % pre_s,
        quality=qual,
        gaps=_gaps(quotes) + _gaps(trades),
        book_invalid=[q for q in qual if q[1] in ('DISCONNECT',
                                                  'BOOK_RESYNC_START',
                                                  'BOOK_READY')],
        read=info,
        bytes_read=sum(v['bytes_read'] for v in info.values()),
        truncated=any(v['truncated'] for v in info.values()))
