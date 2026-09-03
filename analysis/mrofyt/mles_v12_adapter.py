#!/usr/bin/env python3
# ======================================================================
# MLES-CAPTURE-1.2 CANONICAL INGESTION ADAPTER (additive; v1.1 adapter
# untouched). New schema column: captureInstanceId; new quality kinds
# for lifecycle, connection and book-readiness telemetry.
#
# Build 1.2.1 (streaming repair): the first genuine session produced a
# 5.2 GB / 25M-row depth file, and parse_file() (a list of dicts) would
# need >15 GB of RAM. iter_file() streams one row at a time; parse_file
# is kept for small inputs and existing tests. merge_run() heap-merges
# the four streams of a run by eventSeq in O(1) memory. lite=True keeps
# timestamps as float epoch seconds via a fixed-format fast path
# (falls back to the ISO parser on anything unexpected).
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv
import datetime as _dt
import heapq
import os

import mles_v11_adapter as AD11

SCHEMA = 'MLES-CAPTURE-1.2'
parse_iso = AD11.parse_iso                 # ISO-8601, no float(), reuse
UnknownEnumError = AD11.UnknownEnumError
MalformedHeaderError = AD11.MalformedHeaderError

HEADER_COMMON = ['schema', 'captureInstanceId', 'runId', 'segId',
                 'session', 'instrument', 'contract', 'stream',
                 'eventSeq', 'streamSeq', 'tRecvUtc', 'tExchUtc',
                 'tMono']
HEADERS = {
    'quotes': HEADER_COMMON + ['side', 'px', 'sz', 'bidPx', 'bidSz',
                               'askPx', 'askSz', 'flags'],
    'trades': HEADER_COMMON + ['px', 'sz', 'bidPx', 'bidSz', 'askPx',
                               'askSz', 'aggrRaw', 'aggrInf',
                               'aggrMethod', 'aggrConf', 'flags'],
    'depth':  HEADER_COMMON + ['bookType', 'action', 'side', 'level',
                               'px', 'sz', 'flags'],
    'quality': HEADER_COMMON + ['kind', 'detail'],
}
STREAM_OF_FILE = dict(quotes='QUOTE', trades='TRADE', depth='DEPTH',
                      quality='QUALITY')
STREAMS = ('quotes', 'trades', 'depth', 'quality')

QUALITY_KINDS = ('SESSION_START', 'SESSION_END', 'CONTRACT_ROLL_START',
                 'CONTRACT_ROLL_END', 'HEARTBEAT', 'CONN_STATUS',
                 'DISCONNECT', 'RECONNECT', 'BOOK_RESYNC_START',
                 'BOOK_READY', 'SHUTDOWN')

_EPOCH = _dt.datetime(1970, 1, 1, tzinfo=_dt.timezone.utc)
_day_cache = {}


def iso_to_epoch(s):
    """Fast path for the recorder's fixed ISO-8601 UTC format
    'YYYY-MM-DDTHH:MM:SS[.fffffff]Z'. Truncates (never rounds) the
    fraction exactly like parse_iso. Returns None for blank; falls back
    to parse_iso for any other shape."""
    if not s:
        return None
    if len(s) >= 20 and s[10] == 'T' and s[-1] == 'Z' and s[4] == '-' \
            and s[13] == ':' and s[16] == ':':
        day = s[:10]
        base = _day_cache.get(day)
        if base is None:
            try:
                d = _dt.date(int(day[:4]), int(day[5:7]), int(day[8:10]))
            except ValueError:
                return _to_epoch(parse_iso(s))
            base = (d - _EPOCH.date()).days * 86400.0
            _day_cache[day] = base
        try:
            secs = int(s[11:13]) * 3600 + int(s[14:16]) * 60 + int(s[17:19])
            frac = 0.0
            if len(s) > 20 and s[19] == '.':
                digits = s[20:-1]
                if digits.isdigit():
                    frac = int((digits + '000000')[:6]) / 1e6
                else:
                    return _to_epoch(parse_iso(s))
            elif len(s) != 20:
                return _to_epoch(parse_iso(s))
            return base + secs + frac
        except ValueError:
            return _to_epoch(parse_iso(s))
    return _to_epoch(parse_iso(s))


def _to_epoch(dt):
    return None if dt is None else (dt - _EPOCH).total_seconds()


def check_header(kind, row):
    if list(row) != HEADERS[kind]:
        raise MalformedHeaderError('%s header mismatch: %r'
                                   % (kind, list(row)))
    return True


def _common(d, kind, lite=False):
    if d.get('schema') != SCHEMA:
        raise UnknownEnumError('unknown schema %r' % d.get('schema'))
    stream = (d.get('stream') or '').strip().upper()
    if stream != STREAM_OF_FILE[kind]:
        raise UnknownEnumError('stream %r in %s file' % (stream, kind))
    if lite:
        t_recv = iso_to_epoch(d['tRecvUtc'].strip())
        t_exch = iso_to_epoch(d['tExchUtc'].strip())
    else:
        t_recv = parse_iso(d['tRecvUtc'])
        t_exch = parse_iso(d['tExchUtc'])
    return dict(
        schema=d['schema'],
        capture_instance_id=d['captureInstanceId'],
        run_id=d['runId'], seg_id=AD11._int(d['segId'], 'segId'),
        session=d['session'], instrument=d['instrument'],
        contract=d['contract'], stream=stream,
        event_seq=AD11._int(d['eventSeq'], 'eventSeq'),
        stream_seq=AD11._int(d['streamSeq'], 'streamSeq'),
        t_recv=t_recv, t_exch=t_exch,
        t_mono=AD11._int(d['tMono'], 'tMono'),
        flags=(d.get('flags') or '').strip())


def _decorate(ev, d, kind):
    if kind == 'quotes':
        ev.update(side=AD11._side(d['side']),
                  px=AD11._num(d['px']), sz=AD11._num(d['sz']),
                  bid_px=AD11._num(d['bidPx']),
                  bid_sz=AD11._num(d['bidSz']),
                  ask_px=AD11._num(d['askPx']),
                  ask_sz=AD11._num(d['askSz']))
    elif kind == 'trades':
        inf = (d['aggrInf'] or '').strip().upper()
        conf = (d['aggrConf'] or '').strip().upper()
        if inf not in AD11._AGGR_INF:
            raise UnknownEnumError('unknown aggrInf %r' % inf)
        if conf not in AD11._AGGR_CONF:
            raise UnknownEnumError('unknown aggrConf %r' % conf)
        ev.update(px=AD11._num(d['px']), sz=AD11._num(d['sz']),
                  bid_px=AD11._num(d['bidPx']),
                  bid_sz=AD11._num(d['bidSz']),
                  ask_px=AD11._num(d['askPx']),
                  ask_sz=AD11._num(d['askSz']),
                  aggr_raw=(d['aggrRaw'] or '').strip(),
                  aggr_inf=inf, aggr_method=d['aggrMethod'],
                  aggr_conf=conf)
    elif kind == 'depth':
        bt = (d['bookType'] or '').strip().upper()
        if bt not in ('MBP', 'MBO'):
            raise UnknownEnumError('unknown bookType %r' % bt)
        ev.update(book_type=bt,
                  action=AD11._action(d['action']),
                  side=AD11._side(d['side']),
                  level=AD11._int(d['level'], 'level'),
                  px=AD11._num(d['px']), sz=AD11._num(d['sz']))
    else:
        kd = (d['kind'] or '').strip()
        if kd not in QUALITY_KINDS:
            raise UnknownEnumError('unknown quality kind %r' % kd)
        ev.update(kind=kd, detail=(d['detail'] or '').strip())
    return ev


def iter_file(path, kind, lite=False):
    """Stream one recorder CSV row at a time (O(1) memory). Header is
    validated before the first row. Row-shape and enum errors raise
    exactly as parse_file does."""
    names = HEADERS[kind]
    n = len(names)
    with open(path, newline='') as fh:
        rdr = csv.reader(fh)
        try:
            head = next(rdr)
        except StopIteration:
            raise MalformedHeaderError('%s is empty' % path)
        check_header(kind, head)
        for raw in rdr:
            if not raw:
                continue
            if len(raw) != n:
                raise MalformedHeaderError(
                    '%s: expected %d columns, got %d'
                    % (path, n, len(raw)))
            d = dict(zip(names, raw))
            yield _decorate(_common(d, kind, lite), d, kind)


def parse_file(path, kind, lite=False):
    """Materialized list — small files and tests only. A full session
    depth file (25M rows) must go through iter_file/merge_run."""
    return list(iter_file(path, kind, lite))


def _seq_key(ev):
    return ev['event_seq']


def merge_streams(iters):
    """Heap-merge already event-seq-sorted iterators; O(k) memory."""
    return heapq.merge(*iters, key=_seq_key)


def run_paths(manifest, base_dir):
    """{kind: path} for the streams a manifest declares present."""
    out = {}
    for kind in STREAMS:
        blk = manifest.get(kind)
        if isinstance(blk, dict) and blk.get('present') and blk.get('file'):
            out[kind] = os.path.join(base_dir, blk['file'])
    return out


def merge_run(paths, lite=True, kinds=STREAMS):
    """Stream every event of a run in global eventSeq order across the
    four files. paths: {kind: path}. Each yielded dict carries 'stream'
    (QUOTE/TRADE/DEPTH/QUALITY)."""
    its = [iter_file(paths[k], k, lite) for k in kinds if k in paths]
    return merge_streams(its)


order_events = AD11.order_events
