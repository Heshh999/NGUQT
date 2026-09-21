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
#
# What still carries real assurance for a recovered run: cross-run
# instance sequence contiguity (does its seq range fit its siblings?),
# NQ/MNQ pairing, row-shape and enum validity, and the merge order.
#
# THIS PROJECT DOES NOT AUTHORIZE LIVE TRADING.
# ======================================================================
import csv
import datetime as _dt
import glob
import hashlib
import json
import os
import re
import sys

import mles_v12_adapter as AD

RECOVER_VERSION = 'MROF-YT-RECOVER-1.0'
CLOSE_REASON = 'RECONSTRUCTED_NO_CLEAN_CLOSE'
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
def find_orphan_runs(directory):
    """Group CSVs by run and return only the runs with NO manifest.

    Each entry: dict(base, session, run_id, partial, streams={kind:path},
    missing=[kinds absent]). A run missing a stream entirely is reported
    but never reconstructed: the runner skips such a run whole anyway,
    and inventing a manifest for it would only move the failure later."""
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
        out.append(e)
    return out


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


def reconstruct(directory, run, repair=False, dry_run=False):
    """Reconstruct one orphaned run. Returns a result dict; writes
    nothing when dry_run. `repair` permits rewriting a damaged stream to
    its last well-formed row (as a new file)."""
    res = dict(base=run['base'], run_id=run['run_id'],
               session=run['session'], partial=run['partial'],
               written=[], status=None, notes=[])
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
    json.dump(man, open(mp, 'w'), indent=1)
    res['written'].append(os.path.basename(mp))
    res.update(status='RECONSTRUCTED', manifest=os.path.basename(mp),
               events=man['lastEventSeq'] - man['firstEventSeq'] + 1,
               rows={k: final[k].rows for k in sorted(final)})
    return res


def recover_directory(directory, repair=False, dry_run=False):
    """A dry run PROBES (header + tail only, near-instant even on a 6 GB
    depth file); a real run SCANS every row, because only every row can
    give the sequence bounds and counts a manifest must carry."""
    runs = find_orphan_runs(directory)
    if dry_run:
        results = [probe_run(r) for r in runs]
    else:
        results = [reconstruct(directory, r, repair, False) for r in runs]
    return dict(recover=RECOVER_VERSION, directory=directory,
                repair=repair, dry_run=dry_run,
                orphan_runs=len(runs), results=results)


def text_summary(rep):
    L = ['%s  %s' % (rep['recover'], rep['directory']),
         'orphan runs found: %d   (repair=%s, dry_run=%s)'
         % (rep['orphan_runs'], rep['repair'], rep['dry_run'])]
    gb = sum(r.get('bytes_total') or 0 for r in rep['results']) / 1e9
    if gb:
        L.append('recoverable data in orphaned runs: %.2f GB' % gb)
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
    rep = recover_directory(d, repair='--repair' in argv,
                            dry_run='--dry-run' in argv)
    print(text_summary(rep))
    if '--out' in argv:
        p = argv[argv.index('--out') + 1]
        json.dump(rep, open(p, 'w'), indent=1, default=str)
        print('\nrecovery report -> %s' % p)
    return 0


if __name__ == '__main__':
    sys.exit(main())
