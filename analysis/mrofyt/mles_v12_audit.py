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
            _fail(fails, 'MISSING_FILE', blk.get('file', ''))
            continue
        if os.path.getsize(path) != blk.get('bytes'):
            _fail(fails, 'BYTE_SIZE_MISMATCH', stream)
        if sha256(path) != blk.get('sha256'):
            _fail(fails, 'HASH_MISMATCH', stream)
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
            elif k == 'quality':
                quality.append(e)
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

    for c in ZERO:
        v = man.get(c)
        if v is None:
            _fail(fails, 'MISSING_COUNTER', c)
        elif v:
            _fail(fails, 'RECORDER_REPORTED_' + c.upper(), str(v))

    # ---- depth sides, actions, levels --------------------------------
    info['depth_sides'] = sorted(depth_sides)
    info['depth_actions'] = sorted(depth_actions)
    for need in ('BID', 'ASK'):
        if need not in depth_sides:
            _fail(fails, 'MISSING_DEPTH_SIDE', need)
    for need in ('ADD', 'UPDATE', 'REMOVE'):
        if need not in depth_actions:
            _fail(fails, 'MISSING_DEPTH_ACTION', need)
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
    if info['book_ready'] > info['book_resync_starts']:
        _fail(fails, 'BOOK_READY_WITHOUT_RESYNC', '')
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
        if p.endswith('.csv.partial'):
            _fail(fails, 'ORPHAN_PARTIAL', p)
        elif p.endswith('.csv') and p not in referenced:
            _fail(fails, 'ORPHAN_FINALIZED_CSV', p)
        elif p.endswith('_RECOVERY.json'):
            _fail(fails, 'RECOVERY_ARTIFACT_PRESENT', p)

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
    for cid, rs in by_cid.items():
        ok, why = instance_seq_contiguous(rs)
        if not ok:
            _fail(fails, 'INSTANCE_SEQ_GAP', '%s: %s' % (cid, why))

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
    return dict(ok=not fails, failures=fails, runs=runs, info=info)


def summary(result):
    """Compact text for handing back; no market content."""
    lines = ['audit ok=%s failures=%d manifests=%d'
             % (result['ok'], len(result['failures']),
                result['info'].get('manifests', 0))]
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
    return '\n'.join(lines)


if __name__ == '__main__':
    import sys
    d = sys.argv[1] if len(sys.argv) > 1 else '.'
    print(summary(audit_capture(d)))
