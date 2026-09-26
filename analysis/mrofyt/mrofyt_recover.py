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
#   * ONE UNREADABLE FILE MUST NOT STOP THE PASS. The first real dry run
#     of 1.3 died with OSError 22 on a single leftover file -- one cut
#     off when the drive dropped, most likely; Python reports many
#     Windows disk errors that way. 1.4 names the file with its Windows
#     error, sets that run aside as SKIPPED_UNREADABLE_FILE (never
#     repaired), and carries on; a drive that vanished still stops.
#   * A PASS THAT STOPS MUST SAY WHERE, AND WHY. The first real --repair
#     on the operator's drive (1.4, 26 Sep) printed nothing for its whole
#     run -- the summary comes at the end -- then stopped when Windows
#     refused to create one _RECOVERED.csv (errno 22) and the folder
#     stopped listing. The only record of what got done was the manifests
#     on the drive, and "the drive was disconnected" was a guess: the
#     same errno comes back from a damaged folder index on a drive that
#     is still there. 1.5:
#       - prints each run as it starts and as it ends, and what it is
#         doing in between, so a stop shows exactly how far it got;
#       - asks the drive root and the folder separately after a failed
#         read or write, and names which one stopped answering -- drive
#         gone, folder unreadable, or a step refused while both answer;
#       - never writes after a refused write: this run's own new files
#         are removed and the pass stops, since pressing on means more
#         writes into a folder that has just refused one;
#       - checks, before reading anything in bulk, that the folder takes
#         a new file at all (the recorder needs the same on Sunday);
#       - takes runs oldest session first, so the DEV days the study
#         needs next come before the sealed hold-out days;
#       - does not trust its own manifest blindly: one from an earlier
#         pass that does not parse, or whose copies are missing or not
#         the size it records, marks the run for redoing, never done;
#       - borrows declared fields only from a manifest the recorder
#         wrote, never from a reconstructed one (a redo would otherwise
#         borrow from its own stale manifest).
#
# What still carries real assurance for a recovered run: cross-run
# instance sequence contiguity (does its seq range fit its siblings?),
# NQ/MNQ pairing, row-shape and enum validity, and the merge order.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
"""mrofyt_recover.py - MROF-YT-RECOVER-1.5

    python3 mrofyt_recover.py "<capture folder>" --dry-run   # list, instant
    python3 mrofyt_recover.py "<capture folder>"             # rebuild clean orphans
    python3 mrofyt_recover.py "<capture folder>" --repair    # also rewrite damaged tails
    ... --out recovery.json                                  # keep the report

Safe with NinjaTrader running: a run it still holds is recognised and
left alone. Run --repair on a weekend anyway -- it rewrites gigabytes
onto the drive the recorder writes to. The dry run says how many, and a
pass that would leave that drive with less than 40 GB free stops before
writing anything.

A real pass prints each run as it goes, oldest session first. If it is
interrupted, run it again: runs already rebuilt are skipped, and a run
whose rebuild was cut short is done again.
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

RECOVER_VERSION = 'MROF-YT-RECOVER-1.5'
# Free space a write must leave on the capture drive -- it is the drive
# the recorder writes to, and on the Sunday after a weekend repair it
# starts again: about three session-days at the ~13 GB per session-day
# (both instruments) the September capture shows. A repair copies every
# .partial stream in full (originals are never renamed), so on a real
# folder it writes tens of GB.
RESERVE_BYTES = 40 * 10 ** 9
# No stream row is anywhere near this long. A file cut off when the
# drive dropped can come back zero-filled with no line break at all, and
# a line-by-line reader would then pull the whole multi-GB file into
# memory looking for one. Every read here is bounded by this instead.
MAX_LINE_BYTES = 1 << 20
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


def _group_runs(directory):
    """[dict(base, session, run_id, partial, streams={kind: path})], one
    per run with a stream file in the folder, in the order runs are handled:
    oldest session first (then by name), so the development days a study
    needs next come before the sealed hold-out days."""
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
    return [by[b] for b in sorted(by, key=lambda b: (by[b]['session'], b))]


def reconstructed_problem(directory, base):
    """None when the _RECONSTRUCTED_manifest.json an earlier pass wrote
    for this run holds up; otherwise why it cannot be trusted.

    The manifest is written last, after its copies, so a pass cut off
    mid-run leaves none. But a drive that drops can lose writes it had
    already acknowledged, so the manifest is read back and every file it
    names must exist at the byte count it records. Sizes only -- cheap
    enough for every listing; the auditor re-hashes every file."""
    mp = os.path.join(directory, base + '_RECONSTRUCTED_manifest.json')
    try:
        with open(mp) as fh:
            man = json.load(fh)
    except (OSError, ValueError) as exc:
        return 'its manifest from an earlier pass cannot be read (%s)' % exc
    if not isinstance(man, dict) or man.get('reconstructed') is not True:
        return 'its manifest from an earlier pass is not a reconstructed one'
    for k in AD.STREAMS:
        ent = man.get(k)
        if not isinstance(ent, dict) or not ent.get('file'):
            return 'its manifest from an earlier pass names no %s file' % k
        try:
            size = os.path.getsize(os.path.join(directory, ent['file']))
        except OSError:
            return ('%s, named by its manifest from an earlier pass, is '
                    'missing' % ent['file'])
        if size != ent.get('bytes'):
            return ('%s is %d bytes but its manifest from an earlier pass '
                    'records %s: that pass was cut short'
                    % (ent['file'], size, ent.get('bytes')))
    return None


def _manifest_state(directory, base):
    """'RECORDER' (the recorder's own manifest: never touched), 'REBUILT'
    (an earlier pass's reconstructed manifest that holds up), None (no
    manifest), or the reason an earlier pass's manifest cannot be
    trusted (the run is done again)."""
    if os.path.exists(os.path.join(directory, base + '_manifest.json')):
        return 'RECORDER'
    if not os.path.exists(os.path.join(
            directory, base + '_RECONSTRUCTED_manifest.json')):
        return None
    return reconstructed_problem(directory, base) or 'REBUILT'


def rebuilt_runs(directory):
    """Run ids an earlier pass already rebuilt, whose manifests hold up."""
    return [e['run_id'] for e in _group_runs(directory)
            if _manifest_state(directory, e['base']) == 'REBUILT']


def find_orphan_runs(directory, now=None, probe=None):
    """Group CSVs by run and return only the runs with NO manifest,
    oldest session first.

    Each entry: dict(base, session, run_id, partial, streams={kind:path},
    missing=[kinds absent], live=None|reason, and redo=reason when an
    earlier pass left a manifest that does not hold up). A run missing a
    stream entirely is reported but never reconstructed: the runner
    skips such a run whole anyway, and inventing a manifest for it would
    only move the failure later. A LIVE run (see live_check) is returned
    so the report can name it, and is refused by every path that
    writes."""
    out = []
    for e in _group_runs(directory):
        # a run already reconstructed is no longer an orphan, so running
        # this tool twice over the same folder is a no-op the second time
        # -- unless the first pass was cut short (reconstructed_problem)
        state = _manifest_state(directory, e['base'])
        if state in ('RECORDER', 'REBUILT'):
            continue
        if state is not None:
            e['redo'] = state
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
    observed) fields. Identity is checked before anything is borrowed.

    Only a manifest the RECORDER wrote counts (1.5). A reconstructed one
    holds declarations only second-hand -- borrowed from a recorder
    manifest that is then found directly, or inferred from the rows,
    which are not declarations at all -- and a run rebuilt again (a
    redo) would otherwise borrow from its own stale manifest."""
    inst = run_id.rsplit('-R', 1)[0]
    best = None
    for p in sorted(glob.glob(os.path.join(directory, '*_manifest.json'))):
        try:
            with open(p) as fh:
                man = json.load(fh)
        except Exception:
            continue
        if not isinstance(man, dict) or man.get('reconstructed'):
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


def _lines(fh, max_len=MAX_LINE_BYTES):
    """Lines of a binary file, memory-bounded. Yields each complete line
    as bytes including its newline; a final piece with no newline is
    yielded without one; a line longer than max_len is yielded as None
    (what a zero-filled or garbage stretch looks like) and iteration
    stops -- nothing past it is a row."""
    pending = b''
    while True:
        chunk = fh.read(1 << 20)
        if not chunk:
            if pending:
                yield pending
            return
        pending += chunk
        while True:
            i = pending.find(b'\n')
            if i < 0:
                break
            yield pending[:i + 1]
            pending = pending[i + 1:]
        if len(pending) > max_len:
            yield None
            return


TOO_LONG = 'line longer than %d KB: not a stream row (zero-filled or ' \
           'garbage after a crash?)' % (MAX_LINE_BYTES // 1024)


def _text(b):
    return b.decode('utf-8', 'replace')


def scan_stream(path, kind):
    """Stream one file, tolerating a malformed tail. Returns a _Scan.

    Deliberately does NOT use AD.iter_file: that raises on the first bad
    row, and a bad row is exactly what this tool exists to survive.
    Reads are memory-bounded (see _lines)."""
    s = _Scan(kind)
    names = AD.HEADERS[kind]
    ix = IDX[kind]
    n = len(names)
    with open(path, 'rb') as fh:
        it = _lines(fh)
        head_line = next(it, b'')
        if head_line is None:
            s.bad_row = (0, 'no header line: ' + TOO_LONG)
            return s
        if not head_line:
            s.bad_row = (0, 'file is empty')
            return s
        if next(csv.reader([_text(head_line)]), None) != names:
            s.bad_row = (0, 'header does not match the %s schema' % kind)
            return s
        s.good_bytes = len(head_line)
        for i, bline in enumerate(it, start=1):
            if bline is None:
                s.bad_row = (i, TOO_LONG)
                break
            if not bline.endswith(b'\n'):
                s.bad_row = (i, 'last line has no newline (write cut off)')
                break
            line = _text(bline)
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
            s.good_bytes += len(bline)
    return s


# ---------------------------------------------------------------------
# reconstruct
# ---------------------------------------------------------------------
def _truncate_to(src, dst, kind, safe_ev):
    """Copy rows with eventSeq <= safe_ev into a NEW file. Returns rows
    written. The source is opened read-only and never touched."""
    ix = IDX[kind]
    kept = 0
    try:
        with open(src, 'rb') as fi:
            fo = _open_w(dst, 'wb')    # a failure writing is marked as one,
            try:                       # so a stop can say which side failed
                it = _lines(fi)
                _w(fo, next(it, b'') or b'')          # header
                for bline in it:
                    if bline is None or not bline.endswith(b'\n'):
                        break
                    raw = next(csv.reader([_text(bline)]), None)
                    if raw is None or len(raw) != len(AD.HEADERS[kind]):
                        break
                    try:
                        if int(raw[ix['eventSeq']]) > safe_ev:
                            break
                    except ValueError:
                        break
                    _w(fo, bline)
                    kept += 1
            finally:
                _close_w(fo)
    except OSError as exc:
        if not getattr(exc, 'writing', False):
            _named(exc, src)               # the read side failed
        raise
    return kept


def probe_stream(path, kind):
    """Cheap end-check: is the header right, and does the file end on a
    complete row? Reads the first line and the last few KB, never the
    middle, so it costs the same on a 6 GB file as on a small one.

    This is all a dry run needs. Reconstruction itself still does the
    full scan_stream pass, because sequence bounds and row counts can
    only come from every row."""
    names = AD.HEADERS[kind]
    try:
        size = os.path.getsize(path)
        with open(path, 'rb') as fh:
            first = fh.read(MAX_LINE_BYTES)           # bounded, never readline
            if not first:
                return dict(size=size, ok=False, why='file is empty')
            nl = first.find(b'\n')
            if nl < 0:
                return dict(size=size, ok=False, rows_hint=0,
                            why='no header line: ' + TOO_LONG)
            head = first[:nl + 1]
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
    except OSError as exc:
        # the drive answers but THIS file cannot be read -- typically one
        # cut off when the drive dropped. Named, never repaired, never a
        # crash of the whole pass (a vanished drive is caught in main)
        return dict(size=_size_or_none(path), ok=False, unreadable=True,
                    why=_read_error(exc))
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


def _size_or_none(path):
    try:
        return os.path.getsize(path)
    except OSError:
        return None


def _os_error_text(exc):
    """'Windows error 1392: ...' or 'errno 22: Invalid argument'. Python
    reports many Windows disk errors as errno 22 'Invalid argument'; the
    Windows code, where Python keeps it, is the informative part."""
    we = getattr(exc, 'winerror', None)
    no = getattr(exc, 'errno', None)
    code = ('Windows error %s' % we) if we else \
        ('errno %s' % no) if no else 'error'
    return '%s: %s' % (code, getattr(exc, 'strerror', None) or exc)


def _read_error(exc):
    """'cannot be read (Windows error 1392: ...)'."""
    return 'cannot be read (%s)' % _os_error_text(exc)


# ---------------------------------------------------------------------
# when the drive fails mid-pass: which part stopped answering
# ---------------------------------------------------------------------
DRIVE_GONE = 'DRIVE_GONE'
FOLDER_UNREADABLE = 'FOLDER_UNREADABLE'
WRITE_REFUSED = 'WRITE_REFUSED'
READ_REFUSED = 'READ_REFUSED'
NEXT_STEP = {
    DRIVE_GONE: 'Reconnect the drive (straight into the laptop, not '
                'through a hub), check the folder lists again, and run the '
                'same command: runs already rebuilt are skipped and it '
                'carries on where it stopped.',
    FOLDER_UNREADABLE: 'Do not run --repair again yet: it would write '
                       'into a folder that is failing. Check the drive '
                       'before anything else writes to it.',
    WRITE_REFUSED: 'Do not run --repair again yet: it would write into a '
                   'folder that has just refused a write. Check the drive '
                   'before anything else writes to it.',
    READ_REFUSED: 'The drive and the folder still answer, so this is one '
                  'file or one step, not the drive. Send a screenshot of '
                  'this before running anything else.',
}


class PassStopped(RuntimeError):
    """A read or write failed in a way that ends the pass. .verdict is
    DRIVE_GONE, FOLDER_UNREADABLE, WRITE_REFUSED or READ_REFUSED;
    .results holds what the pass finished before the stop."""

    def __init__(self, verdict, message, results=None):
        RuntimeError.__init__(self, message)
        self.verdict = verdict
        self.results = list(results or [])


def _answers(path):
    """None when the path can be listed, else the OSError."""
    try:
        os.listdir(path)
        return None
    except OSError as exc:
        return exc


def _drive_root(directory):
    """D:\\ for D:\\MLES_Capture; the parent folder where there are no
    drive letters."""
    ap = os.path.abspath(directory)
    drive = os.path.splitdrive(ap)[0]
    return drive + os.sep if drive else os.path.dirname(ap)


def diagnose(directory, exc, writing=True):
    """After a failed step: (verdict, sentence). The drive root and the
    folder are asked separately, at once, because the error itself does
    not say which failed: errno 22 comes back from a drive that has gone
    and from a damaged folder index on a drive that is still there.

      DRIVE_GONE         the drive root does not answer
      FOLDER_UNREADABLE  the root answers, the folder cannot be listed
      WRITE_REFUSED      both answer; the write itself was refused
      READ_REFUSED       both answer; a read was refused (writing=False)
    """
    root = _drive_root(directory)
    f = getattr(exc, 'filename', None)
    step = '%s %s' % ('writing' if writing else 'reading',
                      os.path.basename(f) if f else 'a file')
    what = '%s failed with %s' % (step, _os_error_text(exc))
    root_err = _answers(root)
    if root_err is not None:
        return DRIVE_GONE, (
            '%s. The drive itself (%s) stopped answering (%s): it was '
            'disconnected or lost power.'
            % (what, root, _os_error_text(root_err)))
    folder_err = _answers(directory)
    if folder_err is not None:
        return FOLDER_UNREADABLE, (
            '%s. The drive (%s) still answers, but the folder %s can no '
            'longer be listed (%s). The drive is connected; the folder\'s '
            'index on it is damaged.'
            % (what, root, directory, _os_error_text(folder_err)))
    if writing:
        return WRITE_REFUSED, (
            '%s. The drive (%s) and the folder both still answer, so the '
            'drive did not disconnect: Windows refused the write itself. '
            'That points to damage in the file system on the drive (the '
            'folder\'s index, or its record of free space), not to the '
            'cable.' % (what, root))
    return READ_REFUSED, (
        '%s. The drive (%s) and the folder both still answer.' % (what, root))


def _remove_own(paths):
    """Remove files THIS pass created for a run it could not finish:
    (removed, [(name, error)]). Only ever _RECOVERED.csv copies and a
    manifest .tmp -- never an original."""
    removed, left = [], []
    for p in paths:
        try:
            if os.path.exists(p):
                os.remove(p)
                removed.append(os.path.basename(p))
        except OSError as exc:
            left.append((os.path.basename(p), _os_error_text(exc)))
    return removed, left


def _stopped(directory, exc, written, writing=True, diag=None):
    """The PassStopped for a failed step. Where the drive still answers,
    this run's own new files are removed first, so the folder holds no
    copy that no manifest references."""
    verdict, sentence = diag or diagnose(directory, exc, writing)
    msg = [sentence]
    if verdict != DRIVE_GONE and written:
        removed, left = _remove_own(written)
        if removed:
            msg.append('Removed the unfinished copies this run had '
                       'started: %s.' % ', '.join(removed))
        if left:
            msg.append('Could not remove %s; the next pass replaces it.'
                       % '; '.join('%s (%s)' % x for x in left))
    msg.append('Nothing more was written. Originals are never modified.')
    msg.append(NEXT_STEP[verdict])
    return PassStopped(verdict, ' '.join(msg))


WRITE_CHECK_NAME = '_mrofyt_recover_write_check.tmp'


def write_check(directory):
    """Before a real pass reads anything in bulk: does the folder take a
    new file? One small file is created, synced, read back and removed.
    None when it does, else the OSError. The recorder needs the same
    thing every time it opens a run."""
    p = os.path.join(directory, WRITE_CHECK_NAME)
    payload = b'MROF-YT-RECOVER write check\n' * 64
    try:
        with open(p, 'wb') as fh:
            fh.write(payload)
            fh.flush()
            os.fsync(fh.fileno())
        with open(p, 'rb') as fh:
            back = fh.read()
        os.remove(p)
    except OSError as exc:
        if exc.filename is None:
            exc.filename = p
        return exc
    if back != payload:
        return OSError(5, 'the check file read back different from what '
                          'was written', p)
    return None


def _unreadable_result(res, bad):
    res.update(status='SKIPPED_UNREADABLE_FILE', unreadable=bad,
               notes=['a file of this run cannot be read from the drive '
                      '(often one cut off when the drive disconnected); '
                      'the run is left exactly as it is and nothing is '
                      'written for it'])
    return res


def probe_run(run):
    """Dry-run verdict for one orphaned run, without reading the bulk."""
    res = dict(base=run['base'], run_id=run['run_id'],
               session=run['session'], partial=run['partial'],
               written=[], notes=[])
    if run.get('redo'):
        res['redo'] = run['redo']
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
    res['bytes_total'] = sum(v['size'] or 0 for v in probes.values())
    unread = {os.path.basename(run['streams'][k]): v['why']
              for k, v in probes.items() if v.get('unreadable')}
    if unread:
        return _unreadable_result(res, unread)
    bad = {k: v['why'] for k, v in probes.items() if not v['ok']}
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
    if run.get('redo'):
        res['notes'].append('an earlier pass left this run unfinished (%s); '
                            'a real pass rebuilds it' % run['redo'])
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
                probe=None, say=None):
    """Reconstruct one orphaned run. Returns a result dict; writes
    nothing when dry_run. `repair` permits rewriting a damaged stream to
    its last well-formed row (as a new file). A live run is refused
    here as well as at discovery, re-checked at call time, so a direct
    caller cannot bypass it. `say` receives a line per phase.

    Raises PassStopped when the drive or the folder stops answering, or
    when a write is refused: this run's own new files are removed where
    the drive still answers, and nothing more is written."""
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

    say = say or (lambda s: None)
    scans = {}
    say('reading every row (%.2f GB); this is the slow part'
        % (sum(_size_or_none(p) or 0 for p in run['streams'].values()) / 1e9))
    for k, p in sorted(run['streams'].items()):
        try:
            scans[k] = scan_stream(p, k)
        except OSError as exc:
            # one file the drive will not read sets the run aside (1.4);
            # a drive or folder that stopped answering ends the pass
            diag = diagnose(directory, _named(exc, p), writing=False)
            if diag[0] in (DRIVE_GONE, FOLDER_UNREADABLE):
                raise _stopped(directory, exc, [], writing=False, diag=diag)
            return _unreadable_result(res, {os.path.basename(p):
                                            _read_error(exc)})
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

    # every file this pass creates for the run, so a stop can take them
    # back out: the folder must never hold a copy no manifest references
    written_now = []
    try:
        return _write_run(directory, run, res, scans, ident, damaged,
                          needs_cut, safe_ev, written_now, say)
    except OSError as exc:
        raise _stopped(directory, exc, written_now,
                       writing=getattr(exc, 'writing', False))


def _open_w(path, mode='wb'):
    """open() for writing, with any failure marked as a write."""
    try:
        return open(path, mode)
    except OSError as exc:
        exc.writing = True
        raise


def _named(exc, path):
    """An error from read()/write() on an open file carries no file
    name; give it the one it happened on."""
    if getattr(exc, 'filename', None) is None:
        exc.filename = path
    return exc


def _w(fh, data):
    try:
        fh.write(data)
    except OSError as exc:
        exc.writing = True
        raise _named(exc, fh.name)


def _close_w(fh):
    """close() flushes: a failure there is a failed write too."""
    try:
        fh.close()
    except OSError as exc:
        exc.writing = True
        raise _named(exc, fh.name)


def _read(path, fn, *args):
    """fn(*args), with a read failure named after `path`."""
    try:
        return fn(*args)
    except OSError as exc:
        raise _named(exc, path)


def _write_run(directory, run, res, scans, ident, damaged, needs_cut,
               safe_ev, written_now, say):
    """The writing half of reconstruct(). Every file it creates is added
    to written_now BEFORE it is opened."""
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
    if copy:
        say('writing %d cop%s (%.2f GB)' % (len(copy), 'y' if len(copy) == 1
                                            else 'ies', need / 1e9))
    for k, p in sorted(run['streams'].items()):
        base = os.path.basename(p)
        clean = base[:-len('.partial')] if base.endswith('.partial') else base
        if k in damaged or k in needs_cut or base != clean:
            dst = os.path.join(directory, clean.replace(
                '.csv', '_RECOVERED.csv'))
            written_now.append(dst)
            kept = _truncate_to(p, dst, k, safe_ev)
            out_paths[k] = dst
            res['written'].append(os.path.basename(dst))
            res['notes'].append('%s: kept %d rows up to eventSeq %d'
                                % (k, kept, safe_ev))

    # ---- rescan whatever will actually be referenced ----------------
    say('checking what was written')
    final = {k: _read(p, scan_stream, p, k)
             for k, p in sorted(out_paths.items())}
    if any(s.bad_row for s in final.values()) or \
            not all(s.rows for s in final.values()):
        # nothing is pinned, so the copies would be referenced by no
        # manifest: take them back out rather than leave them loose
        removed, left = _remove_own(written_now)
        res.update(status='FAILED_REPAIR', written=[],
                   notes=res['notes'] + ['a rewritten stream is still not '
                                         'well formed; nothing was pinned'] +
                   (['removed the copies: %s' % ', '.join(removed)]
                    if removed else []) +
                   ['could not remove %s (%s)' % x for x in left])
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
    say('fingerprinting the files (SHA-256) and writing the manifest')
    for k, p in sorted(out_paths.items()):
        sha, nbytes = _read(p, _sha_and_bytes, p)
        man[k] = dict(present=True, file=os.path.basename(p),
                      bytes=nbytes, rows=final[k].rows, sha256=sha)

    mp = os.path.join(directory, run['base'] + '_RECONSTRUCTED_manifest.json')
    # written aside and moved into place, as the recorder does its own:
    # a drive that drops mid-write leaves a .tmp every tool ignores, never
    # a half manifest that marks the run done
    tmp = mp + '.tmp'
    written_now.append(tmp)
    fh = _open_w(tmp, 'w')
    try:
        _w(fh, json.dumps(man, indent=1))
    finally:
        _close_w(fh)
    try:
        os.replace(tmp, mp)
    except OSError as exc:
        exc.writing = True
        raise
    written_now.remove(tmp)
    res['written'].append(os.path.basename(mp))
    res.update(status='RECONSTRUCTED', manifest=os.path.basename(mp),
               events=man['lastEventSeq'] - man['firstEventSeq'] + 1,
               rows={k: final[k].rows for k in sorted(final)})
    return res


def _label(run):
    """'NQ_NQ_DEC26' from MLES12_NQ_NQ_DEC26_<session>_<run id>."""
    head = run['base'].split('_%s_' % run['session'], 1)[0]
    return head[len('MLES12_'):] if head.startswith('MLES12_') else head


def _one_line(res):
    """A run's outcome in one line, for the progress output."""
    st = res.get('status')
    why = ''
    if res.get('unreadable'):
        why = '; '.join('%s %s' % kv for kv in sorted(res['unreadable'].items()))
    elif res.get('empty_streams'):
        why = 'no usable rows in: %s' % ', '.join(res['empty_streams'])
    elif res.get('live'):
        why = res['live']
    elif res.get('missing'):
        why = 'missing: %s' % ', '.join(res['missing'])
    elif st in ('NEEDS_REPAIR', 'SKIPPED_NO_SPACE', 'FAILED_REPAIR',
                'SKIPPED_MIXED_IDENTITY', 'SKIPPED_FOREIGN_SCHEMA') and \
            res.get('notes'):
        why = res['notes'][-1]
    return st + (' (%s)' % why if why else '')


def recover_directory(directory, repair=False, dry_run=False, now=None,
                      probe=None, progress=None):
    """A dry run PROBES (header + tail only, near-instant even on a 6 GB
    depth file); a real run SCANS every row, because only every row can
    give the sequence bounds and counts a manifest must carry. Live
    runs are listed, counted apart, and never scanned or written.

    A real pass first checks the folder takes a new file, then goes
    through the runs oldest session first; `progress`, when given,
    receives a line as each run starts, moves through its phases and
    ends. It raises PassStopped (with .results: what it finished) when
    the drive or the folder stops answering, or a write is refused."""
    say = progress or (lambda s: None)
    rebuilt = rebuilt_runs(directory)
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
        results = []
        will_write = [p for p in probes
                      if p['status'] == 'WOULD_RECONSTRUCT' or
                      (repair and p['status'] ==
                       'WOULD_RECONSTRUCT_WITH_REPAIR')]
        say('rebuilt by an earlier pass: %d run(s). To go through now: %d, '
            'oldest session first.' % (len(rebuilt), len(runs)))
        if will_write:
            say('checking that %s takes a new file ...' % directory)
            err = write_check(directory)
            if err is not None:
                raise _stopped(directory, err,
                               [os.path.join(directory, WRITE_CHECK_NAME)],
                               writing=True)
            say('  yes')
        for i, (r, pr) in enumerate(zip(runs, probes), 1):
            say('[%d/%d] %s  %s  %s  %.2f GB'
                % (i, len(runs), r['session'], _label(r), r['run_id'],
                   (pr.get('bytes_total') or 0) / 1e9))
            t0 = time.time()
            if pr['status'] == 'SKIPPED_UNREADABLE_FILE':
                res = pr        # known unreadable: never read a second time
            else:
                try:
                    res = reconstruct(directory, r, repair, False, now, probe,
                                      say=lambda s: say('      ' + s))
                except PassStopped as exc:
                    exc.results = results
                    raise
            results.append(res)
            say('      done: %s, %.1f min' % (_one_line(res),
                                              (time.time() - t0) / 60))
    live = sum(1 for r in runs if r['live'])
    by = sorted({r.get('liveness_by') for r in runs if r.get('liveness_by')})
    return dict(recover=RECOVER_VERSION, directory=directory,
                repair=repair, dry_run=dry_run,
                rebuilt_earlier=rebuilt,
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
    if 'rebuilt_earlier' in rep:
        L.append('rebuilt by an earlier pass (their manifests check out): %d'
                 % len(rep['rebuilt_earlier']))
    redo = [r for r in rep['results'] if r.get('redo')]
    if redo:
        L.append('  left unfinished by an earlier pass, rebuilt again by a '
                 'real pass: %d' % len(redo))
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
            for f, why in sorted((r.get('unreadable') or {}).items()):
                L.append('      %s %s' % (f, why))
    if any(r['status'] == 'RECONSTRUCTED' for r in rep['results']):
        L.append('')
        L.append('Reconstructed manifests are flagged "reconstructed": '
                 'true and carry NO recorder integrity counters. Re-run '
                 'the auditor; it reports them as '
                 'RECONSTRUCTED_RUN_NOT_SELF_VERIFYING rather than a '
                 'clean pass, because a manifest built from a file '
                 'cannot validate that file.')
    return '\n'.join(L)


def _say(line):
    print(line, flush=True)


def _where(exc):
    """'reconstruct(), line 1040' -- the last step of this tool the
    error passed through, so a screenshot says where it stopped without
    a traceback."""
    import traceback
    tb = traceback.extract_tb(exc.__traceback__)
    mine = [f for f in tb if os.path.basename(f.filename) ==
            os.path.basename(__file__)]
    f = (mine or tb or [None])[-1]
    return None if f is None else '%s(), line %d' % (f.name, f.lineno)


def _report_stop(d, stop, out, where=None):
    done = [r['run_id'] for r in stop.results
            if r.get('status') == 'RECONSTRUCTED']
    print('')
    print('STOPPED (%s): %s' % (stop.verdict, stop))
    print('Rebuilt in this pass before the stop: %d run(s)%s'
          % (len(done), (': ' + ', '.join(done)) if done else '.'))
    if where:
        print('(stopped in %s)' % where)
    if out:
        try:
            with open(out, 'w') as fh:
                json.dump(dict(recover=RECOVER_VERSION, directory=d,
                               stopped=stop.verdict, message=str(stop),
                               where=where, results=stop.results),
                          fh, indent=1, default=str)
            print('stop report -> %s' % out)
        except OSError as exc:
            print('could not write the stop report %s (%s)'
                  % (out, _os_error_text(exc)))


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
    repair = '--repair' in argv
    dry = '--dry-run' in argv
    out = argv[argv.index('--out') + 1] if '--out' in argv else None
    if not dry:
        _say('%s  %s  (%s)' % (RECOVER_VERSION, d, 'repair' if repair
                               else 'rebuild clean orphans'))
    try:
        rep = recover_directory(d, repair=repair, dry_run=dry,
                                progress=None if dry else _say)
    except InsufficientSpace as exc:
        print('STOPPED: %s' % exc)
        return 2
    except PassStopped as exc:
        _report_stop(d, exc, out)
        return 2
    except OSError as exc:
        # anywhere else (discovery, a probe): the same question -- is it
        # the drive, the folder, or one file -- answered, not guessed
        diag = diagnose(d, exc, writing=getattr(exc, 'writing', False))
        stop = PassStopped(diag[0], '%s Nothing more was written. Originals '
                                    'are never modified. %s'
                           % (diag[1], NEXT_STEP[diag[0]]))
        _report_stop(d, stop, out, where=_where(exc))
        return 2
    if not dry:
        _say('')
    print(text_summary(rep))
    if out:
        json.dump(rep, open(out, 'w'), indent=1, default=str)
        print('\nrecovery report -> %s' % out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
