#!/usr/bin/env python3
# ======================================================================
# MROF-YT-RECOVER-1.0 — manifest reconstruction for orphaned capture runs
#
# An ungraceful termination (power loss, forced reboot, NinjaTrader
# killed) stops the recorder before its finalizer can write the run's
# manifest. The CSVs survive -- often complete -- but the manifest IS the
# authoritative entrypoint for both the auditor and the runner, so
# without one the data is invisible to every downstream tool. The first
# fourteen-session capture had one such run on EVERY day of a week.
#
# This tool reconstructs a manifest from the rows themselves. It is a
# recovery aid, never a substitute for a recorder-written manifest:
#
#   * ORIGINALS ARE NEVER MODIFIED. A repaired stream is written as a
#     NEW file; the damaged one stays exactly as it is.
#   * THE RECORDER'S SELF-REPORTED INTEGRITY COUNTERS ARE NOT INVENTED.
#     gaps/duplicates/reversals/queueOverflows/droppedRows/writeErrors
#     are the recorder's own account of what it observed. Nothing in the
#     rows can reveal them. Writing 0 would assert "no rows were ever
#     dropped", which is exactly the claim we cannot make, so the fields
#     are OMITTED and the manifest is flagged `reconstructed`.
#   * A RECONSTRUCTED MANIFEST CANNOT VALIDATE ITS OWN FILE. Its hashes,
#     row counts and sequence bounds are computed FROM that file, so
#     they match by construction. That check is tautological and the
#     auditor says so rather than reporting a clean pass.
#   * A RUN STILL BEING WRITTEN IS NOT AN ORPHAN. The recorder writes
#     the manifest at close, so the run being recorded right now has
#     none either, and its streams end mid-row because a flush is in
#     progress. 1.0 listed today's live NQ and MNQ runs as "damaged,
#     needs --repair" on the first real capture folder it saw.
#
#     1.1 judged liveness by indirect signs (recent write, session label
#     not yet closed). On the operator's Windows machine the first never
#     fires -- Windows does not keep a held file's modified time current
#     -- and the second was the only thing protecting the live runs.
#     Reading the recorder source then showed it would NOT have held on
#     a weekend: the session roll is driven by market data, so the run
#     open over a weekend keeps Friday's label, and the recorder writes
#     nothing at all while the market is closed. 1.1 would have rebuilt
#     a manifest for the run NinjaTrader was still holding.
#
#     1.2 asks Windows directly. The recorder holds every stream open
#     FileShare.Read for the life of the run, so a read-only open that
#     refuses to share writing fails for exactly as long as the recorder
#     holds the file. Anything held, or that cannot be asked, is refused.
#   * A REPAIR MUST NOT FILL THE RECORDER'S DRIVE. Every .partial stream
#     is copied in full (the original is never renamed), so a real
#     folder's repair writes tens of GB onto the drive the recorder
#     writes to. 1.3 states the size against the free space in the dry
#     run, refuses a pass that would leave less than RESERVE_BYTES free
#     before writing anything, and re-checks per run.
#
# What still carries real assurance for a recovered run: cross-run
# instance sequence contiguity (does its seq range fit its siblings?),
# NQ/MNQ pairing, row-shape and enum validity, and the merge order.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
"""mrofyt_recover.py - MROF-YT-RECOVER-1.3

    python3 mrofyt_recover.py "<capture folder>" --dry-run   # list, instant
    python3 mrofyt_recover.py "<capture folder>"             # rebuild clean orphans
    python3 mrofyt_recover.py "<capture folder>" --repair    # also rewrite damaged tails
    ... --out recovery.json                                  # keep the report

Safe with NinjaTrader running: a run it still holds is recognised and
left alone. Run --repair on a weekend anyway -- it rewrites gigabytes
onto the drive the recorder writes to. The dry run says how many, and a
pass that would leave that drive with less than 40 GB free stops before
writing anything.
"""
import csv
import datetime as _dt
import glob
import hashlib
import json
import os
import re
import shutil
import sys
import time

import mles_v12_adapter as AD
import mrofyt_runner as RUN                 # session_id: the CME clock

RECOVER_VERSION = 'MROF-YT-RECOVER-1.3'
# Free space a write must leave on the capture drive -- it is the drive
# the recorder writes to, and on the Sunday after a weekend repair it
# starts again: about three session-days at the ~13 GB per session-day
# (both instruments) the September capture shows. A repair copies every
# .partial stream in full (originals are never renamed), so on a real
# folder it writes tens of GB.
RESERVE_BYTES = 40 * 10 ** 9
CLOSE_REASON = 'RECONSTRUCTED_NO_CLEAN_CLOSE'
# a stream modified more recently than this may be being written NOW;
# during a session the recorder flushes every flushPolicySeconds = 30 s
LIVE_MTIME_S = 600
# a run whose newest row (by the recorder's own clock) is younger than
# this may be one the recorder is closing right now -- its files already
# released, its manifest not yet written. Never touched in that window.
LIVE_CONTENT_S = 600
# the recorder's own account of what it observed; unknowable from rows
NEVER_INVENTED = ('gaps', 'duplicates', 'reversals', 'queueOverflows',
                  'droppedRows', 'writeErrors', 'reconnects', 'crossed',
                  'bookResets')
# taken from a sibling manifest of the SAME capture instance when one
# exists, because these are declarations, not observations
FROM_SIBLING = ('bookType', 'declaredDepth', 'flushPolicySeconds',
                'aggressorSource', 'recorderBuild')
# Anchored on what is STRUCTURAL in the recorder's naming -- an 8-digit
# session and a -R### run suffix (RunsOpened.ToString("D3")) -- not on
# the shape of the capture-instance id, which is only a timestamp plus a
# hash and must never be something this tool depends on.
RUN_RE = re.compile(r'^(?P<base>MLES12_.+?_(?P<session>\d{8})_'
                    r'(?P<run>[^_]+-R\d{3}))_'
                    r'(?P<stream>quotes|trades|depth|quality)\.csv'
                    r'(?P<partial>\.partial)?$')
IDX = {k: {n: i for i, n in enumerate(v)} for k, v in AD.HEADERS.items()}
_RECV = AD.HEADER_COMMON.index('tRecvUtc')


def _sha_and_bytes(path):
    h = hashlib.sha256()
    n = 0
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
            n += len(chunk)
    return h.hexdigest(), n


def _iso(dt):
    return dt.strftime('%Y-%m-%dT%H:%M:%S.%f0Z')


# ---------------------------------------------------------------------
# discovery
# ---------------------------------------------------------------------
def held_open_for_writing(path):
    """Ask Windows whether another process has this file open for
    writing: 'HELD', 'FREE', 'UNSUPPORTED' (not Windows) or 'ERROR: ...'.

    The recorder opens every stream FileAccess.Write, FileShare.Read and
    holds it for the life of the run. A request for READ access that
    does not itself share write access therefore fails with a sharing
    violation for exactly as long as the recorder holds the file, and
    succeeds the moment it is gone, whatever ended it. That answers "is
    this run still being recorded?" directly. The handle asks for read
    access only -- nothing can be written through it -- and is closed at
    once. Any failure other than the sharing violation is reported as an
    ERROR, never as FREE."""
    if os.name != 'nt':
        return 'UNSUPPORTED'
    try:
        import ctypes
        from ctypes import wintypes
        k32 = ctypes.WinDLL('kernel32', use_last_error=True)
        create = k32.CreateFileW
        create.restype = wintypes.HANDLE
        create.argtypes = (wintypes.LPCWSTR, wintypes.DWORD, wintypes.DWORD,
                           wintypes.LPVOID, wintypes.DWORD, wintypes.DWORD,
                           wintypes.HANDLE)
        k32.CloseHandle.argtypes = (wintypes.HANDLE,)
        h = create(os.path.abspath(path),
                   0x80000000,             # GENERIC_READ
                   0x00000001,             # FILE_SHARE_READ, NOT write
                   None,
                   3,                      # OPEN_EXISTING
                   0x80,                   # FILE_ATTRIBUTE_NORMAL
                   None)
        if h is None or h == wintypes.HANDLE(-1).value:
            err = ctypes.get_last_error()
            if err == 32:                  # ERROR_SHARING_VIOLATION
                return 'HELD'
            return 'ERROR: Windows error %d' % err
        k32.CloseHandle(h)
        return 'FREE'
    except Exception as exc:               # a check that failed never
        return 'ERROR: %s' % exc           # reads as "not held"


def newest_recv(path, kind):
    """Epoch seconds of the newest COMPLETE row in the file's last 64 KB,
    by the recorder's own clock (every row carries tRecvUtc), or None
    when there is no complete row there. Reads the tail only."""
    n = len(AD.HEADERS[kind])
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as fh:
            start = max(0, size - 65536)
            fh.seek(start)
            tail = fh.read()
    except OSError:
        return None
    lines = tail.split(b'\n')
    # the last piece is empty (clean end) or a row still being written;
    # the first is cut by the seek unless the tail began the file
    body = lines[:-1] if start == 0 else lines[1:-1]
    for raw in reversed(body):
        try:
            row = next(csv.reader([raw.rstrip(b'\r').decode()]), None)
            if row is None or len(row) != n:
                continue
            t = AD.iso_to_epoch(row[_RECV].strip())
        except Exception:
            continue
        if t is not None:
            return t
    return None


def live_check(run, now=None, probe=None):
    """Why this run must be left alone, or None if it is a true orphan.

    Where the recorder runs (Windows), held_open_for_writing is the
    answer. HELD on any stream: live. ERROR on any stream: refused, since
    a check that could not be asked is never read as "not held". All
    FREE: not being recorded -- unless its newest row is younger than
    LIVE_CONTENT_S or a file was modified within LIVE_MTIME_S, because a
    recorder that has just released the run may still be writing its
    manifest, and a manifest pinned in that window would race it.

    Elsewhere (a copied folder; NinjaTrader cannot run there) only
    indirect signs exist, and each errs toward refusal: a recent row, a
    recent modification, or a session label that is the current CME
    session or later. These are NOT sufficient on a live Windows
    recorder: the session roll is driven by market data, so a run held
    over a weekend keeps Friday's label, and the recorder writes nothing
    while the market is closed. That is why the direct check exists.

    Refusing is the only safe direction: a manifest pinned on a live run
    declares the session complete at whatever byte the scan reached, and
    the recorder later writes its own for the same run."""
    now = time.time() if now is None else now
    probe = held_open_for_writing if probe is None else probe
    verdicts = {os.path.basename(p): probe(p)
                for p in run['streams'].values()}
    answered = any(v in ('HELD', 'FREE') for v in verdicts.values())
    run['liveness_by'] = ('windows file-sharing check' if answered
                          else 'indirect signs (no Windows check here)')
    held = sorted(f for f, v in verdicts.items() if v == 'HELD')
    if held:
        return ('NinjaTrader still has %s open for writing'
                % ', '.join(held))
    errs = sorted('%s: %s' % (f, v) for f, v in verdicts.items()
                  if v.startswith('ERROR'))
    if errs:
        return ('could not ask Windows whether the recorder still holds '
                'this run (%s); a failed check is never read as "not held"'
                % '; '.join(errs))
    stamps = [s for s in (newest_recv(p, k)
                          for k, p in run['streams'].items())
              if s is not None]
    if stamps and now - max(stamps) < LIVE_CONTENT_S:
        return ('its newest row was stamped %d s ago by the recorder\'s '
                'own clock; a run that recent may still be closing'
                % max(now - max(stamps), 0))
    newest = max(os.path.getmtime(p) for p in run['streams'].values())
    age = now - newest
    if age < LIVE_MTIME_S:
        return 'still being written (last write %d s ago)' % max(age, 0)
    if not answered:
        cur = RUN.session_id(now)
        if run['session'] >= cur:
            return ('its session %s is the current CME session (%s) or '
                    'later; the recorder writes the manifest at close'
                    % (run['session'], cur))
    return None


def find_orphan_runs(directory, now=None, probe=None):
    """Group CSVs by run and return only the runs with NO manifest.

    Each entry: dict(base, session, run_id, partial, streams={kind:path},
    missing=[kinds absent], live=None|reason). A run missing a stream
    entirely is reported but never reconstructed: the runner skips such
    a run whole anyway, and inventing a manifest for it would only move
    the failure later. A LIVE run (see live_check) is returned so the
    report can name it, and is refused by every path that writes."""
    by = {}
    for p in sorted(os.listdir(directory)):
        m = RUN_RE.match(p)
        if not m:
            continue
        g = m.groupdict()
        e = by.setdefault(g['base'], dict(
            base=g['base'], session=g['session'], run_id=g['run'],
            partial=False, streams={}))
        e['streams'][g['stream']] = os.path.join(directory, p)
        if g['partial']:
            e['partial'] = True
    out = []
    for base, e in sorted(by.items()):
        # a run already reconstructed is no longer an orphan, so running
        # this tool twice over the same folder is a no-op the second time
        if any(os.path.exists(os.path.join(directory, base + suf))
               for suf in ('_manifest.json',
                           '_RECONSTRUCTED_manifest.json')):
            continue
        e['missing'] = sorted(set(AD.STREAMS) - set(e['streams']))
        e['live'] = live_check(e, now, probe)
        out.append(e)
    return out


def _live_result(res, reason):
    res.update(status='SKIPPED_LIVE_RUN', live=reason,
               notes=['NOT an orphan: ' + reason,
                      'left alone: the recorder writes this run\'s '
                      'manifest when the run closes; nothing was read '
                      'in bulk, nothing was written'])
    return res


def sibling_manifest(directory, run_id):
    """A manifest from the SAME capture instance, for the declared (not
    observed) fields. Identity is checked before anything is borrowed."""
    inst = run_id.rsplit('-R', 1)[0]
    best = None
    for p in sorted(glob.glob(os.path.join(directory, '*_manifest.json'))):
        try:
            man = json.load(open(p))
        except Exception:
            continue
        if man.get('captureInstanceId') == inst:
            best = man
            break
    return best


# ---------------------------------------------------------------------
# scan
# ---------------------------------------------------------------------
class _Scan(object):
    """Row statistics for one stream, plus the byte offset at which the
    file stops being well formed."""

    def __init__(self, kind):
        self.kind = kind
        self.rows = 0
        self.first_ev = self.last_ev = None
        self.first_ss = self.last_ss = None
        self.first_seg = self.last_seg = None
        self.first_recv = self.last_recv = None
        self.last_exch = None
        self.ident = {}
        self.good_bytes = 0        # end of the last well-formed row
        self.bad_row = None        # (row number, why)
        self.n_bid = self.n_ask = 0
        self.max_bid = self.max_ask = -1
        self.act = dict(ADD=0, UPDATE=0, REMOVE=0)
        self.book_type = None


def scan_stream(path, kind):
    """Stream one file, tolerating a malformed tail. Returns a _Scan.

    Deliberately does NOT use AD.iter_file: that raises on the first bad
    row, and a bad row is exactly what this tool exists to survive."""
    s = _Scan(kind)
    names = AD.HEADERS[kind]
    ix = IDX[kind]
    n = len(names)
    with open(path, newline='') as fh:
        head_line = fh.readline()
        if not head_line:
            s.bad_row = (0, 'file is empty')
            return s
        if next(csv.reader([head_line]), None) != names:
            s.bad_row = (0, 'header does not match the %s schema' % kind)
            return s
        s.good_bytes = len(head_line.encode())
        for i, line in enumerate(fh, start=1):
            if not line.endswith('\n'):
                s.bad_row = (i, 'last line has no newline (write cut off)')
                break
            raw = next(csv.reader([line]), None)
            if raw is None or len(raw) != n:
                s.bad_row = (i, 'expected %d columns, got %d'
                             % (n, 0 if raw is None else len(raw)))
                break
            try:
                ev = int(raw[ix['eventSeq']])
                ss = int(raw[ix['streamSeq']])
                seg = int(raw[ix['segId']])
                recv = AD.parse_iso(raw[ix['tRecvUtc']])
            except Exception as exc:
                s.bad_row = (i, 'unparsable row: %s' % exc)
                break
            if recv is None:
                s.bad_row = (i, 'row has no receive timestamp')
                break
            if not s.rows:
                s.first_ev, s.first_ss, s.first_seg = ev, ss, seg
                s.first_recv = recv
                s.ident = {f: raw[ix[f]] for f in
                           ('schema', 'captureInstanceId', 'runId',
                            'session', 'instrument', 'contract')}
            s.last_ev, s.last_ss, s.last_seg = ev, ss, seg
            s.last_recv = recv
            ex = AD.parse_iso(raw[ix['tExchUtc']])
            if ex is not None:
                s.last_exch = ex
            if kind == 'depth':
                s.book_type = s.book_type or raw[ix['bookType']]
                side, act = raw[ix['side']], raw[ix['action']]
                try:
                    lvl = int(raw[ix['level']])
                except ValueError:
                    lvl = -1
                if side == 'BID':
                    s.n_bid += 1
                    s.max_bid = max(s.max_bid, lvl)
                else:
                    s.n_ask += 1
                    s.max_ask = max(s.max_ask, lvl)
                if act in s.act:
                    s.act[act] += 1
            s.rows += 1
            s.good_bytes += len(line.encode())
    return s


# ---------------------------------------------------------------------
# reconstruct
# ---------------------------------------------------------------------
def _truncate_to(src, dst, kind, safe_ev):
    """Copy rows with eventSeq <= safe_ev into a NEW file. Returns rows
    written. The source is opened read-only and never touched."""
    ix = IDX[kind]
    kept = 0
    with open(src, newline='') as fi, open(dst, 'w', newline='') as fo:
        fo.write(fi.readline())                       # header
        for line in fi:
            if not line.endswith('\n'):
                break
            raw = next(csv.reader([line]), None)
            if raw is None or len(raw) != len(AD.HEADERS[kind]):
                break
            try:
                if int(raw[ix['eventSeq']]) > safe_ev:
                    break
            except ValueError:
                break
            fo.write(line)
            kept += 1
    return kept


def probe_stream(path, kind):
    """Cheap end-check: is the header right, and does the file end on a
    complete row? Reads the first line and the last few KB, never the
    middle, so it costs the same on a 6 GB file as on a small one.

    This is all a dry run needs. Reconstruction itself still does the
    full scan_stream pass, because sequence bounds and row counts can
    only come from every row."""
    size = os.path.getsize(path)
    names = AD.HEADERS[kind]
    with open(path, 'rb') as fh:
        head = fh.readline()
        if not head:
            return dict(size=size, ok=False, why='file is empty')
        try:
            cols = next(csv.reader([head.decode().rstrip('\r\n')]), None)
        except UnicodeDecodeError:
            return dict(size=size, ok=False, why='header is not text')
        if cols != names:
            return dict(size=size, ok=False,
                        why='header does not match the %s schema' % kind)
        if size <= len(head):
            return dict(size=size, ok=False, rows_hint=0,
                        why='header only, no rows')
        fh.seek(max(len(head), size - 65536))
        tail = fh.read()
    if not tail.endswith(b'\n'):
        return dict(size=size, ok=False,
                    why='last line has no newline (write cut off)')
    last = tail.rstrip(b'\n').rsplit(b'\n', 1)[-1]
    try:
        raw = next(csv.reader([last.decode()]), None)
    except UnicodeDecodeError:
        return dict(size=size, ok=False, why='last line is not text')
    if raw is None or len(raw) != len(names):
        return dict(size=size, ok=False,
                    why='last row has %d columns, expected %d'
                        % (0 if raw is None else len(raw), len(names)))
    return dict(size=size, ok=True,
                last_event_seq=int(raw[IDX[kind]['eventSeq']]))


def probe_run(run):
    """Dry-run verdict for one orphaned run, without reading the bulk."""
    res = dict(base=run['base'], run_id=run['run_id'],
               session=run['session'], partial=run['partial'],
               written=[], notes=[])
    if run.get('live'):
        res['bytes_total'] = sum(os.path.getsize(p)
                                 for p in run['streams'].values())
        return _live_result(res, run['live'])
    if run['missing']:
        res.update(status='SKIPPED_INCOMPLETE_RUN', missing=run['missing'],
                   notes=['a run missing a whole stream is skipped by the '
                          'runner anyway; reconstructing its manifest '
                          'would only move the failure downstream'])
        return res
    probes = {k: probe_stream(p, k) for k, p in run['streams'].items()}
    bad = {k: v['why'] for k, v in probes.items() if not v['ok']}
    res['bytes_total'] = sum(v['size'] for v in probes.values())
    res['streams'] = {k: dict(bytes=v['size'], ends_cleanly=v['ok'],
                              why=v.get('why'))
                      for k, v in sorted(probes.items())}
    if any(v.get('rows_hint') == 0 for v in probes.values()):
        res.update(status='SKIPPED_NO_USABLE_ROWS',
                   empty_streams=sorted(k for k, v in probes.items()
                                        if v.get('rows_hint') == 0))
    elif bad:
        res.update(status='WOULD_RECONSTRUCT_WITH_REPAIR', damaged_tail=bad,
                   notes=['needs --repair: a damaged stream is rewritten '
                          'as a new _RECOVERED.csv and the original is '
                          'left untouched'])
    else:
        res.update(status='WOULD_RECONSTRUCT',
                   notes=['every stream ends on a complete row; no repair '
                          'needed, just the missing manifest'])
    return res


class InsufficientSpace(RuntimeError):
    """A write that would leave the capture drive with less than
    RESERVE_BYTES free. Raised before anything is written."""


def _free_bytes(directory):
    return shutil.disk_usage(directory).free


def _copies(run, damaged_names=(), needs_cut=()):
    """The streams a non-dry run rewrites as _RECOVERED.csv: every
    .partial one (a finalized name cannot be had without a copy, and the
    original is never renamed), every damaged one, every one cut."""
    out = []
    for k, p in run['streams'].items():
        if p.endswith('.partial') or k in damaged_names or k in needs_cut:
            out.append(k)
    return out


def write_plan(runs, results, directory, repair):
    """Upper bound of what a real run would write, from the dry-run
    probes: for a damaged run every stream (the cut may reach any of
    them), otherwise the .partial ones. Damaged runs count only when
    `repair` (without it they are left as NEEDS_REPAIR)."""
    by_base = {r['base']: r for r in runs}
    need = 0
    for res in results:
        run = by_base.get(res.get('base'))
        if run is None or run.get('live'):
            continue
        st = res.get('status')
        if st == 'WOULD_RECONSTRUCT_WITH_REPAIR':
            if repair:
                need += sum(os.path.getsize(p) for p in run['streams'].values())
        elif st == 'WOULD_RECONSTRUCT':
            need += sum(os.path.getsize(run['streams'][k])
                        for k in _copies(run))
    try:
        free = _free_bytes(directory)
    except OSError:
        free = None
    return dict(bytes_to_write=need, free_bytes=free,
                reserve_bytes=RESERVE_BYTES,
                fits=None if free is None else free - need >= RESERVE_BYTES)


def reconstruct(directory, run, repair=False, dry_run=False, now=None,
                probe=None):
    """Reconstruct one orphaned run. Returns a result dict; writes
    nothing when dry_run. `repair` permits rewriting a damaged stream to
    its last well-formed row (as a new file). A live run is refused
    here as well as at discovery, re-checked at call time, so a direct
    caller cannot bypass it."""
    res = dict(base=run['base'], run_id=run['run_id'],
               session=run['session'], partial=run['partial'],
               written=[], status=None, notes=[])
    reason = run.get('live') or live_check(run, now, probe)
    if reason:
        return _live_result(res, reason)
    if run['missing']:
        res.update(status='SKIPPED_INCOMPLETE_RUN',
                   missing=run['missing'],
                   notes=['a run missing a whole stream is skipped by the '
                          'runner anyway; reconstructing its manifest '
                          'would only move the failure downstream'])
        return res

    scans = {k: scan_stream(p, k) for k, p in run['streams'].items()}
    empty = [k for k, s in scans.items() if not s.rows]
    if empty:
        res.update(status='SKIPPED_NO_USABLE_ROWS', empty_streams=empty)
        return res

    # one identity for the whole run, taken from the rows and checked
    ident = scans['depth'].ident if 'depth' in scans else \
        next(iter(scans.values())).ident
    for k, s in scans.items():
        if s.ident != ident:
            res.update(status='SKIPPED_MIXED_IDENTITY',
                       notes=['%s disagrees on identity with the rest of '
                              'the run' % k])
            return res
    if ident.get('schema') != AD.SCHEMA:
        res.update(status='SKIPPED_FOREIGN_SCHEMA',
                   notes=[str(ident.get('schema'))])
        return res

    damaged = {k: s.bad_row for k, s in scans.items() if s.bad_row}
    # The cut point is constrained ONLY by damaged streams.
    #
    # When a stream is cut off mid-write, rows beyond its last good one
    # are gone, and rows in OTHER streams past that point describe a
    # world the damaged stream can no longer account for -- merged, they
    # would advance quotes past the last depth update and freeze the
    # book, the precise failure the runner's STREAM_SIZE_MISMATCH guard
    # exists to prevent. So every stream is truncated to the earliest
    # such point.
    #
    # An UNDAMAGED run is not cut at all. Its four streams legitimately
    # end at different eventSeq -- whichever kind of event happened last
    # wins, and a SHUTDOWN row in `quality` routinely ends above the
    # others. Taking a minimum there would silently discard real data.
    if damaged:
        safe_ev = min(scans[k].last_ev for k in damaged)
    else:
        safe_ev = max(s.last_ev for s in scans.values())
    needs_cut = {k: s for k, s in scans.items() if s.last_ev > safe_ev}
    if damaged and not repair:
        res.update(status='NEEDS_REPAIR', damaged={k: list(v) for k, v
                                                   in damaged.items()},
                   notes=['re-run with repair=True (--repair) to write '
                          'truncated copies; originals are never touched'])
        return res
    if dry_run:
        res.update(status='WOULD_RECONSTRUCT',
                   damaged={k: list(v) for k, v in damaged.items()},
                   safe_event_seq=safe_ev,
                   streams_to_truncate=sorted(needs_cut))
        return res

    # ---- room on the drive the recorder writes to, checked per run ----
    # (the directory-level plan refuses a pass that cannot fit; this
    # catches the space shrinking during one, and direct callers)
    copy = [k for k in run['streams']
            if k in damaged or k in needs_cut or
            run['streams'][k].endswith('.partial')]
    need = sum(os.path.getsize(run['streams'][k]) for k in copy)
    if need and _free_bytes(directory) - need < RESERVE_BYTES:
        res.update(status='SKIPPED_NO_SPACE',
                   notes=['would write %.1f GB with %.1f GB free; at least '
                          '%.0f GB must stay free for the recorder'
                          % (need / 1e9, _free_bytes(directory) / 1e9,
                             RESERVE_BYTES / 1e9)])
        return res

    # ---- write repaired copies where needed -------------------------
    out_paths = dict(run['streams'])
    for k, p in sorted(run['streams'].items()):
        base = os.path.basename(p)
        clean = base[:-len('.partial')] if base.endswith('.partial') else base
        if k in damaged or k in needs_cut or base != clean:
            dst = os.path.join(directory, clean.replace(
                '.csv', '_RECOVERED.csv'))
            kept = _truncate_to(p, dst, k, safe_ev)
            out_paths[k] = dst
            res['written'].append(os.path.basename(dst))
            res['notes'].append('%s: kept %d rows up to eventSeq %d'
                                % (k, kept, safe_ev))

    # ---- rescan whatever will actually be referenced ----------------
    final = {k: scan_stream(p, k) for k, p in out_paths.items()}
    if any(s.bad_row for s in final.values()) or \
            not all(s.rows for s in final.values()):
        res.update(status='FAILED_REPAIR',
                   notes=res['notes'] + ['a rewritten stream is still not '
                                         'well formed; nothing was pinned'])
        return res

    dep = final['depth']
    man = dict(ident)
    man.update(
        reconstructed=True,
        reconstructedBy=RECOVER_VERSION,
        reconstructedAtUtc=_iso(_dt.datetime.now(_dt.timezone.utc)),
        reconstructionNote=(
            'Rebuilt from the rows after an ungraceful termination left '
            'no manifest. The recorder self-reported counters (%s) are '
            'ABSENT, not zero: nothing in the rows can reveal them. '
            'Hashes, row counts and sequence bounds here are computed '
            'from these files, so they match by construction and prove '
            'nothing about them.' % ', '.join(NEVER_INVENTED)),
        closeReason=CLOSE_REASON,
        firstRecvUtc=_iso(min(s.first_recv for s in final.values())),
        lastRecvUtc=_iso(max(s.last_recv for s in final.values())),
        lastExchUtc=_iso(max(s.last_exch for s in final.values()
                             if s.last_exch is not None))
        if any(s.last_exch for s in final.values()) else None,
        firstEventSeq=min(s.first_ev for s in final.values()),
        lastEventSeq=max(s.last_ev for s in final.values()),
        firstSegId=min(s.first_seg for s in final.values()),
        lastSegId=max(s.last_seg for s in final.values()),
        connectionSegments=max(s.last_seg for s in final.values()),
        maxBidLevelSeen=dep.max_bid + 1, maxAskLevelSeen=dep.max_ask + 1,
        maxBidLevelRun=dep.max_bid + 1, maxAskLevelRun=dep.max_ask + 1,
        depthBid=dep.n_bid, depthAsk=dep.n_ask,
        depthAdd=dep.act['ADD'], depthUpdate=dep.act['UPDATE'],
        depthRemove=dep.act['REMOVE'])
    # written out one by one on purpose: the manifest's per-stream key
    # names are irregular (quotes -> Quote, quality -> Quality) and a
    # clever loop here would be a silent naming bug
    man.update(firstQuoteSeq=final['quotes'].first_ss,
               lastQuoteSeq=final['quotes'].last_ss,
               firstTradeSeq=final['trades'].first_ss,
               lastTradeSeq=final['trades'].last_ss,
               firstDepthSeq=final['depth'].first_ss,
               lastDepthSeq=final['depth'].last_ss,
               firstQualitySeq=final['quality'].first_ss,
               lastQualitySeq=final['quality'].last_ss)
    sib = sibling_manifest(directory, run['run_id'])
    if sib:
        man['reconstructedFieldsFrom'] = sib.get('runId')
        for f in FROM_SIBLING:
            if sib.get(f) is not None:
                man[f] = sib[f]
    else:
        man['bookType'] = dep.book_type or 'MBP'
        man['declaredDepth'] = max(dep.max_bid, dep.max_ask) + 1
        man['declaredDepthInferred'] = True
        res['notes'].append('no sibling manifest for this capture '
                            'instance; declaredDepth inferred from the '
                            'deepest level observed')
    for k, p in sorted(out_paths.items()):
        sha, nbytes = _sha_and_bytes(p)
        man[k] = dict(present=True, file=os.path.basename(p),
                      bytes=nbytes, rows=final[k].rows, sha256=sha)

    mp = os.path.join(directory, run['base'] + '_RECONSTRUCTED_manifest.json')
    # written aside and moved into place, as the recorder does its own:
    # a drive that drops mid-write leaves a .tmp every tool ignores, never
    # a half manifest that marks the run done
    tmp = mp + '.tmp'
    with open(tmp, 'w') as fh:
        json.dump(man, fh, indent=1)
    os.replace(tmp, mp)
    res['written'].append(os.path.basename(mp))
    res.update(status='RECONSTRUCTED', manifest=os.path.basename(mp),
               events=man['lastEventSeq'] - man['firstEventSeq'] + 1,
               rows={k: final[k].rows for k in sorted(final)})
    return res


def recover_directory(directory, repair=False, dry_run=False, now=None,
                      probe=None):
    """A dry run PROBES (header + tail only, near-instant even on a 6 GB
    depth file); a real run SCANS every row, because only every row can
    give the sequence bounds and counts a manifest must carry. Live
    runs are listed, counted apart, and never scanned or written."""
    runs = find_orphan_runs(directory, now, probe)
    probes = [probe_run(r) for r in runs]
    # what --repair would write, and whether the drive can take it; a
    # real pass that cannot fit is refused before anything is written
    plan = write_plan(runs, probes, directory, repair=True)
    plan_now = write_plan(runs, probes, directory, repair) \
        if not dry_run else None
    if not dry_run and plan_now['fits'] is False:
        raise InsufficientSpace(
            'this pass would write up to %.1f GB and %s has %.1f GB free; '
            'at least %.0f GB must stay free for the recorder. Nothing was '
            'written.' % (plan_now['bytes_to_write'] / 1e9, directory,
                          plan_now['free_bytes'] / 1e9, RESERVE_BYTES / 1e9))
    if dry_run:
        results = probes
    else:
        results = [reconstruct(directory, r, repair, False, now, probe)
                   for r in runs]
    live = sum(1 for r in runs if r['live'])
    by = sorted({r.get('liveness_by') for r in runs if r.get('liveness_by')})
    return dict(recover=RECOVER_VERSION, directory=directory,
                repair=repair, dry_run=dry_run,
                runs_without_manifest=len(runs),
                orphan_runs=len(runs) - live, live_runs=live,
                liveness_by=by, repair_write_plan=plan, results=results)


def text_summary(rep):
    L = ['%s  %s' % (rep['recover'], rep['directory']),
         'runs without a manifest: %d   (repair=%s, dry_run=%s)'
         % (rep.get('runs_without_manifest', rep['orphan_runs']),
            rep['repair'], rep['dry_run']),
         '  orphaned (recoverable): %d' % rep['orphan_runs'],
         '  still being written (NOT orphans, left alone): %d'
         % rep.get('live_runs', 0)]
    if rep.get('liveness_by'):
        L.append('  "still being written" decided by: %s'
                 % ', '.join(rep['liveness_by']))
    gb = sum(r.get('bytes_total') or 0 for r in rep['results']
             if r['status'] != 'SKIPPED_LIVE_RUN') / 1e9
    if gb:
        L.append('recoverable data in orphaned runs: %.2f GB' % gb)
    wp = rep.get('repair_write_plan')
    if wp and wp.get('bytes_to_write'):
        L.append('--repair would write up to %.1f GB of copies (originals '
                 'are never touched); drive free now: %s; must stay free for '
                 'the recorder: %.0f GB -> %s'
                 % (wp['bytes_to_write'] / 1e9,
                    'unknown' if wp['free_bytes'] is None
                    else '%.1f GB' % (wp['free_bytes'] / 1e9),
                    wp['reserve_bytes'] / 1e9,
                    'fits' if wp['fits'] else
                    'DOES NOT FIT: free space first, or ask'
                    if wp['fits'] is False else 'cannot tell'))
    by = {}
    for r in rep['results']:
        by.setdefault(r['status'], []).append(r)
    for st in sorted(by):
        L.append('')
        L.append('%s: %d' % (st, len(by[st])))
        for r in by[st]:
            sz = (('  %.2f GB' % (r['bytes_total'] / 1e9))
                  if r.get('bytes_total') else '')
            L.append('  %s %s%s%s' % (r['session'], r['run_id'],
                                      '  [partial]' if r['partial'] else '',
                                      sz))
            for nt in r.get('notes', []):
                L.append('      %s' % nt)
            for d, why in sorted((r.get('damaged_tail') or {}).items()):
                L.append('      %s ends badly: %s' % (d, why))
            for d, why in sorted((r.get('damaged') or {}).items()):
                L.append('      %s damaged at row %s: %s'
                         % (d, why[0], why[1]))
    if any(r['status'] == 'RECONSTRUCTED' for r in rep['results']):
        L.append('')
        L.append('Reconstructed manifests are flagged "reconstructed": '
                 'true and carry NO recorder integrity counters. Re-run '
                 'the auditor; it reports them as '
                 'RECONSTRUCTED_RUN_NOT_SELF_VERIFYING rather than a '
                 'clean pass, because a manifest built from a file '
                 'cannot validate that file.')
    return '\n'.join(L)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv:
        print(__doc__)
        return 2
    d = argv[0]
    try:
        os.listdir(d)
    except OSError as exc:
        print('STOPPED: cannot read %s (%s). Is the drive connected, and '
              'is it still that letter?' % (d, exc))
        return 2
    try:
        rep = recover_directory(d, repair='--repair' in argv,
                                dry_run='--dry-run' in argv)
    except InsufficientSpace as exc:
        print('STOPPED: %s' % exc)
        return 2
    except OSError as exc:
        try:
            os.listdir(d)
        except OSError:
            print('STOPPED: %s stopped answering mid-run (%s). The drive '
                  'was disconnected or lost power. Originals are never '
                  'modified, so nothing is damaged: reconnect and re-run.'
                  % (d, exc))
            return 2
        raise
    print(text_summary(rep))
    if '--out' in argv:
        p = argv[argv.index('--out') + 1]
        json.dump(rep, open(p, 'w'), indent=1, default=str)
        print('\nrecovery report -> %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
