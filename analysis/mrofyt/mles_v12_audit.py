#!/usr/bin/env python3
# ======================================================================
# MLES-CAPTURE-1.2 INTEGRITY AUDIT (additive; v1.1 auditor untouched).
# The MANIFEST is the authoritative entrypoint. Outcome-blind.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import glob
import json
import os

import mles_v11_audit as AU11
import mles_v12_adapter as AD

sha256 = AU11.sha256
REQUIRED_STREAMS = ('quotes', 'trades', 'depth', 'quality')
REQUIRED_INSTRUMENTS = ('NQ', 'MNQ')
OPTIONAL_INSTRUMENTS = ('ES',)
ZERO = ('gaps', 'duplicates', 'reversals', 'queueOverflows',
        'droppedRows', 'writeErrors')
MIN_OVERLAP_FRAC = 0.5


def _fail(fails, code, detail=''):
    fails.append((code, detail))


def audit_run(manifest_path):
    fails = []
    info = {}
    try:
        man = json.load(open(manifest_path))
    except Exception as exc:
        return dict(ok=False,
                    failures=[('MANIFEST_UNREADABLE', str(exc))],
                    info=info)
    if man.get('schema') != AD.SCHEMA:
        return dict(ok=False,
                    failures=[('SCHEMA_MISMATCH', str(man.get('schema')))],
                    info=info)
    base = os.path.dirname(os.path.abspath(manifest_path))
    cid = man.get('captureInstanceId')
    rid, ses = man.get('runId'), man.get('session')
    inst, con = man.get('instrument'), man.get('contract')
    info.update(capture_instance_id=cid, run_id=rid, session=ses,
                instrument=inst, contract=con,
                first_recv=AD.parse_iso(man.get('firstRecvUtc') or ''),
                last_recv=AD.parse_iso(man.get('lastRecvUtc') or ''))

    events = {}
    referenced = []
    for stream in REQUIRED_STREAMS:
        blk = man.get(stream)
        if not isinstance(blk, dict) or not blk.get('present'):
            _fail(fails, 'MISSING_REQUIRED_STREAM', stream)
            continue
        path = os.path.join(base, blk.get('file', ''))
        referenced.append(blk.get('file', ''))
        if not os.path.exists(path):
            _fail(fails, 'MISSING_FILE', blk.get('file', ''))
            continue
        if os.path.getsize(path) != blk.get('bytes'):
            _fail(fails, 'BYTE_SIZE_MISMATCH', stream)
        if sha256(path) != blk.get('sha256'):
            _fail(fails, 'HASH_MISMATCH', stream)
        try:
            evs = AD.parse_file(path, stream)
        except AD.MalformedHeaderError as exc:
            _fail(fails, 'MALFORMED_HEADER', '%s: %s' % (stream, exc))
            continue
        except AD.UnknownEnumError as exc:
            _fail(fails, 'UNKNOWN_ENUM', '%s: %s' % (stream, exc))
            continue
        if len(evs) != blk.get('rows'):
            _fail(fails, 'ROW_COUNT_MISMATCH',
                  '%s file %d vs manifest %s'
                  % (stream, len(evs), blk.get('rows')))
        events[stream] = evs
    info['referenced_files'] = referenced
    if not events:
        return dict(ok=False, failures=fails, info=info)

    # identity on EVERY row
    for stream, evs in events.items():
        for field, want, code in (
                ('capture_instance_id', cid, 'MIXED_CAPTURE_INSTANCE'),
                ('run_id', rid, 'MIXED_RUN'),
                ('session', ses, 'MIXED_SESSION'),
                ('instrument', inst, 'MIXED_INSTRUMENT'),
                ('contract', con, 'MIXED_CONTRACT')):
            for e in evs:
                if e[field] != want:
                    _fail(fails, code, '%s: %r' % (stream, e[field]))
                    break

    # per-file event-seq monotonic + per-run streamSeq reset/contiguity
    STREAM_KEYS = dict(quotes=('firstQuoteSeq', 'lastQuoteSeq'),
                       trades=('firstTradeSeq', 'lastTradeSeq'),
                       depth=('firstDepthSeq', 'lastDepthSeq'),
                       quality=('firstQualitySeq', 'lastQualitySeq'))
    for stream, evs in events.items():
        prev = None
        for e in evs:
            if prev is not None and e['event_seq'] <= prev:
                _fail(fails, 'SEQUENCE_REVERSAL'
                      if e['event_seq'] < prev else 'DUPLICATE_EVENT_SEQ',
                      '%s: %d after %d' % (stream, e['event_seq'], prev))
                break
            prev = e['event_seq']
        if evs and evs[0]['stream_seq'] != 1:
            _fail(fails, 'STREAM_SEQ_NOT_RESET',
                  '%s starts at %d' % (stream, evs[0]['stream_seq']))
        prevs = None
        for e in evs:
            if prevs is not None and e['stream_seq'] != prevs + 1:
                _fail(fails, 'STREAM_SEQ_BREAK', stream)
                break
            prevs = e['stream_seq']
        fk, lk = STREAM_KEYS[stream]
        if evs:
            if evs[0]['stream_seq'] != man.get(fk):
                _fail(fails, 'STREAM_FIRST_SEQ_MISMATCH', stream)
            if evs[-1]['stream_seq'] != man.get(lk):
                _fail(fails, 'STREAM_LAST_SEQ_MISMATCH', stream)

    # global ordering, boundaries, clocks, segments
    all_ev = sorted((e for evs in events.values() for e in evs),
                    key=lambda e: e['event_seq'])
    info['events'] = len(all_ev)
    info['event_seqs'] = [e['event_seq'] for e in all_ev]
    if all_ev:
        if all_ev[0]['event_seq'] != man.get('firstEventSeq'):
            _fail(fails, 'FIRST_EVENT_SEQ_MISMATCH',
                  str(all_ev[0]['event_seq']))
        if all_ev[-1]['event_seq'] != man.get('lastEventSeq'):
            _fail(fails, 'LAST_EVENT_SEQ_MISMATCH',
                  str(all_ev[-1]['event_seq']))
        prev_t = prev_m = None
        for e in all_ev:
            if e['t_recv'] is None:
                _fail(fails, 'MISSING_RECV_TIMESTAMP',
                      str(e['event_seq']))
                break
            if prev_t is not None and e['t_recv'] < prev_t:
                _fail(fails, 'RECV_TIMESTAMP_REVERSAL',
                      str(e['event_seq']))
                break
            if prev_m is not None and e['t_mono'] < prev_m:
                _fail(fails, 'MONO_REVERSAL', str(e['event_seq']))
                break
            prev_t, prev_m = e['t_recv'], e['t_mono']
        segs = [e['seg_id'] for e in all_ev]
        if min(segs) != man.get('firstSegId') or \
                max(segs) != man.get('lastSegId') or \
                max(segs) != man.get('connectionSegments'):
            _fail(fails, 'SEG_COUNT_MISMATCH',
                  'rows %d..%d vs manifest %s..%s/%s'
                  % (min(segs), max(segs), man.get('firstSegId'),
                     man.get('lastSegId'), man.get('connectionSegments')))
        # segments are a worker-side annotation stamped at write
        # time: non-decreasing in each file's write order (the queue
        # can lag a reconnect, so global seq order is NOT the check)
        for stream, evs in events.items():
            prev_s = None
            for e in evs:
                if prev_s is not None and e['seg_id'] < prev_s:
                    _fail(fails, 'SEG_REVERSAL',
                          '%s: %d' % (stream, e['event_seq']))
                    break
                prev_s = e['seg_id']

    for c in ZERO:
        v = man.get(c)
        if v is None:
            _fail(fails, 'MISSING_COUNTER', c)
        elif v:
            _fail(fails, 'RECORDER_REPORTED_' + c.upper(), str(v))

    # depth sides, actions, declared depth
    dev = events.get('depth', [])
    sides = {e['side'] for e in dev}
    actions = {e['action'] for e in dev}
    info['depth_sides'] = sorted(sides)
    info['depth_actions'] = sorted(actions)
    for need in ('BID', 'ASK'):
        if need not in sides:
            _fail(fails, 'MISSING_DEPTH_SIDE', need)
    for need in ('ADD', 'UPDATE', 'REMOVE'):
        if need not in actions:
            _fail(fails, 'MISSING_DEPTH_ACTION', need)
    mb = max([e['level'] for e in dev if e['side'] == 'BID'] or [-1]) + 1
    ma = max([e['level'] for e in dev if e['side'] == 'ASK'] or [-1]) + 1
    if mb != man.get('maxBidLevelSeen') or ma != man.get('maxAskLevelSeen'):
        _fail(fails, 'DEPTH_LEVEL_MISMATCH',
              '%d/%d vs %s/%s' % (mb, ma, man.get('maxBidLevelSeen'),
                                  man.get('maxAskLevelSeen')))
    info['declared_depth'] = man.get('declaredDepth')
    for key, side in (('depthBid', 'BID'), ('depthAsk', 'ASK')):
        n = sum(1 for e in dev if e['side'] == side)
        if n != man.get(key):
            _fail(fails, 'DEPTH_SIDE_COUNT_MISMATCH', side)
    for key, act in (('depthAdd', 'ADD'), ('depthUpdate', 'UPDATE'),
                     ('depthRemove', 'REMOVE')):
        n = sum(1 for e in dev if e['action'] == act)
        if n != man.get(key):
            _fail(fails, 'DEPTH_ACTION_COUNT_MISMATCH', act)

    # book invalid / resync intervals
    qual = events.get('quality', [])
    kinds = [e['kind'] for e in qual]
    info['book_resync_starts'] = kinds.count('BOOK_RESYNC_START')
    info['book_ready'] = kinds.count('BOOK_READY')
    info['suppressed_rows'] = sum(
        1 for evs in events.values() for e in evs
        if 'DATA_SUPPRESSED' in e['flags'])
    if info['book_ready'] > info['book_resync_starts']:
        _fail(fails, 'BOOK_READY_WITHOUT_RESYNC', '')

    return dict(ok=not fails, failures=fails, info=info,
                events=all_ev, manifest=man)


def discover_manifests(directory):
    """Collision manifests keep a .json extension, so one glob finds
    primary AND collision manifests."""
    out = []
    for p in sorted(glob.glob(os.path.join(directory, '*_manifest*.json'))):
        if p.endswith('.tmp'):
            continue
        out.append(p)
    return out


def audit_capture(directory, min_overlap=MIN_OVERLAP_FRAC):
    fails = []
    mans = discover_manifests(directory)
    runs = [audit_run(m) for m in mans]
    info = dict(manifests=len(mans))

    # orphan artifacts
    referenced = set()
    for r in runs:
        for f in r['info'].get('referenced_files', []):
            referenced.add(f)
    for p in sorted(os.listdir(directory)):
        full = os.path.join(directory, p)
        if p.endswith('.csv.partial'):
            _fail(fails, 'ORPHAN_PARTIAL', p)
        elif p.endswith('.csv') and p not in referenced:
            _fail(fails, 'ORPHAN_FINALIZED_CSV', p)
        elif p.endswith('_RECOVERY.json'):
            _fail(fails, 'RECOVERY_ARTIFACT_PRESENT', p)
        _ = full

    # duplicate run ids / one run spanning contracts
    seen = {}
    for r in runs:
        rid = r['info'].get('run_id')
        con = r['info'].get('contract')
        if rid in seen:
            if seen[rid] != con:
                _fail(fails, 'CONTRACT_ROLL_COLLISION', rid)
            _fail(fails, 'RESTART_COLLISION', 'duplicate runId %s' % rid)
        seen[rid] = con

    # capture-instance seq contiguity across the union of its runs
    by_cid = {}
    for r in runs:
        by_cid.setdefault(r['info'].get('capture_instance_id'),
                          []).append(r)
    for cid, rs in by_cid.items():
        seqs = sorted(s for r in rs for s in r['info'].get('event_seqs', []))
        if seqs and (seqs[0] != 1 or
                     seqs != list(range(seqs[0], seqs[0] + len(seqs)))):
            _fail(fails, 'INSTANCE_SEQ_GAP', str(cid))

    # NQ + MNQ pairing by session with overlap
    by_ses = {}
    for r in runs:
        inst = r['info'].get('instrument')
        if inst in OPTIONAL_INSTRUMENTS:
            continue
        by_ses.setdefault(r['info'].get('session'), {}).setdefault(
            inst, []).append(r)
    insts_present = {r['info'].get('instrument') for r in runs}
    for need in REQUIRED_INSTRUMENTS:
        if need not in insts_present:
            _fail(fails, 'MISSING_REQUIRED_INSTRUMENT', need)
    overlaps = {}
    for ses, d in by_ses.items():
        if 'NQ' not in d or 'MNQ' not in d:
            _fail(fails, 'NQ_MNQ_SESSION_MISMATCH',
                  '%s has only %s' % (ses, sorted(d)))
            continue
        a = d['NQ'][0]['info']
        b = d['MNQ'][0]['info']
        if not all([a['first_recv'], a['last_recv'], b['first_recv'],
                    b['last_recv']]):
            _fail(fails, 'PAIR_WINDOW_UNKNOWN', ses)
            continue
        lo = max(a['first_recv'], b['first_recv'])
        hi = min(a['last_recv'], b['last_recv'])
        ov = max((hi - lo).total_seconds(), 0.0)
        span = max(min((a['last_recv'] - a['first_recv']).total_seconds(),
                       (b['last_recv'] - b['first_recv']).total_seconds()),
                   1e-9)
        frac = ov / span
        overlaps[ses] = dict(overlap_seconds=ov, overlap_frac=frac,
                             nq=[str(a['first_recv']), str(a['last_recv'])],
                             mnq=[str(b['first_recv']), str(b['last_recv'])])
        if frac < min_overlap:
            _fail(fails, 'NQ_MNQ_INSUFFICIENT_OVERLAP',
                  '%s frac=%.3f' % (ses, frac))
    info['overlaps'] = overlaps

    for r in runs:
        if not r['ok'] and r['info'].get('instrument') \
                not in OPTIONAL_INSTRUMENTS:
            _fail(fails, 'RUN_AUDIT_FAILED',
                  '%s/%s: %s' % (r['info'].get('instrument'),
                                 r['info'].get('run_id'),
                                 r['failures'][:2]))
    return dict(ok=not fails, failures=fails, runs=runs, info=info)
