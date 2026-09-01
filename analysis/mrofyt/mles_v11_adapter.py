#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.5 — CANONICAL INGESTION ADAPTER for MLES-CAPTURE-1.1
# Parses the recorder's ACTUAL emitted format: ISO-8601 timestamps
# (never float()), explicit enum normalization, hard rejection of
# unknown enum values. Additive; predecessors untouched.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING. SUBMITS NO ORDERS.
# ======================================================================
import csv
import datetime as _dt

SCHEMA = 'MLES-CAPTURE-1.1'

HEADER_COMMON = ['schema', 'runId', 'segId', 'session', 'instrument',
                 'contract', 'stream', 'eventSeq', 'streamSeq',
                 'tRecvUtc', 'tExchUtc', 'tMono']
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

STREAM_OF_FILE = {'quotes': 'QUOTE', 'trades': 'TRADE',
                  'depth': 'DEPTH', 'quality': 'QUALITY'}

_SIDES = {'BID': 'BID', 'B': 'BID', 'ASK': 'ASK', 'A': 'ASK'}
_ACTIONS = {'ADD': 'ADD', 'INSERT': 'ADD',
            'UPDATE': 'UPDATE', 'CHANGE': 'UPDATE',
            'REMOVE': 'REMOVE', 'DELETE': 'REMOVE'}
_STREAMS = ('QUOTE', 'TRADE', 'DEPTH', 'QUALITY')
_AGGR_INF = ('BUY', 'SELL', '')
_AGGR_CONF = ('HIGH', 'LOW', 'NONE', '')


class UnknownEnumError(ValueError):
    """Raised instead of silently ignoring an unrecognized enum."""


class MalformedHeaderError(ValueError):
    pass


# ---------------------------------------------------------------------
# ISO-8601 parsing WITHOUT float(): the recorder emits
# "yyyy-MM-ddTHH:mm:ss.fffffffZ" (7 fractional digits + Z), which
# datetime.fromisoformat rejects on most versions.
# ---------------------------------------------------------------------
def parse_iso(s):
    if s is None:
        return None
    s = s.strip()
    if not s:
        return None
    tz = _dt.timezone.utc
    if s.endswith('Z') or s.endswith('z'):
        s = s[:-1]
    elif '+' in s[10:]:
        base, off = s.rsplit('+', 1)
        hh, _, mm = off.partition(':')
        tz = _dt.timezone(_dt.timedelta(hours=int(hh),
                                        minutes=int(mm or '0')))
        s = base
    date_part, _, time_part = s.partition('T')
    if not time_part:
        raise ValueError('not an ISO-8601 datetime: %r' % s)
    y, mo, d = date_part.split('-')
    hms, dot, frac = time_part.partition('.')
    hh, mi, ss = hms.split(':')
    if dot:
        digits = ''.join(ch for ch in frac if ch.isdigit())
        micro = int((digits + '000000')[:6])      # truncate, never round
    else:
        micro = 0
    return _dt.datetime(int(y), int(mo), int(d), int(hh), int(mi),
                        int(ss), micro, tzinfo=tz)


def _num(v):
    """Numeric field: empty -> None. Timestamps never pass through here."""
    if v is None:
        return None
    v = v.strip()
    if v == '':
        return None
    return float(v)


def _int(v, field):
    v = (v or '').strip()
    if v == '':
        raise UnknownEnumError('empty integer field %s' % field)
    return int(v)


def _side(v):
    k = (v or '').strip().upper()
    if k not in _SIDES:
        raise UnknownEnumError('unknown side %r' % v)
    return _SIDES[k]


def _action(v):
    k = (v or '').strip().upper()
    if k not in _ACTIONS:
        raise UnknownEnumError('unknown depth action %r' % v)
    return _ACTIONS[k]


def check_header(kind, row):
    want = HEADERS[kind]
    if list(row) != want:
        raise MalformedHeaderError(
            '%s header mismatch: got %r' % (kind, list(row)))
    return True


# ---------------------------------------------------------------------
# canonical event
# ---------------------------------------------------------------------
def _common(d, kind):
    if d.get('schema') != SCHEMA:
        raise UnknownEnumError('unknown schema %r' % d.get('schema'))
    stream = (d.get('stream') or '').strip().upper()
    if stream not in _STREAMS:
        raise UnknownEnumError('unknown stream %r' % d.get('stream'))
    if stream != STREAM_OF_FILE[kind]:
        raise UnknownEnumError('stream %r in %s file' % (stream, kind))
    return dict(
        schema=d['schema'], run_id=d['runId'],
        seg_id=_int(d.get('segId'), 'segId'),
        session=d['session'], instrument=d['instrument'],
        contract=d['contract'], stream=stream,
        event_seq=_int(d.get('eventSeq'), 'eventSeq'),
        stream_seq=_int(d.get('streamSeq'), 'streamSeq'),
        t_recv=parse_iso(d.get('tRecvUtc')),
        t_exch=parse_iso(d.get('tExchUtc')),
        t_mono=_int(d.get('tMono'), 'tMono'),
        flags=(d.get('flags') or '').strip())


def parse_file(path, kind):
    """Parse one recorder file into canonical events (file order)."""
    out = []
    with open(path, newline='') as fh:
        rdr = csv.reader(fh)
        try:
            head = next(rdr)
        except StopIteration:
            raise MalformedHeaderError('%s is empty' % path)
        check_header(kind, head)
        names = HEADERS[kind]
        for raw in rdr:
            if not raw:
                continue
            if len(raw) != len(names):
                raise MalformedHeaderError(
                    '%s: expected %d columns, got %d'
                    % (path, len(names), len(raw)))
            d = dict(zip(names, raw))
            ev = _common(d, kind)
            if kind == 'quotes':
                ev.update(side=_side(d['side']), px=_num(d['px']),
                          sz=_num(d['sz']), bid_px=_num(d['bidPx']),
                          bid_sz=_num(d['bidSz']), ask_px=_num(d['askPx']),
                          ask_sz=_num(d['askSz']))
            elif kind == 'trades':
                inf = (d['aggrInf'] or '').strip().upper()
                conf = (d['aggrConf'] or '').strip().upper()
                if inf not in _AGGR_INF:
                    raise UnknownEnumError('unknown aggrInf %r' % d['aggrInf'])
                if conf not in _AGGR_CONF:
                    raise UnknownEnumError('unknown aggrConf %r'
                                           % d['aggrConf'])
                ev.update(px=_num(d['px']), sz=_num(d['sz']),
                          bid_px=_num(d['bidPx']), bid_sz=_num(d['bidSz']),
                          ask_px=_num(d['askPx']), ask_sz=_num(d['askSz']),
                          aggr_raw=(d['aggrRaw'] or '').strip(),
                          aggr_inf=inf, aggr_method=d['aggrMethod'],
                          aggr_conf=conf)
            elif kind == 'depth':
                bt = (d['bookType'] or '').strip().upper()
                if bt not in ('MBP', 'MBO'):
                    raise UnknownEnumError('unknown bookType %r'
                                           % d['bookType'])
                ev.update(book_type=bt, action=_action(d['action']),
                          side=_side(d['side']),
                          level=_int(d['level'], 'level'),
                          px=_num(d['px']), sz=_num(d['sz']))
            else:
                ev.update(kind=(d['kind'] or '').strip(),
                          detail=(d['detail'] or '').strip())
            out.append(ev)
    return out


def order_events(*event_lists):
    """Global causal ordering by the recorder's single monotonic
    eventSeq. Returns (ordered, problems)."""
    all_ev = [e for lst in event_lists for e in lst]
    all_ev.sort(key=lambda e: e['event_seq'])
    problems = []
    seen = set()
    prev = None
    for e in all_ev:
        s = e['event_seq']
        if s in seen:
            problems.append(('DUPLICATE_EVENT_SEQ', s))
        seen.add(s)
        if prev is not None and s > prev + 1:
            problems.append(('EVENT_SEQ_GAP', (prev, s)))
        prev = s
    return all_ev, problems
