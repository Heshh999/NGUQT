#!/usr/bin/env python3
# ======================================================================
# MROF-YT-OF-01.5 — MLES-CAPTURE-1.1 INTEGRITY AUDIT
# The MANIFEST is the authoritative entrypoint. Nothing downstream may
# read a capture that has not passed this audit. Outcome-blind: this
# module never reads a price outcome, return or P&L.
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import hashlib
import json
import os

import mles_v11_adapter as AD

REQUIRED_STREAMS = ('quotes', 'trades', 'depth', 'quality')
REQUIRED_INSTRUMENTS = ('NQ', 'MNQ')
OPTIONAL_INSTRUMENTS = ('ES',)

ZERO_TOLERANCE_COUNTERS = ('gaps', 'duplicates', 'reversals',
                           'queueOverflows', 'droppedRows',
                           'writeErrors')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def _fail(fails, code, detail=''):
    fails.append((code, detail))


def audit_run(manifest_path):
    """Authoritative per-run audit. Returns dict(ok, failures, info)."""
    fails = []
    info = {}
    try:
        man = json.load(open(manifest_path))
    except Exception as exc:
        return dict(ok=False, failures=[('MANIFEST_UNREADABLE', str(exc))],
                    info=info)
    if man.get('schema') != AD.SCHEMA:
        _fail(fails, 'SCHEMA_MISMATCH', str(man.get('schema')))
        return dict(ok=False, failures=fails, info=info)
    base = os.path.dirname(os.path.abspath(manifest_path))
    run_id = man.get('runId')
    contract = man.get('contract')
    session = man.get('session')
    instrument = man.get('instrument')
    info.update(run_id=run_id, contract=contract, session=session,
                instrument=instrument)

    # ---- files: presence, size, hash, row count, header -------------
    events = {}
    for stream in REQUIRED_STREAMS:
        blk = man.get(stream)
        if not isinstance(blk, dict) or not blk.get('present'):
            _fail(fails, 'MISSING_REQUIRED_STREAM', stream)
            continue
        path = os.path.join(base, blk.get('file', ''))
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
                  '%s: file %d vs manifest %s'
                  % (stream, len(evs), blk.get('rows')))
        events[stream] = evs

    if not events:
        return dict(ok=False, failures=fails, info=info)

    # ---- identity ----------------------------------------------------
    for stream, evs in events.items():
        for e in evs:
            if e['run_id'] != run_id:
                _fail(fails, 'MIXED_RUN', '%s: %s' % (stream, e['run_id']))
                break
        for e in evs:
            if e['contract'] != contract:
                _fail(fails, 'MIXED_CONTRACT',
                      '%s: %s' % (stream, e['contract']))
                break
        for e in evs:
            if e['session'] != session:
                _fail(fails, 'MIXED_SESSION',
                      '%s: %s' % (stream, e['session']))
                break
        for e in evs:
            if e['instrument'] != instrument:
                _fail(fails, 'MIXED_INSTRUMENT',
                      '%s: %s' % (stream, e['instrument']))
                break

    # ---- per-file monotonicity (one ordered writer) ------------------
    for stream, evs in events.items():
        prev = None
        for e in evs:
            s = e['event_seq']
            if prev is not None:
                if s < prev:
                    _fail(fails, 'SEQUENCE_REVERSAL', '%s: %d<%d'
                          % (stream, s, prev))
                elif s == prev:
                    _fail(fails, 'DUPLICATE_EVENT_SEQ', '%s: %d'
                          % (stream, s))
            prev = s
        prevs = None
        for e in evs:
            s = e['stream_seq']
            if prevs is not None and s != prevs + 1:
                _fail(fails, 'STREAM_SEQ_BREAK', '%s: %d after %d'
                      % (stream, s, prevs))
            prevs = s

    # ---- global ordering ---------------------------------------------
    ordered, problems = AD.order_events(*events.values())
    info['events'] = len(ordered)
    for code, detail in problems:
        _fail(fails, code, str(detail))
    if ordered:
        if ordered[0]['event_seq'] != man.get('firstEventSeq'):
            _fail(fails, 'FIRST_EVENT_SEQ_MISMATCH',
                  str(ordered[0]['event_seq']))
        if ordered[-1]['event_seq'] != man.get('lastEventSeq'):
            _fail(fails, 'LAST_EVENT_SEQ_MISMATCH',
                  str(ordered[-1]['event_seq']))
        prev_t = None
        for e in ordered:
            if e['t_recv'] is None:
                _fail(fails, 'MISSING_RECV_TIMESTAMP',
                      str(e['event_seq']))
                break
            if prev_t is not None and e['t_recv'] < prev_t:
                _fail(fails, 'TIMESTAMP_REVERSAL', str(e['event_seq']))
                break
            prev_t = e['t_recv']

    # ---- recorder self-reported counters ------------------------------
    for c in ZERO_TOLERANCE_COUNTERS:
        v = man.get(c)
        if v is None:
            _fail(fails, 'MISSING_COUNTER', c)
        elif v:
            _fail(fails, 'RECORDER_REPORTED_' + c.upper(), str(v))

    # ---- depth coverage: BOTH sides and ALL actions -------------------
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
    if man.get('depthBid') is not None:
        nb = sum(1 for e in dev if e['side'] == 'BID')
        na = sum(1 for e in dev if e['side'] == 'ASK')
        if nb != man['depthBid'] or na != man.get('depthAsk'):
            _fail(fails, 'DEPTH_SIDE_COUNT_MISMATCH',
                  'bid %d/%s ask %d/%s' % (nb, man.get('depthBid'), na,
                                           man.get('depthAsk')))
    if man.get('depthAdd') is not None:
        for key, act in (('depthAdd', 'ADD'), ('depthUpdate', 'UPDATE'),
                         ('depthRemove', 'REMOVE')):
            n = sum(1 for e in dev if e['action'] == act)
            if n != man.get(key):
                _fail(fails, 'DEPTH_ACTION_COUNT_MISMATCH',
                      '%s %d/%s' % (act, n, man.get(key)))

    return dict(ok=not fails, failures=fails, info=info, events=ordered,
                manifest=man)


def audit_capture(directory):
    """Capture-level audit: NQ and MNQ REQUIRED, ES optional. Detects
    restart and contract-roll collisions across manifests."""
    fails = []
    runs = []
    for fn in sorted(os.listdir(directory)):
        if fn.endswith('_manifest.json'):
            runs.append(audit_run(os.path.join(directory, fn)))
    by_inst = {}
    for r in runs:
        by_inst.setdefault(r['info'].get('instrument'), []).append(r)
    for need in REQUIRED_INSTRUMENTS:
        if need not in by_inst:
            _fail(fails, 'MISSING_REQUIRED_INSTRUMENT', need)
    for inst, rs in by_inst.items():
        if inst in OPTIONAL_INSTRUMENTS:
            continue
        # restart collision: two runs claiming the same run identity
        ids = [r['info'].get('run_id') for r in rs]
        if len(set(ids)) != len(ids):
            _fail(fails, 'RESTART_COLLISION', '%s: duplicate runId' % inst)
        # contract-roll collision: one (session, run) spanning contracts
        seen = {}
        for r in rs:
            k = (r['info'].get('session'), r['info'].get('run_id'))
            c = r['info'].get('contract')
            if k in seen and seen[k] != c:
                _fail(fails, 'CONTRACT_ROLL_COLLISION',
                      '%s: %s vs %s' % (inst, seen[k], c))
            seen[k] = c
    bad = [r for r in runs
           if not r['ok'] and r['info'].get('instrument')
           not in OPTIONAL_INSTRUMENTS]
    for r in bad:
        _fail(fails, 'RUN_AUDIT_FAILED',
              '%s/%s' % (r['info'].get('instrument'),
                         r['info'].get('run_id')))
    return dict(ok=not fails, failures=fails, runs=runs,
                instruments=sorted(k for k in by_inst if k))
