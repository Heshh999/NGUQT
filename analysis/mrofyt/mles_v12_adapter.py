#!/usr/bin/env python3
# ======================================================================
# MLES-CAPTURE-1.2 CANONICAL INGESTION ADAPTER (additive; v1.1 adapter
# untouched). New schema column: captureInstanceId; new quality kinds
# for lifecycle, connection and book-readiness telemetry.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv

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

QUALITY_KINDS = ('SESSION_START', 'SESSION_END', 'CONTRACT_ROLL_START',
                 'CONTRACT_ROLL_END', 'HEARTBEAT', 'CONN_STATUS',
                 'DISCONNECT', 'RECONNECT', 'BOOK_RESYNC_START',
                 'BOOK_READY', 'SHUTDOWN')


def check_header(kind, row):
    if list(row) != HEADERS[kind]:
        raise MalformedHeaderError('%s header mismatch: %r'
                                   % (kind, list(row)))
    return True


def _common(d, kind):
    if d.get('schema') != SCHEMA:
        raise UnknownEnumError('unknown schema %r' % d.get('schema'))
    stream = (d.get('stream') or '').strip().upper()
    if stream != STREAM_OF_FILE[kind]:
        raise UnknownEnumError('stream %r in %s file' % (stream, kind))
    return dict(
        schema=d['schema'],
        capture_instance_id=d['captureInstanceId'],
        run_id=d['runId'], seg_id=AD11._int(d['segId'], 'segId'),
        session=d['session'], instrument=d['instrument'],
        contract=d['contract'], stream=stream,
        event_seq=AD11._int(d['eventSeq'], 'eventSeq'),
        stream_seq=AD11._int(d['streamSeq'], 'streamSeq'),
        t_recv=parse_iso(d['tRecvUtc']), t_exch=parse_iso(d['tExchUtc']),
        t_mono=AD11._int(d['tMono'], 'tMono'),
        flags=(d.get('flags') or '').strip())


def parse_file(path, kind):
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
            out.append(ev)
    return out


order_events = AD11.order_events
