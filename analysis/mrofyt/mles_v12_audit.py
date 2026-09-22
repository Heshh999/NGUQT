#!/usr/bin/env python3
# ======================================================================
# MLES-CAPTURE-1.2 INTEGRITY AUDIT (additive; v1.1 auditor untouched).
# The MANIFEST is the authoritative entrypoint. Outcome-blind.
#
# Build 1.2.1 (streaming repair). The first genuine sessions exposed
# three defects in the 1.2.0 auditor, all fixed here:
#   1. audit_run materialised every row (a 5.2 GB / 25M-row depth file
#      needs >15 GB RAM). Now ONE streaming pass over the eventSeq-
#      merged union of the four files; every check is incremental and
#      memory is O(holes + quality rows).
#   2. DEPTH_LEVEL_MISMATCH compared the file's run-lifetime maximum
#      against a manifest field the 1.2.0 recorder RESET on reconnect
#      (a run closed after a reconnect with a shallower book reported
#      maxBidLevelSeen=0 beside 10.9M depth rows). Build 1.2.1
#      manifests carry maxBid/AskLevelRun and are checked strictly;
#      legacy manifests are checked with the only inequality that
#      holds (observed >= post-reconnect value) and labelled.
#   3. NQ/MNQ pairing used the FIRST run per instrument per session,
#      so an ordinary restart mid-session permanently reported zero
#      overlap. Pairing now uses the union coverage of all runs.
# Instance-level seq contiguity no longer stores every seq: each run
# reports (first, last, count, holes) and holes are reconciled across
# the instance's runs (holes are tiny — they occur only at rotation
# boundaries where queued market rows interleave with minted quality
# rows).
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import glob
import json
import os
import re

import mles_v11_audit as AU11
import mles_v12_adapter as AD

sha256 = AU11.sha256
REQUIRED_STREAMS = ('quotes', 'trades', 'depth', 'quality')
REQUIRED_INSTRUMENTS = ('NQ', 'MNQ')
OPTIONAL_INSTRUMENTS = ('ES',)
ZERO = ('gaps', 'duplicates', 'reversals', 'queueOverflows',
        'droppedRows', 'writeErrors')
MIN_OVERLAP_FRAC = 0.5
MAX_HOLES = 100000            # more than this is not a rotation artefact
LAT_BINS_MS = 5000            # 1 ms histogram bins for recv-exch latency
REPAIRED_BUILD = (1, 2, 2)    # first recorder with the disconnect repair

STREAM_KEYS = dict(quotes=('firstQuoteSeq', 'lastQuoteSeq'),
                   trades=('firstTradeSeq', 'lastTradeSeq'),
                   depth=('firstDepthSeq', 'lastDepthSeq'),
                   quality=('firstQualitySeq', 'lastQualitySeq'))
IDENTITY = (('capture_instance_id', 'captureInstanceId',
             'MIXED_CAPTURE_INSTANCE'),
            ('run_id', 'runId', 'MIXED_RUN'),
            ('session', 'session', 'MIXED_SESSION'),
            ('instrument', 'instrument', 'MIXED_INSTRUMENT'),
            ('contract', 'contract', 'MIXED_CONTRACT'))


def _fail(fails, code, detail=''):
    fails.append((code, detail))


# ---------------------------------------------------------------------
# an unreadable capture is stopped, never reported
# ---------------------------------------------------------------------
class CaptureUnavailable(RuntimeError):
    """The capture folder cannot be read: missing, or it stopped
    answering mid-pass (drive disconnected, USB power dropped). Raised
    instead of reporting, because every later read fails the same way
    and a report missing everything after that point reads exactly like
    a quiet market. Found 2026-09-22: a loose drive took down a runner,
    pilot and wave-two pass, and the wave-two pass printed a clean,
    well-formatted report of zero fires on zero sessions."""


class NoCaptureData(RuntimeError):
    """The folder answers but holds no manifest for the instruments
    asked for: the wrong folder, or a drive that came back under
    another letter. Never a valid result on a real capture."""


def capture_dir_alive(directory):
    try:
        os.listdir(directory)
        return True
    except OSError:
        return False


def stop_if_capture_gone(directory, what, exc):
    """Called on an OSError while reading the capture. If the folder
    itself no longer answers, the device is gone: raise. If it still
    answers, the error belongs to this one file, and the caller records
    it and carries on."""
    if not capture_dir_alive(directory):
        raise CaptureUnavailable(
            'the capture folder %s stopped answering while reading %s '
            '(%s). The drive was disconnected or lost power. Nothing was '
            'written: a report missing everything after this point would '
            'read like a quiet market. Reconnect the drive, check it is '
            'still the same letter, and re-run.' % (directory, what, exc))


class _StreamState:
    __slots__ = ('rows', 'prev_seq', 'first_ss', 'last_ss', 'prev_ss',
                 'ss_break', 'seq_rev', 'first_seg', 'prev_seg',
                 'seg_rev', 'ident_bad')

    def __init__(self):
        self.rows = 0
        self.prev_seq = None
        self.first_ss = None
        self.last_ss = None
        self.prev_ss = None
        self.ss_break = False
        self.seq_rev = None
        self.first_seg = None
        self.prev_seg = None
        self.seg_rev = None
        self.ident_bad = {}


def _lat_summary(hist, n):
    if n == 0:
        return None
    out = {}
    cum = 0
    targets = {'p50': 0.5 * n, 'p95': 0.95 * n}
    for ms, c in enumerate(hist):
        if not c:
            continue
        cum += c
        for k, want in list(targets.items()):
            if cum >= want and k not in out:
                out[k] = ms
    out['n'] = n
    out['overflow'] = hist[-1]
    return out


def audit_run(manifest_path, lite=True):
    fails = []
    info = {}
    try:
        man = json.load(open(manifest_path))
    except Exception as exc:
        return dict(ok=False,
                    failures=[('MANIFEST_UNREADABLE', str(exc))],
                    info=info, events=[], manifest=None)
    if man.get('schema') != AD.SCHEMA:
        return dict(ok=False,
                    failures=[('SCHEMA_MISMATCH', str(man.get('schema')))],
                    info=info, events=[], manifest=man)
    base = os.path.dirname(os.path.abspath(manifest_path))
    cid = man.get('captureInstanceId')
    rid, ses = man.get('runId'), man.get('session')
    inst, con = man.get('instrument'), man.get('contract')
    info.update(capture_instance_id=cid, run_id=rid, session=ses,
                instrument=inst, contract=con,
                recorder_build=man.get('recorderBuild', '1.2.0'),
                first_recv=AD.parse_iso(man.get('firstRecvUtc') or ''),
                last_recv=AD.parse_iso(man.get('lastRecvUtc') or ''))

    # ---- files: presence, size, hash (hash streams in 1 MB chunks) ----
    paths = {}
    referenced = []
    for stream in REQUIRED_STREAMS:
        blk = man.get(stream)
        if not isinstance(blk, dict) or not blk.get('present'):
            _fail(fails, 'MISSING_REQUIRED_STREAM', stream)
            continue
        path = os.path.join(base, blk.get('file', ''))
        referenced.append(blk.get('file', ''))
        if not os.path.exists(path):
            # a vanished drive makes every file look absent
            stop_if_capture_gone(base, blk.get('file', ''), 'not found')
            _fail(fails, 'MISSING_FILE', blk.get('file', ''))
            continue
        try:
            if os.path.getsize(path) != blk.get('bytes'):
                _fail(fails, 'BYTE_SIZE_MISMATCH', stream)
            if sha256(path) != blk.get('sha256'):
                _fail(fails, 'HASH_MISMATCH', stream)
        except OSError as exc:
            stop_if_capture_gone(base, blk.get('file', ''), exc)
            _fail(fails, 'IO_ERROR', '%s: %s' % (blk.get('file', ''), exc))
            return dict(ok=False, failures=fails, info=info, events=[],
                        manifest=man)
        paths[stream] = path
    info['referenced_files'] = referenced
    if not paths:
        return dict(ok=False, failures=fails, info=info, events=[],
                    manifest=man)

    # ---- ONE streaming pass over the merged union -------------------
    st = {k: _StreamState() for k in paths}
    want = {f: man.get(mk) for f, mk, _ in IDENTITY}
    quality = []
    first_seq = last_seq = None
    count = 0
    holes = []
    holes_over = False
    dup_seq = rev_seq = None
    prev_t = prev_m = None
    t_missing = t_rev = m_rev = None
    depth_sides = set()
    depth_actions = set()
    max_bid = max_ask = -1
    n_bid = n_ask = 0
    n_act = dict(ADD=0, UPDATE=0, REMOVE=0)
    # depth rows AFTER the book was first built. Before BOOK_READY the
    # recorder is still constructing the book and only ADDs are expected,
    # so completeness of sides/actions can only be asserted on rows that
    # came after it (see the completeness check below).
    book_ready_seen = False
    n_depth_after_ready = 0
    suppressed = 0
    lat_hist = [0] * (LAT_BINS_MS + 1)
    lat_n = 0
    kind_of = {v: k for k, v in AD.STREAM_OF_FILE.items()}

    try:
        for e in AD.merge_run(paths, lite=lite):
            k = kind_of[e['stream']]
            s = st[k]
            s.rows += 1
            seq = e['event_seq']
            # identity on EVERY row (first offender per field recorded)
            for f, _, code in IDENTITY:
                if e[f] != want[f] and code not in s.ident_bad:
                    s.ident_bad[code] = '%s: %r' % (k, e[f])
            # per-file event-seq order (merge consumes each file in
            # its own order, so this IS the file order)
            if s.prev_seq is not None and seq <= s.prev_seq and \
                    s.seq_rev is None:
                s.seq_rev = ('SEQUENCE_REVERSAL' if seq < s.prev_seq
                             else 'DUPLICATE_EVENT_SEQ',
                             '%s: %d after %d' % (k, seq, s.prev_seq))
            s.prev_seq = seq
            # per-run streamSeq reset/contiguity
            ss = e['stream_seq']
            if s.first_ss is None:
                s.first_ss = ss
            elif s.prev_ss is not None and ss != s.prev_ss + 1:
                s.ss_break = True
            s.prev_ss = ss
            s.last_ss = ss
            # per-file segment order (non-decreasing in write order)
            seg = e['seg_id']
            if s.first_seg is None:
                s.first_seg = seg
            if s.prev_seg is not None and seg < s.prev_seg and \
                    s.seg_rev is None:
                s.seg_rev = '%s: %d' % (k, seq)
            s.prev_seg = seg
            # global union: boundaries, holes, duplicates, clocks
            count += 1
            if first_seq is None:
                first_seq = seq
            elif seq <= last_seq:
                if seq == last_seq and dup_seq is None:
                    dup_seq = seq
                elif seq < last_seq and rev_seq is None:
                    rev_seq = seq
            elif seq > last_seq + 1 and not holes_over:
                gap = seq - last_seq - 1
                if len(holes) + gap > MAX_HOLES:
                    holes_over = True
                else:
                    holes.extend(range(last_seq + 1, seq))
            if last_seq is None or seq > last_seq:
                last_seq = seq
            tr = e['t_recv']
            if tr is None:
                if t_missing is None:
                    t_missing = seq
            else:
                if prev_t is not None and tr < prev_t and t_rev is None:
                    t_rev = seq
                prev_t = tr
            tm = e['t_mono']
            if prev_m is not None and tm < prev_m and m_rev is None:
                m_rev = seq
            prev_m = tm
            if 'DATA_SUPPRESSED' in e['flags']:
                suppressed += 1
            # stream-specific accounting
            if k == 'depth':
                side, act, lvl = e['side'], e['action'], e['level']
                depth_sides.add(side)
                depth_actions.add(act)
                if side == 'BID':
                    n_bid += 1
                    if lvl > max_bid:
                        max_bid = lvl
                else:
                    n_ask += 1
                    if lvl > max_ask:
                        max_ask = lvl
                if act in n_act:
                    n_act[act] += 1
                if book_ready_seen:
                    n_depth_after_ready += 1
            elif k == 'quality':
                quality.append(e)
                if e['kind'] == 'BOOK_READY':
                    book_ready_seen = True
            elif k in ('trades', 'quotes'):
                te = e['t_exch']
                if te is not None and tr is not None:
                    ms = int((tr - te) * 1000.0)
                    if ms < 0:
                        ms = 0
                    lat_hist[min(ms, LAT_BINS_MS)] += 1
                    lat_n += 1
    except AD.MalformedHeaderError as exc:
        _fail(fails, 'MALFORMED_HEADER', str(exc))
        return dict(ok=False, failures=fails, info=info, events=quality,
                    manifest=man)
    except AD.UnknownEnumError as exc:
        _fail(fails, 'UNKNOWN_ENUM', str(exc))
        return dict(ok=False, failures=fails, info=info, events=quality,
                    manifest=man)
    except OSError as exc:
        stop_if_capture_gone(base, rid, exc)
        _fail(fails, 'IO_ERROR', '%s: %s' % (rid, exc))
        return dict(ok=False, failures=fails, info=info, events=quality,
                    manifest=man)

    # ---- per-stream verdicts ----------------------------------------
    for k, s in st.items():
        blk = man.get(k) or {}
        if s.rows != blk.get('rows'):
            _fail(fails, 'ROW_COUNT_MISMATCH',
                  '%s file %d vs manifest %s' % (k, s.rows, blk.get('rows')))
        for code, detail in s.ident_bad.items():
            _fail(fails, code, detail)
        if s.seq_rev:
            _fail(fails, s.seq_rev[0], s.seq_rev[1])
        if s.rows and s.first_ss != 1:
            _fail(fails, 'STREAM_SEQ_NOT_RESET',
                  '%s starts at %d' % (k, s.first_ss))
        if s.ss_break:
            _fail(fails, 'STREAM_SEQ_BREAK', k)
        fk, lk = STREAM_KEYS[k]
        if s.rows:
            if s.first_ss != man.get(fk):
                _fail(fails, 'STREAM_FIRST_SEQ_MISMATCH', k)
            if s.last_ss != man.get(lk):
                _fail(fails, 'STREAM_LAST_SEQ_MISMATCH', k)
        if s.seg_rev:
            _fail(fails, 'SEG_REVERSAL', s.seg_rev)

    # ---- global verdicts --------------------------------------------
    info['events'] = count
    info['seq_first'] = first_seq
    info['seq_last'] = last_seq
    info['seq_count'] = count
    info['seq_holes'] = holes
    if holes_over:
        _fail(fails, 'RUN_SEQ_HOLES_EXCESSIVE', '> %d' % MAX_HOLES)
    if count:
        if first_seq != man.get('firstEventSeq'):
            _fail(fails, 'FIRST_EVENT_SEQ_MISMATCH', str(first_seq))
        if last_seq != man.get('lastEventSeq'):
            _fail(fails, 'LAST_EVENT_SEQ_MISMATCH', str(last_seq))
        if dup_seq is not None:
            _fail(fails, 'DUPLICATE_EVENT_SEQ', 'union: %d' % dup_seq)
        if rev_seq is not None:
            _fail(fails, 'SEQUENCE_REVERSAL', 'union: %d' % rev_seq)
        if t_missing is not None:
            _fail(fails, 'MISSING_RECV_TIMESTAMP', str(t_missing))
        if t_rev is not None:
            _fail(fails, 'RECV_TIMESTAMP_REVERSAL', str(t_rev))
        if m_rev is not None:
            _fail(fails, 'MONO_REVERSAL', str(m_rev))
        # segment range across the union: each file is non-decreasing
        # in write order, so its first row holds its lowest segment and
        # its last row its highest
        seg_hi = max(s.prev_seg for s in st.values() if s.rows)
        seg_lo = min(s.first_seg for s in st.values() if s.rows)
        if seg_lo != man.get('firstSegId') or \
                seg_hi != man.get('lastSegId') or \
                seg_hi != man.get('connectionSegments'):
            _fail(fails, 'SEG_COUNT_MISMATCH',
                  'rows %d..%d vs manifest %s..%s/%s'
                  % (seg_lo, seg_hi, man.get('firstSegId'),
                     man.get('lastSegId'), man.get('connectionSegments')))

    # A manifest rebuilt by mrofyt_recover.py from the rows of a run
    # whose recorder died before finalizing. Two things must be said
    # about it, and exactly once each, instead of a pile of
    # MISSING_COUNTER failures that look like ordinary corruption:
    #   1. the recorder's self-reported counters are ABSENT, not zero --
    #      nothing in the rows can reveal them, so their absence is
    #      correct and inventing them would have been the defect;
    #   2. its hashes, row counts and sequence bounds were computed from
    #      the very files they describe, so they match by construction
    #      and prove nothing about those files. That is NOT a clean pass
    #      and is never reported as one.
    info['reconstructed'] = bool(man.get('reconstructed'))
    if info['reconstructed']:
        info['reconstructed_by'] = man.get('reconstructedBy')
        _fail(fails, 'RECONSTRUCTED_RUN_NOT_SELF_VERIFYING',
              '%s rebuilt this manifest from the run\'s own rows; its '
              'hashes/counts/seq bounds are tautological and the recorder '
              'counters (%s) are absent by design. Cross-run instance '
              'contiguity, pairing and row-shape checks above still apply.'
              % (man.get('reconstructedBy') or 'a recovery tool',
                 ', '.join(ZERO)))
    else:
        for c in ZERO:
            v = man.get(c)
            if v is None:
                _fail(fails, 'MISSING_COUNTER', c)
            elif v:
                _fail(fails, 'RECORDER_REPORTED_' + c.upper(), str(v))

    # ---- depth sides, actions, levels --------------------------------
    info['depth_sides'] = sorted(depth_sides)
    info['depth_actions'] = sorted(depth_actions)
    # Completeness of sides/actions is only assertable on a run that
    # carried enough depth activity to expect them. A near-empty run --
    # a closed-market fragment, or a few seconds before an orderly
    # shutdown -- legitimately never sees a REMOVE, and failing it for
    # that is a false positive, not a detection. Two genuine runs in the
    # first nine recorded sessions tripped this: 20260905 (608 rows; the
    # market was shut, 18:04 ET Friday) and 20260908 (70 rows). The
    # floor is deliberately far below any real session -- a live NQ/MNQ
    # run carries tens of millions of depth rows -- so no feed defect
    # can hide behind it.
    # The first floor counted depth rows from row one, and a 228-row
    # restart stub (20260913, NQ) still tripped it: ~60 of those rows
    # were the book being BUILT, during which only ADDs can occur.
    # Completeness of actions is a claim about churn on a built book, so
    # it is asserted only on rows after the run's first BOOK_READY. A run
    # that never reached BOOK_READY built no book and can support no
    # such claim at all. Any live session has millions of post-ready
    # rows, so no feed defect can hide behind this.
    n_depth = n_bid + n_ask
    min_rows = 20 * (man.get('declaredDepth') or 10)
    info['depth_rows'] = n_depth
    info['depth_rows_after_book_ready'] = n_depth_after_ready
    checked = book_ready_seen and n_depth_after_ready >= min_rows
    info['depth_completeness_checked'] = checked
    if checked:
        for need in ('BID', 'ASK'):
            if need not in depth_sides:
                _fail(fails, 'MISSING_DEPTH_SIDE', need)
        for need in ('ADD', 'UPDATE', 'REMOVE'):
            if need not in depth_actions:
                _fail(fails, 'MISSING_DEPTH_ACTION', need)
    elif not book_ready_seen:
        info['depth_completeness_skipped'] = (
            'run never reached BOOK_READY (%d depth rows); no built book, '
            'so sides/actions are not assertable' % n_depth)
    else:
        info['depth_completeness_skipped'] = (
            '%d depth rows after BOOK_READY < %d; sides/actions are not '
            'assertable on this little churn (%d rows total)'
            % (n_depth_after_ready, min_rows, n_depth))
    mb, ma = max_bid + 1, max_ask + 1
    info['depth_max_bid_obs'] = mb
    info['depth_max_ask_obs'] = ma
    if 'maxBidLevelRun' in man:
        info['level_semantics'] = 'run'
        if mb != man.get('maxBidLevelRun') or ma != man.get('maxAskLevelRun'):
            _fail(fails, 'DEPTH_LEVEL_MISMATCH',
                  'run %d/%d vs manifest %s/%s'
                  % (mb, ma, man.get('maxBidLevelRun'),
                     man.get('maxAskLevelRun')))
    else:
        # 1.2.0 manifests: the field is the post-reconnect maximum, so
        # the run-lifetime observation can only be >= it.
        info['level_semantics'] = 'legacy_post_reconnect'
        sb, sa = man.get('maxBidLevelSeen'), man.get('maxAskLevelSeen')
        if sb is None or sa is None or mb < sb or ma < sa:
            _fail(fails, 'DEPTH_LEVEL_MISMATCH',
                  'legacy: observed %d/%d < manifest %s/%s'
                  % (mb, ma, sb, sa))
    info['declared_depth'] = man.get('declaredDepth')
    if n_bid != man.get('depthBid'):
        _fail(fails, 'DEPTH_SIDE_COUNT_MISMATCH', 'BID')
    if n_ask != man.get('depthAsk'):
        _fail(fails, 'DEPTH_SIDE_COUNT_MISMATCH', 'ASK')
    for key, act in (('depthAdd', 'ADD'), ('depthUpdate', 'UPDATE'),
                     ('depthRemove', 'REMOVE')):
        if n_act[act] != man.get(key):
            _fail(fails, 'DEPTH_ACTION_COUNT_MISMATCH', act)

    # ---- book invalid / resync intervals ----------------------------
    kinds = [e['kind'] for e in quality]
    info['book_resync_starts'] = kinds.count('BOOK_RESYNC_START')
    info['book_ready'] = kinds.count('BOOK_READY')
    info['suppressed_rows'] = suppressed
    # A run that BEGINS an instance builds its book from nothing, so its
    # first BOOK_READY is legitimately not preceded by a resync. Later
    # runs of the same instance inherit an already-built book, so every
    # BOOK_READY there must follow a BOOK_RESYNC_START. The first genuine
    # multi-session captures exposed this: every R001 failed and every
    # R002 passed, which is the signature of an off-by-one rule, not of
    # bad data.
    first_of_instance = man.get('firstEventSeq') == 1
    allowed = info['book_resync_starts'] + (1 if first_of_instance else 0)
    info['book_ready_allowed'] = allowed
    if info['book_ready'] > allowed:
        _fail(fails, 'BOOK_READY_WITHOUT_RESYNC',
              '%d ready > %d allowed' % (info['book_ready'], allowed))
    # the trigger the 1.2.2 repair exists for; see repair_evidence()
    info['disconnects'] = kinds.count('DISCONNECT')
    info['spurious_book_ready'] = max(0, info['book_ready'] - allowed)
    info['latency_ms'] = _lat_summary(lat_hist, lat_n)

    return dict(ok=not fails, failures=fails, info=info,
                events=quality, manifest=man)


def discover_manifests(directory):
    """Collision manifests keep a .json extension, so one glob finds
    primary AND collision manifests."""
    out = []
    for p in sorted(glob.glob(os.path.join(directory, '*_manifest*.json'))):
        if p.endswith('.tmp'):
            continue
        out.append(p)
    return out


# ---------------------------------------------------------------------
# instance seq contiguity from (first, last, count, holes) per run
# ---------------------------------------------------------------------
def instance_seq_contiguous(runs_info):
    """runs_info: list of info dicts (seq_first/seq_last/seq_count/
    seq_holes). The union of the runs must be exactly 1..N with every
    seq in exactly one run. Holes inside a run must be filled by
    another run of the same instance (rotation interleaving)."""
    rs = [r for r in runs_info if r.get('seq_count')]
    if not rs:
        return True, ''
    lo = min(r['seq_first'] for r in rs)
    hi = max(r['seq_last'] for r in rs)
    total = sum(r['seq_count'] for r in rs)
    if lo != 1:
        return False, 'first seq %d != 1' % lo
    if total != hi - lo + 1:
        return False, 'count %d != span %d' % (total, hi - lo + 1)
    holes = {id(r): set(r.get('seq_holes', [])) for r in rs}

    def present(r, s):
        return r['seq_first'] <= s <= r['seq_last'] and s not in holes[id(r)]

    # every hole must be present in exactly one other run
    for r in rs:
        for h in holes[id(r)]:
            n = sum(1 for o in rs if o is not r and present(o, h))
            if n != 1:
                return False, 'seq %d present in %d runs' % (h, n)
    # overlapping ranges: each seq in the overlap present exactly once
    srt = sorted(rs, key=lambda r: r['seq_first'])
    for i in range(len(srt)):
        for j in range(i + 1, len(srt)):
            a, b = srt[i], srt[j]
            if b['seq_first'] > a['seq_last']:
                break
            if b['seq_last'] - b['seq_first'] > MAX_HOLES and \
                    a['seq_last'] - b['seq_first'] > MAX_HOLES:
                return False, 'overlap too large to reconcile'
            for s in range(b['seq_first'], min(a['seq_last'],
                                               b['seq_last']) + 1):
                n = sum(1 for o in rs if present(o, s))
                if n != 1:
                    return False, 'seq %d present in %d runs' % (s, n)
    return True, ''


# ---------------------------------------------------------------------
# NQ/MNQ pairing over the UNION coverage of each instrument's runs
# ---------------------------------------------------------------------
def coverage(runs_info):
    """Merged [first_recv, last_recv] intervals of a run list."""
    iv = sorted((r['first_recv'], r['last_recv']) for r in runs_info
                if r.get('first_recv') and r.get('last_recv'))
    out = []
    for a, b in iv:
        if out and a <= out[-1][1]:
            if b > out[-1][1]:
                out[-1] = (out[-1][0], b)
        else:
            out.append((a, b))
    return out


def overlap_frac(cov_a, cov_b):
    """Overlap seconds between two coverages / the smaller total
    coverage. With one run per side this is the 1.2.0 computation."""
    ov = 0.0
    for a0, a1 in cov_a:
        for b0, b1 in cov_b:
            lo, hi = max(a0, b0), min(a1, b1)
            if hi > lo:
                ov += (hi - lo).total_seconds()
    span_a = sum((b - a).total_seconds() for a, b in cov_a)
    span_b = sum((b - a).total_seconds() for a, b in cov_b)
    span = max(min(span_a, span_b), 1e-9)
    return ov, ov / span


def pair_sessions(runs, min_overlap=MIN_OVERLAP_FRAC):
    """runs: audit_run results. Returns (failures, overlaps)."""
    fails = []
    by_ses = {}
    for r in runs:
        inst = r['info'].get('instrument')
        if inst in OPTIONAL_INSTRUMENTS:
            continue
        by_ses.setdefault(r['info'].get('session'), {}).setdefault(
            inst, []).append(r['info'])
    overlaps = {}
    for ses, d in by_ses.items():
        if 'NQ' not in d or 'MNQ' not in d:
            _fail(fails, 'NQ_MNQ_SESSION_MISMATCH',
                  '%s has only %s' % (ses, sorted(d)))
            continue
        ca, cb = coverage(d['NQ']), coverage(d['MNQ'])
        if not ca or not cb:
            _fail(fails, 'PAIR_WINDOW_UNKNOWN', ses)
            continue
        ov, frac = overlap_frac(ca, cb)
        overlaps[ses] = dict(overlap_seconds=ov, overlap_frac=frac,
                             nq=[str(ca[0][0]), str(ca[-1][1])],
                             mnq=[str(cb[0][0]), str(cb[-1][1])],
                             nq_runs=len(d['NQ']), mnq_runs=len(d['MNQ']))
        if frac < min_overlap:
            _fail(fails, 'NQ_MNQ_INSUFFICIENT_OVERLAP',
                  '%s frac=%.3f' % (ses, frac))
    return fails, overlaps


def _build_tuple(b):
    try:
        return tuple(int(x) for x in str(b).split('.'))
    except ValueError:
        return (0,)


def repair_evidence(runs):
    """Has the 1.2.2 disconnect repair actually been EXERCISED?

    The repair acts only after a feed disconnect. A repaired build with
    no spurious BOOK_READY therefore proves nothing unless its runs
    contained a disconnect -- and comparing builds alone proves nothing
    either, because old sessions are the old-build sessions by
    construction: the build is confounded with the calendar. This counts
    the trigger itself. A run whose rows could not be read is counted
    separately, never assumed clean."""
    by = {}
    for r in runs:
        i = r['info']
        b = i.get('recorder_build') or '1.2.0'
        e = by.setdefault(b, dict(runs=0, read=0, disconnects=0,
                                  runs_with_disconnect=0,
                                  spurious_book_ready=0))
        e['runs'] += 1
        if 'disconnects' in i:
            e['read'] += 1
            e['disconnects'] += i['disconnects']
            e['runs_with_disconnect'] += 1 if i['disconnects'] else 0
            e['spurious_book_ready'] += i['spurious_book_ready']
    keys = ('runs', 'read', 'disconnects', 'runs_with_disconnect',
            'spurious_book_ready')
    rep = [e for b, e in by.items() if _build_tuple(b) >= REPAIRED_BUILD]
    tot = {k: sum(e[k] for e in rep) for k in keys}
    if not tot['read']:
        tot['verdict'] = 'NO_REPAIRED_RUN_READ'
    elif tot['spurious_book_ready']:
        tot['verdict'] = 'FAILED'
    elif not tot['disconnects']:
        tot['verdict'] = 'NOT_EXERCISED'
    else:
        tot['verdict'] = 'EXERCISED_AND_HELD'
    return dict(by_build=dict(sorted(by.items())), repaired=tot)


REPAIR_VERDICT_TEXT = dict(
    NOT_EXERCISED='no run on a repaired build has had a feed disconnect '
                  'yet, so the repair is UNTESTED -- the absence of '
                  'spurious readies proves nothing',
    EXERCISED_AND_HELD='disconnects occurred on repaired builds and none '
                       'produced a spurious BOOK_READY: the repair was '
                       'exercised and held',
    FAILED='a repaired build produced a spurious BOOK_READY: the repair '
           'did NOT hold',
    NO_REPAIRED_RUN_READ='no run from a repaired build could be read')


def _classify_leftovers(directory):
    """Which unreferenced CSVs are NOT failures, and why.

    * a run the recorder is still writing (it has no manifest because
      the recorder writes that at close) -- judged by the same rule the
      recovery tool uses before it writes anything, so the two can never
      disagree about which runs are live;
    * a damaged original kept beside the _RECOVERED copy that a
      reconstructed manifest references -- kept deliberately, because
      originals are never modified.

    Imported lazily: the recovery tool imports the runner, which imports
    this module. Without it, nothing is reclassified."""
    try:
        import mrofyt_recover as RC
    except ImportError:
        return {}, {}, set()
    live_files, live_inst = {}, {}
    for run in RC.find_orphan_runs(directory):
        if run.get('live'):
            live_inst[run['run_id'].rsplit('-R', 1)[0]] = run['run_id']
            for p in run['streams'].values():
                live_files[os.path.basename(p)] = (run['run_id'],
                                                   run['live'])
    kept = set()
    for p in os.listdir(directory):
        m = RC.RUN_RE.match(p)
        if m and os.path.exists(os.path.join(
                directory, m.group('base') + '_RECONSTRUCTED_manifest.json')):
            kept.add(p)
    return live_files, live_inst, kept


def audit_capture(directory, min_overlap=MIN_OVERLAP_FRAC):
    if not capture_dir_alive(directory):
        raise CaptureUnavailable(
            'cannot read the capture folder %s. Is the drive connected, '
            'and is it still that letter?' % directory)
    fails = []
    mans = discover_manifests(directory)
    if not mans:
        _fail(fails, 'NO_MANIFESTS',
              '%s holds no MLES-CAPTURE-1.2 manifest: the wrong folder, or '
              'a drive that came back under another letter' % directory)
    runs = [audit_run(m) for m in mans]
    info = dict(manifests=len(mans))

    # orphan artifacts
    referenced = set()
    for r in runs:
        for f in r['info'].get('referenced_files', []):
            referenced.add(f)
    live_files, live_inst, kept = _classify_leftovers(directory)
    open_runs = {}
    kept_originals = []
    open_instances = set()
    for p in sorted(os.listdir(directory)):
        loose = p.endswith('.csv.partial') or \
            (p.endswith('.csv') and p not in referenced)
        if loose and p in live_files:
            rid, why = live_files[p]
            open_runs[rid] = why
            continue
        if loose and p in kept:
            kept_originals.append(p)
            continue
        if p.endswith('.csv.partial'):
            _fail(fails, 'ORPHAN_PARTIAL', p)
            m = re.search(r'_(\d{17}-[0-9a-f]{8})-R\d{3}_', p)
            if m:
                open_instances.add(m.group(1))
        elif p.endswith('.csv') and p not in referenced:
            _fail(fails, 'ORPHAN_FINALIZED_CSV', p)
        elif p.endswith('_RECOVERY.json'):
            _fail(fails, 'RECOVERY_ARTIFACT_PRESENT', p)
    info['open_runs_in_progress'] = open_runs
    info['recovery_originals_kept'] = kept_originals

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
                          []).append(r['info'])
    in_progress = []
    for cid, rs in by_cid.items():
        ok, why = instance_seq_contiguous(rs)
        if ok:
            continue
        # An instance whose later run is still an unfinalized .csv.partial
        # has rows that carry a published seq but reach no manifest, so the
        # union is SHORT by exactly those rows. That is an unverifiable
        # union, not a detected gap, and calling it a gap points at the
        # wrong cause. Only the count/span shortfall is reclassified: a
        # hole or an overlap is never explained by an open run.
        # When that run is being RECORDED right now the shortfall is the
        # normal state of every audit taken during a session -- noted,
        # not failed, or the weekly check would never read clean.
        if cid in live_inst and why.startswith('count '):
            in_progress.append('%s: %s (run %s is still being recorded; '
                               'this resolves when it closes)'
                               % (cid, why, live_inst[cid]))
        elif cid in open_instances and why.startswith('count '):
            _fail(fails, 'INSTANCE_SEQ_UNVERIFIABLE_OPEN_RUN',
                  '%s: %s (instance has a run with no manifest; if it is '
                  'orphaned, mrofyt_recover.py rebuilds it -- re-audit '
                  'after)' % (cid, why))
        else:
            _fail(fails, 'INSTANCE_SEQ_GAP', '%s: %s' % (cid, why))
    info['instance_shortfall_in_progress'] = in_progress

    insts_present = {r['info'].get('instrument') for r in runs}
    for need in REQUIRED_INSTRUMENTS:
        if need not in insts_present:
            _fail(fails, 'MISSING_REQUIRED_INSTRUMENT', need)
    pf, overlaps = pair_sessions(runs, min_overlap)
    fails.extend(pf)
    info['overlaps'] = overlaps

    for r in runs:
        if not r['ok'] and r['info'].get('instrument') \
                not in OPTIONAL_INSTRUMENTS:
            _fail(fails, 'RUN_AUDIT_FAILED',
                  '%s/%s: %s' % (r['info'].get('instrument'),
                                 r['info'].get('run_id'),
                                 r['failures'][:2]))
    info['repair_evidence'] = repair_evidence(runs)
    return dict(ok=not fails, failures=fails, runs=runs, info=info)


def summary(result):
    """Compact text for handing back; no market content."""
    i0 = result['info']
    lines = ['audit ok=%s failures=%d manifests=%d'
             % (result['ok'], len(result['failures']),
                i0.get('manifests', 0))]
    for rid, why in sorted(i0.get('open_runs_in_progress', {}).items()):
        lines.append('  OPEN (being recorded, not a failure) %s: %s'
                     % (rid, why))
    for x in i0.get('instance_shortfall_in_progress', []):
        lines.append('  OPEN (being recorded, not a failure) %s' % x)
    if i0.get('recovery_originals_kept'):
        lines.append('  KEPT %d damaged originals beside their recovered '
                     'copies (never modified, by design; not a failure)'
                     % len(i0['recovery_originals_kept']))
    for c, d in result['failures']:
        lines.append('  FAIL %s %s' % (c, d))
    for r in result.get('runs', []):
        i = r['info']
        lat = i.get('latency_ms') or {}
        lines.append('  %-4s %-8s %-36s rows=%-10s ok=%-5s build=%s '
                     'levels=%s/%s(%s) lat_p50=%sms'
                     % (i.get('instrument'), i.get('session'),
                        i.get('run_id'), i.get('events'), r['ok'],
                        i.get('recorder_build'), i.get('depth_max_bid_obs'),
                        i.get('depth_max_ask_obs'),
                        i.get('level_semantics', '')[:6],
                        lat.get('p50')))
    for ses, o in result['info'].get('overlaps', {}).items():
        lines.append('  pair %s overlap=%.3f (NQ runs %d, MNQ runs %d)'
                     % (ses, o['overlap_frac'], o['nq_runs'], o['mnq_runs']))
    ev = i0.get('repair_evidence')
    if ev:
        t = ev['repaired']
        lines.append('  disconnect repair (recorder >= %s): %d of %d runs '
                     'read, %d with a feed disconnect (%d disconnects), %d '
                     'spurious BOOK_READY -> %s: %s'
                     % ('.'.join(map(str, REPAIRED_BUILD)), t['read'],
                        t['runs'], t['runs_with_disconnect'],
                        t['disconnects'], t['spurious_book_ready'],
                        t['verdict'], REPAIR_VERDICT_TEXT[t['verdict']]))
        for b, e in ev['by_build'].items():
            lines.append('    build %-6s runs=%d read=%d disconnects=%d '
                         'spurious_book_ready=%d'
                         % (b, e['runs'], e['read'], e['disconnects'],
                            e['spurious_book_ready']))
    return '\n'.join(lines)


def main(argv=None):
    import sys
    argv = list(sys.argv[1:] if argv is None else argv)
    d = argv[0] if argv else '.'
    try:
        print(summary(audit_capture(d)))
    except CaptureUnavailable as exc:
        print('STOPPED: %s' % exc)
        return 2
    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
